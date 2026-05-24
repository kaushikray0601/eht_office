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

Implemented in Pass 8, refined in Pass 10:

- MI selection queries `MIAlloyTempFactor` by heater conductor material, not by
  family sheath alloy.
- Heater resistance at maintenance temperature is corrected before checking heat
  delivery and nominal current.
- Heater resistance at startup temperature is corrected before checking cold-start
  current and breaker-loading suitability.
- Factor rows are linearly interpolated between known temperatures.
- Temperatures outside the available factor range use the nearest endpoint,
  avoiding unbounded extrapolation.
- If no TCR or factor rows exist for the heater conductor material, the engine
  keeps the old multiplier of `1.0` and records `default_no_factor_table` in the
  selection basis.

Recorded evidence:

- `selection_basis.resistance_temperature_basis` includes sheath alloy,
  conductor material, TCR, factor row count, maintain/startup temperatures,
  selected multipliers, and correction method.

Current live-data note:

- The project database currently contains MI family/heater/cold-lead catalogue
  rows, but no `MIAlloyTempFactor` rows yet.
- The project database also currently has no validated MI family rows, so the
  production selector will keep rejecting MI until catalogue families are marked
  `is_validated=True` after engineering review.

## Pass 9 MI T-Class Review Gate Correction

Pass 9 removes a false hard rejection in MI selection.

Corrected basis:

- `max_sheath_temp_c` on an MI family is the published cable survival/rating
  limit.
- It is not the calculated installed sheath/surface temperature for the selected
  circuit.
- Therefore a 400-600°C published maximum sheath rating must not be compared
  directly against T1-T6 project limits as if it were the operating surface
  temperature.

Implemented:

- MI selection no longer rejects candidates when `max_sheath_temp_c` is above
  the project T-class limit.
- MI T-class verdict remains `review` until a later pass adds a real
  sheath/surface-temperature calculation basis.
- `selection_basis.t_class_review_reason` records whether review is required
  because T-class is design-specific, or because catalogue/project T-class
  evidence is missing.
- Regression coverage now uses a real catalogue-like MI family with a 600°C
  published maximum sheath rating under a T3 project basis and confirms it
  remains selectable.

Deferred:

- Calculated MI sheath/surface temperature.
- Vendor-specific T-rating validation curves/tables where available.
- Final hazardous-area compliance report wording for MI circuits.

## Pass 10 Heater-Level Resistance Temperature Basis

Pass 10 corrects the resistance-temperature correction key.

Corrected basis:

- `MICableFamily.alloy_type` describes the MI sheath/tube alloy.
- The sheath does not determine heater resistance in normal MI heater design.
- Heater resistance temperature behavior belongs to the conductor/resistance
  alloy for the specific heater code.

Implemented:

- Added `MICableHeater.tcr_per_degree_c` with default `0.0`.
- Heater TCR is now the primary resistance-temperature correction method when
  populated.
- `MIAlloyTempFactor` remains available as a fallback lookup table, but it is
  keyed by `MICableHeater.conductor_material`.
- A factor row for sheath alloy, such as `Alloy 825`, no longer applies to all
  heater codes in the family.
- The resistance evidence payload now separates:
  - `sheath_alloy_type`
  - `conductor_material`
  - `tcr_per_degree_c`
  - `factor_lookup_key`

Data implication:

- Existing populated MI heater rows need conductor/TCR review.
- If reliable TCR values are available from vendor tables, load them directly
  into `MICableHeater.tcr_per_degree_c`.
- If full R-vs-T curves are available later, populate `MIAlloyTempFactor` with
  keys matching `MICableHeater.conductor_material`.

Deferred:

- Normalizing conductor material names into controlled choices.
- Data import validation to reject populated MI heaters with blank conductor
  material and zero TCR when temperature correction is required.

## Pass 11 MI Cold-Start Temperature Basis

Pass 11 fixes the MI cold-start temperature basis used for startup resistance
and cold-start current.

Corrected basis:

- A literal `startup_t = 0°C` is a valid project value and must not fall back to
  maintain temperature.
- MI cold-start current is governed by the conductor temperature at energisation.
- For the current engineering basis, the conservative temperature is the lower
  of project `startup_t` and `min_amb_t` when both are available.

Implemented:

- Replaced the old truthiness fallback with explicit `None` handling.
- Added `cold_start_temperature_basis` evidence under
  `selection_basis.resistance_temperature_basis`.
- The evidence records:
  - selection rule
  - selected temperature source
  - selected cold-start temperature
  - candidate `startup_t` and `min_amb_t` values used in the comparison
- Added regression tests for:
  - `startup_t = 0.0°C`
  - `min_amb_t` colder than `startup_t`

Deferred:

- A future project-level standard option may allow companies to choose whether
  MI startup basis is conservative ambient/process minimum or a client-specified
  energisation temperature.

## Pass 12 MI Catalogue TCR Population Path

Pass 12 makes the MI catalogue seed/update command compatible with the
heater-level TCR basis introduced in Pass 10.

Implemented:

- `populate_mi_catalogue` now derives `conductor_material` and
  `tcr_per_degree_c` for published Thermon, nVent, and Chromalox heater codes.
- Added `--update` mode so an already-loaded catalogue can be refreshed instead
  of leaving blank TCR fields untouched by `get_or_create`.
- Existing family validation status is preserved during update; the command does
  not set `is_validated=True`.
- Existing family source/rating fields, heater resistance/current/TCR fields,
  and cold-lead lengths are refreshed from the command data in update mode.

Representative TCR basis:

- Thermon MIQ: Nickel-Chromium, `0.000088 /°C`.
- nVent HAF/HAA: Nickel-Chromium, `0.000088` or `0.000085 /°C`.
- nVent HAQ/HAP/HAC: nickel/alloy conductor groups from published code prefixes.
- Chromalox B-series: TCR inferred from published resistance-code groups.

Verification:

- Tests confirm fresh population writes conductor/TCR values.
- Tests confirm `--update` repairs existing blank TCR rows without clearing a
  manually validated family flag.

Still requires engineering review:

- The command remains a catalogue-loading aid, not a validation authority.
- Families must remain `is_validated=False` until source documents and extracted
  values are checked by an engineer.

## Pass 13 Real-Catalogue Smoke Test

Pass 13 adds the first controlled selection test using catalogue rows created by
the MI population command.

Purpose:

- Prove that command-loaded MI catalogue data is structurally usable by the
  selector.
- Keep the validation gate intact by validating the family only inside the
  isolated test database.
- Confirm TCR correction, cold-start basis, and catalogue selection evidence all
  work together on real-shaped catalogue data.

Implemented:

- The test loads Thermon MIQ data through `populate_mi_catalogue`.
- The test manually sets only the test copy of the Thermon MIQ family to
  `is_validated=True`.
- The MI selector then evaluates a high-temperature line and selects a published
  MIQ heater/cold-lead option.
- Assertions confirm:
  - selected family/vendor are from the command-loaded catalogue
  - selected heater is `MIQ-11EOH-2S`
  - TCR basis is `Nickel-Chromium` with `0.000088 /°C`
  - maintain resistance is above catalogue-base resistance
  - cold-start resistance is below catalogue-base resistance when `min_amb_t` is
    colder than the 20°C reference
  - cold-start temperature evidence records `min_amb_t` as the selected source

Limit:

- This is a structural smoke test, not the final vendor worked-example
  benchmark. It proves the engine can use real-shaped catalogue data, but it
  does not yet compare against a published vendor design output.

## Pass 14 User-Facing MI Fallback Output

Pass 14 tightened the MVP output path for uploaded line lists where high-temperature lines automatically move from SR to MI.

Implemented:

- Result summaries split SR and MI result counts, connected load, and heating cable length.
- Successful automatic MI fallback no longer appears as an unresolved SR selection failure in the result-page warning count. The SR rejection evidence remains stored, but the user-facing warning is reserved for lines that still need action.
- The per-line result table shows a heating-cable type badge. MI fallback rows are labelled as automatic fallback and show cold-lead length beside the heated MI length.
- The result Excel export now includes heating cable type, heating cable length, length basis, SR-only ordered length, MI heated length, MI cold-lead option, and MI cold-lead length.

Current limitation:

- MI output is still single-heater-set MVP logic. Multi-heater splitting, three-phase MI grouping, and final vendor worked-example validation remain future passes.

## Pass 15 Rejected MI Fallback Diagnostics

Pass 15 improves the user-facing behavior when a high-temperature line triggers automatic MI fallback but still cannot receive a selected MI heater.

Implemented:

- Rejected MI fallback rows are no longer rendered as empty design outputs with `0.00 W/m`, `0.00 W`, and `0.00 A`.
- The MI Selection Records table now shows the rejection message, reason code, evidence, and next action for rejected MI rows.
- The result page now warns specifically when high-temperature lines triggered MI fallback but did not receive a selected MI heater.
- Rejected MI fallback rows are kept out of the per-line design summary, because they are diagnostics, not issued design outputs.
- The MI Selection export now includes rejection code, rejection message, diagnostic evidence, and next action.

Observed manual-test implication:

- If MI catalogue rows exist but are not marked `is_validated=True`, automatic MI fallback correctly rejects the line. The user should now see that the blocker is catalogue validation, not a mysterious zero-output design.
