# Codex Handoff Note for Claude

Date: 2026-05-24  
Project: eTrace EHT design software  
Prepared by: Codex  
Audience: Claude Desktop / Claude Code collaborator

## 1. Purpose of This Note

Claude is being introduced as a new collaborator for the eTrace development effort.

The user's intent is clear:

- Codex remains responsible for the main coding implementation inside the project workspace.
- Claude should act as architect, auditor, adversarial reviewer, standards researcher, and code reviewer.
- Claude should challenge assumptions, identify subtle technical risks, and help prevent AI confirmation bias.
- Claude should produce tangible engineering outcomes, not broad commentary or distracting discussions.
- Gemini / Antigravity notes are historical inputs for now. They may be read, but should not be treated as authoritative.

The immediate technical focus is the development and integration of:

- MI cable / mineral insulated heating cable module
- constant power / constant wattage tracer module
- later integration with cold cable sizing, circuit design, BOQ, cable schedule, SLD, and model/3D workflows

## 2. Current Product Reality

eTrace is a development-stage Django application for electric heat tracing design.

The current implemented calculation scope is mainly pipeline-based self-regulating cable selection. The application has meaningful working foundations, but it is not production-ready and should not be described as certified, complete, or externally approved.

Current working foundations include:

- project setup
- line-list/input import
- SR heat-loss calculation path
- SR tracer selection
- persisted calculation evidence
- diagnostic rejection reasons
- result tables
- BOQ/cable schedule outputs
- project-backed SLD workspace
- helper/user guide page
- regression tests around the hardened SR calculation path

Current non-implemented or incomplete areas include:

- production MI cable calculation
- production constant wattage/constant power calculation
- full cold-cable sizing
- voltage-drop/distribution optimization
- complete convection/radiation heat-transfer model
- integrated insulation conductivity k(T) method
- production model-driven cable routing
- certified IEC/IEEE compliance workflow
- multi-user design/check/approve workflow

The truth-first product overview is documented here:

- `NOTES/eht-overview.md`

## 3. Roles and Collaboration Protocol

### User

The user is the product owner and domain authority. The user has practical EHT design expectations and wants the tool to become admired by experienced EPC/engineering users, not just technically functional.

### Codex

Codex will continue to:

- read and modify the codebase
- implement agreed changes
- run tests
- update trackers/docs
- keep changes small enough for review
- preserve the currently working SR path

### Claude

Claude should focus on:

- independent research
- architecture challenge
- standards interpretation
- design basis review
- edge-case discovery
- code review
- test case proposals
- risk register updates
- adversarial reasoning against the current plan

Claude should avoid:

- making large code edits directly unless explicitly requested by the user
- duplicating Codex implementation work
- accepting existing notes as correct without checking
- producing generic "looks good" reviews
- expanding scope without a concrete engineering deliverable
- treating manufacturer brochures as standards

Preferred Claude output style:

- specific findings
- clear severity or priority
- file/module references where relevant
- recommended action
- test/validation impact
- open questions for the user only where genuinely needed

## 4. Important Existing Project Notes

Claude should read these first:

1. `NOTES/eht-overview.md`
   - Current truth-first status of eTrace.
   - Separates implemented reality from roadmap.

2. `NOTES/SR_CALCULATION_HARDENING_TRACKER.md`
   - Records SR calculation hardening tasks.
   - Shows completed fixes and deferred heat-loss backlog.

3. `NOTES/MI_CABLE_RESEARCH_AND_INTEGRATION_PLAN.md`
   - Existing MI research/integration plan.
   - Useful starting point, but it should be challenged and improved.

4. `NOTES/CALCULATION_MODULE_USER_MANUAL.md`
   - Current calculation user manual.
   - Useful to understand current user-facing logic.

5. `NOTES/SR_CONDUCTIVITY_BASIS_RESEARCH.md`
   - Heat-loss conductivity basis discussion.
   - Current decision: mean insulation temperature method as default, with placeholders for future methods.

6. `NOTES/gemini_MI_notes.md`
   - Historical MI notes from Gemini.
   - Treat as input only, not as governing basis.

7. `MI_Cable_Engineering_Note.docx`
   - Historical MI engineering note in the root directory.
   - Treat as input only, not as governing basis.

## 5. Current Codebase Entry Points

Useful files/modules to inspect:

- `eht/models.py`
  - Main data models.
  - Includes existing MI placeholder models/migrations.

- `eht/calculation.py`
  - Existing broader calculation orchestration.

- `eht/calculations/heat_loss.py`
  - Shared heat-loss calculation logic.

- `eht/heat_loss_methods.py`
  - Conductivity basis strategy/placeholders.

- `eht/calculations/tracer_selection.py`
  - SR tracer selection logic and catalogue filtering.

- `eht/calculations/boq.py`
  - BOQ calculation/output logic.

- `eht/cable_schedule.py`
  - Cable schedule generation.

- `eht/calculations/power_distribution.py`
  - Electrical/topology support logic.

- `eht/sld_*`
  - SLD payload, topology, validation, PDF, layout, and workflow modules.

- `eht/forms.py`
  - Project setup form and heat-loss basis selection.

- `eht/views.py`
  - Main view orchestration.

- `eht/test_sr_calculation_hardening.py`
  - Focused SR hardening tests.

- `eht/test_sr_reporting_alignment.py`
  - Result/reporting alignment tests.

- `eht/tests.py`
  - Large legacy test file; useful, but should eventually be modularized.

## 6. What Has Already Been Achieved

### SR Calculation Hardening

Recent work stabilized the self-regulating cable calculation before starting MI. Completed items include:

- confirmed-input-only calculation behavior
- base heat loss separated from factored heat loss
- heat-loss safety factor evidence
- heat-loss method dropdown in project setup
- mean insulation temperature method as current default
- placeholders for future conductivity methods
- improved accessory adder semantics
- SR catalogue suitability filtering
- vendor-aware tracer selection
- voltage class handling improvements
- rejection diagnostics when no tracer satisfies constraints
- current/breaker interpretation improvements
- termination margin clarification
- result/BOQ/cable schedule/SLD data alignment
- regression tests for the hardened behavior

### Bugs Fixed

Notable bugs fixed during this phase:

- missing migration for `base_heat_loss`
- project setup data not reliably submitted before calculation
- selected vendor being ignored and Thermon being used by default
- vendor case/name mismatch issues
- project P2 disappearing from project list
- SST/KRUS-Zapad selection not working due to data/filter mismatch
- nVent SR selection clarified: current local data does not contain usable nVent SR rows, so no nVent SR selection is possible until real SR catalogue rows are loaded

### Documentation and Helper Page

Created:

- calculation module user manual
- helper/manual page in the app
- diagrams and visual guide assets
- print/PDF-friendly manual view
- improved formula notation
- compact search behavior
- truth-first product overview

## 7. Strategic Architecture Decision

MI cable should not be added as a special case inside the existing SR selection code.

The agreed target architecture is:

1. shared input and validation layer
2. shared thermal heat-loss layer
3. separate cable-technology selection engines
   - SR engine
   - MI engine
   - constant wattage/constant power engine
4. shared electrical/circuit/topology layer
5. shared persistence/evidence layer
6. shared presentation/export layer

This matters because SR, MI, and constant wattage cables are not just catalogue variants. They have different physical behavior, selection constraints, electrical sizing logic, temperature limits, manufacturing constraints, and deliverable expectations.

## 8. Why MI Needs a Separate Engine

Self-regulating cable behavior:

- parallel resistance heater
- output varies with pipe temperature
- selected mostly by maintain temperature, heat loss, voltage class, exposure, and maximum maintain/exposure limits
- starting current and circuit loading are important
- cable can usually be cut to length in the field within manufacturer rules

MI cable behavior:

- series resistance heater
- factory-engineered heater set
- resistance, heated length, voltage, phase configuration, sheath material, cold leads, and power output interact
- sheath temperature and hazardous-area T-class are central
- cold lead/hot-cold joint details matter
- minimum bend radius and installation constraints matter
- circuit segmentation is more design-intensive
- output is often not selected by a simple "catalogue power at maintain temperature" rule

Constant wattage/constant power cable behavior:

- often closer to fixed power output per unit length
- may be parallel zone-type or other manufacturer-specific construction
- different maximum exposure, circuit length, zone length, and control constraints
- not equivalent to MI and not equivalent to SR

Claude should challenge and refine these distinctions.

## 9. MI / Constant Power Research Expected From Claude

Claude should independently research and produce a concise but technically serious augmentation note.

The research should distinguish:

- mandatory standards
- recommended design guides
- manufacturer-specific practices
- assumptions made by eTrace
- areas where data is unavailable or proprietary

Target references include, where accessible:

- IEC/IEEE 60079-30-1
- IEC/IEEE 60079-30-2
- IEC/IEEE 62395-1
- IEC/IEEE 62395-2
- IEEE 515
- NEC Article 427
- nVent / Raychem MI and constant wattage design guides
- Thermon MI and constant wattage design guides
- Chromalox MI and constant wattage design guides
- Heat Trace Ltd guides
- other reputable manufacturer literature where useful

Important research topics:

- MI cable selection workflow
- MI resistance and power calculation
- resistance temperature correction
- allowable sheath temperature
- hazardous area T-class verification
- cold lead and hot-cold joint rules
- maximum circuit length and voltage limits
- single-phase vs three-phase configurations
- series vs parallel heater set implications
- start-up and steady-state current
- overcurrent protection and leakage/ground-fault protection
- control method assumptions
- pipe/material/insulation interaction
- high-temperature maintain and exposure cases
- corrosive/environmental sheath selection
- installation constraints and bend radius
- minimum/maximum power density
- special cases such as valves, supports, flanges, dead legs, and heat sinks
- deliverables expected by EPC users

Claude should also identify where real manufacturer data is required and where representative/demo data would be unsafe.

## 10. Desired Claude Deliverables

Claude should produce tangible outputs in a separate section/file, preferably titled:

`Claude Independent MI/CW Augmentation Note`

The note should include:

1. architecture critique
   - What is right or wrong about the separate-engine plan?
   - What should be shared vs cable-technology-specific?

2. MI design-basis summary
   - What equations/logic are essential?
   - What must be treated as manufacturer-specific?
   - What needs standards-based validation?

3. constant wattage/constant power design-basis summary
   - How it differs from SR and MI.
   - Whether it should be built before, after, or alongside MI.

4. data model recommendations
   - Required catalogue fields.
   - Required project/line inputs.
   - Required result/evidence fields.

5. calculation workflow proposal
   - Step-by-step MI workflow.
   - Step-by-step constant wattage workflow.
   - Decision points and rejection reasons.

6. risk register
   - Technical risks.
   - Standards risks.
   - Data risks.
   - UX risks.
   - Testing/validation risks.

7. test matrix
   - Unit tests.
   - Regression tests.
   - Engineering scenario tests.
   - Edge cases.

8. review questions for the user
   - Only questions that materially affect implementation.
   - Avoid broad discussion prompts.

## 11. Known Weak Spots Claude Should Challenge

Claude should pay special attention to:

- Current heat-loss calculation is simplified and mainly conduction-oriented.
- Heat-loss safety factor is a safeguard, not a physical convection/radiation model.
- Mean insulation temperature method is current default, but more advanced methods remain deferred.
- Future integrated k(T) method may improve physics but adds complexity and input/data burden.
- Catalogue data quality is critical; wrong vendor data caused selection failures before.
- MI placeholder catalogue/data should not be trusted as production data.
- SLD is useful but not yet a full production-grade electrical design package.
- BOQ/cable schedule outputs are useful but depend on calculation integrity.
- Tests exist, but validation against experienced EHT engineer expectation and vendor outputs is still needed.
- External documentation must not overstate current production readiness.

## 12. Code Review Expectations From Claude

When reviewing Codex changes, Claude should inspect for:

- engineering correctness
- hidden assumptions
- standards mismatch
- incorrect reuse of SR logic in MI/CW context
- data model shortcuts that will hurt later
- catalogue filtering mistakes
- unit confusion
- temperature basis confusion
- unsafe defaults
- missing diagnostics
- missing evidence fields
- missing tests
- UI fields that do not persist or are not used in calculation
- reports that show values not backed by persisted evidence
- regressions in the currently working SR path

Preferred review format:

```text
Finding:
Severity:
Location:
Why it matters:
Recommended action:
Suggested test:
```

## 13. Near-Term Development Plan

The next practical sequence should be:

1. Claude performs independent MI/CW research and writes the augmentation note.
2. User reviews Codex + Claude recommendations and decides final design basis.
3. Codex updates the tracker and creates an MI/CW implementation plan.
4. Codex implements in small passes.
5. Claude reviews each pass for architecture, standards, and subtle defects.
6. User accepts/rejects open engineering assumptions.

Likely coding passes:

1. MI/CW tracker and design-basis document
2. data model cleanup for MI/CW catalogue and results
3. shared heating-technology abstraction
4. MI selection service skeleton
5. MI calculation/evidence/rejection logic
6. constant wattage service skeleton
7. reporting/export integration
8. BOQ/cable schedule integration
9. SLD/electrical integration
10. tests and validation scenarios

## 14. Important Guardrail

The currently working SR path must not be broken while MI/CW is added.

New MI/CW work should be isolated until it is stable enough to connect into shared outputs. Any refactor of shared heat-loss, project setup, result persistence, BOQ, cable schedule, or SLD code should include regression tests for the existing SR behavior.

## 15. Success Criteria for Claude's Contribution

Claude's contribution is successful if it helps the team:

- avoid incorrect MI/SR/CW mixing
- identify standards-sensitive issues before code is written
- define the right data model early
- add tests before subtle bugs are embedded
- keep documentation truthful
- make implementation decisions faster
- produce review findings that Codex can act on directly

The user wants practical progress. The best Claude output is therefore concise, referenced, critical, and directly convertible into implementation tasks.

