from django.contrib import admin
from django.db.models import Sum, Count
from django.utils import timezone
from django.utils.html import format_html

from .models import ActivityGateCheck, ActivitySession, ActivityStatusChange


class ActivityGateCheckInline(admin.TabularInline):
    model = ActivityGateCheck
    extra = 0
    can_delete = False
    readonly_fields = [
        "timestamp",
        "mouse_x",
        "mouse_y",
        "mouse_moved",
        "key_pressed",
        "process_name",
        "window_title",
        "is_allowed_app",
        "is_present",
        "timer_running",
    ]
    max_num = 0  # backup data, view-only from admin -- never hand-add rows here


class ActivityStatusChangeInline(admin.TabularInline):
    model = ActivityStatusChange
    extra = 0
    can_delete = False
    readonly_fields = ["timestamp", "status", "reason"]
    max_num = 0


@admin.register(ActivitySession)
class ActivitySessionAdmin(admin.ModelAdmin):
    change_list_template = "admin/activity/activitysession/change_list.html"

    list_display = [
        "username",
        "owner",
        "client_session_id",
        "start_time",
        "end_time",
        "active_fmt",
        "afk_fmt",
        "blocked_fmt",
        "productivity_badge",
        "synced_at",
    ]
    list_filter = ["username", "owner"]
    search_fields = ["username", "owner__username", "client_session_id"]
    date_hierarchy = "start_time"
    readonly_fields = [
        "owner",
        "client_session_id",
        "username",
        "start_time",
        "end_time",
        "total_active_seconds",
        "total_afk_seconds",
        "total_blocked_seconds",
        "synced_at",
    ]
    inlines = [ActivityStatusChangeInline, ActivityGateCheckInline]

    def has_add_permission(self, request):
        # Backup data only arrives via the sync API, never hand-entered.
        return False

    @staticmethod
    def _fmt(total_seconds):
        total_seconds = int(total_seconds or 0)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes:02d}m"
        return f"{minutes}m"

    def active_fmt(self, obj):
        return self._fmt(obj.total_active_seconds)

    active_fmt.short_description = "Active"
    active_fmt.admin_order_field = "total_active_seconds"

    def afk_fmt(self, obj):
        return self._fmt(obj.total_afk_seconds)

    afk_fmt.short_description = "AFK"
    afk_fmt.admin_order_field = "total_afk_seconds"

    def blocked_fmt(self, obj):
        return self._fmt(obj.total_blocked_seconds)

    blocked_fmt.short_description = "Blocked"
    blocked_fmt.admin_order_field = "total_blocked_seconds"

    def productivity_badge(self, obj):
        total = obj.total_active_seconds + obj.total_afk_seconds + obj.total_blocked_seconds
        if not total:
            return format_html('<span style="color:#888;">no data</span>')
        pct = round(100 * obj.total_active_seconds / total, 1)
        color = "#2fae6b" if pct >= 70 else ("#c9a227" if pct >= 40 else "#c0392b")
        return format_html(
            '<span style="background:{}22;color:{};padding:2px 8px;border-radius:999px;'
            'font-size:11px;font-weight:700;">{}%</span>',
            color, color, pct,
        )

    productivity_badge.short_description = "Productivity"

    def changelist_view(self, request, extra_context=None):
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        agg = ActivitySession.objects.filter(start_time__gte=today_start).aggregate(
            active=Sum("total_active_seconds"),
            afk=Sum("total_afk_seconds"),
            blocked=Sum("total_blocked_seconds"),
            sessions=Count("id"),
            people=Count("owner_id", distinct=True),
        )
        extra_context = extra_context or {}
        extra_context["gap_activity_stats"] = {
            "active": self._fmt(agg["active"]),
            "afk": self._fmt(agg["afk"]),
            "blocked": self._fmt(agg["blocked"]),
            "sessions": agg["sessions"] or 0,
            "people": agg["people"] or 0,
        }
        return super().changelist_view(request, extra_context=extra_context)
