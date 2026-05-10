# MI Cable Research And Integration Plan

Date: 2026-05-11

This note records the first serious MI-cable pass for the EHT Office
calculation module. It combines local code review, the existing AG/Gemini MI
notes, public manufacturer literature, and public standard/catalogue metadata.
It is intentionally written as an engineering basis document, not as final
issued design procedure. Before production use, the calculation method must be
validated against purchased standards, manufacturer-certified examples, and the
project's applicable jurisdiction.

## 1. Executive Direction

The current application is structurally ready for MI integration because it
already has a modular calculation pipeline:

- `eht/pipeline.py` is the project-level entry point.
- `eht/cal.py` orchestrates per-line heat loss, tracer selection, power
  distribution, BOQ, and result aggregation.
- `eht/calculations/heat_loss.py`, `tracer_selection.py`,
  `power_distribution.py`, and `boq.py` are the active calculation modules.
- `PowerDistributionBranch.tagged_components` feeds the SLD graph and cable
  schedule.

MI must not be added as another row type in the present SR catalogue. It is a
different design product:

- SR cable is a parallel self-regulating heater selected mainly by output
  curve at pipe temperature.
- MI cable is a factory-engineered series-resistance heater set where heated
  length, resistance, voltage, phase configuration, cold leads, sheath
  temperature, and hazardous-area temperature class all interact.

The right direction is to introduce a generic "heating technology selection"
layer and then plug SR and MI into it as separate engines. SR remains the
default path. MI becomes either an explicit line-level choice or an automatic
choice when SR cannot satisfy maintain/exposure/temperature-class constraints.

## 2. Existing Local Research

Reviewed local MI material:

- `NOTES/gemini_MI_notes.md`
- `MI_Cable_Engineering_Note.docx`
- `generate_mi_doc.py`
- `eht/models.py` MI model stubs
- `eht/management/commands/populate_mi_cables.py`
- `NOTES/REFRACTOR_TASK_TRACKER.md`

The existing MI notes correctly identify the big shift: MI is series
resistance, cannot be field-cut like SR, needs exact engineered length, needs
single/three-phase support, and must pass sheath-temperature/T-class checks.

The existing MI database work is only a placeholder. The current
`MICableFamily`, `MICableHeater`, and `MIAlloyTempFactor` models in
`eht/models.py` store family, resistance, conductor count, and one broad
temperature factor curve. That is useful as a seed, but not enough for design.
The `populate_mi_cables.py` command uses representative/fabricated catalogue
values and should be treated as demo data only.

## 3. Standards Basis

Public standard metadata points to this standards stack:

| Area | Standard family | Role in our app |
| --- | --- | --- |
| Explosive atmospheres | IEC/IEEE 60079-30-1:2025 | General and testing requirements for electrical resistance trace heating in explosive atmospheres. Covers series and parallel trace heaters, factory and field assemblies, terminations, and control methods. |
| Explosive atmospheres application | IEC/IEEE 60079-30-2:2025 | Application guidance for design, installation, and maintenance in explosive atmospheres. This is the key guide for hazardous-area design workflow. |
| Industrial/commercial non-explosive areas | IEC/IEEE 62395-1:2024 | General/test requirements for electrical resistance trace heating outside explosive atmospheres. IEEE indicates this supersedes IEEE 515-2017. |
| Industrial/commercial application guide | IEC/IEEE 62395-2 | Application/design guide companion to 62395-1. Use with purchased text for design procedure details. |
| Legacy/industry reference | IEEE 515-2017 | Historically important industrial heat-tracing standard; now superseded in IEEE listings by IEC/IEEE 62395-1. |
| US electrical installation | NEC Article 427 and hazardous-location articles | Branch circuit, ground-fault, wiring, and installation compliance. Public manufacturer docs repeatedly require ground-fault protection for heating circuits. |

Important implementation consequence:

The software should store the governing design basis per project:

- `design_standard_family`: IEC/IEEE 62395, IEC/IEEE 60079-30, NEC/CEC, or
  project-specific.
- `hazardous_area_basis`: safe area, IEC Zone/ATEX, NEC Class/Division, or
  hybrid.
- `temperature_class`: T1 through T6 plus any dust-layer or project derating
  rule.
- `temperature_class_limit_c`: derived numeric limit, not only display text.
- `requires_temperature_limiter`: boolean/rule result from cable type, area
  class, control method, and sheath-temperature calculation.

## 4. Manufacturer Literature Summary

### 4.1 nVent Raychem / Chemelex

The Raychem MI design guide describes MI cable as fixed-length resistance
heater sets. The public guide covers selection workflow, power requirements,
resistance selection, resistance tolerance, sheath temperature, controls,
installation details, and ordering/package data.

Notable design points for our application:

- XMI-A is positioned for very high maintain/exposure temperatures.
- XMI-L is positioned as a larger-diameter, lower-sheath-temperature option.
- Cable output is a function of applied voltage, selected cable resistance,
  and heated length.
- Resistance tolerance must be considered when evaluating minimum heat output
  and maximum sheath temperature.
- Design must account for heat sinks such as valves, supports, and flanges.
- Fixed heater length matters. Extra length cannot simply disappear; poor
  placement can create local overheating.
- Ground-fault protection and controllers/limiters are treated as part of the
  system, not an afterthought.

The nVent guide gives the important selection idea used by many MI workflows:
for a required power per length `Pmin` and heated length `L`, determine the
maximum permissible cable resistance per length, then choose a catalogue cable
whose resistance is equal to or below that value. Higher resistance would
underheat; much lower resistance may overheat or violate T-class.

### 4.2 Thermon

Thermon's MIQ specification sheet and installation guide describe MIQ as an
Alloy 825 sheathed MI cable family with 300/600 Vac options, high maintain and
exposure limits, several factory set configurations, standard cold-lead
lengths, multiple resistance codes, and resistance tolerance.

Notable design points:

- Factory fabrication type/configuration is central. We need to model set
  geometry, not just cable meters.
- Standard cold-lead options and cold-lead length affect ordering and voltage
  drop.
- The catalogue resistance code is only one part of design; sheath/exposure,
  watt density, current, and hazardous approval must all pass.
- Installation guidance includes accessory and routing practices that should
  become validation warnings, not free-text notes.

### 4.3 Chromalox

Chromalox MI literature positions MI cable for high-temperature metal pipe and
surface applications, with high maintain/exposure temperatures, factory
terminated sets, and high watt density capability.

Notable design points:

- Chromalox explicitly presents MI as factory assembled and intended for metal
  pipes, tanks, and vessels.
- The app must not output "bulk MI cable length" as if procurement can cut it
  freely on site.
- Ground-fault equipment protection is explicitly recommended in public
  Chromalox MI material.

### 4.4 Heat Trace

Heat Trace describes MI cables as series-resistance heaters where length and
resistance determine power. Public literature shows multiple sheath/material
families with different maximum withstand/maintain temperatures and power
density capability.

Notable design points:

- Manufacturer families can vary widely in max maintain/exposure temperature.
- We need family-specific limits and not one global MI maximum.
- Some MI products reach very high withstand temperatures, but the allowable
  sheath temperature in hazardous areas may be far lower because of T-class.

### 4.5 eltherm, BARTEC, and Design Software

eltherm and BARTEC material reinforces the same pattern: MI is selected as an
engineered heater system and high-quality commercial tools include project
reports, hazardous-area checks, load/electrical summaries, bill of material,
and design workflow support.

TraceCalc Pro, ChromaTrace, CompuTrace, and Heloc Pro all matter as product
benchmarks. Our application should aim beyond a hidden calculator. It should
make the design basis, rejected options, T-class proof, circuit grouping, and
procurement set schedule visible to the engineer.

## 5. Technical Integrity Findings In Current SR Calculation

These findings should be fixed before or during MI integration because MI will
otherwise inherit incorrect assumptions.

### 5.1 Heat loss safety factor is stored but not applied

`ProjectData.heat_loss_sf` is saved and validated in `eht/models.py`, and
`fetch_project_data()` exposes it. The active heat-loss calculation in
`eht/calculations/heat_loss.py` does not multiply the calculated heat loss by
that safety factor.

Impact:

- SR selection may be undersized relative to project setup.
- MI resistance selection would be directly wrong because MI uses required
  W/m as the core sizing input.

Action:

- Add a named field such as `base_heat_loss_w_m` and
  `design_heat_loss_w_m`.
- Apply `heat_loss_sf` explicitly.
- Preserve both values in persistence/reporting.

### 5.2 Confirmed input filtering is inconsistent

`fetch_process_lines()` currently filters only by `proj_id`, not by
`status='confirmed'`. The pipeline error message says "No confirmed input
data found", but the query can include pending rows.

Impact:

- Partial invalid upload workflows can accidentally calculate unconfirmed
  rows.
- MI factory-set output could be generated from provisional data.

Action:

- Filter confirmed rows in `fetch_process_lines()`.
- Add a regression test that pending rows are ignored.

### 5.3 SR vendor filtering lost important engineering constraints

The active `fetch_vendor_data()` filters by vendor and voltage only. The
legacy retired code had intended filters for maintain temperature, operating
temperature, exposure temperature, and vendor catalogue suitability. The active
`get_tracer_options()` even carries a TODO at the filtering point.

Impact:

- A tracer can be selected even if its maintain/operating/exposure limits,
  area approval, gas group, or T-rating do not match the line/project.
- This is a bigger risk for MI because suitability is dominated by family,
  sheath, approvals, T-class, and max sheath temperature.

Action:

- For SR, restore catalogue filtering for maintain temperature, max operating
  temperature, max exposure, zone/area class, gas group, and T-rating where
  catalogue data is available.
- For MI, build a separate catalogue predicate layer with explicit reject
  reasons.

### 5.4 Accessory adders are hard coded

The heat-loss module hard codes valve/support/flange length adders while
`ProjectData` already has `valve_factor`, `flange_factor`, and
`support_factor` fields that are not used.

Impact:

- Engineers cannot tune project/client/vendor-specific heat-sink allowances.
- MI set length depends on these adders, so this becomes an ordering and
  sheath-temperature issue, not just quantity.

Action:

- Move accessory rules into named data tables or project-level defaults.
- Store accessory-adders by type in the result, not only a single summed
  `tracer_adder`.

### 5.5 Breaker sizing uses total line current in a confusing way

`compute_power_params()` calculates total line maximum current, derives number
of circuits from loading, but selects breaker size from the total maximum
current rather than the current assigned to each generated circuit/branch.

Impact:

- Breaker size can be oversized and can distort SLD topology.
- MI three-phase sets will need much more explicit circuit current semantics:
  one-phase loop, dual conductor, three single-conductor star/delta set, or
  multiple parallel heater sets.

Action:

- Refactor to compute per-circuit or per-branch current first.
- Select breaker rating per circuit/branch after applying configured loading
  percentage.
- Store both total line load and branch load.

### 5.6 Termination margin is added after current/load calculation

`compute_power_params()` calculates operating/start current using
`Tracer_With_Margin`, then adds termination length afterward into
`total_tracer_length`.

Impact:

- Reported total tracer length and calculated current/load are based on
  different lengths.
- For MI, any extra heated length changes resistance and power, so this
  pattern cannot be reused.

Action:

- Decide whether termination margin is heated length, cold lead, or physical
  allowance by technology.
- Use the same electrically active length in power/current calculations and
  result reporting.

### 5.7 Startup temperature is not used in SR electrical calculation

`ProjectData.startup_t` exists but current maximum current is calculated at
`min_amb_t`. That may be a conservative approximation in some cases, but it is
not named or documented as such.

Impact:

- Starting current logic is ambiguous.
- MI needs both cold-start current and operating current because conductor
  resistance changes with temperature.

Action:

- Rename the calculation scenario to `cold_start_current`.
- Use project startup temperature where intended.
- Preserve worst-case minimum ambient as a separate check where required.

### 5.8 Existing MI models are not design-grade

Current MI models lack:

- Cable diameter and mass.
- Conductor material and resistance basis.
- Resistance tolerance.
- Cold-lead data and cold-lead resistance.
- Maximum maintain/exposure limits by energized/de-energized condition.
- Maximum watt density curves by maintain/exposure/installation condition.
- Minimum/maximum heater length.
- Hazardous-area approvals, gas/dust groups, and T-class certification data.
- Manufacturer design/configuration code.
- Source document/version/provenance.

Action:

- Replace the placeholder schema with a catalogue model built around
  manufacturer source data and rejection reasons.

## 6. MI Design Concepts For The Application

### 6.1 Fundamental equations

Use the equations below as the internal calculation skeleton. Exact modifiers
must be validated against vendor examples and the selected standard.

Design heat loss:

```text
Q_design_w_m = Q_base_w_m * heat_loss_sf
```

Heated length:

```text
L_heated_m = L_pipe_m + L_accessory_adders_m + L_field_allowance_m
```

Catalogue resistance:

```text
R20_total_ohm = R20_per_m * L_heated_m
Rhot_total_ohm = R20_total_ohm * resistance_factor(T_conductor_or_operating)
```

Single-phase power:

```text
P_total_w = V_heater^2 / R_total_ohm
P_w_m = P_total_w / L_heated_m
I_a = V_heater / R_total_ohm
```

Three-phase star:

```text
V_phase = V_line_line / sqrt(3)
P_total_w = 3 * V_phase^2 / R_each_phase_ohm
I_line_a = V_phase / R_each_phase_ohm
```

Three-phase delta:

```text
V_phase = V_line_line
P_total_w = 3 * V_phase^2 / R_each_phase_ohm
I_line_a = sqrt(3) * (V_phase / R_each_phase_ohm)
```

Cold-lead voltage drop, first-pass approximation:

```text
V_heater = V_supply - (I_a * R_cold_lead_total)
```

In implementation this should be solved iteratively because current depends on
heater voltage and heater voltage depends on current.

### 6.2 Worst-case checks

For every candidate, evaluate at least these scenarios:

| Scenario | Use for |
| --- | --- |
| Low voltage plus high resistance tolerance | Minimum delivered heat. Candidate must still meet `Q_design_w_m`. |
| Nominal voltage and nominal/hot resistance | Normal operating load and energy report. |
| Maximum voltage plus low resistance tolerance | Maximum power density, maximum current, and maximum sheath temperature. |
| Cold start temperature | Breaker/circuit starting current. |
| Maximum process/exposure temperature | Cable family exposure suitability and T-class/sheath check. |

Resistance tolerance matters because a low-resistance manufactured heater
produces higher power and higher sheath temperature, while a high-resistance
heater may underheat.

### 6.3 Sheath temperature and T-class approach

This is the most important MI safety check.

Temperature class limits normally used in hazardous-area design:

| Class | Max surface temperature |
| --- | --- |
| T1 | 450 deg C |
| T2 | 300 deg C |
| T3 | 200 deg C |
| T4 | 135 deg C |
| T5 | 100 deg C |
| T6 | 85 deg C |

The app must distinguish:

- Maintain-temperature design: enough heat at low ambient.
- Maximum sheath temperature: safe surface temperature at high voltage, low
  resistance, maximum process/ambient/exposure condition.
- Cable family maximum sheath/exposure temperature: material survival.
- Hazardous-area T-class limit: ignition prevention.
- Controller/limiter design: control-only, limiter-required, or certified
  self-limiting design basis.

First implementation strategy:

1. Store the T-class numeric limit and candidate maximum sheath temperature.
2. If manufacturer catalogue/certified data gives maximum sheath temperature
   for the selected design condition, use that as primary evidence.
3. If no certified data is available, calculate a conservative preliminary
   estimate and mark the result `manufacturer_review_required`.
4. Reject candidates where preliminary or certified sheath temperature exceeds
   the project T-class limit or family maximum.
5. Retain all rejection reasons in the result.

The exact thermal-resistance model should be a dedicated follow-up document
after purchased IEC/IEEE 60079-30-2 and vendor design examples are available.
Do not bury a guessed formula inside `mi_selection.py`.

### 6.4 Candidate selection algorithm

Per process line:

1. Calculate base and design heat loss.
2. Build accessory/heated-length breakdown.
3. Decide allowed technologies: SR, MI, or both.
4. For MI, derive required power per heated metre.
5. Generate candidate heater sets:
   - family
   - heater resistance code
   - conductor count
   - construction/configuration
   - single-phase or three-phase arrangement
   - number of passes/runs
   - cold-lead option
6. Filter by hard suitability:
   - vendor/project selection
   - voltage
   - maintain temperature
   - design/exposure temperature
   - material/sheath
   - hazardous approvals
   - gas/dust group where applicable
   - cable length limits
   - ampacity/cold-lead rating
7. Calculate electrical scenarios:
   - minimum heat output
   - nominal operating output
   - maximum output
   - cold-start current
   - voltage drop
8. Calculate/lookup maximum sheath temperature.
9. Reject candidates that fail:
   - insufficient heat
   - excessive W/m or watt density
   - excessive current
   - excessive voltage drop
   - T-class failure
   - family exposure failure
   - installability failure
10. Rank valid candidates:
   - passes all safety checks
   - lowest T-class margin risk
   - closest heat output to requirement without underheating
   - lower circuit count where safe
   - better phase balance
   - shorter/simpler cold-lead arrangement
   - lower procurement complexity
11. Persist best selection and all valid/rejected alternatives.

Important: MI ranking should not simply prefer the shortest heater length or
highest W/m. That is exactly how T-class and local overheating problems sneak
in.

## 7. Proposed Data Model

### 7.1 Catalogue/source models

Replace or expand the current MI models with:

```text
HeatingTechnology
  code: SR, MI
  display_name
  is_active

MICableFamily
  vendor
  family_name
  product_series
  sheath_material
  conductor_material
  insulation_material
  max_voltage_v
  max_maintain_temp_c
  max_exposure_power_on_c
  max_exposure_power_off_c
  max_sheath_temp_c
  max_watt_density_w_m
  hazardous_approvals_json
  notes
  source_document
  source_revision

MICableHeater
  family
  part_number_or_resistance_code
  conductor_count
  resistance_ohm_per_m_at_20c
  resistance_basis: PER_CABLE, PER_CONDUCTOR, LOOP
  resistance_tolerance_percent
  cable_diameter_mm
  min_bend_radius_mm
  max_current_a
  min_heated_length_m
  max_heated_length_m
  compatible_configurations_json
  source_document

MIColdLeadOption
  family
  conductor_count
  cross_section_or_awg
  max_current_a
  resistance_ohm_per_m
  max_voltage_v
  standard_lengths_json
  gland_or_termination_type

MIResistanceTemperatureFactor
  material_or_alloy
  temperature_c
  resistance_multiplier
  source_document
```

### 7.2 Selection/result models

Do not force MI into `SelectedTracer` as-is. Create a generic result layer:

```text
HeatingSelection
  line
  technology: SR, MI
  selected_catalogue_uid
  family
  selection_rank
  status: selected, alternate, rejected, review_required
  rejection_reasons_json
  design_heat_loss_w_m
  heated_length_m
  nominal_power_w_m
  min_power_w_m
  max_power_w_m
  nominal_total_power_w
  operating_current_a
  cold_start_current_a
  breaker_size_a
  circuit_count
  voltage_drop_percent
  sheath_temp_max_c
  t_class_limit_c
  t_class_pass
  review_required
  calculation_payload_json

MIHeaterSet
  heating_selection
  configuration
  phase_arrangement: 1PH, 3PH_STAR, 3PH_DELTA
  heater_part_number
  runs_or_passes
  heated_length_per_run_m
  cold_lead_length_m
  star_point_required
  factory_order_description
```

Keep `SelectedTracer` during migration for SR compatibility, but the UI should
eventually read from `HeatingSelection`.

## 8. Input Model Changes

Minimum line-list additions:

- `heating_technology`: AUTO, SR, MI.
- `control_method`: ambient sensing, line sensing, limiter, controller plus
  limiter.
- `hazardous_area`: project default or line override.
- `gas_group` and/or dust group where applicable.
- `temperature_class`: allow project default and line override.
- `max_exposure_temp_c`: line-specific if different from design temp.
- `mi_configuration_preference`: auto, 1PH, 3PH star, 3PH delta, dual-core.
- `cold_lead_length_m`: optional line-specific override.
- `field_length_tolerance_percent`: used for as-built sensitivity.

Important future improvement:

The current line model is one-segment only. Competitor tools and real projects
need multi-segment lines: different pipe sizes, insulation thicknesses,
ambient/exposure areas, or heat sinks along one circuit. MI integration should
not block on multi-segment support, but the data model should avoid making it
harder.

## 9. Power Distribution, SLD, BOQ, And Cable Schedule Impact

### 9.1 Power distribution

MI requires different topology concepts:

- A one-phase MI heater set may still look like one heating circuit.
- A three-phase star MI set needs a star point/end node.
- Delta/star arrangements have line/phase current semantics unlike SR
  circuits grouped under 1PH JBs.
- Multiple MI runs on one pipe may be one electrical set or several circuits.

The generated power-distribution payload should include technology metadata:

```text
component_type: Tracer
metadata:
  technology: MI
  heater_set_id
  phase_arrangement
  nominal_power_w_m
  sheath_temp_max_c
  t_class_pass
```

Add component types when needed:

- `MIColdLead`
- `MIHotColdJoint`
- `MIStarPoint`
- `MIEndSeal`

The existing task tracker already mentions future `MI_STAR_POINT`; that should
be implemented as a graph endpoint/terminal first, not as a freeform SLD
object.

### 9.2 BOQ

SR BOQ can count tracer by metres. MI BOQ must count factory heater sets.

New BOQ items:

- `MI_HEATER_SET`: each factory heater set with engineered heated length.
- `MI_COLD_LEAD`: if ordered/quantified separately.
- `MI_HOT_COLD_JOINT`: factory or field assembly count.
- `MI_GLAND_KIT`
- `MI_STAR_POINT_KIT`
- `MI_END_SEAL`
- `HEAT_TRANSFER_CEMENT`
- `STAINLESS_STEEL_STRAP` or tie wire.
- `TEMPERATURE_LIMITER` where required.
- `MI_WARNING_LABEL` if project labelling differs from SR labels.

Reports must show:

- Factory order description.
- Heated length.
- Cold-lead length and side.
- Resistance code.
- Voltage/phase configuration.
- Power output at minimum, nominal, maximum scenario.
- Maximum sheath temperature and T-class result.

### 9.3 Cable schedule

Do not mix MI heater sets with cold power cable schedule as if they are the
same commodity. The cable schedule should keep:

- Power/cold cable from panel to JB.
- MI cold lead from JB to hot-cold joint.
- MI heated cable/set schedule.

The existing dedicated `eht/cable_schedule.py` page can be expanded, but the
row types must be explicit.

## 10. Implementation Roadmap

### Phase 0: SR integrity repair

1. Apply heat-loss safety factor explicitly.
2. Filter process lines to confirmed rows.
3. Restore SR catalogue suitability filtering.
4. Refactor breaker sizing to per-circuit/per-branch current.
5. Align termination margin with electrical length semantics.
6. Add tests for each repaired behavior.

### Phase 1: MI design-basis and catalogue foundation

1. Replace placeholder MI schema with design-grade catalogue models.
2. Mark `populate_mi_cables.py` data as sample/demo only or remove it.
3. Add admin views/import path for MI catalogue data.
4. Store source document and revision for every catalogue row.
5. Add T-class numeric mapping table.

### Phase 2: Pure MI calculation engine

Create pure modules with no Django side effects:

- `eht/calculations/mi_length.py`
- `eht/calculations/mi_electrical.py`
- `eht/calculations/mi_sheath_temperature.py`
- `eht/calculations/mi_selection.py`

Start with deterministic unit tests:

- Resistance and power for one-phase candidate.
- Star and delta three-phase calculation.
- Voltage-drop iteration.
- Resistance tolerance min/max scenarios.
- Rejection reasons.
- T-class pass/fail.

### Phase 3: Pipeline integration

1. Add line/project technology selection.
2. Introduce a generic heating-selection contract.
3. Keep SR path unchanged initially behind an adapter.
4. Add MI path behind a feature flag.
5. Persist both selected and alternate MI candidates.
6. Make calculation summaries technology-aware.

### Phase 4: BOQ/report/SLD integration

1. Extend BOQ metadata for MI set items.
2. Add MI result fields to result tab/export.
3. Add MI metadata into SLD tracer nodes.
4. Add `MIStarPoint` for 3PH star designs.
5. Add MI-specific cable schedule row types.

### Phase 5: UI workflow

1. Add project-level MI design basis controls.
2. Add line-level technology override.
3. Add candidate review table with rejected reasons.
4. Add sheath/T-class badge in result and SLD inspector.
5. Add "manufacturer review required" status where calculation evidence is
   preliminary.

### Phase 6: Engineering polish

1. Multi-segment line support.
2. Phase balancing across panels.
3. As-built length sensitivity simulator.
4. Insulation optimization.
5. Vendor-source comparison/report.

## 11. Proposed Pseudocode

```python
def calculate_line_heating(line, project, catalogues):
    heat = calculate_heat_loss(line, project)
    heat.design_heat_loss_w_m = heat.base_heat_loss_w_m * project.heat_loss_sf

    allowed_technologies = resolve_allowed_technologies(line, project)
    candidates = []

    if "SR" in allowed_technologies:
        candidates.extend(select_sr_candidates(line, project, heat, catalogues.sr))

    if "MI" in allowed_technologies:
        mi_input = build_mi_design_input(line, project, heat)
        candidates.extend(select_mi_candidates(mi_input, catalogues.mi))

    valid_candidates = [item for item in candidates if item.status == "valid"]
    if not valid_candidates:
        return no_selection_result(line, candidates)

    selected = rank_heating_candidates(valid_candidates)[0]
    return build_line_result(line, heat, selected, candidates)


def select_mi_candidates(mi_input, mi_catalogue):
    candidates = []
    for family in mi_catalogue.compatible_families(mi_input):
        for heater in family.heaters:
            for config in allowed_mi_configurations(mi_input, heater):
                candidate = evaluate_mi_candidate(mi_input, family, heater, config)
                candidates.append(candidate)
    return candidates


def evaluate_mi_candidate(mi_input, family, heater, config):
    length = calculate_mi_heated_length(mi_input, config)

    min_heat = calculate_mi_electrical(
        voltage=mi_input.min_voltage,
        resistance_tolerance="high",
        temperature_scenario="operating",
        length=length,
        heater=heater,
        config=config,
    )
    max_heat = calculate_mi_electrical(
        voltage=mi_input.max_voltage,
        resistance_tolerance="low",
        temperature_scenario="max_sheath",
        length=length,
        heater=heater,
        config=config,
    )
    cold_start = calculate_mi_electrical(
        voltage=mi_input.nominal_voltage,
        resistance_tolerance="low",
        temperature_scenario="cold_start",
        length=length,
        heater=heater,
        config=config,
    )

    rejection_reasons = []
    if min_heat.power_w_m < mi_input.design_heat_loss_w_m:
        rejection_reasons.append("insufficient_heat_output")
    if max_heat.power_w_m > family.max_watt_density_w_m:
        rejection_reasons.append("exceeds_family_watt_density")
    if cold_start.current_a > config.max_allowed_current_a:
        rejection_reasons.append("exceeds_current_limit")

    sheath = evaluate_mi_sheath_temperature(mi_input, family, heater, config, max_heat)
    if sheath.temperature_c > mi_input.temperature_class_limit_c:
        rejection_reasons.append("fails_temperature_class")
    if sheath.temperature_c > family.max_sheath_temp_c:
        rejection_reasons.append("exceeds_family_sheath_temperature")

    return MICandidateResult(
        family=family,
        heater=heater,
        config=config,
        length=length,
        min_heat=min_heat,
        nominal=calculate_nominal(mi_input, family, heater, config, length),
        max_heat=max_heat,
        cold_start=cold_start,
        sheath=sheath,
        status="rejected" if rejection_reasons else "valid",
        rejection_reasons=rejection_reasons,
        review_required=sheath.is_preliminary,
    )
```

## 12. Questions For The Next Pass

1. Which design basis should be primary: IEC/ATEX/IECEx, NEC/CEC, or both?
2. Should MI be selectable per line from the Excel input, or should the app
   auto-select MI only when SR cannot pass?
3. Which vendor should be implemented first with real catalogue data:
   nVent/Raychem, Thermon, Chromalox, Heat Trace, or SST?
4. Are we allowed to store manufacturer catalogue extracts directly in the
   application database, or should imports remain project-private/manual?
5. For hazardous areas, do you want the app to issue only preliminary
   calculation output until manufacturer verification, or should it attempt a
   fully auditable internal sheath-temperature calculation after standards are
   purchased?

## 13. Sources Reviewed

- IEEE SA, IEC/IEEE 60079-30-1-2025:
  https://standards.ieee.org/ieee/60079-30-1/7569/
- IEEE SA, IEC/IEEE 60079-30-2-2025:
  https://standards.ieee.org/ieee/60079-30-2/7570/
- IEEE SA, IEC/IEEE 62395-1-2024:
  https://standards.ieee.org/ieee/62395-1/10451/
- IEEE SA, IEEE 515-2017:
  https://standards.ieee.org/ieee/515/6672/
- nVent Raychem/Chemelex MI cable design guide:
  https://pim.chemelex.com/Product%20Documents/Design%20Guides-Forms/Raychem-DG-H56884-MIcables-EN.pdf
- nVent Raychem TraceCalc Pro:
  https://www.nvent.com/en-us/raychem/resources/design-tools/tracecalc-pro
- Thermon MIQ mineral insulated cable specification sheet:
  https://content.thermon.com/pdf/THM_US_Mineral_Insulated_Cable_Spec_Sheet_250806.pdf
- Thermon MIQ installation procedures:
  https://content.thermon.com/pdf/ca_pdf_files/PN50273-MIQ-Installation.pdf
- Chromalox MI mineral insulated high-temperature heating cable:
  https://www.chromalox.com/en/products-and-technologies/heat-trace/industrial-heat-trace-cable/industrial-mineral-insulated-heating-cables/mi-mineral-insulated-high-temperature
- Chromalox ChromaTrace design software:
  https://www.chromalox.com/en/products-and-technologies/heat-trace/industrial-heat-trace-system-components-and-accessories/industrial-tools-and-accessories/chromatrace-project-design-software
- Thermon CompuTrace design suite:
  https://thermon.com/products/heat-trace/design-technology/computrace-design-suite/
- Heat Trace mineral insulated cables:
  https://www.heat-trace.com/products/mineral-insulated-mi-cables
- eltherm mineral insulated heating cables:
  https://eltherm.com/products-and-systems/mi-cable
- BARTEC Heloc Pro:
  https://bartec.com/products-solutions/product-finder/product-detail/heloc-pro
- TE Connectivity hazardous location classifications:
  https://www.te.com/en/industries/industrial-machinery/insights/hazloc-classifications.html
