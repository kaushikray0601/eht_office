import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from plant3d.access import render_packages_for_user, source_models_for_user

from .access import require_project_access
from .models import RacewayFamily, RacewayLayer, RacewayNode, RacewayRun, RacewaySize


def raceway_home_view(request):
    return JsonResponse(
        {
            "app": "raceway",
            "status": "ok",
            "boundary": "peer-consumer",
            "platform": "plant3d",
        }
    )


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
        run.metadata = _metadata_value(payload, "metadata")
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


@require_http_methods(["GET", "POST"])
def run_collection_view(request, layer_id):
    layer = _layer_for_user(request.user, layer_id)
    if layer is None:
        return _error_response("Raceway layer was not found.", status=404)
    if request.method == "GET":
        runs = RacewayRun.objects.select_related("layer", "family", "size").filter(layer=layer).order_by("tag", "pk")
        return JsonResponse({"runs": [_run_payload(run) for run in runs]})
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
    except ValidationError as exc:
        return _error_response("Invalid raceway run payload.", errors=_validation_payload(exc))
    return JsonResponse({"run": _run_payload(run)})


def _node_from_payload(run, raw_node, index):
    if not isinstance(raw_node, dict):
        raise ValidationError({"nodes": f"Node {index + 1} must be an object."})
    sequence = _optional_non_negative_int(raw_node.get("sequence", index), "sequence")
    if sequence is None:
        sequence = index
    node = RacewayNode(
        run=run,
        sequence=sequence,
        node_kind=raw_node.get("node_kind") or "intermediate",
        source_x_m=raw_node.get("source_x_m"),
        source_y_m=raw_node.get("source_y_m"),
        source_z_m=raw_node.get("source_z_m"),
        anchor=_metadata_value(raw_node, "anchor"),
        metadata=_metadata_value(raw_node, "metadata"),
    )
    node.full_clean(exclude=["run"])
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
        nodes = [_node_from_payload(run, raw_node, index) for index, raw_node in enumerate(raw_nodes)]
        sequences = [node.sequence for node in nodes]
        if len(sequences) != len(set(sequences)):
            raise ValidationError({"nodes": "Node sequences must be unique within a run."})
        with transaction.atomic():
            run.nodes.all().delete()
            RacewayNode.objects.bulk_create(nodes)
    except ValidationError as exc:
        return _error_response("Invalid raceway node payload.", errors=_validation_payload(exc))
    return JsonResponse({"nodes": [_node_payload(node) for node in run.nodes.order_by("sequence", "pk")]})
