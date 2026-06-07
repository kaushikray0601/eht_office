from django.core.management import call_command
from django.db import connections
from django.test.runner import DiscoverRunner


class ExistingPostgresTestRunner(DiscoverRunner):
    """Run tests against the pre-created PostgreSQL TEST database.

    This is intentionally opt-in from settings/env. It avoids Django's normal
    CREATE DATABASE path for local PostgreSQL setups where the test database is
    already provisioned but the role shouldn't manage databases.
    """

    def _discard_cached_connection(self, alias):
        if hasattr(connections._connections, alias):
            delattr(connections._connections, alias)

    def setup_databases(self, *, aliases=None, **kwargs):
        aliases = set(connections) if aliases is None else set(aliases)
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

            old_config.append((alias, live_name))
            connections.close_all()
            connections.databases[alias]['NAME'] = test_name
            connections.databases[alias]['CONN_MAX_AGE'] = 0
            self._discard_cached_connection(alias)
            connection = connections[alias]

            if self.verbosity >= 1:
                self.log(
                    f"Using existing PostgreSQL test database for alias '{alias}' ('{test_name}')."
                )
            call_command('migrate', database=alias, verbosity=0, interactive=False)
            call_command('flush', database=alias, verbosity=0, interactive=False)

        return old_config

    def teardown_databases(self, old_config, **kwargs):
        for alias, live_name in old_config:
            connection = connections[alias]
            call_command(
                'flush',
                database=alias,
                verbosity=0,
                interactive=False,
            )
            connection.close()
            connections.databases[alias]['NAME'] = live_name
            self._discard_cached_connection(alias)
