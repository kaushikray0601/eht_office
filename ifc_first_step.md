# IFC First Step

## Decision

This repo now starts IFC support with a backend-first approach using `IfcOpenShell`.

The goal of this first slice is to keep IFC aligned with the current Django + static Three.js architecture while avoiding premature large-model persistence decisions.

## Scope In This Pass

- Detect `.ifc` uploads in the existing `idfviewer` flow
- Parse IFC geometry and metadata on the backend with `IfcOpenShell`
- Render IFC objects in the existing viewer as selectable mesh geometry
- Surface IFC metadata in the right-side properties panel
- Keep IFC in preview mode only for now

## Why IFC Save Is Deliberately Deferred

The current save model is built around lightweight component rows with point/segment geometry in JSON.

That is acceptable for IDF and PCF, but not a good long-term storage shape for IFC triangulation because:

- IFC geometry payloads get large very quickly
- raw mesh JSON in the current component table will become brittle and expensive
- production IFC needs a dedicated backend strategy for geometry caching, metadata indexing, and model revisioning

## What The First IFC Parser Extracts

- element class, name, object type, predefined type, tag, GlobalId
- spatial containment path
- materials
- property sets
- quantities
- normalized triangle mesh data for preview rendering

## Current Limitation

`IfcOpenShell` is not yet installed in this environment, so IFC upload support is coded but requires dependency installation before real parsing can run.

## Likely Next Steps

1. Install and verify `IfcOpenShell` against the sample Tekla IFC.
2. Add a proper IFC import model instead of reusing the lightweight component-save path.
3. Decide whether heavy geometry stays in JSON, GLB, cached mesh blobs, or a viewer-oriented conversion format.
4. Add class filters and better hierarchy grouping for structural/reference models.
5. Evaluate xeokit later if browser-side IFC model scale outgrows the current Three.js viewer.
