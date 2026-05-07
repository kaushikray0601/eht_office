from django.core.management.base import BaseCommand
from eht.models import MICableFamily, MICableHeater, MIAlloyTempFactor

class Command(BaseCommand):
    help = 'Populates the database with default MI Cable catalogue data for Thermon and nVent.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting MI Cable database population...")

        # 1. Create MI Cable Families
        thermon_miq, created = MICableFamily.objects.get_or_create(
            vendor='THR',
            family_name='MIQ',
            defaults={
                'alloy_type': 'Alloy 825',
                'max_voltage': 600.0,
                'max_sheath_temp_c': 600.0,
                'max_maintain_temp_c': 500.0,
                'max_watt_density_w_m': 250.0,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created Thermon MIQ Family'))

        nvent_xmi, created = MICableFamily.objects.get_or_create(
            vendor='nVN',
            family_name='XMI-A',
            defaults={
                'alloy_type': 'Alloy 825',
                'max_voltage': 600.0,
                'max_sheath_temp_c': 600.0,
                'max_maintain_temp_c': 500.0,
                'max_watt_density_w_m': 250.0,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created nVent XMI-A Family'))

        chromalox_mi, created = MICableFamily.objects.get_or_create(
            vendor='CHR',
            family_name='CMR',
            defaults={
                'alloy_type': 'Alloy 825',
                'max_voltage': 600.0,
                'max_sheath_temp_c': 600.0,
                'max_maintain_temp_c': 500.0,
                'max_watt_density_w_m': 250.0,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created Chromalox CMR Family'))

        # 2. Populate Alloy Temperature Factors (Alloy 825)
        # Alloy 825 resistance increases roughly by 0.00012 per degree C above 20C.
        temp_curve = [
            (20.0, 1.000),
            (100.0, 1.009),
            (200.0, 1.020),
            (300.0, 1.031),
            (400.0, 1.042),
            (500.0, 1.054),
            (600.0, 1.065),
        ]
        
        for temp, multiplier in temp_curve:
            factor, created = MIAlloyTempFactor.objects.get_or_create(
                alloy_type='Alloy 825',
                temperature_c=temp,
                defaults={'resistance_multiplier': multiplier}
            )

        self.stdout.write(self.style.SUCCESS('Populated Alloy 825 Temperature Curve'))

        # 3. Populate Heaters (Representative standard resistance range Ohms/km)
        # We'll use a standard array of resistances common to MI cables:
        # e.g., 10, 16, 25, 40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000, 20000
        
        resistances = [
            10.0, 16.0, 25.0, 40.0, 63.0, 100.0, 160.0, 250.0, 
            400.0, 630.0, 1000.0, 1600.0, 2500.0, 4000.0, 6300.0, 10000.0, 20000.0, 30000.0
        ]
        
        count = 0
        
        for idx, res in enumerate(resistances, start=1):
            # Thermon Single Core
            MICableHeater.objects.get_or_create(
                family=thermon_miq,
                part_number=f"1MIQ{int(res)}",
                defaults={
                    'conductors': 1,
                    'base_resistance_ohms_km': res,
                    'max_ampacity': 60.0,
                }
            )
            # Thermon Dual Core
            MICableHeater.objects.get_or_create(
                family=thermon_miq,
                part_number=f"2MIQ{int(res)}",
                defaults={
                    'conductors': 2,
                    'base_resistance_ohms_km': res,
                    'max_ampacity': 60.0,
                }
            )
            
            # nVent Single Core
            MICableHeater.objects.get_or_create(
                family=nvent_xmi,
                part_number=f"61XMI{int(res)}",
                defaults={
                    'conductors': 1,
                    'base_resistance_ohms_km': res,
                    'max_ampacity': 60.0,
                }
            )
            # nVent Dual Core
            MICableHeater.objects.get_or_create(
                family=nvent_xmi,
                part_number=f"62XMI{int(res)}",
                defaults={
                    'conductors': 2,
                    'base_resistance_ohms_km': res,
                    'max_ampacity': 60.0,
                }
            )

            # Chromalox Single Core
            MICableHeater.objects.get_or_create(
                family=chromalox_mi,
                part_number=f"CMR1-{int(res)}",
                defaults={
                    'conductors': 1,
                    'base_resistance_ohms_km': res,
                    'max_ampacity': 60.0,
                }
            )

            count += 5

        self.stdout.write(self.style.SUCCESS(f'Successfully populated {count} MICableHeater records across vendors.'))
