import math
from collections import defaultdict

from .graph import (
    MIN_SEGMENT_LENGTH_M,
    PLAN_BEND_COSINE_LIMIT,
    build_layer_graph,
)
from .models import RacewayLayer, RacewayRun


SHORT_SEGMENT_WARNING_M = 0.05
EXCESSIVE_BEND_COUNT_WARNING = 8
SUPPORT_SPAN_PLACEHOLDER_M = 3.0
BEND_MIN_ANGLE_DEG = 5.0


def build_layer_warnings(
    layer,
    *,
    graph_payload=None,
    short_segment_m=SHORT_SEGMENT_WARNING_M,
    excessive_bend_count=EXCESSIVE_BEND_COUNT_WARNING,
    support_span_m=SUPPORT_SPAN_PLACEHOLDER_M,
):
    layer_obj = layer if isinstance(layer, RacewayLayer) else RacewayLayer.objects.get(pk=int(layer))
    if graph_payload is None:
        graph_payload = build_layer_graph(layer_obj).to_payload()

    warnings = [
        _normalize_graph_warning(warning, layer_obj.pk)
        for warning in graph_payload.get("warnings", [])
    ]
    runs = (
        RacewayRun.objects
        .select_related("layer", "family", "size")
        .prefetch_related("nodes")
        .filter(layer=layer_obj)
        .order_by("tag", "pk")
    )

    if layer_obj.source_model_id is None or layer_obj.render_package_id is None:
        warnings.append(
            _warning(
                "raceway.warning.unknown_coordinate_context",
                "warning",
                "Raceway layer is missing source model or render package context.",
                source="route",
                object_type="layer",
                layer_id=layer_obj.pk,
                values={
                    "source_model_id": layer_obj.source_model_id,
                    "render_package_id": layer_obj.render_package_id,
                },
            )
        )

    has_measurable_route = False
    for run in runs:
        nodes = sorted(run.nodes.all(), key=lambda node: (node.sequence, node.pk))
        warnings.extend(_run_catalog_warnings(run))
        warnings.extend(_run_context_warnings(run, layer_obj))
        if len(nodes) < 2:
            warnings.append(
                _warning(
                    "raceway.warning.too_few_nodes",
                    "warning",
                    "Raceway run has fewer than two nodes and cannot form a schedulable route.",
                    source="route",
                    object_type="run",
                    layer_id=layer_obj.pk,
                    run=run,
                    values={"node_count": len(nodes)},
                )
            )
            continue

        bend_count = _plan_bend_count(nodes)
        if bend_count > excessive_bend_count:
            warnings.append(
                _warning(
                    "raceway.warning.excessive_bends",
                    "warning",
                    "Raceway run has a high number of plan bends; review constructability and pulling path.",
                    source="route",
                    object_type="run",
                    layer_id=layer_obj.pk,
                    run=run,
                    values={
                        "plan_bend_count": bend_count,
                        "threshold": excessive_bend_count,
                    },
                )
            )

        for index in range(1, len(nodes)):
            start_node = nodes[index - 1]
            end_node = nodes[index]
            length_m = _distance(_point_from_node(start_node), _point_from_node(end_node))
            has_measurable_route = has_measurable_route or length_m > MIN_SEGMENT_LENGTH_M
            if MIN_SEGMENT_LENGTH_M < length_m < short_segment_m:
                warnings.append(
                    _warning(
                        "raceway.warning.short_segment",
                        "warning",
                        "Raceway segment is very short; review whether adjacent nodes should be merged.",
                        source="route",
                        object_type="segment",
                        layer_id=layer_obj.pk,
                        run=run,
                        node_keys=[str(start_node.key), str(end_node.key)],
                        segment_index=index,
                        source_point_m=_point_from_node(end_node),
                        values={
                            "length_m": length_m,
                            "threshold_m": short_segment_m,
                        },
                    )
                )

    if has_measurable_route:
        warnings.append(
            _warning(
                "raceway.warning.support_span_placeholder_basis",
                "info",
                "Support quantities are placeholder counts only; no span-table or structural support validation has been applied.",
                source="schedule",
                object_type="layer",
                layer_id=layer_obj.pk,
                values={"support_span_m": support_span_m},
            )
        )

    return sorted(
        warnings,
        key=lambda warning: (
            warning.get("severity", ""),
            warning.get("code", ""),
            warning.get("run_tag", ""),
            warning.get("segment_index") or 0,
            warning.get("message", ""),
        ),
    )


def summarize_warnings(warnings):
    by_code = defaultdict(int)
    by_severity = defaultdict(int)
    for warning in warnings:
        by_code[warning.get("code") or "unknown"] += 1
        by_severity[warning.get("severity") or "warning"] += 1
    return {
        "total": len(warnings),
        "by_code": dict(sorted(by_code.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "warning": by_severity.get("warning", 0),
        "info": by_severity.get("info", 0),
        "error": by_severity.get("error", 0),
    }


def _normalize_graph_warning(warning, layer_id):
    normalized = dict(warning)
    normalized.setdefault("severity", "warning")
    normalized.setdefault("source", "graph")
    normalized.setdefault("object_type", _graph_object_type(warning))
    normalized.setdefault("layer_id", layer_id)
    normalized.setdefault("values", _graph_values(warning))
    return normalized


def _graph_object_type(warning):
    code = warning.get("code")
    if code == "raceway.graph.zero_length_segment":
        return "segment"
    if code == "raceway.graph.near_miss_endpoint":
        return "endpoint"
    if code == "raceway.graph.unconnected_crossing":
        return "graph"
    return "graph"


def _graph_values(warning):
    return {
        key: warning[key]
        for key in ("distance_m", "tolerance_m", "near_miss_radius_m")
        if key in warning
    }


def _run_catalog_warnings(run):
    warnings = []
    if not run.family.is_active:
        warnings.append(
            _warning(
                "raceway.warning.inactive_catalog_reference",
                "warning",
                "Raceway run references an inactive family.",
                source="route",
                object_type="run",
                layer_id=run.layer_id,
                run=run,
                values={"family_id": run.family_id, "family_code": run.family.code},
            )
        )
    if not run.size.is_active:
        warnings.append(
            _warning(
                "raceway.warning.inactive_catalog_reference",
                "warning",
                "Raceway run references an inactive size.",
                source="route",
                object_type="run",
                layer_id=run.layer_id,
                run=run,
                values={"size_id": run.size_id, "size_label": f"{run.size.width_mm} x {run.size.depth_mm} mm"},
            )
        )
    service_values = {choice[0] for choice in RacewayRun.SERVICE_CLASS_CHOICES}
    if run.service_class not in service_values:
        warnings.append(
            _warning(
                "raceway.warning.missing_service_class",
                "warning",
                "Raceway run has an unknown service class.",
                source="route",
                object_type="run",
                layer_id=run.layer_id,
                run=run,
                values={"service_class": run.service_class},
            )
        )
    return warnings


def _run_context_warnings(run, layer):
    has_layer_context = layer.source_model_id is not None and layer.render_package_id is not None
    has_run_context = run.source_model_id is not None and run.render_package_id is not None
    if has_layer_context or has_run_context:
        return []
    return [
        _warning(
            "raceway.warning.unknown_coordinate_context",
            "warning",
            "Raceway run is missing source model or render package context.",
            source="route",
            object_type="run",
            layer_id=layer.pk,
            run=run,
            values={
                "source_model_id": run.source_model_id,
                "render_package_id": run.render_package_id,
            },
        )
    ]


def _warning(
    code,
    severity,
    message,
    *,
    source,
    object_type,
    layer_id,
    run=None,
    node_keys=None,
    segment_index=None,
    source_point_m=None,
    values=None,
):
    payload = {
        "code": code,
        "severity": severity,
        "message": message,
        "source": source,
        "object_type": object_type,
        "layer_id": layer_id,
    }
    if run is not None:
        payload.update(
            {
                "run_id": run.pk,
                "run_key": str(run.key),
                "run_tag": run.tag or str(run.key),
            }
        )
    if node_keys:
        payload["node_keys"] = list(node_keys)
    if segment_index is not None:
        payload["segment_index"] = segment_index
    if source_point_m:
        payload["source_point_m"] = source_point_m
    if values is not None:
        payload["values"] = values
    return payload


def _plan_bend_count(nodes):
    count = 0
    for index in range(1, len(nodes) - 1):
        angle_deg = _plan_bend_angle_deg(nodes[index - 1], nodes[index], nodes[index + 1])
        if angle_deg is not None and angle_deg >= BEND_MIN_ANGLE_DEG:
            count += 1
    return count


def _plan_bend_angle_deg(previous_node, node, next_node):
    in_x = float(node.source_x_m) - float(previous_node.source_x_m)
    in_y = float(node.source_y_m) - float(previous_node.source_y_m)
    out_x = float(next_node.source_x_m) - float(node.source_x_m)
    out_y = float(next_node.source_y_m) - float(node.source_y_m)
    in_plan = math.hypot(in_x, in_y)
    out_plan = math.hypot(out_x, out_y)
    if in_plan < MIN_SEGMENT_LENGTH_M or out_plan < MIN_SEGMENT_LENGTH_M:
        return None
    cosine = ((in_x * out_x) + (in_y * out_y)) / (in_plan * out_plan)
    cosine = max(-1.0, min(1.0, cosine))
    if cosine >= PLAN_BEND_COSINE_LIMIT:
        return None
    return math.degrees(math.acos(cosine))


def _distance(start, end):
    dx = end["x"] - start["x"]
    dy = end["y"] - start["y"]
    dz = end["z"] - start["z"]
    return math.sqrt((dx * dx) + (dy * dy) + (dz * dz))


def _point_from_node(node):
    return {
        "x": float(node.source_x_m),
        "y": float(node.source_y_m),
        "z": float(node.source_z_m),
    }
