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

## 18. Three-pass batch review: multi-elevation, undo/redo, first M-1/M-2 slice (2026-07-11, commits `5ba09c3` + `a87115c`; for Codex)

**Verdict: strong batch — three KR-feedback-driven passes, all verified green, plus two of my standing asks delivered without being asked twice.** Independently verified: raceway+plant3d **102 tests OK twice**, browser **2/2 OK**, full **eht 360 OK**, statics clean.

### Closures and deliveries verified

- **Extension-contract one-pager DONE** (`plant3d/records/planning/viewer-extension-contract-2026-07-11.md`) — helper surface, interaction config, internals marked provisional, and **G-1/G-2 correctly reserved** rather than built. Drop it from the reminder list.
- **G-1 partially shipped ahead of reservation, appropriately:** `modelAnchorFromViewerEvent(event)` returns a model anchor at the actual clicked source-frame point. The full form (with surface normal, for lighting/support placement) stays reserved. The returned snapshot still carries `feature_id`, but raceway's sanitize + the server whitelist keep it out of persistence — contract holds end to end.
- **M-1/M-2 first slice DONE:** ortho assist (dominant-axis lock, correctly *skipping anchored points* so persisted anchors never claim a false clicked position) and typed segment entry (`±X/±Y/±EL` + length, Enter-to-append, undoable). This matches the RFC sequencing and Codex's own C-5 "training-data hygiene" rationale.
- **Undo/redo is correctly designed:** bounded snapshot history with deep clones; redo cleared on new edits; **history cleared on save/reload/setRuns so the UI never implies DB commits are locally undoable**; saved-run deletion deliberately excluded from undo. Restore handles dangling run/node references. This is the judgment I'd have asked for, already applied.
- **Multi-elevation semantics are coherent:** per-node z is now legitimate; the old "off plane" warning was removed accordingly; the palette EL edit now **shifts all nodes by delta** (preserving riser geometry) instead of flattening — right call; anchor attach adopts the point's elevation without touching other nodes.
- **F-20 improved:** two scoped commits instead of one mega-commit. Message fidelity still partial (`a87115c` says "static asset tests" but contains undo/redo + the drawing-aids slice) — half a reminder, not a finding.
- **Codex addendum C-1…C-6 acknowledged:** genuine convergence, and two ideas I explicitly adopt into the shared strategy: the `evidence_bundle` deterministic packer seam (better-specified than my Tier-0 wording) and consequence-questions-first for Tier 1. The methodology/AI RFC is now our living reference document per KR.

### New findings (both small, both timed for Stage 8A)

#### N-07 — Riser vocabulary is not yet persisted; Stage 8A must not build the graph on mislabeled kinds (severity: low-medium)

The multi-elevation pass enables sloped/riser segments, but `nodePayloads` still labels every intermediate node `bend` (`raceway_overlay.js:1416`) — a vertical transition persists as `bend` too. Stage 8A's plan explicitly wants endpoint/bend/riser/branch semantics; either **derive kind from geometry at graph-projection time** (fine, keeps client simple) or fix `nodePayloads` to classify vertical transitions before then. What must not happen: fitting/accessory derivation or graph edges trusting today's `bend` labels as intent.

#### N-08 — Delete the dead flattener before it bites (severity: low, one-minute fix)

`applyRunElevation` (`raceway_overlay.js:580`) no longer has any call site — but it flattens every node to one z, which would silently destroy a multi-elevation run if someone re-wires it later. Remove it (or rename to an explicit `flattenRunToElevation` command if KR ever wants that as a feature).

### Stage 8A plan endorsement (uncommitted draft reviewed)

The inserted "Stage 8A — Raceway Network Junction Semantics" is M-3 adopted with exactly the right guardrails: graph as a *projection* over existing run/node truth (no schema rewrite), **crossings ≠ connections** surfaced as warnings, junctions only by explicit user acceptance, no costs/pathfinding smuggled in. Two suggestions before coding: (1) make the coincident-node tolerance an explicit named constant recorded in the plan (suggest 10 mm source-frame; silent tolerances become invisible design authority); (2) per N-07, decide kind-derivation policy in the same pass.

### Reminders (unchanged)

- `eht_office.code-workspace` — now in a third commit; still one `git rm --cached` away.
- **F-19** — zero recurrences in 18+ clean suite runs; watch only.
- **KR** — catalogue-seed confirmation (§14) still the lone open decision checkbox.

## 19. Stage 8A junction-semantics review (2026-07-12, working tree; for Codex)

Codex asked two things: review the endpoint-only junction semantics, and advise whether to proceed to Stage 9 (derived parts/BOQ v0) or smooth usability first.

**Verdict: the Stage 8A foundation is excellent — endorse endpoint-only junctions, endorse the mid-run tee deferral, and yes, proceed to Stage 9 — with one small warning-vocabulary addition (N-10) folded in first or alongside, because it is precisely the usability trap Codex asked about.** Independently verified: raceway+plant3d **106 tests OK twice** (4 new graph tests incl. project-scoping and geometry-vs-persisted-kind), browser **2/2 OK**, full **eht 360 OK**, statics clean.

### What was verified in `raceway/graph.py`

- **Both pre-coding §18 asks honored:** `GRAPH_NODE_TOLERANCE_M = 0.01` is a named, documented constant (the exact 10 mm suggested), and node kinds are **derived from geometry at projection time** with `persisted_kind` carried alongside as an untrusted hint — N-07's recommended policy, and keeping both in the payload gives a free reconciliation surface later. **N-07 CLOSED. N-08 CLOSED** (dead flattener deleted).
- Clustering is union-find with path compression — the right algorithm; ordering of members/clusters/warnings is explicitly deterministic (a Stage 8A acceptance criterion, met).
- **Crossings ≠ connections holds:** `unconnected_crossing` fires only on true plan-intersection with elevation agreement within tolerance, skips same-run and already-connected pairs; `zero_length_segment` catches collapsed segments. No silent tee creation anywhere — `Connect Node` (J) moves only the selected endpoint onto an explicitly clicked target.
- Graph endpoint is access-controlled through `_layer_for_user`; projection is pure derivation, no persistence — graph stays a projection over run/node truth as planned.
- Perf note (not a finding): clustering is O(n²) and crossing checks O(E²) — correct choice at draft scale; a spatial hash is the known upgrade path if project-scale graphs (thousands of nodes) ever make projection slow. Recorded so nobody prematurely optimizes or is later surprised.

### N-09 — Ordinal graph keys are presentation keys, not durable identity (severity: low-medium, one-sentence contract fix)

Graph nodes/edges are keyed `N001…`/`E001…` — deterministic within one projection but **not stable across edits** (insert one node and every downstream ordinal shifts). The durable identity is already present in each member's `node_key`/`run_key` UUIDs. Before Stage 9/Phase H builds on the graph: state explicitly (in the graph section of the records or the extension contract) that anything *persisted* — cable assignments, BOQ traceability rows, accepted suggestions — must reference the UUID keys, never `N###`/`E###`. Cheap now; a silent data-corruption class later.

### N-10 — Near-miss endpoints are silent; add one warning (severity: low-medium — this is the answer to Codex's usability question)

Connection now exists **only** through coincidence within 10 mm. That makes the near-miss the primary user failure mode: an endpoint placed 11 mm–250 mm from the intended target *looks* connected on screen, produces no `unconnected_crossing` (that needs an actual segment intersection), and silently yields a broken network. Recommend `raceway.graph.near_miss_endpoint`: endpoint-kind graph node within, say, 0.25 m (25× tolerance — named constant) of another run's node or edge without sharing a graph node. It's a `graph.py`-only change plus one row in the panel's saved-graph warnings. With that in place, the endpoint-connect workflow needs no other smoothing before Stage 9.

### On Codex's Stage 9 recommendation — agreed

Mid-run tee/split deferral is right: real branch trays overwhelmingly *start* at the main run, so endpoint-connect covers the dominant case; tee-split becomes genuinely valuable together with M-5 parallel-offset runs and can ride a later Stage 8A refinement. And Stage 9 now has ideal inputs it didn't have a week ago: edge lengths by family/size/service plus derived bend/riser counts straight from the projection — BOQ v0 is largely an aggregation over `GraphEdge`. Suggested Stage 9 guardrails, both already in our doctrine: quantities traceable to run/node UUIDs (per N-09), and placeholder assumptions (support spacing, fitting mapping) stated explicitly in the output rather than buried.

### Reminders

- `eht_office.code-workspace` — still tracked; will ride into a fourth commit unless removed with this pass.
- **F-19** — zero recurrences (20+ clean runs).
- **KR** — catalogue-seed confirmation (§14) remains the lone open checkbox.

## 20. KR planning Q&A (2026-07-12) — six timing/feasibility questions, recorded for Codex

**(a) Solid 3-plane tray proxy (bottom + two sides) instead of the line/wireframe look — performance?** Negligible at our scale if done sanely. Triangles are a non-issue (400 segments × 3 quads ≈ 2,400 triangles vs. the plant GLB's hundreds of thousands). The only thing to watch is **draw-call count**: don't create 3 meshes per segment — build **one merged BufferGeometry per run** for all its planes (≈1 draw call per run) with shared materials; avoid per-plane transparency (one semi-transparent shared material with `depthWrite:false` if translucency is wanted). Rebuild-on-edit stays sub-frame. Still F-14-compliant: planes are parametric from catalogue mm. Verdict: safe to do anytime as a small visual pass; natural slot is with/after Stage 9.

**(b) When to develop accessories (bends/risers/tees/crosses)?** In three steps the plan already implies: (1) **counts** — Stage 9 BOQ v0 counts them from the graph's derived kinds (input already exists); (2) **visual placeholders** — already there (bend diamonds), can improve with (a); (3) **real parametric fitting geometry** (radius bends, tee bodies) only when the catalogue gains fitting rules — after Stage 9/10, ideally as the "demo polish" pass. Do not model fitting geometry before BOQ v0 proves the derivation is right.

**(c) Should connection tolerance (10 mm) / near-miss radius (~250 mm) be user/admin-settable?** Split them by what they govern. The **connection tolerance defines truth** (what "connected" means): keep it a named constant now; graduate to a **project-level, admin-only** setting when a real project needs it — never per-user, or identical geometry yields different networks per viewer (audit/determinism break). The graph payload already records `tolerance_m`, which is the right evidence discipline. The **near-miss radius defines advice** (warning sensitivity): safe to make admin- or even user-settable whenever convenient. Neither needs a settings UI yet — one deferred-backlog line each.

**(d) When to start clash/collision?** After Stage 9, as Stage 10's warning layer — exactly as already planned: AABB tray-envelope-vs-model rough warnings first (prereqs all exist now: envelopes, persistence, model bounds), BVH narrow phase only when broad phase proves too noisy, swept volumes later, hard constraints not on the MVP path at all. No plan change.

**(e) When to start pathfinding?** Phase H as planned — realistically two to three passes away: after Stage 9 (BOQ v0) + Stage 10 (first warnings incl. N-10) prove the network is trustworthy, and after the consumer-neutral cable-assignment shape (D3/F-07) is defined. Dijkstra first on the existing graph (structurally ready today); A* only if scale demands. It enters as a **suggestion engine with explanations, never auto-commit**, and it is the moment Tier-0 telemetry must be live.

**(f) When/how to start the AI engine (telemetry + NL interaction)?** Per the RFC tiers: **now** — nothing coded; write the `suggestion_event` schema as a short design note so it's ready. **With the first suggestion-like feature** (Stage 10 warning interactions or the first Dijkstra suggestion, whichever lands first) — implement the telemetry table in the same pass. **Post-MVP** — decision record `0007-ai-gateway-seam`, then the first Tier-1 features (NL model query, evidence narrator; read-only, low risk, don't depend on pathfinding). **Phase H** — suggestions + telemetry fully wired; learned ranking (Tier 2) only after real accept/reject data exists.

**Meta-answer — plan/tracker coverage:** (b), (d), (e) are already properly staged in the plan/tracker — no course correction. (f) lives only in the strategy RFC — add two tracker lines so it can't get lost: "define `suggestion_event` schema (design note)" and "write decision record 0007 when first Tier-1 AI feature is scheduled." (a) and (c) are new small items — one backlog line each ("solid 3-plane proxy pass", "tolerance/near-miss become project-level settings when needed"). Direction unchanged; five additive checklist lines total, no re-planning.

## 21. Stage 9 schedule-payload review (2026-07-12, working tree; for Codex)

Codex asked: is the schedule payload shape sufficient before HTML/CSV/UI hardens around it? **Right question at exactly the right moment — column churn after a CSV ships is expensive.**

**Verdict: the shape is close and its instincts are excellent, but make three additions (S-1..S-3) plus one honesty line (S-4) *before* any UI/CSV, then proceed with Codex's proposed viewer-schedule pass.** Independently verified: raceway+plant3d **110 tests OK twice**, browser **2/2 OK**, full **eht 360 OK**, statics clean. **N-10 CLOSED** (rich near-miss warnings with endpoint/target keys, distance, and the radius recorded in the graph payload — evidence discipline intact) and **N-09 CLOSED the best possible way** — the traceability rule is stated *inside the payload itself* as a machine-readable assumption.

### What the payload already gets right (keep all of it)

Assumptions block with codes and stated formulas; honest unknown-weight handling (`known_weight_kg` + `has_unknown_weight` instead of fake zeros); bend categories matching fitting-catalogue conventions (≤45° / 46–90° / >90°, with a 5° noise floor); horizontal-vs-riser length split; UUID traceability on every row (runs, segments, bends, risers); family|size|service grouping; deterministic ordering.

### S-1 — Add standard-length piece counts and offcut estimate (must, before UI)

Procurement thinks in **pieces**, not meters — and this was in the original RFC Phase A BOQ list ("offcut summary"). `RacewayFamily.standard_length_mm` already exists (3000). Add per run: `standard_length_mm`, `piece_count_estimate = ceil(length_m / standard_length_m)`, `offcut_m_estimate`; aggregate in groups/totals; one assumptions line ("piece estimate ignores fitting deductions and cut planning"). This is the single most contractor-useful number currently missing.

### S-2 — Add a generation envelope to the schedule payload (must, before CSV)

The view wrapper carries the layer, but the schedule dict itself — which is what a CSV/export will be built from — has no `generated_at`, `project_id`, or `layer` context. An exported schedule that can't say *when* and *from which design state* it was generated fails the evidence standard everything else here meets. Add `generated_at` (ISO), `project_id`, `layer_id`/`layer_name` at the top of the schedule payload.

### S-3 — Embed a graph-quality summary (should, before UI)

A BOQ over a broken network misleads quietly. Embed counts only: `graph_warnings: {near_miss_endpoint: n, unconnected_crossing: n, zero_length_segment: n, total: n}` so every rendering/export can show "n network warnings — verify connections before trusting quantities." Counts, not full warning bodies — the graph endpoint remains the detail source.

### S-4 — Name the tee/junction omission (one assumptions line now, derivation later)

`fitting_placeholders` counts plan bends and risers, but junctions exist since Stage 8A and a CSV reader will assume tee count = 0 rather than "not counted." Add an assumptions line ("junction/tee placeholder counts deferred") now; derive real counts from graph branch/junction nodes when the schedule consumes the graph projection (natural to pair with S-3).

### On the proposed next pass — agreed, with two notes

Compact viewer schedule panel + CSV download, JSON as the single source: right call. Two notes: (1) generate the **CSV server-side** from the same payload (one canonical formatter; panel and file can never diverge); (2) render the assumptions block **prominently** in both panel and CSV header rows — our explicit-placeholder doctrine only works if the user actually sees it.

### Reminders as of §21

- `eht_office.code-workspace` — still tracked.
- **F-19** — quiet, 22+ clean runs.
- **KR** — catalogue-seed confirmation (§14): still open, and worth closing before the first schedule CSV goes to an outsider, since the seed data now appears in deliverable-shaped output.

## 22. Schedule CSV + viewer summary review (2026-07-12, commit `d561d08`; for Codex)

Codex asked: are the CSV sections and compact viewer summary sufficient before Stage 10 begins?

**Verdict: sufficient — proceed to Stage 10. S-1 through S-4 are all properly closed; one small CSV completeness item (S-5) can ride the Stage 10 pass rather than block it.** Independently verified: raceway+plant3d **111 tests OK twice**, browser **2/2 OK**, full **eht 360 OK**, statics clean.

### S-1..S-4 closures verified

- **S-1 CLOSED:** `piece_count_estimate` + `offcut_m_estimate` per run, per group, and in totals, with the fitting-deduction assumption line — in JSON, CSV, and the viewer summary line ("N piece(s) | N m offcut").
- **S-2 CLOSED, exceeds ask:** generation envelope carries `generated_at`, `project_id`, layer id/name/**status/revision**, and source/package ids — more design-state context than requested.
- **S-3 CLOSED the better way:** the schedule builder consumes the graph projection directly and embeds per-code warning counts; the viewer summary shows "N graph warning(s) affect this schedule" and the CSV header carries the warning total.
- **S-4 CLOSED:** `raceway.schedule.junction_placeholder_deferred` assumption states the tee/cross omission and points to the graph endpoint for branch-node visibility.
- Both §21 implementation notes honored: **CSV is server-side** (one canonical formatter; panel and file cannot diverge) and **assumptions are printed prominently** (second section of the CSV, before any quantity).

### S-5 — CSV completeness rounding-out (severity: low, fold into Stage 10 or any small pass)

Three small things the JSON has but the CSV doesn't yet print: (1) a **Fitting Placeholders section** (bend counts by angle category ≤45°/46–90°/>90°, riser up/down) — procurement will want the categories, not just per-run totals; (2) a **Totals row/section**; (3) **per-code graph-warning rows** in the header block (near-miss / unconnected-crossing / zero-length), since a printed sheet saying "3 warnings" without *kind* invites the wrong assumption. All three are additive rows from data already in the payload.

### On Stage 10 as the next track — agreed, with one strategic attachment

Warning-layer work is the natural next pass, and the vocabulary problem is already solved: the graph warnings' shape (code/severity/message/refs/values) should simply become the standard for all Stage 10 validation warnings — don't invent a second format. Codex's instinct to put warning evidence into schedule/export is exactly our evidence doctrine.

**The strategic attachment: Stage 10 is the moment to implement Tier-0 telemetry (§20-f).** Warning interactions are the first real suggestion-response loop — a user sees a near-miss warning and connects the endpoint (accepted) or ignores it (rejected). That is precisely the `suggestion_event` shape the AI strategy needs, arriving naturally. One small table + a couple of logging calls inside the Stage 10 pass starts the data flywheel with zero extra ceremony. If Codex takes only one §22 suggestion, take this one.

### Reminders as of §22

- `eht_office.code-workspace` — rode into its fourth commit (`d561d08`); still one `git rm --cached` away.
- `d561d08` again bundles ~5 tracker entries under one title (F-20) — granularity reminder only, message content was at least accurate this time.
- **F-19** — quiet, 24+ clean runs.
- **KR** — catalogue-seed confirmation: now genuinely urgent-adjacent, since seed data appears in exportable deliverables (§21 note stands).

## 23. Stage 10 warning-layer review (2026-07-12, working tree; for Codex)

**Verdict: Stage 10 foundation is right, S-5 is closed, and the screen-scale flag is a clean platform pattern. Two small code-hygiene findings (N-11, N-12); the telemetry design note Codex named as next is now written and ready — see below.** Independently verified: raceway+plant3d **113 tests OK twice**, browser **2/2 OK**, full **eht 360 OK**, statics clean.

### Verified

- **One warning vocabulary, as asked (§22):** `raceway/warnings.py` *normalizes* graph warnings into the canonical shape instead of inventing a second format; all planned Stage 10 warnings present (too-few-nodes, short-segment, excessive-bends, inactive family/size, unknown service, unknown coordinate context, support-basis notice as `info`); thresholds are named constants; ordering deterministic; per-code/per-severity summary; warnings embedded in the schedule payload with `graph_warnings` kept for compatibility.
- **S-5 CLOSED:** CSV now prints per-code graph-warning counts, warning summary + detail rows, a totals section, and fitting-placeholder category rows.
- **Screen-scaled handles done the platform way:** opt-in `screenScaledObjects` layer flag; only opted-in groups are traversed in the animation loop (no per-frame cost for non-consumers); measurement graphics migrated onto the same helper — one implementation, not two. EHT drafts can adopt the flag later for free.
- **KR's refinements recorded** in the backlog with sensible sequencing: reducer between unequal widths, face-offset editing for riser/bend fitting alignment (faces must align, not just centerlines — a genuinely important constructability point), parametric fitting geometry after placeholder counts stabilize, crosses deferred.

### N-11 — Geometry helpers now exist in triplicate (severity: low, consolidate soon)

`_plan_bend_angle_deg`, `_distance`, `_point_from_node` are copied in `graph.py`, `schedule.py`, and `warnings.py` (constants are shared via import — good — but the functions are pasted). Three copies of bend math means a future change can silently diverge and, e.g., the schedule could count a bend the warning layer doesn't. Consolidate into one home (`graph.py` exports, or a small `raceway/geometry.py`) in any nearby pass.

### N-12 — Severity ordering is alphabetical (severity: cosmetic)

The warning sort uses the severity *string*, so `error < info < warning` — `info` rows print above `warning` rows in lists/CSV. Use an explicit rank map (`error=0, warning=1, info=2`). One line.

### Telemetry design note delivered (the named next architecture item)

Written as parallel work: `plant3d/records/planning/suggestion-telemetry-design-2026-07-12.md` — one `SuggestionEvent` model (UUID lifecycle key, loose `project_id`, `owner_module`, suggestion code, action enum incl. `unresolved_at_save`, context = the existing warning payload verbatim), a batch ingestion endpoint with the established auth/rate-limit patterns, an event taxonomy v0 that maps entirely onto features that already exist (near-miss/crossing warnings, ortho keep/undo), log-transitions-not-renders rule, observation-only guarantee with tests, and an explicit not-in-scope list. Recommended home: a minimal peer `telemetry` app (one model, imports nothing domain-side) — fallback of raceway-owned-first is acceptable, Codex's call, record either way. Sized at roughly one catalogue-endpoint-scale pass.

### Reminders as of §23

- `eht_office.code-workspace` — still tracked (fifth commit approaching).
- **F-19** — quiet, 26+ clean runs.
- **KR** — catalogue-seed confirmation: unchanged, still the lone open decision.

## 24. Three-face proxy review + next-pass recommendation (2026-07-12, working tree; for Codex)

**Verdict: the solid proxy is implemented exactly per the §20(a) guidance — approved. On the next-pass question: telemetry foundation first, then clash.** Independently verified: raceway+plant3d **113 tests OK twice**, browser **2/2 OK**, full **eht 360 OK**, statics clean.

### Verified in the proxy implementation

- **One merged mesh per run**, as advised: a single `BufferGeometry` accumulates all segments' bottom + two side quads (two triangles each), one `Mesh`, one shared material → one draw call per run. Draw-call guidance honored precisely.
- Bottom face sits at the authored elevation with sides extending up by catalogue depth — consistent with the established tray-bottom convention; envelope dimensions still come from catalogue mm (F-14 intact).
- Partial-vertex rollback (`positions.length = before`) keeps a failed transform from emitting degenerate triangles; `faceCount` recorded in userData; proxy remains derived and non-persistent; line rails/rungs retained as legibility overlays on top.
- One shared low-opacity `DoubleSide` material per run (0.14 / 0.24 selected) with `renderOrder` set — a single transparent object per run, not per plane.
- Known cosmetic limitation, fine to leave: adjacent segments' side faces meet without miter joins at bends (slight overlap/gap). Invisible at this opacity; real miter geometry belongs to the future fitting-geometry pass, not here.

### Next pass: telemetry foundation, then clash — reasoning

1. **The design note is ready** (`suggestion-telemetry-design-2026-07-12.md`) and sized at one small pass; clash/envelope warnings are a materially bigger one.
2. **The first event sources are already live** — every week the Stage 10 warnings run un-instrumented is labeled training data lost forever. The flywheel argument only works if the intake valve is installed while suggestions are flowing.
3. **Clash warnings should be born instrumented.** If telemetry lands first, the clash pass's new warnings (shown → resolved/ignored) emit events from their first day at zero marginal cost; land clash first and we retrofit instead.
4. Convenient side-fact: the three-face proxy just made the clash pass easier anyway — the run envelope now exists as actual render geometry, so rough AABB extraction is nearly free when clash's turn comes.

### Reminders as of §24

- `eht_office.code-workspace` — unchanged, still tracked.
- **F-19** — quiet, 28+ clean runs.
- **N-11/N-12** (helper triplication, severity ordering) — open from §23, fold into any nearby pass.
- **KR** — catalogue-seed confirmation: still the lone open decision.

## 25. Surface/wire toggle + riser visual polish review (2026-07-12, working tree; for Codex)

**Verdict: clean visual pass; merged-mesh rule verified intact; nothing blocks the agreed next order (telemetry → clash).** Independently verified: raceway+plant3d **113 tests OK twice**, browser **2/2 OK**, full **eht 360 OK**, statics clean.

Verified in code:

- **One-mesh-per-run preserved:** bottom/side shading is done with **per-vertex colors** (`vertexColors: true`) inside the same single geometry/material — differentiation without a second draw call. Exactly the right technique.
- `segmentCornerPoints` now centralizes the corner math for faces (and the line overlays ride the same helper) — a small de-duplication in the right direction; the Python-side N-11 triplication still stands as the open item.
- Surface On / Wire Only toggle (`Shift+V`) removes only the shaded face mesh; rails, rungs, handles, placeholders, graph/schedule data, and save behavior untouched — a pure view-mode switch, correctly scoped.
- Riser polish: the segment frame now follows the 3D segment so vertical runs get real side faces instead of collapsing into one laminar plane.

One cosmetic note for a future fitting-geometry pass, not a finding: a **pure-vertical** riser has no intrinsic plan direction, so its width orientation falls back to a default axis. The nicer behavior — inherit orientation from the adjacent horizontal segment — belongs with the real fitting/miter geometry work, not now.

Codex's note re-confirms the §24 order (telemetry foundation first, clash born instrumented) — alignment recorded; the design note is waiting.

### Reminders as of §25

Unchanged from §24: `.code-workspace` still tracked; F-19 quiet (30+ runs); N-11/N-12 open; KR catalogue-seed confirmation open.

## 26. Telemetry foundation review (2026-07-13, working tree; for Codex)

**Verdict: the data flywheel's intake valve is installed, and installed well — this pass meets every acceptance criterion in the design note and exceeds it in one important place.** Independently verified: raceway+plant3d+telemetry **117 tests OK twice** (4 telemetry tests), browser **2/2 OK**, full **eht 360 OK**, `telemetry/0001` applied to live PostgreSQL, statics clean.

### Verified against the design note

- **Peer app, as recommended:** `telemetry` imports nothing domain-side (verified — only `plant3d.project_gateway`, the allowed direction); one model, one endpoint; raceway talks to it over HTTP like any future consumer will.
- **Schema matches the note exactly:** UUID lifecycle `key`, loose `project_id`, `owner_module`, `suggestion_code`, the full action enum including `unresolved_at_save`, context/action_detail JSON, `client` version tag, the three planned indexes.
- **Exceeds the ask — the no-domain-PK rule is *enforced*, not trusted:** `_strip_domain_ids` recursively removes forbidden PK keys (`run_id`, `node_id`, `layer_id`, …) from every context/action_detail at ingestion. Clients cannot pollute the training data with non-durable identity even by mistake. This is the single best decision in the pass.
- **Ingestion hygiene:** per-event project access via the gateway; action whitelist; batch capped at 50; configurable rate limit (`TELEMETRY_EVENTS_RATE_LIMIT`, default 120/m) with explicit 429; `bulk_create`.
- **Both v0 event sources live:** warning lifecycle (session-signature dedup = log-transitions-not-renders honored; stable lifecycle keys group `shown` → resolution) and ortho axis-lock (context carries previous/raw/adjusted points — the edit-delta-grade signal).
- **Observation-only holds structurally:** queued, batched, timer-flushed with `keepalive` for unload; failure path is a `console.warn` and nothing else. One half-line polish item, not a finding: an explicit browser-test assertion that a *blocked* telemetry endpoint leaves draw/save fully working would complete the design note's acceptance list verbatim — fine to ride along with any later pass.

### Standing note

From this pass onward, engineering decisions made in the raceway tool are being recorded with context. Tier 2 (learned ranking) now has a growing corpus from day one of Phase H — which was the entire point of sequencing telemetry before clash.

### Next pass — confirmed

Clash/envelope warnings born instrumented, with N-11 (helper consolidation) and N-12 (severity rank ordering) riding along — agreed on all three. The clash warnings should emit the same lifecycle events through the same client helper; zero new telemetry design needed.

### Reminders as of §26

- `.code-workspace` — still tracked.
- **F-19** — quiet, 32+ clean runs.
- **KR** — catalogue-seed confirmation: still the lone open decision checkbox.

## 27. Coarse AABB clash review (2026-07-13, working tree; for Codex)

Codex asked three specific things: the 0.10 m clearance band, the 2000-object scan cap, and whether `RenderTile.bounds` should be the first spatial partition. **Verdicts: sound default / acceptable because disclosed / yes — endorsed.** One boundary finding (N-13). Independently verified: raceway+plant3d+telemetry **122 tests OK twice**, browser **2/2 OK**, full **eht 360 OK**, statics clean.

### The three assumptions

1. **0.10 m clearance band — keep it.** Correct understanding of what it is: a box-gap proximity band on top of an axis-aligned envelope, not a true clearance check — diagonal runs over-approximate, which is exactly what a warnings-only broad phase should do (err toward showing). Two notes: it's advice-category per §20(c), so it graduates to a project-level setting whenever convenient, never per-user; and when real clearance rules arrive (maintenance access above tray is typically 200–300 mm in EPC practice), those are *narrow-phase, rule-based* checks — don't stretch this band to fake them.
2. **2000-object scan cap — acceptable, specifically because truncation is disclosed.** Verified: the limit+1 fetch detects overflow and emits `model_clash_scan_limited` so the user knows coverage is partial. The completeness doctrine held without prompting — this is the pattern that separates trustworthy warnings from dangerous ones. With the tile partition (below), the cap should rarely trigger; keep it as the final safety valve.
3. **`RenderTile.bounds` as first spatial partition — yes, endorsed as the next scalable step, before any BVH.** Tiles are a spatial decomposition the pipeline already builds; the query becomes: intersect the layer's overall envelope with tile bounds → candidate objects via the existing `render_tile` FK → per-object AABB tests. No new infrastructure, uses STABLE contract data, and correctly postpones BVH until envelope *precision* (not candidate count) is the limiting factor. Implement it inside the N-13 helper below, so the partition is a platform service from birth.

### Also verified

- **N-11 CLOSED:** `raceway/geometry.py` consolidates the shared math (graph −97 lines, schedule −39; the module is pure — imports `math` only). **N-12 CLOSED:** explicit `SEVERITY_ORDER` rank map.
- **Clash born instrumented** as agreed — the new warnings ride the existing pipeline into telemetry with zero new design.
- Good judgment not asked for: `MODEL_CLASH_WARNING_LIMIT = 25` flood cap with deterministic worst-first ordering (penetration before proximity, then by gap) — a bad route can't bury the panel in 2,000 rows.

### N-13 — First direct ORM import of `plant3d.models` from a consumer (severity: medium, fix before the pattern spreads)

`raceway/warnings.py:5` does `from plant3d.models import ModelObject` and queries the table directly. The boundary contract is explicit: consumers reference by ID, *"never by importing `plant3d` models, joining its tables."* Every other integration point goes through a named seam (`project_gateway`, `plant3d.access`, `plant3d.overlay`). Fix is small and makes the tile partition better too: a plant3d-side helper — e.g. `plant3d.overlay.model_object_bounds_for_source(source_model_id, render_package_id=None, bounds_filter=None, limit=...)` returning plain dicts plus a truncation flag — moves the ORM behind the seam (function call today, API call at Stage 1, zero raceway change either time) and is the natural home for the tile-bounds prefilter. Not urgent while co-located; genuinely important before lighting copies the shortcut.

### On Codex's next-pass list

Warning UX polish and the shortcut reliability audit: proceed freely — small, revertible, UI-layer. **The accessory architecture pass is different in kind:** reducers, face-offset editing, and parametric fitting geometry touch catalogue schema and authoring semantics — the migration-pain category. That one should start as a short design note (fitting rules, face-alignment semantics, what persists vs derives) reviewed before coding, the same discipline that made Stage 8A land clean. Sequence suggestion: warning UX → shortcuts → N-13 + tile partition (one small platform pass) → accessory design note → accessory coding.

### Reminders as of §27

- `.code-workspace` — still tracked.
- **F-19** — quiet, 34+ clean runs.
- **T-1 event dictionary** — starts mattering with the next new `suggestion_code` (the clash codes qualify; add their context shapes to the telemetry note).
- **KR** — catalogue-seed confirmation: still open.

## 28. Seam-fix + warning-UX + shortcut batch review, with full register sweep (2026-07-13; for Codex)

**Verdict: no digression anywhere — every sub-pass traces to the agreed lists — and two closures are exemplary. But this batch ships one real test failure (N-14) that must be fixed before commit, and it exposes a verification-scope gap worth one checklist line.** Verified: browser **2/2 OK**, full **eht 360 OK**, statics clean — but raceway+plant3d+telemetry **FAILED (1)** deterministically.

### N-14 — Stale cache-key assertion; fix before commit (severity: medium only because it blocks a green baseline)

`plant3d/tests.py:2081` asserts `raceway_overlay.js?v=20260712_raceway22`; the shortcut sub-pass bumped settings to `raceway23`. The deeper cause: **that sub-pass's verification list ran raceway suites only — never plant3d, where the assertion lives.** Two fixes, both cheap: (1) make the test read the expected version from `settings.PLANT3D_VIEWER_EXTENSIONS` instead of hardcoding the string — then cache-key bumps can *never* break it again; (2) checklist rule: the **last** sub-pass of any batch runs the full battery, whatever the sub-pass touched. (Side observation while chasing this: test counts varied between consecutive runs, 124 vs 127 — possibly conditional discovery; this may be F-19's mechanism. Worth one look while in the file.)

### Exemplary closures verified

- **N-13 CLOSED beyond the ask:** bounds lookup moved to `plant3d.overlay.model_object_bounds_for_source()`; raceway consumes plain dicts; **a new guard test now scans raceway for direct `plant3d.models` imports** — the breach class is structurally prevented, not just fixed; **and the `RenderTile.bounds` prefilter (§27's endorsed next step) was implemented in the same pass, with a test proving tiles prefilter candidates.** Bounds normalization handles three historical formats defensively.
- **T-1 honored on schedule:** event-dictionary entries added to the telemetry note for all three clash codes with full context shapes.
- Warning UX: schedule warning rows click-to-select the affected run/node with segment highlight; layer-level warnings stay plain. Shortcut gating reworked with browser coverage reproducing KR's exact manual failure shape (canvas focus + `B`, `Ctrl+S`). Source-detail progress strip under the primary action. KR's threshold-config and warning-lifecycle (ack/dismiss with evidence-preserving CSV) notes both recorded in the backlog — correctly deferred, correctly worded.

### Register sweep — old and very-old items

| Item | Age | Status |
| --- | --- | --- |
| `.code-workspace` in records/audit | §13-era (oldest open item) | **Still tracked.** Once more, with feeling: `git rm --cached plant3d/records/audit/eht_office.code-workspace` + one `.gitignore` line. Fold into the N-14 fix commit. |
| KR catalogue-seed confirmation | §14-era | **Still open** — the only KR-side item; seed data ships in CSVs now. |
| F-19 flake | §13-era | Quiet, but today's run-count variance (124/127) is the first new clue; check discovery while fixing N-14. |
| F-20 commit granularity | §17 | Watch at next commit — this batch is 3 tracker entries; ideal would be 3 commits. |
| §26 blocked-endpoint browser assertion | §26 | Open, tiny, non-urgent. |
| T-2 `session_key` column | §T-register | Open; next telemetry-touching pass. |
| M-5 parallel offset, M-6 plan view | RFC | Open. Note: the viewer already has Top/Front/Side quick buttons — M-6 is *half done*; remaining = working-plane grid at active EL while drawing. |
| Accessory design note before accessory code | §27 | Correctly held — not started in this batch. Next architecture item. |
| 0007 `ai_gateway` | RFC | Awaiting first Tier-1 feature. |

### Low-hanging UI/UX gains (KR asked; all few-line items, in value order)

1. **Warning → camera fly-to.** Click-to-select just shipped; add the existing `focus` behavior so the camera flies to the highlighted segment. In a dense plant this is the difference between "warning noted" and "warning found."
2. **Warning-count badge on the Raceway section summary** (visible even collapsed) — the cheapest seed of the ambient-compliance-dashboard idea from the vision RFC.
3. **Service-class color legend chips** in the palette — users forget which color is instrument vs control; four colored spans.
4. **Inline run-tag rename in the inspector** — `RWY-001` is a placeholder; engineers will want their own tags, and the API already accepts `tag` on PATCH.
5. **`?` shortcut cheat-sheet overlay** — the shortcut set just got audited; make it discoverable.

### Reminders as of §28

N-14 fix + workspace-file removal in the same commit; F-19 clue to check; KR seed confirmation; accessory design note is the next architecture deliverable (I can draft the skeleton on request).

## 29. Fitting projection review + next-pass position (2026-07-13; for Codex)

Codex asked: does the pane-level fitting summary expose the right early engineering signals — especially `reducer_candidate` and `requires_face_alignment` — before any fitting/accessory records are persisted?

**Verdict: yes — both signals are right, the taxonomy is better than asked for, and the keep-persistence-deferred position is exactly correct. Three signal additions recommended before persistence (below), none blocking the next pass.** Independently verified: **N-14 CLOSED** the robust way (the test reads script/version from `settings.PLANT3D_VIEWER_EXTENSIONS` — bumps can never break it again); raceway+plant3d+telemetry **127 tests OK three times** (count variance from §28 did not recur), browser **2/2 OK**, full **eht 360 OK**, statics clean.

### Why the two signals are right

- **`reducer_candidate` with a transition taxonomy** (width / depth / width+depth / family / service) is engineering-correct and more useful than a count: a *width* reducer is a stocked catalogue fitting; a *depth* transition usually is not (step plate or bottom-aligned open joint); a *family* transition (ladder→perforated) needs an adapter plate; and a *service* transition is usually not a fitting at all but a design smell. Deriving these from graph nodes with unequal size-groups is exactly where the information lives.
- **`requires_face_alignment` assignments are correct:** False for same-size plan bends (faces align automatically), True for risers (orientation/handedness pending) and reducers (handedness must align faces, not centerlines — KR's original observation, now encoded). The `face_alignment.status: "required_not_modelled"` pattern is the honesty doctrine applied to geometry: the pending design decision is *surfaced*, not silently mis-modeled. Keep this pattern for every future deferred-geometry case.
- Projection-only, versioned (`raceway.fittings.v0`), enveloped, assumption-stamped, UUID-traceable — all disciplines intact.

### Three signal additions before persistence (cheap, high engineering value)

1. **N-15 — Non-standard bend angle flag.** Catalogues stock 30/45/60/90° bends; a 37° plan bend is special-fabrication or a route that should be squared up *now*, while editing costs nothing. Add `nearest_standard_angle_deg`, `deviation_deg`, and a `non_standard_angle` flag (suggest ±2.5° tolerance, named constant) to plan-bend items, plus a count. This is the single most actionable early signal a tray designer can get.
2. **N-16 — Promote `service_transition` to a warning too.** Two service classes sharing a junction node (power tray joined to instrument tray) is usually a modeling error or a segregation problem, not a fitting need. Keep it in the fitting taxonomy, but also emit `raceway.warning.service_mismatch_at_junction` through the canonical warning pipeline — it deserves panel/CSV/telemetry visibility, not just a count in the fittings pane.
3. **Branch-width sanity at branch nodes** (branch wider than main run) — can wait for tee materialization; recording it here so it rides the tee pass, not as a now-item.

### On the next-pass plan — endorsed, with the standing condition

1. **Face/orientation control foundation: agreed it is next and architecture-sensitive — which is precisely why it starts as a design note, not code** (the §27/§28 held item, now correctly scoped tighter). The note must decide: orientation representation (per-run vs per-segment; reference-face enum bottom/top/left/right + offset vs rotation-about-centerline for wall-mounted trays); what persists (authoring intent) vs what derives (face geometry); default + inheritance rules when a run changes size; effect on the proxy envelope and clash bounds; reducer handedness (left/right/center) and riser inside/outside handedness; migration shape (additive nullable columns). I will co-draft or review the note — one page is enough, same as Stage 8A.
2. **Warning fly-to / isolate: endorsed** — it was §28's top low-hanging item.
3. **Fitting persistence stays deferred: endorsed without reservation.** Persisting placeholder rows now would freeze v0 semantics mid-design; the projection *is* the correct storage until face/orientation semantics are settled. Route-as-truth, parts-as-derived — the founding rule, still paying rent.

### Reminders as of §29

- `.code-workspace`: the tracker now words this as "decide whether to untrack" — **KR, this is now explicitly your one-word call** (my vote remains: untrack + gitignore).
- KR catalogue-seed confirmation — still open, still the only other KR-side item.
- T-2 `session_key`, §26 blocked-endpoint assertion, M-5/M-6 remainder — open, non-urgent, correctly parked in Codex's deferred-stock list.
- F-19 — count variance did not recur across three runs today; back to quiet watch.

## 30. KR Q&A on shipped behavior + sequencing (2026-07-13) — positions recorded for Codex

- **(c) Anchor Node button:** keep the function, demote its prominence. Auto-anchor on surface clicks covers the common case, but the button remains the only *selection-based* path (anchor the selected node to a hierarchy-selected object without a canvas click) and the correction path when auto-anchor grabs the wrong face. Suggest relocating Anchor/Clear next to the node inspector rather than the main command strip.
- **(d) Mid-run node insertion (split segment to accept a branch):** yes — it is the already-recorded tee/split deferral coming due. It is the *prerequisite* for tee materialization; semantics were settled in Stage 8A (explicit acceptance, crossings ≠ connections). Schedule after (or parallel to) the face/orientation design note; modest complexity (project click onto segment, insert at parameter t, resequence — the node-replace API already supports full rewrite).
- **(e) Copy-run-with-offset (M-5):** one small pass, comparable to typed-segment entry. Deep-clone nodes + offset vector + new tag; the two design decisions are: drop anchors on copies (they'd lie) and drop junction connections (user reconnects) — both should warn. Good slot right after warning fly-to.
- **(f) Support steel + 2D fabrication drawings:** v2 wave, realistically after Phase H proves the MVP loop. Prerequisite chain: face/orientation semantics → full G-1 (surface normal) → load/span tables → SupportType parametric + fabrication template → drawings. Recommend installation-plan output (SVG/PDF plan views) before dimensioned fabrication GAs — earlier value, fraction of the cost. Support *count* placeholders already ship in BOQ, so schedules aren't blocked meanwhile.
- **(a) note for the face/orientation design note:** KR independently observed the vertical-tray orientation inconsistency (§25's known limitation) in manual use — confirmation that orientation inheritance for vertical segments belongs in the note's must-decide list. Also worth considering there: bend/riser markers are world-space glyphs today, so a diamond reads as a square from a 45° camera yaw — screen-space billboard markers would remove the ambiguity if users find it confusing.

## 31. Measure-snap defect postmortem + answers to Codex's snap/ordering questions (2026-07-13; for Codex)

*Process note for the record: at KR's request, my independent investigation of the edge-snap unreliability was deliberately withheld from this file until Codex had root-caused and fixed it unaided, and KR's manual test confirmed ±2 mm accuracy. Both investigations are now on record for calibration.*

### Postmortem — three stacked defects, independently found by both of us

My pre-fix diagnosis (held in chat): **D1** — the measurement snap raycast ran with Three.js's default `Line.threshold` of 1.0 world unit (a one-meter slop radius; the codebase already knew this trap — `pickDraftElement` tightens to 0.25), so clicks near one tray put many trays' edges in the candidate set; **D2** — Three.js orders line hits by camera distance, not cursor proximity, so the eye-nearest edge beat the aimed-at edge; **D3** — `nearestFaceVertex` needs a mesh `faceIndex`, which line hits never have, so no corner/vertex snapping ever ran and picks landed at arbitrary points along whichever rail won.

**Codex's fix, verified: all three closed, by an approach stronger than threshold-tuning** — raycasting is abandoned for layer snaps entirely; segment endpoints are projected to screen pixels, the closest 2D point-on-segment to the cursor wins, accepted within a named 9 px radius. D1 gone by removal; D2 fixed by construction (cursor proximity *is* the sort key); D3 addressed via precise on-edge interpolation (aim at a corner → t→0/1 → land on the corner within millimeters — hence KR's ±2 mm). The old raycast fallback no longer receives layer lines, so the bug cannot re-enter. Verified green: 127 tests ×2, browser 2/2. One residual nuance, not a defect: screen-space selection has no occlusion knowledge — an obscured rail projecting within 9 px can beat a visible one; add a depth tie-break only if users ever report it. One polish item for later: CAD-convention **endpoint-priority** snapping (corner beats mid-edge within tolerance).

### Answer 1 — is 9 px the right default? Yes

It sits in the CAD-convention band (AutoCAD's default aperture is 10 px; SketchUp/Revit similar) and matches real mouse pointing accuracy. Larger re-invites adjacent-edge confusion at rack density; smaller makes users miss and call it broken. Two forward notes: it's measured in CSS pixels so high-DPI is already handled; and when touch/tablet input matters (site construction module), scale by `event.pointerType` (~20 px for touch) rather than raising the mouse default. Keep it a named constant; it's advice-category per §20(c) if anyone ever wants it configurable.

### Answer 2 — explicit snap-point/segment metadata: yes, and Codex's timing condition is exactly right

Today the host reads `Line` geometry directly, which works because proxy edges *are* clean line segments coinciding with semantic edges. That coincidence dies with accessories: a tessellated bend's triangles are not snap edges — its semantic snap targets (tangent points, arc center, face corners) exist nowhere in the render geometry. So evolve the provider contract **before accessories become selectable** (Codex's own condition): `getMeasurementSnapGeometry()` returning kind-tagged primitives — `points: [{position, kind: corner|node|center}]`, `segments: [{start, end, kind: edge|centerline}]` — with the host running the same screen-space selection over them. Kind tags buy two things for free: CAD-style snap priority (corner > node > edge > centerline — the D3 polish lands naturally) and meaningful measurement readouts later ("corner of RWY-001 → beam flange"). Record it as a reserved contract addition alongside G-1/G-2; implement it with the accessory-materialization pass, not before.

### Answer 3 — next-pass order: agreed, with the standing one-page condition

Orientation presets → preserve node UUID keys before segment-level overrides → reducer/face-offset with one-edge default is the right order, and I would *not* swap in backlog convenience items ahead of it — this is the architecture-critical path, and it directly answers KR's observed vertical-tray-facing inconsistency. Three riders:

1. **The §29 design-note condition stands, scoped small:** before the persistence part of orientation presets, one page recording: orientation representation (per-run enum first; per-segment override shape reserved), persist-vs-derive split, inheritance when size/family changes, effect on proxy envelope and clash bounds, and — new question surfaced by the node-UUID rider — **when a segment is split by future mid-run insertion, which side inherits a segment-level override?** Draft-local-first with save through the normal flow (Codex's plan) is the right implementation shape; the note is half-written by Codex's own three plan lines.
2. **One-edge matching as the reducer default is the correct engineering choice** — in plant practice the common edge stays straight (continuous along the rack/wall side) and the taper takes the other side; center reducers are rarer on site. The note must fix the edge-naming convention (left/right relative to node-order direction — stable, since node order is truth) and the default side, with explicit override.
3. Slotting suggestions, not reordering: N-15/N-16 (bend-angle flag, service-mismatch warning) ride whichever pass next touches fittings/warnings; M-5 copy-offset and mid-run node insertion queue immediately after the orientation foundation — insertion is the tee prerequisite.

## 32. Run-level orientation slice review (2026-07-13; for Codex)

Codex asked: is the run-level metadata schema acceptable as the first persistence slice? **Yes — approved, and the slice is a model of how to ship a schema-sensitive feature: design note first (the §29/§31 condition, honored), draft-local with undo, saved only through the normal flow, and server-side canonicalization with a version tag.** One integration gap found (N-17), and strong confirmation that Codex's next-pass item #1 is a correctness prerequisite, with evidence below. Verified: raceway+plant3d+telemetry **128 tests OK twice**, browser **2/2 OK**, full **eht 360 OK**, statics clean.

### Why the persistence shape is right

`RacewayRun.metadata["orientation"]` with a **whitelisted preset**, canonicalized server-side to `{schema: "raceway.orientation.v0", preset, quarter_turns, label}` — no migration, garbage rejected with a field-level error, and the embedded schema tag means a future graduation to a real column (if orientation ever becomes a query dimension) is a clean data migration rather than archaeology. JSON-with-version-tag is exactly the right home while orientation is constructability intent rather than something we filter runs by. Four orthogonal presets (`Open Up/Down`, `Roll Left/Right`) as quarter-turns about the centerline is the correct v0 vocabulary — free-angle rotation has no catalogue meaning.

### N-17 — Clash envelope ignores orientation (severity: medium, next-pass rider)

`warnings.py`'s `_segment_envelope_bounds` still assumes width-horizontal/depth-up; `grep orientation` across `warnings.py`/`schedule.py`/`graph.py` returns nothing. A 600×100 run rolled 90° now has its AABB wrong by ~250 mm laterally and its depth extent pointing the wrong way — so rotated runs get silently wrong clash/clearance warnings, the exact class of quiet inaccuracy our doctrine forbids. Schedule/BOQ are unaffected (lengths/weights are rotation-invariant), so this is the single integration point. Fix is small: apply `quarter_turns` to the cross-section offsets in the server envelope. Until then, one assumptions line ("clash envelopes assume default orientation") would keep the honesty rule intact. Should ride the very next pass.

### Node-key preservation — confirmed as a correctness prerequisite, not just ordering

Verified in code: `run_nodes_view` PUT does `run.nodes.all().delete()` + `bulk_create` — **every save regenerates every node UUID.** So the F-06 durable-identity promise currently holds within a draft session but *not across saves*. Today's blast radius is tolerable (telemetry contexts and warning-lifecycle signatures go stale per save; junctions survive because they're coincidence-based) — but segment-level orientation overrides keyed by node pairs would be **silently orphaned on every save**. Codex's instinct to block segment overrides behind this fix is exactly right. Suggested mechanism: the client already holds each node's `key` — echo it in the PUT payload; server matches by key (update existing, create new, delete missing) inside the same transaction. Additive, no migration; add a regression test asserting keys survive a save→edit→save cycle.

### Next-pass order — agreed as stated

Node-key preservation → segment-level orientation/face-offset groundwork → reducer handedness with one-edge matching. No reordering suggested; N-17 rides pass one.

## 33. Node-key preservation review (2026-07-13; for Codex)

Codex asked: is delete/recreate-with-preserved-keys enough for segment-level intent? **Yes — approved, and the ownership rule is stricter than I suggested, in the right direction.** One slipped rider (N-17) must not slip twice. Verified: raceway+plant3d+telemetry **130 tests OK twice** (including the two new key tests: preservation across saves, and foreign-key rejection *without destroying existing nodes*), browser **2/2 OK**, full **eht 360 OK**, statics clean.

### Why the approach is sound

- **Ownership check beats regeneration:** an echoed key must already belong to this run; a foreign or invented UUID fails with a clean field error instead of being silently re-minted. An unknown key in a payload signals a client bug or a hijack attempt — failing loudly is the correct policy, and the test proves failure is non-destructive.
- **Both payload-level uniqueness checks exist** (sequences *and* keys), so the duplicate-key path yields a 400, never an IntegrityError 500. `full_clean(exclude=["key"])` is correctly sequenced — validation runs while old rows still exist; the DB unique constraint still guards the insert inside the transaction.
- **Lifecycle is right:** echoed key → identity survives; omitted key → new node, new UUID; not echoed → node (and its identity) gone. Delete/recreate as rows with durable UUID identity on top is exactly the "PKs are never promised, UUIDs are" contract — row PK churn per save remains, and remains fine, because nothing durable may reference PKs (telemetry already strips them).
- **Sufficient for segment intent:** an ordered `(start_key, end_key)` pair now survives save→edit→save. The substrate is ready.

### N-17 slipped — must ride the segment-groundwork pass, stated plainly

The clash envelope still ignores orientation (`grep orientation raceway/warnings.py` → nothing). It was flagged in §32 to ride this pass and didn't. It is arguably *more* natural in the segment-orientation pass (same envelope code), but that's the last pass it can ride before rotated runs accumulate in real drafts with silently wrong clash warnings. If it can't ride, add the one-line assumptions disclosure now.

### Answer to "how does segment intent follow node split/insertion" — recommended semantics for the design note

1. **Key segment intent by the ordered node-key pair** `(start_key, end_key)` — now durable.
2. **Split (insert C between A–B): both children inherit the parent's intent.** Orientation/face-offset are continuous physical properties along the tray; cutting a piece doesn't change which way it faces. Inheritance is the only default that never surprises.
3. **Merge (delete C, A–C–B → A–B): keep the intent only if both parents agreed; if they differed, drop to run-level default and warn** — never silently pick a winner. This is the one case that must ask the user.
4. **Stale-intent hygiene at save:** server drops (or flags) intent entries whose node pairs are no longer adjacent, with a response note — the honesty rule applied to intent metadata.
5. **Storage:** same pattern as the orientation slice — versioned entry in `run.metadata` (`raceway.segment_orientation.v0`, list keyed by node pairs), no new table until fitting persistence forces one.

With those five rules in the design note, the recommended order stands: segment groundwork (+N-17) → reducer handedness with one-edge matching.

## 34. Segment groundwork + manual-feedback pass review (2026-07-14; for Codex)

Two layers reviewed: commit `3e8238c` (segment identity + oriented clash) and the working-tree manual-feedback fixes. **Verdict: both clean; N-17 closed on schedule; one process observation about the measurement regression.** Verified: raceway+plant3d+telemetry **131 tests OK twice**, browser **2/2 OK**, full **eht 360 OK**, statics clean.

### Commit `3e8238c` — verified

- **N-17 CLOSED, did not slip twice:** the rough clash AABB now derives from oriented proxy corners (`_run_orientation_quarter_turns` → `_segment_proxy_corner_points`), with a regression test proving `Roll Right` changes the detected envelope. The §33 split/merge/stale-intent semantics were folded into the design note as asked.
- **Segment identity groundwork is correctly scoped:** derived rows keyed `start_node_key::end_node_key` (stable, thanks to §33's substrate), draft identity until first save, selection UX in blue — and *no persistence*, exactly as agreed. Reducer handedness remains correctly queued behind segment intent.

### Manual-feedback pass — verified, with one process note

- **KR caught a real regression from the snap fix:** structure-only measurement broke (a layer-snap miss returned an error instead of falling back to the model). The fix restores a clean priority cascade — raceway edges (9 px screen-space) → selected objects → **visible model geometry with face-vertex snap** → clear message. Correct ordering. Process note: this is the second consequence-bug from the same snap pass; the lesson is a test-matrix line, not a person — **any change to a selection/snap path must include the "no raceway present, model-only" case**. A browser assertion for model-only measurement with snap on would lock this regression class shut; small, worth adding.
- **Continue-from-selected-endpoint with prepend support** is correctly anchored: first endpoint prepends, last appends, mid-run declines (consistent with deferred tee/split). Prepending shifts every sequence number — which is now safe *because* node keys survive saves; the §33 substrate is already paying rent one pass later.
- Two deferred observations are well-worded in the tracker: nearest-segment-interior picking (so shared endpoint handles don't block middle-segment selection) and the explicit work-plane mode message (supports must never feel like a drawing prerequisite — KR's product point, correctly captured).
- Polish verified: Shift+M model-layer toggle, differentiated lower-edge colour, source-detail progress dedup.

Next: segment-level orientation/face-offset persistence per the design note's five rules, then reducer handedness with one-edge matching — order unchanged.

## 35. N-15/N-16 pass review (2026-07-14, commit `3538046`; for Codex)

**Verdict: both findings closed exactly to the §29 specifications — one small documentation gap (T-1) is the only observation.** Verified: raceway+plant3d+telemetry **134 tests OK twice** (three new tests), browser **2/2 OK**, full **eht 360 OK**, statics clean, tree clean.

### N-15/N-16 closures verified

- **N-15 CLOSED to spec:** `BEND_STANDARD_ANGLES_DEG = (30, 45, 60, 90)` with the suggested **2.5° tolerance as a named constant**; each plan bend now carries `nearest_standard_angle_deg`, `deviation_deg`, and the `non_standard_angle` flag; aggregate counts flow into the fitting summary and schedule CSV; and the assumptions block documents the check with exactly the right honesty framing — *"advisory flags until a vendor catalogue is selected."* A tray designer now learns to square up a 37° bend while editing is still free.
- **N-16 CLOSED to spec:** `raceway.warning.service_mismatch_at_junction` emits through the canonical warning shape whenever a connected graph node's members span two or more service classes — with node keys, source point, member evidence, and run keys/tags — so it reaches panel, CSV, *and* telemetry for free, while the `service_transition` entry stays in the fitting taxonomy as specified. Power-tray-joined-to-instrument-tray is now a visible, exportable, recorded event.
- Commit granularity note (F-20, positive for once): `3538046` bundles the manual-feedback fixes with N-15/N-16 — two tracker entries, one commit — but the message names the dominant content accurately.

### T-1 gap — one table row owed

`raceway.warning.service_mismatch_at_junction` is a **new suggestion_code flowing into telemetry**, and the event dictionary in `suggestion-telemetry-design-2026-07-12.md` has no entry for it (checked — absent). The T-1 rule exists precisely for codes like this one, whose context carries an unusual shape (multi-run members list). One row, next touch of the telemetry note.

### Register state after this pass

The findings register is effectively clean again: open items are T-2 (`session_key`), the §26 blocked-endpoint assertion, the two KR decisions (workspace file, catalogue seed), M-5/M-6 remainders, and the two well-recorded deferred observations (segment-interior picking, explicit work-plane mode). Architecture path unchanged: segment-level intent persistence → reducer handedness with one-edge matching.

## 36. Segment-intent persistence + hydration regression review (2026-07-15; for Codex)

Scope: commit `9748e57` (warning detail view, home navigation, upload retention fix, **segment-level orientation intent**) plus the working-tree UI-context polish and save-regression fix. **Verdict: the segment-intent foundation implements the §33 five-rule spec faithfully; the regression diagnosis is correct and the fix is sound — I traced its one subtle edge and it holds.** Verified: raceway+plant3d+telemetry **139 tests OK twice**, browser **2/2 OK**, full **eht 360 OK**, statics clean.

### Segment-level orientation intent — spec compliance verified

Keyed by adjacent node-UUID pairs (`start::end`); persisted as versioned `raceway.segment_orientation.v0` metadata (same canonicalized pattern as the run slice); server rejects unsupported presets and **prunes stale overrides when node replacement changes adjacency** — §33 rule 4, implemented server-side where it belongs; draft overrides re-keyed at first save. Split/merge inheritance (§33 rules 2–3) correctly remains the named next step. **T-1 CLOSED** — the `service_mismatch_at_junction` dictionary row now exists with the full member-list context shape. The warning-detail endpoint is access-controlled through `_layer_for_user`.

### The hydration regression — diagnosis confirmed, fix traced

Codex's root-cause is right: server metadata saved correctly; the browser reset its override cache to `{}` after save and treated emptiness as authoritative, and `runFromServer()` had the same risk on reload. The fix's architecture is coherent: **cache and local `run.metadata` are mutated together on every edit** (so they can't disagree), rebuild-from-metadata fires only when the cache is empty *and* metadata is non-empty, and override deletion sends an explicit payload from the current map. I specifically traced the resurrection edge — *delete the last override locally (empty cache) while saved metadata is still non-empty* — and it holds precisely because the edit handler updates local metadata in the same step. Browser smoke covers the three states (draft-before-save, post-save, reload).

**Pattern recommendation (for the file, not a finding):** this is the codebase's first cache-authority bug, and the durable idiom that prevents the class is *hydrate-from-response* — after any successful save, the client rebuilds its local state from the server's response snapshot rather than resetting or preserving caches by rule. The runs already do this (`applySavedRunPayload`); adopting it as the standard for every future consumer-side cache (face-offset is next) closes the class, not just the instance.

### Face-offset groundwork observed underway

Face-offset groundwork (`raceway.segment_face_offset.v0`, ±5 m clamp, 0.5 mm epsilon) is already visible in the working tree — the next architecture pass underway as stated. Not reviewed here; it gets its own review when complete. Next path confirmed: face-offset foundation → reducer handedness → split/merge inheritance.

## 37. Segment face-offset review (2026-07-16; for Codex)

Codex asked: review the `segment_face_offset` metadata shape and the warning-envelope alignment. **Verdict: both approved — and the envelope integration deserves specific praise: the N-17 lesson was applied proactively this time, with a regression test, without being asked.** Verified: raceway+plant3d+telemetry **143 tests OK twice** (4 new offset tests), browser **2/2 OK**, full **eht 360 OK**, statics clean.

### Metadata shape — approved

Identical discipline to the segment-orientation slice, which is exactly right: versioned schema (`raceway.segment_face_offset.v0`), node-UUID-pair keying, server-side canonicalization (object shape, UUID validation, finite values, **±5 m limit, 0.5 mm epsilon dropping no-op offsets**), stale-override pruning on node replacement, draft offsets re-keyed at first save. The two intent kinds (orientation, offset) now share one persistence idiom — the third (reducer handedness) should copy it verbatim.

### Semantics — the important checks all pass

- **Centerline stays truth:** node coordinates, graph topology, and schedule lengths are untouched by offsets — correct, because an eccentrically-placed tray is the same length of tray, and the whole point of this intent is to prepare one-edge reducer matching without corrupting route truth.
- **Envelope honesty:** `_segment_proxy_corner_points(..., face_offset_m)` consumes the offset per segment, and the regression test proves an offset segment changes clash detection. Orientation + offset both now flow into the envelope — the class of "geometry intent the warnings silently ignore" is being closed at the source.
- **UI honesty:** offset-only segments show `Run default` orientation instead of faking an override.

### Rider for the reducer pass (small, don't lose it)

Two adjacent segments with different offsets now create a **face step at their shared node** — precisely the input reducer handedness will consume, but today it renders without comment. When the reducer pass lands, add a `face_offset_step` entry to the fitting/warning vocabulary for nodes where adjacent offsets differ beyond epsilon *within a same-size run* — that's either a deliberate reducer-like transition or a modeling slip, and both deserve visibility.

### N-18 — PG-mode fixture failure noted in the tracker (severity: low, test hygiene)

The tracker honestly records that PostgreSQL-backed `test plant3d` fails on a fixture project id (`P3D-GATEWAY-INACCESSIBLE`, 25 chars) exceeding a 20-char column — invisible in SQLite because SQLite doesn't enforce varchar lengths. Fix is one line (shorten the fixture id), but the lesson is worth keeping: **the periodic PostgreSQL-backed run catches length/constraint truths SQLite hides** — same reason the eht project runs both. Shorten the id in any nearby pass and re-green the PG path.

### Next

Reducer handedness / one-edge matching — with the persistence idiom to copy, the face-step vocabulary rider above, and the §33 split/merge inheritance rules still queued behind it. The architecture-critical path holds.

## 38. Reducer one-edge matching + offset-step review (2026-07-16; for Codex)

**Verdict: the reducer intelligence pass is approved — every §37 rider delivered, T-1 followed in-pass for the first time, N-18 fixed — and one new finding: the real-viewer browser suite has a cold-start timeout flake (N-19) that should be fixed before it teaches anyone to ignore red.** Verified: raceway+plant3d+telemetry **145 tests OK twice**, full **eht 360 OK**, statics clean. Browser suite: **flaky on cold start** (details below), green warm ×2 and green isolated ×2.

### Verified in the pass

- **One-edge matching as default, with the convention defined in math:** `_edge_offsets_m` fixes left/right relative to the segment's node-order direction (`left = offset + width/2`), and handedness is a named option set (`left_edge | right_edge | centerline`). One doctrine note: cross-member "left edge" is well-defined for near-collinear connections — which is precisely the reducer case — and reducers at strongly angled junctions aren't a real fitting anyway; if that ever needs guarding, gate the recommendation on approximate collinearity.
- **Honest resolution semantics:** `requires_face_alignment` flips to false *only* when saved segment offsets already align the recommended edge; centerline coincidence remains diagnostic context and no longer masks a missing alignment. Recommended `face_offset_m` per member turns the finding into an actionable suggestion — and the suggestion-apply workflow already has its own real-viewer browser test.
- **§37 rider delivered exactly:** `face_offset_step` placeholder + `raceway.warning.face_offset_step_at_node` with previous/next offsets, delta, epsilon, and recommended action — **with its T-1 event-dictionary row shipped in the same pass** (the rule is now being followed at source, not on reminder). **N-18 CLOSED** (fixture shortened; PG-mode plant3d in the verification list).
- KR's visual observation (shifted faces look odd against unmoved centerline nodes) recorded with the correct doctrine: a display-polish problem, never a reason to move saved route nodes.

### N-19 — Real-viewer browser suite cold-start flake (severity: low-medium, fix soon — flaky red is corrosive)

`test_real_viewer_draw_save_and_reload_raceway_run` times out (15 s `wait_for_function` on package load) when the three browser tests run consecutively on a cold start (~19 s total run), and passes warm (~6 s) and isolated (~3 s). Root cause is margin, not product: three consecutive Chromium launches against the live server on this machine. Two standard fixes, either suffices: raise the runtime-ready timeouts in the real-viewer class (15 → 45 s — generous timeouts on *readiness* waits cost nothing when green), or share one Playwright browser per test class instead of launching per test (also faster). Worth doing promptly: we watched F-19 erode trust for weeks precisely because intermittent red trains people to re-run instead of investigate.

### Next-pass advice — endorsed

(1) Surface reducer edge-match suggestions in the authoring workflow (apply-the-offset instead of reading JSON) — already begun, and note it is the **first true suggestion-apply loop in the product**: wire the accept/reject telemetry events on it from day one (the Tier-0 machinery is waiting for exactly this). (2) Segment split/insert/branch semantics for tee/cross materialization — with the §33 inheritance rules ready to apply.

## 39. Edge-match apply command review — the flywheel's first turn (2026-07-17; for Codex)

**Verdict: milestone pass, approved on every axis. The product now records its first real engineering-suggestion acceptances, the loop is tested end-to-end including the telemetry row, and N-19 is closed beyond my own diagnosis.** Verified: browser suite **green four consecutive runs** (~6 s each — the flake is dead), raceway+plant3d+telemetry **145 tests OK twice**, full **eht 360 OK**, statics clean.

### The apply command — semantics verified, one precedent worth naming

`Apply Edge Match` (Shift+T) collects unresolved one-edge reducer candidates and writes each `suggested_face_offset_m` into the segment's `segment_face_offset.v0` override — batched into **one undo step**, affected runs marked dirty, stale projection cleared, user told to save-then-refresh. The guard that matters most: **the command refuses to run while unsaved local edits exist, because suggestions derive from the last saved graph.** Name that as doctrine now — *every* future apply-suggestion command (Dijkstra routes included) must carry the same saved-state precondition, or a suggestion computed against stale truth gets applied to different geometry. First instance sets the pattern; this one sets it correctly.

### The telemetry loop — live, and tested end-to-end

`raceway.reducer.edge_match_offset` records `shown` when suggestions surface via fitting refresh and `accepted` on apply, with previous/applied offsets and `source: "apply_edge_match_command"` in the action detail; the event dictionary was updated **in the same pass** (T-1 at source, second time running). The real-viewer browser smoke drives the whole loop — 300 mm and 600 mm connected runs → suggestion → apply → 0.15 m offset on the small tray → **telemetry flushed and the accepted row asserted**. The data flywheel's first turn has an end-to-end test. From this pass onward, the Tier-2 training corpus contains genuine labeled examples of exactly the shape future route suggestions will use.

### N-19 CLOSED — beyond my diagnosis (calibration note)

My §38 diagnosis was timeout margin; Codex implemented the 45 s readiness constant *and found a second, real root cause I had missed*: a *test-order catalogue-seed dependency* (real-viewer setup now ensures a minimal catalogue when earlier tests flushed the migration seed). The verification note honestly records the first full-suite attempt failing before the fix — the reporting discipline holding even when it documents a stumble. Verified dead: four consecutive green suite runs.

### Next pass — split/insert semantics with intent inheritance: endorsed, rules ready

The §33 rules apply verbatim, now to **both** intent kinds: split → both children inherit orientation *and* face-offset; merge → keep only if parents agreed, else drop to run default *and warn*; stale-intent pruning already exists server-side and extends to the split path naturally. Two riders: the split point should cluster within the graph tolerance (10 mm) so an inserted node lands exactly on the segment; and the tee, once real, becomes the third fitting-vocabulary consumer of the same node — branch-width sanity (§29's parked third signal) rides in then.

## 40. Accessory geometry note review (2026-07-18; for Codex + KR)

Design review of `raceway-accessory-geometry-note-2026-07-17.md`. **Verdict: this is the best design note of the project so far — the Apply-Edge-Match ≠ reducer correction is exactly right, the port-based accessory model is the industry-correct abstraction, and the three-phase persistence plan applies our proven pattern with a better-stated criterion than I'd have written ("store only decisions that cannot be re-derived reliably"). Approved, with one must-decide gap (A-1), one must-address geometry problem (A-2), and answers to the three open questions.**

### What the note gets right (keep all of it)

Port-derived accessories (the same P-point/connector concept E3D, SP3D, and Revit all converged on — deriving ports from segment ends with full frame, dims, orientation, offset, and edge positions future-proofs vendor mapping for free); Offset-vs-Move as different commands with six-direction move gated behind split/insert; no vendor meshes for MVP with the parametric proxy retained for clash even after vendor visuals arrive (F-10/F-14 doctrine holding); "do not persist baked vertices"; the implementation order (split/insert first, again); and an acceptance list that includes a product-truth test — *proving Shift+T is not mistaken for final reducer geometry*.

### A-1 — The port-frame handedness convention is unstated; pin it before any reducer geometry (must-decide)

At a junction, two ports meet with **opposing tangents** — run A's segment points *into* the node, run B's points *out*. If each port defines "left" in its own direction sense, port A's left and port B's left are on *opposite sides*, and `left_edge` handedness is ambiguous — the exact ambiguity class that ships mirrored reducers. One paragraph fixes it; suggested convention: **handedness is expressed in the frame of the wider port**, and the narrower port's frame is flip-aligned so both tangents point the same way before edges are compared. Whatever the choice, it must be written before proxy v0, and the existing `_edge_offsets_m` convention (left = +lateral normal in node-order direction) must be reconciled with it explicitly.

### A-2 — Straight-proxy cutback at accessory extents (must-address in proxy v0)

A reducer body of development length L, or a bend of radius R, occupies centerline length that the straight tray proxies currently also occupy — without **cutback** (trimming each straight proxy by the accessory's occupied extent: L/2 per side for reducers, `R·tan(θ/2)` for bends), the bodies overlap: visually wrong in shaded mode and double-counted in the clash envelope. This is the classic fitting-trim problem every plant CAD kernel solves; for us it's a *derived* per-segment trim distance (never persisted). Add it to the reducer acceptance list.

### Smaller riders

- **A-3 (BOQ honesty line, Phase 1):** today's schedule reports gross centerline length; once accessories carry real development lengths, add the assumptions line "straight lengths are gross; fitting development lengths not yet deducted" — deduction itself can come later, silence about it cannot.
- **A-4 (sequencing):** riser inside/outside derivation depends on face orientation, and vertical-segment orientation still falls back to an arbitrary axis (§25). The note's "expose unresolved status" is right, but **vertical-orientation inheritance from the adjacent horizontal segment should land before or with riser proxy v0**, or most risers will report ambiguous.
- **A-5 (scope line):** reducer proxy v0 should cover **same-family unequal-width** transitions only; `family_transition` and `service_transition` categories stay warnings/advisories, not generated bodies.

### Answers to the note's open questions

1. **(KR's, my advice)** Default `left_edge`, deterministic, with the chosen handedness always visible and one-click switchable — do *not* force a modal choice per reducer; defaults-with-override is our pattern, and forced modals at every unequal junction would be Stage-6-v1-grade friction. A later refinement can make the default side-aware (keep the rack/wall-side edge straight).
2. **(KR/Claude)** **Heuristic first, catalogue later — do not block rendering on catalogue tables.** Requiring vendor data before geometry inverts our generic-seed doctrine and re-opens the F-10 trap. The `max(0.45 m, 2·Δwidth)` heuristic is conservative versus real parts (straight reducers are commonly ~300 mm) — slightly long is the *safe* error direction for clash — and the note already requires exposing the assumption. Named constants + assumption line, ship it.
3. **(Mine to answer) Yes — gate reducer auto-suggestion on near-collinearity.** Suggest `REDUCER_COLLINEARITY_MAX_ANGLE_DEG = 15` (named constant): beyond that, an unequal-size junction is really a bend-plus-reducer or a tee case, and the suggestion should stand down with an advisory ("unequal sizes at angled junction — resolve bend and reducer separately"). This also protects A-1, since frame alignment is only well-defined near-collinear.

### Sequence confirmed

Split/insert semantics → reducer handedness UI (with A-1 pinned) → reducer proxy v0 (with A-2 cutback) → bend/riser proxies (with A-4) → tee → cross. No reordering.

## 41. Split/insert foundation review + the merge-rule answer (2026-07-18; for Codex)

**Verdict: the split/insert foundation is approved — inheritance, remapping, and re-keying all match the §33/§40 rules, and the A-1 decisions were folded into the accessory note before coding. On the merge nuance Codex asked about: per-kind preservation is the right base rule, but there is a real frame-coupling exception (N-20) — small fix, genuine silent-meaning-change class.** Verified: raceway+plant3d+telemetry **145 tests OK twice**, browser **3/3 OK**, full **eht 360 OK**, statics clean.

### Split/insert implementation verified

Split at percentage with the inserted node immediately selected (right UX); **children inherit both intent kinds** (§33 rule 2 ✓ across orientation *and* offset); draft intent remaps on index shifts and re-keys through the node-UUID migration path at save; merge on intermediate-node delete carries agreeing intent and drops conflicts with a status message (§33 rule 3, per-kind); projections cleared on every topology change; undo/redo covers split context. A-1 decisions recorded in the accessory note as KR decisions: wider-port frame, `left_edge` default with override, heuristic development length, named collinearity gate — all four of §40's answers, adopted.

### N-20 — Agreeing face offset must not survive a merge that changes its frame (severity: low-medium, few-line fix)

Codex's nuance question, answered from the geometry: **the face offset is applied along the *oriented* width axis** (`_segment_proxy_corner_points` builds the oriented basis first, then offsets laterally within it — same in the JS `segmentCornerPoints`). So the offset's *physical direction depends on the orientation it was expressed under*. Concrete failure: parent A `Roll Right` + 0.15, parent B `Roll Left` + 0.15 — orientations conflict and drop to run default `Open Up`; offsets numerically agree and survive — but the merged segment is now displaced 0.15 m *horizontally*, when each parent's 0.15 was a *vertical* displacement (opposite verticals, in fact). The preserved number never meant what it now does. Rule to add: **an agreeing face offset survives a merge only if the effective orientation (override-or-run-default) is unchanged by the merge; otherwise drop it too, with one combined status message.** Parents agreeing on orientation are unaffected; only the conflict path triggers. Rare in practice, but it's the silent-meaning-change class our doctrine exists to forbid, and the fix is a few lines where the merge already compares intent.

### Next-pass set — endorsed, matches §40's sequence exactly

Reducer handedness UI (`left_edge` default, `right_edge`/`center` override — wider-port frame per A-1) → reducer proxy geometry v0 (tapered body, heuristic development length exposed as assumption, **A-2 straight-proxy cutback in the acceptance list**) → then click-on-segment split and the tee branch workflow on this foundation. Fold N-20 into whichever of these touches the merge code first.

## 42. Scorecard established + one queued task for Codex (2026-07-18)

- **Development scorecard created at KR's request:** `plant3d/records/audit/development-scorecard.md` — Claude-owned, honest 1–10 per category, with a written update policy (phase completions, every ~10 passes, score-moving events, monthly minimum), a drift-watch section, and an append-only history log. Baseline overall ≈ 7.9. Includes a correction: Claude's earlier "no remote/backup" flag was wrong — remote push discipline and vendor-data backup DBs (local WSL Docker + cloud Ubuntu Docker) exist; the true DevOps gap is the absence of an automated test pipeline (CI).
- **Queued task for Codex (KR-assigned): vendor-catalogue sync command.** Sync the irreplaceable curated data from the dev database to KR's two backup databases. Suggested shape, consistent with house rules: a management command, **dry-run by default with `--execute`**, source strictly read-only, targets passed explicitly (env/URL), Database Safety Protocol wording in `--help`; scope = the curated/validated tables only — `ElecEHT_Vendor` (SR+legacy MI), the normalized MI catalogue tables, cold-cable catalogue, ASME B36 + thermal-conductivity references, and now also **`RacewayFamily`/`RacewaySize`** (the raceway seed is curated data too). Row-count report per table, no deletes on targets without a separate explicit flag.
- Drift-watch note now lives in the scorecard: the accessory arc is at its timebox boundary — reducer v0 + tee close it; the strategic frontier is Phase H + durable EHT persistence.

## 43. Synthetic accessory proxy review (2026-07-19, commit `579af3d`; for Codex)

**Verdict: approved — N-20 closed with the exact §41 semantics, A-2 cutback delivered with textbook math, and the deferral list is disciplined.** Verified: raceway+plant3d+telemetry **146 tests OK twice**, browser **3/3 OK**, full **eht 360 OK**, statics clean.

### Verified closures

- **N-20 CLOSED precisely:** `mergedSegmentIntent` records each parent's *effective* orientation frame, and an agreeing face offset survives only when both parents' effective frames equal the merged frame (`offsetFrameSurvives`) — otherwise dropped with the existing warning path. This is the frame-coupling rule word for word.
- **A-2 cutback delivered ahead of the reducer:** straight rails/faces trim near bend/riser proxies using `R·tan(θ/2)` (`_bend_cutback_m`) — the correct formula — with tangent points in the geometry recipe, so the future reducer inherits a solved problem.
- Bend/riser proxies as `synthetic_proxy` items with radius, cutback, and geometry recipes under a versioned scheme (`raceway.accessory_proxy.v0`) plus an assumptions row for the project-neutral defaults (0.6 m radius, 8 curve segments) — honesty discipline intact; riser inside/outside still reports *unresolved* where orientation is ambiguous (A-4 pattern held rather than guessed).
- Tee/cross placeholders derive from graph degree (3/4) — topology-first, exactly as the accessory note requires; accessory rails join the measurement snap set; `Radius m` control is draft-local.
- Deferrals are the right ones: reducer body with handedness/taper (the remaining arc item), detailed tee/cross bodies, radius/handedness persistence, vendor dimensions.

### One watch item, no new findings

The default radius (0.6 m) and curve segments are draft-local and *not yet persisted* — consistent with Phase-2 persistence rules ("store only what can't be re-derived": a user-chosen radius qualifies *when* the choice UI becomes real). When radius/handedness persistence arrives, it should reuse the segment-intent metadata idiom verbatim. Not a finding — a reminder that the third intent kind now has a proven template.

### Arc status

With bends/risers proxied and cutback solved, **the accessory arc's remaining MVP item is the reducer body (handedness + taper)** — after which, per the drift-watch, the pivot to Phase H + durable EHT persistence is due. The scorecard's drift-watch is updated accordingly.

## 44. JS audit reconciliation — Codex's findings vs Claude's parallel audit (2026-07-20; for Codex + KR)

Double-blind round two, reconciled. Codex's audit (`raceway-overlay-js-audit-2026-07-19.md`) and my parallel investigation converged on the same core defects: **F-21** (global dirty gate) = my H1(a) — and Codex found the *precise* mechanism (a harmless one-node draft tripping the gate) where I had only the class; **A-7** (left-edge-only body materialization) = my H2, which I predicted might survive unnoticed — it didn't. **F-22** covers my H1(b) symptom (candidates present but inapplicable, now explained on click). Fixed state verified green: 146 tests ×2, browser **4/4** including the new one-node-draft and family-transition regressions. Codex's five hardening recommendations are endorsed as written — #1 (`computeRacewayCommandStates` as a pure, testable layer) and #4 (state invariants) are better-specified than my equivalents.

### Balance items — in my audit, not yet in Codex's (B-series)

| # | Item | Why it matters |
| --- | --- | --- |
| B-1 | **Cross-boundary contract tests, server-side**: Python tests pinning the exact fields/strings the JS reads (`face_alignment.basis == "one_edge_matching"`, `member_offsets`, `proxy_kind == "reducer_taper"`, candidate `kind`/`status` values) | The bug family here is *server↔client string drift with no referee*. Client-side invariants (Codex #4) can't catch a server rename; a server-side pin breaks a test instead of a button. The single most important structural addition |
| B-2 | **Fail-loud client checks**: validate the projection `schema`/version tag on load and warn on mismatch; when a non-empty candidate list filters to zero, log per-candidate exclusion reasons to console | F-22 explains on *click*; B-2 makes silent drift announce itself *without* user action |
| B-3 | **Disabled-reason in the status line**, not tooltip-only | A disabled button cannot be clicked for its F-22 explanation; the reason must surface where the user is already looking. Ten lines |
| B-4 | **Server enrichment hardening for `insufficient_segment_context`**: verify a normally-connected endpoint can never legitimately lack adjacent-segment context, and contract-test that guarantee | F-22 *explains* the case; nobody yet asked whether it should be reachable at all for healthy geometry |
| B-5 | Tie the whole hardening pass to **CI (register A3)** | Every check above only defends if it runs on every push |

### Sequencing suggestion

Codex's hardening pass + B-1..B-4 as one combined slice **before tee/cross body geometry** (Codex's own recommendation, seconded) — with B-5/A3 landed the same week so the new pure-function tests run per-push from day one. A-7's resolution (persist handedness via the segment-intent idiom, or label right/center as drafting aids) should be decided in that pass rather than deferred, since the handedness UI is already user-visible.

## 45. Tee/Cross v0 plan review + the main/branch persistence question (2026-07-20; for Codex + KR)

### Answer to Codex's question: projection-only wins — with one boundary rule

**Agree with Codex's vote.** The persistence criterion from the accessory note settles it: *store only decisions that cannot be re-derived reliably.* Main/branch at a tee is re-derivable in the overwhelming majority of real cases — the through-run (two near-collinear segments at the node) is the main; the odd leg is the branch. Genuinely ambiguous nodes (all-angled three-ways, equal-width Y-junctions) get the same honest treatment risers already have: **inferred where clear, `unresolved` + ambiguity warning where not.** Persisting now would freeze semantics before manual use validates them, and the retrofit cost later is ~zero — when override intent is needed, it's one more `raceway.tee_intent.v0` node-keyed metadata entry in the proven idiom on stable UUID keys.

**The boundary rule to record now:** inferred main/branch may drive *proxy visuals and warnings*, but must **not** drive *part sizing in exportable deliverables*. A tee is procured as main×branch; if the schedule CSV ever lists a tee size derived from a wrong inference, an inference error becomes a procurement error. Until inference is unambiguous for a node or a user override exists, the schedule line reads "tee (orientation unresolved)" — never a guessed designation. Honesty doctrine, applied to the one place it could leak into money.

### On the arc-closure plan — endorsed, with three adjustments and one addition

1. **"Stop polishing reducer/bend/riser; close with Tee/Cross v0; then pivot" — full agreement.** This is the drift-watch position verbatim, and Codex enforcing the timebox on itself is the healthiest sentence in the plan.
2. **Branch Contract Hardening first = B-1 applied proactively to the new surface — excellent. But clarify C10's fate.** The plan lists contract tests for *tee/cross* fields only; the agreed C10 slice (pure command-state layer, JSDoc/@ts-check, geometry/DOM split, invariants, **B-1 retro-pins for the existing reducer/bend/riser fields**, B-2/B-3 fail-loud diagnostics, A-7 resolution) is not in the task list. My position: retro-pin B-1 for existing surfaces + B-3 + the A-7 decision ride the arc-closure passes now; the **full C10 refactor sits between arc closure and Phase H, not skipped** — Phase H adds the biggest JS yet (path preview, assignment UI), and building it on the unrefactored monolith repeats the Apply-Edge-Match trap at higher stakes.
3. **Mild scope challenge on Cross v0:** KR's recorded refinement (§23-era backlog) was "cross fittings can follow later if project usage demands it," and degree-4 placeholders + mixed-size warnings already exist. If the cross body falls out of the tee machinery in a few hours, fine; if it's half a pass or more, cut it — a placeholder is MVP-sufficient and Phase H arrives one pass sooner. Codex's judgment call, with the recorded deferral cited.
4. **One addition to the pivot list:** cable routing/assignment/fill/AI-loops is right, but the pivot scope must name **durable EHT persistence** — the integrated-chain demo (heat-trace calc → route through trays → length back into cold-cable sizing → schedule) needs EHT devices and routes in the database, not localStorage, and EHT is Phase H's first consumer. Also flag: "AI-assisted suggestion loops" is the trigger for decision record **0007 (`ai_gateway`)** — the moment approaches. And when Dijkstra lands: suggestion-with-reasons, saved-state precondition (§39 doctrine), telemetry wired from day one — all machinery already waiting.

## 46. Nine-day catch-up review: B-list closure, hybrid doctrine, Tee/Cross v0, C10 slice (2026-07-28; for Codex + KR)

Scope: commits `4ba609d` → `888ef9b` (five passes). **Verdict: the strongest stretch of the project — every B-item landed (several beyond the ask), the hybrid accessory doctrine is exactly right, Tee/Cross v0 honors the §45 boundary rule, and the C10 slice quietly began Phase-H contract preparation.** Verified: raceway+plant3d+telemetry **152 tests OK twice**, browser **6/6 OK**, full **eht 360 OK**, statics clean, tree clean.

### Closures verified in code/tests

- **B-1 CLOSED (reducer surface) and extended:** Python contract pins for every reducer field/string the JS reads — projection version, kinds, statuses, basis, handedness options, `member_offsets`, `proxy_kind == "reducer_taper"`, port fields. Plus a **Phase-H schedule contract test** pinning durable run/node keys, source points, `coordinate_frame` (added additively — smart prep), edge offsets, and branch placeholder fields with *projection-only sizing status* — which also **verifies the §45 boundary rule** (inferred main/branch never drives exportable sizing).
- **B-2 CLOSED:** projection-version mismatch warnings, shape validation on `items`/`counts`, per-candidate exclusion diagnostics retained. Console-based — acceptable.
- **B-3 CLOSED and generalizing:** `#racewayCommandHint` shows disabled reasons visibly below the status line, browser-asserted; shortcut-triggered disabled commands report the raw reason.
- **B-4 CLOSED beyond the ask:** the fallback now carries diagnostics, **a contract test proves normally-connected unequal endpoints cannot reach `insufficient_segment_context`** (exactly what I asked), and a deliberate malformed-case test keeps the branch visible rather than vestigial.
- **Hardening rec #1 REALIZED:** `computeRacewayCommandStates(snapshot)` — pure, DOM-free, drives buttons *and* hints, exposed for browser probing, tested for the clean-enabled and dirty-disabled cases. This is the architectural fix for the Apply-Edge-Match failure class, not just the instance.
- **Hybrid accessory doctrine (KR's palette question): the recorded answer is correct** — derive candidates server-side, present lightweight proxies, user accepts/overrides/replaces from a palette, choices persist as intent, vendor parts substitute later. Manual-only would drift from schedules/clash/pathfinding; automation-only demands vendor choices too early. It is the suggest-accept doctrine extended to accessories, now written into the accessory note where it belongs.
- **Tee/Cross v0:** projection-only with inferred branch intent and ambiguity placeholders, counts in schedule + CSV — per §45 on every point.
- **C10 slice:** JSDoc typedefs for command/summary shapes; DOM-free `buildScheduleSummaryViewModel`/`buildFittingSummaryViewModel` replacing scattered field reads in HTML rendering.

### Still open from my previous asks (the balance)

C10 remainder (deeper geometry/DOM module split; broader graph/fitting-summary contract pins; eventual separate JS module file); **A-7 decision** (persist handedness or label right/center as drafting aids — UI is user-visible now); **A-4** (vertical-orientation inheritance for risers — proxies ship with honest `unresolved`, but inheritance itself is unbuilt); **B-5/CI** — still the most-repeated open item on the book, blocked only by KR's A3 go-ahead; C8 (BOQ gross-length assumptions line — not yet sighted in the schedule passes).

### Scorecard update triggered

Score-moving events landed (command-state seam, contract pins, view models, six browser workflow tests): JS 6→7, Testing 7.5→8, overall ≈ 8.0. DevOps stays 5 — CI remains the gap. Scorecard history updated.

## 47. Tee/Cross authoring + C10.2 review — the balance narrows (2026-07-28; for Codex + KR)

Scope: `5dc8d58` (intuitive Tee/Cross authoring) + `9797238` (C10.2 guardrails). **Verdict: both approved. Make Tee completes the original M-3 vision in full — snap a branch onto a segment, split, join, one undo step — and Make Cross reusing the `unconnected_crossing` warning as its picker is a genuinely elegant design (the warning *is* the work-list). Codex's point-by-point §46 response in the tracker is the collaboration protocol at its best.** Verified: **154 tests OK twice**, browser **6/6 OK**, full **eht 360 OK**, statics clean.

Highlights verified: shared `splitRunSegment()` gives Split/Make-Tee/Make-Cross one intent-remapping path (no divergence class); a refactor bug was caught by browser smoke before shipping (the net works); graph contract pins cover every Make-Cross JS dependency; the fitting-summary pins close the last un-pinned viewer surface; **C8 CLOSED** with the exact assumptions line, pinned in tests; `validateGraphProjectionContract` extends fail-loud to the graph payload. **A-7 DECIDED** via Codex's recorded stance — left/right/center are drafting controls; only resulting face offsets persist until accessory acceptance/intent exists — which is the "label as drafting aids" option and is accepted; A-7 closes.

### The remaining balance — everything raised and not yet taken up

**Codex-side (all agreed-deferred, none disputed):** C10 tail (geometry/DOM module split; separate JS module file) — *the one item I'd insist rides before Phase H's big JS*; A-4 riser orientation inheritance (backlog, agreed non-blocking); C9 accessory-intent persistence (waits for the acceptance palette); C4 `session_key`; C5 blocked-endpoint assertion; C6 M-5 copy-offset + M-6 EL-grid; C7 remainder (work-plane messaging, segment-pick reuse beyond Tee); C1 vendor-sync command (KR-assigned, still unbuilt); C11 stale-doc retirement; B-5/CI — coded in an afternoon the day A3 is spoken.

**KR-side (unchanged, all aging):** A1 catalogue-seed (19+ days), A2 workspace file, **A3 CI go-ahead — the highest-leverage word on the board**, B1 decision-sweep habit, B2 eht June sign-off, B3 root-stub refresh.

**Gates:** D2 georeference proof, D3 large-model test, D4 SEC-P1b leftovers, D5 vendor licensing, D6 0007 — all correctly parked, none started.

### Arc verdict

With Make Tee/Make Cross accepted by KR's manual check, **the accessory arc is closed for MVP.** Per §45/D1: the C10 module-split tail, then Phase H + durable EHT persistence. The next §-entry here should be reviewing route discovery over the graph — the thing this entire raceway campaign was built to enable.

## 48. Phase H-A1 plan position + pre-coding riders (2026-07-28; for Codex + KR)

Codex proposes Phase H-A1: server-side route-graph foundation (`raceway.routing`, weighted network from the saved graph, path tests, optional `/routes/preview/` endpoint), with H-A2 manual assignment UI after. **Aligned — this is the pivot the whole campaign built toward, and starting server-side with little visual change is the same projection-first pattern that made Stage 8A land clean.** Five riders to record before coding:

1. **H-1 — Edge identity must be node-pair-derived, not ordinal.** Codex's list promises "stable `edge_key` output for future consumers" — but graph edges today carry `E###` presentation keys that shift on any insertion (N-09). The durable edge identity is `start_node_key::end_node_key` (already the segment-intent convention). Any consumer-visible `edge_key` in routing output must be that pair form; `E###` must never appear in a route payload a consumer might store.
2. **H-2 — Make the weight function a seam, not a constant.** Length-only weights are right for A1, but Phase I adds bends, fill, and cost. Structure the router as `shortest_path(graph, start, end, cost=edge_length_cost)` with the cost callable injected — a five-minute decision now that prevents an algorithm rewrite later, and it is precisely where Tier-2 learned weights eventually plug in.
3. **H-3 — Deterministic tie-breaking.** Equal-cost paths must resolve identically every run (stable ordering by node/edge keys) — same doctrine as the graph projection, and it needs its own test, because a nondeterministic route suggestion would poison telemetry labels later.
4. **H-4 — Contract-first from birth.** Pin the route-preview payload in Python tests in the *same pass* that creates it (B-1 discipline, now house style): path node/edge pair-keys, per-edge lengths, total length, riser/horizontal flags, and an explicit `basis`/assumption block ("length-only weights, single-layer scope"). Endpoint access through `_layer_for_user`, node-key membership validated, and single-layer scope stated as an assumption (cross-layer/multi-package routing is a recorded non-goal for A1).
5. **H-5 — What A1 must NOT do:** no route/assignment persistence (that needs the consumer-neutral cable-ref design note first — one page, D3/F-07 shape: `owner_module` + opaque `cable_ref`, no eht imports); no UI suggestion loop yet (telemetry code `raceway.route.candidate` is already reserved for H-A2, where the §39 doctrine — reasons, saved-state precondition, telemetry from day one — applies wholesale). And **durable EHT persistence must appear in the Phase H plan as a named parallel workstream** — A1 doesn't need it, the integrated-chain demo does, and it must not slip to the end.

**Sequencing note:** H-A1 is server-side, so it does *not* violate §47's "module split before Phase H's big JS" — the C10 split must land **before H-A2 (the assignment UI)**, not before A1. Recorded so it can't quietly evaporate.

**On the CI fork Codex posed to KR:** false dilemma — the answer is *both*, in the order CI-then-A1. CI is one afternoon pass; approving A3 today means every Phase H pass is born under CI, and the momentum cost is half a day against a phase that will run for weeks. If KR forces a binary: CI first — Phase H is exactly the "project grows" moment CI exists to protect.
