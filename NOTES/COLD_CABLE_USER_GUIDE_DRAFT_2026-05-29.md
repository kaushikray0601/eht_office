# Cold Cable Sizing — User Guide Addition
# (To be integrated into CALCULATION_MODULE_USER_MANUAL.md)

Document status: Draft for review before integration
Section numbers assume addition after the existing Section 10 (MI Module)

---

## 11. Cold Cable Sizing Module

### 11.1 Purpose and Scope

The cold cable module sizes the upstream electrical conductors that carry power
from the distribution board (DB) or motor control centre (MCC) to the field
junction boxes (JBs) and to the heating cable cold-end connections.

Cold cables are the conventional power cables — the same family of cables used
throughout industrial power distribution — that connect the electrical panel to
the heat tracing field circuits. They are called cold cables to distinguish them
from the heating cables (SR or MI) that are the actual tracing element.

The cold cable module is the third major calculation step in EHT Office, after
heat loss calculation and SR/MI tracer selection. The module reads the confirmed
SR/MI electrical outputs — circuit count, per-circuit current, breaker size, and
SLD topology — and produces sized cold cable specifications for each feeder
segment in the project.

The cold cable module does not recalculate heat loss, re-select heating cables,
or modify the upstream SR/MI calculation. It is a downstream consumer of that
stable output.

### 11.2 What the Cold Cable Module Calculates

For every feeder segment in the active SLD topology, the module produces:

| Output | Meaning |
| --- | --- |
| Cable type and size (mm²) | Selected conductor cross-section for this segment |
| Core count | 3-core for single-phase circuits, 4-core for three-phase trunk feeders |
| Conductor material | Copper (default) or aluminium |
| Derated ampacity (A) | Current-carrying capacity after temperature and grouping correction |
| Ampacity margin (%) | Headroom between operating current and derated ampacity |
| Voltage drop (%) | Calculated voltage drop for this cable segment |
| Total path voltage drop (%) | Sum of voltage drop across all series segments to the tracer |
| Load-end voltage (V) | Supply voltage minus total series voltage drop |
| VD status | Pass or fail against the project allowable voltage drop |
| Fault protection status | Whether the MCB can trip fast enough on a worst-case fault |
| Earth loop note | GFEP status and any review notes |
| Sizing status | Selected, Review Required, or Unsizeable |
| Sizing basis | Which calculation constraints drove the final cable selection |

### 11.3 Cold Cable Sizing — Step by Step

The sizing engine works through five checks for each feeder segment. Each step
can only increase the cable size. No step reduces a size chosen by an earlier step.

**Step 1 — Ampacity (current-carrying capacity)**

The cable must carry the maximum continuous operating current of the heating
circuit without overheating.

The catalogue ampacity is adjusted for:

- Site ambient temperature: using the formula
  `K_temp = sqrt((T_max_conductor − T_site) / (T_max_conductor − T_ref_catalogue))`
  where T_max_conductor is 90°C for XLPE or 70°C for PVC, T_site is the project
  maximum ambient temperature, and T_ref_catalogue is the temperature at which the
  catalogue ampacity was published (typically 30°C).

  Example: XLPE cable, 40°C site ambient, 30°C catalogue reference:
  `K_temp = sqrt((90 − 40) / (90 − 30)) = sqrt(50/60) = 0.913`
  A cable rated 52 A at 30°C is derated to 52 × 0.913 = 47 A at 40°C.

- Grouping and spacing: the project setup field Cable Grouping Derating Factor
  (K_group) allows the user to enter an overall derating factor for the cable laying
  arrangement. This factor represents the combined effect of cables lying close together
  in a bundle, multiple layers on a cable tray, or any other installation-specific
  grouping reduction not covered by the installation method selection. The available
  ampacity for sizing is: `A_available = Catalogue_ampacity × K_temp × K_group`.

The engine selects the smallest standard cable size whose derated ampacity equals
or exceeds the circuit operating current.

Important: the cold cable is sized for operating current, not starting current.
The starting (cold-start or inrush) current is short-duration and transient. The
MCB is already selected to accommodate the starting current. Sizing cold cables
for starting current would result in uneconomically large cables.

A project minimum cable size can be configured in project setup. If set, no
cold cable smaller than the minimum will be selected, even if the calculated
minimum from ampacity is smaller.

**Step 2 — Voltage Drop**

The cable must deliver adequate voltage to the heating cable terminals.

EHT heating cables are resistive loads. The power factor of the load is 1.0 (unity),
meaning current and voltage are in phase. For resistive loads, the voltage drop
formula simplifies to:

- Single-phase 3-core circuit: `VD (V) = 2 × I × R × L`
  The factor 2 accounts for the outgoing phase conductor and the returning neutral
  conductor, both of which carry the same current.

- Three-phase 4-core trunk feeder: `VD (V) = √3 × I_phase × R × L`
  The factor √3 is a property of balanced three-phase geometry. The current used
  is the per-phase current, which equals the per-circuit operating current when the
  load is balanced across the three phases.

In both formulas, R is the conductor resistance per metre (in ohms) at the
estimated operating temperature, and L is the cable route length in metres.

The conductor resistance increases with temperature. The engine corrects R from
the catalogue reference temperature (20°C) to the cable operating temperature
using the copper temperature coefficient of 0.00393 per °C.

The voltage drop percentage is calculated as:
`VD_% = VD (V) / V_nominal × 100`

The load-end voltage is:
`V_load = V_nominal − VD_4C (V) − VD_3C (V)`

For series segments — a 4-core trunk from the MCB to a 3-phase JB, followed
by a 3-core outgoing from the JB to the 1-phase JB — the voltage drops add.
The total path drop must be within the project allowable voltage drop.

**Step 3 — Optimisation for Three-Phase Distribution Branches**

When the SLD topology includes a 4-core trunk cable feeding a 3-phase JB with
two or three outgoing 3-core branches, the engine optimises the cable sizes
across the two levels to minimise the total conductor volume.

Conductor volume is the cost proxy: `Cost = 4 × A_4C × L_4C + N_out × 3 × A_3C × L_3C`

where A_4C and A_3C are the selected conductor cross-sections, L_4C and L_3C
are the respective cable lengths, and N_out is the number of active outgoing
circuits from the 3-phase JB.

The engine searches the catalogue combinations systematically. It starts with
the smallest ampacity-qualified cable on both levels and finds the combination
with lowest conductor volume that also satisfies the total voltage drop constraint.

The optimisation does not apply to single-phase direct circuits (one MCB feeding
one 3-core cable directly to a 1-phase JB and tracer). In that case, the full
project allowable voltage drop is available for the single cable segment, and
the engine simply selects the smallest qualifying cable.

When the user combines multiple single-phase circuits through a 3-phase JB via
the SLD topology editor, the optimisation runs automatically in the background
for the new combined topology. The cable schedule is updated accordingly.

**Step 4 — Fault Protection (Phase-to-Phase on 4-Core Trunk)**

The MCB must trip fast enough if a phase-to-phase short circuit develops at the
remote end of the 4-core trunk cable.

GFEP (ground fault equipment protection) does not detect a phase-to-phase fault.
The MCB must detect and clear this fault within 0.4 seconds, as required by
IEC 60364-4-41 for TN systems with a 230 V phase-to-earth voltage.

The worst-case fault current for a bolted phase-to-phase fault at the end of the
4-core trunk is:
`I_fault = V_line / (2 × R_phase × L)`

where V_line is the line-to-line voltage, R_phase is the per-conductor resistance
at operating temperature, and L is the cable length. The factor 2 accounts for
both fault-loop conductors (outgoing and returning).

For instantaneous MCB trip:
- MCB Type B (instantaneous at 3–5× In): I_fault must exceed 5× the breaker rating
- MCB Type C (instantaneous at 5–10× In): I_fault must exceed 10× the breaker rating
- MCB Type D (instantaneous at 10–20× In): I_fault must exceed 20× the breaker rating

The engine uses the lower bound of each range as the pass criterion (B→3×, C→5×,
D→10×, which corresponds to the worst case where the MCB is at the bottom of its
trip window).

If the fault current does not reach the instantaneous trip threshold, the MCB
relies on its thermal-overcurrent characteristic and may not clear the fault within
0.4 seconds. In this case, the engine upsizes the 4-core cable until the fault
current satisfies the criterion.

MCB curve selection is set in project setup. The default is Type C, which is
appropriate for EHT circuits where cold-start current produces a short-duration
current elevation above the MCB rating.

Note: IEC 60898-1 defines MCB characteristic types B, C, and D only.
There is no standardised IEC Type A. The Type C default is the most common choice
for industrial EHT panels.

**Step 5 — Earth Fault on Single-Phase Outgoing Circuits (GFEP + MCB)**

Earth faults on the single-phase outgoing circuits (3-core cable from JB to
heating cable) are handled primarily by GFEP when GFEP is enabled in project setup.

GFEP devices trip at a low earth-fault current (typically 30 mA for industrial
equipment protection). At 230 V, a 30 mA trip requires a maximum fault loop
impedance of 7,667 Ω. This condition is easily satisfied by any real fault path
on a cold cable circuit, so the GFEP protection requirement does not drive cable
sizing.

The MCB earth-loop check for the 3-core outgoing cable is therefore a secondary,
informational calculation when GFEP is present. When GFEP is absent (project
setup option), the MCB is the sole earth fault protection and the check becomes
a hard sizing gate.

Note on tracer impedance: a fault at the extreme end of the heating cable passes
through both the cold cable and the tracer element in series. The full fault loop
impedance includes the tracer element resistance. This calculation is deferred to
a later module pass, pending the addition of heating-cable PE-path resistance data
to the SR and MI catalogues. In the current pass, the earth loop check uses the
cold cable impedance only, which overestimates the fault current and is therefore
non-conservative for the earth loop check on the 3-core outgoing circuit. The
result will carry a review note flagging this limitation.

### 11.4 Project Setup Fields for Cold Cable Sizing

The following project setup fields control cold cable sizing. They are in addition
to the existing hot-engineering setup fields.

| Field | Meaning | User Guidance |
| --- | --- | --- |
| Cable Standard | Design standard basis for cable catalogue data | Default is IEC 60502-1 (international). Select the appropriate standard for the project jurisdiction. |
| Cold Cable Conductor Material | Conductor material for all cold cables in this project | Default is copper. Aluminium is available as an alternative for later project phases. |
| Cold Cable Insulation Type | Cable insulation specification | Default is XLPE. PVC may be used in non-hazardous area applications with lower operating temperature requirements. |
| Cable Installation Method | How cables are installed (IEC 60364-5-52 method code) | Select the predominant installation arrangement. Method E (multi-core on open cable tray) is the default for EHT industrial tray installations. |
| Cable Grouping Derating Factor | Overall derating factor for cable grouping and spacing | Enter a value between 0.1 and 1.0. A value of 1.0 means no grouping derating (cables are spaced as reference conditions). Lower values represent densely grouped cables. The user calculates this factor from their project-specific cable spacing, number of layers, and standard derating tables. |
| Minimum Cold Cable Size | Project contractual minimum conductor size | Default is Calculated (no minimum floor). Select 2.5 mm² or higher if the project specification or site preference sets a minimum cable size independent of the calculated result. |
| MCB Characteristic Curve | Trip curve type for all heating circuit MCBs | Default is Type C. Use Type B for pure SR loads with no meaningful cold-start current. Use Type C for MI loads or SR circuits with elevated cold-start current. Type D is reserved for unusual applications. |
| GFEP Provided | Whether all heating circuits have ground fault equipment protection | Default is Yes. All EHT circuits should have GFEP. Unchecking this field will make the MCB earth-loop check a hard sizing gate instead of a secondary informational check. |

### 11.5 Understanding the Voltage Drop Result

The project allowable voltage drop field sets the maximum permissible voltage
drop between the MCB and the heating cable cold-end connection (load point).

For a direct circuit (MCB → 3-core cable → 1-phase JB → tracer), the full
allowable drop is available for the single cable run.

For a distributed circuit (MCB → 4-core trunk → 3-phase JB → 3-core outgoing →
1-phase JB → tracer), the voltage drop is shared across two cable segments.
The engine optimises how this allowance is distributed by finding the cable pair
with minimum conductor volume that keeps the sum of both segment drops within
the project limit.

Example: 5% allowable VD, L_4C = 40 m, L_3C = 20 m, 3 circuits, 8 A per circuit.
The engine might find: 4-core 4 mm² (2.1% drop) + 3-core 2.5 mm² (2.6% drop) =
4.7% total. The conductor volume cost proxy is 4×4×40 + 3×3×2.5×20 = 640 + 450 = 1090.
Comparing alternatives: 4-core 6 mm² (1.4%) + 3-core 2.5 mm² (2.6%) = 4.0% total,
cost = 4×6×40 + 3×3×2.5×20 = 960 + 450 = 1410 (more expensive despite smaller total VD).
The 4 mm² + 2.5 mm² combination is selected.

The load-end voltage is shown in absolute volts. For SR cable performance, the
heating cable power output at this terminal voltage should be verified against
the heat duty. This cross-check is a manual engineering step; the cold cable
module records the terminal voltage as evidence but does not re-evaluate SR power
output at the reduced voltage.

### 11.6 Understanding the Sizing Status

Each cold cable result carries one of three statuses:

**Selected:** All checks pass. The cable size satisfies ampacity, voltage drop,
and fault protection requirements. The sizing basis field indicates which check
drove the final size (ampacity, VD, or fault protection).

**Review Required:** The calculation completed but one or more conditions require
engineering review before the result is used for procurement or construction.
Common reasons include:
- GFEP is not enabled and earth loop check is borderline
- Cable length is based on a project default rather than a measured route length
- Tracer PE-path resistance was not available for the earth loop check
- MCB fault protection for the 3-core outgoing circuit is marginal
- A manual SLD topology edit changed the circuit but the cold cable has not been
  re-sized since the edit

**Unsizeable:** No catalogue cable combination satisfies all constraints within
the searched size range. Common causes include:
- Route length is too long for the current voltage drop allowance — reduce length
  or increase the allowable VD percentage
- The maximum site ambient temperature is too close to the cable conductor temperature
  limit — only a higher-rated cable insulation can resolve this
- No catalogue rows are available for the selected material, installation method,
  and core count combination — check catalogue population

### 11.7 Manual Cable Length Input and Auto-Sizing

Cable route lengths entered in the cable schedule or via the SLD cable length
override field trigger an automatic cold cable re-size for the affected branch.
No manual re-run is needed.

The length basis is recorded with each result:
- **project_default:** The project setup circuit or loop length was used because no
  measured length is available. This is an engineering assumption and will carry a
  Review Required note until the user confirms or updates the length.
- **manual_override:** The user entered a specific length in the cable schedule or
  SLD inspector. This length is used without further assumption.
- **topology_edit:** The length was set when a combine, downstream JB, or attach
  topology edit was applied and a trunk cable length was entered at that time.

When project setup circuit or loop lengths change, the cold cable sizing must be
manually re-run for all branches that use project defaults. Branches with manual
or topology-edit lengths are not affected by project length changes.

### 11.8 Relationship with the SLD and Cable Schedule

Cold cable sizing results appear in:

- The Cold Cable section of the result tab (one row per feeder segment)
- The cable schedule (added columns for selected size, VD%, end voltage, ampacity
  margin, fault status, and review notes)
- SLD component labels (cable size annotation on Cable4C and Cable3C symbols)
- SLD review badges for segments with Review Required or Unsizeable status
- Excel export (cold cable sizing columns added to the existing export)

When the user performs a topology edit (combine, split, downstream JB, branch
move) and applies it, the cold cable sizing is marked stale for all affected
branches. The user should review and re-run sizing after topology edits.

### 11.9 Limitations and Deferred Scope

The following items are not yet calculated in the current cold cable module.
They are planned for future passes:

- Aluminium conductor sizing (cable type selectable but sizes not yet fully
  characterised in the catalogue)
- Short-circuit withstand verification (minimum cable cross-section for the
  prospective short-circuit current at the MCB)
- Tracer PE-path resistance in the earth loop calculation (both SR braid/shield
  and MI sheath resistance — deferred pending catalogue data addition)
- Phase balancing across 3-phase JB outgoing circuits (all circuits currently
  assumed balanced for the 4-core trunk current)
- Route-aware cable length from 3D model or layout drawing import
- Cable drum optimisation and cut-length management
- Panel loading schedule and phase-bus current totals
- MI cold-lead integration with upstream cold cable VD budget

These limitations are marked on affected results as review notes and do not
block the primary cable sizing function.

### 11.10 Engineering Notes for Reviewers

The following notes explain the engineering assumptions embedded in the cold
cable sizing calculation. These are for senior reviewers and design checkers.

**Power factor assumption:** EHT heating cables are pure resistive loads.
The power factor of the combined load seen by a cold cable feeder is unity (1.0).
The standard IEC 60364-5-52 voltage drop formula reduces to `VD = 2·I·R·L` for
single-phase and `VD = √3·I·R·L` for three-phase when power factor is 1.0,
because the reactive (inductive) component of the voltage drop is zero for
resistive loads. IEEE 515-2011 and IEC 60519-1 both treat EHT loads as resistive.
No power factor derating below 1.0 is applied in this calculation.

**Balanced load assumption for 4-core trunks:** The cold cable module assigns
balanced loading across the three phases of a 4-core trunk (each phase carries
per-circuit operating current). Phase assignment is not tracked in the current
SLD topology. The actual phase-conductor current may be higher if circuits are
not balanced across phases. Phase balancing is a future enhancement. Until it is
implemented, the per-phase VD and fault current for the 4-core trunk are
calculated on the balanced assumption. The result carries this as an assumption note.

**MCB characteristic curves and instantaneous trip bounds:** The fault protection
check uses the lower bound of the MCB characteristic range (Type B: 3× In, Type C:
5× In, Type D: 10× In) as the pass threshold. This is the most conservative
interpretation of the standard and ensures the MCB will trip instantaneously
throughout its manufacturing tolerance range.

**Trip time requirement:** IEC 60364-4-41 Table 41.1 requires a maximum
disconnection time of 0.4 seconds for TN systems where the phase-to-earth voltage
U₀ is 230 V. For a standard 400 V / 230 V TN-S system, U₀ = 230 V, so the 0.4-second
limit applies regardless of whether the supply is single-phase 230 V or three-phase
400 V. A successful instantaneous MCB trip achieves disconnection in under 50 ms,
which satisfies this requirement with a large margin.

**GFEP and the earth loop:** GFEP (ground fault equipment protection) devices
trip at approximately 30 mA earth fault current for industrial equipment protection
grade. At 230 V, a 30 mA trip requires a maximum fault loop impedance of 7,667 Ω,
which is easily satisfied by any reasonable cold cable on an EHT circuit. GFEP
therefore does not drive cable sizing — it provides protection at a threshold far
below any cable-size-dependent constraint. The MCB earth loop check remains a
secondary verification for the scenario where GFEP is not present or fails.
All EHT circuits should be designed with GFEP as a primary protection requirement
per IEEE 515-2011 Section 7.4 and IEC 60519-1.
