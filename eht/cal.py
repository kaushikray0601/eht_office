import logging

import pandas as pd

from eht.calculations.boq import compute_bill_of_quantities
from eht.calculations.heat_loss import calculate_heat_loss
from eht.calculations.mi_selection import get_mi_heater_options
from eht.calculations.power_distribution import compute_mi_power_params, compute_power_distribution, compute_power_params
from eht.calculations.tag_management import ProjectTagFactory
from eht.calculations.tracer_selection import get_tracer_options
from eht.models import MICableFamily


logger = logging.getLogger(__name__)


def _ensure_process_lines_df(process_lines):
    if isinstance(process_lines, pd.DataFrame):
        return process_lines
    return pd.DataFrame(process_lines)


def _sort_process_lines_df(process_lines_df):
    sort_columns = [column for column in ['xlid', 'line_id', 'uid'] if column in process_lines_df.columns]
    if not sort_columns:
        return process_lines_df
    return process_lines_df.sort_values(by=sort_columns, kind='stable', na_position='last')


SR_TEMPERATURE_LIMIT_COLUMNS = [
    ('maint_temp', 'Maint_T'),
    ('oper_temp', 'Max_Op_T'),
    ('design_temp', 'Max_Exp_T_On'),
]


def _is_self_regulating_row(value):
    normalized = ''.join(ch for ch in str(value or '').upper() if ch.isalnum())
    return normalized in {'SR', 'SELFREGULATING'} or 'SELFREGULATING' in normalized


def _sr_temperature_limit_exceeded(line, vendor_data):
    """Return true only when line temperatures exceed published SR catalogue limits."""
    if vendor_data is None or vendor_data.empty:
        return False

    sr_rows = vendor_data.copy()
    if 'Tracer_Family' in sr_rows.columns:
        sr_rows = sr_rows[sr_rows['Tracer_Family'].map(_is_self_regulating_row)]
    if sr_rows.empty:
        return False

    for line_field, catalogue_field in SR_TEMPERATURE_LIMIT_COLUMNS:
        if catalogue_field not in sr_rows.columns:
            continue
        catalogue_limit = pd.to_numeric(sr_rows[catalogue_field], errors='coerce').max()
        if pd.isna(catalogue_limit):
            continue
        line_temperature = float(line.get(line_field) or 0.0)
        if line_temperature > float(catalogue_limit):
            return True
    return False


def _has_validated_mi_catalogue(project_settings):
    """Avoid noisy MI alternate probes when no reviewed catalogue exists yet."""
    try:
        return MICableFamily.objects.filter(
            vendor=project_settings.get('vendor'),
            is_validated=True,
        ).exists()
    except Exception:
        # Some pure calculation tests run without DB access. In that context the
        # autonomous SR path must remain pure and simply skip optional MI alternates.
        return False


def _mi_rejection_result(line, heat_loss, selection_mode):
    """Build a persistable MI diagnostic row when no heater can be selected."""
    return {
        'uid': line['uid'],
        'mi_selection_status': heat_loss.get('mi_selection_status', 'rejected'),
        'mi_selection_rejection_reasons': heat_loss.get('mi_selection_rejection_reasons', []),
        'selection_basis': {
            'rule_set': 'MI_SELECTION_REJECTION_RECORD_V1',
            'selection_mode': selection_mode,
        },
    }


def _mi_selection_result(line, heat_loss, project_settings, selection_mode, selection_status):
    """Evaluate MI once and return a persistable selection row when one is available."""
    if selection_mode == 'available_alternative' and not _has_validated_mi_catalogue(project_settings):
        return None

    mi_heat_loss = {**heat_loss}
    selected_mi_heater, _alternative_mi_heaters = get_mi_heater_options(
        mi_heat_loss,
        line,
        project_settings,
    )
    if not selected_mi_heater:
        if selection_mode == 'automatic_temperature_fallback':
            return _mi_rejection_result(line, mi_heat_loss, selection_mode)
        return None

    selection_basis = {
        **selected_mi_heater.get("selection_basis", {}),
        "selection_mode": selection_mode,
    }
    return {
        **selected_mi_heater,
        "uid": line["uid"],
        "selection_status": selection_status,
        "selection_rejection_reasons": [],
        "selection_basis": selection_basis,
    }


def _append_mi_electrical_outputs(aggregated_results, line, project_settings, asme_b36_table, tag_factory, mi_result):
    """Persist first-pass MI downstream outputs for a selected single heater set."""
    power_params = compute_mi_power_params(line, project_settings, asme_b36_table, mi_result)
    if not power_params:
        return

    power_distribution = compute_power_distribution(power_params, project_settings, tag_factory=tag_factory)
    aggregated_results["power_distribution"].append(power_distribution)

    boq = compute_bill_of_quantities(
        power_distribution=power_distribution,
        project_settings=project_settings,
        tracer_qty=0,
        line_length=line["line_length"],
        pipe_size_mm=power_params["pipe_size_mm"],
        is_process_temp_controlled=line["service_type"] == "EP",
    )
    heater_set_count = int(mi_result.get("heater_set_count") or power_params.get("heater_set_count") or 1)
    boq["MI_HEATER_SET"] = heater_set_count
    boq["MI_HEATED_LENGTH"] = power_params.get("total_heated_tracer_length", power_params["heated_tracer_length"])
    boq["MI_COLD_LEAD_LENGTH"] = float(mi_result.get("cold_lead_length_m") or 0.0) * heater_set_count

    line_uid = line["uid"]
    aggregated_results["boq_per_line"][line_uid] = boq
    aggregated_results["tracer_power_param"].append(power_params)

    for item, count in boq.items():
        aggregated_results["consolidated_boq"].setdefault(item, 0)
        aggregated_results["consolidated_boq"][item] += count


def orchestrate_calculations(process_lines, vendor_data, project_settings, asme_b36_table, thermal_cond_data):
    """Run the active heat-tracing pipeline and return the aggregated payload."""
    aggregated_results = {
        "heat_loss": [],
        "selected_tracers": [],
        "selected_mi_heaters": [],
        "alternative_tracers": [],
        "power_distribution": [],
        "boq_per_line": {},
        "consolidated_boq": {},
        "tracer_power_param": [],
    }
    process_lines_df = _ensure_process_lines_df(process_lines)
    if process_lines_df.empty:
        return aggregated_results
    process_lines_df = _sort_process_lines_df(process_lines_df)
    tag_factory = ProjectTagFactory(project_settings.get('proj_id'))

    for _, line in process_lines_df.iterrows():
        try:
            heat_loss = calculate_heat_loss(line, project_settings, asme_b36_table, thermal_cond_data)
            if not heat_loss:
                continue
            aggregated_results["heat_loss"].append(heat_loss)

            selected_tracer, alternative_tracers = get_tracer_options(
                heat_loss,
                line,
                project_settings,
                vendor_data,
            )
            if not selected_tracer:
                if _sr_temperature_limit_exceeded(line, vendor_data):
                    mi_result = _mi_selection_result(
                        line,
                        heat_loss,
                        project_settings,
                        selection_mode='automatic_temperature_fallback',
                        selection_status='selected',
                    )
                    if mi_result:
                        aggregated_results["selected_mi_heaters"].append(mi_result)
                        if mi_result.get("selection_status") == "selected":
                            _append_mi_electrical_outputs(
                                aggregated_results,
                                line,
                                project_settings,
                                asme_b36_table,
                                tag_factory,
                                mi_result,
                            )
                continue

            selected_tracer = {**selected_tracer, "uid": line["uid"]}
            power_params = compute_power_params(line, project_settings, asme_b36_table, selected_tracer)
            if not power_params:
                heat_loss['selection_status'] = 'rejected'
                heat_loss['selection_rejection_reasons'] = [{
                    'rule_set': 'SR_POWER_PARAMETER_SAFETY_GUARD_V1',
                    'code': 'SR_POWER_PARAMETER_CALCULATION_FAILED',
                    'message': (
                        'SR tracer was not carried forward because downstream '
                        'power-parameter calculation failed. Review SR catalogue '
                        'power coefficients and rerun the calculation.'
                    ),
                    'details': {'selected_tracer': selected_tracer.get('V_UID', '')},
                }]
                continue
            aggregated_results["selected_tracers"].append(selected_tracer)
            mi_alternative = _mi_selection_result(
                line,
                heat_loss,
                project_settings,
                selection_mode='available_alternative',
                selection_status='available_alternative',
            )
            if mi_alternative:
                aggregated_results["selected_mi_heaters"].append(mi_alternative)

            if isinstance(alternative_tracers, list):
                aggregated_results["alternative_tracers"].extend(
                    {**tracer, "uid": line["uid"]}
                    for tracer in alternative_tracers
                )

            power_distribution = compute_power_distribution(power_params, project_settings, tag_factory=tag_factory)
            aggregated_results["power_distribution"].append(power_distribution)

            boq = compute_bill_of_quantities(
                power_distribution=power_distribution,
                project_settings=project_settings,
                tracer_qty=power_params["total_tracer_length"],
                line_length=line["line_length"],
                pipe_size_mm=power_params["pipe_size_mm"],
                is_process_temp_controlled=line["service_type"] == "EP",
            )
            line_uid = line["uid"]
            aggregated_results["boq_per_line"][line_uid] = boq
            aggregated_results["tracer_power_param"].append(power_params)

            for item, count in boq.items():
                aggregated_results["consolidated_boq"].setdefault(item, 0)
                aggregated_results["consolidated_boq"][item] += count

        except Exception:
            logger.exception("Error processing line UID %s", line.get("uid"))

    return aggregated_results
