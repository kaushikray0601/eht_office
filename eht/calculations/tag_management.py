import hashlib


COMPONENT_TAG_PREFIXES = {
    'MCB': 'MCB',
    'Cable4C': 'CCAB4C',
    'Cable3C': 'CCAB3C',
    'Isolator3PH': 'ISOL_3PH',
    'Isolator1PH': 'ISOL_1PH',
    'JB3PH': 'JB3PH',
    'JB1PH': 'JB1PH',
    'Tracer': 'Tracer',
    'EndTermination': 'ENDTRM',
}


def _stable_component_uid(component_id):
    return hashlib.sha1(component_id.encode('utf-8')).hexdigest()[:16]


class ProjectTagFactory:
    """
    Generate project-wide display tags while preserving a stable component identity
    that is independent from human-readable tag numbering.
    """

    def __init__(self, project_id='project'):
        self.project_id = str(project_id or 'project')
        self._counters = {component_type: 1 for component_type in COMPONENT_TAG_PREFIXES}

    def create_component(
        self,
        component_type,
        *,
        line_uid,
        line_id,
        branch_index,
        sequence_index,
        circuit_index=None,
        metadata=None,
    ):
        prefix = COMPONENT_TAG_PREFIXES[component_type]
        counter_value = self._counters[component_type]
        self._counters[component_type] += 1

        display_tag = f'{prefix}_{counter_value:03d}'
        line_scope = str(line_id or line_uid or 'line')
        id_parts = [
            self.project_id,
            f'line:{line_scope}',
            f'branch:{branch_index}',
            component_type,
            f'seq:{sequence_index}',
        ]
        if circuit_index is not None:
            id_parts.append(f'ckt:{circuit_index}')
        component_id = ':'.join(id_parts)

        return {
            'component_id': component_id,
            'component_uid': _stable_component_uid(component_id),
            'display_tag': display_tag,
            'component_type': component_type,
            'project_id': self.project_id,
            'line_uid': str(line_uid),
            'line_id': line_id,
            'line_ids': [line_id] if line_id else [],
            'branch_index': branch_index,
            'circuit_index': circuit_index,
            'metadata': metadata or {},
        }


def build_connection(source_component, target_component):
    return {
        'from_component_id': source_component['component_id'],
        'to_component_id': target_component['component_id'],
        'from_display_tag': source_component['display_tag'],
        'to_display_tag': target_component['display_tag'],
        'line_ids': source_component.get('line_ids', []),
        'branch_index': source_component.get('branch_index'),
        'circuit_index': target_component.get('circuit_index'),
    }
