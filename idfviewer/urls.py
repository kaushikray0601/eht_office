from django.urls import path
from .views import (
    analyze_nearest_structure_view,
    download_saved_file_view,
    eht_design_elements_view,
    project_attribute_mappings_view,
    save_preview_view,
    saved_file_view,
    saved_library_view,
    upload_idf_view,
)

urlpatterns = [
    path("", upload_idf_view, name="idf_upload"),
    path("save/", save_preview_view, name="idf_save_preview"),
    path("projects/<str:project_id>/attribute-mappings/", project_attribute_mappings_view, name="idf_attribute_mappings"),
    path("projects/<str:project_id>/eht-elements/", eht_design_elements_view, name="idf_eht_design_elements"),
    path("analyze-nearest-structure/", analyze_nearest_structure_view, name="idf_analyze_nearest_structure"),
    path("library/", saved_library_view, name="idf_saved_library"),
    path("saved/<int:file_id>/", saved_file_view, name="idf_saved_file"),
    path("saved/<int:file_id>/download/", download_saved_file_view, name="idf_saved_file_download"),
]
