from copy import deepcopy

from .models import SLDTopologyEdit


def get_active_topology_edit(project_id):
    if not project_id:
        return None
    return (
        SLDTopologyEdit.objects
        .filter(project_id=project_id, status='applied')
        .order_by('-created_at', '-id')
        .first()
    )


def _sort_node(node):
    circuit_index = node.get('circuit_index')
    return (
        str(node.get('line_id') or ''),
        str(node.get('line_uid') or ''),
        node.get('branch_index') or 0,
        -1 if circuit_index is None else circuit_index,
        str(node.get('component_type') or ''),
        str(node.get('component_id') or ''),
    )


def _sort_edge(edge):
    circuit_index = edge.get('circuit_index')
    return (
        ','.join(str(line_id) for line_id in edge.get('line_ids', [])),
        str(edge.get('line_uid') or ''),
        edge.get('branch_index') or 0,
        -1 if circuit_index is None else circuit_index,
        str(edge.get('from_component_id') or ''),
        str(edge.get('to_component_id') or ''),
    )


def _sort_line_group(group):
    return (
        str(group.get('line_id') or ''),
        str(group.get('line_uid') or ''),
    )


def _normalize_payload(payload, project_id, edit):
    normalized = deepcopy(payload)
    normalized['project_id'] = project_id
    normalized['nodes'] = sorted(normalized.get('nodes', []), key=_sort_node)
    normalized['edges'] = sorted(normalized.get('edges', []), key=_sort_edge)
    normalized['line_groups'] = sorted(normalized.get('line_groups', []), key=_sort_line_group)

    meta = dict(normalized.get('meta') or {})
    meta.update({
        'node_count': len(normalized['nodes']),
        'edge_count': len(normalized['edges']),
        'branch_count': meta.get(
            'branch_count',
            sum(len(group.get('branch_indices', [])) for group in normalized['line_groups']),
        ),
        'has_topology_edit': True,
        'topology_edit_id': edit.id,
        'topology_edit_type': edit.edit_type,
        'topology_edit_status': edit.status,
    })
    normalized['meta'] = meta
    return normalized


def apply_active_topology_edit(project_id, generated_payload):
    edit = get_active_topology_edit(project_id)
    if edit is None:
        return generated_payload

    edited_payload = (edit.edit_payload or {}).get('sld_payload')
    if isinstance(edited_payload, dict):
        return _normalize_payload(edited_payload, project_id, edit)

    return _normalize_payload(generated_payload, project_id, edit)


def apply_active_summary_overrides(project_id, summary_name, summary):
    edit = get_active_topology_edit(project_id)
    if edit is None:
        return summary

    overrides = (edit.edit_payload or {}).get('downstream_summaries', {}).get(summary_name)
    if not isinstance(overrides, dict):
        return summary

    adjusted = {**summary, **overrides}
    adjusted.update({
        'has_topology_edit': True,
        'topology_edit_id': edit.id,
        'topology_edit_type': edit.edit_type,
    })
    return adjusted


def apply_active_cable_schedule_rows(project_id, branch_rows):
    edit = get_active_topology_edit(project_id)
    if edit is None:
        return branch_rows

    rows = (edit.edit_payload or {}).get('cable_schedule_rows')
    if not isinstance(rows, list):
        return branch_rows

    return deepcopy(rows)
