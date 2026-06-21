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
- [ ] Decide whether to create a minimal Django app skeleton now or after Claude final review.
- [ ] Decide provisional app label/name for code: `plant3d` unless changed.

## Phase 1 - Spike Inputs

- [ ] Collect one real project IFC around 20 MB.
- [ ] Collect public/sample IFC files.
- [ ] Record source file provenance, expected units, source system if known, and rough model content.
- [ ] Add one IDF or PCF sample later for federation checks.
- [ ] Identify whether any available IFC has large plant/global coordinates.

## Phase 2 - Minimal Platform Skeleton

- [ ] Create neutral Django app/bounded context.
- [ ] Add minimal records/models only if needed for the spike:
  - `SourceModel`
  - `ConversionJob`
  - `RenderPackage`
  - `RenderTile`
  - optional early `ModelObject`
- [ ] Keep schema narrow and reversible.
- [ ] Add tests for model creation, job status, and package/tile metadata if models are created.

## Phase 3 - Conversion Experiment

- [ ] Test current Python/IfcOpenShell conversion path.
- [ ] Produce first browser-friendly runtime package.
- [ ] Evaluate GLB/glTF output path.
- [ ] Evaluate mesh compression feasibility if setup cost is reasonable.
- [ ] Record conversion time and output size.
- [ ] Record extracted units, bounds, object count, and coordinate frame assumptions.

## Phase 4 - Tiling And Precision Experiment

- [ ] Create a tiled or chunked package manifest.
- [ ] Add tile-local origin/RTC metadata.
- [ ] Store geometry coordinates relative to tile origin.
- [ ] Test whether large coordinates create visible jitter without RTC.
- [ ] Test whether RTC/tile-local rendering improves measurement and orbit stability.

## Phase 5 - Browser Viewer Spike

- [ ] Build a minimal Three.js viewer for the spike package.
- [ ] Load package/tile manifest.
- [ ] Render batched/merged geometry rather than per-object meshes.
- [ ] Show basic model bounds.
- [ ] Add basic object picking or object-id lookup if feasible.
- [ ] Add minimal metadata panel if object index exists.
- [ ] Avoid polishing UI beyond what is needed to measure the pipeline.

## Phase 6 - Measurement And Acceptance Metrics

Record at minimum:

- [ ] Source file size.
- [ ] Conversion time.
- [ ] Runtime package size.
- [ ] Browser load time.
- [ ] Draw call count.
- [ ] Browser memory use where measurable.
- [ ] FPS during orbit/pan/zoom.
- [ ] Selection/picking latency.
- [ ] Metadata lookup latency.
- [ ] Visual stability at real coordinates.
- [ ] Snapping/measurement stability where tested.

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

## Immediate Next Actions

1. Ask Claude for final review of the frozen architecture candidate.
2. Confirm app name `plant3d` or choose a different neutral name.
3. Gather the real IFC and sample IFC inputs.
4. Decide whether the first spike is script-first or minimal-Django-app-backed.
5. Start implementation only after the final architecture review is accepted.

