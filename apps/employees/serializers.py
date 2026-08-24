from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from .models import Employee


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Add custom claims to JWT token including role.

    Also gates who is even allowed to obtain an API token in the first
    place: only promoted Employee/Admin accounts (or Django staff /
    superusers) can log in via /api/auth/login/. A freshly self-registered
    account defaults to Employee.role == "user" and is rejected here --
    they can still use the browser session login at /accounts/login/, they
    just can't pull a JWT for the API / desktop app until an admin promotes
    them (see EmployeeViewSet.promote).
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        try:
            employee = user.employee
            token["role"] = employee.role
            token["name"] = employee.name
            token["is_admin"] = employee.is_admin
        except Employee.DoesNotExist:
            token["role"] = "employee"
            token["name"] = user.username
            token["is_admin"] = user.is_staff or user.is_superuser

        return token

    def validate(self, attrs):
        # Runs after SimpleJWT has already authenticated username/password,
        # so self.user is set. Reject here, before any token is minted, if
        # the account isn't staff/superuser and isn't an employee or admin.
        data = super().validate(attrs)

        user = self.user
        try:
            employee = user.employee
            is_authorized = (
                employee.role in ("employee", "admin")
                or user.is_staff
                or user.is_superuser
            )
        except Employee.DoesNotExist:
            is_authorized = user.is_staff or user.is_superuser

        if not is_authorized:
            raise AuthenticationFailed(
                "Your account isn't approved for API access yet. "
                "Ask an admin to promote you to employee.",
                code="not_authorized",
            )

        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = ["id"]


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    is_admin = serializers.BooleanField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "user",
            "username",
            "email",
            "password",
            "name",
            "phone",
            "address",
            "emergency_contact",
            "salary",
            "position",
            "role",
            "join_date",
            "is_admin",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_role(self, value):
        """
        Only an admin may set/change role through this serializer. The
        view (EmployeeViewSet.perform_update / perform_create) is
        responsible for stripping 'role' out of validated_data for
        non-admin requests before save() is called, but we also guard
        here in case this serializer is ever reused elsewhere.
        """
        request = self.context.get("request")
        if request is not None:
            user = request.user
            is_admin = bool(
                user
                and user.is_authenticated
                and (user.is_staff or user.is_superuser or getattr(getattr(user, "employee", None), "is_admin", False))
            )
            if not is_admin:
                raise serializers.ValidationError("Only an admin can set the role field.")
        return value

    def create(self, validated_data):
        # Extract user data
        username = validated_data.pop("username", None)
        email = validated_data.pop("email", None)
        password = validated_data.pop("password", None)

        # Create user
        user = User.objects.create_user(
            username=username, email=email, password=password
        )

        # Create employee
        employee = Employee.objects.create(user=user, **validated_data)
        return employee


class EmployeeListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing employees"""

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    is_admin = serializers.BooleanField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "username",
            "email",
            "name",
            "phone",
            "position",
            "role",
            "is_admin",
            "join_date",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long"
            )
        return value

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user