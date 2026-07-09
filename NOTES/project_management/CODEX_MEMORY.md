# Codex Memory

Last updated: 2026-07-09

Purpose: compact operating memory for Codex when resuming work after context
compression, pauses, or new chats. Keep this file short and current.

## Current Plant3D Reset Snapshot - 2026-07-08

Primary restart context:

- `plant3d/records/prompts/codex-platform-reset-start-prompt-2026-07-08.md`
- `plant3d/records/planning/platform-reset-handover-2026-07-08.md`
- `plant3d/records/planning/platform-ecosystem-development-plan-2026-07-08.md`
- `plant3d/records/tracking/platform-ecosystem-reset-tracker-2026-07-08.md`
- `plant3d/records/decisions/0005-plant3d-independent-platform-boundary.md`
- `plant3d/records/planning/raceway-module-architecture-2026-07-02.md`

North star: `plant3d` is the neutral 3D engineering platform. EHT,
raceway/tray, cable routing, construction, review, and future modules consume
it through stable anchors and viewer/API seams. They do not put domain
persistence into `plant3d`.

Current pivot: stop pushing cable-first free-space autorouting. Real EPC cable
routing is shared raceway/tray/trunk first, then cable assignment. Existing EHT
cable centerline tools remain draft/manual exception tooling and a useful
editing prototype, not the product architecture.

KR alignment from Claude discussion on 2026-07-08:

- MVP standard direction is IEC-first for Middle East, Asia, and Europe target
  markets. NEMA/ANSI comes later.
- MVP raceway scope is aboveground first: tray, ladder, sleeve/trunking style
  work. Underground trench/duct-bank work is deferred until the MVP integration
  shape is proven.
- EHT must remain a consumer of `plant3d`, not tied into `plant3d`. Future
  modules such as lighting design should follow the same peer-consumer pattern.
- Durable raceway geometry should not be package-RTC render coordinates as the
  only truth. Prefer source/world coordinates or model-object stable anchors
  with source/package context; derive render-frame positions through the
  `plant3d` coordinate/RTC contract for the viewer.

Immediate active plan:

1. Redo Stage 6 centerline authoring after designing the viewer-extension
   interaction contract and browser-smoke-testing real canvas clicks.
2. Keep raceway drawing/persistence in `raceway`; use Plant3D only as the
   viewer host and coordinate/package contract provider.
3. Use the generic viewer extension seam for all raceway viewer code.
4. Keep schema narrow. Supports/fittings/vendor catalogue/cable assignment are
   later after raceway graph shape is proven.
5. Update `plant3d/records/tracking/raceway-mvp-progress-tracker-2026-07-08.md`
   after each pass.

Code facts verified on 2026-07-09:

- Minimal `raceway` app now exists and is registered in `ELECSENSE/settings.py`
  and `ELECSENSE/urls.py`, with an authenticated JSON home endpoint and
  boundary tests. `raceway/access.py` wraps `plant3d.project_gateway` for Stage
  0 project scoping without direct EHT runtime imports. Minimal schema exists:
  `RacewayFamily`, `RacewaySize`, `RacewayLayer`, `RacewayRun`, and
  `RacewayNode`, with loose plant3d ids, source/world metre node coordinates,
  and UUID stable keys on runs/nodes.
- Raceway JSON API slice exists for layers, runs, and ordered node replacement.
  It validates project access, source/package access, family/size consistency,
  coordinate frame, finite node coordinates, and payload shape server-side.
- Plant3D viewer extensions are settings-driven through
  `PLANT3D_VIEWER_EXTENSIONS`; `plant3d` knows only generic extension script
  descriptors, not peer-app details. `package_viewer.js` can create an
  extension-owned overlay group through `createGroup: true` and emits
  `plant3dviewer:layers-ready`. Raceway owns
  `raceway/static/raceway/js/raceway_overlay.js`, which registers
  `raceway-overlay` as owner `raceway`.
- Stage 6 authoring attempt on 2026-07-09 was reverted after KR manual testing:
  Start produced a draft row, but canvas clicks/node commands did not work.
  Do not mark authoring complete without a browser smoke test that actually
  clicks the viewer and verifies nodes are created/moved/deleted.
- `plant3d.models.SourceModel.project_id` is a loose string reference, not a
  hard FK to EHT. The EHT-backed access dependency is intentionally confined to
  `plant3d.project_gateway`.
- `plant3d.tests.Plant3DProjectGatewayTests.test_eht_model_imports_stay_confined_to_project_gateway`
  guards that boundary.
- `plant3d.urls` has source list/upload/detail/json, job json, package viewer
  and package/object/tile APIs.
- `package_json_view` already exposes top-level `coordinate_transform` and does
  not expose `manifest_storage_key`; `source_model_json_view` already exists.
  These satisfy important July 5 contract recommendations.
- `package_viewer.js` already exposes `window.plant3dViewerLayers` with
  `register`, `update`, `setVisible`, `isVisible`, and summaries. Current
  registered layers include model, measurement, reference grid, plot plan, EHT
  draft, and hidden EHT route preview.
- `routing_core.js` remains pure JS with route diagnostics/validation and graph
  primitives, but no server-authoritative validation yet.

Guardrails:

- Do not modify EHT calculation logic while working on `plant3d`/`raceway`.
- Do not add EHT or raceway domain persistence to `plant3d`.
- Do not revive always-on Manhattan/free-click routing as the main UX.
- Do not build smarter cable autorouting before a raceway graph exists.
- Do not split repo/service or add Celery/Redis unless KR explicitly restarts
  that infrastructure track.
- Do not add AGPL runtime dependencies.
- Do not hide model completeness or coordinate/precision uncertainty.
- Collision/pathfinding must begin as warnings/previews. Hard constraints and
  authoritative routing wait for tested collision/pathfinding foundations.

Claude/Fable role: architecture advisor, auditor, reviewer, and independent
researcher. Treat Claude output as valuable review input, not automatic coding
instruction. Major pivots go back to KR before implementation.

Collaboration habit: Claude should write durable findings into a short
date-stamped record under `plant3d/records/audit/` or `plant3d/records/planning/`
with stable section headings. KR can then cite file path plus line/section to
Codex. Codex should either implement accepted items or fold them into the active
plan/tracker with a note, rather than relying on long pasted chat transcripts.

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

1. Move to the next agreed audit-convergence pass outside Claude's dashboard
   workstream.
2. KR/manual release sign-off: demo walkthrough, cold-cable label overlap
   inspection, large-project browsing/search feel, and terminal-voltage manual
   cross-check.
3. KR/Claude catalogue decisions: live MI validation state, SR catalogue gate
   or warning policy, and final approved catalogue state.
4. Keep the calculation manual aligned with any behavior changes.

## Current Repo State

- Working directory: `/home/kr/mydev/eht_office`.
- Current date at latest update: 2026-06-15.
- Phase A code through `CAT-P1 / SEC-P1a` and `EHT-P1` is implemented in the
  current worktree.
- Latest full SQLite test status (verified 2026-06-15 with
  `USE_POSTGRES=false`): 332 tests passed. SQLite quick testing remains the
  default fast path.
- Latest full PostgreSQL test status (verified independently by Claude on
  2026-06-15 against local PostgreSQL): 320 tests passed.
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
  SQLite suite is now 330 tests passed after `EHT-P1` close-out. Manual release
  sign-off items remain:
  demo walkthrough, cold-cable label overlap inspection, large-project
  browsing/search feel, and terminal-voltage manual cross-check.
- `CAT-P1 / SEC-P1a` code safety sweep is complete: `import_data_from_file` is
  blocked by default and requires `--execute` plus exact confirmation text
  before legacy CSV import; SR selection tests explicitly ignore legacy
  `Tracer_Family='MI'` vendor rows; login `next` redirects are validated with
  `url_has_allowed_host_and_scheme`; and production host/security settings are
  environment-driven.
- `EHT-P1` is complete: upload validation now enforces
  `Maint_T <= Oper_T <= Design_T`, including the `Maint_T == Oper_T` boundary.
  SR no-selection now persists diagnostics, and SR heat-duty no-match can
  trigger automatic MI fallback with mode `automatic_heat_duty_fallback`. If
  MI also fails, result pages show both SR and MI reasons. Cold-cable results
  now store startup-current voltage-drop warning evidence with a project
  threshold default of 10%; this is warning-only and does not auto-upsize.
  Model-level `HeatTracingInput.clean()` validation is implemented. The result
  page now tells users to review startup terminal voltage, route length, manual
  cold-cable size, or branch/load split when startup VD exceeds threshold.
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
- MI is automatic only when SR catalogue temperature limits are exceeded or SR
  cannot meet heat duty within configured run/spiral limits.
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
- Cold cable sizing uses operating current, not starting current. Startup
  current is checked as a warning-only voltage-drop review item.
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
- `import_data_from_file` is blocked by default and requires explicit
  confirmation; `eht/tmp/elecEHT_Vendor.csv` is still not catalogue truth.
- A lightweight SCH-P1 procurement annotation/export layer exists. Full
  document-level schedule snapshot/issue revision control is deferred.
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

Current recommendation: move through `APP-P1`, `SEC-P1b`, `SCH-P2`, and
low-risk `UX-P1` items as KR prioritizes MVP convergence, while avoiding
overlap with Claude's dashboard work.

Latest APP-P1 note, 2026-06-15: self-registration is explicitly disabled
with HTTP 410. Upload validation error workbooks now use bounded rotating
filenames (`error_file_01.xlsx` ... `error_file_N.xlsx`) instead of the shared
`error_file.xlsx` or unbounded UUID files. Default retention is 10 files at
5 MB each, with admin configurability added by migration
`0040_errorfileretentionpolicy`, applied to PostgreSQL on 2026-06-15. No
policy row was auto-created; runtime fallback remains 10 files at 5 MB until
an admin-configured row is added. Upload validation now rejects path-like
names, non-XLSX/MIME mismatches, and disguised non-XLSX content. Focused
SQLite regression slice passed 12 tests and the full SQLite suite passed
335 tests.

Latest APP-P1 stale-workspace guard, 2026-06-15: project setup save and
replacement line-list upload now require explicit confirmation before clearing
an existing project workspace. Confirmed clears are scoped to the selected
project's uploaded inputs, calculated outputs, BOQ rows, cold-cable results,
SLD layout/topology edits, cable schedule overrides, and tracer overrides.
Catalogue/vendor/reference tables are not in this deletion path. Focused
SQLite tests passed 21 tests; full SQLite suite passed 338 tests.

Latest SEC-P1b login-attempt hardening, 2026-06-15: the existing
`UserAttempt` model is now wired into `my_login` without a migration. Existing
usernames lock for the configured 30-minute cooldown after three bad password
attempts; successful login clears prior attempt rows. Unknown usernames keep a
generic login error and do not create user-linked attempt rows. Focused
security tests passed 8 tests; full SQLite suite passed 341 tests.

Latest SEC-P1b app-level rate limiting, 2026-06-15: `django-ratelimit==4.1.0`
is installed and pinned. Login now has both IP and posted-username request
limits, while upload, valid-row confirmation, and error-file download endpoints
are limited by authenticated user or IP. These are configurable with
`EHT_LOGIN_IP_RATE_LIMIT`, `EHT_LOGIN_USERNAME_RATE_LIMIT`,
`EHT_UPLOAD_RATE_LIMIT`, `EHT_CONFIRM_UPLOAD_RATE_LIMIT`, and
`EHT_ERROR_FILE_DOWNLOAD_RATE_LIMIT`. `UserAttempt` remains account-specific
lockout; `django-ratelimit` is the request-throttle layer. Focused security
tests passed 12 tests; full SQLite suite passed 345 tests.

Latest SEC-P1b admin-path hardening, 2026-06-15: rate/security thresholds stay
environment-owned for the MVP; do not make them casual admin-editable fields
until validation, audit logging, and safe deployment semantics are designed.
`DJANGO_ADMIN_PATH` now controls the Django admin mount, login-required
middleware exemption, and staff-only landing-page admin link. Default remains
`admin/` for local development; production should set a non-default env value
and still use Cloudflare/IP/identity restrictions, 2FA, strong admin passwords,
and logging. Focused security/admin-path tests passed 15 tests; quick checks
passed; full SQLite suite passed 348 tests.

Latest APP-P1 dead-code cleanup, 2026-06-15: removed legacy `eht/calculation.py`
from the shipped app after import scans confirmed no active code imports it and
the live path is `eht.pipeline` -> `eht.cal` -> `eht.calculations/*`. Removed the
obsolete triple-quoted `ElecEHT_CalculatedTable` / `ElecEHT_IO` model reference
block from `eht/models.py`. `manage.py check`, migration dry-run, and the full
SQLite suite passed afterward; no migration was generated.

Latest APP-P1 project referential-integrity pass, 2026-06-15:
`HeatTracingInput.proj_id` is now backed by a `ProjectData` foreign key named
`proj`, with `db_column='proj_id'` so existing raw-ID code such as
`line.proj_id` and `filter(proj_id='P1')` still works. Migration
`0041_heattracinginput_project_fk` includes a fail-fast pre-check for missing,
blank, or overlength line-list project IDs; it does not silently delete or
remap data. Added tests proving `ProjectData.delete()` cascades only project-
owned line/calculation data and does not touch another project, `ManagedProject`,
or catalogue/reference rows. Full SQLite suite passed 349 tests. PostgreSQL
`0041` was applied to `eht_local` on 2026-06-15.
Read-only PostgreSQL orphan check on 2026-06-15 returned `invalid_count: 0` for
current line-list project IDs (`p-fault-4c`, `sp`, `P1`); no rows were modified
during the check. `showmigrations eht`, `migrate --check`, and `manage.py check`
passed after applying the migration.

Latest SCH-P2 cable schedule lifecycle pass, 2026-06-15: schedule visible/full
audit export behavior is complete, and migration `0042_cableschedulerecord`
adds a derived `CableScheduleRecord` audit table keyed by project + autogenerated
cable tag. Schedule view/export syncs active rows into this table when the
schedule is generated for display/export. Internal revision starts at `0`, does
not churn on unchanged schedule views, increments on schedule-relevant changes,
and retires missing tags with timestamp/user evidence where available. The table
is read-only in admin and does not drive calculations, SLD, BOQ, or cold-cable
sizing. Full audit export includes generated/modified/lifecycle evidence; the
default visible export remains compact. Added the shared-feeder/deduplication
legend. Focused lifecycle tests passed, `ResultAndBoqViewTests` passed 81 tests,
and the full SQLite suite passed 355 tests. Migration `0042` was applied to
PostgreSQL `eht_local` on 2026-06-15 after `migrate --plan` confirmed it only
creates the `CableScheduleRecord` table. `showmigrations`, `migrate --check`,
`manage.py check`, and a read-only count query on `CableScheduleRecord` passed
after migration.

Latest UX-P1 result timestamp pass, 2026-06-15:
`ProcessLineCalculation.calculated_at` was added by migration
`0043_processlinecalculation_calculated_at` and applied to PostgreSQL
`eht_local` after `migrate --plan` confirmed it only adds the timestamp field.
`store_calculated_results` stamps all stored line calculation rows from the
same calculation run with one timestamp, and the result tab header now shows
`Last calculated` from the latest stored process-line calculation. Existing
PostgreSQL rows received a migration-time timestamp; future runs will show the
actual storage-run timestamp. Focused timestamp tests passed, the combined
storage/result slice passed 84 tests, full SQLite suite passed 355 tests,
`migrate --check`, `manage.py check`, and read-only PostgreSQL smoke query
passed after migration.

Latest UX-P1 polish completion pass, 2026-06-15: completed the remaining
low-risk first-customer polish items. Added `eht.context_processors.nav_projects`
and wired it into settings so authenticated pages can show a navbar project
selector with coarse status badges: New, Setup, Input ready, Calculated. The
landing page shows the same badges for active projects. `/base/?project_id=...`
now validates the project against `ManagedProject.available_to_user()` and
preselects the workspace form for allowed projects.

Project setup forms are now grouped into logical sections, with extra help text
for technical fields that affect heat loss, catalogue selection, cold-cable
sizing, BOQ, and schedule basis. The full workspace setup form now includes the
startup VD warning threshold field to match the edit partial. Result tab gained
a `Jump to line` helper for the per-line table and a clearer MI rejected-row
cue explaining that unavailable MI records show reason, evidence, and next
action.

Added `eht/excel.py::polish_openpyxl_workbook` and applied it to input, result,
BOQ, and cable schedule exports for freeze panes, auto-filter, and bounded
auto-width. SLD gained a guarded `Shift+F` fit-all shortcut reusing the existing
Fit All button path, and SLD PDF export gained a compact title block with
project, generated timestamp, and generated-for-review status. The first
PostgreSQL targeted test attempt hit the known Codex-side test-runner
`psycopg.OperationalError: connection is bad` before tests executed. SQLite
targeted tests passed 101 tests; full SQLite `eht` suite passed 358 tests.
`manage.py check`, SQLite migration dry-run, `node --check static/js/sld_workspace.js`,
and `git diff --check` passed.

Latest release-readiness reconciliation, 2026-06-15: tracker/checklist status
was refreshed after the UX/dashboard/FAQ work so completed implementation
passes are marked complete without hiding the remaining release gates. `EHT-P1`
is complete; `APP-P1` code is complete with Claude's dashboard delivered;
`SEC-P1b` implemented controls are complete while dependency hygiene, admin
exposure policy, and production key/markdown decisions remain open. Added
focused smoke coverage for Claude's project dashboard and FAQ/help page. The
focused SQLite dashboard/FAQ smoke slice passed 2 tests. Final reconciliation
checks passed (`manage.py check`, SQLite migration dry-run, SLD JavaScript
syntax check, and `git diff --check`), and the full SQLite `eht` suite passed
360 tests.
