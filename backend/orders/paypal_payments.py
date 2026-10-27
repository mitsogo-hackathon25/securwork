"""PayPal Checkout (Orders API v2) — redirect flow."""

import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal

from django.conf import settings

from .models import Order

logger = logging.getLogger(__name__)


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


def _frontend_base() -> str:
    base = (getattr(settings, "FRONTEND_URL", "") or "").strip().rstrip("/")
    if not base.startswith("http://") and not base.startswith("https://"):
        raise PayPalError(
            "Store checkout URL is not configured (FRONTEND_URL). "
            "Contact support or try bank transfer."
        )
    return base


def _items_subtotal(items: list[dict]) -> Decimal:
    total = Decimal("0.00")
    for item in items:
        unit = Decimal(item["unit_amount"]["value"])
        qty = int(item["quantity"])
        total += unit * qty
    return total.quantize(Decimal("0.01"))


def _build_paypal_items(order: Order, currency: str) -> list[dict]:
    """Line items for PayPal; item totals must match order.subtotal."""
    items: list[dict] = []
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

    subtotal = Decimal(order.subtotal).quantize(Decimal("0.01"))
    if items and _items_subtotal(items) != subtotal:
        items = [{
            "name": f"SecurWork {order.order_number}"[:127],
            "quantity": "1",
            "unit_amount": {"currency_code": currency, "value": _money(subtotal)},
        }]
    return items


def _breakdown_for_order(order: Order, currency: str) -> dict:
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
    if order.payment_fee > 0:
        breakdown["handling"] = {
            "currency_code": currency,
            "value": _money(order.payment_fee),
        }
    return breakdown


def _breakdown_matches_total(order: Order, breakdown: dict) -> bool:
    item_total = Decimal(breakdown["item_total"]["value"])
    shipping = Decimal(breakdown["shipping"]["value"])
    tax = Decimal(breakdown["tax_total"]["value"])
    discount = Decimal("0.00")
    if "discount" in breakdown:
        discount = Decimal(breakdown["discount"]["value"])
    handling = Decimal("0.00")
    if "handling" in breakdown:
        handling = Decimal(breakdown["handling"]["value"])
    expected = (item_total + shipping + tax - discount + handling).quantize(Decimal("0.01"))
    return expected == Decimal(order.total).quantize(Decimal("0.01"))


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
        raise PayPalError(detail or str(e), status_code=e.code) from e
    except urllib.error.URLError as e:
        raise PayPalError(f"Could not reach PayPal: {e.reason}") from e


class PayPalError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

    def issue_codes(self) -> list[str]:
        try:
            payload = json.loads(str(self))
        except json.JSONDecodeError:
            return []
        codes = []
        for detail in payload.get("details", []):
            issue = detail.get("issue")
            if issue:
                codes.append(str(issue))
        return codes

    def user_message(self) -> str:
        raw = str(self).strip()
        try:
            json.loads(raw)
        except json.JSONDecodeError:
            if raw and not raw.lstrip().startswith("<"):
                return raw[:500]

        codes = set(self.issue_codes())
        if "INVALID_REQUEST_URL" in codes or "INVALID_REDIRECT_URL" in codes:
            return (
                "PayPal could not start checkout because the store return URL is invalid. "
                "Please contact support or use bank transfer."
            )
        if "AMOUNT_MISMATCH" in codes or "ITEM_TOTAL_MISMATCH" in codes:
            return (
                "PayPal could not match the order total. Please refresh the cart and try again, "
                "or use another payment method."
            )
        if "PAYEE_ACCOUNT_RESTRICTED" in codes:
            return (
                "PayPal payments are temporarily unavailable because the merchant "
                "account is restricted. Please choose another payment method or try again later."
            )
        if "PAYEE_ACCOUNT_LOCKED_OR_CLOSED" in codes:
            return "PayPal payments are unavailable for this store. Please use another payment method."
        if codes:
            return "PayPal could not start this payment. Please try another payment method."
        return "PayPal payment could not be started. Please try again or use another payment method."


class PayPalVerificationError(Exception):
    """PayPal payment could not be verified against the order."""


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
            token = payload.get("access_token")
            if not token:
                raise PayPalError("PayPal did not return an access token.")
            return token
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise PayPalError(detail or str(e), status_code=e.code) from e
    except urllib.error.URLError as e:
        raise PayPalError(f"Could not reach PayPal: {e.reason}") from e


def _basic_auth(client_id: str, secret: str) -> str:
    import base64

    token = base64.b64encode(f"{client_id}:{secret}".encode()).decode("ascii")
    return token


def _create_paypal_order_payload(order: Order, *, include_redirect: bool) -> dict:
    currency = settings.SECURWORK_CURRENCY
    breakdown = _breakdown_for_order(order, currency)
    items = _build_paypal_items(order, currency)
    amount: dict = {
        "currency_code": currency,
        "value": _money(order.total),
    }
    purchase_unit: dict = {
        "reference_id": order.order_number,
        "description": f"SecurWork {order.order_number}",
        "amount": amount,
    }
    if _breakdown_matches_total(order, breakdown) and _items_subtotal(items) == Decimal(
        order.subtotal
    ).quantize(Decimal("0.01")):
        amount["breakdown"] = breakdown
        purchase_unit["items"] = items
    else:
        logger.warning(
            "PayPal amount breakdown mismatch for order %s; sending total-only amount",
            order.order_number,
        )

    payload: dict = {
        "intent": "CAPTURE",
        "purchase_units": [purchase_unit],
    }
    if include_redirect:
        frontend = _frontend_base()
        payload["application_context"] = {
            "brand_name": "SecurWork",
            "landing_page": "BILLING",
            "user_action": "PAY_NOW",
            "return_url": f"{frontend}/order-confirmation/{order.order_number}",
            "cancel_url": f"{frontend}/checkout?cancelled=1",
        }
    return payload


def _create_paypal_order(order: Order, payload: dict) -> str:
    access_token = get_paypal_access_token()
    result = _paypal_request("POST", "/v2/checkout/orders", access_token, payload)
    paypal_order_id = result.get("id", "")
    if not paypal_order_id:
        raise PayPalError("PayPal did not return an order id.")
    order.paypal_order_id = paypal_order_id
    order.save(update_fields=["paypal_order_id", "updated_at"])
    return paypal_order_id


def create_paypal_order_for_card(order: Order) -> str:
    """Create PayPal order for on-page Card Fields (no redirect)."""
    payload = _create_paypal_order_payload(order, include_redirect=False)
    return _create_paypal_order(order, payload)


def create_paypal_checkout(order: Order) -> str:
    """Create PayPal order and return the approval URL."""
    payload = _create_paypal_order_payload(order, include_redirect=True)
    access_token = get_paypal_access_token()
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


def get_paypal_order(paypal_order_id: str, access_token: str | None = None) -> dict:
    token = access_token or get_paypal_access_token()
    return _paypal_request("GET", f"/v2/checkout/orders/{paypal_order_id}", token)


def _is_already_captured_error(err: PayPalError) -> bool:
    text = str(err)
    if "ORDER_ALREADY_CAPTURED" in text:
        return True
    if err.status_code == 422:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return False
        for detail in payload.get("details", []):
            if detail.get("issue") == "ORDER_ALREADY_CAPTURED":
                return True
    return False


def capture_or_retrieve_paypal_order(paypal_order_id: str) -> dict:
    """Capture payment, or retrieve order details if already captured."""
    access_token = get_paypal_access_token()
    try:
        return _paypal_request(
            "POST",
            f"/v2/checkout/orders/{paypal_order_id}/capture",
            access_token,
            {},
        )
    except PayPalError as e:
        if _is_already_captured_error(e):
            logger.info(
                "PayPal order %s already captured; retrieving order details.",
                paypal_order_id,
            )
            return get_paypal_order(paypal_order_id, access_token)
        raise


def capture_paypal_payment(paypal_order_id: str) -> dict:
    """Backward-compatible capture helper (prefer capture_or_retrieve_paypal_order)."""
    return capture_or_retrieve_paypal_order(paypal_order_id)


def _amounts_match(paypal_value: str | None, order_total: Decimal) -> bool:
    if paypal_value is None:
        return False
    try:
        captured = Decimal(str(paypal_value)).quantize(Decimal("0.01"))
    except Exception:
        return False
    return captured == order_total.quantize(Decimal("0.01"))


def _completed_capture_for_reference(paypal_response: dict, order_number: str) -> dict | None:
    for unit in paypal_response.get("purchase_units", []):
        if unit.get("reference_id") != order_number:
            continue
        for capture in unit.get("payments", {}).get("captures", []):
            if capture.get("status") == "COMPLETED":
                return capture
    return None


def verify_paypal_payment_for_order(order: Order, paypal_order_id: str) -> str:
    """
    Capture (or retrieve) the PayPal order and validate it against the SecurWork order.
    Returns the PayPal capture id on success.
    """
    if order.payment_method not in (Order.PaymentMethod.PAYPAL, Order.PaymentMethod.CARD):
        raise PayPalVerificationError("Order payment method is not PayPal.")
    if not order.paypal_order_id or order.paypal_order_id != paypal_order_id:
        raise PayPalVerificationError("PayPal order id does not match this order.")

    paypal_response = capture_or_retrieve_paypal_order(paypal_order_id)
    response_id = paypal_response.get("id")
    if response_id != paypal_order_id:
        raise PayPalVerificationError("PayPal response order id mismatch.")

    capture = _completed_capture_for_reference(paypal_response, order.order_number)
    if not capture:
        raise PayPalVerificationError("No completed PayPal capture for this order.")

    if capture.get("status") != "COMPLETED":
        raise PayPalVerificationError("PayPal capture is not completed.")

    amount = capture.get("amount") or {}
    currency = amount.get("currency_code")
    if currency != settings.SECURWORK_CURRENCY:
        raise PayPalVerificationError("PayPal capture currency does not match.")

    if not _amounts_match(amount.get("value"), order.total):
        raise PayPalVerificationError("PayPal capture amount does not match order total.")

    capture_id = capture.get("id") or ""
    if not capture_id:
        raise PayPalVerificationError("PayPal capture id missing.")

    return capture_id


def paypal_capture_completed(capture_result: dict) -> bool:
    """Legacy helper — prefer verify_paypal_payment_for_order."""
    status = capture_result.get("status")
    if status == "COMPLETED":
        return True
    for unit in capture_result.get("purchase_units", []):
        for payment in unit.get("payments", {}).get("captures", []):
            if payment.get("status") == "COMPLETED":
                return True
    return False
