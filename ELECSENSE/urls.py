from django.contrib import admin
from django.conf import settings
from django.urls import path, include

urlpatterns = [
    path(settings.ADMIN_SITE_PATH, admin.site.urls),
    path('', include("eht.urls")),
    path("idfviewer/", include("idfviewer.urls")),  # TEST: Temporarily added comment
]
