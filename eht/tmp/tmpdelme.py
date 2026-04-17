import math
import logging

def compute_bill_of_quantities(power_distribution_data, project_data):
    """
    Computes the Bill of Quantities (BOQ) for all components in the power flow.
    Includes MCBs, JB3PH, JB1PH, cables, tracers, end termination kits, isolators, RTDs, thermostats, and accessories.
    """
    try:
        boq = {
            'MCB': 0,
            'JB3PH': 0,
            'JB1PH': 0,
            'CCMCB-3PHJB': 0,
            'CC3PHJB-1PHJB': 0,
            'TRACER': 0,
            'ENDTRM': 0,
            'ISOLATOR': 0,
            'RTD': 0,
            'THERMOSTAT': 0,
            'Caution_Label': 0,
            'Aluminium_Adhesive_Tape': 0,
            'Pipe_Strap': 0
        }
        
        for circuit in power_distribution_data:
            no_of_circuits = circuit['no_of_circuits']
            boq['MCB'] += 1  # One breaker per circuit
            boq['TRACER'] += no_of_circuits  # One tracer per circuit
            boq['ENDTRM'] += no_of_circuits  # One termination per circuit
            
            for branch in circuit['branches']:
                if branch['type'] == '3phJB':
                    boq['JB3PH'] += 1
                    boq['CCMCB-3PHJB'] += 1  # Cable from DB to first 3phJB
                elif branch['type'] == '1phJB':
                    boq['JB1PH'] += 1
                    boq['CC3PHJB-1PHJB'] += 1  # Cable between 3phJB to 1phJB
        
        # Compute Isolators based on user setting
        isolator_setting = project_data['Isolator_Type']
        if isolator_setting == 'Both Sides':
            boq['ISOLATOR'] = boq['JB3PH'] + boq['JB1PH']
        elif isolator_setting == 'Outgoing Only':
            boq['ISOLATOR'] = boq['JB1PH']
        elif isolator_setting == 'Incoming Only':
            boq['ISOLATOR'] = boq['JB3PH']
        else:
            boq['ISOLATOR'] = 0  # No isolators
        
        # Compute RTD/Thermostat based on project settings
        if project_data['Select_RTD_THST'] in ['RTD, Inline', 'Thermostat, Inline']:
            boq['RTD'] = boq['JB1PH'] if 'RTD' in project_data['Select_RTD_THST'] else 0
            boq['THERMOSTAT'] = boq['JB1PH'] if 'Thermostat' in project_data['Select_RTD_THST'] else 0
        elif project_data['Select_RTD_THST'] in ['RTD, Offline', 'Thermostat, Offline']:
            additional_count = (no_of_circuits % 3) if no_of_circuits > 2 else no_of_circuits
            boq['RTD'] = boq['JB3PH'] + additional_count if 'RTD' in project_data['Select_RTD_THST'] else 0
            boq['THERMOSTAT'] = boq['JB3PH'] + additional_count if 'Thermostat' in project_data['Select_RTD_THST'] else 0
        
        # Compute Accessories
        boq['Caution_Label'] = math.ceil(max(project_data['eqv_pipe_length'] / project_data['caution_label_interval'], 1))
        boq['Aluminium_Adhesive_Tape'] = math.ceil(max(project_data['pipe_size_mm'] * math.pi * 4 * project_data['eqv_pipe_length'] / 1000, 1))
        boq['Pipe_Strap'] = boq['JB1PH'] + boq['RTD'] + boq['THERMOSTAT']
        
        return boq
    except Exception as e:
        logging.error(f"Error in BOQ calculation: {str(e)}")
        return {}

'''
'0-ID
'1-UID
'2-Heat_Loss            :OK > 139.23493958134125    >> heat_loss_results[0]['heat_loss']
'3-Tracer_Power_Output  :OK > 40.106                >> tracer_results[0]['Power_Output']
'4-User_Tracer_Cat_UID  : ?
'5-Auto_Tracer_Cat_UID  :OK > Thermon^VSX20-2       >> tracer_results[0]['V_UID']
'6-Tracer_Length        :OK > 1158.3252420309586    >> power_params_results[0]['total_tracer_length']
'7-Spiral_Factor        :OK > 3.645257232344495     >> tracer_results[0]['Spiral_Factor']
'8-DB_No                :--
'9-CKT_No               :--   
'10-Breaker_Size        :OK > 40.0                  >> power_params_results[0]['breaker_size']   
'11-Operating_Current   :OK > 218.99525399809903    >> power_params_results[0]['operating_current']
'12-Maximum_Current     :OK > 359.0874735433286     >> power_params_results[0]['max_current']
'13-Operating_Load      :OK > 50368.90841956278     >> power_params_results[0]['operating_load']
'14-Optional_Tracer     :OK > []                    >> input_data[0]['alternative_tracers']
'15-Total_Tracer_Length :OK > 1158.3252420309586    >> power_params_results[0]['total_tracer_length']
'16-Last_Design         :--
'17-No_of_Ckt           :OK > 11                    >> power_params_results[0]['no_of_circuits']
'18-Isolator            :OK > 15                    >> boq_results['ISOLATOR'] 
'19-JB_3PH              :OK > 4                     >> boq_results['JB3PH']
'20-JB_1PH              :OK > 11                    >> boq_results['JB1PH']
'21-Splice_Conn_Box     : ?
'22-Tee_Connection_Box  : ?
'23-End_Connection_Box  :OK > 11                    >> boq_results['ENDTRM']
'24-RTD                 :OK > 0                     >> boq_results['RTD']
'25-Thermostat          :OK > 11                    >> boq_results['THERMOSTAT']
'26-Caution_Label       :OK > 50                    >> boq_results['Caution_Label']
'27-Aluminium_Tape      :OK > 1456                  >> boq_results['Aluminium_Adhesive_Tape'] 
'28-Others              : ?
'29-Pipe_Strap          :OK > 22                    >> boq_results['Pipe_Strap']

'''