# Current Phase Tracker

Last updated: 2026-06-12

## Active Phase

Phase A: production hardening for the current SR/MI + cold cable + SLD path.

## Current State

- Phase A work through `CC-P5` is committed (HEAD `dc8c741`). Current dirty
  work includes `TEST-P1`, `SLD-P2`, `SLD-P1`, project-management
  documentation updates, and Claude's vendor-validation notes.
- Latest full SQLite test status (verified 2026-06-12 with `USE_POSTGRES=false`):
  307 tests passed. SQLite quick testing is restored.
- Latest full PostgreSQL test status (verified 2026-06-12 against
  `eht_local_test` via the programmatic runner): 306 tests passed.
- `eht_local` catalogue restoration after the CC-P5 accidental flush completed
  2026-06-11 — see `DB-R1`.
- Database Safety Protocol is now mandatory for all database-modifying
  commands — see `CODEX_MEMORY.md`.
- Latest quick health check: `venv/bin/python manage.py check` passed on
  2026-06-12.

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
- Result export included a dedicated per-segment sheet; renamed by `CC-P5` to
  `Cold Cable Branch Segments`.
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
- Housekeeping follow-up removed local debug/dropdown projects
  `p-debug-sld`, `p-debug-sld-api`, `p-hard`, and empty orphan `p2`; local
  project selectors should now show only `default_project` and `p1`. Ignored
  Python cache directories were cleaned. Tracked SLD review docs and browser
  regression tests are retained as intentional guard rails.
- Admin audit visibility added for `SLDTopologyEdit`: Django admin now exposes
  read-only topology edit history, operation count, compaction status,
  chain-audit metadata, validation summary, current-baseline comparison, and a
  safe replay diagnostic without adding user-facing undo/restore controls.
- SLD topology history retention added on 2026-06-07: old superseded/reset rows
  can be compacted to audit-only payloads through admin selected-row action or
  the dry-run-by-default `compact_sld_topology_history` management command.
  Active `applied` and `needs_review` rows are protected from compaction and
  emergency deletion. Admin now shows payload size and payload-compaction
  status, and includes a guarded emergency delete action for non-active old
  history records only. Local live cleanup compacted 100 old rows and saved
  about 57.5 MB of JSON payload; a follow-up dry-run reported 0 remaining
  candidates under the keep-full 20 / keep-reset 10 policy.
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
  and phase evidence columns to the branch-segment evidence sheet.
- Targeted PostgreSQL-backed tests: 4 tests passed using existing database
  `eht_local_test`.
- `venv/bin/python manage.py check`: passed.
- `node --check static/js/sld_workspace.js`: passed.
- `git diff --check`: passed.

### CC-P4 - Panel/Load Summary

Status: complete

- [x] Aggregate MCB count, breaker sizes, load current, and connected load.
- [x] Group by panel/source where source identity exists; otherwise group under project main distribution.
- [x] Surface review-required/unsizeable cold-cable counts.
- [x] Add Result tab section and result-export sheet.
- [x] Correct branch-current aggregation so branch current is calculated from
      `per_circuit_operating_current_a x circuit_count` before using line-total
      fallback data.
- [x] Count shared MCB/breaker capacity once when one MCB feeds multiple
      downstream branches.
- [x] Add three-phase EHT DB fault rating project setting foundation for source
      impedance.

Checkpoint result, 2026-06-07:

- Result tab now includes **Panel / Load Summary** with source label, line count,
  MCB count, circuit count, load current, connected load, breaker distribution,
  cold-cable selected/review/unsizeable/not-sized counts, and load basis.
- Result Excel export now includes a `Panel Load Summary` sheet.
- This is branch-based review evidence only. It does not yet compare against an
  upstream panel main breaker, spare capacity, or bus phase totals.
- 2026-06-08 correction: the summary now treats branch current and shared-MCB
  count as separate concepts. Loads are summed per downstream branch; MCB count,
  breaker distribution, and breaker-capacity sum are deduplicated by MCB tag.
- 2026-06-08 foundation: `ProjectData.eht_db_fault_rating_ka` defaults to 15 kA
  as the three-phase EHT DB prospective short-circuit current and feeds
  `ProjectData.eht_db_source_impedance_ohm` for the L-PE fault-loop rebuild.
- `ResultAndBoqViewTests`: 66 tests passed through the programmatic
  existing-PostgreSQL runner after adapting the class to Claude's new
  login-required middleware.
- `eht.test_manual_guide`: 1 test passed after making the manual view test
  authenticate under Claude's new login-required middleware.
- `venv/bin/python manage.py check`: passed.
- `venv/bin/python -m py_compile eht/views.py eht/tests.py eht/test_manual_guide.py`: passed.
- `git diff --check`: passed.

### CC-P5 - Single-Phase Cold-Cable Rebuild

Status: complete

- [x] Delete stale ColdCableResult rows in migration.
- [x] Retire misleading 4C phase-to-phase fault result fields.
- [x] Add L-PE fault-loop fields and basis evidence.
- [x] Add ColdCableCatalogue PE conductor size and seed equal-core rows.
- [x] Rebuild sizing around FeederCable + BranchCable complete paths.
- [x] Deduplicate shared FeederCable material in cable schedule totals.
- [x] Update SLD/UI labels from 3PH/4C terminology to Feeder/Branch naming.
- [x] Add upgrade notice prompting cold-cable recalculation when branch rows
      exist without cold-cable results.
- [x] Update design guide active text and regression tests.

Checkpoint result, 2026-06-08:

- Migration `0036_single_phase_cold_cable_fault_loop` applied locally.
- Result export sheet renamed to `Cold Cable Branch Segments`.
- Verification report and design guide active text now show single-phase
  Feeder/Branch VD and L-PE loop basis.
- Follow-up review patch clarified three-phase PSCC wording, added
  `Z_source = 0.0` fallback review notes for invalid migrated project data, and
  added panel-summary tests for line-current fallback and multi-circuit branches.
- Follow-up verification: `ColdCableFoundationTests`, `ProjectDataFormTests`,
  `ProjectDataViewTests`, and `ResultAndBoqViewTests` passed 130 tests.
- Second review patch updated the stale SR parallel-run test to the shared-MCB
  model, added shared SR group metadata (`sr_parallel_run_count`,
  `sr_parallel_run_basis`, `sr_shared_mcb`) to generated branch tags, and added
  migration `0037_remove_legacy_3c_fault_fields`.
- Follow-up verification: `PowerDistributionCalculationTests`,
  `ColdCableFoundationTests`, `ResultAndBoqViewTests`, and
  `SldTopologyWorkflowTests` passed 147 tests.
- `ColdCableFoundationTests`: 39 tests passed.
- `ProjectDataFormTests`, `ProjectDataViewTests`, `ResultAndBoqViewTests`:
  88 tests passed.
- `SldTopologyWorkflowTests` and `SldWorkspaceJavaScriptTests`: 35 tests passed.
- SR reporting alignment export gate: 1 test passed.
- `venv/bin/python manage.py check`: passed.
- `venv/bin/python manage.py makemigrations --check --dry-run`: passed.
- `venv/bin/python -m py_compile` on touched Python modules: passed.
- `git diff --check`: passed.

### DB-R1 - Development Database Restoration

Status: complete

- [x] Restore SR + MI tracer library: 130 rows from backup table
      `eht_eleceht_vendor_backup_temp`.
- [x] Restore ASME B36 pipe sizes: 200 rows from `eht/tmp/elecEHT_ASMEB36.csv`.
- [x] Restore thermal conductivity: 5 rows from
      `eht/tmp/elecEHT_ThermalConductivity.csv`.
- [x] Confirm cold cable catalogue intact: 14 rows (migration-seeded).
- [x] Record vendor CSV divergence warning: `eht/tmp/elecEHT_Vendor.csv` must
      NOT be imported (178 unverified rows not in DB; 89 validated DB rows
      missing from the CSV).
- [x] Adopt mandatory Database Safety Protocol in `CODEX_MEMORY.md`.

Checkpoint result, 2026-06-11: restoration complete; KR still reviewing
whether the 178 unverified CSV rows (Constant Wattage Thermon/nVent = 91,
Krus-Zapad MI = 87) should be added to the catalogue.

### VDV-P1 - Vendor Data Validation (KR-instructed, Claude-executed)

Status: MI complete; SR validation complete (report only — corrections pending KR)

- [x] Download official vendor documents (Thermon TEP0020-0714, nVent
      DOC2210-HAX-EN-1704 + H56870-1810, Chromalox mod-mi G-25) and archive
      in `NOTES/vendor_validation/source_docs/`.
- [x] Validate all 72 seeded MI heater rows: only 5 fully correct; 3 real
      codes with wrong resistance; 64 nonexistent codes. Evidence:
      `NOTES/vendor_validation/MI_VENDOR_DATA_VALIDATION_2026-06-12.md`.
- [x] KR approvals 2026-06-12: revoke validation; reseed from official
      tables; nVent governed by EMEA DOC2210 (brazed-unit limits);
      no derived cold-lead data.
- [x] Backup + reseed executed against `eht_local`: 72 official heaters,
      177 cold-lead options, corrected family limits, all families
      `is_validated=False`.
- [x] 15 `SelectedMIHeater` snapshots orphaned (computed from fabricated
      data) — recalculation required.
- [ ] KR row-by-row review of reseeded data, then `is_validated=True` via
      Django admin (R7 gate / R-011).
- [x] SR catalogue validation against vendor data (report only), 2026-06-12:
      25 of 58 SR rows verified good (Thermon HTSX/VSX, Chromalox SRM/E,
      SST BTC/BTX); 8 nVent rows fabricated (impossible power classes,
      exposure 204 vs real 85 C); 9 rows attributed to families that do not
      exist at Eltherm/Heat Trace/Pentair; 16 Krus-Zapad rows unverifiable
      online (KR to supply source). Evidence:
      `NOTES/vendor_validation/SR_VENDOR_DATA_VALIDATION_2026-06-12.md`.
- [ ] KR decisions on SR corrective plan (nVent replacement, unsourced-vendor
      rows, Krus-Zapad source, SR `is_validated` gate recommendation).

### TEST-P1 - Test Baseline Repair

Status: complete

- [x] Add `self.client.force_login(self.user)` to `SldLayoutTests.setUp`
      (same pattern as `ResultAndBoqViewTests`) — fixes 7 failures.
- [x] Update `'4C x 2.5 mm2'` to `'3C x 2.5 mm2'` in
      `SldPayloadTests.test_build_project_sld_payload_adds_cold_cable_metadata_to_cable_nodes`
      — fixes 1 failure.
- [x] Fix migration `0037` SQLite incompatibility by replacing
      PostgreSQL-specific `DROP COLUMN IF EXISTS` SQL with a schema-editor
      column drop guarded by introspection.
- [x] Confirm full test baseline >= 305 green via the PostgreSQL programmatic
      runner.

Checkpoint result, 2026-06-12:

- `USE_POSTGRES=false venv/bin/python manage.py test eht -v 2 --noinput`:
  305 tests passed. Migration `0037` applies cleanly on SQLite.
- PostgreSQL programmatic runner against `eht_local_test`: 305 tests passed,
  `Failures: 0`.
- Targeted `SldLayoutTests` and `SldPayloadTests`: 21 tests passed.
- `venv/bin/python manage.py check`: passed.
- `USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run`:
  passed, no changes detected.
- `node --check static/js/sld_workspace.js`: passed.
- `git diff --check`: passed.

### SLD-P2 - Combined-Circuit Cold-Cable Resizing and Impact Summary

Status: complete

- [x] When circuits are combined, trigger cold-cable re-sizing of the new
      combined FeederCable from combined current, using the CC-P5 single-phase
      FeederCable/BranchCable engine.
- [x] Warn that prior separate feeder cable lengths are invalid; default the
      combined length to the max of the combined cables' lengths; require
      user review. (Foundation metadata `combined_current` and
      `recommended_breaker_rating` is already stored in the combine preview.)
- [x] Show affected MCBs and breaker rating changes.
- [x] Show cable length/size/mass deltas where known.
- [x] Show affected BOQ/schedule rows.
- [x] Persist impact evidence.

Checkpoint result, 2026-06-12:

- Combined feeder apply now builds a graph-level cold-cable impact summary for
  the manual FeederCable trunk. The impact stores calculated size, status,
  VD/fault evidence, conductor mass, length deltas, affected lines, and affected
  cable schedule rows in `SLDTopologyEdit.edit_payload`.
- If no combined trunk length is entered, the preview defaults to the maximum
  selected feeder cable length and marks the length basis for review.
- Applied combined-trunk metadata is kept on the manual `Cable4C` node and is
  protected from stale persisted branch cold-cable results.
- Targeted regression:
  `USE_POSTGRES=false venv/bin/python manage.py test eht.tests.SldTopologyWorkflowTests -v 2 --noinput`:
  32 tests passed.
- Broader SLD/payload/result/JS regression:
  `USE_POSTGRES=false venv/bin/python manage.py test eht.tests.SldPayloadTests eht.tests.ResultAndBoqViewTests eht.tests.SldWorkspaceJavaScriptTests -v 2 --noinput`:
  87 tests passed.
- Full SQLite suite:
  `USE_POSTGRES=false venv/bin/python manage.py test eht -v 2 --noinput`:
  306 tests passed.
- Full PostgreSQL-backed suite against `eht_local_test` through the
  programmatic runner: 306 tests passed, `Failures: 0`.

### SLD-P1 - Visual Review Badges

Status: complete

- [x] Badge missing cable length.
- [x] Badge cold cable review-required or unsizeable.
- [x] Badge manual override.
- [x] Badge stale/review-required topology.
- [x] Add tests for metadata and basic rendering strings.

Checkpoint result, 2026-06-12:

- SLD workspace now derives compact visual review badges from existing payload
  metadata for missing cable length, cold-cable review/unsizeable states,
  manual cable/tracer overrides, and manual topology review/stale states.
- Badges move with their owning component and are refreshed after layout
  changes.
- Focused JS/source coverage:
  `USE_POSTGRES=false venv/bin/python manage.py test eht.tests.SldWorkspaceJavaScriptTests -v 2 --noinput`:
  5 tests passed.
- Broader SLD/payload/result/topology regression:
  `USE_POSTGRES=false venv/bin/python manage.py test eht.tests.SldPayloadTests eht.tests.ResultAndBoqViewTests eht.tests.SldTopologyWorkflowTests eht.tests.SldWorkspaceJavaScriptTests -v 2 --noinput`:
  120 tests passed.
- Full SQLite suite:
  `USE_POSTGRES=false venv/bin/python manage.py test eht -v 2 --noinput`:
  307 tests passed.

### SCH-P1 - Procurement-Grade Cable Schedule

Status: pending (next pass)

- [ ] Add route/reference fields.
- [ ] Add drum tag / cable lot fields.
- [ ] Add installation area/basis fields.
- [ ] Add revision/review status.
- [ ] Improve Excel export for procurement review.

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
