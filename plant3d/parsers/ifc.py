import os
import tempfile
from copy import deepcopy
from math import floor

import numpy as np

from .units import coordinate_unit_stats


IFC_RECORD_ID = 9100
IFC_SUPPORTED_EXTENSIONS = (".ifc",)
IFC_DEFAULT_COLOR = [0.45, 0.55, 0.72]
IFC_SI_PREFIX_SCALE_TO_M = {
    "EXA": 1e18,
    "PETA": 1e15,
    "TERA": 1e12,
    "GIGA": 1e9,
    "MEGA": 1e6,
    "KILO": 1e3,
    "HECTO": 1e2,
    "DECA": 1e1,
    "DECI": 1e-1,
    "CENTI": 1e-2,
    "MILLI": 1e-3,
    "MICRO": 1e-6,
    "NANO": 1e-9,
    "PICO": 1e-12,
    "FEMTO": 1e-15,
    "ATTO": 1e-18,
}
IFC_SI_LENGTH_DISPLAY = {
    ("", "METRE"): "m",
    ("MILLI", "METRE"): "mm",
    ("CENTI", "METRE"): "cm",
    ("KILO", "METRE"): "km",
}
IFC_CONVERSION_LENGTH_DISPLAY = {
    "FOOT": "ft",
    "INCH": "in",
}
IFC_DEFAULT_ITERATOR_THREADS = 1
IFC_PARSER_THREADS_SETTING = "PLANT3D_PARSER_THREADS"
IFC_PARSER_THREAD_CAP_SETTING = "PLANT3D_PARSER_THREAD_CAP"
IFC_PARSER_MEMORY_PER_THREAD_MB_SETTING = "PLANT3D_PARSER_MEMORY_PER_THREAD_MB"
IFC_PARSER_MEMORY_RESERVE_MB_SETTING = "PLANT3D_PARSER_MEMORY_RESERVE_MB"
IFC_DEFAULT_PARSER_MEMORY_PER_THREAD_MB = 2048
IFC_DEFAULT_PARSER_MEMORY_RESERVE_MB = 1024
BYTES_PER_MIB = 1024 * 1024


class IFCDependencyError(RuntimeError):
    pass


class IFCParseError(RuntimeError):
    pass


def _ifc_token(value):
    return str(value or "").strip().strip(".").strip("'").upper()


def _ifc_is_a(entity, type_name):
    try:
        return bool(entity.is_a(type_name))
    except TypeError:
        try:
            return entity.is_a() == type_name
        except (AttributeError, TypeError):
            return False
    except AttributeError:
        return False


def _ifc_entity_name(entity):
    try:
        return entity.is_a()
    except (AttributeError, TypeError):
        return entity.__class__.__name__


def _float_measure(value):
    if value is None:
        return None
    wrapped = getattr(value, "wrappedValue", None)
    if wrapped is not None:
        try:
            return float(wrapped)
        except (TypeError, ValueError):
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    try:
        return float(value[0])
    except (IndexError, TypeError, ValueError):
        return None


def _si_length_unit_record(unit):
    unit_type = _ifc_token(getattr(unit, "UnitType", ""))
    name = _ifc_token(getattr(unit, "Name", ""))
    if unit_type != "LENGTHUNIT" or name != "METRE":
        return None

    prefix = _ifc_token(getattr(unit, "Prefix", ""))
    scale = IFC_SI_PREFIX_SCALE_TO_M.get(prefix, 1.0)
    return {
        "entity": _ifc_entity_name(unit),
        "unit_type": unit_type,
        "name": name,
        "prefix": prefix,
        "display_unit": IFC_SI_LENGTH_DISPLAY.get((prefix, name), f"{prefix.lower()} {name.lower()}".strip()),
        "scale_to_m": scale,
        "confidence": "ifc_unit_assignment",
    }


def _conversion_length_unit_record(unit):
    unit_type = _ifc_token(getattr(unit, "UnitType", ""))
    if unit_type != "LENGTHUNIT":
        return None

    conversion_factor = getattr(unit, "ConversionFactor", None)
    value_component = getattr(conversion_factor, "ValueComponent", None)
    factor = _float_measure(value_component)
    if factor is None:
        return None

    unit_component = getattr(conversion_factor, "UnitComponent", None)
    base_record = _si_length_unit_record(unit_component) if unit_component is not None else None
    base_scale = (base_record or {}).get("scale_to_m", 1.0)
    name = str(getattr(unit, "Name", "") or "").strip()
    name_key = _ifc_token(name)
    return {
        "entity": _ifc_entity_name(unit),
        "unit_type": unit_type,
        "name": name,
        "display_unit": IFC_CONVERSION_LENGTH_DISPLAY.get(name_key, name.lower()),
        "scale_to_m": factor * base_scale,
        "conversion_factor": factor,
        "conversion_base_unit": base_record,
        "confidence": "ifc_unit_assignment",
    }


def extract_ifc_length_unit_stats(ifc_file):
    length_units = []
    try:
        assignments = ifc_file.by_type("IfcUnitAssignment")
    except Exception:
        assignments = []

    for assignment in assignments:
        for unit in getattr(assignment, "Units", []) or []:
            record = None
            if _ifc_is_a(unit, "IfcSIUnit"):
                record = _si_length_unit_record(unit)
            elif _ifc_is_a(unit, "IfcConversionBasedUnit"):
                record = _conversion_length_unit_record(unit)
            if record:
                length_units.append(record)

    primary = length_units[0] if length_units else {}
    return {
        "ifc_declared_length_units": length_units[:8],
        "ifc_declared_length_unit": primary.get("display_unit", ""),
        "ifc_declared_length_unit_name": primary.get("name", ""),
        "ifc_declared_length_unit_entity": primary.get("entity", ""),
        "ifc_declared_length_scale_to_m": primary.get("scale_to_m"),
        "ifc_declared_length_confidence": primary.get("confidence", ""),
    }


def _settings_get(settings, name):
    try:
        return settings.get(name)
    except Exception:
        return None


def _django_setting(name, default=None):
    try:
        from django.conf import settings as django_settings

        return getattr(django_settings, name, default)
    except Exception:
        return default


def _positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _cpu_count_from_cgroup_v2(cpu_max_text):
    parts = str(cpu_max_text or "").strip().split()
    if len(parts) < 2 or parts[0] == "max":
        return None
    quota = _positive_int(parts[0])
    period = _positive_int(parts[1])
    if quota is None or period is None:
        return None
    return max(1, floor(quota / period))


def _cpu_count_from_cgroup_v1(quota_text, period_text):
    quota = _positive_int(str(quota_text or "").strip())
    period = _positive_int(str(period_text or "").strip())
    if quota is None or period is None:
        return None
    return max(1, floor(quota / period))


def _memory_bytes_from_cgroup_v2(memory_max_text):
    text = str(memory_max_text or "").strip()
    if not text or text == "max":
        return None
    return _positive_int(text)


def _memory_bytes_from_cgroup_v1(memory_limit_text):
    memory_limit = _positive_int(str(memory_limit_text or "").strip())
    if memory_limit is None:
        return None
    # Docker/cgroup v1 often reports a huge sentinel when memory is unlimited.
    if memory_limit >= 1 << 60:
        return None
    return memory_limit


def _read_text_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


def effective_cpu_count():
    candidates = [os.cpu_count() or 1]
    try:
        candidates.append(len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        pass

    cgroup_v2_count = _cpu_count_from_cgroup_v2(_read_text_file("/sys/fs/cgroup/cpu.max"))
    if cgroup_v2_count is not None:
        candidates.append(cgroup_v2_count)

    cgroup_v1_count = _cpu_count_from_cgroup_v1(
        _read_text_file("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"),
        _read_text_file("/sys/fs/cgroup/cpu/cpu.cfs_period_us"),
    )
    if cgroup_v1_count is not None:
        candidates.append(cgroup_v1_count)

    return max(1, min(int(candidate) for candidate in candidates if candidate))


def effective_memory_limit_bytes():
    candidates = []

    cgroup_v2_limit = _memory_bytes_from_cgroup_v2(_read_text_file("/sys/fs/cgroup/memory.max"))
    if cgroup_v2_limit is not None:
        candidates.append(cgroup_v2_limit)

    cgroup_v1_limit = _memory_bytes_from_cgroup_v1(_read_text_file("/sys/fs/cgroup/memory/memory.limit_in_bytes"))
    if cgroup_v1_limit is not None:
        candidates.append(cgroup_v1_limit)

    if not candidates:
        return None
    return max(1, min(candidates))


def parse_ifc_iterator_thread_cap_value(value):
    if value in (None, ""):
        return None
    return _positive_int(value)


def _configured_positive_int(name, default=None):
    env_value = _positive_int(os.environ.get(name))
    if env_value is not None:
        return env_value
    setting_value = _positive_int(_django_setting(name))
    if setting_value is not None:
        return setting_value
    return default


def _configured_ifc_iterator_thread_cap():
    env_cap = parse_ifc_iterator_thread_cap_value(os.environ.get(IFC_PARSER_THREAD_CAP_SETTING))
    if env_cap is not None:
        return env_cap
    return parse_ifc_iterator_thread_cap_value(_django_setting(IFC_PARSER_THREAD_CAP_SETTING))


def _thread_cap_from_memory_limit(memory_limit_bytes, per_thread_mb=None, reserve_mb=None):
    if memory_limit_bytes is None:
        return None
    per_thread_mb = _positive_int(per_thread_mb) or IFC_DEFAULT_PARSER_MEMORY_PER_THREAD_MB
    reserve_mb = _positive_int(reserve_mb)
    if reserve_mb is None:
        reserve_mb = IFC_DEFAULT_PARSER_MEMORY_RESERVE_MB
    usable_bytes = max(0, int(memory_limit_bytes) - (reserve_mb * BYTES_PER_MIB))
    return max(1, floor(usable_bytes / (per_thread_mb * BYTES_PER_MIB)))


def _configured_memory_thread_cap():
    memory_limit = effective_memory_limit_bytes()
    if memory_limit is None:
        return None
    return _thread_cap_from_memory_limit(
        memory_limit,
        per_thread_mb=_configured_positive_int(
            IFC_PARSER_MEMORY_PER_THREAD_MB_SETTING,
            IFC_DEFAULT_PARSER_MEMORY_PER_THREAD_MB,
        ),
        reserve_mb=_configured_positive_int(
            IFC_PARSER_MEMORY_RESERVE_MB_SETTING,
            IFC_DEFAULT_PARSER_MEMORY_RESERVE_MB,
        ),
    )


def parse_ifc_iterator_thread_count_value(value, thread_cap=None):
    if value in (None, ""):
        return None
    text = str(value).strip().lower()
    if text in {"auto", "cpu", "cores"}:
        parsed = max(1, effective_cpu_count() - 1)
        memory_cap = _configured_memory_thread_cap()
        if memory_cap is not None:
            parsed = min(parsed, memory_cap)
    else:
        parsed = _positive_int(value)
    if parsed is None:
        return None
    cap = parse_ifc_iterator_thread_cap_value(thread_cap)
    if cap is not None:
        parsed = min(parsed, cap)
    return max(1, parsed)


def configured_ifc_iterator_thread_count():
    thread_cap = _configured_ifc_iterator_thread_cap()
    env_value = os.environ.get(IFC_PARSER_THREADS_SETTING)
    env_count = parse_ifc_iterator_thread_count_value(env_value, thread_cap=thread_cap)
    if env_count is not None:
        return env_count, "env"

    setting_value = _django_setting(IFC_PARSER_THREADS_SETTING)
    setting_count = parse_ifc_iterator_thread_count_value(setting_value, thread_cap=thread_cap)
    if setting_count is not None:
        return setting_count, "django_settings"

    return IFC_DEFAULT_ITERATOR_THREADS, "default"


def _ifcopenshell_geometry_unit_stats(settings):
    length_unit = _settings_get(settings, "length-unit")
    convert_back_units = bool(_settings_get(settings, "convert-back-units"))
    return {
        "geometry_unit": "M",
        "geometry_scale_to_m": 1.0,
        "geometry_unit_basis": "ifcopenshell_geom_iterator",
        "ifcopenshell_length_unit_setting": length_unit,
        "ifcopenshell_convert_back_units": convert_back_units,
        "ifcopenshell_geometry_note": (
            "IfcOpenShell geometry iterator settings report length-unit=1.0 and convert-back-units=False; "
            "render coordinates are treated as SI metres while IFC-declared source units are stored separately."
        ),
    }


def _import_ifcopenshell():
    try:
        import ifcopenshell
        import ifcopenshell.geom
        import ifcopenshell.util.shape
    except ImportError as exc:
        raise IFCDependencyError(
            "IfcOpenShell is not installed in this environment. "
            "Install it before uploading IFC files."
        ) from exc
    return ifcopenshell


def _safe_str(value):
    if value in (None, "", "$"):
        return ""
    return str(value).strip()


def _humanize_ifc_name(value):
    text = _safe_str(value)
    if not text:
        return ""
    if text.startswith("Ifc"):
        return text
    return text


def _get_attr(entity, attr_name):
    return getattr(entity, attr_name, None) if entity is not None else None


def _unwrap_nominal_value(value):
    if value is None:
        return ""
    if hasattr(value, "wrappedValue"):
        return value.wrappedValue
    return value


def _clean_scalar(value):
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    wrapped = _unwrap_nominal_value(value)
    if isinstance(wrapped, (str, int, float, bool)):
        return wrapped
    if hasattr(wrapped, "is_a"):
        name = _safe_str(_get_attr(wrapped, "Name"))
        return name or wrapped.is_a()
    return _safe_str(wrapped)


def _quantity_value(quantity):
    for attr_name in (
        "LengthValue",
        "AreaValue",
        "VolumeValue",
        "CountValue",
        "WeightValue",
        "TimeValue",
    ):
        value = _get_attr(quantity, attr_name)
        if value is not None:
            return _clean_scalar(value)
    return ""


def _extract_property_sets(element):
    property_sets = {}
    quantities = {}

    for rel in list(_get_attr(element, "IsDefinedBy") or []):
        if not rel or not rel.is_a("IfcRelDefinesByProperties"):
            continue
        definition = _get_attr(rel, "RelatingPropertyDefinition")
        if definition is None:
            continue

        if definition.is_a("IfcPropertySet"):
            pset_name = _safe_str(_get_attr(definition, "Name")) or f"PropertySet_{definition.id()}"
            values = {}
            for prop in list(_get_attr(definition, "HasProperties") or []):
                prop_name = _safe_str(_get_attr(prop, "Name")) or f"Property_{prop.id()}"
                if prop.is_a("IfcPropertySingleValue"):
                    values[prop_name] = _clean_scalar(_get_attr(prop, "NominalValue"))
                else:
                    values[prop_name] = prop.is_a()
            property_sets[pset_name] = values

        elif definition.is_a("IfcElementQuantity"):
            quantity_set_name = _safe_str(_get_attr(definition, "Name")) or f"QuantitySet_{definition.id()}"
            values = {}
            for quantity in list(_get_attr(definition, "Quantities") or []):
                quantity_name = _safe_str(_get_attr(quantity, "Name")) or f"Quantity_{quantity.id()}"
                values[quantity_name] = _quantity_value(quantity)
            quantities[quantity_set_name] = values

    return property_sets, quantities


def _material_names(material_ref):
    if material_ref is None:
        return []

    if hasattr(material_ref, "is_a"):
        if material_ref.is_a("IfcMaterial"):
            name = _safe_str(_get_attr(material_ref, "Name"))
            return [name] if name else []

        if material_ref.is_a("IfcMaterialList"):
            names = []
            for item in list(_get_attr(material_ref, "Materials") or []):
                names.extend(_material_names(item))
            return names

        if material_ref.is_a("IfcMaterialLayerSetUsage"):
            return _material_names(_get_attr(material_ref, "ForLayerSet"))

        if material_ref.is_a("IfcMaterialLayerSet"):
            names = []
            for layer in list(_get_attr(material_ref, "MaterialLayers") or []):
                names.extend(_material_names(_get_attr(layer, "Material")))
            return names

        if material_ref.is_a("IfcMaterialLayer"):
            return _material_names(_get_attr(material_ref, "Material"))

    return [_safe_str(material_ref)] if _safe_str(material_ref) else []


def _extract_materials(element):
    names = []
    for rel in list(_get_attr(element, "HasAssociations") or []):
        if not rel or not rel.is_a("IfcRelAssociatesMaterial"):
            continue
        names.extend(_material_names(_get_attr(rel, "RelatingMaterial")))

    ordered = []
    seen = set()
    for name in names:
        clean_name = _safe_str(name)
        if clean_name and clean_name not in seen:
            seen.add(clean_name)
            ordered.append(clean_name)
    return ordered


def _extract_spatial_path(element):
    path = []
    seen = set()

    rels = list(_get_attr(element, "ContainedInStructure") or [])
    current = rels[0].RelatingStructure if rels else None

    while current is not None:
        current_id = current.id()
        if current_id in seen:
            break
        seen.add(current_id)

        label = _safe_str(_get_attr(current, "Name")) or "Unnamed"
        path.append(f"{current.is_a()}:{label}")

        decomposes = list(_get_attr(current, "Decomposes") or [])
        current = decomposes[0].RelatingObject if decomposes else None

    path.reverse()
    return path


def _extract_reference_from_psets(property_sets):
    for pset_name, values in property_sets.items():
        if "Reference" in values and values["Reference"]:
            return _safe_str(values["Reference"])
        if pset_name == "Tekla Common":
            for key in ("Initial GUID", "Preliminary mark"):
                if values.get(key):
                    return _safe_str(values[key])
    return ""


def _default_color_for_class(ifc_class):
    palette = {
        "IfcColumn": [0.42, 0.54, 0.73],
        "IfcBeam": [0.59, 0.45, 0.72],
        "IfcMember": [0.49, 0.58, 0.76],
        "IfcPlate": [0.78, 0.54, 0.33],
        "IfcCovering": [0.53, 0.63, 0.55],
        "IfcSlab": [0.67, 0.62, 0.50],
        "IfcWall": [0.74, 0.69, 0.62],
    }
    return palette.get(ifc_class, IFC_DEFAULT_COLOR)


def _extract_display_color(shape, ifc_class):
    geometry = getattr(shape, "geometry", None)
    materials = list(getattr(geometry, "materials", None) or [])
    for style in materials:
        if getattr(style, "has_diffuse", False):
            diffuse = list(getattr(style, "diffuse", []) or [])
            if len(diffuse) >= 3:
                return [float(diffuse[0]), float(diffuse[1]), float(diffuse[2])]
    return _default_color_for_class(ifc_class)


def _world_vertices(shape, ifcopenshell):
    verts = np.array(getattr(shape.geometry, "verts", []) or [], dtype=float)
    faces = list(getattr(shape.geometry, "faces", []) or [])

    if verts.size == 0 or not faces:
        return None, None, None

    verts = verts.reshape(-1, 3)
    matrix = np.array(ifcopenshell.util.shape.get_shape_matrix(shape), dtype=float)
    if matrix.shape != (4, 4):
        raise IFCParseError("Unexpected IFC transform matrix shape.")

    verts_h = np.concatenate([verts, np.ones((verts.shape[0], 1))], axis=1)
    transformed = (matrix @ verts_h.T).T[:, :3]

    mins = transformed.min(axis=0)
    maxs = transformed.max(axis=0)
    bounds = {
        "min_x": float(mins[0]),
        "max_x": float(maxs[0]),
        "min_y": float(mins[1]),
        "max_y": float(maxs[1]),
        "min_z": float(mins[2]),
        "max_z": float(maxs[2]),
    }
    return transformed.tolist(), faces, bounds


def _hierarchy_group(spatial_path, ifc_class):
    if spatial_path:
        return f"{spatial_path[-1]} / {ifc_class}"
    return ifc_class or "IFC Objects"


def _mesh_item_from_shape(uid, filename, element, shape, ifcopenshell):
    ifc_class = element.is_a()
    vertices_raw, indices, bounds = _world_vertices(shape, ifcopenshell)
    if vertices_raw is None:
        return None

    property_sets, quantities = _extract_property_sets(element)
    materials = _extract_materials(element)
    spatial_path = _extract_spatial_path(element)
    component_ref = (
        _extract_reference_from_psets(property_sets)
        or _safe_str(_get_attr(element, "Tag"))
        or _safe_str(_get_attr(element, "Name"))
        or _safe_str(_get_attr(element, "GlobalId"))
    )

    display_color = _extract_display_color(shape, ifc_class)
    material_rows = [{"code": "", "description": name} for name in materials]

    item = {
        "uid": uid,
        "record_id": IFC_RECORD_ID,
        "kind": _humanize_ifc_name(ifc_class),
        "mesh_vertices_raw": vertices_raw,
        "mesh_indices_raw": indices,
        "properties": {
            "source_format": "IFC",
            "source_record": ifc_class,
            "record_id": IFC_RECORD_ID,
            "kind": _humanize_ifc_name(ifc_class),
            "filename": filename,
            "ifc_class": ifc_class,
            "global_id": _safe_str(_get_attr(element, "GlobalId")),
            "component_ref": component_ref,
            "name": _safe_str(_get_attr(element, "Name")),
            "description": _safe_str(_get_attr(element, "Description")),
            "object_type": _safe_str(_get_attr(element, "ObjectType")),
            "predefined_type": _safe_str(_get_attr(element, "PredefinedType")),
            "tag": _safe_str(_get_attr(element, "Tag")),
            "hierarchy_group": _hierarchy_group(spatial_path, ifc_class),
            "spatial_path": spatial_path,
            "storey_name": spatial_path[-1] if spatial_path else "",
            "materials": material_rows,
            "material_names": materials,
            "property_sets": property_sets,
            "quantities": quantities,
            "display_color": display_color,
            "raw_bounds": bounds,
            "notes": [],
        },
    }
    return item


def _normalize_ifc_scene(scene):
    all_points = []
    for item in scene["meshes"]:
        all_points.extend(item["mesh_vertices_raw"])

    stats = scene.setdefault("stats", {})
    stats.update(
        {
            "pipe_count": len(scene["pipes"]),
            "fitting_count": len(scene["fittings"]),
            "weld_count": len(scene["welds"]),
            "support_count": len(scene["supports"]),
            "marker_count": len(scene["markers"]),
            "mesh_count": len(scene["meshes"]),
            "save_supported": False,
        }
    )

    if not all_points:
        stats.update(coordinate_unit_stats("IFC", "M", "ifcopenshell_geometry_si"))
        stats["scale_factor"] = 1.0
        stats["raw_bounds"] = {}
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
    stats.update(coordinate_unit_stats("IFC", "M", "ifcopenshell_geometry_si"))
    scale = stats["coordinate_scale_to_m"]

    def tx(point):
        return [
            (point[0] - cx) * scale,
            (point[2] - cz) * scale,
            (point[1] - cy) * scale,
        ]

    for item in scene["meshes"]:
        normalized_vertices = [coord for vertex in item.pop("mesh_vertices_raw") for coord in tx(vertex)]
        item["mesh"] = {
            "positions": normalized_vertices,
            "indices": item.pop("mesh_indices_raw"),
            "color": deepcopy(item["properties"].get("display_color") or IFC_DEFAULT_COLOR),
        }

    stats["scale_factor"] = scale
    stats["raw_bounds"] = {
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
        "min_z": min_z,
        "max_z": max_z,
    }
    return scene


def _parse_ifc_file(path, filename):
    ifcopenshell = _import_ifcopenshell()
    ifc_file = ifcopenshell.open(path)

    scene = {
        "pipes": [],
        "fittings": [],
        "welds": [],
        "supports": [],
        "markers": [],
        "meshes": [],
        "stats": {
            "total_lines": 0,
            "source_format": "IFC",
            "source_label": "IFC Scene",
        },
    }

    scene["stats"].update(extract_ifc_length_unit_stats(ifc_file))

    settings = ifcopenshell.geom.settings()
    scene["stats"].update(_ifcopenshell_geometry_unit_stats(settings))
    iterator_threads, iterator_thread_source = configured_ifc_iterator_thread_count()
    scene["stats"]["ifcopenshell_iterator_threads"] = iterator_threads
    scene["stats"]["ifcopenshell_iterator_thread_source"] = iterator_thread_source
    iterator = ifcopenshell.geom.iterator(settings, ifc_file, iterator_threads)
    if not iterator.initialize():
        raise IFCParseError(f"Unable to initialize IFC geometry iterator for {filename}.")

    next_uid = 1
    while True:
        shape = iterator.get()
        element = ifc_file.by_id(shape.id)
        if element is not None and _safe_str(_get_attr(element, "Representation")) != "":
            item = _mesh_item_from_shape(next_uid, filename, element, shape, ifcopenshell)
            if item:
                scene["meshes"].append(item)
                next_uid += 1
        if not iterator.next():
            break

    scene["stats"]["total_lines"] = len(scene["meshes"])
    scene["stats"]["ifc_object_count"] = len(scene["meshes"])
    return scene


def parse_multiple_ifc_uploads(file_payloads, project):
    del project

    combined_scene = {
        "pipes": [],
        "fittings": [],
        "welds": [],
        "supports": [],
        "markers": [],
        "meshes": [],
        "stats": {
            "total_lines": 0,
            "source_format": "IFC",
            "source_label": "Batched IFC Scene",
        },
    }

    temp_paths = []
    try:
        for filename, raw_bytes in file_payloads:
            suffix = os.path.splitext(filename)[1].lower()
            if suffix not in IFC_SUPPORTED_EXTENSIONS:
                continue

            with tempfile.NamedTemporaryFile(suffix=suffix or ".ifc", delete=False) as handle:
                handle.write(raw_bytes)
                temp_paths.append(handle.name)
                file_scene = _parse_ifc_file(handle.name, filename)

            combined_scene["meshes"].extend(file_scene["meshes"])
            file_stats = file_scene.get("stats") or {}
            source_files = combined_scene["stats"].setdefault("source_files", [])
            source_files.append(
                {
                    "filename": filename,
                    "mesh_count": len(file_scene["meshes"]),
                    "ifc_declared_length_unit": file_stats.get("ifc_declared_length_unit", ""),
                    "ifc_declared_length_scale_to_m": file_stats.get("ifc_declared_length_scale_to_m"),
                    "geometry_unit": file_stats.get("geometry_unit", ""),
                    "ifcopenshell_length_unit_setting": file_stats.get("ifcopenshell_length_unit_setting"),
                    "ifcopenshell_convert_back_units": file_stats.get("ifcopenshell_convert_back_units"),
                    "ifcopenshell_iterator_threads": file_stats.get("ifcopenshell_iterator_threads"),
                    "ifcopenshell_iterator_thread_source": file_stats.get("ifcopenshell_iterator_thread_source", ""),
                }
            )
            for key in (
                "ifc_declared_length_units",
                "ifc_declared_length_unit",
                "ifc_declared_length_unit_name",
                "ifc_declared_length_unit_entity",
                "ifc_declared_length_scale_to_m",
                "ifc_declared_length_confidence",
                "geometry_unit",
                "geometry_scale_to_m",
                "geometry_unit_basis",
                "ifcopenshell_length_unit_setting",
                "ifcopenshell_convert_back_units",
                "ifcopenshell_iterator_threads",
                "ifcopenshell_iterator_thread_source",
                "ifcopenshell_geometry_note",
            ):
                if key not in combined_scene["stats"] and key in file_stats:
                    combined_scene["stats"][key] = file_stats[key]

        combined_scene["stats"]["total_lines"] = len(combined_scene["meshes"])
        combined_scene["stats"]["ifc_object_count"] = len(combined_scene["meshes"])
        return _normalize_ifc_scene(combined_scene)
    finally:
        for temp_path in temp_paths:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
