from django.urls import path

from .views import ActivitySyncView, MyActivitySessionsView

urlpatterns = [
    path("activity/sync/", ActivitySyncView.as_view(), name="activity_sync"),
    path("activity/sessions/", MyActivitySessionsView.as_view(), name="activity_sessions"),
]
