import json
import logging
import os
from collections import Counter
from io import BytesIO
from time import perf_counter

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.timezone import now, timedelta

from .cable_management import (
    attach_cable_override_summaries,
    find_cable_node,
    reset_cable_override,
    save_cable_override,
)
from .cable_schedule import (
    CABLE_SCHEDULE_EXPORT_HEADERS,
    build_cable_schedule_workspace_data,
    cable_schedule_export_rows,
)
from .forms import ProjectDataForm
from .data_service import clear_project_workspace_data
from .models import (
    AlternateTracer,
    BOQ,
    DEFAULT_PROJECT_ID,
    HeatTracingInput,
    ManagedProject,
    PowerDistributionBranch,
    ProcessLineCalculation,
    ProjectData,
    SLDTopologyEdit,
    TracerSelectionOverride,
    UserAttempt,
    is_default_project_id,
)
from .pipeline import run_project_calculations
from .sanatize_input import sanitize_file
from .sld_layout import get_project_sld_layout, reset_project_sld_layout, save_project_sld_layout
from .sld_payload import build_project_sld_payload
from .sld_pdf import build_sld_pdf
from .sld_topology import apply_active_cable_schedule_rows, apply_active_summary_overrides
from .sld_topology_workflows import (
    apply_attach_to_jb,
    apply_combine_feeders,
    apply_downstream_jb,
    apply_scoped_reset,
    apply_split_circuits,
    preview_attach_to_jb,
    preview_combine_feeders,
    preview_downstream_jb,
    preview_split_circuits,
)
from .tracer_management import find_tracer_node, reset_tracer_override, save_tracer_override
from .sld_validation import validate_project_sld_payload

COOLDOWN_PERIOD_MINUTES = 30
MAX_FAILED_ATTEMPTS = 3

logger = logging.getLogger(__name__)

PROJECT_DATA_TEMPLATE_FIELDS = [
    'min_amb_t',
    'max_amb_t',
    'startup_t',
    'area_class',
    'temp_class',
    'voltage',
    'max_cb_size',
    'restrict_cb_current',
    'vendor',
    'spiral_wrap_allowed',
    'spiral_factor',
    'valve_factor',
    'flange_factor',
    'support_factor',
    'margin_on_tracer_lengths',
    'voltage_var_factor',
    'res_tol',
    'termination_margin',
    'heat_loss_sf',
    'heat_loss_method',
    'rtd_thrm',
    'wind_speed',
    'req_local_isolator',
    'caution_label_interval',
    'k_factor_ccons',
    'isolator_location',
    'ckt_ln',
    'loop_ln',
    'acc_power_density',
    'tracer_temp_factor',
    'alpha_for_res',
    'allowablevdrop',
    'udf1',
    'udf2',
    'udf3',
]


def copy_project_setup(source_project, target_project):
    for field_name in PROJECT_DATA_TEMPLATE_FIELDS:
        setattr(target_project, field_name, getattr(source_project, field_name))


def emit_timing(message):
    if not getattr(settings, "EHT_TIMING_LOGS", False):
        return
    print(message, flush=True)
    logger.warning(message)


def _timed_json_response(payload, *, status=200, context_label='response'):
    serialization_started = perf_counter()
    serialized_payload = json.dumps(payload, default=str)
    serialization_duration = perf_counter() - serialization_started
    payload_size_bytes = len(serialized_payload.encode('utf-8'))
    emit_timing(
        "EHT timing | {label} | response_build={duration:.3f}s | response_bytes={payload_bytes}".format(
            label=context_label,
            duration=serialization_duration,
            payload_bytes=payload_size_bytes,
        )
    )
    return JsonResponse(payload, status=status)

# Create your views here.
def index(request):
    context = {'key1': 'value1','key2': 'value2' }
    return render (request, 'eht/home.html', context)


# --------------Create project data--------------------------------------------------
def create_project_data(request, project_id=None,):  
    form = handle_project_data(request)
    return render(request, 'eht/project_data.html', {'form': form})
# --------------Edit project data--------------------------------------------------
def update_project_data(request, project_id=None, *arg, **kwarg):
    form = handle_project_data(request, project_id)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        form_html = render_to_string('eht/partials/project_data_form.html', {'form': form, 'project_id': project_id}, request)
        return JsonResponse({'form_html': form_html})    
    return render (request, 'eht/project_data.html', {'form': form, 'project_id': project_id})

# --------------Download Input data Template--------------------------------------------------
@login_required
def download_template(request):
    file_path = os.path.join('file_storage', os.path.basename('EHT_Input_template.xlsx'))    
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_path)
        return response
    else:
        messages.error(request, "The file could not be found.")
        return redirect('some_error_page')

@login_required
def calculate_view(request, project_id=None):
    project_id = project_id or request.GET.get('project_id') or request.POST.get('project_id')

    if request.method == 'POST':
        request_started = perf_counter()
        file = request.FILES.get('file')
        if not file: return JsonResponse({'error': 'No file uploaded'}, status=400)
        if not project_id:
            return JsonResponse({'error': 'Project ID is required before uploading input data.'}, status=400)

        try:
            _save_project_setup_from_upload(request, project_id)

            # Step 1: Sanitize the file
            sanitize_started = perf_counter()
            valid_process_line_data, invalid_data, error_file_path = sanitize_file(file, request.session, request.user)
            sanitize_duration = perf_counter() - sanitize_started
            emit_timing(
                "EHT timing | calculate_view | project={project} | sanitize={duration:.3f}s | valid_rows={valid_rows} | invalid_rows={invalid_rows}".format(
                    project=project_id,
                    duration=sanitize_duration,
                    valid_rows=len(valid_process_line_data),
                    invalid_rows=len(invalid_data),
                )
            )
            if not valid_process_line_data and invalid_data:
                error_file_name = os.path.basename(error_file_path)
                error_file_url = reverse('download_error_file', args=[error_file_name])
                response = _timed_json_response({
                    'error': 'No valid rows were found in the uploaded file. The existing project workspace was left unchanged.',
                    'error_file_url': error_file_url,
                }, status=400, context_label='calculate_view_invalid_only')
                emit_timing(
                    "EHT timing | calculate_view | project={project} | total_request={duration:.3f}s".format(
                        project=project_id,
                        duration=perf_counter() - request_started,
                    )
                )
                return response

            if not valid_process_line_data:
                return JsonResponse({'error': 'No valid uploaded data was available to process.'}, status=400)

            replace_started = perf_counter()
            clear_duration = 0.0
            upload_duration = 0.0
            with transaction.atomic():
                clear_started = perf_counter()
                clear_project_workspace_data(project_id)
                clear_duration = perf_counter() - clear_started
                upload_started = perf_counter()
                uploaded_count = upload_inputData_in_DB(valid_process_line_data, project_id)
                upload_duration = perf_counter() - upload_started
            replace_duration = perf_counter() - replace_started
            emit_timing(
                "EHT timing | calculate_view | project={project} | replace_and_upload={duration:.3f}s | clear={clear:.3f}s | upload={upload:.3f}s | commit={commit:.3f}s | uploaded_rows={uploaded_rows}".format(
                    project=project_id,
                    duration=replace_duration,
                    clear=clear_duration,
                    upload=upload_duration,
                    commit=max(replace_duration - clear_duration - upload_duration, 0.0),
                    uploaded_rows=uploaded_count,
                )
            )

            # If invalid data exists, store only the valid pending rows and ask the user to review the error file.
            if invalid_data:
                error_file_name = os.path.basename(error_file_path)
                error_file_url = reverse('download_error_file', args=[error_file_name])
                response = _timed_json_response({
                    'valid_data_with_error': True,
                    'error_file_url': error_file_url,
                    'project_id': project_id,
                    'uploaded_rows': uploaded_count,
                    'success': 'Partial valid data uploaded. Download the error file and confirm the pending rows when ready.',
                }, status=200, context_label='calculate_view_partial_valid')
                emit_timing(
                    "EHT timing | calculate_view | project={project} | total_request={duration:.3f}s".format(
                        project=project_id,
                        duration=perf_counter() - request_started,
                    )
                )
                return response

            # Confirm the uploaded rows in a short transaction before calculation/storage work begins.
            confirm_started = perf_counter()
            with transaction.atomic():
                status_ok, _valid_data, updated_count = update_pending_status(project_id)
            confirm_duration = perf_counter() - confirm_started
            emit_timing(
                "EHT timing | calculate_view | project={project} | confirm_pending={duration:.3f}s | confirmed_rows={confirmed_rows}".format(
                    project=project_id,
                    duration=confirm_duration,
                    confirmed_rows=updated_count,
                )
            )

            if not status_ok:
                raise ValidationError('Failed to confirm uploaded data.')

            if updated_count == 0:
                return JsonResponse({'error': 'No valid uploaded data was available to process.'}, status=400)

            calculation_result, result_counts = run_project_calculations(project_id)
            response = _timed_json_response({
                'success': 'Input file processed and calculations completed successfully.',
                'project_id': project_id,
                'confirmed_rows': updated_count,
                'result_counts': result_counts,
                'calculation_result': calculation_result,
            }, context_label='calculate_view_success')
            emit_timing(
                "EHT timing | calculate_view | project={project} | total_request={duration:.3f}s".format(
                    project=project_id,
                    duration=perf_counter() - request_started,
                )
            )
            return response

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return JsonResponse({'error': f"An unexpected error occurred: {str(e)}"}, status=500)
    return JsonResponse({'error': 'Invalid request method.'}, status=405)

def _get_project_workspace_context(request, project_id):
    context = {
        'project_id': project_id or '',
        'managed_project': None,
        'project_setup': None,
        'total_input_count': 0,
        'confirmed_input_count': 0,
        'pending_input_count': 0,
        'calculated_line_count': 0,
    }
    if not project_id:
        return context

    managed_project = ManagedProject.available_to_user(getattr(request, 'user', None)).filter(proj_id=project_id).first()
    if managed_project is None:
        raise Http404("Project not found.")

    project_setup = ProjectData.objects.filter(proj_id=project_id).first()
    input_lines = HeatTracingInput.objects.filter(proj_id=project_id)

    context.update({
        'managed_project': managed_project,
        'project_setup': project_setup,
        'total_input_count': input_lines.count(),
        'confirmed_input_count': input_lines.filter(status='confirmed').count(),
        'pending_input_count': input_lines.filter(status='pending').count(),
        'calculated_line_count': ProcessLineCalculation.objects.filter(line__proj_id=project_id).count(),
    })
    return context


def _build_result_workspace_data(project_id):
    calculations = list(
        ProcessLineCalculation.objects.filter(line__proj_id=project_id)
        .select_related(
            'line',
            'line__selected_tracer_result',
            'line__power_distribution_result',
        )
        .prefetch_related(
            Prefetch(
                'line__alternate_tracer_results',
                queryset=AlternateTracer.objects.order_by('option_rank'),
            ),
            Prefetch(
                'line__power_distribution_result__branches',
                queryset=PowerDistributionBranch.objects.order_by('branch_index'),
            ),
        )
        .order_by('line__line_id')
    )
    sld_payload = build_project_sld_payload(project_id)
    sld_meta = sld_payload.get('meta') or {}
    allow_topology_overrides = not sld_meta.get('topology_edit_review_required')
    branch_rows = list(
        PowerDistributionBranch.objects.filter(distribution__line__proj_id=project_id)
        .select_related('distribution__line')
        .order_by('distribution__line__line_id', 'branch_index')
    )
    branch_rows = apply_active_cable_schedule_rows(
        project_id,
        branch_rows,
        allow_stale=allow_topology_overrides,
    )
    branch_rows = attach_cable_override_summaries(branch_rows, sld_payload)
    active_tracer_overrides = {
        str(override.line_id): override
        for override in TracerSelectionOverride.objects.filter(
            project_id=project_id,
            is_active=True,
        ).select_related('line')
    }
    override_alternates = {
        (str(alternate.line_id), alternate.v_uid): alternate
        for alternate in AlternateTracer.objects.filter(
            line_id__in=active_tracer_overrides.keys(),
        )
    }

    line_results = []
    for calculation in calculations:
        line = calculation.line
        tracer_override = active_tracer_overrides.get(str(line.uid))
        override_alternate = (
            override_alternates.get((str(line.uid), tracer_override.selected_v_uid))
            if tracer_override
            else None
        )
        line_results.append({
            'calculation': calculation,
            'line': line,
            'selected_tracer': getattr(line, 'selected_tracer_result', None),
            'alternate_tracers': list(line.alternate_tracer_results.all()),
            'tracer_override': tracer_override,
            'tracer_override_alternate': override_alternate,
            'branch_count': len(getattr(line.power_distribution_result, 'branches').all()) if hasattr(line, 'power_distribution_result') else 0,
        })

    summary = {
        'calculated_lines': len(line_results),
        'total_circuits': sum(item['calculation'].total_circuits for item in line_results),
        'total_power_kw': sum(item['calculation'].total_power_consumption for item in line_results) / 1000 if line_results else 0,
        'total_tracer_length': sum(item['calculation'].total_tracer_length for item in line_results),
        'branch_count': len(branch_rows),
        'tracer_override_count': len(active_tracer_overrides),
    }
    summary = apply_active_summary_overrides(
        project_id,
        'result',
        summary,
        allow_stale=allow_topology_overrides,
    )
    return {
        'line_results': line_results,
        'branch_rows': branch_rows,
        'summary': summary,
    }


def _branch_value(branch, path, default=''):
    missing = object()
    value = branch
    for key in path:
        if isinstance(value, dict):
            value = value.get(key, missing)
        else:
            value = getattr(value, key, missing)
        if value is missing:
            return default
    return value


def result_view(request):
    project_id = request.GET.get('project_id')
    context = _get_project_workspace_context(request, project_id)
    line_results = []
    branch_rows = []
    summary = {
        'calculated_lines': 0,
        'total_circuits': 0,
        'total_power_kw': 0,
        'total_tracer_length': 0,
        'branch_count': 0,
    }

    if project_id and context['project_setup']:
        result_data = _build_result_workspace_data(project_id)
        line_results = result_data['line_results']
        branch_rows = result_data['branch_rows']
        summary = result_data['summary']

    context.update({
        'line_results': line_results,
        'branch_rows': branch_rows,
        'result_summary': summary,
        'has_results': bool(line_results),
    })
    return render(request, 'eht/partials/result_tab.html', context)


def cable_schedule_view(request):
    project_id = request.GET.get('project_id')
    context = _get_project_workspace_context(request, project_id)
    cable_schedule_rows = []
    cable_schedule_summary = {
        'row_count': 0,
        'source_label': 'Generated calculation',
        'has_topology_edit': False,
        'topology_baseline_changed': False,
        'manual_topology_warning': '',
        'db_to_jb_total_m': 0,
        'jb_to_jb_total_m': 0,
        'branch_cable_total_m': 0,
        'override_count': 0,
    }

    if project_id and context['project_setup']:
        cable_schedule_data = build_cable_schedule_workspace_data(project_id)
        cable_schedule_rows = cable_schedule_data['cable_rows']
        cable_schedule_summary = cable_schedule_data['summary']

    context.update({
        'cable_schedule_rows': cable_schedule_rows,
        'cable_schedule_summary': cable_schedule_summary,
        'has_cable_schedule_rows': bool(cable_schedule_rows),
        'cable_schedule_export_url': reverse('cable_schedule_export_view'),
    })
    return render(request, 'eht/partials/cable_schedule_tab.html', context)


def cable_schedule_export_view(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to export cable schedule.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    cable_schedule_data = build_cable_schedule_workspace_data(project_id)
    cable_rows = cable_schedule_data['cable_rows']
    if not cable_rows:
        return JsonResponse({'error': 'No cable schedule rows are available for this project yet.'}, status=400)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(
            cable_schedule_export_rows(cable_rows),
            columns=CABLE_SCHEDULE_EXPORT_HEADERS,
        ).to_excel(writer, sheet_name='Cable Schedule', index=False)

    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{project_id}_cable_schedule.xlsx"'
    return response


def import_input_view(request):
    project_id = request.GET.get('project_id')
    context = _get_project_workspace_context(request, project_id)
    input_rows = []

    if project_id:
        input_rows = list(
            HeatTracingInput.objects.filter(proj_id=project_id)
            .order_by('xlid', 'line_id')
        )

    context.update({
        'input_rows': input_rows,
        'has_input_rows': bool(input_rows),
    })
    return render(request, 'eht/partials/import_input_tab.html', context)


def input_data_export_view(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to export input data.'}, status=400)

    _get_project_workspace_context(request, project_id)
    input_rows = list(
        HeatTracingInput.objects.filter(proj_id=project_id)
        .order_by('xlid', 'line_id')
    )

    if not input_rows:
        return JsonResponse({'error': 'No imported input data is available for this project yet.'}, status=400)

    export_rows = [
        {
            'Project ID': row.proj_id,
            'Excel Row': row.xlid,
            'Line ID': row.line_id,
            'PID No': row.pid_no,
            'Area': row.area,
            'Train': row.train,
            'Service Type': row.service_type,
            'Line Size': row.line_size,
            'Line Length': row.line_length,
            'Valve Qty': row.valve_qty,
            'Flange Qty': row.flange_qty,
            'Support Qty': row.support_qty,
            'Pipe Material Class': row.pipe_mat_class,
            'Insulation Material': row.ins_mat_type,
            'Insulation Thickness': row.insul_thick,
            'Maintenance Temp': row.maint_temp,
            'Operating Temp': row.oper_temp,
            'Design Temp': row.design_temp,
            'Emergency Supply': row.emergency_supply,
            'Discipline': row.discipline,
            'Remarks': row.remarks,
            'Status': row.status,
        }
        for row in input_rows
    ]

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(export_rows).to_excel(writer, sheet_name='Input Data', index=False)

    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{project_id}_input_data.xlsx"'
    return response


def _build_boq_workspace_data(project_id):
    consolidated_items = list(
        BOQ.objects.filter(project_id=project_id, scope='consolidated')
        .order_by('item_code')
    )
    line_items = (
        BOQ.objects.filter(project_id=project_id, scope='line')
        .select_related('line')
        .order_by('line__line_id', 'item_code')
    )
    grouped_items = {}
    for item in line_items:
        if item.line_id is None:
            continue
        group = grouped_items.setdefault(
            item.line_id,
            {'line': item.line, 'items': []},
        )
        group['items'].append(item)

    line_groups = []
    for line_id, group in grouped_items.items():
        tracer_quantity = next(
            (entry.quantity for entry in group['items'] if entry.item_code == 'TRACER'),
            0,
        )
        line_groups.append({
            'line_id': line_id,
            'line': group['line'],
            'items': group['items'],
            'item_count': len(group['items']),
            'tracer_quantity': tracer_quantity,
        })

    line_groups.sort(key=lambda group: group['line'].line_id if group['line'] else '')
    consolidated_lookup = {item.item_code: item.quantity for item in consolidated_items}
    sld_payload = build_project_sld_payload(project_id)
    sld_meta = sld_payload.get('meta') or {}
    allow_topology_overrides = not sld_meta.get('topology_edit_review_required')
    summary = {
        'consolidated_item_count': len(consolidated_items),
        'line_group_count': len(line_groups),
        'tracer_total': consolidated_lookup.get('TRACER', 0),
        'mcb_total': consolidated_lookup.get('MCB', 0),
        'junction_box_total': consolidated_lookup.get('JB3PH', 0) + consolidated_lookup.get('JB1PH', 0),
    }
    summary = apply_active_summary_overrides(
        project_id,
        'boq',
        summary,
        allow_stale=allow_topology_overrides,
    )
    return {
        'consolidated_items': consolidated_items,
        'line_groups': line_groups,
        'summary': summary,
    }


def _build_sld_workspace_data(project_id, line_id=None):
    payload = build_project_sld_payload(project_id, line_id=line_id)
    layout = get_project_sld_layout(project_id, payload=payload)
    validation = validate_project_sld_payload(project_id, payload=payload, line_id=line_id)
    selected_line_id = ''
    if line_id and payload.get('line_groups'):
        selected_line_id = payload['line_groups'][0]['line_id'] if len(payload['line_groups']) == 1 else line_id

    return {
        'payload': payload,
        'layout': layout,
        'validation': validation,
        'component_summary': _build_sld_component_summary(payload['nodes']),
        'line_summary': _build_sld_line_summary(payload),
        'summary': _build_sld_summary(payload),
        'topology_state': _build_sld_topology_state(payload),
        'selected_line_id': selected_line_id,
    }


def _build_sld_topology_state(payload):
    meta = payload.get('meta', {})
    return {
        'has_topology_edit': bool(meta.get('has_topology_edit')),
        'topology_edit_id': meta.get('topology_edit_id'),
        'topology_edit_type': meta.get('topology_edit_type') or '',
        'topology_edit_status': meta.get('topology_edit_status') or '',
        'topology_baseline_changed': bool(meta.get('topology_baseline_changed')),
        'manual_topology_warning': meta.get('manual_topology_warning') or '',
    }


def _build_sld_summary(payload):
    return {
        'line_group_count': len(payload['line_groups']),
        'branch_count': payload['meta']['branch_count'],
        'node_count': payload['meta']['node_count'],
        'edge_count': payload['meta']['edge_count'],
    }


def _build_sld_component_summary(nodes):
    component_type_counts = Counter(node['component_type'] for node in nodes)
    component_summary = []
    for component_type, count in sorted(component_type_counts.items()):
        sample_node = next((node for node in nodes if node['component_type'] == component_type), {})
        component_summary.append({
            'component_type': component_type,
            'display_name': sample_node.get('display_name', component_type),
            'count': count,
        })
    return component_summary


def _node_matches_line_group(node, line_group):
    line_uid = line_group.get('line_uid')
    if line_uid:
        return str(node.get('line_uid') or '') == str(line_uid)
    return line_group.get('line_id') in node.get('line_ids', [])


def _edge_matches_line_group(edge, line_group):
    line_uid = line_group.get('line_uid')
    if line_uid and edge.get('line_uid'):
        return str(edge.get('line_uid') or '') == str(line_uid)
    return line_group.get('line_id') in edge.get('line_ids', [])


def _build_sld_line_summary(payload):
    line_summary = []
    nodes = payload['nodes']
    edges = payload['edges']
    for group in payload['line_groups']:
        line_id = group['line_id']
        component_count = sum(1 for node in nodes if _node_matches_line_group(node, group))
        edge_count = sum(1 for edge in edges if _edge_matches_line_group(edge, group))
        line_summary.append({
            'line_id': line_id,
            'line_uid': group.get('line_uid', ''),
            'branch_indices': group['branch_indices'],
            'branch_count': len(group['branch_indices']),
            'component_count': component_count,
            'edge_count': edge_count,
        })
    return line_summary


def boq_view(request):
    project_id = request.GET.get('project_id')
    context = _get_project_workspace_context(request, project_id)
    consolidated_items = []
    line_groups = []
    summary = {
        'consolidated_item_count': 0,
        'line_group_count': 0,
        'tracer_total': 0,
        'mcb_total': 0,
        'junction_box_total': 0,
    }

    if project_id and context['project_setup']:
        boq_data = _build_boq_workspace_data(project_id)
        consolidated_items = boq_data['consolidated_items']
        line_groups = boq_data['line_groups']
        summary = boq_data['summary']

    context.update({
        'consolidated_items': consolidated_items,
        'line_groups': line_groups,
        'boq_summary': summary,
        'has_boq': bool(consolidated_items or line_groups),
    })
    return render(request, 'eht/partials/boq_tab.html', context)


def boq_line_detail_view(request):
    project_id = request.GET.get('project_id')
    line_id = (request.GET.get('line_id') or '').strip()

    if not project_id or not line_id:
        return JsonResponse({'error': 'Project ID and line ID are required.'}, status=400)

    _get_project_workspace_context(request, project_id)

    line_items = list(
        BOQ.objects.filter(
            project_id=project_id,
            scope='line',
            line__line_id__iexact=line_id,
        )
        .select_related('line')
        .order_by('item_code')
    )

    if not line_items:
        return JsonResponse({'error': f"No BOQ line items were found for line ID '{line_id}'."}, status=404)

    line = line_items[0].line
    tracer_quantity = next((item.quantity for item in line_items if item.item_code == 'TRACER'), 0)
    context = {
        'project_id': project_id,
        'line': line,
        'line_items': line_items,
        'item_count': len(line_items),
        'tracer_quantity': tracer_quantity,
    }
    return render(request, 'eht/partials/boq_line_detail.html', context)


def sld_workspace_view(request):
    project_id = request.GET.get('project_id')
    selected_line_id = (request.GET.get('line_id') or '').strip()
    context = _get_project_workspace_context(request, project_id)
    sld_data = {
        'summary': {
            'line_group_count': 0,
            'branch_count': 0,
            'node_count': 0,
            'edge_count': 0,
        },
        'layout': {
            'project_id': project_id or '',
            'positions': {},
            'meta': {
                'saved_count': 0,
                'node_count': 0,
                'has_saved_layout': False,
            },
        },
        'validation': {
            'project_id': project_id or '',
            'status': 'warning',
            'summary': {
                'passed_count': 0,
                'warning_count': 0,
                'failed_count': 0,
                'check_count': 0,
            },
            'checks': [],
            'branch_checks': [],
        },
        'component_summary': [],
        'line_summary': [],
        'topology_state': {
            'has_topology_edit': False,
            'topology_edit_id': None,
            'topology_edit_type': '',
            'topology_edit_status': '',
            'topology_baseline_changed': False,
            'manual_topology_warning': '',
        },
        'selected_line_id': '',
    }
    selected_line_error = ''

    if project_id and context['project_setup']:
        if selected_line_id:
            sld_data = _build_sld_workspace_data(project_id, line_id=selected_line_id)
            if not sld_data['summary']['node_count']:
                selected_line_error = f"No SLD line group was found for line ID '{selected_line_id}'."
                sld_data = _build_sld_workspace_data(project_id)
        else:
            sld_data = _build_sld_workspace_data(project_id)

    context.update({
        'sld_summary': sld_data['summary'],
        'sld_layout': sld_data['layout'],
        'sld_validation': sld_data['validation'],
        'sld_component_summary': sld_data['component_summary'],
        'sld_line_summary': sld_data['line_summary'],
        'has_sld_payload': bool(sld_data['summary']['node_count']),
        'sld_payload_url': reverse('sld_payload_view'),
        'sld_pdf_export_url': reverse('sld_pdf_export_view'),
        'sld_layout_url': reverse('sld_layout_view'),
        'sld_layout_reset_url': reverse('sld_layout_reset_view'),
        'sld_topology_combine_preview_url': reverse('sld_topology_combine_preview_view'),
        'sld_topology_combine_apply_url': reverse('sld_topology_combine_apply_view'),
        'sld_topology_split_preview_url': reverse('sld_topology_split_preview_view'),
        'sld_topology_split_apply_url': reverse('sld_topology_split_apply_view'),
        'sld_topology_downstream_jb_preview_url': reverse('sld_topology_downstream_jb_preview_view'),
        'sld_topology_downstream_jb_apply_url': reverse('sld_topology_downstream_jb_apply_view'),
        'sld_topology_attach_jb_preview_url': reverse('sld_topology_attach_jb_preview_view'),
        'sld_topology_attach_jb_apply_url': reverse('sld_topology_attach_jb_apply_view'),
        'sld_topology_reset_url': reverse('sld_topology_reset_view'),
        'sld_topology_reset_selected_url': reverse('sld_topology_reset_selected_view'),
        'sld_cable_override_save_url': reverse('sld_cable_override_save_view'),
        'sld_cable_override_reset_url': reverse('sld_cable_override_reset_view'),
        'sld_tracer_override_save_url': reverse('sld_tracer_override_save_view'),
        'sld_tracer_override_reset_url': reverse('sld_tracer_override_reset_view'),
        'sld_topology_state': sld_data['topology_state'],
        'sld_validation_url': reverse('sld_validation_view'),
        'sld_selected_line_id': sld_data.get('selected_line_id', ''),
        'sld_selected_line_query': selected_line_id,
        'sld_selected_line_error': selected_line_error,
    })
    return render(request, 'eht/partials/sld_tab.html', context)


def sld_payload_view(request):
    project_id = request.GET.get('project_id')
    selected_line_id = (request.GET.get('line_id') or '').strip()
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to load SLD data.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    if selected_line_id:
        payload = build_project_sld_payload(project_id, line_id=selected_line_id)
        if not payload['meta']['node_count']:
            return JsonResponse({'error': f"No SLD line group was found for line ID '{selected_line_id}'."}, status=404)
    else:
        payload = build_project_sld_payload(project_id)
        if not payload['meta']['node_count']:
            return JsonResponse({'error': 'No stored power-distribution data is available for this project yet.'}, status=400)

    return JsonResponse(payload)


def sld_pdf_export_view(request):
    project_id = request.GET.get('project_id')
    selected_line_id = (request.GET.get('line_id') or '').strip()
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to export SLD PDF.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    payload = build_project_sld_payload(project_id, line_id=selected_line_id)
    if not payload['meta']['node_count']:
        return JsonResponse({'error': 'No stored SLD graph data is available for PDF export.'}, status=404)

    pdf_bytes = build_sld_pdf(project_id, payload)
    filename = f'{project_id}_sld.pdf'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _json_validation_error(message, status=400):
    if isinstance(message, ValidationError):
        message = '; '.join(message.messages)
    return JsonResponse({'error': str(message)}, status=status)


def sld_cable_override_save_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid cable override payload.'}, status=400)

    project_id = body.get('project_id')
    component_id = body.get('component_id')
    if not project_id or not component_id:
        return JsonResponse({'error': 'Project ID and cable component ID are required.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    payload = build_project_sld_payload(project_id)
    node = find_cable_node(payload, component_id)
    if node is None:
        return JsonResponse({'error': 'Selected component is not a cable in the active SLD payload.'}, status=404)

    try:
        override = save_cable_override(
            project_id,
            node,
            manual_length_m=body.get('manual_length_m'),
            manual_cable_size=body.get('manual_cable_size', ''),
            remarks=body.get('remarks', ''),
            user=getattr(request, 'user', None),
        )
    except ValidationError as exc:
        return _json_validation_error(exc)

    return JsonResponse({
        'success': f'Cable override saved for {override.display_tag}.',
        'component_id': override.component_id,
        'display_tag': override.display_tag,
        'manual_length_m': override.manual_length_m,
        'manual_cable_size': override.manual_cable_size,
    })


def sld_cable_override_reset_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid cable override reset payload.'}, status=400)

    project_id = body.get('project_id')
    component_id = body.get('component_id')
    if not project_id or not component_id:
        return JsonResponse({'error': 'Project ID and cable component ID are required.'}, status=400)

    _get_project_workspace_context(request, project_id)
    reset_count = reset_cable_override(project_id, component_id)
    return JsonResponse({
        'success': 'Cable override reset to generated value.',
        'reset_count': reset_count,
    })


def sld_tracer_override_save_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid tracer override payload.'}, status=400)

    project_id = body.get('project_id')
    component_id = body.get('component_id')
    if not project_id or not component_id:
        return JsonResponse({'error': 'Project ID and tracer component ID are required.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    payload = build_project_sld_payload(project_id)
    node = find_tracer_node(payload, component_id)
    if node is None:
        return JsonResponse({'error': 'Selected component is not a tracer in the active SLD payload.'}, status=404)

    try:
        override = save_tracer_override(
            project_id,
            node,
            selected_v_uid=body.get('selected_v_uid', ''),
            remarks=body.get('remarks', ''),
            user=getattr(request, 'user', None),
        )
    except ValidationError as exc:
        return _json_validation_error(exc)

    if override is None:
        return JsonResponse({'success': 'Tracer override reset to generated selection.'})
    return JsonResponse({
        'success': f'Tracer override saved for {node.get("display_tag")}.',
        'component_id': component_id,
        'line_uid': str(override.line_id),
        'selected_v_uid': override.selected_v_uid,
        'selected_option_rank': override.selected_option_rank,
    })


def sld_tracer_override_reset_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid tracer override reset payload.'}, status=400)

    project_id = body.get('project_id')
    line_uid = body.get('line_uid')
    if not project_id or not line_uid:
        return JsonResponse({'error': 'Project ID and tracer line UID are required.'}, status=400)

    _get_project_workspace_context(request, project_id)
    reset_count = reset_tracer_override(project_id, line_uid)
    return JsonResponse({
        'success': 'Tracer override reset to generated selection.',
        'reset_count': reset_count,
    })


def sld_validation_view(request):
    project_id = request.GET.get('project_id')
    selected_line_id = (request.GET.get('line_id') or '').strip()
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to validate the SLD.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    payload = build_project_sld_payload(project_id, line_id=selected_line_id)
    if not payload['meta']['node_count']:
        if selected_line_id:
            return JsonResponse({'error': f"No SLD line group was found for line ID '{selected_line_id}'."}, status=404)
        return JsonResponse({'error': 'No stored power-distribution data is available for this project yet.'}, status=400)

    return JsonResponse(validate_project_sld_payload(project_id, payload=payload, line_id=selected_line_id))


def sld_layout_view(request):
    if request.method == 'GET':
        body = {}
        project_id = request.GET.get('project_id')
        selected_line_id = (request.GET.get('line_id') or '').strip()
    elif request.method == 'POST':
        try:
            body = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid layout payload.'}, status=400)
        project_id = body.get('project_id') or request.POST.get('project_id')
        selected_line_id = (body.get('line_id') or '').strip()
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    if not project_id:
        return JsonResponse({'error': 'Project ID is required to load or save the SLD layout.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    payload = build_project_sld_payload(project_id, line_id=selected_line_id)
    if not payload['meta']['node_count']:
        if selected_line_id:
            return JsonResponse({'error': f"No SLD line group was found for line ID '{selected_line_id}'."}, status=404)
        return JsonResponse({'error': 'No stored power-distribution data is available for this project yet.'}, status=400)

    response_payload = payload
    if request.method == 'GET':
        return JsonResponse(get_project_sld_layout(project_id, payload=response_payload))

    save_summary = save_project_sld_layout(
        project_id,
        positions=body.get('positions', {}),
        payload=payload,
        prune_stale=not selected_line_id,
    )
    refreshed_layout = get_project_sld_layout(project_id, payload=response_payload)
    return JsonResponse({
        'success': 'SLD layout saved successfully.',
        'project_id': project_id,
        'saved_count': save_summary['saved_count'],
        'ignored_component_ids': save_summary['ignored_component_ids'],
        'layout': refreshed_layout,
    })


def sld_layout_reset_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        body = {}
    project_id = body.get('project_id') or request.POST.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to reset the SLD layout.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    reset_summary = reset_project_sld_layout(project_id)
    return JsonResponse({
        'success': 'Stored SLD layout reset successfully.',
        **reset_summary,
    })


def _parse_json_request(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def sld_topology_combine_preview_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology edit payload.'}, status=400)

    project_id = body.get('project_id')
    component_ids = body.get('component_ids') or []
    trunk_length_m = body.get('trunk_length_m')
    cable_size = body.get('cable_size') or '4C'
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to preview topology edits.'}, status=400)

    _get_project_workspace_context(request, project_id)
    preview = preview_combine_feeders(project_id, component_ids, trunk_length_m=trunk_length_m, cable_size=cable_size)
    if not preview['ok']:
        return JsonResponse({'error': preview['error'], **preview}, status=400)
    return JsonResponse(preview)


def sld_topology_combine_apply_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology edit payload.'}, status=400)

    project_id = body.get('project_id')
    component_ids = body.get('component_ids') or []
    trunk_length_m = body.get('trunk_length_m')
    cable_size = body.get('cable_size') or '4C'
    remarks = body.get('remarks') or ''
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to apply topology edits.'}, status=400)

    _get_project_workspace_context(request, project_id)
    result = apply_combine_feeders(
        project_id,
        component_ids,
        trunk_length_m=trunk_length_m,
        cable_size=cable_size,
        user=getattr(request, 'user', None),
        remarks=remarks,
    )
    if not result['ok']:
        return JsonResponse({'error': result['error'], **result}, status=400)
    return JsonResponse({'success': 'Feeder combine topology edit applied.', **result})


def sld_topology_split_preview_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology edit payload.'}, status=400)

    project_id = body.get('project_id')
    component_ids = body.get('component_ids') or []
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to preview topology edits.'}, status=400)

    _get_project_workspace_context(request, project_id)
    preview = preview_split_circuits(project_id, component_ids)
    if not preview['ok']:
        return JsonResponse({'error': preview['error'], **preview}, status=400)
    return JsonResponse(preview)


def sld_topology_split_apply_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology edit payload.'}, status=400)

    project_id = body.get('project_id')
    component_ids = body.get('component_ids') or []
    remarks = body.get('remarks') or ''
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to apply topology edits.'}, status=400)

    _get_project_workspace_context(request, project_id)
    result = apply_split_circuits(
        project_id,
        component_ids,
        user=getattr(request, 'user', None),
        remarks=remarks,
    )
    if not result['ok']:
        return JsonResponse({'error': result['error'], **result}, status=400)
    return JsonResponse({'success': 'Circuit split topology edit applied.', **result})


def sld_topology_downstream_jb_preview_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology edit payload.'}, status=400)

    project_id = body.get('project_id')
    parent_component_id = body.get('parent_component_id') or ''
    branch_component_ids = body.get('branch_component_ids') or []
    trunk_length_m = body.get('trunk_length_m')
    cable_size = body.get('cable_size') or '4C'
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to preview topology edits.'}, status=400)

    _get_project_workspace_context(request, project_id)
    preview = preview_downstream_jb(
        project_id,
        parent_component_id,
        branch_component_ids,
        trunk_length_m,
        cable_size=cable_size,
    )
    if not preview['ok']:
        return JsonResponse({'error': preview['error'], **preview}, status=400)
    return JsonResponse(preview)


def sld_topology_downstream_jb_apply_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology edit payload.'}, status=400)

    project_id = body.get('project_id')
    parent_component_id = body.get('parent_component_id') or ''
    branch_component_ids = body.get('branch_component_ids') or []
    trunk_length_m = body.get('trunk_length_m')
    cable_size = body.get('cable_size') or '4C'
    remarks = body.get('remarks') or ''
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to apply topology edits.'}, status=400)

    _get_project_workspace_context(request, project_id)
    result = apply_downstream_jb(
        project_id,
        parent_component_id,
        branch_component_ids,
        trunk_length_m=trunk_length_m,
        cable_size=cable_size,
        user=getattr(request, 'user', None),
        remarks=remarks,
    )
    if not result['ok']:
        return JsonResponse({'error': result['error'], **result}, status=400)
    return JsonResponse({'success': 'Downstream 3PH JB topology edit applied.', **result})


def sld_topology_attach_jb_preview_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology edit payload.'}, status=400)

    project_id = body.get('project_id')
    source_component_id = body.get('source_component_id') or ''
    target_jb_component_id = body.get('target_jb_component_id') or ''
    trunk_length_m = body.get('trunk_length_m')
    cable_size = body.get('cable_size') or '4C'
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to preview topology edits.'}, status=400)

    _get_project_workspace_context(request, project_id)
    preview = preview_attach_to_jb(
        project_id,
        source_component_id,
        target_jb_component_id,
        trunk_length_m=trunk_length_m,
        cable_size=cable_size,
    )
    if not preview['ok']:
        return JsonResponse({'error': preview['error'], **preview}, status=400)
    return JsonResponse(preview)


def sld_topology_attach_jb_apply_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology edit payload.'}, status=400)

    project_id = body.get('project_id')
    source_component_id = body.get('source_component_id') or ''
    target_jb_component_id = body.get('target_jb_component_id') or ''
    trunk_length_m = body.get('trunk_length_m')
    cable_size = body.get('cable_size') or '4C'
    remarks = body.get('remarks') or ''
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to apply topology edits.'}, status=400)

    _get_project_workspace_context(request, project_id)
    result = apply_attach_to_jb(
        project_id,
        source_component_id,
        target_jb_component_id,
        trunk_length_m=trunk_length_m,
        cable_size=cable_size,
        user=getattr(request, 'user', None),
        remarks=remarks,
    )
    if not result['ok']:
        return JsonResponse({'error': result['error'], **result}, status=400)
    return JsonResponse({'success': 'Feeder attached to 3PH JB.', **result})


def sld_topology_reset_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology reset payload.'}, status=400)

    project_id = body.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to reset topology edits.'}, status=400)

    _get_project_workspace_context(request, project_id)
    reset_count = SLDTopologyEdit.objects.filter(
        project_id=project_id,
        status='applied',
    ).update(status='reset')
    return JsonResponse({
        'success': 'Manual topology edit reset. Generated topology is active.',
        'project_id': project_id,
        'reset_count': reset_count,
    })


def sld_topology_reset_selected_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology reset payload.'}, status=400)

    project_id = body.get('project_id')
    component_id = body.get('component_id') or ''
    remarks = body.get('remarks') or ''
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to reset selected topology.'}, status=400)
    if not component_id:
        return JsonResponse({'error': 'Select a feeder component to reset.'}, status=400)

    _get_project_workspace_context(request, project_id)
    result = apply_scoped_reset(
        project_id,
        component_id,
        user=getattr(request, 'user', None),
        remarks=remarks,
    )
    if not result['ok']:
        return JsonResponse({'error': result['error'], **result}, status=400)
    return JsonResponse({'success': 'Selected feeder tree reset to generated topology.', **result})


def result_export_view(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to export results.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    result_data = _build_result_workspace_data(project_id)
    if not result_data['line_results']:
        return JsonResponse({'error': 'No stored calculation results are available for this project yet.'}, status=400)

    line_rows = []
    alternate_rows = []
    for item in result_data['line_results']:
        calculation = item['calculation']
        line = item['line']
        selected_tracer = item['selected_tracer']
        tracer_override = item.get('tracer_override')
        tracer_override_alternate = item.get('tracer_override_alternate')
        line_rows.append({
            'Project ID': project_id,
            'Line ID': line.line_id,
            'Service Type': line.service_type,
            'Line Size': calculation.line_size,
            'Line Length': calculation.line_length,
            'Operating Temp': calculation.operating_temp,
            'Heat Loss': calculation.heat_loss,
            'Selected Tracer': calculation.selected_tracer,
            'Tracer Family': getattr(selected_tracer, 'tracer_family', ''),
            'SLD Tracer Override': tracer_override.selected_v_uid if tracer_override else '',
            'SLD Override Family': getattr(tracer_override_alternate, 'tracer_family', ''),
            'SLD Override Review Status': (
                'Review-only: load/BOQ/cable sizing not recalculated from override'
                if tracer_override
                else ''
            ),
            'Spiral Factor': calculation.spiral_factor,
            'Breaker Size': calculation.breaker_size,
            'Total Circuits': calculation.total_circuits,
            'Starting Current': calculation.starting_current,
            'Operating Current': calculation.operating_current,
            'Total Power Consumption': calculation.total_power_consumption,
            'Total Tracer Length': calculation.total_tracer_length,
            'Pipe Size mm': calculation.pipe_size_mm,
        })
        for alternate in item['alternate_tracers']:
            alternate_rows.append({
                'Project ID': project_id,
                'Line ID': line.line_id,
                'Option Rank': alternate.option_rank,
                'Tracer UID': alternate.v_uid,
                'Tracer Family': alternate.tracer_family,
                'Power Output': alternate.power_output,
                'Spiral Factor': alternate.spiral_factor,
                'Tracer Length': alternate.tracer_length,
                'Tracer With Margin': alternate.tracer_with_margin,
            })

    branch_rows = [
        {
            'Project ID': project_id,
            'Line ID': _branch_value(branch, ['distribution', 'line', 'line_id']),
            'Branch Index': _branch_value(branch, ['branch_index']),
            'Branch Type': _branch_value(branch, ['branch_type']),
            'Connected To': _branch_value(branch, ['connected_to']),
            'Circuit Count': _branch_value(branch, ['circuit_count']),
            'Cable Length DB to JB': _branch_value(branch, ['cable_length_db_to_jb']),
            'Cable Length JB to JB': _branch_value(branch, ['cable_length_jb_to_jb']),
            'Branch Cable Length Total': _branch_value(branch, ['branch_cable_length_total_m']),
            'Cable Overrides': json.dumps(_branch_value(branch, ['cable_override_summary'], []), default=str),
            'Tagged Components': str(_branch_value(branch, ['tagged_components'], {})),
        }
        for branch in result_data['branch_rows']
    ]

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(line_rows).to_excel(writer, sheet_name='Line Results', index=False)
        pd.DataFrame(branch_rows).to_excel(writer, sheet_name='Power Distribution', index=False)
        pd.DataFrame(alternate_rows).to_excel(writer, sheet_name='Alternate Tracers', index=False)

    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{project_id}_results.xlsx"'
    return response


def boq_export_view(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to export BOQ.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    boq_data = _build_boq_workspace_data(project_id)
    if not boq_data['consolidated_items'] and not boq_data['line_groups']:
        return JsonResponse({'error': 'No stored BOQ data is available for this project yet.'}, status=400)

    summary_rows = [
        {
            'Project ID': project_id,
            'Item Code': item.item_code,
            'Description': item.item_description,
            'Quantity': item.quantity,
            'Unit': item.unit,
        }
        for item in boq_data['consolidated_items']
    ]
    detail_rows = []
    for group in boq_data['line_groups']:
        for item in group['items']:
            detail_rows.append({
                'Project ID': project_id,
                'Line ID': group['line'].line_id if group['line'] else '',
                'Service Type': group['line'].service_type if group['line'] else '',
                'Item Code': item.item_code,
                'Description': item.item_description,
                'Quantity': item.quantity,
                'Unit': item.unit,
            })

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name='BOQ Summary', index=False)
        pd.DataFrame(detail_rows).to_excel(writer, sheet_name='BOQ Per Line', index=False)

    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename=\"{project_id}_boq.xlsx\"'
    return response

# -------------Download error File -------------------------------------------------------

def download_error_file(request, file_name):
    file_path = os.path.join(settings.BASE_DIR, 'file_storage','error_file', file_name)  
    try:
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_name)
    except FileNotFoundError:
        return JsonResponse({'error': 'File not found.'}, status=404)

# --------------Process the valid data --------------------------------------------------
@login_required
def confirm_valid_data(request):
    if request.method == 'POST':
        request_started = perf_counter()
        project_id = request.POST.get('project_id')
        if not project_id:
            return JsonResponse({'error': 'Project ID is required.'}, status=400)

        try:            
            with transaction.atomic():
                confirm_started = perf_counter()
                status_ok, valid_data, updated_count = update_pending_status(project_id)
                confirm_duration = perf_counter() - confirm_started
                emit_timing(
                    "EHT timing | confirm_valid_data | project={project} | confirm_pending={duration:.3f}s | confirmed_rows={confirmed_rows}".format(
                        project=project_id,
                        duration=confirm_duration,
                        confirmed_rows=updated_count,
                    )
                )
                if not status_ok:
                    raise ValidationError('Failed to confirm valid uploaded data.')

            if updated_count == 0:
                return JsonResponse({'error': 'No valid uploaded data is pending confirmation.'}, status=400)

            calculation_result, result_counts = run_project_calculations(project_id)
            logger.info(
                "Project ID: %s - Pending rows confirmed and calculations completed for %s row(s).",
                project_id,
                updated_count,
            )
            response = _timed_json_response({
                'success': 'Valid data confirmed and calculations completed successfully.',
                'project_id': project_id,
                'confirmed_rows': updated_count,
                'result_counts': result_counts,
                'calculation_result': calculation_result,
            }, status=200, context_label='confirm_valid_data_success')
            emit_timing(
                "EHT timing | confirm_valid_data | project={project} | total_request={duration:.3f}s".format(
                    project=project_id,
                    duration=perf_counter() - request_started,
                )
            )
            return response
        except Exception as e:
            logger.error(f"Project ID: {project_id} - Failed to confirm 'EHT Input data': {str(e)}", exc_info=True)
            return JsonResponse({'error': f"Failed to confirm valid data: {str(e)}"}, status=500)
        
    return JsonResponse({'error': 'Invalid request method.'}, status=405)





# # Success page when form is created successfully
# def success(request):
#     return render(request, 'eht/success.html')



# ----------Helper functions--------------------

#  Get the validated instance of forms
def handle_project_data(request, project_id=None):
    selected_project_id = request.POST.get('proj_id') or project_id or request.GET.get('project_id')
    available_projects = ManagedProject.available_to_user(getattr(request, 'user', None))
    available_project_ids = set(available_projects.values_list('proj_id', flat=True))

    if selected_project_id and not available_projects.filter(proj_id=selected_project_id).exists() and request.method != 'POST':
        raise Http404("Project not found.")

    instance = ProjectData.objects.filter(proj_id=selected_project_id).first() if selected_project_id else None
    if instance is None:
        instance = ProjectData(proj_id=selected_project_id) if selected_project_id else ProjectData()

    if request.method == 'POST' and request.POST.get('action') == 'load_defaults':
        if not selected_project_id:
            messages.error(request, "Select a project before loading the default project data.")
        elif selected_project_id not in available_project_ids:
            messages.error(request, "The selected project is not available for this user.")
        else:
            default_project = ProjectData.objects.filter(proj_id__iexact=DEFAULT_PROJECT_ID).first()
            if default_project is None:
                messages.error(request, "Default project data is not configured yet.")
            elif is_default_project_id(selected_project_id):
                messages.error(request, "Select a working project before loading the default project data.")
            else:
                copy_project_setup(default_project, instance)
                instance.proj_id = selected_project_id
                try:
                    instance.full_clean()
                    instance.save()
                    messages.success(request, "Default project data loaded successfully. Review and adjust any project-specific values.")
                except ValidationError as exc:
                    for field_errors in exc.message_dict.values():
                        for message in field_errors:
                            messages.error(request, message)
        return ProjectDataForm(instance=instance, user=getattr(request, 'user', None))

    form = ProjectDataForm(request.POST or None, instance=instance, user=getattr(request, 'user', None))
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Project data saved successfully.")
    return form


def _format_form_errors(form):
    errors = []
    for field_name, field_errors in form.errors.items():
        label = form.fields[field_name].label if field_name in form.fields else field_name
        for error in field_errors:
            errors.append(f"{label}: {error}")
    return "; ".join(errors)


def _save_project_setup_from_upload(request, project_id):
    setup_fields = set(ProjectDataForm.Meta.fields)
    if not any(field in request.POST for field in setup_fields if field != 'proj_id'):
        return None

    post_data = request.POST.copy()
    selected_project_id = post_data.get('proj_id') or project_id
    if selected_project_id != project_id:
        raise ValidationError("Uploaded project setup does not match the selected project.")
    post_data['proj_id'] = project_id

    instance = ProjectData.objects.filter(proj_id=project_id).first() or ProjectData(proj_id=project_id)
    form = ProjectDataForm(post_data, instance=instance, user=getattr(request, 'user', None))
    if not form.is_valid():
        raise ValidationError(f"Project setup could not be saved before calculation. {_format_form_errors(form)}")
    return form.save()


#  Logic for userAtempt and limit invalid attempts.
def log_failed_attempt(user, ip_address):
    # Check if a user is already locked
    attempt = UserAttempt.objects.filter(user=user).first()
    if attempt and attempt.is_locked():
        return {'locked': True, 'cooldown_expires': attempt.cooldown_expires}

    # Create or update an attempt entry
    if not attempt:
        attempt = UserAttempt.objects.create(
            user=user,
            ip_address=ip_address,
            failed_at=now(),
            lockout=False,
            cooldown_expires=None
        )
    else:
        attempt.failed_at = now()

    # Increment failed attempts and check for lockout
    attempts_count = UserAttempt.objects.filter(user=user, lockout=False).count()
    if attempts_count >= MAX_FAILED_ATTEMPTS:
        attempt.lockout = True
        attempt.cooldown_expires = now() + timedelta(minutes=COOLDOWN_PERIOD_MINUTES)

    attempt.save()
    return {'locked': attempt.lockout, 'cooldown_expires': attempt.cooldown_expires}


# Bulk upload valid/sanitized input data into database
def upload_inputData_in_DB(valid_data, project_id):
    if not project_id:
        raise ValidationError("Project ID is required before storing input rows.")

    try:
        if not valid_data:
            return 0
        build_started = perf_counter()
        valid_rows = [
            HeatTracingInput(               
                proj_id=project_id,
                xlid=row['XLID'],
                line_id=row['Line_ID'],
                service_type=row['Service_Type'],
                line_size=row['Line_Size'],
                line_length=row['Line_Length'],
                ins_mat_type=row['Ins_Mat_Type'],
                insul_thick=row['Insul_Thick'],
                maint_temp=row['Maint_T'],
                oper_temp=row['Oper_T'],
                design_temp=row['Design_T'],
                is_deleted=row['IsDeleted'],
                pid_no=row['PID_No'],
                area=row['Area'],
                train=row['Train'],
                valve_qty=row['Valve_Qty'],
                flange_qty=row['Flange_Qty'],
                support_qty=row['Support_Qty'],
                pipe_mat_class=row['Pipe_Mat_Class'],
                emergency_supply=row['Emergency_Supply'],
                discipline=row['Discipline'],
                remarks=row['Remarks'],
                status='pending',
            )
            for row in valid_data
        ]
        build_duration = perf_counter() - build_started
        bulk_create_started = perf_counter()
        HeatTracingInput.objects.bulk_create(valid_rows, batch_size=500)
        bulk_create_duration = perf_counter() - bulk_create_started
        emit_timing(
            "EHT timing | upload_inputData_in_DB | project={project} | rows={rows} | build={build:.3f}s | bulk_create={bulk_create:.3f}s".format(
                project=project_id,
                rows=len(valid_rows),
                build=build_duration,
                bulk_create=bulk_create_duration,
            )
        )
        return len(valid_rows)

    except Exception as e:
        logger.error("Failed to upload input data for project %s: %s", project_id, str(e), exc_info=True)
        raise

# Update input data status from 'pending' to confirm

def update_pending_status(project_id):
    # Update the status of valid data for the given project ID
    try:
        updated_count = HeatTracingInput.objects.filter(proj_id=project_id, status='pending').update(status='confirmed')
        valid_data = HeatTracingInput.objects.filter(proj_id=project_id, status='confirmed').values()
        logger.info(f"Project ID: {project_id} -  'EHT input data' Status updated successfully. Updated {updated_count} records.")
        return True, valid_data, updated_count
    except Exception as e:
        logger.error(f"Project ID: {project_id} - Failed to update pending status: {str(e)}", exc_info=True)
        return False, None, None



# test Base template

# --------------Create project data--------------------------------------------------
def base(request):  
    form = ProjectDataForm(user=getattr(request, 'user', None))
    return render(request, 'eht/base.html', {'form': form})

def my_login(request):    
    return render(request, 'eht/my_login.html')

def my_logout(request):    
    return render(request, 'eht/my_logout.html')

def my_register(request):    
    return render(request, 'eht/my_register.html')
