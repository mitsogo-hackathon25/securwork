from django.db.models import F
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Product
from .serializers import CategorySerializer, ProductDetailSerializer, ProductListSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True, parent__isnull=True)
    serializer_class = CategorySerializer
    lookup_field = "slug"
    pagination_class = None

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["lang"] = self.request.query_params.get("lang", "it")
        return ctx

    @action(detail=False, methods=["get"])
    def all(self, request):
        """Flat list of all active categories."""
        lang = request.query_params.get("lang", "it")
        qs = Category.objects.filter(is_active=True)
        serializer = CategorySerializer(qs, many=True, context={"request": request, "lang": lang})
        return Response(serializer.data)


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="categories__slug")
    section = filters.CharFilter(field_name="categories__section")
    brand = filters.CharFilter(field_name="brand", lookup_expr="iexact")
    min_price = filters.NumberFilter(field_name="variants__price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="variants__price", lookup_expr="lte")
    size = filters.CharFilter(field_name="variants__size", lookup_expr="iexact")
    color = filters.CharFilter(field_name="variants__color", lookup_expr="iexact")
    in_stock = filters.BooleanFilter(method="filter_in_stock")
    featured = filters.BooleanFilter(field_name="is_featured")
    new_arrival = filters.BooleanFilter(field_name="is_new_arrival")
    bestseller = filters.BooleanFilter(field_name="is_bestseller")
    on_sale = filters.BooleanFilter(method="filter_on_sale")

    class Meta:
        model = Product
        fields = ["category", "section", "brand", "size", "color", "in_stock", "on_sale"]

    def filter_on_sale(self, queryset, name, value):
        if value:
            return queryset.filter(
                variants__is_active=True,
                variants__sale_price__isnull=False,
                variants__sale_price__lt=F("variants__price"),
            ).distinct()
        return queryset

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(variants__stock_quantity__gt=0, variants__is_active=True).distinct()
        return queryset.filter(variants__stock_quantity=0, variants__is_active=True).distinct()


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True).prefetch_related(
        "images", "variants", "categories", "translations"
    )
    lookup_field = "slug"
    filterset_class = ProductFilter
    search_fields = ["translations__name", "sku"]
    ordering_fields = ["created_at", "translations__name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["lang"] = self.request.query_params.get("lang", "it")
        return ctx

    @action(detail=False, methods=["get"])
    def brands(self, request):
        qs = self.get_queryset().exclude(brand="")
        section = request.query_params.get("section")
        category = request.query_params.get("category")
        if section:
            qs = qs.filter(categories__section=section).distinct()
        if category:
            qs = qs.filter(categories__slug=category).distinct()
        brands = sorted(
            {b for b in qs.values_list("brand", flat=True) if b},
            key=str.casefold,
        )
        return Response(brands)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        qs = self.get_queryset().filter(is_featured=True)[:8]
        serializer = ProductListSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def new_arrivals(self, request):
        qs = self.get_queryset().filter(is_new_arrival=True)[:8]
        serializer = ProductListSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def bestsellers(self, request):
        qs = self.get_queryset().filter(is_bestseller=True)[:8]
        serializer = ProductListSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def related(self, request, slug=None):
        product = self.get_object()
        category_ids = product.categories.values_list("id", flat=True)
        qs = (
            self.get_queryset()
            .filter(categories__in=category_ids)
            .exclude(pk=product.pk)
            .distinct()[:4]
        )
        serializer = ProductListSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)
