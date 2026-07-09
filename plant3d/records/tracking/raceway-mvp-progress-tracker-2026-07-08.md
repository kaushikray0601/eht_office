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
- [ ] Confirm generic curated catalogue seed first.
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

- [ ] Add raceway tool palette.
- [ ] Add family selector.
- [ ] Add size selector.
- [ ] Add service class selector.
- [ ] Add elevation/working-plane control.
- [ ] Add start run mode.
- [ ] Add ordered node click placement.
- [ ] Add finish/cancel.
- [ ] Add undo last node.
- [ ] Add node handles.
- [ ] Add move node.
- [ ] Add delete node.
- [ ] Add coordinate/elevation inspector editing.
- [ ] Add live HUD length/node/bend/elevation/size/service.
- [ ] Add first warnings in HUD.

Acceptance:

- [ ] User can draw a raceway centerline.
- [ ] User can edit nodes.
- [ ] User can distinguish raceway from EHT routes.
- [ ] Existing EHT draft centerline workflow still works.

## Stage 7 - Simple Tray Geometry Preview

- [ ] Generate preview geometry from centerline.
- [ ] Apply width.
- [ ] Apply depth.
- [ ] Apply service color.
- [ ] Show bend placeholders.
- [ ] Update preview on node edit.
- [ ] Update preview on family/size edit.
- [ ] Add selected run highlight.
- [ ] Keep geometry lightweight.

Acceptance:

- [ ] Preview reads visually as tray/raceway.
- [ ] Preview is derived from route data, not independently edited parts.

## Stage 8 - Persistence Integration

- [ ] Save run from viewer to `raceway`.
- [ ] Save ordered nodes from viewer to `raceway`.
- [ ] Load saved layers/runs on viewer open.
- [ ] Handle save errors visibly.
- [ ] Preserve run after page refresh.
- [ ] Revalidate server-side on every save.
- [ ] Add browser/manual test checklist.

Acceptance:

- [ ] Draw, save, refresh, reload works.
- [ ] Unauthorized users cannot load/mutate raceway data.
- [ ] Failed save does not pretend to persist.

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
