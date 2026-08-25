from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AllowedAppViewSet,
    manage_allowed_apps_view,
    toggle_allowed_app_view,
    delete_allowed_app_view,
)

router = DefaultRouter()
router.register(r"allowed-apps", AllowedAppViewSet, basename="allowed-app")

urlpatterns = [
    path("", include(router.urls)),
]

# Browser-facing (session-based) admin page -- separate from the JWT API above.
allowlist_page_urlpatterns = [
    path("allowed-apps/", manage_allowed_apps_view, name="manage_allowed_apps"),
    path(
        "allowed-apps/<int:pk>/toggle/",
        toggle_allowed_app_view,
        name="toggle_allowed_app",
    ),
    path(
        "allowed-apps/<int:pk>/delete/",
        delete_allowed_app_view,
        name="delete_allowed_app",
    ),
]
