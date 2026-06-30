# plant3d Pipeline Spike Tracker

Date: 2026-06-22

Status: execution spike in progress; GLB/Three.js viewer path is healthy on current samples; current focus is correctness gates plus conversion-stage timing, not render/pick optimization

## Objective

Prove the first source-file-to-browser pipeline for the new 3D platform before building a polished workspace UI or broad semantic model.

The spike should answer:

- Can the web-first platform render real IFC/model data acceptably?
- What conversion/package strategy should become the first platform foundation?
- What metadata and precision fields are required from day one?
- How much of the current `idfviewer` prototype should be harvested?

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
- Worker parser-thread selection now needs deployment sizing: `auto` is appropriate for a roomy local/dev worker, but shared cloud Docker hosts should use cgroup-aware `auto` plus `--parser-thread-cap` or a fixed thread count to avoid starving database and sibling containers.
- KR manual comparison against `idfviewer` found that 10-15 MB IFC conversion/render time is roughly comparable between the old prototype and `plant3d`, so the immediate user-visible gap is not speed at this scale. `idfviewer` still feels visually cleaner on beam edges, while `plant3d` feels slightly lighter during movement. The next viewer passes should preserve completeness and responsiveness while improving visual fidelity and selected-object feedback.
- Naive Three.js object-per-mesh rendering will not scale.
- Coordinate precision problems may not show unless source files use large coordinates.
- Browser memory and draw calls can become the limiting factor before triangle count.
- Manual side-by-side review against `idfviewer` exposed a serious viewer completeness issue: active-cap tile streaming can show holes or incomplete steelwork, and camera rotation can unload previously visible geometry while new tiles load. This is expected from the first cap/unload algorithm but unacceptable for production engineering review. The immediate mitigation is now complete/review mode for manageable packages, persistent completeness status, and retained-cache partial streaming for larger packages. HLOD/coarse proxies remain the future production answer.
- Conversion now runs off-request through a management-command worker for the spike. Full Celery/RQ/SSE infrastructure is still required before user-facing or long-running production workflows.
- The spike worker now has a documented long-running container role in `plant3d/records/operations/worker-container-runbook-2026-06-28.md`; local/manual operation should use `process_plant3d_job --watch`, not repeated `--all` runs.
- The IFC parser is now copied under `plant3d/parsers/`, closing the immediate platform-boundary dependency on `idfviewer`. Future parser refactor/shared ownership is still possible.
- Package/tile JSON is still served through Django. This is acceptable for the spike but must move toward signed object-storage URLs before real-scale use.
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
- Production delivery remains deferred: package/tile payloads should move from Django JSON responses to signed object-storage URLs before real scale.
- Production package format remains partially deferred: first GLB+sidecar, feature IDs, spatial child tiles, a 3D-Tiles-style manifest, first viewer-side tile streaming/culling, synthetic large-coordinate GLB child-tile regression, optional meshopt/gltfpack hook, and `MeshoptDecoder` viewer support exist. Rendering is acceptable on the current sample set; measured compression, instancing, signed/object-storage delivery, and real plant-global precision proof remain open. BVH is parked unless real picking latency regresses.
- Compression strategy clarification after external/general review: current code path is GLB + optional `gltfpack`/meshopt (`EXT_meshopt_compression`), not Draco. Draco (`KHR_draco_mesh_compression`) remains a future comparison option, but it is not the current default because runtime decode speed, feature-ID preservation, and annotation/picking correctness matter more than headline byte reduction.
- GLB feature IDs are now present in the first binary package path via `_FEATURE_ID_0` plus sidecar object-feature mapping. The viewer can now click GLB render meshes and resolve feature ID -> stable ID -> `ModelObject` metadata without hidden per-object proxies. BVH acceleration and shader/feature-ID highlighting are still deferred.
- Local spike data cleanup is now supported by `purge_plant3d_data`: Django admin deletion is acceptable for DB-only cleanup during tests, but the command should be used when source/render storage blobs also need to be removed.
- Unit/scale proof is improved but not fully closed: IFC `IfcUnitAssignment`, IfcOpenShell geometry settings, a synthetic metre-declared known-one-metre fixture, and a synthetic foot-declared known-one-metre fixture now validate the service contract. A real source-system/exporter benchmark is still needed before trusting measurement/federation workflows.
- Parser cleanup remains a TODO: the extracted parser is a direct copy for boundary safety, not yet a deeply refactored production parser.

## Immediate Next Actions

> **Claude sequence review (2026-06-23) — see audit R1-R3 / C1-C5.** KR confirmed real-GPU rendering is smooth (15-17 FPS is a headless artifact) and a plant-global IFC is weeks away. Claude recommended promoting a synthetic large-coordinate offset fixture, known-dimension unit fixture, and meshopt compression. The 2026-06-28 pass landed the synthetic known-one-metre fixture, a synthetic large-coordinate GLB child-tile regression, and first viewer streaming because package 24 already gave us a useful 9-child-tile runtime proof. The list below is the post-2026-06-28 order.

1. Correctness gate F3: obtain or create a real plant-global/georeferenced IFC test before marking float32 jitter, RTC precision, orbit stability, or measurement stability as proven.
2. Correctness gate C3/F4: synthetic metre-declared and foot-declared one-metre fixtures are covered; add a real source-system/exporter known-dimension proof before marking measurement/federation scale fully trusted.
3. Conversion performance A/B: **done for current 13.7 MB sample.** Worker parser threading is a confirmed local win: 61,073 ms -> 11,826 ms total conversion, with stable RAM. The recommended local/dev worker hint now uses `--parser-threads auto`. Before making this a hard production default, repeat on the largest available IFC and size worker CPU/RAM intentionally.
4. Phase 7 partial decision: write the rendering decision with current evidence: Three.js-first and GLB + tiling + complete-review are acceptable at current sample scale; precision-at-scale and unit truth remain open gates. **Done 2026-06-30: see `plant3d/records/decisions/0003-phase-7-rendering-spike-decision.md`.**
5. Opportunistic only: when `gltfpack` is available, measure real meshopt compression ratio, compression duration, browser decode/load time, and feature-ID correctness with `measure_plant3d_package`. Payload is not the current bottleneck.
6. If real `gltfpack -cc` output is rejected by the feature-ID gate, discuss before changing format strategy: options include safer gltfpack args, keeping meshopt disabled, or a future `EXT_mesh_features`/metadata-extension pass.
7. Evaluate `three-mesh-bvh` acceleration only if direct render-mesh raycast becomes sluggish on larger samples.
8. Use `purge_plant3d_data` for clean local retests when DB rows and storage blobs should both be removed.
9. Keep production EHT, cold cable, SLD, and `idfviewer` behavior unchanged.

2026-07-01 coding note: Phase 7 tracker checkboxes are now closed against decision record 0003, but the acceptance remains deliberately scoped to current sample scale. Added a stronger synthetic F3 guard proving child-tile GLB payloads keep plant-global coordinates in tile RTC metadata while GLB vertex positions stay tile-local and reconstruct back into source-coordinate tile bounds. This does not replace the real plant-global IFC gate.

2026-07-01 timing note: KR's fresh 13.7 MB `8-SSPAU-800203.ifc` GLB run recorded 61,073 ms total, with `parse_ms=59,656 ms`, GLB build 479 ms, tile write 29 ms, tileset write 1 ms, and DB/index write 329 ms. The next pass added an explicit `process_plant3d_job --parser-threads` option so the A/B test is repeatable without hidden environment variables.

2026-07-01 A/B result: the same sample converted with `process_plant3d_job --watch --parser-threads auto` completed in 11,826 ms, with `parse_ms=10,411 ms`. CPU rose to about 97%, GPU stayed unchanged as expected, and RAM stayed around 30%. The source-detail and JSON worker hints now recommend the threaded worker command for local/dev conversion.

2026-07-01 worker sizing note: `auto` now uses a Docker/cgroup-aware effective CPU count where Linux exposes CPU quota files, and supports a thread cap (`--parser-thread-cap N` or `PLANT3D_PARSER_THREAD_CAP=N`). The worker also calls Python garbage collection after each job. Native IfcOpenShell allocations can still benefit from operational recycling, so production/shared Docker workers should use explicit CPU/RAM limits and consider `--max-jobs` plus container restart policy for long-running conversion loads.

Current manual check path:

1. Upload one available local sample IFC from `ifc/` through `/plant3d/sources/upload/`.
2. Start the local worker once in a separate terminal: `venv/bin/python manage.py process_plant3d_job --watch --parser-threads auto`.
   For a crowded/shared Docker host, use a cap or fixed count, for example `--parser-threads auto --parser-thread-cap 2` or `--parser-threads 2`.
3. Run metadata conversion through the source detail page or POST endpoint.
4. Run IFC JSON debug conversion if needed; the worker should pick it up automatically.
5. Queue the IFC GLB conversion; the worker should pick it up automatically.
6. Open both package viewers and compare package size/load behavior.
7. Measure the resulting package with `venv/bin/python manage.py measure_plant3d_package <package_id>`.
8. Record the timing line from `measure_plant3d_package`, especially `parse_ms`, `glb_build_ms`, `tile_write_ms`, and `db_write_ms`.
9. For a clean local reset, first dry-run `venv/bin/python manage.py purge_plant3d_data --project-id <proj_id>` or `--source-id <id>`, then add `--confirm` only after reviewing the summary.

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
- 2026-07-01: Added Docker/cgroup-aware effective CPU detection for parser-thread `auto`, added `PLANT3D_PARSER_THREAD_CAP` / `--parser-thread-cap`, and added worker-side Python `gc.collect()` after every processed job. Updated runbook guidance for shared Docker hosts: use capped auto or fixed thread counts plus `--max-jobs`/container restart policy for long-running conversion loads.
- 2026-07-01: `venv/bin/python -m py_compile plant3d/parsers/ifc.py plant3d/management/commands/process_plant3d_job.py plant3d/tests.py`, `venv/bin/python manage.py check`, focused cgroup/cap/GC worker tests, and `USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1` passed after worker sizing and cleanup hardening. Plant3d suite: 52 tests.

## Platform Rules Discovered During Implementation

- Browser viewers should load render packages through stable platform API URLs, not direct storage keys. This preserves freedom to move from local/self-hosted storage to MinIO, Oracle Object Storage, S3, signed URLs, or CDN delivery later.
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
