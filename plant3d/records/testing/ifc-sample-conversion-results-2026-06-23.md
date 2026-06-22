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

Interpretation:

- GLB materially reduces runtime payload size versus the debug JSON package.
- IFC parsing/conversion time is still the dominant cost; GLB does not remove the need for proper async workers.
- The GLB sidecar carries object spans and metadata, but browser object picking for GLB is deliberately deferred until feature IDs / binary picking strategy are designed.
- Browser GLB rendering still needs a Playwright/manual GPU probe before performance is accepted.

## Manual Viewer Check

Use the source/package records created in the local development database:

- Package 1: Revit electrical sample
- Package 2: Tekla `8-SSPAR-800203`
- Package 3: Tekla `8-SSPAR-800205B`

If project access blocks these package URLs for the current browser user, upload the same files through `/plant3d/sources/upload/` while logged in as a user assigned to the target managed project, then process queued jobs with:

```bash
venv/bin/python manage.py process_plant3d_job --all
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
