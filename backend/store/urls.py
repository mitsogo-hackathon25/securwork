from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .admin_views import AdminBrandViewSet, AdminCategoryViewSet, AdminColorViewSet, AdminProductViewSet
from .views import CategoryViewSet, ProductViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")

admin_router = DefaultRouter()
admin_router.register("products", AdminProductViewSet, basename="admin-product")
admin_router.register("categories", AdminCategoryViewSet, basename="admin-category")
admin_router.register("brands", AdminBrandViewSet, basename="admin-brand")
admin_router.register("colors", AdminColorViewSet, basename="admin-color")

urlpatterns = [
    path("", include(router.urls)),
    path("admin/", include(admin_router.urls)),
]
