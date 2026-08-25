"""
Injects dashboard stats into the template context ONLY when rendering the
Django admin homepage (/admin/). Every other page (including every other
admin page) gets an empty dict back immediately, so this has no effect
anywhere else in the app -- existing pages/behaviour are untouched.
"""


def gapsit_admin_dashboard(request):
    match = getattr(request, "resolver_match", None)
    if not match or match.view_name != "admin:index":
        return {}

    try:
        from apps.employees.stats import dashboard_summary

        return {"gapsit_dashboard": dashboard_summary()}
    except Exception:
        # Never let a stats query break the admin homepage.
        return {}
