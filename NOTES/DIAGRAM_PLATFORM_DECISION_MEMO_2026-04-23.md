# Diagram Platform Decision Memo

Date: 2026-04-23

Status: Approved working direction for the next architecture phase

Scope:
- EHT auto-generated SLD
- project/presentation SLD
- cable block diagrams and related logic diagrams
- power system study diagrams and study-backed network views

## 1. Decision

We will build a centralized diagram platform with distributed domain logic.

In practical terms:
- one shared `diagram_core` capability will provide the editor, graph primitives, persistence patterns, rendering pipeline, interaction model, and common exports
- each business module will provide its own domain adapter, symbol pack, validation rules, auto-layout strategy, and data translators

This is a hybrid architecture:
- centralized infrastructure
- distributed engineering semantics

This is explicitly not:
- a fully separate drawing implementation inside each module
- a monolithic universal engineering-diagram app that embeds all domain rules in one place

## 2. Problem Statement

The broader electrical engineering ecosystem needs multiple kinds of diagrams:

1. Cable block diagrams for cable logic, load relationships, and quantity/design workflows
2. Project SLDs for presentation, understanding, and design communication
3. Power-system study diagrams with simulation-backed electrical network attributes
4. EHT SLDs generated from heat-tracing power-distribution topology

These diagrams overlap heavily in editor behavior and persistence needs, but they differ in:
- graph semantics
- symbol conventions
- validation rules
- data density
- calculation/source-of-truth ownership
- user workflows

## 3. Options Considered

### Option A. Fully Distributed Diagram Tools

Each module builds its own editor and persistence path.

Benefits:
- fastest local progress at the beginning
- each team can optimize for its own use case
- fewer upfront abstraction decisions

Costs:
- duplicated canvas/editor work
- duplicated save/load/versioning logic
- inconsistent UX across modules
- multiple incompatible graph formats
- expensive future integration between EHT, cable, and power-study modules
- very high long-term maintenance cost

Assessment:
- good for prototypes
- poor fit for the target EPC-grade product ecosystem

### Option B. Fully Centralized Universal Diagram App

One giant platform owns both the editor and all domain semantics.

Benefits:
- maximum consistency
- one place for all diagrams
- potentially simpler governance

Costs:
- domain rules become tightly coupled
- every special case becomes a platform change
- high design overhead before shipping value
- hard to evolve safely as new engineering modules appear
- risk of a generic-but-clumsy tool that satisfies nobody well

Assessment:
- too rigid and too coupled for this ecosystem

### Option C. Centralized Platform With Distributed Domain Adapters

One diagram platform, many domain packages.

Benefits:
- shared editor and UX
- shared persistence/versioning/export patterns
- domain-specific modeling remains local
- easier cross-module navigation and reuse
- lower long-term cost without forcing false uniformity

Costs:
- requires clear interfaces between core and domain adapters
- some upfront architecture discipline is needed
- migration/extraction work must be done carefully from the current EHT SLD

Assessment:
- best balance of speed, quality, and scalability

## 4. Decision Drivers

The main drivers behind the recommendation are:

1. Shared behavior is real:
   pan/zoom, select, drag, connect, group, save, version, export, review, print, permissions

2. Shared semantics are not real:
   EHT topology, cable logic, and pandapower network models should not be forced into one domain schema

3. Future integration matters:
   the ecosystem will benefit from a common graph shell and shared UI language

4. Reuse must not destroy domain clarity:
   electrical study data should not be contaminated by EHT-specific assumptions and vice versa

## 5. Final Recommendation

Adopt Option C.

Build:
- `diagram_core` as reusable platform infrastructure
- `diagram_conventions` as reusable drafting/presentation standards
- domain adapters inside each module such as `eht_diagrams`, `power_system_diagrams`, and `cable_diagrams`

## 6. Implementation Strategy

Do not pause all work to build the final enterprise-wide platform first.

Instead:

1. Continue improving the EHT SLD now
2. Refactor it intentionally so reusable parts become extractable
3. Extract `diagram_core` from the stabilized EHT implementation
4. Reuse that core for power-study and cable modules

This gives the fastest path to value with the lowest rework risk.

## 7. Architectural Boundaries

Centralized responsibilities:
- graph/document primitives
- diagram editor shell
- renderer abstraction
- interaction model
- layout persistence pattern
- versioning/audit hooks
- print/export framework
- common symbol registration contract

Distributed responsibilities:
- domain source-of-truth models
- domain graph translators
- domain validations
- domain auto-layout rules
- domain symbol packs
- domain property inspectors
- domain-specific commands and workflows

## 8. Risks If We Ignore This Decision

If we build separate tools per module:
- duplicated effort will multiply quickly
- users will face inconsistent behavior across modules
- cross-module diagrams will be difficult later

If we over-centralize too early:
- platform complexity will delay delivery
- domain teams will start bypassing the platform
- the diagram system will become hard to evolve

## 9. Immediate Next Steps

1. Use the current EHT SLD as the first extraction candidate for `diagram_core`
2. Stabilize EHT persistence and graph contracts before adding more interactive features
3. Define the target architecture and execution roadmap for the SLD program
4. Keep future cable and power-study modules aligned to the same platform boundaries
