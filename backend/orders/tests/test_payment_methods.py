from django.test import TestCase

from orders.models import Order
from orders.payment_methods import normalize_payment_method


class NormalizePaymentMethodTests(TestCase):
    def test_card_maps_to_card(self):
        self.assertEqual(normalize_payment_method("card"), Order.PaymentMethod.CARD)

    def test_paypal_unchanged(self):
        self.assertEqual(normalize_payment_method("paypal"), Order.PaymentMethod.PAYPAL)
