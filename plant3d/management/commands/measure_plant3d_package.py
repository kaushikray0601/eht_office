import json

from django.core.management.base import BaseCommand, CommandError

from plant3d.models import RenderPackage
from plant3d.storage import exists, stat_size


def _safe_stat_size(storage_key):
    if not storage_key or not exists(storage_key):
        return 0
    return stat_size(storage_key)


def _ratio(input_bytes, output_bytes):
    if not input_bytes:
        return None
    return round(output_bytes / input_bytes, 4)


def collect_package_measurement(package):
    tiles = list(package.tiles.order_by("sequence", "id"))
    tile_rows = []
    glb_bytes = 0
    sidecar_bytes = 0
    compression_input_bytes = 0
    compression_output_bytes = 0
    compression_completed_tiles = 0
    compression_failed_tiles = 0
    compression_skipped_tiles = 0

    for tile in tiles:
        tile_bytes = tile.byte_size or _safe_stat_size(tile.storage_key)
        sidecar_key = tile.metadata.get("sidecar_storage_key", "")
        tile_sidecar_bytes = _safe_stat_size(sidecar_key)
        compression = tile.metadata.get("compression", {}) or {}
        status = compression.get("status", "not_recorded")

        if status == "completed":
            compression_completed_tiles += 1
        elif status == "failed":
            compression_failed_tiles += 1
        elif status == "skipped":
            compression_skipped_tiles += 1

        input_bytes = int(compression.get("input_bytes") or 0)
        output_bytes = int(compression.get("output_bytes") or 0)
        compression_input_bytes += input_bytes
        compression_output_bytes += output_bytes
        glb_bytes += tile_bytes
        sidecar_bytes += tile_sidecar_bytes

        tile_rows.append(
            {
                "id": tile.pk,
                "tile_id": tile.tile_id,
                "objects": tile.object_count,
                "geometry_bytes": tile_bytes,
                "sidecar_bytes": tile_sidecar_bytes,
                "compression_status": status,
                "compression_ratio": compression.get("ratio") or _ratio(input_bytes, output_bytes),
            }
        )

    manifest_bytes = _safe_stat_size(package.manifest_storage_key)
    measured_total_bytes = glb_bytes + sidecar_bytes + manifest_bytes
    package_compression = package.metadata.get("meshopt_compression", {}) or {}

    return {
        "package_id": package.pk,
        "source_id": package.source_model_id,
        "source": package.source_model.display_name,
        "project": package.source_model.project_id,
        "format": package.package_format,
        "objects": package.object_count,
        "tiles": package.tile_count,
        "recorded_package_bytes": package.byte_size,
        "measured_total_bytes": measured_total_bytes,
        "geometry_bytes": glb_bytes,
        "sidecar_bytes": sidecar_bytes,
        "manifest_bytes": manifest_bytes,
        "compression": {
            "enabled": package_compression.get("enabled", False),
            "status": package_compression.get("status", "not_recorded"),
            "completed_tiles": compression_completed_tiles,
            "failed_tiles": compression_failed_tiles,
            "skipped_tiles": compression_skipped_tiles,
            "input_bytes": compression_input_bytes,
            "output_bytes": compression_output_bytes,
            "saved_bytes": compression_input_bytes - compression_output_bytes if compression_input_bytes else 0,
            "ratio": _ratio(compression_input_bytes, compression_output_bytes),
        },
        "tile_measurements": tile_rows,
    }


class Command(BaseCommand):
    help = "Measure plant3d render package size and meshopt/gltfpack compression status."

    def add_arguments(self, parser):
        parser.add_argument("package_ids", nargs="*", type=int, help="RenderPackage id(s) to measure.")
        parser.add_argument("--source-id", type=int, help="Measure packages for one SourceModel id.")
        parser.add_argument("--latest", type=int, default=0, help="Measure the latest N render packages.")
        parser.add_argument("--json", action="store_true", help="Write machine-readable JSON.")

    def handle(self, *args, **options):
        package_ids = options["package_ids"]
        source_id = options["source_id"]
        latest = options["latest"]
        use_json = options["json"]

        query = RenderPackage.objects.select_related("source_model", "source_model__project").prefetch_related("tiles")
        if package_ids:
            query = query.filter(pk__in=package_ids)
        elif source_id:
            query = query.filter(source_model_id=source_id)
        elif latest:
            query = query.order_by("-created_at", "-id")[:latest]
        else:
            raise CommandError("Provide package id(s), --source-id, or --latest N.")

        packages = list(query)
        if not packages:
            raise CommandError("No render packages matched the requested filter.")

        measurements = [collect_package_measurement(package) for package in packages]

        if use_json:
            self.stdout.write(json.dumps(measurements, indent=2, sort_keys=True))
            return

        for measurement in measurements:
            self.stdout.write(
                "Package {package_id} | source {source_id} {source!r} | {format} | "
                "{objects} objects | {tiles} tiles".format(**measurement)
            )
            self.stdout.write(
                "  bytes: measured={measured_total_bytes} recorded={recorded_package_bytes} "
                "geometry={geometry_bytes} sidecar={sidecar_bytes} manifest={manifest_bytes}".format(**measurement)
            )
            compression = measurement["compression"]
            ratio = compression["ratio"]
            ratio_text = "n/a" if ratio is None else f"{ratio:.4f}"
            self.stdout.write(
                "  meshopt: status={status} enabled={enabled} completed_tiles={completed_tiles} "
                "skipped_tiles={skipped_tiles} failed_tiles={failed_tiles} "
                "input={input_bytes} output={output_bytes} saved={saved_bytes} ratio={ratio_text}".format(
                    ratio_text=ratio_text,
                    **compression,
                )
            )
            for tile in measurement["tile_measurements"]:
                tile_ratio = tile["compression_ratio"]
                tile_ratio_text = "n/a" if tile_ratio is None else f"{tile_ratio:.4f}"
                self.stdout.write(
                    "    {tile_id}: objects={objects} geometry={geometry_bytes} sidecar={sidecar_bytes} "
                    "compression={compression_status} ratio={ratio}".format(
                        **tile,
                        ratio=tile_ratio_text,
                    )
                )
