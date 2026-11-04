from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from store.toptex_client import TOPTEX_USAGE_RIGHTS, extract_toptex_list_payload, _list_records_from_toptex_response
from store.toptex_import import (
    _inventory_stock_value,
    _inventory_sku_key,
    _price_from_toptex_price_api_row,
    merge_toptex_catalog_items,
    toptex_item_to_parsed_rows,
)


class TopTexImportTests(SimpleTestCase):
    def test_usage_rights_constants(self):
        self.assertEqual(
            TOPTEX_USAGE_RIGHTS,
            ("b2b_b2c", "b2b_uniquement", "b2c_uniquement"),
        )

    def test_merge_catalog_by_reference(self):
        item_a = {
            "catalogReference": "B050",
            "designation": {"it": "Maglietta"},
            "colors": [{"colors": {"it": "Bianco"}, "sizes": [{"sku": "B050-WHT-M", "size": "M", "publicUnitPrice": "10,00 €"}]}],
        }
        item_b = {
            "catalogReference": "B050",
            "colors": [{"colors": {"it": "Nero"}, "sizes": [{"sku": "B050-BLK-M", "size": "M", "publicUnitPrice": "10,00 €"}]}],
        }
        merged = merge_toptex_catalog_items({
            "b2b_b2c": [item_a],
            "b2c_uniquement": [item_b],
        })
        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged[0]["colors"]), 2)

    @override_settings(TOPTEX_PRICE_MARKUP_PERCENT=10)
    def test_price_markup_and_mapping(self):
        item = {
            "catalogReference": "B050",
            "brand": "BrandX",
            "designation": {"it": "Prodotto test", "en": "Test product"},
            "description": {"it": "Desc", "en": "Desc"},
            "family": {"it": "Abbigliamento"},
            "sub_family": {"it": "T-shirt"},
            "colors": [{
                "colors": {"it": "Rosso"},
                "sizes": [{
                    "sku": "SKU-1",
                    "size": "L",
                    "publicUnitPrice": "10,00 €",
                }],
            }],
        }
        rows = toptex_item_to_parsed_rows(item, lang="it")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["product_sku"], "B050")
        self.assertEqual(row["variant_sku"], "SKU-1")
        self.assertEqual(row["price"], Decimal("11.00"))
        self.assertEqual(row["brand"], "BrandX")

    def test_inventory_stock_parser(self):
        self.assertEqual(_inventory_stock_value({"sku": "A", "quantity": 12}), 12)
        self.assertEqual(_inventory_stock_value({"SKU": "B", "availableQuantity": "5"}), 5)
        self.assertIsNone(_inventory_stock_value({"sku": "C"}))
        self.assertEqual(_inventory_sku_key({"sku": "X-1"}), "x-1")

    def test_extract_toptex_list_payload(self):
        self.assertEqual(len(extract_toptex_list_payload({"inventoryItems": [{"sku": "1"}]})), 1)

    def test_list_records_single_price_row(self):
        row = {
            "catalogReference": "B57",
            "sku": "B57_51335_51334",
            "prices": [{"quantity": 1, "price": 6.18}],
        }
        records = _list_records_from_toptex_response(row)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["sku"], "B57_51335_51334")

    @override_settings(TOPTEX_PRICE_MARKUP_PERCENT=0)
    def test_price_api_row_parsing(self):
        item = {
            "sku": "SKU-1",
            "prices": [{"quantity": 10, "price": 5.0}, {"quantity": 1, "price": 6.18}],
        }
        price = _price_from_toptex_price_api_row(item, Decimal("0"))
        self.assertEqual(price, Decimal("6.18"))

    def test_inventory_stock_skips_price_tier_quantity(self):
        item = {"sku": "X", "prices": [{"quantity": 1, "price": 6}], "stock": 42}
        self.assertEqual(_inventory_stock_value(item), 42)
