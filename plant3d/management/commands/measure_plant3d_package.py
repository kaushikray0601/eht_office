import json

from django.core.management.base import BaseCommand, CommandError

from plant3d.models import RenderPackage
from plant3d.storage import exists, stat_size

TIMING_LABELS = [
    ("source_read_ms", "source read"),
    ("parse_ms", "IFC parse"),
    ("context_metadata_ms", "metadata"),
    ("tile_grouping_ms", "tile grouping"),
    ("tile_prepare_ms", "tile prep"),
    ("json_build_ms", "JSON build"),
    ("glb_build_ms", "GLB build"),
    ("meshopt_hook_ms", "meshopt hook"),
    ("feature_id_validation_ms", "feature ID validation"),
    ("tile_write_ms", "tile write"),
    ("tileset_write_ms", "tileset write"),
    ("db_write_ms", "DB/index write"),
]


def _safe_stat_size(storage_key):
    if not storage_key or not exists(storage_key):
        return 0
    return stat_size(storage_key)


def _ratio(input_bytes, output_bytes):
    if not input_bytes:
        return None
    return round(output_bytes / input_bytes, 4)


def _saved_percent(input_bytes, output_bytes):
    if not input_bytes:
        return None
    return round((input_bytes - output_bytes) * 100 / input_bytes, 1)


def _safe_timing_ms(value):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def collect_timing_breakdown(timings):
    timing_rows = []
    for key, label in TIMING_LABELS:
        if key not in (timings or {}):
            continue
        timing_rows.append({"key": key, "label": label, "ms": _safe_timing_ms(timings.get(key))})
    total_ms = sum(row["ms"] for row in timing_rows)
    for row in timing_rows:
        row["percent"] = round(row["ms"] * 100 / total_ms, 1) if total_ms else None
    dominant = max(timing_rows, key=lambda row: row["ms"], default=None)
    return {
        "total_ms": total_ms,
        "dominant_key": dominant["key"] if dominant else "",
        "dominant_label": dominant["label"] if dominant else "",
        "dominant_ms": dominant["ms"] if dominant else 0,
        "dominant_percent": dominant["percent"] if dominant else None,
        "stages": timing_rows,
    }


def collect_aggregate_timing_breakdown(measurements):
    aggregate = {}
    for measurement in measurements:
        for key, value in (measurement.get("conversion_timings") or {}).items():
            aggregate[key] = aggregate.get(key, 0) + _safe_timing_ms(value)
    return collect_timing_breakdown(aggregate)


def collect_package_measurement(package):
    tiles = list(package.tiles.order_by("sequence", "id"))
    tile_rows = []
    glb_bytes = 0
    sidecar_bytes = 0
    compression_input_bytes = 0
    compression_output_bytes = 0
    compression_duration_ms = 0
    compression_completed_tiles = 0
    compression_failed_tiles = 0
    compression_rejected_tiles = 0
    compression_skipped_tiles = 0

    for tile in tiles:
        tile_bytes = tile.byte_size or _safe_stat_size(tile.storage_key)
        sidecar_key = tile.metadata.get("sidecar_storage_key", "")
        tile_sidecar_bytes = _safe_stat_size(sidecar_key)
        compression = tile.metadata.get("compression", {}) or {}
        status = compression.get("status", "not_recorded")

        if status == "completed":
            compression_completed_tiles += 1
            input_bytes = int(compression.get("input_bytes") or 0)
            output_bytes = int(compression.get("output_bytes") or 0)
            compression_input_bytes += input_bytes
            compression_output_bytes += output_bytes
        elif status == "failed":
            compression_failed_tiles += 1
        elif status == "rejected_feature_id_validation":
            compression_rejected_tiles += 1
        elif status == "skipped":
            compression_skipped_tiles += 1

        input_bytes = int(compression.get("input_bytes") or 0)
        output_bytes = int(compression.get("output_bytes") or 0)
        compression_duration_ms += int(compression.get("duration_ms") or 0)
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
                "compression_duration_ms": compression.get("duration_ms"),
                "compression_input_bytes": input_bytes,
                "compression_output_bytes": output_bytes,
                "compression_ratio": compression.get("ratio") if status == "completed" else None,
                "compression_saved_percent": _saved_percent(input_bytes, output_bytes) if status == "completed" else None,
            }
        )

    manifest_bytes = _safe_stat_size(package.manifest_storage_key)
    measured_total_bytes = glb_bytes + sidecar_bytes + manifest_bytes
    byte_drift = measured_total_bytes - package.byte_size
    package_compression = package.metadata.get("meshopt_compression", {}) or {}
    conversion_timings = package.metadata.get("conversion_timings") or {}
    if not conversion_timings and package.conversion_job_id:
        conversion_timings = (package.conversion_job.metrics or {}).get("timings") or {}

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
        "byte_drift": byte_drift,
        "byte_drift_warning": bool(byte_drift),
        "geometry_bytes": glb_bytes,
        "sidecar_bytes": sidecar_bytes,
        "manifest_bytes": manifest_bytes,
        "compression": {
            "enabled": package_compression.get("enabled", False),
            "status": package_compression.get("status", "not_recorded"),
            "completed_tiles": compression_completed_tiles,
            "failed_tiles": compression_failed_tiles,
            "rejected_tiles": compression_rejected_tiles,
            "skipped_tiles": compression_skipped_tiles,
            "input_bytes": compression_input_bytes,
            "output_bytes": compression_output_bytes,
            "saved_bytes": compression_input_bytes - compression_output_bytes if compression_input_bytes else 0,
            "saved_percent": _saved_percent(compression_input_bytes, compression_output_bytes),
            "ratio": _ratio(compression_input_bytes, compression_output_bytes),
            "duration_ms": compression_duration_ms,
        },
        "conversion_timings": conversion_timings,
        "conversion_timing_breakdown": collect_timing_breakdown(conversion_timings),
        "tile_measurements": tile_rows,
    }


def collect_measurement_summary(measurements):
    compression_input_bytes = sum(item["compression"]["input_bytes"] for item in measurements)
    compression_output_bytes = sum(item["compression"]["output_bytes"] for item in measurements)
    return {
        "packages": len(measurements),
        "objects": sum(item["objects"] for item in measurements),
        "tiles": sum(item["tiles"] for item in measurements),
        "recorded_package_bytes": sum(item["recorded_package_bytes"] for item in measurements),
        "measured_total_bytes": sum(item["measured_total_bytes"] for item in measurements),
        "geometry_bytes": sum(item["geometry_bytes"] for item in measurements),
        "sidecar_bytes": sum(item["sidecar_bytes"] for item in measurements),
        "manifest_bytes": sum(item["manifest_bytes"] for item in measurements),
        "byte_drift": sum(item["byte_drift"] for item in measurements),
        "compression": {
            "completed_tiles": sum(item["compression"]["completed_tiles"] for item in measurements),
            "failed_tiles": sum(item["compression"]["failed_tiles"] for item in measurements),
            "rejected_tiles": sum(item["compression"]["rejected_tiles"] for item in measurements),
            "skipped_tiles": sum(item["compression"]["skipped_tiles"] for item in measurements),
            "input_bytes": compression_input_bytes,
            "output_bytes": compression_output_bytes,
            "saved_bytes": compression_input_bytes - compression_output_bytes if compression_input_bytes else 0,
            "saved_percent": _saved_percent(compression_input_bytes, compression_output_bytes),
            "ratio": _ratio(compression_input_bytes, compression_output_bytes),
            "duration_ms": sum(item["compression"]["duration_ms"] for item in measurements),
        },
        "conversion_timing_breakdown": collect_aggregate_timing_breakdown(measurements),
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

        query = RenderPackage.objects.select_related(
            "source_model",
            "source_model__project",
            "conversion_job",
        ).prefetch_related("tiles")
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
        summary = collect_measurement_summary(measurements)

        if use_json:
            self.stdout.write(json.dumps({"packages": measurements, "summary": summary}, indent=2, sort_keys=True))
            return

        for measurement in measurements:
            self.stdout.write(
                "Package {package_id} | source {source_id} {source!r} | {format} | "
                "{objects} objects | {tiles} tiles".format(**measurement)
            )
            self.stdout.write(
                "  bytes: measured_total={measured_total_bytes} recorded_package={recorded_package_bytes} "
                "geometry={geometry_bytes} sidecar={sidecar_bytes} manifest={manifest_bytes}".format(**measurement)
            )
            if measurement["byte_drift_warning"]:
                self.stdout.write(
                    self.style.WARNING(
                        "  warning: measured_total and recorded_package differ by "
                        f"{measurement['byte_drift']} byte(s); check for missing or orphaned blobs."
                    )
                )
            compression = measurement["compression"]
            ratio = compression["ratio"]
            ratio_text = "n/a" if ratio is None else f"{ratio:.4f}"
            saved_percent = compression["saved_percent"]
            saved_percent_text = "n/a" if saved_percent is None else f"{saved_percent:.1f}%"
            self.stdout.write(
                "  meshopt: status={status} enabled={enabled} completed_tiles={completed_tiles} "
                "skipped_tiles={skipped_tiles} failed_tiles={failed_tiles} rejected_tiles={rejected_tiles} "
                "input={input_bytes} output={output_bytes} saved={saved_bytes} saved_pct={saved_percent_text} "
                "ratio_output_over_input={ratio_text} duration_ms={duration_ms}".format(
                    ratio_text=ratio_text,
                    saved_percent_text=saved_percent_text,
                    **compression,
                )
            )
            timings = measurement.get("conversion_timings") or {}
            if timings:
                self.stdout.write(
                    "  timings: source_read_ms={source_read_ms} parse_ms={parse_ms} tile_grouping_ms={tile_grouping_ms} "
                    "glb_build_ms={glb_build_ms} meshopt_hook_ms={meshopt_hook_ms} tile_write_ms={tile_write_ms} "
                    "tileset_write_ms={tileset_write_ms} db_write_ms={db_write_ms}".format(
                        source_read_ms=timings.get("source_read_ms", "n/a"),
                        parse_ms=timings.get("parse_ms", "n/a"),
                        tile_grouping_ms=timings.get("tile_grouping_ms", "n/a"),
                        glb_build_ms=timings.get("glb_build_ms", "n/a"),
                        meshopt_hook_ms=timings.get("meshopt_hook_ms", "n/a"),
                        tile_write_ms=timings.get("tile_write_ms", "n/a"),
                        tileset_write_ms=timings.get("tileset_write_ms", "n/a"),
                        db_write_ms=timings.get("db_write_ms", "n/a"),
                    )
                )
                breakdown = measurement.get("conversion_timing_breakdown") or {}
                dominant_percent = breakdown.get("dominant_percent")
                dominant_percent_text = "n/a" if dominant_percent is None else f"{dominant_percent:.1f}%"
                self.stdout.write(
                    "  timing decision: total_timed_ms={total_ms} dominant={dominant_label} "
                    "dominant_ms={dominant_ms} dominant_pct={dominant_percent}".format(
                        total_ms=breakdown.get("total_ms", 0),
                        dominant_label=breakdown.get("dominant_label") or "n/a",
                        dominant_ms=breakdown.get("dominant_ms", 0),
                        dominant_percent=dominant_percent_text,
                    )
                )
            for tile in measurement["tile_measurements"]:
                tile_ratio = tile["compression_ratio"]
                tile_ratio_text = "n/a" if tile_ratio is None else f"{tile_ratio:.4f}"
                tile_saved_percent = tile["compression_saved_percent"]
                tile_saved_percent_text = "n/a" if tile_saved_percent is None else f"{tile_saved_percent:.1f}%"
                self.stdout.write(
                    "    {tile_id}: objects={objects} geometry={geometry_bytes} sidecar={sidecar_bytes} "
                    "compression={compression_status} saved_pct={saved_percent} ratio_output_over_input={ratio}".format(
                        **tile,
                        saved_percent=tile_saved_percent_text,
                        ratio=tile_ratio_text,
                    )
                )

        summary_ratio = summary["compression"]["ratio"]
        summary_ratio_text = "n/a" if summary_ratio is None else f"{summary_ratio:.4f}"
        summary_saved_percent = summary["compression"]["saved_percent"]
        summary_saved_percent_text = "n/a" if summary_saved_percent is None else f"{summary_saved_percent:.1f}%"
        self.stdout.write(
            "Summary: packages={packages} objects={objects} tiles={tiles} measured_total={measured_total_bytes} "
            "recorded_package={recorded_package_bytes} geometry={geometry_bytes} sidecar={sidecar_bytes} "
            "manifest={manifest_bytes}".format(**summary)
        )
        if summary["byte_drift"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Summary warning: measured_total and recorded_package differ by {summary['byte_drift']} byte(s)."
                )
            )
        self.stdout.write(
            "Summary meshopt: completed_tiles={completed_tiles} skipped_tiles={skipped_tiles} failed_tiles={failed_tiles} "
            "rejected_tiles={rejected_tiles} input={input_bytes} output={output_bytes} saved={saved_bytes} saved_pct={saved_percent_text} "
            "ratio_output_over_input={ratio_text} duration_ms={duration_ms}".format(
                ratio_text=summary_ratio_text,
                saved_percent_text=summary_saved_percent_text,
                **summary["compression"],
            )
        )
        timing_summary = summary.get("conversion_timing_breakdown") or {}
        if timing_summary.get("total_ms"):
            dominant_percent = timing_summary.get("dominant_percent")
            dominant_percent_text = "n/a" if dominant_percent is None else f"{dominant_percent:.1f}%"
            self.stdout.write(
                "Summary timings: total_timed_ms={total_ms} dominant={dominant_label} "
                "dominant_ms={dominant_ms} dominant_pct={dominant_percent}".format(
                    total_ms=timing_summary.get("total_ms", 0),
                    dominant_label=timing_summary.get("dominant_label") or "n/a",
                    dominant_ms=timing_summary.get("dominant_ms", 0),
                    dominant_percent=dominant_percent_text,
                )
            )
