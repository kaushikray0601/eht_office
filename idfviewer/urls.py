from django.urls import path
from .views import (
    analyze_nearest_structure_view,
    download_saved_file_view,
    save_preview_view,
    saved_file_view,
    saved_library_view,
    upload_idf_view,
)

urlpatterns = [
    path("", upload_idf_view, name="idf_upload"),
    path("save/", save_preview_view, name="idf_save_preview"),
    path("analyze-nearest-structure/", analyze_nearest_structure_view, name="idf_analyze_nearest_structure"),
    path("library/", saved_library_view, name="idf_saved_library"),
    path("saved/<int:file_id>/", saved_file_view, name="idf_saved_file"),
    path("saved/<int:file_id>/download/", download_saved_file_view, name="idf_saved_file_download"),
]
