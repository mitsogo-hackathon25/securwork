"""Download or generate demo images for products and categories."""
import io
import logging
import mimetypes
import re
from html import unescape
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

from .image_sources import category_photo_url, product_photo_url

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp", ".svg")
DRIVE_FILE_ID_RE = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")
DRIVE_CONFIRM_RE = re.compile(r"confirm=([0-9A-Za-z_-]+)")
DRIVE_DOWNLOAD_HREF_RE = re.compile(
    r'href=["\'](https://(?:drive\.google\.com/uc[^"\']+|drive\.usercontent\.google\.com/download[^"\']+))["\']',
    re.I,
)
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

BRAND_COLORS = [
    (26, 43, 74), (45, 74, 122), (55, 65, 81), (30, 58, 95),
    (232, 93, 4), (75, 85, 99), (31, 41, 55), (15, 26, 46),
]


def _looks_like_image(data: bytes, content_type: str = "") -> bool:
    if not data:
        return False
    if content_type.startswith("image/"):
        return True
    header = data[:16]
    return (
        header.startswith(b"\xff\xd8\xff")
        or header.startswith(b"\x89PNG\r\n\x1a\n")
        or header.startswith(b"GIF87a")
        or header.startswith(b"GIF89a")
        or header.startswith(b"RIFF")
        or header.startswith(b"BM")
        or header[:4] == b"RIFF"
    )


def _filename_for_download(url: str, filename: str, content_type: str, data: bytes) -> str:
    path = urlparse(url).path.lower()
    for ext in IMAGE_EXTENSIONS:
        if path.endswith(ext):
            base = filename.rsplit(".", 1)[0]
            return f"{base}{ext}"
    guessed = mimetypes.guess_extension((content_type or "").split(";")[0].strip())
    if guessed:
        base = filename.rsplit(".", 1)[0]
        return f"{base}{guessed}"
    if data[:4] == b"RIFF":
        return filename.replace(".jpg", ".webp")
    return filename


def google_drive_file_id(url: str) -> str | None:
    match = DRIVE_FILE_ID_RE.search(url)
    if match:
        return match.group(1)
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "drive.google.com" in host or "docs.google.com" in host:
        ids = parse_qs(parsed.query).get("id")
        if ids:
            return ids[0]
    return None


def is_direct_image_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in IMAGE_EXTENSIONS)


def resolve_image_url(url: str) -> str:
    file_id = google_drive_file_id(url)
    if file_id:
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


def _http_get(url: str, opener, referer: str = "") -> tuple[bytes, str, str]:
    parsed = urlparse(url)
    headers = {
        **BROWSER_HEADERS,
        "Referer": referer or f"{parsed.scheme}://{parsed.netloc}/",
    }
    req = Request(url, headers=headers)
    with opener.open(req, timeout=30) as response:
        content_type = (response.headers.get("Content-Type") or "").lower()
        data = response.read()
        final_url = response.geturl()
    return data, content_type, final_url


def _content_file_from_bytes(data: bytes, content_type: str, source_url: str, filename: str) -> ContentFile | None:
    if data[:15].lower().startswith((b"<!doctype", b"<html")):
        return None
    if not _looks_like_image(data, content_type):
        return None
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except Exception:
        return None
    name = _filename_for_download(source_url, filename, content_type, data)
    return ContentFile(data, name=name)


def _drive_followup_url(html: str, file_id: str) -> str | None:
    href_match = DRIVE_DOWNLOAD_HREF_RE.search(html)
    if href_match:
        return unescape(href_match.group(1)).replace("&amp;", "&")
    confirm = DRIVE_CONFIRM_RE.search(html)
    if confirm:
        return (
            f"https://drive.google.com/uc?export=download&id={file_id}"
            f"&confirm={confirm.group(1)}"
        )
    form_action = re.search(r'<form[^>]+action=["\']([^"\']+)["\']', html, re.I)
    if form_action:
        action = unescape(form_action.group(1))
        if action.startswith("/"):
            action = urljoin("https://drive.google.com/", action)
        if "download" in action:
            return action
    return None


def download_image(url: str, filename: str) -> ContentFile | None:
    content, _reason = download_image_with_reason(url, filename)
    return content


def download_image_with_reason(url: str, filename: str) -> tuple[ContentFile | None, str]:
    file_id = google_drive_file_id(url)
    candidates = []
    resolved = resolve_image_url(url)
    candidates.append(resolved)
    if file_id:
        candidates.append(f"https://lh3.googleusercontent.com/d/{file_id}")

    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    last_error = "Could not download an image from this URL."

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            data, content_type, final_url = _http_get(candidate, opener)
        except HTTPError as exc:
            last_error = f"The image host returned HTTP {exc.code}."
            if file_id and exc.code in (401, 403):
                last_error = (
                    "This Google Drive file is not publicly accessible. "
                    "Set sharing to Anyone with the link, or upload the file instead."
                )
            logger.warning("Could not download %s: %s", candidate, exc)
            continue
        except URLError as exc:
            last_error = "Could not reach this URL."
            logger.warning("Could not download %s: %s", candidate, exc)
            continue
        except Exception as exc:
            last_error = "Could not download an image from this URL."
            logger.warning("Could not download %s: %s", candidate, exc)
            continue

        content = _content_file_from_bytes(data, content_type, final_url, filename)
        if content:
            return content, ""

        if file_id and (b"<html" in data[:200].lower() or b"<!doctype" in data[:200].lower()):
            html = data.decode("utf-8", errors="ignore")
            followup = _drive_followup_url(html, file_id)
            if followup and followup not in seen:
                try:
                    data, content_type, final_url = _http_get(
                        followup, opener, referer=candidate
                    )
                    content = _content_file_from_bytes(data, content_type, final_url, filename)
                    if content:
                        return content, ""
                except Exception as exc:
                    logger.warning("Could not download Drive follow-up %s: %s", followup, exc)
            last_error = (
                "This Google Drive link is a sharing page, not a direct image, "
                "or the file is not public. Set sharing to Anyone with the link, "
                "or upload the file instead."
            )
            continue

        last_error = (
            "This URL did not return an image file. Use a direct .jpg/.png/.webp link, "
            "or upload the file instead."
        )

    return None, last_error


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
