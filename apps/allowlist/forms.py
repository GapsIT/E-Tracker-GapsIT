from django import forms
from .models import AllowedApp


class AllowedAppForm(forms.Form):
    """Add-one-entry form used on the /accounts/allowed-apps/ management page."""

    kind = forms.ChoiceField(
        choices=AllowedApp.KIND_CHOICES,
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    value = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "e.g. GapsSight or GapsSight – Figma",
            }
        ),
    )

    def clean_value(self):
        value = self.cleaned_data["value"].strip()
        if not value:
            raise forms.ValidationError("This field may not be blank.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        kind = cleaned_data.get("kind")
        value = cleaned_data.get("value")
        if kind and value:
            if AllowedApp.objects.filter(kind=kind, value__iexact=value).exists():
                raise forms.ValidationError(
                    "An entry with this value already exists for this kind."
                )
        return cleaned_data
