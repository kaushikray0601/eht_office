# MI Engine — Full Audit Report, Passes 1–10
_Author: Claude Code | Date: 2026-05-24_

---

## Test Suite Snapshot

| Suite | Tests | Status |
|-------|-------|--------|
| Full EHT suite | 197 | All green |
| MI selection unit | 12 | All green |
| MI persistence | 5 | All green |
| MI orchestration | 5 | All green |
| MI catalogue structure | 10 | All green |
| SR suite | unmodified | All green |

---

## What Was Built Across All 10 Passes

| Pass | Delivered |
|------|-----------|
| 1–2 | MI catalogue schema, migration 0022, `mi_selection.py` skeleton, unit tests |
| 3 | Persistence layer: `_transform_mi_heater_item`, `store_calculated_results` MI path, `clear_project_workspace_data` MI path, `test_mi_persistence.py` |
| 4 | `cal.py` temperature-triggered auto-escalation, `test_mi_orchestration.py` |
| 5 | SLD MI override (`MI:{uid}` prefix), result tab UI, export sheet, `tracer_management.py` MI path, 3 integration tests |
| 6 | T-class gate fixed (no longer auto-rejects on `max_sheath_temp_c`), MI fallback lines visible in main results table (`result_mode='mi_only'`), stale override UID fixed to `MI:{part_number}:{option_code}`, `active_option` dead code removed |
| 7 | `compute_mi_power_params` in `power_distribution.py`, MI BOQ/breaker sizing for fallback lines |
| 8–9 | (per Codex notes) UI polish, export, integration tests |
| 10 | `tcr_per_degree_c` on `MICableHeater`, migration 0026, TCR correction in `_single_phase_power`, `MIAlloyTempFactor` lookup keyed by `heater.conductor_material` (not `family.alloy_type`), regression tests |

---

## What Works Well

### Architecture

**Temperature-trigger escalation is correct.** `_sr_temperature_limit_exceeded` in `cal.py` filters to SR rows only, checks all three temperature columns (maint/oper/design), and triggers MI only when a catalogue limit is actually exceeded. It cannot be confused by power failures or zone mismatches.

**Dual-path resistance calculation is correct.** `_resistance_multiplier_for_temperature` implements the right priority: `tcr_per_degree_c` on the heater takes precedence (linear formula), falling back to `MIAlloyTempFactor` lookup keyed by `heater.conductor_material`. Critically, `family.alloy_type` (sheath material) is no longer used as the lookup key — this was the core engineering concern Codex raised and resolved correctly in Pass 10.

**Startup vs maintain resistance are properly separated.** `_evaluate_single_phase_candidate` now computes:
- `heater_resistance_ohms` at maintain temperature (for power and nominal current)
- `heater_startup_resistance_ohms` at startup temperature (for cold-start current checks)

For positive-TCR conductors (Alloy 825: TCR=3.93×10⁻³/K), resistance at cold start is lower, meaning cold-start current is higher. The engine correctly uses `heater_startup_resistance_ohms` for `current_cold_start_a` and breaker/ampacity checks.

**T-class gate is correct.** `max_sheath_temp_c` is no longer used to reject candidates. The gate now returns `t_class_verdict='review'` with reason `DESIGN_SPECIFIC_SURFACE_TEMPERATURE_REVIEW_REQUIRED` and adds the context to `selection_basis`. The engineer sees it and confirms during detailed design. No auto-rejection.

**Override UID is stable.** `_mi_option_uid` uses `MI:{heater.part_number}:{cold_lead_option_code}` — survives recalculation because it does not depend on the DB primary key.

**Snapshot persistence is complete.** `SelectedMIHeater` stores both FK references (heater, cold_lead_option) and calculated snapshot fields. `selection_basis` JSON includes full `resistance_temperature_basis` evidence: method used, multiplier applied, reference temperature, conductor material, factor row count, maintain/startup temperature. Historical results remain traceable even if catalogue rows are later corrected.

**Test coverage is correctly layered.** Unit tests verify engine logic without DB overhead. Persistence tests exercise model round-trips. Orchestration tests exercise the `cal.py` trigger boundary. Integration tests exercise view rendering and export shape. The three new Pass 10 tests (conductor factor used, sheath factor ignored, TCR priority over lookup) each test a distinct failure mode.

---

## Issues Found — Ranked by Severity

### ISSUE 1 — MEDIUM: `startup_t=0.0` silently falls back to maintain temperature

**File:** `mi_selection.py:133` — **FIXED**

Was using `or maintain_temp_c` which treats `0.0` as falsy.

**Fix applied:** New helper `_cold_start_temp_c(project_settings, maintain_temp_c)` takes
`min(startup_t, min_amb_t)` — whichever is colder gives the lowest conductor resistance and
highest cold-start current (conservative worst-case design). If neither key is present
(pure unit tests), falls back to `maintain_temp_c`.

Engineering basis (confirmed by KR): A traced line may carry fluid colder than ambient, or
ambient may be colder than process startup temperature. Taking the minimum of both temperatures
ensures the breaker is sized for the actual worst-case cold-start condition regardless of
which source dominates on any given project.

---

### ISSUE 2 — MEDIUM: Catalogue data loaded but TCR and conductor_material are still blank

`populate_mi_catalogue.py` was not updated after Pass 10 added `tcr_per_degree_c` and established the `conductor_material` field as the lookup key. All 72 loaded heaters still have `tcr_per_degree_c=0.0` and `conductor_material=''`.

**Consequence:** When any family is set `is_validated=True`, the engine will run with no TCR correction (`tcr_per_degree_c=0.0` is falsy; blank `conductor_material` means no factor table lookup). Power will be computed at 20°C nominal resistance. For Alloy 825 conductors at 342°C maintain, this overestimates power by ~16%.

**Fix:** Update `populate_mi_catalogue.py` heater tuples to include `(part_number, conductors, resistance_ohms_m, max_current_a, tcr_per_degree_c, conductor_material)` and populate with the vendor TCR values from the datasheets (nVent and Chromalox published these; Thermon estimated at 0.088×10⁻³/K):

| Heater group | conductor_material | tcr_per_degree_c |
|---|---|---|
| MIQ-* (Thermon) | `'Nickel-Chromium'` | `0.000088` |
| HAF/HAA codes (nVent) | `'Nickel-Chromium'` | `0.000088` |
| HAQ codes (nVent) | `'Nickel Alloy Q'` | `0.00050` |
| HAP codes (nVent) | `'Nickel Alloy P'` | `0.00130` |
| HAC codes (nVent) | `'Alloy 825 Conductor'` | `0.00390` |
| 1110B–510B (Chromalox) | `'Nickel-Chromium'` | `0.000100` |
| 410B–310B (Chromalox) | `'Nichrome T'` | `0.000180` |
| 210B–200B (Chromalox) | `'Nickel Alloy Q'` | `0.000500` |
| 115B–103B, 508B–506B (Chromalox) | `'Alloy 825 Conductor'` | `0.003930` |

Also re-run `python manage.py populate_mi_catalogue` after updating (command is idempotent — `get_or_create` won't overwrite existing rows unless you add `update_fields` or delete first).

Note: Because `get_or_create` only sets `conductor_material` and `tcr_per_degree_c` on creation (not on update), you need to either run `python manage.py shell` to update existing rows, or add an `update_fields` path to the command.

---

### ISSUE 3 — LOW: `startup_t` conceptually mismatched for MI cold-start

**Context:** For SR cables, `startup_t` is the minimum fluid temperature at process startup — the coldest condition the process fluid reaches. For MI cables, cold-start current depends on the conductor temperature at the moment of energisation, which is the ambient temperature (`min_amb_t`), not the process startup temperature.

If a project has `startup_t=20°C` (minimum process temperature) but `min_amb_t=-20°C` (minimum ambient), the MI cold-start current will be underestimated because the conductor is actually at -20°C at startup, not 20°C.

**Severity:** Low — only matters for high-TCR conductors (Alloy 825 group) and only affects cold-start current sizing, not nominal power. The fix requires a decision from KR on whether `startup_t` or `min_amb_t` is the right reference for MI cold start, which is an engineering design choice.

For now: if `min_amb_t` < `startup_t`, use `min_amb_t` as the startup temperature for MI cold-start resistance. If KR agrees, this is a one-line change in `_resistance_temperature_basis`.

---

### ISSUE 4 — LOW: `SelectedMIHeater` does not store temperature-corrected flag

The model stores `heater_resistance_ohms` which is the temperature-corrected resistance at maintain temperature (not the 20°C catalogue value). A future engineer reading the persisted row might not realise the stored resistance differs from `MICableHeater.resistance_ohms_m × heated_length_m`. The full basis is available in `selection_basis['resistance_temperature_basis']` JSON, but the top-level field is ambiguous.

**Fix (no migration needed):** Minor rename clarity: consider `heater_resistance_ohms` → `heater_resistance_at_maint_ohms` in the model, or just add a note in the model docstring. Very low priority — the JSON basis provides full evidence.

---

### ISSUE 5 — LOW: Migrations 0024+0025 are a create-and-destroy pair

`0024` adds `ProjectData.heating_cable_type`, `0025` immediately removes it. On fresh installs both migrations run cleanly. No data loss. Safe to squash into a no-op when making the next migration batch. Not urgent.

---

## Open Scope Items (Pre-Production)

These are known deferred items, not newly found in this audit. Listed for completeness.

| Item | Priority | What's needed |
|------|----------|---------------|
| **R7: Worked-example test gate** | **MVP merge blocker** | One test against a published Thermon or nVent design example. Engine structure is correct; power formula is sound. Requires KR to verify one real heater code selection against a known result. Cannot be closed by code alone. |
| **Validate catalogue and set `is_validated=True`** | Pre-production | KR must verify each loaded family row against the source PDF before flipping the flag. Engine will not select from unvalidated data. |
| **Populate `tcr_per_degree_c` and `conductor_material`** | Pre-production | See Issue 2 above. Until populated, TCR correction is silent no-op on real catalogue runs. |
| **Per-code max circuit length** | Post-MVP | nVent publishes per-resistance-code maximum circuit lengths (100–312m). Currently only a single family-level `max_circuit_length_m` is checked. Add `max_heated_length_m` to `MICableHeater`. |
| **Per-option cold lead ampacity/resistance** | Post-MVP | `heater.cold_lead_max_ampacity_a` is a single field. nVent S25A/34A/49A/65A have different ratings. Should move to `MIColdLeadOption.ampacity_a` and `.resistance_ohms_m`. |
| **`MIAlloyTempFactor` table** | Post-MVP | 0 rows. Discuss with Codex: use lookup table OR `tcr_per_degree_c` field? If lookup table, need full R-vs-T curves from alloy manufacturer datasheets. If field, TCR is already in place. |
| **MI star-point / multi-heater topology** | Post-MVP | One MI heater = one circuit for now. Parallel arrangements deferred. |
| **3-phase MI** | Post-MVP | Only single-phase implemented. |

---

## Things to Discuss Before Next Pass

### On Issue 2 (catalogue data gap)

The management command I wrote earlier (`populate_mi_catalogue.py`) needs a `--update` path or a separate `update_mi_catalogue_tcr` command that updates existing heater rows with TCR and conductor_material values. `get_or_create` does not update existing rows. Options:

**Option A:** Add an `update_or_create` path to the command controlled by `--update` flag.
**Option B:** Write a one-shot migration or shell command to set TCR and conductor_material on the 72 existing rows.

Either is acceptable. Option A is cleaner for repeatable runs.

### On Issue 3 (startup_t vs min_amb_t for MI)

Engineering question for KR: when sizing the MI heater's cold-start current (and hence breaker), should the engine use:
- `startup_t` (minimum process fluid temperature at process startup), or
- `min_amb_t` (minimum ambient air temperature — the temperature the cable is actually at before energisation)?

For SR cables, `startup_t` is correct (SR cable tracks fluid temperature via self-regulation). For MI cables, the cable temperature at cold-start is ambient — so `min_amb_t` is arguably more correct.

### On R7 (worked-example test gate)

The engine's power formula is verified analytically: `P = I² × R_heater`, `I = V / (R_heater + R_cold_lead)`, with TCR correction. The math is consistent.

What R7 requires is a cross-check against a real vendor design tool output. The simplest path: take one heater code from the loaded nVent data (e.g., `HAF2N4.5K`, 4.5 Ω/m, 20m heated, 240V, S25A cold lead), compute the expected power/current manually or with nVent's calculator, and write the test. KR needs to supply the reference answer.

---

## Overall Verdict

**The MI engine is structurally complete and architecturally sound.** Ten passes have delivered a well-layered system: catalogue discipline, dual-path resistance correction, temperature-triggered escalation, stable override UID, snapshot persistence, MI BOQ, and a result UI that correctly shows both SR and MI lines. The SR test suite is completely untouched.

**Two actions required before setting `is_validated=True` on any catalogue family:**
1. Fix the `startup_t=0.0` falsy bug (3-line change, no migration) — Issue 1
2. Update `populate_mi_catalogue.py` with TCR values and re-populate — Issue 2

**One action required before MVP merge:**
- Close R7 (worked-example test against published vendor numbers)

Everything else is post-MVP scope.
