from copy import deepcopy

from django.core.exceptions import ValidationError

from .models import CableScheduleOverride, ProjectData


CABLE_COMPONENT_TYPES = {'Cable3C', 'Cable4C'}


def is_cable_node(node):
    return (node or {}).get('component_type') in CABLE_COMPONENT_TYPES


def _to_float(value):
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _generated_length(node):
    metadata = (node or {}).get('metadata') or {}
    return _to_float(metadata.get('generated_length_m') or metadata.get('length_m'))


def _generated_size(node):
    metadata = (node or {}).get('metadata') or {}
    return str(metadata.get('generated_cable_size') or metadata.get('cable_size') or '').strip()


def _active_overrides(project_id):
    if not project_id:
        return {}
    return {
        override.component_id: override
        for override in CableScheduleOverride.objects.filter(project_id=project_id, is_active=True)
    }


def apply_cable_overrides_to_payload(project_id, payload):
    adjusted = deepcopy(payload)
    overrides = _active_overrides(project_id)
    for node in adjusted.get('nodes', []):
        if not is_cable_node(node):
            continue
        metadata = dict(node.get('metadata') or {})
        generated_length = _generated_length(node)
        generated_size = _generated_size(node)
        override = overrides.get(node.get('component_id'))

        metadata['generated_length_m'] = generated_length
        metadata['generated_cable_size'] = generated_size
        metadata['length_m'] = generated_length
        metadata['cable_size'] = generated_size
        metadata['cable_override_active'] = False

        if override:
            if override.manual_length_m is not None:
                metadata['length_m'] = override.manual_length_m
                metadata['manual_length_m'] = override.manual_length_m
            if override.manual_cable_size:
                metadata['cable_size'] = override.manual_cable_size
                metadata['manual_cable_size'] = override.manual_cable_size
            metadata['cable_override_active'] = True
            metadata['cable_override_id'] = override.id
            metadata['cable_override_remarks'] = override.remarks

        node['metadata'] = metadata
    return adjusted


def find_cable_node(payload, component_id):
    for node in payload.get('nodes', []):
        if node.get('component_id') == component_id and is_cable_node(node):
            return node
    return None


def save_cable_override(project_id, node, *, manual_length_m=None, manual_cable_size='', remarks='', user=None):
    if not project_id or not node or not is_cable_node(node):
        raise ValidationError('A valid cable component is required.')
    manual_length = _to_float(manual_length_m)
    if manual_length is not None and manual_length <= 0:
        raise ValidationError('Manual cable length must be greater than zero.')
    manual_size = str(manual_cable_size or '').strip()
    project = ProjectData.objects.filter(proj_id=project_id).first()
    if project is None:
        raise ValidationError('Project setup is required before saving cable overrides.')

    override, _created = CableScheduleOverride.objects.update_or_create(
        project=project,
        component_id=node['component_id'],
        defaults={
            'component_uid': node.get('component_uid') or '',
            'display_tag': node.get('display_tag') or node.get('component_id'),
            'component_type': node.get('component_type') or '',
            'line_id': node.get('line_id') or '',
            'line_uid': node.get('line_uid') or '',
            'branch_index': node.get('branch_index') or 0,
            'circuit_index': node.get('circuit_index'),
            'generated_length_m': _generated_length(node),
            'manual_length_m': manual_length,
            'generated_cable_size': _generated_size(node),
            'manual_cable_size': manual_size,
            'remarks': str(remarks or '').strip(),
            'is_active': True,
            'updated_by': user if getattr(user, 'is_authenticated', False) else None,
        },
    )
    if override.created_by_id is None and getattr(user, 'is_authenticated', False):
        override.created_by = user
        override.save(update_fields=['created_by'])
    return override


def reset_cable_override(project_id, component_id):
    return CableScheduleOverride.objects.filter(
        project_id=project_id,
        component_id=component_id,
        is_active=True,
    ).update(is_active=False)


def cable_override_summary_by_branch(project_id, payload):
    summaries = {}
    for node in payload.get('nodes', []):
        if not is_cable_node(node):
            continue
        metadata = node.get('metadata') or {}
        if not metadata.get('cable_override_active'):
            continue
        key = (str(node.get('line_uid') or ''), node.get('branch_index') or 0)
        summaries.setdefault(key, []).append({
            'tag': node.get('display_tag') or '',
            'length_m': metadata.get('length_m'),
            'cable_size': metadata.get('cable_size') or '',
        })
    return summaries


def attach_cable_override_summaries(branch_rows, payload):
    summaries = cable_override_summary_by_branch(payload.get('project_id'), payload)
    for branch in branch_rows:
        line = None
        if isinstance(branch, dict):
            line = ((branch.get('distribution') or {}).get('line') or {})
            key = (str(line.get('uid') or ''), branch.get('branch_index') or 0)
            branch['cable_override_summary'] = summaries.get(key, [])
            branch['cable_override_count'] = len(branch['cable_override_summary'])
        else:
            line = branch.distribution.line
            key = (str(line.uid), branch.branch_index)
            branch.cable_override_summary = summaries.get(key, [])
            branch.cable_override_count = len(branch.cable_override_summary)
    return branch_rows
