import math
import logging

def compute_bill_of_quantities(power_distribution_data, project_settings, tracer_qty, line_length, pipe_size_mm, is_process_temp_controlled):
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
            'TRACER': tracer_qty,    
            'ENDTRM': 0,
            'ISOLATOR_1PH': 0,
            'ISOLATOR_3PH': 0,
            'RTD': 0,
            'THERMOSTAT': 0,
            'Caution_Label': 0,
            'Aluminium_Adhesive_Tape': 0,
            'Pipe_Strap': 0
        }
        
        for col, row in power_distribution_data.iterrows():
            no_of_circuits = row['total_circuits']           
       
            if row['branches']['type'] == '3phJB':
                  boq['MCB'] += 1  # One breaker per circuit
                  boq['JB3PH'] += 1
                  boq['CCMCB-3PHJB'] += row['branches']['cable_length_db_to_jb']  # Cable from DB to first 3phJB
                  if  row['branches']['connected_to'] in ['3x 1phJB', '2x 1phJB']:
                      boq['JB1PH'] += row['branches']['circuit_count']
                      boq['CC3PHJB-1PHJB'] += row['branches']['circuit_count'] * row['branches']['cable_length_jb_to_jb']
            elif row['branches']['type'] == '1phJB':
                  boq['MCB'] += 1  # One breaker per circuit
                  boq['JB1PH'] += row['branches']['circuit_count']
                  boq['CC3PHJB-1PHJB'] += project_settings['ckt_ln']  # Cable between MCB to 1phJB
        
        # Compute Isolators based on user setting
        isolator_setting = project_settings['isolator_location']
        if isolator_setting == 'bothSides':
            boq['ISOLATOR_3PH'] = boq['JB3PH'] 
            boq['ISOLATOR_1PH'] = no_of_circuits
        elif isolator_setting == 'outgoingOnly':
            boq['ISOLATOR_3PH'] = 0
            boq['ISOLATOR_1PH'] = no_of_circuits            
        elif isolator_setting == 'incomingOnly':
            boq['ISOLATOR_3PH'] = boq['JB3PH'] 
            boq['ISOLATOR_1PH'] = 0
        else:
            boq['ISOLATOR'] = 0  # No isolators
        
        # Compute RTD/Thermostat based on project settings
        '''
        (a) If Inline : RTD/Thermostat = number of circuits
        (b) If Offline: RTD/Thermostat = no. of direct connection to 3PhJB + no. of direct connection to 1PhJB, i.e. math.ceil(No. of circuits/3) or number of MCBs
        (c) If the EHT is coltrolled by ambient temp, then RTD/Thermostat (inline/offline) is not required
        '''
        if is_process_temp_controlled:           
            if project_settings['rtd_thrm'] in ['RI', 'TI']:
                boq['RTD'] = no_of_circuits if 'RI' in project_settings['rtd_thrm'] else 0
                boq['THERMOSTAT'] = no_of_circuits if 'TI' in project_settings['rtd_thrm'] else 0
                boq['Pipe_Strap'] = boq['RTD'] + boq['THERMOSTAT']

            elif project_settings['rtd_thrm'] in ['RO', 'TO']:              
                boq['RTD'] = boq['MCB'] if 'RO' in project_settings['rtd_thrm'] else 0
                boq['THERMOSTAT'] = boq['MCB'] if 'TO' in project_settings['rtd_thrm'] else 0
                boq['Pipe_Strap'] = boq['JB1PH'] + boq['RTD'] + boq['THERMOSTAT']

        boq['ENDTRM'] += no_of_circuits  # One termination per circuit

        # Compute Accessories
        '''AL Tape is considered to be applied at 250mm interval'''
        boq['Caution_Label'] = math.ceil(max(float(line_length) / float(project_settings['caution_label_interval']), 1))
        boq['Aluminium_Adhesive_Tape'] = math.ceil(max(float(pipe_size_mm) * math.pi * 4 * float(line_length) / 1000, 1))
              
        return boq
    except Exception as e:
        logging.error(f"Error in BOQ calculation for lune uid {power_distribution_data['uid'][0]}: {str(e)}")
        return {}


# ---------------------------------------------------------------------------------

### NOT USED: Refactored `boq.py` ###
# TODO: Refactor the following code snippet for BOQ compilation and validation 
def generate_boq(process_lines, power_distribution_results):
    """
    Generate a bill of quantities (BOQ) by validating against power distribution results.

    Args:
        process_lines (list of dict): List of process line details.
        power_distribution_results (dict): Electrical power distribution results.

    Returns:
        dict: BOQ including counts of junction boxes, isolators, cables, etc.
    """
    boq = {
        "junction_boxes": 0,
        "isolators": 0,
        "cables": 0,
        "accessories": {},
    }

    for line in process_lines:
        line_id = line["line_id"]
        if line_id not in power_distribution_results:
            continue

        power_data = power_distribution_results[line_id]

        # Validate power distribution results
        if power_data["voltage_drop"] > line["max_voltage_drop"]:
            raise ValueError(f"Voltage drop exceeds limits for line {line_id}")

        # Add BOQ items based on validated data
        boq["junction_boxes"] += 1
        boq["isolators"] += 1
        boq["cables"] += power_data["cable_length"]

        # Add accessories dynamically
        for accessory, count in power_data.get("accessories", {}).items():
            boq["accessories"].setdefault(accessory, 0)
            boq["accessories"][accessory] += count

    return boq
