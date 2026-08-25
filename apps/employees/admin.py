from django.contrib import admin
from django.db.models import Sum
from django.urls import path
from django.utils.html import format_html
from .models import Employee

# Branding only -- purely cosmetic, doesn't change any behaviour.
admin.site.site_header = "GapsIT Core Admin"
admin.site.site_title = "GapsIT Core Admin"
admin.site.index_title = "Dashboard"


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["name", "position", "role", "phone", "join_date", "is_admin"]
    list_filter = ["role", "position", "join_date"]
    search_fields = ["name", "user__username", "phone", "position"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("User Information", {"fields": ("user", "name", "role")}),
        ("Contact Information", {"fields": ("phone", "address", "emergency_contact")}),
        ("Employment Details", {"fields": ("position", "salary", "join_date")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def is_admin(self, obj):
        return obj.is_admin

    is_admin.boolean = True
    is_admin.short_description = "Admin Status"


# ----------------------------------------------------------------------
# Employee Management -- a richer, role-scoped view of the same Employee
# table (employees + admins only), with an at-a-glance activity summary.
# Uses a proxy model so it shows up as its own entry in the admin sidebar
# without touching the original "Employee" registration above.
# ----------------------------------------------------------------------
class EmployeeManagement(Employee):
    class Meta:
        proxy = True
        verbose_name = "Employee (management)"
        verbose_name_plural = "🧑\u200d💼 Employee Management"


@admin.register(EmployeeManagement)
class EmployeeManagementAdmin(admin.ModelAdmin):
    list_display = ["name", "position", "role_badge", "phone", "join_date", "salary", "activity_today"]
    list_filter = ["role", "position", "join_date"]
    search_fields = ["name", "user__username", "phone", "position"]
    readonly_fields = ["created_at", "updated_at", "activity_summary"]
    ordering = ["name"]

    fieldsets = (
        ("User Information", {"fields": ("user", "name", "role")}),
        ("Contact Information", {"fields": ("phone", "address", "emergency_contact")}),
        ("Employment Details", {"fields": ("position", "salary", "join_date")}),
        ("Activity Summary", {"fields": ("activity_summary",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role__in=["employee", "admin"])

    def role_badge(self, obj):
        colors = {"admin": "#7c5cff", "employee": "#2fae6b", "user": "#888"}
        return format_html(
            '<span style="background:{}22;color:{};padding:2px 8px;border-radius:999px;'
            'font-size:11px;font-weight:700;">{}</span>',
            colors.get(obj.role, "#888"), colors.get(obj.role, "#888"), obj.get_role_display(),
        )

    role_badge.short_description = "Role"

    def activity_today(self, obj):
        from django.utils import timezone
        from apps.activity.models import ActivitySession
        from apps.employees.stats import fmt_hms

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        agg = ActivitySession.objects.filter(
            owner=obj.user, start_time__gte=today_start
        ).aggregate(active=Sum("total_active_seconds"))
        return fmt_hms(agg["active"] or 0)

    activity_today.short_description = "Active Today"

    def activity_summary(self, obj):
        from apps.activity.models import ActivitySession
        from apps.employees.stats import fmt_hms, productivity_pct

        sessions = ActivitySession.objects.filter(owner=obj.user).order_by("-start_time")[:5]
        if not sessions:
            return "No synced activity sessions yet."
        rows = "".join(
            format_html(
                "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>",
                s.start_time.strftime("%Y-%m-%d %H:%M"),
                fmt_hms(s.total_active_seconds),
                fmt_hms(s.total_afk_seconds),
                (
                    f"{productivity_pct(s.total_active_seconds, s.total_afk_seconds, s.total_blocked_seconds)}%"
                    if productivity_pct(s.total_active_seconds, s.total_afk_seconds, s.total_blocked_seconds) is not None
                    else "—"
                ),
            )
            for s in sessions
        )
        return format_html(
            '<table style="width:100%;"><tr><th>Start</th><th>Active</th><th>AFK</th>'
            "<th>Productivity</th></tr>{}</table>",
            rows,
        )

    activity_summary.short_description = "Last 5 sessions"


# ----------------------------------------------------------------------
# User Management -- plain "user" accounts (self-registered, not yet
# promoted to employee). Separate sidebar entry so admins can review
# signups and promote them without wading through the full roster.
# ----------------------------------------------------------------------
class UserManagement(Employee):
    class Meta:
        proxy = True
        verbose_name = "User"
        verbose_name_plural = "👤 User Management"


@admin.register(UserManagement)
class UserManagementAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "phone", "created_at"]
    search_fields = ["name", "user__username", "user__email", "phone"]
    readonly_fields = ["created_at", "updated_at"]
    actions = ["promote_to_employee"]

    fieldsets = (
        ("User Information", {"fields": ("user", "name", "role")}),
        ("Contact Information", {"fields": ("phone", "address", "emergency_contact")}),
        (
            "Employment Details (fill in before promoting)",
            {"fields": ("position", "salary", "join_date")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role="user")

    def has_add_permission(self, request):
        # Accounts are created via self-registration only.
        return False

    def promote_to_employee(self, request, queryset):
        missing, promoted = 0, 0
        for emp in queryset:
            if not emp.position or emp.salary is None or not emp.join_date:
                missing += 1
                continue
            emp.role = "employee"
            emp.save()
            promoted += 1
        if promoted:
            self.message_user(request, f"Promoted {promoted} user(s) to Employee.")
        if missing:
            self.message_user(
                request,
                f"Skipped {missing} user(s): fill in position, salary, and join date first.",
                level="warning",
            )

    promote_to_employee.short_description = "Promote selected users to Employee"


# ----------------------------------------------------------------------
# CEO Work Table -- a full report page, not backed by its own model, so
# it's wired in as an extra admin URL rather than a ModelAdmin. Uses
# admin.site.admin_view() so it gets the same staff-login protection as
# every other admin page.
# ----------------------------------------------------------------------
_original_get_urls = admin.site.get_urls


def _get_urls_with_ceo_dashboard():
    from apps.employees.ceo_dashboard import ceo_work_table_view

    custom = [
        path(
            "ceo-work-table/",
            admin.site.admin_view(ceo_work_table_view),
            name="ceo-work-table",
        ),
    ]
    return custom + _original_get_urls()


admin.site.get_urls = _get_urls_with_ceo_dashboard
