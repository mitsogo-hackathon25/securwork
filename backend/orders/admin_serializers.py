from rest_framework import serializers

from .models import Order
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
