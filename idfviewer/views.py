import codecs
import json
import re

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from eht.models import ProjectData

from .forms import PipelineUploadForm
from .ifc_parser import IFCDependencyError, IFCParseError, parse_multiple_ifc_uploads
from .models import IDFFile
from .parser import parse_multiple_idf_texts
from .pcf_parser import parse_multiple_pcf_texts
from .services import (
    build_download_payload,
    build_scene_from_saved_file,
    persist_preview_scene,
)


def decode_pipeline_bytes(raw: bytes) -> str:
    """
    Robust decoder for plant pipeline files.
    IDF files are often UTF-16 LE, while PCF is usually plain text.
    """
    encodings_to_try = []

    if raw.startswith(codecs.BOM_UTF16_LE) or raw.startswith(codecs.BOM_UTF16_BE):
        encodings_to_try = ["utf-16", "utf-16-le", "utf-16-be", "utf-8-sig", "utf-8"]
    else:
        encodings_to_try = ["utf-8-sig", "utf-8", "utf-16", "utf-16-le", "cp1252", "latin-1"]

    for enc in encodings_to_try:
        try:
            text = raw.decode(enc)
            if text.count("\x00") > 10:
                continue
            return text
        except UnicodeDecodeError:
            continue

    return raw.decode("latin-1", errors="replace")


def detect_pipeline_format(filename: str, text: str) -> str | None:
    lower_name = filename.lower()
    if lower_name.endswith(".idf"):
        return "IDF"
    if lower_name.endswith(".pcf"):
        return "PCF"
    if lower_name.endswith(".ifc"):
        return "IFC"

    head = text[:4000].upper()
    if "PIPELINE-REFERENCE" in head and "MATERIALS" in head and ("END-POINT" in head or "CO-ORDS" in head):
        return "PCF"
    if "ISO-10303-21" in head and "FILE_SCHEMA" in head and "IFC" in head:
        return "IFC"
    if re.search(r"^\s*[+-]?\d+", text, re.MULTILINE):
        return "IDF"
    return None


def _viewer_context(scene, project, filename, saved_file=None):
    stats = scene.get("stats") or {}
    return {
        "scene": scene,
        "filename": filename,
        "project": project,
        "saved_file": saved_file,
        "is_saved_scene": bool(saved_file),
        "save_supported": bool(stats.get("save_supported", True)) and not saved_file,
    }


def upload_idf_view(request):
    if request.method == "POST":
        form = PipelineUploadForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.cleaned_data["project"]
            f1 = form.cleaned_data.get("idf_files") or []
            f2 = form.cleaned_data.get("idf_directory") or []
            all_files = f1 + f2

            grouped_payloads = {"IDF": [], "PCF": [], "IFC": []}
            for uf in all_files:
                fname = uf.name.split("/")[-1]
                raw = uf.read()
                text = decode_pipeline_bytes(raw)
                detected_format = detect_pipeline_format(fname, text)
                if detected_format:
                    if detected_format == "IFC":
                        grouped_payloads[detected_format].append((fname, raw))
                    else:
                        grouped_payloads[detected_format].append((fname, text))

            idf_payloads = grouped_payloads["IDF"]
            pcf_payloads = grouped_payloads["PCF"]
            ifc_payloads = grouped_payloads["IFC"]

            active_formats = [name for name, payloads in grouped_payloads.items() if payloads]
            if len(active_formats) > 1:
                messages.error(request, "Please upload only one source format at a time. Mixed IDF, PCF, and IFC batches are not yet supported in a single scene.")
                return render(request, "idfviewer/upload.html", {"form": form})

            if not idf_payloads and not pcf_payloads and not ifc_payloads:
                messages.error(request, "No valid .idf, .pcf, or .ifc files found in upload.")
                return render(request, "idfviewer/upload.html", {"form": form})

            try:
                if ifc_payloads:
                    scene = parse_multiple_ifc_uploads(ifc_payloads, project)
                    filename = f"Batch: {len(ifc_payloads)} IFC file(s)"
                elif pcf_payloads:
                    scene = parse_multiple_pcf_texts(pcf_payloads, project)
                    filename = f"Batch: {len(pcf_payloads)} PCF file(s)"
                else:
                    scene = parse_multiple_idf_texts(idf_payloads, project)
                    filename = f"Batch: {len(idf_payloads)} IDF file(s)"
            except IFCDependencyError as exc:
                messages.error(request, str(exc))
                return render(request, "idfviewer/upload.html", {"form": form})
            except IFCParseError as exc:
                messages.error(request, str(exc))
                return render(request, "idfviewer/upload.html", {"form": form})

            return render(
                request,
                "idfviewer/viewer.html",
                _viewer_context(scene, project, filename),
            )
    else:
        form = PipelineUploadForm()

    return render(request, "idfviewer/upload.html", {"form": form})


@require_http_methods(["POST"])
def save_preview_view(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request payload."}, status=400)

    project_id = str(payload.get("project_id", "")).strip()
    scene = payload.get("scene")
    force = bool(payload.get("force"))

    if not project_id:
        return JsonResponse({"error": "Project is required."}, status=400)
    if not isinstance(scene, dict):
        return JsonResponse({"error": "Scene data is required."}, status=400)
    source_format = str(((scene.get("stats") or {}).get("source_format") or "")).upper()
    if source_format == "IFC":
        return JsonResponse(
            {"error": "IFC preview save is not enabled yet. Large IFC persistence will be added in a dedicated backend pass."},
            status=400,
        )

    project = get_object_or_404(ProjectData, proj_id=project_id)
    results = persist_preview_scene(project, scene, force=force)
    status_code = 409 if results["conflicts"] and not force else 200
    return JsonResponse(results, status=status_code)


def saved_library_view(request):
    selected_project_id = (request.GET.get("project_id") or "").strip()
    saved_files = IDFFile.objects.select_related("project").order_by("-last_saved_at", "-uploaded_at", "-pk")
    if selected_project_id:
        saved_files = saved_files.filter(project_id=selected_project_id)

    return render(
        request,
        "idfviewer/library.html",
        {
            "projects": ProjectData.objects.order_by("proj_id"),
            "saved_files": saved_files[:200],
            "selected_project_id": selected_project_id,
        },
    )


def saved_file_view(request, file_id):
    saved_file = get_object_or_404(IDFFile.objects.select_related("project"), pk=file_id)
    scene = build_scene_from_saved_file(saved_file)
    return render(
        request,
        "idfviewer/viewer.html",
        _viewer_context(scene, saved_file.project, saved_file.filename, saved_file=saved_file),
    )


def download_saved_file_view(request, file_id):
    saved_file = get_object_or_404(IDFFile.objects.select_related("project"), pk=file_id)
    payload = build_download_payload(saved_file)
    response = JsonResponse(payload, json_dumps_params={"indent": 2})
    download_name = re.sub(r"[^A-Za-z0-9._-]+", "_", saved_file.filename or "pipeline")
    response["Content-Disposition"] = f'attachment; filename="{download_name}.json"'
    return response
