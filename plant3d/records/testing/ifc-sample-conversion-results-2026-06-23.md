# IFC Sample Conversion Results

Date: 2026-06-23

Purpose: first real-file check of the `plant3d` source-to-render-package pipeline using local IFC samples under `ifc/`.

## Environment

- Project used for local spike records: `P1`
- Parser path: current `idfviewer.ifc_parser.parse_multiple_ifc_uploads`
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

- The Revit sample header is IFC2X3 and includes metre SI units plus foot conversion units.
- The Tekla samples are IFC2X3 and declare millimetre SI length units in the header.
- The current parser reports geometry package unit as `M` with `unit_confidence=assumed`.
- This may be correct if IfcOpenShell is already returning SI-normalized vertices, but it is not proven yet.
- Unit extraction and scale verification must be treated as an open spike risk before measurement, snapping, or cross-discipline federation are trusted.

Update after unit-hint pass:

- `plant3d` now extracts IFC header length-unit hints and carries them into metadata/package/tile/job records for new conversions.
- The extractor reports:
  - `Ifc2s3_Duplex_Electrical.ifc`: primary SI length unit `m`, plus conversion-based `FOOT`.
  - `8-SSPAR-800203.ifc`: primary SI length unit `mm`, plus conversion-based `FOOT`.
  - `8-SSPAR-800205B.ifc`: primary SI length unit `mm`, plus conversion-based `FOOT`.
- For non-metre or conversion-based declarations combined with parser `M / assumed`, new conversions now include unit warnings. This is a visibility improvement, not a final proof of coordinate scale.

## First Observations

- The complete ingest/conversion/package/index path works with real IFC files.
- JSON expansion is visible already:
  - the 2.8 MB Tekla sample became a 10.5 MB JSON tile.
  - the 4.8 MB Tekla sample became a 7.5 MB JSON tile.
- Conversion time is acceptable for small samples, but the 2.8 MB Tekla sample already took about 17 seconds.
- The current package remains a single JSON tile, so these results do not prove EPC-scale tiling, streaming, or browser memory behavior.

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

- Verify IFC units and geometry scale rather than relying on `M / assumed`.
- Compare header unit hints against known dimensions or source-system exported coordinates to prove whether IfcOpenShell is returning SI-normalized geometry.
- Move beyond JSON if larger sample payloads show high parse time or browser memory pressure.
- Implement real tile/chunk manifests before treating RTC and streaming as solved.
- Extract or neutralize the parser dependency on `idfviewer` after this first measurement round.
- Reduce or replace hidden pick-proxy geometry before larger samples; visible draw calls are low, but browser FPS is still below target on Tekla samples in the headless probe.
