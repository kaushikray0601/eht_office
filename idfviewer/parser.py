import re
from statistics import median
from .models import IDFFile, IDFComponent

RECORD_ID_RE = re.compile(r"^\s*([+-]?\d+)")
DN_RE = re.compile(r"\bDN\s*(\d+)\b", re.I)
SCH_RE = re.compile(r"\bSch\s*([A-Z0-9/]+)\b", re.I)
CLASS_RE = re.compile(r"\bCL\s*(\d+)\b", re.I)
STD_RE = re.compile(r"\b(ASME\s+B[0-9.]+|MSS\s+SP-\d+)\b", re.I)
ASTM_RE = re.compile(r"\bASTM\s+([A-Z0-9 .\-]+)", re.I)

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

KNOWN_META = {"-20", "-21", "-22", "-26", "-30", "-31", "-37", "-39", "-40", "-46", "-70"}
INHERITED_META_KEYS = {"-30"}
IDENTIFIER_META_KEYS = {"-20", "-22", "-26", "-30", "-31", "-39", "-70"}

def derive_material_properties(materials):
    text = " | ".join(
        f"{m.get('code','')} {m.get('description','')}"
        for m in materials
    )

    dns = DN_RE.findall(text)
    schs = SCH_RE.findall(text)
    classes = CLASS_RE.findall(text)
    stds = STD_RE.findall(text)
    astms = ASTM_RE.findall(text)

    return {
        "dn_values": sorted(set(dns)),
        "schedules": sorted(set(schs)),
        "pressure_classes": sorted(set(classes)),
        "standards": sorted(set(stds)),
        "astm_materials": sorted(set(a.strip() for a in astms)),
    }

def _clean_line(line: str) -> str:
    return line.replace("\x00", "").lstrip("\ufeff").rstrip()


def _extract_record_id(line: str):
    m = RECORD_ID_RE.match(line)
    if not m:
        return None
    return int(m.group(1))


def _extract_text_after_record_id(line: str) -> str:
    m = RECORD_ID_RE.match(line)
    if not m:
        return ""
    return re.sub(r"\s+", " ", line[m.end():]).strip()


def _extract_ints_after_record_id(line: str):
    nums = [int(x) for x in re.findall(r"[+-]?\d+", line)]
    if not nums:
        return []
    return nums[1:]


def _extract_text_segments(line: str):
    segments = [seg.strip() for seg in line.split(",")]
    out = []
    for seg in segments:
        if not seg:
            continue
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


def _copy_meta(meta):
    return {key: list(values) for key, values in meta.items()}


def _merge_meta_text(existing: str, extra: str, meta_key: str) -> str:
    if not existing:
        return extra
    if not extra:
        return existing

    if meta_key in IDENTIFIER_META_KEYS and (" " not in extra or extra[:1] in "-/_"):
        return existing + extra
    return f"{existing} {extra}"


def _collect_candidate_records(text: str, filename: str):
    scene = {
        "pipes": [], "fittings": [], "welds": [], "supports": [], "markers": [],
        "stats": {
            "total_lines": 0, "parsed_records": 0, "pipe_count": 0,
            "fitting_count": 0, "weld_count": 0, "support_count": 0,
            "marker_count": 0, "scale_factor": 1.0,
        },
    }

    lines = text.splitlines()
    scene["stats"]["total_lines"] = len(lines)

    current_item = None
    current_meta_key = None
    current_meta_target = None
    inherited_meta = {}
    in_context_block = False
    uid_counter = 1

    for raw_line in lines:
        line = _clean_line(raw_line)
        if not line.strip():
            continue

        record_id = _extract_record_id(line)
        if record_id is None:
            continue

        if record_id < 0:
            text_part = _extract_text_after_record_id(line)
            if record_id == -1:
                if current_meta_target == "context" and current_meta_key and inherited_meta.get(current_meta_key):
                    inherited_meta[current_meta_key][-1] = _merge_meta_text(
                        inherited_meta[current_meta_key][-1],
                        text_part,
                        current_meta_key,
                    )
                elif (
                    current_meta_target == "item"
                    and current_item is not None
                    and current_meta_key
                    and current_item["_meta"].get(current_meta_key)
                ):
                    current_item["_meta"][current_meta_key][-1] = _merge_meta_text(
                        current_item["_meta"][current_meta_key][-1],
                        text_part,
                        current_meta_key,
                    )
            else:
                current_meta_key = str(record_id)
                if current_meta_key in INHERITED_META_KEYS:
                    inherited_meta[current_meta_key] = [text_part] if text_part else []
                    current_meta_target = "context"
                    in_context_block = True
                elif current_item is not None and not in_context_block:
                    _append_meta(current_item, current_meta_key, text_part)
                    current_meta_target = "item"
                else:
                    current_meta_target = None
            continue

        current_meta_key = None
        current_meta_target = None
        nums = _extract_ints_after_record_id(line)
        text_segments = _extract_text_segments(line)
        inline_code = text_segments[0] if text_segments else ""

        item = None
        if record_id in PIPE_IDS and len(nums) >= 6:
            item = {"start_raw": [nums[0], nums[1], nums[2]], "end_raw": [nums[3], nums[4], nums[5]]}
            scene["pipes"].append(item)
        elif record_id in FITTING_IDS and len(nums) >= 6:
            item = {"start_raw": [nums[0], nums[1], nums[2]], "end_raw": [nums[3], nums[4], nums[5]]}
            scene["fittings"].append(item)
        elif record_id in WELD_IDS and len(nums) >= 3:
            item = {"point_raw": [nums[0], nums[1], nums[2]]}
            scene["welds"].append(item)
        elif record_id == 150 and len(nums) >= 3:
            item = {"point_raw": [nums[0], nums[1], nums[2]]}
            scene["supports"].append(item)
        elif record_id == 149 and len(nums) >= 3:
            item = {"point_raw": [nums[0], nums[1], nums[2]]}
            scene["markers"].append(item)

        if item is not None:
            item.update({
                "uid": uid_counter,
                "record_id": record_id,
                "kind": _kind_name(record_id),
                "inline_code": inline_code,
                "_meta": _copy_meta(inherited_meta),
                "filename": filename
            })
            current_item = item
            in_context_block = False
            uid_counter += 1

    return scene


def _build_reference_scale(scene):
    magnitudes = []
    for bucket in ("pipes", "fittings"):
        for item in scene[bucket]:
            if not _all_zero_point(item["start_raw"]): magnitudes.append(_point_magnitude(item["start_raw"]))
            if not _all_zero_point(item["end_raw"]): magnitudes.append(_point_magnitude(item["end_raw"]))

    for bucket in ("welds", "supports", "markers"):
        for item in scene[bucket]:
            if not _all_zero_point(item["point_raw"]): magnitudes.append(_point_magnitude(item["point_raw"]))

    return median(magnitudes) if magnitudes else 1.0


def _is_valid_geometry_record(item, reference_scale):
    low_limit = max(reference_scale * 0.1, 1000)

    if _record_is_point_to_point(item):
        s, e = item["start_raw"], item["end_raw"]
        if _all_zero_point(s) and _all_zero_point(e): return False
        if item.get("record_id") == 90 and (_all_zero_point(s) or _all_zero_point(e)): return False
        if _point_magnitude(s) < low_limit and _point_magnitude(e) < low_limit: return False
        return True

    if _record_is_single_point(item):
        p = item["point_raw"]
        if _all_zero_point(p): return False
        if _point_magnitude(p) < low_limit: return False
        return True
    return False


def _filter_scene(scene):
    ref_scale = _build_reference_scale(scene)
    filtered = {"pipes": [], "fittings": [], "welds": [], "supports": [], "markers": [], "stats": scene["stats"]}
    filtered["stats"]["reference_scale"] = ref_scale

    for bucket in ("pipes", "fittings", "welds", "supports", "markers"):
        for item in scene[bucket]:
            if _is_valid_geometry_record(item, ref_scale):
                filtered[bucket].append(item)

    for k in ["pipe", "fitting", "weld", "support", "marker"]:
        filtered["stats"][f"{k}_count"] = len(filtered[f"{k}s"])
        
    filtered["stats"]["parsed_records"] = sum(filtered["stats"][f"{k}_count"] for k in ["pipe", "fitting", "weld", "support", "marker"])
    return filtered


def _build_properties(item):
    meta = item.get("_meta", {})

    materials = []
    codes, descs = meta.get("-20", []), meta.get("-21", [])
    for i in range(max(len(codes), len(descs))):
        materials.append({
            "code": codes[i] if i < len(codes) else "",
            "description": descs[i] if i < len(descs) else "",
        })

    unmapped = {k: v for k, v in meta.items() if k not in KNOWN_META}

    props = {
        "uid": item.get("uid"),
        "record_id": item.get("record_id"),
        "kind": item.get("kind"),
        "inline_code": item.get("inline_code", ""),
        "materials": materials,
        "instrument_tag": " | ".join(meta.get("-22", [])),
        "insulation_spec": " | ".join(meta.get("-26", [])),
        "pipeline_ref": " | ".join(meta.get("-30", [])),
        "spool_ref": " | ".join(meta.get("-31", [])),
        "component_ref": " | ".join(meta.get("-39", [])),
        "direction": " | ".join(meta.get("-40", []) + meta.get("-46", [])),
        "support_code": " | ".join(meta.get("-70", [])),
        "notes": meta.get("-37", []),
        "unmapped_meta": unmapped,
        "raw_meta": meta,
        "filename": item.get("filename"),
    }

    if "start_raw" in item:
        props["raw_start"] = item["start_raw"]
        props["raw_end"] = item["end_raw"]
    if "point_raw" in item:
        props["raw_point"] = item["point_raw"]

    return props


def _normalize_points(scene):
    all_points = []
    for bucket in ("pipes", "fittings"):
        for item in scene[bucket]:
            all_points.extend([tuple(item["start_raw"]), tuple(item["end_raw"])])
    for bucket in ("welds", "supports", "markers"):
        for item in scene[bucket]:
            all_points.append(tuple(item["point_raw"]))

    if not all_points:
        scene["stats"]["scale_factor"], scene["stats"]["raw_bounds"] = 1.0, {}
        return scene

    xs, ys, zs = [p[0] for p in all_points], [p[1] for p in all_points], [p[2] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    
    cx, cy, cz = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0
    # Convert typical mm measurements to meters for stable WebGL scale without collapsing faraway pipelines
    scale = 0.001

    def tx(p):
        return [(p[0] - cx) * scale, (p[2] - cz) * scale, (p[1] - cy) * scale]

    for bucket in ("pipes", "fittings"):
        for item in scene[bucket]:
            item["start"], item["end"] = tx(item["start_raw"]), tx(item["end_raw"])
            item["properties"] = _build_properties(item)

    for bucket in ("welds", "supports", "markers"):
        for item in scene[bucket]:
            item["point"] = tx(item["point_raw"])
            item["properties"] = _build_properties(item)

    scene["stats"].update({"scale_factor": scale, "raw_bounds": {
        "min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y, "min_z": min_z, "max_z": max_z
    }})
    return scene


def _strip_internal(scene):
    for bucket in ("pipes", "fittings"):
        for item in scene[bucket]:
            item.pop("start_raw", None); item.pop("end_raw", None); item.pop("_meta", None)
    for bucket in ("welds", "supports", "markers"):
        for item in scene[bucket]:
            item.pop("point_raw", None); item.pop("_meta", None)
    return scene


def parse_multiple_idf_texts(file_payloads, project):
    combined_scene = {"pipes": [], "fittings": [], "welds": [], "supports": [], "markers": [], "stats": {"total_lines": 0}}
    
    db_files = {}
    for filename, text in file_payloads:
        idf_file = IDFFile.objects.create(project=project, filename=filename)
        db_files[filename] = idf_file
        
        scene = _collect_candidate_records(text, filename)
        for bucket in ["pipes", "fittings", "welds", "supports", "markers"]:
            combined_scene[bucket].extend(scene[bucket])
        combined_scene["stats"]["total_lines"] += scene["stats"]["total_lines"]
        
    combined_scene = _filter_scene(combined_scene)
    combined_scene = _normalize_points(combined_scene)
    
    bounds = combined_scene["stats"].get("raw_bounds", {})
    if bounds:
        IDFFile.objects.filter(id__in=[f.id for f in db_files.values()]).update(**bounds)

    db_components = []
    bucket_keys = ["pipes", "fittings", "welds", "supports", "markers"]
    for bucket in bucket_keys:
        for item in combined_scene[bucket]:
            p = item["properties"]
            lines = p.get('pipeline_ref', '')
            db_components.append(IDFComponent(
                idf_file=db_files[p["filename"]],
                project=project,
                uid=p["uid"],
                record_id=p["record_id"],
                kind=p["kind"],
                line_id=lines if len(lines) <= 100 else lines[:100],
                properties=p
            ))
            
    batch_size = 5000
    for i in range(0, len(db_components), batch_size):
        IDFComponent.objects.bulk_create(db_components[i:i+batch_size])

    combined_scene = _strip_internal(combined_scene)
    return combined_scene
