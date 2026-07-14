import math
from collections import defaultdict

from django.utils import timezone

from .geometry import (
    MIN_SEGMENT_LENGTH_M,
    plan_bend_angle_deg,
    point_from_node,
)
from .graph import RISER_ELEVATION_DELTA_M, build_layer_graph
from .models import RacewayLayer, RacewayRun


BEND_MIN_ANGLE_DEG = 5.0
BEND_STANDARD_ANGLES_DEG = (30.0, 45.0, 60.0, 90.0)
BEND_STANDARD_ANGLE_TOLERANCE_DEG = 2.5
FITTING_PROJECTION_VERSION = "raceway.fittings.v0"


def build_layer_fitting_projection(layer):
    layer_obj = layer if isinstance(layer, RacewayLayer) else RacewayLayer.objects.get(pk=int(layer))
    runs = list(
        RacewayRun.objects
        .select_related("layer", "family", "size")
        .prefetch_related("nodes")
        .filter(layer=layer_obj)
        .order_by("tag", "pk")
    )
    graph = build_layer_graph(layer_obj).to_payload()
    items = []
    for run in runs:
        nodes = sorted(run.nodes.all(), key=lambda node: (node.sequence, node.pk))
        segments = [segment_payload(run, nodes[index - 1], nodes[index], index) for index in range(1, len(nodes))]
        items.extend(
            bend
            for index in range(1, len(nodes) - 1)
            if (bend := plan_bend_placeholder(run, nodes[index - 1], nodes[index], nodes[index + 1])) is not None
        )
        items.extend(riser_placeholder_from_segment(segment) for segment in segments if segment["is_riser"])
    items.extend(_reducer_candidates(graph, runs))
    items = sorted(items, key=_fitting_sort_key)
    return {
        **_generation_envelope(layer_obj),
        "projection": FITTING_PROJECTION_VERSION,
        "status": "derived_placeholder",
        "assumptions": _fitting_assumptions(),
        "items": items,
        "counts": fitting_item_counts(items),
        "graph_summary": _graph_summary(graph),
    }


def segment_payload(run, start_node, end_node, segment_index):
    start = point_from_node(start_node)
    end = point_from_node(end_node)
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
        "family_kind": run.family.kind,
        "size_label": f"{run.size.width_mm} x {run.size.depth_mm} mm",
        "width_mm": run.size.width_mm,
        "depth_mm": run.size.depth_mm,
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


def plan_bend_placeholder(run, previous_node, node, next_node):
    angle_deg = plan_bend_angle_deg(previous_node, node, next_node)
    if angle_deg is None or angle_deg < BEND_MIN_ANGLE_DEG:
        return None
    standard_angle = bend_standard_angle_check(angle_deg)
    return {
        **_run_fitting_basis(run),
        "fitting_key": f"fit:{run.key}:node:{node.key}:plan_bend",
        "kind": "plan_bend",
        "category": bend_angle_category(angle_deg),
        "status": "placeholder",
        "derivation": "centerline_direction_change",
        "node_id": node.pk,
        "node_key": str(node.key),
        "previous_node_key": str(previous_node.key),
        "next_node_key": str(next_node.key),
        "sequence": node.sequence,
        "angle_deg": angle_deg,
        "nearest_standard_angle_deg": standard_angle["nearest_standard_angle_deg"],
        "deviation_deg": standard_angle["deviation_deg"],
        "standard_angle_tolerance_deg": BEND_STANDARD_ANGLE_TOLERANCE_DEG,
        "non_standard_angle": standard_angle["non_standard_angle"],
        "source_point_m": point_from_node(node),
        "requires_catalogue_validation": True,
        "requires_face_alignment": False,
        "face_alignment": {
            "basis": "shared_centerline_node",
            "status": "not_modelled",
        },
    }


def riser_placeholder_from_segment(segment):
    horizontal = max(float(segment["horizontal_length_m"]), 0.0)
    dz = float(segment["dz_m"])
    slope_angle = 90.0 if horizontal < MIN_SEGMENT_LENGTH_M else math.degrees(math.atan2(abs(dz), horizontal))
    return {
        "run_id": segment["run_id"],
        "run_key": segment["run_key"],
        "run_tag": segment["run_tag"],
        "family_code": segment["family_code"],
        "family_kind": segment["family_kind"],
        "size_label": segment["size_label"],
        "width_mm": segment["width_mm"],
        "depth_mm": segment["depth_mm"],
        "service_class": segment["service_class"],
        "fitting_key": f"fit:{segment['run_key']}:seg:{segment['segment_index']}:riser",
        "kind": "riser",
        "category": "riser_up" if dz > 0 else "riser_down",
        "status": "placeholder",
        "derivation": "centerline_elevation_change",
        "segment_index": segment["segment_index"],
        "start_node_id": segment["start_node_id"],
        "start_node_key": segment["start_node_key"],
        "end_node_id": segment["end_node_id"],
        "end_node_key": segment["end_node_key"],
        "start_sequence": segment["start_sequence"],
        "end_sequence": segment["end_sequence"],
        "start_point_m": segment["start_point_m"],
        "end_point_m": segment["end_point_m"],
        "length_m": segment["length_m"],
        "horizontal_length_m": segment["horizontal_length_m"],
        "dz_m": dz,
        "slope_angle_deg": slope_angle,
        "requires_catalogue_validation": True,
        "requires_face_alignment": True,
        "face_alignment": {
            "basis": "centerline_segment",
            "status": "required_not_modelled",
            "note": "Riser fitting orientation and inside/outside handedness need the face-offset workflow.",
        },
    }


def fitting_counts(plan_bends, risers):
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
        "non_standard_plan_bend_total": sum(1 for bend in plan_bends if bend.get("non_standard_angle")),
        "riser_total": len(risers),
    }


def fitting_item_counts(items):
    by_kind = defaultdict(int)
    by_category = defaultdict(int)
    for item in items:
        by_kind[item.get("kind") or "unknown"] += 1
        by_category[item.get("category") or "unknown"] += 1
    return {
        "total": len(items),
        "by_kind": dict(sorted(by_kind.items())),
        "by_category": dict(sorted(by_category.items())),
        "requires_catalogue_validation": sum(1 for item in items if item.get("requires_catalogue_validation")),
        "requires_face_alignment": sum(1 for item in items if item.get("requires_face_alignment")),
        "non_standard_plan_bends": sum(
            1
            for item in items
            if item.get("kind") == "plan_bend" and item.get("non_standard_angle")
        ),
    }


def bend_angle_category(angle_deg):
    if angle_deg <= 45:
        return "plan_bend_le_45"
    if angle_deg <= 90:
        return "plan_bend_46_90"
    return "plan_bend_gt_90"


def bend_standard_angle_check(angle_deg):
    nearest = min(BEND_STANDARD_ANGLES_DEG, key=lambda candidate: abs(candidate - angle_deg))
    deviation = abs(float(angle_deg) - nearest)
    return {
        "nearest_standard_angle_deg": nearest,
        "deviation_deg": deviation,
        "non_standard_angle": deviation > BEND_STANDARD_ANGLE_TOLERANCE_DEG,
    }


def _reducer_candidates(graph, runs):
    runs_by_id = {run.pk: run for run in runs}
    candidates = []
    for graph_node in graph.get("nodes", []):
        members = _node_members_with_run_context(graph_node, runs_by_id)
        if len(members) < 2:
            continue
        size_groups = _size_groups(members)
        if len(size_groups) < 2:
            continue
        category = _reducer_category(size_groups)
        candidates.append(
            {
                "fitting_key": f"fit:graph:{graph_node['key']}:reducer",
                "kind": "reducer_candidate",
                "category": category,
                "status": "placeholder",
                "derivation": "connected_graph_members_with_unequal_sizes",
                "graph_node_key": graph_node["key"],
                "graph_node_kind": graph_node.get("derived_kind", ""),
                "source_point_m": graph_node.get("source_point_m", {}),
                "members": members,
                "size_groups": size_groups,
                "requires_catalogue_validation": True,
                "requires_face_alignment": True,
                "face_alignment": {
                    "basis": "shared_centerline_node",
                    "status": "required_not_modelled",
                    "note": "Reducer handedness/offset must align tray faces, not only the centerline node.",
                },
            }
        )
    return candidates


def _node_members_with_run_context(graph_node, runs_by_id):
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
                "family_kind": run.family.kind,
                "size_label": f"{run.size.width_mm} x {run.size.depth_mm} mm",
                "width_mm": run.size.width_mm,
                "depth_mm": run.size.depth_mm,
                "service_class": run.service_class,
            }
        )
    return sorted(members, key=lambda item: (item["run_tag"], item["sequence"], item["node_key"]))


def _size_groups(members):
    groups = {}
    for member in members:
        key = (
            member["family_code"],
            member["family_kind"],
            member["width_mm"],
            member["depth_mm"],
            member["service_class"],
        )
        group = groups.setdefault(
            key,
            {
                "family_code": member["family_code"],
                "family_kind": member["family_kind"],
                "size_label": member["size_label"],
                "width_mm": member["width_mm"],
                "depth_mm": member["depth_mm"],
                "service_class": member["service_class"],
                "run_keys": [],
            },
        )
        group["run_keys"].append(member["run_key"])
    return sorted(
        groups.values(),
        key=lambda item: (item["family_code"], item["width_mm"], item["depth_mm"], item["service_class"]),
    )


def _reducer_category(size_groups):
    widths = {group["width_mm"] for group in size_groups}
    depths = {group["depth_mm"] for group in size_groups}
    families = {group["family_code"] for group in size_groups}
    services = {group["service_class"] for group in size_groups}
    if len(families) > 1:
        return "family_transition"
    if len(services) > 1:
        return "service_transition"
    if len(widths) > 1 and len(depths) > 1:
        return "width_depth_reducer"
    if len(widths) > 1:
        return "width_reducer"
    return "depth_reducer"


def _run_fitting_basis(run):
    return {
        "run_id": run.pk,
        "run_key": str(run.key),
        "run_tag": run.tag or str(run.key),
        "family_code": run.family.code,
        "family_kind": run.family.kind,
        "size_label": f"{run.size.width_mm} x {run.size.depth_mm} mm",
        "width_mm": run.size.width_mm,
        "depth_mm": run.size.depth_mm,
        "service_class": run.service_class,
    }


def _weight_kg(run, length_m):
    if run.size.weight_kg_per_m is None:
        return None
    return float(run.size.weight_kg_per_m) * length_m


def _fitting_assumptions():
    return [
        {
            "code": "raceway.fittings.route_as_truth",
            "message": (
                "Fittings are derived from saved centerline runs and graph nodes. "
                "No fitting/accessory rows are persisted in this projection."
            ),
        },
        {
            "code": "raceway.fittings.catalogue_deferred",
            "message": (
                "Vendor part numbers, bend radii, development lengths, covers, dividers, and exact accessory geometry "
                "are not selected by this first-pass projection."
            ),
        },
        {
            "code": "raceway.fittings.standard_angle_check",
            "standard_angles_deg": list(BEND_STANDARD_ANGLES_DEG),
            "tolerance_deg": BEND_STANDARD_ANGLE_TOLERANCE_DEG,
            "message": (
                "Plan bends are checked against common 30/45/60/90 degree catalogue angles. "
                "Non-standard angles are advisory flags until a vendor catalogue is selected."
            ),
        },
        {
            "code": "raceway.fittings.face_alignment_deferred",
            "message": (
                "Reducer and riser placeholders are marked where tray faces must be aligned. "
                "The current centerline model does not yet store face offsets or handedness."
            ),
        },
        {
            "code": "raceway.fittings.tee_cross_deferred",
            "message": (
                "Branch/junction graph nodes are visible in the graph projection, but tee/cross fitting materialization "
                "is deferred until mid-run split and branch semantics are finalized."
            ),
        },
    ]


def _graph_summary(graph):
    graph_nodes = graph.get("nodes", [])
    return {
        "node_count": len(graph_nodes),
        "edge_count": len(graph.get("edges", [])),
        "branch_node_count": sum(1 for node in graph_nodes if node.get("derived_kind") == "branch"),
        "junction_node_count": sum(1 for node in graph_nodes if node.get("derived_kind") == "junction"),
        "warning_count": len(graph.get("warnings", [])),
    }


def _generation_envelope(layer):
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


def _fitting_sort_key(item):
    return (
        item.get("run_tag", ""),
        item.get("graph_node_key", ""),
        item.get("sequence", item.get("segment_index", 0)) or 0,
        item.get("kind", ""),
        item.get("fitting_key", ""),
    )
