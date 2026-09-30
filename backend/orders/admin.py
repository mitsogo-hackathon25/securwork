from django.contrib import admin

from .models import Cart, Coupon, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "size", "color", "unit_price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "email", "status", "payment_status", "payment_method", "total", "created_at")
    list_filter = ("status", "payment_status", "payment_method", "created_at")
    search_fields = ("order_number", "email", "billing_last_name")
    readonly_fields = ("order_number", "created_at", "updated_at")
    inlines = [OrderItemInline]
    fieldsets = (
        ("Order", {"fields": ("order_number", "user", "status", "email", "phone", "language")}),
        ("Payment", {"fields": (
            "payment_method", "payment_status", "stripe_session_id",
            "stripe_payment_intent_id", "paid_at",
        )}),
        ("Billing", {"fields": (
            "billing_first_name", "billing_last_name", "billing_company",
            "billing_address", "billing_city", "billing_postcode", "billing_country", "billing_vat",
        )}),
        ("Shipping", {"fields": (
            "shipping_first_name", "shipping_last_name",
            "shipping_address", "shipping_city", "shipping_postcode", "shipping_country",
        )}),
        ("Totals", {"fields": ("subtotal", "shipping_cost", "tax_amount", "discount_amount", "total", "coupon_code")}),
        ("Notes", {"fields": ("notes", "created_at", "updated_at")}),
    )


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_percent", "discount_amount", "used_count", "max_uses", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "updated_at")
