# EHT Refactor Task Tracker

This tracker is derived from [CODEBASE_REVIEW_2026-04-17.md](/home/kr/mydev/eht_office/NOTES/CODEBASE_REVIEW_2026-04-17.md:1) and is intended to be worked through in order.

Current architecture/program references:
- [Diagram Platform Decision Memo](/home/kr/mydev/eht_office/NOTES/DIAGRAM_PLATFORM_DECISION_MEMO_2026-04-23.md:1)
- [Diagram Platform Target Architecture](/home/kr/mydev/eht_office/NOTES/DIAGRAM_PLATFORM_TARGET_ARCHITECTURE.md:1)
- [SLD Refactor And Build Roadmap](/home/kr/mydev/eht_office/NOTES/SLD_REFACTOR_BUILD_ROADMAP.md:1)
- [EHT SLD Graph Contract](/home/kr/mydev/eht_office/NOTES/EHT_SLD_GRAPH_CONTRACT.md:1)

Program-level SLD execution baseline:
- [ ] Phase 1: Hardening the current EHT SLD foundation
- [ ] Phase 2: Stabilize the graph model
- [ ] Phase 3: Layout persistence and edit safety
- [ ] Phase 4: Professional EHT SLD UX
- [ ] Phase 5: Controlled domain editing
- [ ] Phase 6: Extract reusable diagram-core pieces
- [ ] Phase 7: Prepare multi-module adoption

- [x] Task 1: Stabilize result persistence for the current calculation payloads so calculations can complete without runtime storage errors.
- [x] Task 2: Redesign result models so persisted rows are project-safe and line-safe instead of overwriting by tracer catalog ID, and so BOQ data can be stored as real line items instead of being skipped.
- [x] Task 3: Finish the partial-invalid upload flow so "proceed with valid rows" actually runs calculations and stores outputs.
- [x] Task 4: Fix project setup constraints, then correct project setup UX to use an admin-managed project dropdown and remove tracer-family from global setup.
- [x] Task 5: Normalize the calculation pipeline contracts and remove duplicate old/new code paths that drifted during the refactor.
- [x] Task 6: Build usable result and BOQ views on top of persisted calculation data.
- [ ] Task 7: Connect the SLD prototype to real stored project/component relationships.
  - [x] Task 7.1: Introduce project-wide unique tag generation with separate `display_tag` and stable internal `component_id` / `component_uid`.
  - [x] Task 7.2: Build an SLD payload service that reads persisted `PowerDistributionBranch.tagged_components` and emits normalized nodes/edges.
  - [x] Task 7.3: Add a project-backed SLD endpoint for the workspace tab.
  - [x] Task 7.4: Replace the hardcoded JointJS demo with data-driven read-only rendering.
  - [x] Task 7.5: Validate generated SLDs against real stored projects in the browser.
  - [x] Task 7.6: Add coordinate persistence so manual layout can be saved and reloaded.
    - [x] Task 7.6.1: Make links and labels fully derived from component-node positions so drag/save/reset behavior stays deterministic.
    - [x] Task 7.6.2: Improve symbol readability: move cable labels/specs out of cramped boxes, simplify tracer/end-termination labeling, and tighten geometry sizing.
    - [x] Task 7.6.3: Add clearer per-line visual grouping so all circuits belonging to one line are easy to read as a set.
    - [x] Task 7.6.4: Add basic SLD browsing for large projects: search/select by `line_id`, one-line-at-a-time viewing, and collapsed-by-default validation details.
    - [x] Task 7.6.5: Review remaining SLD correctness/presentation refinements before starting regrouping logic.
  - [x] Task 7.7: Later enhancement: allow regrouping/reorganization of branches and sources independent of the raw calculation topology.
- [x] Task 8: Add automated test coverage for import, calculation, persistence, and reporting flows.

Active ordered task queue as of 2026-04-25:
- [x] Task 9.1: Restore trustworthy test coverage around upload/confirm calculation transaction boundaries, including the currently failing hardening test.
- [x] Task 9.2: Move `confirm_valid_data()` calculation work out of the short confirmation transaction so it matches the safer upload flow.
- [x] Task 9.3: Fix the SLD line-focus form so it reloads `sld_workspace_view` through the canonical AJAX tab loader instead of submitting to the wrong page context.
- [x] Task 9.4: Add server-side `line_id` filtering for SLD payload/layout requests so focused views do not fetch the full project graph in the browser.
- [x] Task 9.5: Avoid redundant SLD endpoint work by separating payload-only, layout-only, validation-only, and full workspace build paths.
- [x] Task 9.6: Add explicit SLD graph schema versioning and deterministic graph tests.
- [x] Task 9.7: Add duplicate `line_id` collision coverage and decide whether `component_id` should include internal line UID as well as display `line_id`.
- [x] Task 9.8: Stabilize engineering display tags across recalculation where feasible, or document when display tags may legitimately renumber.
- [x] Task 9.9: Refine path highlighting from connected-component highlighting to true source-to-selected path highlighting.
- [x] Task 9.10: Continue SLD presentation work: conventional symbol sizing, cable/spec label placement, and clearer per-line grouping.
- [x] Task 9.11: Add lightweight fit-all and fit-selected-line canvas navigation without introducing a separate navigation model.

Next ordered task queue: SLD engineering topology editing:
- [x] Task 10.1: Define the topology-edit contract: generated baseline vs user override, audit/provenance fields, reset-to-generated behavior, and recalculation survival rules.
- [x] Task 10.2: Add 4A and 6A breaker ratings to the standard MCB rating choices and confirm all affected forms/tests accept them.
- [x] Task 10.3: Model a minimal persisted topology override layer that can represent feeder combine/split edits without rewriting calculation-owned branch source data.
- [x] Task 10.4: Build deterministic topology-override application so SLD payload, validation, BOQ, cable schedule, and connected-load summaries consume the edited topology when present.
- [x] Task 10.5: Push SLD `line_id` filtering into the payload query/build layer so focused line browsing does not build the full project graph before filtering.
- [x] Task 10.6: Implement layout delta saves from the browser by tracking dirty component nodes and posting only changed coordinates.
- [ ] Task 10.7: Audit existing `tagged_components` payloads for explicit connection/schema coverage, then plan a one-time migration so fallback graph reconstruction can be removed from the hot path.
- [x] Task 10.8: Review `component_uid` generation and switch to a fuller deterministic identity if it can be done without disturbing persisted layout/component identity.
- [ ] Task 10.9: Implement the first controlled combine-feeders workflow: select eligible feeder paths, preview removed/added components, calculate next available MCB rating, require user confirmation, and store audit remarks.
- [ ] Task 10.10: Implement the first controlled split-feeder workflow: select branches/circuits to move to a new feeder path, preview generated MCB/cable/JB changes, require user confirmation, and store audit remarks.
- [ ] Task 10.11: Add clear UI states for generated, edited, recalculated, warning, and resettable topology so users can understand and trust manual engineering changes.
- [ ] Task 10.12: Add regression tests for edited topology persistence, recalculation validation, reset-to-generated, BOQ/cable-schedule impact, and audit trail integrity.

Current self-check note:
- The SLD refactor path remains layered: generated payload, validation, saved layout, and browser rendering stay separate. Duplicate display `line_id` handling is fixed by using `line_uid` for physical line ownership. Display tags are intentionally presentation labels: stable for the same sorted line set, allowed to renumber when the line set or sort identity changes.
- Simplification pass: removed duplicate browser-side line filtering because `/sld/payload/` is now the canonical server-side line filter. The browser now trusts the endpoint response and only renders it. This keeps filtering rules in one place and avoids maintaining two copies of the same duplicate-`line_id` logic.
- Path highlighting now follows directed SLD edges from source components to the selected component. The code falls back to zero-incoming nodes only for malformed/legacy graphs without an MCB, so normal project graphs use the electrical source path rather than a whole connected-component highlight.
- Presentation pass: kept the SLD renderer as the only active diagram presentation code, deleted the unused old standalone SLD stylesheet, slimmed cable/tracer symbols, moved their detail labels outside the cramped symbol bodies, and made line labels read more like grouping anchors.
- Navigation pass: the existing fit button is now explicitly fit-all, and a fit-line button frames the physical line group for the currently selected component. This stays entirely in the browser because the rendered payload already contains the required line-group ownership.
- Task 7.6.5 review: no new SLD architecture is needed before regrouping. The follow-up scope should stay bounded to tests and domain validation first; regrouping remains explicitly later under Task 7.7. As part of this review, dead presentation branches left behind by the cable/tracer label move were removed instead of adding more code.
- Task 8 coverage review: existing tests now cover the import workspace/export, calculation orchestration, result persistence including rollback, result and BOQ views/exports, upload replacement safety, confirm-pending behavior, and the SLD payload/layout/validation path. No extra tests were added in this pass because the target flows are already covered.
- ProjectData validation pass: added one model-level `clean()` for shared engineering guardrails and kept `save()` scoped to those domain rules plus existing derived-field sync. Field-level validation remains with forms/admin/DB constraints, which avoids surprising direct-save behavior while still catching calculation-breaking setup values early.
- Task 7.7 regrouping pass: added presentation-only line and branch drag handles in the SLD renderer. The browser moves the relevant component nodes and existing layout save persists only coordinates; generated edges, source paths, branch indices, and calculation-owned topology remain untouched.
- Task 10.1 topology-edit contract: topology edits are now defined as a separate engineering override layer over the generated baseline. The first allowed edit types are combine-feeders and split-circuits; applied edits become the basis for SLD, BOQ, cable schedule, and load summaries, while generated baseline data remains available for validation, review, and reset.
- Task 10.2 breaker-rating pass: added 4A and 6A to the shared `ProjectData.max_cb_size` choices and recorded the matching schema-state migration. The calculation layer already included these ratings, so this aligns project setup forms/admin with the existing breaker-selection logic.
- Task 10.3/10.4 topology-edit infrastructure pass: added a first-class `SLDTopologyEdit` audit/override model plus a small deterministic application service. Applied edits can provide a validated edited SLD payload, cable-schedule rows, and downstream summary overrides; the generated calculation branch data remains untouched and available as baseline.
- Antigravity architecture review triage: accepted immediate low-risk improvements are true query pushdown for focused SLD browsing, dirty-node layout saves, legacy fallback schema audit/migration planning, and deterministic UID entropy review. Broader graph normalization, JointJS embedding rewrites, caching, async calculation execution, and diagram-core extraction remain discussion/future-platform items rather than blockers for the first topology-edit workflows.
- Task 10.5/10.6/10.8 focused performance pass: `build_project_sld_payload()` now accepts an optional `line_id` and filters branches before graph construction, validation follows the same focused scope, and layout saves can persist filtered/delta coordinates without pruning saved nodes from other lines. The browser now tracks dirty component IDs and posts only moved node coordinates. `component_uid` generation now uses a 32-hex deterministic SHA-256-derived value that fits the existing layout field while reducing arbitrary hash truncation.

Carry-over items:
- [x] Add deeper domain/business-rule validation for `ProjectData` so admin-created setup/templates fail early on engineering constraints instead of only on field/model-level validation.
- [ ] Refine SLD presentation after the architecture phase: conventional SLD visual language, geometry/symbol sizing, text sizing, page layout, cable/spec label placement, and overall UI polish.
- [ ] Improve SLD interaction correctness: fully derived link routing on node move/reset, clearer grouping cues per line, and review/reset behavior for saved vs derived visual elements.
- [ ] Add scalable SLD browsing UX for large projects: server-side filtering by `line_id`, one-line focused browsing, collapsible validation panels, and other large-project readability improvements.
