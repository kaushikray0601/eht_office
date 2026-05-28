"""Readiness checks for enabling MI catalogue families.

The selection engine refuses unvalidated MI families. These checks define the
minimum catalogue completeness required before a family can be marked usable for
MVP calculations, while keeping known engineering refinements visible as
warnings for later passes.
"""


def _positive(value):
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def _non_negative(value):
    try:
        return float(value) >= 0
    except (TypeError, ValueError):
        return False


def evaluate_mi_family_readiness(family):
    """Return blockers/warnings for one MI family validation decision."""
    blockers = []
    warnings = []

    if not family.source_document:
        blockers.append('SOURCE_DOCUMENT_MISSING')

    for field_name in [
        'max_voltage',
        'max_sheath_temp_c',
        'max_maintain_temp_c',
        'max_exposure_temp_c',
        'max_watt_density_w_m',
        'max_circuit_length_m',
    ]:
        if not _positive(getattr(family, field_name, None)):
            blockers.append(f'{field_name.upper()}_MISSING_OR_NON_POSITIVE')

    if not _non_negative(family.min_circuit_length_m):
        blockers.append('MIN_CIRCUIT_LENGTH_NEGATIVE_OR_MISSING')
    if _positive(family.max_circuit_length_m) and float(family.max_circuit_length_m) < float(family.min_circuit_length_m or 0):
        blockers.append('MAX_CIRCUIT_LENGTH_BELOW_MINIMUM')

    heaters = list(family.heaters.all())
    if not heaters:
        blockers.append('NO_HEATER_ROWS')

    heater_count = len(heaters)
    cold_lead_count = 0
    for heater in heaters:
        heater_label = heater.part_number or f'heater#{heater.pk}'
        if not _positive(heater.resistance_ohms_m):
            blockers.append(f'{heater_label}:RESISTANCE_MISSING_OR_NON_POSITIVE')
        if not _positive(heater.max_current_a):
            blockers.append(f'{heater_label}:MAX_CURRENT_MISSING_OR_NON_POSITIVE')
        if not heater.conductor_material:
            blockers.append(f'{heater_label}:CONDUCTOR_MATERIAL_MISSING')
        if not _positive(heater.tcr_per_degree_c):
            blockers.append(f'{heater_label}:TCR_MISSING_OR_NON_POSITIVE')
        if not _positive(heater.cold_lead_resistance_ohms_m):
            warnings.append(f'{heater_label}:COLD_LEAD_RESISTANCE_NOT_AVAILABLE')
        if not _positive(heater.cold_lead_max_ampacity_a):
            warnings.append(f'{heater_label}:COLD_LEAD_AMPACITY_NOT_AVAILABLE')

        cold_leads = list(heater.cold_lead_options.all())
        cold_lead_count += len(cold_leads)
        if not cold_leads:
            blockers.append(f'{heater_label}:NO_COLD_LEAD_OPTIONS')
        for cold_lead in cold_leads:
            option_label = cold_lead.option_code or f'coldlead#{cold_lead.pk}'
            if not _positive(cold_lead.length_m):
                blockers.append(f'{heater_label}:{option_label}:COLD_LEAD_LENGTH_MISSING_OR_NON_POSITIVE')

    if not family.temp_class_rating:
        warnings.append('T_CLASS_REMAINS_DESIGN_REVIEW_ITEM')
    if not family.gas_group:
        warnings.append('GAS_GROUP_NOT_DECLARED')
    if not family.zone_approval:
        warnings.append('ZONE_APPROVAL_NOT_DECLARED')

    return {
        'family': family,
        'ready': not blockers,
        'blockers': blockers,
        'warnings': warnings,
        'heater_count': heater_count,
        'cold_lead_count': cold_lead_count,
    }


def summarize_mi_catalogue_readiness(families):
    """Evaluate a family iterable and return list plus aggregate counts."""
    reports = [evaluate_mi_family_readiness(family) for family in families]
    return {
        'reports': reports,
        'family_count': len(reports),
        'ready_count': sum(1 for report in reports if report['ready']),
        'blocked_count': sum(1 for report in reports if not report['ready']),
        'validated_count': sum(1 for report in reports if report['family'].is_validated),
    }
