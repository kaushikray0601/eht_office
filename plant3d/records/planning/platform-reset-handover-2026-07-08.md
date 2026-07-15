# plant3d Platform Reset Handover

Date: 2026-07-08

Status: reset/handover note for a fresh development chat

Audience: KR, Codex, Claude/Fable

## Recommendation

Start a new chat after this handover.

The current chat has valuable history, but it also carries too many abandoned routing experiments: free-click cable routing, always-on Manhattan routing, Ortho/Free route editing, and direct cable-first authoring. The code and tracker have been cleaned and marked, but a fresh chat will reduce the chance that old momentum quietly steers the next phase.

Do **not** split `plant3d` into a separate repository or separate deployed service immediately. Do continue building it as an independent platform boundary inside the current Django project during Stage 0. The next clean architectural step is a peer `raceway` app that consumes `plant3d`, not full service extraction.

## One-Line Direction

`plant3d` is the neutral 3D engineering platform. EHT, raceway/tray, cable routing, cable pulling, construction management, review, and future modules consume it. They do not own its internals.

The next product direction should be **raceway/tray network first, cable assignment second**.

## What We Built

### Platform Foundation

- `plant3d` Django app exists as a neutral bounded context.
- `/plant3d/` URL boundary exists.
- Source upload, source detail, job status, package JSON, tile/blob APIs, and viewer pages exist.
- Source models are scoped by loose `project_id`, not a hard FK to EHT `ProjectData`.
- `plant3d.project_gateway` confines the current EHT-backed project access dependency to one seam.
- Source uploads are retained per user/project until explicit user deletion; saved geometry cases are explicitly marked/protected references and capped.
- Cleanup tooling exists for plant3d test/source/package data.

### Conversion And Rendering

- IFC source ingestion and IfcOpenShell-based parsing are under `plant3d.parsers`.
- GLB + sidecar package path exists.
- Spatial child tiles, `tileset.json` style manifest, tile RTC origins, coordinate transforms, and feature IDs exist.
- Viewer supports GLB packages, complete-review mode, tile/error completeness state, feature-ID picking, selected-object metadata, and runtime metrics.
- Worker command exists: `process_plant3d_job --watch`.
- Parser threading is container-aware: CPU/cgroup/memory-aware auto thread selection plus explicit caps.
- Conversion speed improved materially with parser threads on local dev hardware.

### Viewer And UX

- Three.js viewer renders plant model packages.
- Side panels, collapsible sections, object hierarchy, runtime metrics, selected-object panel, layer controls, context menu, keyboard shortcuts, grid, plot-plan overlay, and measurement tools exist.
- EHT draft tools exist in the viewer as **browser-local draft overlays**:
  - DB, JB, isolator, RTD, end termination, strap.
  - SR/MI/cold-cable draft route tools.
  - Component selection, move, delete, parameter editing, coordinate editing, hide/unhide, undo/redo.
- Draft save currently uses `localStorage`, not DB persistence.

### Route Authoring State

After several failed experiments, the current route authoring baseline is:

1. Select cable/tracer tool.
2. Select source EHT component.
3. Select destination EHT component.
4. Click ordered centerline/path points.
5. Finish route.

`Ortho Assist` remains optional. It must not silently replace user centerline intent.

## Hard Lessons Learned

### We Tried To Be Too Smart Too Early

The route tool experiments became worse when the software tried to infer too much:

- Always-on Manhattan expansion felt arbitrary.
- Nearest-segment insertion caused surprising reroutes.
- Orthogonal drag modes created confusing expectations.
- Individual point-to-point cable routing did not match real EPC practice.

The product lesson is firm:

**Do not build clever cable autorouting before a raceway/tray graph and collision/cost model exist.**

### Cable Is Usually Not The Primary Route Object

In actual EPC electrical work:

- DBs usually feed multiple JBs through shared tray/trunk routes.
- Large common trays carry many cables.
- Smaller branch trays or drops serve local destinations.
- Individual source-to-destination free-space cable routes are the exception, not the foundation.

Therefore:

- Raceway/tray/duct/trench routes should be authored first.
- Cables should be assigned to or routed through that network.
- Individual free-space cable centerlines can remain as manual exceptions and draft placeholders.

### `plant3d` Must Stay Neutral

EHT is one consumer, not the owner of the 3D platform. The same is true for raceway and future modules. Domain persistence must not be added into `plant3d` core.

### Completeness Beats Speed In Engineering Review

The viewer must not silently hide model parts. The prior tile-cap issue proved that users cannot trust an incomplete scene unless the UI says clearly what is loaded, loading, failed, or intentionally hidden.

### Current Performance Is Good Enough For The Next Architecture Step

At current 10-15 MB IFC sample scale:

- Rendering is acceptable.
- GLB/Three.js path is accepted for current scale.
- Conversion cost is mostly IfcOpenShell parsing/tessellation.
- The next major bottleneck is not another viewer micro-optimization; it is product/domain modeling.

## Current Boundaries

### `plant3d` Owns

- Source models and source files.
- Conversion jobs.
- Render packages, tiles, sidecars, feature IDs.
- Model object identity/index metadata.
- Package/source/object APIs.
- Viewer shell, reference model rendering, selection, measurement, layer registry.
- Generic overlay registration/visibility concepts.
- Coordinate/RTC/render-frame contract.

### EHT Owns

- Heat tracing engineering calculations.
- EHT-specific devices and cable/tracer data.
- Future durable EHT drawing/draft persistence.
- Electrical validation rules for EHT routes.
- EHT deliverables.

### Raceway Should Own

- Tray/ladder/trunking/duct/trench route networks.
- Raceway catalogue: family, type, width/depth, material, load/span data.
- Tray route centerlines and nodes.
- Derived tray segments, fittings, supports.
- Capacity/fill/segregation/support validation.
- Raceway BOQ and future fabrication/installation drawings.

### Future Cable Routing Should Own

- Cable assignment to raceway graph edges.
- Graph pathfinding through tray/trench/duct networks.
- Route/cost optimization.
- Cable pulling feasibility.
- Drum/cut optimization integration.

## Service Extraction Recommendation

Do not immediately extract `plant3d` into a separate repo/service.

Recommended sequence:

1. Keep `plant3d` co-located in the current Django project.
2. Keep hard boundaries: no EHT/raceway domain persistence in `plant3d`.
3. Build a peer `raceway` Django app in the same repo.
4. Make `raceway` consume `plant3d` through source/package/object/coordinate/overlay seams.
5. Add durable EHT/raceway persistence in their owner apps.
6. Extract `plant3d` into a separately deployable service only when a concrete trigger appears:
   - raceway becomes a real second consumer,
   - release cadence conflicts appear,
   - resource contention becomes real,
   - independent deployment/commercial packaging is needed,
   - auth/API token boundary is ready.

This follows decision `0005-plant3d-independent-platform-boundary.md`.

## Next Product Direction

### Pivot

Move from cable-first route drawing to raceway/tray-first design.

The first major feature after this reset should be a **Raceway MVP**:

- draw tray/raceway centerline,
- set family/type/width/depth/elevation/service,
- render simple tray geometry,
- edit/delete nodes,
- persist route-as-truth in a peer `raceway` app,
- derive initial segments/fittings/support placeholders,
- generate first BOQ/schedule,
- keep cable assignment as a later layer.

### Keep Existing Cable Tool As

- a draft/manual exception tool,
- a testbed for centerline editing primitives,
- not the main route optimization foundation.

## Long-Term Ecosystem Goal

The long-term target is a complete EPC electrical engineering ecosystem:

- Plant/model viewer and authoring substrate (`plant3d`).
- Heat tracing design and deliverables (`eht`).
- Raceway/tray/trench/duct/sleeve network authoring (`raceway`).
- Cable assignment and routing through raceway graph.
- Cable pulling tension and installation feasibility.
- Cable drum optimization and cutting plans.
- Construction cable laying management.
- Review, clash, issue tracking, scenario comparison.
- Cost optimization for cable + raceway + supports + installation.

The architecture should grow horizontally by adding consumer apps, not by making `plant3d` a domain monolith.

## Collision, Pathfinding, And Optimization Strategy

Do not build full collision/pathfinding immediately.

Staged strategy:

1. **Geometry broad phase:** bounding boxes and rough clearance warnings.
2. **Narrow phase:** BVH-backed checks, likely reusing `three-mesh-bvh`/tile spatial indices.
3. **Swept-volume checks:** sampled along route/tray centerlines for cables/tray envelopes.
4. **Graph costs:** length, bends, support count, fill %, segregation, clash risk, installability, material cost.
5. **Pathfinding:** Dijkstra on established raceway graphs; A* only when spatial graph size justifies heuristic search.
6. **Explainable suggestions:** show why a route was suggested, not just the route itself.
7. **Cost optimization:** compare material + installation cost for cable/tray/trench/duct alternatives.

Important rule:

**Routing/pathfinding suggests. The user accepts/edits. The software must not silently become the design authority.**

## Current Unfinished Work To Carry Forward

### High Priority

- Create new accepted plan/tracker from this reset.
- Decide/record raceway as peer app.
- Begin Raceway MVP.
- Keep `plant3d` core neutral.
- Build durable EHT/raceway persistence in owner modules, not `plant3d`.
- Add server-side validation before saved routes/drafts become official.

### Platform Correctness Gates

- Real plant-global/georeferenced IFC precision proof.
- Real known-dimension source-system scale validation.
- Larger real EPC file testing.
- Signed/object-storage delivery later.
- HLOD/LOD later for larger plant review.

### Viewer Structural Debt

- `package_viewer.js` is large and feature-dense. Before major new overlay modules pile in, consider splitting by concern:
  - scene/core,
  - package loading/tiles,
  - picking/selection,
  - hierarchy,
  - measurement,
  - layers,
  - EHT draft overlay,
  - future raceway overlay.

### Product Gaps

- EHT draft persistence is localStorage only.
- EHT route endpoints are snapshot anchors; live anchor re-resolution is not designed.
- SR auto-end-termination is not implemented.
- Connection-face rules are only early/basic.
- Dragging elevation/vertical changes still needs a better gizmo.
- Route math JS has smoke tests but not deep behavioral unit tests.

## Important Records

- `plant3d/records/decisions/0001-platform-architecture.md`
- `plant3d/records/decisions/0002-viewer-completeness-and-lod.md`
- `plant3d/records/decisions/0003-phase-7-rendering-spike-decision.md`
- `plant3d/records/decisions/0004-eht-overlay-integration-boundary.md`
- `plant3d/records/decisions/0005-plant3d-independent-platform-boundary.md`
- `plant3d/records/planning/public-api-boundary-contract-2026-07-05.md`
- `plant3d/records/planning/plant3d-platform-boundary-contract-2026-07-05.md`
- `plant3d/records/planning/raceway-module-architecture-2026-07-02.md`
- `plant3d/records/planning/cable-routing-vision-and-gap-analysis-2026-07-06.md`
- `plant3d/records/tracking/platform-ecosystem-reset-tracker-2026-07-08.md`

## Verification Baseline

Before this reset:

- `node --check /tmp/package_viewer.mjs` passed.
- `node --check /tmp/routing_core.mjs` passed.
- `venv/bin/python manage.py check` passed.
- focused upload/source/viewer tests passed.
- full `plant3d` suite passed: 74 tests.
- `git diff --check` clean.

## Instruction For Next Chat

Read this file first, then read:

1. `plant3d/records/tracking/platform-ecosystem-reset-tracker-2026-07-08.md`
2. `plant3d/records/planning/platform-ecosystem-development-plan-2026-07-08.md`
3. the role-specific prompt:
   - Codex: `plant3d/records/prompts/codex-platform-reset-start-prompt-2026-07-08.md`
   - Claude: `plant3d/records/prompts/claude-platform-architecture-review-prompt-2026-07-08.md`

Then continue from the new tracker, not from the older pipeline spike tracker except as history.
