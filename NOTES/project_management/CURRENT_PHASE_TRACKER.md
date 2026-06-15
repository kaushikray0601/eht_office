# Current Phase Tracker

Last updated: 2026-06-15

## Active Phase

Phase A: production hardening for the current SR/MI + cold cable + SLD path.

## Current State

- Phase A code through `CAT-P1 / SEC-P1a`, `EHT-P1`, `APP-P1`, `SCH-P2`,
  `SEC-P1b` implemented controls, and `UX-P1` is implemented in the current
  worktree. Remaining open items are mostly catalogue/vendor-validation
  decisions, dependency/admin exposure hardening, manual visual checks, and
  final release acceptance.
- Latest full SQLite test status (verified 2026-06-15 with `USE_POSTGRES=false`):
  360 tests passed. SQLite quick testing remains the default fast path.
- Latest full PostgreSQL test status (verified independently by Claude on
  2026-06-15 against local PostgreSQL): 320 tests passed. Codex may still use
  SQLite fallback when its sandbox hits the known PostgreSQL test-runner
  reconnect issue.
- `eht_local` catalogue restoration after the CC-P5 accidental flush completed
  2026-06-11 — see `DB-R1`.
- Database Safety Protocol is now mandatory for all database-modifying
  commands — see `CODEX_MEMORY.md`.
- Latest quick health check: `venv/bin/python manage.py check` passed on
  2026-06-15.
- Latest safety/compliance audit follow-up: `CAT-P1 / SEC-P1a` on 2026-06-14
  guarded the dangerous legacy import path, added SR/MI catalogue-isolation
  regression coverage, fixed login open-redirect handling, and hardened
  error-file downloads. The remaining catalogue items are KR/vendor-validation
  decisions, not code changes to make without approval.

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

### AUD-P1 - Safety, Compliance, and Side-Effect Audit

Status: complete

- [x] Review recent work from DB restoration through `TEST-P1`, `SLD-P2`, and
      `SLD-P1` for hanging/orphaned/stale side effects.
- [x] Run read-only `eht_local` catalogue/reference count checks.
- [x] Check migration state and quick Django health.
- [x] Run Django deploy security check for release-readiness warnings.
- [x] Search for destructive commands, raw SQL, unsafe HTML insertion, and
      import/catalgoue mutation paths.
- [x] Re-sequence next passes only where needed for MVP convergence.

Checkpoint result, 2026-06-13:

- Worktree was clean at audit start.
- `venv/bin/python manage.py check`: passed.
- `venv/bin/python manage.py check --deploy`: returned expected deployment
  warnings for HSTS, SSL redirect, secure session/CSRF cookies, and production
  `SECRET_KEY` handling. These are release-environment settings, not current
  calculation defects.
- `venv/bin/python manage.py showmigrations eht`: all migrations through
  `0037_remove_legacy_3c_fault_fields` applied.
- Read-only live `eht_local` counts:
  - `ElecEHT_Vendor`: 130 rows total = 58 SR rows + 72 legacy MI rows.
  - ASME B36 pipe rows: 200.
  - Thermal conductivity rows: 5.
  - Cold cable catalogue rows: 14, all validated Method E/Cu/XLPE rows.
  - Normalized MI catalogue: 3 families, 72 heaters, 177 cold-lead options.
  - Current project data: 3 projects, all using Method E/Cu/XLPE; 22 input
    lines; 13 cold-cable results.
- Legacy MI rows remain in `ElecEHT_Vendor` as `Tracer_Family='MI'`. The
  current SR selector filters SR candidates by family (`SR`/self-regulating),
  so these rows are not an active SR selection path, but they remain confusing
  historical data and must not be reimported from CSV.
- `SelectedMIHeater` currently has 6 rejected snapshots with no heater
  references; no active selected MI orphan was found in the read-only audit.
- Normalized MI validation state in the live DB is inconsistent with the
  vendor-validation note/tracker: THR/MIQ and CHR/MI-825B are currently
  `is_validated=True`; nVent/XMI-A62 is `False`. No data was changed during
  the audit. This must be resolved with KR/Claude before more MI-sensitive
  calculations are trusted.
- `import_data_from_file` used to blindly import `eht/tmp/elecEHT_Vendor.csv`,
  which project notes say would corrupt the restored vendor catalogue. This was
  guarded in `CAT-P1 / SEC-P1a`.
- Ignored local root database artifacts exist: `db.sqlite3` and
  `db.sqlite3.bak`. They are not the active PostgreSQL database and are not
  tracked, but should be treated as local artifacts during release cleanup.

### CAT-P1 - Catalogue Gate and Import Safety

Status: code safety complete; KR catalogue decisions pending

- [ ] Resolve the live MI `is_validated` discrepancy with KR/Claude. If the
      current THR/CHR validation was not intentional R7 approval, explicitly
      close the gate again through an approved data-change path.
- [x] Guard or retire `import_data_from_file` so the divergent vendor CSV
      cannot be imported accidentally.
- [x] Add explicit safety confirmation to the legacy catalogue import command.
- [ ] Review any other catalogue mutation commands that can delete or clear
      catalogue/reference rows before production catalogue maintenance.
- [x] Add/confirm tests that SR selection ignores legacy MI rows in
      `ElecEHT_Vendor`.
- [ ] Decide whether Phase A needs an SR validation gate, or at minimum a
      vendor/readiness warning for unverified SR blocks, before production use.
- [x] Record the command policy in PM docs.
- [ ] Record the final approved catalogue state after KR/Claude vendor review.

Checkpoint result, 2026-06-14:

- `import_data_from_file` is now blocked by default. It requires both
  `--execute` and the exact confirmation text
  `"I understand this imports legacy catalogue CSV data"` before importing any
  legacy CSV data.
- Added regression coverage proving the command does not alter vendor,
  thermal-conductivity, or pipe catalogue counts without explicit confirmation.
- Strengthened SR selection regression coverage with an explicit legacy
  `Tracer_Family='MI'` row in `ElecEHT_Vendor`-style data; SR selection ignores
  it.
- Fixed Claude security finding D-2: `my_login` now validates `next` with
  `url_has_allowed_host_and_scheme` and falls back to `base` for unsafe
  external redirects.
- Fixed Claude security finding D-4: `download_error_file` rejects path
  separators and resolves file paths inside the configured error-file
  directory before serving.
- Added Codex response/disposition section to
  `NOTES/audit/sch-p1-requirements-2026-06-13.md`.
- Focused SQLite regression:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht.tests.CatalogueAndSecurityHardeningTests eht.tests.TracerSelectionTests.test_get_tracer_options_filters_catalogue_temperature_limits_and_family -v 2 --noinput`:
  5 tests passed.

### SCH-P1 - Procurement-Grade Cable Schedule

Status: complete

- [x] Add route/reference fields.
- [x] Add drum tag / cable lot fields.
- [x] Add installation area/basis fields.
- [x] Add revision/review status.
- [x] Improve Excel export for procurement review.

Checkpoint result, 2026-06-13:

- `CableScheduleOverride` now carries optional procurement/review annotations:
  route reference, installation area/basis, drum tag, cable lot, schedule
  revision, review status, checked-by/date.
- Existing SLD cable override save paths preserve those annotations while
  continuing to update manual length/size/remarks.
- Cable schedule rows now surface generated route references and project cable
  installation basis, plus any manual procurement annotations.
- Cable schedule table exposes procurement fields through optional columns and
  shows review status/revision in the active schedule.
- Cable schedule Excel export includes route reference, installation area,
  installation basis, drum tag, cable lot, review status, checked-by/date, and
  revision fields.
- Admin now provides a focused `CableScheduleOverride` maintenance surface for
  procurement annotations without building a larger cable-management workflow.
- New migration: `0038_cablescheduleoverride_cable_lot_and_more`.
- Live PostgreSQL dev database `eht_local` was updated to migration `0038` on
  2026-06-13 after the running app exposed the pending-schema mismatch during
  line-list upload.
- Targeted SQLite `ResultAndBoqViewTests`: 71 tests passed.
- Full SQLite suite: 309 tests passed.
- Claude's SCH requirements review at
  `NOTES/audit/sch-p1-requirements-2026-06-13.md` recommends a fuller
  procurement snapshot model with Draft/Issued revision semantics and says the
  route/drum/lot fields are later pre-construction fields. KR accepted the
  current lighter SCH-P1 as complete for convergence. The fuller snapshot model
  is deferred, not deleted from consideration.

### QA-P1a - SR Power-Coefficient Safety Guard

Status: complete

- [x] Review Claude's SCH-P1 blocker about null SR A/B/C coefficients.
- [x] Confirm the active code path is `eht.calculations.power_distribution`,
      not the legacy `eht/calculation.py` implementation.
- [x] Add an explicit SR A/B/C coefficient guard before power-parameter
      calculation.
- [x] Ensure orchestration does not publish an SR selected tracer when
      downstream power-parameter calculation fails.
- [x] Add focused regression tests.

Checkpoint result, 2026-06-14:

- `compute_power_params` now rejects missing or non-numeric SR power
  coefficients explicitly and logs the affected coefficient names.
- `orchestrate_calculations` now converts a downstream SR power-parameter
  failure into a structured `SR_POWER_PARAMETER_CALCULATION_FAILED` rejection
  and does not append selected tracer, power distribution, BOQ, or tracer power
  rows for that line.
- PostgreSQL-first test attempt:
  `venv/bin/python manage.py test eht.tests.ResultAndBoqViewTests.test_cable_schedule_export_returns_schedule_sheet -v 2 --noinput`
  still failed during Django test-runner database setup with
  `psycopg.OperationalError: connection is bad` before the test executed.
- Direct Django PostgreSQL connection check passed against live dev DB
  `eht_local`; `connection.vendor == postgresql` and `connection.is_usable()`
  returned `True`.
- Pure targeted calculation tests passed:
  `venv/bin/python manage.py test eht.tests.PowerDistributionCalculationTests eht.tests.OrchestrationTests -v 2 --noinput`:
  11 tests passed.
- SQLite fallback DB-backed schedule smoke passed:
  `USE_POSTGRES=false venv/bin/python manage.py test eht.tests.ResultAndBoqViewTests.test_cable_schedule_export_returns_schedule_sheet -v 2 --noinput`:
  1 test passed.
- Full SQLite suite:
  `USE_POSTGRES=false venv/bin/python manage.py test eht -v 2 --noinput`:
  311 tests passed.
- `venv/bin/python manage.py check`: passed.
- `USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run`: passed.
- `git diff --check`: passed.

### QA-P1 - Worked Examples and Verification Alignment

Status: complete

- [x] Add SR worked example.
- [x] Add MI worked example.
- [x] Add direct 1PH cold-cable worked example.
- [x] Add 3PH JB cold-cable optimization worked example.
- [x] Confirm report formulas are aligned with code.
- [x] Verify Sections B-E formula text in the verification report against
      `cold_cable.py`, `pipeline.py`, and `calculation.py` (covers Risk R-006).

Checkpoint result, 2026-06-14:

- Added `NOTES/verification/QA_P1_WORKED_EXAMPLES.md` with worked examples for
  SR heat loss/selection, MI fallback evidence, direct single-phase cold-cable
  voltage-drop/fault-loop sizing, and shared FeederCable / BranchCable
  optimization.
- Corrected stale SR parallel-run wording in the verification report,
  calculation manual, and Engineering Hub design guide. Active basis is now
  stated consistently: SR parallel straight runs share one 2-pole MCB per run
  group; MI multi-sets remain independently protected.
- Added regression coverage that pins verification-report Sections B-E formula
  text to the active source basis and prevents the old SR independent-branch
  wording from returning.
- Added manual/design-guide regression coverage for the shared-MCB SR parallel
  basis and worked-example coverage.
- PostgreSQL-first targeted test attempt still failed during Django test-runner
  database setup with the known `psycopg.OperationalError: connection is bad`
  before tests executed. Direct Django PostgreSQL connection to live `eht_local`
  passed immediately after.
- Targeted SQLite fallback tests passed: 4 tests.
- Full SQLite suite:
  `USE_POSTGRES=false venv/bin/python manage.py test eht -v 2 --noinput`:
  314 tests passed.
- `venv/bin/python manage.py check`: passed.
- `USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run`:
  passed.
- `node --check static/js/sld_workspace.js`: passed.
- `git diff --check`: passed.

### RELEASE-P1 - Production Readiness Sweep

Status: code sweep complete; manual release sign-off pending

- [x] Full test suite green.
- [x] Migrations applied and checked.
- [ ] Manual demo project verified.
- [x] Known limitations visible in UI/report/manual.
- [ ] Release checklist complete.

Checkpoint result, 2026-06-14:

- Production settings hardening added in `ELECSENSE/settings.py`:
  - Removed the hardcoded `ALLOWED_HOSTS = ["*"]` override.
  - Added robust comma/JSON-ish parsing for `ALLOWED_HOSTS` and
    `CSRF_TRUSTED_ORIGINS`.
  - Added environment-driven HTTPS redirect, HSTS, secure session cookie, and
    secure CSRF cookie settings. Defaults remain local-development friendly;
    production mode can satisfy Django deploy checks through explicit
    environment variables.
  - Changed the default PostgreSQL host from the old hardcoded public IP to
    `127.0.0.1`; `.env` or process environment remains the source of truth for
    actual deployment/database hosts.
- Production-shaped deploy check passed with a non-development `SECRET_KEY`,
  explicit host/origin, and `SECURE_HSTS_PRELOAD=true`:
  `DEBUG=false ... venv/bin/python manage.py check --deploy`.
  HSTS preload remains a deployment decision and should only be enabled for a
  domain that is permanently HTTPS.
- PostgreSQL migration check passed against live `eht_local` after local DB
  access was allowed:
  `DEBUG=true venv/bin/python manage.py migrate --check`.
- Direct Django PostgreSQL connection check passed against `eht_local`.
- SQLite migration dry run passed:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py makemigrations --check --dry-run`.
- Acceptance smoke slice passed 14 tests covering SLD layout save/reset,
  SLD PDF export, result export, BOQ export, cable schedule export, manual
  cable override save/reset, verification report render, and combined-feeder
  schedule/cold-cable impact.
- Full SQLite suite:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  318 tests passed.
- `venv/bin/python manage.py check`: passed.
- `node --check static/js/sld_workspace.js`: passed.
- `git diff --check`: passed.
- Remaining release sign-off items are manual/visual rather than code blockers:
  demo project walkthrough, cold-cable label overlap inspection, large-project
  browsing/search feel, and terminal-voltage manual cross-check.

### SCH-P2 - Cable Schedule UX and Internal Lifecycle

Status: complete

- [x] Hide route reference, drum tag, cable lot, installation area, and other
      later-stage procurement columns by default in the cable schedule table.
- [x] Add/export visible-column behavior for the working cable schedule export,
      with clear wording so users understand whether they are exporting visible
      columns or a full audit schedule.
- [x] Keep hot-engineering values such as maintain temperature, minimum ambient,
      trace type, breaker size, and W/m basis out of the cable schedule; those
      belong on result/engineering pages unless KR later reopens the schedule
      column policy.
- [x] Add internal generation/modification tracking for cable schedule records:
      generated timestamp, modified timestamp, and user where available.
- [x] Add internal cable revision tracking keyed by autogenerated cable tag.
      Increment the internal revision only when the cable's schedule-relevant
      state changes, such as size change, added cable, or deleted/retired cable.
- [x] Track cable deletion/retirement due to recalculation or SLD topology
      change with date/time/user evidence rather than silently losing history.
- [x] Add a schedule note/evidence column or legend explaining why shared
      feeder/cable rows can appear per circuit while summary quantities are
      deduplicated.

Checkpoint result, 2026-06-15:

- Cable schedule table keeps later-stage procurement/checking columns hidden by
  default while preserving the Bootstrap column chooser for advanced users.
- Default `Download Visible` export now follows the current visible table
  column selection passed from the UI; without a UI column list it exports the
  default visible schedule columns only.
- Added explicit `Full Audit` export for hidden procurement/checking columns
  and detailed cold-cable evidence such as segment role, VD, fault status,
  length basis, and manual-size review notes.
- Focused schedule export/view tests passed: 8 tests.
- Full SQLite-mode `eht` suite passed: 351 tests.
- `venv/bin/python manage.py check`: passed.
- `env USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run`: passed.
- `git diff --check`: passed.

Checkpoint result, 2026-06-15 internal lifecycle pass:

- Added migration `0042_cableschedulerecord` with a generated
  `CableScheduleRecord` audit table keyed by project + autogenerated cable tag.
  This is a derived audit table only; it does not drive calculation, SLD, BOQ,
  or cold-cable sizing behavior.
- Cable schedule view/export now sync active schedule rows into the audit table
  when the schedule is generated for display/export.
- Internal revision starts at `0`, does not churn on unchanged schedule views,
  increments only when schedule-relevant state changes, and increments/marks
  retired when a previously active cable tag disappears from the generated
  schedule.
- Full audit export now includes hidden generated-at, modified-at, and lifecycle
  status columns. The visible schedule keeps a compact default view.
- Admin exposes `CableScheduleRecord` as read-only generated audit evidence.
- Added visible schedule note explaining that shared feeder rows may appear
  against multiple circuits for traceability while summary cable quantities are
  deduplicated.
- Focused lifecycle/schedule tests passed: 4 tests.
- `ResultAndBoqViewTests`: 81 tests passed.
- Full SQLite-mode `eht` suite passed: 355 tests.
- `venv/bin/python manage.py check`: passed.
- `env USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run`: passed.
- `git diff --check`: passed.
- PostgreSQL migrations `0042_cableschedulerecord` and
  `0043_processlinecalculation_calculated_at` were applied to `eht_local` on
  2026-06-15. `migrate --check`, `manage.py check`, and read-only smoke
  queries passed afterward.

### EHT-P1 - Engineering Rule Corrections and Warnings

Status: complete

- [x] Correct upload line-list temperature validation to enforce:
      `Maint_T <= Oper_T <= Design_T`.
- [x] Add model-level temperature-order validation so admin/API paths cannot
      bypass the upload sanitizer.
- [x] Add starting-voltage-drop warning for cold cable using startup/inrush
      current basis where available. Default warning threshold: 10% of rated
      voltage.
- [x] Add an advanced project setting for startup voltage-drop warning threshold
      while keeping 10% as the default.
- [x] Allow MI fallback when SR is within temperature range but no validated SR
      cable from the selected vendor can meet heat duty, if an MI solution is
      available. The result must clearly state that MI was selected because no
      SR heat-duty match was available, not because SR temperature limits were
      exceeded.
- [x] Add assumptions/limitations text for source impedance approximation and
      accessory heat-loss empirical adders.
- [x] Record advanced heat-loss methods and three-phase heat-tracing design in
      the future/coming-soon engineering notes.

Checkpoint note, 2026-06-14:

- Claude independently verified the temperature ordering issue and KR confirmed
  the corrected rule. `eht/sanatize_input.py` now enforces
  `Maint_T <= Oper_T <= Design_T` for Excel uploads.
- Added focused regression coverage:
  `InputSanitizerValidationTests.test_sanitize_file_accepts_maintain_operating_design_temperature_order`
  and
  `InputSanitizerValidationTests.test_sanitize_file_rejects_operating_temperature_below_maintain_temperature`.
  Focused SQLite test result: 2 tests passed.
- Full SQLite suite after the initial temperature upload fix: 320 tests passed.
- Added boundary coverage for `Maint_T == Oper_T`.
- Implemented B-6 first in two steps: SR no-selection now always carries a
  persisted diagnostic, and `NO_SPIRAL_FACTOR_MATCH` can trigger automatic MI
  fallback with selection mode `automatic_heat_duty_fallback`.
- If SR heat-duty fallback probes MI and MI also fails, the result page shows
  both the SR Selection Diagnostics and the MI Selection Records. Focused
  SQLite fallback tests for this path passed: 5 tests.
- Added `HeatTracingInput.clean()` validation for
  `Maint_T <= Oper_T <= Design_T`, with model-level tests covering the
  equality boundary and both invalid orderings.
- Focused EHT-P1 SQLite slice after model validation and B-6 fallback changes:
  11 tests passed.
- Full SQLite suite after EHT-P1 B-1/B-6 changes:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  327 tests passed.
- Implemented B-4 startup-current cold-cable voltage-drop warning:
  `ProjectData.startup_vd_warning_threshold_pct` defaults to 10%, selected
  cold-cable paths store startup VD evidence, and over-threshold startup VD
  marks the cold-cable result review-required without automatic upsizing.
- Focused SQLite tests for startup VD warning, project form guidance, cold-cable
  sizing input, and SLD JavaScript passed: 10 tests.
- Full SQLite suite after EHT-P1 B-4 startup VD warning:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  329 tests passed.
- EHT-P1 close-out added visible startup-VD review guidance on the result page,
  expanded the stored review note to tell users what to check, documented the
  source-impedance approximation and empirical accessory-adders limitation, and
  recorded advanced heat-loss / three-phase design as future engineering scope.
- Full SQLite suite after EHT-P1 close-out:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  330 tests passed.
- Claude independently confirmed PostgreSQL 320/320 green. The older C-8 item
  is closed as an environment/test-runner reconnect issue in Codex, not an open
  product test failure. Optional retry logic in the custom PostgreSQL test
  runner can be considered later.

### APP-P1 - Data Integrity, Cleanup, and Project Lifecycle

Status: code complete; dashboard delivered by Claude; manual release sign-off pending

- [x] Remove dead legacy calculation stub code from production package after
      confirming no imports remain. Keep any needed historical context in
      `NOTES/archive/` or git history, not shipped Python modules.
- [x] Remove obsolete commented-out model blocks after confirming no active
      migration/code dependency.
- [x] Plan and implement `HeatTracingInput.proj_id` referential integrity with
      `ProjectData` and project-owned cascade deletion only. No catalogue,
      vendor, reference, or cross-project data may be touched.
- [x] Disable or remove self-registration links/routes; user creation remains
      admin-managed.
- [x] Replace the shared upload validation error workbook with bounded rotating
      error files and an admin-configurable retention policy.
- [x] On project setup save or line-list upload, show a confirmation when
      existing calculated data would be cleared. If confirmed, clear only that
      project's calculated result/BOQ/SLD/cable-schedule data and require
      recalculation; if not confirmed, cancel the change.
- [x] Add a project dashboard showing project calculation state, last run,
      stale/ready status, and high-level project counts.

Checkpoint note, 2026-06-15:

- Disabled the self-registration endpoint explicitly: `/register/` now returns
  HTTP 410 with an admin-contact message instead of entering a login redirect
  loop. User creation remains admin-managed.
- Upload validation error workbooks now use bounded rotating names
  `error_file_01.xlsx` ... `error_file_N.xlsx` under
  `file_storage/error_file/`, avoiding the previous shared `error_file.xlsx`
  overwrite race while preventing unbounded disk growth. The default retention
  policy is 10 files at 5 MB each; migration `0040_errorfileretentionpolicy`
  adds admin configurability and was applied to PostgreSQL on 2026-06-15.
  No policy row was created automatically; the runtime fallback remains
  10 files at 5 MB until an admin-configured row is added.
- Upload sanitizer now rejects path-like upload names, non-`.xlsx` extensions,
  wrong XLSX MIME types, and disguised non-XLSX content using the ZIP/XLSX
  signature check.
- Focused SQLite tests passed for input sanitizer validation and
  catalogue/security hardening: 12 tests.
- Full SQLite suite after APP-P1 C-4/C-5:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  335 tests passed.
- Project setup save and replacement line-list upload now require explicit
  confirmation before clearing an existing project workspace. The guarded clear
  path resets only the selected project's uploaded inputs, calculated outputs,
  BOQ rows, cold-cable results, SLD layout/topology edits, cable schedule
  overrides, and tracer overrides; catalogue/vendor/reference data is not in
  the deletion path.
- Focused SQLite tests passed for workspace cleanup, project setup confirmation,
  and upload replacement confirmation: 21 tests.
- Full SQLite suite after APP-P1 stale-workspace guard:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  338 tests passed.
- Legacy `eht/calculation.py` was removed from the shipped app after import
  scans confirmed the active path is `eht.pipeline` -> `eht.cal` ->
  `eht.calculations/*`. The obsolete triple-quoted `ElecEHT_CalculatedTable`
  / `ElecEHT_IO` reference block was removed from `eht/models.py`. No database
  migration was generated.
- Checks after dead-code cleanup:
  `venv/bin/python manage.py check` passed,
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py makemigrations --check --dry-run`
  reported no changes, and the full SQLite suite passed:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  348 tests passed.
- `HeatTracingInput.proj_id` now has database-level referential integrity to
  `ProjectData.proj_id` via migration `0041_heattracinginput_project_fk`.
  The physical column remains `proj_id`, preserving existing raw-ID code such
  as `line.proj_id` and `filter(proj_id='P1')`. The migration includes a
  fail-fast pre-check: if any line-list row points to a missing, blank, or
  overlength project ID, migration stops with a clear message and does not
  silently delete or remap data.
- Added regression coverage proving `ProjectData.delete()` cascades only that
  project's uploaded line-list and derived calculation rows, while another
  project and catalogue/reference rows remain intact. Test fixtures that
  created standalone line-list rows were corrected to create owning projects.
- Focused SQLite tests for FK/cascade and repaired fixtures passed:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht.test_mi_catalogue_structure eht.test_mi_selection eht.tests.HeatTracingInputModelValidationTests eht.tests.ProcessLineFetchTests eht.tests.ProjectWorkspaceCleanupTests -v 2 --noinput`:
  40 tests passed.
- Full SQLite suite after C-3:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  349 tests passed.
- Read-only PostgreSQL orphan check on 2026-06-15 found `invalid_count: 0`
  for current line-list project IDs (`p-fault-4c`, `sp`, `P1`). No rows were
  modified during the check.
- PostgreSQL migration `0041` was applied on 2026-06-15:
  `venv/bin/python manage.py migrate` completed with
  `Applying eht.0041_heattracinginput_project_fk... OK`.
  `showmigrations eht`, `migrate --check`, and `manage.py check` passed after
  application.

### SEC-P1b - Upload, Authentication, Admin, and Dependency Hardening

Status: implemented controls complete; dependency/admin exposure decisions remain before production release

- [x] Add upload hardening: file size limit, actual XLSX/ZIP magic-byte check,
      XLSX MIME check, upload-name traversal guard, bounded validation-error
      file retention, and tests for disguised uploads.
- [x] Wire existing `UserAttempt` or equivalent login attempt tracking so failed
      logins are counted, lockout behavior works, and error messages do not
      disclose whether a username exists.
- [x] Add rate limiting for login and other abuse-prone endpoints. Preferred
      first pass: use `django-ratelimit` or equivalent, with Cloudflare/Nginx
      edge limits documented as deployment defense in depth.
- [ ] Run a dedicated dependency hygiene pass for Django, openpyxl, JointJS, and
      other Python/JS packages. Record versions, known vulnerabilities,
      upgrade decisions, and regression results.
- [x] Add configurable non-default Django admin path support for production
      deployments.
- [ ] Finish Django admin exposure review before production: Cloudflare/IP or
      identity restriction, 2FA, strong admin passwords, logging, and whether
      `django-admin-honeypot` or a similar decoy path is useful for this
      deployment.
- [ ] Keep `SECRET_KEY`/`DEBUG` local-development behavior for now, but record
      a future production key-rotation/admin mechanism discussion.
- [ ] Document that repo Markdown manuals/notes are not user/admin editable in
      production. Development PM/audit notes may remain in `NOTES/`, but they
      should not be exposed by production views unless intentionally published.

KR/Codex convergence notes, 2026-06-14:

- KR accepted Codex pushback not to add all `NOTES/` to `.gitignore`; PM/audit
  notes remain a development review trail and must simply not be exposed as
  production-editable/user-editable content.
- KR accepted Codex pushback that `django-admin-honeypot` may be useful as a
  low-friction signal/decoy, but is not a substitute for non-default admin
  path, Cloudflare/IP/identity restrictions, 2FA, strong admin passwords, and
  logging.
- KR accepted Codex pushback that rate limiting must be implemented carefully
  so normal engineering uploads are not blocked.
- KR accepted Codex pushback that `SECRET_KEY` must come from production env
  for now; admin-driven key rotation is a future deployment/admin feature.

Checkpoint note, 2026-06-15:

- Existing `UserAttempt` tracking is now wired into `my_login` without a schema
  change. Existing usernames lock for the configured cooldown after three bad
  password attempts; successful login clears prior attempt rows. Unknown
  usernames keep the same generic login error and do not create user-linked
  attempt rows.
- Focused SQLite security tests passed:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht.tests.CatalogueAndSecurityHardeningTests -v 2 --noinput`:
  8 tests passed.
- Full SQLite suite after login-attempt hardening:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  341 tests passed.
- `django-ratelimit==4.1.0` is now pinned in `requirements.txt` and wired as
  the app-level request throttle. Login is limited by both IP and posted
  username; upload, valid-row confirmation, and error-file download endpoints
  are limited by authenticated user or IP. The earlier `UserAttempt` work
  remains as account-specific lockout, not a substitute for rate limiting.
- Rate values are configurable through environment variables:
  `EHT_LOGIN_IP_RATE_LIMIT`, `EHT_LOGIN_USERNAME_RATE_LIMIT`,
  `EHT_UPLOAD_RATE_LIMIT`, `EHT_CONFIRM_UPLOAD_RATE_LIMIT`, and
  `EHT_ERROR_FILE_DOWNLOAD_RATE_LIMIT`.
- Focused SQLite security/rate-limit tests passed:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht.tests.CatalogueAndSecurityHardeningTests -v 2 --noinput`:
  12 tests passed.
- Full SQLite suite after app-level rate limiting:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  345 tests passed.
- KR/Codex decision: rate/security thresholds stay environment-owned for MVP.
  Error-file retention remains admin-editable because it is operational storage
  housekeeping, but login/upload/download throttles are security policy and
  should not become casual admin form fields before validation, audit logging,
  and safe deployment semantics exist. A read-only admin "security settings
  status" page may be useful later.
- `DJANGO_ADMIN_PATH` now controls the mounted Django admin URL, the
  login-required middleware exempt path, and the staff-only landing-page admin
  link. Default remains `admin/` for local development; production should set a
  non-default value in environment and still use Cloudflare/IP/identity
  restrictions and 2FA as defense in depth.
- Focused SQLite security/admin-path tests passed:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht.tests.CatalogueAndSecurityHardeningTests -v 2 --noinput`:
  15 tests passed.
- Quick checks passed after admin-path hardening:
  `venv/bin/python manage.py check`,
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py makemigrations --check --dry-run`,
  and `git diff --check`.
- Full SQLite suite after admin-path hardening:
  `USE_POSTGRES=false DEBUG=true venv/bin/python manage.py test eht -v 2 --noinput`:
  348 tests passed.

### UX-P1 - Low-Risk First-Customer Polish

Status: complete

- [x] Add project selector in navbar.
- [x] Add calculation status badge on project list.
- [x] Group project setup form into logical sections.
- [x] Add help text/tooltips for technical project setup fields.
- [x] Add MI-not-available reason text tied to catalogue validation/readiness.
- [x] Add jump-to-line search/filter on result tables.
- [x] Add Excel export freeze panes and auto-width polish.
- [x] Show last-calculated timestamp on result pages.
- [x] Review existing SLD fit-to-screen/full-screen controls and add a keyboard
      shortcut only if it is low-risk and does not disturb current SLD controls.
- [x] Add SLD PDF title block as low-priority document-package polish.

Checkpoint note, 2026-06-15:

- Added `ProcessLineCalculation.calculated_at` via migration
  `0043_processlinecalculation_calculated_at`, stamped consistently during
  result storage and shown in the result-tab header as `Last calculated`.
- PostgreSQL migration `0043` was applied to `eht_local` after `migrate --plan`
  confirmed it only adds the timestamp field. Existing rows received a
  migration-time timestamp; future calculations receive the actual storage-run
  timestamp.
- Focused timestamp tests passed: 2 tests.
- `StoreCalculatedResultsTests` + `ResultAndBoqViewTests`: 84 tests passed.
- Full SQLite-mode `eht` suite passed: 355 tests.
- `venv/bin/python manage.py check`: passed.
- `env USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run`: passed.
- `git diff --check`: passed.

Completion note, 2026-06-15:

- Added a global project selector to the navbar using a read-only context
  processor. Status badges are intentionally coarse for MVP convergence:
  `New`, `Setup`, `Input ready`, or `Calculated`.
- Authenticated landing page now shows the same project status badges for the
  first few active projects, giving a lightweight project list without creating
  a new dashboard surface.
- `/base/?project_id=...` now validates the requested project against the
  current user's available projects and preselects the workspace form when the
  project is allowed.
- Grouped both project setup forms into project basis, temperature/environment,
  electrical/protection, cold-cable basis, tracer/heat-loss basis, and field
  accessories/classification sections. The full workspace form now includes the
  startup VD warning threshold field already present in the edit partial.
- Added help text for the technical setup fields that directly affect
  catalogue selection, heat loss, cold-cable sizing, and BOQ/schedule basis.
- Result tab now includes a `Jump to line` helper for the per-line result
  table. MI selection records explicitly tell users that rejected MI rows show
  the unavailable reason, catalogue evidence, and next action.
- Added shared openpyxl export polish for input, result, BOQ, and cable
  schedule exports: freeze panes, sheet auto-filter, and bounded auto-width.
- Added SLD `Shift+F` fit-all shortcut, guarded so it does not fire while users
  type in inputs/search fields. Existing Fit All button behavior remains the
  implementation path.
- SLD PDF export now draws a compact engineering title block with project,
  generated timestamp, and review status text.
- PostgreSQL-first targeted test attempt again hit the known Codex-side
  `psycopg.OperationalError: connection is bad` during test database setup
  before tests executed. SQLite fallback targeted tests passed:
  `ProjectDataViewTests`, `ResultAndBoqViewTests`, and
  `SldWorkspaceJavaScriptTests`: 101 tests passed.
- Full SQLite-mode `eht` suite passed: 358 tests.
- Final checks passed:
  `venv/bin/python manage.py check`,
  `env USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run`,
  `node --check static/js/sld_workspace.js`, and `git diff --check`.

### REL-P1a - Release-Readiness Reconciliation

Status: complete

- [x] Reconcile tracker status against completed code passes.
- [x] Review Claude dashboard integration for access scope, generated schedule
      basis, MI validation exposure, SLD-stage basis, responsiveness, and
      external dependency risk.
- [x] Add focused smoke coverage for project dashboard and FAQ/help rendering.
- [x] Run final quick checks and full SQLite suite after reconciliation edits.
- [ ] Confirm remaining manual release checklist items with KR before declaring
      the MVP ready for external engineering review.

Checkpoint note, 2026-06-15:

- Dashboard review found no release-blocking integration issue. It uses
  `ManagedProject.available_to_user()` access scope, project-specific MI
  family validation exposure, actual generated schedule workspace data, and
  `PowerDistributionBranch` as the SLD-output basis. The remaining dashboard
  deep-link polish is optional: schedule/workspace links may later pass
  `?project_id=...` now that `/base/` supports it.
- FAQ/help page was treated as Claude-owned polish during this pass. Codex
  added a stable smoke test for the searchable FAQ surface without modifying
  Claude's template work.
- Final reconciliation checks passed:
  `venv/bin/python manage.py check`,
  `env USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run`,
  `node --check static/js/sld_workspace.js`, and `git diff --check`.
- Full SQLite-mode `eht` suite passed after reconciliation:
  `env USE_POSTGRES=false venv/bin/python manage.py test eht -v 2 --noinput`:
  360 tests passed.
