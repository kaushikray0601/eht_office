# Codex Prompt - Composite 3D Workspace Development Start

You are Codex working in `/home/kr/mydev/eht_office`, a Django-based electrical heat tracing engineering application.

## Absolute Caution

**DO NOT TAMPER WITH OR BREAK THE EXISTING PRODUCTION EHT APPLICATION.**

The existing codebase contains important hot/tracer engineering, cold cable engineering, SLD generation, vendor catalogue logic, project data, and existing database records. These are already in MVP/final-release territory.

You must not casually modify:

- Hot/tracer engineering calculation logic.
- Cold cable engineering calculation logic.
- SLD generation, SLD topology, SLD reporting, or existing SLD browser workspace behavior.
- Existing vendor catalogue data.
- Existing project engineering result data.
- Existing production database tables outside the clearly scoped `idfviewer`/3D workstream.

If a future integration needs to touch those areas, stop first, explain the need, and make an explicit plan. Prefer read-only integration and additive isolated models until approved.

## Collaboration Model

The user wants Codex to implement carefully and progressively. Claude is the architect/auditor/reviewer. Codex should not rush into broad refactors.

For the first pass in the new chat, do **not** immediately code the composite workspace. Start with an architecture discussion and a proposed execution plan. Then implement only after the plan is accepted.

## Current Project Context

The main app performs electrical heat tracing design. It has mature workstreams for:

- Hot/tracer engineering.
- Cold cable engineering.
- SLD generation and topology.
- Existing database-backed project/vendor/result data.

The `idfviewer` side app started as an IDF-only viewer and has expanded into a 3D engineering concept workspace.

Current `idfviewer` status:

- Custom IDF parser exists.
- Custom PCF parser exists.
- IFC parser exists using IfcOpenShell-backed preview parsing.
- IDF/PCF saved-file flow exists.
- IFC preview works for smaller IFC files, but long-term IFC persistence/caching remains a design question.
- Three.js viewer renders pipeline and IFC geometry.
- Coordinate/unit handling exists:
  - PCF reads `UNITS-CO-ORDS` when present.
  - IDF currently assumes millimetres.
  - IFC currently assumes metres.
- Measurement tool exists with snap preview and first mismatch checks.
- EHT manual authoring exists:
  - `EHTDesignElement` model.
  - Backend-owned EHT tool catalogue in `idfviewer/eht_tools.py`.
  - API `/idfviewer/projects/<project_id>/eht-elements/`.
  - Point elements: Distribution Board, Junction Box, Isolator, RTD, End Termination, Pipe Strap.
  - Route elements: SR Tracer, MI Tracer, Cold Cable.
  - Direct drag, coordinate entry, X/Y/Z movement locks, undo stack, route placement, connection warnings.
- Local records exist under `idfviewer/records`.

Important existing records to read first:

- `idfviewer/records/README.md`
- `idfviewer/records/tracking/progress-2026-06-18.md`
- `idfviewer/records/tracking/composite-workspace-tracker-2026-06-21.md`
- `idfviewer/records/decisions/0001-app-name.md`
- `idfviewer/records/decisions/0002-coordinate-units-and-grid-scale.md`
- `idfviewer/records/planning/baseline-2026-06-18.md`

## Big-Picture Goal

Build a composite 3D engineering workspace where the user can:

1. Load/superimpose multiple IDF, PCF, and IFC files.
2. Treat each file as a separate 3D layer.
3. Align those layers by transform controls:
   - X/Y/Z offset.
   - Z rotation.
   - Scale.
   - Future two-point/three-point alignment.
4. Link preliminary hot/tracer and cold cable engineering data by primary key `line id`.
5. Use the 3D EHT drawing tools to validate and complete layout engineering.
6. Later add tray, trench, duct bank, and cable-routing graph tools.

The end goal is not just a viewer. The end goal is a 3D engineering workspace that links:

- Pipeline geometry from IDF/PCF.
- Civil/structural model geometry from IFC.
- Hot/tracer engineering data.
- Cold cable engineering data.
- Manual/assisted EHT layout.
- Future cable tray/trench/duct routing.

## User's Current Thinking

The user believes:

- PDMS may produce IDF.
- SP3D/E3D may produce PCF.
- IFC may come from Tekla/civil structure exports.
- IFC structure-by-structure exports may be more browser-friendly than a full Navisworks-scale plant model.
- IFC parsing is attractive because IfcOpenShell is available.
- The immediate tangible next work is superimposing IDF/PCF and IFC in one workspace.
- Later work should add cable tray, underground trench, duct bank, and cable routing.

Your interpretation:

- The IFC direction is reasonable, but IFC is not automatically light. Treat IFC as source/import format, but plan for cached/simplified viewer payloads.
- Coordinate alignment is the biggest risk.
- The next real milestone is a composite workspace with layer transforms, not tray routing yet.

## Recommended First Discussion

Start the new chat by proposing and discussing this architecture:

### Data Model Concepts

Potential new `idfviewer` models:

- `CompositeWorkspace`
  - project
  - name
  - description
  - created/updated metadata

- `CompositeWorkspaceLayer`
  - workspace
  - source saved file reference, probably `IDFFile` initially
  - source format
  - display name
  - visible
  - opacity
  - tint/color
  - transform JSON or explicit fields:
    - offset_x
    - offset_y
    - offset_z
    - rotation_z
    - scale
  - coordinate basis metadata
  - bounding box metadata
  - layer order

Open question: whether IFC should first be made persistable as `IDFFile`, or whether composite layers should reference a separate IFC/cache record.

### APIs

Potential endpoints:

- list/create/open composite workspaces
- add saved file to workspace
- update layer transform/visibility/opacity
- render composite scene payload

### Viewer Concepts

Composite viewer should:

- Render multiple saved file payloads in one Three.js scene.
- Keep each file as a separate Three.js group.
- Apply per-layer transform at group level.
- Provide layer panel:
  - show/hide
  - opacity
  - focus
  - color/tint
  - transform edit

### Alignment MVP

Start with manual transform:

- offset X/Y/Z
- rotation Z
- scale
- layer bounding boxes
- coordinate/unit badges

Defer automatic alignment until manual superimposition is reliable.

### Testing

Before coding:

- Unit tests for model scoping.
- API tests for layer transform persistence.
- Scene payload test for multiple layers.
- Ensure existing `idfviewer` tests still pass.
- Do not run broad unrelated test suites unless necessary.

## First Coding Pass After Discussion

After the user approves architecture:

1. Add isolated `idfviewer` models/migrations for composite workspace/layers.
2. Add minimal backend CRUD/load endpoints.
3. Add tests.
4. Do not alter hot/cold/SLD logic.
5. Do not change existing single-file viewer behavior.

## Communication Style

Be explicit and cautious. The user values ambitious engineering but has asked not to go too fast or too deep without grounding. Recommend a plan, ask for agreement on architecture, then implement in small reversible passes.

