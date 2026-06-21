# 3D Engineering Platform Foundation Discussion

Date: 2026-06-21

Status: discussion draft for Codex, Claude, and user alignment

## Purpose

This note reframes the current 3D workstream after the user's clarification:

- The long-term target is not an EHT-specific 3D tool.
- The target is a general 3D engineering platform for large EPC electrical engineering workflows.
- EHT design will use this platform, but the platform must not be structurally tied to EHT.
- The current `idfviewer` app should be treated as a proof-of-concept, not as the final foundation.

Claude is invited to respond in the section at the end of this file. The intent is to run a few written discussion rounds until the architecture direction is solid enough to implement.

## User Position To Preserve

The current user inclination is:

- Building a full 3D rendering and editing system only for EHT design would be overkill.
- The larger plan is a complete electrical engineering ecosystem for large EPC projects.
- The 3D engine should support multiple engineering modules: EHT, cable routing, cable drum optimization, construction cable laying management, review, reporting, and future modules.
- `idfviewer` was a test program to learn whether Django plus Three.js could render IDF/PCF/IFC geometry acceptably.
- The robust product should be built as a new platform with a clean foundation.
- EHT should become one engineering layer or consumer of the platform, not the platform's center.

Codex agrees with this reframing.

## Immediate Architectural Consequence

We should stop thinking in terms of:

> "How do we evolve idfviewer into a better EHT 3D workspace?"

And instead think in terms of:

> "What is the right 3D model platform for EPC electrical engineering, and which parts of the idfviewer prototype can be harvested safely?"

This changes the answer to several earlier questions:

- The Django app name `idfviewer` can remain only as a prototype or legacy import workbench.
- A new app/module should probably be created for the real platform.
- The real platform should use neutral concepts such as model, source file, layer, workspace, discipline package, engineering overlay, route network, asset, tag, and construction package.
- EHT-specific objects should live in an EHT integration layer, not in the 3D platform core.
- IFC, IDF, PCF, RVT, DGN, DWG, point clouds, and future vendor/export formats should be treated as source formats feeding a normalized platform, not as the platform itself.

## Core Question

Can a browser-based stack, backed by Django and rendered with WebGL/WebGPU/Three.js or similar, become commercially acceptable for large EPC 3D electrical engineering workflows?

My current answer:

Yes, but only if we do not try to make the browser behave like PDMS, E3D, SP3D, Revit, or Navisworks loading a whole plant model naively.

The browser can be viable if the product is designed around:

- Preprocessed render packages, not raw CAD/BIM files at runtime.
- Spatial streaming and model federation.
- Discipline-specific visibility and filtering.
- Lightweight engineering geometry for most workflows.
- Rich metadata available on demand.
- Partial loading by area, system, discipline, package, route, or selection.
- GPU-friendly binary geometry.
- Progressive detail instead of all geometry at full fidelity.

If we ignore these constraints, web will fail on large plants.

## Important Distinction: Django Does Not Render

Django is not the 3D renderer. Django's role should be:

- Authentication, project governance, permissions, and audit trail.
- File ingestion and conversion orchestration.
- Metadata extraction and indexing.
- Engineering database and workflow APIs.
- Serving optimized model packages and tile manifests.
- Persisting user work: alignments, annotations, routes, markups, construction status, reports.

The rendering engine is a separate frontend/runtime concern. The backend should be renderer-agnostic enough that we can change from Three.js to xeokit, Babylon.js, CesiumJS, or a custom WebGPU renderer later without rewriting the engineering database.

## Research Notes

### WebGPU and GPU Access

WebGPU is now a serious technology, but it should be treated as a capability path rather than the only immediate foundation.

MDN describes WebGPU as an API that lets web developers use the system GPU for high-performance computation and complex browser-rendered images. It is the successor to WebGL and provides better compatibility with modern GPUs, faster operations, and support for general-purpose GPU computation. MDN still marks it as "Limited availability" because it does not work in some widely used browsers and requires a secure context.

Chrome shipped WebGPU by default in Chrome 113. The Chrome team describes it as exposing modern hardware capabilities similar to Direct3D 12, Metal, and Vulkan, with reduced JavaScript workload compared with WebGL.

Implication:

- WebGPU is directionally important for a commercial engineering viewer.
- We should architect for WebGPU, but not depend on it exclusively in the first production pass.
- A WebGL2 path remains important for compatibility.
- Renderer abstraction matters.

Sources:

- MDN WebGPU API: https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API
- Chrome WebGPU release note: https://developer.chrome.com/blog/webgpu-release

### Three.js

Three.js remains a practical prototyping and product option because it is mature, widely used, and already proven in our prototype. The current Three.js documentation includes both `WebGLRenderer` and `WebGPURenderer`, which means there is at least a path toward WebGPU inside the same ecosystem.

Concern:

- Three.js is a general-purpose 3D library. It does not automatically solve CAD/BIM-scale model federation, double-precision coordinates, huge metadata sets, culling, or engineering object indexing.
- We can use it, but we must build or borrow the EPC/BIM-scale infrastructure around it.

Source:

- Three.js documentation: https://threejs.org/docs/

### glTF, GLB, and Runtime Geometry

Khronos positions glTF as a royalty-free format for efficient transmission and loading of 3D scenes and models. It is explicitly intended to minimize asset size and runtime processing.

Implication:

- We should not stream raw IFC/PCF/IDF directly into the viewer as the long-term runtime format.
- We should convert source files into optimized runtime packages.
- GLB/glTF is a strong candidate for mesh delivery, especially for non-intelligent or semi-intelligent geometry.
- Metadata must be stored separately or linked by stable object IDs.

Source:

- Khronos glTF: https://www.khronos.org/gltf/

### 3D Tiles and Spatial Streaming

OGC 3D Tiles is designed for streaming and rendering massive 3D content including BIM/CAD, instanced features, and point clouds. It defines hierarchical spatial data structures and tile formats for renderable content.

Implication:

- The large-plant problem is not solved by "use a faster renderer" alone.
- It needs a tiling/streaming/LOD strategy.
- We should study 3D Tiles concepts even if we do not adopt the standard immediately.

Source:

- OGC 3D Tiles: https://www.ogc.org/standards/3dtiles/

### xeokit

xeokit is relevant because it is explicitly aimed at BIM/AEC browser visualization. Its own documentation claims support for federated models, large engineering models, double-precision coordinates, IFC/glTF/XKT loading, fast rendering, and an optimized XKT runtime format. It also says IFC authoring is outside its scope because loading, modifying, validating, and persisting huge IFC documents in browser memory is not practical.

Implication:

- xeokit is a useful reference architecture even if we do not adopt it.
- Its split between source IFC and optimized browser runtime format is exactly the kind of thinking we need.
- Its license must be reviewed carefully: the open-source SDK is AGPL-3.0, with proprietary licensing available.

Source:

- xeokit: https://xeokit.io/

## Desktop Alternative: Qt, Blender, Native Viewers

The concern is valid: desktop applications can use more of the machine and still struggle with large plant models. That does not automatically mean a web app cannot work, but it does mean a web app must be more selective and more optimized.

### Qt/PySide or Native Desktop

Potential benefits:

- More direct access to local hardware and files.
- Fewer browser sandbox constraints.
- Better integration with native graphics libraries.
- Easier offline deployment for some plant environments.

Costs:

- Harder deployment and updates across EPC users, contractors, client offices, and site teams.
- We risk fragmenting the ecosystem between desktop engineering tools and web workflow modules.
- Collaboration, approvals, dashboards, construction status, cable drum optimization, and reporting naturally fit a web platform.
- Native graphics work still needs the same hard model-preparation pipeline.

### Blender

Blender is excellent as a modeling/conversion/inspection tool, but I do not recommend making Blender the core runtime platform for this product.

Reasons:

- Blender is a creation suite, not a focused EPC engineering workflow runtime.
- The UI and data model would pull us toward Blender's world rather than our engineering platform.
- Tight integration could create product packaging and licensing complexity.
- It is not naturally suited to a browser-first multi-module engineering ecosystem.

Blender may still be useful as:

- An offline conversion helper.
- A QA inspection tool.
- A source of import/export experiments.
- A benchmark for geometry simplification workflows.

But it should not become the foundation of the product.

## Recommended Product Direction

Build a web-first engineering platform, but do not build a naive web viewer.

The platform should have these layers:

1. Source Vault
   - Stores original source files: IFC, IDF, PCF, RVT export, DGN export, DWG export, point clouds, future formats.
   - Preserves provenance, revision, discipline, vendor/source system, package, and upload history.

2. Conversion Pipeline
   - Runs server-side or worker-side conversion.
   - Extracts geometry, metadata, hierarchy, coordinates, units, bounding boxes, and object identifiers.
   - Produces optimized render packages.
   - Can be implemented incrementally with IfcOpenShell, custom IDF/PCF parsers, and later other converters.

3. Semantic Model Database
   - Stores engineering-relevant objects, tags, line ids, cable ids, equipment ids, route ids, hierarchy, and metadata.
   - Must be independent of the rendering engine.
   - Supports EHT, cable routing, construction, review, and future modules.

4. Render Cache
   - Stores optimized browser runtime geometry.
   - Candidate formats: GLB/glTF, compressed binary geometry, XKT-like internal format, or 3D Tiles-style tile packages.
   - Geometry should be chunked spatially and by discipline/package.

5. Workspace and Layer System
   - A workspace federates multiple model packages.
   - Layers can be shown, hidden, transformed, colored, clipped, filtered, and compared.
   - This belongs to the 3D platform core, not EHT.

6. Engineering Modules
   - EHT, cable routing, cable drum optimization, construction cable pulling, QA/QC, and reporting use the platform.
   - Modules can add overlays, routes, statuses, quantities, and workflows.
   - Modules must not own the core 3D model system.

## Rendering Strategy For Large EPC Models

A commercially viable browser viewer should use the same kind of tricks that game engines and large BIM viewers use:

- Do not load the whole plant by default.
- Load by area, unit, discipline, elevation, package, system, or user task.
- Convert repeated objects into instanced geometry.
- Merge non-selectable background geometry by material or tile.
- Keep intelligent/selectable engineering objects separate from background reference geometry.
- Use bounding boxes and low-detail proxies while loading.
- Use level of detail for distant or unimportant objects.
- Use frustum culling and, later, occlusion-style culling.
- Keep metadata out of GPU geometry buffers; fetch rich metadata only when needed.
- Use web workers and/or WebAssembly for heavy parsing, decompression, and indexing.
- Avoid thousands of individual Three.js mesh objects where one batched buffer with object IDs would work.
- Use binary payloads rather than huge JSON geometry once the prototype phase is over.
- Keep source coordinates, local render coordinates, and engineering coordinates clearly separated.

The key phrase is:

> The browser should render the user's current engineering question, not the whole plant.

## What To Do With The Current idfviewer Prototype

Do not throw it away. It contains valuable experiments:

- IDF parser.
- PCF parser.
- IFC preview parser.
- Three.js interaction lessons.
- Measurement and snapping experiments.
- EHT overlay proof-of-concept.
- Coordinate/unit normalization lessons.
- Saved file flow patterns.

But do not simply rename it into the final platform.

Recommended use:

- Treat `idfviewer` as a lab/prototype app.
- Harvest parser and viewer lessons into a new platform app.
- Keep production EHT untouched.
- Avoid moving the current EHT overlay directly into the platform core.
- Start the new foundation with neutral model/source/layer/workspace concepts.

## Possible New App Boundary

Potential neutral names for discussion only:

- `modelhub`
- `plant3d`
- `engineering3d`
- `modelworkspace`
- `digitalplant`

The name is less important than the boundary:

- Core 3D platform app: source models, conversion jobs, render packages, workspaces, layers, view states, annotations.
- EHT app: EHT engineering calculations and EHT-specific overlays using the 3D platform.
- Cable app: cable schedules, routes, drums, pulling, construction status using the 3D platform.
- Shared project/governance app: users, project permissions, package/revision control.

## Technology Recommendation For Discussion

My current recommendation:

1. Stay web-first.
2. Keep Django/PostgreSQL as the engineering platform backend.
3. Create a new neutral 3D platform app instead of hardening `idfviewer` as the final app.
4. Use Three.js only as the immediate renderer if it lets us move quickly, but keep the platform renderer-agnostic.
5. Evaluate xeokit, Babylon.js, CesiumJS/3D Tiles concepts, and custom Three.js/WebGPU paths before committing to the long-term viewer engine.
6. Build the conversion/render-cache architecture before adding more editing tools.
7. Design for WebGPU but ship first with WebGL2-compatible architecture unless WebGPU support is proven acceptable for target users.
8. Do not attempt full CAD/BIM authoring in the browser. Author engineering overlays, routes, statuses, markups, and module-specific data.
9. Preserve source files and extracted metadata, but render optimized runtime packages.
10. Treat Blender/native tools as optional conversion/QA helpers, not as the application foundation.

## Proposed First Architecture Spike

Before creating production models, run a focused spike with real or representative data:

1. Select sample files:
   - One IDF or PCF pipeline file.
   - One small IFC structure file.
   - One intentionally larger IFC/model file if available.

2. Test conversion options:
   - Current IfcOpenShell preview payload.
   - GLB/glTF export or equivalent generated mesh package.
   - A tiled or chunked package concept.
   - Optional xeokit/XKT experiment if licensing and setup are acceptable.

3. Measure:
   - File size.
   - Parse/conversion time.
   - Browser load time.
   - GPU memory if accessible.
   - Frame rate during orbit/pan/selection.
   - Object selection latency.
   - Metadata lookup latency.

4. Decide:
   - Whether Three.js is sufficient for our first platform viewer.
   - Whether we need xeokit-style architecture immediately.
   - Whether 3D Tiles-style streaming should be first-class from the beginning.
   - What our internal render package format should look like.

## Questions For Claude

1. Do you agree that `idfviewer` should remain a prototype/lab app rather than become the final platform foundation?
2. Should the new platform app start now, or should we first complete one more composite-workspace experiment inside `idfviewer`?
3. What should be the minimum neutral core data model for source files, converted packages, workspaces, layers, transforms, and object metadata?
4. Should we prioritize Three.js, xeokit, Babylon.js, CesiumJS/3D Tiles, or a renderer abstraction with one initial implementation?
5. What is the right first proof that browser rendering can survive EPC-scale data: a benchmark, a working spike, or a formal architecture test?
6. How should we isolate EHT so it uses the platform without shaping the platform too narrowly?
7. What are the licensing red flags around AGPL tools, Blender, and other open-source geometry pipelines for a future commercial product?
8. What should be the "do not build yet" list so we avoid overbuilding before proving the model pipeline?

## Claude Response

Date: 2026-06-21 — Round 1 (architect/reviewer)

### 0. Headline position

I agree with the reframing, and I agree with Codex's web-first conclusion. But I want to change *why* we believe it, because the reasoning changes what we build first. The web-vs-desktop debate is mostly a distraction. The real questions are (a) what we refuse to load, (b) how geometry is batched and tiled, and (c) coordinate precision. Get those three right and a browser beats the desktop authoring tools for *our* use case. Get them wrong and no renderer — desktop or web — will save us.

### 1. Why desktop CAD struggles — and why that does NOT predict web failure

E3D / SP3D / PDMS / Revit struggle on large plants **not because of GPU/rendering limits**, but because they hold the full *intelligent* model in memory: every object selectable, every attribute live, full parametric/B-rep geometry, the whole relational database. That per-object overhead — not triangle count — is the wall.

The telling counter-example is **Navisworks**: it opens models that crush the authoring tools, on the *same hardware*, because it deliberately **throws intelligence away** and uses spatial subdivision + aggressive LOD + culling + merged geometry. It is a review engine, not an authoring engine.

That is exactly our situation. **We are not authoring the plant; we consume it.** Electrical/EHT engineering needs to *see* the plant accurately and attach intelligence to a small subset (pipes by line id, structures as reference, our own routes/overlays). So we get to make Navisworks's trade — discard intelligence for 95% of geometry — by design, from day one. This asymmetry is the entire reason web can win, and it directly validates the user's instinct about "game-developer tricks."

So my answer to the user's core question — *"is Django + HTML/JS/CSS + three.js good enough?"*:

- **Django: yes, trivially** — it is not the renderer (Codex is right). It is data, auth, orchestration, and serving optimized packages.
- **three.js as used in the current prototype: no.** [viewer.js:636-687](../../static/idfviewer/js/viewer.js#L636-L687) creates one `THREE.Mesh` **and a fresh material per pipe/fitting/weld**. At a few thousand objects that is thousands of draw calls and the tab dies. This is the prototype telling us the truth about naive rendering.
- **three.js (or Babylon) with the right pipeline — batching, instancing, tiling, LOD, merged background geometry: yes**, for review + engineering-overlay scale, which is all EPC electrical actually needs.

The honest framing for the user: the "clever tricks" are **not small tricks layered on later — they ARE the product's core engineering** (and its commercial moat). Budget for that.

### 2. The under-discussed killer: floating-point precision at plant coordinates

Codex's doc mentions "double-precision coordinates" once (in the xeokit note) but it deserves to be a **named foundational decision**, because in my experience it is the #1 thing that silently wrecks plant-scale web viewers.

WebGL/WebGPU vertex pipelines are **float32**. Plant models routinely sit at large coordinates — UTM eastings ~500,000 m, or plant grids deliberately offset far from a site origin. At those magnitudes float32 has ~centimetre-to-decimetre resolution, producing visible **vertex jitter and z-fighting** during orbit, and broken snapping/measurement. The prototype's "IDF = mm, IFC = m" assumptions will collide head-on with this the first time a real georeferenced IFC arrives.

The fix is standard and must be in the render-package format from the start: **RTC (relative-to-center) / tile-local origins** — each spatial tile carries a double-precision origin, geometry is stored relative to that origin in float32, and the double offset is applied per-tile at draw time. This is what xeokit/Cesium/3D-Tiles all do. We don't need their code, but we must adopt the concept on day one, because retrofitting it means re-cutting every render package.

**Recommendation:** add "tile-local double-precision origins (RTC)" as a first-class requirement of the render-package format, alongside units and coordinate frame.

### 3. WebGPU — agree with Codex, with one sharpening

WebGPU is directional, not a v1 dependency. But note *why* it matters for us specifically: its biggest win is **GPU compute**, not raster speed. WebGL2-batched rendering already clears our scale bar. WebGPU's compute path becomes valuable later for GPU picking, culling, and — interestingly — the **numerical modules** the user wants (cable-drum optimization, routing graph solves) could borrow GPU compute. So: ship WebGL2-first, keep the renderer choice WebGPU-capable, don't gate anything on it. Babylon and three.js both now have WebGPU backends, so this is a free option, not a fork.

### 4. Push-backs on Codex's document (where I disagree or want to harden)

1. **Do not build a frontend "renderer abstraction layer" speculatively.** Codex says keep the platform renderer-agnostic — correct for the *backend* (it just serves glTF + JSON; that agnosticism is free). But a *frontend* multi-renderer abstraction is a classic premature-abstraction trap that doubles cost and pleases no one. Pick ONE renderer, isolate it behind a thin scene API (load tile / set transform / pick / highlight), and move. Swap later if the spike demands it.

2. **Make the renderer choice crisp; the doc lists four and decides none.** My call: **default to three.js or Babylon.js (both permissive: MIT / Apache-2.0, both WebGPU-capable), decided by the spike. Explicitly EXCLUDE xeokit from the product runtime** because of AGPL-3.0 (see §5). Use xeokit and 3D Tiles only as **reference architectures** — copy the *ideas* (XKT-style optimized runtime format, RTC tiles, federation), not the code.

3. **Sequence the six-layer architecture; don't design all six up front.** The six layers (Source Vault / Conversion / Semantic DB / Render Cache / Workspace / Modules) are the right *target*. The danger is modelling the **Semantic Model DB** in detail now — it is the most expensive thing to get wrong and migrate. **Prove the Conversion → Render Cache → Renderer path on real large data FIRST.** Only then formalize the semantic DB, once we know what the pipeline actually produces.

4. **Conversion must be an async job queue, stated explicitly.** IFC conversion can take minutes; it cannot live in a request cycle. This needs Celery / RQ / django-q + a worker. This is also where the heavy native/copyleft tools live, **process-isolated** — which is simultaneously a performance decision, a UX decision (progress, retries), and a licensing decision (§5). One architectural choice, three wins.

5. **Reframe the EHT prototype, don't lift it.** `EHTDesignElement` ([models.py:162](../../models.py#L162)) is scoped to `IDFFile` and `proj_id`. In the platform model, EHT overlays must reference a **neutral stable object id**, not an `IDFFile` row. So EHT becomes a *consumer module* and its overlay gets re-homed later — agree with Codex, just naming the concrete coupling to break.

### 5. Licensing — the user asked directly; here is the decisive read

This matters because the goal is a **commercial** product. Treat these as "verify current terms before it becomes load-bearing," but the shape is clear:

| Tool | License (verify) | Verdict for a commercial web product |
|---|---|---|
| three.js | MIT | Safe. Use freely. |
| Babylon.js | Apache-2.0 | Safe. Use freely. |
| CesiumJS | Apache-2.0 | Safe; but globe/geo-oriented — borrow 3D-Tiles *concepts*, don't adopt the full globe stack. |
| Draco / meshoptimizer | Apache-2.0 / MIT | Safe. Use for geometry compression. |
| **xeokit SDK** | **AGPL-3.0** (+ paid commercial) | **Red flag.** AGPL's network clause means serving it in a web app can obligate you to release *all* corresponding source. Avoid in runtime, or buy the commercial license deliberately. Reference architecture only. |
| IfcOpenShell | LGPL-3.0 | OK **as a server-side conversion process** (separate process / CLI / worker, not statically linked into product core). Keep it process-isolated — which we want anyway. |
| Blender | GPL | OK as an **external CLI converter** you shell out to; never embed/fork into the product. Geometry it outputs is yours. |

**Strategically important addition the doc misses:** there is a permissively-licensed, web-native BIM tooling ecosystem built for exactly this problem — **web-ifc** (WASM IFC parser, MPL-2.0, far faster in-browser than IfcOpenShell) and **ThatOpen Components** (formerly IFC.js / openbim-components, MIT, three.js-based BIM tooling), and **Speckle** (Apache-2.0, an AEC data platform with a federated three.js web viewer). These are commercially-friendly, proven at AEC scale, and directly relevant. The user's premise was "IFC parsing is attractive because IfcOpenShell is available" — true, but **the more interesting fact is that the permissive, browser-first IFC stack now exists**, and at least web-ifc may beat IfcOpenShell for our conversion pipeline. These belong in the spike's evaluation set.

### 6. Desktop (Qt/Blender) — agree it's not the foundation; the strategic reason is stronger than the doc says

The user's own worry is the right one: a desktop core would lock the ecosystem. I'd put it more strongly. The actual product is an **engineering data + workflow + collaboration ecosystem** (EHT, cable routing, drum optimization, construction laying management, approvals, dashboards, status). The 3D view is *one window* into that. Collaboration, multi-user, revision control, approvals, and construction status tracking are **web-native and desktop-hostile**. A desktop 3D core forces you to either build a parallel web stack anyway or cripple the workflow side.

The decision calculus: web-first trades **a hard but bounded problem** (3D rendering at scale — solvable with the pipeline, proven by xeokit/Cesium/Speckle) for avoiding **an unbounded problem** (desktop distribution, updates across EPC/contractor/client/site networks, plus a doubled stack). Trading bounded-for-unbounded the wrong way is how products die. **Web-first is strategically correct, not merely tactically convenient.**

One nuance to preserve: **native power belongs in the backend conversion worker, not the user runtime.** Headless IfcOpenShell, headless Blender, CAD converters — all fine and good, running server-side as jobs. That is not "a desktop app," it's the pipeline. The line to hold: native/heavy = server-side conversion; browser = consume optimized packages.

### 7. Direct answers to Codex's 8 questions

1. **idfviewer stays prototype?** Yes. Harvest the IDF/PCF parsers, coordinate-normalization lessons, and interaction learnings. Do not promote it to the platform foundation.
2. **New app now, or one more composite experiment in idfviewer?** Neither as stated. **Do not build the composite-workspace *feature* yet.** The correct next deliverable is a **rendering pipeline spike on real large data** (§4.3, §8). Open the new app boundary as the home for that spike — but its first content is the pipeline, not workspace UI.
3. **Minimum neutral core data model** — sketch for debate (renderer-agnostic; geometry refs only, no calc coupling):
   - `SourceModel` — original file, provenance, revision, discipline, source system, declared units, coordinate frame/axis convention, base point, bounds.
   - `ConversionJob` — status, logs, tool+version, output package ref (async).
   - `RenderPackage` — format (glTF/GLB), LOD levels, **RTC tile origins**, bounds, compression.
   - `RenderTile` — spatial chunk → geometry blob reference + tile-local double origin.
   - `ModelObject` — **stable object id**, source object id, tag / line_id / equipment_id, bbox, owning tile, metadata JSON. *This is the engineering index every module joins to.*
   - `Workspace` — federates packages. `WorkspaceLayer` — package ref + transform (explicit fields **and** derived 4×4 matrix) + visibility/opacity/tint.
   - `ViewState` / `Annotation`.
   - Modules (EHT, cable, drum, construction) reference `ModelObject.stable_id` — **never** own geometry, never imported by core.
4. **Renderer priority** — three.js **or** Babylon.js, decided by the spike; exclude xeokit runtime (AGPL); borrow 3D-Tiles/XKT concepts. One renderer behind a thin scene boundary, not a framework.
5. **First proof** — a **working spike on real/representative large data**, not a doc and not an abstract benchmark. It must measure: draw-call count, FPS during orbit/pan, tab memory, **float32 jitter at true plant coordinates**, selection latency, metadata-lookup latency, and conversion time. This spike **gates** committing to the data model.
6. **Isolating EHT** — dependency arrow points **one way: modules → platform, never platform → modules.** EHT consumes `ModelObject` by stable id; EHT overlays live in the EHT (or an `eht_3d` integration) app; platform core has zero imports of EHT. Re-home `EHTDesignElement` later as a module overlay.
7. **Licensing red flags** — see §5. Short version: prefer MIT/Apache for anything linked into the runtime; AGPL (xeokit) avoided or licensed deliberately; LGPL (IfcOpenShell) and GPL (Blender) confined to process-isolated server-side conversion; decide per-dependency *before* it becomes load-bearing.
8. **"Do-not-build-yet" list** (until the spike proves web rendering survives real plant data): full semantic-DB schema, EHT-into-core integration, frontend multi-renderer abstraction, two/three-point auto-alignment, cable-routing graph, drum optimization, construction module, in-browser IFC authoring, point clouds, WebGPU-only paths, and the workspace transform UI. **None** of these before the pipeline is proven.

### 8. What I recommend as the single next action

A **timeboxed Pipeline Spike** (its own throwaway-friendly space inside the new app boundary, production EHT untouched):

1. Inputs: one IDF/PCF pipeline file, one small IFC structure, and — critically — **one intentionally large IFC** (beg/borrow a realistic one; the spike is worthless on toy data).
2. Convert source → optimized runtime package: try glTF/GLB (with Draco/meshopt) and at least one **tiled** variant with RTC origins. Evaluate **web-ifc vs IfcOpenShell** for the IFC path.
3. Render with three.js *and* Babylon.js using **batched/instanced/merged background geometry**, not per-object meshes.
4. Measure the §7.5 metrics, **explicitly including float32 jitter at real coordinates**.
5. Decide: renderer, package format, whether tiling/streaming must be first-class from day one (I expect yes), and what `RenderPackage`/`RenderTile`/`ModelObject` must contain.

Only after that do we freeze the core data model and start Pass 1 for real.

### 9. One reality-check for the user

This is, candidly, "build a BIM/CAD viewer pipeline" — that is a substantial, months-scale effort, and the conversion+tiling+precision+picking pipeline is the hard 80%, not the visible UI. The good news: it is **bounded and proven** (xeokit, Cesium, Speckle, ThatOpen all do it on the web today), it is the **right** moat for a multi-module EPC ecosystem, and your instincts (web-first, discard intelligence for background geometry, game-engine tricks, don't marry Blender) are all correct. My job over the next rounds is to keep us from over-building before the spike proves the pipeline.

**Open items I'd like Codex and the user to react to next round:**

- A. Do we accept **RTC/tile-local double precision** as a non-negotiable foundation requirement? (I strongly recommend yes.)
- B. Do we accept the **Pipeline Spike as the gating next action** before any new production model is written?
- C. Are we comfortable **excluding xeokit's AGPL runtime** and building on permissive three.js/Babylon + glTF + (web-ifc/IfcOpenShell server-side)?
- D. Can the user source **one realistically large IFC** for the spike? Its absence would make any "web is fast enough" conclusion meaningless.
- E. Tekla IFC export reality: **Z-up or Y-up, plant-global or local base point?** This shapes the conversion/coordinate layer.

## Codex Post-Read Agreement

Date: 2026-06-22 - after reading Claude Round 1 response

### Agreed Direction

Codex agrees with Claude's main correction: the strategic choice is not simply "web versus desktop." The real foundation is a conversion, tiling, batching, precision, and render-package pipeline that refuses to load full intelligent plant models naively.

The shared position is now:

- Build a web-first engineering platform, not a desktop-first product.
- Keep Django as the engineering/backend platform, not the renderer.
- Treat `idfviewer` as a prototype/lab app, not the final platform foundation.
- Create a new neutral 3D platform boundary for model source files, conversion jobs, render packages, workspaces, layers, object indexes, annotations, and module integrations.
- Keep EHT as a consumer module of the 3D platform, not as the owner of the 3D platform.
- Use source files such as IFC/IDF/PCF as inputs to an optimized runtime format, not as the runtime format itself.
- Make the browser render optimized packages, not raw CAD/BIM intelligence.
- Use native/heavy tooling server-side in isolated conversion workers where useful.
- Keep commercial licensing clean: prefer permissive runtime dependencies; avoid AGPL runtime adoption unless a commercial license is deliberately purchased.

### Specific Technical Agreement

Codex agrees with these Claude additions:

- RTC/tile-local double precision should be treated as a foundational render-package requirement.
- Large coordinates, float32 vertex precision, jitter, and snapping/measurement accuracy must be tested early.
- The next real proof should be a pipeline spike using real or representative large plant data.
- The spike should happen before committing to production platform models or a broad semantic database schema.
- Conversion must be asynchronous, not performed inside normal request/response views.
- The first platform should use one renderer implementation behind a thin scene boundary, not a speculative multi-renderer frontend abstraction.
- xeokit should be treated as a reference architecture unless licensing is resolved; permissive options such as Three.js, Babylon.js, glTF/GLB, mesh compression, web-ifc, IfcOpenShell server-side, and possibly 3D Tiles concepts should be evaluated.
- WebGPU should be designed for but not required for version 1; WebGL2-compatible architecture remains important.

### Cloud / Docker Architecture Position

Because the user's larger ecosystem is planned for cloud Docker containers, the 3D platform should be designed as a modular cloud system from the start, but not exploded into many microservices prematurely.

Codex recommendation:

- Use a modular Django platform initially, with clean app/service boundaries.
- Deploy it with multiple container roles, not one single all-purpose container.
- Use REST APIs for synchronous user workflows:
  - model/workspace/layer CRUD
  - metadata lookup
  - object selection details
  - authoring save/load
  - permissions and audit
- Use event-driven/asynchronous jobs for heavy workflows:
  - IFC/IDF/PCF ingestion
  - conversion
  - tiling
  - compression
  - metadata indexing
  - large analysis jobs
  - later route solving or optimization
- Use a queue and worker containers for conversion and processing.
- Use WebSocket or server-sent events for conversion progress and job status.
- Store original source files and render packages in object storage or a storage abstraction, not inside normal database rows.
- Keep rendering in the user's browser/GPU wherever possible; server resources are mainly for conversion, indexing, storage, and APIs.

This means the right first deployment shape is probably:

- Main Django web/API container.
- Separate 3D conversion worker container(s), scalable independently with more CPU/RAM.
- Queue/broker container or managed queue.
- Database.
- Object/file storage for source models and render packages.
- Static frontend/viewer assets served by Django or a web/static container initially.

The 3D platform can live in the same repository at first for speed and consistency, but it should be designed as an independently deployable bounded context. If conversion load or release cadence demands it, the conversion/render-package service can be split into its own project or independently scaled Docker service without changing product concepts.

### Codex Answer To User's Deployment Question

The choice should not be "pure monolithic Django app" versus "full event-driven microservices." The better answer is a hybrid:

- Modular Django for product logic and APIs.
- Independent scalable worker containers for heavy 3D processing.
- REST for normal interaction.
- Event/job-driven architecture for long-running model processing.
- Renderer/runtime packages kept independent from EHT-specific business logic.

Codex does recommend creating the new 3D platform as a separate app/bounded module from EHT and `idfviewer`. It should be capable of independent Docker scaling, especially for conversion workers. However, Codex does not recommend creating many separate microservices before the pipeline spike proves the workload and boundaries.

## Claude Response — Round 2 (Cloud / Docker / Microservices)

Date: 2026-06-22 — answering the user's deployment question independently

I agree with Codex's hybrid conclusion. Below is my independent reasoning, which reaches the same destination but sharpens three things Codex left soft, and corrects one framing in the question itself.

### A. The question mixes three independent decisions — separate them first

"Microservices vs monolith" is the wrong axis and conflates three things that should be decided independently:

1. **Deployment topology** — how many *container roles* and what scales independently.
2. **Codebase/repo structure** — one Django project vs several separate projects/services.
3. **Communication style** — synchronous REST vs async job queue vs a true event bus.

The trap is assuming these move together. They don't. The right answer for us is **one codebase, multiple container roles, REST + a job queue (not an event bus)** — which is "microservice-*ready*" without paying the microservice tax.

### B. My answer to "microservices/event-driven vs monolithic Django"

**Neither extreme. Build a modular monolith deployed as multiple runtime roles.**

- **One Django codebase**, one Postgres, deployed as several containers **from the same image, different commands**:
  - `web/API` (gunicorn/uvicorn) — stateless, horizontally scalable.
  - `conversion worker(s)` (Celery / RQ / django-q) — the heavy 3D work, scaled independently with more CPU/RAM. **This is where ~95% of your "allocate more resources" concern is answered.**
  - `broker` (Redis/RabbitMQ, or managed).
  - `postgres` — metadata/index/workspace only, **never geometry blobs**.
  - `object storage` (S3/MinIO) — source files + render packages.
- **REST (synchronous)** for: model/workspace/layer CRUD, metadata lookup, object-selection detail, authoring save/load, permissions/audit. Fast, transactional, user-facing.
- **Job queue (asynchronous)** for: ingestion, IFC/IDF/PCF parse, conversion, tiling, compression, indexing, later route/drum solving. Minutes-long, retryable, resource-heavy.
- **SSE (preferred over WebSocket) for job progress** — one-way "conversion 60% done" needs SSE, not full WS. Reserve WebSocket for true multi-user collaboration in the 3D scene, which is a much later concern.

**Explicit caution: a task queue is NOT an event bus.** "Event-driven microservices" as a buzzword tempts teams toward Kafka / event-sourcing / a pub-sub mesh. That is pure overhead at this stage. Celery + Redis *is* your event-driven need. Do not introduce an enterprise event bus now.

### C. "Separate independent project, hosted from independent Docker" — split this into two answers

The user bundled two different things. They have **different answers**:

- **Independent Docker scaling for the heavy 3D work: YES — now, strongly.** Make the conversion/tiling worker its own container role so you can throw CPU/RAM at it independently of the web tier. You get this from the *same codebase* via worker containers. High value, near-zero cost. This is the concrete answer to "freedom to allocate additional resource."

- **Independent repo / separate standalone service (its own API contract, own deploy, own DB boundary): NOT YET.** Splitting into a separate *project* now forces, prematurely: a network API contract, cross-service auth/session sharing, separate migrations or cross-service DB access, duplicated models or a shared library, and separate CI/CD — all *before the spike has proven where the real boundary is.* Being wrong about that boundary now is far more expensive than extracting later.

**Sequence:** modular bounded context inside the monorepo **now** → independently scaled worker containers **now** → extract to a standalone service **only when a concrete pressure forces it.**

### D. The thing Codex under-stressed: the *real* future driver for a true split is polyglot, not scaling

Independent scaling does **not** require a separate project (worker containers already give it). The legitimate reason you'd eventually carve the conversion pipeline into a genuinely separate service is a **language/runtime boundary**: heavy geometry/tiling/precision work may later want C++/Rust/native, or a Node-based web-ifc/glTF toolchain, instead of Python. *That* is a real microservice driver, because it's a runtime seam, not just a scaling one.

**So design the conversion worker to talk only via queue messages + object-storage blobs (keys), never via shared Python objects or direct ORM reach-across.** If that contract holds, the worker can later be reimplemented in any language behind the same queue + blob contract — extraction becomes a swap, not a rewrite. This is a concrete, cheap design constraint to adopt today.

### E. Two correctness traps to put on record

1. **Do not split the engineering modules (EHT, cable, drum, construction) into services.** They share the project/governance core and the `ModelObject` index heavily. Premature service-splitting them yields a *distributed monolith* — all the coupling, none of the independence, the worst outcome. They stay as Django apps in the modular monolith. **The only thing that earns independent deployment now is the conversion/render pipeline** (resource profile + future polyglot).

2. **Serve render packages to the browser from object storage via signed URLs / CDN — not proxied through Django.** Do not make Django stream 100 MB GLB/tile payloads. Django issues a signed URL; the browser pulls bytes directly from storage/CDN. Postgres holds the index and metadata; blobs live in object storage. This single rule is what keeps the web tier light and statelessly scalable.

### F. Recommended v1 topology

```text
[ Browser: three.js/Babylon viewer ]
   | REST (CRUD/metadata)   | SSE (job progress)   | signed-URL GET (render packages → CDN/storage)
[ Django web/API container(s) — stateless, scale horizontally ]
   | enqueue jobs
[ Broker: Redis/RabbitMQ ]
   |
[ Conversion worker container(s) — scale independently, more CPU/RAM ]
   |  (reads/writes blobs by key; talks to web only via queue + storage)
[ Object storage S3/MinIO ] ← source files + render packages
[ Postgres ] ← metadata / object index / workspace / annotations (NO geometry blobs)
```

Same image for web + worker; sessions in Redis/DB (not local memory); no local file state → horizontal scaling is free.

### G. What does and doesn't need a decision *now*

- **No decision needed before the spike:** the deployment topology does not block the Pipeline Spike — the spike can be a plain local script. Don't let infra design delay proving the renderer.
- **Cheap disciplines to adopt now (so options stay open):** clean bounded-context seam at the conversion worker; queue + blob-key contract (no cross-imports, no shared ORM reach-across); blobs in object storage; stateless web tier.
- **Genuinely needs the user's decision (see below):** how far to go on infra in the *first* buildout vs. keeping the spike dead-simple.

### H. Net recommendation to the user (deployment)

1. **Monolithic-but-modular Django, deployed as multiple container roles** — not microservices, not a single all-purpose container.
2. **Yes to an independently scalable conversion-worker container** from day one of the real build (this is your "more resources" freedom).
3. **No to a separate standalone project/repo yet** — keep one bounded context in the monorepo; design the worker's queue+blob contract so a future extraction (likely for a polyglot geometry service) is a swap, not a rewrite.
4. **REST for interaction, job queue for heavy work, SSE for progress.** No event bus.
5. **Object storage + signed URLs for render packages; Postgres for index/metadata only.**
6. **Do not service-split the engineering modules** — only the pipeline earns independent deployment.

### Items needing the user's decision / next round

- **F1.** Agree the boundary is "independent *container role* now, independent *repo/service* only when polyglot or release-cadence pressure is real"? (My recommendation: yes.)
- **F2.** Confirm: heavy geometry conversion stays **Python-first for v1** (IfcOpenShell/web-ifc via worker), with the queue+blob contract designed so it *can* go polyglot later — rather than committing to a native/C++/Rust geometry service up front?
- **F3.** Object storage choice — managed (S3/GCS/Azure Blob) vs self-hosted **MinIO** in your Docker cluster? This affects nothing architecturally (same API) but matters for your cloud cost/ops model, so it's your call.
- **F4.** Still open from Round 1: **(B)** Pipeline Spike as the gating next action, **(C)** exclude xeokit AGPL runtime, **(D)** can you supply one realistically large IFC, **(E)** Tekla IFC Z-up/Y-up + base point. These still need your sign-off before any code.

### Items That Need User Decision Or Another Claude Round

These are the only items Codex thinks still need explicit user decision or another Claude discussion round before implementation:

1. New platform boundary:
   - Decision needed: create a new neutral 3D platform app now, or perform one more spike inside `idfviewer` while treating it as disposable?
   - Codex preference: create the new platform boundary now, but keep the first spike small and reversible.

2. Pipeline spike gate:
   - Decision needed: accept that the next implementation should be a pipeline/rendering spike before production workspace models.
   - Codex preference: yes.

3. Large sample IFC:
   - Decision needed: can the user provide one realistic large IFC/model export for the spike?
   - Codex view: without this, performance conclusions will be weak.

4. Renderer candidates:
   - Decision needed: should the spike compare Three.js and Babylon.js, or start with Three.js only because the prototype already uses it?
   - Codex preference: compare both only if the setup cost is controlled; otherwise start with Three.js and keep Babylon as the first fallback.

5. Runtime licensing policy:
   - Decision needed: do we formally exclude AGPL runtime dependencies unless commercial licensing is purchased?
   - Codex preference: yes.

6. Platform deployment boundary:
   - Decision needed: should the 3D platform be a new Django app inside the current project first, or a separate repository/project from day one?
   - Codex preference: same repository/new app first, independent Docker roles for workers, with boundaries designed so it can split later.

7. Source format priority:
   - Decision needed: should the first spike prioritize IFC first, or IFC plus IDF/PCF federation together?
   - Codex preference: IFC pipeline first for scale risk, then add IDF/PCF federation once render-package strategy is proven.

8. Coordinate reality:
   - Decision needed: gather actual export conventions from Tekla/PDMS/E3D/SP3D sources: units, base point, axis orientation, and whether coordinates are plant-global or local.
   - Codex preference: make this part of the spike intake checklist.

### Proposed Next Round Prompt For Claude

If the user wants another Claude round, ask Claude to respond specifically to:

1. Whether the new 3D platform should begin as a new Django app in the same repo or as a separate service/repository from day one.
2. Whether the initial cloud deployment should be modular-monolith-plus-workers or stricter microservices.
3. What minimum queue, storage, and worker architecture is needed for the pipeline spike.
4. Whether Three.js-only is sufficient for the spike or Babylon.js comparison is worth the extra time.
5. What acceptance metrics should decide whether the web platform is viable for EPC-scale electrical engineering.

## Codex Convergence And Final Architecture Proposal

Date: 2026-06-22 - after Claude Round 2 and user answers

### User Answers Recorded

- **F2 - Python/Django-first geometry pipeline:** accepted. Heavy geometry conversion starts Django/Python-first for v1. We will later evaluate whether C++, Rust, native code, Node/web-ifc, or other runtimes are needed.
- **F3 - Storage:** self-hosted object storage first. Later we can evaluate Oracle Object Storage, Amazon S3, or another managed bucket provider.
- **xeokit AGPL runtime:** exclude for now. Keep xeokit as a future exploration/reference architecture; revisit only if the benefit is large enough to justify commercial licensing or a deliberate legal review.
- **Large IFC availability:** yes. The user has some real old-project IFC files around 20 MB and some downloaded sample IFC files. These are enough to begin a first spike, while still acknowledging that a later EPC-scale test will need larger/more representative files.
- **Tekla/base-point/axis uncertainty:** accepted as an unknown to measure, not a reason to abandon IFC. IFC is selected because Navisworks `.nwd` would be a better review format in theory but is too difficult and distracting as an initial foundation.

### Converged Architecture Decision

The final architecture direction for the next implementation pass is:

1. **Web-first product**
   - The engineering ecosystem remains web-first because the larger product includes engineering tools, EHT, cable optimization, cable pulling/construction management, dashboards, database workflows, approvals, collaboration, and reporting.
   - Native/desktop tools may be used server-side for conversion or QA, but the user-facing product is not built as a desktop application.

2. **Modular Django platform, not strict microservices yet**
   - Build the platform as a modular Django system in the current repo first.
   - Create a new neutral 3D platform app/bounded context, separate from `idfviewer` and separate from EHT.
   - Do not make the 3D platform an independent repo/service from day one.
   - Do not split EHT, cable, drum, construction, and database modules into microservices now.

3. **Multiple Docker container roles**
   - Deploy the same codebase as multiple runtime roles:
     - Django web/API container.
     - 3D conversion/tiling worker container(s).
     - Queue/broker.
     - Postgres.
     - Self-hosted object storage.
   - The worker containers can be allocated more CPU/RAM independently, which answers the performance/scaling concern without premature service extraction.

4. **REST plus async jobs**
   - Use REST for normal synchronous application behavior:
     - project/model/workspace/layer CRUD
     - metadata lookup
     - object selection detail
     - authoring save/load
     - permissions and audit
   - Use async job queues for heavy work:
     - source file ingestion
     - IFC/IDF/PCF parsing
     - conversion
     - tiling
     - compression
     - metadata/object indexing
     - future heavy calculations such as route solving or optimization
   - Use SSE for job progress first; WebSocket can wait until true collaborative editing or bidirectional scene events exist.
   - Do not introduce Kafka/event-sourcing/pub-sub event-bus architecture now.

5. **Object storage for blobs, Postgres for metadata**
   - Store original source files and render packages in self-hosted object storage first.
   - Postgres stores job state, indexes, metadata, workspace/layer data, object IDs, annotations, and engineering references.
   - Do not store large geometry blobs in Postgres.
   - Do not proxy large render files through Django; use signed URLs or an equivalent direct-object-storage download pattern once the deployment supports it.

6. **Renderer and runtime format**
   - Start with a practical browser renderer path, most likely Three.js because the prototype already uses it.
   - Keep Babylon.js as a fallback/comparison candidate if setup cost is controlled.
   - Do not build a broad multi-renderer frontend abstraction now.
   - Do isolate viewer operations behind a thin internal scene boundary: load package/tile, set transform, set visibility, pick object, highlight object, focus bounds.
   - WebGPU remains a future-capable path, not a v1 dependency.

7. **Pipeline before workspace UI**
   - The next technical milestone is not a polished composite workspace UI.
   - The next milestone is a pipeline spike proving source-file-to-optimized-render-package-to-browser performance.
   - The spike gates production data model freezing.

8. **3D platform core concepts**
   - The neutral core should eventually contain:
     - `SourceModel`
     - `ConversionJob`
     - `RenderPackage`
     - `RenderTile`
     - `ModelObject`
     - `Workspace`
     - `WorkspaceLayer`
     - `ViewState`
     - `Annotation`
   - EHT/cable/construction modules reference platform object IDs and workspace/layer objects.
   - The platform core must not import EHT or depend on EHT calculation internals.

9. **Precision and scale are foundational**
   - RTC/tile-local origins are accepted as a foundational requirement.
   - Coordinate units, base points, axis orientation, raw bounds, local render origin, and transformed engineering coordinates must be tracked from the beginning.
   - IFC coordinate uncertainty is treated as a measured input to the conversion pipeline, not as a reason to delay the platform.

10. **Future extraction path**
   - Independent scaling is solved now through worker containers.
   - A true separate 3D conversion service/repository is deferred until there is concrete pressure:
     - C++/Rust/native geometry processing becomes necessary.
     - Node/web-ifc tooling becomes dominant.
     - conversion workload needs a distinct release cadence.
     - licensing/process isolation requires stronger separation.
   - The queue plus object-storage-key contract should be kept clean so that future extraction is possible.

### Critical Weighing Of Claude's Proposal

Claude's proposal fits the current scenario well because:

- It avoids turning the project into a distributed system before the rendering pipeline is proven.
- It gives immediate resource freedom through worker containers.
- It keeps the commercial product web-first, which aligns with the larger engineering ecosystem.
- It keeps the hardest risk visible: conversion, tiling, batching, coordinate precision, and package format.
- It protects EHT and other production modules from being pulled into the 3D core.

Codex would adjust only one operational detail:

- Claude's "no direct ORM reach-across" principle is correct as a future extraction rule, but in a Django-first v1 it should not prevent practical worker implementation. A Python worker may use Django models/service functions to update `ConversionJob` status and create `RenderPackage`/`RenderTile`/`ModelObject` rows, as long as the heavy geometry inputs/outputs are passed by queue payloads and object-storage keys rather than in-memory Python object sharing. This keeps v1 simple while preserving the future polyglot boundary.

### Remaining Disagreements Or Items For Claude Final Review

There are no major philosophical disagreements left between Codex and Claude. The remaining points are implementation-tuning items:

1. **Spike location**
   - Codex final position: create the new neutral 3D platform app/bounded context now, and run the spike there.
   - Alternative: run one more disposable spike inside `idfviewer`.
   - Codex thinks the new boundary is worth creating now because `idfviewer` should not receive more architectural weight.

2. **Three.js-only versus Three.js plus Babylon.js**
   - Codex final position: start with Three.js for the first spike because current prototype knowledge exists; compare Babylon.js only if the first spike exposes renderer-level limitations or if the comparison can be done cheaply.
   - Claude may still prefer comparing both during the first spike.

3. **How formal the v1 data model should be before the spike**
   - Codex final position: create only the minimum models needed to track source file, conversion job, package/tile metadata, and measurement results for the spike. Avoid full semantic schema and workspace UI.
   - Claude may prefer an even more throwaway script-first spike.
   - Codex thinks a tiny app-backed spike is better because it tests the real Docker/Django/object-storage shape without committing the final schema.

4. **Self-hosted object storage choice**
   - User decision: self-hosted now.
   - Codex final position: use an S3-compatible self-hosted store if possible so future Oracle/Amazon migration changes configuration, not application architecture.
   - Need Claude to confirm whether MinIO or a simpler local filesystem abstraction is enough for the first spike.

5. **Sample-size sufficiency**
   - User has ~20 MB real IFC plus samples.
   - Codex final position: acceptable for first spike, but not enough to declare EPC-scale viability.
   - A later benchmark should use larger discipline/area exports closer to real plant-review size.

### Proposed Final Claude Review Questions

For the final Claude round before freezing architecture:

1. Do you agree with the final decision: modular Django monolith in one repo, new neutral 3D app, independently scalable worker containers, no standalone 3D service yet?
2. Do you accept Django/Python-first conversion workers for v1, with future C++/Rust/native/Node extraction protected by queue plus object-storage-key boundaries?
3. For self-hosted storage, should v1 use MinIO/S3-compatible storage from the beginning, or is a filesystem-backed storage abstraction acceptable for the first local spike?
4. Do you accept Three.js-first for the spike, with Babylon.js deferred unless Three.js exposes a renderer-level limitation?
5. What minimum spike models are safe to create without prematurely freezing the final semantic database?
6. What exact pass/fail metrics should decide whether the web rendering pipeline is acceptable for continuing?

### Final Architecture Freeze Candidate

Unless Claude raises a serious objection in the final round, the architecture to freeze is:

> A web-first EPC electrical 3D engineering platform implemented first as a new neutral Django app in the current repo, deployed as a modular monolith with independently scalable conversion workers, REST APIs for normal workflows, async queue jobs for heavy model processing, self-hosted object storage for source/render blobs, Postgres for metadata/indexes, browser-side rendering through optimized tiled packages with RTC/tile-local origins, Three.js-first viewer implementation, and EHT/cable/construction modules as consumers rather than owners of the 3D core.

## Claude Response — Final Round (Architecture Freeze Sign-Off)

Date: 2026-06-22 — final review before freeze

### Verdict

**No strong disagreement remains. I endorse the freeze candidate as written.** Codex's convergence matches the architecture I argued across Rounds 1–2 on every load-bearing point. The remaining items are implementation tuning, not philosophy. Codex's clarification on worker ORM use (heavy geometry by queue + storage key; metadata rows via ORM is fine) is a correct refinement of my rule, not a conflict — accepted.

### Terse answers to Codex's 6 final questions

1. **Modular Django monolith, one repo, new neutral 3D app, scalable workers, no standalone service yet?** Yes. Agreed.
2. **Python/Django-first conversion workers, polyglot extraction protected by queue + storage-key boundary?** Yes. Agreed.
3. **MinIO/S3-compatible vs filesystem for the spike?** **Use S3-compatible (MinIO) from the start.** A filesystem abstraction tempts you into POSIX semantics (paths, in-place mutation, directory listing) that object storage does not have; you would rewrite at migration time. Put `django-storages` + an S3 backend in front of MinIO now; later Oracle/S3 is a config change. This is the one item I would not soften.
4. **Three.js-first, Babylon deferred unless Three.js hits a wall?** Yes — with a named trigger: defer Babylon **unless Three.js fails a specific spike metric below** (FPS, draw-call batching, or precision). Then, and only then, run a focused Babylon comparison.
5. **Minimum spike models safe to create?** Only: `SourceModel`, `ConversionJob`, `RenderPackage`, `RenderTile`, plus a `SpikeMeasurement`/results record. **No** `ModelObject` semantic schema yet (that is the expensive, migration-sensitive one — freeze it *after* the spike tells us what objects/metadata the pipeline actually yields), **no** `Workspace`/`WorkspaceLayer`/`Annotation`, **no** viewer authoring UI. Mark these models in-code as provisional/spike so they are not mistaken for the frozen schema.
6. **Spike pass/fail metrics?** Defined below — this was the one genuinely missing piece.

### Spike pass/fail metrics (proposed — confirm before running)

Measured on a mid-range laptop GPU, against the ~20 MB IFC first, then the largest IFC available:

| Metric | Target (pass) | Why |
|---|---|---|
| Sustained FPS during orbit/pan | ≥ 30 (goal 60) | Interaction viability |
| Draw calls for loaded view | low hundreds, not thousands | Proves batching/instancing works; the prototype's per-object meshes are the anti-pattern |
| Tab memory for test model | ≤ ~1.5–2 GB | Browser headroom |
| Vertex jitter / z-fighting at true plant coordinates | none visible | Proves RTC/tile-local origins work — the single highest-risk item |
| Measurement repeatability at plant coordinates | error from float precision eliminated (RTC) | Engineering trust in the tool |
| Object pick latency | < ~100 ms | Selection usability |
| Pick → metadata shown | < ~200 ms | Metadata-on-demand pattern works |
| Source → render package conversion time | measured, not gated for v1 | Baseline for worker sizing; flag only if absurd |

**Decision rule:** if Three.js + the tiling/RTC/batched pipeline clears FPS, draw-call, and precision targets on the largest available IFC, the pipeline is accepted and we proceed to freeze the semantic schema. If it fails *precision*, fix the package format (not the renderer). If it fails *FPS/draw-calls* after batching/instancing/LOD are correctly applied, *then* run the Babylon comparison before concluding web is the bottleneck.

### Two non-blocking guardrails (for the record, no user decision needed)

- **G1 — Don't let the spike app become the foundation by inertia.** This is the exact trap that produced `idfviewer`. The spike models are provisional; the semantic schema is frozen only *after* spike results, deliberately, not by accretion.
- **G2 — Adopt the clean seam from line one of the spike:** worker communicates via queue payload + object-storage key; web tier never reaches into worker internals; blobs never enter Postgres; render packages never proxy through Django. These cost nothing now and preserve every future option (polyglot, service extraction).

### Sign-off

Architecture is frozen as far as I am concerned. The next deliverable is the **Pipeline Spike with the metrics above**, not feature code. Production EHT/SLD/cold-cable paths remain untouched throughout. Proceed.
