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
- [x] Apply Claude §26 guidance before clash work.
- [x] Consolidate duplicated raceway geometry helpers.
- [x] Add rough Plant3D object AABB clash/clearance warnings.
- [x] Include schedule warnings in Raceway telemetry lifecycle events.
- [x] Run clash-warning verification commands.
- [x] Close Claude N-13 by moving Plant3D object-bounds lookup behind a
  Plant3D overlay seam.
- [x] Add clickable schedule-warning navigation to affected Raceway
  run/node/segment.
- [x] Move source-detail conversion progress visibility below the primary 3D
  model action.
- [x] Close Claude N-14 by making the Plant3D extension cache-key test
  settings-driven.
- [x] Add compact Raceway pane summary for the fitting/accessory projection.
- [x] Review deferred stock against Claude §28 and keep open items visible.
- [x] Add warning-to-camera framing from Raceway warning rows.
- [x] Add collapsed-visible Raceway warning/notice badge.
- [x] Add face/orientation foundation design note before coding controls.
- [x] Record Measure Snap Vertex requirement for Raceway tray/edge snapping.
- [x] Add generic Measurement snap-provider contract on viewer layers.
- [x] Expose Raceway tray/ladder edges as Measure Snap Vertex targets.
- [x] Fix Raceway edge snap reliability by using closest screen-space edge
  selection before mesh snap fallback.
- [x] Add first run-level Raceway orientation preset controls with save-flow
  persistence.
- [x] Preserve stable Raceway node UUID keys during node replacement.
- [x] Add derived segment identity/selection groundwork before segment-level
  face-offset persistence.
- [x] Make rough model clash/clearance AABB respect saved run orientation.
- [x] Restore Measurement snap fallback to visible Plant3D model geometry after
  Raceway layer snapping.
- [x] Fix Raceway continuation from the selected endpoint instead of always from
  the last-created node.
- [x] Add Plant model reference-layer hide/show shortcut.
- [x] Add non-standard plan-bend angle flags to fitting/schedule projections.
- [x] Promote connected service-class transitions to canonical warnings.
- [x] Add browser warning-detail page for fast Raceway validation review.
- [x] Add Plant3D home-page links to accessible uploaded/source models.
- [x] Stop Plant3D source uploads from auto-pruning prior unsaved uploads.

## Default Pass Ritual

- [x] Read Claude/Fable notes before coding.
- [x] Do quick housekeeping/status check and preserve unrelated dirty files.
- [x] Answer KR clarification/advice questions before implementation.
- [x] Report what KR should manually verify after each pass.
- [x] Add note to Claude when review/research/architecture input is useful.
- [x] End every pass summary with an explicit `Next Pass` recommendation
  section: ordered items, one-line reason per item when useful, and a short
  note if the order differs from the tracker.

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
- [x] Confirm BOQ-first before DXF/fabrication drawings.
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
- [x] Derived segments/fittings/supports remain regenerable.
- [ ] Cable pathfinding is deferred until raceway graph exists.
- [x] Collision starts as warnings/previews, not hard authority.

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

## Stage 8A - Raceway Network Junction Semantics

- [x] Define graph projection over saved raceway runs/nodes.
- [x] Add project-scoped layer graph JSON endpoint.
- [x] Use explicit 10 mm source-frame graph-node tolerance.
- [x] Derive endpoint/bend/riser/junction/branch semantics from geometry.
- [x] Keep persisted `node_kind` as a hint, not routing/fitting authority.
- [x] Warn for same-elevation crossings that do not share a graph node.
- [x] Warn for near-miss endpoints that look connected but are outside graph
  tolerance.
- [x] Add viewer graph warning display for saved raceways.
- [x] Add explicit endpoint-to-existing-node connect workflow.
- [ ] Add mid-run tee/split workflow for connecting into segment interiors.
- [ ] Add richer graph/junction visualization if manual testing shows it helps.

Acceptance:

- [x] The system can derive a simple raceway graph from authored runs.
- [x] A user can intentionally create a connected branch/junction.
- [x] Unconnected crossings are visible as warnings, not silent tees.
- [x] Existing draw/save/reload behavior remains intact.

## Stage 9 - Derived Parts And BOQ v0

- [x] Split run into straight segment lengths.
- [x] Detect bend nodes.
- [x] Count route length by family/size/service.
- [x] Add placeholder fitting count.
- [x] Add placeholder support count using simple span rule.
- [x] Add schedule JSON endpoint.
- [x] Add schedule HTML or CSV output.
- [x] Add tests for length and counts.
- [x] Document placeholder assumptions.

Acceptance:

- [x] User can produce a simple raceway schedule JSON payload.
- [x] User can refresh a compact schedule summary from the viewer.
- [x] User can download a schedule CSV from the viewer.
- [x] Quantities are traceable to durable run/node UUID keys.
- [x] Placeholder basis is visible in the payload assumptions.

## Stage 10 - Warning Layer

- [x] Define warning payload shape.
- [x] Add too-few-nodes warning.
- [x] Add short-segment warning.
- [x] Add excessive-bend warning.
- [x] Add unsupported-span placeholder warning.
- [x] Add missing/inactive family/size/service warning.
- [x] Add unknown coordinate context warning.
- [x] Add rough Plant3D object AABB clash/clearance warnings.
- [x] Add inspector warning display.
- [x] Add schedule/export warning evidence.
- [x] Defer hard clash constraints.

Acceptance:

- [x] Warnings appear before save and after reload.
- [x] Only invalid payload/access blocks persistence.
- [x] Warning vocabulary can grow to fill/segregation/clash.

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
- [x] Solid 3-plane tray/ladder proxy visual pass.
- [x] Surface/wire visual toggle, shaded bottom/side faces, and vertical
  riser face-legibility polish.
- [ ] Tray/riser cross-section orientation controls:
  - inherit riser orientation from adjacent horizontal tray by default,
  - [x] add cheap run-level orthogonal rotate presets first,
  - [x] close first server integration by using orientation in rough clash AABB,
  - defer arbitrary numeric roll angle until field usage proves it is needed.
- [x] Face/orientation foundation design note:
  - `../planning/raceway-face-orientation-foundation-2026-07-12.md`,
  - route centerline remains truth,
  - orientation/handedness/face-offset are authoring intent,
  - fitting/accessory persistence remains deferred,
  - node-key preservation is a prerequisite before segment-level overrides.
- [x] Preserve stable node UUID keys during node replacement before any
  segment-level orientation/face-offset override is persisted.
- [x] Add derived segment identity and selectable segment rows:
  - stable identity is derived from adjacent saved node UUIDs,
  - unsaved segments show draft identity until first save,
  - no segment-level override persistence yet.
- [x] Extend Measure `Snap Vertex On` to Raceway tray/ladder edges:
  - add a viewer-layer snap-provider contract,
  - let visible consumer overlays expose snap objects/points,
  - avoid Plant3D Measurement importing or special-casing Raceway.
- [ ] Evolve Measurement snap-provider contract before accessory geometry is
  selectable:
  - explicit snap points/segments with kind tags,
  - endpoint/corner priority over edge midpoint,
  - optional depth tie-break only if occluded-edge picking becomes a real user
    problem.
- [ ] Raceway visual opacity preference for shaded faces:
  - viewer/user preference first,
  - no effect on saved centreline geometry, schedule, graph, or clash truth.
- [ ] Governed Raceway colour strategy:
  - keep service-class colours as the engineering semantic default,
  - add project/service palette configuration before arbitrary per-run colours,
  - allow run-level visual override later only with legend/metadata clarity.
- [ ] Lightweight Raceway visual legend and/or isolate-selected-run polish.
- [ ] Canvas segment picking refinement:
  - when adjacent segments share/coincide at nodes, support direct segment
    picking by closest screen-space segment interior rather than letting shared
    endpoint node handles always win,
  - keep node selection available where the user explicitly aims at the node.
- [ ] Explicit Raceway work-plane/free-route drawing mode:
  - expose the existing working-plane fallback so AG tray routing does not feel
    dependent on pre-existing structural supports,
  - later support generation should consume the tray route rather than being a
    prerequisite for drawing it.
- [ ] Screen-scaled consumer overlay handles as a platform pattern beyond
  Raceway.
- [ ] Reducer fitting/accessory between unequal tray widths.
- [ ] Segment/face-offset edit workflow for riser/bend fitting alignment where
  connected tray faces must align rather than only centreline nodes.
- [ ] Parametric bend/riser/tee fitting geometry after placeholder counts are
  stable; cross fittings can follow later if project usage demands it.
- [x] Accessory/fitting foundation note and read-only derived projection:
  - plan-bend placeholders,
  - riser placeholders,
  - reducer candidates at connected unequal-size graph nodes,
  - no fitting/accessory persistence yet.
- [x] Raceway pane fitting projection summary:
  - `Refresh Fittings` button,
  - `T` keyboard shortcut,
  - placeholder, reducer-candidate, face-alignment, catalogue-validation, and
    graph branch/junction counts.
- [ ] Review `raceway-fitting-accessory-foundation-2026-07-12.md` before
  persisting fitting/accessory records or coding face-offset authoring.
- [x] Non-standard bend-angle advisory:
  - fitting placeholders now record nearest standard angle, deviation, and
    non-standard flag against common 30/45/60/90 degree bends,
  - fitting summary and schedule CSV expose the aggregate count.
- [x] Service-class transition warning:
  - service transitions remain visible in the fitting taxonomy,
  - connected mixed-service junctions now emit
    `raceway.warning.service_mismatch_at_junction` through the canonical
    warning/schedule/telemetry path.
- [ ] Project/admin-level connection tolerance setting when needed.
- [ ] Project/admin or user-level near-miss warning sensitivity setting when
  needed.
- [ ] Role-gated Raceway warning/config panel:
  - short segment threshold,
  - excessive bend count threshold,
  - support placeholder span,
  - rough AABB clash clearance band,
  - broad-phase object scan cap,
  - graph tolerance / near-miss sensitivity,
  - project defaults first; user display preferences only where they do not
    change engineering truth.
- [ ] Warning lifecycle UX:
  - acknowledge/accept/ignore/dismiss warnings from the Raceway panel,
  - preserve warning evidence in JSON/CSV even when the working UI filters it,
  - record reviewer, action, timestamp, optional reason, and telemetry event.
- [x] Raceway warning-detail browser page:
  - opens from the Raceway panel without downloading CSV,
  - shows warning summary, table rows, source points, evidence payloads,
    assumptions, JSON links, and CSV link.
- [x] Warning-to-camera framing:
  - expose Plant3D runtime `frameSourcePoints`,
  - frame the affected Raceway segment/source point when a schedule warning row
    is clicked.
- [x] Collapsed Raceway warning-count badge on the section header.
- [ ] Service-class colour legend chips.
- [ ] Inline run-tag rename in the Raceway inspector.
- [ ] Raceway shortcut cheat sheet.
- [x] Define `suggestion_event` telemetry schema in a design note.
- [x] Implement Tier-0 suggestion telemetry foundation:
  - peer `telemetry` app,
  - `SuggestionEvent` lifecycle model,
  - session/CSRF batch endpoint with project access validation,
  - Raceway warning/ortho event producers.
- [x] Raceway keyboard shortcut reliability audit:
  - review context gating for every advertised shortcut,
  - add focused browser coverage for shortcuts that can be triggered from the
    viewer canvas as well as from the Raceway pane,
  - avoid broad key capture that conflicts with typing or viewer navigation.
- [ ] Decision record `0007-ai-gateway-seam` before first Tier-1 AI feature.
- [ ] Telemetry `session_key` column or equivalent browser-session grouping
  strategy.
- [ ] Browser assertion for blocked telemetry endpoint behavior.
- [ ] Commit/readiness housekeeping from Claude §28:
  - decide whether to untrack `.code-workspace`,
  - keep KR catalogue seed confirmation visible,
  - revisit F-19 plant3d test-count variance only if it reappears,
  - preserve F-20 commit granularity when preparing changes.

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
  - `git diff --check`

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

### 2026-07-11 - Raceway Undo/Redo and Shortcut Productivity Pass

- Addressed KR's manual feedback after the multi-elevation pass:
  - Raceway now has bounded local undo/redo history for draft mutations,
  - `Undo Node` became general `Undo`, and a `Redo` command was added,
  - keyboard shortcuts were added for fast testing and day-to-day authoring,
  - each Raceway command button now carries its shortcut in the tooltip,
  - the selected-node coordinate editor moved directly below the command
    buttons, above the summary/run/node lists.
- Undo/redo scope:
  - draft mutations such as start run, add/move/delete node, anchor/clear
    anchor, palette changes, elevation shifts, unsaved run delete, and numeric
    coordinate edits push history,
  - `Ctrl+Z` undoes and `Ctrl+Shift+Z` / `Ctrl+Y` redoes,
  - successful server save/reload and external `setRuns()` clear local history
    so the UI does not imply that database commits/deletes can be undone by the
    local drafting stack.
- Shortcut scope:
  - Ctrl shortcuts are available from Raceway context including the coordinate
    editor,
  - single-key shortcuts are scoped to Raceway activity/panel focus so they do
    not casually steal Plant3D's broader viewer shortcuts,
  - current hints: `S` Start, `C` Continue, `F` Finish, `N` Select Node, `M`
    Move Node, `A` Anchor, `Shift+A` Clear Anchor, `Del` Delete Node,
    `Shift+Del` Delete Run, `R` Reload, `Esc` Cancel, `Ctrl+S` Save.
- Bumped browser cache key:
  - Raceway overlay: `20260711_raceway11`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-11 - Raceway Methodology/AI Addendum and Drawing-Aids Pass

- Read Claude's independent methodology/AI strategy RFC and appended a Codex
  addendum to
  `plant3d/records/planning/raceway-methodology-and-ai-strategy-2026-07-11.md`.
- Codex addendum position:
  - the long-term moat is the engineering chain from evidence-backed sizing to
    BOQ, 3D raceway graph, cable assignment, pull cards, and change impact,
    not the viewer alone,
  - AI should enter through an `ai_gateway`, suggestion telemetry, and
    deterministic evidence bundles rather than early model training,
  - clean manual graph-authoring data is AI-readiness work, not just UX polish.
- Implemented the first M-1/M-2 drawing-feel slice:
  - added optional `Ortho` drawing assist with shortcut `O`,
  - free working-plane clicks now lock to one plan axis from the previous node
    when Ortho is on,
  - model-surface anchors are deliberately not coordinate-modified by Ortho so
    persisted anchors do not claim a false clicked point,
  - added typed segment entry: direction `+X/-X/+Y/-Y/+EL/-EL`, length in
    metres, and `Add Segment`,
  - `Enter` in the segment direction/length fields appends the typed segment,
  - typed segments are undoable and keep the active run in draw mode.
- Bumped browser cache key:
  - Raceway overlay: `20260711_raceway12`.
- Manual verification:
  - KR confirmed the user can now confidently draw raceway on the 3D plant.
- Planning refinement:
  - inserted execution-plan Stage 8A, "Raceway Network Junction Semantics",
    before Stage 9 BOQ v0 so the next development step creates clean graph
    intent before we derive quantities and later route cables through it.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-11 - Stage 8A Graph Projection Foundation

- Started Stage 8A with a server-side derived graph projection, not new
  persistence:
  - added `raceway/graph.py`,
  - added `GET /raceway/layers/<id>/graph/`,
  - graph nodes are clustered with explicit
    `GRAPH_NODE_TOLERANCE_M = 0.01` (10 mm source-frame distance),
  - graph edges are derived from ordered saved run nodes,
  - project graph projection is project-scoped.
- Implemented geometry-derived semantics per Claude N-07:
  - endpoint from first/last node position,
  - riser from adjacent elevation deltas,
  - bend from plan-direction change,
  - junction/branch from shared graph nodes and graph degree,
  - persisted `RacewayNode.node_kind` remains a hint and is not trusted as
    authoritative graph/fitting semantics.
- Added first warning vocabulary for graph quality:
  - `raceway.graph.unconnected_crossing` when segments cross at the same
    elevation but do not share a graph node,
  - `raceway.graph.zero_length_segment` when segment endpoints collapse within
    graph tolerance.
- Addressed Claude N-08:
  - removed the dead `applyRunElevation` JavaScript helper so future code
    cannot accidentally flatten multi-elevation runs.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`

### 2026-07-11 - Stage 8A Graph-Aware Authoring Pass

- Made the graph projection visible in the Raceway authoring pane:
  - added `Refresh Graph` with shortcut `G`,
  - graph projection refreshes after saved load, save, and server delete,
  - the panel now shows saved-graph warnings separately from local draft
    warnings.
- Added the first explicit junction workflow:
  - `Connect Node` with shortcut `J`,
  - selected first/last node can be stitched to an existing raceway node by
    clicking that target node handle,
  - the command moves only the selected endpoint; mid-run tee/split insertion
    remains a later Stage 8A/9 refinement,
  - unconnected geometric crossings remain warnings unless the user explicitly
    creates a shared graph node.
- Bumped browser cache key:
  - Raceway overlay: `20260711_raceway13`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-12 - Stage 9 Schedule JSON Foundation

- Folded Claude N-10 into the graph projection before BOQ work:
  - added `NEAR_MISS_ENDPOINT_RADIUS_M = 0.25`,
  - added `raceway.graph.near_miss_endpoint` warnings for endpoints that look
    close to another run's node/edge but are outside the 10 mm graph
    connection tolerance,
  - updated the Raceway panel warning text for near-miss endpoints.
- Added the first non-persistent derived schedule/BOQ payload:
  - added `raceway/schedule.py`,
  - added `GET /raceway/layers/<id>/schedule/`,
  - split saved runs into segment lengths with durable run/node UUID trace,
  - counted length by family/size/service,
  - counted plan-bend and riser placeholders,
  - counted support placeholders using explicit
    `PLACEHOLDER_SUPPORT_SPAN_M = 3.0`,
  - exposed assumptions in the payload, including that `N001`/`E001` graph
    keys are presentation keys only and UUID keys are durable traceability.
- Added backlog lines from Claude/KR planning Q&A:
  - solid 3-plane proxy visual pass,
  - project/admin tolerance settings when needed,
  - near-miss warning sensitivity setting when needed,
  - `suggestion_event` telemetry design note,
  - future `0007-ai-gateway-seam` decision.
- Bumped browser cache key:
  - Raceway overlay: `20260712_raceway14`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-12 - Stage 9 Schedule Payload and Viewer Export Pass

- Addressed Claude S-1 through S-4 before hardening schedule UI/export:
  - added standard-length piece estimates from
    `RacewayFamily.standard_length_mm`,
  - added offcut estimate per run/group/total,
  - added `generated_at`, project, layer, source-model, and render-package
    context into the schedule payload,
  - embedded graph-warning counts in the schedule payload,
  - added an explicit assumption that junction/tee/cross placeholder counts
    are deferred.
- Added server-side CSV export from the same schedule payload:
  - `GET /raceway/layers/<id>/schedule.csv`,
  - CSV includes generation context, graph warning total, assumptions, grouped
    quantities, run rows, and segment rows.
- Made the schedule usable from the viewer:
  - `Refresh Schedule` button with shortcut `B`,
  - `CSV` button with shortcut `Shift+B`,
  - compact schedule summary shows total length, piece estimate, offcut,
    bend/riser/support placeholders, graph-warning count, assumptions count,
    and leading family/size/service groups.
- Bumped browser cache key:
  - Raceway overlay: `20260712_raceway15`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-12 - Stage 10 Warning Layer Foundation

- Added canonical derived warning projection in `raceway/warnings.py`:
  - normalizes graph warnings into the shared warning shape,
  - adds too-few-nodes, short-segment, excessive-bends, inactive catalogue
    reference, unknown service, unknown coordinate context, and support-span
    placeholder-basis notices,
  - summarizes warnings by code and severity.
- Integrated warnings into the schedule payload:
  - added `warnings` and `warning_summary`,
  - kept existing `graph_warnings` for compatibility.
- Rounded out CSV completeness from Claude S-5:
  - added graph warning counts by code,
  - added warning summary and warning detail rows,
  - added totals section,
  - added fitting placeholder category rows for plan bends and risers.
- Updated viewer schedule summary to show validation notices from the new
  warning summary and bumped the Raceway overlay cache key:
  - Raceway overlay: `20260712_raceway16`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-12 - Stage 10 Inspector Warnings and Screen-Scaled Handles

- Made Stage 10 warnings visible inside the authoring pane:
  - local draft warnings now use structured warning objects,
  - inspector shows selected-node/run warnings before save,
  - schedule summary shows validation warning details after refresh,
  - reloading saved raceways refreshes the schedule projection if the user had
    already opened it.
- Added an opt-in Plant3D viewer screen-scale hook for consumer overlay
  objects:
  - viewer layers may set `screenScaledObjects`,
  - only opted-in layer groups are traversed in the animation loop,
  - Raceway node handles and invisible hit targets now stay visually small
    while remaining selectable.
- Captured KR architecture refinements in the backlog:
  - reducer fitting/accessory between unequal tray widths,
  - segment/face-offset editing for riser/bend fitting alignment,
  - parametric bend/riser/tee fitting geometry after placeholder counts are
    stable,
  - cross fittings deferred until project usage demands it.
- Bumped browser cache keys:
  - Plant3D package viewer: `20260712_screen_scale1`,
  - Raceway overlay: `20260712_raceway17`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`
- Note:
  - Plain `node --check plant3d/static/plant3d/js/package_viewer.js` is not a
    valid check in the current Node mode because that file is an ES module with
    top-level `import`; plant3d static tests cover the updated viewer contract.

### 2026-07-12 - Solid 3-Plane Proxy Visual Pass

- Added a merged parametric proxy mesh per Raceway run:
  - one `solid-3-plane-proxy` mesh per run,
  - bottom face plus two side faces generated from centreline nodes and
    catalogue width/depth,
  - existing side rails, lower edges, rungs/cross-members, bend placeholders,
    riser placeholders, and node handles remain as legibility overlays.
- Kept the proxy derived and non-persistent:
  - saved geometry remains source-frame centreline nodes,
  - the mesh is rebuilt on render from current run data,
  - manufacturer/vendor assets remain later presentation overlays, not
    engineering truth.
- Kept draw-call control in line with Claude's guidance:
  - direct triangle positions are merged into one `BufferGeometry` per run,
  - no per-face/per-segment mesh objects are created.
- Bumped browser cache key:
  - Raceway overlay: `20260712_raceway18`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `venv/bin/python manage.py migrate telemetry`
  - `git diff --check`

### 2026-07-12 - Raceway Surface/Wire Toggle and Riser Visual Polish

- Kept the solid proxy as one merged mesh per Raceway run while adding shaded
  bottom/side differentiation:
  - bottom and side faces now use per-vertex colour shades,
  - one transparent material/draw-call profile is preserved,
  - the change remains a visual proxy only; persistence stays centreline based.
- Added a lightweight view toggle:
  - Raceway aid strip has a `Surface On` / `Wire Only` button,
  - `Shift+V` toggles the same view mode,
  - wire-only mode removes only the shaded face mesh and keeps rails, rungs,
    node handles, bend/riser placeholders, graph/schedule data, and save
    behavior intact.
- Polished vertical/riser geometry:
  - segment frame basis now follows the 3D source segment,
  - horizontal trays still grow upward from bottom elevation,
  - vertical risers push tray depth sideways so side faces/rails do not collapse
    into a single laminar plane.
- Bumped browser cache key:
  - Raceway overlay: `20260712_raceway19`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations raceway --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `git diff --check`

### 2026-07-12 - Tier-0 Suggestion Telemetry Foundation

- Added a consumer-neutral peer `telemetry` app:
  - `SuggestionEvent` records UUID lifecycle key, user, loose `project_id`,
    owner module, suggestion code, action, context, action detail, and client,
  - no domain-table FK to Raceway/EHT/Plant3D models,
  - context/action detail are server-sanitized to remove primary-key-like IDs.
- Added batch ingestion endpoint:
  - `POST /telemetry/events/`,
  - session login, CSRF, project-access gateway validation,
  - rate-limited and capped to 50 accepted events per batch.
- Wired Raceway viewer producers:
  - local/graph warning `shown` events are deduped per browser session,
  - save emits `unresolved_at_save` for visible unresolved warnings,
  - ortho-lock node commits emit `raceway.ortho.axis_lock`,
  - telemetry requests are fire-and-forget and cannot block authoring or save.
- Recorded KR shortcut reliability observation:
  - dedicated shortcut audit/testing pass added to backlog.
- Bumped browser cache key:
  - Raceway overlay: `20260712_raceway20`.
- Focused verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `git diff --check`

### 2026-07-12 - Rough Plant3D AABB Clash Warning Pass

- Read Claude/Fable §26 before coding; no course correction was needed.
- Folded in Claude N-11/N-12 housekeeping:
  - added `raceway/geometry.py` for shared point, distance, bend-angle, bounds,
    interpolation, and point-to-segment helpers,
  - switched graph/schedule/warnings to shared helpers where practical,
  - changed warning sorting to an explicit severity rank:
    error -> warning -> info.
- Added warning-only Plant3D envelope checks:
  - `raceway.warning.model_clash_aabb` for overlap between a raceway segment
    rough envelope and a `plant3d.ModelObject.bounds` box,
  - `raceway.warning.model_clearance_aabb` for objects inside the rough
    clearance band,
  - warning payloads carry stable object evidence, object/raceway bounds, gap,
    method, clearance, run/node keys, and segment index,
  - warnings are capped so a dense model area does not flood the panel/export,
  - a separate `raceway.warning.model_clash_scan_limited` warning appears when
    the first-pass object-bounds scan cap is reached.
- Kept collision authority deliberately deferred:
  - this is a coarse source-frame AABB preview,
  - it is not BVH, swept-volume, fitting-aware, support-aware, or a hard
    persistence blocker.
- Extended telemetry coverage:
  - schedule warnings now emit `shown`,
  - saved visible schedule warnings are refreshed before
    `unresolved_at_save`,
  - new clash/clearance warnings therefore join the same lifecycle event stream
    from day one.
- Bumped browser cache key:
  - Raceway overlay: `20260712_raceway21`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`

### 2026-07-12 - Warning Navigation and Source Progress Polish

- Read Claude/Fable §27 before coding.
- Closed Claude N-13 boundary correction:
  - moved the Plant3D model-object bounds lookup from `raceway.warnings` into
    `plant3d.overlay.model_object_bounds_for_source()`,
  - kept Raceway consuming plain dictionaries through the seam,
  - added a Raceway boundary test preventing runtime direct imports of
    `plant3d.models`,
  - added a Plant3D helper test proving `RenderTile.bounds` prefilters object
    candidates before object AABB checks.
- Improved warning UX:
  - schedule warning rows tied to a saved `run_key` are clickable,
  - clicking selects the affected run/node,
  - the affected segment is highlighted in the Raceway overlay as
    `warning-segment-highlight`,
  - layer-level warnings remain plain text.
- Updated telemetry documentation:
  - added event dictionary entries for rough model clash/clearance and
    scan-limited warning context shapes.
- Added source-detail progress visibility:
  - latest conversion progress now appears directly below the primary 3D Model
    card action, including below `Open 3D Viewer`,
  - existing polling keeps the visible progress strip updated,
  - Conversion Jobs still retains full evidence and raw metrics.
- Recorded KR's threshold-config observation in the backlog as a future
  role-gated project/admin configuration panel.
- Bumped browser cache keys:
  - Raceway overlay: `20260712_raceway22`,
  - Plant3D source detail script: `20260712_sourceui2`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `node --check plant3d/static/plant3d/js/source_detail.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`

### 2026-07-12 - Raceway Shortcut Reliability Audit

- Read Claude/Fable §27 before coding; no course correction was needed.
- Reworked Raceway keyboard shortcut gating:
  - shortcuts now map to concrete Raceway actions before context checks,
  - advertised commands work from the viewer canvas when a run/layer context
    makes them relevant,
  - `S`, view toggles, reload, saved-layer graph/schedule commands, and active
    run commands no longer depend on focus remaining inside the Raceway pane,
  - external typing targets still keep normal keyboard behavior.
- Added browser coverage for the manual failure shape:
  - after saving and focusing the viewer canvas, `B` refreshes the schedule,
  - after focusing the viewer canvas, `Ctrl+S` saves through the existing API,
  - the test stub now handles saved-run `PATCH` to cover repeat saves.
- Recorded KR's warning-action note as deferred:
  - acknowledge/accept/ignore/dismiss workflow belongs in a later warning
    lifecycle UX pass,
  - JSON/CSV evidence should remain complete even when the panel lets a user
    filter or close items.
- Bumped browser cache key:
  - Raceway overlay: `20260712_raceway23`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `git diff --check`

### 2026-07-12 - Fitting and Accessory Projection Foundation

- Read Claude/Fable §27 before coding; no new blocking note was present.
- Added design note:
  - `plant3d/records/planning/raceway-fitting-accessory-foundation-2026-07-12.md`,
  - records route-as-truth, persistence boundary, reducer semantics,
    face-alignment problem, tee/cross deferral, and review questions.
- Added read-only derived fitting projection:
  - new `raceway/fittings.py`,
  - new `GET /raceway/layers/<id>/fittings/`,
  - layer payload now includes `graph_url`, `schedule_url`, and `fittings_url`.
- Derived placeholder items currently include:
  - `plan_bend` at saved direction-change nodes,
  - `riser` on elevation-changing saved segments,
  - `reducer_candidate` at connected graph nodes with unequal tray
    width/depth/family/service context.
- Kept the implementation intentionally non-persistent:
  - no schema change,
  - no vendor part table,
  - no fitting/accessory rows,
  - no face-offset or handedness authority yet.
- Refactored schedule bend/riser placeholder logic to reuse the new fitting
  helpers so schedule and fitting projection do not drift.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-12 - Fitting Projection Pane and Deferred Stock Review

- Read Claude/Fable §28 before coding.
- Closed Claude N-14:
  - `plant3d.tests` no longer hardcodes a Raceway overlay cache key,
  - the test now reads `raceway-overlay` script/version from
    `settings.PLANT3D_VIEWER_EXTENSIONS`.
- Added compact fitting projection visibility to the Raceway pane:
  - `Refresh Fittings` button,
  - `T` keyboard shortcut,
  - summary for total placeholders, plan bends, risers, reducer candidates,
    face-alignment counts, catalogue-validation counts, and graph branch/junction
    counts.
- Kept the fitting pane read-only:
  - no schema change,
  - no fitting persistence,
  - no vendor part mapping or face-offset authority yet.
- Added browser smoke coverage:
  - button-driven fitting refresh,
  - canvas-focus `T` shortcut refresh,
  - summary rendering for placeholder/reducer/face-alignment counts.
- Reviewed deferred stock against Claude §28:
  - no item discarded,
  - `.code-workspace` cleanup, catalogue seed confirmation, telemetry
    `session_key`, blocked-endpoint browser assertion, warning lifecycle/config,
    reducer/face-offset semantics, M-5/M-6, and `ai_gateway` remain open.
- Bumped browser cache key:
  - Raceway overlay: `20260712_raceway24`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `git diff --check`

### 2026-07-13 - Stable Node Key Preservation

- Read Claude/Fable §31 before coding; no blocker found.
- Closed the identity prerequisite before segment-level orientation/face-offset
  overrides:
  - saved nodes resend their durable `node.key` values in the replacement
    payload,
  - `PUT /raceway/runs/<id>/nodes/` still replaces rows as one ordered set,
    but reuses keys that already belong to the same run,
  - new nodes receive fresh UUID keys,
  - foreign, malformed, or duplicate node keys are rejected before any existing
    node rows are deleted.
- Browser smoke now verifies the second save sends saved node keys back.
- API tests now verify:
  - same-run node keys are preserved across replacement and reorder,
  - a key from another run is rejected without deleting existing nodes.
- Bumped browser cache key:
  - Raceway overlay: `20260713_raceway28`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `git diff --check`

### 2026-07-12 - Warning Camera Framing and Header Badge

- Read Claude/Fable §28 and KR's pasted review before coding.
- No course correction needed:
  - N-14 was already closed by the previous pass,
  - accessory design note and fitting projection were already in place,
  - `.code-workspace` cleanup remains a commit-hygiene item rather than part of
    this UI behavior pass.
- Added a Plant3D viewer runtime helper:
  - `frameSourcePoints(points, options)`,
  - frames source-frame points through host-owned camera/controls logic,
  - options currently include `paddingM` and `minRadiusM`.
- Documented the helper in the viewer-extension contract note.
- Improved Raceway warning navigation:
  - clicking a schedule warning still selects the affected run/node and segment,
  - now also frames the affected segment/source point in the 3D viewer,
  - status text confirms when the warning was framed.
- Added a collapsed-visible Raceway header badge:
  - shows current validation notice count,
  - avoids double-counting graph warnings when a schedule warning payload is
    already loaded,
  - adds no geometry or per-frame viewer work.
- Bumped browser cache keys:
  - Plant3D package viewer: `20260712_frame_source1`,
  - Raceway overlay: `20260712_raceway25`.
- Verification passed:
  - `cp plant3d/static/plant3d/js/package_viewer.js /tmp/package_viewer_check.mjs`
  - `node --check /tmp/package_viewer_check.mjs`
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `git diff --check`

### 2026-07-12 - Face Orientation Design Note and Raceway Snap Requirement

- Read Claude/Fable §29 before coding.
- Agreed with Claude's course correction:
  - face/orientation controls are the correct next architecture item,
  - because they affect persistence, reducer handedness, riser orientation, clash
    envelopes, and fitting semantics, this pass is a design-note pass before
    implementation.
- Added design note:
  - `plant3d/records/planning/raceway-face-orientation-foundation-2026-07-12.md`.
- Key design conclusions:
  - route centerline remains the truth,
  - orientation/handedness/face-offset are authoring intent,
  - fitting/accessory persistence remains deferred,
  - first coded slice should start with cheap orientation presets,
  - arbitrary roll angle remains deferred,
  - stable node-key preservation is required before segment-level overrides.
- Recorded KR's measurement requirement:
  - Measure with `Snap Vertex On` must snap to Raceway tray/ladder edges,
  - this should use a generic viewer-layer snap-provider contract,
  - Measurement should not import or special-case Raceway.
- No runtime/schema changes in this pass.
- Verification passed:
  - `venv/bin/python manage.py check`
  - `git diff --check`

### 2026-07-12 - Measurement Snap Provider and Raceway Edge Snap

- Read Claude/Fable §30 before coding; no blocker found.
- Folded KR orientation answers into the face/orientation design note:
  - orientation changes should save through the normal Raceway save flow,
  - reducers/expanders should default to one-edge matching instead of
    centerline matching.
- Added a generic viewer-layer measurement snap provider:
  - `getMeasurementSnapObjects`,
  - Measurement gathers visible provider objects without importing consumer apps,
  - selected EHT/model snap behavior remains unchanged.
- Raceway now exposes measurement snap targets:
  - side rails,
  - lower edges,
  - depth ticks,
  - rungs,
  - tray cross-members.
- Node handles, warning glyphs, and centerline guides remain excluded from
  measurement snap targets.
- Updated the viewer-extension contract note with the layer snap-provider seam.
- Bumped browser cache keys:
  - Plant3D package viewer: `20260712_snap_provider1`,
  - Raceway overlay: `20260712_raceway26`.
- Verification passed:
  - `cp plant3d/static/plant3d/js/package_viewer.js /tmp/package_viewer_check.mjs`
  - `node --check /tmp/package_viewer_check.mjs`
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `git diff --check`

### 2026-07-13 - Raceway Edge Snap Reliability Fix

- Read Claude/Fable notes before coding; no new blocking item found for this
  fix.
- Root cause from KR manual test:
  - the first snap-provider implementation merged Raceway line objects and
    selected mesh objects into ordinary raycaster hit order,
  - thin Raceway edges could therefore lose the click to nearby trays,
    structures, or another 3D hit that was closer along the ray.
- Changed Measurement snap behavior:
  - visible layer snap-provider line objects are ranked by closest projected
    screen-space segment,
  - a tight 9 px radius is required before an edge snap is accepted,
  - selected EHT/model mesh vertex snap remains as the fallback,
  - free measurement behavior with `Snap Vertex Off` remains unchanged.
- Updated the viewer-extension contract note to record the screen-space edge
  selection rule.
- Bumped browser cache key:
  - Plant3D package viewer: `20260713_snap_provider2`.
- Verification passed:
  - `cp plant3d/static/plant3d/js/package_viewer.js /tmp/package_viewer_check.mjs`
  - `node --check /tmp/package_viewer_check.mjs`
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `git diff --check`
- KR manual verification:
  - previous random/nearby edge selection symptoms are resolved,
  - observed measurement agreement is about `+/-2 mm`, acceptable for this
    stage.
- Claude/Fable §31 independently confirmed:
  - the camera-distance winner defect is fixed by construction,
  - screen-space edge selection has a theoretical occlusion nuance, not a current
    defect,
  - endpoint-priority snapping and explicit snap geometry should be deferred
    until before accessory geometry becomes selectable.

### 2026-07-13 - Run-Level Orientation Presets

- Read Claude/Fable §31 before coding; no blocker found.
- Implemented first Raceway orientation-control slice:
  - active run dropdown with `Open Up`, `Roll Right`, `Open Down`, `Roll Left`,
  - run-level orientation rotates proxy width/depth axes around each segment
    centreline,
  - new runs inherit the current preset,
  - run rows and summary show the selected orientation.
- Save behavior:
  - orientation edits are draft-local while editing,
  - undo/redo works through the existing Raceway history stack,
  - orientation persists only through the normal `Save Draft` flow,
  - server validates and canonicalizes `RacewayRun.metadata["orientation"]`
    without adding a migration.
- Still deferred:
  - vertical riser inheritance from adjacent non-vertical segment,
  - stable node-key preservation before segment-level overrides,
  - segment/face-offset authoring,
  - reducer handedness and one-edge reducer materialization.
- Bumped browser cache key:
  - Raceway overlay: `20260713_raceway27`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `git diff --check`

### 2026-07-13 - Segment Identity Groundwork and Oriented Clash Envelope

- Read Claude/Fable §33 before finalizing the pass:
  - node-key preservation was approved as the right substrate,
  - segment split/merge/stale-intent semantics were folded into the face/
    orientation design note,
  - N-17 was kept in this pass as requested.
- Added derived segment identity/selection groundwork in the Raceway overlay:
  - segment rows are derived from adjacent node pairs,
  - saved segments show stable `start_node_key::end_node_key` identity,
  - unsaved segments show a temporary draft identity until first save,
  - selecting a segment clears node selection and highlights the segment in blue.
- Kept persistence intentionally out of this pass:
  - no segment-level orientation/face-offset override is saved yet,
  - reducer handedness remains the next architecture item after segment intent.
- Closed Claude N-17:
  - rough model clash/clearance AABB now uses oriented proxy corners for saved
    run-level orientation,
  - the behavior is covered by a warning regression test where `Roll Right`
    changes the detected envelope.
- Bumped browser cache key:
  - Raceway overlay: `20260713_raceway29`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
    after rerun outside sandbox because Playwright/live-server were blocked
    inside the sandbox,
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `git diff --check`

### 2026-07-14 - Manual Feedback Fixes: Snap, Continue, and Viewer Polish

- Read Claude/Fable §33 before coding; no new blocker found.
- Addressed KR manual feedback:
  - Measurement with `Snap Vertex On` now falls back to visible Plant3D model
    geometry after Raceway layer-edge snapping, restoring tray-to-structure and
    structure-only measurement.
  - Raceway `Continue` and typed segment entry now extend from the selected
    endpoint:
    - selected first endpoint prepends,
    - selected last endpoint appends,
    - single-node drafts still append,
    - mid-run branch insertion remains deferred to tee/split support.
  - Raceway lower edges now use a slightly different line colour for quick
    visual recognition without adding geometry.
  - Shift+M toggles the Plant model reference layer visibility.
  - Source detail conversion progress is no longer duplicated inside
    `Conversion Jobs`; completed job view links are surfaced in the primary
    progress/action area.
- Recorded deferred/manual observations:
  - canvas segment picking needs a future nearest-segment-interior pass so
    shared/coincident endpoint nodes do not prevent middle segment selection,
  - explicit work-plane/free-route Raceway drawing mode should make it clear
    that supports are not a prerequisite for sketching AG tray routes.
- Bumped browser cache keys:
  - Plant3D package viewer: `20260714_snap_provider3`,
  - Plant3D source detail: `20260714_sourceui3`,
  - Raceway overlay: `20260714_raceway30`.
- Verification passed:
  - `cp plant3d/static/plant3d/js/package_viewer.js /tmp/package_viewer_check.mjs`
  - `node --check /tmp/package_viewer_check.mjs`
  - `node --check plant3d/static/plant3d/js/source_detail.js`
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
    outside sandbox for Playwright/live-server,
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
    outside sandbox for the same reason,
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `git diff --check`

### 2026-07-14 - Fitting Advisory Signals: Bend Angles and Service Mismatch

- Read Claude/Fable notes before coding; no blocker found.
- Kept this pass projection-only:
  - no fitting/accessory persistence,
  - no vendor catalogue rules,
  - no reducer handedness or face-offset authority.
- Closed Claude/Fable N-15 as an advisory fitting signal:
  - plan-bend placeholders now include:
    - `nearest_standard_angle_deg`,
    - `deviation_deg`,
    - `standard_angle_tolerance_deg`,
    - `non_standard_angle`,
  - the check uses common `30/45/60/90` degree catalogue angles with a
    named `2.5` degree tolerance,
  - fitting projection counts `non_standard_plan_bends`,
  - schedule placeholder counts and CSV export include the non-standard bend
    total.
- Closed Claude/Fable N-16:
  - connected graph nodes with mixed service classes now emit
    `raceway.warning.service_mismatch_at_junction`,
  - the warning carries graph-node key/kind, source point, affected run keys,
    service classes, and member evidence,
  - service transitions remain in the fitting taxonomy as
    `service_transition`.
- Improved the existing fitting summary:
  - `Refresh Fittings` now shows the non-standard bend count beside face
    alignment and catalogue-validation counts.
- Bumped browser cache key:
  - Raceway overlay: `20260714_raceway31`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python -m py_compile raceway/fittings.py raceway/warnings.py raceway/views.py raceway/tests.py`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests.RacewayWarningProjectionTests raceway.tests.RacewayFittingProjectionTests raceway.tests.RacewayApiTests.test_layer_schedule_csv_endpoint_uses_same_schedule_payload_shape raceway.tests.RacewayStaticAssetTests.test_raceway_overlay_registers_external_viewer_layer --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`

### 2026-07-14 - Warning Details Page and Plant3D Home Navigation

- Read Claude/Fable §34 before coding; no blocker found:
  - segment-level orientation/face-offset remains the next architecture path,
  - this pass stayed UI/evidence-only and did not change route semantics.
- Added Raceway warning detail page:
  - new route: `/raceway/layers/<id>/warnings/`,
  - opens from the Raceway panel via `Warnings` button or `Shift+W`,
  - uses the same `build_layer_schedule()` and fitting projection evidence as
    JSON/CSV,
  - shows summary counts, warning rows, source point labels, expandable evidence
    payloads, assumptions, and quick links to schedule/graph/fittings JSON and
    CSV.
- Added Plant3D home navigation:
  - `/plant3d/` now lists recent accessible source models,
  - each row links to `Open Source`,
  - rows with a render package include direct `Open 3D Viewer`,
  - inaccessible project models stay hidden.
- Bumped browser cache key:
  - Raceway overlay: `20260714_raceway32`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python -m py_compile plant3d/views.py raceway/views.py plant3d/tests.py raceway/tests.py`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d.tests.Plant3DIntakeTests.test_home_page_lists_accessible_models_with_viewer_links raceway.tests.RacewayApiTests.test_layer_warning_detail_page_surfaces_schedule_warning_evidence raceway.tests.RacewayStaticAssetTests.test_raceway_overlay_registers_external_viewer_layer --noinput -v 2`
    after correcting the Plant3D test class target,
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`

### 2026-07-14 - Plant3D Source Upload Retention Fix

- Read Claude/Fable notes before coding; no blocker found for this safety fix:
  - Claude's §35 T-1 telemetry dictionary reminder remains open and recorded,
  - segment-level Raceway orientation/face-offset remains the next architecture
    path after this Plant3D data-retention correction.
- Addressed KR manual observation:
  - second and later IFC/source uploads no longer delete/prune earlier unsaved
    uploads for the same user/project,
  - users can keep multiple uploaded source models and delete explicitly from
    the source page when needed.
- Implementation:
  - removed the upload view's `replace_working=True` override,
  - kept duplicate-content idempotency by `content_signature`,
  - updated source upload/detail UI wording,
  - updated stale platform/pipeline records so they no longer describe
    disposable uploads as current behavior.
- No schema or migration change.
- Verification passed:
  - `venv/bin/python -m py_compile plant3d/views.py plant3d/tests.py`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d.tests.Plant3DIntakeTests.test_upload_view_retains_prior_working_source_for_same_user_project plant3d.tests.Plant3DIntakeTests.test_saved_source_is_not_replaced_by_next_working_upload plant3d.tests.Plant3DIntakeTests.test_home_page_lists_accessible_models_with_viewer_links --noinput -v 2`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`

### 2026-07-14 - Segment-Level Raceway Orientation Intent

- Read Claude/Fable notes before coding; no blocker found:
  - Claude/Fable §35 T-1 telemetry dictionary gap for
    `raceway.warning.service_mismatch_at_junction` was closed in
    `suggestion-telemetry-design-2026-07-12.md`,
  - next architecture direction remains face-offset/reducer handedness after
    this orientation-intent foundation.
- Implemented segment-level orientation override foundation:
  - selected segment inspector now exposes `Segment Orientation`,
  - `Run default` remains the default behavior,
  - overrides use the same four orthogonal presets as run orientation,
  - affected segment proxy faces/rails rotate immediately while the rest of the
    run remains unchanged,
  - segment list rows show the effective orientation and whether the segment is
    using run default or segment override.
- Persistence:
  - persisted under `RacewayRun.metadata["segment_orientation"]` with schema
    `raceway.segment_orientation.v0`,
  - keyed by adjacent node UUID pair `start_node_key::end_node_key`,
  - draft segment overrides are carried through first Save Draft and re-keyed
    once node UUIDs exist,
  - server rejects unsupported segment presets and prunes stale overrides when
    node replacement changes adjacency.
- Deferred/not yet implemented:
  - face-offset authoring,
  - reducer handedness and one-edge matching geometry,
  - split/merge inheritance UI,
  - vendor bend/riser/tee/reducer geometry.
- Bumped browser cache key:
  - Raceway overlay: `20260714_raceway33`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python -m py_compile raceway/views.py raceway/tests.py`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests.RacewayApiTests.test_run_accepts_segment_orientation_overrides_by_adjacent_node_keys raceway.tests.RacewayApiTests.test_node_replace_prunes_stale_segment_orientation_overrides raceway.tests.RacewayApiTests.test_run_rejects_unsupported_segment_orientation_preset raceway.tests.RacewayStaticAssetTests.test_raceway_overlay_registers_external_viewer_layer --noinput -v 2`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `git diff --check`

### 2026-07-15 - Segment Orientation UI Context Polish

- Read Claude/Fable notes before coding; no new blocker found.
- Addressed KR manual UX feedback:
  - removed the lower `Segment Orientation` dropdown from the segment
    inspector,
  - reused the top `Orientation` selector contextually:
    - no segment selected: edits the run/default orientation,
    - segment selected: edits the selected segment override,
    - selected segment options include `Run default (...)` to remove the
      override,
  - preserved the same undo/redo and Save Draft persistence behavior from the
    previous pass.
- Bumped browser cache key:
  - Raceway overlay: `20260715_raceway34`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python -m py_compile raceway/tests.py raceway/browser_tests.py`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests.RacewayStaticAssetTests.test_raceway_overlay_registers_external_viewer_layer --noinput -v 2`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`

### 2026-07-15 - Segment Orientation Save Regression Fix

- Read Claude/Fable notes before coding; no new blocker found.
- Addressed KR manual regression:
  - segment rotation previewed correctly,
  - pressing `Save Draft` made the browser appear to forget/undo the selected
    segment override.
- Root cause:
  - server metadata was saving the segment override correctly,
  - the browser reset `segmentOrientationOverrides` to `{}` after save and then
    treated that empty cache as authoritative,
  - reload had the same risk because `runFromServer()` initialized an empty map
    before reading `metadata.segment_orientation`.
- Fix:
  - empty override cache now rebuilds from non-empty saved metadata,
  - `Run default` deletion uses an explicit payload-from-current-map path so
    deleting an override does not resurrect old metadata,
  - browser smoke now covers draft segment override before first save, post-save
    local state, and reload persistence.
- Bumped browser cache key:
  - Raceway overlay: `20260715_raceway35`.
- Verification passed:
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python -m py_compile raceway/browser_tests.py raceway/tests.py`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests.RacewayStaticAssetTests.test_raceway_overlay_registers_external_viewer_layer --noinput -v 2`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`

### 2026-07-15 - Segment Face-Offset Foundation

- Read Claude/Fable notes before coding; no new blocker found:
  - face-offset/reducer handedness remains the architecture-critical path,
  - no accessory/fitting persistence was introduced in this pass.
- Implemented segment face offset:
  - selected segments now expose `Offset m` in the top Raceway aid grid,
  - the offset shifts the selected segment tray faces, rails, and cross members
    laterally from the route centerline,
  - node coordinates, route graph truth, schedule length, and topology remain
    unchanged,
  - offset-only segments keep the top `Orientation` selector on `Run default`
    instead of pretending there is a segment orientation override.
- Persistence:
  - saved under `RacewayRun.metadata["segment_face_offset"]`,
  - schema: `raceway.segment_face_offset.v0`,
  - keyed by adjacent node UUID pairs,
  - draft offsets re-key after first Save Draft,
  - server validates finite offsets within +/-5 m and prunes stale offsets
    after node replacement.
- Warning-envelope integration:
  - rough model clash/clearance envelopes now honor segment-level orientation
    and segment face offset,
  - added a regression test proving an offset segment changes model-clash
    detection.
- Bumped browser cache key:
  - Raceway overlay: `20260715_raceway36`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python -m py_compile raceway/views.py raceway/warnings.py raceway/tests.py raceway/browser_tests.py`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests.RacewayWarningProjectionTests.test_layer_warnings_use_saved_segment_face_offset_for_model_envelope raceway.tests.RacewayApiTests.test_run_accepts_segment_face_offset_overrides_by_adjacent_node_keys raceway.tests.RacewayApiTests.test_node_replace_prunes_stale_segment_face_offset_overrides raceway.tests.RacewayApiTests.test_run_rejects_invalid_segment_face_offset raceway.tests.RacewayStaticAssetTests.test_raceway_overlay_registers_external_viewer_layer --noinput -v 2`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput`
- Verification note:
  - `venv/bin/python manage.py test plant3d -v 2 --noinput` against the local
    PostgreSQL test DB still fails on an existing Plant3D fixture project id
    longer than the database column permits
    (`P3D-GATEWAY-INACCESSIBLE` > 20 chars). The same suite is green with
    `USE_POSTGRES=false`; this is unrelated to the face-offset pass.
- Next recommended pass:
  - reducer handedness/one-edge matching metadata and preview foundation,
  - then split/insert segment semantics needed for tee/accessory
    materialization.

### 2026-07-16 - Reducer One-Edge Matching and Offset-Step Signals

- Read Claude/Fable notes before coding; no blocker found:
  - Claude §37 endorsed the segment face-offset metadata direction,
  - Claude requested that adjacent face-offset discontinuities be added to the
    fitting/warning vocabulary,
  - Claude N-18 PostgreSQL fixture-length issue was accepted as a cheap
    housekeeping fix.
- Implemented projection-only reducer/expander alignment intelligence:
  - unequal-size connected graph members now default to one-edge matching
    (`left_edge`) instead of centerline matching,
  - reducer candidates expose current edge offsets and recommended
    `face_offset_m` adjustments per member,
  - reducer candidates only mark `requires_face_alignment = false` when the
    recommended edge is already aligned by saved segment face offsets,
  - centerline coincidence is kept as diagnostic context, but no longer hides a
    missing one-edge reducer alignment.
- Implemented same-size face-offset-step detection:
  - adjacent same-size segments with different saved offsets now produce a
    `face_offset_step` fitting placeholder,
  - `raceway.warning.face_offset_step_at_node` is emitted with previous/next
    segment keys, offsets, delta, epsilon, and recommended action,
  - the warning is documented in the telemetry event dictionary.
- UI/projection exposure:
  - fitting summary now shows edge-match candidates, offset steps, and
    offset-resolved alignments,
  - warning labels now render the new face-offset-step warning in the Raceway
    panel and warning-detail page,
  - Raceway overlay cache key bumped to `20260716_raceway37`.
- Housekeeping:
  - fixed the PostgreSQL-mode Plant3D gateway fixture id by shortening
    `P3D-GATEWAY-INACCESSIBLE` to `P3D-GATEWAY-BLOCK`.
- Deferred/not yet implemented:
  - real reducer/accessory model rows,
  - reducer handedness editing from the authoring UI,
  - visual bridge/annotation for face-offset segments where tray faces shift
    while route centerline nodes remain unchanged,
  - segment split/insert/branch semantics for tee/cross materialization.
- KR manual observation recorded:
  - shifted tray faces may look visually odd because the centerline and nodes
    intentionally remain the route/topology truth. Treat this as a display and
    UX problem to polish, not a reason to move the saved route nodes.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python -m py_compile raceway/fittings.py raceway/warnings.py raceway/tests.py plant3d/tests.py`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests.RacewayFittingProjectionTests.test_layer_fitting_projection_flags_unequal_size_reducer_candidate_at_connected_node raceway.tests.RacewayFittingProjectionTests.test_layer_fitting_projection_marks_reducer_alignment_resolved_by_offset raceway.tests.RacewayFittingProjectionTests.test_layer_fitting_projection_flags_same_size_face_offset_step raceway.tests.RacewayStaticAssetTests.test_raceway_overlay_registers_external_viewer_layer plant3d.tests.Plant3DProjectGatewayTests.test_validate_project_id_rejects_inaccessible_project_for_user --noinput -v 2`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput`
- Next recommended pass:
  - surface reducer edge-match suggestions in the authoring workflow so the
    user can apply the suggested offset instead of reading JSON,
  - then implement segment split/insert/branch semantics as the foundation for
    tee/cross/accessory materialization.

### 2026-07-17 - Reducer Edge-Match Apply Command

- Read Claude/Fable notes before coding; no blocker found:
  - §37 reducer rider was already addressed in the prior projection pass,
  - next useful slice was to make reducer edge-match suggestions actionable in
    the authoring UI.
- Implemented a viewer authoring command:
  - added `Apply Edge Match` beside `Refresh Fittings`,
  - added `Shift+T` shortcut,
  - command loads the fitting projection if needed,
  - refuses to run while unsaved local edits exist because suggestions are
    derived from the last saved graph,
  - collects unresolved one-edge reducer candidates,
  - applies each recommended `suggested_face_offset_m` into the affected
    segment's `segment_face_offset.v0` override,
  - batches changes into one undo step,
  - selects the first affected segment and marks affected runs dirty,
  - clears stale fitting projection output and tells the user to Save Draft,
    then refresh fittings.
- Implemented first suggestion-accept telemetry loop:
  - `raceway.reducer.edge_match_offset` is recorded as `shown` when reducer
    suggestions are exposed through fitting refresh,
  - `accepted` is recorded when `Apply Edge Match` applies a recommended offset,
  - event dictionary updated with context and action-detail shape.
- Kept accessory persistence deferred:
  - no reducer/accessory rows introduced,
  - reducer correction still lives as segment intent over route truth.
- Test hardening:
  - added static assertions for the new command,
  - added a real-viewer browser smoke where 300 mm and 600 mm connected runs
    produce an edge-match suggestion and the command applies the 0.15 m offset
    to the small tray,
  - the same browser smoke flushes telemetry and verifies an accepted
    `raceway.reducer.edge_match_offset` row,
  - fixed a browser-test order dependency by ensuring a minimal catalogue in
    real-viewer test setup when migration seed rows have been flushed,
  - raised real-viewer readiness waits to 45 s to avoid cold-start timeout
    flakes becoming normalized red.
- Bumped browser cache key:
  - Raceway overlay: `20260717_raceway38`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python -m py_compile raceway/browser_tests.py raceway/tests.py`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests.RacewayStaticAssetTests.test_raceway_overlay_registers_external_viewer_layer --noinput -v 2`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests.RacewayRealViewerBrowserSmokeTests.test_real_viewer_applies_reducer_edge_match_offsets --noinput -v 2`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests.RacewayRealViewerBrowserSmokeTests.test_real_viewer_draw_save_and_reload_raceway_run --noinput -v 2`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput`
- Verification note:
  - the first full browser-suite attempt exposed the test-order catalogue seed
    dependency and failed before this setup fix; the focused draw test and full
    browser suite are green after the fix.
- Manual check:
  - save two connected unequal-width raceways,
  - use `Refresh Fittings` or directly click `Apply Edge Match`,
  - confirm the suggested segment offset is applied,
  - click Save Draft,
  - refresh fittings again and confirm the reducer candidate no longer needs
    face alignment when the intended edge matches.
- Next recommended pass:
  - implement segment split/insert semantics so tee/cross and accessory
    materialization can be built on explicit branch topology,
  - carry forward the split inheritance rule: child segments inherit parent
    orientation and face-offset intent.

### 2026-07-17 - Accessory Geometry Doctrine Note

- Wrote the focused accessory geometry note:
  - `plant3d/records/planning/raceway-accessory-geometry-note-2026-07-17.md`.
- Reason:
  - KR correctly observed that `Shift+T`/`Apply Edge Match` visually aligns a
    tray edge but does not create a real reducer fitting.
- Decisions recorded:
  - `Apply Edge Match` is an alignment aid only,
  - real accessories are generated from connection ports,
  - reducers need left/right/center handedness,
  - real reducer proxy geometry must be a tapered or curved transition body,
  - route centerline and node keys remain design truth,
  - `Offset m` is local face offset, while six-direction segment movement is a
    separate route edit requiring split/insert semantics,
  - generic parametric proxies come before vendor/model replacement.
- Sources recorded:
  - Eaton, Superior Tray, PohlCon, BIMobject, PlantCon, and OBO fitting/catalogue
    references.
- Next recommended coding order refined:
  - segment split/insert semantics,
  - reducer handedness UI,
  - reducer proxy geometry v0,
  - bend/riser proxy geometry v0,
  - tee/cross once explicit branch topology exists.

### 2026-07-18 - Segment Split/Insert Foundation

- Read Claude/Fable notes before coding; §40 aligned with the next slice:
  - split/merge semantics must preserve segment intent,
  - reducer geometry must wait for explicit topology and port-frame rules,
  - straight proxy cutback and development-length honesty remain for reducer
    proxy v0.
- Updated the accessory geometry note with KR decisions:
  - reducer handedness defaults to `left_edge` with user override,
  - reducer development length uses a local heuristic first, later overridden
    by vendor catalogue or project/user preference,
  - reducer handedness is evaluated in the wider-port frame,
  - reducer auto-suggestion should be gated by a named near-collinearity
    tolerance.
- Implemented first segment split UI in `raceway_overlay.js`:
  - added `Split %` and `Split Segment`,
  - added `Shift+X` shortcut,
  - selected segment is split into two segments at the entered percentage,
  - inserted node is selected immediately for fine adjustment/anchoring,
  - local undo/redo restores split edits and split percentage context,
  - graph/schedule/fitting projections are cleared after topology changes.
- Implemented segment intent remapping:
  - split children inherit parent segment orientation override and face-offset
    intent,
  - draft segment intent is remapped when indexes shift before the first save,
  - save/reload re-keys inherited draft intent through the existing node UUID
    migration path.
- Improved delete/merge semantics:
  - deleting an intermediate node merges adjacent segments,
  - matching parent intent is carried to the merged segment,
  - conflicting orientation/offset intent is dropped with a status message,
  - endpoint deletes and index shifts preserve unaffected segment intent.
- Bumped browser cache key:
  - Raceway overlay: `20260718_raceway39`.
- Verification passed:
  - `node --check raceway/static/raceway/js/raceway_overlay.js`
  - `venv/bin/python -m py_compile raceway/tests.py raceway/browser_tests.py`
  - `venv/bin/python manage.py check`
  - `venv/bin/python manage.py makemigrations --check --dry-run`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.tests.RacewayStaticAssetTests.test_raceway_overlay_registers_external_viewer_layer --noinput -v 2`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway.browser_tests --noinput -v 1`
  - `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
  - `venv/bin/python manage.py test plant3d -v 2 --noinput`
  - `USE_POSTGRES=false venv/bin/python manage.py test telemetry -v 2 --noinput`
  - `git diff --check`
- Verification note:
  - non-escalated browser attempts failed due sandbox/browser socket limits,
    then the escalated browser suite passed,
  - a first telemetry run without `USE_POSTGRES=false` failed before tests due
    local PostgreSQL connection state; the SQLite telemetry run passed.
- Manual check:
  - open the 3D viewer, create or load a run with at least two segments,
  - select a segment row,
  - enter a `Split %` such as `40`,
  - click `Split Segment` or press `Shift+X`,
  - confirm a new node appears at that percentage and can be moved/anchored,
  - if the original segment had `Offset m` or segment orientation, confirm both
    child segments inherit it,
  - delete the inserted node and confirm matching intent is carried back to the
    merged segment.
- Notes to Claude/Fable:
  - please review whether keeping per-intent-kind agreement on merge is enough:
    current code preserves an agreeing face offset even if orientation conflicts
    and drops only the conflicting kind while warning in status.
- Next recommended pass:
  - reducer handedness UI using the same segment-intent persistence idiom,
  - then reducer proxy geometry v0 with development-length assumption and
    straight-proxy cutback,
  - keep click-on-segment insertion and branch tee workflow behind the current
    percentage split foundation unless KR wants that UX accelerated.
