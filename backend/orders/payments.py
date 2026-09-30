from decimal import Decimal

import stripe
from django.conf import settings
from django.utils import timezone

from .emails import send_order_admin_notification, send_order_confirmation
from .models import Order


def stripe_enabled() -> bool:
    return bool(getattr(settings, "STRIPE_SECRET_KEY", ""))


def get_stripe_client():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def create_stripe_checkout_session(order: Order) -> str:
    """Create Stripe Checkout Session and return redirect URL."""
    client = get_stripe_client()
    line_items = []
    for item in order.items.all():
        line_items.append({
            "price_data": {
                "currency": settings.SECURWORK_CURRENCY.lower(),
                "unit_amount": int(item.unit_price * 100),
                "product_data": {
                    "name": item.product_name,
                    "metadata": {"sku": item.sku},
                },
            },
            "quantity": item.quantity,
        })

    if order.shipping_cost > 0:
        line_items.append({
            "price_data": {
                "currency": settings.SECURWORK_CURRENCY.lower(),
                "unit_amount": int(order.shipping_cost * 100),
                "product_data": {"name": "Spedizione" if order.language == "it" else "Shipping"},
            },
            "quantity": 1,
        })

    if order.tax_amount > 0:
        line_items.append({
            "price_data": {
                "currency": settings.SECURWORK_CURRENCY.lower(),
                "unit_amount": int(order.tax_amount * 100),
                "product_data": {"name": "IVA" if order.language == "it" else "VAT"},
            },
            "quantity": 1,
        })

    success_url = (
        f"{settings.FRONTEND_URL}/order-confirmation/{order.order_number}"
        f"?session_id={{CHECKOUT_SESSION_ID}}"
    )
    cancel_url = f"{settings.FRONTEND_URL}/checkout?cancelled=1"

    session = client.checkout.Session.create(
        mode="payment",
        customer_email=order.email,
        line_items=line_items,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"order_number": order.order_number},
        locale=order.language if order.language in ("it", "en") else "it",
    )

    order.stripe_session_id = session.id
    order.save(update_fields=["stripe_session_id", "updated_at"])
    return session.url


def confirm_order_payment(order: Order, payment_intent_id: str = "") -> Order:
    """Mark order as paid and send notifications."""
    if order.payment_status == Order.PaymentStatus.PAID:
        return order

    order.payment_status = Order.PaymentStatus.PAID
    order.status = Order.Status.PROCESSING
    order.paid_at = timezone.now()
    if payment_intent_id:
        order.stripe_payment_intent_id = payment_intent_id
    order.save()

    send_order_confirmation(order)
    send_order_admin_notification(order)
    return order


def cancel_order(order: Order, restore_stock: bool = True) -> Order:
    """Cancel order and optionally restore inventory."""
    if order.status == Order.Status.CANCELLED:
        return order

    if restore_stock:
        from store.models import ProductVariant
        for item in order.items.select_related("variant"):
            variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
            variant.stock_quantity += item.quantity
            variant.save(update_fields=["stock_quantity"])

    order.status = Order.Status.CANCELLED
    order.payment_status = Order.PaymentStatus.FAILED
    order.save()
    return order


def handle_stripe_webhook(payload: bytes, sig_header: str):
    """Verify and process Stripe webhook event."""
    client = get_stripe_client()
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if webhook_secret:
        event = client.Webhook.construct_event(payload, sig_header, webhook_secret)
    else:
        import json
        event = client.Event.construct_from(json.loads(payload), stripe.api_key)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_number = session.get("metadata", {}).get("order_number")
        if order_number:
            try:
                order = Order.objects.get(order_number=order_number)
                confirm_order_payment(
                    order,
                    payment_intent_id=session.get("payment_intent", ""),
                )
            except Order.DoesNotExist:
                pass

    elif event["type"] == "checkout.session.expired":
        session = event["data"]["object"]
        order_number = session.get("metadata", {}).get("order_number")
        if order_number:
            try:
                order = Order.objects.get(order_number=order_number)
                if order.payment_status != Order.PaymentStatus.PAID:
                    cancel_order(order)
            except Order.DoesNotExist:
                pass

    return event
