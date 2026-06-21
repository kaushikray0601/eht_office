UNIT_SCALE_TO_M = {
    "M": 1.0,
    "METRE": 1.0,
    "METER": 1.0,
    "MM": 0.001,
    "MILLIMETRE": 0.001,
    "MILLIMETER": 0.001,
    "CM": 0.01,
    "CENTIMETRE": 0.01,
    "CENTIMETER": 0.01,
    "IN": 0.0254,
    "INCH": 0.0254,
    "INCHES": 0.0254,
    "FT": 0.3048,
    "FOOT": 0.3048,
    "FEET": 0.3048,
}


def normalize_unit(unit, default="MM"):
    value = str(unit or default).strip().upper()
    return value or default


def coordinate_unit_stats(source_format, unit=None, confidence="assumed"):
    source_unit = normalize_unit(unit, default="M" if source_format == "IFC" else "MM")
    scale = UNIT_SCALE_TO_M.get(source_unit)
    if scale is None:
        source_unit = "M" if source_format == "IFC" else "MM"
        scale = UNIT_SCALE_TO_M[source_unit]
        confidence = "fallback"

    return {
        "coordinate_unit": source_unit,
        "coordinate_scale_to_m": scale,
        "display_unit": "m",
        "unit_confidence": confidence,
    }
