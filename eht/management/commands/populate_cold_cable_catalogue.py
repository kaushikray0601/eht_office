from django.core.management.base import BaseCommand

from eht.models import ColdCableCatalogue


IEC_CU_XLPE_METHOD_E_ROWS = [
    {'core_count': 3, 'conductor_size_mm2': 2.5, 'ampacity_a': 26, 'resistance_mohm_per_m': 7.41},
    {'core_count': 3, 'conductor_size_mm2': 6, 'ampacity_a': 45, 'resistance_mohm_per_m': 3.08},
    {'core_count': 3, 'conductor_size_mm2': 10, 'ampacity_a': 61, 'resistance_mohm_per_m': 1.83},
    {'core_count': 3, 'conductor_size_mm2': 16, 'ampacity_a': 81, 'resistance_mohm_per_m': 1.15},
    {'core_count': 4, 'conductor_size_mm2': 2.5, 'ampacity_a': 23, 'resistance_mohm_per_m': 7.41},
    {'core_count': 4, 'conductor_size_mm2': 4, 'ampacity_a': 30, 'resistance_mohm_per_m': 4.61},
    {'core_count': 4, 'conductor_size_mm2': 6, 'ampacity_a': 38, 'resistance_mohm_per_m': 3.08},
    {'core_count': 4, 'conductor_size_mm2': 10, 'ampacity_a': 52, 'resistance_mohm_per_m': 1.83},
    {'core_count': 4, 'conductor_size_mm2': 16, 'ampacity_a': 70, 'resistance_mohm_per_m': 1.15},
    {'core_count': 4, 'conductor_size_mm2': 25, 'ampacity_a': 92, 'resistance_mohm_per_m': 0.727},
    {'core_count': 4, 'conductor_size_mm2': 35, 'ampacity_a': 112, 'resistance_mohm_per_m': 0.524},
    {'core_count': 4, 'conductor_size_mm2': 50, 'ampacity_a': 133, 'resistance_mohm_per_m': 0.387},
    {'core_count': 4, 'conductor_size_mm2': 70, 'ampacity_a': 163, 'resistance_mohm_per_m': 0.268},
    {'core_count': 4, 'conductor_size_mm2': 95, 'ampacity_a': 192, 'resistance_mohm_per_m': 0.193},
]


class Command(BaseCommand):
    help = 'Populate the initial validated cold-cable catalogue rows for IEC Cu XLPE method E.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview rows without writing to the database.')
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete matching IEC Cu XLPE method E rows before loading.',
        )

    def handle(self, *args, **options):
        defaults = {
            'vendor': 'IEC reference',
            'cable_standard': 'IEC_60502_1',
            'catalogue_ref': 'IEC 60364-5-52:2009 Table B.52.4 / IEC 60502-1',
            'cable_type_code': 'Cu/XLPE/SWA/PVC 0.6/1kV',
            'voltage_grade': '0.6/1kV',
            'conductor_material': 'Cu',
            'insulation_type': 'XLPE',
            'installation_method': 'E',
            'ampacity_temp_ref_c': 30.0,
            'max_conductor_temp_c': 90.0,
            'reactance_mohm_per_m': 0.08,
            'source_document': 'IEC 60364-5-52:2009 Table B.52.4 / IEC 60502-1 seed basis',
            'is_validated': True,
        }

        if options['dry_run']:
            self.stdout.write(f"Ready to load {len(IEC_CU_XLPE_METHOD_E_ROWS)} cold-cable rows.")
            for row in IEC_CU_XLPE_METHOD_E_ROWS:
                self.stdout.write(
                    f"  {row['core_count']}C x {row['conductor_size_mm2']:g} mm2 | "
                    f"{row['ampacity_a']} A | {row['resistance_mohm_per_m']} mOhm/m"
                )
            return

        if options['clear']:
            deleted, _ = ColdCableCatalogue.objects.filter(
                cable_standard=defaults['cable_standard'],
                conductor_material=defaults['conductor_material'],
                insulation_type=defaults['insulation_type'],
                installation_method=defaults['installation_method'],
            ).delete()
            self.stdout.write(f'Deleted {deleted} matching cold-cable catalogue row(s).')

        created_count = 0
        updated_count = 0
        for row in IEC_CU_XLPE_METHOD_E_ROWS:
            row_defaults = {**defaults, **row, 'pe_conductor_size_mm2': row['conductor_size_mm2']}
            lookup = {
                'cable_standard': defaults['cable_standard'],
                'conductor_material': defaults['conductor_material'],
                'insulation_type': defaults['insulation_type'],
                'core_count': row['core_count'],
                'conductor_size_mm2': row['conductor_size_mm2'],
                'installation_method': defaults['installation_method'],
            }
            obj, created = ColdCableCatalogue.objects.update_or_create(
                **lookup,
                defaults=row_defaults,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Cold-cable catalogue load complete: {created_count} created, {updated_count} updated.'
            )
        )
