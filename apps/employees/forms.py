from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Employee


class StyledAuthenticationForm(AuthenticationForm):
    """Login form -- same behaviour as Django's default, just styled widgets."""

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "Username", "autofocus": True}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Password"}
        )
    )


class EmployeeRegisterForm(forms.Form):
    """
    Self-service registration: creates a User + linked Employee profile
    in one step. Anyone can register this way and always lands with
    role='user' -- a plain account with no employment details yet.

    An admin later promotes a user to 'employee' (filling in position,
    salary, join date, etc. at that point) via the API's
    /api/employees/{id}/promote/ action, or through /admin/.
    """

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Username"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "Email"})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Confirm password"}
        ),
    )

    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Full name"}),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Phone number (optional)"}),
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-input", "rows": 3, "placeholder": "Address (optional)"}
        ),
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        if password1 and len(password1) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
        )
        employee = Employee.objects.create(
            user=user,
            name=self.cleaned_data["name"],
            phone=self.cleaned_data.get("phone", ""),
            address=self.cleaned_data.get("address", ""),
            role="user",
        )
        return user, employee
