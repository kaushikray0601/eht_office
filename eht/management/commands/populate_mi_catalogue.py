"""Seed MI cable catalogue with Thermon MIQ, nVent XMI-A62, and Chromalox MI (B-series) data.

All families are created with is_validated=False. KR must inspect each row against the source
document and set is_validated=True manually via Django admin before the engine will use the data.

Run:
    python manage.py populate_mi_catalogue
    python manage.py populate_mi_catalogue --vendor THR
    python manage.py populate_mi_catalogue --update
    python manage.py populate_mi_catalogue --dry-run

Sources:
    Thermon  — TEP0020-MIQ-Spec.pdf
    nVent    — Raychem-DS-H56870-XMIA-EN-1810 + Raychem-DS-DOC2210-HAX-EN-1704
    Chromalox — mod-mi.ashx (Chromalox MI Heating Cables datasheet)
"""

import logging

from django.core.management.base import BaseCommand

from eht.models import MICableFamily, MICableHeater, MIColdLeadOption


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Catalogue data definitions
# ---------------------------------------------------------------------------

THERMON_MIQ_HEATERS = [
    # (part_number, conductors, resistance_ohms_m, max_current_a)
    # Source: TEP0020-MIQ-Spec.pdf resistance table
    # Conductor: Ni-Cr alloy wire, TCR ≈ 0.085–0.090 ×10⁻³/K
    # Cold leads: 4 ft (1.219 m) or 7 ft (2.134 m) standard
    ('MIQ-11EOH-2S', 2, 36.10,  3.0),
    ('MIQ-11E2H-2S', 2, 18.00,  4.5),
    ('MIQ-11E4H-2S', 2,  9.02,  6.0),
    ('MIQ-11E6H-2S', 2,  4.51,  8.0),
    ('MIQ-21EOH-2S', 2,  2.29, 11.0),
    ('MIQ-21E2H-2S', 2,  1.64, 13.0),
    ('MIQ-21E4H-2S', 2,  0.984, 16.0),
    ('MIQ-21E6H-2S', 2,  0.655, 20.0),
    ('MIQ-31EOH-2S', 2,  0.328, 28.0),
    ('MIQ-31E2H-2S', 2,  0.246, 32.0),
    ('MIQ-31E4H-2S', 2,  0.164, 39.0),
    ('MIQ-31E6H-2S', 2,  0.123, 45.0),
    ('MIQ-41EOH-2S', 2,  0.0820, 55.0),
    ('MIQ-41E2H-2S', 2,  0.0656, 61.0),
    ('MIQ-41E4H-2S', 2,  0.0492, 71.0),
    ('MIQ-41E6H-2S', 2,  0.0410, 77.0),
    ('MIQ-51EOH-2S', 2,  0.0328, 86.0),
    ('MIQ-61EOH-2S', 2,  0.0164, 122.0),
    ('MIQ-71EOH-2S', 2,  0.00656, 192.0),
    ('MIQ-81E2H-2S', 2,  0.03281, 86.0),
    ('MIQ-81E4H-2S', 2,  0.02684, 96.0),
]

# Thermon cold lead options apply to ALL MIQ heaters (both lengths available per heater)
THERMON_MIQ_COLD_LEADS = [
    # (option_code, length_m)
    # Source: TEP0020-MIQ-Spec.pdf — standard 4 ft and 7 ft options
    # Resistance: not published in spec; estimated from wire gauge on request from Thermon
    ('CL-4FT',  1.219),
    ('CL-7FT',  2.134),
]

NVENT_XMIA_HEATERS = [
    # (part_number, conductors, resistance_ohms_m, max_current_a)
    # Source: Raychem-DS-DOC2210-HAX-EN-1704 (HAx = XMI-A family)
    # part_number uses nVent HAx catalogue codes for XMI-A62 (600V dual conductor)
    # TCR values are per-code:
    #   A/F suffix → 0.085–0.090 ×10⁻³/K (Ni-Cr)
    #   B suffix   → 0.040 ×10⁻³/K (Balco)
    #   T suffix   → 0.10–0.18 ×10⁻³/K (Nichrome)
    #   Q suffix   → 0.50 ×10⁻³/K (Nickel alloy)
    #   P suffix   → 1.30 ×10⁻³/K (Nickel alloy)
    #   C suffix   → 3.90 ×10⁻³/K (Alloy 825 / Inconel)
    ('HAF2N36K',      2, 36.00,   3.4),
    ('HAF2N18K',      2, 18.00,   4.8),
    ('HAF2N9.0K',     2,  9.00,   6.7),
    ('HAF2N4.5K',     2,  4.50,   9.5),
    ('HAA2N2.3K',     2,  2.30,  13.0),
    ('HAA2N1.8K',     2,  1.80,  15.0),
    ('HAA2N1.1K',     2,  1.10,  19.0),
    ('HAA2N0.73K',    2,  0.730, 24.0),
    ('HAA2N0.36K',    2,  0.360, 34.0),
    ('HAA2N0.27K',    2,  0.270, 39.0),
    ('HAA2N0.18K',    2,  0.180, 48.0),
    ('HAA2N0.14K',    2,  0.140, 55.0),
    ('HAA2N0.090K',   2,  0.0900, 68.0),
    ('HAA2N0.072K',   2,  0.0720, 77.0),
    ('HAA2N0.054K',   2,  0.0540, 88.0),
    ('HAA2N0.045K',   2,  0.0450, 97.0),
    ('HAA2N0.036K',   2,  0.0360, 109.0),
    ('HAQ2N0.018K',   2,  0.0180, 116.0),
    ('HAQ2N0.014K',   2,  0.0140, 131.0),
    ('HAQ2N0.0090K',  2,  0.00900, 164.0),
    ('HAQ2N0.0072K',  2,  0.00720, 184.0),
    ('HAP2N0.0054K',  2,  0.00540, 197.0),
    ('HAP2N0.0042K',  2,  0.00420, 223.0),
    ('HAC2N0.036K',   2,  0.0360,  90.0),
    ('HAC2N0.027K',   2,  0.0270, 104.0),
    ('HAC2N0.018K',   2,  0.0180, 127.0),
    ('HAC2N0.014K',   2,  0.0140, 146.0),
    ('HAC2N4.3',      2,  0.00420, 218.0),
]

NVENT_XMIA_COLD_LEADS = [
    # (option_code, length_m)
    # Source: Raychem-DS-H56870-XMIA-EN-1810 — Design D/E cold lead options
    # S25A = 25A rated, ~2.5mm² Cu, R ≈ 7.41 mΩ/m
    # S34A = 34A rated, ~4.0mm² Cu, R ≈ 4.61 mΩ/m
    # S49A = 49A rated, ~6.0mm² Cu, R ≈ 3.08 mΩ/m
    # S65A = 65A rated, ~10.0mm² Cu, R ≈ 1.83 mΩ/m
    # Standard spool length includes 2.1 m cold lead on each end
    ('S25A', 2.100),
    ('S34A', 2.100),
    ('S49A', 2.100),
    ('S65A', 2.100),
]

CHROMALOX_MI_HEATERS = [
    # (part_number, conductors, resistance_ohms_m, max_current_a)
    # Source: mod-mi.ashx (Chromalox MI 600V Alloy 825 B-series)
    # TCR values: 0.10 ×10⁻³/K for 700–600 series (Nichrome), 0.18 for 400 series,
    #             0.50 for 200 series, 3.93 for 500B/100 series (Alloy 825 conductors)
    ('1110B', 2, 36.10,  3.0),
    ('1010B', 2, 18.00,  4.5),
    ( '910B', 2,  9.02,  6.0),
    ( '810B', 2,  4.51,  8.0),
    ( '710B', 2,  2.29, 11.0),
    ( '610B', 2,  1.64, 13.0),
    ( '520B', 2,  0.984, 16.0),
    ( '510B', 2,  0.820, 18.0),
    ( '410B', 2,  0.328, 28.0),
    ( '320B', 2,  0.164, 38.0),
    ( '310B', 2,  0.123, 44.0),
    ( '210B', 2,  0.0656, 61.0),
    ( '205B', 2,  0.0328, 86.0),
    ( '200B', 2,  0.0164, 122.0),
    ( '115B', 2,  0.00820, 175.0),
    ( '110B', 2,  0.00410, 247.0),
    ( '108B', 2,  0.00273, 303.0),
    ( '106B', 2,  0.00164, 391.0),
    ( '105B', 2,  0.00136, 430.0),
    ( '104B', 2,  0.000820, 553.0),
    ( '103B', 2,  0.000656, 619.0),
    ( '508B', 2,  0.0268,  96.0),
    ( '506B', 2,  0.0164, 122.0),
]

CHROMALOX_MI_COLD_LEADS = [
    # (option_code, length_m)
    # Source: mod-mi.ashx — #12 AWG copper, 4 ft standard cold lead
    # R ≈ 5.21 mΩ/m at 20°C, ampacity ~20A per NEC 310 60°C column
    ('CL-4FT', 1.219),
]


# ---------------------------------------------------------------------------
# Heater conductor / resistance-temperature basis
# ---------------------------------------------------------------------------

THERMON_MIQ_CONDUCTOR_MATERIAL = 'Nickel-Chromium'
THERMON_MIQ_TCR_PER_DEGREE_C = 0.000088

NVENT_CONDUCTOR_BASIS_BY_PREFIX = {
    'HAF': ('Nickel-Chromium', 0.000088),
    'HAA': ('Nickel-Chromium', 0.000085),
    'HAQ': ('Nickel Alloy Q', 0.000500),
    'HAP': ('Nickel Alloy P', 0.001300),
    'HAC': ('Alloy 825 Conductor', 0.003900),
}


def _chromalox_conductor_basis(part_number):
    code = int(part_number.rstrip('B'))
    if code in {506, 508} or 103 <= code <= 115:
        return 'Alloy 825 Conductor', 0.003930
    if 200 <= code <= 210:
        return 'Nickel Alloy Q', 0.000500
    if 310 <= code <= 410:
        return 'Nichrome T', 0.000180
    return 'Nickel-Chromium', 0.000100


def heater_conductor_basis(vendor, part_number):
    """Return the conductor material and TCR for the published heater code."""
    if vendor == 'THR':
        return THERMON_MIQ_CONDUCTOR_MATERIAL, THERMON_MIQ_TCR_PER_DEGREE_C
    if vendor == 'nVN':
        for prefix, basis in NVENT_CONDUCTOR_BASIS_BY_PREFIX.items():
            if part_number.startswith(prefix):
                return basis
    if vendor == 'CHR':
        return _chromalox_conductor_basis(part_number)
    return '', 0.0


# ---------------------------------------------------------------------------
# Family definitions
# ---------------------------------------------------------------------------

FAMILIES = [
    {
        'vendor': 'THR',
        'family_name': 'MIQ',
        'alloy_type': 'Alloy 825',
        'max_voltage': 600.0,
        'max_sheath_temp_c': 600.0,
        'max_maintain_temp_c': 500.0,
        'max_exposure_temp_c': 600.0,
        'max_watt_density_w_m': 250.0,
        'min_circuit_length_m': 1.0,
        'max_circuit_length_m': 200.0,
        'temp_class_rating': '',
        'gas_group': 'IIC',
        'zone_approval': 'Zone 1, Zone 2',
        'source_document': 'TEP0020-MIQ-Spec.pdf',
        'is_validated': False,
        'heaters': THERMON_MIQ_HEATERS,
        'cold_leads': THERMON_MIQ_COLD_LEADS,
    },
    {
        'vendor': 'nVN',
        'family_name': 'XMI-A62',
        'alloy_type': 'Alloy 825',
        'max_voltage': 600.0,
        'max_sheath_temp_c': 500.0,
        'max_maintain_temp_c': 538.0,
        'max_exposure_temp_c': 600.0,
        'max_watt_density_w_m': 250.0,
        'min_circuit_length_m': 1.0,
        'max_circuit_length_m': 312.0,
        'temp_class_rating': '',
        'gas_group': 'IIC',
        'zone_approval': 'Zone 1, Zone 2',
        'source_document': 'Raychem-DS-H56870-XMIA-EN-1810',
        'is_validated': False,
        'heaters': NVENT_XMIA_HEATERS,
        'cold_leads': NVENT_XMIA_COLD_LEADS,
    },
    {
        'vendor': 'CHR',
        'family_name': 'MI-825B',
        'alloy_type': 'Alloy 825',
        'max_voltage': 600.0,
        'max_sheath_temp_c': 400.0,
        'max_maintain_temp_c': 400.0,
        'max_exposure_temp_c': 450.0,
        'max_watt_density_w_m': 200.0,
        'min_circuit_length_m': 1.0,
        'max_circuit_length_m': 200.0,
        'temp_class_rating': '',
        'gas_group': 'IIC',
        'zone_approval': 'Zone 1, Zone 2',
        'source_document': 'Chromalox-mod-mi.pdf',
        'is_validated': False,
        'heaters': CHROMALOX_MI_HEATERS,
        'cold_leads': CHROMALOX_MI_COLD_LEADS,
    },
]


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        'Populate MI cable catalogue with Thermon MIQ, nVent XMI-A62, and Chromalox MI-825B data. '
        'All families are created with is_validated=False. '
        'KR must verify each row against the source document and set is_validated=True via Django admin.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--vendor',
            choices=['THR', 'nVN', 'CHR'],
            default=None,
            help='Load only one vendor. Omit to load all three.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Print what would be created without writing to the database.',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            default=False,
            help='Update existing MI family, heater, and cold-lead catalogue rows from this command data.',
        )

    def handle(self, *args, **options):
        target_vendor = options['vendor']
        dry_run = options['dry_run']
        update_existing = options['update']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no database writes.'))
        if update_existing:
            self.stdout.write(self.style.WARNING('UPDATE mode — existing catalogue rows will be refreshed.'))

        families_to_load = [
            f for f in FAMILIES
            if target_vendor is None or f['vendor'] == target_vendor
        ]

        total_families = total_heaters = total_cold_leads = 0

        for family_data in families_to_load:
            vendor = family_data['vendor']
            family_name = family_data['family_name']

            family_defaults = {k: v for k, v in family_data.items()
                               if k not in ('heaters', 'cold_leads', 'vendor', 'family_name')}

            if dry_run:
                self.stdout.write(f'  [DRY] Family: {vendor} {family_name}')
                for part_number, conductors, resistance, max_current in family_data['heaters']:
                    conductor_material, tcr_per_degree_c = heater_conductor_basis(vendor, part_number)
                    self.stdout.write(
                        f'        Heater: {part_number} '
                        f'({resistance} Ω/m, {max_current} A, '
                        f'{conductor_material}, TCR={tcr_per_degree_c})'
                    )
                    for option_code, length_m in family_data['cold_leads']:
                        self.stdout.write(f'          Cold lead: {option_code} {length_m} m')
                total_families += 1
                total_heaters += len(family_data['heaters'])
                total_cold_leads += len(family_data['heaters']) * len(family_data['cold_leads'])
                continue

            family, family_created = MICableFamily.objects.get_or_create(
                vendor=vendor,
                family_name=family_name,
                defaults=family_defaults,
            )
            if update_existing and not family_created:
                for field, value in family_defaults.items():
                    if field != 'is_validated':
                        setattr(family, field, value)
                family.save()
            total_families += 1

            action = 'Created' if family_created else ('Updated' if update_existing else 'Exists')
            self.stdout.write(f'  {action}: {vendor} {family_name} (id={family.pk})')

            for part_number, conductors, resistance_ohms_m, max_current_a in family_data['heaters']:
                conductor_material, tcr_per_degree_c = heater_conductor_basis(vendor, part_number)
                heater_defaults = {
                    'family': family,
                    'conductors': conductors,
                    'resistance_ohms_m': resistance_ohms_m,
                    'max_current_a': max_current_a,
                    'cold_lead_resistance_ohms_m': 0.0,
                    'cold_lead_max_ampacity_a': 0.0,
                    'sheath_material': family_data['alloy_type'],
                    'conductor_material': conductor_material,
                    'tcr_per_degree_c': tcr_per_degree_c,
                }
                heater, heater_created = MICableHeater.objects.get_or_create(
                    part_number=part_number,
                    defaults=heater_defaults,
                )
                if update_existing and not heater_created:
                    for field, value in heater_defaults.items():
                        setattr(heater, field, value)
                    heater.save()
                total_heaters += 1

                for option_code, length_m in family_data['cold_leads']:
                    cold_lead, cl_created = MIColdLeadOption.objects.get_or_create(
                        heater=heater,
                        option_code=option_code,
                        defaults={'length_m': length_m},
                    )
                    if update_existing and not cl_created:
                        cold_lead.length_m = length_m
                        cold_lead.save()
                    total_cold_leads += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\nDRY RUN complete. Would create: '
                f'{total_families} families, {total_heaters} heaters, {total_cold_leads} cold lead options.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nDone. Processed: '
                f'{total_families} families, {total_heaters} heaters, {total_cold_leads} cold lead options.'
            ))
            self.stdout.write(self.style.WARNING(
                '\nIMPORTANT: All families have is_validated=False. '
                'Open Django admin → MI Cable Families and verify each row against the source document '
                'before setting is_validated=True.'
            ))
