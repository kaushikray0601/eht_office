from django.urls import path
from .views import upload_idf_view

urlpatterns = [
    path("", upload_idf_view, name="idf_upload"),
]