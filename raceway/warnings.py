import math
from collections import defaultdict

from plant3d.overlay import model_object_bounds_for_source

from .geometry import (
    MIN_SEGMENT_LENGTH_M,
    bounds_center,
    bounds_from_points,
    bounds_gap,
    bounds_intersect,
    distance,
    normalize_bounds,
    plan_bend_angle_deg,
    point_from_node,
)
from .graph import (
    build_layer_graph,
)
from .models import RacewayLayer, RacewayRun


SHORT_SEGMENT_WARNING_M = 0.05
EXCESSIVE_BEND_COUNT_WARNING = 8
SUPPORT_SPAN_PLACEHOLDER_M = 3.0
BEND_MIN_ANGLE_DEG = 5.0
MODEL_CLASH_CLEARANCE_M = 0.10
MODEL_CLASH_WARNING_LIMIT = 25
MODEL_OBJECT_SCAN_LIMIT = 2000
ORIENTATION_QUARTER_TURNS = {
    "open_up": 0,
    "roll_right": 1,
    "open_down": 2,
    "roll_left": 3,
}
SEVERITY_ORDER = {
    "error": 0,
    "warning": 1,
    "info": 2,
}


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
    runs = list(
        RacewayRun.objects
        .select_related("layer", "family", "size")
        .prefetch_related("nodes")
        .filter(layer=layer_obj)
        .order_by("tag", "pk")
    )
    runs_by_id = {run.pk: run for run in runs}

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

    model_objects, model_scan_limited = _model_objects_for_layer(layer_obj, runs)
    if model_scan_limited:
        warnings.append(
            _warning(
                "raceway.warning.model_clash_scan_limited",
                "warning",
                "Only part of the Plant3D object-bounds index was scanned; rough clash warnings may be incomplete.",
                source="model_envelope",
                object_type="layer",
                layer_id=layer_obj.pk,
                values={"scan_limit": MODEL_OBJECT_SCAN_LIMIT},
            )
        )
    warnings.extend(_service_mismatch_warnings(graph_payload, runs_by_id, layer_obj.pk))
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
            length_m = distance(point_from_node(start_node), point_from_node(end_node))
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
                        source_point_m=point_from_node(end_node),
                        values={
                            "length_m": length_m,
                            "threshold_m": short_segment_m,
                        },
                    )
                )
        if model_objects:
            remaining = max(MODEL_CLASH_WARNING_LIMIT - _model_warning_count(warnings), 0)
            if remaining > 0:
                warnings.extend(
                    _model_clash_warnings(
                        run,
                        nodes,
                        model_objects,
                        layer_id=layer_obj.pk,
                        warning_limit=remaining,
                        clearance_m=MODEL_CLASH_CLEARANCE_M,
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
            SEVERITY_ORDER.get(warning.get("severity"), 9),
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


def _service_mismatch_warnings(graph_payload, runs_by_id, layer_id):
    warnings = []
    for graph_node in graph_payload.get("nodes", []):
        members = _graph_node_run_members(graph_node, runs_by_id)
        services = sorted({member["service_class"] for member in members if member["service_class"]})
        if len(services) < 2:
            continue
        representative = members[0]
        representative_run = runs_by_id.get(representative["run_id"])
        warning = _warning(
            "raceway.warning.service_mismatch_at_junction",
            "warning",
            "Connected raceway junction mixes service classes; review segregation or modelling intent.",
            source="graph",
            object_type="junction",
            layer_id=layer_id,
            run=representative_run,
            node_keys=[member["node_key"] for member in members],
            source_point_m=graph_node.get("source_point_m"),
            values={
                "graph_node_key": graph_node.get("key", ""),
                "graph_node_kind": graph_node.get("derived_kind", ""),
                "service_classes": services,
                "members": members,
            },
        )
        warning["run_ids"] = sorted({member["run_id"] for member in members})
        warning["run_keys"] = sorted({member["run_key"] for member in members})
        warning["run_tags"] = sorted({member["run_tag"] for member in members})
        warnings.append(warning)
    return warnings


def _graph_node_run_members(graph_node, runs_by_id):
    members = []
    for member in graph_node.get("members", []):
        run = runs_by_id.get(member.get("run_id"))
        if run is None:
            continue
        members.append(
            {
                "run_id": run.pk,
                "run_key": str(run.key),
                "run_tag": run.tag or str(run.key),
                "node_key": member.get("node_key", ""),
                "sequence": member.get("sequence"),
                "family_code": run.family.code,
                "size_label": f"{run.size.width_mm} x {run.size.depth_mm} mm",
                "service_class": run.service_class,
            }
        )
    return sorted(members, key=lambda item: (item["run_tag"], item["sequence"], item["node_key"]))


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
        angle_deg = plan_bend_angle_deg(nodes[index - 1], nodes[index], nodes[index + 1])
        if angle_deg is not None and angle_deg >= BEND_MIN_ANGLE_DEG:
            count += 1
    return count


def _model_objects_for_layer(layer, runs):
    if layer.source_model_id is None:
        return [], False
    payload = model_object_bounds_for_source(
        layer.source_model_id,
        render_package_id=layer.render_package_id,
        bounds_filter=_layer_envelope_bounds(runs),
        limit=MODEL_OBJECT_SCAN_LIMIT,
    )
    return payload["objects"], bool(payload["limited"])


def _layer_envelope_bounds(runs):
    layer_bounds = None
    for run in runs:
        nodes = sorted(run.nodes.all(), key=lambda node: (node.sequence, node.pk))
        for index in range(1, len(nodes)):
            segment_bounds = _segment_envelope_bounds(
                run,
                nodes[index - 1],
                nodes[index],
                clearance_m=MODEL_CLASH_CLEARANCE_M,
            )
            layer_bounds = _bounds_union(layer_bounds, segment_bounds)
    return layer_bounds


def _bounds_union(left, right):
    left_bounds = normalize_bounds(left)
    right_bounds = normalize_bounds(right)
    if left_bounds is None:
        return right_bounds
    if right_bounds is None:
        return left_bounds
    return {
        "min_x": min(left_bounds["min_x"], right_bounds["min_x"]),
        "max_x": max(left_bounds["max_x"], right_bounds["max_x"]),
        "min_y": min(left_bounds["min_y"], right_bounds["min_y"]),
        "max_y": max(left_bounds["max_y"], right_bounds["max_y"]),
        "min_z": min(left_bounds["min_z"], right_bounds["min_z"]),
        "max_z": max(left_bounds["max_z"], right_bounds["max_z"]),
    }


def _model_clash_warnings(run, nodes, model_objects, *, layer_id, warning_limit, clearance_m):
    warnings = []
    for index in range(1, len(nodes)):
        start_node = nodes[index - 1]
        end_node = nodes[index]
        raceway_bounds = _segment_envelope_bounds(run, start_node, end_node, clearance_m=0.0)
        if raceway_bounds is None:
            continue
        clearance_bounds = _segment_envelope_bounds(run, start_node, end_node, clearance_m=clearance_m)
        if clearance_bounds is None:
            continue
        segment_candidates = []
        for model_object in model_objects:
            object_bounds = model_object["bounds"]
            if bounds_intersect(raceway_bounds, object_bounds):
                segment_candidates.append((0, 0.0, model_object, object_bounds))
                continue
            if bounds_intersect(clearance_bounds, object_bounds):
                gap_m = bounds_gap(raceway_bounds, object_bounds)
                if gap_m is not None and gap_m <= clearance_m:
                    segment_candidates.append((1, gap_m, model_object, object_bounds))
        for category, gap_m, model_object, object_bounds in sorted(
            segment_candidates,
            key=lambda item: (item[0], round(item[1], 6), item[2]["stable_id"]),
        ):
            warnings.append(
                _model_clash_warning(
                    run,
                    start_node,
                    end_node,
                    segment_index=index,
                    layer_id=layer_id,
                    model_object=model_object,
                    object_bounds=object_bounds,
                    raceway_bounds=raceway_bounds,
                    gap_m=gap_m,
                    is_clash=category == 0,
                    clearance_m=clearance_m,
                )
            )
            if len(warnings) >= warning_limit:
                return warnings
    return warnings


def _segment_envelope_bounds(run, start_node, end_node, *, clearance_m):
    start = point_from_node(start_node)
    end = point_from_node(end_node)
    if distance(start, end) < MIN_SEGMENT_LENGTH_M:
        return None
    width_m = max(float(run.size.width_mm or 0) / 1000.0, 0.0)
    depth_m = max(float(run.size.depth_mm or 0) / 1000.0, 0.0)
    return bounds_from_points(
        _segment_proxy_corner_points(
            start,
            end,
            width_m=width_m,
            depth_m=depth_m,
            quarter_turns=_run_orientation_quarter_turns(run),
        ),
        margin_m=max(float(clearance_m or 0.0), 0.0),
    )


def _run_orientation_quarter_turns(run):
    metadata = run.metadata if isinstance(run.metadata, dict) else {}
    orientation = metadata.get("orientation")
    if not isinstance(orientation, dict):
        return 0
    try:
        return int(orientation.get("quarter_turns")) % 4
    except (TypeError, ValueError):
        return ORIENTATION_QUARTER_TURNS.get(str(orientation.get("preset") or ""), 0)


def _segment_proxy_corner_points(start, end, *, width_m, depth_m, quarter_turns):
    basis = _oriented_segment_basis(start, end, quarter_turns=quarter_turns)
    half_width = width_m / 2.0
    points = []
    for source_point in (start, end):
        for lateral_offset_m in (half_width, -half_width):
            bottom = _source_frame_offset_point(source_point, basis, lateral_offset_m, 0.0)
            top = _source_frame_offset_point(source_point, basis, lateral_offset_m, depth_m)
            points.extend([bottom, top])
    return points


def _oriented_segment_basis(start, end, *, quarter_turns):
    basis = _segment_plan_basis(start, end)
    turns = int(quarter_turns or 0) % 4
    if not turns:
        return basis
    angle = turns * math.pi / 2.0
    cos_value = round(math.cos(angle))
    sin_value = round(math.sin(angle))
    return {
        **basis,
        "nx": (basis["nx"] * cos_value) + (basis["dx"] * sin_value),
        "ny": (basis["ny"] * cos_value) + (basis["dy"] * sin_value),
        "nz": (basis["nz"] * cos_value) + (basis["dz"] * sin_value),
        "dx": (basis["dx"] * cos_value) - (basis["nx"] * sin_value),
        "dy": (basis["dy"] * cos_value) - (basis["ny"] * sin_value),
        "dz": (basis["dz"] * cos_value) - (basis["nz"] * sin_value),
    }


def _segment_plan_basis(start, end):
    delta_x = end["x"] - start["x"]
    delta_y = end["y"] - start["y"]
    delta_z = end["z"] - start["z"]
    length = math.sqrt((delta_x * delta_x) + (delta_y * delta_y) + (delta_z * delta_z))
    if length < MIN_SEGMENT_LENGTH_M:
        return {
            "tx": 1.0,
            "ty": 0.0,
            "tz": 0.0,
            "nx": 0.0,
            "ny": 1.0,
            "nz": 0.0,
            "dx": 0.0,
            "dy": 0.0,
            "dz": 1.0,
        }

    plan_length = math.hypot(delta_x, delta_y)
    normal_x = 0.0
    normal_y = 1.0
    if plan_length >= MIN_SEGMENT_LENGTH_M:
        normal_x = -delta_y / plan_length
        normal_y = delta_x / plan_length

    tangent_x = delta_x / length
    tangent_y = delta_y / length
    tangent_z = delta_z / length
    depth_x = -tangent_z * normal_y
    depth_y = tangent_z * normal_x
    depth_z = (tangent_x * normal_y) - (tangent_y * normal_x)
    depth_length = math.sqrt((depth_x * depth_x) + (depth_y * depth_y) + (depth_z * depth_z))
    if depth_length < MIN_SEGMENT_LENGTH_M:
        depth_x = 0.0
        depth_y = 0.0
        depth_z = 1.0
        depth_length = 1.0
    depth_x /= depth_length
    depth_y /= depth_length
    depth_z /= depth_length
    if depth_z < -MIN_SEGMENT_LENGTH_M:
        depth_x *= -1.0
        depth_y *= -1.0
        depth_z *= -1.0

    return {
        "tx": tangent_x,
        "ty": tangent_y,
        "tz": tangent_z,
        "nx": normal_x,
        "ny": normal_y,
        "nz": 0.0,
        "dx": depth_x,
        "dy": depth_y,
        "dz": depth_z,
    }


def _source_frame_offset_point(point, basis, lateral_offset_m=0.0, depth_offset_m=0.0):
    return {
        "x": point["x"] + (basis["nx"] * lateral_offset_m) + (basis["dx"] * depth_offset_m),
        "y": point["y"] + (basis["ny"] * lateral_offset_m) + (basis["dy"] * depth_offset_m),
        "z": point["z"] + (basis["nz"] * lateral_offset_m) + (basis["dz"] * depth_offset_m),
    }


def _model_clash_warning(
    run,
    start_node,
    end_node,
    *,
    segment_index,
    layer_id,
    model_object,
    object_bounds,
    raceway_bounds,
    gap_m,
    is_clash,
    clearance_m,
):
    code = "raceway.warning.model_clash_aabb" if is_clash else "raceway.warning.model_clearance_aabb"
    message = (
        "Raceway segment envelope overlaps a Plant3D object bounds box; review route or elevation."
        if is_clash
        else "Raceway segment envelope is within the rough clearance band of a Plant3D object bounds box."
    )
    return _warning(
        code,
        "warning",
        message,
        source="model_envelope",
        object_type="segment",
        layer_id=layer_id,
        run=run,
        node_keys=[str(start_node.key), str(end_node.key)],
        segment_index=segment_index,
        source_point_m=bounds_center(raceway_bounds),
        values={
            "method": "aabb",
            "clearance_m": clearance_m,
            "gap_m": gap_m,
            "object_stable_id": model_object["stable_id"],
            "object_source_object_id": model_object["source_object_id"],
            "object_type": model_object["object_type"],
            "object_label": (
                model_object["tag"]
                or model_object["line_id"]
                or model_object["source_object_id"]
                or model_object["stable_id"]
            ),
            "object_bounds": object_bounds,
            "raceway_bounds": raceway_bounds,
        },
    )


def _model_warning_count(warnings):
    return sum(
        1
        for warning in warnings
        if warning.get("code") in {"raceway.warning.model_clash_aabb", "raceway.warning.model_clearance_aabb"}
    )
