from decimal import Decimal

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from store.models import Product, ProductVariant


@override_settings(USE_SQLITE=True)
class CartAddRequiresLoginTests(APITestCase):
    def setUp(self):
        product = Product.objects.create(slug="cart-auth", sku="CART-AUTH")
        product.set_current_language("it")
        product.name = "Cart auth"
        product.save()
        self.variant = ProductVariant.objects.create(
            product=product,
            sku="CART-AUTH-V1",
            price=Decimal("10.00"),
            stock_quantity=5,
        )
        self.user = User.objects.create_user(username="buyer", password="pass12345")

    def test_anonymous_cannot_add_to_cart(self):
        url = reverse("cart")
        response = self.client.post(url, {"variant_id": self.variant.pk, "quantity": 1}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_add_to_cart(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cart")
        response = self.client.post(url, {"variant_id": self.variant.pk, "quantity": 1}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["item_count"], 1)
