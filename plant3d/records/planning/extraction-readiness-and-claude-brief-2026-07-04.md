# plant3d Extraction Readiness And Claude Brief

Date: 2026-07-04
Status: active execution note

## Current Decision

`plant3d` is now treated as a neutral 3D engineering platform that is co-located in the current Django repo for development convenience, but designed for future independent deployment.

The immediate direction is **not** full microservice extraction. The direction is to make the codebase extraction-ready while continuing to mature the 3D engineering tool.

Celery/Redis is deliberately deferred for now. The current worker command remains acceptable during this phase:

```bash
venv/bin/python manage.py process_plant3d_job --watch --parser-threads auto
```

For constrained/shared containers, use a cap:

```bash
venv/bin/python manage.py process_plant3d_job --watch --parser-threads auto --parser-thread-cap 2
```

## What Is Already Settled

- `plant3d` must remain EHT-neutral.
- EHT, raceway, cable routing, construction, and future engineering modules should consume `plant3d`; they should not own its internals.
- Stage 0 decoupling has started:
  - `SourceModel.project` hard FK/cascade was replaced by loose `project_id`.
  - Project listing/access/validation now goes through `plant3d.project_gateway`.
  - The current gateway still calls EHT internally, but this dependency is confined to one seam.
- EHT-specific persistence must not be added to `plant3d` core.
- Raceway/cable tray persistence must also stay out of `plant3d` core.

## Current Engineering Priority

The next phase should focus on stable foundation stones:

1. Define the public `plant3d` API/boundary contract.
2. Harden tests around `project_gateway`.
3. Formalise a generic viewer overlay/layer contract.
4. Keep EHT draft tools as an adapter/consumer of the overlay contract, not as platform persistence.
5. Decide whether raceway becomes a peer app before any tray persistence is coded.
6. Continue practical UI/tool improvements without weakening the platform boundary.

## Boundary Contract To Define Next

The public contract should name the stable concepts external modules may rely on:

- Project reference: `project_id`
- Source model reference: source id plus project id
- Conversion job reference and status payload
- Render package reference
- Tileset/tile blob URLs and metadata URLs
- Model object stable id and package-local feature id
- RTC coordinate contract
- Viewer route/deep-link contract
- Overlay layer anchors:
  - package id
  - model object stable id when attached to plant geometry
  - source/world coordinates when free-positioned
  - layer owner/module id

This contract should not expose storage-key internals or Django model relationships as the integration API.

## Overlay Contract Direction

`plant3d` should own generic viewer services:

- scene loading,
- object picking,
- measurement,
- snapping,
- model visibility,
- reference grid/plot layers,
- coordinate transforms,
- layer registration/display.

Consumer modules should own domain meaning:

- EHT owns DB/JB/isolator/RTD/cable draft data and persistence.
- Raceway owns tray/run/support/catalogue data and persistence.
- Future cable-routing owns route/load/fill/pulling calculations.

The viewer may host consumer tools, but the platform model must remain generic.

## Deferred Items

Deferred until the boundary is clearer or a concrete scale trigger appears:

- Celery/Redis conversion backend.
- Separate `plant3d` database/service deployment.
- Signed object-storage delivery.
- Full meshopt/Draco comparison.
- BVH picking.
- HLOD/LOD.
- Persistent EHT or raceway data models inside `plant3d` core.

## Open Correctness Gates

- **F3:** real plant-global/georeferenced IFC is still required before precision-at-scale is proven.
- **Real known-dimension source-system proof:** synthetic metre and foot fixtures are covered, but a real exporter benchmark is still needed before measurement/federation is fully trusted.
- **Largest-file conversion check:** parser threading is proven helpful on current samples, but worker sizing should be repeated on the largest available file and constrained container profile.

## Context For Claude

Please review with the following stance:

- Do not push full microservice extraction yet unless a concrete trigger is identified.
- Do not push Celery/Redis in the immediate next pass; KR has deferred it.
- Prioritise maintainability, separability, and stable contracts over new viewer features.
- Watch for accidental EHT or raceway persistence creeping into `plant3d` core.
- Watch for direct imports from EHT outside `plant3d.project_gateway`.
- Watch for templates/forms/views that expose Django relationships instead of stable identifiers.
- Help define the overlay/layer API so EHT, raceway, and future modules can share one viewer without coupling their data models.

Useful independent research topics for Claude:

1. A minimal API contract for a neutral 3D plant model service used by multiple engineering modules.
2. Overlay/layer data models used by CAD/BIM review systems, especially how annotations reference model objects and coordinates.
3. Raceway/cable tray module placement: peer `raceway` app versus EHT submodule, with attention to future cable routing and construction workflows.
4. Auth strategy for future extraction: short-lived signed tokens versus hot-path access API calls.
5. Safe orphan-reporting strategy after replacing hard project FK/cascade with loose `project_id`.

## Immediate Coding Plan

1. Add direct tests for `plant3d.project_gateway`. **Done 2026-07-05.**
2. Write the boundary/API contract record. **Done 2026-07-05: see `public-api-boundary-contract-2026-07-05.md`.**
3. Refactor or document the viewer overlay interface so current EHT draft tools are clearly a consumer adapter. **Started 2026-07-05 with the generic viewer-layer registry; continued with visible Reference Layers controls backed by the same registry.**
4. Keep UI polish scoped to low-risk engineering usability improvements.
5. Revisit raceway only after the placement decision is recorded.
