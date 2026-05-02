from .models import PowerDistributionBranch


PUBLIC_TAGGED_COMPONENT_SCHEMA_VERSION = 1


def _branch_issue(branch, code, message):
    return {
        'code': code,
        'line_id': branch.distribution.line.line_id,
        'line_uid': str(branch.distribution.line.uid),
        'branch_index': branch.branch_index,
        'message': message,
    }


def _audit_branch(branch):
    tagged = branch.tagged_components or {}
    issues = []

    if tagged.get('schema_version') != PUBLIC_TAGGED_COMPONENT_SCHEMA_VERSION:
        issues.append(_branch_issue(
            branch,
            'missing_schema_version',
            'Tagged components are missing schema_version 1.',
        ))

    component_details = tagged.get('component_details')
    if not isinstance(component_details, dict) or not component_details:
        issues.append(_branch_issue(
            branch,
            'missing_component_details',
            'Tagged components are missing explicit component_details.',
        ))

    connections = tagged.get('connections')
    if not isinstance(connections, list) or not connections:
        issues.append(_branch_issue(
            branch,
            'missing_connections',
            'Tagged components are missing explicit graph connections.',
        ))
    else:
        for index, connection in enumerate(connections, start=1):
            if not isinstance(connection, dict):
                issues.append(_branch_issue(
                    branch,
                    'invalid_connection',
                    f'Connection {index} is not an object.',
                ))
                continue
            if not connection.get('from_component_id') or not connection.get('to_component_id'):
                issues.append(_branch_issue(
                    branch,
                    'invalid_connection_endpoint',
                    f'Connection {index} is missing from/to component IDs.',
                ))

    downstream_items = tagged.get('Downstream')
    if not isinstance(downstream_items, list) or not downstream_items:
        issues.append(_branch_issue(
            branch,
            'missing_downstream',
            'Tagged components are missing downstream circuit details.',
        ))
    else:
        for index, downstream in enumerate(downstream_items, start=1):
            downstream_details = downstream.get('component_details') if isinstance(downstream, dict) else None
            if not isinstance(downstream_details, dict) or not downstream_details:
                issues.append(_branch_issue(
                    branch,
                    'missing_downstream_component_details',
                    f'Downstream circuit {index} is missing explicit component_details.',
                ))

    return issues


def audit_tagged_component_schema(project_id=None, line_id=None):
    branch_query = PowerDistributionBranch.objects.select_related('distribution__line').order_by(
        'distribution__line__line_id',
        'distribution__line__uid',
        'branch_index',
    )
    if project_id:
        branch_query = branch_query.filter(distribution__line__proj_id=project_id)
    if line_id:
        branch_query = branch_query.filter(distribution__line__line_id__icontains=line_id)

    branches = list(branch_query)
    issues = []
    for branch in branches:
        issues.extend(_audit_branch(branch))

    affected_branches = {
        (issue['line_uid'], issue['branch_index'])
        for issue in issues
    }
    return {
        'project_id': project_id or '',
        'line_id': line_id or '',
        'branch_count': len(branches),
        'issue_count': len(issues),
        'affected_branch_count': len(affected_branches),
        'ready_for_strict_schema': not issues,
        'issues': issues,
    }
