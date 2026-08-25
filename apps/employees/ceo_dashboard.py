import json

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from apps.employees.stats import employee_work_table, dashboard_summary


@staff_member_required
def ceo_work_table_view(request):
    """
    /admin/ceo-work-table/ -- a full-page report across every employee,
    for the CEO/admins to see who's been working and how much, without
    digging through raw ActivitySession rows.
    """
    range_key = request.GET.get("range", "today")
    if range_key not in ("today", "week", "month"):
        range_key = "today"

    rows, label = employee_work_table(range_key)
    summary = dashboard_summary()

    worked_rows = [r for r in rows if r["active_seconds"] > 0][:15]

    context = {
        "title": "CEO Work Table",
        "site_title": "GapsIT Core Admin",
        "rows": rows,
        "range_key": range_key,
        "range_label": label,
        "summary": summary,
        "chart_labels": json.dumps([r["employee"].name for r in worked_rows]),
        "chart_active": json.dumps([round(r["active_seconds"] / 3600, 2) for r in worked_rows]),
        "chart_afk": json.dumps([round(r["afk_seconds"] / 3600, 2) for r in worked_rows]),
    }
    return render(request, "admin/ceo_work_table.html", context)
