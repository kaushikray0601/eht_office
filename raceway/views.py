import csv
import json
import math
import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from plant3d.access import render_packages_for_user, source_models_for_user
from plant3d.overlay import validate_overlay_anchor

from .access import require_project_access
from .fittings import build_layer_fitting_projection
from .graph import build_layer_graph
from .models import RacewayFamily, RacewayLayer, RacewayNode, RacewayRun, RacewaySize
from .schedule import build_layer_schedule

RUN_ORIENTATION_PRESETS = {
    "open_up": {"label": "Open Up", "quarter_turns": 0},
    "roll_right": {"label": "Roll Right", "quarter_turns": 1},
    "open_down": {"label": "Open Down", "quarter_turns": 2},
    "roll_left": {"label": "Roll Left", "quarter_turns": 3},
}
RUN_ORIENTATION_SCHEMA = "raceway.orientation.v0"
RUN_SEGMENT_ORIENTATION_SCHEMA = "raceway.segment_orientation.v0"
RUN_SEGMENT_FACE_OFFSET_SCHEMA = "raceway.segment_face_offset.v0"
RUN_SEGMENT_FACE_OFFSET_EPSILON_M = 0.0005
RUN_SEGMENT_FACE_OFFSET_LIMIT_M = 5.0


def raceway_home_view(request):
    return JsonResponse(
        {
            "app": "raceway",
            "status": "ok",
            "boundary": "peer-consumer",
            "platform": "plant3d",
        }
    )


def _truthy_query(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _validation_payload(exc):
    if hasattr(exc, "message_dict"):
        return {
            field: [str(message) for message in messages]
            for field, messages in exc.message_dict.items()
        }
    return {"__all__": [str(message) for message in getattr(exc, "messages", [exc])]}


def _error_response(message, status=400, *, errors=None):
    payload = {"status": "error", "error": message}
    if errors:
        payload["errors"] = errors
    return JsonResponse(payload, status=status)


def _json_body(request):
    if not request.body:
        return {}
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValidationError("Request body must be valid JSON.")
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")
    return payload


def _optional_positive_int(value, field_name):
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: "Value must be a positive integer."})
    if parsed <= 0:
        raise ValidationError({field_name: "Value must be a positive integer."})
    return parsed


def _optional_non_negative_int(value, field_name):
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: "Value must be a non-negative integer."})
    if parsed < 0:
        raise ValidationError({field_name: "Value must be a non-negative integer."})
    return parsed


def _optional_float(value, field_name):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: "Value must be a number."})


def _metadata_value(payload, field_name):
    value = payload.get(field_name, {})
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValidationError({field_name: "Value must be an object."})
    return value


def _run_metadata_value(payload, field_name):
    metadata = dict(_metadata_value(payload, field_name))
    orientation = metadata.get("orientation")
    if orientation not in (None, ""):
        metadata["orientation"] = _orientation_payload(orientation, "metadata.orientation")
    segment_orientation = metadata.get("segment_orientation")
    if segment_orientation not in (None, ""):
        metadata["segment_orientation"] = _segment_orientation_payload(segment_orientation)
    segment_face_offset = metadata.get("segment_face_offset")
    if segment_face_offset not in (None, ""):
        metadata["segment_face_offset"] = _segment_face_offset_payload(segment_face_offset)
    return metadata


def _orientation_payload(orientation, field_name):
    if not isinstance(orientation, dict):
        raise ValidationError({field_name: "Orientation must be an object."})
    preset = str(orientation.get("preset") or "").strip()
    if preset not in RUN_ORIENTATION_PRESETS:
        raise ValidationError({f"{field_name}.preset": "Unsupported orientation preset."})
    preset_config = RUN_ORIENTATION_PRESETS[preset]
    return {
        "schema": RUN_ORIENTATION_SCHEMA,
        "preset": preset,
        "quarter_turns": preset_config["quarter_turns"],
        "label": preset_config["label"],
    }


def _segment_orientation_node_key(value, field_name):
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        raise ValidationError({field_name: "Node key must be a UUID."})


def _segment_orientation_payload(segment_orientation):
    if not isinstance(segment_orientation, dict):
        raise ValidationError({"metadata.segment_orientation": "Segment orientation must be an object."})
    raw_overrides = segment_orientation.get("overrides", [])
    if raw_overrides in (None, ""):
        raw_overrides = []
    if not isinstance(raw_overrides, list):
        raise ValidationError({"metadata.segment_orientation.overrides": "Overrides must be a list."})
    overrides_by_pair = {}
    for index, raw_override in enumerate(raw_overrides, start=1):
        if not isinstance(raw_override, dict):
            raise ValidationError({f"metadata.segment_orientation.overrides.{index}": "Override must be an object."})
        start_node_key = _segment_orientation_node_key(
            raw_override.get("start_node_key"),
            f"metadata.segment_orientation.overrides.{index}.start_node_key",
        )
        end_node_key = _segment_orientation_node_key(
            raw_override.get("end_node_key"),
            f"metadata.segment_orientation.overrides.{index}.end_node_key",
        )
        if start_node_key == end_node_key:
            raise ValidationError({f"metadata.segment_orientation.overrides.{index}": "Segment node keys must be different."})
        preset = str(raw_override.get("preset") or "").strip()
        if preset not in RUN_ORIENTATION_PRESETS:
            raise ValidationError({f"metadata.segment_orientation.overrides.{index}.preset": "Unsupported orientation preset."})
        preset_config = RUN_ORIENTATION_PRESETS[preset]
        overrides_by_pair[(start_node_key, end_node_key)] = {
            "start_node_key": start_node_key,
            "end_node_key": end_node_key,
            "preset": preset,
            "quarter_turns": preset_config["quarter_turns"],
            "label": preset_config["label"],
        }
    return {
        "schema": RUN_SEGMENT_ORIENTATION_SCHEMA,
        "overrides": list(overrides_by_pair.values()),
    }


def _segment_face_offset_payload(segment_face_offset):
    if not isinstance(segment_face_offset, dict):
        raise ValidationError({"metadata.segment_face_offset": "Segment face offset must be an object."})
    raw_overrides = segment_face_offset.get("overrides", [])
    if raw_overrides in (None, ""):
        raw_overrides = []
    if not isinstance(raw_overrides, list):
        raise ValidationError({"metadata.segment_face_offset.overrides": "Overrides must be a list."})
    overrides_by_pair = {}
    for index, raw_override in enumerate(raw_overrides, start=1):
        if not isinstance(raw_override, dict):
            raise ValidationError({f"metadata.segment_face_offset.overrides.{index}": "Override must be an object."})
        start_node_key = _segment_orientation_node_key(
            raw_override.get("start_node_key"),
            f"metadata.segment_face_offset.overrides.{index}.start_node_key",
        )
        end_node_key = _segment_orientation_node_key(
            raw_override.get("end_node_key"),
            f"metadata.segment_face_offset.overrides.{index}.end_node_key",
        )
        if start_node_key == end_node_key:
            raise ValidationError({f"metadata.segment_face_offset.overrides.{index}": "Segment node keys must be different."})
        try:
            face_offset_m = float(raw_override.get("face_offset_m"))
        except (TypeError, ValueError):
            raise ValidationError({f"metadata.segment_face_offset.overrides.{index}.face_offset_m": "Face offset must be a number."})
        if not math.isfinite(face_offset_m):
            raise ValidationError({f"metadata.segment_face_offset.overrides.{index}.face_offset_m": "Face offset must be finite."})
        if abs(face_offset_m) > RUN_SEGMENT_FACE_OFFSET_LIMIT_M:
            raise ValidationError(
                {
                    f"metadata.segment_face_offset.overrides.{index}.face_offset_m":
                    f"Face offset must be within +/-{RUN_SEGMENT_FACE_OFFSET_LIMIT_M:g} m."
                }
            )
        if abs(face_offset_m) < RUN_SEGMENT_FACE_OFFSET_EPSILON_M:
            continue
        overrides_by_pair[(start_node_key, end_node_key)] = {
            "start_node_key": start_node_key,
            "end_node_key": end_node_key,
            "face_offset_m": face_offset_m,
        }
    return {
        "schema": RUN_SEGMENT_FACE_OFFSET_SCHEMA,
        "overrides": list(overrides_by_pair.values()),
    }


def _adjacent_node_key_pairs(run):
    nodes = list(run.nodes.order_by("sequence", "pk").values_list("key", flat=True))
    return {
        (str(nodes[index - 1]), str(nodes[index]))
        for index in range(1, len(nodes))
    }


def _prune_stale_segment_orientation(run):
    metadata = dict(run.metadata or {})
    segment_orientation = metadata.get("segment_orientation")
    if not isinstance(segment_orientation, dict):
        return False
    raw_overrides = segment_orientation.get("overrides", [])
    if not isinstance(raw_overrides, list):
        metadata.pop("segment_orientation", None)
        run.metadata = metadata
        run.save(update_fields=["metadata"])
        return True
    adjacent_pairs = _adjacent_node_key_pairs(run)
    kept = [
        override
        for override in raw_overrides
        if (
            str(override.get("start_node_key") or ""),
            str(override.get("end_node_key") or ""),
        )
        in adjacent_pairs
    ]
    if len(kept) == len(raw_overrides):
        return False
    metadata["segment_orientation"] = {
        "schema": RUN_SEGMENT_ORIENTATION_SCHEMA,
        "overrides": kept,
    }
    run.metadata = metadata
    run.save(update_fields=["metadata"])
    return True


def _prune_stale_segment_face_offset(run):
    metadata = dict(run.metadata or {})
    segment_face_offset = metadata.get("segment_face_offset")
    if not isinstance(segment_face_offset, dict):
        return False
    raw_overrides = segment_face_offset.get("overrides", [])
    if not isinstance(raw_overrides, list):
        metadata.pop("segment_face_offset", None)
        run.metadata = metadata
        run.save(update_fields=["metadata"])
        return True
    adjacent_pairs = _adjacent_node_key_pairs(run)
    kept = [
        override
        for override in raw_overrides
        if (
            str(override.get("start_node_key") or ""),
            str(override.get("end_node_key") or ""),
        )
        in adjacent_pairs
    ]
    if len(kept) == len(raw_overrides):
        return False
    metadata["segment_face_offset"] = {
        "schema": RUN_SEGMENT_FACE_OFFSET_SCHEMA,
        "overrides": kept,
    }
    run.metadata = metadata
    run.save(update_fields=["metadata"])
    return True


def _node_key_from_payload(raw_node, index, existing_node_keys):
    raw_key = raw_node.get("key")
    if raw_key in (None, ""):
        return None
    try:
        parsed_key = uuid.UUID(str(raw_key))
    except (TypeError, ValueError, AttributeError):
        raise ValidationError({"nodes": f"Node {index + 1} key must be a UUID."})
    existing_key = existing_node_keys.get(str(parsed_key))
    if existing_key is None:
        raise ValidationError({"nodes": f"Node {index + 1} key does not belong to this raceway run."})
    return existing_key


def _validated_context(user, project_id, payload, *, default_source_model_id=None, default_render_package_id=None):
    source_model_id = _optional_positive_int(
        payload.get("source_model_id", default_source_model_id),
        "source_model_id",
    )
    render_package_id = _optional_positive_int(
        payload.get("render_package_id", default_render_package_id),
        "render_package_id",
    )
    package = None
    if source_model_id is not None:
        if not source_models_for_user(user).filter(pk=source_model_id, project_id=project_id).exists():
            raise ValidationError({"source_model_id": "Source model is not accessible for this project."})
    if render_package_id is not None:
        package = (
            render_packages_for_user(user)
            .select_related("source_model")
            .filter(pk=render_package_id, source_model__project_id=project_id)
            .first()
        )
        if package is None:
            raise ValidationError({"render_package_id": "Render package is not accessible for this project."})
        if source_model_id is not None and package.source_model_id != source_model_id:
            raise ValidationError({"render_package_id": "Render package does not belong to the source model."})
        if source_model_id is None:
            source_model_id = package.source_model_id
    return source_model_id, render_package_id


def _layer_for_user(user, layer_id):
    layer = RacewayLayer.objects.filter(pk=layer_id).first()
    if layer is None:
        return None
    require_project_access(layer.project_id, user)
    return layer


def _run_for_user(user, run_id):
    run = RacewayRun.objects.select_related("layer", "family", "size").filter(pk=run_id).first()
    if run is None:
        return None
    require_project_access(run.layer.project_id, user)
    return run


def _layer_payload(layer):
    return {
        "id": layer.pk,
        "project_id": layer.project_id,
        "source_model_id": layer.source_model_id,
        "render_package_id": layer.render_package_id,
        "name": layer.name,
        "description": layer.description,
        "status": layer.status,
        "revision": layer.revision,
        "metadata": layer.metadata,
        "created_by_id": layer.created_by_id,
        "created_at": layer.created_at.isoformat() if layer.created_at else "",
        "updated_at": layer.updated_at.isoformat() if layer.updated_at else "",
        "url": reverse("raceway:layer_detail", args=[layer.pk]),
        "runs_url": reverse("raceway:layer_runs", args=[layer.pk]),
        "graph_url": reverse("raceway:layer_graph", args=[layer.pk]),
        "schedule_url": reverse("raceway:layer_schedule", args=[layer.pk]),
        "fittings_url": reverse("raceway:layer_fittings", args=[layer.pk]),
    }


def _size_payload(size):
    return {
        "id": size.pk,
        "family_id": size.family_id,
        "code": f"{size.family.code}-{size.width_mm}x{size.depth_mm}",
        "label": f"{size.width_mm} x {size.depth_mm} mm",
        "width_mm": size.width_mm,
        "depth_mm": size.depth_mm,
        "weight_kg_per_m": size.weight_kg_per_m,
        "load_span_table": size.load_span_table,
        "metadata": size.metadata,
        "is_active": size.is_active,
    }


def _family_payload(family):
    return {
        "id": family.pk,
        "code": family.code,
        "name": family.name,
        "kind": family.kind,
        "material": family.material,
        "standard_length_mm": family.standard_length_mm,
        "standard_basis": family.standard_basis,
        "profile": family.profile,
        "metadata": family.metadata,
        "is_active": family.is_active,
        "is_validated": family.is_validated,
        "sizes": [_size_payload(size) for size in family.sizes.all()],
    }


def _run_family_payload(family):
    return {
        "id": family.pk,
        "code": family.code,
        "name": family.name,
        "kind": family.kind,
        "material": family.material,
        "standard_basis": family.standard_basis,
        "is_active": family.is_active,
        "is_validated": family.is_validated,
    }


def _run_size_payload(size):
    return {
        "id": size.pk,
        "family_id": size.family_id,
        "label": f"{size.width_mm} x {size.depth_mm} mm",
        "width_mm": size.width_mm,
        "depth_mm": size.depth_mm,
        "weight_kg_per_m": size.weight_kg_per_m,
        "is_active": size.is_active,
    }


def _node_payload(node):
    return {
        "id": node.pk,
        "key": str(node.key),
        "sequence": node.sequence,
        "node_kind": node.node_kind,
        "source_x_m": node.source_x_m,
        "source_y_m": node.source_y_m,
        "source_z_m": node.source_z_m,
        "anchor": node.anchor,
        "metadata": node.metadata,
    }


def _run_payload(run, *, include_nodes=False):
    payload = {
        "id": run.pk,
        "key": str(run.key),
        "layer_id": run.layer_id,
        "project_id": run.layer.project_id,
        "tag": run.tag,
        "family_id": run.family_id,
        "size_id": run.size_id,
        "family": _run_family_payload(run.family),
        "size": _run_size_payload(run.size),
        "service_class": run.service_class,
        "status": run.status,
        "coordinate_frame": run.coordinate_frame,
        "elevation_m": run.elevation_m,
        "source_model_id": run.source_model_id,
        "render_package_id": run.render_package_id,
        "validation_summary": run.validation_summary,
        "metadata": run.metadata,
        "created_at": run.created_at.isoformat() if run.created_at else "",
        "updated_at": run.updated_at.isoformat() if run.updated_at else "",
        "url": reverse("raceway:run_detail", args=[run.pk]),
        "nodes_url": reverse("raceway:run_nodes", args=[run.pk]),
    }
    if include_nodes:
        payload["nodes"] = [_node_payload(node) for node in run.nodes.order_by("sequence", "pk")]
    return payload


@require_http_methods(["GET"])
def catalog_view(request):
    active_sizes = RacewaySize.objects.filter(is_active=True).select_related("family").order_by("width_mm", "depth_mm")
    families = (
        RacewayFamily.objects.filter(is_active=True)
        .prefetch_related(Prefetch("sizes", queryset=active_sizes))
        .order_by("code")
    )
    return JsonResponse({"families": [_family_payload(family) for family in families]})


def _apply_layer_payload(layer, payload, user):
    layer.name = str(payload.get("name", layer.name or "")).strip()
    if not layer.name:
        raise ValidationError({"name": "Layer name is required."})
    if "description" in payload:
        layer.description = str(payload.get("description") or "")
    if "status" in payload:
        layer.status = payload.get("status") or "draft"
    if "revision" in payload:
        layer.revision = _optional_positive_int(payload.get("revision"), "revision") or 1
    if "metadata" in payload:
        layer.metadata = _metadata_value(payload, "metadata")
    source_model_id, render_package_id = _validated_context(
        user,
        layer.project_id,
        payload,
        default_source_model_id=layer.source_model_id,
        default_render_package_id=layer.render_package_id,
    )
    layer.source_model_id = source_model_id
    layer.render_package_id = render_package_id
    layer.full_clean()
    return layer


def _family_and_size(payload, current_family=None, current_size=None):
    family_id = _optional_positive_int(payload.get("family_id", current_family.pk if current_family else None), "family_id")
    size_id = _optional_positive_int(payload.get("size_id", current_size.pk if current_size else None), "size_id")
    if family_id is None:
        raise ValidationError({"family_id": "Raceway family is required."})
    if size_id is None:
        raise ValidationError({"size_id": "Raceway size is required."})
    family = RacewayFamily.objects.filter(pk=family_id, is_active=True).first()
    if family is None:
        raise ValidationError({"family_id": "Raceway family is not active or does not exist."})
    size = RacewaySize.objects.filter(pk=size_id, is_active=True).first()
    if size is None:
        raise ValidationError({"size_id": "Raceway size is not active or does not exist."})
    return family, size


def _apply_run_payload(run, payload, user):
    family, size = _family_and_size(payload, run.family if run.pk else None, run.size if run.pk else None)
    run.family = family
    run.size = size
    if "tag" in payload:
        run.tag = str(payload.get("tag") or "").strip()
    if "service_class" in payload:
        run.service_class = payload.get("service_class") or "power"
    if "status" in payload:
        run.status = payload.get("status") or "draft"
    if "elevation_m" in payload:
        run.elevation_m = _optional_float(payload.get("elevation_m"), "elevation_m")
    if "validation_summary" in payload:
        run.validation_summary = _metadata_value(payload, "validation_summary")
    if "metadata" in payload:
        run.metadata = _run_metadata_value(payload, "metadata")
    source_model_id, render_package_id = _validated_context(
        user,
        run.layer.project_id,
        payload,
        default_source_model_id=run.source_model_id or run.layer.source_model_id,
        default_render_package_id=run.render_package_id or run.layer.render_package_id,
    )
    run.source_model_id = source_model_id
    run.render_package_id = render_package_id
    run.full_clean()
    return run


@require_http_methods(["GET", "POST"])
def layer_collection_view(request, project_id):
    project_id = require_project_access(project_id, request.user)
    if request.method == "GET":
        layers = RacewayLayer.objects.filter(project_id=project_id).order_by("-updated_at", "-pk")
        source_filter = request.GET.get("source_model_id")
        package_filter = request.GET.get("render_package_id")
        try:
            if source_filter:
                layers = layers.filter(source_model_id=_optional_positive_int(source_filter, "source_model_id"))
            if package_filter:
                layers = layers.filter(render_package_id=_optional_positive_int(package_filter, "render_package_id"))
        except ValidationError as exc:
            return _error_response("Invalid raceway layer filter.", errors=_validation_payload(exc))
        return JsonResponse({"layers": [_layer_payload(layer) for layer in layers]})

    try:
        payload = _json_body(request)
        layer = RacewayLayer(project_id=project_id, created_by=request.user)
        _apply_layer_payload(layer, payload, request.user)
        layer.save()
    except ValidationError as exc:
        return _error_response("Invalid raceway layer payload.", errors=_validation_payload(exc))
    return JsonResponse({"layer": _layer_payload(layer)}, status=201)


@require_http_methods(["GET", "PATCH", "DELETE"])
def layer_detail_view(request, layer_id):
    layer = _layer_for_user(request.user, layer_id)
    if layer is None:
        return _error_response("Raceway layer was not found.", status=404)
    if request.method == "GET":
        return JsonResponse({"layer": _layer_payload(layer)})
    if request.method == "DELETE":
        layer.delete()
        return JsonResponse({"status": "deleted", "layer_id": layer_id})
    try:
        payload = _json_body(request)
        _apply_layer_payload(layer, payload, request.user)
        layer.save()
    except ValidationError as exc:
        return _error_response("Invalid raceway layer payload.", errors=_validation_payload(exc))
    return JsonResponse({"layer": _layer_payload(layer)})


@require_http_methods(["GET"])
def layer_graph_view(request, layer_id):
    layer = _layer_for_user(request.user, layer_id)
    if layer is None:
        return _error_response("Raceway layer was not found.", status=404)
    return JsonResponse({"layer": _layer_payload(layer), "graph": build_layer_graph(layer).to_payload()})


@require_http_methods(["GET"])
def layer_schedule_view(request, layer_id):
    layer = _layer_for_user(request.user, layer_id)
    if layer is None:
        return _error_response("Raceway layer was not found.", status=404)
    return JsonResponse({"layer": _layer_payload(layer), "schedule": build_layer_schedule(layer)})


def _json_detail(value):
    return json.dumps(value or {}, indent=2, sort_keys=True, default=str)


def _point_label(point):
    if not isinstance(point, dict):
        return ""
    try:
        return "X {x:.3f} Y {y:.3f} EL {z:.3f}".format(
            x=float(point.get("x")),
            y=float(point.get("y")),
            z=float(point.get("z")),
        )
    except (TypeError, ValueError):
        return ""


def _warning_detail_rows(warnings):
    rows = []
    for index, warning in enumerate(warnings, start=1):
        values = warning.get("values") if isinstance(warning.get("values"), dict) else {}
        rows.append(
            {
                "index": index,
                "severity": warning.get("severity", ""),
                "code": warning.get("code", ""),
                "source": warning.get("source", ""),
                "object_type": warning.get("object_type", ""),
                "run_tag": warning.get("run_tag", ""),
                "segment_index": warning.get("segment_index", ""),
                "message": warning.get("message", ""),
                "point_label": _point_label(warning.get("source_point_m")),
                "node_keys": ", ".join(str(key) for key in warning.get("node_keys", [])[:4]),
                "run_tags": ", ".join(str(tag) for tag in warning.get("run_tags", [])[:4]),
                "values_json": _json_detail(values),
            }
        )
    return rows


@require_http_methods(["GET"])
def layer_warning_detail_view(request, layer_id):
    layer = _layer_for_user(request.user, layer_id)
    if layer is None:
        return _error_response("Raceway layer was not found.", status=404)
    schedule = build_layer_schedule(layer)
    fittings = build_layer_fitting_projection(layer)
    return render(
        request,
        "raceway/warning_detail.html",
        {
            "layer": layer,
            "layer_payload": _layer_payload(layer),
            "schedule": schedule,
            "fittings": fittings,
            "warning_rows": _warning_detail_rows(schedule.get("warnings", [])),
            "schedule_url": reverse("raceway:layer_schedule", args=[layer.pk]),
            "schedule_csv_url": reverse("raceway:layer_schedule_csv", args=[layer.pk]),
            "graph_url": reverse("raceway:layer_graph", args=[layer.pk]),
            "fittings_url": reverse("raceway:layer_fittings", args=[layer.pk]),
        },
    )


@require_http_methods(["GET"])
def layer_fittings_view(request, layer_id):
    layer = _layer_for_user(request.user, layer_id)
    if layer is None:
        return _error_response("Raceway layer was not found.", status=404)
    return JsonResponse({"layer": _layer_payload(layer), "fittings": build_layer_fitting_projection(layer)})


@require_http_methods(["GET"])
def layer_schedule_csv_view(request, layer_id):
    layer = _layer_for_user(request.user, layer_id)
    if layer is None:
        return _error_response("Raceway layer was not found.", status=404)
    schedule = build_layer_schedule(layer)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="raceway-layer-{layer.pk}-schedule.csv"'
    _write_schedule_csv(response, layer, schedule)
    return response


def _write_schedule_csv(response, layer, schedule):
    writer = csv.writer(response)
    writer.writerow(["Raceway Schedule"])
    writer.writerow(["Project", schedule.get("project_id", layer.project_id)])
    writer.writerow(["Layer ID", schedule.get("layer_id", layer.pk)])
    writer.writerow(["Layer Name", schedule.get("layer_name", layer.name)])
    writer.writerow(["Generated At", schedule.get("generated_at", "")])
    writer.writerow(["Graph Warning Total", schedule.get("graph_warnings", {}).get("total", 0)])
    graph_counts = {
        "raceway.graph.near_miss_endpoint": 0,
        "raceway.graph.unconnected_crossing": 0,
        "raceway.graph.zero_length_segment": 0,
        **schedule.get("graph_warnings", {}).get("by_code", {}),
    }
    writer.writerow(["Graph Warning Counts"])
    writer.writerow(["Code", "Count"])
    for code, count in sorted(graph_counts.items()):
        writer.writerow([code, count])
    writer.writerow([])
    writer.writerow(["Warning Summary"])
    warning_summary = schedule.get("warning_summary", {})
    writer.writerow(["Total", warning_summary.get("total", 0)])
    writer.writerow(["Warnings", warning_summary.get("warning", 0)])
    writer.writerow(["Info", warning_summary.get("info", 0)])
    writer.writerow(["Severity Counts"])
    writer.writerow(["Severity", "Count"])
    for severity, count in sorted(warning_summary.get("by_severity", {}).items()):
        writer.writerow([severity, count])
    writer.writerow(["Code Counts"])
    writer.writerow(["Code", "Count"])
    for code, count in sorted(warning_summary.get("by_code", {}).items()):
        writer.writerow([code, count])
    writer.writerow([])
    writer.writerow(["Assumptions"])
    writer.writerow(["Code", "Message"])
    for assumption in schedule.get("assumptions", []):
        writer.writerow([assumption.get("code", ""), assumption.get("message", "")])
    writer.writerow([])
    writer.writerow(["Totals"])
    writer.writerow([
        "Runs",
        "Segments",
        "Length m",
        "Horizontal m",
        "Riser m",
        "Plan Bends",
        "Risers",
        "Tees",
        "Crosses",
        "Branch Accessories",
        "Support Placeholders",
        "Piece Estimate",
        "Offcut Estimate m",
        "Known Weight kg",
        "Has Unknown Weight",
    ])
    totals = schedule.get("totals", {})
    writer.writerow([
        totals.get("run_count", 0),
        totals.get("segment_count", 0),
        _csv_number(totals.get("length_m")),
        _csv_number(totals.get("horizontal_length_m")),
        _csv_number(totals.get("riser_length_m")),
        totals.get("plan_bend_count", 0),
        totals.get("riser_count", 0),
        totals.get("tee_count", 0),
        totals.get("cross_count", 0),
        totals.get("branch_accessory_count", 0),
        totals.get("support_placeholders", 0),
        totals.get("piece_count_estimate", 0),
        _csv_number(totals.get("offcut_m_estimate")),
        _csv_number(totals.get("known_weight_kg")),
        "yes" if totals.get("has_unknown_weight") else "no",
    ])
    writer.writerow([])
    writer.writerow(["Fitting Placeholders"])
    writer.writerow(["Kind", "Category", "Count"])
    fitting_counts = schedule.get("fitting_placeholders", {}).get("counts", {})
    writer.writerow(["plan_bend", "total", fitting_counts.get("plan_bend_total", 0)])
    writer.writerow(["plan_bend", "non_standard_angle", fitting_counts.get("non_standard_plan_bend_total", 0)])
    for category, count in sorted(fitting_counts.get("plan_bends", {}).items()):
        writer.writerow(["plan_bend", category, count])
    writer.writerow(["riser", "total", fitting_counts.get("riser_total", 0)])
    for category, count in sorted(fitting_counts.get("risers", {}).items()):
        writer.writerow(["riser", category, count])
    writer.writerow(["branch_accessory", "total", fitting_counts.get("branch_accessory_total", 0)])
    writer.writerow(["tee", "projection_only_total", fitting_counts.get("tee_total", 0)])
    writer.writerow(["cross", "projection_only_total", fitting_counts.get("cross_total", 0)])
    writer.writerow([
        "branch_accessory",
        "projection_only_unresolved",
        fitting_counts.get("branch_accessory_unresolved_total", 0),
    ])
    for category, count in sorted(fitting_counts.get("branch_accessories", {}).items()):
        writer.writerow(["branch_accessory", category, count])
    writer.writerow([])
    writer.writerow(["Branch Accessory Placeholders"])
    writer.writerow([
        "Kind",
        "Category",
        "Graph Node",
        "Degree",
        "Port Count",
        "Run Tags",
        "Sizing Status",
        "Branch Intent",
        "Intent Persistence",
        "Needs Catalogue Validation",
        "Needs Face Alignment",
        "Message",
    ])
    for accessory in schedule.get("fitting_placeholders", {}).get("branch_accessories", []):
        writer.writerow([
            accessory.get("kind", ""),
            accessory.get("category", ""),
            accessory.get("graph_node_key", ""),
            accessory.get("degree", 0),
            accessory.get("port_count", 0),
            "; ".join(accessory.get("run_tags", [])),
            accessory.get("sizing_status", ""),
            accessory.get("branch_intent_status", ""),
            accessory.get("branch_intent_persistence", ""),
            "yes" if accessory.get("requires_catalogue_validation") else "no",
            "yes" if accessory.get("requires_face_alignment") else "no",
            accessory.get("message", ""),
        ])
    writer.writerow([])
    writer.writerow(["Validation Warnings"])
    writer.writerow(["Severity", "Code", "Source", "Object", "Run Tag", "Segment", "Message"])
    for warning in schedule.get("warnings", []):
        writer.writerow([
            warning.get("severity", ""),
            warning.get("code", ""),
            warning.get("source", ""),
            warning.get("object_type", ""),
            warning.get("run_tag", ""),
            warning.get("segment_index", ""),
            warning.get("message", ""),
        ])
    writer.writerow([])
    writer.writerow(["Grouped Quantities"])
    writer.writerow([
        "Family",
        "Size",
        "Service",
        "Runs",
        "Segments",
        "Length m",
        "Horizontal m",
        "Riser m",
        "Plan Bends",
        "Risers",
        "Support Placeholders",
        "Standard Length mm",
        "Piece Estimate",
        "Offcut Estimate m",
        "Known Weight kg",
        "Has Unknown Weight",
    ])
    for group in schedule.get("groups", []):
        writer.writerow([
            group.get("family_code", ""),
            group.get("size_label", ""),
            group.get("service_class", ""),
            group.get("run_count", 0),
            group.get("segment_count", 0),
            _csv_number(group.get("length_m")),
            _csv_number(group.get("horizontal_length_m")),
            _csv_number(group.get("riser_length_m")),
            group.get("plan_bend_count", 0),
            group.get("riser_count", 0),
            group.get("support_placeholders", 0),
            group.get("standard_length_mm", ""),
            group.get("piece_count_estimate", 0),
            _csv_number(group.get("offcut_m_estimate")),
            _csv_number(group.get("known_weight_kg")),
            "yes" if group.get("has_unknown_weight") else "no",
        ])
    writer.writerow([])
    writer.writerow(["Runs"])
    writer.writerow([
        "Run Tag",
        "Run Key",
        "Family",
        "Size",
        "Service",
        "Nodes",
        "Segments",
        "Length m",
        "Plan Bends",
        "Risers",
        "Support Placeholders",
        "Piece Estimate",
        "Offcut Estimate m",
    ])
    for run in schedule.get("runs", []):
        writer.writerow([
            run.get("run_tag", ""),
            run.get("run_key", ""),
            run.get("family_code", ""),
            run.get("size_label", ""),
            run.get("service_class", ""),
            run.get("node_count", 0),
            run.get("segment_count", 0),
            _csv_number(run.get("length_m")),
            run.get("plan_bend_count", 0),
            run.get("riser_count", 0),
            run.get("support_placeholders", 0),
            run.get("piece_count_estimate", 0),
            _csv_number(run.get("offcut_m_estimate")),
        ])
    writer.writerow([])
    writer.writerow(["Segments"])
    writer.writerow([
        "Run Tag",
        "Segment",
        "Start Node Key",
        "End Node Key",
        "Length m",
        "Horizontal m",
        "dZ m",
        "Is Riser",
    ])
    for segment in schedule.get("segments", []):
        writer.writerow([
            segment.get("run_tag", ""),
            segment.get("segment_index", ""),
            segment.get("start_node_key", ""),
            segment.get("end_node_key", ""),
            _csv_number(segment.get("length_m")),
            _csv_number(segment.get("horizontal_length_m")),
            _csv_number(segment.get("dz_m")),
            "yes" if segment.get("is_riser") else "no",
        ])


def _csv_number(value):
    if value is None:
        return ""
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return value


@require_http_methods(["GET", "POST"])
def run_collection_view(request, layer_id):
    layer = _layer_for_user(request.user, layer_id)
    if layer is None:
        return _error_response("Raceway layer was not found.", status=404)
    if request.method == "GET":
        include_nodes = _truthy_query(request.GET.get("include_nodes"))
        runs = RacewayRun.objects.select_related("layer", "family", "size").filter(layer=layer).order_by("tag", "pk")
        if include_nodes:
            runs = runs.prefetch_related("nodes")
        return JsonResponse({"runs": [_run_payload(run, include_nodes=include_nodes) for run in runs]})
    try:
        payload = _json_body(request)
        run = RacewayRun(layer=layer)
        _apply_run_payload(run, payload, request.user)
        run.save()
    except ValidationError as exc:
        return _error_response("Invalid raceway run payload.", errors=_validation_payload(exc))
    return JsonResponse({"run": _run_payload(run)}, status=201)


@require_http_methods(["GET", "PATCH", "DELETE"])
def run_detail_view(request, run_id):
    run = _run_for_user(request.user, run_id)
    if run is None:
        return _error_response("Raceway run was not found.", status=404)
    if request.method == "GET":
        return JsonResponse({"run": _run_payload(run, include_nodes=True)})
    if request.method == "DELETE":
        run.delete()
        return JsonResponse({"status": "deleted", "run_id": run_id})
    try:
        payload = _json_body(request)
        _apply_run_payload(run, payload, request.user)
        run.save()
        _prune_stale_segment_orientation(run)
        _prune_stale_segment_face_offset(run)
    except ValidationError as exc:
        return _error_response("Invalid raceway run payload.", errors=_validation_payload(exc))
    return JsonResponse({"run": _run_payload(run)})


def _node_from_payload(run, raw_node, index, existing_node_keys):
    if not isinstance(raw_node, dict):
        raise ValidationError({"nodes": f"Node {index + 1} must be an object."})
    sequence = _optional_non_negative_int(raw_node.get("sequence", index), "sequence")
    if sequence is None:
        sequence = index
    preserved_key = _node_key_from_payload(raw_node, index, existing_node_keys)
    node = RacewayNode(
        run=run,
        sequence=sequence,
        node_kind=raw_node.get("node_kind") or "intermediate",
        source_x_m=raw_node.get("source_x_m"),
        source_y_m=raw_node.get("source_y_m"),
        source_z_m=raw_node.get("source_z_m"),
        anchor=validate_overlay_anchor(
            _metadata_value(raw_node, "anchor"),
            source_model_id=run.source_model_id,
            owner_module="raceway",
        ),
        metadata=_metadata_value(raw_node, "metadata"),
    )
    if preserved_key is not None:
        node.key = preserved_key
    node.full_clean(exclude=["run", "key"])
    return node


@require_http_methods(["GET", "POST", "PUT"])
def run_nodes_view(request, run_id):
    run = _run_for_user(request.user, run_id)
    if run is None:
        return _error_response("Raceway run was not found.", status=404)
    if request.method == "GET":
        return JsonResponse({"nodes": [_node_payload(node) for node in run.nodes.order_by("sequence", "pk")]})
    try:
        payload = _json_body(request)
        raw_nodes = payload.get("nodes")
        if not isinstance(raw_nodes, list):
            raise ValidationError({"nodes": "Nodes must be provided as a list."})
        if len(raw_nodes) < 2:
            raise ValidationError({"nodes": "At least two ordered nodes are required to save a raceway run."})
        existing_node_keys = {str(key): key for key in run.nodes.values_list("key", flat=True)}
        nodes = [_node_from_payload(run, raw_node, index, existing_node_keys) for index, raw_node in enumerate(raw_nodes)]
        sequences = [node.sequence for node in nodes]
        if len(sequences) != len(set(sequences)):
            raise ValidationError({"nodes": "Node sequences must be unique within a run."})
        node_keys = [node.key for node in nodes]
        if len(node_keys) != len(set(node_keys)):
            raise ValidationError({"nodes": "Node keys must be unique within a run payload."})
        with transaction.atomic():
            run.nodes.all().delete()
            RacewayNode.objects.bulk_create(nodes)
        _prune_stale_segment_orientation(run)
        _prune_stale_segment_face_offset(run)
    except ValidationError as exc:
        return _error_response("Invalid raceway node payload.", errors=_validation_payload(exc))
    return JsonResponse({"nodes": [_node_payload(node) for node in run.nodes.order_by("sequence", "pk")]})
