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
ACCESSORY_PROXY_SCHEMA = "raceway.accessory_proxy.v0"
ACCESSORY_DEFAULT_BEND_RADIUS_M = 0.6
ACCESSORY_PROXY_CURVE_SEGMENTS = 8
SEGMENT_FACE_OFFSET_EPSILON_M = 0.0005
REDUCER_DEFAULT_DEVELOPMENT_LENGTH_M = 0.45
REDUCER_DEVELOPMENT_WIDTH_FACTOR = 2.0
REDUCER_DEFAULT_HANDEDNESS = "left_edge"
REDUCER_HANDEDNESS_OPTIONS = ("left_edge", "right_edge", "centerline")
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
        items.extend(
            step
            for index in range(1, len(nodes) - 1)
            if (step := face_offset_step_placeholder(run, nodes[index - 1], nodes[index], nodes[index + 1])) is not None
        )
        items.extend(riser_placeholder_from_segment(segment) for segment in segments if segment["is_riser"])
    items.extend(_branch_accessory_placeholders(graph, runs))
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
    face_offset_m = _segment_face_offset_m(run, str(start_node.key), str(end_node.key))
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
        "face_offset_m": face_offset_m,
        "edge_offsets_m": _edge_offsets_m(run.size.width_mm, face_offset_m),
        "weight_kg": _weight_kg(run, length_m),
    }


def plan_bend_placeholder(run, previous_node, node, next_node):
    angle_deg = plan_bend_angle_deg(previous_node, node, next_node)
    if angle_deg is None or angle_deg < BEND_MIN_ANGLE_DEG:
        return None
    standard_angle = bend_standard_angle_check(angle_deg)
    cutback_m = _bend_cutback_m(angle_deg)
    return {
        **_run_fitting_basis(run),
        "fitting_key": f"fit:{run.key}:node:{node.key}:plan_bend",
        "kind": "plan_bend",
        "category": bend_angle_category(angle_deg),
        "status": "synthetic_proxy",
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
        "default_radius_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
        "cutback_m": cutback_m,
        "geometry_recipe": _plan_bend_geometry_recipe(previous_node, node, next_node, angle_deg, cutback_m),
        "requires_catalogue_validation": True,
        "requires_face_alignment": False,
        "face_alignment": {
            "basis": "shared_centerline_node",
            "status": "proxy_modelled",
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
        "status": "synthetic_proxy",
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
        "face_offset_m": segment.get("face_offset_m", 0.0),
        "edge_offsets_m": segment.get("edge_offsets_m", {}),
        "slope_angle_deg": slope_angle,
        "default_radius_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
        "cutback_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
        "geometry_recipe": _riser_geometry_recipe(segment, slope_angle),
        "requires_catalogue_validation": True,
        "requires_face_alignment": True,
        "face_alignment": {
            "basis": "centerline_segment",
            "status": "proxy_modelled_orientation_unresolved",
            "note": "Riser proxy is generated from centerline geometry; inside/outside handedness still needs orientation resolution.",
        },
    }


def face_offset_step_placeholder(run, previous_node, node, next_node):
    previous_offset_m = _segment_face_offset_m(run, str(previous_node.key), str(node.key))
    next_offset_m = _segment_face_offset_m(run, str(node.key), str(next_node.key))
    delta_m = next_offset_m - previous_offset_m
    if abs(delta_m) < SEGMENT_FACE_OFFSET_EPSILON_M:
        return None
    previous_edges = _edge_offsets_m(run.size.width_mm, previous_offset_m)
    next_edges = _edge_offsets_m(run.size.width_mm, next_offset_m)
    return {
        **_run_fitting_basis(run),
        "fitting_key": f"fit:{run.key}:node:{node.key}:face_offset_step",
        "kind": "face_offset_step",
        "category": "same_size_face_offset_step",
        "status": "placeholder",
        "derivation": "adjacent_segments_with_different_face_offsets",
        "node_id": node.pk,
        "node_key": str(node.key),
        "previous_node_key": str(previous_node.key),
        "next_node_key": str(next_node.key),
        "sequence": node.sequence,
        "previous_segment_index": node.sequence,
        "next_segment_index": node.sequence + 1,
        "previous_face_offset_m": previous_offset_m,
        "next_face_offset_m": next_offset_m,
        "face_offset_delta_m": delta_m,
        "left_edge_delta_m": next_edges["left_edge_m"] - previous_edges["left_edge_m"],
        "right_edge_delta_m": next_edges["right_edge_m"] - previous_edges["right_edge_m"],
        "source_point_m": point_from_node(node),
        "requires_catalogue_validation": True,
        "requires_face_alignment": True,
        "face_alignment": {
            "basis": "segment_face_offset",
            "status": "offset_step_unresolved",
            "current_status": "offsets_differ",
            "epsilon_m": SEGMENT_FACE_OFFSET_EPSILON_M,
            "note": (
                "Adjacent same-size tray segments have different face offsets at this node. "
                "Align offsets or later accept a reducer/offset accessory."
            ),
        },
    }


def fitting_counts(plan_bends, risers, branch_accessories=None):
    branch_accessories = branch_accessories or []
    bend_counts = defaultdict(int)
    riser_counts = defaultdict(int)
    branch_counts = defaultdict(int)
    branch_status_counts = defaultdict(int)
    for bend in plan_bends:
        bend_counts[bend["category"]] += 1
    for riser in risers:
        riser_counts[riser["category"]] += 1
    for accessory in branch_accessories:
        branch_counts[accessory.get("category") or "unknown"] += 1
        branch_status_counts[accessory.get("sizing_status") or accessory.get("status") or "unknown"] += 1
    return {
        "plan_bends": dict(sorted(bend_counts.items())),
        "risers": dict(sorted(riser_counts.items())),
        "branch_accessories": dict(sorted(branch_counts.items())),
        "branch_accessory_status": dict(sorted(branch_status_counts.items())),
        "plan_bend_total": len(plan_bends),
        "non_standard_plan_bend_total": sum(1 for bend in plan_bends if bend.get("non_standard_angle")),
        "riser_total": len(risers),
        "tee_total": sum(1 for accessory in branch_accessories if accessory.get("kind") == "tee"),
        "cross_total": sum(1 for accessory in branch_accessories if accessory.get("kind") == "cross"),
        "branch_accessory_total": len(branch_accessories),
        "branch_accessory_unresolved_total": branch_status_counts.get("projection_only_unresolved", 0),
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
        "synthetic_proxy_total": sum(1 for item in items if item.get("status") == "synthetic_proxy"),
        "reducer_proxy_total": sum(
            1
            for item in items
            if item.get("kind") == "reducer_candidate" and item.get("status") == "synthetic_proxy"
        ),
        "one_edge_alignment_candidates": sum(
            1
            for item in items
            if item.get("kind") == "reducer_candidate"
            and item.get("face_alignment", {}).get("basis") == "one_edge_matching"
        ),
        "face_alignment_resolved_by_offset": sum(
            1
            for item in items
            if item.get("face_alignment", {}).get("status") == "offsets_match_recommended_edge"
        ),
        "face_offset_steps": sum(1 for item in items if item.get("kind") == "face_offset_step"),
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


def _bend_cutback_m(angle_deg, radius_m=ACCESSORY_DEFAULT_BEND_RADIUS_M):
    return float(radius_m) * math.tan(math.radians(float(angle_deg) / 2.0))


def _point_from_center_toward(center_node, target_node, distance_m):
    center = point_from_node(center_node)
    target = point_from_node(target_node)
    dx = target["x"] - center["x"]
    dy = target["y"] - center["y"]
    dz = target["z"] - center["z"]
    length = math.sqrt((dx * dx) + (dy * dy) + (dz * dz))
    if length < MIN_SEGMENT_LENGTH_M:
        return center
    distance = min(max(float(distance_m), 0.0), length)
    return {
        "x": center["x"] + (dx / length) * distance,
        "y": center["y"] + (dy / length) * distance,
        "z": center["z"] + (dz / length) * distance,
    }


def _plan_bend_geometry_recipe(previous_node, node, next_node, angle_deg, cutback_m):
    return {
        "schema": ACCESSORY_PROXY_SCHEMA,
        "proxy_kind": "plan_bend_curve",
        "radius_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
        "curve_segments": ACCESSORY_PROXY_CURVE_SEGMENTS,
        "angle_deg": angle_deg,
        "cutback_m": cutback_m,
        "control_points_m": {
            "incoming_tangent_point": _point_from_center_toward(node, previous_node, cutback_m),
            "route_node": point_from_node(node),
            "outgoing_tangent_point": _point_from_center_toward(node, next_node, cutback_m),
        },
        "straight_proxy_cutback": {
            "incoming_m": cutback_m,
            "outgoing_m": cutback_m,
            "basis": "radius_tan_half_angle",
        },
    }


def _riser_geometry_recipe(segment, slope_angle_deg):
    return {
        "schema": ACCESSORY_PROXY_SCHEMA,
        "proxy_kind": "riser_curve",
        "radius_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
        "curve_segments": ACCESSORY_PROXY_CURVE_SEGMENTS,
        "cutback_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
        "slope_angle_deg": slope_angle_deg,
        "start_point_m": segment["start_point_m"],
        "end_point_m": segment["end_point_m"],
        "straight_proxy_cutback": {
            "start_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
            "end_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
            "basis": "default_riser_radius",
        },
    }


def _branch_accessory_placeholders(graph, runs):
    runs_by_id = {run.pk: run for run in runs}
    placeholders = []
    for graph_node in graph.get("nodes", []):
        degree = int(graph_node.get("degree") or 0)
        if degree < 3:
            continue
        members = _node_members_with_run_context(graph_node, runs_by_id)
        if len(members) < 2:
            continue
        kind = "cross" if degree >= 4 else "tee"
        category = "four_way_cross" if kind == "cross" else "three_way_tee"
        size_groups = _size_groups(members)
        mixed_physical_sizes = len({
            (group["family_code"], group["width_mm"], group["depth_mm"])
            for group in size_groups
        }) > 1
        placeholders.append(
            {
                "fitting_key": f"fit:graph:{graph_node['key']}:{kind}",
                "kind": kind,
                "category": category,
                "status": "synthetic_proxy",
                "derivation": "connected_graph_node_degree",
                "graph_node_key": graph_node["key"],
                "graph_node_kind": graph_node.get("derived_kind", ""),
                "degree": degree,
                "source_point_m": graph_node.get("source_point_m", {}),
                "members": members,
                "ports": _branch_ports(members),
                "size_groups": size_groups,
                "branch_intent": _branch_intent(kind, members),
                "requires_catalogue_validation": True,
                "requires_face_alignment": mixed_physical_sizes,
                "geometry_recipe": _branch_geometry_recipe(graph_node, kind, members),
                "face_alignment": {
                    "basis": "branch_node_ports",
                    "status": "proxy_modelled_size_review" if mixed_physical_sizes else "proxy_modelled",
                    "note": (
                        "Branch accessory proxy is generated from connected graph ports. "
                        "Mixed widths/depths need reducer/branch-size review before catalogue selection."
                    ),
                },
            }
        )
    return placeholders


def _branch_ports(members):
    ports = []
    for member in members:
        for segment in member.get("adjacent_segments") or []:
            ports.append(
                {
                    "run_key": member["run_key"],
                    "run_tag": member["run_tag"],
                    "node_key": member["node_key"],
                    "segment_key": segment["segment_key"],
                    "segment_index": segment["segment_index"],
                    "role_at_node": segment["role_at_node"],
                    "family_code": member["family_code"],
                    "family_kind": member["family_kind"],
                    "width_mm": member["width_mm"],
                    "depth_mm": member["depth_mm"],
                    "service_class": member["service_class"],
                    "face_offset_m": segment.get("face_offset_m", 0.0),
                    "edge_offsets_m": segment.get("edge_offsets_m", {}),
                }
            )
    return sorted(ports, key=lambda item: (item["run_tag"], item["segment_index"], item["role_at_node"]))


def _branch_intent(kind, members):
    through_members = [
        member
        for member in members
        if len(member.get("adjacent_segments") or []) >= 2
    ]
    through_run_keys = [member["run_key"] for member in through_members]
    through_run_tags = [member["run_tag"] for member in through_members]
    branch_members = [
        member
        for member in members
        if member["run_key"] not in set(through_run_keys)
    ]
    status = "main_ambiguous"
    note = "Main/branch selection is projection-only and needs user review."
    if kind == "tee" and len(through_members) == 1:
        status = "main_inferred"
        note = "Tee main is inferred from the member that passes through the graph node."
    elif kind == "cross" and len(through_members) >= 2:
        status = "cross_axes_inferred"
        note = "Cross axes are inferred from members that pass through the graph node."
    elif kind == "cross" and len(through_members) == 1:
        status = "main_inferred_branch_review"
        note = "Cross has one through member; secondary branch axis still needs user/catalogue review."
    return {
        "basis": "connected_graph_node_degree",
        "status": status,
        "persistence": "projection_only",
        "ambiguous": status == "main_ambiguous",
        "main_run_keys": through_run_keys,
        "main_run_tags": through_run_tags,
        "branch_run_keys": [member["run_key"] for member in branch_members],
        "branch_run_tags": [member["run_tag"] for member in branch_members],
        "note": note,
    }


def _branch_geometry_recipe(graph_node, kind, members):
    return {
        "schema": ACCESSORY_PROXY_SCHEMA,
        "proxy_kind": f"{kind}_node_proxy",
        "center_point_m": graph_node.get("source_point_m", {}),
        "degree": int(graph_node.get("degree") or 0),
        "default_radius_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
        "curve_segments": ACCESSORY_PROXY_CURVE_SEGMENTS,
        "port_count": sum(len(member.get("adjacent_segments") or []) for member in members),
        "straight_proxy_cutback": {
            "default_each_port_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
            "basis": "default_branch_radius",
        },
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
        face_alignment = _reducer_face_alignment(category, members)
        geometry_recipe = _reducer_geometry_recipe(category, graph_node, members, face_alignment)
        candidates.append(
            {
                "fitting_key": f"fit:graph:{graph_node['key']}:reducer",
                "kind": "reducer_candidate",
                "category": category,
                "status": "synthetic_proxy" if geometry_recipe else "placeholder",
                "derivation": "connected_graph_members_with_unequal_sizes",
                "graph_node_key": graph_node["key"],
                "graph_node_kind": graph_node.get("derived_kind", ""),
                "source_point_m": graph_node.get("source_point_m", {}),
                "members": members,
                "size_groups": size_groups,
                "requires_catalogue_validation": True,
                "requires_face_alignment": (
                    _reducer_requires_face_alignment(category)
                    and face_alignment.get("status") != "offsets_match_recommended_edge"
                ),
                "face_alignment": face_alignment,
                **({"geometry_recipe": geometry_recipe} if geometry_recipe else {}),
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
                "adjacent_segments": _adjacent_segments_for_member(run, member.get("node_key", "")),
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


def _reducer_requires_face_alignment(category):
    return category != "service_transition"


def _reducer_face_alignment(category, members):
    if not _reducer_requires_face_alignment(category):
        return {
            "basis": "service_transition",
            "status": "not_required",
            "current_status": "same_physical_size",
            "note": "Service transitions are segregation/modeling warnings, not reducer geometry by themselves.",
        }
    alignment_members = [_alignment_member_payload(member) for member in members]
    alignment_members = [member for member in alignment_members if member is not None]
    if len(alignment_members) < 2:
        missing_members = [
            {
                "run_key": member["run_key"],
                "run_tag": member["run_tag"],
                "node_key": member["node_key"],
                "adjacent_segment_count": len(member.get("adjacent_segments") or []),
            }
            for member in members
            if not member.get("adjacent_segments")
        ]
        return {
            "basis": "one_edge_matching",
            "status": "required_not_modelled",
            "current_status": "insufficient_segment_context",
            "recommended_handedness": REDUCER_DEFAULT_HANDEDNESS,
            "options": list(REDUCER_HANDEDNESS_OPTIONS),
            "segment_context": {
                "member_count": len(members),
                "alignment_member_count": len(alignment_members),
                "missing_adjacent_segment_count": len(missing_members),
                "missing_members": missing_members,
            },
            "note": "Reducer handedness needs adjacent segment context at the shared graph node.",
        }
    current_status = _current_alignment_status(alignment_members)
    suggestions_by_handedness = {
        handedness: _alignment_suggestion(alignment_members, handedness)
        for handedness in REDUCER_HANDEDNESS_OPTIONS
    }
    recommended = suggestions_by_handedness[REDUCER_DEFAULT_HANDEDNESS]
    status = (
        "offsets_match_recommended_edge"
        if current_status == f"{REDUCER_DEFAULT_HANDEDNESS}_aligned"
        else "required_not_modelled"
    )
    return {
        "basis": "one_edge_matching",
        "status": status,
        "current_status": current_status,
        "centerline_aligned": (
            _spread_m(member["current_face_offset_m"] for member in alignment_members)
            <= SEGMENT_FACE_OFFSET_EPSILON_M
        ),
        "recommended_handedness": REDUCER_DEFAULT_HANDEDNESS,
        "options": list(REDUCER_HANDEDNESS_OPTIONS),
        "suggestions_by_handedness": suggestions_by_handedness,
        "edge_reference": "left/right are relative to each adjacent segment's saved node order.",
        "epsilon_m": SEGMENT_FACE_OFFSET_EPSILON_M,
        "recommended_offsets": recommended["member_offsets"],
        "max_recommended_offset_delta_m": recommended["max_delta_m"],
        "ambiguous_member_count": sum(1 for member in members if len(member.get("adjacent_segments") or []) > 1),
        "note": (
            "Reducer/expander default is one-edge matching. "
            "Centerline matching remains an explicit uncommon option."
        ),
    }


def _reducer_geometry_recipe(category, graph_node, members, face_alignment):
    if category != "width_reducer":
        return None
    if face_alignment.get("status") != "offsets_match_recommended_edge":
        return None
    alignment_members = [_alignment_member_payload(member) for member in members]
    alignment_members = [member for member in alignment_members if member is not None]
    if len(alignment_members) != 2:
        return None
    development_length_m = _reducer_development_length_m(alignment_members)
    return {
        "schema": ACCESSORY_PROXY_SCHEMA,
        "proxy_kind": "reducer_taper",
        "handedness": face_alignment.get("recommended_handedness") or REDUCER_DEFAULT_HANDEDNESS,
        "development_length_m": development_length_m,
        "development_length_basis": "max(default_0_45m, 2x_width_delta)",
        "center_point_m": graph_node.get("source_point_m", {}),
        "ports": [
            {
                "run_key": member["run_key"],
                "run_tag": member["run_tag"],
                "node_key": member["node_key"],
                "segment_key": member["segment_key"],
                "segment_index": member["segment_index"],
                "role_at_node": member["segment_role_at_node"],
                "width_mm": member["width_mm"],
                "depth_mm": member["depth_mm"],
                "face_offset_m": member["current_face_offset_m"],
                "edge_offsets_m": member["edge_offsets_m"],
            }
            for member in sorted(alignment_members, key=lambda item: (-item["width_mm"], item["run_tag"], item["segment_index"]))
        ],
        "straight_proxy_cutback": {
            "each_port_m": development_length_m / 2.0,
            "basis": "half_reducer_development_length",
        },
    }


def _reducer_development_length_m(alignment_members):
    widths_m = [max(float(member["width_mm"] or 0.0), 0.0) / 1000.0 for member in alignment_members]
    width_delta_m = max(widths_m, default=0.0) - min(widths_m, default=0.0)
    return max(REDUCER_DEFAULT_DEVELOPMENT_LENGTH_M, REDUCER_DEVELOPMENT_WIDTH_FACTOR * width_delta_m)


def _alignment_member_payload(member):
    adjacent_segments = member.get("adjacent_segments") or []
    if not adjacent_segments:
        return None
    segment = adjacent_segments[0]
    face_offset_m = float(segment.get("face_offset_m") or 0.0)
    edge_offsets = _edge_offsets_m(member["width_mm"], face_offset_m)
    return {
        "run_key": member["run_key"],
        "run_tag": member["run_tag"],
        "node_key": member["node_key"],
        "segment_index": segment["segment_index"],
        "segment_key": segment["segment_key"],
        "segment_role_at_node": segment["role_at_node"],
        "width_mm": member["width_mm"],
        "depth_mm": member["depth_mm"],
        "current_face_offset_m": face_offset_m,
        "edge_offsets_m": edge_offsets,
        "adjacent_segment_count": len(adjacent_segments),
    }


def _current_alignment_status(alignment_members):
    if _spread_m(member["edge_offsets_m"]["left_edge_m"] for member in alignment_members) <= SEGMENT_FACE_OFFSET_EPSILON_M:
        return "left_edge_aligned"
    if _spread_m(member["edge_offsets_m"]["right_edge_m"] for member in alignment_members) <= SEGMENT_FACE_OFFSET_EPSILON_M:
        return "right_edge_aligned"
    return "edges_not_aligned"


def _alignment_suggestion(alignment_members, handedness):
    reference = max(alignment_members, key=lambda member: (member["width_mm"], member["run_tag"], member["run_key"]))
    if handedness == "left_edge":
        target_edge_m = reference["edge_offsets_m"]["left_edge_m"]
        member_offsets = [
            _suggested_member_offset(member, handedness, target_edge_m - (member["width_mm"] / 2000.0))
            for member in alignment_members
        ]
    elif handedness == "right_edge":
        target_edge_m = reference["edge_offsets_m"]["right_edge_m"]
        member_offsets = [
            _suggested_member_offset(member, handedness, target_edge_m + (member["width_mm"] / 2000.0))
            for member in alignment_members
        ]
    else:
        target_edge_m = 0.0
        member_offsets = [
            _suggested_member_offset(member, handedness, 0.0)
            for member in alignment_members
        ]
    return {
        "handedness": handedness,
        "reference_run_key": reference["run_key"],
        "reference_run_tag": reference["run_tag"],
        "target_edge_m": target_edge_m,
        "member_offsets": member_offsets,
        "max_delta_m": max((abs(member["delta_face_offset_m"]) for member in member_offsets), default=0.0),
    }


def _suggested_member_offset(member, handedness, suggested_face_offset_m):
    current_offset_m = member["current_face_offset_m"]
    return {
        "run_key": member["run_key"],
        "run_tag": member["run_tag"],
        "node_key": member["node_key"],
        "segment_index": member["segment_index"],
        "segment_key": member["segment_key"],
        "width_mm": member["width_mm"],
        "current_face_offset_m": current_offset_m,
        "suggested_face_offset_m": suggested_face_offset_m,
        "delta_face_offset_m": suggested_face_offset_m - current_offset_m,
        "handedness": handedness,
    }


def _spread_m(values):
    values = list(values)
    if not values:
        return 0.0
    return max(values) - min(values)


def _adjacent_segments_for_member(run, node_key):
    nodes = sorted(run.nodes.all(), key=lambda node: (node.sequence, node.pk))
    for index, node in enumerate(nodes):
        if str(node.key) != str(node_key):
            continue
        segments = []
        if index > 0:
            segments.append(_adjacent_segment_payload(run, nodes[index - 1], node, index, "incoming_to_node"))
        if index < len(nodes) - 1:
            segments.append(_adjacent_segment_payload(run, node, nodes[index + 1], index + 1, "outgoing_from_node"))
        return segments
    return []


def _adjacent_segment_payload(run, start_node, end_node, segment_index, role_at_node):
    face_offset_m = _segment_face_offset_m(run, str(start_node.key), str(end_node.key))
    return {
        "segment_index": segment_index,
        "segment_key": f"{start_node.key}::{end_node.key}",
        "start_node_key": str(start_node.key),
        "end_node_key": str(end_node.key),
        "role_at_node": role_at_node,
        "face_offset_m": face_offset_m,
        "edge_offsets_m": _edge_offsets_m(run.size.width_mm, face_offset_m),
    }


def _segment_face_offset_m(run, start_node_key, end_node_key):
    metadata = run.metadata if isinstance(run.metadata, dict) else {}
    payload = metadata.get("segment_face_offset")
    if not isinstance(payload, dict):
        return 0.0
    overrides = payload.get("overrides", [])
    if not isinstance(overrides, list):
        return 0.0
    for override in overrides:
        if (
            str(override.get("start_node_key") or "") == str(start_node_key)
            and str(override.get("end_node_key") or "") == str(end_node_key)
        ):
            try:
                value = float(override.get("face_offset_m") or 0.0)
            except (TypeError, ValueError):
                return 0.0
            return value if math.isfinite(value) else 0.0
    return 0.0


def _edge_offsets_m(width_mm, face_offset_m):
    half_width_m = max(float(width_mm or 0.0) / 1000.0, 0.0) / 2.0
    offset_m = float(face_offset_m or 0.0)
    return {
        "left_edge_m": offset_m + half_width_m,
        "right_edge_m": offset_m - half_width_m,
        "centerline_offset_m": offset_m,
    }


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
            "code": "raceway.fittings.synthetic_proxy_defaults",
            "schema": ACCESSORY_PROXY_SCHEMA,
            "default_bend_radius_m": ACCESSORY_DEFAULT_BEND_RADIUS_M,
            "curve_segments": ACCESSORY_PROXY_CURVE_SEGMENTS,
            "message": (
                "Synthetic accessory proxies use project-neutral defaults until a project preference or vendor "
                "catalogue overrides bend/riser radius and development dimensions."
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
                "Reducer, riser, and offset-step placeholders are marked where tray faces must be aligned. "
                "Segment face offsets may be stored, but explicit reducer/riser handedness and accessory geometry "
                "are still projection-only."
            ),
        },
        {
            "code": "raceway.fittings.reducer_one_edge_matching",
            "default_handedness": REDUCER_DEFAULT_HANDEDNESS,
            "options": list(REDUCER_HANDEDNESS_OPTIONS),
            "message": (
                "Reducer/expander candidates default to one-edge matching. Left/right are relative to each "
                "adjacent segment's saved node order; centerline matching is retained as an uncommon explicit option."
            ),
        },
        {
            "code": "raceway.fittings.tee_cross_deferred",
            "message": (
                "Tee/cross graph-node proxies are derived where explicit connected topology exists. Catalogue "
                "selection, main/branch choice, and special branch-size fittings remain deferred."
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
