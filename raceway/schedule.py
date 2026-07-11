import math
from collections import defaultdict

from django.utils import timezone

from .graph import (
    MIN_SEGMENT_LENGTH_M,
    PLAN_BEND_COSINE_LIMIT,
    RISER_ELEVATION_DELTA_M,
    build_layer_graph,
)
from .models import RacewayLayer, RacewayRun


PLACEHOLDER_SUPPORT_SPAN_M = 3.0
BEND_MIN_ANGLE_DEG = 5.0


def build_layer_schedule(layer, *, support_span_m=PLACEHOLDER_SUPPORT_SPAN_M):
    layer_obj = layer if isinstance(layer, RacewayLayer) else RacewayLayer.objects.get(pk=int(layer))
    runs = (
        RacewayRun.objects
        .select_related("layer", "family", "size")
        .prefetch_related("nodes")
        .filter(layer=layer_obj)
        .order_by("tag", "pk")
    )
    graph = build_layer_graph(layer_obj).to_payload()
    return build_schedule_for_runs(
        runs,
        layer=layer_obj,
        graph_warnings=graph.get("warnings", []),
        support_span_m=support_span_m,
    )


def build_schedule_for_runs(runs, *, layer=None, graph_warnings=None, support_span_m=PLACEHOLDER_SUPPORT_SPAN_M):
    run_payloads = []
    segment_payloads = []
    plan_bends = []
    risers = []
    groups = {}

    for run in runs:
        nodes = sorted(run.nodes.all(), key=lambda node: (node.sequence, node.pk))
        segments = [_segment_payload(run, nodes[index - 1], nodes[index], index) for index in range(1, len(nodes))]
        bends = [
            bend
            for index in range(1, len(nodes) - 1)
            if (bend := _plan_bend_payload(run, nodes[index - 1], nodes[index], nodes[index + 1])) is not None
        ]
        run_risers = [_riser_payload(segment) for segment in segments if segment["is_riser"]]
        length_m = sum(segment["length_m"] for segment in segments)
        support_placeholders = _support_placeholder_count(length_m, support_span_m)
        run_payload = _run_summary_payload(
            run,
            nodes,
            segments,
            bends,
            run_risers,
            length_m,
            support_span_m,
            support_placeholders,
        )
        run_payloads.append(run_payload)
        segment_payloads.extend(segments)
        plan_bends.extend(bends)
        risers.extend(run_risers)
        _add_to_group(groups, run, run_payload)

    group_payloads = sorted(groups.values(), key=lambda item: item["group_key"])
    return {
        **_generation_envelope(layer),
        "assumptions": _schedule_assumptions(support_span_m),
        "graph_warnings": _graph_warning_summary(graph_warnings or []),
        "runs": run_payloads,
        "segments": segment_payloads,
        "fitting_placeholders": {
            "plan_bends": plan_bends,
            "risers": risers,
            "counts": _fitting_counts(plan_bends, risers),
        },
        "groups": group_payloads,
        "totals": _totals_payload(run_payloads, segment_payloads, plan_bends, risers),
    }


def _schedule_assumptions(support_span_m):
    return [
        {
            "code": "raceway.schedule.traceability",
            "message": (
                "Schedule traceability uses durable run_key and node_key UUIDs. "
                "Projection-local graph keys such as N001/E001 are presentation keys only."
            ),
        },
        {
            "code": "raceway.schedule.support_placeholder",
            "support_span_m": support_span_m,
            "message": (
                "Support placeholders use ceil(run_length_m / support_span_m) + 1 per run. "
                "This is not a final support design or span-table validation."
            ),
        },
        {
            "code": "raceway.schedule.fitting_placeholder",
            "message": (
                "Fitting placeholders are geometry-derived counts only. Vendor fittings, bend radii, "
                "tees, crosses, and fabrication geometry are deferred."
            ),
        },
        {
            "code": "raceway.schedule.standard_length_piece_estimate",
            "message": (
                "Piece estimates use family standard_length_mm and ceil(run_length_m / standard_length_m). "
                "Offcut estimate ignores fitting deductions, cut planning, splice rules, and procurement rounding."
            ),
        },
        {
            "code": "raceway.schedule.junction_placeholder_deferred",
            "message": (
                "Junction, tee, and cross placeholder counts are deferred. Branch/junction graph nodes exist, "
                "but this schedule currently counts only plan-bend and riser placeholders."
            ),
        },
    ]


def _run_summary_payload(run, nodes, segments, bends, risers, length_m, support_span_m, support_placeholders):
    standard_length_m = _standard_length_m(run)
    piece_count_estimate = _piece_count_estimate(length_m, standard_length_m)
    offcut_m_estimate = _offcut_m_estimate(length_m, standard_length_m, piece_count_estimate)
    return {
        "run_id": run.pk,
        "run_key": str(run.key),
        "run_tag": run.tag or str(run.key),
        "family_id": run.family_id,
        "family_code": run.family.code,
        "family_kind": run.family.kind,
        "standard_length_mm": run.family.standard_length_mm,
        "size_id": run.size_id,
        "size_label": f"{run.size.width_mm} x {run.size.depth_mm} mm",
        "width_mm": run.size.width_mm,
        "depth_mm": run.size.depth_mm,
        "service_class": run.service_class,
        "node_count": len(nodes),
        "segment_count": len(segments),
        "length_m": length_m,
        "horizontal_length_m": sum(segment["horizontal_length_m"] for segment in segments),
        "riser_length_m": sum(segment["length_m"] for segment in segments if segment["is_riser"]),
        "plan_bend_count": len(bends),
        "riser_count": len(risers),
        "support_span_m": support_span_m,
        "support_placeholders": support_placeholders,
        "piece_count_estimate": piece_count_estimate,
        "offcut_m_estimate": offcut_m_estimate,
        "weight_kg": _weight_kg(run, length_m),
    }


def _segment_payload(run, start_node, end_node, segment_index):
    start = _point_from_node(start_node)
    end = _point_from_node(end_node)
    dx = end["x"] - start["x"]
    dy = end["y"] - start["y"]
    dz = end["z"] - start["z"]
    horizontal_length_m = math.hypot(dx, dy)
    length_m = math.sqrt((dx * dx) + (dy * dy) + (dz * dz))
    return {
        "run_id": run.pk,
        "run_key": str(run.key),
        "run_tag": run.tag or str(run.key),
        "segment_index": segment_index,
        "family_code": run.family.code,
        "size_label": f"{run.size.width_mm} x {run.size.depth_mm} mm",
        "service_class": run.service_class,
        "start_node_id": start_node.pk,
        "start_node_key": str(start_node.key),
        "start_sequence": start_node.sequence,
        "end_node_id": end_node.pk,
        "end_node_key": str(end_node.key),
        "end_sequence": end_node.sequence,
        "start_point_m": start,
        "end_point_m": end,
        "length_m": length_m,
        "horizontal_length_m": horizontal_length_m,
        "dz_m": dz,
        "is_riser": abs(dz) > RISER_ELEVATION_DELTA_M,
        "weight_kg": _weight_kg(run, length_m),
    }


def _plan_bend_payload(run, previous_node, node, next_node):
    angle_deg = _plan_bend_angle_deg(previous_node, node, next_node)
    if angle_deg is None or angle_deg < BEND_MIN_ANGLE_DEG:
        return None
    return {
        "run_id": run.pk,
        "run_key": str(run.key),
        "run_tag": run.tag or str(run.key),
        "node_id": node.pk,
        "node_key": str(node.key),
        "sequence": node.sequence,
        "angle_deg": angle_deg,
        "category": _bend_angle_category(angle_deg),
        "source_point_m": _point_from_node(node),
    }


def _riser_payload(segment):
    return {
        "run_id": segment["run_id"],
        "run_key": segment["run_key"],
        "run_tag": segment["run_tag"],
        "start_node_key": segment["start_node_key"],
        "end_node_key": segment["end_node_key"],
        "start_sequence": segment["start_sequence"],
        "end_sequence": segment["end_sequence"],
        "length_m": segment["length_m"],
        "dz_m": segment["dz_m"],
        "category": "riser_up" if segment["dz_m"] > 0 else "riser_down",
    }


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


def _bend_angle_category(angle_deg):
    if angle_deg <= 45:
        return "plan_bend_le_45"
    if angle_deg <= 90:
        return "plan_bend_46_90"
    return "plan_bend_gt_90"


def _add_to_group(groups, run, run_payload):
    group_key = f"{run.family.code}|{run.size.width_mm}x{run.size.depth_mm}|{run.service_class}"
    group = groups.setdefault(
        group_key,
        {
            "group_key": group_key,
            "family_id": run.family_id,
            "family_code": run.family.code,
            "family_kind": run.family.kind,
            "standard_length_mm": run.family.standard_length_mm,
            "size_id": run.size_id,
            "size_label": f"{run.size.width_mm} x {run.size.depth_mm} mm",
            "width_mm": run.size.width_mm,
            "depth_mm": run.size.depth_mm,
            "service_class": run.service_class,
            "run_count": 0,
            "segment_count": 0,
            "length_m": 0.0,
            "horizontal_length_m": 0.0,
            "riser_length_m": 0.0,
            "plan_bend_count": 0,
            "riser_count": 0,
            "support_placeholders": 0,
            "piece_count_estimate": 0,
            "offcut_m_estimate": 0.0,
            "known_weight_kg": 0.0,
            "has_unknown_weight": False,
        },
    )
    group["run_count"] += 1
    group["segment_count"] += run_payload["segment_count"]
    group["length_m"] += run_payload["length_m"]
    group["horizontal_length_m"] += run_payload["horizontal_length_m"]
    group["riser_length_m"] += run_payload["riser_length_m"]
    group["plan_bend_count"] += run_payload["plan_bend_count"]
    group["riser_count"] += run_payload["riser_count"]
    group["support_placeholders"] += run_payload["support_placeholders"]
    group["piece_count_estimate"] += run_payload["piece_count_estimate"]
    group["offcut_m_estimate"] += run_payload["offcut_m_estimate"]
    if run_payload["weight_kg"] is None:
        group["has_unknown_weight"] = True
    else:
        group["known_weight_kg"] += run_payload["weight_kg"]


def _fitting_counts(plan_bends, risers):
    bend_counts = defaultdict(int)
    riser_counts = defaultdict(int)
    for bend in plan_bends:
        bend_counts[bend["category"]] += 1
    for riser in risers:
        riser_counts[riser["category"]] += 1
    return {
        "plan_bends": dict(sorted(bend_counts.items())),
        "risers": dict(sorted(riser_counts.items())),
        "plan_bend_total": len(plan_bends),
        "riser_total": len(risers),
    }


def _totals_payload(runs, segments, plan_bends, risers):
    known_weight = sum(run["weight_kg"] for run in runs if run["weight_kg"] is not None)
    return {
        "run_count": len(runs),
        "segment_count": len(segments),
        "length_m": sum(run["length_m"] for run in runs),
        "horizontal_length_m": sum(run["horizontal_length_m"] for run in runs),
        "riser_length_m": sum(run["riser_length_m"] for run in runs),
        "plan_bend_count": len(plan_bends),
        "riser_count": len(risers),
        "support_placeholders": sum(run["support_placeholders"] for run in runs),
        "piece_count_estimate": sum(run["piece_count_estimate"] for run in runs),
        "offcut_m_estimate": sum(run["offcut_m_estimate"] for run in runs),
        "known_weight_kg": known_weight,
        "has_unknown_weight": any(run["weight_kg"] is None for run in runs),
    }


def _generation_envelope(layer):
    if layer is None:
        return {"generated_at": timezone.now().isoformat()}
    return {
        "generated_at": timezone.now().isoformat(),
        "project_id": layer.project_id,
        "layer_id": layer.pk,
        "layer_name": layer.name,
        "layer_status": layer.status,
        "layer_revision": layer.revision,
        "source_model_id": layer.source_model_id,
        "render_package_id": layer.render_package_id,
    }


def _graph_warning_summary(warnings):
    counts = defaultdict(int)
    for warning in warnings:
        counts[warning.get("code") or "unknown"] += 1
    return {
        "total": len(warnings),
        "by_code": dict(sorted(counts.items())),
        "near_miss_endpoint": counts.get("raceway.graph.near_miss_endpoint", 0),
        "unconnected_crossing": counts.get("raceway.graph.unconnected_crossing", 0),
        "zero_length_segment": counts.get("raceway.graph.zero_length_segment", 0),
    }


def _support_placeholder_count(length_m, support_span_m):
    if length_m <= 0:
        return 0
    return math.ceil(length_m / support_span_m) + 1


def _standard_length_m(run):
    return max(float(run.family.standard_length_mm or 0) / 1000.0, MIN_SEGMENT_LENGTH_M)


def _piece_count_estimate(length_m, standard_length_m):
    if length_m <= 0:
        return 0
    return math.ceil(length_m / standard_length_m)


def _offcut_m_estimate(length_m, standard_length_m, piece_count_estimate):
    if piece_count_estimate <= 0:
        return 0.0
    return max((piece_count_estimate * standard_length_m) - length_m, 0.0)


def _weight_kg(run, length_m):
    if run.size.weight_kg_per_m is None:
        return None
    return float(run.size.weight_kg_per_m) * length_m


def _point_from_node(node):
    return {
        "x": float(node.source_x_m),
        "y": float(node.source_y_m),
        "z": float(node.source_z_m),
    }
