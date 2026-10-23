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
    "prezzo_unico": "prezzo",
    "prezzo_unitario": "prezzo",
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


def _normalize_header(value: str) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    return HEADER_ALIASES.get(text, text)


def _is_supplier_format(headers: list[str]) -> bool:
    header_set = set(headers)
    if header_set & SUPPLIER_FORMAT_MARKERS:
        return True
    return "sku_variante" in header_set and "descrizione_it" in header_set and "nome_it" not in header_set


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
        if url.startswith(("http://", "https://")):
            valid.append(url)
        elif strict:
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


def _parse_price(value: str, field: str, row_num: int, errors: list[dict]) -> Decimal | None:
    if not value:
        return None
    cleaned = value.replace(",", ".").replace("€", "").replace(" ", "")
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
) -> list[int]:
    if not raw:
        return []
    ids: list[int] = []
    for token in [s.strip() for s in raw.replace(";", ",").split(",") if s.strip()]:
        key = token.lower()
        cat = by_slug.get(key) or by_name.get(key)
        if cat:
            ids.append(cat.id)
        else:
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
    for key in ("prezzo", "prezzo_unico", "prezzo_confezione", "prezzo_imballo"):
        value = _cell(row, key)
        if value:
            return value
    return ""


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
    if not _cell(row, "prezzo"):
        row["prezzo"] = _supplier_price_raw(row)
    if not _cell(row, "scorte"):
        incoming = _cell(row, "in_arrivo")
        if incoming.isdigit():
            row["scorte"] = incoming


def _supplier_category_names(row: dict) -> tuple[str, str, str]:
    return (
        _cell(row, "merceologica"),
        _cell(row, "categoria"),
        _cell(row, "scategoria"),
    )


def _resolve_row_categories(
    row: dict,
    *,
    supplier: bool,
    by_slug: dict[str, Category],
    by_name: dict[str, Category],
    row_num: int,
    errors: list[dict],
) -> list[int]:
    if supplier:
        _merceologica, parent_name, child_name = _supplier_category_names(row)
        if not parent_name and not child_name:
            errors.append({
                "row": row_num,
                "field": "categoria",
                "message": "Indica Categoria o SCategoria.",
            })
        return []
    return _resolve_category_ids(_cell(row, "categoria"), by_slug, by_name, row_num, errors)


def parse_and_validate_csv(
    file_bytes: bytes,
    *,
    progress_callback: Callable[[int, int], None] | None = None,
    progress_total: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """Return (parsed_rows, errors). parsed_rows is empty when errors exist."""
    errors: list[dict] = []
    text, decode_error = _decode_csv_bytes(file_bytes)
    if decode_error:
        return [], [decode_error]

    reader = _csv_reader(text)
    if not reader.fieldnames:
        return [], [{"row": 0, "field": "file", "message": "Il CSV non ha una riga di intestazione."}]

    normalized_headers = [_normalize_header(h) for h in reader.fieldnames if h is not None]
    supplier_format = _is_supplier_format(normalized_headers)
    if supplier_format:
        has_product_id = any(h in normalized_headers for h in ("sku_prodotto", "sku_variante"))
        has_name = any(h in normalized_headers for h in ("nome_it", "descrizione_it"))
        has_price = any(
            h in normalized_headers
            for h in ("prezzo", "prezzo_unico", "prezzo_confezione", "prezzo_imballo")
        )
        missing_headers = []
        if not has_product_id:
            missing_headers.append("Codice Padre o SKU")
        if not has_name:
            missing_headers.append("Descrizione")
        if not has_price:
            missing_headers.append("Prezzo Unico")
    else:
        missing_headers = [h for h in REQUIRED_FIELDS if h not in normalized_headers]
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

    for index, raw in enumerate(reader, start=2):  # header is row 1
        row = {_normalize_header(k): (v or "").strip() if v is not None else "" for k, v in raw.items() if k}
        row_num = index
        _apply_derived_fields(row)

        required_now = ["sku_prodotto", "nome_it", "descrizione_it"]
        if not supplier_format:
            required_now = list(REQUIRED_FIELDS)
        for field in required_now:
            if not _cell(row, field):
                errors.append({"row": row_num, "field": field, "message": f"{field} è obbligatorio."})

        product_sku = _cell(row, "sku_prodotto")
        brand_raw = _cell(row, "marca")
        name_it = _cell(row, "nome_it")
        name_en = _cell(row, "nome_en")
        description_it = _cell(row, "descrizione_it")
        description_en = _cell(row, "descrizione_en")
        short_description_it = _cell(row, "descrizione_breve_it")
        short_description_en = _cell(row, "descrizione_breve_en")
        bestseller_raw = _cell(row, "bestseller")
        size_raw = _cell(row, "taglia")
        size = size_raw.upper() if size_raw.upper() in CLOTHING_SIZES else size_raw
        color_raw = _cell(row, "colore")
        price_raw = _cell(row, "prezzo")
        stock_raw = _cell(row, "scorte")
        variant_sku = _cell(row, "sku_variante")
        category_slugs_raw = _cell(row, "categoria")
        sale_price_raw = _cell(row, "prezzo_scontato")

        if supplier_format and not price_raw:
            continue

        if product_sku and supplier_format:
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
            sku_key = product_sku.lower()
            prev_sku = csv_name_to_sku.get(name_key)
            if prev_sku and prev_sku != sku_key:
                errors.append({
                    "row": row_num,
                    "field": "nome_it",
                    "message": (
                        f"Il nome prodotto '{name_it}' è usato da più SKU nel CSV "
                        f"('{prev_sku}' e '{product_sku}')."
                    ),
                })
            elif name_key:
                csv_name_to_sku[name_key] = sku_key

        if supplier_format:
            price = _parse_price(price_raw, "prezzo", row_num, [])
            if price is None:
                continue
        else:
            price = _parse_price(price_raw, "prezzo", row_num, errors) if price_raw else None
        if stock_raw != "":
            stock = _parse_stock(stock_raw, row_num, errors, required=not supplier_format)
        else:
            stock = _parse_stock("", row_num, errors, required=not supplier_format)

        sale_price = None
        if sale_price_raw:
            sale_price = _parse_price(sale_price_raw, "prezzo_scontato", row_num, errors)

        method_values: dict[str, bool | Decimal] = {}
        method_parse_ok = True
        for enabled_csv, fee_csv, enabled_attr, fee_attr in METHOD_CSV_FIELDS:
            enabled = _parse_bool(_cell(row, enabled_csv), enabled_csv, row_num, errors, default=False)
            if enabled is None:
                method_parse_ok = False
                enabled = False
            fee = Decimal("0.00")
            fee_raw = _cell(row, fee_csv)
            if fee_raw:
                parsed_fee = _parse_price(fee_raw, fee_csv, row_num, errors)
                if parsed_fee is None:
                    method_parse_ok = False
                else:
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
            supplier=supplier_format,
            by_slug=categories_by_slug,
            by_name=categories_by_name,
            row_num=row_num,
            errors=errors,
        )
        merceologica, category_name, subcategory_name = _supplier_category_names(row)

        if not variant_sku and product_sku:
            variant_sku = _suggest_variant_sku(product_sku, size, color_raw)

        supplier_variant_duplicate = bool(
            supplier_format
            and variant_sku
            and variant_sku.lower() in supplier_variant_row_index
        )
        if variant_sku and not supplier_format:
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
            if prev and not (supplier_format and supplier_variant_duplicate):
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
            strict=not supplier_format,
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
                    if supplier_format:
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
                    if not supplier_format:
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
            continue
        if not supplier_format and (not size or not color_raw):
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
            "supplier_section": _section_from_merceologica(merceologica) if supplier_format else "",
            "supplier_category": category_name if supplier_format else "",
            "supplier_subcategory": subcategory_name if supplier_format else "",
            "allows_customization": allows_customization,
            "customization_fee": customization_fee,
            "image_urls": meta.get("image_urls") or image_urls,
            "mockup_url": meta.get("mockup_url") or mockup_url,
            **method_values,
        }
        if supplier_format and variant_sku:
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

    with transaction.atomic():
        for index, rows in enumerate(grouped.values(), start=1):
            first = rows[0]
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
