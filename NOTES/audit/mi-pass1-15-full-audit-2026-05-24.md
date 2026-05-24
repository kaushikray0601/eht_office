# MI Cable Engine — Full Audit: Passes 1–15
**Date:** 2026-05-24  
**Auditor:** Claude Code (architectural review, independent of Codex implementation)  
**Test suite state at audit:** 206 tests, all green  
**Migrations:** through 0026 (tcr_per_degree_c on MICableHeater)

---

## Pass-by-Pass Delivery Summary

| Pass | Theme | Key Deliverables | Issues Introduced | Issues Fixed |
|------|-------|-------------------|-------------------|--------------|
| 1 | Model foundation | `MICableFamily`, `MICableHeater`, `MIColdLeadOption`, `MIAlloyTempFactor` schema | — | — |
| 2 | Selection engine skeleton | `mi_selection.py` structure, basic ohm-law sizing | startup_t falsy bug (latent) | — |
| 3 | Temperature escalation | SR→MI auto-trigger in `cal.py` when temp exceeds SR limits | — | — |
| 4 | SelectedMIHeater | Snapshot persistence model, FK + snapshot fields | MI UID = `MI:{db_id}` (unstable) | — |
| 5 | Fallback display | MI lines in main results table (`result_mode='mi_only'`) | UID stale after recalc | — |
| 6 | T-class gate fix + UID fix | `'review'` verdict replaces hard reject; `MI:{pn}:{cl}` stable UID | T-class gate wrongly used `max_sheath_temp_c` | Both T-class bug + UID bug |
| 7 | BOQ + breaker | MI BOQ line items, breaker sizing for fallback lines | — | — |
| 8 | Dual-key naming | `mi_selection_status`/`mi_selection_rejection_reasons` vs SR keys | — | — |
| 9 | Snapshot audit trail | `resistance_temperature_basis` audit dict stored on `SelectedMIHeater` | — | — |
| 10 | TCR correction | Dual-path TCR: `tcr_per_degree_c` primary, `MIAlloyTempFactor` by `conductor_material` fallback; factor lookup keyed by `heater.conductor_material` not `family.alloy_type` | — | TCR key confusion |
| 11 | Cold-start fix | `_cold_start_temperature_basis()` replaces falsy `or` pattern; `startup_t=0.0` safe; full evidence dict | — | startup_t=0.0 falsy bug |
| 12 | Catalogue population | `populate_mi_catalogue.py` updated with TCR/conductor_material per vendor; `--update` flag added; 72 heaters / 177 cold leads loaded | Live DB still blank (--update not run) | Command missing TCR data |
| 13 | Smoke test | Real-catalogue end-to-end test: loads THR MIQ from populate script, validates in test DB, confirms `MIQ-11EOH-2S` selected with TCR=0.000088 | — | — |
| 14 | UI pass | SR/MI badge in results summary; export columns; BOQ wording; 204→204 tests | — | — |
| 15 | Rejection diagnostics | `MI_REJECTION_ACTION_HINTS`, `_mi_rejection_evidence_text()`, `_mi_result_review_summary()` per rejected line; warning alert on result page; export includes rejection fields | — | Empty 0.00 outputs for rejected MI rows |

---

## Architecture Assessment

### What is Working Well

**Selection path integrity.** The SR→MI escalation boundary in `cal.py` is clean. Each path produces a typed result dict with consistent keys. The dual-key naming (`mi_selection_status` vs `selection_status`) prevents cross-contamination with no ambiguity at the template layer.

**TCR correction.** The two-path TCR implementation is correct for industry practice: linear `tcr_per_degree_c` (Pass 10/12) covers the three main conductor alloys cleanly. The `MIAlloyTempFactor` lookup-table fallback is in place but currently has 0 rows — that is an acceptable steady state now that `tcr_per_degree_c` is populated on the heater rows (once `--update` is run on the live DB).

**Snapshot persistence.** `SelectedMIHeater` carries both FK references and calculated snapshot fields. Historical results remain stable even if the catalogue is corrected later. The `resistance_temperature_basis` audit dict (Pass 9) lets an engineer reconstruct exactly what correction factor was applied to a historical calc without re-running it.

**Stable override UID.** `MI:{part_number}:{cold_lead_option_code}` (Pass 6) survives recalculation cleanly. The earlier `MI:{db_id}` bug would have produced ghost overrides after every recalculation — serious UX defect, correctly fixed.

**T-class gate.** The Pass 6 fix is architecturally correct: `max_sheath_temp_c` is a survival rating (400–600°C), not an operating surface temperature. The gate now always returns `'review'` with an evidence string, which is the right engineering answer — T-class compliance requires a site-specific surface temperature calculation that a selection engine cannot do without more inputs.

**Test coverage.** 206 tests. The Pass 11 regression tests for `startup_t=0.0` and the Pass 13 real-catalogue smoke test are particularly valuable. The smoke test exercises the full path from database load through TCR correction to part selection — it will catch future schema/command drift immediately.

**`is_validated=False` discipline.** The engine hard-stops at three levels when no validated catalogue exists. This prevents phantom selections on unreviewed data and forces the catalogue validation step before production use.

---

## Issues by Severity

### SEVERITY 1 — Blocks production use

#### Issue A: Django admin has no MI model registrations

**File:** [eht/admin.py](eht/admin.py)  
**Detail:** `MICableFamily`, `MICableHeater`, `MIColdLeadOption`, `MIAlloyTempFactor`, and `SelectedMIHeater` are not registered. KR cannot inspect, correct, or validate catalogue records through the Django admin interface.

**Impact:** The `is_validated` flag on `MICableFamily` — the gate that prevents the engine from using unreviewed data — cannot be set to `True` through the admin UI. All 3 loaded families remain `is_validated=False`. The selection engine will hard-stop on every MI escalation attempt.

**Fix scope:** 30–50 lines in `admin.py`. Recommend `MICableFamilyAdmin` with inline `MICableHeaterInline` and `MIColdLeadOptionInline`, and a custom action `mark_validated`. `MIAlloyTempFactor` and `SelectedMIHeater` need basic list-display-only registrations.

**Priority for Pass 16:** This is the single most important remaining item.

---

#### Issue B: Live database — 72 heaters have blank conductor_material and tcr_per_degree_c=0.0

**File:** [eht/management/commands/populate_mi_catalogue.py](eht/management/commands/populate_mi_catalogue.py)  
**Detail:** The `--update` flag was added in Pass 12 to patch existing rows that were created before the TCR schema existed. It has not been run against the live PostgreSQL database. All 72 heaters in production have:
- `conductor_material = ''`
- `tcr_per_degree_c = 0.0`

**Impact:** Even if a family is marked `is_validated=True`, every TCR correction calculation will fall back to the `MIAlloyTempFactor` lookup (which has 0 rows), and then silently use multiplier=1.0 — a systematic under-sizing error for all high-temperature MI applications. For a 300°C maintain temperature with Nichrome conductor (TCR ≈ 0.00018), the uncorrected power at temperature would be under-estimated by ~5%. For NiCr alloys at 300°C this is acceptable margin. But for Alloy 825 (TCR ≈ 0.0039), the error at 300°C reaches ~110% — a factor-of-two sizing error.

**Fix scope:** One shell command. Run against the live database before setting `is_validated=True` on any family:
```
python manage.py populate_mi_catalogue --update
```

**Priority:** Run immediately before catalogue validation.

---

### SEVERITY 2 — Engineering completeness gap

#### Issue C: MIColdLeadOption is missing ampacity_a and resistance_ohms_m fields

**File:** [eht/models.py](eht/models.py) — `MIColdLeadOption`  
**Detail:** nVent cold lead options are rated by current-carrying capacity: S25A (25 A), S34A (34 A), S49A (49 A), S65A (65 A). Thermon cold lead options also have distinct ampacity ratings by cross-section. The current schema stores only `cold_lead_option_code` (string) and `length_m` (float). There is no `ampacity_a` field.

**Impact:** The selection engine cannot verify that the selected cold lead option can carry the calculated cold-start current. A heater requiring 47 A cold-start current could be matched with a 34 A cold lead — this would pass all engine gates and appear in the output without warning.

**Engineering severity:** This is a real safety gap. Cold lead undersizing causes junction failure and potential ignition in a hazardous area.

**Fix scope:** Add `ampacity_a = models.FloatField(null=True)` and optionally `resistance_ohms_per_m = models.FloatField(null=True)` to `MIColdLeadOption`. Add a gate in `mi_selection.py` that rejects a cold lead option if `cold_start_current_a > cold_lead.ampacity_a` (when field is non-null). Update `populate_mi_catalogue.py` to populate from vendor data.

**Priority for Pass 17 or 18.**

---

#### Issue D: MICableHeater is missing max_heated_length_m

**File:** [eht/models.py](eht/models.py) — `MICableHeater`  
**Detail:** MI cables have a maximum circuit length determined by their construction (sheath diameter, conductor cross-section, voltage rating). Thermon MIQ at 240V is limited to specific max lengths by part number. The engine does not check whether the calculated heated length exceeds this limit.

**Impact:** An MI heater could be selected for a 500 m circuit when it is only rated for 200 m. The output would show a valid-looking selection that the vendor would reject as a circuit too long to manufacture.

**Fix scope:** Add `max_heated_length_m = models.FloatField(null=True)` to `MICableHeater`. Add a gate in `mi_selection.py` that rejects if `heated_length_m > heater.max_heated_length_m` (when non-null). Update populate command.

**Priority for Pass 17 or 18.**

---

### SEVERITY 3 — Technical debt / housekeeping

#### Issue E: Migrations 0024 and 0025 are a create-destroy pair

**Files:** [eht/migrations/0024_add_heating_cable_type.py](eht/migrations/0024_add_heating_cable_type.py), [eht/migrations/0025_remove_heating_cable_type.py](eht/migrations/0025_remove_heating_cable_type.py)  
**Detail:** Migration 0024 adds `heating_cable_type` to a model; 0025 removes it. Net effect is zero schema change. The pair is harmless but adds noise to `migrate` output and wastes a migration slot.

**Fix:** Squash both into a no-op or delete the pair and update the migration chain. Low priority — do only if the migration history is being cleaned up for another reason.

---

#### Issue F: MIAlloyTempFactor table has 0 rows

**File:** [eht/models.py](eht/models.py) — `MIAlloyTempFactor`  
**Detail:** The model exists and the TCR fallback path references it, but the table is empty. Now that `tcr_per_degree_c` is populated on each heater row (once `--update` is run), the fallback will never be reached in normal operation.

**Options:**
1. Leave as-is — the fallback is harmless dead code when `tcr_per_degree_c` is non-zero.
2. Add a `CHECK` constraint or model validator requiring at least one of `tcr_per_degree_c != 0` or a matching `MIAlloyTempFactor` row to exist at validation time.
3. Remove the table entirely and simplify the selection engine to linear-TCR-only.

**Recommendation:** Option 1 for now. If the `MIAlloyTempFactor` table remains empty for 3+ months with no vendor requiring it, remove it.

---

#### Issue G: No admin action to bulk-run populate_mi_catalogue

**Detail:** Currently the `--update` command must be run from the server shell. There is no Django admin action or management UI to trigger a re-population. This means KR or a developer must have shell access to update catalogue data — not appropriate for a production deployment.

**Fix scope:** Low-priority. Consider a custom admin action on `MICableFamilyAdmin` that calls the populate logic for a selected family. Requires refactoring `populate_mi_catalogue.py` to expose callable functions (not just `handle()`).

---

### SEVERITY 4 — Pre-production validation

#### Issue H: R7 — No vendor worked-example benchmark

**Detail:** The engine's ohm-law sizing, TCR correction, and breaker calculation have not been compared against a vendor's published worked example. This was deliberately deferred by KR as a post-stabilisation spot-check, not a merge blocker.

**Status:** Still open. Not a blocker. Recommend one test case from each of the three vendors (Thermon, nVent, Chromalox) before setting `is_validated=True` on production catalogue families.

---

## Pass 16 Recommended Scope

The engine is architecturally sound and the selection path works end-to-end. The only thing blocking production use is the catalogue validation gate. Pass 16 should unlock that gate.

**Minimum viable Pass 16:**

1. **Register MI models in `eht/admin.py`** with `MICableFamilyAdmin` (includes `MICableHeaterInline`, `MIColdLeadOptionInline`), custom action `mark_family_validated`, read-only `SelectedMIHeaterAdmin`, and basic `MIAlloyTempFactorAdmin`. This is the only code change needed.

2. **Document the post-admin runbook** for KR to follow:
   - Run `python manage.py populate_mi_catalogue --update` on live DB
   - Open admin → MI Cable Families → review all 3 families
   - Mark `is_validated=True` on each family after spot-check
   - Run one manual calculation to confirm MI selection fires

**Pass 17–18 (engineering completeness):**
- Add `ampacity_a` to `MIColdLeadOption` + gate in engine (Issue C)
- Add `max_heated_length_m` to `MICableHeater` + gate in engine (Issue D)
- R7 vendor spot-check with real worked examples

---

## What to Hand to Codex

Suggested instruction for Codex Pass 16:

> **Task: Register MI catalogue models in Django admin (admin.py)**
>
> Open `eht/admin.py`. Add registrations for all five MI models:
> - `MICableFamilyAdmin`: list_display with family_code, vendor, alloy_type, voltage_rating_v, is_validated. Inline: `MICableHeaterInline` (tabular, fields: part_number, watts_per_metre, conductor_material, tcr_per_degree_c, max_sheath_temp_c), `MIColdLeadOptionInline` (tabular, fields: cold_lead_option_code, description). Custom admin action: `mark_family_validated` that sets `is_validated=True` on selected families and logs a message.
> - `MICableHeaterAdmin`: list_display with part_number, family, conductor_material, tcr_per_degree_c. list_filter by family__vendor, family__family_code.
> - `MIColdLeadOptionAdmin`: list_display with cold_lead_option_code, heater, description. (Add ampacity_a to list_display if field exists.)
> - `MIAlloyTempFactorAdmin`: basic list_display.
> - `SelectedMIHeaterAdmin`: read-only list_display with project, line, heater, selected_at. No add/change permissions.
>
> No model changes, no migrations, no engine changes in this pass. Admin only. Write tests if the test suite has admin tests; otherwise update the admin smoke test if one exists.

---

## Summary Table: Open Items After Pass 15

| # | Issue | Severity | Blocking? | Recommended Pass |
|---|-------|----------|-----------|------------------|
| A | No Django admin for MI models | 1 | Yes — catalogue cannot be validated | 16 |
| B | Live DB: blank conductor_material + tcr=0.0 | 1 | Yes — TCR will be wrong after validation | Before any validation |
| C | No ampacity_a on MIColdLeadOption | 2 | No — but cold lead undersizing risk | 17 |
| D | No max_heated_length_m on MICableHeater | 2 | No — but over-length circuit risk | 17 |
| E | Migrations 0024+0025 create-destroy pair | 3 | No | Future cleanup |
| F | MIAlloyTempFactor table empty | 3 | No | Defer or remove |
| G | No admin-triggered catalogue repopulation | 3 | No | Future |
| H | R7 vendor spot-check | 4 | No | Post-stabilisation |

---

*Audit prepared by Claude Code. All code references verified against current file state at audit date.*
