from django.urls import path

from . import views


app_name = "telemetry"

urlpatterns = [
    path("events/", views.events_view, name="events"),
]
