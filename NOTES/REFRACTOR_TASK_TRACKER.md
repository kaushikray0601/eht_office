# EHT Refactor Task Tracker

This tracker is derived from [CODEBASE_REVIEW_2026-04-17.md](/home/kr/mydev/eht_office/NOTES/CODEBASE_REVIEW_2026-04-17.md:1) and is intended to be worked through in order.

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
    - [ ] Task 7.6.2: Improve symbol readability: move cable labels/specs out of cramped boxes, simplify tracer/end-termination labeling, and tighten geometry sizing.
    - [ ] Task 7.6.3: Add clearer per-line visual grouping so all circuits belonging to one line are easy to read as a set.
    - [ ] Task 7.6.4: Add scalable SLD browsing for large projects: search/select by `line_id`, paged one-line-at-a-time viewing, and collapsed-by-default validation details.
    - [ ] Task 7.6.5: Review remaining SLD correctness/presentation refinements before starting regrouping logic.
  - [ ] Task 7.7: Later enhancement: allow regrouping/reorganization of branches and sources independent of the raw calculation topology.
- [ ] Task 8: Add automated test coverage for import, calculation, persistence, and reporting flows.

Carry-over items:
- [ ] Add deeper domain/business-rule validation for `ProjectData` so admin-created setup/templates fail early on engineering constraints instead of only on field/model-level validation.
- [ ] Refine SLD presentation after the architecture phase: conventional SLD visual language, geometry/symbol sizing, text sizing, page layout, cable/spec label placement, and overall UI polish.
- [ ] Improve SLD interaction correctness: fully derived link routing on node move/reset, clearer grouping cues per line, and review/reset behavior for saved vs derived visual elements.
- [ ] Add scalable SLD browsing UX for large projects: pagination/search by `line_id`, collapsible validation panels, and other large-project readability improvements.
