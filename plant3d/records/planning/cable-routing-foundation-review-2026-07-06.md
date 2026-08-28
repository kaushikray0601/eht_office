# Cable Routing Foundation — Claude Review (Phases 1–6)

Date: 2026-07-06
Author: Claude (architect), reviewing Codex's plan in `pipeline-spike-tracker-2026-06-22.md` ("Next Big Coding Step — Source/Destination-First Cable Routing Foundation")
Lifecycle note, 2026-08-28: historical review of the cable-first routing
foundation. Phase H should use the later Raceway graph/pathfinding records,
especially `raceway-clash-pathfinding-staging-2026-08-28.md`.
Status: review/guidance for Phase 1 kickoff — not an instruction to change the phase order

## Verdict

Endorse the plan as written. Phasing, non-goals, and the explicit "what Claude can help with" ask are all sound. This document answers the five requested topics and adds structural risks found while reasoning through them — fold into Phase 1/2/6 before coding, not as new phases.

## 1. Route state-machine — gaps to close before Phase 1 coding

States `idle/select_source/select_destination/edit_route/review_route` are the right skeleton. Gaps:

- **Reject source == destination at the `select_destination → edit_route` transition**, not deferred to Phase 4's rule layer. A degenerate zero-length route reaching `edit_route` risks divide-by-zero in Manhattan math and a degenerate bbox for collision. Cheap check now; expensive to retrofit after Phase 2/5 are built against the assumption it can't happen.
- **Missing first-class transition: re-opening an already-committed route.** The five states describe author-once-linearly; real usage includes editing a saved route later. That's `idle → edit_route` with anchors pre-populated from the saved route, skipping selection states — name it explicitly rather than letting it fall out of whatever the hierarchy-panel click handler does.
- **Define anchor resolution as live, not snapshot.** Once locked to a component anchor, the rendered endpoint should re-resolve that component's current position every render — the entire point of anchoring vs. raw coordinates. This is exactly the `OverlayAnchor` "snapped" semantics from `plant3d-platform-boundary-contract-2026-07-05.md` — build the route's anchor resolution against that shape, don't invent a second one.
- **Escape/Cancel target:** define once — Escape from any in-progress state returns to `idle` (matches the existing EHT draft Cancel pattern), not a single-step backward walk through states.

## 2. Routing algorithm abstraction

Codex's Phase 2 shape (stable output contract, swappable implementation, `suggest_manhattan_route` first) is correct. Additions:

- **Manhattan = a "lift → transit → drop" heuristic, not a search.** Rise to a safe transit elevation, move in fixed-order axis-aligned segments, descend to destination — the standard first-pass approach real plant-routing tools (Plant3D/SP3D nozzle-to-nozzle routing) use. This is what should drive Codex's own Phase 3 ghost preview.
- **Implement one graph-search function, not two.** A* is Dijkstra with a pluggable heuristic (zero heuristic = Dijkstra exactly). Don't build them as separate code paths.
- **Design the graph abstraction (nodes + weighted edges + cost function) as a generic placeholder in Phase 2 now**, even before anything populates it. This is the shared primitive between "route through free space" (today) and "route through a tray network" (raceway, later, per its own graph-readiness principle). Skipping this risks a rewrite when raceway's graph routing arrives instead of a drop-in swap.
- **Sequencing:** Manhattan-heuristic now (no obstacle model needed) → Dijkstra once a real graph with real edge costs exists and is small (hundreds–low-thousands of nodes) → A* only once that graph is large enough that Dijkstra visibly lags. Don't build A* ahead of that proof point.

## 3. Electrical rule checklist (first pass)

**Structural recommendation first:** give every warning a `severity: "block" | "warn"` field from day one, not a flat warning concept. Most rules below are advisory; a genuinely dangling/unterminated cable end should hard-block commit. Retrofitting severity after users depend on flat behavior is painful.

- Endpoint compatibility: `cold_cable` — DB/JB/isolator ↔ JB/isolator/equipment (DB↔DB = advisory-warn). `tracer_sr`/`tracer_mi` — must start at a powered DB/JB, must terminate at an End Termination (already well-scoped by Codex's (i) answer). Clarify with KR whether RTD wiring uses this workflow at all, or is always a short direct connection.
- Same source/destination — belongs at the state-machine level (§1), not here.
- Minimum bend radius (12–15× diameter) — for today's polylines, this is "sharp turn within short node spacing," not a true curve check (curved-bend geometry is future work per Codex's own Phase 3 note).
- Maximum unsupported span — same underlying concept as raceway's future support-spacing/load-table rule. Share the `RouteWarning(code, severity, message)` shape across both now so they converge rather than diverge later.
- Segregation between service classes — too early without tray context; share vocabulary only.
- Terminal/device capacity ("too many cables on one device") — needs per-component-type capacity metadata; belongs in the EHT tool catalogue (`eht_tools.py`), not `plant3d`.
- Unrealistic open cable end → **block**, per the severity split above.

## 4. Collision engine staging

Codex's staging (bounding box → BVH → swept volume → clearance envelopes → search cost) is exactly the standard game-engine broad-phase/narrow-phase pipeline — well-trodden, not a research problem.

- **Broad phase is buildable today, zero new infrastructure.** `ModelObject.bounds` is already a populated JSONField (confirmed in `plant3d/models.py`). AABB-vs-AABB against nearby `ModelObject.bounds` is the entire MVP.
- **Narrow phase should reuse `three-mesh-bvh`** — already recommended earlier in this project for fast picking. One BVH per loaded tile serves both picking and collision; don't build a second spatial index.
- **Swept volume, pragmatically:** true continuous collision detection is genuinely hard — use discrete sampling along the path (test every N cm), which is what real engines do in practice. State this so nobody feels obligated to solve continuous CD analytically.
- **Placement:** geometry primitives (AABB test, BVH query, sweep sampling) are domain-neutral → `plant3d/collision.py` (mirrors the small-gateway-module pattern of `project_gateway.py`). What counts as a *violation* (cable-vs-structure = bad; tray-vs-designated-support = fine) is domain-specific → belongs in the consumer module.

## 5. Persistence model review — the sharpest risk in this plan

Checked: **no EHT-integration app exists yet** — only the main `eht` app. Phase 6 needs an explicit decision (extend `eht`, or scaffold a genuinely separate integration app), not an implicit one.

**The one non-negotiable:** route source/destination anchors must be loose references (package id + `stable_id` as plain values, validated through a `plant3d`-provided lookup — the same pattern as `project_gateway.validate_project_id`), **never** a real Django ForeignKey into `plant3d.ModelObject`/`RenderPackage`. This is the identical mistake Stage 0 just spent real effort undoing (the `CASCADE` FK to `eht.ProjectData`), one layer up. A hard FK here quietly recreates `EHTDesignElement` — the exact anti-pattern the whole `plant3d` reframing exists to avoid. Also store the coordinate-frame/RTC-origin reference alongside route nodes (which package's origin they were authored against) — the same discipline `OverlayAnchor` already carries.

## Cross-cutting observation

All five areas independently converge on the same three things built over the last several passes: the `OverlayAnchor` shape, the layer-registry contract (`window.plant3dViewerLayers`), and the loose-reference discipline from Stage 0. That convergence is a good signal — the boundary work wasn't abstract; it's what this feature actually needs.

## Open questions for Codex/KR

1. Does RTD wiring go through this route state machine at all, or is it always a direct/short connection outside it?
2. Extend the existing `eht` app for route persistence, or scaffold a separate EHT-integration app now (Phase 6 decision, needed before Phase 6 starts, not during)?
3. Confirm live anchor-resolution (not snapshot) is the intended semantic before Phase 1 rendering code is written against one assumption or the other.

## Follow-up — 2026-07-06b: routing_core.js + draggable guide handles pass, reviewed

Verified in code (not from the commit description alone). 73 tests green, `check` clean.

### State-machine gaps from §1 — 2 of 3 already closed, 1 still open

- **Same-source/destination rejection: CLOSED.** `setRouteDestinationAnchor` ([package_viewer.js:2459-2463](../../static/plant3d/js/package_viewer.js#L2459)) checks `anchor.element.id === routeSourceAnchor.element.id` and rejects before the state transitions to `edit_route`. Exactly the fix recommended, at exactly the right point.
- **Re-opening an existing route: CLOSED.** `editDraftRoute` ([package_viewer.js:2510](../../static/plant3d/js/package_viewer.js#L2510)) reconstructs source/destination anchors from the saved route's metadata and re-enters `edit_route` directly — the named `idle → edit_route` transition I recommended.
- **Live vs. snapshot anchor resolution: STILL OPEN.** `anchor.point.clone()` is captured once at pick time ([package_viewer.js:2452](../../static/plant3d/js/package_viewer.js#L2452), 2466) and never re-queried from the source component's current position. If a DB/JB is moved after a route is drawn to it, the route will **not** follow. Needs an explicit decision (accept for v1 vs. fix now while the anchor model is still small) before more phases build on top of an ambiguous semantic.

### New finding — the routing core quietly became JavaScript-only; the original Python location doesn't exist

- Severity: **MEDIUM (architecture fork, needs an explicit decision before Phase 4/6)**
- The original plan (§2 above, and the tracker) named `plant3d/routing/` — a Python location. Confirmed: **`plant3d/routing/` does not exist.** Instead, `routing_core.js` (verified genuinely pure — zero DOM/THREE imports, plain data-in/data-out functions, real `export`ed functions, actually imported and called from `package_viewer.js`) is the only routing core that exists.
- This is fine for **preview** (see chat discussion — client-side is the correct choice for drag-to-reshape). It is a real risk if Phase 4 (electrical rules) and Phase 6 (persistence) end up validating routes **only** in JS, because client-side logic can't be the authoritative gate for data that will become real construction/fabrication drawings — a non-browser caller (bulk import, future API consumer, a devtools-savvy user) could persist a route that never passed validation.
- Recommend: treat this pass's JS module as the **preview-only** half of the eventual split; when Phase 4/6 land, the save/commit endpoint must independently re-run the authoritative version server-side (Python) before persisting, not trust whatever the client posts. Some duplication is fine and normal here (same pattern as client+server form validation) as long as the server side is the actual gate.
- Status: **OPEN — needs an explicit decision, not silent continuation**

### Minor findings

- **No behavioral unit tests for the pure functions.** The only coverage is Python tests asserting the served JS file's *text* contains `"export function suggestManhattanRoute"` etc. ([tests.py:2077](../../tests.py#L2077)) — a smoke check, not a correctness test. Since the module has zero dependencies, real tests (plain Node.js assertions on `suggestManhattanRoute`/`routeLength`/`routeDiagnostics` output) would be cheap and are exactly the payoff the "pure, extracted module" design was meant to unlock. Worth doing now while the functions are still simple.
- **Default axis order (`['x','z','y']`) adjusts elevation last**, not first. Given the render frame's Y is elevation, this means the heuristic moves horizontally at the *starting* component's height and only rises/descends at the very end — generally less collision-safe in a real plant than lifting to a safe transit elevation first, then moving horizontally, then dropping (the "lift-transit-drop" pattern recommended in §2). Not a bug — collision-awareness doesn't exist yet — but worth reconsidering the default order once Phase 5 lands, since it's a one-line change now vs. a behavior change later.
- **Drag-handle claims verified accurate, not overclaimed:** source/destination confirmed non-draggable (`draggableRouteGuide = !isEndpoint`); the "horizontal-only, elevation plane" limitation is real and precisely matches the claim (`THREE.Plane(new THREE.Vector3(0,1,0), -guidePoint.y)` — a plane at the guide's current Y, so drags can't move it vertically). Honestly scoped, not a hidden shortcut.
