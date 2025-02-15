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



def compute_power_distribution(power_params, project_setting):
    """
    Determines power distribution strategy based on circuit requirements.
    1. Computes how power is distributed from DB → JB → Tracer.
    2. Uses a branching strategy to distribute circuits optimally.
    3. Returns a structured plan for power flow.
    """
    try:
        db_to_jb_length = float(project_setting['ckt_ln'])  # DB to JB Cable Length
        loop_length = float(project_setting['loop_ln'])     # JB to JB Loop Length
      
        uid = power_params['uid']
        no_of_circuits = power_params['no_of_circuits']

        optimized_distribution = []
        branches = []

        # Distribute circuits optimally into branches
        remaining_circuits = no_of_circuits
        while remaining_circuits > 0:
            if remaining_circuits >= 3:
                branches.append(3)
                remaining_circuits -= 3
            elif remaining_circuits == 2:
                branches.append(2)
                remaining_circuits -= 2
            else:
                branches.append(1)
                remaining_circuits -= 1

        # Generate distribution strategy
        distribution_plan = {
            'uid': uid,
            'total_circuits': no_of_circuits,
            'branches': [],
            'db_to_jb_length': db_to_jb_length,
            'loop_length': loop_length
        }
        for branch in branches:
            if branch == 3:
                distribution_plan['branches'].append({
                    'type': '3phJB',
                    'connected_to': '3x 1phJB',
                    'circuit_count': 3,
                    'cable_length_db_to_jb': db_to_jb_length,
                    'cable_length_jb_to_jb': loop_length
                })
            elif branch == 2:
                distribution_plan['branches'].append({
                    'type': '3phJB',
                    'connected_to': '2x 1phJB',
                    'circuit_count': 2,
                    'cable_length_db_to_jb': db_to_jb_length,
                    'cable_length_jb_to_jb': loop_length
                })
            else:
                distribution_plan['branches'].append({
                    'type': '1phJB',
                    'connected_to': 'Tracer',
                    'circuit_count': 1,
                    'cable_length_db_to_jb': db_to_jb_length,
                    'cable_length_jb_to_jb': None
                })
        optimized_distribution.append(distribution_plan)

        return optimized_distribution
    except Exception as e:
        logging.error(f"Error in power distribution strategy calculation: {str(e)}")
        return []
