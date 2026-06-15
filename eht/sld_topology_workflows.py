from copy import deepcopy
import hashlib

from django.db import transaction

from .cold_cable import (
    ColdCable3CSegmentLength,
    ColdCableSizingInput,
    build_cold_cable_sizing_snapshot,
)
from .models import MAX_CB_SIZE, ProcessLineCalculation, ProjectData, SLDTopologyEdit
from .sld_payload import build_project_sld_payload
from .sld_topology import (
    TOPOLOGY_OPERATION_SCHEMA_VERSION,
    payload_fingerprint,
    validate_sld_topology_invariants,
    validate_topology_operation_records,
)


SLD_OPERATION_CHAIN_COMPACT_THRESHOLD = 40
SLD_OPERATION_CHAIN_KEEP_COUNT = 12


def _topology_operation(operation_type, preview, inputs):
    return {
        'schema_version': TOPOLOGY_OPERATION_SCHEMA_VERSION,
        'operation_type': operation_type,
        'inputs': inputs,
        'preview': preview,
    }


def _active_topology_edit(project, *, for_update=False):
    query = (
        SLDTopologyEdit.objects
        .filter(project=project, status='applied')
        .order_by('-created_at', '-id')
    )
    if for_update:
        query = query.select_for_update()
    return query.first()


def _active_topology_operations(project):
    active_edit = _active_topology_edit(project)
    operations = (active_edit.edit_payload or {}).get('topology_operations') if active_edit else []
    return deepcopy(operations) if isinstance(operations, list) else []


def _replayable_active_topology_operations(project, generated_payload):
    active_edit = _active_topology_edit(project)
    operations = (active_edit.edit_payload or {}).get('topology_operations') if active_edit else []
    operations = deepcopy(operations) if isinstance(operations, list) else []
    if not operations:
        return [], {}
    if (active_edit.edit_payload or {}).get('topology_chain_compacted'):
        return [], {
            'source_edit_id': active_edit.id,
            'source_operation_count': len(operations),
            'dropped_operation_count': len(operations),
            'reason': 'compacted_active_chain_cannot_be_replayed_as_inheritance',
        }
    replay = replay_topology_operations(project.proj_id, generated_payload, operations)
    if replay.get('ok'):
        return operations, {}
    return [], {
        'source_edit_id': active_edit.id,
        'source_operation_count': len(operations),
        'dropped_operation_count': len(operations),
        'reason': 'active_chain_failed_replay',
        'failed_operation_index': replay.get('failed_operation_index'),
        'failed_operation_type': replay.get('failed_operation_type'),
        'error': replay.get('error') or '',
    }


def _compact_topology_operation_chain(operations):
    if len(operations) <= SLD_OPERATION_CHAIN_COMPACT_THRESHOLD:
        return operations, {}
    kept = operations[-SLD_OPERATION_CHAIN_KEEP_COUNT:]
    dropped = len(operations) - len(kept)
    digest = hashlib.sha256(repr(operations).encode('utf-8')).hexdigest()
    return kept, {
        'operation_chain_compacted': True,
        'original_operation_count': len(operations),
        'kept_operation_count': len(kept),
        'dropped_operation_count': dropped,
        'operation_chain_digest': digest,
        'reason': 'operation_chain_length_threshold',
    }


def _topology_operation_chain(project, operation_type, preview, inputs, generated_payload=None):
    if generated_payload is not None:
        inherited_operations, inheritance_audit = _replayable_active_topology_operations(project, generated_payload)
    else:
        inherited_operations, inheritance_audit = _active_topology_operations(project), {}
    operations = [
        *inherited_operations,
        _topology_operation(operation_type, preview, inputs),
    ]
    operations, compaction_audit = _compact_topology_operation_chain(operations)
    audit = {}
    if inheritance_audit:
        audit['inheritance'] = inheritance_audit
    if compaction_audit:
        audit['compaction'] = compaction_audit
    return operations, audit


def _next_breaker_size(total_rating):
    ratings = [value for value, _label in MAX_CB_SIZE]
    return next((rating for rating in ratings if rating >= total_rating), None)


def _breaker_rating(node):
    try:
        return float((node.get('metadata') or {}).get('breaker_size') or 0)
    except (TypeError, ValueError):
        return 0


def _starting_current(node):
    try:
        return float((node.get('metadata') or {}).get('starting_current') or 0)
    except (TypeError, ValueError):
        return 0


def _project_line_current_lookup(project_id):
    lookup = {'by_uid': {}, 'by_line_id': {}}
    if not project_id:
        return lookup
    calculations = (
        ProcessLineCalculation.objects
        .filter(line__proj_id=project_id)
        .select_related('line')
    )
    for calculation in calculations:
        current = float(calculation.starting_current or 0)
        if current <= 0:
            continue
        lookup['by_uid'][str(calculation.line_id)] = current
        line_id = calculation.line.line_id if calculation.line else ''
        if line_id:
            lookup['by_line_id'][line_id] = lookup['by_line_id'].get(line_id, 0) + current
    return lookup


def _project_line_operating_current_lookup(project_id):
    lookup = {'by_uid': {}, 'by_line_id': {}}
    if not project_id:
        return lookup
    calculations = (
        ProcessLineCalculation.objects
        .filter(line__proj_id=project_id)
        .select_related('line')
    )
    for calculation in calculations:
        current = float(calculation.operating_current or 0)
        if current <= 0:
            continue
        lookup['by_uid'][str(calculation.line_id)] = current
        line_id = calculation.line.line_id if calculation.line else ''
        if line_id:
            lookup['by_line_id'][line_id] = lookup['by_line_id'].get(line_id, 0) + current
    return lookup


def _node_starting_current(node, current_lookup=None):
    current = _starting_current(node)
    if current > 0:
        return current
    if not current_lookup:
        return 0

    line_uids, line_ids = _node_line_identity(node)
    if line_ids:
        by_line_id = current_lookup.get('by_line_id') or {}
        line_id_current = sum(by_line_id.get(line_id, 0) for line_id in line_ids)
        if line_id_current > 0:
            return line_id_current
    by_uid = current_lookup.get('by_uid') or {}
    return sum(by_uid.get(str(line_uid), 0) for line_uid in line_uids)


def _node_operating_current(node, current_lookup=None):
    metadata = node.get('metadata') or {}
    for key in ('combined_feeder_operating_current', 'line_operating_current', 'operating_current', 'per_circuit_operating_current'):
        current = _to_positive_float(metadata.get(key))
        if current is not None:
            return current
    if not current_lookup:
        return 0

    line_uids, line_ids = _node_line_identity(node)
    if line_ids:
        by_line_id = current_lookup.get('by_line_id') or {}
        line_id_current = sum(by_line_id.get(line_id, 0) for line_id in line_ids)
        if line_id_current > 0:
            return line_id_current
    by_uid = current_lookup.get('by_uid') or {}
    return sum(by_uid.get(str(line_uid), 0) for line_uid in line_uids)


def _combined_feeder_current(nodes, current_lookup=None):
    currents = [_node_starting_current(node, current_lookup) for node in nodes]
    if currents and all(current > 0 for current in currents):
        return sum(currents), 'starting_current'
    return sum(_breaker_rating(node) for node in nodes), 'breaker_rating'


def _combined_feeder_operating_current(nodes, current_lookup=None):
    currents = [_node_operating_current(node, current_lookup) for node in nodes]
    positive_currents = [current for current in currents if current > 0]
    if currents and len(positive_currents) == len(currents):
        return sum(positive_currents), max(positive_currents), 'operating_current', positive_currents
    fallback_total = sum(_breaker_rating(node) for node in nodes)
    fallback_per_branch = fallback_total / len(nodes) if nodes else 0
    return fallback_total, fallback_per_branch, 'breaker_rating_fallback', positive_currents


def _mcb_nodes_by_id(payload):
    return {
        node['component_id']: node
        for node in payload.get('nodes', [])
        if node.get('component_type') == 'MCB'
    }


def _node_lookup(payload):
    return {
        node['component_id']: node
        for node in payload.get('nodes', [])
    }


def _edge_lookup(payload):
    incoming = {}
    outgoing = {}
    for edge in payload.get('edges', []):
        incoming.setdefault(edge['to_component_id'], []).append(edge)
        outgoing.setdefault(edge['from_component_id'], []).append(edge)
    return incoming, outgoing


def _descendant_component_ids(payload, source_component_id):
    node_by_id = _node_lookup(payload)
    _incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    descendants = set()
    stack = [source_component_id]
    while stack:
        component_id = stack.pop()
        for edge in outgoing_by_id.get(component_id, []):
            target_id = edge.get('to_component_id')
            if not target_id or target_id in descendants or target_id not in node_by_id:
                continue
            descendants.add(target_id)
            stack.append(target_id)
    return descendants


def _upstream_mcb_node(payload, component_id):
    node_by_id = _node_lookup(payload)
    incoming_by_id, _outgoing_by_id = _edge_lookup(payload)
    visited = set()
    stack = [component_id]
    while stack:
        cursor = stack.pop()
        if cursor in visited:
            continue
        visited.add(cursor)
        node = node_by_id.get(cursor)
        if node and node.get('component_type') == 'MCB':
            return node
        for edge in incoming_by_id.get(cursor, []):
            parent_id = edge.get('from_component_id')
            if parent_id and parent_id not in visited:
                stack.append(parent_id)
    return None


def _selected_mcb_nodes(payload, component_ids):
    lookup = _mcb_nodes_by_id(payload)
    selected = []
    invalid_ids = []
    for component_id in component_ids:
        node = lookup.get(component_id)
        if node is None:
            invalid_ids.append(component_id)
        else:
            selected.append(node)
    selected.sort(key=_mcb_selection_sort_key)
    return selected, invalid_ids


def _mcb_selection_sort_key(node):
    metadata = node.get('metadata') or {}
    return (
        0 if metadata.get('manual_topology_edit') == 'combine_feeders' else 1,
        str(node.get('line_id') or ''),
        str(node.get('line_uid') or ''),
        node.get('branch_index') or 0,
        str(node.get('display_tag') or ''),
    )


def _component_uid(component_id):
    return hashlib.sha256(component_id.encode('utf-8')).hexdigest()[:32]


def _dedupe_edges(edges):
    deduped = []
    seen = set()
    for edge in edges:
        key = (
            edge.get('from_component_id'),
            edge.get('to_component_id'),
            edge.get('line_uid'),
            edge.get('branch_index'),
            edge.get('circuit_index'),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(edge)
    return deduped


def _graph_component_count(payload, component_types):
    component_types = set(component_types)
    return sum(1 for node in payload.get('nodes', []) if node.get('component_type') in component_types)


def _requires_incoming_isolator(isolator_location):
    return isolator_location in {'bothSides', 'incomingOnly'}


def _node_line_ids(nodes):
    return sorted({
        line_id
        for node in nodes
        for line_id in (node.get('line_ids') or ([node.get('line_id')] if node.get('line_id') else []))
        if line_id
    })


def _to_positive_float(value, default=None):
    if value in (None, ''):
        value = default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _manual_trunk_size(value):
    return str(value or '').strip() or '4C'


def _lock_project_for_topology_apply(project_id):
    return ProjectData.objects.select_for_update().get(proj_id=project_id)


def _topology_validation_summary(preview, edited_payload, topology_operations):
    warnings = [preview.get('warning') or 'Manual topology edit requires engineering review.']
    operation_errors = validate_topology_operation_records(topology_operations)
    invariant_summary = validate_sld_topology_invariants(edited_payload)
    errors = [*operation_errors, *invariant_summary.get('errors', [])]
    warnings.extend(invariant_summary.get('warnings', []))
    return {
        'status': 'failed' if errors else 'needs_review',
        'errors': errors,
        'warnings': [warning for warning in warnings if warning],
        'topology_invariants': invariant_summary,
        'operation_count': len(topology_operations),
    }


def _finalize_edit_payload(
    edited_payload,
    topology_operations,
    preview,
    *,
    preview_key,
    boq_overrides,
    topology_chain_audit=None,
):
    validation_summary = _topology_validation_summary(preview, edited_payload, topology_operations)
    if validation_summary['errors']:
        return None, validation_summary

    edit_payload = {
        'sld_payload': edited_payload,
        'topology_operations': topology_operations,
        preview_key: preview,
        'downstream_summaries': {
            'boq': boq_overrides,
            'result': {'branch_count': _graph_component_count(edited_payload, ['MCB'])},
        },
        'cable_schedule_rows': _edited_cable_schedule_rows(edited_payload),
    }
    if topology_chain_audit:
        edit_payload['topology_chain_audit'] = topology_chain_audit
        compaction = topology_chain_audit.get('compaction') or {}
        if compaction:
            edit_payload['topology_chain_compacted'] = True
            edit_payload['topology_chain_compaction'] = compaction
    return edit_payload, validation_summary


RUNTIME_TOPOLOGY_META_KEYS = {
    'has_topology_edit',
    'topology_edit_id',
    'topology_edit_type',
    'topology_edit_status',
    'topology_baseline_changed',
    'topology_edit_review_required',
    'topology_edit_replayed_on_current_baseline',
    'manual_topology_warning',
}


def _fresh_edit_payload_meta(payload):
    meta = dict((payload or {}).get('meta') or {})
    for key in RUNTIME_TOPOLOGY_META_KEYS:
        meta.pop(key, None)
    return meta


def _node_length_m(node):
    try:
        return float((node.get('metadata') or {}).get('length_m') or 0)
    except (TypeError, ValueError):
        return 0


def _format_mm2(value):
    if value in (None, ''):
        return ''
    value = float(value)
    return f'{value:g}'


def _format_cold_cable_size(size_mm2):
    if size_mm2 in (None, ''):
        return ''
    return f'3C x {_format_mm2(size_mm2)} mm2'


def _selected_feeder_entry_nodes(payload, selected_nodes):
    node_by_id = _node_lookup(payload)
    _incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    selected_ids = {node['component_id'] for node in selected_nodes}
    entries = []
    seen = set()
    for selected_node in selected_nodes:
        for edge in outgoing_by_id.get(selected_node['component_id'], []):
            entry_id = edge.get('to_component_id')
            if not entry_id or entry_id in selected_ids or entry_id in seen:
                continue
            entry_node = node_by_id.get(entry_id)
            if not entry_node:
                continue
            entries.append(entry_node)
            seen.add(entry_id)
    return entries


def _default_combined_trunk_length(payload, selected_nodes):
    entry_lengths = [
        _node_length_m(node)
        for node in _selected_feeder_entry_nodes(payload, selected_nodes)
        if _node_length_m(node) > 0
    ]
    return max(entry_lengths) if entry_lengths else None


def _trunk_length_basis(trunk_length_input, default_length_basis):
    return 'user_input' if trunk_length_input not in (None, '') else default_length_basis


def _cable_role(node):
    return (node.get('metadata') or {}).get('cable_role') or ''


def _edited_cable_lengths(mcb, cable_nodes, outgoing_by_id):
    direct_cable_ids = {
        edge.get('to_component_id')
        for edge in outgoing_by_id.get(mcb['component_id'], [])
    }
    mcb_trunks = [
        node for node in cable_nodes
        if node.get('component_id') in direct_cable_ids or _cable_role(node) == 'MCB_TO_JB3PH'
    ]
    jb_trunks = [
        node for node in cable_nodes
        if _cable_role(node) == 'JB3PH_TO_JB3PH'
    ]
    trunk_ids = {
        node.get('component_id')
        for node in [*mcb_trunks, *jb_trunks]
    }
    branch_cables = [
        node for node in cable_nodes
        if node.get('component_id') not in trunk_ids
    ]
    return {
        'db_to_jb': sum(_node_length_m(node) for node in mcb_trunks),
        'jb_to_jb': sum(_node_length_m(node) for node in jb_trunks),
        'branch_total': sum(_node_length_m(node) for node in branch_cables),
        'roles': {
            'mcb_trunks': [node.get('display_tag') for node in mcb_trunks],
            'jb_trunks': [node.get('display_tag') for node in jb_trunks],
            'branch_cables': [node.get('display_tag') for node in branch_cables],
        },
    }


def _edited_cable_schedule_rows(payload):
    node_by_id = _node_lookup(payload)
    _incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    rows = []
    for branch_index, mcb in enumerate(
        sorted(
            (node for node in payload.get('nodes', []) if node.get('component_type') == 'MCB'),
            key=_mcb_selection_sort_key,
        ),
        start=1,
    ):
        visited = set()
        stack = [mcb['component_id']]
        downstream_nodes = []
        while stack:
            component_id = stack.pop()
            for edge in outgoing_by_id.get(component_id, []):
                target_id = edge.get('to_component_id')
                if not target_id or target_id in visited:
                    continue
                visited.add(target_id)
                target = node_by_id.get(target_id)
                if not target:
                    continue
                downstream_nodes.append(target)
                stack.append(target_id)

        line_ids = sorted({
            line_id
            for node in [mcb, *downstream_nodes]
            for line_id in (node.get('line_ids') or ([node.get('line_id')] if node.get('line_id') else []))
            if line_id
        })
        cable_nodes = [node for node in downstream_nodes if node.get('component_type') in {'Cable4C', 'Cable3C'}]
        tracer_nodes = [node for node in downstream_nodes if node.get('component_type') == 'Tracer']
        cable_lengths = _edited_cable_lengths(mcb, cable_nodes, outgoing_by_id)
        rows.append({
            'distribution': {'line': {'line_id': ', '.join(line_ids) or mcb.get('line_id') or ''}},
            'branch_index': branch_index,
            'branch_type': 'manual_topology_edit',
            'connected_to': ', '.join(node.get('display_tag', '') for node in tracer_nodes) or 'Manual topology path',
            'circuit_count': max(1, len(tracer_nodes)),
            'cable_length_db_to_jb': cable_lengths['db_to_jb'],
            'cable_length_jb_to_jb': cable_lengths['jb_to_jb'] or None,
            'branch_cable_length_total_m': cable_lengths['branch_total'],
            'tagged_components': {
                'MCB': mcb.get('display_tag'),
                'Cables': [node.get('display_tag') for node in cable_nodes],
                'CableRoles': cable_lengths['roles'],
                'Downstream': [{'Tracer': node.get('display_tag')} for node in tracer_nodes],
            },
        })
    return rows


def _manual_display_name(component_type):
    return {
        'Cable4C': '4C Cable',
        'Isolator3PH': '3PH Isolator',
        'JB3PH': '3PH JB',
    }.get(component_type, component_type)


def _manual_distribution_edges(source_component_id, cable4c, isolator3ph, jb3ph):
    chain = [cable4c]
    if isolator3ph:
        chain.append(isolator3ph)
    chain.append(jb3ph)
    edges = []
    previous_id = source_component_id
    for node in chain:
        edges.append({
            'from_component_id': previous_id,
            'to_component_id': node['component_id'],
            'line_ids': node.get('line_ids', []),
            'line_uid': node.get('line_uid'),
            'branch_index': node.get('branch_index'),
            'circuit_index': None,
        })
        previous_id = node['component_id']
    return edges


def _single_edge(edges, component_id, node_by_id):
    valid_edges = [
        edge for edge in edges.get(component_id, [])
        if edge.get('from_component_id') in node_by_id or edge.get('to_component_id') in node_by_id
    ]
    return valid_edges[0] if len(valid_edges) == 1 else None


def _can_collapse_3ph_jb_to_target(target_node):
    return (target_node or {}).get('component_type') in {'Cable3C', 'Isolator1PH'}


def _collapse_single_outgoing_3ph_jbs(payload):
    """Remove redundant 3PH distribution islands that now feed one branch."""
    simplified = deepcopy(payload)
    collapsed_count = 0

    while True:
        node_by_id = _node_lookup(simplified)
        incoming_by_id, outgoing_by_id = _edge_lookup(simplified)
        collapse = None

        for jb in simplified.get('nodes', []):
            if jb.get('component_type') != 'JB3PH':
                continue
            incoming_edge = _single_edge(incoming_by_id, jb['component_id'], node_by_id)
            outgoing_edge = _single_edge(outgoing_by_id, jb['component_id'], node_by_id)
            if not incoming_edge or not outgoing_edge:
                continue

            remove_ids = {jb['component_id']}
            upstream_source_id = incoming_edge.get('from_component_id')
            cursor_id = upstream_source_id
            current_child_id = jb['component_id']

            while cursor_id in node_by_id and node_by_id[cursor_id].get('component_type') in {'Isolator3PH', 'Cable4C'}:
                cursor_incoming = _single_edge(incoming_by_id, cursor_id, node_by_id)
                cursor_outgoing = _single_edge(outgoing_by_id, cursor_id, node_by_id)
                if not cursor_incoming or not cursor_outgoing:
                    break
                if cursor_outgoing.get('to_component_id') != current_child_id:
                    break
                remove_ids.add(cursor_id)
                current_child_id = cursor_id
                upstream_source_id = cursor_incoming.get('from_component_id')
                cursor_id = upstream_source_id

            target_id = outgoing_edge.get('to_component_id')
            if not upstream_source_id or upstream_source_id == target_id or target_id not in node_by_id:
                continue

            target_node = node_by_id[target_id]
            if not _can_collapse_3ph_jb_to_target(target_node):
                continue
            collapse = {
                'remove_ids': remove_ids,
                'bypass_edge': {
                    'from_component_id': upstream_source_id,
                    'to_component_id': target_id,
                    'line_ids': target_node.get('line_ids', []),
                    'line_uid': target_node.get('line_uid'),
                    'branch_index': target_node.get('branch_index'),
                    'circuit_index': target_node.get('circuit_index'),
                },
            }
            break

        if not collapse:
            break

        remove_ids = collapse['remove_ids']
        simplified['nodes'] = [
            node for node in simplified.get('nodes', [])
            if node.get('component_id') not in remove_ids
        ]
        simplified['edges'] = _dedupe_edges([
            *[
                dict(edge) for edge in simplified.get('edges', [])
                if edge.get('from_component_id') not in remove_ids
                and edge.get('to_component_id') not in remove_ids
            ],
            collapse['bypass_edge'],
        ])
        collapsed_count += 1

    if collapsed_count:
        meta = dict(simplified.get('meta') or {})
        meta['single_outgoing_3ph_jb_collapsed_count'] = collapsed_count
        simplified['meta'] = meta
    return simplified


def _node_line_identity(node):
    metadata = node.get('metadata') or {}
    line_uids = {
        value
        for value in [node.get('line_uid'), metadata.get('original_line_uid')]
        if value
    }
    line_ids = {
        value
        for value in [node.get('line_id'), metadata.get('original_line_id'), *(node.get('line_ids') or [])]
        if value
    }
    return line_uids, line_ids


def _node_matches_line_scope(node, line_uids, line_ids):
    node_line_uids, node_line_ids = _node_line_identity(node)
    return bool(node_line_uids & line_uids or node_line_ids & line_ids)


def _group_matches_line_scope(group, line_uids, line_ids):
    group_uids = {
        value
        for value in [group.get('line_uid'), group.get('original_line_uid')]
        if value
    }
    group_ids = {
        value
        for value in [group.get('line_id'), group.get('original_line_id')]
        if value
    }
    return bool(group_uids & line_uids or group_ids & line_ids)


def _selected_reset_scope(payload, component_id):
    node_by_id = _node_lookup(payload)
    selected = node_by_id.get(component_id)
    if not selected:
        return None, 'Select a component in the feeder tree to reset.'
    source_mcb = selected if selected.get('component_type') == 'MCB' else _upstream_mcb_node(payload, component_id)
    if not source_mcb:
        return None, 'Selected component does not have a clear upstream MCB source.'
    tree_ids = _descendant_component_ids(payload, source_mcb['component_id']) | {source_mcb['component_id']}
    scope_nodes = [node_by_id[node_id] for node_id in tree_ids if node_id in node_by_id]
    line_uids = set()
    line_ids = set()
    for node in scope_nodes:
        node_uids, node_ids = _node_line_identity(node)
        line_uids.update(node_uids)
        line_ids.update(node_ids)
    if not line_uids and not line_ids:
        return None, 'Selected feeder tree does not carry enough line identity to reset safely.'
    return {
        'source_mcb': source_mcb,
        'tree_component_ids': tree_ids,
        'line_uids': line_uids,
        'line_ids': line_ids,
    }, ''


def _build_scoped_reset_payload(active_payload, generated_payload, reset_scope):
    line_uids = reset_scope['line_uids']
    line_ids = reset_scope['line_ids']
    remove_ids = {
        node['component_id']
        for node in active_payload.get('nodes', [])
        if node['component_id'] in reset_scope['tree_component_ids']
        or _node_matches_line_scope(node, line_uids, line_ids)
    }
    generated_nodes = [
        deepcopy(node)
        for node in generated_payload.get('nodes', [])
        if _node_matches_line_scope(node, line_uids, line_ids)
    ]
    generated_node_ids = {node['component_id'] for node in generated_nodes}
    if not generated_nodes:
        return None

    nodes = [
        deepcopy(node)
        for node in active_payload.get('nodes', [])
        if node['component_id'] not in remove_ids
    ]
    existing_ids = {node['component_id'] for node in nodes}
    nodes.extend(node for node in generated_nodes if node['component_id'] not in existing_ids)

    kept_edges = [
        deepcopy(edge)
        for edge in active_payload.get('edges', [])
        if edge.get('from_component_id') not in remove_ids
        and edge.get('to_component_id') not in remove_ids
    ]
    generated_edges = [
        deepcopy(edge)
        for edge in generated_payload.get('edges', [])
        if edge.get('from_component_id') in generated_node_ids
        and edge.get('to_component_id') in generated_node_ids
    ]

    line_groups = [
        deepcopy(group)
        for group in active_payload.get('line_groups', [])
        if not _group_matches_line_scope(group, line_uids, line_ids)
    ]
    line_groups.extend(
        deepcopy(group)
        for group in generated_payload.get('line_groups', [])
        if _group_matches_line_scope(group, line_uids, line_ids)
    )

    edited = deepcopy(active_payload)
    edited['nodes'] = nodes
    edited['edges'] = _dedupe_edges([*kept_edges, *generated_edges])
    edited['line_groups'] = line_groups
    meta = _fresh_edit_payload_meta(edited)
    meta.update({
        'node_count': len(edited['nodes']),
        'edge_count': len(edited['edges']),
        'branch_count': sum(len(group.get('branch_indices') or []) for group in line_groups),
        'scoped_reset_line_ids': sorted(line_ids),
        'manual_topology_warning': (
            'Selected feeder tree reset to generated topology. Other manual topology edits remain active.'
        ),
    })
    edited['meta'] = meta
    return edited


def _manual_combine_node(
    source_mcb,
    component_type,
    display_tag,
    selected_nodes,
    recommended_rating,
    trunk_length_m=None,
    cable_size='4C',
    current_lookup=None,
):
    component_id = f"{source_mcb['component_id']}:manual_combine:{component_type}"
    line_ids = sorted({
        line_id
        for node in selected_nodes
        for line_id in (node.get('line_ids') or ([node.get('line_id')] if node.get('line_id') else []))
        if line_id
    })
    metadata = {
        'manual_topology_edit': 'combine_feeders',
        'combined_feeder_count': len(selected_nodes),
    }
    combined_current, rating_basis = _combined_feeder_current(selected_nodes, current_lookup)
    if component_type == 'Cable4C':
        metadata.update({
            'cable_role': 'MCB_TO_JB3PH',
            'length_m': trunk_length_m,
            'generated_length_m': trunk_length_m,
            'cable_size': _manual_trunk_size(cable_size),
            'generated_cable_size': _manual_trunk_size(cable_size),
            'note': 'Manual feeder-combine trunk cable. Cable sizing is pending detailed cable design.',
        })
    if component_type == 'Isolator3PH':
        metadata.update({
            'location': 'incoming',
            'source_mcb': source_mcb.get('display_tag'),
        })
    if component_type == 'JB3PH':
        metadata.update({
            'circuit_count': len(selected_nodes),
            'source_mcb': source_mcb.get('display_tag'),
            'combined_feeder_current': combined_current,
            'breaker_rating_basis': rating_basis,
            'recommended_breaker_rating': recommended_rating,
        })

    return {
        'component_id': component_id,
        'component_uid': _component_uid(component_id),
        'display_tag': display_tag,
        'component_type': component_type,
        'display_name': _manual_display_name(component_type),
        'label': display_tag,
        'line_id': source_mcb.get('line_id'),
        'line_ids': line_ids,
        'line_uid': source_mcb.get('line_uid'),
        'branch_index': source_mcb.get('branch_index'),
        'circuit_index': None,
        'metadata': metadata,
    }


def _manual_display_tag(display_tag):
    return display_tag if str(display_tag).endswith('-M') else f"{display_tag}-M"


def _display_tag_suffix(display_tag):
    return str(display_tag or 'MANUAL').split('_', 1)[1] if '_' in str(display_tag or '') else str(display_tag or 'MANUAL')


def _manual_combine_distribution(payload, source_mcb):
    node_by_id = _node_lookup(payload)
    _incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    for edge in outgoing_by_id.get(source_mcb['component_id'], []):
        cable = node_by_id.get(edge.get('to_component_id'))
        if not cable or cable.get('component_type') != 'Cable4C':
            continue
        if (cable.get('metadata') or {}).get('manual_topology_edit') != 'combine_feeders':
            continue
        for cable_edge in outgoing_by_id.get(cable['component_id'], []):
            next_node = node_by_id.get(cable_edge.get('to_component_id'))
            isolator = None
            jb = next_node
            if next_node and next_node.get('component_type') == 'Isolator3PH':
                isolator = next_node
                next_edges = outgoing_by_id.get(next_node['component_id'], [])
                jb = node_by_id.get(next_edges[0].get('to_component_id')) if len(next_edges) == 1 else None
            if (
                jb
                and jb.get('component_type') == 'JB3PH'
                and (jb.get('metadata') or {}).get('manual_topology_edit') == 'combine_feeders'
            ):
                return cable, isolator, jb
    return None, None, None


def _manual_combine_branch_segments(payload, combine_jb):
    node_by_id = _node_lookup(payload)
    _incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    segments = []
    for index, edge in enumerate(outgoing_by_id.get(combine_jb['component_id'], []), start=1):
        node = node_by_id.get(edge.get('to_component_id'))
        if not node:
            continue
        segments.append(ColdCable3CSegmentLength(
            component_id=node.get('component_id') or '',
            display_tag=node.get('display_tag') or '',
            circuit_index=node.get('circuit_index') or index,
            length_m=_node_length_m(node) or None,
            length_basis='topology_edit',
        ))
    return segments


def _snapshot_cold_cable_metadata(snapshot, *, length_m, force_review=True):
    calculated_size = _format_cold_cable_size(snapshot.get('cable_4c_size_mm2'))
    sizing_status = snapshot.get('sizing_status') or 'unsizeable'
    review_notes = list(snapshot.get('review_notes') or [])
    if force_review and sizing_status == 'selected':
        sizing_status = 'review_required'
        review_notes.append('Manual combined-feeder topology edit requires route and schedule review before issue.')
    return {
        'calculated_size': calculated_size,
        'conductor_size_mm2': snapshot.get('cable_4c_size_mm2'),
        'sizing_status': sizing_status,
        'sizing_engine_status': snapshot.get('sizing_status'),
        'vd_status': snapshot.get('vd_status'),
        'fault_status': snapshot.get('fault_loop_status'),
        'length_basis': snapshot.get('length_basis'),
        'length_m': length_m,
        'derated_ampacity_a': snapshot.get('cable_4c_ampacity_derated_a'),
        'ampacity_margin_pct': snapshot.get('cable_4c_ampacity_margin_pct'),
        'conductor_temp_c': snapshot.get('cable_4c_conductor_temp_c'),
        'conductor_mass_mt': snapshot.get('cable_4c_conductor_mass_mt'),
        'vd_pct': snapshot.get('cable_4c_vd_pct'),
        'vd_total_pct': snapshot.get('vd_total_pct'),
        'vd_allowable_pct': snapshot.get('vd_allowable_pct'),
        'startup_vd_total_pct': snapshot.get('startup_vd_total_pct'),
        'startup_vd_threshold_pct': snapshot.get('startup_vd_threshold_pct'),
        'startup_vd_status': snapshot.get('startup_vd_status'),
        'per_circuit_starting_current_a': snapshot.get('per_circuit_starting_current_a'),
        'load_end_voltage_v': snapshot.get('load_end_voltage_v'),
        'fault_current_a': snapshot.get('fault_current_l_pe_a'),
        'k_temp': snapshot.get('k_temp'),
        'k_group': snapshot.get('k_group'),
        'k_total': snapshot.get('k_total'),
        'review_notes': review_notes,
    }


def _previous_feeder_mass_mt(selected_entries):
    values = [
        ((node.get('metadata') or {}).get('cold_cable') or {}).get('conductor_mass_mt')
        for node in selected_entries
    ]
    values = [float(value) for value in values if value not in (None, '')]
    return sum(values) if values else None


def _combined_feeder_cold_cable_impact(project, source_payload, edited_payload, selected_nodes, preview):
    primary = selected_nodes[0]
    cable4c, _isolator3ph, combine_jb = _manual_combine_distribution(edited_payload, primary)
    if not cable4c or not combine_jb:
        return {
            'status': 'not_calculated',
            'review_notes': ['Combined feeder trunk could not be resolved in the edited SLD payload.'],
        }

    operating_lookup = _project_line_operating_current_lookup(project.proj_id)
    operating_total, operating_per_branch, operating_basis, operating_currents = _combined_feeder_operating_current(
        selected_nodes,
        operating_lookup,
    )
    segments = _manual_combine_branch_segments(edited_payload, combine_jb)
    selected_entries = _selected_feeder_entry_nodes(source_payload, selected_nodes)
    previous_lengths = [_node_length_m(node) for node in selected_entries if _node_length_m(node) > 0]
    review_notes = [
        'Manual combined-feeder topology edit recalculates the new feeder trunk from combined operating current.',
        'Prior separate feeder cable lengths may no longer represent the final combined route; review affected SLD, BOQ, and cable schedule rows before issue.',
    ]
    if operating_basis != 'operating_current':
        review_notes.append('Operating current could not be resolved for every selected feeder; breaker rating fallback was used for cold-cable impact sizing.')
    sizing_input = ColdCableSizingInput(
        project_id=project.proj_id,
        line_id=', '.join(preview.get('affected_lines') or []),
        line_uid=primary.get('line_uid') or primary.get('component_uid') or primary.get('component_id'),
        branch_index=primary.get('branch_index') or 1,
        branch_type='3phJB',
        circuit_count=max(1, len(segments) or len(selected_nodes)),
        heating_cable_type='SR',
        per_circuit_operating_current_a=operating_per_branch or 0.0,
        per_circuit_starting_current_a=operating_per_branch or 0.0,
        line_operating_current_a=operating_total or 0.0,
        breaker_size_a=preview.get('recommended_breaker_rating') or 0.0,
        length_4c_m=preview.get('trunk_length_m'),
        length_3c_m=max((segment.length_m or 0 for segment in segments), default=0) or None,
        length_basis='topology_edit',
        length_missing=not preview.get('trunk_length_m') or any(not segment.length_m for segment in segments),
        length_3c_segments=segments,
        review_notes=review_notes,
    )
    snapshot = build_cold_cable_sizing_snapshot(project, sizing_input)
    cold_metadata = _snapshot_cold_cable_metadata(snapshot, length_m=preview.get('trunk_length_m'))

    metadata = dict(cable4c.get('metadata') or {})
    metadata['cold_cable'] = cold_metadata
    metadata['cold_cable_calculated_size'] = cold_metadata['calculated_size']
    metadata['cold_cable_status'] = cold_metadata['sizing_status']
    metadata['cold_cable_vd_status'] = cold_metadata['vd_status']
    metadata['cold_cable_fault_status'] = cold_metadata['fault_status']
    metadata['cold_cable_impact_role'] = 'combined_feeder_trunk'
    cable4c['metadata'] = metadata

    previous_mass = _previous_feeder_mass_mt(selected_entries)
    new_mass = snapshot.get('cable_4c_conductor_mass_mt')
    mass_delta = None
    if previous_mass is not None and new_mass is not None:
        mass_delta = float(new_mass) - previous_mass

    return {
        'status': cold_metadata['sizing_status'],
        'sizing_engine_status': snapshot.get('sizing_status'),
        'calculated_feeder_size': cold_metadata['calculated_size'],
        'manual_input_cable_size': metadata.get('cable_size'),
        'feeder_length_m': preview.get('trunk_length_m'),
        'feeder_length_basis': preview.get('trunk_length_basis'),
        'previous_feeder_lengths_m': previous_lengths,
        'previous_feeder_length_max_m': max(previous_lengths) if previous_lengths else None,
        'previous_feeder_length_total_m': sum(previous_lengths) if previous_lengths else None,
        'length_delta_vs_previous_total_m': (
            float(preview.get('trunk_length_m')) - sum(previous_lengths)
            if previous_lengths and preview.get('trunk_length_m') is not None else None
        ),
        'combined_operating_current_a': operating_total,
        'max_selected_operating_current_a': operating_per_branch,
        'operating_current_basis': operating_basis,
        'selected_operating_currents_a': operating_currents,
        'recommended_breaker_rating': preview.get('recommended_breaker_rating'),
        'input_breaker_ratings': preview.get('input_breaker_ratings') or [],
        'downstream_segment_count': len(segments),
        'downstream_segments': [
            {
                'component_id': segment.component_id,
                'display_tag': segment.display_tag,
                'length_m': segment.length_m,
                'length_basis': segment.length_basis,
            }
            for segment in segments
        ],
        'vd_total_pct': snapshot.get('vd_total_pct'),
        'vd_allowable_pct': snapshot.get('vd_allowable_pct'),
        'fault_loop_status': snapshot.get('fault_loop_status'),
        'fault_current_l_pe_a': snapshot.get('fault_current_l_pe_a'),
        'new_feeder_conductor_mass_mt': new_mass,
        'previous_feeder_conductor_mass_mt': previous_mass,
        'feeder_conductor_mass_delta_mt': mass_delta,
        'affected_lines': preview.get('affected_lines') or [],
        'affected_branch_count': preview.get('affected_branch_count'),
        'affected_schedule_rows': _edited_cable_schedule_rows(edited_payload),
        'review_notes': cold_metadata['review_notes'],
    }


def _apply_combined_feeder_cold_cable_impact(project, source_payload, edited_payload, selected_nodes, preview):
    impact = _combined_feeder_cold_cable_impact(project, source_payload, edited_payload, selected_nodes, preview)
    meta = dict(edited_payload.get('meta') or {})
    meta['combined_feeder_cold_cable_status'] = impact.get('status')
    meta['combined_feeder_cold_cable_size'] = impact.get('calculated_feeder_size') or ''
    meta['combined_feeder_cold_cable_review_required'] = impact.get('status') == 'review_required'
    edited_payload['meta'] = meta
    return impact


def _build_edited_payload(
    payload,
    selected_nodes,
    recommended_rating,
    isolator_location='noIsolator',
    trunk_length_m=None,
    cable_size='4C',
    current_lookup=None,
):
    primary = selected_nodes[0]
    secondary_ids = {node['component_id'] for node in selected_nodes[1:]}
    selected_ids = {node['component_id'] for node in selected_nodes}
    primary_id = primary['component_id']
    edited = deepcopy(payload)
    _, outgoing_by_id = _edge_lookup(edited)
    existing_cable4c, existing_isolator3ph, existing_jb3ph = _manual_combine_distribution(edited, primary)
    combined_line_ids = _node_line_ids(selected_nodes)
    operating_lookup = _project_line_operating_current_lookup(payload.get('project_id'))
    combined_operating_current, _max_operating_current, operating_basis, _operating_currents = _combined_feeder_operating_current(
        selected_nodes,
        operating_lookup,
    )

    for node in edited['nodes']:
        if node['component_id'] != primary_id:
            continue
        metadata = dict(node.get('metadata') or {})
        combined_current, rating_basis = _combined_feeder_current(selected_nodes, current_lookup)
        metadata.update({
            'breaker_size': recommended_rating,
            'starting_current': combined_current,
            'combined_feeder_current': combined_current,
            'combined_feeder_operating_current': combined_operating_current,
            'breaker_rating_basis': rating_basis,
            'cold_cable_current_basis': operating_basis,
            'manual_topology_edit': 'combine_feeders',
            'combined_feeder_count': len(selected_nodes),
        })
        node['metadata'] = metadata
        node['line_ids'] = combined_line_ids
        node['display_tag'] = _manual_display_tag(node.get('display_tag', 'MCB'))
        node['label'] = node['display_tag']

    feeder_entry_ids = []
    for selected_node in selected_nodes:
        if existing_jb3ph and selected_node['component_id'] == primary_id:
            continue
        for edge in outgoing_by_id.get(selected_node['component_id'], []):
            entry_id = edge.get('to_component_id')
            if entry_id and entry_id not in selected_ids:
                feeder_entry_ids.append(entry_id)
    feeder_entry_ids = sorted(set(feeder_entry_ids))

    primary_tag = _manual_display_tag(primary.get('display_tag', 'MCB'))
    tag_suffix = primary_tag.split('_', 1)[1] if '_' in primary_tag else primary_tag
    cable4c = existing_cable4c or _manual_combine_node(
        primary,
        'Cable4C',
        f"CCAB4C_{tag_suffix}-M",
        selected_nodes,
        recommended_rating,
        trunk_length_m=trunk_length_m,
        cable_size=cable_size,
        current_lookup=current_lookup,
    )
    if existing_cable4c:
        metadata = dict(cable4c.get('metadata') or {})
        metadata.update({
            'length_m': trunk_length_m,
            'generated_length_m': trunk_length_m,
            'cable_size': _manual_trunk_size(cable_size),
            'generated_cable_size': _manual_trunk_size(cable_size),
        })
        cable4c['metadata'] = metadata
    isolator3ph = existing_isolator3ph
    if _requires_incoming_isolator(isolator_location) and not isolator3ph:
        isolator3ph = _manual_combine_node(
            primary,
            'Isolator3PH',
            f"ISOL_3PH_{tag_suffix}-M",
            selected_nodes,
            recommended_rating,
            trunk_length_m=trunk_length_m,
            cable_size=cable_size,
            current_lookup=current_lookup,
        )
    jb3ph = existing_jb3ph or _manual_combine_node(
        primary,
        'JB3PH',
        f"JB3PH_{tag_suffix}-M",
        selected_nodes,
        recommended_rating,
        trunk_length_m=trunk_length_m,
        cable_size=cable_size,
        current_lookup=current_lookup,
    )

    edited['nodes'] = [
        node for node in edited['nodes']
        if node['component_id'] not in secondary_ids
    ]
    existing_manual_ids = {node['component_id'] for node in edited['nodes']}
    if cable4c['component_id'] not in existing_manual_ids:
        edited['nodes'].append(cable4c)
        existing_manual_ids.add(cable4c['component_id'])
    if isolator3ph and isolator3ph['component_id'] not in existing_manual_ids:
        edited['nodes'].append(isolator3ph)
        existing_manual_ids.add(isolator3ph['component_id'])
    if jb3ph['component_id'] not in existing_manual_ids:
        edited['nodes'].append(jb3ph)

    rewired_edges = []
    for edge in edited['edges']:
        if edge.get('to_component_id') in secondary_ids:
            continue
        if edge.get('from_component_id') in selected_ids and not (
            existing_jb3ph and edge.get('from_component_id') == primary_id
        ):
            continue
        if (
            isolator3ph
            and existing_jb3ph
            and not existing_isolator3ph
            and edge.get('from_component_id') == cable4c['component_id']
            and edge.get('to_component_id') == jb3ph['component_id']
        ):
            continue
        rewired_edges.append(dict(edge))

    if not existing_jb3ph or (isolator3ph and not existing_isolator3ph):
        rewired_edges.extend(_manual_distribution_edges(primary_id, cable4c, isolator3ph, jb3ph))
    node_by_id = _node_lookup(edited)
    for entry_id in feeder_entry_ids:
        entry_node = node_by_id.get(entry_id)
        if not entry_node:
            continue
        rewired_edges.append({
            'from_component_id': jb3ph['component_id'],
            'to_component_id': entry_id,
            'line_ids': entry_node.get('line_ids', []),
            'line_uid': entry_node.get('line_uid'),
            'branch_index': entry_node.get('branch_index'),
            'circuit_index': entry_node.get('circuit_index'),
        })
    edited['edges'] = _dedupe_edges(rewired_edges)

    meta = _fresh_edit_payload_meta(edited)
    meta.update({
        'node_count': len(edited['nodes']),
        'edge_count': len(edited['edges']),
        'combine_feeder_count': len(selected_nodes),
        'manual_topology_warning': (
            'Manual feeder combine applied with a Feeder Cable and Distribution JB before the original outgoing feeder cables. Review the recalculated cold-cable sizing before issue.'
        ),
    })
    edited['meta'] = meta
    return edited


def _node_workflow_sort_key(node):
    return (
        str(node.get('line_id') or ''),
        str(node.get('line_uid') or ''),
        node.get('branch_index') or 0,
        node.get('circuit_index') or 0,
        str(node.get('component_id') or ''),
    )


def _selected_split_mcb(payload, component_ids):
    selected, invalid_ids = _selected_mcb_nodes(payload, component_ids)
    return selected[0] if len(selected) == 1 and not invalid_ids else None, invalid_ids


def _split_source_details(payload, source_mcb):
    # Split acts at the selected MCB. Walk the single shared feeder chain until
    # it fans out; those shared nodes are removed and the fan-out entries become
    # independent MCB-fed circuit starts.
    node_by_id = _node_lookup(payload)
    _incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    cursor = source_mcb['component_id']
    shared_component_ids = []
    visited = {cursor}

    while True:
        outgoing_edges = [
            edge for edge in outgoing_by_id.get(cursor, [])
            if edge.get('to_component_id') in node_by_id
        ]
        if len(outgoing_edges) >= 2:
            entry_nodes = sorted(
                [node_by_id[edge['to_component_id']] for edge in outgoing_edges],
                key=_node_workflow_sort_key,
            )
            return {
                'shared_component_ids': shared_component_ids,
                'entry_nodes': entry_nodes,
            }
        if len(outgoing_edges) != 1:
            return None

        next_id = outgoing_edges[0].get('to_component_id')
        next_node = node_by_id.get(next_id)
        if not next_node or next_id in visited or next_node.get('component_type') == 'MCB':
            return None
        visited.add(next_id)
        shared_component_ids.append(next_id)
        cursor = next_id


def _split_mcb_display_tag(source_mcb, index):
    return f"{source_mcb.get('display_tag', 'MCB')}-S{index}"


def _new_split_mcb_node(source_mcb, entry_node, index, recommended_rating, circuit_count):
    component_id = (
        f"{source_mcb['component_id']}:manual_split:"
        f"{entry_node.get('line_uid')}:{entry_node.get('branch_index')}:{entry_node.get('circuit_index')}"
    )
    display_tag = _split_mcb_display_tag(source_mcb, index)
    return {
        'component_id': component_id,
        'component_uid': _component_uid(component_id),
        'display_tag': display_tag,
        'component_type': 'MCB',
        'display_name': 'MCB',
        'label': display_tag,
        'line_id': entry_node.get('line_id'),
        'line_ids': entry_node.get('line_ids') or ([entry_node.get('line_id')] if entry_node.get('line_id') else []),
        'line_uid': entry_node.get('line_uid'),
        'branch_index': entry_node.get('branch_index'),
        'circuit_index': None,
        'metadata': {
            'breaker_size': recommended_rating,
            'manual_topology_edit': 'split_circuits',
            'source_mcb': source_mcb.get('display_tag'),
            'split_circuit_count': circuit_count,
            'split_circuit_index': entry_node.get('circuit_index'),
        },
    }


def _split_part_identity(entry_node, suffix_index=None):
    original_line_id = entry_node.get('line_id') or 'LINE'
    original_line_uid = entry_node.get('line_uid') or original_line_id
    line_id = f"{original_line_id}-part{suffix_index}" if suffix_index else original_line_id
    line_uid = f"{original_line_uid}:manual_split:part{suffix_index}" if suffix_index else original_line_uid
    return {
        'line_id': line_id,
        'line_uid': line_uid,
        'original_line_id': original_line_id,
        'original_line_uid': original_line_uid,
    }


def _split_circuit_key(node):
    return (
        node.get('line_uid'),
        node.get('branch_index'),
        node.get('circuit_index'),
    )


def _apply_split_part_identity(item, part_identity):
    item['line_id'] = part_identity['line_id']
    item['line_ids'] = [part_identity['line_id']]
    item['line_uid'] = part_identity['line_uid']
    metadata = dict(item.get('metadata') or {})
    metadata.update({
        'original_line_id': part_identity['original_line_id'],
        'original_line_uid': part_identity['original_line_uid'],
    })
    item['metadata'] = metadata


def _build_split_payload(payload, source_mcb, split_details, recommended_rating):
    edited = deepcopy(payload)
    source_id = source_mcb['component_id']
    removed_ids = set(split_details['shared_component_ids'])
    entry_nodes = split_details['entry_nodes']
    entry_ids = {node['component_id'] for node in entry_nodes}
    split_scope_ids = _descendant_component_ids(payload, source_id) | {source_id}
    entry_counts_by_uid = {}
    entry_index_by_uid = {}
    for entry in entry_nodes:
        line_uid = entry.get('line_uid') or entry.get('line_id') or entry.get('component_id')
        entry_counts_by_uid[line_uid] = entry_counts_by_uid.get(line_uid, 0) + 1
    outside_line_uids = {
        node.get('line_uid')
        for node in payload.get('nodes', [])
        if node.get('line_uid') and node.get('component_id') not in split_scope_ids
    }
    part_identity_by_key = {}
    for entry in entry_nodes:
        line_uid = entry.get('line_uid') or entry.get('line_id') or entry.get('component_id')
        needs_part_suffix = entry_counts_by_uid[line_uid] > 1 or line_uid in outside_line_uids
        suffix_index = None
        if needs_part_suffix:
            entry_index_by_uid[line_uid] = entry_index_by_uid.get(line_uid, 0) + 1
            suffix_index = entry_index_by_uid[line_uid]
        part_identity_by_key[_split_circuit_key(entry)] = _split_part_identity(entry, suffix_index)
    split_mcb_by_entry = {
        entry['component_id']: _new_split_mcb_node(
            source_mcb,
            entry,
            index,
            recommended_rating,
            len(entry_nodes),
        )
        for index, entry in enumerate(entry_nodes[1:], start=2)
    }
    for entry in entry_nodes[1:]:
        _apply_split_part_identity(
            split_mcb_by_entry[entry['component_id']],
            part_identity_by_key[_split_circuit_key(entry)],
        )

    nodes = []
    for node in edited['nodes']:
        if node['component_id'] in removed_ids:
            continue
        node = dict(node)
        if node['component_id'] == source_id:
            metadata = dict(node.get('metadata') or {})
            metadata.update({
                'breaker_size': recommended_rating,
                'manual_topology_edit': 'split_circuits',
                'split_circuit_count': len(entry_nodes),
                'split_circuit_index': entry_nodes[0].get('circuit_index'),
            })
            node['metadata'] = metadata
            node['display_tag'] = _split_mcb_display_tag(source_mcb, 1)
            node['label'] = node['display_tag']
            _apply_split_part_identity(node, part_identity_by_key[_split_circuit_key(entry_nodes[0])])
        elif _split_circuit_key(node) in part_identity_by_key:
            _apply_split_part_identity(node, part_identity_by_key[_split_circuit_key(node)])
        nodes.append(node)
    nodes.extend(split_mcb_by_entry.values())
    edited['nodes'] = nodes

    rewired_edges = []
    for edge in edited['edges']:
        if edge.get('from_component_id') == source_id:
            continue
        if edge.get('from_component_id') in removed_ids or edge.get('to_component_id') in removed_ids:
            continue
        if edge.get('to_component_id') in entry_ids:
            continue
        edge = dict(edge)
        edge_key = (
            edge.get('line_uid'),
            edge.get('branch_index'),
            edge.get('circuit_index'),
        )
        if edge_key in part_identity_by_key:
            part_identity = part_identity_by_key[edge_key]
            edge['line_ids'] = [part_identity['line_id']]
            edge['line_uid'] = part_identity['line_uid']
        rewired_edges.append(edge)

    for index, entry_node in enumerate(entry_nodes, start=1):
        part_identity = part_identity_by_key[_split_circuit_key(entry_node)]
        source_component_id = source_id if index == 1 else split_mcb_by_entry[entry_node['component_id']]['component_id']
        rewired_edges.append({
            'from_component_id': source_component_id,
            'to_component_id': entry_node['component_id'],
            'line_ids': [part_identity['line_id']],
            'line_uid': part_identity['line_uid'],
            'branch_index': entry_node.get('branch_index'),
            'circuit_index': entry_node.get('circuit_index'),
        })
    edited['edges'] = _dedupe_edges(rewired_edges)
    split_group_uids = {
        str(identity['original_line_uid'])
        for identity in part_identity_by_key.values()
    }
    remaining_original_branches = {}
    new_split_mcb_ids = {
        node['component_id']
        for node in split_mcb_by_entry.values()
    }
    for node in edited['nodes']:
        if node.get('component_id') in split_scope_ids or node.get('component_id') in new_split_mcb_ids:
            continue
        line_uid = str(node.get('line_uid'))
        if line_uid not in split_group_uids:
            continue
        branch_index = node.get('branch_index')
        if branch_index is not None:
            remaining_original_branches.setdefault(str(line_uid), set()).add(branch_index)
    preserved_groups = []
    for group in edited.get('line_groups', []):
        group_uid = str(group.get('line_uid'))
        if group_uid in split_group_uids:
            remaining_branches = remaining_original_branches.get(group_uid)
            if not remaining_branches:
                continue
            group = {**group, 'branch_indices': sorted(remaining_branches)}
        preserved_groups.append(group)
    edited['line_groups'] = preserved_groups
    for entry in entry_nodes:
        identity = part_identity_by_key[_split_circuit_key(entry)]
        edited['line_groups'].append({
            'line_id': identity['line_id'],
            'line_uid': identity['line_uid'],
            'original_line_id': identity['original_line_id'],
            'original_line_uid': identity['original_line_uid'],
            'branch_indices': [entry.get('branch_index')],
        })

    meta = _fresh_edit_payload_meta(edited)
    meta.update({
        'node_count': len(edited['nodes']),
        'edge_count': len(edited['edges']),
        'branch_count': sum(len(group.get('branch_indices') or []) for group in edited['line_groups']),
        'split_circuit_count': len(entry_nodes),
        'manual_topology_warning': (
            'Manual circuit split applied: the shared multi-circuit feeder distribution was removed and each outgoing circuit now starts from its own MCB. Breaker ratings are recommended for engineering review.'
        ),
    })
    edited['meta'] = meta
    return edited


def _downstream_jb_sort_key(edge, node_by_id):
    node = node_by_id.get(edge.get('to_component_id')) or {}
    return _node_workflow_sort_key(node)


def _downstream_jb_outgoing_edges(payload, parent_jb):
    node_by_id = _node_lookup(payload)
    _incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    return sorted(
        [
            edge for edge in outgoing_by_id.get(parent_jb['component_id'], [])
            if edge.get('to_component_id') in node_by_id
        ],
        key=lambda edge: _downstream_jb_sort_key(edge, node_by_id),
    )


def _selected_downstream_jb_details(payload, parent_component_id, branch_component_ids):
    node_by_id = _node_lookup(payload)
    parent = node_by_id.get(parent_component_id)
    if not parent or parent.get('component_type') != 'JB3PH':
        return None
    outgoing_edges = _downstream_jb_outgoing_edges(payload, parent)
    outgoing_by_target = {
        edge.get('to_component_id'): edge
        for edge in outgoing_edges
    }
    branch_component_ids = [
        component_id for component_id in (branch_component_ids or [])
        if component_id
    ]
    invalid_ids = [
        component_id for component_id in branch_component_ids
        if component_id not in outgoing_by_target
    ]
    selected_edges = [
        outgoing_by_target[component_id]
        for component_id in branch_component_ids
        if component_id in outgoing_by_target
    ]
    selected_edges.sort(key=lambda edge: _downstream_jb_sort_key(edge, node_by_id))
    return {
        'parent': parent,
        'outgoing_edges': outgoing_edges,
        'selected_edges': selected_edges,
        'invalid_ids': invalid_ids,
        'node_by_id': node_by_id,
    }


def _unique_manual_tag(existing_tags, prefix, base_suffix):
    index = 1
    while True:
        tag = f"{prefix}_{base_suffix}-D{index}"
        if tag not in existing_tags:
            return tag
        index += 1


def _downstream_jb_manual_node(parent_jb, component_type, display_tag, selected_nodes, trunk_length_m, cable_size='4C'):
    component_id = f"{parent_jb['component_id']}:manual_downstream_jb:{component_type}:{display_tag}"
    line_ids = sorted({
        line_id
        for node in selected_nodes
        for line_id in (node.get('line_ids') or ([node.get('line_id')] if node.get('line_id') else []))
        if line_id
    })
    metadata = {
        'manual_topology_edit': 'downstream_jb',
        'source_jb': parent_jb.get('display_tag'),
        'moved_outgoing_count': len(selected_nodes),
    }
    if component_type == 'Cable4C':
        metadata.update({
            'cable_role': 'JB3PH_TO_JB3PH',
            'length_m': trunk_length_m,
            'generated_length_m': trunk_length_m,
            'cable_size': _manual_trunk_size(cable_size),
            'generated_cable_size': _manual_trunk_size(cable_size),
            'note': 'Manual downstream 3PH JB trunk cable.',
        })
    if component_type == 'Isolator3PH':
        metadata.update({
            'location': 'incoming',
        })
    if component_type == 'JB3PH':
        metadata.update({
            'circuit_count': len(selected_nodes),
        })
    return {
        'component_id': component_id,
        'component_uid': _component_uid(component_id),
        'display_tag': display_tag,
        'component_type': component_type,
        'display_name': _manual_display_name(component_type),
        'label': display_tag,
        'line_id': parent_jb.get('line_id'),
        'line_ids': line_ids,
        'line_uid': parent_jb.get('line_uid'),
        'branch_index': parent_jb.get('branch_index'),
        'circuit_index': None,
        'metadata': metadata,
    }


def _downstream_jb_preview_tags(payload, parent_jb, isolator_location='noIsolator'):
    existing_tags = {node.get('display_tag') for node in payload.get('nodes', [])}
    base_suffix = _display_tag_suffix(parent_jb.get('display_tag', 'JB3PH'))
    cable_tag = _unique_manual_tag(existing_tags, 'CCAB4C', base_suffix)
    isolator_tag = ''
    if _requires_incoming_isolator(isolator_location):
        isolator_tag = _unique_manual_tag(existing_tags | {cable_tag}, 'ISOL_3PH', base_suffix)
    jb_tag = _unique_manual_tag(existing_tags | {cable_tag, isolator_tag}, 'JB3PH', base_suffix)
    return cable_tag, isolator_tag, jb_tag


def _target_mcb_distribution_preview_tags(payload, target_mcb, isolator_location='noIsolator'):
    existing_tags = {node.get('display_tag') for node in payload.get('nodes', [])}
    base_suffix = _display_tag_suffix(target_mcb.get('display_tag', 'MCB'))
    cable_tag = _unique_manual_tag(existing_tags, 'CCAB4C', base_suffix)
    isolator_tag = ''
    if _requires_incoming_isolator(isolator_location):
        isolator_tag = _unique_manual_tag(existing_tags | {cable_tag}, 'ISOL_3PH', base_suffix)
    jb_tag = _unique_manual_tag(existing_tags | {cable_tag, isolator_tag}, 'JB3PH', base_suffix)
    return cable_tag, isolator_tag, jb_tag


def _build_downstream_jb_payload(payload, details, trunk_length_m, isolator_location='noIsolator', cable_size='4C'):
    edited = deepcopy(payload)
    parent = details['parent']
    selected_edges = details['selected_edges']
    node_by_id = _node_lookup(edited)
    selected_target_ids = {edge.get('to_component_id') for edge in selected_edges}
    selected_nodes = [
        node_by_id[component_id]
        for component_id in selected_target_ids
        if component_id in node_by_id
    ]
    cable_tag, isolator_tag, jb_tag = _downstream_jb_preview_tags(edited, parent, isolator_location)
    cable4c = _downstream_jb_manual_node(parent, 'Cable4C', cable_tag, selected_nodes, trunk_length_m, cable_size=cable_size)
    isolator3ph = (
        _downstream_jb_manual_node(parent, 'Isolator3PH', isolator_tag, selected_nodes, trunk_length_m, cable_size=cable_size)
        if isolator_tag
        else None
    )
    jb3ph = _downstream_jb_manual_node(parent, 'JB3PH', jb_tag, selected_nodes, trunk_length_m, cable_size=cable_size)
    edited['nodes'].extend([node for node in [cable4c, isolator3ph, jb3ph] if node])

    rewired_edges = []
    for edge in edited['edges']:
        if (
            edge.get('from_component_id') == parent['component_id']
            and edge.get('to_component_id') in selected_target_ids
        ):
            continue
        rewired_edges.append(dict(edge))

    rewired_edges.extend(_manual_distribution_edges(parent['component_id'], cable4c, isolator3ph, jb3ph))
    for edge in selected_edges:
        target = node_by_id.get(edge.get('to_component_id'))
        if not target:
            continue
        rewired_edges.append({
            'from_component_id': jb3ph['component_id'],
            'to_component_id': target['component_id'],
            'line_ids': target.get('line_ids', []),
            'line_uid': target.get('line_uid'),
            'branch_index': target.get('branch_index'),
            'circuit_index': target.get('circuit_index'),
        })

    edited['edges'] = _dedupe_edges(rewired_edges)
    edited = _collapse_single_outgoing_3ph_jbs(edited)
    meta = _fresh_edit_payload_meta(edited)
    meta.update({
        'node_count': len(edited['nodes']),
        'edge_count': len(edited['edges']),
        'manual_topology_warning': (
            'Manual downstream Distribution JB inserted to keep outgoing feeders within the configured engineering limit. Review the new Feeder Cable length and downstream cable schedule before issue.'
        ),
    })
    edited['meta'] = meta
    return edited


def _selected_attach_to_jb_details(payload, source_component_id, target_jb_component_id):
    node_by_id = _node_lookup(payload)
    _incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    source_mcb = node_by_id.get(source_component_id)
    target_jb = node_by_id.get(target_jb_component_id)
    if not source_mcb or source_mcb.get('component_type') != 'MCB':
        return None, 'Select the MCB-fed circuit that should be fed from another 3PH JB.'
    if not target_jb or target_jb.get('component_type') != 'JB3PH':
        return None, 'Select the target 3PH JB that should feed the selected circuit.'

    source_outgoing_edges = [
        edge for edge in outgoing_by_id.get(source_mcb['component_id'], [])
        if edge.get('to_component_id') in node_by_id
    ]
    if len(source_outgoing_edges) != 1:
        return None, 'This first attach pass supports one existing MCB-fed outgoing feeder path at a time.'
    if target_jb['component_id'] in _descendant_component_ids(payload, source_mcb['component_id']):
        return None, 'Target 3PH JB cannot be downstream of the selected source MCB.'

    target_source_mcb = _upstream_mcb_node(payload, target_jb['component_id'])
    if not target_source_mcb:
        return None, 'Target 3PH JB must have an upstream MCB source.'
    if target_source_mcb['component_id'] == source_mcb['component_id']:
        return None, 'Selected circuit is already fed from that 3PH JB source path.'

    target_outgoing_edges = [
        edge for edge in outgoing_by_id.get(target_jb['component_id'], [])
        if edge.get('to_component_id') in node_by_id
    ]
    target_after_count = len(target_outgoing_edges) + len(source_outgoing_edges)
    if target_after_count > 3:
        return None, f"Target 3PH JB would have {target_after_count} outgoing feeders. Limit is 3 in this pass."

    return {
        'source_mcb': source_mcb,
        'target_jb': target_jb,
        'target_source_mcb': target_source_mcb,
        'source_outgoing_edges': source_outgoing_edges,
        'target_outgoing_before': len(target_outgoing_edges),
        'target_outgoing_after': target_after_count,
        'node_by_id': node_by_id,
    }, ''


def _selected_branch_move_details(payload, source_component_id, target_component_id, isolator_location='noIsolator'):
    node_by_id = _node_lookup(payload)
    incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    selected_node = node_by_id.get(source_component_id)
    target_node = node_by_id.get(target_component_id)
    if not selected_node:
        return None, 'Select the branch or circuit component to move.'
    if selected_node.get('component_type') in {'MCB', 'JB3PH'}:
        return None, 'Select a downstream branch component such as a cable, 1PH JB, tracer, or end termination.'
    if not target_node or target_node.get('component_type') not in {'JB3PH', 'MCB'}:
        return None, 'Select the target 3PH JB or standalone MCB that should feed the selected branch.'

    cursor_id = selected_node['component_id']
    visited = set()
    source_parent_jb = None
    branch_root = None
    while cursor_id and cursor_id not in visited:
        visited.add(cursor_id)
        incoming_edges = [
            edge for edge in incoming_by_id.get(cursor_id, [])
            if edge.get('from_component_id') in node_by_id
        ]
        if len(incoming_edges) != 1:
            return None, 'Selected branch must have one clear upstream path to a 3PH JB.'
        parent = node_by_id[incoming_edges[0]['from_component_id']]
        if parent.get('component_type') == 'JB3PH':
            source_parent_jb = parent
            branch_root = node_by_id[cursor_id]
            break
        if parent.get('component_type') == 'MCB':
            return None, 'Selected component is not downstream of a 3PH JB. Use whole-feeder attach for MCB-fed circuits.'
        cursor_id = parent['component_id']

    if not source_parent_jb or not branch_root:
        return None, 'Selected component is not downstream of a 3PH JB.'
    if source_parent_jb['component_id'] == target_node['component_id']:
        return None, 'Selected branch is already fed from the target 3PH JB.'
    if target_node['component_id'] in _descendant_component_ids(payload, branch_root['component_id']):
        return None, 'Target component cannot be downstream of the selected branch.'

    source_mcb = _upstream_mcb_node(payload, source_parent_jb['component_id'])
    target_mcb = target_node if target_node.get('component_type') == 'MCB' else _upstream_mcb_node(payload, target_node['component_id'])
    if not source_mcb or not target_mcb:
        return None, 'Both source and target paths must have upstream MCB sources.'
    if target_mcb['component_id'] == source_mcb['component_id'] and target_node.get('component_type') == 'MCB':
        return None, 'Selected branch is already in the target MCB feeder tree. Select a target 3PH JB instead.'

    source_outgoing_edges = [
        edge for edge in outgoing_by_id.get(source_parent_jb['component_id'], [])
        if edge.get('to_component_id') in node_by_id
    ]
    target_outgoing_edges = [
        edge for edge in outgoing_by_id.get(target_node['component_id'], [])
        if edge.get('to_component_id') in node_by_id
    ]
    target_mcb_existing_edge = None
    target_mcb_existing_child = None
    target_insert_cable_tag = ''
    target_insert_isolator_tag = ''
    target_insert_jb_tag = ''
    target_insert_trunk_length = None
    if target_node.get('component_type') == 'MCB':
        if len(target_outgoing_edges) != 1:
            return None, 'Target MCB must be a standalone one-outgoing feeder. Select an existing 3PH JB for multi-outgoing targets.'
        target_mcb_existing_edge = target_outgoing_edges[0]
        target_mcb_existing_child = node_by_id.get(target_mcb_existing_edge.get('to_component_id'))
        if not target_mcb_existing_child:
            return None, 'Target MCB outgoing feeder path could not be resolved.'
        target_child_descendants = _descendant_component_ids(payload, target_mcb_existing_child['component_id'])
        if target_mcb_existing_child.get('component_type') in {'Cable4C', 'Isolator3PH', 'JB3PH'} or any(
            (node_by_id.get(component_id) or {}).get('component_type') == 'JB3PH'
            for component_id in target_child_descendants
        ):
            return None, 'Target MCB already has a 3PH distribution path. Select its existing 3PH JB as the target.'
        target_outgoing_before = 1
        target_after_count = 2
        target_insert_cable_tag, target_insert_isolator_tag, target_insert_jb_tag = _target_mcb_distribution_preview_tags(
            payload,
            target_mcb,
            isolator_location,
        )
        target_insert_trunk_length = _to_positive_float((target_mcb_existing_child.get('metadata') or {}).get('length_m'))
    else:
        target_outgoing_before = len(target_outgoing_edges)
        target_after_count = target_outgoing_before + 1
    if target_after_count > 3:
        return None, f"Target would have {target_after_count} outgoing feeders. Limit is 3 in this pass."

    is_cross_mcb_move = source_mcb['component_id'] != target_mcb['component_id']
    estimated_branch_rating = 0
    recommended_source_rating = None
    recommended_target_rating = None
    source_rating = _breaker_rating(source_mcb)
    target_rating = _breaker_rating(target_mcb)
    if is_cross_mcb_move:
        estimated_branch_rating = source_rating / len(source_outgoing_edges) if source_outgoing_edges else source_rating
        remaining_source_rating = max(0, source_rating - estimated_branch_rating)
        if remaining_source_rating:
            recommended_source_rating = _next_breaker_size(remaining_source_rating)
        recommended_target_rating = _next_breaker_size(target_rating + estimated_branch_rating)
        if recommended_source_rating is None and remaining_source_rating:
            return None, (
                f"Remaining source feeder rating {remaining_source_rating:g}A cannot be matched to a configured breaker size."
            )
        if recommended_target_rating is None:
            return None, (
                f"Moved branch estimated rating {estimated_branch_rating:g}A would exceed the largest "
                "configured breaker size on the target MCB."
            )

    return {
        'selected_node': selected_node,
        'source_parent_jb': source_parent_jb,
        'target_jb': target_node if target_node.get('component_type') == 'JB3PH' else None,
        'target_component': target_node,
        'branch_root': branch_root,
        'upstream_mcb': source_mcb,
        'target_mcb': target_mcb,
        'target_mcb_existing_edge': target_mcb_existing_edge,
        'target_mcb_existing_child': target_mcb_existing_child,
        'target_insert_cable_tag': target_insert_cable_tag,
        'target_insert_isolator_tag': target_insert_isolator_tag,
        'target_insert_jb_tag': target_insert_jb_tag,
        'target_insert_trunk_length': target_insert_trunk_length,
        'cross_mcb_move': is_cross_mcb_move,
        'estimated_branch_rating': estimated_branch_rating,
        'source_breaker_rating': source_rating,
        'target_breaker_rating': target_rating,
        'recommended_source_breaker_rating': recommended_source_rating,
        'recommended_target_breaker_rating': recommended_target_rating,
        'source_outgoing_before': len(source_outgoing_edges),
        'source_outgoing_after': max(0, len(source_outgoing_edges) - 1),
        'target_outgoing_before': target_outgoing_before,
        'target_outgoing_after': target_after_count,
        'node_by_id': node_by_id,
    }, ''


def _build_attach_to_jb_payload(payload, details, recommended_rating):
    edited = deepcopy(payload)
    source_mcb = details['source_mcb']
    target_jb = details['target_jb']
    target_source_mcb = details['target_source_mcb']
    source_id = source_mcb['component_id']
    target_id = target_jb['component_id']
    target_source_id = target_source_mcb['component_id']
    source_outgoing_edges = details['source_outgoing_edges']
    moved_entry_ids = {edge.get('to_component_id') for edge in source_outgoing_edges}

    nodes = []
    for node in edited.get('nodes', []):
        if node.get('component_id') == source_id:
            continue
        node = dict(node)
        if node.get('component_id') == target_source_id:
            metadata = dict(node.get('metadata') or {})
            metadata.update({
                'breaker_size': recommended_rating,
                'manual_topology_edit': metadata.get('manual_topology_edit') or 'attach_to_jb',
                'attach_to_jb_review_required': True,
                'attached_source_mcb': source_mcb.get('display_tag'),
                'attached_target_jb': target_jb.get('display_tag'),
            })
            node['metadata'] = metadata
            node['display_tag'] = _manual_display_tag(node.get('display_tag', 'MCB'))
            node['label'] = node['display_tag']
        elif node.get('component_id') == target_id and details['target_jb']:
            metadata = dict(node.get('metadata') or {})
            metadata.update({
                'attach_to_jb_review_required': True,
                'attached_source_mcb': source_mcb.get('display_tag'),
            })
            node['metadata'] = metadata
        nodes.append(node)
    edited['nodes'] = nodes
    node_by_id = _node_lookup(edited)

    rewired_edges = []
    for edge in edited.get('edges', []):
        if edge.get('from_component_id') == source_id or edge.get('to_component_id') == source_id:
            continue
        rewired_edges.append(dict(edge))

    for edge in source_outgoing_edges:
        target_node = node_by_id.get(edge.get('to_component_id'))
        if not target_node:
            continue
        rewired_edges.append({
            'from_component_id': target_id,
            'to_component_id': target_node['component_id'],
            'line_ids': target_node.get('line_ids', []),
            'line_uid': target_node.get('line_uid'),
            'branch_index': target_node.get('branch_index'),
            'circuit_index': target_node.get('circuit_index'),
        })
    edited['edges'] = _dedupe_edges(rewired_edges)
    edited = _collapse_single_outgoing_3ph_jbs(edited)

    meta = _fresh_edit_payload_meta(edited)
    meta.update({
        'node_count': len(edited['nodes']),
        'edge_count': len(edited['edges']),
        'manual_topology_warning': (
            'Manual feeder reattachment applied: the selected MCB-fed circuit is now fed from a selected 3PH JB. Breaker rating and cable sizing remain review-required engineering data.'
        ),
    })
    edited['meta'] = meta
    return edited


def _target_mcb_distribution_node(target_mcb, component_type, display_tag, selected_nodes, trunk_length_m, cable_size='4C'):
    component_id = f"{target_mcb['component_id']}:manual_target_mcb_distribution:{component_type}:{display_tag}"
    metadata = {
        'manual_topology_edit': 'move_branch_to_jb',
        'target_mcb_distribution': True,
        'source_mcb': target_mcb.get('display_tag'),
    }
    if component_type == 'Cable4C':
        metadata.update({
            'cable_role': 'MCB_TO_JB3PH',
            'length_m': trunk_length_m,
            'generated_length_m': trunk_length_m,
            'cable_size': _manual_trunk_size(cable_size),
            'generated_cable_size': _manual_trunk_size(cable_size),
            'note': 'Manual target-MCB 3PH distribution trunk cable.',
        })
    if component_type == 'Isolator3PH':
        metadata.update({
            'location': 'incoming',
        })
    if component_type == 'JB3PH':
        metadata.update({
            'circuit_count': len(selected_nodes),
        })
    return {
        'component_id': component_id,
        'component_uid': _component_uid(component_id),
        'display_tag': display_tag,
        'component_type': component_type,
        'display_name': _manual_display_name(component_type),
        'label': display_tag,
        'line_id': target_mcb.get('line_id'),
        'line_ids': _node_line_ids([target_mcb, *selected_nodes]),
        'line_uid': target_mcb.get('line_uid'),
        'branch_index': target_mcb.get('branch_index'),
        'circuit_index': None,
        'metadata': metadata,
    }


def _build_branch_move_payload(payload, details, target_trunk_length_m=None, target_cable_size='4C'):
    edited = deepcopy(payload)
    source_parent_id = details['source_parent_jb']['component_id']
    source_mcb_id = details['upstream_mcb']['component_id']
    target_component = details['target_component']
    target_id = target_component['component_id']
    target_mcb_id = details['target_mcb']['component_id']
    branch_root = details['branch_root']
    branch_root_id = branch_root['component_id']
    target_distribution_jb_id = target_id

    if details['target_mcb_existing_child']:
        selected_nodes = [details['target_mcb_existing_child'], branch_root]
        cable4c = _target_mcb_distribution_node(
            details['target_mcb'],
            'Cable4C',
            details['target_insert_cable_tag'],
            selected_nodes,
            target_trunk_length_m or details['target_insert_trunk_length'],
            cable_size=target_cable_size,
        )
        isolator3ph = (
            _target_mcb_distribution_node(
                details['target_mcb'],
                'Isolator3PH',
                details['target_insert_isolator_tag'],
                selected_nodes,
                target_trunk_length_m or details['target_insert_trunk_length'],
                cable_size=target_cable_size,
            )
            if details['target_insert_isolator_tag']
            else None
        )
        jb3ph = _target_mcb_distribution_node(
            details['target_mcb'],
            'JB3PH',
            details['target_insert_jb_tag'],
            selected_nodes,
            target_trunk_length_m or details['target_insert_trunk_length'],
            cable_size=target_cable_size,
        )
        target_distribution_jb_id = jb3ph['component_id']
        edited['nodes'].extend([node for node in [cable4c, isolator3ph, jb3ph] if node])

    nodes = []
    for node in edited.get('nodes', []):
        node = dict(node)
        if node.get('component_id') == source_parent_id:
            metadata = dict(node.get('metadata') or {})
            metadata.update({
                'move_branch_to_jb_review_required': True,
                'moved_branch_out': branch_root.get('display_tag'),
            })
            node['metadata'] = metadata
        elif node.get('component_id') == source_mcb_id and details['cross_mcb_move']:
            metadata = dict(node.get('metadata') or {})
            metadata.update({
                'manual_topology_edit': metadata.get('manual_topology_edit') or 'move_branch_to_jb',
                'move_branch_to_jb_review_required': True,
                'moved_branch_out': branch_root.get('display_tag'),
                'estimated_moved_branch_rating': details['estimated_branch_rating'],
                'previous_breaker_size': details['source_breaker_rating'],
                'recommended_breaker_size': details['recommended_source_breaker_rating'],
            })
            if details['recommended_source_breaker_rating']:
                metadata['breaker_size'] = details['recommended_source_breaker_rating']
            node['metadata'] = metadata
            node['display_tag'] = _manual_display_tag(node.get('display_tag', 'MCB'))
            node['label'] = node['display_tag']
        elif node.get('component_id') == target_id and details['target_jb']:
            metadata = dict(node.get('metadata') or {})
            metadata.update({
                'move_branch_to_jb_review_required': True,
                'moved_branch_in': branch_root.get('display_tag'),
            })
            node['metadata'] = metadata
        elif node.get('component_id') == target_mcb_id and (details['cross_mcb_move'] or details['target_mcb_existing_child']):
            metadata = dict(node.get('metadata') or {})
            metadata.update({
                'manual_topology_edit': metadata.get('manual_topology_edit') or 'move_branch_to_jb',
                'move_branch_to_jb_review_required': True,
                'moved_branch_in': branch_root.get('display_tag'),
                'estimated_moved_branch_rating': details['estimated_branch_rating'],
                'previous_breaker_size': details['target_breaker_rating'],
                'recommended_breaker_size': details['recommended_target_breaker_rating'],
            })
            if details['recommended_target_breaker_rating']:
                metadata['breaker_size'] = details['recommended_target_breaker_rating']
            node['metadata'] = metadata
            node['display_tag'] = _manual_display_tag(node.get('display_tag', 'MCB'))
            node['label'] = node['display_tag']
        elif node.get('component_id') == branch_root_id:
            metadata = dict(node.get('metadata') or {})
            metadata.update({
                'manual_topology_edit': metadata.get('manual_topology_edit') or 'move_branch_to_jb',
                'moved_from_jb': details['source_parent_jb'].get('display_tag'),
                'moved_to_jb': (details['target_jb'] or {}).get('display_tag') or details['target_insert_jb_tag'],
                'cross_mcb_move': details['cross_mcb_move'],
            })
            node['metadata'] = metadata
        nodes.append(node)
    edited['nodes'] = nodes

    rewired_edges = []
    for edge in edited.get('edges', []):
        if (
            edge.get('from_component_id') == source_parent_id
            and edge.get('to_component_id') == branch_root_id
        ):
            continue
        if (
            details['target_mcb_existing_edge']
            and edge.get('from_component_id') == details['target_mcb_existing_edge'].get('from_component_id')
            and edge.get('to_component_id') == details['target_mcb_existing_edge'].get('to_component_id')
        ):
            continue
        rewired_edges.append(dict(edge))

    if details['target_mcb_existing_child']:
        jb_id = target_distribution_jb_id
        rewired_edges.extend([
            *_manual_distribution_edges(target_mcb_id, cable4c, isolator3ph, jb3ph),
            {
                'from_component_id': jb_id,
                'to_component_id': details['target_mcb_existing_child']['component_id'],
                'line_ids': details['target_mcb_existing_child'].get('line_ids', []),
                'line_uid': details['target_mcb_existing_child'].get('line_uid'),
                'branch_index': details['target_mcb_existing_child'].get('branch_index'),
                'circuit_index': details['target_mcb_existing_child'].get('circuit_index'),
            },
        ])

    rewired_edges.append({
        'from_component_id': target_distribution_jb_id,
        'to_component_id': branch_root_id,
        'line_ids': branch_root.get('line_ids', []),
        'line_uid': branch_root.get('line_uid'),
        'branch_index': branch_root.get('branch_index'),
        'circuit_index': branch_root.get('circuit_index'),
    })
    edited['edges'] = _dedupe_edges(rewired_edges)
    edited = _collapse_single_outgoing_3ph_jbs(edited)

    meta = _fresh_edit_payload_meta(edited)
    meta.update({
        'node_count': len(edited['nodes']),
        'edge_count': len(edited['edges']),
        'manual_topology_warning': (
            'Manual branch move applied: the selected downstream branch is now fed from a different 3PH distribution point. Review cable routing, breaker rating, and schedule before issue.'
        ),
    })
    edited['meta'] = meta
    return edited


def preview_combine_feeders(project_id, component_ids, trunk_length_m=None, cable_size='4C'):
    component_ids = [component_id for component_id in (component_ids or []) if component_id]
    if len(component_ids) < 2:
        return {
            'ok': False,
            'error': 'Select at least two MCB feeder sources to combine.',
        }
    project = ProjectData.objects.get(proj_id=project_id)
    normalized_cable_size = _manual_trunk_size(cable_size)
    payload = build_project_sld_payload(project_id)
    selected_nodes, invalid_ids = _selected_mcb_nodes(payload, component_ids)
    if invalid_ids:
        return {
            'ok': False,
            'error': 'One or more selected components are not eligible MCB feeder sources.',
            'invalid_component_ids': invalid_ids,
        }
    if len(selected_nodes) < 2:
        return {
            'ok': False,
            'error': 'Select at least two valid MCB feeder sources to combine.',
        }
    _, outgoing_by_id = _edge_lookup(payload)
    selected_ids = {node['component_id'] for node in selected_nodes}
    missing_outgoing = [
        node['display_tag']
        for node in selected_nodes
        if not any(
            edge.get('to_component_id') not in selected_ids
            for edge in outgoing_by_id.get(node['component_id'], [])
        )
    ]
    if missing_outgoing:
        return {
            'ok': False,
            'error': 'Selected MCB feeder sources must have outgoing feeder paths to combine.',
            'missing_outgoing_feeders': missing_outgoing,
        }

    default_trunk_length = _default_combined_trunk_length(payload, selected_nodes)
    default_trunk_basis = 'max_selected_feeder_length' if default_trunk_length is not None else 'project_default'
    trunk_length = _to_positive_float(trunk_length_m, default_trunk_length or project.ckt_ln)
    if trunk_length is None:
        return {
            'ok': False,
            'error': 'Enter a valid positive Feeder Cable length for the combined feeder.',
        }

    current_lookup = _project_line_current_lookup(project_id)
    ratings = [_breaker_rating(node) for node in selected_nodes]
    total_current, rating_basis = _combined_feeder_current(selected_nodes, current_lookup)
    recommended_rating = _next_breaker_size(total_current)
    if recommended_rating is None:
        return {
            'ok': False,
            'error': f"Combined feeder current {total_current:g}A exceeds the largest configured breaker size.",
        }

    primary = selected_nodes[0]
    removed_nodes = selected_nodes[1:]
    existing_cable4c, existing_isolator3ph, existing_jb3ph = _manual_combine_distribution(payload, primary)
    primary_tag = _manual_display_tag(primary.get('display_tag', 'MCB'))
    tag_suffix = primary_tag.split('_', 1)[1] if '_' in primary_tag else primary_tag
    added_component_types = []
    added_display_tags = []
    if not existing_cable4c:
        added_component_types.append('Cable4C')
        added_display_tags.append(f"CCAB4C_{tag_suffix}-M")
    if _requires_incoming_isolator(project.isolator_location) and not existing_isolator3ph:
        added_component_types.append('Isolator3PH')
        added_display_tags.append(f"ISOL_3PH_{tag_suffix}-M")
    if not existing_jb3ph:
        added_component_types.append('JB3PH')
        added_display_tags.append(f"JB3PH_{tag_suffix}-M")
    return {
        'ok': True,
        'project_id': project_id,
        'edit_type': 'combine_feeders',
        'selected_component_ids': [node['component_id'] for node in selected_nodes],
        'primary_component_id': primary['component_id'],
        'primary_display_tag': primary['display_tag'],
        'updated_display_tags': [primary_tag],
        'removed_component_ids': [node['component_id'] for node in removed_nodes],
        'removed_display_tags': [node['display_tag'] for node in removed_nodes],
        'added_component_types': added_component_types,
        'added_display_tags': added_display_tags,
        'extends_existing_combine': bool(existing_jb3ph),
        'input_breaker_ratings': ratings,
        'combined_breaker_rating': total_current,
        'combined_feeder_current': total_current,
        'breaker_rating_basis': rating_basis,
        'recommended_breaker_rating': recommended_rating,
        'trunk_length_m': trunk_length,
        'trunk_length_basis': _trunk_length_basis(trunk_length_m, default_trunk_basis),
        'cable_size': normalized_cable_size,
        'affected_lines': sorted({node.get('line_id') for node in selected_nodes if node.get('line_id')}),
        'affected_branch_count': len({
            (node.get('line_uid'), node.get('branch_index'))
            for node in selected_nodes
        }),
        'warning': (
            'This workflow combines feeders through a manual Feeder Cable and Distribution JB. Review recalculated cold-cable sizing before issue.'
        ),
    }


def preview_split_circuits(project_id, component_ids):
    component_ids = [component_id for component_id in (component_ids or []) if component_id]
    if not component_ids:
        return {
            'ok': False,
            'error': 'Select one MCB feeder source with multiple downstream circuits to split.',
        }
    payload = build_project_sld_payload(project_id)
    source_mcb, invalid_ids = _selected_split_mcb(payload, component_ids)
    if invalid_ids or source_mcb is None:
        return {
            'ok': False,
            'error': 'Select exactly one MCB feeder source to split.',
            'invalid_component_ids': invalid_ids,
        }
    split_details = _split_source_details(payload, source_mcb)
    if not split_details or len(split_details['entry_nodes']) < 2:
        return {
            'ok': False,
            'error': 'Selected MCB must feed multiple downstream circuits through one distribution path.',
        }

    source_rating = float((source_mcb.get('metadata') or {}).get('breaker_size') or 0)
    split_circuit_count = len(split_details['entry_nodes'])
    proportional_rating = source_rating / split_circuit_count if split_circuit_count else source_rating
    recommended_rating = _next_breaker_size(proportional_rating)
    if recommended_rating is None:
        return {
            'ok': False,
            'error': f"Split feeder rating {proportional_rating:g}A exceeds the largest configured breaker size.",
        }

    return {
        'ok': True,
        'project_id': project_id,
        'edit_type': 'split_circuits',
        'selected_component_ids': [source_mcb['component_id']],
        'source_mcb_component_id': source_mcb['component_id'],
        'source_mcb_display_tag': source_mcb['display_tag'],
        'updated_display_tags': [_split_mcb_display_tag(source_mcb, 1)],
        'added_display_tags': [
            _split_mcb_display_tag(source_mcb, index)
            for index in range(2, split_circuit_count + 1)
        ],
        'removed_display_tags': [
            node['display_tag']
            for node in payload.get('nodes', [])
            if node['component_id'] in set(split_details['shared_component_ids'])
        ],
        'selected_circuit_count': split_circuit_count,
        'source_circuit_count': split_circuit_count,
        'new_mcb_count': split_circuit_count - 1,
        'source_breaker_rating': source_rating,
        'recommended_breaker_rating': recommended_rating,
        'affected_lines': sorted({node.get('line_id') for node in split_details['entry_nodes'] if node.get('line_id')}),
        'affected_branch_count': len({
            (node.get('line_uid'), node.get('branch_index'))
            for node in split_details['entry_nodes']
        }),
        'warning': (
            'This workflow splits one multi-circuit MCB feeder into independent MCB-fed circuits. Review the reduced breaker rating before issue.'
        ),
    }


def preview_downstream_jb(project_id, parent_component_id, branch_component_ids, trunk_length_m=None, cable_size='4C'):
    project = ProjectData.objects.get(proj_id=project_id)
    default_length = float(project.loop_ln)
    trunk_length = _to_positive_float(trunk_length_m, default_length)
    if trunk_length is None:
        return {
            'ok': False,
            'error': 'Enter a valid downstream JB trunk cable length greater than zero.',
        }

    payload = build_project_sld_payload(project_id)
    details = _selected_downstream_jb_details(payload, parent_component_id, branch_component_ids)
    if not details:
        return {
            'ok': False,
            'error': 'Select one upstream Distribution JB.',
        }
    if details['invalid_ids']:
        return {
            'ok': False,
            'error': 'Selected outgoing branches must be directly fed from the selected Distribution JB.',
            'invalid_component_ids': details['invalid_ids'],
        }
    selected_edges = details['selected_edges']
    outgoing_count = len(details['outgoing_edges'])
    selected_count = len(selected_edges)
    if selected_count < 2:
        return {
            'ok': False,
            'error': 'Select at least two outgoing branches to move under the new downstream 3PH JB.',
        }
    if selected_count > 3:
        return {
            'ok': False,
            'error': 'A downstream 3PH JB can feed at most three outgoing branches in this pass.',
        }
    parent_after_count = outgoing_count - selected_count + 1
    if parent_after_count > 3:
        return {
            'ok': False,
            'error': f"Move more branches: parent 3PH JB would still have {parent_after_count} outgoing feeders.",
            'parent_outgoing_after': parent_after_count,
        }

    node_by_id = details['node_by_id']
    selected_nodes = [node_by_id[edge['to_component_id']] for edge in selected_edges]
    cable_tag, isolator_tag, jb_tag = _downstream_jb_preview_tags(payload, details['parent'], project.isolator_location)
    added_component_types = ['Cable4C']
    added_display_tags = [cable_tag]
    if isolator_tag:
        added_component_types.append('Isolator3PH')
        added_display_tags.append(isolator_tag)
    added_component_types.append('JB3PH')
    added_display_tags.append(jb_tag)
    return {
        'ok': True,
        'project_id': project_id,
        'edit_type': 'downstream_jb',
        'parent_component_id': details['parent']['component_id'],
        'parent_display_tag': details['parent']['display_tag'],
        'selected_component_ids': [node['component_id'] for node in selected_nodes],
        'selected_display_tags': [node['display_tag'] for node in selected_nodes],
        'added_component_types': added_component_types,
        'added_display_tags': added_display_tags,
        'parent_outgoing_before': outgoing_count,
        'parent_outgoing_after': parent_after_count,
        'downstream_outgoing_count': selected_count,
        'trunk_length_m': trunk_length,
        'default_trunk_length_m': default_length,
        'cable_size': _manual_trunk_size(cable_size),
        'affected_lines': sorted({
            line_id
            for node in selected_nodes
            for line_id in (node.get('line_ids') or ([node.get('line_id')] if node.get('line_id') else []))
            if line_id
        }),
        'warning': (
            'This workflow inserts a downstream Distribution JB and moves selected outgoing branches under it. Confirm the new Feeder Cable length before issue.'
        ),
    }


def preview_attach_to_jb(project_id, source_component_id, target_jb_component_id, trunk_length_m=None, cable_size='4C'):
    project = ProjectData.objects.get(proj_id=project_id)
    payload = build_project_sld_payload(project_id)
    source_node = _node_lookup(payload).get(source_component_id)
    if source_node and source_node.get('component_type') != 'MCB':
        details, error = _selected_branch_move_details(
            payload,
            source_component_id,
            target_jb_component_id,
            project.isolator_location,
        )
        if not details:
            return {
                'ok': False,
                'error': error,
            }
        branch_root = details['branch_root']
        selected_node = details['selected_node']
        affected_nodes = [
            details['node_by_id'][component_id]
            for component_id in _descendant_component_ids(payload, branch_root['component_id']) | {branch_root['component_id']}
            if component_id in details['node_by_id']
        ]
        affected_lines = sorted({
            line_id
            for node in affected_nodes
            for line_id in (node.get('line_ids') or ([node.get('line_id')] if node.get('line_id') else []))
            if line_id
        })
        target_trunk_length = None
        if details['target_mcb_existing_child']:
            target_trunk_length = _to_positive_float(
                trunk_length_m,
                details['target_insert_trunk_length'] or project.ckt_ln,
            )
            if target_trunk_length is None:
                return {
                    'ok': False,
                    'error': 'Enter a valid positive Feeder Cable length for the promoted target MCB.',
                }
        return {
            'ok': True,
            'project_id': project_id,
            'edit_type': 'move_branch_to_jb',
            'source_component_id': selected_node['component_id'],
            'source_display_tag': selected_node['display_tag'],
            'branch_root_component_id': branch_root['component_id'],
            'branch_root_display_tag': branch_root['display_tag'],
            'source_jb_component_id': details['source_parent_jb']['component_id'],
            'source_jb_display_tag': details['source_parent_jb']['display_tag'],
            'target_component_id': details['target_component']['component_id'],
            'target_display_tag': details['target_component']['display_tag'],
            'target_component_type': details['target_component']['component_type'],
            'target_jb_component_id': (details['target_jb'] or {}).get('component_id'),
            'target_jb_display_tag': (details['target_jb'] or {}).get('display_tag'),
            'upstream_mcb_component_id': details['upstream_mcb']['component_id'],
            'upstream_mcb_display_tag': details['upstream_mcb']['display_tag'],
            'target_mcb_component_id': details['target_mcb']['component_id'],
            'target_mcb_display_tag': details['target_mcb']['display_tag'],
            'insert_target_distribution_jb': bool(details['target_mcb_existing_child']),
            'added_display_tags': [
                tag for tag in [
                    details['target_insert_cable_tag'],
                    details['target_insert_isolator_tag'],
                    details['target_insert_jb_tag'],
                ] if tag
            ],
            'cross_mcb_move': details['cross_mcb_move'],
            'estimated_branch_rating': details['estimated_branch_rating'],
            'source_breaker_rating': details['source_breaker_rating'],
            'target_breaker_rating': details['target_breaker_rating'],
            'recommended_source_breaker_rating': details['recommended_source_breaker_rating'],
            'recommended_target_breaker_rating': details['recommended_target_breaker_rating'],
            'moved_component_ids': [branch_root['component_id']],
            'moved_display_tags': [branch_root['display_tag']],
            'source_outgoing_before': details['source_outgoing_before'],
            'source_outgoing_after': details['source_outgoing_after'],
            'target_outgoing_before': details['target_outgoing_before'],
            'target_outgoing_after': details['target_outgoing_after'],
            'target_insert_trunk_length': target_trunk_length,
            'target_insert_cable_size': _manual_trunk_size(cable_size),
            'affected_lines': affected_lines,
            'warning': (
                'This workflow promotes the target MCB with a manual Feeder Cable and Distribution JB before moving the selected branch. Review cable routing and breaker rating before issue.'
                if details['target_mcb_existing_child']
                else 'This workflow moves one downstream branch between Distribution JBs. Review cable routing and breaker rating before issue.'
            ),
        }

    details, error = _selected_attach_to_jb_details(payload, source_component_id, target_jb_component_id)
    if not details:
        return {
            'ok': False,
            'error': error,
        }

    source_mcb = details['source_mcb']
    target_jb = details['target_jb']
    target_source_mcb = details['target_source_mcb']
    source_rating = float((source_mcb.get('metadata') or {}).get('breaker_size') or 0)
    target_source_rating = float((target_source_mcb.get('metadata') or {}).get('breaker_size') or 0)
    combined_rating = source_rating + target_source_rating
    recommended_rating = _next_breaker_size(combined_rating)
    if recommended_rating is None:
        return {
            'ok': False,
            'error': f"Reattached feeder rating {combined_rating:g}A exceeds the largest configured breaker size.",
        }

    moved_nodes = [
        details['node_by_id'][edge['to_component_id']]
        for edge in details['source_outgoing_edges']
        if edge.get('to_component_id') in details['node_by_id']
    ]
    affected_lines = sorted({
        line_id
        for node in [source_mcb, *moved_nodes]
        for line_id in (node.get('line_ids') or ([node.get('line_id')] if node.get('line_id') else []))
        if line_id
    })
    return {
        'ok': True,
        'project_id': project_id,
        'edit_type': 'attach_to_jb',
        'source_component_id': source_mcb['component_id'],
        'source_display_tag': source_mcb['display_tag'],
        'target_jb_component_id': target_jb['component_id'],
        'target_jb_display_tag': target_jb['display_tag'],
        'target_source_mcb_component_id': target_source_mcb['component_id'],
        'target_source_mcb_display_tag': target_source_mcb['display_tag'],
        'removed_component_ids': [source_mcb['component_id']],
        'removed_display_tags': [source_mcb['display_tag']],
        'moved_component_ids': [node['component_id'] for node in moved_nodes],
        'moved_display_tags': [node['display_tag'] for node in moved_nodes],
        'target_outgoing_before': details['target_outgoing_before'],
        'target_outgoing_after': details['target_outgoing_after'],
        'source_breaker_rating': source_rating,
        'target_source_breaker_rating': target_source_rating,
        'combined_breaker_rating': combined_rating,
        'recommended_breaker_rating': recommended_rating,
        'affected_lines': affected_lines,
        'warning': (
            'This workflow reattaches one existing MCB-fed circuit to a selected 3PH JB. Review the updated MCB rating and cable schedule before issue.'
        ),
    }


def _replay_combine_feeders(project, payload, inputs):
    trunk_length = _to_positive_float(inputs.get('trunk_length_m'), project.ckt_ln)
    if trunk_length is None:
        return None, 'Combine feeders replay failed: invalid or missing trunk cable length.'
    selected_nodes, invalid_ids = _selected_mcb_nodes(payload, inputs.get('component_ids') or [])
    if invalid_ids or len(selected_nodes) < 2:
        return None, 'Combine feeders replay failed: selected MCB sources no longer match the generated SLD.'

    selected_ids = {node['component_id'] for node in selected_nodes}
    _incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    if any(
        not any(edge.get('to_component_id') not in selected_ids for edge in outgoing_by_id.get(node['component_id'], []))
        for node in selected_nodes
    ):
        return None, 'Combine feeders replay failed: one selected MCB no longer has an outgoing feeder path.'

    current_lookup = _project_line_current_lookup(project.proj_id)
    total_current, _rating_basis = _combined_feeder_current(selected_nodes, current_lookup)
    recommended_rating = _next_breaker_size(total_current)
    if recommended_rating is None:
        return None, 'Combine feeders replay failed: combined current exceeds available breaker sizes.'

    return _build_edited_payload(
        payload,
        selected_nodes,
        recommended_rating,
        project.isolator_location,
        trunk_length_m=trunk_length,
        cable_size=inputs.get('cable_size') or '4C',
        current_lookup=current_lookup,
    ), ''


def _replay_split_circuits(_project, payload, inputs):
    source_mcb, invalid_ids = _selected_split_mcb(payload, inputs.get('component_ids') or [])
    if invalid_ids or source_mcb is None:
        return None, 'Split circuits replay failed: selected MCB source no longer matches the generated SLD.'
    split_details = _split_source_details(payload, source_mcb)
    if not split_details or len(split_details['entry_nodes']) < 2:
        return None, 'Split circuits replay failed: selected MCB no longer feeds multiple downstream circuits.'

    source_rating = _breaker_rating(source_mcb)
    proportional_rating = source_rating / len(split_details['entry_nodes'])
    recommended_rating = _next_breaker_size(proportional_rating)
    if recommended_rating is None:
        return None, 'Split circuits replay failed: reduced rating exceeds available breaker sizes.'

    return _build_split_payload(payload, source_mcb, split_details, recommended_rating), ''


def _replay_downstream_jb(project, payload, inputs):
    trunk_length = _to_positive_float(inputs.get('trunk_length_m'), project.loop_ln)
    if trunk_length is None:
        return None, 'Downstream JB replay failed: invalid or missing trunk cable length.'
    details = _selected_downstream_jb_details(
        payload,
        inputs.get('parent_component_id'),
        inputs.get('branch_component_ids') or [],
    )
    if not details or details.get('invalid_ids'):
        return None, 'Downstream JB replay failed: selected parent JB or outgoing branches no longer match.'

    selected_count = len(details['selected_edges'])
    parent_after_count = len(details['outgoing_edges']) - selected_count + 1
    if selected_count < 2 or selected_count > 3 or parent_after_count > 3:
        return None, 'Downstream JB replay failed: 3PH JB outgoing-count rules are no longer satisfied.'

    return _build_downstream_jb_payload(
        payload,
        details,
        trunk_length,
        project.isolator_location,
        cable_size=inputs.get('cable_size') or '4C',
    ), ''


def _replay_attach_to_jb(project, payload, inputs):
    source_component_id = inputs.get('source_component_id')
    target_component_id = inputs.get('target_component_id')
    source_node = _node_lookup(payload).get(source_component_id)
    if not source_node:
        return None, 'Attach replay failed: selected source component no longer exists.'

    if source_node.get('component_type') != 'MCB':
        details, error = _selected_branch_move_details(
            payload,
            source_component_id,
            target_component_id,
            project.isolator_location,
        )
        if not details:
            return None, error or 'Branch move replay failed: source branch or target no longer matches.'
        target_trunk_length = _to_positive_float(
            inputs.get('trunk_length_m'),
            details.get('target_insert_trunk_length') or project.ckt_ln,
        )
        if details.get('target_mcb_existing_child') and target_trunk_length is None:
            return None, 'Branch move replay failed: target MCB promotion needs a valid trunk cable length.'
        return _build_branch_move_payload(
            payload,
            details,
            target_trunk_length_m=target_trunk_length,
            target_cable_size=inputs.get('cable_size') or '4C',
        ), ''

    details, error = _selected_attach_to_jb_details(payload, source_component_id, target_component_id)
    if not details:
        return None, error or 'Attach replay failed: source feeder or target JB no longer matches.'
    recommended_rating = _next_breaker_size(
        _breaker_rating(details['source_mcb']) + _breaker_rating(details['target_source_mcb'])
    )
    if recommended_rating is None:
        return None, 'Attach replay failed: combined rating exceeds available breaker sizes.'
    return _build_attach_to_jb_payload(payload, details, recommended_rating), ''


def _replay_scoped_reset(generated_payload, payload, inputs):
    reset_scope, error = _selected_reset_scope(
        payload,
        inputs.get('component_id') or inputs.get('source_mcb_component_id'),
    )
    if not reset_scope:
        return None, error or 'Scoped reset replay failed: selected feeder tree no longer matches.'
    edited_payload = _build_scoped_reset_payload(payload, generated_payload, reset_scope)
    if not edited_payload:
        return None, 'Scoped reset replay failed: generated replacement tree could not be resolved.'
    return edited_payload, ''


def replay_topology_operations(project_id, generated_payload, operations):
    project = ProjectData.objects.get(proj_id=project_id)
    replayed_payload = deepcopy(generated_payload)
    for index, operation in enumerate(operations or [], start=1):
        operation_type = operation.get('operation_type')
        inputs = operation.get('inputs') or {}
        if operation_type == 'combine_feeders':
            replayed_payload, error = _replay_combine_feeders(project, replayed_payload, inputs)
        elif operation_type == 'split_circuits':
            replayed_payload, error = _replay_split_circuits(project, replayed_payload, inputs)
        elif operation_type == 'downstream_jb':
            replayed_payload, error = _replay_downstream_jb(project, replayed_payload, inputs)
        elif operation_type in {'attach_to_jb', 'move_branch_to_jb'}:
            replayed_payload, error = _replay_attach_to_jb(project, replayed_payload, inputs)
        elif operation_type == 'scoped_reset':
            replayed_payload, error = _replay_scoped_reset(generated_payload, replayed_payload, inputs)
        else:
            replayed_payload, error = None, f'Unsupported topology operation: {operation_type or "unknown"}.'

        if not replayed_payload:
            return {
                'ok': False,
                'error': error or 'Topology operation replay failed.',
                'failed_operation_index': index,
                'failed_operation_type': operation_type or '',
            }

    return {
        'ok': True,
        'payload': replayed_payload,
    }


@transaction.atomic
def apply_combine_feeders(project_id, component_ids, trunk_length_m=None, cable_size='4C', user=None, remarks=''):
    project = _lock_project_for_topology_apply(project_id)
    preview = preview_combine_feeders(project_id, component_ids, trunk_length_m=trunk_length_m, cable_size=cable_size)
    if not preview['ok']:
        return preview

    baseline_payload = build_project_sld_payload(project_id, apply_topology=False)
    active_payload = build_project_sld_payload(project_id)
    selected_nodes, _invalid_ids = _selected_mcb_nodes(active_payload, preview['selected_component_ids'])
    current_lookup = _project_line_current_lookup(project_id)
    edited_payload = _build_edited_payload(
        active_payload,
        selected_nodes,
        preview['recommended_breaker_rating'],
        project.isolator_location,
        trunk_length_m=preview['trunk_length_m'],
        cable_size=preview['cable_size'],
        current_lookup=current_lookup,
    )
    cold_cable_impact = _apply_combined_feeder_cold_cable_impact(
        project,
        active_payload,
        edited_payload,
        selected_nodes,
        preview,
    )

    boq_overrides = {
        'mcb_total': _graph_component_count(edited_payload, ['MCB']),
        'junction_box_total': _graph_component_count(edited_payload, ['JB3PH', 'JB1PH']),
    }

    topology_operations, topology_chain_audit = _topology_operation_chain(project, 'combine_feeders', preview, {
        'component_ids': preview['selected_component_ids'],
        'trunk_length_m': preview['trunk_length_m'],
        'cable_size': preview['cable_size'],
    }, generated_payload=baseline_payload)
    edit_payload, validation_summary = _finalize_edit_payload(
        edited_payload,
        topology_operations,
        preview,
        preview_key='combine_preview',
        boq_overrides=boq_overrides,
        topology_chain_audit=topology_chain_audit,
    )
    if edit_payload is None:
        return {
            'ok': False,
            'error': 'Topology edit failed structural validation.',
            'validation_summary': validation_summary,
        }
    edit_payload['cold_cable_impact_summary'] = cold_cable_impact
    edit_payload.setdefault('downstream_summaries', {})['cold_cable'] = cold_cable_impact
    SLDTopologyEdit.objects.filter(project=project, status='applied').update(status='superseded')
    edit = SLDTopologyEdit.objects.create(
        project=project,
        edit_type='combine_feeders',
        status='applied',
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        remarks=remarks or '',
        baseline_fingerprint=payload_fingerprint(baseline_payload),
        generated_snapshot=baseline_payload,
        edit_payload=edit_payload,
        validation_summary=validation_summary,
    )
    return {
        'ok': True,
        'edit_id': edit.id,
        'preview': preview,
        'cold_cable_impact': cold_cable_impact,
        'validation_summary': edit.validation_summary,
    }


@transaction.atomic
def apply_attach_to_jb(
    project_id,
    source_component_id,
    target_jb_component_id,
    trunk_length_m=None,
    cable_size='4C',
    user=None,
    remarks='',
):
    project = _lock_project_for_topology_apply(project_id)
    preview = preview_attach_to_jb(
        project_id,
        source_component_id,
        target_jb_component_id,
        trunk_length_m=trunk_length_m,
        cable_size=cable_size,
    )
    if not preview['ok']:
        return preview

    generated_payload = build_project_sld_payload(project_id, apply_topology=False)
    active_payload = build_project_sld_payload(project_id)
    if preview['edit_type'] == 'move_branch_to_jb':
        details, error = _selected_branch_move_details(
            active_payload,
            preview['source_component_id'],
            preview.get('target_component_id') or preview.get('target_jb_component_id'),
            project.isolator_location,
        )
        if not details:
            return {
                'ok': False,
                'error': error or 'Selected branch move topology could not be rebuilt safely.',
            }
        edited_payload = _build_branch_move_payload(
            active_payload,
            details,
            target_trunk_length_m=preview.get('target_insert_trunk_length'),
            target_cable_size=preview.get('target_insert_cable_size') or cable_size,
        )
        edit_payload_key = 'move_branch_to_jb_preview'
    else:
        details, error = _selected_attach_to_jb_details(
            active_payload,
            preview['source_component_id'],
            preview['target_jb_component_id'],
        )
        if not details:
            return {
                'ok': False,
                'error': error or 'Selected feeder attach topology could not be rebuilt safely.',
            }
        edited_payload = _build_attach_to_jb_payload(active_payload, details, preview['recommended_breaker_rating'])
        edit_payload_key = 'attach_to_jb_preview'
    boq_overrides = {
        'mcb_total': _graph_component_count(edited_payload, ['MCB']),
        'junction_box_total': _graph_component_count(edited_payload, ['JB3PH', 'JB1PH']),
    }

    topology_operations, topology_chain_audit = _topology_operation_chain(project, preview['edit_type'], preview, {
        'source_component_id': preview['source_component_id'],
        'target_component_id': preview.get('target_component_id') or preview.get('target_jb_component_id'),
        'trunk_length_m': preview.get('target_insert_trunk_length') or trunk_length_m,
        'cable_size': preview.get('target_insert_cable_size') or cable_size,
    }, generated_payload=generated_payload)
    edit_payload, validation_summary = _finalize_edit_payload(
        edited_payload,
        topology_operations,
        preview,
        preview_key=edit_payload_key,
        boq_overrides=boq_overrides,
        topology_chain_audit=topology_chain_audit,
    )
    if edit_payload is None:
        return {
            'ok': False,
            'error': 'Topology edit failed structural validation.',
            'validation_summary': validation_summary,
        }
    SLDTopologyEdit.objects.filter(project=project, status='applied').update(status='superseded')
    edit = SLDTopologyEdit.objects.create(
        project=project,
        edit_type=preview['edit_type'],
        status='applied',
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        remarks=remarks or '',
        baseline_fingerprint=payload_fingerprint(generated_payload),
        generated_snapshot=generated_payload,
        edit_payload=edit_payload,
        validation_summary=validation_summary,
    )
    return {
        'ok': True,
        'edit_id': edit.id,
        'preview': preview,
        'validation_summary': edit.validation_summary,
    }


@transaction.atomic
def apply_downstream_jb(
    project_id,
    parent_component_id,
    branch_component_ids,
    trunk_length_m=None,
    cable_size='4C',
    user=None,
    remarks='',
):
    project = _lock_project_for_topology_apply(project_id)
    preview = preview_downstream_jb(
        project_id,
        parent_component_id,
        branch_component_ids,
        trunk_length_m,
        cable_size=cable_size,
    )
    if not preview['ok']:
        return preview

    generated_payload = build_project_sld_payload(project_id, apply_topology=False)
    active_payload = build_project_sld_payload(project_id)
    details = _selected_downstream_jb_details(
        active_payload,
        preview['parent_component_id'],
        preview['selected_component_ids'],
    )
    if not details:
        return {
            'ok': False,
            'error': 'Selected downstream JB topology could not be rebuilt safely.',
        }
    edited_payload = _build_downstream_jb_payload(
        active_payload,
        details,
        preview['trunk_length_m'],
        project.isolator_location,
        cable_size=preview['cable_size'],
    )
    boq_overrides = {
        'mcb_total': _graph_component_count(edited_payload, ['MCB']),
        'junction_box_total': _graph_component_count(edited_payload, ['JB3PH', 'JB1PH']),
    }

    topology_operations, topology_chain_audit = _topology_operation_chain(project, 'downstream_jb', preview, {
        'parent_component_id': preview['parent_component_id'],
        'branch_component_ids': preview['selected_component_ids'],
        'trunk_length_m': preview['trunk_length_m'],
        'cable_size': preview['cable_size'],
    }, generated_payload=generated_payload)
    edit_payload, validation_summary = _finalize_edit_payload(
        edited_payload,
        topology_operations,
        preview,
        preview_key='downstream_jb_preview',
        boq_overrides=boq_overrides,
        topology_chain_audit=topology_chain_audit,
    )
    if edit_payload is None:
        return {
            'ok': False,
            'error': 'Topology edit failed structural validation.',
            'validation_summary': validation_summary,
        }
    SLDTopologyEdit.objects.filter(project=project, status='applied').update(status='superseded')
    edit = SLDTopologyEdit.objects.create(
        project=project,
        edit_type='downstream_jb',
        status='applied',
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        remarks=remarks or '',
        baseline_fingerprint=payload_fingerprint(generated_payload),
        generated_snapshot=generated_payload,
        edit_payload=edit_payload,
        validation_summary=validation_summary,
    )
    return {
        'ok': True,
        'edit_id': edit.id,
        'preview': preview,
        'validation_summary': edit.validation_summary,
    }


@transaction.atomic
def apply_split_circuits(project_id, component_ids, user=None, remarks=''):
    project = _lock_project_for_topology_apply(project_id)
    preview = preview_split_circuits(project_id, component_ids)
    if not preview['ok']:
        return preview

    generated_payload = build_project_sld_payload(project_id, apply_topology=False)
    active_payload = build_project_sld_payload(project_id)
    source_mcb, _invalid_ids = _selected_split_mcb(active_payload, preview['selected_component_ids'])
    if source_mcb is None:
        return {
            'ok': False,
            'error': 'Selected MCB split topology could not be rebuilt safely.',
        }
    split_details = _split_source_details(active_payload, source_mcb)
    if not split_details:
        return {
            'ok': False,
            'error': 'Selected MCB split topology could not be rebuilt safely.',
        }
    edited_payload = _build_split_payload(
        active_payload,
        source_mcb,
        split_details,
        preview['recommended_breaker_rating'],
    )

    boq_overrides = {
        'mcb_total': _graph_component_count(edited_payload, ['MCB']),
        'junction_box_total': _graph_component_count(edited_payload, ['JB3PH', 'JB1PH']),
    }

    topology_operations, topology_chain_audit = _topology_operation_chain(project, 'split_circuits', preview, {
        'component_ids': preview['selected_component_ids'],
    }, generated_payload=generated_payload)
    edit_payload, validation_summary = _finalize_edit_payload(
        edited_payload,
        topology_operations,
        preview,
        preview_key='split_preview',
        boq_overrides=boq_overrides,
        topology_chain_audit=topology_chain_audit,
    )
    if edit_payload is None:
        return {
            'ok': False,
            'error': 'Topology edit failed structural validation.',
            'validation_summary': validation_summary,
        }
    SLDTopologyEdit.objects.filter(project=project, status='applied').update(status='superseded')
    edit = SLDTopologyEdit.objects.create(
        project=project,
        edit_type='split_circuits',
        status='applied',
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        remarks=remarks or '',
        baseline_fingerprint=payload_fingerprint(generated_payload),
        generated_snapshot=generated_payload,
        edit_payload=edit_payload,
        validation_summary=validation_summary,
    )
    return {
        'ok': True,
        'edit_id': edit.id,
        'preview': preview,
        'validation_summary': edit.validation_summary,
    }


@transaction.atomic
def apply_scoped_reset(project_id, component_id, user=None, remarks=''):
    project = _lock_project_for_topology_apply(project_id)
    generated_payload = build_project_sld_payload(project_id, apply_topology=False)
    active_payload = build_project_sld_payload(project_id)
    if not active_payload.get('meta', {}).get('has_topology_edit'):
        return {
            'ok': False,
            'error': 'There is no active manual topology edit to reset selectively.',
        }

    reset_scope, error = _selected_reset_scope(active_payload, component_id)
    if not reset_scope:
        return {
            'ok': False,
            'error': error or 'Selected feeder tree could not be resolved for reset.',
        }
    edited_payload = _build_scoped_reset_payload(active_payload, generated_payload, reset_scope)
    if not edited_payload:
        return {
            'ok': False,
            'error': 'Generated topology for the selected feeder tree could not be resolved.',
        }

    preview = {
        'ok': True,
        'project_id': project_id,
        'edit_type': 'scoped_reset',
        'selected_component_id': component_id,
        'source_mcb_component_id': reset_scope['source_mcb']['component_id'],
        'source_mcb_display_tag': reset_scope['source_mcb'].get('display_tag'),
        'reset_line_ids': sorted(reset_scope['line_ids']),
        'reset_component_count': len(reset_scope['tree_component_ids']),
        'warning': 'Selected feeder tree reset to generated topology. Other manual topology edits remain active.',
    }
    boq_overrides = {
        'mcb_total': _graph_component_count(edited_payload, ['MCB']),
        'junction_box_total': _graph_component_count(edited_payload, ['JB3PH', 'JB1PH']),
    }

    topology_operations, topology_chain_audit = _topology_operation_chain(project, 'scoped_reset', preview, {
        'component_id': component_id,
        'source_mcb_component_id': preview['source_mcb_component_id'],
        'reset_line_ids': preview['reset_line_ids'],
    }, generated_payload=generated_payload)
    edit_payload, validation_summary = _finalize_edit_payload(
        edited_payload,
        topology_operations,
        preview,
        preview_key='scoped_reset_preview',
        boq_overrides=boq_overrides,
        topology_chain_audit=topology_chain_audit,
    )
    if edit_payload is None:
        return {
            'ok': False,
            'error': 'Topology edit failed structural validation.',
            'validation_summary': validation_summary,
        }
    SLDTopologyEdit.objects.filter(project=project, status='applied').update(status='superseded')
    edit = SLDTopologyEdit.objects.create(
        project=project,
        edit_type='scoped_reset',
        status='applied',
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        remarks=remarks or '',
        baseline_fingerprint=payload_fingerprint(generated_payload),
        generated_snapshot=generated_payload,
        edit_payload=edit_payload,
        validation_summary=validation_summary,
    )
    return {
        'ok': True,
        'edit_id': edit.id,
        'preview': preview,
        'validation_summary': edit.validation_summary,
    }
