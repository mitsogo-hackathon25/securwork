from django.db.models import Count, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .admin_serializers import (
    AdminCategoryOptionSerializer,
    AdminProductImageSerializer,
    AdminProductListSerializer,
    AdminProductSerializer,
)
from .models import Category, Product, ProductImage
from .permissions import IsStaffUser


class AdminProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["translations__name", "sku", "slug"]
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

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_image(self, request, pk=None):
        product = self.get_object()
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"detail": "No image file provided."}, status=status.HTTP_400_BAD_REQUEST)

        is_primary = request.data.get("is_primary", "false").lower() in ("true", "1", "yes")
        alt_text = request.data.get("alt_text", "")
        sort_order = int(request.data.get("sort_order", product.images.count()))

        if is_primary:
            product.images.update(is_primary=False)

        product_image = ProductImage.objects.create(
            product=product,
            image=image_file,
            alt_text=alt_text,
            sort_order=sort_order,
            is_primary=is_primary or not product.images.exists(),
        )
        return Response(
            AdminProductImageSerializer(product_image).data,
            status=status.HTTP_201_CREATED,
        )

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
        return Response(AdminProductImageSerializer(product_image).data)


class AdminCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsStaffUser]
    serializer_class = AdminCategoryOptionSerializer
    queryset = Category.objects.filter(is_active=True).select_related("parent").order_by("sort_order", "slug")
    pagination_class = None
