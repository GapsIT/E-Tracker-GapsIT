from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeViewSet,
    EmployeeLoginView,
    register_view,
    logout_view,
    dashboard_view,
)

router = DefaultRouter()
router.register(r"employees", EmployeeViewSet, basename="employee")

urlpatterns = [
    path("", include(router.urls)),
]

# Browser-facing (session-based) pages -- separate from the JWT API above.
auth_page_urlpatterns = [
    path("login/", EmployeeLoginView.as_view(), name="login"),
    path("register/", register_view, name="register"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
]
