from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from orders.models import Order

User = get_user_model()


class AdminUsersApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user(
            username="buyer1",
            email="buyer@example.com",
            password="pass12345",
            first_name="Mario",
            last_name="Rossi",
        )
        cls.customer.profile.phone = "3331234567"
        cls.customer.profile.save()

        Order.objects.create(
            user=cls.customer,
            email="buyer@example.com",
            billing_first_name="Mario",
            billing_last_name="Rossi",
            billing_address="Via Roma 1",
            billing_city="Roma",
            billing_postcode="00100",
            shipping_first_name="Mario",
            shipping_last_name="Rossi",
            shipping_address="Via Roma 1",
            shipping_city="Roma",
            shipping_postcode="00100",
            subtotal=Decimal("50.00"),
            total=Decimal("50.00"),
            payment_status=Order.PaymentStatus.PAID,
        )

    def test_list_requires_staff(self):
        client = APIClient()
        client.force_authenticate(user=self.customer)
        response = client.get(reverse("admin-user-list"))
        self.assertEqual(response.status_code, 403)

    def test_list_returns_users(self):
        client = APIClient()
        staff = User.objects.create_user(
            username="staff2",
            email="staff2@securwork.it",
            password="pass12345",
            is_staff=True,
        )
        client.force_authenticate(user=staff)
        response = client.get(reverse("admin-user-list"))
        self.assertEqual(response.status_code, 200)
        emails = [row["email"] for row in response.data["results"]]
        self.assertIn("buyer@example.com", emails)

    def test_detail_includes_orders(self):
        client = APIClient()
        staff = User.objects.create_user(
            username="staff3",
            email="staff3@securwork.it",
            password="pass12345",
            is_staff=True,
        )
        client.force_authenticate(user=staff)
        url = reverse("admin-user-detail", kwargs={"pk": self.customer.pk})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "buyer@example.com")
        self.assertEqual(response.data["profile"]["phone"], "3331234567")
        self.assertEqual(response.data["order_count"], 1)
        self.assertEqual(response.data["paid_order_count"], 1)
        self.assertEqual(len(response.data["recent_orders"]), 1)
