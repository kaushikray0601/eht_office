# MI Engine — Running Review Log
_Author: Claude Code (architect/auditor) | Started: 2026-05-24_
_Do not act on these items until explicitly scheduled. Record only._

---

## Pass 1 + 2 State (as at end of 2026-05-24 coding session)

Schema (`models.py`), migration (`0022`), selection engine (`mi_selection.py`),
and two test modules are in place. SR path is unchanged. The overall architecture
is sound. Items below are deferred refinements, not blockers.

---

## R1 — Cold lead AWG assumption baked into schema (flag for when real data loads)

`MICableHeater.cold_lead_resistance_ohms_m` is a single value shared by ALL
`MIColdLeadOption` length options under that heater. This is correct only if the
vendor attaches the same AWG regardless of cold lead length. For MVP this is the
right simplification. When KR loads real Thermon MIQ or nVent catalogue data,
verify this holds. If longer cold lead runs use a heavier (lower Ω/m) conductor,
`cold_lead_resistance_ohms_m` must move to `MIColdLeadOption` and off the heater.

**Where to fix if needed:** Add `resistance_ohms_m` and `max_ampacity_a` to
`MIColdLeadOption`, deprecate from `MICableHeater`. One migration.

---

## R2 — `rejected_candidates` list has inconsistent shape in rejection details

In `get_mi_heater_options`, `rejected_candidates` accumulates two different dict
shapes:

- When `candidate is None`: `{'family_id', 'heater_id', 'cold_lead_option_id', 'reasons'}`
- When candidate is evaluated but fails checks: the full candidate dict (which has
  `rejection_reasons` embedded, not `reasons`)

Both shapes appear in `NO_MI_CANDIDATE_MATCH → details → candidate_rejections[:20]`.
Diagnostic output will be inconsistent. Not a functional bug — the engine correctly
rejects — but diagnostic rendering in the UI will need to handle both shapes.

**Where to fix:** Normalise `rejected_candidates` entries to a single shape when
building the rejection detail dict. A small cleanup in `get_mi_heater_options`.

---

## R3 — `allowablevdrop` semantic reuse needs confirmation

`ProjectData.allowablevdrop` is the project-level allowable voltage drop field,
likely intended for the distribution cold cable schedule. `mi_selection.py` reuses
it as the cold-lead voltage drop limit check on the MI heater cold lead. These
are different circuits. The cold cable (DB to junction box) is the original use;
the MI cold lead (junction box to heater start) is a different check.

For MVP the reuse is pragmatic and probably correct in direction, but when the
UI is updated for MI project settings, clarify whether a separate
`mi_cold_lead_max_vdrop_pct` project field is needed or whether `allowablevdrop`
is genuinely shared.

---

## R4 — MI selection engine queries DB directly; SR does not

`get_mi_heater_options` calls `MICableFamily.objects.filter(...)` inside the
engine. The SR equivalent `get_tracer_options` receives its catalogue data as a
pre-loaded DataFrame parameter — the caller fetches, the engine filters.

This divergence means:
- MI tests require a live test DB (Django TestCase) rather than pure unit tests
- The `families=None` bypass parameter works for tests but is an extra surface
- Profiling/caching is harder when DB calls are buried in the engine

**When to fix:** Pass 3 or when performance matters. Option: pull the DB query
into `cal.py` / `pipeline.py` and pass `families` always, matching SR's pattern.

---

## R5 — `_evaluate_single_phase_candidate` defined before `_heated_length_m` and `_single_phase_power`

Function order in the file: `_evaluate_single_phase_candidate` (line 116) calls
`_heated_length_m` (line 214) and `_single_phase_power` (line 199). Python
resolves these at call time so there is no runtime error. But reading the file
top-to-bottom is confusing — helpers are defined after their callers. Reorder:
`_heated_length_m` → `_single_phase_power` → `_evaluate_single_phase_candidate`
→ `_is_family_suitable` → `get_mi_heater_options`.

**Where to fix:** Pure readability refactor, zero functional change.

---

## R6 — `t_class_verdict='review'` appears on rejected candidates

When `MISSING_T_CLASS_EVIDENCE` triggers, `t_class_verdict` is set to `'review'`
and the candidate enters `rejected_candidates`. In future UI rendering, the
`SelectedMIHeater.t_class_verdict` field is meant to signal the engineer to review.
A candidate that was rejected before selection (due to missing evidence) and one
that was selected with a 'review' verdict (theoretical future case) will look the
same in the result model. Add a note in the model docstring or add a
`mi_selection_status` check to distinguish.

---

## R7 — Worked-example test gate still open (MVP merge blocker)

Current tests (`test_mi_selection.py`) use synthetic resistance values and test
engine logic, not engineering correctness. The MVP directive requires:

> "≥2 worked-example MI tests validated against a PUBLISHED vendor design example
> (Thermon MIQ or nVent Raychem MI design guide)."

This gate applies before MI is wired into the pipeline (Pass 3 merge). KR must
provide actual catalogue numbers from a vendor design guide. Without these tests,
Pass 3 cannot be considered merge-ready per the SR_CALCULATION_HARDENING_TRACKER
discipline.

---

## R8 — Candidate sorting: T-class margin and cost not considered

Candidates are sorted by: closest low-voltage W/m to design requirement → lowest
high-voltage W/m → lowest cold-start current. This is sensible for MVP.

Two missing dimensions for future consideration:
1. **T-class margin**: A candidate with max_sheath_temp=130°C against a T4 limit
   (135°C) passes but with only 5°C margin. A candidate with 100°C sheath temp
   against the same limit has 35°C margin. The tighter candidate is not preferred
   by the current sort.
2. **Resistance economics**: Lower Ω/m means longer heater for same circuit — more
   expensive and heavier. Higher Ω/m means shorter, cheaper heater. For field work,
   the shorter heater is usually preferred if it passes all checks.

Not a bug. Log for Pass 4.

---

## R9 — Phase check position: line-level vs project-level

`phase` is stored on `HeatTracingInput` (line level). The phase check in
`get_mi_heater_options` reads `_value(line, 'phase', '1PH')`. This is correct.

However, `ProjectData` has no `phase` default field. If KR later wants to set
a project-wide default phase (e.g., all MI circuits on this project are 1PH),
there is currently no place to store it. When 3PH is added, revisit whether a
`mi_default_phase` on `ProjectData` is needed, or whether line-level is sufficient.

---

## R10 — `SelectedMIHeater` model not yet wired to persistence

`get_mi_heater_options` returns `(best_candidate_dict, alternatives_list)` but
nothing persists these to `SelectedMIHeater`. This is explicitly deferred to
Pass 3. When writing the persistence layer, note that:
- `SelectedMIHeater.heater` is a FK (SET_NULL on delete) — the snapshot fields
  (`heater_resistance_ohms`, `cold_lead_resistance_total_ohms` etc.) preserve the
  calculated values even if the catalogue row is later edited. This is the correct
  pattern, mirrors how SR results work.
- `SelectedMIHeater.cold_lead_option` is also FK (SET_NULL) — same snapshot logic
  applies via `cold_lead_option_code` and `cold_lead_length_m` denormalized fields.

---

---

## Pass 3 State (in progress as at 2026-05-24)

**What is done:**
- `SelectedMIHeater` updated with `selection_status` + `selection_rejection_reasons` (migration 0023 clean, no pending)
- `data_service.py`: `_transform_mi_heater_item()`, `clear_project_workspace_data()` deletes MI rows, `store_calculated_results()` bulk-creates MI rows from `aggregated_results['selected_mi_heaters']`
- `data_service._transform_mi_heater_item` correctly maps candidate dict PKs (`heater_id`, `cold_lead_option_id`) to Django FK columns

**What is NOT yet done (cal.py is untouched):**
- `orchestrate_calculations()` has no MI call; `aggregated_results` has no `selected_mi_heaters` key
- MI rejection records are not yet persisted (only described in model docstring)

---

## P3-R1 — `_transform_mi_heater_item` rejection fallback is fragile

Lines 111–116 of `data_service.py` infer `selection_status` from `heater_id` presence
when neither `selection_status` nor `mi_selection_status` keys exist in the item.
The candidate dict from `get_mi_heater_options` carries neither — it has
`rejection_reasons` (embedded) but not the status keys. The fallback `'selected' if
normalized_item.get('heater_id') else ('rejected' if rejection_reasons else '')`
works for now but is order-sensitive and opaque.

When cal.py is wired, explicitly inject `mi_selection_status` and
`mi_selection_rejection_reasons` into the item dict before appending to
`selected_mi_heaters`, so the transform doesn't need inference. Same pattern as
how SR injects `uid`.

---

## P3-R2 — Rejected MI lines: persistence design decision needed before cal.py wiring

The `SelectedMIHeater` docstring says "Rejected MI selections also use this table."
The engine writes rejection info to `heat_loss['mi_selection_rejection_reasons']`, not
to the candidate dict (which is `{}`). For rejected lines, cal.py must explicitly
build a rejection record and append it to `selected_mi_heaters`. Without this step,
rejected MI lines are silent — they don't appear in any result table, unlike SR
rejections which are visible on `HeatLoss.selection_rejection_reasons`.

Two options when wiring cal.py:

Option A — Store rejection on `HeatLoss` (like SR does): write `mi_selection_status`
and `mi_selection_rejection_reasons` from the heat_loss dict into `HeatLoss` extra
fields. Minimal extra model work, reuses existing storage.

Option B — Always create a `SelectedMIHeater` record even for rejections (null heater,
rejection payload populated). Cleaner per-technology separation; matches the model
docstring intent. Requires building the record from the heat_loss dict directly.

**Recommendation: Option B** — consistent with the model design intent. But needs a
decision before cal.py wiring is finished.

---

## P3-R3 — `aggregated_results` key name needs to be agreed between cal.py and data_service.py

`data_service.store_calculated_results` reads `aggregated_results.get('selected_mi_heaters')`.
When cal.py is wired, it must use exactly this key. Note the existing SR keys:
`selected_tracers`, `alternative_tracers`, `power_distribution`. MI key must be
`selected_mi_heaters` (already in data_service). Confirm cal.py uses this exact name.

---

---

## Pass 3 Persistence Layer — Confirmed Good (2026-05-24)

`test_mi_persistence.py` (4 tests) exercises:
- Selected MI heater snapshot stored correctly with FK references + all float fields
- Rejected MI records persisted (null heater/cold_lead, rejection reasons payload)
- Stale rows cleared on recalculate even when new results are empty
- `clear_project_workspace_data` counts and removes MI rows

The rejection persistence path is wired correctly: cal.py must build a dict with
`mi_selection_status` and `mi_selection_rejection_reasons` keys and append it to
`selected_mi_heaters` for rejected lines. The transform handles both shapes.

**Still pending: `cal.py` orchestration wiring — `get_mi_heater_options` not yet called.**

---

## P3-R4 — No `AlternateMIHeater` model; MI alternatives are silently dropped

`get_mi_heater_options` returns `(best, alternatives_list)`. `store_calculated_results`
only reads `selected_mi_heaters` — there is no `alternative_mi_heaters` key and no
`AlternateMIHeater` model. For MVP this is acceptable; the alternatives exist only
in memory and are discarded after selection.

When UI shows MI results, engineers expect to see ranked options (different resistance
codes, different cold lead lengths) the way SR shows `AlternateTracer`. Log for
post-MVP: add `AlternateMIHeater` model and persistence path. Do not implement now.

---

## P3-R5 — MI trigger: when does cal.py call MI? (decision gap before wiring)

`orchestrate_calculations` runs SR for every confirmed line. MI must not run for
every line unconditionally — that would flood every SR-only project with
`NO_VALIDATED_MI_CATALOGUE_DATA` rejections stored in `SelectedMIHeater` for every line.

The trigger needs a decision. Three options:

A. Per-line field: `HeatTracingInput.cable_technology` (would need adding — not present)
B. Project-level: call MI only when vendor has validated MI catalogue rows — implicit
   opt-in, no field needed, no MI records created if catalogue is empty
C. Per-line `phase` field acts as proxy — MI only runs for `phase='1PH'` lines where
   the vendor has MI capability

Option B is the least disruptive for MVP: `get_mi_heater_options` already returns
`NO_VALIDATED_MI_CATALOGUE_DATA` immediately if the catalogue is empty, so even if
called unconditionally, the result is safe. But it creates empty rejection records in
`SelectedMIHeater` for every line on every SR-only project — storage noise.

**Preferred: call MI only if `project_settings` vendor has at least one validated MI
family. A single DB query at the start of `orchestrate_calculations` is enough.**

---

## P3-R6 — Persistence test hardcoded values are NOT engineering-validated numbers

`test_mi_persistence.py` test_store_calculated_results_persists_selected_mi_snapshot
uses `power_nominal_w: 5284.8` and `power_density_w_m: 50.33`. Quick check:
- I = 230 / (10.5 + 0.04) = 21.82 A → P = 21.82² × 10.5 ≈ 5000 W → W/m ≈ 47.6

The hardcoded 5284.8 W does not match hand-calculation. This is fine — persistence
tests round-trip values through storage, they don't validate arithmetic. But note
that no test in the suite validates the power formula output against a real number.
This is the worked-example gap (R7 in original log) still open.

---

---

## Pass 4 → Design Change State (2026-05-24)

**RESOLVED by design change refactor (12 files, all 187 tests green):**

- P4-R1 resolved: `heating_cable_type` project switch removed entirely; replaced with temperature-triggered auto-escalation in `cal.py`
- P4-R3 resolved: `test_mi_orchestration.py` added with 5 boundary tests covering all trigger/fallback/rejection paths
- P3-R1 resolved: cal.py now explicitly injects `selection_mode` and `selection_status`; transform no longer needs inference
- P3-R2 resolved: rejection records built in `_mi_rejection_result` and appended to `selected_mi_heaters`
- P3-R3 resolved: `selected_mi_heaters` key confirmed in both cal.py and data_service.py
- P3-R5 resolved: MI called only when SR fails specifically due to temperature exceedance; no spurious rejections
- R10 resolved: `SelectedMIHeater` fully wired to persistence

---

## Pass 4 Original State (for historical context)

**What is done:**
- `ProjectData.heating_cable_type` field added (`SR`/`MI`, default `SR`) — migration 0024 clean
- `cal.py` fully wired: `_is_mi_project()` gate, MI selection called, rejection records built, `continue` skips SR path for MI projects
- `fetch_project_data` returns `heating_cable_type` in `project_settings` ✓
- `forms.py`: `heating_cable_type` exposed in project settings form with honest tooltip
- `admin.py`: field visible in list display and filter ✓
- Template: `heating_cable_type` rendered in both project data form partials ✓
- `tests.py`: existing SR fixture dicts updated with `heating_cable_type: 'SR'` — SR tests protected ✓

**No MI orchestration integration test added.** The MI path through
`orchestrate_calculations` (MI mode on, line goes through engine) is exercised
by unit tests only. No end-to-end cal.py test with `heating_cable_type='MI'`.

---

## ⚠️ FLAG FOR KR — P4-R1: Project-level technology switch is a real-world workflow limitation

`_is_mi_project(project_settings)` makes technology selection ALL-OR-NOTHING at
the project level. Every confirmed line on the project runs either SR or MI —
there is no per-line choice.

In real EPC projects, SR and MI coexist on the same project number. Most pipelines
use SR; high-temperature or high-wattage lines use MI. With the current design, an
engineer would need to register TWO projects in eTrace for a single physical project:
one with `heating_cable_type=SR`, one with `heating_cable_type=MI`.

**This is not a code bug and not a reason to stop Codex now.** The code is clean
and isolated. The refactor path is manageable:
- Add `cable_technology` CharField to `HeatTracingInput` (with `blank=True`, default `''`)
- Change `_is_mi_project` to check the LINE first, fall back to project default
- `ProjectData.heating_cable_type` becomes a project-level default, not a hard switch
- Forms add a per-line override in the input table

**Action: KR to decide** whether project-level-only is acceptable for MVP go-live, or
whether per-line override must be in before real project data is entered. If KR
enters a real mixed project and hits this limit, the refactor becomes urgent.
Record this as a known limitation in the user manual / release note.

---

## P4-R2 — MI lines produce no BOQ, no power distribution, no SLD output (by design but needs a user-visible indicator)

The `continue` after MI selection in `cal.py` deliberately skips:
- `compute_power_params`
- `compute_power_distribution`
- `compute_bill_of_quantities`

An engineer running a project in MI mode will get MI selection results but:
- SLD shows nothing (no `PowerDistributionBranch` for MI lines)
- BOQ is empty for MI lines
- Panel loading / breaker sizing is absent
- Cable schedule for cold cables is absent

The calculation results page will appear to show an incomplete run. Without a visible
"MI — BOQ and SLD deferred" indicator, an engineer could mistake this for a bug or
failed calculation.

**No need to stop Codex.** But the UI pass must add a clear status indicator on
MI-mode projects showing what is and is not yet computed. Log as UI debt for the
next UI pass.

---

## P4-R3 — No integration test for the MI orchestration path through cal.py

`tests.py` only added `heating_cable_type: 'SR'` to existing fixtures. There is
no test that sets `heating_cable_type: 'MI'` and exercises the full
`orchestrate_calculations → get_mi_heater_options → selected_mi_heaters` path.

The coverage gap means a regression in the MI orchestration wiring would not be
caught by the test suite. The SR gate is correct (all existing tests stay SR), but
the MI gate is untested at the orchestration level.

**Log for the test pass:** Add at minimum one `orchestrate_calculations` test with
`heating_cable_type='MI'`, a validated MI family in the test DB, and assertions on
`aggregated_results['selected_mi_heaters']`. Not urgent now; add before the first
real project run.

---

---

## Pass 5 State (2026-05-24 — SLD override, result UI, export)

**What is done:**
- `tracer_management.py`: `_mi_option_payload`, `apply_tracer_selection_to_payload` surfaces MI as alternative with `MI:{id}` UID, `save_tracer_override` accepts `MI:` prefix and validates against `SelectedMIHeater.selection_status='available_alternative'`
- `views.py`: `_build_result_workspace_data` fetches MI rows, result view passes `mi_result_rows` and summary counts to template
- `result_tab.html`: MI Option column in main table, MI Selection Records section, alert banner with fallback/alternative counts
- `sld_workspace.js`: MI-specific rendering in SLD detail panel and override dropdown
- `tests.py`: 3 new integration tests (SLD payload MI metadata, export sheet shape, result_view + export combined)
- Test count: 190 (all green)

**NEW OPEN ITEM — P5-R1 (HIGH): MI override UID is ephemeral → stale after recalculation**
`MI:{SelectedMIHeater.id}` changes on every recalculation. SR UIDs are stable (catalogue part codes). After recalculation, saved MI overrides silently revert to SR. Fix: use `MI:{heater.part_number}:{cold_lead_option_code}` as the UID — stable, no migration needed. 15-line change in `tracer_management.py`.

**Still open: P4-R2** — MI auto-fallback lines absent from main results table without explanation.

**Still open: `active_option` dead code** — `active_option` in `apply_tracer_selection_to_payload` is no longer used after MI change. Minor cleanup only.

---

## Pass 3 Watch Items (historical — for reference)

Things to verify as Pass 3 (pipeline integration) is coded:

1. MI selection must be called ONLY when the line's selected vendor has MI catalogue
   data. The current SR flow runs for all confirmed lines unconditionally. MI should
   not generate spurious `NO_VALIDATED_MI_CATALOGUE_DATA` rejections for projects
   that are purely SR — only run MI when the user has requested MI for the line.
   **Decision needed:** Is MI an explicit per-line choice, or an automatic fallback
   when SR cannot satisfy requirements? The MVP directive doesn't settle this clearly.

2. When persisting `SelectedMIHeater`, map candidate dict keys to model fields
   carefully — `cold_lead_resistance_total_ohms` in the candidate dict, but
   `SelectedMIHeater.cold_lead_resistance_total_ohms` in the model. Confirm names
   match or add a mapping function.

3. SR `158 green tests` must stay green after pipeline integration. Run the full
   suite before marking Pass 3 complete.
