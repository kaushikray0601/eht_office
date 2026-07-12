from dataclasses import dataclass, field

from .geometry import (
    MIN_SEGMENT_LENGTH_M,
    PLAN_BEND_COSINE_LIMIT,
    distance,
    interpolate,
    is_plan_bend,
    point_from_node,
    point_to_segment_distance,
)
from .models import RacewayLayer, RacewayRun


GRAPH_NODE_TOLERANCE_M = 0.01
NEAR_MISS_ENDPOINT_RADIUS_M = 0.25
RISER_ELEVATION_DELTA_M = 0.001


@dataclass
class GraphMember:
    run_id: int
    run_key: str
    run_tag: str
    node_id: int
    node_key: str
    sequence: int
    persisted_kind: str
    derived_kind: str
    source_point_m: dict
    anchor: dict = field(default_factory=dict)

    def to_payload(self):
        return {
            "run_id": self.run_id,
            "run_key": self.run_key,
            "run_tag": self.run_tag,
            "node_id": self.node_id,
            "node_key": self.node_key,
            "sequence": self.sequence,
            "persisted_kind": self.persisted_kind,
            "derived_kind": self.derived_kind,
            "source_point_m": self.source_point_m,
            "anchor": self.anchor,
        }


@dataclass
class GraphNode:
    key: str
    source_point_m: dict
    members: list[GraphMember]
    derived_kind: str = "intermediate"
    degree: int = 0

    def to_payload(self):
        anchors = [
            member.anchor
            for member in self.members
            if member.anchor
        ]
        return {
            "key": self.key,
            "derived_kind": self.derived_kind,
            "degree": self.degree,
            "source_point_m": self.source_point_m,
            "member_count": len(self.members),
            "run_ids": sorted({member.run_id for member in self.members}),
            "anchors": anchors,
            "members": [member.to_payload() for member in self.members],
        }


@dataclass
class GraphEdge:
    key: str
    run_id: int
    run_key: str
    run_tag: str
    start_node_key: str
    end_node_key: str
    start_sequence: int
    end_sequence: int
    start_point_m: dict
    end_point_m: dict
    length_m: float
    dz_m: float
    is_riser: bool

    def to_payload(self):
        return {
            "key": self.key,
            "run_id": self.run_id,
            "run_key": self.run_key,
            "run_tag": self.run_tag,
            "start_node_key": self.start_node_key,
            "end_node_key": self.end_node_key,
            "start_sequence": self.start_sequence,
            "end_sequence": self.end_sequence,
            "start_point_m": self.start_point_m,
            "end_point_m": self.end_point_m,
            "length_m": self.length_m,
            "dz_m": self.dz_m,
            "is_riser": self.is_riser,
        }


@dataclass
class RacewayGraph:
    tolerance_m: float
    near_miss_endpoint_radius_m: float = NEAR_MISS_ENDPOINT_RADIUS_M
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)

    def to_payload(self):
        return {
            "tolerance_m": self.tolerance_m,
            "near_miss_endpoint_radius_m": self.near_miss_endpoint_radius_m,
            "nodes": [node.to_payload() for node in self.nodes],
            "edges": [edge.to_payload() for edge in self.edges],
            "warnings": self.warnings,
        }


def build_layer_graph(layer, *, tolerance_m=GRAPH_NODE_TOLERANCE_M):
    layer_id = layer.pk if isinstance(layer, RacewayLayer) else int(layer)
    runs = (
        RacewayRun.objects
        .select_related("layer")
        .prefetch_related("nodes")
        .filter(layer_id=layer_id)
        .order_by("tag", "pk")
    )
    return build_graph_for_runs(runs, tolerance_m=tolerance_m)


def build_project_graph(project_id, *, tolerance_m=GRAPH_NODE_TOLERANCE_M):
    runs = (
        RacewayRun.objects
        .select_related("layer")
        .prefetch_related("nodes")
        .filter(layer__project_id=project_id)
        .order_by("layer_id", "tag", "pk")
    )
    return build_graph_for_runs(runs, tolerance_m=tolerance_m)


def build_graph_for_runs(
    runs,
    *,
    tolerance_m=GRAPH_NODE_TOLERANCE_M,
    near_miss_radius_m=NEAR_MISS_ENDPOINT_RADIUS_M,
):
    prepared_runs = list(runs)
    run_members = {}
    members = []
    for run in prepared_runs:
        ordered_nodes = sorted(run.nodes.all(), key=lambda node: (node.sequence, node.pk))
        run_members[run.pk] = [
            _member_from_node(run, node, ordered_nodes, index)
            for index, node in enumerate(ordered_nodes)
        ]
        members.extend(run_members[run.pk])

    if not members:
        return RacewayGraph(tolerance_m=tolerance_m, near_miss_endpoint_radius_m=near_miss_radius_m)

    member_to_graph_key = {}
    graph_nodes = _cluster_members(members, member_to_graph_key, tolerance_m)
    graph_edges, warnings = _build_edges(prepared_runs, run_members, member_to_graph_key, tolerance_m)
    _apply_degrees_and_kinds(graph_nodes, graph_edges)
    warnings.extend(_unconnected_crossing_warnings(graph_nodes, graph_edges, tolerance_m))
    warnings.extend(_endpoint_near_miss_warnings(graph_nodes, graph_edges, tolerance_m, near_miss_radius_m))
    return RacewayGraph(
        tolerance_m=tolerance_m,
        near_miss_endpoint_radius_m=near_miss_radius_m,
        nodes=graph_nodes,
        edges=graph_edges,
        warnings=sorted(
            warnings,
            key=lambda item: (
                item["code"],
                item.get("endpoint_node_key", ""),
                item.get("edge_keys", []),
                item.get("node_key", ""),
            ),
        ),
    )


def _member_from_node(run, node, ordered_nodes, index):
    return GraphMember(
        run_id=run.pk,
        run_key=str(run.key),
        run_tag=run.tag or str(run.key),
        node_id=node.pk,
        node_key=str(node.key),
        sequence=node.sequence,
        persisted_kind=node.node_kind,
        derived_kind=_derived_node_kind(ordered_nodes, index),
        source_point_m=point_from_node(node),
        anchor=dict(node.anchor or {}),
    )


def _derived_node_kind(nodes, index):
    if index <= 0 or index >= len(nodes) - 1:
        return "endpoint"
    previous_node = nodes[index - 1]
    node = nodes[index]
    next_node = nodes[index + 1]
    if (
        abs(float(node.source_z_m) - float(previous_node.source_z_m)) > RISER_ELEVATION_DELTA_M
        or abs(float(next_node.source_z_m) - float(node.source_z_m)) > RISER_ELEVATION_DELTA_M
    ):
        return "riser"
    if is_plan_bend(previous_node, node, next_node):
        return "bend"
    return "intermediate"


def _cluster_members(members, member_to_graph_key, tolerance_m):
    parent = list(range(len(members)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left_index, left_member in enumerate(members):
        for right_index in range(left_index + 1, len(members)):
            if distance(left_member.source_point_m, members[right_index].source_point_m) <= tolerance_m:
                union(left_index, right_index)

    clusters = {}
    for index, member in enumerate(members):
        clusters.setdefault(find(index), []).append(member)

    cluster_records = []
    for cluster_members in clusters.values():
        sorted_members = sorted(
            cluster_members,
            key=lambda member: (member.run_tag, member.run_id, member.sequence, member.node_id),
        )
        source_point = _average_point([member.source_point_m for member in sorted_members])
        cluster_records.append((source_point, sorted_members))

    cluster_records.sort(
        key=lambda record: (
            round(record[0]["x"], 6),
            round(record[0]["y"], 6),
            round(record[0]["z"], 6),
            record[1][0].run_id,
            record[1][0].sequence,
            record[1][0].node_id,
        )
    )

    graph_nodes = []
    for index, (source_point, cluster_members) in enumerate(cluster_records, start=1):
        key = f"N{index:03d}"
        for member in cluster_members:
            member_to_graph_key[member.node_id] = key
        graph_nodes.append(GraphNode(key=key, source_point_m=source_point, members=cluster_members))
    return graph_nodes


def _average_point(points):
    count = len(points)
    return {
        "x": sum(point["x"] for point in points) / count,
        "y": sum(point["y"] for point in points) / count,
        "z": sum(point["z"] for point in points) / count,
    }


def _build_edges(runs, run_members, member_to_graph_key, tolerance_m):
    edges = []
    warnings = []
    for run in runs:
        members = run_members.get(run.pk, [])
        for index in range(1, len(members)):
            start_member = members[index - 1]
            end_member = members[index]
            start_key = member_to_graph_key[start_member.node_id]
            end_key = member_to_graph_key[end_member.node_id]
            if start_key == end_key:
                warnings.append(
                    {
                        "code": "raceway.graph.zero_length_segment",
                        "severity": "warning",
                        "message": "Segment endpoints collapse within graph tolerance.",
                        "run_id": run.pk,
                        "node_key": start_key,
                        "tolerance_m": tolerance_m,
                    }
                )
                continue
            dz = end_member.source_point_m["z"] - start_member.source_point_m["z"]
            edges.append(
                GraphEdge(
                    key=f"E{len(edges) + 1:003d}",
                    run_id=run.pk,
                    run_key=str(run.key),
                    run_tag=run.tag or str(run.key),
                    start_node_key=start_key,
                    end_node_key=end_key,
                    start_sequence=start_member.sequence,
                    end_sequence=end_member.sequence,
                    start_point_m=start_member.source_point_m,
                    end_point_m=end_member.source_point_m,
                    length_m=distance(start_member.source_point_m, end_member.source_point_m),
                    dz_m=dz,
                    is_riser=abs(dz) > RISER_ELEVATION_DELTA_M,
                )
            )
    return edges, warnings


def _apply_degrees_and_kinds(graph_nodes, graph_edges):
    degree_by_key = {node.key: 0 for node in graph_nodes}
    for edge in graph_edges:
        degree_by_key[edge.start_node_key] += 1
        degree_by_key[edge.end_node_key] += 1
    for node in graph_nodes:
        node.degree = degree_by_key[node.key]
        node.derived_kind = _cluster_kind(node)


def _cluster_kind(node):
    distinct_runs = {member.run_id for member in node.members}
    member_kinds = {member.derived_kind for member in node.members}
    if node.degree >= 3:
        return "branch"
    if len(distinct_runs) > 1:
        return "junction"
    if "riser" in member_kinds:
        return "riser"
    if node.degree <= 1:
        return "endpoint"
    if "bend" in member_kinds:
        return "bend"
    return "intermediate"


def _unconnected_crossing_warnings(graph_nodes, graph_edges, tolerance_m):
    warnings = []
    for left_index, left_edge in enumerate(graph_edges):
        for right_edge in graph_edges[left_index + 1:]:
            if left_edge.run_id == right_edge.run_id:
                continue
            if {left_edge.start_node_key, left_edge.end_node_key} & {right_edge.start_node_key, right_edge.end_node_key}:
                continue
            intersection = _plan_intersection(left_edge, right_edge)
            if intersection is None:
                continue
            x, y, left_t, right_t = intersection
            left_z = interpolate(left_edge.start_point_m["z"], left_edge.end_point_m["z"], left_t)
            right_z = interpolate(right_edge.start_point_m["z"], right_edge.end_point_m["z"], right_t)
            if abs(left_z - right_z) > tolerance_m:
                continue
            source_point = {"x": x, "y": y, "z": (left_z + right_z) / 2}
            if _point_matches_graph_node(graph_nodes, source_point, tolerance_m):
                continue
            warnings.append(
                {
                    "code": "raceway.graph.unconnected_crossing",
                    "severity": "warning",
                    "message": "Raceway segments cross at the same elevation but are not connected by a graph node.",
                    "edge_keys": [left_edge.key, right_edge.key],
                    "run_ids": sorted([left_edge.run_id, right_edge.run_id]),
                    "source_point_m": source_point,
                    "tolerance_m": tolerance_m,
                }
            )
    return warnings


def _endpoint_near_miss_warnings(graph_nodes, graph_edges, tolerance_m, near_miss_radius_m):
    warnings = []
    for node in graph_nodes:
        distinct_runs = {member.run_id for member in node.members}
        if len(distinct_runs) > 1:
            continue
        endpoint_members = [member for member in node.members if member.derived_kind == "endpoint"]
        if not endpoint_members:
            continue
        endpoint_member = sorted(endpoint_members, key=lambda member: (member.run_tag, member.sequence, member.node_id))[0]
        candidate = _closest_near_miss_candidate(
            node,
            endpoint_member,
            graph_nodes,
            graph_edges,
            tolerance_m,
            near_miss_radius_m,
        )
        if not candidate:
            continue
        warnings.append(
            {
                "code": "raceway.graph.near_miss_endpoint",
                "severity": "warning",
                "message": "Raceway endpoint is close to another raceway node or segment but is not connected.",
                "endpoint_node_key": endpoint_member.node_key,
                "endpoint_graph_key": node.key,
                "endpoint_run_id": endpoint_member.run_id,
                "endpoint_run_key": endpoint_member.run_key,
                "endpoint_run_tag": endpoint_member.run_tag,
                "endpoint_sequence": endpoint_member.sequence,
                "target_kind": candidate["target_kind"],
                "target_graph_key": candidate.get("target_graph_key", ""),
                "target_edge_key": candidate.get("target_edge_key", ""),
                "target_run_id": candidate["target_run_id"],
                "target_run_key": candidate["target_run_key"],
                "target_run_tag": candidate["target_run_tag"],
                "run_ids": sorted({endpoint_member.run_id, candidate["target_run_id"]}),
                "source_point_m": node.source_point_m,
                "target_point_m": candidate["target_point_m"],
                "distance_m": candidate["distance_m"],
                "tolerance_m": tolerance_m,
                "near_miss_radius_m": near_miss_radius_m,
            }
        )
    return warnings


def _closest_near_miss_candidate(node, endpoint_member, graph_nodes, graph_edges, tolerance_m, near_miss_radius_m):
    candidates = []
    for target_node in graph_nodes:
        if target_node.key == node.key:
            continue
        target_member = _first_member_from_other_run(target_node.members, endpoint_member.run_id)
        if not target_member:
            continue
        gap = distance(node.source_point_m, target_node.source_point_m)
        if tolerance_m < gap <= near_miss_radius_m:
            candidates.append(
                {
                    "target_kind": "node",
                    "target_graph_key": target_node.key,
                    "target_run_id": target_member.run_id,
                    "target_run_key": target_member.run_key,
                    "target_run_tag": target_member.run_tag,
                    "target_point_m": target_node.source_point_m,
                    "distance_m": gap,
                }
            )
    for edge in graph_edges:
        if edge.run_id == endpoint_member.run_id:
            continue
        gap, target_point = point_to_segment_distance(node.source_point_m, edge.start_point_m, edge.end_point_m)
        if tolerance_m < gap <= near_miss_radius_m:
            candidates.append(
                {
                    "target_kind": "edge",
                    "target_edge_key": edge.key,
                    "target_run_id": edge.run_id,
                    "target_run_key": edge.run_key,
                    "target_run_tag": edge.run_tag,
                    "target_point_m": target_point,
                    "distance_m": gap,
                }
            )
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            round(item["distance_m"], 6),
            0 if item["target_kind"] == "node" else 1,
            item["target_run_tag"],
            item.get("target_graph_key", item.get("target_edge_key", "")),
        ),
    )[0]


def _first_member_from_other_run(members, run_id):
    candidates = [member for member in members if member.run_id != run_id]
    if not candidates:
        return None
    return sorted(candidates, key=lambda member: (member.run_tag, member.sequence, member.node_id))[0]


def _plan_intersection(left_edge, right_edge):
    left_start = left_edge.start_point_m
    left_end = left_edge.end_point_m
    right_start = right_edge.start_point_m
    right_end = right_edge.end_point_m
    left_dx = left_end["x"] - left_start["x"]
    left_dy = left_end["y"] - left_start["y"]
    right_dx = right_end["x"] - right_start["x"]
    right_dy = right_end["y"] - right_start["y"]
    denominator = (left_dx * right_dy) - (left_dy * right_dx)
    if abs(denominator) < MIN_SEGMENT_LENGTH_M:
        return None
    delta_x = right_start["x"] - left_start["x"]
    delta_y = right_start["y"] - left_start["y"]
    left_t = ((delta_x * right_dy) - (delta_y * right_dx)) / denominator
    right_t = ((delta_x * left_dy) - (delta_y * left_dx)) / denominator
    if not (0 < left_t < 1 and 0 < right_t < 1):
        return None
    return (
        interpolate(left_start["x"], left_end["x"], left_t),
        interpolate(left_start["y"], left_end["y"], left_t),
        left_t,
        right_t,
    )


def _point_matches_graph_node(graph_nodes, point, tolerance_m):
    return any(distance(node.source_point_m, point) <= tolerance_m for node in graph_nodes)
