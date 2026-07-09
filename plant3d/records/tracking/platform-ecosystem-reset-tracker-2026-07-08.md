# Platform Ecosystem Reset Tracker

Date: 2026-07-08

Status: active tracker after cable-route reset

## Current Focus

Move from cable-first authoring to raceway/tray-first engineering.

Keep `plant3d` as the neutral platform. Add domain capability through peer/consumer apps.

## Active North Star

Build a strong foundation for a full EPC electrical ecosystem:

- 3D model platform,
- raceway/tray/trench/duct/sleeve authoring,
- EHT design integration,
- cable assignment/routing,
- cable pulling and constructability,
- cable drum optimization,
- construction cable-laying management,
- review/clash/scenario workflows.

## Immediate Decisions

- [x] Treat `plant3d` as independent platform boundary during Stage 0.
- [x] Keep `plant3d` co-located in current Django project for now.
- [x] Reject always-on individual cable Manhattan routing as primary UX.
- [x] Keep cable centerline drafting only as baseline/manual exception.
- [x] Record raceway as peer app, not EHT submodule.
- [x] Confirm app name: `raceway`.
- [ ] Confirm default catalogue seed strategy: generic curated seed first.
- [x] Confirm first standard/default: IEC-first; NEMA/ANSI later.

## Phase 0 — Reset Documentation

- [x] Create platform reset handover.
- [x] Create new development plan.
- [x] Create new tracker.
- [x] Create Codex restart prompt.
- [x] Create Claude restart prompt.
- [x] Mark Claude cable-routing RFC as historical where always-on Manhattan is discussed.
- [x] Update `plant3d/records/README.md`.
- [x] Ask Claude to review reset records.

## Phase 1 — Boundary Stabilization

- [x] Loose `SourceModel.project_id` boundary implemented.
- [x] Project gateway seam implemented.
- [x] EHT overlay boundary decision exists.
- [x] Public API boundary contract exists.
- [x] Viewer layer registry exists.
- [ ] Reconfirm exported/usable layer registration contract before raceway overlay coding.
- [x] Add/confirm tests that `plant3d` imports no raceway module.
- [x] Keep route/draft persistence out of `plant3d`.

## Phase 2 — Raceway App Foundation

- [x] Add decision record for `raceway` peer app.
- [x] Create `raceway` Django app.
- [x] Register app.
- [x] Add URL namespace.
- [ ] Add app-level records folder or link to `plant3d/records` as appropriate.
- [x] Add project access helper using existing gateway/access pattern.
- [x] Add minimal tests.

Minimal schema candidates:

- [x] `RacewayLayer`
- [x] `RacewayRun`
- [x] `RacewayNode`
- [x] `RacewayFamily`
- [x] `RacewaySize`

Schema rules:

- [x] Store route centerline as truth.
- [x] Resolve durable coordinate stance: store source/world coordinates or stable anchors; derive render-frame positions for viewer use.
- [x] Reference `plant3d` package/source/object anchors loosely.
- [x] Do not FK from `plant3d` back to `raceway`.

## Phase 3 — Raceway Viewer MVP

- [ ] Add raceway overlay layer.
- [ ] Add raceway tool palette.
- [ ] Add centerline drawing.
- [ ] Add node handles.
- [ ] Add route delete/reset.
- [ ] Add elevation/working-plane UI.
- [ ] Add family/size/service controls.
- [ ] Render simple tray/ladder preview geometry.
- [ ] Add selected raceway inspector panel.

Acceptance:

- [ ] User can draw a tray centerline.
- [ ] User can edit nodes.
- [ ] User can change width/depth/service.
- [ ] User can visually distinguish raceway from plant model and EHT drafts.
- [ ] Existing plant3d package viewing remains unchanged.

## Phase 4 — Raceway Persistence

- [ ] Save raceway layer/run/node data in `raceway`.
- [ ] Load raceway data on viewer open.
- [ ] Validate project/package access.
- [ ] Add server-side payload validation.
- [ ] Keep browser localStorage only as temporary draft fallback, if still needed.

## Phase 5 — Derived Parts

- [ ] Split runs into straight segments.
- [ ] Detect bends.
- [ ] Add placeholder fitting records or derived JSON.
- [ ] Add support placeholders.
- [ ] Add first BOQ/schedule.

## Phase 6 — Collision And Validation

- [ ] Define collision warning levels:
  - info,
  - warning,
  - hard-invalid later.
- [ ] Add rough AABB warning.
- [ ] Add support span placeholder warning.
- [ ] Add fill/capacity placeholder warning.
- [ ] Add segregation placeholder warning.
- [ ] Defer BVH/narrow phase until basic route and persistence are stable.

## Phase 7 — Cable Assignment

- [ ] Define cable-to-raceway assignment shape.
- [ ] Assign one EHT/cable route to a raceway path.
- [ ] Compute route length through raceway path.
- [ ] Warn when cable is free-space-only.
- [ ] Keep routing suggestions explicit and user-accepted.

## Phase 8 — Optimization

- [ ] Define graph cost fields:
  - length,
  - bend count,
  - support count,
  - capacity/fill,
  - collision risk,
  - material cost,
  - installation cost.
- [ ] Add Dijkstra for established raceway graph.
- [ ] Add A* only if graph scale requires it.
- [ ] Add explainable route suggestions.
- [ ] Add scenario comparison.

## Carry-Forward Open Gates From Old Tracker

- [ ] Real plant-global/georeferenced IFC precision proof.
- [ ] Real source-system known-dimension proof.
- [ ] Larger real EPC model test.
- [ ] Meshopt/gltfpack measurement when available.
- [ ] Signed object-storage/CDN delivery later.
- [ ] HLOD/LOD/coarse proxy strategy later.
- [ ] `package_viewer.js` modular split before overlay complexity becomes unmanageable.
- [ ] EHT durable overlay persistence.
- [ ] Server-side EHT route validation.
- [ ] SR auto-end-termination.
- [ ] Live-vs-snapshot anchor decision.
- [ ] Connection-face rules.
- [ ] Better 3-axis/elevation editing gizmo.

## Manual Testing Baseline

For current plant3d viewer:

- [ ] Upload IFC.
- [ ] Process with `process_plant3d_job --watch --parser-threads auto`.
- [ ] Open package viewer.
- [ ] Verify model renders.
- [ ] Verify source/detail UI is simple for normal user.
- [ ] Verify EHT draft centerline routes still draw.
- [ ] Verify local draft save/restore still works.
- [ ] Verify no model completeness regression.

## Verification Commands

Use these before reporting a coding pass:

```bash
node --check /tmp/package_viewer.mjs
node --check /tmp/routing_core.mjs
venv/bin/python manage.py check
USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1
git diff --check
```

For raceway app once created:

```bash
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
```

## Notes For Next Chat

Start with `plant3d/records/planning/platform-reset-handover-2026-07-08.md`.

Then use this tracker as the active checklist.

The older `pipeline-spike-tracker-2026-06-22.md` remains useful for history and rendering/conversion context, but it is no longer the primary development tracker.
