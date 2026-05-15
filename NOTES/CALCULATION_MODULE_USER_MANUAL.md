# Calculation Module User Manual

Document status: Draft for integration into the full EHT Office user guide  
Module covered: Electrical heat tracing calculation module  
Current calculation technology: Self-regulating tracer cable, also called SR cable  
Future technology: MI cable will be added as a separate calculation module

## 1. Purpose of This Manual

This manual explains how to use the calculation module in EHT Office from a
user's point of view. It is written for engineers, designers, reviewers, and
project users who need to prepare project setup data, upload line-list input,
run heat-tracing calculations, and review the generated calculation results,
BOQ, cable schedule, and SLD output.

The current calculation module is focused on self-regulating heating cables.
The module calculates heat loss, selects a suitable SR tracer from the selected
vendor catalogue, sizes circuits and breakers, generates per-line and
consolidated BOQ quantities, creates cable schedule data, and builds SLD-ready
power-distribution information.

The manual also explains the engineering meaning of important result fields so
that users do not misinterpret values such as heat loss, current, tracer
length, or rejected tracer selections.

## 2. Current Scope and Important Boundary

The current calculation engine supports SR cable calculation. MI cable
calculation is intentionally not included in this SR module. MI cable will be
developed as a separate calculation path because MI cable engineering uses
different selection logic, factory heater-set constraints, sheath temperature
checks, cold lead and hot-cold joint considerations, series resistance behavior,
and circuit design rules.

The current SR calculation module includes:

- Project setup data entry.
- Input Excel upload and validation.
- Confirmed-line calculation.
- Conduction-based heat-loss calculation with insulation conductivity evidence.
- Heat-loss safety factor application.
- SR vendor catalogue filtering and tracer selection.
- Voltage scenario handling for low-voltage heat delivery, nominal display, and
  high-voltage current checks.
- Per-circuit current and breaker sizing.
- Termination allowance handling as ordered SR length, not energized heat
  delivery length.
- Per-line and consolidated BOQ generation.
- Cable schedule generation from the active SLD/power-distribution model.
- SLD graph generation and SLD PDF export.
- Structured diagnostics when a line cannot receive a suitable SR tracer.

The current SR calculation module does not yet include:

- MI cable calculation.
- Full external convection and radiation heat-transfer calculation.
- Integrated k(T) insulation conductivity solver.
- Vendor or standard heat-loss table interpolation.
- Multi-layer insulation thermal resistance.
- Recalculation of load, BOQ, or cable size from manual SLD tracer overrides.

These deferred items are planned as future enhancements and should not be
assumed to be active unless explicitly released.

## 3. Typical User Workflow

The normal calculation workflow is:

1. Open the project workspace.
2. Select a project in the Project Data tab.
3. Enter or verify project setup values.
4. Save the project setup, or upload an input file from the same workspace. If
   the upload is started after changing project setup values, the visible setup
   values are saved before the calculation runs.
5. Upload the input Excel file.
6. Review the upload validation result.
7. Confirm valid imported rows when required.
8. Let the calculation run.
9. Review Calculation Results.
10. Review SR Selection Diagnostics, if any lines were not assigned a tracer.
11. Review BOQ.
12. Review Cable Schedule.
13. Review the Single Line Diagram.
14. Export required Excel or PDF outputs.

The application is designed to store calculation evidence. This means the
result tabs and exports display persisted calculation values rather than
recalculating silently when the user opens a report.

## 4. Project Selection

A calculation must be associated with a project. Projects are managed in Django
admin and appear in the Project ID dropdown when they are active and available
to the current user.

The Project ID controls which project setup, imported line-list rows,
calculation results, BOQ, cable schedule, and SLD graph are displayed.

Important behavior:

- The default/template project is not shown as a normal working project.
- If a project has no saved setup, the result and BOQ tabs will show a message
  indicating that setup must be saved before calculation results can be used.
- If a user changes project setup fields and uploads an input file immediately,
  the upload process saves the visible project setup before running the
  calculation.

## 5. Project Setup Fields

Project setup values define the design basis for all lines in the selected
project. Users should treat these values as controlled engineering inputs.

### 5.1 Project and Vendor Fields

| Field | Meaning | User Guidance |
| --- | --- | --- |
| Project ID | The active project for calculation and reporting. | Select the correct project before saving setup or uploading input data. |
| Select Vendor | SR vendor catalogue to use for tracer selection. | Select the vendor whose SR catalogue should be used. If the selected vendor has no SR rows in the local catalogue, no SR tracer can be selected for that vendor. |
| Heat loss calculation method | Conductivity basis for heat-loss calculation. | Default is Mean insulation temperature. Placeholder methods are visible for future expansion but currently fall back to the implemented mean-temperature method. |

Current vendor choices shown by the application are Thermon, Chromalox, nVent,
SST, and KRUS-Zapad. Catalogue availability depends on the data loaded into the
application database. A vendor appearing in the dropdown does not guarantee that
valid SR rows are available for all project conditions.

### 5.2 Temperature and Area Classification Fields

| Field | Meaning | User Guidance |
| --- | --- | --- |
| Min. ambient Temp. (deg C) | Minimum ambient temperature used for heat loss and starting/current checks. | Use the project design minimum ambient temperature. This value directly affects heat loss and maximum current. |
| Max. ambient Temp. (deg C) | Maximum ambient temperature stored in project setup. | Used as part of project design data. Current SR selection primarily uses minimum ambient for heat loss and current checks. |
| Startup Temp. (deg C) | Project startup temperature. | Stored in the project design basis. Current SR logic stores startup-related catalogue fields but main current sizing uses minimum ambient. |
| Area Class | Hazardous-area or safe-area classification. | Use the project area classification, such as safe area or Zone/classification text. If catalogue area data is declared, the SR selection checks compatibility. |
| Temp. Class | Required temperature class, such as T3, T4, etc. | Used for SR catalogue filtering when vendor catalogue rows declare temperature rating data. |

Temperature validation:

- Minimum ambient temperature cannot be greater than maximum ambient
  temperature.
- In line-list input, operating, maintain, and design temperatures must satisfy:
  `Oper_T <= Maint_T <= Design_T`.

### 5.3 Electrical Design Fields

| Field | Meaning | User Guidance |
| --- | --- | --- |
| System Voltage (V) | Nominal project supply voltage. | Used for voltage compatibility, power correction, current calculation, and load calculation. |
| Max. circuit breaker size (A) | Maximum breaker size allowed by the project basis. | Used to calculate circuit count and final breaker selection. |
| Max. circuit breaker loading (%) | Allowed breaker loading percentage. | Used as the restricted loading factor for per-circuit current sizing. Must be greater than 0 and not more than 100. |
| Allowed voltage drop for cold cable (%) | Voltage drop design criterion for cold cable. | Stored as project basis for cable design development. Current SR power-distribution output does not yet perform full voltage-drop cable sizing from this value. |
| Design margin for voltage variation (%) | Voltage variation allowance. | Used to create low-voltage and high-voltage scenarios. Low voltage sizes heat delivery. High voltage sizes maximum current. |
| Tracer resistance tolerance (%) | Resistance tolerance design field. | Stored as project basis. Current SR calculation does not yet apply a detailed resistance-tolerance current model. |

The calculation separates voltage scenarios:

- Low-voltage scenario: used to check heat delivery.
- Nominal-voltage scenario: used for displayed tracer power output.
- High-voltage scenario: used for maximum current and breaker sizing.

This prevents one voltage value from being incorrectly used for every design
purpose.

### 5.4 SR Installation and Tracer Selection Fields

| Field | Meaning | User Guidance |
| --- | --- | --- |
| Allowed Spiral Factor | Maximum allowed spiral factor for SR selection. | A tracer is rejected if the required spiral factor is above this limit. |
| Installation with spiral wrap | Whether spiral installation is allowed. | If disabled, only straight-run selections with spiral factor not more than 1.0 are allowed. |
| Margin on tracer length (%) | Design margin applied to heated tracer length. | This margin is applied before termination allowance is added. |
| Termination margin (in mm) | Installation allowance per circuit for termination. | Added to ordered SR cable length per circuit. It is not treated as energized heat-delivery length. |
| Safety Factor on Heat Loss (> 1.0) | Safety factor applied to base heat loss. | The result called Design Heat Loss is base heat loss multiplied by this factor. |

Important distinction:

- Heated tracer length is the length required for heat delivery after spiral
  factor and design margin.
- Ordered SR length includes the termination installation allowance.
- Termination allowance is excluded from electrical load and heat-delivery
  sizing.

### 5.5 Control, Label, and Local Isolator Fields

| Field | Meaning | User Guidance |
| --- | --- | --- |
| Select RTD/Thermostat type | Defines RTD or thermostat basis and whether the control point is inline or offline. | Used by BOQ logic to count RTD, thermostat, and pipe strap quantities for process-temperature-controlled services. |
| Wind speed (kmph) | Project wind speed. | Used in the current heat-loss correction. |
| Caution Label Interval (m) | Spacing basis for caution labels. | Used to calculate caution label quantity. |
| Local Isolator Location | Defines incoming/outgoing/both/no local isolator basis. | Used to count local isolators and generate SLD component arrangement. |
| Cable Length (DB to JB) (m) | Assumed cable length from distribution board to junction box. | Used in power distribution, BOQ, cable schedule, and SLD generation. |
| Loop Length (JB to JB) (m) | Assumed loop length between 3-phase JB and 1-phase JBs. | Used when multiple circuits are grouped under a 3-phase junction box. |

The local isolator requirement is synchronized from Local Isolator Location. If
the location is set to no isolator, the local isolator requirement is treated as
not required.

## 6. Input Excel File Requirements

The calculation module accepts Excel input files with extension `.xlsx`.

Upload restrictions:

- Maximum file size is 10 MB.
- File extension must be `.xlsx`.
- The file must be a valid Excel workbook.

### 6.1 Mandatory Input Columns

The following columns are mandatory for calculation:

| Column | Meaning |
| --- | --- |
| Service_Type | Service type for the line. |
| Line_Size | Nominal pipe size, in inches. |
| Line_Length | Pipe length, in meters. |
| Ins_Mat_Type | Insulation material type matching the conductivity database. |
| Insul_Thick | Insulation thickness, in mm. |
| Maint_T | Maintain temperature, in deg C. |
| Oper_T | Operating temperature, in deg C. |
| Design_T | Design temperature, in deg C. |

### 6.2 Optional or Defaulted Input Columns

The following columns may be blank. The system applies safe defaults where
appropriate:

| Column | Default Behavior |
| --- | --- |
| IsDeleted | Defaults to false. |
| Emergency_Supply | Defaults to false. |
| Valve_Qty | Defaults to 0. |
| Flange_Qty | Defaults to 0. |
| Support_Qty | Defaults to 0. |
| PID_No | Defaults to `n/A`. |
| Area | Defaults to `n/A`. |
| Train | Defaults to `n/A`. |
| Pipe_Mat_Class | Defaults to `n/A`. |
| Discipline | Defaults to `n/A`. |
| Remarks | Defaults to `n/A`. |

### 6.3 Input Validation Rules

The upload validation checks:

- Mandatory fields are present.
- Numeric fields are numeric.
- Line size, line length, and insulation thickness are not negative.
- Temperatures satisfy `Oper_T <= Maint_T <= Design_T`.
- Duplicate rows are detected using key line and design fields.

If invalid rows are found, the module generates an error workbook. The error
workbook includes an Errors column describing why each row failed validation.

### 6.4 Pending and Confirmed Rows

Imported rows may pass through a confirmation step. The calculation engine uses
only confirmed rows.

Important behavior:

- Pending rows are not included in calculation.
- If a project has only pending rows, calculation is rejected until valid rows
  are confirmed.
- If a new upload has no valid rows, existing project calculation data is not
  cleared.

This protects previously calculated project data from being accidentally
removed because of a bad upload.

## 7. Calculation Flow

After project setup and confirmed input data are available, the calculation
pipeline runs in this order:

1. Fetch confirmed process lines for the selected project.
2. Fetch project setup.
3. Fetch pipe outside diameter data.
4. Fetch insulation conductivity data.
5. Fetch selected vendor catalogue data.
6. Calculate heat loss for each line.
7. Select SR tracer candidates.
8. Calculate circuit current, breaker size, and ordered tracer length.
9. Build power-distribution branches.
10. Calculate per-line BOQ.
11. Consolidate BOQ.
12. Persist result evidence.
13. Make results available to the Result, BOQ, Cable Schedule, and SLD tabs.

If a line fails at heat-loss calculation, it will not proceed to tracer
selection. If a line passes heat-loss calculation but no SR tracer can be
selected, the heat-loss evidence and rejection reason are stored and displayed
under SR Selection Diagnostics.

## 8. Heat-Loss Calculation Basis

The current heat-loss calculation is a conduction-based insulated-pipe heat
loss model with a wind correction and user-defined heat-loss safety factor.

### 8.1 Conductivity Method

The default conductivity basis is Mean insulation temperature. This evaluates
the insulation conductivity polynomial at:

`(Maint_T + Min_Ambient_T) / 2`

Current method options:

| Method | Current Status | User Guidance |
| --- | --- | --- |
| Mean insulation temperature (recommended) | Implemented and default. | Recommended for current project work. |
| Legacy maintain temperature | Implemented for comparison/backward compatibility. | Use only when older project comparison is required. |
| Standard/vendor table | Placeholder. | Currently falls back to mean-temperature calculation with evidence. |
| Integrated k(T) | Placeholder. | Currently falls back to mean-temperature calculation with evidence. |
| Fixed project basis | Placeholder. | Currently falls back to mean-temperature calculation with evidence. |

The result evidence records the requested method and the effective method. This
is important where a placeholder method is selected by the user, because the
calculation will still state that the active method was the mean-temperature
fallback.

### 8.2 Conductivity Polynomial

Insulation conductivity is calculated from stored conductivity coefficients:

`k = A*T^2 + B*T + C`

Where:

- `k` is insulation conductivity.
- `T` is the selected conductivity evaluation temperature.
- `A`, `B`, and `C` come from the insulation conductivity database.

The input insulation material type must match a material in the conductivity
database. If no conductivity row is found, the line cannot proceed to heat-loss
calculation.

### 8.3 Pipe Outside Diameter

The module first attempts to find pipe outside diameter from the stored ASME
B36 pipe table. If the nominal pipe size is not found, the module uses an
approximation formula for pipe outside diameter.

Users should review unusual pipe sizes carefully and ensure the pipe table data
is complete where project accuracy depends on exact outside diameter.

### 8.4 Base Heat Loss and Design Heat Loss

Base heat loss is calculated before applying the heat-loss safety factor.

The calculation uses:

`q = 2*pi*k*(Maint_T - Min_Ambient_T) / ln((2*t + D) / D)`

Where:

- `q` is base heat loss per meter.
- `k` is insulation conductivity.
- `t` is insulation thickness.
- `D` is pipe outside diameter.
- `Maint_T` is maintain temperature.
- `Min_Ambient_T` is project minimum ambient temperature.

The module then applies wind correction and heat-loss safety factor:

`Design Heat Loss = Base Heat Loss after wind correction * Heat Loss SF`

The result tab and Excel export distinguish:

- Base Heat Loss before SF.
- Heat Loss Safety Factor.
- Design Heat Loss.

The Design Heat Loss is the value used for SR tracer heat-delivery selection.

### 8.5 Wind Correction

Wind correction is currently applied as a simple correction factor:

- No reduction is applied for low wind.
- Above 32 kmph, the correction increases by approximately 1 percent per mph
  equivalent above 32 kmph.
- The correction is capped at 20 percent.

This is a practical project correction, not a full external heat-transfer
model. A future external heat-transfer model is planned for convection,
radiation, emissivity, jacket material, and indoor/outdoor basis.

### 8.6 Accessory Tracer Adders

The SR calculation adds tracer length for valves, supports, and flanges using a
named empirical rule set based on pipe outside diameter.

These adders affect tracer length selection. They are stored as calculation
evidence so reviewers can see the accessory basis.

Current accessory basis:

- Valve adder: based on valve quantity and pipe outside diameter.
- Support adder: based on support quantity and pipe outside diameter.
- Flange adder: based on flange quantity and pipe size range.

These are not currently vendor-specific adders. If a project requires
vendor-specific accessory allowance rules, those rules should be added as a
future engineering enhancement.

## 9. SR Tracer Selection Basis

SR tracer selection uses the selected vendor catalogue and the project/line
design basis.

### 9.1 Vendor Catalogue Filtering

The module filters candidate rows using declared catalogue data. Missing or
blank catalogue suitability fields are treated as non-blocking because many
legacy catalogue rows are incomplete.

When catalogue data exists, the following checks may be applied:

- Tracer family must be SR or self-regulating.
- Maintain temperature must be within catalogue maintain limit.
- Operating temperature must be within catalogue operating limit.
- Design/exposure temperature must be within catalogue exposure limit.
- Hazardous-area zone compatibility is checked when zone data is declared.
- IEC gas-group compatibility is checked when gas-group data is declared.
- Temperature class compatibility is checked when T-rating data is declared.

If no catalogue rows survive these checks, the line appears in SR Selection
Diagnostics.

### 9.2 Voltage Compatibility

Voltage compatibility is handled after vendor data is fetched. The module does
not exclude vendor rows at the database query stage merely because catalogue
voltage is slightly below project voltage.

The current rule is:

1. Prefer catalogue rows rated at or above the project nominal voltage.
2. If no such rows exist, allow nearby nominal voltage classes within 10
   percent deviation.

Example:

- A 230 V catalogue class may be allowed for a 240 V project if no higher-rated
  class exists and the deviation is within the allowed nominal-class rule.

This is a compatibility rule for catalogue class handling. The actual heat
delivery and current calculations still apply voltage correction scenarios.

### 9.3 Voltage Scenarios

The module separates voltage into three engineering scenarios:

| Scenario | Purpose |
| --- | --- |
| Low voltage | Used for heat-delivery sizing. |
| Nominal voltage | Used for displayed/recorded nominal power output. |
| High voltage | Used for maximum current and breaker sizing. |

Low voltage and high voltage are derived from the project voltage variation
factor.

This separation is important because SR cable must deliver enough heat at low
voltage, while maximum current and breaker sizing should be checked at the
high-voltage condition.

### 9.4 Power Output and Spiral Factor

For each candidate tracer, the module calculates power output at the maintain
temperature using the vendor polynomial:

`Power = A*Maint_T^2 + B*Maint_T + C`

The heat-delivery power is voltage-corrected using the low-voltage scenario.

Required spiral factor is calculated from:

`Spiral Factor = Design Heat Loss / Low-Voltage Heat-Delivery Power`

The module currently requires spiral factor to be at least 0.8 and not greater
than the project Allowed Spiral Factor. If spiral wrap is not allowed, the
spiral factor must not exceed 1.0.

If no candidate row satisfies the spiral factor limits, the line appears in SR
Selection Diagnostics with reason code `NO_SPIRAL_FACTOR_MATCH`.

### 9.5 Selected Tracer and Alternate Tracers

After filtering and sizing, candidate tracers are ranked by:

1. Lowest tracer length with margin.
2. Lower nominal power output as the secondary sort.

The first row becomes the generated selected tracer. Remaining valid rows are
stored as alternate tracers.

Alternate tracer rows are available for review and SLD tracer override
workflows. However, selecting an alternate in the SLD is currently review-only.
It does not recalculate load, BOQ, cable schedule, or breaker sizing.

## 10. Circuit Current and Breaker Sizing

The current electrical model calculates line-level currents first, then splits
the line into circuits.

### 10.1 Current Basis

The result fields shown as current are per-circuit values:

- Operating Current / Circuit.
- Starting or Maximum Current / Circuit.

The total connected load is based on the full line operating current and the
project nominal voltage.

### 10.2 Circuit Count

The module calculates allowed current per circuit:

`Allowed Current per Circuit = Max CB Size * Max CB Loading Factor`

The number of circuits is then calculated from line maximum current divided by
the allowed current per circuit, rounded up.

### 10.3 Breaker Size

After circuit count is known, the module calculates per-circuit maximum current
and selects a breaker size that satisfies the restricted loading requirement.

Available breaker sizes are selected from the standard sizes configured in the
application.

### 10.4 Termination Margin

Termination margin is treated as an installation allowance.

This means:

- It is added to ordered SR cable length.
- It is added per circuit.
- It is excluded from heat delivery.
- It is excluded from current and load calculation.

Result and BOQ labels use "Ordered SR Length" or similar wording to remind
users that the total ordered cable quantity includes this termination
allowance.

## 11. Power Distribution and SLD Basis

After breaker sizing, the module builds a power-distribution structure for each
line.

General behavior:

- One circuit can be connected through a 1-phase junction box branch.
- Multiple circuits may be grouped through a 3-phase junction box branch.
- Each branch carries tagged component data for MCB, cables, isolators,
  junction boxes, tracers, and end terminations.
- The SLD graph is generated from the stored branch data.

The SLD tab is therefore not an independent drafting tool. It is a graphical
representation of the persisted calculation and power-distribution data, with
controlled manual-edit workflows layered on top.

## 12. Bill of Quantities Basis

The BOQ is generated per line and then consolidated at project level.

Typical BOQ items include:

- MCB.
- 3-phase junction box.
- 1-phase junction box.
- Cable from MCB to 3-phase junction box.
- Cable from 3-phase junction box to 1-phase junction box.
- Ordered SR heating tracer length, including termination allowance.
- End termination kit.
- 1-phase isolator.
- 3-phase isolator.
- RTD.
- Thermostat.
- Caution label.
- Aluminium adhesive tape.
- Pipe strap.

The BOQ tracer item is an ordered cable quantity. It should not be interpreted
as only the energized heat-delivery length.

Control item behavior:

- Inline and offline RTD/thermostat choices affect RTD, thermostat, and pipe
  strap quantities.
- Local isolator location affects isolator counts.
- Caution label interval affects caution label quantity.
- Cable length settings affect cable quantities.

## 13. Result Tab

The Calculation Results tab is the primary review screen for stored
calculation results.

### 13.1 Summary Cards

The summary cards show:

- Calculated Lines.
- Total Circuits.
- Connected Load.
- Ordered SR Length.

Ordered SR Length includes termination allowance.

### 13.2 Per-Line Design Summary

The per-line table includes:

- Line ID and service information.
- Design Heat Loss.
- Base heat loss and heat-loss safety factor.
- Conductivity method evidence.
- Selected tracer.
- Tracer override status, if an SLD override exists.
- Spiral factor.
- Breaker size.
- Circuit count.
- Operating and starting current per circuit.
- Total connected load.
- Ordered SR length.
- Alternate tracer list.

Users should review this table before accepting the project calculation.

### 13.3 SR Selection Diagnostics

If heat loss was calculated but no SR tracer was selected, the line appears in
SR Selection Diagnostics.

The diagnostics table shows:

- Line ID.
- Design heat loss.
- Base heat loss and safety factor.
- Conductivity method.
- Selection status.
- Primary rejection reason code.
- Primary rejection message.

This table is intended to prevent rejected lines from being missed.

## 14. Result Excel Export

The result Excel export contains:

| Worksheet | Contents |
| --- | --- |
| Line Results | Main per-line calculation summary. |
| Selection Diagnostics | Lines where heat loss was calculated but SR tracer selection failed. |
| Power Distribution | Branch-level power-distribution rows. |
| Alternate Tracers | Valid alternate tracer options by line. |

Important exported fields include:

- Design Heat Loss (W/m).
- Base Heat Loss before SF (W/m).
- Heat Loss Safety Factor.
- Conductivity Method.
- Conductivity Rule Set.
- Conductivity (W/m.K).
- Wind Correction Factor.
- Accessory Tracer Adders (m).
- SR Selection Status.
- Starting Current / Circuit (A).
- Operating Current / Circuit (A).
- Current Basis.
- Total Connected Load (W).
- Ordered SR Tracer Length incl. Termination Allowance (m).
- Heated Tracer Length excl. Termination Allowance (m).
- Tracer Length Basis.

The export is intended for review and record keeping. It should be checked
against the project calculation basis before issue.

## 15. BOQ Tab and BOQ Export

The BOQ tab shows:

- Consolidated item count.
- Line group count.
- Ordered SR tracer quantity.
- MCB and junction box totals.
- Consolidated BOQ table.
- Per-line BOQ index with expandable detail.

The BOQ Excel export contains:

- BOQ Summary.
- BOQ Per Line.

The tracer quantity is labeled and described as ordered SR heating tracer
length, including termination allowance.

## 16. Cable Schedule Tab

The Cable Schedule tab displays cable schedule rows generated from the active
SLD/power-distribution data.

Users can review:

- Cable tag.
- Cable specification.
- Cable length.
- Connected from.
- Connected to.
- Line IDs.
- Purpose.
- Manual override status, where applicable.
- Route and remarks fields.

If manual SLD topology or cable length overrides exist, the cable schedule may
show the active manual state or a warning that review is required.

## 17. Single Line Diagram Tab

The Single Line Diagram tab displays the stored SLD graph for the project.

The graph is based on persisted calculation output and branch data. It includes
component metadata such as line identity, branch index, circuit index, selected
tracer information, and SR calculation basis.

### 17.1 SLD Tracer Review

Tracer nodes carry selected tracer metadata and alternate tracer metadata. If
alternate options are available, users can review them from the SLD workflow.

Current limitation:

- SLD tracer overrides are review-only.
- A tracer override does not currently recalculate current, breaker size, BOQ,
  cable schedule, or heat loss.

The result tab and export clearly indicate when an SLD tracer override is
active.

### 17.2 Manual SLD Edits

Manual topology edits are supported by controlled SLD workflows. When a manual
SLD edit is active, the downstream BOQ and cable schedule impact should be
reviewed before issue.

If the project is recalculated after an SLD edit, the application may mark the
manual edit as requiring review or may show a safe generated fallback state
until the edit is reviewed.

## 18. Common Diagnostics and Corrective Actions

### 18.1 No Vendor Catalogue Rows

Reason code: `NO_VENDOR_CATALOGUE_ROWS`

Meaning:

The selected vendor has no usable catalogue rows available to the SR selection
engine.

User actions:

- Confirm that the correct vendor is selected in Project Data.
- Confirm that the vendor's SR catalogue rows are loaded into the database.
- Check whether the vendor has only non-SR rows, such as constant-wattage or MI
  rows.

### 18.2 No SR Catalogue Suitability Match

Reason code: `NO_SR_CATALOGUE_SUITABILITY`

Meaning:

Catalogue rows were available, but none satisfied declared suitability limits.
This may involve tracer family, maintain temperature, operating temperature,
exposure temperature, hazardous-area zone, gas group, or temperature class.

User actions:

- Review maintain, operating, and design temperatures.
- Review area class and temperature class.
- Confirm that vendor catalogue suitability data is correctly loaded.
- Check whether the selected vendor has a suitable SR family for the project
  conditions.

### 18.3 No Voltage-Compatible Catalogue Class

Reason code: `NO_SR_CATALOGUE_VOLTAGE_COMPATIBILITY`

Meaning:

No SR catalogue row satisfied the voltage compatibility rule.

User actions:

- Review project System Voltage.
- Confirm that the vendor catalogue includes the required voltage class.
- Check whether a nearby nominal voltage class should be added or corrected in
  the catalogue data.

### 18.4 No Positive Power Output

Reason code: `NO_POSITIVE_POWER_OUTPUT`

Meaning:

Candidate SR rows did not produce positive heat-delivery power at maintain
temperature after low-voltage correction.

User actions:

- Review vendor polynomial coefficients.
- Review maintain temperature.
- Check catalogue data quality.

### 18.5 No Spiral Factor Match

Reason code: `NO_SPIRAL_FACTOR_MATCH`

Meaning:

Candidate SR rows could not satisfy the configured spiral factor limits.

User actions:

- Confirm that spiral wrap is allowed if project practice permits it.
- Review Allowed Spiral Factor.
- Review heat-loss safety factor.
- Consider a higher-output tracer family if technically acceptable.
- Review insulation thickness and heat-loss basis.

### 18.6 Unexpected Tracer Selection Error

Reason code: `TRACER_SELECTION_ERROR`

Meaning:

The SR selection engine encountered an unexpected error.

User actions:

- Check the line data and vendor catalogue data for unusual or missing values.
- Review server logs.
- Escalate to the application maintainer if the issue persists.

## 19. User Review Checklist Before Issuing Results

Before issuing a calculation package, review the following:

1. Correct Project ID is selected.
2. Correct vendor is selected.
3. Heat-loss calculation method is correct.
4. Min ambient, wind speed, voltage, voltage variation, and heat-loss safety
   factor match the project basis.
5. Area class and temperature class are correct.
6. Input rows are confirmed.
7. There are no unexpected pending input rows.
8. SR Selection Diagnostics are empty, or every diagnostic line has been
   reviewed and resolved.
9. Design heat loss and base heat loss are reasonable.
10. Selected tracer family is acceptable for the service.
11. Spiral factor is within installation practice.
12. Current values are understood as per-circuit values.
13. Ordered SR length is understood to include termination allowance.
14. Circuit count and breaker sizes are acceptable.
15. BOQ quantities are reasonable.
16. Cable schedule lengths are reasonable.
17. SLD topology matches the intended distribution philosophy.
18. Any manual SLD edit or tracer override is reviewed.
19. Exported Excel reports match the on-screen result.
20. Known limitations are acceptable for the project stage.

## 20. Known Limitations

The current calculation module is ready for SR calculation workflows, but users
should understand these limitations:

- The module currently supports SR calculation only. MI cable calculation will
  be added separately.
- Heat loss is currently based on insulated-pipe conduction with a wind
  correction and safety factor. It is not a full convection/radiation external
  heat-transfer model.
- Standard/vendor table, integrated k(T), and fixed project basis methods are
  placeholders. They currently fall back to the mean-temperature method and
  record evidence of that fallback.
- Multi-layer insulation is not yet modeled.
- Vendor catalogue completeness affects selection. A vendor dropdown value does
  not guarantee the required SR rows exist in the database.
- Blank vendor catalogue suitability fields are treated as non-blocking. This
  avoids false rejection of legacy catalogue rows, but users should curate
  catalogue data carefully for final design use.
- Resistance tolerance and allowable voltage drop are stored project fields,
  but the current SR release does not yet perform a complete resistance
  tolerance or cold-cable voltage-drop design calculation.
- Manual SLD tracer overrides are review-only and do not recalculate electrical
  load, BOQ, breaker size, or cable schedule.
- Accessory tracer adders are empirical SR rules, not vendor-specific detailed
  installation rules.

## 21. Recommended User Practice

For routine SR calculation work:

1. Use Mean insulation temperature as the heat-loss method unless a project
   specifically requires legacy comparison.
2. Keep vendor catalogue data curated and reviewed.
3. Treat SR Selection Diagnostics as mandatory review items.
4. Do not issue results with unresolved rejected lines unless the project
   document clearly excludes those lines.
5. Use result Excel exports for engineering review and traceability.
6. Use BOQ and Cable Schedule outputs as generated quantities that still require
   normal engineering review before procurement or construction issue.
7. Record project assumptions outside the app where required by the project
   quality system.

## 22. Glossary

| Term | Meaning |
| --- | --- |
| SR cable | Self-regulating heating cable. |
| MI cable | Mineral insulated heating cable. Future separate module. |
| Base heat loss | Heat loss before heat-loss safety factor. |
| Design heat loss | Heat loss after applying heat-loss safety factor. Used for tracer selection. |
| Heat-loss safety factor | Project factor applied to base heat loss. |
| Conductivity method | Basis used to evaluate insulation conductivity. |
| Spiral factor | Ratio of required heat loss to available tracer heat output. |
| Heated tracer length | Tracer length used for heat delivery, including design length margin but excluding termination allowance. |
| Ordered SR length | Total SR cable quantity including termination allowance. |
| Termination allowance | Installation allowance added per circuit, excluded from heat delivery and current. |
| Operating current / circuit | Per-circuit current at operating condition. |
| Starting current / circuit | Per-circuit maximum/start current used for breaker sizing. |
| Connected load | Total line operating load. |
| Selection diagnostics | Stored reason why a line did not receive a selected SR tracer. |
| SLD | Single Line Diagram. |
| BOQ | Bill of Quantities. |

