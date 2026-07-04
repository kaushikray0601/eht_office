from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectOption:
    project_id: str
    label: str


def project_identifier(project):
    if project is None:
        return ""
    return str(getattr(project, "proj_id", project)).strip()


def accessible_project_ids(user):
    if not getattr(user, "is_authenticated", False):
        return []
    from eht.models import ManagedProject

    return list(ManagedProject.available_to_user(user).values_list("proj_id", flat=True))


def project_options_for_user(user):
    project_ids = accessible_project_ids(user)
    if not project_ids:
        return []
    from eht.models import ProjectData

    labels_by_id = {
        project.proj_id: str(project)
        for project in ProjectData.objects.filter(proj_id__in=project_ids).order_by("proj_id")
    }
    return [
        ProjectOption(project_id=project_id, label=labels_by_id.get(project_id) or project_id)
        for project_id in project_ids
    ]


def validate_project_id(project_id, user=None):
    project_id = project_identifier(project_id)
    if not project_id:
        return ""
    resolved_project_id = project_id
    from eht.models import ProjectData

    if not ProjectData.objects.filter(proj_id=resolved_project_id).exists():
        try:
            resolved_project_id = ProjectData.objects.get(pk=project_id).proj_id
        except (ProjectData.DoesNotExist, ValueError, TypeError):
            resolved_project_id = project_id

    if user is not None and getattr(user, "is_authenticated", False):
        return resolved_project_id if resolved_project_id in set(accessible_project_ids(user)) else ""

    return resolved_project_id if ProjectData.objects.filter(proj_id=resolved_project_id).exists() else ""
