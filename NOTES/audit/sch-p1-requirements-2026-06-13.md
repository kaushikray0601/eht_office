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

### A-5 Deduplication Bug  [LOW]

In `cable_schedule.py`, `unique_cable_rows` (a deduplicated dict keyed by cable spec) is
built for the summary totals sheet, but `cable_rows` (the full, non-deduplicated list) is
what is exported in the main schedule tab. If two circuits share the same feeder cable, that
cable will appear twice in the export with different circuit references. The summary tab will
correctly show one combined quantity row, but the main schedule tab will show the duplicate.
This is arguably correct behavior for a "per-circuit" schedule, but it creates confusion when
comparing quantities between tabs. At minimum, a note column "shared feeder — see summary
for combined quantity" would clarify intent.

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

---

## B. EHT Engineering Correctness Review

### B-1 Temperature Constraint Enforcement — Gap at Model Level  [MEDIUM]

`sanatize_input.py` enforces `Oper_T ≤ Maint_T ≤ Design_T` for Excel file uploads (the
primary data entry path). However, `HeatTracingInput` has no `clean()` or `save()` override
that enforces this constraint. A Django admin user entering data directly, or any future API
endpoint that creates `HeatTracingInput` records programmatically, can produce rows where
`Oper_T > Maint_T` or `Maint_T > Design_T`. The calculation engine will then produce
physically invalid heat loss results (negative or grossly underestimated) without raising an
error.

Recommended fix: add a `clean()` method to `HeatTracingInput` enforcing the temperature
ordering constraint. This is a model-level safety net, not a replacement for the upload
sanitizer.

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

### B-3 Single-Phase Assumption — No Hard Enforcement  [LOW]

The cold cable module, SLD, and power distribution are all coded on a single-phase (L-N)
basis. The formula `VD = 2·I·R·L` and the `eht_db_source_impedance_ohm` derivation from
3-phase fault MVA (`V / (I_fault_kA × 1000)`) are single-phase approximations. There is
no runtime check that rejects a project configured for 3-phase EHT (which is a real scenario
for higher-power MI cables, particularly 3-phase skin-effect systems). If a user configures
such a project in the future, the calculations will silently produce wrong results. For the
current release this is acceptable as the scope is explicitly single-phase SR/MI, but the
limitations section of the user manual and verification report should state this explicitly.

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

### B-5 Fault Loop Impedance — Approximation Disclosed, Completeness Gap  [LOW]

`eht_db_source_impedance_ohm = V / (I_fault_ka × 1000)` is a single-phase scalar approximation
derived from a 3-phase fault rating. This method ignores the X/R ratio of the source, which
is the dominant variable in determining actual fault current magnitude at the tracer. The
value is defensibly conservative for most distribution-level EHT panels, but for panels fed
from large transformers with low X/R ratios the approximation can over-estimate fault current
clearance capability. The verification report should note this limitation and recommend that
the user supply an actual measured source impedance when available.

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

### B-7 Accessory Heat Loss — No Published Reference  [LOW]

The insulation accessory heat loss multipliers (flanges, supports, instrumentation taps) use
empirical adder formulas. The verification report cites them but does not reference a
specific IEC/IEEE table. For a commercial EHT design tool, every empirical coefficient must
trace to a published source. This is a documentation gap, not a code defect. The
verification report should either cite the source or state that values are based on
engineering judgment, so a reviewing engineer knows what to audit.

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

### C-2 Dead Code — Commented-Out Models  [LOW]

`eht/models.py` lines 943–1040 contain a large commented-out old model definition
(`ElecEHT_CalculatedTable`, `ElecEHT_IO`) wrapped in a triple-quoted docstring. This is not
an actual docstring — it is assigned to no name, so it is a discarded string literal that
the garbage collector ignores. It serves no purpose and will mislead developers. Delete it.

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

### C-4 Self-Registration Disabled — No User-Facing Indication  [LOW]

`my_register` at `views.py:3610` silently redirects to the login page.
`/register/` is NOT in `_EXEMPT_PREFIXES`, so an unauthenticated user navigating to
`/register/` is first redirected to `/login/?next=/register/`, then after login redirects
to the login page again (since `my_register` just calls `redirect('my_login')`). This
creates a confusing redirect loop for any user who follows a "register" link. If
self-registration is intentionally disabled (all users created by admin), the `/register/`
URL should be removed from `urls.py` or return a clear `403 / "Account creation is
admin-managed"` message.

### C-5 Error File Shared Path — Race Condition on Concurrent Uploads  [MEDIUM]

`sanatize_input.py` writes validation error output to a hardcoded path
`'file_storage/error_file/error_file.xlsx'`. If two users upload invalid files simultaneously,
the second write will overwrite the first before the first user downloads it. The second user
gets correct output; the first user downloads the wrong file (or finds the file already
replaced). Fix: use a per-request unique filename (e.g., include user ID or a UUID in the
filename). The `download_error_file` URL already accepts a variable filename — the generator
just needs to write to a unique path and pass that name back to the client.

### C-6 No Stale-Results Warning After Project Edit  [MEDIUM]

If a user edits project settings (e.g., changes ambient temperature or voltage) and then
views the results or cable schedule, the displayed values still reflect the previous
calculation run. There is no "project settings have changed — results may be outdated" banner.
A first customer will not know that the schedule no longer matches the current project
settings. The UI should compare the `ProjectData` last-modified timestamp against the last
calculation timestamp and show a warning banner if the project is newer than the results.

### C-7 No Project Dashboard / Summary View  [MEDIUM]

The base/project-list page shows projects but no per-project summary: number of lines
calculated, calculation status (complete / in-progress / not run), last calculated date,
number of lines with SR selected vs. MI, total panel loading. A first customer opening the
app after a week away has no way to know the state of any project at a glance.

### C-8 Test Suite Maintenance Failures  [HIGH]

The baseline prior to this session was 305 tests / 8 maintenance failures. These 8 failures
are real regressions that a first customer's Q/A team will encounter. They must be resolved
before the production release. The 8 failures were noted as "database state issue" in
project memory — they need root-cause analysis and individual fixes, not a global reset.

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

### D-9 [MEDIUM] No Rate Limiting on Any Endpoint

**OWASP:** A07 Identification and Authentication Failures / A04 Insecure Design  

There is no rate limiting middleware, no `django-ratelimit`, no IP-based throttling on any
endpoint — including `/login/`, `/register/`, file upload, or any API endpoint. Combined
with D-8 (lockout not wired), the login endpoint is a wide-open brute-force target. File
upload endpoints can be called in a tight loop to exhaust disk space.

**For production:** At minimum, add rate limiting to `/login/` (e.g., 10 attempts per IP
per minute). The simplest drop-in is `django-ratelimit` — it is already a compatible
package. Alternatively, configure rate limiting at the Nginx / Cloudflare level.

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

### Nice-to-Have (Would Increase Willingness to Pay)

- Schedule snapshot / issued-revision model (A-1/A-4 above)
- Cold-start VD check (B-4)
- Project dashboard with calculation status summary (C-7)
- PDF export of cable schedule with basic title block

---

## F. Low-Hanging UX Polish — Non-Invasive Improvements

*These are targeted improvements that do not require deep model changes, new modules, or
calculation engine work. Each can be built with template/view/CSS changes only.*

### F-1 Project Selector in Navbar  [EFFORT: Low]

The current navbar shows the project name but requires navigating to the base page to switch
projects. A dropdown `<select>` in the navbar showing all of the user's projects would let
engineers switch context without a page reload. Implementation: one template change, one
queryset in the context processor.

### F-2 Calculation Status Badge on Project List  [EFFORT: Low]

Add a coloured status badge on the project list: "Not calculated", "Results ready (DD/MM/YY)",
"Settings changed — recalculate". Implementation: compare `ProjectData.updated_at` vs.
the latest `HeatTracingInput` or result timestamp. One additional context annotation per
project row.

### F-3 Project Setup Form Grouped into Logical Sections  [EFFORT: Low-Medium]

Use `<fieldset>` + `<legend>` or Bootstrap card-groups to visually separate:
- **Site & Environmental** (ambient, wind, altitude)
- **Insulation** (type, thickness, conductivity)
- **Process** (fluid, pipe material, temperatures)
- **Electrical** (voltage, fault rating, max CB)
- **Calculation Controls** (SR max runs, termination margin, etc.)

No model change required — pure template/form layout change.

### F-4 Tooltip / Help Text on Technical Fields  [EFFORT: Low]

Add Bootstrap tooltip `title=` attributes to the label of each non-obvious field in the
project setup form. Example: "Maintain Temperature — The minimum pipe surface temperature
that must be maintained during the coldest design condition." Implementation: add `help_text`
to `ProjectDataForm` fields — crispy_forms renders it automatically.

### F-5 MI "Not Available" Reason Text  [EFFORT: Very Low]

When MI is shown as "not available" in the results, display: "MI catalogue for [vendor]
is pending validation. Contact administrator." One template `{% if %}` check on
`is_validated` status.

### F-6 "Results May Be Outdated" Banner  [EFFORT: Low]

When `ProjectData.updated_at > last_calculation_timestamp`, show a dismissible yellow
Bootstrap alert banner on all result/schedule/SLD/BOQ views: "Project settings have changed
since this calculation was run. Recalculate to update results." This is a single view context
variable check.

### F-7 "Jump to Line" Search on Results Table  [EFFORT: Low]

Add a client-side search/filter input above the results table that filters rows by line ID,
pipe tag, or area using JavaScript `input` event + `tr.style.display`. No server change
required. For projects with 50+ lines this is a significant navigation improvement.

### F-8 Excel Export Polish — Freeze Panes + Auto-Width  [EFFORT: Very Low]

In `cable_schedule.py` and `result_export_view`, add two lines to the `openpyxl` workbook
after writing data:
```python
ws.freeze_panes = 'A2'      # freeze header row
for col in ws.columns:
    ws.column_dimensions[col[0].column_letter].width = max(len(str(c.value or '')) for c in col) + 2
```
This makes the Excel export immediately usable without manual formatting.

### F-9 Last-Calculated Timestamp on Results Page  [EFFORT: Very Low]

Show "Last calculated: DD/MM/YYYY HH:MM UTC" at the top of the results page.
The timestamp already exists in the calculation result records — it is just not surfaced
in the template.

### F-10 SLD — Fit-to-Screen Keyboard Shortcut  [EFFORT: Very Low]

JointJS supports `paper.fitToContent()` via JavaScript. Add a "Fit to Screen" button
(or `Ctrl+Shift+F` keyboard shortcut) to the SLD toolbar. This is a single JS event handler
addition. Reviewers and approvers who open large SLDs are currently left zoomed into the
default view with no easy way to see the full diagram.

### F-11 SLD PDF Title Block  [EFFORT: Low-Medium]

The current `sld/pdf/` export produces a bare diagram image. For a design document, an
EHT SLD needs: project name, project number, revision, date, drawn/checked/approved
signatures (blank), and a company logo placeholder. This is an `<html2canvas>` or
`puppeteer`-equivalent overlay on the frontend before the print/download trigger. The SLD
PDF export already exists — the title block is a template overlay addition.

---

## G. Summary Action Table for Codex

Priority: MUST = before production release. SHOULD = for first customer credibility.
NICE = low-risk polish, any sprint.

| ID | Priority | Area | Action |
|----|----------|------|--------|
| D-1 | **MUST** | Security | Remove `ALLOWED_HOSTS = ["*"]` line 30 of settings.py |
| D-2 | **MUST** | Security | Validate `next_url` with `url_has_allowed_host_and_scheme` in `my_login` |
| D-3 | **MUST** | Security | Remove insecure defaults for `SECRET_KEY` and `DEBUG` in settings.py |
| C-8 | **MUST** | Tests | Fix all 8 maintenance test failures — root-cause each one |
| D-5 | **MUST** | Security | Add `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT` to settings.py |
| D-4 | **MUST** | Security | Add `os.path.basename(file_name)` in `download_error_file` |
| D-6 | **MUST** | Catalogue | Guard or delete `import_data_from_file` command (CAT-P1) |
| A-1 | **MUST** | SCH | Create `ScheduleSnapshot` model; remove revision/status fields from `CableScheduleOverride` |
| A-3 | **MUST** | SCH | Add maintain_temp, min_ambient, trace_type, cb_size columns to schedule export headers |
| C-6 | **MUST** | UX | Add "project settings changed — recalculate" warning banner |
| D-8 | **SHOULD** | Security | Wire `UserAttempt` lockout logic in `my_login` |
| D-9 | **SHOULD** | Security | Add rate limiting to `/login/` endpoint |
| D-7 | **SHOULD** | Security | Add file size limit and magic-byte check in `sanitize_file_basic_check` |
| B-1 | **SHOULD** | EHT | Add `clean()` to `HeatTracingInput` for temperature ordering constraint |
| B-4 | **SHOULD** | EHT | Add startup-current VD adequacy check in cold cable sizing |
| B-6 | **SHOULD** | EHT | Persist SR heat-duty rejection reasons on heat_loss record |
| C-1 | **SHOULD** | Code quality | Delete `eht/calculation.py` (dead legacy stub) |
| C-2 | **SHOULD** | Code quality | Delete commented-out model definitions in `models.py:943-1040` |
| C-3 | **SHOULD** | Architecture | Migrate `HeatTracingInput.proj_id` to `ForeignKey(ProjectData, CASCADE)` |
| C-4 | **SHOULD** | UX | Remove `/register/` URL or return clear "admin-managed" message |
| C-5 | **SHOULD** | Architecture | Use per-request unique filename for error file to fix race condition |
| A-2 | **SHOULD** | SCH | Remove overbuilt deferred fields (route_reference, drum_tag, cable_lot, installation_area) from `CableScheduleOverride` |
| D-11 | **SHOULD** | Security | Run `pip-audit` + `npm audit`; patch known-vulnerable packages |
| D-12 | **SHOULD** | Security | Move Django admin to non-default path; restrict by IP |
| F-6 | NICE | UX | Stale-results warning banner |
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
| B-2 | NICE | EHT | Add wind-speed validity range disclosure to verification report |
| B-3 | NICE | EHT | Add single-phase limitation statement to user manual and verification report |
| B-5 | NICE | EHT | Add X/R ratio approximation note to verification report |
| B-7 | NICE | EHT | Add source citations for accessory heat-loss empirical adders |
