import hashlib

from .models import PowerDistributionBranch


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


def _stable_uid(value):
    return hashlib.sha1(value.encode('utf-8')).hexdigest()[:16]


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
        ':'.join([
            branch.distribution.line.proj_id or 'project',
            f'line:{branch.distribution.line.line_id or branch.distribution.line.uid}',
            f'branch:{branch.branch_index}',
            component_type,
            f'ckt:{circuit_index or 0}',
            'fallback',
        ]),
    )
    line_id = detail.get('line_id') or branch.distribution.line.line_id
    line_ids = detail.get('line_ids') or ([line_id] if line_id else [])
    component_uid = detail.get('component_uid') or _stable_uid(component_id)
    metadata = detail.get('metadata') or {}

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
                'branch_index': branch.branch_index,
                'circuit_index': downstream_chain[0].get('circuit_index'),
            })
        for index in range(len(downstream_chain) - 1):
            fallback_edges.append({
                'from_component_id': downstream_chain[index]['component_id'],
                'to_component_id': downstream_chain[index + 1]['component_id'],
                'line_ids': downstream_chain[index].get('line_ids', []),
                'branch_index': branch.branch_index,
                'circuit_index': downstream_chain[index].get('circuit_index'),
            })

    return fallback_edges


def build_project_sld_payload(project_id):
    branches = list(
        PowerDistributionBranch.objects.filter(distribution__line__proj_id=project_id)
        .select_related('distribution__line', 'distribution__line__process_line_calculation')
        .order_by('distribution__line__line_id', 'branch_index')
    )

    node_by_component_id = {}
    edges = []
    line_groups = {}

    for branch in branches:
        extracted_components = _extract_branch_components(branch)
        component_lookup = {}
        for component in extracted_components:
            component_lookup[component['display_tag']] = component
            node_by_component_id.setdefault(component['component_id'], component)

        for line_id in {branch.distribution.line.line_id}:
            line_groups.setdefault(line_id, []).append(branch.branch_index)

        stored_connections = (branch.tagged_components or {}).get('connections') or []
        if stored_connections:
            for connection in stored_connections:
                edges.append({
                    'from_component_id': connection['from_component_id'],
                    'to_component_id': connection['to_component_id'],
                    'line_ids': connection.get('line_ids', [branch.distribution.line.line_id]),
                    'branch_index': connection.get('branch_index', branch.branch_index),
                    'circuit_index': connection.get('circuit_index'),
                })
        else:
            edges.extend(_fallback_connections(branch, component_lookup))

    return {
        'project_id': project_id,
        'nodes': list(node_by_component_id.values()),
        'edges': edges,
        'line_groups': [
            {
                'line_id': line_id,
                'branch_indices': sorted(branch_indices),
            }
            for line_id, branch_indices in sorted(line_groups.items())
        ],
        'meta': {
            'branch_count': len(branches),
            'node_count': len(node_by_component_id),
            'edge_count': len(edges),
        },
    }
