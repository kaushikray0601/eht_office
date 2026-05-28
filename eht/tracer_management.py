from django.core.exceptions import ValidationError

from .models import (
    AlternateTracer,
    HeatLoss,
    HeatTracingInput,
    ProcessLineCalculation,
    ProjectData,
    SelectedMIHeater,
    SelectedTracer,
    TracerSelectionOverride,
)


def _rounded_or_blank(value):
    if value in (None, ''):
        return ''
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return value


def _tracer_option_payload(tracer, option_rank=None):
    payload = {
        'v_uid': tracer.v_uid,
        'tracer_family': tracer.tracer_family,
        'power_output': _rounded_or_blank(tracer.power_output),
        'spiral_factor': _rounded_or_blank(tracer.spiral_factor),
        'sr_parallel_run_count': getattr(tracer, 'sr_parallel_run_count', 1),
        'sr_parallel_run_basis': getattr(tracer, 'sr_parallel_run_basis', ''),
        'sr_constructability_warning': getattr(tracer, 'sr_constructability_warning', ''),
        'sr_per_run_tracer_length': _rounded_or_blank(getattr(tracer, 'sr_per_run_tracer_length', 0)),
        'tracer_length': _rounded_or_blank(tracer.tracer_length),
        'tracer_with_margin': _rounded_or_blank(tracer.tracer_with_margin),
    }
    if option_rank is not None:
        payload['option_rank'] = option_rank
    return payload


def _mi_option_uid(mi_result):
    heater = mi_result.heater
    part_number = heater.part_number if heater else ''
    return f"MI:{part_number}:{mi_result.cold_lead_option_code}"


def _mi_option_payload(mi_result, option_rank=None):
    heater = mi_result.heater
    payload = {
        'v_uid': _mi_option_uid(mi_result),
        'tracer_family': 'MI',
        'power_output': _rounded_or_blank(mi_result.power_density_w_m),
        'spiral_factor': '',
        'tracer_length': _rounded_or_blank(mi_result.heated_length_m),
        'tracer_with_margin': _rounded_or_blank(mi_result.heated_length_m),
        'option_kind': 'MI',
        'heater_part_number': heater.part_number if heater else '',
        'cold_lead_option_code': mi_result.cold_lead_option_code,
        'current_nominal_a': _rounded_or_blank(mi_result.current_nominal_a),
        'current_cold_start_a': _rounded_or_blank(mi_result.current_cold_start_a),
        't_class_verdict': mi_result.t_class_verdict,
        'selection_status': mi_result.selection_status,
    }
    if option_rank is not None:
        payload['option_rank'] = option_rank
    return payload


def _tracer_display_label(selected_payload, mi_result=None):
    if selected_payload.get('option_kind') == 'MI':
        return selected_payload.get('heater_part_number') or selected_payload.get('v_uid') or 'MI tracer'
    if selected_payload.get('v_uid'):
        return selected_payload['v_uid']
    if mi_result and mi_result.selection_status == 'selected':
        heater = mi_result.heater
        return heater.part_number if heater else 'MI tracer'
    return ''


def _heat_loss_payload(heat_loss):
    if not heat_loss:
        return {}
    basis = heat_loss.conductivity_basis or {}
    return {
        'design_heat_loss': _rounded_or_blank(heat_loss.design_heat_loss),
        'base_heat_loss': _rounded_or_blank(heat_loss.base_heat_loss),
        'heat_loss_sf': _rounded_or_blank(heat_loss.heat_loss_sf),
        'conductivity': _rounded_or_blank(heat_loss.conductivity),
        'conductivity_method': basis.get('effective_method_label') or basis.get('effective_method') or '',
        'conductivity_rule_set': basis.get('rule_set') or '',
        'wind_correction': _rounded_or_blank(heat_loss.wind_correction),
        'accessory_tracer_adders_m': _rounded_or_blank(heat_loss.tracer_adder),
        'selection_status': heat_loss.selection_status,
        'selection_rejection_reasons': heat_loss.selection_rejection_reasons or [],
    }


def _calculation_payload(calculation, selected):
    if not calculation:
        return {}
    payload = {
        'breaker_size': _rounded_or_blank(calculation.breaker_size),
        'total_circuits': calculation.total_circuits,
        'starting_current_per_circuit': _rounded_or_blank(calculation.starting_current),
        'operating_current_per_circuit': _rounded_or_blank(calculation.operating_current),
        'current_basis': 'per_circuit',
        'total_connected_load_w': _rounded_or_blank(calculation.total_power_consumption),
        'ordered_tracer_length_m': _rounded_or_blank(calculation.total_tracer_length),
        'tracer_length_basis': 'ordered_length_includes_termination_allowance',
        'sr_parallel_run_count': getattr(calculation, 'sr_parallel_run_count', 1),
        'sr_parallel_run_basis': getattr(calculation, 'sr_parallel_run_basis', ''),
        'sr_constructability_warning': getattr(calculation, 'sr_constructability_warning', ''),
    }
    if selected:
        payload['heated_tracer_length_excluding_termination_m'] = _rounded_or_blank(selected.tracer_with_margin)
    return payload


def _active_overrides(project_id, line_uids):
    if not project_id or not line_uids:
        return {}
    return {
        str(override.line_id): override
        for override in TracerSelectionOverride.objects.filter(
            project_id=project_id,
            line_id__in=line_uids,
            is_active=True,
        )
    }


def _source_line_uid(node):
    metadata = (node or {}).get('metadata') or {}
    return str(metadata.get('original_line_uid') or (node or {}).get('line_uid') or '')


def _real_line_uids(nodes):
    line_uids = {
        _source_line_uid(node)
        for node in nodes
        if node.get('component_type') == 'Tracer' and _source_line_uid(node)
    }
    return {
        line_uid
        for line_uid in line_uids
        if str(line_uid).isdigit()
    }


def apply_tracer_selection_to_payload(project_id, payload):
    line_uids = _real_line_uids(payload.get('nodes', []))
    if not line_uids:
        return payload

    selected_by_line_uid = {
        str(tracer.line_id): tracer
        for tracer in SelectedTracer.objects.filter(line_id__in=line_uids)
    }
    heat_loss_by_line_uid = {
        str(heat_loss.line_id): heat_loss
        for heat_loss in HeatLoss.objects.filter(line_id__in=line_uids)
    }
    calculation_by_line_uid = {
        str(calculation.line_id): calculation
        for calculation in ProcessLineCalculation.objects.filter(line_id__in=line_uids)
    }
    alternate_by_line_uid = {}
    for alternate in AlternateTracer.objects.filter(line_id__in=line_uids).order_by('line_id', 'option_rank'):
        alternate_by_line_uid.setdefault(str(alternate.line_id), []).append(alternate)
    mi_by_line_uid = {
        str(mi_result.line_id): mi_result
        for mi_result in SelectedMIHeater.objects.filter(
            line_id__in=line_uids,
            selection_status__in=['available_alternative', 'selected'],
        ).select_related('heater', 'cold_lead_option')
    }
    overrides = _active_overrides(project_id, line_uids)

    for node in payload.get('nodes', []):
        if node.get('component_type') != 'Tracer':
            continue
        line_uid = _source_line_uid(node)
        selected = selected_by_line_uid.get(line_uid)
        alternatives = alternate_by_line_uid.get(line_uid, [])
        mi_result = mi_by_line_uid.get(line_uid)
        alternative_payloads = [
            _tracer_option_payload(alternate, alternate.option_rank)
            for alternate in alternatives
        ]
        if mi_result and mi_result.selection_status == 'available_alternative':
            alternative_payloads.append(_mi_option_payload(mi_result, len(alternative_payloads) + 1))
        override = overrides.get(line_uid)
        active_payload = None
        if override:
            active_payload = next(
                (option for option in alternative_payloads if option.get('v_uid') == override.selected_v_uid),
                None,
            )
        selected_payload = active_payload or (
            _mi_option_payload(mi_result) if mi_result and mi_result.selection_status == 'selected'
            else _tracer_option_payload(selected) if selected
            else {}
        )
        calculation = calculation_by_line_uid.get(line_uid)
        heat_loss = heat_loss_by_line_uid.get(line_uid)
        metadata = dict(node.get('metadata') or {})
        metadata['tracer_selection'] = {
            'selected': selected_payload,
            'generated_selected': _tracer_option_payload(selected) if selected else {},
            'alternatives': alternative_payloads,
            'alternate_count': len(alternative_payloads),
            'override_supported': bool(alternative_payloads),
            'override_active': bool(active_payload),
            'override_id': override.id if active_payload else None,
            'override_remarks': override.remarks if active_payload else '',
        }
        metadata['sr_calculation'] = {
            'heat_loss': _heat_loss_payload(heat_loss),
            'electrical': _calculation_payload(calculation, selected),
        }
        node['metadata'] = metadata
        display_label = _tracer_display_label(selected_payload, mi_result=mi_result)
        if display_label:
            node['display_name'] = display_label
            node['label'] = display_label
    return payload


def find_tracer_node(payload, component_id):
    for node in payload.get('nodes', []):
        if node.get('component_id') == component_id and node.get('component_type') == 'Tracer':
            return node
    return None


def save_tracer_override(project_id, node, *, selected_v_uid='', remarks='', user=None):
    selected_uid = str(selected_v_uid or '').strip()
    line_uid = _source_line_uid(node)
    if not project_id or not node or node.get('component_type') != 'Tracer' or not line_uid:
        raise ValidationError('A valid tracer component is required.')
    if not selected_uid:
        raise ValidationError('Select one calculated alternate tracer option.')

    project = ProjectData.objects.filter(proj_id=project_id).first()
    line = HeatTracingInput.objects.filter(uid=line_uid, proj_id=project_id).first()
    if project is None or line is None:
        raise ValidationError('Project setup and source line are required before saving tracer overrides.')

    generated = SelectedTracer.objects.filter(line=line).first()
    if generated and selected_uid == generated.v_uid:
        reset_tracer_override(project_id, line_uid)
        return None

    if selected_uid.startswith('MI:'):
        try:
            _prefix, heater_part_number, cold_lead_option_code = selected_uid.split(':', 2)
        except ValueError:
            raise ValidationError('Selected MI tracer option is not valid.')
        mi_result = SelectedMIHeater.objects.filter(
            line=line,
            heater__part_number=heater_part_number,
            cold_lead_option_code=cold_lead_option_code,
            selection_status='available_alternative',
        ).first()
        if mi_result is None:
            raise ValidationError('Selected MI tracer must be one of the calculated MI alternate options for this line.')
        override, _created = TracerSelectionOverride.objects.update_or_create(
            project=project,
            line=line,
            defaults={
                'selected_v_uid': selected_uid,
                'selected_option_rank': None,
                'remarks': str(remarks or '').strip(),
                'is_active': True,
                'updated_by': user if getattr(user, 'is_authenticated', False) else None,
            },
        )
        if override.created_by_id is None and getattr(user, 'is_authenticated', False):
            override.created_by = user
            override.save(update_fields=['created_by'])
        return override

    alternate = AlternateTracer.objects.filter(line=line, v_uid=selected_uid).order_by('option_rank').first()
    if alternate is None:
        raise ValidationError('Selected tracer must be one of the calculated alternate options for this line.')

    override, _created = TracerSelectionOverride.objects.update_or_create(
        project=project,
        line=line,
        defaults={
            'selected_v_uid': alternate.v_uid,
            'selected_option_rank': alternate.option_rank,
            'remarks': str(remarks or '').strip(),
            'is_active': True,
            'updated_by': user if getattr(user, 'is_authenticated', False) else None,
        },
    )
    if override.created_by_id is None and getattr(user, 'is_authenticated', False):
        override.created_by = user
        override.save(update_fields=['created_by'])
    return override


def reset_tracer_override(project_id, line_uid):
    line_uid = str(line_uid or '').split(':manual_split:', 1)[0]
    return TracerSelectionOverride.objects.filter(
        project_id=project_id,
        line_id=line_uid,
        is_active=True,
    ).update(is_active=False)
