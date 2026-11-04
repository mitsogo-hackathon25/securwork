"""Map TopTex catalog JSON to SecurWork CSV-import row format."""
from __future__ import annotations

import gzip
import json
import logging
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings

from .csv_import import (
    _merge_image_url_lists,
    _normalize_http_url,
    _normalize_price_string,
    csv_import_staging_dir,
    stage_parsed_import_rows,
)
from .toptex_client import TOPTEX_USAGE_RIGHTS, TopTexAPIError, TopTexClient, TopTexConfigError

logger = logging.getLogger(__name__)

TOPTEX_CATALOG_STAGING_SUFFIX = ".toptex_catalog.json.gz"


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


def _parse_toptex_price_amount(raw: Any, markup_percent: Decimal) -> Decimal | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        try:
            amount = Decimal(str(raw))
        except InvalidOperation:
            return None
        if markup_percent:
            amount = amount * (Decimal("1") + markup_percent / Decimal("100"))
        return amount.quantize(Decimal("0.01"))
    return _parse_toptex_price(str(raw), markup_percent)


def _price_from_toptex_price_api_row(item: dict[str, Any], markup_percent: Decimal) -> Decimal | None:
    """Parse GET /v3/products/price row (prices[] tiers + legacy root fields)."""
    prices = item.get("prices")
    if isinstance(prices, list) and prices:
        tier: dict[str, Any] | None = None
        for entry in prices:
            if not isinstance(entry, dict):
                continue
            qty = entry.get("quantity")
            if qty == 1 or qty == "1":
                tier = entry
                break
        if tier is None:
            first = prices[0]
            tier = first if isinstance(first, dict) else None
        if tier is not None:
            parsed = _parse_toptex_price_amount(tier.get("price"), markup_percent)
            if parsed is not None:
                return parsed
    for key in ("publicUnitPrice", "price", "unitPrice", "publicPrice"):
        parsed = _parse_toptex_price_amount(item.get(key), markup_percent)
        if parsed is not None:
            return parsed
        parsed = _parse_toptex_price(str(item.get(key) or ""), markup_percent)
        if parsed is not None:
            return parsed
    return None


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
    # Ignore price-tier "quantity" inside prices[] (price API rows).
    if isinstance(item.get("prices"), list):
        for key in (
            "stock",
            "availableQuantity",
            "available_quantity",
            "inventory",
            "inStock",
            "in_stock",
            "qty",
        ):
            raw = item.get(key)
            if raw is None or raw == "":
                continue
            try:
                return max(int(raw), 0)
            except (TypeError, ValueError):
                continue
        return None
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
            price = _price_from_toptex_price_api_row(item, markup_percent)
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
            if not isinstance(item, dict):
                continue
            ref = (item.get("catalogReference") or "").strip().lower()
            if not ref:
                continue
            buckets.setdefault(ref, []).append(item)

    merged: list[dict[str, Any]] = []
    for group in buckets.values():
        base = dict(group[0])
        all_colors: list[dict[str, Any]] = []
        for part in group:
            if isinstance(part.get("colors"), list):
                all_colors.extend(part.get("colors") or [])
        base["colors"] = all_colors
        merged.append(base)
    return merged


def apply_toptex_stock_to_product_rows(
    rows: list[dict[str, Any]],
    client: TopTexClient | None = None,
) -> None:
    """Fetch /v3/products/inventory for one Codice Padre (during chunked import)."""
    if not rows or not getattr(settings, "TOPTEX_FETCH_INVENTORY", True):
        return
    catalog_ref = (rows[0].get("product_sku") or "").strip()
    if not catalog_ref:
        return
    client = client or TopTexClient()
    if not client._token:
        client.authenticate()
    stock_by_sku = build_stock_by_sku_from_inventory(client, [catalog_ref])
    for row in rows:
        sku = (row.get("variant_sku") or "").strip().lower()
        if sku in stock_by_sku:
            row["stock"] = stock_by_sku[sku]


def _validate_toptex_sync_id(sync_id: str) -> None:
    from .csv_import import _UPLOAD_ID_RE

    if not _UPLOAD_ID_RE.match(sync_id or ""):
        raise ValueError("sync_id non valido")


def toptex_catalog_staging_path(sync_id: str):
    _validate_toptex_sync_id(sync_id)
    return csv_import_staging_dir() / f"{sync_id}{TOPTEX_CATALOG_STAGING_SUFFIX}"


def load_toptex_catalog_staging(sync_id: str) -> dict[str, list[dict]] | None:
    path = toptex_catalog_staging_path(sync_id)
    if not path.is_file():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        return None
    return {
        str(key): [row for row in value if isinstance(row, dict)]
        for key, value in data.items()
        if isinstance(value, list)
    }


def save_toptex_catalog_staging(sync_id: str, by_right: dict[str, list[dict]]) -> None:
    path = toptex_catalog_staging_path(sync_id)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(by_right, handle, ensure_ascii=False)


def delete_toptex_catalog_staging(sync_id: str) -> None:
    try:
        toptex_catalog_staging_path(sync_id).unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not delete TopTex catalog staging %s", sync_id)


def fetch_and_stage_toptex_catalog_usage_right(
    sync_id: str,
    usage_right: str,
    client: TopTexClient | None = None,
) -> int:
    if usage_right not in TOPTEX_USAGE_RIGHTS:
        raise ValueError(
            f"usage_right must be one of: {', '.join(TOPTEX_USAGE_RIGHTS)}",
        )
    _validate_toptex_sync_id(sync_id)
    lang = getattr(settings, "TOPTEX_LANG", "it") or "it"
    client = client or TopTexClient()
    client.authenticate()
    items = client.fetch_products_all_for_usage_right(usage_right, lang=lang)
    by_right = load_toptex_catalog_staging(sync_id) or {}
    by_right[usage_right] = items
    save_toptex_catalog_staging(sync_id, by_right)
    return len(items)


def build_parsed_rows_from_catalog_rights(
    by_right: dict[str, list[dict[str, Any]]],
    *,
    client: TopTexClient | None = None,
    lang: str | None = None,
) -> tuple[list[dict], dict[str, int]]:
    lang = lang or getattr(settings, "TOPTEX_LANG", "it") or "it"
    stats = {right: len(items) for right, items in by_right.items()}
    merged_items = merge_toptex_catalog_items(by_right)
    markup = Decimal(str(getattr(settings, "TOPTEX_PRICE_MARKUP_PERCENT", 0)))
    catalog_refs = sorted({
        (item.get("catalogReference") or item.get("productReference") or "").strip()
        for item in merged_items
    } - {""})

    stock_by_sku: dict[str, int] = {}
    if getattr(settings, "TOPTEX_FETCH_INVENTORY", True) and getattr(
        settings,
        "TOPTEX_FETCH_INVENTORY_IN_PREPARE",
        False,
    ):
        client = client or TopTexClient()
        if not client._token:
            client.authenticate()
        stock_by_sku = build_stock_by_sku_from_inventory(client, catalog_refs)

    price_by_sku: dict[str, Decimal] = {}
    if getattr(settings, "TOPTEX_FETCH_PRICES", False):
        client = client or TopTexClient()
        if not client._token:
            client.authenticate()
        price_by_sku = build_price_by_sku_from_price_api(
            client,
            catalog_refs,
            markup_percent=markup,
        )

    parsed_rows: list[dict] = []
    seen_variants: set[tuple[str, str]] = set()
    for item in merged_items:
        if not isinstance(item, dict):
            continue
        try:
            row_iter = toptex_item_to_parsed_rows(
                item,
                lang=lang,
                markup_percent=markup,
                stock_by_sku=stock_by_sku,
                price_by_sku=price_by_sku,
            )
        except Exception:
            logger.exception(
                "TopTex skip item %s",
                item.get("catalogReference"),
            )
            continue
        for row in row_iter:
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
    return build_parsed_rows_from_catalog_rights(by_right, client=client, lang=lang)


def prepare_toptex_import_staging_from_sync_id(
    sync_id: str,
) -> tuple[str, list[dict], dict[str, int]]:
    """Build parsed import rows from staged TopTex catalog slices (no catalog HTTP)."""
    by_right = load_toptex_catalog_staging(sync_id)
    if not by_right:
        raise ValueError(
            "Catalogo TopTex non trovato o scaduto. "
            "Ripeti la sincronizzazione (passi usage_right).",
        )
    missing = [r for r in TOPTEX_USAGE_RIGHTS if r not in by_right]
    if missing and len(by_right) < len(TOPTEX_USAGE_RIGHTS):
        logger.warning("TopTex catalog staging missing usage_rights: %s", missing)
    try:
        parsed_rows, stats = build_parsed_rows_from_catalog_rights(by_right)
    except Exception as exc:
        raise ValueError(f"Preparazione catalogo TopTex: {exc}") from exc
    if not parsed_rows:
        raise ValueError(
            "Nessuna variante importabile da TopTex. "
            "Verifica usage_right, lang e prodotti active.",
        )
    try:
        stage_parsed_import_rows(sync_id, parsed_rows)
    except OSError as exc:
        raise ValueError(
            f"Impossibile salvare staging import (verifica permessi MEDIA): {exc}",
        ) from exc
    delete_toptex_catalog_staging(sync_id)
    return sync_id, parsed_rows, stats


def prepare_toptex_import_staging(
    client: TopTexClient | None = None,
) -> tuple[str, list[dict], dict[str, int]]:
    """Fetch TopTex (all usage rights), convert to parsed rows, stage on disk."""
    try:
        parsed_rows, stats = build_parsed_rows_from_toptex(client=client)
    except (TopTexAPIError, TopTexConfigError):
        raise
    except Exception as exc:
        raise ValueError(f"Preparazione catalogo TopTex: {exc}") from exc
    if not parsed_rows:
        raise ValueError(
            "Nessuna variante importabile da TopTex. "
            "Verifica usage_right, lang e prodotti active.",
        )
    sync_id = str(uuid.uuid4())
    try:
        stage_parsed_import_rows(sync_id, parsed_rows)
    except OSError as exc:
        raise ValueError(
            f"Impossibile salvare staging import (verifica permessi MEDIA): {exc}",
        ) from exc
    return sync_id, parsed_rows, stats
