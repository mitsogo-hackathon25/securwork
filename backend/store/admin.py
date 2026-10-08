from django.contrib import admin
from parler.admin import TranslatableAdmin

from .models import Category, Product, ProductImage, ProductVariant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("sku", "size", "color", "price", "sale_price", "stock_quantity", "is_active")


@admin.register(Category)
class CategoryAdmin(TranslatableAdmin):
    list_display = ("name", "slug", "section", "parent", "sort_order", "is_active")
    list_filter = ("section", "is_active")
    search_fields = ("translations__name", "slug")
    prepopulated_fields = {"slug": ()}
    fieldsets = (
        (None, {"fields": ("name", "description", "slug", "section", "parent", "image")}),
        ("Settings", {"fields": ("sort_order", "is_active")}),
    )


@admin.register(Product)
class ProductAdmin(TranslatableAdmin):
    list_display = ("name", "sku", "brand", "slug", "is_active", "is_featured", "in_stock_display", "created_at")
    list_filter = ("is_active", "is_featured", "is_new_arrival", "is_bestseller")
    search_fields = ("translations__name", "sku", "slug")
    filter_horizontal = ("categories",)
    inlines = [ProductVariantInline, ProductImageInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "sku", "brand", "categories")}),
        ("Content", {"fields": ("short_description", "description")}),
        ("Customization", {"fields": (
            "allows_customization", "mockup_front", "customization_fee",
            "embroidery_chest_enabled", "embroidery_chest_fee",
            "embroidery_large_enabled", "embroidery_large_fee",
            "dtf_chest_enabled", "dtf_chest_fee",
            "dtf_large_enabled", "dtf_large_fee",
        )}),
        ("SEO", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        ("Flags", {"fields": ("is_active", "is_featured", "is_new_arrival", "is_bestseller")}),
    )

    @admin.display(boolean=True, description="In stock")
    def in_stock_display(self, obj):
        return obj.in_stock


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "size", "color", "price", "sale_price", "stock_quantity", "is_active")
    list_filter = ("is_active", "size", "color")
    search_fields = ("sku", "product__translations__name")
    list_editable = ("stock_quantity", "price", "sale_price", "is_active")
