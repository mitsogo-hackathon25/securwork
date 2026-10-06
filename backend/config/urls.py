from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from cms.sitemap import sitemap_xml

urlpatterns = [
    path(f"{settings.DJANGO_ADMIN_PATH}/", admin.site.urls),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("api/", include("store.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("accounts.urls")),
    path("api/", include("cms.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "SecurWork Admin"
admin.site.site_title = "SecurWork"
admin.site.index_title = "Gestione negozio"
