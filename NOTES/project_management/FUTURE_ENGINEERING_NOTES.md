# Future Engineering Notes

Last updated: 2026-06-15

Purpose: record credible post-MVP engineering extensions without letting them
expand the current Phase A release scope.

## Advanced Heat-Loss Methods

Current MVP basis uses the existing heat-loss model and documents known
assumptions. A later release should add advanced heat-loss options aligned with
recognised design methods and/or vendor design guides.

Technical notes:

- Include a more formal external convection/wind model instead of the current
  simplified wind correction.
- Add vendor/project-specific accessory allowance tables where project
  specifications require published valve, flange, and support adders instead
  of the current empirical rule set.
- Define validity ranges for wind speed, insulation conditions, pipe geometry,
  and ambient assumptions.
- Keep the current method available as a simple/conservative mode if useful for
  early-stage estimates.
- Add report language that identifies which heat-loss method was used for each
  calculation run.
- Add worked examples before allowing production use.

## Three-Phase Heat-Tracing Design

Current MVP scope is single-phase SR/MI heat-tracing branch design with
three-phase visibility used only for distribution/load review where applicable.
A later release should add native three-phase heat-tracing design.

Technical notes:

- Define supported three-phase heating topologies before coding.
- Add explicit phase connection and balancing data models.
- Extend cold-cable voltage-drop, protection, and SLD logic for true
  three-phase heat-tracing loads.
- Add project setup controls that clearly distinguish single-phase heat tracing,
  three-phase distribution, and true three-phase heater circuits.
- Add verification examples and manual limitations before enabling the feature.

## Constant Power / Constant Wattage Tracer

Constant Power remains a separate future hot-engineering module, not a
catalogue variant inside SR/MI selection.

Technical notes:

- Design catalogue models and validation workflow first.
- Treat selection, electrical current, breaker sizing, BOQ, cable schedule, SLD,
  and reporting integration as a complete module.
- Do not let Constant Power selection silently use SR assumptions.

## Advanced Routing and 3D/Model Workflow

Model-based routing remains a Phase C/D differentiator after the current SR/MI,
cold cable, SLD, BOQ, and schedule path is stable.

Technical notes:

- Use IDF/PCF/IFC or other model sources to derive route lengths.
- Feed tray/trench/cable route geometry into cold-cable sizing.
- Preserve manual override and review evidence when model-derived lengths are
  edited.
- Prepare export paths that can later integrate with SP3D/E3D-style workflows.
