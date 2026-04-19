import json
import logging
import os
from collections import Counter
from io import BytesIO

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.timezone import now, timedelta

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
    UserAttempt,
    is_default_project_id,
)
from .pipeline import run_project_calculations
from .sanatize_input import *  # sanitize_file
from .sld_layout import get_project_sld_layout, reset_project_sld_layout, save_project_sld_layout
from .sld_payload import build_project_sld_payload
from .sld_validation import validate_project_sld_payload

COOLDOWN_PERIOD_MINUTES = 30
MAX_FAILED_ATTEMPTS = 3
BOQ_LINE_DROPDOWN_LIMIT = 25

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
        file = request.FILES.get('file')
        if not file: return JsonResponse({'error': 'No file uploaded'}, status=400)

        try:
            # Step 1: Sanitize the file
            valid_process_line_data, invalid_data, error_file_path = sanitize_file(file, request.session, request.user)
            if project_id:
                clear_project_workspace_data(project_id)
            # Save valid data to the database with a "pending" status
            if valid_process_line_data:
                upload_inputData_in_DB(valid_process_line_data, project_id)

            # If invalid data exists, send the error file and ask for user confirmation            
            if invalid_data:
                error_file_name = os.path.basename(error_file_path)
                error_file_url = reverse('download_error_file', args=[error_file_name])  # A dedicated endpoint for file download
                # Return JSON metadata with the download URL
                return JsonResponse({
                    'valid_data_with_error': True,
                    'error_file_url': error_file_url,
                    'success': 'Partial valid data uploaded. Download the error file.',
                }, status=200)
                        
            # If all data is valid, proceed directly to the calculation stage                    
            status_ok, valid_data, updated_count = update_pending_status(project_id)     

            if not status_ok:
                return JsonResponse({'error': 'Failed to confirm uploaded data.'}, status=500)

            if updated_count == 0:
                return JsonResponse({'error': 'No valid uploaded data was available to process.'}, status=400)

            calculation_result, result_counts = run_project_calculations(project_id)
            return JsonResponse({
                'success': 'Input file processed and calculations completed successfully.',
                'project_id': project_id,
                'confirmed_rows': updated_count,
                'result_counts': result_counts,
                'calculation_result': calculation_result,
            })           
        
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
    branch_rows = list(
        PowerDistributionBranch.objects.filter(distribution__line__proj_id=project_id)
        .select_related('distribution__line')
        .order_by('distribution__line__line_id', 'branch_index')
    )

    line_results = []
    for calculation in calculations:
        line = calculation.line
        line_results.append({
            'calculation': calculation,
            'line': line,
            'selected_tracer': getattr(line, 'selected_tracer_result', None),
            'alternate_tracers': list(line.alternate_tracer_results.all()),
            'branch_count': len(getattr(line.power_distribution_result, 'branches').all()) if hasattr(line, 'power_distribution_result') else 0,
        })

    summary = {
        'calculated_lines': len(line_results),
        'total_circuits': sum(item['calculation'].total_circuits for item in line_results),
        'total_power_kw': sum(item['calculation'].total_power_consumption for item in line_results) / 1000 if line_results else 0,
        'total_tracer_length': sum(item['calculation'].total_tracer_length for item in line_results),
        'branch_count': len(branch_rows),
    }
    return {
        'line_results': line_results,
        'branch_rows': branch_rows,
        'summary': summary,
    }


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
    summary = {
        'consolidated_item_count': len(consolidated_items),
        'line_group_count': len(line_groups),
        'tracer_total': consolidated_lookup.get('TRACER', 0),
        'mcb_total': consolidated_lookup.get('MCB', 0),
        'junction_box_total': consolidated_lookup.get('JB3PH', 0) + consolidated_lookup.get('JB1PH', 0),
    }
    return {
        'consolidated_items': consolidated_items,
        'line_groups': line_groups,
        'summary': summary,
    }


def _build_sld_workspace_data(project_id):
    payload = build_project_sld_payload(project_id)
    layout = get_project_sld_layout(project_id, payload=payload)
    validation = validate_project_sld_payload(project_id, payload=payload)
    nodes = payload['nodes']
    edges = payload['edges']
    line_groups = payload['line_groups']

    component_type_counts = Counter(node['component_type'] for node in nodes)
    component_summary = []
    for component_type, count in sorted(component_type_counts.items()):
        sample_node = next((node for node in nodes if node['component_type'] == component_type), {})
        component_summary.append({
            'component_type': component_type,
            'display_name': sample_node.get('display_name', component_type),
            'count': count,
        })

    line_summary = []
    for group in line_groups:
        line_id = group['line_id']
        component_count = sum(1 for node in nodes if line_id in node.get('line_ids', []))
        edge_count = sum(1 for edge in edges if line_id in edge.get('line_ids', []))
        line_summary.append({
            'line_id': line_id,
            'branch_indices': group['branch_indices'],
            'branch_count': len(group['branch_indices']),
            'component_count': component_count,
            'edge_count': edge_count,
        })

    summary = {
        'line_group_count': len(line_groups),
        'branch_count': payload['meta']['branch_count'],
        'node_count': payload['meta']['node_count'],
        'edge_count': payload['meta']['edge_count'],
    }
    return {
        'payload': payload,
        'layout': layout,
        'validation': validation,
        'component_summary': component_summary,
        'line_summary': line_summary,
        'summary': summary,
    }


def boq_view(request):
    project_id = request.GET.get('project_id')
    context = _get_project_workspace_context(request, project_id)
    consolidated_items = []
    line_groups = []
    selected_line_group = None
    selected_line_query = (request.GET.get('line_lookup') or request.GET.get('line_id') or '').strip()
    selected_line_error = ''
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

        if len(line_groups) == 1 and not selected_line_query:
            selected_line_group = line_groups[0]
            selected_line_query = selected_line_group['line'].line_id
        elif selected_line_query:
            selected_line_group = next(
                (
                    group
                    for group in line_groups
                    if group['line'] and group['line'].line_id.casefold() == selected_line_query.casefold()
                ),
                None,
            )
            if selected_line_group is None:
                selected_line_error = f"No BOQ line items were found for line ID '{selected_line_query}'."

    context.update({
        'consolidated_items': consolidated_items,
        'line_groups': line_groups,
        'boq_summary': summary,
        'has_boq': bool(consolidated_items or line_groups),
        'selected_line_group': selected_line_group,
        'selected_line_query': selected_line_query,
        'selected_line_error': selected_line_error,
        'show_line_dropdown': len(line_groups) < BOQ_LINE_DROPDOWN_LIMIT,
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
    }

    if project_id and context['project_setup']:
        sld_data = _build_sld_workspace_data(project_id)

    context.update({
        'sld_summary': sld_data['summary'],
        'sld_layout': sld_data['layout'],
        'sld_validation': sld_data['validation'],
        'sld_component_summary': sld_data['component_summary'],
        'sld_line_summary': sld_data['line_summary'],
        'has_sld_payload': bool(sld_data['summary']['node_count']),
        'sld_payload_url': reverse('sld_payload_view'),
        'sld_layout_url': reverse('sld_layout_view'),
        'sld_layout_reset_url': reverse('sld_layout_reset_view'),
        'sld_validation_url': reverse('sld_validation_view'),
    })
    return render(request, 'eht/partials/sld_tab.html', context)


def sld_payload_view(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to load SLD data.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    sld_data = _build_sld_workspace_data(project_id)
    if not sld_data['summary']['node_count']:
        return JsonResponse({'error': 'No stored power-distribution data is available for this project yet.'}, status=400)

    return JsonResponse(sld_data['payload'])


def sld_validation_view(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'Project ID is required to validate the SLD.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    sld_data = _build_sld_workspace_data(project_id)
    if not sld_data['summary']['node_count']:
        return JsonResponse({'error': 'No stored power-distribution data is available for this project yet.'}, status=400)

    return JsonResponse(sld_data['validation'])


def sld_layout_view(request):
    project_id = request.GET.get('project_id') if request.method == 'GET' else request.POST.get('project_id')
    if not project_id and request.method == 'POST':
        try:
            body = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            body = {}
        project_id = body.get('project_id')

    if not project_id:
        return JsonResponse({'error': 'Project ID is required to load or save the SLD layout.'}, status=400)

    context = _get_project_workspace_context(request, project_id)
    if not context['project_setup']:
        return JsonResponse({'error': 'Project setup has not been saved for this project yet.'}, status=400)

    sld_data = _build_sld_workspace_data(project_id)
    if not sld_data['summary']['node_count']:
        return JsonResponse({'error': 'No stored power-distribution data is available for this project yet.'}, status=400)

    if request.method == 'GET':
        return JsonResponse(sld_data['layout'])

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid layout payload.'}, status=400)

    save_summary = save_project_sld_layout(
        project_id,
        positions=body.get('positions', {}),
        payload=sld_data['payload'],
    )
    refreshed_layout = get_project_sld_layout(project_id, payload=sld_data['payload'])
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
            'Line ID': branch.distribution.line.line_id,
            'Branch Index': branch.branch_index,
            'Branch Type': branch.branch_type,
            'Connected To': branch.connected_to,
            'Circuit Count': branch.circuit_count,
            'Cable Length DB to JB': branch.cable_length_db_to_jb,
            'Cable Length JB to JB': branch.cable_length_jb_to_jb,
            'Tagged Components': str(branch.tagged_components),
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
        project_id = request.POST.get('project_id')
        if not project_id:
            return JsonResponse({'error': 'Project ID is required.'}, status=400)

        try:            
            status_ok, valid_data, updated_count = update_pending_status(project_id)
            if not status_ok:
                return JsonResponse({'error': 'Failed to confirm valid uploaded data.'}, status=500)

            if updated_count == 0:
                return JsonResponse({'error': 'No valid uploaded data is pending confirmation.'}, status=400)

            calculation_result, result_counts = run_project_calculations(project_id)
            logger.info(
                "Project ID: %s - Pending rows confirmed and calculations completed for %s row(s).",
                project_id,
                updated_count,
            )
            return JsonResponse({
                'success': 'Valid data confirmed and calculations completed successfully.',
                'project_id': project_id,
                'confirmed_rows': updated_count,
                'result_counts': result_counts,
                'calculation_result': calculation_result,
            }, status=200)
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
    try:
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
        HeatTracingInput.objects.bulk_create(valid_rows)

    except Exception as e:
        logger.error("Failed to upload input data for project %s: %s", project_id, str(e), exc_info=True)

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

#  generate SLD
def sld(request):      
    return render(request, 'eht/sld.html', {})
