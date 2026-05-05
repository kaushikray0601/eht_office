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
- [x] Task 10.7: Audit existing `tagged_components` payloads for explicit connection/schema coverage, then plan a one-time migration so fallback graph reconstruction can be removed from the hot path.
- [x] Task 10.8: Review `component_uid` generation and switch to a fuller deterministic identity if it can be done without disturbing persisted layout/component identity.
- [x] Task 10.9: Implement the first controlled combine-feeders workflow: select eligible feeder paths, preview removed/added components, calculate next available MCB rating, require user confirmation, and store audit remarks.
- [x] Task 10.10: Implement the controlled split-feeder workflow: select a multi-circuit MCB, remove the shared distribution path, create independent MCB-fed outgoing circuits, recommend the reduced breaker rating, require user confirmation, and store audit remarks.
- [x] Task 10.11: Add clear UI states for generated, edited, recalculated, warning, and resettable topology so users can understand and trust manual engineering changes.
- [x] Task 10.12: Add regression tests for edited topology persistence, recalculation validation, reset-to-generated, BOQ/cable-schedule impact, and audit trail integrity.
- [x] Task 10.13: Add first controlled downstream-3PH-JB workflow: select an upstream 3PH JB, select 2-3 direct outgoing branch roots, enter the new 4C trunk cable length, enforce the 3-outgoing limit, and persist an audited topology edit.
- [x] Task 10.14: Start the guided graph-operation editor: allow a user to select an existing MCB-fed circuit, choose an eligible 3PH JB with spare outgoing capacity, and let the system reattach the feeder path while preserving audit/reset behavior.
- [x] Task 10.15: Extend the guided attach operation to downstream branch moves: select a branch component, resolve its direct 3PH-JB branch root, choose another eligible 3PH JB in the same upstream MCB tree, and move the branch without forcing split/recombine.
- [x] Task 10.16: Make SLD links selectable and expose link-context topology actions without allowing unsafe raw freeform link deletion/creation.
- [x] Task 10.17: Refine downstream branch/subtree reassignment UX after testing and decide whether drag/drop earns its code volume.

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
- Task 10.7 schema audit pass: added a reusable `tagged_components` schema audit that checks for schema version, explicit component details, downstream component details, and explicit graph connections. Validation now reports schema coverage as a project check, so fallback reconstruction remains visible technical debt instead of hidden hot-path behavior. Migration plan: audit current projects first, repair legacy branches to schema version 1 only after the audit identifies affected rows, then remove fallback reconstruction once validation reports strict coverage.
- Task 10.9 first combine-feeders workflow: added a controlled MCB-source selection mode in the SLD inspector, preview/apply endpoints, next-available breaker recommendation, audit remarks, and applied `SLDTopologyEdit` persistence. The combine override now inserts the required manual `Cable4C` trunk and `JB3PH` distribution node so the combined MCB feeds one trunk path before branching into the existing outgoing `Cable3C` feeder paths. Cable sizing remains review-required follow-up domain work.
- Task 10.9 experimental geometry follow-up: active combine topology now gets a topology-aware browser layout pass that walks the edited graph from the combined MCB, lays each descendant circuit path by hierarchy/depth, normalizes the diagram into visible canvas bounds, and keeps the shell top-left scrollable while the canvas is active. Saved positions are still merged for unrelated nodes, but edited combine descendants are auto-positioned so stale pre-combine coordinates cannot pull nested 3PH branches into overlapping geometry. Keep this change under review after user testing; if the visual result is not accepted, this isolated browser layout pass is the intended rollback point.
- Task 10.9 combine UX follow-up: removed the separate visible preview button. The inspector now runs the existing preview/validation endpoint automatically after selection changes, shows checking/ready/error status inline, ignores stale preview responses, and enables `Apply Edit` only when the latest selection is valid. This preserves the defensive server validation while removing a low-value UI step.
- Task 10.9 incremental combine follow-up: combine edits can now extend the currently active combine topology. The next combine preview/apply works against the active SLD graph, supersedes the previous applied edit revision, reuses the existing manual 4C trunk/3PH JB when extending a combined feeder, and keeps reset-to-generated behavior intact. Split remains intentionally single-edit guarded until its merge semantics are designed.
- Task 10.10/10.11 split-and-state pass: updated split-circuits to match the engineering workflow: the user selects one multi-circuit MCB, the edit removes the shared upstream 3PH distribution chain, keeps the first outgoing circuit on the original marked MCB, adds new marked MCBs for the other outgoing circuits, displays each result as a complete source-to-load circuit with `-partN` line suffixes, recommends the reduced breaker rating, and persists an audited topology edit. Added generated-vs-edited/recalculated SLD UI state, active-edit warnings, baseline fingerprints, and a reset-to-generated endpoint/button. Cable sizing remains explicit follow-up domain work.
- SLD refinement pass: added client-side line-group pagination with 5/10/20/25/all page sizes, changed edited-topology rendering to rebuild clean MCB-rooted source trees after combine/split so stale coordinates do not create overlap or large gaps, and added a first right-click context menu for inspect, fit, combine selection, split selection, and clear-selection actions.
- Task 10.12 hardening pass: added regression coverage for combine/split edit payload persistence, generated baseline snapshots, validation/audit warnings, authenticated `created_by`, reset status transitions, recalculation detection, BOQ/result summary overrides, and edited cable-schedule rows flowing into the result schedule. Combine/split now write minimal edited cable schedule rows derived from the active edited graph so downstream result views are tied to the topology override instead of stale generated branch rows.
- SLD layout hierarchy pass: reduced top-page clutter by replacing metric cards with a compact summary strip, moved active topology warnings near the page header with a dismiss control, merged focus-line search and line pagination into one browser toolbar, promoted topology-edit controls above the property inspector, separated reset-to-generated from apply, made apply labels mode-specific, added context-menu apply actions, and tightened canvas vertical padding/height so the diagram remains the center of attention.
- Task 10.13 downstream-JB first pass: added a guided `Add JB` topology mode and matching context-menu actions. The user selects the upstream `JB3PH`, selects 2-3 direct outgoing branch roots, confirms a new 4C trunk length defaulted from project setup `loop_ln`, and applies an audited `downstream_jb` topology edit. Server validation remains the source of truth: parent and child 3PH JBs are limited to three outgoing feeders in this pass, invalid indirect branch selections are rejected, and the edited SLD/cable schedule rows are generated from the persisted overlay. Drag/drop is deferred until the reassignment semantics are proven worth the added UI code.
- Task 10.14 strategy pivot: the SLD editor should move away from accumulating one-off workflow rules and toward guided graph operations. The persistence model remains `SLDTopologyEdit`; the change is the edit philosophy. Users should express electrical intent such as "feed this circuit from that JB", while reusable graph operations handle detach/attach, capacity validation, MCB rating recommendation, BOQ/cable-schedule impact, and audit. Full drag/drop remains deferred until these operations are stable enough to expose through richer gestures without turning the renderer into a fragile CAD subsystem.
- Task 10.15 branch move pass: extended the `Attach` interaction so the selected source can be a downstream branch component, not only an MCB. The server resolves the direct branch root fed by the source `JB3PH`, validates that the target `JB3PH` has spare capacity and shares the same upstream MCB tree, then rewires only the parent JB edge for that branch. This avoids asking users to split and recombine an already engineered manual topology just to move one outgoing branch.
- Task 10.16 selectable-link UX pass: SLD graph links can now be selected and inspected. A selected link can be used as the source for the guided `Attach` operation, meaning the user may right-click a connection and choose `Feed Downstream From JB`; the system uses the downstream component of that link as the movable source while keeping server-side topology validation. Raw delete-link/create-link editing remains intentionally blocked until there is a validated graph-operation layer behind it.
- Task 10.17 first refinement pass: branch moves between different upstream MCB trees are now allowed when the target is an eligible 3PH JB with spare outgoing capacity. The server estimates the moved branch rating from the source MCB/outgoing count, uprates the target MCB to the next configured breaker size, and keeps the edit review-required. Targeting a standalone MCB by automatically inserting a new 4C trunk/3PH JB remains a separate next slice.
- Task 10.17 second refinement pass: Attach can now target a standalone one-outgoing MCB for a selected downstream branch. The server promotes that target MCB to a proper 3PH distribution by inserting a manual `Cable4C -> JB3PH`, reconnecting the original outgoing feeder and moved branch under the new JB, and recommending the uprated target MCB rating. Multi-outgoing target MCBs still require selecting an existing target 3PH JB.
- Task 10.17 breaker rebalance follow-up: cross-MCB branch moves now recommend both sides of the breaker change. The moved branch rating is estimated from the source MCB divided by source-JB outgoing count; the source MCB is reduced for the remaining outgoing branches and the target MCB is uprated for the added branch. Added 2A to the standard project breaker choices so a 4A two-branch manual combine can reduce back to 2A when one branch is moved away.
- Task 10.17 breaker review UX follow-up: branch-move previews now show source/target breaker ratings as before, moved-load estimate, and recommended values instead of burying them in prose. Applied cross-MCB moves store previous/recommended breaker data on affected MCBs, affected MCBs render with a subtle amber review signal, and schematic MCB/JB labels now use the same readable label scale as cable labels.
- Task 10.17 interaction wording follow-up: right-click topology actions now use intent-based labels such as move branch/feeder, feed selected branch here, add downstream 3PH JB, and include in new downstream JB. Fit Line now also works from a selected/right-clicked link by fitting the connected line group, reducing the "what does this do?" ambiguity without adding another workflow.
- Task 10.17 close-out: drag/drop topology editing is deferred. The current guided graph operations now cover the tested reassignment cases with server validation, audit/reset behavior, breaker review, and BOQ/cable-schedule impact, while avoiding a larger CAD-like freeform editor. The context menu now exposes target capacity hints (`n/3 used`) and blocks full target JBs before preview, so the user gets clearer feedback without adding brittle raw link creation/deletion.

Carry-over items:
- [x] Add deeper domain/business-rule validation for `ProjectData` so admin-created setup/templates fail early on engineering constraints instead of only on field/model-level validation.
- [ ] Refine SLD presentation after the architecture phase: conventional SLD visual language, geometry/symbol sizing, text sizing, page layout, cable/spec label placement, and overall UI polish.
- [ ] Improve SLD interaction correctness: fully derived link routing on node move/reset, clearer grouping cues per line, and review/reset behavior for saved vs derived visual elements.
- [ ] Add scalable SLD browsing UX for large projects: server-side filtering by `line_id`, one-line focused browsing, collapsible validation panels, and other large-project readability improvements.

Next SLD follow-up queue:
- [x] Task 11.1: First UI cleanup block: remove redundant context-menu inspect actions, right-click-select the component/link before showing actions, compact/style the context menu, make topology mode buttons responsive, restore visible scrollbars for zoomed canvas work, and increase schematic MCB/JB/isolator label scale for readability.
- [x] Task 11.2: Engineering topology correctness: when manual operations insert a 3PH JB, insert the configured upstream/downstream isolator if project settings require it; when a 3PH JB is reduced to one outgoing branch, collapse it to the appropriate 1PH path instead of leaving a misleading 3PH distribution point.
- [ ] Task 11.3: Enable split for manually edited topologies, especially manually combined and branch-moved MCB trees, without forcing reset/recombine workflows.
- [ ] Task 11.4: Add scoped reset-to-generated for a selected MCB/downstream tree so one engineer can undo a local mistake without deleting unrelated manual edits elsewhere in the project.
- [ ] Task 11.5: Extend tracer inspection/editing: show tracer family and calculated alternate tracer options in the property inspector, then allow a controlled tracer selection override.
- [ ] Task 11.6: Repair SLD PDF export so exported output matches the visible SLD, including multi-page diagrams, links, labels, and edited topology geometry.

Progress notes:
- Task 11.2 first slice: manual topology operations that create a 3PH
  distribution path now mirror the generated incoming-isolator rule. Combine
  feeders, Add Downstream 3PH JB, and Attach-to-standalone-MCB insert
  `Isolator3PH` between the manual 4C trunk and 3PH JB when project settings
  are `bothSides` or `incomingOnly`. The remaining Task 11.2 slice is the
  reverse cleanup: collapsing a now-single-outgoing 3PH JB into the appropriate
  one-phase path when branches are moved away.
- Task 11.2 second slice: topology edits now run a conservative graph
  simplification pass after branch/feeder moves. A 3PH JB with exactly one
  incoming and one outgoing path is removed together with its single-purpose
  upstream 4C/isolator chain, and the upstream source is reconnected directly
  to the remaining branch root. This keeps manually edited SLDs from showing
  misleading one-outgoing 3PH distribution points while preserving the
  generated baseline for full reset.
- Task 11.3 first slice: Split now operates on the active SLD graph rather
  than refusing to run whenever a topology edit exists. This allows a manually
  combined MCB tree to be split without first resetting the whole project. When
  the split separates different original line IDs, those original line IDs are
  preserved; when it splits one generated multi-circuit line, the established
  `-part1`, `-part2` naming remains. More complex split semantics after deep
  branch moves/downstream JBs remain open under Task 11.3.
- Task 11.3 second slice: Split line-identity handling now detects mixed
  branch-move cases where a line still exists elsewhere in the active SLD. In
  those cases the split branch receives a `-partN` identity so the renderer and
  cable schedule do not accidentally regroup it with an unrelated remaining
  branch from the same original line. Distinct manually combined line IDs still
  split back to their original names when there is no collision.
