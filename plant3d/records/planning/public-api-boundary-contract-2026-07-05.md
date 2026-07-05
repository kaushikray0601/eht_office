# plant3d Public API Boundary Contract

Date: 2026-07-05
Status: Stage 0 contract draft

## Purpose

This record defines the boundary that EHT, raceway, cable routing, construction, and future modules should use when integrating with `plant3d`.

`plant3d` is currently a co-located Django app, but the contract should be shaped as if it will later become a separately deployable service. Code may still call local Django views/helpers in Stage 0, but module boundaries should use the same concepts this future service API will expose.

## Core Rule

Consumer modules may reference `plant3d` anchors. They must not own or mutate `plant3d` internals.

Allowed anchors:

- `project_id`
- source model id
- conversion job id
- render package id
- render tile id/tile id
- model object `stable_id`
- package-local feature id when paired with a package id
- source/world coordinates with an explicit coordinate frame
- overlay/layer id owned by the consumer module

Not stable integration contracts:

- storage keys,
- Django model relationship names,
- database foreign keys to EHT or raceway models,
- GLB buffer layout details,
- private parser output structures,
- temporary browser draft ids.

## Project Boundary

Stage 0 project access is mediated by `plant3d.project_gateway`.

Responsibilities:

- list accessible project ids for a user,
- provide project picker options,
- validate a project id at write time,
- normalize object/string project identifiers.

Current implementation detail: the gateway still imports EHT models internally. No other `plant3d` runtime module should import EHT project models directly.

Future service direction: replace the gateway internals with signed-token or API-based authorization without changing the rest of `plant3d`.

## Source Model Contract

A source model represents an uploaded/federated source file.

Stable external fields:

- source id,
- `project_id`,
- display name,
- source format,
- original filename,
- source system,
- file size,
- content signature,
- created/updated timestamps,
- saved-case flag.

Consumer modules may link their work to a source id and `project_id`.

Consumers should not depend on source storage keys. Blob delivery may move from local Django storage to object storage or signed URLs.

## Conversion Job Contract

A conversion job represents asynchronous processing of a source model.

Stable external fields:

- job id,
- source id,
- job type,
- status,
- progress percent,
- stage,
- started/completed timestamps,
- metrics payload,
- package URL when completed,
- error summary when failed.

Current Stage 0 worker:

```bash
venv/bin/python manage.py process_plant3d_job --watch --parser-threads auto
```

Future infrastructure may replace this with Celery/Redis or another queue. Consumer modules should depend on the job status contract, not the worker mechanism.

## Render Package Contract

A render package is the browser/runtime package for one converted source.

Stable external fields:

- package id,
- source id,
- format,
- package byte count,
- object count,
- tile count,
- coordinate unit,
- coordinate frame metadata,
- package origin/RTC metadata,
- package JSON URL,
- viewer URL.

Consumer modules may deep-link to the viewer URL or request package metadata by package id.

Consumer modules should not depend on current Django blob URLs staying permanent. Blob transport may later become signed object-storage URLs.

## Tile And Blob Contract

Tiles are implementation units for loading/rendering.

Stable external fields:

- render tile id,
- logical tile id,
- package id,
- tile origin/RTC metadata,
- tile bounds,
- byte count,
- GLB/blob URL,
- sidecar/object metadata URL.

Consumers should treat tile URLs as read-only delivery artifacts. They are not a semantic ownership boundary.

## Model Object Contract

A model object is the semantic pickable object extracted from a source model.

Stable external fields:

- object id,
- source id,
- package id when applicable,
- `stable_id`,
- source object id/GUID where available,
- object type/class,
- name/tag,
- hierarchy path/group,
- bounds,
- source/render coordinate metadata,
- package-local feature id when applicable.

Important identity rule:

- `stable_id` is the durable integration key.
- Feature ids are package-local render keys and must not be stored by external modules as durable identity.

## Coordinate Contract

Every integration point must name its coordinate frame.

Current important frames:

- source/world frame from IFC/source metadata,
- render frame used by GLB/Three.js,
- tile-local frame after RTC origin subtraction,
- screen/canvas frame for browser interaction.

External overlay data should store source/world coordinates or explicit anchors to model object `stable_id`s. Browser-local coordinates are not enough for persistence.

## Overlay / Layer Contract

`plant3d` owns generic overlay hosting:

- layer registration,
- scene attachment,
- picking bridge,
- snap/measurement helpers,
- coordinate transforms,
- visibility/hide/show controls,
- viewer session state.

Consumer modules own domain meaning:

- EHT owns DB/JB/isolator/RTD/cable data.
- Raceway owns tray runs, supports, fittings, catalogues, and routing graph data.
- Cable routing owns cable path/fill/pulling calculations.

Generic overlay anchor shape:

- owner module: for example `eht`, `raceway`, `review`,
- layer id,
- element id,
- package id/source id,
- optional model object `stable_id`,
- coordinate frame,
- points/geometry parameters,
- style/classification metadata,
- editability/visibility flags.

Do not add EHT or raceway persistence models to `plant3d` core. If `plant3d` later stores generic overlay review layers, they must be domain-neutral and owner-scoped.

## Viewer Contract

The viewer may host tools from multiple modules, but the platform responsibilities are limited to:

- loading and displaying the package,
- exposing object selection and metadata,
- measuring and snapping,
- showing/hiding model features and overlay elements,
- managing reference layers,
- routing user interactions to registered overlay tools.

Viewer features should be built against the generic overlay/layer contract where practical. Module-specific labels may appear in an adapter, not in core platform storage.

## Access And Data Safety

Every source/package/tile/object endpoint must enforce project access.

Access checks should use `project_id` and the project gateway seam in Stage 0. Future service extraction should replace this with a token/API-backed implementation without changing the endpoint semantics.

After replacing hard foreign keys with loose references, future housekeeping should include an orphan report for `plant3d` rows whose `project_id` no longer resolves through the project gateway.

## Deferred API Decisions

Deferred until concrete extraction pressure appears:

- OpenAPI schema format and versioning policy,
- signed-token payload format,
- object-storage signed URL expiry policy,
- Celery/Redis task API shape,
- separate service database schema,
- webhook/eventing model for conversion completion.

## Immediate Implementation Checks

- Keep EHT project imports confined to `plant3d.project_gateway`.
- Add tests around project gateway access/list/validate behavior.
- Keep overlay persistence out of `plant3d` until the generic layer contract is proven.
- Treat raceway as a likely peer consumer app, not an EHT subfeature, pending KR decision.
