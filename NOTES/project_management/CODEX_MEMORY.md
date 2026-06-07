# Codex Memory

Last updated: 2026-06-07

Purpose: compact operating memory for Codex when resuming work after context
compression, pauses, or new chats. Keep this file short and current.

## Current Objective

Make the current SR/MI + cold cable + SLD + BOQ/cable schedule path
production-ready before starting Constant Power tracer or major 3D/model-routing
work.

## Product Vision

eTrace should become a comprehensive EHT engineering platform that exceeds
manufacturer tools by combining heat-loss calculation, tracer selection, cold
cable engineering, interactive SLDs, BOQ/schedules, auditable reports, and
eventually model-based routing/component placement.

## Active Phase

Phase A: production hardening of the current working path.

Immediate next pass:

1. Start `CC-P4`: panel/load summary.
2. Keep the calculation manual aligned with any behavior changes.
3. Consider a checkpoint/commit of PM files plus `CC-P1`/`CC-P2`/`CC-P3` and
   SLD regression-fix changes before the next pass.

## Current Repo State

- Working directory: `/home/kr/mydev/eht_office`.
- Current date at creation: 2026-06-07.
- Current dirty files include `CC-P1` code/docs plus the untracked
  project-management/orientation files: `CLAUDE.md` and
  `NOTES/project_management/`.
- The previous large cold-cable/SLD code diff is not present in the current
  workspace state.
- Migrations through `0034_rcd_cu_only_cold_cable` applied cleanly in the
  SQLite-mode test run. Local PostgreSQL is healthy; first-attempt failures from
  Codex were command-sandbox local-network restrictions. Use local Postgres
  access for PostgreSQL-backed Django commands instead of falling back to SQLite.
- Latest full test status: `281 tests OK` on 2026-06-07.
- Latest SLD topology regression status: `SldTopologyWorkflowTests` 26 tests OK
  against PostgreSQL test DB `eht_local_test` on 2026-06-07 after hardening
  browser-side SLD render-state lifecycle.
- Latest quick check: `venv/bin/python manage.py check` passed on 2026-06-07.
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
- SR parallel runs and MI multi-sets are represented as independently protected
  branches for MVP clarity.
- SLD alternate tracer overrides are review-only and do not recalculate load,
  BOQ, breaker size, or cable schedule yet.
- SR A/B/C polynomial method remains active; vendor curve-point interpolation is deferred.
- MI T-class is review evidence, not final calculated sheath-temperature approval.
- Cold cable conductor path is Cu-only for now.
- Aluminium cold-cable catalogue path has been removed/deferred.
- Cold cable uses RCD terminology, not GFEP terminology.
- Cold cable sizing uses operating current, not starting current.
- Cold cable voltage-drop basis: PF = 1.0; reactance term ignored.
- 1PH VD formula: `2 x I x R x L`.
- 3PH trunk VD formula: `sqrt(3) x I_phase x R x L`.
- For 3PH JB trunk, `I_phase = per_circuit_operating_current`.
- 3PH JB outgoing phase visibility uses inferred L1/L2/L3 round-robin by
  outgoing circuit index. This is review evidence only, not automatic
  rebalancing.
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
- Per-outgoing 3C segment evidence is visible in the result tab, cable schedule,
  cable schedule export, and a dedicated `Cold Cable 3C Segments` result-export sheet.
- `CC-P3` adds `phase_slot`, `phase_label`, and `phase_basis` to per-outgoing
  3C segment JSON, propagates the phase label into SLD Cable3C metadata, and
  shows L1/L2/L3 phase-current totals plus imbalance in result UI/export.
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
- Upcoming SLD combine feature: when circuits are combined, the new combined
  4C trunk must trigger cold-cable re-sizing based on combined current. The UI
  should warn that previous separate feeder lengths are no longer valid; default
  the new combined trunk length to the highest length among the selected feeder
  cables and require user review/confirmation.
- Housekeeping pass after SLD hardening removed live debug/dropdown projects
  `p-debug-sld`, `p-debug-sld-api`, `p-hard`, and empty orphan `p2` from local
  PostgreSQL. Current live project selectors should show only `default_project`
  and `p1`. Ignored `__pycache__` directories were cleaned once; normal checks
  may recreate them.
- Tracked SLD review docs (`SLD_DEEP_ANALYSIS.md`,
  `SLD_RENDERING_REVIEW.md`) and `eht/browser_tests.py` are intentional guard
  rails and should not be treated as temporary artifacts.

## Known Deferred Gaps

- Installation-method catalogue coverage remains limited to Method E seed rows;
  D2 catalogue work is deferred and shown as coming soon in project setup.
- Automatic phase rebalancing/user-editable phase slots are not built.
- Panel/load summary is not built.
- Procurement-grade cable schedule fields are not built.
- SLD visual issue badges are not built.
- Topology edit impact summary is not built.
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

Local PostgreSQL is the normal development database. In Codex-managed commands,
PostgreSQL-backed tests need local Postgres access enabled; otherwise the
command sandbox can produce a false connection failure. Use SQLite only for
explicit isolation checks.

```bash
venv/bin/python manage.py check
env USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run
node --check static/js/sld_workspace.js
git diff --check
venv/bin/python manage.py test eht -v 2 --noinput
venv/bin/python manage.py test eht.browser_tests -v 2 --noinput
```

Current caveat: raw DB-using `venv/bin/python manage.py test ...` can still
fail during existing PostgreSQL test DB setup with `connection is bad`; the
same test passes via `manage.py shell -c "from django.core.management import
call_command; call_command('test', ...)"`. Keep this as `R-012` until the
plain CLI launcher is fixed.

## New Chat Guidance

Recommend a new chat when:

- A major pass is complete and tests are green.
- The worktree is checkpointed.
- A new module begins.
- Context replay becomes more expensive than reading this memory file.
- The next task is large enough to deserve a clean brief.

Current recommendation: project-management setup, stabilization, `CC-P1`,
`CC-P2`, SLD-R1, and `CC-P3` are complete. Consider a checkpoint/commit before
starting `CC-P4`.
