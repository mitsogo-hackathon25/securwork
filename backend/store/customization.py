"""Product logo customization methods and helpers."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Product

# code, enabled_field, fee_field, italian label, english label
CUSTOMIZATION_METHOD_DEFS = (
    (
        "embroidery_chest",
        "embroidery_chest_enabled",
        "embroidery_chest_fee",
        "Ricamo — lato cuore/petto",
        "Embroidery — heart/chest side",
    ),
    (
        "embroidery_large",
        "embroidery_large_enabled",
        "embroidery_large_fee",
        "Ricamo grande",
        "Large embroidery",
    ),
    (
        "dtf_chest",
        "dtf_chest_enabled",
        "dtf_chest_fee",
        "DTF — lato cuore/petto",
        "DTF — heart/chest side",
    ),
    (
        "dtf_large",
        "dtf_large_enabled",
        "dtf_large_fee",
        "DTF grande (formato A4)",
        "Large DTF (A4 size)",
    ),
)

CUSTOMIZATION_METHOD_CODES = tuple(item[0] for item in CUSTOMIZATION_METHOD_DEFS)

CUSTOMIZATION_METHOD_CHOICES = [
    (code, label_it) for code, _, _, label_it, _ in CUSTOMIZATION_METHOD_DEFS
]

METHOD_LABELS = {
    code: {"it": label_it, "en": label_en}
    for code, _, _, label_it, label_en in CUSTOMIZATION_METHOD_DEFS
}


def method_label(code: str, lang: str = "it") -> str:
    labels = METHOD_LABELS.get(code) or {}
    return labels.get(lang) or labels.get("it") or code


def product_has_customization(product: Product) -> bool:
    if any(getattr(product, enabled_field) for _, enabled_field, _, _, _ in CUSTOMIZATION_METHOD_DEFS):
        return True
    return bool(product.allows_customization)


def product_customization_options(product: Product, lang: str = "it") -> list[dict]:
    options: list[dict] = []
    for code, enabled_field, fee_field, _, _ in CUSTOMIZATION_METHOD_DEFS:
        if getattr(product, enabled_field):
            fee = getattr(product, fee_field) or Decimal("0.00")
            options.append({
                "code": code,
                "label": method_label(code, lang),
                "fee": f"{fee:.2f}",
            })
    if not options and product.allows_customization:
        fee = product.customization_fee or Decimal("0.00")
        options.append({
            "code": "embroidery_chest",
            "label": method_label("embroidery_chest", lang),
            "fee": f"{fee:.2f}",
        })
    return options


def product_fee_for_method(product: Product, method: str | None) -> Decimal:
    if not method:
        return product.customization_fee or Decimal("0.00")
    for code, enabled_field, fee_field, _, _ in CUSTOMIZATION_METHOD_DEFS:
        if code == method:
            if getattr(product, enabled_field):
                return getattr(product, fee_field) or Decimal("0.00")
            if product.allows_customization and not any(
                getattr(product, ef) for _, ef, _, _, _ in CUSTOMIZATION_METHOD_DEFS
            ):
                return product.customization_fee or Decimal("0.00")
            return Decimal("0.00")
    return Decimal("0.00")


def product_method_enabled(product: Product, method: str) -> bool:
    for code, enabled_field, _, _, _ in CUSTOMIZATION_METHOD_DEFS:
        if code == method:
            if getattr(product, enabled_field):
                return True
            # Legacy: master flag only, no per-method flags set
            return bool(product.allows_customization) and not any(
                getattr(product, ef) for _, ef, _, _, _ in CUSTOMIZATION_METHOD_DEFS
            )
    return False


def sync_allows_customization(product: Product) -> bool:
    """Set allows_customization from enabled methods; return whether any are enabled."""
    enabled = any(getattr(product, ef) for _, ef, _, _, _ in CUSTOMIZATION_METHOD_DEFS)
    product.allows_customization = enabled
    if enabled:
        fees = [
            getattr(product, fee_field) or Decimal("0.00")
            for _, enabled_field, fee_field, _, _ in CUSTOMIZATION_METHOD_DEFS
            if getattr(product, enabled_field)
        ]
        if fees:
            product.customization_fee = min(fees)
    return enabled
