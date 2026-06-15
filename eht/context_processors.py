from urllib.parse import urlencode

from django.db.models import Count
from django.urls import reverse

from .models import (
    DEFAULT_PROJECT_ID,
    HeatTracingInput,
    ManagedProject,
    ProcessLineCalculation,
    ProjectData,
    is_default_project_id,
)


def nav_projects(request):
    user = getattr(request, 'user', None)
    if not getattr(user, 'is_authenticated', False):
        return {'nav_projects': []}

    projects = [
        project
        for project in ManagedProject.available_to_user(user)
        if not is_default_project_id(project.proj_id)
    ]
    if not projects:
        return {'nav_projects': []}

    project_ids = [project.proj_id for project in projects]
    setup_project_ids = set(
        ProjectData.objects
        .filter(proj_id__in=project_ids)
        .values_list('proj_id', flat=True)
    )
    input_counts = {
        row['proj_id']: row['count']
        for row in HeatTracingInput.objects
        .filter(proj_id__in=project_ids)
        .values('proj_id')
        .annotate(count=Count('uid'))
    }
    result_counts = {
        row['line__proj_id']: row['count']
        for row in ProcessLineCalculation.objects
        .filter(line__proj_id__in=project_ids)
        .values('line__proj_id')
        .annotate(count=Count('uid'))
    }

    nav_rows = []
    for project in projects:
        project_id = project.proj_id
        if result_counts.get(project_id, 0):
            status_label = 'Calculated'
            status_tone = 'success'
        elif input_counts.get(project_id, 0):
            status_label = 'Input ready'
            status_tone = 'warning'
        elif project_id in setup_project_ids:
            status_label = 'Setup'
            status_tone = 'info'
        else:
            status_label = 'New'
            status_tone = 'secondary'
        nav_rows.append({
            'proj_id': project_id,
            'display_name': project.display_name,
            'status_label': status_label,
            'status_tone': status_tone,
            'workspace_url': f"{reverse('base')}?{urlencode({'project_id': project_id})}",
        })

    return {
        'nav_projects': nav_rows,
        'default_project_id': DEFAULT_PROJECT_ID,
    }
