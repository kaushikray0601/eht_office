import os
import tempfile
from copy import deepcopy

import numpy as np

from .units import coordinate_unit_stats


IFC_RECORD_ID = 9100
IFC_SUPPORTED_EXTENSIONS = (".ifc",)
IFC_DEFAULT_COLOR = [0.45, 0.55, 0.72]


class IFCDependencyError(RuntimeError):
    pass


class IFCParseError(RuntimeError):
    pass


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
        stats.update(coordinate_unit_stats("IFC", "M", "assumed"))
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
    stats.update(coordinate_unit_stats("IFC", "M", "assumed"))
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

    settings = ifcopenshell.geom.settings()
    iterator = ifcopenshell.geom.iterator(settings, ifc_file, 1)
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

        combined_scene["stats"]["total_lines"] = len(combined_scene["meshes"])
        combined_scene["stats"]["ifc_object_count"] = len(combined_scene["meshes"])
        return _normalize_ifc_scene(combined_scene)
    finally:
        for temp_path in temp_paths:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
