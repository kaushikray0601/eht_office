import logging
import re

import pandas as pd


BLANK_CATALOGUE_VALUES = {'', 'NA', 'N/A', 'NONE', 'NULL'}
SAFE_AREA_VALUES = {
    '',
    'SAFE',
    'UNCLASSIFIED',
    'NONHAZ',
    'NONHAZARDOUS',
    'NONHAZARDOUSAREA',
    'GENERALPURPOSE',
}
IEC_GAS_GROUP_RANK = {'IIA': 1, 'IIB': 2, 'IIC': 3}
ROMAN_ZONE_RANK = {'I': '1', 'II': '2'}
SR_NOMINAL_VOLTAGE_RULE_SET = 'SR_NOMINAL_VOLTAGE_CLASS_V1'
SR_NOMINAL_VOLTAGE_DEVIATION_LIMIT = 0.10
SR_REJECTION_RULE_SET = 'SR_SELECTION_REJECTION_REASON_V1'


def _is_blank(value):
    if value is None or pd.isna(value):
        return True
    return str(value).strip().upper() in BLANK_CATALOGUE_VALUES


def _normalized_text(value):
    if _is_blank(value):
        return ''
    return re.sub(r'[^A-Z0-9]+', '', str(value).upper())


def _series_has_declared_values(tracers, column):
    if column not in tracers:
        return False
    return tracers[column].map(lambda value: not _is_blank(value)).any()


def _filter_numeric_catalogue_limit(tracers, column, required_value):
    if column not in tracers or required_value is None:
        return tracers

    declared = tracers[column].map(lambda value: not _is_blank(value))
    if not declared.any():
        return tracers

    required_value = float(required_value)
    catalogue_values = pd.to_numeric(tracers[column], errors='coerce')
    return tracers[(~declared) | (catalogue_values >= required_value)]


def _catalogue_text_contains_required(catalogue_value, required_value):
    if _is_blank(required_value) or _is_blank(catalogue_value):
        return True
    return _normalized_text(required_value) in _normalized_text(catalogue_value)


def _area_requires_catalogue_match(area_class):
    return _normalized_text(area_class) not in SAFE_AREA_VALUES


def _extract_zone_tokens(value):
    if _is_blank(value):
        return set()
    zones = set()
    for match in re.finditer(r'ZONE\s*[- ]*(0|1|2|II|I)\b', str(value).upper()):
        zone = match.group(1)
        zones.add(f"ZONE{ROMAN_ZONE_RANK.get(zone, zone)}")
    return zones


def _catalogue_supports_area_zone(catalogue_value, required_area_class):
    project_zones = _extract_zone_tokens(required_area_class)
    if not project_zones or _is_blank(catalogue_value):
        return True
    catalogue_zones = _extract_zone_tokens(catalogue_value)
    if not catalogue_zones:
        return True
    return bool(project_zones & catalogue_zones)


def _extract_iec_gas_group(value):
    if _is_blank(value):
        return ''
    match = re.search(r'\b(IIA|IIB|IIC)\b', str(value).upper())
    return match.group(1) if match else ''


def _catalogue_supports_temperature_class(catalogue_value, required_temp_class):
    if _is_blank(required_temp_class) or _is_blank(catalogue_value):
        return True

    required_match = re.search(r'T([1-6])', str(required_temp_class).upper())
    if not required_match:
        return True

    required_rank = int(required_match.group(1))
    catalogue_text = str(catalogue_value).upper()
    catalogue_ranks = [int(rank) for rank in re.findall(r'T([1-6])', catalogue_text)]
    if not catalogue_ranks:
        return True

    return max(catalogue_ranks) >= required_rank


def _catalogue_supports_gas_group(catalogue_value, required_gas_group):
    if _is_blank(required_gas_group) or _is_blank(catalogue_value):
        return True

    catalogue_text = _normalized_text(catalogue_value)
    required_text = _normalized_text(required_gas_group)
    if required_text in catalogue_text:
        return True

    required_rank = IEC_GAS_GROUP_RANK.get(required_text)
    catalogue_rank = max(
        (rank for group, rank in IEC_GAS_GROUP_RANK.items() if group in catalogue_text),
        default=None,
    )
    if required_rank is None or catalogue_rank is None:
        return True
    return catalogue_rank >= required_rank


def _is_self_regulating_family(family):
    if _is_blank(family):
        return True
    normalized_family = _normalized_text(family)
    return normalized_family == 'SR' or 'SELFREGULATING' in normalized_family


def calculate_voltage_scenarios(system_voltage, voltage_var_factor, catalogue_voltage):
    system_voltage = float(system_voltage)
    voltage_var_factor = max(float(voltage_var_factor), 0.0)
    catalogue_voltage = float(catalogue_voltage)
    low_voltage = system_voltage * max(1 - voltage_var_factor, 0)
    high_voltage = system_voltage * (1 + voltage_var_factor)
    return {
        'low_voltage': low_voltage,
        'nominal_voltage': system_voltage,
        'high_voltage': high_voltage,
        'heat_delivery_correction': (low_voltage / catalogue_voltage) ** 2,
        'nominal_correction': (system_voltage / catalogue_voltage) ** 2,
        'max_current_correction': (high_voltage / catalogue_voltage) ** 2,
    }


def filter_sr_catalogue_voltage_compatibility(
    tracers,
    system_voltage,
    nominal_deviation_limit=SR_NOMINAL_VOLTAGE_DEVIATION_LIMIT,
):
    """Keep voltage-compatible SR rows without treating nominal voltage as a DB gate.

    Preference order:
    1. Use rows rated at/above the project nominal voltage when present.
    2. If a vendor only stores a nearby nominal class (for example 230 V for a
       240 V project), allow rows within the stated deviation limit and record
       that compatibility basis on the candidate rows.
    """
    if 'Voltage_Float' not in tracers:
        return tracers.copy()

    compatible_tracers = tracers.copy()
    catalogue_voltage = pd.to_numeric(compatible_tracers['Voltage_Float'], errors='coerce')
    declared = catalogue_voltage.notna() & (catalogue_voltage > 0)
    if not declared.any():
        return compatible_tracers

    system_voltage = float(system_voltage)
    voltage_deviation = abs(catalogue_voltage - system_voltage) / catalogue_voltage
    compatible_tracers['Catalogue_Voltage_Rule_Set'] = SR_NOMINAL_VOLTAGE_RULE_SET
    compatible_tracers['Catalogue_Voltage_Deviation'] = voltage_deviation

    rated_at_or_above = declared & (catalogue_voltage >= system_voltage)
    if rated_at_or_above.any():
        result = compatible_tracers[rated_at_or_above].copy()
        result['Catalogue_Voltage_Compatibility'] = 'rated_at_or_above_system_nominal'
        return result

    same_nominal_class = declared & (voltage_deviation <= float(nominal_deviation_limit))
    result = compatible_tracers[same_nominal_class].copy()
    if not result.empty:
        result['Catalogue_Voltage_Compatibility'] = 'nearby_nominal_voltage_class'
    return result


def filter_sr_catalogue_suitability(vendor_data, line, project_settings):
    """Filter SR catalogue rows where declared suitability data proves a mismatch."""
    tracers = vendor_data.copy()

    if _series_has_declared_values(tracers, 'Tracer_Family'):
        tracers = tracers[tracers['Tracer_Family'].map(_is_self_regulating_family)]

    tracers = _filter_numeric_catalogue_limit(tracers, 'Maint_T', line.get('maint_temp'))
    tracers = _filter_numeric_catalogue_limit(tracers, 'Max_Op_T', line.get('oper_temp'))
    tracers = _filter_numeric_catalogue_limit(tracers, 'Max_Exp_T_On', line.get('design_temp'))

    area_class = project_settings.get('area_class')
    if (
        _area_requires_catalogue_match(area_class)
        and _extract_zone_tokens(area_class)
        and _series_has_declared_values(tracers, 'Zone')
    ):
        tracers = tracers[
            tracers['Zone'].map(lambda value: _catalogue_supports_area_zone(value, area_class))
        ]

    gas_group = project_settings.get('gas_group') or _extract_iec_gas_group(area_class)
    if gas_group and _series_has_declared_values(tracers, 'Gas_Group'):
        tracers = tracers[
            tracers['Gas_Group'].map(lambda value: _catalogue_supports_gas_group(value, gas_group))
        ]

    temp_class = project_settings.get('temp_class')
    if temp_class and _series_has_declared_values(tracers, 'T_Rating'):
        tracers = tracers[
            tracers['T_Rating'].map(lambda value: _catalogue_supports_temperature_class(value, temp_class))
        ]

    return tracers.copy()


def _record_selection_rejection(heat_loss, code, message, details=None):
    heat_loss['selection_status'] = 'rejected'
    heat_loss['selection_rejection_reasons'] = [{
        'rule_set': SR_REJECTION_RULE_SET,
        'code': code,
        'message': message,
        'details': details or {},
    }]


def _record_selection_success(heat_loss):
    heat_loss['selection_status'] = 'selected'
    heat_loss['selection_rejection_reasons'] = []


def get_tracer_options(heat_loss, line, project_settings, vendor_data):
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
        if vendor_data.empty or 'Voltage_Float' not in vendor_data:
            logging.warning(f"No vendor catalogue rows available, UID: {line['uid']}")
            _record_selection_rejection(
                heat_loss,
                'NO_VENDOR_CATALOGUE_ROWS',
                'No catalogue rows were available for the selected vendor.',
            )
            return {}, []

        system_voltage = project_settings['voltage']
        voltage_var_factor = project_settings['voltage_var_factor'] / 100  # Convert percentage to fraction
        tracer_length_margin = project_settings['margin_on_tracer_lengths'] / 100
        spiral_allowed = project_settings['spiral_wrap_allowed']
        max_spiral_factor = project_settings['spiral_factor']
        min_spiral_factor = 0.8  # Hardcoded lower limit to prevent unrealistic spiral factors
        

        available_tracers = filter_sr_catalogue_suitability(vendor_data, line, project_settings)
        if available_tracers.empty:
            logging.warning(f"No SR tracers satisfy catalogue suitability limits, UID: {line['uid']}")
            _record_selection_rejection(
                heat_loss,
                'NO_SR_CATALOGUE_SUITABILITY',
                'No SR catalogue rows satisfied family, temperature, area, gas group, and T-rating suitability limits.',
                {'catalogue_rows': len(vendor_data.index)},
            )
            return {}, []

        available_tracers = filter_sr_catalogue_voltage_compatibility(available_tracers, system_voltage)
        if available_tracers.empty:
            logging.warning(f"No SR tracers satisfy catalogue voltage compatibility limits, UID: {line['uid']}")
            _record_selection_rejection(
                heat_loss,
                'NO_SR_CATALOGUE_VOLTAGE_COMPATIBILITY',
                'No SR catalogue rows satisfied the nominal voltage compatibility rule.',
                {'system_voltage': system_voltage},
            )
            return {}, []
        
        scenario_columns = available_tracers['Voltage_Float'].apply(
            lambda catalogue_voltage: calculate_voltage_scenarios(
                system_voltage,
                voltage_var_factor,
                catalogue_voltage,
            )
        )
        available_tracers['Heat_Delivery_Voltage'] = scenario_columns.map(lambda item: item['low_voltage'])
        available_tracers['Nominal_Voltage'] = scenario_columns.map(lambda item: item['nominal_voltage'])
        available_tracers['Max_Current_Voltage'] = scenario_columns.map(lambda item: item['high_voltage'])
        available_tracers['Voltage_Correction_Factor_Heat_Delivery'] = scenario_columns.map(
            lambda item: item['heat_delivery_correction']
        )
        available_tracers['Voltage_Correction_Factor'] = scenario_columns.map(lambda item: item['nominal_correction'])
        available_tracers['Voltage_Correction_Factor_Nominal'] = scenario_columns.map(
            lambda item: item['nominal_correction']
        )
        available_tracers['Voltage_Correction_Factor_Max_Current'] = scenario_columns.map(
            lambda item: item['max_current_correction']
        )
        
        # Calculate required tracer power output
        maint_temp = float(line['maint_temp'])
        base_power_at_maint = available_tracers.apply(
            lambda row: row['A_Coeff'] * maint_temp**2 + row['B_Coeff'] * maint_temp + row['C_Coeff'],
            axis=1,
        )
        available_tracers['Power_Output_Heat_Delivery'] = (
            base_power_at_maint * available_tracers['Voltage_Correction_Factor_Heat_Delivery']
        )
        available_tracers['Power_Output'] = available_tracers.apply(
            lambda row: (row['A_Coeff'] * maint_temp**2 + row['B_Coeff'] * maint_temp + row['C_Coeff']
                         ) * row['Voltage_Correction_Factor'], axis=1)

        # Filter out invalid tracers (negative or zero power output)
        valid_tracers = available_tracers[available_tracers['Power_Output_Heat_Delivery'] > 0].copy()
        if valid_tracers.empty:
            logging.warning(f"No valid tracers with required power output, UID: {line['uid']}")
            _record_selection_rejection(
                heat_loss,
                'NO_POSITIVE_POWER_OUTPUT',
                'No voltage-corrected SR rows had positive heat-delivery power at maintain temperature.',
                {'candidate_rows': len(available_tracers.index), 'maint_temp': maint_temp},
            )
            return {}, []
            
        # Size heat delivery at low voltage; nominal and high-voltage scenarios are used separately.
        valid_tracers.loc[:, 'Spiral_Factor'] = abs(
            heat_loss['heat_loss'] / valid_tracers['Power_Output_Heat_Delivery']
        )

        # Validate spiral factor within project constraints
        valid_tracers = valid_tracers[(valid_tracers['Spiral_Factor'] <= max_spiral_factor) & 
                                      (valid_tracers['Spiral_Factor'] >= min_spiral_factor) & 
                                      (spiral_allowed or (valid_tracers['Spiral_Factor'] <= 1.0))                                    ]
            
        if valid_tracers.empty:
            logging.warning(f"No valid tracers found within spiral factor limits, UID: {line['uid']}")
            _record_selection_rejection(
                heat_loss,
                'NO_SPIRAL_FACTOR_MATCH',
                'No SR rows satisfied the configured spiral factor limits.',
                {
                    'candidate_rows': len(available_tracers.index),
                    'min_spiral_factor': min_spiral_factor,
                    'max_spiral_factor': max_spiral_factor,
                    'spiral_wrap_allowed': spiral_allowed,
                },
            )
            return  {}, []

        # Calculate total required tracer length
        eqv_pipe_length = float(line['line_length'])
        tracer_adder = float(heat_loss['tracer_adder'])
        valid_tracers['Tracer_Length'] = (eqv_pipe_length + tracer_adder) * valid_tracers['Spiral_Factor']

        # Apply design margin to total tracer length       
        valid_tracers['Tracer_With_Margin'] = valid_tracers['Tracer_Length'] * (1 + tracer_length_margin)

        # Rank by efficiency (lowest length preferred, then lower power output)
        valid_tracers = valid_tracers.sort_values(by=['Tracer_With_Margin', 'Power_Output'], ascending=[True, True])

        # Select best tracer in dictionary and store alternatives in list
        best_tracer = valid_tracers.iloc[0].to_dict()   
        alternative_tracers = valid_tracers.iloc[1:].to_dict('records') if len(valid_tracers) > 1 else []
        _record_selection_success(heat_loss)

        return best_tracer, alternative_tracers
                
    except Exception as e:
        logging.error(f"Error selecting tracer for UID {line['uid']}: {str(e)}")
        _record_selection_rejection(
            heat_loss,
            'TRACER_SELECTION_ERROR',
            'Unexpected error while selecting SR tracer.',
            {'error': str(e)},
        )
        return {}, []
    


    
# # Custom function to convert Decimal to float
# def convert_decimal_to_float(obj):
#     if isinstance(obj, Decimal):
#         return float(obj)  # Convert Decimal to float
#     raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# ------------------------------------------------------------------------------------------------------
