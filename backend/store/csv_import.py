"""CSV bulk product import with row-level validation."""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.text import slugify

from .constants import CLOTHING_SIZES
from .models import Brand, Category, Color, Product, ProductVariant
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
    "nome_it",
    "nome_en",
    "descrizione_it",
    "descrizione_en",
    "taglia",
    "colore",
    "prezzo",
    "scorte",
    "sku_variante",
    "slug_categorie",
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
    "name_it": "nome_it",
    "name_en": "nome_en",
    "description_it": "descrizione_it",
    "description_en": "descrizione_en",
    "size": "taglia",
    "color": "colore",
    "price": "prezzo",
    "stock": "scorte",
    "variant_sku": "sku_variante",
    "category_slugs": "slug_categorie",
    "sale_price": "prezzo_scontato",
    "allows_customization": "ricamo_petto",
    "customization_fee": "costo_ricamo_petto",
    "personalizzazione": "ricamo_petto",
    "costo_personalizzazione": "costo_ricamo_petto",
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
        "descrizione_it": "Polo resistente per uso professionale.",
        "descrizione_en": "Durable polo for professional use.",
        "taglia": "M",
        "colore": "Blu",
        "prezzo": "29.90",
        "scorte": "10",
        "sku_variante": "SW-POLO-01-M-BLU",
        "slug_categorie": "polo",
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
        "descrizione_it": "Polo resistente per uso professionale.",
        "descrizione_en": "Durable polo for professional use.",
        "taglia": "L",
        "colore": "Blu",
        "prezzo": "29.90",
        "scorte": "8",
        "sku_variante": "SW-POLO-01-L-BLU",
        "slug_categorie": "polo",
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
            "descrizione_it": _translation(product, "description", "it"),
            "descrizione_en": _translation(product, "description", "en"),
            "slug_categorie": category_slugs,
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
    normalized = (value or "").strip().lower().replace(" ", "_")
    return HEADER_ALIASES.get(normalized, normalized)


def _cell(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


def _parse_http_urls(raw: str, field: str, row_num: int, errors: list[dict]) -> list[str]:
    urls = split_url_list(raw)
    valid: list[str] = []
    for url in urls:
        if not url.startswith(("http://", "https://")):
            errors.append({
                "row": row_num,
                "field": field,
                "message": f"URL non valido in {field}: '{url}'. Usa http:// o https://.",
            })
        else:
            valid.append(url)
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


def _parse_stock(value: str, row_num: int, errors: list[dict]) -> int | None:
    if value == "":
        errors.append({"row": row_num, "field": "scorte", "message": "scorte è obbligatorio."})
        return None
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


def parse_and_validate_csv(file_bytes: bytes) -> tuple[list[dict], list[dict]]:
    """Return (parsed_rows, errors). parsed_rows is empty when errors exist."""
    errors: list[dict] = []
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], [{"row": 0, "field": "file", "message": "Il CSV deve essere codificato in UTF-8."}]

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], [{"row": 0, "field": "file", "message": "Il CSV non ha una riga di intestazione."}]

    normalized_headers = [_normalize_header(h) for h in reader.fieldnames if h is not None]
    missing_headers = [h for h in REQUIRED_FIELDS if h not in normalized_headers]
    if missing_headers:
        return [], [{
            "row": 0,
            "field": "headers",
            "message": f"Colonne obbligatorie mancanti: {', '.join(missing_headers)}.",
        }]

    brands = {b.name.lower(): b.name for b in Brand.objects.filter(is_active=True)}
    colors = {c.name.lower(): c.name for c in Color.objects.filter(is_active=True)}
    categories = {c.slug.lower(): c for c in Category.objects.filter(is_active=True)}
    allowed_sizes = set(CLOTHING_SIZES)
    existing_product_skus = {
        sku.lower(): sku for sku in Product.objects.values_list("sku", flat=True)
    }
    existing_variant_skus = {
        sku.lower(): sku for sku in ProductVariant.objects.values_list("sku", flat=True)
    }

    brand_names = sorted(brands.values())
    color_names = sorted(colors.values())
    size_list = ", ".join(CLOTHING_SIZES)

    parsed_rows: list[dict] = []
    seen_variant_skus: dict[str, int] = {}
    product_meta: dict[str, dict] = {}
    product_size_colors: dict[str, dict[tuple[str, str], int]] = defaultdict(dict)

    for index, raw in enumerate(reader, start=2):  # header is row 1
        row = {_normalize_header(k): (v or "").strip() if v is not None else "" for k, v in raw.items() if k}
        row_num = index

        for field in REQUIRED_FIELDS:
            if not _cell(row, field):
                errors.append({"row": row_num, "field": field, "message": f"{field} è obbligatorio."})

        product_sku = _cell(row, "sku_prodotto")
        brand_raw = _cell(row, "marca")
        name_it = _cell(row, "nome_it")
        name_en = _cell(row, "nome_en")
        description_it = _cell(row, "descrizione_it")
        description_en = _cell(row, "descrizione_en")
        size = _cell(row, "taglia").upper()
        color_raw = _cell(row, "colore")
        price_raw = _cell(row, "prezzo")
        stock_raw = _cell(row, "scorte")
        variant_sku = _cell(row, "sku_variante")
        category_slugs_raw = _cell(row, "slug_categorie")
        sale_price_raw = _cell(row, "prezzo_scontato")

        brand = None
        if brand_raw:
            brand = brands.get(brand_raw.lower())
            if not brand:
                hint = f" Marche ammesse: {', '.join(brand_names)}." if brand_names else " Nessuna marca attiva nel catalogo."
                errors.append({
                    "row": row_num,
                    "field": "marca",
                    "message": f"Marca '{brand_raw}' non trovata.{hint}",
                })

        color = None
        if color_raw:
            color = colors.get(color_raw.lower())
            if not color:
                hint = f" Colori ammessi: {', '.join(color_names)}." if color_names else " Nessun colore attivo nel catalogo."
                errors.append({
                    "row": row_num,
                    "field": "colore",
                    "message": f"Colore '{color_raw}' non trovato.{hint}",
                })

        if size and size not in allowed_sizes:
            errors.append({
                "row": row_num,
                "field": "taglia",
                "message": f"Taglia '{_cell(row, 'taglia')}' non valida. Taglie ammesse: {size_list}.",
            })

        price = _parse_price(price_raw, "prezzo", row_num, errors) if price_raw else None
        stock = _parse_stock(stock_raw, row_num, errors) if stock_raw != "" else None

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

        category_ids: list[int] = []
        if category_slugs_raw:
            for slug in [s.strip() for s in category_slugs_raw.replace(";", ",").split(",") if s.strip()]:
                cat = categories.get(slug.lower())
                if not cat:
                    errors.append({
                        "row": row_num,
                        "field": "slug_categorie",
                        "message": f"Slug categoria '{slug}' non trovato.",
                    })
                else:
                    category_ids.append(cat.id)

        if product_sku and product_sku.lower() in existing_product_skus:
            errors.append({
                "row": row_num,
                "field": "sku_prodotto",
                "message": f"Lo SKU prodotto '{product_sku}' esiste già.",
            })

        if not variant_sku and product_sku and size and color:
            variant_sku = _suggest_variant_sku(product_sku, size, color)

        if variant_sku:
            key = variant_sku.lower()
            if key in existing_variant_skus:
                errors.append({
                    "row": row_num,
                    "field": "sku_variante",
                    "message": f"Lo SKU variante '{variant_sku}' esiste già.",
                })
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

        if product_sku and size and color:
            pair = (size, color.lower() if color else color_raw.lower())
            prev = product_size_colors[product_sku.lower()].get(pair)
            if prev:
                errors.append({
                    "row": row_num,
                    "field": "taglia",
                    "message": (
                        f"Taglia '{size}' + colore '{color or color_raw}' è duplicata "
                        f"per il prodotto '{product_sku}' (anche alla riga {prev})."
                    ),
                })
            else:
                product_size_colors[product_sku.lower()][pair] = row_num

        image_urls = _parse_http_urls(_cell(row, "url_immagini"), "url_immagini", row_num, errors)
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
                "marca": brand or brand_raw,
                "nome_it": name_it,
                "nome_en": name_en,
                "descrizione_it": description_it,
                "descrizione_en": description_en,
                "category_ids": category_ids,
                "allows_customization": allows_customization,
                "customization_fee": customization_fee,
                "image_urls": image_urls,
                "mockup_url": mockup_url,
                **method_values,
            }
            if meta_key in product_meta:
                prev = product_meta[meta_key]
                for field in ("marca", "nome_it", "nome_en", "descrizione_it", "descrizione_en"):
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
                        "field": "slug_categorie",
                        "message": f"slug_categorie per il prodotto '{product_sku}' non corrisponde a una riga precedente.",
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
                if prev.get("image_urls") and image_urls and prev["image_urls"] != image_urls:
                    errors.append({
                        "row": row_num,
                        "field": "url_immagini",
                        "message": f"url_immagini per il prodotto '{product_sku}' non corrisponde a una riga precedente.",
                    })
                if prev.get("mockup_url") and mockup_url and prev["mockup_url"] != mockup_url:
                    errors.append({
                        "row": row_num,
                        "field": "url_mockup",
                        "message": f"url_mockup per il prodotto '{product_sku}' non corrisponde a una riga precedente.",
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
            or not size
            or not (color or color_raw)
            or not method_parse_ok
        ):
            continue

        meta = product_meta.get(product_sku.lower(), {})
        parsed_rows.append({
            "row": row_num,
            "product_sku": product_sku,
            "brand": brand or "",
            "name_it": name_it,
            "name_en": name_en,
            "description_it": description_it,
            "description_en": description_en,
            "size": size,
            "color": color or "",
            "price": price,
            "stock": stock,
            "sale_price": sale_price,
            "variant_sku": variant_sku,
            "category_ids": category_ids,
            "allows_customization": allows_customization,
            "customization_fee": customization_fee,
            "image_urls": meta.get("image_urls") or image_urls,
            "mockup_url": meta.get("mockup_url") or mockup_url,
            **method_values,
        })

    if errors:
        errors.sort(key=lambda e: (e.get("row") or 0, e.get("field") or ""))
        return [], errors

    if not parsed_rows:
        return [], [{"row": 0, "field": "file", "message": "Il CSV non contiene righe di dati."}]

    return parsed_rows, []


def import_parsed_rows(parsed_rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in parsed_rows:
        grouped[row["product_sku"].lower()].append(row)

    created_products = 0
    created_variants = 0

    with transaction.atomic():
        for rows in grouped.values():
            first = rows[0]
            base_slug = slugify(first["name_it"])[:240] or slugify(first["product_sku"])[:240] or "product"
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            product = Product.objects.create(
                sku=first["product_sku"],
                brand=first["brand"],
                slug=slug,
                is_active=True,
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
            product.short_description = ""
            product.save()
            product.set_current_language("en")
            product.name = first["name_en"]
            product.description = first["description_en"]
            product.short_description = ""
            product.save()

            category_ids = first.get("category_ids") or []
            if category_ids:
                product.categories.set(category_ids)

            image_urls = first.get("image_urls") or []
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

            created_products += 1

            for row in rows:
                ProductVariant.objects.create(
                    product=product,
                    sku=row["variant_sku"],
                    size=row["size"],
                    color=row["color"],
                    price=row["price"],
                    sale_price=row["sale_price"],
                    stock_quantity=row["stock"],
                    is_active=True,
                )
                created_variants += 1

    return {
        "created_products": created_products,
        "created_variants": created_variants,
    }
