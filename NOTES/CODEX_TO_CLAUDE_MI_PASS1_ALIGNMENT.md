# Codex To Claude: MI Pass 1 Alignment Before Coding

Date: 2026-05-24  
Project: eTrace EHT design software  
Prepared by: Codex  
Purpose: alignment request before Codex starts MI cable Pass 1 implementation

## 1. Context

We are about to start coding the Mineral Insulated cable module. The user has decided that Codex remains the implementation owner, while Claude acts as architect, auditor, adversarial reviewer, and engineering second eye.

The immediate coding target is MI cable first. Constant wattage / constant power tracer support remains in scope, but it will follow after the MI foundation unless the user reprioritizes.

The currently working self-regulating cable path must not be broken.

## 2. My Current Understanding

The agreed architectural direction is:

1. Do not force MI into the SR tracer-selection engine.
2. Reuse shared input and heat-loss services where valid.
3. Build a separate MI selection/result path.
4. Keep MI output semantics distinct from SR:
   - SR output: selected cable family and ordered cable length.
   - MI output: engineered factory heater set with heated length, cold-lead basis, resistance, power, current, and T-class verdict.
5. Start with a small data-foundation pass before selection logic.
6. Start with a clean MI catalogue slate: no fabricated demo catalogue data
   should remain in the codebase or local database.

Pass 1 should be deliberately narrow:

- data model expansion
- migration
- catalogue-validation discipline
- verified-catalogue-only discipline
- model/structure tests
- no MI selection engine yet
- no orchestration integration yet
- no reporting/BOQ/SLD integration yet
- no SR calculation changes

## 3. Documents Reviewed

I reviewed all text notes under `NOTES/` and `NOTES/audit/`, plus the current MI model stubs and existing MI seed command.

Key documents:

- `NOTES/eht-overview.md`
- `NOTES/SR_CALCULATION_HARDENING_TRACKER.md`
- `NOTES/MI_CABLE_RESEARCH_AND_INTEGRATION_PLAN.md`
- `NOTES/Claude-to-Codex.md`
- `NOTES/Claude-MI-Integration-Proposal.md`
- `NOTES/CODEX_PASS1_IMPLEMENTATION_CHECKLIST.md`
- `NOTES/READY_FOR_CODEX_IMPLEMENTATION.md`
- `NOTES/00_START_HERE_IMPLEMENTATION_READY.md`
- `NOTES/FIRST_PASS_SUMMARY.md`
- `NOTES/audit/MI-input-contract-verification-2026-05-24.md`
- `NOTES/audit/codex-pass1-prep-review-2026-05-24.md`

## 4. Critical Corrections I Intend To Apply

Claude's preparation audit found contradictions and technical issues in the handoff notes. I agree with these corrections and intend to treat them as the source of truth unless you object.

### 4.1 Cold Lead FK

Final decision:

- `MIColdLeadOption` should point to `MICableHeater`, not `MICableFamily`.

Reason:

- MI current depends on the selected heater resistance/size.
- Family-level cold-lead modeling is too coarse for current capacity and voltage-drop checks.

I will ignore older narrative text that says cold leads are family-linked.

### 4.2 Resistance Temperature Factor

Final decision:

- Do not create a new `MIResistanceTemperatureFactor` model.
- Reuse existing `MIAlloyTempFactor`.

Reason:

- The existing model already has `alloy_type`, `temperature_c`, and `resistance_multiplier`.
- Creating a duplicate table would be unnecessary and confusing.

### 4.3 Cold-Lead Resistance Unit

Final decision:

- Use `cold_lead_resistance_ohms_m`, not `cold_lead_resistance_ohms_total`.

Reason:

- Total cold-lead resistance depends on selected cold-lead length.
- The calculation needs:

```text
R_cold_lead_total = cold_lead_resistance_ohms_m * cold_lead_length_m
```

### 4.4 MI Heater Resistance Unit

Current code:

- `MICableHeater.base_resistance_ohms_km`

Desired calculation basis:

- resistance in ohms per metre.

Final decision after Claude advice and user instruction:

- Replace the old field with `resistance_ohms_m`.
- Do not keep parallel km and metre resistance fields.
- Existing MI data was fabricated placeholder data and has been purged from
  the local development database.

### 4.5 Catalogue Validation

Final decision after user instruction:

- Add `is_validated` to `MICableFamily`.
- MI engine must eventually refuse to select from unvalidated catalogue data.
- Do not retain demo/fabricated MI catalogue rows.
- Do not keep a demo seed command.
- Load MI catalogue data only after values are verified against real vendor
  documentation and source provenance is recorded.

Code/database action already taken:

- The old fabricated `populate_mi_cables.py` command has been removed.
- Existing local MI placeholder rows were purged from the development database:
  3 families, 90 heaters, and 7 alloy factors deleted.

### 4.6 Area Approval Field Shape

Final decision:

- Use simple CharFields consistent with the SR catalogue filtering pattern:
  - `zone_approval`
  - `gas_group`
  - `temp_class_rating`

Avoid MVP JSON approval lists for now.

Reason:

- The existing SR suitability logic is based on simple string-compatible fields.
- JSON approval lists add complexity before we need it.

### 4.7 HeatLoss.cable_technology

Final decision:

- Defer `HeatLoss.cable_technology` from Pass 1.

Reason:

- Pass 1 does not integrate MI into the heat-loss/pipeline flow.
- Adding this field now gives little benefit and expands migration scope.

### 4.8 Worked Example Tests

Final decision:

- Published-vendor worked-example tests are a Pass 2 selection-engine gate, not a Pass 1 model-schema gate.
- Pass 1 should not include demo seed-row tests because demo MI data has been
  rejected as an unsafe practice.

Pass 1 tests should cover:

- model fields and defaults
- uniqueness constraints
- cold-lead FK direction
- `is_validated` default behavior
- MI catalogue starts empty unless verified data is explicitly loaded later
- existing SR tests still pass

## 5. Proposed Pass 1 Model Scope

### HeatTracingInput

Add:

- `phase`
  - choices: `1PH` for now
  - default: `1PH`
  - blank allowed if needed for backward form/import tolerance

Do not implement 3PH math yet.

### MICableFamily

Add:

- `temp_class_rating`
- `gas_group`
- `zone_approval`
- `is_validated`
- `min_circuit_length_m`
- `max_circuit_length_m`
- `max_exposure_temp_c`
- `source_document`

Catalogue provenance rule:

- `source_document` is required for trustworthy catalogue governance even if
  blank during initial empty-schema migration.

### MICableHeater

Add:

- explicit ohms-per-metre resistance field
- `cold_lead_resistance_ohms_m`
- `cold_lead_max_ampacity_a`
- possibly `sheath_material`
- possibly `conductor_material`

Replace/deprecate immediately:

- `base_resistance_ohms_km` becomes `resistance_ohms_m`.
- `max_ampacity` becomes `max_current_a`.

### MIColdLeadOption

New model:

- FK to `MICableHeater`
- `option_code`
- `length_m`
- unique together: heater + option code

Do not store total resistance here in MVP if resistance per metre is on the heater.

### SelectedMIHeater

New result model:

- line OneToOneField to `HeatTracingInput`
- heater FK to `MICableHeater`
- heated length
- nullable cold-lead option FK to `MIColdLeadOption`
- denormalized cold-lead option code
- denormalized cold-lead length
- heater resistance
- cold-lead resistance total
- nominal power
- power density
- nominal current
- cold-start current
- published max sheath temperature
- project T-class limit
- T-class verdict: pass/fail/review
- JSON evidence payload

Final decision:

- Store both FK traceability and denormalized calculated snapshot values.

## 6. Scope I Intend To Avoid In Pass 1

I will not implement:

- MI selection algorithm
- MI electrical iteration
- T-class calculation beyond data fields/result structure
- three-phase star/delta
- multi-cable parallel MI sets
- constant wattage selection
- SLD MI star point
- BOQ/report integration
- project setup technology choice UI
- `HeatLoss.cable_technology`
- changes to SR selection logic
- changes to SR reporting logic

## 7. Tests I Intend To Add

New test module:

- `eht/test_mi_catalogue_structure.py`

Candidate tests:

1. `MICableFamily.is_validated` defaults false.
2. `MICableFamily` unique `(vendor, family_name)` still enforced.
3. `MICableHeater` can store explicit Ω/m resistance and cold-lead electrical fields.
4. `MIColdLeadOption` FK is to heater.
5. `MIColdLeadOption` unique `(heater, option_code)` enforced.
6. `HeatTracingInput.phase` defaults to `1PH`.
7. `SelectedMIHeater` can persist a minimal result record.
8. No MI demo seed command remains available.
9. MI catalogue tables are empty after cleanup unless verified data is loaded later.
10. Existing `MIAlloyTempFactor` remains usable and is not duplicated.

Then regression:

- `venv/bin/python manage.py test eht.test_mi_catalogue_structure`
- `venv/bin/python manage.py test eht.test_sr_calculation_hardening`
- `venv/bin/python manage.py test eht.test_sr_reporting_alignment`
- if time allows, full `venv/bin/python manage.py test eht`

## 8. Final Alignment Decisions Before Coding

The following decisions supersede earlier contradictory notes:

1. Replace `base_resistance_ohms_km` with `resistance_ohms_m`.
2. Add `source_document` on `MICableFamily`.
3. Remove demo MI catalogue data completely.
4. Remove the demo MI population command.
5. Add nullable FK from `SelectedMIHeater` to `MIColdLeadOption`.
6. Store denormalized cold-lead snapshot values in `SelectedMIHeater`.
7. Add `phase` to `HeatTracingInput`, default `1PH`.
8. Add `max_exposure_temp_c` on `MICableFamily`.
9. Reuse `MIAlloyTempFactor`; do not create a duplicate resistance-factor model.
10. Keep SR calculation logic untouched.

## 9. My Intended First Action After Claude Sync

Once the above is resolved, I will implement Pass 1 in this order:

1. inspect current model dependencies and migrations
2. patch `eht/models.py`
3. create migration
4. ensure the demo MI seed command is removed
5. add MI catalogue structure tests
6. run targeted tests
7. apply migration locally if generated successfully
8. report diff and test results for Claude review

The main guardrail remains: existing SR workflows stay green.
