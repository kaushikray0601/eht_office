import json
import logging
import math
import os
from collections import Counter
from io import BytesIO
from pathlib import Path
from time import perf_counter

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
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
from .cold_cable import size_cold_cables_for_project
from .forms import PROJECT_FORM_COLD_CABLE_DEFAULTS, ProjectDataForm
from .data_service import clear_project_workspace_data
from .manual_renderer import render_markdown_manual
from .models import (
    AlternateTracer,
    BOQ,
    ColdCableResult,
    DEFAULT_PROJECT_ID,
    HeatLoss,
    HeatTracingInput,
    ManagedProject,
    PowerDistributionBranch,
    ProcessLineCalculation,
    ProjectData,
    SelectedMIHeater,
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

MI_MVP_RESULT_BASIS_NOTES = [
    'Automatic MI fallback is used only when SR catalogue temperature limits are exceeded.',
    'Each MI heater set is treated as an independently protected branch with its own breaker.',
    'Single-point/shared temperature sensing is assumed for this MVP output; final RTD placement remains an engineering review item.',
    'MI T-class status remains design-review evidence, not a calculated sheath-temperature approval.',
    'Physical JB terminal capacity and panel coordination remain deferred; cold-cable sizing results are now shown separately for engineering review.',
]

PROJECT_DATA_TEMPLATE_FIELDS = [
    'min_amb_t',
    'max_amb_t',
    'startup_t',
    'area_class',
    'temp_class',
    'voltage',
    'eht_db_fault_rating_ka',
    'max_cb_size',
    'restrict_cb_current',
    'vendor',
    'spiral_wrap_allowed',
    'spiral_factor',
    'sr_parallel_run_basis',
    'sr_max_parallel_runs',
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
    'cable_standard',
    'cable_conductor_material',
    'cable_insulation_type',
    'cable_install_method',
    'cable_grouping_derating',
    'min_cold_cable_size_mm2',
    'mcb_curve',
    'rcd_provided',
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
    return render(request, 'eht/landing.html')


def design_guide_view(request):
    manual_path = Path(settings.BASE_DIR) / 'NOTES' / 'CALCULATION_MODULE_USER_MANUAL.md'
    try:
        manual_source = manual_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        manual_source = '# Calculation Module User Manual\n\nThe calculation module manual has not been generated yet.'
    rendered = render_markdown_manual(manual_source)
    return render(request, 'eht/design_guide.html', {
        'manual_html': mark_safe(rendered.html),
        'manual_toc': rendered.toc,
    })


def _verification_report_projects(user):
    available_project_ids = ManagedProject.available_to_user(user).exclude(
        proj_id__iexact=DEFAULT_PROJECT_ID
    ).values_list('proj_id', flat=True)
    return ProjectData.objects.filter(proj_id__in=available_project_ids).order_by('proj_id')


def verification_report_view(request):
    project_id = request.GET.get('project_id', '').strip()
    line_uid   = request.GET.get('line_uid',   '').strip()

    projects = _verification_report_projects(getattr(request, 'user', None))
    ctx = {
        'projects':            projects,
        'selected_project_id': project_id,
        'selected_line_uid':   line_uid,
        'lines':               [],
        'line':                None,
        'project':             None,
        'report':              None,
        'error':               None,
    }

    if not project_id:
        return render(request, 'eht/verification_report.html', ctx)

    project = projects.filter(proj_id=project_id).first()
    if project is None:
        ctx['selected_project_id'] = ''
        ctx['error'] = 'Project not found or unavailable.'
        return render(request, 'eht/verification_report.html', ctx)
    ctx['project'] = project

    lines = HeatTracingInput.objects.filter(
        proj_id=project_id, status='confirmed', is_deleted=False
    ).order_by('line_id')
    ctx['lines'] = lines

    if not line_uid:
        return render(request, 'eht/verification_report.html', ctx)

    try:
        line_uid_int = int(line_uid)
    except (TypeError, ValueError):
        line_uid_int = None
    line = lines.filter(uid=line_uid_int).first() if line_uid_int is not None else None
    if line is None:
        ctx['error'] = 'Line or project not found.'
        return render(request, 'eht/verification_report.html', ctx)

    ctx['line']    = line
    ctx['project'] = project

    hl   = getattr(line, 'heat_loss_result',          None)
    st   = getattr(line, 'selected_tracer_result',    None)
    calc = getattr(line, 'process_line_calculation',  None)
    mi   = getattr(line, 'selected_mi_heater_result', None)
    cc_results = list(ColdCableResult.objects.filter(
        project_id=project_id, line_uid=str(line.uid)
    ).order_by('branch_index'))

    import math
    from .models import AlternateTracer, ColdCableCatalogue

    def f2(v, n=2):
        try:
            return round(float(v), n)
        except (TypeError, ValueError):
            return None

    def fmt(v, n=2, suffix=''):
        r = f2(v, n)
        return f'{r}{suffix}' if r is not None else '—'

    alt_tracers = list(AlternateTracer.objects.filter(line=line).order_by('option_rank'))

    # ── shared inputs ──────────────────────────────────────────
    maint_t      = f2(line.maint_temp)
    min_amb      = f2(project.min_amb_t)
    ins_thick_mm = f2(line.insul_thick)
    ins_thick_m  = round(ins_thick_mm / 1000, 5) if ins_thick_mm else None
    pipe_size_in = f2(line.line_size)
    proj_vendor  = getattr(project, 'vendor',              '—')
    proj_wind    = getattr(project, 'wind_speed',          None)
    proj_cb_max  = getattr(project, 'max_cb_size',         None)
    proj_cb_load = getattr(project, 'restrict_cb_current', None)
    proj_voltage = getattr(project, 'voltage',             None)

    # ── VD optimisation baseline comparison helper ─────────────
    def _vd_split_comparison(cc):
        if not cc.optimization_run or not cc.cable_4c_catalogue or not cc.cable_3c_catalogue:
            return None
        try:
            I      = float(cc.per_circuit_operating_current_a or 0)
            L_4c   = float(cc.length_4c_m or 0)
            L_3c   = float(cc.length_3c_m or 0)
            N_out  = int(cc.circuit_count or 1)
            V_nom  = float(proj_voltage or 230)
            vd_all_v = V_nom * float(cc.vd_allowable_pct or 5) / 100
            k_tot  = float(cc.k_total or 1.0)
            alpha  = 0.00393
            if not I or not L_4c or not L_3c:
                return None
            cat4c = list(ColdCableCatalogue.objects.filter(
                cable_standard=cc.cable_4c_catalogue.cable_standard,
                conductor_material=cc.cable_4c_catalogue.conductor_material,
                insulation_type=cc.cable_4c_catalogue.insulation_type,
                installation_method=cc.cable_4c_catalogue.installation_method,
                core_count=3, is_validated=True,
            ).order_by('conductor_size_mm2'))
            cat3c = list(ColdCableCatalogue.objects.filter(
                cable_standard=cc.cable_3c_catalogue.cable_standard,
                conductor_material=cc.cable_3c_catalogue.conductor_material,
                insulation_type=cc.cable_3c_catalogue.insulation_type,
                installation_method=cc.cable_3c_catalogue.installation_method,
                core_count=3, is_validated=True,
            ).order_by('conductor_size_mm2'))
            T4 = float(cc.cable_4c_catalogue.max_conductor_temp_c or 90)
            T3 = float(cc.cable_3c_catalogue.max_conductor_temp_c or 90)

            def R_op(row, T_op):
                return float(row.resistance_mohm_per_m) / 1000 * (1 + alpha * (T_op - 20))

            opt_vol = float(cc.conductor_volume_proxy or 0)
            baselines = []
            for label, f4, f3 in [('25/75', 0.25, 0.75), ('50/50', 0.50, 0.50), ('75/25', 0.75, 0.25)]:
                b4 = vd_all_v * f4
                b3 = vd_all_v * f3
                feeder_current = float(cc.per_circuit_operating_current_a or 0) * max(1, int(cc.circuit_count or 1))
                s4 = next((r for r in cat4c if r.ampacity_a * k_tot >= float(cc.breaker_size_a or feeder_current)
                            and 2 * feeder_current * R_op(r, T4) * L_4c <= b4), None)
                s3 = next((r for r in cat3c if r.ampacity_a * k_tot >= I
                            and 2 * I * R_op(r, T3) * L_3c <= b3), None)
                if s4 and s3:
                    vol = 3 * s4.conductor_size_mm2 * L_4c + N_out * 3 * s3.conductor_size_mm2 * L_3c
                    saving = round((vol - opt_vol) / vol * 100, 1) if vol > 0 else 0
                    baselines.append({'label': label, 'size_4c': s4.conductor_size_mm2,
                                      'size_3c': s3.conductor_size_mm2,
                                      'volume': round(vol, 0), 'saving_pct': saving})
                else:
                    baselines.append({'label': label, 'feasible': False})
            return {'opt_vol': round(opt_vol, 0), 'baselines': baselines}
        except Exception:
            return None

    # ── Cold-cable sub-steps builder ───────────────────────────
    def _cc_steps(cc, step_start):
        result = []
        n      = step_start
        I      = f2(cc.per_circuit_operating_current_a, 3)
        L3     = f2(cc.length_3c_m, 1)
        L4     = f2(cc.length_4c_m, 1)
        k_t    = f2(cc.k_temp, 4)
        k_g    = f2(cc.k_group, 3)
        k_tot  = f2(cc.k_total, 4)
        t_site = f2(cc.site_ambient_temp_c, 1)
        t_ref  = f2(cc.catalogue_temp_ref_c, 1)
        cat4   = cc.cable_4c_catalogue
        cat3   = cc.cable_3c_catalogue
        T_max4 = float(cat4.max_conductor_temp_c) if cat4 else 90.0
        T_max3 = float(cat3.max_conductor_temp_c) if cat3 else 90.0
        c4     = f2(cc.cable_4c_size_mm2, 1)
        c3     = f2(cc.cable_3c_size_mm2, 1)
        vd4    = f2(cc.cable_4c_vd_pct, 2)
        vd3    = f2(cc.cable_3c_vd_pct, 2)
        vd_tot = f2(cc.vd_total_pct, 2)
        v_end  = f2(cc.load_end_voltage_v, 1)
        vd_all = f2(cc.vd_allowable_pct, 1)
        brk    = f2(cc.breaker_size_a, 0)
        is_3ph = bool(cc.length_4c_m and c4)
        alpha  = 0.00393

        # E-step helper
        def _es(num_offset, title, **kwargs):
            return dict(section='E', section_color='purple',
                        num=f'E{n + num_offset}', num_color='purple',
                        title=title, available=True, **kwargs)

        # E1: Ampacity — Temperature Derating
        T_ref_use = T_max4 if is_3ph else T_max3
        subs_kt = (
            f'K_temp = sqrt(({T_ref_use} − {t_site}) / ({T_ref_use} − {t_ref}))\n'
            f'       = sqrt({round(T_ref_use - (t_site or 0), 1)} / {round(T_ref_use - (t_ref or 30), 1)})\n'
            f'       = {k_t}'
        ) if k_t else f'K_temp = {k_t}'
        result.append(_es(0,
            'Ampacity — Temperature Derating Factor K_temp',
            symbolic='K_temp = √( (T_max_conductor − T_site) / (T_max_conductor − T_ref_catalogue) )',
            substitution=subs_kt,
            result_value=fmt(k_t, 4),
            result_unit='(≤ 1.0; reduces ampacity for site ambient above catalogue reference)',
            result_label=(
                f'T_max_conductor = {T_ref_use} °C (insulation thermal limit)  ·  '
                f'T_site = {t_site} °C (project max ambient)  ·  T_ref = {t_ref} °C (catalogue publish condition)'
            ),
            evidence=[
                {'icon': 'bi-thermometer', 'label': f'Site max ambient = {t_site} °C  ·  Catalogue reference = {t_ref} °C'},
            ],
            std_refs=[{'label': 'IEC 60364-5-52 Table B.52.14 — Temperature correction factors for ampacity'}],
        ))
        n += 1

        # E2: Ampacity — Grouping Derating and Cable Selection
        amp4 = f2(cc.cable_4c_ampacity_derated_a, 2)
        amp3 = f2(cc.cable_3c_ampacity_derated_a, 2)
        m4   = f2(cc.cable_4c_ampacity_margin_pct, 1)
        m3   = f2(cc.cable_3c_ampacity_margin_pct, 1)
        subs_amp = (
            f'K_total = K_temp × K_group = {k_t} × {k_g} = {k_tot}\n'
            f'A_available = A_catalogue × K_total\n\n'
            + (f'Feeder Cable {c4} mm²: A_available = {amp4} A  (margin {m4}% above breaker/group-current basis)\n' if is_3ph else '')
            + f'Branch Cable {c3} mm²: A_available = {amp3} A  (margin {m3}% above breaker/branch-current basis)'
        )
        result.append(_es(0,
            'Ampacity — Grouping Derating and Minimum Size Selection',
            symbolic='A_available = A_catalogue × K_temp × K_group  ≥  I_operating',
            substitution=subs_amp,
            result_value=(f'{c3} mm² Branch Cable' + (f'  +  {c4} mm² Feeder Cable' if is_3ph else '')),
            result_unit='',
            result_label=(
                f'Sized on operating current {I} A/circuit (not starting current — MCB already handles starting).  '
                f'Minimum standard cable size selected with sufficient derated ampacity margin.'
            ),
            evidence=[
                {'icon': 'bi-sliders', 'label': f'K_group = {k_g}  (project cable grouping/spacing factor, range 0.25–1.0)'},
                {'icon': 'bi-info-circle', 'label': 'Cold cables sized for continuous operating current. Starting (cold-start) current is transient; MCB selection accounts for it separately.'},
            ],
            std_refs=[
                {'label': 'IEC 60364-5-52 — Cable grouping derating factors'},
                {'label': 'IEC 60502-1 — Catalogue ampacity data source'},
            ],
        ))
        n += 1

        # E3: Feeder Cable Voltage Drop (distribution branches only)
        if is_3ph and cat4:
            T_op4 = f2(cc.cable_4c_conductor_temp_c) or T_max4
            R20_4 = f2(cat4.resistance_mohm_per_m, 3)
            R_op4 = round(float(R20_4 or 0) / 1000 * (1 + alpha * (T_op4 - 20)), 6) if R20_4 else None
            vd4_v = f2(cc.cable_4c_vd_v, 2)
            subs_vd4 = (
                f'R(T) = R_20 × (1 + α × (T_op − 20))\n'
                f'     = {R20_4} mΩ/m × (1 + 0.00393 × ({T_op4} − 20))\n'
                f'     = {round(R_op4 * 1000, 4) if R_op4 else "?"} mΩ/m  at T_op = {T_op4} °C\n\n'
                f'VD_feeder = 2 × I_group × R(T) × L_feeder\n'
                f'          = 2 × ({I} × {cc.circuit_count}) × {round(R_op4, 6) if R_op4 else "?"} × {L4}\n'
                f'      = {vd4_v} V  ({vd4}% of {fmt(proj_voltage, 0)} V)'
            )
            result.append(_es(0,
                f'Feeder Cable — Voltage Drop  [{c4} mm² Cu, {L4} m]',
                symbolic='VD_feeder = 2 · I_group · R(T) · L     [single-phase, PF = 1.0]',
                substitution=subs_vd4,
                result_value=f'{vd4_v} V  ({vd4}%)',
                result_unit='',
                result_label=(
                    f'Single-phase factor 2 covers phase and neutral conductors. '
                    f'VD_feeder uses the combined downstream group operating current.'
                ),
                evidence=[
                    {'icon': 'bi-lightning-charge', 'label': f'Conductor operating temp T_op = {T_op4} °C  ·  α_Cu = 0.00393 /°C  (IEC 60228)'},
                    {'icon': 'bi-rulers', 'label': f'Trunk length = {L4} m  ·  Length basis: {cc.length_basis}'},
                ],
                std_refs=[
                    {'label': 'IEC 60228 — Conductor resistance-temperature correction'},
                    {'label': 'IEC 60364-5-52 — VD formula, EHT loads are purely resistive (PF = 1.0)'},
                ],
            ))
            n += 1

        # E4: Branch Cable Voltage Drop
        if cat3:
            T_op3 = f2(cc.cable_3c_conductor_temp_c) or T_max3
            R20_3 = f2(cat3.resistance_mohm_per_m, 3)
            R_op3 = round(float(R20_3 or 0) / 1000 * (1 + alpha * (T_op3 - 20)), 6) if R20_3 else None
            vd3_v = f2(cc.cable_3c_vd_v, 2)
            subs_vd3 = (
                f'R(T) = {R20_3} mΩ/m × (1 + 0.00393 × ({T_op3} − 20))\n'
                f'     = {round(R_op3 * 1000, 4) if R_op3 else "?"} mΩ/m  at T_op = {T_op3} °C\n\n'
                f'VD_branch = 2 × I_branch × R(T) × L_branch\n'
                f'      = 2 × {I} × {round(R_op3, 6) if R_op3 else "?"} × {L3}\n'
                f'      = {vd3_v} V  ({vd3}% of {fmt(proj_voltage, 0)} V)\n\n'
                f'Total path VD = {vd4 or 0}% (Feeder) + {vd3}% (Branch) = {vd_tot}%  ≤  {vd_all}% allowable'
            )
            result.append(_es(0,
                f'Branch Cable — Voltage Drop  [{c3} mm² Cu, {L3} m per branch]',
                symbolic='VD_branch = 2 · I_branch · R(T) · L     [single-phase; factor 2 = phase + neutral]',
                substitution=subs_vd3,
                result_value=f'Total path VD = {vd_tot}%',
                result_unit=f'(allowable: {vd_all}%)  →  {cc.vd_status.upper()}',
                result_label=f'Load-end voltage = {v_end} V  (supply {fmt(proj_voltage, 0)} V minus all cable VD)',
                evidence=[
                    {'icon': 'bi-lightning-charge', 'label': f'T_op = {T_op3} °C  ·  {cc.circuit_count} outgoing circuit(s)'},
                    {'icon': 'bi-rulers', 'label': f'Outgoing length = {L3} m/circuit  ·  Length basis: {cc.length_basis}'},
                ],
                std_refs=[{'label': 'IEC 60228 — Conductor resistance-temperature correction'}],
            ))
            n += 1

        # E5: VD Optimisation (distribution branches only)
        if is_3ph and cc.optimization_run:
            cmp     = _vd_split_comparison(cc)
            opt_vol = f2(cc.conductor_volume_proxy, 0)
            mass_mt = f2(cc.conductor_mass_total_mt, 4)
            cost_eq = f'3 × {c4} mm² × {L4} m  +  {cc.circuit_count} × 3 × {c3} mm² × {L3} m  =  {opt_vol} mm²·m'
            savings_lines = []
            if cmp and cmp.get('baselines'):
                for b in cmp['baselines']:
                    if b.get('feasible') is False:
                        savings_lines.append(f"  {b['label']} split: no feasible solution at this VD budget")
                    else:
                        sp = b['saving_pct']
                        dir_note = f'optimised uses {sp}% less material' if sp > 0 else f'optimised is {abs(sp)}% heavier (but still global minimum)'
                        savings_lines.append(
                            f"  {b['label']} split → {b['size_4c']} mm² Feeder + {b['size_3c']} mm² Branch = {b['volume']} mm²·m  ({dir_note})"
                        )
            subs_opt = cost_eq + ('\n\nComparison vs fixed VD-split baselines:\n' + '\n'.join(savings_lines) if savings_lines else '')
            result.append(_es(0,
                'Feeder/Branch VD Optimisation — Minimum Conductor Tonnage',
                symbolic=(
                    'minimise { 3·A_feeder·L_feeder + Σ(3·A_branch·L_branch) }\n'
                    'subject to:  VD_feeder + VD_branch ≤ VD_allowable  and  ampacity ≥ upstream MCB rating'
                ),
                substitution=subs_opt,
                result_value=f'{mass_mt} metric tonnes',
                result_unit='conductor (this branch)',
                result_label=(
                    f'Optimised solution: {c4} mm² Feeder + {c3} mm² Branch.  '
                    'The engine systematically searches every valid Feeder/Branch catalogue pair and selects the minimum-mass '
                    'combination, allowing the voltage drop to split across the two cable segments in whatever ratio produces '
                    'the lowest total conductor volume — not a fixed proportional split.'
                ),
                evidence=[
                    {'icon': 'bi-graph-down', 'label': 'Nested discrete search: for each ampacity-qualified Feeder size, find smallest qualifying Branch size; select pair with lowest conductor volume proxy'},
                    {'icon': 'bi-info-circle', 'label': 'Fixed-split (25/50/75) baselines shown above constrain VD allocation arbitrarily. Optimiser finds true minimum-mass solution at any feasible split.'},
                ],
                std_refs=[],
            ))
            n += 1

        # E6: L-PE Fault Loop
        if cat3:
            i_f3  = f2(cc.fault_current_l_pe_a, 1)
            mcb_k3= {'B': 3, 'C': 5, 'D': 10}.get(cc.mcb_curve, 5)
            thr3  = round(float(brk or 0) * mcb_k3, 1) if brk else None
            st3   = cc.fault_loop_status
            rcd  = 'RCD earth-fault protection is provided — MCB check is secondary verification.' if cc.rcd_provided else 'No RCD provided — MCB is sole earth-fault protection; hard sizing gate.'
            basis = cc.fault_loop_basis or {}
            result.append(_es(0,
                f'L-PE Fault Loop Check  [{st3.upper()}]',
                symbolic='I_fault = V_phase / (Z_source + R_phase_feeder + R_PE_feeder + R_phase_branch + R_PE_branch)',
                substitution=(
                    f'Z_source = {f2(basis.get("source_impedance_ohm"), 6)} Ω from three-phase EHT DB fault rating {basis.get("eht_db_fault_rating_ka", "—")} kA\n'
                    f'I_fault = {fmt(proj_voltage, 0)} V / Z_loop\n'
                    f'        = {i_f3} A  vs threshold {thr3} A  →  {st3.upper()}\n\n'
                    f'{rcd}'
                ),
                result_value=f'{i_f3} A',
                result_unit=f'vs {thr3} A  →  {st3.upper()}',
                result_label=rcd,
                evidence=[
                    {'icon': 'bi-shield-check', 'label': 'Fault loop includes project source impedance plus Feeder/Branch phase and PE conductor resistance.'},
                ],
                std_refs=[
                    {'label': 'IEC 60364-4-41 — Earth fault disconnection time, TN systems'},
                    {'label': 'IEC 60364-4-41 — RCD/earth-fault protective devices as part of automatic disconnection of supply'},
                ],
            ))
            n += 1

        # E8: Branch Summary
        result.append(_es(0,
            f'Branch {cc.branch_index} Summary — Status: {cc.sizing_status.upper()}',
            table=[
                ('Branch type',            'Distribution JB (Feeder + Branch Cables)' if is_3ph else 'Direct single-phase Feeder Cable'),
                ('Feeder Cable',           f'{c4} mm² Cu · {L4} m · {vd4}% VD' if is_3ph else 'N/A'),
                ('Branch Cable',           f'{c3} mm² Cu · {L3} m/branch · {vd3}% VD · L-PE loop: {cc.fault_loop_status}'),
                ('Total path VD',          f'{vd_tot}%  (allowable: {vd_all}%)  →  {cc.vd_status.upper()}'),
                ('Load-end voltage',       f'{v_end} V'),
                ('Operating current',      f'{I} A/circuit  ·  Breaker: {brk} A  ·  MCB Type {cc.mcb_curve}'),
                ('Conductor mass',         f'{f2(cc.conductor_mass_total_mt, 4)} metric tonnes'),
                ('Length basis',           cc.length_basis),
                ('RCD provided',           'Yes' if cc.rcd_provided else 'No — MCB earth loop is hard sizing gate'),
                ('Review notes',           '; '.join(cc.review_notes) if cc.review_notes else 'None'),
            ],
            evidence=[], std_refs=[],
        ))
        return result

    steps = []

    # ── SECTION A: INPUT DATA ──────────────────────────────────
    steps.append({
        'section': 'A', 'section_color': 'blue', 'num': 1, 'num_color': '',
        'title': 'Input Data Summary', 'available': True,
        'table': [
            ('Line ID',               line.line_id),
            ('Service Type',          line.service_type),
            ('Pipe Nominal Size',      f'{pipe_size_in}″  NPS'),
            ('Pipe Outside Diameter',  f'{fmt(hl.pipe_size_mm if hl else None, 1)} mm  (ASME B36.10M lookup)' if hl else '—'),
            ('Pipe Length',           f'{fmt(line.line_length, 1)} m'),
            ('Insulation Material',   line.ins_mat_type),
            ('Insulation Thickness',  f'{fmt(line.insul_thick, 1)} mm  ({fmt(ins_thick_m, 4)} m)'),
            ('Maintain Temperature',  f'{fmt(maint_t, 1)} °C'),
            ('Operating Temperature', f'{fmt(line.oper_temp, 1)} °C'),
            ('Design Temperature',    f'{fmt(line.design_temp, 1)} °C'),
            ('Min Ambient (Project)', f'{fmt(min_amb, 1)} °C'),
            ('Max Ambient (Project)', f'{fmt(project.max_amb_t, 1)} °C'),
            ('Accessories',           f'{line.valve_qty} valve(s) · {line.flange_qty} flange(s) · {line.support_qty} support(s)'),
            ('Project vendor',        str(proj_vendor)),
            ('System voltage',        f'{fmt(proj_voltage, 0)} V'),
        ],
        'evidence': [{'icon': 'bi-table', 'label': 'Confirmed line list upload'},
                     {'icon': 'bi-gear',  'label': 'Project setup'}],
        'std_refs': [],
    })

    # ── SECTION B: THERMAL ────────────────────────────────────
    if hl:
        pipe_od_mm = f2(hl.pipe_size_mm, 1)
        pipe_od_m  = round(pipe_od_mm / 1000, 5) if pipe_od_mm else None
        steps.append({
            'section': 'B', 'section_color': 'amber', 'num': 2, 'num_color': 'amber',
            'title': 'Pipe Outside Diameter Lookup', 'available': True,
            'symbolic':     'D = ASME_B36_table.lookup(Nominal_Pipe_Size)',
            'substitution': f'D = lookup({pipe_size_in}″ NPS)  →  {pipe_od_mm} mm  (= {pipe_od_m} m)',
            'result_value': fmt(pipe_od_mm, 1), 'result_unit': 'mm',
            'result_label': 'Pipe outside diameter D used in the heat-loss geometry factor ln((2t+D)/D)',
            'evidence': [{'icon': 'bi-book', 'label': 'ASME B36.10M pipe table stored in application database'}],
            'std_refs': [{'label': 'ASME B36.10M — Welded and Seamless Wrought Steel Pipe'}],
        })
    else:
        steps.append({'section': 'B', 'section_color': 'amber', 'num': 2, 'num_color': 'amber',
                      'title': 'Pipe Outside Diameter Lookup', 'available': False})

    if hl:
        basis  = hl.conductivity_basis or {}
        t_eval = f2(basis.get('evaluation_temperature_c'), 2)
        method_raw   = basis.get('effective_method_label', 'Mean insulation temperature')
        method_clean = method_raw.replace(' (recommended)', '').replace(' (Recommended)', '').strip()
        steps.append({
            'section': 'B', 'section_color': 'amber', 'num': 3, 'num_color': 'amber',
            'title': 'Mean Insulation Temperature', 'available': True,
            'symbolic':     'T_mean = (T_maint + T_amb,min) / 2',
            'substitution': f'T_mean = ({maint_t} + ({min_amb})) / 2',
            'result_value': fmt(t_eval, 2), 'result_unit': '°C',
            'result_label': (
                'T_mean approximates the average temperature across the insulation annulus, '
                'treating the inner face at T_maint and outer face at T_amb. '
                'Insulation conductivity k is evaluated at this temperature.'
            ),
            'evidence': [{'icon': 'bi-gear', 'label': f'Conductivity evaluation method: {method_clean}  (project setting)'}],
            'std_refs': [{'label': 'IEC/IEEE 62395-1 — Mean insulation temperature method for conductivity evaluation'}],
        })
    else:
        steps.append({'section': 'B', 'section_color': 'amber', 'num': 3, 'num_color': 'amber',
                      'title': 'Mean Insulation Temperature', 'available': False})

    if hl:
        basis  = hl.conductivity_basis or {}
        coeffs = basis.get('coefficients', {})
        A_k = f2(coeffs.get('K_factor_A'), 8)
        B_k = f2(coeffs.get('K_factor_B'), 6)
        C_k = f2(coeffs.get('K_factor_C'), 4)
        t_ev = f2(basis.get('evaluation_temperature_c'), 2)
        k    = f2(hl.conductivity, 5)
        subs4 = f'k = {A_k} × {t_ev}² + {B_k} × {t_ev} + {C_k}' if all(x is not None for x in [A_k, B_k, C_k, t_ev]) else '—'
        steps.append({
            'section': 'B', 'section_color': 'amber', 'num': 4, 'num_color': 'amber',
            'title': 'Insulation Conductivity Polynomial Evaluation', 'available': True,
            'symbolic': 'k(T) = A·T² + B·T + C',
            'substitution': subs4,
            'result_value': fmt(k, 5), 'result_unit': 'W/m·K',
            'result_label': f'k at T_mean = {t_ev} °C  ·  Material: {line.ins_mat_type}  ·  A={A_k}, B={B_k}, C={C_k}',
            'evidence': [
                {'icon': 'bi-database', 'label': f'Source: project insulation conductivity database  ({line.ins_mat_type})'},
                {'icon': 'bi-info-circle', 'label': (
                    'The A·T²+B·T+C polynomial is an empirical curve fit to measured thermal conductivity vs temperature data '
                    'for this insulation material. Coefficients A, B, C are not derived from first principles — '
                    'they are regression-calibrated from laboratory measurements per ASTM C177 or EN ISO 8497.'
                )},
            ],
            'std_refs': [
                {'label': 'Empirical polynomial fit — source data per ASTM C177 / EN ISO 8497 thermal conductivity test methods'},
                {'label': 'IEC/IEEE 62395-1 Annex — Polynomial representation of insulation conductivity data'},
            ],
        })
    else:
        steps.append({'section': 'B', 'section_color': 'amber', 'num': 4, 'num_color': 'amber',
                      'title': 'Insulation Conductivity Polynomial', 'available': False})

    if hl and ins_thick_m and (f2(hl.pipe_size_mm, 5) is not None):
        pipe_od_mm2 = f2(hl.pipe_size_mm, 1)
        pipe_d_m    = round(pipe_od_mm2 / 1000, 5) if pipe_od_mm2 else None
        k2  = f2(hl.conductivity, 5)
        bhl = f2(hl.base_heat_loss, 3)
        dT  = round(maint_t - min_amb, 1) if maint_t is not None and min_amb is not None else None
        try:
            ln_arg = f2(math.log((2 * ins_thick_m + pipe_d_m) / pipe_d_m), 4) if pipe_d_m else None
        except Exception:
            ln_arg = None
        subs5 = (
            f'q_base = 2π × {k2} × ({maint_t} − ({min_amb})) / ln((2×{ins_thick_m} + {pipe_d_m}) / {pipe_d_m})\n'
            f'       = 2π × {k2} × {dT} / {ln_arg}'
        ) if all(x is not None for x in [k2, maint_t, min_amb, ins_thick_m, pipe_d_m, ln_arg]) else '—'
        steps.append({
            'section': 'B', 'section_color': 'amber', 'num': 5, 'num_color': 'amber',
            'title': 'Base Heat Loss — Cylindrical Conduction Model', 'available': True,
            'symbolic': 'q_base = 2π · k · (T_maint − T_amb,min) / ln((2t + D) / D)',
            'substitution': subs5,
            'result_value': fmt(bhl, 2), 'result_unit': 'W/m',
            'result_label': (
                f'q_base is steady-state heat loss per metre before safety factor.  '
                f'Variables: t = insulation thickness = {ins_thick_mm} mm ({ins_thick_m} m);  '
                f'D = pipe OD = {pipe_od_mm2} mm ({pipe_d_m} m);  '
                f'ΔT = {dT} °C;  '
                f'ln((2t+D)/D) = {ln_arg} — cylindrical geometry factor.'
            ),
            'evidence': [{'icon': 'bi-thermometer-half', 'label': f't = {ins_thick_mm} mm  ·  D = {pipe_od_mm2} mm  ·  ΔT = {dT} °C'}],
            'std_refs': [
                {'label': 'IEC/IEEE 62395-1 · IEEE 515-2017 §4.3 — Cylindrical insulation steady-state heat loss (Fourier conduction)'},
                {'label': 'ASME B36.10M — Source of pipe OD (D)'},
            ],
        })
    else:
        steps.append({'section': 'B', 'section_color': 'amber', 'num': 5, 'num_color': 'amber',
                      'title': 'Base Heat Loss', 'available': False})

    if hl:
        wind  = f2(hl.wind_correction, 4)
        sf    = f2(hl.heat_loss_sf, 2)
        bhl2  = f2(hl.base_heat_loss, 3)
        dhl   = f2(hl.design_heat_loss, 3)
        wind_add_pct = round((float(wind or 1) - 1) * 100, 1)
        sf_add_pct   = round((float(sf or 1) - 1) * 100, 0)
        subs6 = f'Q_design = {bhl2} × {wind} × {sf}  =  {dhl} W/m' if all(x is not None for x in [bhl2, wind, sf]) else '—'
        steps.append({
            'section': 'B', 'section_color': 'amber', 'num': 6, 'num_color': 'amber',
            'title': 'Wind Correction + Safety Factor → Design Heat Loss', 'available': True,
            'symbolic': 'Q_design = q_base × k_wind × SF',
            'substitution': subs6,
            'result_value': fmt(dhl, 2), 'result_unit': 'W/m',
            'result_label': f'Q_design is the heat duty used for tracer selection.  Wind adds {wind_add_pct}%.  SF adds a further {sf_add_pct:.0f}% design margin.',
            'evidence': [
                {'icon': 'bi-wind', 'label': (
                    f'k_wind = {wind}  ·  Project wind speed = {fmt(proj_wind, 0)} km/h  ·  '
                    'Empirical correction: speeds above 32 km/h add ~1% per mph above that threshold, capped at +20% maximum. '
                    'This is a practical project factor — not a rigorous external convection/radiation model.'
                )},
                {'icon': 'bi-shield-check', 'label': f'Safety factor SF = {sf}  (project setting applied to base heat loss)'},
            ],
            'std_refs': [
                {'label': 'Wind correction: empirical project factor, ceiling 20%. Future: full external HT model per IEC 62395-2.'},
            ],
        })
    else:
        steps.append({'section': 'B', 'section_color': 'amber', 'num': 6, 'num_color': 'amber',
                      'title': 'Wind Correction + Design Heat Loss', 'available': False})

    # ── SECTION C: SR TRACER SELECTION ────────────────────────
    if st:
        A_s  = f2(st.a_coeff, 8)
        B_s  = f2(st.b_coeff, 6)
        C_s  = f2(st.c_coeff, 4)
        vcf  = f2(st.voltage_correction_factor, 4)
        p_out= f2(st.power_output, 3)
        n_sr = st.sr_parallel_run_count or 1
        dhl_v= f2(hl.design_heat_loss, 3) if hl else None
        p_nom_calc = round(A_s * maint_t**2 + B_s * maint_t + C_s, 3) if all(x is not None for x in [A_s, B_s, C_s, maint_t]) else None
        vcf_loss_pct = round((1 - float(vcf or 1)**2) * 100, 1)
        max_sr = getattr(project, 'max_sr_parallel_runs', 4) or 4
        subs7 = (
            f'P_nom = A·T² + B·T + C  (at V_nom, T_maint)\n'
            f'      = {A_s}×{maint_t}² + {B_s}×{maint_t} + {C_s}  =  {p_nom_calc} W/m\n\n'
            f'P_LV  = P_nom × (V_LV / V_nom)²  =  P_nom × VCF²\n'
            f'      = {p_nom_calc} × {vcf}²  ≈  {p_out} W/m  '
            f'({vcf_loss_pct:.1f}% power reduction from nominal due to voltage variation margin)\n\n'
            f'Note: V_LV accounts for supply voltage variation only. '
            f'Cold cable VD reduces terminal voltage further — cross-check performed in Section E.'
        ) if all(x is not None for x in [A_s, B_s, C_s, maint_t, vcf, p_out]) else '—'

        sr_sel_note = (
            f'Engine evaluated 1 to {max_sr} straight runs (project cap). '
            f'Selected {n_sr} run(s) as the minimum satisfying F_duty ≤ allowed limit. '
            f'For each run count, the highest-power qualifying tracers were tried first to minimise run count.'
        )
        alt_note = f'{len(alt_tracers)} alternate tracer(s) also qualified and stored for SLD review.' if alt_tracers else 'No alternate tracers qualified.'

        steps.append({
            'section': 'C', 'section_color': 'green', 'num': 7, 'num_color': 'green',
            'title': f'SR Tracer Power Output at T_maint — {st.tracer_family}  ({n_sr}× straight run)',
            'available': True,
            'symbolic': 'P_LV = P_nom × (V_LV / V_nom)²  where  P_nom = A·T² + B·T + C',
            'substitution': subs7,
            'result_value': fmt(p_out, 2), 'result_unit': 'W/m per run',
            'result_label': (
                f'Low-voltage heat delivery at {fmt(maint_t, 1)} °C.  '
                f'VCF = V_LV/V_nom = {vcf}.  '
                f'Total available: {round(float(p_out or 0) * n_sr, 2)} W/m from {n_sr} run(s).'
            ),
            'evidence': [
                {'icon': 'bi-database',         'label': f'Catalogue: {st.tracer_family}  |  A={A_s}, B={B_s}, C={C_s}'},
                {'icon': 'bi-layers',            'label': sr_sel_note},
                {'icon': 'bi-list-check',        'label': alt_note},
                {'icon': 'bi-exclamation-circle', 'label': (
                    'Voltage note: P_LV uses V_LV (supply LV). Cold cable VD further reduces terminal voltage, '
                    'giving P_actual < P_LV. Adequacy is cross-checked in Section E.'
                )},
            ],
            'std_refs': [
                {'label': 'Vendor polynomial catalogue — power output at T_maint and V_LV scenario'},
                {'label': 'SR cable power scales with V² (purely resistive load, PF = 1.0)'},
            ],
        })

        if dhl_v is not None and p_out is not None and p_out > 0:
            duty_calc = round(dhl_v / (p_out * n_sr), 4)
        else:
            duty_calc = f2(st.spiral_factor, 4)
        subs8 = f'F_duty = {dhl_v} / ({p_out} × {n_sr})  =  {duty_calc}' if all(x is not None for x in [dhl_v, p_out]) else '—'
        constr_warn  = st.sr_constructability_warning or ''
        sr_per_run_m = f2(st.sr_per_run_tracer_length, 1)
        duty_note = (
            f'F_duty = {duty_calc} ≤ 1.0 → full straight run delivers adequate heat with {round((1 - float(duty_calc or 1)) * 100, 1):.1f}% headroom.'
            if duty_calc is not None and duty_calc <= 1.0 else
            f'F_duty = {duty_calc} > 1.0 → spiral installation or additional run required (check project allowance).'
        )
        steps.append({
            'section': 'C', 'section_color': 'green', 'num': 8, 'num_color': 'green',
            'title': 'SR Duty Ratio — Heat Delivery Adequacy Confirmation', 'available': True,
            'symbolic': 'F_duty = Q_design / (P_LV × N_SR)',
            'substitution': subs8,
            'result_value': fmt(duty_calc, 3), 'result_unit': '(pass if ≤ project spiral factor limit)',
            'result_label': duty_note,
            'evidence': [
                {'icon': 'bi-info-circle', 'label': (
                    f'The duty ratio confirms heat delivery adequacy — it is NOT a physical cable-length ratio. '
                    f'For straight tracing (F_duty ≤ 1.0), the full pipe length is always traced regardless of F_duty value: '
                    f'a result of 0.70 means 43% heat-delivery headroom for a full straight run, not that 70% of the cable is active. '
                    f'F_duty > 1.0 is the flag that spiral installation or an additional run is physically necessary.'
                )},
                {'icon': 'bi-arrows-expand', 'label': f'Per-run tracer length: {sr_per_run_m} m  ·  {n_sr} run(s)  ·  Basis: {st.sr_parallel_run_basis or "straight"}'},
            ] + ([{'icon': 'bi-exclamation-triangle', 'label': f'Constructability note: {constr_warn}'}] if constr_warn else []),
            'std_refs': [],
        })
    elif mi:
        mi_heater_pn = mi.heater.part_number if mi.heater else '—'
        mi_family_nm = mi.heater.family.family_name if (mi.heater and mi.heater.family) else '—'
        mi_set_count = mi.selection_basis.get('set_count', 1) if isinstance(mi.selection_basis, dict) else 1
        steps.append({
            'section': 'C', 'section_color': 'green', 'num': 7, 'num_color': 'green',
            'title': 'MI Heater Selection — SR temperature limits exceeded', 'available': True,
            'note': (
                f'SR catalogue temperature limits exceeded for this line. Automatic MI fallback activated. '
                f'Selected: {mi_heater_pn}  ·  Family: {mi_family_nm}  ·  Sets: {mi_set_count}  ·  '
                f'Heated length: {fmt(mi.heated_length_m, 1)} m/set  ·  Nominal power: {fmt(mi.power_nominal_w, 1)} W  ·  '
                f'Cold lead: {mi.cold_lead_option_code}'
            ),
            'evidence': [{'icon': 'bi-layers', 'label': f'MI family: {mi_family_nm}  |  T-class verdict: {mi.t_class_verdict}'}],
            'std_refs': [],
        })
    else:
        steps.append({'section': 'C', 'section_color': 'green', 'num': 7, 'num_color': 'green',
                      'title': 'SR/MI Tracer Selection', 'available': False})

    # ── SECTION D: ELECTRICAL SIZING ─────────────────────────
    if calc:
        n_cct  = calc.total_circuits
        brk    = f2(calc.breaker_size, 0)
        i_op   = f2(calc.operating_current, 3)
        i_st   = f2(calc.starting_current, 3)
        load_w = f2(calc.total_power_consumption, 1)
        allowed_i = round(float(proj_cb_max) * float(proj_cb_load) / 100, 1) if proj_cb_max and proj_cb_load else None
        subs9 = (
            f'N_circuits = ceil(I_max_line / (CB_max × f_load))\n'
            f'           ≈ {n_cct}  (CB_max = {proj_cb_max} A,  f_load = {proj_cb_load}%,  max/circuit = {allowed_i} A)'
        )
        steps.append({
            'section': 'D', 'section_color': 'purple', 'num': 9, 'num_color': 'purple',
            'title': 'Electrical Sizing — Circuit Count and Breaker Selection', 'available': True,
            'symbolic': 'N_circuits = ⌈ I_max_line / (CB_max × f_load) ⌉',
            'substitution': subs9,
            'result_value': str(n_cct), 'result_unit': f'circuit(s)  ·  {brk} A MCB',
            'result_label': (
                f'Op. current = {i_op} A/circuit  ·  Start current = {i_st} A/circuit  ·  '
                f'Total connected load = {fmt(load_w, 0)} W ({fmt(load_w / 1000 if load_w else None, 2)} kW)  ·  '
                'High-voltage scenario used for current sizing; low-voltage scenario used for heat delivery check.'
            ),
            'evidence': [
                {'icon': 'bi-gear', 'label': f'CB max = {proj_cb_max} A  ·  loading = {proj_cb_load}%  ·  voltage = {fmt(proj_voltage, 0)} V'},
                {'icon': 'bi-lightning-charge', 'label': 'SR parallel straight runs share one 2-pole MCB per run group; MI multi-sets remain independently protected.'},
            ],
            'std_refs': [],
        })
    else:
        steps.append({'section': 'D', 'section_color': 'purple', 'num': 9, 'num_color': 'purple',
                      'title': 'Electrical Sizing', 'available': False})

    # ── SECTION E: COLD CABLE ─────────────────────────────────
    step_n = 1
    if cc_results:
        for cc in cc_results:
            steps.extend(_cc_steps(cc, step_n))
            step_n += 10

        # Terminal voltage cross-check
        first_cc = cc_results[0]
        v_terminal = f2(first_cc.load_end_voltage_v, 1)
        if st and proj_voltage and v_terminal:
            vcf_eff   = round(float(v_terminal) / float(proj_voltage), 4)
            p_nom_ref = f2(st.power_output / float(st.voltage_correction_factor)**2, 3) if st.voltage_correction_factor else None
            p_terminal= round(float(p_nom_ref or 0) * vcf_eff**2, 3) if p_nom_ref else None
            q_des     = f2(hl.design_heat_loss, 3) if hl else None
            n_sr_r    = (st.sr_parallel_run_count or 1)
            p_total   = round(float(p_terminal or 0) * n_sr_r, 2) if p_terminal else None
            adequate  = p_total is not None and q_des is not None and p_total >= float(q_des)
            steps.append({
                'section': 'E', 'section_color': 'purple',
                'num': f'E{step_n}', 'num_color': 'green' if adequate else 'amber',
                'title': 'Cross-Check — Tracer Heat Delivery at Final Terminal Voltage',
                'available': True,
                'symbolic': 'P_actual = P_nom × (V_terminal / V_nom)²  ≥  Q_design / N_SR',
                'substitution': (
                    f'V_terminal = load-end voltage from cold cable sizing = {v_terminal} V\n'
                    f'Effective VCF_actual = {v_terminal} / {fmt(proj_voltage, 0)} = {vcf_eff}\n'
                    f'P_actual per run = P_nom × VCF_actual² = {p_terminal} W/m\n'
                    f'Total heat delivery = {p_terminal} × {n_sr_r} = {p_total} W/m\n'
                    f'Required Q_design = {q_des} W/m  →  {"ADEQUATE ✓" if adequate else "REQUIRES REVIEW — marginal heat delivery"}'
                ),
                'result_value': f'{p_total} W/m', 'result_unit': 'actual heat delivery',
                'result_label': (
                    f'Required: {q_des} W/m  ·  ' +
                    ('Heat delivery confirmed adequate at final terminal voltage including cold cable VD.' if adequate
                     else 'Heat delivery may be marginal. Consider increasing VD allowance, reducing cable lengths, or reviewing safety factor.')
                ),
                'evidence': [{'icon': 'bi-info-circle', 'label': (
                    'This step closes the loop: Section C sized the tracer at V_LV (supply voltage variation margin). '
                    'Cold cable VD then reduces V_LV further to V_terminal. '
                    'This cross-check confirms the selected tracer still delivers adequate heat at the final reduced terminal voltage.'
                )}],
                'std_refs': [],
            })
    else:
        steps.append({
            'section': 'E', 'section_color': 'purple',
            'num': 'E1', 'num_color': 'purple',
            'title': 'Cold Cable Sizing — Not Run', 'available': False,
            'note': 'No cold cable sizing results found. Run cold cable sizing from the Cable Schedule tab.',
        })

    ctx['report'] = {
        'line':    line,
        'project': project,
        'steps':   steps,
        'has_mi':  mi is not None,
        'has_sr':  st is not None,
        'has_cc':  bool(cc_results),
        'sections': [
            {'letter': 'A', 'color': 'blue',   'title': 'Input Data'},
            {'letter': 'B', 'color': 'amber',  'title': 'Thermal Calculation'},
            {'letter': 'C', 'color': 'green',  'title': 'Tracer Selection'},
            {'letter': 'D', 'color': 'purple', 'title': 'Electrical Sizing'},
            {'letter': 'E', 'color': 'purple', 'title': 'Cold Cable Sizing'},
        ],
    }

    return render(request, 'eht/verification_report.html', ctx)


def calculation_manual_view(request):
    manual_path = Path(settings.BASE_DIR) / 'NOTES' / 'CALCULATION_MODULE_USER_MANUAL.md'
    try:
        manual_source = manual_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        manual_source = (
            '# Calculation Module User Manual\n\n'
            'The calculation module manual has not been generated yet.'
        )
    rendered = render_markdown_manual(manual_source)
    return render(request, 'eht/calculation_manual.html', {
        'manual_html': mark_safe(rendered.html),
        'manual_toc': rendered.toc,
        'manual_section_count': len([item for item in rendered.toc if item['level'] == 2]),
        'manual_path': manual_path,
    })


# --------------Create project data--------------------------------------------------
def create_project_data(request, project_id=None,):  
    form = handle_project_data(request)
    return render(request, 'eht/project_data.html', {'form': form})
# --------------Edit project data--------------------------------------------------
def update_project_data(request, project_id=None, *arg, **kwarg):
    form = handle_project_data(request, project_id)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        form_html = render_to_string(
            'eht/partials/project_data_form.html',
            {'form': form, 'project_id': project_id},
            request,
        )
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
            'line__heat_loss_result',
            'line__selected_tracer_result',
            'line__selected_mi_heater_result',
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
    mi_result_rows = list(
        SelectedMIHeater.objects.filter(line__proj_id=project_id)
        .select_related('line', 'heater', 'cold_lead_option')
        .order_by('line__line_id')
    )
    mi_by_line_uid = {
        str(mi_result.line_id): mi_result
        for mi_result in mi_result_rows
        if mi_result.line_id
    }
    selected_mi_line_uids = {
        str(mi_result.line_id)
        for mi_result in mi_result_rows
        if mi_result.line_id and mi_result.selection_status == 'selected'
    }
    selection_issue_rows = [
        _selection_issue_payload(heat_loss)
        for heat_loss in HeatLoss.objects.filter(line__proj_id=project_id, selection_status='rejected')
        .select_related('line')
        .order_by('line__line_id')
        if str(heat_loss.line_id) not in selected_mi_line_uids
    ]
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
    cold_cable_rows = _cold_cable_results(project_id)
    branch_rows = _attach_cold_cable_results(branch_rows, cold_cable_rows)
    panel_summary_rows, panel_summary_totals = _build_panel_load_summary(
        project_id,
        branch_rows,
        ProjectData.objects.filter(proj_id=project_id).first(),
    )
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
    calculation_line_uids = set()
    for calculation in calculations:
        line = calculation.line
        calculation_line_uids.add(str(line.uid))
        tracer_override = active_tracer_overrides.get(str(line.uid))
        override_alternate = (
            override_alternates.get((str(line.uid), tracer_override.selected_v_uid))
            if tracer_override
            else None
        )
        line_results.append({
            'result_mode': 'sr_calculated',
            'calculation': calculation,
            'line': line,
            'heat_loss': getattr(line, 'heat_loss_result', None),
            'heat_loss_basis_label': _heat_loss_basis_label(getattr(line, 'heat_loss_result', None)),
            'heat_loss_rule_set': _heat_loss_rule_set(getattr(line, 'heat_loss_result', None)),
            'selected_tracer': getattr(line, 'selected_tracer_result', None),
            'selected_mi_heater': mi_by_line_uid.get(str(line.uid)),
            'alternate_tracers': list(line.alternate_tracer_results.all()),
            'tracer_override': tracer_override,
            'tracer_override_alternate': override_alternate,
            'branch_count': len(getattr(line.power_distribution_result, 'branches').all()) if hasattr(line, 'power_distribution_result') else 0,
        })
    for mi_result in mi_result_rows:
        mi_result.review_summary = _mi_result_review_summary(mi_result)
        line = mi_result.line
        if str(line.uid) in calculation_line_uids:
            continue
        if mi_result.selection_status != 'selected':
            continue
        tracer_override = active_tracer_overrides.get(str(line.uid))
        line_results.append({
            'result_mode': 'mi_only',
            'calculation': None,
            'line': line,
            'heat_loss': getattr(line, 'heat_loss_result', None),
            'heat_loss_basis_label': _heat_loss_basis_label(getattr(line, 'heat_loss_result', None)),
            'heat_loss_rule_set': _heat_loss_rule_set(getattr(line, 'heat_loss_result', None)),
            'selected_tracer': None,
            'selected_mi_heater': mi_result,
            'alternate_tracers': [],
            'tracer_override': tracer_override,
            'tracer_override_alternate': None,
            'branch_count': 0,
        })
    line_results.sort(key=lambda item: item['line'].line_id)

    sr_result_count = sum(1 for item in line_results if not _is_selected_mi_result(item.get('selected_mi_heater')))
    mi_selected_count = sum(1 for item in line_results if _is_selected_mi_result(item.get('selected_mi_heater')))
    sr_connected_load_w = sum(
        item['calculation'].total_power_consumption
        for item in line_results
        if item['calculation'] and not _is_selected_mi_result(item.get('selected_mi_heater'))
    )
    mi_connected_load_w = sum(
        _selected_mi_power_w(item)
        for item in line_results
        if _is_selected_mi_result(item.get('selected_mi_heater'))
    )
    sr_tracer_length_m = sum(
        item['calculation'].total_tracer_length
        for item in line_results
        if item['calculation'] and not _is_selected_mi_result(item.get('selected_mi_heater'))
    )
    mi_heated_length_m = sum(
        _selected_mi_heated_length_m(item)
        for item in line_results
        if _is_selected_mi_result(item.get('selected_mi_heater'))
    )

    summary = {
        'calculated_lines': len(line_results),
        'total_circuits': sum(item['calculation'].total_circuits for item in line_results if item['calculation']),
        'total_power_kw': (sr_connected_load_w + mi_connected_load_w) / 1000 if line_results else 0,
        'total_tracer_length': sr_tracer_length_m + mi_heated_length_m,
        'sr_result_count': sr_result_count,
        'mi_selected_count': mi_selected_count,
        'sr_connected_load_kw': sr_connected_load_w / 1000,
        'mi_connected_load_kw': mi_connected_load_w / 1000,
        'sr_tracer_length': sr_tracer_length_m,
        'mi_heated_length': mi_heated_length_m,
        'branch_count': len(branch_rows),
        'tracer_override_count': len(active_tracer_overrides),
        'selection_issue_count': len(selection_issue_rows),
        'mi_result_count': len(mi_result_rows),
        'mi_fallback_count': sum(1 for item in mi_result_rows if item.selection_status == 'selected'),
        'mi_alternative_count': sum(1 for item in mi_result_rows if item.selection_status == 'available_alternative'),
        'mi_rejected_count': sum(1 for item in mi_result_rows if item.selection_status == 'rejected'),
        'mi_multi_set_count': sum(
            1
            for item in mi_result_rows
            if item.selection_status == 'selected' and (item.selection_basis or {}).get('heater_set_count', 1) > 1
        ),
        'cold_cable_result_count': len(cold_cable_rows),
        'cold_cable_selected_count': sum(1 for item in cold_cable_rows if item.sizing_status == 'selected'),
        'cold_cable_review_count': sum(1 for item in cold_cable_rows if item.sizing_status == 'review_required'),
        'cold_cable_unsizeable_count': sum(1 for item in cold_cable_rows if item.sizing_status == 'unsizeable'),
        'cold_cable_total_mass_mt': sum(item.conductor_mass_total_mt or 0 for item in cold_cable_rows),
        'panel_source_count': panel_summary_totals['source_count'],
        'panel_mcb_count': panel_summary_totals['mcb_count'],
        'panel_load_current_a': panel_summary_totals['load_current_a'],
        'panel_connected_load_kw': panel_summary_totals['connected_load_kw'],
        'panel_review_required_count': panel_summary_totals['review_required_count'],
        'panel_unsizeable_count': panel_summary_totals['unsizeable_count'],
    }
    summary = apply_active_summary_overrides(
        project_id,
        'result',
        summary,
        allow_stale=allow_topology_overrides,
    )
    return {
        'line_results': line_results,
        'selection_issue_rows': selection_issue_rows,
        'mi_result_rows': mi_result_rows,
        'branch_rows': branch_rows,
        'cold_cable_rows': cold_cable_rows,
        'panel_summary_rows': panel_summary_rows,
        'panel_summary_totals': panel_summary_totals,
        'summary': summary,
    }


def _is_selected_mi_result(mi_result):
    return bool(mi_result and mi_result.selection_status == 'selected')


def _selected_mi_power_w(item):
    mi_result = item.get('selected_mi_heater')
    if mi_result and mi_result.power_nominal_w:
        return mi_result.power_nominal_w
    calculation = item.get('calculation')
    if calculation:
        return calculation.total_power_consumption
    return 0


def _selected_mi_heated_length_m(item):
    mi_result = item.get('selected_mi_heater')
    if mi_result and mi_result.heated_length_m:
        return mi_result.heated_length_m
    calculation = item.get('calculation')
    if calculation:
        return calculation.total_tracer_length
    return 0


def _line_heater_type(item):
    return 'MI' if _is_selected_mi_result(item.get('selected_mi_heater')) else 'SR'


def _line_heating_cable_length_m(item):
    if _line_heater_type(item) == 'MI':
        return _selected_mi_heated_length_m(item)
    calculation = item.get('calculation')
    return calculation.total_tracer_length if calculation else 0


def _line_heating_length_basis(item):
    if _line_heater_type(item) == 'MI':
        return 'MI heated length excludes cold leads and factory terminations'
    calculation = item.get('calculation')
    if calculation and calculation.sr_parallel_run_count > 1:
        return 'Ordered SR length includes all straight parallel runs and termination installation allowance'
    return 'Ordered SR length includes termination installation allowance'


def _mi_export_design_basis_notes(mi_result):
    if not mi_result:
        return ''
    basis = mi_result.selection_basis or {}
    notes = [
        'Automatic MI fallback after SR temperature-limit exceedance'
        if basis.get('selection_mode') == 'automatic_temperature_fallback'
        else 'MI candidate stored for engineering review',
        'Independent breaker per MI heater set',
        'Shared sensing assumed; RTD location requires project review',
        'T-class requires design review; no calculated sheath-temperature approval yet',
        'JB terminal capacity, cold cable, panel coordination, and voltage drop are deferred checks',
    ]
    heater_set_count = basis.get('heater_set_count')
    if heater_set_count and heater_set_count > 1:
        notes.insert(1, f'{heater_set_count} identical heater sets selected for aggregate heat delivery')
    return '; '.join(notes)


MI_REJECTION_ACTION_HINTS = {
    'NO_VALIDATED_MI_CATALOGUE_DATA': (
        'Validate reviewed MI catalogue rows for the selected vendor, then rerun the calculation.'
    ),
    'NO_MI_CANDIDATE_MATCH': (
        'Review MI family limits, heater resistance codes, cold-lead options, voltage, breaker loading, and line length; then rerun the calculation.'
    ),
    'UNSUPPORTED_PHASE': 'Use a single-phase MI heater set for the MVP path or defer the line to the later multi-heater/three-phase MI module.',
    'MI_SELECTION_ERROR': 'Review the error details, correct the catalogue/input data, and rerun the calculation.',
}


def _first_reason_payload(reasons):
    if reasons and isinstance(reasons[0], dict):
        return reasons[0]
    return {}


def _mi_rejection_evidence_text(code, details):
    if code == 'NO_VALIDATED_MI_CATALOGUE_DATA':
        catalogue_rows = details.get('catalogue_rows')
        vendor = details.get('vendor') or 'selected vendor'
        if catalogue_rows:
            return f'{catalogue_rows} MI family row(s) exist for {vendor}, but none are marked as validated.'
        return f'No MI catalogue family rows were found for {vendor}.'
    if code == 'NO_MI_CANDIDATE_MATCH':
        rejected_count = details.get('rejected_candidate_count')
        family_rejections = details.get('family_rejections') or []
        if rejected_count:
            return f'{rejected_count} heater/cold-lead candidate(s) were rejected after catalogue and electrical checks.'
        if family_rejections:
            return f'{len(family_rejections)} family record(s) were rejected before heater evaluation.'
    return ''


def _mi_result_review_summary(mi_result):
    if mi_result.selection_status != 'rejected':
        return {
            'code': '',
            'message': '',
            'evidence': '',
            'action': '',
        }
    reason = _first_reason_payload(mi_result.selection_rejection_reasons or [])
    code = reason.get('code') or 'MI_SELECTION_REJECTED'
    details = reason.get('details') or {}
    return {
        'code': code,
        'message': reason.get('message') or 'MI heater selection did not produce an acceptable candidate.',
        'evidence': _mi_rejection_evidence_text(code, details),
        'action': MI_REJECTION_ACTION_HINTS.get(
            code,
            'Review the MI selection diagnostic details and rerun the calculation after correcting catalogue or input data.',
        ),
    }


def _first_selection_rejection(heat_loss):
    if not heat_loss:
        return {}
    reasons = heat_loss.selection_rejection_reasons or []
    if reasons and isinstance(reasons[0], dict):
        return reasons[0]
    return {}


def _heat_loss_basis(heat_loss):
    if not heat_loss:
        return {}
    return heat_loss.conductivity_basis or {}


def _heat_loss_basis_label(heat_loss):
    basis = _heat_loss_basis(heat_loss)
    return basis.get('effective_method_label') or basis.get('effective_method') or ''


def _heat_loss_rule_set(heat_loss):
    basis = _heat_loss_basis(heat_loss)
    return basis.get('rule_set') or ''


def _selection_issue_payload(heat_loss):
    reason = _first_selection_rejection(heat_loss)
    reason_details = reason.get('details') or {}
    return {
        'line': heat_loss.line,
        'heat_loss': heat_loss,
        'status': heat_loss.selection_status or 'rejected',
        'reason_code': reason.get('code') or '',
        'reason_message': reason.get('message') or '',
        'reason_details': reason_details,
        'reason_evidence': _sr_selection_rejection_evidence_text(reason.get('code') or '', reason_details),
        'basis_label': _heat_loss_basis_label(heat_loss),
        'rule_set': _heat_loss_rule_set(heat_loss),
    }


def _sr_selection_rejection_evidence_text(code, details):
    if code == 'NO_SPIRAL_FACTOR_MATCH':
        attempted = details.get('attempted_run_counts') or []
        attempted_label = ', '.join(str(item) for item in attempted) if attempted else details.get('sr_parallel_run_cap', '')
        best_uid = details.get('best_candidate_v_uid') or 'best available candidate'
        best_duty = details.get('best_per_run_duty_ratio_at_max_runs')
        max_delivery = details.get('max_heat_delivery_at_run_cap_w_m')
        pieces = []
        if attempted_label:
            pieces.append(f"Attempted SR straight run counts: {attempted_label}.")
        if best_duty not in (None, ''):
            pieces.append(f"Best per-run duty at cap: {float(best_duty):.2f} using {best_uid}.")
        if max_delivery not in (None, ''):
            pieces.append(f"Max heat delivery at cap: {float(max_delivery):.2f} W/m.")
        return ' '.join(pieces)
    if code == 'NO_SR_CATALOGUE_SUITABILITY':
        return 'Catalogue rows were rejected before heat-duty sizing by family, temperature, area, gas group, or T-rating checks.'
    if code == 'NO_SR_CATALOGUE_VOLTAGE_COMPATIBILITY':
        return f"System voltage checked: {details.get('system_voltage', '-') } V."
    if code == 'NO_POSITIVE_POWER_OUTPUT':
        return f"Candidate rows checked at maintain temperature: {details.get('candidate_rows', '-') }."
    return ''


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


def _number_or_zero(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _branch_tagged_components(branch):
    tagged = _branch_value(branch, ['tagged_components'], {})
    return tagged if isinstance(tagged, dict) else {}


def _branch_component_metadata(branch, component_key):
    tagged = _branch_tagged_components(branch)
    component_details = tagged.get('component_details') if isinstance(tagged.get('component_details'), dict) else {}
    component = component_details.get(component_key) if isinstance(component_details.get(component_key), dict) else {}
    metadata = component.get('metadata') if isinstance(component.get('metadata'), dict) else {}
    return metadata


def _branch_panel_source(branch, project_id):
    tagged = _branch_tagged_components(branch)
    mcb_metadata = _branch_component_metadata(branch, 'MCB')
    source_id = (
        mcb_metadata.get('panel_id')
        or mcb_metadata.get('panel')
        or mcb_metadata.get('source_panel')
        or tagged.get('panel_id')
        or tagged.get('source_panel')
        or f'{project_id}:MAIN'
    )
    source_label = (
        mcb_metadata.get('panel_label')
        or mcb_metadata.get('source_label')
        or tagged.get('panel_label')
        or tagged.get('source_label')
        or f'Project {project_id} main distribution'
    )
    source_type = 'metadata' if source_id != f'{project_id}:MAIN' else 'project_default'
    return source_id, source_label, source_type


def _branch_breaker_size(branch):
    cold_result = _branch_value(branch, ['cold_cable_result'], None)
    if cold_result and cold_result.breaker_size_a:
        return _number_or_zero(cold_result.breaker_size_a)
    return _number_or_zero(_branch_component_metadata(branch, 'MCB').get('breaker_size'))


def _branch_load_current(branch):
    cold_result = _branch_value(branch, ['cold_cable_result'], None)
    if cold_result:
        if cold_result.per_circuit_operating_current_a:
            circuit_count = _number_or_zero(cold_result.circuit_count) or _number_or_zero(_branch_value(branch, ['circuit_count'], 0)) or 1
            return (
                _number_or_zero(cold_result.per_circuit_operating_current_a) * circuit_count,
                'cold_cable_result.per_circuit_operating_current_a x circuit_count',
            )
        if cold_result.line_operating_current_a:
            return _number_or_zero(cold_result.line_operating_current_a), 'cold_cable_result.line_operating_current_a'

    metadata = _branch_component_metadata(branch, 'MCB')
    if metadata.get('operating_current') not in (None, ''):
        circuit_count = _number_or_zero(_branch_value(branch, ['circuit_count'], 0)) or 1
        return (
            _number_or_zero(metadata.get('operating_current')) * circuit_count,
            'MCB metadata operating_current x branch circuit_count',
        )
    if metadata.get('line_operating_current') not in (None, ''):
        return _number_or_zero(metadata.get('line_operating_current')), 'MCB metadata line_operating_current'
    return 0.0, 'not_available'


def _panel_status_counts(cold_result):
    counts = {
        'selected_count': 0,
        'review_required_count': 0,
        'unsizeable_count': 0,
        'missing_cold_cable_count': 0,
    }
    if not cold_result:
        counts['missing_cold_cable_count'] = 1
        return counts
    if cold_result.sizing_status == 'selected':
        counts['selected_count'] = 1
    elif cold_result.sizing_status == 'unsizeable':
        counts['unsizeable_count'] = 1
    else:
        counts['review_required_count'] = 1
    return counts


def _build_panel_load_summary(project_id, branch_rows, project_setup=None):
    voltage = _number_or_zero(getattr(project_setup, 'voltage', None)) or 230.0
    groups = {}
    for branch in branch_rows:
        source_id, source_label, source_type = _branch_panel_source(branch, project_id)
        group = groups.setdefault(source_id, {
            'project_id': project_id,
            'source_id': source_id,
            'source_label': source_label,
            'source_type': source_type,
            'branch_count': 0,
            'mcb_count': 0,
            'mcb_tags': set(),
            'circuit_count': 0,
            'line_ids': set(),
            'load_current_a': 0.0,
            'connected_load_kw': 0.0,
            'breaker_capacity_a': 0.0,
            'largest_breaker_a': 0.0,
            'breaker_distribution': {},
            'selected_count': 0,
            'review_required_count': 0,
            'unsizeable_count': 0,
            'missing_cold_cable_count': 0,
            'load_basis': set(),
        })
        tagged = _branch_tagged_components(branch)
        mcb_tag = tagged.get('MCB')
        mcb_key = str(mcb_tag or f'branch:{group["branch_count"]}')
        branch_current, load_basis = _branch_load_current(branch)
        breaker_size = _branch_breaker_size(branch)
        cold_result = _branch_value(branch, ['cold_cable_result'], None)
        line_id = _branch_value(branch, ['distribution', 'line', 'line_id'], '') or _branch_value(branch, ['line_id'], '')
        status_counts = _panel_status_counts(cold_result)

        group['branch_count'] += 1
        is_new_mcb = bool(mcb_key and mcb_key not in group['mcb_tags'])
        if is_new_mcb:
            group['mcb_tags'].add(mcb_key)
        group['circuit_count'] += int(_number_or_zero(_branch_value(branch, ['circuit_count'], 0)))
        if line_id:
            group['line_ids'].add(str(line_id))
        group['load_current_a'] += branch_current
        group['connected_load_kw'] += (branch_current * voltage) / 1000.0
        if is_new_mcb:
            group['breaker_capacity_a'] += breaker_size
            group['largest_breaker_a'] = max(group['largest_breaker_a'], breaker_size)
        if is_new_mcb and breaker_size:
            breaker_key = f'{breaker_size:g} A'
            group['breaker_distribution'][breaker_key] = group['breaker_distribution'].get(breaker_key, 0) + 1
        for key, value in status_counts.items():
            group[key] += value
        group['load_basis'].add(load_basis)

    rows = []
    for group in groups.values():
        breaker_distribution = ', '.join(
            f'{size}: {count}'
            for size, count in sorted(
                group['breaker_distribution'].items(),
                key=lambda item: _number_or_zero(item[0].split()[0]),
            )
        )
        rows.append({
            **group,
            'mcb_count': len(group['mcb_tags']),
            'line_count': len(group['line_ids']),
            'line_ids_display': ', '.join(sorted(group['line_ids'])),
            'breaker_distribution_display': breaker_distribution or '-',
            'load_basis_display': '; '.join(sorted(group['load_basis'])) or 'not_available',
        })
    rows.sort(key=lambda item: item['source_label'])

    totals = {
        'source_count': len(rows),
        'branch_count': sum(row['branch_count'] for row in rows),
        'mcb_count': sum(row['mcb_count'] for row in rows),
        'circuit_count': sum(row['circuit_count'] for row in rows),
        'load_current_a': sum(row['load_current_a'] for row in rows),
        'connected_load_kw': sum(row['connected_load_kw'] for row in rows),
        'breaker_capacity_a': sum(row['breaker_capacity_a'] for row in rows),
        'selected_count': sum(row['selected_count'] for row in rows),
        'review_required_count': sum(row['review_required_count'] for row in rows),
        'unsizeable_count': sum(row['unsizeable_count'] for row in rows),
        'missing_cold_cable_count': sum(row['missing_cold_cable_count'] for row in rows),
        'basis': 'Grouped by panel/source metadata when present; otherwise by project main distribution.',
    }
    return rows, totals


def _panel_load_summary_export_rows(panel_rows):
    rows = []
    for row in panel_rows:
        rows.append({
            'Project ID': row['project_id'],
            'Source ID': row['source_id'],
            'Source Label': row['source_label'],
            'Source Type': row['source_type'],
            'Line Count': row['line_count'],
            'Line IDs': row['line_ids_display'],
            'Branch Count': row['branch_count'],
            'MCB Count': row['mcb_count'],
            'Circuit Count': row['circuit_count'],
            'Total Load Current (A)': row['load_current_a'],
            'Connected Load (kW)': row['connected_load_kw'],
            'Breaker Capacity Sum (A)': row['breaker_capacity_a'],
            'Largest Breaker (A)': row['largest_breaker_a'],
            'Breaker Distribution': row['breaker_distribution_display'],
            'Cold Cable Selected': row['selected_count'],
            'Cold Cable Review Required': row['review_required_count'],
            'Cold Cable Unsizeable': row['unsizeable_count'],
            'Cold Cable Missing': row['missing_cold_cable_count'],
            'Load Basis': row['load_basis_display'],
        })
    return rows


def _cold_cable_results(project_id):
    results = list(
        ColdCableResult.objects.filter(project_id=project_id)
        .select_related('distribution', 'distribution__line', 'cable_4c_catalogue', 'cable_3c_catalogue')
        .order_by('line_id', 'branch_index')
    )
    for result in results:
        result.phase_balance_summary = _cold_cable_phase_balance_summary(result)
    return results


def _phase_label_from_circuit_index(circuit_index):
    try:
        normalized_index = int(circuit_index)
    except (TypeError, ValueError):
        return ''
    if normalized_index < 1:
        return ''
    return ('L1', 'L2', 'L3')[(normalized_index - 1) % 3]


def _cold_cable_phase_balance_summary(result):
    segments = result.cable_3c_segments or []
    if not segments:
        return None

    phase_loads = {
        'L1': {'label': 'L1', 'circuit_count': 0, 'operating_current_a': 0.0},
        'L2': {'label': 'L2', 'circuit_count': 0, 'operating_current_a': 0.0},
        'L3': {'label': 'L3', 'circuit_count': 0, 'operating_current_a': 0.0},
    }
    current = float(result.per_circuit_operating_current_a or 0.0)
    assigned_count = 0
    for segment in segments:
        phase_label = segment.get('phase_label') or _phase_label_from_circuit_index(segment.get('circuit_index'))
        if phase_label not in phase_loads:
            continue
        phase_loads[phase_label]['circuit_count'] += 1
        phase_loads[phase_label]['operating_current_a'] += current
        assigned_count += 1

    if not assigned_count:
        return None

    currents = [item['operating_current_a'] for item in phase_loads.values()]
    max_current = max(currents)
    min_current = min(currents)
    average_current = sum(currents) / len(currents)
    imbalance_a = max_current - min_current
    imbalance_pct = (imbalance_a / average_current * 100.0) if average_current else 0.0
    return {
        'phase_loads': list(phase_loads.values()),
        'basis': 'L1/L2/L3 round-robin by outgoing circuit index',
        'max_phase_current_a': max_current,
        'min_phase_current_a': min_current,
        'phase_imbalance_a': imbalance_a,
        'phase_imbalance_pct': imbalance_pct,
    }


def _cold_cable_result_indexes(cold_rows):
    by_distribution_branch = {}
    by_line_branch = {}
    for result in cold_rows:
        by_distribution_branch[(result.distribution_id, result.branch_index)] = result
        by_line_branch[(str(result.line_uid), result.branch_index)] = result
        by_line_branch[(str(result.line_id), result.branch_index)] = result
    return by_distribution_branch, by_line_branch


def _attach_cold_cable_results(branch_rows, cold_rows):
    by_distribution_branch, by_line_branch = _cold_cable_result_indexes(cold_rows)
    for branch in branch_rows:
        result = None
        distribution_id = _branch_value(branch, ['distribution', 'uid'], None)
        branch_index = _branch_value(branch, ['branch_index'], 0)
        if distribution_id is not None:
            result = by_distribution_branch.get((distribution_id, branch_index))
        if result is None:
            line_uid = _branch_value(branch, ['distribution', 'line', 'uid'], '')
            line_id = _branch_value(branch, ['distribution', 'line', 'line_id'], '')
            result = by_line_branch.get((str(line_uid), branch_index)) or by_line_branch.get((str(line_id), branch_index))
        if isinstance(branch, dict):
            branch['cold_cable_result'] = result
        else:
            setattr(branch, 'cold_cable_result', result)
    return branch_rows


def _cold_cable_export_rows(cold_rows):
    rows = []
    for result in cold_rows:
        phase_summary = _cold_cable_phase_balance_summary(result)
        phase_loads = {
            item['label']: item
            for item in (phase_summary or {}).get('phase_loads', [])
        }
        rows.append({
            'Project ID': result.project_id,
            'Line ID': result.line_id,
            'Line UID': result.line_uid,
            'Branch Index': result.branch_index,
            'Heating Cable Type': result.heating_cable_type,
            'Topology Branch': result.branch.branch_type if result.branch else '',
            'Circuit Count': result.circuit_count,
            'Operating Current / Circuit (A)': result.per_circuit_operating_current_a,
            'Line Operating Current (A)': result.line_operating_current_a,
            'Breaker Size (A)': result.breaker_size_a,
            'MCB Curve': result.mcb_curve,
            'RCD Provided': result.rcd_provided,
            'Length Basis': result.length_basis,
            'Feeder Cable Length (m)': result.length_4c_m,
            'Branch Cable Length (m)': result.length_3c_m,
            'Feeder Cable Size (mm2)': result.cable_4c_size_mm2,
            'Branch Cable Size (mm2)': result.cable_3c_size_mm2,
            'Feeder Cable Derated Ampacity (A)': result.cable_4c_ampacity_derated_a,
            'Branch Cable Derated Ampacity (A)': result.cable_3c_ampacity_derated_a,
            'Feeder Cable Conductor Temp (C)': result.cable_4c_conductor_temp_c,
            'Branch Cable Conductor Temp (C)': result.cable_3c_conductor_temp_c,
            'K Temp': result.k_temp,
            'K Group': result.k_group,
            'K Total': result.k_total,
            'VD Allowable (%)': result.vd_allowable_pct,
            'Feeder Cable VD (%)': result.cable_4c_vd_pct,
            'Branch Cable VD (%)': result.cable_3c_vd_pct,
            'Total VD (%)': result.vd_total_pct,
            'Load-End Voltage (V)': result.load_end_voltage_v,
            'VD Status': result.vd_status,
            'L-PE Fault Current (A)': result.fault_current_l_pe_a,
            'L-PE Fault Loop Status': result.fault_loop_status,
            'Source Impedance (ohm)': (result.fault_loop_basis or {}).get('source_impedance_ohm'),
            'EHT DB Fault Rating (kA)': (result.fault_loop_basis or {}).get('eht_db_fault_rating_ka'),
            'Feeder Cable Conductor Mass (MT)': result.cable_4c_conductor_mass_mt,
            'Branch Cable Conductor Mass (MT)': result.cable_3c_conductor_mass_mt,
            'Total Conductor Mass (MT)': result.conductor_mass_total_mt,
            'Density Basis (kg/m3)': result.conductor_material_density_kg_m3,
            'Sizing Status': result.sizing_status,
            'Review Notes': '; '.join(result.review_notes or []),
            'Phase Balance Basis': (phase_summary or {}).get('basis') or '',
            'L1 Current (A)': (phase_loads.get('L1') or {}).get('operating_current_a'),
            'L2 Current (A)': (phase_loads.get('L2') or {}).get('operating_current_a'),
            'L3 Current (A)': (phase_loads.get('L3') or {}).get('operating_current_a'),
            'Phase Imbalance (A)': (phase_summary or {}).get('phase_imbalance_a'),
            'Phase Imbalance (%)': (phase_summary or {}).get('phase_imbalance_pct'),
        })
    return rows


def _cold_cable_3c_segment_export_rows(cold_rows):
    rows = []
    for result in cold_rows:
        critical_size = result.cable_3c_size_mm2
        for segment in result.cable_3c_segments or []:
            size = segment.get('size_mm2')
            try:
                is_critical = bool(size is not None and critical_size is not None and float(size) >= float(critical_size))
            except (TypeError, ValueError):
                is_critical = False
            rows.append({
                'Project ID': result.project_id,
                'Line ID': result.line_id,
                'Line UID': result.line_uid,
                'Branch Index': result.branch_index,
                'Branch Critical Size (mm2)': critical_size,
                'Segment Display Tag': segment.get('display_tag') or '',
                'Segment Component ID': segment.get('component_id') or '',
                'Circuit Index': segment.get('circuit_index'),
                'Phase Slot': segment.get('phase_slot'),
                'Phase Label': segment.get('phase_label') or _phase_label_from_circuit_index(segment.get('circuit_index')),
                'Phase Basis': segment.get('phase_basis') or '',
                'Segment Length (m)': segment.get('length_m'),
                'Length Basis': segment.get('length_basis') or result.length_basis,
                'Branch Segment Size (mm2)': size,
                'Critical Segment': 'Yes' if is_critical else '',
                'Derated Ampacity (A)': segment.get('ampacity_derated_a'),
                'Ampacity Margin (%)': segment.get('ampacity_margin_pct'),
                'Conductor Temp (C)': segment.get('conductor_temp_c'),
                'Conductor Mass (MT)': segment.get('conductor_mass_mt'),
                'Branch VD (%)': segment.get('vd_pct'),
                'Total Path VD (%)': segment.get('vd_total_pct'),
                'Load-End Voltage (V)': segment.get('load_end_voltage_v'),
                'L-PE Fault Current (A)': segment.get('fault_current_a'),
                'L-PE Fault Loop Status': segment.get('fault_status') or result.fault_loop_status,
                'Sizing Status': segment.get('sizing_status') or result.sizing_status,
                'K Temp': segment.get('k_temp'),
                'K Group': segment.get('k_group'),
                'K Total': segment.get('k_total'),
                'Review Notes': '; '.join(segment.get('review_notes') or []),
            })
    return rows


def result_view(request):
    project_id = request.GET.get('project_id')
    context = _get_project_workspace_context(request, project_id)
    line_results = []
    branch_rows = []
    cold_cable_rows = []
    panel_summary_rows = []
    panel_summary_totals = {
        'source_count': 0,
        'branch_count': 0,
        'mcb_count': 0,
        'circuit_count': 0,
        'load_current_a': 0,
        'connected_load_kw': 0,
        'breaker_capacity_a': 0,
        'selected_count': 0,
        'review_required_count': 0,
        'unsizeable_count': 0,
        'missing_cold_cable_count': 0,
        'basis': '',
    }
    selection_issue_rows = []
    mi_result_rows = []
    summary = {
        'calculated_lines': 0,
        'total_circuits': 0,
        'total_power_kw': 0,
        'total_tracer_length': 0,
        'branch_count': 0,
        'selection_issue_count': 0,
        'mi_result_count': 0,
        'mi_fallback_count': 0,
        'mi_alternative_count': 0,
    }

    if project_id and context['project_setup']:
        result_data = _build_result_workspace_data(project_id)
        line_results = result_data['line_results']
        selection_issue_rows = result_data['selection_issue_rows']
        mi_result_rows = result_data['mi_result_rows']
        branch_rows = result_data['branch_rows']
        cold_cable_rows = result_data['cold_cable_rows']
        panel_summary_rows = result_data['panel_summary_rows']
        panel_summary_totals = result_data['panel_summary_totals']
        summary = result_data['summary']

    context.update({
        'line_results': line_results,
        'selection_issue_rows': selection_issue_rows,
        'mi_result_rows': mi_result_rows,
        'branch_rows': branch_rows,
        'cold_cable_rows': cold_cable_rows,
        'panel_summary_rows': panel_summary_rows,
        'panel_summary_totals': panel_summary_totals,
        'result_summary': summary,
        'mi_mvp_basis_notes': MI_MVP_RESULT_BASIS_NOTES if summary.get('mi_result_count') else [],
        'has_results': bool(line_results or selection_issue_rows or mi_result_rows),
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
        mi_heater_sets = next(
            (entry.quantity for entry in group['items'] if entry.item_code == 'MI_HEATER_SET'),
            0,
        )
        mi_heated_length = next(
            (entry.quantity for entry in group['items'] if entry.item_code == 'MI_HEATED_LENGTH'),
            0,
        )
        line_groups.append({
            'line_id': line_id,
            'line': group['line'],
            'items': group['items'],
            'item_count': len(group['items']),
            'tracer_quantity': tracer_quantity,
            'mi_heater_sets': mi_heater_sets,
            'mi_heated_length': mi_heated_length,
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
        'mi_heater_set_total': consolidated_lookup.get('MI_HEATER_SET', 0),
        'mi_heated_length_total': consolidated_lookup.get('MI_HEATED_LENGTH', 0),
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

    cold_results = size_cold_cables_for_project(project_id)
    return JsonResponse({
        'success': f'Cable override saved for {override.display_tag}.',
        'component_id': override.component_id,
        'display_tag': override.display_tag,
        'manual_length_m': override.manual_length_m,
        'manual_cable_size': override.manual_cable_size,
        'cold_cable_result_count': len(cold_results),
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
    cold_results = size_cold_cables_for_project(project_id)
    return JsonResponse({
        'success': 'Cable override reset to generated value.',
        'reset_count': reset_count,
        'cold_cable_result_count': len(cold_results),
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


def _filtered_sld_topology_error(body):
    if not body or not (body.get('line_id') or '').strip():
        return None
    return JsonResponse({
        'error': (
            'Topology edits are not allowed in filtered SLD view. '
            'Clear the line filter before combining, splitting, adding JB, moving, or resetting topology.'
        ),
    }, status=400)


def sld_topology_combine_preview_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    body = _parse_json_request(request)
    if body is None:
        return JsonResponse({'error': 'Invalid topology edit payload.'}, status=400)
    filtered_response = _filtered_sld_topology_error(body)
    if filtered_response:
        return filtered_response

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
    filtered_response = _filtered_sld_topology_error(body)
    if filtered_response:
        return filtered_response

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
    filtered_response = _filtered_sld_topology_error(body)
    if filtered_response:
        return filtered_response

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
    filtered_response = _filtered_sld_topology_error(body)
    if filtered_response:
        return filtered_response

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
    filtered_response = _filtered_sld_topology_error(body)
    if filtered_response:
        return filtered_response

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
    filtered_response = _filtered_sld_topology_error(body)
    if filtered_response:
        return filtered_response

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
    filtered_response = _filtered_sld_topology_error(body)
    if filtered_response:
        return filtered_response

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
    filtered_response = _filtered_sld_topology_error(body)
    if filtered_response:
        return filtered_response

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
    filtered_response = _filtered_sld_topology_error(body)
    if filtered_response:
        return filtered_response

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
    filtered_response = _filtered_sld_topology_error(body)
    if filtered_response:
        return filtered_response

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
    if not result_data['line_results'] and not result_data['selection_issue_rows'] and not result_data['mi_result_rows']:
        return JsonResponse({'error': 'No stored calculation results are available for this project yet.'}, status=400)

    line_rows = []
    alternate_rows = []
    mi_rows = []
    selection_rows = []
    panel_summary_rows = _panel_load_summary_export_rows(result_data['panel_summary_rows'])
    cold_cable_rows = _cold_cable_export_rows(result_data['cold_cable_rows'])
    cold_cable_segment_rows = _cold_cable_3c_segment_export_rows(result_data['cold_cable_rows'])
    for item in result_data['line_results']:
        calculation = item['calculation']
        line = item['line']
        heat_loss = item.get('heat_loss')
        selected_tracer = item['selected_tracer']
        tracer_override = item.get('tracer_override')
        tracer_override_alternate = item.get('tracer_override_alternate')
        selected_mi_heater = item.get('selected_mi_heater')
        mi_basis = selected_mi_heater.selection_basis if selected_mi_heater else {}
        mi_heater_set_count = mi_basis.get('heater_set_count', 1) if mi_basis else ''
        mi_design_basis_notes = _mi_export_design_basis_notes(selected_mi_heater)
        heater_type = _line_heater_type(item)
        heating_cable_length = _line_heating_cable_length_m(item)
        heating_length_basis = _line_heating_length_basis(item)
        line_rows.append({
            'Project ID': project_id,
            'Line ID': line.line_id,
            'Heating Cable Type': heater_type,
            'Service Type': line.service_type,
            'Line Size': calculation.line_size if calculation else line.line_size,
            'Line Length': calculation.line_length if calculation else line.line_length,
            'Operating Temp': calculation.operating_temp if calculation else line.oper_temp,
            'Design Heat Loss (W/m)': heat_loss.design_heat_loss if heat_loss else (calculation.heat_loss if calculation else ''),
            'Base Heat Loss before SF (W/m)': heat_loss.base_heat_loss if heat_loss else '',
            'Heat Loss Safety Factor': heat_loss.heat_loss_sf if heat_loss else '',
            'Conductivity Method': item.get('heat_loss_basis_label') or '',
            'Conductivity Rule Set': item.get('heat_loss_rule_set') or '',
            'Conductivity (W/m.K)': heat_loss.conductivity if heat_loss else '',
            'Wind Correction Factor': heat_loss.wind_correction if heat_loss else '',
            'Accessory Tracer Adders (m)': heat_loss.tracer_adder if heat_loss else '',
            'SR Selection Status': heat_loss.selection_status if heat_loss else '',
            'Selected Tracer': calculation.selected_tracer if calculation else 'MI fallback selected',
            'Tracer Family': getattr(selected_tracer, 'tracer_family', ''),
            'SLD Tracer Override': tracer_override.selected_v_uid if tracer_override else '',
            'SLD Override Family': (
                'MI'
                if tracer_override and str(tracer_override.selected_v_uid or '').startswith('MI:')
                else getattr(tracer_override_alternate, 'tracer_family', '')
            ),
            'SLD Override Review Status': (
                'Review-only: load/BOQ/cable sizing not recalculated from override'
                if tracer_override
                else ''
            ),
            'Spiral Factor': calculation.spiral_factor if calculation else '',
            'SR Duty Ratio': calculation.spiral_factor if calculation else '',
            'SR Parallel Run Count': calculation.sr_parallel_run_count if calculation else '',
            'SR Parallel Run Basis': calculation.sr_parallel_run_basis if calculation else '',
            'SR Constructability Warning': calculation.sr_constructability_warning if calculation else '',
            'Breaker Size': calculation.breaker_size if calculation else '',
            'Total Circuits': calculation.total_circuits if calculation else '',
            'Starting Current / Circuit (A)': calculation.starting_current if calculation else '',
            'Operating Current / Circuit (A)': calculation.operating_current if calculation else '',
            'Current Basis': 'Per circuit',
            'Total Connected Load (W)': calculation.total_power_consumption if calculation else '',
            'Heating Cable Length (m)': heating_cable_length,
            'Heating Cable Length Basis': heating_length_basis,
            'Ordered SR Tracer Length incl. Termination Allowance (m)': (
                heating_cable_length if heater_type == 'SR' and calculation else ''
            ),
            'MI Heated Length excl. Cold Leads (m)': (
                heating_cable_length if heater_type == 'MI' else ''
            ),
            'Heated Tracer Length excl. Termination Allowance (m)': (
                selected_tracer.tracer_with_margin if selected_tracer else ''
            ),
            'Tracer Length Basis': heating_length_basis,
            'Pipe Size mm': calculation.pipe_size_mm if calculation else '',
            'MI Candidate Status': selected_mi_heater.selection_status if selected_mi_heater else '',
            'MI Heater Part Number': (
                selected_mi_heater.heater.part_number
                if selected_mi_heater and selected_mi_heater.heater
                else ''
            ),
            'MI Heater Set Count': mi_heater_set_count,
            'MI Cold Lead Option': (
                selected_mi_heater.cold_lead_option_code
                if selected_mi_heater
                else ''
            ),
            'MI Cold Lead Length (m)': (
                selected_mi_heater.cold_lead_length_m
                if selected_mi_heater
                else ''
            ),
            'MI Design Basis Notes': mi_design_basis_notes,
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
                'SR Duty Ratio': alternate.spiral_factor,
                'SR Parallel Run Count': alternate.sr_parallel_run_count,
                'SR Parallel Run Basis': alternate.sr_parallel_run_basis,
                'SR Constructability Warning': alternate.sr_constructability_warning,
                'Heated Tracer Length before Design Margin (m)': alternate.tracer_length,
                'Heated Tracer Length with Design Margin excl. Termination (m)': alternate.tracer_with_margin,
            })

    for mi_result in result_data['mi_result_rows']:
        basis = mi_result.selection_basis or {}
        line = mi_result.line
        review_summary = getattr(mi_result, 'review_summary', None) or _mi_result_review_summary(mi_result)
        mi_design_basis_notes = _mi_export_design_basis_notes(mi_result)
        mi_rows.append({
            'Project ID': project_id,
            'Line ID': line.line_id if line else '',
            'Service Type': line.service_type if line else '',
            'MI Selection Status': mi_result.selection_status,
            'Selection Mode': basis.get('selection_mode', ''),
            'Rejection Code': review_summary.get('code', ''),
            'Rejection Message': review_summary.get('message', ''),
            'Diagnostic Evidence': review_summary.get('evidence', ''),
            'Next Action': review_summary.get('action', ''),
            'Heater Part Number': mi_result.heater.part_number if mi_result.heater else '',
            'Heater Set Count': basis.get('heater_set_count', 1) if basis else '',
            'Cold Lead Option': mi_result.cold_lead_option_code,
            'Heated Length (m)': mi_result.heated_length_m,
            'Nominal Power (W)': mi_result.power_nominal_w,
            'Power Density (W/m)': mi_result.power_density_w_m,
            'Nominal Current per Set (A)': mi_result.current_nominal_a,
            'Cold Start Current per Set (A)': mi_result.current_cold_start_a,
            'Published Sheath Temp (°C)': mi_result.max_sheath_temp_published_c,
            'Project T-Class Limit (°C)': mi_result.project_t_class_limit_c,
            'T-Class Verdict': mi_result.t_class_verdict,
            'Design Basis Notes': mi_design_basis_notes,
            'Rejection Reasons': json.dumps(mi_result.selection_rejection_reasons or [], default=str),
        })

    for item in result_data['selection_issue_rows']:
        heat_loss = item['heat_loss']
        line = item['line']
        selection_rows.append({
            'Project ID': project_id,
            'Line ID': line.line_id if line else '',
            'Service Type': line.service_type if line else '',
            'Selection Status': item['status'],
            'Reason Code': item['reason_code'],
            'Reason Message': item['reason_message'],
            'Reason Evidence': item.get('reason_evidence', ''),
            'Reason Details': json.dumps(item['reason_details'], default=str),
            'Design Heat Loss (W/m)': heat_loss.design_heat_loss,
            'Base Heat Loss before SF (W/m)': heat_loss.base_heat_loss,
            'Heat Loss Safety Factor': heat_loss.heat_loss_sf,
            'Conductivity Method': item['basis_label'],
            'Conductivity Rule Set': item['rule_set'],
            'Conductivity (W/m.K)': heat_loss.conductivity,
            'Wind Correction Factor': heat_loss.wind_correction,
            'Accessory Tracer Adders (m)': heat_loss.tracer_adder,
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
        pd.DataFrame(selection_rows).to_excel(writer, sheet_name='Selection Diagnostics', index=False)
        pd.DataFrame(branch_rows).to_excel(writer, sheet_name='Power Distribution', index=False)
        pd.DataFrame(panel_summary_rows).to_excel(writer, sheet_name='Panel Load Summary', index=False)
        pd.DataFrame(cold_cable_rows).to_excel(writer, sheet_name='Cold Cable Sizing', index=False)
        pd.DataFrame(cold_cable_segment_rows).to_excel(writer, sheet_name='Cold Cable Branch Segments', index=False)
        pd.DataFrame(alternate_rows).to_excel(writer, sheet_name='Alternate Tracers', index=False)
        pd.DataFrame(mi_rows).to_excel(writer, sheet_name='MI Selection', index=False)

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
    fault_rating_form_fields = {'eht_db_fault_rating_ka_preset', 'eht_db_fault_rating_ka_custom'}
    setup_fields = set(ProjectDataForm.Meta.fields) | fault_rating_form_fields
    if not any(field in request.POST for field in setup_fields if field != 'proj_id'):
        return None

    post_data = request.POST.copy()
    selected_project_id = post_data.get('proj_id') or project_id
    if selected_project_id != project_id:
        raise ValidationError("Uploaded project setup does not match the selected project.")
    post_data['proj_id'] = project_id

    instance = ProjectData.objects.filter(proj_id=project_id).first() or ProjectData(proj_id=project_id)
    for field_name, default_value in PROJECT_FORM_COLD_CABLE_DEFAULTS.items():
        if field_name not in post_data:
            post_data[field_name] = getattr(instance, field_name, default_value) or default_value
    if 'rcd_provided' not in post_data and getattr(instance, 'rcd_provided', True):
        post_data['rcd_provided'] = 'on'
    if 'eht_db_fault_rating_ka_preset' not in post_data:
        current_fault_rating = getattr(instance, 'eht_db_fault_rating_ka', 15) or 15
        current_fault_rating_text = f'{float(current_fault_rating):g}'
        if current_fault_rating_text in {'10', '15', '25', '40', '50'}:
            post_data['eht_db_fault_rating_ka_preset'] = current_fault_rating_text
            post_data.setdefault('eht_db_fault_rating_ka_custom', '')
        else:
            post_data['eht_db_fault_rating_ka_preset'] = 'OTHER'
            post_data['eht_db_fault_rating_ka_custom'] = current_fault_rating_text
    else:
        post_data.setdefault('eht_db_fault_rating_ka_custom', '')
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
    if request.user.is_authenticated:
        return redirect('base')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            next_url = request.POST.get('next', '').strip() or 'base'
            return redirect(next_url)
        error = 'Invalid username or password. Please try again.'
    return render(request, 'eht/my_login.html', {
        'error': error,
        'next': request.GET.get('next', ''),
    })


def my_logout(request):
    auth_logout(request)
    return redirect('my_login')


def my_register(request):
    return redirect('my_login')
