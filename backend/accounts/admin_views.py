from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from store.permissions import IsStaffUser

from .admin_serializers import AdminUserDetailSerializer, AdminUserListSerializer
from orders.models import Order

User = get_user_model()


class AdminUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsStaffUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["email", "username", "first_name", "last_name", "profile__phone"]
    filterset_fields = ["is_active", "is_staff"]
    ordering_fields = ["date_joined", "last_login", "email", "username"]
    ordering = ["-date_joined"]

    def get_queryset(self):
        paid = Order.PaymentStatus.PAID
        qs = User.objects.select_related("profile").annotate(
            order_count=Count("orders", distinct=True),
        )
        if self.action == "retrieve":
            qs = qs.annotate(
                paid_order_count=Count(
                    "orders",
                    filter=Q(orders__payment_status=paid),
                    distinct=True,
                ),
                total_spent=Coalesce(
                    Sum(
                        "orders__total",
                        filter=Q(orders__payment_status=paid),
                    ),
                    Decimal("0.00"),
                ),
                last_order_at=Max("orders__created_at"),
            ).prefetch_related(
                "orders",
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return AdminUserListSerializer
        return AdminUserDetailSerializer
