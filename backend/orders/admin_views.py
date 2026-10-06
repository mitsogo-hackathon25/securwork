from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from store.permissions import IsStaffUser

from .admin_serializers import (
    AdminCouponSerializer,
    AdminOrderListSerializer,
    AdminOrderSerializer,
    AdminOrderUpdateSerializer,
)
from .models import Coupon, Order


class AdminOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsStaffUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["order_number", "email", "billing_last_name", "shipping_last_name"]
    filterset_fields = ["status", "payment_status", "payment_method"]
    ordering_fields = ["created_at", "total", "order_number"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Order.objects.annotate(item_count=Count("items"))
            .prefetch_related("items__customization")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return AdminOrderListSerializer
        if self.action in ("update", "partial_update"):
            return AdminOrderUpdateSerializer
        return AdminOrderSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        updated = self.get_queryset().get(pk=instance.pk)
        return Response(AdminOrderSerializer(updated).data)


class AdminCouponViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    serializer_class = AdminCouponSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["code"]
    filterset_fields = ["is_active"]
    ordering_fields = ["code", "valid_until", "used_count"]
    ordering = ["-id"]
    queryset = Coupon.objects.all()
