from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("eht.urls")),
    path("idfviewer/", include("idfviewer.urls")),  # TEST: Temporarily added comment
]
