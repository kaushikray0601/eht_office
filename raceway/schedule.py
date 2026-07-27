import math
from collections import defaultdict

from django.utils import timezone

from .geometry import (
    MIN_SEGMENT_LENGTH_M,
)
from .fittings import (
    build_layer_fitting_projection,
    fitting_counts,
    plan_bend_placeholder,
    riser_placeholder_from_segment,
    segment_payload,
)
from .graph import (
    build_layer_graph,
)
from .models import RacewayLayer, RacewayRun
from .warnings import build_layer_warnings, summarize_warnings


PLACEHOLDER_SUPPORT_SPAN_M = 3.0


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
    warnings = build_layer_warnings(layer_obj, graph_payload=graph, support_span_m=support_span_m)
    fitting_projection = build_layer_fitting_projection(layer_obj)
    return build_schedule_for_runs(
        runs,
        layer=layer_obj,
        graph_warnings=graph.get("warnings", []),
        warnings=warnings,
        fitting_projection=fitting_projection,
        support_span_m=support_span_m,
    )


def build_schedule_for_runs(
    runs,
    *,
    layer=None,
    graph_warnings=None,
    warnings=None,
    fitting_projection=None,
    support_span_m=PLACEHOLDER_SUPPORT_SPAN_M,
):
    run_payloads = []
    segment_payloads = []
    plan_bends = []
    risers = []
    groups = {}

    for run in runs:
        nodes = sorted(run.nodes.all(), key=lambda node: (node.sequence, node.pk))
        segments = [segment_payload(run, nodes[index - 1], nodes[index], index) for index in range(1, len(nodes))]
        bends = [
            bend
            for index in range(1, len(nodes) - 1)
            if (bend := plan_bend_placeholder(run, nodes[index - 1], nodes[index], nodes[index + 1])) is not None
        ]
        run_risers = [riser_placeholder_from_segment(segment) for segment in segments if segment["is_riser"]]
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
    branch_accessories = _branch_accessory_placeholders(fitting_projection)
    fitting_placeholder_counts = fitting_counts(plan_bends, risers, branch_accessories)
    return {
        **_generation_envelope(layer),
        "assumptions": _schedule_assumptions(support_span_m),
        "graph_warnings": _graph_warning_summary(graph_warnings or []),
        "warning_summary": summarize_warnings(warnings or []),
        "warnings": warnings or [],
        "runs": run_payloads,
        "segments": segment_payloads,
        "fitting_placeholders": {
            "plan_bends": plan_bends,
            "risers": risers,
            "branch_accessories": branch_accessories,
            "counts": fitting_placeholder_counts,
        },
        "groups": group_payloads,
        "totals": _totals_payload(run_payloads, segment_payloads, plan_bends, risers, branch_accessories),
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
                "Fitting placeholders are geometry-derived counts only. Vendor fittings, exact bend radii, "
                "accessory development dimensions, and fabrication geometry are deferred."
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
            "code": "raceway.schedule.gross_straight_length_basis",
            "message": (
                "Straight raceway lengths are gross centerline segment lengths. Bend, riser, reducer, tee, and cross "
                "development lengths are not deducted from straight lengths in this MVP schedule basis."
            ),
        },
        {
            "code": "raceway.schedule.tee_cross_projection_only",
            "message": (
                "Tee/cross counts are projection-only branch accessory placeholders. Main/branch catalogue "
                "designation and procurement sizing remain unresolved unless later user-confirmed."
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


def _totals_payload(runs, segments, plan_bends, risers, branch_accessories=None):
    branch_accessories = branch_accessories or []
    known_weight = sum(run["weight_kg"] for run in runs if run["weight_kg"] is not None)
    return {
        "run_count": len(runs),
        "segment_count": len(segments),
        "length_m": sum(run["length_m"] for run in runs),
        "horizontal_length_m": sum(run["horizontal_length_m"] for run in runs),
        "riser_length_m": sum(run["riser_length_m"] for run in runs),
        "plan_bend_count": len(plan_bends),
        "riser_count": len(risers),
        "tee_count": sum(1 for item in branch_accessories if item.get("kind") == "tee"),
        "cross_count": sum(1 for item in branch_accessories if item.get("kind") == "cross"),
        "branch_accessory_count": len(branch_accessories),
        "support_placeholders": sum(run["support_placeholders"] for run in runs),
        "piece_count_estimate": sum(run["piece_count_estimate"] for run in runs),
        "offcut_m_estimate": sum(run["offcut_m_estimate"] for run in runs),
        "known_weight_kg": known_weight,
        "has_unknown_weight": any(run["weight_kg"] is None for run in runs),
    }


def _branch_accessory_placeholders(fitting_projection):
    if not fitting_projection:
        return []
    placeholders = []
    for item in fitting_projection.get("items", []):
        if item.get("kind") not in {"tee", "cross"}:
            continue
        branch_intent = item.get("branch_intent") or {}
        ports = item.get("ports") or []
        placeholders.append(
            {
                "fitting_key": item.get("fitting_key", ""),
                "kind": item.get("kind", ""),
                "category": item.get("category", ""),
                "status": item.get("status", ""),
                "graph_node_key": item.get("graph_node_key", ""),
                "graph_node_kind": item.get("graph_node_kind", ""),
                "degree": item.get("degree", 0),
                "source_point_m": item.get("source_point_m", {}),
                "port_count": len(ports),
                "run_tags": sorted({port.get("run_tag", "") for port in ports if port.get("run_tag")}),
                "branch_intent_status": branch_intent.get("status", ""),
                "branch_intent_persistence": branch_intent.get("persistence", "projection_only"),
                "branch_intent_ambiguous": bool(branch_intent.get("ambiguous")),
                "requires_catalogue_validation": bool(item.get("requires_catalogue_validation")),
                "requires_face_alignment": bool(item.get("requires_face_alignment")),
                "sizing_status": "projection_only_unresolved",
                "message": (
                    "Projection-only branch fitting count. Catalogue main/branch sizing is not designated "
                    "until the branch intent is unambiguous or user-confirmed."
                ),
            }
        )
    return sorted(placeholders, key=lambda item: (item["kind"], item["graph_node_key"], item["fitting_key"]))


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
