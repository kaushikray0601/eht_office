from copy import deepcopy
import hashlib

from django.db import transaction

from .models import MAX_CB_SIZE, ProjectData, SLDTopologyEdit
from .sld_payload import build_project_sld_payload
from .sld_topology import get_active_topology_edit, payload_fingerprint


def _next_breaker_size(total_rating):
    ratings = [value for value, _label in MAX_CB_SIZE]
    return next((rating for rating in ratings if rating >= total_rating), None)


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


def _to_positive_float(value, default=None):
    if value in (None, ''):
        value = default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


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
        rows.append({
            'distribution': {'line': {'line_id': ', '.join(line_ids) or mcb.get('line_id') or ''}},
            'branch_index': branch_index,
            'branch_type': 'manual_topology_edit',
            'connected_to': ', '.join(node.get('display_tag', '') for node in tracer_nodes) or 'Manual topology path',
            'circuit_count': max(1, len(tracer_nodes)),
            'cable_length_db_to_jb': sum(float((node.get('metadata') or {}).get('length_m') or 0) for node in cable_nodes),
            'cable_length_jb_to_jb': None,
            'tagged_components': {
                'MCB': mcb.get('display_tag'),
                'Cables': [node.get('display_tag') for node in cable_nodes],
                'Downstream': [{'Tracer': node.get('display_tag')} for node in tracer_nodes],
            },
        })
    return rows


def _manual_combine_node(source_mcb, component_type, display_tag, selected_nodes, recommended_rating):
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
    if component_type == 'Cable4C':
        metadata.update({
            'cable_role': 'MCB_TO_JB3PH',
            'note': 'Manual feeder-combine trunk cable. Cable sizing is pending detailed cable design.',
        })
    if component_type == 'JB3PH':
        metadata.update({
            'circuit_count': len(selected_nodes),
            'source_mcb': source_mcb.get('display_tag'),
            'recommended_breaker_rating': recommended_rating,
        })

    return {
        'component_id': component_id,
        'component_uid': _component_uid(component_id),
        'display_tag': display_tag,
        'component_type': component_type,
        'display_name': '4C Cable' if component_type == 'Cable4C' else '3PH JB',
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
            jb = node_by_id.get(cable_edge.get('to_component_id'))
            if (
                jb
                and jb.get('component_type') == 'JB3PH'
                and (jb.get('metadata') or {}).get('manual_topology_edit') == 'combine_feeders'
            ):
                return cable, jb
    return None, None


def _build_edited_payload(payload, selected_nodes, recommended_rating):
    primary = selected_nodes[0]
    secondary_ids = {node['component_id'] for node in selected_nodes[1:]}
    selected_ids = {node['component_id'] for node in selected_nodes}
    primary_id = primary['component_id']
    edited = deepcopy(payload)
    _, outgoing_by_id = _edge_lookup(edited)
    existing_cable4c, existing_jb3ph = _manual_combine_distribution(edited, primary)

    for node in edited['nodes']:
        if node['component_id'] != primary_id:
            continue
        metadata = dict(node.get('metadata') or {})
        metadata.update({
            'breaker_size': recommended_rating,
            'manual_topology_edit': 'combine_feeders',
            'combined_feeder_count': len(selected_nodes),
        })
        node['metadata'] = metadata
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
        primary, 'Cable4C', f"CCAB4C_{tag_suffix}-M", selected_nodes, recommended_rating
    )
    jb3ph = existing_jb3ph or _manual_combine_node(
        primary, 'JB3PH', f"JB3PH_{tag_suffix}-M", selected_nodes, recommended_rating
    )

    edited['nodes'] = [
        node for node in edited['nodes']
        if node['component_id'] not in secondary_ids
    ]
    existing_manual_ids = {node['component_id'] for node in edited['nodes']}
    if cable4c['component_id'] not in existing_manual_ids:
        edited['nodes'].append(cable4c)
        existing_manual_ids.add(cable4c['component_id'])
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
        rewired_edges.append(dict(edge))

    if not existing_jb3ph:
        rewired_edges.extend([
            {
                'from_component_id': primary_id,
                'to_component_id': cable4c['component_id'],
                'line_ids': cable4c['line_ids'],
                'line_uid': cable4c.get('line_uid'),
                'branch_index': cable4c.get('branch_index'),
                'circuit_index': None,
            },
            {
                'from_component_id': cable4c['component_id'],
                'to_component_id': jb3ph['component_id'],
                'line_ids': cable4c['line_ids'],
                'line_uid': cable4c.get('line_uid'),
                'branch_index': cable4c.get('branch_index'),
                'circuit_index': None,
            },
        ])
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

    meta = dict(edited.get('meta') or {})
    meta.update({
        'node_count': len(edited['nodes']),
        'edge_count': len(edited['edges']),
        'combine_feeder_count': len(selected_nodes),
        'manual_topology_warning': (
            'Manual feeder combine applied with a 4C trunk cable and 3PH junction box before the original outgoing feeder cables. Detailed cable sizing remains subject to later cable design rules.'
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


def _split_part_identity(entry_node, index):
    original_line_id = entry_node.get('line_id') or 'LINE'
    original_line_uid = entry_node.get('line_uid') or original_line_id
    return {
        'line_id': f"{original_line_id}-part{index}",
        'line_uid': f"{original_line_uid}:manual_split:part{index}",
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
    part_identity_by_key = {
        _split_circuit_key(entry): _split_part_identity(entry, index)
        for index, entry in enumerate(entry_nodes, start=1)
    }
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
        identity['original_line_uid']
        for identity in part_identity_by_key.values()
    }
    edited['line_groups'] = [
        group for group in edited.get('line_groups', [])
        if str(group.get('line_uid')) not in split_group_uids
    ]
    for entry in entry_nodes:
        identity = part_identity_by_key[_split_circuit_key(entry)]
        edited['line_groups'].append({
            'line_id': identity['line_id'],
            'line_uid': identity['line_uid'],
            'original_line_id': identity['original_line_id'],
            'original_line_uid': identity['original_line_uid'],
            'branch_indices': [entry.get('branch_index')],
        })

    meta = dict(edited.get('meta') or {})
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


def _downstream_jb_manual_node(parent_jb, component_type, display_tag, selected_nodes, trunk_length_m):
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
            'cable_size': '4C',
            'generated_cable_size': '4C',
            'note': 'Manual downstream 3PH JB trunk cable.',
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
        'display_name': '4C Cable' if component_type == 'Cable4C' else '3PH JB',
        'label': display_tag,
        'line_id': parent_jb.get('line_id'),
        'line_ids': line_ids,
        'line_uid': parent_jb.get('line_uid'),
        'branch_index': parent_jb.get('branch_index'),
        'circuit_index': None,
        'metadata': metadata,
    }


def _downstream_jb_preview_tags(payload, parent_jb):
    existing_tags = {node.get('display_tag') for node in payload.get('nodes', [])}
    base_suffix = _display_tag_suffix(parent_jb.get('display_tag', 'JB3PH'))
    cable_tag = _unique_manual_tag(existing_tags, 'CCAB4C', base_suffix)
    jb_tag = _unique_manual_tag(existing_tags | {cable_tag}, 'JB3PH', base_suffix)
    return cable_tag, jb_tag


def _build_downstream_jb_payload(payload, details, trunk_length_m):
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
    cable_tag, jb_tag = _downstream_jb_preview_tags(edited, parent)
    cable4c = _downstream_jb_manual_node(parent, 'Cable4C', cable_tag, selected_nodes, trunk_length_m)
    jb3ph = _downstream_jb_manual_node(parent, 'JB3PH', jb_tag, selected_nodes, trunk_length_m)
    edited['nodes'].extend([cable4c, jb3ph])

    rewired_edges = []
    for edge in edited['edges']:
        if (
            edge.get('from_component_id') == parent['component_id']
            and edge.get('to_component_id') in selected_target_ids
        ):
            continue
        rewired_edges.append(dict(edge))

    rewired_edges.extend([
        {
            'from_component_id': parent['component_id'],
            'to_component_id': cable4c['component_id'],
            'line_ids': cable4c['line_ids'],
            'line_uid': cable4c.get('line_uid'),
            'branch_index': cable4c.get('branch_index'),
            'circuit_index': None,
        },
        {
            'from_component_id': cable4c['component_id'],
            'to_component_id': jb3ph['component_id'],
            'line_ids': cable4c['line_ids'],
            'line_uid': cable4c.get('line_uid'),
            'branch_index': cable4c.get('branch_index'),
            'circuit_index': None,
        },
    ])
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
    meta = dict(edited.get('meta') or {})
    meta.update({
        'node_count': len(edited['nodes']),
        'edge_count': len(edited['edges']),
        'manual_topology_warning': (
            'Manual downstream 3PH junction box inserted to keep 3PH JB outgoing feeders within the configured engineering limit. Review the new trunk cable length and downstream cable schedule before issue.'
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


def _selected_branch_move_details(payload, source_component_id, target_jb_component_id):
    node_by_id = _node_lookup(payload)
    incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    selected_node = node_by_id.get(source_component_id)
    target_jb = node_by_id.get(target_jb_component_id)
    if not selected_node:
        return None, 'Select the branch or circuit component to move.'
    if selected_node.get('component_type') in {'MCB', 'JB3PH'}:
        return None, 'Select a downstream branch component such as a cable, 1PH JB, tracer, or end termination.'
    if not target_jb or target_jb.get('component_type') != 'JB3PH':
        return None, 'Select the target 3PH JB that should feed the selected branch.'

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
    if source_parent_jb['component_id'] == target_jb['component_id']:
        return None, 'Selected branch is already fed from the target 3PH JB.'
    if target_jb['component_id'] in _descendant_component_ids(payload, branch_root['component_id']):
        return None, 'Target 3PH JB cannot be downstream of the selected branch.'

    source_mcb = _upstream_mcb_node(payload, source_parent_jb['component_id'])
    target_mcb = _upstream_mcb_node(payload, target_jb['component_id'])
    if not source_mcb or not target_mcb:
        return None, 'Both source and target 3PH JBs must have upstream MCB sources.'
    if source_mcb['component_id'] != target_mcb['component_id']:
        return None, 'Moving branches between different upstream MCBs needs a breaker rebalancing pass and is not enabled yet.'

    source_outgoing_edges = [
        edge for edge in outgoing_by_id.get(source_parent_jb['component_id'], [])
        if edge.get('to_component_id') in node_by_id
    ]
    target_outgoing_edges = [
        edge for edge in outgoing_by_id.get(target_jb['component_id'], [])
        if edge.get('to_component_id') in node_by_id
    ]
    target_after_count = len(target_outgoing_edges) + 1
    if target_after_count > 3:
        return None, f"Target 3PH JB would have {target_after_count} outgoing feeders. Limit is 3 in this pass."

    return {
        'selected_node': selected_node,
        'source_parent_jb': source_parent_jb,
        'target_jb': target_jb,
        'branch_root': branch_root,
        'upstream_mcb': source_mcb,
        'source_outgoing_before': len(source_outgoing_edges),
        'source_outgoing_after': max(0, len(source_outgoing_edges) - 1),
        'target_outgoing_before': len(target_outgoing_edges),
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
        elif node.get('component_id') == target_id:
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

    meta = dict(edited.get('meta') or {})
    meta.update({
        'node_count': len(edited['nodes']),
        'edge_count': len(edited['edges']),
        'manual_topology_warning': (
            'Manual feeder reattachment applied: the selected MCB-fed circuit is now fed from a selected 3PH JB. Breaker rating and cable sizing remain review-required engineering data.'
        ),
    })
    edited['meta'] = meta
    return edited


def _build_branch_move_payload(payload, details):
    edited = deepcopy(payload)
    source_parent_id = details['source_parent_jb']['component_id']
    target_jb = details['target_jb']
    target_id = target_jb['component_id']
    branch_root = details['branch_root']
    branch_root_id = branch_root['component_id']

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
        elif node.get('component_id') == target_id:
            metadata = dict(node.get('metadata') or {})
            metadata.update({
                'move_branch_to_jb_review_required': True,
                'moved_branch_in': branch_root.get('display_tag'),
            })
            node['metadata'] = metadata
        elif node.get('component_id') == branch_root_id:
            metadata = dict(node.get('metadata') or {})
            metadata.update({
                'manual_topology_edit': metadata.get('manual_topology_edit') or 'move_branch_to_jb',
                'moved_from_jb': details['source_parent_jb'].get('display_tag'),
                'moved_to_jb': target_jb.get('display_tag'),
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
        rewired_edges.append(dict(edge))

    rewired_edges.append({
        'from_component_id': target_id,
        'to_component_id': branch_root_id,
        'line_ids': branch_root.get('line_ids', []),
        'line_uid': branch_root.get('line_uid'),
        'branch_index': branch_root.get('branch_index'),
        'circuit_index': branch_root.get('circuit_index'),
    })
    edited['edges'] = _dedupe_edges(rewired_edges)

    meta = dict(edited.get('meta') or {})
    meta.update({
        'node_count': len(edited['nodes']),
        'edge_count': len(edited['edges']),
        'manual_topology_warning': (
            'Manual branch move applied: the selected downstream branch is now fed from a different 3PH JB within the same upstream MCB feeder tree. Review cable routing and schedule before issue.'
        ),
    })
    edited['meta'] = meta
    return edited


def preview_combine_feeders(project_id, component_ids):
    component_ids = [component_id for component_id in (component_ids or []) if component_id]
    if len(component_ids) < 2:
        return {
            'ok': False,
            'error': 'Select at least two MCB feeder sources to combine.',
        }
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

    ratings = [
        float((node.get('metadata') or {}).get('breaker_size') or 0)
        for node in selected_nodes
    ]
    total_rating = sum(ratings)
    recommended_rating = _next_breaker_size(total_rating)
    if recommended_rating is None:
        return {
            'ok': False,
            'error': f"Combined feeder rating {total_rating:g}A exceeds the largest configured breaker size.",
        }

    primary = selected_nodes[0]
    removed_nodes = selected_nodes[1:]
    existing_cable4c, existing_jb3ph = _manual_combine_distribution(payload, primary)
    primary_tag = _manual_display_tag(primary.get('display_tag', 'MCB'))
    tag_suffix = primary_tag.split('_', 1)[1] if '_' in primary_tag else primary_tag
    added_component_types = [] if existing_jb3ph else ['Cable4C', 'JB3PH']
    added_display_tags = [] if existing_jb3ph else [f"CCAB4C_{tag_suffix}-M", f"JB3PH_{tag_suffix}-M"]
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
        'combined_breaker_rating': total_rating,
        'recommended_breaker_rating': recommended_rating,
        'affected_lines': sorted({node.get('line_id') for node in selected_nodes if node.get('line_id')}),
        'affected_branch_count': len({
            (node.get('line_uid'), node.get('branch_index'))
            for node in selected_nodes
        }),
        'warning': (
            'This workflow combines feeders through a manual 4C trunk cable and 3PH junction box. Review cable sizing before issue.'
        ),
    }


def preview_split_circuits(project_id, component_ids):
    component_ids = [component_id for component_id in (component_ids or []) if component_id]
    if not component_ids:
        return {
            'ok': False,
            'error': 'Select one MCB feeder source with multiple downstream circuits to split.',
        }
    if get_active_topology_edit(project_id):
        return {
            'ok': False,
            'error': 'Reset or supersede the active topology edit before applying another split operation.',
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


def preview_downstream_jb(project_id, parent_component_id, branch_component_ids, trunk_length_m=None):
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
            'error': 'Select one upstream 3PH junction box.',
        }
    if details['invalid_ids']:
        return {
            'ok': False,
            'error': 'Selected outgoing branches must be directly fed from the selected 3PH junction box.',
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
    cable_tag, jb_tag = _downstream_jb_preview_tags(payload, details['parent'])
    return {
        'ok': True,
        'project_id': project_id,
        'edit_type': 'downstream_jb',
        'parent_component_id': details['parent']['component_id'],
        'parent_display_tag': details['parent']['display_tag'],
        'selected_component_ids': [node['component_id'] for node in selected_nodes],
        'selected_display_tags': [node['display_tag'] for node in selected_nodes],
        'added_component_types': ['Cable4C', 'JB3PH'],
        'added_display_tags': [cable_tag, jb_tag],
        'parent_outgoing_before': outgoing_count,
        'parent_outgoing_after': parent_after_count,
        'downstream_outgoing_count': selected_count,
        'trunk_length_m': trunk_length,
        'default_trunk_length_m': default_length,
        'affected_lines': sorted({
            line_id
            for node in selected_nodes
            for line_id in (node.get('line_ids') or ([node.get('line_id')] if node.get('line_id') else []))
            if line_id
        }),
        'warning': (
            'This workflow inserts a downstream 3PH junction box and moves selected outgoing branches under it. Confirm the new 4C trunk cable length before issue.'
        ),
    }


def preview_attach_to_jb(project_id, source_component_id, target_jb_component_id):
    payload = build_project_sld_payload(project_id)
    source_node = _node_lookup(payload).get(source_component_id)
    if source_node and source_node.get('component_type') != 'MCB':
        details, error = _selected_branch_move_details(payload, source_component_id, target_jb_component_id)
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
            'target_jb_component_id': details['target_jb']['component_id'],
            'target_jb_display_tag': details['target_jb']['display_tag'],
            'upstream_mcb_component_id': details['upstream_mcb']['component_id'],
            'upstream_mcb_display_tag': details['upstream_mcb']['display_tag'],
            'moved_component_ids': [branch_root['component_id']],
            'moved_display_tags': [branch_root['display_tag']],
            'source_outgoing_before': details['source_outgoing_before'],
            'source_outgoing_after': details['source_outgoing_after'],
            'target_outgoing_before': details['target_outgoing_before'],
            'target_outgoing_after': details['target_outgoing_after'],
            'affected_lines': affected_lines,
            'warning': (
                'This workflow moves one downstream branch between 3PH JBs under the same upstream MCB. Review cable routing before issue.'
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


@transaction.atomic
def apply_combine_feeders(project_id, component_ids, user=None, remarks=''):
    project = ProjectData.objects.get(proj_id=project_id)
    preview = preview_combine_feeders(project_id, component_ids)
    if not preview['ok']:
        return preview

    baseline_payload = build_project_sld_payload(project_id, apply_topology=False)
    active_payload = build_project_sld_payload(project_id)
    selected_nodes, _invalid_ids = _selected_mcb_nodes(active_payload, preview['selected_component_ids'])
    edited_payload = _build_edited_payload(
        active_payload,
        selected_nodes,
        preview['recommended_breaker_rating'],
    )

    boq_overrides = {
        'mcb_total': _graph_component_count(edited_payload, ['MCB']),
        'junction_box_total': _graph_component_count(edited_payload, ['JB3PH', 'JB1PH']),
    }

    SLDTopologyEdit.objects.filter(project=project, status='applied').update(status='superseded')
    edit = SLDTopologyEdit.objects.create(
        project=project,
        edit_type='combine_feeders',
        status='applied',
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        remarks=remarks or '',
        baseline_fingerprint=payload_fingerprint(baseline_payload),
        generated_snapshot=baseline_payload,
        edit_payload={
            'sld_payload': edited_payload,
            'combine_preview': preview,
            'downstream_summaries': {
                'boq': boq_overrides,
                'result': {'branch_count': _graph_component_count(edited_payload, ['MCB'])},
            },
            'cable_schedule_rows': _edited_cable_schedule_rows(edited_payload),
        },
        validation_summary={
            'status': 'needs_review',
            'warnings': [preview['warning']],
        },
    )
    return {
        'ok': True,
        'edit_id': edit.id,
        'preview': preview,
        'validation_summary': edit.validation_summary,
    }


@transaction.atomic
def apply_attach_to_jb(project_id, source_component_id, target_jb_component_id, user=None, remarks=''):
    project = ProjectData.objects.get(proj_id=project_id)
    preview = preview_attach_to_jb(project_id, source_component_id, target_jb_component_id)
    if not preview['ok']:
        return preview

    generated_payload = build_project_sld_payload(project_id, apply_topology=False)
    active_payload = build_project_sld_payload(project_id)
    if preview['edit_type'] == 'move_branch_to_jb':
        details, error = _selected_branch_move_details(
            active_payload,
            preview['source_component_id'],
            preview['target_jb_component_id'],
        )
        if not details:
            return {
                'ok': False,
                'error': error or 'Selected branch move topology could not be rebuilt safely.',
            }
        edited_payload = _build_branch_move_payload(active_payload, details)
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

    SLDTopologyEdit.objects.filter(project=project, status='applied').update(status='superseded')
    edit = SLDTopologyEdit.objects.create(
        project=project,
        edit_type=preview['edit_type'],
        status='applied',
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        remarks=remarks or '',
        baseline_fingerprint=payload_fingerprint(generated_payload),
        generated_snapshot=generated_payload,
        edit_payload={
            'sld_payload': edited_payload,
            edit_payload_key: preview,
            'downstream_summaries': {
                'boq': boq_overrides,
                'result': {'branch_count': _graph_component_count(edited_payload, ['MCB'])},
            },
            'cable_schedule_rows': _edited_cable_schedule_rows(edited_payload),
        },
        validation_summary={
            'status': 'needs_review',
            'warnings': [preview['warning']],
        },
    )
    return {
        'ok': True,
        'edit_id': edit.id,
        'preview': preview,
        'validation_summary': edit.validation_summary,
    }


@transaction.atomic
def apply_downstream_jb(project_id, parent_component_id, branch_component_ids, trunk_length_m=None, user=None, remarks=''):
    project = ProjectData.objects.get(proj_id=project_id)
    preview = preview_downstream_jb(project_id, parent_component_id, branch_component_ids, trunk_length_m)
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
    edited_payload = _build_downstream_jb_payload(active_payload, details, preview['trunk_length_m'])
    boq_overrides = {
        'mcb_total': _graph_component_count(edited_payload, ['MCB']),
        'junction_box_total': _graph_component_count(edited_payload, ['JB3PH', 'JB1PH']),
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
        edit_payload={
            'sld_payload': edited_payload,
            'downstream_jb_preview': preview,
            'downstream_summaries': {
                'boq': boq_overrides,
                'result': {'branch_count': _graph_component_count(edited_payload, ['MCB'])},
            },
            'cable_schedule_rows': _edited_cable_schedule_rows(edited_payload),
        },
        validation_summary={
            'status': 'needs_review',
            'warnings': [preview['warning']],
        },
    )
    return {
        'ok': True,
        'edit_id': edit.id,
        'preview': preview,
        'validation_summary': edit.validation_summary,
    }


@transaction.atomic
def apply_split_circuits(project_id, component_ids, user=None, remarks=''):
    project = ProjectData.objects.get(proj_id=project_id)
    preview = preview_split_circuits(project_id, component_ids)
    if not preview['ok']:
        return preview

    generated_payload = build_project_sld_payload(project_id, apply_topology=False)
    source_mcb, _invalid_ids = _selected_split_mcb(generated_payload, preview['selected_component_ids'])
    if source_mcb is None:
        return {
            'ok': False,
            'error': 'Selected MCB split topology could not be rebuilt safely.',
        }
    split_details = _split_source_details(generated_payload, source_mcb)
    if not split_details:
        return {
            'ok': False,
            'error': 'Selected MCB split topology could not be rebuilt safely.',
        }
    edited_payload = _build_split_payload(
        generated_payload,
        source_mcb,
        split_details,
        preview['recommended_breaker_rating'],
    )

    boq_overrides = {
        'mcb_total': _graph_component_count(edited_payload, ['MCB']),
        'junction_box_total': _graph_component_count(edited_payload, ['JB3PH', 'JB1PH']),
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
        edit_payload={
            'sld_payload': edited_payload,
            'split_preview': preview,
            'downstream_summaries': {
                'boq': boq_overrides,
                'result': {'branch_count': _graph_component_count(edited_payload, ['MCB'])},
            },
            'cable_schedule_rows': _edited_cable_schedule_rows(edited_payload),
        },
        validation_summary={
            'status': 'needs_review',
            'warnings': [preview['warning']],
        },
    )
    return {
        'ok': True,
        'edit_id': edit.id,
        'preview': preview,
        'validation_summary': edit.validation_summary,
    }
