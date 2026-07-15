import json
from hashlib import sha256

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotModified, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .access import (
    conversion_jobs_for_user,
    model_objects_for_user,
    render_packages_for_user,
    render_tiles_for_user,
    source_models_for_user,
)
from .forms import SourceModelUploadForm
from .services import (
    create_source_model_from_upload,
    delete_source_models_and_storage,
    mark_source_saved_case,
    queue_ifc_geometry_conversion,
    queue_ifc_glb_conversion,
    queue_metadata_conversion,
)
from .storage import exists as storage_exists, read_bytes, read_text

PLANT3D_WORKER_COMMAND = "venv/bin/python manage.py process_plant3d_job --watch --parser-threads auto"
IMMUTABLE_RENDER_CACHE_CONTROL = "private, max-age=31536000, immutable"
HOME_SOURCE_LIMIT = 20
TIMING_LABELS = [
    ("source_read_ms", "source read"),
    ("parse_ms", "IFC parse"),
    ("context_metadata_ms", "metadata"),
    ("tile_grouping_ms", "tile grouping"),
    ("tile_prepare_ms", "tile prep"),
    ("json_build_ms", "JSON build"),
    ("glb_build_ms", "GLB build"),
    ("meshopt_hook_ms", "meshopt hook"),
    ("feature_id_validation_ms", "feature ID validation"),
    ("tile_write_ms", "tile write"),
    ("tileset_write_ms", "tileset write"),
    ("db_write_ms", "DB/index write"),
]


def viewer_extension_context():
    extensions = []
    for raw_extension in getattr(settings, "PLANT3D_VIEWER_EXTENSIONS", []):
        if not isinstance(raw_extension, dict):
            continue
        extension_id = str(raw_extension.get("id") or "").strip()
        script_path = str(raw_extension.get("script") or "").strip()
        script_url = str(raw_extension.get("script_url") or "").strip()
        if not extension_id or not (script_path or script_url):
            continue
        extensions.append(
            {
                "id": extension_id,
                "owner": str(raw_extension.get("owner") or "").strip(),
                "kind": str(raw_extension.get("kind") or "overlay").strip(),
                "script_url": script_url or static(script_path),
                "version": str(raw_extension.get("version") or "").strip(),
            }
        )
    return extensions


def _quoted_etag(value):
    return f'"{value}"'


def _immutable_etag(*parts):
    fingerprint = "|".join(str(part or "") for part in parts)
    return _quoted_etag(sha256(fingerprint.encode("utf-8")).hexdigest()[:32])


def _etag_matches(request, etag):
    candidates = [candidate.strip() for candidate in request.headers.get("If-None-Match", "").split(",")]
    return etag in candidates or "*" in candidates


def _apply_immutable_headers(response, etag):
    response["Cache-Control"] = IMMUTABLE_RENDER_CACHE_CONTROL
    response["ETag"] = etag
    return response


def _not_modified_response(etag):
    response = HttpResponseNotModified()
    return _apply_immutable_headers(response, etag)


def timing_summary_from_metrics(metrics):
    timings = (metrics or {}).get("timings") or {}
    if not isinstance(timings, dict):
        return []
    summary = []
    for key, label in TIMING_LABELS:
        if key in timings:
            summary.append({"key": key, "label": label, "ms": timings[key]})
    return summary


def _axis_extent(bounds, min_key, max_key):
    try:
        return round(float(bounds.get(max_key, 0)) - float(bounds.get(min_key, 0)), 6)
    except (TypeError, ValueError):
        return 0.0


def object_selection_summary(model_object):
    metadata = model_object.metadata if isinstance(model_object.metadata, dict) else {}
    bounds = model_object.bounds if isinstance(model_object.bounds, dict) else {}
    dimensions = {
        "x": _axis_extent(bounds, "min_x", "max_x"),
        "y": _axis_extent(bounds, "min_y", "max_y"),
        "z": _axis_extent(bounds, "min_z", "max_z"),
    }
    name = metadata.get("name") or metadata.get("description") or ""
    spatial_path = metadata.get("spatial_path") if isinstance(metadata.get("spatial_path"), list) else []
    display_label = model_object.tag or name or model_object.source_object_id or model_object.stable_id
    return {
        "display_label": display_label,
        "name": name,
        "object_type": model_object.object_type,
        "tag": model_object.tag,
        "line_id": model_object.line_id,
        "stable_id": model_object.stable_id,
        "source_object_id": model_object.source_object_id,
        "dimensions": dimensions,
        "dimension_unit": "m",
        "dimension_frame": "source_xyz",
        "spatial_path": spatial_path,
        "hierarchy_group": metadata.get("hierarchy_group") or "",
    }


def package_coordinate_transform(package):
    metadata = package.metadata if isinstance(package.metadata, dict) else {}
    transform = metadata.get("coordinate_transform")
    if isinstance(transform, dict):
        return transform
    return {
        "source_axis_order": metadata.get("source_axis_order") or ["x", "y", "z"],
        "render_axis_order": metadata.get("render_axis_order") or ["x", "z", "y"],
        "origin_source_xyz": metadata.get("origin_source_xyz") or metadata.get("raw_origin_source_xyz") or [],
        "rtc_origin_render_xyz": metadata.get("rtc_origin_render_xyz") or [],
        "scale_to_m": metadata.get("scale_to_m") or metadata.get("render_coordinate_scale_to_m") or 1,
    }


def _home_source_rows(sources):
    rows = []
    for source in sources:
        latest_package = source.render_packages.order_by("-created_at", "-pk").first()
        latest_job = source.conversion_jobs.order_by("-created_at", "-pk").first()
        rows.append(
            {
                "id": source.pk,
                "display_name": source.display_name or source.original_filename,
                "project_id": source.project_id,
                "source_format": source.source_format,
                "original_filename": source.original_filename,
                "created_at": source.created_at,
                "detail_url": reverse("plant3d_source_detail", args=[source.pk]),
                "viewer_url": reverse("plant3d_package_viewer", args=[latest_package.pk]) if latest_package else "",
                "package_format": latest_package.package_format if latest_package else "",
                "package_created_at": latest_package.created_at if latest_package else None,
                "job_status": latest_job.status if latest_job else "",
            }
        )
    return rows


def platform_home_view(request):
    sources = source_models_for_user(request.user).order_by("-created_at", "-pk")
    source_count = sources.count()
    source_rows = _home_source_rows(sources[:HOME_SOURCE_LIMIT])
    return render(
        request,
        "plant3d/home.html",
        {
            "source_count": source_count,
            "source_rows": source_rows,
            "source_limit": HOME_SOURCE_LIMIT,
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
                user=request.user,
            )
            return redirect("plant3d_source_detail", source_id=source.pk)
    else:
        form = SourceModelUploadForm(user=request.user)

    return render(request, "plant3d/source_upload.html", {"form": form})


def source_detail_view(request, source_id):
    source = get_object_or_404(source_models_for_user(request.user), pk=source_id)
    packages = source.render_packages.order_by("-created_at")
    latest_package = packages.first()
    jobs = list(source.conversion_jobs.order_by("-created_at"))
    for job in jobs:
        job.timing_summary = timing_summary_from_metrics(job.metrics)
    return render(
        request,
        "plant3d/source_detail.html",
        {
            "source": source,
            "packages": packages,
            "latest_package": latest_package,
            "jobs": jobs,
            "worker_command": PLANT3D_WORKER_COMMAND,
        },
    )


@require_http_methods(["POST"])
def source_save_case_view(request, source_id):
    source = get_object_or_404(source_models_for_user(request.user), pk=source_id)
    try:
        mark_source_saved_case(source)
    except ValueError as exc:
        return JsonResponse({"status": "error", "error": str(exc)}, status=400)
    if request.headers.get("Accept") == "application/json":
        return JsonResponse(
            {
                "status": "saved",
                "source_id": source.pk,
                "is_saved_case": source.is_saved_case,
                "saved_at": source.saved_at.isoformat() if source.saved_at else "",
            }
        )
    return redirect("plant3d_source_detail", source_id=source.pk)


@require_http_methods(["POST"])
def source_delete_view(request, source_id):
    source = get_object_or_404(source_models_for_user(request.user), pk=source_id)
    if source.uploaded_by_id and source.uploaded_by_id != request.user.id:
        return JsonResponse({"status": "error", "error": "Only the owner can delete this source model."}, status=403)
    result = delete_source_models_and_storage([source])
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"status": "deleted", **result})
    return redirect("plant3d_home")


def source_model_payload(source):
    return {
        "id": source.pk,
        "project_id": source.project_id,
        "display_name": source.display_name,
        "source_format": source.source_format,
        "original_filename": source.original_filename,
        "file_size_bytes": source.file_size_bytes,
        "content_signature": source.content_signature,
        "uploaded_by_id": source.uploaded_by_id,
        "is_saved_case": source.is_saved_case,
        "saved_at": source.saved_at.isoformat() if source.saved_at else "",
        "created_at": source.created_at.isoformat() if source.created_at else "",
        "detail_url": reverse("plant3d_source_detail", args=[source.pk]),
        "json_url": reverse("plant3d_source_json", args=[source.pk]),
    }


def source_models_json_view(request):
    sources = source_models_for_user(request.user).order_by("-created_at", "-pk")
    return JsonResponse(
        {
            "sources": [
                source_model_payload(source)
                for source in sources
            ],
        }
    )


def source_model_json_view(request, source_id):
    source = get_object_or_404(source_models_for_user(request.user), pk=source_id)
    latest_package = source.render_packages.order_by("-created_at").first()
    latest_job = source.conversion_jobs.order_by("-created_at").first()
    payload = source_model_payload(source)
    payload.update(
        {
            "latest_package": {
                "id": latest_package.pk,
                "package_format": latest_package.package_format,
                "tile_count": latest_package.tile_count,
                "object_count": latest_package.object_count,
                "byte_size": latest_package.byte_size,
                "viewer_url": reverse("plant3d_package_viewer", args=[latest_package.pk]),
                "json_url": reverse("plant3d_package_json", args=[latest_package.pk]),
            } if latest_package else None,
            "latest_job": {
                "id": latest_job.pk,
                "job_type": latest_job.job_type,
                "status": latest_job.status,
                "progress_percent": latest_job.progress_percent,
                "url": reverse("plant3d_job_json", args=[latest_job.pk]),
            } if latest_job else None,
        }
    )
    return JsonResponse(payload)


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
            "worker_hint": PLANT3D_WORKER_COMMAND,
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
            "worker_hint": PLANT3D_WORKER_COMMAND,
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
            "worker_hint": PLANT3D_WORKER_COMMAND,
        },
        status=202,
    )


def job_json_view(request, job_id):
    job = get_object_or_404(conversion_jobs_for_user(request.user).select_related("source_model"), pk=job_id)
    package = job.render_packages.order_by("-created_at").first()
    timing_summary = timing_summary_from_metrics(job.metrics)
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
            "timing_summary": timing_summary,
            "process_hint": f"venv/bin/python manage.py process_plant3d_job {job.pk}",
            "worker_hint": PLANT3D_WORKER_COMMAND,
            "package": {
                "id": package.pk,
                "package_format": package.package_format,
                "tile_count": package.tile_count,
                "object_count": package.object_count,
                "byte_size": package.byte_size,
                "viewer_url": reverse("plant3d_package_viewer", args=[package.pk]),
                "json_url": reverse("plant3d_package_json", args=[package.pk]),
            } if package else None,
        }
    )


@ensure_csrf_cookie
def package_viewer_view(request, package_id):
    package = get_object_or_404(
        render_packages_for_user(request.user).select_related("source_model"),
        pk=package_id,
    )
    return render(
        request,
        "plant3d/package_viewer.html",
        {
            "package": package,
            "source": package.source_model,
            "package_api_url": reverse("plant3d_package_json", args=[package.pk]),
            "viewer_extensions": viewer_extension_context(),
        },
    )


def package_json_view(request, package_id):
    package = get_object_or_404(render_packages_for_user(request.user).select_related("source_model"), pk=package_id)
    etag = _immutable_etag("package", package.pk, package.updated_at.isoformat(), package.byte_size, package.tile_count)
    if _etag_matches(request, etag):
        return _not_modified_response(etag)

    tiles = package.tiles.order_by("sequence", "pk")
    objects = package.model_objects.order_by("stable_id", "pk")
    object_payload = [
        {
            "id": obj.pk,
            "stable_id": obj.stable_id,
            "source_object_id": obj.source_object_id,
            "object_type": obj.object_type,
            "tag": obj.tag,
            "line_id": obj.line_id,
            "bounds": obj.bounds,
            "selection_summary": object_selection_summary(obj),
            "url": reverse("plant3d_model_object_json", args=[obj.pk]),
        }
        for obj in objects
    ]
    tile_payload = [
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
    ]
    tileset_payload = None
    if package.package_format == "GLB" and package.manifest_storage_key and storage_exists(package.manifest_storage_key):
        try:
            tileset_payload = json.loads(read_text(package.manifest_storage_key))
        except json.JSONDecodeError:
            tileset_payload = None
        if not (isinstance(tileset_payload, dict) and "asset" in tileset_payload and "root" in tileset_payload):
            tileset_payload = None

    if tileset_payload and tile_payload:
        tiles_by_id = {tile["tile_id"]: tile for tile in tile_payload}

        def enrich_tileset_node(node):
            extras = node.get("extras") or {}
            tile = tiles_by_id.get(extras.get("tile_id"))
            if tile:
                content = node.get("content") or {}
                content["url"] = tile["blob_url"]
                extras["metadata_url"] = tile["metadata_url"]
                node["content"] = content
            node["extras"] = extras
            node["children"] = [enrich_tileset_node(child) for child in node.get("children") or []]
            return node

        tileset_payload["root"] = enrich_tileset_node(tileset_payload.get("root") or {})

    response = JsonResponse(
        {
            "id": package.pk,
            "project_id": package.source_model.project_id,
            "source_model_id": package.source_model_id,
            "source_display_name": package.source_model.display_name,
            "package_format": package.package_format,
            "object_count": package.object_count,
            "tile_count": package.tile_count,
            "byte_size": package.byte_size,
            "coordinate_unit": package.coordinate_unit,
            "coordinate_frame": package.coordinate_frame,
            "coordinate_transform": package_coordinate_transform(package),
            "bounds": package.bounds,
            "metadata": package.metadata,
            "tileset": tileset_payload,
            "objects": object_payload,
            "tiles": tile_payload,
        }
    )
    return _apply_immutable_headers(response, etag)


def model_object_json_view(request, object_id):
    model_object = get_object_or_404(
        model_objects_for_user(request.user).select_related("source_model", "render_tile"),
        pk=object_id,
    )
    selection_summary = object_selection_summary(model_object)
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
            "selection_summary": selection_summary,
        }
    )


def tile_json_view(request, tile_id):
    tile = get_object_or_404(render_tiles_for_user(request.user), pk=tile_id)
    storage_key = tile.metadata.get("sidecar_storage_key") or tile.storage_key
    if not storage_exists(storage_key):
        return JsonResponse({"error": "Tile payload is missing from storage."}, status=404)
    etag = _immutable_etag("tile-json", tile.pk, storage_key, tile.byte_size, tile.created_at.isoformat())
    if _etag_matches(request, etag):
        return _not_modified_response(etag)

    try:
        payload = json.loads(read_text(storage_key))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Tile payload is not valid JSON."}, status=500)

    return _apply_immutable_headers(JsonResponse(payload), etag)


def tile_blob_view(request, tile_id):
    tile = get_object_or_404(render_tiles_for_user(request.user), pk=tile_id)
    if not storage_exists(tile.storage_key):
        return JsonResponse({"error": "Tile blob is missing from storage."}, status=404)
    etag = _immutable_etag("tile-blob", tile.pk, tile.storage_key, tile.byte_size, tile.created_at.isoformat())
    if _etag_matches(request, etag):
        return _not_modified_response(etag)
    response = HttpResponse(read_bytes(tile.storage_key), content_type="model/gltf-binary")
    response["Content-Length"] = str(tile.byte_size)
    response["Content-Disposition"] = f'inline; filename="{tile.tile_id}.glb"'
    return _apply_immutable_headers(response, etag)
