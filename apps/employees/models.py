from django.db import models
from django.contrib.auth.models import User


class Employee(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("employee", "Employee"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee")
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")

    # Employment-only details. These aren't known/required until an admin
    # promotes a plain "user" to "employee", so they're optional at the DB
    # level and get filled in at promotion time (see EmployeeViewSet.promote).
    emergency_contact = models.CharField(max_length=20, blank=True, default="")
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    position = models.CharField(max_length=100, blank=True, default="")
    join_date = models.DateField(null=True, blank=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_employee(self):
        return self.role == "employee"
