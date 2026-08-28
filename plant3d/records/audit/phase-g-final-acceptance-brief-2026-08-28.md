# Phase G Final Acceptance Brief

Date: 2026-08-28  
Owner: Codex, with KR decision authority and Claude/Fable review

## Verdict

Phase G Raceway MVP implementation and closure sequence are complete enough to
start Phase H-A1 server-side routing/pathfinding foundation.

This was not a silent close of KR-owned decisions. At Closure Pass 6, the
following remained open by explicit authority boundary:

- A1: bless or amend the generic IEC/vendor-free Raceway catalogue seed.
- A2: remove/untrack or keep `plant3d/records/audit/eht_office.code-workspace`.
- A3: approve or reject the L1 CI workflow.

Those items were named in `open-items-register.md`; they were not forgotten
and were not decided by Codex.

Hot-standby update, 2026-08-29: KR explicitly closed A1 and A2. A3 remains the
open KR decision.

## What Closed

- Raceway aboveground centerline authoring.
- Server persistence for layers, runs, nodes, metadata, orientation, and face
  offsets.
- Graph projection, warnings, schedule JSON/CSV, fitting projection, and
  warning detail page.
- Accessory proxy arc for reducer candidates/proxies, plan bends, risers,
  Tee, and Cross.
- Intuitive Make Tee and Make Cross authoring.
- Save/delete synchronization regression.
- JS hardening slice: pure projection core module, command-state seam, summary
  view models, fail-loud projection validation.
- JS unit-test foundation for the extracted core module.
- Telemetry browser session key and blocked-endpoint browser assertion.
- Curated catalogue sync command, dry-run-first and explicit target only.
- Clash v0 warning system and H6 durable edge-penalty bridge.
- Markdown housekeeping inventory and lifecycle headers for stale active-looking
  records.

## What Remains Deferred

Deferred to Phase H:

- H-A1 route graph/path preview:
  - durable node-pair edge identity,
  - injectable edge weight function,
  - deterministic tie-breaking,
  - route preview payload contract pin.
- H-A2 assignment UI:
  - consumer-neutral cable reference design,
  - larger interaction/panel/state JS split,
  - route suggestion telemetry and override loop.

Deferred beyond H-A1/H-A2:

- accessory acceptance palette and persisted accessory intent,
- vendor catalogue/mesh-grade fitting dimensions,
- riser orientation inheritance where still ambiguous,
- detailed supports,
- warning acknowledge/ignore/delete workflow,
- Clash v1 spatial index/category clearance rules,
- Clash v2 mesh/BVH/narrow-phase proof,
- georeference precision proof and larger real EPC model gate.

## Phase H-A1 Start Rules

The next coding phase should begin server-side and stay contract-first:

1. Do not add route persistence in H-A1.
2. Do not create an assignment UI before the cable-reference design note.
3. Do not use graph-local `E###` keys in route payloads.
4. Route weight must be injectable from the first implementation.
5. Equal-cost route results must be deterministic.
6. Route preview JSON must be pinned in Python tests in the same pass.
7. Clash penalties may consume `raceway.clash_edge_penalties.v0` as optional
   soft route-cost hints.

## Verification Battery

Final verification should include:

- JS syntax checks for Raceway overlay/core/test files,
- `node --test` for `raceway_projection_core.test.js`,
- full `raceway` tests,
- full `plant3d` tests,
- full `telemetry` tests,
- curated catalogue sync command tests,
- full `eht` tests if runtime permits,
- full Raceway browser smoke,
- `manage.py check`,
- `makemigrations --check --dry-run`,
- `git diff --check`.

Executed final verification, 2026-08-29:

- JS syntax checks for Raceway overlay/core/test files: passed.
- `node --test raceway_projection_core.test.js`: passed.
- `raceway` Django tests: 77 passed.
- `plant3d` Django tests: 76 passed.
- `telemetry` Django tests: 5 passed.
- curated catalogue sync command tests: 6 passed.
- full `eht` Django tests: 366 passed.
- full Raceway browser smoke: 6 passed.
- `manage.py check`: passed.
- `makemigrations --check --dry-run`: passed, no changes detected.
- `py_compile` for touched Python modules: passed.
- `git diff --check`: passed.

## Manual Acceptance Check

No new visual UI is expected from Passes 5-6.

Recommended quick manual checks:

- open the Raceway viewer and confirm the Draft pane still loads,
- draw/save a small tray route,
- refresh graph/schedule/fittings,
- open `/raceway/layers/<layer_id>/clash-penalties/` and confirm the projection
  is visible,
- skim this brief, the open-items register, and the markdown housekeeping
  inventory.

## Note To Claude/Fable

Please review this as the Phase G closure candidate:

- confirm whether H-A1 may start with A1/A2/A3 carried explicitly,
- confirm whether the new `node --test` coverage justifies the §51 JS score
  bump,
- challenge the final deferred list before route preview work begins.
