from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from orders.models import Cart, CartItem, Order
from orders.payment_fees import calculate_paypal_customer_fee
from orders.services import quote_checkout_from_cart
from store.models import Product, ProductVariant


def _cart_with_item(user, price: str = "1.00") -> Cart:
    product = Product.objects.create(slug="fee-test", sku="FEE-1")
    product.set_current_language("it")
    product.name = "Test"
    product.save()
    variant = ProductVariant.objects.create(
        product=product,
        sku="FEE-V1",
        price=Decimal(price),
        stock_quantity=10,
    )
    cart, _ = Cart.objects.get_or_create(user=user)
    CartItem.objects.create(cart=cart, variant=variant, quantity=1)
    return cart


@override_settings(USE_SQLITE=True)
class PayPalCustomerFeeTests(TestCase):
    def test_fee_gross_up_example(self):
        # Net €7.21 → fee should cover PayPal on gross
        net = Decimal("7.21")
        fee = calculate_paypal_customer_fee(net)
        gross = net + fee
        paypal_fee = (gross * Decimal("0.034") + Decimal("0.35")).quantize(Decimal("0.01"))
        self.assertGreater(fee, Decimal("0.00"))
        self.assertAlmostEqual(float(gross - paypal_fee), float(net), places=1)

    def test_quote_includes_fee_for_paypal_only(self):
        user = User.objects.create_user(username="u1", email="u1@test.com", password="pass12345")
        cart = _cart_with_item(user)
        paypal_quote = quote_checkout_from_cart(cart, payment_method=Order.PaymentMethod.PAYPAL)
        bank_quote = quote_checkout_from_cart(cart, payment_method=Order.PaymentMethod.BANK_TRANSFER)
        self.assertGreater(paypal_quote["payment_fee"], Decimal("0.00"))
        self.assertEqual(bank_quote["payment_fee"], Decimal("0.00"))
        self.assertGreater(paypal_quote["total"], bank_quote["total"])

    def test_checkout_quote_endpoint(self):
        user = User.objects.create_user(username="u2", email="u2@test.com", password="pass12345")
        _cart_with_item(user)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(reverse("checkout-quote"), {"payment_method": "paypal"})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(float(response.data["payment_fee"]), 0)
        self.assertEqual(response.data["total"], "7.83")  # net 7.21 + PayPal fee gross-up
