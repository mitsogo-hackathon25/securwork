from django.conf import settings
from django.http import HttpResponse

from store.models import Category, Product


def sitemap_xml(request):
    base = settings.FRONTEND_URL.rstrip("/")

    static_pages = [
        ("/", "daily", "1.0"),
        ("/shop", "daily", "0.9"),
        ("/about", "monthly", "0.7"),
        ("/contact", "monthly", "0.7"),
        ("/faq", "monthly", "0.6"),
        ("/pages/shipping", "monthly", "0.5"),
        ("/pages/returns", "monthly", "0.5"),
        ("/pages/privacy", "monthly", "0.4"),
        ("/pages/cookies", "monthly", "0.4"),
        ("/pages/terms", "monthly", "0.4"),
    ]

    urls = []
    for path, changefreq, priority in static_pages:
        urls.append(_url_entry(base + path, changefreq, priority))

    for cat in Category.objects.all():
        urls.append(_url_entry(f"{base}/shop?category={cat.slug}", "weekly", "0.7"))

    for product in Product.objects.filter(is_active=True):
        urls.append(_url_entry(f"{base}/product/{product.slug}", "weekly", "0.8"))

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return HttpResponse(xml, content_type="application/xml")


def _url_entry(loc, changefreq, priority):
    return (
        "  <url>\n"
        f"    <loc>{loc}</loc>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>"
    )
