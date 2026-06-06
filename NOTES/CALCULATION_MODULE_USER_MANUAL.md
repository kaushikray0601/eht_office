# Calculation Module User Manual

Document status: Draft for integration into the full EHT Office user guide  
Module covered: Electrical heat tracing calculation module  
Current calculation technologies: Self-regulating tracer cable, also called SR
cable, with automatic MI fallback for validated high-temperature cases  
Future technology: Constant wattage cable and advanced MI zoning will be added
as separate calculation modules

## 1. Purpose of This Manual

This manual explains how to use the calculation module in EHT Office from a
user's point of view. It is written for engineers, designers, reviewers, and
project users who need to prepare project setup data, upload line-list input,
run heat-tracing calculations, and review the generated calculation results,
BOQ, cable schedule, and SLD output.

The current calculation module is focused on self-regulating heating cables as
the default technology. The module calculates heat loss, selects a suitable SR
tracer from the selected vendor catalogue, sizes circuits and breakers,
generates per-line and consolidated BOQ quantities, creates cable schedule data,
and builds SLD-ready power-distribution information.

For lines whose temperatures exceed the available SR catalogue temperature
limits, the module can automatically select a validated mineral insulated, or
MI, heater set. MI selection is a separate calculation path with its own
catalogue validation, resistance-temperature correction, cold-lead option, and
heater-set output evidence.

The manual also explains the engineering meaning of important result fields so
that users do not misinterpret values such as heat loss, current, tracer
length, or rejected tracer selections.

## 2. Current Scope and Important Boundary

The current calculation engine supports SR cable calculation and a bounded MI
automatic-fallback MVP. SR remains the normal default. MI is selected only when
SR catalogue temperature limits are exceeded and validated MI catalogue data is
available for the selected vendor.

MI is intentionally kept as a separate calculation path because MI cable
engineering uses different selection logic, factory heater-set constraints,
sheath-temperature review, cold lead and hot-cold joint considerations, series
resistance behavior, and circuit design rules.

The current SR calculation module includes:

- Project setup data entry.
- Input Excel upload and validation.
- Confirmed-line calculation.
- Conduction-based heat-loss calculation with insulation conductivity evidence.
- Heat-loss safety factor application.
- SR vendor catalogue filtering and tracer selection.
- Straight-run SR parallel selection up to the configured project cap, currently
  no more than four runs.
- Pipe-size guided constructability warnings for small-bore parallel SR
  arrangements.
- Voltage scenario handling for low-voltage heat delivery, nominal display, and
  high-voltage current checks.
- Per-circuit current and breaker sizing.
- Termination allowance handling as ordered SR length, not energized heat
  delivery length.
- Per-line and consolidated BOQ generation.
- Cable schedule generation from the active SLD/power-distribution model.
- SLD graph generation and SLD PDF export.
- Structured diagnostics when a line cannot receive a suitable SR tracer.
- Automatic MI fallback when SR temperature limits are exceeded.
- Validated MI family/heater/cold-lead catalogue selection.
- MI resistance-temperature correction using heater-level TCR values, with
  alloy factor table fallback where available.
- Single-phase MI heater-set current, power, breaker, BOQ, cable schedule, and
  SLD output.
- Bounded identical multi-set MI selection when one heater set cannot meet the
  required heat within per-set electrical limits.

The current SR calculation module does not yet include:

- Full external convection and radiation heat-transfer calculation.
- Integrated k(T) insulation conductivity solver.
- Vendor or standard heat-loss table interpolation.
- SR vendor curve-point interpolation as the primary power-output basis.
- Multi-layer insulation thermal resistance.
- Recalculation of load, BOQ, or cable size from manual SLD tracer overrides.
- Three-phase MI star/delta circuiting.
- Mixed MI heater optimization.
- MI line zoning with independent temperature sensors or zone-specific control.
- Calculated MI sheath/surface temperature for final T-class approval.
- Physical JB terminal/gland capacity validation for grouped MI cold leads.

The cold cable sizing module is now implemented. See Section 10B.

These deferred items are planned as future enhancements and should not be
assumed to be active unless explicitly released.

## 3. Typical User Workflow

The normal calculation workflow is:

1. Open the project workspace.
2. Select a project in the Project Data tab.
3. Enter or verify project setup values, including cold cable basis fields.
4. Save the project setup, or upload an input file from the same workspace. If
   the upload is started after changing project setup values, the visible setup
   values are saved before the calculation runs.
5. Upload the input Excel file.
6. Review the upload validation result.
7. Confirm valid imported rows when required.
8. Let the calculation run.
9. Review Calculation Results.
10. Review SR Selection Diagnostics and MI Selection Records, if any lines were
    not assigned a suitable heating cable.
11. Review Cold Cable Sizing results. Check sizing status, voltage drop, fault
    protection, and any review notes for each branch.
12. Review BOQ.
13. Review Cable Schedule, which now includes cold cable columns.
14. Review the Single Line Diagram.
15. Export required Excel or PDF outputs.

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
| Allowed voltage drop for cold cable (%) | Maximum permissible voltage drop from the MCB to the heating cable cold-end connection, as a percentage of the nominal supply voltage. | Used by the cold cable sizing engine. The engine selects cable sizes such that the total series voltage drop across trunk and outgoing segments does not exceed this value. See Section 10B for the full cold cable sizing basis. |
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
| Allowed Spiral Factor | Legacy maximum SR spiral/duty factor. | Current project default is 1.0 because the preferred basis is straight tracing. Higher values should be used only when spiral installation is intentionally accepted. |
| Installation with spiral wrap | Whether spiral installation is allowed. | If disabled, each selected straight run must have a heat-duty ratio not more than 1.0. |
| SR parallel run basis | Constructability basis for straight parallel SR tracing. | Default pipe-size guided basis prefers 1 run below 1 in, 2 runs below 2 in, 3 runs below 3 in, and up to 4 runs from 3 in upward. |
| Max. SR parallel runs | Absolute project cap for SR straight runs. | Default and current MVP maximum is 4. Designs exceeding the pipe-size preference are flagged for review rather than silently rejected. |
| Margin on tracer length (%) | Design margin applied to heated tracer length. | This margin is applied before termination allowance is added. |
| Termination margin (in mm) | Installation allowance per circuit for termination. | Added to ordered SR cable length per circuit. It is not treated as energized heat-delivery length. |
| Safety Factor on Heat Loss (> 1.0) | Safety factor applied to base heat loss. | The result called Design Heat Loss is base heat loss multiplied by this factor. |

Important distinction:

- SR spiral factor is now treated as a heat-duty ratio for selection evidence.
- For straight SR tracing, installed length is not reduced below one full run
  per trace. Multiple straight SR runs multiply the full heated route length.
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
13. Run cold cable sizing for all active feeder branches using the confirmed SLD topology.
14. Persist cold cable sizing results.
15. Make results available to the Result, BOQ, Cable Schedule, Cold Cable, and SLD tabs.

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

### 9.4 Power Output and SR Duty Ratio

For each candidate tracer, the module calculates power output at the maintain
temperature using the vendor polynomial:

`Power = A*Maint_T² + B*Maint_T + C`

The heat-delivery power is voltage-corrected using the low-voltage scenario.

The legacy single-run heat-duty factor is calculated from:

`Duty Factor = Design Heat Loss / Low-Voltage Heat-Delivery Power`

For SR parallel tracing, the module tries straight run counts from 1 to the
project cap, currently no more than 4:

`Per-Run Duty Ratio = Duty Factor / SR Parallel Run Count`

The module requires this per-run duty ratio to be not greater than the project
Allowed Spiral Factor. If spiral wrap is not allowed, the per-run duty ratio
must not exceed 1.0.

For straight tracing, the ordered heated length is not shortened when duty
ratio is below 1.0. One selected run still means one full heated route. Two,
three, or four selected SR runs mean two, three, or four full straight passes.
The project records constructability warnings when the selected run count
exceeds the pipe-size guided preference.

If no candidate row satisfies the spiral factor limits, the line appears in SR
Selection Diagnostics with reason code `NO_SPIRAL_FACTOR_MATCH`. The diagnostic
row records the attempted straight-run counts, the best catalogue candidate at
the configured run cap, and the maximum heat delivery available at that cap.

### 9.5 Selected Tracer and Alternate Tracers

After filtering and sizing, candidate tracers are ranked by:

1. Lowest SR parallel run count.
2. Lowest ordered tracer length with margin.
3. Lower nominal power output as the secondary sort.

The first row becomes the generated selected tracer. Remaining valid rows are
stored as alternate tracers.

The result page and SLD inspector label the selected value as SR duty ratio /
runs instead of treating every value as a spiral instruction. This is deliberate:
for the current straight-run basis, a duty ratio below 1.0 does not shorten the
installed cable; it only indicates heat-delivery margin for a full straight run.

Alternate tracer rows are available for review and SLD tracer override
workflows. However, selecting an alternate in the SLD is currently review-only.
It does not recalculate load, BOQ, cable schedule, or breaker sizing.

### 9.6 Recent SR Straight-Run Closure Basis

The current SR selector reflects a shift away from spiral-first design. The
project setup still contains the legacy Allowed Spiral Factor field because
some projects may permit spiral installation, but the intended default basis is
straight tracing with Allowed Spiral Factor set to 1.0.

The selector now evaluates SR heat delivery in this order:

1. Filter catalogue rows by family, temperature, hazardous-area, gas group,
   temperature class, and voltage compatibility.
2. Calculate low-voltage heat-delivery power from the stored vendor polynomial.
3. Try straight SR run counts from 1 up to the project cap.
4. Reject a candidate only when the per-run duty ratio exceeds the allowed
   limit or, where spiral wrap is disabled, exceeds 1.0.
5. Keep the simplest acceptable run count for each catalogue row.
6. Rank valid candidates by run count, ordered cable length, and power fit.

There is no lower duty-ratio rejection for straight tracing. A duty ratio of
0.70 does not mean 70 percent of a cable is installed. It means one full
straight run has heat-delivery margin at the checked condition.

The Max. SR parallel runs field is intentionally limited in the project setup
UI to values 1 through 4. Server-side validation also enforces this range in
case a browser payload is modified manually.

### 9.7 SR Result, Export, and SLD Review Labels

Recent result labels avoid presenting every SR duty calculation as a physical
spiral instruction:

- The result page shows SR Duty / Runs.
- Result export includes both Spiral Factor and SR Duty Ratio for backward
  readability while making the active interpretation clear.
- Selected SR rows show SR parallel run count and constructability warnings.
- The SLD tracer inspector shows selected tracer UID, SR duty ratio, SR run
  count, SR run basis, current per circuit, line current, total load, and
  constructability warning.
- SLD tracer nodes display the selected tracer model/UID rather than the
  generic label "Heat Tracing Cable".
- Selection diagnostics for `NO_SPIRAL_FACTOR_MATCH` include attempted run
  counts, best available catalogue candidate, best per-run duty at the run cap,
  and maximum heat delivery at the run cap.

This makes SR calculation results reviewable before the cold-cable module uses
the circuit count, current, and SLD topology as its input basis.

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

For a single SR run, the number of circuits is calculated from line maximum
current divided by the allowed current per circuit, rounded up.

For multiple straight SR runs in the current MVP, each physical SR run is
treated as independently protected. Therefore two straight SR runs create two
one-circuit branches, three straight runs create three branches, and so on.
This is a conservative design basis for fault isolation and review clarity.

This SR multi-run topology intentionally mirrors the clarity of the MI
multi-set topology. It does not yet optimize grouped feeders or shared upstream
field junction boxes. Those optimizations belong with the cold-cable sizing,
voltage-drop, and panel-coordination module because they depend on cable size,
route length, voltage drop, and protective-device coordination.

For SR parallel runs, the current values shown in the SLD inspector distinguish
between per-circuit current and total line current. This distinction is
important before the cold-cable module is developed because each straight run
may become a separate protected feeder path.

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

## 10A. MI Automatic Fallback Basis

MI calculation is not a manual user-selected mode in project setup. The normal
principle is:

- Use SR by default.
- Use MI automatically only when the line temperature exceeds the SR catalogue
  suitability limit.
- Keep MI alternatives visible for SLD review where an MI candidate is
  available, but do not silently replace a valid SR design for non-temperature
  reasons.

### 10A.1 MI Catalogue Gate

MI selection uses only catalogue families marked as validated. A family should
be validated only after the source document, family limits, heater resistance
codes, conductor/TCR data, and cold-lead options have been reviewed.

If MI rows exist in the database but are not validated, the line appears in MI
Selection Records with a rejection reason. This is intentional. The application
must not select unreviewed MI catalogue data.

### 10A.2 MI Heater-Set Selection

The MVP MI selector evaluates factory heater sets. The selected output includes:

- MI family and heater part number.
- Heated length.
- Cold-lead option and cold-lead length.
- Power density in W/m.
- Nominal power.
- Nominal current per heater set.
- Cold-start current per heater set.
- T-class review status.

If one heater set cannot provide enough heat within per-set current and
watt-density limits, the MVP can select multiple identical heater sets. For
example, a line may require three identical MI heater sets. Each set is counted
separately in BOQ and appears as a separate protected branch in the SLD.

### 10A.3 MI Electrical Topology

Each selected MI heater set is treated as independently protected. A three-set
MI result is therefore shown as three one-circuit branches, each with its own
MCB path. This is different from SR grouping logic, where multiple circuits may
be represented under a shared distribution branch.

The SLD currently represents electrical protection truth first. It does not yet
try to optimize physical consolidation of multiple MI cold leads into one shared
field junction box.

### 10A.4 MI T-Class Review

The MI result shows T-class status as review evidence. The published maximum
sheath temperature of an MI family is a cable rating/survival limit, not the
calculated operating sheath temperature for the installed circuit.

Therefore, the MVP does not claim final T-class approval from catalogue maximum
sheath temperature alone. Final hazardous-area approval requires project
engineering review and, in a later module, a proper sheath/surface-temperature
calculation or vendor-confirmed basis.

### 10A.5 MI MVP Review Boundaries

The following items are not yet calculated by the MI MVP:

- Physical JB terminal capacity for multiple cold leads.
- Gland count and junction-box internal capacity.
- Full cold-cable sizing from distribution board to field devices.
- Upstream panel coordination.
- Voltage-drop optimization.
- N-1 thermal redundancy.
- Mixed heater combinations.
- Line zoning and independent RTD/control behavior.

If one heater set trips in a multi-set MI design, the remaining heater sets may
remain energized if their protection is independent. That remaining energized
capacity should be treated as circuit-continuity information, not as proof that
the line still satisfies the full heat-loss requirement.

## 10B. Cold Cable Sizing Module

### 10B.1 Purpose and Scope

The cold cable sizing module sizes the upstream electrical conductors that carry
power from the distribution board or MCC to the field junction boxes and to the
heating cable cold-end connections.

Cold cables are conventional power cables — the same family used throughout
industrial power distribution — that connect the electrical panel to the heat
tracing field circuits. They are called cold cables to distinguish them from the
heating cables (SR or MI) that form the actual tracing element.

The cold cable module is the third major calculation step in EHT Office, after
heat loss and SR/MI tracer selection. The module reads the confirmed SR/MI
electrical outputs — circuit count, per-circuit current, breaker size, and SLD
topology — and produces sized cold cable specifications for each feeder segment.

The cold cable module does not recalculate heat loss, re-select heating cables,
or modify the SR/MI calculation. It is a downstream consumer of that stable output.

### 10B.2 What the Cold Cable Module Calculates

For every feeder segment in the active SLD topology, the module produces:

| Output | Meaning |
| --- | --- |
| Cable type and size (mm²) | Selected conductor cross-section for this segment |
| Core count | 3-core for single-phase circuits, 4-core for three-phase trunk feeders |
| Derated ampacity (A) | Current-carrying capacity after temperature and grouping correction |
| Ampacity margin (%) | Headroom between operating current and derated ampacity |
| Voltage drop (%) | Calculated voltage drop for this cable segment |
| Total path voltage drop (%) | Sum across all series segments to the tracer |
| Load-end voltage (V) | Supply voltage minus total series voltage drop |
| VD status | Pass or fail against the project allowable voltage drop |
| Fault protection status | Whether the MCB can trip instantaneously on a worst-case fault |
| Earth loop status | RCD provision status and review notes |
| Conductor mass (metric tonnes) | Material takeoff basis per branch |
| Sizing status | Selected, Review Required, or Unsizeable |

### 10B.3 Cold Cable Sizing — Step by Step

The sizing engine works through the following checks for each feeder segment.
Each step can only increase the cable size. No step reduces a size chosen by
an earlier step.

#### Step 1 — Resolve Active Cable Lengths

The engine resolves the active cable length from three possible sources in
priority order:

1. Manual override: a length entered in the cable schedule or SLD inspector.
2. Topology edit: a length set when a combine, downstream JB, or attach-JB
   topology edit was applied.
3. Project default: the project setup circuit or loop length assumption.

The source is recorded as the length basis. Results based on a project default
will carry a Review Required note until the user confirms or updates the length.

If no length is available, the branch receives a Length Missing status and no
sizing is attempted.

#### Step 2 — Ampacity (current-carrying capacity)

The cable must carry the maximum continuous operating current without overheating.

The catalogue ampacity is adjusted for:

- Site ambient temperature, using the formula:

  `K_temp = sqrt((T_max_conductor - T_site) / (T_max_conductor - T_ref_catalogue))`

  where `T_max_conductor` is 90°C for XLPE or 70°C for PVC, `T_site` is the
  project maximum ambient temperature, and `T_ref_catalogue` is the temperature
  at which the catalogue ampacity was published, typically 30°C.

  Reference: IEC 60364-5-52 temperature correction factors.

  Example: XLPE cable, 40°C site ambient, 30°C catalogue reference:
  `K_temp = sqrt((90 - 40) / (90 - 30)) = sqrt(50/60) = 0.913`

- Grouping and spacing: the project field Cable Grouping Derating Factor
  (`K_group`) allows the user to enter an overall derating factor for the
  cable laying arrangement.

  `Available_ampacity = Catalogue_ampacity × K_temp × K_group`

The engine selects the smallest standard cable size whose derated ampacity
equals or exceeds the circuit operating current.

Note: the cold cable is sized for operating current, not starting current.
The starting current is transient and the MCB is already selected to handle it.

#### Step 3 — Voltage Drop

The cable must deliver adequate voltage to the heating cable terminals.

EHT heating cables are resistive loads (power factor 1.0). Conductor resistance
is corrected from the catalogue reference (20°C) to operating temperature using
the temperature coefficient of resistance, per IEC 60228:

`R(T) = R_20 × (1 + α × (T_op - 20))`

where α is 0.00393/°C for copper. Aluminium cold-cable sizing is deferred in
the current module.

Voltage drop formulas:

- Single-phase 3-core: `VD (V) = 2 × I × R(T) × L`
- Three-phase 4-core trunk: `VD (V) = sqrt(3) × I_phase × R(T) × L`

The total path voltage drop is the sum of trunk and outgoing segment drops.
The load-end voltage is: `V_load = V_nominal - VD_4C - VD_3C`.

#### Step 4 — Optimisation for Three-Phase Distribution Branches

When the SLD topology includes a 4-core trunk cable feeding a 3-phase JB
with outgoing 3-core branches, the engine systematically searches all
ampacity-qualified cable combinations and selects the pair that minimises
total conductor volume, which is directly proportional to copper tonnage:

`Conductor_volume_proxy = 4 × A_4C × L_4C + N_out × 3 × A_3C × L_3C`

where `A_4C` and `A_3C` are the selected conductor cross-sections, `L_4C` and
`L_3C` are the respective cable lengths, and `N_out` is the number of active
outgoing circuits from the 3-phase JB.

This optimisation distributes the voltage drop budget between the trunk and
outgoing cables to find the most material-efficient combination that still
satisfies the total path VD constraint. A lower trunk VD leaves more budget
for the outgoing cables, and vice versa — the optimiser finds the minimum-mass
pair, not just the minimum-size pair.

For direct single-phase branches (MCB to 3-core cable to 1-phase JB), no
optimisation is needed. The full project VD allowance is available for the
single cable segment.

#### Step 5 — Fault Protection (Phase-to-Phase on 4-Core Trunk)

The MCB must trip instantaneously if a phase-to-phase short circuit develops
at the far end of the 4-core trunk.

The worst-case fault current is:
`I_fault = V_line_to_line / (2 × R(T) × L)`

For the MCB to trip instantaneously (within 0.4 seconds per IEC 60364-4-41):
`I_fault >= k_curve × I_breaker`

where `k_curve` is the lower bound of the MCB characteristic range:
Type B → 3×, Type C → 5×, Type D → 10×.

If the fault current does not meet the threshold, the engine upsizes the 4-core
cable until the check passes.

#### Step 6 — Earth Fault on Single-Phase Outgoing Circuits

Earth faults on the single-phase outgoing circuits are handled primarily by
Residual Current Device (RCD) when enabled in project setup.

When an RCD is present, the MCB earth-loop check is a secondary verification.
If the check is borderline, the result is Review Required rather than a hard
rejection. When no RCD is provided, the MCB is the sole earth fault protection
and the check becomes a hard sizing gate.

The fault current for the 3-core outgoing circuit is calculated as:
`I_fault = V_phase / (2 × R(T) × L)`

Note: tracer PE-path resistance is excluded from this calculation because
SR braid and MI sheath resistance data are not yet in the heating cable
catalogues. The calculation therefore overestimates the fault current and
is non-conservative for the earth loop check. All results carry a review
note flagging this limitation.

### 10B.4 Project Setup Fields for Cold Cable Sizing

The following project setup fields control cold cable sizing:

| Field | Meaning | User Guidance |
| --- | --- | --- |
| Cable Standard | Design standard for cable catalogue data | Default is IEC 60502-1. |
| Cold Cable Conductor Material | Conductor material for all cold cables | Copper only in the current cold-cable module. Aluminium is deferred. |
| Cold Cable Insulation Type | Cable insulation specification | Default is XLPE. PVC available for non-hazardous, lower-temperature applications. |
| Cable Installation Method | Installation arrangement (IEC 60364-5-52 code) | Default is Method E (multi-core on open cable tray). |
| Cable Grouping Derating Factor | Overall derating for grouping and spacing | Enter 0.25–1.0. A value of 1.0 means no grouping derating. |
| Minimum Cold Cable Size | Project contractual minimum conductor size | Default is Calculated (no floor). Set 2.5 mm² or higher if the project specification requires it. |
| MCB Characteristic Curve | Trip curve type for heating circuit MCBs | Default is Type C. Use Type B for pure resistive SR loads. Type C for MI or SR circuits with cold-start current. |
| RCD Provided | Whether all heating circuits have a Residual Current Device (RCD) | Default is Yes. All EHT circuits should have RCD protection. If unchecked, the MCB earth-loop check becomes a hard sizing gate instead of a secondary verification. |

The project form shows live cold-cable catalogue readiness by installation
method for the selected cable standard, conductor material, and insulation type.
In the current seed catalogue, Method E has validated IEC/Cu/XLPE 3C and 4C
rows. Methods B2, C, D1, and D2 remain selectable so the project engineering
basis is visible, but cold-cable sizing will be reported as unsizeable until
matching catalogue rows are added and validated.

### 10B.5 Understanding the Voltage Drop Result

The project allowable voltage drop sets the maximum permissible voltage drop
between the MCB and the heating cable cold-end connection.

For a direct circuit (MCB → 3-core cable → 1-phase JB → tracer), the full
allowable drop is available for the single cable run.

For a distributed circuit (MCB → 4-core trunk → 3-phase JB → 3-core outgoing
→ 1-phase JB → tracer), the voltage drop is shared across two cable segments.
The engine optimises how the allowance is distributed by finding the cable pair
with minimum conductor volume that keeps the sum of both drops within the limit.

The load-end voltage is shown in absolute volts. For SR cable, the heating cable
power output at this terminal voltage may differ from the design heat delivery
power calculated at the low-voltage scenario. This cross-check is a manual
engineering step.

### 10B.6 Sizing Status

Each cold cable result carries one of four statuses:

**Selected**: All checks pass. Ampacity, voltage drop, and fault protection
requirements are satisfied.

**Review Required**: The calculation completed but one or more conditions require
engineering review. Common reasons include: RCD not provided and earth loop
check is borderline; cable length is based on a project default; tracer
PE-path resistance was not available for the earth loop check.

**Unsizeable**: No catalogue cable combination satisfies all constraints.
Common causes: route length too long for the voltage drop allowance; maximum
site ambient too close to the cable conductor temperature limit; no catalogue
rows available for the selected material and installation method.

**Length Missing**: No cable length is available for the branch. Sizing cannot
proceed. Enter a length in the cable schedule or via the SLD cable length
override field.

### 10B.7 Limitations and Deferred Scope

The following items are not calculated in the current cold cable module:

- Tracer PE-path resistance in the earth loop calculation (deferred pending
  SR/MI catalogue data addition).
- Aluminium conductor sizing (deferred; current catalogue path is copper only).
- Short-circuit withstand verification (minimum cable cross-section for the
  prospective short-circuit current at the MCB).
- Phase balancing across 3-phase JB outgoing circuits (all circuits currently
  assumed balanced for the 4-core trunk current).
- Route-aware cable length from a 3D model or layout drawing.
- Panel loading schedule and phase-bus current totals.
- MI cold-lead integration with upstream cold cable voltage drop budget.

These limitations are noted as review notes on affected results.

### 10B.8 What Must Be Reviewed Before Issuing Cold Cable Results

1. All branches have a measured or topology-edit cable length. Project-default
   lengths are engineering assumptions and should not be used for procurement.
2. Sizing status is Selected or Review Required (not Unsizeable).
3. All Review Required notes are read and assessed.
4. Total path voltage drop is within the project allowable limit for all branches.
5. Load-end voltage is acceptable for the heating cable type (SR or MI).
6. Fault protection status is Pass for all 4-core trunk cables.
7. Earth loop status is acceptable for all 3-core outgoing circuits.
8. RCD provision basis matches the project protection philosophy.
9. Conductor mass output has been passed to the material takeoff engineer.
10. Any topology edit or cable length override made after the initial cold cable
    run has triggered an updated sizing result for the affected branch.

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

For MI-selected lines, BOQ includes MI-specific quantities such as MI heater set
count, MI heated length, and MI cold-lead length. Multiple MI heater sets are
counted as multiple factory heater sets.

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
- Heating Cable Length.
- SR and MI result/load/length split where MI output exists.

For SR, heating cable length is the ordered SR length and includes termination
allowance. For MI, heating cable length is the selected MI heated length and
excludes cold leads.

### 13.2 Per-Line Design Summary

The per-line table includes:

- Line ID and service information.
- Design Heat Loss.
- Base heat loss and heat-loss safety factor.
- Conductivity method evidence.
- Selected tracer.
- Heating cable type, normally SR or MI.
- Tracer override status, if an SLD override exists.
- SR duty ratio and SR straight-run count.
- Breaker size.
- Circuit count.
- Operating and starting current per circuit.
- Total connected load.
- Heating cable length.
- MI cold-lead length where MI is selected.
- Alternate tracer list.
- MI option status where available.

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
- Reason evidence, including attempted SR run counts for heat-duty failures.

This table is intended to prevent rejected lines from being missed.

### 13.4 MI Selection Records

The MI Selection Records table shows selected, available-alternative, and
rejected MI outcomes.

For selected MI records, the table shows heater part number, cold-lead option,
heater set count, heated length, power density, total nominal power, nominal
current per heater set, cold-start current per heater set, and T-class review
status.

For rejected MI records, the table shows the primary rejection code, rejection
message, diagnostic evidence, and suggested next action.

When multiple heater sets are selected, the result should be read as multiple
independently protected factory heater sets serving the same process line.

## 14. Result Excel Export

The result Excel export contains:

| Worksheet | Contents |
| --- | --- |
| Line Results | Main per-line calculation summary. |
| Selection Diagnostics | Lines where heat loss was calculated but SR tracer selection failed. |
| Power Distribution | Branch-level power-distribution rows. |
| Alternate Tracers | Valid alternate tracer options by line. |
| MI Selection | Selected, alternative, and rejected MI records by line. |

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
- Heating Cable Type.
- Heating Cable Length (m).
- Heating Cable Length Basis.
- Ordered SR Tracer Length incl. Termination Allowance (m).
- MI Heated Length excl. Cold Leads (m).
- MI Cold Lead Option.
- MI Cold Lead Length (m).
- MI Design Basis Notes.
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
- Cable specification and cold cable size calculated by the sizing engine.
- Cable length.
- Connected from.
- Connected to.
- Line IDs.
- Purpose.
- Manual override status, where applicable.
- Manual size review status, where a manual cable specification has been entered.
- Route and remarks fields.

If manual SLD topology or cable length overrides exist, the cable schedule may
show the active manual state or a warning that review is required.

### 16.1 Manual Cable Size Review

When a user manually enters a cable specification for a schedule row, the
application compares the manually entered size against the calculated cold cable
result for that branch. The comparison produces one of three review statuses:

| Status | Meaning |
| --- | --- |
| Acceptable | The manually entered conductor size is equal to or larger than the calculated cold cable size. |
| Review Required | The manual size could not be compared with the calculated size, or the manual core count does not match the required core count for the segment (3-core for outgoing, 4-core for trunk). |
| Undersized | The manually entered conductor size is below the calculated cold cable size. This is a warning that the manual specification may not satisfy ampacity or voltage-drop requirements. |

The cable schedule summary card shows a count of rows with Review Required or
Undersized status. The Excel cable schedule export includes the Manual Size
Review and Manual Size Review Note columns.

A manual cable size that passes the review does not mean that the sizing is
final — the review check compares conductor cross-section and core count only.
The cold cable sizing result still reflects the engine-calculated values and
should be the primary engineering basis.

## 17. Single Line Diagram Tab

The Single Line Diagram tab displays the stored SLD graph for the project.

The graph is based on persisted calculation output and branch data. It includes
component metadata such as line identity, branch index, circuit index, selected
tracer information, SR calculation basis, and MI heater-set evidence where MI
fallback has been selected.

### 17.1 SLD Tracer Review

Tracer nodes carry selected tracer metadata and alternate tracer metadata. If
alternate options are available, users can review them from the SLD workflow.

Current limitation:

- SLD tracer overrides are review-only.
- A tracer override does not currently recalculate current, breaker size, BOQ,
  cable schedule, or heat loss.
- MI available-alternative overrides are also review-only until the calculation
  engine consumes overrides as recalculation input.

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

Candidate SR rows could not satisfy the configured duty-ratio/run-count limits.
For straight tracing, this usually means even the configured run count could not
meet the required heat duty, or the project allowed duty/spiral limit is more
restrictive than the available catalogue candidates.

User actions:

- Confirm that spiral wrap is allowed if project practice permits it.
- Review Allowed Spiral Factor.
- Review Max. SR parallel runs and the SR parallel run basis.
- Review the diagnostic evidence showing attempted run counts and the best
  available candidate at the configured run cap.
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
9. MI Selection Records are reviewed where MI fallback is triggered.
10. Design heat loss and base heat loss are reasonable.
11. Selected tracer or MI heater family is acceptable for the service.
12. SR duty ratio, straight-run count, and any constructability warning are
    acceptable for the line size and installation practice.
13. Current values are understood as per-circuit or per-heater-set values.
14. Ordered SR length is understood to include termination allowance.
15. MI heated length is understood to exclude cold leads.
16. Circuit count and breaker sizes are acceptable.
17. BOQ quantities are reasonable.
18. Cable schedule lengths are reasonable.
19. SLD topology matches the intended distribution philosophy.
20. Any manual SLD edit or tracer override is reviewed.
20a. If any cable schedule row has a manual cable specification, the Manual
    Size Review status is Acceptable. Undersized or Review Required statuses
    must be resolved before procurement.
21. Cold cable sizing results are reviewed: all branches are Selected or
    Review Required, not Unsizeable or Length Missing.
22. Cold cable length basis is confirmed — project-default lengths must be
    replaced with measured route lengths before procurement.
23. Total path voltage drop is within the project allowable limit for all branches.
24. Residual Current Device (RCD) provision basis matches the project protection
    philosophy. If no RCD is provided, all MCB earth-loop checks must pass.
25. Conductor mass output has been passed to the materials engineer.
26. Exported Excel reports match the on-screen result.
27. Known limitations are acceptable for the project stage.

## 20. Known Limitations

The current calculation module is ready for SR calculation workflows and bounded
MI automatic fallback, but users should understand these limitations:

- The module supports SR calculation and a bounded MI automatic-fallback MVP.
  MI advanced design features remain future work.
- Heat loss is currently based on insulated-pipe conduction with a wind
  correction and safety factor. It is not a full convection/radiation external
  heat-transfer model.
- Standard/vendor table, integrated k(T), and fixed project basis methods are
  placeholders. They currently fall back to the mean-temperature method and
  record evidence of that fallback.
- Multi-layer insulation is not yet modeled.
- Vendor catalogue completeness affects selection. A vendor dropdown value does
  not guarantee the required SR rows exist in the database.
- SR power output is still primarily evaluated from stored A/B/C polynomial
  coefficients in the existing catalogue. These coefficients are a fitted
  engineering representation of vendor curves, not values normally published as
  A/B/C constants by vendors. Table-based SR curve interpolation is deferred.
- Blank vendor catalogue suitability fields are treated as non-blocking. This
  avoids false rejection of legacy catalogue rows, but users should curate
  catalogue data carefully for final design use.
- Resistance tolerance is a stored project field, but the current SR release
  does not yet apply a detailed resistance-tolerance current model.
- Manual SLD tracer overrides are review-only and do not recalculate electrical
  load, BOQ, breaker size, or cable schedule.
- Accessory tracer adders are empirical SR rules, not vendor-specific detailed
  installation rules.
- MI T-class status is review evidence, not a final calculated
  sheath-temperature approval.
- MI physical JB terminal capacity, gland count, and panel coordination are not
  yet calculated.
- Multi-set MI remaining energized capacity after one breaker trip is not a
  guaranteed N-1 thermal design unless a future project basis explicitly sizes
  for that case.
- Cold cable sizing is implemented for ampacity, voltage drop, fault protection,
  and earth loop. Remaining limitations: tracer PE-path in earth loop (non-
  conservative, review note applied); aluminium conductor sizing deferred;
  short-circuit withstand check not yet implemented; phase balancing across
  3-phase JB circuits assumed balanced; route-aware lengths not yet available
  from 3D model.

## 21. Recommended User Practice

For routine calculation work:

1. Use Mean insulation temperature as the heat-loss method unless a project
   specifically requires legacy comparison.
2. Keep vendor catalogue data curated and reviewed.
3. Treat SR Selection Diagnostics as mandatory review items.
4. Treat MI Selection Records as mandatory review items when MI fallback is
   triggered.
5. Do not issue results with unresolved rejected lines unless the project
   document clearly excludes those lines.
6. Use result Excel exports for engineering review and traceability.
7. Use BOQ and Cable Schedule outputs as generated quantities that still require
   normal engineering review before procurement or construction issue.
8. Record project assumptions outside the app where required by the project
   quality system.

## 22. MI Pass 1-18 Engineering Record

This section records the current MI engineering basis at the close of Pass 18.
It is included in the user guide because MI behavior affects what the user sees
in the result page, Excel export, BOQ, cable schedule, and SLD. It also prevents
future readers from confusing MVP output with a fully commercial MI design
suite.

### 22.1 Current Implemented Status

The current implemented status is:

- SR remains the default heating cable technology.
- MI is not selected from a project setup dropdown.
- MI fallback is triggered automatically when published SR catalogue
  temperature suitability limits are exceeded for a process line.
- MI selection uses only validated MI catalogue families.
- Unvalidated MI catalogue data is rejected even if rows exist in the database.
- MI selection is separate from SR selection logic.
- Selected MI results are stored as `SelectedMIHeater` snapshots, including
  catalogue references and calculated values.
- Rejected MI attempts are also stored, with diagnostic reason codes and user
  action hints.
- Available MI alternatives can be shown in the SLD tracer review workflow.
- The SLD override workflow can record an MI alternative as a review-only
  decision, but recalculation does not yet consume that override as a new design
  input.
- MI output participates in result summaries, result export, BOQ, cable
  schedule, SLD payload, and SLD PDF output.
- Multi-set MI output is supported for identical heater sets where one heater
  set cannot meet the required heat within per-set limits.
- Each MI heater set is represented as an independently protected branch in the
  generated electrical topology.

### 22.2 Design Assumptions Made During MI Passes 1-18

The following assumptions are active in the MI MVP:

| Area | Current assumption |
| --- | --- |
| Technology choice | SR is attempted first; MI is automatic only for SR temperature-limit exceedance. |
| User choice | The user does not manually choose SR or MI in project setup. |
| Catalogue authority | MI families must be marked validated before selection. |
| Catalogue provenance | MI family source document is recorded; validation remains an engineering/admin responsibility. |
| MI construction | MI is treated as a factory heater set, not a field-cut SR-style cable. |
| Phase basis | Current MI calculation path is single-phase MVP. |
| Heat-loss basis | MI uses the same calculated design heat loss as the line; no MI-specific heat-loss method is added yet. |
| Resistance basis | Heater-level TCR is the primary resistance-temperature correction. `MIAlloyTempFactor` remains available as a fallback lookup. |
| TCR ownership | TCR belongs to the heater conductor material, not the sheath/family alloy. |
| Cold-start basis | MI cold-start resistance uses the lower of startup temperature and minimum ambient where both are available. |
| T-class | T-class remains a review verdict; published maximum sheath rating is not treated as installed operating sheath temperature. |
| Multi-set basis | Multiple identical heater sets may be selected, capped by the MVP limit, when one set under-delivers heat. |
| Protection | Each MI heater set gets independent protection; current is checked per set. |
| Sensing | Shared/single-point sensing is assumed for MVP result output. Final RTD location remains project review. |
| SLD topology | The generated SLD prioritizes electrical protection truth, not physical JB consolidation. |
| BOQ | MI heater set count, MI heated length, and MI cold-lead length are reported separately. |
| Redundancy | Remaining energized sets after one trip are continuity evidence, not proof of N-1 thermal adequacy. |

### 22.3 Noteworthy Architectural Decisions

The following architectural decisions were made deliberately:

- MI was built as a separate selector/service path instead of being forced into
  the SR tracer-selection algorithm.
- Demo MI catalogue data was removed. Wrong catalogue rows are more dangerous
  than an empty catalogue.
- `is_validated` is a hard catalogue gate for MI selection.
- MI result persistence uses snapshot fields so historical results do not drift
  if catalogue data is later edited.
- MI rejected rows are persisted and displayed; rejected high-temperature lines
  are not allowed to disappear silently.
- The project setup page does not expose a manual SR/MI selector. Automation is
  based on temperature suitability.
- MI SLD override identifiers use stable heater part number and cold-lead option
  code, not transient database row IDs.
- T-class is not auto-approved by comparing published maximum sheath rating
  with the project T-class limit. The software records review evidence instead.
- Resistance-temperature correction keys off heater conductor material/TCR, not
  MI sheath alloy.
- Multi-set MI uses identical heater sets only in the MVP. Mixed heater
  optimization is intentionally deferred.
- Multi-set MI is represented as independent one-circuit branches, not as an
  SR-style grouped 3PH branch.
- The current result page and export expose MI assumptions and deferred checks
  directly to the user.
- Cold-lead terminal-capacity checks are not faked. The current schema does not
  yet store conductor count, gland count, terminal count, or JB capacity.

### 22.4 Known Limitations Specific to MI

Known MI limitations at the close of Pass 18 are:

- No vendor worked-example benchmark has yet been completed against TraceCalc,
  CompuTrace, ChromaTrace, or an approved vendor calculation sheet.
- MI T-class is review-only; the app does not yet calculate installed sheath or
  surface temperature.
- Physical JB terminal capacity is not calculated.
- Gland count and JB internal space are not calculated.
- Cold cable sizing from DB to JB is not calculated from ampacity/voltage-drop
  rules.
- Upstream panel coordination is not calculated.
- Voltage-drop optimization is not yet implemented.
- Per-cold-lead ampacity and resistance are not yet modeled at cold-lead option
  level.
- Per-heater maximum heated length is not yet modeled.
- Three-phase MI star/delta design is not implemented.
- MI star-point topology is not implemented.
- Mixed heater combinations are not implemented.
- Line zoning with independent control/RTD behavior is not implemented.
- Grouped control with independent breakers is not yet explicitly modeled.
- SLD MI overrides are review-only and do not yet drive recalculated output.
- The current MI catalogue validation workflow is admin/command driven, not a
  polished user-facing catalogue import and approval workflow.

### 22.5 What Must Be Reviewed Before Issuing MI Results

Before issuing a calculation package containing MI lines, the reviewer should
check:

1. MI catalogue family is validated from an acceptable source document.
2. Selected MI heater part number and cold-lead option are acceptable.
3. Heater set count is reasonable for the line length, heat duty, and field
   installation practice.
4. Per-set nominal and cold-start current are acceptable.
5. Independent breaker-per-set topology is acceptable.
6. T-class review status is understood and resolved outside the MVP where
   required.
7. Physical JB/cold-lead terminal capacity is reviewed manually.
8. Cold cable sizing and voltage-drop design are reviewed manually.
9. Panel loading/coordination is reviewed manually.
10. BOQ quantities are checked before procurement use.

## 23. SR Pass 19 Straight-Run Closure Record

This section records the SR closeout basis after the recent SR parallel-run
passes. It is included because it changes how users should read SR results,
diagnostics, and SLD topology.

### 23.1 Current Implemented Status

The current implemented SR status is:

- SR remains the default heating cable technology.
- Project setup defaults to straight tracing with Allowed Spiral Factor set to
  1.0.
- The Max. SR parallel runs field is limited to values 1 through 4 in the user
  interface and server-side validation.
- The selector tries one straight run first, then two, three, and four where
  permitted by the project cap.
- The pipe-size guided setting creates constructability warnings for small-bore
  lines when the selected run count exceeds the preferred value.
- A low duty ratio is no longer treated as a rejection condition. One selected
  straight run still means one full installed trace.
- Selected SR rows persist SR run count, duty ratio, run basis, per-run tracer
  length, and constructability warning.
- SR parallel runs are represented as independent protected branches in the SLD
  and power-distribution payload.
- The result tab, Excel export, SLD inspector, and diagnostic table expose SR
  duty/run evidence.
- `NO_SPIRAL_FACTOR_MATCH` diagnostics now include attempted run counts and the
  best available catalogue evidence at the configured run cap.

### 23.2 Design Assumptions Made During SR Parallel-Run Passes

| Area | Current assumption |
| --- | --- |
| Installation basis | Straight tracing is preferred. Spiral installation remains possible only when the project intentionally permits it. |
| Maximum run count | The MVP supports up to four parallel SR runs. |
| Small-bore guidance | Pipe-size guidance is a review warning, not a hard rejection, because unusual projects may intentionally accept tighter arrangements. |
| Protection | Each straight SR run is modeled as independently protected for review clarity and fault isolation. |
| Duty ratio | Duty ratio is heat-delivery evidence, not a command to install fractional cable length. |
| Catalogue power basis | Existing SR power output still uses fitted A/B/C catalogue coefficients. |
| Future SR data basis | Vendor curve-point interpolation is preferred for future hardening, with A/B/C retained as compatibility fallback. |
| Feeder grouping | Upstream grouping and shared field-junction-box optimization are deferred to cold-cable engineering. |

### 23.3 Known Limitations Specific to SR Parallel Runs

Known SR limitations after Pass 19 are:

- Parallel SR runs are electrically represented as independent protected
  branches. The MVP does not yet optimize grouped feeders or shared upstream
  distribution.
- Physical installation space around small-bore pipe is not calculated.
  Pipe-size guidance is a warning only.
- The selected SR run count does not yet drive a detailed RTD/control-zone
  model.
- SR alternate override remains review-only and does not recalculate BOQ,
  breaker size, current, or cable schedule.
- SR power output is still based on fitted polynomial coefficients rather than
  vendor-published curve-point interpolation.
- Vendor-specific accessory allowances are not yet modeled.

### 23.4 What Must Be Reviewed Before Issuing SR Parallel-Run Results

Before issuing a calculation package containing multiple SR runs, the reviewer
should check:

1. Straight-run count is physically installable on the pipe size.
2. Constructability warnings are resolved or accepted by project engineering.
3. The selected SR model is acceptable for the temperature, area, gas group,
   and project voltage.
4. Per-circuit current and total line current are both understood.
5. Independent breaker-per-run topology is acceptable for the project stage.
6. Future cold-cable sizing will revisit feeder grouping, voltage drop, and
   panel loading.
7. BOQ quantity is understood as full straight-run cable length, including
   termination allowance.

## 24. Pending Activities and Phase Assignment

The following backlog separates MVP-closeout items from future commercial
product development.

### 24.1 Priority P0 - Before External Issue of MI Results

| Activity | Reason | Status |
| --- | --- | --- |
| Validate MI catalogue data source-by-source | Prevent selection from incorrect vendor data | Pending engineering/admin review per project database |
| Complete at least one worked-example comparison per vendor | Prove numerical behavior against vendor/EPC expectation | Pending vendor output/examples |
| Review MI T-class basis for hazardous-area jobs | Current result is review evidence only | Manual review required |
| Review physical JB/cold-lead capacity manually | Current schema cannot calculate terminal/gland capacity | Manual review required |
| Review cold-cable voltage drop and panel loading manually | Next module not yet built | Manual review required |

### 24.2 Priority P1 - Cold Cable Module Status (Complete)

This item was previously tracked as **Priority P1 - Next Calculation Module**.
The cold-cable module is now implemented, with remaining work split into the
deferred coordination and capacity items below.

| Activity | Reason | Status |
| --- | --- | --- |
| Cold cable sizing module | Cable size, voltage drop, and installation deliverables | **Complete** — see Section 10B |
| Voltage-drop optimization | Minimize feeder/cold cable conductor tonnage via VD allocation | **Complete** — paired 4C/3C optimisation in engine |
| Consume active SLD topology in cable sizing | Manual topology edits affect cable quantities and sizing | **Complete** — topology and manual overrides consumed |
| Consume SR/MI independent branch topology | Cold-cable sizing respects the stabilized branch/circuit model | **Complete** |
| Panel/load coordination summary | Needed for upstream electrical review | P3 — deferred |
| Physical JB/cold-lead capacity data model | Needed before terminal-capacity gates can be honest | P2 — deferred |

### 24.3 Priority P2 - MI Engineering Enhancements

| Activity | Reason | Target phase |
| --- | --- | --- |
| Per-cold-lead option ampacity and resistance | Current fields are heater-level approximations | MI refinement |
| Per-heater maximum heated length | Some vendor limits are code-specific | MI refinement |
| Calculated MI sheath/surface temperature | Needed for stronger T-class evidence | MI refinement |
| MI line zoning | Needed for long/high-duty lines with zone-specific control | MI phase 2 |
| Grouped control with independent breakers | Reflect practical control architecture after MI output stabilizes | MI phase 2 |
| Three-phase MI star/delta and star-point topology | Needed for advanced MI arrangements | MI phase 2+ |
| Recalculate from MI SLD override | Convert review-only MI override into active design input | MI/SRD refinement |

### 24.4 Priority P2 - SR Engineering Enhancements

| Activity | Reason | Target phase |
| --- | --- | --- |
| SR vendor curve-point interpolation | Replace fitted A/B/C as the primary SR power-output basis where source curve points exist | SR refinement |
| Keep A/B/C polynomial as fallback | Preserve compatibility with existing catalogue rows during transition | SR refinement |
| Vendor-specific accessory adders | Improve valve/flange/support heat-tracing quantity evidence | SR refinement |
| SR control zoning | Needed for long lines or lines with meaningful temperature variation | SR phase 2 |
| Recalculate from SR SLD override | Convert review-only alternate tracer choice into active design input | SR refinement |

### 24.5 Priority P3 - Commercial Product Development

| Activity | Reason | Target phase |
| --- | --- | --- |
| Constant wattage cable module | Separate cable technology with different engineering behavior | Future module |
| User-facing catalogue import/governance workflow | Needed for controlled catalogue lifecycle | Commercial hardening |
| Designer/checker/approver workflow | Required for production engineering issue control | Commercial hardening |
| Revision control and calculation sign-off | Required for auditable project deliverables | Commercial hardening |
| 3D model/cable-routing integration | Connect IDF/PCF/IFC/NWD context to design review and routing | Platform expansion |
| Advanced heat-transfer models | Add convection/radiation, integrated k(T), and multilayer insulation | Calculation expansion |

## 25. Glossary

| Term | Meaning |
| --- | --- |
| SR cable | Self-regulating heating cable. |
| MI cable | Mineral insulated heating cable. In the current MVP it is selected automatically for validated high-temperature fallback cases. |
| MI heater set | Factory-engineered MI heating cable set with heated section, hot-cold transition, cold lead, and selected resistance code. |
| MI multi-set selection | Multiple identical MI heater sets selected for one process line when one heater set cannot satisfy heat delivery within per-set limits. |
| Base heat loss | Heat loss before heat-loss safety factor. |
| Design heat loss | Heat loss after applying heat-loss safety factor. Used for tracer selection. |
| Heat-loss safety factor | Project factor applied to base heat loss. |
| Conductivity method | Basis used to evaluate insulation conductivity. |
| Spiral factor | Legacy project limit used to compare required heat against available SR heat delivery. In the straight-run workflow it is read as an allowed duty limit unless spiral installation is explicitly permitted. |
| SR duty ratio | Required heat loss divided by available low-voltage SR heat delivery after considering the selected SR run count. |
| SR parallel run | Additional full-length straight SR trace installed along the same process line, currently modeled as an independently protected branch. |
| Heated tracer length | Tracer length used for heat delivery, including design length margin but excluding termination allowance. |
| Ordered SR length | Total SR cable quantity including termination allowance. |
| Termination allowance | Installation allowance added per circuit, excluded from heat delivery and current. |
| Operating current / circuit | Per-circuit current at operating condition. |
| Starting current / circuit | Per-circuit maximum/start current used for breaker sizing. |
| Connected load | Total line operating load. |
| Selection diagnostics | Stored reason why a line did not receive a selected SR tracer. |
| SLD | Single Line Diagram. |
| BOQ | Bill of Quantities. |
| Cold cable | Conventional power cable carrying electricity from the distribution board or MCC to field junction boxes and heating cable cold ends. Distinguished from heating cables (SR or MI) by the fact that it does not generate heat. |
| CC module | Cold cable sizing module — the third calculation step in EHT Office. |
| K_temp | Temperature derating factor applied to catalogue ampacity to correct for site ambient temperature above the catalogue reference temperature. Formula: sqrt((T_max_conductor - T_site) / (T_max_conductor - T_ref)). |
| K_group | Grouping derating factor entered by the user to account for cable spacing and laying arrangement. Multiplied with K_temp to give the total derating applied to catalogue ampacity. |
| RCD | Residual Current Device. A protective device that trips at low earth fault current, typically 30 mA for industrial equipment protection. When an RCD is present on a heating circuit, the MCB earth-loop check for the 3-core outgoing circuit is a secondary verification, not a primary sizing gate. All EHT circuits should be designed with RCD protection as a primary requirement. |
| Load-end voltage | The supply voltage minus the total series voltage drop across the cold cable path (trunk + outgoing). Reported in absolute volts as evidence that adequate voltage reaches the heating cable cold end. |
| Conductor volume proxy | The cost function used in the 3-phase JB cable pair optimisation: 4 x A_4C x L_4C + N_out x 3 x A_3C x L_3C. Minimising this proxy minimises conductor cross-section times length, which is directly proportional to copper tonnage and procurement cost. |
| 3phJB branch | A power distribution branch where an MCB feeds a 4-core trunk cable to a 3-phase junction box, which in turn feeds 3-core outgoing cables to individual 1-phase junction boxes and tracers. Requires the paired optimisation algorithm. |
| 1phJB branch | A power distribution branch where an MCB feeds a 3-core cable directly to a 1-phase junction box and tracer, with no intermediate 3-phase junction box. Uses the simpler direct sizing algorithm. |
| CP cable | Constant power heating cable — fixed wattage per metre regardless of temperature. A planned future module in EHT Office. |

## 26. Calculation Verification Report

### 26.1 Purpose and Access

The Calculation Verification Report is a read-only engineering evidence document that
presents persisted calculation data in a structured, hand-calculation-style layout. It
is intended for design review, checker sign-off, and project audit traceability.

Access the report from the Engineering Hub navigation bar, or directly at the
`/verification-report/` URL. Select a working project from the dropdown, then select
a confirmed process line to generate the report.

The report reads from persisted calculation data stored in the application database. It
does not re-run heat-loss, tracer-selection, electrical sizing, or cold cable sizing
calculations. If project inputs or setup have changed since the last calculation run,
the report will reflect the last stored calculation state, not the revised inputs.

### 26.2 Report Sections

The report is organised into five sections:

| Section | Content |
| --- | --- |
| A — Input Summary | Process line inputs (pipe size, length, insulation, temperatures) and project setup fields used in the calculation. |
| B — Thermal Calculation | Conductivity method, polynomial evaluation, wind correction factor, safety factor, base heat loss, and design heat loss per metre. |
| C — Tracer Selection | SR catalogue filtering basis, voltage correction factor, low-voltage heat delivery, duty ratio, parallel run count, alternate tracers, and MI heater selection where applicable. |
| D — Electrical Sizing | Circuit count formula, breaker size, per-circuit current, starting current, and total connected load. |
| E — Cold Cable Sizing | One or more detailed sub-steps per feeder branch: K_temp derating, K_group and ampacity selection, 4C trunk voltage drop (where applicable), 3C outgoing voltage drop, VD optimisation result, fault protection check, earth fault loop check, and branch summary. |

### 26.3 Terminal Voltage Cross-Check

Section E includes a terminal voltage cross-check step. This step computes the actual
power available from the selected heating cable at the final load-end voltage — the
supply voltage minus the total cold cable voltage drop. It then confirms whether this
power meets the design heat-loss requirement.

This cross-check closes the loop between the tracer selection (which uses the
low-voltage supply scenario) and the cold cable sizing (which further reduces the
terminal voltage). If the available heat delivery at the final terminal voltage is
marginally below the design requirement, the report flags the result for engineering
review. Options for resolution include increasing the VD allowance, reducing cable
route lengths, or reviewing the heat-loss safety factor.

### 26.4 Optimisation Savings Comparison

For three-phase junction box branches, the Section E report shows a comparison between
the engine's optimised cable pair selection and three fixed voltage-drop split
baselines: 25/75, 50/50, and 75/25 allocation between the 4-core trunk and 3-core
outgoing cables. The comparison shows the conductor volume proxy and the percentage
saving achieved by the optimised selection versus each fixed-split baseline.

### 26.5 Review Checklist

The verification report includes a review checklist. The checklist covers input
confirmation, thermal evidence, tracer selection, electrical sizing, and cold cable
sizing for each process line. Engineers use the checklist to confirm all evidence is
acceptable before signing off the calculation package.

The checklist items include conditional entries for MI heater lines (T-class review,
cold-lead arrangement) and cold cable sizing lines (VD compliance, fault protection,
cable length basis).

### 26.6 Printing and Export

The verification report includes a print button. Browser-native PDF generation is the
intended export format. The print stylesheet removes the navigation bar, selector panel,
and scroll progress indicator from the printed output, leaving only the report header,
calculation sections, and review checklist.
