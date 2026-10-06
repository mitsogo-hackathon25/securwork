from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseRedirect


class DevFrontendRedirectMiddleware:
    """Send browser traffic to the Vite dev server when DEBUG is enabled."""

    def __init__(self, get_response):
        self.get_response = get_response
        admin_prefix = f"/{settings.DJANGO_ADMIN_PATH.strip('/')}/"
        self.skip_prefixes = ("/api/", admin_prefix, "/static/", "/media/", "/sitemap.xml")

    def __call__(self, request):
        if settings.DEBUG and settings.FRONTEND_URL:
            path = request.path
            if path != "/favicon.ico" and not any(path.startswith(p) for p in self.skip_prefixes):
                # Match the request host so 127.0.0.1 and localhost both work
                parsed = urlparse(settings.FRONTEND_URL)
                host = request.get_host().split(":")[0]
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                scheme = parsed.scheme or ("https" if request.is_secure() else "http")
                frontend = f"{scheme}://{host}:{port}"
                query = request.META.get("QUERY_STRING", "")
                url = f"{frontend}{path}"
                if query:
                    url = f"{url}?{query}"
                return HttpResponseRedirect(url)
        return self.get_response(request)
