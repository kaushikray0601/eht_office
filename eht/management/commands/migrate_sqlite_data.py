import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connections


class Command(BaseCommand):
    help = (
        "Dump project data from a SQLite source database and load it into the "
        "current default database. Intended for one-time SQLite to PostgreSQL migration."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-alias",
            default="sqlite_source",
            help="SQLite database alias defined in settings.py. Defaults to sqlite_source.",
        )
        parser.add_argument(
            "--fixture-path",
            help="Optional path for the intermediate JSON fixture. A temp file is used by default.",
        )
        parser.add_argument(
            "--include-auth-user",
            action="store_true",
            help="Also migrate auth.User records so linked UserAttempt rows remain valid.",
        )
        parser.add_argument(
            "--skip-load",
            action="store_true",
            help="Only create the fixture dump and do not load it into the default database.",
        )
        parser.add_argument(
            "--migrate-target",
            action="store_true",
            help="Run migrations on the default database before loading data.",
        )

    def handle(self, *args, **options):
        source_alias = options["source_alias"]
        fixture_path = options.get("fixture_path")
        include_auth_user = options["include_auth_user"]
        skip_load = options["skip_load"]
        migrate_target = options["migrate_target"]

        if source_alias not in settings.DATABASES:
            raise CommandError(f"Database alias '{source_alias}' is not configured.")

        source_db = settings.DATABASES[source_alias]
        if source_db["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError(
                f"Database alias '{source_alias}' is not SQLite and cannot be used as a source."
            )

        source_path = Path(source_db["NAME"])
        if not source_path.exists():
            raise CommandError(f"SQLite source database not found: {source_path}")

        default_db = settings.DATABASES["default"]
        using_postgres = default_db["ENGINE"] == "django.db.backends.postgresql"

        if not skip_load and not using_postgres:
            raise CommandError(
                "The default database is not PostgreSQL. Set USE_POSTGRES=1 and the "
                "PostgreSQL connection variables before loading data into the target database."
            )

        models_to_dump = ["eht"]
        if include_auth_user:
            models_to_dump.insert(0, "auth.user")

        created_temp_fixture = False
        if not fixture_path:
            handle, fixture_path = tempfile.mkstemp(prefix="sqlite_migration_", suffix=".json")
            os.close(handle)
            created_temp_fixture = True

        self.stdout.write(
            f"Dumping data from '{source_alias}' ({source_path}) to fixture: {fixture_path}"
        )

        try:
            # Touch the source connection early so we fail fast on bad paths/aliases.
            connections[source_alias].ensure_connection()

            call_command(
                "dumpdata",
                *models_to_dump,
                database=source_alias,
                output=fixture_path,
                indent=2,
                verbosity=1,
            )

            if skip_load:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Fixture created successfully at {fixture_path}. Load step was skipped."
                    )
                )
                return

            if migrate_target:
                self.stdout.write("Running migrations on the default PostgreSQL database...")
                call_command("migrate", database="default", verbosity=1)

            self.stdout.write(f"Loading fixture into default database ({default_db['NAME']})...")
            call_command("loaddata", fixture_path, database="default", verbosity=1)
            self.stdout.write(self.style.SUCCESS("SQLite data migrated into the default database."))

        finally:
            if created_temp_fixture and Path(fixture_path).exists():
                Path(fixture_path).unlink()
