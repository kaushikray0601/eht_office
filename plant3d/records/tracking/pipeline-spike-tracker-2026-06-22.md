# plant3d Pipeline Spike Tracker

Date: 2026-06-22

Status: render/conversion spike accepted at current sample scale; current focus is extraction readiness, stable platform boundaries, and disciplined viewer/tool maturation

## Objective

Prove the first source-file-to-browser pipeline for the new 3D platform before building a polished workspace UI or broad semantic model.

The spike should answer:

- Can the web-first platform render real IFC/model data acceptably?
- What conversion/package strategy should become the first platform foundation?
- What metadata and precision fields are required from day one?
- How much of the current `idfviewer` prototype should be harvested?

Post-spike objective, accepted 2026-07-04:

- Keep developing `plant3d` as a neutral 3D engineering platform that can later run as an independent service.
- Loosen EHT coupling without throwing away the proven GLB/Three.js/tiled-viewer work.
- Keep EHT, raceway, cable routing, and future engineering modules as consumers of `plant3d`, not owners of `plant3d` internals.
- Defer Celery/Redis and full service/database extraction until the platform boundary, API contract, and overlay integration seams are stable.

## Guardrails

- Do not modify EHT production calculation logic.
- Do not modify cold cable engineering logic.
- Do not modify SLD/topology/reporting workflows.
- Do not promote `idfviewer` as the final platform foundation.
- Do not create a full semantic database before the render pipeline is proven.
- Do not introduce strict microservices or event-bus architecture.
- Do not adopt AGPL runtime dependencies without explicit future decision.

## Phase 0 - Records And Boundary

- [x] Create `plant3d/records/` as the new platform record area.
- [x] Record agreed architecture.
- [x] Record execution tracker.
- [x] Decide whether to create a minimal Django app skeleton now or after Claude final review.
- [x] Decide provisional app label/name for code: `plant3d` unless changed.
- [x] Create minimal Django app boundary: `plant3d`.
- [x] Register `plant3d` in `INSTALLED_APPS`.
- [x] Add `/plant3d/` URL boundary.

## Phase 1 - Spike Inputs

- [ ] Collect one real project IFC around 20 MB.
- [x] Collect public/sample IFC files.
- [x] Record initial source file provenance, expected units, source system if known, and rough model content for available local IFC samples.
- [ ] Add one IDF or PCF sample later for federation checks.
- [x] Identify whether any available IFC has large plant/global coordinates.
- [x] Check current workspace for IFC samples.
- [x] Add IFC samples to a known local test/input location or upload through `/plant3d/sources/upload/`.

## Phase 2 - Minimal Platform Skeleton

- [x] Create neutral Django app/bounded context.
- [x] Add minimal records/models only if needed for the spike:
  - `SourceModel`
  - `ConversionJob`
  - `RenderPackage`
  - `RenderTile`
  - optional early `ModelObject`
- [x] Keep schema narrow and reversible.
- [x] Add tests for model creation, job status, and package/tile metadata if models are created.
- [x] Add local/self-hosted storage-key helpers for source and render package paths.
- [x] Add storage interface helpers so services use storage keys rather than direct filesystem `Path` operations.
- [x] Add containment guard for storage-key path resolution.
- [x] Add minimal source upload form and endpoints.
- [x] Add JSON source listing endpoint.
- [x] Add metadata conversion trigger endpoint.
- [x] Add managed-project access scoping for source/package/tile views and APIs.
- [x] Add duplicate-upload reuse by project/content signature.
- [x] Change conversion endpoints to enqueue jobs instead of running conversion inside HTTP requests.
- [x] Add `process_plant3d_job` management command for off-request spike processing.
- [x] Add `process_plant3d_job --all` to drain all queued spike jobs in FIFO order.
- [x] Add job status JSON endpoint.
- [x] Add job/package URLs to queue and job-status JSON responses.
- [x] Add lightweight source-detail polling so queued/running jobs update in-place.
- [x] Apply `plant3d.0001_initial` migration in local development database after upload URL exposed missing table.

## Phase 3 - Conversion Experiment

- [x] Add metadata-only conversion scaffold.
- [x] Write first render-package manifest blob.
- [x] Record conversion job, package, and tile metadata for the scaffold.
- [x] Add first IFC geometry conversion service using the existing Python/IfcOpenShell parser path.
- [x] Extract the IFC parser dependency into `plant3d/parsers/` after first real-file measurements, so plant3d no longer imports the `idfviewer` lab parser at runtime.
- [x] Produce first JSON geometry runtime package from stored IFC source blobs.
- [x] Record IFC geometry conversion job, package, tile, mesh count, byte size, and object index metadata.
- [x] Add package/tile JSON API URLs so the browser does not depend on storage-key details.
- [x] Wrap conversion package/tile/object-index writes in database transactions.
- [x] Keep queued -> running -> completed/failed state transitions real for management-command processing.
- [x] Keep the source-detail page polling queued/running jobs until completion and show worker command hints clearly.
- [x] Run the IFC geometry conversion against real project/sample IFC files and record actual metrics.
- [x] Evaluate first GLB/glTF output path with a binary GLB tile plus metadata sidecar.
- [x] Add feature/object IDs to the first GLB path before treating GLB as more than a render smoke test.
- [x] Add optional meshopt/gltfpack compression hook and viewer decoder support.
- [ ] Measure real meshopt compression ratio and decode/load time after `gltfpack` is available in the worker image.
- [x] Record metadata-manifest output size.
- [x] Record sample-file geometry conversion time and output size.
- [x] Record extracted units, bounds, object count, and coordinate frame assumptions for available samples.
- [x] Add IFC header length-unit hint extraction and propagate unit warnings into metadata/package/tile/job records for new conversions.
- [x] Extract IFC `IfcUnitAssignment` declared length units through the plant3d parser and store render-unit-vs-source-unit evidence in package/tile/job metadata.
- [ ] Repeat conversion metrics against the target 20 MB real project IFC.

## Phase 4 - Tiling And Precision Experiment

- [x] Create a tiled or chunked package manifest.
- [x] Define glTF axis convention before expanding GLB output: GLB buffers use current `render_xyz_m` frame, source Z is emitted as glTF/Three.js Y-up, and no additional root transform is applied.
- [x] Start a primitive 3D-Tiles-style `tileset.json` manifest after feature IDs are in the single-tile GLB.
- [x] Split GLB output into first spatial child tiles under the `tileset.json` root.
- [x] Add viewer-side tile culling/streaming so child tiles are not all loaded at once.
- [x] Add tile-local origin/RTC metadata for the current single JSON geometry tile.
- [x] Store the source-coordinate origin on the tile row and tile payload.
- [x] Add transform metadata showing source axis/order, render axis/order, origin, and scale.
- [x] Separate raw/source origin from render-frame RTC origin so the origin is in the same frame as viewer vertices.
- [x] Test that `rtc_origin_render_xyz + local_position` reconstructs source coordinates after reversing scale and Y/Z swap.
- [x] Test that large source coordinates are represented by RTC origin while render coordinates remain local/small.
- [ ] Test whether large coordinates create visible jitter without RTC using a real file.
- [ ] Test whether RTC/tile-local rendering improves measurement and orbit stability.

## Phase 5 - Browser Viewer Spike

- [x] Build a minimal Three.js viewer for the JSON spike package.
- [x] Load JSON geometry package/tile manifest through platform APIs.
- [x] Load first GLB package tile through the same package API using Three.js `GLTFLoader`.
- [x] Show basic runtime metrics: loaded meshes, triangles, tiles, load time, package bytes, raw bounds.
- [x] Show tile RTC origin in runtime metrics.
- [x] Show live browser-side FPS, draw calls, and WebGL geometry/texture counters.
- [x] Show adaptive viewer quality state and effective renderer pixel ratio.
- [x] Render merged color-bucket geometry rather than one visible mesh per object for the JSON debug viewer.
- [x] Keep per-object pick proxies outside the rendered scene so metadata picking still works with merged visible geometry.
- [x] Show basic model/package bounds in the viewer sidebar.
- [x] Add basic object picking and highlight in the viewer.
- [x] Add minimal metadata panel backed by `ModelObject` API.
- [x] Add first GLB feature-ID click-to-metadata path without hidden per-object pick proxies.
- [x] Add interaction-time adaptive pixel ratio and high-performance WebGL context for smoother orbit/pan on heavy packages.
- [ ] Avoid polishing UI beyond what is needed to measure the pipeline.
- [x] Verify viewer with real converted IFC packages using Playwright screenshot/pixel checks through a temporary static probe.

## Phase 6 - Measurement And Acceptance Metrics

Record at minimum:

- [x] Source file size.
- [x] Conversion time.
- [x] Runtime package size.
- [x] Browser load time.
- [x] Draw call count.
- [x] Browser memory use where measurable.
- [x] FPS during orbit/pan/zoom.
- [x] Selection/picking latency.
- [x] Metadata lookup latency.
- [ ] Visual stability at real coordinates.
- [ ] Snapping/measurement stability where tested.

Measurement hooks now implemented:

- [x] Conversion jobs record `conversion_duration_ms` in job metrics.
- [x] Source detail page surfaces job metrics after processing.
- [x] Viewer sidebar reports draw calls and rough FPS during orbit/pan/zoom.
- [x] Viewer sidebar reports WebGL geometry and texture counts.
- [x] Viewer sidebar reports effective pixel ratio and adaptive quality mode.
- [x] Viewer sidebar reports render batch count, pick proxy count, pick latency, and metadata lookup latency.
- [x] Viewer sidebar reports browser JS heap where Chromium exposes `performance.memory`.

Acceptance thresholds for the first real IFC spike:

- [ ] FPS during orbit/pan should be at least 30 sustained; 60 is the goal.
- [ ] Draw calls should stay in the low hundreds, not thousands, after batching/instancing work begins.
- [ ] Browser tab memory should stay under roughly 2 GB for first target files.
- [ ] There should be zero visible jitter at true plant coordinates.
- [ ] Pick latency should be under 100 ms once picking is added.
- [ ] Pick-to-metadata lookup should be under 200 ms once metadata lookup is added.
- [ ] Conversion time must be recorded, but is not initially a hard gate.

Decision rules:

- [ ] Precision failure means fix package coordinate format/RTC strategy before changing renderer.
- [ ] FPS failure after batching/instancing/LOD means compare Babylon.js or another renderer path.
- [ ] JSON payload size or parse-time failure means move to GLB/binary tiles; do not keep expanding JSON.
- [ ] Binary package proof requires format + RTC + precision to be validated together on a plant-global/georeferenced file.

## Phase 7 - Decision Report

- [x] Summarize whether Three.js-first remains acceptable.
- [x] Summarize whether Babylon.js comparison is needed.
- [x] Summarize whether GLB/glTF is enough or tiled/custom packages are mandatory.
- [x] Summarize whether first available IFC samples are sufficient or larger EPC files are required.
- [x] Recommend production model shape after spike.
- [x] Recommend next implementation pass.

Decision record: `plant3d/records/decisions/0003-phase-7-rendering-spike-decision.md`.

Phase 7 status: accepted for current sample scale only. F3 plant-global precision, real source-system known-dimension proof, conversion timing/PERF2, production object-storage delivery, and LOD/HLOD remain open gates.

## Current Risks

- 20 MB IFC is useful but may be too small to prove EPC-scale viability.
- Public sample IFC files may not represent plant-global coordinates.
- IfcOpenShell conversion may be slow or heavy for large files.
- Package-55 metrics moved the current bottleneck: rendering/picking is healthy at 715k triangles, 36 draw calls, 60 FPS, 22 MB heap, and 5 ms pick latency. The 2026-07-01 timing run then proved the conversion bottleneck is IfcOpenShell parse/tessellation: 59,656 ms parse out of 61,073 ms total, with parser threads at the default 1. The follow-up `--parser-threads auto` run reduced total conversion to 11,826 ms and parse time to 10,411 ms, with CPU rising to about 97% and RAM stable around 30%.
- Worker parser-thread selection needs deployment sizing: `auto` is appropriate for a roomy local/dev worker, and now considers Docker/Linux CPU and memory cgroup limits where available. Shared cloud Docker hosts should still use `--parser-thread-cap` or a fixed thread count to avoid starving database and sibling containers.
- KR manual comparison against `idfviewer` found that 10-15 MB IFC conversion/render time is roughly comparable between the old prototype and `plant3d`, so the immediate user-visible gap is not speed at this scale. `idfviewer` still feels visually cleaner on beam edges, while `plant3d` feels slightly lighter during movement. The next viewer passes should preserve completeness and responsiveness while improving visual fidelity and selected-object feedback.
- Naive Three.js object-per-mesh rendering will not scale.
- Coordinate precision problems may not show unless source files use large coordinates.
- Browser memory and draw calls can become the limiting factor before triangle count.
- Manual side-by-side review against `idfviewer` exposed a serious viewer completeness issue: active-cap tile streaming can show holes or incomplete steelwork, and camera rotation can unload previously visible geometry while new tiles load. This is expected from the first cap/unload algorithm but unacceptable for production engineering review. The immediate mitigation is now complete/review mode for manageable packages, persistent completeness status, and retained-cache partial streaming for larger packages. HLOD/coarse proxies remain the future production answer.
- Conversion now runs off-request through a management-command worker for the spike. Full Celery/RQ/SSE infrastructure is still required before user-facing or long-running production workflows.
- The spike worker now has a documented long-running container role in `plant3d/records/operations/worker-container-runbook-2026-06-28.md`; local/manual operation should use `process_plant3d_job --watch`, not repeated `--all` runs.
- The IFC parser is now copied under `plant3d/parsers/`, closing the immediate platform-boundary dependency on `idfviewer`. Future parser refactor/shared ownership is still possible.
- Package/tile JSON and GLB blobs are still served through Django. This is acceptable for the spike, and these endpoints now support immutable ETag-based reuse, but real-scale deployment should still move toward signed object-storage URLs/CDN delivery.
- Working source uploads are now disposable per user/project. A normal upload through the UI replaces the prior unsaved working source for that same user and project, while explicit saved geometry cases are protected and capped at five per user/project.
- First GLB package output is now available and is materially smaller than JSON on the tested samples, but still served through Django during the spike.
- Claude's render-format research confirms the next serious stack direction: GLB + meshopt + GPU instancing + feature IDs, arranged by a 3D-Tiles-style manifest and rendered in Three.js with `3d-tiles-renderer` / `three-mesh-bvh` where needed. The current GLB pass is a smoke-test step, not the final runtime format.
- RTC metadata is now frame-correct for the current single-tile JSON package, and first spatial GLB child tiles now carry per-tile RTC origins. Real-file proof of tile-local precision/orbit stability remains pending.
- The debug viewer now reduces visible draw calls by merging geometry by color, but object picking currently keeps per-object geometry proxies in memory. This is acceptable for the spike but not a final large-model strategy.
- Source-detail job polling is a practical spike bridge, not the final progress architecture. Production still needs a real worker process plus SSE/WebSocket or push-style progress.
- Source-detail polling must keep polling queued/running jobs until the worker completes them. A bug briefly made the page poll only once, which could hide completed package links until manual refresh.
- Real sample conversion exposed a unit-confidence risk. The parser now reports source-declared IFC units separately from render units: Revit sample declares `ft`, Tekla samples declare `mm`, while IfcOpenShell geometry settings report metre output (`length-unit=1.0`, `convert-back-units=False`). A known-dimension scale fixture is still required before trusting measurement/federation workflows.
- JSON expansion is already visible on small samples; one 2.8 MB Tekla IFC produced a 10.5 MB JSON tile.
- GLB reduces payload size materially on first samples: Revit JSON 1.51 MB -> GLB 0.56 MB plus 0.03 MB sidecar; Tekla JSON 10.49 MB -> GLB 5.38 MB plus 0.17 MB sidecar. Conversion time remains dominated by IFC parsing.
- Browser probe rendered all three real converted packages, but Tekla samples measured only 15-17 FPS in headless Chromium after orbit movement. This fails the 30 FPS target in that environment and needs GPU/manual confirmation plus format/picking optimization.

## Available Local IFC Inputs

- `ifc/Ifc2s3_Duplex_Electrical.ifc`: 1,602,758 bytes; IFC2X3; public/sample-looking Revit 2013 electrical file; header includes metre SI unit plus foot conversion unit.
- `ifc/8-SSPAR-800205B.ifc`: 4,767,500 bytes; IFC2X3; Tekla Structures 2024 SP2 structural/surface geometry export; header declares millimetre SI length unit.
- `ifc/8-SSPAR-800203.ifc`: 2,815,485 bytes; IFC2X3; Tekla Structures 2024 SP2 structural/surface geometry export; header declares millimetre SI length unit.
- `ifc/8-SSPAR-800206A.ifc`: 9,402,996 bytes; IFC2X3; Tekla-style sample added by KR; header declares millimetre SI length unit; DB-backed GLB conversion previously produced 3,770 objects/features before the spatial child-tiling pass.

These files are useful for first conversion and viewer testing, but they are smaller than the target 20 MB EPC-scale sample.
The Tekla samples have plant-offset coordinates around X 540-590 and Y 2227-2282, but they do not prove very large national-grid/global-coordinate behavior.

## Sample Conversion Metrics

Detailed record: `plant3d/records/testing/ifc-sample-conversion-results-2026-06-23.md`.

| File | Source size | Objects | JSON tile size | Conversion time |
| --- | ---: | ---: | ---: | ---: |
| `ifc/Ifc2s3_Duplex_Electrical.ifc` | 1,602,758 bytes | 104 | 1,510,791 bytes | 1,733 ms |
| `ifc/8-SSPAR-800203.ifc` | 2,815,485 bytes | 867 | 10,487,263 bytes | 17,375 ms |
| `ifc/8-SSPAR-800205B.ifc` | 4,767,500 bytes | 1,637 | 7,459,364 bytes | 10,031 ms |

## Browser Probe Metrics

Detailed record: `plant3d/records/testing/ifc-sample-conversion-results-2026-06-23.md`.

| Package | File | Browser load | FPS after orbit | Draw calls | Render batches | Pick proxies |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `ifc/Ifc2s3_Duplex_Electrical.ifc` | 88 ms | 59 | 1 | 1 | 104 |
| 2 | `ifc/8-SSPAR-800203.ifc` | 185 ms | 15 | 4 | 4 | 867 |
| 3 | `ifc/8-SSPAR-800205B.ifc` | 149 ms | 17 | 5 | 4 | 1,637 |

## Confirmed / Deferred From Claude Review

Confirmed:

- D1 remains closed for the spike: real conversion timings show request-inline conversion would be unsafe.
- Q3 is now quantified: JSON tile output can inflate several times over the source IFC and must stay a debug/spike format.
- F1 is closed for the current single-tile frame contract: Claude verified RTC reconstruction on real sample geometry.

Deferred / TODO:

- F3 remains open: obtain one plant-global/georeferenced IFC with large coordinates before marking jitter, orbit stability, or RTC precision as proven.
- D3 is closed for the platform boundary: `plant3d` now imports from `plant3d.parsers.ifc`, not `idfviewer.ifc_parser`.
- Production delivery remains deferred: package/tile payloads should move from Django JSON responses to signed object-storage URLs before real scale. The current Django delivery path now uses immutable cache headers and ETags/304 responses for package JSON, tile sidecars, and GLB blobs so repeat viewer opens avoid unnecessary artifact transfer during the spike.
- Production package format remains partially deferred: first GLB+sidecar, feature IDs, spatial child tiles, a 3D-Tiles-style manifest, first viewer-side tile streaming/culling, synthetic large-coordinate GLB child-tile regression, optional meshopt/gltfpack hook, and `MeshoptDecoder` viewer support exist. Rendering is acceptable on the current sample set; measured compression, instancing, signed/object-storage delivery, and real plant-global precision proof remain open. BVH is parked unless real picking latency regresses.
- Compression strategy clarification after external/general review: current code path is GLB + optional `gltfpack`/meshopt (`EXT_meshopt_compression`), not Draco. Draco (`KHR_draco_mesh_compression`) remains a future comparison option, but it is not the current default because runtime decode speed, feature-ID preservation, and annotation/picking correctness matter more than headline byte reduction.
- GLB feature IDs are now present in the first binary package path via `_FEATURE_ID_0` plus sidecar object-feature mapping. The viewer can now click GLB render meshes and resolve feature ID -> stable ID -> `ModelObject` metadata without hidden per-object proxies. BVH acceleration and shader/feature-ID highlighting are still deferred.
- Local spike data cleanup is now supported by `purge_plant3d_data`: Django admin deletion is acceptable for DB-only cleanup during tests, but the command should be used when source/render storage blobs also need to be removed.
- Unit/scale proof is improved but not fully closed: IFC `IfcUnitAssignment`, IfcOpenShell geometry settings, a synthetic metre-declared known-one-metre fixture, and a synthetic foot-declared known-one-metre fixture now validate the service contract. A real source-system/exporter benchmark is still needed before trusting measurement/federation workflows.
- Parser cleanup remains a TODO: the extracted parser is a direct copy for boundary safety, not yet a deeply refactored production parser.

## Immediate Next Actions

> **Plan refresh (2026-07-04):** the GLB/Three.js viewer path is accepted at current sample scale. Stage 0 service-extraction work has started and the hard EHT project FK/cascade has been removed. KR has explicitly deferred Celery/Redis for later. The immediate priority is now maintainable extraction readiness plus continued 3D-tool maturity, not more render-format churn.

1. **Boundary/API contract pass.** Document the public `plant3d` surface that EHT, raceway, and future modules may consume: source upload/list/detail, conversion queue/status, package/tileset/tile/object metadata, viewer route, project access seam, storage/blob access pattern, and overlay/layer anchors. **Drafted 2026-07-05: see `plant3d/records/planning/public-api-boundary-contract-2026-07-05.md`.**
2. **Project gateway hardening.** Add focused tests around `plant3d.project_gateway`: accessible project ids, picker enumeration/display, write-time validation, invalid project rejection, and the Stage 0 rule that EHT imports remain confined to the gateway seam. **Initial tests added 2026-07-05.**
3. **Overlay integration seam.** Refactor/document the viewer-side overlay contract so EHT draft tools, future raceway tools, measurements, reference layers, and review visibility all plug into `plant3d` through generic layer/anchor concepts. Do not add EHT/raceway persistence models to `plant3d` core. **Started 2026-07-05: viewer now has an inspectable generic layer registry for model, measurement, reference-grid, reference-plot-plan, EHT draft, and EHT route-preview layers. Continued 2026-07-05: Reference Layers now exposes user-facing layer visibility controls backed by the same registry.**
4. **Raceway placement decision.** Before coding cable tray/raceway persistence, decide and record whether `raceway` becomes a peer app consuming `plant3d` (recommended) or remains inside an EHT integration layer.
5. **Viewer maturity backlog.** Continue improving the engineering UI after the boundary work: hierarchy-wide hide/filter semantics, cleaner layer controls, robust context actions, snap/measurement refinements, plane-distance measurement, persistent review states, and professional layout polish.
6. **EHT-owned route persistence.** Move browser-local cable/component drafts toward durable persistence in an EHT/integration-owned model/API in the current shared database. Do not add EHT route tables to `plant3d`; `plant3d` supplies package/source/object anchors and render context, while EHT owns electrical route data and server-side validation.
7. **Route-authoring correctness gap closure.** Keep the JS routing layer as responsive preview/authoring only. Before durable save, add Python-authoritative validation for source/destination validity, dangling ends, route payload shape, and basic warnings. Decide/document live anchors versus snapshot anchors before route data becomes construction-grade.
8. **Boundary contract follow-up from Claude RFC.** Near-term but not this product pass: remove raw `manifest_storage_key` from public package JSON, promote `coordinate_transform` to a top-level stable response key, add a per-source JSON endpoint, and add contract tests for stable API fields/RTC round-trip. Strategic decision still needed: confirm `OverlayAnchor` is a plain shared shape/helper, not a `plant3d`-owned annotations table.
9. **Correctness gate F3.** Obtain a real plant-global/georeferenced IFC before marking float32 jitter, RTC precision, orbit stability, or measurement stability as proven. Synthetic large-coordinate tests reduce risk but do not replace this gate.
10. **Correctness gate C3/F4.** Synthetic metre-declared and foot-declared one-metre fixtures are covered; add a real source-system/exporter known-dimension proof before marking measurement/federation scale fully trusted.
11. **Performance scale checks.** Worker parser threading is a confirmed local win: 61,073 ms -> 11,826 ms total conversion on the 13.7 MB sample, with stable RAM. Repeat on the largest available IFC and size worker CPU/RAM intentionally before making aggressive defaults for constrained containers.
12. **Opportunistic package optimization only.** When `gltfpack` is available, measure meshopt compression ratio, compression duration, browser decode/load time, and feature-ID correctness. Payload is not the current bottleneck, so do not let compression displace boundary work.
13. **Deferred infrastructure.** Celery/Redis, signed object-storage delivery, Stage 1 service/database extraction, BVH, HLOD/LOD, and full meshopt/Draco comparison are deferred until the boundary/API and overlay seams are stable or a concrete scale trigger appears.
14. **Clean retests and guardrails.** Use `purge_plant3d_data` for clean local retests when DB rows and storage blobs should both be removed. Keep production EHT, cold cable, SLD, and `idfviewer` behavior unchanged.

## Next Big Coding Step — Source/Destination-First Cable Routing Foundation

**Objective:** replace the old free-click cable route workflow with a source/destination-first, centerline-drafting foundation that can later grow into Manhattan suggestions, bend-radius checks, A*/Dijkstra routing, collision-aware routing, raceway/tray graph routing, and durable EHT/raceway persistence without rewriting the viewer again.

### Why this is the next big step

- The route tool proves geometry and node editing, but it must stay predictable for users: source, destination, then ordered centerline points.
- Engineering cable routes should have explicit anchors: from DB/JB/isolator/etc. to JB/isolator/RTD/end termination/etc.
- Long routes need route intent, not hundreds of visible XYZ rows in the property panel.
- Raceway/tray work will need the same primitives: anchors, nodes, route graph, validation, suggestions, and collision costs.
- Collision physics should not be mixed directly into the EHT drawing tool. It needs a reusable engine that can serve cable, tray, duct, trench, sleeve, and future modules.

### Phase 1 — Viewer Workflow Refactor (safe product step)

Deliverable: a cleaner cable route authoring workflow inside the current `plant3d` viewer.

- Add a route mode state machine:
  - `idle`
  - `select_source`
  - `select_destination`
  - `edit_route`
  - `review_route`
- For route tools (`cold_cable`, `tracer_sr`, `tracer_mi`), ask the user to select a source component first, then a destination component.
- Lock route endpoints to component anchors once selected.
- Keep intermediate centerline/guide points editable, but do not force full collision/orthogonal rules yet.
- Replace free-click “Finish Route” assumptions with explicit route state:
  - Start and end anchors are known before route editing begins.
  - Finish/Save only commits a route with valid anchors.
  - Cancel returns cleanly to select mode.
- Show a small route HUD:
  - source label
  - destination label
  - route length
  - node count
  - warning count
- Keep node labels contextual:
  - visible while editing/selecting a route
  - hidden otherwise
- Keep route node coordinate editing available, but prepare to move long-route editing toward selected-node/on-canvas editing in a later pass.

Acceptance checks:

- User can select DB/JB/etc. as source and destination before drawing a cable.
- Route preview appears between locked anchors and follows clicked centerline points in order.
- Route cannot be committed without both anchors.
- Existing local draft save/restore still works.
- Existing point component placement, selection, delete, hide/unhide, and measurement remain unchanged.

### Phase 2 — Routing Core Skeleton (separate from viewer)

Deliverable: a small pure routing module that has no Django view or Three.js dependency.

Recommended location for now:

- `plant3d/routing/`

Initial responsibilities:

- Define route input shapes:
  - anchors
  - free nodes
  - route options
  - preferred orthogonal axes
  - bend radius metadata
  - avoid zones placeholder
  - route graph placeholder
- Return route result shapes:
  - suggested nodes
  - length
  - bend count
  - warnings
  - reasons/diagnostics
- Implement deterministic helpers:
  - direct centerline route through ordered guide points
  - optional `suggest_manhattan_route(source, destination, options)` for assist/suggestion workflows
- Keep A*/Dijkstra as placeholders, not active production behavior yet.

Acceptance checks:

- Unit tests prove the routing core can preserve a direct centerline route and can suggest a simple Manhattan route.
- Unit tests prove it returns route warnings without mutating viewer state.
- Viewer can call the routing core output shape later without knowing the final algorithm.

### Phase 3 — Centerline First, Orthogonal Assist Later (UX step)

Deliverable: predictable centerline drafting as the default, with optional assist modes clearly separated from committed user intent.

- Default route drawing is source -> ordered centerline points -> destination.
- Optional Ortho Assist may show or generate a Manhattan route, but it must not silently replace the user's centerline.
- Any future dotted/ghost Manhattan suggestion must be explicitly accepted before it changes committed geometry.
- When editing a route, new centerline points append predictably before destination unless the user has selected a guide insertion point.
- Display bend-radius warning text only after cable diameter/type is known.
- Do not force 90-degree bends until the software earns user trust through predictable previews.

Acceptance checks:

- Centerline drafting can create direct non-orthogonal route segments when the user chooses them.
- Ortho Assist is visible as an assist mode, not the hidden/default behavior.
- Non-orthogonal/free-space warnings remain visible without blocking drafting.

### Phase 4 — Electrical Rule Layer

Deliverable: first discipline-aware cable rules.

- SR tracer finish behavior:
  - Recommended default: allow the user to route from JB and auto-create an End Termination at the final end if one is not already present.
  - Record the auto-created termination as a draft element and link it to the route metadata.
- Component connection faces:
  - DB/isolator: top/bottom preferred entry.
  - JB: side/top/bottom entries, front/back discouraged.
  - RTD/end termination: endpoint-only role.
- Add warning placeholders:
  - unrealistic open cable end
  - same source and destination
  - too many cables on one device
  - bend radius below minimum

Acceptance checks:

- SR route can complete with an end termination rule.
- Warnings are visible but do not over-block the user at this stage.

### Phase 5 — Collision/Routing Engine Gate

Deliverable: a design/implementation bridge before raceway/tray/duct work.

- Introduce collision as a reusable service, not a viewer-side patch.
- Start with bounding-box warning mode only:
  - detect rough overlap/penetration
  - show warning in selected route/component panel
  - do not hard-stop movement yet
- Later evolve to:
  - BVH-backed clash checks
  - swept-volume route checks
  - clearance envelopes
  - collision costs for A*/Dijkstra

Acceptance checks:

- Collision warnings are clearly marked as approximate.
- No false claim that hard collision physics is production-ready.

### Phase 6 — Persistence Boundary

Deliverable: decide and implement durable route storage in the correct owner module.

- Do not persist EHT cable routes in `plant3d` core tables.
- Use an EHT/integration-owned model in the current shared database for now.
- Store:
  - plant3d package/source/project anchors
  - route source/destination anchor references
  - route node coordinates
  - cable/tracer type
  - warnings/validation snapshot
  - created/updated metadata
- Keep future service extraction clean: EHT owns EHT cable data; `plant3d` owns model/package/render context.

### What Claude Can Help With

Ask Claude for targeted review/research in parallel with Codex implementation:

1. **Routing state-machine review:** validate the proposed `idle/select_source/select_destination/edit_route/review_route` flow and identify edge cases before coding.
2. **Cable/raceway algorithm research:** recommend clean abstractions for Manhattan routing now and A*/Dijkstra later, including where each algorithm is appropriate.
3. **Electrical rule checklist:** define practical first-pass validation rules for SR/MI/cold cable routing, JB/DB/isolator entries, end termination placement, and bend-radius warnings.
4. **Collision engine staging:** recommend a staged collision architecture for bounding boxes -> BVH -> swept volumes, including what should remain approximate in the MVP.
5. **Persistence model review:** review the future EHT/integration-owned route persistence model so we do not accidentally re-couple `plant3d` to EHT domain data.

### Non-Goals For This Milestone

- No full tray/raceway persistence yet.
- No hard collision physics yet.
- No automatic clash resolution.
- No full A*/Dijkstra production router yet.
- No forced 90-degree bend behavior.
- No Celery/Redis or service split work.

2026-07-01 coding note: Phase 7 tracker checkboxes are now closed against decision record 0003, but the acceptance remains deliberately scoped to current sample scale. Added a stronger synthetic F3 guard proving child-tile GLB payloads keep plant-global coordinates in tile RTC metadata while GLB vertex positions stay tile-local and reconstruct back into source-coordinate tile bounds. This does not replace the real plant-global IFC gate.

2026-07-01 timing note: KR's fresh 13.7 MB `8-SSPAU-800203.ifc` GLB run recorded 61,073 ms total, with `parse_ms=59,656 ms`, GLB build 479 ms, tile write 29 ms, tileset write 1 ms, and DB/index write 329 ms. The next pass added an explicit `process_plant3d_job --parser-threads` option so the A/B test is repeatable without hidden environment variables.

2026-07-01 A/B result: the same sample converted with `process_plant3d_job --watch --parser-threads auto` completed in 11,826 ms, with `parse_ms=10,411 ms`. CPU rose to about 97%, GPU stayed unchanged as expected, and RAM stayed around 30%. The source-detail and JSON worker hints now recommend the threaded worker command for local/dev conversion.

2026-07-01 worker sizing note: `auto` now uses Docker/cgroup-aware effective CPU count and cgroup memory limits where Linux exposes quota files. It supports a hard thread cap (`--parser-thread-cap N` or `PLANT3D_PARSER_THREAD_CAP=N`) and memory assumptions (`PLANT3D_PARSER_MEMORY_PER_THREAD_MB`, `PLANT3D_PARSER_MEMORY_RESERVE_MB`). The worker also calls Python garbage collection after each job. Native IfcOpenShell allocations can still benefit from operational recycling, so production/shared Docker workers should use explicit CPU/RAM limits and consider `--max-jobs` plus container restart policy for long-running conversion loads.

2026-07-06 touchup note: source upload is now user-flow oriented rather than developer-form oriented. The upload form places project/name/source-system fields before file selection, and choosing a file auto-submits the form. Source detail now presents a simpler normal-user path (`Open 3D Viewer` or `Process 3D Model`) while retaining conversion jobs, reprocess buttons, package internals, and cleanup actions inside explicit advanced/detail sections. Delete wording was clarified: working source deletion affects only the current source and generated plant3d artifacts, not saved cases or other users' data.

2026-07-06 route-edit note: the selected-route HUD was moved out of the left sidebar into a compact floating glass card over the viewer. Route edit clicks now insert guide points into the nearest existing route segment instead of always appending before the destination, reducing the unrealistic long zigzag behavior when a user wants an existing cable to pass through one additional point. This is still a guide-point editing heuristic, not a full pathfinding or collision-aware reroute engine.

2026-07-06 persistence note: browser `localStorage` remains an interim draft convenience only. Durable DB persistence for EHT routes/components should be the next product-grade boundary pass: create EHT/integration-owned storage in the current shared database, load it into the viewer on package open, and validate route payloads server-side before save. Do not persist EHT route data in `plant3d` core tables.

2026-07-07 route-edit note, superseded by centerline correction below: guide-handle dragging was tested as orthogonal by default on the current elevation plane, with a visible `Ortho Move` / `Free Move` toggle and a temporary `Shift` override for free planar drag. Manual testing later showed this still felt too clever/unpredictable for first-pass authoring.

2026-07-07 route-mode correction, superseded by centerline correction below: `Free Move` was changed to affect route geometry, not just handle dragging. This proved direct polyline routes were needed, but the final current direction is simpler: centerline-first route drafting with optional `Ortho Assist`.

2026-07-07 centerline correction: after KR manual testing, the routing UI was simplified again. New cable routes now default to `Centerline` drafting: select source, select destination, click centerline/path points in order, then `Finish Route`. `Ortho Assist` remains available as an optional Manhattan helper, but it is no longer the default authoring mode. Centerline clicks append predictably before the destination, or after the selected guide if one is selected.

Current manual check path:

1. Upload one available local sample IFC from `ifc/` through `/plant3d/sources/upload/`.
2. Start the local worker once in a separate terminal: `venv/bin/python manage.py process_plant3d_job --watch --parser-threads auto`.
   For a crowded/shared Docker host, use a cap or fixed count, for example `--parser-threads auto --parser-thread-cap 2` or `--parser-threads 2`.
3. Run metadata conversion through the source detail page or POST endpoint.
4. Run IFC JSON debug conversion if needed; the worker should pick it up automatically.
5. Click `Process 3D Model` to queue the IFC GLB conversion; the worker should pick it up automatically.
6. Open both package viewers and compare package size/load behavior.
7. Measure the resulting package with `venv/bin/python manage.py measure_plant3d_package <package_id>`.
8. Record the timing line from `measure_plant3d_package`, especially `parse_ms`, `glb_build_ms`, `tile_write_ms`, and `db_write_ms`.
9. For delivery-cache validation, open browser DevTools Network before reloading the same package viewer. Repeat package/tile artifact requests should show `304 Not Modified` or browser memory/disk-cache hits, while the viewer remains visually unchanged.
10. For a clean local reset, first dry-run `venv/bin/python manage.py purge_plant3d_data --project-id <proj_id>` or `--source-id <id>`, then add `--confirm` only after reviewing the summary.

## Verification Log

- 2026-06-22: `venv/bin/python manage.py check` passed with no issues.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 5 tests.
- 2026-06-22: `venv/bin/python manage.py check` passed after source intake/conversion scaffold.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 8 tests.
- 2026-06-22: `venv/bin/python manage.py check` passed after IFC geometry conversion scaffold.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 10 tests.
- 2026-06-22: Workspace scan found no IFC files available outside ignored/generated areas, so real-file metrics remain pending.
- 2026-06-22: `venv/bin/python manage.py check` passed after package API/viewer scaffold.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 12 tests.
- 2026-06-22: Claude audit reviewed. Took D2, S1, S2, Q1, Q4, Q5, Q6, P1; deferred D1/D3/Q2 for deliberate architecture phases; tracked Q3 as spike limitation.
- 2026-06-22: `venv/bin/python manage.py check` passed after audit hardening pass.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 16 tests.
- 2026-06-22: Claude re-review accepted deferrals but required D1 before real IFC metrics. Implemented queued conversion endpoints plus `process_plant3d_job`.
- 2026-06-22: `venv/bin/python manage.py check` passed after management-command worker pass.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 18 tests.
- 2026-06-22: Applied local database migration `plant3d.0001_initial` to fix `/plant3d/sources/upload/` missing-table error.
- 2026-06-22: `venv/bin/python manage.py check` passed after viewer inspection/object metadata pass.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 19 tests.
- 2026-06-22: Closed Claude Q2 for the JSON spike by computing/storing RTC origin from raw bounds and adding large-coordinate tests.
- 2026-06-22: `venv/bin/python manage.py check` passed after RTC metadata pass.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 19 tests.
- 2026-06-22: Took Claude F1. Corrected RTC frame contract by separating `origin_source_xyz` from render-frame `rtc_origin_render_xyz` and adding source-coordinate reconstruction assertions.
- 2026-06-22: `venv/bin/python manage.py check` passed after RTC frame-correction pass.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 19 tests.
- 2026-06-22: Added conversion duration metrics plus viewer FPS/draw-call/WebGL resource counters for the first manual IFC measurement.
- 2026-06-22: `venv/bin/python manage.py check` passed after measurement instrumentation pass.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 19 tests.
- 2026-06-22: Added merged color-bucket rendering in the Three.js debug viewer, with hidden per-object pick proxies for metadata selection.
- 2026-06-22: `venv/bin/python manage.py check` passed after merged-viewer pass.
- 2026-06-22: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 19 tests.
- 2026-06-22: `node --check /tmp/package_viewer.mjs` passed after copying the browser module to `.mjs` for syntax checking.
- 2026-06-23: Added source-detail async queue submission/polling, job/package URLs in JSON responses, and `process_plant3d_job --all`.
- 2026-06-23: `venv/bin/python manage.py check` passed after source-detail polling pass.
- 2026-06-23: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 21 tests.
- 2026-06-23: `node --check plant3d/static/plant3d/js/source_detail.js` passed.
- 2026-06-23: `node --check /tmp/package_viewer.mjs` passed after copying the browser module to `.mjs` for syntax checking.
- 2026-06-23: Found three local IFC samples under `ifc/` and recorded their size/source-system/unit-header notes.
- 2026-06-23: Converted all three local IFC samples through the real IfcOpenShell/parser path and recorded conversion metrics in `plant3d/records/testing/ifc-sample-conversion-results-2026-06-23.md`.
- 2026-06-23: Verified all three real converted packages with a temporary static Playwright/browser probe. Canvases were nonblank; Tekla package probes measured 15-17 FPS after orbit movement in headless Chromium.
- 2026-06-23: `venv/bin/python manage.py check` passed after browser-probe documentation pass.
- 2026-06-23: `venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 21 tests.
- 2026-06-23: `venv/bin/python -m py_compile plant3d/records/testing/browser_viewer_probe.py` passed.
- 2026-06-23: `node --check plant3d/static/plant3d/js/source_detail.js` passed.
- 2026-06-23: `node --check /tmp/package_viewer.mjs` passed after copying the browser module to `.mjs`.
- 2026-06-23: Added IFC header length-unit hint extraction and warnings to metadata/package/tile/job records for new conversions; sample headers report Revit `m + FOOT` and Tekla `mm + FOOT`.
- 2026-06-23: Closed D3 platform-boundary dependency by copying the IFC parser/unit helper into `plant3d/parsers/` and changing `plant3d.services` to import from `plant3d.parsers.ifc`.
- 2026-06-23: `venv/bin/python -m py_compile plant3d/parsers/ifc.py plant3d/parsers/units.py plant3d/services.py` passed.
- 2026-06-23: Direct extracted-parser check on `ifc/Ifc2s3_Duplex_Electrical.ifc` returned 104 meshes.
- 2026-06-23: `venv/bin/python manage.py check` passed after parser extraction.
- 2026-06-23: `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 22 tests. The default reused PostgreSQL test database failed during setup on an unrelated auth/content-type integrity issue before plant3d tests ran.
- 2026-06-23: Added parser-level IFC `IfcUnitAssignment` extraction. Real samples now report Revit `ft` and Tekla `mm` as source-declared units while render geometry remains `M` with `ifcopenshell_geometry_si` confidence.
- 2026-06-23: `venv/bin/python -m py_compile plant3d/parsers/ifc.py plant3d/services.py plant3d/tests.py` passed after parser unit extraction.
- 2026-06-23: `venv/bin/python manage.py check` passed after parser unit extraction.
- 2026-06-23: `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 24 tests.
- 2026-06-23: Real parser unit check: `Ifc2s3_Duplex_Electrical.ifc` declares `ft` scale `0.3048`; `8-SSPAR-800203.ifc` and `8-SSPAR-800205B.ifc` declare `mm` scale `0.001`; all report render coordinate unit `M`, IfcOpenShell `length-unit=1.0`, `convert-back-units=False`.
- 2026-06-23: Added first GLB package path: `plant3d.ifc-glb` queued conversion, binary GLB tile, JSON metadata sidecar, blob endpoint, and GLB viewer loading through `GLTFLoader`.
- 2026-06-23: `venv/bin/python -m py_compile plant3d/glb.py plant3d/services.py plant3d/views.py plant3d/tests.py` passed after GLB pass.
- 2026-06-23: `venv/bin/python manage.py check` passed after GLB pass.
- 2026-06-23: `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 28 tests.
- 2026-06-23: `node --check /tmp/package_viewer.mjs` passed after refreshing the viewer module copy.
- 2026-06-23: Real GLB conversion metrics: `Ifc2s3_Duplex_Electrical.ifc` produced 560,296 byte GLB plus 26,266 byte sidecar for 104 objects; `8-SSPAR-800203.ifc` produced 5,376,268 byte GLB plus 167,948 byte sidecar for 867 objects in 17,546 ms.
- 2026-06-23: Claude render-format research reviewed. Accepted stack direction: GLB first, meshopt over Draco for default compression, feature IDs before serious picking, no custom binary, no xeokit/AGPL, 3D-Tiles-style manifest for streaming/LOD. Recorded that format, RTC, and precision must be proven together on plant-global coordinates.
- 2026-06-23: Admin cleanup note: deleting local spike `ModelObject` / `ConversionJob` rows from Django admin is DB-safe, but it does not remove stored source/render files. Deleting only jobs leaves packages; deleting only objects leaves package counts stale. For a clean local reset, delete `SourceModel` records or add a dedicated cleanup command that also removes storage keys.
- 2026-06-23: Added GLB `_FEATURE_ID_0` vertex attribute plus sidecar `object_features` / `object_spans` mapping. `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed: 28 tests; `node --check /tmp/package_viewer.mjs` passed.
- 2026-06-23: Tested user-supplied `ifc/8-SSPAR-800206A.ifc` through DB-backed GLB conversion: 9,402,996 byte IFC, 3,770 objects/features, 5,960,624 byte GLB, 1,269,630 byte sidecar, 7,230,254 total bytes, 20,717 ms conversion, source unit `mm`.
- 2026-06-23: Fixed source-detail job polling so queued/running jobs continue polling until terminal state; added explicit worker command hint and removed stale "No conversion jobs yet" row when jobs are inserted. `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput`, and `node --check /tmp/source_detail.js` passed.
- 2026-06-23: Documented GLB axis convention in package metadata/sidecar: buffers use `render_xyz_m`, source axis order maps `x,z,y`, glTF up axis is `Y`, and no root transform is required.
- 2026-06-23: Added first GLB feature-ID click-to-metadata viewer path. The viewer indexes package objects, reads sidecar `object_features`, raycasts against visible GLB meshes, resolves `_FEATURE_ID_0` to stable object metadata, and keeps GLB pick-proxy count at zero. `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput`, and `node --check /tmp/package_viewer.mjs` passed.
- 2026-06-23: Added adaptive viewer quality for interaction performance: high-performance WebGL context, no MSAA for the spike viewer, capped idle pixel ratio, lower pixel ratio during orbit/pan/zoom, automatic FPS-based up/down shift, and sidebar reporting of pixel ratio/quality mode. `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput`, and `node --check /tmp/package_viewer.mjs` passed.
- 2026-06-23: Added first single-root 3D-Tiles-style `tileset.json` manifest for new GLB conversions. New GLB packages store the tileset as `manifest_storage_key`, keep per-tile feature metadata in the sidecar endpoint, and expose a runtime `tileset` payload through package JSON with API blob/metadata URLs. Older GLB packages without a tileset remain compatible through the existing tile list. `venv/bin/python -m py_compile plant3d/services.py plant3d/views.py plant3d/tests.py`, `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput`, and `node --check /tmp/package_viewer.mjs` passed.
- 2026-06-23: Closed Claude G1/G2 before spatial tiling: GLB `_FEATURE_ID_0` now uses glTF-valid `FLOAT` accessors instead of `UNSIGNED_INT`, and GLB sidecar stable IDs use the same resolver as indexed `ModelObject` rows so GUID-less meshes pick correctly. Added a GUID-less mesh regression test. `venv/bin/python -m py_compile plant3d/glb.py plant3d/services.py plant3d/tests.py`, `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput`, and `node --check /tmp/package_viewer.mjs` passed.
- 2026-06-23: Added first spatial GLB child-tiling pass. Large GLB conversions are grouped by source-bounds grid at roughly 500 objects per tile, each child tile gets its own GLB, sidecar, feature-ID range, RTC origin, `RenderTile` row, and `tileset.json` child entry. The viewer applies `tile.rtc_origin - package.rtc_origin` so tile-local GLBs preserve model placement while still loading all tiles for now. Added a 501-object regression test. `venv/bin/python -m py_compile plant3d/glb.py plant3d/services.py plant3d/views.py plant3d/tests.py`, `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput`, and `node --check /tmp/package_viewer.mjs` passed.
- 2026-06-28: Recorded fresh spatial GLB child-tile conversion measurements for `Ifc2s3_Duplex_Electrical.ifc`, `8-SSPAR-800203.ifc`, `8-SSPAR-800205B.ifc`, and `8-SSPAR-800206A.ifc` in `plant3d/records/testing/ifc-sample-conversion-results-2026-06-23.md`. The 9.4 MB Tekla sample produced 9 child tiles, 3,770 objects, 5,107,980 GLB bytes, 1,315,122 sidecar bytes, 9,536 tileset bytes, 6,432,638 package bytes, and a 21,474 ms conversion.
- 2026-06-28: Added first viewer-side GLB tile streaming/culling. The viewer now prepares tile state from package JSON, frames from package bounds before loading child GLBs, loads only active visible tiles up to a cap of 6 for larger packages, unloads inactive child tiles, and reports loaded/loading tile counts in runtime metrics. Browser/manual validation is still required on a logged-in local viewer session.
- 2026-06-28: Added a synthetic known-one-metre IFC conversion fixture test. It proves the current service contract preserves a 1 m render extent across source bounds, RTC origin, local render coordinates, and reconstructed source coordinates. A real source-system/exporter scale benchmark remains open.
- 2026-06-28: `venv/bin/python -m py_compile plant3d/glb.py plant3d/services.py plant3d/views.py plant3d/tests.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after the viewer streaming and unit-fixture pass.
- 2026-06-28: Static browser probe passed for real package 24 payloads using current `package_viewer.js`: 9 total child tiles, 6 loaded after probe, 2,468 feature IDs loaded, 123,620 triangles loaded, 60 FPS after orbit, 19 draw calls, 0 pick proxies, and nonblank canvas ratio 6.86%. Manual confirmation in the logged-in Django viewer remains useful before treating this as user-accepted performance.
- 2026-06-28: Added `process_plant3d_job --watch` so local/dev and future worker containers can continuously process queued jobs instead of requiring repeated manual `--all` runs. `--next`, `--all`, and `--watch` now claim queued jobs before execution.
- 2026-06-28: Added staged conversion progress (`stage` in job metrics plus log lines) for metadata, IFC JSON, and IFC GLB jobs. IfcOpenShell tessellation still has no internal progress callback, but the page now shows the long parsing stage instead of staying at an unexplained 5%.
- 2026-06-28: Strengthened the synthetic large-coordinate GLB child-tiling regression: generated GLB child tiles now assert large render-frame RTC origins while GLB buffer positions remain local/small, keeping C1 covered until a real plant-global IFC arrives.
- 2026-06-28: `venv/bin/python -m py_compile plant3d/glb.py plant3d/services.py plant3d/views.py plant3d/tests.py plant3d/management/commands/process_plant3d_job.py`, `node --check /tmp/source_detail.js`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after worker/progress/large-coordinate fixture pass. Plant3d suite: 33 tests.
- 2026-06-28: Added optional meshopt/gltfpack compression hook for GLB tile bytes. If `PLANT3D_GLTFPACK_BIN` or `gltfpack` on PATH is available, conversion runs `gltfpack -cc` and records input/output byte metrics; otherwise conversion succeeds with compression status `skipped`.
- 2026-06-28: Registered Three.js `MeshoptDecoder` in the GLB viewer so future `EXT_meshopt_compression` packages can load through the existing viewer path.
- 2026-06-28: Vectorized GLB writer hot paths with numpy: normal calculation, float packing, index packing, and position bounds are now array-based instead of pure-Python loops.
- 2026-06-28: `venv/bin/python -m py_compile plant3d/glb.py plant3d/compression.py plant3d/services.py plant3d/views.py plant3d/tests.py plant3d/management/commands/process_plant3d_job.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after meshopt-hook/numpy pass. Plant3d suite: 34 tests.
- 2026-06-28: Added `plant3d/records/operations/worker-container-runbook-2026-06-28.md` documenting the `plant3d-worker` container role, current `--watch` command, job-claiming behavior, meshopt/gltfpack environment knobs, and production gaps before Celery/RQ/SSE.
- 2026-06-28: `venv/bin/python manage.py check` and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after tracker/audit/runbook updates. Plant3d suite: 34 tests.
- 2026-06-28: KR manual browser check confirmed no visible graphics degradation, no noticed side effects, and `process_plant3d_job --watch` works as the local long-running worker. One checked package reported 2,221 objects, 6/6 loaded tiles, 3,322,076 bytes, 151 ms viewer load time, 60 FPS, 24 draw calls, 0 pick proxies, and 13 ms metadata latency. Because the package has 6 total tiles, streaming mode was `load-all`, not partial active-cap streaming.
- 2026-06-28: Added `measure_plant3d_package` management command to summarize render-package bytes and meshopt/gltfpack status from package/tile records. It reports recorded bytes, measured geometry/sidecar/manifest bytes, per-tile compression status, input/output bytes, saved bytes, and ratio, with human and JSON output. Real ratio measurement still waits for an installed `gltfpack` binary.
- 2026-06-28: `venv/bin/python manage.py check` and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after package-measurement command pass. Plant3d suite: 35 tests.
- 2026-06-28: Housekeeping review removed generated `__pycache__` folders and one unused storage helper. JSON debug conversion/viewer remains intentionally retained for comparison and diagnostics, not treated as production runtime format. Older planning/explainer records are kept as historical snapshots where later code has superseded them.
- 2026-06-28: Updated `measure_plant3d_package` after Claude MM1-MM3: human/JSON output now includes aggregate summary, compression duration, saved percent, clearer `ratio_output_over_input` wording, and measured-vs-recorded byte drift warnings.
- 2026-06-28: `venv/bin/python -m py_compile plant3d/storage.py plant3d/views.py plant3d/management/commands/measure_plant3d_package.py plant3d/tests.py`, `venv/bin/python manage.py check`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after housekeeping pass. Plant3d suite: 35 tests.
- 2026-06-28: Added meshopt feature-ID correctness gate. Compressed GLB bytes are accepted only if `_FEATURE_ID_0` remains inspectable, integral, mapped to the sidecar feature IDs, and preserves per-feature vertex counts. If validation fails or cannot inspect the feature stream, conversion falls back to the original uncompressed GLB and records `rejected_feature_id_validation`. Focused meshopt tests passed.
- 2026-06-28: `venv/bin/python -m py_compile plant3d/glb.py plant3d/services.py plant3d/management/commands/measure_plant3d_package.py plant3d/tests.py`, `venv/bin/python manage.py check`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after meshopt feature-ID safety pass. Plant3d suite: 36 tests.
- 2026-06-28: KR manual screenshot comparison found the first serious viewer regression: the active tile cap can make plant3d show incomplete geometry versus the old idfviewer. Root cause is current viewer streaming behavior (`MAX_LOADED_GLB_TILES = 6`, active visible slice, immediate unload), not proven compression data loss. This must be addressed before treating streaming as production-acceptable.
- 2026-06-28: Added decision record `plant3d/records/decisions/0002-viewer-completeness-and-lod.md`: degrade fidelity before completeness. Implemented complete/review mode in the GLB viewer for packages up to 24 tiles and 64 MB, persistent completeness reporting, and retained-cache partial streaming for larger packages (`active cap=6`, retained cache=18, unload grace=4 s). Bumped viewer script version to avoid browser cache using old cap behavior.
- 2026-06-28: `venv/bin/python -m py_compile plant3d/tests.py plant3d/views.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after viewer completeness pass. Plant3d suite: 36 tests.
- 2026-06-28: KR manual retest after complete/review mode found a second viewer regression: first load was slow, zoom could drive the camera into an unusable/stale state, and attempting to recover could leave a white canvas until reset. Added OrbitControls zoom/pan guardrails, min/max camera distance from model bounds, safer camera near/far planes, and a one-time reframe after all review-mode GLB tiles load. Bumped viewer script version again.
- 2026-06-28: `venv/bin/python -m py_compile plant3d/tests.py plant3d/views.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after zoom/camera guardrail pass. Plant3d suite: 36 tests.
- 2026-06-28: KR manual retest confirmed the zoom/stale/white-canvas regression is fixed on a 9-tile GLB package. Source 23/package 51 reported 4,313 objects, 715,028 triangles, 9/9 loaded tiles, 36 draw calls, 16,050,726 package bytes, 361 ms viewer load time, 60 FPS, 5 ms pick latency, 27 ms metadata latency, and `review-complete` streaming. Meshopt/gltfpack was skipped because `gltfpack` is not installed.
- 2026-06-28: Added viewer-side graphics diagnostics so manual tests can distinguish server conversion cost from browser GPU rendering: frame time, renderer triangle count, browser JS heap where available, WebGL renderer, WebGL vendor, and WebGL version are now shown in the runtime metrics panel. Important clarification: `Queue IFC GLB Conversion` is CPU/IO-side Django/IfcOpenShell/GLB packaging work and is not expected to load the NVIDIA GPU; GPU usage begins when Chrome/Edge renders the package viewer through WebGL.
- 2026-06-28: `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, and `venv/bin/python manage.py test plant3d -v 2 --noinput` passed after viewer GPU/WebGL diagnostics pass. Plant3d suite: 36 tests.
- 2026-06-28: KR clean-DB fresh run after deleting plant3d admin data: `8-SSPAU-800203.ifc` 13.4 MB source, off-request worker/watch conversion about 1 minute 6 seconds, Windows Task Manager observed CPU about 40%, GPU 1 about 4%, GPU 2 0%. Package 55 reported 4,313 objects, 9 tiles, 16,050,726 package bytes, 287 ms viewer load time, 715,028 render triangles, 36 draw calls, 9/9 loaded tiles, 0 failed tiles before VC1, 60 FPS, 18.2 ms frame time, pixel ratio 0.9, 22 MB browser heap, 5 ms pick latency, and 55 ms metadata latency. WebGL renderer confirmed hardware acceleration through `ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti ... Direct3D11)`.
- 2026-06-28: Closed Claude VC1 in the viewer: GLB tile state now has failed/attempt/error tracking, retries stop after 3 failed attempts, failed tiles are excluded from future candidates, runtime metrics show failed tile count, and completeness/status text reports `Model INCOMPLETE` instead of misleading perpetual loading when a tile permanently fails.
- 2026-06-28: `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, and `venv/bin/python manage.py test plant3d -v 2 --noinput` passed after failed-tile completeness pass. Plant3d suite: 36 tests.
- 2026-06-28: Added `purge_plant3d_data` management command for safe local spike cleanup. It requires exactly one scope (`--source-id`, `--project-id`, or `--all`), dry-runs by default, needs `--confirm` to delete, and removes explicit source/package/tile storage blobs unless `--keep-storage` is used.
- 2026-06-28: `venv/bin/python -m py_compile plant3d/storage.py plant3d/management/commands/purge_plant3d_data.py plant3d/tests.py`, `venv/bin/python manage.py check`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after purge-command pass. Plant3d suite: 38 tests. A first focused run against the default PostgreSQL test DB hit a local connection error before tests executed, so the verified suite used the existing SQLite fallback.
- 2026-06-29: Accepted Claude SEQ1/PERF1 sequencing correction. Package-55 metrics prove rendering/picking is healthy at current scale, so next work is correctness gates (F3 plant-global precision and C3/F4 known-dimension units) plus conversion timing instrumentation. Meshopt is opportunistic once `gltfpack` exists; BVH remains parked unless pick latency regresses.
- 2026-06-29: Added per-stage conversion timings to IFC JSON/GLB jobs and GLB package metadata. New GLB metrics include `source_read_ms`, `parse_ms`, `context_metadata_ms`, `tile_grouping_ms`, `tile_prepare_ms`, `glb_build_ms`, `meshopt_hook_ms`, `feature_id_validation_ms`, `tile_write_ms`, `tileset_write_ms`, and `db_write_ms` where applicable. `measure_plant3d_package` now prints/exports conversion timings.
- 2026-06-29: `venv/bin/python -m py_compile plant3d/services.py plant3d/management/commands/measure_plant3d_package.py plant3d/tests.py`, `venv/bin/python manage.py check`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after conversion-timing instrumentation pass. Plant3d suite: 38 tests.
- 2026-06-29: Added synthetic foot-declared known-one-metre fixture coverage for C3/F4. The test declares IFC source length as `ft` / `0.3048` while asserting the render geometry remains a 1.0 m extent under the IfcOpenShell-SI geometry contract. This covers the deterministic foot-scale regression case; a real source-system/exporter known-dimension proof remains open.
- 2026-06-29: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d -v 2 --noinput` passed after foot-declared known-dimension fixture pass. Plant3d suite: 39 tests.
- 2026-06-29: Source detail and job JSON now surface conversion timing summaries directly. Completed jobs show total conversion duration plus ordered timing rows such as IFC parse, GLB build, tile write, tileset write, and DB/index write; raw metrics are tucked behind a disclosure. The polling UI also renders the timing summary as soon as a watched job completes.
- 2026-06-29: Started visual-fidelity correction after KR compared `plant3d` with `idfviewer`. The GLB viewer now enables WebGL antialiasing, keeps review-size packages in full-fidelity pixel mode during interaction unless FPS actually regresses, reduces shiny/specular material response on generated GLBs, reports antialiasing in runtime metrics, and builds a temporary selected-feature highlight mesh from `_FEATURE_ID_0` so clicked GLB objects are visibly outlined instead of only showing metadata.
- 2026-06-29: `node --check /tmp/package_viewer.mjs`, `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d.tests.Plant3DIntakeTests.test_package_viewer_page_exposes_package_api_url --noinput -v 2`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the visual-fidelity/selection-highlight pass. Plant3d suite: 40 tests.
- 2026-06-29: KR manual retest confirmed beam-edge shimmer is fixed and the viewer now feels real. The amber selected-feature wire overlay is acceptable and preferable to apparent missing/disappearing members. Added first review-selection controls: `Fit Selected`, `Clear`, and Escape-to-clear. Selection controls are enabled only when geometry is selected, and partial-streaming tile unload clears stale selections.
- 2026-06-29: `node --check /tmp/package_viewer.mjs`, `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d.tests.Plant3DIntakeTests.test_package_viewer_page_exposes_package_api_url --noinput -v 2`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the selection-controls pass. Plant3d suite: 40 tests.
- 2026-06-29: Added normalized object `selection_summary` to the object JSON API and changed the viewer selection panel to show engineering-readable details first: label, type, tag/name, line ID, dimensions, spatial path, group, stable ID, and source object. Raw bounds/metadata remain available behind a disclosure for debugging.
- 2026-06-29: `node --check /tmp/package_viewer.mjs`, `venv/bin/python -m py_compile plant3d/views.py plant3d/tests.py`, `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d.tests.Plant3DIntakeTests.test_package_and_tile_json_endpoints_return_render_payload plant3d.tests.Plant3DIntakeTests.test_package_viewer_page_exposes_package_api_url --noinput -v 2`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the selection-summary pass. Plant3d suite: 40 tests.
- 2026-06-30: Closed Claude SEL1. The GLB viewer now indexes sidecar `object_spans` as `featureId -> span` and builds selected-feature highlight geometry from the feature's recorded index range instead of scanning the whole tile buffer on every click. The old full-feature scan remains only as a correctness fallback if a future compression/reorder invalidates the span. Selection dimensions are now labelled as source extents, with `dimension_frame = source_xyz` in the object API. Sequencing reminder: next non-fix work should be the 66 s conversion timing readout and Phase 7 rendering decision, not more viewer polish.
- 2026-06-30: `node --check /tmp/package_viewer.mjs`, `venv/bin/python -m py_compile plant3d/views.py plant3d/tests.py`, `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d.tests.Plant3DIntakeTests.test_package_and_tile_json_endpoints_return_render_payload plant3d.tests.Plant3DIntakeTests.test_package_viewer_page_exposes_package_api_url --noinput -v 2`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the span-based highlight pass. Plant3d suite: 40 tests.
- 2026-06-30: Improved `measure_plant3d_package` for the pending 66 s conversion readout. The command now computes `conversion_timing_breakdown` in JSON and prints a `timing decision` line with total timed milliseconds, dominant stage, dominant milliseconds, and dominant percentage. This should make the next real conversion measurement actionable without manual arithmetic.
- 2026-06-30: `venv/bin/python -m py_compile plant3d/management/commands/measure_plant3d_package.py plant3d/tests.py`, `venv/bin/python manage.py check`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d.tests.Plant3DIntakeTests.test_measure_package_command_reports_meshopt_status --noinput -v 2`, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the measurement-command timing-breakdown pass. Plant3d suite: 40 tests.
- 2026-06-30: Accepted Claude PERF2 direction conditionally. Configurable IfcOpenShell geometry iterator thread count is likely the next high-value conversion-speed lever if `parse_ms` dominates, but it should not be activated blind. Attempted `venv/bin/python manage.py measure_plant3d_package --latest 3` from this shell; it was blocked by a local PostgreSQL connection error (`django.db.utils.OperationalError: connection is bad`). Manual/live environment measurement remains required before enabling multi-threaded parser conversion.
- 2026-06-30: Added decision record `plant3d/records/decisions/0003-phase-7-rendering-spike-decision.md`. Decision: continue Three.js-first and GLB+sidecar+3D-Tiles-style manifests at current sample scale; keep JSON as debug only; keep BVH, compression adoption, signed object storage, and HLOD as gated future work. Open gates remain F3 plant-global precision, real known-dimension source-system proof, conversion timing/PERF2, and production LOD/HLOD.
- 2026-06-30: Added gated PERF2 plumbing without changing default behavior. `plant3d.parsers.ifc` now reads `PLANT3D_PARSER_THREADS` from environment or Django settings, defaults to 1, accepts fixed positive integers, and supports `auto = max(1, os.cpu_count() - 1)`. Parser stats now record `ifcopenshell_iterator_threads` and `ifcopenshell_iterator_thread_source`; the worker runbook documents how to run a controlled parser-thread test after `parse_ms` is proven dominant.
- 2026-06-30: `venv/bin/python -m py_compile plant3d/parsers/ifc.py plant3d/tests.py`, `venv/bin/python manage.py check`, focused parser-thread tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after gated parser-thread plumbing. Plant3d suite: 44 tests.
- 2026-07-01: Closed the mechanical Phase 7 tracker items against decision record 0003 and strengthened the synthetic F3 precision guard. The new regression uses internally consistent large source coordinates around X 5,000,000 / Y 2,800,000, asserts child tile RTC origins carry the large values, asserts GLB POSITION accessors remain tile-local, and reconstructs sampled GLB vertices back inside the tile source bounds.
- 2026-07-01: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, focused synthetic F3 child-tile test, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the precision-guard pass. Plant3d suite: 45 tests.
- 2026-07-01: Recorded KR's live conversion timing: 13.7 MB `8-SSPAU-800203.ifc`, 61,073 ms total, `parse_ms=59,656 ms`, default parser threads `1`. Added `process_plant3d_job --parser-threads <auto|N>` for controlled parser-thread A/B testing without hidden environment variables. Default remains 1 until the A/B result is reviewed.
- 2026-07-01: `venv/bin/python -m py_compile plant3d/parsers/ifc.py plant3d/management/commands/process_plant3d_job.py plant3d/tests.py`, `venv/bin/python manage.py check`, focused parser-thread command tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after worker parser-thread option pass. Plant3d suite: 47 tests.
- 2026-07-01: KR A/B-tested `--parser-threads auto` on the same 13.7 MB sample. Conversion improved from 61,073 ms to 11,826 ms; `parse_ms` improved from 59,656 ms to 10,411 ms; CPU rose to about 97%; GPU remained unchanged; RAM stayed around 30%. Updated local/dev worker hints to recommend `process_plant3d_job --watch --parser-threads auto` while keeping the parser's low-level default conservative.
- 2026-07-01: `venv/bin/python -m py_compile plant3d/views.py plant3d/tests.py plant3d/management/commands/process_plant3d_job.py plant3d/parsers/ifc.py`, `venv/bin/python manage.py check`, focused worker-hint/parser-thread command tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after accepting parser-threaded local/dev worker mode. Plant3d suite: 47 tests.
- 2026-07-01: Added Docker/cgroup-aware effective CPU detection and memory-limit-aware auto caps for parser-thread `auto`, added `PLANT3D_PARSER_THREAD_CAP` / `--parser-thread-cap`, added `PLANT3D_PARSER_MEMORY_PER_THREAD_MB` and `PLANT3D_PARSER_MEMORY_RESERVE_MB`, and added worker-side Python `gc.collect()` after every processed job. Updated runbook guidance for shared Docker hosts: use capped auto or fixed thread counts plus `--max-jobs`/container restart policy for long-running conversion loads.
- 2026-07-01: `venv/bin/python -m py_compile plant3d/parsers/ifc.py plant3d/management/commands/process_plant3d_job.py plant3d/tests.py`, `venv/bin/python manage.py check`, focused cgroup/cap/GC worker tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after worker sizing and cleanup hardening. Plant3d suite: 52 tests.
- 2026-07-01: Took Claude MEM1/MEM2. `auto` now factors visible Docker/cgroup memory limits using configurable per-thread and reserve assumptions, and the runbook documents worker recycling as the mitigation for native IfcOpenShell heap fragmentation. `venv/bin/python -m py_compile plant3d/parsers/ifc.py plant3d/management/commands/process_plant3d_job.py plant3d/tests.py`, `venv/bin/python manage.py check`, focused cgroup-memory/cap/GC tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed. Plant3d suite: 55 tests.
- 2026-07-01: Added conversion process CPU-time metrics to explain short threaded conversions that Task Manager may visually miss. New job/package metrics include `process_cpu_time_ms` and `process_cpu_to_wall_ratio`; source detail and `measure_plant3d_package` now display them. A CPU/wall ratio above 1.0 is evidence of multi-core/native threaded work during the conversion.
- 2026-07-01: `node --check plant3d/static/plant3d/js/source_detail.js`, `venv/bin/python -m py_compile plant3d/services.py plant3d/management/commands/measure_plant3d_package.py plant3d/tests.py`, `venv/bin/python manage.py check`, focused conversion/measurement tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after CPU-time instrumentation. Plant3d suite: 55 tests.
- 2026-07-02: Added immutable ETag/cache-control delivery for package JSON, tile sidecar JSON, and GLB tile blobs. This is not the final signed-object-storage delivery architecture, but it improves repeat viewer opens and gives a measurable cache contract while the spike still serves artifacts through Django.
- 2026-07-02: `venv/bin/python -m py_compile plant3d/views.py plant3d/tests.py`, `venv/bin/python manage.py check`, focused package API cache test, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after artifact-cache delivery pass. Plant3d suite: 55 tests.
- 2026-07-02: Started convergence cleanup after the GLB path became the accepted runtime path. The source detail page now presents one normal production action, `Process 3D Model`, while metadata-only and JSON debug conversions are folded under `Developer actions`. Added a shared `plant3d` stylesheet and moved home, upload, source detail, and package viewer pages into a consistent engineering shell.
- 2026-07-02: Added a collapsible properties panel to the package viewer, reusing the proven `idfviewer` side-panel pattern without importing EHT-specific drawing/annotation tools into the neutral platform yet. `node --check plant3d/static/plant3d/js/source_detail.js`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, focused UI tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed. Plant3d suite: 55 tests.
- 2026-07-02: Added plant3d retention controls. Source models now record `uploaded_by`, `is_saved_case`, and `saved_at`; upload UI replacement deletes the previous unsaved working source for the same user/project; users can explicitly save up to five geometry cases per user/project; old terminal conversion jobs are pruned per source; repeated JSON/GLB conversion keeps only the latest package row per source/format. Legacy pre-migration sources have no owner and should be cleaned with `purge_plant3d_data` if they are no longer needed.
- 2026-07-02: Updated the package viewer layout to more closely match the `idfviewer` shell: topbar, left Assets panel, main 3D viewport, right Properties panel, and independent left/right collapse controls. `venv/bin/python manage.py check`, focused retention/UI tests, `node --check /tmp/package_viewer.mjs`, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, and `venv/bin/python manage.py migrate plant3d` passed. Plant3d suite: 60 tests.
- 2026-07-02: Ported the first reusable `idfviewer` interaction patterns into the neutral `plant3d` viewer: foldable object hierarchy grouped from package object summaries, hierarchy search/focus/isolate controls, package-object selection summaries embedded in package JSON, and an EHT draft tool palette for DB/JB/isolator/RTD/end termination/strap plus SR/MI/cold-cable route drafting. This is a browser draft overlay only; backend EHT layer persistence remains a separate next pass.
- 2026-07-02: `venv/bin/python -m py_compile plant3d/views.py plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused package API/viewer tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after hierarchy/EHT draft pass. Plant3d suite: 60 tests.
- 2026-07-02: Refined the object hierarchy to more closely match `idfviewer`: source/file root -> collapsible object groups -> object leaves, plus search, focus, and list filtering. EHT draft elements now render as a component hierarchy grouped by type, with type-level collapse, real type visibility toggles, real element visibility toggles, and selectable component rows.
- 2026-07-02: Per-object visibility in the hierarchy remains a focus/isolate/listing control for now. True hide/show of arbitrary GLB feature IDs should be handled later through feature-mask/shader or package-level filtering, not by pretending a checkbox can safely remove geometry from merged GLB batches. `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused viewer test, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed. Plant3d suite: 60 tests.
- 2026-07-02: Took Claude UI1/ARCH1. Removed misleading model-object hierarchy visibility checkboxes and renamed the search action to `Filter List`; the model hierarchy is now explicitly search/focus/list-filter until a real GLB feature-mask/shader visibility pass exists. EHT draft checkboxes remain because draft overlay elements are separate browser objects and their visibility toggles are real.
- 2026-07-02: Added decision record `plant3d/records/decisions/0004-eht-overlay-integration-boundary.md`. Decision: keep `plant3d` core EHT-neutral; future EHT overlay persistence must live in an EHT/integration boundary that references `plant3d` source/package/object anchors rather than adding EHT persistence models to `plant3d`.
- 2026-07-02: `venv/bin/python -m py_compile plant3d/tests.py plant3d/views.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, focused package viewer test, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the UI1/ARCH1 correction pass. Plant3d suite: 60 tests.
- 2026-07-02: Added first editable EHT draft-component behavior in the browser viewer. Draft DB/JB/isolator/RTD/end-termination/strap/route elements can now be selected from the component tree or canvas, edited through a parameter form, moved by clicking a new model position, deleted, and dimension-adjusted for point components. This remains draft-only UI under decision 0004; backend persistence still belongs in the EHT/integration boundary.
- 2026-07-02: `venv/bin/python -m py_compile plant3d/tests.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, focused package viewer test, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after editable EHT draft-component pass. Plant3d suite: 60 tests.
- 2026-07-02: Added a Three.js reference grid/axes overlay sized from package bounds, a show/hide `Grid On/Grid Off` control with scale HUD, and a first point-to-point measurement tool. Measurement mode disables EHT placement while active, lets the user pick two model/grid points, draws markers/line/label in the scene, and reports distance in metres and millimetres.
- 2026-07-02: `venv/bin/python -m py_compile plant3d/tests.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, focused package viewer test, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after grid/measurement pass. Plant3d suite: 60 tests.
- 2026-07-02: Added direct delete buttons to EHT draft component rows, local 2D plot-plan image import for the helper grid with visibility/opacity/clear controls, and fixed SR/MI/cold-cable route drafting. Route tools now exit measurement mode when selected, show live route preview points/tube while drafting, and commit visible tube-style cable geometry instead of relying on thin WebGL lines.
- 2026-07-02: `venv/bin/python -m py_compile plant3d/tests.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, focused package viewer test, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after plot-plan/delete/route-fix pass. Plant3d suite: 60 tests.
- 2026-07-02: Added owner-safe source-model delete from the source detail page so saved/working geometry cases, conversion jobs, render packages, object indexes, and stored geometry files can be deliberately removed. Deletion is project-access scoped and blocks deleting another user's owned source in the same project.
- 2026-07-02: Reworked the package viewer sidebars for readability: left panel now uses collapsible Model Hierarchy, EHT Draft Tools, and Reference Layers sections; right panel now prioritizes Selected Object, with Package Summary and Runtime Metrics collapsed below. Added low-risk Wide/Normal toggles for both sidebars instead of a drag splitter.
- 2026-07-02: `venv/bin/python -m py_compile plant3d/views.py plant3d/tests.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, focused delete/viewer tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after source-delete/sidebar pass. Plant3d suite: 62 tests.
- 2026-07-02: Added viewer polish without changing the EHT persistence boundary: left panel sections now default folded, package summary/runtime metrics stay folded while selected-object properties remain open, quick navigation controls now sit unfolded in the top toolbar beside Reset/Fit, and measurement has a `Snap Vertex` toggle.
- 2026-07-02: Tightened measurement snap behavior. With `Snap Vertex` on, measurement clicks are scoped to the currently selected model feature or draft component, avoiding accidental snaps to unrelated background geometry; users can turn snap off for free point/grid measurement. Measurement markers and labels now keep a screen-sized scale while orbiting/zooming so the endpoint spheres do not become oversized at close zoom.
- 2026-07-02: Changed selected model-object highlighting from a wireframe overlay to a depth-tested translucent color overlay to make selection easier to read against structural steel while reducing the impression that unrelated objects behind a large selected plate are also selected. This is still overlay-based, so it avoids mutating original GLB materials.
- 2026-07-02: Added `plant3d/records/planning/cable-tray-authoring-framework-2026-07-02.md` for cable tray and support authoring. The plan keeps tray/support persistence outside `plant3d` core and records plane-distance measurement as a feasible future pass.
- 2026-07-02: `venv/bin/python -m py_compile plant3d/tests.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, focused package viewer test, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, and `git diff --check` passed after toolbar/snap/highlight/sidebar polish. Plant3d suite: 62 tests.
- 2026-07-02: Changed model selection highlight color from yellow/orange to blue to better match the older `idfviewer` visual language, and restyled the top quick tools as a compact glass segmented toolbar rather than a loose set of ordinary buttons.
- 2026-07-02: Added first real selected-model hide/unhide support for GLB packages. Hidden model features use a per-vertex visibility mask and shader discard on the loaded merged GLB batches, and canvas picking skips hidden feature IDs. This is viewer-session local only; hierarchy-wide filters and persistent review visibility sets remain future work.
- 2026-07-02: `venv/bin/python -m py_compile plant3d/tests.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, focused package viewer test, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, and `git diff --check` passed after blue-selection/toolbar/selected-hide pass. Plant3d suite: 62 tests.
- 2026-07-03: Added a viewport right-click context menu with navigation actions, fit, selected hide/unhide, EHT draft move, and EHT draft delete. Added CAD-style shortcuts: `P` for pan, `O`/`R` for orbit/rotate, `F` for fit selected, `Ctrl+H` for hide/unhide toggle, and `Delete`/`Backspace` for deleting the selected EHT draft element. Shortcuts are ignored while typing in inputs/forms.
- 2026-07-03: Extended viewer-session visibility controls to EHT draft elements as well as GLB model features. Hidden EHT drafts reuse the existing draft hierarchy visibility state; `Unhide All` restores both hidden model features and hidden EHT draft items.
- 2026-07-03: `venv/bin/python -m py_compile plant3d/tests.py`, `node --check /tmp/package_viewer.mjs`, `venv/bin/python manage.py check`, focused package viewer test, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, and `git diff --check` passed after context-menu/shortcut pass. Plant3d suite: 62 tests.
- 2026-07-04: Accepted the Stage 0 service-extraction pivot in `plant3d/records/decisions/0005-plant3d-independent-platform-boundary.md`: `plant3d` is now treated as an independent platform boundary co-located in the current repo, with full service/database extraction deferred until a concrete trigger.
- 2026-07-04: Loosened the hard EHT project coupling. `SourceModel.project` FK/cascade was replaced with a loose `project_id` string reference; upload project listing, project access, and write-time validation now go through `plant3d.project_gateway`. The gateway still calls EHT internally during Stage 0, but the dependency is confined to one seam.
- 2026-07-04: Added migration `0003_loosen_project_reference` and a regression test proving deleting an EHT `ProjectData` row no longer cascades into `plant3d` source models. Removed `select_related("project")` runtime assumptions and updated upload tests to use `proj_id` as the public boundary identifier.
- 2026-07-04: `venv/bin/python -m py_compile plant3d/models.py plant3d/forms.py plant3d/access.py plant3d/project_gateway.py plant3d/services.py plant3d/views.py plant3d/tests.py`, `venv/bin/python manage.py check`, `venv/bin/python manage.py migrate plant3d`, `venv/bin/python manage.py makemigrations plant3d --check --dry-run`, focused no-cascade test, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after Stage 0 decoupling. Plant3d suite: 63 tests.
- 2026-07-04: KR manually checked EHT and `plant3d` after Stage 0 decoupling and reported no regression or side effect. The tracker was refreshed to prioritize extraction readiness, API/overlay boundaries, gateway hardening, and continued 3D-tool maturity while explicitly deferring Celery/Redis until later.
- 2026-07-05: Added focused `plant3d.project_gateway` tests covering project identifier normalization, anonymous access, scoped project picker options, accessible/inaccessible/unknown project validation, legacy primary-key normalization, and a seam guard that fails if runtime EHT model imports reappear outside `project_gateway`. Added `plant3d/records/planning/public-api-boundary-contract-2026-07-05.md` to define the Stage 0 integration contract for projects, sources, jobs, packages, tiles, model objects, coordinates, overlays, access, and deferred API decisions.
- 2026-07-05: `venv/bin/python -m py_compile plant3d/project_gateway.py plant3d/forms.py plant3d/access.py plant3d/tests.py`, `venv/bin/python manage.py check`, focused gateway/intake tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, and `git diff --check` passed after the boundary/API contract and gateway-hardening pass. Plant3d suite: 71 tests.
- 2026-07-05: Added the first browser-side overlay seam without changing user behavior. `package_viewer.js` now registers generic viewer layers for the plant model, measurement overlay, grid/axes reference, 2D plot-plan reference, EHT draft overlay, and EHT route preview. The registry is exposed as `window.plant3dViewerLayers.summary()` for debugging/review and gives future EHT/raceway tools a shared layer vocabulary instead of more ad hoc globals.
- 2026-07-05: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused viewer tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, and `git diff --check` passed after the viewer-layer registry pass. Plant3d suite: 72 tests.
- 2026-07-05: Turned the overlay seam into visible product UI. The Reference Layers section now renders a compact layer list from the registry, with viewer-session toggles for the plant model, measurement overlay, grid/axes reference, plot-plan reference, and EHT draft layer. Existing Grid and Plot Plan controls stay synchronized with the layer list, hidden model layers are excluded from picking, hidden EHT draft layers are excluded from draft picking/snap, and layer counts update during package load, tile streaming, draft edits, and measurement changes.
- 2026-07-05: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused viewer tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, and `git diff --check` passed after the product-facing layer-control pass. Plant3d suite: 72 tests.
- 2026-07-05: Reviewed Claude's platform-boundary RFC. Accepted the direction of the three-tier contract model and the near-term API cleanup list, but deliberately kept this pass product-focused. Tracker now carries the follow-up: remove public `manifest_storage_key`, promote top-level coordinate-transform fields, add per-source JSON, and add API contract tests. KR decision still needed before backend work: `OverlayAnchor` should be a plain shared shape/helper rather than a `plant3d`-owned annotations table.
- 2026-07-05: Added viewer usability improvements: `Show All` and `Hide Overlays` layer presets, visible layer-off styling, hidden-layer/model/EHT badges, synchronized hidden-state feedback after hide/unhide actions, and a first `Plane Δ` clearance tool that reports selected model/EHT draft distance to the current grid/reference plane. The plane-distance readout appears in selected-object and draft-property panels and can be triggered from the top toolbar.
- 2026-07-05: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused viewer tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, and `git diff --check` passed after the usability/plane-distance pass. Plant3d suite: 72 tests.
- 2026-07-05: Took the manual-test polish pass. EHT draft point/route selections now expose numeric Position X/Y/Z controls in the selected-object panel for fine placement. Canvas drag/orbit/pan gestures suppress accidental EHT placement, and Escape now cancels active drawing tools, pending route previews, and move mode before falling back to selection clear.
- 2026-07-05: Added browser-local EHT draft persistence as an interim product feature. `Save Draft Local` stores draft elements/routes/parameters to `localStorage` for the current package URL and restores them on viewer reload. This is deliberately not the final database-backed EHT layer; backend persistence still belongs in an EHT/integration boundary, not `plant3d` core.
- 2026-07-05: Improved the source/model-processing page for regular users: raw storage/signature details moved under `Technical source details`, conversion jobs now show progress bars in the initial HTML and live polling rows, and the package/source API cleanup from Claude's RFC landed: per-source JSON endpoint added, source JSON no longer exposes `storage_key`, package JSON no longer exposes raw `manifest_storage_key`, and package JSON now exposes top-level `coordinate_transform`.
- 2026-07-05: `venv/bin/python -m py_compile plant3d/views.py plant3d/urls.py plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check plant3d/static/plant3d/js/source_detail.js`, `node --check /tmp/package_viewer.mjs`, focused API/viewer/source tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, and `git diff --check` passed after the polish/API cleanup pass. Plant3d suite: 73 tests.
- 2026-07-05: Started the fine-placement usability pass. EHT point components now live-update their X/Y/Z position from inspector edits without requiring the Apply button, route/cable draft elements expose editable per-node X/Y/Z fields, point-device placement offsets outward from the clicked model face normal to reduce structure penetration, double-click focus frames the picked object/draft item when no drawing/measure mode is active, and EHT draft type expand/collapse controls use compact `+`/`-` buttons. Mouse-drag route-node handles remain deferred until a dedicated handle/gizmo mode is added so it does not fight orbit/pan gestures.
- 2026-07-05: Refreshed `plant3d/records/planning/raceway-module-architecture-2026-07-02.md` with the current viewer primitives available for the coming tray/raceway module: generic overlay layers, editable route nodes, surface-normal placement offset, plane-distance measurement, and the boundary rule that durable EHT/raceway data belongs to the consumer module/integration app while `plant3d` supplies anchors and render context.
- 2026-07-05: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused viewer/source tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, and `git diff --check` passed after the fine-placement/raceway-readiness pass. Plant3d suite: 73 tests.
- 2026-07-05: Took a second safe UI/electrical-intent pass. Corrected point-device placement to offset toward the visible side of the clicked face using camera-facing normals and component extents; exposed `window.plant3dViewerLayers.register/update/setVisible/isVisible` for future external overlay consumers; removed the public `manifest_storage_key` leak from embedded job package JSON; added route-node viewport labels; and added first-pass cable route anchoring so cable routes must start and finish on different EHT point components while intermediate bend nodes remain free. Full clash/physics hard stops are deferred until mounting/orientation and collision-volume rules are designed.
- 2026-07-05: `venv/bin/python -m py_compile plant3d/views.py plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused job/viewer tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, `git diff --check`, and `git diff --cached --check` passed after the cable-anchor/contract cleanup pass. Plant3d suite: 73 tests.
- 2026-07-05: Took a small route-UI polish and collision-planning pass. Route node coordinate controls are more compact, node labels are hidden by default behind a `Node Labels` toggle and render with shorter badges, selected EHT draft elements now tint blue in the 3D view, and the raceway plan now records a deliberate collision/routing engine gate: avoid fake hard-stop physics, add warning/preview/hard-constraint levels, move cable routing toward source/destination-first Manhattan suggestions, and reserve A*/Dijkstra for suggestion workflows after anchors and avoid zones exist.
- 2026-07-05: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused viewer tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, `git diff --check`, and `git diff --cached --check` passed after the route-UI/collision-planning pass. Plant3d suite: 73 tests.
- 2026-07-05: Took the route clutter cleanup pass. Removed the explicit `Node Labels` button; route node labels now appear automatically while creating a route or when an existing route is selected. Component and route-node XYZ controls now use compact grouped coordinate rows. Confirmed there is no hard/soft floor-stop collision code to remove; the retained logic is only the surface-normal placement offset. Raceway planning now carries the recommended route-engine order: source/destination mode, routing core, Manhattan suggestion, A*/Dijkstra extension, then collision-cost integration.
- 2026-07-05: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused viewer tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, `git diff --check`, and `git diff --cached --check` passed after the route clutter cleanup pass. Plant3d suite: 73 tests.
- 2026-07-05: Started the source/destination-first route workflow. Route tools now enter an explicit workflow state (`select_source`, `select_destination`, `edit_route`) instead of free-clicking from the first point. The user selects a source EHT component, then a destination EHT component; the viewer locks those endpoints and starts a route preview. `Finish Route` now requires the route to be in edit mode with valid, different anchors.
- 2026-07-05: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused viewer tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, `git diff --check`, and `git diff --cached --check` passed after the source/destination-first route workflow pass. Plant3d suite: 73 tests.
- 2026-07-06: Took KR manual-feedback correction on route UX. After source/destination are locked, additional clicks are now route guide points, not exact physical cable nodes. The viewer expands guide points into a deterministic Manhattan-style orthogonal route (`X -> Z -> Y` per guide segment), previews that route, and commits the generated route on `Finish Route` with `route_method=manhattan_guide`. Immediate Claude takeaways accepted: same-source/destination rejection at transition, Escape/Cancel-to-idle behavior, source/destination-first route state, Manhattan heuristic before graph search. Deferred/discussion items: live anchor re-resolution, RTD workflow scope, persistence owner app, collision/BVH, route warnings severity, and A*/Dijkstra graph search.
- 2026-07-06: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused viewer tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, `git diff --check`, and `git diff --cached --check` passed after the Manhattan guide-point route UX pass. Plant3d suite: 73 tests.
- 2026-07-06: Added the first route re-edit loop. Finished cable routes now carry guide-point and loose source/destination anchor metadata. Selecting a route exposes `Edit Route`, which reopens the same route into the source/destination-first workflow; `Finish Route` updates that route instead of duplicating it. Added contextual route controls for `Undo Guide` and `Reset Path` while editing/creating a route. This improves usability but does not replace the planned pure routing-core extraction.
- 2026-07-06: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/package_viewer.mjs`, focused viewer tests, `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`, `git diff --check`, and `git diff --cached --check` passed after the route re-edit loop pass. Plant3d suite: 73 tests.
- 2026-07-06: Took the next cable-routing control pass. Added a small browser-side `routing_core.js` with pure Manhattan route helpers and diagnostics so the viewer is no longer the only owner of route math. Added on-scene draggable intermediate guide handles while creating/editing a route; source/destination endpoints remain anchored and non-draggable. This gives users direct route-shaping control without forcing premature collision physics or A*/Dijkstra.
- 2026-07-06: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/routing_core.mjs`, `node --check /tmp/package_viewer.mjs`, focused viewer/static tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the route-core/guide-handle pass. Plant3d suite: 73 tests.
- 2026-07-06: Added the first reusable route validation layer. `routing_core.js` now returns route diagnostics and block/warn/info validation messages for impossible anchors, very short segments, non-orthogonal segments, excessive bends, and simplifiable collinear nodes. The viewer records warnings in route metadata and shows compact diagnostics/warning badges on selected cable routes. Architectural direction confirmed: author raceway/containment networks first where available, then route cables through them; keep free/manual cable routing as a controlled exception path until raceway graph routing exists.
- 2026-07-06: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/routing_core.mjs`, `node --check /tmp/package_viewer.mjs`, focused viewer/static tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the route-validation pass. Plant3d suite: 73 tests.
- 2026-07-06: Took the routing-control polish pass. Added browser-side draft undo/redo stacks with `Ctrl+Z` and `Ctrl+Shift+Z`, plus separate in-progress route-edit history so cable guide-point edits undo without touching committed draft elements. Added left-panel `Edit Selected Route`, `Delete Guide`, and `Redo` controls. Selected intermediate route guide points can now be deleted; source/destination guide points remain protected. Deleting a source/destination EHT point component now cascades to associated cable routes so cables do not hang without anchors.
- 2026-07-06 strategy note: JS routing code is the responsive preview/authoring layer only. Python must become the authoritative route validator before any durable EHT/raceway save is accepted. Keep the overlap intentionally small: JS owns instant interaction, guide dragging, ghost routes, and optimistic warnings; Python owns persisted-rule gates for bend radius, dangling ends, source/destination validity, segregation/capacity, and future construction deliverables.
- 2026-07-06: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/routing_core.mjs`, `node --check /tmp/package_viewer.mjs`, focused viewer/static tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the routing-control polish pass. Plant3d suite: 73 tests.
- 2026-07-06: Added the first route HUD/intent pass. The left EHT panel now shows a compact active/selected route HUD with source, destination, length, segments/bends, guide count, substrate, warning count, and next action. `routing_core.js` now also exposes a neutral graph skeleton (`createRouteGraph`, `summarizeRouteGraph`) so future raceway/tray/duct networks can be represented as nodes/edges before A*/Dijkstra or persisted `raceway` models are introduced.
- 2026-07-06: `venv/bin/python -m py_compile plant3d/tests.py`, `venv/bin/python manage.py check`, `node --check /tmp/routing_core.mjs`, `node --check /tmp/package_viewer.mjs`, focused viewer/static tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after the route-HUD/graph-skeleton pass. Plant3d suite: 73 tests.
- 2026-07-06: Took the source-page and route-edit touchup pass. Upload source now auto-submits when a file is selected; source detail now defaults to a clean normal-user path with advanced conversion/job/package/cleanup details tucked behind explicit sections; selected-route HUD now floats over the viewer instead of consuming left-panel space; route edit guide clicks now insert into the nearest existing route segment to reduce unrealistic zigzag reroutes. `node --check /tmp/routing_core.mjs`, `node --check /tmp/package_viewer.mjs`, focused upload/source/viewer tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed. Plant3d suite: 74 tests.
- 2026-07-07: Superseded experiment: tightened route-edit controls with orthogonal default dragging plus `Ortho Move` / `Free Move`. Manual testing rejected this as still too clever/unpredictable for first-pass cable authoring.
- 2026-07-07: Superseded experiment: corrected `Free Move` route semantics after KR manual review. This proved direct polyline routes were needed, but the final UI was simplified further into centerline-first authoring.
- 2026-07-07: Simplified route authoring to default centerline drafting. New source/destination routes start in Centerline mode, clicks add ordered centerline points, and `Ortho Assist` is now an optional toggle rather than the primary behavior. This intentionally steps back from clever auto-routing until the raceway/collision/pathfinding layer is ready.
- 2026-07-07: Took the routing housekeeping pass after multiple UX experiments. Removed stale route import/test expectation, corrected user-facing route status text, simplified Ortho Assist insertion helper, refreshed the active tracker plan to centerline-first, and marked the rejected Ortho/Free experiments as superseded. Added a supersession note to Claude's cable-routing RFC so always-on Manhattan analysis is treated as historical.

## Cable Tray / Raceway Module — Claude Architecture Notes (2026-07-02)

Research-based thought process on Codex's `cable-tray-authoring-framework-2026-07-02.md`. Full design: `plant3d/records/planning/raceway-module-architecture-2026-07-02.md`.

### Strong agreement

- Tray/support persistence **must stay out of `plant3d` core** — same as decision 0004 for EHT. The viewer hosts the *interaction* layer; the discipline owns its data. This is the correct, non-negotiable boundary.
- Route-first draft tools, snapping to model/grid/vertices, parametric width/depth preview, auto-support spacing, plane-distance measurement as a focused later pass — all sound.

### One refinement worth a KR decision (the fork)

Codex's framework folds tray persistence into the **"EHT/electrical integration layer."** I recommend instead a **separate `raceway` peer app**, *not* a sub-part of EHT. Rationale:
- Raceway is **shared physical infrastructure** consumed by *multiple* disciplines — EHT, power/control cable routing, and construction/pulling all reference the same trays. It is not an EHT feature; putting it under EHT recreates a coupling and blocks the other consumers.
- Dependency shape should be: `eht → plant3d`, `raceway → plant3d`, and later `cable-routing → raceway + plant3d`. Raceway is a **peer** of EHT, not a child of it.
- Net: keep the boundary Codex drew (out of `plant3d` core) **and** give raceway its own app. Same rule, cleaner placement.

### Research-based pillars to fold into the framework

1. **Overlay contract (shared).** Formalise how any module plugs into the viewer: read `ModelObject` + the **RTC coordinate contract**, register an overlay group (like `measurementGroup`), reuse `access.*_for_user`. EHT and raceway use the identical seam.
2. **Route-as-truth, parts-as-derived.** User edits a centerline `TrayRun`; straights + fittings + supports are **materialised** from the catalogue and regenerated on edit — mirrors plant3d's own "source → derived package" model. Never hand-edit derived parts.
3. **Parametric library, not stored meshes.** Types × sizes × fittings × supports is combinatorial — store parameters + generation rules + **load/span tables** (NEMA VE / IEC 61537), not a mesh per instance. Generic families first; vendor parts under the existing validation governance.
4. **Hybrid geometry.** Client-side live generation while drafting (instant feel) → server "bake" to a GLB overlay on save, riding the existing RTC/tile/feature-ID pipeline (pickable tray parts, no new renderer).
5. **Graph-ready from day one.** `TrayRun`/`TrayNode` *is* the node/edge graph the future cable-routing/pulling module traverses (edges carry length + fill capacity). Design stable keys now; attach later without schema change.
6. **Support spacing is engineered.** Auto-place from the load table (tray + cable-fill weight vs allowable span), anchored to a structural `ModelObject.stable_id`, with pass/fail — not a fixed spacing guess.
7. **Deliverables, phased.** BOQ/schedules first (near-free from derived rows) → DXF layout drawings (AutoCAD-openable for both contractors) → support **fabrication** sheets. Full drafting-grade 2D is a large subsystem; do not front-load it.

### UX (the commercial differentiator)

One principle: **route-first, part-later** — the failure mode of plant tools is placing 3 m sections one at a time. Key moves: **elevation-plane (2.5D) routing** (lock a working plane at EL, draw like on a floor, riser up/down), snapping as the product, a **live route HUD** (length/fill/next support/clashes), colour-by-service, recolour-selection (not wireframe — matches KR item d), and a **ghost-the-plant focus mode** (Navisworks-style).

### Open decisions for KR (before raceway coding starts)

1. **Module placement:** separate `raceway` app (recommended) vs fold into EHT-integration.
2. **App name:** `raceway` (covers ladder/tray/trunking/conduit) vs `cabletray`.
3. **Governing standard** for support span / fill defaults: NEMA VE-1/VE-2 vs IEC 61537 (configurable per project).
4. **Catalogue seed:** ship a curated generic library vs start empty.
5. **Geometry approach:** confirm the hybrid (client live-author + server bake). Recommended.

## Platform Rules Discovered During Implementation

- Browser viewers should load render packages through stable platform API URLs, not direct storage keys. This preserves freedom to move from local/self-hosted storage to MinIO, Oracle Object Storage, S3, signed URLs, or CDN delivery later.
- Stable platform package/tile URLs should expose a cache contract even before object storage is adopted. Immutable ETags/304 responses are now part of the Django spike delivery path for package manifests, tile sidecars, and GLB blobs.
- Reuse `idfviewer` UI behavior selectively. The foldable panels, hierarchy search, component lists, and drawing palette are useful product patterns; the old EHT-specific persistence and prototype assumptions should be reimplemented against `plant3d` models rather than copied wholesale.
- The current JSON geometry viewer is useful for proving flow and debugging, but it is not the final large-model runtime format.
- GLB+sidecar is the first serious runtime package candidate. The sidecar keeps metadata available while the GLB focuses on renderable geometry; feature/object IDs are now present, while BVH picking/highlighting remains deferred.
- Do not treat a renderable GLB as a complete engineering package until feature IDs are connected to selection, filtering, highlighting, and backend metadata lookup.
- Browser verification should include a real converted package, not only mocked API tests.
- Access checks must be applied at source, package, and tile levels because package/tile IDs are enough to expose cross-project data if left unscoped.
- Conversion writes must be transactional so a failed package/index rebuild does not destroy the previous object index.
- Object picking should fetch metadata from the indexed `ModelObject` API rather than depending only on tile JSON properties.
- Manual viewer testing is now useful after a real IFC is uploaded and processed because the viewer shows runtime metrics and selected-object metadata.
- RTC origin should be visible in package/tile APIs and viewer metrics so large-coordinate behavior can be inspected during real IFC tests.
- Coordinate metadata must name its frame explicitly. A stored RTC origin is only useful if it is in the same frame as the geometry vertices and can reconstruct source/world coordinates with a tested formula.
- Measurement should be built into the spike UI and job records from the start; otherwise real-file testing will produce subjective impressions instead of architecture evidence.
- Merged visible geometry and per-object pick proxies are a useful bridge for the JSON debug viewer, but the production format should move picking IDs/feature metadata into the render package rather than duplicating geometry in browser memory.
- GLB packages should not reintroduce hidden per-object pick-proxy geometry. The next picking strategy should use feature IDs, object spans, BVH picking, or metadata-backed selection designed for binary packages.
- Direct GLB render-mesh raycast is acceptable as the first feature-ID proof, but it is not the final acceleration strategy. If pick latency rises on larger samples, adopt `three-mesh-bvh` before adding more UI features.
- Adaptive pixel ratio is a practical interaction bridge, not the final EPC-scale solution. If FPS remains poor while the viewer is already in `adaptive-interaction` or `adaptive-fps-downshift`, the next fix must be geometry-side: tiling, LOD, instancing, meshopt, or BVH/picking acceleration.
- A single-root `tileset.json` was only an architecture contract. The current path now has spatial child GLB tiles plus first viewer-side stream/cull behavior, but it still needs real browser measurements before performance claims.
- Feature IDs in GLB must stay glTF-conformant before meshopt/gltfpack work begins. Use `FLOAT` or the future standard feature metadata extension, not `UNSIGNED_INT` vertex attributes.
- GLB sidecar stable IDs and `ModelObject.stable_id` must be generated by the same resolver. Otherwise GUID-less IFC objects and future IDF/PCF objects will render but fail pick-to-metadata.
- Spatial child tiles now exist in the package and the current viewer no longer has to fetch/render all child tiles at once for packages above the active-tile cap. This proves the first streaming behavior, not final EPC-scale performance.
- Engineering review needs an explicit completeness contract. A fast partial view is not acceptable if users cannot tell whether geometry is missing, still loading, or intentionally out of the active cache.
- Local spike DB cleanup through Django admin is acceptable, but storage cleanup needs an explicit tool/command. Otherwise media blobs under `MEDIA_ROOT/plant3d` will become orphaned.
- Spike UX should expose the exact worker command and poll job status from the source page so manual IFC testing does not depend on raw JSON pages or repeated full-page refreshes.
- A queued job is not a failed conversion. In the current spike, no package/view link appears until `process_plant3d_job` runs and the source page sees the completed job.
- Browser verification should distinguish nonblank render success from performance success. The current real-sample probe renders correctly, but Tekla FPS is below target.
- Source-declared IFC units and render geometry units are different facts. Store both: source unit from `IfcUnitAssignment`, render unit from parser/IfcOpenShell geometry settings, and only mark measurement scale trusted after a known-dimension validation.
- Meshopt byte savings are not sufficient for adoption. Compressed GLB packages must also prove feature-ID picking correctness because compression/quantization can reorder or alter custom vertex attributes.
- Do not use compression as a substitute for tiling/completeness strategy. Compression reduces payload bytes, but it does not solve model completeness, LOD/HLOD, metadata identity, annotation anchoring, or source-unit correctness.
- Windows Task Manager GPU load is not a reliable indicator for server-side conversion. Watch the browser process and the viewer's WebGL renderer/frame-time metrics for display performance; watch worker logs, conversion duration, CPU, disk IO, and memory for conversion performance.
- A tile-loading error is a completeness state, not a transient log message. Production viewers must distinguish complete, loading, partial, and failed/incomplete geometry so engineering users do not trust a permanently incomplete scene.
- Do not optimize conversion speed from a total duration alone. Use per-stage timings first; if `parse_ms` dominates, the real speed lever is parser/native tooling and should be treated as an architecture decision, not a quick code tweak.

## Manual Testing Checklist

When an IFC sample is available, test manually:

1. Log in as a user assigned to the target managed project.
2. Open `/plant3d/sources/upload/`.
3. Upload an IFC file and confirm it redirects to the source detail page.
4. Queue metadata conversion and confirm JSON response shows `status: queued`.
5. Start the local worker once in a separate terminal with `venv/bin/python manage.py process_plant3d_job --watch`; it should claim queued jobs automatically.
6. Refresh the source detail page and confirm a metadata package appears.
7. Run IFC geometry conversion and confirm JSON response shows `status: queued`.
8. Confirm the already-running worker claims and processes the queued job.
9. Queue and process IFC GLB conversion for the same source.
10. Refresh the source detail page and open both JSON and GLB package viewer links.
11. Confirm each model appears, can orbit/pan/zoom, and shows load status.
12. Record conversion duration from the source detail job metrics.
13. Record viewer load time, rough FPS, draw calls, render batches, pick proxies, triangles, mesh count, pixel ratio, quality mode, tile origin, pick latency, metadata latency, and visible jitter from the viewer sidebar.
14. For GLB packages, click a visible object and confirm the selected-object panel resolves a feature ID to indexed metadata; record pick latency and any sluggishness.
15. Log in as a user not assigned to that project and confirm source/package/tile URLs return 404.

## Claude Research / Review Asks Status

Completed or superseded:

- Runtime format recommendation is recorded in `plant3d/records/planning/claude-render-format-research-2026-06-23.md`: GLB + meshopt + feature IDs + 3D-Tiles-style manifest, no custom binary and no xeokit/AGPL for now.
- Three.js remains acceptable for the spike; Babylon.js comparison is deferred until real GPU/browser failure after batching/tiling/LOD.
- JSON geometry loading is retained as a debug/comparison path only.
- Parser extraction timing is resolved: `plant3d` now imports from `plant3d.parsers.ifc`, not from `idfviewer`.
- IFC unit handling is partially resolved: source-declared units and render units are stored separately; real known-dimension proof remains open.

Active asks:

- Review the meshopt feature-ID correctness gate before we accept `gltfpack -cc` as production-safe.
- Recommend or review a practical foot-declared Revit known-dimension fixture.
- Review when to introduce LOD/coarse proxies for over-cap tile views.
- Review object-storage/signed-URL delivery when the package format stabilizes.

Historical asks retained below for context:

- Research and recommend the next runtime package format after the JSON spike:
  - GLB/glTF with metadata sidecar
  - 3D Tiles style manifests
  - meshopt-compressed glTF
  - custom binary tile chunks
- Review whether Three.js JSON loading should be kept only as a debug path once GLB/tiling begins.
- Review the merged-visible-geometry plus hidden-pick-proxy strategy and recommend the production picking approach for GLB/binary tiles.
- Review the new GLB+sidecar path: validate GLB structure, sidecar contents, and recommend the next feature-ID/object-picking strategy.
- Review the glTF axis convention decision: current render frame uses `x,z,y`; choose whether to keep that convention in GLB or emit glTF-standard Y-up with a root transform.
- Recommend measurable thresholds for when JSON payload size becomes unacceptable and we must move to GLB/binary tiles.
- Independently review API delivery strategy: direct platform JSON API now versus signed object-storage URLs later.
- Review the right timing and minimal implementation for moving inline conversion to queued worker/SSE progress.
- Review whether parser extraction from `idfviewer` should happen before real-file metrics or immediately after.
- Review IFC unit handling: confirm whether IfcOpenShell vertices are already SI-normalized in our parser path, and recommend how to store source units versus render units for measurement/federation.
- Review the headless-browser FPS result: determine whether low FPS is mainly software/headless rendering, hidden pick proxies, JSON geometry shape, or a renderer/package issue.
- Recommend a practical scale-validation fixture: known IFC dimension, source-system benchmark, or synthetic IFC that proves header units versus rendered coordinates.
