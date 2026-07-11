import math

from django.core.exceptions import ValidationError


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
