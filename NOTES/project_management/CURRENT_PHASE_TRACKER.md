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
  test database. Local PostgreSQL is healthy; earlier first-attempt failures
  were Codex command-sandbox local-network restrictions, not a database outage.
  PostgreSQL-backed Django tests should be run with local Postgres access
  enabled instead of falling back to SQLite.
- Latest full test status: `281 tests OK` on 2026-06-07.
- Latest SLD regression check: `SldTopologyWorkflowTests` 26 tests passed
  against PostgreSQL test DB `eht_local_test` on 2026-06-07 after browser
  lifecycle hardening for topology controls.
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
- Plain `showmigrations` against the default PostgreSQL connection failed in
  the initial Codex sandbox because local Postgres access was blocked there.
  Re-running with local Postgres access confirmed the default PostgreSQL
  connection and migrations are usable.

### CC-P1 - Installation-Method Catalogue Readiness

Status: complete

- [x] Confirm which cold-cable installation methods have validated catalogue rows.
- [x] Improve project setup help/validation so users understand unavailable methods.
- [x] Add admin/readiness feedback for catalogue rows by installation method.
- [x] Add tests for method with no rows and method with valid rows.

Checkpoint result, 2026-06-07:

- Live catalogue inspection: Method E has 4 validated 3C rows and 10 validated
  4C rows. Methods B2, C, D1, and D2 have no validated rows.
- Project setup now exposes Method E as the active selectable method and Method
  D2 as a disabled coming-soon option. B2, C, and D1 are hidden from setup for
  now.
- Admin now shows project/catalogue readiness for the selected method/basis.
- Cold-cable sizing preserves explicit unsizeable guidance when the selected
  method has no validated rows.
- Calculation manual updated.
- Targeted `ColdCableFoundationTests` and `ProjectDataViewTests`: 48 tests passed after the Method E/D2 UI adjustment.
- Full SQLite-mode `eht` suite: 275 tests passed.

### CC-P2 - Per-Segment 3C Reporting

Status: complete

- [x] Surface each outgoing 3C segment in cold-cable result export.
- [x] Surface each outgoing 3C segment in cable schedule.
- [x] Add report evidence for critical segment versus all segments.
- [x] Add tests for unequal outgoing lengths and unequal selected 3C sizes.

Checkpoint result, 2026-06-07:

- Result tab now shows branch critical 3C size plus each outgoing 3C segment.
- Cable schedule rows now expose segment role, circuit index, length basis,
  total path VD, load-end voltage, fault current, and critical-segment status.
- Cable schedule export includes the same segment columns.
- Result export includes a dedicated `Cold Cable 3C Segments` sheet.
- Calculation manual updated.
- Targeted `ResultAndBoqViewTests` and `ColdCableFoundationTests`: 103 tests passed.
- Full SQLite-mode `eht` suite: 281 tests passed.

### SLD-R1 - Topology Control Regression Fix

Status: complete

- [x] Investigate combine, split, downstream JB, and attach/move failures as a
      shared browser-control regression.
- [x] Confirm server-side topology workflows still pass for all four operations.
- [x] Harden `static/js/sld_workspace.js` render-state lifecycle so controls do
      not silently no-op when the SLD shell exists without active `__sldState`.
- [x] Add workspace render-contract coverage for all topology preview/apply URLs.

Checkpoint result, 2026-06-07:

- Root cause: browser-side SLD workspace state could become unavailable while
  the shell remained present, and topology handlers returned early because the
  render guard was never released after load/error paths.
- Follow-up production review fixes added `try/finally` render-guard release,
  a top-level `renderSldGraph` exception handler, and a render watchdog so
  runtime exceptions cannot leave topology controls permanently locked.
- Deeper root cause found on 2026-06-07: after cold-cable engineering, SLD
  rendering added explicit Cable4C/Cable3C nodes and more schematic SVG
  path/text drawing. The browser still relied on implicit hit testing of
  transparent component bodies, so user clicks could fail before any topology
  preview/apply request was made. Component bodies now declare explicit
  pointer hit targets.
- P1-specific root cause found on 2026-06-07: P1 had a stale active topology
  edit containing 96 historical operation records. The first saved
  `combine_feeders` operation referenced MCB component IDs that no longer exist
  in the current generated SLD, so replay failed at operation #1. New edits
  previously inherited that stale chain, so they applied successfully in the
  database but rendered as generated/stale again. Apply workflows now inherit
  active operation records only when that chain replays successfully against
  the current generated baseline.
- Cold-cable metadata also made topology fingerprints too sensitive. The SLD
  baseline fingerprint now ignores volatile node metadata such as cold-cable
  sizing status and voltage-drop evidence, and tracks graph structure instead.
- Browser-cache risk was also addressed by versioning the `sld_workspace.js`
  script URL in `base.html` as `sld-r3-hit-targets`; without this, Chrome could
  continue running old SLD interaction code after the file was patched.
- PostgreSQL-backed SLD regression batch: 32 tests passed, including
  `SldWorkspaceJavaScriptTests`, the versioned-script shell assertion, the SLD
  workspace render contract, topology fingerprint coverage, stale-chain repair,
  and all `SldTopologyWorkflowTests`.
- `eht.browser_tests` now contains an opt-in Playwright SLD browser smoke test
  that loads `/base/`, opens the SLD tab, waits for live `__sldState`, and
  toggles Combine, Split, Add JB, and Attach modes. It also selects real
  rendered SLD cells, verifies preview readiness, applies each topology edit on
  a fresh project, waits for re-render, and asserts an applied topology record.
- Local venv Playwright browser smoke passed:
  `venv/bin/python manage.py test eht.browser_tests -v 2 --noinput` ran 3 tests
  in 11.943s against PostgreSQL test DB `eht_local_test`.
- Real P1 dry run passed inside rolled-back transactions: Combine, Split, Add
  downstream JB, and Attach each returned `ok=True`; each new edit had one clean
  operation and `baseline_changed=False` / no review-required stale flag. The
  live P1 active edit remained unchanged after rollback.
- SLD hardening pass on 2026-06-07 added a single safe frontend render gateway
  for pager/search render paths, centralized external detail label geometry,
  disabled topology mutations in filtered/focused SLD views while preserving
  cable length and tracer overrides, and added backend filtered-view rejection.
- Backend topology apply now locks the project row, validates operation records
  and graph invariants before persisting, records stale-chain inheritance drops,
  and compacts very long operation chains fail-closed: the saved edited payload
  remains active while the generated baseline is unchanged, but a later baseline
  change requires review instead of unsafe replay.
- Combine-feeder hardening now preserves combined-current/recommended-breaker
  metadata and review warnings as the foundation for the next feature: automatic
  cold-cable re-sizing after combine, with the new combined trunk length
  defaulting to the highest selected feeder length and requiring user review.
- SLD hardening verification: source/pycompile/static checks passed; focused
  PostgreSQL SLD regression suite passed 38 tests through the programmatic
  existing-PostgreSQL runner. The normal `manage.py test ...` command still
  fails in Django test-command setup with `psycopg.OperationalError: connection
  is bad` even though direct Django connections and programmatic runner setup
  connect to `eht_local_test`; keep this as a test-runner follow-up.
- `node --check static/js/sld_workspace.js`: passed.
- `venv/bin/python manage.py check`: passed.
- `git diff --check`: passed.

### CC-P3 - 3PH JB Phase-Balancing Visibility

Status: complete

- [x] Define phase-slot semantics for 3PH JB outgoing circuits.
- [x] Avoid a schema migration by storing inferred phase evidence in existing
      per-segment `ColdCableResult.cable_3c_segments` JSON.
- [x] Store/display inferred phase position using L1/L2/L3 round-robin by
      outgoing circuit index.
- [x] Summarize phase currents and imbalance in the result tab and result export.
- [x] Keep this as visibility/review first, not automatic topology optimization.

Checkpoint result, 2026-06-07:

- Per-outgoing 3C segment JSON now includes `phase_slot`, `phase_label`, and
  `phase_basis`.
- SLD cold-cable node metadata carries the same phase label for Cable3C nodes.
- Result tab shows L1/L2/L3 current totals and phase-current imbalance for
  3PH JB branches.
- Result export appends phase-balance summary columns to `Cold Cable Sizing`
  and phase evidence columns to `Cold Cable 3C Segments`.
- Targeted PostgreSQL-backed tests: 4 tests passed using existing database
  `eht_local_test`.
- `venv/bin/python manage.py check`: passed.
- `node --check static/js/sld_workspace.js`: passed.
- `git diff --check`: passed.

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
