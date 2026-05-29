from dataclasses import dataclass, field

from .models import CableScheduleOverride, SLDTopologyEdit


LENGTH_BASIS_PRIORITY = {
    'project_default': 0,
    'topology_edit': 1,
    'manual_override': 2,
}


@dataclass
class ColdCableLengthResolution:
    """Active cold-cable length basis for one generated power branch."""
    project_id: str
    line_id: str
    line_uid: str
    branch_index: int
    branch_type: str
    circuit_count: int
    length_4c_m: float | None = None
    length_3c_m: float | None = None
    length_3c_total_m: float | None = None
    length_4c_basis: str = 'project_default'
    length_3c_basis: str = 'project_default'
    length_basis: str = 'project_default'
    cable_4c_component_id: str = ''
    cable_3c_component_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def length_missing(self):
        if self.branch_type == '3phJB' and not self.length_4c_m:
            return True
        return not self.length_3c_m


def _to_float(value):
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _project_id(project):
    return getattr(project, 'proj_id', project)


def _line(branch):
    distribution = getattr(branch, 'distribution', None)
    return getattr(distribution, 'line', None)


def _line_id(branch):
    line = _line(branch)
    return getattr(line, 'line_id', '') or ''


def _line_uid(branch):
    line = _line(branch)
    uid = getattr(line, 'uid', '')
    return str(uid or '')


def _component_detail(branch, component_type):
    tagged_components = getattr(branch, 'tagged_components', None) or {}
    return (tagged_components.get('component_details') or {}).get(component_type) or {}


def _downstream_component_details(branch, component_type):
    tagged_components = getattr(branch, 'tagged_components', None) or {}
    details = []
    for downstream in tagged_components.get('Downstream', []):
        component_details = downstream.get('component_details') or {}
        detail = component_details.get(component_type) or {}
        if detail:
            details.append(detail)
    return details


def _component_id(detail):
    return str((detail or {}).get('component_id') or '')


def _display_tag(detail):
    return str((detail or {}).get('display_tag') or '')


def _active_overrides(project_id, component_ids, display_tags):
    if not project_id:
        return {}
    if not component_ids and not display_tags:
        return {}
    overrides = CableScheduleOverride.objects.filter(project_id=project_id, is_active=True).filter(
        models_q_for_components(component_ids, display_tags)
    )
    by_key = {}
    for override in overrides:
        by_key[override.component_id] = override
        by_key[override.display_tag] = override
    return by_key


def models_q_for_components(component_ids, display_tags):
    from django.db.models import Q

    query = Q()
    if component_ids:
        query |= Q(component_id__in=component_ids)
    if display_tags:
        query |= Q(display_tag__in=display_tags)
    return query


def _manual_length_for_detail(overrides, detail):
    override = overrides.get(_component_id(detail)) or overrides.get(_display_tag(detail))
    if override and override.manual_length_m is not None:
        return float(override.manual_length_m)
    return None


def _active_topology_row(project_id, branch):
    edit = SLDTopologyEdit.objects.filter(project_id=project_id, status='applied').first()
    if edit is None:
        return None
    rows = (edit.edit_payload or {}).get('cable_schedule_rows')
    if not isinstance(rows, list):
        return None

    tagged_components = getattr(branch, 'tagged_components', None) or {}
    branch_mcb = tagged_components.get('MCB') or ''
    branch_line_id = _line_id(branch)
    branch_index = getattr(branch, 'branch_index', 0)
    for row in rows:
        row_components = row.get('tagged_components') or {}
        row_line_id = (((row.get('distribution') or {}).get('line') or {}).get('line_id') or '')
        if branch_mcb and row_components.get('MCB') == branch_mcb:
            return row
        if row.get('branch_index') == branch_index and branch_line_id and branch_line_id in row_line_id:
            return row
    return None


def _combine_basis(*basis_values):
    return max(basis_values, key=lambda basis: LENGTH_BASIS_PRIORITY.get(basis, -1))


def resolve_cable_lengths(branch, project):
    """Resolve active 4C/3C cable lengths for the first cold-cable pass.

    The service preserves the source basis because later sizing results must be
    traceable to project defaults, manual SLD overrides, or applied topology edits.
    """
    project_id = _project_id(project)
    branch_type = getattr(branch, 'branch_type', '') or ''
    circuit_count = int(getattr(branch, 'circuit_count', 0) or 0)

    cable_4c_detail = _component_detail(branch, 'Cable4C')
    cable_3c_details = _downstream_component_details(branch, 'Cable3C')
    component_ids = [_component_id(cable_4c_detail), *[_component_id(detail) for detail in cable_3c_details]]
    display_tags = [_display_tag(cable_4c_detail), *[_display_tag(detail) for detail in cable_3c_details]]
    component_ids = [value for value in component_ids if value]
    display_tags = [value for value in display_tags if value]
    overrides = _active_overrides(project_id, component_ids, display_tags)

    length_4c_m = None
    length_4c_basis = 'project_default'
    manual_4c = _manual_length_for_detail(overrides, cable_4c_detail)
    if manual_4c is not None:
        length_4c_m = manual_4c
        length_4c_basis = 'manual_override'

    manual_3c_lengths = [
        length for length in (_manual_length_for_detail(overrides, detail) for detail in cable_3c_details)
        if length is not None
    ]
    length_3c_m = None
    length_3c_total_m = None
    length_3c_basis = 'project_default'
    if manual_3c_lengths:
        length_3c_m = max(manual_3c_lengths)
        length_3c_total_m = sum(manual_3c_lengths)
        length_3c_basis = 'manual_override'

    topology_row = _active_topology_row(project_id, branch)
    if topology_row and length_4c_basis != 'manual_override':
        topology_4c = _to_float(topology_row.get('cable_length_db_to_jb'))
        if topology_4c is not None:
            length_4c_m = topology_4c
            length_4c_basis = 'topology_edit'
    if topology_row and length_3c_basis != 'manual_override':
        topology_3c_total = _to_float(topology_row.get('branch_cable_length_total_m'))
        topology_3c = _to_float(topology_row.get('cable_length_jb_to_jb'))
        if topology_3c is None and topology_3c_total is not None and circuit_count:
            topology_3c = topology_3c_total / circuit_count
        if topology_3c is not None:
            length_3c_m = topology_3c
            length_3c_total_m = topology_3c_total if topology_3c_total is not None else topology_3c * max(circuit_count, 1)
            length_3c_basis = 'topology_edit'

    if length_4c_m is None:
        length_4c_m = _to_float(getattr(branch, 'cable_length_db_to_jb', None)) if branch_type == '3phJB' else None
    if length_3c_m is None:
        fallback_3c = (
            getattr(branch, 'cable_length_jb_to_jb', None)
            if branch_type == '3phJB'
            else getattr(branch, 'cable_length_db_to_jb', None)
        )
        length_3c_m = _to_float(fallback_3c)
    if length_3c_total_m is None and length_3c_m is not None:
        length_3c_total_m = length_3c_m * max(circuit_count, 1)

    warnings = []
    if branch_type == '3phJB' and not length_4c_m:
        warnings.append('4C trunk cable length is missing.')
    if not length_3c_m:
        warnings.append('3C outgoing cable length is missing.')

    return ColdCableLengthResolution(
        project_id=project_id,
        line_id=_line_id(branch),
        line_uid=_line_uid(branch),
        branch_index=int(getattr(branch, 'branch_index', 0) or 0),
        branch_type=branch_type,
        circuit_count=circuit_count,
        length_4c_m=length_4c_m,
        length_3c_m=length_3c_m,
        length_3c_total_m=length_3c_total_m,
        length_4c_basis=length_4c_basis,
        length_3c_basis=length_3c_basis,
        length_basis=_combine_basis(length_4c_basis, length_3c_basis),
        cable_4c_component_id=_component_id(cable_4c_detail),
        cable_3c_component_ids=[_component_id(detail) for detail in cable_3c_details if _component_id(detail)],
        warnings=warnings,
    )
