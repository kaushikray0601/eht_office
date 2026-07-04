# Decision 0005 - plant3d Independent Platform Boundary

Date: 2026-07-04

Status: accepted for Stage 0 implementation

## Context

`plant3d` has moved beyond an EHT viewer spike. It now owns source-model intake, conversion jobs, GLB/tile packages, model object identity, model selection, measurement, visibility, generic overlay UI, and worker-oriented conversion behavior.

The product direction is also broader than EHT:

- EHT design should consume the 3D platform.
- Raceway/cable tray should consume the 3D platform.
- Cable routing, cable pulling, construction management, review, and future engineering modules should consume the same platform.

Keeping `plant3d` as an ordinary EHT sub-application would recreate the coupling the platform was created to avoid.

## Decision

Treat `plant3d` as an independent 3D engineering platform boundary, currently co-located in this Django repo for development convenience.

`plant3d` may remain in the current monorepo and Django project during Stage 0, but it must be designed as a future service provider with its own deployable web/API role, worker role, queue/broker, storage, and eventually its own database.

EHT and other engineering modules must integrate with `plant3d` through stable project/source/package/object/layer identifiers and API-like seams, not by adding module-specific persistence into `plant3d` core.

## Stage 0 Scope

Stage 0 makes the boundary real without paying the full service-extraction cost.

Accepted Stage 0 actions:

- Replace the hard `SourceModel.project -> eht.ProjectData` database foreign key with a loose `project_id` reference.
- Remove the `on_delete=CASCADE` risk where deleting an EHT project silently deletes `plant3d` source models and render packages.
- Add an explicit project gateway seam responsible for:
  - accessible project ids,
  - project picker enumeration/display,
  - project id validation at write time.
- Keep the current implementation of that seam backed by EHT models while the applications are co-located.
- Keep EHT-specific persistence out of `plant3d` core.

Stage 0 does **not** claim complete decoupling. It relocates the `plant3d -> eht` Python dependency into one named seam so Stage 1 can replace that seam with token/API-based integration.

Current sequencing note, accepted after Stage 0 testing: Celery/Redis is deferred. The immediate focus is extraction readiness, public boundary contracts, overlay/layer integration seams, and disciplined continued viewer/tool development. The existing management-command worker remains the development path until the boundary is stable enough to justify queue infrastructure work.

## Deferred Stage 1

Move to a separately deployable `plant3d` service when a concrete trigger appears, such as:

- raceway or another non-EHT module becomes a real second consumer,
- EHT release cadence conflicts with `plant3d` development,
- shared database/resource contention becomes real,
- `plant3d` needs independent packaging or commercial deployment,
- auth/API boundaries are ready to support service separation.

Stage 1 should prefer a same-repo separate deployable first. A separate repository is deferred until a separate team, licensing/commercial packaging, or CI/release pressure justifies it.

## Future Auth Direction

For service extraction, prefer short-lived signed tokens over hot-path access API calls.

The token should carry enough scoped identity for `plant3d` to authorize project/package/object access without calling EHT on every viewer request:

- user id,
- accessible project ids or project roles,
- expiry,
- future tenant/company scope if needed.

## Consequences

- Existing source models keep their `project_id` values as plain strings.
- Deleting an EHT project no longer cascades into `plant3d`; future orphan checks can report `plant3d` rows whose `project_id` no longer resolves.
- Upload forms and access checks use `plant3d.project_gateway`, not direct `ProjectData` or `ManagedProject` imports outside that seam.
- The current EHT-backed gateway is a temporary adapter, not the final integration architecture.
- Consumer modules should reference `plant3d` anchors instead of embedding 3D model data.
