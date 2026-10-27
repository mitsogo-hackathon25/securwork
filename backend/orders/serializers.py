from decimal import Decimal

from django.conf import settings
from rest_framework import serializers

from store.models import ProductVariant
from store.serializers import ProductVariantSerializer

from .models import Cart, CartItem, Coupon, LineItemCustomization, Order, OrderItem, PickupLocation


class LineItemCustomizationSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()

    class Meta:
        model = LineItemCustomization
        fields = ["id", "logo", "preview", "method", "design_data", "created_at"]

    def get_logo(self, obj):
        return obj.logo.url if obj.logo else None

    def get_preview(self, obj):
        return obj.preview.url if obj.preview else None


class CartItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.filter(is_active=True),
        source="variant",
        write_only=True,
    )
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_name = serializers.SerializerMethodField()
    customization = LineItemCustomizationSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id", "variant", "variant_id", "quantity", "unit_price",
            "line_total", "product_name", "customization",
        ]

    def get_product_name(self, obj):
        lang = self.context.get("lang", "it")
        return obj.variant.product.safe_translation_getter("name", language_code=lang, any_language=True)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total", "item_count", "updated_at"]

    def get_item_count(self, obj):
        return sum(item.quantity for item in obj.items.all())


class AddToCartSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    customization_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        try:
            variant = ProductVariant.objects.select_related("product").get(
                pk=data["variant_id"], is_active=True
            )
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError({"variant_id": "Variant not found."})
        if variant.stock_quantity < data["quantity"]:
            raise serializers.ValidationError(
                {"quantity": f"Only {variant.stock_quantity} units available."}
            )
        customization_id = data.get("customization_id")
        if customization_id:
            try:
                customization = LineItemCustomization.objects.get(pk=customization_id)
            except LineItemCustomization.DoesNotExist:
                raise serializers.ValidationError({"customization_id": "Customization not found."})
            from store.customization import product_has_customization, product_method_enabled

            if not product_has_customization(variant.product):
                raise serializers.ValidationError({"customization_id": "Product is not customizable."})
            method = customization.method or "embroidery_chest"
            if not product_method_enabled(variant.product, method):
                raise serializers.ValidationError(
                    {"customization_id": "Selected customization method is not available for this product."}
                )
            data["customization"] = customization
        data["variant"] = variant
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    customization = LineItemCustomizationSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "product_name", "sku", "size", "color", "unit_price", "quantity",
            "line_total", "customization",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "order_number", "status", "email", "phone", "language",
            "billing_first_name", "billing_last_name", "billing_company",
            "billing_address", "billing_city", "billing_postcode", "billing_country", "billing_vat",
            "shipping_first_name", "shipping_last_name",
            "shipping_address", "shipping_city", "shipping_postcode", "shipping_country",
            "subtotal", "shipping_cost", "tax_amount", "discount_amount", "payment_fee", "total",
            "fulfillment_type", "pickup_location_name",
            "coupon_code", "payment_method", "payment_status", "paid_at",
            "items", "created_at",
        ]
        read_only_fields = fields


class CheckoutSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    billing_first_name = serializers.CharField(max_length=100)
    billing_last_name = serializers.CharField(max_length=100)
    billing_company = serializers.CharField(max_length=200, required=False, allow_blank=True)
    billing_address = serializers.CharField(max_length=255)
    billing_city = serializers.CharField(max_length=100)
    billing_postcode = serializers.CharField(max_length=20)
    billing_country = serializers.CharField(max_length=2, default="IT")
    billing_vat = serializers.CharField(max_length=50, required=False, allow_blank=True)
    shipping_first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    shipping_last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    shipping_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    shipping_city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    shipping_postcode = serializers.CharField(max_length=20, required=False, allow_blank=True)
    shipping_country = serializers.CharField(max_length=2, default="IT", required=False, allow_blank=True)
    fulfillment_type = serializers.ChoiceField(
        choices=["delivery", "pickup"],
        default="delivery",
    )
    pickup_location_id = serializers.IntegerField(required=False, allow_null=True)
    coupon_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    language = serializers.ChoiceField(choices=["it", "en"], default="it")
    payment_method = serializers.ChoiceField(
        choices=["paypal", "bank_transfer", "card"],
        default="paypal",
    )
    accept_terms = serializers.BooleanField()

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions.")
        return value

    def validate(self, data):
        from .payment_methods import normalize_payment_method

        data["payment_method"] = normalize_payment_method(data.get("payment_method", "paypal"))

        fulfillment = data.get("fulfillment_type", "delivery")
        if fulfillment == "pickup":
            location_id = data.get("pickup_location_id")
            if not location_id:
                raise serializers.ValidationError({
                    "pickup_location_id": "Select a pickup location.",
                })
            try:
                location = PickupLocation.objects.get(pk=location_id, is_active=True)
            except PickupLocation.DoesNotExist:
                raise serializers.ValidationError({
                    "pickup_location_id": "Pickup location is not available.",
                })
            data["_pickup_location"] = location
            data["shipping_first_name"] = data["billing_first_name"]
            data["shipping_last_name"] = data["billing_last_name"]
            data["shipping_address"] = location.address
            data["shipping_city"] = location.city
            data["shipping_postcode"] = location.postcode
            data["shipping_country"] = location.country or "IT"
            return data

        required_shipping = [
            "shipping_first_name",
            "shipping_last_name",
            "shipping_address",
            "shipping_city",
            "shipping_postcode",
        ]
        errors = {}
        for field in required_shipping:
            if not (data.get(field) or "").strip():
                errors[field] = "This field is required for delivery."
        if errors:
            raise serializers.ValidationError(errors)
        if not data.get("shipping_country"):
            data["shipping_country"] = "IT"
        return data
