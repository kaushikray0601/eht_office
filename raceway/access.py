from django.core.exceptions import PermissionDenied

from plant3d.project_gateway import (
    accessible_project_ids as gateway_accessible_project_ids,
    project_identifier,
    validate_project_id as gateway_validate_project_id,
)


def normalize_project_id(project):
    return project_identifier(project)


def accessible_project_ids(user):
    return list(gateway_accessible_project_ids(user))


def validate_project_id(project_id, user=None):
    return gateway_validate_project_id(project_id, user)


def user_can_access_project(user, project_id):
    return bool(validate_project_id(project_id, user))


def require_project_access(project_id, user=None):
    resolved_project_id = validate_project_id(project_id, user)
    if not resolved_project_id:
        raise PermissionDenied("You do not have access to this raceway project.")
    return resolved_project_id
