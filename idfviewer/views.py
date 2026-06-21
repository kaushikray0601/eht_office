import codecs
import json
import re

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from eht.models import ProjectData

from .forms import PipelineUploadForm
from .analysis_utils import nearest_structure_report
from .eht_tools import (
    EHT_TOOL_DEFINITIONS,
    clean_eht_metadata,
    eht_tool_definition_payload,
    geometry_with_metrics,
)
from .ifc_parser import IFCDependencyError, IFCParseError, parse_multiple_ifc_uploads
from .models import EHTDesignElement, IDFFile, ProjectAttributeMapping
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


ATTRIBUTE_KEY_RE = re.compile(r"^ATTRIBUTE\d+$", re.I)


def _mapping_payload(mapping):
    return {
        "attribute_key": mapping.attribute_key,
        "display_name": mapping.display_name,
        "display_order": mapping.display_order,
    }


EHT_ELEMENT_TYPES = set(EHT_TOOL_DEFINITIONS)


def _eht_element_payload(element):
    return {
        "element_uid": element.element_uid,
        "element_type": element.element_type,
        "label": element.label,
        "geometry": geometry_with_metrics(element.geometry),
        "metadata": element.metadata,
        "updated_at": element.updated_at.isoformat() if element.updated_at else "",
    }


def _get_overlay_file(request, project):
    file_id = str(request.GET.get("file_id") or "").strip()
    if not file_id:
        return None
    return get_object_or_404(IDFFile, pk=file_id, project=project)


def _clean_eht_element(raw, index):
    if not isinstance(raw, dict):
        raise ValueError("Each EHT element must be an object.")

    element_uid = str(raw.get("element_uid", "")).strip()
    element_type = str(raw.get("element_type", "")).strip()
    label = str(raw.get("label", "")).strip()
    geometry = raw.get("geometry") or {}
    metadata = raw.get("metadata") or {}

    if not element_uid:
        raise ValueError(f"EHT element {index + 1} is missing an element_uid.")
    if len(element_uid) > 64:
        raise ValueError(f"EHT element {index + 1} has an element_uid that is too long.")
    if element_type not in EHT_ELEMENT_TYPES:
        raise ValueError(f"Unsupported EHT element type: {element_type or '(blank)'}.")
    if len(label) > 120:
        raise ValueError(f"EHT element {index + 1} label is too long.")
    if not isinstance(geometry, dict):
        raise ValueError(f"EHT element {index + 1} geometry must be an object.")
    if not isinstance(metadata, dict):
        raise ValueError(f"EHT element {index + 1} metadata must be an object.")

    geometry_type = str(geometry.get("type") or "").strip()
    points = geometry.get("points")
    if geometry_type not in {"point", "polyline"}:
        raise ValueError(f"EHT element {index + 1} geometry type must be point or polyline.")
    expected_geometry_type = EHT_TOOL_DEFINITIONS[element_type]["geometry_type"]
    if geometry_type != expected_geometry_type:
        raise ValueError(
            f"EHT element {index + 1} geometry type must be {expected_geometry_type} for {element_type}."
        )
    if not isinstance(points, list) or not points:
        raise ValueError(f"EHT element {index + 1} geometry must include points.")
    if geometry_type == "point" and len(points) != 1:
        raise ValueError(f"EHT element {index + 1} point geometry must include exactly one point.")
    if geometry_type == "polyline" and len(points) < 2:
        raise ValueError(f"EHT element {index + 1} polyline geometry must include at least two points.")

    for point in points:
        if (
            not isinstance(point, list)
            or len(point) != 3
            or not all(isinstance(value, (int, float)) for value in point)
        ):
            raise ValueError(f"EHT element {index + 1} has an invalid coordinate point.")

    return {
        "element_uid": element_uid,
        "element_type": element_type,
        "label": label,
        "geometry": geometry_with_metrics(geometry),
        "metadata": clean_eht_metadata(element_type, metadata),
    }


@ensure_csrf_cookie
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


@require_http_methods(["GET", "POST"])
def project_attribute_mappings_view(request, project_id):
    project = get_object_or_404(ProjectData, proj_id=project_id)

    if request.method == "GET":
        mappings = ProjectAttributeMapping.objects.filter(
            project=project,
            source_format="PCF",
        ).order_by("display_order", "attribute_key")
        return JsonResponse({"mappings": [_mapping_payload(mapping) for mapping in mappings]})

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request payload."}, status=400)

    raw_mappings = payload.get("mappings")
    if not isinstance(raw_mappings, list):
        return JsonResponse({"error": "Mappings must be a list."}, status=400)

    cleaned = []
    seen = set()
    for index, item in enumerate(raw_mappings):
        if not isinstance(item, dict):
            return JsonResponse({"error": "Each mapping must be an object."}, status=400)

        attribute_key = str(item.get("attribute_key", "")).strip().upper()
        display_name = str(item.get("display_name", "")).strip()

        if not attribute_key and not display_name:
            continue
        if not ATTRIBUTE_KEY_RE.match(attribute_key):
            return JsonResponse({"error": f"Invalid attribute key: {attribute_key or '(blank)'}."}, status=400)
        if not display_name:
            return JsonResponse({"error": f"Display name is required for {attribute_key}."}, status=400)
        if len(display_name) > 120:
            return JsonResponse({"error": f"Display name for {attribute_key} is too long."}, status=400)
        if attribute_key in seen:
            return JsonResponse({"error": f"Duplicate mapping for {attribute_key}."}, status=400)

        seen.add(attribute_key)
        cleaned.append(
            ProjectAttributeMapping(
                project=project,
                source_format="PCF",
                attribute_key=attribute_key,
                display_name=display_name,
                display_order=index,
            )
        )

    with transaction.atomic():
        ProjectAttributeMapping.objects.filter(project=project, source_format="PCF").delete()
        if cleaned:
            ProjectAttributeMapping.objects.bulk_create(cleaned)

    mappings = ProjectAttributeMapping.objects.filter(
        project=project,
        source_format="PCF",
    ).order_by("display_order", "attribute_key")
    return JsonResponse({"mappings": [_mapping_payload(mapping) for mapping in mappings]})


@require_http_methods(["GET", "POST"])
def eht_design_elements_view(request, project_id):
    project = get_object_or_404(ProjectData, proj_id=project_id)
    saved_file = _get_overlay_file(request, project)

    if request.method == "GET":
        elements = EHTDesignElement.objects.filter(project=project, idf_file=saved_file)
        return JsonResponse({
            "elements": [_eht_element_payload(element) for element in elements],
            "tool_definitions": eht_tool_definition_payload(),
            "scope": {
                "project_id": project.proj_id,
                "file_id": saved_file.id if saved_file else None,
            },
        })

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request payload."}, status=400)

    raw_elements = payload.get("elements")
    if not isinstance(raw_elements, list):
        return JsonResponse({"error": "Elements must be a list."}, status=400)

    seen = set()
    cleaned = []
    try:
        for index, raw_element in enumerate(raw_elements):
            element = _clean_eht_element(raw_element, index)
            if element["element_uid"] in seen:
                raise ValueError(f"Duplicate EHT element UID: {element['element_uid']}.")
            seen.add(element["element_uid"])
            cleaned.append(element)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    with transaction.atomic():
        EHTDesignElement.objects.filter(project=project, idf_file=saved_file).delete()
        created = [
            EHTDesignElement(
                project=project,
                idf_file=saved_file,
                element_uid=element["element_uid"],
                element_type=element["element_type"],
                label=element["label"],
                geometry=element["geometry"],
                metadata=element["metadata"],
            )
            for element in cleaned
        ]
        if created:
            EHTDesignElement.objects.bulk_create(created)

    elements = EHTDesignElement.objects.filter(project=project, idf_file=saved_file)
    return JsonResponse({
        "elements": [_eht_element_payload(element) for element in elements],
        "tool_definitions": eht_tool_definition_payload(),
        "count": len(created),
    })


@require_http_methods(["POST"])
def analyze_nearest_structure_view(request):
    scene_payload = request.POST.get("scene", "")
    if not scene_payload:
        return JsonResponse({"error": "Scene data is required."}, status=400)

    try:
        scene = json.loads(scene_payload)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid scene payload."}, status=400)

    source_format = str(((scene.get("stats") or {}).get("source_format") or "")).upper()
    if source_format == "IFC":
        return JsonResponse(
            {"error": "Nearest-structure analysis expects an IDF or PCF scene as the active pipeline view."},
            status=400,
        )

    pipeline_count = sum(len(scene.get(bucket, []) or []) for bucket in ("pipes", "fittings", "welds", "supports", "markers"))
    if pipeline_count == 0:
        return JsonResponse({"error": "No pipeline geometry found in the current scene."}, status=400)

    reference_files = request.FILES.getlist("ifc_files")
    if not reference_files:
        return JsonResponse({"error": "Please choose one or more IFC files for analysis."}, status=400)

    ifc_payloads = []
    for upload in reference_files:
        filename = upload.name.split("/")[-1]
        if not filename.lower().endswith(".ifc"):
            continue
        ifc_payloads.append((filename, upload.read()))

    if not ifc_payloads:
        return JsonResponse({"error": "No valid IFC files were provided."}, status=400)

    try:
        ifc_scene = parse_multiple_ifc_uploads(ifc_payloads, None)
    except IFCDependencyError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except IFCParseError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    report = nearest_structure_report(scene, ifc_scene)
    report["source_format"] = source_format
    report["ifc_source_label"] = f"{len(ifc_payloads)} IFC file(s)"
    return JsonResponse(report)


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


@ensure_csrf_cookie
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
