# SLD Refactor And Build Roadmap

Date: 2026-04-23
Last updated: 2026-04-25

Status: Execution baseline

Purpose:
- stabilize the current EHT SLD
- turn it into a professional, production-capable feature
- extract reusable platform pieces for the wider engineering ecosystem

## 1. Planning Principles

This roadmap follows four guardrails:

1. Do not add visual polish on top of fragile persistence
2. Keep EHT domain logic inside `eht`; extract only truly reusable diagram infrastructure
3. Prefer additive refactors with passing tests at each phase
4. Preserve a usable SLD at all times during the transition

## 2. Program Outcome

At the end of this roadmap, EHT should have:
- a stable generated SLD graph contract
- reliable persistence for layout and later controlled edit operations
- a professional diagram workspace with scalable browsing
- a clear extraction boundary for shared diagram-core capabilities

## 3. Phase Overview

### Phase 0. Freeze The Baseline

Goal:
- align docs and current-state understanding before more implementation work

Exit criteria:
- architecture decision is documented
- target architecture is documented
- execution roadmap is accepted as the working baseline

Tasks:
- [x] Write centralized-vs-distributed decision memo
- [x] Write target architecture reference
- [x] Write phase-by-phase roadmap with trackable tasks
- [x] Update existing notes that still describe the SLD as only a prototype
- [x] Add a short architecture/roadmap index entry to `README.md`

### Phase 1. Hardening The Current EHT SLD Foundation

Goal:
- remove the most dangerous fragile behavior before feature expansion

Exit criteria:
- project recalculation cannot leave SLD-related data half-broken
- one canonical SLD entry path is used
- graph generation/persistence contracts are explicit and test-covered

Tasks:
- [x] Wrap upload-confirm-calculate-store flows in proper transactional boundaries
- [x] Make `store_calculated_results()` atomic and fail-safe
- [x] Make upload replacement safe so prior project data is not lost on partial failure
- [x] Stop swallowing bulk-upload exceptions in `upload_inputData_in_DB()`
- [x] Remove wildcard import usage in `views.py`
- [x] Retire the legacy `sld/` prototype route and page once the workspace path is fully canonical
- [x] Document the canonical SLD graph contract: node IDs, edge IDs, line groups, metadata rules
- [x] Add regression tests for full project regenerate-and-reload flow
- [x] Add regression tests for safe failure during persistence

Recommended file focus:
- [eht/views.py](/home/kr/mydev/eht_office/eht/views.py:116)
- [eht/data_service.py](/home/kr/mydev/eht_office/eht/data_service.py:217)
- [eht/urls.py](/home/kr/mydev/eht_office/eht/urls.py:18)

### Phase 2. Stabilize The Graph Model

Goal:
- make the SLD graph a trustworthy product artifact, not only a rendering by-product

Exit criteria:
- stable graph schema is defined and versioned
- graph IDs and metadata rules are deterministic
- layout and graph concerns are cleanly separated

Tasks:
- [x] Introduce explicit graph schema versioning in payloads
- [ ] Define a normalized internal graph contract for nodes, edges, groups, and annotations
- [ ] Separate generated graph payload from future user-edit overrides
- [ ] Review whether branch JSON remains the generated source or whether a normalized graph table is required next
- [ ] Define how future manual edits will be represented without corrupting generated topology
- [x] Add tests for graph determinism across repeated graph builds
- [ ] Add tests for backward compatibility with legacy branch JSON fallback

Recommended file focus:
- [eht/sld_payload.py](/home/kr/mydev/eht_office/eht/sld_payload.py:162)
- [eht/sld_validation.py](/home/kr/mydev/eht_office/eht/sld_validation.py:117)
- [eht/models.py](/home/kr/mydev/eht_office/eht/models.py:233)

### Phase 3. Layout Persistence And Edit Safety

Goal:
- make layout persistence robust enough for professional use and future editing

Exit criteria:
- save/reset behavior is deterministic
- partial saves are supported safely or explicitly disallowed by contract
- layout persistence no longer depends on fragile whole-document assumptions

Tasks:
- [x] Decide whether layout saves are full-document snapshots or patch/delta updates
- [x] Record that the current API uses merge-style coordinate updates rather than full-document replacement
- [x] If moving to partial updates, redesign `save_project_sld_layout()` to stop deleting omitted nodes
- [ ] Add optimistic version checks or last-modified checks for concurrent save safety
- [ ] Persist viewport preferences separately from node coordinates if useful
- [x] Add tests for partial node visibility/filtering without accidental layout deletion
- [x] Add tests for project recalculation where stable component IDs keep prior layout where valid

Recommended file focus:
- [eht/sld_layout.py](/home/kr/mydev/eht_office/eht/sld_layout.py:35)
- [static/js/sld_workspace.js](/home/kr/mydev/eht_office/static/js/sld_workspace.js:244)

### Phase 4. Professional EHT SLD UX

Goal:
- make the current EHT SLD feel intentional, readable, and useful in real project work

Exit criteria:
- diagrams are readable on medium and large projects
- users can inspect and navigate the system without wrestling the canvas
- validation and engineering metadata are visible in context

Tasks:
- [x] Improve symbol readability: cable labels/specs out of cramped boxes
- [x] Simplify tracer and end-termination labeling
- [x] Add stronger per-line grouping cues
- [x] Add basic line search/select and one-line focused viewing mode
- [x] Make line-focused browsing fully AJAX/server-backed so large projects do not require full-payload browser filtering
- [x] Add collapsible validation sections and branch-detail drilldown
- [x] Add click selection highlighting for the currently connected rendered graph
- [x] Refine path highlighting to show the true source-to-selected path instead of the whole connected component
- [x] Add property inspector panel for selected components
- [ ] Add export to PNG/PDF for the current rendered view
- [x] Add fit/zoom/export SVG navigation tools
- [x] Improve first-pass SLD readability with slimmer cable/tracer symbols, external cable/tracer detail labels, and stronger line group labels
- [x] Add a “fit selected line” and “fit all” navigation flow
- [ ] Add workspace loading/error states that feel production-grade

Recommended file focus:
- [templates/eht/partials/sld_tab.html](/home/kr/mydev/eht_office/templates/eht/partials/sld_tab.html:1)
- [static/js/sld_workspace.js](/home/kr/mydev/eht_office/static/js/sld_workspace.js:48)
- [static/css/base_css.css](/home/kr/mydev/eht_office/static/css/base_css.css:386)

### Phase 5. Controlled Domain Editing

Goal:
- move from generated-and-positioned SLD to selective, safe engineering edits

Exit criteria:
- edit capabilities are intentionally scoped
- user edits do not silently diverge from the source calculation model
- write-back rules are explicit

Tasks:
- [ ] Decide the first allowed edit set:
  `layout only`, `annotation only`, or `approved topology adjustments`
- [ ] Add annotations/comments without affecting generated topology
- [ ] Add user-defined grouping or presentation-only grouping
- [ ] Define edit provenance: generated vs user-added vs user-overridden
- [ ] Design a review/reset model for returning to generated baseline
- [ ] Define where cold-cable-length edits belong and how they propagate
- [ ] Define alternate-tracer reselection workflow and how diagram refresh is communicated
- [ ] Add tests for reset-to-generated behavior after allowed edits

Important note:
- topology editing should not be enabled before the provenance model is clear

### Phase 6. Extract Reusable Diagram-Core Pieces

Goal:
- turn the EHT SLD foundation into the first reusable platform slice for the broader ecosystem

Exit criteria:
- reusable editor/persistence/render pieces are clearly separated from EHT business logic
- EHT still works unchanged from a user perspective

Tasks:
- [ ] Identify backend services that are generic vs EHT-specific
- [ ] Identify frontend editor/runtime code that is generic vs EHT-specific
- [ ] Extract reusable graph rendering helpers
- [ ] Extract reusable layout persistence service contract
- [ ] Define symbol-registration API for future modules
- [ ] Define adapter interface for domain translators
- [ ] Move shared code into a reusable package/module without breaking EHT
- [ ] Add at least one small non-EHT proof of reuse, even if minimal

### Phase 7. Prepare Multi-Module Adoption

Goal:
- make the platform ready for cable and power-study modules

Exit criteria:
- other modules can target the same platform with their own adapters
- no EHT assumptions leak into the core

Tasks:
- [ ] Define the first cable-diagram adapter contract
- [ ] Define the first power-study adapter contract
- [ ] Specify how pandapower network data maps to graph primitives
- [ ] Specify how cable block diagram data maps to graph primitives
- [ ] Define shared export and review conventions across modules
- [ ] Define cross-module diagram document metadata: project, revision, owner, source module

## 4. Priority Order

Work should proceed in this order:

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6
7. Phase 7

Reason:
- persistence and graph integrity must come before UX polish
- UX polish must come before advanced editing
- reusable platform extraction should happen only after local boundaries are proven

## 5. Immediate Sprint Candidate

If we start the next implementation sprint now, I recommend this sprint scope:

Sprint A:
- [x] make calculation/result persistence atomic
- [x] harden upload replacement flow
- [x] remove the old standalone prototype route
- [x] document the canonical graph contract
- [x] add regression tests for regenerate + reload

Sprint B:
- [x] redesign layout save contract
- [x] preserve layout safely across valid recalculation changes
- [x] add line-focused browsing
- [x] add collapsed validation drilldown

Sprint C:
- [ ] improve symbol readability and visual grouping
- [x] add property inspector and path highlighting
- [x] add export and fit/navigation tools

Current next sprint:
- [x] restore trustworthy test coverage around upload/confirm calculation transaction boundaries
- [x] fix the SLD line-focus form so it reloads the workspace tab through the canonical AJAX tab loader
- [x] add server-side `line_id` filtering for SLD payload/layout flows to avoid full-payload client filtering on large projects
- [x] reduce redundant SLD endpoint work so payload-only requests do not also build layout and validation data
- [x] add graph schema versioning and determinism tests
- [x] add duplicate `line_id` collision coverage and line-UID-backed physical line ownership
- [x] define display-tag stability boundary: stable for the same sorted line set, allowed to renumber when line membership/order changes
- [x] refine source-to-selected path highlighting semantics before advanced regrouping
- [x] remove the unused old standalone SLD stylesheet and keep current SLD presentation in the active workspace stylesheet/renderer
- [x] add fit-all and fit-selected-line canvas navigation

## 6. Delivery Risks

Key risks to manage:
- adding edit features before provenance rules exist
- over-extracting shared code too early
- continuing to rely on implicit contracts in JSON blobs
- polishing the UI before save/rebuild behavior is trustworthy

## 7. Definition Of Done For “Production-Ready EHT SLD”

The EHT SLD should be considered production-ready only when:
- the generated graph is deterministic and validated
- project recalculation is safe and transactional
- layout persistence survives legitimate project reruns
- the workspace scales to realistic project sizes
- exports are reliable
- the old prototype path is gone
- the code is covered by automated tests around graph, persistence, and UI endpoints

## 8. Working Backlog Index

These docs now define the active baseline:
- [DIAGRAM_PLATFORM_DECISION_MEMO_2026-04-23.md](/home/kr/mydev/eht_office/NOTES/DIAGRAM_PLATFORM_DECISION_MEMO_2026-04-23.md:1)
- [DIAGRAM_PLATFORM_TARGET_ARCHITECTURE.md](/home/kr/mydev/eht_office/NOTES/DIAGRAM_PLATFORM_TARGET_ARCHITECTURE.md:1)
- [SLD_REFACTOR_BUILD_ROADMAP.md](/home/kr/mydev/eht_office/NOTES/SLD_REFACTOR_BUILD_ROADMAP.md:1)
- [EHT_SLD_GRAPH_CONTRACT.md](/home/kr/mydev/eht_office/NOTES/EHT_SLD_GRAPH_CONTRACT.md:1)
