import math
import logging

from eht.heat_loss_methods import (
    DEFAULT_HEAT_LOSS_METHOD,
    HEAT_LOSS_METHOD_LEGACY_MAINT_TEMPERATURE,
    HEAT_LOSS_METHOD_LABELS,
    PLACEHOLDER_HEAT_LOSS_METHODS,
    normalize_heat_loss_method,
)


MM_PER_INCH = 25.4
FT_PER_METER = 3.048
CONDUCTIVITY_BASIS_MEAN_TEMPERATURE = 'MEAN_INSULATION_TEMPERATURE_AMBIENT_SURFACE_V1'
CONDUCTIVITY_BASIS_LEGACY_MAINT_TEMPERATURE = 'LEGACY_MAINTAIN_TEMPERATURE_V1'
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


def _conductivity_coefficients(conductivity_constants):
    constants = conductivity_constants.iloc[0]
    return {
        'K_factor_A': _as_float(constants['K_factor_A']),
        'K_factor_B': _as_float(constants['K_factor_B']),
        'K_factor_C': _as_float(constants['K_factor_C']),
    }


def _polynomial_conductivity(coefficients, temperature_c):
    temperature_c = _as_float(temperature_c)
    return float(
        coefficients['K_factor_A'] * temperature_c**2
        + coefficients['K_factor_B'] * temperature_c
        + coefficients['K_factor_C']
    )


def calculate_insulation_conductivity(maint_t, ambient_t, conductivity_constants, requested_method=None):
    """Return insulation conductivity and method evidence for the SR heat-loss engine."""
    requested_method = normalize_heat_loss_method(requested_method)
    effective_method = requested_method
    warnings = []
    if requested_method in PLACEHOLDER_HEAT_LOSS_METHODS:
        effective_method = DEFAULT_HEAT_LOSS_METHOD
        warnings.append(
            f"{HEAT_LOSS_METHOD_LABELS[requested_method]} is a placeholder; "
            f"using {HEAT_LOSS_METHOD_LABELS[effective_method]} for this calculation."
        )

    coefficients = _conductivity_coefficients(conductivity_constants)
    maint_t = _as_float(maint_t)
    ambient_t = _as_float(ambient_t)

    if effective_method == HEAT_LOSS_METHOD_LEGACY_MAINT_TEMPERATURE:
        evaluation_temperature_c = maint_t
        temperature_basis = 'maint_temp'
        rule_set = CONDUCTIVITY_BASIS_LEGACY_MAINT_TEMPERATURE
        outer_surface_temperature_basis = None
    else:
        evaluation_temperature_c = (maint_t + ambient_t) / 2
        temperature_basis = 'mean_insulation_temperature'
        rule_set = CONDUCTIVITY_BASIS_MEAN_TEMPERATURE
        outer_surface_temperature_basis = 'ambient_approximation_pending_external_solver'

    conductivity = _polynomial_conductivity(coefficients, evaluation_temperature_c)
    return {
        'conductivity': conductivity,
        'basis': {
            'requested_method': requested_method,
            'effective_method': effective_method,
            'requested_method_label': HEAT_LOSS_METHOD_LABELS[requested_method],
            'effective_method_label': HEAT_LOSS_METHOD_LABELS[effective_method],
            'rule_set': rule_set,
            'temperature_basis': temperature_basis,
            'hot_face_temperature_c': maint_t,
            'cold_face_temperature_c': ambient_t,
            'evaluation_temperature_c': evaluation_temperature_c,
            'outer_surface_temperature_basis': outer_surface_temperature_basis,
            'formula': 'A*T^2 + B*T + C',
            'coefficients': coefficients,
            'warnings': warnings,
        },
    }


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
        ambient_t = float(project_specific_settings['min_amb_t'])

        # (A) Fetch conductivity data
        conductivity_constants = thermal_cond_data[thermal_cond_data['Ins_Mat_Type'] == ins_mat_type]
        if conductivity_constants.empty:
            logging.warning(f"No thermal conductivity data for '{ins_mat_type}', UID {line['uid']}")
            return None
        
        conductivity_result = calculate_insulation_conductivity(
            maint_t,
            ambient_t,
            conductivity_constants,
            project_specific_settings.get('heat_loss_method'),
        )
        conductivity = conductivity_result['conductivity']
        
        # (B) Fetch pipe outer diameter from ASME B36
        pipe_size_in = float(line['line_size'])
        outer_dia_mm = asme_b36_table[asme_b36_table['Nominal_Pipe_Size'] == pipe_size_in]['Outside_Diameter_mm']
        
        if outer_dia_mm.empty:
            pipe_size_mm = 25.206 * pipe_size_in + 9.4852  # Approximation formula
            # logging.info(f"No ASME B36 data for pipe size {pipe_size_in} inch, using approximation.")
        else:
            pipe_size_mm = outer_dia_mm.iloc[0]
        
        # (C) Calculate base heat loss
        delta_tmp = maint_t - ambient_t
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
            'conductivity_basis': conductivity_result['basis'],
            'wind_correction': wind_correction,
            'accessory_adders': accessory_adders,
            'tracer_adder':tracer_adder
        }

        return heat_loss

    except Exception as e:
        logging.error(f"Error calculating heat loss for UID {line['uid']}: {str(e)}")
        return None
