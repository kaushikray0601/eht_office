# Current Phase Tracker

Last updated: 2026-06-07

## Active Phase

Phase A: production hardening for the current SR/MI + cold cable + SLD path.

## Current State

- The previous large cold-cable/SLD code diff is not present in the current
  workspace state. Current dirty files are the `CC-P1` code/docs plus
  untracked project-management/orientation files, including `CLAUDE.md` and
  `NOTES/project_management/`.
- Migrations through `0034_rcd_cu_only_cold_cable` apply cleanly in the SQLite
  test database. The default PostgreSQL connection was unavailable during the
  2026-06-07 checkpoint, so default-DB migration status was not reverified.
- Latest full test status: `275 tests OK` on 2026-06-07.
- Latest quick health check: `venv/bin/python manage.py check` passed on 2026-06-07.

## Active Work Queue

### PM-00 - Project Management Setup

Status: complete

- [x] Create `NOTES/project_management/`.
- [x] Create `MASTER_ROADMAP.md`.
- [x] Create `CURRENT_PHASE_TRACKER.md`.
- [x] Create `CODEX_MEMORY.md`.
- [x] Create `DECISION_LOG.md`.
- [x] Create `OPEN_QUESTIONS.md`.
- [x] Create `RISK_REGISTER.md`.
- [x] Create `RELEASE_CHECKLIST.md`.
- [x] Run full stabilization checks after file creation.
- [ ] Decide whether to checkpoint/commit the current project-management files.

### CC-P0 - Stabilization Checkpoint

Status: complete

- [x] Run `venv/bin/python manage.py check`.
- [x] Run `env USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run`.
- [x] Run `node --check static/js/sld_workspace.js`.
- [x] Run `git diff --check`.
- [x] Run full `env USE_POSTGRES=false venv/bin/python manage.py test eht -v 2 --noinput`.
- [x] Review dirty diff for accidental or stale changes.
- [x] Record final checkpoint status in `CODEX_MEMORY.md`.

Checkpoint result, 2026-06-07:

- `manage.py check`: passed.
- `makemigrations --check --dry-run` with `USE_POSTGRES=false`: passed, no changes detected.
- `node --check static/js/sld_workspace.js`: passed.
- `git diff --check`: passed.
- Full `eht` test suite with `USE_POSTGRES=false`: 272 tests passed.
- Plain `showmigrations` against the default PostgreSQL connection failed
  because the database connection was unavailable; this did not affect the
  SQLite-mode test migration run.

### CC-P1 - Installation-Method Catalogue Readiness

Status: complete

- [x] Confirm which cold-cable installation methods have validated catalogue rows.
- [x] Improve project setup help/validation so users understand unavailable methods.
- [x] Add admin/readiness feedback for catalogue rows by installation method.
- [x] Add tests for method with no rows and method with valid rows.

Checkpoint result, 2026-06-07:

- Live catalogue inspection: Method E has 4 validated 3C rows and 10 validated
  4C rows. Methods B2, C, D1, and D2 have no validated rows.
- Project setup now shows readiness badges and help text for the selected
  cold-cable basis.
- Admin now shows project/catalogue readiness for the selected method/basis.
- Cold-cable sizing preserves explicit unsizeable guidance when the selected
  method has no validated rows.
- Calculation manual updated.
- Targeted `ColdCableFoundationTests` and `ProjectDataViewTests`: 46 tests passed.
- Full SQLite-mode `eht` suite: 275 tests passed.

### CC-P2 - Per-Segment 3C Reporting

Status: pending

- [ ] Surface each outgoing 3C segment in cold-cable result export.
- [ ] Surface each outgoing 3C segment in cable schedule.
- [ ] Add report evidence for critical segment versus all segments.
- [ ] Add tests for unequal outgoing lengths and unequal selected 3C sizes.

### CC-P3 - 3PH JB Phase-Balancing Visibility

Status: pending

- [ ] Define phase-slot semantics for 3PH JB outgoing circuits.
- [ ] Design phase-slot data model and migration. Phase-balancing visibility
      requires a schema change to `PowerDistributionBranch` or `ColdCableResult`.
- [ ] Store/display phase assignment or inferred phase position.
- [ ] Summarize phase currents and imbalance.
- [ ] Keep this as visibility/review first, not automatic topology optimization.

### CC-P4 - Panel/Load Summary

Status: pending

- [ ] Aggregate MCB count, breaker sizes, load current, and connected load.
- [ ] Group by panel/source where source identity exists.
- [ ] Surface review-required/unsizeable counts.
- [ ] Add result/export sheet.

### SCH-P1 - Procurement-Grade Cable Schedule

Status: pending

- [ ] Add route/reference fields.
- [ ] Add drum tag / cable lot fields.
- [ ] Add installation area/basis fields.
- [ ] Add revision/review status.
- [ ] Improve Excel export for procurement review.

### SLD-P1 - Visual Review Badges

Status: pending

- [ ] Badge missing cable length.
- [ ] Badge cold cable review-required or unsizeable.
- [ ] Badge manual override.
- [ ] Badge stale/review-required topology.
- [ ] Add tests for metadata and basic rendering strings.

### SLD-P2 - Topology Edit Impact Summary

Status: pending

- [ ] Show affected MCBs and breaker rating changes.
- [ ] Show cable length/size/mass deltas where known.
- [ ] Show affected BOQ/schedule rows.
- [ ] Persist or export impact evidence.

### QA-P1 - Worked Examples and Verification Alignment

Status: pending

- [ ] Add SR worked example.
- [ ] Add MI worked example.
- [ ] Add direct 1PH cold-cable worked example.
- [ ] Add 3PH JB cold-cable optimization worked example.
- [ ] Confirm report formulas are aligned with code.
- [ ] Verify Sections B-E formula text in the verification report against
      `cold_cable.py`, `pipeline.py`, and `calculation.py` (covers Risk R-006).

### RELEASE-P1 - Production Readiness Sweep

Status: pending

- [ ] Full test suite green.
- [ ] Migrations applied and checked.
- [ ] Manual demo project verified.
- [ ] Known limitations visible in UI/report/manual.
- [ ] Release checklist complete.
