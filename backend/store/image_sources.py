"""
Curated workwear / professional-clothing photos for demo seeding.
All URLs are verified against Unsplash and Pexels CDNs.
"""

from __future__ import annotations


def _unsplash(photo_id: str, width: int = 800) -> str:
    return f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w={width}&q=80"


def _pexels(photo_id: int, width: int = 800) -> str:
    return (
        f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg"
        f"?auto=compress&cs=tinysrgb&w={width}"
    )


# Verified photo pools per category slug.
CATEGORY_PHOTOS: dict[str, list[str]] = {
    "abbigliamento-da-lavoro": [
        _unsplash("photo-1581094794329-c8112a89af12", 960),
        _pexels(1216589, 960),
        "https://images.pexels.com/photos/159358/construction-site-build-construction-work-159358.jpeg?auto=compress&cs=tinysrgb&w=960",
    ],
    "t-shirt": [
        _unsplash("photo-1521572163474-6864f9cf17ab", 960),
        _pexels(7678390, 960),
        _unsplash("photo-1581092160562-40aa08e78837", 960),
    ],
    "polo": [
        _unsplash("photo-1622445275463-afa2ab738c34", 960),
        _pexels(7671166, 960),
        _unsplash("photo-1602810318383-e386cc2a3ccf", 960),
    ],
    "pantaloni-da-lavoro": [
        _pexels(6474455, 960),
        _unsplash("photo-1594938298603-c8148c4dae35", 960),
        _pexels(6474489, 960),
    ],
    "scarpe-da-lavoro": [
        _unsplash("photo-1549298916-b41d501d3772", 960),
        _pexels(112406, 960),
        _pexels(631986, 960),
    ],
    "giacche": [
        _unsplash("photo-1551028719-00167b16eac5", 960),
        _unsplash("photo-1539533018447-63fcce2678e3", 960),
        _pexels(1124468, 960),
    ],
    "gilet": [
        _pexels(1181396, 960),
        _unsplash("photo-1618354691373-d851c5c3a990", 960),
        _pexels(2437453, 960),
    ],
    "felpe": [
        _unsplash("photo-1556821840-3a63f95609a7", 960),
        _pexels(7671165, 960),
        _unsplash("photo-1434389677669-e08b4cac3105", 960),
    ],
    "maglioni": [
        _unsplash("photo-1434389677669-e08b4cac3105", 960),
        _pexels(6069103, 960),
        _unsplash("photo-1556821840-3a63f95609a7", 960),
    ],
    "guanti": [
        _pexels(4484071, 960),
        _pexels(4484070, 960),
        _unsplash("photo-1581092160562-40aa08e78837", 960),
    ],
    "camicie": [
        _unsplash("photo-1602810318383-e386cc2a3ccf", 960),
        _pexels(7671166, 960),
        _unsplash("photo-1622445275463-afa2ab738c34", 960),
    ],
    "salopette": [
        _unsplash("photo-1594938298603-c8148c4dae35", 960),
        _pexels(6474489, 960),
        _pexels(6474455, 960),
    ],
    "camici": [
        _unsplash("photo-1576091160399-112ba8d25d1d", 960),
        _pexels(8460097, 960),
        _pexels(8460096, 960),
    ],
    "estate": [
        _unsplash("photo-1581092160562-40aa08e78837", 960),
        _pexels(1216589, 960),
        _unsplash("photo-1581094794329-c8112a89af12", 960),
    ],
    "inverno": [
        _unsplash("photo-1539533018447-63fcce2678e3", 960),
        _pexels(1124468, 960),
        _unsplash("photo-1551028719-00167b16eac5", 960),
    ],
    "abbigliamento-professionale": [
        _unsplash("photo-1556910103-1c02745aae4d", 960),
        _pexels(262978, 960),
        _pexels(3182813, 960),
    ],
    "grembiuli": [
        _pexels(6957552, 960),
        _unsplash("photo-1556910103-1c02745aae4d", 960),
        _pexels(262978, 960),
    ],
    "pantaloni-professionali": [
        _pexels(262978, 960),
        _pexels(3184191, 960),
        _unsplash("photo-1556910103-1c02745aae4d", 960),
    ],
    "abbigliamento-sanitario": [
        _unsplash("photo-1576091160399-112ba8d25d1d", 960),
        _pexels(8460096, 960),
        _pexels(8460097, 960),
    ],
    "abbigliamento-alimentare": [
        _unsplash("photo-1556910103-1c02745aae4d", 960),
        _pexels(262978, 960),
        _pexels(6957552, 960),
    ],
    "divise-professionali": [
        _unsplash("photo-1582719478250-c89cae4dc85b", 960),
        _unsplash("photo-1573496359142-b8d87734a5a2", 960),
        _pexels(3182813, 960),
    ],
    "cappelli": [
        _unsplash("photo-1581092160562-40aa08e78837", 960),
        _pexels(7678390, 960),
        _unsplash("photo-1521572163474-6864f9cf17ab", 960),
    ],
    "linea-chef": [
        _unsplash("photo-1556910103-1c02745aae4d", 960),
        _pexels(262978, 960),
        _pexels(6957552, 960),
    ],
    "taglia-unica": [
        _pexels(3182813, 960),
        _unsplash("photo-1556910103-1c02745aae4d", 960),
        _pexels(3184191, 960),
    ],
    "hotel-ristorante-caffe": [
        _pexels(262978, 960),
        _pexels(3182813, 960),
        _unsplash("photo-1556910103-1c02745aae4d", 960),
    ],
    "parrucchiere": [
        _unsplash("photo-1582719478250-c89cae4dc85b", 960),
        _pexels(3993449, 960),
        _unsplash("photo-1573496359142-b8d87734a5a2", 960),
    ],
    "scarpe-professionali": [
        _unsplash("photo-1549298916-b41d501d3772", 960),
        _pexels(112406, 960),
        _pexels(631986, 960),
    ],
}

DEFAULT_WORKWEAR = [
    _unsplash("photo-1581094794329-c8112a89af12", 960),
    _pexels(1216589, 960),
]
DEFAULT_PROFESSIONAL = [
    _unsplash("photo-1556910103-1c02745aae4d", 960),
    _pexels(262978, 960),
]

_PROFESSIONAL_SLUGS = {
    "abbigliamento-professionale",
    "grembiuli",
    "pantaloni-professionali",
    "abbigliamento-sanitario",
    "abbigliamento-alimentare",
    "divise-professionali",
    "linea-chef",
    "taglia-unica",
    "hotel-ristorante-caffe",
    "parrucchiere",
    "scarpe-professionali",
}


def _photos_for_slug(slug: str | None) -> list[str]:
    if slug and slug in CATEGORY_PHOTOS:
        return CATEGORY_PHOTOS[slug]
    if slug and slug in _PROFESSIONAL_SLUGS:
        return DEFAULT_PROFESSIONAL
    return DEFAULT_WORKWEAR


def _resize_url(url: str, width: int) -> str:
    if "images.unsplash.com/" in url:
        photo_id = url.split("images.unsplash.com/")[1].split("?")[0]
        return _unsplash(photo_id, width)
    if "/construction-site-build-construction-work-" in url:
        return url.replace("w=960", f"w={width}").replace("w=800", f"w={width}")
    photo_id = int(url.split("/photos/")[1].split("/")[0])
    return _pexels(photo_id, width)


def category_photo_url(slug: str) -> str:
    return _resize_url(_photos_for_slug(slug)[0], 960)


def product_photo_url(sku: str, category_slug: str | None = None) -> str:
    pool = _photos_for_slug(category_slug)
    index = abs(hash(f"{category_slug}-{sku}")) % len(pool)
    return _resize_url(pool[index], 800)
