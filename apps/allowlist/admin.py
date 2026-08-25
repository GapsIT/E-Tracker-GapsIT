from django.contrib import admin
from .models import AllowedApp


@admin.register(AllowedApp)
class AllowedAppAdmin(admin.ModelAdmin):
    list_display = ["value", "kind", "is_active", "created_by", "updated_at"]
    list_filter = ["kind", "is_active"]
    search_fields = ["value"]
    readonly_fields = ["created_at", "updated_at"]
