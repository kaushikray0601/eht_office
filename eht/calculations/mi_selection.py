import logging
import re

from eht.calculations.tracer_selection import (
    _area_requires_catalogue_match,
    _catalogue_supports_area_zone,
    _catalogue_supports_gas_group,
    _catalogue_supports_temperature_class,
    _extract_iec_gas_group,
    _is_blank,
)
from eht.models import MIAlloyTempFactor, MICableFamily


logger = logging.getLogger(__name__)


MI_REJECTION_RULE_SET = 'MI_SELECTION_REJECTION_REASON_V1'
MI_SELECTION_RULE_SET = 'MI_SINGLE_PHASE_SELECTION_MVP_V1'
MI_RESISTANCE_TEMPERATURE_RULE_SET = 'MI_ALLOY_RESISTANCE_TEMPERATURE_FACTOR_V1'
T_CLASS_LIMIT_C = {
    'T1': 450.0,
    'T2': 300.0,
    'T3': 200.0,
    'T4': 135.0,
    'T5': 100.0,
    'T6': 85.0,
}


def _value(source, key, default=None):
    if hasattr(source, 'get'):
        return source.get(key, default)
    return getattr(source, key, default)


def _float_value(source, key, default=0.0):
    value = _value(source, key, default)
    if value is None:
        return default
    return float(value)


def _extract_t_class(value):
    if _is_blank(value):
        return ''
    match = re.search(r'T([1-6])', str(value).upper())
    return f"T{match.group(1)}" if match else ''


def _t_class_limit(project_settings):
    temp_class = _extract_t_class(project_settings.get('temp_class'))
    return T_CLASS_LIMIT_C.get(temp_class, 0.0)


def _record_mi_rejection(heat_loss, code, message, details=None):
    heat_loss['mi_selection_status'] = 'rejected'
    heat_loss['mi_selection_rejection_reasons'] = [{
        'rule_set': MI_REJECTION_RULE_SET,
        'code': code,
        'message': message,
        'details': details or {},
    }]


def _record_mi_success(heat_loss):
    heat_loss['mi_selection_status'] = 'selected'
    heat_loss['mi_selection_rejection_reasons'] = []


def _query_families(project_settings, families=None):
    if families is not None:
        return list(families)
    return list(MICableFamily.objects.filter(vendor=project_settings.get('vendor')).prefetch_related(
        'heaters__cold_lead_options',
    ))


def _temperature_factor_lookup(families):
    alloy_types = {
        family.alloy_type
        for family in families
        if family.alloy_type
    }
    factors_by_alloy = {}
    if not alloy_types:
        return factors_by_alloy

    for factor in MIAlloyTempFactor.objects.filter(alloy_type__in=alloy_types).order_by('alloy_type', 'temperature_c'):
        factors_by_alloy.setdefault(factor.alloy_type, []).append(factor)
    return factors_by_alloy


def _interpolate_resistance_multiplier(factors, target_temperature_c):
    if not factors:
        return 1.0, 'default_no_factor_table'

    target_temperature_c = float(target_temperature_c)
    ordered = sorted(factors, key=lambda item: item.temperature_c)
    if target_temperature_c <= ordered[0].temperature_c:
        return float(ordered[0].resistance_multiplier), 'nearest_low_endpoint'
    if target_temperature_c >= ordered[-1].temperature_c:
        return float(ordered[-1].resistance_multiplier), 'nearest_high_endpoint'

    for lower, upper in zip(ordered, ordered[1:]):
        if lower.temperature_c == target_temperature_c:
            return float(lower.resistance_multiplier), 'exact'
        if lower.temperature_c <= target_temperature_c <= upper.temperature_c:
            if upper.temperature_c == lower.temperature_c:
                return float(lower.resistance_multiplier), 'duplicate_temperature_endpoint'
            fraction = (target_temperature_c - lower.temperature_c) / (upper.temperature_c - lower.temperature_c)
            multiplier = lower.resistance_multiplier + fraction * (upper.resistance_multiplier - lower.resistance_multiplier)
            return float(multiplier), 'linear_interpolation'

    return 1.0, 'default_no_matching_temperature'


def _resistance_temperature_basis(family, line, project_settings, factors_by_alloy):
    factors = factors_by_alloy.get(family.alloy_type, [])
    maintain_temp_c = _float_value(line, 'maint_temp')
    startup_temp_c = float(project_settings.get('startup_t') or maintain_temp_c)
    maintain_multiplier, maintain_method = _interpolate_resistance_multiplier(factors, maintain_temp_c)
    startup_multiplier, startup_method = _interpolate_resistance_multiplier(factors, startup_temp_c)
    return {
        'rule_set': MI_RESISTANCE_TEMPERATURE_RULE_SET,
        'alloy_type': family.alloy_type,
        'factor_rows': len(factors),
        'maintain_temp_c': maintain_temp_c,
        'startup_temp_c': startup_temp_c,
        'maintain_multiplier': maintain_multiplier,
        'startup_multiplier': startup_multiplier,
        'maintain_method': maintain_method,
        'startup_method': startup_method,
    }


def _is_family_suitable(family, line, project_settings, heated_length_m):
    """Apply hard catalogue gates before detailed candidate evaluation."""
    reasons = []
    voltage = float(project_settings.get('voltage') or 0.0)
    maintain_temp = _float_value(line, 'maint_temp')
    design_temp = _float_value(line, 'design_temp')

    if not family.is_validated:
        reasons.append('UNVALIDATED_CATALOGUE')
    if family.max_voltage and family.max_voltage < voltage:
        reasons.append('VOLTAGE_EXCEEDS_FAMILY_LIMIT')
    if family.max_maintain_temp_c and family.max_maintain_temp_c < maintain_temp:
        reasons.append('MAINTAIN_TEMP_EXCEEDS_FAMILY_LIMIT')
    if family.max_exposure_temp_c and family.max_exposure_temp_c < design_temp:
        reasons.append('EXPOSURE_TEMP_EXCEEDS_FAMILY_LIMIT')
    if family.min_circuit_length_m and heated_length_m < family.min_circuit_length_m:
        reasons.append('HEATED_LENGTH_BELOW_FAMILY_MINIMUM')
    if family.max_circuit_length_m and heated_length_m > family.max_circuit_length_m:
        reasons.append('HEATED_LENGTH_EXCEEDS_FAMILY_MAXIMUM')

    area_class = project_settings.get('area_class')
    if (
        _area_requires_catalogue_match(area_class)
        and not _catalogue_supports_area_zone(family.zone_approval, area_class)
    ):
        reasons.append('AREA_ZONE_MISMATCH')

    gas_group = project_settings.get('gas_group') or _extract_iec_gas_group(area_class)
    if gas_group and not _catalogue_supports_gas_group(family.gas_group, gas_group):
        reasons.append('GAS_GROUP_MISMATCH')

    temp_class = project_settings.get('temp_class')
    if temp_class and not _catalogue_supports_temperature_class(family.temp_class_rating, temp_class):
        reasons.append('TEMPERATURE_CLASS_RATING_MISMATCH')

    return reasons


def _evaluate_single_phase_candidate(heat_loss, line, project_settings, family, heater, cold_lead, factors_by_alloy=None):
    heated_length_m = _heated_length_m(heat_loss, line)
    if heated_length_m <= 0:
        return None, ['NON_POSITIVE_HEATED_LENGTH']

    resistance_basis = _resistance_temperature_basis(family, line, project_settings, factors_by_alloy or {})
    heater_base_resistance_ohms = float(heater.resistance_ohms_m) * heated_length_m
    heater_resistance_ohms = heater_base_resistance_ohms * resistance_basis['maintain_multiplier']
    heater_startup_resistance_ohms = heater_base_resistance_ohms * resistance_basis['startup_multiplier']
    cold_lead_resistance_ohms = float(heater.cold_lead_resistance_ohms_m) * float(cold_lead.length_m)
    total_resistance_ohms = heater_resistance_ohms + cold_lead_resistance_ohms
    startup_total_resistance_ohms = heater_startup_resistance_ohms + cold_lead_resistance_ohms
    if total_resistance_ohms <= 0 or heater_resistance_ohms <= 0 or startup_total_resistance_ohms <= 0:
        return None, ['NON_POSITIVE_RESISTANCE']

    voltage = float(project_settings.get('voltage') or 0.0)
    variation = max(float(project_settings.get('voltage_var_factor') or 0.0), 0.0) / 100.0
    low_voltage = voltage * max(1.0 - variation, 0.0)
    high_voltage = voltage * (1.0 + variation)
    design_heat_loss_w_m = float(heat_loss.get('design_heat_loss') or heat_loss.get('heat_loss') or 0.0)

    low = _single_phase_power(low_voltage, heater_resistance_ohms, cold_lead_resistance_ohms, heated_length_m)
    nominal = _single_phase_power(voltage, heater_resistance_ohms, cold_lead_resistance_ohms, heated_length_m)
    high = _single_phase_power(high_voltage, heater_startup_resistance_ohms, cold_lead_resistance_ohms, heated_length_m)

    reasons = []
    if low['power_density_w_m'] < design_heat_loss_w_m:
        reasons.append('INSUFFICIENT_HEAT_AT_LOW_VOLTAGE')
    if family.max_watt_density_w_m and high['power_density_w_m'] > float(family.max_watt_density_w_m):
        reasons.append('EXCEEDS_FAMILY_WATT_DENSITY')
    if heater.max_current_a and high['current_a'] > float(heater.max_current_a):
        reasons.append('EXCEEDS_HEATER_CURRENT_LIMIT')
    if heater.cold_lead_max_ampacity_a and high['current_a'] > float(heater.cold_lead_max_ampacity_a):
        reasons.append('EXCEEDS_COLD_LEAD_AMPACITY')

    max_cb_size = float(project_settings.get('max_cb_size') or 0.0)
    restricted_loading_factor = float(project_settings.get('restrict_cb_current') or 0.0) / 100.0
    allowed_current_per_circuit = max_cb_size * restricted_loading_factor
    if allowed_current_per_circuit > 0 and high['current_a'] > allowed_current_per_circuit:
        reasons.append('EXCEEDS_PROJECT_BREAKER_LOADING_LIMIT')

    allowable_vdrop = float(project_settings.get('allowablevdrop') or 0.0)
    if allowable_vdrop > 0 and nominal['cold_lead_voltage_drop_percent'] > allowable_vdrop:
        reasons.append('EXCEEDS_COLD_LEAD_VOLTAGE_DROP')

    t_class_limit_c = _t_class_limit(project_settings)
    t_class_verdict = 'review'
    if t_class_limit_c <= 0 or not family.max_sheath_temp_c:
        reasons.append('MISSING_T_CLASS_EVIDENCE')
    elif float(family.max_sheath_temp_c) <= t_class_limit_c:
        t_class_verdict = 'pass'
    else:
        t_class_verdict = 'fail'
        reasons.append('FAILS_T_CLASS_SHEATH_TEMPERATURE')

    candidate = {
        'rule_set': MI_SELECTION_RULE_SET,
        'family_id': family.id,
        'family_name': family.family_name,
        'vendor': family.vendor,
        'heater_id': heater.id,
        'heater_part_number': heater.part_number,
        'cold_lead_option_id': cold_lead.id,
        'cold_lead_option_code': cold_lead.option_code,
        'heated_length_m': heated_length_m,
        'cold_lead_length_m': float(cold_lead.length_m),
        'heater_resistance_ohms': heater_resistance_ohms,
        'heater_base_resistance_ohms': heater_base_resistance_ohms,
        'heater_startup_resistance_ohms': heater_startup_resistance_ohms,
        'cold_lead_resistance_total_ohms': cold_lead_resistance_ohms,
        'total_resistance_ohms': total_resistance_ohms,
        'power_nominal_w': nominal['power_w'],
        'power_density_w_m': nominal['power_density_w_m'],
        'current_nominal_a': nominal['current_a'],
        'current_cold_start_a': high['current_a'],
        'low_voltage_power_density_w_m': low['power_density_w_m'],
        'high_voltage_power_density_w_m': high['power_density_w_m'],
        'cold_lead_voltage_drop_percent': nominal['cold_lead_voltage_drop_percent'],
        'max_sheath_temp_published_c': float(family.max_sheath_temp_c) if family.max_sheath_temp_c else None,
        'project_t_class_limit_c': t_class_limit_c,
        't_class_verdict': t_class_verdict,
        'selection_basis': {
            'rule_set': MI_SELECTION_RULE_SET,
            'phase': '1PH',
            'design_heat_loss_w_m': design_heat_loss_w_m,
            'low_voltage_v': low_voltage,
            'nominal_voltage_v': voltage,
            'high_voltage_v': high_voltage,
            'source_document': family.source_document,
            'max_cb_size': max_cb_size,
            'restricted_loading_factor': restricted_loading_factor,
            'allowed_current_per_circuit': allowed_current_per_circuit,
            'resistance_temperature_basis': resistance_basis,
        },
        'rejection_reasons': reasons,
    }
    return candidate, reasons


def _single_phase_power(voltage, heater_resistance_ohms, cold_lead_resistance_ohms, heated_length_m):
    total_resistance = heater_resistance_ohms + cold_lead_resistance_ohms
    current = voltage / total_resistance if total_resistance else 0.0
    heater_voltage = current * heater_resistance_ohms
    power = current ** 2 * heater_resistance_ohms
    cold_lead_drop = voltage - heater_voltage
    return {
        'current_a': current,
        'heater_voltage_v': heater_voltage,
        'power_w': power,
        'power_density_w_m': power / heated_length_m if heated_length_m else 0.0,
        'cold_lead_voltage_drop_percent': (cold_lead_drop / voltage * 100.0) if voltage else 0.0,
    }


def _heated_length_m(heat_loss, line):
    return _float_value(line, 'line_length') + float(heat_loss.get('tracer_adder') or 0.0)


def get_mi_heater_options(heat_loss, line, project_settings, families=None):
    """Evaluate single-phase MI heater candidates without touching SR flow.

    This function is intentionally side-effect-light: it mutates only MI-specific
    diagnostic keys on the passed `heat_loss` dict. Persistence and pipeline
    integration are deferred to the next pass.
    """
    try:
        if _value(line, 'phase', '1PH') != '1PH':
            _record_mi_rejection(
                heat_loss,
                'UNSUPPORTED_PHASE',
                'MI MVP supports single-phase heater sets only.',
                {'phase': _value(line, 'phase')},
            )
            return {}, []

        heated_length_m = _heated_length_m(heat_loss, line)
        all_families = _query_families(project_settings, families=families)
        vendor_families = [
            family for family in all_families
            if family.vendor == project_settings.get('vendor')
        ]
        validated_families = [family for family in vendor_families if family.is_validated]
        factors_by_alloy = _temperature_factor_lookup(validated_families)

        if not validated_families:
            _record_mi_rejection(
                heat_loss,
                'NO_VALIDATED_MI_CATALOGUE_DATA',
                'No validated MI catalogue rows are available for the selected vendor.',
                {'vendor': project_settings.get('vendor'), 'catalogue_rows': len(vendor_families)},
            )
            return {}, []

        family_rejections = []
        valid_candidates = []
        rejected_candidates = []
        for family in validated_families:
            family_reasons = _is_family_suitable(family, line, project_settings, heated_length_m)
            if family_reasons:
                family_rejections.append({
                    'family_id': family.id,
                    'family_name': family.family_name,
                    'reasons': family_reasons,
                })
                continue

            heaters = list(family.heaters.all())
            if not heaters:
                family_rejections.append({
                    'family_id': family.id,
                    'family_name': family.family_name,
                    'reasons': ['NO_HEATER_ROWS'],
                })
                continue

            for heater in heaters:
                cold_leads = list(heater.cold_lead_options.all())
                if not cold_leads:
                    rejected_candidates.append({
                        'family_id': family.id,
                        'heater_id': heater.id,
                        'reasons': ['NO_COLD_LEAD_OPTIONS'],
                    })
                    continue
                for cold_lead in cold_leads:
                    candidate, reasons = _evaluate_single_phase_candidate(
                        heat_loss,
                        line,
                        project_settings,
                        family,
                        heater,
                        cold_lead,
                        factors_by_alloy=factors_by_alloy,
                    )
                    if candidate is None:
                        rejected_candidates.append({
                            'family_id': family.id,
                            'heater_id': heater.id,
                            'cold_lead_option_id': cold_lead.id,
                            'reasons': reasons,
                        })
                    elif reasons:
                        rejected_candidates.append(candidate)
                    else:
                        valid_candidates.append(candidate)

        if not valid_candidates:
            logger.warning("No MI heaters satisfy catalogue and electrical limits, UID: %s", _value(line, 'uid'))
            _record_mi_rejection(
                heat_loss,
                'NO_MI_CANDIDATE_MATCH',
                'No validated MI heater option satisfied catalogue, electrical, cold-lead, and T-class checks.',
                {
                    'family_rejections': family_rejections,
                    'candidate_rejections': rejected_candidates[:20],
                    'rejected_candidate_count': len(rejected_candidates),
                },
            )
            return {}, []

        valid_candidates = sorted(
            valid_candidates,
            key=lambda item: (
                abs(item['low_voltage_power_density_w_m'] - item['selection_basis']['design_heat_loss_w_m']),
                item['high_voltage_power_density_w_m'],
                item['current_cold_start_a'],
            ),
        )
        _record_mi_success(heat_loss)
        return valid_candidates[0], valid_candidates[1:]
    except Exception as exc:
        logger.exception("Error selecting MI heater for UID %s", _value(line, 'uid'))
        _record_mi_rejection(
            heat_loss,
            'MI_SELECTION_ERROR',
            'Unexpected error while selecting MI heater.',
            {'error': str(exc)},
        )
        return {}, []
