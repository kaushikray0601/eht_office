from collections import defaultdict

from .models import SOURCE_COORDINATE_FRAME, RacewayLayer
from .warnings import build_layer_warnings


CLASH_EDGE_PENALTY_PROJECTION = "raceway.clash_edge_penalties.v0"
MODEL_CLASH_WARNING_CODE = "raceway.warning.model_clash_aabb"
MODEL_CLEARANCE_WARNING_CODE = "raceway.warning.model_clearance_aabb"
MODEL_CLASH_ROUTE_PENALTY_M = 5.0
MODEL_CLEARANCE_ROUTE_PENALTY_M = 1.0


def durable_segment_edge_key(start_node_key, end_node_key):
    start = str(start_node_key or "").strip()
    end = str(end_node_key or "").strip()
    return f"{start}::{end}" if start and end else ""


def build_layer_clash_edge_penalties(layer, *, warnings=None):
    layer_obj = layer if isinstance(layer, RacewayLayer) else RacewayLayer.objects.get(pk=int(layer))
    warning_items = list(warnings) if warnings is not None else build_layer_warnings(layer_obj)
    return build_clash_edge_penalties_from_warnings(
        warning_items,
        project_id=layer_obj.project_id,
        layer_id=layer_obj.pk,
    )


def build_clash_edge_penalties_from_warnings(warnings, *, project_id="", layer_id=None):
    buckets = defaultdict(_empty_edge_bucket)
    unmapped = []
    scan_limited = False

    for warning in warnings or []:
        if not isinstance(warning, dict):
            continue
        code = warning.get("code")
        if code == "raceway.warning.model_clash_scan_limited":
            scan_limited = True
            continue
        if code not in {MODEL_CLASH_WARNING_CODE, MODEL_CLEARANCE_WARNING_CODE}:
            continue
        raw_node_keys = warning.get("node_keys", [])
        if not isinstance(raw_node_keys, (list, tuple)):
            unmapped.append(_unmapped_warning(warning, "invalid_node_keys"))
            continue
        node_keys = [str(key) for key in raw_node_keys if str(key or "").strip()]
        if len(node_keys) != 2:
            unmapped.append(_unmapped_warning(warning, "missing_two_node_keys"))
            continue
        edge_key = durable_segment_edge_key(node_keys[0], node_keys[1])
        bucket = buckets[edge_key]
        bucket["edge_key"] = edge_key
        bucket["reverse_edge_key"] = durable_segment_edge_key(node_keys[1], node_keys[0])
        bucket["node_keys"] = node_keys
        bucket["run_key"] = str(warning.get("run_key") or bucket["run_key"] or "")
        bucket["run_tag"] = str(warning.get("run_tag") or bucket["run_tag"] or "")
        bucket["segment_index"] = warning.get("segment_index", bucket["segment_index"])
        if code == MODEL_CLASH_WARNING_CODE:
            bucket["model_clash_count"] += 1
            bucket["route_penalty_m"] += MODEL_CLASH_ROUTE_PENALTY_M
        else:
            bucket["model_clearance_count"] += 1
            bucket["route_penalty_m"] += MODEL_CLEARANCE_ROUTE_PENALTY_M
        bucket["warning_count"] += 1
        bucket["reasons"].append(_reason_from_warning(warning))

    edges = [_finalize_edge_bucket(bucket) for _, bucket in sorted(buckets.items())]
    clash_count = sum(edge["model_clash_count"] for edge in edges)
    clearance_count = sum(edge["model_clearance_count"] for edge in edges)
    return {
        "projection": CLASH_EDGE_PENALTY_PROJECTION,
        "project_id": project_id,
        "layer_id": layer_id,
        "basis": {
            "source": "existing_raceway_aabb_warnings",
            "method": "aggregate_model_clash_and_clearance_warnings_by_durable_segment_edge",
            "coordinate_frame": SOURCE_COORDINATE_FRAME,
            "edge_key_basis": "ordered_adjacent_node_uuid_pair",
            "route_authority": "soft_cost_hint_not_hard_collision_clearance_authority",
            "model_clash_penalty_m": MODEL_CLASH_ROUTE_PENALTY_M,
            "model_clearance_penalty_m": MODEL_CLEARANCE_ROUTE_PENALTY_M,
        },
        "edges": edges,
        "counts": {
            "edge_count": len(edges),
            "warning_count": clash_count + clearance_count,
            "model_clash_count": clash_count,
            "model_clearance_count": clearance_count,
            "unmapped_warning_count": len(unmapped),
            "scan_limited": scan_limited,
            "route_penalty_m_total": sum(edge["route_penalty_m"] for edge in edges),
        },
        "unmapped_warnings": unmapped,
        "assumptions": [
            {
                "code": "raceway.clash_edge_penalty.soft_cost_hint",
                "message": (
                    "Clash edge penalties are route-cost hints derived from rough AABB warnings. "
                    "They are not final collision clearance approval."
                ),
            },
            {
                "code": "raceway.clash_edge_penalty.durable_edge_key",
                "message": (
                    "Edge keys use ordered adjacent Raceway node UUID pairs, not projection-local graph keys "
                    "such as E001."
                ),
            },
        ],
    }


def _empty_edge_bucket():
    return {
        "edge_key": "",
        "reverse_edge_key": "",
        "node_keys": [],
        "run_key": "",
        "run_tag": "",
        "segment_index": None,
        "warning_count": 0,
        "model_clash_count": 0,
        "model_clearance_count": 0,
        "route_penalty_m": 0.0,
        "reasons": [],
    }


def _finalize_edge_bucket(bucket):
    payload = dict(bucket)
    payload["route_penalty_m"] = round(float(payload["route_penalty_m"]), 6)
    payload["reasons"] = sorted(
        payload["reasons"],
        key=lambda item: (
            item.get("code", ""),
            item.get("object_stable_id", ""),
            item.get("gap_m") if item.get("gap_m") is not None else -1,
        ),
    )
    return payload


def _reason_from_warning(warning):
    values = warning.get("values") if isinstance(warning.get("values"), dict) else {}
    return {
        "code": warning.get("code", ""),
        "message": warning.get("message", ""),
        "source_point_m": warning.get("source_point_m") or {},
        "object_stable_id": values.get("object_stable_id", ""),
        "object_source_object_id": values.get("object_source_object_id", ""),
        "object_type": values.get("object_type", ""),
        "object_label": values.get("object_label", ""),
        "gap_m": values.get("gap_m"),
        "clearance_m": values.get("clearance_m"),
        "raceway_bounds": values.get("raceway_bounds", {}),
        "object_bounds": values.get("object_bounds", {}),
    }


def _unmapped_warning(warning, reason):
    return {
        "code": warning.get("code", ""),
        "message": warning.get("message", ""),
        "reason": reason,
        "run_key": str(warning.get("run_key") or ""),
        "run_tag": str(warning.get("run_tag") or ""),
        "segment_index": warning.get("segment_index"),
    }
