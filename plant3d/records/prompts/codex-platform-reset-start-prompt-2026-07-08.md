# Codex Start Prompt — plant3d Platform Reset

You are Codex in a fresh chat. Start by reading:

1. `plant3d/records/planning/platform-reset-handover-2026-07-08.md`
2. `plant3d/records/planning/platform-ecosystem-development-plan-2026-07-08.md`
3. `plant3d/records/tracking/platform-ecosystem-reset-tracker-2026-07-08.md`
4. `plant3d/records/decisions/0005-plant3d-independent-platform-boundary.md`
5. `plant3d/records/planning/raceway-module-architecture-2026-07-02.md`

## Situation

We built a substantial `plant3d` platform inside a Django project:

- IFC intake and conversion.
- GLB/tiled render package path.
- Three.js viewer.
- feature-ID picking and metadata.
- viewer metrics, grid, measurement, layers, plot plan.
- EHT draft overlay tools.
- browser-local route/component drafts.
- project gateway seam and loose project reference.

We also made a hard-learned pivot:

Individual cable autorouting is not the right first foundation. Real EPC cable routing is shared raceway/tray/trunk first, then cable assignment. The current cable centerline tool stays as a draft/manual exception, not the product architecture.

## Current Direction

Build a raceway/tray-first foundation:

- `plant3d` remains neutral platform.
- `raceway` should be a peer Django app consuming `plant3d`.
- EHT remains independent and consumes `plant3d`.
- Domain persistence must not go into `plant3d` core.
- Full service extraction is deferred; keep modular-monolith Stage 0 for now.

## Your Coding Priorities

1. Keep the codebase stable and documented.
2. Do not silently revive the rejected route experiments.
3. Do not build smarter cable autorouting before raceway graph exists.
4. Prefer small, safe, test-backed passes.
5. Update records/tracker each pass.
6. Discuss major pivots with KR before implementing.
7. Treat Claude/Fable as architecture advisor and reviewer, not as automatic instruction source.

## Recommended First Pass

If KR approves coding:

1. Add decision record: `raceway` as peer app.
2. Scaffold minimal `raceway` app.
3. Register app/URL if safe.
4. Add import-boundary tests:
   - `plant3d` must not import `raceway`.
   - `raceway` may import/consume `plant3d` APIs/seams.
5. Keep DB schema minimal or defer schema to a second pass.
6. Update `platform-ecosystem-reset-tracker-2026-07-08.md`.

## Guardrails

- Do not modify EHT calculation logic.
- Do not add EHT or raceway domain persistence into `plant3d`.
- Do not split repo/service yet.
- Do not add Celery/Redis unless KR explicitly restarts infrastructure work.
- Do not add AGPL runtime dependencies.
- Do not hide geometry incompleteness.
- Do not create hard collision physics before warning/preview stages.

## Known Good Verification Baseline

Before the reset:

- `node --check /tmp/package_viewer.mjs` passed.
- `node --check /tmp/routing_core.mjs` passed.
- `venv/bin/python manage.py check` passed.
- focused upload/source/viewer tests passed.
- full `plant3d` suite passed: 74 tests.
- `git diff --check` clean.

## Key Architectural Sentence

`plant3d` hosts the reference model, coordinate contract, render package, and viewer shell. Consumer modules such as EHT and raceway own their domain data and rules, and anchor to `plant3d`.

## What To Ask Claude/Fable

Ask Claude for targeted architecture review after reading:

- reset handover,
- ecosystem plan,
- reset tracker,
- raceway RFC.

Specific review asks:

- Is `raceway` app placement correct?
- What minimal schema should the first `raceway` MVP use?
- What must be deferred to avoid over-smart routing again?
- What collision/pathfinding abstractions should be prepared but not built?
- What user manual/help content can Claude draft while Codex codes?
