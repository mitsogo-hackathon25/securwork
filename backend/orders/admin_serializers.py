from decimal import Decimal

from rest_framework import serializers

from .models import Coupon, Order
from .serializers import OrderItemSerializer


class AdminOrderListSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "email",
            "status",
            "payment_status",
            "payment_method",
            "total",
            "item_count",
            "created_at",
        ]


class AdminOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "email",
            "phone",
            "language",
            "billing_first_name",
            "billing_last_name",
            "billing_company",
            "billing_address",
            "billing_city",
            "billing_postcode",
            "billing_country",
            "billing_vat",
            "shipping_first_name",
            "shipping_last_name",
            "shipping_address",
            "shipping_city",
            "shipping_postcode",
            "shipping_country",
            "subtotal",
            "shipping_cost",
            "tax_amount",
            "discount_amount",
            "total",
            "coupon_code",
            "notes",
            "payment_method",
            "payment_status",
            "paid_at",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AdminOrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["status", "payment_status", "notes"]


class AdminCouponSerializer(serializers.ModelSerializer):
    uses_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "discount_percent",
            "discount_amount",
            "min_order_amount",
            "max_uses",
            "used_count",
            "uses_remaining",
            "is_active",
            "valid_from",
            "valid_until",
        ]
        read_only_fields = ["id", "used_count", "uses_remaining"]

    def get_uses_remaining(self, obj):
        if obj.max_uses is None:
            return None
        return max(obj.max_uses - obj.used_count, 0)

    def validate_code(self, value):
        code = value.strip().upper()
        if not code:
            raise serializers.ValidationError("Coupon code is required.")
        qs = Coupon.objects.filter(code__iexact=code)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A coupon with this code already exists.")
        return code

    def validate(self, attrs):
        percent = attrs.get("discount_percent", getattr(self.instance, "discount_percent", None))
        amount = attrs.get("discount_amount", getattr(self.instance, "discount_amount", None))
        if not percent and not amount:
            raise serializers.ValidationError(
                "Set either a percentage discount or a fixed amount discount."
            )
        if percent is not None and percent <= Decimal("0"):
            raise serializers.ValidationError({"discount_percent": "Must be greater than zero."})
        if amount is not None and amount <= Decimal("0"):
            raise serializers.ValidationError({"discount_amount": "Must be greater than zero."})
        max_uses = attrs.get("max_uses", getattr(self.instance, "max_uses", None))
        if max_uses is not None and max_uses < 1:
            raise serializers.ValidationError({"max_uses": "Must be at least 1."})
        valid_from = attrs.get("valid_from", getattr(self.instance, "valid_from", None))
        valid_until = attrs.get("valid_until", getattr(self.instance, "valid_until", None))
        if valid_from and valid_until and valid_until < valid_from:
            raise serializers.ValidationError({"valid_until": "End date must be after start date."})
        return attrs
