from django.contrib import admin
from parler.admin import TranslatableAdmin

from .models import ContactSubmission, FAQItem, Page


@admin.register(Page)
class PageAdmin(TranslatableAdmin):
    list_display = ("title", "page_type", "slug", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("translations__title", "slug")


@admin.register(FAQItem)
class FAQItemAdmin(TranslatableAdmin):
    list_display = ("question", "sort_order", "is_published")
    list_editable = ("sort_order", "is_published")


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    readonly_fields = ("name", "email", "phone", "subject", "message", "created_at")
