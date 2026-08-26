from django.urls import path

from .views import request_download_view, serve_download_view

# Included under "accounts/" in core/urls.py, same as login/register/dashboard
# -> final paths are /core/accounts/download/<platform>/ and
#    /core/accounts/download/file/<token>/. Both views require an
#    authenticated session, so in practice they're only ever reached right
#    after a user has signed in at /core/accounts/login/.
release_page_urlpatterns = [
    path("download/<str:platform>/", request_download_view, name="gapsight_download_request"),
    path("download/file/<str:token>/", serve_download_view, name="gapsight_download_file"),
]
