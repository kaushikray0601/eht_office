from math import ceil

from .models import ColdCableResult
from .sld_payload import build_project_sld_payload


CABLE_COMPONENT_TYPES = {'Cable3C', 'Cable4C'}
CABLE_ROLE_LABELS = {
    'MCB_TO_JB3PH': 'MCB to Distribution JB',
    'JB3PH_TO_JB3PH': 'Distribution JB to downstream Distribution JB',
    'JB_TO_1PHJB': 'Distribution JB to Branch JB',
    'MCB_TO_1PHJB': 'MCB to Branch JB',
}
CABLE_SCHEDULE_EXPORT_HEADERS = [
    'Sr. No',
    'Cable Tag',
    'Cable Specification',
    'Calculated Cold Cable Size',
    'Cold Cable Segment Role',
    'Cold Cable Circuit Index',
    'Cold Cable Status',
    'Voltage Drop Status',
    'Fault Protection Status',
    'Total Path VD (%)',
    'Load-End Voltage (V)',
    'Fault Current (A)',
    'Length Basis',
    'Critical Branch Segment',
    'Conductor Mass (MT)',
    'Cable Length (m)',
    'Connected From',
    'Connected To',
    'Line IDs',
    'Purpose',
    'Cable Drum Tag',
    'Cable Route Details',
    'Remarks',
    'Manual Size Review',
    'Manual Size Review Note',
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


def _format_size(core_count, size_mm2):
    if size_mm2 in (None, ''):
        return ''
    return f'{core_count}C x {float(size_mm2):g} mm2'


def _cold_cable_result_for_node(node, cold_results):
    branch_index = node.get('branch_index') or 0
    line_uid = str(node.get('line_uid') or '')
    line_id = str(node.get('line_id') or '')
    return (
        cold_results.get((line_uid, branch_index))
        or cold_results.get((line_id, branch_index))
    )


def _cold_cable_fields(node, cold_results):
    metadata = _metadata(node)
    cold_cable = metadata.get('cold_cable') or {}
    component_type = node.get('component_type') or ''
    if cold_cable:
        conductor_size = cold_cable.get('conductor_size_mm2')
        return {
            'calculated_cold_cable_size': cold_cable.get('calculated_size') or '',
            'cold_cable_status': cold_cable.get('sizing_status') or '',
            'cold_cable_vd_status': cold_cable.get('vd_status') or '',
            'cold_cable_fault_status': cold_cable.get('fault_status') or '',
            'cold_cable_conductor_mass_mt': cold_cable.get('conductor_mass_mt'),
            'cold_cable_segment_role': 'Feeder Cable' if component_type == 'Cable4C' else 'Branch Cable',
            'cold_cable_circuit_index': node.get('circuit_index') or '',
            'cold_cable_length_basis': cold_cable.get('length_basis') or '',
            'cold_cable_vd_total_pct': cold_cable.get('vd_total_pct'),
            'cold_cable_load_end_voltage_v': cold_cable.get('load_end_voltage_v'),
            'cold_cable_fault_current_a': cold_cable.get('fault_current_a'),
            'cold_cable_is_critical_3c_segment': (
                bool(component_type == 'Cable3C' and conductor_size is not None)
                and _is_critical_3c_segment(conductor_size, _cold_cable_result_for_node(node, cold_results))
            ),
        }
    result = _cold_cable_result_for_node(node, cold_results)
    if result is None:
        return {
            'calculated_cold_cable_size': '',
            'cold_cable_status': '',
            'cold_cable_vd_status': '',
            'cold_cable_fault_status': '',
            'cold_cable_conductor_mass_mt': None,
            'cold_cable_segment_role': '',
            'cold_cable_circuit_index': '',
            'cold_cable_length_basis': '',
            'cold_cable_vd_total_pct': None,
            'cold_cable_load_end_voltage_v': None,
            'cold_cable_fault_current_a': None,
            'cold_cable_is_critical_3c_segment': False,
        }

    if component_type == 'Cable4C':
        size = _format_size(3, result.cable_4c_size_mm2)
        fault_status = result.fault_loop_status
        mass = result.cable_4c_conductor_mass_mt
        role = 'Feeder Cable'
        circuit_index = ''
        fault_current = result.fault_current_l_pe_a
        is_critical = False
    else:
        size = _format_size(3, result.cable_3c_size_mm2)
        fault_status = result.fault_loop_status
        mass = result.cable_3c_conductor_mass_mt
        role = 'Branch Cable'
        circuit_index = node.get('circuit_index') or ''
        fault_current = result.fault_current_l_pe_a
        is_critical = bool(result.cable_3c_size_mm2)
    return {
        'calculated_cold_cable_size': size,
        'cold_cable_status': result.sizing_status,
        'cold_cable_vd_status': result.vd_status,
        'cold_cable_fault_status': fault_status,
        'cold_cable_conductor_mass_mt': mass,
        'cold_cable_segment_role': role,
        'cold_cable_circuit_index': circuit_index,
        'cold_cable_length_basis': result.length_basis,
        'cold_cable_vd_total_pct': result.vd_total_pct,
        'cold_cable_load_end_voltage_v': result.load_end_voltage_v,
        'cold_cable_fault_current_a': fault_current,
        'cold_cable_is_critical_3c_segment': is_critical,
    }


def _is_critical_3c_segment(conductor_size, result):
    if result is None or result.cable_3c_size_mm2 is None:
        return False
    try:
        return float(conductor_size) >= float(result.cable_3c_size_mm2)
    except (TypeError, ValueError):
        return False


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
            return 'Distribution JB to Branch JB'
        if 'MCB' in source_types:
            return 'MCB to Branch JB'
        return 'Branch Cable'
    if component_type == 'Cable4C':
        if 'JB3PH' in source_types:
            return 'Distribution JB to downstream Distribution JB'
        if 'MCB' in source_types or {'Isolator3PH', 'JB3PH'} & target_types:
            return 'MCB to Distribution JB'
        return 'Feeder Cable'
    return ''


def _cable_schedule_rows(payload, cold_results=None):
    cold_results = cold_results or {}
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
        cold_fields = _cold_cable_fields(node, cold_results)
        rows.append({
            'sr_no': index,
            'cable_tag': _display_tag(node),
            'cable_specification': _cable_specification(node),
            **cold_fields,
            'cable_length_m': _cable_length_m(node),
            'connected_from': _connected_tags(incoming_edges, node_by_id, 'from_component_id'),
            'connected_to': _connected_tags(outgoing_edges, node_by_id, 'to_component_id'),
            'line_ids': _line_ids(node),
            'purpose': _purpose(node, incoming_edges, outgoing_edges, node_by_id),
            'cable_drum_tag': '',
            'cable_route_details': '',
            'remarks': metadata.get('cable_override_remarks') or '',
            'revision_no': '0',
            'manual_override_active': bool(metadata.get('cable_override_active')),
            'manual_size_review_status': metadata.get('manual_size_review_status') or '',
            'manual_size_review_note': metadata.get('manual_size_review_note') or '',
        })
    return rows


def build_cable_schedule_workspace_data(project_id):
    sld_payload = build_project_sld_payload(project_id)
    sld_meta = sld_payload.get('meta') or {}
    allow_topology_overrides = not sld_meta.get('topology_edit_review_required')
    cold_results = {}
    cold_result_rows = list(ColdCableResult.objects.filter(project_id=project_id).order_by('line_id', 'branch_index'))
    for result in cold_result_rows:
        cold_results[(str(result.line_uid), result.branch_index)] = result
        cold_results[(str(result.line_id), result.branch_index)] = result
    cable_rows = _cable_schedule_rows(sld_payload, cold_results)

    unique_cable_rows = {}
    for row in cable_rows:
        dedupe_key = row.get('cable_tag') or f"{row.get('line_ids', '')}:{row.get('sr_no', '')}"
        unique_cable_rows.setdefault(dedupe_key, row)
    total_cable_length_m = sum(row['cable_length_m'] for row in unique_cable_rows.values())
    total_conductor_mass_mt = sum(row.get('cold_cable_conductor_mass_mt') or 0 for row in unique_cable_rows.values())
    summary = {
        'row_count': len(cable_rows),
        'source_label': 'Manual SLD topology' if sld_meta.get('has_topology_edit') and allow_topology_overrides else 'Generated calculation',
        'has_topology_edit': bool(sld_meta.get('has_topology_edit')),
        'topology_baseline_changed': bool(sld_meta.get('topology_baseline_changed')),
        'manual_topology_warning': sld_meta.get('manual_topology_warning') or '',
        'total_cable_length_m': total_cable_length_m,
        'total_cable_length_display': f'{ceil(total_cable_length_m):,}',
        'total_conductor_mass_mt': total_conductor_mass_mt,
        'override_count': sum(1 for row in cable_rows if row['manual_override_active']),
        'manual_size_review_count': sum(1 for row in cable_rows if row.get('manual_size_review_status') in {'undersized', 'review_required'}),
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
            'Calculated Cold Cable Size': row.get('calculated_cold_cable_size', ''),
            'Cold Cable Segment Role': row.get('cold_cable_segment_role', ''),
            'Cold Cable Circuit Index': row.get('cold_cable_circuit_index', ''),
            'Cold Cable Status': row.get('cold_cable_status', ''),
            'Voltage Drop Status': row.get('cold_cable_vd_status', ''),
            'Fault Protection Status': row.get('cold_cable_fault_status', ''),
            'Total Path VD (%)': row.get('cold_cable_vd_total_pct', ''),
            'Load-End Voltage (V)': row.get('cold_cable_load_end_voltage_v', ''),
            'Fault Current (A)': row.get('cold_cable_fault_current_a', ''),
            'Length Basis': row.get('cold_cable_length_basis', ''),
            'Critical Branch Segment': 'Yes' if row.get('cold_cable_is_critical_3c_segment') else '',
            'Conductor Mass (MT)': row.get('cold_cable_conductor_mass_mt', ''),
            'Cable Length (m)': row.get('cable_length_m', ''),
            'Connected From': row.get('connected_from', ''),
            'Connected To': row.get('connected_to', ''),
            'Line IDs': row.get('line_ids', ''),
            'Purpose': row.get('purpose', ''),
            'Cable Drum Tag': row.get('cable_drum_tag', ''),
            'Cable Route Details': row.get('cable_route_details', ''),
            'Remarks': row.get('remarks', ''),
            'Manual Size Review': row.get('manual_size_review_status', ''),
            'Manual Size Review Note': row.get('manual_size_review_note', ''),
            'Rev. No.': row.get('revision_no', ''),
        }
        for row in cable_rows
    ]
