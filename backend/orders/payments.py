import logging
from decimal import Decimal

import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .emails import send_order_admin_notification, send_order_confirmation
from .models import Order

logger = logging.getLogger(__name__)


class StripeVerificationError(Exception):
    """Stripe session could not be verified against the order."""


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


def _expected_stripe_amount_cents(order: Order) -> int:
    return int(order.total.quantize(Decimal("0.01")) * 100)


def stripe_session_matches_order(order: Order, session) -> bool:
    """Validate a Stripe Checkout session object or dict against the order."""
    if isinstance(session, dict):
        payment_status = session.get("payment_status")
        metadata = session.get("metadata") or {}
        session_id = session.get("id")
        amount_total = session.get("amount_total")
        currency = (session.get("currency") or "").upper()
    else:
        payment_status = session.payment_status
        metadata = session.metadata or {}
        session_id = session.id
        amount_total = session.amount_total
        currency = (session.currency or "").upper()

    if payment_status != "paid":
        return False
    if metadata.get("order_number") != order.order_number:
        return False
    if order.stripe_session_id and session_id != order.stripe_session_id:
        return False
    if amount_total is not None and int(amount_total) != _expected_stripe_amount_cents(order):
        return False
    if currency and currency != settings.SECURWORK_CURRENCY:
        return False
    return True


def verify_stripe_checkout_for_order(order: Order, session_id: str) -> Order:
    if order.payment_method != Order.PaymentMethod.STRIPE:
        raise StripeVerificationError("Order payment method is not Stripe.")
    if order.stripe_session_id and session_id != order.stripe_session_id:
        raise StripeVerificationError("Stripe session id does not match this order.")

    client = get_stripe_client()
    session = client.checkout.Session.retrieve(session_id)
    if not stripe_session_matches_order(order, session):
        raise StripeVerificationError("Stripe session failed verification.")

    payment_intent = session.payment_intent or ""
    if hasattr(payment_intent, "id"):
        payment_intent = payment_intent.id
    return confirm_order_payment(order, payment_intent_id=str(payment_intent) if payment_intent else "")


def confirm_order_payment(order: Order, payment_intent_id: str = "") -> Order:
    """Mark order as paid and send notifications (idempotent under concurrency)."""
    order_id = order.pk if isinstance(order, Order) else order
    send_emails = False

    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order_id)
        if locked.payment_status == Order.PaymentStatus.PAID:
            return locked

        locked.payment_status = Order.PaymentStatus.PAID
        locked.status = Order.Status.PROCESSING
        locked.paid_at = timezone.now()
        if payment_intent_id:
            locked.stripe_payment_intent_id = payment_intent_id
        locked.save()
        send_emails = True
        order = locked

    if send_emails:
        send_order_confirmation(order)
        send_order_admin_notification(order)
    return order


def verify_and_confirm_paypal_order(order: Order, paypal_order_id: str) -> Order:
    from .paypal_payments import verify_paypal_payment_for_order

    verify_paypal_payment_for_order(order, paypal_order_id)
    return confirm_order_payment(order)


@transaction.atomic
def cancel_order(order: Order, restore_stock: bool = True) -> Order:
    """Cancel order and optionally restore inventory."""
    locked = Order.objects.select_for_update().get(pk=order.pk)
    if locked.status == Order.Status.CANCELLED:
        return locked
    if locked.payment_status == Order.PaymentStatus.PAID:
        logger.info(
            "Skipping cancellation for paid order %s",
            locked.order_number,
        )
        return locked

    if restore_stock:
        from store.models import ProductVariant
        for item in locked.items.select_related("variant"):
            variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
            variant.stock_quantity += item.quantity
            variant.save(update_fields=["stock_quantity"])

    locked.status = Order.Status.CANCELLED
    locked.payment_status = Order.PaymentStatus.FAILED
    locked.save()
    return locked


def handle_stripe_webhook(payload: bytes, sig_header: str):
    """Verify and process Stripe webhook event."""
    client = get_stripe_client()
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    if webhook_secret:
        event = client.Webhook.construct_event(payload, sig_header, webhook_secret)
    elif settings.DEBUG:
        import json

        event = client.Event.construct_from(json.loads(payload), stripe.api_key)
    else:
        raise stripe.error.SignatureVerificationError(
            "Missing STRIPE_WEBHOOK_SECRET",
            sig_header,
        )

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_number = session.get("metadata", {}).get("order_number")
        if order_number:
            try:
                order = Order.objects.get(order_number=order_number)
                if stripe_session_matches_order(order, session):
                    confirm_order_payment(
                        order,
                        payment_intent_id=session.get("payment_intent", "") or "",
                    )
                else:
                    logger.warning(
                        "Stripe webhook session failed verification for order %s",
                        order_number,
                    )
            except Order.DoesNotExist:
                logger.warning("Stripe webhook: unknown order %s", order_number)

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
