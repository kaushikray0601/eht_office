from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import SourceModelUploadForm
from .models import SourceModel
from .services import create_source_model_from_upload, run_ifc_geometry_conversion, run_metadata_conversion


def platform_home_view(request):
    return render(
        request,
        "plant3d/home.html",
        {
            "source_count": SourceModel.objects.count(),
        },
    )


@require_http_methods(["GET", "POST"])
def source_upload_view(request):
    if request.method == "POST":
        form = SourceModelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            source = create_source_model_from_upload(
                project=form.cleaned_data["project"],
                uploaded_file=form.cleaned_data["source_file"],
                display_name=form.cleaned_data.get("display_name") or "",
                source_system=form.cleaned_data.get("source_system") or "",
            )
            return redirect("plant3d_source_detail", source_id=source.pk)
    else:
        form = SourceModelUploadForm()

    return render(request, "plant3d/source_upload.html", {"form": form})


def source_detail_view(request, source_id):
    source = get_object_or_404(SourceModel.objects.select_related("project"), pk=source_id)
    packages = source.render_packages.order_by("-created_at")
    jobs = source.conversion_jobs.order_by("-created_at")
    return render(
        request,
        "plant3d/source_detail.html",
        {
            "source": source,
            "packages": packages,
            "jobs": jobs,
        },
    )


def source_models_json_view(request):
    del request
    sources = SourceModel.objects.select_related("project").order_by("-created_at", "-pk")
    return JsonResponse(
        {
            "sources": [
                {
                    "id": source.pk,
                    "project_id": source.project_id,
                    "display_name": source.display_name,
                    "source_format": source.source_format,
                    "original_filename": source.original_filename,
                    "storage_key": source.storage_key,
                    "file_size_bytes": source.file_size_bytes,
                    "content_signature": source.content_signature,
                    "created_at": source.created_at.isoformat() if source.created_at else "",
                }
                for source in sources
            ],
        }
    )


@require_http_methods(["POST"])
def source_metadata_convert_view(request, source_id):
    del request
    source = get_object_or_404(SourceModel, pk=source_id)
    job, package = run_metadata_conversion(source)
    return JsonResponse(
        {
            "job": {
                "id": job.pk,
                "status": job.status,
                "progress_percent": job.progress_percent,
                "metrics": job.metrics,
            },
            "package": {
                "id": package.pk,
                "package_format": package.package_format,
                "manifest_storage_key": package.manifest_storage_key,
                "tile_count": package.tile_count,
                "byte_size": package.byte_size,
            },
        }
    )


@require_http_methods(["POST"])
def source_ifc_geometry_convert_view(request, source_id):
    del request
    source = get_object_or_404(SourceModel, pk=source_id)
    job, package = run_ifc_geometry_conversion(source)
    return JsonResponse(
        {
            "job": {
                "id": job.pk,
                "status": job.status,
                "progress_percent": job.progress_percent,
                "metrics": job.metrics,
            },
            "package": {
                "id": package.pk,
                "package_format": package.package_format,
                "manifest_storage_key": package.manifest_storage_key,
                "tile_count": package.tile_count,
                "object_count": package.object_count,
                "byte_size": package.byte_size,
            },
        }
    )
