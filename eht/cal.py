import pandas as pd
from eht.calculations.heat_loss import calculate_heat_loss
from eht.calculations.tracer_selection import get_tracer_options
from eht.calculations.power_distribution import compute_power_params, compute_power_distribution
from eht.calculations.boq import compute_bill_of_quantities


import logging
logger = logging.getLogger(__name__)


def orchestrate_calculations(project_id, process_lines, vendor_data, project_settings, asme_b36_table, thermal_cond_data):

    # Initialize aggregated result containers
    aggregated_results = {
        "heat_loss": [],
        "selected_tracers": [],
        "alternative_tracers": [],
        "power_distribution": [],
        "boq_per_line": {},         # Store BOQ per line (keyed by line UID)
        "consolidated_boq": {},     # Aggregated BOQ across all lines
        "tracer_power_param": []    # Store tracer power parameters for each line     
    }

    # Loop through rows in the DataFrame
    for _, line in pd.DataFrame(process_lines).iterrows():
        try: 
            # Step-1: Heat Loss Calculation
            heat_loss = calculate_heat_loss(line, project_settings, asme_b36_table, thermal_cond_data)
            if not heat_loss:   continue
            aggregated_results["heat_loss"].append(heat_loss)

            # Step-2: Tracer Selection
            selected_tracer, alternative_tracers = get_tracer_options(heat_loss, line, project_settings, vendor_data)
            if not selected_tracer: continue
            selected_tracer = {**selected_tracer, "uid": line["uid"]}
            aggregated_results["selected_tracers"].append(selected_tracer)
            if isinstance(alternative_tracers, list):
                aggregated_results["alternative_tracers"].extend(
                    {**tracer, "uid": line["uid"]}
                    for tracer in alternative_tracers
                )
             
            # Step 3: Power Distribution
            power_params = compute_power_params(line, project_settings, asme_b36_table, selected_tracer) # adding asme_data data to append pipe-dia (mm), when returned to calculate BOQ later
            power_distribution = compute_power_distribution(power_params, project_settings)              # Step 3.1: Compute Power Distribution Strategy
            aggregated_results["power_distribution"].append(power_distribution)
            
            # Step 4: Bill of Quantities (BOQ) Calculation
            power_distribution_df= pd.DataFrame(power_distribution)
            boq = compute_bill_of_quantities(
                power_distribution_data=power_distribution_df, 
                project_settings=project_settings,
                tracer_qty=power_params["total_tracer_length"],
                line_length=line["line_length"],
                pipe_size_mm=power_params["pipe_size_mm"],
                is_process_temp_controlled= True if line.service_type == 'EP' else False
                )

            # Store BOQ for this line
            line_uid = line["uid"]
            aggregated_results["boq_per_line"][line_uid] = boq
            
            # Store tracer power parameters for each line
            aggregated_results['tracer_power_param'].append(power_params)  

             # Aggregate BOQ across lines
            for item, count in boq.items():
                aggregated_results["consolidated_boq"].setdefault(item, 0)
                aggregated_results["consolidated_boq"][item] += count

        except Exception as e:
            logging.error(f"Error processing line UID {line['uid']}: {str(e)}")

    return aggregated_results


# -- old Calculation function for reference -- #
# from django.db.models import FloatField
# from django.db.models.functions import Cast
# from eht.models import ProjectData, HeatTracingInput, ElecEHT_ThermalConductivity, ElecEHT_ASMEB36, ElecEHT_Vendor, SELECT_VENDOR # import required models


# def parent_calculation_func(project_id, input_data):
#     try:
#         project_data = ProjectData.objects.get(proj_id=project_id)         
#         vendor_dict = dict(SELECT_VENDOR)

#         vendor_data_query = list(ElecEHT_Vendor.objects.filter(
#             Vendor=vendor_dict.get(project_data.vendor),
#             Voltage__gte=float(project_data.voltage)
#             ).annotate(
#                 Voltage_Float= Cast('Voltage', FloatField())  # Convert to float at DB level
#                 ).values(
#                     'V_UID', 'Voltage_Float', 'A_Coeff', 'B_Coeff', 'C_Coeff', 
#                     'Power_at_Startup_T', 'Ohm_per_km', 'Res_corrFactor_Mica', 'Tracer_Family'
#                 ).distinct())
            
#         vendor_data = pd.DataFrame(vendor_data_query)  # Convert list to Pandas DataFrame

#         df_asme_b36 = ElecEHT_ASMEB36.objects.values('Nominal_Pipe_Size', 'Outside_Diameter_mm')
#         asme_data = pd.DataFrame.from_records(df_asme_b36) 
#         thermal_conductivity_data = ElecEHT_ThermalConductivity.objects.values('Ins_Mat_Type', 'K_factor_A', 'K_factor_B', 'K_factor_C')
#         thermal_data = pd.DataFrame.from_records(thermal_conductivity_data)   


#         calculation_result = run_full_calculation(project_id, input_data, project_data, vendor_data, asme_data, thermal_data)
#         return calculation_result
#     except Exception as e:
#         logger.error(f"Error in parent_cal_function: {str(e)}")
#         return None    



# def run_full_calculation(project_id, input_data, project_data, vendor_data, asme_data, thermal_data):
#     """
#     Integrates all calculation modules into a single function.
#     Executes the calculation in sequential order:
#     1. Heat Loss Calculation
#     2. Tracer Selection
#     3. Power Distribution Parameter Calculation
#     4. Power Distribution Strategy
#     5. Bill of Quantities Calculation
#     Returns consolidated results.
#     """
#     try:
#         logging.info("Starting full calculation process...")
        
#         # Step 1: Compute Heat Loss for Each Line
#         heat_loss_results = [calculate_heat_loss(row, project_data, asme_data, thermal_data) for row in input_data]
        
#         # Merge Heat Loss Data into Input
#         for idx, row in enumerate(input_data):
#             row.update(heat_loss_results[idx])
        
#         # Step 2: Select Suitable Tracer Options
#         tracer_results = []
#         for row in input_data:
#             best_tracer, alternative_tracers = get_tracer_options(row['heat_loss'], row, project_data, vendor_data)
#             row['selected_tracer'] = best_tracer
#             row['alternative_tracers'] = alternative_tracers
#             tracer_results.append(best_tracer)
        
#         # Step 3: Compute Power Distribution Parameters
#         power_params_results = [compute_power_params(row, project_data, asme_data) for row in input_data] # adding asme_data data to append pipe-dia (mm), when return to calculate BOQ later
        
#         # Merge Power Parameters into Input
#         for idx, row in enumerate(input_data):
#             if power_params_results[idx]:
#                 row.update(power_params_results[idx])
        
#         # Step 4: Compute Power Distribution Strategy
#         power_distribution_results = compute_power_distribution(project_data, input_data)

#         # Step 5: Compute Bill of Quantities (BOQ)
#         power_distribution_results = pd.DataFrame(power_distribution_results)
#         power_distribution_results['line_length'] = pd.DataFrame(input_data)['line_length']
#         power_distribution_results['pipe_size_mm'] = pd.DataFrame(input_data)['pipe_size_mm']        
#         boq_results = compute_bill_of_quantities(power_distribution_results, project_data)
        
#         logging.info("Full calculation process completed successfully.")
        
#         return {
#             'heat_loss': heat_loss_results,
#             'tracer_selection': tracer_results,
#             'power_distribution': power_distribution_results,
#             'boq': boq_results
#         }
#     except Exception as e:
#         logging.error(f"Error in full calculation process: {str(e)}")
#         return None


# # -------------------------------------------------------------------------------------------------------------------
# # ### Refactored `cal.py` ###




# # Utility function to preprocess vendor data
# from decimal import Decimal
# def preprocess_vendor_data(vendor_data):
#     def convert_decimals_to_floats(data):
#         """ Converts Decimal values in a dictionary to float. """
#         return {
#             key: float(value) if isinstance(value, Decimal) else value
#             for key, value in data.items()
#         }
#     # Process each dictionary in the list
#     return [convert_decimals_to_floats(item) for item in vendor_data]

# # Utility function to preprocess project-specific settings
# def preprocess_project_settings(settings):
#     # Example: Filter and format settings as needed
#     settings["temperature"] = float(settings["temperature"])
#     settings["wind_speed"] = float(settings["wind_speed"])
#     # Add other conversions as necessary
#     return settings

# # Utility function to preprocess process Lines
# def preprocess_process_lines(process_lines):
#     """
#     Convert process lines to a Pandas DataFrame and preprocess the data.
#     """
#     process_lines_df = pd.DataFrame(process_lines)
    
#     # Ensure numeric columns are properly formatted
#     if "line_length" in process_lines_df.columns:
#         process_lines_df["line_length"] = process_lines_df["line_length"].astype(float)

#     if "insulation_thickness" in process_lines_df.columns:
#         process_lines_df["insulation_thickness"] = process_lines_df["insulation_thickness"].astype(float)

#     # Add other preprocessing steps as needed
#     return process_lines_df
