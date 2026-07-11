# Raceway MVP Progress Tracker

Date: 2026-07-08

Status: active detailed tracker

Plan: `../planning/raceway-mvp-execution-plan-2026-07-08.md`

North star: build the first raceway/tray-first foundation as a peer consumer of
`plant3d`, with route intent as truth and derived tray parts/BOQ growing from
that foundation.

## Status Legend

- `[ ]` not started
- `[~]` in progress
- `[x]` complete
- `[!]` blocked / needs KR decision
- `[?]` needs review

## Current Pass

- [x] Create detailed execution plan and tracker.
- [x] Add raceway peer-app decision record.
- [x] Scaffold minimal raceway app and URL boundary.
- [x] Add import-boundary and skeleton tests.
- [x] Run Stage 1 verification commands.
- [x] Read Claude/Fable reset architecture review notes.
- [x] Add raceway project-scope helper.
- [x] Add accessible/inaccessible project access tests.
- [x] Run Stage 2 verification commands.
- [x] Add minimal raceway domain schema.
- [x] Generate initial raceway migration.
- [x] Add schema tests.
- [x] Run Stage 3 verification commands.
- [x] Apply Claude §10 corrections before API work.
- [x] Add raceway layer/run/node JSON endpoints.
- [x] Add Stage 4 API tests.
- [x] Run Stage 4 verification commands.

## Decisions

- [x] Keep `plant3d` as neutral co-located platform during Stage 0.
- [x] Keep EHT and future modules as consumers of `plant3d`.
- [x] Reject cable-first always-on Manhattan routing as primary direction.
- [x] Treat existing cable centerline drafting as manual/draft exception tooling.
- [x] Use IEC-first direction for MVP target markets: Middle East, Asia, Europe.
- [x] Prioritize aboveground tray/ladder/sleeve MVP; defer underground trench
  and duct-bank work.
- [x] Treat future lighting design like EHT: a consumer of `plant3d`, not part
  of `plant3d` core.
- [x] Record `raceway` as peer app in decisions folder.
- [x] Confirm app name: `raceway`.
- [x] Implement initial generic curated catalogue seed first; keep rows
  vendor-free and `is_validated=False` until KR-reviewed source data exists.
- [x] Choose initial standards/default stance: IEC-first; NEMA/ANSI later.
- [ ] Confirm BOQ-first before DXF/fabrication drawings.
- [x] Resolve coordinate-frame contract stance: durable source/world metres or
  stable anchors; render-frame derived for viewer.

## Boundary Guardrails

- [x] `plant3d` has no runtime import of `raceway`.
- [x] `raceway` has no direct import of `eht.models`.
- [x] `raceway` uses loose `project_id`, not FK to `eht.ProjectData`.
- [x] Raceway persistence is outside `plant3d`.
- [x] Durable raceway coordinates use source/world coordinates or model-object
  anchors, with source/package context.
- [x] Render-frame positions are derived through `plant3d` coordinate/RTC
  contract, not stored as durable truth.
- [x] Route centerline is stored as truth.
- [ ] Derived segments/fittings/supports remain regenerable.
- [ ] Cable pathfinding is deferred until raceway graph exists.
- [ ] Collision starts as warnings/previews, not hard authority.

## Stage 0 - Reset Closure And Decision

- [x] Platform reset handover exists.
- [x] Ecosystem development plan exists.
- [x] Platform ecosystem reset tracker exists.
- [x] Codex restart prompt exists.
- [x] Claude restart prompt exists.
- [x] Codex local memory updated for plant3d reset.
- [x] Detailed raceway MVP execution plan created.
- [x] Detailed raceway MVP progress tracker created.
- [x] Records README links detailed plan and tracker.
- [x] KR decisions recorded: IEC-first, aboveground first, future consumers
  remain peer consumers of `plant3d`.
- [x] Decision record created: `raceway` as peer app.
- [x] Claude/Fable review requested.
- [x] Claude/Fable review findings recorded.

Acceptance:

- [x] All reset records point to the same direction.
- [x] No conflicting active tracker remains.
- [x] KR has a clear next-pass coding target.

Verification:

- [x] `git diff --check`

## Stage 1 - Raceway App Skeleton

- [x] Create Django app `raceway`.
- [x] Add `raceway/apps.py` with `RacewayConfig`.
- [x] Add `raceway/urls.py`.
- [x] Add minimal view/API health endpoint.
- [x] Register app in `ELECSENSE/settings.py`.
- [x] Include `raceway/` in `ELECSENSE/urls.py`.
- [x] Add `raceway/tests.py` or test package.
- [x] Test app URL boundary.
- [x] Test `plant3d` runtime modules do not import `raceway`.
- [x] Test `raceway` does not import EHT models directly.
- [x] Update records after pass.

Acceptance:

- [x] `venv/bin/python manage.py check` passes.
- [x] `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1` passes.
- [x] `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passes.

Notes:

- Defer schema if the app skeleton pass is already large.

## Stage 2 - Project Scope And Access

- [x] Add raceway project-scope helper.
- [x] Reuse `plant3d.project_gateway` for Stage 0 access.
- [x] Add accessible project test.
- [x] Add inaccessible project test.
- [x] Add no-direct-EHT-import guard.
- [x] Document Stage 0 adapter/future token/API direction.

Acceptance:

- [x] Raceway can validate project ids.
- [x] Raceway queries are project-scoped.
- [x] Raceway has no hard FK or direct import dependency on EHT project models.

## Stage 3 - Minimal Domain Schema

- [x] Define `RacewayLayer`.
- [x] Define `RacewayFamily`.
- [x] Define `RacewaySize`.
- [x] Define `RacewayRun`.
- [x] Define `RacewayNode`.
- [x] Add model validation/clean methods where useful.
- [x] Add admin registrations if helpful for inspection.
- [x] Generate migration.
- [x] Add model tests.
- [x] Add project-scope query tests.
- [x] Update records after pass.

Schema acceptance:

- [x] Route centerline can be stored as ordered nodes.
- [x] Family/size can be assigned to a run.
- [x] Service class/status can be assigned to a run.
- [x] Source/package context can be stored.
- [x] Source/world or anchor coordinates can be stored.
- [x] Render-frame coordinates are derived or cached only, not durable truth.
- [x] Node coordinates are finite and ordered.
- [x] No `plant3d` model has FK/import back to `raceway`.

Deferred:

- [ ] Underground trench/duct-bank scope.
- [ ] Supports.
- [ ] Detailed fittings.
- [ ] Vendor catalogue.
- [ ] Cable assignment.
- [ ] GLB overlay cache.

## Stage 4 - Raceway JSON API

- [x] List layers for project/package context.
- [x] Create/update/delete layer.
- [x] List runs.
- [x] Create/update/delete run.
- [x] Replace ordered node list.
- [x] Validate project access.
- [x] Validate package/source access where provided.
- [x] Validate coordinate frame.
- [x] Validate finite XYZ.
- [x] Validate family/size/service.
- [x] Add unauthorized access tests.
- [x] Add invalid payload tests.
- [x] Add successful save/reload tests.

Acceptance:

- [x] A run can be saved and loaded through JSON.
- [x] Bad payloads fail cleanly.
- [x] Private implementation fields are not exposed.

## Stage 5 - Viewer Extension Seam

- [x] Confirm current layer registry is sufficient.
- [x] Add external consumer script hook if required.
- [x] Add raceway script placeholder/include.
- [x] Register `raceway-overlay` layer.
- [x] Confirm layer controls show/hide raceway overlay.
- [x] Confirm EHT draft layer behavior unchanged.
- [x] Confirm measurement/grid/plot plan behavior unchanged.
- [x] Add JS smoke/static tests.

Acceptance:

- [x] Raceways can render in a separate overlay group.
- [x] Viewer remains a `plant3d` host, not raceway-owned.

## Stage 6 - Centerline Authoring MVP

- [x] Add raceway tool palette.
- [x] Add family selector.
- [x] Add size selector.
- [x] Add service class selector.
- [x] Add elevation/working-plane control.
- [x] Add start run mode.
- [x] Add ordered node click placement.
- [x] Add finish/cancel.
- [x] Add undo last node.
- [x] Add node handles.
- [x] Add move node.
- [x] Add delete node.
- [x] Add coordinate/elevation inspector editing.
- [x] Add live HUD length/node/bend/elevation/size/service.
- [x] Add first warnings in HUD.

Acceptance:

- [x] User can draw a raceway centerline.
- [x] User can edit nodes.
- [x] User can distinguish raceway from EHT routes.
- [x] Existing EHT draft centerline workflow still works.

## Stage 7 - Simple Tray Geometry Preview

- [x] Generate preview geometry from centerline.
- [x] Apply width.
- [x] Apply depth.
- [x] Apply service color.
- [x] Show bend placeholders.
- [x] Update preview on node edit.
- [x] Update preview on family/size edit.
- [x] Add selected run highlight.
- [x] Keep geometry lightweight.

Acceptance:

- [x] Preview reads visually as tray/raceway.
- [x] Preview is derived from route data, not independently edited parts.

## Stage 8 - Persistence Integration

- [x] Save run from viewer to `raceway`.
- [x] Save ordered nodes from viewer to `raceway`.
- [x] Load saved layers/runs on viewer open.
- [x] Handle save errors visibly.
- [x] Preserve run after page refresh.
- [x] Revalidate server-side on every save.
- [x] Add browser/manual test checklist.

Acceptance:

- [x] Draw, save, refresh, reload works.
- [x] Unauthorized users cannot load/mutate raceway data.
- [x] Failed save does not pretend to persist.

## Stage 9 - Derived Parts And BOQ v0

- [ ] Split run into straight segment lengths.
- [ ] Detect bend nodes.
- [ ] Count route length by family/size/service.
- [ ] Add placeholder fitting count.
- [ ] Add placeholder support count using simple span rule.
- [ ] Add schedule JSON endpoint.
- [ ] Add schedule HTML or CSV output.
- [ ] Add tests for length and counts.
- [ ] Document placeholder assumptions.

Acceptance:

- [ ] User can produce a simple raceway schedule.
- [ ] Quantities are traceable to run/node ids.
- [ ] Placeholder basis is visible.

## Stage 10 - Warning Layer

- [ ] Define warning payload shape.
- [ ] Add too-few-nodes warning.
- [ ] Add short-segment warning.
- [ ] Add excessive-bend warning.
- [ ] Add unsupported-span placeholder warning.
- [ ] Add missing family/size/service warning.
- [ ] Add unknown coordinate context warning.
- [ ] Add inspector warning display.
- [ ] Add schedule/export warning evidence.
- [ ] Defer hard clash constraints.

Acceptance:

- [ ] Warnings appear before save and after reload.
- [ ] Only invalid payload/access blocks persistence.
- [ ] Warning vocabulary can grow to fill/segregation/clash.

## Deferred Backlog

- [ ] Underground trench and duct-bank modelling.
- [ ] Auto-support anchoring to structural model objects.
- [ ] Detailed support records.
- [ ] Detailed fitting records.
- [ ] Vendor part mapping and validation workflow.
- [ ] Server-baked GLB overlay cache.
- [ ] BVH/narrow-phase clash.
- [ ] Fill/capacity from assigned cables.
- [ ] Cable assignment to raceway graph.
- [ ] Dijkstra on raceway graph.
- [ ] A* only if graph/search scale demands it.
- [ ] Explainable route suggestions.
- [ ] Cable pulling tension.
- [ ] Drum/cut optimization.
- [ ] DXF layout drawings.
- [ ] Support fabrication sheets.
- [ ] Multi-user collaboration.

## Open Questions

- [ ] KR: exact generic catalogue seed?
- [ ] KR: BOQ-first is sufficient before drawings?
- [ ] KR/Codex/Claude: exact source/world coordinate and anchor payload shape.
- [ ] Claude/Fable: minimal schema review.
- [ ] Claude/Fable: collision/pathfinding staging review.
- [ ] Claude/Fable: UX risk review for over-smart routing.

## Verification Log

Append each pass here.

### 2026-07-08 - Tracker Creation

- Created detailed plan and tracker.
- No code changes.
- Updated records README to link the detailed files.
- Folded in KR alignment from Claude discussion: IEC-first, aboveground-first,
  and future consumers remain peer consumers of `plant3d`.
- Resolved active-plan coordinate stance toward durable source/world or anchor
  coordinates, with render-frame positions derived for the viewer.
- Verification passed: `git diff --check`.

### 2026-07-08 - Raceway Peer App Skeleton

- Read Claude/Fable architecture review notes.
- Added `0006-raceway-peer-app.md`.
- Created minimal `raceway` app, URL boundary, authenticated JSON home view,
  and skeleton/boundary tests.
- Registered `raceway` in settings and root URLs.
- Deferred models/schema until coordinate and anchor payload shape is settled.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`

### 2026-07-08 - Raceway Project Scope Helper

- Added `raceway/access.py` as the Stage 0 project access seam.
- Reused `plant3d.project_gateway` for accessible project ids and validation.
- Added access tests for accessible and inaccessible projects.
- Kept direct EHT model imports out of raceway runtime modules.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`

### 2026-07-08 - Minimal Raceway Schema

- Added `RacewayFamily`, `RacewaySize`, `RacewayLayer`, `RacewayRun`, and
  `RacewayNode`.
- Added stable UUID keys on runs and nodes.
- Added source/world metre coordinate fields on nodes and source/package loose
  context ids on layers/runs.
- Added admin registrations for inspection.
- Generated `raceway/migrations/0001_initial.py`.
- Added model tests for IEC defaults, loose references, source coordinates,
  stable keys, frame validation, node coordinate validation, uniqueness, and no
  FK to `plant3d`/`eht`.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`

### 2026-07-08 - Raceway JSON API Slice

- Read Claude §10 and applied pre-API corrections:
  - added UUID keys to the execution-plan Stage 3 field list,
  - broadened the no-direct-EHT import guard,
  - removed persisted node render-frame cache.
- Added JSON endpoints for layers, runs, and ordered node replacement.
- Added project access validation through `raceway/access.py`.
- Added source/package access validation through `plant3d.access`.
- Added server-side payload validation for family/size, coordinate frame, finite
  node coordinates, metadata object shape, and unique node sequences.
- Added API tests for create/list/update/delete, unauthorized access, invalid
  source context, family/size mismatch, invalid node coordinates, and response
  payload hygiene.
- Verification passed:
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`

### 2026-07-09 - Viewer Extension Seam

- Addressed Claude F-03/F-04 before overlay authoring:
  - Plant3D viewer now loads configured extensions from
    `PLANT3D_VIEWER_EXTENSIONS` without importing or naming peer apps in
    `plant3d` code.
  - `package_viewer.js` can create an extension-owned overlay group through
    `window.plant3dViewerLayers.register({createGroup: true})`.
  - The viewer emits `plant3dviewer:layers-ready` for peer modules.
  - Raceway overlay code was born in
    `raceway/static/raceway/js/raceway_overlay.js`, not inside the Plant3D
    viewer monolith.
  - `raceway-overlay` registers as owner `raceway` and is controlled through
    the existing layer controls.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `node --check /tmp/package_viewer.mjs`
  - `node --check /tmp/raceway_overlay.mjs`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`

### 2026-07-09 - Raceway Centerline Authoring Attempt Reverted

- Manual check by KR found the first Stage 6 authoring attempt was not usable:
  Start created a draft row, but viewer clicks and node commands did not work
  reliably.
- Reverted the Stage 6 authoring code and its generic runtime API back to the
  stable Stage 5 viewer-extension placeholder.
- Kept the proven Stage 5 seam:
  - settings-driven extension script loading,
  - `window.plant3dViewerLayers.register({createGroup: true})`,
  - `plant3dviewer:layers-ready`,
  - `raceway-overlay` registered by `raceway/static/raceway/js/raceway_overlay.js`.
- Lesson for next Stage 6 pass: design the extension interaction contract first
  and browser-smoke-test actual canvas clicks before marking authoring complete.

### 2026-07-09 - Raceway Centerline Authoring Redo

- Rebuilt Stage 6 on an explicit viewer-extension interaction contract instead
  of direct canvas interception:
  - `window.plant3dViewerRuntime`,
  - `plant3dviewer:runtime-ready`,
  - `registerInteraction`,
  - source/render coordinate conversion helpers,
  - source-elevation plane picking.
- Fixed the missing-layer risk by refreshing layer controls after external
  layer register/update and bumping the raceway static script version to
  `20260709_raceway2`.
- Reintroduced `raceway/static/raceway/js/raceway_overlay.js` authoring:
  - RaceWay Draft panel,
  - family/size/service/elevation controls,
  - start/finish/cancel/undo,
  - click-to-place ordered nodes,
  - node list selection, move/delete, and numeric coordinate edits,
  - simple 3D line/handle preview in the raceway overlay group.
- Added `raceway/browser_tests.py`, an opt-in Playwright smoke test with a
  stubbed viewer host. It loads the real raceway script, registers the layer,
  clicks the canvas, creates nodes, undoes a node, moves a selected node, and
  deletes it.
- Recorded the geometry strategy in the execution plan: proxy tray/ladder
  geometry is derived from centerline/catalogue dimensions; vendor meshes are
  later optional catalogue assets, not durable truth.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `node --check /tmp/package_viewer.mjs`
  - `node --check /tmp/raceway_overlay.mjs`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`

### 2026-07-09 - Raceway Viewer Root-Cause Fix

- KR reported the 3D view disappeared and Reference Layers showed only
  `Raceway`.
- Root cause: the viewer runtime host was published too early in
  `package_viewer.js`, before the core viewer had completed built-in layer
  registration and before later runtime state was initialized. That created an
  unsafe extension load-order surface where raceway could initialize against a
  half-formed host.
- Fix:
  - removed early `plant3dviewer:*` event dispatch,
  - added `publishViewerExtensionHost()` after core layer registration and
    viewer setup,
  - kept layer-control refresh after external layer registration,
  - bumped host script cache to `20260709_raceway_runtime1`,
  - bumped raceway extension cache to `20260709_raceway3`.
- Strengthened `raceway/browser_tests.py` so it seeds existing core layers and
  asserts `model`, `measurement`, `eht-draft`, and `raceway-overlay` coexist
  after loading the real raceway script.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `node --check /tmp/package_viewer.mjs`
  - `node --check /tmp/raceway_overlay.mjs`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`

### 2026-07-09 - Simple Tray Geometry Preview

- Completed Stage 7 as a derived proxy, not persisted mesh:
  - side rails from `widthMm`,
  - lower edges/depth ticks from `depthMm`,
  - ladder rungs for `LADDER-HDG`,
  - tray cross-members for `PERF-HDG`,
  - bend placeholders at intermediate nodes,
  - service-class color,
  - selected-run centerline highlight and node handles.
- Active run preview updates on:
  - node add/move/delete/coordinate edit,
  - family change,
  - size change,
  - service change,
  - elevation-plane shift.
- Bumped raceway extension cache to `20260709_raceway4`.
- Strengthened `raceway.browser_tests` to verify generated preview kinds
  (`side-rail`, `rung`, `bend-placeholder`, `node-handle`) and live size/service
  updates.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `node --check /tmp/package_viewer.mjs`
  - `node --check /tmp/raceway_overlay.mjs`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`

### 2026-07-09 - Raceway Persistence Integration

- Completed Stage 8 persistence integration:
  - added generic IEC-flavored, vendor-free catalogue seed migration
    `raceway.0002_seed_generic_catalog` for `LADDER-HDG` and `PERF-HDG`
    sizes already used by the Stage 7 proxy UI,
  - added `GET /raceway/catalog/`,
  - made the viewer fetch catalogue rows from the server instead of trusting
    hardcoded JavaScript IDs,
  - exposed package `project_id` in Plant3D package JSON,
  - ensured the Plant3D package viewer sets a CSRF cookie for Raceway AJAX
    saves,
  - added `plant3dviewer:package-loaded`,
  - added single-active-canvas-tool arbitration so Measure/EHT/Raceway do not
    silently steal each other's clicks,
  - added `Save Draft` and `Reload Saved` controls to the Raceway panel,
  - saved runs and ordered source-frame nodes through the `raceway` JSON API,
  - loaded saved runs/nodes on viewer open and after refresh,
  - kept persisted geometry as source-frame centreline nodes; tray/ladder proxy
    geometry remains derived/regenerable.
- Added browser coverage for both sides of Stage 8:
  - synthetic extension-host smoke still checks layer coexistence, draw/edit,
    generated proxy kinds, and mocked save payloads,
  - real live-server smoke opens the actual Plant3D viewer, draws on the real
    canvas, saves through Django, reloads the page, and confirms the saved
    Raceway run returns.
- Applied local development migrations:
  - `venv/bin/python manage.py migrate raceway`
- Verification passed:
  - `venv/bin/python manage.py check`
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `node --check /tmp/package_viewer_stage8.mjs`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`
  - `git diff --check`

### 2026-07-09 - Plant Model Anchor Bridge

- Addressed Claude N-04 before deeper 3D/collision work:
  - `raceway` run payloads now embed authoritative family and size details
    (`family.code`, `family.kind`, `size.width_mm`, `size.depth_mm`) from the
    saved FK rows,
  - the viewer uses those saved dimensions when reloading runs, instead of
    guessing from the currently-active catalogue palette.
- Added the first practical link from Raceway nodes to Plant3D model geometry:
  - `package_viewer.js` exposes `getSelectedModelAnchor()` through the generic
    viewer runtime,
  - Raceway panel adds `Anchor Node` and `Clear Anchor`,
  - anchoring uses the currently selected Plant3D object, stores its stable
    object references in the node `anchor`, and places the Raceway node at the
    object's source XY center while preserving the active tray elevation,
  - saved nodes persist/reload anchor metadata through the existing Raceway
    node API.
- Bumped browser cache keys:
  - Plant3D viewer host: `20260709_raceway_runtime3`,
  - Raceway overlay: `20260709_raceway6`.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `node --check /tmp/package_viewer_anchor.mjs`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`

### 2026-07-09 - Raceway Anchor Elevation Fix

- KR found `Anchor Node` preserved the Raceway elevation field, so anchored
  nodes could remain at `0.000 m` even when the selected Plant3D model point was
  higher.
- Corrected anchor behavior:
  - Plant3D runtime now records the actual selected model hit point in
    source-frame metres where available,
  - hierarchy-only model selections still fall back to source bounds center,
  - Raceway anchoring now adopts the anchor source `z` and shifts the active
    run's working elevation to that value,
  - the selected node is moved to the selected model source point instead of
    only its XY at the previous Raceway elevation.
- Bumped browser cache keys:
  - Plant3D viewer host: `20260709_raceway_runtime4`,
  - Raceway overlay: `20260709_raceway7`.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `node --check /tmp/package_viewer_anchor_fix.mjs`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-10 - Raceway Usability and Anchor Contract Pass

- Addressed the next usability slice after KR confirmed node anchoring works:
  - run rows and the active-run summary now show `unsaved`, `unsaved changes`,
    or `saved`,
  - invalid actions are disabled instead of appearing clickable with no effect,
  - `Reload Saved` asks for confirmation before discarding local unsaved runs
    or dirty saved runs,
  - `Delete Run` is exposed in the Raceway panel and calls the existing
    `DELETE /raceway/runs/<id>/` API for saved runs,
  - multi-run save failures now report the failing run tag.
- Fixed the visual proxy orientation noted by KR:
  - the authored source elevation is now treated as the tray/ladder bottom
    reference plane,
  - depth ticks and side rails extend upward from that plane, so the raceway
    reads as open/facing sky instead of inverted toward ground.
- Folded in Claude §15 anchor findings while the anchor code was fresh:
  - added `plant3d/overlay.py::validate_overlay_anchor`,
  - `raceway.views` validates persisted node anchors against allowed keys,
    `stable_id`, source-model consistency, and source-frame point shape,
  - `raceway_overlay.js` sanitizes anchors before save and strips package-local
    `feature_id`,
  - persisted anchors now use `owner_module: raceway`; Plant3D remains the
    provider of the selected anchor snapshot.
- Bumped raceway overlay cache to `20260710_raceway8`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-10 - Raceway Node Selection and Navigation-Safe Authoring

- Addressed KR's manual observations from the Raceway UI pass:
  - canvas node selection was not active/reliable, so users could not choose
    the intended node before moving it,
  - orbit/pan-style scene movement could still end as a Raceway click commit.
- Strengthened the generic Plant3D extension interaction contract:
  - added `raycastObjectsFromViewerEvent(event, objects, recursive)` to the
    runtime helper surface so extensions can pick their own handles without
    touching raw raycaster/camera internals,
  - added `shouldIgnoreViewerCommitClick()` in the host click dispatch path so
    active extensions do not receive commit clicks after navigation drags,
  - extensions can now receive `onNavigationClick` to show a tool-specific
    status message when a drag was intentionally ignored.
- Improved Raceway node interaction:
  - added `Select Node` command,
  - finished/selected runs now stay in lightweight selection mode,
  - node handles have invisible pick targets (`node-hit-target`) around the
    visible spheres,
  - Raceway first tries host raycasting, then falls back to a tolerant
    screen-sized source-elevation plane pick,
  - clicks on node handles select the exact run/node and keep misses falling
    through to normal Plant3D model selection.
- Bumped browser cache keys:
  - Plant3D viewer host: `20260710_raceway_runtime5`,
  - Raceway overlay: `20260710_raceway9`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `node --check /tmp/package_viewer_interaction.mjs`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-11 - Raceway Surface-Click and Multi-Elevation Authoring

- Addressed KR's next manual observations:
  - continuing a run after navigating the plant should feel like continuation,
    not a select-and-move workaround,
  - Raceway nodes need to be placeable at the actual clicked structure
    elevation, not only the starting horizontal plane,
  - a structure click should auto-anchor the node instead of requiring a
    separate `Anchor Node` button click,
  - horizontal bends and elevation risers need explicit vocabulary for later
    fitting/accessory generation.
- Extended the Plant3D runtime helper surface:
  - added `modelAnchorFromViewerEvent(event)` to return a model anchor at the
    actual clicked source-frame model point when visible model geometry is hit.
- Improved Raceway authoring:
  - draw/move clicks now try model-surface anchoring first and fall back to the
    current working elevation plane only on miss,
  - nodes may now keep distinct `z` values, enabling sloped/riser segments,
  - the `Anchor Node` button remains available, but normal structure clicks no
    longer require it,
  - added `Continue` to re-enter append mode on the active run after finishing
    or selecting,
  - navigation gestures in draw mode show a continuation status and keep the
    command armed for the next clean click.
- Added bend/riser classification:
  - summary/run rows now distinguish horizontal `bends` from elevation
    `risers`,
  - riser segments get a simple `riser-placeholder` proxy marker,
  - the old "off plane" warning was removed because multi-elevation runs are
    now intentional.
- Added `plant3d/records/planning/viewer-extension-contract-2026-07-11.md`
  documenting current helpers, interaction callbacks, provisional raw
  internals, and reserved future additions for surface normals and pointer
  move routing.
- Bumped browser cache keys:
  - Plant3D viewer host: `20260711_raceway_runtime6`,
  - Raceway overlay: `20260711_raceway10`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `node --check /tmp/package_viewer_surface_anchor.mjs`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
