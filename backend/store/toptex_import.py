"""Map TopTex catalog JSON to SecurWork CSV-import row format."""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings

from .csv_import import (
    _merge_image_url_lists,
    _normalize_http_url,
    _normalize_price_string,
    stage_parsed_import_rows,
)
from .toptex_client import TopTexAPIError, TopTexClient

logger = logging.getLogger(__name__)


def _localized(value: Any, lang: str, fallback: str = "en") -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in (lang, fallback, "it", "en"):
            text = value.get(key)
            if text and str(text).strip():
                return str(text).strip()
    return ""


def _parse_toptex_price(raw: str, markup_percent: Decimal) -> Decimal | None:
    normalized = _normalize_price_string(raw or "")
    if not normalized:
        return None
    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None
    if markup_percent:
        amount = amount * (Decimal("1") + markup_percent / Decimal("100"))
    return amount.quantize(Decimal("0.01"))


def _extract_image_urls_from_packshots(packshots: Any) -> list[str]:
    urls: list[str] = []
    if not isinstance(packshots, dict):
        return urls
    for value in packshots.values():
        if isinstance(value, str):
            url = _normalize_http_url(value)
            if url.startswith(("http://", "https://")):
                urls.append(url)
        elif isinstance(value, dict):
            if value.get("error"):
                continue
            for key in ("url", "href", "src", "link"):
                url = _normalize_http_url(str(value.get(key) or ""))
                if url.startswith(("http://", "https://")):
                    urls.append(url)
    return urls


def _extract_product_images(item: dict[str, Any], color_block: dict[str, Any] | None) -> list[str]:
    urls: list[str] = []
    for img in item.get("images") or []:
        if isinstance(img, dict) and not img.get("error"):
            url = _normalize_http_url(str(img.get("url") or img.get("href") or ""))
            if url.startswith(("http://", "https://")):
                urls.append(url)
        elif isinstance(img, str):
            url = _normalize_http_url(img)
            if url.startswith(("http://", "https://")):
                urls.append(url)
    if color_block:
        urls.extend(_extract_image_urls_from_packshots(color_block.get("packshots")))
    return urls


def _variant_sale_state_ok(state: Any) -> bool:
    if state is None or state == "":
        return True
    return str(state).strip().lower() == "active"


def _product_sale_state_ok(item: dict[str, Any]) -> bool:
    if not getattr(settings, "TOPTEX_IMPORT_ONLY_ACTIVE", True):
        return True
    return _variant_sale_state_ok(item.get("saleState"))


def _inventory_stock_value(item: dict[str, Any]) -> int | None:
    for key in (
        "quantity",
        "stock",
        "availableQuantity",
        "available_quantity",
        "qty",
        "inventory",
        "inStock",
        "in_stock",
    ):
        raw = item.get(key)
        if raw is None or raw == "":
            continue
        try:
            stock = int(raw)
        except (TypeError, ValueError):
            continue
        return max(stock, 0)
    return None


def _inventory_sku_key(item: dict[str, Any]) -> str:
    for key in ("sku", "SKU", "productSku", "product_sku", "variantSku"):
        raw = item.get(key)
        if raw and str(raw).strip():
            return str(raw).strip().lower()
    return ""


def build_stock_by_sku_from_inventory(
    client: TopTexClient,
    catalog_refs: list[str],
) -> dict[str, int]:
    stock_by_sku: dict[str, int] = {}
    for catalog_ref in catalog_refs:
        ref = (catalog_ref or "").strip()
        if not ref:
            continue
        try:
            items = client.fetch_inventory_by_catalog_ref(ref)
        except TopTexAPIError:
            logger.exception("TopTex inventory fetch failed for %s", ref)
            continue
        for item in items:
            sku = _inventory_sku_key(item)
            stock = _inventory_stock_value(item)
            if sku and stock is not None:
                stock_by_sku[sku] = stock
    return stock_by_sku


def build_price_by_sku_from_price_api(
    client: TopTexClient,
    catalog_refs: list[str],
    *,
    markup_percent: Decimal,
) -> dict[str, Decimal]:
    price_by_sku: dict[str, Decimal] = {}
    for catalog_ref in catalog_refs:
        ref = (catalog_ref or "").strip()
        if not ref:
            continue
        try:
            items = client.fetch_prices_by_catalog_ref(ref)
        except TopTexAPIError:
            logger.exception("TopTex price fetch failed for %s", ref)
            continue
        for item in items:
            sku = _inventory_sku_key(item)
            if not sku:
                continue
            raw = (
                item.get("publicUnitPrice")
                or item.get("price")
                or item.get("unitPrice")
                or item.get("publicPrice")
                or ""
            )
            price = _parse_toptex_price(str(raw), markup_percent)
            if price is not None:
                price_by_sku[sku] = price
    return price_by_sku


def toptex_item_to_parsed_rows(
    item: dict[str, Any],
    *,
    lang: str = "it",
    markup_percent: Decimal | None = None,
    stock_by_sku: dict[str, int] | None = None,
    price_by_sku: dict[str, Decimal] | None = None,
) -> list[dict[str, Any]]:
    if not _product_sale_state_ok(item):
        return []
    catalog_ref = (item.get("catalogReference") or item.get("productReference") or "").strip()
    if not catalog_ref:
        return []
    markup = markup_percent
    if markup is None:
        markup = Decimal(str(getattr(settings, "TOPTEX_PRICE_MARKUP_PERCENT", 0)))
    brand = (item.get("brand") or "").strip()
    name_it = _localized(item.get("designation"), lang)
    name_en = _localized(item.get("designation"), "en", fallback="it")
    if not name_it:
        name_it = catalog_ref
    if not name_en:
        name_en = name_it
    desc_it = _localized(item.get("description"), lang)
    desc_en = _localized(item.get("description"), "en", fallback="it")
    if not desc_it:
        desc_it = desc_it or name_it
    if not desc_en:
        desc_en = desc_en or name_en
    family = _localized(item.get("family"), lang)
    sub_family = _localized(item.get("sub_family"), lang)
    base_images = _extract_product_images(item, None)

    rows: list[dict[str, Any]] = []
    for color_block in item.get("colors") or []:
        if not isinstance(color_block, dict):
            continue
        if not _variant_sale_state_ok(color_block.get("saleState")):
            continue
        color_name = _localized(color_block.get("colors"), lang) or _localized(
            color_block.get("colorsDominant"),
            lang,
        )
        if not color_name:
            color_name = "UNICO"
        color_images = _extract_product_images(item, color_block)
        image_urls = _merge_image_url_lists(base_images, color_images)

        for size_row in color_block.get("sizes") or []:
            if not isinstance(size_row, dict):
                continue
            if not _variant_sale_state_ok(size_row.get("saleState")):
                continue
            variant_sku = (size_row.get("sku") or "").strip()
            if not variant_sku:
                continue
            size = (size_row.get("size") or "UNICA").strip()
            price_raw = size_row.get("publicUnitPrice") or size_row.get("price") or ""
            price = _parse_toptex_price(str(price_raw), markup)
            if price is None and price_by_sku:
                price = price_by_sku.get(variant_sku.lower())
            if price is None:
                continue
            stock = 0
            if stock_by_sku and variant_sku.lower() in stock_by_sku:
                stock = stock_by_sku[variant_sku.lower()]
            elif getattr(settings, "TOPTEX_DEFAULT_STOCK", 0):
                try:
                    stock = int(getattr(settings, "TOPTEX_DEFAULT_STOCK", 0))
                except (TypeError, ValueError):
                    stock = 0

            rows.append({
                "row": 0,
                "product_sku": catalog_ref,
                "_toptex_source": True,
                "brand": brand,
                "name_it": name_it,
                "name_en": name_en,
                "short_description_it": "",
                "short_description_en": "",
                "description_it": desc_it,
                "description_en": desc_en,
                "is_bestseller": False,
                "size": size,
                "color": color_name,
                "price": price,
                "stock": stock,
                "sale_price": None,
                "variant_sku": variant_sku,
                "category_ids": [],
                "supplier_section": "",
                "supplier_category": family,
                "supplier_subcategory": sub_family,
                "allows_customization": False,
                "customization_fee": Decimal("0.00"),
                "embroidery_chest_enabled": False,
                "embroidery_chest_fee": Decimal("0.00"),
                "embroidery_large_enabled": False,
                "embroidery_large_fee": Decimal("0.00"),
                "dtf_chest_enabled": False,
                "dtf_chest_fee": Decimal("0.00"),
                "dtf_large_enabled": False,
                "dtf_large_fee": Decimal("0.00"),
                "image_urls": image_urls,
                "mockup_url": "",
            })
    return rows


def merge_toptex_catalog_items(
    items_by_usage_right: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Merge catalog entries from b2b_b2c, b2b_uniquement, b2c_uniquement."""
    buckets: dict[str, list[dict[str, Any]]] = {}
    for usage_right, items in items_by_usage_right.items():
        for item in items:
            ref = (item.get("catalogReference") or "").strip().lower()
            if not ref:
                continue
            buckets.setdefault(ref, []).append(item)

    merged: list[dict[str, Any]] = []
    for group in buckets.values():
        base = dict(group[0])
        all_colors: list[dict[str, Any]] = []
        for part in group:
            all_colors.extend(part.get("colors") or [])
        base["colors"] = all_colors
        merged.append(base)
    return merged


def build_parsed_rows_from_toptex(
    client: TopTexClient | None = None,
    *,
    lang: str | None = None,
    usage_rights: tuple[str, ...] | None = None,
) -> tuple[list[dict], dict[str, int]]:
    lang = lang or getattr(settings, "TOPTEX_LANG", "it") or "it"
    client = client or TopTexClient()
    client.authenticate()
    by_right = client.fetch_products_all_usage_rights(usage_rights)
    stats = {right: len(items) for right, items in by_right.items()}
    merged_items = merge_toptex_catalog_items(by_right)
    markup = Decimal(str(getattr(settings, "TOPTEX_PRICE_MARKUP_PERCENT", 0)))
    catalog_refs = sorted({
        (item.get("catalogReference") or item.get("productReference") or "").strip()
        for item in merged_items
    } - {""})

    stock_by_sku: dict[str, int] = {}
    if getattr(settings, "TOPTEX_FETCH_INVENTORY", True):
        stock_by_sku = build_stock_by_sku_from_inventory(client, catalog_refs)

    price_by_sku: dict[str, Decimal] = {}
    if getattr(settings, "TOPTEX_FETCH_PRICES", True):
        price_by_sku = build_price_by_sku_from_price_api(
            client,
            catalog_refs,
            markup_percent=markup,
        )

    parsed_rows: list[dict] = []
    seen_variants: set[tuple[str, str]] = set()
    for item in merged_items:
        for row in toptex_item_to_parsed_rows(
            item,
            lang=lang,
            markup_percent=markup,
            stock_by_sku=stock_by_sku,
            price_by_sku=price_by_sku,
        ):
            key = (row["product_sku"].lower(), row["variant_sku"].lower())
            if key in seen_variants:
                idx = next(
                    i for i, r in enumerate(parsed_rows)
                    if (r["product_sku"].lower(), r["variant_sku"].lower()) == key
                )
                parsed_rows[idx]["image_urls"] = _merge_image_url_lists(
                    parsed_rows[idx].get("image_urls") or [],
                    row.get("image_urls") or [],
                )
                continue
            seen_variants.add(key)
            parsed_rows.append(row)
    stats["catalog_references"] = len(catalog_refs)
    stats["inventory_skus"] = len(stock_by_sku)
    return parsed_rows, stats


def prepare_toptex_import_staging(
    client: TopTexClient | None = None,
) -> tuple[str, list[dict], dict[str, int]]:
    """Fetch TopTex (all usage rights), convert to parsed rows, stage on disk."""
    parsed_rows, stats = build_parsed_rows_from_toptex(client=client)
    if not parsed_rows:
        raise ValueError(
            "Nessuna variante importabile da TopTex. "
            "Verifica usage_right, lang e prodotti active.",
        )
    sync_id = str(uuid.uuid4())
    stage_parsed_import_rows(sync_id, parsed_rows)
    return sync_id, parsed_rows, stats
