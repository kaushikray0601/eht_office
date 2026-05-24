# MI Engine — Consolidated Architect Review
_Author: Claude Code | Date: 2026-05-24 | Covers: Pass 1 through Pass 5_

---

## What Was Built Today — Pass Summary

| Pass | Delivered |
|------|-----------|
| 1–2  | MI catalogue schema (`MICableFamily`, `MICableHeater`, `MIColdLeadOption`, `SelectedMIHeater`), migration 0022, selection engine `mi_selection.py`, unit tests |
| 3    | Persistence layer: `_transform_mi_heater_item`, `store_calculated_results` MI path, `clear_project_workspace_data` MI path, `test_mi_persistence.py` |
| 4    | `cal.py` wired (Pass 4 originally added project-level switch, then design change replaced it with temperature-triggered auto-escalation); `test_mi_orchestration.py` |
| 5    | SLD MI override, result tab UI, export sheet, `tracer_management.py` MI path, `views.py` MI surfaces, JS rendering, 3 integration tests |

**Final test count: 190 (all green). SR suite untouched.**

---

## What Works Well

### Architecture

**Temperature trigger is correct and clean.** `_sr_temperature_limit_exceeded` in `cal.py` reads all three temperatures (maint/oper/design) against the SR catalogue's published limits for those columns (`Maint_T`, `Max_Op_T`, `Max_Exp_T_On`). It filters to SR rows only before comparing. The trigger fires only when the line temperature exceeds the catalogue max — not on SR power failure, not on zone/area mismatches. This is exactly the specified behaviour.

**Dual-path result storage is clean.** `SelectedMIHeater` serves both "auto fallback selected" lines and "SR selected, MI available as alternative" lines via `selection_status`. The `mi_selection_status` / `mi_selection_rejection_reasons` key names on the heat_loss dict are intentionally distinct from SR's `selection_status` / `selection_rejection_reasons`, preventing key collision.

**Catalogue discipline holds.** `is_validated=False` is an unconditional hard stop at three levels: (1) `_is_family_suitable` returns `UNVALIDATED_CATALOGUE` and the family is skipped, (2) `_has_validated_mi_catalogue` in `cal.py` prevents the `available_alternative` MI probe from running at all when no validated catalogue exists, (3) `get_mi_heater_options` early-exits with `NO_VALIDATED_MI_CATALOGUE_DATA` if all families are unvalidated.

**Snapshot persistence is correct.** `SelectedMIHeater` stores both FK references (`heater`, `cold_lead_option`) and calculated snapshot fields. If a catalogue row is later corrected, historical results remain traceable. This is the same pattern as SR's `SelectedTracer`.

**MI override using `MI:` UID prefix is clean.** The `MI:{db_id}` namespace is distinct from SR UIDs (which are catalogue part codes). The `save_tracer_override` MI path validates `selection_status='available_alternative'` — the engineer cannot override to an auto-fallback MI result, only to an "available as alternative" one.

**Tests are layered correctly.** Unit tests (`test_mi_selection.py`) exercise engine logic without DB overhead. Persistence tests (`test_mi_persistence.py`) exercise model → DB round-trips. Orchestration tests (`test_mi_orchestration.py`) exercise `cal.py` trigger logic. Integration tests (`tests.py` additions) exercise result_view rendering and export shape. Each layer tests what it can, no layer over-reaches.

---

## Issues Found — Ranked by Severity

### ISSUE 1 — HIGH: MI override becomes silently stale after recalculation

**What happens:** When the engineer overrides a line to MI on the SLD, the override stores `selected_v_uid = "MI:{SelectedMIHeater.id}"`. When the project is recalculated, `store_calculated_results` deletes all `SelectedMIHeater` rows and recreates them with new DB primary keys. The override record is NOT touched. On the next SLD load, `apply_tracer_selection_to_payload` cannot match `MI:{old_id}` against the new `MI:{new_id}`, so `active_payload` is None and the line silently falls back to the generated SR selection.

**Why this matters:** The engineer has made a deliberate engineering decision (use MI here). Recalculation silently reverses it without any warning. On a real project, changing insulation thickness → recalculate → engineer's MI decisions are lost. This is a workflow correctness issue, not just cosmetic.

**SR does not have this bug.** SR's `AlternateTracer.v_uid` is the catalogue part code (e.g., `CHR-XMI-2100`) — a stable string that survives recalculation. The `SelectedMIHeater` approach uses the DB primary key as the UID, which changes every run.

**Fix:** Change MI UID to `MI:{heater_part_number}:{cold_lead_option_code}` in `_mi_option_uid`. This is stable across recalculations as long as the heater part number and cold lead code don't change. In `save_tracer_override`, validate against `SelectedMIHeater.heater.part_number + cold_lead_option_code` instead of `id`. In `apply_tracer_selection_to_payload`, build the payload UID the same way. One function change in `tracer_management.py`.

---

### ISSUE 2 — MEDIUM: MI lines with auto-fallback are invisible in the main results table

**What happens:** When `design_temp > SR_limit`, the line takes the `automatic_temperature_fallback` path. No SR tracer is selected, no `compute_power_params` is called, so the line does NOT appear in `line_results` (the main results table). It DOES appear in `mi_result_rows` (the separate MI Selection Records table). An engineer looking at the main results table will see missing lines with no explanation.

**What's missing:** A row in the main results table that says "This line has no SR result — it is covered by MI automatic fallback. See MI Selection Records." Currently the engineer must cross-reference between two tables.

**This is P4-R2 from the running log, still open.** The new MI Selection Records section helps, but the main table gap is confusing.

---

### ISSUE 3 — MEDIUM: `populate_mi_cables.py` management command removed but no note in admin

**What happened:** The `populate_mi_cables.py` command (which had fabricated data) was deleted earlier. This is correct. But there is no admin-level or UI-level guidance on how to populate MI catalogue data. An admin who navigates to the MI section in Django admin will see empty tables with no instructions. The existing Django admin for `MICableFamily` / `MICableHeater` / `MIColdLeadOption` presumably exists (from migration 0017 and 0022), but there is no `admin.py` registration shown as changed in Pass 5.

**Risk:** Whoever enters production data could inadvertently set `is_validated=True` before verifying against a source document, bypassing the catalogue discipline gate.

---

### ISSUE 4 — LOW: Migration 0024+0025 roundtrip is wasteful but harmless

Migrations 0024 (add `heating_cable_type`) and 0025 (remove `heating_cable_type`) are a create-and-immediately-destroy pair. On fresh databases both run cleanly. On an existing database with `heating_cable_type` values already set, 0025 drops the column — fine. There is no data migration needed since the feature never reached production.

The migrations can be squashed to a no-op if desired. Not urgent; harmless as-is.

---

### ISSUE 5 — LOW: `active_option` vs `active_payload` dual-lookup in `apply_tracer_selection_to_payload`

After the MI change in Pass 5, `tracer_management.py` does two nearly identical lookups:
- `active_payload`: scans `alternative_payloads` (includes MI) by `v_uid` — used for everything except `active_option`
- `active_option`: scans `alternatives` ORM objects (SR only) by `v_uid` — no longer used for any output

`active_option` is now dead weight. The final `selected_payload` uses `active_payload`, the `override_id` and `override_remarks` use `active_payload`. The only place `active_option` was used — as the guard for `selected_payload` — was replaced. This code reads as if `active_option` still matters when it no longer does. A future reader could think they need to keep both.

**Fix:** Remove `active_option` lookup. `active_payload` is sufficient.

---

## What Is Still Missing (Open Scope Items)

| Item | Priority | Note |
|------|----------|------|
| Worked-example test gate (R7) | **MVP merge blocker** | ≥2 tests against published Thermon MIQ / nVent numbers. Needs real catalogue data from KR. No code fix can close this — it requires real engineering data. |
| Real catalogue data (`is_validated=True`) | **Prerequisite** | Engine is complete but will return `NO_VALIDATED_MI_CATALOGUE_DATA` on every run until KR provides real Thermon or nVent data and marks it validated. |
| MI BOQ + power distribution | Post-MVP | MI auto-fallback lines skip `compute_power_params` / `compute_power_distribution`. No panel loading, no breaker sizing, no cold-cable schedule for MI lines. |
| `AlternateMIHeater` model (P3-R4) | Post-MVP | `get_mi_heater_options` returns `alternatives_list` which is currently discarded. For the SLD to show multiple ranked MI options, this list needs storage. Currently only the single best MI candidate is persisted. |
| MI admin registration and data-entry guidance | Pre-production | Whoever enters catalogue data needs clear guidance on `is_validated` workflow and `source_document` requirement. |
| Stale MI override warning in UI (follow-on from Issue 1) | Needed with Issue 1 fix | When `MI:{uid}` cannot be matched after recalculation, the UI should show "MI override stale — please re-select." rather than silently falling back. |

---

## Things to Discuss

### On Issue 1 (stale MI override)

The SR UID stability pattern (`v_uid = catalogue_part_code`) was a deliberate design choice. The MI `MI:{db_id}` approach breaks this pattern. The question is how hard to fix before real projects start:

**Option A (preferred):** Change `_mi_option_uid` to `MI:{heater.part_number}:{cold_lead_option_code}`. This is stable. Validate by matching this string in the `available_alternative` result set. Small change, no model migration needed.

**Option B (defer):** Accept stale override risk for MVP. Before any real project run, warn the engineer in the user manual that MI overrides must be re-applied after recalculation.

I recommend Option A — it is a 15-line change in `tracer_management.py` and eliminates a silent data integrity issue before real project data enters.

### On Issue 2 (MI fallback lines invisible in main table)

This was P4-R2 in my running log and was flagged before Pass 5. Pass 5 added the MI Selection Records section, which is good. But the main results table still has the gap. The question is whether this is acceptable for initial use:

- If your first real project has ANY auto-fallback lines (temperature exceeded), the engineer will see "fewer lines than expected" in the main table.
- If the first projects are SR-only (no temperature exceedance), this will never be seen.

If you expect to enter high-temperature line projects soon, this needs a UI note before that project run. It doesn't require code changes — a conditional row in the Jinja template saying "MI automatic fallback — see MI Selection Records" in greyed text is enough.

### On the worked-example test gate

This is the one gate that cannot be met by code alone. The engine is correct in structure and logic. But until a known-good worked example (real heater, real line, real result) passes through the engine and produces the published answer, we cannot say the math is verified. Every MVP pass was careful about this. The code ships when you provide two real numbers from a Thermon MIQ or nVent design guide and the engine reproduces them. No amount of structural testing closes this gate.

---

## Overall Verdict

The five passes have delivered a complete, structurally sound MI engine. The architecture choices (catalogue discipline, dual key names, snapshot persistence, temperature-trigger auto-escalation, stable SR test suite) are all good. The code is readable, well-tested for its scope, and safe to run — it cannot produce a fabricated "selected" result without real validated catalogue data.

**Before any real project data is entered:**
1. Fix the stale MI override UID (Issue 1) — 15-line change, no migration
2. Add a conditional note in the main results table for MI fallback lines (Issue 2) — template-only change
3. Provide real catalogue data and close the worked-example test gate (R7)

**Pass 5 specifically** is a solid UI/integration layer. The export sheet, the result tab MI section, and the SLD override mechanism all work correctly. The 3 new tests are meaningful. The only structural problem introduced in Pass 5 is the ephemeral `MI:{db_id}` UID for overrides.
