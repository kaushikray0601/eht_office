# plant3d Pipeline Spike Tracker

Date: 2026-06-22

Status: ready for execution planning

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
- [ ] Evaluate meshopt compression feasibility if setup cost is reasonable.
- [x] Record metadata-manifest output size.
- [x] Record sample-file geometry conversion time and output size.
- [x] Record extracted units, bounds, object count, and coordinate frame assumptions for available samples.
- [x] Add IFC header length-unit hint extraction and propagate unit warnings into metadata/package/tile/job records for new conversions.
- [x] Extract IFC `IfcUnitAssignment` declared length units through the plant3d parser and store render-unit-vs-source-unit evidence in package/tile/job metadata.
- [ ] Repeat conversion metrics against the target 20 MB real project IFC.

## Phase 4 - Tiling And Precision Experiment

- [ ] Create a tiled or chunked package manifest.
- [x] Define glTF axis convention before expanding GLB output: GLB buffers use current `render_xyz_m` frame, source Z is emitted as glTF/Three.js Y-up, and no additional root transform is applied.
- [x] Start a primitive 3D-Tiles-style `tileset.json` manifest after feature IDs are in the single-tile GLB.
- [x] Split GLB output into first spatial child tiles under the `tileset.json` root.
- [ ] Add viewer-side tile culling/streaming so child tiles are not all loaded at once.
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
- [ ] Browser memory use where measurable.
- [x] FPS during orbit/pan/zoom.
- [x] Selection/picking latency.
- [ ] Metadata lookup latency.
- [ ] Visual stability at real coordinates.
- [ ] Snapping/measurement stability where tested.

Measurement hooks now implemented:

- [x] Conversion jobs record `conversion_duration_ms` in job metrics.
- [x] Source detail page surfaces job metrics after processing.
- [x] Viewer sidebar reports draw calls and rough FPS during orbit/pan/zoom.
- [x] Viewer sidebar reports WebGL geometry and texture counts.
- [x] Viewer sidebar reports effective pixel ratio and adaptive quality mode.
- [x] Viewer sidebar reports render batch count, pick proxy count, pick latency, and metadata lookup latency.

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

- [ ] Summarize whether Three.js-first remains acceptable.
- [ ] Summarize whether Babylon.js comparison is needed.
- [ ] Summarize whether GLB/glTF is enough or tiled/custom packages are mandatory.
- [ ] Summarize whether first available IFC samples are sufficient or larger EPC files are required.
- [ ] Recommend production model shape after spike.
- [ ] Recommend next implementation pass.

## Current Risks

- 20 MB IFC is useful but may be too small to prove EPC-scale viability.
- Public sample IFC files may not represent plant-global coordinates.
- IfcOpenShell conversion may be slow or heavy for large files.
- Naive Three.js object-per-mesh rendering will not scale.
- Coordinate precision problems may not show unless source files use large coordinates.
- Browser memory and draw calls can become the limiting factor before triangle count.
- Conversion now runs off-request through a management-command worker for the spike. Full Celery/RQ/SSE infrastructure is still required before user-facing or long-running production workflows.
- The IFC parser is now copied under `plant3d/parsers/`, closing the immediate platform-boundary dependency on `idfviewer`. Future parser refactor/shared ownership is still possible.
- Package/tile JSON is still served through Django. This is acceptable for the spike but must move toward signed object-storage URLs before real-scale use.
- First GLB package output is now available and is materially smaller than JSON on the tested samples, but still served through Django during the spike.
- Claude's render-format research confirms the next serious stack direction: GLB + meshopt + GPU instancing + feature IDs, arranged by a 3D-Tiles-style manifest and rendered in Three.js with `3d-tiles-renderer` / `three-mesh-bvh` where needed. The current GLB pass is a smoke-test step, not the final runtime format.
- RTC metadata is now frame-correct for the current single-tile JSON package, but real per-tile origins are still unproven until actual spatial tiling begins.
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
- Production package format remains partially deferred: first GLB+sidecar path exists, but compression, tiling, feature IDs, and 3D Tiles-style manifests remain open.
- GLB feature IDs are now present in the first binary package path via `_FEATURE_ID_0` plus sidecar object-feature mapping. The viewer can now click GLB render meshes and resolve feature ID -> stable ID -> `ModelObject` metadata without hidden per-object proxies. BVH acceleration and shader/feature-ID highlighting are still deferred.
- Unit/scale proof remains partially deferred: IFC `IfcUnitAssignment` and IfcOpenShell geometry settings are visible now, but we still need a known-dimension or source-system validation to confirm rendered geometry scale end-to-end.
- Parser cleanup remains a TODO: the extracted parser is a direct copy for boundary safety, not yet a deeply refactored production parser.

## Immediate Next Actions

1. Queue fresh GLB conversions for the Tekla samples and record actual tile counts/package sizes under the new spatial child-tiling path.
2. Re-run browser GLB viewer checks after spatial child tiling and record whether loading all child tiles still feels acceptable.
3. Add viewer-side tile culling/streaming so child tiles are not all fetched/rendered at once.
4. Add the known-dimension unit validation fixture to close F4 when practical.
5. Evaluate `three-mesh-bvh` acceleration for GLB picking if direct render-mesh raycast is sluggish on the larger samples.
6. Gather the real 20 MB and/or plant-global IFC input when available.
7. Keep production EHT, cold cable, SLD, and `idfviewer` behavior unchanged.

Current manual check path:

1. Upload one available local sample IFC from `ifc/` through `/plant3d/sources/upload/`.
2. Run metadata conversion through the source detail page or POST endpoint.
3. Process the queued job with `venv/bin/python manage.py process_plant3d_job <job_id>` or `venv/bin/python manage.py process_plant3d_job --next`.
4. Run IFC JSON debug conversion and process the queued job.
5. Queue the IFC GLB conversion and process that queued job.
6. Open both package viewers and compare package size/load behavior.

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
- A single-root `tileset.json` is an architecture contract, not yet a performance feature. Real performance benefit begins when the root is split into spatial child GLB tiles and the viewer can stream/cull them.
- Feature IDs in GLB must stay glTF-conformant before meshopt/gltfpack work begins. Use `FLOAT` or the future standard feature metadata extension, not `UNSIGNED_INT` vertex attributes.
- GLB sidecar stable IDs and `ModelObject.stable_id` must be generated by the same resolver. Otherwise GUID-less IFC objects and future IDF/PCF objects will render but fail pick-to-metadata.
- Spatial child tiles now exist in the package, but the current viewer still fetches and renders all child tiles. This proves the package shape and tile-local RTC, not final streaming performance.
- Local spike DB cleanup through Django admin is acceptable, but storage cleanup needs an explicit tool/command. Otherwise media blobs under `MEDIA_ROOT/plant3d` will become orphaned.
- Spike UX should expose the exact worker command and poll job status from the source page so manual IFC testing does not depend on raw JSON pages or repeated full-page refreshes.
- A queued job is not a failed conversion. In the current spike, no package/view link appears until `process_plant3d_job` runs and the source page sees the completed job.
- Browser verification should distinguish nonblank render success from performance success. The current real-sample probe renders correctly, but Tekla FPS is below target.
- Source-declared IFC units and render geometry units are different facts. Store both: source unit from `IfcUnitAssignment`, render unit from parser/IfcOpenShell geometry settings, and only mark measurement scale trusted after a known-dimension validation.

## Manual Testing Checklist

When an IFC sample is available, test manually:

1. Log in as a user assigned to the target managed project.
2. Open `/plant3d/sources/upload/`.
3. Upload an IFC file and confirm it redirects to the source detail page.
4. Queue metadata conversion and confirm JSON response shows `status: queued`.
5. Note the queued job ID and run `venv/bin/python manage.py process_plant3d_job <job_id>` or `venv/bin/python manage.py process_plant3d_job --all`.
6. Refresh the source detail page and confirm a metadata package appears.
7. Run IFC geometry conversion and confirm JSON response shows `status: queued`.
8. Process that queued job with `venv/bin/python manage.py process_plant3d_job <job_id>` or `venv/bin/python manage.py process_plant3d_job --all`.
9. Queue and process IFC GLB conversion for the same source.
10. Refresh the source detail page and open both JSON and GLB package viewer links.
11. Confirm each model appears, can orbit/pan/zoom, and shows load status.
12. Record conversion duration from the source detail job metrics.
13. Record viewer load time, rough FPS, draw calls, render batches, pick proxies, triangles, mesh count, pixel ratio, quality mode, tile origin, pick latency, metadata latency, and visible jitter from the viewer sidebar.
14. For GLB packages, click a visible object and confirm the selected-object panel resolves a feature ID to indexed metadata; record pick latency and any sluggishness.
15. Log in as a user not assigned to that project and confirm source/package/tile URLs return 404.

## Claude Research / Review Asks

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
