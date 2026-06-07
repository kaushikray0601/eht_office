from django.core.management.base import BaseCommand, CommandError

from eht.sld_topology_history import compact_sld_topology_history


class Command(BaseCommand):
    help = 'Compact old SLD topology edit history rows into audit-only records.'

    def add_arguments(self, parser):
        parser.add_argument('--project-id', help='Limit compaction to one project id.')
        parser.add_argument(
            '--keep-full',
            type=int,
            default=20,
            help='Number of latest superseded full-payload rows to keep per project.',
        )
        parser.add_argument(
            '--keep-reset',
            type=int,
            default=10,
            help='Number of latest reset full-payload rows to keep per project.',
        )
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Actually compact records. Without this flag the command runs as a dry-run.',
        )
        parser.add_argument(
            '--reason',
            default='management_command_retention_policy',
            help='Audit reason recorded on compacted rows.',
        )

    def handle(self, *args, **options):
        if options['keep_full'] < 0 or options['keep_reset'] < 0:
            raise CommandError('--keep-full and --keep-reset must be zero or greater.')

        summary = compact_sld_topology_history(
            project_id=options.get('project_id'),
            keep_full=options['keep_full'],
            keep_reset=options['keep_reset'],
            dry_run=not options['execute'],
            reason=options['reason'],
        )

        mode = 'DRY RUN' if summary['dry_run'] else 'EXECUTED'
        saved_kb = round(summary['saved_size_bytes'] / 1024, 1)
        self.stdout.write(
            f"{mode}: {summary['candidate_count']} candidate row(s), "
            f"{summary['compacted_count']} compactable, {summary['skipped_count']} skipped, "
            f"estimated saved {saved_kb} KB."
        )

        if summary['dry_run']:
            self.stdout.write('Re-run with --execute to apply this compaction.')
        else:
            self.stdout.write(self.style.SUCCESS('SLD topology history compaction complete.'))
