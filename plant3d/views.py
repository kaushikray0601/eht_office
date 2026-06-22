import json

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .access import (
    conversion_jobs_for_user,
    model_objects_for_user,
    render_packages_for_user,
    render_tiles_for_user,
    source_models_for_user,
)
from .forms import SourceModelUploadForm
from .models import SourceModel
from .services import (
    create_source_model_from_upload,
    queue_ifc_geometry_conversion,
    queue_ifc_glb_conversion,
    queue_metadata_conversion,
)
from .storage import exists as storage_exists, read_bytes, read_text


def platform_home_view(request):
    sources = source_models_for_user(request.user)
    return render(
        request,
        "plant3d/home.html",
        {
            "source_count": sources.count(),
        },
    )


@require_http_methods(["GET", "POST"])
def source_upload_view(request):
    if request.method == "POST":
        form = SourceModelUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            source = create_source_model_from_upload(
                project=form.cleaned_data["project"],
                uploaded_file=form.cleaned_data["source_file"],
                display_name=form.cleaned_data.get("display_name") or "",
                source_system=form.cleaned_data.get("source_system") or "",
            )
            return redirect("plant3d_source_detail", source_id=source.pk)
    else:
        form = SourceModelUploadForm(user=request.user)

    return render(request, "plant3d/source_upload.html", {"form": form})


def source_detail_view(request, source_id):
    source = get_object_or_404(source_models_for_user(request.user).select_related("project"), pk=source_id)
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
    sources = source_models_for_user(request.user).select_related("project").order_by("-created_at", "-pk")
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
    source = get_object_or_404(source_models_for_user(request.user), pk=source_id)
    job = queue_metadata_conversion(source)
    return JsonResponse(
        {
            "job": {
                "id": job.pk,
                "job_type": job.job_type,
                "status": job.status,
                "progress_percent": job.progress_percent,
                "metrics": job.metrics,
                "url": reverse("plant3d_job_json", args=[job.pk]),
            },
            "process_hint": f"venv/bin/python manage.py process_plant3d_job {job.pk}",
        },
        status=202,
    )


@require_http_methods(["POST"])
def source_ifc_geometry_convert_view(request, source_id):
    source = get_object_or_404(source_models_for_user(request.user), pk=source_id)
    job = queue_ifc_geometry_conversion(source)
    return JsonResponse(
        {
            "job": {
                "id": job.pk,
                "job_type": job.job_type,
                "status": job.status,
                "progress_percent": job.progress_percent,
                "metrics": job.metrics,
                "url": reverse("plant3d_job_json", args=[job.pk]),
            },
            "process_hint": f"venv/bin/python manage.py process_plant3d_job {job.pk}",
        },
        status=202,
    )


@require_http_methods(["POST"])
def source_ifc_glb_convert_view(request, source_id):
    source = get_object_or_404(source_models_for_user(request.user), pk=source_id)
    job = queue_ifc_glb_conversion(source)
    return JsonResponse(
        {
            "job": {
                "id": job.pk,
                "job_type": job.job_type,
                "status": job.status,
                "progress_percent": job.progress_percent,
                "metrics": job.metrics,
                "url": reverse("plant3d_job_json", args=[job.pk]),
            },
            "process_hint": f"venv/bin/python manage.py process_plant3d_job {job.pk}",
        },
        status=202,
    )


def job_json_view(request, job_id):
    job = get_object_or_404(conversion_jobs_for_user(request.user).select_related("source_model"), pk=job_id)
    package = job.render_packages.order_by("-created_at").first()
    return JsonResponse(
        {
            "id": job.pk,
            "source_model_id": job.source_model_id,
            "job_type": job.job_type,
            "url": reverse("plant3d_job_json", args=[job.pk]),
            "status": job.status,
            "progress_percent": job.progress_percent,
            "tool_name": job.tool_name,
            "error_message": job.error_message,
            "metrics": job.metrics,
            "process_hint": f"venv/bin/python manage.py process_plant3d_job {job.pk}",
            "package": {
                "id": package.pk,
                "package_format": package.package_format,
                "manifest_storage_key": package.manifest_storage_key,
                "tile_count": package.tile_count,
                "object_count": package.object_count,
                "byte_size": package.byte_size,
                "viewer_url": reverse("plant3d_package_viewer", args=[package.pk]),
                "json_url": reverse("plant3d_package_json", args=[package.pk]),
            } if package else None,
        }
    )


def package_viewer_view(request, package_id):
    package = get_object_or_404(
        render_packages_for_user(request.user).select_related("source_model", "source_model__project"),
        pk=package_id,
    )
    return render(
        request,
        "plant3d/package_viewer.html",
        {
            "package": package,
            "source": package.source_model,
            "package_api_url": reverse("plant3d_package_json", args=[package.pk]),
        },
    )


def package_json_view(request, package_id):
    package = get_object_or_404(render_packages_for_user(request.user).select_related("source_model"), pk=package_id)
    tiles = package.tiles.order_by("sequence", "pk")
    objects = package.model_objects.order_by("stable_id", "pk")
    return JsonResponse(
        {
            "id": package.pk,
            "source_model_id": package.source_model_id,
            "source_display_name": package.source_model.display_name,
            "package_format": package.package_format,
            "object_count": package.object_count,
            "tile_count": package.tile_count,
            "byte_size": package.byte_size,
            "coordinate_unit": package.coordinate_unit,
            "coordinate_frame": package.coordinate_frame,
            "bounds": package.bounds,
            "metadata": package.metadata,
            "objects": [
                {
                    "id": obj.pk,
                    "stable_id": obj.stable_id,
                    "source_object_id": obj.source_object_id,
                    "object_type": obj.object_type,
                    "tag": obj.tag,
                    "line_id": obj.line_id,
                    "bounds": obj.bounds,
                    "url": reverse("plant3d_model_object_json", args=[obj.pk]),
                }
                for obj in objects
            ],
            "tiles": [
                {
                    "id": tile.pk,
                    "tile_id": tile.tile_id,
                    "sequence": tile.sequence,
                    "object_count": tile.object_count,
                    "byte_size": tile.byte_size,
                    "bounds": tile.bounds,
                    "rtc_origin": tile.rtc_origin,
                    "url": reverse("plant3d_tile_json", args=[tile.pk]),
                    "metadata_url": reverse("plant3d_tile_json", args=[tile.pk]),
                    "blob_url": reverse("plant3d_tile_blob", args=[tile.pk]),
                    "content_type": tile.metadata.get("tile_type", ""),
                }
                for tile in tiles
            ],
        }
    )


def model_object_json_view(request, object_id):
    model_object = get_object_or_404(
        model_objects_for_user(request.user).select_related("source_model", "render_tile"),
        pk=object_id,
    )
    return JsonResponse(
        {
            "id": model_object.pk,
            "source_model_id": model_object.source_model_id,
            "stable_id": model_object.stable_id,
            "source_object_id": model_object.source_object_id,
            "object_type": model_object.object_type,
            "tag": model_object.tag,
            "line_id": model_object.line_id,
            "bounds": model_object.bounds,
            "metadata": model_object.metadata,
        }
    )


def tile_json_view(request, tile_id):
    tile = get_object_or_404(render_tiles_for_user(request.user), pk=tile_id)
    storage_key = tile.metadata.get("sidecar_storage_key") or tile.storage_key
    if not storage_exists(storage_key):
        return JsonResponse({"error": "Tile payload is missing from storage."}, status=404)

    try:
        payload = json.loads(read_text(storage_key))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Tile payload is not valid JSON."}, status=500)

    return JsonResponse(payload)


def tile_blob_view(request, tile_id):
    tile = get_object_or_404(render_tiles_for_user(request.user), pk=tile_id)
    if not storage_exists(tile.storage_key):
        return JsonResponse({"error": "Tile blob is missing from storage."}, status=404)
    response = HttpResponse(read_bytes(tile.storage_key), content_type="model/gltf-binary")
    response["Content-Length"] = str(tile.byte_size)
    response["Content-Disposition"] = f'inline; filename="{tile.tile_id}.glb"'
    return response
