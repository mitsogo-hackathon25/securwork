from django.utils.text import slugify
from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductVariant

TRANSLATION_FIELDS = (
    "name",
    "short_description",
    "description",
    "meta_title",
    "meta_description",
)


class AdminCategoryOptionSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "slug", "name", "section", "parent"]

    def get_name(self, obj):
        return obj.safe_translation_getter("name", language_code="it", any_language=True) or obj.slug


class AdminProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "sort_order", "is_primary"]

    def get_image(self, obj):
        return obj.image.url if obj.image else None


class AdminProductVariantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id", "sku", "size", "color", "price", "sale_price",
            "stock_quantity", "is_active", "effective_price", "in_stock",
        ]
        extra_kwargs = {
            # Uniqueness is validated in AdminProductSerializer.validate (supports updates).
            "sku": {"validators": []},
        }


class AdminProductListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_stock = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(read_only=True)
    variant_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "sku", "name", "primary_image", "min_price",
            "total_stock", "in_stock", "variant_count",
            "is_active", "is_featured", "is_new_arrival", "is_bestseller",
            "created_at", "updated_at",
        ]

    def get_name(self, obj):
        return obj.safe_translation_getter("name", language_code="it", any_language=True) or obj.slug

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        return img.image.url if img and img.image else None

    def get_total_stock(self, obj):
        return sum(v.stock_quantity for v in obj.variants.all() if v.is_active)


class AdminProductSerializer(serializers.ModelSerializer):
    name_it = serializers.CharField(required=False, allow_blank=True)
    name_en = serializers.CharField(required=False, allow_blank=True)
    short_description_it = serializers.CharField(required=False, allow_blank=True)
    short_description_en = serializers.CharField(required=False, allow_blank=True)
    description_it = serializers.CharField(required=False, allow_blank=True)
    description_en = serializers.CharField(required=False, allow_blank=True)
    meta_title_it = serializers.CharField(required=False, allow_blank=True)
    meta_title_en = serializers.CharField(required=False, allow_blank=True)
    meta_description_it = serializers.CharField(required=False, allow_blank=True)
    meta_description_en = serializers.CharField(required=False, allow_blank=True)

    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        many=True,
        source="categories",
        required=False,
    )
    variants = AdminProductVariantSerializer(many=True)
    images = AdminProductImageSerializer(many=True, read_only=True)
    mockup_front = serializers.SerializerMethodField()
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_stock = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "sku", "brand",
            "name_it", "name_en",
            "short_description_it", "short_description_en",
            "description_it", "description_en",
            "meta_title_it", "meta_title_en",
            "meta_description_it", "meta_description_en",
            "category_ids", "variants", "images",
            "is_active", "is_featured", "is_new_arrival", "is_bestseller",
            "allows_customization", "mockup_front", "customization_fee",
            "min_price", "total_stock", "in_stock",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_total_stock(self, obj):
        return sum(v.stock_quantity for v in obj.variants.all() if v.is_active)

    def get_mockup_front(self, obj):
        if obj.mockup_front:
            request = self.context.get("request")
            url = obj.mockup_front.url
            if request and not url.startswith("http"):
                return request.build_absolute_uri(url)
            return url
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for lang in ("it", "en"):
            instance.set_current_language(lang)
            for field in TRANSLATION_FIELDS:
                data[f"{field}_{lang}"] = getattr(instance, field, "") or ""
        data["category_ids"] = list(instance.categories.values_list("id", flat=True))
        return data

    def validate(self, attrs):
        variants = attrs.get("variants", [])
        if not variants and not self.instance:
            raise serializers.ValidationError({"variants": "At least one variant is required."})
        skus = [v["sku"] for v in variants if v.get("sku")]
        if len(skus) != len(set(skus)):
            raise serializers.ValidationError({"variants": "Variant SKUs must be unique."})
        for variant in variants:
            sku = variant.get("sku")
            if not sku:
                continue
            qs = ProductVariant.objects.filter(sku__iexact=sku)
            variant_id = variant.get("id")
            if variant_id:
                qs = qs.exclude(pk=variant_id)
            if qs.exists():
                raise serializers.ValidationError(
                    {"variants": f"Variant SKU '{sku}' is already used by another product."}
                )
        if not self.instance and not attrs.get("name_it"):
            raise serializers.ValidationError({"name_it": "Italian product name is required."})
        return attrs

    def _save_translations(self, product, validated_data):
        for lang in ("it", "en"):
            product.set_current_language(lang)
            for field in TRANSLATION_FIELDS:
                key = f"{field}_{lang}"
                if key in validated_data:
                    setattr(product, field, validated_data.get(key, ""))
            product.save()

    def _sync_variants(self, product, variants_data):
        keep_ids = []
        for raw in variants_data:
            variant_data = dict(raw)
            if variant_data.get("sale_price") in ("", None):
                variant_data["sale_price"] = None
            variant_id = variant_data.pop("id", None)
            if variant_id:
                variant = ProductVariant.objects.filter(id=variant_id, product=product).first()
                if not variant:
                    raise serializers.ValidationError(
                        {"variants": f"Variant id {variant_id} not found for this product."}
                    )
                for attr, value in variant_data.items():
                    setattr(variant, attr, value)
                variant.save()
                keep_ids.append(variant.id)
            else:
                sku = variant_data.get("sku")
                variant = (
                    ProductVariant.objects.filter(product=product, sku=sku).first()
                    if sku
                    else None
                )
                if variant:
                    for attr, value in variant_data.items():
                        setattr(variant, attr, value)
                    variant.save()
                else:
                    variant = ProductVariant.objects.create(product=product, **variant_data)
                keep_ids.append(variant.id)
        product.variants.exclude(id__in=keep_ids).delete()

    def create(self, validated_data):
        variants_data = validated_data.pop("variants", [])
        categories = validated_data.pop("categories", [])
        translation_keys = [k for k in validated_data if k.endswith("_it") or k.endswith("_en")]
        product_fields = {k: v for k, v in validated_data.items() if k not in translation_keys}

        if not product_fields.get("slug"):
            name = validated_data.get("name_it") or validated_data.get("name_en") or product_fields.get("sku", "product")
            base_slug = slugify(name)[:240] or "product"
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            product_fields["slug"] = slug

        product = Product.objects.create(**product_fields)
        self._save_translations(product, validated_data)
        if categories:
            product.categories.set(categories)
        self._sync_variants(product, variants_data)
        return product

    def update(self, instance, validated_data):
        variants_data = validated_data.pop("variants", None)
        categories = validated_data.pop("categories", None)
        translation_keys = [k for k in validated_data if k.endswith("_it") or k.endswith("_en")]
        product_fields = {k: v for k, v in validated_data.items() if k not in translation_keys}

        for attr, value in product_fields.items():
            setattr(instance, attr, value)
        instance.save()

        self._save_translations(instance, validated_data)
        if categories is not None:
            instance.categories.set(categories)
        if variants_data is not None:
            self._sync_variants(instance, variants_data)
        return instance
