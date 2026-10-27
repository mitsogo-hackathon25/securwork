"""Checkout payment method normalization."""

from .models import Order


def normalize_payment_method(method: str) -> str:
    """Map API aliases to stored Order.PaymentMethod values."""
    if method == "card":
        return Order.PaymentMethod.CARD
    if method in Order.PaymentMethod.values:
        return method
    return Order.PaymentMethod.PAYPAL
