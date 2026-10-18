from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
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

    @action(detail=False, methods=["get"], url_path="monthly-sales")
    def monthly_sales(self, request):
        """Paid revenue and order counts grouped by calendar month for a given year."""
        raw_year = request.query_params.get("year")
        now = timezone.now()
        try:
            year = int(raw_year) if raw_year is not None else now.year
        except (TypeError, ValueError):
            return Response({"detail": "Invalid year."}, status=400)
        if year < 2000 or year > now.year + 1:
            return Response({"detail": "Year out of range."}, status=400)

        paid_status = Order.PaymentStatus.PAID
        rows = (
            Order.objects.filter(created_at__year=year)
            .exclude(status=Order.Status.CANCELLED)
            .annotate(period=TruncMonth("created_at"))
            .values("period")
            .annotate(
                order_count=Count("id"),
                paid_order_count=Count("id", filter=Q(payment_status=paid_status)),
                revenue=Sum("total", filter=Q(payment_status=paid_status)),
            )
        )
        by_month: dict[int, dict] = {}
        for row in rows:
            if not row["period"]:
                continue
            month = row["period"].month
            revenue = row["revenue"] or Decimal("0.00")
            by_month[month] = {
                "month": month,
                "order_count": row["order_count"],
                "paid_order_count": row["paid_order_count"],
                "revenue": str(revenue.quantize(Decimal("0.01"))),
            }

        months = []
        total_revenue = Decimal("0.00")
        total_orders = 0
        total_paid_orders = 0
        for month in range(1, 13):
            entry = by_month.get(month, {
                "month": month,
                "order_count": 0,
                "paid_order_count": 0,
                "revenue": "0.00",
            })
            months.append(entry)
            total_revenue += Decimal(entry["revenue"])
            total_orders += entry["order_count"]
            total_paid_orders += entry["paid_order_count"]

        return Response({
            "year": year,
            "currency": settings.SECURWORK_CURRENCY,
            "months": months,
            "summary": {
                "order_count": total_orders,
                "paid_order_count": total_paid_orders,
                "revenue": str(total_revenue.quantize(Decimal("0.01"))),
            },
        })


class AdminCouponViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    serializer_class = AdminCouponSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["code"]
    filterset_fields = ["is_active"]
    ordering_fields = ["code", "valid_until", "used_count"]
    ordering = ["-id"]
    queryset = Coupon.objects.all()
