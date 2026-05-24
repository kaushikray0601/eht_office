# MI Cable Model Design

Date: 2026-05-24  
Status: Pass 4 autonomous SR-to-MI boundary note

## Purpose

This note records the first implementation boundary for the Mineral Insulated
heating cable module. It is intentionally limited to data structures and review
discipline. It does not claim that MI selection logic is implemented.

## Design Boundary

MI cable is not being added to the SR tracer-selection engine. MI will use a
separate selection path because it is a factory-engineered series-resistance
heater set, not a field-cut parallel SR cable.

SR result semantics:

- selected tracer catalogue row
- spiral factor
- ordered SR length
- per-circuit current and breaker data

MI result semantics:

- selected heater resistance code
- engineered heated length
- cold-lead option and calculated cold-lead electrical effect
- total power and W/m
- nominal and cold-start current
- published sheath-temperature / T-class verdict
- calculation evidence snapshot

## Catalogue Discipline

No fabricated MI catalogue data is allowed.

The previous demo MI population command was removed, and the local placeholder
MI rows were purged. Future MI catalogue rows must be loaded only from verified
vendor documentation. The `source_document` field on `MICableFamily` records
that provenance.

`MICableFamily.is_validated` defaults to false. The future MI selection engine
must refuse to select from unvalidated catalogue data.

## Key Model Decisions

### MICableFamily

The family stores vendor-level suitability and safety limits:

- voltage
- maximum maintain temperature
- maximum exposure temperature
- maximum sheath temperature
- maximum watt density
- minimum and maximum circuit length
- hazardous-area compatibility fields
- source document
- validation status

The hazardous-area fields are simple strings for Pass 1, matching the SR
catalogue filtering style. A richer approval model can be added after real
catalogue governance exists.

### MICableHeater

The heater stores the specific resistance code and current limits.

Resistance is stored as `resistance_ohms_m`. The old placeholder field used
ohms per kilometre and was removed because Pass 2 calculations need ohms per
metre directly.

Cold-lead resistance and ampacity are stored at heater level because MI current
depends on the selected heater resistance/size. This is deliberately not a
family-level field.

### MIColdLeadOption

Cold-lead options are linked to `MICableHeater`. The selected option provides
the length; the heater provides cold-lead resistance per metre and ampacity.

Future calculation basis:

```text
R_cold_lead_total = cold_lead_resistance_ohms_m * cold_lead_length_m
```

### SelectedMIHeater

The selected result stores both catalogue references and calculated snapshot
values. This avoids report drift if catalogue data is revised later.

It stores:

- line reference
- heater reference
- cold-lead option reference
- cold-lead code and length snapshot
- heater and cold-lead resistance snapshot
- nominal power/current values
- cold-start current
- published sheath-temperature evidence
- project T-class limit
- T-class verdict
- JSON calculation basis

## Explicitly Deferred

The following are not implemented in Pass 1:

- MI selection algorithm
- MI electrical iteration
- three-phase star/delta
- multi-heater parallel arrangements
- constant wattage / constant power cable
- MI BOQ/report integration
- MI SLD integration
- MI star-point topology
- heat-loss model changes
- SR calculation changes

## Pass 2 Gate

Before MI selection logic is accepted, it needs engineering tests against at
least two published vendor worked examples or verified EPC/vendor calculation
benchmarks. Model-structure tests alone are not enough to prove MI engineering
correctness.

## Pass 2 Selector Skeleton Added

The first standalone selector lives in `eht/calculations/mi_selection.py`.

Current selector scope:

- single-phase only
- validated catalogue data only
- selected vendor only
- family suitability checks for voltage, maintain temperature, exposure
  temperature, circuit length, area zone, gas group, and T-class rating
- heater/cold-lead candidate evaluation
- cold-lead voltage-drop effect
- heater and cold-lead current limit checks
- low-voltage heat-delivery check
- high-voltage watt-density/current check
- vendor-published sheath temperature compared against project T-class limit
- MI-specific diagnostics written to `mi_selection_status` and
  `mi_selection_rejection_reasons`

Current selector exclusions:

- no pipeline/orchestration integration
- no BOQ/report/SLD integration
- no three-phase star/delta
- no multi-heater parallel arrangements
- no first-principles sheath-temperature calculation

Because the real MI catalogue is intentionally empty, project runs will not
select MI until verified vendor catalogue rows are loaded. The selector tests
create their own validated rows inside the test database only.

## Pass 3 Persistence Boundary Added

`SelectedMIHeater` now stores both selected and rejected MI outcomes.

Persistence rules:

- selected MI rows store catalogue references to `MICableHeater` and
  `MIColdLeadOption`
- selected MI rows also store calculated snapshot values such as heated length,
  total heater resistance, cold-lead resistance, nominal power, nominal current,
  cold-start current, published sheath-temperature evidence, and T-class verdict
- rejected MI rows can be stored with blank catalogue references
- rejected MI rows carry `selection_status` and
  `selection_rejection_reasons`, so reviewers can see why no MI selection was
  made
- workspace cleanup and calculation-result replacement now remove stale MI
  result rows, matching the SR cleanup discipline

This pass still does not enable MI in the main SR production calculation path.
The storage hook accepts an explicit `selected_mi_heaters` payload so the next
orchestration pass can be reviewed separately.

## Pass 4 Autonomous SR-to-MI Boundary

The manual project-level SR/MI switch was removed. The calculation philosophy is
now:

- SR is always attempted first
- MI is selected automatically only when published SR catalogue temperature
  limits are exceeded for the line
- when SR is valid and a validated MI option also exists, the MI result is kept
  as an `available_alternative` candidate for later case-by-case override work
- when SR is rejected for non-temperature reasons, MI is not used as a silent
  substitute

Current MI fallback output:

- selected MI fallback rows are persisted through `selected_mi_heaters`
- rejected MI fallback attempts carry diagnostic reasons
- MI alternatives are stored with `selection_status = available_alternative`

MI electrical distribution, MI BOQ, cable schedule, SLD topology, and result-page
presentation are still separate future passes.

## Pass 5 Result and SLD Visibility

MI selection records are now visible outside the calculation core.

Result page/export:

- `SelectedMIHeater` rows appear in a dedicated MI selection section
- SR line rows show whether an MI candidate is available for the same line
- result Excel includes an `MI Selection` sheet with MI status, selection mode,
  heater, cold lead, power, current, T-class evidence, and rejection reasons

SLD review:

- validated MI alternatives are included in tracer-selection metadata as
  calculated alternatives with stable `MI:<heater part number>:<cold lead code>`
  identifiers
- the SLD tracer editor can display MI heater/cold-lead evidence
- users can save an MI available-alternative override on a tracer node
- MI overrides are still review-only; SR load, BOQ, cable schedule, and power
  distribution are not recalculated from that override yet

## Pass 6 Review Hardening

Pass 6 closes the first review issues found after the result/SLD visibility pass.

Resolved:

- MI SLD override keys no longer use transient `SelectedMIHeater.id` values.
  They now use the stable heater part number and cold-lead option code, so a
  recalculation can delete and recreate MI result snapshots without silently
  dropping the user's override.
- MI override matching still requires the same heater/cold-lead option to be
  present as a current `available_alternative` for that line. A stale or
  no-longer-valid MI option is not silently accepted.
- MI fallback rows that do not yet have SR-style `ProcessLineCalculation` rows
  are visible in the main result table as `MI fallback selected`, with MI load
  distribution clearly marked as pending.
- The dead SR alternate ORM lookup in SLD tracer metadata application was
  removed; the active selected option now comes from the unified option payload.

Deferred at the end of Pass 6:

- MI fallback rows still do not feed panel loading, breaker sizing, BOQ, cable
  schedule, or power distribution. Those are future MI electrical/reporting
  passes.

## Pass 7 MI Downstream Electrical Output

Pass 7 adds the first downstream electrical path for automatically selected MI
fallback lines.

Implemented:

- selected MI fallback rows now produce single-heater electrical power parameters
  using the MI snapshot current and power values
- MI breaker sizing uses the cold-start current, project maximum breaker size, and
  project breaker loading restriction
- MI selection rejects candidates whose high-voltage/cold-start current exceeds
  the project breaker loading limit; one MI heater is not silently split into
  multiple circuits
- MI fallback lines now feed the existing power-distribution branch generator, so
  SLD and cable-schedule rows are generated from the same branch model used by SR
- BOQ now carries MI-specific items:
  - `MI_HEATER_SET` in each selected MI fallback line
  - `MI_HEATED_LENGTH` for the factory heated length
  - `MI_COLD_LEAD_LENGTH` for the selected cold-lead length
- `ProcessLineCalculation` rows for MI fallback store the MI heater part number
  and mark `remarks = MI_SINGLE_HEATER_MVP` so result/report code can distinguish
  the calculation basis

Still deferred:

- multi-heater MI optimization and splitting
- three-phase MI arrangements
- detailed MI cold-lead cable sizing beyond the selected catalogue cold-lead
  snapshot
- re-consuming SLD MI overrides into a full recalculation run

## Pass 8 MI Alloy Resistance Temperature Factor

Pass 8 starts using the existing `MIAlloyTempFactor` table.

Purpose of the table:

- MI heater catalogue resistance is normally recorded at a reference temperature
  such as 20°C.
- Heater resistance changes with conductor/alloy temperature.
- `MIAlloyTempFactor` stores `R(T) / R(reference)` multipliers by `alloy_type`
  and `temperature_c`.

Implemented:

- MI selection now queries `MIAlloyTempFactor` for each validated MI family alloy.
- Heater resistance at maintenance temperature is corrected before checking heat
  delivery and nominal current.
- Heater resistance at startup temperature is corrected before checking cold-start
  current and breaker-loading suitability.
- Factor rows are linearly interpolated between known temperatures.
- Temperatures outside the available factor range use the nearest endpoint,
  avoiding unbounded extrapolation.
- If no factor rows exist for the alloy, the engine keeps the old multiplier of
  `1.0` and records `default_no_factor_table` in the selection basis.

Recorded evidence:

- `selection_basis.resistance_temperature_basis` includes the alloy, factor row
  count, maintain/startup temperatures, selected multipliers, and interpolation
  method.

Current live-data note:

- The project database currently contains MI family/heater/cold-lead catalogue
  rows, but no `MIAlloyTempFactor` rows yet.
- The project database also currently has no validated MI family rows, so the
  production selector will keep rejecting MI until catalogue families are marked
  `is_validated=True` after engineering review.
