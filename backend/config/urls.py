from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from cms.sitemap import sitemap_xml

urlpatterns = [
    path(f"{settings.DJANGO_ADMIN_PATH}/", admin.site.urls),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("api/", include("store.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("accounts.urls")),
    path("api/", include("cms.urls")),
    path("api/", include("support.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Gunicorn behind Docker/nginx: proxy_pass /media/ → Django; whitenoise does not serve MEDIA.
    media_prefix = settings.MEDIA_URL.lstrip("/")
    urlpatterns += [
        re_path(
            rf"^{media_prefix}(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]

admin.site.site_header = "SecurWork Admin"
admin.site.site_title = "SecurWork"
admin.site.index_title = "Gestione negozio"
