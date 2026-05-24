from decimal import Decimal
from time import perf_counter

import pandas as pd
from django.conf import settings
from django.db import transaction
from django.db.models import FloatField
from django.db.models.functions import Cast

import logging

from .models import (
    AlternateTracer,
    BOQ,
    ElecEHT_ASMEB36,
    ElecEHT_ThermalConductivity,
    ElecEHT_Vendor,
    HeatLoss,
    HeatTracingInput,
    PowerDistribution,
    PowerDistributionBranch,
    ProcessLineCalculation,
    ProjectData,
    SelectedMIHeater,
    SelectedTracer,
)


logger = logging.getLogger(__name__)


def emit_timing(message, *args):
    if not getattr(settings, "EHT_TIMING_LOGS", False):
        return
    if args:
        logger.warning(message, *args)
        try:
            print(message % args, flush=True)
        except Exception:
            pass
        return
    print(message, flush=True)
    logger.warning(message)

BOQ_ITEM_METADATA = {
    'MCB': {'description': 'Miniature Circuit Breaker', 'unit': 'EA'},
    'JB3PH': {'description': '3-Phase Junction Box', 'unit': 'EA'},
    'JB1PH': {'description': '1-Phase Junction Box', 'unit': 'EA'},
    'CCMCB-3PHJB': {'description': 'Cable from MCB to 3-Phase Junction Box', 'unit': 'm'},
    'CC3PHJB-1PHJB': {'description': 'Cable from 3-Phase Junction Box to 1-Phase Junction Box', 'unit': 'm'},
    'TRACER': {'description': 'Ordered SR heating tracer length (incl. termination allowance)', 'unit': 'm'},
    'ENDTRM': {'description': 'End Termination Kit', 'unit': 'EA'},
    'ISOLATOR_1PH': {'description': '1-Phase Isolator', 'unit': 'EA'},
    'ISOLATOR_3PH': {'description': '3-Phase Isolator', 'unit': 'EA'},
    'ISOLATOR': {'description': 'Isolator', 'unit': 'EA'},
    'RTD': {'description': 'RTD', 'unit': 'EA'},
    'THERMOSTAT': {'description': 'Thermostat', 'unit': 'EA'},
    'Caution_Label': {'description': 'Caution Label', 'unit': 'EA'},
    'Aluminium_Adhesive_Tape': {'description': 'Aluminium Adhesive Tape', 'unit': 'm'},
    'Pipe_Strap': {'description': 'Pipe Strap', 'unit': 'EA'},
    'MI_HEATER_SET': {'description': 'MI factory heating cable set', 'unit': 'EA'},
    'MI_HEATED_LENGTH': {'description': 'MI heated cable length', 'unit': 'm'},
    'MI_COLD_LEAD_LENGTH': {'description': 'MI cold lead length', 'unit': 'm'},
}

TRACER_FIELD_MAPPING = {
    'A_Coeff': 'a_coeff',
    'B_Coeff': 'b_coeff',
    'C_Coeff': 'c_coeff',
    'Ohm_per_km': 'ohm_per_km',
    'Power_Output': 'power_output',
    'Power_at_Startup_T': 'power_at_startup_t',
    'Res_corrFactor_Mica': 'res_corrFactor_mica',
    'Spiral_Factor': 'spiral_factor',
    'Tracer_Family': 'tracer_family',
    'Tracer_Length': 'tracer_length',
    'Tracer_With_Margin': 'tracer_with_margin',
    'V_UID': 'v_uid',
    'Voltage_Correction_Factor': 'voltage_correction_factor',
    'Voltage_Float': 'voltage_float',
}


def _to_builtin(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            return value
    return value


def _normalize_payload(value):
    if isinstance(value, dict):
        return {key: _normalize_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_payload(item) for item in value]
    return _to_builtin(value)


def _transform_tracer_item(item):
    normalized_item = _normalize_payload(item)
    return {
        model_field: normalized_item[source_field]
        for source_field, model_field in TRACER_FIELD_MAPPING.items()
        if source_field in normalized_item
    }


def _transform_mi_heater_item(item):
    normalized_item = _normalize_payload(item)
    rejection_reasons = normalized_item.get('selection_rejection_reasons')
    if rejection_reasons is None:
        rejection_reasons = normalized_item.get('mi_selection_rejection_reasons', [])
    selection_status = normalized_item.get('selection_status') or normalized_item.get('mi_selection_status', '')
    if not selection_status:
        selection_status = 'selected' if normalized_item.get('heater_id') else ('rejected' if rejection_reasons else '')

    # The selector returns catalogue primary keys plus calculated snapshot values.
    # Storing both keeps future reports stable even if catalogue rows are corrected.
    return {
        'heater_id': normalized_item.get('heater_id') or None,
        'cold_lead_option_id': normalized_item.get('cold_lead_option_id') or None,
        'selection_status': selection_status,
        'selection_rejection_reasons': rejection_reasons,
        'heated_length_m': normalized_item.get('heated_length_m', 0),
        'cold_lead_option_code': normalized_item.get('cold_lead_option_code', ''),
        'cold_lead_length_m': normalized_item.get('cold_lead_length_m', 0),
        'heater_resistance_ohms': normalized_item.get('heater_resistance_ohms', 0),
        'cold_lead_resistance_total_ohms': normalized_item.get('cold_lead_resistance_total_ohms', 0),
        'power_nominal_w': normalized_item.get('power_nominal_w', 0),
        'power_density_w_m': normalized_item.get('power_density_w_m', 0),
        'current_nominal_a': normalized_item.get('current_nominal_a', 0),
        'current_cold_start_a': normalized_item.get('current_cold_start_a', 0),
        'max_sheath_temp_published_c': normalized_item.get('max_sheath_temp_published_c'),
        'project_t_class_limit_c': normalized_item.get('project_t_class_limit_c', 0),
        't_class_verdict': normalized_item.get('t_class_verdict', 'review'),
        'selection_basis': normalized_item.get('selection_basis', {}),
    }


def _index_by_uid(rows):
    indexed_rows = {}
    for row in rows:
        if 'uid' in row:
            indexed_rows[str(row['uid'])] = row
    return indexed_rows


def _get_boq_metadata(item_code):
    return BOQ_ITEM_METADATA.get(item_code, {'description': item_code, 'unit': 'EA'})



def fetch_asme_b36_table():
    """Fetch ASME B36 table data from the database and return as a DataFrame."""
    data = ElecEHT_ASMEB36.objects.values('Nominal_Pipe_Size', 'Outside_Diameter_mm')
    return pd.DataFrame.from_records(data)


def fetch_thermal_conductivity_data():
    """Fetch thermal conductivity data from the database and return as a DataFrame."""
    data = ElecEHT_ThermalConductivity.objects.values('Ins_Mat_Type', 'K_factor_A', 'K_factor_B', 'K_factor_C')
    return pd.DataFrame.from_records(data)


def fetch_process_lines(project_id):
    """Fetch confirmed process lines for the given project ID and return as a DataFrame."""
    data = HeatTracingInput.objects.filter(proj_id=project_id, status='confirmed').values()
    return pd.DataFrame(data)


def fetch_vendor_data(selected_vendor, project_voltage):
    """Fetch selected vendor catalogue data and return as a DataFrame.

    Voltage compatibility is handled in the SR selection layer because some
    catalogues store 230 V nominal rows that are valid candidates for 240 V
    projects after voltage correction.
    """
    data = ElecEHT_Vendor.objects.filter(
        Vendor__iexact=selected_vendor,
    ).annotate(
        Voltage_Float=Cast('Voltage', FloatField())  # Convert to float at DB level
    ).values(
        'V_UID', 'Voltage_Float', 'A_Coeff', 'B_Coeff', 'C_Coeff',
        'Power_at_Startup_T', 'Ohm_per_km', 'Res_corrFactor_Mica',
        'Tracer_Family', 'Tracer_Model', 'Tracer_Cat_No', 'Zone',
        'Gas_Group', 'T_Rating', 'Maint_T', 'Max_Op_T',
        'Min_Installation_T', 'Max_Exp_T_On', 'Max_Exp_T_Off',
    ).distinct()
    return pd.DataFrame(data)


def fetch_project_data(project_id):
    """Fetch project-specific settings from the database."""
    project_data = ProjectData.objects.get(proj_id=project_id)
    return {
        "id": project_data.id,
        "proj_id": project_data.proj_id,
        "min_amb_t": float(project_data.min_amb_t),
        "max_amb_t": float(project_data.max_amb_t),
        "startup_t": float(project_data.startup_t),
        "area_class": project_data.area_class,
        "temp_class": project_data.temp_class,
        "voltage": float(project_data.voltage),
        "max_cb_size": float(project_data.max_cb_size),
        "restrict_cb_current": float(project_data.restrict_cb_current),
        "vendor": project_data.vendor,
        "spiral_wrap_allowed": project_data.spiral_wrap_allowed,
        "spiral_factor": float(project_data.spiral_factor),
        "margin_on_tracer_lengths": float(project_data.margin_on_tracer_lengths),
        "voltage_var_factor": float(project_data.voltage_var_factor),
        "res_tol": float(project_data.res_tol),
        "termination_margin": float(project_data.termination_margin),
        "heat_loss_sf": float(project_data.heat_loss_sf),
        "heat_loss_method": project_data.heat_loss_method,
        "rtd_thrm": project_data.rtd_thrm,
        "wind_speed": float(project_data.wind_speed),
        "caution_label_interval": float(project_data.caution_label_interval),
        "isolator_location": project_data.isolator_location,
        "ckt_ln": float(project_data.ckt_ln),
        "loop_ln": float(project_data.loop_ln),
        "allowablevdrop": float(project_data.allowablevdrop),
    }


@transaction.atomic
def clear_project_workspace_data(project_id):
    """Delete all uploaded inputs and derived outputs for a project in one clean reset."""
    clear_started = perf_counter()
    if not project_id:
        return {
            'project_id': project_id,
            'input_lines': 0,
            'boq_items': 0,
            'derived_rows': 0,
        }

    project_line_ids = list(HeatTracingInput.objects.filter(proj_id=project_id).values_list('uid', flat=True))
    project_line_uid_strings = [str(uid) for uid in project_line_ids]
    input_lines = len(project_line_ids)
    boq_items = BOQ.objects.filter(project_id=project_id).count()
    derived_rows = 0

    if project_line_ids:
        derived_rows += HeatLoss.objects.filter(line_id__in=project_line_ids).count()
        derived_rows += SelectedTracer.objects.filter(line_id__in=project_line_ids).count()
        derived_rows += SelectedMIHeater.objects.filter(line_id__in=project_line_ids).count()
        derived_rows += AlternateTracer.objects.filter(line_id__in=project_line_ids).count()
        derived_rows += PowerDistribution.objects.filter(line_id__in=project_line_ids).count()
        derived_rows += PowerDistributionBranch.objects.filter(distribution_id__in=project_line_uid_strings).count()
        derived_rows += ProcessLineCalculation.objects.filter(line_id__in=project_line_ids).count()
        derived_rows += BOQ.objects.filter(line_id__in=project_line_ids).count()

    # Delete consolidated BOQ rows explicitly. Line-scoped BOQ rows are removed via input cascade.
    consolidated_boq_rows = BOQ.objects.filter(project_id=project_id, line__isnull=True).delete()[0]
    HeatTracingInput.objects.filter(proj_id=project_id).delete()

    orphan_rows = 0
    if project_line_uid_strings:
        # Defensive cleanup for any legacy/orphaned rows keyed only by stored UID text.
        orphan_rows += HeatLoss.objects.filter(uid__in=project_line_uid_strings).delete()[0]
        orphan_rows += PowerDistribution.objects.filter(uid__in=project_line_uid_strings).delete()[0]
        orphan_rows += ProcessLineCalculation.objects.filter(uid__in=project_line_uid_strings).delete()[0]

    total_duration = perf_counter() - clear_started
    emit_timing(
        "EHT timing | clear_project_workspace_data | project=%s | input_lines=%s | boq_items=%s | derived_rows=%s | consolidated_boq=%s | orphan_cleanup=%s | total=%.3fs",
        project_id,
        input_lines,
        boq_items,
        derived_rows,
        consolidated_boq_rows,
        orphan_rows,
        total_duration,
    )

    logger.info(
        "Project ID: %s - Workspace reset complete. Deleted %s input line(s), %s BOQ row(s), %s derived row(s).",
        project_id,
        input_lines,
        boq_items,
        derived_rows + orphan_rows,
    )
    return {
        'project_id': project_id,
        'input_lines': input_lines,
        'boq_items': boq_items,
        'derived_rows': derived_rows + orphan_rows,
    }


# Store calculated data in the database

# Function to store aggregated_results into the database
@transaction.atomic
def store_calculated_results(project_id, aggregated_results):
    project = ProjectData.objects.get(proj_id=project_id)
    project_lines = {
        str(line.uid): line
        for line in HeatTracingInput.objects.filter(proj_id=project_id)
    }
    project_line_ids = [line.uid for line in project_lines.values()]

    HeatLoss.objects.filter(line_id__in=project_line_ids).delete()
    SelectedTracer.objects.filter(line_id__in=project_line_ids).delete()
    SelectedMIHeater.objects.filter(line_id__in=project_line_ids).delete()
    AlternateTracer.objects.filter(line_id__in=project_line_ids).delete()
    PowerDistribution.objects.filter(line_id__in=project_line_ids).delete()
    ProcessLineCalculation.objects.filter(line_id__in=project_line_ids).delete()
    BOQ.objects.filter(project=project).delete()

    heat_loss_lookup = _index_by_uid(aggregated_results.get('heat_loss', []))
    selected_tracer_lookup = _index_by_uid(aggregated_results.get('selected_tracers', []))
    alternative_tracers = aggregated_results.get('alternative_tracers')
    if alternative_tracers is None:
        alternative_tracers = aggregated_results.get('alternate_tracers', [])

    heat_loss_rows = []
    for item in aggregated_results.get('heat_loss', []):
        normalized_item = _normalize_payload(item)
        line = project_lines.get(str(normalized_item['uid']))
        if not line:
            continue
        design_heat_loss = normalized_item.get('design_heat_loss', normalized_item['heat_loss'])
        heat_loss_rows.append(HeatLoss(
            uid=str(normalized_item['uid']),
            line=line,
            heat_loss=design_heat_loss,
            base_heat_loss=normalized_item.get('base_heat_loss', design_heat_loss),
            design_heat_loss=design_heat_loss,
            heat_loss_sf=normalized_item.get('heat_loss_sf', 1),
            pipe_size_mm=normalized_item.get('pipe_size_mm', 0),
            conductivity=normalized_item.get('conductivity', 0),
            conductivity_basis=normalized_item.get('conductivity_basis', {}),
            wind_correction=normalized_item.get('wind_correction', 1),
            accessory_adders=normalized_item.get('accessory_adders', {}),
            selection_status=normalized_item.get('selection_status', ''),
            selection_rejection_reasons=normalized_item.get('selection_rejection_reasons', []),
            tracer_adder=normalized_item['tracer_adder'],
        ))
    if heat_loss_rows:
        HeatLoss.objects.bulk_create(heat_loss_rows, batch_size=500)

    selected_tracer_rows = []
    for item in aggregated_results.get('selected_tracers', []):
        normalized_item = _normalize_payload(item)
        line = project_lines.get(str(normalized_item['uid']))
        if not line:
            continue
        transformed_item = _transform_tracer_item(normalized_item)
        selected_tracer_rows.append(SelectedTracer(line=line, **transformed_item))
    if selected_tracer_rows:
        SelectedTracer.objects.bulk_create(selected_tracer_rows, batch_size=500)

    selected_mi_heater_rows = []
    for item in aggregated_results.get('selected_mi_heaters', []):
        normalized_item = _normalize_payload(item)
        line = project_lines.get(str(normalized_item['uid']))
        if not line:
            continue
        selected_mi_heater_rows.append(SelectedMIHeater(line=line, **_transform_mi_heater_item(normalized_item)))
    if selected_mi_heater_rows:
        SelectedMIHeater.objects.bulk_create(selected_mi_heater_rows, batch_size=500)
    
    alternate_rank_by_line = {}
    alternate_tracer_rows = []
    for item in alternative_tracers:
        normalized_item = _normalize_payload(item)
        line_uid = str(normalized_item['uid'])
        line = project_lines.get(line_uid)
        if not line:
            continue
        alternate_rank_by_line[line_uid] = alternate_rank_by_line.get(line_uid, 0) + 1
        transformed_item = _transform_tracer_item(normalized_item)
        alternate_tracer_rows.append(AlternateTracer(
            line=line,
            option_rank=alternate_rank_by_line[line_uid],
            **transformed_item,
        ))
    if alternate_tracer_rows:
        AlternateTracer.objects.bulk_create(alternate_tracer_rows, batch_size=500)
    
    power_distribution_rows = []
    power_distribution_branch_rows = []
    for item in aggregated_results.get('power_distribution', []):
        normalized_item = _normalize_payload(item)
        distribution_uid = str(normalized_item['uid'])
        line = project_lines.get(distribution_uid)
        if not line:
            continue
        power_distribution_rows.append(PowerDistribution(
            uid=distribution_uid,
            line=line,
            total_circuits=normalized_item['total_circuits'],
        ))
        for branch_index, branch in enumerate(normalized_item.get('branches', []), start=1):
            power_distribution_branch_rows.append(PowerDistributionBranch(
                distribution_id=distribution_uid,
                branch_index=branch_index,
                branch_type=branch['type'],
                circuit_count=branch['circuit_count'],
                connected_to=branch['connected_to'],
                cable_length_db_to_jb=branch['cable_length_db_to_jb'] or 0,
                cable_length_jb_to_jb=branch.get('cable_length_jb_to_jb'),
                tagged_components=branch.get('tagged_components', {}),
            ))
    if power_distribution_rows:
        PowerDistribution.objects.bulk_create(power_distribution_rows, batch_size=500)
    if power_distribution_branch_rows:
        PowerDistributionBranch.objects.bulk_create(power_distribution_branch_rows, batch_size=500)
    
    boq_rows = []
    for line_uid, boq_items in aggregated_results.get('boq_per_line', {}).items():
        line = project_lines.get(str(line_uid))
        if not line:
            continue
        for item_code, quantity in _normalize_payload(boq_items).items():
            metadata = _get_boq_metadata(item_code)
            boq_rows.append(BOQ(
                uid=str(line.uid),
                project=project,
                line=line,
                scope='line',
                item_code=item_code,
                item_description=metadata['description'],
                quantity=quantity,
                unit=metadata['unit'],
            ))

    for item_code, quantity in _normalize_payload(aggregated_results.get('consolidated_boq', {})).items():
        metadata = _get_boq_metadata(item_code)
        boq_rows.append(BOQ(
            uid=f'{project_id}:consolidated',
            project=project,
            line=None,
            scope='consolidated',
            item_code=item_code,
            item_description=metadata['description'],
            quantity=quantity,
            unit=metadata['unit'],
        ))
    if boq_rows:
        BOQ.objects.bulk_create(boq_rows, batch_size=500)
    
    process_line_calc_rows = []
    for item in aggregated_results.get('tracer_power_param', []):
        normalized_item = _normalize_payload(item)
        uid = str(normalized_item['uid'])
        line = project_lines.get(uid)
        if not line:
            continue
        heat_loss = heat_loss_lookup.get(uid, {})
        selected_tracer = selected_tracer_lookup.get(uid, {})
        selected_tracer_name = selected_tracer.get('V_UID') or normalized_item.get('selected_tracer', '')
        spiral_factor = selected_tracer.get('Spiral_Factor', normalized_item.get('spiral_factor', 0))
        process_line_calc_rows.append(ProcessLineCalculation(
            uid=uid,
            line=line,
            line_size=_to_builtin(line.line_size),
            line_length=_to_builtin(line.line_length),
            operating_temp=_to_builtin(line.oper_temp),
            heat_loss=heat_loss.get('heat_loss', 0),
            selected_tracer=selected_tracer_name,
            breaker_size=normalized_item.get('breaker_size', 0),
            total_circuits=normalized_item.get('no_of_circuits', 0),
            starting_current=normalized_item.get('max_current', 0),
            operating_current=normalized_item.get('operating_current', 0),
            total_power_consumption=normalized_item.get('operating_load', 0),
            total_tracer_length=normalized_item.get('total_tracer_length', 0),
            pipe_size_mm=normalized_item.get('pipe_size_mm', 0),
            spiral_factor=spiral_factor,
            remarks=normalized_item.get('calculation_basis', ''),
        ))
    if process_line_calc_rows:
        ProcessLineCalculation.objects.bulk_create(process_line_calc_rows, batch_size=500)
    
    return True



# TODO : make sure the temp folder is deleted after the file is 
# downloaded and file pointer is reset to the start of the file

# Function to export all reports in an Excel file with multiple sheets
def export_full_report_excel(request):
    boq_data = list(BOQ.objects.values('project_id', 'scope', 'line_id', 'item_code', 'item_description', 'quantity', 'unit', 'cost'))
    calculation_data = list(ProcessLineCalculation.objects.values(
        'line_id',
        'line_size',
        'line_length',
        'operating_temp',
        'heat_loss',
        'selected_tracer',
        'breaker_size',
        'total_circuits',
        'starting_current',
        'operating_current',
        'total_power_consumption',
        'total_tracer_length',
        'pipe_size_mm',
        'spiral_factor',
        'remarks',
    ))
    cable_schedule_data = list(PowerDistributionBranch.objects.values(
        'distribution_id',
        'branch_index',
        'branch_type',
        'circuit_count',
        'connected_to',
        'cable_length_db_to_jb',
        'cable_length_jb_to_jb',
        'tagged_components',
    ))
    
    with pd.ExcelWriter('/tmp/full_report.xlsx', engine='xlsxwriter') as writer:
        if boq_data:
            pd.DataFrame(boq_data).to_excel(writer, sheet_name="BOQ Summary", index=False)
        if calculation_data:
            pd.DataFrame(calculation_data).to_excel(writer, sheet_name="Calculation Results", index=False)
        if cable_schedule_data:
            pd.DataFrame(cable_schedule_data).to_excel(writer, sheet_name="Cable Schedule", index=False)
    
    with open('/tmp/full_report.xlsx', 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="full_report.xlsx"'
    
    return response
