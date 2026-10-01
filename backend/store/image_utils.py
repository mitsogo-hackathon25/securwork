"""Download or generate demo images for products and categories."""
import io
import logging
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

from .image_sources import category_photo_url, product_photo_url

logger = logging.getLogger(__name__)

BRAND_COLORS = [
    (26, 43, 74), (45, 74, 122), (55, 65, 81), (30, 58, 95),
    (232, 93, 4), (75, 85, 99), (31, 41, 55), (15, 26, 46),
]


def download_image(url: str, filename: str) -> ContentFile | None:
    try:
        req = Request(url, headers={"User-Agent": "SecurWork-Seed/1.0"})
        with urlopen(req, timeout=30) as response:
            final_url = response.geturl()
            data = response.read()
        if len(data) < 2000:
            return None
        # picsum may return webp — save as jpg filename (browsers accept it)
        if final_url.endswith(".webp") or data[:4] == b"RIFF":
            name = filename.replace(".jpg", ".webp")
        else:
            name = filename
        return ContentFile(data, name=name)
    except Exception as exc:
        logger.warning("Could not download %s: %s", url, exc)
        return None


def _gradient_fallback(width: int, height: int, color: tuple) -> ContentFile:
    """Simple photo-like gradient when download fails (no text)."""
    img = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(img)
    r, g, b = color
    for y in range(height):
        factor = y / height
        line_color = (
            int(r + (255 - r) * factor * 0.12),
            int(g + (255 - g) * factor * 0.12),
            int(b + (255 - b) * factor * 0.12),
        )
        draw.line([(0, y), (width, y)], fill=line_color)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return ContentFile(buffer.read(), name="fallback.jpg")


def get_category_image(slug: str, section: str = "workwear") -> ContentFile:
    filename = f"cat-{slug}.jpg"
    url = category_photo_url(slug)
    content = download_image(url, filename)
    if content:
        return content
    color = BRAND_COLORS[hash(slug) % len(BRAND_COLORS)]
    fallback = _gradient_fallback(960, 640, color)
    fallback.name = filename
    return fallback


def get_product_image(sku: str, category_slug: str | None = None) -> ContentFile:
    filename = f"{sku.lower()}.jpg"
    url = product_photo_url(sku, category_slug)
    content = download_image(url, filename)
    if content:
        return content
    color = BRAND_COLORS[hash(sku) % len(BRAND_COLORS)]
    fallback = _gradient_fallback(800, 1000, color)
    fallback.name = filename
    return fallback


# Backwards-compatible aliases for seed commands
def generate_category_image(name: str, slug: str, section: str = "workwear") -> ContentFile:
    return get_category_image(slug, section)


def generate_product_image(label: str, sku: str, color: tuple | None = None, category_slug: str | None = None) -> ContentFile:
    return get_product_image(sku, category_slug)
