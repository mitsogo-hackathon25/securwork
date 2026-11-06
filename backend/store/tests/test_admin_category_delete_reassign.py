from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from store.models import Category, Product


@override_settings(USE_SQLITE=True)
class AdminCategoryDeleteReassignTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.staff)

        self.work = Category.objects.create(slug="w-test", section=Category.Section.WORKWEAR)
        self.work.set_current_language("it")
        self.work.name = "W"
        self.work.save()
        self.old = Category.objects.create(
            slug="old-cat",
            section=Category.Section.WORKWEAR,
            parent=self.work,
        )
        self.old.set_current_language("it")
        self.old.name = "Old"
        self.old.save()
        self.target = Category.objects.create(
            slug="target-cat",
            section=Category.Section.WORKWEAR,
            parent=self.work,
        )
        self.target.set_current_language("it")
        self.target.name = "Target"
        self.target.save()
        self.product = Product.objects.create(sku="P-R-1", slug="p-r-1", brand="T")
        self.product.categories.add(self.old)

    def test_delete_without_reassign_returns_400_with_code(self):
        url = reverse("admin-category-detail", kwargs={"pk": self.old.pk})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "category_has_products")

    def test_delete_with_reassign_moves_products_and_deletes(self):
        url = reverse("admin-category-detail", kwargs={"pk": self.old.pk})
        res = self.client.delete(f"{url}?reassign_to={self.target.pk}")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=self.old.pk).exists())
        self.product.refresh_from_db()
        self.assertTrue(self.product.categories.filter(pk=self.target.pk).exists())
        self.assertFalse(self.product.categories.filter(pk=self.old.pk).exists())

    def test_bulk_delete_with_reassign(self):
        url = reverse("admin-category-bulk-delete")
        res = self.client.post(
            url,
            {"ids": [self.old.pk], "reassign_to": self.target.pk},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["deleted"], [self.old.pk])
        self.assertEqual(res.data["failed"], [])
        self.assertFalse(Category.objects.filter(pk=self.old.pk).exists())
