
import pandas as pd
from django.db.models import FloatField
from django.db.models.functions import Cast

from eht.calculations.heat_loss import calculate_heat_loss
from eht.calculations.tracer_selection import get_tracer_options
from eht.calculations.power_distribution import compute_power_params, compute_power_distribution
from eht.calculations.boq import compute_bill_of_quantities
from eht.models import ProjectData, HeatTracingInput, ElecEHT_ThermalConductivity, ElecEHT_ASMEB36, ElecEHT_Vendor, SELECT_VENDOR # import required models

import logging
logger = logging.getLogger(__name__)


def parent_calculation_func(project_id, input_data):
    try:
        project_data = ProjectData.objects.get(proj_id=project_id)         
        vendor_dict = dict(SELECT_VENDOR)

        vendor_data_query = list(ElecEHT_Vendor.objects.filter(
            Vendor=vendor_dict.get(project_data.vendor),
            Voltage__gte=float(project_data.voltage)
            ).annotate(
                Voltage_Float= Cast('Voltage', FloatField())  # Convert to float at DB level
                ).values(
                    'V_UID', 'Voltage_Float', 'A_Coeff', 'B_Coeff', 'C_Coeff', 
                    'Power_at_Startup_T', 'Ohm_per_km', 'Res_corrFactor_Mica', 'Tracer_Family'
                ).distinct())
            
        vendor_data = pd.DataFrame(vendor_data_query)  # Convert list to Pandas DataFrame

        df_asme_b36 = ElecEHT_ASMEB36.objects.values('Nominal_Pipe_Size', 'Outside_Diameter_mm')
        asme_data = pd.DataFrame.from_records(df_asme_b36) 
        thermal_conductivity_data = ElecEHT_ThermalConductivity.objects.values('Ins_Mat_Type', 'K_factor_A', 'K_factor_B', 'K_factor_C')
        thermal_data = pd.DataFrame.from_records(thermal_conductivity_data)   


        calculation_result = run_full_calculation(project_id, input_data, project_data, vendor_data, asme_data, thermal_data)
        return calculation_result
    except Exception as e:
        logger.error(f"Error in parent_cal_function: {str(e)}")
        return None    



def run_full_calculation(project_id, input_data, project_data, vendor_data, asme_data, thermal_data):
    """
    Integrates all calculation modules into a single function.
    Executes the calculation in sequential order:
    1. Heat Loss Calculation
    2. Tracer Selection
    3. Power Distribution Parameter Calculation
    4. Power Distribution Strategy
    5. Bill of Quantities Calculation
    Returns consolidated results.
    """
    try:
        logging.info("Starting full calculation process...")
        
        # Step 1: Compute Heat Loss for Each Line
        heat_loss_results = [calculate_heat_loss(row, project_data, asme_data, thermal_data) for row in input_data]
        
        # Merge Heat Loss Data into Input
        for idx, row in enumerate(input_data):
            row.update(heat_loss_results[idx])
        
        # Step 2: Select Suitable Tracer Options
        tracer_results = []
        for row in input_data:
            best_tracer, alternative_tracers = get_tracer_options(row['heat_loss'], row, project_data, vendor_data)
            row['selected_tracer'] = best_tracer
            row['alternative_tracers'] = alternative_tracers
            tracer_results.append(best_tracer)
        
        # Step 3: Compute Power Distribution Parameters
        power_params_results = [compute_power_params(row, project_data, asme_data) for row in input_data] # adding asme_data data to append pipe-dia (mm), when return to calculate BOQ later
        
        # Merge Power Parameters into Input
        for idx, row in enumerate(input_data):
            if power_params_results[idx]:
                row.update(power_params_results[idx])
        
        # Step 4: Compute Power Distribution Strategy
        power_distribution_results = compute_power_distribution(project_data, input_data)

        # Step 5: Compute Bill of Quantities (BOQ)
        power_distribution_results = pd.DataFrame(power_distribution_results)
        power_distribution_results['line_length'] = pd.DataFrame(input_data)['line_length']
        power_distribution_results['pipe_size_mm'] = pd.DataFrame(input_data)['pipe_size_mm']        
        boq_results = compute_bill_of_quantities(power_distribution_results, project_data)
        
        logging.info("Full calculation process completed successfully.")
        
        return {
            'heat_loss': heat_loss_results,
            'tracer_selection': tracer_results,
            'power_distribution': power_distribution_results,
            'boq': boq_results
        }
    except Exception as e:
        logging.error(f"Error in full calculation process: {str(e)}")
        return None

