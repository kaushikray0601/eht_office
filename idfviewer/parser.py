import re
from statistics import median


PIPE_IDS = {100, 101, 102, 103}
WELD_IDS = {120}

POINT_TO_POINT_IDS = {
    30, 31, 35, 36, 40, 41, 42, 45, 46, 47, 50, 51, 52, 53, 55,
    60, 61, 62, 65, 70, 71, 72, 75, 76, 80, 81, 82, 85, 86, 87, 88,
    90, 91, 92, 93, 95, 96, 100, 101, 102, 103, 105, 106, 107, 110,
    115, 120, 125, 126, 127, 130, 132, 134, 136
}

FITTING_IDS = POINT_TO_POINT_IDS - PIPE_IDS - WELD_IDS

KIND_MAP = {
    100: "Pipe",
    101: "Fixed Pipe",
    102: "Pipe Block Fixed",
    103: "Pipe Block Variable",
    120: "Weld",
    149: "Marker",
    150: "Support",
    35: "Elbow In",
    36: "Elbow Out",
    40: "Olet In",
    41: "Olet Branch",
    42: "Olet Out",
    45: "Tee In",
    46: "Tee Branch",
    47: "Tee Out",
    55: "Reducer",
    105: "Flange",
    107: "Blind Flange",
    110: "Gasket",
    115: "Bolt",
    125: "Cap",
    126: "Coupling",
    127: "Union",
    130: "Valve",
    132: "Trap",
    134: "Vent",
    136: "Filter",
}


def _clean_line(line: str) -> str:
    return line.replace("\x00", "").lstrip("\ufeff").rstrip()


def _extract_record_id(line: str):
    m = re.match(r"^\s*([+-]?\d+)", line)
    if not m:
        return None
    return int(m.group(1))


def _extract_ints_after_record_id(line: str):
    nums = [int(x) for x in re.findall(r"[+-]?\d+", line)]
    if not nums:
        return []
    return nums[1:]


def _extract_text_segments(line: str):
    """
    Pull text-ish comma-separated fragments from lines such as:
      120 .... ,      ,       0 ,BW  ,      0     1
      149 .... ,FLOW, ...
      150 .... ,NCU7, ...
    """
    segments = [seg.strip() for seg in line.split(",")]
    out = []
    for seg in segments:
        if not seg:
            continue
        # Skip purely numeric fragments
        if re.fullmatch(r"[+\-]?\d+(\s+[+\-]?\d+)*", seg):
            continue
        if any(ch.isalpha() for ch in seg):
            out.append(re.sub(r"\s+", " ", seg).strip())
    return out


def _kind_name(record_id):
    return KIND_MAP.get(record_id, f"Record {record_id}")


def _point_magnitude(p):
    return max(abs(p[0]), abs(p[1]), abs(p[2]))


def _all_zero_point(p):
    return p[0] == 0 and p[1] == 0 and p[2] == 0


def _record_is_point_to_point(item):
    return "start_raw" in item and "end_raw" in item


def _record_is_single_point(item):
    return "point_raw" in item


def _append_meta(item, meta_key, text):
    if "_meta" not in item:
        item["_meta"] = {}
    item["_meta"].setdefault(meta_key, []).append(text)


def _collect_candidate_records(text: str):
    scene = {
        "pipes": [],
        "fittings": [],
        "welds": [],
        "supports": [],
        "markers": [],
        "stats": {
            "total_lines": 0,
            "parsed_records": 0,
            "pipe_count": 0,
            "fitting_count": 0,
            "weld_count": 0,
            "support_count": 0,
            "marker_count": 0,
            "scale_factor": 1.0,
        },
    }

    lines = text.splitlines()
    scene["stats"]["total_lines"] = len(lines)

    current_item = None
    current_meta_key = None
    uid_counter = 1

    for raw_line in lines:
        line = _clean_line(raw_line)
        if not line.strip():
            continue

        record_id = _extract_record_id(line)
        if record_id is None:
            continue

        # Negative metadata lines
        if record_id < 0:
            if current_item is None:
                continue

            text_part = line[len(str(record_id)):].strip()

            if record_id == -1:
                # continuation line
                if current_meta_key and current_item["_meta"].get(current_meta_key):
                    current_item["_meta"][current_meta_key][-1] += " " + text_part
            else:
                current_meta_key = str(record_id)
                _append_meta(current_item, current_meta_key, text_part)

            continue

        current_meta_key = None
        nums = _extract_ints_after_record_id(line)
        text_segments = _extract_text_segments(line)
        inline_code = text_segments[0] if text_segments else ""

        item = None

        if record_id in PIPE_IDS and len(nums) >= 6:
            item = {
                "uid": uid_counter,
                "record_id": record_id,
                "kind": _kind_name(record_id),
                "inline_code": inline_code,
                "start_raw": [nums[0], nums[1], nums[2]],
                "end_raw": [nums[3], nums[4], nums[5]],
                "_meta": {},
            }
            scene["pipes"].append(item)

        elif record_id in FITTING_IDS and len(nums) >= 6:
            item = {
                "uid": uid_counter,
                "record_id": record_id,
                "kind": _kind_name(record_id),
                "inline_code": inline_code,
                "start_raw": [nums[0], nums[1], nums[2]],
                "end_raw": [nums[3], nums[4], nums[5]],
                "_meta": {},
            }
            scene["fittings"].append(item)

        elif record_id in WELD_IDS and len(nums) >= 3:
            item = {
                "uid": uid_counter,
                "record_id": record_id,
                "kind": _kind_name(record_id),
                "inline_code": inline_code,
                "point_raw": [nums[0], nums[1], nums[2]],
                "_meta": {},
            }
            scene["welds"].append(item)

        elif record_id == 150 and len(nums) >= 3:
            item = {
                "uid": uid_counter,
                "record_id": record_id,
                "kind": _kind_name(record_id),
                "inline_code": inline_code,
                "point_raw": [nums[0], nums[1], nums[2]],
                "_meta": {},
            }
            scene["supports"].append(item)

        elif record_id == 149 and len(nums) >= 3:
            item = {
                "uid": uid_counter,
                "record_id": record_id,
                "kind": _kind_name(record_id),
                "inline_code": inline_code,
                "point_raw": [nums[0], nums[1], nums[2]],
                "_meta": {},
            }
            scene["markers"].append(item)

        if item is not None:
            current_item = item
            uid_counter += 1

    return scene


def _build_reference_scale(scene):
    magnitudes = []

    for bucket in ("pipes", "fittings"):
        for item in scene[bucket]:
            s = item["start_raw"]
            e = item["end_raw"]
            if not _all_zero_point(s):
                magnitudes.append(_point_magnitude(s))
            if not _all_zero_point(e):
                magnitudes.append(_point_magnitude(e))

    for bucket in ("welds", "supports", "markers"):
        for item in scene[bucket]:
            p = item["point_raw"]
            if not _all_zero_point(p):
                magnitudes.append(_point_magnitude(p))

    if not magnitudes:
        return 1.0

    return median(magnitudes)


def _is_valid_geometry_record(item, reference_scale):
    low_limit = max(reference_scale * 0.1, 1000)

    if _record_is_point_to_point(item):
        s = item["start_raw"]
        e = item["end_raw"]

        if _all_zero_point(s) and _all_zero_point(e):
            return False

        if _point_magnitude(s) < low_limit and _point_magnitude(e) < low_limit:
            return False

        return True

    if _record_is_single_point(item):
        p = item["point_raw"]

        if _all_zero_point(p):
            return False

        if _point_magnitude(p) < low_limit:
            return False

        return True

    return False


def _filter_scene(scene):
    reference_scale = _build_reference_scale(scene)

    filtered = {
        "pipes": [],
        "fittings": [],
        "welds": [],
        "supports": [],
        "markers": [],
        "stats": {
            "total_lines": scene["stats"]["total_lines"],
            "parsed_records": 0,
            "pipe_count": 0,
            "fitting_count": 0,
            "weld_count": 0,
            "support_count": 0,
            "marker_count": 0,
            "scale_factor": 1.0,
            "reference_scale": reference_scale,
        },
    }

    for bucket in ("pipes", "fittings", "welds", "supports", "markers"):
        for item in scene[bucket]:
            if _is_valid_geometry_record(item, reference_scale):
                filtered[bucket].append(item)

    filtered["stats"]["pipe_count"] = len(filtered["pipes"])
    filtered["stats"]["fitting_count"] = len(filtered["fittings"])
    filtered["stats"]["weld_count"] = len(filtered["welds"])
    filtered["stats"]["support_count"] = len(filtered["supports"])
    filtered["stats"]["marker_count"] = len(filtered["markers"])
    filtered["stats"]["parsed_records"] = (
        filtered["stats"]["pipe_count"]
        + filtered["stats"]["fitting_count"]
        + filtered["stats"]["weld_count"]
        + filtered["stats"]["support_count"]
        + filtered["stats"]["marker_count"]
    )

    return filtered


def _build_properties(item):
    meta = item.get("_meta", {})

    materials = []
    codes = meta.get("-20", [])
    descs = meta.get("-21", [])

    max_len = max(len(codes), len(descs))
    for i in range(max_len):
        materials.append({
            "code": codes[i] if i < len(codes) else "",
            "description": descs[i] if i < len(descs) else "",
        })

    props = {
        "uid": item.get("uid"),
        "record_id": item.get("record_id"),
        "kind": item.get("kind"),
        "inline_code": item.get("inline_code", ""),
        "component_ref": " | ".join(meta.get("-39", [])),
        "pipeline_ref": " | ".join(meta.get("-30", [])),
        "support_code": " | ".join(meta.get("-70", [])),
        "notes": meta.get("-37", []),
        "materials": materials,
        "raw_meta": meta,
    }

    if "start_raw" in item:
        props["raw_start"] = item["start_raw"]
        props["raw_end"] = item["end_raw"]

    if "point_raw" in item:
        props["raw_point"] = item["point_raw"]

    return props


def _normalize_points(scene):
    all_points = []

    for item in scene["pipes"]:
        all_points.append(tuple(item["start_raw"]))
        all_points.append(tuple(item["end_raw"]))

    for item in scene["fittings"]:
        all_points.append(tuple(item["start_raw"]))
        all_points.append(tuple(item["end_raw"]))

    for item in scene["welds"]:
        all_points.append(tuple(item["point_raw"]))

    for item in scene["supports"]:
        all_points.append(tuple(item["point_raw"]))

    for item in scene["markers"]:
        all_points.append(tuple(item["point_raw"]))

    if not all_points:
        scene["stats"]["scale_factor"] = 1.0
        return scene

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    zs = [p[2] for p in all_points]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    cz = (min_z + max_z) / 2.0

    span_x = max_x - min_x
    span_y = max_y - min_y
    span_z = max_z - min_z
    max_span = max(span_x, span_y, span_z, 1.0)

    scale = 250.0 / max_span

    def tx(p):
        x = (p[0] - cx) * scale
        y = (p[2] - cz) * scale
        z = (p[1] - cy) * scale
        return [x, y, z]

    for bucket in ("pipes", "fittings"):
        for item in scene[bucket]:
            item["start"] = tx(item["start_raw"])
            item["end"] = tx(item["end_raw"])
            item["properties"] = _build_properties(item)

    for bucket in ("welds", "supports", "markers"):
        for item in scene[bucket]:
            item["point"] = tx(item["point_raw"])
            item["properties"] = _build_properties(item)

    scene["stats"]["scale_factor"] = scale
    scene["stats"]["raw_bounds"] = {
        "min_x": min_x, "max_x": max_x,
        "min_y": min_y, "max_y": max_y,
        "min_z": min_z, "max_z": max_z,
    }

    return scene


def _strip_internal(scene):
    for bucket in ("pipes", "fittings"):
        for item in scene[bucket]:
            item.pop("start_raw", None)
            item.pop("end_raw", None)
            item.pop("_meta", None)

    for bucket in ("welds", "supports", "markers"):
        for item in scene[bucket]:
            item.pop("point_raw", None)
            item.pop("_meta", None)

    return scene


def parse_idf_text(text: str):
    scene = _collect_candidate_records(text)
    scene = _filter_scene(scene)
    scene = _normalize_points(scene)
    scene = _strip_internal(scene)
    return scene