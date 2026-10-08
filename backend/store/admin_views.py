from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db.models import Count, Prefetch
from django.http import HttpResponse
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
    build_csv_template,
    export_products_csv,
    import_parsed_rows,
    parse_and_validate_csv,
)
from .models import Brand, Category, Color, Product, ProductImage, ProductVariant
from .permissions import IsStaffUser
from .product_images import attach_image_from_url, create_product_image


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
        if percent_raw in (None, ""):
            return Response(
                {"detail": "Indica una percentuale (es. 10 o -5)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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

        factor = (Decimal("100") + percent) / Decimal("100")
        updated_variants = 0
        for variant in ProductVariant.objects.all().iterator():
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
                f"Prezzi {direction} del {abs(percent)}% su {updated_variants} varianti."
            ),
            "updated_variants": updated_variants,
            "percent": str(percent),
        })

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

        parsed_rows, errors = parse_and_validate_csv(upload.read())
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
    ordering_fields = ["sort_order", "slug", "created_at"]
    ordering = ["section", "sort_order", "slug"]
    pagination_class = None

    def get_queryset(self):
        return Category.objects.select_related("parent").prefetch_related("translations")

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
