# Raceway MVP Execution Plan

Date: 2026-07-08

Status: active detailed execution plan

Parent records:

- `platform-reset-handover-2026-07-08.md`
- `platform-ecosystem-development-plan-2026-07-08.md`
- `../tracking/platform-ecosystem-reset-tracker-2026-07-08.md`
- `raceway-module-architecture-2026-07-02.md`
- `public-api-boundary-contract-2026-07-05.md`
- `../decisions/0005-plant3d-independent-platform-boundary.md`

## Purpose

This plan converts the post-reset direction into execution work packages.

The strategic plan says what the platform ecosystem should become. This file
says how Codex should build the first raceway/tray foundation in small,
reviewable, test-backed passes without reviving the rejected cable-first route
experiments.

## Operating Thesis

The first commercially meaningful 3D electrical authoring object is not an
individual cable route. It is a shared aboveground raceway/tray/ladder/sleeve
network. Underground trench/duct-bank work is strategically important, but it
is deferred until the aboveground MVP and integration shape are proven.

Therefore the MVP should prove:

1. `raceway` can exist as a peer consumer of `plant3d`.
2. A user can author a route centerline as engineering intent.
3. The system can derive simple tray geometry and schedules from that route.
4. Persistence lives in `raceway`, not `plant3d`.
5. Cable assignment, pathfinding, collision, support automation, and BOQ can
   grow from this foundation without schema or UX reversal.

## Architectural Rules

- `plant3d` owns reference source models, conversion jobs, render packages,
  model objects, package/tile APIs, coordinate/RTC contract, viewer shell,
  measurement, picking, generic layer registration, and generic anchor helpers.
- `raceway` owns raceway domain persistence: layers, runs, nodes, catalogue,
  derived parts, validation, and BOQ.
- `eht` owns heat tracing calculations and EHT-specific deliverables.
- Future consumers such as lighting design must be treated the same way as EHT:
  they consume `plant3d`; they do not become part of `plant3d`.
- `plant3d` must not import `raceway`.
- `raceway` may consume `plant3d` public APIs, helpers, and stable anchors.
- Store durable raceway coordinates as source/world coordinates or explicit
  model-object anchors, with source/package context. Render-frame positions are
  derived for the viewer through the `plant3d` coordinate/RTC contract. Do not
  persist raw screen/canvas coordinates as durable truth.
- Route centerline is truth. Tray segments, fittings, supports, and GLB overlay
  caches are derived/regenerable.
- Suggestions are explicit and user-accepted. The software must not silently
  become the design authority.

## Stage Gates

Each stage should end with:

- code and records updated,
- focused tests passing,
- `git diff --check` clean,
- tracker updated with status, findings, and next pass.

Do not move to the next stage if the current stage violates a boundary rule or
creates hidden coupling.

## Stage 0 - Reset Closure And Decision

Goal: make the pivot durable before coding the new app.

Tasks:

- Add decision record: `raceway` is a peer app consuming `plant3d`.
- Confirm app name: `raceway`.
- Confirm catalogue seed direction: generic curated seed first.
- Record default standards strategy: IEC-first for target markets in the Middle
  East, Asia, and Europe. NEMA/ANSI is a later configurable path.
- Record MVP containment scope: aboveground tray/ladder/sleeve first;
  underground trench/duct-bank later.
- Update records README to include this detailed plan and tracker.
- Ask Claude/Fable for architecture review of the reset and MVP plan.

Acceptance:

- A durable decision record exists.
- No code changes are required to understand the current direction.
- Tracker has all Stage 0 decisions recorded.

Verification:

- Documentation-only pass: `git diff --check`.

## Stage 1 - Raceway App Skeleton

Goal: create an empty but real peer app with hard import boundaries.

Tasks:

- Create Django app `raceway`.
- Add `RacewayConfig`.
- Register app in `INSTALLED_APPS`.
- Add `raceway/urls.py` with a minimal namespace boundary.
- Include `raceway/` in project URLs only if the shell can remain harmless.
- Add a minimal health/index view or JSON endpoint for wiring verification.
- Add tests proving the URL boundary resolves for an authenticated accessible
  user where required by the current middleware shape.
- Add import-boundary tests:
  - `plant3d` runtime modules must not import `raceway`.
  - `raceway` must not import EHT models directly.
  - `raceway` may import `plant3d.project_gateway`, `plant3d.access`, or future
    public helper modules.

Acceptance:

- `raceway` is installed and importable.
- No database schema beyond Django defaults is introduced unless explicitly
  chosen in this stage.
- `plant3d` behavior is unchanged.

Verification:

```bash
venv/bin/python manage.py check
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1
git diff --check
```

## Stage 2 - Project Scope And Access Contract

Goal: give `raceway` the same loose project boundary discipline as `plant3d`.

Tasks:

- Add a small `raceway/access.py` or `raceway/project_scope.py`.
- Reuse `plant3d.project_gateway` for Stage 0 project id validation and picker
  behavior.
- Keep all raceway queries project-scoped by `project_id` string.
- Do not FK to `eht.ProjectData`.
- Add tests for accessible and inaccessible project ids.
- Document that this is a Stage 0 co-located adapter and can become API/token
  validation after service extraction.

Acceptance:

- Raceway write/read helpers can validate project scope without importing EHT
  models directly.
- Direct `from eht.models import ...` in `raceway` is forbidden by test.

Verification:

```bash
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
git diff --check
```

## Stage 3 - Minimal Domain Schema

Goal: persist route-as-truth without over-modeling supports, fittings, or
vendor catalogue.

Initial models:

- `RacewayLayer`
  - `project_id`
  - name, description, status, revision
  - source/package context fields as loose ids
  - created/updated metadata
- `RacewayFamily`
  - kind: ladder, perforated tray, solid tray, mesh tray, trunking, sleeve
  - material
  - standard length
  - generic profile parameters JSON
  - active/validated flags
- `RacewaySize`
  - family relation
  - width/depth
  - weight per metre placeholder
  - load/span table JSON placeholder
- `RacewayRun`
  - layer relation
  - stable UUID key
  - family/size relation
  - service class
  - tag/status
  - elevation or working-plane metadata
  - package/source context
  - validation summary JSON
- `RacewayNode`
  - run relation
  - stable UUID key
  - ordered index
  - source/world XYZ or explicit model-object anchor
  - optional anchor owner/package/stable id
  - node kind: endpoint, bend, branch, riser placeholder

Explicitly deferred:

- underground trench and duct-bank modelling,
- support records,
- detailed fitting records,
- vendor part mapping,
- cable assignments,
- GLB overlay cache table,
- drawing output tables.

Acceptance:

- Schema is narrow and additive.
- Runs can store centerline nodes in order.
- Nodes can represent both free positions and future plant-object anchors.
- Durable coordinates survive package reconversion because render-frame
  positions are derived, not treated as source of truth.
- No reverse persistence into `plant3d`.

Verification:

```bash
venv/bin/python manage.py makemigrations raceway
venv/bin/python manage.py check
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
git diff --check
```

## Stage 4 - API Surface For Raceway Data

Goal: make durable raceway data available to the viewer without embedding
raceway persistence in `plant3d`.

Tasks:

- Add JSON endpoints:
  - list layers for project/package context,
  - create/update/delete layer,
  - list/create/update/delete runs,
  - replace ordered node list for a run.
- Add payload validation:
  - project access,
  - package/source access where provided,
  - coordinate frame present,
  - finite XYZ coordinates,
  - source/world or anchor payload present for durable nodes,
  - valid service/family/size references,
  - ordered node indices.
- Keep POST/PUT/PATCH/DELETE CSRF/session-authenticated for Stage 0.
- Return stable ids and URLs, not storage keys or private implementation data.

Acceptance:

- A raceway run can be saved and reloaded through JSON.
- Invalid project/package/node payloads fail cleanly.
- Raceways are invisible to users without project access.

Verification:

```bash
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1
git diff --check
```

## Stage 5 - Viewer Extension Seam

Goal: let a consumer overlay attach to the existing `plant3d` viewer without
turning `package_viewer.js` into a raceway-specific monolith.

Tasks:

- Confirm `window.plant3dViewerLayers.register` is enough for raceway overlay
  group registration.
- Add a settings-driven viewer extension list so `plant3d` knows only that
  extension scripts exist, not which peer app owns them.
- Add a raceway script include only through the configured extension list.
- Register `raceway-overlay` layer with owner `raceway`.
- Keep EHT draft overlay behavior unchanged.
- Do not add raceway database calls to `plant3d` views unless routed through a
  clearly documented extension/adaptor.

Acceptance:

- The viewer can show a raceway overlay group.
- Layer visibility controls include raceway overlay when present.
- Plant model, measurement, grid, plot plan, and EHT draft layers still work.

Verification:

```bash
node --check /tmp/package_viewer.mjs
USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
git diff --check
```

## Stage 6 - Centerline Authoring MVP

Goal: user can draw and edit a raceway run centerline on a working elevation
plane.

Tasks:

- Add raceway tool palette with family, size, service class, elevation.
- Add draw mode:
  - start run,
  - click ordered nodes,
  - finish/cancel,
  - undo last node.
- Add basic snapping:
  - grid/elevation plane first,
  - model-object snap later if safe.
- Add node handles:
  - select run,
  - move node,
  - delete node,
  - edit XYZ/elevation in inspector.
- Add live HUD:
  - length,
  - node count,
  - bend count,
  - elevation,
  - family/size/service,
  - warning count.

Acceptance:

- User can draw at least one run with three or more nodes.
- User can edit node positions and see the route update.
- User can distinguish raceway from EHT draft routes.
- Existing EHT draft route workflow still works.

Verification:

```bash
node --check /tmp/package_viewer.mjs
USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
git diff --check
```

## Stage 7 - Simple Tray Geometry Preview

Goal: derive visible tray geometry from the centerline without storing meshes as
truth.

Tasks:

- Generate simple client-side geometry from run centerline.
- Start with simplified rectangular/ladder-style preview:
  - width,
  - depth,
  - centerline,
  - service color,
  - bend placeholder.
- Keep geometry light and responsive.
- Add selection/highlight for raceway run.
- Keep exact fittings/supports deferred.

Acceptance:

- Tray preview updates when route nodes change.
- Width/depth changes update the preview.
- Preview is visibly a tray/raceway, not just a polyline.
- It remains clear that this is an MVP derived preview.

Verification:

```bash
node --check /tmp/package_viewer.mjs
USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
git diff --check
```

## Stage 8 - Persistence Integration

Goal: saved raceway runs load back into the viewer.

Tasks:

- Save a run and ordered nodes from the viewer to `raceway`.
- Load project/package raceway layers when the viewer opens.
- Add optimistic UI state only where safe.
- Keep browser localStorage as temporary draft fallback only if useful.
- Add server-side revalidation on every save.

Acceptance:

- Draw, save, refresh, and reload preserves the run.
- Unauthorized users cannot load or mutate raceway data.
- Failed save does not silently pretend to persist.

Verification:

```bash
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1
git diff --check
```

## Stage 9 - Derived Parts And BOQ v0

Goal: convert route intent into first useful engineering quantities.

Tasks:

- Split each run into straight segment lengths.
- Count bend nodes.
- Compute total length by family/size/service.
- Add placeholder fitting count by bend angle category.
- Add placeholder support count using simple max-span rule from size data.
- Add JSON/HTML/CSV schedule endpoint.

Acceptance:

- A user can get a simple raceway schedule from saved runs.
- Quantity output is traceable back to run ids and segment lengths.
- Placeholder assumptions are explicit.

Verification:

```bash
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
git diff --check
```

## Stage 10 - Warning Layer

Goal: begin engineering validation as warnings, not hard stops.

Tasks:

- Define warning shape: code, severity, message, object/run/node reference.
- Add route warnings:
  - too few nodes,
  - very short segments,
  - excessive bend count,
  - unsupported span placeholder,
  - missing size/family/service,
  - off-package or unknown coordinate context.
- Add inspector display and schedule export evidence.
- Keep clash/collision as rough AABB warning only when enough model data is
  available.

Acceptance:

- Warnings are visible before save and after reload.
- Warnings do not block unless payload shape is invalid or access is denied.
- Warning vocabulary can be extended for fill, segregation, and clash later.

Verification:

```bash
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
git diff --check
```

## Deferred Until After MVP

- Full vendor catalogue.
- Auto-support anchoring to beams.
- Detailed fittings and reducer/riser library.
- Underground trench and duct-bank modelling.
- Server-baked GLB overlay cache.
- BVH/narrow-phase collision.
- Cable assignment to raceway graph.
- Dijkstra/A* pathfinding.
- Cable pulling tension.
- Drum/cut optimization.
- Drafting-grade DXF/fabrication drawings.
- Multi-user live collaboration.

## Verification Baseline

Use these as the broad pass before reporting larger milestones:

```bash
node --check /tmp/package_viewer.mjs
node --check /tmp/routing_core.mjs
venv/bin/python manage.py check
USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1
USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1
git diff --check
```

If a browser-facing milestone changes layout or 3D behavior, add manual
verification:

- upload/process IFC,
- open package viewer,
- verify plant model renders,
- verify layer controls,
- draw/edit raceway run,
- verify EHT draft tools still work,
- save/reload raceway run where persistence is in scope.

## Claude/Fable Review Points

Ask Claude to review after Stage 0 and again after Stage 3:

- Is the peer app boundary still clean?
- Is the minimal schema too much, too little, or incorrectly shaped?
- Are any future cable-routing assumptions being smuggled in too early?
- Are collision/pathfinding hooks prepared without being overbuilt?
- Is the UX still route-first and user-controlled?

## KR Decision Points

These require KR direction before implementation hardens around them:

- Final app name if not `raceway`.
- Detailed IEC-first seed basis and when NEMA/ANSI should enter.
- Generic catalogue seed contents.
- Whether BOQ-first is enough before drawings.
- When server-baked GLB overlay cache becomes necessary.
