# eTrace — Domain Overview and Current Reality

Codex: Document status: truth-first domain overview updated on 2026-05-18.

Codex: This document deliberately separates the current code reality from the
product ambition. Earlier wording risked making future roadmap items sound like
implemented capability. This version is stricter: if the code does not provide
an end-to-end working feature today, it is described as partial, planned, or
not implemented.

## Executive Summary

Codex: eTrace is currently a development-stage Django application for
electrical heat tracing design. It has meaningful implemented modules, but it
is not yet a production-ready EHT engineering platform.

Codex: The current working engineering scope is pipeline-based self-regulating
tracer cable calculation. The application can manage project setup, import
line-list input, run SR-oriented heat-loss and tracer-selection calculations,
persist calculation evidence, show results, generate BOQ/cable schedule
outputs, and render a project-backed SLD workspace.

Codex: The application does not yet provide a production MI cable calculation
module, constant wattage cable module, full cold-cable sizing engine,
voltage-drop distribution optimizer, model-driven cable routing, or certified
standards-compliance workflow. These are roadmap items.

Codex: The current codebase is valuable because it has moved beyond a sketch:
it contains models, calculation modules, view routes, persistence, exports,
SLD topology work, IDF parsing work, and automated tests. But it should still
be described as an active engineering prototype or internal development system,
not a finished commercial design tool.

## Product Name and Scope

Codex: The working product name is eTrace.

Codex: The current scope is pipeline EHT design. Tanks, vessels, skids,
packages, and other non-pipeline objects are not currently implemented as
calculation modules. They are future scope and should be developed separately
with their own design assumptions and workflows.

Codex: Current cable technology support is SR only. MI cable and constant
wattage cable are important planned cable technologies, but they are not
available today as end-to-end calculation paths.

## Current Implemented Capabilities

Codex: The following items are implemented in the current codebase to a
meaningful degree.

| Area | Current status |
| --- | --- |
| Django application foundation | Implemented. The app has models, forms, routes, templates, static assets, and migrations. |
| Project setup | Implemented for core project design-basis fields. Projects are managed through `ManagedProject`/`ProjectData`; available projects can be filtered by user. |
| Excel line-list import | Implemented for `.xlsx` upload with validation, pending/confirmed rows, error handling, and project-scoped replacement behavior. |
| SR heat-loss calculation | Implemented for a conduction-based insulated-pipe model with insulation conductivity evidence, heat-loss safety factor, wind correction, pipe OD lookup/fallback, and accessory adders. |
| Heat-loss method selection | Partly implemented. Mean insulation temperature is the active default. Other methods are placeholders or fallbacks, not independent implemented methods. |
| SR vendor catalogue selection | Implemented for SR catalogue rows using selected vendor, catalogue suitability checks, nominal voltage compatibility, voltage correction, power output, spiral factor, and selected/alternate tracer records. |
| SR selection diagnostics | Implemented. Lines that fail after heat-loss calculation can retain rejection reasons such as missing catalogue rows, unsuitable catalogue rows, voltage incompatibility, no positive power output, or spiral factor mismatch. |
| Electrical sizing for SR | Implemented for current SR workflow at a practical level: voltage scenarios, operating/max current, circuit count, breaker sizing, and power-distribution branch records. |
| BOQ output | Implemented for current generated data. The preferred term is BOQ, meaning Bill of Quantity. |
| Cable schedule output | Implemented as an output derived from the active power-distribution/SLD topology and configured length assumptions. |
| SLD workspace | Implemented as a project-backed SLD workspace. It is not just a hardcoded drawing prototype anymore. |
| SLD layout persistence | Implemented through saved node layout records tied to project/component identity. |
| SLD validation | Implemented to check active SLD payload consistency against stored branch/tag/circuit/line data. |
| Manual SLD topology edits | Implemented for selected workflows such as combine feeders, split circuits, downstream junction box work, attach/move branch behavior, reset, and review state handling. |
| SLD PDF export | Implemented for the current SLD payload. |
| Tracer and cable overrides in SLD | Partly implemented. Overrides can be captured/reviewed, but tracer override does not yet recalculate load, BOQ, breaker, or cable schedule. |
| Calculation manual/helper page | Implemented as a rendered guide page backed by the calculation manual markdown. |
| IDF viewer foundation | Implemented in a separate app at a foundational level: IDF files/components can be parsed/stored with structured metadata. |
| Automated tests | Meaningfully present. The test suite covers many calculation, reporting, SLD, topology, and view behaviors, though organization still needs cleanup. |

## Current Partial or Limited Capabilities

Codex: These areas exist in some form but should not be oversold.

Codex: The heat-loss model is simplified. It is conduction-based through
insulation with a practical wind correction and a heat-loss safety factor. It
does not yet perform a full external heat-transfer calculation including
convection, radiation, emissivity, jacket material, solar/environmental
conditions, multi-layer insulation, or an integrated k(T) solver.

Codex: Vendor catalogue selection is only as strong as the local catalogue
data. The code has been hardened to avoid some incorrect vendor fallback and
voltage filtering behavior, but real engineering reliability still depends on
clean catalogue data and disciplined catalogue management.

Codex: SLD topology work is substantial but complex. It is a real project-backed
workspace, not merely a picture, but it is not a mature CAD/electrical design
environment. Manual edits, replay, validation, BOQ/cable-schedule consequence,
and user interpretation need continued testing and careful documentation.

Codex: Cable schedule output exists, but cold-cable engineering is not complete.
Current output uses configured DB-to-JB/JB-to-JB lengths and topology-derived
structure. It does not yet perform full cable size selection based on ampacity,
voltage drop, installation method, grouping, derating, or standards basis.

Codex: The IDF viewer is real but not yet integrated into the EHT calculation
loop. It does not yet drive line-list validation, accessory count
cross-checking, cable routing, or model-based EHT component placement.

Codex: Approval workflow is not implemented as a production workflow. Designer,
checker, and approver roles are a product requirement, but current role/status
handling is not a finished approval/sign-off system.

## Not Implemented Today

Codex: The following capabilities should be described as roadmap items, not as
current functionality.

- MI cable calculation as an end-to-end module.
- Constant wattage cable calculation.
- Full cold-cable sizing.
- Voltage-drop distribution optimization.
- Cable quantity optimization based on voltage drop and topology alternatives.
- Standards-certified IEC or IEEE compliance workflow.
- User-selectable IEC/IEEE calculation basis in project setup.
- Full convection/radiation external heat-transfer model.
- Integrated k(T) conductivity solver.
- Standard/vendor heat-loss table interpolation.
- Multi-layer insulation thermal resistance.
- Tank/vessel/skid/package EHT calculation modules.
- Model-driven heat tracing design from IDF/PCF/IFC/NWD data.
- 3D cable routing and EHT component visualization inside plant model context.
- Machine-intelligence design review.
- Production issue/revision/sign-off workflow.
- Vendor catalogue import/review workflow for non-admin users.
- Independent benchmark validation package accepted by outside reviewers.

## Users and Customer Reality

Codex: The intended first users are EHT engineers and designers at EPC
contractors and engineering consultants. This matches the current pipeline and
line-list driven workflow.

Codex: Secondary users are discipline leads, checkers, approvers, and 3D/model
reviewers. These users need traceability and review outputs, but their complete
workflow is not fully implemented yet.

Codex: Procurement and construction teams are not direct application users at
this stage. They are consumers of exported deliverables such as BOQ, cable
schedule, reports, drawings, and issue packages.

Codex: The likely first paying customer segment is EPC contractors, followed
by engineering consultants, then heat-tracing vendors. Owner-operators may be
a later customer type but are less likely to be the first commercial adopter.

## Current Inputs

Codex: Current project setup inputs include project ID, selected SR vendor,
startup/minimum/maximum ambient temperatures, area classification, temperature
class, system voltage, maximum circuit breaker size, maximum circuit breaker
loading, allowable cold-cable voltage drop field, allowed spiral factor,
spiral-wrap permission, margin on tracer length, voltage variation factor,
tracer resistance tolerance, termination margin, heat-loss safety factor,
heat-loss calculation method, RTD/thermostat type, wind speed, caution-label
interval, local isolator location, DB-to-JB cable length, and JB-to-JB loop
length.

Codex: Current line-list input is uploaded as `.xlsx`. The main line fields
include project ID, line ID, P&ID number, area, train, service type, line size,
line length, valve quantity, flange quantity, support quantity, pipe material
class, insulation material type, insulation thickness, maintain temperature,
operating temperature, design temperature, emergency supply flag, discipline,
remarks, deletion flag, and upload/confirmation status.

Codex: Current reference data includes insulation thermal conductivity
coefficients, ASME B36 pipe outside diameter data, SR vendor catalogue data,
standard circuit breaker sizes, and project-specific SLD/topology/layout data.

Codex: IDF and PCF are intended as piping isometric inputs. IFC is intended for
3D structure input. NWD or other model formats are future candidates. Today,
these model inputs are not the source of truth for the EHT calculation.

Codex: Vendor catalogue management should be controlled by admin users or a
dedicated catalogue/profile role. It should not be a general-user workflow
until there is validation, review, and versioning around catalogue data.

## Current Outputs

Codex: Current outputs include SR heat-loss evidence, selected SR tracer,
alternate SR tracer records, SR Selection Diagnostics, electrical sizing data,
power-distribution branch data, result views, Excel result export, BOQ, cable
schedule, SLD workspace, SLD validation, SLD PDF export, and SLD layout data.

Codex: These outputs are useful for internal engineering development and
review. They should not yet be represented as fully validated, externally
approved, production-grade deliverables for real project issue without further
engineering validation.

Codex: The SLD output is based on stored calculation/power-distribution data.
That is a strong current foundation. But manual SLD tracer overrides remain
review-only for downstream calculation, and manual topology edits require
review when the generated baseline changes.

## Standards and Compliance Reality

Codex: The intended first-release design language is IEC-first. IEEE can be
added later as a selectable project setup basis or project-standard option.

Codex: Current implementation has some standards-aligned engineering controls:
project design-basis fields, hazardous-area/temperature-class catalogue checks
where data exists, voltage scenario separation, breaker loading basis, and
traceable calculation evidence.

Codex: Current implementation should not be described as IEC-compliant,
IEEE-compliant, or certified. It has not yet been validated against a formal
benchmark set or independently reviewed against all clauses of the governing
standards.

Codex: The relevant reference direction is:

- IEC/IEEE 62395 series for electrical resistance trace heating systems in
  industrial and commercial applications.
- IEC/IEEE 60079-30-1 for electric resistance trace heating in explosive
  atmospheres.
- IEC 60079-14 for electrical installations in explosive atmospheres.
- IEEE 515 for industrial electric resistance trace heating.
- IEEE 515.1 for commercial electric resistance trace heating, where relevant.
- Manufacturer design guides and catalogues from nVent/Raychem and Chromalox
  as initial preferred vendor references.

Codex: Client/company standards are not part of the current design basis.

## Roadmap Direction

Codex: The roadmap remains ambitious, but it must be stated as roadmap.

Codex: MI cable is the next major calculation module. Preliminary MI models and
research notes exist, but there is no production MI calculation workflow yet.
The MI module must handle cable family data, conductor/resistance data,
temperature correction, heater-set length, series circuit behavior, cold leads,
hot-cold joints, sheath temperature, watt-density limits, voltage/current
checks, installation constraints, and manufacturer catalogue rules.

Codex: Constant wattage cable is also in scope but should be its own cable
technology module, not an SR variant.

Codex: Cold cable sizing should become a dedicated engineering module. It must
go beyond configured length assumptions and include cable type/size selection,
ampacity, voltage drop, installation derating, grouping basis, evidence, and
alignment with active SLD topology.

Codex: Voltage-drop distribution optimization should evaluate distribution
layout and cable sizing alternatives. Engineering acceptability comes first;
quantity and cost optimization come after acceptability is satisfied.

Codex: 3D model integration should eventually connect line-list data,
calculation records, SLD components, model components, and cable routing. Today,
the IDF viewer is a foundation, not a completed EHT model-integration system.

Codex: Tank, vessel, skid, package, and other non-pipeline EHT design modules
should be added later with their own geometry, input, calculation, and output
basis.

## Production-Ready Definition

Codex: eTrace is not production-ready today.

Codex: To become production-ready, it must support reliable use on realistic
projects of about 500 to 1000 heat-traced lines, preserve calculation evidence,
control project revisions, distinguish designer/checker/approver states,
support issue/sign-off workflow, maintain traceable exports, and keep result,
BOQ, cable schedule, and SLD data aligned.

Codex: There is no single published benchmark dataset that can prove correctness
for all EHT design cases. Practical validation should combine review by
experienced EPC/consulting EHT engineers, comparison with vendor responses,
comparison with vendor design deliverables, and project-style benchmark cases
built from realistic engineering examples.

Codex: A production release should not rely only on passing internal unit
tests. It also needs engineering benchmark packs, user acceptance testing,
catalogue data governance, documented limitations, migration discipline, and
repeatable project workflows.

## Commercial Reality

Codex: The likely commercial direction is a professional SaaS or
enterprise-hosted application, first targeted at EPC contractors, then
engineering consultants, then heat-tracing vendors. Owner-operators may be a
later customer segment.

Codex: This commercial direction is not yet proven by the code. The current
application is not ready to sell as a completed design platform. Its value
today is as an internal engineering prototype with several strong foundations:
SR calculation, calculation evidence, reporting, SLD topology, and model-viewer
direction.

Codex: The future differentiator should be connected traceability, not simply
heat-loss calculation. The product should eventually connect calculation basis,
catalogue selection, diagnostics, SLD, BOQ, cable schedule, model review, and
engineering sign-off.

## Known Technical Boundaries

Codex: The current heat-loss model is not a complete heat-transfer model.

Codex: The SR cable calculation is not a universal cable-selection engine.

Codex: MI cable is not implemented as a working calculation module.

Codex: Constant wattage cable is not implemented.

Codex: Cold cable sizing is not complete.

Codex: Voltage-drop distribution optimization is not implemented.

Codex: The SLD workbench is real but not yet a mature production drawing
system.

Codex: Manual tracer overrides do not recalculate downstream electrical and
quantity outputs.

Codex: 3D/model data is not yet integrated into calculation or routing.

Codex: Standards alignment is partial and should not be claimed as compliance.

Codex: Vendor catalogue data quality remains a major engineering dependency.

Codex: Test coverage is meaningful but still needs better modular organization.
The large `eht/tests.py` file should be split into domain-specific test modules
over time.

## What Should Not Be Claimed Today

Codex: The following claims should not be made about the current software:

- It is production-ready.
- It is IEC certified or IEEE certified.
- It performs complete EHT design for all cable technologies.
- It supports MI cable calculation end to end.
- It supports constant wattage cable calculation end to end.
- It performs full cold-cable sizing.
- It optimizes voltage drop or cable quantity.
- It performs full convection/radiation heat-loss modelling.
- It generates model-driven cable routing.
- It provides finished machine-intelligence design checking.
- It replaces review by experienced EHT engineers.

## Conclusion

Codex: eTrace currently stands as a serious internal development platform with
working SR calculation, persistence, reporting, BOQ, cable schedule, and
project-backed SLD foundations. It is no longer merely an idea, but it is also
not yet a finished commercial engineering product.

Codex: The honest next step is to continue building module by module while
protecting this separation between implemented capability and roadmap. MI cable
engineering, constant wattage cable, cold cable sizing, voltage-drop
optimization, model integration, approval workflow, and production validation
should be developed as explicit future modules with their own tests,
documentation, and engineering review.

Codex: The guiding principle remains traceable engineering: every important
output should show what input produced it, what rule checked it, what evidence
supports it, and what still requires human engineering review before issue.
