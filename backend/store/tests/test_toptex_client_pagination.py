from unittest.mock import MagicMock

from django.test import SimpleTestCase, override_settings

from store.toptex_client import TopTexClient


@override_settings(TOPTEX_API_PAGE_SIZE=2, TOPTEX_MAX_CATALOG_PAGES=10)
class TopTexClientPaginationTests(SimpleTestCase):
    def test_fetch_prices_uses_catalog_reference_and_pages(self):
        client = TopTexClient(
            base_url="https://api.example.com",
            api_key="key",
            username="u",
            password="p",
        )
        client._token = "tok"
        client.get = MagicMock(side_effect=[
            {
                "items": [
                    {"sku": "A", "prices": [{"quantity": 1, "price": 1}]},
                    {"sku": "B", "prices": [{"quantity": 1, "price": 2}]},
                ],
            },
            {"items": [{"sku": "C", "prices": [{"quantity": 1, "price": 3}]}]},
        ])
        rows = client.fetch_prices_by_catalog_ref("B57")
        self.assertEqual(len(rows), 3)
        self.assertEqual(client.get.call_count, 2)
        first_params = client.get.call_args_list[0][0][1]
        self.assertEqual(first_params["catalog_reference"], "B57")
        self.assertEqual(first_params["page_number"], "1")
        self.assertEqual(first_params["page_size"], "2")
