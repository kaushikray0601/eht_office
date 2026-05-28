from django.core.management.base import BaseCommand, CommandError

from eht.mi_catalogue_readiness import summarize_mi_catalogue_readiness
from eht.models import MICableFamily


class Command(BaseCommand):
    help = 'Report MI catalogue readiness and optionally mark reviewed-ready families as validated.'

    def add_arguments(self, parser):
        parser.add_argument('--vendor', help='Limit to one vendor code, for example THR, CHR, or nVN.')
        parser.add_argument(
            '--mark-validated',
            action='store_true',
            help='Set is_validated=True for readiness-passing families.',
        )
        parser.add_argument(
            '--confirm-reviewed',
            action='store_true',
            help='Required with --mark-validated to confirm catalogue rows were reviewed against source documents.',
        )

    def handle(self, *args, **options):
        if options['mark_validated'] and not options['confirm_reviewed']:
            raise CommandError('--mark-validated requires --confirm-reviewed.')

        families = MICableFamily.objects.all().prefetch_related('heaters__cold_lead_options').order_by('vendor', 'family_name')
        if options.get('vendor'):
            families = families.filter(vendor=options['vendor'])

        summary = summarize_mi_catalogue_readiness(families)
        self.stdout.write(
            f"MI catalogue readiness: {summary['ready_count']} ready / "
            f"{summary['family_count']} total, {summary['validated_count']} already validated."
        )

        validated_now = 0
        for report in summary['reports']:
            family = report['family']
            status = 'READY' if report['ready'] else 'BLOCKED'
            validated = 'validated' if family.is_validated else 'not validated'
            self.stdout.write(
                f"- {family.vendor} {family.family_name}: {status}, {validated}, "
                f"{report['heater_count']} heater(s), {report['cold_lead_count']} cold lead option(s)"
            )
            for blocker in report['blockers']:
                self.stdout.write(f"  BLOCKER: {blocker}")
            for warning in report['warnings'][:10]:
                self.stdout.write(f"  WARNING: {warning}")
            if len(report['warnings']) > 10:
                self.stdout.write(f"  WARNING: {len(report['warnings']) - 10} additional warning(s) hidden")

            if options['mark_validated'] and report['ready'] and not family.is_validated:
                family.is_validated = True
                family.save(update_fields=['is_validated'])
                validated_now += 1

        if options['mark_validated']:
            self.stdout.write(self.style.SUCCESS(f'Marked {validated_now} MI family/families as validated.'))
