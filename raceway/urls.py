from django.urls import path

from . import views


app_name = "raceway"

urlpatterns = [
    path("", views.raceway_home_view, name="home"),
    path("catalog/", views.catalog_view, name="catalog"),
    path("projects/<str:project_id>/layers/", views.layer_collection_view, name="layer_collection"),
    path("layers/<int:layer_id>/", views.layer_detail_view, name="layer_detail"),
    path("layers/<int:layer_id>/graph/", views.layer_graph_view, name="layer_graph"),
    path("layers/<int:layer_id>/schedule/", views.layer_schedule_view, name="layer_schedule"),
    path("layers/<int:layer_id>/fittings/", views.layer_fittings_view, name="layer_fittings"),
    path("layers/<int:layer_id>/schedule.csv", views.layer_schedule_csv_view, name="layer_schedule_csv"),
    path("layers/<int:layer_id>/runs/", views.run_collection_view, name="layer_runs"),
    path("runs/<int:run_id>/", views.run_detail_view, name="run_detail"),
    path("runs/<int:run_id>/nodes/", views.run_nodes_view, name="run_nodes"),
]
