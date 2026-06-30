# Decision 0003 - Phase 7 Rendering Spike Decision

Date: 2026-06-30

Status: accepted for current sample scale; EPC-scale precision and conversion proof remain open

## Context

The `plant3d` spike set out to test whether a web-first Django + Three.js platform can become the neutral 3D model foundation for the wider EPC electrical engineering ecosystem.

The critical question was not whether a browser can show a small model. The critical question was whether the architecture can move beyond the `idfviewer` prototype toward a robust model platform:

- source IFC ingestion
- async conversion jobs
- runtime render packages
- GLB/binary geometry instead of large JSON geometry
- object identity and metadata lookup
- tiled packages with RTC/tile-local coordinates
- complete-review behavior for engineering trust
- enough viewer performance to justify continuing Three.js-first

## Evidence

Current strongest manual evidence is the clean-DB run for `8-SSPAU-800203.ifc`:

- source size: about 13.4 MB
- objects: 4,313
- child tiles: 9
- package bytes: 16,050,726
- render triangles: 715,028
- loaded tiles: 9/9
- draw calls: 36
- browser heap: about 22 MB
- pick latency: about 5 ms
- viewer load time after package availability: about 287 ms
- FPS: 60 on the GTX 1050 Ti development machine
- WebGL renderer: ANGLE / NVIDIA GeForce GTX 1050 Ti / D3D11

Manual comparison against `idfviewer` also showed:

- conversion/load time at 10-15 MB scale is broadly similar, not yet a visible win
- `plant3d` now feels lighter during movement
- visual quality became acceptable after antialiasing/material/selection-highlight corrections
- complete-review mode fixed the unacceptable missing-geometry behavior for manageable packages

Conversion remains the major unresolved performance question:

- one 13.4 MB sample conversion was about 66 seconds through the worker
- Windows Task Manager showed CPU around 40% and GPU mostly idle during conversion
- this is expected because conversion is CPU/IO-side IfcOpenShell + packaging, not browser GPU rendering
- per-stage timing instrumentation now exists, but the post-instrumentation 66 second timing split still needs to be read from a fresh package

## Decision

Continue with the Three.js-first, browser-side rendering architecture for the next platform phase.

Continue using GLB + metadata sidecar + 3D-Tiles-style package manifests as the first serious runtime package direction.

Keep the current JSON geometry package only as a debug/comparison path.

Treat complete-review mode as the correct default for manageable packages. Do not silently show incomplete geometry to engineering users. For larger packages, partial streaming is acceptable only when the viewer clearly reports partial/incomplete state.

Keep feature-ID based picking as the production direction for GLB packages. Do not reintroduce hidden per-object pick-proxy geometry for GLB.

Keep BVH acceleration deferred until real pick latency regresses on larger samples. Current direct render-mesh picking is acceptable at 715k triangles and 36 draw calls.

## Current Acceptance

Accepted at current sample scale:

- Three.js/WebGL2 is sufficient for current GLB package sizes.
- Browser GPU rendering is not the immediate bottleneck at current scale.
- GLB + sidecar is a better runtime package than JSON geometry.
- Spatial child tiles plus RTC metadata are the correct package shape.
- Complete-review mode is necessary for engineering trust.
- Feature-ID picking with backend metadata lookup is viable.

Not accepted yet:

- EPC-scale plant-global precision.
- Final source/render unit trust for real exporter workflows.
- Final conversion performance strategy.
- Final compression strategy.
- Final large-model LOD/HLOD strategy.
- Final object-storage/signed-URL delivery strategy.

## Open Gates

### F3 - Plant-Global Precision

The current real samples are not enough to prove float32 behavior at true plant-global or georeferenced coordinates.

Before claiming production coordinate robustness, test a real large-coordinate IFC or equivalent plant-global sample:

- conversion succeeds
- GLB positions stay tile-local
- RTC origins remain frame-correct
- orbit/pan/zoom show no jitter
- object picking still resolves metadata
- future measurement/snap tests remain stable

### C3/F4 - Real Known-Dimension Proof

Synthetic metre-declared and foot-declared one-metre fixtures now prove the service contract. A real source-system/exporter known-dimension benchmark is still needed before measurement/federation workflows are trusted.

### PERF1/PERF2 - Conversion Timing And Parser Threads

The next measurement must read the per-stage timing breakdown for a real post-instrumentation GLB conversion.

If `parse_ms` dominates, evaluate configurable IfcOpenShell geometry iterator thread count for worker containers.

If tile writing or storage dominates, do not tune parser threads first; investigate storage/write batching instead.

Any parser thread change must preserve stable object identity. Feature IDs are render-package-local and must not become persistent identity keys.

### LOD/HLOD

Current complete-review mode is good for manageable packages, but it cannot be the only answer for very large EPC models.

Production large-model viewing will need coarse complete representations plus streamed detail tiles.

## Consequences

- Do not spend the next passes on general viewer polish.
- Do not switch to Babylon.js or desktop rendering based on current evidence.
- Do not adopt Draco/meshopt based on byte reduction alone; picking/feature-ID correctness and decode behavior remain gates.
- Do not claim final EPC-scale viability until F3 and real conversion timing proof are complete.
- Continue the pipeline spike toward measurement, precision proof, and worker/container performance choices.

