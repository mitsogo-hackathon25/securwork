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

CSV_HEADERS = [
    "product_sku",
    "brand",
    "name_it",
    "name_en",
    "description_it",
    "description_en",
    "size",
    "color",
    "price",
    "stock",
    "variant_sku",
    "category_slugs",
    "sale_price",
]

REQUIRED_FIELDS = [
    "product_sku",
    "brand",
    "name_it",
    "name_en",
    "description_it",
    "description_en",
    "size",
    "color",
    "price",
    "stock",
]

TEMPLATE_EXAMPLE_ROWS = [
    {
        "product_sku": "SW-POLO-01",
        "brand": "ExampleBrand",
        "name_it": "Polo da lavoro",
        "name_en": "Work polo",
        "description_it": "Polo resistente per uso professionale.",
        "description_en": "Durable polo for professional use.",
        "size": "M",
        "color": "Blu",
        "price": "29.90",
        "stock": "10",
        "variant_sku": "SW-POLO-01-M-BLU",
        "category_slugs": "polo",
        "sale_price": "",
    },
    {
        "product_sku": "SW-POLO-01",
        "brand": "ExampleBrand",
        "name_it": "Polo da lavoro",
        "name_en": "Work polo",
        "description_it": "Polo resistente per uso professionale.",
        "description_en": "Durable polo for professional use.",
        "size": "L",
        "color": "Blu",
        "price": "29.90",
        "stock": "8",
        "variant_sku": "SW-POLO-01-L-BLU",
        "category_slugs": "polo",
        "sale_price": "",
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


def export_products_csv() -> str:
    """Export all products as CSV (one row per variant), matching import columns."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_HEADERS, lineterminator="\n")
    writer.writeheader()

    products = (
        Product.objects.prefetch_related("variants", "categories")
        .order_by("sku")
    )
    for product in products:
        category_slugs = ",".join(
            product.categories.order_by("slug").values_list("slug", flat=True)
        )
        base = {
            "product_sku": product.sku,
            "brand": product.brand or "",
            "name_it": _translation(product, "name", "it"),
            "name_en": _translation(product, "name", "en"),
            "description_it": _translation(product, "description", "it"),
            "description_en": _translation(product, "description", "en"),
            "category_slugs": category_slugs,
        }
        variants = list(product.variants.all())
        if not variants:
            writer.writerow({
                **base,
                "size": "",
                "color": "",
                "price": "",
                "stock": "",
                "variant_sku": "",
                "sale_price": "",
            })
            continue
        for variant in variants:
            writer.writerow({
                **base,
                "size": variant.size or "",
                "color": variant.color or "",
                "price": f"{variant.price:.2f}",
                "stock": str(variant.stock_quantity),
                "variant_sku": variant.sku,
                "sale_price": f"{variant.sale_price:.2f}" if variant.sale_price is not None else "",
            })
    return buffer.getvalue()


def _normalize_header(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "_")


def _cell(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


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
        errors.append({"row": row_num, "field": field, "message": f"Invalid {field}: '{value}'."})
        return None
    if amount < 0:
        errors.append({"row": row_num, "field": field, "message": f"{field} cannot be negative."})
        return None
    return amount


def _parse_stock(value: str, row_num: int, errors: list[dict]) -> int | None:
    if value == "":
        errors.append({"row": row_num, "field": "stock", "message": "stock is required."})
        return None
    try:
        stock = int(value)
    except ValueError:
        errors.append({"row": row_num, "field": "stock", "message": f"Invalid stock: '{value}'."})
        return None
    if stock < 0:
        errors.append({"row": row_num, "field": "stock", "message": "stock cannot be negative."})
        return None
    return stock


def parse_and_validate_csv(file_bytes: bytes) -> tuple[list[dict], list[dict]]:
    """Return (parsed_rows, errors). parsed_rows is empty when errors exist."""
    errors: list[dict] = []
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], [{"row": 0, "field": "file", "message": "CSV must be UTF-8 encoded."}]

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], [{"row": 0, "field": "file", "message": "CSV has no header row."}]

    normalized_headers = [_normalize_header(h) for h in reader.fieldnames if h is not None]
    missing_headers = [h for h in REQUIRED_FIELDS if h not in normalized_headers]
    if missing_headers:
        return [], [{
            "row": 0,
            "field": "headers",
            "message": f"Missing required columns: {', '.join(missing_headers)}.",
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
                errors.append({"row": row_num, "field": field, "message": f"{field} is required."})

        product_sku = _cell(row, "product_sku")
        brand_raw = _cell(row, "brand")
        name_it = _cell(row, "name_it")
        name_en = _cell(row, "name_en")
        description_it = _cell(row, "description_it")
        description_en = _cell(row, "description_en")
        size = _cell(row, "size").upper()
        color_raw = _cell(row, "color")
        price_raw = _cell(row, "price")
        stock_raw = _cell(row, "stock")
        variant_sku = _cell(row, "variant_sku")
        category_slugs_raw = _cell(row, "category_slugs")
        sale_price_raw = _cell(row, "sale_price")

        brand = None
        if brand_raw:
            brand = brands.get(brand_raw.lower())
            if not brand:
                hint = f" Allowed brands: {', '.join(brand_names)}." if brand_names else " No active brands in catalog."
                errors.append({
                    "row": row_num,
                    "field": "brand",
                    "message": f"Brand '{brand_raw}' not found.{hint}",
                })

        color = None
        if color_raw:
            color = colors.get(color_raw.lower())
            if not color:
                hint = f" Allowed colors: {', '.join(color_names)}." if color_names else " No active colors in catalog."
                errors.append({
                    "row": row_num,
                    "field": "color",
                    "message": f"Color '{color_raw}' not found.{hint}",
                })

        if size and size not in allowed_sizes:
            errors.append({
                "row": row_num,
                "field": "size",
                "message": f"Size '{_cell(row, 'size')}' is invalid. Allowed sizes: {size_list}.",
            })

        price = _parse_price(price_raw, "price", row_num, errors) if price_raw else None
        stock = _parse_stock(stock_raw, row_num, errors) if stock_raw != "" else None

        sale_price = None
        if sale_price_raw:
            sale_price = _parse_price(sale_price_raw, "sale_price", row_num, errors)

        category_ids: list[int] = []
        if category_slugs_raw:
            for slug in [s.strip() for s in category_slugs_raw.replace(";", ",").split(",") if s.strip()]:
                cat = categories.get(slug.lower())
                if not cat:
                    errors.append({
                        "row": row_num,
                        "field": "category_slugs",
                        "message": f"Category slug '{slug}' not found.",
                    })
                else:
                    category_ids.append(cat.id)

        if product_sku and product_sku.lower() in existing_product_skus:
            errors.append({
                "row": row_num,
                "field": "product_sku",
                "message": f"Product SKU '{product_sku}' already exists.",
            })

        if not variant_sku and product_sku and size and color:
            variant_sku = _suggest_variant_sku(product_sku, size, color)

        if variant_sku:
            key = variant_sku.lower()
            if key in existing_variant_skus:
                errors.append({
                    "row": row_num,
                    "field": "variant_sku",
                    "message": f"Variant SKU '{variant_sku}' already exists.",
                })
            if key in seen_variant_skus:
                errors.append({
                    "row": row_num,
                    "field": "variant_sku",
                    "message": (
                        f"Variant SKU '{variant_sku}' is duplicated in the CSV "
                        f"(also on row {seen_variant_skus[key]})."
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
                    "field": "size",
                    "message": (
                        f"Size '{size}' + color '{color or color_raw}' is duplicated "
                        f"for product '{product_sku}' (also on row {prev})."
                    ),
                })
            else:
                product_size_colors[product_sku.lower()][pair] = row_num

        if product_sku:
            meta_key = product_sku.lower()
            current = {
                "brand": brand or brand_raw,
                "name_it": name_it,
                "name_en": name_en,
                "description_it": description_it,
                "description_en": description_en,
                "category_ids": category_ids,
            }
            if meta_key in product_meta:
                prev = product_meta[meta_key]
                for field in ("brand", "name_it", "name_en", "description_it", "description_en"):
                    if prev.get(field) and current.get(field) and prev[field] != current[field]:
                        errors.append({
                            "row": row_num,
                            "field": field,
                            "message": (
                                f"{field} for product '{product_sku}' does not match an earlier row "
                                f"('{prev[field]}' vs '{current[field]}')."
                            ),
                        })
                if prev.get("category_ids") and category_ids and set(prev["category_ids"]) != set(category_ids):
                    errors.append({
                        "row": row_num,
                        "field": "category_slugs",
                        "message": f"category_slugs for product '{product_sku}' does not match an earlier row.",
                    })
            else:
                product_meta[meta_key] = current

        # Skip collecting row if critical fields failed hard — still collect when only soft? collect always if minimal ok
        if not product_sku or price is None or stock is None or not size or not (color or color_raw):
            continue

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
        })

    if errors:
        errors.sort(key=lambda e: (e.get("row") or 0, e.get("field") or ""))
        return [], errors

    if not parsed_rows:
        return [], [{"row": 0, "field": "file", "message": "CSV has no data rows."}]

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
