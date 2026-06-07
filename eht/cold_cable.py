from dataclasses import dataclass, field
import math

from .models import (
    CABLE_GROUPING_DERATING_MAX,
    CABLE_GROUPING_DERATING_MIN,
    CABLE_INSTALL_METHOD_CHOICES,
    CableScheduleOverride,
    ColdCableCatalogue,
    ColdCableResult,
    ProjectData,
    PowerDistributionBranch,
    SLDTopologyEdit,
)


LENGTH_BASIS_PRIORITY = {
    'project_default': 0,
    'topology_edit': 1,
    'manual_override': 2,
}
MCB_INSTANTANEOUS_FACTORS = {
    'B': 3.0,
    'C': 5.0,
    'D': 10.0,
}
CONDUCTOR_TEMP_COEFFICIENTS = {
    'Cu': 0.00393,
}
CONDUCTOR_DENSITY_KG_M3 = {
    'Cu': 8960.0,
}
INSULATION_CONDUCTOR_TEMPERATURE_C = {
    'PVC': 70.0,
    'XLPE': 90.0,
}
TRACER_PE_FAULT_LOOP_NOTE = (
    'Tracer PE-path resistance is deferred and not included; this overestimates earth-fault current and is non-conservative.'
)
PHASE_SLOT_LABELS = ('L1', 'L2', 'L3')
PHASE_SLOT_BASIS = 'round_robin_by_outgoing_circuit_index'


def _phase_slot_for_circuit(circuit_index):
    try:
        normalized_index = int(circuit_index)
    except (TypeError, ValueError):
        return None, ''
    if normalized_index < 1:
        return None, ''
    slot = ((normalized_index - 1) % len(PHASE_SLOT_LABELS)) + 1
    return slot, PHASE_SLOT_LABELS[slot - 1]


@dataclass
class ColdCable3CSegmentLength:
    component_id: str
    display_tag: str
    circuit_index: int | None
    length_m: float | None
    length_basis: str


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
    length_3c_segments: list[ColdCable3CSegmentLength] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def length_missing(self):
        if self.branch_type == '3phJB' and not self.length_4c_m:
            return True
        if self.length_3c_segments:
            return any(not segment.length_m for segment in self.length_3c_segments)
        return not self.length_3c_m


@dataclass
class ColdCableSizingInput:
    project_id: str
    line_id: str
    line_uid: str
    branch_index: int
    branch_type: str
    circuit_count: int
    heating_cable_type: str
    per_circuit_operating_current_a: float
    line_operating_current_a: float
    breaker_size_a: float
    length_4c_m: float | None
    length_3c_m: float | None
    length_basis: str
    length_missing: bool
    length_3c_segments: list[ColdCable3CSegmentLength] = field(default_factory=list)
    review_notes: list[str] = field(default_factory=list)


@dataclass
class AmpacitySelection:
    catalogue: ColdCableCatalogue | None
    core_count: int
    required_current_a: float
    k_temp: float | None = None
    k_group: float | None = None
    k_total: float | None = None
    derated_ampacity_a: float | None = None
    ampacity_margin_pct: float | None = None
    status: str = 'selected'
    review_notes: list[str] = field(default_factory=list)


@dataclass
class VoltageDropResult:
    vd_v: float
    vd_pct: float


@dataclass
class CableCandidate:
    selection: AmpacitySelection
    resistance_mohm_per_m_at_temp: float
    conductor_temp_c: float
    vd: VoltageDropResult | None = None


@dataclass
class FaultProtectionResult:
    status: str
    fault_current_a: float | None = None
    threshold_current_a: float | None = None
    review_notes: list[str] = field(default_factory=list)


@dataclass
class CablePairOptimisation:
    status: str
    selection_4c: AmpacitySelection | None = None
    selection_3c: AmpacitySelection | None = None
    conductor_temp_4c_c: float | None = None
    conductor_temp_3c_c: float | None = None
    vd_4c: VoltageDropResult | None = None
    vd_3c: VoltageDropResult | None = None
    vd_total_pct: float | None = None
    load_end_voltage_v: float | None = None
    conductor_volume_proxy: float | None = None
    fault_4c: FaultProtectionResult | None = None
    fault_3c: FaultProtectionResult | None = None
    segment_3c_results: list[dict] = field(default_factory=list)
    review_notes: list[str] = field(default_factory=list)


def _to_float(value):
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_float(value):
    value = _to_float(value)
    if value is None or value <= 0:
        return None
    return value


def _project_id(project):
    return getattr(project, 'proj_id', project)


def _project(project):
    if isinstance(project, ProjectData):
        return project
    return ProjectData.objects.get(proj_id=project)


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


def _component_metadata(branch, component_type):
    return _component_detail(branch, component_type).get('metadata') or {}


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
        if row.get('branch_index') == branch_index and branch_line_id and branch_line_id == row_line_id:
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

    length_3c_m = None
    length_3c_total_m = None
    length_3c_basis = 'project_default'

    topology_row = _active_topology_row(project_id, branch)
    if topology_row and branch_type == '3phJB' and length_4c_basis != 'manual_override':
        topology_4c = _positive_float(topology_row.get('cable_length_db_to_jb'))
        if topology_4c is not None:
            length_4c_m = topology_4c
            length_4c_basis = 'topology_edit'
    topology_3c = None
    topology_3c_total = None
    if topology_row:
        topology_3c_total = _positive_float(topology_row.get('branch_cable_length_total_m'))
        if branch_type == '3phJB':
            topology_3c = _positive_float(topology_row.get('cable_length_jb_to_jb'))
            if topology_3c is None and topology_3c_total is not None and circuit_count:
                topology_3c = topology_3c_total / circuit_count
        else:
            # Direct 1Ph branches use the MCB-to-load route as the 3C cable length.
            topology_3c = _positive_float(topology_row.get('cable_length_db_to_jb'))

    if length_4c_m is None:
        length_4c_m = _to_float(getattr(branch, 'cable_length_db_to_jb', None)) if branch_type == '3phJB' else None
    fallback_3c = (
        getattr(branch, 'cable_length_jb_to_jb', None)
        if branch_type == '3phJB'
        else getattr(branch, 'cable_length_db_to_jb', None)
    )
    fallback_3c = _to_float(fallback_3c)
    if not cable_3c_details:
        cable_3c_details = [{}]
    length_3c_segments = []
    for index, detail in enumerate(cable_3c_details, start=1):
        manual_3c = _manual_length_for_detail(overrides, detail)
        if manual_3c is not None:
            segment_length = manual_3c
            segment_basis = 'manual_override'
        elif topology_3c is not None:
            segment_length = topology_3c
            segment_basis = 'topology_edit'
        else:
            segment_length = fallback_3c
            segment_basis = 'project_default'
        length_3c_segments.append(
            ColdCable3CSegmentLength(
                component_id=_component_id(detail),
                display_tag=_display_tag(detail),
                circuit_index=(detail or {}).get('circuit_index') or index,
                length_m=segment_length,
                length_basis=segment_basis,
            )
        )

    segment_lengths = [segment.length_m for segment in length_3c_segments if segment.length_m is not None]
    if segment_lengths:
        length_3c_m = max(segment_lengths)
        length_3c_total_m = sum(segment_lengths)
        length_3c_basis = _combine_basis(*(segment.length_basis for segment in length_3c_segments))

    warnings = []
    if branch_type == '3phJB' and not length_4c_m:
        warnings.append('4C trunk cable length is missing.')
    if not length_3c_segments or any(not segment.length_m for segment in length_3c_segments):
        warnings.append('One or more 3C outgoing cable lengths are missing.')

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
        length_3c_segments=length_3c_segments,
        warnings=warnings,
    )


def _process_line_calculation(branch):
    line = _line(branch)
    return getattr(line, 'process_line_calculation', None)


def _numeric_metadata_value(metadata, *keys):
    for key in keys:
        value = _to_float(metadata.get(key))
        if value is not None:
            return value
    return None


def _heating_cable_type(branch):
    tagged_components = getattr(branch, 'tagged_components', None) or {}
    mcb_metadata = _component_metadata(branch, 'MCB')
    value = (
        tagged_components.get('heating_cable_type')
        or mcb_metadata.get('heating_cable_type')
        or ''
    )
    if value:
        return str(value).upper()
    line = _line(branch)
    if line and hasattr(line, 'selected_mi_heater_result'):
        mi_result = getattr(line, 'selected_mi_heater_result', None)
        if mi_result and mi_result.selection_status == 'selected':
            return 'MI'
    return 'SR'


def build_cold_cable_sizing_input(branch, project):
    project = _project(project)
    mcb_metadata = _component_metadata(branch, 'MCB')
    calculation = _process_line_calculation(branch)
    length_resolution = resolve_cable_lengths(branch, project)

    per_circuit_current = _numeric_metadata_value(mcb_metadata, 'operating_current', 'per_circuit_operating_current')
    if per_circuit_current is None and calculation is not None:
        per_circuit_current = _to_float(calculation.operating_current)
    line_current = _numeric_metadata_value(mcb_metadata, 'line_operating_current')
    if line_current is None and calculation is not None:
        # Fallback only: total_power_consumption / voltage gives approximate line current
        # for single-phase unity-PF loads. Sizing uses per_circuit_operating_current_a.
        line_current = _to_float(calculation.total_power_consumption)
        if line_current and project.voltage:
            line_current = line_current / float(project.voltage)
    breaker_size = _numeric_metadata_value(mcb_metadata, 'breaker_size')
    if breaker_size is None and calculation is not None:
        breaker_size = _to_float(calculation.breaker_size)

    review_notes = list(length_resolution.warnings)
    if length_resolution.length_basis == 'project_default':
        review_notes.append('Cable length is based on project default route length.')

    return ColdCableSizingInput(
        project_id=project.proj_id,
        line_id=length_resolution.line_id,
        line_uid=length_resolution.line_uid,
        branch_index=length_resolution.branch_index,
        branch_type=length_resolution.branch_type,
        circuit_count=length_resolution.circuit_count,
        heating_cable_type=_heating_cable_type(branch),
        per_circuit_operating_current_a=per_circuit_current or 0.0,
        line_operating_current_a=line_current or 0.0,
        breaker_size_a=breaker_size or 0.0,
        length_4c_m=length_resolution.length_4c_m,
        length_3c_m=length_resolution.length_3c_m,
        length_basis=length_resolution.length_basis,
        length_missing=length_resolution.length_missing,
        length_3c_segments=length_resolution.length_3c_segments,
        review_notes=review_notes,
    )


def calculate_k_temp(site_ambient_c, catalogue_ref_temp_c, max_conductor_temp_c):
    site_ambient = float(site_ambient_c)
    catalogue_ref = float(catalogue_ref_temp_c)
    max_conductor = float(max_conductor_temp_c)
    denominator = max_conductor - catalogue_ref
    numerator = max_conductor - site_ambient
    if denominator <= 0:
        raise ValueError('Catalogue reference temperature must be below maximum conductor temperature.')
    if numerator <= 0:
        raise ValueError('Site ambient temperature must be below maximum conductor temperature.')
    return math.sqrt(numerator / denominator)


def _minimum_cable_size(project):
    value = getattr(project, 'min_cold_cable_size_mm2', 'CALCULATED') or 'CALCULATED'
    if value == 'CALCULATED':
        return None
    return float(value)


def _catalogue_rows(project, core_count):
    rows = ColdCableCatalogue.objects.filter(
        cable_standard=project.cable_standard,
        conductor_material=project.cable_conductor_material,
        insulation_type=project.cable_insulation_type,
        installation_method=project.cable_install_method,
        core_count=core_count,
        is_validated=True,
    ).order_by('conductor_size_mm2')
    minimum_size = _minimum_cable_size(project)
    if minimum_size is not None:
        rows = rows.filter(conductor_size_mm2__gte=minimum_size)
    return rows


def _installation_method_label(method):
    return dict(CABLE_INSTALL_METHOD_CHOICES).get(method, method)


def find_minimum_cable_for_ampacity(project, core_count, required_current_a):
    project = _project(project)
    required_current = float(required_current_a or 0.0)
    if required_current <= 0:
        return AmpacitySelection(
            catalogue=None,
            core_count=core_count,
            required_current_a=required_current,
            status='unsizeable',
            review_notes=['Operating current must be greater than zero for cold-cable ampacity sizing.'],
        )

    rows = list(_catalogue_rows(project, core_count))
    if not rows:
        method = getattr(project, 'cable_install_method', '')
        return AmpacitySelection(
            catalogue=None,
            core_count=core_count,
            required_current_a=required_current,
            status='unsizeable',
            review_notes=[
                (
                    'No validated cold-cable catalogue rows match the project cable basis '
                    f'for {core_count}C, {project.cable_standard}/{project.cable_conductor_material}/'
                    f'{project.cable_insulation_type}, installation method {method} '
                    f'({_installation_method_label(method)}). Select a catalogue-ready method '
                    'or add and validate catalogue rows before using this basis.'
                ),
            ],
        )

    thermal_notes = []
    k_group, grouping_note = _project_grouping_derating(project)
    for row in rows:
        try:
            k_temp = calculate_k_temp(project.max_amb_t, row.ampacity_temp_ref_c, row.max_conductor_temp_c)
        except ValueError as exc:
            thermal_notes.append(str(exc))
            continue
        k_total = k_temp * k_group
        derated_ampacity = row.ampacity_a * k_total
        if derated_ampacity >= required_current:
            return AmpacitySelection(
                catalogue=row,
                core_count=core_count,
                required_current_a=required_current,
                k_temp=k_temp,
                k_group=k_group,
                k_total=k_total,
                derated_ampacity_a=derated_ampacity,
                ampacity_margin_pct=((derated_ampacity - required_current) / required_current) * 100,
                status='selected',
                review_notes=[grouping_note] if grouping_note else [],
            )

    notes = ['No validated cold-cable catalogue row satisfies ampacity after temperature and grouping derating.']
    if grouping_note:
        notes.append(grouping_note)
    notes.extend(sorted(set(thermal_notes)))
    return AmpacitySelection(
        catalogue=None,
        core_count=core_count,
        required_current_a=required_current,
        status='unsizeable',
        review_notes=notes,
    )


def _ampacity_selection_for_row(project, row, required_current):
    k_temp = calculate_k_temp(project.max_amb_t, row.ampacity_temp_ref_c, row.max_conductor_temp_c)
    k_group, grouping_note = _project_grouping_derating(project)
    k_total = k_temp * k_group
    derated_ampacity = row.ampacity_a * k_total
    if derated_ampacity < required_current:
        return None
    return AmpacitySelection(
        catalogue=row,
        core_count=row.core_count,
        required_current_a=required_current,
        k_temp=k_temp,
        k_group=k_group,
        k_total=k_total,
        derated_ampacity_a=derated_ampacity,
        ampacity_margin_pct=((derated_ampacity - required_current) / required_current) * 100,
        status='selected',
        review_notes=[grouping_note] if grouping_note else [],
    )


def _ampacity_candidates(project, core_count, required_current_a):
    project = _project(project)
    required_current = float(required_current_a or 0.0)
    if required_current <= 0:
        return []

    candidates = []
    for row in _catalogue_rows(project, core_count):
        try:
            selection = _ampacity_selection_for_row(project, row, required_current)
            conductor_temp = conductor_operating_temperature(row)
            resistance_at_temp = get_conductor_resistance_at_temp(row, conductor_temp)
        except ValueError:
            continue
        if selection is None:
            continue
        candidates.append(CableCandidate(
            selection=selection,
            resistance_mohm_per_m_at_temp=resistance_at_temp,
            conductor_temp_c=conductor_temp,
        ))
    return candidates


def conductor_operating_temperature(row):
    insulation_type = str(getattr(row, 'insulation_type', '') or '').upper()
    if insulation_type in INSULATION_CONDUCTOR_TEMPERATURE_C:
        return INSULATION_CONDUCTOR_TEMPERATURE_C[insulation_type]
    raise ValueError("Insulation type must be 'XLPE' or 'PVC'.")


def conductor_temperature_coefficient(conductor_material):
    material = str(conductor_material or '').strip()
    if material not in CONDUCTOR_TEMP_COEFFICIENTS:
        raise ValueError("Conductor material must be 'Cu'.")
    return CONDUCTOR_TEMP_COEFFICIENTS[material]


def conductor_density_kg_m3(conductor_material):
    material = str(conductor_material or '').strip()
    if material not in CONDUCTOR_DENSITY_KG_M3:
        raise ValueError("Conductor material must be 'Cu'.")
    return CONDUCTOR_DENSITY_KG_M3[material]


def get_conductor_resistance_at_temp(row, conductor_temp_c, alpha=None):
    if alpha is None:
        alpha = conductor_temperature_coefficient(getattr(row, 'conductor_material', 'Cu'))
    return float(row.resistance_mohm_per_m) * (1 + float(alpha) * (float(conductor_temp_c) - 20.0))


def calculate_vd(current_a, resistance_mohm_per_m, length_m, circuit_type, nominal_voltage_v):
    circuit_type = str(circuit_type or '').casefold()
    if circuit_type in {'3phase', '3ph', 'three_phase'}:
        factor = math.sqrt(3)
    elif circuit_type in {'1phase', '1ph', 'single_phase'}:
        factor = 2.0
    else:
        raise ValueError("circuit_type must be '1phase' or '3phase'.")
    nominal_voltage = float(nominal_voltage_v)
    if nominal_voltage <= 0:
        raise ValueError('Nominal voltage must be greater than zero for voltage-drop calculation.')
    vd_v = factor * float(current_a) * (float(resistance_mohm_per_m) / 1000.0) * float(length_m)
    return VoltageDropResult(vd_v=vd_v, vd_pct=(vd_v / nominal_voltage) * 100.0)


def mcb_instantaneous_factor(mcb_curve):
    curve = str(mcb_curve or '').upper()
    if curve not in MCB_INSTANTANEOUS_FACTORS:
        raise ValueError("MCB curve must be one of 'B', 'C', or 'D'.")
    return MCB_INSTANTANEOUS_FACTORS[curve]


def _fault_threshold_current(breaker_size_a, mcb_curve):
    breaker_size = float(breaker_size_a or 0.0)
    if breaker_size <= 0:
        raise ValueError('Breaker size must be greater than zero for fault-protection check.')
    return mcb_instantaneous_factor(mcb_curve) * breaker_size


def _fault_resistance_mohm_per_m(row, conductor_temp_c=None):
    conductor_temp = float(conductor_temp_c) if conductor_temp_c is not None else conductor_operating_temperature(row)
    return get_conductor_resistance_at_temp(row, conductor_temp)


def check_fault_4c(row_4c, length_4c_m, nominal_voltage_v, breaker_size_a, mcb_curve, conductor_temp_c=None):
    length = float(length_4c_m or 0.0)
    if length <= 0:
        return FaultProtectionResult(status='not_calculated', review_notes=['4C cable length is required for fault check.'])
    threshold = _fault_threshold_current(breaker_size_a, mcb_curve)
    r_ohm_per_m = _fault_resistance_mohm_per_m(row_4c, conductor_temp_c) / 1000.0
    fault_current = float(nominal_voltage_v) * math.sqrt(3) / (2 * r_ohm_per_m * length)
    return FaultProtectionResult(
        status='pass' if fault_current >= threshold else 'fail',
        fault_current_a=fault_current,
        threshold_current_a=threshold,
    )


def check_fault_3c(row_3c, length_3c_m, nominal_voltage_v, breaker_size_a, mcb_curve, rcd_provided, conductor_temp_c=None):
    length = float(length_3c_m or 0.0)
    if length <= 0:
        return FaultProtectionResult(status='not_calculated', review_notes=['3C cable length is required for fault check.'])
    threshold = _fault_threshold_current(breaker_size_a, mcb_curve)
    r_ohm_per_m = _fault_resistance_mohm_per_m(row_3c, conductor_temp_c) / 1000.0
    fault_current = float(nominal_voltage_v) / (2 * r_ohm_per_m * length)
    status = 'pass'
    if fault_current < threshold:
        status = 'review_required' if rcd_provided else 'fail'
    return FaultProtectionResult(
        status=status,
        fault_current_a=fault_current,
        threshold_current_a=threshold,
        review_notes=[TRACER_PE_FAULT_LOOP_NOTE],
    )


def _append_unique(notes, additions):
    for note in additions:
        if note and note not in notes:
            notes.append(note)


def _project_grouping_derating(project):
    raw_value = float(project.cable_grouping_derating)
    effective_value = min(max(raw_value, CABLE_GROUPING_DERATING_MIN), CABLE_GROUPING_DERATING_MAX)
    if effective_value != raw_value:
        return effective_value, (
            f'Cable grouping derating {raw_value:g} is outside the allowed range; '
            f'{effective_value:g} used for cold-cable sizing.'
        )
    return effective_value, ''


def _cable_cost_proxy(sizing_input, selection_4c=None, selection_3c=None):
    cost = 0.0
    if selection_4c and sizing_input.length_4c_m:
        cost += 4 * selection_4c.catalogue.conductor_size_mm2 * float(sizing_input.length_4c_m)
    if selection_3c and sizing_input.length_3c_m:
        cost += (
            max(1, int(sizing_input.circuit_count or 1))
            * 3
            * selection_3c.catalogue.conductor_size_mm2
            * float(sizing_input.length_3c_m)
        )
    return cost or None


def _segment_cost_proxy(selection, length_m):
    if not selection or not selection.catalogue or not length_m:
        return 0.0
    return 3 * selection.catalogue.conductor_size_mm2 * float(length_m)


def _selection_mass_mt(selection, length_m, parallel_count=1):
    if not selection or not selection.catalogue or not length_m:
        return None
    density = conductor_density_kg_m3(selection.catalogue.conductor_material)
    volume_m3 = (
        int(parallel_count or 1)
        * selection.catalogue.core_count
        * selection.catalogue.conductor_size_mm2
        * float(length_m)
        * 1e-6
    )
    return volume_m3 * density / 1000.0


def _total_mass_mt(*masses):
    values = [mass for mass in masses if mass is not None]
    if not values:
        return None
    return sum(values)


def _active_3c_segments(sizing_input):
    if sizing_input.length_3c_segments:
        return sizing_input.length_3c_segments
    return [
        ColdCable3CSegmentLength(
            component_id='',
            display_tag='',
            circuit_index=index,
            length_m=sizing_input.length_3c_m,
            length_basis=sizing_input.length_basis,
        )
        for index in range(1, max(1, int(sizing_input.circuit_count or 1)) + 1)
    ]


def _catalogue_id(row):
    return row.pk if row and row.pk is not None else None


def _segment_result_payload(segment, selection, conductor_temp_c, vd_3c, vd_4c, fault, nominal_voltage):
    vd_4c_v = vd_4c.vd_v if vd_4c else 0.0
    vd_4c_pct = vd_4c.vd_pct if vd_4c else 0.0
    vd_total_v = vd_4c_v + vd_3c.vd_v
    vd_total_pct = vd_4c_pct + vd_3c.vd_pct
    mass_mt = _selection_mass_mt(selection, segment.length_m)
    phase_slot, phase_label = _phase_slot_for_circuit(segment.circuit_index)
    return {
        'component_id': segment.component_id,
        'display_tag': segment.display_tag,
        'circuit_index': segment.circuit_index,
        'phase_slot': phase_slot,
        'phase_label': phase_label,
        'phase_basis': PHASE_SLOT_BASIS if phase_slot else '',
        'length_m': segment.length_m,
        'length_basis': segment.length_basis,
        'catalogue_id': _catalogue_id(selection.catalogue),
        'size_mm2': selection.catalogue.conductor_size_mm2,
        'ampacity_derated_a': selection.derated_ampacity_a,
        'ampacity_margin_pct': selection.ampacity_margin_pct,
        'conductor_temp_c': conductor_temp_c,
        'conductor_mass_mt': mass_mt,
        'vd_v': vd_3c.vd_v,
        'vd_pct': vd_3c.vd_pct,
        'vd_total_pct': vd_total_pct,
        'load_end_voltage_v': nominal_voltage - vd_total_v,
        'fault_current_a': fault.fault_current_a,
        'fault_status': fault.status,
        'sizing_status': 'review_required' if fault.status == 'review_required' else 'selected',
        'k_temp': selection.k_temp,
        'k_group': selection.k_group,
        'k_total': selection.k_total,
        'review_notes': list(fault.review_notes),
    }


def _select_3c_segment_for_voltage_drop(project, sizing_input, segment, vd_4c=None):
    current = float(sizing_input.per_circuit_operating_current_a or 0.0)
    nominal_voltage = float(project.voltage)
    allowable_vd_pct = float(project.allowablevdrop)
    if not segment.length_m:
        return None, ['3C outgoing cable length is missing.']

    candidates = _ampacity_candidates(project, 3, current)
    if not candidates:
        notes = ['No ampacity-qualified 3C cable is available for the outgoing branch.']
        _append_unique(notes, find_minimum_cable_for_ampacity(project, 3, current).review_notes)
        return None, notes

    vd_4c_pct = vd_4c.vd_pct if vd_4c else 0.0
    notes = []
    for candidate in candidates:
        vd_3c = calculate_vd(
            current,
            candidate.resistance_mohm_per_m_at_temp,
            segment.length_m,
            '1phase',
            nominal_voltage,
        )
        if vd_4c_pct + vd_3c.vd_pct > allowable_vd_pct:
            continue
        fault = check_fault_3c(
            candidate.selection.catalogue,
            segment.length_m,
            nominal_voltage,
            sizing_input.breaker_size_a,
            project.mcb_curve,
            project.rcd_provided,
            conductor_temp_c=candidate.conductor_temp_c,
        )
        _append_unique(notes, fault.review_notes)
        if fault.status == 'fail':
            continue
        return _segment_result_payload(
            segment,
            candidate.selection,
            candidate.conductor_temp_c,
            vd_3c,
            vd_4c,
            fault,
            nominal_voltage,
        ), notes

    failure_note = (
        'No 3C cable satisfies ampacity, voltage-drop, and fault-protection constraints '
        'for one outgoing branch.'
    )
    if not project.rcd_provided:
        failure_note = 'No 3C cable satisfies the breaker instantaneous fault threshold without RCD protection.'
    notes.append(failure_note)
    return None, notes


def _selection_from_segment_result(project, segment_result, required_current_a):
    if not segment_result or not segment_result.get('catalogue_id'):
        return None
    row = ColdCableCatalogue.objects.filter(pk=segment_result['catalogue_id']).first()
    if row is None:
        return None
    return _ampacity_selection_for_row(project, row, float(required_current_a or 0.0))


def _critical_3c_segment(segment_results):
    if not segment_results:
        return None
    return max(
        segment_results,
        key=lambda item: (
            float(item.get('size_mm2') or 0),
            float(item.get('vd_total_pct') or 0),
            float(item.get('length_m') or 0),
        ),
    )


def _apply_4c_fault_check(project, sizing_input, sizing_result):
    if not sizing_result.selection_4c or not sizing_input.length_4c_m:
        return sizing_result

    current = float(sizing_input.per_circuit_operating_current_a or 0.0)
    nominal_voltage = float(project.voltage)
    allowable_vd_pct = float(project.allowablevdrop)
    selected_size = sizing_result.selection_4c.catalogue.conductor_size_mm2
    candidates = [
        candidate for candidate in _ampacity_candidates(project, 4, current)
        if candidate.selection.catalogue.conductor_size_mm2 >= selected_size
    ]
    for candidate in candidates:
        vd_4c = calculate_vd(
            current,
            candidate.resistance_mohm_per_m_at_temp,
            sizing_input.length_4c_m,
            '3phase',
            nominal_voltage,
        )
        vd_total_pct = vd_4c.vd_pct + (sizing_result.vd_3c.vd_pct if sizing_result.vd_3c else 0.0)
        if vd_total_pct > allowable_vd_pct:
            continue
        fault = check_fault_4c(
            candidate.selection.catalogue,
            sizing_input.length_4c_m,
            nominal_voltage,
            sizing_input.breaker_size_a,
            project.mcb_curve,
            conductor_temp_c=candidate.conductor_temp_c,
        )
        if fault.status == 'pass':
            sizing_result.selection_4c = candidate.selection
            sizing_result.conductor_temp_4c_c = candidate.conductor_temp_c
            sizing_result.vd_4c = vd_4c
            sizing_result.vd_total_pct = vd_total_pct
            sizing_result.load_end_voltage_v = nominal_voltage - vd_4c.vd_v - (sizing_result.vd_3c.vd_v if sizing_result.vd_3c else 0.0)
            sizing_result.conductor_volume_proxy = _cable_cost_proxy(
                sizing_input,
                sizing_result.selection_4c,
                sizing_result.selection_3c,
            )
            sizing_result.fault_4c = fault
            return sizing_result

    sizing_result.status = 'unsizeable'
    sizing_result.fault_4c = FaultProtectionResult(status='fail')
    _append_unique(sizing_result.review_notes, ['No 4C cable satisfies the breaker instantaneous fault threshold.'])
    return sizing_result


def _apply_3c_fault_check(project, sizing_input, sizing_result):
    if not sizing_result.selection_3c or not sizing_input.length_3c_m:
        return sizing_result

    current = float(sizing_input.per_circuit_operating_current_a or 0.0)
    nominal_voltage = float(project.voltage)
    allowable_vd_pct = float(project.allowablevdrop)
    selected_size = sizing_result.selection_3c.catalogue.conductor_size_mm2

    if project.rcd_provided:
        conductor_temp = sizing_result.conductor_temp_3c_c
        fault = check_fault_3c(
            sizing_result.selection_3c.catalogue,
            sizing_input.length_3c_m,
            nominal_voltage,
            sizing_input.breaker_size_a,
            project.mcb_curve,
            True,
            conductor_temp_c=conductor_temp,
        )
        sizing_result.fault_3c = fault
        _append_unique(sizing_result.review_notes, fault.review_notes)
        if fault.status == 'review_required' and sizing_result.status == 'selected':
            sizing_result.status = 'review_required'
        return sizing_result

    candidates = [
        candidate for candidate in _ampacity_candidates(project, 3, current)
        if candidate.selection.catalogue.conductor_size_mm2 >= selected_size
    ]
    for candidate in candidates:
        vd_3c = calculate_vd(
            current,
            candidate.resistance_mohm_per_m_at_temp,
            sizing_input.length_3c_m,
            '1phase',
            nominal_voltage,
        )
        vd_total_pct = (sizing_result.vd_4c.vd_pct if sizing_result.vd_4c else 0.0) + vd_3c.vd_pct
        if vd_total_pct > allowable_vd_pct:
            continue
        fault = check_fault_3c(
            candidate.selection.catalogue,
            sizing_input.length_3c_m,
            nominal_voltage,
            sizing_input.breaker_size_a,
            project.mcb_curve,
            False,
            conductor_temp_c=candidate.conductor_temp_c,
        )
        _append_unique(sizing_result.review_notes, fault.review_notes)
        if fault.status == 'pass':
            sizing_result.selection_3c = candidate.selection
            sizing_result.conductor_temp_3c_c = candidate.conductor_temp_c
            sizing_result.vd_3c = vd_3c
            sizing_result.vd_total_pct = vd_total_pct
            sizing_result.load_end_voltage_v = nominal_voltage - (sizing_result.vd_4c.vd_v if sizing_result.vd_4c else 0.0) - vd_3c.vd_v
            sizing_result.conductor_volume_proxy = _cable_cost_proxy(
                sizing_input,
                sizing_result.selection_4c,
                sizing_result.selection_3c,
            )
            sizing_result.fault_3c = fault
            return sizing_result

    sizing_result.status = 'unsizeable'
    sizing_result.fault_3c = FaultProtectionResult(status='fail', review_notes=[TRACER_PE_FAULT_LOOP_NOTE])
    _append_unique(sizing_result.review_notes, [
        TRACER_PE_FAULT_LOOP_NOTE,
        'No 3C cable satisfies the breaker instantaneous fault threshold without RCD protection.',
    ])
    return sizing_result


def apply_fault_protection_checks(project, sizing_input, sizing_result):
    if sizing_result.status not in {'selected', 'review_required'}:
        return sizing_result
    if sizing_result.segment_3c_results:
        return sizing_result
    sizing_result = _apply_4c_fault_check(project, sizing_input, sizing_result)
    if sizing_result.status == 'unsizeable':
        return sizing_result
    return _apply_3c_fault_check(project, sizing_input, sizing_result)


def optimise_cable_pair(project, sizing_input):
    project = _project(project)
    current = float(sizing_input.per_circuit_operating_current_a or 0.0)
    if current <= 0:
        return CablePairOptimisation(
            status='unsizeable',
            review_notes=['Operating current must be greater than zero for voltage-drop sizing.'],
        )
    segments = _active_3c_segments(sizing_input)
    if not sizing_input.length_4c_m or any(not segment.length_m for segment in segments):
        return CablePairOptimisation(
            status='length_missing',
            review_notes=['4C and all 3C outgoing cable lengths are required for 3phJB voltage-drop optimisation.'],
        )

    candidates_4c = _ampacity_candidates(project, 4, current)
    candidates_3c = _ampacity_candidates(project, 3, current)
    if not candidates_4c or not candidates_3c:
        review_notes = ['No ampacity-qualified 4C/3C cable pair is available for voltage-drop optimisation.']
        if not candidates_4c:
            _append_unique(review_notes, find_minimum_cable_for_ampacity(project, 4, current).review_notes)
        if not candidates_3c:
            _append_unique(review_notes, find_minimum_cable_for_ampacity(project, 3, current).review_notes)
        return CablePairOptimisation(
            status='unsizeable',
            review_notes=review_notes,
        )

    best = None
    nominal_voltage = float(project.voltage)
    allowable_vd_pct = float(project.allowablevdrop)
    for candidate_4c in candidates_4c:
        vd_4c = calculate_vd(
            current,
            candidate_4c.resistance_mohm_per_m_at_temp,
            sizing_input.length_4c_m,
            '3phase',
            nominal_voltage,
        )
        if vd_4c.vd_pct >= allowable_vd_pct:
            continue
        fault_4c = check_fault_4c(
            candidate_4c.selection.catalogue,
            sizing_input.length_4c_m,
            nominal_voltage,
            sizing_input.breaker_size_a,
            project.mcb_curve,
            conductor_temp_c=candidate_4c.conductor_temp_c,
        )
        if fault_4c.status != 'pass':
            continue

        segment_results = []
        review_notes = list(candidate_4c.selection.review_notes)
        option_cost = 4 * candidate_4c.selection.catalogue.conductor_size_mm2 * float(sizing_input.length_4c_m)
        for segment in segments:
            segment_result, segment_notes = _select_3c_segment_for_voltage_drop(
                project,
                sizing_input,
                segment,
                vd_4c=vd_4c,
            )
            _append_unique(review_notes, segment_notes)
            if segment_result is None:
                break
            segment_results.append(segment_result)
            option_cost += _segment_cost_proxy(
                _selection_from_segment_result(project, segment_result, current),
                segment.length_m,
            )
        if len(segment_results) != len(segments):
            continue

        critical_segment = _critical_3c_segment(segment_results)
        selection_3c = _selection_from_segment_result(project, critical_segment, current)
        status = 'review_required' if any(item.get('sizing_status') == 'review_required' for item in segment_results) else 'selected'
        option = CablePairOptimisation(
            status=status,
            selection_4c=candidate_4c.selection,
            selection_3c=selection_3c,
            conductor_temp_4c_c=candidate_4c.conductor_temp_c,
            conductor_temp_3c_c=critical_segment.get('conductor_temp_c') if critical_segment else None,
            vd_4c=vd_4c,
            vd_3c=VoltageDropResult(
                vd_v=critical_segment.get('vd_v'),
                vd_pct=critical_segment.get('vd_pct'),
            ) if critical_segment else None,
            vd_total_pct=max(item.get('vd_total_pct') or 0 for item in segment_results),
            load_end_voltage_v=min(item.get('load_end_voltage_v') or nominal_voltage for item in segment_results),
            conductor_volume_proxy=option_cost,
            fault_4c=fault_4c,
            fault_3c=FaultProtectionResult(
                status=critical_segment.get('fault_status'),
                fault_current_a=critical_segment.get('fault_current_a'),
            ) if critical_segment else None,
            segment_3c_results=segment_results,
            review_notes=review_notes,
        )
        if best is None or option_cost < best.conductor_volume_proxy:
            best = option

    if best is None:
        return CablePairOptimisation(
            status='unsizeable',
            review_notes=[
                'No 4C/3C cable combination satisfies ampacity and total voltage-drop constraints.'
            ],
        )
    return best


def select_direct_3c_cable(project, sizing_input):
    project = _project(project)
    current = float(sizing_input.per_circuit_operating_current_a or 0.0)
    if current <= 0:
        return CablePairOptimisation(
            status='unsizeable',
            review_notes=['Operating current must be greater than zero for voltage-drop sizing.'],
        )
    segments = _active_3c_segments(sizing_input)
    segment = segments[0]
    if not segment.length_m:
        return CablePairOptimisation(
            status='length_missing',
            review_notes=['3C cable length is required for direct 1phJB voltage-drop sizing.'],
        )

    nominal_voltage = float(project.voltage)
    segment_result, segment_notes = _select_3c_segment_for_voltage_drop(project, sizing_input, segment)
    if segment_result is not None:
        selection_3c = _selection_from_segment_result(project, segment_result, current)
        return CablePairOptimisation(
            status=segment_result.get('sizing_status') or 'selected',
            selection_3c=selection_3c,
            conductor_temp_3c_c=segment_result.get('conductor_temp_c'),
            vd_3c=VoltageDropResult(vd_v=segment_result.get('vd_v'), vd_pct=segment_result.get('vd_pct')),
            vd_total_pct=segment_result.get('vd_total_pct'),
            load_end_voltage_v=segment_result.get('load_end_voltage_v'),
            conductor_volume_proxy=_segment_cost_proxy(selection_3c, segment.length_m),
            fault_3c=FaultProtectionResult(
                status=segment_result.get('fault_status'),
                fault_current_a=segment_result.get('fault_current_a'),
            ),
            segment_3c_results=[segment_result],
            review_notes=segment_notes,
        )

    return CablePairOptimisation(
        status='unsizeable',
        fault_3c=FaultProtectionResult(
            status='fail' if not project.rcd_provided else 'not_calculated',
            review_notes=segment_notes,
        ),
        review_notes=segment_notes or ['No 3C cable satisfies ampacity and voltage-drop constraints for the direct branch.'],
    )


def _result_derating_basis(*selections):
    selected = [selection for selection in selections if selection and selection.catalogue]
    if not selected:
        return None, None, None, 30.0
    k_temp = min(selection.k_temp for selection in selected if selection.k_temp is not None)
    k_group = selected[0].k_group
    k_total = min(selection.k_total for selection in selected if selection.k_total is not None)
    catalogue_ref = selected[0].catalogue.ampacity_temp_ref_c
    return k_temp, k_group, k_total, catalogue_ref


def _ampacity_defaults(selection, prefix):
    if not selection or not selection.catalogue:
        return {
            f'{prefix}_catalogue': None,
            f'{prefix}_size_mm2': None,
            f'{prefix}_ampacity_derated_a': None,
            f'{prefix}_ampacity_margin_pct': None,
        }
    return {
        f'{prefix}_catalogue': selection.catalogue,
        f'{prefix}_size_mm2': selection.catalogue.conductor_size_mm2,
        f'{prefix}_ampacity_derated_a': selection.derated_ampacity_a,
        f'{prefix}_ampacity_margin_pct': selection.ampacity_margin_pct,
    }


def _vd_defaults(vd_result, prefix):
    if vd_result is None:
        return {
            f'{prefix}_vd_v': None,
            f'{prefix}_vd_pct': None,
        }
    return {
        f'{prefix}_vd_v': vd_result.vd_v,
        f'{prefix}_vd_pct': vd_result.vd_pct,
    }


def _fault_status(fault_result):
    return fault_result.status if fault_result else 'not_calculated'


def _fault_current(fault_result):
    return fault_result.fault_current_a if fault_result else None


def size_cold_cable_for_branch(branch, project):
    project = _project(project)
    sizing_input = build_cold_cable_sizing_input(branch, project)
    review_notes = list(sizing_input.review_notes)
    selection_4c = None
    selection_3c = None
    sizing_result = None

    if sizing_input.length_missing:
        sizing_status = 'length_missing'
    else:
        sizing_result = (
            optimise_cable_pair(project, sizing_input)
            if sizing_input.branch_type == '3phJB'
            else select_direct_3c_cable(project, sizing_input)
        )
        sizing_result = apply_fault_protection_checks(project, sizing_input, sizing_result)
        selection_4c = sizing_result.selection_4c
        selection_3c = sizing_result.selection_3c
        _append_unique(review_notes, sizing_result.review_notes)
        sizing_status = sizing_result.status
        if sizing_status in {'selected', 'review_required'} and sizing_input.length_basis == 'project_default':
            sizing_status = 'review_required'

    k_temp, k_group, k_total, catalogue_ref = _result_derating_basis(selection_4c, selection_3c)
    vd_status = 'not_calculated'
    if sizing_result is not None:
        vd_status = 'pass' if sizing_result.status in {'selected', 'review_required'} else 'fail'
    cable_4c_mass_mt = _selection_mass_mt(selection_4c, sizing_input.length_4c_m) if sizing_result else None
    if sizing_result and sizing_result.segment_3c_results:
        cable_3c_mass_mt = _total_mass_mt(
            *(segment.get('conductor_mass_mt') for segment in sizing_result.segment_3c_results)
        )
    else:
        cable_3c_mass_mt = (
            _selection_mass_mt(selection_3c, sizing_input.length_3c_m, sizing_input.circuit_count)
            if sizing_result else None
        )
    selected_catalogue = (
        selection_4c.catalogue if selection_4c and selection_4c.catalogue
        else selection_3c.catalogue if selection_3c and selection_3c.catalogue
        else None
    )
    conductor_density = (
        conductor_density_kg_m3(selected_catalogue.conductor_material)
        if selected_catalogue else None
    )
    result_defaults = {
        'project': project,
        'distribution': branch.distribution,
        'branch': branch,
        'branch_index': sizing_input.branch_index,
        'line_id': sizing_input.line_id,
        'line_uid': sizing_input.line_uid,
        'heating_cable_type': sizing_input.heating_cable_type,
        'per_circuit_operating_current_a': sizing_input.per_circuit_operating_current_a,
        'line_operating_current_a': sizing_input.line_operating_current_a,
        'breaker_size_a': sizing_input.breaker_size_a,
        'circuit_count': sizing_input.circuit_count,
        'mcb_curve': project.mcb_curve,
        'rcd_provided': project.rcd_provided,
        'length_4c_m': sizing_input.length_4c_m,
        'length_3c_m': sizing_input.length_3c_m,
        'length_basis': sizing_input.length_basis,
        'site_ambient_temp_c': float(project.max_amb_t),
        'catalogue_temp_ref_c': catalogue_ref,
        'k_temp': k_temp,
        'k_group': k_group if k_group is not None else _project_grouping_derating(project)[0],
        'k_total': k_total,
        'install_method': project.cable_install_method,
        'vd_allowable_pct': float(project.allowablevdrop),
        'vd_total_pct': sizing_result.vd_total_pct if sizing_result else None,
        'vd_status': vd_status,
        'load_end_voltage_v': sizing_result.load_end_voltage_v if sizing_result else None,
        'optimization_run': bool(sizing_result and sizing_input.branch_type == '3phJB'),
        'conductor_volume_proxy': sizing_result.conductor_volume_proxy if sizing_result else None,
        'conductor_material_density_kg_m3': conductor_density,
        'conductor_mass_total_mt': _total_mass_mt(cable_4c_mass_mt, cable_3c_mass_mt),
        'fault_current_4c_phase_to_phase_a': _fault_current(sizing_result.fault_4c) if sizing_result else None,
        'fault_protection_4c_status': _fault_status(sizing_result.fault_4c) if sizing_result else 'not_calculated',
        'fault_current_3c_line_to_neutral_a': _fault_current(sizing_result.fault_3c) if sizing_result else None,
        'fault_protection_3c_status': _fault_status(sizing_result.fault_3c) if sizing_result else 'not_calculated',
        'sizing_status': sizing_status,
        'review_notes': review_notes,
    }
    result_defaults.update(_ampacity_defaults(selection_4c, 'cable_4c'))
    result_defaults.update(_ampacity_defaults(selection_3c, 'cable_3c'))
    result_defaults.update({
        'cable_4c_conductor_temp_c': sizing_result.conductor_temp_4c_c if sizing_result else None,
        'cable_3c_conductor_temp_c': sizing_result.conductor_temp_3c_c if sizing_result else None,
        'cable_4c_conductor_mass_mt': cable_4c_mass_mt,
        'cable_3c_conductor_mass_mt': cable_3c_mass_mt,
        'cable_3c_segments': sizing_result.segment_3c_results if sizing_result else [],
    })
    result_defaults.update(_vd_defaults(sizing_result.vd_4c if sizing_result else None, 'cable_4c'))
    result_defaults.update(_vd_defaults(sizing_result.vd_3c if sizing_result else None, 'cable_3c'))
    result, _created = ColdCableResult.objects.update_or_create(
        distribution=branch.distribution,
        branch_index=branch.branch_index,
        defaults=result_defaults,
    )
    return result


def size_cold_cables_for_project(project):
    project = _project(project)
    branches = PowerDistributionBranch.objects.filter(
        distribution__line__proj_id=project.proj_id,
    ).select_related('distribution', 'distribution__line', 'distribution__line__process_line_calculation')
    return [
        size_cold_cable_for_branch(branch, project)
        for branch in branches
    ]
