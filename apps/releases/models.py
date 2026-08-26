from django.contrib.auth.models import User
from django.db import models


class DownloadToken(models.Model):
    """
    A one-time-use download link for a GapsSight installer.

    A token is created the moment a logged-in user clicks a "Download"
    button on their dashboard, and it is only ever valid for:
      - that one user,
      - one redemption (marked ``used_at`` the instant it's redeemed), and
      - a short expiry window (see ``GAPSIGHT_DOWNLOAD_TOKEN_MINUTES`` in
        settings).

    This is intentionally separate from the ``employees`` app -- it's a
    new, self-contained feature and doesn't touch any existing model.
    """

    PLATFORM_CHOICES = [
        ("windows", "Windows"),
        ("linux", "Linux"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="gapsight_download_tokens"
    )
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        state = "used" if self.used_at else "pending"
        return f"{self.user.username} - {self.get_platform_display()} ({state})"
