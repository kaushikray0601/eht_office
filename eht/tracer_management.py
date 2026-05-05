from django.core.exceptions import ValidationError

from .models import (
    AlternateTracer,
    HeatTracingInput,
    ProjectData,
    SelectedTracer,
    TracerSelectionOverride,
)


def _rounded_or_blank(value):
    if value in (None, ''):
        return ''
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return value


def _tracer_option_payload(tracer, option_rank=None):
    payload = {
        'v_uid': tracer.v_uid,
        'tracer_family': tracer.tracer_family,
        'power_output': _rounded_or_blank(tracer.power_output),
        'spiral_factor': _rounded_or_blank(tracer.spiral_factor),
        'tracer_length': _rounded_or_blank(tracer.tracer_length),
        'tracer_with_margin': _rounded_or_blank(tracer.tracer_with_margin),
    }
    if option_rank is not None:
        payload['option_rank'] = option_rank
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


def apply_tracer_selection_to_payload(project_id, payload):
    line_uids = {
        str(node.get('line_uid'))
        for node in payload.get('nodes', [])
        if node.get('component_type') == 'Tracer' and node.get('line_uid')
    }
    if not line_uids:
        return payload

    selected_by_line_uid = {
        str(tracer.line_id): tracer
        for tracer in SelectedTracer.objects.filter(line_id__in=line_uids)
    }
    alternate_by_line_uid = {}
    for alternate in AlternateTracer.objects.filter(line_id__in=line_uids).order_by('line_id', 'option_rank'):
        alternate_by_line_uid.setdefault(str(alternate.line_id), []).append(alternate)
    overrides = _active_overrides(project_id, line_uids)

    for node in payload.get('nodes', []):
        if node.get('component_type') != 'Tracer':
            continue
        line_uid = str(node.get('line_uid') or '')
        selected = selected_by_line_uid.get(line_uid)
        alternatives = alternate_by_line_uid.get(line_uid, [])
        override = overrides.get(line_uid)
        active_option = None
        if override:
            active_option = next(
                (option for option in alternatives if option.v_uid == override.selected_v_uid),
                None,
            )
        selected_payload = _tracer_option_payload(active_option, active_option.option_rank) if active_option else (
            _tracer_option_payload(selected) if selected else {}
        )
        metadata = dict(node.get('metadata') or {})
        metadata['tracer_selection'] = {
            'selected': selected_payload,
            'generated_selected': _tracer_option_payload(selected) if selected else {},
            'alternatives': [
                _tracer_option_payload(alternate, alternate.option_rank)
                for alternate in alternatives
            ],
            'alternate_count': len(alternatives),
            'override_supported': bool(alternatives),
            'override_active': bool(active_option),
            'override_id': override.id if active_option else None,
            'override_remarks': override.remarks if active_option else '',
        }
        node['metadata'] = metadata
    return payload


def find_tracer_node(payload, component_id):
    for node in payload.get('nodes', []):
        if node.get('component_id') == component_id and node.get('component_type') == 'Tracer':
            return node
    return None


def save_tracer_override(project_id, node, *, selected_v_uid='', remarks='', user=None):
    selected_uid = str(selected_v_uid or '').strip()
    line_uid = str((node or {}).get('line_uid') or '')
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
    return TracerSelectionOverride.objects.filter(
        project_id=project_id,
        line_id=line_uid,
        is_active=True,
    ).update(is_active=False)
