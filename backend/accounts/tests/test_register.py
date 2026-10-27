from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import UserProfile

User = get_user_model()


@override_settings(USE_SQLITE=True)
class RegisterViewTests(APITestCase):
    def test_register_creates_user_and_profile(self):
        url = reverse("register")
        response = self.client.post(
            url,
            {
                "email": "shopper1@example.com",
                "first_name": "Shop",
                "last_name": "Per",
                "password": "Str0ngPass!2026",
                "password_confirm": "Str0ngPass!2026",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="shopper1@example.com")
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_register_password_mismatch_message_italian(self):
        url = reverse("register")
        response = self.client.post(
            f"{url}?lang=it",
            {
                "email": "shopper2@example.com",
                "password": "Str0ngPass!2026",
                "password_confirm": "Different!2026",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("non coincidono", str(response.data["password_confirm"][0]).lower())

    def test_register_password_mismatch_message_english(self):
        url = reverse("register")
        response = self.client.post(
            f"{url}?lang=en",
            {
                "email": "shopper3@example.com",
                "password": "Str0ngPass!2026",
                "password_confirm": "Different!2026",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("do not match", str(response.data["password_confirm"][0]).lower())
