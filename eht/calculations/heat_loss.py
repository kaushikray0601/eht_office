import math
import logging


MM_PER_INCH = 25.4
FT_PER_METER = 3.048
SR_ACCESSORY_ADDER_RULE_SET = 'SR_LEGACY_EMPIRICAL_PIPE_SIZE_IN_V1'


def _as_float(value):
    if value in (None, ''):
        return 0.0
    return float(value)


def _flange_adder_per_item_m(pipe_size_in):
    if pipe_size_in < 3:
        return 0.3
    if pipe_size_in < 6:
        return 0.5
    if pipe_size_in < 14:
        return 0.8
    return 1.0


def calculate_accessory_adders(line, pipe_size_mm):
    """Return SR tracer-length adders and rule evidence for line accessories."""
    pipe_size_in = _as_float(pipe_size_mm) / MM_PER_INCH
    accessory_rules = {
        'valve': {
            'quantity_field': 'valve_qty',
            'quantity': _as_float(line.get('valve_qty')),
            'per_item_m': (3.5 + 0.5 * pipe_size_in) / FT_PER_METER,
        },
        'support': {
            'quantity_field': 'support_qty',
            'quantity': _as_float(line.get('support_qty')),
            'per_item_m': (2 + 0.08 * pipe_size_in) / FT_PER_METER,
        },
        'flange': {
            'quantity_field': 'flange_qty',
            'quantity': _as_float(line.get('flange_qty')),
            'per_item_m': _flange_adder_per_item_m(pipe_size_in),
        },
    }

    adders = {}
    basis_items = {}
    for accessory_type, rule in accessory_rules.items():
        total_m = rule['quantity'] * rule['per_item_m']
        adders[accessory_type] = total_m
        basis_items[accessory_type] = {
            'quantity_field': rule['quantity_field'],
            'quantity': rule['quantity'],
            'per_item_m': rule['per_item_m'],
            'total_m': total_m,
        }

    adders['total'] = sum(adders.values())
    adders['basis'] = {
        'rule_set': SR_ACCESSORY_ADDER_RULE_SET,
        'pipe_size_basis': 'pipe_od_in',
        'pipe_size_in': pipe_size_in,
        'items': basis_items,
    }
    return adders


def calculate_heat_loss(line, project_specific_settings, asme_b36_table, thermal_cond_data):

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
        maint_t = float(line['maint_temp'])
        insul_thick = float(line['insul_thick'])
        ins_mat_type = str(line['ins_mat_type'])

        # (A) Fetch conductivity data
        conductivity_constants = thermal_cond_data[thermal_cond_data['Ins_Mat_Type'] == ins_mat_type]
        if conductivity_constants.empty:
            logging.warning(f"No thermal conductivity data for '{ins_mat_type}', UID {line['uid']}")
            return None
        
        cond_a, cond_b, cond_c = conductivity_constants.iloc[0][['K_factor_A', 'K_factor_B', 'K_factor_C']]
        conductivity = float(cond_a * maint_t**2 + cond_b * maint_t + cond_c)
        
        # (B) Fetch pipe outer diameter from ASME B36
        pipe_size_in = float(line['line_size'])
        outer_dia_mm = asme_b36_table[asme_b36_table['Nominal_Pipe_Size'] == pipe_size_in]['Outside_Diameter_mm']
        
        if outer_dia_mm.empty:
            pipe_size_mm = 25.206 * pipe_size_in + 9.4852  # Approximation formula
            # logging.info(f"No ASME B36 data for pipe size {pipe_size_in} inch, using approximation.")
        else:
            pipe_size_mm = outer_dia_mm.iloc[0]
        
        # (C) Calculate base heat loss
        delta_tmp = maint_t - project_specific_settings['min_amb_t']
        if pipe_size_mm > 0:
            base_heat_loss = (2 * math.pi * conductivity * delta_tmp) / math.log((2 * insul_thick + pipe_size_mm) / pipe_size_mm)
        else:
            base_heat_loss = 0
            logging.warning(f"Pipe diameter is zero for UID {line['uid']}")
        
        # (D) Wind speed correction (1% per mph over 32 kmph, max 20%)
        wind_correction = max(1 + min(20, (float(project_specific_settings['wind_speed']) - 32) / 1.60934) / 100, 1)
        
        base_heat_loss *= wind_correction
        heat_loss_sf = float(project_specific_settings.get('heat_loss_sf', 1) or 1)
        design_heat_loss = base_heat_loss * heat_loss_sf
        
        # (E) Additional tracer length due to accessories
        accessory_adders = calculate_accessory_adders(line, pipe_size_mm)
        tracer_adder = accessory_adders['total']
        
        heat_loss= {
            'uid': line['uid'],
            'heat_loss': design_heat_loss,
            'base_heat_loss': base_heat_loss,
            'design_heat_loss': design_heat_loss,
            'heat_loss_sf': heat_loss_sf,
            'pipe_size_mm': pipe_size_mm,
            'conductivity': conductivity,
            'wind_correction': wind_correction,
            'accessory_adders': accessory_adders,
            'tracer_adder':tracer_adder
        }

        return heat_loss

    except Exception as e:
        logging.error(f"Error calculating heat loss for UID {line['uid']}: {str(e)}")
        return None
