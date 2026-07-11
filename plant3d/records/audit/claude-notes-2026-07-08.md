# Claude Notes — Platform Reset Architecture Review

Date: 2026-07-08
Author: Claude (Fable), architect/auditor role
Status: active review notes — KR references findings to Codex by ID (F-xx) or line number
Inputs: reset handover, ecosystem plan, reset tracker, decisions 0001–0005, raceway RFC (2026-07-02), cable-routing vision (2026-07-06), both boundary contracts (2026-07-05), current `plant3d` code (models, urls, views, `package_viewer.js`, `routing_core.js`).

> Referencing convention: each finding has a stable ID (`F-01`, `F-02`, …). This file is append-only within a session; new sessions append a new dated section or start a new dated file, so IDs and line numbers stay stable once shared.

---

## 1. Decisions received from KR (2026-07-08)

Recorded here so Codex can read them directly:

- **D1 — Standard/market:** IEC 61537 is the default seed standard. Target market: Middle East, Asia, Europe. NEMA/ANSI support is a later addition, per-project configurable when it comes.
- **D2 — MVP containment scope:** Above-ground first — tray/ladder/sleeve. Underground (trench/duct bank) is deferred until after MVP integration. Core routing/path concepts should be designed to generalize to UG later (same principles, different nuances), but no UG-specific modeling now.
- **D3 — Consumer neutrality:** EHT must not be tied into `plant3d` or `raceway`. EHT is one consumer; lighting design is an explicitly planned future consumer (fittings, JBs, circuiting like the EHT SLD, installation 2D drawings). Cable assignment (Phase H) must therefore be designed as a consumer-neutral interface — any domain module assigns its cables to the raceway graph via loose anchors; `raceway` never imports `eht`.

---

## 2. Verdict

**The reset direction is correct and I endorse it without reservation.** Raceway/tray-first before cable autorouting matches real EPC practice (shared containment first, cable assignment second), and the failed experiments were correctly diagnosed: the software inferred too much before a graph and cost model existed to justify inference. The peer-app placement (`raceway → plant3d`, never back), the Stage 0 modular monolith, and the staged collision strategy are all right. The reset records themselves are high-quality handover hygiene.

`raceway` is the right name (covers ladder, tray, trunking, conduit, sleeve, duct — no rename needed when scope grows) and the right placement (peer of `eht`, consumer of `plant3d`).

## 3. Strong Agreement

- Route intent as source of truth, physical parts derived and regenerable — mirrors `plant3d`'s own source→package model.
- No domain persistence in `plant3d` core; `window.plant3dViewerLayers.register()` (verified present, `package_viewer.js:197`) is the correct extension seam and Codex already delivered several boundary-contract items (per-source JSON endpoint, top-level `coordinate_transform`).
- Suggestions must be explainable and user-accepted; the software must never silently become the design authority.
- Deferring Celery/Redis, service extraction, GLB bake, DXF drawings, and hard collision physics.
- Keeping the cable centerline tool as a manual/draft exception and a testbed for editing primitives.

---

## 4. Findings (Concerns / Must-Fix / Recommendations)

### F-01 — MUST FIX BEFORE PHASE B: coordinate-frame contract conflict (severity: high)

The reset tracker Phase 2 says: *"Store coordinates in plant3d render frame with explicit transform/package context."* The public API boundary contract (2026-07-05) says the opposite: *"External overlay data should store source/world coordinates or explicit anchors… browser-local coordinates are not enough for persistence."* These two active records disagree on the single most migration-painful schema decision.

**Recommendation: persist source/world coordinates, normalized to meters, with an explicit frame label.** Render-frame coordinates are tied to one package's RTC origin and axis swap; re-convert the source (new package, new tiling, new RTC origins) and every persisted run is orphaned or needs a data migration. Source/world frame is the durable truth; the render frame is a view, derived at load time through the documented RTC formula (`render = axis_swap(source) · scale − rtc_origin`). Engineers also think in plant coordinates and elevations (EL +106.500) — that is the source frame, not the render frame.

Codex should confirm or push back; whichever way it lands, correct the losing record so only one contract exists.

### F-02 — Stale orientation pointers (severity: low, quick doc fix)

Root `CLAUDE.md` stub and `NOTES/project_management/*` (last updated 2026-06-15) still present eht Phase A as the active work. A fresh session following only those pointers is steered to the wrong tracker. Fix: one-line updates pointing to `plant3d/records/tracking/platform-ecosystem-reset-tracker-2026-07-08.md` as the active tracker (eht Phase A remains parked, not cancelled). Also still open in the tracker: update `plant3d/records/README.md`.

### F-03 — Overlay JS injection seam is undefined (severity: medium, needed before Phase C/D)

`plant3dViewerLayers.register()` lets external code create a layer, but nothing defines how a peer app's JavaScript gets **loaded into the viewer page** without `plant3d` templates referencing `raceway` (which would invert the dependency at the template layer). Two clean options:

1. **Viewer extension config:** the `plant3d` viewer template exposes a generic, data-driven extension list (e.g., a context/setting listing extra static JS URLs + a mount hook), populated by project settings — `plant3d` knows "there are extensions," never "there is raceway."
2. **Consumer-hosted page:** `raceway` serves its own page that embeds/includes the plant3d viewer and adds its own script tag.

I lean toward option 1 (one shared viewer surface was the decided direction for EHT overlays; two viewer pages will drift). Codex to propose the mechanism before raceway overlay coding starts.

### F-04 — Raceway JS in a separate file from day one (severity: medium)

`package_viewer.js` is ~4,500 lines. Full modular split can stay a staged carry-forward item, but the minimum bar for the raceway MVP: **all raceway overlay/tool code lives in its own file(s)** (e.g., `raceway/static/raceway/js/raceway_overlay.js`), calling the registry seam — the new module never adds mass to the monolith. If Codex wants to split `package_viewer.js` first, sensible; but do not let the split become a blocking precondition for the raceway skeleton.

### F-05 — Loose references only, no DB FKs from `raceway` into `plant3d` rows (severity: high, day one)

Store `source_model_id` / `render_package_id` / `stable_id` anchors as plain integers/strings, exactly like `SourceModel.project_id`. A Django FK would work today but welds the schemas together against the Stage 1 extraction path (plant3d with its own DB/service). Converting FK→loose later is a migration; starting loose costs nothing. FKs *within* `raceway` (run→layer, node→run, run→family/size) are normal and correct.

### F-06 — Stable graph keys on runs and nodes from day one (severity: high, day one)

`RacewayRun` and `RacewayNode` each need a stable, non-recycled key (UUID) besides the auto PK, created at first save and never reassigned on edit. This is what Phase H cable assignment, junction/tee references, and future scenario comparison will anchor to. Retrofitting stable identity after users have live data is genuine migration pain; a UUID column now is free.

### F-07 — Cable assignment must be consumer-neutral (per KR decision D3)

Phase H's assignment shape should be: consumer module owns the cable record and holds `(raceway_run_key sequence / path, consumer_cable_ref)` on **its** side, or `raceway` holds a generic assignment row with `owner_module` + opaque `cable_ref` string — never an FK to `eht` tables and never `eht`-specific fields (no tracer/heat-trace vocabulary in `raceway`). This is the same `OverlayAnchor` philosophy one level up. EHT today, lighting tomorrow, generic power/instrument cables later — same interface. Not built now; but Phase H design must start from this rule.

### F-08 — Server-side validation from the first persistence pass (severity: high, Phase E)

Lesson already learned on the EHT side: routing rules that exist only in JavaScript are preview, not truth. When raceway save lands (Phase E), the server must independently validate: project access (gateway), payload shape, node count/ordering sanity, coordinate finiteness/bounds, family/size existence and validity. Never persist a browser draft unchecked. This is in the plan already — I'm pinning it as non-negotiable, not polish.

### F-09 — Units: normalized meters + explicit frame label stored with the data (severity: medium, day one)

The `idfviewer` mm-hardcode drift is the cautionary tale. Persist coordinates in **meters**, store the frame label explicitly (e.g., `coordinate_frame = "source_xyz_m"`), and keep catalogue dimensions in mm (industry convention for tray sizes) with `_mm` suffixed field names. Never leave a number's unit implicit.

### F-10 — Catalogue governance: generic seed, `is_validated` gate, no fabricated vendor data (severity: high)

The MI catalogue incident (5 of 72 seeded rows correct, KR-approved reseed required) is the project's most expensive data lesson. The raceway seed avoids the entire trap by being **generic and vendor-free**: curated IEC 61537-flavored families with conventional dimensions, making no vendor claims. Keep the `is_validated=False` default on families anyway (governance muscle memory), and when vendor parts arrive later, they follow the same rule as EHT: no vendor row enters as trusted without KR-reviewed source documents.

---

## 5. Answers to the review prompt's specific questions

### Q3/Q4 — Smallest useful MVP schema, and day-one fields

Five models, narrower than the RFC's full design (which remains the v2/v3 map):

**Catalogue (reference data, seedable, project-independent):**

- `RacewayFamily`: `code` (unique slug), `name`, `kind` (full enum from day one: `ladder | perforated | solid | mesh | trunking | conduit | sleeve | duct | trench` — enum values are free, geometry support is phased), `material` (default HDG), `standard_length_mm` (default 3000), `standard_basis` (default `"IEC 61537"`), `is_validated` (default False), `metadata` JSON.
- `RacewaySize`: FK family (`on_delete=PROTECT`), `width_mm`, `depth_mm`, optional `weight_kg_per_m` (nullable — feeds BOQ steel weight when known), unique (family, width, depth). Load/span tables deliberately absent (deferred with supports). Sleeve/conduit diameter: add a nullable `diameter_mm` later when sleeve geometry is actually built — additive, no pain.

**Routing (project truth):**

- `RacewayLayer`: `project_id` (loose char, indexed, gateway-validated), `source_model_id` (loose int — the source the layer is authored against, F-05), `name`, `status` (`draft | active | superseded`), created_by/timestamps. Keep it a thin container; no versioning machinery yet.
- `RacewayRun`: FK layer (CASCADE), `key` (UUID, F-06), `tag` (user-facing, blank ok), FK family + size (PROTECT), `service_class` (`power | control | instrument | telecom`), `status` (`draft | committed`), `coordinate_frame` (explicit label, F-01/F-09), `metadata` JSON, timestamps.
- `RacewayNode`: FK run (CASCADE), `sequence` (int), `key` (UUID, F-06), `x/y/z` floats (source frame, meters), optional `anchor` JSON (OverlayAnchor shape — `stable_id` snap evidence when snapped to structure), unique (run, sequence).

Day-one non-negotiables inside that: loose plant3d refs (F-05), UUID keys (F-06), explicit frame + meters (F-01/F-09), `service_class`, full `kind` enum, `is_validated` (F-10), PROTECT on catalogue FKs so a family delete can't orphan live runs.

### Q5 — Deliberately deferred

Supports (types, auto-placement, span tables), fittings library (MVP detects bends geometrically; no `FittingType` table yet), vendor/`VendorPart` overlay, derived-part persistence (`RacewaySegment`/`TrayFitting` rows — Phase F can start by computing these in memory/JSON before adding tables), GLB bake/render cache, DXF/fabrication drawings, cable assignment, fill/segregation numeric fields, trench/duct/UG modeling (D2), multi-layer revision workflows, Dijkstra/A*.

### Q7 — Minimal catalogue seed (per D1: IEC, metric)

Two or three generic families, vendor-free (F-10):

- `LADDER-HDG` — ladder, HDG steel, 3000/6000 mm lengths; widths 150/300/450/600/750/900, depths 100/125/150.
- `PERF-HDG` — perforated tray, HDG steel, 3000 mm; widths 100/150/200/300/450/600, depths 50/75/100.
- Optional third: `MESH-EZ` wire mesh basket, widths 100/200/300, depth 50/100 — cheap to seed, common in ME/Asia instrument work; fine to drop if Codex wants minimum.

Service classes seeded as choices, not a table: power / control / instrument / telecom.

### Q8 — Warning rules: MVP vs deferred

MVP (Phase D/E, all warning-only, computed live in the HUD/inspector):

- degenerate/very short segments; duplicate consecutive nodes,
- bend angle sanity (non-orthogonal bend flag as info, matching `routing_core.js` vocabulary),
- elevation discontinuity (accidental Z jump between nodes when a working plane is active),
- run has no committed family/size,
- route length + bend count display (not a warning, but the ambient evidence).

Phase G (post-persistence, still warnings): rough AABB clash vs reference model, support-span placeholder, fill/segregation placeholders. Deferred beyond that: BVH narrow phase, swept volumes, hard constraints. This matches the plan; no change requested.

### Q9 — What Codex should avoid building now

Auto-support placement; auto-fitting insertion beyond bend detection; any pathfinding (Dijkstra/A*); GLB bake; DXF output; vendor catalogue import tooling; hard collision stops; live anchor re-resolution machinery (snapshot anchors + a stated stale-risk note is fine for MVP); localStorage→DB sync cleverness (a plain save/load API is enough); UG trench modeling (D2).

### Q10 — Most natural EPC designer workflow

1. Pick family → size → service from the palette (recently-used on top).
2. Lock a working plane at a plant elevation — displayed as **EL +xxx.xxx in plant/source coordinates**, because that is the number on the designer's drawings (another reason for F-01 source-frame truth).
3. Click centerline nodes on the plane, snapping to structure (`stable_id` evidence recorded in node `anchor`), orthogonal snap as an explicit toggle — never silent.
4. Live HUD: length, elevation, bend count, family/size.
5. Riser up/down at a node to change plane (v2 if needed; MVP can accept plane re-lock).
6. Finish → run appears in inspector; edit nodes/properties; everything re-previews.
7. Save → server validates (F-08) → persisted in `raceway`.

The one thing that makes this feel professional rather than fiddly is the elevation-plane 2.5D discipline — free-3D dragging for every node is what made the cable experiments feel arbitrary.

---

## 6. Suggested Codex Next Pass

Matches the plan's pass 1, with one addition (c):

1. Decision record `0006-raceway-peer-app.md` — peer app named `raceway`, consuming `plant3d`; record D1–D3 from §1.
2. Scaffold `raceway` app + URL namespace + registration.
3. **Resolve F-01 first** (one-paragraph position is enough) and correct the losing record — before any model file is written.
4. Import-boundary tests: `plant3d` imports no `raceway` module; `raceway` accesses projects only via the gateway pattern.
5. Tracker checkpoint + F-02 pointer fixes.

Models (per §5 Q3/Q4) are pass 2. Viewer overlay (needs F-03 answered) is pass 3.

## 7. Suggested KR Manual Test (after pass 1)

Pure regression — nothing user-visible should change: upload IFC → `process_plant3d_job --watch --parser-threads auto` → open viewer → model renders complete → EHT draft tools still draw/save/restore locally → layer panel unchanged. Any visible difference after a skeleton pass is a red flag.

## 8. Open questions for Codex

- **C-1 (F-01):** Which coordinate frame do you consider authoritative for persisted raceway geometry? I recommend source/world meters; confirm or push back with reasoning.
- **C-2 (F-03):** Proposed mechanism for loading consumer-module JS into the viewer page without a `plant3d → raceway` template reference?
- **C-3 (F-04):** Split `package_viewer.js` before or after the raceway skeleton? Either is acceptable if raceway JS is born in its own file.
- **C-4:** Is `plant3d/overlay.py` (`OverlayAnchor` resolver/validator from the 2026-07-05 contract, not yet built) planned for Phase C, or do you consider the JS layer registry sufficient until Phase E persistence needs server-side anchor validation?

## 9. Parallel work I can pick up while Codex codes

Per the role prompt, ready on request: raceway MVP user-workflow/manual outline; IEC 61537 support-span/fill research note (feeds v2 catalogue fields); schema review checklist for pass 2; collision/pathfinding staging note refresh; test-plan recommendation for the raceway app.

---

## 10. Session addendum — Review of Codex skeleton pass (2026-07-08, later same day)

Scope reviewed: decision `0006-raceway-peer-app.md`, `raceway/` app (apps/urls/views/access/tests), `ELECSENSE` settings/urls diff, raceway MVP execution plan + progress tracker, reset-tracker updates.

**Independently verified:** `manage.py check` clean; `USE_POSTGRES=false manage.py test raceway plant3d` — 82 tests, OK. Boundary tests are real (filesystem import scans, not stubs). Access seam correctly routes through `plant3d.project_gateway` — no direct `eht` import in raceway runtime code.

**Resolved this pass:** C-1/F-01 closed in the recommended direction — source/world coordinates as durable truth, render frame derived — and consistently recorded in decision 0006, the execution plan, and both trackers. F-02 pointers, F-04 (raceway JS born outside `package_viewer.js`), F-05, F-07, F-10 are all correctly encoded in 0006/plan. Good pass; no boundary violations found.

### F-11 — Stage 3 plan omits the UUID stable keys mandated by decision 0006 (severity: medium — fix before models are coded)

Decision 0006 says "use UUID-style stable keys on runs and nodes from day one" (F-06), but the execution plan's Stage 3 field lists for `RacewayRun` and `RacewayNode` (raceway-mvp-execution-plan §Stage 3) have no `key` field. Codex will code from the plan's field list — add `key` (UUID, unique, non-recycled) to both models there so it doesn't silently drop.

### F-12 — eht-import boundary test is too narrow (severity: low, one-line tightening)

`raceway/tests.py::test_raceway_runtime_modules_do_not_import_eht_models_directly` only matches `"from eht.models import"` / `"import eht.models"`. It would pass `from eht import models`, `from eht.views import …`, or `import eht.pipeline`. Recommend matching any `from eht` / `import eht` (module prefix) in raceway runtime files — the boundary rule is "no direct eht dependency," not just "no eht.models".

### F-13 — Drop the "last resolved render-frame XYZ cache" field from `RacewayNode` (severity: low, advisory for Stage 3)

The plan's Stage 3 node list includes an "optional last resolved render-frame XYZ cache for viewer convenience only." Recommend not adding it: the RTC transform is trivially cheap at load time, and a persisted render-frame copy creates a staleness/ambiguity surface (two coordinate representations in one row, one of which can silently rot after reconversion) for no measurable saving. Derive, don't cache — if profiling ever proves otherwise, adding a nullable column later is painless.

### Housekeeping (no ID needed)

Progress-tracker "Decisions" block still shows "[ ] Record raceway as peer app" and "[ ] Confirm app name" unchecked although both are done (0006 exists; Stage 0 checklist marks them complete). Two-checkbox sync.

### Open KR decisions Codex is waiting on (from the plan's KR Decision Points)

- **Generic catalogue seed contents** — my proposal is in §5 Q7 above (LADDER-HDG + PERF-HDG, optional MESH-EZ; IEC metric widths/depths). KR to confirm or amend.
- **BOQ-first before drawings** — I recommend confirming yes (matches the raceway RFC Phase A reasoning; DXF is a large subsystem with no MVP payoff).

## 11. Verification of F-11/F-12/F-13 closure (2026-07-09)

Reviewed Codex's Stage 3–5 work (models + migration `0001`, admin, JSON API, viewer extension seam, `raceway_overlay.js`). **All three findings adequately addressed:**

- **F-11 CLOSED:** `RacewayRun.key` and `RacewayNode.key` are `UUIDField(default=uuid4, unique=True, editable=False, db_index=True)` (`raceway/models.py:137`, `:184`).
- **F-12 CLOSED (exceeds ask):** the eht-import guard was rewritten using AST parsing — it now catches every form (`import eht`, `import eht.x`, `from eht import …`, `from eht.x import …`), immune to string/comment false positives.
- **F-13 CLOSED:** `RacewayNode` stores only `source_x/y/z_m` + `anchor` JSON — no render-frame cache field. `coordinate_frame` is locked to `source_xyz_m` by model `clean()`; finite-coordinate validation present.

Also reviewed in passing, no findings:

- Extension seam is the F-03 "option 1" done right: a generic `PLANT3D_VIEWER_EXTENSIONS` settings list drives script injection in the viewer template; `plant3d` runtime code contains zero raceway references (only `plant3d/tests.py` asserts against the configured extension, which the boundary test correctly excludes). Registry gained `createGroup` support and a `plant3dviewer:layers-ready` event; raceway JS lives in `raceway/static/raceway/js/raceway_overlay.js` (F-04 honored).
- All raceway API endpoints are method-guarded (`require_http_methods`) and project-scoped (`require_project_access` directly or via `_layer_for_user`/`_run_for_user`); mutation stays session+CSRF per Stage 0.

Independently verified (2026-07-09): `manage.py check` clean; `makemigrations --check` no changes; raceway+plant3d 99 tests OK; full eht suite 360 tests OK (settings change caused no regression); JS syntax checks OK via `.mjs` copies; `git diff --check` clean.

## 12. Response to Codex's note — "parametric engineering proxy first, manufacturer assets later" (2026-07-09)

Context: the first Stage 6 authoring attempt was reverted after KR's manual check (draft row created, but canvas clicks/node commands unreliable). Codex asked whether the modeling conception should be written explicitly into the execution plan before the next Stage 6 attempt.

**Answer: yes — the conception is correct, and it should be written in.** It is already the implied direction in three places (raceway RFC §4 "parametric, generated — never a stored mesh per instance"; execution plan Stage 7's simplified preview; decision 0006's vendor-catalogue deferral), but nothing states it as a rule, and the failure mode it guards against — reaching for manufacturer 3D assets/part meshes to make the viewer look finished — is exactly the kind of long jump that just failed. Rules that live only in chat get lost; this one has earned a place in the plan's Architectural Rules.

### F-14 — Add the proxy-first rule to the execution plan's Architectural Rules (severity: medium, before next Stage 6 attempt)

Suggested wording Codex can adapt:

> Raceway 3D geometry is a **parametric engineering proxy** generated from centerline + catalogue parameters (kind, width/depth in mm). The proxy must be **dimensionally true** — its envelope drives clearance, clash, and fill reasoning — but visually simple: kind-differentiated styling (ladder rung hints, solid tray, translucent mesh) and service-class colour are enough. **Manufacturer/vendor 3D assets are a later presentation overlay** (with the same `is_validated` governance as all vendor data); they never replace parametric data as the source of truth, and BOQ/validation always derive from the parametric model, never from imported meshes.

Two boundaries inside that rule worth keeping sharp:

- Proxy envelope dimensions must come from `RacewaySize.width_mm/depth_mm`, not styling constants — otherwise the later clash/fill layers inherit cosmetic geometry.
- "Manufacturer assets later" is the 3D form of F-10: vendor meshes carry the same fabrication/trust risk as vendor data rows, plus scale/origin/licensing risk. They enter, if ever, through the vendor-part overlay stage, validated.

### F-15 — Define the extension interaction contract before re-attempting Stage 6 (severity: high — this is the actual root cause)

The tracker's own lesson is right; making it concrete: Stage 5's seam covers **rendering** (script loading, layer group registration) but nothing routes **interaction** to an extension — which is why raceway JS could register a group but not reliably receive clicks. Before the next Stage 6 attempt, define a minimal platform-side interaction surface, roughly:

1. **Tool registration/activation:** an extension declares a named tool; the viewer routes pointer events (down/move/up, click) to the *active* tool only, and tells the tool when it is deactivated (Esc, layer hidden, another tool activated). This mirrors how the EHT draft tools already interlock with measurement mode — the same arbitration, exposed generically.
2. **Pick/plane helpers:** platform-provided functions for "screen coords → working-plane intersection" and "screen coords → model raycast hit (feature id / position)" so extensions never touch the raycaster or camera internals directly.
3. **Coordinate helpers:** render↔source frame transforms for the active package exposed to extensions — raceway persists source-frame metres (F-01), so the overlay needs the package `coordinate_transform` without re-implementing the RTC math.
4. **A browser smoke test that performs real canvas clicks** before Stage 6 is marked complete — the Playwright pattern already exists in `eht.browser_tests`; reuse it. Static/HTML assertion tests cannot catch "clicks don't work," as this failure proved.

Keep the surface minimal (those three helpers plus tool routing are enough for centerline drawing); resist making a plugin framework out of it.

### Verification of the revert (2026-07-09)

Working tree clean; raceway+plant3d 99 tests OK; `manage.py check` clean; zero `raceway` references remain in `package_viewer.js` — the revert back to the Stage 5 seam is complete with no remnants.

*Caveat: Codex's full modeling-conception text was in chat, not in the repo; this review is based on the quoted phrase plus the existing records. If the conception text contains more detail (e.g., specific proxy geometry plans), paste it into the execution plan alongside F-14 so it is durable.*

## 13. Stage 6 completion review (2026-07-09, commit `1aea7e4`)

**Verdict: the Stage 6 rebuild is architecturally sound and closes F-14 and F-15 properly.** KR's manual test passing is consistent with what the code shows. Codex may proceed with Stage 7 on this foundation.

Verified in code and by test:

- **F-14 CLOSED:** proxy-first rule written into the execution plan's Architectural Rules; the implementation honors it — proxy envelope dimensions come from catalogue `widthMm/depthMm` (`runWidthM`/`runDepthM`), kind-differentiated visuals (ladder rungs vs tray cross-members), service-class colour.
- **F-15 CLOSED, all four items:** (1) `registerViewerInteraction` with activate/deactivate/cancel, `pick()` routes clicks to the active interaction, Escape cancels the interaction before falling back to EHT tools; (2) `pointOnSourceElevationFromViewerEvent`/`rayFromViewerEvent` pick helpers; (3) `sourcePointToRenderPoint`/`renderPointToSourcePoint` — **RTC math checked against the documented contract (§3.4 of the boundary doc): axis swap, scale, origin all correct, and the two functions are exact inverses**; (4) `raceway/browser_tests.py` performs real Playwright canvas clicks (draw, undo, select, move-with-elevation-preserved, delete, console-error assertion).
- Authoring stays in source-frame metres with the working-plane 2.5D discipline; overlay geometry is disposed on rebuild; panel HTML is escaped; all raceway JS remains in `raceway/static/`.
- Independently verified: raceway+plant3d 99 tests OK across 9 consecutive runs; `raceway.browser_tests` 1 test OK; JS syntax OK; `manage.py check` clean; F-14 plan text present; tracker claims match code.

New findings (none blocks Stage 7):

### F-16 — Browser smoke tests a synthetic host, not the real viewer (severity: medium, due by Stage 8)

`raceway/browser_tests.py` mocks `plant3dViewerRuntime`/`plant3dViewerLayers` in a bare page. That proves the **extension side** of the interaction contract, but not that the **real** `package_viewer.js` routes clicks correctly — which was exactly the Stage-6-v1 failure mode. Today the real-host half is covered only by KR's manual test. By Stage 8 (persistence), add one true end-to-end smoke: live server + real viewer page + small fixture package, the `eht.browser_tests` pattern. Until then, keep the manual canvas-click check in every Stage 6/7-touching pass.

### F-17 — Cross-tool arbitration is one-directional (severity: low-medium, small follow-up pass)

`pick()` checks the active extension interaction before measure/EHT handling, and Escape works — but activating Measure or an EHT tool does **not** deactivate an armed raceway interaction, so raceway draw mode silently swallows canvas clicks meant for the other tools (and vice-versa arrangements are ad hoc). Recommend a platform-level single-active-tool rule: activating any canvas tool (measure, EHT tool, extension interaction) deactivates the others. Small, contained change in the viewer.

### F-18 — Hardcoded JS catalogue placeholder must be replaced before Stage 8 (severity: low now, blocking at Stage 8)

`raceway_overlay.js` embeds a two-family catalogue (`LADDER-HDG`, `PERF-HDG` + sizes). Acceptable Stage 6 staging — but Stage 8 saves need server-side `RacewayFamily`/`RacewaySize` rows, so before then: seed the DB catalogue, expose a catalogue JSON endpoint, fetch it in the overlay, and make the JS ids equal the seeded `RacewayFamily.code` values. **This makes KR's still-open catalogue-seed confirmation a Stage 8 gate** — the JS placeholder is effectively a seed proposal (ladder 300/450/600, perforated 150/300/450); KR should confirm or amend it now so DB seed and UI don't drift.

### F-19 — One unreproduced test failure observed (severity: low, watch)

My first `raceway plant3d` suite run returned `FAILED (failures=1)`; nine subsequent runs were green and the failure did not reproduce, so I could not name the test. Likely a timing-sensitive plant3d worker/job test. Not a blocker, but a flake erodes trust in the verification baseline — Codex should watch for it and identify it when it next appears (capture `-v 2` output on failure).

### Housekeeping (no IDs)

- `plant3d/records/audit/eht_office.code-workspace` (IDE workspace file) was committed into records/audit — move it out or gitignore it.
- `scheduleBootstrap` gives up silently after 80 attempts; add a `console.warn` so future template drift doesn't invisibly remove the raceway panel.
- `window.plant3dViewerRuntime` exposes wide internals (scene, camera, raycaster, controls) alongside the helpers. Fine for Stage 0, but treat the raw internals as PROVISIONAL; extensions should prefer the helpers and their own layer group. Do not freeze this surface yet.
- Raceway drafts are in-memory only (lost on refresh) until Stage 8 — known, correct staging; noted so nobody mistakes it for a bug report later.

## 14. Stage 7 + Stage 8 review (2026-07-09, working tree; for Codex)

**Verdict: strong pass.** Stage 7 (parametric proxy preview) and Stage 8 (persistence) both land cleanly, and every open finding that was due by this point is now closed. Independently verified: `manage.py check` and `makemigrations --check` clean; raceway+plant3d **101 tests OK twice**; `raceway.browser_tests` **2 tests OK including the real-viewer end-to-end**; full **eht suite 360 OK**; JS syntax OK; `git diff --check` clean; migrations `0001`+`0002` confirmed applied on live PostgreSQL (read-only `showmigrations`).

### Closure status of prior findings

- **F-16 CLOSED (exceeds ask):** `RacewayRealViewerBrowserSmokeTests` is a genuine end-to-end smoke — live server, real `package_viewer` page, real canvas clicks, draw 3 nodes → finish → save → **page reload → runs restored from the DB**, asserting `serverRunId` and zero console errors. This closes the exact gap that caused the Stage-6-v1 failure. The synthetic-host test remains as a fast unit-level check — good layering.
- **F-17 CLOSED (bidirectional):** interaction `activate()` now deactivates other interactions, measure mode, EHT tool, and draft-move; conversely `setActiveEhtTool`/`setMeasureMode` deactivate the extension interaction, with an `onDeactivate` callback so raceway pauses its mode and tells the user. This is the single-active-tool arbiter as recommended.
- **F-18 CLOSED:** hardcoded JS catalogue removed; migration `0002_seed_generic_catalog` seeds the generic vendor-free IEC 61537 families (matching §5 Q7's proposal, `is_validated=False`, additive `get_or_create`, safe under the DB protocol); `/raceway/catalog/` endpoint added; overlay fetches, normalizes, and uses server PKs, with family/size codes carried in run metadata.
- **F-19 remains WATCH:** the flake did not reappear in 11 subsequent suite runs; keep capturing `-v 2` on any future failure.
- Housekeeping: `console.warn` on bootstrap give-up — done. **`eht_office.code-workspace` is still tracked in `records/audit/`** — still open, please remove/ignore it. `project_id` added to the package JSON is a correct additive contract change (it is already in the allowed-anchors list); note it as STABLE in the next boundary-doc revision.

### New findings (none blocking; smallest-first)

#### N-01 — "Reload Saved" silently discards unsaved local drafts (severity: low-medium)

`loadSavedRaceways({force: true})` replaces `state.runs` wholesale. A user who drew two runs, saved one, then clicks Reload Saved loses the unsaved run without warning. Cheap guard: if any run lacks `serverRunId` (or differs from its saved shape), ask for confirmation before replacing.

#### N-02 — No UI path to delete a saved run (severity: low)

The server supports `DELETE /raceway/runs/<id>/`, but the panel has no Delete Run action, so a saved-then-unwanted run is immovable from the UI. One button + confirm; natural companion to N-01.

#### N-03 — Partial-save reporting (severity: low)

`saveDrafts()` saves runs sequentially (run POST/PATCH, then nodes PUT). A mid-loop failure leaves earlier runs saved and later ones not, and the error status doesn't say which run failed. Include the failing run's tag in the status message. (A combined atomic run+nodes save endpoint is the deeper fix, but not worth building until something actually demands it.)

#### N-04 — Proxy envelope should come from the server run payload, not a client catalogue join (severity: medium — one small server change)

`runFromServer` resolves width/depth by joining `size_id` against the fetched catalogue, and silently falls back to **300×100** when the lookup fails. That lookup *will* fail in a real scenario: `/raceway/catalog/` filters `is_active=True`, so if an admin deactivates a size, every saved run referencing it silently renders with a wrong default envelope — a dimensionally-false proxy, which violates the F-14 rule that the envelope is engineering truth. Fix: `_run_payload` should embed the authoritative dimensions from the FK'd rows (`size.width_mm`, `size.depth_mm`, plus `family.kind`/`family.code`/labels), and the overlay should use those, keeping the catalogue join only for the palette. Server knows the truth; the client should never guess it.

### KR action

The seeded catalogue now exists in the live DB and matches the §5 Q7 proposal (ladder 300/450/600, perforated 150/300/450, HDG, IEC 61537, no mesh family). Please formally confirm this as the accepted MVP seed so the tracker's open "confirm generic curated catalogue seed" decision can be checked — or name amendments now, while changing it is still one small migration.

## 15. Anchor bridge pass review (2026-07-10; for Codex)

Scope: the two tracker entries after my §14 — "Plant Model Anchor Bridge" (N-04 fix + node-to-model anchoring) and "Raceway Anchor Elevation Fix."

**Verdict: good pass; N-04 is closed correctly and the anchor bridge is the right first plant3d↔raceway link.** Independently verified: `manage.py check`, `makemigrations --check`, JS syntax, `git diff --check` all clean; raceway+plant3d **101 tests OK twice**; browser tests **2/2 OK** (incl. real-viewer e2e); full **eht suite 360 OK**.

### Closures verified

- **N-04 CLOSED:** `_run_payload` now embeds authoritative `family` and `size` sub-payloads straight from the FK rows (`_run_family_payload`/`_run_size_payload` with `width_mm`/`depth_mm`/`kind`), and `runFromServer` uses them — the proxy envelope no longer depends on a client catalogue join, and a deactivated size can no longer silently produce a wrong envelope.
- **Elevation fix verified:** `selectedModelAnchorSourcePoint` is captured from the actual raycast hit at pick time (`package_viewer.js:4272`, `:4399`) and cleared on deselect; `attachSelectedModelToNode` adopts the anchor's source-z via `applyRunElevation`. Setting the whole run's nodes to the new plane is coherent with the 2.5D single-elevation run design — noted deliberately so it isn't later mistaken for a bug.
- Anchor capture has sensible fallbacks (feature pick → mesh → hierarchy → highlight bounds), and hierarchy-only selections still fall back to bounds center.

### New findings

#### N-05 — Persisted anchor JSON contains package-local `feature_id` (severity: low-medium, cheap fix now, expensive later)

`modelAnchorFromObjectSummary` spreads the full anchor into the node's persisted `anchor` JSON — including `feature_id`. The boundary contract is explicit: *feature ids are package-local render keys and must not be stored by external modules as durable identity.* `stable_id` is correctly present as the durable key, but a persisted `feature_id` is a trap: after the source is re-converted, it silently points at the wrong object, and someone will eventually "optimize" a highlight path by trusting it. Fix: strip `feature_id` before persisting (it is always re-resolvable from `stable_id` via the package sidecar), and treat `model_object_id`/`bounds`/`label` explicitly as display snapshots, not identity. Minor vocabulary note while touching it: the contract intended `owner_module` to name the consumer owning the element (`raceway`), not the provider — cosmetic, align when convenient.

#### N-06 — Server persists any dict as an anchor (severity: medium, natural next slice)

`_node_from_payload` passes `anchor` through a dict-shape check only; no content validation exists anywhere. That was fine while anchors were empty; now they are a real persisted feature. Recommend a minimal validator: allowed-keys shape, `stable_id` is a non-empty string when `anchor_kind == "model_object"`, and `source_model_id` in the anchor consistent with the run's context. This is the natural first slice of the long-deferred `plant3d/overlay.py` `validate_anchor` (question C-4 from §8, still open) — `raceway → plant3d` imports are the allowed direction, so a plant3d-side helper is the contract-conformant home, with the raceway view calling it at node-save time.

### Soft reminders — agreed items still open (no disagreement recorded, not yet implemented)

- **N-01:** "Reload Saved" still replaces unsaved local drafts without confirmation.
- **N-02:** still no UI path to delete a saved run (server DELETE exists).
- **N-03:** partial-save errors still don't name the failing run.
- **Housekeeping:** `eht_office.code-workspace` is still tracked in `records/audit/`.
- **F-19:** flake watch continues — still zero recurrences in my runs.
- **KR (not Codex):** formal confirmation of the seeded catalogue is still pending (see §14 KR action).

None of these blocks the next stage; N-05/N-06 are the ones I'd fold into the next coding pass while anchors are fresh.

## 16. Interaction-contract extension review (2026-07-11; for Codex)

Scope: the "Raceway Usability and Anchor Contract" and "Node Selection and Navigation-Safe Authoring" tracker entries, plus Codex's note asking whether the extended contract is enough for future lighting/support/cable tools.

**Verdict: excellent pass — every open Codex-side finding is now closed and verified. The findings register is clean for the first time since this file started.** Independently verified: `manage.py check`, `makemigrations --check`, JS syntax, `git diff --check` all clean; raceway+plant3d **102 tests OK twice**; browser tests **2/2 OK**; full **eht suite 360 OK**.

### Closures verified in code

- **N-01 CLOSED:** `confirmDiscardLocalChanges()` guards Reload Saved (and kindred discard paths), driven by real `dirty`/unsaved tracking rather than a blanket prompt.
- **N-02 CLOSED:** Delete Run button wired to `DELETE /raceway/runs/<id>/`, disabled when invalid, with confirmation.
- **N-03 CLOSED:** per-run save failures re-throw as `` `${run.tag}: <reason>` `` so the user knows which run failed mid-batch.
- **N-05 CLOSED:** `sanitizeAnchorForPersistence` builds a whitelisted anchor (no `feature_id`), sets `owner_module: 'raceway'` — both the trap and the vocabulary point fixed.
- **N-06 CLOSED — and C-4 finally answered:** `plant3d/overlay.py::validate_overlay_anchor` exists, with allowed-keys whitelist (so a stray `feature_id` is rejected server-side too), anchor-kind enum, `stable_id` required for model-object anchors, source-model consistency against the run, owner enforcement, and finite source-frame point checks. `raceway.views` calls it at node build time. This is the §4.3 contract shape from the 2026-07-05 RFC realized: a validator function, not a table. The regression test also asserts a rejected anchor payload does **not** delete existing nodes — good non-destructive failure discipline.
- Also verified: proxy orientation fix (authored elevation is now the tray **bottom** plane; rails/ticks extend upward), and `shouldIgnoreViewerCommitClick` is a single shared primitive that EHT's own `shouldIgnoreToolPlacementClick` now reuses — the platform and EHT converged on one implementation instead of two copies.

### Review of the contract extension itself

`raycastObjectsFromViewerEvent(event, objects, recursive)` is the right shape — a thin wrapper over the shared raycaster, so extensions pick their own handles without touching camera/raycaster internals. Host click dispatch now applies navigation suppression **before** forwarding to the active extension, with `onNavigationClick` as the courtesy callback. Raceway's use (invisible `node-hit-target` spheres, host raycast first, tolerant plane-pick fallback, miss falls through to model selection) is exactly how a consumer should sit on this seam. No defects found.

### Answer to Codex's question: is this enough for lighting/support/cable tools?

**Enough for cable assignment; two named gaps before lighting/support placement tools — and I recommend NOT building them yet.**

- **Cable assignment (Phase H):** needs panel/graph work plus picking *raceway's* rendered runs — already feasible today with `raycastObjectsFromViewerEvent` against the raceway layer's group children. Direct extension-to-extension picking is acceptable while co-located; a mediated "pick from layer X" helper is only worth adding if a third consumer ever needs it. No platform work required.
- **G-1 — model-surface raycast with normal (needed by lighting/support placement):** placing a fitting or support on structure needs "ray under cursor → model hit → `{source_point_m, source_normal, objectSummary}`". Today `getSelectedModelAnchor()` covers the select-then-place flow (with real hit point) but exposes no surface normal, and there is no hover-time model raycast helper. The EHT tools already compute surface-normal offsets internally — when lighting/support authoring starts, promote that logic into one runtime helper rather than writing it a third time.
- **G-2 — pointer-move routing (needed for ghost previews / true drags):** interactions currently receive clicks only. Click-commit authoring works (proven), but a ghost fitting under the cursor or a dragged handle needs an `onPointerMove` on the interaction config (throttled by the host).

Both gaps are additive and fit the existing shape; neither has a consumer today. Building them now would be speculative API — the same trap the routing experiments taught us to avoid. **Recommendation: reserve the two names/shapes in a short contract doc and build each with its first real consumer.** Concretely: the runtime surface is now large enough that a one-page `plant3d/records/planning/viewer-extension-contract.md` is warranted — listing the helper surface (contract, additive-only), the raw internals (`scene`, `camera`, `raycaster` — PROVISIONAL, may be withdrawn), the interaction config keys, and G-1/G-2 as reserved future entries. That way the lighting module starts from a document, not from reverse-engineering `package_viewer.js`. I can draft it as parallel work if KR/Codex want.

### Remaining reminders (short list now)

- **Housekeeping:** `eht_office.code-workspace` is *still* tracked in `records/audit/` — last surviving housekeeping item, one `git rm --cached` away.
- **F-19:** flake watch continues; still zero recurrences (13+ clean suite runs to date).
- **KR:** formal catalogue-seed confirmation is still the one open decision gating the tracker checkbox (§14 KR action).

## 17. Checkpoint commit review (2026-07-11, commit `5299d62`; for Codex)

Scope clarification first, so the record is honest: **this pass contains no new functional code.** Commit `5299d62` is a consolidation checkpoint — it commits, in one 2,260-insertion commit, everything I reviewed in §13–§16 (Stage 7 proxy, Stage 8 persistence, anchor bridge + elevation fix, usability/anchor-contract pass, node-selection/navigation pass, `plant3d/overlay.py`, all migrations, tests, and this notes file). The working tree is clean and byte-identical to the tree I verified in §16.

Re-stamped at HEAD: raceway+plant3d **102 tests OK**, browser **2/2 OK**, `manage.py check` clean. Nothing to re-review functionally — the §16 verdict stands, register still clean.

### F-20 — Commit granularity and message fidelity (severity: low, process — going forward only)

`5299d62`'s message ("Add catalog endpoint and seed generic catalog data") describes roughly one-sixth of what the commit contains — six distinct passes spanning two stages, a new platform module, and an interaction-contract extension. Two practical costs: `git log` archaeology will mislead anyone (including us) reconciling history against the tracker, and if the F-19 flake ever needs `git bisect`, six passes in one commit is the worst granularity for it. The tracker's verification-log entries are natural commit boundaries — **recommend one commit per tracker entry from the next pass onward**, with the entry's heading as the message's first line. Not worth rewriting history for; purely forward-looking.

### Soft reminders — same three, none disagreed, none yet done

1. `eht_office.code-workspace` has now survived into a second commit — still one `git rm --cached plant3d/records/audit/eht_office.code-workspace` away (add `*.code-workspace` to `.gitignore` while at it).
2. **F-19** flake: zero recurrences (now 14+ clean suite runs); stays on watch, nothing to do.
3. **KR** (not Codex): catalogue-seed confirmation from §14 remains the only open decision — the seed has now shipped in a commit, so confirming it (or amending) is increasingly just paperwork catching up with reality.
4. The **viewer-extension-contract one-pager** (§16, with G-1/G-2 reserved) is offered and unowned — if Codex agrees it's useful, say so and either of us can write it; if not, record the disagreement and I'll drop it from the reminder list.
