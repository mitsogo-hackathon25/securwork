import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from store.models import CsvImportBatch


@override_settings(USE_SQLITE=True)
class TopTexAdminAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.staff)

    @patch("store.admin_views.prepare_toptex_import_staging_from_sync_id")
    def test_toptex_sync_prepare_creates_batch(self, prepare_mock):
        sync_id = str(uuid.uuid4())
        rows = [{
            "row": 0,
            "product_sku": "B57",
            "variant_sku": "SKU1",
            "brand": "B",
            "name_it": "Cap",
            "name_en": "Cap",
            "description_it": "",
            "description_en": "",
            "short_description_it": "",
            "short_description_en": "",
            "size": "U",
            "color": "Black",
            "price": Decimal("6.18"),
            "stock": 0,
            "sale_price": None,
            "category_ids": [],
            "supplier_section": "",
            "supplier_category": "",
            "supplier_subcategory": "",
            "allows_customization": False,
            "customization_fee": Decimal("0"),
            "embroidery_chest_enabled": False,
            "embroidery_chest_fee": Decimal("0"),
            "embroidery_large_enabled": False,
            "embroidery_large_fee": Decimal("0"),
            "dtf_chest_enabled": False,
            "dtf_chest_fee": Decimal("0"),
            "dtf_large_enabled": False,
            "dtf_large_fee": Decimal("0"),
            "image_urls": [],
            "mockup_url": "",
            "is_bestseller": False,
            "_toptex_source": True,
        }]
        prepare_mock.return_value = (
            sync_id,
            rows,
            {"b2b_b2c": 1, "b2b_uniquement": 0, "b2c_uniquement": 0},
        )
        url = reverse("admin-product-toptex-sync-prepare")
        response = self.client.post(url, {"sync_id": sync_id}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        prepare_mock.assert_called_once_with(sync_id)
        self.assertTrue(CsvImportBatch.objects.filter(staging_upload_id=sync_id).exists())

    def test_toptex_sync_prepare_requires_sync_id(self):
        url = reverse("admin-product-toptex-sync-prepare")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("sync_id", response.data["detail"])

    @patch("store.toptex_import.load_toptex_catalog_staging")
    @patch("store.admin_views.fetch_and_stage_toptex_catalog_usage_right")
    def test_toptex_sync_catalog_step(self, fetch_mock, load_mock):
        sync_id = str(uuid.uuid4())
        fetch_mock.return_value = 42
        load_mock.return_value = {"b2b_b2c": [{}] * 42}
        url = reverse("admin-product-toptex-sync-catalog-step")
        response = self.client.post(
            url,
            {"sync_id": sync_id, "usage_right": "b2b_b2c"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        fetch_mock.assert_called_once_with(sync_id, "b2b_b2c")
        self.assertEqual(response.data["catalog_items"], 42)
        self.assertEqual(response.data["sync_id"], sync_id)

    @patch("store.admin_views.TopTexClient")
    def test_toptex_connection_test_ok(self, client_cls):
        mock = MagicMock()
        mock.fetch_products_all_usage_rights = MagicMock()
        client_cls.return_value = mock
        mock.ensure_configured.return_value = None
        mock.authenticate.return_value = "token"
        mock.get.return_value = {"items": [{"catalogReference": "B57"}], "totalPages": 1}
        url = reverse("admin-product-toptex-connection-test")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("catalog_items_page1", response.data)
