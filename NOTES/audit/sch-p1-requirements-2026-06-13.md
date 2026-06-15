# SCH-P1 Pre-Implementation Requirements Review
# Reviewed by Claude — 2026-06-13
#
# CODEX: start reading from line 14.

---

## Sequencing Note

The tracker lists SCH-P1 as **"pending (after CAT-P1)"** and CAT-P1 as **"pending (next pass)"**.
CAT-P1 must complete first — it resolves the live MI `is_validated` discrepancy, guards the
dangerous `import_data_from_file` path, and adds the SR validation-gate decision. SCH-P1
pulling unvalidated catalogue data defeats the procurement credibility goal. **Do CAT-P1 first;
then start SCH-P1.**

---

## Upstream Data Already Available (do not re-calculate at export)

The schedule must pull from already-persisted sizing snapshots. Export must be fast,
deterministic, and auditable — no recalculation on demand.

| Source | Available data |
|---|---|
| SR sizing | `calculation.py` results: circuit power W, CB size A, heat loss W/m, voltage |
| MI sizing | MI engine results: heater type, watts/m, total power |
| Cold cable | `build_cold_cable_sizing_snapshot` dict: cable type, size mm², VD%, fault loop, conductor mass, feeder/branch lengths, sizing status |
| SLD topology | Combined feeder impact in `edit_payload['cold_cable_impact_summary']` |
| Catalogue | Cable type, manufacturer part number (MI families gated by `is_validated`) |

---

## Minimum Procurement Fields — MVP

These are the fields a buyer physically needs to purchase and install. Every field below is
**in scope for SCH-P1**. Nothing listed here is deferred.

| Field | Source | Notes |
|---|---|---|
| Circuit tag / ID | Project model | Must be unique and meaningful |
| Area / location | Project model | Plant area or line segment |
| Process pipe tag | Project model | The line being traced |
| Pipe nominal size | Project model | NPS or DN |
| Maintain temperature (°C) | Design input | Target temperature |
| Design / min ambient (°C) | Design input | Drives heat loss |
| Cable type (SR / MI) | Sizing result | Category |
| Cable catalog number | Catalogue | Actual purchasable part number |
| Installed circuit length (m) | Sizing result | Includes end allowance + connection tail |
| Number of parallel circuits | Sizing result | For circuits with parallel runs |
| Rated watts/m at design temp | Sizing result / catalogue | Power density at operating point |
| Total circuit power (W) | Sizing result | For panel loading |
| Operating voltage (V) | Design input | 120V / 240V / 480V |
| Circuit breaker size (A) | Sizing result | For panel/board schedule |
| Connection box / JB type | Design input or SLD | Reference to JB catalogue |
| Status | Schedule snapshot field | Draft / Issued |
| Revision | Schedule snapshot field | Integer, starts at 0 |

---

## Export Columns — MVP CSV/Excel

Ordered as a typical EHT cable schedule reads left-to-right:

**Main schedule sheet:**

1. Circuit No. / Tag
2. Area / Location
3. Pipe Tag
4. Pipe Size (NPS/DN)
5. Trace Type (SR / MI)
6. Maintain Temp (°C)
7. Min Ambient Temp (°C)
8. Heat Loss (W/m) — from sizing
9. Cable Type / Catalog No.
10. Circuit Length (m)
11. No. of Circuits
12. Watts/m (at design temp)
13. Total Power (W)
14. Voltage (V)
15. CB Size (A)
16. JB / T-Box Reference
17. Status
18. Rev.
19. Notes / Remarks

**Cold cable sub-schedule** (separate sheet or appended rows with distinct row type):

20. Feeder cable size (mm²)
21. Feeder length (m)
22. Branch cable size (mm²)
23. Branch length (m)
24. Feeder VD (%)
25. Cold cable sizing status

---

## Revision / Status Semantics — MVP

Keep it simple. No approval workflow in MVP.

- **Status**: choice field on the schedule **snapshot** (not on individual rows).
  - `Draft` — working copy, internal only
  - `Issued` — released for procurement/construction
- **Revision**: non-negative integer on the snapshot. Starts at 0. Increments on each
  re-issue after first `Issued` status. First issue is Rev. 0.
- **No row-level revision tracking in MVP.** The entire schedule is versioned as a unit.
  Individual row changes between revisions are visible only via the audit trail of snapshot
  objects.
- **No signatures, no approval routing in MVP.** Those belong to document control systems
  (Aconex, Procore, SharePoint), not eTrace.
- **Revision reason**: a short free-text `notes` field on the snapshot is acceptable but
  optional for MVP. Defer if it adds model complexity.

Suggested snapshot model (Codex to decide final shape):

```
ScheduleSnapshot:
    project        → FK to Project
    revision       → PositiveIntegerField, default=0
    status         → CharField choices=['draft', 'issued']
    generated_at   → DateTimeField auto
    generated_by   → FK to User (optional for MVP)
    notes          → TextField blank=True
```

---

## Suggested ScheduleRow Shape

```
ScheduleRow:
    snapshot           → FK to ScheduleSnapshot
    circuit_tag        → CharField
    area               → CharField
    pipe_tag           → CharField
    pipe_size          → CharField
    trace_type         → CharField          # SR / MI
    maintain_temp_c    → DecimalField
    min_ambient_c      → DecimalField
    heat_loss_w_per_m  → DecimalField null=True
    cable_catalog_no   → CharField
    circuit_length_m   → DecimalField
    num_circuits       → PositiveIntegerField
    watts_per_m        → DecimalField null=True
    total_power_w      → DecimalField null=True
    voltage_v          → IntegerField
    cb_size_a          → DecimalField null=True
    jb_reference       → CharField blank=True
    cold_cable_data    → JSONField null=True   # feeder/branch sub-fields
    sizing_status      → CharField             # complete / incomplete / length_missing
    notes              → TextField blank=True
```

The schedule should be a **snapshot model** — a point-in-time capture of sizing results,
not a live computed view. Reasons:
1. Sizing results can change (user edits project, re-runs calculation). A snapshot preserves
   what was sent to procurement.
2. Export is O(1) — no recalculation; just serialise snapshot rows.
3. Revision semantics are natural: each re-issue creates a new snapshot; old snapshots remain
   auditable.

---

## MVP vs Deferred — Hard Line

### IN MVP (minimum to be credible for procurement)

- All fields in the procurement fields table above
- CSV export (one row per circuit)
- Excel export (.xlsx) — header row, column widths, cold cable sub-sheet
- Schedule status (Draft/Issued) + revision number on the snapshot
- Read-only Django view: schedule list + schedule detail
- Regenerate / re-snapshot on demand

### DEFERRED — do NOT build for SCH-P1

- PDF generation with company letterhead / title block
- Full approval workflow (review stages, sign-off, countersignature)
- Row-level revision delta highlighting (what changed vs. previous rev)
- P&ID drawing cross-reference columns
- Cost estimation / unit rate fields
- Conduit / tray sizing columns
- Panel schedule integration / auto-populate board loading
- Weight per metre / total cable weight
- Vendor/supply tracking (PO number, delivery status)
- Multi-discipline cross-reference (instrument, civil)
- QR code / barcode per circuit for field use
- Route / drum tag / cable lot / installation area fields (listed in tracker under SCH-P1 —
  these are pre-construction fields that belong in a later schedule extension pass, not MVP)

---

## Critical Blocker — Must Resolve Before SCH-P1 Ships

`calculation.py:231–256` has no None guard on SR polynomial coefficients A/B/C. Any SR
circuit whose catalogue row has NULL coefficients will **crash** during the power calculation
that feeds the schedule.

**Two acceptable resolutions — Codex/KR to choose:**

**(a) Add None guard in `calculation.py` before SCH-P1 is merged** (preferred — unblocks
everything cleanly).

**(b) SCH-P1 must explicitly exclude SR circuits with NULL coefficients from schedule export**,
displaying a `sizing_status = 'incomplete'` / "sizing incomplete" placeholder for those rows.

Option (a) is cleaner. Option (b) is a viable MVP workaround if (a) requires a broader
calculation-engine pass. This must be resolved — it is not deferrable.

---

## Action Summary for Codex

| ID | Priority | Action |
|----|----------|--------|
| SEQ-001 | Do first | Complete CAT-P1 before starting SCH-P1 implementation |
| BLK-001 | Must resolve before SCH-P1 merges | Add None guard for NULL SR A/B/C coefficients in `calculation.py:231–256`, OR add `sizing_status='incomplete'` exclusion path in schedule export |
| SCH-MVP | SCH-P1 scope | Fields table + export columns above; snapshot model; Draft/Issued/Rev semantics; CSV + Excel; read-only view; regenerate on demand |
| SCH-DEF | Deferred | Route/drum/lot fields, PDF, approval workflow, row-level delta, all items in the Deferred list above |

---
---

# PRODUCTION-READINESS AUDIT — FULL CODEBASE REVIEW
# Reviewed by Claude — 2026-06-14
#
# CODEX: start reading from line 222.

---

## A. SCH-P1 Pass Review — Commit 14d5649

**Overall assessment: Partial credit. Correct intent, wrong model, overbuilt, missing critical columns.**

### A-1 Design Deviation — Wrong Model for Procurement Fields  [CRITICAL]

The requirements spec (above) specified a new `ScheduleSnapshot` model with document-level
`revision` (int) and `status` (`Draft` / `Issued`). Codex instead added the procurement
fields directly to `CableScheduleOverride` (the per-cable-row annotation/override model).
This is architecturally incorrect for the following reasons:

- `CableScheduleOverride` is a per-row override layer — each row carries its own
  `schedule_revision` (CharField) and `review_status`. Rows can diverge: cable A can be on
  "Rev 1 / Checked" while cable B is still "Rev 0 / Generated". A procurement document does
  not work this way. An issued cable schedule is a single document issued at one revision.
- There is no concept of "issuing the schedule" as a unit. You cannot atomically set all rows
  to "Issued / Rev 1" without looping over every override row individually.
- `schedule_revision` is a `CharField` (free text). Revision semantics require a structured
  non-negative integer with ordering. A CharField allows "Rev A", "Rev 1a", "Draft", or any
  arbitrary string — none of which are comparable or sortable.
- The `review_status` choices (`generated`, `review_required`, `checked`, `issued`) on
  individual rows describe the review state of a single annotation, not the document issue
  state. These semantics conflict with the document-level Draft/Issued flow.

**Codex action required:** Create the `ScheduleSnapshot` model as specified in the
requirements above. Keep `CableScheduleOverride` for its original purpose (annotation /
engineering override per cable). Do not conflate them.

**Codex Response:** Agree with the architecture direction for an issued procurement
document. I do not agree that this belongs in the CAT-P1 safety pass or that it blocks the
current engineering MVP/manual review. The current implementation is a lightweight live
engineering schedule with row annotations; a true issued schedule needs a dedicated
`ScheduleSnapshot` workflow pass.

**Status:** Open.

**KR/Codex Action Plan:** Defer external issued-schedule workflow. Implement an
internal cable-schedule lifecycle in `SCH-P2`: generation/modification
date/time/user, internal revision by autogenerated cable tag, and add/change/delete
history. External revision/approval/issued control remains future scope.

### A-2 Overbuilt — Deferred Items Implemented  [MEDIUM]

The requirements spec explicitly listed the following as **DEFERRED — do NOT build for
SCH-P1**: route_reference, drum_tag, cable_lot, installation_area. Codex implemented all
four. Building deferred fields now:
- Adds untested DB columns that occupy schema space with no backing logic or validation.
- Means the `ScheduleSnapshot` refactor (A-1 above) has more fields to migrate.
- Introduces `drum_tag` and `cable_lot` as free-text annotation fields with no linkage to
  any procurement or warehouse system — these fields will stay empty in every real use case
  until a deeper procurement integration pass is done.

These fields are not harmful, but they are premature. The correct path is: fix the snapshot
model first, then revisit whether these fields belong on the snapshot or on a future
procurement extension model.

**Codex Response:** Partly agree. The fields are premature for formal procurement control,
but they are not currently harmful and are covered by migration/tests. I do not recommend
removing them now because that adds churn without improving MVP safety. Their final
ownership should be revisited when `ScheduleSnapshot` is designed.

**Status:** Open.

**KR/Codex Action Plan:** Do not remove the fields now. Hide route/drum/lot/area
columns by default in the schedule UI, and allow users to opt in. Working export
should support visible-column export with clear wording.

### A-3 Missing Minimum Procurement Columns in Export  [HIGH]

Comparing `CABLE_SCHEDULE_EXPORT_HEADERS` in `cable_schedule.py` (31 columns) against
the minimum procurement fields table in this spec:

| Required column | Present in export? |
|---|---|
| Maintain temperature (°C) | **Missing** |
| Min ambient temperature (°C) | **Missing** |
| Trace type (SR / MI) | **Missing** |
| CB size (A) | **Missing** — exported as a power distribution sub-field, not a top-level column |
| Watts/m at design temp | Partial — power output present but not explicitly labeled as "at design temp" |

A cable schedule that omits the maintain temperature, minimum ambient, and trace type is not
a credible procurement document. These are the top three columns an EHT engineer reads first
on any cable schedule. Codex must add these columns from the upstream sizing data.

**Codex Response:** Superseded by KR decision. Maintain temperature, minimum ambient,
trace type, CB size, and W/m basis are hot-engineering/result-page data for the current
product boundary, not cold-engineering cable schedule columns.

**Status:** Closed.

**KR/Codex Action Plan:** Do not add these hot-engineering fields to the cable schedule
for MVP. Keep them visible on result/engineering pages.

### A-4 Live Schedule — Not a Snapshot  [HIGH]

`build_cable_schedule_workspace_data` in `cable_schedule.py` calls `build_project_sld_payload`
live on each schedule export. This means the schedule is rebuilt from the current calculation
results on every export, including on every Excel download. The implications:

- If a user re-runs calculations (e.g., changes project ambient temperature), the new schedule
  export will show updated cable sizes — but any previously issued schedule document is gone.
  There is no "what was issued at Rev 0" view.
- The `schedule_revision` / `review_status` fields on `CableScheduleOverride` give a false
  sense of document control that does not hold: the exported values can change between two
  exports of the "same" revision.

This is not a blocker for a first internal beta, but it is a blocker for giving the schedule
to a procurement team. The `ScheduleSnapshot` model (A-1 above) resolves this entirely.

**Codex Response:** Agree. The current schedule is live engineering output, not an issued
document. Release language should preserve that distinction until a real snapshot/issue
workflow exists.

**Status:** Open.

**KR/Codex Action Plan:** Track cable-schedule lifecycle only for now. On recalculation
or SLD topology change, compare cable tag state and record internal revision increments,
additions, and retirements with date/time/user where available.

### A-5 Deduplication Bug  [LOW]

In `cable_schedule.py`, `unique_cable_rows` (a deduplicated dict keyed by cable spec) is
built for the summary totals sheet, but `cable_rows` (the full, non-deduplicated list) is
what is exported in the main schedule tab. If two circuits share the same feeder cable, that
cable will appear twice in the export with different circuit references. The summary tab will
correctly show one combined quantity row, but the main schedule tab will show the duplicate.
This is arguably correct behavior for a "per-circuit" schedule, but it creates confusion when
comparing quantities between tabs. At minimum, a note column "shared feeder — see summary
for combined quantity" would clarify intent.

**Codex Response:** Agree with the nuance. The current behavior can be valid for
per-circuit traceability, but the export should explicitly label shared feeder rows so the
main sheet and summary sheet are not perceived as contradictory.

**Status:** Open.

**KR/Codex Action Plan:** Add a schedule note/evidence column or legend explaining that
shared feeder rows can appear per circuit while summary quantities are deduplicated.

### A-6 NULL Coefficient Blocker — Status Update  [RESOLVED]

The pre-implementation spec flagged `calculation.py:231–256` as the crash site for NULL
A/B/C coefficients. This concern was written against the legacy stub. The **active** pipeline
(`cal.py` + `tracer_selection.py` + `power_distribution.py`) has proper NULL guards in TWO
places:
1. `_validate_sr_tracers()` in `tracer_selection.py`: filters out DataFrame rows with NaN
   in any of `A_Coeff`, `B_Coeff`, `C_Coeff` before selection.
2. `_sr_power_coefficients()` in `power_distribution.py` lines 22–38: returns `None` and
   logs an error if any coefficient is missing or non-numeric after selection.
3. `orchestrate_calculations()` in `cal.py` lines 205–218: handles `compute_power_params`
   returning `None` and emits a structured rejection record with rule set
   `SR_POWER_PARAMETER_SAFETY_GUARD_V1`.

The blocker is resolved in the active code path. The concern about `calculation.py` is
moot — that file now raises `NotImplementedError` and should be deleted (see Section C).

**Codex Response:** Agree. `QA-P1a` closed the active calculation risk by guarding SR
A/B/C coefficients in the active power-distribution path and preventing partial selected
outputs when power-parameter calculation fails. Deleting the legacy stub is separate
housekeeping.

**Status:** Closed.

**KR/Codex Action Plan:** No further action except later dead-code cleanup of the legacy
calculation stub under `APP-P1`.

---

## B. EHT Engineering Correctness Review

### B-1 Temperature Constraint — WRONG INEQUALITY IN CODE AND MANUAL  [HIGH → MUST FIX]

**Updated finding — 2026-06-14 (post-audit research):**

`sanatize_input.py` line 162 enforces:
```python
Oper_T <= Maint_T <= Design_T   # WRONG
```
This is **physically incorrect** and will reject valid EHT inputs while accepting
invalid ones.

**Correct inequality confirmed by IEEE 515, IEC 62395, and manufacturer design guides
(nVent/Raychem, Thermon, Chromalox):**
```
Maint_T <= Oper_T <= Design_T   # CORRECT
```

**Engineering reasoning:**

| Temperature | Engineering meaning | Typical value (freeze protection example) |
|---|---|---|
| Maint_T (maintain) | Minimum pipe surface temperature the heat tracing must maintain. The heat tracing setpoint. The value used in the heat-loss formula `q = 2π·k·(Maint_T − T_amb)`. | 5 °C |
| Oper_T (operating) | Normal process operating temperature. The pipe/fluid is at this temperature during normal operation. The heat tracer is mostly off during normal operation because the fluid is warmer than the setpoint. Used for SR catalogue maximum-operating-temperature filtering. | 60 °C |
| Design_T (design / exposure) | Maximum temperature the pipe/fluid can reach: includes upset, steam-out, process excursion. The heat tracing cable must survive this temperature without damage. Maps to SR catalogue `Max_Exp_T_On` (maximum exposure temperature with power on). | 120 °C |

Maint_T is the **lowest** (the minimum the tracer must maintain). Oper_T is the
**middle** (normal operation is above the setpoint). Design_T is the **highest**
(cable survival limit for worst-case excursion).

The current code enforces `Oper_T ≤ Maint_T` — i.e., operating temperature must be
*below* the maintain temperature. This is the **reverse** of every published EHT design
guide and standard, and would reject a valid design like {Maint_T=5, Oper_T=60,
Design_T=120} while accepting a physically impossible one like {Maint_T=60, Oper_T=5,
Design_T=120}.

**What needs to change (Codex):**

1. `eht/sanatize_input.py` line 162:
   ```python
   # Replace:
   numeric_values['Oper_T'] <= numeric_values['Maint_T'] <= numeric_values['Design_T']
   # With:
   numeric_values['Maint_T'] <= numeric_values['Oper_T'] <= numeric_values['Design_T']
   ```

2. `eht/sanatize_input.py` line 164 — update error message to match:
   ```python
   "Temperatures must satisfy Maint_T <= Oper_T <= Design_T."
   ```

3. `eht/models.py` — add `clean()` to `HeatTracingInput` with the **corrected**
   constraint `Maint_T <= Oper_T <= Design_T` (model-level safety net for admin/API paths).

4. Tests: update any test fixtures or assertions that use the old (wrong) ordering.
   Confirm existing tests that were testing the wrong constraint are inverted to test
   the correct one.

**User manual (`NOTES/CALCULATION_MODULE_USER_MANUAL.md`) has already been updated**
(Sections 5.2 and 6.3) to state the correct constraint.

**Codex Implementation Update:** Upload sanitizer fixed on 2026-06-14:
`eht/sanatize_input.py` now enforces `Maint_T <= Oper_T <= Design_T` and emits the
matching error message. Added focused regression tests for valid and invalid ordering.
Model-level validation fixed on 2026-06-15: `HeatTracingInput.clean()` enforces the same
constraint for admin/model-form/API-style validation paths. Focused tests cover
`Maint_T == Oper_T`, `Oper_T < Maint_T`, and `Design_T < Oper_T`.

**Status:** Closed for MVP validation behavior.

### B-2 Wind Correction — Rule-of-Thumb, Not IEC/IEEE Standard  [MEDIUM]

The wind correction applied to external convection heat loss uses an empirical formula:
1% per mph of wind above 20 mph, capped at 20% uplift. This is a widely-used industry
shortcut but is not the rigorous approach defined in:
- IEEE 515-2017 Section 5.1: external convection with Nusselt/Reynolds number correlation
- IEC 62395-1 Annex A: similar correlation approach

The shortcut is conservative at moderate winds but may diverge significantly at high winds
(> 50 km/h in exposed process locations). The verification report correctly discloses this
deviation; this finding simply confirms it. For the production release, the verification
report should explicitly state the wind speed range within which the shortcut is calibrated
and flag that locations with design wind speeds above that range require manual review.

**Codex Response:** Agree. This is primarily a disclosure/reporting improvement for MVP.
The rigorous IEC/IEEE wind model should be deferred unless KR wants advanced heat-loss
methods before release.

**Status:** Open.

**KR/Codex Action Plan:** Defer rigorous advanced heat-loss model to future release and
record it in `FUTURE_ENGINEERING_NOTES.md`. Keep current shortcut disclosed in assumptions/
verification material.

### B-3 Single-Phase Assumption — No Hard Enforcement  [LOW]

The cold cable module, SLD, and power distribution are all coded on a single-phase (L-N)
basis. The formula `VD = 2·I·R·L` and the `eht_db_source_impedance_ohm` derivation from
3-phase fault MVA (`V / (I_fault_kA × 1000)`) are single-phase approximations. There is
no runtime check that rejects a project configured for 3-phase EHT (which is a real scenario
for higher-power MI cables, particularly 3-phase skin-effect systems). If a user configures
such a project in the future, the calculations will silently produce wrong results. For the
current release this is acceptable as the scope is explicitly single-phase SR/MI, but the
limitations section of the user manual and verification report should state this explicitly.

**Codex Response:** Agree with the limitation. Current scope is single-phase SR/MI cold
cable, and the manual/report should say so plainly. A runtime hard gate is only needed if
the UI/API can currently create out-of-scope three-phase heating cases.

**Status:** Open.

**KR/Codex Action Plan:** Record true three-phase heat-tracing design as coming soon in
`FUTURE_ENGINEERING_NOTES.md`; current MVP remains single-phase heat-tracing design.

### B-4 Cold-Start Voltage Drop — No Startup-Current Adequacy Check  [MEDIUM]

The cold cable sizing calculates VD at operating current through the cold cable. SR cables
draw a much higher startup current at cold ambient temperature (pre-self-regulation state),
which can be 2–4× the operating current depending on tracer type. The cold cable VD check
does not verify that startup current through the cold cable does not cause the terminal
voltage at the tracer to fall below the minimum self-regulation voltage (typically ~85–90 V
for a 120 V system). If terminal voltage falls below that threshold at startup, the tracer
may fail to self-regulate and draw sustained overcurrent. This is a real-world failure mode.

Recommend: add a startup-current VD cross-check using the tracer's published startup wattage
at minimum ambient temperature and flag as a warning (not a blocker) if VD exceeds 5% at
startup current.

**Codex Response:** Agree as an engineering enhancement, especially for SR. I would not
make it a hard blocker until the rule basis and report wording are agreed. Warning-first is
the right posture. Implemented as a warning-only cold-cable review check.

**Status:** Closed for MVP warning behavior.

**KR/Codex Action Plan:** Implement startup voltage-drop warning in `EHT-P1`. Default
warning threshold is 10% of rated voltage, with an advanced project setting to override.
Warning only; do not automatically upsize on startup current. Implemented with
`ProjectData.startup_vd_warning_threshold_pct`, stored startup VD evidence on
`ColdCableResult`, result/export/SLD visibility, and focused regression coverage.

### B-5 Fault Loop Impedance — Approximation Disclosed, Completeness Gap  [LOW]

`eht_db_source_impedance_ohm = V / (I_fault_ka × 1000)` is a single-phase scalar approximation
derived from a 3-phase fault rating. This method ignores the X/R ratio of the source, which
is the dominant variable in determining actual fault current magnitude at the tracer. The
value is defensibly conservative for most distribution-level EHT panels, but for panels fed
from large transformers with low X/R ratios the approximation can over-estimate fault current
clearance capability. The verification report should note this limitation and recommend that
the user supply an actual measured source impedance when available.

**Codex Response:** Agree. This is a documentation/report limitation for now. A future
source-impedance input model can replace the approximation when project electrical data is
available.

**Status:** Open.

**KR/Codex Action Plan:** Add source-impedance approximation to assumptions/limitations
content. Future source-impedance input can replace the approximation later.

### B-6 SR Rejection with No MI Fallback — Silent Line  [LOW]

If an SR tracer is rejected and `_sr_temperature_limit_exceeded()` returns `False` (i.e.,
temperatures are within SR catalogue range, but no tracer can meet the heat duty), the line
exits `orchestrate_calculations()` without any `selected_tracer`, `selected_mi_heater`, or
diagnostic record being appended. The `heat_loss` record IS appended, so the line appears in
results with a heat loss but no tracer selection. The rejection reason is not persisted in
this path — only the `SR_HEAT_DUTY_REJECTION_DETAILS` diagnostic in `get_tracer_options`
return value holds it, but that diagnostic is not forwarded to the aggregated results. This
means the user sees a line with heat loss but no tracer and no explanation in the UI. The
rejection reasons should be persisted on the heat loss record in this path.

**Codex Response:** Agree. This is useful reporting hardening and should be fixed before
first-customer review if time allows, because unexplained blank selections reduce trust.
It is separate from catalogue import safety. Implemented in two stages: first, every
unselected SR line now keeps a persisted SR diagnostic; second, SR heat-duty no-match
(`NO_SPIRAL_FACTOR_MATCH`) can trigger MI fallback with a distinct
`automatic_heat_duty_fallback` mode.

**Status:** Closed for MVP behavior; keep future refinement open only if KR wants richer
wording.

**KR/Codex Action Plan:** Implement MI fallback when SR is within temperature range but no
validated SR cable from the selected vendor meets heat duty, if MI can solve it. Diagnostics
must state that MI was selected due to SR heat-duty mismatch, not SR temperature exceedance.
If MI is also rejected, the result page must show both SR and MI reasons. Implemented with
focused regression coverage on 2026-06-15.

### B-7 Accessory Heat Loss — No Published Reference  [LOW]

The insulation accessory heat loss multipliers (flanges, supports, instrumentation taps) use
empirical adder formulas. The verification report cites them but does not reference a
specific IEC/IEEE table. For a commercial EHT design tool, every empirical coefficient must
trace to a published source. This is a documentation gap, not a code defect. The
verification report should either cite the source or state that values are based on
engineering judgment, so a reviewing engineer knows what to audit.

**Codex Response:** Agree. For MVP, the honest fix is to label these adders as engineering
judgment unless KR can provide the exact source table. Later, replace or cite coefficients
against the chosen standard/vendor basis.

**Status:** Open.

**KR/Codex Action Plan:** Add accessory heat-loss empirical basis to assumptions/limitations
content unless KR supplies a published coefficient source.

---

## C. Application Architecture Review

### C-1 Dead Code — Legacy Calculation Stub  [MEDIUM]

`eht/calculation.py` is ~460 lines of dead code. The file raises `NotImplementedError`
and wraps the entire old implementation as a string constant `LEGACY_IMPLEMENTATION`. It
imports `pandas`, `numpy`, `scipy`, and multiple model classes that are no longer used via
this path. This file:
- Confuses any new developer reading the codebase about what the calculation engine is.
- Adds dependency surface area that is never exercised.
- The string constant is not tested, not executable, and will rot silently as the active
  code evolves.

Codex action: delete `eht/calculation.py` in full. Confirm all imports from this file
have been removed from other modules before deleting.

**Codex Response:** Agree as housekeeping. I would do it after the current release
checkpoint to avoid mixing cleanup with safety fixes. Before deletion, run an import search
and targeted calculation tests.

**Status:** Closed.

**KR/Codex Action Plan:** Remove from production package under `APP-P1` after confirming
no imports remain. Preserve any useful context in `NOTES/archive/` or git history, not as
dead Python shipped with the app.

**Codex Implementation Update, 2026-06-15:** Deleted `eht/calculation.py` after scanning
for active imports and confirming the live path is `eht.pipeline` -> `eht.cal` ->
`eht.calculations/*`. `manage.py check`, migration dry-run, and the full SQLite suite
passed after deletion.

### C-2 Dead Code — Commented-Out Models  [LOW]

`eht/models.py` lines 943–1040 contain a large commented-out old model definition
(`ElecEHT_CalculatedTable`, `ElecEHT_IO`) wrapped in a triple-quoted docstring. This is not
an actual docstring — it is assigned to no name, so it is a discarded string literal that
the garbage collector ignores. It serves no purpose and will mislead developers. Delete it.

**Codex Response:** Agree. This is low-risk cleanup, but best done in a housekeeping pass
after release safety work is checkpointed.

**Status:** Closed.

**KR/Codex Action Plan:** Remove obsolete commented-out model blocks under `APP-P1` after
confirming no migration/code dependency.

**Codex Implementation Update, 2026-06-15:** Removed the triple-quoted old
`ElecEHT_CalculatedTable` / `ElecEHT_IO` reference block from `eht/models.py`. Django
reported no migration changes and the full SQLite suite passed.

### C-3 Referential Integrity Gap — `HeatTracingInput.proj_id`  [MEDIUM]

`HeatTracingInput.proj_id` is a `CharField` (free text), not a `ForeignKey` to `ProjectData`.
This means:
- Deleting a project does not cascade to delete its `HeatTracingInput` rows.
- Orphaned input rows can accumulate with no owning project.
- Joining input data to projects requires a string match rather than a DB-level join.
- The admin can create `HeatTracingInput` rows for a non-existent `proj_id`.

For production, this should be migrated to a proper `ForeignKey(ProjectData, on_delete=CASCADE)`.
This is a non-trivial migration (requires data cleanup of any existing orphaned rows).
Flag as a technical debt item for the post-release backlog if not done before release.

**Codex Response:** Agree with the long-term model direction. This is a real data migration
and should not be rushed while live project data exists. It belongs in a planned data-model
pass with orphan inspection first.

**Status:** Closed in `APP-P1`.

**KR/Codex Action Plan:** Implement project-owned referential integrity and cascade
deletion carefully under `APP-P1`. Only project-owned rows may cascade on project delete;
catalogue/vendor/reference/cross-project data must not be touched.

**Codex Implementation Update, 2026-06-15:** `HeatTracingInput.proj_id` now has
database-level referential integrity to `ProjectData.proj_id` via migration
`0041_heattracinginput_project_fk`, while preserving the physical column name `proj_id`
and existing raw-ID code patterns. The migration has a fail-fast guard for missing, blank,
or overlength project IDs and does not silently delete/remap data. Regression coverage
confirms deleting one `ProjectData` row cascades that project's line-list and derived
calculation records without touching another project, `ManagedProject`, or catalogue/
reference tables. PostgreSQL migration application remains a deliberate deployment step
after a read-only orphan check.

### C-4 Self-Registration Disabled — No User-Facing Indication  [LOW]

`my_register` at `views.py:3610` silently redirects to the login page.
`/register/` is NOT in `_EXEMPT_PREFIXES`, so an unauthenticated user navigating to
`/register/` is first redirected to `/login/?next=/register/`, then after login redirects
to the login page again (since `my_register` just calls `redirect('my_login')`). This
creates a confusing redirect loop for any user who follows a "register" link. If
self-registration is intentionally disabled (all users created by admin), the `/register/`
URL should be removed from `urls.py` or return a clear `403 / "Account creation is
admin-managed"` message.

**Codex Response:** Agree. This is small UX/security polish. It was not included in
CAT-P1 / SEC-P1a because it is not catalogue/import safety, but it is safe to take in a
near-term `SEC-P1b` pass.

**Status:** Open.

**KR/Codex Action Plan:** Disable/remove self-registration route/link. User creation stays
admin-managed.

### C-5 Error File Shared Path — Race Condition on Concurrent Uploads  [MEDIUM]

`sanatize_input.py` writes validation error output to a hardcoded path
`'file_storage/error_file/error_file.xlsx'`. If two users upload invalid files simultaneously,
the second write will overwrite the first before the first user downloads it. The second user
gets correct output; the first user downloads the wrong file (or finds the file already
replaced). Fix: use a per-request unique filename (e.g., include user ID or a UUID in the
filename). The `download_error_file` URL already accepts a variable filename — the generator
just needs to write to a unique path and pass that name back to the client.

**Codex Response:** Agree. CAT-P1 / SEC-P1a fixed path traversal on download, but the
shared filename race remains. This should be a focused upload workflow hardening task.

**Status:** Open.

**KR/Codex Action Plan:** Fix before production by writing validation error files with
per-request unique filenames.

### C-6 No Stale-Results Warning After Project Edit  [MEDIUM]

If a user edits project settings (e.g., changes ambient temperature or voltage) and then
views the results or cable schedule, the displayed values still reflect the previous
calculation run. There is no "project settings have changed — results may be outdated" banner.
A first customer will not know that the schedule no longer matches the current project
settings. The UI should compare the `ProjectData` last-modified timestamp against the last
calculation timestamp and show a warning banner if the project is newer than the results.

**Codex Response:** Superseded by KR/Codex convergence. Prefer an explicit confirmation
workflow before project setup save or line-list upload clears existing project-owned
calculated outputs.

**Status:** Open.

**KR/Codex Action Plan:** On project setup save or line-list upload, show confirmation when
existing calculated data would be cleared. If confirmed, clear only that project's
calculated result/BOQ/SLD/cable-schedule data and require recalculation. If not confirmed,
cancel the change.

### C-7 No Project Dashboard / Summary View  [MEDIUM]

The base/project-list page shows projects but no per-project summary: number of lines
calculated, calculation status (complete / in-progress / not run), last calculated date,
number of lines with SR selected vs. MI, total panel loading. A first customer opening the
app after a week away has no way to know the state of any project at a glance.

**Codex Response:** Agree as product polish, but defer until after manual release sign-off
or combine with the stale-results/status badge work. It is not a calculation correctness
blocker.

**Status:** Open.

**KR/Codex Action Plan:** Build project dashboard under `APP-P1`: calculation state, last
run, ready/stale status, and useful high-level counts.

### C-8 Test Suite Maintenance Failures  [HIGH]

The baseline prior to this session was 305 tests / 8 maintenance failures. These 8 failures
are real regressions that a first customer's Q/A team will encounter. They must be resolved
before the production release. The 8 failures were noted as "database state issue" in
project memory — they need root-cause analysis and individual fixes, not a global reset.

**Codex Response:** Closed as stale. The current full SQLite suite is green at 320 tests
after EHT-P1 temperature validation. Claude independently confirmed 320/320 tests green on
local PostgreSQL. The intermittent `psycopg.OperationalError: connection is bad` happens in
Codex's sandbox during the custom test-runner database-switch sequence before tests execute;
it is not an application test failure.

**Status:** Closed.

**KR/Codex Action Plan:** No product-code action. Codex may keep using the SQLite fallback
for routine verification. Optional future test-infrastructure hardening: retry once in the
custom PostgreSQL test runner after an `OperationalError`.

---

## D. Cybersecurity & Vulnerability Assessment

This section uses OWASP Top 10 2021 as the primary reference frame.

### D-1 [CRITICAL] Host Header Injection — `ALLOWED_HOSTS = ["*"]`

**File:** `ELECSENSE/settings.py`, line 30
**OWASP:** A05 Security Misconfiguration

```python
# Line 28 — correctly reads from environment:
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["local.enggsense.com", "localhost", "127.0.0.1"])
# Line 30 — OVERWRITES line 28 unconditionally:
ALLOWED_HOSTS = ["*"]
```

Any `Host:` header is accepted. Consequences:
- **Password reset poisoning**: Django's built-in password reset uses `request.get_host()`
  to build the reset link. An attacker can trigger a reset for a victim's email with a
  spoofed `Host: attacker.com` — the victim receives a reset link pointing to the attacker's
  server.
- **Cache poisoning**: if a caching layer (Nginx, CDN) keys on Host, a poisoned entry can
  serve attacker-controlled URLs to all users.
- **Open redirect amplification**: combined with the next finding.

**Fix:** Remove line 30. The env-based setting on line 28 is correct. Verify the
`ALLOWED_HOSTS` env var is set in the production `.env` file.

**Codex Response:** Agree. This is already fixed in the code path from `RELEASE-P1`.
The remaining lesson is operational: the `.env` value must be correct because it overrides
the settings default. KR already corrected the local `.env` entry for `local.enggsense.com`.

**Status:** Closed.

**KR/Codex Action Plan:** No further code action. Keep `.env`/deployment host values
correct.

### D-2 [CRITICAL] Open Redirect — Login View

**File:** `eht/views.py`, lines 3596–3597
**OWASP:** A01 Broken Access Control

```python
next_url = request.POST.get('next', '').strip() or 'base'
return redirect(next_url)
```

`redirect('https://evil.com')` will issue an HTTP 302 to `https://evil.com`. Django's
`redirect()` passes absolute URLs through unchanged. An attacker crafts:

```
POST /login/
next=https%3A%2F%2Fattacker.com%2Fsteal-session
```

After successful login the victim is sent to the attacker's site, where session tokens in
the URL (Referer header, browser history) can be harvested. This is a standard phishing
amplification vector — the login URL is on a trusted domain, which makes the phishing link
appear legitimate.

**Fix:** Before `redirect(next_url)`, validate with Django's built-in:
```python
from django.utils.http import url_has_allowed_host_and_scheme
if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
    next_url = 'base'
return redirect(next_url)
```

**Codex Response:** Agree. This was implemented in CAT-P1 / SEC-P1a. `my_login`
validates `next` using Django's `url_has_allowed_host_and_scheme` and falls back to `base`
for external or unsafe redirect targets. Regression coverage was added.

**Status:** Closed.

**KR/Codex Action Plan:** No further action for this item after the login redirect fix and
regression coverage.

### D-3 [HIGH] Insecure Defaults — DEBUG and SECRET_KEY

**File:** `ELECSENSE/settings.py`, lines 20–26
**OWASP:** A05 Security Misconfiguration

```python
SECRET_KEY = env("SECRET_KEY", default="django-insecure-5ms*1c5@!*%6q)ve3&guld-jc$ii_!pbvyvr*g$_lf)f0d*r6a")
DEBUG = env.bool("DEBUG", default=True)
```

If the `.env` file is absent or `SECRET_KEY` / `DEBUG` are not set:
- The application runs with a published, hardcoded secret key (visible in this source file).
  This compromises all CSRF tokens, session cookies, and signed URLs — they can be forged by
  anyone with access to the source repository.
- `DEBUG = True` exposes full stack traces (including local variable values, SQL queries,
  settings values) in HTTP 500 responses — a goldmine for an attacker mapping the application.

**Fix:** Remove the `default=` arguments from both. The application should fail to start,
not silently degrade, if these environment variables are missing. Django will raise
`ImproperlyConfigured` automatically if `SECRET_KEY` is empty string.

**Codex Response:** Partly agree. For true production deployment, real env values are
mandatory and production-shaped deploy checks should be run with explicit values. I do not
recommend making local engineering startup brittle before MVP manual review. Current
position: keep development-friendly local defaults for now, but treat production hard-fail
policy as an open release/deployment decision.

**Status:** Open.

**KR/Codex Action Plan:** Keep local-development behavior for now. Production must use
environment-provided strong `SECRET_KEY`; admin-driven key rotation is a future
deployment/admin feature.

### D-4 [HIGH] Path Traversal — Error File Download

**File:** `eht/views.py`, lines 3320–3325
**OWASP:** A01 Broken Access Control / A03 Injection

```python
def download_error_file(request, file_name):
    file_path = os.path.join(settings.BASE_DIR, 'file_storage', 'error_file', file_name)
    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_name)
```

Django's `<str:file_name>` URL converter blocks literal `/` characters in the URL path
segment, preventing classic `../` traversal in a single hop. However:
- On Windows hosts, `%5c` (`\`) is not filtered by Django's URL routing and would allow
  traversal (`..%5csettings.py`).
- A URL-decoded `file_name` of `..%2fother_file` could be decoded differently by intermediate
  proxies vs. Django.
- Most critically: there is no validation that the resolved `file_path` is actually inside
  the `error_file` directory. Any file the web process can read becomes accessible.

**Fix:** One line:
```python
file_path = os.path.join(settings.BASE_DIR, 'file_storage', 'error_file',
                         os.path.basename(file_name))
```
`os.path.basename` strips all directory components regardless of separator.

**Codex Response:** Agree. This was implemented in CAT-P1 / SEC-P1a with stricter handling
than basename-only: separator/backslash names are rejected, the resolved file path must stay
inside the error-file directory, and safe basename downloads are covered by tests.

**Status:** Closed.

**KR/Codex Action Plan:** No further action for traversal after CAT-P1 / SEC-P1a. Shared
filename race remains separate C-5 work.

### D-5 [HIGH] Missing HTTPS/Cookie Security Settings for Production

**File:** `ELECSENSE/settings.py`
**OWASP:** A05 Security Misconfiguration

The following Django security settings are absent:

```python
# None of these are set:
SESSION_COOKIE_SECURE = True      # sends session cookie over HTTPS only
CSRF_COOKIE_SECURE = True         # sends CSRF cookie over HTTPS only
SECURE_SSL_REDIRECT = True        # redirects all HTTP to HTTPS
SECURE_HSTS_SECONDS = 31536000   # 1 year HSTS header
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
X_FRAME_OPTIONS = 'DENY'         # clickjacking protection (Django default is SAMEORIGIN — verify)
```

Without `SESSION_COOKIE_SECURE`, session cookies are sent over HTTP connections. If any
page is served over HTTP (even a redirect page), the session cookie is transmitted in
cleartext and can be sniffed on the local network. The Cloudflare tunnel noted in
`CSRF_TRUSTED_ORIGINS` suggests HTTPS is in use — add `SESSION_COOKIE_SECURE` and
`CSRF_COOKIE_SECURE` at minimum. These are zero-cost hardening that Django's
`check --deploy` will flag as errors.

**Note:** `CSRF_TRUSTED_ORIGINS` is already set (good for Cloudflare). The remaining
security headers are the gap.

**Codex Response:** Agree. This was handled in `RELEASE-P1` using environment-driven
secure cookie/HTTPS settings, and production-shaped `check --deploy` passed with explicit
deployment values. HSTS preload/subdomain policy remains a KR deployment decision.

**Status:** Closed.

**KR/Codex Action Plan:** No further action except final deployment confirmation of HTTPS,
secure cookie, and HSTS policy values.

### D-6 [HIGH] Dangerous Management Command — `import_data_from_file`

**File:** `eht/management/commands/import_data_from_file.py`
**Risk:** Catalogue data integrity (CAT-P1 prerequisite)

The command at line 14 hardcodes import from `eht/tmp/elecEHT_Vendor.csv`. This CSV
contains 178 rows of which:
- Only 89 validated rows exist in the current database.
- The remaining rows include fabricated nVent data (wrong exposure ratings) and rows for
  non-existent product families.

Running `python manage.py import_data_from_file` on production would corrupt the validated
vendor catalogue silently (no dry-run mode, no confirmation prompt, no diff output). Any
developer with Django management access — including a cloud shell session — can trigger this.

**Fix (CAT-P1):** Either (a) add an `--allow-destructive` flag and a confirmation prompt,
or (b) rename the command to `import_legacy_vendor_csv_UNSAFE` to make the risk visually
obvious, or (c) delete the command entirely if the CSV import path is permanently retired.
The validated catalogue was seeded via a separate Codex pass — this command's purpose is
now obsolete.

**Codex Response:** Agree. This was implemented in CAT-P1. The command is blocked by
default and requires both `--execute` and an exact confirmation phrase before it can import
legacy CSV data. A regression test verifies that the unconfirmed command raises and leaves
catalogue row counts unchanged.

**Status:** Closed.

**KR/Codex Action Plan:** No further action for accidental legacy import. Any future
catalogue import must stay explicit, reviewed, and non-accidental.

### D-7 [MEDIUM] File Upload MIME Type — Extension Only, Not Magic Bytes

**File:** `eht/sanatize_input.py`, lines 50–53
**OWASP:** A03 Injection / A04 Insecure Design

```python
mime_type, _ = guess_type(file.name)
```

`guess_type` inspects only the file **name** (extension), not the file **contents**.
Renaming a `.html` or `.py` file to `.xlsx` bypasses the MIME check entirely. A malicious
payload (e.g., a macro-enabled `.xlsm` disguised as `.xlsx`) would pass the check. The
subsequent `openpyxl` parse provides a secondary defense (it will reject non-XLSX content),
but:
- An XML-injection payload in a valid XLSX file (e.g., crafted cell content with formula
  injections) is not caught by `openpyxl`.
- A ZIP bomb (valid XLSX structure, exponentially expanded content) could cause a DoS via
  memory exhaustion on parse.

**Recommended fix:** Use `python-magic` to inspect actual file magic bytes as the primary
check. As a lightweight alternative, open the file and check for the XLSX magic bytes
(`PK\x03\x04` — XLSX/OOXML is a ZIP archive) before calling `openpyxl`. Set a file size
limit before parse. Enforce `max_rows` in the `openpyxl` load to prevent ZIP-bomb expansion.

**Codex Response:** Agree. This is a valid upload-hardening task and should be taken in a
dedicated `SEC-P1b` or upload safety pass. I would start with file size limit plus XLSX/ZIP
signature and workbook-open failure messaging, then consider `python-magic` if dependency
policy allows.

**Status:** Open.

**KR/Codex Action Plan:** Implement in `SEC-P1b`: file size limit, XLSX/ZIP magic-byte
check, safer parse failure behavior, and tests for disguised/oversized uploads.

### D-8 [MEDIUM] Brute-Force Protection Built but Never Triggered

**File:** `eht/views.py`, lines 3586–3602 (`my_login`); `eht/models.py` (`UserAttempt`)
**OWASP:** A07 Identification and Authentication Failures

`UserAttempt` model exists with fields for tracking failed login attempts and lockouts.
There is no call to `log_failed_attempt` (or equivalent) anywhere in `my_login`. Failed
login attempts are silently discarded — the lockout mechanism is structurally dead. An
attacker can attempt unlimited password guesses without triggering any account lockout or
alert.

**Fix:** Wire `my_login` to call the lockout logic on failed authenticate() result. Check
the lockout status before attempting authentication. Return a generic error message (do not
confirm whether the username exists).

**Codex Response:** Agree. This is a real security backlog item. It is outside CAT-P1, but
should be addressed before broad internet exposure. We should preserve generic login errors
and add tests for lockout, reset-after-success, and non-enumerating messages.

**Status:** Closed in `SEC-P1b` first pass.

**KR/Codex Action Plan:** Implement in `SEC-P1b` using existing `UserAttempt` or equivalent
logic plus tests for failed attempts, lockout, reset-after-success, and non-enumerating
messages.

**Codex Implementation Update, 2026-06-15:** Existing `UserAttempt` tracking is now wired
into `my_login`. Existing usernames lock after the configured failed-attempt threshold,
successful login clears prior failed attempts, and unknown usernames keep the same generic
error without creating user-linked attempt rows. This is account-specific lockout, not a
substitute for request rate limiting.

### D-9 [MEDIUM] No Rate Limiting on Any Endpoint

**OWASP:** A07 Identification and Authentication Failures / A04 Insecure Design

There is no rate limiting middleware, no `django-ratelimit`, no IP-based throttling on any
endpoint — including `/login/`, `/register/`, file upload, or any API endpoint. Combined
with D-8 (lockout not wired), the login endpoint is a wide-open brute-force target. File
upload endpoints can be called in a tight loop to exhaust disk space.

**For production:** At minimum, add rate limiting to `/login/` (e.g., 10 attempts per IP
per minute). The simplest drop-in is `django-ratelimit` — it is already a compatible
package. Alternatively, configure rate limiting at the Nginx / Cloudflare level.

**Codex Response:** Agree. For the current controlled Cloudflare review tunnel, edge-level
controls may be enough temporarily. For production, login and upload throttling should be
implemented either at Cloudflare/Nginx or in-app with regression tests around legitimate
engineering uploads.

**Status:** Closed in `SEC-P1b` first pass; edge controls remain deployment defense in depth.

**KR/Codex Action Plan:** Implement in `SEC-P1b` with `django-ratelimit` or equivalent,
carefully tuned so normal engineering uploads are not blocked. Document Cloudflare/Nginx
edge limits as defense in depth.

**Codex Implementation Update, 2026-06-15:** `django-ratelimit==4.1.0` is now pinned and
wired on login, line-list upload, valid-row confirmation, and validation-error-file
download. Login is limited by both IP and posted username; upload/download flows are limited
by authenticated user or IP. Thresholds are environment-owned for MVP:
`EHT_LOGIN_IP_RATE_LIMIT`, `EHT_LOGIN_USERNAME_RATE_LIMIT`, `EHT_UPLOAD_RATE_LIMIT`,
`EHT_CONFIRM_UPLOAD_RATE_LIMIT`, and `EHT_ERROR_FILE_DOWNLOAD_RATE_LIMIT`.

**KR/Codex Decision:** Do not make these rate/security thresholds editable in admin for the
MVP. Error-file retention is admin-editable because it is operational storage housekeeping;
login/upload/download throttles are security policy and should remain deployment-owned
until validation, audit logging, and safe runtime semantics exist. A read-only admin
"security settings status" view can be considered later.

### D-10 [LOW] `mark_safe` on Server-Side Markdown HTML

**File:** `eht/views.py`, lines 181, 965
**OWASP:** A03 Injection (XSS)

`mark_safe(rendered.html)` is called where `rendered.html` is the output of rendering a
markdown file from the server filesystem (the calculation manual and design guide). Since
the source markdown is not user-supplied, the XSS risk is limited to: (1) the server
filesystem being compromised, or (2) the markdown renderer emitting unsafe HTML from the
markdown source content. The risk is low for the current deployment, but the pattern is
fragile. If the manual is ever editable via admin, this becomes an XSS sink immediately.
Document this constraint: "manual files must be version-controlled and reviewed — never
editable via admin or user upload."

**Codex Response:** Agree with the constraint. Risk is low while manuals/design guides are
repo-controlled reviewed files, but this must not become an admin/user-editable Markdown
feature without sanitization. The constraint should be documented in release/security notes.

**Status:** Open.

**KR/Codex Action Plan:** Do not add all `NOTES/` to `.gitignore`. Keep PM/audit notes as
development memory. Ensure internal notes are not exposed or admin/user editable in
production unless intentionally published.

### D-11 [LOW] Django and Package Version Hygiene

No `requirements.txt` version pinning audit was performed in this session, but the following
known-vulnerable surface areas should be checked before the production release:

- **Django**: Confirm the installed version is the latest 5.x LTS release. Django has had
  security patches in 5.0.x series (SQL injection in specific ORM paths, session fixation
  in older versions). Run `pip install --upgrade django` in a staging environment and re-test.
- **openpyxl**: Versions prior to 3.1.2 had a ReDoS vulnerability in formula parsing.
- **Pillow** (if used): Frequent CVEs; confirm version.
- **JointJS (frontend)**: Confirm the version in use. JointJS 3.x had XSS issues in earlier
  patch releases via malicious diagram JSON. Since SLD topology data is user-persisted, an
  attacker who can write to a project's SLD topology could inject XSS payloads into the
  JointJS renderer.

**Action for CAT-P1 or a dedicated SEC-P1:** Run `pip-audit` (or `safety check`) against
the installed packages. Check `npm audit` for JS dependencies if `package.json` exists.

**Codex Response:** Agree. This belongs in a dedicated dependency hygiene pass because it
may require network access, package upgrades, and regression testing. It should be run in
staging before production release, not mixed into catalogue safety work.

**Status:** Open.

**KR/Codex Action Plan:** Dedicated dependency hygiene pass before production release:
Django, openpyxl, JointJS, Python/JS packages, vulnerability results, upgrade decisions,
and regression evidence.

### D-12 [LOW] Django Admin Exposed at Default Path

**File:** `ELECSENSE/urls.py` (not read, inferred from middleware exempt list: `/admin/`)
**OWASP:** A05 Security Misconfiguration

The Django admin is mounted at `/admin/` — the default path that automated scanners target
first. For a production application, the admin should be:
- Mounted at a non-obvious path (e.g., `/internal-control-<random>/`), AND/OR
- Restricted by IP at the Nginx / Cloudflare level, AND
- Protected by 2FA (e.g., `django-otp`).

The admin is the highest-privilege entry point in the application. A compromised admin
account can corrupt the entire vendor catalogue, delete all projects, and access all user
data.

**Codex Response:** Agree for production. For the present controlled review environment,
this can be deferred if Cloudflare/account access is restricted. Before production, admin
access should be constrained by at least IP/identity controls, and a non-default path or
2FA should be considered.

**Status:** Partly closed in `SEC-P1b`; remaining controls are deployment work.

**KR/Codex Action Plan:** Review before production: non-default admin path,
Cloudflare/IP/identity restriction, 2FA, strong admin passwords, and logging. A honeypot
package can be considered only as a low-friction signal/decoy, not a primary control.

**Codex Implementation Update, 2026-06-15:** `DJANGO_ADMIN_PATH` now controls the mounted
Django admin URL, the login-required middleware exempt path, and the staff-only landing-page
admin link. Default remains `admin/` for local development; production should set a
non-default path in environment. This does not replace Cloudflare/IP/identity restriction,
2FA, strong admin passwords, and logging.

---

## E. First-Customer Perspective (Buyer View)

*Imagining I am an EHT design engineer buying eTrace as my first EHT design software.*

### What I Would Love

- **SLD auto-generation from sizing is genuinely impressive.** I have never seen an EHT
  design tool that generates a single-line diagram from circuit sizing automatically. This
  alone is a differentiating feature versus spreadsheet tools.
- **Cold cable sizing with fault loop check.** Most tools I have seen leave cold cable to
  the engineer's hand-calc. Having the sizing, VD check, and fault loop status in one pass
  is a real time-saver.
- **Per-project isolation.** I can have multiple projects open without data mixing. Good.
- **Verification report.** The presence of a documented verification report builds
  confidence that the calculations are defensible in a HAZOP or client audit. I would use
  this as my "design basis" document.
- **Engineering transparency.** The calculation outputs show rule set IDs and rejection
  reasons, not just final numbers. An experienced engineer can see WHY a tracer was selected
  or rejected.

### What I Would Dislike

- **The project setup form has ~40 fields with no logical grouping or progressive disclosure.**
  When I first open "create project," I am confronted with ambient temperature, insulation
  type, insulation thickness, wind speed, voltage, fault rating, max CB size, SR max runs,
  ground reflectivity, pipe material, fluid, and more — all on one page with no sections.
  For a new user this is overwhelming. For an experienced user it is still friction. Group
  these into tabbed sections: Basic / Thermal / Electrical / Advanced.
- **MI "not available" with no explanation.** When MI is not selectable (because the
  catalogue has `is_validated=False`), the UI says "not available" but does not say why.
  A buyer who does not know about the catalogue validation gate will think the software
  does not support MI cables, which is a deal-breaker for high-temperature applications.
- **No project dashboard.** The base page shows a list of project names. I cannot see, at
  a glance, which projects have been calculated, when they were last run, or how many lines
  are complete vs. missing sizing. I have to open each project to check its state.
- **No print view for the schedule.** An EHT cable schedule needs to go into a
  document package — 11×17 paper, title block, revision stamp. The current Excel export
  is bare bones. Even a "print preview" mode with basic formatting would be better than
  nothing.
- **Recalculating overwrites previous results with no warning.** If I sent a schedule to
  procurement last week and re-run today with updated line lengths, the previous schedule
  is gone. There is no "issued schedule" that is frozen.

**KR/Codex Disposition:** Accepted as useful buyer-perspective feedback with product-boundary
adjustments. Project setup grouping/help text, MI not-available reason, dashboard, and
confirmation-before-clearing-results are planned. Formal issued schedule freezing is deferred
to cable-schedule lifecycle/snapshot work rather than being forced into the current live
engineering schedule.

### Must-Have Before I Would Buy

1. **Fix the 8 failing tests.** A commercial engineering tool with known test failures is
   not releasable. Any buyer doing due diligence will run the test suite.
2. **Fix the ALLOWED_HOSTS wildcard (D-1).** This is a security issue that no corporate
   IT department will approve.
3. **Fix the open redirect in login (D-2).** Same — automatic rejection in any security
   review.
4. **Validated MI catalogue (at least 1 complete validated family).** The first customer
   will want to use MI on at least some lines. An entirely unvalidated catalogue makes the
   MI module unusable on day one.
5. **Cable schedule that shows maintain temperature, trace type, and min ambient.** A
   schedule without these three columns is not a usable procurement document.
6. **A "stale results" warning (C-6).** If I change a project setting, I need to know my
   displayed results are outdated.
7. **Remove DEBUG default = True and insecure SECRET_KEY default (D-3).** Non-negotiable
   for production deployment.
8. **Document the wind correction limitation (B-2) in the verification report.** I need to
   know when to hand-check results.

**KR/Codex Disposition:** D-1, D-2, D-4, D-5, D-6, and test-suite stability are already
closed or mitigated. MI catalogue validation remains a KR/Claude data-governance lane.
Cable-schedule hot-engineering columns are not accepted for MVP; those values belong in
results/engineering pages. Stale-result warning is reframed as confirmation before clearing
project-owned calculated outputs. D-3 production key policy remains open for later
deployment/admin design.

### Nice-to-Have (Would Increase Willingness to Pay)

- Schedule snapshot / issued-revision model (A-1/A-4 above)
- Cold-start VD check (B-4)
- Project dashboard with calculation status summary (C-7)
- PDF export of cable schedule with basic title block

**KR/Codex Disposition:** Accepted into planned passes: schedule lifecycle under `SCH-P2`,
startup voltage-drop warning under `EHT-P1`, dashboard under `APP-P1`, and document-package
polish under later UX/SCH work.

---

## F. Low-Hanging UX Polish — Non-Invasive Improvements

*These are targeted improvements that do not require deep model changes, new modules, or
calculation engine work. Each can be built with template/view/CSS changes only.*

### F-1 Project Selector in Navbar  [EFFORT: Low]

The current navbar shows the project name but requires navigating to the base page to switch
projects. A dropdown `<select>` in the navbar showing all of the user's projects would let
engineers switch context without a page reload. Implementation: one template change, one
queryset in the context processor.

**Codex Response:** Agree. Useful navigation polish, but not an MVP safety blocker. Good
candidate for a small first-customer UX pass.

**Status:** Open.

**KR/Codex Action Plan:** Add to `UX-P1` as low-priority navigation polish.

### F-2 Calculation Status Badge on Project List  [EFFORT: Low]

Add a coloured status badge on the project list: "Not calculated", "Results ready (DD/MM/YY)",
"Settings changed — recalculate". Implementation: compare `ProjectData.updated_at` vs.
the latest `HeatTracingInput` or result timestamp. One additional context annotation per
project row.

**Codex Response:** Agree. This should be combined with the stale-results warning so the
same freshness logic is used consistently across dashboard/results/schedule pages.

**Status:** Open.

**KR/Codex Action Plan:** Add to `UX-P1`; share freshness/status logic with dashboard and
project-change confirmation work.

### F-3 Project Setup Form Grouped into Logical Sections  [EFFORT: Low-Medium]

Use `<fieldset>` + `<legend>` or Bootstrap card-groups to visually separate:
- **Site & Environmental** (ambient, wind, altitude)
- **Insulation** (type, thickness, conductivity)
- **Process** (fluid, pipe material, temperatures)
- **Electrical** (voltage, fault rating, max CB)
- **Calculation Controls** (SR max runs, termination margin, etc.)

No model change required — pure template/form layout change.

**Codex Response:** Agree. This improves first-use confidence and can be done without
calculation risk. It should stay restrained and functional, not become a redesign project.

**Status:** Open.

**KR/Codex Action Plan:** Add to `UX-P1` as low-priority first-customer polish.

### F-4 Tooltip / Help Text on Technical Fields  [EFFORT: Low]

Add Bootstrap tooltip `title=` attributes to the label of each non-obvious field in the
project setup form. Example: "Maintain Temperature — The minimum pipe surface temperature
that must be maintained during the coldest design condition." Implementation: add `help_text`
to `ProjectDataForm` fields — crispy_forms renders it automatically.

**Codex Response:** Agree. Prefer form `help_text` where possible so guidance remains close
to the field and testable in templates.

**Status:** Open.

**KR/Codex Action Plan:** Add to `UX-P1`. Prefer form `help_text` and minimal tooltips.

### F-5 MI "Not Available" Reason Text  [EFFORT: Very Low]

When MI is shown as "not available" in the results, display: "MI catalogue for [vendor]
is pending validation. Contact administrator." One template `{% if %}` check on
`is_validated` status.

**Codex Response:** Agree, and this is more important than its effort suggests. It prevents
users from mistaking a catalogue governance gate for missing MI capability. Coordinate with
Claude/KR on final MI validation wording.

**Status:** Open.

**KR/Codex Action Plan:** Add to `UX-P1`/catalogue readiness messaging. This is high-value
despite low effort because it prevents users from thinking MI is unsupported.

### F-6 "Results May Be Outdated" Banner  [EFFORT: Low]

When `ProjectData.updated_at > last_calculation_timestamp`, show a dismissible yellow
Bootstrap alert banner on all result/schedule/SLD/BOQ views: "Project settings have changed
since this calculation was run. Recalculate to update results." This is a single view context
variable check.

**Codex Response:** Superseded by KR/Codex convergence. Use a confirmation workflow before
clearing/replacing project-owned calculated outputs, rather than a passive stale-results
banner only.

**Status:** Open.

**KR/Codex Action Plan:** Implement confirmation on project setup save or line-list upload:
if existing calculated data would be cleared, proceed only after user confirmation.

### F-7 "Jump to Line" Search on Results Table  [EFFORT: Low]

Add a client-side search/filter input above the results table that filters rows by line ID,
pipe tag, or area using JavaScript `input` event + `tr.style.display`. No server change
required. For projects with 50+ lines this is a significant navigation improvement.

**Codex Response:** Agree. Good candidate for manual review productivity after the
freshness/status work.

**Status:** Open.

**KR/Codex Action Plan:** Add to `UX-P1` for result-table navigation.

### F-8 Excel Export Polish — Freeze Panes + Auto-Width  [EFFORT: Very Low]

In `cable_schedule.py` and `result_export_view`, add two lines to the `openpyxl` workbook
after writing data:
```python
ws.freeze_panes = 'A2'      # freeze header row
for col in ws.columns:
    ws.column_dimensions[col[0].column_letter].width = max(len(str(c.value or '')) for c in col) + 2
```
This makes the Excel export immediately usable without manual formatting.

**Codex Response:** Agree. This is harmless polish with high day-to-day value. It can ride
with the next schedule export touch-up.

**Status:** Open.

**KR/Codex Action Plan:** Add to `UX-P1`/schedule export polish.

### F-9 Last-Calculated Timestamp on Results Page  [EFFORT: Very Low]

Show "Last calculated: DD/MM/YYYY HH:MM UTC" at the top of the results page.
The timestamp already exists in the calculation result records — it is just not surfaced
in the template.

**Codex Response:** Agree. This pairs naturally with the stale-results banner/status badge.

**Status:** Open.

**KR/Codex Action Plan:** Add to `UX-P1`; pair with dashboard/status work.

### F-10 SLD — Fit-to-Screen Keyboard Shortcut  [EFFORT: Very Low]

JointJS supports `paper.fitToContent()` via JavaScript. Add a "Fit to Screen" button
(or `Ctrl+Shift+F` keyboard shortcut) to the SLD toolbar. This is a single JS event handler
addition. Reviewers and approvers who open large SLDs are currently left zoomed into the
default view with no easy way to see the full diagram.

**Codex Response:** Agree. This is useful SLD reviewer polish and should be small, but I
would verify it with browser smoke coverage because SLD layout regressions are visually
painful.

**Status:** Open.

**KR/Codex Action Plan:** Review existing SLD fit/full-screen controls first. Add keyboard
shortcut only if small and covered by JS/browser smoke checks.

### F-11 SLD PDF Title Block  [EFFORT: Low-Medium]

The current `sld/pdf/` export produces a bare diagram image. For a design document, an
EHT SLD needs: project name, project number, revision, date, drawn/checked/approved
signatures (blank), and a company logo placeholder. This is an `<html2canvas>` or
`puppeteer`-equivalent overlay on the frontend before the print/download trigger. The SLD
PDF export already exists — the title block is a template overlay addition.

**Codex Response:** Agree for document-package maturity. It is lower priority than the
stale-results warning and schedule minimum columns, but should be done before calling SLD
PDF export issue-ready.

**Status:** Open.

**KR/Codex Action Plan:** Add to `UX-P1` as low-priority document-package polish.

---

## G. Summary Action Table for Codex

Priority: MUST = before production release. SHOULD = for first customer credibility.
NICE = low-risk polish, any sprint.

| ID | Priority | Area | Action |
|----|----------|------|--------|
| B-1 | Closed | EHT | Upload sanitizer and model-level `HeatTracingInput.clean()` now enforce corrected temperature order |
| B-4 | Closed | EHT | Startup-current cold-cable VD warning added; default threshold 10%, warning only |
| C-3 | Closed | Architecture | `HeatTracingInput` now FK-owned by `ProjectData`; guarded migration and cascade tests added |
| C-6/F-6 | Closed | UX/Data | Confirmation now required before project setup or line-list upload clears existing calculated outputs |
| D-7 | Closed | Security | Upload file-size/MIME/magic-byte/path-name hardening and bounded error-file retention added |
| D-8/D-9 | Closed | Security | Login attempt tracking and `django-ratelimit` request throttling added |
| D-11 | **MUST** | Security | Run dedicated dependency hygiene pass for Django/openpyxl/JointJS/Python/JS packages |
| SCH-P2 | **SHOULD** | SCH | Hide later procurement columns by default; add visible-column export and internal cable lifecycle tracking |
| A-3 | Closed | SCH | Do not add hot-engineering fields to cable schedule for MVP; keep them on result pages |
| D-1/D-2/D-4/D-5/D-6/C-8 | Closed | Security/Tests | Already fixed or mitigated in current worktree |
| D-3 | Deferred | Security | Keep dev-friendly defaults for now; production env secret and future key-rotation/admin mechanism |
| C-1/C-2 | Closed | Code quality | Dead legacy calculation stub and commented-out model block removed after import/dependency check |
| C-4 | Closed | UX | `/register/` disabled with HTTP 410; user creation remains admin-managed |
| C-5 | Closed | Architecture | Error-file race fixed with bounded rotating filenames and retention policy |
| B-6 | Closed | EHT | MI fallback now supports SR heat-duty no-match and preserves both SR/MI reasons |
| D-12 | Partly closed | Security | Configurable admin path added; access restriction, 2FA, logging remain deployment controls |
| F-1 | NICE | UX | Project selector dropdown in navbar |
| F-2 | NICE | UX | Calculation status badge on project list |
| F-3 | NICE | UX | Group project setup form into logical sections |
| F-4 | NICE | UX | Tooltip help text on technical form fields |
| F-5 | NICE | UX | MI "not available" — show reason text |
| F-7 | NICE | UX | Jump-to-line search on results table |
| F-8 | NICE | UX | Excel freeze panes + auto-column width |
| F-9 | NICE | UX | Last-calculated timestamp on results page |
| F-10 | NICE | UX | SLD fit-to-screen button / keyboard shortcut |
| F-11 | NICE | UX | SLD PDF title block overlay |
| B-2/B-3 | NICE | EHT | Record advanced heat loss and true three-phase heat tracing in future engineering notes |
| B-5/B-7 | NICE | EHT | Add source-impedance and accessory-heat-loss assumptions/limitations |
