import re
from copy import deepcopy
from textwrap import dedent

from .parser import _filter_scene, derive_material_properties


COMPONENT_TYPES = {
    "PIPE",
    "FLANGE",
    "GASKET",
    "BOLT",
    "WELD",
    "ELBOW",
    "TEE",
    "SUPPORT",
    "FLOW-ARROW",
    "END-CONNECTION-EQUIPMENT",
    "END-CONNECTION-PIPELINE",
}

PIPE_TYPES = {"PIPE"}
FITTING_TYPES = {"FLANGE", "GASKET", "ELBOW", "TEE"}
WELD_TYPES = {"WELD"}
SUPPORT_TYPES = {"SUPPORT"}
MARKER_TYPES = {"BOLT", "FLOW-ARROW", "END-CONNECTION-EQUIPMENT", "END-CONNECTION-PIPELINE"}

PCF_RECORD_IDS = {
    "PIPE": 100,
    "FLANGE": 105,
    "GASKET": 110,
    "BOLT": 115,
    "WELD": 120,
    "ELBOW": 35,
    "TEE": 45,
    "SUPPORT": 150,
    "FLOW-ARROW": 149,
    "END-CONNECTION-EQUIPMENT": 149,
    "END-CONNECTION-PIPELINE": 149,
}


def _clean_line(line: str) -> str:
    return line.replace("\x00", "").lstrip("\ufeff").rstrip()


def _is_indented(line: str) -> bool:
    return bool(line) and line[0].isspace()


def _split_key_value(line: str):
    parts = line.strip().split(None, 1)
    key = parts[0].strip()
    value = parts[1].strip() if len(parts) > 1 else ""
    return key, value


def _set_attr(attrs: dict, key: str, value: str):
    if key in attrs:
        if not isinstance(attrs[key], list):
            attrs[key] = [attrs[key]]
        attrs[key].append(value)
    else:
        attrs[key] = value


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _kind_name(component_type: str) -> str:
    return component_type.replace("-", " ").title()


def _parse_coord_value(value: str):
    tokens = value.split()
    if len(tokens) < 3:
        return {"point": None, "bore": None, "end_type": ""}

    try:
        point = [float(tokens[0]), float(tokens[1]), float(tokens[2])]
    except ValueError:
        return {"point": None, "bore": None, "end_type": ""}

    idx = 3
    bore = None
    if len(tokens) > idx:
        try:
            bore = float(tokens[idx])
            idx += 1
        except ValueError:
            bore = None

    end_type = " ".join(tokens[idx:]).strip() if len(tokens) > idx else ""
    return {"point": point, "bore": bore, "end_type": end_type}


def _pick(comp: dict, key: str, file_meta: dict, default=""):
    value = comp.get(key, "")
    if isinstance(value, list):
        value = " | ".join(str(v) for v in value)
    if value not in ("", None):
        return value

    value = file_meta.get(key, default)
    if isinstance(value, list):
        value = " | ".join(str(v) for v in value)
    return value


def _flag_on(comp: dict, key: str, file_meta: dict):
    comp_val = str(comp.get(key, "")).strip().upper()
    if comp_val == "ON":
        return True
    file_val = str(file_meta.get(key, "")).strip().upper()
    return file_val == "ON"


def _parse_pipeline_block(lines, i):
    key, value = _split_key_value(lines[i])
    file_meta = {key: value}
    i += 1

    while i < len(lines) and _is_indented(lines[i]):
        sub_key, sub_value = _split_key_value(lines[i])
        _set_attr(file_meta, sub_key, sub_value)
        i += 1

    return file_meta, i


def _parse_component_block(lines, i):
    comp_type = lines[i].strip()
    comp = {"TYPE": comp_type}
    i += 1

    while i < len(lines) and _is_indented(lines[i]):
        key, value = _split_key_value(lines[i])
        _set_attr(comp, key, value)
        i += 1

    return comp, i


def _parse_materials_section(lines, i):
    materials = {}
    i += 1

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        if _is_indented(line):
            i += 1
            continue

        key, value = _split_key_value(line)
        if key != "MATERIAL-IDENTIFIER":
            break

        material_id = value.strip()
        material = {"MATERIAL-IDENTIFIER": material_id}
        i += 1

        while i < len(lines) and _is_indented(lines[i]):
            mk, mv = _split_key_value(lines[i])
            _set_attr(material, mk, mv)
            i += 1

        materials[material_id] = material

    return materials, i


def _parse_document(text: str):
    lines = [_clean_line(line) for line in dedent(text).splitlines()]
    lines = [line for line in lines if line.strip()]

    file_meta = {}
    components = []
    materials = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_indented(line):
            i += 1
            continue

        stripped = line.strip()
        key, value = _split_key_value(stripped)

        if stripped == "MATERIALS":
            parsed_materials, i = _parse_materials_section(lines, i)
            materials.update(parsed_materials)
            continue

        if key == "PIPELINE-REFERENCE":
            pipeline_meta, i = _parse_pipeline_block(lines, i)
            file_meta.update(pipeline_meta)
            continue

        if stripped in COMPONENT_TYPES:
            component, i = _parse_component_block(lines, i)
            components.append(component)
            continue

        _set_attr(file_meta, key, value)
        i += 1

    return file_meta, components, materials


def _kind_for_component(comp_type: str, comp: dict):
    if comp_type == "FLOW-ARROW":
        return "Flow Arrow"
    if comp_type == "END-CONNECTION-EQUIPMENT":
        return "End Connection Equipment"
    if comp_type == "END-CONNECTION-PIPELINE":
        return "End Connection Pipeline"
    return _kind_name(comp_type)


def _component_ref(comp: dict, material: dict):
    return (
        str(comp.get("CONNECTION-REFERENCE", "")).strip()
        or str(comp.get("NAME", "")).strip()
        or str(material.get("ITEM-CODE", "")).strip()
        or str(comp.get("COMPONENT-IDENTIFIER", "")).strip()
    )


def _build_properties(comp: dict, file_meta: dict, material: dict, filename: str):
    material_id = str(comp.get("MATERIAL-IDENTIFIER", "")).strip()
    item_code = str(material.get("ITEM-CODE", "")).strip()
    description = str(material.get("DESCRIPTION", "")).strip()

    end_points = [_parse_coord_value(v) for v in _as_list(comp.get("END-POINT"))]
    end_points = [entry for entry in end_points if entry.get("point")]
    branch1 = _parse_coord_value(comp.get("BRANCH1-POINT", "")) if comp.get("BRANCH1-POINT") else None
    centre = _parse_coord_value(comp.get("CENTRE-POINT", "")) if comp.get("CENTRE-POINT") else None
    coords = _parse_coord_value(comp.get("CO-ORDS", "")) if comp.get("CO-ORDS") else None

    material_rows = []
    if item_code or description:
        material_rows.append({"code": item_code, "description": description})

    support_messages = [msg for msg in _as_list(comp.get("TEXT")) if str(msg).strip()]
    notes = []
    if "CONTINUATION" in comp:
        notes.append("Continuation")
    if comp.get("STATUS"):
        notes.append(str(comp.get("STATUS")).strip())
    if comp.get("MESSAGE") == "" and support_messages:
        notes.extend(support_messages[1:])

    mapped_comp_keys = {
        "TYPE", "COMPONENT-IDENTIFIER", "MASTER-COMPONENT-IDENTIFIER", "UCI", "SKEY",
        "MATERIAL-IDENTIFIER", "END-POINT", "CO-ORDS", "CENTRE-POINT", "BRANCH1-POINT",
        "PIPING-SPEC", "INSULATION-SPEC", "INSULATION", "TRACING", "TRACING-SPEC",
        "PAINTING-SPEC", "MISC-SPEC1", "MISC-SPEC2", "MISC-SPEC3", "WEIGHT",
        "CUT-PIECE-LENGTH", "FABRICATION-ITEM", "ERECTION-ITEM", "SUPPORT-TYPE",
        "SUPPORT-DIRECTION", "NAME", "TEXT", "MESSAGE", "CONNECTION-REFERENCE", "FLOW",
        "STATUS", "MATERIAL-LIST", "REPEAT-WELD-IDENTIFIER", "WELD-REMARK-NUMBER",
    }
    comp_unmapped = {k: deepcopy(v) for k, v in comp.items() if k not in mapped_comp_keys and not k.startswith("WELD-ATTRIBUTE")}

    pipeline_meta = {k: deepcopy(v) for k, v in file_meta.items() if k != "PIPELINE-REFERENCE"}

    properties = {
        "source_format": "PCF",
        "source_record": comp.get("TYPE", ""),
        "record_id": PCF_RECORD_IDS.get(comp.get("TYPE", ""), 9000),
        "kind": _kind_for_component(comp.get("TYPE", ""), comp),
        "filename": filename,
        "inline_code": str(comp.get("SKEY", "")).strip(),
        "pipeline_ref": str(file_meta.get("PIPELINE-REFERENCE", "")).strip(),
        "spool_ref": "",
        "component_ref": _component_ref(comp, material),
        "component_identifier": str(comp.get("COMPONENT-IDENTIFIER", "")).strip(),
        "master_component_identifier": str(comp.get("MASTER-COMPONENT-IDENTIFIER", "")).strip(),
        "uci": str(comp.get("UCI", "")).strip(),
        "materials": material_rows,
        "item_code": item_code,
        "description": description,
        "derived": derive_material_properties(material_rows),
        "piping_spec": _pick(comp, "PIPING-SPEC", file_meta),
        "insulation_spec": _pick(comp, "INSULATION-SPEC", file_meta),
        "insulation_on": _flag_on(comp, "INSULATION", file_meta),
        "tracing_spec": _pick(comp, "TRACING-SPEC", file_meta),
        "tracing_on": _flag_on(comp, "TRACING", file_meta),
        "painting_spec": _pick(comp, "PAINTING-SPEC", file_meta),
        "misc_spec1": _pick(comp, "MISC-SPEC1", file_meta),
        "misc_spec2": _pick(comp, "MISC-SPEC2", file_meta),
        "misc_spec3": _pick(comp, "MISC-SPEC3", file_meta),
        "weight": str(comp.get("WEIGHT", "")).strip(),
        "cut_piece_length": str(comp.get("CUT-PIECE-LENGTH", "")).strip(),
        "fabrication_item": "FABRICATION-ITEM" in comp,
        "erection_item": "ERECTION-ITEM" in comp,
        "support_type": str(comp.get("SUPPORT-TYPE", "")).strip(),
        "support_direction": str(comp.get("SUPPORT-DIRECTION", "")).strip(),
        "support_name": str(comp.get("NAME", "")).strip(),
        "support_code": " | ".join(support_messages),
        "messages": support_messages,
        "connection_reference": str(comp.get("CONNECTION-REFERENCE", "")).strip(),
        "flow_value": str(comp.get("FLOW", "")).strip(),
        "status": str(comp.get("STATUS", "")).strip(),
        "material_list": str(comp.get("MATERIAL-LIST", "")).strip(),
        "end_bores": [entry.get("bore") for entry in end_points if entry.get("bore") is not None],
        "end_types": [entry.get("end_type") for entry in end_points if entry.get("end_type")],
        "branch_bore": branch1.get("bore") if branch1 and branch1.get("bore") is not None else "",
        "branch_end_type": branch1.get("end_type") if branch1 and branch1.get("end_type") else "",
        "notes": notes,
        "pipeline_metadata": pipeline_meta,
        "unmapped_meta": {
            "component": comp_unmapped,
            "weld_attributes": {
                key: deepcopy(comp.get(key, ""))
                for key in comp.keys()
                if key.startswith("WELD-ATTRIBUTE")
            },
        },
    }

    if coords and coords.get("point"):
        properties["raw_point"] = coords["point"]
        if coords.get("bore") is not None:
            properties["coord_bore"] = coords["bore"]
        if coords.get("end_type"):
            properties["coord_end_type"] = coords["end_type"]

    if centre and centre.get("point"):
        properties["centre_point"] = centre["point"]

    if branch1 and branch1.get("point"):
        properties["branch1_point"] = branch1["point"]

    if len(end_points) >= 1 and end_points[0].get("point"):
        properties["raw_start"] = end_points[0]["point"]
    if len(end_points) >= 2 and end_points[1].get("point"):
        properties["raw_end"] = end_points[1]["point"]

    return properties


def _make_segment(uid, comp_type, start, end, properties):
    item_properties = deepcopy(properties)
    item_properties["uid"] = uid
    item_properties["record_id"] = PCF_RECORD_IDS.get(comp_type, 9000)
    return {
        "uid": uid,
        "record_id": PCF_RECORD_IDS.get(comp_type, 9000),
        "kind": item_properties["kind"],
        "inline_code": item_properties.get("inline_code", ""),
        "start_raw": start,
        "end_raw": end,
        "properties": item_properties,
    }


def _make_point(uid, comp_type, point, properties):
    item_properties = deepcopy(properties)
    item_properties["uid"] = uid
    item_properties["record_id"] = PCF_RECORD_IDS.get(comp_type, 9000)
    return {
        "uid": uid,
        "record_id": PCF_RECORD_IDS.get(comp_type, 9000),
        "kind": item_properties["kind"],
        "inline_code": item_properties.get("inline_code", ""),
        "point_raw": point,
        "properties": item_properties,
    }


def _component_to_scene_items(uid_start: int, comp: dict, file_meta: dict, materials: dict, filename: str):
    items = []
    comp_type = comp.get("TYPE", "")
    material_id = str(comp.get("MATERIAL-IDENTIFIER", "")).strip()
    material = deepcopy(materials.get(material_id, {}))
    props = _build_properties(comp, file_meta, material, filename)

    end_points = [_parse_coord_value(v) for v in _as_list(comp.get("END-POINT"))]
    end_points = [entry for entry in end_points if entry.get("point")]
    coords = _parse_coord_value(comp.get("CO-ORDS", "")) if comp.get("CO-ORDS") else None
    centre = _parse_coord_value(comp.get("CENTRE-POINT", "")) if comp.get("CENTRE-POINT") else None
    branch1 = _parse_coord_value(comp.get("BRANCH1-POINT", "")) if comp.get("BRANCH1-POINT") else None

    uid = uid_start

    if comp_type in PIPE_TYPES and len(end_points) >= 2:
        items.append(("pipes", _make_segment(uid, comp_type, end_points[0]["point"], end_points[1]["point"], props)))
        uid += 1

    elif comp_type in {"FLANGE", "GASKET", "ELBOW"} and len(end_points) >= 2:
        items.append(("fittings", _make_segment(uid, comp_type, end_points[0]["point"], end_points[1]["point"], props)))
        uid += 1

    elif comp_type == "TEE":
        if len(end_points) >= 2:
            main_props = deepcopy(props)
            main_props["geometry_role"] = "main_run"
            items.append(("fittings", _make_segment(uid, comp_type, end_points[0]["point"], end_points[1]["point"], main_props)))
            uid += 1
        if centre and centre.get("point") and branch1 and branch1.get("point"):
            branch_props = deepcopy(props)
            branch_props["geometry_role"] = "branch"
            items.append(("fittings", _make_segment(uid, comp_type, centre["point"], branch1["point"], branch_props)))
            uid += 1

    elif comp_type in WELD_TYPES:
        point = end_points[0]["point"] if end_points else (coords["point"] if coords and coords.get("point") else None)
        if point:
            items.append(("welds", _make_point(uid, comp_type, point, props)))
            uid += 1

    elif comp_type in SUPPORT_TYPES:
        point = coords["point"] if coords and coords.get("point") else None
        if point:
            items.append(("supports", _make_point(uid, comp_type, point, props)))
            uid += 1

    elif comp_type in MARKER_TYPES:
        point = None
        if coords and coords.get("point"):
            point = coords["point"]
        elif end_points:
            point = end_points[0]["point"]
        if point:
            items.append(("markers", _make_point(uid, comp_type, point, props)))
            uid += 1

    return items, uid


def _normalize_scene(scene):
    all_points = []

    for bucket in ("pipes", "fittings"):
        for item in scene[bucket]:
            all_points.append(tuple(item["start_raw"]))
            all_points.append(tuple(item["end_raw"]))

    for bucket in ("welds", "supports", "markers"):
        for item in scene[bucket]:
            all_points.append(tuple(item["point_raw"]))

    if not all_points:
        scene["stats"]["scale_factor"] = 1.0
        scene["stats"]["raw_bounds"] = {}
        return scene

    xs = [point[0] for point in all_points]
    ys = [point[1] for point in all_points]
    zs = [point[2] for point in all_points]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    cz = (min_z + max_z) / 2.0
    scale = 0.001

    def tx(point):
        return [(point[0] - cx) * scale, (point[2] - cz) * scale, (point[1] - cy) * scale]

    for bucket in ("pipes", "fittings"):
        for item in scene[bucket]:
            item["start"] = tx(item["start_raw"])
            item["end"] = tx(item["end_raw"])

    for bucket in ("welds", "supports", "markers"):
        for item in scene[bucket]:
            item["point"] = tx(item["point_raw"])

    scene["stats"].update({
        "scale_factor": scale,
        "raw_bounds": {
            "min_x": min_x, "max_x": max_x,
            "min_y": min_y, "max_y": max_y,
            "min_z": min_z, "max_z": max_z,
        },
    })
    return scene


def _strip_internal(scene):
    for bucket in ("pipes", "fittings"):
        for item in scene[bucket]:
            item.pop("start_raw", None)
            item.pop("end_raw", None)

    for bucket in ("welds", "supports", "markers"):
        for item in scene[bucket]:
            item.pop("point_raw", None)

    return scene


def parse_multiple_pcf_texts(file_payloads, project):
    combined_scene = {
        "pipes": [],
        "fittings": [],
        "welds": [],
        "supports": [],
        "markers": [],
        "stats": {
            "total_lines": 0,
            "source_format": "PCF",
            "source_label": "PCF Scene",
        },
    }

    for filename, text in file_payloads:
        file_meta, components, materials = _parse_document(text)
        combined_scene["stats"]["total_lines"] += len(text.splitlines())

        next_uid = 1
        for component in components:
            scene_items, next_uid = _component_to_scene_items(next_uid, component, file_meta, materials, filename)
            for bucket, scene_item in scene_items:
                combined_scene[bucket].append(scene_item)

    combined_scene = _filter_scene(combined_scene)
    combined_scene["stats"]["source_format"] = "PCF"
    combined_scene["stats"]["source_label"] = "PCF Scene"
    combined_scene = _normalize_scene(combined_scene)

    return _strip_internal(combined_scene)
