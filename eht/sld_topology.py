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

OPERATION_INPUT_SCHEMA = {
    'combine_feeders': {
        'list_min': {'component_ids': 2},
        'positive_float': {'trunk_length_m'},
        'string': {'cable_size'},
    },
    'split_circuits': {
        'list_exact': {'component_ids': 1},
    },
    'downstream_jb': {
        'string': {'parent_component_id'},
        'list_min': {'branch_component_ids': 2},
        'positive_float': {'trunk_length_m'},
        'string': {'cable_size'},
    },
    'attach_to_jb': {
        'string': {'source_component_id', 'target_component_id'},
    },
    'move_branch_to_jb': {
        'string': {'source_component_id', 'target_component_id'},
    },
    'scoped_reset': {
        'string': {'component_id'},
        'list': {'reset_line_ids'},
    },
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


def _positive_number(value):
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def _operation_input_errors(operation_type, inputs, index):
    schema = OPERATION_INPUT_SCHEMA.get(operation_type) or {}
    errors = []
    for field in schema.get('string', set()):
        if not str(inputs.get(field) or '').strip():
            errors.append(f'Topology operation #{index} is missing input "{field}".')
    for field in schema.get('positive_float', set()):
        if not _positive_number(inputs.get(field)):
            errors.append(f'Topology operation #{index} input "{field}" must be a positive number.')
    for field in schema.get('list', set()):
        if not isinstance(inputs.get(field), list):
            errors.append(f'Topology operation #{index} input "{field}" must be a list.')
    for field, minimum in schema.get('list_min', {}).items():
        value = inputs.get(field)
        if not isinstance(value, list) or len([item for item in value if item]) < minimum:
            errors.append(f'Topology operation #{index} input "{field}" must contain at least {minimum} value(s).')
    for field, expected in schema.get('list_exact', {}).items():
        value = inputs.get(field)
        if not isinstance(value, list) or len([item for item in value if item]) != expected:
            errors.append(f'Topology operation #{index} input "{field}" must contain exactly {expected} value(s).')
    return errors


def validate_topology_operation_records(edit_payload_or_operations):
    if isinstance(edit_payload_or_operations, list):
        operations = edit_payload_or_operations
    else:
        operations = (edit_payload_or_operations or {}).get('topology_operations')
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
            continue
        if not isinstance(operation.get('inputs'), dict):
            errors.append(f'Topology operation #{index} is missing structured inputs.')
            continue
        errors.extend(_operation_input_errors(operation.get('operation_type'), operation['inputs'], index))
    return errors


def _cycle_errors(payload, node_id_set):
    outgoing = {node_id: [] for node_id in node_id_set}
    for edge in payload.get('edges', []):
        source_id = edge.get('from_component_id')
        target_id = edge.get('to_component_id')
        if source_id in node_id_set and target_id in node_id_set:
            outgoing.setdefault(source_id, []).append(target_id)

    visiting = set()
    visited = set()

    def visit(node_id, path):
        if node_id in visiting:
            return f"Cycle detected in SLD topology at {node_id}."
        if node_id in visited:
            return ''
        visiting.add(node_id)
        for target_id in outgoing.get(node_id, []):
            error = visit(target_id, [*path, node_id])
            if error:
                return error
        visiting.remove(node_id)
        visited.add(node_id)
        return ''

    errors = []
    for node_id in sorted(node_id_set):
        error = visit(node_id, [])
        if error:
            errors.append(error)
            break
    return errors


def validate_sld_topology_invariants(payload):
    payload = payload or {}
    errors = _payload_reference_errors(payload)
    warnings = []

    node_by_id = {
        node.get('component_id'): node
        for node in payload.get('nodes', [])
        if node.get('component_id')
    }
    node_id_set = set(node_by_id)
    incoming = {component_id: 0 for component_id in node_id_set}
    outgoing = {component_id: 0 for component_id in node_id_set}
    edge_keys = set()
    duplicate_edges = set()

    for edge in payload.get('edges', []):
        source_id = edge.get('from_component_id')
        target_id = edge.get('to_component_id')
        key = (
            source_id,
            target_id,
            edge.get('line_uid'),
            edge.get('branch_index'),
            edge.get('circuit_index'),
        )
        if key in edge_keys:
            duplicate_edges.add(f"{source_id or '-'} -> {target_id or '-'}")
        edge_keys.add(key)
        if source_id in outgoing:
            outgoing[source_id] += 1
        if target_id in incoming:
            incoming[target_id] += 1

    if duplicate_edges:
        errors.append(f"Duplicate topology edge(s): {', '.join(sorted(duplicate_edges))}.")

    for component_id, node in node_by_id.items():
        component_type = node.get('component_type')
        if component_type != 'MCB' and incoming.get(component_id, 0) > 1:
            errors.append(f"Component {node.get('display_tag') or component_id} has more than one upstream feed.")
        if component_type == 'JB3PH' and outgoing.get(component_id, 0) > 3:
            warnings.append(f"3PH JB {node.get('display_tag') or component_id} has more than three outgoing feeders.")

    errors.extend(_cycle_errors(payload, node_id_set))

    source_ids = [
        component_id
        for component_id, node in node_by_id.items()
        if node.get('component_type') == 'MCB' or incoming.get(component_id, 0) == 0
    ]
    reachable = set()
    stack = list(source_ids)
    outgoing_targets = {}
    for edge in payload.get('edges', []):
        outgoing_targets.setdefault(edge.get('from_component_id'), []).append(edge.get('to_component_id'))
    while stack:
        component_id = stack.pop()
        if component_id in reachable or component_id not in node_id_set:
            continue
        reachable.add(component_id)
        stack.extend(outgoing_targets.get(component_id, []))
    orphan_ids = sorted(node_id_set - reachable)
    if orphan_ids:
        warnings.append(f"Topology contains {len(orphan_ids)} component(s) not reachable from a source.")

    status = 'failed' if errors else ('warning' if warnings else 'passed')
    return {
        'status': status,
        'errors': errors,
        'warnings': warnings,
    }


def _operation_record_errors(edit_payload):
    return validate_topology_operation_records(edit_payload)


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
        if (edit.edit_payload or {}).get('topology_chain_compacted'):
            return _normalize_review_required_payload(
                generated_payload,
                project_id,
                edit,
                (
                    'Manual topology edit requires review because the generated SLD baseline changed after '
                    'the saved operation chain was compacted. Generated topology is shown until the edit is reviewed.'
                ),
            )
        operations = (edit.edit_payload or {}).get('topology_operations')
        if operations:
            from .sld_topology_workflows import replay_topology_operations

            replay_result = replay_topology_operations(project_id, generated_payload, operations)
            if replay_result.get('ok'):
                replay_validation = validate_sld_topology_invariants(replay_result['payload'])
                if replay_validation['errors']:
                    return _normalize_review_required_payload(
                        generated_payload,
                        project_id,
                        edit,
                        (
                            'Manual topology edit requires review because replay produced an invalid SLD graph: '
                            f"{' '.join(replay_validation['errors'])}"
                        ),
                    )
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
        invariant_summary = validate_sld_topology_invariants(edited_payload)
        if invariant_summary['errors']:
            return _normalize_review_required_payload(
                generated_payload,
                project_id,
                edit,
                (
                    'Manual topology edit requires review because its saved graph violates topology guard rails: '
                    f"{' '.join(invariant_summary['errors'])}"
                ),
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
