from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from support.models import SupportMessage, SupportTicket


@override_settings(USE_SQLITE=True)
class CustomerSupportTicketTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="buyer1", password="pass12345")
        self.other = User.objects.create_user(username="buyer2", password="pass12345")
        self.ticket = SupportTicket.objects.create(
            user=self.customer,
            subject="Need help",
            needs_staff_attention=False,
            needs_user_attention=True,
        )
        SupportMessage.objects.create(
            ticket=self.ticket,
            author=self.customer,
            body="My question",
            is_staff_reply=False,
        )
        SupportMessage.objects.create(
            ticket=self.ticket,
            author=self.customer,
            body="Support answer",
            is_staff_reply=True,
        )

    def test_customer_can_open_ticket_detail(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse("support-ticket-detail", kwargs={"pk": self.ticket.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["messages"]), 2)
        self.assertFalse(response.data["needs_user_attention"])

    def test_customer_cannot_open_other_users_ticket(self):
        self.client.force_authenticate(user=self.other)
        url = reverse("support-ticket-detail", kwargs={"pk": self.ticket.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
