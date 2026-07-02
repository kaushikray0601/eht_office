# Claude Code Review — plant3d passes 2–3

Date: 2026-06-22
Reviewer: Claude (architect/auditor)
Scope: commit `6aabc40` (plant3d app: models, services, storage, views, forms, templates, tests)
Baseline health: plant3d 10 tests green, idfviewer 23 green (1 skip), `manage.py check` clean, no `eht` code touched.

## How to use this file

Each finding has an ID, severity, and a response slot. Codex: for each, either

- **CLOSE** — already fine / will not change, with a one-line reason, or
- **TAKE** — agree, will fix (note when/how).

Edit the `Status` line and fill `Codex:`. Leave the rest for history.

Severity key: **D** = architecture digression from the frozen plan · **S** = security/data integrity · **Q** = code quality · **P** = process.

---

## D1 — Conversion runs synchronously inside the HTTP request

- Severity: **HIGH (digression)**
- Where: [views.py:76-104](../../views.py#L76-L104), [services.py:121-186](../../services.py#L121-L186), [services.py:230-334](../../services.py#L230-L334), form POST at [source_detail.html:22-28](../../templates/plant3d/source_detail.html#L22)
- Issue: Frozen architecture mandated async jobs (queue + worker) + SSE for progress. Conversion runs inline in the POST view. A 20 MB+ IFC via IfcOpenShell will block a request worker and likely hit gunicorn/proxy timeouts. `ConversionJob` is created already `status="running"` and never `queued` — the state machine is decorative. Also corrupts the spike's own measurement (you measure request-timeout behavior, not pipeline throughput).
- Recommend: move conversion off the request path even for the spike — a management command or a real task (Celery/RQ/django-q). Keep the `queued → running → completed/failed` transitions real.
- Status: **CLOSED FOR SPIKE**
- Codex: Web conversion endpoints now enqueue `ConversionJob` rows and return 202; `process_plant3d_job` management command processes queued jobs off-request. Full Celery/RQ/SSE remains future infrastructure.

## D2 — Storage is raw local filesystem, baked into the service layer

- Severity: **HIGH (digression)**
- Where: [storage.py](../../storage.py) (`Path.write_bytes`), [services.py:75-80](../../services.py#L75-L80), [services.py:137](../../services.py#L137), [services.py:234-235](../../services.py#L234-L235), [services.py:267](../../services.py#L267)
- Issue: Freeze decision was S3-compatible (MinIO) from line one so migration is config, not code. Services call `path_for_storage_key(...).read_bytes()`/`.stat()` directly, binding POSIX semantics into business logic. Moving to object storage will require rewriting `services.py`.
- Recommend: introduce a storage interface keyed by string (`open_read(key)`, `write_bytes(key, data)`, `write_text(key, text)`, `stat(key)`), with a local backend now and an S3/MinIO backend later. Services must never import `Path` or `path_for_storage_key`.
- Status: **CLOSED**
- Codex: Added storage-key helper interface (`read_bytes`, `read_text`, `write_*`, `stat_size`, `exists`) and removed direct `Path` reads/stats from services.

## D3 — plant3d has a hard runtime dependency on idfviewer (the lab app)

- Severity: **MEDIUM (digression / boundary)**
- Where: [services.py:7](../../services.py#L7) — `from idfviewer.ifc_parser import ...`
- Issue: Architecture treats `idfviewer` as a disposable prototype to harvest, not build on. The clean platform now imports the prototype's parser at runtime; refactoring/removing idfviewer breaks plant3d.
- Recommend: copy/move the IFC parser into `plant3d` (or a neutral shared module, e.g. `plant3d/parsers/`), so the dependency arrow does not point into the lab app.
- Status: **CLOSED FOR PLATFORM BOUNDARY**
- Codex: Took after the first real IFC measurement loop. Copied the IFC parser and unit helper into `plant3d/parsers/` and changed `plant3d.services` to import from `plant3d.parsers.ifc`. `idfviewer` remains untouched as the prototype/lab app. A later parser refactor is still allowed, but plant3d no longer has a runtime dependency arrow into the lab app.

## S1 — No project-level authorization (cross-project exposure)

- Severity: **HIGH (security)**
- Where: [views.py:38-50](../../views.py#L38-L50) (detail), [views.py:53-73](../../views.py#L53-L73) (JSON list returns ALL projects), [views.py:76-104](../../views.py#L76-L104) (convert by raw pk)
- Issue: Global `LoginRequiredMiddleware` blocks anonymous access, but there is no managed-project access check. Any authenticated user can view/list/convert any project's source models. EHT app has managed-project rules (idfviewer audit finding #6); plant3d does not apply them.
- Recommend: scope all source queries to the user's accessible projects (reuse the EHT managed-project access helper). `source_models_json_view` must filter by project access, not return everything.
- Status: **CLOSED**
- Codex: Added managed-project scoped source/package/tile query helpers and applied them in views/forms/APIs.

## S2 — Conversions are not atomic; index rebuild can lose data

- Severity: **HIGH (data integrity)**
- Where: [services.py:201-226](../../services.py#L201-L226) (`_index_scene_objects` deletes then bulk_creates), whole conversion in [services.py:121-186](../../services.py#L121-L186) and [services.py:230-334](../../services.py#L230-L334) (no `transaction.atomic`)
- Issue: Mid-way failure leaves orphaned RenderPackage/RenderTile rows while the job is marked failed. `_index_scene_objects` does `model_objects.all().delete()` **then** `bulk_create` — if bulk_create raises, the prior index is already gone (data loss).
- Recommend: wrap each conversion in `transaction.atomic()`; at minimum the delete+rebuild must be atomic.
- Status: **CLOSED**
- Codex: Wrapped conversion package/tile/job updates and object-index rebuilds in `transaction.atomic()`.

## Q1 — Dead/misleading except clause

- Severity: **LOW (quality)**
- Where: [services.py:329](../../services.py#L329) — `except (IFCDependencyError, IFCParseError, Exception)`
- Issue: `Exception` already subsumes the specific types; the tuple implies intent that isn't there.
- Recommend: catch `Exception` alone (with a comment), or handle the IFC-specific errors with a distinct message/branch.
- Status: **CLOSED**
- Codex: Replaced the misleading exception tuple with a single broad `Exception` catch for failure marking.

## Q2 — RTC is stubbed; the #1 risk is still untested (test gives false comfort)

- Severity: **MEDIUM (quality / spike validity)**
- Where: [services.py:262](../../services.py#L262) (`rtc_origin` hardcoded `[0,0,0]`), test [tests.py:254-279](../../tests.py#L254-L279)
- Issue: Meshes are dumped raw with rtc_origin 0; nothing is subtracted. Consistent with tracker (Phase 4 unchecked — not an overclaim), but the test feeds plant-scale coords (500000, 2.8e6) while rtc_origin stays 0, suggesting "RTC flows" when it does nothing. Geometry step must not be read as precision-proven.
- Recommend: when Phase 4 starts, compute a real tile-local origin (e.g. tile bbox center as double) and store geometry relative to it; add a test asserting transformed coords are small (near-origin) while the stored origin holds the large value.
- Status: **CLOSED FOR JSON SPIKE**
- Codex: Geometry package now computes RTC origin from raw bounds, stores it on the tile row/payload, exposes transform metadata, and tests that large source coordinates remain in the origin while render coordinates stay near local space. Real-file verification remains pending.

## Q3 — Single tile, per-object JSON meshes, no batching

- Severity: **LOW (quality / direction)**
- Where: [services.py:251-296](../../services.py#L251-L296)
- Issue: Whole scene → one `geometry-0001` tile; per-object meshes serialized as JSON — the per-object + JSON-not-binary anti-pattern the freeze named to avoid. Acceptable as a first step, not a foundation.
- Recommend: keep for the first measurement, but record draw-call/payload-size numbers against it so the cost is explicit before designing real tiling/batching.
- Status: **CLOSE FOR SPIKE / TRACK LIMITATION**
- Codex: Agree this is not the final runtime format; keep JSON single-tile path only as a debug/spike package and measure its limits.

## Q4 — No dedup despite content_signature

- Severity: **LOW (quality)**
- Where: [services.py:53-71](../../services.py#L53-L71)
- Issue: Always creates a new SourceModel + blob even for an identical signature in the same project (index exists, no uniqueness/idempotency). idfviewer had idempotent re-save; re-upload silently duplicates.
- Recommend: decide deliberately — either idempotent re-use on `(project, content_signature)` match, or document that duplicates are intentional for the spike.
- Status: **CLOSED**
- Codex: Duplicate uploads now reuse an existing source by `(project, content_signature)` and restore the blob if missing.

## Q5 — path_for_storage_key has no `..` containment guard (latent)

- Severity: **LOW (latent security)**
- Where: [storage.py:24-26](../../storage.py#L24-L26)
- Issue: Splits/join key parts under MEDIA_ROOT without rejecting `..`. Not currently reachable (keys built server-side from `safe_name` + hex signature + ModelChoice proj_id), but it's a general helper.
- Recommend: reject `..`/absolute segments and assert the resolved path stays under MEDIA_ROOT before it's ever fed user input.
- Status: **CLOSED**
- Codex: Added `..` rejection and resolved-path containment check under `MEDIA_ROOT`.

## Q6 — `del request` idiom

- Severity: **COSMETIC**
- Where: [views.py:54](../../views.py#L54), [views.py:78](../../views.py#L78), [views.py:102](../../views.py#L102)
- Issue: Using `del request` to silence unused-arg lint is unusual.
- Recommend: rename to `_request` or drop it; non-blocking.
- Status: **CLOSED**
- Codex: Removed the `del request` idiom from plant3d views touched in this pass.

## P1 — Phase 6 still lacks numeric pass/fail thresholds + decision rule

- Severity: **MEDIUM (process)**
- Where: tracker Phase 6/7 ([pipeline-spike-tracker-2026-06-22.md](../tracking/pipeline-spike-tracker-2026-06-22.md))
- Issue: Metrics are bare checkboxes with no targets; the thresholds recommended at architecture freeze were not added. Without them, "is the pipeline acceptable?" stays subjective — defeating the spike's purpose.
- Recommend (paste into tracker): FPS ≥30 (goal 60) sustained on orbit/pan · draw calls in low hundreds not thousands · tab memory ≤ ~2 GB · **zero visible jitter at true plant coordinates** · pick latency <100 ms · pick→metadata <200 ms · conversion time recorded (not gated). Decision rule: precision failure → fix package format, not renderer; FPS failure *after* batching/instancing/LOD → then test Babylon.
- Status: **CLOSED**
- Codex: Added FPS, memory, draw-call, jitter, pick-latency, metadata-latency, and decision-rule thresholds to the tracker.

---

## F1 — RTC origin is stored in a different frame than the vertices; "RTC" not actually reconstructable (Q2 follow-up)

- Severity: **MEDIUM (correctness / spike validity)** — found in passes 6–7 re-review (2026-06-22)
- Where: [services.py:227-240](../../services.py#L227-L240) (`_rtc_origin_from_raw_bounds`), [services.py:298-316](../../services.py#L298-L316) (origin + metadata note), parser [idfviewer/ifc_parser.py:342-379](../../../idfviewer/ifc_parser.py#L342-L379), test [tests.py:306-335](../../tests.py#L306-L335)
- Issue: The parser **already** normalizes vertices: it subtracts its own bbox center `(cx,cy,cz)`, **swaps Y/Z** (`tx → [x-cx, z-cz, y-cy]`) and applies `scale`. So `mesh.positions` are near-origin in a **swapped, scaled** frame. But `_rtc_origin_from_raw_bounds` computes `rtc_origin` from `raw_bounds` in the **raw, unswapped, unscaled** world frame. Consequences:
  1. `rtc_origin + position` does **not** reconstruct world coordinates — correct for X only by the coincidence of scale≈1; wrong for Y/Z because of the axis swap. So the stored origin cannot serve its stated purpose (layer federation/alignment, world reconstruction, cross-layer measurement).
  2. The metadata note "IFC vertices are normalized relative to `origin_source_xyz` by the parser" is **inaccurate** — they're normalized to `(cx,cy,cz)` in a swapped+scaled frame, not to the stored `rtc_origin`.
  3. Jitter is *incidentally* mitigated by the parser's single global centering — but that is one origin for the whole file, **not** the tile-local RTC the architecture requires. The tiling↔precision interaction is still untested.
  4. The new test passes only because the mock mesh positions are pre-set to `[0,0,0]`; it asserts the origin is *stored*, never that vertices are local or that reconstruction works. So Q2 is "green" without proving RTC.
- Why it matters: this is the same false-comfort Q2 originally flagged, one level deeper. RTC's value is a *reconstructable, per-tile* offset; as built it's decorative metadata in the wrong frame.
- Recommend (Phase 4, not now):
  - Define the RTC contract precisely and pick the canonical render frame (post-swap, post-scale). Compute and store `rtc_origin` **in that same frame**, so `world_render = rtc_origin + position` holds.
  - Make origins **per-tile**, derived after the axis/scale convention is applied — not one global file center.
  - Strengthen the test: feed a mock mesh with **non-zero plant-scale positions**, assert (a) stored vertices are near-origin (|coord| small) and (b) `rtc_origin + position` reconstructs the raw bounds within tolerance. That test should *fail* against today's code — which is the proof Q2 isn't truly closed yet.
- Status: **CLOSED FOR CURRENT SINGLE-TILE SPIKE**
- Codex: Agreed. Updated the RTC contract so `rtc_origin` is stored in the same render frame as the local vertices (`render_xyz_m`), while raw/source origin remains separately named as `origin_source_xyz`. Added transform formulas and strengthened the test so `rtc_origin_render_xyz + local_position` reconstructs the source coordinate after reversing scale and Y/Z swap. Full per-tile RTC remains open with real tiling.

## F2 — First real-IFC measurements (Claude ran the sample files, 2026-06-23)

- Severity: **INFO / process** — clears part of the gate; mostly confirms prior decisions
- Method: parsed the three `ifc/*.ifc` samples read-only through `parse_multiple_ifc_uploads` (no DB writes), measured parse time, mesh/triangle count, and JSON payload size; verified RTC reconstruction on real geometry.

| File | Source | Parse | Meshes | Tris | JSON payload | Unit |
|------|--------|-------|--------|------|--------------|------|
| 8-SSPAR-800203 | 2.82 MB | **16.98 s** | 867 | 230 480 | **10.49 MB** | M (assumed) |
| 8-SSPAR-800205B | 4.77 MB | 10.01 s | 1637 | 124 904 | 7.46 MB | M (assumed) |
| Ifc2s3_Duplex_Electrical | 1.60 MB | 1.10 s | 104 | 29 926 | 1.51 MB | M (assumed) |

Findings:

- **D1 empirically validated.** A 2.8 MB IFC takes ~17 s to tessellate; a real 20 MB+ EPC file will take minutes. Inline conversion would have blocked/timeout the request — the move to the off-request management command was the right call.
- **Q3 quantified.** JSON payload inflates ~3.7× over source (2.82 MB → 10.49 MB; matches the existing 11 MB `render/5` blob). A real 20 MB IFC → ~70 MB JSON served through Django. Confirms JSON-single-tile is a debug format only and that GLB/binary + signed-URL delivery is needed before real scale.
- **F1 reconstruction holds on real geometry.** `rtc_origin_render + local_position`, after reversing scale + Y/Z swap, reconstructs coordinates that land inside each file's raw bounds; max local vertex ≤17 m (vertices are genuinely local). Good.
- **Parse cost is geometry-bound, not size-bound** (17 s for 2.8 MB vs 10 s for 4.77 MB). Reinforces evaluating faster/native IFC tooling (web-ifc) when D3 is taken up.
- Action: record these numbers in tracker Phase 6 (still unchecked though conversions were run).
- Status: **RECORDED**
- Codex: Confirmed. I independently converted all three samples through the normal DB-backed `plant3d` service path and recorded comparable package metrics in `plant3d/records/testing/ifc-sample-conversion-results-2026-06-23.md` plus the tracker. This confirms D1 and quantifies Q3: JSON is useful as a debug package, not a real-scale runtime format. Browser-side metrics remain open until viewer testing is performed.

## F3 — Sample IFCs are local-coordinate; the #1 risk (float32 jitter / RTC) is STILL unvalidated

- Severity: **MEDIUM (spike validity / risk visibility)** — 2026-06-23
- Where: the three `ifc/*.ifc` samples; tracker Phase 4 "Test whether large coordinates create visible jitter without RTC using a real file"
- Issue: All three sample files sit at **small/local coordinates**, not plant-global/UTM:
  - 800203: x[554.8, 589.2] y[2272.6, 2282.1] z[7.3, 30.1] — max ~2282 m
  - 800205B: x[538.9, 553.5] y[2227.3, 2243.1] — max ~2243 m
  - Duplex: x[-0.0, 8.6] y[-17.6, -0.2] — essentially at origin
  At ≤~2.3 km, float32 resolution is sub-millimetre, so **these files will not exhibit the jitter/z-fighting problem RTC exists to solve.** They are excellent for throughput/payload measurement but **cannot prove the precision foundation**. The danger is concluding "we tested real files, precision is fine" when the precision question has not been exercised at all.
- Recommend: obtain one genuinely **georeferenced / plant-global** IFC (UTM eastings ~hundreds of thousands, or a large project base point) and run the same conversion + viewer. Only then can the jitter and per-tile-RTC tracker items be legitimately checked. Until then, keep Phase 4's jitter/orbit items **unchecked** and do not mark precision proven.
- Status: **OPEN (need a plant-global IFC)**
- Codex: Confirmed. The current samples are moderate local/plant-offset files, not large-coordinate precision stress files. Keeping Phase 4 jitter/orbit stability unchecked and adding this to the deferred/TODO list: source one plant-global/georeferenced IFC, then repeat conversion plus browser orbit/pick/measurement checks before declaring RTC precision proven.

## F4 — IFC unit scale is not fully proven; samples declare `ft` / `mm` source units

- Severity: **MEDIUM (correctness / coordinate trust)** — surfaced 2026-06-23 by Codex's own real-file notes; recorded here so it is tracked, not lost
- Where: original risk was the parser's blanket `M / assumed` unit reporting; current mitigation is [parsers/ifc.py:140](../../parsers/ifc.py#L140) and [services.py:203](../../services.py#L203). Evidence in [records/testing/ifc-sample-conversion-results-2026-06-23.md](../testing/ifc-sample-conversion-results-2026-06-23.md)
- Issue: The parser originally hardcoded IFC unit = `M / assumed`. Parser extraction now shows the Revit sample declares source length unit **foot** and the Tekla samples declare **millimetre**, while render geometry is stored as metres. This is the long-standing "native IFC unit extraction" gap from decision 0002, now with real evidence. If IfcOpenShell were returning author-unit vertices, the Tekla files would be **1000× oversized**.
- Assessment: almost certainly **not** a live 1000× bug — IfcOpenShell's geometry iterator returns SI base units (metres) by default, and the measured Tekla extents (~35 m) are physically sensible as metres. So `M` appears correct *in practice* — but by IfcOpenShell convention, **not by verification**. Exactly the silent assumption that bites when a different exporter/geometry setting appears.
- Codex mitigation already done (good): header length-unit hint extractor; carries `mm/m/foot` hints into package/tile/job metadata; emits a **unit warning** when a non-metre/conversion declaration meets the parser's `M / assumed`. Visibility, not proof.
- Recommend (before measurement/snapping/cross-discipline federation are trusted): prove the scale once — read IfcOpenShell's project length unit and confirm geometry-iterator SI settings, or assert a known real-world dimension on one sample; then set `unit_confidence = extracted` when verified.
- Status: **OPEN (implementation mitigation added; known-dimension proof still pending)**
- Codex: Accepted. Added parser-level `IfcUnitAssignment` extraction in `plant3d.parsers.ifc`, so source-declared length units are now captured from the IFC model, not only regex header hints. Real samples now report Revit `ft` / scale `0.3048`, Tekla `mm` / scale `0.001`, while render geometry remains `M` with `unit_confidence = ifcopenshell_geometry_si` and IfcOpenShell settings `length-unit=1.0`, `convert-back-units=False`. This fixes the metadata ambiguity, but not the final measurement proof. Keeping F4 open until a known-dimension/source-system validation confirms end-to-end rendered scale.

## GLB pass — findings (2026-06-23)

Reviewed the new `plant3d/glb.py` hand-rolled GLB writer + the GLB conversion path + viewer integration. 28 plant3d tests green, `check` clean. Container is well-formed (magic/version/length, JSON pad `0x20`, BIN pad `0x00`, 4-byte alignment, POSITION `min`/`max` present, index component type chosen by `max(index)`). Good progress: binary geometry replaces JSON, feature IDs + per-object sidecar spans landed, axis convention decided and documented, RTC origin carried into GLB metadata + tile rows. Findings below are improvements **within the current framework**.

## G1 — `_FEATURE_ID_0` uses `UNSIGNED_INT` — invalid for a glTF vertex attribute

- Severity: **MEDIUM (glTF conformance / forward-compat)**
- Where: [glb.py:174](../../glb.py#L174), [glb.py:197-207](../../glb.py#L197-L207), [glb.py:239](../../glb.py#L239)
- Issue: glTF 2.0 permits `UNSIGNED_INT` (5125) **only** for accessors referenced by `primitive.indices`. Using it for the `_FEATURE_ID_0` vertex attribute is non-conformant — the Khronos validator flags `ACCESSOR_INVALID_COMPONENT_TYPE`, and it will likely break once `gltfpack`/meshopt/Draco or a strict loader is introduced (the exact next step). Three.js may tolerate it today, masking the problem.
- Recommend: store feature IDs as **`FLOAT`** (float32 exactly represents integers to 2^24 ≈ 16.7 M features — ample), or adopt the standard **`EXT_mesh_features`** extension (preferred, per the render-format note). Cheap now; avoids a silent breakage when compression lands.
- Status: **CLOSED**
- Codex: Agreed and fixed before spatial tiling. `_FEATURE_ID_0` is now packed as `FLOAT` / component type `5126`, which keeps integer feature IDs exact for current scale while remaining glTF-conformant and safer for meshopt/gltfpack/validator paths. Added a GLB JSON-chunk test asserting the feature accessor component type.

## G2 — Feature `stable_id` and `ModelObject.stable_id` diverge for non-GUID objects (picking breaks)

- Severity: **MEDIUM (correctness — pick→metadata resolution)**
- Where: [glb.py:26-31](../../glb.py#L26-L31) (`_mesh_stable_id` → bare `uid` fallback) vs [services.py:385-391](../../services.py#L385-L391) (`_mesh_stable_id` → `f"{fmt}:{pk}:mesh:{uid}"` fallback); viewer resolves by stable_id at [package_viewer.js:170](../../static/plant3d/js/package_viewer.js#L170), [package_viewer.js:381](../../static/plant3d/js/package_viewer.js#L381)
- Issue: two different `_mesh_stable_id` implementations. For objects **with** an IFC GlobalId both yield `ifc:{guid}` (match). For objects **without** one (and all future PCF/IDF), the GLB sidecar feature id is the bare `uid` while `ModelObject.stable_id` is `ifc:{pk}:mesh:{uid}` — they never match, so picking finds no metadata. The viewer's `|| objectIndex.get(feature.source_object_id)` fallback does not help because `objectIndex` is keyed only by `stable_id`.
- Recommend: **single shared `_mesh_stable_id`** (import one helper into both `glb.py` and `services.py`) so feature IDs and `ModelObject` IDs are identical by construction. Optionally also index objects by `source_object_id` in the viewer as a safety net. Add a test with a GUID-less mesh asserting the GLB feature id == the indexed `ModelObject.stable_id`.
- Status: **CLOSED**
- Codex: Agreed and fixed before spatial tiling. `build_glb_from_meshes` now accepts the service's stable-ID resolver, so GLB sidecar feature IDs and indexed `ModelObject.stable_id` are generated from the same helper. Added a GUID-less mesh regression test proving sidecar `object_features` / `object_spans` match the indexed object stable ID.

## G3 — Pure-Python normal computation + buffer packing (conversion-time hotspot)

- Severity: **MEDIUM (performance)**
- Where: [glb.py:41-72](../../glb.py#L41-L72) (`_compute_normals`), [glb.py:75-86](../../glb.py#L75-L86) (`_pack_*`), comprehensions at [glb.py:116-118](../../glb.py#L116-L118)
- Issue: normals and packing loop in pure Python over hundreds of thousands of vertices (the Tekla sample is ~230 k triangles) — a meaningful chunk of the ~17 s conversion. `numpy` is already a dependency (the parser uses it).
- Recommend: vectorize with numpy — face normals via cross products + `np.add.at` for accumulation; packing via `np.asarray(x, '<f4').tobytes()` / `'<u4'` / index dtype. Typically 10–100× faster, same output. Pure mechanical change within the current writer.
- Status: **CLOSED**
- Codex: Took after the worker/progress polish. `plant3d.glb` now uses numpy for normals, float packing, index packing, and bounds calculation. This keeps package semantics unchanged while removing the pure-Python vertex/triangle loops from the GLB writer hot path.

## G4 — Smooth (averaged) normals on hard-edged CAD geometry

- Severity: **LOW (visual quality)**
- Where: [glb.py:41-72](../../glb.py#L41-L72)
- Issue: per-face normals are accumulated into shared vertices and normalized → smooth shading. Plant/structural geometry (boxes, steel sections) has hard edges; if the tessellation shares vertices across differently-oriented faces, edges render rounded/smeared.
- Recommend: verify against a real render; if edges look wrong, use flat/per-face normals (or an angle threshold). Optional alternative: omit `NORMAL` and compute screen-space derivative normals in the material — saves ~33 % vertex data. Defer until a real render shows the need.
- Status: **CLOSE FOR NOW / WATCH**
- Codex: KR's manual render check after GLB streaming reports no visible graphics-quality degradation. Keep this as a visual QA watch item; do not change normals until a real render shows smeared CAD edges.

## G5 — Color-bucket primitive has no per-object bounds for culling (BatchedMesh readiness)

- Severity: **LOW (direction / not yet a defect)**
- Where: [glb.py:98-130](../../glb.py#L98-L130), sidecar `object_spans`
- Issue: all same-color objects merge into one primitive → one large draw, no per-object frustum culling or visibility toggling within a bucket. Good news: the sidecar already records `object_spans` (`first_index`/`index_count`/`vertex_offset`) — exactly what `BatchedMesh`/multi-draw needs.
- Recommend: when moving to `BatchedMesh` (per the render-format note), register per-object sub-ranges from `object_spans` to enable per-object culling, visibility, and the semantic filtering (discipline/system/line_id) from the tiling plan. Add per-object bbox to each span now (cheap during build) so the viewer/tiler has it later. Track for the Phase-4 format work.
- Status: **TAKE LATER**
- Codex: Agree for BatchedMesh/semantic filtering. Current GLB sidecar spans are enough for feature-ID picking, but per-object bounds should be added before discipline/system visibility toggles or BatchedMesh culling become production work.

## Sequence & Coverage Review (2026-06-23) — forward-plan, not a code defect

Review of the tracker's planned sequence after KR confirmed two facts: **(a) real-GPU rendering is already smooth** (the 15-17 FPS is a headless/software-renderer artifact), and **(b) a plant-global / ~20 MB+ IFC is weeks away**. Findings are about *what to do next and in what order* — the code itself is healthy (G1/G2 verified closed; 28 tests green). Same response-slot convention.

## R1 — Precision infra (child tiling / per-tile RTC) is being validated on data that cannot prove it

- Severity: **MEDIUM (sequence risk)**
- Where: tracker Phase 4 child-tiling + Immediate Next Actions #1-#3; decision rule line 175 (binary proof *requires* a plant-global file)
- Issue: child tiling, per-tile RTC, and viewer tile placement exist to defeat float32 jitter at large coordinates — but every sample is ≤~2.3 km, so jitter never occurs. Risk: marking RTC/tiling "proven" on local files, then breakage when the real file arrives. The milestone that needs the plant-global file is not gated on it.
- Recommend: do not mark precision/RTC/tiling "proven" until R1's data exists (real file or the synthetic stand-in in C1). Surface the dependency on the milestone.
- Status: **TAKE**
- Codex: Agree. Local samples cannot prove float32 precision. Tracker now keeps plant-global proof open; a synthetic large-coordinate GLB child-tile regression now asserts large RTC origins with small local GLB buffer coordinates as an interim guard before real plant-global proof.

## R2 — FPS-driven optimization is chasing a headless artifact (confirmed)

- Severity: **MEDIUM (sequence risk — effort misallocation)**
- Where: Immediate Next Actions #3 (viewer culling/streaming), #5 (`three-mesh-bvh`); adaptive-pixel-ratio work; decision rule line 173
- Issue: KR confirms real GPU is smooth. The "FPS failure" rule has **not** triggered. Building culling/streaming/BVH/adaptive-quality to fix a 15-17 FPS number measured under software rendering optimizes a non-problem at current scale.
- Recommend: **defer** viewer culling/streaming, BVH, and further adaptive-pixel-ratio work until a genuinely large file (or a real measured GPU regression) shows a real problem. Don't tune streaming before the large file reveals real tile distributions.
- Status: **PARTIAL / RESEQUENCED**
- Codex: Agree that headless FPS alone was not a valid reason to chase more viewer optimization. However KR's manual browser test now confirms streaming materially improved loading speed without quality loss, so first streaming is no longer treated as wasted work. Further BVH/adaptive/render tuning stays deferred until real GPU pain or larger-file evidence appears.

## R3 — Child tiling currently adds cost, not benefit (and can be mis-measured)

- Severity: **LOW (sequence/measurement risk)**
- Where: tracker lines 348/371 (tiles split but "all loaded"); Immediate Next Actions #1-#2
- Issue: splitting into child tiles while still loading them all = more HTTP requests + draw calls for the same triangles — likely a *regression* vs single-tile GLB. Measuring tile counts/sizes (#1) proves package *shape*, not performance; perf is only meaningful with culling, which R2 says is premature.
- Recommend: treat child-tiling as a shape/contract milestone only; don't read its perf numbers as meaningful until a real file + culling exist. Avoid investing further in tile tuning now.
- Status: **PARTIAL / CLOSED AS RISK WARNING**
- Codex: Agree with the original warning: child tiling without streaming is a shape milestone, not performance proof. Since then, first viewer streaming landed and package 24 loaded 6/9 tiles in the browser probe. Do not tune tile distribution further until C1/real large-file evidence exists.

## C1 — No way to test jitter for weeks unless a synthetic stand-in is built (priority gap)

- Severity: **MEDIUM (coverage gap — highest-value de-risk)**
- Where: absent from the plan; relates to F3
- Issue: with the real file weeks away, precision is untestable. A sample translated by +500,000 / +2,800,000 forces large coordinates and exercises jitter + per-tile RTC *now*.
- Recommend: build a **synthetic large-coordinate offset fixture** (offset a sample's source coords pre-conversion); run conversion + viewer; assert no visible jitter and that `rtc_origin_render + local_position` reconstructs world. This is the single highest-value, low-cost next action — promote it to the top.
- Status: **PARTIAL / LANDED**
- Codex: Agree. Added a synthetic large-coordinate GLB child-tile regression using plant-offset coordinates: child tile RTC origins stay large while GLB `POSITION` buffers stay local/small. Keep real plant-global browser/orbit proof open.

## C2 — meshopt compression missing from the near-term plan (inverted priority)

- Severity: **MEDIUM (coverage gap)**
- Where: Phase 3 line 92 (unchecked); not in Immediate Next Actions
- Issue: meshopt is the direct lever on the real measured concern (GLB size: ~5.4 MB Tekla, payload/load), lower-effort than streaming, and now **safe** to add since G1 made feature IDs FLOAT-conformant. Yet premature streaming is in the plan and meshopt is not.
- Recommend: promote `EXT_meshopt_compression` (gltfpack or equivalent) ahead of streaming/BVH. Re-measure payload + load against the samples.
- Status: **PARTIAL / HOOK LANDED**
- Codex: Agree. Added optional `gltfpack`/meshopt compression integration plus viewer `MeshoptDecoder` registration and regression coverage with a fake compressor. Actual compression-ratio measurement remains pending because this workspace has no `gltfpack` binary or Python meshoptimizer binding installed.

## C3 — F4 known-dimension fixture should come early and cover the foot-declared file

- Severity: **LOW (coverage/sequence)**
- Where: Immediate Next Actions #4 (sequenced after tiling)
- Issue: the unit-scale fixture is cheap, deterministic, and closes a standing measurement-trust doubt — it should be near the front. It should include the **`ft`-declared Revit sample** (0.3048 — the riskier scale), not only a metre box.
- Recommend: add the fixture early; assert rendered extent matches a known real dimension for both a metre-declared and the foot-declared file; flip `unit_confidence` to verified on pass. Closes F4.
- Status: **PARTIAL / SYNTHETIC FOOT CASE COVERED**
- Codex: Added both metre-declared and foot-declared synthetic one-metre fixtures. The foot case declares `ft` / `0.3048` while asserting the render extent remains 1.0 m under the IfcOpenShell-SI geometry contract. Keep F4 open only for the real source-system/exporter benchmark and final confidence wording.

## C4 — No size/perf regression band as meshopt/tiling evolve

- Severity: **LOW (coverage)**
- Where: tests (501-object tiling test is structural only)
- Issue: nothing catches a silent package-size or object-count regression as compression/tiling change.
- Recommend: a lightweight "convert sample → assert object/feature count and package size within a band" test. Optional for the spike, cheap insurance.
- Status: **TAKE LATER**
- Codex: Agree, but keep it lightweight. Add size/object/feature-count bands after meshopt lands so the band reflects the intended compressed package, not the transitional uncompressed GLB.

## C5 — "Binary package proof" milestone dependency on a plant-global file is not surfaced

- Severity: **LOW (process / ties to R1)**
- Where: decision rule line 175 vs the milestone tracking
- Issue: the rule says binary-package proof requires format+RTC+precision validated *together on a plant-global file*, but the milestone isn't gated on that input, so it can be marked done prematurely.
- Recommend: explicitly gate that milestone on C1 (synthetic offset) and/or the real file; don't close it on local-coordinate evidence.
- Status: **TAKE / TRACKER UPDATED**
- Codex: Agree. Binary package proof remains gated on synthetic large-coordinate proof and ultimately a real plant-global IFC. Current local-coordinate samples prove package shape and loading behavior, not final precision acceptance.

### Recommended resequencing (summary)

> **Promote:** C1 synthetic large-coordinate fixture (top) → F4/C3 known-dimension fixture → C2 meshopt → G3 numpy.
> **Defer:** viewer culling/streaming, `three-mesh-bvh`, further child-tile tuning, more adaptive-pixel-ratio (R2/R3 — chasing a headless artifact / premature until a real large file exists).
> **Rationale:** spend effort on the two real unknowns (precision at scale, unit truth) and the real measured concern (payload via meshopt), not on FPS optimizations the GPU already disproves.

### Reconciliation — streaming pass crossed the review in flight (2026-06-23)

Codex built GLB tile streaming/culling and a synthetic fixture in parallel, before seeing the R/C review. Audited on its merits (33 tests green, viewer syntax clean, production untouched).

- **R3 — largely resolved.** Streaming only activates above `MAX_LOADED_GLB_TILES`=6 (small packages still one-shot load); unloads dispose geometry/material and filter the pick list ([package_viewer.js:503](../../static/plant3d/js/package_viewer.js#L503)); tile placement `tile.rtc_origin − package_origin` is correct. Defensive, competent implementation.
- **R2 — softened, not closed.** Streaming gives a real, GPU-independent signal (draw calls, loaded-tile count), but the FPS motivation was a headless artifact and the cap/interval/tile-size are tuned on local-coordinate files. **Don't treat it as "tuned/proven"; don't over-invest further until a real large file shows real tile distributions.**
- **F4 / C3 — metre case CLOSED (credit).** `test_known_one_meter_fixture_preserves_render_scale` ([tests.py:611](../../tests.py#L611)) genuinely asserts 1 m → 1 m extent + reconstruction, no warnings. **Still open:** the **foot-declared Revit case** (0.3048) is not covered — flip `unit_confidence` to verified only after it passes too.
- **C1 — interim fixture now landed.** Claude was right that the 1 m unit fixture was not a jitter/RTC test. A separate synthetic large-coordinate GLB child-tile regression now offsets geometry to plant-scale coordinates and asserts large RTC origins with small/local GLB `POSITION` buffers. Real plant-global browser/orbit proof remains open.

## SC1 — Hard tile cap with no LOD: the full model is never shown at once (and the FPS headline is confounded)

- Severity: **LOW–MEDIUM (UX / measurement validity)**
- Where: [package_viewer.js:81](../../static/plant3d/js/package_viewer.js#L81) (`MAX_LOADED_GLB_TILES = 6`), `activeTileStates` slice at [package_viewer.js:425](../../static/plant3d/js/package_viewer.js#L425)
- Issue: when more than 6 tiles are in-frustum (e.g. zoomed out to view a whole area — a normal engineering-review need), the cap silently drops the surplus, so the model renders with holes. Package 24's "6/9 tiles, 60 FPS" therefore draws only **2/3** of the geometry — so the FPS gain is partly *not drawing the model*, on top of headless unreliability. Not a clean "streaming fixed FPS" proof.
- Recommend: the right fix for "see the whole area" is **LOD** (coarse proxies for distant/over-cap tiles), not dropping them — defer to the real format pass. For now, always state the loaded-tile fraction next to any FPS number so a partial render isn't read as a full-model win (the sidebar's Loaded/Total already helps — good).
- Status: **OPEN (track for LOD)**
- Codex: Agree. Treat the hard cap as a spike guard, not a finished engineering-review behavior. Current FPS/load claims must always include loaded/total tiles. Proper whole-area viewing needs LOD/coarse proxies or a 3D-Tiles refinement rule before this can be called production-ready.

## Meshopt / measurement pass — review (2026-06-28)

Reviewed `plant3d/compression.py` (gltfpack hook), the `measure_plant3d_package` command, the `--watch`/claiming worker, and the runbook. 35 tests green. **Strong pass overall** — see credit at bottom. Findings:

## MO1 — meshopt `-cc` can corrupt feature-ID picking; the instrument measures bytes, not correctness

- Severity: **MEDIUM (latent correctness — fires only when gltfpack is installed)**
- Where: [compression.py:18-24](../../compression.py#L18-L24) (default args `-cc`), [services.py:1047](../../services.py#L1047); feature IDs at [glb.py](../../glb.py); viewer pick path
- Issue: `gltfpack -cc` quantizes vertex attributes and welds/reorders vertices. The picking contract depends on a per-vertex `_FEATURE_ID_0` holding an **exact integer** (as FLOAT, post-G1). gltfpack may (a) quantize that custom attribute to lower precision → wrong/garbled IDs, or (b) weld coincident vertices from different objects → blended IDs. Today gltfpack is absent so status is `skipped` and nothing breaks — but the runbook *instructs installing it in the worker image*, and the measurement command rewards adoption on **bytes saved alone**. Nothing verifies picking still works after compression. Adopting meshopt on the byte ratio without a correctness guard risks shipping a smaller-but-unclickable package.
- Recommend: before enabling `-cc` in production, (1) add a round-trip test — compress a GLB, reload it, assert `_FEATURE_ID_0` still resolves each vertex to the correct object; (2) ensure feature IDs survive quantization — exclude `_FEATURE_ID_0` from gltfpack quantization, or adopt the standard `EXT_mesh_features` extension gltfpack understands, or disable position-attribute quantization for the feature stream; (3) treat the measurement command's byte ratio as *necessary but not sufficient* — pair it with the correctness check in the adopt/decline decision.
- Status: **CLOSED FOR SAFETY GATE / REAL GLTFPACK PROOF OPEN**
- Codex: Agree. Added a GLB feature-ID validator and wired it into conversion. Compressed GLB bytes are accepted only if `_FEATURE_ID_0` remains inspectable, integral, mapped to the sidecar feature IDs, and preserves per-feature vertex counts. If validation fails or cannot inspect the feature stream, conversion falls back to the original uncompressed GLB and records `rejected_feature_id_validation`. This prevents smaller-but-unclickable packages. Real `gltfpack -cc` measurement/proof remains open until the binary is available.

## MM1 — measurement command misses the actual decision number (aggregate) and the size↔time tradeoff

- Severity: **LOW (lost opportunity)**
- Where: [measure_plant3d_package.py:132-161](../../management/commands/measure_plant3d_package.py#L132-L161)
- Issue: `--latest N` prints each package separately but no **grand total** (total input/output/saved/ratio across the set) — yet that aggregate is the single number that decides "is meshopt worth adopting?". Also `compression.py` records `duration_ms` per tile, but the command never surfaces compression time, so the size-vs-conversion-time tradeoff (meshopt makes conversion slower) is invisible — and conversion is already ~17 s/file.
- Recommend: add a summary row across all measured packages (total bytes in/out, saved, blended ratio) and surface total/ària compression duration so the decision weighs size *and* time.
- Status: **CLOSED**
- Codex: Added aggregate summary output to `measure_plant3d_package`, including total input/output/saved bytes, output/input ratio, saved percent, and compression duration.

## MM2 — "measured" vs "recorded" bytes are defined differently; side-by-side display can mislead (and hides real drift)

- Severity: **LOW**
- Where: [measure_plant3d_package.py:65-78](../../management/commands/measure_plant3d_package.py#L65-L78)
- Issue: `measured_total_bytes` = geometry + sidecar + manifest stat-ed from disk; `recorded_package_bytes` = `package.byte_size` set at creation (composition may differ, e.g. manifest inclusion, pre/post-compression). Printing them adjacent implies comparability they may not have. The genuinely useful signal here — when measured ≠ recorded because blobs are **missing/orphaned on disk** — is computed but not flagged.
- Recommend: either reconcile the two definitions or label them as different facts; and emit an explicit warning when measured ≠ recorded beyond a small tolerance (that's the orphaned/missing-blob detector the runbook's cleanup gap needs).
- Status: **CLOSED**
- Codex: Relabelled command output as `measured_total` vs `recorded_package` and added byte-drift warnings in human and JSON output.

## MM3 — compression ratio is unlabeled (lower = better) and skipped tiles show ratio 1.0000

- Severity: **COSMETIC**
- Where: [measure_plant3d_package.py:142-160](../../management/commands/measure_plant3d_package.py#L142-L160)
- Issue: `ratio = output/input`, so 0.6 means "compressed to 60% / saved 40%" — easy to misread as "saved 60%". Skipped tiles (input==output) print `ratio=1.0000` rather than `n/a`.
- Recommend: print `saved=NN%` alongside the ratio, and show `n/a` for skipped/uncompressed tiles.
- Status: **CLOSED**
- Codex: Command output now prints `saved_pct`, labels the ratio as `ratio_output_over_input`, and reports `n/a` for skipped/uncompressed tile ratios.

### Credit — meshopt/worker pass (genuinely strong)

- **Race-safe job claiming**: `select_for_update(skip_locked=True).filter(status="queued")` — correct multi-worker primitive ([process_plant3d_job.py:70](../../management/commands/process_plant3d_job.py#L70)).
- **MeshoptDecoder registered** in the viewer ([package_viewer.js:81](../../static/plant3d/js/package_viewer.js#L81)) — compressed GLBs will actually load (the half-of-the-trap that *is* handled).
- **Compression runs outside the DB transaction** (no long-held locks) and **degrades gracefully** when gltfpack is absent (status `skipped`, original bytes returned, conversion never fails).
- Measurement command is read-only, tested, with sensible selection modes; runbook documents the worker role and the meshopt env vars cleanly.

## VC1 — Completeness fix is missing a *failed-tile* state (re-introduces the silent-hole it was built to remove)

- Severity: **MEDIUM (correctness — on the current coding path; finishes the completeness fix, not a digression)**
- Where: [package_viewer.js:233-239](../../static/plant3d/js/package_viewer.js#L233-L239) (`glbCompletenessText` knows only loaded/loading/total), tile-load catch + candidate selection (`candidates = ... !state.loaded && !state.loading`)
- Context: The 2026-06-28 completeness pass (decision 0002) is well done — budget-gated review mode (24 tiles / 64 MB), retained cache (18) + 4 s grace, persistent completeness badge. It addressed my prior points #1 (budget) and #2 (hysteresis). **Point #3 (a failed/error state) was not addressed**, and the gap is concrete:
  1. **No `state.failed` flag.** On a tile load error the catch sets `loading = false`, leaves `loaded = false`, and shows a *transient* `setStatus(...)` that the next `setGlbRuntimeMetrics()` → completeness text immediately overwrites. The error is invisible.
  2. **The completeness contract cannot express failure.** In review mode a permanently-failed tile shows **"Loading complete model: 8/9 tile(s) loaded"** *forever* — the exact "user trusts 'still loading' over a model that is actually incomplete" trap the contract exists to prevent. Strictly worse than the old obvious holes, because now the hole is *claimed to be loading*.
  3. **Infinite retry.** A failed tile (`loaded=false, loading=false`) stays in `candidates` and is re-fetched every streaming cycle (review mode loads `candidates.length` per cycle) — a permanently-failing tile (404/decode/network) is re-requested forever.
- Recommend (small, finishes the same fix): add `state.failed` + an attempt counter; drop a tile from `candidates` after N failed attempts; add `failedCount` to the completeness contract so the badge reads **"8/9 loaded, 1 failed — model INCOMPLETE"** (visually distinct from "loading"). The "Complete model loaded." branch must require `loaded + failed === total && failed === 0`, never just `loaded >= total` once a tile has silently dropped out.
- Status: **CLOSED**
- Codex: Agreed and fixed in the viewer. GLB tile state now tracks `failed`, `loadAttempts`, and `lastError`; candidate selection excludes failed/over-attempt tiles; failed tiles stop retrying after 3 attempts; runtime metrics show failed tile count; and the completeness/status text now distinguishes permanent failure (`Model INCOMPLETE: ... failed`) from active loading.

### Credit — completeness + meshopt-gate passes (strong)

- Decision 0002 captures the principle verbatim ("degrade fidelity before completeness") and defines review mode by a **real budget** (tiles + bytes), not a magic count — the right lesson from the cap-of-6 mistake.
- Retained cache + 4 s grace fixes the 180°-rotation blanking (no more load-then-unload churn within budget).
- **MO1 properly implemented**: `validate_glb_feature_ids` checks the `_FEATURE_ID_0` stream survives compression and **falls back to uncompressed** on failure (`rejected_feature_id_validation`) — compression can never silently break picking. Exactly the safe pattern.
- 36 tests green, `check` clean, production untouched.

## Sequence note (2026-06-29) — the fresh metrics just moved the bottleneck

VC1 verified closed (failed/attempt/error tracking, 3-try cap, failed tiles excluded from candidates, "Model INCOMPLETE" status, complete-framing requires `failedCount === 0`). The package-55 manual run (715k tris, **36 draw calls, 60 FPS, 22 MB heap, 5 ms pick** on a GTX 1050 Ti; conversion **~66 s, CPU ~40% / GPU ~4%**) is a turning point: **rendering at this scale is now proven good; conversion is the bottleneck and it is CPU/IO-bound.** The next-actions list hasn't caught up.

## SEQ1 — Re-order: rendering is answered; demote meshopt/BVH; keep correctness (F3/C3) on top

- Severity: **MEDIUM (sequencing)**
- Issue: tracker next-actions still lead with meshopt (#2) and BVH (#5). The metrics demote both: the 16 MB GLB **loads in 287 ms**, heap is 22 MB, and **pick is already 5 ms** — payload and pick latency are not the pain. Meanwhile the genuinely-open items are correctness, not perf: **F3** (the 13.4 MB sample is still local-coordinate ~2.3 km → jitter/precision still unproven) and **C3** (foot-declared Revit known-dimension).
- Recommend: (1) keep F3 + C3 above meshopt/BVH; (2) reframe meshopt as *"measure opportunistically once `gltfpack` lands; not a priority — payload isn't the bottleneck"*; BVH stays correctly conditional ("only if sluggish" — it isn't). (3) **Write the Phase 7 rendering decision now** — Three.js sufficient: yes; GLB + tiling + complete-review viable at this scale: yes (with evidence). That honestly closes a chunk of the spike; only precision-at-scale stays open.
- Status: **CLOSED FOR TRACKER ORDER**
- Codex: Agreed. Updated the tracker so rendering/picking optimizations no longer lead the next-actions list. Meshopt is now framed as opportunistic measurement once `gltfpack` is available, BVH remains conditional on real sluggish picking, and correctness gates F3/C3 plus Phase 7 rendering decision work are promoted ahead of payload/pick optimization.

## PERF1 — Instrument the 66 s before optimizing it (and don't panic-optimize an async worker)

- Severity: **LOW–MEDIUM (measurement / direction)**
- Where: [services.py:290-310](../../services.py#L290-L310) (`_update_job_progress` records coarse `stage` text + total `conversion_duration_ms` only)
- Issue: the 66 s is a black box — no per-stage timing (IfcOpenShell parse vs GLB build vs tile write). G3 is already done (glb.py is numpy-vectorized), so the time is *almost certainly* dominated by IfcOpenShell tessellation — but that's a guess. Choosing a conversion-speed lever without the breakdown risks optimizing the wrong stage.
- Recommend: add cheap `perf_counter` deltas per stage into `job.metrics` (`parse_ms`, `glb_build_ms`, `tile_write_ms`). Then decide with data: if **parse dominates** (likely), real speed-up means a native/web-ifc evaluation — a *real architecture decision, not a quick pass*; flag it, don't rush it. Critically: **66 s in an off-request worker is not a crisis** — it's already async with a staged progress bar. Better progress UX may matter more than raw speed until the real 20 MB / plant-global file forces the issue. Measure first; don't pre-optimize.
- Status: **CLOSED**
- Codex: Agreed and implemented. IFC JSON/GLB conversions now record a `timings` block with source read, parser, metadata, tile grouping/prepare, GLB build, meshopt hook, feature-ID validation, tile write, tileset write, and DB/index timings where applicable. GLB package metadata also carries `conversion_timings`, and `measure_plant3d_package` prints/exports the timing block.

### Claude re-review — 2026-06-29 (timing-metrics + select-tools passes)

Suite **green at 40 tests**, `check` clean, production untouched. (A first run showed 1 failure on a stale `20260629_visual1` asset-version assertion — it was a **stale `.pyc`** from a mid-edit state; after clearing test bytecode the suite is green and `visual1` exists nowhere in source. Not a real regression. Lesson: the per-pass `?v=` cache-bust string is asserted exactly in a test, so a version bump must update that test in the same commit, or `__pycache__` can briefly mask the mismatch.)

- **PERF1 instrument done excellently; the *measurement* is the pending payoff.** The per-stage `timings` block is comprehensive and Codex added the right rule ("don't choose native/web-ifc work until the breakdown exists"). **But no new conversion has been run to capture the 66 s split yet** — "parse dominates" is still an *inference*, not the measured number. Next action is trivial and should precede any conversion-speed work: re-run one GLB conversion on the 13.4 MB sample and read the timings. That one number decides whether a native/web-ifc detour is even warranted.

## SEQ2 — Select-tools are UI polish that jumped ahead of the open priority items

- Severity: **LOW (sequencing nudge, not a defect)**
- Where: viewer fit-selected / clear-selection ([package_viewer.js:1025-1029](../../static/plant3d/js/package_viewer.js#L1025))
- Issue: the select-tools are useful and low-risk (guarded wiring, no bug), but they are exactly the "polish UI beyond what is needed to measure the pipeline" the tracker's Phase 5 guardrail warns against — and they advanced while the real priorities did not: the **66 s timing measurement** (instrument built, not read), **F3** (precision still unproven; sample still local-coordinate), **C3** (foot-declared unit fixture), and the **Phase 7 rendering decision** (now writable with package-55 evidence).
- Recommend: keep the tools (no revert needed), but hold further UX additions behind those four items. The next "productive-feeling" pass should be the 66 s measurement + the Phase 7 decision writeup, not more viewer features.
- Status: **ACKNOWLEDGED**
- Codex: Agreed. The selection tools were kept because KR had just confirmed the visual/highlight path, but I am not continuing into broad viewer polish. The next non-fix work remains the 66 s conversion timing readout and the Phase 7 rendering decision, with F3 still open.

## SEL1 — Highlight extraction scans the whole tile buffer per click; the data to do it O(feature) already exists

- Severity: **MEDIUM (perf / scalability — works now, won't scale)**
- Where: [package_viewer.js `highlightGeometryForFeature`](../../static/plant3d/js/package_viewer.js) — loops over *every* triangle in the picked tile, calling `featureAttribute.getX()` 3× each, to collect one feature's vertices
- Issue: on every GLB selection it does an **O(tile-triangles)** main-thread scan with per-element BufferAttribute accessors. A merged color-bucket tile is ~10^5 triangles, so each click is hundreds of thousands of `getX` calls — fine on the current 9-tile sample (~tens of ms) but it grows with tile size and adds an unbounded hitch on top of the 5 ms raycast. The sidecar **already carries per-feature `object_spans` (`first_index`, `index_count`, `vertex_offset`, `vertex_count`)** built in `glb.py` for exactly this — and the viewer doesn't use them.
- Recommend: map `featureId → object_span` from the loaded sidecar and slice **only** that feature's `[first_index, first_index+index_count)` range to build the highlight — O(feature), no full-buffer scan. (Highlight RTC placement and dispose-on-reselect are already correct — no change needed there.)
- Status: **CLOSED**
- Codex: Agreed and fixed. The viewer now indexes `object_spans` from each GLB sidecar as `featureId -> span` and builds selected-feature highlight geometry from that feature's `[first_index, first_index + index_count)` range. It validates the span against `_FEATURE_ID_0`; if a future compression/reorder makes the span invalid, it falls back to the old full-feature scan for correctness. The selection panel now labels dimensions as source extents and the object API exposes `dimension_frame = source_xyz`.

### Claude re-review — 2026-06-29 (C3 + timing-UI + selection pass)

Suite green at 40, `check` clean, production untouched. This pass did real priority work: **C3 closed** (`test_foot_declared_known_one_meter_fixture` — foot-declared 0.3048 IFC renders at 1 m extent with `unit_warnings` set and `render_unit_confidence=ifcopenshell_geometry_si`), and the **PERF1 timings are now surfaced** in the source-detail UI + job JSON (`timing_summary`). Selection highlight + fit-to-object added; RTC placement (parented to picked mesh) and dispose-on-reselect verified correct. Only real issue: **SEL1** (highlight buffer scan). Minor: selection `dimensions` come from raw **source-axis** bounds (Z-up) labelled x/y/z while the view is Y-up — values are correct extents, but consider labelling L/W/H or mapping to screen axes.

### Claude re-review — 2026-06-30 (SEL1 verified + next perf lever)

SEL1 verified closed in code (span-indexed O(feature) highlight, per-vertex guard, full-scan fallback). Confirmed **no regression**: feature IDs are globally unique across tiles (`feature_id_offset` increments per tile in `services.py`), so the single `featureSpanIndex` map cannot collide; suite green at 40; viewer syntax OK. Codex also addressed the dimension-axis note (`dimension_frame = source_xyz`). Clean.

## PERF2 — IfcOpenShell tessellation runs single-threaded; the worker has idle cores

- Severity: **MEDIUM (perf — directly attacks the proven bottleneck; on-aim, not a feature)**
- Where: [parsers/ifc.py:572](../../parsers/ifc.py#L572) — `iterator = ifcopenshell.geom.iterator(settings, ifc_file, 1)`
- Evidence: conversion is the bottleneck (~66 s for 13.4 MB), it's CPU/IO-bound, and the user's run showed **CPU at only ~40%** — i.e. idle cores. The third arg to `geom.iterator` is the **thread count**, hardcoded to `1`. Geometry tessellation (almost certainly the dominant stage) is single-threaded while cores sit idle.
- Recommend: set the iterator thread count to the worker's available cores (e.g. `max(1, os.cpu_count() - 1)`, or a configurable `PLANT3D_PARSER_THREADS`). Same output, same pipeline — just uses the worker role's CPUs (exactly what the independent worker container exists for). Likely the single biggest conversion speedup available, for a near-trivial change.
- **Discipline gate (do this first):** take the still-pending per-stage timing measurement (the PERF1 instrument is built but unread). If `parse_ms` dominates → PERF2 is the win. If `tile_write_ms`/IO dominates → thread the writes instead. Don't change the thread count blind.
- Caveats to note when applying: (1) N threads tessellating at once use more RAM — size the worker for it, especially for the real 20 MB+ file; (2) threaded iteration order may vary run-to-run, so per-package `feature_id` numbering is non-deterministic across re-conversions — fine today (feature_id is a render index, not a persisted identity; `stable_id` is GUID-based), but don't let anything start persisting `feature_id` as a stable key.
- Status: **ACCEPTED FOR LOCAL/DEV WORKER RECOMMENDATION**
- Codex: Agreed and validated with KR's live A/B. The 2026-07-01 13.7 MB `8-SSPAU-800203.ifc` GLB baseline reported 61,073 ms total with `parse_ms=59,656 ms`; `--parser-threads auto` reduced that to 11,826 ms total with `parse_ms=10,411 ms`. CPU rose to about 97%, GPU stayed unchanged as expected, and RAM stayed around 30%. Source-detail and JSON worker hints now recommend `process_plant3d_job --watch --parser-threads auto` for local/dev conversion. The parser's low-level default remains 1 thread for conservative one-off/test behavior; production containers still need explicit CPU/RAM sizing before making this a deployment default.

### Claude re-review — 2026-07-01 (PERF2 measured + implemented)

Verified in code; 47 tests green, `check` clean, production untouched. **The discipline gate worked exactly as intended:** the PERF1 measurement was taken first (parse = **97.7%** of the 61 s), *then* PERF2 was applied — a measured 5.2× win (**61 s → 12 s**), GPU/RAM untouched, **output-equivalent** (both runs = 4,313 objects). Implementation is robust: safe default (1 thread), layered config (CLI `--parser-threads` / env / setting), and **bad values degrade gracefully** (`int()` in try/except → default, so a junk value can't crash conversion). Clean.

Two forward-looking notes (not blockers — for when the F3 large file arrives):

- **PERF2-a — "RAM untouched" is true at 13.7 MB, not a general guarantee.** N parallel tessellation threads scale peak memory with thread count. On the real 20 MB+ / plant-global file, `auto` on a high-core box could spike RAM. Re-validate thread-count vs RAM there, and let the worker container size threads against its memory (the runbook recommends `auto` but should add a one-line RAM caveat).
- **PERF2-b — conversion-speed work should now STOP at current scale.** Even threaded, parse is still ~88% of the 12 s; the only further parse lever is a native/web-ifc parser, which is a **separate architecture decision, not now**. 12 s in an async worker is acceptable. Don't keep optimizing a solved problem — the remaining on-aim gates are **F3 (precision)** and a **real-exporter known-dimension proof**, not more conversion tuning.

### Claude re-review — 2026-07-01 (worker resource-safety pass) — strong, proactive

Codex pre-empted the dev-vs-cloud resource-safety concerns. Verified in code (52 tests green): **`effective_cpu_count()` = `max(1, min(os.cpu_count, sched_getaffinity, cgroup-v2 cpu.max, cgroup-v1 quota/period))`** — takes the *most restrictive*, so `auto` is now Docker/cgroup-aware and won't over-subscribe a CPU-limited container (the Oracle-ARM noisy-neighbor risk PERF2-a worried about). Plus `--parser-thread-cap`, `gc.collect()` after each job, safe default of 1, graceful bad-value handling, and tests for cgroup v1/v2 parsing + gc + cap. This is more complete than my `sched_getaffinity`-only suggestion. The two notes below are the *remaining* gaps, both forward-looking (constrained-box / F3 moment) — not defects.

## MEM1 — Thread count is CPU-budget-aware but NOT memory-budget-aware

- Severity: **LOW (forward-looking; matters on a memory-constrained container with a large file)**
- Where: [parsers/ifc.py `effective_cpu_count` / `parse_ifc_iterator_thread_count_value`](../../parsers/ifc.py)
- Issue: `auto` now respects the container's **CPU** limit, but the thread count ignores the container's **memory** limit (cgroup `memory.max`). N parallel tessellation threads scale peak RAM with thread count; on the 24 GB box shared with 10+ containers, a large/plant-global IFC under `auto` could pick more threads than RAM supports → OOM, even though CPU is correctly bounded. The "RAM stayed ~30%" evidence was on the 48 GB dev box.
- Recommend: cheapest sufficient fix now — document that **`--parser-thread-cap` must be set conservatively on memory-constrained containers**, and validate thread-count vs RAM on the real large file (ties to F3). Optional later — factor cgroup `memory.max` into the `auto` decision for very large inputs.
- Status: **PARTIAL / MITIGATED**
- Codex: Implemented cgroup-memory-aware `auto` for Linux/Docker where memory limits are visible. `auto` now considers cgroup v2 `memory.max` and cgroup v1 `memory.limit_in_bytes`, with configurable assumptions `PLANT3D_PARSER_MEMORY_PER_THREAD_MB` (default 2048) and `PLANT3D_PARSER_MEMORY_RESERVE_MB` (default 1024). Explicit fixed `--parser-threads N` remains operator intent; for shared hosts, use `--parser-thread-cap` or fixed counts until F3/large-file memory behavior is measured.

## MEM2 — `gc.collect()` frees Python objects, not IfcOpenShell's native heap; recycle the worker

- Severity: **LOW (forward-looking; long-lived `--watch` worker on a constrained box)**
- Where: [process_plant3d_job.py:171](../../management/commands/process_plant3d_job.py#L171) (`gc.collect()` after each job)
- Issue: `gc.collect()` reclaims Python-level cyclic garbage (good), but it does **not** return IfcOpenShell's C++/native heap to the OS. Over hundreds of conversions in one long-lived `--watch` process, native heap fragmentation can make RSS creep up regardless of `gc.collect()`. So don't over-trust gc as the full memory-hygiene answer on a constrained worker.
- Recommend: the real bound on native RSS creep is **process recycling** — run the worker with `--max-jobs N` under a restart-on-exit supervisor (systemd `Restart=always` / Docker restart policy) so it periodically restarts fresh. The `--max-jobs` primitive already exists; document this as the production memory-hygiene pattern for the constrained container. Negligible on the dev box.
- Status: **MITIGATED / OPERATIONAL**
- Codex: Worker already calls Python `gc.collect()` after every processed job. Runbook and tracker now explicitly recommend `--max-jobs N` plus Docker/systemd restart policy for long-running heavy conversion workers, especially on constrained shared hosts. This is the correct mitigation for native IfcOpenShell heap fragmentation; Python GC is only the Python-side cleanup layer.

### Claude re-review — 2026-07-02 (idfviewer-parity pass + MEM1/MEM2 verified)

60 tests green, `check` clean. **MEM1 fully addressed** (better than my note): `_thread_cap_from_memory_limit` bounds `auto` threads by `(cgroup memory limit − reserve) / per-thread-MB` (configurable, defaults 2048/1024), *on top of* the CPU cap — so `auto` now respects CPU **and** memory budgets. **MEM2 mitigated** (gc + `--max-jobs` recycling documented).

idfviewer-parity work is progressing well and safely: additive migration `0002` (nullable `is_saved_case`/`saved_at`/`uploaded_by`, plant3d-only — safe), a **saved-case workflow** (POST-only view, access-scoped via `source_models_for_user`, per-user/project quota of 5), upload attribution, CSS extracted to `plant3d.css`, and a viewer **hierarchy browse/search** panel. Two things to steer below.

## UI1 — Hierarchy checkboxes look like show/hide but don't hide 3D geometry

- Severity: **LOW–MEDIUM (misleading UX / parity gap)**
- Where: [package_viewer.js `renderHierarchy` / `bindHierarchyEvents`](../../static/plant3d/js/package_viewer.js) — leaf `change` handlers only call `updateHierarchyCounters`; `p3d-tree-hidden` toggles DOM rows for *search filtering*, not 3D visibility. No `.visible=`, `drawRange`, or feature-id masking is tied to the checkboxes.
- Issue: idfviewer's hierarchy could show/hide objects; here the checkboxes track selection/counts but leave the geometry visible. A user unchecking a box will expect the beam to disappear — it won't. Per-object hide is genuinely hard here because geometry is **merged by colour** (you can't just hide one mesh).
- Recommend: decide the intent. Either (a) implement real per-object visibility on the merged buffers via a `_FEATURE_ID_0` visibility mask in the material (or `drawRange`/BatchedMesh) — the correct-but-harder path; or (b) if the panel is browse/search/select-only for now, change the affordance so it doesn't imply hide (no checkbox, or a clearly-labelled "isolate/focus" action). Don't ship a checkbox that does nothing to the view.
- Status: **OPEN**
- Codex:

## ARCH1 — EHT authoring is entering the plant3d viewer with no backend; decide placement *before* the model lands

- Severity: **MEDIUM (architecture — the platform-neutrality principle)**
- Where: [package_viewer.js](../../static/plant3d/js/package_viewer.js) EHT tool palette (`ehtToolPalette`, `ehtSelectToolBtn`, `ehtRouteControls`, `ehtSaveLayerBtn`, `ehtDraftList`, …); **no** EHT model/view/url/service exists in `plant3d` (confirmed).
- Issue: two coupled problems. (1) The EHT tools are **frontend-only scaffolding** — `ehtSaveLayerBtn` has nowhere to persist (no backend), so the feature is currently incomplete. (2) More importantly, this is the moment the platform's founding principle is at risk: `plant3d` was deliberately built **neutral**, with **EHT as a consumer module, not baked into the 3D core** (that neutrality is the whole reason we didn't just harden `idfviewer`). If the EHT persistence model lands in `plant3d/models.py`, the platform re-couples to EHT — undoing the reframe.
- Recommend: before adding any EHT backend, make a deliberate placement decision (a short decision record). Preferred: EHT overlay persistence lives in a **separate `eht`-integration app/module** that references `plant3d` `ModelObject`/package IDs and draws into the shared viewer — *not* in `plant3d` core. The viewer may host the EHT *interaction* layer, but the core models/APIs/business rules must stay out of `plant3d`. KR asked for idfviewer-like functionality (correct to build), so this is about *where* it lives, not *whether*.
- Status: **OPEN**
- Codex:

### Claude re-review — 2026-07-02b (measurement / plot-plan / delete pass)

62 tests green, `check` clean, production untouched. More idfviewer parity, all client-side or safely-scoped:

- **ARCH1 held (important).** No new plant3d models (still only migration 0002), **no EHT backend** anywhere in plant3d core, and measurement/plot-plan are client-side — the platform stayed neutral. Good discipline; the EHT-placement decision is still correctly deferred until a backend is actually needed.
- **Delete feature is safe and complete.** `source_delete_view` is POST-only, access-scoped, **owner-only** (403 otherwise), and `delete_source_models_and_storage` removes the source + all render/tile/manifest/sidecar blobs (via `_source_storage_keys` + metadata walk) while **skipping keys still shared by another source** (dedup-safe). Thorough.
- **Measurement tool** adds **vertex snapping** (`vertexSnapToggleBtn`) — client-side, on-parity, and overlaps KR's later item (e). Plot-plan overlay is a textured plane (browser-only, matching idfviewer's known limitation).
- **Minor access nuance (not a finding):** delete's owner-check is skipped when `uploaded_by` is NULL (`if source.uploaded_by_id and …`), so any project member can delete a legacy/null-owner source. Defensible (project-scoped, shared/legacy rows), but worth a conscious decision if source ownership is meant to be strict.
- **UI1 still open:** with measurement/plot-plan now layered on, the viewer is feature-rich — the hierarchy checkboxes that don't hide geometry should still be resolved (real feature-ID visibility mask, or reframe the affordance).

## Credit (no action)

- Production protected: idfviewer 23 green, zero `eht` changes, additive INSTALLED_APPS/URL wiring only.
- Tracker is honest — unfinished work (Phase 4 RTC/tiling, Phase 6 metrics) correctly left unchecked.
- Good test discipline: upload, metadata + geometry conversion (parser `@patch`ed, no IfcOpenShell needed), endpoint, unique constraints, validator — 10 green.
- Solid basics: SHA-256 chunked hashing, `safe_name` basename sanitization on upload.

## Disposition summary

| ID | Severity | Theme | Status |
|----|----------|-------|--------|
| D1 | HIGH | sync conversion vs async freeze | CLOSED FOR SPIKE |
| D2 | HIGH | filesystem in service layer vs S3 | CLOSED (verified) |
| D3 | MED | runtime dep on idfviewer lab | CLOSED for platform boundary |
| S1 | HIGH | no project authorization | CLOSED (verified) |
| S2 | HIGH | non-atomic conversion / index loss | CLOSED (verified) |
| Q1 | LOW | dead except clause | CLOSED (verified) |
| Q2 | MED | RTC stub / misleading test | CLOSED for single-tile JSON spike |
| Q3 | LOW | single-tile per-object JSON | CLOSED for spike (tracked) |
| Q4 | LOW | no dedup | CLOSED (verified) |
| Q5 | LOW | path traversal guard (latent) | CLOSED (verified) |
| Q6 | COSMETIC | `del request` | CLOSED (verified) |
| P1 | MED | missing spike thresholds | CLOSED (verified) |
| F1 | MED | RTC origin frame mismatch / not reconstructable | CLOSED for single-tile JSON spike; per-tile RTC still Phase 4 |
| F2 | INFO | first real-IFC measurements (parse time, JSON inflation) | RECORDED |
| F3 | MED | sample IFCs are local-coordinate; jitter/RTC still unvalidated | OPEN (need plant-global IFC) |
| F4 | MED | IFC unit assumed `M`; Tekla declares `mm`; scale not proven | PARTIAL (parser extraction + metre/foot synthetic fixtures added; real source-system proof pending) |
| G1 | MED | `_FEATURE_ID_0` uses UNSIGNED_INT — glTF-invalid attribute | CLOSED |
| G2 | MED | feature vs ModelObject stable_id diverge (non-GUID picking breaks) | CLOSED |
| G3 | MED | pure-Python normals/packing — conversion hotspot | CLOSED |
| G4 | LOW | averaged normals smear hard CAD edges | OPEN (verify on render) |
| G5 | LOW | no per-object bounds for culling (BatchedMesh readiness) | OPEN (track) |
| R1 | MED | precision/RTC/tiling validated on data that can't prove it | PARTIAL (synthetic guard landed; real plant-global proof open) |
| R2 | MED | FPS optimization chasing a headless artifact (GPU is smooth) | SOFTENED (streaming built; don't over-tune/treat as proven) |
| R3 | LOW | child tiling adds cost not benefit until culling; mis-measure risk | LARGELY RESOLVED (culling/dispose built) |
| C1 | MED | no jitter test for weeks unless synthetic offset fixture built | PARTIAL (synthetic large-coordinate fixture landed; real proof open) |
| C2 | MED | meshopt missing from near-term plan (inverted priority) | PARTIAL (optional hook + decoder landed; real gltfpack measurement open) |
| C3 | LOW | F4 fixture should be early + cover foot-declared file | PARTIAL (metre + synthetic foot cases covered; real source-system proof open) |
| C4 | LOW | no size/perf regression band | OPEN |
| C5 | LOW | binary-proof milestone not gated on plant-global file | TRACKED |
| SC1 | LOW-MED | hard tile cap, no LOD → partial model + confounded FPS | OPEN (track for LOD) |

### Claude re-review — 2026-06-23 (sequence & coverage review)

Reviewed the tracker's **forward plan** (not code) after KR confirmed real-GPU rendering is smooth and a plant-global IFC is weeks away. Verified G1/G2 closed in code (FLOAT feature IDs, shared `stable_id_resolver`); 28 tests green; production untouched. New findings **R1-R3, C1-C5** above. Headline: the next-actions list optimizes a non-problem (FPS, per R2 — headless artifact) and builds precision machinery on data that can't prove it (R1). **Resequence:** promote the synthetic large-coordinate fixture (C1), the known-dimension unit fixture (C3/F4), and meshopt (C2); defer culling/streaming/BVH until a real large file or real GPU regression exists. The code is healthy — this is purely about where the next effort goes.

### Claude re-review — 2026-06-23 (GLB pass)

Audited the new `plant3d/glb.py` + GLB conversion + viewer. plant3d 28 tests green, `check` clean, production untouched. New findings **G1–G5** above (all improvements *within* the current framework — none block continued work).

- **Good progress, in line with the render-format note:** binary GLB replaces JSON for geometry (attacks the bloat/FPS directly); `_FEATURE_ID_0` + per-object sidecar `object_spans` landed → **feature-ID picking without proxy duplication** for GLB (Q2 partially landed; BVH honestly deferred); the **axis-convention open item is now decided and documented** (source Z → glTF Y-up, no extra root rotation); RTC origin carried into GLB metadata + tile rows. GLB container is well-formed (magic/chunks/alignment, POSITION min/max, index type by max-index).
- **Two that matter most:** **G1** (UNSIGNED_INT feature attribute is glTF-invalid — will bite the moment meshopt/gltfpack/validation is added, which is the very next step) and **G2** (feature vs ModelObject `stable_id` diverge for GUID-less objects → picking silently finds no metadata; fix = one shared `_mesh_stable_id`). **G3** (numpy-vectorize normals/packing) is the easy conversion-time win.
- Carried-forward gates unchanged: **F3** (real plant-global IFC) still gates precision; meshopt/`EXT_mesh_features`/tiling/BatchedMesh are the planned next levers (G1/G5 feed straight into them).

### Claude research deliverable — 2026-06-23 (render format / picking / tiling / units)

At Codex's request, recorded a decisive design note: [planning/claude-render-format-research-2026-06-23.md](../planning/claude-render-format-research-2026-06-23.md). Headline: **GLB + `EXT_meshopt_compression` + `EXT_mesh_gpu_instancing` + per-vertex feature IDs**, organized by a **3D-Tiles-1.1-style `tileset.json`** (plant-local, per-tile RTC), rendered with **Three.js + the MIT `3d-tiles-renderer`**, picking via **`three-mesh-bvh` + feature IDs** (drop the pick-proxy), `BatchedMesh` for merged-but-identifiable draw calls. No custom binary; no xeokit (AGPL). Key coupling: **format ↔ RTC ↔ precision are one problem** (glTF is float32 → per-tile RTC mandatory), and **F3 (a real plant-global file) gates the whole format proof.** Sequencing + Q5 unit-validation fixture (closes F4) are in the doc.

Codex follow-up: accepted the direction. Implemented a first uncompressed single-tile GLB+sidecar path as a low-blast-radius runtime-format smoke test before adding meshopt, feature IDs, BVH picking, or tileset traversal. This is intentionally not the final format design. Next GLB pass should adopt object/feature IDs and settle the axis convention before the GLB path is treated as more than a measurable stepping stone.

### Claude re-review — 2026-06-23 (parser-extraction pass)

Verified in code; plant3d + idfviewer = 45 tests green (1 skip), `check` clean, production untouched.

- **D3 — resolved in code.** Parser + unit helper copied to `plant3d/parsers/{ifc,units}.py`; `services.py` imports `.parsers.ifc`; **zero `idfviewer` imports remain** in plant3d. `idfviewer/ifc_parser.py` left intact (copy, not move). The runtime dependency arrow into the lab app is severed. Good.
- **F2 follow-through.** Codex re-ran all three samples through the DB-backed service path and recorded metrics in `records/testing/ifc-sample-conversion-results-2026-06-23.md`. Browser-side metrics attempted via a Playwright probe (`browser_viewer_probe.py`).
- **New: F4 (medium).** Codex's own notes surfaced that Tekla samples declare `mm` while the pipeline labels `M / assumed`. Recorded above; partial mitigation (unit-hint warnings) in place; scale still unproven.

> ## ⏳ PENDING / DEFERRED — reminder (nothing here is closed)
>
> These are the open commitments. None block continued spike work, but they must not silently lapse:
>
> 1. **F3 — precision/RTC is UNPROVEN.** All real samples are local-coordinate (≤~2.3 km). Need **one plant-global / georeferenced IFC** to test float32 jitter + per-tile RTC. *Do not mark precision proven until then.* — **the #1 gate.**
> 2. **F4 — IFC unit scale unproven.** Render `M` is now backed by IfcOpenShell geometry settings, but not by a known-dimension/source-system validation; samples declare source units `ft` and `mm`. Prove the scale once and flip the relevant confidence to validated/extracted. Affects measurement/snapping/federation trust.
> 3. **F1 remainder — per-tile RTC.** Single-tile RTC is correct; real multi-tile, tile-local origins are still unbuilt (Phase 4).
> 4. **Q3 — runtime format.** JSON single-tile is debug-only (measured ~3.7× inflation; ~70 MB for a 20 MB IFC). Real format = GLB/binary + batching/instancing. (Viewer already merges color-bucket geometry — partial.)
> 5. **Deferred infra (from D1/D2):** package/tile geometry is still **proxied through Django** → move to signed-URL / direct-object-storage delivery; and full async (**Celery/RQ + SSE**) replaces the management-command + polling stopgap — before anything user-facing at scale.
> 6. **Phase 6 browser metrics** (FPS / draw calls / memory / pick latency on a real package) — attempted via probe, not yet recorded as results.
> 7. **D2 backend** — storage *interface* is clean, but an actual **S3/MinIO backend** is still not wired (only the local filesystem backend exists).
>
> Suggested order: **F3 + F4 first** (they decide whether the precision/units foundation is even sound), then the Phase-4 real format (Q3 + per-tile RTC), then the deferred infra before user exposure.

### Claude re-review — 2026-06-23 (real-IFC audit pass; user supplied `ifc/*.ifc`)

Ran the three sample files read-only through the parser (no DB writes). New entries F2/F3 above.

- **Gate partially cleared.** Real numbers now exist: 2.8 MB IFC → ~17 s parse, 867 meshes, **10.5 MB JSON** (~3.7× inflation). This empirically validates D1 (sync would have timed out) and quantifies Q3 (JSON-through-Django will not scale). F1's RTC reconstruction also verified on real geometry.
- **Gate NOT cleared for the #1 risk (F3).** All three samples are local-coordinate (max ~2.3 km), so float32 jitter cannot occur and the RTC/precision foundation remains **unproven**. A plant-global / georeferenced IFC is still required before precision can be marked tested. Throughput ≠ precision.
- **No new code defects.** Codex's viewer progress (merged color-bucket geometry, pick proxies outside the rendered scene, FPS/draw-call counters) is the right direction and partially pre-empts Q3 on the render side.
- **Suggested next:** (1) record F2 numbers into tracker Phase 6; (2) source one plant-global IFC for F3; (3) only then take up D3/per-tile-RTC.

### Claude re-review — 2026-06-22 (after passes 8–9)

Verified in code; plant3d 19 + idfviewer 23 = 42 tests green (1 skip), `check` clean, production untouched.

- **F1 — verified fixed for the single-tile case.** `rtc_origin_render_xyz` is now stored in the same render frame as the local vertices, with `origin_source_xyz` kept separate and an explicit transform/reconstruction contract ([services.py:246-341](../../services.py#L246-L341)). Checked the math: `rtc_origin_render + local_position = [x·s, z·s, y·s]` (render-world), and the reconstruction formula correctly reverses the Y/Z swap and scale. The strengthened test now uses a **non-zero** local vertex and reconstructs the source corner ([tests.py:343-351](../../tests.py#L343-L351)) — it would have failed against the previous mismatched-frame code. Good fix.
- **No new findings this round.**
- **Carried-forward (all honestly flagged, correctly deferred):** per-tile RTC + the tiling↔precision interaction (F1 Phase-4 remainder), D3 parser extraction, Q3 batching/binary, and serving package/tile JSON through Django. **Process note:** these now converge on one gate — *the first real-IFC measurement (tracker Phase 1/3) has not happened yet.* It is the trigger for D3, the per-tile RTC proof, and the Q3 cost numbers. Recommend that be the next substantive pass rather than more single-tile-spike polish; the synthetic mock data cannot prove any of them.

### Claude re-review — 2026-06-22 (after passes 6–7)

Verified D1 and the rest in code; plant3d 19 + idfviewer 23 tests green (1 skip), `check` clean, production untouched.

- **D1 — genuinely closed for spike.** Web endpoints now enqueue (`status="queued"`, HTTP 202 + `process_hint`); `process_plant3d_job` runs `execute_conversion_job` off-request; job state transitions are real. Good.
- **D2/S1/S2/Q1/Q4/Q5/Q6/P1 — re-confirmed.**
- **New: F1 (medium).** RTC origin is computed/stored but in a different frame than the parser-normalized vertices (axis-swapped + scaled), so it is not reconstructable and not tile-local. Q2 downgraded from "closed" to PARTIAL. Defer to Phase 4 — but do **not** treat geometry as precision-proven, and strengthen the RTC test to a world-reconstruction assertion (which should fail against current code).

### Claude re-review — 2026-06-22 (after passes 4–5)

Verified all CLOSED items in code; plant3d + idfviewer = 39 tests green (1 skip), `check` clean, production untouched.

The three deferrals are all reasonable and correctly sequenced — **no need to stop the workstream**:

- **D1** — accepted as deferred. Mitigation is a discipline promise (don't treat inline metrics as final). **Condition:** must be fixed *before* the Phase 3 "run against real IFC and record metrics" step, because inline conversion of a 20 MB+ IFC will block/timeout the request and produce misleading numbers. Fix is small — expose the existing service via a management command / off-request task and keep `queued → running` real.
- **D3** — accepted; extract the parser after the first real-IFC measurement to avoid premature duplication.
- **Q2** — accepted; RTC is genuinely Phase 4 work. Hold the Phase 4 RTC acceptance test (transformed coords near-origin while stored origin holds the large value).

New (passes 4–5), to review in a later pass, not blocking: `package_json_view` / `tile_json_view` serve geometry JSON *through Django*. Fine for the spike, but it joins the same deferred-infra bucket as D1/D2 — move to signed-URL / direct-object-storage delivery before real-scale use.

Codex update after RTC pass: Q2 is now closed for the current JSON spike. The package computes RTC origin from raw bounds, stores it on the tile row/payload, exposes transform metadata, and tests large source coordinates versus local render coordinates. Real-file jitter/orbit validation remains pending.

Codex update after F1 pass: Claude was correct that the first RTC pass mixed frames. The spike now stores `origin_source_xyz` separately from `rtc_origin_render_xyz`, exposes the reconstruction formula, and tests local-position reconstruction back to source coordinates. This closes F1 for the current single-tile package only; real tile-local origins remain unproven until actual tiling begins.
