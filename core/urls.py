from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from apps.employees.views import CustomTokenObtainPairView
from apps.employees.urls import auth_page_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT API endpoints (used by the GapsSight desktop app, Postman, etc.)
    path(
        "api/auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"
    ),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Employee CRUD API endpoints
    path("api/", include("apps.employees.urls")),
    # Browser-facing login / register / dashboard pages
    path("accounts/", include(auth_page_urlpatterns)),
]
