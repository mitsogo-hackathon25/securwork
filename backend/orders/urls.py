from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CartItemView,
    CartView,
    CheckoutView,
    OrderVerifyView,
    OrderViewSet,
    PaymentConfigView,
    stripe_webhook_view,
)

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/<int:item_id>/", CartItemView.as_view(), name="cart-item"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("payments/config/", PaymentConfigView.as_view(), name="payment-config"),
    path("payments/webhook/stripe/", stripe_webhook_view, name="stripe-webhook"),
    path("orders/<str:order_number>/verify/", OrderVerifyView.as_view(), name="order-verify"),
    path("", include(router.urls)),
]
