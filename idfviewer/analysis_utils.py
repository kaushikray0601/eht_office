import math


def _safe_float_list(value):
    if not isinstance(value, list) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


def _bbox_distance(point, bounds):
    px, py, pz = point
    min_x = float(bounds["min_x"])
    max_x = float(bounds["max_x"])
    min_y = float(bounds["min_y"])
    max_y = float(bounds["max_y"])
    min_z = float(bounds["min_z"])
    max_z = float(bounds["max_z"])

    dx = 0.0 if min_x <= px <= max_x else min(abs(px - min_x), abs(px - max_x))
    dy = 0.0 if min_y <= py <= max_y else min(abs(py - min_y), abs(py - max_y))
    dz = 0.0 if min_z <= pz <= max_z else min(abs(pz - min_z), abs(pz - max_z))
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _merge_bounds(bounds_list):
    if not bounds_list:
        return {}
    return {
        "min_x": min(float(bounds["min_x"]) for bounds in bounds_list),
        "max_x": max(float(bounds["max_x"]) for bounds in bounds_list),
        "min_y": min(float(bounds["min_y"]) for bounds in bounds_list),
        "max_y": max(float(bounds["max_y"]) for bounds in bounds_list),
        "min_z": min(float(bounds["min_z"]) for bounds in bounds_list),
        "max_z": max(float(bounds["max_z"]) for bounds in bounds_list),
    }


def _bounds_from_points(points):
    if not points:
        return {}
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    return {
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
        "min_z": min(zs),
        "max_z": max(zs),
    }


def _bounds_center(bounds):
    if not bounds:
        return None
    return [
        (float(bounds["min_x"]) + float(bounds["max_x"])) / 2.0,
        (float(bounds["min_y"]) + float(bounds["max_y"])) / 2.0,
        (float(bounds["min_z"]) + float(bounds["max_z"])) / 2.0,
    ]


def _point_distance(a, b):
    return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(3)))


def _axis_overlap(a_min, a_max, b_min, b_max):
    return max(float(a_min), float(b_min)) <= min(float(a_max), float(b_max))


def _overlap_flags(bounds_a, bounds_b):
    if not bounds_a or not bounds_b:
        return {"x": False, "y": False, "z": False}
    return {
        "x": _axis_overlap(bounds_a["min_x"], bounds_a["max_x"], bounds_b["min_x"], bounds_b["max_x"]),
        "y": _axis_overlap(bounds_a["min_y"], bounds_a["max_y"], bounds_b["min_y"], bounds_b["max_y"]),
        "z": _axis_overlap(bounds_a["min_z"], bounds_a["max_z"], bounds_b["min_z"], bounds_b["max_z"]),
    }


def _midpoint(a, b):
    return [(a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, (a[2] + b[2]) / 2.0]


def _line_key(item):
    properties = item.get("properties") or {}
    return (
        str(properties.get("pipeline_ref") or "").strip()
        or str(properties.get("spool_ref") or "").strip()
        or f"Unknown::{properties.get('filename') or 'Unknown File'}"
    )


def _line_label(line_key):
    if line_key.startswith("Unknown::"):
        return line_key.split("::", 1)[1]
    return line_key


def _collect_pipeline_samples(scene):
    groups = {}
    scene_buckets = ("pipes", "fittings", "welds", "supports", "markers")

    for bucket in scene_buckets:
        for item in scene.get(bucket, []) or []:
            properties = item.get("properties") or {}
            line_key = _line_key(item)
            group = groups.setdefault(
                line_key,
                {
                    "line_key": line_key,
                    "line_label": _line_label(line_key),
                    "filename": properties.get("filename") or "",
                    "sample_points_m": [],
                    "component_count": 0,
                },
            )
            group["component_count"] += 1

            raw_start = _safe_float_list(properties.get("raw_start"))
            raw_end = _safe_float_list(properties.get("raw_end"))
            raw_point = _safe_float_list(properties.get("raw_point"))

            if raw_start and raw_end:
                start_m = [coord * 0.001 for coord in raw_start]
                end_m = [coord * 0.001 for coord in raw_end]
                group["sample_points_m"].extend([start_m, end_m, _midpoint(start_m, end_m)])
            elif raw_point:
                group["sample_points_m"].append([coord * 0.001 for coord in raw_point])

    return [group for group in groups.values() if group["sample_points_m"]]


def _ifc_candidates(ifc_scene):
    candidates = []
    for item in ifc_scene.get("meshes", []) or []:
        properties = item.get("properties") or {}
        bounds = properties.get("raw_bounds") or {}
        if not {"min_x", "max_x", "min_y", "max_y", "min_z", "max_z"}.issubset(bounds.keys()):
            continue
        candidates.append(
            {
                "uid": item.get("uid"),
                "ifc_class": properties.get("ifc_class") or item.get("kind") or "IFC Object",
                "component_ref": properties.get("component_ref") or "",
                "name": properties.get("name") or "",
                "storey_name": properties.get("storey_name") or "",
                "material_names": properties.get("material_names") or [],
                "bounds": bounds,
                "filename": properties.get("filename") or "",
            }
        )
    return candidates


def nearest_structure_report(scene, ifc_scene, limit=50):
    line_groups = _collect_pipeline_samples(scene)
    ifc_objects = _ifc_candidates(ifc_scene)
    pipeline_bounds = _bounds_from_points([point for group in line_groups for point in group["sample_points_m"]])
    ifc_bounds = _merge_bounds([candidate["bounds"] for candidate in ifc_objects])

    results = []
    for line_group in line_groups:
        best = None
        for candidate in ifc_objects:
            for point in line_group["sample_points_m"]:
                distance = _bbox_distance(point, candidate["bounds"])
                if best is None or distance < best["distance_m"]:
                    best = {
                        "line_key": line_group["line_key"],
                        "line_label": line_group["line_label"],
                        "pipeline_file": line_group["filename"],
                        "component_count": line_group["component_count"],
                        "distance_m": distance,
                        "distance_mm": distance * 1000.0,
                        "ifc_uid": candidate["uid"],
                        "ifc_class": candidate["ifc_class"],
                        "component_ref": candidate["component_ref"],
                        "name": candidate["name"],
                        "storey_name": candidate["storey_name"],
                        "material_names": candidate["material_names"],
                        "ifc_file": candidate["filename"],
                    }
        if best is not None:
            results.append(best)

    results.sort(key=lambda row: (row["distance_m"], row["line_label"]))
    limited = results[:limit]
    centroid_distance_m = None
    pipeline_center = _bounds_center(pipeline_bounds)
    ifc_center = _bounds_center(ifc_bounds)
    if pipeline_center and ifc_center:
        centroid_distance_m = _point_distance(pipeline_center, ifc_center)

    warning = ""
    if not ifc_objects:
        warning = "No renderable IFC objects were found in the uploaded reference file(s)."
    elif not line_groups:
        warning = "The current scene does not contain raw pipeline geometry to compare."
    elif limited:
        overlap = _overlap_flags(pipeline_bounds, ifc_bounds)
        best_distance = limited[0]["distance_m"]
        if centroid_distance_m is not None and centroid_distance_m > 250 and best_distance > 250:
            warning = "Pipeline and IFC coordinates appear far apart. The selected files may not belong to the same plant area or may use different site origins."
        elif not any(overlap.values()) and best_distance > 25:
            warning = "Pipeline and IFC extents do not overlap on any main axis. Check that the chosen files share the same plant reference frame."

    return {
        "results": limited,
        "summary": {
            "line_count": len(line_groups),
            "ifc_object_count": len(ifc_objects),
            "result_count": len(limited),
            "pipeline_bounds_m": pipeline_bounds,
            "ifc_bounds_m": ifc_bounds,
            "centroid_distance_m": centroid_distance_m,
            "warning": warning,
        },
    }
