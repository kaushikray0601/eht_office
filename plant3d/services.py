import hashlib
import json
from pathlib import Path

from django.utils import timezone

from idfviewer.ifc_parser import IFCDependencyError, IFCParseError, parse_multiple_ifc_uploads

from .models import ConversionJob, RenderPackage, RenderTile, SourceModel
from .storage import (
    path_for_storage_key,
    render_manifest_storage_key,
    safe_name,
    source_storage_key,
    write_text,
)


IFC_HEADER_MARKERS = ("ISO-10303-21", "FILE_SCHEMA", "IFC")


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
    filename = safe_name(uploaded_file.name)
    source_format = detect_source_format(filename, raw[:4096])
    key = source_storage_key(project.proj_id, signature, filename)
    path = path_for_storage_key(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)

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
    path = path_for_storage_key(source_model.storage_key)
    if not path.exists():
        return ""
    with path.open("rb") as handle:
        raw = handle.read(limit_bytes)
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
    return metadata


def run_metadata_conversion(source_model, tool_name="plant3d.metadata", tool_version="0.1"):
    job = ConversionJob.objects.create(
        source_model=source_model,
        status="running",
        progress_percent=10,
        tool_name=tool_name,
        tool_version=tool_version,
        input_storage_key=source_model.storage_key,
        started_at=timezone.now(),
    )

    try:
        manifest = build_metadata_manifest(source_model)
        manifest_key = render_manifest_storage_key(source_model.pk)
        manifest_text = json.dumps(manifest, indent=2, sort_keys=True)
        write_text(manifest_key, manifest_text)
        manifest_size = Path(path_for_storage_key(manifest_key)).stat().st_size

        package = RenderPackage.objects.create(
            source_model=source_model,
            conversion_job=job,
            package_format="TILED_JSON",
            storage_prefix=str(Path(manifest_key).parent).replace("\\", "/"),
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


def _render_tile_storage_key(source_id, tile_id):
    return f"plant3d/render/{source_id}/{tile_id}.json"


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
    if source_model.source_format != "IFC":
        raise ValueError("IFC geometry conversion requires an IFC source model.")

    source_path = path_for_storage_key(source_model.storage_key)
    raw = source_path.read_bytes()

    job = ConversionJob.objects.create(
        source_model=source_model,
        status="running",
        progress_percent=5,
        tool_name=tool_name,
        tool_version=tool_version,
        input_storage_key=source_model.storage_key,
        started_at=timezone.now(),
    )

    try:
        scene = parse_multiple_ifc_uploads([(source_model.original_filename, raw)], source_model.project)
        meshes = scene.get("meshes") or []
        stats = scene.get("stats") or {}
        tile_key = _render_tile_storage_key(source_model.pk, "geometry-0001")
        tile_payload = {
            "package_version": 1,
            "tile_id": "geometry-0001",
            "source_model_id": source_model.pk,
            "source_format": source_model.source_format,
            "coordinate_unit": stats.get("coordinate_unit") or "",
            "coordinate_scale_to_m": stats.get("coordinate_scale_to_m"),
            "display_unit": stats.get("display_unit") or "",
            "unit_confidence": stats.get("unit_confidence") or "",
            "raw_bounds": stats.get("raw_bounds") or {},
            "rtc_origin": [0.0, 0.0, 0.0],
            "meshes": meshes,
        }
        tile_text = json.dumps(tile_payload, separators=(",", ":"))
        write_text(tile_key, tile_text)
        tile_size = Path(path_for_storage_key(tile_key)).stat().st_size

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
            bounds=stats.get("raw_bounds") or {},
            metadata={
                "conversion_scope": "ifc-geometry-json",
                "display_unit": stats.get("display_unit") or "",
                "unit_confidence": stats.get("unit_confidence") or "",
            },
        )
        tile = RenderTile.objects.create(
            render_package=package,
            tile_id="geometry-0001",
            storage_key=tile_key,
            sequence=1,
            object_count=len(meshes),
            byte_size=tile_size,
            bounds=stats.get("raw_bounds") or {},
            metadata={"tile_type": "ifc-geometry-json"},
        )
        indexed_count = _index_scene_objects(source_model, package, tile, meshes)

        source_model.declared_unit = source_model.declared_unit or (stats.get("coordinate_unit") or "")
        source_model.bounds = stats.get("raw_bounds") or source_model.bounds
        source_model.metadata = {
            **(source_model.metadata or {}),
            "last_geometry_conversion_job_id": job.pk,
            "ifc_mesh_count": len(meshes),
            "model_object_count": indexed_count,
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
    except (IFCDependencyError, IFCParseError, Exception) as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        raise
