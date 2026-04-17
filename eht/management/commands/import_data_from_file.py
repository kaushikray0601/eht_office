import csv
from django.core.management.base import BaseCommand
from eht.models import ElecEHT_ThermalConductivity, ElecEHT_Vendor, ElecEHT_ASMEB36 # import other models


class Command(BaseCommand):
    help = "Imports initial data from CSV files."

    def handle(self, *args, **options):
        # import ThermalConductivity data
        self.import_data_from_csv("eht/tmp/elecEHT_ThermalConductivity.csv", ElecEHT_ThermalConductivity, ['Ins_Mat_Type', 'K_factor_A', 'K_factor_B', 'K_factor_C'])

        # import Vendor data
        self.import_data_from_csv("eht/tmp/elecEHT_Vendor.csv", ElecEHT_Vendor, ['V_UID', 'Vendor', 'Tracer_Family', 'Tracer_Model', 'Tracer_Cat_No', 'Voltage', 'Zone', 'Gas_Group', 'T_Rating', 'A_Coeff', 'B_Coeff', 'C_Coeff', 'Maint_T', 'Max_Op_T', 'Min_Installation_T', 'Max_Exp_T_On', 'Max_Exp_T_Off', 'Power_at_Startup_T', 'Ohm_per_km', 'Res_corrFactor_Mica'])
        
        #import ASME B36 data
        self.import_data_from_csv("eht/tmp/elecEHT_ASMEB36.csv", ElecEHT_ASMEB36, ['Nominal_Pipe_Size', 'Outside_Diameter', 'Wall_Thickness', 'Plain_End_Weight', 'Schedule_No', 'Nominal_Diameter', 'Outside_Diameter_mm', 'Wall_Thickness_mm', 'Plain_end_Mass'])


        self.stdout.write(self.style.SUCCESS('Successfully imported initial data.'))

    def import_data_from_csv(self, csv_path, model, field_names):
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    instance = model()
                    for field in field_names:
                        value = row.get(field) #Use get to avoid key error, if key is missing
                        if value is not None:
                          try:
                            setattr(instance, field, value)
                          except ValueError as e:
                              print(f"Error setting value of '{value}' for field '{field}': {e}")
                              # You can add logging here
                    instance.save()
                except Exception as e:
                  print(f"Error creating record for row {row} : {e}")
                    # You can add logging here