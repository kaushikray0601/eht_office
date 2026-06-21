# Composite 3D Workspace Tracker - 2026-06-21

## Strategic Pivot

The `idfviewer` side app is pivoting from a single-file 3D viewer and EHT drawing concept tool into a composite 3D engineering workspace.

The intended final workflow is:

1. Import or reuse saved IDF/PCF pipeline isometrics.
2. Import or reuse IFC structural/model reference geometry.
3. Superimpose these files in one 3D workspace as independent layers.
4. Align files by coordinate system, units, offsets, rotation, and scale.
5. Link pipeline geometry to preliminary hot tracer and cold cable engineering data by primary key `line id`.
6. Use the manual 3D EHT authoring tools to validate, adjust, and complete layout engineering.
7. Add cable tray, trench, duct bank, routing nodes, and cable routes.
8. Move toward an integrated engineering output that connects hot engineering, cold engineering, physical routing, and construction metadata.

## Non-Negotiable Guardrails

**Do not disturb the existing EHT production code paths while developing this side workspace.**

Protected areas include:

- Hot/tracer engineering calculation logic and data.
- Cold cable engineering calculation logic and data.
- SLD generation, topology, reporting, and browser workspace.
- Existing production database schema/data unrelated to this side app.
- Existing vendor catalogue data and project engineering results.
- Current MVP release behavior outside the `idfviewer`/3D workstream unless explicitly requested.

All new work should be additive, scoped, reversible, and tested. New persistence should use new tables/models or clearly isolated `idfviewer` records unless an integration point is explicitly approved.

## Current Status

### Existing Main Application

- Hot/tracer engineering: mature MVP workstream exists; preliminary hot engineering outputs are assumed available by `line id`.
- Cold cable engineering: mature MVP workstream exists; preliminary cold cable outputs are assumed available by `line id`.
- SLD: existing SLD/topology/reporting workstream exists and must not be disrupted.
- Database: contains important current project/vendor/engineering data and must not be modified casually.

### Current `idfviewer` Capability

- IDF parser: custom parser exists for pipeline isometrics.
- PCF parser: custom block parser exists and extracts pipeline metadata/attributes.
- IFC parser: IfcOpenShell-backed preview parser exists and works for smaller IFC files.
- Saved file flow: IDF/PCF save/reload exists; IFC preview persistence remains a deferred design item.
- Viewer: Three.js scene renders pipes/fittings/welds/supports/markers/IFC mesh payloads.
- Coordinate basis: PCF reads coordinate units where available; IDF assumed mm; IFC assumed m.
- Measurement: snap-based measure tool exists with first-pass mismatch checks.
- EHT authoring: persistent `EHTDesignElement` layer exists for DB, JB, isolator, RTD, end termination, pipe strap, SR/MI tracer, and cold cable.
- EHT editing: direct drag, coordinate entry, axis locks, undo, route preview, connection warnings, and backend schema validation exist.
- Records: local records/audit/planning/tracking folders exist under `idfviewer/records`.

## Target Architecture Direction

### Core Concept

Introduce a "Composite 3D Workspace" that contains multiple imported/saved model layers:

- IDF layer(s)
- PCF layer(s)
- IFC layer(s)
- EHT design overlay layer(s)
- Future tray/trench/duct/routing layers

Each layer should have:

- Source file reference.
- Source format.
- Project scope.
- Visibility.
- Opacity.
- Color/tint override.
- Transform:
  - `offset_x`
  - `offset_y`
  - `offset_z`
  - `rotation_z`
  - `scale`
- Coordinate/unit metadata.
- Bounding box metadata.
- Optional display simplification/cached geometry metadata.

### First MVP Milestone

Build a composite workspace foundation:

1. Create a composite workspace record model.
2. Create a composite workspace layer record model.
3. Allow saved IDF/PCF/IFC files to be added to one workspace.
4. Render layers together in the viewer.
5. Add layer panel controls:
   - Show/hide.
   - Opacity.
   - Focus.
   - Color/tint.
   - Transform fields.
6. Store and apply per-layer transforms.
7. Keep the current single-file viewer route working.

### Second MVP Milestone

Add alignment tools:

1. Per-layer bounding boxes.
2. Coordinate/unit badges per layer.
3. Manual transform editing.
4. Two-point or three-point alignment planning.
5. Measured-distance verification across layers.

### Third MVP Milestone

Link preliminary engineering data:

1. Extract/normalize line id from IDF/PCF.
2. Map hot/tracer engineering output by `line id`.
3. Map cold cable engineering output by `line id`.
4. Display linked/missing/mismatch state in the viewer.
5. Use linked engineering data to suggest or pre-create EHT elements.

### Fourth MVP Milestone

Add route infrastructure authoring:

1. Cable tray segment.
2. Tray elbow/tee/riser.
3. Underground trench.
4. Duct bank.
5. Pull pit/manhole.
6. Penetration/sleeve.
7. Routing node/edge graph foundation.

### Fifth MVP Milestone

Route cold cables through tray/trench/duct:

1. Convert physical route infrastructure into a graph.
2. Route cables from DB/JB/isolator/end devices.
3. Validate route length.
4. Track capacity/fill.
5. Track construction notes and metadata.
6. Produce reports/export sheets.

## Immediate Work Plan

### Pass 0 - Architecture Discussion

Before coding the composite workspace, hold an architecture discussion and settle:

- Model names and ownership.
- Whether IFC persistence is required immediately or can remain preview/cache-only.
- Whether composite workspace should live inside `idfviewer` or be renamed later.
- How to add files to a workspace without duplicating saved geometry unnecessarily.
- How to represent layer transforms.
- How to handle coordinate systems and units.
- How to keep performance acceptable for larger IFC chunks.
- What tests are required before enabling user-facing composite workspaces.

### Pass 1 - Backend Foundation

- Add composite workspace/layer models.
- Add migrations isolated to `idfviewer`.
- Add basic CRUD/load APIs.
- Add tests for project scoping and layer transform persistence.

### Pass 2 - Viewer Foundation

- Add composite viewer route/template.
- Load multiple layer payloads into one scene.
- Apply per-layer transform.
- Add layer list UI with show/hide/focus/opacity.

### Pass 3 - Alignment Tools

- Add bounding boxes and coordinate badges.
- Add layer transform editing UI.
- Store transform updates.
- Add simple visual alignment aids.

### Pass 4 - Engineering Data Link

- Add line-id extraction/normalization review.
- Add read-only engineering data linking by `line id`.
- Display linked/missing/mismatch status.

## Risks

- Coordinate mismatch between IDF/PCF and IFC will be the largest technical risk.
- IFC files can still be heavy even when exported by structure.
- Browser rendering can degrade unless IFC geometry is simplified/cached/chunked.
- Adding persistence carelessly could affect production database stability.
- Current EHT overlay is useful but should not be confused with final cable-routing graph architecture.

## Open Questions

- Are IFC files from Tekla using plant global coordinates, local structure coordinates, or mixed project base points?
- Will IDF/PCF line ids always be available through existing attributes/metadata?
- Should composite workspace support one IFC plus many IDF/PCF files first, or many of each from day one?
- Should IFC saved persistence be designed now or deferred until after manual composite proof of concept?
- What is the minimum useful transform UI: numeric only, drag handles, two-point align, or all later?
- Where will preliminary hot/cold engineering data be exposed for read-only linking?

## Current Recommendation

Start with Pass 0 architecture discussion, then implement Pass 1/2 in small reversible increments.

Do not begin tray/trench/cable-routing graph work until composite layer loading and manual alignment are stable.

