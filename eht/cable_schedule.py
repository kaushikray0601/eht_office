from math import ceil

from .sld_payload import build_project_sld_payload


CABLE_COMPONENT_TYPES = {'Cable3C', 'Cable4C'}
CABLE_ROLE_LABELS = {
    'MCB_TO_JB3PH': 'MCB to first 3PhJB',
    'JB3PH_TO_JB3PH': '3PhJB to downstream 3PhJB',
}
CABLE_SCHEDULE_EXPORT_HEADERS = [
    'Sr. No',
    'Cable Tag',
    'Cable Specification',
    'Cable Length (m)',
    'Connected From',
    'Connected To',
    'Line IDs',
    'Purpose',
    'Cable Drum Tag',
    'Cable Route Details',
    'Remarks',
    'Rev. No.',
]


def _to_float(value):
    if value in (None, ''):
        return 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _node_lookup(payload):
    return {
        node.get('component_id'): node
        for node in payload.get('nodes', [])
        if node.get('component_id')
    }


def _edge_lookup(payload):
    incoming = {}
    outgoing = {}
    for edge in payload.get('edges', []):
        incoming.setdefault(edge.get('to_component_id'), []).append(edge)
        outgoing.setdefault(edge.get('from_component_id'), []).append(edge)
    return incoming, outgoing


def _display_tag(node):
    return (node or {}).get('display_tag') or (node or {}).get('component_id') or ''


def _connected_tags(edges, node_by_id, endpoint_key):
    tags = [
        _display_tag(node_by_id.get(edge.get(endpoint_key)))
        for edge in edges
    ]
    return ', '.join(tag for tag in tags if tag)


def _metadata(node):
    return (node or {}).get('metadata') or {}


def _cable_specification(node):
    metadata = _metadata(node)
    return (
        metadata.get('manual_cable_size')
        or metadata.get('cable_size')
        or metadata.get('generated_cable_size')
        or node.get('display_name')
        or ''
    )


def _cable_length_m(node):
    metadata = _metadata(node)
    return _to_float(
        metadata.get('manual_length_m')
        or metadata.get('length_m')
        or metadata.get('generated_length_m')
    )


def _line_ids(node):
    line_ids = node.get('line_ids') or ([node.get('line_id')] if node.get('line_id') else [])
    return ', '.join(line_id for line_id in line_ids if line_id)


def _purpose(node, incoming_edges, outgoing_edges, node_by_id):
    metadata = _metadata(node)
    role = metadata.get('cable_role') or ''
    if role in CABLE_ROLE_LABELS:
        return CABLE_ROLE_LABELS[role]

    source_types = {
        (node_by_id.get(edge.get('from_component_id')) or {}).get('component_type')
        for edge in incoming_edges
    }
    target_types = {
        (node_by_id.get(edge.get('to_component_id')) or {}).get('component_type')
        for edge in outgoing_edges
    }
    component_type = node.get('component_type')
    if component_type == 'Cable3C':
        if 'JB3PH' in source_types:
            return '3PhJB to 1PhJB'
        if 'MCB' in source_types:
            return 'MCB to 1PhJB'
        return '1Ph branch cable'
    if component_type == 'Cable4C':
        if 'JB3PH' in source_types:
            return '3PhJB to downstream 3PhJB'
        if 'MCB' in source_types or {'Isolator3PH', 'JB3PH'} & target_types:
            return 'MCB to first 3PhJB'
        return '3Ph trunk cable'
    return ''


def _cable_schedule_rows(payload):
    node_by_id = _node_lookup(payload)
    incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    cable_nodes = sorted(
        [
            node for node in payload.get('nodes', [])
            if node.get('component_type') in CABLE_COMPONENT_TYPES
        ],
        key=lambda node: (
            _line_ids(node),
            node.get('branch_index') or 0,
            -1 if node.get('circuit_index') is None else node.get('circuit_index'),
            node.get('component_type') or '',
            _display_tag(node),
        ),
    )

    rows = []
    for index, node in enumerate(cable_nodes, start=1):
        component_id = node.get('component_id')
        incoming_edges = incoming_by_id.get(component_id, [])
        outgoing_edges = outgoing_by_id.get(component_id, [])
        metadata = _metadata(node)
        rows.append({
            'sr_no': index,
            'cable_tag': _display_tag(node),
            'cable_specification': _cable_specification(node),
            'cable_length_m': _cable_length_m(node),
            'connected_from': _connected_tags(incoming_edges, node_by_id, 'from_component_id'),
            'connected_to': _connected_tags(outgoing_edges, node_by_id, 'to_component_id'),
            'line_ids': _line_ids(node),
            'purpose': _purpose(node, incoming_edges, outgoing_edges, node_by_id),
            'cable_drum_tag': '',
            'cable_route_details': '',
            'remarks': '',
            'revision_no': '0',
            'manual_override_active': bool(metadata.get('cable_override_active')),
        })
    return rows


def build_cable_schedule_workspace_data(project_id):
    sld_payload = build_project_sld_payload(project_id)
    sld_meta = sld_payload.get('meta') or {}
    allow_topology_overrides = not sld_meta.get('topology_edit_review_required')
    cable_rows = _cable_schedule_rows(sld_payload)

    total_cable_length_m = sum(row['cable_length_m'] for row in cable_rows)
    summary = {
        'row_count': len(cable_rows),
        'source_label': 'Manual SLD topology' if sld_meta.get('has_topology_edit') and allow_topology_overrides else 'Generated calculation',
        'has_topology_edit': bool(sld_meta.get('has_topology_edit')),
        'topology_baseline_changed': bool(sld_meta.get('topology_baseline_changed')),
        'manual_topology_warning': sld_meta.get('manual_topology_warning') or '',
        'total_cable_length_m': total_cable_length_m,
        'total_cable_length_display': f'{ceil(total_cable_length_m):,}',
        'override_count': sum(1 for row in cable_rows if row['manual_override_active']),
    }
    return {
        'cable_rows': cable_rows,
        'summary': summary,
    }


def cable_schedule_export_rows(cable_rows):
    """Map internal schedule rows to the engineering-facing Excel columns."""
    return [
        {
            'Sr. No': row.get('sr_no', ''),
            'Cable Tag': row.get('cable_tag', ''),
            'Cable Specification': row.get('cable_specification', ''),
            'Cable Length (m)': row.get('cable_length_m', ''),
            'Connected From': row.get('connected_from', ''),
            'Connected To': row.get('connected_to', ''),
            'Line IDs': row.get('line_ids', ''),
            'Purpose': row.get('purpose', ''),
            'Cable Drum Tag': row.get('cable_drum_tag', ''),
            'Cable Route Details': row.get('cable_route_details', ''),
            'Remarks': row.get('remarks', ''),
            'Rev. No.': row.get('revision_no', ''),
        }
        for row in cable_rows
    ]
