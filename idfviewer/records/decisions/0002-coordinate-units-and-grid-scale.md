# 0002 - Coordinate Units and Grid Scale

## Status

Accepted

## Context

The viewer must support IDF, PCF, and IFC geometry as inputs for future EHT design workflows. A fixed visual grid can mislead users when files arrive in different coordinate units or with very different geometry extents.

## Decision

- Store scene-level coordinate metadata in `stats` during normalization:
  - `coordinate_unit`
  - `coordinate_scale_to_m`
  - `display_unit`
  - `unit_confidence`
- Use declared `UNITS-CO-ORDS` for PCF where available.
- Treat IDF as millimetres for now.
- Treat IFC as metres for now, pending native IFC unit extraction.
- Size the grid from the visible geometry extent and derive a human-friendly grid step from that extent.

## Consequences

- Measurement tools can use scene-normalized metre coordinates without guessing per format.
- PCF files with declared coordinate units become safer to compare against file parameters.
- IFC needs a follow-up pass to read project units directly from the IFC file instead of relying on an assumption.
