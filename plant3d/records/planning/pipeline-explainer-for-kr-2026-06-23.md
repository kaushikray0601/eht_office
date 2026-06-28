# plant3d Pipeline — Explainer for KR (basics → advanced)

Date: 2026-06-23
Author: Claude
Purpose: explain, from the ground up, the 3D rendering pipeline Codex has built and is planning, for a reader who knows Django/MVT well but has limited 3D-graphics background. Grounded in the actual `plant3d` code, with examples.

---

## 0. Start from your mental model (it was correct — just incomplete)

Your original mind-map was:

> User uploads an IFC → an off-the-shelf parser (IfcOpenShell) decodes it → Django sends the geometry/metadata to the browser → JavaScript hands it to Three.js → Three.js draws it.

**That is still exactly the shape of the system.** Nothing about that direction was wrong. What changed is that each arrow had to become *much* smarter, because a real plant model is enormous and a browser is a small, sandboxed program compared to PDMS/Navisworks on a workstation.

Think of it like the difference between:
- emailing someone a 2-page PDF (your original model — just send the data), versus
- shipping a 10,000-page document set to a site office: now you need indexing, volumes, a delivery schedule, and "only pull the drawings you're working on today."

Same direction (get the document to the reader), but the scale forces logistics. Everything Codex added is **logistics for geometry**.

---

## 1. The vocabulary you need (3D basics, in plain terms)

Before the code, six terms. I'll use a plant example for each.

- **Vertex**: a single 3D point, `(x, y, z)`. A corner of a steel beam is a vertex.
- **Triangle**: three vertices. *All* 3D graphics is made of triangles — a flat plate is 2 triangles, a pipe is hundreds, a whole plant is millions. The GPU only knows how to draw triangles.
- **Mesh**: a bag of vertices + a list of which vertices form each triangle. One beam = one mesh. The IFC file, once decoded, becomes thousands of meshes.
- **GPU (Graphics Processing Unit)**: a chip whose entire job is "draw millions of triangles per frame, 60 times a second." Your CPU is a few clever workers; a GPU is thousands of simple workers doing the same tiny job in parallel. Rendering 3D *fast* means handing work to the GPU in the exact shape it likes.
- **WebGL / Three.js**: WebGL is the browser's doorway to the GPU (a low-level API). **Three.js** is a friendly JavaScript library on top of WebGL so you write `scene.add(mesh)` instead of hundreds of lines of GPU plumbing. This is the "Three.js" in your mind-map.
- **Draw call**: one instruction from JavaScript to the GPU saying "draw this batch of triangles now." Here's the crucial, non-obvious fact: **the number of draw calls matters more than the number of triangles.** A GPU can draw 5 million triangles in *one* draw call easily, but 5,000 separate small meshes (5,000 draw calls) will choke the browser. This single fact explains ~half of what Codex built.

Also two scale/precision terms that come up later:

- **float32**: GPUs store coordinates as 32-bit floating-point numbers — only ~7 significant digits. Fine for `12.345 m`. *Not* fine for `512345.678 m` (a plant on a national survey grid), where the digits after the decimal get rounded away — geometry visibly shakes ("jitter"). Fixing this is the **RTC** story in §5.
- **LOD (Level of Detail)**: show a coarse/simple version of far-away objects and the detailed version only up close — like a map that shows more detail as you zoom in.

---

## 2. The big picture (one diagram)

```text
        ┌─────────── DJANGO (the "factory" — prepares geometry) ───────────┐
USER →  Upload IFC → store file → queue a Job → [worker] decode + convert  │
        │                                              ↓                    │
        │                              optimized binary packages (GLB)      │
        │                              + metadata index in the database      │
        └──────────────────────────────────────────────┬───────────────────┘
                                                        │  (served via API URLs)
        ┌──────────── BROWSER (the "site office" — draws geometry) ─────────┐
        │  JavaScript fetches packages in chunks → Three.js → GPU draws them │
        │  + only loads the tiles you're currently looking at                │
        └───────────────────────────────────────────────────────────────────┘
```

Mapping to **Django MVT**, so it's familiar:
- **Model**: `SourceModel`, `ConversionJob`, `RenderPackage`, `RenderTile`, `ModelObject` — rows in the database (`plant3d/models.py`).
- **View**: the URL endpoints in `plant3d/views.py` — upload, list, "give me package N as JSON", "give me tile N's binary blob", "what's the status of job N".
- **Template**: `plant3d/templates/plant3d/*.html` — thin HTML shells that mostly just host the JavaScript viewer.
- **The new part that isn't classic MVT**: a **background worker** (a management command) that does the heavy decoding *outside* the request/response cycle, and a **storage layer** for big binary files. More on both below.

---

## 3. Stage by stage, with the real code

### Stage 1 — Upload and store (pure Django, familiar territory)

When the user uploads an IFC, `create_source_model_from_upload` in `plant3d/services.py`:
1. reads the file in chunks and computes a **SHA-256 content signature** (a fingerprint of the bytes),
2. writes the raw file to storage under a **storage key** (a string path like `plant3d/source/<project>/<hash>/file.ifc`),
3. creates a `SourceModel` database row recording the filename, size, project, signature, and that storage key.

Why a "storage key" string instead of a Django `FileField`? So that later the same code can save to local disk **or** to cloud object storage (MinIO/S3) by swapping the backend — the business logic never hard-codes a filesystem path. This is the `plant3d/storage.py` layer.

Example `SourceModel` row (conceptually):
```
display_name = "8-SSPAR-800203.ifc"
storage_key  = "plant3d/source/P1/eda6e4c7.../8-SSPAR-800203.ifc"
content_signature = "eda6e4c7..."   file_size_bytes = 2,815,485   source_format = "IFC"
```

So far this is 100% ordinary Django. Nothing 3D yet.

### Stage 2 — The job queue (why decoding is NOT done in the web request)

Decoding a 2.8 MB IFC takes **~17 seconds** (measured). A web request that takes 17 seconds will time out behind a normal web server, and it ties up a worker the whole time. So Codex separated it:

- The upload/convert **View** just creates a `ConversionJob` row with `status = "queued"` and returns immediately (HTTP 202 "Accepted"). It does *no* heavy work.
- A separate program — the management command `process_plant3d_job` (`plant3d/management/commands/`) — picks up queued jobs and runs the actual decode/convert. You run it with `manage.py process_plant3d_job --next`.
- The job row marches through `queued → running → completed` (or `failed`), and the source page **polls** ("are we done yet?") until it sees `completed`.

This is the classic "don't do slow work in the request" pattern. Today the "worker" is a manual command (fine for the spike); later it becomes an automatic queue (Celery/RQ). Conceptually: **the View takes the order; the worker cooks the meal.**

### Stage 3 — Decode the IFC into meshes (the parser)

The worker calls `parse_multiple_ifc_uploads` (now in `plant3d/parsers/ifc.py`, copied out of the old prototype). This uses **IfcOpenShell** (the off-the-shelf library) to turn IFC entities into raw triangles. The output is a Python dict — a "scene" — shaped like:

```python
scene = {
  "meshes": [
     { "uid": 1, "kind": "IfcBeam",
       "mesh": { "positions": [x,y,z, x,y,z, ...],   # flat list of vertex coords
                 "indices":   [0,1,2, 2,3,0, ...],   # which vertices form each triangle
                 "color":     [0.5, 0.5, 0.55] },
       "properties": { "global_id": "3kP7...", "ifc_class": "IfcBeam", "tag": "B-001", ... } },
     ...  # one entry per object in the model
  ],
  "stats": { "raw_bounds": {min_x, max_x, min_y, ...}, "coordinate_unit": "M", ... }
}
```

So a "mesh" is just **positions + indices + a color + engineering properties**. The whole IFC becomes a list of these. `stats.raw_bounds` is the bounding box of the entire model — used next for the coordinate fix.

### Stage 4 — The coordinate problem (RTC), the part that looks mysterious

Two adjustments happen to every vertex, and they're the source of most of the "what is going on" feeling:

**(a) Axis swap.** IFC/engineering convention is **Z-up** (Z is the vertical/elevation axis). Three.js/glTF convention is **Y-up**. So the parser maps source `(x, y, z)` → render `(x, z, y)`. That's why you'll see `[x, z, y]` reorderings in the code — it's just "make elevation point up the way the renderer expects."

**(b) RTC — Relative-To-Center (the float32 fix).** Remember float32 only has ~7 digits. If a plant sits at easting `512345.678`, every vertex carries that huge number and the GPU rounds away the millimetres → visible shaking. The fix: pick an **origin** (the centre of the model/tile), subtract it from every vertex so the vertices become small numbers near zero (`-17.2 … +17.2`), and store the big origin **once** as a separate double-precision number. At draw time the viewer places the whole tile back at its origin.

In `plant3d/services.py` this is `origin_source_xyz` (the big centre, in source coordinates) and `rtc_origin_render_xyz` (the same centre, already axis-swapped/scaled into render space). The contract, stored in the package, is literally written out as a formula:

```
render_world_xyz = rtc_origin_render_xyz + local_vertex_xyz     # put the tile back
source_xyz       = [render_world.x/scale, render_world.z/scale, render_world.y/scale]  # reverse it
```

There's a test that takes a vertex, adds the origin, reverses the scale and swap, and checks it lands back on the original coordinate — proving the maths is self-consistent. (Caveat we've flagged: the sample files are at small coordinates, so this *correctness* is proven but the *jitter-at-scale* benefit isn't yet — that needs a real large-coordinate file.)

### Stage 5 — Packaging the geometry: JSON first (debug), then GLB (the real leap)

Now the worker has to turn the scene into something the browser downloads. Two formats exist:

**JSON package (the first/debug version).** Just `json.dumps(scene)` — the positions/indices as text. It works, but a 2.8 MB IFC became a **10.5 MB JSON** file. Text is bloated, slow to parse, and not in the GPU's native shape. Good enough to prove the flow; useless at scale. This is what matched your original mind-map most literally ("send the metadata as JSON").

**GLB package (the leap that "went beyond your understanding").** `plant3d/glb.py` builds a **GLB** file. GLB = "binary glTF" — glTF is the industry-standard 3D file format (think "the JPEG of 3D"), and GLB is its single-binary form. Crucially, the vertex numbers are stored as **raw binary floats in the exact layout the GPU wants**, not as text. Same Tekla model: JSON 10.5 MB → **GLB 5.4 MB**, and it loads far faster because the browser hands the binary almost straight to the GPU.

What `build_glb_from_meshes` does, in plain terms:
1. **Color bucketing (batching).** Instead of 867 separate meshes (= 867 draw calls = slow), it groups all objects of the *same colour* into one combined mesh. The Tekla model collapsed to ~4 buckets → **~4 draw calls.** This is the single biggest performance trick, and it's exactly the "draw calls matter more than triangles" point from §1.
2. **Feature IDs (how picking survives the merge).** If you merge 867 beams into 4 big blobs, how do you click one beam and get *its* tag? Codex tags every vertex with a number — a **feature ID** — saying "this vertex belongs to object #438." It's stored as a special vertex attribute `_FEATURE_ID_0`, plus a small "sidecar" JSON mapping `feature 438 → {global_id, tag, ...}`. So picking needs **no duplicate geometry** — you read the feature number under the cursor and look it up. (We caught and Codex fixed two bugs here: the ID was stored in a glTF-illegal number format, and the ID didn't match the database ID for objects lacking a GlobalId.)
3. **Normals.** For each triangle it computes a "normal" (the direction the surface faces) so lighting/shading looks right. (We flagged this is done in slow pure-Python; numpy would speed it up — a pending cleanup.)
4. **Writes the GLB container**: a 12-byte header + a JSON chunk (the structure: which buffer, what colors) + a BIN chunk (the raw binary vertex bytes).

The `RenderPackage` / `RenderTile` database rows record *where* these blobs live and their metadata (object count, byte size, RTC origin). The actual geometry bytes live in storage, **not** in the database.

### Stage 6 — Splitting into tiles (so one giant file isn't loaded all at once)

Even a good GLB of a *whole plant* would be huge. So for large models Codex splits the geometry into **spatial child tiles** — chop the model's bounding box into a grid, ~500 objects per tile, each tile its own little GLB with its own RTC origin (`services.py`, `GLB_TARGET_OBJECTS_PER_TILE = 500`).

A small **`tileset.json`** file lists the tiles (this is a simplified version of the industry "3D Tiles" standard — think "the index/table-of-contents for the volumes"). The package-9.4 MB sample produced **9 tiles**. Why tile? So the browser can fetch and draw **only the tiles you're currently looking at**, not the entire plant. That's the "asynchronous streaming" you noticed.

### Stage 7 — The browser viewer (your "JS feeds Three.js", upgraded)

`plant3d/static/plant3d/js/package_viewer.js` is the JavaScript. The flow:

1. Fetch the package description from a Django API URL (`/plant3d/packages/<id>/json/`). For a GLB package this includes the `tileset.json` (the list of tiles + their RTC origins).
2. **Streaming/culling** — the part that looks like "chunked async loading":
   - It works out which tiles are inside the camera's view ("frustum culling" — a frustum is the pyramid-shaped volume the camera can see).
   - It loads at most `MAX_LOADED_GLB_TILES = 6` tiles, nearest first, and as you orbit it **loads tiles that come into view and unloads (and frees the memory of) tiles that leave view** (`loadGlbTileState` / `unloadGlbTileState`). This is the "send/draw data in chunks" behaviour.
   - Each loaded tile is positioned at `tile.rtc_origin − package_origin`, which is the RTC trick from §4 putting the tile back in its correct place.
   - It loads the binary GLB with Three.js's `GLTFLoader`, which decodes it and uploads the triangles to the GPU.
3. **Picking**: when you click, it works out which object is under the cursor, reads that vertex's `_FEATURE_ID_0`, looks up the sidecar/database to show the object's tag and properties.
4. The sidebar shows live numbers: FPS (frames per second), draw calls, triangles, loaded tiles, etc. — so we can *measure* instead of guessing.

So your mind-map's last arrow ("JS feeds Three.js") is intact — it's just now "JS *streams* binary tiles into Three.js and only the visible ones."

---

## 4. What's planned next (basics → advanced), in plain terms

In rough order:

1. **A large-coordinate test (precision proof).** The current files sit near the origin, so the jitter problem can't actually appear. Plan: take a sample and shift it by +500,000 to force the problem, and confirm the RTC fix really removes the shaking. *Why it matters:* it's the one big risk we haven't truly proven.
2. **A known-dimension unit check.** Convert an object known to be exactly 1 m and confirm it renders as 1 m — and especially check the file that declares **feet**, since unit mistakes cause silent 0.3 m / 3 m / 1000× scale errors. (Half-done: the metre case passes; the feet case is pending.)
3. **meshopt compression.** A standard glTF compression that shrinks the GLB further and loads faster — the direct lever on file size. (The biggest "make it lighter" win still on the table.)
4. **Faster conversion (numpy).** Replace slow pure-Python loops in `glb.py` with vectorised maths to cut the 17 s.
5. **LOD (level of detail).** Right now if you zoom out past 6 tiles, the extra tiles simply don't draw (holes). The grown-up fix is to show a coarse stand-in for far tiles instead of dropping them — so the whole plant is visible, cheaply, when zoomed out.
6. **Better picking at scale (BVH).** A spatial index (`three-mesh-bvh`) so "what's under the cursor?" stays instant on huge tiles.
7. **Proper delivery & worker (production infra).** Serve the binary blobs straight from object storage via signed URLs (not through Django), and replace the manual `process_plant3d_job` command with an automatic queue + live progress (SSE/WebSocket).

None of these change the *shape* of the pipeline — they each make one arrow lighter, faster, or more correct.

---

## 5. Where each new idea lives, in Django terms (cheat-sheet)

| New concept | Plain meaning | Where in the code | Django analogy |
|---|---|---|---|
| Content signature | file fingerprint for dedup | `services.py` | a unique hash field |
| ConversionJob + command | slow work done outside the request | `models.py`, `management/commands/` | a background task / cron job |
| Storage key + storage.py | save big files by string key, swappable backend | `storage.py` | `FileField` but cloud-ready |
| Parser scene | IFC decoded to triangles + properties | `parsers/ifc.py` | a serializer's raw output |
| RTC origin / axis swap | keep coordinates small so the GPU is accurate | `services.py` | a normalize step |
| JSON package | text geometry (debug only) | `services.py` | `JsonResponse` of data |
| GLB package | binary, GPU-ready geometry | `glb.py` | a generated binary file artifact |
| Feature IDs + sidecar | click a merged blob, get one object's data | `glb.py`, viewer | a foreign-key lookup table |
| Tiles + tileset.json | split geometry into streamable chunks | `services.py` | pagination, for 3D |
| Streaming/culling | load only the tiles in view | `package_viewer.js` | lazy-loading / infinite scroll |

---

## 6. The one-paragraph summary to hold onto

Django is now a **geometry factory**: it takes an IFC, decodes it to triangles, fixes the coordinates so the GPU stays accurate, packs the triangles into compact **binary GLB files** (merged by colour so the GPU draws them in a handful of "draw calls"), tags each vertex with an **object ID** so clicking still identifies a single beam, and splits big models into **tiles** with a table-of-contents. The browser is now a **streaming viewer**: it reads the table-of-contents, downloads only the tiles you're looking at, hands their binary straight to the GPU through Three.js, frees tiles you've left behind, and uses the vertex IDs to answer "what did I just click?". Your original mental model was the right skeleton; all of this is the muscle that lets it carry a whole plant in a browser tab.
