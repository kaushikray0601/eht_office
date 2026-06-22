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
- [x] Produce first JSON geometry runtime package from stored IFC source blobs.
- [x] Record IFC geometry conversion job, package, tile, mesh count, byte size, and object index metadata.
- [x] Add package/tile JSON API URLs so the browser does not depend on storage-key details.
- [x] Wrap conversion package/tile/object-index writes in database transactions.
- [x] Keep queued -> running -> completed/failed state transitions real for management-command processing.
- [x] Run the IFC geometry conversion against real project/sample IFC files and record actual metrics.
- [ ] Evaluate GLB/glTF output path.
- [ ] Evaluate mesh compression feasibility if setup cost is reasonable.
- [x] Record metadata-manifest output size.
- [x] Record sample-file geometry conversion time and output size.
- [x] Record extracted units, bounds, object count, and coordinate frame assumptions for available samples.
- [x] Add IFC header length-unit hint extraction and propagate unit warnings into metadata/package/tile/job records for new conversions.
- [ ] Repeat conversion metrics against the target 20 MB real project IFC.

## Phase 4 - Tiling And Precision Experiment

- [ ] Create a tiled or chunked package manifest.
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
- [x] Show basic runtime metrics: loaded meshes, triangles, tiles, load time, package bytes, raw bounds.
- [x] Show tile RTC origin in runtime metrics.
- [x] Show live browser-side FPS, draw calls, and WebGL geometry/texture counters.
- [x] Render merged color-bucket geometry rather than one visible mesh per object for the JSON debug viewer.
- [x] Keep per-object pick proxies outside the rendered scene so metadata picking still works with merged visible geometry.
- [x] Show basic model/package bounds in the viewer sidebar.
- [x] Add basic object picking and highlight in the viewer.
- [x] Add minimal metadata panel backed by `ModelObject` API.
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
- `plant3d` still imports the prototype `idfviewer` IFC parser. Parser extraction into `plant3d/parsers/` or a neutral shared module remains a deliberate follow-up.
- Package/tile JSON is still served through Django. This is acceptable for the spike but must move toward signed object-storage URLs before real-scale use.
- RTC metadata is now frame-correct for the current single-tile JSON package, but real per-tile origins are still unproven until actual spatial tiling begins.
- The debug viewer now reduces visible draw calls by merging geometry by color, but object picking currently keeps per-object geometry proxies in memory. This is acceptable for the spike but not a final large-model strategy.
- Source-detail job polling is a practical spike bridge, not the final progress architecture. Production still needs a real worker process plus SSE/WebSocket or push-style progress.
- Real sample conversion exposed a unit-confidence risk: parser packages report `M / assumed` while IFC headers may declare millimetre or conversion-based foot units. Header hints are now extracted for new conversions, but explicit scale validation is still required before trusting measurements or federation.
- JSON expansion is already visible on small samples; one 2.8 MB Tekla IFC produced a 10.5 MB JSON tile.
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
- D3 remains deferred: extract the parser from `idfviewer` after the current real-sample/browser measurement loop.
- Production delivery remains deferred: package/tile payloads should move from Django JSON responses to signed object-storage URLs before real scale.
- Production package format remains deferred: evaluate GLB/glTF, 3D Tiles style manifests, meshopt, or custom binary chunks before expanding the JSON path.
- Unit/scale proof remains deferred: header hints are visible now, but we still need a known-dimension or source-system validation to confirm rendered geometry scale.

## Immediate Next Actions

1. Gather the real 20 MB IFC input when available.
2. Upload one available local sample IFC from `ifc/` through `/plant3d/sources/upload/`.
3. Run metadata conversion through the source detail page or POST endpoint.
4. Process the queued job with `venv/bin/python manage.py process_plant3d_job <job_id>` or `venv/bin/python manage.py process_plant3d_job --next`.
5. Run IFC geometry conversion through the source detail page or POST endpoint.
6. Process that queued job with the same management command.
7. Open the resulting package viewer and record load behavior.
8. Keep production EHT, cold cable, SLD, and `idfviewer` behavior unchanged.

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

## Platform Rules Discovered During Implementation

- Browser viewers should load render packages through stable platform API URLs, not direct storage keys. This preserves freedom to move from local/self-hosted storage to MinIO, Oracle Object Storage, S3, signed URLs, or CDN delivery later.
- The current JSON geometry viewer is useful for proving flow and debugging, but it is not the final large-model runtime format.
- Browser verification should include a real converted package, not only mocked API tests.
- Access checks must be applied at source, package, and tile levels because package/tile IDs are enough to expose cross-project data if left unscoped.
- Conversion writes must be transactional so a failed package/index rebuild does not destroy the previous object index.
- Object picking should fetch metadata from the indexed `ModelObject` API rather than depending only on tile JSON properties.
- Manual viewer testing is now useful after a real IFC is uploaded and processed because the viewer shows runtime metrics and selected-object metadata.
- RTC origin should be visible in package/tile APIs and viewer metrics so large-coordinate behavior can be inspected during real IFC tests.
- Coordinate metadata must name its frame explicitly. A stored RTC origin is only useful if it is in the same frame as the geometry vertices and can reconstruct source/world coordinates with a tested formula.
- Measurement should be built into the spike UI and job records from the start; otherwise real-file testing will produce subjective impressions instead of architecture evidence.
- Merged visible geometry and per-object pick proxies are a useful bridge for the JSON debug viewer, but the production format should move picking IDs/feature metadata into the render package rather than duplicating geometry in browser memory.
- Spike UX should expose the exact worker command and poll job status from the source page so manual IFC testing does not depend on raw JSON pages or repeated full-page refreshes.
- Browser verification should distinguish nonblank render success from performance success. The current real-sample probe renders correctly, but Tekla FPS is below target.

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
9. Refresh the source detail page and open the package viewer link.
10. Confirm the model appears, can orbit/pan/zoom, and shows load status.
11. Record conversion duration from the source detail job metrics.
12. Record viewer load time, rough FPS, draw calls, render batches, pick proxies, triangles, mesh count, tile origin, pick latency, metadata latency, and visible jitter from the viewer sidebar.
13. Log in as a user not assigned to that project and confirm source/package/tile URLs return 404.

## Claude Research / Review Asks

- Research and recommend the next runtime package format after the JSON spike:
  - GLB/glTF with metadata sidecar
  - 3D Tiles style manifests
  - meshopt-compressed glTF
  - custom binary tile chunks
- Review whether Three.js JSON loading should be kept only as a debug path once GLB/tiling begins.
- Review the merged-visible-geometry plus hidden-pick-proxy strategy and recommend the production picking approach for GLB/binary tiles.
- Recommend measurable thresholds for when JSON payload size becomes unacceptable and we must move to GLB/binary tiles.
- Independently review API delivery strategy: direct platform JSON API now versus signed object-storage URLs later.
- Review the right timing and minimal implementation for moving inline conversion to queued worker/SSE progress.
- Review whether parser extraction from `idfviewer` should happen before real-file metrics or immediately after.
- Review IFC unit handling: confirm whether IfcOpenShell vertices are already SI-normalized in our parser path, and recommend how to store source units versus render units for measurement/federation.
- Review the headless-browser FPS result: determine whether low FPS is mainly software/headless rendering, hidden pick proxies, JSON geometry shape, or a renderer/package issue.
- Recommend a practical scale-validation fixture: known IFC dimension, source-system benchmark, or synthetic IFC that proves header units versus rendered coordinates.
