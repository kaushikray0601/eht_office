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
- Status: **DEFER FOR DELIBERATION**
- Codex: Agree this is a boundary concern, but will defer parser extraction/copy until after the first real IFC measurement so we avoid duplicating parser code prematurely.

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
| D3 | MED | runtime dep on idfviewer lab | DEFERRED (accepted) |
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
