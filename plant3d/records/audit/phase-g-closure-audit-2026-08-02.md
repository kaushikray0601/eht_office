# Phase G Closure Audit - Raceway MVP Before Phase H

Date: 2026-08-02  
Owner: Codex, with KR decision authority and Claude/Fable review  
Scope: audit-only closure pass before cable assignment, routing/pathfinding,
and durable EHT integration work.

## Sources Reviewed

- `plant3d/records/tracking/raceway-mvp-progress-tracker-2026-07-08.md`
- `plant3d/records/audit/open-items-register.md`
- `plant3d/records/audit/claude-notes-2026-07-08.md`
- `plant3d/records/audit/development-scorecard.md`
- `NOTES/project_management/CODEX_MEMORY.md`
- `CLAUDE.md`
- `NOTES/project_management/CLAUDE.md`
- `plant3d/records/README.md`
- Current Raceway warning code/tests for rough clash/clearance basis.
- Markdown inventory under `plant3d/records/` and `NOTES/`.

## Executive Position

Phase G is functionally successful, but it should not be declared closed until
the remaining technical balance, records balance, and decision balance are
settled deliberately.

The accessory authoring arc is MVP-complete:

- reducer, bend, riser, Tee, and Cross proxy paths exist,
- schedule/fitting/warning projection contracts are pinned,
- Make Tee/Make Cross authoring is accepted by KR manual testing,
- inferred Tee/Cross branch intent remains projection-only and does not drive
  procurement sizing,
- current reducer handedness is a drafting control until real accessory intent
  persistence exists.

The phase is not blocked by a missing core Raceway feature. It is blocked by
closure discipline: stale orientation files, open KR decisions, JS hardening
tail, clash/pathfinding staging clarity, and housekeeping.

Claude/Fable §49 reviewed this closure audit and endorsed the closure instinct
with adjustments:

- keep `open-items-register.md` as the single source of truth by adding
  dispositions there,
- include CI and the vendor-catalogue sync command in Technical Closure,
- treat A1 catalogue-seed blessing as a closure item,
- timebox closure so it does not become drift,
- make Clash v0 queryable per durable graph edge before route suggestions rely
  on penalties/reasons.

## What "Complete This Phase" Means

Not every deferred idea should be coded before Phase H. Closure means each item
is placed into one of five states:

1. Closed in code and tests.
2. Closed by explicit KR decision.
3. Deferred to Phase H because it belongs to cable/routing.
4. Deferred to post-MVP because it is vendor/detail/production hardening work.
5. Discarded as superseded.

Anything left as a vague open reminder is not closed.

## Must Close Before Starting Phase H-A1

### G-1. Records And Session Orientation

Status: closed in Closure Pass 2.

Why it matters: fresh Codex/Claude sessions still see stale June-era
orientation in root/project management documents.

Close by:

- refresh root `CLAUDE.md` so it points to the Plant3D/Raceway era,
- refresh or supersede `NOTES/project_management/CLAUDE.md`,
- update `plant3d/records/README.md` active-plan section after closure,
- keep `CODEX_MEMORY.md` as Codex's local continuity note,
- make the open-items register the single source for open decisions.

### G-2. KR Decision Sweep

Status: closed for A1/A2 on 2026-08-29; A3 and B2 remain KR-owned follow-ups.

Decisions needed:

- A1: bless or amend the generic IEC/vendor-free Raceway catalogue seed.
- A2: decide whether `plant3d/records/audit/eht_office.code-workspace` should
  be untracked/ignored or kept deliberately.
- A3: approve or reject L1 CI before Phase H.
- B2: schedule/record the pending EHT release sign-off separately from Raceway.

Recommendation:

- Accept A1 for MVP as "generic IEC/vendor-free seed, not vendor-validated."
- Remove/untrack A2 unless KR intentionally wants workspace files in records.
- Approve A3 before Phase H. Routing/pathfinding will add enough surface that
  manual-only verification becomes fragile.

Closure Pass 6 note: A1/A2/A3 were still open in
`open-items-register.md`. Codex did not silently close them.

Hot-standby update, 2026-08-29: KR accepted A1 as a generic IEC/vendor-free MVP
seed, explicitly not vendor-validated, and approved A2 workspace-file cleanup.
A3 CI remains open.

### G-3. C10 Tail - JavaScript Hardening

Status: low-risk closure slice closed; larger H-A2 split deferred.

Already closed:

- command-state pure seam,
- JSDoc typedefs,
- schedule/fitting view-model helpers,
- server-client contract pins,
- fail-loud graph/fitting validation,
- visible disabled reasons.

Still deferred:

- deeper geometry/DOM module split,
- eventual separate JS module file,
- broader reusable topology/segment-picking helpers,
- JS pure-function test runner or equivalent lightweight unit coverage.

Recommendation:

- Close at least one more hardening slice before Phase H UI work.
- If H-A1 stays server-side only, this can happen before H-A2, but KR's current
  closure request reasonably pulls it before Phase H starts.

Closure Pass 6 note: the low-risk separate module and Node unit-test seam now
exist. The risky interaction/panel/state decomposition remains a hard
precondition before H-A2 assignment UI, not before H-A1 server routing.

### G-4. Accessory Arc Acceptance Record

Status: closed in Closure Pass 2 as an MVP acceptance record.

Close by writing one explicit record entry:

- MVP accepted: reducer taper proxy, bend/riser proxy, Tee/Cross proxy and
  intuitive authoring.
- MVP limitations:
  - no vendor-grade meshes,
  - no catalogue-grade part sizing,
  - no branch-size procurement designation unless unambiguous/user-confirmed,
  - no persisted accessory acceptance palette yet,
  - riser orientation inheritance remains unresolved where geometry cannot
    infer it safely.
- Post-MVP:
  - covers/dividers/couplers,
  - vendor-specific dimensions,
  - detailed Tee/Cross side-rail cosmetics,
  - explicit accessory intent palette.

### G-5. Clash/Collision Staging

Status: Clash v0 plus H6 route-penalty bridge closed; full physics deferred.

Current implementation:

- `raceway.warning.model_clash_aabb`
- `raceway.warning.model_clearance_aabb`
- `raceway.warning.model_clash_scan_limited`
- source-frame AABB raceway envelope checks against Plant3D object bounds,
- tests cover clash, clearance, scan-limit, orientation-aware envelopes, and
  face-offset-aware envelopes.

Current limits:

- not BVH,
- not mesh/narrow-phase,
- not swept-volume collision,
- not fitting/support-aware,
- not a hard save blocker,
- capped scan behavior can make warnings incomplete in very dense models.

Recommendation:

- Keep this as Clash v0.
- Before route suggestions become user-visible, add Clash v1 planning and
  routing penalties:
  - broad-phase spatial index,
  - configurable clearance categories,
  - clash/clearance as route cost penalties or hard constraints by rule,
  - explicit assumption in route preview payload,
  - defer mesh/narrow-phase to high-risk/selected zones.

Do not build expensive live mesh physics for every mouse movement.

Closure Pass 6 note: H6 is now implemented as
`raceway.clash_edge_penalties.v0`; Clash v1/v2 remain deferred.

### G-6. Phase H-A1 Preconditions

Status: ready to start as Phase H-A1.

H-A1 should begin only after the above closure is recorded.

H-A1 must follow Claude §48 riders:

- durable route edge identity is node-pair-derived, not ordinal `E###`,
- weight function is an injectable seam,
- deterministic tie-breaking is tested,
- route preview payload is contract-pinned from birth,
- no route/assignment persistence until consumer-neutral cable reference design
  exists,
- no UI suggestion loop until saved-state precondition and telemetry are ready.

## Should Close Before Phase H If Cheap

These are small enough that closing them before H would reduce noise:

- C4: telemetry `session_key` or equivalent browser-session grouping.
- C5: browser assertion for blocked telemetry endpoint behavior.
- C7: work-plane/free-route messaging and reusable segment-pick helper notes.
- B3: root `CLAUDE.md` stub refresh.
- C11: stale-doc retirement plan, with no destructive deletion until approved.

## Safe To Defer With Explicit Label

These should not block H-A1 if documented:

- M-5 copy-run-with-offset.
- M-6 EL grid while drawing.
- warning acknowledge/ignore/delete workflow.
- service-class color legend chips.
- inline run-tag rename.
- shortcut cheat sheet.
- opacity/color preference panel.
- detailed support records and structural support automation.
- detailed vendor accessory records.
- underground trench/duct-bank.
- cable pulling tension, drum/cut optimization, fabrication sheets.

## Markdown Housekeeping Inventory

### Keep Canonical

- `plant3d/records/decisions/*.md`
- `plant3d/records/audit/open-items-register.md`
- `plant3d/records/audit/development-scorecard.md`
- `plant3d/records/audit/claude-notes-2026-07-08.md`
- `plant3d/records/audit/raceway-overlay-js-audit-2026-07-19.md`
- `plant3d/records/tracking/raceway-mvp-progress-tracker-2026-07-08.md`
- `plant3d/records/planning/raceway-mvp-execution-plan-2026-07-08.md`
- `plant3d/records/planning/raceway-methodology-and-ai-strategy-2026-07-11.md`
- `plant3d/records/planning/raceway-accessory-geometry-note-2026-07-17.md`
- `plant3d/records/planning/raceway-face-orientation-foundation-2026-07-12.md`
- `plant3d/records/planning/suggestion-telemetry-design-2026-07-12.md`
- platform boundary contracts and viewer extension contracts.

### Keep As Historical But Mark Superseded

- `plant3d/records/tracking/pipeline-spike-tracker-2026-06-22.md`
- older cable-routing vision/review files from July 6,
- June render-format and pipeline explainer files,
- old reset/handover files after the closure record becomes active.

### Needs Review Before Archive Or Deletion

- broad legacy `NOTES/` files from April-June,
- old MI/SR/SLD audit reports,
- old project-management trackers that root `CLAUDE.md` still references,
- `idfviewer/records/` history.

These may still matter for EHT release sign-off or historical reasoning, so
they should be archived/indexed rather than deleted blindly.

### Immediate Delete/Untrack Candidate

- `plant3d/records/audit/eht_office.code-workspace`

Only delete/untrack after KR confirms A2.

## Recommended Closure Sequence

### Closure Pass 2 - Register And Orientation Cleanup

Status: completed 2026-08-02.

- refreshed root/project `CLAUDE.md` orientation,
- made `open-items-register.md` the single source of truth with dispositions,
- staged A1/A2/A3 as KR decisions,
- marked accessory arc accepted for MVP in the accessory geometry note,
- updated tracker and record map.

### Closure Pass 3 - Technical Balance

- close telemetry `session_key`,
- close blocked telemetry endpoint assertion,
- add CI if KR approves A3,
- add vendor-catalogue sync command,
- close the low-risk pure-JS module extraction slice,
- add or update tests only where needed.

### Closure Pass 4 - Clash/Pathfinding Staging

Status: completed 2026-08-28.

- write clash/collision/pathfinding staging note,
- define Clash v0/v1/v2,
- define how H-A1 route costs consume clash/clearance evidence,
- define the edge-penalty bridge from current AABB warnings to durable graph
  edge keys,
- ask Claude to challenge before code.

### Closure Pass 5 - Markdown Housekeeping

Status: completed 2026-08-28.

- apply approved keep/archive/delete list,
- avoid deleting history-bearing docs,
- add superseded headers or archive index,
- remove/untrack workspace file if approved.

### Closure Pass 6 - Final Phase G Acceptance

Status: completed 2026-08-28 as implementation/closure acceptance, with
A1/A2/A3 carried as explicit KR decisions.

- run agreed verification battery,
- update scorecard/register/tracker,
- send Claude closure brief,
- declare Phase G closed,
- then start H-A1.

## Claude/Fable Review Brief

Please challenge:

1. Is the blocker/defer split correct before Phase H?
2. Should C10 JS module split block H-A1, or only H-A2 UI?
3. Is current AABB Clash v0 acceptable as the first route-penalty input, or
   must broad-phase spatial indexing land before H-A1?
4. Is accessory v0 really closed for MVP after Make Tee/Cross acceptance?
5. Which markdown files should be archived versus kept canonical?
6. Do you agree that no mesh/narrow-phase collision physics should be attempted
   live during ordinary tray drawing?

## Pass 1 Outcome

No application code changed. No files deleted. This audit creates the closure
map for the remaining Raceway MVP phase before Phase H.

## Pass 2 Outcome

Closure Pass 2 converted this audit into project records:

- register dispositions were added in `open-items-register.md`,
- root/project Claude orientation was refreshed,
- the accessory note gained an MVP acceptance/limitations table,
- the record README now points fresh sessions to the closure sequence.

## Pass 3 Outcome

Technical Closure Pass 3 partially completed the technical-balance list:

- telemetry `session_key` landed as an additive nullable indexed field,
- Raceway telemetry now carries one browser-session UUID per loaded overlay,
- blocked telemetry endpoint behavior is pinned in the focused browser smoke,
- `sync_curated_catalogue_data` landed as a dry-run-first, explicit-target,
  no-delete database-alias sync command for curated EHT and Raceway catalogue
  tables,
- the sync command reports missing/stale schema as dry-run readiness warnings
  and fails clearly before `--execute`,
- the low-risk C10 JavaScript extraction landed as
  `raceway_projection_core.js`, loaded before the overlay through the existing
  Plant3D extension list.

Not done in this pass:

- CI remains blocked on KR A3 approval,
- `.code-workspace` cleanup remains blocked on KR A2 approval,
- catalogue-seed confirmation remains blocked on KR A1 approval,
- the larger interaction/panel/state JS refactor remains deferred until before
  H-A2 assignment UI.
- local SQLite catalogue aliases are not fully migrated for all curated tables;
  fix the alias schema before treating an actual sync execution as meaningful.

## Pass 4 Outcome

Closure Pass 4 closed the clash/pathfinding staging item:

- added `planning/raceway-clash-pathfinding-staging-2026-08-28.md`,
- defined Clash v0/v1/v2 and the split between warning evidence, route-cost
  hints, and real collision/clearance authority,
- added server module `raceway.clash`,
- added JSON endpoint `/raceway/layers/<layer_id>/clash-penalties/`,
- added projection `raceway.clash_edge_penalties.v0`,
- aggregates existing rough AABB clash/clearance warnings by durable adjacent
  node UUID edge key,
- exposes soft route penalties for H-A1 without introducing new mesh physics,
- pins the projection and endpoint access contract in tests.

## Pass 5 Outcome

Closure Pass 5 closed the records-housekeeping item without destructive edits:

- added `audit/markdown-housekeeping-inventory-2026-08-28.md`,
- added lifecycle headers to historical active-sounding records:
  - `tracking/pipeline-spike-tracker-2026-06-22.md`,
  - `tracking/platform-ecosystem-reset-tracker-2026-07-08.md`,
  - `planning/platform-ecosystem-development-plan-2026-07-08.md`,
  - `planning/cable-routing-foundation-review-2026-07-06.md`,
- listed deletion candidates but removed none,
- left `plant3d/records/audit/eht_office.code-workspace` untouched because A2
  requires explicit KR approval,
- added `raceway_projection_core.test.js` to close the cheap JS unit-test gap
  Claude §51 identified before final acceptance.

## Pass 6 Outcome

Closure Pass 6 added the final acceptance brief:

- added `audit/phase-g-final-acceptance-brief-2026-08-28.md`,
- states that Phase G Raceway MVP implementation and closure sequence are
  complete enough to start H-A1 server-side routing/pathfinding,
- keeps A1/A2/A3 open as explicit KR decisions,
- defines the H-A1 start rules:
  - no route persistence in H-A1,
  - no assignment UI before the consumer-neutral cable-reference note,
  - no graph-local `E###` keys in route payloads,
  - injectable route weight from first implementation,
  - deterministic tie-breaking,
  - route preview contract pinned in Python tests,
  - optional use of `raceway.clash_edge_penalties.v0` as soft route-cost hints.
