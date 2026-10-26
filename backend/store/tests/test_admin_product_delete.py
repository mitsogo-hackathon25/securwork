from decimal import Decimal

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from orders.models import Order, OrderItem
from store.models import Product, ProductVariant


@override_settings(USE_SQLITE=True)
class AdminProductDeleteTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.staff)

    def _create_product(self) -> Product:
        product = Product.objects.create(slug="delete-me", sku="DEL-ME")
        product.set_current_language("it")
        product.name = "Delete me"
        product.save()
        ProductVariant.objects.create(
            product=product,
            sku="DEL-ME-V1",
            price=Decimal("25.00"),
            stock_quantity=5,
        )
        return product

    def test_delete_product_without_orders(self):
        product = self._create_product()
        url = reverse("admin-product-detail", kwargs={"pk": product.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_delete_product_with_order_history_removes_product_keeps_order_line(self):
        product = self._create_product()
        variant = product.variants.get()
        order = Order.objects.create(
            email="buyer@example.com",
            billing_first_name="A",
            billing_last_name="B",
            billing_address="Via 1",
            billing_city="Roma",
            billing_postcode="00100",
            shipping_first_name="A",
            shipping_last_name="B",
            shipping_address="Via 1",
            shipping_city="Roma",
            shipping_postcode="00100",
            subtotal=Decimal("25.00"),
            total=Decimal("25.00"),
        )
        line = OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name="Delete me",
            sku=variant.sku,
            unit_price=Decimal("25.00"),
            quantity=1,
            line_total=Decimal("25.00"),
        )

        url = reverse("admin-product-detail", kwargs={"pk": product.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        line.refresh_from_db()
        self.assertIsNone(line.variant_id)
        self.assertEqual(line.product_name, "Delete me")
        self.assertEqual(line.sku, variant.sku)
