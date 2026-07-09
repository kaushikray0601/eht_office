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
