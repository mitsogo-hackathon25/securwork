import json
import queue
import threading
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import close_old_connections, transaction
from django.db.models import Count, Prefetch, ProtectedError
from django.db.utils import DatabaseError, OperationalError
from django.http import HttpResponse, StreamingHttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .admin_serializers import (
    AdminBrandSerializer,
    AdminColorSerializer,
    AdminCategoryOptionSerializer,
    AdminCategorySerializer,
    AdminProductImageSerializer,
    AdminProductListSerializer,
    AdminProductSerializer,
)
from .filters import BilingualProductSearchFilter
from .csv_import import (
    BRAND_FILTER_NONE,
    canonical_brand_key,
    build_csv_template,
    export_products_csv,
    import_parsed_rows,
    iter_import_parsed_rows,
    normalize_column_key,
    parse_and_validate_csv,
    scan_csv_brands,
    scan_csv_column_values,
    scan_csv_columns,
)
from .category_ordering import sort_categories
from .models import Brand, Category, Color, Product, ProductImage, ProductVariant
from .permissions import IsStaffUser
from .product_images import attach_image_from_url, create_product_image

_PRODUCT_DELETE_BLOCKED_CODE = "product_delete_blocked"
_PRODUCT_DELETE_BLOCKED_DETAIL = (
    "Impossibile eliminare il prodotto per vincoli del database."
)
_PRODUCT_DELETE_DB_ERROR_DETAIL = (
    "Eliminazione non riuscita: database occupato o schema non aggiornato. "
    "Attendi la fine di un import CSV, poi riprova. "
    "Se il problema persiste, esegui `python manage.py migrate` sul server."
)
_PRODUCT_DELETE_DB_ERROR_CODE = "product_delete_database_error"

_DELETE_ALL_CONFIRM = "Stilpromo@2026"
_DELETE_SQLITE_MAX_ATTEMPTS = 10
_DELETE_SQLITE_RETRY_BASE_SEC = 0.05


def _parse_string_list_field(request, *field_names: str) -> list[str] | None:
    raw = None
    for name in field_names:
        raw = request.data.get(name)
        if raw is None:
            raw = request.POST.get(name)
        if raw is not None and raw != "":
            break
    if raw is None or raw == "":
        return None
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        parsed = [part.strip() for part in str(raw).split(",") if part.strip()]
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    single = str(parsed).strip()
    return [single] if single else []


def _normalize_filter_value_keys(keys: list[str]) -> set[str]:
    from .csv_import import _header_key

    normalized: set[str] = set()
    for key in keys:
        if key == BRAND_FILTER_NONE:
            normalized.add(BRAND_FILTER_NONE)
            continue
        normalized.add(canonical_brand_key(key))
        normalized.add(key.strip().lower())
        folded = _header_key(key)
        if folded:
            normalized.add(folded)
    return normalized


def _parse_brand_keys_filter(request) -> set[str] | None:
    """None = import all brands; empty set = invalid (caller should reject)."""
    keys = _parse_string_list_field(request, "brands")
    if keys is None:
        return None
    return _normalize_filter_value_keys(keys)


def _parse_column_value_filter(request) -> tuple[str, set[str]] | None:
    """None = no column filter. Empty value set = invalid (caller should reject)."""
    column_raw = request.data.get("filter_column")
    if column_raw is None:
        column_raw = request.POST.get("filter_column")
    value_keys = _parse_string_list_field(request, "filter_values")
    if not column_raw and value_keys is None:
        return None
    if not column_raw or not str(column_raw).strip():
        return ("", set())
    if value_keys is None:
        return (normalize_column_key(str(column_raw)), set())
    return (normalize_column_key(str(column_raw)), _normalize_filter_value_keys(value_keys))


def _product_display_name(product: Product) -> str:
    return (
        product.safe_translation_getter("name", language_code="it", any_language=True)
        or product.sku
    )


def _sqlite_lock_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return "locked" in message or "busy" in message


def _delete_one_product(product: Product) -> None:
    """Remove catalog product; order lines keep name/SKU snapshots (variant unlinked)."""
    from orders.models import OrderItem

    pk = product.pk
    last_error: OperationalError | None = None

    for attempt in range(_DELETE_SQLITE_MAX_ATTEMPTS):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return

        try:
            with transaction.atomic():
                variant_ids = list(
                    ProductVariant.objects.filter(product_id=product.pk).values_list("pk", flat=True),
                )
                if variant_ids:
                    OrderItem.objects.filter(variant_id__in=variant_ids).update(variant=None)
                product.delete()
            return
        except OperationalError as exc:
            if not _sqlite_lock_error(exc):
                raise
            last_error = exc
            close_old_connections()
            time.sleep(_DELETE_SQLITE_RETRY_BASE_SEC * (2 ** attempt))

    if last_error:
        raise last_error


def _iter_products_for_delete(products) -> list[Product]:
    """Resolve products by id so SQLite is not read via a live iterator while rows are deleted."""
    if isinstance(products, Product):
        return [products]
    if hasattr(products, "values_list"):
        pk_list = list(products.values_list("pk", flat=True))
    else:
        pk_list = [p.pk for p in products]
    resolved: list[Product] = []
    for pk in pk_list:
        product = Product.objects.filter(pk=pk).first()
        if product:
            resolved.append(product)
    return resolved


def _delete_catalog_products(products) -> tuple[list[int], list[dict]]:
    deleted_ids: list[int] = []
    blocked: list[dict] = []
    for product in _iter_products_for_delete(products):
        pk = product.pk
        name = _product_display_name(product)
        try:
            _delete_one_product(product)
            deleted_ids.append(pk)
        except ProtectedError:
            blocked.append({
                "id": pk,
                "name": name,
                "detail": _PRODUCT_DELETE_BLOCKED_DETAIL,
                "code": _PRODUCT_DELETE_BLOCKED_CODE,
            })
        except DatabaseError:
            close_old_connections()
            blocked.append({
                "id": pk,
                "name": name,
                "detail": _PRODUCT_DELETE_DB_ERROR_DETAIL,
                "code": _PRODUCT_DELETE_DB_ERROR_CODE,
            })
    return deleted_ids, blocked


def _bulk_delete_response(deleted_ids: list[int], blocked: list[dict], not_found: list[int]) -> Response:
    deleted_count = len(deleted_ids)
    blocked_count = len(blocked)
    if deleted_count and not blocked_count:
        detail = f"Eliminati {deleted_count} prodott{'o' if deleted_count == 1 else 'i'}."
    elif deleted_count and blocked_count:
        detail = (
            f"Eliminati {deleted_count} prodott{'o' if deleted_count == 1 else 'i'}. "
            f"{blocked_count} non eliminabili."
        )
    elif blocked_count:
        detail = (
            f"Nessun prodotto eliminato: {blocked_count} "
            f"non eliminabili."
        )
    else:
        detail = "Nessun prodotto trovato da eliminare."

    return Response({
        "detail": detail,
        "deleted": deleted_ids,
        "blocked": blocked,
        "not_found": not_found,
    })


class AdminProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    filter_backends = [DjangoFilterBackend, BilingualProductSearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "is_featured", "is_new_arrival", "is_bestseller"]
    ordering_fields = ["created_at", "updated_at", "sku", "slug"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        qs = Product.objects.prefetch_related(
            Prefetch("variants", to_attr="prefetched_variants"),
            Prefetch("images", to_attr="prefetched_images"),
            "categories",
        ).annotate(variant_count=Count("variants"))

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(categories__slug=category)

        in_stock = self.request.query_params.get("in_stock")
        if in_stock == "true":
            qs = qs.filter(variants__is_active=True, variants__stock_quantity__gt=0).distinct()
        elif in_stock == "false":
            qs = qs.exclude(variants__is_active=True, variants__stock_quantity__gt=0).distinct()

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return AdminProductListSerializer
        return AdminProductSerializer

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        try:
            _delete_one_product(product)
        except ProtectedError:
            return Response(
                {
                    "detail": _PRODUCT_DELETE_BLOCKED_DETAIL,
                    "code": _PRODUCT_DELETE_BLOCKED_CODE,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DatabaseError:
            return Response(
                {
                    "detail": _PRODUCT_DELETE_DB_ERROR_DETAIL,
                    "code": _PRODUCT_DELETE_DB_ERROR_CODE,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="csv_template")
    def csv_template(self, request):
        content = build_csv_template()
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="securwork-products-template.csv"'
        return response

    @action(detail=False, methods=["get"], url_path="export_csv")
    def export_csv(self, request):
        content = export_products_csv()
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="securwork-products-export.csv"'
        return response

    @action(detail=False, methods=["post"], url_path="adjust_prices")
    def adjust_prices(self, request):
        percent_raw = request.data.get("percent")
        brand_raw = request.data.get("brand")
        if percent_raw in (None, ""):
            return Response(
                {"detail": "Indica una percentuale (es. 10 o -5)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if brand_raw is None or (isinstance(brand_raw, str) and not brand_raw.strip()):
            return Response(
                {"detail": "Seleziona una marca."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        brand_key = str(brand_raw).strip()
        try:
            percent = Decimal(str(percent_raw).replace(",", "."))
        except (InvalidOperation, ValueError):
            return Response(
                {"detail": "Percentuale non valida."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if percent <= -100:
            return Response(
                {"detail": "La riduzione non può essere del 100% o superiore."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if percent == 0:
            return Response(
                {"detail": "La percentuale deve essere diversa da zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if brand_key == "__none__":
            variants_qs = ProductVariant.objects.filter(product__brand="")
            brand_label = "Senza marca"
        else:
            variants_qs = ProductVariant.objects.filter(product__brand__iexact=brand_key)
            brand_label = brand_key

        factor = (Decimal("100") + percent) / Decimal("100")
        updated_variants = 0
        for variant in variants_qs.select_related("product").iterator():
            new_price = (variant.price * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            variant.price = max(Decimal("0.01"), new_price)
            if variant.sale_price is not None:
                new_sale = (variant.sale_price * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                variant.sale_price = max(Decimal("0.01"), new_sale)
            variant.save(update_fields=["price", "sale_price"])
            updated_variants += 1

        direction = "aumentati" if percent > 0 else "ridotti"
        return Response({
            "detail": (
                f"Prezzi {direction} del {abs(percent)}% su {updated_variants} varianti "
                f"({brand_label})."
            ),
            "updated_variants": updated_variants,
            "percent": str(percent),
            "brand": brand_label,
        })

    @action(detail=False, methods=["post"], url_path="bulk_delete")
    def bulk_delete(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "Indica almeno un id prodotto (campo ids)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(ids) > 500:
            return Response(
                {"detail": "Puoi eliminare al massimo 500 prodotti per volta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        not_found: list[int] = []
        products_to_delete: list[Product] = []

        for raw_id in ids:
            try:
                pk = int(raw_id)
            except (TypeError, ValueError):
                continue
            product = Product.objects.filter(pk=pk).first()
            if not product:
                not_found.append(pk)
                continue
            products_to_delete.append(product)

        deleted_ids, blocked = _delete_catalog_products(products_to_delete)
        return _bulk_delete_response(deleted_ids, blocked, not_found)

    @action(detail=False, methods=["post"], url_path="delete_all")
    def delete_all(self, request):
        if request.data.get("confirm") != _DELETE_ALL_CONFIRM:
            return Response(
                {
                    "detail": (
                        "Operazione distruttiva: invia confirm='Stilpromo@2026' "
                        "per eliminare tutti i prodotti del catalogo."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_ids, blocked = _delete_catalog_products(Product.objects.all())
        return _bulk_delete_response(deleted_ids, blocked, [])

    def _ndjson_line(self, payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=False) + "\n"

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="import_csv_brands",
    )
    def import_csv_brands(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "Carica un file CSV usando il campo file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = (upload.name or "").lower()
        if not name.endswith(".csv"):
            return Response(
                {"detail": "Sono accettati solo file .csv."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        brands, errors = scan_csv_brands(upload.read())
        if errors:
            return Response(
                {
                    "detail": errors[0].get("message", "Impossibile leggere il CSV."),
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"brands": brands})

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="import_csv_columns",
    )
    def import_csv_columns(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "Carica un file CSV usando il campo file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = (upload.name or "").lower()
        if not name.endswith(".csv"):
            return Response(
                {"detail": "Sono accettati solo file .csv."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        columns, errors = scan_csv_columns(upload.read())
        if errors:
            return Response(
                {
                    "detail": errors[0].get("message", "Impossibile leggere il CSV."),
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"columns": columns})

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="import_csv_column_values",
    )
    def import_csv_column_values(self, request):
        upload = request.FILES.get("file")
        column = request.data.get("column") or request.POST.get("column")
        if not upload:
            return Response(
                {"detail": "Carica un file CSV usando il campo file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not column or not str(column).strip():
            return Response(
                {"detail": "Indica la colonna da analizzare."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = (upload.name or "").lower()
        if not name.endswith(".csv"):
            return Response(
                {"detail": "Sono accettati solo file .csv."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        values, errors = scan_csv_column_values(upload.read(), str(column))
        if errors:
            return Response(
                {
                    "detail": errors[0].get("message", "Impossibile leggere il CSV."),
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            "column": normalize_column_key(str(column)),
            "values": values,
        })

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="import_csv_stream",
    )
    def import_csv_stream(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "Carica un file CSV usando il campo file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = (upload.name or "").lower()
        if not name.endswith(".csv"):
            return Response(
                {"detail": "Sono accettati solo file .csv."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_bytes = upload.read()
        estimated_rows = max(1, file_bytes.count(b"\n") - 1)
        column_value_filter = _parse_column_value_filter(request)
        brand_keys_filter = _parse_brand_keys_filter(request)
        if column_value_filter is not None:
            col_key, value_keys = column_value_filter
            if not col_key:
                return Response(
                    {"detail": "Seleziona una colonna per filtrare l'import."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not value_keys:
                return Response(
                    {"detail": "Seleziona almeno un valore da importare."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            brand_keys_filter = None
        elif brand_keys_filter is not None and not brand_keys_filter:
            return Response(
                {"detail": "Seleziona almeno una marca da importare."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        def event_stream():
            progress_queue: queue.Queue = queue.Queue()
            parsed_holder: list[list[dict]] = []
            errors_holder: list[list[dict]] = []

            def on_validate(current: int, total: int) -> None:
                progress_queue.put({
                    "phase": "validating",
                    "current": current,
                    "total": total,
                    "message": "Validazione righe CSV…",
                })

            def run_parse() -> None:
                try:
                    parsed, errors = parse_and_validate_csv(
                        file_bytes,
                        progress_callback=on_validate,
                        progress_total=estimated_rows,
                        brand_keys_filter=brand_keys_filter,
                        column_value_filter=column_value_filter,
                    )
                    parsed_holder.append(parsed)
                    errors_holder.append(errors)
                except Exception as exc:
                    parsed_holder.append([])
                    errors_holder.append([{
                        "row": 0,
                        "field": "file",
                        "message": f"Errore durante la lettura del CSV: {exc}",
                    }])
                finally:
                    progress_queue.put(None)

            yield self._ndjson_line({
                "phase": "uploading",
                "current": 100,
                "total": 100,
                "message": "File ricevuto, avvio validazione…",
            })
            yield self._ndjson_line({
                "phase": "validating",
                "current": 0,
                "total": estimated_rows,
                "message": "Validazione righe CSV…",
            })

            thread = threading.Thread(target=run_parse, daemon=True)
            thread.start()
            while True:
                item = progress_queue.get()
                if item is None:
                    break
                yield self._ndjson_line(item)
            thread.join()

            parsed_rows = parsed_holder[0] if parsed_holder else []
            errors = errors_holder[0] if errors_holder else []
            if errors:
                yield self._ndjson_line({
                    "phase": "failed",
                    "detail": "Validazione CSV non riuscita. Correggi gli errori sotto e riprova.",
                    "errors": errors[:300],
                    "error_count": len(errors),
                    "created_products": 0,
                    "created_variants": 0,
                })
                return

            if not parsed_rows:
                yield self._ndjson_line({
                    "phase": "failed",
                    "detail": "Nessuna riga da importare. Verifica il filtro colonne/valori e il file CSV.",
                    "errors": [{
                        "row": 0,
                        "field": "file",
                        "message": "Nessuna riga valida da importare.",
                    }],
                    "created_products": 0,
                    "created_variants": 0,
                })
                return

            yield self._ndjson_line({
                "phase": "validated",
                "current": len(parsed_rows),
                "total": len(parsed_rows),
                "message": f"{len(parsed_rows)} righe varianti pronte per l'import.",
            })

            try:
                for event in iter_import_parsed_rows(parsed_rows):
                    if event["phase"] == "importing":
                        yield self._ndjson_line(event)
                    elif event["phase"] == "complete":
                        products = event["created_products"]
                        variants = event["created_variants"]
                        yield self._ndjson_line({
                            "phase": "done",
                            "detail": (
                                f"Importati {products} prodott{'o' if products == 1 else 'i'} "
                                f"con {variants} variant{'e' if variants == 1 else 'i'}."
                            ),
                            "errors": [],
                            "created_products": products,
                            "created_variants": variants,
                        })
            except ValueError as exc:
                yield self._ndjson_line({
                    "phase": "failed",
                    "detail": str(exc),
                    "errors": [{"row": 0, "field": "url_immagini", "message": str(exc)}],
                    "created_products": 0,
                    "created_variants": 0,
                })
            except Exception as exc:
                yield self._ndjson_line({
                    "phase": "failed",
                    "detail": f"Import interrotto: {exc}",
                    "errors": [{"row": 0, "field": "file", "message": str(exc)}],
                    "created_products": 0,
                    "created_variants": 0,
                })

        response = StreamingHttpResponse(
            event_stream(),
            content_type="application/x-ndjson; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser], url_path="import_csv")
    def import_csv(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "Carica un file CSV usando il campo file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = (upload.name or "").lower()
        if not name.endswith(".csv"):
            return Response(
                {"detail": "Sono accettati solo file .csv."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        column_value_filter = _parse_column_value_filter(request)
        brand_keys_filter = _parse_brand_keys_filter(request)
        if column_value_filter is not None:
            col_key, value_keys = column_value_filter
            if not col_key:
                return Response(
                    {"detail": "Seleziona una colonna per filtrare l'import."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not value_keys:
                return Response(
                    {"detail": "Seleziona almeno un valore da importare."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            brand_keys_filter = None
        elif brand_keys_filter is not None and not brand_keys_filter:
            return Response(
                {"detail": "Seleziona almeno una marca da importare."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parsed_rows, errors = parse_and_validate_csv(
            upload.read(),
            brand_keys_filter=brand_keys_filter,
            column_value_filter=column_value_filter,
        )
        if errors:
            return Response(
                {
                    "detail": "Validazione CSV non riuscita. Correggi gli errori sotto e riprova.",
                    "errors": errors,
                    "created_products": 0,
                    "created_variants": 0,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_parsed_rows(parsed_rows)
        except ValueError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "errors": [{"row": 0, "field": "url_immagini", "message": str(exc)}],
                    "created_products": 0,
                    "created_variants": 0,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        products = result["created_products"]
        variants = result["created_variants"]
        return Response(
            {
                "detail": (
                    f"Importati {products} prodott{'o' if products == 1 else 'i'} "
                    f"con {variants} variant{'e' if variants == 1 else 'i'}."
                ),
                "errors": [],
                **result,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_mockup(self, request, pk=None):
        product = self.get_object()
        image_file = request.FILES.get("mockup_front")
        if not image_file:
            return Response({"detail": "No mockup image provided."}, status=status.HTTP_400_BAD_REQUEST)

        if product.mockup_front:
            product.mockup_front.delete(save=False)
        product.mockup_front = image_file
        product.save(update_fields=["mockup_front"])
        return Response(AdminProductSerializer(product, context={"request": request}).data)

    @action(detail=True, methods=["delete"])
    def remove_mockup(self, request, pk=None):
        product = self.get_object()
        if product.mockup_front:
            product.mockup_front.delete(save=False)
            product.mockup_front = None
            product.save(update_fields=["mockup_front"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_image(self, request, pk=None):
        product = self.get_object()
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"detail": "No image file provided."}, status=status.HTTP_400_BAD_REQUEST)

        is_primary = request.data.get("is_primary", "false").lower() in ("true", "1", "yes")
        alt_text = request.data.get("alt_text", "")
        sort_order = request.data.get("sort_order")
        sort_order = int(sort_order) if sort_order is not None else None

        product_image = create_product_image(
            product,
            image_file,
            alt_text=alt_text,
            is_primary=is_primary,
            sort_order=sort_order,
        )
        return Response(
            AdminProductImageSerializer(product_image, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], parser_classes=[JSONParser, FormParser, MultiPartParser])
    def add_image_url(self, request, pk=None):
        product = self.get_object()
        image_url = (request.data.get("image_url") or "").strip()
        is_primary = request.data.get("is_primary", False)
        if isinstance(is_primary, str):
            is_primary = is_primary.lower() in ("true", "1", "yes")
        alt_text = request.data.get("alt_text", "")
        sort_order = request.data.get("sort_order")
        sort_order = int(sort_order) if sort_order is not None else None

        product_image, reason = attach_image_from_url(
            product,
            image_url,
            is_primary=is_primary,
            alt_text=alt_text,
            sort_order=sort_order,
        )
        if not product_image:
            return Response(
                {"image_url": [reason]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = AdminProductImageSerializer(product_image, context={"request": request}).data
        if product_image.external_url and not product_image.image:
            data["linked_externally"] = True
        return Response(data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"images/(?P<image_id>[^/.]+)",
    )
    def manage_image(self, request, pk=None, image_id=None):
        product = self.get_object()
        try:
            product_image = product.images.get(pk=image_id)
        except ProductImage.DoesNotExist:
            return Response({"detail": "Image not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            was_primary = product_image.is_primary
            product_image.delete()
            if was_primary:
                next_img = product.images.first()
                if next_img:
                    next_img.is_primary = True
                    next_img.save(update_fields=["is_primary"])
            return Response(status=status.HTTP_204_NO_CONTENT)

        if "is_primary" in request.data and request.data["is_primary"]:
            product.images.update(is_primary=False)
            product_image.is_primary = True

        for field in ("alt_text", "sort_order"):
            if field in request.data:
                setattr(product_image, field, request.data[field])
        product_image.save()
        return Response(
            AdminProductImageSerializer(product_image, context={"request": request}).data
        )


class AdminCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["translations__name", "slug"]
    filterset_fields = ["section", "is_active", "parent"]
    ordering_fields = ["slug", "created_at"]
    ordering = ["slug"]
    pagination_class = None

    def get_queryset(self):
        return Category.objects.select_related("parent").prefetch_related("translations")

    def list(self, request, *args, **kwargs):
        queryset = sort_categories(self.filter_queryset(self.get_queryset()), "it")
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action == "list" and self.request.query_params.get("options") == "true":
            return AdminCategoryOptionSerializer
        return AdminCategorySerializer

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if category.children.exists():
            return Response(
                {"detail": "Cannot delete a category that has subcategories."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if category.products.exists():
            return Response(
                {"detail": "Cannot delete a category that has products assigned."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class AdminBrandViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    serializer_class = AdminBrandSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    filterset_fields = ["is_active"]
    ordering_fields = ["sort_order", "name", "created_at"]
    ordering = ["sort_order", "name"]
    queryset = Brand.objects.all()
    pagination_class = None

    def destroy(self, request, *args, **kwargs):
        brand = self.get_object()
        if Product.objects.filter(brand__iexact=brand.name).exists():
            return Response(
                {"detail": "Cannot delete a brand that is assigned to products. Deactivate it instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class AdminColorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    serializer_class = AdminColorSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    filterset_fields = ["is_active"]
    ordering_fields = ["sort_order", "name", "created_at"]
    ordering = ["sort_order", "name"]
    queryset = Color.objects.all()
    pagination_class = None

    def destroy(self, request, *args, **kwargs):
        color = self.get_object()
        if ProductVariant.objects.filter(color__iexact=color.name).exists():
            return Response(
                {"detail": "Cannot delete a color that is assigned to product variants. Deactivate it instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
