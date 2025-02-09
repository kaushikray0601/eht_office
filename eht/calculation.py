# Here goes the calculation
import pandas as pd
import numpy as np
import math
from collections import namedtuple

from eht.models import ProjectData, HeatTracingInput, ElecEHT_ThermalConductivity, ElecEHT_ASMEB36, ElecEHT_Vendor, SELECT_VENDOR # import required models

import logging
logger = logging.getLogger(__name__)


def calculation(project_id, valid_data):

    try:

        # 1. Retrieve Project Data
        project_data = ProjectData.objects.get(proj_id=project_id)

        # 2. Get Thermal Conductivity Data
            # using  Django ORM select_related(), prefetch_related() or values() is optimal for performance.
        thermal_conductivity_data = ElecEHT_ThermalConductivity.objects.values('Ins_Mat_Type', 'K_factor_A', 'K_factor_B', 'K_factor_C')
        df_thermal_conductivity = pd.DataFrame.from_records(thermal_conductivity_data)       
        
        # 3. Get ASME B36 data
        asme_data = ElecEHT_ASMEB36.objects.values('Nominal_Pipe_Size', 'Outside_Diameter_mm')
        df_asme_b36 = pd.DataFrame.from_records(asme_data)

        # 4. Get the required data from valid_data object (which is your HeatTracingInput object).        
        df_input_data = pd.DataFrame.from_records(valid_data.values())        
        
        # Initialize the output dictionary, this dictionary will hold all the output data for this method

        def calculate_heat_loss(row):
            main_t  = float(row['maint_temp'])
            insul_thick = float(row['insul_thick'])
            ins_mat_type = str(row['ins_mat_type'])

            # (a) Calculate conductivity from insulation material type
            conductivity_contants = df_thermal_conductivity[df_thermal_conductivity['Ins_Mat_Type'] == ins_mat_type]
            if conductivity_contants.empty:
                conductivity = 0.0
                logger.warning(f"Warning: No thermal conductivity data for '{ins_mat_type}' for line with UID {row['uid']}")
                return False
            else:
                cond_cons_a = conductivity_contants['K_factor_A'].iloc[0]
                cond_cons_b = conductivity_contants['K_factor_B'].iloc[0]
                cond_cons_c = conductivity_contants['K_factor_C'].iloc[0]
                conductivity = cond_cons_a * main_t * main_t + cond_cons_b * main_t + cond_cons_c

            # (b) Calculate pipe size from ASME B36 data
            pipe_size_in = row['line_size']      
            outer_dia_mm = df_asme_b36[df_asme_b36['Nominal_Pipe_Size'] == pipe_size_in]['Outside_Diameter_mm']
            
            if outer_dia_mm.empty:
                pipe_size_mm = 25.206 * pipe_size_in + 9.4852
                logger.info(f"Warning: No ASME B36 data for pipe size '{pipe_size_in}' inch, using approx formula to convert for line with UID {row['uid']}")
                return False
            else:
                pipe_size_mm = outer_dia_mm.iloc[0]

            # (c) calculate delta temp
            delta_tmp = main_t - float(project_data.min_amb_t)

            # (A) Calculate HEAT LOSS
            if pipe_size_mm !=0:
                heat_loss = 2 * math.pi * conductivity * delta_tmp / math.log((2 * insul_thick + pipe_size_mm) / pipe_size_mm)
            else:
                heat_loss = 0
                logger.warning(f"Warning: Pipe diameter is zero for line with UID {row['uid']}")
        
            # (B) Heat loss correction due to wind Speed [above 32kmph, 1% per mile/hr increase subject to a maximum of 20% (assuming 1mile = 1.60934km)].
            windspeed_factor =  1 +  min(20, (float(project_data.wind_speed) - 32)/1.60934)/100
            heat_loss = heat_loss * windspeed_factor

            # (C) Add tracer length due to number of valves, supports & flanges in the line

            pipe_size = pipe_size_mm / 25.4
            add_tracer_for_valve = float(row.valve_qty) * (3.5 + 0.5 * pipe_size)/3.048
            add_tracer_for_support = float(row.support_qty) * (2 + 0.08 * pipe_size)/3.048
            add_tracer_for_flange = float(row.flange_qty) * ( 0.3 if pipe_size < 3 else 0.5 if pipe_size < 6 else 0.8 if pipe_size < 14 else 1)

            tracer_adder = add_tracer_for_valve + add_tracer_for_support + add_tracer_for_flange

            # (D) Get the tracer catalogue data matching the following criteria:
            ''' SELECT DISTINCT V_UID, Voltage, A_Coeff,B_Coeff, C_Coeff, Power_at_Startup_T, Ohm_per_km, Res_corrFactor_Mica,Tracer_Family 
                FROM elecEHT_Vendor 
                WHERE Vendor = '" & vendor & "' AND Maint_T >" & maint_t & " AND Max_Op_T>" & oper_t & " AND Max_Exp_T_On>" & design_t '''
            
            # ---- Calculate Tracer Options ----
            vendor_dict = dict(SELECT_VENDOR)
            matching_tracer_data = ElecEHT_Vendor.objects.filter(
                    Vendor = vendor_dict.get(project_data.vendor),
                    Maint_T__gt = main_t,
                    Max_Op_T__gt = float(row['oper_temp']),
                    Max_Exp_T_On__gt = float(row['design_temp'])
                ).values('V_UID', 'Voltage', 'A_Coeff', 'B_Coeff', 'C_Coeff', 'Power_at_Startup_T', 'Ohm_per_km', 'Res_corrFactor_Mica', 'Tracer_Family'
                ).distinct()

            Tracer_params = namedtuple('Tracer_params',
                                        ['design_margin', 'termination_margin', 'maint_t', 'oper_t', 'min_amb_t',
                                        'spiral_factor_allowed', 'heat_loss', 'eqv_pipe_length', 'voltage',
                                        'voltage_var_factor', 'sprialAllowed', 'tracerAdder'])


            tracerOption_params = Tracer_params(
                                    design_margin=float(project_data.margin_on_tracer_lengths),
                                    termination_margin=float(project_data.termination_margin),
                                    min_amb_t=float(project_data.min_amb_t),
                                    spiral_factor_allowed=float(project_data.spiral_factor),
                                    voltage=float(project_data.voltage),
                                    voltage_var_factor=float(project_data.voltage_var_factor),
                                    sprialAllowed=project_data.spiral_wrap_allowed,                                    
                                    maint_t=main_t,
                                    oper_t=float(row['oper_temp']),
                                    eqv_pipe_length=float(row['line_length']),
                                    heat_loss=heat_loss,                                   
                                    tracerAdder=tracer_adder
                                     )

            tracer_options, tracer_found = get_tracer_options(tracerOption_params, matching_tracer_data)
            
            if tracer_found is False: return False

            #-------------- Manage Tag and BOQ -------------------------

            # Build Unique ID concatenating Line_ID, Line_size and Line_length

            u_id = row.line_id + '_' + str(row.line_size) + '_' + str(int(row.line_length))

            TagManagementParams = namedtuple('TagManagementParams',
                                        ['uid', 'heat_loss', 'tracer_options', 'voltage_var_factor', 'voltage', 'max_cb_size',
                                        'allowed_cb_loading_in_amp', 'termination_margin', 'eqv_pipe_length', 'design_margin',
                                        'service_type', 'caution_label_interval', 'pipe_size_mm', 'req_local_isolator',
                                        'loop_ln', 'ckt_ln', 'dt_tracer'])
        
            tagging_params = TagManagementParams(
                                        uid=u_id,
                                        heat_loss=heat_loss,
                                        tracer_options=tracer_options,
                                        voltage_var_factor=float(project_data.voltage_var_factor),
                                        voltage=float(project_data.voltage),
                                        max_cb_size=float(project_data.max_cb_size),
                                        allowed_cb_loading_in_amp=float(project_data.restrict_cb_current)/100, # data received by user in % (eg. 85 percent)
                                        termination_margin=float(project_data.termination_margin),
                                        eqv_pipe_length=float(row['line_length']),
                                        design_margin=float(project_data.margin_on_tracer_lengths),
                                        service_type=row.service_type,
                                        caution_label_interval=float(project_data.caution_label_interval),
                                        pipe_size_mm=pipe_size_mm,
                                        req_local_isolator=project_data.req_local_isolator,
                                        loop_ln = float(project_data.loop_ln),
                                        ckt_ln = float(project_data.ckt_ln),
                                        dt_tracer = matching_tracer_data
                                        )

            tag_mgmt_table, cal_table= SRTracerDesign(tagging_params)

            # tag_mgmt_table, cal_table= TagManagement(u_id, heat_loss, tracer_options, project_data.voltage_var_factor, project_data.voltage, project_data.max_cb_size, 
                #   project_data.restrict_cb_current, project_data.termination_margin, float(row['line_length']), float(project_data.margin_on_tracer_lengths), 
                #   row.service_type, project_data.caution_label_interval, pipe_size_mm, project_data.req_local_isolator, 
                #   project_data.loop_ln, project_data.ckt_ln, matching_tracer_data)


            return {
                'uid': row['uid'],          
                'heat_loss': heat_loss
            }
        
        # Apply the calculation to each row
        #   - Use apply() method to apply the function to each row of the dataframe   

        heat_loss_results_df = df_input_data.apply(calculate_heat_loss, axis=1, result_type='expand')
        # Merge the calculated heat loss data into a new df (using left join)
        df_combined_results = pd.merge(df_input_data, heat_loss_results_df, on='uid', how='left') # use left join

        return df_combined_results.to_dict('records')

    except ProjectData.DoesNotExist:
         logger.error(f"Project data not found for project ID: {project_id}")
         raise Exception(f"Project data not found for project ID: {project_id}")
    except Exception as e:
         logger.error(f"Error during heat loss calculation for project ID: {project_id}: {str(e)}")
         raise Exception(f"Error during heat loss calculation for project ID: {project_id}: {str(e)}")



'''Heat Loss Cal'''
def heat_loss_cal(project_id, valid_data):    
    # retrieve project data based on the project_id
    pass
    return True


'''Design Power Distribution System'''
def power_distribution_cal(project_id, valid_data):
    pass
    return True




#---------- Helper functions ----------------------------------------

def get_tracer_options (param, matching_tracer_data):

    try:

        # Initialize a list to store tracer options
        tracer_options = []

        #Filter unwanted tracers before looping:
        matching_tracer_data = matching_tracer_data.filter(Tracer_Family__icontains="Self Regulating")

        for tracer in matching_tracer_data:

            vendor_voltage_correction  = (param.voltage/float(tracer['Voltage']))**2       #correction for the catalogue voltage vs. system voltage

            tracer_power_output = vendor_voltage_correction  * (
                tracer['A_Coeff'] * param.maint_t * param.maint_t + 
                tracer['B_Coeff'] * param.maint_t + 
                tracer['C_Coeff'])
            
            spr_fact = abs(param.heat_loss * (1 + param.voltage_var_factor / 100) / tracer_power_output)                                                              #' Voltage variation factor is considered to compensate for lower power rated tracer < heat loss

            # Skip if spiral factor is out of bounds or spiral is not allowed
            if spr_fact > param.spiral_factor_allowed or spr_fact < 0.8 or param.sprialAllowed.lower()!='yes': continue

            spr_fact = math.ceil(spr_fact)      

            # Calculate tracer length and total tracer length
            itracer_length = (param.eqv_pipe_length + param.tracerAdder) * spr_fact
            itotal_tracer_length = (itracer_length * (1 + param.design_margin / 100)) #only design margin is added to tracer length (termination margin to be added to this after finding no. of ckts)
            
            # Calculate operating current and max current
            operating_current = itotal_tracer_length * vendor_voltage_correction  * (
                tracer['A_Coeff'] * param.oper_t * param.oper_t + 
                tracer['B_Coeff'] * param.oper_t + 
                tracer['C_Coeff']
                ) / param.voltage
                    
            max_current = itotal_tracer_length * vendor_voltage_correction  * (
                tracer['A_Coeff'] * param.min_amb_t * param.min_amb_t + 
                tracer['B_Coeff'] * param.min_amb_t + 
                tracer['C_Coeff']
                ) / param.voltage
            
            # Calculate tracer power output at start
            tracer_power_output_start = max_current * param.voltage
            
            # Store the results in a dictionary
            tracer_data = {
                "V_UID": tracer['V_UID'],
                "Power_OP": tracer_power_output,
                "Spiral_Factor": spr_fact,
                "TracerPower_OP_Start": tracer_power_output_start,
                "Operating_Current": operating_current,
                "Max_Current": max_current,
                "ith_Tracer_Length": itracer_length,
                "iTotal_Tracer_Length": itotal_tracer_length
            }

            # Append the dictionary to the list
            tracer_options.append(tracer_data)

            # If no match is found return
            if len(tracer_options) < 1 : return [], False

        # Sort the list by iTotal_Tracer_Length and the with Tracer_power_output in ascending order
        df_tracer_options = pd.DataFrame(tracer_options)
        df_tracer_options.sort_values(by=['iTotal_Tracer_Length', 'Power_OP'], ascending=[True, True], inplace=True)
        # tracer_options = df_tracer_options.to_dict('records')
        
    except Exception as e:
        logger.error(f"Error in get_tracer_options: {str(e)}")
        return [], False

    return df_tracer_options, True


# Tag Management system


def SRTracerDesign(TagParams):

    tag_mgmt_columns = ["ID", "UID", "TypeofItem", "User_Tag", "LineUID", "From_Item_Tag", 
                        "To_Item_Tag", "Para1", "Para2", "X_Coordinate", "Y_Coordinate"]
    tag_mgmt_table = pd.DataFrame(columns=tag_mgmt_columns)
    
    cal_table_columns = ["ID", "UID", "Heat_Loss", "Tracer_Power_Output", "User_Tracer_Cat_UID", 
                         "Auto_Tracer_Cat_UID", "Tracer_Length", "Spiral_Factor", "DB_No", 
                         "CKT_No", "Breaker_Size", "Operating_Current", "Maximum_Current", 
                         "Operating_Load", "Optional_Tracer", "Total_Tracer_Length", 
                         "Last_Design", "No_of_Ckt", "Isolator", "JB_3PH", "JB_1PH", 
                         "Splice_Connection_Box", "Tee_Connection_Box", "End_Connection_Box", 
                         "RTD", "Thermostat", "Caution_Label", "Aluminium_Adhesive_Tape", 
                         "Others", "Pipe_Strap"]
                         
    cal_table = pd.DataFrame(columns=cal_table_columns)
    
    # Initialize Calculation Table
    cal_table.loc[0]                        = [0] * len(cal_table_columns)
    cal_table.at[0, "UID"]                  = TagParams.uid
    cal_table.at[0, "Heat_Loss"]            = TagParams.heat_loss
    cal_table.at[0, "Tracer_Power_Output"]  = float(TagParams.tracer_options.iloc[0, 1])
    cal_table.at[0, "User_Tracer_Cat_UID"]  = TagParams.tracer_options.iloc[0, 0]
    cal_table.at[0, "Auto_Tracer_Cat_UID"]  = TagParams.tracer_options.iloc[0, 0]
    cal_table.at[0, "Spiral_Factor"]        = float(TagParams.tracer_options.iloc[0, 2])
    cal_table.at[0, "DB_No"]                = "Later"
    cal_table.at[0, "CKT_No"]               = "Later"
    
    # Circuit Calculation
    no_ckt = math.ceil(TagParams.tracer_options.iloc[0, 5] / TagParams.max_cb_size * TagParams.allowed_cb_loading_in_amp)
    TagParams.tracer_options.iloc[0, 7] += no_ckt * TagParams.termination_margin / 1000     #termination margin (converted to meter) added
    cal_table.at[0, "Tracer_Length"] = TagParams.tracer_options.iloc[0, 7]
    
    # Breaker Size Calculation
    breaker_sizes = [2, 4, 6, 10, 16, 20, 25, 32]
    if no_ckt <= 1:
        breaker_size_a = math.ceil(TagParams.tracer_options.iloc[0, 5] / TagParams.allowed_cb_loading_in_amp)
        breaker_size_a = next((size for size in breaker_sizes if size >= breaker_size_a), TagParams.max_cb_size)
    else:
        breaker_size_a = TagParams.max_cb_size
    cal_table.at[0, "Breaker_Size"] = breaker_size_a
    
    # Additional calculations
    cal_table.at[0, "Operating_Current"] = TagParams.tracer_options.iloc[0, 4]
    cal_table.at[0, "Maximum_Current"] = TagParams.tracer_options.iloc[0, 5]
    cal_table.at[0, "Operating_Load"] = TagParams.tracer_options.iloc[0, 4] * TagParams.voltage
    
    # Optional Tracer Calculation
    optional_tracer = "!".join([f"{row[0]}__{row[1]}__{row[2]}__{row[7]}" for _, row in TagParams.tracer_options.iterrows()])
    cal_table.at[0, "Optional_Tracer"] = optional_tracer if TagParams.tracer_options.shape[0] > 1 else " "
    
    # Isolator Calculation
    n_threeph_jb = math.floor((no_ckt + 1) / 3)
    cal_table.at[0, "No_of_Ckt"] = no_ckt
    
    # Caution Labels
    cal_table.at[0, "Caution_Label"] = math.ceil(max(TagParams.eqv_pipe_length / TagParams.caution_label_interval, 1))
    
    # Aluminium Tape Calculation
    cal_table.at[0, "Aluminium_Adhesive_Tape"] = math.ceil(max(TagParams.pipe_size_mm * 3.141 * 4 * TagParams.eqv_pipe_length / 1000, 1))
    
    # Returning Tables
    return {"TagManagement": tag_mgmt_table, "Calculation": cal_table}







# # ----------------------------

# import pandas as pd
# import numpy as np
# from eht.models import ProjectData, HeatTracingInput, ElecEHT_ThermalConductivity, ElecEHT_ASMEB36 # import required models
# import logging
# import math
# logger = logging.getLogger(__name__)

# def heat_loss_cal(project_id, valid_data):
#     try:
#         # 1. Retrieve Project Data
#         project = ProjectData.objects.get(proj_id=project_id)

#         # 2. Get Thermal Conductivity Data
#         thermal_conductivity_data = ElecEHT_ThermalConductivity.objects.all().values()
#         df_thermal_conductivity = pd.DataFrame.from_records(thermal_conductivity_data)

#         # 3. Get ASME B36 data
#         asme_data = ElecEHT_ASMEB36.objects.all().values()
#         df_asme_b36 = pd.DataFrame.from_records(asme_data)

#         # 4. Get the required data from valid_data object (which is your HeatTracingInput object).
#         df_input_data = pd.DataFrame.from_records(valid_data.values())

#         # Define a function to calculate heat loss
#         def calculate_heat_loss(row):
#             # Retrieve data from dataframe rows (input data)

#             maint_t = row['maint_temp']
#             insul_thick = row['insul_thick']
#             ins_mat_type = row['ins_mat_type']

#             # Calculate delta_tmp (maint_t - min_amb_t)
#             delta_tmp = maint_t - project.min_amb_t

#             # Get conductivity from the thermal conductivity data
#             thermal_data = df_thermal_conductivity[df_thermal_conductivity['Ins_Mat_Type'] == ins_mat_type]
#             if not thermal_data.empty:
#                 k_a = thermal_data['K_factor_A'].iloc[0]
#                 k_b = thermal_data['K_factor_B'].iloc[0]
#                 k_c = thermal_data['K_factor_C'].iloc[0]
#                 conductivity = k_a * maint_t * maint_t + k_b * maint_t + k_c
#             else:
#                 conductivity = 0.0
#                 logger.warning(f"Warning: No thermal conductivity data for '{ins_mat_type}' for line with UID {row['uid']}")

#             # Get pipe size from ASME B36 data
#             pipe_size_in = row['line_size']
#             asme_data_row = df_asme_b36[df_asme_b36['Nominal_Pipe_Size'] == pipe_size_in]
#             if not asme_data_row.empty:
#                 pipe_size_mm = asme_data_row['Outside_Diameter_mm'].iloc[0]
#             else:
#                  pipe_size_mm = 25.206 * pipe_size_in + 9.4852
#                  logger.warning(f"Warning: No ASME B36 data for pipe size '{pipe_size_in}' inch, using approx formula to convert for line with UID {row['uid']}")

#             # Calculate the heat loss
#             if pipe_size_mm !=0:
#                heat_loss = 2 * math.pi * conductivity * delta_tmp / math.log((2 * insul_thick + pipe_size_mm) / pipe_size_mm)
#             else:
#                 heat_loss = 0 # Assign zero if the pipe diameter is zero (to avoid error)
#                 logger.warning(f"Warning: Pipe diameter is zero for line with UID {row['uid']}")
            
#             # Create a dictionary and return the calculated value
#             return {
#                 'uid': row['uid'],                
#                 'heat_loss': heat_loss
#              }
         
#        # Apply the calculation to each row
#         heat_loss_results_df = df_input_data.apply(calculate_heat_loss, axis=1, result_type='expand')
#         # Merge the calculated heat loss data into a new df (using left join)
#         df_combined_results = pd.merge(df_input_data, heat_loss_results_df, on='uid', how='left') # use left join

#         # Convert Pandas df to list of dict
#         heat_loss_results = df_combined_results.to_dict('records')

#         return heat_loss_results

#     except ProjectData.DoesNotExist:
#          logger.error(f"Project data not found for project ID: {project_id}")
#          raise Exception(f"Project data not found for project ID: {project_id}")
#     except Exception as e:
#          logger.error(f"Error during heat loss calculation for project ID: {project_id}: {str(e)}")
#          raise Exception(f"Error during heat loss calculation for project ID: {project_id}: {str(e)}")