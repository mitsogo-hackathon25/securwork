from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase


@override_settings(USE_SQLITE=True)
class EmailLoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer1",
            email="buyer@example.com",
            password="Str0ngPass!2026",
        )

    def test_login_with_email(self):
        url = reverse("token_obtain")
        response = self.client.post(
            url,
            {"email": "buyer@example.com", "password": "Str0ngPass!2026"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_login_rejects_wrong_password(self):
        url = reverse("token_obtain")
        response = self.client.post(
            url,
            {"email": "buyer@example.com", "password": "wrong"},
            format="json",
        )
        self.assertIn(response.status_code, (400, 401))
