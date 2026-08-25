"""
Shared aggregation helpers used by:
  - the "beautiful" stat cards on the /admin/ homepage
    (apps/employees/context_processors.py)
  - the full CEO Work Table page (apps/employees/ceo_dashboard.py)

Kept in one place so both stay consistent and cheap to query.
"""
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Sum, Count, Max
from django.utils import timezone

from apps.employees.models import Employee
from apps.activity.models import ActivitySession


def fmt_hms(total_seconds):
    """1h 05m style formatting for a raw seconds count."""
    total_seconds = int(total_seconds or 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours and minutes:
        return f"{hours}h {minutes:02d}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def productivity_pct(active, afk, blocked):
    total = (active or 0) + (afk or 0) + (blocked or 0)
    if not total:
        return None
    return round(100 * (active or 0) / total, 1)


def range_bounds(range_key):
    """Return (start, label) for 'today' | 'week' | 'month'."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if range_key == "week":
        return today_start - timedelta(days=6), "Last 7 days"
    if range_key == "month":
        return today_start - timedelta(days=29), "Last 30 days"
    return today_start, "Today"


def employee_work_table(range_key="today"):
    """
    Per-employee aggregated ActivitySession totals for the given range,
    joined against the Employee roster so people with zero sessions in
    the range still show up (with zeroes) rather than disappearing.
    """
    start, label = range_bounds(range_key)

    totals_by_owner = {
        row["owner_id"]: row
        for row in ActivitySession.objects.filter(start_time__gte=start).values(
            "owner_id"
        ).annotate(
            active=Sum("total_active_seconds"),
            afk=Sum("total_afk_seconds"),
            blocked=Sum("total_blocked_seconds"),
            sessions=Count("id"),
            last_session=Max("start_time"),
        )
    }

    rows = []
    employees = Employee.objects.select_related("user").order_by("name")
    for emp in employees:
        agg = totals_by_owner.get(emp.user_id, {})
        active = agg.get("active", 0) or 0
        afk = agg.get("afk", 0) or 0
        blocked = agg.get("blocked", 0) or 0
        rows.append(
            {
                "employee": emp,
                "sessions": agg.get("sessions", 0) or 0,
                "active_seconds": active,
                "afk_seconds": afk,
                "blocked_seconds": blocked,
                "active_fmt": fmt_hms(active),
                "afk_fmt": fmt_hms(afk),
                "blocked_fmt": fmt_hms(blocked),
                "productivity": productivity_pct(active, afk, blocked),
                "last_session": agg.get("last_session"),
            }
        )

    # Busiest first, idle roster members trail to the bottom.
    rows.sort(key=lambda r: r["active_seconds"], reverse=True)
    return rows, label


def dashboard_summary():
    """Small set of headline numbers for the admin homepage cards."""
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    role_counts = {r["role"]: r["n"] for r in Employee.objects.values("role").annotate(n=Count("id"))}

    today_agg = ActivitySession.objects.filter(start_time__gte=today_start).aggregate(
        active=Sum("total_active_seconds"),
        afk=Sum("total_afk_seconds"),
        blocked=Sum("total_blocked_seconds"),
        sessions=Count("id"),
        people=Count("owner_id", distinct=True),
    )
    active = today_agg["active"] or 0
    afk = today_agg["afk"] or 0
    blocked = today_agg["blocked"] or 0

    top_rows, _ = employee_work_table("today")
    top_rows = [r for r in top_rows if r["active_seconds"] > 0][:8]

    return {
        "total_users": role_counts.get("user", 0),
        "total_employees": role_counts.get("employee", 0),
        "total_admins": role_counts.get("admin", 0),
        "total_accounts": User.objects.count(),
        "sessions_today": today_agg["sessions"] or 0,
        "people_active_today": today_agg["people"] or 0,
        "active_today_fmt": fmt_hms(active),
        "afk_today_fmt": fmt_hms(afk),
        "productivity_today": productivity_pct(active, afk, blocked),
        "chart_labels": json.dumps([r["employee"].name for r in top_rows]),
        "chart_active_hours": json.dumps(
            [round(r["active_seconds"] / 3600, 2) for r in top_rows]
        ),
    }
