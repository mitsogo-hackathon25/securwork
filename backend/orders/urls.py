from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .admin_views import AdminCouponViewSet, AdminOrderViewSet, AdminPickupLocationViewSet
from .pickup_views import PickupLocationListView
from .customization_views import CustomizationCreateView
from .views import (
    CartItemView,
    CartView,
    CheckoutQuoteView,
    CheckoutView,
    OrderVerifyView,
    OrderViewSet,
    PaymentConfigView,
    stripe_webhook_view,
)

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")

admin_router = DefaultRouter()
admin_router.register("orders", AdminOrderViewSet, basename="admin-order")
admin_router.register("coupons", AdminCouponViewSet, basename="admin-coupon")
admin_router.register("pickup-locations", AdminPickupLocationViewSet, basename="admin-pickup-location")

urlpatterns = [
    path("customizations/", CustomizationCreateView.as_view(), name="customization-create"),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/<int:item_id>/", CartItemView.as_view(), name="cart-item"),
    path("pickup-locations/", PickupLocationListView.as_view(), name="pickup-locations"),
    path("checkout/quote/", CheckoutQuoteView.as_view(), name="checkout-quote"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("payments/config/", PaymentConfigView.as_view(), name="payment-config"),
    path("payments/webhook/stripe/", stripe_webhook_view, name="stripe-webhook"),
    path("orders/<str:order_number>/verify/", OrderVerifyView.as_view(), name="order-verify"),
    path("admin/", include(admin_router.urls)),
    path("", include(router.urls)),
]
