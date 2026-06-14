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
