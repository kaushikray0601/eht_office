# Platform Ecosystem Development Plan

Date: 2026-07-08

Status: active plan after cable-routing reset

Supersedes as active plan:

- the route-tool-heavy portions of `pipeline-spike-tracker-2026-06-22.md`
- the always-on Manhattan/Ortho-Free routing experiments

Retains as history:

- all Phase 1-7 rendering/conversion spike records
- all decisions `0001` through `0005`

## Strategic Decision

The next architecture/product step is not smarter individual cable routing. The next step is a **raceway/tray network authoring foundation**.

Reason:

Real EPC cable routing is shared-containment-first. Cables from a DB to multiple JBs mostly run through common trunk trays and branch trays. Designing individual radial cable routes independently creates unrealistic geometry and fights the actual engineering workflow.

## Active Architecture Shape

```text
eht        ─┐
raceway    ├──► plant3d
cable route┘
```

`plant3d` remains the shared 3D model/render/selection/coordinate platform. Domain modules consume it.

## Module Placement

### `plant3d`

Neutral 3D engineering platform:

- source intake,
- conversion,
- render packages,
- model identity,
- viewer shell,
- reference model selection,
- measurement,
- coordinate/RTC contract,
- generic overlay/layer seams.

### `eht`

Heat tracing domain:

- EHT calculations,
- EHT components,
- heat tracing routes,
- electrical rules,
- EHT drawing/draft persistence,
- deliverables.

### `raceway`

New peer app, not a child of EHT:

- tray/ladder/trunking/duct/trench route networks,
- catalogue,
- supports,
- BOQ,
- validation,
- future overlay bake/cache.

### Future `cable_routing` / integration layer

Later module:

- cable assignment to raceway graph,
- pathfinding,
- route optimization,
- cable pulling,
- cost comparison.

## Immediate Product Goal

Build a **Raceway MVP** that proves the route-first, part-later workflow:

1. User selects tray/raceway family and size.
2. User locks/uses an elevation plane.
3. User draws a centerline route.
4. Viewer previews simple tray/ladder geometry.
5. User edits nodes.
6. System derives approximate straight segments and simple bends.
7. User can save the route in a peer `raceway` app.
8. System can produce a first simple BOQ/schedule.

## Design Principles

- Route intent is the source of truth.
- Physical parts are derived.
- Do not hand-place every 3 m tray piece.
- Do not hide geometry incompleteness.
- Do not silently autoroute.
- Suggestions must be explainable and accepted by the user.
- Domain persistence stays in domain apps.
- Keep the viewer responsive; heavy validation can be staged.
- Build with extraction in mind, but do not prematurely split services.

## Phases

### Phase A — Reset And Boundary

- [x] Mark failed route experiments as superseded.
- [x] Confirm centerline-first cable route baseline.
- [x] Create reset handover.
- [x] Create new plan/tracker/prompts.
- [ ] Decide and record `raceway` as peer app.
- [ ] Update records README to point to reset tracker.
- [ ] Ask Claude for final architecture review of the reset plan.

### Phase B — Raceway App Skeleton

- [ ] Create `raceway` Django app.
- [ ] Register app and URL boundary.
- [ ] Add records folder if needed.
- [ ] Add dependency guard: `plant3d` must not import `raceway`.
- [ ] Add project scoping using the current gateway/access pattern.
- [ ] Keep DB schema narrow and additive.

Initial models, minimal:

- [ ] `RacewayLayer`
- [ ] `RacewayRun`
- [ ] `RacewayNode`
- [ ] `RacewayCatalogueFamily`
- [ ] `RacewaySize`

Deferred:

- detailed supports,
- fittings library,
- vendor catalogue,
- drawing output,
- cable assignments.

### Phase C — Viewer Overlay Contract

- [ ] Confirm `window.plant3dViewerLayers` exposes enough hooks for external overlays.
- [ ] If needed, add a small viewer extension seam for consumer modules.
- [ ] Do not add raceway persistence to `plant3d`.
- [ ] Add a raceway overlay group and visibility layer.
- [ ] Keep geometry in the same render frame/RTC convention as the active package.

### Phase D — Raceway Authoring MVP

- [ ] Add tray/raceway tool palette.
- [ ] Add centerline drawing mode for raceway runs.
- [ ] Add node handles and delete/move behavior.
- [ ] Add elevation/working-plane control.
- [ ] Add basic width/depth/family/service properties.
- [ ] Render simple parametric tray geometry from centerline.
- [ ] Use color by service/class/status.
- [ ] Show live route HUD: length, elevation, width, bend count.

### Phase E — Persistence

- [ ] Save raceway layer/run/node data in `raceway`.
- [ ] Load saved raceway runs into the `plant3d` viewer.
- [ ] Keep source/package/object anchor references stable and loose.
- [ ] Add server-side validation for payload shape and project access.
- [ ] Keep render cache/GLB bake deferred until route editing is proven.

### Phase F — Derived Parts And BOQ

- [ ] Split centerline into straight segments.
- [ ] Identify simple bends.
- [ ] Add placeholder fitting derivation.
- [ ] Add manual support placeholders.
- [ ] Generate first BOQ:
  - tray length by family/size,
  - fitting count,
  - support count placeholder,
  - route length.

### Phase G — Validation And Collision

Start with warnings, not hard stops.

- [ ] Bounding-box rough clash warnings.
- [ ] Clearance/penetration warning vocabulary.
- [ ] Support span warnings.
- [ ] Fill/capacity placeholder.
- [ ] Segregation placeholder.
- [ ] BVH/narrow phase later.
- [ ] Swept-volume route checks later.

### Phase H — Cable Assignment

After raceway graph exists:

- [ ] Assign cable/tracer route to raceway run/path.
- [ ] Compute cable length through raceway graph.
- [ ] Compute fill.
- [ ] Warn when free-space cable route is used as exception.
- [ ] Add Dijkstra on raceway graph.
- [ ] Add A* only if graph/search scale demands it.

### Phase I — Cost And Optimization

Later:

- [ ] Material cost for tray/cable/support.
- [ ] Installation cost assumptions.
- [ ] Cost-weighted route comparison.
- [ ] Explainable route suggestions.
- [ ] Scenario comparison.
- [ ] Cable pulling tension.
- [ ] Drum optimization integration.

## Do Not Do Yet

- Do not extract `plant3d` to a separate repo immediately.
- Do not add full Celery/Redis just for this reset.
- Do not build full automatic cable autorouting.
- Do not build hard collision physics before warning layers.
- Do not add EHT/raceway domain tables to `plant3d`.
- Do not build drafting-grade DXF/fabrication drawings in the first raceway MVP.

## Service Extraction Position

Continue as co-located modular monolith for now.

Prepare for service extraction by:

- keeping project refs loose,
- keeping stable APIs/contracts,
- keeping owner modules separate,
- using object/source/package anchors,
- avoiding direct cross-module persistence coupling.

Extraction trigger:

- real second consumer (`raceway`) matures,
- deployment/release cadence requires it,
- resource contention requires it,
- API/auth boundary is ready.

## Claude/Fable Role

Claude should:

- audit architectural boundaries,
- review raceway model placement,
- research standards and catalog assumptions,
- review collision/pathfinding staging,
- challenge over-smart UX,
- help write help/user manual/design docs while Codex codes,
- perform targeted code reviews after passes.

## Codex Role

Codex should:

- code conservatively,
- keep records updated,
- avoid silent pivots,
- ask before following Claude into a major direction change,
- run tests/checks,
- keep `plant3d` neutral,
- prioritize raceway MVP over further cable-route cleverness.

## First Recommended Next Coding Pass

1. Add decision record: `raceway` as peer app consuming `plant3d`.
2. Create minimal `raceway` Django app skeleton.
3. Add basic model plan/migration for layer/run/node/catalogue seed only if safe.
4. Add tests proving no `plant3d -> raceway` import.
5. Add tracker checkpoint.

If that feels too much for one pass, split:

- pass 1: decision + app skeleton + import guard,
- pass 2: minimal models + admin/basic views/API,
- pass 3: viewer overlay/authoring.
