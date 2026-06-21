EHT_TOOL_DEFINITIONS = {
    "distribution_board": {
        "label": "Distribution Board",
        "geometry_type": "point",
        "color": "#7c3aed",
        "fields": [
            {"key": "tag", "label": "Tag", "type": "text", "max_length": 80},
            {"key": "board_ref", "label": "Board Ref", "type": "text", "max_length": 80},
            {"key": "circuit", "label": "Circuit", "type": "text", "max_length": 80},
            {"key": "voltage", "label": "Voltage", "type": "text", "max_length": 40},
            {"key": "length_m", "label": "Length m", "type": "number", "default": "0.80", "max_length": 40},
            {"key": "width_m", "label": "Width m", "type": "number", "default": "0.25", "max_length": 40},
            {"key": "height_m", "label": "Height m", "type": "number", "default": "1.00", "max_length": 40},
            {"key": "note", "label": "Construction Note", "type": "textarea", "max_length": 1000},
        ],
    },
    "junction_box": {
        "label": "Junction Box",
        "geometry_type": "point",
        "color": "#2563eb",
        "fields": [
            {"key": "tag", "label": "Tag", "type": "text", "max_length": 80},
            {"key": "circuit", "label": "Circuit", "type": "text", "max_length": 80},
            {"key": "source_board", "label": "Source Board", "type": "text", "max_length": 80},
            {"key": "length_m", "label": "Length m", "type": "number", "default": "0.35", "max_length": 40},
            {"key": "width_m", "label": "Width m", "type": "number", "default": "0.16", "max_length": 40},
            {"key": "height_m", "label": "Height m", "type": "number", "default": "0.30", "max_length": 40},
            {"key": "note", "label": "Construction Note", "type": "textarea", "max_length": 1000},
        ],
    },
    "isolator": {
        "label": "Isolator",
        "geometry_type": "point",
        "color": "#0f766e",
        "fields": [
            {"key": "tag", "label": "Tag", "type": "text", "max_length": 80},
            {"key": "circuit", "label": "Circuit", "type": "text", "max_length": 80},
            {"key": "isolator_type", "label": "Isolator Type", "type": "text", "max_length": 80},
            {"key": "note", "label": "Construction Note", "type": "textarea", "max_length": 1000},
        ],
    },
    "tracer_sr": {
        "label": "SR Tracer",
        "geometry_type": "polyline",
        "color": "#f59e0b",
        "fields": [
            {"key": "tag", "label": "Tag", "type": "text", "max_length": 80},
            {"key": "tracer_family", "label": "Tracer Family", "type": "select", "options": ["SR"], "default": "SR"},
            {"key": "tracer_type", "label": "Tracer Type", "type": "text", "max_length": 120},
            {"key": "circuit", "label": "Circuit", "type": "text", "max_length": 80},
            {"key": "watts_per_m", "label": "W/m", "type": "number", "max_length": 40},
            {"key": "note", "label": "Construction Note", "type": "textarea", "max_length": 1000},
        ],
    },
    "tracer_mi": {
        "label": "MI Tracer",
        "geometry_type": "polyline",
        "color": "#ea580c",
        "fields": [
            {"key": "tag", "label": "Tag", "type": "text", "max_length": 80},
            {"key": "tracer_family", "label": "Tracer Family", "type": "select", "options": ["MI"], "default": "MI"},
            {"key": "tracer_type", "label": "Tracer Type", "type": "text", "max_length": 120},
            {"key": "circuit", "label": "Circuit", "type": "text", "max_length": 80},
            {"key": "watts_per_m", "label": "W/m", "type": "number", "max_length": 40},
            {"key": "note", "label": "Construction Note", "type": "textarea", "max_length": 1000},
        ],
    },
    "rtd": {
        "label": "RTD",
        "geometry_type": "point",
        "color": "#dc2626",
        "fields": [
            {"key": "tag", "label": "Tag", "type": "text", "max_length": 80},
            {"key": "circuit", "label": "Circuit", "type": "text", "max_length": 80},
            {"key": "setpoint_c", "label": "Setpoint C", "type": "number", "max_length": 40},
            {"key": "note", "label": "Construction Note", "type": "textarea", "max_length": 1000},
        ],
    },
    "cold_cable": {
        "label": "Cold Cable",
        "geometry_type": "polyline",
        "color": "#0284c7",
        "fields": [
            {"key": "tag", "label": "Tag", "type": "text", "max_length": 80},
            {"key": "from", "label": "From", "type": "text", "max_length": 120},
            {"key": "to", "label": "To", "type": "text", "max_length": 120},
            {"key": "cable_type", "label": "Cable Type", "type": "text", "max_length": 120},
            {"key": "circuit", "label": "Circuit", "type": "text", "max_length": 80},
            {"key": "note", "label": "Construction Note", "type": "textarea", "max_length": 1000},
        ],
    },
    "end_termination": {
        "label": "End Termination",
        "geometry_type": "point",
        "color": "#be123c",
        "fields": [
            {"key": "tag", "label": "Tag", "type": "text", "max_length": 80},
            {"key": "circuit", "label": "Circuit", "type": "text", "max_length": 80},
            {"key": "termination_type", "label": "Termination Type", "type": "text", "max_length": 80},
            {"key": "note", "label": "Construction Note", "type": "textarea", "max_length": 1000},
        ],
    },
    "pipe_strap": {
        "label": "Pipe Strap",
        "geometry_type": "point",
        "color": "#65a30d",
        "fields": [
            {"key": "tag", "label": "Tag", "type": "text", "max_length": 80},
            {"key": "strap_type", "label": "Strap Type", "type": "text", "max_length": 80},
            {"key": "spacing_m", "label": "Spacing m", "type": "number", "max_length": 40},
            {"key": "note", "label": "Construction Note", "type": "textarea", "max_length": 1000},
        ],
    },
}


def _point_distance(a, b):
    return sum((float(a[index]) - float(b[index])) ** 2 for index in range(3)) ** 0.5


def geometry_with_metrics(geometry):
    geometry = dict(geometry or {})
    points = geometry.get("points") or []
    geometry["point_count"] = len(points)
    if geometry.get("type") == "polyline" and len(points) >= 2:
        geometry["length_m"] = round(
            sum(_point_distance(points[index - 1], points[index]) for index in range(1, len(points))),
            4,
        )
        geometry["segment_count"] = len(points) - 1
    else:
        geometry["length_m"] = 0.0
        geometry["segment_count"] = 0
    return geometry


def eht_tool_definition_payload():
    return EHT_TOOL_DEFINITIONS


def metadata_defaults(element_type):
    definition = EHT_TOOL_DEFINITIONS[element_type]
    return {
        field["key"]: str(field.get("default", ""))
        for field in definition["fields"]
    }


def clean_eht_metadata(element_type, metadata):
    definition = EHT_TOOL_DEFINITIONS[element_type]
    fields = {field["key"]: field for field in definition["fields"]}
    cleaned = metadata_defaults(element_type)

    for key, raw_value in (metadata or {}).items():
        key = str(key).strip()
        if not key:
            continue
        value = "" if raw_value is None else str(raw_value).strip()
        field = fields.get(key)
        max_length = int((field or {}).get("max_length", 1000))
        if len(value) > max_length:
            label = (field or {}).get("label", key)
            raise ValueError(f"{label} is too long.")
        if field and field.get("type") == "select":
            options = field.get("options") or []
            if value and value not in options:
                raise ValueError(f"{field['label']} must be one of: {', '.join(options)}.")
        cleaned[key] = value

    return cleaned
