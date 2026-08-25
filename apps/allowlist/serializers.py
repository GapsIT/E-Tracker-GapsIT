from rest_framework import serializers
from .models import AllowedApp


class AllowedAppSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = AllowedApp
        fields = [
            "id",
            "kind",
            "kind_display",
            "value",
            "is_active",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate_value(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate(self, attrs):
        """
        DB uniqueness is case-sensitive; the matching itself is
        case-insensitive, so also reject entries that only differ by case
        (e.g. 'GapsSight' vs 'gapssight') to avoid confusing duplicates.
        """
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        value = attrs.get("value", getattr(self.instance, "value", None))
        if kind and value:
            qs = AllowedApp.objects.filter(kind=kind, value__iexact=value)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"value": "An entry with this value already exists for this kind."}
                )
        return attrs


def build_sync_payload():
    """
    Shape this exactly like the local allowed-apps.json the GapsSight
    desktop app already reads, so the app can drop this straight in:

        {
          "allowedVsCodeProjects": [...],
          "allowedBrowserTabs": [...]
        }
    """
    active = AllowedApp.objects.filter(is_active=True)
    return {
        "allowedVsCodeProjects": list(
            active.filter(kind=AllowedApp.KIND_VSCODE).values_list("value", flat=True)
        ),
        "allowedBrowserTabs": list(
            active.filter(kind=AllowedApp.KIND_BROWSER).values_list("value", flat=True)
        ),
    }
