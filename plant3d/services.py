import hashlib
import json
import re
import time

from django.db import transaction
from django.utils import timezone

from .glb import build_glb_from_meshes
from .parsers.ifc import parse_multiple_ifc_uploads

from .models import ConversionJob, RenderPackage, RenderTile, SourceModel
from .storage import (
    exists as storage_exists,
    read_bytes,
    render_manifest_storage_key,
    safe_name,
    source_storage_key,
    stat_size,
    write_bytes,
    write_text,
)


IFC_HEADER_MARKERS = ("ISO-10303-21", "FILE_SCHEMA", "IFC")
IFC_UNIT_PREFIX_SCALE_TO_M = {
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
IFC_UNIT_DISPLAY = {
    ("", "METRE"): "m",
    ("MILLI", "METRE"): "mm",
    ("CENTI", "METRE"): "cm",
    ("KILO", "METRE"): "km",
}


def detect_source_format(filename, sample_bytes=b""):
    lower_name = str(filename or "").lower()
    if lower_name.endswith(".ifc"):
        return "IFC"
    if lower_name.endswith(".idf"):
        return "IDF"
    if lower_name.endswith(".pcf"):
        return "PCF"

    try:
        head = sample_bytes[:4096].decode("utf-8", errors="ignore").upper()
    except AttributeError:
        head = str(sample_bytes or "")[:4096].upper()
    if all(marker in head for marker in IFC_HEADER_MARKERS):
        return "IFC"
    if "PIPELINE-REFERENCE" in head or "UNITS-CO-ORDS" in head:
        return "PCF"
    return "OTHER"


def _read_chunks(uploaded_file):
    hasher = hashlib.sha256()
    chunks = []
    size = 0
    for chunk in uploaded_file.chunks():
        hasher.update(chunk)
        chunks.append(chunk)
        size += len(chunk)
    return hasher.hexdigest(), b"".join(chunks), size


def create_source_model_from_upload(project, uploaded_file, display_name="", source_system=""):
    signature, raw, size = _read_chunks(uploaded_file)
    existing = SourceModel.objects.filter(project=project, content_signature=signature).order_by("-created_at").first()
    if existing:
        if not storage_exists(existing.storage_key):
            write_bytes(existing.storage_key, raw)
        return existing

    filename = safe_name(uploaded_file.name)
    source_format = detect_source_format(filename, raw[:4096])
    key = source_storage_key(project.proj_id, signature, filename)
    write_bytes(key, raw)

    return SourceModel.objects.create(
        project=project,
        display_name=(display_name or filename),
        source_format=source_format,
        original_filename=filename,
        storage_key=key,
        content_signature=signature,
        file_size_bytes=size,
        source_system=source_system,
    )


def _source_file_text(source_model, limit_bytes=2_000_000):
    if not storage_exists(source_model.storage_key):
        return ""
    raw = read_bytes(source_model.storage_key, limit_bytes=limit_bytes)
    return raw.decode("utf-8", errors="ignore")


def _ifc_metadata_from_text(text):
    entity_count = 0
    schema = ""
    file_name = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            entity_count += 1
        upper = stripped.upper()
        if upper.startswith("FILE_SCHEMA"):
            schema = stripped[:240]
        elif upper.startswith("FILE_NAME"):
            file_name = stripped[:240]
    return {
        "ifc_entity_count_sample": entity_count,
        "ifc_schema_line": schema,
        "ifc_file_name_line": file_name,
    }


def _ifc_token(value):
    return str(value or "").strip().strip(".").strip("'").upper()


def extract_ifc_unit_hints(text):
    si_units = []
    conversion_units = []
    for match in re.finditer(
        r"#(?P<id>\d+)\s*=\s*IFCSIUNIT\(\s*\*\s*,\s*\.LENGTHUNIT\.\s*,\s*(?P<prefix>\$|\.[A-Z]+\.)\s*,\s*(?P<unit>\.[A-Z_]+\.)\s*\)",
        text,
        flags=re.IGNORECASE,
    ):
        prefix = "" if match.group("prefix") == "$" else _ifc_token(match.group("prefix"))
        unit = _ifc_token(match.group("unit"))
        scale_to_m = IFC_UNIT_PREFIX_SCALE_TO_M.get(prefix, 1.0) if unit == "METRE" else None
        si_units.append(
            {
                "entity_id": f"#{match.group('id')}",
                "prefix": prefix,
                "unit": unit,
                "display_unit": IFC_UNIT_DISPLAY.get((prefix, unit), f"{prefix.lower()} {unit.lower()}".strip()),
                "scale_to_m": scale_to_m,
            }
        )

    for match in re.finditer(
        r"#(?P<id>\d+)\s*=\s*IFCCONVERSIONBASEDUNIT\([^;]*?\.LENGTHUNIT\.\s*,\s*'(?P<name>[^']+)'",
        text,
        flags=re.IGNORECASE,
    ):
        conversion_units.append(
            {
                "entity_id": f"#{match.group('id')}",
                "name": match.group("name").strip(),
            }
        )

    primary = si_units[0] if si_units else {}
    return {
        "length_si_units": si_units[:8],
        "conversion_based_length_units": conversion_units[:8],
        "primary_length_display_unit": primary.get("display_unit", ""),
        "primary_length_scale_to_m": primary.get("scale_to_m"),
        "unit_hint_confidence": "header" if si_units or conversion_units else "",
    }


def _ifc_unit_warnings(unit_hints, parser_stats):
    warnings = []
    parser_unit = str(parser_stats.get("coordinate_unit") or "").upper()
    parser_confidence = str(parser_stats.get("unit_confidence") or "").lower()
    header_scale = unit_hints.get("primary_length_scale_to_m")
    declared_scale = parser_stats.get("ifc_declared_length_scale_to_m")
    declared_unit = parser_stats.get("ifc_declared_length_unit") or unit_hints.get("primary_length_display_unit") or ""
    if header_scale not in (None, 1.0) and parser_unit == "M" and parser_confidence == "assumed":
        warnings.append(
            "IFC header declares a non-metre primary length unit, while parser output reports M/assumed. Verify whether IfcOpenShell normalized coordinates before using measurements."
        )
    if unit_hints.get("conversion_based_length_units") and parser_confidence == "assumed":
        warnings.append(
            "IFC header includes conversion-based length units; measurement/federation should verify source units against rendered coordinates."
        )
    if declared_scale not in (None, 1.0) and parser_unit == "M" and parser_confidence == "ifcopenshell_geometry_si":
        warnings.append(
            f"IFC source declares length unit {declared_unit}, while render geometry is stored in metres from IfcOpenShell. Keep source-declared units and render units separate for measurement/federation."
        )
    return warnings


def _ifc_unit_metadata(unit_hints, parser_stats):
    return {
        "render_coordinate_unit": parser_stats.get("coordinate_unit") or "",
        "render_coordinate_scale_to_m": parser_stats.get("coordinate_scale_to_m"),
        "render_unit_confidence": parser_stats.get("unit_confidence") or "",
        "display_unit": parser_stats.get("display_unit") or "",
        "source_unit_hints": unit_hints,
        "ifc_declared_length_units": parser_stats.get("ifc_declared_length_units") or [],
        "ifc_declared_length_unit": parser_stats.get("ifc_declared_length_unit") or "",
        "ifc_declared_length_unit_name": parser_stats.get("ifc_declared_length_unit_name") or "",
        "ifc_declared_length_unit_entity": parser_stats.get("ifc_declared_length_unit_entity") or "",
        "ifc_declared_length_scale_to_m": parser_stats.get("ifc_declared_length_scale_to_m"),
        "ifc_declared_length_confidence": parser_stats.get("ifc_declared_length_confidence") or "",
        "geometry_unit": parser_stats.get("geometry_unit") or "",
        "geometry_scale_to_m": parser_stats.get("geometry_scale_to_m"),
        "geometry_unit_basis": parser_stats.get("geometry_unit_basis") or "",
        "ifcopenshell_length_unit_setting": parser_stats.get("ifcopenshell_length_unit_setting"),
        "ifcopenshell_convert_back_units": parser_stats.get("ifcopenshell_convert_back_units"),
        "ifcopenshell_geometry_note": parser_stats.get("ifcopenshell_geometry_note") or "",
        "source_files": parser_stats.get("source_files") or [],
    }


def build_metadata_manifest(source_model):
    text = _source_file_text(source_model)
    metadata = {
        "source_model_id": source_model.pk,
        "display_name": source_model.display_name,
        "source_format": source_model.source_format,
        "original_filename": source_model.original_filename,
        "content_signature": source_model.content_signature,
        "file_size_bytes": source_model.file_size_bytes,
        "storage_key": source_model.storage_key,
        "generated_at": timezone.now().isoformat(),
        "conversion_scope": "metadata-only",
    }
    if source_model.source_format == "IFC":
        metadata.update(_ifc_metadata_from_text(text))
        metadata["ifc_unit_hints"] = extract_ifc_unit_hints(text)
    return metadata


def queue_metadata_conversion(source_model, tool_name="plant3d.metadata", tool_version="0.1"):
    return ConversionJob.objects.create(
        source_model=source_model,
        job_type="metadata_index",
        status="queued",
        progress_percent=0,
        tool_name=tool_name,
        tool_version=tool_version,
        input_storage_key=source_model.storage_key,
    )


def queue_ifc_geometry_conversion(source_model, tool_name="plant3d.ifc-json", tool_version="0.1"):
    if source_model.source_format != "IFC":
        raise ValueError("IFC geometry conversion requires an IFC source model.")
    return ConversionJob.objects.create(
        source_model=source_model,
        job_type="render_package",
        status="queued",
        progress_percent=0,
        tool_name=tool_name,
        tool_version=tool_version,
        input_storage_key=source_model.storage_key,
    )


def queue_ifc_glb_conversion(source_model, tool_name="plant3d.ifc-glb", tool_version="0.1"):
    if source_model.source_format != "IFC":
        raise ValueError("IFC GLB conversion requires an IFC source model.")
    return queue_ifc_geometry_conversion(source_model, tool_name=tool_name, tool_version=tool_version)


def _mark_job_running(job, progress_percent):
    job.status = "running"
    job.progress_percent = progress_percent
    job.started_at = job.started_at or timezone.now()
    job.completed_at = None
    job.error_message = ""
    job.save(update_fields=["status", "progress_percent", "started_at", "completed_at", "error_message", "updated_at"])


def run_metadata_conversion(source_model, job=None, tool_name="plant3d.metadata", tool_version="0.1"):
    job = job or queue_metadata_conversion(source_model, tool_name=tool_name, tool_version=tool_version)
    _mark_job_running(job, 10)
    started = time.perf_counter()

    try:
        manifest = build_metadata_manifest(source_model)
        manifest_key = render_manifest_storage_key(source_model.pk)
        manifest_text = json.dumps(manifest, indent=2, sort_keys=True)
        write_text(manifest_key, manifest_text)
        manifest_size = stat_size(manifest_key)

        with transaction.atomic():
            package = RenderPackage.objects.create(
                source_model=source_model,
                conversion_job=job,
                package_format="TILED_JSON",
                storage_prefix=manifest_key.rsplit("/", 1)[0],
                manifest_storage_key=manifest_key,
                object_count=0,
                tile_count=1,
                byte_size=manifest_size,
                coordinate_unit=source_model.declared_unit,
                coordinate_frame=source_model.coordinate_frame,
                bounds=source_model.bounds,
                metadata={"conversion_scope": "metadata-only"},
            )
            RenderTile.objects.create(
                render_package=package,
                tile_id="metadata",
                storage_key=manifest_key,
                sequence=0,
                object_count=0,
                byte_size=manifest_size,
                metadata={"tile_type": "manifest"},
            )

            job.status = "completed"
            job.progress_percent = 100
            job.output_storage_prefix = package.storage_prefix
            job.completed_at = timezone.now()
            job.metrics = {
                "manifest_storage_key": manifest_key,
                "manifest_bytes": manifest_size,
                "conversion_scope": "metadata-only",
                "conversion_duration_ms": round((time.perf_counter() - started) * 1000),
            }
            job.save(update_fields=[
                "status",
                "progress_percent",
                "output_storage_prefix",
                "completed_at",
                "metrics",
                "updated_at",
            ])
        return job, package
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        raise


def _render_tile_storage_key(source_id, tile_id, extension="json"):
    return f"plant3d/render/{source_id}/{tile_id}.{extension}"


def _raw_bounds_center(raw_bounds):
    if not raw_bounds:
        return [0.0, 0.0, 0.0]
    required_keys = ("min_x", "max_x", "min_y", "max_y", "min_z", "max_z")
    try:
        if not all(key in raw_bounds for key in required_keys):
            return [0.0, 0.0, 0.0]
        return [
            (float(raw_bounds["min_x"]) + float(raw_bounds["max_x"])) / 2.0,
            (float(raw_bounds["min_y"]) + float(raw_bounds["max_y"])) / 2.0,
            (float(raw_bounds["min_z"]) + float(raw_bounds["max_z"])) / 2.0,
        ]
    except (TypeError, ValueError):
        return [0.0, 0.0, 0.0]


def _source_to_render_coordinates(source_xyz, scale_to_m=1.0):
    scale = float(scale_to_m or 1.0)
    return [
        float(source_xyz[0]) * scale,
        float(source_xyz[2]) * scale,
        float(source_xyz[1]) * scale,
    ]


def _rtc_origins_from_raw_bounds(raw_bounds, scale_to_m=1.0):
    source_origin = _raw_bounds_center(raw_bounds)
    return source_origin, _source_to_render_coordinates(source_origin, scale_to_m=scale_to_m)


def _mesh_stable_id(source_model, mesh):
    properties = mesh.get("properties") or {}
    global_id = str(properties.get("global_id") or "").strip()
    if global_id:
        return f"ifc:{global_id}"
    return f"{source_model.source_format.lower()}:{source_model.pk}:mesh:{mesh.get('uid')}"


def _index_scene_objects(source_model, package, tile, meshes):
    source_model.model_objects.all().delete()
    objects = []
    for mesh in meshes:
        properties = mesh.get("properties") or {}
        objects.append(
            source_model.model_objects.model(
                source_model=source_model,
                render_package=package,
                render_tile=tile,
                stable_id=_mesh_stable_id(source_model, mesh),
                source_object_id=str(properties.get("global_id") or mesh.get("uid") or ""),
                object_type=str(properties.get("ifc_class") or properties.get("kind") or mesh.get("kind") or ""),
                tag=str(properties.get("tag") or properties.get("component_ref") or ""),
                line_id=str(properties.get("line_id") or ""),
                bounds=properties.get("raw_bounds") or {},
                metadata={
                    "name": properties.get("name") or "",
                    "description": properties.get("description") or "",
                    "hierarchy_group": properties.get("hierarchy_group") or "",
                    "spatial_path": properties.get("spatial_path") or [],
                },
            )
        )
    if objects:
        source_model.model_objects.bulk_create(objects)
    return len(objects)


def run_ifc_geometry_conversion(source_model, tool_name="plant3d.ifc-json", tool_version="0.1"):
    job = None
    return _run_ifc_geometry_conversion(source_model, job=job, tool_name=tool_name, tool_version=tool_version)


def run_ifc_glb_conversion(source_model, tool_name="plant3d.ifc-glb", tool_version="0.1"):
    job = None
    return _run_ifc_glb_conversion(source_model, job=job, tool_name=tool_name, tool_version=tool_version)


def _ifc_scene_context(source_model):
    raw = read_bytes(source_model.storage_key)
    scene = parse_multiple_ifc_uploads([(source_model.original_filename, raw)], source_model.project)
    meshes = scene.get("meshes") or []
    stats = scene.get("stats") or {}
    unit_hints = extract_ifc_unit_hints(raw[:2_000_000].decode("utf-8", errors="ignore"))
    unit_warnings = _ifc_unit_warnings(unit_hints, stats)
    unit_metadata = _ifc_unit_metadata(unit_hints, stats)
    raw_bounds = stats.get("raw_bounds") or {}
    scale_to_m = stats.get("coordinate_scale_to_m")
    origin_source_xyz, rtc_origin_render_xyz = _rtc_origins_from_raw_bounds(raw_bounds, scale_to_m=scale_to_m)
    coordinate_transform = {
        "source_axis_order": ["x", "y", "z"],
        "render_axis_order": ["x", "z", "y"],
        "origin_source_xyz": origin_source_xyz,
        "rtc_origin_render_xyz": rtc_origin_render_xyz,
        "scale_to_m": scale_to_m,
        "local_position_frame": "render_xyz_m_relative_to_rtc_origin_render_xyz",
        "render_world_formula": "render_world_xyz_m = rtc_origin_render_xyz + local_position_xyz_m",
        "source_reconstruction_formula": "source_xyz = [render_world.x/scale, render_world.z/scale, render_world.y/scale]",
        "note": "IFC vertices are local render-frame coordinates produced by axis swap and scale after subtracting the source bbox center.",
    }
    return {
        "raw": raw,
        "scene": scene,
        "meshes": meshes,
        "stats": stats,
        "unit_hints": unit_hints,
        "unit_warnings": unit_warnings,
        "unit_metadata": unit_metadata,
        "raw_bounds": raw_bounds,
        "scale_to_m": scale_to_m,
        "origin_source_xyz": origin_source_xyz,
        "rtc_origin_render_xyz": rtc_origin_render_xyz,
        "coordinate_transform": coordinate_transform,
    }


def _run_ifc_geometry_conversion(source_model, job=None, tool_name="plant3d.ifc-json", tool_version="0.1"):
    if source_model.source_format != "IFC":
        raise ValueError("IFC geometry conversion requires an IFC source model.")

    job = job or queue_ifc_geometry_conversion(source_model, tool_name=tool_name, tool_version=tool_version)
    _mark_job_running(job, 5)
    started = time.perf_counter()

    try:
        context = _ifc_scene_context(source_model)
        meshes = context["meshes"]
        stats = context["stats"]
        unit_hints = context["unit_hints"]
        unit_warnings = context["unit_warnings"]
        unit_metadata = context["unit_metadata"]
        raw_bounds = context["raw_bounds"]
        origin_source_xyz = context["origin_source_xyz"]
        rtc_origin_render_xyz = context["rtc_origin_render_xyz"]
        tile_key = _render_tile_storage_key(source_model.pk, "geometry-0001", "json")
        tile_payload = {
            "package_version": 1,
            "tile_id": "geometry-0001",
            "source_model_id": source_model.pk,
            "source_format": source_model.source_format,
            "coordinate_unit": stats.get("coordinate_unit") or "",
            "coordinate_scale_to_m": stats.get("coordinate_scale_to_m"),
            "display_unit": stats.get("display_unit") or "",
            "unit_confidence": stats.get("unit_confidence") or "",
            "source_unit_hints": unit_hints,
            "unit_metadata": unit_metadata,
            "unit_warnings": unit_warnings,
            "raw_bounds": raw_bounds,
            "rtc_origin": rtc_origin_render_xyz,
            "rtc_origin_frame": "render_xyz_m",
            "coordinate_transform": context["coordinate_transform"],
            "meshes": meshes,
        }
        tile_text = json.dumps(tile_payload, separators=(",", ":"))
        write_text(tile_key, tile_text)
        tile_size = stat_size(tile_key)

        with transaction.atomic():
            package = RenderPackage.objects.create(
                source_model=source_model,
                conversion_job=job,
                package_format="TILED_JSON",
                storage_prefix=f"plant3d/render/{source_model.pk}",
                manifest_storage_key=tile_key,
                object_count=len(meshes),
                tile_count=1,
                byte_size=tile_size,
                coordinate_unit=stats.get("coordinate_unit") or "",
                coordinate_frame=source_model.coordinate_frame,
                bounds=raw_bounds,
                metadata={
                    "conversion_scope": "ifc-geometry-json",
                    "display_unit": stats.get("display_unit") or "",
                    "unit_confidence": stats.get("unit_confidence") or "",
                    "source_unit_hints": unit_hints,
                    "unit_metadata": unit_metadata,
                    "unit_warnings": unit_warnings,
                    "origin_source_xyz": origin_source_xyz,
                    "rtc_origin_render_xyz": rtc_origin_render_xyz,
                },
            )
            tile = RenderTile.objects.create(
                render_package=package,
                tile_id="geometry-0001",
                storage_key=tile_key,
                sequence=1,
                rtc_origin_x=rtc_origin_render_xyz[0],
                rtc_origin_y=rtc_origin_render_xyz[1],
                rtc_origin_z=rtc_origin_render_xyz[2],
                object_count=len(meshes),
                byte_size=tile_size,
                bounds=raw_bounds,
                metadata={
                    "tile_type": "ifc-geometry-json",
                    "coordinate_transform": tile_payload["coordinate_transform"],
                    "source_unit_hints": unit_hints,
                    "unit_metadata": unit_metadata,
                    "unit_warnings": unit_warnings,
                },
            )
            indexed_count = _index_scene_objects(source_model, package, tile, meshes)

            source_model.declared_unit = source_model.declared_unit or (
                str(stats.get("ifc_declared_length_unit") or stats.get("coordinate_unit") or "").upper()
            )
            source_model.bounds = raw_bounds or source_model.bounds
            source_model.metadata = {
                **(source_model.metadata or {}),
                "last_geometry_conversion_job_id": job.pk,
                "ifc_mesh_count": len(meshes),
                "model_object_count": indexed_count,
                "ifc_unit_hints": unit_hints,
                "ifc_unit_metadata": unit_metadata,
                "ifc_unit_warnings": unit_warnings,
                "last_origin_source_xyz": origin_source_xyz,
                "last_rtc_origin_render_xyz": rtc_origin_render_xyz,
            }
            source_model.save(update_fields=["declared_unit", "bounds", "metadata", "updated_at"])

            job.status = "completed"
            job.progress_percent = 100
            job.output_storage_prefix = package.storage_prefix
            job.completed_at = timezone.now()
            job.metrics = {
                "tile_storage_key": tile_key,
                "tile_bytes": tile_size,
                "mesh_count": len(meshes),
                "model_object_count": indexed_count,
                "conversion_scope": "ifc-geometry-json",
                "conversion_duration_ms": round((time.perf_counter() - started) * 1000),
                "source_unit_hints": unit_hints,
                "unit_metadata": unit_metadata,
                "unit_warnings": unit_warnings,
            }
            job.save(update_fields=[
                "status",
                "progress_percent",
                "output_storage_prefix",
                "completed_at",
                "metrics",
                "updated_at",
            ])
        return job, package
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        raise


def _run_ifc_glb_conversion(source_model, job=None, tool_name="plant3d.ifc-glb", tool_version="0.1"):
    if source_model.source_format != "IFC":
        raise ValueError("IFC GLB conversion requires an IFC source model.")

    job = job or queue_ifc_glb_conversion(source_model, tool_name=tool_name, tool_version=tool_version)
    _mark_job_running(job, 5)
    started = time.perf_counter()

    try:
        context = _ifc_scene_context(source_model)
        meshes = context["meshes"]
        stats = context["stats"]
        unit_hints = context["unit_hints"]
        unit_warnings = context["unit_warnings"]
        unit_metadata = context["unit_metadata"]
        raw_bounds = context["raw_bounds"]
        origin_source_xyz = context["origin_source_xyz"]
        rtc_origin_render_xyz = context["rtc_origin_render_xyz"]
        tile_id = "geometry-0001"
        glb_key = _render_tile_storage_key(source_model.pk, tile_id, "glb")
        sidecar_key = _render_tile_storage_key(source_model.pk, f"{tile_id}-metadata", "json")
        glb_metadata = {
            "package_version": 1,
            "tile_id": tile_id,
            "source_model_id": source_model.pk,
            "source_format": source_model.source_format,
            "coordinate_unit": stats.get("coordinate_unit") or "",
            "coordinate_scale_to_m": stats.get("coordinate_scale_to_m"),
            "display_unit": stats.get("display_unit") or "",
            "unit_confidence": stats.get("unit_confidence") or "",
            "unit_metadata": unit_metadata,
            "unit_warnings": unit_warnings,
            "raw_bounds": raw_bounds,
            "rtc_origin": rtc_origin_render_xyz,
            "rtc_origin_frame": "render_xyz_m",
            "coordinate_transform": context["coordinate_transform"],
        }
        glb_bytes, sidecar = build_glb_from_meshes(meshes, metadata=glb_metadata)
        sidecar.update(
            {
                "tile_id": tile_id,
                "source_model_id": source_model.pk,
                "glb_storage_key": glb_key,
                "sidecar_storage_key": sidecar_key,
                "coordinate_transform": context["coordinate_transform"],
                "unit_metadata": unit_metadata,
                "unit_warnings": unit_warnings,
                "raw_bounds": raw_bounds,
            }
        )
        write_bytes(glb_key, glb_bytes)
        write_text(sidecar_key, json.dumps(sidecar, separators=(",", ":")))
        glb_size = stat_size(glb_key)
        sidecar_size = stat_size(sidecar_key)

        with transaction.atomic():
            package = RenderPackage.objects.create(
                source_model=source_model,
                conversion_job=job,
                package_format="GLB",
                storage_prefix=f"plant3d/render/{source_model.pk}",
                manifest_storage_key=sidecar_key,
                object_count=len(meshes),
                tile_count=1,
                byte_size=glb_size + sidecar_size,
                coordinate_unit=stats.get("coordinate_unit") or "",
                coordinate_frame=source_model.coordinate_frame,
                bounds=raw_bounds,
                metadata={
                    "conversion_scope": "ifc-glb",
                    "display_unit": stats.get("display_unit") or "",
                    "unit_confidence": stats.get("unit_confidence") or "",
                    "source_unit_hints": unit_hints,
                    "unit_metadata": unit_metadata,
                    "unit_warnings": unit_warnings,
                    "origin_source_xyz": origin_source_xyz,
                    "rtc_origin_render_xyz": rtc_origin_render_xyz,
                    "glb_storage_key": glb_key,
                    "sidecar_storage_key": sidecar_key,
                    "render_batch_count": sidecar["render_batch_count"],
                    "picking_strategy": "metadata-sidecar-only; GLB object picking deferred until feature IDs are designed",
                },
            )
            tile = RenderTile.objects.create(
                render_package=package,
                tile_id=tile_id,
                storage_key=glb_key,
                sequence=1,
                rtc_origin_x=rtc_origin_render_xyz[0],
                rtc_origin_y=rtc_origin_render_xyz[1],
                rtc_origin_z=rtc_origin_render_xyz[2],
                object_count=len(meshes),
                byte_size=glb_size,
                bounds=raw_bounds,
                metadata={
                    "tile_type": "ifc-glb",
                    "sidecar_storage_key": sidecar_key,
                    "sidecar_bytes": sidecar_size,
                    "coordinate_transform": context["coordinate_transform"],
                    "source_unit_hints": unit_hints,
                    "unit_metadata": unit_metadata,
                    "unit_warnings": unit_warnings,
                    "render_batch_count": sidecar["render_batch_count"],
                },
            )
            indexed_count = _index_scene_objects(source_model, package, tile, meshes)

            source_model.declared_unit = source_model.declared_unit or (
                str(stats.get("ifc_declared_length_unit") or stats.get("coordinate_unit") or "").upper()
            )
            source_model.bounds = raw_bounds or source_model.bounds
            source_model.metadata = {
                **(source_model.metadata or {}),
                "last_glb_conversion_job_id": job.pk,
                "ifc_mesh_count": len(meshes),
                "model_object_count": indexed_count,
                "ifc_unit_hints": unit_hints,
                "ifc_unit_metadata": unit_metadata,
                "ifc_unit_warnings": unit_warnings,
                "last_origin_source_xyz": origin_source_xyz,
                "last_rtc_origin_render_xyz": rtc_origin_render_xyz,
                "last_glb_storage_key": glb_key,
                "last_glb_sidecar_storage_key": sidecar_key,
            }
            source_model.save(update_fields=["declared_unit", "bounds", "metadata", "updated_at"])

            job.status = "completed"
            job.progress_percent = 100
            job.output_storage_prefix = package.storage_prefix
            job.completed_at = timezone.now()
            job.metrics = {
                "glb_storage_key": glb_key,
                "glb_bytes": glb_size,
                "sidecar_storage_key": sidecar_key,
                "sidecar_bytes": sidecar_size,
                "mesh_count": len(meshes),
                "render_batch_count": sidecar["render_batch_count"],
                "model_object_count": indexed_count,
                "conversion_scope": "ifc-glb",
                "conversion_duration_ms": round((time.perf_counter() - started) * 1000),
                "source_unit_hints": unit_hints,
                "unit_metadata": unit_metadata,
                "unit_warnings": unit_warnings,
            }
            job.save(update_fields=[
                "status",
                "progress_percent",
                "output_storage_prefix",
                "completed_at",
                "metrics",
                "updated_at",
            ])
        return job, package
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        raise


def execute_conversion_job(job):
    if job.status not in {"queued", "failed"}:
        raise ValueError(f"Conversion job {job.pk} is not queued or failed.")

    source_model = job.source_model
    if job.job_type == "metadata_index":
        return run_metadata_conversion(source_model, job=job)
    if job.job_type == "render_package":
        if source_model.source_format == "IFC":
            if job.tool_name == "plant3d.ifc-glb":
                return _run_ifc_glb_conversion(source_model, job=job)
            return _run_ifc_geometry_conversion(source_model, job=job)
        raise ValueError(f"Render package conversion is not implemented for {source_model.source_format}.")
    raise ValueError(f"Unsupported conversion job type: {job.job_type}")
