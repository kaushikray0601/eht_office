# Cable Tray Authoring Framework

Date: 2026-07-02

Status: planning framework; do not implement persistence in `plant3d` core

## Intent

Add cable tray and support authoring on top of the neutral `plant3d` viewer without turning `plant3d` into an EHT-only application.

The viewer should provide generic 3D anchors, measurement, snapping, and drawing surfaces. Cable tray engineering data should belong to an electrical/EHT integration layer that references `plant3d` source/package/object anchors.

## First User Workflow

1. Load a plant/structure model.
2. Optionally import a 2D plot plan image onto the helper grid for spatial correlation.
3. Choose a cable tray route tool.
4. Pick tray route points on structure, grid, or snapped model vertices.
5. Select tray type and size.
6. Add supports along the route using spacing rules.
7. Edit tray/support parameters from the properties panel.
8. Review clearances, approximate length, support count, and route warnings.
9. Save the tray layer through the future EHT/electrical integration backend.

## Candidate Features

- Tray route tools: ladder tray, perforated tray, channel tray, conduit bank.
- Tray geometry preview: rectangular tray corridor/tube while drafting, with width/depth based on selected tray size.
- Support tools: wall bracket, cantilever, trapeze, post support.
- Automatic support placement: user-defined spacing, max span, support at bends/endpoints.
- Snap targets: model vertex, picked face point, grid point, existing tray node, existing support node.
- Measurement: point-to-point now exists; plane-distance is a future extension.
- 2D plot-plan overlay: currently browser-local; should later persist in the integration layer with transform metadata.
- Clash/clearance checks: future, after tray geometry is persistent.

## Plane-Distance Measurement Option

Feasible, but it should be a separate focused pass.

Minimum implementation:

- Let user define a measurement plane from one of:
  - picked face normal,
  - world XY/XZ/YZ plane,
  - three picked points,
  - selected object bounding face.
- Let user pick a point or vertex.
- Compute perpendicular distance from point to plane.
- Draw plane ghost, projected point, and distance line.

Estimated effort: one medium pass for axis-plane/picked-face plane distance; one larger pass for robust three-point planes plus persistence/reporting.

## Architecture Boundary

`plant3d` may own:

- viewer surface,
- generic drawing/snapping helpers,
- source/package/object anchors,
- generic local draft primitives while editing.

The electrical/EHT integration layer should own:

- tray route records,
- support records,
- cable tray catalog parameters,
- EHT/electrical metadata,
- persistence APIs,
- export/report semantics.

## Suggested Sequencing

1. Stabilize current draft tools: snap, move, delete, parameter editing.
2. Add tray route draft tool with visible geometry and editable width/depth.
3. Add support draft tool with placement on tray/structure.
4. Add automatic support spacing preview.
5. Add EHT/electrical integration persistence outside `plant3d`.
6. Add clearance/clash checks once tray/support data is persistent.
