# SR Conductivity Basis Research

Date: 2026-05-13

Purpose: decide how the SR heat-loss engine should apply insulation thermal
conductivity when conductivity varies with temperature. This note responds to
`heat_tracing_insulation_conductivity_basis.docx` in the project root and
records the basis to discuss before coding SR-05.

## Short Answer

Do not make pipe maintain temperature the normal conductivity basis.

For a serious heat-tracing calculation engine, the preferred calculation basis
is effective insulation conductivity across the insulation temperature gradient.
In practice, this means either:

1. Integrated k(T), with the insulation outer surface temperature solved
   iteratively; or
2. k evaluated at each insulation layer mean temperature, also with an
   estimated or solved outer surface temperature.

Maintain-temperature k can remain as a named legacy/conservative mode, but it
should not be the default engineering basis for future SR or MI work.

## Why Maintain-Temperature k Is Weak

The current SR code effectively does this:

```text
k = A * maintain_temp^2 + B * maintain_temp + C
q = 2 * pi * k * (maintain_temp - min_ambient) / ln((pipe_od + 2 * insulation_thickness) / pipe_od)
```

That assumes one representative insulation temperature equal to the pipe
maintain temperature. The insulation is actually hot near the pipe and colder
near the cladding/ambient side. If k increases with temperature, maintain-temp
k will normally overstate the layer-average k and therefore overstate heat
loss. That can be conservative for cable selection, but it is not the best
physics basis and it will distort connected load, circuit count, energy
estimates, MI watt-density decisions, and hazardous-area temperature checks.

## Literature Check

- NIA Mechanical Insulation Design Guide says most insulation k varies
  significantly with temperature, and recommends effective conductivity from
  integration of the conductivity-temperature curve or, approximately, k at the
  mean temperature across the insulation layer.
- ASTM C680-23a is specifically a computer-method standard for heat gain/loss
  and surface temperatures of insulated flat, cylindrical, and spherical
  systems under one-dimensional steady or quasi-steady conditions.
- ISO 12241:2022 is the international calculation-rules standard for heat
  transfer properties of building equipment and industrial installations,
  predominantly under steady-state conditions.
- IEC/IEEE 60079-30-2 is the electrical resistance trace-heating application
  guide. Publicly accessible older text describes heat-loss calculation with
  insulation conductivity evaluated at mean temperature and recognizes that the
  system factor depends on insulation layer type/thickness, mean insulation
  temperature, and film coefficients.
- Thermon steam-tracing guidance asks for a complete insulation specification,
  including thermal conductivity at several mean temperatures, before actual
  heat losses are determined.
- nVent RAYCHEM and Chromalox SR design guides commonly use vendor heat-loss
  tables plus insulation correction factors. Those guides are useful for quick
  and comparable SR selection, but they are table/assumption methods rather
  than a general k(T) solver.

## Recommended Architecture

Add a shared thermal service that returns both results and evidence. The SR
engine and future MI engine should call the same service.

Calculation methods to support:

1. `standard_table`
   - Uses vendor/IEEE-style heat-loss tables and insulation factors.
   - Good for quick SR comparison and legacy validation.
   - Evidence must include table name, assumed insulation, wind basis, safety
     factor, and interpolation details.
2. `mean_temperature`
   - Solves or estimates insulation outer surface temperature.
   - Evaluates k at `(T_inner + T_outer) / 2` for each layer.
   - Good first implementation if our source data is catalogue k at mean
     temperature.
3. `integrated_kT`
   - Uses the fitted k(T) curve to calculate effective conductivity across the
     layer:

```text
k_eff = integral(k(T), T_outer..T_inner) / (T_inner - T_outer)
q_per_m = 2 * pi * k_eff * (T_inner - T_outer) / ln(D_outer / D_inner)
```

   - For `k(T) = A*T^2 + B*T + C`:

```text
k_eff =
  (A/3 * (T_inner^3 - T_outer^3)
 + B/2 * (T_inner^2 - T_outer^2)
 + C   * (T_inner   - T_outer))
 / (T_inner - T_outer)
```

   - Best long-term method when data source, units, basis, and valid
     temperature range are known.
4. `fixed_project_basis`
   - Uses a client/project/vendor-mandated conductivity value or reference
     temperature.
   - Must be explicit in the report and not silently mixed with other methods.
5. `legacy_maint_temperature`
   - Preserves the current behavior for regression comparison only.
   - Should carry a warning/evidence flag: conservative screening basis, not
     preferred design basis.

## Data Model Implications

The current `ElecEHT_ThermalConductivity` table only stores material plus A, B,
C coefficients. That is not enough for calculation-grade traceability.

Add or evolve data to capture:

- Source document/manufacturer/specification.
- Temperature unit used for fitting.
- Conductivity unit.
- Whether source x-axis is mean temperature, hot-face temperature, or another
  declared basis.
- Valid temperature range.
- Insulation product density/class/standard where relevant.
- Curve-fit method and fit error, or raw tabulated points.
- Safety factor or ageing/wet-service allowance if mandated by project spec.

## My Position vs the DOCX

I agree with the DOCX on the main technical conclusion: maintain-temperature k
should not be our normal design basis; mean-temperature or integrated effective
k is the right direction.

I would adjust the implementation recommendation:

- The DOCX says the default should be `integrated_kT`. I agree long-term, but I
  would not make it the immediate default until our conductivity data is
  properly tagged with source, unit, temperature-basis, and valid range. For the
  next SR hardening pass, I recommend adding a documented method switch and
  keeping current numeric behavior as `legacy_maint_temperature`, then adding
  `mean_temperature`/`integrated_kT` behind tests using curated data.
- I would not treat vendor heat-loss-table methods as inferior or obsolete.
  nVent and Chromalox still use table/factor workflows in published SR design
  guides. We should support table mode for comparison and simple SR work, while
  using the detailed solver for EPC-grade calculation and MI work.
- For composite or multi-layer insulation, I would avoid a simple arithmetic
  average conductivity as the general method. The calculation-grade method
  should use layer-by-layer thermal resistances and layer-specific mean or
  effective k.

## Proposed Decision for Discussion

Adopt this policy:

- `legacy_maint_temperature` stays only to preserve current SR outputs while we
  harden the app.
- `mean_temperature` becomes the first new engineering method because it is
  supported by insulation design guidance and easier to validate.
- `integrated_kT` becomes the target advanced method once conductivity data is
  curated and the outer-surface solver is implemented.
- `standard_table` stays available for vendor/IEEE-style SR quick checks and
  validation against published design guides.
- Every heat-loss result must persist the selected method, input temperatures,
  final k or k_eff, data source, and any safety factors.

## Decision Recorded 2026-05-14

- Default project setup method: `mean_temperature`.
- Active comparison method: `legacy_maint_temperature`.
- Placeholder methods: `standard_table`, `integrated_kT`, and
  `fixed_project_basis`.
- Placeholder methods currently calculate using mean-temperature basis and
  write an evidence warning so the result is reviewable.
- External convection/radiation modelling, standard/vendor table sources,
  integrated k(T), fixed project basis, and multi-layer insulation are deferred
  to the heat-loss method backlog in `NOTES/SR_CALCULATION_HARDENING_TRACKER.md`.

## Sources

- NIA Mechanical Insulation Design Guide, Design Data:
  https://insulation.org/training-tools/designguide/design-data/
- ASTM C680-23a listing at ANSI:
  https://webstore.ansi.org/standards/astm/astmc68023a
- ISO 12241:2022 official ISO page:
  https://www.iso.org/standard/74655.html
- IEEE/IEC 60079-30-2-2025 official IEEE page:
  https://standards.ieee.org/ieee/60079-30-2/7570/
- IEC/IEEE 60079-30-2:2025 official IEC page:
  https://webstore.iec.ch/en/publication/73328
- Accessible EN 60079-30-2:2007 preview text:
  https://standards.iteh.ai/catalog/standards/clc/f5e1ef2b-d60e-4b6b-a8c9-ab3c6701cdf9/en-60079-30-2-2007
- Thermon Specification Guide for Steam Tracing Applications:
  https://content.thermon.com/pdf/ca_pdf_files/TSP0010-Steam-Tracing-Spec-Guide.pdf
- nVent RAYCHEM Self-Regulating Heat-Tracing Design Guide:
  https://www.nvent.com/sites/default/files/acquiadam_assets/2023-01/Raychem-DG-H56882-SelfRegulating-EN.pdf
- Chromalox Heat Trace Design Guide:
  https://content.chromalox.com/-/media/chromalox/documents/design-guides/dg-heat-trace-design-guide.ashx
