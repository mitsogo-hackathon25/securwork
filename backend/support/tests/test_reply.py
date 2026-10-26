from decimal import Decimal

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from support.models import SupportMessage, SupportTicket


@override_settings(USE_SQLITE=True)
class SupportReplyTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="cust", password="pass12345")
        self.staff = User.objects.create_user(
            username="staff",
            password="pass12345",
            is_staff=True,
        )
        self.ticket = SupportTicket.objects.create(
            user=self.customer,
            subject="Help",
            needs_staff_attention=True,
        )
        SupportMessage.objects.create(
            ticket=self.ticket,
            author=self.customer,
            body="Hello",
            is_staff_reply=False,
        )

    def test_admin_can_reply(self):
        self.client.force_authenticate(user=self.staff)
        url = reverse("admin-support-ticket-reply", kwargs={"pk": self.ticket.pk})
        response = self.client.post(url, {"message": "We are on it."}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ticket.messages.filter(is_staff_reply=True).count(), 1)
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.needs_user_attention)
        self.assertFalse(self.ticket.needs_staff_attention)
