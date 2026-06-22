from django.urls import path

from . import views

urlpatterns = [
    path("", views.platform_home_view, name="plant3d_home"),
    path("sources/", views.source_models_json_view, name="plant3d_source_models_json"),
    path("sources/upload/", views.source_upload_view, name="plant3d_source_upload"),
    path("sources/<int:source_id>/", views.source_detail_view, name="plant3d_source_detail"),
    path("sources/<int:source_id>/convert-metadata/", views.source_metadata_convert_view, name="plant3d_source_metadata_convert"),
    path("sources/<int:source_id>/convert-ifc-geometry/", views.source_ifc_geometry_convert_view, name="plant3d_source_ifc_geometry_convert"),
]
