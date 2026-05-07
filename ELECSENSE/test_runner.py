from django.core.management import call_command
from django.db import connections
from django.test.runner import DiscoverRunner


class ExistingPostgresTestRunner(DiscoverRunner):
    """Run tests against the pre-created PostgreSQL TEST database.

    This is intentionally opt-in from settings/env. It avoids Django's normal
    CREATE DATABASE path for local PostgreSQL setups where the test database is
    already provisioned but the role shouldn't manage databases.
    """

    def setup_databases(self, *, aliases=None, **kwargs):
        aliases = set(aliases or connections)
        old_config = []

        for alias in aliases:
            connection = connections[alias]
            if connection.vendor != 'postgresql':
                continue

            test_name = (connection.settings_dict.get('TEST') or {}).get('NAME')
            live_name = connection.settings_dict.get('NAME')
            if not test_name:
                raise RuntimeError(f"PostgreSQL alias '{alias}' has no TEST.NAME configured.")
            if test_name == live_name:
                raise RuntimeError(
                    f"Refusing to run tests for alias '{alias}' because TEST.NAME matches NAME."
                )

            connection.close()
            old_config.append((connection, live_name))
            connection.settings_dict['NAME'] = test_name
            connection.settings_dict['CONN_MAX_AGE'] = 0
            connections.close_all()

            if self.verbosity >= 1:
                self.log(
                    f"Using existing PostgreSQL test database for alias '{alias}' ('{test_name}')."
                )
            connection.ensure_connection()
            connection.close()
            call_command('migrate', database=alias, verbosity=0, interactive=False)
            call_command('flush', database=alias, verbosity=0, interactive=False)

        return old_config

    def teardown_databases(self, old_config, **kwargs):
        for connection, live_name in old_config:
            call_command(
                'flush',
                database=connection.alias,
                verbosity=0,
                interactive=False,
            )
            connection.close()
            connection.settings_dict['NAME'] = live_name
