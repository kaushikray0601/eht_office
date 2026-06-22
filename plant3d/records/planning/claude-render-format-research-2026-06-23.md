# Claude Research — Render Format, Picking, Tiling, Unit Validation

Date: 2026-06-23
Author: Claude (architect/auditor), at Codex's request
Audience: Codex + KR
Companion to: [audit](../audit/claude-review-2026-06-22.md), [agreed architecture](agreed-architecture-2026-06-22.md)

## TL;DR — the recommended stack (decisive)

> **Per-tile content = binary glTF (`.glb`) + `EXT_meshopt_compression` + `EXT_mesh_gpu_instancing`, with per-vertex feature IDs (`EXT_mesh_features`). Scene = a 3D-Tiles-1.1-style `tileset.json` (plant-local, not geospatial), one subtree per Area/Unit, octree + elevation split, geometricError LOD, per-tile RTC origins. Viewer = Three.js + the MIT `3d-tiles-renderer` + `three-mesh-bvh` for picking + `BatchedMesh`/instancing. All dependencies MIT/Apache. No custom binary format. No xeokit (AGPL).**

Everything below justifies and sequences that. The single most important cross-cutting point: **format choice and the RTC/precision story are the same problem** — glTF/meshopt buffers are float32 and quantized, so you *cannot* store plant-global coordinates in a `.glb`. Per-tile RTC is not optional once you go binary; the tile origin must be applied at the scene-graph node, not inside the buffer. Design them together. This also means **F3 (a real plant-global file) gates the format work**, not just the old JSON viewer.

I strongly endorse Codex's instinct: **stop polishing the JSON viewer; make the leap to a real package format.** JSON was the right spike; it has served its purpose.

---

## Q1 — Best browser format for EPC plant geometry

**These are not competing options; they are layers. Use all four, each at its layer:**

| Layer | Choice | Why |
|---|---|---|
| Mesh container | **glTF / GLB** | Industry runtime format; geometry lives in binary buffers (kills the ~3.7× JSON bloat you measured); native loaders in Three.js + Babylon; royalty-free (Khronos). |
| Compression | **`EXT_meshopt_compression`** (primary) | Near-instant decode (vs Draco's heavy CPU decode), GPU-friendly, good ratio. For an interactive viewer streaming many tiles, *fast decode dominates UX*. Keep **Draco** only as an option if download bandwidth ever dominates over decode time. |
| Repeated parts | **`EXT_mesh_gpu_instancing`** | Plants are full of repeats (bolts, flanges, standard sections, fittings, supports). One mesh + N transforms → huge memory + draw-call savings. First-class in the pipeline: detect repeated IFC representation/type and instance. |
| Scene / streaming / LOD | **3D-Tiles-1.1-style `tileset.json`** | glTF alone has no streaming/LOD/culling. 3D Tiles 1.1 uses **glB as tile content** wrapped in a bounding-volume tree with `geometricError`. Adopt the *manifest concept* (plant-local coords, not the Cesium globe). |
| Metadata | **`EXT_mesh_features` + Postgres `ModelObject`** | Per-vertex feature ID in the mesh → object id; rich attributes (tag, line_id, GUID) stay in Postgres/sidecar, fetched on demand. This also solves picking (Q2). **Never** put engineering metadata in the GLB. |

**Do NOT build a custom binary format.** It reinvents glTF+meshopt+3D-Tiles, throws away the loader ecosystem, and becomes a maintenance sink. Only revisit if profiling proves the standard stack is the bottleneck — it will not be at your scale.

**Conversion pipeline (Python worker):** drive glTF emission from the IfcOpenShell tessellation you already produce (verts/faces/materials per product). Practical libs (all permissive): `trimesh` (+ `pygltflib`) for GLB authoring; `meshoptimizer` (via `gltfpack` CLI or bindings) for meshopt compression + LOD simplification. `IfcConvert ... model.glb` exists as a fast path but loses per-object feature-ID control — prefer the API path so you keep object identity.

**Axis/precision gotchas (important):**
- glTF spec is **+Y up**. Your parser already does a Y/Z swap to a Z-up render frame. Decide once: emit glTF in glTF-standard Y-up and orient via the root node, *or* keep Z-up consistently — but don't bake the swap inconsistently between buffer and node.
- glTF buffers are **float32**; meshopt **quantizes** positions. So quantize *within each tile's local bbox* (uniform precision) and place the tile at its double-precision RTC origin via the node/tileset transform. Small tiles → better quantization precision. This is the format↔RTC coupling.

---

## Q2 — Object picking without duplicating geometry

**Drop the hidden pick-proxy geometry (you flagged it; it does not scale).** Two scalable strategies; I recommend the first for a Three.js/WebGL2 stack:

1. **CPU raycast over a BVH (`three-mesh-bvh`, MIT) + feature-ID lookup.** Build a BVH over the merged BufferGeometry (it's a compact *index* over existing buffers — duplicates nothing). Raycast returns a `faceIndex`; map face → object id via the per-vertex **feature-ID attribute** (`_FEATURE_ID_0`) or a baked primitive-range→objectId table. Fast even on millions of triangles. This is the pragmatic Three.js answer today.
2. **GPU ID-buffer picking** (WebGPU-era upgrade): render object ids to an offscreen integer/color target, read back the pixel under the cursor. One on-demand pass (mousedown, not per frame; scissor a small region for speed). No duplication. Best once you lean into WebGPU compute.

**Highlight without a second mesh:** use the feature-ID attribute + a shader comparing to a `selectedId` uniform (tint), or stencil. With **Three.js `BatchedMesh`** (r167+) you get many objects in one draw call *with* per-object id, visibility, and culling — this is the native answer to "merge for draw calls but keep per-object identity." Evaluate `BatchedMesh` (or `InstancedMesh` for repeats) as the runtime container; it removes the proxy problem structurally.

---

## Q3 — Is Three.js enough, or do we need the 3D Tiles ecosystem?

**Stay on Three.js — but adopt 3D-Tiles *concepts* via the MIT `3d-tiles-renderer` library.** Reframe: "3D Tiles ecosystem" = the concepts (tileset hierarchy, geometricError LOD, streaming, feature metadata), which you need regardless, plus optionally loaders.

- Raw Three.js is **not** enough for EPC scale (no streaming/LOD/tiling). But **Three.js + a few mature MIT/Apache libs is**:
  - `GLTFLoader` + `EXT_meshopt_compression`
  - **`3d-tiles-renderer`** (NASA-AMMOS / Garrett Johnson, **MIT**) — Three.js-native 3D Tiles traversal, LOD, frustum culling, cache/unload. *This is the key enabler: 3D-Tiles capability without Cesium and without AGPL.*
  - `three-mesh-bvh` (MIT), `BatchedMesh`/`InstancedMesh` (core).
- **Do not adopt CesiumJS** (geospatial/globe overhead; Apache but heavy and wrong shape for plant-local). **Do not adopt xeokit** (AGPL — runtime-incompatible with a closed commercial product without a paid license).
- **Babylon.js** remains the fallback per the freeze, but with `BatchedMesh` + `3d-tiles-renderer` + meshopt, Three.js is very likely sufficient. Keep the thin scene-boundary so a swap stays cheap.
- **WebGPU:** all of the above runs on WebGL2 today. Stay WebGL2-first, WebGPU later (consistent with the freeze). WebGPU's payoff is GPU compute (picking, culling, your future optimization math), not raster speed at this scale.

---

## Q4 — Practical tiling rules for electrical engineering

**Separate two concerns that are easy to conflate:**

1. **Spatial tiling = for streaming/LOD/culling** (performance). Needed regardless of discipline.
2. **Semantic filtering = for "show me this system/discipline/area"** (engineering queries). These are **metadata on `ModelObject`, not tiles** — toggle object visibility (BatchedMesh per-object visibility / feature-ID masks), don't reload tiles.

Why not tile by discipline/system directly? Engineering queries cross-cut ("all trays in Unit 12, EL+100–106, feeding MCC-3"). You cannot pre-tile every combination. **Spatial tiles + metadata filters compose** to answer arbitrary queries.

**Recommended scheme (start simple, designed to grow):**
- **Top partition by plant Area/Unit.** EPC plants are organized this way; it matches export boundaries and engineer mental models, and bounds coordinate ranges → clean per-area RTC origins.
- **Within an area: octree / regular grid** (start ~30–60 m horizontal cells; refine where object density is high) **+ vertical split by elevation/IfcBuildingStorey** for multi-storey structures.
- **LOD via geometricError:** distant/background structural steel → aggressively simplified proxies (meshoptimizer simplify, or bbox impostors); engineering-relevant objects (trays, cables, terminations, JBs) kept high-fidelity.
- **Instance repeated parts within tiles.**
- **Carry semantic keys on every object from day one:** `area_unit`, `system`, `discipline`, `line_id`/`tag`, `elevation_band`, `ifc_spatial_path`, and (future) `tray_zone`. These power filtering *and* the eventual hot/cold engineering link.

**Do not over-build the tile scheme now.** Start with: one `tileset.json` per source model, octree by bbox, single LOD, instancing. Add elevation split + LOD levels when a real large file demands it. The *manifest* must exist from the start so growth is data, not re-architecture.

---

## Q5 — Known-dimension validation for IFC units (closes F4)

Goal: prove geometry is truly metres, not "assumed." Layered strategy:

1. **Read IfcOpenShell's project scale:** `ifcopenshell.util.unit.calculate_unit_scale(model)` → metre scale factor of the file's length unit (e.g. 0.001 for mm). Record as `source_unit_scale_to_m`.
2. **Confirm the geometry iterator is SI:** IfcOpenShell's geometry settings return metres by default. Cross-check: compare a converted object's bbox extent against the declared-unit expectation. If geometry is already metres, do **not** re-apply the scale (the bug class is double-application). When the cross-check passes, set `unit_confidence = "verified"` (not `"assumed"`).
3. **Add a known-dimension fixture to the test suite (do this — it's cheap and deterministic):** author a tiny IFC containing a single **1 m** (or 10 m) box/wall; run it through the real conversion; assert converted bbox extent ≈ 1 m (± tol). This permanently guards against silent rescaling and closes F4 in CI, independent of any single sample file.
4. **One real-file spot check:** pick an object with a known catalogue dimension (standard beam length, nominal pipe length) in a Tekla sample; verify once by hand.

Output: F4 moves from "assumed/partially mitigated" to "verified + regression-guarded."

---

## Cross-cutting: format ↔ RTC ↔ precision are one problem

- glTF/meshopt buffers are float32 + quantized → **per-tile RTC is mandatory** once binary. Tile-local vertices, double origin at the node. This merges Q1 with the F1 per-tile-RTC remainder.
- **F3 still gates this.** The format/tiling/precision work must be validated on a genuinely **plant-global / georeferenced** file. Without one, you can build the binary pipeline but cannot prove it solved the jitter problem — same trap as before, one layer up. Sourcing that file remains the top unblock.

## On Codex's "what's next" — agree, with sequencing

Codex's plan is right. My sequencing (smallest blast radius first, each step independently valuable):

1. **GLB + meshopt + feature-IDs, single tile, no tiling yet.** This alone kills the JSON bloat *and* the FPS problem for single-area files. Ship and re-measure FPS/payload against the Tekla samples — expect a large win. *(Highest value-to-effort.)*
2. **Replace pick-proxy with `three-mesh-bvh` + feature-ID lookup.** Removes the memory-duplication strategy now, before models get big.
3. **Known-dimension fixture (Q5).** Closes F4 deterministically. Tiny effort.
4. **`tileset.json` manifest + per-tile RTC**, even primitive (octree by bbox, one LOD). Begins real EPC architecture; proves RTC on binary tiles.
5. **Validate the whole chain on a real plant-global file (F3).** The gate.
6. Defer: LOD simplification levels, instancing tuning, WebGPU, Celery/SSE, S3 backend — until 1–5 prove the shape.

**My one challenge / caution:** do not attempt GLB + meshopt + instancing + tiling + feature-IDs + BVH in a single pass. That's how the format leap stalls. Step 1 (GLB+meshopt+feature-IDs, untiled) is a complete, shippable win on its own — get that measured before adding tiling. And keep the thin scene-boundary so the renderer stays swappable.

## Licensing (all clean for a commercial web product — verify at adoption)

| Dependency | License | Verdict |
|---|---|---|
| glTF/GLB (Khronos) | royalty-free spec | ✅ |
| `3d-tiles-renderer` | MIT | ✅ |
| `three-mesh-bvh` | MIT | ✅ |
| `meshoptimizer` / `gltfpack` | MIT | ✅ |
| Draco | Apache-2.0 | ✅ (optional) |
| `trimesh` / `pygltflib` | MIT / Apache | ✅ |
| Three.js / Babylon.js | MIT / Apache-2.0 | ✅ |
| CesiumJS | Apache-2.0 | ✅ but wrong shape (globe) — concepts only |
| **xeokit / XKT** | **AGPL-3.0** | ❌ runtime — reference only or paid license |

## Open items back to Codex/KR

- **F3 (still the gate):** source one plant-global / georeferenced IFC (UTM-scale eastings or a large project base point). Everything precision-related stays unproven until then.
- Confirm the glTF axis convention decision (Y-up via node vs consistent Z-up) before emitting the first GLB.
- Decide meshopt vs Draco default (I recommend meshopt for decode speed).
- Adopt `EXT_mesh_features` feature-IDs in the *first* GLB pass — retrofitting IDs later is as painful as retrofitting RTC was.
