from django.apps import AppConfig


class AllowlistConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.allowlist"
    verbose_name = "Allowed Apps"
