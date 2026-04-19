import math
import logging

def compute_power_params(line, project_settings, asme_data, selected_tracer):
    """
    Computes electrical parameters for each heating circuit.
    1. Computes number of circuits based on max breaker size.
    2. Assigns appropriate breaker rating.
    3. Computes operating current, max current, and operating load.
    4. Applies termination margin and other accessory margins.
    Returns:
        - no_of_circuits
        - breaker_size
        - operating_current
        - max_current
        - operating_load
        - total_tracer_length
    """
    try:
        voltage = project_settings['voltage']
        max_cb_size = project_settings['max_cb_size']
        margin_on_max_cb_size = project_settings['restrict_cb_current'] / 100  # Convert percentage to fraction     
        tracer_length = float(selected_tracer['Tracer_With_Margin'])
        tracer_A_const = float(selected_tracer['A_Coeff'])
        tracer_B_const = float(selected_tracer['B_Coeff'])
        tracer_C_const = float(selected_tracer['C_Coeff'])
        min_amb_temp = float(project_settings['min_amb_t'])
        operating_temp = float(line['oper_temp'])
        vendorVoltage_Correction = float(selected_tracer['Voltage_Correction_Factor'])
   
        # Compute Maximum Current
        maximum_current = (
            (tracer_A_const * min_amb_temp**2 + tracer_B_const * min_amb_temp + tracer_C_const)
            * (tracer_length * vendorVoltage_Correction)
        ) / voltage

        # Compute Operating Current
        operating_current = (
            (tracer_A_const * operating_temp**2 + tracer_B_const * operating_temp + tracer_C_const)
            * (tracer_length * vendorVoltage_Correction)
        ) / voltage

        # Compute No. of Circuits Required
        no_of_circuits = math.ceil(maximum_current / (max_cb_size * margin_on_max_cb_size))

        # Breaker Size Selection
        breaker_sizes = [2, 4, 6, 10, 16, 20, 25, 32, 40]
        breaker_size = next((size for size in breaker_sizes if size >= maximum_current), max_cb_size)
        
        # Compute Operating Load
        operating_load = operating_current * voltage
        
        # Apply termination margins to tracer length
        total_tracer_length = tracer_length + no_of_circuits * float(project_settings['termination_margin']) / 1000
       
        outer_dia_mm = asme_data.loc[asme_data['Nominal_Pipe_Size'] == float(line['line_size']), 'Outside_Diameter_mm']
        pipe_size_mm = outer_dia_mm.iloc[0] if not outer_dia_mm.empty else 25.206 * float(line['line_size']) + 9.4852
        return {
            'uid': line['uid'],
            'no_of_circuits': no_of_circuits,
            'breaker_size': breaker_size,
            'operating_current': operating_current,
            'max_current': maximum_current,
            'operating_load': operating_load,
            'total_tracer_length': total_tracer_length,
            'pipe_size_mm':pipe_size_mm if pipe_size_mm else 0
        }
    except Exception as e:
        logging.error(f"Error in power parameter computation for UID {line['uid']}: {str(e)}")
        return None

def compute_power_distribution(power_params, project_settings):
    """
    Compute the power distribution for a given process line and include tagging logic.

    Args:
        process_line (dict): Process line data containing line attributes and circuit details.
        project_settings (dict): Project-specific settings.

    Returns:
        dict: Power distribution results with tagging and relationships.
    """
    # Initialize results
    power_distribution_results = {
        "uid": power_params["uid"],
        "total_circuits": power_params["no_of_circuits"],
        "branches": []
    }

    # Tag counters for unique tag generation
    tag_counter = {
        "MCB": 1,
        "Cable4C": 1,
        "Cable3C": 1,
        "Isolator3PH": 1,
        "Isolator1PH": 1,
        "JB3PH": 1,
        "JB1PH": 1,
        "Tracer": 1,
        "EndTermination": 1
    }

    total_circuits = power_params["no_of_circuits"]
    remaining_circuits = total_circuits
    isolator_setting = project_settings.get('isolator_location', 'none')

    # Process circuits in batches of 3
    while remaining_circuits > 0:
        circuits_in_this_batch = min(3, remaining_circuits)
        remaining_circuits -= circuits_in_this_batch

        # Generate upstream tags for this batch
        mcb_tag = f"MCB_{tag_counter['MCB']:03d}"
        cable4c_tag = f"CCAB4C_{tag_counter['Cable4C']:03d}"
        isolator_3ph_tag = (
            f"ISOL_3PH_{tag_counter['Isolator3PH']:03d}"
            if isolator_setting in ['bothSides', 'incomingOnly']
            else None
        )
        jb3ph_tag = f"JB3PH_{tag_counter['JB3PH']:03d}"

        # Increment upstream tag counters
        tag_counter["MCB"] += 1
        tag_counter["Cable4C"] += 1
        if isolator_3ph_tag:
            tag_counter["Isolator3PH"] += 1
        tag_counter["JB3PH"] += 1

        # Initialize branch data
        branch = {
            "type": "3phJB" if circuits_in_this_batch > 1 else "1phJB",
            "circuit_count": circuits_in_this_batch,      
            "connected_to": "3x 1phJB" if circuits_in_this_batch == 3 else "2x 1phJB" if circuits_in_this_batch == 2 else "Tracer",
            "cable_length_db_to_jb": project_settings["ckt_ln"],
            "cable_length_jb_to_jb": project_settings["loop_ln"] if circuits_in_this_batch > 1 else None,
            "tagged_components": {
                "MCB": mcb_tag,
                "Cable4C": cable4c_tag,
                "Isolator3PH": isolator_3ph_tag,
                "JB3PH": jb3ph_tag,
                "Downstream": []
            }
        }

        # Generate downstream tags for each circuit in this batch
        for _ in range(circuits_in_this_batch):
            cable3c_tag = f"CCAB3C_{tag_counter['Cable3C']:03d}"
            jb1ph_tag = f"JB1PH_{tag_counter['JB1PH']:03d}"
            tracer_tag = f"Tracer_{tag_counter['Tracer']:03d}"
            end_term_tag = f"ENDTRM_{tag_counter['EndTermination']:03d}"

            # Add downstream components
            downstream = {
                "Cable3C": cable3c_tag,
                "JB1PH": jb1ph_tag,
                "Tracer": tracer_tag,
                "EndTermination": end_term_tag
            }
            branch["tagged_components"]["Downstream"].append(downstream)

            # Increment downstream tag counters
            tag_counter["Cable3C"] += 1
            tag_counter["JB1PH"] += 1
            tag_counter["Tracer"] += 1
            tag_counter["EndTermination"] += 1

        # Add Isolator 1PH if required
        if isolator_setting in ['bothSides', 'outgoingOnly']:
            isolator_1ph_tag = f"ISOL_1PH_{tag_counter['Isolator1PH']:03d}"
            tag_counter["Isolator1PH"] += 1
            branch["tagged_components"]["Isolator1PH"] = isolator_1ph_tag

        # Append branch to results
        power_distribution_results["branches"].append(branch)

    return power_distribution_results
