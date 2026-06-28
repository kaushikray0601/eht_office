# Decision 0002 - Viewer Completeness And LOD Strategy

Date: 2026-06-28

Status: accepted for the current spike; HLOD remains future work

## Context

Manual side-by-side testing against `idfviewer` showed a serious viewer regression in `plant3d`: the GLB tile streaming cap could show an incomplete structure. Rotating the camera could also unload geometry that had already appeared while new tiles loaded.

The root cause was not proven compression loss. The current regression came from the viewer's active-tile strategy: it capped loaded child tiles at 6 and unloaded non-active tiles immediately. That is acceptable for a technical streaming experiment, but not for engineering review.

## Principle

Degrade fidelity before degrading completeness.

An engineering reviewer must not silently see holes in the plant. If the viewer is showing a partial model, that state must be explicit and persistent.

## Decision

For the current spike:

- Small and medium GLB packages use complete review mode.
- Complete review mode loads all child GLB tiles and keeps them resident.
- Partial active streaming is reserved for larger packages only.
- Partial streaming must report that the visible model is partial.
- Partial streaming retains previously loaded tiles up to a larger cache budget instead of unloading immediately on camera movement.

Current viewer thresholds:

- Complete review mode: up to 24 GLB tiles and 64 MB package bytes.
- Partial streaming detail cap: 6 active tiles.
- Partial streaming retained cache: 18 loaded tiles.
- Unload grace period: 4 seconds after a tile leaves the active set.

These thresholds are spike defaults, not production promises.

## Future Work

For real EPC-scale models, complete loading may not fit browser memory. The production answer is HLOD/coarse proxy geometry:

- Keep a coarse complete representation visible.
- Stream detailed child tiles as camera position and zoom require.
- Evict detail under memory pressure while retaining coarse coverage.
- Avoid presenting empty holes as if they were complete model state.

Dashed or faint bounding boxes for unloaded tiles are acceptable as an interim "honest partial" indicator, but they are not a substitute for HLOD.

## Non-Decisions

- This decision does not switch renderer.
- This decision does not choose Draco over meshopt.
- This decision does not implement annotation persistence.
- This decision does not claim current tiling is production-tuned.
