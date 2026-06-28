import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from plant3d.models import ConversionJob, ModelObject, RenderPackage, RenderTile, SourceModel
from plant3d.storage import delete_key, exists


def _walk_storage_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("_storage_key") and isinstance(item, str) and item:
                yield item
            else:
                yield from _walk_storage_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_storage_keys(item)


def _collect_source_storage_keys(sources):
    keys = set()
    for source in sources:
        if source.storage_key:
            keys.add(source.storage_key)
        for package in source.render_packages.all():
            if package.manifest_storage_key:
                keys.add(package.manifest_storage_key)
            keys.update(_walk_storage_keys(package.metadata))
            for tile in package.tiles.all():
                if tile.storage_key:
                    keys.add(tile.storage_key)
                keys.update(_walk_storage_keys(tile.metadata))
        for job in source.conversion_jobs.all():
            if job.input_storage_key:
                keys.add(job.input_storage_key)
            keys.update(_walk_storage_keys(job.metrics))
    return sorted(keys)


def build_purge_plan(queryset):
    sources = list(
        queryset
        .prefetch_related("conversion_jobs", "model_objects", "render_packages__tiles")
        .order_by("project_id", "id")
    )
    source_ids = [source.pk for source in sources]
    storage_keys = _collect_source_storage_keys(sources)
    existing_storage_keys = [key for key in storage_keys if exists(key)]
    return {
        "source_ids": source_ids,
        "sources": len(sources),
        "conversion_jobs": ConversionJob.objects.filter(source_model_id__in=source_ids).count() if source_ids else 0,
        "render_packages": RenderPackage.objects.filter(source_model_id__in=source_ids).count() if source_ids else 0,
        "render_tiles": RenderTile.objects.filter(render_package__source_model_id__in=source_ids).count() if source_ids else 0,
        "model_objects": ModelObject.objects.filter(source_model_id__in=source_ids).count() if source_ids else 0,
        "storage_keys": storage_keys,
        "existing_storage_keys": existing_storage_keys,
        "missing_storage_keys": [key for key in storage_keys if key not in set(existing_storage_keys)],
    }


class Command(BaseCommand):
    help = "Dry-run or purge local plant3d spike data and associated storage blobs."

    def add_arguments(self, parser):
        parser.add_argument("--source-id", action="append", type=int, dest="source_ids", help="SourceModel id to purge.")
        parser.add_argument("--project-id", help="Purge all plant3d sources for one project id.")
        parser.add_argument("--all", action="store_true", dest="all_sources", help="Purge all plant3d sources.")
        parser.add_argument("--confirm", action="store_true", help="Actually delete rows and storage blobs.")
        parser.add_argument("--keep-storage", action="store_true", help="Delete database rows but leave storage blobs.")
        parser.add_argument("--json", action="store_true", help="Write machine-readable JSON.")

    def handle(self, *args, **options):
        source_ids = options["source_ids"] or []
        project_id = options["project_id"]
        all_sources = options["all_sources"]
        confirm = options["confirm"]
        keep_storage = options["keep_storage"]
        use_json = options["json"]

        scope_count = bool(source_ids) + bool(project_id) + bool(all_sources)
        if scope_count != 1:
            raise CommandError("Choose exactly one purge scope: --source-id, --project-id, or --all.")

        queryset = SourceModel.objects.all()
        if source_ids:
            queryset = queryset.filter(pk__in=source_ids)
        elif project_id:
            queryset = queryset.filter(project_id=project_id)

        plan = build_purge_plan(queryset)
        result = {
            **plan,
            "confirmed": confirm,
            "dry_run": not confirm,
            "keep_storage": keep_storage,
            "deleted_storage_keys": [],
            "failed_storage_keys": [],
            "deleted_sources": 0,
        }

        if confirm and plan["source_ids"]:
            with transaction.atomic():
                deleted_count, _deleted_by_model = SourceModel.objects.filter(pk__in=plan["source_ids"]).delete()
                result["deleted_sources"] = plan["sources"]
                result["deleted_rows_total"] = deleted_count

            if not keep_storage:
                for key in plan["existing_storage_keys"]:
                    try:
                        if delete_key(key):
                            result["deleted_storage_keys"].append(key)
                    except OSError:
                        result["failed_storage_keys"].append(key)

        if use_json:
            self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
            return

        self.stdout.write(
            "Plant3D purge plan: sources={sources} jobs={conversion_jobs} packages={render_packages} "
            "tiles={render_tiles} objects={model_objects} storage_files={storage_count}".format(
                storage_count=len(plan["existing_storage_keys"]),
                **plan,
            )
        )
        if plan["source_ids"]:
            self.stdout.write(f"  source_ids={plan['source_ids']}")
        if not confirm:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run with --confirm to delete."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Deleted plant3d DB scope: sources={sources}, storage_deleted={deleted}, storage_failed={failed}.".format(
                    sources=result["deleted_sources"],
                    deleted=len(result["deleted_storage_keys"]),
                    failed=len(result["failed_storage_keys"]),
                )
            )
        )
        if result["failed_storage_keys"]:
            self.stdout.write(self.style.WARNING(f"Storage keys not deleted: {result['failed_storage_keys']}"))
