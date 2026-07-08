# Cable Routing Tool — Vision, Gap Analysis & Commercial Research

Date: 2026-07-06
Author: Claude (architect), at KR's request
Audience: KR + Codex
Status: research/vision RFC — analysis and proposals, not an instruction to build all of this

> **Codex housekeeping note, 2026-07-07:** this RFC correctly captured the route workflow as it existed on 2026-07-06, especially the then-current always-on Manhattan expansion. KR's subsequent manual testing rejected that UX as too unpredictable. The live viewer now uses **Centerline-first drafting** by default: source -> destination -> ordered centerline points -> finish route. `Ortho Assist` remains optional and explicit. Treat sections that describe always-on Manhattan expansion as historical analysis, not the current product direction.

## 0. Purpose

KR asked for three things in one: (1) understand the *complete* current cable-routing workflow, not just the latest diff; (2) an honest audit of what's done poorly or missing; (3) commercial-tool research and genuinely innovative ideas that would make this tool earn respect on ease of use, intuitive control, and features nobody else has built. This document does all three, grounded in the actual code as it exists today (verified by reading, not inferred from commit messages).

## 1. The complete workflow, as it actually exists today

Traced end-to-end through `package_viewer.js` and `routing_core.js`:

1. User selects a route tool (`cold_cable`/`tracer_sr`/`tracer_mi`) → state machine `idle → select_source → select_destination → edit_route`. Same-component source/destination is rejected at the transition (verified, [package_viewer.js:2459](../../static/plant3d/js/package_viewer.js#L2459)).
2. In `edit_route`, the user clicks rough "guide points." **These are not a separate ghost/preview the user later accepts** — `suggestManhattanRoute(guides)` continuously expands them into the actual rendered/committed route geometry. The guide points are control points driving a live Manhattan expansion, not a draft-vs-final two-step. (Worth a conscious confirmation this is the intended final UX, not an accidental simplification of the original Phase 3 "ghost suggestion, accept or reject" plan.)
3. Intermediate guide handles are draggable, **horizontally only**, constrained to the guide's current elevation plane (`THREE.Plane` at the guide's Y); source/destination endpoints are locked, non-draggable. Vertical adjustment is still via XYZ text fields.
4. A route HUD (this pass's addition) shows source, destination, length, segment/bend count, guide count, `substrate` (currently always `free_space` — a placeholder, not yet functional), and a warning count with a "next action" line, live-updating from `routeProfile()`.
5. `routing_core.js` now genuinely implements: `validateRoute()` with **block/warn/info** severity (same-source-destination and route-too-short = block; short segments, non-orthogonal segments, too-many-bends = warn; collinear nodes = info), and a clean graph primitive (`createRouteGraph`/`summarizeRouteGraph` — nodes, weighted/bidirectional edges, adjacency list, a `capacity` placeholder) ready for Dijkstra/A* to consume later.
6. Finish Route commits the element as a draft; Cancel discards cleanly. Drafts persist across page refresh via real `localStorage` (verified — not just in-session undo).
7. Selection tints blue (verified real). Node labels are hidden by default, shown contextually while editing/selecting.
8. **Nothing is persisted server-side.** No backend model, no multi-user, no audit trail — entirely browser-local. This is correct and deliberate per decision 0004, not a gap.

## 2. What's done poorly or genuinely missing (vs. correctly-deferred future work)

Being precise about the difference: persistence, collision physics, and raceway integration are *correctly staged* future work, not oversights — they're not on this list. What follows are things that look like unintentional gaps or inconsistencies.

1. **Routing logic exists only in JavaScript; nothing authoritative exists server-side.** Flagged in the last review, still true. `validateRoute`'s block/warn/info rules can be bypassed by anything that isn't the browser UI. Fine for preview; not fine once persistence lands without an independent server-side re-check.
2. **SR tracer auto-end-termination is not implemented.** Codex's own prior response named this as the obvious next behavior ("auto-create an End Termination on Finish Route if none exists"); it isn't in the code yet. Worth closing before this becomes a taken-for-granted assumption elsewhere.
3. **Live vs. snapshot anchor resolution — still unresolved.** A route's endpoint position is captured once at pick time and never re-queried. Move the anchored DB/JB afterward and the route silently stops matching it. This is a correctness trap waiting for a user to hit it.
4. **No unit tests for the pure routing math**, despite the module being purpose-built to be trivially testable (zero dependencies). Only text-content smoke checks exist. Cheapest fix on this whole list.
5. **The always-on Manhattan expansion (point 1.2 above) removes the "suggest, then accept or reject" step from the original plan** — possibly a deliberate, reasonable simplification, but it should be a *stated* decision, not something that happened as a side effect of implementation order.
6. **No connection-face rules yet** (DB/isolator top/bottom preferred; JB side/top/bottom; RTD/termination endpoint-only) — named in the original Phase 4 plan, not yet built.
7. **Vertical dragging is still a text-field affair**, not a proper 3-axis gizmo — already flagged, still open, and it's the single most "unpolished" interaction in an otherwise well-feeling tool.
8. **Bend-radius is a structural/angle heuristic, not real physics** — because cable diameter/type metadata doesn't flow into the route yet. Not wrong for now, but worth naming as the reason the current "many bends" warning is a proxy, not the real rule.

## 3. Commercial tool research — what's actually good out there, and what's realistic for us

Grounded in how the major EPC/BIM tools actually work, not generic buzzwords:

- **AVEVA E3D / SP3D (piping/cable routing):** parametric, catalogue-driven routing with automatic support placement; interference/clash reports; design-basis rule checks (segregation class, fill %) — but these are almost universally **batch reports run after modeling**, not live feedback while drawing. This is the single biggest structural weakness of legacy tools that our live-HUD approach (already started) directly improves on.
- **Revit MEP:** auto fitting-insertion on cable tray/conduit runs, "Automatic Route Solutions" that propose multiple ranked candidate paths, auto-generated schedules/tags. The "multiple ranked candidates, pick one" idea is worth borrowing once a real graph-search algorithm exists.
- **Navisworks:** clash detection and 4D construction sequencing, but it's a downstream review tool, not an authoring tool — relevant to our future collision-engine and construction-sequencing roadmap, not to routing itself.
- **ETAP and cable-engineering-specific tools:** ampacity/voltage-drop calculations tied to actual routed length; **cable-pulling tension calculations** (weight × friction × cumulative bend-angle) — almost always a **separate, offline, after-the-fact calculation**, run once a route is finalized, not integrated into the drawing experience. This is a second structural gap in the incumbents worth exploiting (§4, Idea 5).
- **Common thread across all of them:** they are single-user, desktop-licensed, check-in/check-out software. None of them do live multi-user collaboration, none show *why* an automated suggestion was made, and none let you compare routing scenarios side by side without committing. These aren't oversights on their part — it's because their data models and desktop architectures were never built for it. **That's our actual opening**, not "build more clash-detection" (a race we'd lose against 30-year-old, more mature engines) but "build the things a web-native, reactive tool can do that theirs structurally cannot."

## 4. Genuinely innovative ideas — ranked by novelty × buildability

Not a wishlist — five ideas, each tied to something already half-built, ranked so the cheap/high-value ones come first.

1. **Ambient Design-Compliance Dashboard (build first — natural extension of what exists).** The per-route HUD already computes live warnings. Extend it project-wide: a persistent "Project Health" panel aggregating warnings/length/fill across *every* drafted route in the session, updating continuously as anything changes — turning compliance checking from a batch chore (E3D/SP3D's model) into ambient awareness. This is the single most differentiated, cheapest-to-build idea here, because the warning/severity machinery already exists — this is aggregation and a panel, not new math.
2. **Explainable Routing ("why", not just "what").** Once real graph-search (Dijkstra/A*) lands, don't just show the winning path — show what it avoided and at what cost ("12% longer than straight-line, to keep 1.5 m clearance from Zone 3"). This is what turns automated suggestion into something an engineer trusts enough to sign off on, which is the whole "gain respect from users" goal stated directly. Cheap on top of the graph-cost model already built (`createRouteGraph`'s per-edge `cost`/`length_m` already carries what's needed).
3. **Cable-Pull Feasibility Preview.** Compute a rough pulling-tension estimate live, from the drawn route (cable weight/m × friction × cumulative bend-angle), and flag "may exceed practical pulling tension" *during* design. This is a real, well-known EPC pain point (pulling-tension problems are normally caught at installation, expensively) that even expensive commercial tools treat as a separate offline calculation. A first version needs only cable weight/diameter metadata (already partially planned for bend-radius) plus simple physics — no new infrastructure.
4. **Scenario Branching / What-If Comparison.** Since routes are currently pure JSON/localStorage anyway, let a user snapshot a named scenario ("Option A: direct" vs "Option B: via tray"), render both simultaneously in distinct colors/opacity, and compare total length/bend-count/clash-count side by side before committing. Legacy single-timeline tools structurally can't do this cheaply; we already have the cheap draft-state architecture that makes it natural.
5. **Live multi-user collaborative routing (Figma-style cursors/selection).** The biggest strategic differentiator against desktop-locked incumbents — but it requires the WebSocket/Celery-Redis infrastructure this project has deliberately deferred. Flag as high-value, explicitly gated behind that infrastructure decision, not a near-term build.

## 5. Recommended next steps (priority order)

1. Close the honest gaps first (§2 items 2–4, 6–7 are all cheap): SR auto-termination, live anchor resolution, unit tests for the pure functions, connection-face rules, the vertical-drag gizmo.
2. **Resolved 2026-07-07:** always-on Manhattan expansion is **not** the final UX. Centerline-first drafting is the default; Ortho/Manhattan behavior is an optional assist only.
3. Build Idea 1 (ambient compliance dashboard) as the first innovation pass — it's aggregation over machinery that already exists.
4. Then Idea 2 (explainable routing) once real graph-search lands, and Idea 3 (pull-feasibility preview) once cable diameter/weight metadata flows into routes.
5. Hold Ideas 4–5 as named, deliberate future bets — not because they're weak ideas, but because they're gated behind infrastructure/data this project has correctly chosen not to build ahead of proof.

## 6. Open questions for Codex/KR

1. **Resolved 2026-07-07:** always-on Manhattan expansion is not the intended final UX. Keep centerline-first drafting as the baseline; any future Manhattan/A*/Dijkstra suggestion must be explicit and accepted or edited by the user.
2. Priority: close the honest gaps (§2) before any innovation work, or interleave (e.g., ship the compliance dashboard now, close gaps in parallel)?
3. Does the ambient dashboard belong in the same left panel as the per-route HUD, or as a new, separate panel/tab — given panel real estate is already a stated UX concern from earlier passes?
