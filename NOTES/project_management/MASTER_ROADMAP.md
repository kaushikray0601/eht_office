# eTrace Master Roadmap

Last updated: 2026-06-07

## Product Vision

Build a comprehensive electrical heat tracing design platform that goes beyond
manufacturer tools by joining heat-loss calculation, tracer selection, cold
cable design, SLD engineering, BOQ/cable schedules, model-based routing, and
auditable engineering reports in one workflow.

The product should be credible to practicing EHT engineers, useful for design
iteration, and strong enough to expose assumptions, limitations, and review
items instead of hiding them.

## Current Intermediate Goal

Close the current working path to production-ready quality:

1. Hot engineering for SR and MI.
2. Cold cable engineering.
3. BOQ and cable schedule.
4. Interactive SLD and SLD export.
5. Calculation manual and hand-calculation verification report.

Constant Power tracer and 3D/model-routing work remain future modules until the
current SR/MI/cold-cable/SLD path is stable.

## Completed Capability Baseline

- Basic heat-loss calculation.
- SR tracer selection and reporting.
- SR straight parallel-run support.
- MI automatic fallback when SR catalogue suitability limits are exceeded.
- MI validated catalogue gating.
- MI identical multi-set support.
- Power distribution topology for SR/MI outputs.
- SLD generation from persisted power-distribution branches.
- Controlled SLD topology edits and layout persistence.
- BOQ and cable schedule foundations.
- Cold cable ampacity, voltage drop, RCD-aware earth-loop review, and 4C/3C optimization.
- Per-outgoing 3C cold-cable sizing.
- Cold-cable conductor mass estimate.
- SLD/cable schedule/result/report integration for cold cable results.
- Calculation verification report: hand-calculation style, Sections A-E,
  terminal voltage cross-check, and optimisation savings comparison.
- Engineering Hub and Design Guide at `/design-guide/`.
- Calculation user manual in `NOTES/CALCULATION_MODULE_USER_MANUAL.md`.

## Phase Roadmap

### Phase A - Current Production Path

Objective: make the existing SR/MI + cold cable + SLD workflow production-ready.

- Stabilize current worktree and migrations.
- Complete cold-cable production hardening.
- Complete procurement-grade cable schedule.
- Complete SLD review-state/issue-badge polish.
- Complete verification examples and release checklist.

### Phase B - Constant Power Tracer

Objective: add constant power / constant wattage tracer as a separate hot-engineering module.

- Catalogue model design and engineering-basis review come first, before any
  implementation, following the same sequence used for MI.
- Catalogue model and validation.
- Selection calculation.
- Electrical current/breaker integration.
- BOQ/cable schedule/SLD integration.
- Reporting and worked examples.

### Phase C - Model-Based Routing and 3D/Isometric Workflow

Objective: extend `idfviewer` into a model-assisted EHT engineering workspace.

- Strengthen IDF/PCF/IFC parsing and 3D rendering.
- Allow model-based EHT component placement.
- Model tray/trench/cable-route geometry.
- Feed route lengths into cold-cable sizing.
- Prepare exports for project model integration such as SP3D/E3D workflows.

### Phase D - Advanced Engineering Differentiators

Objective: build features that exceed manufacturer tools.

- Phase balancing and panel coordination.
- Cable drum/route optimization.
- Tracer PE-path impedance and protection evidence.
- Advanced heat-loss methods.
- SR vendor curve-point interpolation.
- MI terminal/gland/JB capacity.
- Design-option comparison dashboards.

## Current Recommended Sequence

1. `PM-00`: Create project-management control files.
2. `CC-P0`: Stabilization checkpoint.
3. `CC-P1`: Installation-method catalogue readiness and UI guidance. Complete.
4. `CC-P2`: Per-segment 3C cold-cable reporting/export. Complete.
5. `CC-P3`: 3PH JB phase-balancing visibility. Next.
6. `CC-P4`: Panel/load summary.
7. `SCH-P1`: Procurement-grade cable schedule fields/export.
8. `SLD-P1`: Visual issue badges and review indicators.
9. `SLD-P2`: Topology edit impact summary.
10. `QA-P1`: Worked examples and verification report alignment.
11. `RELEASE-P1`: Production readiness sweep.
