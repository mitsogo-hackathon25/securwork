from django.urls import path

from .admin_views import AdminGlobalSettingsView, AdminHeroImageView
from .views import ContactView, FAQListView, PageDetailView, SiteConfigView

urlpatterns = [
    path("site-config/", SiteConfigView.as_view(), name="site-config"),
    path("pages/<str:page_type>/", PageDetailView.as_view(), name="page-detail"),
    path("faq/", FAQListView.as_view(), name="faq-list"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("admin/global-settings/", AdminGlobalSettingsView.as_view(), name="admin-global-settings"),
    path("admin/global-settings/hero-image/", AdminHeroImageView.as_view(), name="admin-hero-image"),
]
