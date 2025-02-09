import logging
import json
from decimal import Decimal
import math
from eht.models import ElecEHT_Vendor

def get_tracer_options(heat_loss, row, project_data, vendor_data):
    """
    Selects the optimal heating tracer from the vendor database.
    1. Fetches tracer data matching project specifications.
    2. Applies voltage correction factor.
    3. Computes spiral factor and validates against project constraints.
    4. Calculates total required tracer length.
    5. Stores best tracer & alternative tracers in JSON format.
    6. If no valid tracer is found, stores remark "No suitable SR tracer found".
    Returns:
    - best_tracer
    - alternative_tracers (JSON format)
    """
    try:
        system_voltage = float(project_data.voltage)
        voltage_var_factor = float(project_data.voltage_var_factor) / 100  # Convert percentage to fraction
        max_spiral_factor = float(project_data.spiral_factor)
        min_spiral_factor = 0.8  # Hardcoded lower limit to prevent unrealistic spiral factors
        spiral_allowed = project_data.spiral_wrap_allowed

        # !Check for other criteria! Filter vendor data to match project voltage and heating requirements
        available_tracers = vendor_data[vendor_data['Voltage_Float'] >= float(project_data.voltage)]

        if available_tracers.empty:  # Now this works because vendor_data is a DataFrame
            logging.warning(f"No tracers available for selected voltage, UID: {row['uid']}")
            return None, json.dumps({})
        
        # Apply voltage correction factor
        available_tracers['Voltage_Correction_Factor'] = (system_voltage / available_tracers['Voltage_Float'])**2
        
        # Calculate required tracer power output
        maint_temp = float(row['maint_temp'])
        available_tracers['Power_Output'] = available_tracers.apply(
            lambda row: (row['A_Coeff'] * maint_temp**2 + row['B_Coeff'] * maint_temp + row['C_Coeff']
                         ) * row['Voltage_Correction_Factor'], axis=1)

        # Filter out invalid tracers (negative or zero power output)
        valid_tracers = available_tracers[available_tracers['Power_Output'] > 0].copy()  # Explicitly create a copy
        if valid_tracers.empty:
            logging.warning(f"No valid tracers with required power output, UID: {row['uid']}")
            return "No suitable SR tracer found", json.dumps({})
            
        # Calculate spiral factor (Voltage variation factor is considered to compensate for low power tracers those have output < heat loss)
        valid_tracers.loc[:, 'Spiral_Factor'] = abs((heat_loss * (1 + voltage_var_factor)) / valid_tracers['Power_Output'])

        # Validate spiral factor within project constraints
        valid_tracers = valid_tracers[(valid_tracers['Spiral_Factor'] <= max_spiral_factor) & 
                                      (valid_tracers['Spiral_Factor'] >= min_spiral_factor) & 
                                      (spiral_allowed or (valid_tracers['Spiral_Factor'] <= 1.0))
                                    ]
        # # If spiraling is not allowed, filter out all tracers with Spiral Factor > 1
        # if not spiral_allowed:
        #     valid_tracers = valid_tracers[valid_tracers['Spiral_Factor'] <= 1.0]
        
        if valid_tracers.empty:
            logging.warning(f"No valid tracers found within spiral factor limits, UID: {row['uid']}")
            return "No suitable SR tracer found", json.dumps({})

        # Calculate total required tracer length
        eqv_pipe_length = float(row['line_length'])
        tracer_adder = float(row['tracer_adder'])
        valid_tracers['Tracer_Length'] = (eqv_pipe_length + tracer_adder) * valid_tracers['Spiral_Factor']

        # Apply design margin to total tracer length
        tracer_length_margin = float(project_data.margin_on_tracer_lengths) / 100
        valid_tracers['Tracer_With_Margin'] = valid_tracers['Tracer_Length'] * (1 + tracer_length_margin)

        # Rank by efficiency (lowest length preferred, then lower power output)
        valid_tracers = valid_tracers.sort_values(by=['Tracer_With_Margin', 'Power_Output'], ascending=[True, True])

        # Select best tracer and store alternatives as JSON
        best_tracer = valid_tracers.iloc[0].to_dict()
        alternative_tracers = valid_tracers.iloc[1:].to_dict('records')

        return best_tracer, json.dumps(alternative_tracers, default=convert_decimal_to_float)
                
    except Exception as e:
        logging.error(f"Error selecting tracer for UID {row['uid']}: {str(e)}")
        return "Error in tracer selection", json.dumps({})
    
# Custom function to convert Decimal to float
def convert_decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)  # Convert Decimal to float
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")