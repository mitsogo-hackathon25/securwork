import json
import logging
import os
import queue
import threading
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.core.management import call_command
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
    csv_download_bytes,
    export_products_csv,
    csv_upload_filename_ok,
    import_parsed_rows,
    iter_import_parsed_rows,
    normalize_column_key,
    parse_and_validate_csv,
    read_csv_upload_bytes,
    delete_staged_csv,
    load_staged_csv,
    load_staged_parsed_rows,
    import_parsed_rows_chunk,
    group_parsed_product_rows,
    stage_parsed_import_rows,
    scan_csv_brands,
    scan_csv_column_values,
    scan_csv_columns,
    stage_csv_upload,
)
from .category_ordering import sort_categories
from .models import Brand, Category, Color, CsvImportBatch, Product, ProductImage, ProductVariant
from .permissions import IsStaffUser
from .product_images import attach_image_from_url, create_product_image
from .toptex_client import TOPTEX_USAGE_RIGHTS, TopTexAPIError, TopTexClient, TopTexConfigError
from .toptex_import import prepare_toptex_import_staging

logger = logging.getLogger(__name__)

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
_IMPORT_BATCH_MIGRATION_DETAIL = (
    "Il database non è aggiornato: manca la tabella import batch (CsvImportBatch). "
    "Sul server esegui: python manage.py migrate"
)
_IMPORT_BATCH_MIGRATION_CODE = "database_migration_required"

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


def _parse_skip_existing_in_catalog(request) -> bool:
    """When true, existing Codice Padre rows are skipped instead of failing validation."""
    raw = request.data.get("skip_existing")
    if raw is None:
        raw = request.POST.get("skip_existing")
    if raw is None or raw == "":
        return True
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _parse_int_param(request, name: str, default: int) -> int:
    raw = request.data.get(name)
    if raw is None:
        raw = request.POST.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _csv_import_chunk_size(request) -> int:
    configured = getattr(settings, "CSV_IMPORT_CHUNK_SIZE", 20)
    size = _parse_int_param(request, "chunk_size", configured)
    return max(1, min(100, size))


def _import_batch_create_error_response(
    exc: Exception,
    *,
    staging_upload_id: str | None = None,
) -> Response | None:
    """Map missing CsvImportBatch table (migrate not run) to a clear API response."""
    if not isinstance(exc, (OperationalError, DatabaseError)):
        return None
    if staging_upload_id:
        delete_staged_csv(staging_upload_id)
    message = str(exc).lower()
    if (
        "csvimportbatch" in message
        or "no such table" in message
        or "does not exist" in message
    ):
        return Response(
            {
                "detail": _IMPORT_BATCH_MIGRATION_DETAIL,
                "code": _IMPORT_BATCH_MIGRATION_CODE,
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(
        {
            "detail": f"Errore database durante creazione import batch: {exc}",
            "code": "database_error",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


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
        response = HttpResponse(csv_download_bytes(content), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="securwork-products-template.csv"'
        return response

    @action(detail=False, methods=["get"], url_path="export_csv")
    def export_csv(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        product_count = queryset.count()
        variant_count = ProductVariant.objects.filter(product__in=queryset).count()

        if product_count == 0:
            return Response(
                {
                    "detail": (
                        "Nessun prodotto nel catalogo su questo server. "
                        "Usa Import CSV per caricare un listino fornitore, "
                        "oppure verifica che l’admin e l’export puntino allo stesso ambiente "
                        "(locale vs produzione)."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            content = export_products_csv(queryset)
        except Exception:
            logger.exception("Product CSV export failed")
            return Response(
                {"detail": "Esportazione CSV non riuscita. Riprova o contatta il supporto."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        data_lines = [ln for ln in content.splitlines() if ln.strip()]
        if len(data_lines) < 2:
            return Response(
                {
                    "detail": (
                        f"Export vuoto ({product_count} prodotti, {variant_count} varianti in DB). "
                        "Controlla i log del backend: alcuni prodotti potrebbero essere stati "
                        "saltati per errori dati; assicurati che ogni prodotto abbia varianti."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        response = HttpResponse(csv_download_bytes(content), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="securwork-products-export.csv"'
        response["X-Export-Row-Count"] = str(len(data_lines) - 1)
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

    @action(detail=False, methods=["post"], url_path="restore_demo_catalog")
    def restore_demo_catalog(self, request):
        """Recreate DEMO/SW- sample products (e.g. after delete all)."""
        admin_password = os.environ.get("ADMIN_PASSWORD", "SecurWork_Admin_2026!")
        try:
            call_command("seed_data", admin_password=admin_password, verbosity=0)
            call_command("seed_catalog", verbosity=0)
        except Exception:
            logger.exception("restore_demo_catalog failed")
            return Response(
                {"detail": "Impossibile caricare il catalogo demo."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        product_count = Product.objects.count()
        variant_count = ProductVariant.objects.count()
        return Response({
            "detail": (
                f"Catalogo demo ripristinato: {product_count} prodotti, "
                f"{variant_count} varianti. Ora puoi esportare il CSV."
            ),
            "product_count": product_count,
            "variant_count": variant_count,
        })

    def _ndjson_line(self, payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=False) + "\n"

    def _resolve_csv_import_filters(self, request):
        column_value_filter = _parse_column_value_filter(request)
        brand_keys_filter = _parse_brand_keys_filter(request)
        if column_value_filter is not None:
            col_key, value_keys = column_value_filter
            if not col_key:
                return None, Response(
                    {"detail": "Seleziona una colonna per filtrare l'import."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not value_keys:
                return None, Response(
                    {"detail": "Seleziona almeno un valore da importare."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            brand_keys_filter = None
        elif brand_keys_filter is not None and not brand_keys_filter:
            return None, Response(
                {"detail": "Seleziona almeno una marca da importare."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return (column_value_filter, brand_keys_filter), None

    def _iter_csv_import_events(
        self,
        file_bytes: bytes,
        *,
        column_value_filter,
        brand_keys_filter,
        staged_upload_id: str | None = None,
        skip_existing_in_catalog: bool = True,
        import_filename: str = "",
    ):
        estimated_rows = max(1, file_bytes.count(b"\n") - 1)
        import_batch: CsvImportBatch | None = None
        try:
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
                        skip_existing_in_catalog=skip_existing_in_catalog,
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
                try:
                    item = progress_queue.get(timeout=15)
                except queue.Empty:
                    yield self._ndjson_line({
                        "phase": "validating",
                        "message": "Validazione CSV in corso…",
                    })
                    continue
                if item is None:
                    break
                yield self._ndjson_line(item)
            thread.join(timeout=600)
            if thread.is_alive():
                yield self._ndjson_line({
                    "phase": "failed",
                    "detail": "Validazione CSV troppo lenta o interrotta. Riduci il file o usa un filtro colonna.",
                    "errors": [{
                        "row": 0,
                        "field": "file",
                        "message": "Timeout validazione CSV.",
                    }],
                    "created_products": 0,
                    "created_variants": 0,
                })
                return

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

            import_batch = CsvImportBatch.objects.create(
                filename=(import_filename or "")[:255],
                status=CsvImportBatch.Status.IN_PROGRESS,
            )
            batch_id = str(import_batch.id)

            import_queue: queue.Queue = queue.Queue()
            import_thread_error: list[BaseException] = []

            def run_import() -> None:
                try:
                    for event in iter_import_parsed_rows(
                        parsed_rows,
                        import_batch=import_batch,
                        skip_existing_in_catalog=skip_existing_in_catalog,
                    ):
                        import_queue.put(event)
                except BaseException as exc:
                    import_thread_error.append(exc)
                finally:
                    import_queue.put(None)

            yield self._ndjson_line({
                "phase": "importing",
                "current": 0,
                "total": max(1, len({r["product_sku"].lower() for r in parsed_rows})),
                "message": "Avvio import prodotti…",
                "batch_id": batch_id,
            })

            import_thread = threading.Thread(target=run_import, daemon=True)
            import_thread.start()
            import_keepalive = 0
            while True:
                try:
                    event = import_queue.get(timeout=15)
                except queue.Empty:
                    import_keepalive += 1
                    yield self._ndjson_line({
                        "phase": "importing",
                        "message": "Import in corso…",
                        "batch_id": batch_id,
                        "keepalive": import_keepalive,
                    })
                    continue
                if event is None:
                    break

                phase = event.get("phase")
                if phase == "skipped":
                    yield self._ndjson_line({**event, "batch_id": batch_id})
                elif phase == "importing":
                    yield self._ndjson_line({**event, "batch_id": batch_id})
                elif phase == "complete":
                    products = event["created_products"]
                    variants = event["created_variants"]
                    skipped = event.get("skipped_products", 0)
                    import_errors = event.get("import_errors") or []
                    import_batch.created_products = products
                    import_batch.created_variants = variants
                    import_batch.skipped_products = skipped
                    if import_errors:
                        import_batch.status = CsvImportBatch.Status.PARTIAL
                        import_batch.error_detail = import_errors[0].get("message", "")[:2000]
                    else:
                        import_batch.status = CsvImportBatch.Status.COMPLETED
                    import_batch.save(
                        update_fields=[
                            "created_products",
                            "created_variants",
                            "skipped_products",
                            "status",
                            "error_detail",
                        ],
                    )
                    detail_parts = [
                        f"Importati {products} prodott{'o' if products == 1 else 'i'} "
                        f"con {variants} variant{'e' if variants == 1 else 'i'}.",
                    ]
                    if skipped:
                        detail_parts.append(
                            f"Saltati {skipped} già presenti nel catalogo.",
                        )
                    if import_errors:
                        detail_parts.append(
                            f"{len(import_errors)} prodott{'o' if len(import_errors) == 1 else 'i'} "
                            "non importati per errore.",
                        )
                    yield self._ndjson_line({
                        "phase": "done",
                        "detail": " ".join(detail_parts),
                        "errors": import_errors[:50],
                        "error_count": len(import_errors),
                        "created_products": products,
                        "created_variants": variants,
                        "skipped_products": skipped,
                        "batch_id": batch_id,
                        "can_rollback": products > 0,
                        "import_partial": bool(import_errors),
                    })

            import_thread.join(timeout=600)
            if import_thread_error:
                exc = import_thread_error[0]
                if import_batch is not None:
                    import_batch.created_products = import_batch.items.count()
                    if isinstance(exc, ValueError):
                        import_batch.status = CsvImportBatch.Status.FAILED
                    else:
                        import_batch.status = CsvImportBatch.Status.PARTIAL
                    import_batch.error_detail = str(exc)[:2000]
                    import_batch.save(update_fields=["created_products", "status", "error_detail"])
                created_in_batch = import_batch.items.count() if import_batch else 0
                field = "url_immagini" if isinstance(exc, ValueError) else "file"
                yield self._ndjson_line({
                    "phase": "failed",
                    "detail": str(exc) if isinstance(exc, ValueError) else f"Import interrotto: {exc}",
                    "errors": [{"row": 0, "field": field, "message": str(exc)}],
                    "created_products": created_in_batch,
                    "created_variants": import_batch.created_variants if import_batch else 0,
                    "batch_id": batch_id,
                    "can_rollback": created_in_batch > 0,
                })
            elif import_thread.is_alive():
                if import_batch is not None:
                    import_batch.created_products = import_batch.items.count()
                    import_batch.status = CsvImportBatch.Status.PARTIAL
                    import_batch.error_detail = "Timeout import CSV."
                    import_batch.save(update_fields=["created_products", "status", "error_detail"])
                created_in_batch = import_batch.items.count() if import_batch else 0
                yield self._ndjson_line({
                    "phase": "failed",
                    "detail": "Import troppo lento o interrotto. Usa un filtro colonna o riprova.",
                    "errors": [{
                        "row": 0,
                        "field": "file",
                        "message": "Timeout import CSV.",
                    }],
                    "created_products": created_in_batch,
                    "created_variants": 0,
                    "batch_id": batch_id,
                    "can_rollback": created_in_batch > 0,
                })
        finally:
            if staged_upload_id:
                delete_staged_csv(staged_upload_id)

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="import_csv_stage",
    )
    def import_csv_stage(self, request):
        """Upload CSV once; returns upload_id for import_csv_stream (shorter second request)."""
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "Carica un file CSV usando il campo file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = (upload.name or "").lower()
        if not csv_upload_filename_ok(name):
            return Response(
                {"detail": "Sono accettati file .csv, .txt o .tsv (listino esportato da Excel)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        file_bytes = read_csv_upload_bytes(upload.read(), upload.name or "")
        upload_id, estimated_rows = stage_csv_upload(file_bytes)
        return Response({"upload_id": upload_id, "estimated_rows": estimated_rows})

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
        url_path="import_csv_prepare",
    )
    def import_csv_prepare(self, request):
        """Validate staged CSV once; store parsed rows for chunked import."""
        try:
            return self._import_csv_prepare_impl(request)
        except Exception as exc:
            logger.exception("import_csv_prepare failed")
            return Response(
                {"detail": f"Errore preparazione import: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _import_csv_prepare_impl(self, request):
        upload_id = (request.data.get("upload_id") or request.POST.get("upload_id") or "").strip()
        file_bytes = load_staged_csv(upload_id)
        if file_bytes is None:
            return Response(
                {
                    "detail": (
                        "Upload CSV non trovato o scaduto. "
                        "Riprova: seleziona di nuovo il file e avvia l'import."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        filters, error_response = self._resolve_csv_import_filters(request)
        if error_response is not None:
            return error_response
        column_value_filter, brand_keys_filter = filters
        skip_existing = _parse_skip_existing_in_catalog(request)
        filename = (
            request.data.get("filename")
            or request.POST.get("filename")
            or ""
        ).strip()

        parsed_rows, errors = parse_and_validate_csv(
            file_bytes,
            brand_keys_filter=brand_keys_filter,
            column_value_filter=column_value_filter,
            skip_existing_in_catalog=skip_existing,
        )
        if errors:
            return Response(
                {
                    "detail": "Validazione CSV non riuscita. Correggi gli errori sotto e riprova.",
                    "errors": errors[:300],
                    "error_count": len(errors),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not parsed_rows:
            return Response(
                {
                    "detail": "Nessuna riga da importare. Verifica filtri e file CSV.",
                    "errors": [{
                        "row": 0,
                        "field": "file",
                        "message": "Nessuna riga valida da importare.",
                    }],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            stage_parsed_import_rows(upload_id, parsed_rows)
        except (OSError, TypeError, ValueError) as exc:
            logger.exception("Could not stage parsed CSV rows")
            return Response(
                {"detail": f"Impossibile preparare l'import: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        total_products = len(group_parsed_product_rows(parsed_rows))
        try:
            import_batch = CsvImportBatch.objects.create(
                filename=(filename or "")[:255],
                staging_upload_id=upload_id,
                status=CsvImportBatch.Status.IN_PROGRESS,
            )
        except (OperationalError, DatabaseError) as exc:
            logger.exception("import_csv_prepare batch create failed")
            db_response = _import_batch_create_error_response(exc, staging_upload_id=upload_id)
            if db_response is not None:
                return db_response
            raise
        chunk_size = _csv_import_chunk_size(request)

        return Response({
            "upload_id": upload_id,
            "batch_id": str(import_batch.id),
            "total_products": total_products,
            "variant_rows": len(parsed_rows),
            "chunk_size": chunk_size,
            "detail": (
                f"Pronti {total_products} prodotti ({len(parsed_rows)} righe varianti). "
                f"Import a blocchi da {chunk_size}."
            ),
        })

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[JSONParser],
        url_path="toptex_connection_test",
    )
    def toptex_connection_test(self, request):
        """Quick TopTex auth + one catalog page (diagnose 500 / config issues)."""
        try:
            client = TopTexClient()
            client.ensure_configured()
            client.authenticate()
            data = client.get(
                "/v3/products/all",
                {
                    "usage_right": "b2b_b2c",
                    "lang": getattr(settings, "TOPTEX_LANG", "it") or "it",
                    "display_prices": "1",
                },
            )
            from .toptex_client import extract_toptex_list_payload, _catalog_total_pages

            items = extract_toptex_list_payload(data)
            return Response({
                "detail": "Connessione TopTex OK.",
                "catalog_items_page1": len(items),
                "total_pages": _catalog_total_pages(data),
                "response_keys": sorted(data.keys())[:30],
            })
        except TopTexConfigError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except TopTexAPIError as exc:
            code = status.HTTP_502_BAD_GATEWAY
            if exc.status and 400 <= exc.status < 500:
                code = status.HTTP_400_BAD_REQUEST
            return Response({"detail": str(exc)}, status=code)
        except Exception as exc:
            logger.exception("toptex_connection_test failed")
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[JSONParser, FormParser],
        url_path="toptex_sync_prepare",
    )
    def toptex_sync_prepare(self, request):
        """
        Fetch TopTex catalog for all configured usage_right values, stage rows, start import batch.
        """
        try:
            return self._toptex_sync_prepare_impl(request)
        except TopTexConfigError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except TopTexAPIError as exc:
            code = status.HTTP_502_BAD_GATEWAY
            if exc.status and 400 <= exc.status < 500:
                code = status.HTTP_400_BAD_REQUEST
            return Response({"detail": str(exc)}, status=code)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("toptex_sync_prepare failed")
            return Response(
                {"detail": f"Errore sincronizzazione TopTex: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _toptex_sync_prepare_impl(self, request):
        sync_id, parsed_rows, usage_stats = prepare_toptex_import_staging()
        total_products = len(group_parsed_product_rows(parsed_rows))
        try:
            import_batch = CsvImportBatch.objects.create(
                filename="TopTex API",
                staging_upload_id=sync_id,
                status=CsvImportBatch.Status.IN_PROGRESS,
            )
        except (OperationalError, DatabaseError) as exc:
            logger.exception("toptex_sync_prepare batch create failed")
            db_response = _import_batch_create_error_response(exc, staging_upload_id=sync_id)
            if db_response is not None:
                return db_response
            raise
        chunk_size = _csv_import_chunk_size(request)
        rights_summary = ", ".join(
            f"{right}={usage_stats.get(right, 0)}"
            for right in TOPTEX_USAGE_RIGHTS
        )
        return Response({
            "upload_id": sync_id,
            "batch_id": str(import_batch.id),
            "total_products": total_products,
            "variant_rows": len(parsed_rows),
            "chunk_size": chunk_size,
            "usage_right_stats": usage_stats,
            "detail": (
                f"TopTex: {total_products} prodotti ({len(parsed_rows)} varianti) "
                f"catalogo ({rights_summary}). "
                f"Stock via API inventory durante import a blocchi. "
                f"Import a blocchi da {chunk_size}."
            ),
        })

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
        url_path="import_csv_chunk",
    )
    def import_csv_chunk(self, request):
        """Import the next slice of prepared product groups (short HTTP request)."""
        try:
            return self._import_csv_chunk_impl(request)
        except Exception as exc:
            logger.exception("import_csv_chunk failed")
            return Response(
                {"detail": f"Errore import blocco: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _import_csv_chunk_impl(self, request):
        upload_id = (request.data.get("upload_id") or request.POST.get("upload_id") or "").strip()
        batch_id = (request.data.get("batch_id") or request.POST.get("batch_id") or "").strip()
        offset = _parse_int_param(request, "offset", 0)
        chunk_size = _csv_import_chunk_size(request)
        skip_existing = _parse_skip_existing_in_catalog(request)

        if not upload_id or not batch_id:
            return Response(
                {"detail": "Mancano upload_id o batch_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        import_batch = CsvImportBatch.objects.filter(pk=batch_id).first()
        if import_batch is None:
            return Response(
                {"detail": "Import batch non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if import_batch.staging_upload_id != upload_id:
            return Response(
                {"detail": "batch_id non corrisponde a questo upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if import_batch.status == CsvImportBatch.Status.ROLLED_BACK:
            return Response(
                {"detail": "Questo import è stato annullato."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parsed_rows = load_staged_parsed_rows(upload_id)
        if parsed_rows is None:
            return Response(
                {
                    "detail": (
                        "Dati import non trovati o scaduti. "
                        "Ripeti preparazione (seleziona di nuovo il file)."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        chunk_result = import_parsed_rows_chunk(
            parsed_rows,
            offset,
            chunk_size,
            import_batch=import_batch,
            skip_existing_in_catalog=skip_existing,
        )

        import_batch.created_products += chunk_result["chunk_created_products"]
        import_batch.created_variants += chunk_result["chunk_created_variants"]
        import_batch.skipped_products += chunk_result["chunk_skipped_products"]
        chunk_errors = chunk_result.get("import_errors") or []
        if chunk_errors:
            import_batch.error_detail = chunk_errors[0].get("message", "")[:2000]

        done = chunk_result["done"]
        if done:
            if chunk_errors or import_batch.error_detail:
                import_batch.status = CsvImportBatch.Status.PARTIAL
            else:
                import_batch.status = CsvImportBatch.Status.COMPLETED
            delete_staged_csv(upload_id)

        import_batch.save()

        products = import_batch.created_products
        variants = import_batch.created_variants
        skipped = import_batch.skipped_products
        detail_parts = []
        if done:
            detail_parts.append(
                f"Importati {products} prodott{'o' if products == 1 else 'i'} "
                f"con {variants} variant{'e' if variants == 1 else 'i'}.",
            )
            if skipped:
                detail_parts.append(f"Saltati {skipped} già in catalogo.")
            if chunk_errors:
                detail_parts.append(
                    f"{len(chunk_errors)} errori in questo blocco.",
                )
        else:
            detail_parts.append(
                f"Blocco completato: {chunk_result['next_offset']} / "
                f"{chunk_result['total_products']} prodotti.",
            )

        return Response({
            "upload_id": upload_id,
            "batch_id": str(import_batch.id),
            "offset": chunk_result["offset"],
            "next_offset": chunk_result["next_offset"],
            "done": done,
            "total_products": chunk_result["total_products"],
            "chunk_created_products": chunk_result["chunk_created_products"],
            "chunk_skipped_products": chunk_result["chunk_skipped_products"],
            "chunk_created_variants": chunk_result["chunk_created_variants"],
            "created_products": products,
            "created_variants": variants,
            "skipped_products": skipped,
            "errors": chunk_errors,
            "can_rollback": products > 0,
            "import_partial": bool(chunk_errors),
            "detail": " ".join(detail_parts),
        })

    @action(detail=False, methods=["post"], url_path="rollback_import_batch")
    def rollback_import_batch(self, request):
        """Delete all products created in a CSV import batch (undo partial import)."""
        batch_id = (request.data.get("batch_id") or request.POST.get("batch_id") or "").strip()
        if not batch_id:
            return Response(
                {"detail": "Manca batch_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        batch = CsvImportBatch.objects.filter(pk=batch_id).first()
        if batch is None:
            return Response(
                {"detail": "Import batch non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if batch.status == CsvImportBatch.Status.ROLLED_BACK:
            return Response({
                "detail": "Questo import è già stato annullato.",
                "deleted": [],
                "blocked": [],
                "batch_id": str(batch.id),
            })

        product_ids = list(batch.items.values_list("product_id", flat=True))
        if not product_ids:
            batch.status = CsvImportBatch.Status.ROLLED_BACK
            batch.save(update_fields=["status"])
            return Response({
                "detail": "Nessun prodotto da rimuovere per questo import.",
                "deleted": [],
                "blocked": [],
                "batch_id": str(batch.id),
            })

        products = Product.objects.filter(pk__in=product_ids)
        deleted_ids, blocked = _delete_catalog_products(products)
        batch.status = CsvImportBatch.Status.ROLLED_BACK
        batch.save(update_fields=["status"])

        if blocked and not deleted_ids:
            detail = (
                f"Nessun prodotto rimosso: {len(blocked)} collegati a ordini e non eliminabili."
            )
        elif blocked:
            detail = (
                f"Rimossi {len(deleted_ids)} prodotti da questo import. "
                f"{len(blocked)} non eliminabili (ordini collegati)."
            )
        else:
            detail = (
                f"Annullato import: eliminati {len(deleted_ids)} "
                f"prodott{'o' if len(deleted_ids) == 1 else 'i'} aggiunti in questo batch."
            )

        return Response({
            "detail": detail,
            "deleted": deleted_ids,
            "blocked": blocked,
            "batch_id": str(batch.id),
        })

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
        if not csv_upload_filename_ok(name):
            return Response(
                {"detail": "Sono accettati file .csv, .txt o .tsv (listino esportato da Excel)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        brands, errors = scan_csv_brands(
            read_csv_upload_bytes(upload.read(), upload.name or ""),
        )
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
            content_type = (request.content_type or "").lower()
            if "application/json" in content_type:
                detail = (
                    "Il file non è stato caricato (richiesta senza allegato). "
                    "Aggiorna la pagina con Ctrl+Shift+R e riprova l'import."
                )
            else:
                detail = "Carica un file CSV usando il campo file."
            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = (upload.name or "").lower()
        if not csv_upload_filename_ok(name):
            return Response(
                {"detail": "Sono accettati file .csv, .txt o .tsv (listino esportato da Excel)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        columns, errors = scan_csv_columns(
            read_csv_upload_bytes(upload.read(), upload.name or ""),
        )
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
        if not csv_upload_filename_ok(name):
            return Response(
                {"detail": "Sono accettati file .csv, .txt o .tsv (listino esportato da Excel)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        values, errors = scan_csv_column_values(
            read_csv_upload_bytes(upload.read(), upload.name or ""),
            str(column),
        )
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
        upload_id = (request.data.get("upload_id") or request.POST.get("upload_id") or "").strip()
        staged_upload_id: str | None = None
        file_bytes: bytes | None = None

        if upload_id:
            file_bytes = load_staged_csv(upload_id)
            if file_bytes is None:
                return Response(
                    {
                        "detail": (
                            "Upload CSV non trovato o scaduto. "
                            "Riprova: seleziona di nuovo il file e avvia l'import."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            staged_upload_id = upload_id
        else:
            upload = request.FILES.get("file")
            if not upload:
                return Response(
                    {"detail": "Carica un file CSV o invia upload_id dopo import_csv_stage."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            name = (upload.name or "").lower()
            if not csv_upload_filename_ok(name):
                return Response(
                    {"detail": "Sono accettati file .csv, .txt o .tsv (listino esportato da Excel)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            file_bytes = read_csv_upload_bytes(upload.read(), upload.name or "")

        filters, error_response = self._resolve_csv_import_filters(request)
        if error_response is not None:
            if staged_upload_id:
                delete_staged_csv(staged_upload_id)
            return error_response
        column_value_filter, brand_keys_filter = filters
        skip_existing = _parse_skip_existing_in_catalog(request)
        filename = (
            request.data.get("filename")
            or request.POST.get("filename")
            or ""
        ).strip()

        response = StreamingHttpResponse(
            self._iter_csv_import_events(
                file_bytes,
                column_value_filter=column_value_filter,
                brand_keys_filter=brand_keys_filter,
                staged_upload_id=staged_upload_id,
                skip_existing_in_catalog=skip_existing,
                import_filename=filename,
            ),
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
        if not csv_upload_filename_ok(name):
            return Response(
                {"detail": "Sono accettati file .csv, .txt o .tsv (listino esportato da Excel)."},
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
            read_csv_upload_bytes(upload.read(), upload.name or ""),
            brand_keys_filter=brand_keys_filter,
            column_value_filter=column_value_filter,
            skip_existing_in_catalog=_parse_skip_existing_in_catalog(request),
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
