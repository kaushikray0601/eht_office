# Codex Memory

Last updated: 2026-07-12

Purpose: compact operating memory for Codex when resuming work after context
compression, pauses, or new chats. Keep this file short and current.

## Current Plant3D Reset Snapshot - 2026-07-08

Primary restart context:

- `plant3d/records/prompts/codex-platform-reset-start-prompt-2026-07-08.md`
- `plant3d/records/planning/platform-reset-handover-2026-07-08.md`
- `plant3d/records/planning/platform-ecosystem-development-plan-2026-07-08.md`
- `plant3d/records/tracking/platform-ecosystem-reset-tracker-2026-07-08.md`
- `plant3d/records/decisions/0005-plant3d-independent-platform-boundary.md`
- `plant3d/records/planning/raceway-module-architecture-2026-07-02.md`

North star: `plant3d` is the neutral 3D engineering platform. EHT,
raceway/tray, cable routing, construction, review, and future modules consume
it through stable anchors and viewer/API seams. They do not put domain
persistence into `plant3d`.

Current pivot: stop pushing cable-first free-space autorouting. Real EPC cable
routing is shared raceway/tray/trunk first, then cable assignment. Existing EHT
cable centerline tools remain draft/manual exception tooling and a useful
editing prototype, not the product architecture.

KR alignment from Claude discussion on 2026-07-08:

- MVP standard direction is IEC-first for Middle East, Asia, and Europe target
  markets. NEMA/ANSI comes later.
- MVP raceway scope is aboveground first: tray, ladder, sleeve/trunking style
  work. Underground trench/duct-bank work is deferred until the MVP integration
  shape is proven.
- EHT must remain a consumer of `plant3d`, not tied into `plant3d`. Future
  modules such as lighting design should follow the same peer-consumer pattern.
- Durable raceway geometry should not be package-RTC render coordinates as the
  only truth. Prefer source/world coordinates or model-object stable anchors
  with source/package context; derive render-frame positions through the
  `plant3d` coordinate/RTC contract for the viewer.

Default Raceway pass ritual from KR, 2026-07-12:

1. Read Claude/Fable notes first.
2. Do quick housekeeping/status check and respect unrelated dirty files.
3. Answer KR clarification/advice questions before coding.
4. State what KR should manually verify after the pass, including any useful
   code sections to inspect for understanding.
5. Leave a concise note to Claude when review, research, or architecture input
   would benefit the project.
6. End every pass summary with an explicit `Next Pass` recommendation section:
   ordered items, one-line reason per item when useful, and a short note if the
   order differs from the tracker. Do not omit this section even when the pass
   is small or mostly invisible.

Immediate active plan:

1. Move from coarse warning evidence toward useful engineering refinement:
   fitting/accessory modeling order is derived projection first, reducer
   candidate review, segment/face-offset editing, parametric bend/riser/tee
   geometry, then cross if field usage demands it.
2. Keep raceway drawing/persistence in `raceway`; use Plant3D only as the
   viewer host and coordinate/package/object-bounds contract provider.
3. Keep clash/collision warning-only until BVH/narrow-phase, swept-volume, and
   fitting-aware geometry foundations are tested.
4. Keep schema narrow. Vendor catalogue assets, cable assignment, and
   pathfinding remain later.
5. Update `plant3d/records/tracking/raceway-mvp-progress-tracker-2026-07-08.md`
   after each pass.

Code facts verified on 2026-07-09:

- Minimal `raceway` app now exists and is registered in `ELECSENSE/settings.py`
  and `ELECSENSE/urls.py`, with an authenticated JSON home endpoint and
  boundary tests. `raceway/access.py` wraps `plant3d.project_gateway` for Stage
  0 project scoping without direct EHT runtime imports. Minimal schema exists:
  `RacewayFamily`, `RacewaySize`, `RacewayLayer`, `RacewayRun`, and
  `RacewayNode`, with loose plant3d ids, source/world metre node coordinates,
  and UUID stable keys on runs/nodes.
- Raceway JSON API slice exists for layers, runs, and ordered node replacement.
  It validates project access, source/package access, family/size consistency,
  coordinate frame, finite node coordinates, and payload shape server-side.
- Plant3D viewer extensions are settings-driven through
  `PLANT3D_VIEWER_EXTENSIONS`; `plant3d` knows only generic extension script
  descriptors, not peer-app details. `package_viewer.js` can create an
  extension-owned overlay group through `createGroup: true` and emits
  `plant3dviewer:layers-ready`. Raceway owns
  `raceway/static/raceway/js/raceway_overlay.js`, which registers
  `raceway-overlay` as owner `raceway`.
- Stage 6 authoring was rebuilt after the failed attempt. `package_viewer.js`
  now exposes `window.plant3dViewerRuntime`, `plant3dviewer:runtime-ready`,
  source/render coordinate conversion, source-elevation plane picking, and
  `registerInteraction`. `raceway_overlay.js` owns the RaceWay Draft panel and
  supports family/size/service/elevation, start/finish/cancel, local
  undo/redo, click-to-place nodes, node list selection, move/delete, keyboard
  shortcuts, numeric edits, optional ortho drawing assist, and typed segment
  entry.
- `raceway/browser_tests.py` is the opt-in smoke test proving the raceway script
  registers its layer and handles canvas click/create/ortho/typed-segment/
  keyboard undo-redo/move/delete against a stubbed viewer host. Run it before
  asking KR to manually check authoring.
- Static cache note: Plant3D viewer host script version is
  `20260712_snap_provider1`; raceway overlay script version is
  `20260712_raceway26`. Bump the relevant cache key whenever changing either
  browser file.
- Root-cause correction after KR reported missing 3D view/only Raceway layer:
  do not dispatch `plant3dviewer:*` extension host events before core viewer
  setup is complete. `publishViewerExtensionHost()` now publishes runtime and
  dispatches events near the bottom of `package_viewer.js`, after built-in
  layer registration and viewer setup. Host script cache is
  `20260709_raceway_runtime1`; raceway overlay script cache is
  `20260709_raceway4`.
- Geometry principle: initial tray/ladder visuals are parametric engineering
  proxies derived from centerline plus catalogue dimensions. Vendor meshes may
  be attached later as catalogue visualization assets, but are not durable
  design truth.
- Stage 7 preview is complete in `raceway_overlay.js`: rail/edge/depth/rung or
  tray-cross-member line proxies are generated from `widthMm`, `depthMm`,
  service class, and nodes. Bend placeholders are generated at intermediate
  nodes. `raceway.browser_tests` verifies `side-rail`, `rung`,
  `bend-placeholder`, and live size/service updates. Overlay script cache is
  `20260709_raceway4`.
- Stage 8 persistence is complete. `raceway.0002_seed_generic_catalog` seeds
  generic vendor-free `LADDER-HDG` and `PERF-HDG` catalogue rows with
  `is_validated=False`; `/raceway/catalog/` exposes active families/sizes.
  `raceway_overlay.js` loads catalogue IDs from the server, saves finished
  centreline runs/nodes through the Raceway JSON API, and reloads saved runs
  on package viewer open/refresh. Plant3D package JSON now exposes
  `project_id`, package viewer sets a CSRF cookie, and the viewer emits
  `plant3dviewer:package-loaded`.
- `package_viewer.js` now has a single-active-canvas-tool rule across Raceway
  extension interactions, Measure, and EHT tools. Activating one deactivates
  the others so armed Raceway draw mode cannot silently swallow Measure/EHT
  clicks.
- `raceway.browser_tests` now has two opt-in Playwright tests: a synthetic
  extension-host smoke and a real live-server Plant3D viewer smoke that draws
  on the real canvas, saves through Django, reloads, and confirms the saved
  Raceway run returns.
- First Plant3D model anchor bridge is in place. `package_viewer.js` exposes
  `getSelectedModelAnchor()` on `plant3dViewerRuntime`; `raceway_overlay.js`
  has `Anchor Node` / `Clear Anchor`. Anchoring stores Plant3D stable object
  references in `RacewayNode.anchor` and places the node at the selected model
  source point. For clicked model selections, Plant3D records the clicked source
  point; hierarchy-only selections fall back to object source bounds center.
  Raceway adopts the anchor source Z as the active run elevation. This is not
  final collision/snapping; it is the first durable link between Raceway
  centerline nodes and plant model objects.
- Raceway run payloads now embed authoritative saved family/size fields
  (`family.code`, `family.kind`, `size.width_mm`, `size.depth_mm`) so reloaded
  proxy geometry does not silently guess dimensions from the active catalogue.
- Raceway usability pass after KR's manual anchor test: run rows and summary
  now show `unsaved`, `unsaved changes`, or `saved`; invalid actions are
  disabled; `Reload Saved` asks before discarding local changes; `Delete Run`
  calls the existing server delete API; save errors name the failing run tag.
  The tray/ladder proxy now treats the authored/source elevation as the
  bottom/reference plane and extends depth upward so the tray faces sky.
- Anchor contract tightening: `plant3d/overlay.py` provides
  `validate_overlay_anchor`; `raceway.views` validates node anchors while
  saving. `raceway_overlay.js` sanitizes anchors before persistence, stores
  `owner_module: raceway` plus durable `stable_id`/source/package snapshots,
  and strips package-local `feature_id`.
- Raceway interaction usability pass after KR's manual node-selection/navigation
  findings: `package_viewer.js` now suppresses extension commit clicks after
  navigation drags through `shouldIgnoreViewerCommitClick`, and exposes
  `raycastObjectsFromViewerEvent` for extension-owned handles. Raceway now has
  explicit `Select Node` mode, pickable `node-hit-target` spheres, a tolerant
  fallback node pick against the source-elevation plane, and keeps finished or
  selected runs in lightweight select mode where node hits are consumed but
  misses fall through to normal Plant3D picking.
- Raceway surface-click authoring pass after KR's continuation/elevation notes:
  `package_viewer.js` now exposes `modelAnchorFromViewerEvent(event)`.
  Raceway draw/move clicks auto-anchor to the clicked Plant3D model source
  point when available, so nodes can be created at different elevations without
  pressing `Anchor Node`. `Continue` re-enters append mode for a selected run,
  and navigation gestures leave draw mode armed for the next clean click.
  Summary rows now distinguish horizontal `bends` from elevation `risers`, and
  riser segments get simple `riser-placeholder` proxy markers. The viewer
  helper surface is recorded in
  `plant3d/records/planning/viewer-extension-contract-2026-07-11.md`.
- Raceway productivity pass after KR confirmed multi-elevation authoring:
  `raceway_overlay.js` now keeps bounded local undo/redo history for draft
  mutations, exposes toolbar `Undo`/`Redo`, and wires `Ctrl+Z`,
  `Ctrl+Shift+Z`, `Ctrl+Y`, and `Ctrl+S` plus scoped single-key shortcuts
  (`S/C/F/N/M/A/R/Delete/Esc`) with tooltip hints. Coordinate editing moved
  directly below the Raceway command buttons. History is intentionally cleared
  after successful server save/reload or external `setRuns()` so local undo
  does not pretend to undo database commits/deletes.
- Raceway methodology/AI strategy pass: Claude's
  `plant3d/records/planning/raceway-methodology-and-ai-strategy-2026-07-11.md`
  now has a Codex addendum emphasizing evidence-grounded AI, an `ai_gateway`
  seam, suggestion telemetry, and clean graph-authoring data as the real moat.
  The first M-1/M-2 authoring slice is in `raceway_overlay.js`: optional
  Ortho locks free working-plane clicks to one plan axis without falsifying
  model anchors, and typed segment entry appends +X/-X/+Y/-Y/+EL/-EL segments
  from the last node with undo support.
- Stage 8A graph foundation is underway. `raceway/graph.py` derives a
  non-persistent graph projection from saved `RacewayRun`/`RacewayNode`
  centerlines, exposed through `GET /raceway/layers/<id>/graph/`.
  `GRAPH_NODE_TOLERANCE_M = 0.01` is the explicit 10 mm source-frame
  coincident-node tolerance. Graph node/edge semantics are geometry-derived:
  endpoint, bend, riser, junction, and branch do not trust persisted
  `RacewayNode.node_kind` as authoritative. Same-elevation crossings without a
  shared graph node produce `raceway.graph.unconnected_crossing` warnings.
  The old `applyRunElevation` JS flattener was removed to protect
  multi-elevation runs.
- Stage 8A graph-aware authoring pass: `raceway_overlay.js` now refreshes the
  saved graph projection after load/save/server delete and exposes `Refresh
  Graph` (`G`) plus a graph warning block in the Raceway pane. `Connect Node`
  (`J`) is an explicit endpoint-to-existing-node stitch command: select the
  first/last node, click another raceway node handle, then save/refresh for the
  server graph to confirm the shared junction. Crossings still do not become
  tees automatically; mid-run tee/split insertion remains open.
- Stage 9 schedule JSON foundation is underway. `raceway.graph` now emits
  `raceway.graph.near_miss_endpoint` warnings for endpoints within
  `NEAR_MISS_ENDPOINT_RADIUS_M = 0.25` of another run but outside the 10 mm
  connection tolerance. `raceway/schedule.py` derives non-persistent schedule
  quantities from saved runs: segment lengths, grouped length by
  family/size/service, plan-bend and riser placeholders, support placeholders
  using `PLACEHOLDER_SUPPORT_SPAN_M = 3.0`, and explicit assumptions. The
  endpoint is `GET /raceway/layers/<id>/schedule/`. Schedule traceability uses
  durable `run_key`/`node_key` UUIDs, never projection-local `N001`/`E001` keys.
- Stage 9 schedule viewer/export pass is in place. The schedule payload now
  includes generation context, graph-warning counts, standard-length
  `piece_count_estimate`, `offcut_m_estimate`, and an explicit deferred
  junction/tee/cross assumption. `GET /raceway/layers/<id>/schedule.csv`
  exports server-side CSV from the same payload. The Raceway panel adds
  `Refresh Schedule` (`B`) and `CSV` (`Shift+B`) with a compact summary of
  length, pieces, offcut, bend/riser/support placeholders, graph warning count,
  and leading family/size/service groups.
- Stage 10 warning-layer foundation is in place. `raceway/warnings.py`
  standardizes warning payloads, normalizes graph warnings, and derives
  route/catalog/context notices for too-few nodes, short segments, excessive
  bends, inactive catalogue references, unknown service class, missing
  coordinate context, and support-placeholder basis. Schedule JSON now includes
  `warnings` and `warning_summary` while keeping `graph_warnings`; schedule CSV
  now prints graph warning counts, warning summary/detail rows, totals, and
  fitting placeholder category rows. Viewer cache key is
  `20260712_raceway16`. Hard-clash warnings remain next-stage work.
- Stage 10 inspector/polish pass is in place. Raceway local draft warnings now
  use structured warning objects and are visible in the inspector before save;
  refreshed schedules show warning detail rows in the panel. Plant3D viewer
  layers now have an opt-in `screenScaledObjects` hook, and Raceway node handles
  use it so visible spheres stay small while invisible hit targets remain
  selectable. Cache keys: package viewer `20260712_screen_scale1`, Raceway
  overlay `20260712_raceway17`. Backlog now explicitly includes reducer
  fittings, segment/face-offset editing for riser/bend face alignment,
  parametric bend/riser/tee fitting geometry, and cross fittings later.
- Solid 3-plane Raceway proxy visual pass is in place. Each run now renders one
  merged `solid-3-plane-proxy` mesh from source-frame centreline nodes and
  catalogue width/depth: bottom face plus two side faces. Existing lines/rungs,
  bend/riser placeholders, and node handles remain as legibility overlays. The
  mesh is derived/non-persistent and does not change centerline truth or vendor
  asset policy. Raceway overlay cache key is `20260712_raceway18`.
- Raceway surface/wire visual polish is in place. The solid proxy remains one
  merged mesh per run, but now uses vertex colours so bottom and side faces have
  different shades without extra draw calls. Users can toggle shaded faces with
  the Surface On/Wire Only button or `Shift+V`; wire mode keeps rails, rungs,
  bend/riser placeholders, nodes, and engineering truth active. Segment frame
  geometry is now 3D-aware so vertical risers push tray depth sideways instead
  of collapsing side faces into the riser direction. Raceway overlay cache key
  is `20260712_raceway19`.
- KR visual-control notes, 2026-07-12: vertical/riser trays need user-controlled
  cross-section orientation. Default should eventually inherit from the
  adjacent horizontal segment; add orthogonal rotate presets before arbitrary
  roll angles. A shaded-face opacity slider is cheap if treated as viewer/user
  preference only. Colour is graphically cheap but semantically important:
  service-class colours remain the default truth; project/service palette config
  should precede arbitrary per-run colour overrides.
- Tier-0 suggestion telemetry foundation is implemented as peer app
  `telemetry`. `SuggestionEvent` stores a UUID lifecycle key, loose
  `project_id`, owner module, suggestion code, action, context, action detail,
  client, and user FK; it has no FK to Raceway/EHT/Plant3D domain rows. The
  ingestion endpoint is `POST /telemetry/events/`, session/CSRF protected,
  project-gateway validated, rate-limited, and capped to 50 accepted events per
  batch. Server sanitizes context/action detail to remove primary-key-like IDs.
  Raceway overlay emits deduped warning `shown`, save-time
  `unresolved_at_save`, and `raceway.ortho.axis_lock` events through a
  fire-and-forget queue; telemetry failure cannot block authoring/save. Raceway
  overlay cache key is `20260712_raceway20`.
- Rough Plant3D envelope warnings are implemented in `raceway/warnings.py`.
  `raceway/geometry.py` now centralizes point/distance/bend/bounds helpers for
  graph/schedule/warnings. `build_layer_warnings()` reads accessible
  `plant3d.ModelObject.bounds` by loose source/package ids and emits
  warning-only `raceway.warning.model_clash_aabb` / `model_clearance_aabb`
  notices with stable object evidence, raceway/object AABBs, gap, run/node
  keys, and segment index. The first-pass object scan is capped and emits
  `raceway.warning.model_clash_scan_limited` when incomplete. This is coarse
  source-frame AABB only: not BVH, swept-volume, fitting-aware, or a hard
  blocker. Schedule warnings now emit telemetry `shown` and are included before
  `unresolved_at_save`. Claude N-13 is closed: Raceway now consumes object
  bounds through `plant3d.overlay.model_object_bounds_for_source()` instead of
  importing `plant3d.models`, and that helper can prefilter through
  `RenderTile.bounds`. Raceway overlay cache key is `20260712_raceway22`.
- Raceway warning UX polish: schedule warning rows tied to a saved `run_key`
  are clickable. Clicking selects the affected run/node and highlights the
  affected segment with `warning-segment-highlight`; layer-level warnings
  remain plain text. The telemetry design note now documents the context shapes
  for `model_clash_aabb`, `model_clearance_aabb`, and `model_clash_scan_limited`.
- Plant3D source detail polish: `source_detail.html` shows the latest
  conversion progress directly below the primary 3D Model action, including
  below `Open 3D Viewer`, and `source_detail.js` keeps it updated during
  polling. Source detail script cache key is `20260712_sourceui2`.
- KR threshold-config note: warning thresholds/settings should later move into
  a role-gated project/admin configuration surface, not stay hardcoded forever.
  Include short-segment threshold, excessive-bend count, support placeholder
  span, rough clash clearance, broad-phase scan cap, graph tolerance, and
  near-miss sensitivity.
- Raceway shortcut reliability audit is complete. `raceway_overlay.js` now maps
  keyboard events to concrete actions before gating. Advertised commands work
  from viewer canvas focus when a run/layer context makes them relevant, while
  external typing targets keep normal keyboard behavior. Browser smoke covers
  canvas-focus `B` schedule refresh and `Ctrl+S` repeat save. Raceway overlay
  cache key is `20260712_raceway23`.
- KR warning-action note: after functional pieces stabilize, add a warning
  lifecycle UX for acknowledge/accept/ignore/dismiss actions. It should preserve
  full JSON/CSV evidence and record reviewer/action/timestamp/reason plus
  telemetry, not silently delete engineering evidence.
- Fitting/accessory foundation slice is in place. Design note:
  `plant3d/records/planning/raceway-fitting-accessory-foundation-2026-07-12.md`.
  `raceway/fittings.py` derives a read-only `raceway.fittings.v0` projection
  exposed at `GET /raceway/layers/<id>/fittings/`: plan-bend placeholders,
  riser placeholders, and reducer candidates at connected unequal-size graph
  nodes. Schedule now reuses these bend/riser helpers. No schema change and no
  fitting/accessory persistence yet; review reducer candidate shape and
  face-alignment semantics before coding persisted fitting records or
  face-offset authoring.
- Raceway fitting projection is now visible in the authoring pane. `Refresh
  Fittings` / shortcut `T` loads the saved layer fitting projection and shows
  placeholder totals, plan-bend/riser/reducer counts, face-alignment/catalogue
  validation counts, and branch/junction graph counts. This remains read-only
  and non-persistent. Claude N-14 is closed: `plant3d.tests` now reads the
  Raceway extension script/version from `settings.PLANT3D_VIEWER_EXTENSIONS`
  instead of hardcoding a stale cache key. Raceway overlay cache key is
  `20260712_raceway24`.
- Warning navigation polish is in place. `package_viewer.js` exposes
  `frameSourcePoints(points, { paddingM, minRadiusM })` as a consumer-helper on
  `plant3dViewerRuntime`; the viewer-extension contract note documents it.
  Raceway schedule warning rows now select/highlight the affected run/node and
  frame the warning segment/source point in the host camera. The Raceway section
  summary has a collapsed-visible notice-count badge. Cache keys: package viewer
  `20260712_frame_source1`, Raceway overlay `20260712_raceway25`.
- Face/orientation foundation note is written:
  `plant3d/records/planning/raceway-face-orientation-foundation-2026-07-12.md`.
  It keeps centerline as truth, treats orientation/handedness/face-offset as
  authoring intent, defers fitting/accessory persistence, and identifies stable
  node-key preservation as a prerequisite before segment-level overrides. KR's
  Measure Snap Vertex requirement is recorded: Measurement should snap to
  Raceway tray/ladder edges through a generic viewer-layer snap-provider
  contract, not by importing or special-casing Raceway.
- Measurement snap provider foundation is implemented. `registerViewerLayer`
  accepts `getMeasurementSnapObjects`; the Measure tool includes visible
  provider objects while preserving selected EHT/model snap behavior. Raceway
  exposes side rails, lower edges, depth ticks, rungs, and tray cross-members as
  snap targets through that contract, excluding node handles and warning glyphs.
  Follow-up reliability fix: provider edge objects are selected by closest
  screen-space line segment within a tight pixel threshold before selected mesh
  vertex snapping, so nearby structures/trays do not win by raycaster depth
  order.
- First Raceway orientation-control slice is implemented. Active runs have a
  run-level orientation preset (`Open Up`, `Roll Right`, `Open Down`,
  `Roll Left`), applied to proxy geometry, undo/redo aware, and persisted only
  through the normal Save Draft flow under validated
  `RacewayRun.metadata["orientation"]`. Still deferred: segment/face-offset
  authoring, reducer handedness, and explicit accessory snap geometry.
- Raceway node-key preservation is implemented. Saved nodes resend `node.key`;
  the server preserves keys only when they already belong to the same run,
  rejects foreign/invalid keys without deleting existing nodes, and gives new
  nodes fresh UUID keys. This closes the identity prerequisite before
  segment-level orientation/face-offset overrides. Cache keys: package viewer
  `20260713_snap_provider2`, Raceway overlay `20260713_raceway28`.
- Raceway segment identity/selection groundwork is implemented. The overlay
  derives selectable segment rows from adjacent node pairs, uses
  `start_node_key::end_node_key` as the stable authoring identity after save,
  and temporary `draft:<segment_index>` identities before save. Selected
  segments get a blue viewer highlight and inspector text. No segment-level
  override is persisted yet. Split-inheritance rule in the design note: if a
  segment is split by future mid-run insertion, both child segments inherit the
  original segment intent by default; new branch segments start from the run
  default unless explicitly copied/assigned. Merge/stale-intent future rules are
  also recorded: keep merged intent only when both parents agree, and drop/flag
  stale non-adjacent segment entries. Claude N-17 is closed: rough model
  clash/clearance AABB now uses oriented proxy corners for saved run
  orientation. Raceway overlay cache key: `20260713_raceway29`.
- KR manual follow-up on 2026-07-14 produced two fixes and two recorded
  backlogs. Fixes: Measurement snap now falls back to visible Plant3D model
  meshes after Raceway layer-edge snapping, so tray-to-structure measurement is
  possible again; Raceway Continue/Add Segment now extends from the selected
  endpoint, prepending from N1 and appending from the last node. UI polish:
  Shift+M toggles the Plant model reference layer, source-detail conversion
  progress is only shown in the primary action area, completed conversion view
  links surface there, and Raceway lower edges use a slightly different colour.
  Backlogs: direct canvas segment picking for middle segments whose shared node
  handles win the click, and an explicit work-plane/free-route mode so tray
  routing does not appear dependent on pre-existing support steel. Cache keys:
  package viewer `20260714_snap_provider3`, source detail `20260714_sourceui3`,
  Raceway overlay `20260714_raceway30`.
- Deferred stock reviewed against Claude §28 on 2026-07-12. Keep open:
  `.code-workspace` tracked-file cleanup decision, KR generic catalogue seed
  confirmation, F-19/F-20 commit hygiene notes, blocked-telemetry browser
  assertion, telemetry `session_key`, M-5 parallel offset, M-6 plan-view
  polish, warning lifecycle/config, reducer/face-offset semantics, and the
  `ai_gateway` decision record before Tier-1 AI.
- `plant3d.models.SourceModel.project_id` is a loose string reference, not a
  hard FK to EHT. The EHT-backed access dependency is intentionally confined to
  `plant3d.project_gateway`.
- `plant3d.tests.Plant3DProjectGatewayTests.test_eht_model_imports_stay_confined_to_project_gateway`
  guards that boundary.
- `plant3d.urls` has source list/upload/detail/json, job json, package viewer
  and package/object/tile APIs.
- `package_json_view` already exposes top-level `coordinate_transform` and does
  not expose `manifest_storage_key`; `source_model_json_view` already exists.
  These satisfy important July 5 contract recommendations.
- `package_viewer.js` already exposes `window.plant3dViewerLayers` with
  `register`, `update`, `setVisible`, `isVisible`, and summaries. Current
  registered layers include model, measurement, reference grid, plot plan, EHT
  draft, and hidden EHT route preview.
- `routing_core.js` remains pure JS with route diagnostics/validation and graph
  primitives, but no server-authoritative validation yet.

Guardrails:

- Do not modify EHT calculation logic while working on `plant3d`/`raceway`.
- Do not add EHT or raceway domain persistence to `plant3d`.
- Do not revive always-on Manhattan/free-click routing as the main UX.
- Do not build smarter cable autorouting before a raceway graph exists.
- Do not split repo/service or add Celery/Redis unless KR explicitly restarts
  that infrastructure track.
- Do not add AGPL runtime dependencies.
- Do not hide model completeness or coordinate/precision uncertainty.
- Collision/pathfinding must begin as warnings/previews. Hard constraints and
  authoritative routing wait for tested collision/pathfinding foundations.

Claude/Fable role: architecture advisor, auditor, reviewer, and independent
researcher. Treat Claude output as valuable review input, not automatic coding
instruction. Major pivots go back to KR before implementation.

Collaboration habit: Claude should write durable findings into a short
date-stamped record under `plant3d/records/audit/` or `plant3d/records/planning/`
with stable section headings. KR can then cite file path plus line/section to
Codex. Codex should either implement accepted items or fold them into the active
plan/tracker with a note, rather than relying on long pasted chat transcripts.

## Current Objective

Make the current SR/MI + cold cable + SLD + BOQ/cable schedule path
production-ready before starting Constant Power tracer or major 3D/model-routing
work.

## Database Safety Protocol (MANDATORY — no exceptions)

Adopted 2026-06-11 after the accidental CC-P5 flush of `eht_local`:

- `manage.py flush` is banned without explicit written KR approval.
- No `DELETE`, `TRUNCATE`, or `DROP` against `eht_local` without explicit
  written KR approval.
- No `.objects.all().delete()` or `QuerySet.delete()` on any
  catalogue/reference table without KR approval.
- Before every database-modifying command, verify the active database name and
  state it explicitly.
- This applies every time, with no exceptions.

VENDOR CSV WARNING: `eht/tmp/elecEHT_Vendor.csv` (219 rows) is a post-research
working file, NOT a database mirror. It contains 178 rows that are NOT in the
current database (91 Constant Wattage Thermon/nVent + 87 Krus-Zapad MI, all
unverified) and is MISSING 89 validated rows that ARE in the database. Do NOT
run `import_data_from_file` against the vendor table — it will corrupt it.
KR is reviewing whether to add the 178 unverified rows.

## Product Vision

eTrace should become a comprehensive EHT engineering platform that exceeds
manufacturer tools by combining heat-loss calculation, tracer selection, cold
cable engineering, interactive SLDs, BOQ/schedules, auditable reports, and
eventually model-based routing/component placement.

## Active Phase

Phase A: production hardening of the current working path.

Immediate next pass:

1. Move to the next agreed audit-convergence pass outside Claude's dashboard
   workstream.
2. KR/manual release sign-off: demo walkthrough, cold-cable label overlap
   inspection, large-project browsing/search feel, and terminal-voltage manual
   cross-check.
3. KR/Claude catalogue decisions: live MI validation state, SR catalogue gate
   or warning policy, and final approved catalogue state.
4. Keep the calculation manual aligned with any behavior changes.

## Current Repo State

- Working directory: `/home/kr/mydev/eht_office`.
- Current date at latest update: 2026-06-15.
- Phase A code through `CAT-P1 / SEC-P1a` and `EHT-P1` is implemented in the
  current worktree.
- Latest full SQLite test status (verified 2026-06-15 with
  `USE_POSTGRES=false`): 332 tests passed. SQLite quick testing remains the
  default fast path.
- Latest full PostgreSQL test status (verified independently by Claude on
  2026-06-15 against local PostgreSQL): 320 tests passed.
- `TEST-P1` is complete: `SldLayoutTests` now authenticate under the
  login-required middleware, the SLD cold-cable label assertion matches the
  CC-P5 single-phase terminology, and migration `0037` is SQLite-compatible.
- `SLD-P2` is complete: combine-feeder apply now recalculates the manual
  combined FeederCable trunk from operating-current impact evidence, defaults
  missing combined length to the maximum selected feeder length, forces route
  review, persists cold-cable impact evidence in `SLDTopologyEdit.edit_payload`,
  and preserves the calculated trunk metadata in the active SLD payload.
- `SLD-P1` is complete: SLD workspace shows compact review badges for missing
  cable length, cold-cable review/unsizeable states, manual overrides, and
  manual topology review/stale states. Full SQLite suite passed 307 tests on
  2026-06-12.
- `AUD-P1` is complete: read-only `eht_local` audit confirmed restored
  reference counts, all migrations through `0037` applied, and no active
  selected-MI orphan driving output. It found two follow-up items for `CAT-P1`:
  live normalized MI validation currently has THR/MIQ and CHR/MI-825B
  `is_validated=True` while project notes say all families should remain false
  until KR row review; and `import_data_from_file` can still blindly import the
  divergent vendor CSV.
- `SCH-P1` is complete: cable schedule overrides now carry optional
  procurement/review annotations (route reference, installation area/basis,
  drum tag, cable lot, revision, review status, checked-by/date). The schedule
  table and Excel export surface these fields, admin can maintain them, and
  migration `0038_cablescheduleoverride_cable_lot_and_more` adds the columns.
  `0038` is applied to live PostgreSQL dev database `eht_local` as of
  2026-06-13 19:25 fix after the upload path exposed the pending-schema
  mismatch.
- Claude's SCH-P1 requirements review recommended a fuller procurement
  schedule snapshot model and identified null SR A/B/C coefficients as a
  must-fix blocker. KR accepted the lighter SCH-P1 as complete for convergence;
  the fuller snapshot model is deferred. `QA-P1a` fixed the active blocker:
  `compute_power_params` explicitly rejects missing/non-numeric SR coefficients,
  and `orchestrate_calculations` no longer publishes selected SR/power/BOQ rows
  when downstream power parameters fail.
- `QA-P1` is complete: added `NOTES/verification/QA_P1_WORKED_EXAMPLES.md`
  with SR, MI, direct single-phase cold-cable, and shared Feeder/Branch
  optimization worked examples; corrected stale SR parallel independent-branch
  wording in the verification report, manual, and design guide to the active
  shared-MCB basis; added regression tests for verification-report Sections B-E
  formula text and manual/design-guide shared-MCB wording.
- `RELEASE-P1` code sweep is complete: `ELECSENSE/settings.py` no longer
  hardcodes wildcard `ALLOWED_HOSTS`; production HTTPS/HSTS/secure-cookie
  settings are environment-driven; default PostgreSQL host is local unless
  overridden. Production-shaped `manage.py check --deploy` passed with explicit
  deployment env values. PostgreSQL `migrate --check` and direct connection
  passed against live `eht_local` after local DB access was allowed. Full
  SQLite suite is now 330 tests passed after `EHT-P1` close-out. Manual release
  sign-off items remain:
  demo walkthrough, cold-cable label overlap inspection, large-project
  browsing/search feel, and terminal-voltage manual cross-check.
- `CAT-P1 / SEC-P1a` code safety sweep is complete: `import_data_from_file` is
  blocked by default and requires `--execute` plus exact confirmation text
  before legacy CSV import; SR selection tests explicitly ignore legacy
  `Tracer_Family='MI'` vendor rows; login `next` redirects are validated with
  `url_has_allowed_host_and_scheme`; and production host/security settings are
  environment-driven.
- `EHT-P1` is complete: upload validation now enforces
  `Maint_T <= Oper_T <= Design_T`, including the `Maint_T == Oper_T` boundary.
  SR no-selection now persists diagnostics, and SR heat-duty no-match can
  trigger automatic MI fallback with mode `automatic_heat_duty_fallback`. If
  MI also fails, result pages show both SR and MI reasons. Cold-cable results
  now store startup-current voltage-drop warning evidence with a project
  threshold default of 10%; this is warning-only and does not auto-upsize.
  Model-level `HeatTracingInput.clean()` validation is implemented. The result
  page now tells users to review startup terminal voltage, route length, manual
  cold-cable size, or branch/load split when startup VD exceeds threshold.
- Testing convention from 2026-06-14: try PostgreSQL-backed tests first where
  meaningful, then fall back to SQLite if Django test-runner setup hits the
  known `psycopg.OperationalError: connection is bad`. Direct Django PostgreSQL
  connection to `eht_local` remains usable.
- Local PostgreSQL is healthy; first-attempt failures from Codex were
  command-sandbox local-network restrictions. Use local Postgres access for
  PostgreSQL-backed Django commands.
- `eht_local` restoration after the CC-P5 accidental flush is COMPLETE
  (2026-06-11): SR + MI tracer library 130 rows restored from backup table
  `eht_eleceht_vendor_backup_temp`; ASME B36 pipe sizes 200 rows restored from
  `eht/tmp/elecEHT_ASMEB36.csv`; thermal conductivity 5 rows restored from
  `eht/tmp/elecEHT_ThermalConductivity.csv`; cold cable catalogue 14 rows
  intact (migration-seeded, unaffected).
- Claude's KR-instructed MI vendor-validation pass on 2026-06-12 found the
  originally seeded MI catalogue data was not R7-valid. The MI catalogue was
  backed up and reseeded from official vendor documents under
  `NOTES/vendor_validation/`; the documented intended state after reseed was
  all MI families `is_validated=False` pending KR row-by-row review via Django
  admin. `AUD-P1` later found the live DB has THR/MIQ and CHR/MI-825B marked
  validated; resolve in `CAT-P1`.
- Latest SLD topology regression status: `SldTopologyWorkflowTests` 32 tests OK
  in SQLite mode on 2026-06-12 after `SLD-P2`.
- Latest broader SLD/payload/result/topology/JS regression status:
  `SldPayloadTests`, `ResultAndBoqViewTests`, `SldTopologyWorkflowTests`, and
  `SldWorkspaceJavaScriptTests` 120 tests OK in SQLite mode on 2026-06-12.
- Latest PostgreSQL-backed targeted test status: 4 `CC-P3` result/cold-cable
  tests OK on 2026-06-07 using existing database `eht_local_test`.
- Latest cold-cable catalogue readiness inspection: Method E has validated
  IEC/Cu/XLPE rows only: 4 rows for 3C and 10 rows for 4C. Methods B2, C, D1,
  and D2 have no validated rows.
- Project setup currently exposes only Method E as selectable. Method D2 direct
  buried is visible as a disabled coming-soon option. B2, C, and D1 are hidden
  from project setup until their catalogue basis is ready.

## Frozen Engineering Decisions

- SR remains the default hot-cable technology.
- MI is automatic only when SR catalogue temperature limits are exceeded or SR
  cannot meet heat duty within configured run/spiral limits.
- Users do not manually choose SR versus MI in project setup.
- Constant Power tracer is a future separate hot-engineering module.
- SR parallel runs now use one shared 2-pole MCB per run group for cold-cable
  rebuild purposes.
- MI multi-sets remain represented as independently protected branches.
- SLD alternate tracer overrides are review-only and do not recalculate load,
  BOQ, breaker size, or cable schedule yet.
- SR A/B/C polynomial method remains active; vendor curve-point interpolation is deferred.
- MI T-class is review evidence, not final calculated sheath-temperature approval.
- Cold cable conductor path is Cu-only for now.
- Aluminium cold-cable catalogue path has been removed/deferred.
- Cold cable uses RCD terminology, not GFEP terminology.
- Cold cable sizing uses operating current, not starting current. Startup
  current is checked as a warning-only voltage-drop review item.
- Cold cable voltage-drop basis: PF = 1.0; reactance term ignored.
- Active cold-cable rebuild basis is single-phase: `FeederCable` from MCB to
  optional `DistributionJB`, then `BranchCable` to `BranchJB`/tracer.
- Single-phase VD formula: `2 x I x R x L`, evaluated across the full terminal
  path (`VD_feeder + VD_branch`).
- L-PE fault loop basis:
  `Z_loop = Z_source + R_phase_feeder + R_PE_feeder + R_phase_branch + R_PE_branch`.
- EHT DB fault rating is mandatory, defaults to 15 kA, and accepts presets
  10/15/25/40/50 kA plus Other >= 1 kA. It is the three-phase prospective
  short-circuit current at the EHT DB busbar. Source impedance is
  `V_phase / (three_phase_fault_rating_ka x 1000)`.
- Cable conductor temperature basis: XLPE = 90 C, PVC = 70 C.
- Copper resistance temperature coefficient: `0.00393 / C`.
- Ampacity derating: `K_temp x K_group`.
- Grouping derating valid range: `0.25` to `1.0`.
- RCD provided: weak 3C MCB earth-loop result becomes review-required, not automatic upsizing.
- RCD not provided: MCB earth-loop check is hard gate; engine can upsize 3C if a larger cable passes.
- Tracer PE-path resistance is deferred and documented as non-conservative.
- Project default cable lengths force `review_required` even when sizing passes.

## Important Implemented Cold-Cable Behavior

- `ColdCableResult.cable_3c_segments` stores per-outgoing 3C sizing evidence.
- Different outgoing 3C lengths from the same JB can select different 3C sizes.
- Branch-level 3C result stores the critical/largest selected 3C summary.
- SLD/cable schedule metadata can read per-node 3C segment results.
- Cable mass is calculated from conductor area, length, core count, and copper density.
- Per-branch Branch Cable segment evidence is visible in the result tab, cable
  schedule, cable schedule export, and a dedicated `Cold Cable Branch Segments`
  result-export sheet.
- `CC-P3` adds `phase_slot`, `phase_label`, and `phase_basis` to per-outgoing
  3C segment JSON, propagates the phase label into SLD Cable3C metadata, and
  shows L1/L2/L3 phase-current totals plus imbalance in result UI/export.
- `CC-P4` adds a branch-based Panel / Load Summary to the Result tab and result
  export. It groups by panel/source metadata when present; otherwise it groups
  under the project main distribution. It reports MCB count, circuit count,
  load current, connected load, breaker distribution, and cold-cable selected /
  review-required / unsizeable / not-sized counts. It is review evidence only;
  upstream main-breaker spare-capacity checks and bus phase totals remain
  deferred.
- 2026-06-08 CC-P4 correction: panel/load summary now uses branch current
  (`per_circuit_operating_current_a x circuit_count`) before line-total
  fallback data, and deduplicates shared MCB count/breaker capacity by MCB tag.
- `ProjectData.eht_db_fault_rating_ka` and
  `ProjectData.eht_db_source_impedance_ohm` are in place as the source
  impedance foundation for `CC-P5`.
- Migration `0034_rcd_cu_only_cold_cable` renames GFEP fields to RCD and deletes Al catalogue rows.
- `CC-P1` adds cold-cable installation-method readiness feedback in admin and
  explicit unsizeable guidance instead of a generic no-catalogue message.
  Project setup is simplified to active Method E plus disabled coming-soon D2.
- SLD topology operations are hardened against a stale/empty browser workspace
  state. The SLD shell now clears stale state at render start, releases the
  render guard on success/error/focused-line fallback, and controls re-trigger
  SLD loading instead of silently no-oping when `__sldState` is missing.
- SLD render guard follow-up fixed the remaining sticky-lock path: render
  callbacks use `finally`, `renderSldGraph` catches top-level runtime failures,
  and a watchdog clears a stuck render flag after 20 seconds.
- SLD topology browser regression had a second, more fundamental cause after
  cold-cable engineering: rendered SLD symbols/cable nodes became more
  SVG-path-driven, while component click handling relied on unreliable implicit
  hit testing. Component bodies now declare explicit pointer hit targets, and
  the browser test performs real rendered-cell preview/apply workflows.
- P1-specific SLD stale failure root cause: P1 had a 96-operation historical
  active topology chain whose first saved `combine_feeders` operation referenced
  old MCB component IDs no longer present in the recalculated generated graph.
  New edits previously inherited that unreplayable chain, so every new apply
  was hidden behind operation #1 failing replay. Apply workflows now inherit an
  active operation chain only if it replays successfully against the current
  generated baseline; otherwise the new edit starts from the graph the user is
  actually seeing.
- Cold-cable engineering also exposed an over-broad topology fingerprint:
  `payload_fingerprint` included all node metadata, including volatile cold
  cable sizing/review evidence. The fingerprint now tracks topology structure
  only, so cold-cable calculation metadata cannot falsely mark an SLD edit as
  stale.
- `base.html` versions the SLD script as `sld_workspace.js?v=sld-r3-hit-targets`
  so Chrome does not keep executing old SLD interaction code after this fix.
- `eht.browser_tests` is the optional Playwright browser-smoke module for SLD.
  It is intentionally separate from normal backend tests and runs successfully
  through venv Playwright against the Django live server and PostgreSQL test DB.
  Latest run: `venv/bin/python manage.py test eht.browser_tests -v 2 --noinput`
  passed 3 tests in 11.943s on 2026-06-07, including preview and apply for
  Combine, Split, Add downstream JB, and Attach/Move.
- Real P1 verification was performed with database transactions rolled back:
  Combine, Split, Add downstream JB, and Attach all returned `ok=True`, produced
  one clean operation in the new active edit, and cleared false
  `topology_edit_review_required` / `topology_baseline_changed` state without
  mutating the live P1 data.
- SLD hardening pass on 2026-06-07:
  - Frontend render paths now use one `safeRenderCurrentSldPage` gateway for
    initial load, pager, page-size changes, and search-driven page changes.
  - External detail labels use one geometry helper for create/refresh so labels
    do not drift after component movement.
  - Filtered/focused SLD views disallow topology mutation with a warning, while
    cable length overrides and tracer alternate selection remain available.
  - Topology apply locks the project row, validates operation schemas and graph
    invariants, records stale-chain drop audit metadata, and compacts very long
    operation chains fail-closed.
  - Programmatic existing-PostgreSQL SLD suite passed 38 tests. Standard
    `manage.py test ...` still fails in the test-command setup connection path
    with `psycopg.OperationalError: connection is bad`, despite direct Django
    connection/migrate and the programmatic runner succeeding.
- `CC-P5` rebuild is implemented: SR parallel runs share one 2-pole MCB per run
  group; cold-cable sizing uses single-phase Feeder Cable + Branch Cable paths,
  terminal-path `VD = 2 x I x R x L`, project three-phase EHT DB fault rating
  source impedance, and complete L-PE loop evidence. Migration
  `0036_single_phase_cold_cable_fault_loop` deletes stale `ColdCableResult`
  rows and replaces old 4C phase-to-phase result fields with
  `fault_current_l_pe_a`, `fault_loop_status`, and `fault_loop_basis`.
  If migrated/invalid data makes source impedance unavailable, the engine uses
  `Z_source = 0.0` and writes an explicit review note.
- Claude review follow-up after CC-P5: form/manual/docs now explicitly say the
  EHT DB fault rating is the three-phase PSCC at the DB busbar; tests now cover
  panel-summary fallback from zero per-circuit current to line current and
  multi-circuit per-circuit multiplication.
- Second Claude review follow-up after CC-P5: migration
  `0037_remove_legacy_3c_fault_fields` removes the legacy 3C line-to-neutral
  fault fields; SR shared-MCB branches now retain group-level tagged metadata
  (`sr_parallel_run_count`, `sr_parallel_run_basis`, `sr_shared_mcb`) without a
  per-run index.
- Upcoming SLD combine feature: when circuits are combined, the new combined
  Feeder Cable must trigger cold-cable re-sizing based on combined current. The
  UI should warn that previous separate feeder lengths are no longer valid;
  default the new combined Feeder Cable length to the highest length among the
  selected feeder cables and require user review/confirmation.
- Local dev DB caveat from 2026-06-08: during CC-P5 verification, Codex
  accidentally executed a destructive `flush` against the local PostgreSQL
  development database. Catalogue/reference restoration completed 2026-06-11
  (see Current Repo State). This incident is the origin of the mandatory
  Database Safety Protocol section above.
- Housekeeping pass after SLD hardening removed live debug/dropdown projects
  `p-debug-sld`, `p-debug-sld-api`, `p-hard`, and empty orphan `p2` from local
  PostgreSQL. Current live project selectors should show only `default_project`
  and `p1`. Ignored `__pycache__` directories were cleaned once; normal checks
  may recreate them.
- Tracked SLD review docs (`SLD_DEEP_ANALYSIS.md`,
  `SLD_RENDERING_REVIEW.md`) and `eht/browser_tests.py` are intentional guard
  rails and should not be treated as temporary artifacts.
- `SLDTopologyEdit` is registered in Django admin as a read-only audit panel.
  It shows operation history, operation count, compaction state, stale-chain
  audit metadata, validation JSON, current-baseline fingerprint comparison, and
  an in-memory replay diagnostic. This is admin visibility only; there is still
  no user-facing undo/restore-to-operation feature.
- SLD topology history retention is implemented. Old `superseded` and `reset`
  rows can be compacted to audit-only payloads while active `applied` and
  `needs_review` rows remain protected. Django admin shows payload size and
  payload-compaction status, provides a selected-row compaction action, and has
  a guarded emergency delete action for non-active history rows only. The
  `compact_sld_topology_history` management command defaults to dry-run and
  requires `--execute` to mutate records. Local live cleanup on 2026-06-07
  compacted 100 old rows and saved about 57.5 MB of JSON payload; follow-up
  dry-run reported 0 remaining candidates under the keep-full 20 / keep-reset
  10 policy.

## Known Deferred Gaps

- Installation-method catalogue coverage remains limited to Method E seed rows;
  D2 catalogue work is deferred and shown as coming soon in project setup.
- Automatic phase rebalancing/user-editable phase slots are not built.
- Upstream main-breaker coordination/spare-capacity checking is not built. The
  CC-P4 branch-based panel/load summary is available for review evidence.
- MI R7 row-by-row validation state needs reconciliation after Claude's
  2026-06-12 official document review/reseed. The intended gate is
  `MICableFamily.is_validated=False` until KR approves rows via Django admin,
  but `AUD-P1` found the live DB currently has THR/MIQ and CHR/MI-825B marked
  validated. Resolve before trusting MI-sensitive calculations.
- `import_data_from_file` is blocked by default and requires explicit
  confirmation; `eht/tmp/elecEHT_Vendor.csv` is still not catalogue truth.
- A lightweight SCH-P1 procurement annotation/export layer exists. Full
  document-level schedule snapshot/issue revision control is deferred.
- Browser-level SLD smoke coverage exists in `eht.browser_tests` and is green
  in the local dev setup after installing Playwright's Linux browser
  dependencies in the venv workflow.
- Tracer PE-path impedance is not included in earth-loop calculation.
- Short-circuit withstand/minimum conductor cross-section is deferred.
- MI max heated length, cold-lead completeness, terminal/gland/JB capacity are deferred.
- SR vendor curve-point interpolation is deferred.
- Constant Power tracer is deferred.
- Model-based cable routing and 3D component placement are deferred.

## Collaboration Notes

- Claude acts as architect/auditor/reviewer/critic/collaborator.
- Codex acts as senior developer/collaborator/consultant/adviser and implements.
- Do not code immediately from Claude review notes unless user approves.
- Record review findings intended for Claude in a shareable note.
- Keep `NOTES/CALCULATION_MODULE_USER_MANUAL.md` aligned when implementing or
  changing any calculation behavior. Claude maintains the manual, but Codex
  should flag discrepancies during implementation.

## Testing Commands

SQLite is the quick/default test path. Local PostgreSQL remains the development
database and PostgreSQL-backed safety check. In Codex-managed commands,
PostgreSQL-backed tests need local Postgres access enabled; otherwise the
command sandbox can produce a false connection failure.

```bash
venv/bin/python manage.py check
USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run
USE_POSTGRES=false venv/bin/python manage.py test eht -v 2 --noinput
node --check static/js/sld_workspace.js
git diff --check
venv/bin/python manage.py test eht.browser_tests -v 2 --noinput

# Full suite — PostgreSQL-backed programmatic runner (backup/safety path)
venv/bin/python manage.py shell -c "
from django.test.utils import get_runner
from django.conf import settings
TestRunner = get_runner(settings)
runner = TestRunner(verbosity=1, keepdb=True)
print('Failures:', runner.run_tests(['eht']))
"
```

Current caveat: raw DB-using `venv/bin/python manage.py test ...` can fail in
the Codex sandbox unless local PostgreSQL access is explicitly enabled. SQLite
tests do not need that access.

## New Chat Guidance

Recommend a new chat when:

- A major pass is complete and tests are green.
- The worktree is checkpointed.
- A new module begins.
- Context replay becomes more expensive than reading this memory file.
- The next task is large enough to deserve a clean brief.

Current recommendation: move through `APP-P1`, `SEC-P1b`, `SCH-P2`, and
low-risk `UX-P1` items as KR prioritizes MVP convergence, while avoiding
overlap with Claude's dashboard work.

Latest APP-P1 note, 2026-06-15: self-registration is explicitly disabled
with HTTP 410. Upload validation error workbooks now use bounded rotating
filenames (`error_file_01.xlsx` ... `error_file_N.xlsx`) instead of the shared
`error_file.xlsx` or unbounded UUID files. Default retention is 10 files at
5 MB each, with admin configurability added by migration
`0040_errorfileretentionpolicy`, applied to PostgreSQL on 2026-06-15. No
policy row was auto-created; runtime fallback remains 10 files at 5 MB until
an admin-configured row is added. Upload validation now rejects path-like
names, non-XLSX/MIME mismatches, and disguised non-XLSX content. Focused
SQLite regression slice passed 12 tests and the full SQLite suite passed
335 tests.

Latest APP-P1 stale-workspace guard, 2026-06-15: project setup save and
replacement line-list upload now require explicit confirmation before clearing
an existing project workspace. Confirmed clears are scoped to the selected
project's uploaded inputs, calculated outputs, BOQ rows, cold-cable results,
SLD layout/topology edits, cable schedule overrides, and tracer overrides.
Catalogue/vendor/reference tables are not in this deletion path. Focused
SQLite tests passed 21 tests; full SQLite suite passed 338 tests.

Latest SEC-P1b login-attempt hardening, 2026-06-15: the existing
`UserAttempt` model is now wired into `my_login` without a migration. Existing
usernames lock for the configured 30-minute cooldown after three bad password
attempts; successful login clears prior attempt rows. Unknown usernames keep a
generic login error and do not create user-linked attempt rows. Focused
security tests passed 8 tests; full SQLite suite passed 341 tests.

Latest SEC-P1b app-level rate limiting, 2026-06-15: `django-ratelimit==4.1.0`
is installed and pinned. Login now has both IP and posted-username request
limits, while upload, valid-row confirmation, and error-file download endpoints
are limited by authenticated user or IP. These are configurable with
`EHT_LOGIN_IP_RATE_LIMIT`, `EHT_LOGIN_USERNAME_RATE_LIMIT`,
`EHT_UPLOAD_RATE_LIMIT`, `EHT_CONFIRM_UPLOAD_RATE_LIMIT`, and
`EHT_ERROR_FILE_DOWNLOAD_RATE_LIMIT`. `UserAttempt` remains account-specific
lockout; `django-ratelimit` is the request-throttle layer. Focused security
tests passed 12 tests; full SQLite suite passed 345 tests.

Latest SEC-P1b admin-path hardening, 2026-06-15: rate/security thresholds stay
environment-owned for the MVP; do not make them casual admin-editable fields
until validation, audit logging, and safe deployment semantics are designed.
`DJANGO_ADMIN_PATH` now controls the Django admin mount, login-required
middleware exemption, and staff-only landing-page admin link. Default remains
`admin/` for local development; production should set a non-default env value
and still use Cloudflare/IP/identity restrictions, 2FA, strong admin passwords,
and logging. Focused security/admin-path tests passed 15 tests; quick checks
passed; full SQLite suite passed 348 tests.

Latest APP-P1 dead-code cleanup, 2026-06-15: removed legacy `eht/calculation.py`
from the shipped app after import scans confirmed no active code imports it and
the live path is `eht.pipeline` -> `eht.cal` -> `eht.calculations/*`. Removed the
obsolete triple-quoted `ElecEHT_CalculatedTable` / `ElecEHT_IO` model reference
block from `eht/models.py`. `manage.py check`, migration dry-run, and the full
SQLite suite passed afterward; no migration was generated.

Latest APP-P1 project referential-integrity pass, 2026-06-15:
`HeatTracingInput.proj_id` is now backed by a `ProjectData` foreign key named
`proj`, with `db_column='proj_id'` so existing raw-ID code such as
`line.proj_id` and `filter(proj_id='P1')` still works. Migration
`0041_heattracinginput_project_fk` includes a fail-fast pre-check for missing,
blank, or overlength line-list project IDs; it does not silently delete or
remap data. Added tests proving `ProjectData.delete()` cascades only project-
owned line/calculation data and does not touch another project, `ManagedProject`,
or catalogue/reference rows. Full SQLite suite passed 349 tests. PostgreSQL
`0041` was applied to `eht_local` on 2026-06-15.
Read-only PostgreSQL orphan check on 2026-06-15 returned `invalid_count: 0` for
current line-list project IDs (`p-fault-4c`, `sp`, `P1`); no rows were modified
during the check. `showmigrations eht`, `migrate --check`, and `manage.py check`
passed after applying the migration.

Latest SCH-P2 cable schedule lifecycle pass, 2026-06-15: schedule visible/full
audit export behavior is complete, and migration `0042_cableschedulerecord`
adds a derived `CableScheduleRecord` audit table keyed by project + autogenerated
cable tag. Schedule view/export syncs active rows into this table when the
schedule is generated for display/export. Internal revision starts at `0`, does
not churn on unchanged schedule views, increments on schedule-relevant changes,
and retires missing tags with timestamp/user evidence where available. The table
is read-only in admin and does not drive calculations, SLD, BOQ, or cold-cable
sizing. Full audit export includes generated/modified/lifecycle evidence; the
default visible export remains compact. Added the shared-feeder/deduplication
legend. Focused lifecycle tests passed, `ResultAndBoqViewTests` passed 81 tests,
and the full SQLite suite passed 355 tests. Migration `0042` was applied to
PostgreSQL `eht_local` on 2026-06-15 after `migrate --plan` confirmed it only
creates the `CableScheduleRecord` table. `showmigrations`, `migrate --check`,
`manage.py check`, and a read-only count query on `CableScheduleRecord` passed
after migration.

Latest UX-P1 result timestamp pass, 2026-06-15:
`ProcessLineCalculation.calculated_at` was added by migration
`0043_processlinecalculation_calculated_at` and applied to PostgreSQL
`eht_local` after `migrate --plan` confirmed it only adds the timestamp field.
`store_calculated_results` stamps all stored line calculation rows from the
same calculation run with one timestamp, and the result tab header now shows
`Last calculated` from the latest stored process-line calculation. Existing
PostgreSQL rows received a migration-time timestamp; future runs will show the
actual storage-run timestamp. Focused timestamp tests passed, the combined
storage/result slice passed 84 tests, full SQLite suite passed 355 tests,
`migrate --check`, `manage.py check`, and read-only PostgreSQL smoke query
passed after migration.

Latest UX-P1 polish completion pass, 2026-06-15: completed the remaining
low-risk first-customer polish items. Added `eht.context_processors.nav_projects`
and wired it into settings so authenticated pages can show a navbar project
selector with coarse status badges: New, Setup, Input ready, Calculated. The
landing page shows the same badges for active projects. `/base/?project_id=...`
now validates the project against `ManagedProject.available_to_user()` and
preselects the workspace form for allowed projects.

Project setup forms are now grouped into logical sections, with extra help text
for technical fields that affect heat loss, catalogue selection, cold-cable
sizing, BOQ, and schedule basis. The full workspace setup form now includes the
startup VD warning threshold field to match the edit partial. Result tab gained
a `Jump to line` helper for the per-line table and a clearer MI rejected-row
cue explaining that unavailable MI records show reason, evidence, and next
action.

Added `eht/excel.py::polish_openpyxl_workbook` and applied it to input, result,
BOQ, and cable schedule exports for freeze panes, auto-filter, and bounded
auto-width. SLD gained a guarded `Shift+F` fit-all shortcut reusing the existing
Fit All button path, and SLD PDF export gained a compact title block with
project, generated timestamp, and generated-for-review status. The first
PostgreSQL targeted test attempt hit the known Codex-side test-runner
`psycopg.OperationalError: connection is bad` before tests executed. SQLite
targeted tests passed 101 tests; full SQLite `eht` suite passed 358 tests.
`manage.py check`, SQLite migration dry-run, `node --check static/js/sld_workspace.js`,
and `git diff --check` passed.

Latest release-readiness reconciliation, 2026-06-15: tracker/checklist status
was refreshed after the UX/dashboard/FAQ work so completed implementation
passes are marked complete without hiding the remaining release gates. `EHT-P1`
is complete; `APP-P1` code is complete with Claude's dashboard delivered;
`SEC-P1b` implemented controls are complete while dependency hygiene, admin
exposure policy, and production key/markdown decisions remain open. Added
focused smoke coverage for Claude's project dashboard and FAQ/help page. The
focused SQLite dashboard/FAQ smoke slice passed 2 tests. Final reconciliation
checks passed (`manage.py check`, SQLite migration dry-run, SLD JavaScript
syntax check, and `git diff --check`), and the full SQLite `eht` suite passed
360 tests.

Plant3D/Raceway note, 2026-07-14: after KR manually confirmed the snap/
continuation/viewer-polish pass, the next pass stayed projection-only and
closed Claude N-15/N-16. `raceway/fittings.py` now flags plan-bend placeholders
whose angle is outside +/-2.5 degrees of common 30/45/60/90 degree catalogue
angles, and fitting/schedule/CSV outputs expose the non-standard bend count.
`raceway/warnings.py` now emits
`raceway.warning.service_mismatch_at_junction` when connected graph-node members
mix service classes; the warning carries graph-node, source-point, run-key, and
member evidence and participates in the existing schedule/telemetry warning
pipeline. Raceway overlay cache key is `20260714_raceway31`. Fitting/accessory
persistence, reducer handedness, face-offset authoring, and real tee/bend/riser
geometry remain deferred.

Plant3D/Raceway note, 2026-07-14 later: KR manually confirmed the advisory
signal pass. Added a browser warning-detail page at
`/raceway/layers/<id>/warnings/`, opened from the Raceway panel `Warnings`
button or `Shift+W`; it reuses schedule/fitting projection evidence and shows
summary counts, warning rows, expandable evidence payloads, assumptions, and
JSON/CSV links. `/plant3d/` now lists recent accessible source models with
`Open Source` and direct `Open 3D Viewer` links when a render package exists.
Raceway overlay cache key is `20260714_raceway32`. Segment-level
orientation/face-offset remains the next architecture path per Claude §34.

Plant3D note, 2026-07-14 source retention: KR reported that sequential IFC
uploads were overwriting/pruning earlier uploads, which is no longer desired.
The old UI policy used `replace_working=True` in `source_upload_view`; remove
that override so normal uploads create/retain separate `SourceModel` rows until
explicit user deletion. Duplicate-content idempotency by `content_signature`
still reuses an existing row. Source upload/detail wording and the platform/
pipeline records were updated so "saved case" means deliberate protected
reference, not the only way to avoid upload replacement. Next Raceway
architecture path remains segment-level orientation/face-offset.

Plant3D/Raceway note, 2026-07-14 segment orientation foundation: first
segment-level orientation intent is implemented without a new table. Selected
segments can override the run orientation using the same four orthogonal
presets; the override renders immediately, participates in undo/redo, and
persists only through Save Draft under validated
`RacewayRun.metadata["segment_orientation"]` with schema
`raceway.segment_orientation.v0`. Overrides are keyed by adjacent node UUID
pairs, draft segment overrides are re-keyed after first save, and the server
prunes stale overrides when node replacement changes adjacency. Claude/Fable
T-1 telemetry documentation gap for
`raceway.warning.service_mismatch_at_junction` is closed in the telemetry
design note. Face offset, reducer handedness, split/merge inheritance UI, and
real accessory geometry remain next/deferred architecture work.
