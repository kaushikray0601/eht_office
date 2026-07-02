from django.urls import path

from . import views

urlpatterns = [
    path("", views.platform_home_view, name="plant3d_home"),
    path("sources/", views.source_models_json_view, name="plant3d_source_models_json"),
    path("sources/upload/", views.source_upload_view, name="plant3d_source_upload"),
    path("sources/<int:source_id>/", views.source_detail_view, name="plant3d_source_detail"),
    path("sources/<int:source_id>/save-case/", views.source_save_case_view, name="plant3d_source_save_case"),
    path("sources/<int:source_id>/delete/", views.source_delete_view, name="plant3d_source_delete"),
    path("sources/<int:source_id>/convert-metadata/", views.source_metadata_convert_view, name="plant3d_source_metadata_convert"),
    path("sources/<int:source_id>/convert-ifc-geometry/", views.source_ifc_geometry_convert_view, name="plant3d_source_ifc_geometry_convert"),
    path("sources/<int:source_id>/convert-ifc-glb/", views.source_ifc_glb_convert_view, name="plant3d_source_ifc_glb_convert"),
    path("jobs/<int:job_id>/json/", views.job_json_view, name="plant3d_job_json"),
    path("packages/<int:package_id>/", views.package_viewer_view, name="plant3d_package_viewer"),
    path("packages/<int:package_id>/json/", views.package_json_view, name="plant3d_package_json"),
    path("objects/<int:object_id>/json/", views.model_object_json_view, name="plant3d_model_object_json"),
    path("tiles/<int:tile_id>/json/", views.tile_json_view, name="plant3d_tile_json"),
    path("tiles/<int:tile_id>/blob/", views.tile_blob_view, name="plant3d_tile_blob"),
]
