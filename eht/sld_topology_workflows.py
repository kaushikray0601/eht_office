from copy import deepcopy
import hashlib

from django.db import transaction

from .models import BOQ, MAX_CB_SIZE, ProjectData, SLDTopologyEdit
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
    selected.sort(key=lambda node: (
        str(node.get('line_id') or ''),
        str(node.get('line_uid') or ''),
        node.get('branch_index') or 0,
        str(node.get('display_tag') or ''),
    ))
    return selected, invalid_ids


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


def _find_upstream_mcb(node_id, node_by_id, incoming_by_id):
    visited = set()
    cursor = node_id
    while cursor and cursor not in visited:
        visited.add(cursor)
        node = node_by_id.get(cursor)
        if node and node.get('component_type') == 'MCB':
            return node
        incoming_edges = incoming_by_id.get(cursor) or []
        cursor = incoming_edges[0].get('from_component_id') if incoming_edges else None
    return None


def _boq_mcb_total(project_id):
    item = BOQ.objects.filter(project_id=project_id, scope='consolidated', item_code='MCB').first()
    return item.quantity if item else 0


def _boq_junction_box_total(project_id):
    items = BOQ.objects.filter(
        project_id=project_id,
        scope='consolidated',
        item_code__in=['JB3PH', 'JB1PH'],
    )
    return sum(item.quantity for item in items)


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


def _build_edited_payload(payload, selected_nodes, recommended_rating):
    primary = selected_nodes[0]
    secondary_ids = {node['component_id'] for node in selected_nodes[1:]}
    selected_ids = {node['component_id'] for node in selected_nodes}
    primary_id = primary['component_id']
    edited = deepcopy(payload)
    _, outgoing_by_id = _edge_lookup(edited)

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
        node['display_tag'] = f"{node.get('display_tag', 'MCB')}-M"
        node['label'] = node['display_tag']

    feeder_entry_ids = []
    for selected_node in selected_nodes:
        for edge in outgoing_by_id.get(selected_node['component_id'], []):
            entry_id = edge.get('to_component_id')
            if entry_id and entry_id not in selected_ids:
                feeder_entry_ids.append(entry_id)
    feeder_entry_ids = sorted(set(feeder_entry_ids))

    primary_tag = primary.get('display_tag', 'MCB')
    tag_suffix = primary_tag.split('_', 1)[1] if '_' in primary_tag else primary_tag
    cable4c = _manual_combine_node(
        primary,
        'Cable4C',
        f"CCAB4C_{tag_suffix}-M",
        selected_nodes,
        recommended_rating,
    )
    jb3ph = _manual_combine_node(
        primary,
        'JB3PH',
        f"JB3PH_{tag_suffix}-M",
        selected_nodes,
        recommended_rating,
    )

    edited['nodes'] = [
        node for node in edited['nodes']
        if node['component_id'] not in secondary_ids
    ]
    edited['nodes'].extend([cable4c, jb3ph])

    rewired_edges = []
    for edge in edited['edges']:
        if edge.get('to_component_id') in secondary_ids:
            continue
        if edge.get('from_component_id') in selected_ids:
            continue
        rewired_edges.append(dict(edge))

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


def _selected_circuit_groups(payload, component_ids):
    node_by_id = _node_lookup(payload)
    selected_nodes = []
    invalid_ids = []
    for component_id in component_ids:
        node = node_by_id.get(component_id)
        if node is None or node.get('component_type') == 'MCB' or node.get('circuit_index') is None:
            invalid_ids.append(component_id)
        else:
            selected_nodes.append(node)

    groups = {}
    for node in selected_nodes:
        key = (node.get('line_uid'), node.get('branch_index'), node.get('circuit_index'))
        groups.setdefault(key, node)
    circuits = list(groups.values())
    circuits.sort(key=lambda node: (
        str(node.get('line_id') or ''),
        str(node.get('line_uid') or ''),
        node.get('branch_index') or 0,
        node.get('circuit_index') or 0,
        str(node.get('component_id') or ''),
    ))
    return circuits, invalid_ids


def _branch_circuit_count(payload, circuit_node):
    line_uid = circuit_node.get('line_uid')
    branch_index = circuit_node.get('branch_index')
    circuit_indices = {
        node.get('circuit_index')
        for node in payload.get('nodes', [])
        if (
            node.get('line_uid') == line_uid
            and node.get('branch_index') == branch_index
            and node.get('circuit_index') is not None
        )
    }
    return len(circuit_indices) or 1


def _new_split_mcb_node(source_mcb, selected_circuits, recommended_rating):
    first = selected_circuits[0]
    circuit_scope = '-'.join(str(node.get('circuit_index')) for node in selected_circuits)
    component_id = (
        f"{source_mcb['component_id']}:manual_split:"
        f"{first.get('line_uid')}:{first.get('branch_index')}:{circuit_scope}"
    )
    display_tag = f"{source_mcb.get('display_tag', 'MCB')}-S"
    return {
        'component_id': component_id,
        'component_uid': _component_uid(component_id),
        'display_tag': display_tag,
        'component_type': 'MCB',
        'display_name': 'MCB',
        'label': display_tag,
        'line_id': first.get('line_id'),
        'line_ids': first.get('line_ids') or ([first.get('line_id')] if first.get('line_id') else []),
        'line_uid': first.get('line_uid'),
        'branch_index': first.get('branch_index'),
        'circuit_index': None,
        'metadata': {
            'breaker_size': recommended_rating,
            'manual_topology_edit': 'split_circuits',
            'source_mcb': source_mcb.get('display_tag'),
            'split_circuit_count': len(selected_circuits),
        },
    }


def _build_split_payload(payload, selected_circuits, source_mcb, recommended_rating):
    edited = deepcopy(payload)
    incoming_by_id, _outgoing_by_id = _edge_lookup(edited)
    circuit_keys = {
        (node.get('line_uid'), node.get('branch_index'), node.get('circuit_index'))
        for node in selected_circuits
    }
    circuit_component_ids = {key: set() for key in circuit_keys}
    for node in edited['nodes']:
        key = (node.get('line_uid'), node.get('branch_index'), node.get('circuit_index'))
        if key in circuit_component_ids:
            circuit_component_ids[key].add(node['component_id'])

    selected_entry_ids = set()
    for node in edited['nodes']:
        key = (node.get('line_uid'), node.get('branch_index'), node.get('circuit_index'))
        if key not in circuit_component_ids:
            continue
        upstream_ids = {
            edge.get('from_component_id')
            for edge in incoming_by_id.get(node['component_id'], [])
        }
        if any(upstream_id not in circuit_component_ids[key] for upstream_id in upstream_ids):
            selected_entry_ids.add(node['component_id'])

    if not selected_entry_ids:
        selected_entry_ids = {node['component_id'] for node in selected_circuits}

    split_mcb = _new_split_mcb_node(source_mcb, selected_circuits, recommended_rating)
    edited['nodes'].append(split_mcb)

    rewired_edges = []
    for edge in edited['edges']:
        if edge.get('to_component_id') in selected_entry_ids:
            continue
        rewired_edges.append(edge)
    for entry_id in sorted(selected_entry_ids):
        entry_node = next(node for node in edited['nodes'] if node['component_id'] == entry_id)
        rewired_edges.append({
            'from_component_id': split_mcb['component_id'],
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
        'split_circuit_count': len(selected_circuits),
        'manual_topology_warning': (
            'Graph-level circuit split applied. Detailed cable/JB materialization remains subject to later cable sizing and split/combine domain rules.'
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
    if get_active_topology_edit(project_id):
        return {
            'ok': False,
            'error': 'Reset or supersede the active topology edit before applying another combine operation.',
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
    primary_tag = primary.get('display_tag', 'MCB')
    tag_suffix = primary_tag.split('_', 1)[1] if '_' in primary_tag else primary_tag
    return {
        'ok': True,
        'project_id': project_id,
        'edit_type': 'combine_feeders',
        'selected_component_ids': [node['component_id'] for node in selected_nodes],
        'primary_component_id': primary['component_id'],
        'primary_display_tag': primary['display_tag'],
        'updated_display_tags': [f"{primary['display_tag']}-M"],
        'removed_component_ids': [node['component_id'] for node in removed_nodes],
        'removed_display_tags': [node['display_tag'] for node in removed_nodes],
        'added_component_types': ['Cable4C', 'JB3PH'],
        'added_display_tags': [f"CCAB4C_{tag_suffix}-M", f"JB3PH_{tag_suffix}-M"],
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
            'error': 'Select at least one downstream circuit component to split.',
        }
    if get_active_topology_edit(project_id):
        return {
            'ok': False,
            'error': 'Reset or supersede the active topology edit before applying another split operation.',
        }

    payload = build_project_sld_payload(project_id)
    node_by_id = _node_lookup(payload)
    incoming_by_id, _outgoing_by_id = _edge_lookup(payload)
    selected_circuits, invalid_ids = _selected_circuit_groups(payload, component_ids)
    if invalid_ids:
        return {
            'ok': False,
            'error': 'One or more selected components are not downstream circuit components.',
            'invalid_component_ids': invalid_ids,
        }
    if not selected_circuits:
        return {
            'ok': False,
            'error': 'Select at least one downstream circuit component to split.',
        }

    source_mcbs = {
        _find_upstream_mcb(node['component_id'], node_by_id, incoming_by_id)['component_id']:
        _find_upstream_mcb(node['component_id'], node_by_id, incoming_by_id)
        for node in selected_circuits
        if _find_upstream_mcb(node['component_id'], node_by_id, incoming_by_id)
    }
    if len(source_mcbs) != 1:
        return {
            'ok': False,
            'error': 'Selected circuits must share one upstream MCB for this first split workflow.',
        }

    source_mcb = next(iter(source_mcbs.values()))
    source_rating = float((source_mcb.get('metadata') or {}).get('breaker_size') or 0)
    branch_circuit_count = _branch_circuit_count(payload, selected_circuits[0])
    proportional_rating = source_rating * len(selected_circuits) / max(branch_circuit_count, 1)
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
        'selected_component_ids': [node['component_id'] for node in selected_circuits],
        'source_mcb_component_id': source_mcb['component_id'],
        'source_mcb_display_tag': source_mcb['display_tag'],
        'added_display_tags': [f"{source_mcb.get('display_tag', 'MCB')}-S"],
        'selected_circuit_count': len(selected_circuits),
        'source_breaker_rating': source_rating,
        'recommended_breaker_rating': recommended_rating,
        'affected_lines': sorted({node.get('line_id') for node in selected_circuits if node.get('line_id')}),
        'affected_branch_count': len({
            (node.get('line_uid'), node.get('branch_index'))
            for node in selected_circuits
        }),
        'warning': (
            'This first workflow applies a controlled graph-level circuit split and marks the new MCB for review.'
        ),
    }


@transaction.atomic
def apply_combine_feeders(project_id, component_ids, user=None, remarks=''):
    project = ProjectData.objects.get(proj_id=project_id)
    preview = preview_combine_feeders(project_id, component_ids)
    if not preview['ok']:
        return preview

    generated_payload = build_project_sld_payload(project_id)
    selected_nodes, _invalid_ids = _selected_mcb_nodes(generated_payload, preview['selected_component_ids'])
    edited_payload = _build_edited_payload(
        generated_payload,
        selected_nodes,
        preview['recommended_breaker_rating'],
    )

    current_mcb_total = _boq_mcb_total(project_id)
    current_junction_box_total = _boq_junction_box_total(project_id)
    removed_count = len(preview['removed_component_ids'])
    boq_overrides = {
        'mcb_total': max(current_mcb_total - removed_count, 0),
        'junction_box_total': current_junction_box_total + 1,
    }

    SLDTopologyEdit.objects.filter(project=project, status='applied').update(status='superseded')
    edit = SLDTopologyEdit.objects.create(
        project=project,
        edit_type='combine_feeders',
        status='applied',
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        remarks=remarks or '',
        baseline_fingerprint=payload_fingerprint(generated_payload),
        generated_snapshot=generated_payload,
        edit_payload={
            'sld_payload': edited_payload,
            'combine_preview': preview,
            'downstream_summaries': {
                'boq': boq_overrides,
            },
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

    generated_payload = build_project_sld_payload(project_id)
    node_by_id = _node_lookup(generated_payload)
    incoming_by_id, _outgoing_by_id = _edge_lookup(generated_payload)
    selected_circuits, _invalid_ids = _selected_circuit_groups(
        generated_payload,
        preview['selected_component_ids'],
    )
    source_mcb = _find_upstream_mcb(selected_circuits[0]['component_id'], node_by_id, incoming_by_id)
    edited_payload = _build_split_payload(
        generated_payload,
        selected_circuits,
        source_mcb,
        preview['recommended_breaker_rating'],
    )

    current_mcb_total = _boq_mcb_total(project_id)
    boq_overrides = {
        'mcb_total': current_mcb_total + 1,
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
            },
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
