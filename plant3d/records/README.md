# plant3d Records

This folder is the project record book for the new neutral 3D engineering platform.

`plant3d` is the provisional app/bounded-context name for the EPC plant/model 3D platform. It is separate from the `idfviewer` proof-of-concept and separate from EHT production engineering.

## Folder Map

- `planning/` - architecture, implementation plans, and design discussions.
- `tracking/` - active progress trackers and execution checklists.
- `decisions/` - durable decisions that should survive implementation details.
- `operations/` - runbooks for local/dev/prototype operation and future container roles.

## Current Durable Decisions

- `decisions/0001-platform-architecture.md` - neutral `plant3d` platform boundary and web-first modular-monolith architecture.
- `decisions/0002-viewer-completeness-and-lod.md` - engineering review must degrade fidelity before completeness.
- `decisions/0003-phase-7-rendering-spike-decision.md` - Three.js + GLB/sidecar remains accepted at current sample scale, with precision, units, conversion timing, compression, and HLOD gates still open.
- `decisions/0004-eht-overlay-integration-boundary.md` - EHT overlay persistence stays outside `plant3d` core.
- `decisions/0005-plant3d-independent-platform-boundary.md` - `plant3d` is treated as an independent platform boundary while remaining co-located during Stage 0.

## Current Active Plan

- `planning/extraction-readiness-and-claude-brief-2026-07-04.md` - current extraction-readiness plan, deferred Celery/Redis note, and Claude review/research brief.

## Source Discussion

The architecture was converged from the discussion file:

- `idfviewer/records/planning/3d-platform-foundation-discussion-2026-06-21.md`

That file remains the discussion history. New finalized records should live here.
