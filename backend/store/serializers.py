from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "slug", "name", "description", "section",
            "parent", "image", "sort_order", "children",
        ]

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def _lang(self):
        return self.context.get("lang", "it")

    def get_name(self, obj):
        return obj.safe_translation_getter("name", language_code=self._lang(), any_language=True)

    def get_description(self, obj):
        return obj.safe_translation_getter("description", language_code=self._lang(), any_language=True)

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True, context=self.context).data


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "sort_order", "is_primary"]

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None


class ProductVariantSerializer(serializers.ModelSerializer):
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id", "sku", "size", "color", "price", "sale_price",
            "effective_price", "stock_quantity", "in_stock", "is_low_stock",
        ]


class ProductListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "name", "short_description", "sku", "brand",
            "primary_image", "min_price", "in_stock",
            "is_featured", "is_new_arrival", "is_bestseller",
        ]

    def _lang(self):
        return self.context.get("lang", "it")

    def get_name(self, obj):
        return obj.safe_translation_getter("name", language_code=self._lang(), any_language=True)

    def get_short_description(self, obj):
        return obj.safe_translation_getter("short_description", language_code=self._lang(), any_language=True)

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        if img:
            return img.image.url
        return None


class ProductDetailSerializer(ProductListSerializer):
    description = serializers.SerializerMethodField()
    meta_title = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    is_variable = serializers.BooleanField(read_only=True)
    mockup_front = serializers.SerializerMethodField()
    customization_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description", "meta_title", "meta_description",
            "images", "variants", "categories", "is_variable",
            "allows_customization", "mockup_front", "customization_fee",
            "created_at",
        ]

    def get_mockup_front(self, obj):
        if obj.mockup_front:
            return obj.mockup_front.url
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        return img.image.url if img and img.image else None

    def get_description(self, obj):
        return obj.safe_translation_getter("description", language_code=self._lang(), any_language=True)

    def get_meta_title(self, obj):
        return obj.safe_translation_getter("meta_title", language_code=self._lang(), any_language=True)

    def get_meta_description(self, obj):
        return obj.safe_translation_getter("meta_description", language_code=self._lang(), any_language=True)
