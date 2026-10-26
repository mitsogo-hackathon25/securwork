from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdminSupportTicketViewSet, SupportTicketViewSet

router = DefaultRouter()
router.register("support/tickets", SupportTicketViewSet, basename="support-ticket")

admin_router = DefaultRouter()
admin_router.register("support/tickets", AdminSupportTicketViewSet, basename="admin-support-ticket")

urlpatterns = [
    path("", include(router.urls)),
    path("admin/", include(admin_router.urls)),
]
