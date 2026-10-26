"""CSV bulk product import with row-level validation."""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.text import slugify

from .constants import CLOTHING_SIZES
from .models import Brand, Category, Color, Product, ProductVariant


def _existing_product_names_it() -> set[str]:
    names: set[str] = set()
    for product in Product.objects.all():
        name = product.safe_translation_getter("name", language_code="it", any_language=True) or ""
        if name.strip():
            names.add(name.strip().lower())
    return names


def _existing_product_skus() -> set[str]:
    return {sku.strip().lower() for sku in Product.objects.values_list("sku", flat=True) if sku}


BRAND_FILTER_NONE = "__none__"

# Merceologica is often the supplier/brand (Payper, Kariban, …), not a category tree level.
_MERCEOLOGICA_SECTION_HINTS = (
    "abbigliamento",
    "calzatur",
    "accessori",
    "antinfort",
    "lavoro",
    "profession",
    "pulizia",
    "guanti",
    "sicurezza",
    "aliment",
    "industri",
    "ristor",
    "hotel",
    "sanitar",
    "divis",
)


def _is_merceologica_brand_name(raw: str) -> bool:
    cleaned = (raw or "").strip()
    if not cleaned:
        return False
    low = cleaned.lower()
    if any(hint in low for hint in _MERCEOLOGICA_SECTION_HINTS):
        return False
    return len(cleaned) <= 48


_CATEGORY_TYPE_WORDS = (
    "pantaloni",
    "pantalone",
    "polo",
    "t-shirt",
    "tshirt",
    "felpa",
    "giacca",
    "giubb",
    "camicia",
    "gilet",
    "bermuda",
    "shorts",
    "cappello",
    "scarpa",
    "calzatur",
    "boxer",
    "maglia",
    "softshell",
    "parka",
    "fleece",
    "pile",
    "cargo",
    "overall",
    "tuta",
    "cotone",
    "alta visibilit",
    "antinfort",
    "accessori",
)


def _categoria_value_is_brand(cat: str, mer: str, sub: str) -> bool:
    """Listino: brand often in Categoria when Merceologica is the macro family."""
    if not cat or not sub:
        return False
    low = cat.lower().strip()
    if any(word in low for word in _CATEGORY_TYPE_WORDS):
        return False
    if mer and _is_merceologica_brand_name(mer):
        return False
    if mer and not _is_merceologica_brand_name(mer):
        return _is_merceologica_brand_name(cat)
    return False


def canonical_filter_key(raw: str) -> str:
    if not raw or raw == BRAND_FILTER_NONE:
        return BRAND_FILTER_NONE
    text = unicodedata.normalize("NFKD", (raw or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("&amp;", "&")
    text = re.sub(r"\s+", "", text)
    return text or BRAND_FILTER_NONE


def canonical_brand_key(raw: str) -> str:
    return canonical_filter_key(raw)


def _row_brand_raw(row: dict) -> str:
    marca = _cell(row, "marca")
    if marca:
        return marca
    for key in ("marchio", "produttore", "fornitore", "vendor", "brand_name"):
        val = _cell(row, key)
        if val:
            return val
    mer = _cell(row, "merceologica")
    if mer and _is_merceologica_brand_name(mer):
        return mer
    cat = _cell(row, "categoria")
    sub = _cell(row, "scategoria")
    if _categoria_value_is_brand(cat, mer, sub):
        return cat
    return ""


def _product_brand_raw(row: dict, supplier_row: bool) -> str:
    """
    Brand saved on the product. Listino rows share one parent SKU across variants:
    use explicit marca / Merceologica brand only (not per-row Categoria guessing).
    """
    if not supplier_row:
        return _row_brand_raw(row)
    marca = _cell(row, "marca")
    if marca:
        return marca
    for key in ("marchio", "produttore", "fornitore", "vendor", "brand_name"):
        val = _cell(row, key)
        if val:
            return val
    mer = _cell(row, "merceologica")
    if mer and _is_merceologica_brand_name(mer):
        return mer
    return ""


def brand_filter_key(row: dict) -> str:
    raw = _row_brand_raw(row).strip()
    if not raw:
        return BRAND_FILTER_NONE
    return canonical_brand_key(raw)


def row_matches_brand_filter(row: dict, brand_keys_filter: set[str] | None) -> bool:
    if brand_keys_filter is None:
        return True
    row_key = brand_filter_key(row)
    if row_key in brand_keys_filter:
        return True
    raw = _row_brand_raw(row).strip()
    if raw and canonical_brand_key(raw) in brand_keys_filter:
        return True
    if raw and raw.strip().lower() in brand_keys_filter:
        return True
    return False


def brand_display_name(marca_raw: str) -> str:
    cleaned = (marca_raw or "").strip()
    return cleaned if cleaned else "Senza marca"


def filter_value_display_name(raw: str) -> str:
    cleaned = (raw or "").strip()
    return cleaned if cleaned else "(vuoto)"


def normalize_column_key(raw: str) -> str:
    return _normalize_header(raw or "")


def column_cell_raw(row: dict, column_key: str) -> str:
    """Value used for column filters (matches scan + import)."""
    if column_key == "marca":
        return (_cell(row, "marca") or _row_brand_raw(row)).strip()
    return _cell(row, column_key).strip()


def column_value_filter_key(row: dict, column_key: str) -> str:
    raw = column_cell_raw(row, column_key)
    if not raw:
        return BRAND_FILTER_NONE
    return canonical_filter_key(raw)


def row_matches_column_value_filter(
    row: dict,
    column_key: str,
    value_keys_filter: set[str] | None,
) -> bool:
    if value_keys_filter is None:
        return True
    raw = column_cell_raw(row, column_key)
    candidates = {
        column_value_filter_key(row, column_key),
        canonical_filter_key(raw),
        raw.strip().lower(),
        _header_key(raw),
    }
    for candidate in candidates:
        if candidate and candidate in value_keys_filter:
            return True
    return False


def _row_has_product_identity(row: dict) -> bool:
    """Loose check: row looks like a catalog line (used when listing column values)."""
    if _cell(row, "sku_prodotto") or _cell(row, "sku_variante"):
        return True
    if _cell(row, "ean"):
        return True
    name = _cell(row, "nome_it") or _cell(row, "descrizione_it")
    if name and (_cell(row, "prezzo") or _supplier_price_raw(row)):
        return True
    return False


def _treat_as_supplier_row(row: dict, supplier_format: bool) -> bool:
    if supplier_format:
        return True
    if _cell(row, "merceologica"):
        return True
    if _cell(row, "scategoria") and (_cell(row, "sku_prodotto") or _cell(row, "sku_variante")):
        return True
    if _cell(row, "sku_variante") and (_cell(row, "descrizione_it") or _cell(row, "nome_it")):
        if not _cell(row, "nome_en") and not _cell(row, "descrizione_en"):
            return True
    return False


PRICE_COLUMN_KEYS = (
    "prezzo",
    "prezzo_unico",
    "prezzo_confezione",
    "prezzo_imballo",
    "prezzo_listino",
    "prezzo_vendita",
    "prezzo_unitario",
    "prezzo_scontato",
)

_PRICE_KEY_HINTS = ("prezzo", "price", "listino", "importo", "retail", "wholesale", "pv")
_PRICE_SCAN_SKIP_KEYS = frozenset({
    "sku_prodotto", "sku_variante", "nome_it", "nome_en", "descrizione_it", "descrizione_en",
    "descrizione_breve_it", "descrizione_breve_en", "marca", "categoria", "scategoria",
    "merceologica", "colore", "taglia", "ean", "url_immagini", "url_mockup", "foto",
    "in_arrivo", "scorte", "bestseller", "ricamo_petto", "ricamo_grande", "dtf_petto",
    "dtf_grande", "costo_ricamo_petto", "costo_ricamo_grande", "costo_dtf_petto",
    "costo_dtf_grande", "costo_personalizzazione",
})


def _looks_like_price_string(value: str) -> bool:
    if not (value or "").strip():
        return False
    cleaned = _normalize_price_string(value)
    if not cleaned:
        return False
    try:
        Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return False
    return True


def _headers_include_price(normalized_headers: list[str]) -> bool:
    if any(h in normalized_headers for h in PRICE_COLUMN_KEYS):
        return True
    return any(
        "prezzo" in h or h in {"price", "listino", "importo", "pv"}
        for h in normalized_headers
    )


def _remember_row_price(cache: dict[str, str], row: dict, price_raw: str) -> None:
    if not price_raw or not _looks_like_price_string(price_raw):
        return
    for key in (
        _cell(row, "sku_prodotto"),
        _cell(row, "sku_variante"),
        _cell(row, "nome_it"),
        _cell(row, "descrizione_it"),
    ):
        token = key.strip().lower()
        if token:
            cache[token] = price_raw


def _build_row_price_cache(text: str) -> dict[str, str]:
    """First pass: collect prices keyed by parent SKU / variant / name (shared on variant rows)."""
    cache: dict[str, str] = {}
    reader = _csv_reader(text)
    for raw in reader:
        if not raw:
            continue
        row = _build_import_row(raw)
        _apply_derived_fields(row)
        price = _cell(row, "prezzo")
        if price and _looks_like_price_string(price):
            _remember_row_price(cache, row, price)
            continue
        found = _supplier_price_raw(row)
        if found:
            _remember_row_price(cache, row, found)
    return cache


def _resolve_row_price_raw(row: dict, price_cache: dict[str, str]) -> str:
    prezzo = _cell(row, "prezzo")
    if prezzo and _looks_like_price_string(prezzo):
        return prezzo
    found = _supplier_price_raw(row)
    if found:
        return found
    for token in (
        _cell(row, "sku_prodotto"),
        _cell(row, "sku_variante"),
        _cell(row, "nome_it"),
        _cell(row, "descrizione_it"),
    ):
        key = token.strip().lower()
        if key and key in price_cache:
            return price_cache[key]
    return ""


def _effective_price_raw(row: dict) -> str:
    return _resolve_row_price_raw(row, {})


def _row_eligible_for_import_scan(row: dict, supplier_format: bool) -> bool:
    """Rows that will likely produce an importable variant (counts in value scan)."""
    if not _row_has_product_identity(row):
        return False
    product_sku = _cell(row, "sku_prodotto") or _cell(row, "sku_variante")
    if not product_sku:
        return False
    supplier_like = _treat_as_supplier_row(row, supplier_format)
    price_raw = _effective_price_raw(row)
    if supplier_like:
        if not price_raw:
            return False
        if _parse_price(price_raw, "prezzo", 0, []) is None:
            return False
        return True
    if not _cell(row, "taglia") or not _cell(row, "colore"):
        return False
    if price_raw and _parse_price(price_raw, "prezzo", 0, []) is None:
        return False
    return True


def ensure_brand(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        return ""
    existing = Brand.objects.filter(name__iexact=cleaned).first()
    if existing:
        return existing.name
    created = Brand.objects.create(name=cleaned, is_active=True)
    return created.name


def ensure_color(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        return ""
    existing = Color.objects.filter(name__iexact=cleaned).first()
    if existing:
        return existing.name
    created = Color.objects.create(name=cleaned, is_active=True)
    return created.name


def _unique_product_sku(base_sku: str) -> str:
    sku = base_sku.strip()
    if not Product.objects.filter(sku__iexact=sku).exists():
        return sku
    counter = 2
    while Product.objects.filter(sku__iexact=f"{sku}-{counter}").exists():
        counter += 1
    return f"{sku}-{counter}"


def _unique_variant_sku(base_sku: str) -> str:
    sku = base_sku.strip()
    if not ProductVariant.objects.filter(sku__iexact=sku).exists():
        return sku
    counter = 2
    while ProductVariant.objects.filter(sku__iexact=f"{sku}-{counter}").exists():
        counter += 1
    return f"{sku}-{counter}"
from .product_images import (
    absolute_media_url,
    attach_image_from_url,
    attach_mockup_from_url,
    product_image_export_urls,
    split_url_list,
)

# Canonical Italian headers used in template / export.
CSV_HEADERS = [
    "sku_prodotto",
    "marca",
    "categoria",
    "nome_it",
    "nome_en",
    "descrizione_breve_it",
    "descrizione_breve_en",
    "descrizione_it",
    "descrizione_en",
    "bestseller",
    "costo_personalizzazione",
    "taglia",
    "colore",
    "prezzo",
    "scorte",
    "sku_variante",
    "prezzo_scontato",
    "ricamo_petto",
    "costo_ricamo_petto",
    "ricamo_grande",
    "costo_ricamo_grande",
    "dtf_petto",
    "costo_dtf_petto",
    "dtf_grande",
    "costo_dtf_grande",
    "url_immagini",
    "url_mockup",
]

# Accept legacy English / previous Italian headers and map them to Italian keys.
HEADER_ALIASES = {
    "product_sku": "sku_prodotto",
    "brand": "marca",
    "branch": "marca",
    "marchio": "marca",
    "produttore": "marca",
    "fornitore": "marca",
    "vendor": "marca",
    "brand_name": "marca",
    "name_it": "nome_it",
    "name_en": "nome_en",
    "short_description_it": "descrizione_breve_it",
    "short_description_en": "descrizione_breve_en",
    "descrizione_breve_it": "descrizione_breve_it",
    "descrizione_breve_en": "descrizione_breve_en",
    "description_it": "descrizione_it",
    "description_en": "descrizione_en",
    "is_bestseller": "bestseller",
    "bestseller": "bestseller",
    "best_seller": "bestseller",
    "customization_fee": "costo_personalizzazione",
    "size": "taglia",
    "color": "colore",
    "price": "prezzo",
    "listino": "prezzo",
    "importo": "prezzo",
    "valore": "prezzo",
    "pv": "prezzo",
    "selling_price": "prezzo",
    "retail_price": "prezzo",
    "wholesale_price": "prezzo",
    "prezzo_ivato": "prezzo",
    "prezzo_lordo": "prezzo",
    "prezzo_netto": "prezzo",
    "prezzo_di_vendita": "prezzo",
    "price_incl_tax": "prezzo",
    "price_excl_tax": "prezzo",
    "unit_price": "prezzo",
    "variation_price": "prezzo",
    "stock": "scorte",
    "variant_sku": "sku_variante",
    "slug_categorie": "categoria",
    "category_slugs": "categoria",
    "category": "categoria",
    "categories": "categoria",
    "sale_price": "prezzo_scontato",
    "allows_customization": "ricamo_petto",
    "personalizzazione": "ricamo_petto",
    "embroidery_chest": "ricamo_petto",
    "embroidery_chest_fee": "costo_ricamo_petto",
    "embroidery_large": "ricamo_grande",
    "embroidery_large_fee": "costo_ricamo_grande",
    "dtf_chest": "dtf_petto",
    "dtf_chest_fee": "costo_dtf_petto",
    "dtf_large": "dtf_grande",
    "dtf_large_fee": "costo_dtf_grande",
    "image_urls": "url_immagini",
    "images": "url_immagini",
    "mockup_url": "url_mockup",
    "mockup_front_url": "url_mockup",
    # Supplier catalogs (Codice Padre / SCategoria / Prezzo Unico, …)
    "codice_padre": "sku_prodotto",
    "codicepadre": "sku_prodotto",
    "parent_sku": "sku_prodotto",
    "parent_code": "sku_prodotto",
    "sku": "sku_variante",
    "ean": "ean",
    "gtin": "ean",
    "merceologica": "merceologica",
    "scategoria": "scategoria",
    "s_categoria": "scategoria",
    "sottocategoria": "scategoria",
    "subcategoria": "scategoria",
    "subcategory": "scategoria",
    "descrizione": "descrizione_it",
    "foto": "url_immagini",
    "immagine": "url_immagini",
    "immagini": "url_immagini",
    "prezzo_unitario": "prezzo",
    "prezzo_unico": "prezzo_unico",
    "prezzo_confezione": "prezzo_confezione",
    "prezzo_imballo": "prezzo_imballo",
    "prezzo_listino": "prezzo",
    "prezzo_vendita": "prezzo",
    "codice_articolo": "sku_variante",
    "cod_articolo": "sku_variante",
    "articolo": "sku_variante",
    "codice": "sku_variante",
    "riferimento": "sku_variante",
    "ref": "sku_variante",
    "in_arrivo": "in_arrivo",
}

SUPPLIER_FORMAT_MARKERS = {
    "codice_padre",
    "prezzo_unico",
    "prezzo_confezione",
    "prezzo_imballo",
    "merceologica",
    "scategoria",
    "in_arrivo",
}

METHOD_CSV_FIELDS = (
    ("ricamo_petto", "costo_ricamo_petto", "embroidery_chest_enabled", "embroidery_chest_fee"),
    ("ricamo_grande", "costo_ricamo_grande", "embroidery_large_enabled", "embroidery_large_fee"),
    ("dtf_petto", "costo_dtf_petto", "dtf_chest_enabled", "dtf_chest_fee"),
    ("dtf_grande", "costo_dtf_grande", "dtf_large_enabled", "dtf_large_fee"),
)

REQUIRED_FIELDS = [
    "sku_prodotto",
    "marca",
    "categoria",
    "nome_it",
    "nome_en",
    "descrizione_it",
    "descrizione_en",
    "taglia",
    "colore",
    "prezzo",
    "scorte",
]

TEMPLATE_EXAMPLE_ROWS = [
    {
        "sku_prodotto": "SW-POLO-01",
        "marca": "ExampleBrand",
        "nome_it": "Polo da lavoro",
        "nome_en": "Work polo",
        "descrizione_breve_it": "Polo operativa traspirante.",
        "descrizione_breve_en": "Breathable work polo.",
        "descrizione_it": "Polo resistente per uso professionale.",
        "descrizione_en": "Durable polo for professional use.",
        "bestseller": "no",
        "costo_personalizzazione": "5.00",
        "taglia": "M",
        "colore": "Blu",
        "prezzo": "29.90",
        "scorte": "10",
        "sku_variante": "SW-POLO-01-M-BLU",
        "categoria": "polo",
        "prezzo_scontato": "",
        "ricamo_petto": "si",
        "costo_ricamo_petto": "5.00",
        "ricamo_grande": "si",
        "costo_ricamo_grande": "12.00",
        "dtf_petto": "si",
        "costo_dtf_petto": "4.00",
        "dtf_grande": "no",
        "costo_dtf_grande": "",
        "url_immagini": "https://example.com/images/polo-blu-1.jpg,https://example.com/images/polo-blu-2.jpg",
        "url_mockup": "https://example.com/images/polo-blu-mockup.jpg",
    },
    {
        "sku_prodotto": "SW-POLO-01",
        "marca": "ExampleBrand",
        "nome_it": "Polo da lavoro",
        "nome_en": "Work polo",
        "descrizione_breve_it": "Polo operativa traspirante.",
        "descrizione_breve_en": "Breathable work polo.",
        "descrizione_it": "Polo resistente per uso professionale.",
        "descrizione_en": "Durable polo for professional use.",
        "bestseller": "no",
        "costo_personalizzazione": "5.00",
        "taglia": "L",
        "colore": "Blu",
        "prezzo": "29.90",
        "scorte": "8",
        "sku_variante": "SW-POLO-01-L-BLU",
        "categoria": "polo",
        "prezzo_scontato": "",
        "ricamo_petto": "si",
        "costo_ricamo_petto": "5.00",
        "ricamo_grande": "si",
        "costo_ricamo_grande": "12.00",
        "dtf_petto": "si",
        "costo_dtf_petto": "4.00",
        "dtf_grande": "no",
        "costo_dtf_grande": "",
        "url_immagini": "https://example.com/images/polo-blu-1.jpg,https://example.com/images/polo-blu-2.jpg",
        "url_mockup": "https://example.com/images/polo-blu-mockup.jpg",
    },
]


def build_csv_template() -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_HEADERS, lineterminator="\n")
    writer.writeheader()
    for row in TEMPLATE_EXAMPLE_ROWS:
        writer.writerow(row)
    return buffer.getvalue()


def _translation(product: Product, field: str, lang: str) -> str:
    return product.safe_translation_getter(field, language_code=lang, any_language=True) or ""


def _bool_to_csv(value: bool) -> str:
    return "si" if value else "no"


def export_products_csv() -> str:
    """Export all products as CSV (one row per variant), matching import columns."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_HEADERS, lineterminator="\n")
    writer.writeheader()

    products = (
        Product.objects.prefetch_related("variants", "categories", "images")
        .order_by("sku")
    )
    for product in products:
        category_slugs = ",".join(
            product.categories.order_by("slug").values_list("slug", flat=True)
        )
        image_urls = product_image_export_urls(product)
        mockup_url = absolute_media_url(product.mockup_front.url) if product.mockup_front else ""
        base = {
            "sku_prodotto": product.sku,
            "marca": product.brand or "",
            "nome_it": _translation(product, "name", "it"),
            "nome_en": _translation(product, "name", "en"),
            "descrizione_breve_it": _translation(product, "short_description", "it"),
            "descrizione_breve_en": _translation(product, "short_description", "en"),
            "descrizione_it": _translation(product, "description", "it"),
            "descrizione_en": _translation(product, "description", "en"),
            "bestseller": _bool_to_csv(bool(product.is_bestseller)),
            "costo_personalizzazione": f"{product.customization_fee:.2f}",
            "categoria": category_slugs,
            "ricamo_petto": _bool_to_csv(bool(product.embroidery_chest_enabled)),
            "costo_ricamo_petto": f"{product.embroidery_chest_fee:.2f}",
            "ricamo_grande": _bool_to_csv(bool(product.embroidery_large_enabled)),
            "costo_ricamo_grande": f"{product.embroidery_large_fee:.2f}",
            "dtf_petto": _bool_to_csv(bool(product.dtf_chest_enabled)),
            "costo_dtf_petto": f"{product.dtf_chest_fee:.2f}",
            "dtf_grande": _bool_to_csv(bool(product.dtf_large_enabled)),
            "costo_dtf_grande": f"{product.dtf_large_fee:.2f}",
            "url_immagini": ",".join(image_urls),
            "url_mockup": mockup_url,
        }
        variants = list(product.variants.all())
        if not variants:
            writer.writerow({
                **base,
                "taglia": "",
                "colore": "",
                "prezzo": "",
                "scorte": "",
                "sku_variante": "",
                "prezzo_scontato": "",
            })
            continue
        for variant in variants:
            writer.writerow({
                **base,
                "taglia": variant.size or "",
                "colore": variant.color or "",
                "prezzo": f"{variant.price:.2f}",
                "scorte": str(variant.stock_quantity),
                "sku_variante": variant.sku,
                "prezzo_scontato": f"{variant.sale_price:.2f}" if variant.sale_price is not None else "",
            })
    return buffer.getvalue()


def _header_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    return text


def _normalize_header(value: str) -> str:
    return HEADER_ALIASES.get(_header_key(value), _header_key(value))


def _build_import_row(raw: dict) -> dict:
    """Merge duplicate normalized headers; prefer numeric price over SKU-like text in price fields."""
    row: dict[str, str] = {}
    price_keys = frozenset(PRICE_COLUMN_KEYS)
    for key_raw, value in raw.items():
        if not key_raw:
            continue
        norm_key = _normalize_header(key_raw)
        val = (value or "").strip() if value is not None else ""
        if norm_key not in row:
            row[norm_key] = val
            continue
        existing = row[norm_key]
        if norm_key in price_keys:
            new_ok = _looks_like_price_string(val)
            old_ok = _looks_like_price_string(existing)
            if new_ok and not old_ok:
                row[norm_key] = val
            elif not old_ok and not new_ok:
                row[norm_key] = val
        else:
            row[norm_key] = val or existing
    return row


def _is_supplier_format(headers: list[str], raw_headers: list[str] | None = None) -> bool:
    header_set = set(headers)
    if header_set & SUPPLIER_FORMAT_MARKERS:
        return True
    raw_keys = {_header_key(h) for h in (raw_headers or [])}
    if raw_keys & {"prezzo_unico", "prezzo_confezione", "prezzo_imballo", "codice_padre"}:
        return True
    if raw_keys & {"foto", "immagine", "immagini"} and (
        "sku_variante" in header_set or "sku" in raw_keys
    ):
        return True
    if "sku_variante" in header_set and "descrizione_it" in header_set and "nome_it" not in header_set:
        return True
    native_markers = {
        "nome_en",
        "descrizione_en",
        "descrizione_breve_it",
        "descrizione_breve_en",
        "bestseller",
        "costo_personalizzazione",
        "ricamo_petto",
    }
    if (
        "sku_variante" in header_set
        and "sku_prodotto" in header_set
        and not (native_markers & header_set)
    ):
        return True
    if (
        ("descrizione_it" in header_set or "descrizione" in raw_keys)
        and ("sku_variante" in header_set or "sku" in raw_keys)
        and not (native_markers & header_set)
    ):
        return True
    return False


def _section_from_merceologica(raw: str) -> str:
    text = (raw or "").strip().lower()
    if any(token in text for token in ("profession", "divis", "sanitar", "hotel", "chef", "cuoco")):
        return Category.Section.PROFESSIONAL
    return Category.Section.WORKWEAR


def ensure_category(name: str, *, parent: Category | None = None, section: str | None = None) -> Category | None:
    cleaned = (name or "").strip()
    if not cleaned:
        return None
    slug = slugify(cleaned)[:200] or "category"
    existing = Category.objects.filter(slug=slug).first()
    if existing:
        return existing
    for cat in Category.objects.all():
        for lang in ("it", "en"):
            cat_name = cat.safe_translation_getter("name", language_code=lang, any_language=True) or ""
            if cat_name.strip().lower() == cleaned.lower():
                return cat
    section_value = section or (parent.section if parent else Category.Section.WORKWEAR)
    unique_slug = slug
    counter = 2
    while Category.objects.filter(slug=unique_slug).exists():
        unique_slug = f"{slug}-{counter}"[:200]
        counter += 1
    category = Category.objects.create(
        slug=unique_slug,
        section=section_value,
        parent=parent,
        is_active=True,
    )
    for lang in ("it", "en"):
        category.set_current_language(lang)
        category.name = cleaned
        category.save()
    return category


def _cell(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


def _merge_image_url_lists(*lists: list[str]) -> list[str]:
    """Stable union of image URLs (supplier rows often differ per color/size)."""
    seen: set[str] = set()
    merged: list[str] = []
    for urls in lists:
        for url in urls:
            if url and url not in seen:
                seen.add(url)
                merged.append(url)
    return merged


def _normalize_http_url(url: str) -> str:
    cleaned = (url or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    if cleaned.startswith("//"):
        return f"https:{cleaned}"
    if " " in cleaned:
        return cleaned
    if "." in cleaned:
        return f"https://{cleaned.lstrip('/')}"
    return cleaned


def _parse_http_urls(
    raw: str,
    field: str,
    row_num: int,
    errors: list[dict],
    *,
    strict: bool = True,
) -> list[str]:
    urls = split_url_list(raw)
    valid: list[str] = []
    for url in urls:
        normalized = _normalize_http_url(url)
        if normalized.startswith(("http://", "https://")):
            valid.append(normalized)
        elif strict and url.strip():
            errors.append({
                "row": row_num,
                "field": field,
                "message": f"URL non valido in {field}: '{url}'. Usa http:// o https://.",
            })
    return valid


def _suggest_variant_sku(product_sku: str, size: str, color: str) -> str:
    parts = [product_sku.strip()]
    if size:
        parts.append(size)
    if color:
        parts.append(color[:3].upper())
    return "-".join(p for p in parts if p)


def _normalize_price_string(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    raw = re.sub(r"(?i)^\s*(eur|€)\s*", "", raw)
    raw = re.sub(r"(?i)\s*eur\s*$", "", raw)
    raw = raw.replace("€", "").replace("\u00a0", "").replace(" ", "")
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    else:
        raw = raw.replace(",", ".")
    raw = re.sub(r"[^\d.\-]", "", raw)
    return raw


def _parse_price(value: str, field: str, row_num: int, errors: list[dict]) -> Decimal | None:
    if not value:
        return None
    cleaned = _normalize_price_string(value)
    if not cleaned:
        return None
    try:
        amount = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        errors.append({"row": row_num, "field": field, "message": f"{field} non valido: '{value}'."})
        return None
    if amount < 0:
        errors.append({"row": row_num, "field": field, "message": f"{field} non può essere negativo."})
        return None
    return amount


def _parse_stock(
    value: str,
    row_num: int,
    errors: list[dict],
    *,
    required: bool = True,
) -> int | None:
    if value == "":
        if required:
            errors.append({"row": row_num, "field": "scorte", "message": "scorte è obbligatorio."})
            return None
        return 0
    try:
        stock = int(value)
    except ValueError:
        errors.append({"row": row_num, "field": "scorte", "message": f"scorte non valido: '{value}'."})
        return None
    if stock < 0:
        errors.append({"row": row_num, "field": "scorte", "message": "scorte non può essere negativo."})
        return None
    return stock


def _parse_bool(value: str, field: str, row_num: int, errors: list[dict], default: bool = False) -> bool | None:
    if not value:
        return default
    normalized = value.strip().lower()
    if normalized in {"si", "sì", "s", "yes", "y", "true", "1"}:
        return True
    if normalized in {"no", "n", "false", "0"}:
        return False
    errors.append({
        "row": row_num,
        "field": field,
        "message": f"{field} non valido: '{value}'. Usa si/no.",
    })
    return None


def _parse_customization_enabled(value: str) -> bool:
    """Wholesale sheets often put max print size in ricamo/dtf columns instead of si/no."""
    raw = (value or "").strip()
    if not raw:
        return False
    normalized = raw.lower()
    if normalized in {"si", "sì", "s", "yes", "y", "true", "1"}:
        return True
    if normalized in {"no", "n", "false", "0"}:
        return False
    if any(token in normalized for token in ("formato", "max ", " cm", "a4", "x10", "x15", "x20")):
        return True
    return False


def _row_has_category_value(row: dict) -> bool:
    return any(
        _cell(row, key)
        for key in (
            "categoria",
            "scategoria",
            "merceologica",
            "famiglia",
            "linea",
            "reparto",
            "macro_categoria",
            "categoria_principale",
        )
    )


def _missing_native_headers(normalized_headers: list[str]) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        if field in normalized_headers:
            continue
        if field == "categoria" and any(
            key in normalized_headers
            for key in (
                "scategoria",
                "merceologica",
                "slug_categorie",
                "category",
                "categories",
                "famiglia",
                "linea",
                "reparto",
                "macro_categoria",
                "categoria_principale",
            )
        ):
            continue
        missing.append(field)
    return missing


def _category_lookup_maps() -> tuple[dict[str, Category], dict[str, Category]]:
    by_slug: dict[str, Category] = {}
    by_name: dict[str, Category] = {}
    for cat in Category.objects.filter(is_active=True):
        by_slug[cat.slug.lower()] = cat
        for lang in ("it", "en"):
            name = cat.safe_translation_getter("name", language_code=lang, any_language=True) or ""
            key = name.strip().lower()
            if key:
                by_name[key] = cat
    return by_slug, by_name


def _resolve_category_ids(
    raw: str,
    by_slug: dict[str, Category],
    by_name: dict[str, Category],
    row_num: int,
    errors: list[dict],
    *,
    auto_create: bool = False,
) -> list[int]:
    if not raw:
        if auto_create:
            default = ensure_category("Generale")
            return [default.id] if default else []
        return []
    ids: list[int] = []
    for token in [s.strip() for s in raw.replace(";", ",").split(",") if s.strip()]:
        key = token.lower()
        cat = by_slug.get(key) or by_name.get(key)
        if cat:
            ids.append(cat.id)
            continue
        if auto_create:
            created = ensure_category(token)
            if created:
                ids.append(created.id)
                by_slug[created.slug.lower()] = created
                for lang in ("it", "en"):
                    name = created.safe_translation_getter("name", language_code=lang, any_language=True) or ""
                    if name.strip():
                        by_name[name.strip().lower()] = created
            continue
        errors.append({
            "row": row_num,
            "field": "categoria",
            "message": (
                f"Categoria non trovata: '{token}'. "
                "Usa lo slug (es. polo, t-shirt) o il nome IT/EN della categoria."
            ),
        })
    return ids


def _decode_csv_bytes(file_bytes: bytes) -> tuple[str | None, dict | None]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return file_bytes.decode(encoding), None
        except UnicodeDecodeError:
            continue
    return None, {"row": 0, "field": "file", "message": "Il CSV deve essere UTF-8 o Windows-1252."}


def _csv_reader(text: str) -> csv.DictReader:
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
        if sample.count(";") > sample.count(","):
            dialect.delimiter = ";"
    return csv.DictReader(io.StringIO(text), dialect=dialect)


def _supplier_price_raw(row: dict) -> str:
    for key in PRICE_COLUMN_KEYS:
        value = _cell(row, key)
        if value and _looks_like_price_string(value):
            return value
    for key, value in row.items():
        if key in _PRICE_SCAN_SKIP_KEYS:
            continue
        if not any(hint in key for hint in _PRICE_KEY_HINTS):
            continue
        if key.startswith("costo_"):
            continue
        text = (value or "").strip()
        if text and _looks_like_price_string(text):
            return text
    return ""


def _first_parseable_price(row: dict, row_num: int) -> Decimal | None:
    seen: set[str] = set()
    for key in PRICE_COLUMN_KEYS:
        value = _cell(row, key)
        if not value or value in seen:
            continue
        if not _looks_like_price_string(value):
            continue
        seen.add(value)
        parsed = _parse_price(value, "prezzo", row_num, [])
        if parsed is not None:
            return parsed
    return None


def _apply_derived_fields(row: dict) -> None:
    if not _cell(row, "sku_prodotto"):
        row["sku_prodotto"] = _cell(row, "sku_variante")
    if not _cell(row, "nome_it"):
        row["nome_it"] = _cell(row, "descrizione_it")
    if not _cell(row, "descrizione_it"):
        row["descrizione_it"] = _cell(row, "nome_it")
    if not _cell(row, "nome_en"):
        row["nome_en"] = _cell(row, "nome_it")
    if not _cell(row, "descrizione_en"):
        row["descrizione_en"] = _cell(row, "descrizione_it")
    current_prezzo = _cell(row, "prezzo")
    if not current_prezzo or not _looks_like_price_string(current_prezzo):
        derived = _supplier_price_raw(row)
        if derived:
            row["prezzo"] = derived
        elif current_prezzo and not _looks_like_price_string(current_prezzo):
            row["prezzo"] = ""
    if not _cell(row, "marca"):
        inferred_brand = _row_brand_raw(row)
        if inferred_brand:
            row["marca"] = inferred_brand
    if not _cell(row, "categoria"):
        mer_for_category = _cell(row, "merceologica")
        if mer_for_category and _is_merceologica_brand_name(mer_for_category):
            mer_for_category = ""
        row["categoria"] = (
            _cell(row, "scategoria")
            or _cell(row, "famiglia")
            or _cell(row, "linea")
            or _cell(row, "reparto")
            or _cell(row, "macro_categoria")
            or _cell(row, "categoria_principale")
            or mer_for_category
        )
    if not _cell(row, "scorte"):
        incoming = _cell(row, "in_arrivo")
        if incoming.isdigit():
            row["scorte"] = incoming


def _supplier_category_names(row: dict) -> tuple[str, str, str]:
    mer = _cell(row, "merceologica")
    mer_for_section = mer
    if mer and _is_merceologica_brand_name(mer):
        mer_for_section = ""
    parent = _cell(row, "categoria")
    child = _cell(row, "scategoria")
    if not parent and not child:
        if mer_for_section:
            parent = mer_for_section
        else:
            for key in (
                "famiglia",
                "linea",
                "reparto",
                "macro_categoria",
                "categoria_principale",
            ):
                val = _cell(row, key)
                if val:
                    parent = val
                    break
    if not parent and not child:
        parent = "Generale"
    return (mer_for_section, parent, child)


def _uses_supplier_category_tree(row: dict, supplier: bool) -> bool:
    if supplier:
        return True
    return bool(_cell(row, "merceologica") or _cell(row, "scategoria"))


def _resolve_row_categories(
    row: dict,
    *,
    supplier: bool,
    by_slug: dict[str, Category],
    by_name: dict[str, Category],
    row_num: int,
    errors: list[dict],
) -> list[int]:
    if _uses_supplier_category_tree(row, supplier):
        # Supplier/listino categories are created at import from supplier_category fields.
        return []
    return _resolve_category_ids(
        _cell(row, "categoria"),
        by_slug,
        by_name,
        row_num,
        errors,
        auto_create=True,
    )


def scan_csv_brands(file_bytes: bytes) -> tuple[list[dict], list[dict]]:
    """Scan CSV for distinct marca values (no full validation). Returns (brands, errors)."""
    errors: list[dict] = []
    text, decode_error = _decode_csv_bytes(file_bytes)
    if decode_error:
        return [], [decode_error]

    reader = _csv_reader(text)
    if not reader.fieldnames:
        return [], [{"row": 0, "field": "file", "message": "Il CSV non ha una riga di intestazione."}]

    raw_headers = [h for h in reader.fieldnames if h is not None]
    normalized_headers = [_normalize_header(h) for h in raw_headers]
    supplier_format = _is_supplier_format(normalized_headers, raw_headers)

    product_ids: dict[str, set[str]] = defaultdict(set)
    row_counts: dict[str, int] = defaultdict(int)
    labels: dict[str, str] = {}

    for raw in reader:
        row = _build_import_row(raw)
        _apply_derived_fields(row)
        if not _row_has_product_identity(row):
            continue
        product_sku = _cell(row, "sku_prodotto") or _cell(row, "sku_variante")
        marca_raw = _row_brand_raw(row)
        key = brand_filter_key(row)
        if key not in labels:
            labels[key] = brand_display_name(marca_raw)
        product_ids[key].add(product_sku.lower())
        row_counts[key] += 1

    if not product_ids:
        return [], [{"row": 0, "field": "file", "message": "Nessuna riga prodotto trovata nel CSV."}]

    brands = [
        {
            "key": key,
            "name": labels[key],
            "product_count": len(product_ids[key]),
            "row_count": row_counts[key],
        }
        for key in sorted(labels.keys(), key=lambda k: labels[k].lower())
    ]
    return brands, []


def _csv_header_context(file_bytes: bytes) -> tuple[list[str], list[str], list[dict]]:
    """Return (raw_headers, normalized_headers, errors)."""
    text, decode_error = _decode_csv_bytes(file_bytes)
    if decode_error:
        return [], [], [decode_error]
    reader = _csv_reader(text)
    if not reader.fieldnames:
        return [], [], [{
            "row": 0,
            "field": "file",
            "message": "Il CSV non ha una riga di intestazione.",
        }]
    raw_headers = [h for h in reader.fieldnames if h is not None]
    normalized_headers = [_normalize_header(h) for h in raw_headers]
    return raw_headers, normalized_headers, []


def scan_csv_columns(file_bytes: bytes) -> tuple[list[dict], list[dict]]:
    """Distinct CSV columns (normalized key + original header label)."""
    raw_headers, normalized_headers, errors = _csv_header_context(file_bytes)
    if errors:
        return [], errors
    columns: list[dict] = []
    seen: set[str] = set()
    for raw_h, norm_h in zip(raw_headers, normalized_headers, strict=True):
        if not norm_h or norm_h in seen:
            continue
        seen.add(norm_h)
        label = (raw_h or "").strip() or norm_h
        columns.append({"key": norm_h, "label": label})
    if _is_supplier_format(normalized_headers, raw_headers) and "marca" not in seen:
        columns.append({
            "key": "marca",
            "label": "marca (ricavata dal listino)",
        })
    columns.sort(key=lambda c: c["label"].lower())
    return columns, []


def _iter_scannable_product_rows(file_bytes: bytes):
    """
    Yield row dicts used for column-value scans (supplier price/sku rules).
    Returns (iterator, errors).
    """
    text, decode_error = _decode_csv_bytes(file_bytes)
    if decode_error:
        return iter(()), [decode_error]

    reader = _csv_reader(text)
    if not reader.fieldnames:
        return iter(()), [{
            "row": 0,
            "field": "file",
            "message": "Il CSV non ha una riga di intestazione.",
        }]

    raw_headers = [h for h in reader.fieldnames if h is not None]
    normalized_headers = [_normalize_header(h) for h in raw_headers]
    supplier_format = _is_supplier_format(normalized_headers, raw_headers)

    def gen():
        for raw in reader:
            row = _build_import_row(raw)
            _apply_derived_fields(row)
            if not _row_has_product_identity(row):
                continue
            yield row

    return gen(), []


def scan_csv_column_values(file_bytes: bytes, column_key: str) -> tuple[list[dict], list[dict]]:
    """Distinct values in one column with product/row counts."""
    norm_key = normalize_column_key(column_key)
    if not norm_key:
        return [], [{"row": 0, "field": "column", "message": "Colonna non valida."}]

    _, normalized_headers, header_errors = _csv_header_context(file_bytes)
    if header_errors:
        return [], header_errors
    if norm_key not in normalized_headers and norm_key != "marca":
        return [], [{
            "row": 0,
            "field": "column",
            "message": f"Colonna '{column_key}' non trovata nel CSV.",
        }]

    product_ids: dict[str, set[str]] = defaultdict(set)
    row_counts: dict[str, int] = defaultdict(int)
    labels: dict[str, str] = {}

    rows_iter, errors = _iter_scannable_product_rows(file_bytes)
    if errors:
        return [], errors

    for row in rows_iter:
        raw_val = column_cell_raw(row, norm_key)
        key = column_value_filter_key(row, norm_key)
        if key not in labels:
            labels[key] = filter_value_display_name(raw_val)
        product_sku = _cell(row, "sku_prodotto") or _cell(row, "sku_variante")
        product_ids[key].add(product_sku.lower())
        row_counts[key] += 1

    if not product_ids:
        return [], [{
            "row": 0,
            "field": "file",
            "message": (
                "Nessuna riga prodotto trovata nel CSV. "
                "Servono almeno colonne tipo Codice Padre/SKU, Descrizione e Prezzo."
            ),
        }]

    values = [
        {
            "key": key,
            "name": labels[key],
            "product_count": len(product_ids[key]),
            "row_count": row_counts[key],
        }
        for key in sorted(labels.keys(), key=lambda k: labels[k].lower())
    ]
    return values, []


def parse_and_validate_csv(
    file_bytes: bytes,
    *,
    progress_callback: Callable[[int, int], None] | None = None,
    progress_total: int | None = None,
    brand_keys_filter: set[str] | None = None,
    column_value_filter: tuple[str, set[str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Return (parsed_rows, errors). parsed_rows is empty when errors exist."""
    errors: list[dict] = []
    text, decode_error = _decode_csv_bytes(file_bytes)
    if decode_error:
        return [], [decode_error]

    reader = _csv_reader(text)
    if not reader.fieldnames:
        return [], [{"row": 0, "field": "file", "message": "Il CSV non ha una riga di intestazione."}]

    raw_headers = [h for h in reader.fieldnames if h is not None]
    normalized_headers = [_normalize_header(h) for h in raw_headers]
    supplier_format = _is_supplier_format(normalized_headers, raw_headers)
    if supplier_format:
        has_product_id = any(h in normalized_headers for h in ("sku_prodotto", "sku_variante"))
        has_name = any(h in normalized_headers for h in ("nome_it", "descrizione_it"))
        has_price = _headers_include_price(normalized_headers)
        missing_headers = []
        if not has_product_id:
            missing_headers.append("Codice Padre o SKU")
        if not has_name:
            missing_headers.append("Descrizione")
        if not has_price:
            missing_headers.append("Prezzo Unico")
    else:
        missing_headers = _missing_native_headers(normalized_headers)
    if missing_headers:
        return [], [{
            "row": 0,
            "field": "headers",
            "message": f"Colonne obbligatorie mancanti: {', '.join(missing_headers)}.",
        }]

    categories_by_slug, categories_by_name = _category_lookup_maps()
    existing_names_it = _existing_product_names_it()
    existing_skus = _existing_product_skus()
    csv_name_to_sku: dict[str, str] = {}
    reported_existing_parent_skus: set[str] = set()

    parsed_rows: list[dict] = []
    seen_variant_skus: dict[str, int] = {}
    supplier_variant_row_index: dict[str, int] = {}
    product_meta: dict[str, dict] = {}
    product_size_colors: dict[str, dict[tuple[str, str], int]] = defaultdict(dict)

    estimated_rows = progress_total
    if estimated_rows is None:
        estimated_rows = max(1, file_bytes.count(b"\n") - 1)

    row_price_cache = _build_row_price_cache(text)
    reader = _csv_reader(text)

    column_filter_matched_rows = 0
    column_filter_matched_row_nums: set[int] = set()

    for index, raw in enumerate(reader, start=2):  # header is row 1
        row = _build_import_row(raw)
        row_num = index
        _apply_derived_fields(row)
        supplier_row = _treat_as_supplier_row(row, supplier_format)

        if column_value_filter is not None:
            col_key, value_keys = column_value_filter
            if not row_matches_column_value_filter(row, col_key, value_keys):
                continue
            column_filter_matched_rows += 1
            column_filter_matched_row_nums.add(row_num)
            supplier_row = True
            if not _cell(row, "sku_prodotto") and _cell(row, "sku_variante"):
                row["sku_prodotto"] = _cell(row, "sku_variante")
        elif not row_matches_brand_filter(row, brand_keys_filter):
            continue

        price_raw = _resolve_row_price_raw(row, row_price_cache)
        if price_raw:
            row["prezzo"] = price_raw
            _remember_row_price(row_price_cache, row, price_raw)
        if supplier_row and not price_raw:
            continue

        required_now = ["sku_prodotto", "nome_it", "descrizione_it"]
        if not supplier_row:
            required_now = list(REQUIRED_FIELDS)
        for field in required_now:
            if field == "categoria":
                # Resolved later (slug, auto-create, or default "Generale").
                continue
            if not _cell(row, field):
                errors.append({"row": row_num, "field": field, "message": f"{field} è obbligatorio."})

        product_sku = _cell(row, "sku_prodotto") or _cell(row, "sku_variante")
        brand_raw = _product_brand_raw(row, supplier_row)
        if product_sku:
            meta_key = product_sku.lower()
            if meta_key in product_meta and product_meta[meta_key].get("marca"):
                brand_raw = product_meta[meta_key]["marca"]
        name_it = _cell(row, "nome_it")
        name_en = _cell(row, "nome_en")
        description_it = _cell(row, "descrizione_it")
        description_en = _cell(row, "descrizione_en")
        short_description_it = _cell(row, "descrizione_breve_it")
        short_description_en = _cell(row, "descrizione_breve_en")
        bestseller_raw = _cell(row, "bestseller")
        size_raw = _cell(row, "taglia")
        color_raw = _cell(row, "colore")
        if supplier_row:
            if not size_raw:
                size_raw = "UNICA"
            if not color_raw:
                color_raw = "UNICO"
        size = size_raw.upper() if size_raw.upper() in CLOTHING_SIZES else size_raw
        stock_raw = _cell(row, "scorte")
        variant_sku = _cell(row, "sku_variante")
        category_slugs_raw = _cell(row, "categoria")
        sale_price_raw = _cell(row, "prezzo_scontato")

        if product_sku and supplier_row:
            parent_key = product_sku.lower()
            if parent_key in existing_skus and parent_key not in reported_existing_parent_skus:
                reported_existing_parent_skus.add(parent_key)
                errors.append({
                    "row": row_num,
                    "field": "sku_prodotto",
                    "message": (
                        f"Il Codice Padre '{product_sku}' esiste già nel catalogo. "
                        "Rimuovilo dal CSV o elimina/disattiva il prodotto esistente."
                    ),
                })
        elif name_it and product_sku:
            name_key = name_it.strip().lower()
            if name_key in existing_names_it:
                errors.append({
                    "row": row_num,
                    "field": "nome_it",
                    "message": f"Il nome prodotto '{name_it}' esiste già nel catalogo.",
                })
            if name_key:
                csv_name_to_sku[name_key] = product_sku.lower()

        if supplier_row:
            price = _first_parseable_price(row, row_num)
            if price is None:
                continue
            _remember_row_price(row_price_cache, row, price_raw)
        else:
            price = _parse_price(price_raw, "prezzo", row_num, errors) if price_raw else None
        if stock_raw != "":
            stock = _parse_stock(stock_raw, row_num, errors, required=not supplier_row)
        else:
            stock = _parse_stock("", row_num, errors, required=not supplier_row)

        sale_price = None
        if sale_price_raw:
            sale_price = _parse_price(sale_price_raw, "prezzo_scontato", row_num, errors)

        method_values: dict[str, bool | Decimal] = {}
        method_parse_ok = True
        for enabled_csv, fee_csv, enabled_attr, fee_attr in METHOD_CSV_FIELDS:
            enabled = _parse_customization_enabled(_cell(row, enabled_csv))
            fee = Decimal("0.00")
            fee_raw = _cell(row, fee_csv)
            if fee_raw:
                parsed_fee = _parse_price(fee_raw, fee_csv, row_num, [])
                if parsed_fee is not None:
                    fee = parsed_fee
            method_values[enabled_attr] = bool(enabled)
            method_values[fee_attr] = fee

        allows_customization = any(
            method_values[enabled_attr]
            for _, _, enabled_attr, _ in METHOD_CSV_FIELDS
        )
        enabled_fees = [
            method_values[fee_attr]
            for _, _, enabled_attr, fee_attr in METHOD_CSV_FIELDS
            if method_values[enabled_attr]
        ]
        customization_fee = min(enabled_fees) if enabled_fees else Decimal("0.00")
        customization_fee_raw = _cell(row, "costo_personalizzazione")
        if customization_fee_raw:
            parsed_product_fee = _parse_price(
                customization_fee_raw, "costo_personalizzazione", row_num, errors,
            )
            if parsed_product_fee is not None:
                customization_fee = parsed_product_fee

        is_bestseller = _parse_bool(bestseller_raw, "bestseller", row_num, errors, default=False)
        if is_bestseller is None:
            method_parse_ok = False
            is_bestseller = False

        category_ids = _resolve_row_categories(
            row,
            supplier=supplier_row,
            by_slug=categories_by_slug,
            by_name=categories_by_name,
            row_num=row_num,
            errors=errors,
        )
        merceologica, category_name, subcategory_name = _supplier_category_names(row)

        if not variant_sku and product_sku:
            variant_sku = _suggest_variant_sku(product_sku, size, color_raw)

        supplier_variant_duplicate = bool(
            supplier_row
            and variant_sku
            and variant_sku.lower() in supplier_variant_row_index
        )
        if variant_sku and not supplier_row:
            key = variant_sku.lower()
            if key in seen_variant_skus:
                errors.append({
                    "row": row_num,
                    "field": "sku_variante",
                    "message": (
                        f"Lo SKU variante '{variant_sku}' è duplicato nel CSV "
                        f"(anche alla riga {seen_variant_skus[key]})."
                    ),
                })
            else:
                seen_variant_skus[key] = row_num

        if product_sku and size and color_raw:
            pair = (size.lower(), color_raw.lower())
            prev = product_size_colors[product_sku.lower()].get(pair)
            if prev and not (supplier_row and supplier_variant_duplicate):
                errors.append({
                    "row": row_num,
                    "field": "taglia",
                    "message": (
                        f"Taglia '{size}' + colore '{color_raw}' è duplicata "
                        f"per il prodotto '{product_sku}' (anche alla riga {prev})."
                    ),
                })
            elif not prev:
                product_size_colors[product_sku.lower()][pair] = row_num

        image_urls = _parse_http_urls(
            _cell(row, "url_immagini"),
            "url_immagini",
            row_num,
            errors,
            strict=not supplier_row,
        )
        mockup_urls = _parse_http_urls(_cell(row, "url_mockup"), "url_mockup", row_num, errors)
        mockup_url = mockup_urls[0] if mockup_urls else ""
        if len(mockup_urls) > 1:
            errors.append({
                "row": row_num,
                "field": "url_mockup",
                "message": "url_mockup accetta un solo URL.",
            })

        if product_sku:
            meta_key = product_sku.lower()
            current = {
                "marca": brand_raw,
                "nome_it": name_it,
                "nome_en": name_en,
                "descrizione_breve_it": short_description_it,
                "descrizione_breve_en": short_description_en,
                "descrizione_it": description_it,
                "descrizione_en": description_en,
                "is_bestseller": is_bestseller,
                "category_ids": category_ids,
                "allows_customization": allows_customization,
                "customization_fee": customization_fee,
                "image_urls": image_urls,
                "mockup_url": mockup_url,
                **method_values,
            }
            if meta_key in product_meta:
                prev = product_meta[meta_key]
                for field in (
                    "marca", "nome_it", "nome_en",
                    "descrizione_breve_it", "descrizione_breve_en",
                    "descrizione_it", "descrizione_en",
                    "is_bestseller",
                ):
                    if field == "marca" and supplier_row:
                        if not prev.get("marca") and current.get("marca"):
                            prev["marca"] = current["marca"]
                        continue
                    if prev.get(field) and current.get(field) and prev[field] != current[field]:
                        errors.append({
                            "row": row_num,
                            "field": field,
                            "message": (
                                f"{field} per il prodotto '{product_sku}' non corrisponde a una riga precedente "
                                f"('{prev[field]}' vs '{current[field]}')."
                            ),
                        })
                if prev.get("category_ids") and category_ids and set(prev["category_ids"]) != set(category_ids):
                    errors.append({
                        "row": row_num,
                        "field": "categoria",
                        "message": f"categoria per il prodotto '{product_sku}' non corrisponde a una riga precedente.",
                    })
                for enabled_csv, fee_csv, enabled_attr, fee_attr in METHOD_CSV_FIELDS:
                    if prev.get(enabled_attr) != current.get(enabled_attr):
                        errors.append({
                            "row": row_num,
                            "field": enabled_csv,
                            "message": f"{enabled_csv} per il prodotto '{product_sku}' non corrisponde a una riga precedente.",
                        })
                    if prev.get(fee_attr) != current.get(fee_attr):
                        errors.append({
                            "row": row_num,
                            "field": fee_csv,
                            "message": f"{fee_csv} per il prodotto '{product_sku}' non corrisponde a una riga precedente.",
                        })
                if prev.get("customization_fee") != current.get("customization_fee"):
                    errors.append({
                        "row": row_num,
                        "field": "costo_personalizzazione",
                        "message": (
                            f"costo_personalizzazione per il prodotto '{product_sku}' "
                            "non corrisponde a una riga precedente."
                        ),
                    })
                if prev.get("image_urls") and image_urls and prev["image_urls"] != image_urls:
                    if supplier_row:
                        prev["image_urls"] = _merge_image_url_lists(
                            prev["image_urls"],
                            image_urls,
                        )
                    else:
                        errors.append({
                            "row": row_num,
                            "field": "url_immagini",
                            "message": (
                                f"url_immagini per il prodotto '{product_sku}' "
                                "non corrisponde a una riga precedente."
                            ),
                        })
                if prev.get("mockup_url") and mockup_url and prev["mockup_url"] != mockup_url:
                    if not supplier_row:
                        errors.append({
                            "row": row_num,
                            "field": "url_mockup",
                            "message": (
                                f"url_mockup per il prodotto '{product_sku}' "
                                "non corrisponde a una riga precedente."
                            ),
                        })
                if not prev.get("image_urls") and image_urls:
                    prev["image_urls"] = image_urls
                if not prev.get("mockup_url") and mockup_url:
                    prev["mockup_url"] = mockup_url
            else:
                product_meta[meta_key] = current

        if (
            not product_sku
            or price is None
            or stock is None
            or not method_parse_ok
        ):
            if row_num in column_filter_matched_row_nums:
                if not product_sku:
                    errors.append({
                        "row": row_num,
                        "field": "sku_prodotto",
                        "message": "Codice Padre o SKU mancante.",
                    })
                elif price is None:
                    errors.append({
                        "row": row_num,
                        "field": "prezzo",
                        "message": "Prezzo mancante o non valido.",
                    })
                elif stock is None:
                    errors.append({
                        "row": row_num,
                        "field": "scorte",
                        "message": "Scorte non valide.",
                    })
            continue
        if not supplier_row and (not size or not color_raw):
            if row_num in column_filter_matched_row_nums:
                errors.append({
                    "row": row_num,
                    "field": "taglia",
                    "message": "Taglia e colore sono obbligatori per questo formato CSV.",
                })
            continue

        meta = product_meta.get(product_sku.lower(), {})
        parsed_row = {
            "row": row_num,
            "product_sku": product_sku,
            "brand": brand_raw,
            "name_it": name_it,
            "name_en": name_en,
            "short_description_it": short_description_it,
            "short_description_en": short_description_en,
            "description_it": description_it,
            "description_en": description_en,
            "is_bestseller": is_bestseller,
            "size": size,
            "color": color_raw,
            "price": price,
            "stock": stock,
            "sale_price": sale_price,
            "variant_sku": variant_sku,
            "category_ids": category_ids,
            "supplier_section": (
                _section_from_merceologica(
                    merceologica or f"{category_name} {subcategory_name}".strip(),
                )
                if supplier_row
                else ""
            ),
            "supplier_category": category_name if supplier_row else "",
            "supplier_subcategory": subcategory_name if supplier_row else "",
            "allows_customization": allows_customization,
            "customization_fee": customization_fee,
            "image_urls": meta.get("image_urls") or image_urls,
            "mockup_url": meta.get("mockup_url") or mockup_url,
            **method_values,
        }
        if supplier_row and variant_sku:
            variant_key = variant_sku.lower()
            if variant_key in supplier_variant_row_index:
                parsed_rows[supplier_variant_row_index[variant_key]] = parsed_row
                continue
            supplier_variant_row_index[variant_key] = len(parsed_rows)
        parsed_rows.append(parsed_row)

        if progress_callback and index % 500 == 0:
            progress_callback(min(index - 1, estimated_rows), estimated_rows)

    if progress_callback:
        progress_callback(estimated_rows, estimated_rows)

    if errors:
        errors.sort(key=lambda e: (e.get("row") or 0, e.get("field") or ""))
        return [], errors

    if not parsed_rows:
        if column_value_filter is not None:
            col_key, _value_keys = column_value_filter
            if column_filter_matched_rows > 0:
                message = (
                    "Le righe con i valori selezionati non sono importabili "
                    "(controlla prezzo, SKU, taglia/colore e altri campi obbligatori)."
                )
            else:
                message = "Nessuna riga da importare per i valori selezionati."
            return [], [{
                "row": 0,
                "field": col_key,
                "message": message,
            }]
        if brand_keys_filter is not None:
            return [], [{
                "row": 0,
                "field": "marca",
                "message": "Nessuna riga da importare per le marche selezionate.",
            }]
        return [], [{"row": 0, "field": "file", "message": "Il CSV non contiene righe di dati."}]

    for row in parsed_rows:
        meta = product_meta.get(row["product_sku"].lower(), {})
        if meta.get("image_urls"):
            row["image_urls"] = meta["image_urls"]
        if meta.get("mockup_url"):
            row["mockup_url"] = meta["mockup_url"]

    return parsed_rows, []


def _import_one_product_group(rows: list[dict]) -> tuple[int, int]:
    """Create one product and its variants. Returns (variants_created, 1 product)."""
    first = rows[0]
    brand_name = ensure_brand(first["brand"])
    base_slug = slugify(first["name_it"])[:240] or slugify(first["product_sku"])[:240] or "product"
    slug = base_slug
    counter = 1
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    product_sku = _unique_product_sku(first["product_sku"])

    product = Product.objects.create(
        sku=product_sku,
        brand=brand_name,
        slug=slug,
        is_active=True,
        is_bestseller=bool(first.get("is_bestseller")),
        allows_customization=bool(first.get("allows_customization")),
        customization_fee=first.get("customization_fee") or Decimal("0.00"),
        embroidery_chest_enabled=bool(first.get("embroidery_chest_enabled")),
        embroidery_chest_fee=first.get("embroidery_chest_fee") or Decimal("0.00"),
        embroidery_large_enabled=bool(first.get("embroidery_large_enabled")),
        embroidery_large_fee=first.get("embroidery_large_fee") or Decimal("0.00"),
        dtf_chest_enabled=bool(first.get("dtf_chest_enabled")),
        dtf_chest_fee=first.get("dtf_chest_fee") or Decimal("0.00"),
        dtf_large_enabled=bool(first.get("dtf_large_enabled")),
        dtf_large_fee=first.get("dtf_large_fee") or Decimal("0.00"),
    )
    product.set_current_language("it")
    product.name = first["name_it"]
    product.description = first["description_it"]
    product.short_description = first.get("short_description_it") or ""
    product.save()
    product.set_current_language("en")
    product.name = first["name_en"]
    product.description = first["description_en"]
    product.short_description = first.get("short_description_en") or ""
    product.save()

    category_ids = list(first.get("category_ids") or [])
    parent_name = first.get("supplier_category") or ""
    child_name = first.get("supplier_subcategory") or ""
    section = first.get("supplier_section") or Category.Section.WORKWEAR
    if parent_name or child_name:
        parent = ensure_category(parent_name, section=section) if parent_name else None
        if parent:
            category_ids.append(parent.id)
        if child_name and child_name.strip().lower() != parent_name.strip().lower():
            child = ensure_category(child_name, parent=parent, section=section)
            if child:
                category_ids.append(child.id)
        elif child_name and not parent:
            child = ensure_category(child_name, section=section)
            if child:
                category_ids.append(child.id)
    if category_ids:
        product.categories.set(list(dict.fromkeys(category_ids)))

    image_urls = _merge_image_url_lists(
        *(r.get("image_urls") or [] for r in rows),
    )
    for index, image_url in enumerate(image_urls):
        image, reason = attach_image_from_url(
            product,
            image_url,
            is_primary=(index == 0),
        )
        if not image:
            raise ValueError(
                f"Prodotto '{product.sku}': impossibile importare url_immagini "
                f"('{image_url}'): {reason}"
            )

    mockup_url = first.get("mockup_url") or ""
    if mockup_url:
        ok, reason = attach_mockup_from_url(product, mockup_url)
        if not ok:
            raise ValueError(
                f"Prodotto '{product.sku}': impossibile importare url_mockup "
                f"('{mockup_url}'): {reason}"
            )

    variants_created = 0
    for row in rows:
        color_name = ensure_color(row["color"])
        variant_sku = _unique_variant_sku(row["variant_sku"])
        ProductVariant.objects.create(
            product=product,
            sku=variant_sku,
            size=row["size"],
            color=color_name,
            price=row["price"],
            sale_price=row["sale_price"],
            stock_quantity=row["stock"],
            is_active=True,
        )
        variants_created += 1

    return variants_created, 1


def iter_import_parsed_rows(parsed_rows: list[dict]):
    """Yield progress events, then a final complete event with counts."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in parsed_rows:
        grouped[row["product_sku"].lower()].append(row)

    total_products = len(grouped)
    created_products = 0
    created_variants = 0

    for index, rows in enumerate(grouped.values(), start=1):
        first = rows[0]
        with transaction.atomic():
            variant_count, _product_count = _import_one_product_group(rows)
        created_products += 1
        created_variants += variant_count
        yield {
            "phase": "importing",
            "current": index,
            "total": total_products,
            "message": f"Importazione prodotto {index} di {total_products}…",
            "product_sku": first.get("product_sku") or "",
        }

    yield {
        "phase": "complete",
        "created_products": created_products,
        "created_variants": created_variants,
    }


def import_parsed_rows(parsed_rows: list[dict]) -> dict:
    created_products = 0
    created_variants = 0
    for event in iter_import_parsed_rows(parsed_rows):
        if event.get("phase") == "complete":
            created_products = event["created_products"]
            created_variants = event["created_variants"]
    return {
        "created_products": created_products,
        "created_variants": created_variants,
    }
