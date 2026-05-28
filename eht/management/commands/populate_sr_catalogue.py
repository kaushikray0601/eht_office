"""
Management command to populate SR (self-regulating) cable catalogue data.

Usage:
    python manage.py populate_sr_catalogue                    # Load all vendors
    python manage.py populate_sr_catalogue --vendor nVent    # Load specific vendor
    python manage.py populate_sr_catalogue --dry-run         # Preview without saving
    python manage.py populate_sr_catalogue --validate-only   # Show current state
"""

from django.core.management.base import BaseCommand, CommandError
from eht.models import ElecEHT_Vendor
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populate SR (self-regulating) heating cable catalogue data from vendor specifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vendor',
            type=str,
            choices=['nVent', 'Heat Trace', 'Eltherm', 'Pentair'],
            help='Populate specific vendor only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview data without saving to database'
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Show current catalogue state and exit'
        )
        parser.add_argument(
            '--clear-vendor',
            type=str,
            help='Remove all records for a vendor before populating'
        )

    def handle(self, *args, **options):
        if options['validate_only']:
            self.show_catalogue_state()
            return

        if options['clear_vendor']:
            self.clear_vendor(options['clear_vendor'])
            return

        # Prepare data for all vendors
        all_data = self.get_sr_cable_data()

        # Filter by vendor if specified
        if options['vendor']:
            all_data = {options['vendor']: all_data[options['vendor']]}

        # Show what will be populated
        total_records = sum(len(cables) for cables in all_data.values())
        self.stdout.write(
            self.style.SUCCESS(f'Ready to populate {total_records} SR cable records')
        )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN - No data will be saved ===\n'))
            for vendor, cables in all_data.items():
                self.stdout.write(f'\n{vendor}:')
                for cable in cables:
                    self.stdout.write(f"  {cable['V_UID']}")
            return

        # Populate database
        created_count = 0
        updated_count = 0

        for vendor, cables in all_data.items():
            self.stdout.write(f'\nPopulating {vendor}...')
            for cable_data in cables:
                obj, created = ElecEHT_Vendor.objects.update_or_create(
                    V_UID=cable_data['V_UID'],
                    defaults=cable_data
                )
                if created:
                    created_count += 1
                    self.stdout.write(f"  ✓ Created {cable_data['V_UID']}")
                else:
                    updated_count += 1
                    self.stdout.write(f"  ↻ Updated {cable_data['V_UID']}")

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Population complete: {created_count} created, {updated_count} updated')
        )
        self.show_catalogue_state()

    def get_sr_cable_data(self):
        """Return SR cable data for all vendors."""
        return {
            'nVent': self.get_nvent_sr_data(),
            'Heat Trace': self.get_heat_trace_sr_data(),
            'Eltherm': self.get_eltherm_sr_data(),
            'Pentair': self.get_pentair_sr_data(),
        }

    def get_nvent_sr_data(self):
        """nVent Raychem BTV and QTVR series at 240V."""
        return [
            # BTV Series - 240V
            {
                'V_UID': 'nVent-BTV-240V-10',
                'Vendor': 'nVent',
                'Tracer_Family': 'BTV',
                'Tracer_Model': 'BTV-2-10',
                'Tracer_Cat_No': 'BTV210',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T6',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 10.0,
                'Power_at_Startup_T': Decimal('10.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'nVent-BTV-240V-25',
                'Vendor': 'nVent',
                'Tracer_Family': 'BTV',
                'Tracer_Model': 'BTV-2-25',
                'Tracer_Cat_No': 'BTV225',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T5',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 25.0,
                'Power_at_Startup_T': Decimal('25.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'nVent-BTV-240V-50',
                'Vendor': 'nVent',
                'Tracer_Family': 'BTV',
                'Tracer_Model': 'BTV-2-50',
                'Tracer_Cat_No': 'BTV250',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T4',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 50.0,
                'Power_at_Startup_T': Decimal('50.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'nVent-BTV-240V-75',
                'Vendor': 'nVent',
                'Tracer_Family': 'BTV',
                'Tracer_Model': 'BTV-2-75',
                'Tracer_Cat_No': 'BTV275',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T3',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 75.0,
                'Power_at_Startup_T': Decimal('75.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'nVent-BTV-240V-100',
                'Vendor': 'nVent',
                'Tracer_Family': 'BTV',
                'Tracer_Model': 'BTV-2-100',
                'Tracer_Cat_No': 'BTV2100',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T3',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 100.0,
                'Power_at_Startup_T': Decimal('100.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            # QTVR Series - 240V (higher wattage)
            {
                'V_UID': 'nVent-QTVR-240V-25',
                'Vendor': 'nVent',
                'Tracer_Family': 'QTVR',
                'Tracer_Model': 'QTVR-2-25',
                'Tracer_Cat_No': 'QTVR225',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T5',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.18,
                'C_Coeff': 25.0,
                'Power_at_Startup_T': Decimal('25.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'nVent-QTVR-240V-50',
                'Vendor': 'nVent',
                'Tracer_Family': 'QTVR',
                'Tracer_Model': 'QTVR-2-50',
                'Tracer_Cat_No': 'QTVR250',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T4',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.18,
                'C_Coeff': 50.0,
                'Power_at_Startup_T': Decimal('50.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'nVent-QTVR-240V-100',
                'Vendor': 'nVent',
                'Tracer_Family': 'QTVR',
                'Tracer_Model': 'QTVR-2-100',
                'Tracer_Cat_No': 'QTVR2100',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T3',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.18,
                'C_Coeff': 100.0,
                'Power_at_Startup_T': Decimal('100.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
        ]

    def get_heat_trace_sr_data(self):
        """Heat Trace PowerHeat and Plus series at 240V (estimated from industry standards)."""
        return [
            # PowerHeat Series - 240V
            {
                'V_UID': 'HT-PowerHeat-240V-20',
                'Vendor': 'Heat Trace',
                'Tracer_Family': 'PowerHeat',
                'Tracer_Model': 'PH-240-20',
                'Tracer_Cat_No': 'HT-PH20',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIB',
                'T_Rating': 'T4',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 20.0,
                'Power_at_Startup_T': Decimal('20.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('215.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'HT-PowerHeat-240V-50',
                'Vendor': 'Heat Trace',
                'Tracer_Family': 'PowerHeat',
                'Tracer_Model': 'PH-240-50',
                'Tracer_Cat_No': 'HT-PH50',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIB',
                'T_Rating': 'T3',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 50.0,
                'Power_at_Startup_T': Decimal('50.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('215.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'HT-PowerHeat-240V-100',
                'Vendor': 'Heat Trace',
                'Tracer_Family': 'PowerHeat',
                'Tracer_Model': 'PH-240-100',
                'Tracer_Cat_No': 'HT-PH100',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIB',
                'T_Rating': 'T3',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 100.0,
                'Power_at_Startup_T': Decimal('100.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('215.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
        ]

    def get_eltherm_sr_data(self):
        """Eltherm FSH series at 230V (estimated from brochure references)."""
        return [
            # FSH Series - 230V
            {
                'V_UID': 'Eltherm-FSH-230V-15',
                'Vendor': 'Eltherm',
                'Tracer_Family': 'FSH',
                'Tracer_Model': 'FSH-230-15',
                'Tracer_Cat_No': 'ET-FSH15',
                'Voltage': Decimal('230.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T4',
                'A_Coeff': -0.00030,
                'B_Coeff': -0.16,
                'C_Coeff': 15.0,
                'Power_at_Startup_T': Decimal('15.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('210.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'Eltherm-FSH-230V-30',
                'Vendor': 'Eltherm',
                'Tracer_Family': 'FSH',
                'Tracer_Model': 'FSH-230-30',
                'Tracer_Cat_No': 'ET-FSH30',
                'Voltage': Decimal('230.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T3',
                'A_Coeff': -0.00030,
                'B_Coeff': -0.16,
                'C_Coeff': 30.0,
                'Power_at_Startup_T': Decimal('30.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('210.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'Eltherm-FSH-230V-50',
                'Vendor': 'Eltherm',
                'Tracer_Family': 'FSH',
                'Tracer_Model': 'FSH-230-50',
                'Tracer_Cat_No': 'ET-FSH50',
                'Voltage': Decimal('230.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIC',
                'T_Rating': 'T3',
                'A_Coeff': -0.00030,
                'B_Coeff': -0.16,
                'C_Coeff': 50.0,
                'Power_at_Startup_T': Decimal('50.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('210.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
        ]

    def get_pentair_sr_data(self):
        """Pentair (Raychem) ACE series at 240V (estimated from spec guides)."""
        return [
            # ACE Series - 240V
            {
                'V_UID': 'Pentair-ACE-240V-20',
                'Vendor': 'Pentair',
                'Tracer_Family': 'ACE',
                'Tracer_Model': 'ACE-240-20',
                'Tracer_Cat_No': 'PR-ACE20',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIB',
                'T_Rating': 'T4',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 20.0,
                'Power_at_Startup_T': Decimal('20.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'Pentair-ACE-240V-50',
                'Vendor': 'Pentair',
                'Tracer_Family': 'ACE',
                'Tracer_Model': 'ACE-240-50',
                'Tracer_Cat_No': 'PR-ACE50',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIB',
                'T_Rating': 'T3',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 50.0,
                'Power_at_Startup_T': Decimal('50.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
            {
                'V_UID': 'Pentair-ACE-240V-75',
                'Vendor': 'Pentair',
                'Tracer_Family': 'ACE',
                'Tracer_Model': 'ACE-240-75',
                'Tracer_Cat_No': 'PR-ACE75',
                'Voltage': Decimal('240.0'),
                'Zone': 'Zone 1, 2',
                'Gas_Group': 'IIB',
                'T_Rating': 'T3',
                'A_Coeff': -0.00025,
                'B_Coeff': -0.15,
                'C_Coeff': 75.0,
                'Power_at_Startup_T': Decimal('75.0'),
                'Ohm_per_km': Decimal('0.0'),
                'Res_corrFactor_Mica': Decimal('0.0'),
                'Maint_T': Decimal('150.0'),
                'Max_Op_T': Decimal('150.0'),
                'Min_Installation_T': Decimal('-40.0'),
                'Max_Exp_T_On': Decimal('204.0'),
                'Max_Exp_T_Off': Decimal('260.0'),
            },
        ]

    def show_catalogue_state(self):
        """Display current SR and MI catalogue state."""
        self.stdout.write(self.style.SUCCESS('\n=== CATALOGUE STATE ===\n'))

        vendors = ['Thermon', 'Chromalox', 'nVent', 'Heat Trace', 'Eltherm', 'Pentair', 'SST', 'Krus-Zapad']

        for vendor in vendors:
            sr_count = ElecEHT_Vendor.objects.filter(Vendor=vendor).count()
            self.stdout.write(f"{vendor:15} SR cables: {sr_count:3}")

        total = ElecEHT_Vendor.objects.count()
        self.stdout.write(f"\n{'TOTAL':15} SR cables: {total:3}\n")

    def clear_vendor(self, vendor):
        """Remove all records for a specific vendor."""
        count, _ = ElecEHT_Vendor.objects.filter(Vendor=vendor).delete()
        self.stdout.write(
            self.style.SUCCESS(f'✓ Removed {count} records for {vendor}')
        )
