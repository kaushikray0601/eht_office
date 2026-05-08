from copy import deepcopy
import hashlib
import json

from .models import SLDTopologyEdit


TOPOLOGY_OPERATION_SCHEMA_VERSION = 1
KNOWN_TOPOLOGY_OPERATION_TYPES = {
    'combine_feeders',
    'split_circuits',
    'downstream_jb',
    'attach_to_jb',
    'move_branch_to_jb',
    'scoped_reset',
}


def payload_fingerprint(payload):
    stable_payload = {
        'schema_version': payload.get('schema_version'),
        'nodes': sorted(
            (
                node.get('component_id'),
                node.get('component_type'),
                node.get('line_uid'),
                node.get('branch_index'),
                node.get('circuit_index'),
                node.get('display_tag'),
                node.get('metadata') or {},
            )
            for node in payload.get('nodes', [])
        ),
        'edges': sorted(
            (
                edge.get('from_component_id'),
                edge.get('to_component_id'),
                edge.get('line_uid'),
                edge.get('branch_index'),
                edge.get('circuit_index'),
            )
            for edge in payload.get('edges', [])
        ),
        'line_groups': sorted(
            (
                group.get('line_uid'),
                group.get('line_id'),
                tuple(group.get('branch_indices') or []),
            )
            for group in payload.get('line_groups', [])
        ),
    }
    return hashlib.sha256(
        json.dumps(stable_payload, sort_keys=True, default=str).encode('utf-8')
    ).hexdigest()


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


def _normalize_payload(payload, project_id, edit, generated_payload=None):
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
        'topology_baseline_changed': bool(
            edit.baseline_fingerprint
            and edit.baseline_fingerprint != payload_fingerprint(generated_payload or payload)
        ),
    })
    normalized['meta'] = meta
    return normalized


def _baseline_changed(edit, generated_payload):
    return bool(
        edit.baseline_fingerprint
        and edit.baseline_fingerprint != payload_fingerprint(generated_payload)
    )


def _payload_reference_errors(payload):
    node_ids = []
    duplicate_ids = set()
    seen_ids = set()
    for node in payload.get('nodes', []):
        component_id = node.get('component_id')
        if not component_id:
            continue
        if component_id in seen_ids:
            duplicate_ids.add(component_id)
        seen_ids.add(component_id)
        node_ids.append(component_id)

    node_id_set = set(node_ids)
    errors = []
    if duplicate_ids:
        errors.append(f"Duplicate component IDs: {', '.join(sorted(duplicate_ids))}.")
    for edge in payload.get('edges', []):
        source_id = edge.get('from_component_id')
        target_id = edge.get('to_component_id')
        if source_id not in node_id_set or target_id not in node_id_set:
            errors.append(
                f"Invalid edge reference: {source_id or '-'} -> {target_id or '-'}."
            )
    return errors


def _operation_record_errors(edit_payload):
    operations = (edit_payload or {}).get('topology_operations')
    if operations is None:
        return []
    if not isinstance(operations, list):
        return ['Topology operation records must be stored as a list.']

    errors = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            errors.append(f'Topology operation #{index} is not a structured record.')
            continue
        if operation.get('schema_version') != TOPOLOGY_OPERATION_SCHEMA_VERSION:
            errors.append(f'Topology operation #{index} has an unsupported schema version.')
        if operation.get('operation_type') not in KNOWN_TOPOLOGY_OPERATION_TYPES:
            errors.append(f'Topology operation #{index} has an unknown operation type.')
        if not isinstance(operation.get('inputs'), dict):
            errors.append(f'Topology operation #{index} is missing structured inputs.')
    return errors


def _normalize_review_required_payload(generated_payload, project_id, edit, warning):
    normalized = _normalize_payload(generated_payload, project_id, edit, generated_payload=generated_payload)
    meta = dict(normalized.get('meta') or {})
    meta.update({
        'topology_edit_review_required': True,
        'manual_topology_warning': warning,
    })
    normalized['meta'] = meta
    return normalized


def apply_active_topology_edit(project_id, generated_payload):
    edit = get_active_topology_edit(project_id)
    if edit is None:
        return generated_payload

    edited_payload = (edit.edit_payload or {}).get('sld_payload')
    operation_errors = _operation_record_errors(edit.edit_payload)
    if operation_errors:
        return _normalize_review_required_payload(
            generated_payload,
            project_id,
            edit,
            'Manual topology edit requires review because its operation records are invalid.',
        )

    if _baseline_changed(edit, generated_payload):
        operations = (edit.edit_payload or {}).get('topology_operations')
        if operations:
            from .sld_topology_workflows import replay_topology_operations

            replay_result = replay_topology_operations(project_id, generated_payload, operations)
            if replay_result.get('ok'):
                normalized = _normalize_payload(
                    replay_result['payload'],
                    project_id,
                    edit,
                    generated_payload=generated_payload,
                )
                meta = dict(normalized.get('meta') or {})
                meta.update({
                    'topology_edit_replayed_on_current_baseline': True,
                    'topology_edit_review_required': False,
                    'manual_topology_warning': (
                        'Manual topology edit was replayed from audited operation records on the current generated baseline. '
                        'Review affected ratings and cable data before issue.'
                    ),
                })
                normalized['meta'] = meta
                return normalized

            failed_message = replay_result.get('error') or 'The saved operation could not be matched safely.'
            failed_index = replay_result.get('failed_operation_index')
            failed_type = replay_result.get('failed_operation_type')
            operation_context = (
                f" Operation #{failed_index} ({failed_type}) failed: {failed_message}"
                if failed_index
                else f" {failed_message}"
            )
        else:
            operation_context = ' No replayable operation records are available.'

        return _normalize_review_required_payload(
            generated_payload,
            project_id,
            edit,
            (
                'Manual topology edit requires review because the generated SLD baseline changed. '
                'Generated topology is shown until the manual edit can be reapplied safely.'
                f'{operation_context}'
            ),
        )

    if isinstance(edited_payload, dict):
        reference_errors = _payload_reference_errors(edited_payload)
        if reference_errors:
            return _normalize_review_required_payload(
                generated_payload,
                project_id,
                edit,
                'Manual topology edit requires review because its saved graph references are invalid.',
            )
        return _normalize_payload(edited_payload, project_id, edit, generated_payload=generated_payload)

    return _normalize_payload(generated_payload, project_id, edit, generated_payload=generated_payload)


def apply_active_summary_overrides(project_id, summary_name, summary, *, allow_stale=True):
    edit = get_active_topology_edit(project_id)
    if edit is None:
        return summary
    if not allow_stale:
        adjusted = {**summary}
        adjusted.update({
            'has_topology_edit': True,
            'topology_edit_id': edit.id,
            'topology_edit_type': edit.edit_type,
            'topology_edit_review_required': True,
        })
        return adjusted

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


def apply_active_cable_schedule_rows(project_id, branch_rows, *, allow_stale=True):
    edit = get_active_topology_edit(project_id)
    if edit is None:
        return branch_rows
    if not allow_stale:
        return branch_rows

    rows = (edit.edit_payload or {}).get('cable_schedule_rows')
    if not isinstance(rows, list):
        return branch_rows

    return deepcopy(rows)
