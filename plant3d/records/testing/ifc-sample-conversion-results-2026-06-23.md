# IFC Sample Conversion Results

Date: 2026-06-23

Purpose: first real-file check of the `plant3d` source-to-render-package pipeline using local IFC samples under `ifc/`.

## Environment

- Project used for local spike records: `P1`
- Parser path at original measurement time: `idfviewer.ifc_parser.parse_multiple_ifc_uploads`
- Parser path after 2026-06-23 extraction pass: `plant3d.parsers.ifc.parse_multiple_ifc_uploads`
- Converter path: `plant3d.ifc-json`
- Runtime package: single-tile JSON debug package
- Storage: local/self-hosted media storage

## Results

| File | Source system | Source size | Objects | JSON tile size | Conversion time | Package ID |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `ifc/Ifc2s3_Duplex_Electrical.ifc` | Revit 2013 sample | 1,602,758 bytes | 104 | 1,510,791 bytes | 1,733 ms | 1 |
| `ifc/8-SSPAR-800203.ifc` | Tekla Structures 2024 SP2 | 2,815,485 bytes | 867 | 10,487,263 bytes | 17,375 ms | 2 |
| `ifc/8-SSPAR-800205B.ifc` | Tekla Structures 2024 SP2 | 4,767,500 bytes | 1,637 | 7,459,364 bytes | 10,031 ms | 3 |
| `ifc/8-SSPAR-800206A.ifc` | Tekla Structures 2024 SP2 | 9,402,996 bytes | 3,770 | not run as JSON in this pass | not run as JSON in this pass | - |

## Coordinate And Unit Notes

- The Revit sample is IFC2X3. Parser-level `IfcUnitAssignment` extraction reports source-declared length unit `ft` with scale `0.3048`.
- The Tekla samples are IFC2X3. Parser-level `IfcUnitAssignment` extraction reports source-declared length unit `mm` with scale `0.001`.
- Render geometry remains stored as `M` with `unit_confidence=ifcopenshell_geometry_si`; the IfcOpenShell geometry iterator reports `length-unit=1.0` and `convert-back-units=False`.
- This resolves the metadata ambiguity between source-declared units and render units, but final scale trust still needs a known-dimension or source-system validation before measurement, snapping, or cross-discipline federation are trusted.

Update after unit-hint pass:

- `plant3d` now extracts IFC header length-unit hints and carries them into metadata/package/tile/job records for new conversions.
- The extractor reports:
  - `Ifc2s3_Duplex_Electrical.ifc`: primary SI length unit `m`, plus conversion-based `FOOT`.
  - `8-SSPAR-800203.ifc`: primary SI length unit `mm`, plus conversion-based `FOOT`.
  - `8-SSPAR-800205B.ifc`: primary SI length unit `mm`, plus conversion-based `FOOT`.
- At that intermediate stage, non-metre or conversion-based declarations combined with parser `M / assumed` produced unit warnings. The later parser unit-extraction pass below supersedes the `assumed` label, but not the need for a final known-dimension proof.

Update after parser unit-extraction pass:

- `plant3d.parsers.ifc` now extracts declared length units from `IfcUnitAssignment` through IfcOpenShell model data.
- Direct parser checks reported:
  - `Ifc2s3_Duplex_Electrical.ifc`: declared `ft`, scale `0.3048`, render coordinate unit `M`.
  - `8-SSPAR-800203.ifc`: declared `mm`, scale `0.001`, render coordinate unit `M`.
  - `8-SSPAR-800205B.ifc`: declared `mm`, scale `0.001`, render coordinate unit `M`.
- Package/tile/job metadata now carries both source-declared unit evidence and render-unit evidence.

## First Observations

- The complete ingest/conversion/package/index path works with real IFC files.
- JSON expansion is visible already:
  - the 2.8 MB Tekla sample became a 10.5 MB JSON tile.
  - the 4.8 MB Tekla sample became a 7.5 MB JSON tile.
- Conversion time is acceptable for small samples, but the 2.8 MB Tekla sample already took about 17 seconds.
- The current package remains a single JSON tile, so these results do not prove EPC-scale tiling, streaming, or browser memory behavior.

## First GLB Package Results

Purpose: compare the new `plant3d.ifc-glb` package path against the JSON debug package. Each GLB package stores one binary `.glb` tile plus one JSON metadata sidecar.

| File | Objects | JSON tile size | GLB size | Sidecar size | GLB total | GLB conversion time | Package ID |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ifc/Ifc2s3_Duplex_Electrical.ifc` | 104 | 1,510,791 bytes | 560,296 bytes | 26,266 bytes | 586,562 bytes | not separately recorded in first shell print | 4 |
| `ifc/8-SSPAR-800203.ifc` | 867 | 10,487,263 bytes | 5,376,268 bytes | 167,948 bytes | 5,544,216 bytes | 17,546 ms | 5 |
| `ifc/8-SSPAR-800206A.ifc` | 3,770 | not run as JSON in this pass | 5,960,624 bytes | 1,269,630 bytes | 7,230,254 bytes | 20,717 ms | 6 |

Interpretation:

- GLB materially reduces runtime payload size versus the debug JSON package.
- IFC parsing/conversion time is still the dominant cost; GLB does not remove the need for proper async workers.
- The GLB package now carries `_FEATURE_ID_0` vertex attributes plus sidecar `object_features` / `object_spans`, but browser object picking for GLB is deliberately deferred until BVH/feature-ID selection is designed.
- Browser GLB rendering still needs a Playwright/manual GPU probe before performance is accepted.

## Spatial GLB Child-Tile Results

Purpose: measure the first spatial child-tiling path. New GLB conversions now emit a `tileset.json` plus one or more GLB child tiles and sidecars. At original measurement time the viewer still loaded all child tiles; the 2026-06-28 viewer pass added first active-tile streaming/culling.

| File | Objects | Child tiles | GLB bytes | Sidecar bytes | Tileset bytes | Package total | Conversion time | Package ID | Tile object counts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `ifc/Ifc2s3_Duplex_Electrical.ifc` | 104 | 1 | 623,712 | 43,073 | 2,207 | 668,992 | 1,639 ms | 21 | 104 |
| `ifc/8-SSPAR-800203.ifc` | 867 | 2 | 4,650,584 | 301,194 | 3,651 | 4,955,429 | 17,442 ms | 22 | 289, 578 |
| `ifc/8-SSPAR-800205B.ifc` | 1,637 | 4 | 2,608,284 | 570,185 | 5,422 | 3,183,891 | 10,410 ms | 23 | 440, 396, 521, 280 |
| `ifc/8-SSPAR-800206A.ifc` | 3,770 | 9 | 5,107,980 | 1,315,122 | 9,536 | 6,432,638 | 21,474 ms | 24 | 443, 315, 524, 315, 346, 636, 304, 332, 555 |

Interpretation:

- Spatial child tiles are now real package artifacts, not only a manifest placeholder.
- The current grouping target is about 500 objects per child tile; uneven object distribution is expected with the simple source-bounds grid.
- Package total includes GLB, sidecar, and tileset bytes. Sidecar bytes increase because each child tile carries its own feature/object mapping.
- Conversion time remains dominated by IfcOpenShell tessellation. Child tiling changes runtime package shape more than source parsing time.
- The next performance proof must come from browser/manual measurement of viewer-side culling/streaming, because conversion size/timing alone does not prove interactive runtime performance.

## Viewer Streaming Update

Date: 2026-06-28

The GLB viewer now prepares package-level tile state, frames the package from raw bounds before loading child GLBs, and streams active child tiles instead of eagerly fetching every child tile for larger packages. Current spike constants:

- Active loaded child-tile cap: 6
- Load batch size: 2 child tiles per streaming update
- Streaming update interval: 500 ms
- Small packages at or below the cap still load all child tiles for simplicity.

Runtime sidebar additions:

- loaded tiles / total tiles
- loading tiles
- streaming mode (`load-all` or `active-cap-6`)

Validation still required:

- Open package 24 or a fresh `8-SSPAR-800206A.ifc` GLB package in a logged-in browser session.
- Record whether loaded tiles stay below the total tile count during orbit/pan/zoom.
- Record FPS, draw calls, pick latency, metadata latency, and subjective orbit feel.
- If direct render-mesh picking feels slow, evaluate `three-mesh-bvh` next.

## Browser Probe After Viewer Streaming

Date: 2026-06-28

Method: temporary static probe page generated from real package 24 payloads, served on `127.0.0.1:9095`, checked with `plant3d/records/testing/browser_viewer_probe.py`. This bypassed Django login/session but used the real package JSON, GLB child tiles, sidecars, object metadata snapshots, and current `package_viewer.js`.

| Package | File | Child tiles | Loaded tiles after probe | Feature IDs loaded | Triangles loaded | FPS after orbit | Draw calls | Pick proxies | Screenshot non-background |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 24 | `ifc/8-SSPAR-800206A.ifc` | 9 | 6 | 2,468 | 123,620 | 60 | 19 | 0 | 6.86% |

Probe status:

`Loaded GLB package tile stream: 6/9 tile(s) loaded, 0 loading. Feature-ID picking enabled; BVH acceleration deferred.`

Interpretation:

- The streaming viewer path rendered a nonblank canvas for the largest current sample.
- The viewer loaded the active-tile cap of 6 child tiles, not all 9 child tiles.
- Headless browser FPS looked good in this static probe, but the result should still be manually confirmed in the logged-in Django viewer because desktop GPU, browser cache, network behavior, and subjective orbit feel matter.

Manual follow-up from KR:

- Logged-in manual testing reported a large loading-speed improvement after GLB child-tile streaming.
- Graphic quality did not visibly degrade.
- The remaining operational friction was that `venv/bin/python manage.py process_plant3d_job --all` had to be run manually and job progress jumped from an early low percentage to completion. The 2026-06-28 worker/progress pass addresses this with `process_plant3d_job --watch` plus staged job metrics/logs.
- Follow-up manual testing confirmed `process_plant3d_job --watch` works as intended: it waits for queued jobs, processes them as they arrive, then waits for the next job.
- Manual browser check on a later GLB package for `8-SSPAR-800201.ifc` reported no visible graphics degradation and normal existing functionality. Viewer sidebar metrics showed: 2,221 objects, 6/6 loaded tiles, 3,322,076 package bytes, 151 ms load time, 60 FPS, 24 draw calls, 24 GPU geometries, 118,640 triangles, 0 pick proxies, 13 ms metadata latency, and streaming mode `load-all`.
- Progress still jumps from an early staged value to completion for parse-heavy jobs. This is expected until the worker has deeper IfcOpenShell tessellation progress or a production progress channel; the current progress is stage-based, not true per-triangle/per-object streaming.
- Cross-browser repeat viewing can be fast even when the second browser has no browser cache because the expensive IFC conversion is already complete, render packages already exist, and the server/operating-system filesystem cache may serve GLB/media bytes from memory.
- Manual browser check after complete/review mode and zoom guardrails on source 23/package 51 (`8-SSPAU-800203.ifc`) confirmed the previous zoom/stale/white-canvas regression is fixed. The package reported 4,313 objects, 9/9 loaded tiles, 715,028 triangles, 36 draw calls, 16,050,726 package bytes, 361 ms viewer load time, 60 FPS, 5 ms pick latency, 27 ms metadata latency, and `review-complete` streaming.
- The same package conversion took 66,017 ms and reported `gltfpack_not_available`, so the current performance result is uncompressed GLB tile loading, not meshopt-compressed loading.
- GPU load is not expected during `Queue IFC GLB Conversion`; that path is server-side CPU/IO work through Django, IfcOpenShell, GLB packing, and optional external compression. GPU observations should be taken while the package viewer is open in Chrome/Edge, using WebGL renderer/frame-time metrics plus the browser process in system tools.

## Meshopt Hook And Numpy GLB Writer Update

Date: 2026-06-28

Implementation status:

- GLB conversion now has an optional `gltfpack`/meshopt hook.
- If `PLANT3D_GLTFPACK_BIN` is configured or `gltfpack` is on `PATH`, each GLB tile is passed through `gltfpack -cc` and compression input/output bytes are stored in tile sidecar, tile metadata, package metadata, and job metrics.
- If no `gltfpack` binary is available, conversion still succeeds and records compression status `skipped`.
- The Three.js viewer now registers `MeshoptDecoder`, so future `EXT_meshopt_compression` GLBs can load through the existing viewer path.
- `plant3d.glb` now uses numpy for normal generation, float packing, index packing, and position bounds.

Local measurement status:

- This workspace currently has numpy available but does not have `gltfpack`, `meshoptimizer`, `pygltflib`, or `trimesh` installed.
- Therefore this pass proves meshopt integration readiness and records skipped compression cleanly, but it does not yet provide a real meshopt compression ratio or browser decode-time measurement.
- Meshopt adoption is gated on correctness as well as size: compressed GLB output must preserve feature-ID picking and metadata resolution.
- Use `venv/bin/python manage.py measure_plant3d_package <package_id>` after conversion to record bytes, saved percent, output/input ratio, compression duration, and measured-vs-recorded byte drift.
- The converter now rejects unsafe compressed output by falling back to the original uncompressed GLB and recording `rejected_feature_id_validation` when `_FEATURE_ID_0` cannot be validated against the sidecar feature counts.

## Manual Viewer Check

Use the source/package records created in the local development database:

- Package 1: Revit electrical sample
- Package 2: Tekla `8-SSPAR-800203`
- Package 3: Tekla `8-SSPAR-800205B`

If project access blocks these package URLs for the current browser user, upload the same files through `/plant3d/sources/upload/` while logged in as a user assigned to the target managed project, then process queued jobs with:

```bash
venv/bin/python manage.py process_plant3d_job --watch
```

Record from the viewer sidebar:

- load time
- FPS during orbit/pan/zoom
- draw calls
- render batches
- pick proxies
- triangle count
- pick latency
- metadata latency
- visible jitter or orbit instability

## Browser Probe Results

Method: temporary static probe page using the real package JSON/tile payload and current `plant3d/static/plant3d/js/package_viewer.js`, served locally on `127.0.0.1:9095`, checked with headless Chromium/Playwright. The probe performs a small orbit drag and checks screenshot pixels for a nonblank canvas.

| Package | File | Load time | FPS after orbit | Draw calls | Render batches | Pick proxies | Triangles | Screenshot non-background |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `Ifc2s3_Duplex_Electrical.ifc` | 88 ms | 59 | 1 | 1 | 104 | 29,926 | 7.91% |
| 2 | `8-SSPAR-800203.ifc` | 185 ms | 15 | 4 | 4 | 867 | 230,480 | 2.54% |
| 3 | `8-SSPAR-800205B.ifc` | 149 ms | 17 | 5 | 4 | 1,637 | 124,904 | 17.24% |

Interpretation:

- The viewer rendered nonblank canvases for all three real converted packages.
- Merged color-bucket rendering kept visible draw calls low.
- The two Tekla samples failed the 30 FPS target in headless Chromium, despite low draw calls.
- The likely remaining costs are geometry volume, software/headless rendering overhead, JSON parse/build work, and the temporary hidden pick-proxy strategy.
- This is a warning signal, not a final GPU verdict. Repeat on a normal browser/GPU workstation before deciding renderer viability.

## Next Technical Risks

- Prove geometry scale with a known dimension or source-system benchmark, rather than relying only on IfcOpenShell geometry settings.
- Compare header unit hints against known dimensions or source-system exported coordinates to prove whether IfcOpenShell is returning SI-normalized geometry.
- Move beyond JSON if larger sample payloads show high parse time or browser memory pressure.
- Browser-test the GLB package path and compare FPS/draw calls/load time against JSON.
- Design feature/object picking for GLB/binary packages without duplicating hidden per-object geometry.
- Implement real tile/chunk manifests before treating RTC and streaming as solved.
- Refactor the copied parser when needed; the runtime dependency on `idfviewer` has been removed.
- Reduce or replace hidden pick-proxy geometry before larger samples; visible draw calls are low, but browser FPS is still below target on Tekla samples in the headless probe.
