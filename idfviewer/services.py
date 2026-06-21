import hashlib
import json
from copy import deepcopy

from django.db import transaction
from django.utils import timezone

from .models import IDFComponent, IDFFile, IDFFileSaveEvent
from .units import coordinate_unit_stats, normalize_unit


SCENE_BUCKETS = ("pipes", "fittings", "welds", "supports", "markers")
SEGMENT_BUCKETS = {"pipes", "fittings"}
POINT_BUCKETS = {"welds", "supports", "markers"}
COUNT_FIELD_MAP = {
    "pipes": "pipe_count",
    "fittings": "fitting_count",
    "welds": "weld_count",
    "supports": "support_count",
    "markers": "marker_count",
}
PIPE_RECORD_IDS = {100, 101, 102, 103}
WELD_RECORD_IDS = {120}
SUPPORT_RECORD_IDS = {150}
MARKER_RECORD_IDS = {149}


def empty_counts():
    return {bucket: 0 for bucket in SCENE_BUCKETS}


def infer_scene_bucket(record_id=None, kind="", properties=None):
    props = properties or {}

    if props.get("raw_start") is not None and props.get("raw_end") is not None:
        if record_id in PIPE_RECORD_IDS:
            return "pipes"
        if str(kind).strip().lower() in {
            "pipe",
            "fixed pipe",
            "pipe block fixed",
            "pipe block variable",
        }:
            return "pipes"
        return "fittings"

    if props.get("raw_point") is not None:
        if record_id in WELD_RECORD_IDS or str(kind).strip().lower() == "weld":
            return "welds"
        if record_id in SUPPORT_RECORD_IDS or "support" in str(kind).strip().lower():
            return "supports"
        if record_id in MARKER_RECORD_IDS:
            return "markers"
        return "markers"

    if record_id in PIPE_RECORD_IDS:
        return "pipes"
    if record_id in WELD_RECORD_IDS:
        return "welds"
    if record_id in SUPPORT_RECORD_IDS:
        return "supports"
    if record_id in MARKER_RECORD_IDS:
        return "markers"
    return "fittings"


def _iter_raw_points(properties):
    for key in ("raw_start", "raw_end", "raw_point"):
        point = properties.get(key)
        if isinstance(point, list) and len(point) >= 3:
            yield point


def _normalize_signature_entry(bucket, item):
    properties = deepcopy(item.get("properties") or {})
    properties.pop("scene_bucket", None)
    return {
        "bucket": bucket,
        "uid": item.get("uid") or properties.get("uid") or 0,
        "record_id": item.get("record_id") or properties.get("record_id") or 0,
        "kind": item.get("kind") or properties.get("kind") or "",
        "properties": properties,
    }


def _signature_for_entries(entries):
    normalized = [
        _normalize_signature_entry(entry["bucket"], entry["item"])
        for entry in sorted(
            entries,
            key=lambda entry: (
                entry["item"].get("uid")
                or (entry["item"].get("properties") or {}).get("uid")
                or 0,
                entry["item"].get("record_id")
                or (entry["item"].get("properties") or {}).get("record_id")
                or 0,
                entry["bucket"],
            ),
        )
    ]
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _bounds_from_points(points):
    points = list(points)
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


def summarize_scene_by_file(scene):
    groups = {}
    source_format = ((scene.get("stats") or {}).get("source_format") or "").upper() or "IDF"

    for bucket in SCENE_BUCKETS:
        for item in scene.get(bucket, []) or []:
            properties = deepcopy(item.get("properties") or {})
            filename = properties.get("filename") or "Unknown File"
            group = groups.setdefault(
                filename,
                {
                    "filename": filename,
                    "source_format": properties.get("source_format", source_format) or source_format,
                    "entries": [],
                    "counts": empty_counts(),
                    "points": [],
                },
            )

            properties["scene_bucket"] = bucket
            group["entries"].append(
                {
                    "bucket": bucket,
                    "item": {
                        "uid": item.get("uid") or properties.get("uid") or 0,
                        "record_id": item.get("record_id") or properties.get("record_id") or 0,
                        "kind": item.get("kind") or properties.get("kind") or "",
                        "properties": properties,
                    },
                }
            )
            group["counts"][bucket] += 1
            group["points"].extend(_iter_raw_points(properties))

    summaries = []
    for group in groups.values():
        group["component_count"] = sum(group["counts"].values())
        group["bounds"] = _bounds_from_points(group.pop("points", []))
        group["signature"] = _signature_for_entries(group["entries"])
        summaries.append(group)
    return summaries


def _counts_from_component_queryset(components):
    counts = empty_counts()
    for component in components.only("scene_bucket"):
        bucket = component.scene_bucket or infer_scene_bucket(component.record_id, component.kind, component.properties)
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def file_counts(file_obj):
    if file_obj.component_count:
        return file_obj.count_breakdown()
    return _counts_from_component_queryset(file_obj.components.all())


def _coordinate_unit_from_saved_scene(scene, source_format):
    if source_format == "IFC":
        return "M", "assumed"
    if source_format == "IDF":
        return "MM", "assumed"

    units = set()
    for bucket in SCENE_BUCKETS:
        for item in scene.get(bucket, []) or []:
            properties = item.get("properties") or {}
            metadata = properties.get("pipeline_metadata") or {}
            unit = metadata.get("UNITS-CO-ORDS")
            if isinstance(unit, list):
                unit = unit[0] if unit else ""
            if unit:
                units.add(normalize_unit(unit, default="MM"))

    if len(units) == 1:
        return next(iter(units)), "declared"
    if len(units) > 1:
        return "MM", "mixed_or_missing"
    return "MM", "assumed"


def _summary_to_response(file_obj):
    return {
        "id": file_obj.id,
        "filename": file_obj.filename,
        "source_format": file_obj.source_format,
        "component_count": file_obj.component_count or file_obj.components.count(),
        "counts": file_counts(file_obj),
        "saved_at": (file_obj.saved_at_display.isoformat() if file_obj.saved_at_display else ""),
    }


def _apply_summary_to_file(file_obj, summary, saved_at):
    file_obj.source_format = summary["source_format"]
    file_obj.last_saved_at = saved_at
    file_obj.content_signature = summary["signature"]
    file_obj.component_count = summary["component_count"]
    for bucket, field_name in COUNT_FIELD_MAP.items():
        setattr(file_obj, field_name, summary["counts"].get(bucket, 0))
    for key, value in summary["bounds"].items():
        setattr(file_obj, key, value)


def _component_rows(file_obj, project, summary):
    rows = []
    for entry in summary["entries"]:
        item = entry["item"]
        properties = deepcopy(item.get("properties") or {})
        bucket = entry["bucket"]
        properties["scene_bucket"] = bucket
        line_id = properties.get("pipeline_ref") or properties.get("spool_ref") or ""
        rows.append(
            IDFComponent(
                idf_file=file_obj,
                project=project,
                uid=item.get("uid") or 0,
                record_id=item.get("record_id") or 0,
                kind=item.get("kind") or properties.get("kind") or "",
                source_format=summary["source_format"],
                scene_bucket=bucket,
                line_id=line_id[:100],
                properties=properties,
            )
        )
    return rows


def persist_preview_scene(project, scene, force=False):
    results = {
        "created": [],
        "replaced": [],
        "refreshed": [],
        "conflicts": [],
    }

    for summary in summarize_scene_by_file(scene):
        existing_files = list(
            IDFFile.objects.filter(
                project=project,
                filename=summary["filename"],
                source_format=summary["source_format"],
            ).order_by("-last_saved_at", "-uploaded_at", "-pk")
        )
        current_file = existing_files[0] if existing_files else None
        duplicates = existing_files[1:]

        if current_file and current_file.content_signature == summary["signature"]:
            _apply_summary_to_file(current_file, summary, timezone.now())
            current_file.save()
            if duplicates:
                IDFFile.objects.filter(pk__in=[file_obj.pk for file_obj in duplicates]).delete()
            results["refreshed"].append(_summary_to_response(current_file))
            continue

        if current_file and not force:
            existing_counts = file_counts(current_file)
            results["conflicts"].append(
                {
                    "id": current_file.id,
                    "filename": current_file.filename,
                    "source_format": current_file.source_format,
                    "existing_component_count": current_file.component_count or current_file.components.count(),
                    "new_component_count": summary["component_count"],
                    "existing_counts": existing_counts,
                    "new_counts": summary["counts"],
                    "saved_at": (
                        current_file.saved_at_display.isoformat()
                        if current_file.saved_at_display
                        else ""
                    ),
                    "count_mismatch": (
                        (current_file.component_count or current_file.components.count())
                        != summary["component_count"]
                    ),
                    "duplicate_record_count": len(duplicates),
                }
            )
            continue

        with transaction.atomic():
            now = timezone.now()
            if current_file is None:
                current_file = IDFFile(project=project, filename=summary["filename"])
                action = "created"
                previous_component_count = 0
                previous_counts = empty_counts()
                previous_signature = ""
            else:
                action = "replaced"
                previous_component_count = current_file.component_count or current_file.components.count()
                previous_counts = file_counts(current_file)
                previous_signature = current_file.content_signature
                current_file.components.all().delete()

            _apply_summary_to_file(current_file, summary, now)
            current_file.save()

            if duplicates:
                IDFFile.objects.filter(pk__in=[file_obj.pk for file_obj in duplicates]).delete()

            rows = _component_rows(current_file, project, summary)
            if rows:
                IDFComponent.objects.bulk_create(rows, batch_size=5000)

            IDFFileSaveEvent.objects.create(
                idf_file=current_file,
                project=project,
                action=action,
                previous_component_count=previous_component_count,
                component_count=summary["component_count"],
                previous_counts=previous_counts,
                current_counts=summary["counts"],
                previous_signature=previous_signature,
                current_signature=summary["signature"],
            )

            results[action].append(_summary_to_response(current_file))

    return results


def _normalize_scene(scene):
    all_points = []
    for bucket in SEGMENT_BUCKETS:
        for item in scene[bucket]:
            all_points.append(tuple(item["start_raw"]))
            all_points.append(tuple(item["end_raw"]))
    for bucket in POINT_BUCKETS:
        for item in scene[bucket]:
            all_points.append(tuple(item["point_raw"]))

    scene["stats"] = scene.get("stats") or {}
    scene["stats"].update(
        {
            "pipe_count": len(scene["pipes"]),
            "fitting_count": len(scene["fittings"]),
            "weld_count": len(scene["welds"]),
            "support_count": len(scene["supports"]),
            "marker_count": len(scene["markers"]),
        }
    )
    scene["stats"]["parsed_records"] = sum(scene["stats"][f"{name}_count"] for name in ("pipe", "fitting", "weld", "support", "marker"))
    unit, confidence = _coordinate_unit_from_saved_scene(
        scene,
        str(scene["stats"].get("source_format") or "IDF").upper(),
    )
    scene["stats"].update(
        coordinate_unit_stats(
            str(scene["stats"].get("source_format") or "IDF").upper(),
            unit,
            confidence,
        )
    )

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
    scale = scene["stats"]["coordinate_scale_to_m"]

    def tx(point):
        return [(point[0] - cx) * scale, (point[2] - cz) * scale, (point[1] - cy) * scale]

    for bucket in SEGMENT_BUCKETS:
        for item in scene[bucket]:
            item["start"] = tx(item["start_raw"])
            item["end"] = tx(item["end_raw"])

    for bucket in POINT_BUCKETS:
        for item in scene[bucket]:
            item["point"] = tx(item["point_raw"])

    scene["stats"]["scale_factor"] = scale
    scene["stats"]["raw_bounds"] = {
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
        "min_z": min_z,
        "max_z": max_z,
    }
    return scene


def _strip_internal(scene):
    for bucket in SEGMENT_BUCKETS:
        for item in scene[bucket]:
            item.pop("start_raw", None)
            item.pop("end_raw", None)
    for bucket in POINT_BUCKETS:
        for item in scene[bucket]:
            item.pop("point_raw", None)
    return scene


def build_scene_from_saved_file(file_obj):
    scene = {
        "pipes": [],
        "fittings": [],
        "welds": [],
        "supports": [],
        "markers": [],
        "stats": {
            "total_lines": 0,
            "source_format": file_obj.source_format,
            "source_label": f"Saved {file_obj.source_format} Scene",
        },
    }

    components = file_obj.components.order_by("uid", "pk")
    for component in components:
        properties = deepcopy(component.properties or {})
        bucket = component.scene_bucket or infer_scene_bucket(component.record_id, component.kind, properties)
        item = {
            "uid": component.uid,
            "record_id": component.record_id,
            "kind": component.kind,
            "properties": properties,
        }

        if bucket in SEGMENT_BUCKETS:
            start = properties.get("raw_start")
            end = properties.get("raw_end")
            if not (isinstance(start, list) and isinstance(end, list)):
                continue
            item["start_raw"] = start
            item["end_raw"] = end
        else:
            point = properties.get("raw_point")
            if not isinstance(point, list):
                continue
            item["point_raw"] = point

        scene[bucket].append(item)

    return _strip_internal(_normalize_scene(scene))


def build_download_payload(file_obj):
    return {
        "id": file_obj.id,
        "project_id": file_obj.project.proj_id,
        "filename": file_obj.filename,
        "source_format": file_obj.source_format,
        "saved_at": file_obj.saved_at_display.isoformat() if file_obj.saved_at_display else "",
        "component_count": file_obj.component_count or file_obj.components.count(),
        "counts": file_counts(file_obj),
        "bounds": {
            "min_x": file_obj.min_x,
            "max_x": file_obj.max_x,
            "min_y": file_obj.min_y,
            "max_y": file_obj.max_y,
            "min_z": file_obj.min_z,
            "max_z": file_obj.max_z,
        },
        "components": [
            {
                "uid": component.uid,
                "record_id": component.record_id,
                "kind": component.kind,
                "scene_bucket": component.scene_bucket or infer_scene_bucket(component.record_id, component.kind, component.properties),
                "line_id": component.line_id,
                "properties": component.properties,
            }
            for component in file_obj.components.order_by("uid", "pk")
        ],
    }
