

# RFC — Cable Tray / Raceway & Support Module: Architecture, Scope & UX

Date: 2026-07-02
Author: Claude (architect)
Audience: KR + Codex
Status: design proposal for discussion → will seed the new module's own `decisions/` once accepted

> This is a design/RFC, not an instruction to code. It proposes a **separate app** (`raceway`) that consumes the `plant3d` platform, its data model, its geometry strategy, its 2D-drawing path, and — most importantly — its **UX**. It is deliberately phased so Codex can build an MVP first and grow it, exactly as the spike has run so far.

---

## 0. The one-line answer to KR's question

**Yes — build it as a separate Django app, and here's the stronger reason:** the whole point of `plant3d` being neutral (not just a hardened `idfviewer`) is that engineering disciplines are **consumer modules** that reference the 3D platform but never live inside it. Cable tray is the *first real proof* of that contract. If tray logic lands in `plant3d`, we lose the neutrality that justified building `plant3d` separately — the same **ARCH1** concern I raised about EHT. So: `raceway` is a peer app to `eht`; both consume `plant3d`. Dependency arrows point **one way**: `raceway → plant3d`, never back.

I recommend the name **`raceway`** (the correct generic electrical term covering ladder, perforated/solid tray, wire-mesh basket, trunking, and later conduit/duct) over `cabletray`, so the app doesn't have to be renamed when trunking/conduit arrive. KR's call.

---

## 1. Where it sits — the platform overlay contract (the meta-architecture)

Before tray specifics, we should formalise the seam every module uses. This is small and pays back immediately (EHT will use the identical contract).

`plant3d` exposes three things to consumer modules; it imports nothing from them:

1. **Reference-model read API** — query `ModelObject`s (stable_id, tag, line_id, bounds, owning tile) and package/tile geometry + the **RTC coordinate contract** (`rtc_origin_render_xyz`, axis order, scale). Modules snap/anchor to these.
2. **Viewer overlay slot** — the viewer already renders named groups (`root`, `measurementGroup`, `ehtDraftGroup`). A module registers an **overlay group** (`racewayOverlayGroup`) drawn in the *same render frame* as the reference model. One shared camera/scene; each module owns its group.
3. **Access + project scope** — reuse `plant3d.access.*_for_user` (managed-project scoping via `ManagedProject.available_to_user`). Every raceway query is project-scoped the same way.

```
eht (module) ─┐
raceway (module) ─┼──► plant3d (platform: reference model, viewer host, RTC, access)
cable-routing ─┘        └──► never imports a module
```

**Coordinate rule (non-negotiable, per everything we've learned):** raceway geometry is authored and stored in the **plant3d render frame** and rides the **same RTC origin** as the package it overlays. A tray placed against beam B-0472 must sit exactly on B-0472 at plant-global coordinates — so the tray overlay must consume the package's `coordinate_transform`, not invent its own.

---

## 2. Domain grounding (what real EPC cable-tray engineering needs)

So the model is shaped by reality, not guesswork:

- **Tray types:** ladder, perforated, solid-bottom, wire-mesh (basket), trunking. Materials: HDG steel, SS, aluminium, GRP/FRP.
- **Standard sizes:** widths 100–900 mm, depths 50–150 mm, standard lengths (3 m / 6 m). Trays are *cut* from standard lengths.
- **Fittings ("the large accessories"):** horizontal bends (30/45/60/90°), vertical/riser bends (inside & outside), tees, crosses, reducers (straight/left/right), end plates, dropouts, covers, dividers/barriers.
- **Supports:** cantilever brackets, trapeze hangers (rod + channel), floor stanchions, wall brackets, base plates/anchors, strut (Unistrut). **Support spacing is engineered** from cable+tray load vs allowable span/deflection per **NEMA VE-1/VE-2** or **IEC 61537** (configurable per project).
- **Rules engineers care about:** bend radius ≥ cable minimum; **fill %** (power vs control vs instrument, per NEC/IEC); **segregation** distances between service classes; access/maintenance clearance; clash-free against structure and other disciplines.
- **Deliverables:** tray layout drawings, **support fabrication drawings** (for the fab contractor), **installation drawings** (for the site contractor), and **BOQ/BOM** (tray lengths by type/size, fittings by type, supports by type, total steel weight).

Two design consequences fall straight out of this:
- The library must be **parametric** (sizes × types × fittings × supports is a combinatorial explosion — you cannot store a mesh per instance).
- The tray network is naturally a **graph** (runs = edges, junctions/pull-points = nodes). Design it graph-ready now, because the *future* cable-routing/pulling module will route cables through this graph.

---

## 3. Data model (the `raceway` app)

Grouped by concern. All project-scoped; all in the plant3d render frame.

### 3a. Catalogue / library (KR's "separate library of tray objects + accessories")
- **`TrayFamily`** — a *type* of tray: `kind` (ladder/perforated/solid/mesh/trunking), material, standard lengths, rung/perforation params, cover option, plus a **geometry-generation profile** (cross-section rule). Vendor-agnostic.
- **`TraySize`** — width × depth for a family, with **load/span tables** (allowable UDL vs support span) and **weight/m**. This is what drives support spacing and BOQ weight.
- **`FittingType`** — bend/tee/cross/reducer/riser/endcap, with the geometry rule (e.g. bend = swept cross-section over an arc of `angle` at `radius`).
- **`SupportType`** — cantilever/trapeze/stanchion/bracket, with parametric geometry, load capacity, and a **fabrication template** (dimensioned parts list) used later for fab drawings.
- **`Vendor` / `VendorPart`** *(optional overlay)* — maps a generic family/size to a real vendor part number. **Governance:** reuse the project's existing rule — vendor data is *not* imported/trusted without validation (`is_validated` flag, like the EHT/MI catalogue). Start with generic families; add vendor parts deliberately.

The catalogue is **reference data** (seedable, versioned), separate from project routing data. Ships with a curated generic library so users are productive on day one.

### 3b. Routing (the source of truth)
- **`TrayRun`** — the **centerline route**: ordered nodes (each with XYZ in render frame + elevation), a `service_class` (power/control/instrument/IT), a target `TrayFamily`+`TraySize`, a tag, and status. *This is what the user edits.*
- **`TrayNode`** — a route vertex; may be a **junction** (tee/cross where runs meet) or a **pull-point** (graph-relevant later).
- The route is the **single source of truth**; physical parts are *derived* from it.

### 3c. Materialised physical model (derived, regenerable)
- **`TraySegment`** — a straight length realised along a run (cut length ≤ standard length), with size, service, weight.
- **`TrayFitting`** — a fitting instance auto-inserted at a node (bend/tee/reducer/riser), with the matched `FittingType`.
- **`TraySupport`** — a placed support: `SupportType`, position, **anchored to a plant3d `ModelObject.stable_id`** (the beam it hangs from), computed span, load, and pass/fail vs the load table.
- These are **regenerated** whenever the run or catalogue changes (like plant3d's "convert → package"). Never hand-edited as the primary record; overrides are stored on the run/node, not by mutating derived rows.

### 3d. Engineering + graph links (forward-looking, mostly later)
- **`CableAssignment`** *(v3)* — cables (by `cable_id`/`line_id`, read from the cable-engineering module) assigned to a run → drives **fill %** and auto-sizing. Read-only link, same pattern as the hot/cold `line_id` join we designed earlier.
- **Graph readiness** — `TrayRun` + `TrayNode` already form a node/edge graph with capacity (fill) and length. The future cable-routing module traverses *this* graph. Design the node/edge keys to be stable so that module can attach without schema change.

### 3e. Workspace
- **`RacewayLayer`** — a project-scoped, versioned container of runs/supports (an authoring session / revision), so you can snapshot "IFC-for-approval" vs "as-built".

---

## 4. Geometry strategy (how the 3D is made — this decides scalability)

**Parametric, generated — never a stored mesh per instance.** A run stores centerline + family/size; the mesh is *derived*:

- **During authoring: client-side live generation.** Three.js extrudes the tray cross-section along the centerline and swaps in fitting geometry at nodes, **live** as the user drags. This is what makes routing feel instant and premium (see UX). Reuse the family's cross-section profile.
- **On save: server-side "bake".** Persist the run + a generated **GLB overlay tile** (reusing the plant3d GLB pipeline: RTC-local, feature-IDs per part so tray parts are pickable exactly like model objects) + the derived `TraySegment/Fitting/Support` rows (for BOQ and 2D). The GLB is a *cache*; the run is the truth.

This gives instant edit feedback **and** a durable, streamable, pickable overlay that rides the existing tile/RTC/feature-ID machinery — no new render engine, no new picking path. It also keeps the library light: adding a size = new parameters, not new meshes.

---

## 5. The routing engine (materialisation + validation)

The heart of the module. Given a `TrayRun` centerline + catalogue selection, **realise** it:

1. **Split** the centerline into standard-length straights (compute cut lengths, offcuts).
2. **Insert fittings** at each node: bend angle → matching bend `FittingType` (with min-radius check vs assigned cables); size change → reducer; junction → tee/cross; elevation change → riser.
3. **Auto-place supports:** along each straight, at ≤ max span from the load table (tray weight + cable fill weight), at bends, at run ends; **anchor to the nearest valid structural `ModelObject`**; allow manual add/move/override.
4. **Validate** (report as a checklist, like the EHT connection-warning pattern — never block, always inform):
   - bend radius vs cable minimum, fill % vs limit, segregation distance between service classes,
   - support span vs load-table allowable, unsupported spans,
   - **clash** against reference model + other runs (reuse `three-mesh-bvh` from the render-format plan for fast intersection).

Everything is deterministic from (run + catalogue + assigned cables), so it re-materialises cleanly on any edit.

---

## 6. 2D drawings & BOQ (the deliverables — phased, because this is big)

Be honest: drafting-grade 2D is a large sub-system. Phase it so value comes early:

- **Phase A (cheap, high value): schedules/BOQ.** Tray lengths by type/size, fittings by type, supports by type, total steel weight, offcut summary — straight from the derived rows. Export CSV/Excel. This alone is contractor-useful immediately.
- **Phase B: projected layout drawings (SVG/DXF).** Orthographic projection of the run network to plan/section per area/elevation, annotated with tags, sizes, elevations, fitting callouts. **DXF output** so the fabrication/installation contractors open it in AutoCAD. Server-side generation from the derived model.
- **Phase C: support fabrication sheets.** Per `SupportType`, a dimensioned GA + material list + bolt/weld notes from the `SupportType` fabrication template → the fab contractor. Installation sheets = layout + support locations + tags → the site contractor.

Design the derived model now so Phase A works day one and B/C are additive, not a rewrite.

---

## 7. UX design — the part that makes or breaks it

KR is right: this is the commercial differentiator. The failure mode of every plant tool is making users **place 3 m sections one at a time**. We avoid that with one principle:

> **Route-first, part-later.** The user draws *intent* (a path at an elevation); the system *materialises* the physical tray, fittings, and supports. Users think in routes; the software does the catalog bookkeeping.

### 7.1 The seven UX pillars
1. **Elevation-plane (2.5D) routing.** 90% of tray runs are horizontal at a fixed elevation with vertical risers. Let the user **lock a working plane at an elevation** (e.g. EL +106.500) and draw the route on it like drawing on a floor, then "riser up/down" to change level. This matches how engineers think and eliminates fiddly free-3D dragging. (E3D/SP3D/Revit all do this.)
2. **Snapping is the product.** Snap to: structural members (`ModelObject` vertices/edges — the vertex-snap you already built is the seed), grid, elevations, existing tray endpoints/centerlines, and orthogonal directions. Show a clear snap marker + tooltip ("Snap: Beam B-0472 top flange, EL +106.500").
3. **Live feedback while routing.** A floating HUD shows, in real time: run length, current fill %, next support position, elevation, and any live clash — the same instant-feedback pattern as the EHT route length. The user should never wonder "is this valid?"
4. **Catalogue as a visual palette.** A collapsible, glassmorphic left palette (the Navisworks-inspired look KR asked for): pick family → size → service class, then route. Recently-used at top. Change size mid-route → downstream re-fits.
5. **Non-destructive editing.** Drag a node → tray + fittings + supports re-materialise instantly. Change family/size → re-fit. Delete a node → route heals. The route is always the truth.
6. **Ghost-the-plant focus mode.** Navisworks-style: while routing, fade/ghost the reference structure to a translucent grey and keep *your* tray crisp and coloured — so you see what you're doing in a dense plant. Isolate/hide by area or discipline.
7. **Author vs Review modes.** A clean review mode (no edit handles) with markup/measure/section for checkers and clients — because approvals happen here.

### 7.2 Screen layout (builds on the current viewer)
```
┌───────────────────────────────────────────────────────────────────────┐
│  ▸ Nav/View palette (glassmorphic, auto-fold): orbit·pan·plan·section·  │  ← KR item (c)
│    elevation · snap toggles · ghost-plant · measure                     │
├───────────┬───────────────────────────────────────────────┬────────────┤
│ CATALOGUE │                                               │ INSPECTOR  │
│ & TOOLS   │              3D VIEWPORT                       │ selected   │
│ (palette) │   reference model (ghosted) + tray overlay    │ run/segment│
│ family    │   working-plane grid @ EL +106.500            │ /support:  │
│ size      │   live route preview + snap markers           │ props,fill,│
│ service   │                                               │ validation │
│ supports  │                                               │ checklist  │
├───────────┴───────────────────────────────────────────────┴────────────┤
│  ROUTE HUD: length 42.3 m · fill 38% · supports 15 · 0 clashes · EL+106  │
└───────────────────────────────────────────────────────────────────────┘
```
This is deliberately the same shell as the plant3d viewer (collapsible panels — KR items a/b), so it's evolution, not a new UI.

### 7.3 The core authoring loop (what a user actually does)
1. Pick family/size/service from the palette (or accept the project default).
2. Lock a working plane at an elevation (or route free-3D).
3. Click to place route nodes, snapping to structure; the tray **previews live** with fittings auto-forming at bends.
4. Riser up/down at a node to change elevation; tee off to branch.
5. Finish → supports auto-place at spec spacing, anchored to structure; the validation checklist populates.
6. Adjust anything (drag a node, change a size, move a support) → everything re-materialises.
7. Save → baked to a durable overlay + BOQ.

### 7.4 Colour & selection (ties to KR items d/e)
- **Colour by service class** (power/control/instrument) by default, toggle to colour-by-size or colour-by-status. This is how reviewers read a plant instantly.
- **Selection = highlight the actual part** (recolour/emissive), not a superimposed wireframe (KR item d) — reuse the feature-ID highlight path already in the viewer.
- **Measurement** already has vertex snap (KR item e); "distance to a plane/face" is a natural add here because tray work is elevation/offset-driven — pick a reference face on structure, measure perpendicular offset. Moderate effort (define plane from a picked face normal + project); worth doing *inside* this module where it's most valuable.

---

## 8. Access, safety, coordinate integrity (reuse, don't reinvent)
- Every query project-scoped via `plant3d.access.*_for_user` (managed-project rule) — same as plant3d.
- All mutations POST-only + owner/permission-checked (the pattern the delete/save-case views already follow).
- Raceway geometry rides the package RTC origin; a regression test must assert a tray node at plant-global coordinates round-trips to the same render-local position as its anchor `ModelObject` (the F1/F3 discipline, applied to overlays).
- `plant3d` core imports nothing from `raceway`; a CI check can assert the one-way dependency.

---

## 9. Phasing (so Codex builds incrementally, not all at once)

**MVP (prove the loop):**
- `raceway` app + overlay contract + a **small seeded generic catalogue** (1–2 ladder + 1 perforated family, a few sizes, bends/tees/reducers, cantilever + trapeze supports).
- Client-side live centerline routing on an elevation plane, snapping to `ModelObject` + grid.
- Materialise straights + bends + tees; **manual** support placement.
- Save → baked GLB overlay + derived rows; **BOQ (Phase A)**.
- Colour-by-service; feature-ID selection; validation checklist (fill %, bend radius, unsupported span) as warnings.

**v2:**
- Auto-support spacing from load tables; anchoring to structure; risers/reducers; clash check (BVH); reducer/riser fittings; more catalogue.
- Distance-to-plane measurement; ghost-plant focus mode.

**v3:**
- Cable assignment by `cable_id`/`line_id` → fill-driven auto-sizing; graph exposure for the future cable-routing module.
- 2D drawings Phase B/C (DXF layout + support fab sheets); vendor-part overlay with validation governance.

**Explicitly NOT in early scope (avoid drift):** full drafting-grade drawings, automatic clash *resolution*, cable pulling/drum optimisation (separate module), conduit/duct (later, though `raceway` name leaves room).

---

## 10. Open decisions for KR
1. **App name:** `raceway` (future-proof, covers trunking/conduit) vs `cabletray` (specific). Recommend `raceway`.
2. **Governing standard for support spans/fill:** NEMA VE-1/VE-2 vs IEC 61537 — configurable per project, but which is the default seed?
3. **Catalogue seed:** ship a curated generic library (recommended) vs start empty and let users define families.
4. **2D output priority:** confirm BOQ-first (Phase A) is enough to start, with DXF drawings following — vs needing drawings sooner.
5. **Server-bake vs client-only geometry:** confirm the hybrid (live client author + server bake on save) — I strongly recommend it; it reuses the whole plant3d pipeline and keeps edits instant.

---

## 11. Why this design is "clean"
- **Separation of concerns:** a peer module, one-way dependency, zero coupling into `plant3d` core — the ARCH1 principle, finally realised for a real discipline.
- **Route-as-truth / parts-as-derived:** mirrors plant3d's own "source → derived package" model; makes editing non-destructive and BOQ/2D trivially regenerable.
- **Parametric library:** the combinatorial catalogue stays small and the model stays light — reusing GLB/RTC/feature-ID machinery, not a new engine.
- **Graph-ready:** the tray network is already the graph the future cable-routing module needs.
- **UX-first:** route-first authoring + elevation planes + snapping + live feedback is the difference between "another tedious plant tool" and something engineers *want* to use — which is exactly where the commercial value is.

---

## 12. Current Plant3D Readiness Update — 2026-07-05

The viewer now has enough generic authoring primitives to begin the raceway MVP without building a separate render shell:

- Generic overlay/layer controls exist for plant model, measurement, reference grid, plot plan, and consumer draft overlays.
- EHT draft routes now have editable nodes in the inspector. This is the small prototype for future tray-run node editing: route geometry should update from node coordinates, not from hand-placed physical tray parts.
- Component placement now has a first surface-normal offset so point devices do not intentionally place their centerline on the clicked structure face. Raceway will need the stronger version: face/elevation-aware mounting with orientation and clearance.
- Cable routes now have first-pass endpoint anchoring to EHT point devices. This is the same authoring pattern raceway needs later for tray endpoints, tees, and support anchors: an endpoint should resolve to a domain object/anchor, while intermediate bend nodes can remain free route geometry.
- Plane-distance measurement is available against the current grid/reference plane. Raceway should extend this into explicit working-plane/elevation routing rather than free-3D dragging for every tray node.
- Draft persistence is still browser-local. Durable EHT/raceway data must be owned by the consumer module or integration app, with `plant3d` supplying anchors, coordinate transforms, and render-package context only.

Near-term raceway sequencing remains:

1. Define the `raceway` app boundary and overlay payload contract.
2. Implement route-first tray centerline drafting on an elevation plane.
3. Add a small generic catalogue and live client preview.
4. Persist route-as-truth in the raceway app, then server-bake a GLB overlay cache using the existing plant3d coordinate/RTC discipline.

---

## 13. Collision And Cable-Routing Engine Gate — 2026-07-05

Manual testing showed that ad hoc "soft stop" behavior is not enough for engineering authoring. Before serious tray/ladder/trench/duct/sleeve tools are built, the platform needs a deliberate collision and routing foundation.

### Collision stance

- Do **not** ship partial hard-stop physics as if it is authoritative. A false stop or missed clash is worse than no stop because users will trust it.
- Keep the current authoring controls clean and free-moving until a real collision layer exists.
- Build collision in three levels:
  1. **Warning only:** selected draft item reports nearest structure penetration / clearance risk in the inspector.
  2. **Preview constraint:** while dragging or coordinate-editing, show a red/amber state when the next position clashes, but allow override.
  3. **Hard constraint:** only after component mounting faces, bounding volumes, route sweeps, and override rules are designed and tested.
- Use simple bounding boxes/spheres only as early UX hints. Production clash checks should move toward BVH-backed mesh or swept-volume tests, especially for cable trays, supports, ducts, trenches, and sleeves.

### Cable route stance

- Cable routing should move from free air-clicking to a source/destination-first workflow:
  1. Pick source component.
  2. Pick destination component.
  3. Suggest a Manhattan route as a dotted preview.
  4. Let the user edit route nodes inside a reasonable routing envelope.
- A* or Dijkstra should be introduced as a **suggestion engine**, not an automatic design authority. Early graph nodes can be component anchors, route bends, tray/raceway nodes, and blocked/avoid zones.
- SR tracer routes should normally auto-place or require an end termination at the final end. Recommended UX: allow route from JB, then auto-create an End Termination at Finish Route if none exists at the destination.
- Bend handling should start with orthogonal/Manhattan suggestions and bend-radius warnings. Full curved bend geometry should be added after the route-as-truth model has cable diameter and bend-radius metadata.

### Suggested coding order

1. **Viewer UX cleanup:** keep route controls compact; show node labels only while creating or selecting a route; keep coordinates editable but stop growing the inspector as the main long-route editor.
2. **Source/destination route mode:** user selects source and destination components first, then the route is edited between locked anchors.
3. **Routing core module:** create a small pure-Python/JS-neutral routing service that can accept anchors, obstacles/avoid zones, orthogonal preference, bend radius metadata, and later raceway graph edges. Keep it independent of Django views and Three.js.
4. **Manhattan suggestion:** first route suggestion is deterministic orthogonal routing with minimal bends inside a bounding corridor.
5. **A*/Dijkstra extension:** add only after the routing core shape is stable. Dijkstra is useful on established raceway/tray graphs; A* is useful for geometric/grid routing with heuristic distance. Both should return suggestions with reasons, not silently commit design.
6. **Collision layer integration:** route suggestions consume collision/clearance results as costs or blocked cells/edges; the collision engine remains separate from route authoring UI.
