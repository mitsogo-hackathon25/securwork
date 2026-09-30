from decimal import Decimal

from django.conf import settings
from rest_framework import serializers

from store.models import ProductVariant
from store.serializers import ProductVariantSerializer

from .models import Cart, CartItem, Coupon, Order, OrderItem


class CartItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.filter(is_active=True),
        source="variant",
        write_only=True,
    )
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "variant", "variant_id", "quantity", "line_total", "product_name"]

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

    def validate(self, data):
        try:
            variant = ProductVariant.objects.get(pk=data["variant_id"], is_active=True)
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError({"variant_id": "Variant not found."})
        if variant.stock_quantity < data["quantity"]:
            raise serializers.ValidationError(
                {"quantity": f"Only {variant.stock_quantity} units available."}
            )
        data["variant"] = variant
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product_name", "sku", "size", "color", "unit_price", "quantity", "line_total"]


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
            "subtotal", "shipping_cost", "tax_amount", "discount_amount", "total",
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
    shipping_first_name = serializers.CharField(max_length=100)
    shipping_last_name = serializers.CharField(max_length=100)
    shipping_address = serializers.CharField(max_length=255)
    shipping_city = serializers.CharField(max_length=100)
    shipping_postcode = serializers.CharField(max_length=20)
    shipping_country = serializers.CharField(max_length=2, default="IT")
    coupon_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    language = serializers.ChoiceField(choices=["it", "en"], default="it")
    payment_method = serializers.ChoiceField(
        choices=["stripe", "bank_transfer"],
        default="stripe",
    )
    accept_terms = serializers.BooleanField()

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions.")
        return value
