import json
import threading
from decimal import Decimal
from unittest.mock import MagicMock, patch

import stripe
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from orders.models import Order, OrderItem
from orders.payments import (
    cancel_order,
    confirm_order_payment,
    handle_stripe_webhook,
    stripe_session_matches_order,
    verify_stripe_checkout_for_order,
)
from orders.paypal_payments import (
    PayPalError,
    PayPalVerificationError,
    verify_paypal_payment_for_order,
)
from store.models import Product, ProductVariant


def _make_product_variant(stock: int = 20) -> ProductVariant:
    product = Product.objects.create(slug="test-product", sku="PROD-BASE")
    product.set_current_language("it")
    product.name = "Test Product"
    product.save()
    return ProductVariant.objects.create(
        product=product,
        sku="SKU-TEST-1",
        price=Decimal("50.00"),
        stock_quantity=stock,
    )


def _make_order(
    *,
    payment_method=Order.PaymentMethod.PAYPAL,
    total=Decimal("50.00"),
    paypal_order_id="PAYPAL-ORDER-1",
    stripe_session_id="",
) -> Order:
    variant = _make_product_variant()
    order = Order.objects.create(
        email="buyer@example.com",
        billing_first_name="A",
        billing_last_name="B",
        billing_address="Via Roma 1",
        billing_city="Roma",
        billing_postcode="00100",
        shipping_first_name="A",
        shipping_last_name="B",
        shipping_address="Via Roma 1",
        shipping_city="Roma",
        shipping_postcode="00100",
        subtotal=total,
        total=total,
        payment_method=payment_method,
        paypal_order_id=paypal_order_id,
        stripe_session_id=stripe_session_id,
    )
    OrderItem.objects.create(
        order=order,
        variant=variant,
        product_name="Test Product",
        sku=variant.sku,
        unit_price=total,
        quantity=1,
        line_total=total,
    )
    return order


def _paypal_capture_response(
    order: Order,
    *,
    amount: str | None = None,
    currency: str = "EUR",
    capture_status: str = "COMPLETED",
    reference_id: str | None = None,
    paypal_id: str | None = None,
) -> dict:
    return {
        "id": paypal_id or order.paypal_order_id,
        "status": "COMPLETED",
        "purchase_units": [{
            "reference_id": reference_id if reference_id is not None else order.order_number,
            "payments": {
                "captures": [{
                    "id": "CAPTURE-123",
                    "status": capture_status,
                    "amount": {
                        "currency_code": currency,
                        "value": amount if amount is not None else f"{order.total:.2f}",
                    },
                }],
            },
        }],
    }


@override_settings(USE_SQLITE=True)
class PayPalVerificationTests(TestCase):
    @patch("orders.paypal_payments.capture_or_retrieve_paypal_order")
    def test_valid_capture_marks_order_paid_via_verify_flow(self, mock_capture):
        order = _make_order()
        mock_capture.return_value = _paypal_capture_response(order)

        with patch("orders.payments.send_order_confirmation") as mock_mail, patch(
            "orders.payments.send_order_admin_notification"
        ):
            from orders.payments import verify_and_confirm_paypal_order

            updated = verify_and_confirm_paypal_order(order, order.paypal_order_id)

        self.assertEqual(updated.payment_status, Order.PaymentStatus.PAID)
        mock_mail.assert_called_once()

    @patch("orders.paypal_payments.capture_or_retrieve_paypal_order")
    def test_wrong_amount_rejected(self, mock_capture):
        order = _make_order(total=Decimal("50.00"))
        mock_capture.return_value = _paypal_capture_response(order, amount="49.99")

        with self.assertRaises(PayPalVerificationError):
            verify_paypal_payment_for_order(order, order.paypal_order_id)

    @patch("orders.paypal_payments.capture_or_retrieve_paypal_order")
    def test_wrong_currency_rejected(self, mock_capture):
        order = _make_order()
        mock_capture.return_value = _paypal_capture_response(order, currency="USD")

        with self.assertRaises(PayPalVerificationError):
            verify_paypal_payment_for_order(order, order.paypal_order_id)

    @patch("orders.paypal_payments.capture_or_retrieve_paypal_order")
    def test_wrong_reference_rejected(self, mock_capture):
        order = _make_order()
        mock_capture.return_value = _paypal_capture_response(order, reference_id="SW-WRONG")

        with self.assertRaises(PayPalVerificationError):
            verify_paypal_payment_for_order(order, order.paypal_order_id)

    @patch("orders.paypal_payments.capture_or_retrieve_paypal_order")
    def test_wrong_paypal_order_id_rejected(self, mock_capture):
        order = _make_order()
        mock_capture.return_value = _paypal_capture_response(order, paypal_id="OTHER-ID")

        with self.assertRaises(PayPalVerificationError):
            verify_paypal_payment_for_order(order, order.paypal_order_id)

    @patch("orders.paypal_payments.capture_or_retrieve_paypal_order")
    def test_pending_capture_not_paid(self, mock_capture):
        order = _make_order()
        mock_capture.return_value = _paypal_capture_response(order, capture_status="PENDING")

        with self.assertRaises(PayPalVerificationError):
            verify_paypal_payment_for_order(order, order.paypal_order_id)

    @patch("orders.paypal_payments.get_paypal_order")
    @patch("orders.paypal_payments._paypal_request")
    @patch("orders.paypal_payments.get_paypal_access_token", return_value="token")
    def test_already_captured_retrieves_order(self, _token, mock_request, mock_get):
        from orders.paypal_payments import capture_or_retrieve_paypal_order

        order = _make_order()
        err_body = json.dumps({
            "name": "UNPROCESSABLE_ENTITY",
            "details": [{"issue": "ORDER_ALREADY_CAPTURED"}],
        })
        mock_request.side_effect = PayPalError(err_body, status_code=422)
        mock_get.return_value = _paypal_capture_response(order)

        result = capture_or_retrieve_paypal_order(order.paypal_order_id)
        self.assertEqual(result["id"], order.paypal_order_id)
        mock_get.assert_called_once()


@override_settings(USE_SQLITE=True)
class ConfirmOrderPaymentTests(TestCase):
    @patch("orders.payments.send_order_confirmation")
    @patch("orders.payments.send_order_admin_notification")
    def test_repeated_confirmation_no_duplicate_emails(self, mock_admin, mock_user):
        order = _make_order(payment_method=Order.PaymentMethod.STRIPE, paypal_order_id="")

        confirm_order_payment(order)
        confirm_order_payment(order)

        mock_user.assert_called_once()
        mock_admin.assert_called_once()

    @patch("orders.payments.send_order_confirmation")
    @patch("orders.payments.send_order_admin_notification")
    def test_concurrent_confirmation_idempotent(self, mock_admin, mock_user):
        if connection.vendor == "sqlite":
            self.skipTest("SQLite does not support concurrent select_for_update in threads.")

        order = _make_order(payment_method=Order.PaymentMethod.STRIPE, paypal_order_id="")
        errors = []

        def worker():
            try:
                confirm_order_payment(order)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(mock_user.call_count, 1)
        self.assertEqual(mock_admin.call_count, 1)


@override_settings(USE_SQLITE=True)
class StripeVerificationTests(TestCase):
    def test_stripe_session_matches_order(self):
        order = _make_order(
            payment_method=Order.PaymentMethod.STRIPE,
            stripe_session_id="cs_test_123",
            paypal_order_id="",
        )
        session = {
            "id": "cs_test_123",
            "payment_status": "paid",
            "metadata": {"order_number": order.order_number},
            "amount_total": 5000,
            "currency": "eur",
        }
        self.assertTrue(stripe_session_matches_order(order, session))

    def test_stripe_unpaid_session_rejected(self):
        order = _make_order(
            payment_method=Order.PaymentMethod.STRIPE,
            stripe_session_id="cs_test_123",
            paypal_order_id="",
        )
        session = {
            "id": "cs_test_123",
            "payment_status": "unpaid",
            "metadata": {"order_number": order.order_number},
            "amount_total": 5000,
            "currency": "eur",
        }
        self.assertFalse(stripe_session_matches_order(order, session))

    @patch("orders.payments.get_stripe_client")
    def test_verify_stripe_checkout_paid(self, mock_client):
        order = _make_order(
            payment_method=Order.PaymentMethod.STRIPE,
            stripe_session_id="cs_test_123",
            paypal_order_id="",
        )
        session = MagicMock()
        session.payment_status = "paid"
        session.metadata = {"order_number": order.order_number}
        session.id = "cs_test_123"
        session.amount_total = 5000
        session.currency = "eur"
        session.payment_intent = "pi_123"
        mock_client.return_value.checkout.Session.retrieve.return_value = session

        with patch("orders.payments.send_order_confirmation"), patch(
            "orders.payments.send_order_admin_notification"
        ):
            updated = verify_stripe_checkout_for_order(order, "cs_test_123")

        self.assertEqual(updated.payment_status, Order.PaymentStatus.PAID)

    @patch("orders.payments.get_stripe_client")
    def test_webhook_requires_signature_in_production(self, mock_client):
        payload = b"{}"
        with override_settings(DEBUG=False, STRIPE_WEBHOOK_SECRET=""):
            with self.assertRaises(stripe.error.SignatureVerificationError):
                handle_stripe_webhook(payload, "")

    @patch("orders.payments.confirm_order_payment")
    @patch("orders.payments.get_stripe_client")
    def test_webhook_validates_session_before_confirm(self, mock_client, mock_confirm):
        order = _make_order(
            payment_method=Order.PaymentMethod.STRIPE,
            stripe_session_id="cs_test_123",
            paypal_order_id="",
        )
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_wrong",
                    "payment_status": "paid",
                    "metadata": {"order_number": order.order_number},
                    "amount_total": 5000,
                    "currency": "eur",
                    "payment_intent": "pi_x",
                },
            },
        }
        mock_client.return_value.Webhook.construct_event.return_value = event

        with override_settings(DEBUG=False, STRIPE_WEBHOOK_SECRET="whsec_test"):
            handle_stripe_webhook(b"{}", "sig")

        mock_confirm.assert_not_called()


@override_settings(USE_SQLITE=True)
class CancelOrderTests(TestCase):
    def test_repeated_cancel_does_not_double_restore_stock(self):
        variant = _make_product_variant(stock=10)
        order = Order.objects.create(
            email="buyer@example.com",
            billing_first_name="A",
            billing_last_name="B",
            billing_address="x",
            billing_city="Roma",
            billing_postcode="00100",
            shipping_first_name="A",
            shipping_last_name="B",
            shipping_address="x",
            shipping_city="Roma",
            shipping_postcode="00100",
            subtotal=Decimal("10.00"),
            total=Decimal("10.00"),
            payment_method=Order.PaymentMethod.STRIPE,
        )
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name="T",
            sku=variant.sku,
            unit_price=Decimal("10.00"),
            quantity=2,
            line_total=Decimal("20.00"),
        )
        variant.stock_quantity = 8
        variant.save(update_fields=["stock_quantity"])

        cancel_order(order)
        cancel_order(order)
        variant.refresh_from_db()
        self.assertEqual(variant.stock_quantity, 10)

    def test_paid_order_not_cancelled_on_expiry(self):
        order = _make_order(
            payment_method=Order.PaymentMethod.STRIPE,
            paypal_order_id="",
            stripe_session_id="cs_1",
        )
        with patch("orders.payments.send_order_confirmation"), patch(
            "orders.payments.send_order_admin_notification"
        ):
            confirm_order_payment(order)

        cancel_order(order)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertNotEqual(order.status, Order.Status.CANCELLED)


@override_settings(
    USE_SQLITE=True,
    PAYPAL_CLIENT_ID="test-client",
    PAYPAL_CLIENT_SECRET="test-secret",
)
class OrderVerifyViewTests(TestCase):
    @patch("orders.views.verify_and_confirm_paypal_order")
    def test_verify_endpoint_calls_paypal_verification(self, mock_verify):
        order = _make_order()
        mock_verify.return_value = order

        client = APIClient()
        url = reverse("order-verify", kwargs={"order_number": order.order_number})
        response = client.get(url, {"token": order.paypal_order_id})

        self.assertEqual(response.status_code, 200)
        mock_verify.assert_called_once()

    @patch("orders.paypal_payments.capture_or_retrieve_paypal_order")
    def test_verify_rejects_bad_amount(self, mock_capture):
        order = _make_order()
        mock_capture.return_value = _paypal_capture_response(order, amount="1.00")

        client = APIClient()
        url = reverse("order-verify", kwargs={"order_number": order.order_number})
        response = client.get(url, {"token": order.paypal_order_id})

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)


@override_settings(USE_SQLITE=True)
class BankTransferCheckoutTests(TestCase):
    @patch("orders.views.create_order_from_cart")
    @patch("orders.views.send_order_confirmation")
    @patch("orders.views.send_order_admin_notification")
    def test_bank_transfer_stays_unpaid(self, _admin, _user, mock_create):
        user = User.objects.create_user(username="u1", email="u1@example.com", password="pass12345")
        order = _make_order(payment_method=Order.PaymentMethod.BANK_TRANSFER, paypal_order_id="")
        mock_create.return_value = order

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            reverse("checkout"),
            {
                "email": "buyer@example.com",
                "billing_first_name": "A",
                "billing_last_name": "B",
                "billing_address": "x",
                "billing_city": "Roma",
                "billing_postcode": "00100",
                "shipping_first_name": "A",
                "shipping_last_name": "B",
                "shipping_address": "x",
                "shipping_city": "Roma",
                "shipping_postcode": "00100",
                "payment_method": "bank_transfer",
                "accept_terms": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
