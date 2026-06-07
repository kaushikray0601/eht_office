import hashlib
import re

from .cable_management import apply_cable_overrides_to_payload
from .models import ColdCableResult, PowerDistributionBranch
from .sld_topology import apply_active_topology_edit
from .tracer_management import apply_tracer_selection_to_payload


COMPONENT_DISPLAY_NAMES = {
    'MCB': 'MCB',
    'Cable4C': '4C Cable',
    'Cable3C': '3C Cable',
    'Isolator3PH': '3PH Isolator',
    'Isolator1PH': '1PH Isolator',
    'JB3PH': '3PH JB',
    'JB1PH': '1PH JB',
    'Tracer': 'Heat Tracing Cable',
    'EndTermination': 'End Termination',
}

TOP_LEVEL_COMPONENT_ORDER = ['MCB', 'Cable4C', 'Isolator3PH', 'JB3PH']
DOWNSTREAM_COMPONENT_ORDER = ['Isolator1PH', 'Cable3C', 'JB1PH', 'Tracer', 'EndTermination']
SLD_GRAPH_SCHEMA_VERSION = 1

COMPONENT_SORT_ORDER = {
    component_type: index
    for index, component_type in enumerate(TOP_LEVEL_COMPONENT_ORDER + DOWNSTREAM_COMPONENT_ORDER)
}


def _stable_uid(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()[:32]


def _fallback_component_id(branch, component_type, circuit_index):
    line_uid_scope = str(branch.distribution.line.uid or branch.distribution.line.line_id or 'line')
    display_line_scope = str(branch.distribution.line.line_id or '')
    id_parts = [
        branch.distribution.line.proj_id or 'project',
        f'line_uid:{line_uid_scope}',
    ]
    if display_line_scope:
        id_parts.append(f'line:{display_line_scope}')
    id_parts.extend([
        f'branch:{branch.branch_index}',
        component_type,
        f'ckt:{circuit_index or 0}',
        'fallback',
    ])
    return ':'.join(id_parts)


def _normalize_component(
    *,
    branch,
    component_type,
    display_tag,
    detail=None,
    circuit_index=None,
):
    detail = detail or {}
    component_id = detail.get(
        'component_id',
        _fallback_component_id(branch, component_type, circuit_index),
    )
    line_id = detail.get('line_id') or branch.distribution.line.line_id
    line_ids = detail.get('line_ids') or ([line_id] if line_id else [])
    component_uid = detail.get('component_uid') or _stable_uid(component_id)
    metadata = dict(detail.get('metadata') or {})
    if component_type == 'MCB':
        calculation = getattr(branch.distribution.line, 'process_line_calculation', None)
        if calculation:
            metadata.setdefault('starting_current', calculation.starting_current)
            metadata.setdefault('operating_current', calculation.operating_current)
            metadata.setdefault('total_power_consumption', calculation.total_power_consumption)

    return {
        'component_id': component_id,
        'component_uid': component_uid,
        'display_tag': display_tag,
        'component_type': component_type,
        'display_name': COMPONENT_DISPLAY_NAMES.get(component_type, component_type),
        'label': display_tag,
        'line_id': line_id,
        'line_ids': line_ids,
        'line_uid': detail.get('line_uid') or str(branch.distribution.line.uid),
        'branch_index': detail.get('branch_index', branch.branch_index),
        'circuit_index': detail.get('circuit_index', circuit_index),
        'metadata': metadata,
    }


def _extract_branch_components(branch):
    tagged_components = branch.tagged_components or {}
    component_details = tagged_components.get('component_details') or {}
    extracted_components = []

    for component_type in TOP_LEVEL_COMPONENT_ORDER:
        display_tag = tagged_components.get(component_type)
        if not display_tag:
            continue
        extracted_components.append(
            _normalize_component(
                branch=branch,
                component_type=component_type,
                display_tag=display_tag,
                detail=component_details.get(component_type),
            )
        )

    for fallback_index, downstream in enumerate(tagged_components.get('Downstream', []), start=1):
        circuit_index = downstream.get('circuit_index') or fallback_index
        downstream_details = downstream.get('component_details') or {}
        for component_type in DOWNSTREAM_COMPONENT_ORDER:
            display_tag = downstream.get(component_type)
            if not display_tag:
                continue
            extracted_components.append(
                _normalize_component(
                    branch=branch,
                    component_type=component_type,
                    display_tag=display_tag,
                    detail=downstream_details.get(component_type),
                    circuit_index=circuit_index,
                )
            )

    return extracted_components


def _fallback_connections(branch, component_lookup):
    tagged_components = branch.tagged_components or {}
    fallback_edges = []

    def component_by_tag(tag_value):
        if not tag_value:
            return None
        return component_lookup.get(tag_value)

    top_chain = [
        component_by_tag(tagged_components.get(component_type))
        for component_type in TOP_LEVEL_COMPONENT_ORDER
    ]
    top_chain = [component for component in top_chain if component]
    for index in range(len(top_chain) - 1):
        fallback_edges.append({
            'from_component_id': top_chain[index]['component_id'],
            'to_component_id': top_chain[index + 1]['component_id'],
            'line_ids': top_chain[index].get('line_ids', []),
            'line_uid': top_chain[index].get('line_uid'),
            'branch_index': branch.branch_index,
            'circuit_index': None,
        })

    root_component = (
        component_by_tag(tagged_components.get('JB3PH'))
        if branch.branch_type == '3phJB'
        else component_by_tag(tagged_components.get('MCB'))
    )

    for downstream in tagged_components.get('Downstream', []):
        downstream_chain = [
            component_by_tag(downstream.get(component_type))
            for component_type in DOWNSTREAM_COMPONENT_ORDER
        ]
        downstream_chain = [component for component in downstream_chain if component]
        if not downstream_chain:
            continue
        if root_component:
            fallback_edges.append({
                'from_component_id': root_component['component_id'],
                'to_component_id': downstream_chain[0]['component_id'],
                'line_ids': root_component.get('line_ids', []),
                'line_uid': root_component.get('line_uid'),
                'branch_index': branch.branch_index,
                'circuit_index': downstream_chain[0].get('circuit_index'),
            })
        for index in range(len(downstream_chain) - 1):
            fallback_edges.append({
                'from_component_id': downstream_chain[index]['component_id'],
                'to_component_id': downstream_chain[index + 1]['component_id'],
                'line_ids': downstream_chain[index].get('line_ids', []),
                'line_uid': downstream_chain[index].get('line_uid'),
                'branch_index': branch.branch_index,
                'circuit_index': downstream_chain[index].get('circuit_index'),
            })

    return fallback_edges


def _node_sort_key(node):
    circuit_index = node.get('circuit_index')
    return (
        str(node.get('line_id') or ''),
        node.get('branch_index') or 0,
        -1 if circuit_index is None else circuit_index,
        COMPONENT_SORT_ORDER.get(node.get('component_type'), len(COMPONENT_SORT_ORDER)),
        str(node.get('component_id') or ''),
    )


def _edge_sort_key(edge):
    circuit_index = edge.get('circuit_index')
    return (
        ','.join(str(line_id) for line_id in edge.get('line_ids', [])),
        str(edge.get('line_uid') or ''),
        edge.get('branch_index') or 0,
        -1 if circuit_index is None else circuit_index,
        str(edge.get('from_component_id') or ''),
        str(edge.get('to_component_id') or ''),
    )


def _empty_payload(project_id):
    return {
        'schema_version': SLD_GRAPH_SCHEMA_VERSION,
        'project_id': project_id,
        'nodes': [],
        'edges': [],
        'line_groups': [],
        'meta': {
            'branch_count': 0,
            'node_count': 0,
            'edge_count': 0,
        },
    }


def _format_cold_cable_size(core_count, size_mm2):
    if size_mm2 in (None, ''):
        return ''
    return f'{core_count}C x {float(size_mm2):g} mm2'


def _parse_cable_size_label(value):
    match = re.search(r'(?P<core>[34])\s*C\s*(?:x|X)?\s*(?P<size>\d+(?:\.\d+)?)', str(value or ''))
    if not match:
        return None
    return {
        'core_count': int(match.group('core')),
        'size_mm2': float(match.group('size')),
    }


def _manual_size_review(node, cold_metadata):
    metadata = node.get('metadata') or {}
    manual_size = metadata.get('manual_cable_size')
    if not manual_size:
        return {}
    parsed = _parse_cable_size_label(manual_size)
    expected_core_count = 4 if node.get('component_type') == 'Cable4C' else 3
    calculated_size = cold_metadata.get('conductor_size_mm2')
    if not parsed or calculated_size in (None, ''):
        return {
            'manual_size_review_status': 'review_required',
            'manual_size_review_note': 'Manual cable size could not be compared with the calculated cold cable size.',
        }
    if parsed['core_count'] != expected_core_count:
        return {
            'manual_size_review_status': 'review_required',
            'manual_size_review_note': f'Manual cable core count does not match this {expected_core_count}C cable segment.',
        }
    if parsed['size_mm2'] + 1e-9 < float(calculated_size):
        return {
            'manual_size_review_status': 'undersized',
            'manual_size_review_note': 'Manual cable size is below the calculated cold cable size.',
        }
    return {
        'manual_size_review_status': 'acceptable',
        'manual_size_review_note': 'Manual cable size is equal to or larger than the calculated cold cable size.',
    }


def _cold_cable_result_indexes(project_id):
    by_line_branch = {}
    cold_results = ColdCableResult.objects.filter(project_id=project_id).select_related(
        'cable_4c_catalogue',
        'cable_3c_catalogue',
    )
    for result in cold_results:
        by_line_branch[(str(result.line_uid), result.branch_index)] = result
        by_line_branch[(str(result.line_id), result.branch_index)] = result
    return by_line_branch


def _cold_cable_result_for_node(node, cold_result_index):
    branch_index = node.get('branch_index') or 0
    line_uid = str(node.get('line_uid') or '')
    if line_uid:
        result = cold_result_index.get((line_uid, branch_index))
        if result:
            return result
    line_id = str(node.get('line_id') or '')
    if line_id:
        result = cold_result_index.get((line_id, branch_index))
        if result:
            return result
    for candidate_line_id in node.get('line_ids') or []:
        result = cold_result_index.get((str(candidate_line_id), branch_index))
        if result:
            return result
    return None


def _cold_cable_segment_for_node(node, result):
    if node.get('component_type') != 'Cable3C':
        return None
    segments = result.cable_3c_segments or []
    component_id = str(node.get('component_id') or '')
    display_tag = str(node.get('display_tag') or '')
    circuit_index = node.get('circuit_index')
    for segment in segments:
        if component_id and str(segment.get('component_id') or '') == component_id:
            return segment
        if display_tag and str(segment.get('display_tag') or '') == display_tag:
            return segment
    for segment in segments:
        if circuit_index is not None and segment.get('circuit_index') == circuit_index:
            return segment
    return None


def _cold_cable_metadata_for_node(node, result):
    component_type = node.get('component_type')
    phase_slot = None
    phase_label = ''
    phase_basis = ''
    if component_type == 'Cable4C':
        calculated_size = _format_cold_cable_size(4, result.cable_4c_size_mm2)
        conductor_size = result.cable_4c_size_mm2
        derated_ampacity = result.cable_4c_ampacity_derated_a
        ampacity_margin = result.cable_4c_ampacity_margin_pct
        conductor_temp = result.cable_4c_conductor_temp_c
        conductor_mass = result.cable_4c_conductor_mass_mt
        length_m = result.length_4c_m
        vd_pct = result.cable_4c_vd_pct
        fault_status = result.fault_protection_4c_status
        fault_current = result.fault_current_4c_phase_to_phase_a
    elif component_type == 'Cable3C':
        segment = _cold_cable_segment_for_node(node, result)
        if segment:
            calculated_size = _format_cold_cable_size(3, segment.get('size_mm2'))
            conductor_size = segment.get('size_mm2')
            derated_ampacity = segment.get('ampacity_derated_a')
            ampacity_margin = segment.get('ampacity_margin_pct')
            conductor_temp = segment.get('conductor_temp_c')
            conductor_mass = segment.get('conductor_mass_mt')
            length_m = segment.get('length_m')
            vd_pct = segment.get('vd_pct')
            fault_status = segment.get('fault_status') or result.fault_protection_3c_status
            fault_current = segment.get('fault_current_a')
            length_basis = segment.get('length_basis') or result.length_basis
            vd_total_pct = segment.get('vd_total_pct')
            load_end_voltage = segment.get('load_end_voltage_v')
            k_temp = segment.get('k_temp')
            k_group = segment.get('k_group')
            k_total = segment.get('k_total')
            review_notes = list(segment.get('review_notes') or [])
            phase_slot = segment.get('phase_slot')
            phase_label = segment.get('phase_label') or ''
            phase_basis = segment.get('phase_basis') or ''
        else:
            calculated_size = _format_cold_cable_size(3, result.cable_3c_size_mm2)
            conductor_size = result.cable_3c_size_mm2
            derated_ampacity = result.cable_3c_ampacity_derated_a
            ampacity_margin = result.cable_3c_ampacity_margin_pct
            conductor_temp = result.cable_3c_conductor_temp_c
            conductor_mass = result.cable_3c_conductor_mass_mt
            length_m = result.length_3c_m
            vd_pct = result.cable_3c_vd_pct
            fault_status = result.fault_protection_3c_status
            fault_current = result.fault_current_3c_line_to_neutral_a
            length_basis = result.length_basis
            vd_total_pct = result.vd_total_pct
            load_end_voltage = result.load_end_voltage_v
            k_temp = result.k_temp
            k_group = result.k_group
            k_total = result.k_total
            review_notes = result.review_notes or []
    else:
        return None

    return {
        'calculated_size': calculated_size,
        'conductor_size_mm2': conductor_size,
        'sizing_status': result.sizing_status,
        'vd_status': result.vd_status,
        'fault_status': fault_status,
        'length_basis': length_basis if component_type == 'Cable3C' else result.length_basis,
        'length_m': length_m,
        'derated_ampacity_a': derated_ampacity,
        'ampacity_margin_pct': ampacity_margin,
        'conductor_temp_c': conductor_temp,
        'conductor_mass_mt': conductor_mass,
        'vd_pct': vd_pct,
        'vd_total_pct': vd_total_pct if component_type == 'Cable3C' else result.vd_total_pct,
        'vd_allowable_pct': result.vd_allowable_pct,
        'load_end_voltage_v': load_end_voltage if component_type == 'Cable3C' else result.load_end_voltage_v,
        'fault_current_a': fault_current,
        'k_temp': k_temp if component_type == 'Cable3C' else result.k_temp,
        'k_group': k_group if component_type == 'Cable3C' else result.k_group,
        'k_total': k_total if component_type == 'Cable3C' else result.k_total,
        'phase_slot': phase_slot if component_type == 'Cable3C' else None,
        'phase_label': phase_label if component_type == 'Cable3C' else '',
        'phase_basis': phase_basis if component_type == 'Cable3C' else '',
        'review_notes': review_notes if component_type == 'Cable3C' else result.review_notes or [],
    }


def apply_cold_cable_results_to_payload(project_id, payload):
    cold_result_index = _cold_cable_result_indexes(project_id)
    if not cold_result_index:
        return payload

    for node in payload.get('nodes', []):
        if node.get('component_type') not in {'Cable4C', 'Cable3C'}:
            continue
        result = _cold_cable_result_for_node(node, cold_result_index)
        if result is None:
            continue
        metadata = dict(node.get('metadata') or {})
        cold_metadata = _cold_cable_metadata_for_node(node, result)
        if cold_metadata is None:
            continue
        metadata['cold_cable'] = cold_metadata
        metadata['cold_cable_calculated_size'] = cold_metadata['calculated_size']
        metadata['cold_cable_status'] = cold_metadata['sizing_status']
        metadata['cold_cable_vd_status'] = cold_metadata['vd_status']
        metadata['cold_cable_fault_status'] = cold_metadata['fault_status']
        metadata.update(_manual_size_review(node, cold_metadata))
        node['metadata'] = metadata
    return payload


def filter_sld_payload_by_line(payload, selected_line_id):
    selected_line_id = (selected_line_id or '').strip()
    if not selected_line_id:
        return payload, ''
    selected_line_id_key = selected_line_id.casefold()

    target_groups = [
        group
        for group in payload.get('line_groups', [])
        if (
            selected_line_id_key in group.get('line_id', '').casefold()
            or selected_line_id_key in group.get('original_line_id', '').casefold()
        )
    ]
    if not target_groups:
        return None, ''

    normalized_line_id = target_groups[0]['line_id']
    target_line_uids = {
        str(group.get('line_uid'))
        for group in target_groups
        if group.get('line_uid')
    }
    target_line_ids = {
        group.get('line_id')
        for group in target_groups
        if group.get('line_id')
    }
    filtered_nodes = [
        node for node in payload.get('nodes', [])
        if (
            str(node.get('line_uid') or '') in target_line_uids
            or bool(target_line_ids & set(node.get('line_ids') or []))
            or (not target_line_uids and normalized_line_id in node.get('line_ids', []))
        )
    ]
    component_ids = {node['component_id'] for node in filtered_nodes}
    filtered_edges = [
        edge for edge in payload.get('edges', [])
        if edge['from_component_id'] in component_ids
        and edge['to_component_id'] in component_ids
        and (
            str(edge.get('line_uid') or '') in target_line_uids
            or bool(target_line_ids & set(edge.get('line_ids') or []))
            or (not edge.get('line_uid') and normalized_line_id in edge.get('line_ids', []))
            or (not target_line_uids and normalized_line_id in edge.get('line_ids', []))
        )
    ]

    return {
        **payload,
        'nodes': filtered_nodes,
        'edges': filtered_edges,
        'line_groups': target_groups,
        'meta': {
            **payload.get('meta', {}),
            'branch_count': sum(len(group['branch_indices']) for group in target_groups),
            'node_count': len(filtered_nodes),
            'edge_count': len(filtered_edges),
        },
    }, normalized_line_id


def build_project_sld_payload(project_id, line_id=None, apply_topology=True):
    selected_line_id = (line_id or '').strip()
    branch_query = (
        PowerDistributionBranch.objects.filter(distribution__line__proj_id=project_id)
        .select_related('distribution__line', 'distribution__line__process_line_calculation')
        .order_by('distribution__line__line_id', 'distribution__line__uid', 'branch_index')
    )
    if selected_line_id and not apply_topology:
        branch_query = branch_query.filter(distribution__line__line_id__icontains=selected_line_id)
    branches = list(branch_query)

    node_by_component_id = {}
    edges = []
    line_groups = {}

    for branch in branches:
        extracted_components = _extract_branch_components(branch)
        component_lookup = {}
        for component in extracted_components:
            component_lookup[component['display_tag']] = component
            node_by_component_id.setdefault(component['component_id'], component)

        line_id = branch.distribution.line.line_id
        line_uid = str(branch.distribution.line.uid)
        line_group_key = (line_id, line_uid)
        line_groups.setdefault(line_group_key, {
            'line_id': line_id,
            'line_uid': line_uid,
            'branch_indices': [],
        })['branch_indices'].append(branch.branch_index)

        stored_connections = (branch.tagged_components or {}).get('connections') or []
        if stored_connections:
            for connection in stored_connections:
                edges.append({
                    'from_component_id': connection['from_component_id'],
                    'to_component_id': connection['to_component_id'],
                    'line_ids': connection.get('line_ids', [branch.distribution.line.line_id]),
                    'line_uid': connection.get('line_uid') or line_uid,
                    'branch_index': connection.get('branch_index', branch.branch_index),
                    'circuit_index': connection.get('circuit_index'),
                })
        else:
            edges.extend(_fallback_connections(branch, component_lookup))

    generated_payload = {
        'schema_version': SLD_GRAPH_SCHEMA_VERSION,
        'project_id': project_id,
        'nodes': sorted(node_by_component_id.values(), key=_node_sort_key),
        'edges': sorted(edges, key=_edge_sort_key),
        'line_groups': [
            {
                'line_id': group['line_id'],
                'line_uid': group['line_uid'],
                'branch_indices': sorted(group['branch_indices']),
            }
            for _key, group in sorted(line_groups.items())
        ],
        'meta': {
            'branch_count': len(branches),
            'node_count': len(node_by_component_id),
            'edge_count': len(edges),
        },
    }
    generated_payload = apply_cable_overrides_to_payload(project_id, generated_payload)
    generated_payload = apply_tracer_selection_to_payload(project_id, generated_payload)
    payload = apply_active_topology_edit(project_id, generated_payload) if apply_topology else generated_payload
    if apply_topology:
        payload = apply_cable_overrides_to_payload(project_id, payload)
        payload = apply_tracer_selection_to_payload(project_id, payload)
    payload = apply_cold_cable_results_to_payload(project_id, payload)
    if selected_line_id:
        filtered_payload, _normalized_line_id = filter_sld_payload_by_line(payload, selected_line_id)
        return filtered_payload or _empty_payload(project_id)
    return payload
