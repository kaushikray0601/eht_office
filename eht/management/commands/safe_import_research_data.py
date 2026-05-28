"""
SAFE IMPORT MANAGEMENT COMMAND
==============================

This command carefully imports researched vendor data with multiple validation layers:
1. Loads research CSV
2. Compares with existing database
3. Identifies truly new records
4. Shows preview of what will be added
5. Requires explicit confirmation
6. Validates before committing to database

Usage:
    python manage.py safe_import_research_data --csv-path <path>
    python manage.py safe_import_research_data --csv-path <path> --skip-confirmation
    python manage.py safe_import_research_data --preview-only
"""

import csv
from django.core.management.base import BaseCommand
from django.db.models import Q
from eht.models import ElecEHT_Vendor
from decimal import Decimal


class Command(BaseCommand):
    help = 'Safely import researched vendor cable data with validation and comparison'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='/home/kr/mydev/eht_office/RESEARCH_DATA/new_records_for_review.csv',
            help='Path to research CSV file'
        )
        parser.add_argument(
            '--preview-only',
            action='store_true',
            help='Show what would be added without confirming import'
        )
        parser.add_argument(
            '--skip-confirmation',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        preview_only = options['preview_only']
        skip_confirm = options['skip_confirmation']

        self.stdout.write(self.style.WARNING('\n' + '='*80))
        self.stdout.write(self.style.WARNING('SAFE RESEARCH DATA IMPORT'))
        self.stdout.write(self.style.WARNING('='*80))

        # Step 1: Load research CSV
        self.stdout.write('\n📂 Loading research CSV...')
        research_records = self._load_research_csv(csv_path)
        if not research_records:
            self.stdout.write(self.style.ERROR('❌ Failed to load research CSV'))
            return

        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {len(research_records)} candidate records'))

        # Step 2: Compare with existing database
        self.stdout.write('\n🔍 Comparing with existing database...')
        new_records, existing_records, duplicates = self._identify_new_records(research_records)

        # Step 3: Summary
        self.stdout.write(self.style.SUCCESS(f'\n📊 COMPARISON RESULTS:'))
        self.stdout.write(f'  Total candidates:    {len(research_records)}')
        self.stdout.write(self.style.SUCCESS(f'  ✅ Truly new:        {len(new_records)}'))
        self.stdout.write(self.style.WARNING(f'  ⚠️  Already exist:    {len(existing_records)}'))
        self.stdout.write(f'  Duplicates in CSV:   {len(duplicates)}')

        if not new_records:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  No new records to add. All candidates already in database.'
            ))
            return

        # Step 4: Show preview
        self.stdout.write(self.style.SUCCESS(f'\n📋 PREVIEW OF NEW RECORDS ({len(new_records)} records):'))
        self._show_preview(new_records)

        # Step 5: Show existing records that matched
        if existing_records:
            self.stdout.write(self.style.WARNING(f'\n⚠️  RECORDS ALREADY IN DATABASE ({len(existing_records)}):'))
            self._show_existing(existing_records)

        if preview_only:
            self.stdout.write(self.style.WARNING('\n📌 Preview mode - no data was imported'))
            return

        # Step 6: Confirm before import
        if not skip_confirm:
            self.stdout.write(f'\n⚠️  This will ADD {len(new_records)} new records to the database.')
            confirm = input('Proceed? (yes/no): ').strip().lower()
            if confirm != 'yes':
                self.stdout.write(self.style.WARNING('❌ Import cancelled.'))
                return

        # Step 7: Import
        self.stdout.write('\n⏳ Importing new records...')
        try:
            created_count = 0
            for record in new_records:
                obj = ElecEHT_Vendor(**record)
                obj.save()
                created_count += 1
                self.stdout.write(f'  ✅ {obj.V_UID}')

            self.stdout.write(self.style.SUCCESS(
                f'\n✅ IMPORT COMPLETE: {created_count} records added'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Import failed: {str(e)}'))
            return

        # Step 8: Verify
        final_count = ElecEHT_Vendor.objects.count()
        self.stdout.write(f'\nDatabase now contains: {final_count} total records')

        self.stdout.write(self.style.SUCCESS('\n✅ SAFE IMPORT COMPLETE'))
        self.stdout.write(self.style.WARNING('='*80 + '\n'))

    def _load_research_csv(self, csv_path):
        """Load and parse research CSV file"""
        records = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):
                    try:
                        record_dict = {
                            'V_UID': row['V_UID'].strip(),
                            'Vendor': row['Vendor'].strip(),
                            'Tracer_Family': row['Tracer_Family'].strip(),
                            'Tracer_Model': row['Tracer_Model'].strip(),
                            'Tracer_Cat_No': row['Tracer_Cat_No'].strip(),
                            'Voltage': Decimal(row['Voltage'].strip()),
                            'Zone': row['Zone'].strip(),
                            'Gas_Group': row['Gas_Group'].strip(),
                            'T_Rating': row['T_Rating'].strip(),
                            'A_Coeff': Decimal(row['A_Coeff'].strip()),
                            'B_Coeff': Decimal(row['B_Coeff'].strip()),
                            'C_Coeff': Decimal(row['C_Coeff'].strip()),
                            'Maint_T': Decimal(row['Maint_T'].strip()),
                            'Max_Op_T': Decimal(row['Max_Op_T'].strip()),
                            'Min_Installation_T': Decimal(row['Min_Installation_T'].strip()),
                            'Max_Exp_T_On': Decimal(row['Max_Exp_T_On'].strip()),
                            'Max_Exp_T_Off': Decimal(row['Max_Exp_T_Off'].strip()),
                            'Power_at_Startup_T': Decimal(row['Power_at_Startup_T'].strip()),
                            'Ohm_per_km': Decimal(row['Ohm_per_km'].strip()),
                            'Res_corrFactor_Mica': Decimal(row['Res_corrFactor_Mica'].strip()),
                        }
                        records.append(record_dict)
                    except ValueError as e:
                        self.stdout.write(self.style.ERROR(f'  Row {row_num} parse error: {str(e)}'))
                        continue
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'CSV file not found: {csv_path}'))
            return None

        return records

    def _identify_new_records(self, research_records):
        """Compare research records with database, return new/existing/duplicates"""
        new_records = []
        existing_records = []
        duplicates = []
        seen_vuids = set()

        for record in research_records:
            v_uid = record['V_UID']

            # Check for duplicates within CSV
            if v_uid in seen_vuids:
                duplicates.append(record)
                continue
            seen_vuids.add(v_uid)

            # Check if already in database by V_UID
            if ElecEHT_Vendor.objects.filter(V_UID=v_uid).exists():
                existing_records.append(record)
                continue

            # Check for functionally equivalent records
            # (same vendor + model + voltage + power might indicate existing record)
            equivalent = ElecEHT_Vendor.objects.filter(
                Vendor=record['Vendor'],
                Tracer_Model=record['Tracer_Model'],
                Voltage=record['Voltage'],
                Power_at_Startup_T=record['Power_at_Startup_T']
            ).exists()

            if equivalent:
                existing_records.append(record)
                continue

            # This is a new record
            new_records.append(record)

        return new_records, existing_records, duplicates

    def _show_preview(self, records):
        """Display preview of records that will be added"""
        grouped = {}
        for rec in records:
            vendor = rec['Vendor']
            if vendor not in grouped:
                grouped[vendor] = []
            grouped[vendor].append(rec)

        for vendor in sorted(grouped.keys()):
            self.stdout.write(f'\n  {vendor}:')
            for rec in grouped[vendor]:
                self.stdout.write(
                    f'    • {rec["Tracer_Model"]:15} {rec["Power_at_Startup_T"]:6.1f}W @ '
                    f'{rec["Voltage"]:6.1f}V | {rec["V_UID"]}'
                )

    def _show_existing(self, records):
        """Display records that already exist in database"""
        grouped = {}
        for rec in records:
            vendor = rec['Vendor']
            if vendor not in grouped:
                grouped[vendor] = []
            grouped[vendor].append(rec)

        for vendor in sorted(grouped.keys()):
            self.stdout.write(f'\n  {vendor}:')
            for rec in grouped[vendor]:
                self.stdout.write(
                    f'    • {rec["Tracer_Model"]:15} {rec["Power_at_Startup_T"]:6.1f}W @ '
                    f'{rec["Voltage"]:6.1f}V'
                )
