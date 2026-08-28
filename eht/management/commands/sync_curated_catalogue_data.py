from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.utils import DatabaseError

from eht.models import (
    ColdCableCatalogue,
    ElecEHT_ASMEB36,
    ElecEHT_ThermalConductivity,
    ElecEHT_Vendor,
    MIAlloyTempFactor,
    MICableFamily,
    MICableHeater,
    MIColdLeadOption,
)
from raceway.models import RacewayFamily, RacewaySize


CURATED_MODELS = [
    ElecEHT_Vendor,
    ElecEHT_ThermalConductivity,
    ElecEHT_ASMEB36,
    ColdCableCatalogue,
    MICableFamily,
    MICableHeater,
    MIColdLeadOption,
    MIAlloyTempFactor,
    RacewayFamily,
    RacewaySize,
]


class CatalogueSyncSchemaError(Exception):
    def __init__(self, *, model_label, alias, original):
        self.model_label = model_label
        self.alias = alias
        self.original = original
        super().__init__(f"{model_label} unavailable on {alias}: {original}")


class Command(BaseCommand):
    help = (
        "Dry-run-first sync for curated catalogue/reference data from one "
        "configured Django database alias to explicit target aliases. This "
        "command performs no deletes and writes only with --execute."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="default",
            help="Source database alias. Defaults to default. Source is read-only.",
        )
        parser.add_argument(
            "--target",
            action="append",
            default=[],
            help="Target database alias. Repeat for multiple backup databases.",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Actually upsert rows into target aliases. Omit for dry-run.",
        )

    def handle(self, *args, **options):
        source_alias = options["source"]
        target_aliases = options["target"]
        if isinstance(target_aliases, str):
            target_aliases = [target_aliases]
        execute = bool(options["execute"])
        self._validate_aliases(source_alias, target_aliases)

        mode = "EXECUTE" if execute else "DRY-RUN"
        self.stdout.write(f"Curated catalogue sync {mode}: source={source_alias}, targets={', '.join(target_aliases)}")
        self.stdout.write("No deletes are performed. Source database is read-only.")

        for target_alias in target_aliases:
            if execute:
                with transaction.atomic(using=target_alias):
                    self._sync_target(source_alias, target_alias, execute=True)
            else:
                self._sync_target(source_alias, target_alias, execute=False)

    def _validate_aliases(self, source_alias, target_aliases):
        configured = set(connections.databases)
        if source_alias not in configured:
            raise CommandError(f"Unknown source database alias: {source_alias}")
        if not target_aliases:
            raise CommandError("At least one --target database alias is required.")
        for target_alias in target_aliases:
            if target_alias not in configured:
                raise CommandError(f"Unknown target database alias: {target_alias}")
            if target_alias == source_alias:
                raise CommandError("Source and target aliases must be different.")

    def _sync_target(self, source_alias, target_alias, *, execute):
        self.stdout.write(f"Target {target_alias}:")
        unavailable = []
        for model in CURATED_MODELS:
            try:
                stats = self._sync_model(model, source_alias, target_alias, execute=execute)
            except CatalogueSyncSchemaError as exc:
                if execute:
                    raise CommandError(
                        f"Cannot sync curated catalogue data: {exc}. "
                        "Run migrations or choose migrated database aliases before --execute."
                    ) from exc
                unavailable.append(str(exc))
                self.stdout.write(f"  {model._meta.label}: schema unavailable on {exc.alias}: {exc.original}")
                continue
            action = "upserted" if execute else "would upsert"
            self.stdout.write(
                f"  {model._meta.label}: source={stats['source_count']} target={stats['target_count']} "
                f"create={stats['create_count']} update={stats['update_count']} {action}"
            )
        if unavailable:
            self.stdout.write(
                self.style.WARNING(
                    f"  {len(unavailable)} model(s) could not be inspected; migrate source/target aliases before --execute."
                )
            )

    def _sync_model(self, model, source_alias, target_alias, *, execute):
        pk_name = model._meta.pk.attname
        try:
            rows = list(model.objects.using(source_alias).order_by(pk_name))
        except DatabaseError as exc:
            raise CatalogueSyncSchemaError(model_label=model._meta.label, alias=source_alias, original=exc) from exc
        source_pks = [getattr(row, pk_name) for row in rows]
        try:
            target_existing = set(
                model.objects.using(target_alias)
                .filter(**{f"{pk_name}__in": source_pks})
                .values_list(pk_name, flat=True)
            )
            target_count = model.objects.using(target_alias).count()
        except DatabaseError as exc:
            raise CatalogueSyncSchemaError(model_label=model._meta.label, alias=target_alias, original=exc) from exc
        create_count = sum(1 for pk in source_pks if pk not in target_existing)
        update_count = sum(1 for pk in source_pks if pk in target_existing)

        if execute:
            for row in rows:
                lookup = {pk_name: getattr(row, pk_name)}
                defaults = self._row_defaults(row)
                try:
                    model.objects.using(target_alias).update_or_create(defaults=defaults, **lookup)
                except DatabaseError as exc:
                    raise CatalogueSyncSchemaError(model_label=model._meta.label, alias=target_alias, original=exc) from exc

        return {
            "source_count": len(rows),
            "target_count": target_count,
            "create_count": create_count,
            "update_count": update_count,
        }

    def _row_defaults(self, row):
        values = {}
        for field in row._meta.concrete_fields:
            if field.primary_key:
                continue
            values[field.attname] = getattr(row, field.attname)
        return values
