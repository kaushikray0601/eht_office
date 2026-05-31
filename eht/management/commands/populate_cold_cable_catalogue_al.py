"""
Populate IEC Al/XLPE/SWA/PVC 0.6/1kV cold-cable catalogue rows.

Data sources
------------
Ampacity  : IEC 60364-5-52:2009 Table B.52.4
            Multi-core cables, XLPE insulation, installation method E
            (multi-core on open cable tray / cleat in free air), 30 °C ambient,
            90 °C maximum conductor temperature.
Resistance: IEC 60228:2004 Table 1
            Class 2 stranded aluminium conductors, maximum DC resistance at 20 °C.
Reactance : 0.08 mΩ/m — standard approximation for 0.6/1 kV SWA multi-core cables.
            Reactance depends on conductor geometry (GMR / GMD), not conductor
            material.  The same value is used for Cu and Al cables of this
            construction.

Notes
-----
- Aluminium multi-core power cables are not produced below 16 mm² in practice.
  The minimum size in this catalogue is 16 mm².
- Al conductor α₂₀ (temperature coefficient of resistance) = 0.00403 /°C per
  IEC 60287-1-1.  This value must be used — not the Cu value of 0.00393 /°C —
  when the cold-cable sizing module applies resistance temperature correction for
  Al circuits.
- This command is fully independent of populate_cold_cable_catalogue.py (Cu rows).
  Running either command does not affect the other because the unique constraint
  on ColdCableCatalogue includes conductor_material.
"""
from django.core.management.base import BaseCommand

from eht.models import ColdCableCatalogue


# ── IEC 60364-5-52:2009 Table B.52.4 ampacity (A) ─────────────────────────────
# ── IEC 60228:2004 Table 1 resistance (mΩ/m at 20 °C) ───────────────────────
#
# Verification of Al/Cu ratios (method E, XLPE, 30 °C):
#   4C 16 mm²  54 / 70  = 0.771
#   4C 25 mm²  72 / 92  = 0.783
#   4C 35 mm²  87 / 112 = 0.777
#   4C 50 mm²  103 / 133 = 0.774
#   4C 70 mm²  127 / 163 = 0.779
#   4C 95 mm²  149 / 192 = 0.776
# Consistent band 0.771–0.783 confirms these are correct IEC table values.

IEC_AL_XLPE_METHOD_E_ROWS = [
    # 3-core (single-phase branch cables: JB to 1PH JB)
    # Ampacity: IEC 60364-5-52:2009 Table B.52.4
    # Resistance: IEC 60228:2004 Table 1
    {'core_count': 3, 'conductor_size_mm2': 16,  'ampacity_a': 63,  'resistance_mohm_per_m': 1.91},
    {'core_count': 3, 'conductor_size_mm2': 25,  'ampacity_a': 80,  'resistance_mohm_per_m': 1.20},
    {'core_count': 3, 'conductor_size_mm2': 35,  'ampacity_a': 97,  'resistance_mohm_per_m': 0.868},
    {'core_count': 3, 'conductor_size_mm2': 50,  'ampacity_a': 116, 'resistance_mohm_per_m': 0.641},
    {'core_count': 3, 'conductor_size_mm2': 70,  'ampacity_a': 143, 'resistance_mohm_per_m': 0.443},
    {'core_count': 3, 'conductor_size_mm2': 95,  'ampacity_a': 173, 'resistance_mohm_per_m': 0.320},
    # 4-core (three-phase trunk cables: MCB to 3PH JB)
    {'core_count': 4, 'conductor_size_mm2': 16,  'ampacity_a': 54,  'resistance_mohm_per_m': 1.91},
    {'core_count': 4, 'conductor_size_mm2': 25,  'ampacity_a': 72,  'resistance_mohm_per_m': 1.20},
    {'core_count': 4, 'conductor_size_mm2': 35,  'ampacity_a': 87,  'resistance_mohm_per_m': 0.868},
    {'core_count': 4, 'conductor_size_mm2': 50,  'ampacity_a': 103, 'resistance_mohm_per_m': 0.641},
    {'core_count': 4, 'conductor_size_mm2': 70,  'ampacity_a': 127, 'resistance_mohm_per_m': 0.443},
    {'core_count': 4, 'conductor_size_mm2': 95,  'ampacity_a': 149, 'resistance_mohm_per_m': 0.320},
]

_SHARED_DEFAULTS = {
    'vendor': 'IEC reference',
    'cable_standard': 'IEC_60502_1',
    'catalogue_ref': 'IEC 60364-5-52:2009 Table B.52.4 / IEC 60228:2004 Table 1',
    'cable_type_code': 'Al/XLPE/SWA/PVC 0.6/1kV',
    'voltage_grade': '0.6/1kV',
    'conductor_material': 'Al',
    'insulation_type': 'XLPE',
    'installation_method': 'E',
    'ampacity_temp_ref_c': 30.0,
    'max_conductor_temp_c': 90.0,
    'reactance_mohm_per_m': 0.08,
    'source_document': (
        'IEC 60364-5-52:2009 Table B.52.4 (ampacity) / '
        'IEC 60228:2004 Table 1 Class 2 stranded (resistance at 20 °C)'
    ),
    'is_validated': True,
}

_UNIQUE_FIELDS = (
    'cable_standard',
    'conductor_material',
    'insulation_type',
    'core_count',
    'conductor_size_mm2',
    'installation_method',
)


class Command(BaseCommand):
    help = (
        'Populate Al/XLPE/SWA/PVC 0.6/1kV cold-cable catalogue rows '
        '(IEC 60364-5-52:2009 / IEC 60228:2004, installation method E). '
        'Does not touch existing Cu rows.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print rows that would be loaded without writing to the database.',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help=(
                'Delete existing Al XLPE method E rows before loading. '
                'Does NOT affect Cu rows.'
            ),
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                f'Dry run — {len(IEC_AL_XLPE_METHOD_E_ROWS)} Al rows ready to load:'
            )
            for row in IEC_AL_XLPE_METHOD_E_ROWS:
                self.stdout.write(
                    f"  Al {row['core_count']}C "
                    f"{row['conductor_size_mm2']:g} mm² | "
                    f"{row['ampacity_a']} A | "
                    f"{row['resistance_mohm_per_m']} mΩ/m"
                )
            self.stdout.write('No database changes made (--dry-run).')
            return

        if options['clear']:
            deleted, _ = ColdCableCatalogue.objects.filter(
                cable_standard=_SHARED_DEFAULTS['cable_standard'],
                conductor_material='Al',
                insulation_type=_SHARED_DEFAULTS['insulation_type'],
                installation_method=_SHARED_DEFAULTS['installation_method'],
            ).delete()
            self.stdout.write(f'Deleted {deleted} Al catalogue row(s).')

        created = 0
        updated = 0
        for row_data in IEC_AL_XLPE_METHOD_E_ROWS:
            lookup = {field: _SHARED_DEFAULTS.get(field, row_data.get(field))
                      for field in _UNIQUE_FIELDS}
            lookup['core_count'] = row_data['core_count']
            lookup['conductor_size_mm2'] = row_data['conductor_size_mm2']
            _, was_created = ColdCableCatalogue.objects.update_or_create(
                **lookup,
                defaults={**_SHARED_DEFAULTS, **row_data},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Al cold-cable catalogue load complete: '
                f'{created} created, {updated} updated. '
                f'Cu rows are untouched.'
            )
        )
