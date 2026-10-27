from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import UserProfile
from orders.models import Order

User = get_user_model()


class AdminUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["phone", "company", "vat_number"]


class AdminUserOrderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "payment_status",
            "total",
            "created_at",
        ]


class AdminUserListSerializer(serializers.ModelSerializer):
    order_count = serializers.IntegerField(read_only=True)
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "is_active",
            "is_staff",
            "date_joined",
            "last_login",
            "order_count",
        ]

    def get_phone(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.phone if profile else ""


class AdminUserDetailSerializer(serializers.ModelSerializer):
    profile = AdminUserProfileSerializer(read_only=True)
    order_count = serializers.IntegerField(read_only=True)
    paid_order_count = serializers.IntegerField(read_only=True)
    total_spent = serializers.SerializerMethodField()
    last_order_at = serializers.DateTimeField(read_only=True, allow_null=True)
    recent_orders = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "date_joined",
            "last_login",
            "profile",
            "order_count",
            "paid_order_count",
            "total_spent",
            "last_order_at",
            "recent_orders",
        ]

    def get_recent_orders(self, obj):
        orders = obj.orders.order_by("-created_at")[:20]
        return AdminUserOrderSummarySerializer(orders, many=True).data

    def get_total_spent(self, obj):
        value = getattr(obj, "total_spent", None)
        if value is None:
            return "0.00"
        return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"
