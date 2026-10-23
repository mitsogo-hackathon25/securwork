from decimal import Decimal

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from orders.models import Order, OrderItem
from store.models import Product, ProductVariant


@override_settings(USE_SQLITE=True)
class AdminProductBulkDeleteTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.staff)
        self.url = reverse("admin-product-bulk-delete")

    def _create_product(self, sku: str) -> Product:
        product = Product.objects.create(slug=sku.lower(), sku=sku)
        product.set_current_language("it")
        product.name = f"Product {sku}"
        product.save()
        ProductVariant.objects.create(
            product=product,
            sku=f"{sku}-V1",
            price=Decimal("10.00"),
            stock_quantity=1,
        )
        return product

    def test_bulk_delete_removes_products_without_orders(self):
        first = self._create_product("BULK-1")
        second = self._create_product("BULK-2")
        response = self.client.post(self.url, {"ids": [first.pk, second.pk]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deleted"], [first.pk, second.pk])
        self.assertFalse(Product.objects.filter(pk__in=[first.pk, second.pk]).exists())

    def test_bulk_delete_blocks_products_with_orders(self):
        product = self._create_product("BULK-ORD")
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
            subtotal=Decimal("10.00"),
            total=Decimal("10.00"),
        )
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name="Product",
            sku=variant.sku,
            unit_price=Decimal("10.00"),
            quantity=1,
            line_total=Decimal("10.00"),
        )
        deletable = self._create_product("BULK-OK")

        response = self.client.post(
            self.url,
            {"ids": [product.pk, deletable.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deleted"], [deletable.pk])
        self.assertEqual(len(response.data["blocked"]), 1)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
