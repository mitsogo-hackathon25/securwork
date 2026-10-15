"""PayPal Checkout (Orders API v2) — redirect flow."""

import json
import urllib.error
import urllib.request
from decimal import Decimal

from django.conf import settings

from .models import Order


def paypal_enabled() -> bool:
    return bool(
        getattr(settings, "PAYPAL_CLIENT_ID", "")
        and getattr(settings, "PAYPAL_CLIENT_SECRET", "")
    )


def _paypal_api_base() -> str:
    mode = getattr(settings, "PAYPAL_MODE", "sandbox").lower()
    if mode == "live":
        return "https://api-m.paypal.com"
    return "https://api-m.sandbox.paypal.com"


def _money(value: Decimal | str) -> str:
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"


def _paypal_request(method: str, path: str, access_token: str, payload: dict | None = None) -> dict:
    url = f"{_paypal_api_base()}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise PayPalError(detail or str(e)) from e


class PayPalError(Exception):
    pass


def get_paypal_access_token() -> str:
    url = f"{_paypal_api_base()}/v1/oauth2/token"
    data = b"grant_type=client_credentials"
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": (
                "Basic "
                + _basic_auth(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET)
            ),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return payload["access_token"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise PayPalError(detail or str(e)) from e


def _basic_auth(client_id: str, secret: str) -> str:
    import base64

    token = base64.b64encode(f"{client_id}:{secret}".encode()).decode("ascii")
    return token


def create_paypal_checkout(order: Order) -> str:
    """Create PayPal order and return the approval URL."""
    access_token = get_paypal_access_token()
    currency = settings.SECURWORK_CURRENCY

    items = []
    for item in order.items.all():
        items.append({
            "name": (item.product_name or item.sku)[:127],
            "sku": item.sku[:127],
            "quantity": str(item.quantity),
            "unit_amount": {
                "currency_code": currency,
                "value": _money(item.unit_price),
            },
        })

    breakdown = {
        "item_total": {"currency_code": currency, "value": _money(order.subtotal)},
        "shipping": {"currency_code": currency, "value": _money(order.shipping_cost)},
        "tax_total": {"currency_code": currency, "value": _money(order.tax_amount)},
    }
    if order.discount_amount > 0:
        breakdown["discount"] = {
            "currency_code": currency,
            "value": _money(order.discount_amount),
        }

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": order.order_number,
            "description": f"SecurWork {order.order_number}",
            "amount": {
                "currency_code": currency,
                "value": _money(order.total),
                "breakdown": breakdown,
            },
            "items": items,
        }],
        "application_context": {
            "brand_name": "SecurWork",
            "landing_page": "BILLING",
            "user_action": "PAY_NOW",
            "return_url": (
                f"{settings.FRONTEND_URL}/order-confirmation/{order.order_number}"
            ),
            "cancel_url": f"{settings.FRONTEND_URL}/checkout?cancelled=1",
        },
    }

    result = _paypal_request("POST", "/v2/checkout/orders", access_token, payload)
    paypal_order_id = result.get("id", "")
    if not paypal_order_id:
        raise PayPalError("PayPal did not return an order id.")

    approve_url = ""
    for link in result.get("links", []):
        if link.get("rel") == "approve":
            approve_url = link.get("href", "")
            break
    if not approve_url:
        raise PayPalError("PayPal did not return an approval URL.")

    order.paypal_order_id = paypal_order_id
    order.save(update_fields=["paypal_order_id", "updated_at"])
    return approve_url


def capture_paypal_payment(paypal_order_id: str) -> dict:
    access_token = get_paypal_access_token()
    return _paypal_request(
        "POST",
        f"/v2/checkout/orders/{paypal_order_id}/capture",
        access_token,
        {},
    )


def paypal_capture_completed(capture_result: dict) -> bool:
    status = capture_result.get("status")
    if status == "COMPLETED":
        return True
    for unit in capture_result.get("purchase_units", []):
        for payment in unit.get("payments", {}).get("captures", []):
            if payment.get("status") == "COMPLETED":
                return True
    return False
