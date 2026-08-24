from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Employee
from .serializers import (
    EmployeeSerializer,
    EmployeeListSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
)
from .permissions import IsAdmin, IsOwnerOrAdmin, HasAdminAPIKey
from .forms import StyledAuthenticationForm, EmployeeRegisterForm


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token view that includes role in JWT and response"""

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Get the user from request
            from rest_framework_simplejwt.tokens import RefreshToken
            from django.contrib.auth import authenticate

            username = request.data.get("username")
            password = request.data.get("password")
            user = authenticate(username=username, password=password)

            if user:
                try:
                    employee = user.employee
                    response.data["role"] = employee.role
                    response.data["name"] = employee.name
                    response.data["is_admin"] = employee.is_admin
                except Employee.DoesNotExist:
                    response.data["role"] = "employee"
                    response.data["name"] = user.username
                    response.data["is_admin"] = user.is_staff or user.is_superuser

        return response


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Employee CRUD operations

    Endpoints:
    - GET /api/employees/ - List all employees (admin only)
    - POST /api/employees/ - Create new employee (admin only)
    - GET /api/employees/{id}/ - Retrieve employee (owner or admin)
    - PUT/PATCH /api/employees/{id}/ - Update employee (owner or admin)
    - DELETE /api/employees/{id}/ - Delete employee (admin only)
    - GET /api/employees/me/ - Get current user's employee info
    - POST /api/employees/change_password/ - Change password
    - POST /api/employees/{id}/promote/ - Promote a 'user' to 'employee' (admin only)
    - POST /api/employees/{id}/demote/ - Move an 'employee' back to 'user' (admin only)
    - POST /api/employees/verify_admin/ - Verify admin status (with API key)
    """

    queryset = Employee.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return EmployeeListSerializer
        return EmployeeSerializer

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ["create", "destroy", "list", "promote", "demote"]:
            # Only admins can create, delete, list all, or change someone's role
            permission_classes = [IsAuthenticated, IsAdmin]
        elif self.action in ["update", "partial_update", "retrieve"]:
            # Owner or admin can update/view
            permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        elif self.action == "verify_admin":
            # Requires API key
            permission_classes = [HasAdminAPIKey]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def perform_update(self, serializer):
        """
        Belt-and-suspenders: even though the serializer already rejects a
        non-admin trying to set 'role', strip it out here too so an owner
        editing their own record can never change their own role -- only
        the admin-only promote()/demote() actions (or /admin/) can do that.
        """
        user = self.request.user
        is_admin = bool(
            user.is_staff
            or user.is_superuser
            or getattr(getattr(user, "employee", None), "is_admin", False)
        )
        if not is_admin:
            serializer.validated_data.pop("role", None)
        serializer.save()

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current authenticated user's employee information"""
        try:
            employee = request.user.employee
            serializer = self.get_serializer(employee)
            return Response(serializer.data)
        except Employee.DoesNotExist:
            return Response(
                {"error": "Employee profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"])
    def change_password(self, request):
        """Change current user's password"""
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Password changed successfully"}, status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def promote(self, request, pk=None):
        """
        Admin-only: promote a plain 'user' to 'employee'.

        POST /api/employees/{id}/promote/
        Body: { "position": "...", "salary": 50000, "join_date": "2026-08-24",
                "emergency_contact": "..." (optional, keeps existing value if omitted) }
        """
        employee = self.get_object()

        if employee.role == "admin":
            return Response(
                {"error": "This account is already an admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if employee.role == "employee":
            return Response(
                {"error": "This account is already an employee."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        position = request.data.get("position")
        salary = request.data.get("salary")
        join_date = request.data.get("join_date")
        emergency_contact = request.data.get("emergency_contact", employee.emergency_contact)

        if not position or salary in (None, "") or not join_date:
            return Response(
                {"error": "position, salary, and join_date are required to promote to employee."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee.role = "employee"
        employee.position = position
        employee.salary = salary
        employee.join_date = join_date
        employee.emergency_contact = emergency_contact
        employee.save()

        return Response(EmployeeSerializer(employee, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def demote(self, request, pk=None):
        """
        Admin-only: move an 'employee' back down to a plain 'user'.
        Employment details (position/salary/join_date) are left on the
        record so nothing is lost if they're promoted again later.

        POST /api/employees/{id}/demote/
        """
        employee = self.get_object()

        if employee.role == "admin":
            return Response(
                {"error": "Cannot demote an admin via this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if employee.role == "user":
            return Response(
                {"error": "This account is already a plain user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee.role = "user"
        employee.save()

        return Response(EmployeeSerializer(employee, context={"request": request}).data)

    @action(detail=False, methods=["post"], permission_classes=[HasAdminAPIKey])
    def verify_admin(self, request):
        """
        Verify admin status for external services
        Requires X-API-Key header with valid admin API key

        Request body:
        {
            "user_id": 1  // or "username": "john"
        }

        Response:
        {
            "is_admin": true,
            "user_id": 1,
            "username": "john",
            "role": "admin",
            "name": "John Doe"
        }
        """
        user_id = request.data.get("user_id")
        username = request.data.get("username")

        if not user_id and not username:
            return Response(
                {"error": "user_id or username is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if user_id:
                employee = Employee.objects.get(user_id=user_id)
            else:
                employee = Employee.objects.get(user__username=username)

            return Response(
                {
                    "is_admin": employee.is_admin,
                    "user_id": employee.user.id,
                    "username": employee.user.username,
                    "role": employee.role,
                    "name": employee.name,
                }
            )
        except Employee.DoesNotExist:
            return Response(
                {"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND
            )


# ----------------------------------------------------------------------
# Browser-facing pages (session-based login), separate from the JWT API
# above. These render HTML so a person can sign in / register from a web
# browser -- the GapsSight desktop app keeps using /api/auth/login/.
# ----------------------------------------------------------------------


class EmployeeLoginView(LoginView):
    """GET/POST /accounts/login/ -- HTML login page using Django sessions."""

    template_name = "employees/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("dashboard")


def register_view(request):
    """GET/POST /accounts/register/ -- creates a User + Employee profile."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = EmployeeRegisterForm(request.POST)
        if form.is_valid():
            user, employee = form.save()
            django_login(request, user)
            messages.success(request, f"Welcome, {employee.name}! Your account was created.")
            return redirect("dashboard")
    else:
        form = EmployeeRegisterForm()

    return render(request, "employees/register.html", {"form": form})


def logout_view(request):
    django_logout(request)
    return redirect("login")


@login_required(login_url="login")
def dashboard_view(request):
    """A minimal landing page after login, showing the employee's own profile."""
    employee = getattr(request.user, "employee", None)
    return render(request, "employees/dashboard.html", {"employee": employee})
