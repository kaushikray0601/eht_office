# MI/CW Integration: First Pass Proposal - SUMMARY

**Status:** Ready for user decision  
**Key Question:** Approve the data-model-first approach below?

---

## The Situation

- **SR is hardened:** 158 tests green, calculation stable
- **MI is next:** Different physics, different catalogue, different result semantics
- **Critical constraint:** Do NOT break SR path while adding MI

---

## Proposed First Pass: MI Data Model Foundation

### What We'll Build (Pass 1)

**4 focused tasks:**

1. **MI Catalogue Models Migration**
   - Expand `MICableFamily`, `MICableHeater`, `MIAlloyTempFactor` with real fields
   - Add new `SelectedMIHeater` result model (separate from `SelectedTracer`)
   - Add new `MIColdLeadOption` model (MI-specific product component)
   - Add new `MIResistanceTemperatureFactor` (temperature-dependent R correction)
   - Extend `HeatLoss` with optional `cable_technology` field

2. **Seed Catalogue Data**
   - Create `populate_mi_catalogues_seed.py` management command
   - Load representative real Thermon MIQ configurations from public spec sheet
   - Load representative real nVent Raychem MI options from public guide
   - NO synthetic data; only real vendor documentation

3. **Catalogue Structure Tests**
   - Create `test_mi_catalogue_structure.py` (new focused test module)
   - Model schema tests (ensure fields work as intended)
   - Integration tests verify seed data is realistic
   - ≥8 tests, all passing

4. **Documentation**
   - Create `eht/mi_model_design.md` explaining why MI is separate
   - Clarify cold-lead vs heater distinction
   - Document catalogue data quality discipline

### What's NOT in Pass 1

- ❌ No MI selection logic
- ❌ No calculation changes  
- ❌ No SR code touched
- ❌ No pipeline integration yet
- ❌ No orchestration changes

**Why?** Build foundation first, keeps scope tiny, easy review, zero risk to SR.

---

## Key Architectural Decisions Validated ✓

### ✓ Separate MI Engine (Confirmed Correct)

| Aspect | SR | MI | Why Separate |
| --- | --- | --- | --- |
| **Output meaning** | "Order X meters of cable" | "Order factory set: length A, cold leads B, config C" | Semantics differ |
| **Selection basis** | Power curve @ maintain temp | Required W/m + resistance + sheath temp check | Different equations |
| **Cold leads** | Afterthought | First-class design element (carries current, affects power) | Different modeling |
| **T-class role** | Output limit + cert check | Sheath temp @ design W/m is central gate | Different verification |

**Data consequence:** New `SelectedMIHeater` result model (not reusing `SelectedTracer`).

### ✓ Cold-Lead Modeling

Cold leads will be modeled as **ForeignKey to family** (not heater), e.g.:
- Thermon MIQ offers CL-3M, CL-5M, CL-10M options per family
- Each has fixed length + resistance
- Carries full heater current → ampacity check needed
- Reduces available heater voltage: `V_heater = V_supply - I·R_cold_lead`

**Data consequence:** New `MIColdLeadOption` model linked to `MICableFamily`.

### ✓ Sheath Temperature Verification (Pass 1 Foundation)

This pass sets up the model fields; selection logic comes in Pass 2:

- Store vendor-published max sheath temp rating (for design condition)
- Store project T-class numeric limit (e.g., T4 = 135°C)
- Store actual calculated/lookup sheath temp
- Store pass/fail/review verdict
- If vendor data missing → mark as "review required" (not a hard fail)

---

## Diff Footprint

Total: **~800 LOC** across 6 files:

```
eht/models.py                                  (+150 LOC: expanded MI models)
eht/migrations/00xx_mi_catalogue_expansion.py  (+150 LOC: migration)
eht/management/commands/populate_mi_catalogues_seed.py  (+200 LOC: seed data)
eht/test_mi_catalogue_structure.py             (+250 LOC: 8+ model tests)
NOTES/eht/mi_model_design.md                   (+50 LOC: design rationale)
(No changes to pipeline, cal, tracer_selection, SR logic)
```

---

## Validation

After Pass 1 merges:

```bash
# All should pass
python manage.py migrate
python manage.py test eht.test_mi_catalogue_structure  # NEW: ≥8 tests
python manage.py test eht  # EXISTING: 158 SR tests + new MI model tests

# Verify no SR regressions
python manage.py test eht.test_sr_calculation_hardening
python manage.py test eht.test_sr_reporting_alignment
```

---

## Why This Order? (Why Not Start with Selection Logic?)

**Starting with models first:**

✓ **Lower risk:** No calculation logic = no way to break SR  
✓ **Clearer architecture:** Data model forces discipline on what MI needs  
✓ **Faster iteration:** Pass 2 (selection logic) can be written faster once schema is solid  
✓ **Better testing:** Model tests validate data quality before calculation uses it  
✓ **Matches SR pattern:** SR_CALCULATION_HARDENING_TRACKER started with model work too  

**If we started with selection logic first:**

✗ More complex diff (models + logic + tests all entangled)  
✗ Risk of wrong schema discovered mid-implementation  
✗ Hard to review (too much happens at once)  
✗ Harder to isolate bugs (is it a model problem or selection logic?)  

---

## Decisions Made ✓

### 1. Cold-Lead Modeling: **FK to Heater**

**Decision:** Foreign Key to Heater (not Family), because current depends on heater size/resistance. Family-level grouping is too coarse.

**Flagged as provisional:** "FK to Heater for now; revisit once real vendor catalogue data (Thermon MIQ, nVent MI) is loaded and we see how it's actually sold."

**Rationale (from audit):** Series current varies by heater size; T-class/ampacity checks require per-heater cold-lead data.

### 2. Seed Data Timing: **Populate NOW (Pass 1)**

**Decision:** Load real Thermon MIQ + nVent Raychem MI configurations in Pass 1.

**Why:** Validates schema with real data before selection logic is written. Aligns with audit finding that catalogue schema must be correct before MI engine code starts.

### 3. SelectedMIHeater Fields: **Simplify for MVP**

**Decision:** Remove comprehensive T-class fields from MVP; keep only pass/fail verdict.

**Fields kept:** heater FK, heated_length, cold_lead FK, resistance, power, current, sheath_temp_verdict (pass/fail/review only).  
**Fields deferred:** detailed temperature calculations, per-scenario analysis.

**Why:** MVP gate is vendor-published sheath temp check only, not thermal modeling.

---

## Critical Audit Findings: MVP Blockers Identified ⚠️

The MI Input Contract Verification audit (NOTES/audit/MI-input-contract-verification-2026-05-24.md) identified these **must-have fields before MI selection engine is written:**

### MVP Blockers (Pass 1 must include)

1. **`phase` field on HeatTracingInput**
   - CharField with choices: `[('1PH', 'Single Phase')]` for now
   - Default: `'1PH'` (so all existing SR lines unaffected)
   - Why: MVP builds 1-phase only; field must exist to prevent future confusion

2. **T-class / Gas Group / Zone on MICableFamily**
   - T-class rating: 'T1', 'T2', 'T3', 'T4', 'T5', 'T6' (required for gate)
   - Gas group: 'IIA', 'IIB', 'IIC' (for hazardous area filtering, mirrors SR)
   - Zone/ATEX approval (optional, but field shape ready)
   - Why: T-class gate is **explicit MVP requirement** (see Claude-to-Codex.md); cannot be built without this field

3. **Cold-lead ampacity and resistance on MICableHeater**
   - `cold_lead_ampacity_a`: float (max current cold lead can carry)
   - `cold_lead_resistance_ohms_total`: float (total cold-lead R, or per-metre if variable)
   - Why: Cold-lead ampacity check is **explicit MVP requirement**; voltage drop calculation is **explicit MVP requirement**

4. **SelectedMIHeater result model**
   - Store: heater FK, heated_length, cold_lead FK, resistances, power, current, sheath_temp_verdict
   - Why: MI must not reuse `SelectedTracer` (different semantics); this is the result storage contract

5. **Catalogue validation flag on MICableFamily**
   - `is_validated`: BooleanField(default=False)
   - Catalogues with `is_validated=False` cannot be selected (must refuse and return diagnostics)
   - Why: MVP requires "refuse to return result if vendor data missing" discipline

### Safe-to-Build-On (No Refactor Needed)

✓ `calculate_heat_loss` output — `design_heat_loss`, `pipe_size_mm`, `tracer_adder` are directly usable by MI  
✓ `HeatTracingInput` fields — all necessary fields present (except `phase`, added above)  
✓ `ProjectData` fields — all necessary project-level fields present  
✓ Rejection diagnostics pattern from `tracer_selection.py` — reuse with distinct MI keys (`mi_selection_status`, `mi_selection_rejection_reasons`)  

### Safe-to-Skip (Not Blocking)

- Refactoring SR-specific `tracer_adder` name (neutral value, no change needed)
- Advanced heat-loss methods (placeholders remain; MI uses same heat loss as SR)

**Conclusion:** The audit confirms Pass 1 scope is correct. Add the 5 MVP blocker items above, and the data model is ready for MI selection engine (Pass 2).

---

## Next Steps (If Approved)

1. ✓ You review and approve (or request changes to) the proposal above
2. → Codex implements Pass 1 (4 tasks, ~800 LOC, no SR changes)
3. → Claude reviews for:
   - Model correctness
   - Schema completeness
   - Seed data quality (real vendor sources only)
   - Test coverage
   - SR regression check
4. → User accepts/reviews final PR
5. → Claude designs Pass 2 (MI selection engine)
6. → Cycle continues for Passes 3, 4 (integration, reporting, etc.)

---

## Summary

**This pass:** Build rock-solid MI catalogue models + test them against real vendor data.

**Why:** Foundation first, easier reviews later, zero risk to SR.

**Ready to approve?** Answer the 3 open questions above, and we can start.
