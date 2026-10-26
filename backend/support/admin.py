from django.contrib import admin

from .models import SupportMessage, SupportTicket


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    readonly_fields = ("author", "is_staff_reply", "created_at")


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "user", "status", "needs_staff_attention", "updated_at")
    list_filter = ("status", "needs_staff_attention", "needs_user_attention")
    inlines = [SupportMessageInline]
