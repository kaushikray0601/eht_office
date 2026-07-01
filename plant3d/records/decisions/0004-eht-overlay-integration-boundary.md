# Decision 0004 - EHT Overlay Integration Boundary

Date: 2026-07-02

Status: accepted before backend persistence

## Context

The `plant3d` viewer now has a first browser-side EHT draft palette for parity with the older `idfviewer` prototype:

- distribution board
- junction box
- isolator
- RTD
- end termination
- pipe strap
- SR tracer route
- MI tracer route
- cold cable route

This is useful and intentionally close to the user workflow that already existed in `idfviewer`.

However, `plant3d` was created as a neutral 3D model platform for many EPC electrical engineering modules, not as an EHT-only application. If EHT persistence models are added directly to `plant3d/models.py`, the neutral platform boundary will be blurred again.

## Decision

Keep `plant3d` core EHT-neutral.

`plant3d` owns:

- source model intake
- conversion jobs
- render packages
- render tiles
- model object identity
- viewer package APIs
- generic viewer shell and model selection hooks

EHT-specific overlay persistence should live in an EHT/integration boundary, not in `plant3d` core.

The future persistence model should reference `plant3d` entities rather than embed them:

- project
- source model or render package
- optional model object anchors
- EHT element type
- EHT geometry payload
- EHT-specific metadata

The browser viewer can continue to render EHT tools because it is the shared viewer surface, but saved EHT data must be loaded/saved through an EHT-owned API.

## Consequences

- The current EHT palette remains a browser draft overlay until the EHT integration backend is added.
- Do not add `EhtDesignElement` or EHT calculation fields to `plant3d/models.py`.
- The next backend pass should either use the existing `eht` app or a deliberately named integration app that depends on `plant3d`, not the other way around.
- `plant3d` should expose stable object/package anchors that consumer modules can reference.
- This keeps cable optimization, construction/cable-pulling modules, EHT design, and future engineering modules free to consume the same 3D platform.

## Related UI Decision

The model object hierarchy currently provides search, focus, and list filtering only.

It must not present inert visibility checkboxes for merged GLB geometry. True per-object hide/show needs a future feature-mask/shader or package-filtering implementation. EHT draft overlay visibility is different: draft elements are separate browser objects, so EHT type/element visibility checkboxes are valid and may remain.
