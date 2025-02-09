import math
import logging

def calculate_heat_loss(row, project_data, asme_data, thermal_data):

    """   
    Calculates heat loss per line based on insulation thickness, pipe size, and temperature.
    Includes:
        - Conductivity calculation based on insulation type.
        - Pipe diameter retrieval from ASME B36.
        - Heat loss calculation using thermal conductivity.
        - Wind speed correction.
        - Additional tracer length due to valves, supports, flanges.
    """
    try:
        maint_t = float(row['maint_temp'])
        insul_thick = float(row['insul_thick'])
        ins_mat_type = str(row['ins_mat_type'])

        # (A) Fetch conductivity data
        conductivity_constants = thermal_data[thermal_data['Ins_Mat_Type'] == ins_mat_type]
        if conductivity_constants.empty:
            logging.warning(f"No thermal conductivity data for '{ins_mat_type}', UID {row['uid']}")
            return None
        
        cond_a, cond_b, cond_c = conductivity_constants.iloc[0][['K_factor_A', 'K_factor_B', 'K_factor_C']]
        conductivity = float(cond_a * maint_t**2 + cond_b * maint_t + cond_c)
        
        # (B) Fetch pipe outer diameter from ASME B36
        pipe_size_in = float(row['line_size'])
        outer_dia_mm = asme_data[asme_data['Nominal_Pipe_Size'] == pipe_size_in]['Outside_Diameter_mm']
        
        if outer_dia_mm.empty:
            pipe_size_mm = 25.206 * pipe_size_in + 9.4852  # Approximation formula
            logging.info(f"No ASME B36 data for pipe size {pipe_size_in} inch, using approximation.")
        else:
            pipe_size_mm = outer_dia_mm.iloc[0]
        
        # (C) Calculate heat loss
        delta_tmp = maint_t - float(project_data.min_amb_t)
        if pipe_size_mm > 0:
            heat_loss = (2 * math.pi * conductivity * delta_tmp) / math.log((2 * insul_thick + pipe_size_mm) / pipe_size_mm)
        else:
            heat_loss = 0
            logging.warning(f"Pipe diameter is zero for UID {row['uid']}")
        
        # (D) Wind speed correction (1% per mph over 32 kmph, max 20%)
        wind_correction = max(1 + min(20, (float(project_data.wind_speed) - 32) / 1.60934) / 100, 1)
        
        heat_loss *= wind_correction
        
        # (E) Additional tracer length due to accessories
        pipe_size = pipe_size_mm / 25.4  # Convert to inches
        add_tracer_for_valve = float(row['valve_qty']) * (3.5 + 0.5 * pipe_size) / 3.048
        add_tracer_for_support = float(row['support_qty']) * (2 + 0.08 * pipe_size) / 3.048
        add_tracer_for_flange = float(row['flange_qty']) * (0.3 if pipe_size < 3 else 0.5 if pipe_size < 6 else 0.8 if pipe_size < 14 else 1)
        
        tracer_adder = add_tracer_for_valve + add_tracer_for_support + add_tracer_for_flange
        
        return {
            'uid': row['uid'],
            'heat_loss': heat_loss,
            'tracer_adder':tracer_adder
        }
    
    except Exception as e:
        logging.error(f"Error calculating heat loss for UID {row['uid']}: {str(e)}")
        return None
