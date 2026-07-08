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
- [ ] Add raceway peer-app decision record.
- [ ] Ask Claude/Fable for reset and MVP architecture review.

## Decisions

- [x] Keep `plant3d` as neutral co-located platform during Stage 0.
- [x] Keep EHT and future modules as consumers of `plant3d`.
- [x] Reject cable-first always-on Manhattan routing as primary direction.
- [x] Treat existing cable centerline drafting as manual/draft exception tooling.
- [ ] Record `raceway` as peer app in decisions folder.
- [ ] Confirm app name: `raceway`.
- [ ] Confirm generic curated catalogue seed first.
- [!] Choose initial standards/default stance: IEC 61537, NEMA VE-1/VE-2, or
  configurable/no-default MVP.
- [ ] Confirm BOQ-first before DXF/fabrication drawings.

## Boundary Guardrails

- [ ] `plant3d` has no runtime import of `raceway`.
- [ ] `raceway` has no direct import of `eht.models`.
- [ ] `raceway` uses loose `project_id`, not FK to `eht.ProjectData`.
- [ ] Raceway persistence is outside `plant3d`.
- [ ] Durable raceway anchors use package/source/model-object ids and explicit
  coordinate frame.
- [ ] Route centerline is stored as truth.
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
- [ ] Decision record created: `raceway` as peer app.
- [ ] Claude/Fable review requested.
- [ ] Claude/Fable review findings recorded.

Acceptance:

- [ ] All reset records point to the same direction.
- [ ] No conflicting active tracker remains.
- [ ] KR has a clear next-pass coding target.

Verification:

- [x] `git diff --check`

## Stage 1 - Raceway App Skeleton

- [ ] Create Django app `raceway`.
- [ ] Add `raceway/apps.py` with `RacewayConfig`.
- [ ] Add `raceway/urls.py`.
- [ ] Add minimal view/API health endpoint.
- [ ] Register app in `ELECSENSE/settings.py`.
- [ ] Include `raceway/` in `ELECSENSE/urls.py`.
- [ ] Add `raceway/tests.py` or test package.
- [ ] Test app URL boundary.
- [ ] Test `plant3d` runtime modules do not import `raceway`.
- [ ] Test `raceway` does not import EHT models directly.
- [ ] Update records after pass.

Acceptance:

- [ ] `venv/bin/python manage.py check` passes.
- [ ] `USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1` passes.
- [ ] `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passes.

Notes:

- Defer schema if the app skeleton pass is already large.

## Stage 2 - Project Scope And Access

- [ ] Add raceway project-scope helper.
- [ ] Reuse `plant3d.project_gateway` for Stage 0 access.
- [ ] Add accessible project test.
- [ ] Add inaccessible project test.
- [ ] Add no-direct-EHT-import guard.
- [ ] Document Stage 0 adapter/future token/API direction.

Acceptance:

- [ ] Raceway can validate project ids.
- [ ] Raceway queries are project-scoped.
- [ ] Raceway has no hard FK or direct import dependency on EHT project models.

## Stage 3 - Minimal Domain Schema

- [ ] Define `RacewayLayer`.
- [ ] Define `RacewayFamily`.
- [ ] Define `RacewaySize`.
- [ ] Define `RacewayRun`.
- [ ] Define `RacewayNode`.
- [ ] Add model validation/clean methods where useful.
- [ ] Add admin registrations if helpful for inspection.
- [ ] Generate migration.
- [ ] Add model tests.
- [ ] Add project-scope query tests.
- [ ] Update records after pass.

Schema acceptance:

- [ ] Route centerline can be stored as ordered nodes.
- [ ] Family/size can be assigned to a run.
- [ ] Service class/status can be assigned to a run.
- [ ] Package/source/render-frame context can be stored.
- [ ] Node coordinates are finite and ordered.
- [ ] No `plant3d` model has FK/import back to `raceway`.

Deferred:

- [ ] Supports.
- [ ] Detailed fittings.
- [ ] Vendor catalogue.
- [ ] Cable assignment.
- [ ] GLB overlay cache.

## Stage 4 - Raceway JSON API

- [ ] List layers for project/package context.
- [ ] Create/update/delete layer.
- [ ] List runs.
- [ ] Create/update/delete run.
- [ ] Replace ordered node list.
- [ ] Validate project access.
- [ ] Validate package/source access where provided.
- [ ] Validate coordinate frame.
- [ ] Validate finite XYZ.
- [ ] Validate family/size/service.
- [ ] Add unauthorized access tests.
- [ ] Add invalid payload tests.
- [ ] Add successful save/reload tests.

Acceptance:

- [ ] A run can be saved and loaded through JSON.
- [ ] Bad payloads fail cleanly.
- [ ] Private implementation fields are not exposed.

## Stage 5 - Viewer Extension Seam

- [ ] Confirm current layer registry is sufficient.
- [ ] Add external consumer script hook if required.
- [ ] Add raceway script placeholder/include.
- [ ] Register `raceway-overlay` layer.
- [ ] Confirm layer controls show/hide raceway overlay.
- [ ] Confirm EHT draft layer behavior unchanged.
- [ ] Confirm measurement/grid/plot plan behavior unchanged.
- [ ] Add JS smoke/static tests.

Acceptance:

- [ ] Raceways can render in a separate overlay group.
- [ ] Viewer remains a `plant3d` host, not raceway-owned.

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

- [ ] KR: default standard basis?
- [ ] KR: exact generic catalogue seed?
- [ ] KR: BOQ-first is sufficient before drawings?
- [ ] Claude/Fable: minimal schema review.
- [ ] Claude/Fable: collision/pathfinding staging review.
- [ ] Claude/Fable: UX risk review for over-smart routing.

## Verification Log

Append each pass here.

### 2026-07-08 - Tracker Creation

- Created detailed plan and tracker.
- No code changes.
- Updated records README to link the detailed files.
- Verification passed: `git diff --check`.
