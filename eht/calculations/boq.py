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
            # 'TRACER': 0,
            'ENDTRM': 0,
            'ISOLATOR': 0,
            'RTD': 0,
            'THERMOSTAT': 0,
            'Caution_Label': 0,
            'Aluminium_Adhesive_Tape': 0,
            'Pipe_Strap': 0
        }
        
        for col, row in power_distribution_data.iterrows():
            no_of_circuits = row['total_circuits']
           
            # boq['TRACER'] += no_of_circuits  # One tracer per circuit: Tracer Count not required (total tracer length is only required & already available)
            boq['ENDTRM'] += no_of_circuits  # One termination per circuit
            
            for branch in row['branches']:
                if branch['type'] == '3phJB':
                    boq['MCB'] += 1  # One breaker per circuit
                    boq['JB3PH'] += 1
                    boq['CCMCB-3PHJB'] += branch['cable_length_db_to_jb']  # Cable from DB to first 3phJB
                    if  branch['connected_to'] == '3x 1phJB':
                        boq['JB1PH'] += branch['circuit_count']
                        boq['CC3PHJB-1PHJB'] += branch['circuit_count'] * branch['cable_length_jb_to_jb']
                    if  branch['connected_to'] == '2x 1phJB':
                        boq['JB1PH'] += branch['circuit_count']
                        boq['CC3PHJB-1PHJB'] += branch['circuit_count'] * branch['cable_length_jb_to_jb']


                elif branch['type'] == '1phJB':
                    boq['MCB'] += 1  # One breaker per circuit
                    boq['JB1PH'] += branch['circuit_count']
                    boq['CC3PHJB-1PHJB'] += branch['cable_length_db_to_jb']  # Cable between MCB to 1phJB
        
        # Compute Isolators based on user setting
        isolator_setting = project_data.isolator_location
        if isolator_setting == 'bothSides':
            boq['ISOLATOR'] = boq['JB3PH'] + boq['JB1PH']
        elif isolator_setting == 'outgoingOnly':
            boq['ISOLATOR'] = boq['JB1PH']
        elif isolator_setting == 'incomingOnly':
            boq['ISOLATOR'] = boq['JB3PH']
        else:
            boq['ISOLATOR'] = 0  # No isolators
        
        # Compute RTD/Thermostat based on project settings
        if project_data.rtd_thrm in ['RI', 'TI']:
            boq['RTD'] = boq['JB1PH'] if 'RI' in project_data.rtd_thrm else 0
            boq['THERMOSTAT'] = boq['JB1PH'] if 'TI' in project_data.rtd_thrm else 0
        elif project_data.rtd_thrm in ['RO', 'TO']:
            additional_count = (no_of_circuits % 3) if no_of_circuits > 2 else no_of_circuits
            boq['RTD'] = boq['JB3PH'] + additional_count if 'RI' in project_data.rtd_thrm else 0
            boq['THERMOSTAT'] = boq['JB3PH'] + additional_count if 'TI' in project_data.rtd_thrm else 0
        
        # Compute Accessories
        boq['Caution_Label'] = math.ceil(max(float(row['line_length']) / float(project_data.caution_label_interval), 1))
        boq['Aluminium_Adhesive_Tape'] = math.ceil(max(float(row['pipe_size_mm']) * math.pi * 4 * float(row['line_length']) / 1000, 1))
        boq['Pipe_Strap'] = boq['JB1PH'] + boq['RTD'] + boq['THERMOSTAT']
        
        return boq
    except Exception as e:
        logging.error(f"Error in BOQ calculation: {str(e)}")
        return {}

