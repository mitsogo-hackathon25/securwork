"""Helpers for attaching product images from uploads or remote URLs."""
from __future__ import annotations

import os
from urllib.parse import urlparse

from django.conf import settings

from .image_utils import download_image_with_reason, is_direct_image_url
from .models import Product, ProductImage


def filename_from_url(url: str, product_sku: str) -> str:
    path = urlparse(url).path
    name = os.path.basename(path) or f"{product_sku.lower()}-image"
    if "." not in name:
        name = f"{name}.jpg"
    return name


def create_product_image(
    product: Product,
    image_file=None,
    external_url: str = "",
    alt_text: str = "",
    is_primary: bool = False,
    sort_order: int | None = None,
) -> ProductImage:
    if not image_file and not external_url:
        raise ValueError("Either image_file or external_url is required.")
    if sort_order is None:
        sort_order = product.images.count()
    if is_primary:
        product.images.update(is_primary=False)
    return ProductImage.objects.create(
        product=product,
        image=image_file,
        external_url=external_url,
        alt_text=alt_text,
        sort_order=sort_order,
        is_primary=is_primary or not product.images.exists(),
    )


def attach_image_from_url(
    product: Product,
    image_url: str,
    *,
    is_primary: bool = False,
    alt_text: str = "",
    sort_order: int | None = None,
) -> tuple[ProductImage | None, str]:
    """Download or link an image URL. Returns (image, error_message)."""
    url = (image_url or "").strip()
    if not url:
        return None, "URL immagine mancante."
    if not url.startswith(("http://", "https://")):
        return None, "L'URL deve iniziare con http:// o https://."

    content, reason = download_image_with_reason(url, filename_from_url(url, product.sku))
    if content:
        return create_product_image(
            product,
            image_file=content,
            alt_text=alt_text,
            is_primary=is_primary,
            sort_order=sort_order,
        ), ""
    if is_direct_image_url(url):
        return create_product_image(
            product,
            external_url=url,
            alt_text=alt_text,
            is_primary=is_primary,
            sort_order=sort_order,
        ), ""
    return None, reason or "Impossibile scaricare l'immagine da questo URL."


def attach_mockup_from_url(product: Product, image_url: str) -> tuple[bool, str]:
    url = (image_url or "").strip()
    if not url:
        return False, "URL mockup mancante."
    if not url.startswith(("http://", "https://")):
        return False, "L'URL mockup deve iniziare con http:// o https://."

    content, reason = download_image_with_reason(url, filename_from_url(url, f"{product.sku}-mockup"))
    if not content:
        return False, reason or "Impossibile scaricare il mockup da questo URL."

    if product.mockup_front:
        product.mockup_front.delete(save=False)
    product.mockup_front = content
    product.save(update_fields=["mockup_front"])
    return True, ""


def absolute_media_url(url: str | None) -> str:
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    base = (getattr(settings, "FRONTEND_URL", None) or "").rstrip("/")
    if base:
        return f"{base}{url if url.startswith('/') else '/' + url}"
    return url


def product_image_export_urls(product: Product) -> list[str]:
    urls: list[str] = []
    images = product.images.all().order_by("-is_primary", "sort_order", "id")
    for image in images:
        if image.external_url:
            urls.append(image.external_url)
        elif image.image:
            urls.append(absolute_media_url(image.image.url))
    return urls


def split_url_list(raw: str) -> list[str]:
    if not raw:
        return []
    parts: list[str] = []
    for chunk in raw.replace(";", ",").split(","):
        value = chunk.strip()
        if value:
            parts.append(value)
    return parts
