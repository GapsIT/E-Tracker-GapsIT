from django.conf import settings
from django.db import models


class AllowedApp(models.Model):
    """
    One entry in the GapsSight "on task" allow-list.

    This is the server-side source of truth for what used to live only in
    each machine's local allowed-apps.json. The GapsSight desktop app
    fetches the active set from /api/allowed-apps/sync/ and writes it into
    that file, so admins can manage it from here instead of editing JSON
    on every machine by hand.

    Matching (done client-side, by GapsSight) is a case-insensitive
    substring check against the active window title:
      - vscode_project: matched against the VS Code window title.
      - browser_tab: matched against a supported browser's window/tab title.
    """

    KIND_VSCODE = "vscode_project"
    KIND_BROWSER = "browser_tab"
    KIND_CHOICES = [
        (KIND_VSCODE, "VS Code project"),
        (KIND_BROWSER, "Browser tab"),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    value = models.CharField(
        max_length=255,
        help_text=(
            "Text matched as a case-insensitive substring against the "
            "active window title, e.g. 'GapsSight' or 'GapsSight – Figma'."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive entries are kept for reference but left out of sync.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="allowed_apps_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "value"], name="unique_allowedapp_kind_value"
            )
        ]

    def __str__(self):
        return f"[{self.get_kind_display()}] {self.value}"
