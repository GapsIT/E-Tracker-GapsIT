from django.contrib import admin

from .models import DownloadToken


@admin.register(DownloadToken)
class DownloadTokenAdmin(admin.ModelAdmin):
    """Read-only audit trail -- tokens are only ever created by the views."""

    list_display = ("user", "platform", "created_at", "expires_at", "used_at", "ip_address")
    list_filter = ("platform",)
    search_fields = ("user__username", "token")
    readonly_fields = [f.name for f in DownloadToken._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
