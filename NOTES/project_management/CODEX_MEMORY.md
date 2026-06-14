# Codex Memory

Last updated: 2026-06-14

Purpose: compact operating memory for Codex when resuming work after context
compression, pauses, or new chats. Keep this file short and current.

## Current Objective

Make the current SR/MI + cold cable + SLD + BOQ/cable schedule path
production-ready before starting Constant Power tracer or major 3D/model-routing
work.

## Database Safety Protocol (MANDATORY — no exceptions)

Adopted 2026-06-11 after the accidental CC-P5 flush of `eht_local`:

- `manage.py flush` is banned without explicit written KR approval.
- No `DELETE`, `TRUNCATE`, or `DROP` against `eht_local` without explicit
  written KR approval.
- No `.objects.all().delete()` or `QuerySet.delete()` on any
  catalogue/reference table without KR approval.
- Before every database-modifying command, verify the active database name and
  state it explicitly.
- This applies every time, with no exceptions.

VENDOR CSV WARNING: `eht/tmp/elecEHT_Vendor.csv` (219 rows) is a post-research
working file, NOT a database mirror. It contains 178 rows that are NOT in the
current database (91 Constant Wattage Thermon/nVent + 87 Krus-Zapad MI, all
unverified) and is MISSING 89 validated rows that ARE in the database. Do NOT
run `import_data_from_file` against the vendor table — it will corrupt it.
KR is reviewing whether to add the 178 unverified rows.

## Product Vision

eTrace should become a comprehensive EHT engineering platform that exceeds
manufacturer tools by combining heat-loss calculation, tracer selection, cold
cable engineering, interactive SLDs, BOQ/schedules, auditable reports, and
eventually model-based routing/component placement.

## Active Phase

Phase A: production hardening of the current working path.

Immediate next pass:

1. KR/manual release sign-off: demo walkthrough, cold-cable label overlap
   inspection, large-project browsing/search feel, and terminal-voltage manual
   cross-check.
2. `CAT-P1` remains deferred per KR: catalogue gate/import safety is important,
   but CSV import tightening is not the immediate convergence path.
3. Keep the calculation manual aligned with any behavior changes.

## Current Repo State

- Working directory: `/home/kr/mydev/eht_office`.
- Current date at latest update: 2026-06-14.
- Phase A code through `RELEASE-P1` is implemented in the current worktree.
- Latest full SQLite test status (verified 2026-06-14 with
  `USE_POSTGRES=false`): 314 tests passed. SQLite quick testing remains the
  default fast path.
- Latest full PostgreSQL test status (verified 2026-06-12 against
  `eht_local_test` via the programmatic runner): 306 tests passed,
  `Failures: 0`.
- `TEST-P1` is complete: `SldLayoutTests` now authenticate under the
  login-required middleware, the SLD cold-cable label assertion matches the
  CC-P5 single-phase terminology, and migration `0037` is SQLite-compatible.
- `SLD-P2` is complete: combine-feeder apply now recalculates the manual
  combined FeederCable trunk from operating-current impact evidence, defaults
  missing combined length to the maximum selected feeder length, forces route
  review, persists cold-cable impact evidence in `SLDTopologyEdit.edit_payload`,
  and preserves the calculated trunk metadata in the active SLD payload.
- `SLD-P1` is complete: SLD workspace shows compact review badges for missing
  cable length, cold-cable review/unsizeable states, manual overrides, and
  manual topology review/stale states. Full SQLite suite passed 307 tests on
  2026-06-12.
- `AUD-P1` is complete: read-only `eht_local` audit confirmed restored
  reference counts, all migrations through `0037` applied, and no active
  selected-MI orphan driving output. It found two follow-up items for `CAT-P1`:
  live normalized MI validation currently has THR/MIQ and CHR/MI-825B
  `is_validated=True` while project notes say all families should remain false
  until KR row review; and `import_data_from_file` can still blindly import the
  divergent vendor CSV.
- `SCH-P1` is complete: cable schedule overrides now carry optional
  procurement/review annotations (route reference, installation area/basis,
  drum tag, cable lot, revision, review status, checked-by/date). The schedule
  table and Excel export surface these fields, admin can maintain them, and
  migration `0038_cablescheduleoverride_cable_lot_and_more` adds the columns.
  `0038` is applied to live PostgreSQL dev database `eht_local` as of
  2026-06-13 19:25 fix after the upload path exposed the pending-schema
  mismatch.
- Claude's SCH-P1 requirements review recommended a fuller procurement
  schedule snapshot model and identified null SR A/B/C coefficients as a
  must-fix blocker. KR accepted the lighter SCH-P1 as complete for convergence;
  the fuller snapshot model is deferred. `QA-P1a` fixed the active blocker:
  `compute_power_params` explicitly rejects missing/non-numeric SR coefficients,
  and `orchestrate_calculations` no longer publishes selected SR/power/BOQ rows
  when downstream power parameters fail.
- `QA-P1` is complete: added `NOTES/verification/QA_P1_WORKED_EXAMPLES.md`
  with SR, MI, direct single-phase cold-cable, and shared Feeder/Branch
  optimization worked examples; corrected stale SR parallel independent-branch
  wording in the verification report, manual, and design guide to the active
  shared-MCB basis; added regression tests for verification-report Sections B-E
  formula text and manual/design-guide shared-MCB wording.
- `RELEASE-P1` code sweep is complete: `ELECSENSE/settings.py` no longer
  hardcodes wildcard `ALLOWED_HOSTS`; production HTTPS/HSTS/secure-cookie
  settings are environment-driven; default PostgreSQL host is local unless
  overridden. Production-shaped `manage.py check --deploy` passed with explicit
  deployment env values. PostgreSQL `migrate --check` and direct connection
  passed against live `eht_local` after local DB access was allowed. Full
  SQLite suite remains 314 tests passed. Manual release sign-off items remain:
  demo walkthrough, cold-cable label overlap inspection, large-project
  browsing/search feel, and terminal-voltage manual cross-check.
- Testing convention from 2026-06-14: try PostgreSQL-backed tests first where
  meaningful, then fall back to SQLite if Django test-runner setup hits the
  known `psycopg.OperationalError: connection is bad`. Direct Django PostgreSQL
  connection to `eht_local` remains usable.
- Local PostgreSQL is healthy; first-attempt failures from Codex were
  command-sandbox local-network restrictions. Use local Postgres access for
  PostgreSQL-backed Django commands.
- `eht_local` restoration after the CC-P5 accidental flush is COMPLETE
  (2026-06-11): SR + MI tracer library 130 rows restored from backup table
  `eht_eleceht_vendor_backup_temp`; ASME B36 pipe sizes 200 rows restored from
  `eht/tmp/elecEHT_ASMEB36.csv`; thermal conductivity 5 rows restored from
  `eht/tmp/elecEHT_ThermalConductivity.csv`; cold cable catalogue 14 rows
  intact (migration-seeded, unaffected).
- Claude's KR-instructed MI vendor-validation pass on 2026-06-12 found the
  originally seeded MI catalogue data was not R7-valid. The MI catalogue was
  backed up and reseeded from official vendor documents under
  `NOTES/vendor_validation/`; the documented intended state after reseed was
  all MI families `is_validated=False` pending KR row-by-row review via Django
  admin. `AUD-P1` later found the live DB has THR/MIQ and CHR/MI-825B marked
  validated; resolve in `CAT-P1`.
- Latest SLD topology regression status: `SldTopologyWorkflowTests` 32 tests OK
  in SQLite mode on 2026-06-12 after `SLD-P2`.
- Latest broader SLD/payload/result/topology/JS regression status:
  `SldPayloadTests`, `ResultAndBoqViewTests`, `SldTopologyWorkflowTests`, and
  `SldWorkspaceJavaScriptTests` 120 tests OK in SQLite mode on 2026-06-12.
- Latest PostgreSQL-backed targeted test status: 4 `CC-P3` result/cold-cable
  tests OK on 2026-06-07 using existing database `eht_local_test`.
- Latest cold-cable catalogue readiness inspection: Method E has validated
  IEC/Cu/XLPE rows only: 4 rows for 3C and 10 rows for 4C. Methods B2, C, D1,
  and D2 have no validated rows.
- Project setup currently exposes only Method E as selectable. Method D2 direct
  buried is visible as a disabled coming-soon option. B2, C, and D1 are hidden
  from project setup until their catalogue basis is ready.

## Frozen Engineering Decisions

- SR remains the default hot-cable technology.
- MI is automatic only when SR catalogue suitability limits are exceeded.
- Users do not manually choose SR versus MI in project setup.
- Constant Power tracer is a future separate hot-engineering module.
- SR parallel runs now use one shared 2-pole MCB per run group for cold-cable
  rebuild purposes.
- MI multi-sets remain represented as independently protected branches.
- SLD alternate tracer overrides are review-only and do not recalculate load,
  BOQ, breaker size, or cable schedule yet.
- SR A/B/C polynomial method remains active; vendor curve-point interpolation is deferred.
- MI T-class is review evidence, not final calculated sheath-temperature approval.
- Cold cable conductor path is Cu-only for now.
- Aluminium cold-cable catalogue path has been removed/deferred.
- Cold cable uses RCD terminology, not GFEP terminology.
- Cold cable sizing uses operating current, not starting current.
- Cold cable voltage-drop basis: PF = 1.0; reactance term ignored.
- Active cold-cable rebuild basis is single-phase: `FeederCable` from MCB to
  optional `DistributionJB`, then `BranchCable` to `BranchJB`/tracer.
- Single-phase VD formula: `2 x I x R x L`, evaluated across the full terminal
  path (`VD_feeder + VD_branch`).
- L-PE fault loop basis:
  `Z_loop = Z_source + R_phase_feeder + R_PE_feeder + R_phase_branch + R_PE_branch`.
- EHT DB fault rating is mandatory, defaults to 15 kA, and accepts presets
  10/15/25/40/50 kA plus Other >= 1 kA. It is the three-phase prospective
  short-circuit current at the EHT DB busbar. Source impedance is
  `V_phase / (three_phase_fault_rating_ka x 1000)`.
- Cable conductor temperature basis: XLPE = 90 C, PVC = 70 C.
- Copper resistance temperature coefficient: `0.00393 / C`.
- Ampacity derating: `K_temp x K_group`.
- Grouping derating valid range: `0.25` to `1.0`.
- RCD provided: weak 3C MCB earth-loop result becomes review-required, not automatic upsizing.
- RCD not provided: MCB earth-loop check is hard gate; engine can upsize 3C if a larger cable passes.
- Tracer PE-path resistance is deferred and documented as non-conservative.
- Project default cable lengths force `review_required` even when sizing passes.

## Important Implemented Cold-Cable Behavior

- `ColdCableResult.cable_3c_segments` stores per-outgoing 3C sizing evidence.
- Different outgoing 3C lengths from the same JB can select different 3C sizes.
- Branch-level 3C result stores the critical/largest selected 3C summary.
- SLD/cable schedule metadata can read per-node 3C segment results.
- Cable mass is calculated from conductor area, length, core count, and copper density.
- Per-branch Branch Cable segment evidence is visible in the result tab, cable
  schedule, cable schedule export, and a dedicated `Cold Cable Branch Segments`
  result-export sheet.
- `CC-P3` adds `phase_slot`, `phase_label`, and `phase_basis` to per-outgoing
  3C segment JSON, propagates the phase label into SLD Cable3C metadata, and
  shows L1/L2/L3 phase-current totals plus imbalance in result UI/export.
- `CC-P4` adds a branch-based Panel / Load Summary to the Result tab and result
  export. It groups by panel/source metadata when present; otherwise it groups
  under the project main distribution. It reports MCB count, circuit count,
  load current, connected load, breaker distribution, and cold-cable selected /
  review-required / unsizeable / not-sized counts. It is review evidence only;
  upstream main-breaker spare-capacity checks and bus phase totals remain
  deferred.
- 2026-06-08 CC-P4 correction: panel/load summary now uses branch current
  (`per_circuit_operating_current_a x circuit_count`) before line-total
  fallback data, and deduplicates shared MCB count/breaker capacity by MCB tag.
- `ProjectData.eht_db_fault_rating_ka` and
  `ProjectData.eht_db_source_impedance_ohm` are in place as the source
  impedance foundation for `CC-P5`.
- Migration `0034_rcd_cu_only_cold_cable` renames GFEP fields to RCD and deletes Al catalogue rows.
- `CC-P1` adds cold-cable installation-method readiness feedback in admin and
  explicit unsizeable guidance instead of a generic no-catalogue message.
  Project setup is simplified to active Method E plus disabled coming-soon D2.
- SLD topology operations are hardened against a stale/empty browser workspace
  state. The SLD shell now clears stale state at render start, releases the
  render guard on success/error/focused-line fallback, and controls re-trigger
  SLD loading instead of silently no-oping when `__sldState` is missing.
- SLD render guard follow-up fixed the remaining sticky-lock path: render
  callbacks use `finally`, `renderSldGraph` catches top-level runtime failures,
  and a watchdog clears a stuck render flag after 20 seconds.
- SLD topology browser regression had a second, more fundamental cause after
  cold-cable engineering: rendered SLD symbols/cable nodes became more
  SVG-path-driven, while component click handling relied on unreliable implicit
  hit testing. Component bodies now declare explicit pointer hit targets, and
  the browser test performs real rendered-cell preview/apply workflows.
- P1-specific SLD stale failure root cause: P1 had a 96-operation historical
  active topology chain whose first saved `combine_feeders` operation referenced
  old MCB component IDs no longer present in the recalculated generated graph.
  New edits previously inherited that unreplayable chain, so every new apply
  was hidden behind operation #1 failing replay. Apply workflows now inherit an
  active operation chain only if it replays successfully against the current
  generated baseline; otherwise the new edit starts from the graph the user is
  actually seeing.
- Cold-cable engineering also exposed an over-broad topology fingerprint:
  `payload_fingerprint` included all node metadata, including volatile cold
  cable sizing/review evidence. The fingerprint now tracks topology structure
  only, so cold-cable calculation metadata cannot falsely mark an SLD edit as
  stale.
- `base.html` versions the SLD script as `sld_workspace.js?v=sld-r3-hit-targets`
  so Chrome does not keep executing old SLD interaction code after this fix.
- `eht.browser_tests` is the optional Playwright browser-smoke module for SLD.
  It is intentionally separate from normal backend tests and runs successfully
  through venv Playwright against the Django live server and PostgreSQL test DB.
  Latest run: `venv/bin/python manage.py test eht.browser_tests -v 2 --noinput`
  passed 3 tests in 11.943s on 2026-06-07, including preview and apply for
  Combine, Split, Add downstream JB, and Attach/Move.
- Real P1 verification was performed with database transactions rolled back:
  Combine, Split, Add downstream JB, and Attach all returned `ok=True`, produced
  one clean operation in the new active edit, and cleared false
  `topology_edit_review_required` / `topology_baseline_changed` state without
  mutating the live P1 data.
- SLD hardening pass on 2026-06-07:
  - Frontend render paths now use one `safeRenderCurrentSldPage` gateway for
    initial load, pager, page-size changes, and search-driven page changes.
  - External detail labels use one geometry helper for create/refresh so labels
    do not drift after component movement.
  - Filtered/focused SLD views disallow topology mutation with a warning, while
    cable length overrides and tracer alternate selection remain available.
  - Topology apply locks the project row, validates operation schemas and graph
    invariants, records stale-chain drop audit metadata, and compacts very long
    operation chains fail-closed.
  - Programmatic existing-PostgreSQL SLD suite passed 38 tests. Standard
    `manage.py test ...` still fails in the test-command setup connection path
    with `psycopg.OperationalError: connection is bad`, despite direct Django
    connection/migrate and the programmatic runner succeeding.
- `CC-P5` rebuild is implemented: SR parallel runs share one 2-pole MCB per run
  group; cold-cable sizing uses single-phase Feeder Cable + Branch Cable paths,
  terminal-path `VD = 2 x I x R x L`, project three-phase EHT DB fault rating
  source impedance, and complete L-PE loop evidence. Migration
  `0036_single_phase_cold_cable_fault_loop` deletes stale `ColdCableResult`
  rows and replaces old 4C phase-to-phase result fields with
  `fault_current_l_pe_a`, `fault_loop_status`, and `fault_loop_basis`.
  If migrated/invalid data makes source impedance unavailable, the engine uses
  `Z_source = 0.0` and writes an explicit review note.
- Claude review follow-up after CC-P5: form/manual/docs now explicitly say the
  EHT DB fault rating is the three-phase PSCC at the DB busbar; tests now cover
  panel-summary fallback from zero per-circuit current to line current and
  multi-circuit per-circuit multiplication.
- Second Claude review follow-up after CC-P5: migration
  `0037_remove_legacy_3c_fault_fields` removes the legacy 3C line-to-neutral
  fault fields; SR shared-MCB branches now retain group-level tagged metadata
  (`sr_parallel_run_count`, `sr_parallel_run_basis`, `sr_shared_mcb`) without a
  per-run index.
- Upcoming SLD combine feature: when circuits are combined, the new combined
  Feeder Cable must trigger cold-cable re-sizing based on combined current. The
  UI should warn that previous separate feeder lengths are no longer valid;
  default the new combined Feeder Cable length to the highest length among the
  selected feeder cables and require user review/confirmation.
- Local dev DB caveat from 2026-06-08: during CC-P5 verification, Codex
  accidentally executed a destructive `flush` against the local PostgreSQL
  development database. Catalogue/reference restoration completed 2026-06-11
  (see Current Repo State). This incident is the origin of the mandatory
  Database Safety Protocol section above.
- Housekeeping pass after SLD hardening removed live debug/dropdown projects
  `p-debug-sld`, `p-debug-sld-api`, `p-hard`, and empty orphan `p2` from local
  PostgreSQL. Current live project selectors should show only `default_project`
  and `p1`. Ignored `__pycache__` directories were cleaned once; normal checks
  may recreate them.
- Tracked SLD review docs (`SLD_DEEP_ANALYSIS.md`,
  `SLD_RENDERING_REVIEW.md`) and `eht/browser_tests.py` are intentional guard
  rails and should not be treated as temporary artifacts.
- `SLDTopologyEdit` is registered in Django admin as a read-only audit panel.
  It shows operation history, operation count, compaction state, stale-chain
  audit metadata, validation JSON, current-baseline fingerprint comparison, and
  an in-memory replay diagnostic. This is admin visibility only; there is still
  no user-facing undo/restore-to-operation feature.
- SLD topology history retention is implemented. Old `superseded` and `reset`
  rows can be compacted to audit-only payloads while active `applied` and
  `needs_review` rows remain protected. Django admin shows payload size and
  payload-compaction status, provides a selected-row compaction action, and has
  a guarded emergency delete action for non-active history rows only. The
  `compact_sld_topology_history` management command defaults to dry-run and
  requires `--execute` to mutate records. Local live cleanup on 2026-06-07
  compacted 100 old rows and saved about 57.5 MB of JSON payload; follow-up
  dry-run reported 0 remaining candidates under the keep-full 20 / keep-reset
  10 policy.

## Known Deferred Gaps

- Installation-method catalogue coverage remains limited to Method E seed rows;
  D2 catalogue work is deferred and shown as coming soon in project setup.
- Automatic phase rebalancing/user-editable phase slots are not built.
- Upstream main-breaker coordination/spare-capacity checking is not built. The
  CC-P4 branch-based panel/load summary is available for review evidence.
- MI R7 row-by-row validation state needs reconciliation after Claude's
  2026-06-12 official document review/reseed. The intended gate is
  `MICableFamily.is_validated=False` until KR approves rows via Django admin,
  but `AUD-P1` found the live DB currently has THR/MIQ and CHR/MI-825B marked
  validated. Resolve before trusting MI-sensitive calculations.
- `import_data_from_file` still imports `eht/tmp/elecEHT_Vendor.csv`; do not
  run it. `CAT-P1` should guard or retire this command.
- Procurement-grade cable schedule fields/export are not built.
- Browser-level SLD smoke coverage exists in `eht.browser_tests` and is green
  in the local dev setup after installing Playwright's Linux browser
  dependencies in the venv workflow.
- Tracer PE-path impedance is not included in earth-loop calculation.
- Short-circuit withstand/minimum conductor cross-section is deferred.
- MI max heated length, cold-lead completeness, terminal/gland/JB capacity are deferred.
- SR vendor curve-point interpolation is deferred.
- Constant Power tracer is deferred.
- Model-based cable routing and 3D component placement are deferred.

## Collaboration Notes

- Claude acts as architect/auditor/reviewer/critic/collaborator.
- Codex acts as senior developer/collaborator/consultant/adviser and implements.
- Do not code immediately from Claude review notes unless user approves.
- Record review findings intended for Claude in a shareable note.
- Keep `NOTES/CALCULATION_MODULE_USER_MANUAL.md` aligned when implementing or
  changing any calculation behavior. Claude maintains the manual, but Codex
  should flag discrepancies during implementation.

## Testing Commands

SQLite is the quick/default test path. Local PostgreSQL remains the development
database and PostgreSQL-backed safety check. In Codex-managed commands,
PostgreSQL-backed tests need local Postgres access enabled; otherwise the
command sandbox can produce a false connection failure.

```bash
venv/bin/python manage.py check
USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run
USE_POSTGRES=false venv/bin/python manage.py test eht -v 2 --noinput
node --check static/js/sld_workspace.js
git diff --check
venv/bin/python manage.py test eht.browser_tests -v 2 --noinput

# Full suite — PostgreSQL-backed programmatic runner (backup/safety path)
venv/bin/python manage.py shell -c "
from django.test.utils import get_runner
from django.conf import settings
TestRunner = get_runner(settings)
runner = TestRunner(verbosity=1, keepdb=True)
print('Failures:', runner.run_tests(['eht']))
"
```

Current caveat: raw DB-using `venv/bin/python manage.py test ...` can fail in
the Codex sandbox unless local PostgreSQL access is explicitly enabled. SQLite
tests do not need that access.

## New Chat Guidance

Recommend a new chat when:

- A major pass is complete and tests are green.
- The worktree is checkpointed.
- A new module begins.
- Context replay becomes more expensive than reading this memory file.
- The next task is large enough to deserve a clean brief.

Current recommendation: `CC-P0` through `CC-P5`, `SLD-R1`, `DB-R1`,
`TEST-P1`, `SLD-P2`, `SLD-P1`, and `AUD-P1` are complete. Next work:
`CAT-P1` catalogue gate/import safety, then `SCH-P1` procurement-grade cable
schedule fields/export.
