from django.db import transaction

from .models import ProjectData, SLDNodeLayout
from .sld_payload import build_project_sld_payload


def get_project_sld_layout(project_id, payload=None):
    payload = payload or build_project_sld_payload(project_id)
    valid_component_ids = {node['component_id'] for node in payload.get('nodes', [])}
    layout_rows = list(
        SLDNodeLayout.objects.filter(project_id=project_id, component_id__in=valid_component_ids)
        .order_by('line_id', 'branch_index', 'component_type', 'display_tag')
    )

    positions = {
        row.component_id: {
            'x': row.x_position,
            'y': row.y_position,
            'component_uid': row.component_uid,
            'display_tag': row.display_tag,
        }
        for row in layout_rows
    }
    return {
        'project_id': project_id,
        'positions': positions,
        'meta': {
            'saved_count': len(layout_rows),
            'node_count': len(valid_component_ids),
            'has_saved_layout': bool(layout_rows),
            'save_mode': 'merge',
        },
    }


@transaction.atomic
def save_project_sld_layout(project_id, positions, payload=None):
    payload = payload or build_project_sld_payload(project_id)
    project = ProjectData.objects.get(proj_id=project_id)
    valid_nodes = {node['component_id']: node for node in payload.get('nodes', [])}
    valid_component_ids = set(valid_nodes.keys())

    normalized_positions = {}
    ignored_component_ids = []
    for component_id, coords in (positions or {}).items():
        if component_id not in valid_nodes:
            ignored_component_ids.append(component_id)
            continue
        if not isinstance(coords, dict) or 'x' not in coords or 'y' not in coords:
            ignored_component_ids.append(component_id)
            continue
        normalized_positions[component_id] = {
            'x': float(coords['x']),
            'y': float(coords['y']),
        }

    SLDNodeLayout.objects.filter(project=project).exclude(component_id__in=valid_component_ids).delete()
    saved_count = 0
    for component_id, coords in normalized_positions.items():
        node = valid_nodes[component_id]
        SLDNodeLayout.objects.update_or_create(
            project=project,
            component_id=component_id,
            defaults={
                'component_uid': node.get('component_uid', ''),
                'display_tag': node.get('display_tag', ''),
                'component_type': node.get('component_type', ''),
                'line_id': node.get('line_id', ''),
                'line_uid': node.get('line_uid', ''),
                'branch_index': node.get('branch_index') or 0,
                'circuit_index': node.get('circuit_index'),
                'x_position': coords['x'],
                'y_position': coords['y'],
            },
        )
        saved_count += 1

    return {
        'project_id': project_id,
        'saved_count': saved_count,
        'ignored_component_ids': ignored_component_ids,
        'save_mode': 'merge',
    }


@transaction.atomic
def reset_project_sld_layout(project_id):
    deleted_count = SLDNodeLayout.objects.filter(project_id=project_id).delete()[0]
    return {
        'project_id': project_id,
        'deleted_count': deleted_count,
    }
