from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

User = get_user_model()


@override_settings(USE_SQLITE=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer1",
            email="buyer@example.com",
            password="OldPass123!",
        )

    def test_request_sends_otp_email(self):
        url = reverse("password-reset-request")
        response = self.client.post(url, {"email": "buyer@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)

    def test_request_unknown_email_same_response_no_mail(self):
        url = reverse("password-reset-request")
        response = self.client.post(url, {"email": "unknown@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirm_resets_password(self):
        self.client.post(reverse("password-reset-request"), {"email": "buyer@example.com"}, format="json")
        import re

        body = mail.outbox[0].body
        match = re.search(r"\b(\d{6})\b", body)
        self.assertIsNotNone(match)
        code = match.group(1)

        confirm_url = reverse("password-reset-confirm")
        response = self.client.post(
            confirm_url,
            {
                "email": "buyer@example.com",
                "otp": code,
                "password": "NewPass456!",
                "password_confirm": "NewPass456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass456!"))

    def test_confirm_wrong_otp_rejected(self):
        self.client.post(reverse("password-reset-request"), {"email": "buyer@example.com"}, format="json")
        response = self.client.post(
            reverse("password-reset-confirm"),
            {
                "email": "buyer@example.com",
                "otp": "000000",
                "password": "NewPass456!",
                "password_confirm": "NewPass456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPass123!"))
