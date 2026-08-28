# Plant3D/Raceway Hot-Standby Pause Index

Date: 2026-08-29  
Owner: Codex, with KR decision authority and Claude/Fable review

## Pause State

KR paused Plant3D/Raceway work after the Phase G closure sequence so attention
can move to another unfinished project.

The project is intentionally left in hot-standby:

- Phase G Raceway MVP is implementation-closed.
- Claude/Fable §53 approves the closure and says H-A1 may start.
- Claude/Fable §54 approves the hot-standby state and recommends closing A1/A2
  before pause; KR approved both on 2026-08-29.
- Final verification on 2026-08-29 was green:
  - `raceway` 77 tests,
  - `plant3d` 76 tests,
  - `telemetry` 5 tests,
  - curated catalogue sync command tests 6,
  - full `eht` 366 tests,
  - Raceway browser smoke 6,
  - JS syntax checks and `node --test`,
  - Django check, migration dry-run, Python compile, and `git diff --check`.

## Restart Read Order

For a new chat, the shortest copy/paste entry point is:

`plant3d/records/prompts/plant3d-hot-standby-restart-prompt-2026-08-29.md`

Read these first, in order, before coding:

1. `CLAUDE.md`
2. `NOTES/project_management/CLAUDE.md`
3. `NOTES/project_management/CODEX_MEMORY.md`
4. `plant3d/records/README.md`
5. `plant3d/records/audit/hot-standby-pause-index-2026-08-29.md`
6. `plant3d/records/audit/open-items-register.md`
7. `plant3d/records/audit/phase-g-final-acceptance-brief-2026-08-28.md`
8. `plant3d/records/audit/claude-notes-2026-07-08.md`, especially §53.
9. The last entries of
   `plant3d/records/tracking/raceway-mvp-progress-tracker-2026-07-08.md`.
10. `plant3d/records/planning/raceway-clash-pathfinding-staging-2026-08-28.md`
11. `plant3d/records/planning/raceway-accessory-geometry-note-2026-07-17.md`
12. `plant3d/records/planning/suggestion-telemetry-design-2026-07-12.md`

## Current Technical State

Important Phase G closure additions:

- `raceway/static/raceway/js/raceway_projection_core.js`
- `raceway/static/raceway/js/raceway_projection_core.test.js`
- `raceway/clash.py`
- `/raceway/layers/<layer_id>/clash-penalties/`
- `raceway.clash_edge_penalties.v0`
- `telemetry.SuggestionEvent.session_key`
- `sync_curated_catalogue_data` management command

Important viewer/runtime note:

- The Raceway overlay loads `raceway-projection-core` before
  `raceway-overlay` through `PLANT3D_VIEWER_EXTENSIONS`.
- Browser tests load the same order.
- Chromium browser smoke may need unsandboxed execution in this environment.

Curated catalogue sync note:

- A dry-run on 2026-08-29 used `USE_POSTGRES=false` and target
  `sqlite_backup`.
- No data was changed.
- Legacy EHT catalogue/reference tables would upsert to `sqlite_backup`.
- Seven curated models could not be inspected because source schema tables are
  absent on the local `default` alias, including `RacewayFamily` and
  `RacewaySize`.
- Do not run `sync_curated_catalogue_data --execute` until source/target aliases
  are migrated and dry-run readiness is clean.

## KR Decisions

Closed before pause:

- A1: KR accepted the generic IEC/vendor-free Raceway catalogue seed for MVP,
  explicitly not vendor-validated.
- A2: KR approved removing/untracking
  `plant3d/records/audit/eht_office.code-workspace`; future local workspace
  files are ignored.

Open decision to preserve:

- A3: KR must approve or reject L1 CI.

Recommendation remains:

- approve A3 before Phase H grows.

## Next Coding Pass

Start Phase H-A1 server-side routing foundation.

Scope:

- create `raceway.routing`,
- build route network from saved Raceway graph/topology,
- use durable edge identity: `start_node_key::end_node_key`,
- never expose graph-local `E###` keys as stored route truth,
- implement deterministic shortest path,
- make the edge weight function injectable from the first pass,
- start with length-only cost,
- add route preview JSON endpoint,
- pin the route preview payload contract in Python tests in the same pass.

Immediate second H-A1 increment:

- consume `raceway.clash_edge_penalties.v0` as optional soft route-cost hints.

## Phase H-A1 Non-Goals

Do not do these in the first routing pass:

- no route persistence,
- no cable assignment UI,
- no direct EHT imports in Raceway,
- no mesh/BVH/narrow-phase collision physics,
- no large JS interaction refactor,
- no vendor accessory catalogue workflow.

## H-A2 Gates

Before assignment UI:

- write the consumer-neutral cable reference note:
  `owner_module` plus opaque `cable_ref`,
- plan durable EHT persistence as the first consumer path,
- do the larger Raceway JS interaction/panel/state split,
- wire route suggestion telemetry from day one.

## Deferred Work That Must Not Be Forgotten

- warning acknowledge/ignore/delete workflow,
- accessory acceptance palette and persisted accessory intent,
- vendor-grade accessory dimensions/meshes,
- riser orientation inheritance,
- detailed support automation,
- M-5 copy-run-with-offset and M-6 EL grid,
- work-plane/free-route messaging,
- service-color legend and shortcut cheat sheet,
- georeferenced precision proof,
- larger real EPC model test,
- AI gateway decision record `0007-ai_gateway` before Tier-1 AI features.

## Worktree Restart Protocol

On restart:

1. Run `git status --short`.
2. If closure/hot-standby files are still uncommitted, inspect them before
   editing.
3. Do not revert user or Claude changes.
4. Read Claude's latest note before every coding pass.
5. Update `CODEX_MEMORY.md` and the Raceway tracker after every pass.

## Manual Re-Warm Check

Before H-A1 coding after a long pause:

1. Open the Raceway viewer.
2. Confirm the Draft pane loads.
3. Draw and save one small run.
4. Refresh graph, schedule, and fittings.
5. Open `/raceway/layers/<layer_id>/clash-penalties/`.
6. Run:
   - `node --test raceway/static/raceway/js/raceway_projection_core.test.js`
   - `env USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
   - `env USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`

## Note To Future Codex

Be careful: this project has high momentum and many attractive side quests.
The first restart pass should be small, server-side, and contract-first.
Build the route preview foundation before any UI polish or AI suggestion loop.

## Note To Claude/Fable

On restart, please review this pause index and challenge whether H-A1 should
start with length-only route cost first, then H6 clash penalties second, as
recorded in §53.
