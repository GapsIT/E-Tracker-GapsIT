from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.employees.permissions import IsAdmin
from .forms import AllowedAppForm
from .models import AllowedApp
from .serializers import AllowedAppSerializer, build_sync_payload


def _user_is_admin(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return bool(getattr(getattr(user, "employee", None), "is_admin", False))


def admin_required(view_func):
    """Like @login_required, but also requires employee.is_admin (or staff)."""

    @wraps(view_func)
    @login_required(login_url="login")
    def wrapper(request, *args, **kwargs):
        if not _user_is_admin(request.user):
            messages.error(request, "You need admin access to manage allowed apps.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper


# ----------------------------------------------------------------------
# JWT API (used by GapsSight desktop app + admin tooling)
# ----------------------------------------------------------------------


class AllowedAppViewSet(viewsets.ModelViewSet):
    """
    Admin-only CRUD for allow-list entries, plus a /sync/ endpoint any
    authenticated (employee or admin) account can read.

    - GET/POST      /api/allowed-apps/            (admin only)
    - GET/PUT/PATCH /api/allowed-apps/{id}/        (admin only)
    - DELETE        /api/allowed-apps/{id}/        (admin only)
    - GET           /api/allowed-apps/sync/        (any authenticated employee)
    """

    queryset = AllowedApp.objects.all()
    serializer_class = AllowedAppSerializer

    def get_permissions(self):
        if self.action == "sync":
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated, IsAdmin]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def sync(self, request):
        """
        Returns the current active allow-list in the same shape as the
        local allowed-apps.json, e.g.:

            {
              "allowedVsCodeProjects": ["GapsSight"],
              "allowedBrowserTabs": ["GapsSight – Figma", "Gaps IT – Figma"]
            }

        The GapsSight desktop app calls this (with its normal JWT) and
        writes the result straight into its local allowed-apps.json.
        """
        return Response(build_sync_payload(), status=status.HTTP_200_OK)


# ----------------------------------------------------------------------
# Browser-facing admin page (session-based login), separate from the API
# above -- this is where an admin manages the list from a browser.
# ----------------------------------------------------------------------


@admin_required
def manage_allowed_apps_view(request):
    """GET/POST /accounts/allowed-apps/ -- add or list allow-list entries."""
    if request.method == "POST":
        form = AllowedAppForm(request.POST)
        if form.is_valid():
            AllowedApp.objects.create(
                kind=form.cleaned_data["kind"],
                value=form.cleaned_data["value"],
                created_by=request.user,
            )
            messages.success(request, "Entry added.")
            return redirect("manage_allowed_apps")
    else:
        form = AllowedAppForm()

    vscode_entries = AllowedApp.objects.filter(kind=AllowedApp.KIND_VSCODE)
    browser_entries = AllowedApp.objects.filter(kind=AllowedApp.KIND_BROWSER)

    return render(
        request,
        "allowlist/manage.html",
        {
            "form": form,
            "vscode_entries": vscode_entries,
            "browser_entries": browser_entries,
        },
    )


@admin_required
def toggle_allowed_app_view(request, pk):
    """POST /accounts/allowed-apps/{id}/toggle/ -- flip is_active."""
    entry = get_object_or_404(AllowedApp, pk=pk)
    if request.method == "POST":
        entry.is_active = not entry.is_active
        entry.save(update_fields=["is_active", "updated_at"])
        messages.success(
            request, f"'{entry.value}' is now {'active' if entry.is_active else 'inactive'}."
        )
    return redirect("manage_allowed_apps")


@admin_required
def delete_allowed_app_view(request, pk):
    """POST /accounts/allowed-apps/{id}/delete/ -- remove an entry for good."""
    entry = get_object_or_404(AllowedApp, pk=pk)
    if request.method == "POST":
        value = entry.value
        entry.delete()
        messages.success(request, f"Deleted '{value}'.")
    return redirect("manage_allowed_apps")
