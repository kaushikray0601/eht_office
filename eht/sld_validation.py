from .models import PowerDistributionBranch, ProjectData
from .sld_payload import build_project_sld_payload


UPSTREAM_COMPONENT_ORDER = ['MCB', 'Cable4C', 'Isolator3PH', 'JB3PH']
DOWNSTREAM_COMPONENT_ORDER = ['Isolator1PH', 'Cable3C', 'JB1PH', 'Tracer', 'EndTermination']
STATUS_SEVERITY = {'passed': 0, 'warning': 1, 'failed': 2}


def _next_status(current_status, candidate_status):
    if STATUS_SEVERITY[candidate_status] > STATUS_SEVERITY[current_status]:
        return candidate_status
    return current_status


def _append_check(collection, *, code, label, status, details, line_id=None, branch_index=None):
    collection.append({
        'code': code,
        'label': label,
        'status': status,
        'details': details,
        'line_id': line_id,
        'branch_index': branch_index,
    })


def _expected_component_counts(branch, project_setup):
    incoming_isolator_required = (
        branch.branch_type == '3phJB'
        and project_setup.isolator_location in ['bothSides', 'incomingOnly']
    )
    outgoing_isolator_required = project_setup.isolator_location in ['bothSides', 'outgoingOnly']

    top_counts = {
        'MCB': 1,
        'Cable4C': 1 if branch.branch_type == '3phJB' else 0,
        'Isolator3PH': 1 if incoming_isolator_required else 0,
        'JB3PH': 1 if branch.branch_type == '3phJB' else 0,
    }
    downstream_counts = {
        'Isolator1PH': 1 if outgoing_isolator_required else 0,
        'Cable3C': 1,
        'JB1PH': 1,
        'Tracer': 1,
        'EndTermination': 1,
    }
    return top_counts, downstream_counts


def _summarize_branch_validation(branch, branch_nodes, branch_edges, project_setup):
    top_expected, downstream_expected = _expected_component_counts(branch, project_setup)
    issues = []
    status = 'passed'

    component_details = (branch.tagged_components or {}).get('component_details') or {}
    stored_connections = (branch.tagged_components or {}).get('connections') or []
    if not component_details or not stored_connections:
        status = _next_status(status, 'warning')
        issues.append('Legacy branch JSON required fallback reconstruction for some SLD data.')

    top_counts = {
        component_type: sum(
            1
            for node in branch_nodes
            if node['component_type'] == component_type and node.get('circuit_index') is None
        )
        for component_type in UPSTREAM_COMPONENT_ORDER
    }
    for component_type, expected_count in top_expected.items():
        actual_count = top_counts.get(component_type, 0)
        if actual_count != expected_count:
            status = _next_status(status, 'failed')
            issues.append(
                f"{component_type} count mismatch: expected {expected_count}, found {actual_count}."
            )

    circuit_indices = sorted({
        node['circuit_index']
        for node in branch_nodes
        if node.get('circuit_index') is not None
    })
    if len(circuit_indices) != branch.circuit_count:
        status = _next_status(status, 'failed')
        issues.append(
            f"Circuit count mismatch: expected {branch.circuit_count}, found {len(circuit_indices)} in SLD nodes."
        )

    for circuit_index in circuit_indices:
        circuit_nodes = [node for node in branch_nodes if node.get('circuit_index') == circuit_index]
        for component_type, expected_count in downstream_expected.items():
            actual_count = sum(1 for node in circuit_nodes if node['component_type'] == component_type)
            if actual_count != expected_count:
                status = _next_status(status, 'failed')
                issues.append(
                    f"Circuit {circuit_index} {component_type} mismatch: expected {expected_count}, found {actual_count}."
                )

    expected_node_count = sum(top_expected.values()) + branch.circuit_count * sum(downstream_expected.values())
    if len(branch_nodes) != expected_node_count:
        status = _next_status(status, 'failed')
        issues.append(
            f"Branch node count mismatch: expected {expected_node_count}, found {len(branch_nodes)}."
        )

    top_chain_nodes = sum(top_expected.values())
    expected_edge_count = max(top_chain_nodes - 1, 0) + branch.circuit_count * sum(downstream_expected.values())
    if len(branch_edges) != expected_edge_count:
        status = _next_status(status, 'failed')
        issues.append(
            f"Branch edge count mismatch: expected {expected_edge_count}, found {len(branch_edges)}."
        )

    if not issues:
        issues.append(
            f"Branch {branch.branch_index} matches the stored {branch.branch_type} topology for line {branch.distribution.line.line_id}."
        )

    return {
        'line_id': branch.distribution.line.line_id,
        'branch_index': branch.branch_index,
        'branch_type': branch.branch_type,
        'status': status,
        'component_count': len(branch_nodes),
        'edge_count': len(branch_edges),
        'details': ' '.join(issues),
    }


def validate_project_sld_payload(project_id, payload=None):
    payload = payload or build_project_sld_payload(project_id)
    branches = list(
        PowerDistributionBranch.objects.filter(distribution__line__proj_id=project_id)
        .select_related('distribution__line')
        .order_by('distribution__line__line_id', 'branch_index')
    )
    project_setup = ProjectData.objects.filter(proj_id=project_id).first()

    checks = []
    branch_checks = []
    nodes = payload.get('nodes', [])
    edges = payload.get('edges', [])
    node_ids = [node['component_id'] for node in nodes]
    display_tags = [node['display_tag'] for node in nodes]
    component_uids = [node['component_uid'] for node in nodes]
    node_by_id = {node['component_id']: node for node in nodes}

    _append_check(
        checks,
        code='branch_count_matches',
        label='Branch count matches stored project branches',
        status='passed' if payload['meta']['branch_count'] == len(branches) else 'failed',
        details=f"Payload branches: {payload['meta']['branch_count']}, stored branches: {len(branches)}.",
    )
    _append_check(
        checks,
        code='unique_display_tags',
        label='Display tags are unique across the project',
        status='passed' if len(display_tags) == len(set(display_tags)) else 'failed',
        details=f"Checked {len(display_tags)} display tags.",
    )
    _append_check(
        checks,
        code='unique_component_ids',
        label='Stable component IDs are unique across the project',
        status='passed' if len(node_ids) == len(set(node_ids)) else 'failed',
        details=f"Checked {len(node_ids)} component IDs.",
    )
    _append_check(
        checks,
        code='unique_component_uids',
        label='Stable 16-character component UIDs are unique across the project',
        status='passed' if len(component_uids) == len(set(component_uids)) else 'failed',
        details=f"Checked {len(component_uids)} component UIDs.",
    )

    missing_edge_targets = [
        edge for edge in edges
        if edge['from_component_id'] not in node_by_id or edge['to_component_id'] not in node_by_id
    ]
    _append_check(
        checks,
        code='edge_endpoint_resolution',
        label='All SLD edges resolve to real component nodes',
        status='passed' if not missing_edge_targets else 'failed',
        details=(
            f"Checked {len(edges)} edges."
            if not missing_edge_targets
            else f"{len(missing_edge_targets)} edge(s) reference missing nodes."
        ),
    )

    line_group_map = {
        item['line_id']: item['branch_indices']
        for item in payload.get('line_groups', [])
    }
    expected_line_group_map = {}
    for branch in branches:
        expected_line_group_map.setdefault(branch.distribution.line.line_id, []).append(branch.branch_index)
    expected_line_group_map = {
        line_id: sorted(indices)
        for line_id, indices in expected_line_group_map.items()
    }
    _append_check(
        checks,
        code='line_groups_match',
        label='Line groups in the SLD payload match stored branch ownership',
        status='passed' if line_group_map == expected_line_group_map else 'failed',
        details=(
            f"Payload line groups: {len(line_group_map)}, stored line groups: {len(expected_line_group_map)}."
        ),
    )

    if project_setup is None:
        _append_check(
            checks,
            code='project_setup_available',
            label='Project setup exists for validation rules',
            status='failed',
            details='ProjectData record is missing, so branch topology rules cannot be validated.',
        )
    else:
        _append_check(
            checks,
            code='project_setup_available',
            label='Project setup exists for validation rules',
            status='passed',
            details='ProjectData record is available for topology validation.',
        )

    for branch in branches:
        line_id = branch.distribution.line.line_id
        branch_nodes = [
            node for node in nodes
            if node['branch_index'] == branch.branch_index and line_id in node.get('line_ids', [])
        ]
        branch_edges = [
            edge for edge in edges
            if edge['branch_index'] == branch.branch_index and line_id in edge.get('line_ids', [])
        ]

        if project_setup is None:
            branch_checks.append({
                'line_id': line_id,
                'branch_index': branch.branch_index,
                'branch_type': branch.branch_type,
                'status': 'failed',
                'component_count': len(branch_nodes),
                'edge_count': len(branch_edges),
                'details': 'Project setup is missing, so branch validation could not be completed.',
            })
            continue

        branch_checks.append(
            _summarize_branch_validation(branch, branch_nodes, branch_edges, project_setup)
        )

    passed_count = sum(1 for check in checks if check['status'] == 'passed') + sum(
        1 for check in branch_checks if check['status'] == 'passed'
    )
    warning_count = sum(1 for check in checks if check['status'] == 'warning') + sum(
        1 for check in branch_checks if check['status'] == 'warning'
    )
    failed_count = sum(1 for check in checks if check['status'] == 'failed') + sum(
        1 for check in branch_checks if check['status'] == 'failed'
    )
    overall_status = 'failed' if failed_count else 'warning' if warning_count else 'passed'

    return {
        'project_id': project_id,
        'status': overall_status,
        'summary': {
            'passed_count': passed_count,
            'warning_count': warning_count,
            'failed_count': failed_count,
            'check_count': len(checks) + len(branch_checks),
        },
        'checks': checks,
        'branch_checks': branch_checks,
    }
