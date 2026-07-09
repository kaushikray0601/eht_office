# Decision 0006 - Raceway Peer App

Date: 2026-07-08

Status: accepted for Stage 0 implementation

## Context

The platform reset moved the active product direction away from individual
cable-first autorouting and toward shared containment first. In real EPC
electrical work, cables are usually assigned to raceway/tray/trunk networks
rather than routed as independent free-space paths.

`plant3d` is now a neutral 3D engineering platform boundary. EHT consumes it
today, and future modules such as raceway, cable routing, lighting design,
construction review, and other engineering workflows should consume it through
stable anchors and APIs.

Claude/Fable's 2026-07-08 review endorsed the direction and identified several
day-one guardrails:

- persist durable geometry in source/world coordinates or stable anchors, not
  package-RTC render coordinates as the only truth,
- use loose references to `plant3d` objects rather than Django FKs into
  `plant3d`,
- avoid direct `eht` imports from `raceway`,
- keep cable assignment consumer-neutral,
- keep all raceway JavaScript outside the large `plant3d` viewer module when
  viewer work begins.

KR confirmed:

- IEC-first target markets: Middle East, Asia, Europe; NEMA/ANSI later,
- aboveground tray/ladder/sleeve first; underground trench/duct-bank later,
- EHT is only one consumer of `plant3d`; lighting design and other future
  modules must follow the same peer-consumer pattern.

## Decision

Create `raceway` as a peer Django app in the current repository during Stage 0.

`raceway` consumes `plant3d`; `plant3d` does not import `raceway`.

`raceway` is not an EHT submodule. It must not import EHT models directly and
must not use EHT-specific vocabulary or foreign keys in its core domain model.

The MVP scope is aboveground raceway/tray/ladder/sleeve authoring. Underground
trench and duct-bank modelling are deferred until the aboveground MVP and
integration shape are proven.

The default standard direction for seed data and terminology is IEC-first.
NEMA/ANSI support is deferred and should enter later as configurable catalogue
or project policy, not as an MVP assumption.

## Stage 0 Scope

Accepted first actions:

- scaffold a minimal `raceway` app and URL boundary,
- add dependency-boundary tests,
- reuse the existing `plant3d.project_gateway` seam for project access during
  co-located Stage 0,
- keep schema deferred or minimal until the coordinate payload and anchor shape
  are settled.

When schema begins:

- use loose `project_id`, `source_model_id`, `render_package_id`, and
  `stable_id` references,
- use UUID-style stable keys on runs and nodes from day one,
- store source/world coordinates in metres or explicit model-object anchors as
  durable truth,
- derive render-frame coordinates through the `plant3d` coordinate/RTC contract
  for viewer display,
- use FKs only inside `raceway` ownership boundaries, such as run-to-layer and
  node-to-run.

## Consequences

- `raceway` becomes the first real second consumer that proves the `plant3d`
  platform boundary.
- `plant3d` remains neutral and extractable later.
- EHT calculation and persistence logic remain untouched by raceway work.
- Cable assignment/pathfinding waits until a raceway graph exists.
- Raceway viewer code must be born in raceway-owned static files or a generic
  viewer extension seam, not added directly to the monolithic
  `package_viewer.js`.

## Deferred

- underground trench and duct-bank modelling,
- detailed supports and fittings,
- vendor catalogue and vendor part validation,
- cable assignment to raceway graph,
- Dijkstra/A* pathfinding,
- server-baked GLB overlay caches,
- drafting-grade DXF/fabrication drawings,
- hard collision constraints.
