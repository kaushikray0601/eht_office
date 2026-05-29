# Cold Cable Engineering Kickoff Handoff

Date: 2026-05-29  
Prepared by: Codex  
Status: Kickoff contract for the next calculation module

## 1. Purpose

This note defines the handoff from the stabilized hot-engineering calculation
module into the next major module: cold cable sizing and voltage-drop
optimization.

The SR and MI calculation work has reached a useful MVP boundary. The next
module should not recalculate heat loss or re-select heating cable by default.
It should consume the persisted SR/MI electrical topology, branch data, current
values, breaker recommendations, cable schedule assumptions, and SLD structure
already produced by the hot-engineering module.

The goal is to turn calculated heating circuits into credible upstream
electrical deliverables: cold cable size, voltage drop, feeder length,
distribution topology, panel loading, and eventually optimization of cable
quantity and voltage-drop allocation.

## 2. Source of Truth for the Cold Cable Module

The cold cable module should consume persisted calculation output, not re-run
selection logic from raw line-list input.

Primary source objects:

| Source | Role in cold cable module |
| --- | --- |
| `PowerDistribution` | Line-level electrical result and distribution summary. |
| `PowerDistributionBranch` | Branch-level topology and tagged component payload. |
| `ProcessLineCalculation` | Persisted per-line heat loss, tracer type, selected tracer, currents, cable lengths, and diagnostic evidence. |
| `SelectedTracer` | Selected SR tracer snapshot and SR parallel-run metadata. |
| `SelectedMIHeater` | Selected MI heater-set snapshot and MI cold-lead/heater-set metadata. |
| `CableSchedule` / generated schedule payload | Existing cable-tag, from/to, length, and purpose evidence to be upgraded into sized cold-cable records. |
| `SLDTopologyEdit` and related SLD state | Manual topology edits and review state, once the cold-cable module is ready to consume controlled manual edits. |
| `ProjectData` | Project voltage, allowable voltage drop, breaker loading, DB-to-JB length assumptions, loop length assumptions, and future cold-cable design basis fields. |

Important principle:

- The hot-engineering module owns heat loss, SR/MI selection, heating-cable
  load, and branch topology.
- The cold-cable module owns conductor size, voltage drop, installation
  derating, feeder optimization, panel/JB loading, and upstream electrical
  deliverables.

## 3. Required Input Contract

The cold-cable module should start from a normalized branch/circuit input
structure. Each cold-cable sizing candidate should receive one logical feeder
segment at a time.

### 3.1 Project-Level Inputs

| Input | Source | Meaning |
| --- | --- | --- |
| `project_id` | `ProjectData.proj_id` | Active project identifier. |
| `system_voltage_v` | `ProjectData.voltage` | Nominal supply voltage. |
| `allowable_voltage_drop_percent` | `ProjectData.allowablevdrop` | Project voltage-drop criterion for cold cable. |
| `max_cb_size_a` | `ProjectData.max_cb_size` | Upper limit for selected breaker size. |
| `max_cb_loading_percent` | `ProjectData.restrict_cb_current` | Maximum loading allowed on a breaker. |
| `voltage_variation_percent` | `ProjectData.voltage_var_factor` | Existing heating-cable voltage variation basis. Cold cable may need its own refined basis later. |
| `db_to_jb_length_m` | `ProjectData.ckt_ln` | Current project-level DB-to-JB length assumption. |
| `jb_to_jb_loop_length_m` | `ProjectData.loop_ln` | Current project-level loop length assumption. |
| `area_class` | `ProjectData.area_class` | Hazardous-area classification for cable/JB selection evidence. |
| `temperature_class` | `ProjectData.temp_class` | T-class basis, mainly review context rather than cold-cable thermal sizing. |

Future project fields likely required:

- Cable installation method.
- Cable tray/conduit/direct-buried basis.
- Ambient temperature for cable ampacity.
- Grouping/spacing derating basis.
- Cable material, insulation, armour, and core-count preferences.
- Earthing philosophy.
- Short-circuit duration and fault level.
- Preferred cable standards/table set.

### 3.2 Line/Circuit Inputs

| Input | Source | Meaning |
| --- | --- | --- |
| `line_uid` | `PowerDistribution.line_id` / branch payload | Internal line key. |
| `line_id` | `PowerDistribution.line_id` / `ProcessLineCalculation.line_id` | User-facing line identifier. |
| `service_type` | `HeatTracingInput.service_type` / result payload | Service grouping and control context. |
| `heating_cable_type` | `ProcessLineCalculation.heating_cable_type` | `SR` or `MI`. |
| `selected_tracer` | `PowerDistribution.selected_tracer` / selected snapshot | SR model/UID or MI heater part number. |
| `tracer_family` | `PowerDistribution.tracer_family` | Vendor/family context where available. |
| `branch_index` | `PowerDistributionBranch.branch_index` | Branch identity in the generated topology. |
| `circuit_index` | Tagged component payload | Circuit identity under a branch. |
| `no_of_circuits` | `PowerDistribution.no_of_circuits` | Number of protected circuits for the line. |
| `breaker_size_a` | `PowerDistribution.breaker_size` | Current recommended heating-circuit breaker size. |
| `per_circuit_operating_current_a` | `PowerDistribution.operating_current` / `per_circuit_operating_current` | Normal operating current for one protected circuit. |
| `per_circuit_max_current_a` | `PowerDistribution.max_current` / `per_circuit_max_current` | Maximum/start current for one protected circuit. |
| `line_operating_current_a` | `PowerDistribution.line_operating_current` | Total operating current for all circuits on the line. |
| `line_max_current_a` | `PowerDistribution.line_max_current` | Total maximum/start current for all circuits on the line. |
| `operating_load_w` | `PowerDistribution.operating_load` | Total connected heating load for the line. |
| `heated_tracer_length_m` | `PowerDistribution.heated_tracer_length` | Energized heated length basis. |
| `total_tracer_length_m` | `PowerDistribution.total_tracer_length` | Heating-cable ordered/total length basis. |
| `pipe_size_mm` | `PowerDistribution.pipe_size_mm` / `ProcessLineCalculation.pipe_size_mm` | Review context and future routing/physical grouping context. |

Current meaning by cable technology:

- SR single run: one line may have one or more circuits depending on current
  and breaker loading.
- SR parallel run: each straight run is represented as an independently
  protected branch/circuit in the MVP topology.
- MI single set: one factory heater set is represented as one protected
  branch/circuit.
- MI multi-set: each identical heater set is represented as an independently
  protected branch/circuit.

### 3.3 SR-Specific Inputs

| Input | Source | Meaning |
| --- | --- | --- |
| `sr_parallel_run_count` | `SelectedTracer`, `PowerDistribution`, `ProcessLineCalculation` | Number of full straight SR runs selected. |
| `sr_parallel_run_basis` | Selected/power payload | Rule set used for SR parallel-run selection. |
| `sr_per_run_tracer_length_m` | Selected/power payload | Full route length per SR run before/with margin depending on source field. |
| `sr_constructability_warning` | Selected/power/result payload | Small-bore/run-count warning requiring review. |
| `sr_duty_ratio` | `SelectedTracer.spiral_factor` / result export | Heat-delivery duty evidence, not fractional installation length. |

Cold-cable interpretation:

- Treat each selected SR run as a real protected load path unless/until a
  future grouping optimizer deliberately combines upstream feeders.
- Do not infer fractional cable length from SR duty ratio.
- Use per-circuit current for cable ampacity and voltage-drop sizing.
- Use total line current only for line-level load summaries and panel totals.

### 3.4 MI-Specific Inputs

| Input | Source | Meaning |
| --- | --- | --- |
| `mi_heater_part_number` | `SelectedMIHeater.heater_part_number` | Factory heater code. |
| `mi_family` | `SelectedMIHeater.family` / snapshot | MI family and source context. |
| `heater_set_count` | `SelectedMIHeater.heater_set_count` | Number of identical MI heater sets selected. |
| `heated_length_m` | `SelectedMIHeater.heated_length_m` | Heated MI section length per set. |
| `cold_lead_option_code` | `SelectedMIHeater.cold_lead_option_code` | Selected cold-lead option. |
| `cold_lead_length_m` | `SelectedMIHeater.cold_lead_length_m` | MI cold-lead length per heater set. |
| `cold_lead_resistance_total_ohms` | `SelectedMIHeater.cold_lead_resistance_total_ohms` | Existing MI cold-lead electrical evidence. |
| `current_nominal_a` | `SelectedMIHeater.current_nominal_a` | Nominal current per heater set. |
| `current_cold_start_a` | `SelectedMIHeater.current_cold_start_a` | Cold-start current per heater set. |
| `t_class_verdict` | `SelectedMIHeater.t_class_verdict` | Review-only T-class status. |

Cold-cable interpretation:

- Treat each MI heater set as one protected load path in the current MVP.
- Cold-lead data is not the same as upstream cold-cable sizing from DB/panel to
  field JB.
- Physical JB terminal capacity and gland count must not be assumed solved by
  MI selection. The cold-cable/JB module must model it explicitly.

## 4. Topology and JB Path Inputs

The cold-cable module must be topology-aware. It should not size cable from a
flat per-line summary alone.

Relevant topology data:

| Input | Source | Meaning |
| --- | --- | --- |
| `branch_id` / `branch_index` | `PowerDistributionBranch` | Logical branch generated for the line. |
| `tagged_components` | `PowerDistributionBranch.tagged_components` | Component-level SLD payload: MCB, cable, isolator, JB, tracer, end termination, downstream connections. |
| `from_component` | Tagged component edge/payload | Upstream connection point. |
| `to_component` | Tagged component edge/payload | Downstream connection point. |
| `component_type` | Tagged component payload | DB, MCB, cable, JB, isolator, tracer, end termination, etc. |
| `component_tag` | Tagged component payload | User-facing tag to carry into schedules. |
| `branch_load_a` | Derived from per-circuit current | Load used for cold-cable ampacity and voltage drop. |
| `branch_length_m` | Current cable schedule / project default | Length used for first-pass voltage-drop sizing. |
| `manual_edit_state` | SLD edit tables/payload | Whether topology or cable length has been edited manually. |

First-pass rule:

- Size each generated feeder segment independently using the active topology.
- Where topology is generated and unedited, use the persisted generated branch
  structure.
- Where manual SLD edits exist, either consume them explicitly or mark the cold
  cable result as requiring review. Do not silently ignore manual topology.

## 5. Cable Length Inputs

Current available length bases:

| Length | Source | Current meaning |
| --- | --- | --- |
| `ProjectData.ckt_ln` | Project setup | Generic DB-to-JB length assumption. |
| `ProjectData.loop_ln` | Project setup | Generic JB-to-JB loop assumption. |
| Existing cable schedule length | Cable schedule payload | Generated cable length for current SLD component path. |
| Manual cable schedule override | Cable schedule override tables | User-edited length when present. |
| MI cold lead length | `SelectedMIHeater` | Factory MI cold lead, not upstream cold cable. |
| SR heated length | `PowerDistribution` / selected snapshot | Heating cable length, not cold cable. |

Cold-cable rule:

- Use cold-cable route length from the active topology/cable schedule, not SR
  heated tracer length.
- Treat MI cold lead as a separate factory/interface length from panel/JB cold
  cable unless the future design basis explicitly combines them.
- Store the length basis in every sized-cable result: project default,
  generated SLD, manual override, or imported route/model length.

## 6. Outputs Expected from the Cold Cable Module

Minimum MVP outputs:

| Output | Purpose |
| --- | --- |
| Sized cable type/code | Cable selection result for each feeder segment. |
| Core count | 2C/3C/4C/etc. depending on phase/topology basis. |
| Conductor size | Main cold-cable engineering output. |
| Ampacity check | Cable current capacity after derating. |
| Voltage drop percent | Check against project allowable voltage drop. |
| Voltage at load end | Evidence for heating-cable terminal voltage. |
| Cable length basis | Traceability for route length. |
| Breaker/load compatibility | Verify cable size against protective device and loading. |
| Derating basis | Installation method, ambient, grouping, and correction factors. |
| Panel/load summary | Aggregate connected load and current by DB/panel/branch. |
| Issue status | Selected, rejected, or requires review. |

Later outputs:

- Phase balancing.
- Fault current / short-circuit withstand.
- Earth-loop impedance or equivalent project-specific protection check.
- Cable drum optimization.
- Route-aware optimization using 3D/model data.
- Feeder grouping optimization.
- Panel schedule integration.

## 7. Known Review-Only Assumptions Carried Forward

The cold-cable module must preserve these warnings rather than hiding them:

- SR alternate tracer overrides are review-only and do not currently recalculate
  load, BOQ, breaker size, or cable schedule.
- MI available-alternative overrides are review-only and do not currently drive
  recalculated output.
- MI T-class verdict is review evidence, not final calculated sheath/surface
  approval.
- MI physical JB terminal capacity and gland count are not yet calculated.
- SR pipe-size constructability warnings are review warnings, not hard
  rejection gates.
- SR A/B/C catalogue coefficients are fitted engineering representations; SR
  vendor curve-point interpolation remains a future refinement.
- Existing DB-to-JB and loop lengths are project assumptions unless overridden
  or replaced by model/route data.
- Generated topology prioritizes electrical protection clarity; physical JB
  consolidation is not yet optimized.

## 8. Pre-Cold-Cable Hardening Gate

Claude's deep audit dated 2026-05-29 highlighted validation and robustness
issues around voltage, numeric catalogue fields, and MI TCR handling. I agree
that these are useful hardening items before we rely on the hot-engineering
output as an input contract for cold-cable sizing.

Recommended short hardening pass before or at the beginning of cold-cable work:

1. Validate project voltage and catalogue voltage as positive before voltage
   correction.
2. Reject/log SR catalogue rows with missing or non-numeric `A_Coeff`,
   `B_Coeff`, `C_Coeff`, or voltage fields before power calculation.
3. Treat MI `tcr_per_degree_c = 0.0` as an explicit valid value rather than a
   falsy missing value.
4. Refactor SR power polynomial evaluation into one helper so nominal and
   low-voltage calculations cannot drift.
5. Add focused tests for zero voltage, bad SR coefficients, and zero MI TCR.

These items are not a reason to redesign SR/MI selection again. They are
guardrail work to make the next module consume cleaner, more predictable
outputs.

## 9. Recommended Cold-Cable Build Sequence

### Pass CC-01: Data Contract and Result Model

- Define normalized cold-cable input rows from `PowerDistributionBranch`.
- Add cold-cable result model(s) with sizing status, cable selection, ampacity
  evidence, voltage-drop evidence, and length basis.
- Store one result per feeder segment, not merely one result per process line.

### Pass CC-02: First-Pass Cable Catalogue

- Add or confirm cable catalogue schema: conductor size, core count, material,
  insulation, voltage grade, ampacity, resistance/reactance, installation basis,
  and source document.
- Keep catalogue validation/gating explicit, similar to MI.

### Pass CC-03: Ampacity and Voltage-Drop Calculation

- Size cable for per-circuit current.
- Calculate voltage drop using selected cable impedance/resistance and route
  length.
- Record voltage-drop percent and end voltage.
- Reject or flag segments exceeding allowable voltage drop.

### Pass CC-04: UI and Export

- Add cold-cable result tab or section.
- Add schedule/export columns for selected cable size, voltage drop, ampacity
  margin, length basis, and review status.
- Show warning badges where topology is manually edited or length basis is
  assumed.

### Pass CC-05: Optimization

- Optimize cable size and route/grouping choices after the basic calculation is
  stable.
- Introduce panel/load summaries and phase balancing only after cable sizing is
  credible.

## 10. Immediate Decision Points

Before coding the cold-cable module, decide:

1. Which cable standard/catalogue table is the first supported sizing basis.
2. Whether the first MVP sizes only single-phase heating feeders or also
   3-phase/trunk feeders.
3. Whether manual SLD edits should block cold-cable calculation or be consumed
   as active topology.
4. Whether MI cold lead is treated only as factory scope in MVP or included in
   voltage-drop allocation.
5. Whether voltage-drop allowance is checked per feeder segment, total path, or
   allocated across DB-to-JB plus downstream branches.

