import csv
from django.core.management.base import BaseCommand
from django.db.models import Count
from eht.models import ElecEHT_Vendor


class Command(BaseCommand):
    help = 'Restore vendor catalogue from backup CSV file (STEP 3: Restore from authoritative backup)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='/home/kr/mydev/eht_office/eht/tmp/elecEHT_Vendor.csv',
            help='Path to backup CSV file'
        )
        parser.add_argument(
            '--skip-confirmation',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        skip_confirm = options['skip_confirmation']

        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('STEP 3: RESTORE VENDOR CATALOGUE FROM BACKUP CSV'))
        self.stdout.write(self.style.WARNING('='*70))

        # Check current state
        current_count = ElecEHT_Vendor.objects.count()
        self.stdout.write(f'\nCurrent database state: {current_count} records')

        if current_count > 0:
            self.stdout.write(self.style.ERROR(
                f'\n⚠️  WARNING: Database is NOT empty! ({current_count} records present)'
            ))
            self.stdout.write(self.style.ERROR(
                'STEP 3 expects an EMPTY database (from STEP 2).'
            ))
            self.stdout.write(self.style.ERROR(
                'Did you complete STEP 2 (delete all records)?'
            ))
            if not skip_confirm:
                confirm = input('\nContinue anyway? (yes/no): ').strip().lower()
                if confirm != 'yes':
                    self.stdout.write(self.style.ERROR('Cancelled.'))
                    return

        # Read and validate CSV
        self.stdout.write(f'\n📂 Reading backup CSV: {csv_path}')
        records_to_load = []
        errors = []

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):
                    try:
                        record = ElecEHT_Vendor(
                            V_UID=row['V_UID'].strip(),
                            Vendor=row['Vendor'].strip(),
                            Tracer_Family=row['Tracer_Family'].strip(),
                            Tracer_Model=row['Tracer_Model'].strip(),
                            Tracer_Cat_No=row['Tracer_Cat_No'].strip(),
                            Voltage=float(row['Voltage'].strip()),
                            Zone=row['Zone'].strip(),
                            Gas_Group=row['Gas_Group'].strip(),
                            T_Rating=row['T_Rating'].strip(),
                            A_Coeff=float(row['A_Coeff'].strip()),
                            B_Coeff=float(row['B_Coeff'].strip()),
                            C_Coeff=float(row['C_Coeff'].strip()),
                            Maint_T=float(row['Maint_T'].strip()),
                            Max_Op_T=float(row['Max_Op_T'].strip()),
                            Min_Installation_T=float(row['Min_Installation_T'].strip()),
                            Max_Exp_T_On=float(row['Max_Exp_T_On'].strip()),
                            Max_Exp_T_Off=float(row['Max_Exp_T_Off'].strip()),
                            Power_at_Startup_T=float(row['Power_at_Startup_T'].strip()),
                            Ohm_per_km=float(row['Ohm_per_km'].strip()),
                            Res_corrFactor_Mica=float(row['Res_corrFactor_Mica'].strip()),
                        )
                        records_to_load.append(record)
                    except ValueError as e:
                        errors.append(f'Row {row_num}: {str(e)}')
                    except KeyError as e:
                        errors.append(f'Row {row_num}: Missing column {str(e)}')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'\n❌ CSV file not found: {csv_path}'))
            return

        if errors:
            self.stdout.write(self.style.ERROR(f'\n❌ Found {len(errors)} validation errors:'))
            for err in errors[:10]:
                self.stdout.write(f'  - {err}')
            if len(errors) > 10:
                self.stdout.write(f'  ... and {len(errors) - 10} more')
            return

        self.stdout.write(self.style.SUCCESS(f'\n✅ Validated {len(records_to_load)} records from CSV'))

        # Confirm before bulk insert
        if not skip_confirm:
            self.stdout.write(f'\nAbout to restore {len(records_to_load)} records to the database.')
            confirm = input('Proceed? (yes/no): ').strip().lower()
            if confirm != 'yes':
                self.stdout.write(self.style.WARNING('Cancelled.'))
                return

        # Bulk insert
        self.stdout.write('\n⏳ Bulk inserting records...')
        try:
            ElecEHT_Vendor.objects.bulk_create(
                records_to_load,
                batch_size=100,
                ignore_conflicts=False
            )
            self.stdout.write(self.style.SUCCESS(f'\n✅ STEP 3 COMPLETE: {len(records_to_load)} records restored'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Bulk insert failed: {str(e)}'))
            return

        # Verify
        final_count = ElecEHT_Vendor.objects.count()
        self.stdout.write(f'\nDatabase now contains: {final_count} records')

        # Summary by vendor
        self.stdout.write(self.style.SUCCESS('\n📊 BREAKDOWN BY VENDOR:'))
        vendor_counts = (ElecEHT_Vendor.objects
                        .values('Vendor')
                        .annotate(count=Count('id'))
                        .order_by('Vendor'))
        for vc in vendor_counts:
            self.stdout.write(f'  {vc["Vendor"]}: {vc["count"]} records')

        # Summary by Tracer_Family
        self.stdout.write(self.style.SUCCESS('\n📊 BREAKDOWN BY TRACER_FAMILY:'))
        family_counts = (ElecEHT_Vendor.objects
                        .values('Tracer_Family')
                        .annotate(count=Count('id'))
                        .order_by('Tracer_Family'))
        for fc in family_counts:
            self.stdout.write(f'  {fc["Tracer_Family"]}: {fc["count"]} records')

        self.stdout.write(self.style.SUCCESS('\n✅ Ready for STEP 4: Enrich with new vendor data'))
        self.stdout.write(self.style.WARNING('='*70 + '\n'))
