import math

from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import ModelObject, RenderTile


SOURCE_COORDINATE_FRAME = "source_xyz_m"

OVERLAY_ANCHOR_ALLOWED_KEYS = frozenset(
    {
        "owner_module",
        "anchor_kind",
        "render_package_id",
        "source_model_id",
        "model_object_id",
        "stable_id",
        "source_object_id",
        "object_type",
        "label",
        "bounds",
        "source_point_m",
    }
)

OVERLAY_ANCHOR_KINDS = frozenset({"model_object", "model_selection_point"})


def _finite_float(value, field_name):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: "Value must be a finite number."})
    if not math.isfinite(number):
        raise ValidationError({field_name: "Value must be a finite number."})
    return number


def _positive_int(value, field_name, *, required=False):
    if value in (None, ""):
        if required:
            raise ValidationError({field_name: "Value is required."})
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: "Value must be a positive integer."})
    if number <= 0:
        raise ValidationError({field_name: "Value must be a positive integer."})
    return number


def _normalize_bounds(bounds):
    if not isinstance(bounds, dict):
        return None
    try:
        if all(key in bounds for key in ("min_x", "max_x", "min_y", "max_y", "min_z", "max_z")):
            return _bounds_from_values(
                bounds["min_x"],
                bounds["max_x"],
                bounds["min_y"],
                bounds["max_y"],
                bounds["min_z"],
                bounds["max_z"],
            )
        if isinstance(bounds.get("min"), (list, tuple)) and isinstance(bounds.get("max"), (list, tuple)):
            if len(bounds["min"]) >= 3 and len(bounds["max"]) >= 3:
                return _bounds_from_values(
                    bounds["min"][0],
                    bounds["max"][0],
                    bounds["min"][1],
                    bounds["max"][1],
                    bounds["min"][2],
                    bounds["max"][2],
                )
        if isinstance(bounds.get("min"), dict) and isinstance(bounds.get("max"), dict):
            return _bounds_from_values(
                bounds["min"]["x"],
                bounds["max"]["x"],
                bounds["min"]["y"],
                bounds["max"]["y"],
                bounds["min"]["z"],
                bounds["max"]["z"],
            )
    except (KeyError, TypeError, ValueError):
        return None
    return None


def _bounds_from_values(min_x, max_x, min_y, max_y, min_z, max_z):
    x_values = sorted([float(min_x), float(max_x)])
    y_values = sorted([float(min_y), float(max_y)])
    z_values = sorted([float(min_z), float(max_z)])
    return {
        "min_x": x_values[0],
        "max_x": x_values[1],
        "min_y": y_values[0],
        "max_y": y_values[1],
        "min_z": z_values[0],
        "max_z": z_values[1],
    }


def _bounds_intersect(left, right):
    left_bounds = _normalize_bounds(left)
    right_bounds = _normalize_bounds(right)
    if left_bounds is None or right_bounds is None:
        return False
    return (
        left_bounds["min_x"] <= right_bounds["max_x"]
        and left_bounds["max_x"] >= right_bounds["min_x"]
        and left_bounds["min_y"] <= right_bounds["max_y"]
        and left_bounds["max_y"] >= right_bounds["min_y"]
        and left_bounds["min_z"] <= right_bounds["max_z"]
        and left_bounds["max_z"] >= right_bounds["min_z"]
    )


def _candidate_tile_ids(render_package_id, bounds_filter):
    if render_package_id is None or bounds_filter is None:
        return None
    tile_ids = []
    for tile in RenderTile.objects.filter(render_package_id=render_package_id).only("id", "bounds"):
        if _bounds_intersect(tile.bounds, bounds_filter):
            tile_ids.append(tile.pk)
    return tile_ids


def model_object_bounds_for_source(source_model_id, *, render_package_id=None, bounds_filter=None, limit=2000):
    source_id = _positive_int(source_model_id, "source_model_id", required=True)
    package_id = _positive_int(render_package_id, "render_package_id") if render_package_id is not None else None
    scan_limit = max(int(limit or 0), 1)
    normalized_filter = _normalize_bounds(bounds_filter)

    queryset = ModelObject.objects.filter(source_model_id=source_id)
    if package_id is not None:
        queryset = queryset.filter(Q(render_package_id=package_id) | Q(render_package_id__isnull=True))
        candidate_tile_ids = _candidate_tile_ids(package_id, normalized_filter)
        if candidate_tile_ids is not None:
            queryset = queryset.filter(Q(render_tile_id__in=candidate_tile_ids) | Q(render_tile_id__isnull=True))

    raw_objects = list(
        queryset.only("stable_id", "source_object_id", "object_type", "tag", "line_id", "bounds")[: scan_limit + 1]
    )
    objects = []
    for model_object in raw_objects[:scan_limit]:
        bounds = _normalize_bounds(model_object.bounds)
        if bounds is None:
            continue
        if normalized_filter is not None and not _bounds_intersect(bounds, normalized_filter):
            continue
        objects.append(
            {
                "stable_id": model_object.stable_id,
                "source_object_id": model_object.source_object_id,
                "object_type": model_object.object_type,
                "tag": model_object.tag,
                "line_id": model_object.line_id,
                "bounds": bounds,
            }
        )
    return {
        "objects": objects,
        "limited": len(raw_objects) > scan_limit,
        "scan_limit": scan_limit,
    }


def _source_point_payload(value):
    if value in (None, ""):
        return None
    if not isinstance(value, dict):
        raise ValidationError({"source_point_m": "Source point must be an object."})
    coordinate_frame = value.get("coordinate_frame", SOURCE_COORDINATE_FRAME)
    if coordinate_frame != SOURCE_COORDINATE_FRAME:
        raise ValidationError({"source_point_m": f"Source point must use {SOURCE_COORDINATE_FRAME}."})
    return {
        "x": _finite_float(value.get("x"), "source_point_m.x"),
        "y": _finite_float(value.get("y"), "source_point_m.y"),
        "z": _finite_float(value.get("z"), "source_point_m.z"),
        "coordinate_frame": SOURCE_COORDINATE_FRAME,
    }


def validate_overlay_anchor(anchor, *, source_model_id=None, owner_module=None):
    if anchor in (None, "", {}):
        return {}
    if not isinstance(anchor, dict):
        raise ValidationError({"anchor": "Anchor must be an object."})

    extra_keys = sorted(set(anchor) - OVERLAY_ANCHOR_ALLOWED_KEYS)
    if extra_keys:
        raise ValidationError({"anchor": f"Anchor contains unsupported key(s): {', '.join(extra_keys)}."})

    anchor_kind = str(anchor.get("anchor_kind") or "").strip()
    if not anchor_kind:
        raise ValidationError({"anchor_kind": "Anchor kind is required."})
    if anchor_kind not in OVERLAY_ANCHOR_KINDS:
        raise ValidationError({"anchor_kind": "Anchor kind is not supported."})

    stable_id = str(anchor.get("stable_id") or "").strip()
    if anchor_kind == "model_object" and not stable_id:
        raise ValidationError({"stable_id": "Model-object anchors require a stable_id."})

    expected_source_model_id = _positive_int(source_model_id, "source_model_id") if source_model_id else None
    anchor_source_model_id = _positive_int(
        anchor.get("source_model_id"),
        "source_model_id",
        required=expected_source_model_id is not None,
    )
    if expected_source_model_id is not None and anchor_source_model_id != expected_source_model_id:
        raise ValidationError({"source_model_id": "Anchor source model does not match the raceway run."})

    owner = str(anchor.get("owner_module") or "").strip()
    if owner_module and owner and owner != owner_module:
        raise ValidationError({"owner_module": f"Anchor owner_module must be {owner_module}."})

    if "bounds" in anchor and anchor.get("bounds") not in (None, "") and not isinstance(anchor.get("bounds"), dict):
        raise ValidationError({"bounds": "Bounds must be an object."})

    normalized = {
        "owner_module": owner_module or owner,
        "anchor_kind": anchor_kind,
        "stable_id": stable_id,
    }
    for key in ("source_object_id", "object_type", "label"):
        value = str(anchor.get(key) or "").strip()
        if value:
            normalized[key] = value
    if anchor_source_model_id is not None:
        normalized["source_model_id"] = anchor_source_model_id
    render_package_id = _positive_int(anchor.get("render_package_id"), "render_package_id")
    if render_package_id is not None:
        normalized["render_package_id"] = render_package_id
    model_object_id = _positive_int(anchor.get("model_object_id"), "model_object_id")
    if model_object_id is not None:
        normalized["model_object_id"] = model_object_id
    if isinstance(anchor.get("bounds"), dict):
        normalized["bounds"] = anchor["bounds"]
    source_point = _source_point_payload(anchor.get("source_point_m"))
    if source_point:
        normalized["source_point_m"] = source_point
    return {key: value for key, value in normalized.items() if value not in (None, "")}
