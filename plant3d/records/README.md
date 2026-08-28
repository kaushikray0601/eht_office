# plant3d Records

This folder is the project record book for the new neutral 3D engineering platform.

`plant3d` is the provisional app/bounded-context name for the EPC plant/model 3D platform. It is separate from the `idfviewer` proof-of-concept and separate from EHT production engineering.

## Folder Map

- `planning/` - architecture, implementation plans, and design discussions.
- `tracking/` - active progress trackers and execution checklists.
- `decisions/` - durable decisions that should survive implementation details.
- `audit/` - Claude/Fable reviews, scorecards, closure audits, and open-item
  registers.
- `operations/` - runbooks for local/dev/prototype operation and future container roles.
- `prompts/` - restart prompts for Codex and Claude/Fable.

## Current Durable Decisions

- `decisions/0001-platform-architecture.md` - neutral `plant3d` platform boundary and web-first modular-monolith architecture.
- `decisions/0002-viewer-completeness-and-lod.md` - engineering review must degrade fidelity before completeness.
- `decisions/0003-phase-7-rendering-spike-decision.md` - Three.js + GLB/sidecar remains accepted at current sample scale, with precision, units, conversion timing, compression, and HLOD gates still open.
- `decisions/0004-eht-overlay-integration-boundary.md` - EHT overlay persistence stays outside `plant3d` core.
- `decisions/0005-plant3d-independent-platform-boundary.md` - `plant3d` is treated as an independent platform boundary while remaining co-located during Stage 0.
- `decisions/0006-raceway-peer-app.md` - `raceway` is a peer consumer app for aboveground IEC-first raceway/tray MVP work.

## Current Active Plan

- `audit/hot-standby-pause-index-2026-08-29.md` - current pause state, restart read order, and first Phase H-A1 coding pass.
- `audit/phase-g-final-acceptance-brief-2026-08-28.md` - final Phase G closure candidate and H-A1 start rules.
- `audit/phase-g-closure-audit-2026-08-02.md` - Phase G closure audit and pass-by-pass outcome history.
- `audit/open-items-register.md` - single source of open decisions, closure dispositions, and Phase H gates.
- `audit/claude-notes-2026-07-08.md` - Claude/Fable running review notes; latest hot-standby verdict is §54.
- `audit/development-scorecard.md` - periodic scorecard and drift watch.
- `audit/markdown-housekeeping-inventory-2026-08-28.md` - keep/archive/delete classification and non-destructive records cleanup result.
- `planning/raceway-mvp-execution-plan-2026-07-08.md` - detailed execution plan for the raceway/tray MVP.
- `tracking/raceway-mvp-progress-tracker-2026-07-08.md` - detailed progress tracker for the raceway/tray MVP.
- `planning/raceway-accessory-geometry-note-2026-07-17.md` - accepted MVP accessory proxy doctrine and limitations.
- `planning/raceway-clash-pathfinding-staging-2026-08-28.md` - Clash v0/v1/v2 staging and H6 durable edge-penalty bridge for Phase H routing.
- `planning/suggestion-telemetry-design-2026-07-12.md` - Tier-0 suggestion telemetry design.
- `prompts/plant3d-hot-standby-restart-prompt-2026-08-29.md` - short prompt for restarting Codex or Claude/Fable after the pause.
- `prompts/codex-platform-reset-start-prompt-2026-07-08.md` - Codex restart prompt.
- `prompts/claude-platform-architecture-review-prompt-2026-07-08.md` - Claude/Fable architecture review prompt.
- `planning/platform-reset-handover-2026-07-08.md` - historical reset handover for the cable-routing/raceway pivot.
- `planning/platform-ecosystem-development-plan-2026-07-08.md` - post-reset ecosystem plan, now supporting context behind the Raceway closure sequence.
- `tracking/platform-ecosystem-reset-tracker-2026-07-08.md` - post-reset tracker, now supporting context behind the active Raceway tracker.
- `planning/extraction-readiness-and-claude-brief-2026-07-04.md` - extraction-readiness plan and Claude brief; now historical/supporting context behind the reset plan.
- `planning/public-api-boundary-contract-2026-07-05.md` - Stage 0 public boundary contract for project/source/job/package/object/overlay integration.

## Superseded Active Trackers

- `tracking/pipeline-spike-tracker-2026-06-22.md` remains the rendering/conversion spike history and detailed verification log, but the active development tracker is now `tracking/platform-ecosystem-reset-tracker-2026-07-08.md`.
- `tracking/platform-ecosystem-reset-tracker-2026-07-08.md` remains valid context, but day-to-day Raceway closure work is now tracked in `tracking/raceway-mvp-progress-tracker-2026-07-08.md`.

## Source Discussion

The architecture was converged from the discussion file:

- `idfviewer/records/planning/3d-platform-foundation-discussion-2026-06-21.md`

That file remains the discussion history. New finalized records should live here.
