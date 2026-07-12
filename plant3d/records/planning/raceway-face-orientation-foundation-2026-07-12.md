# Raceway Face and Orientation Foundation

Date: 2026-07-12  
Owner: Codex  
Status: Draft for KR and Claude/Fable review before coding

## Purpose

Raceway route centerline is still the design truth, but real tray/riser/reducer
constructability depends on which tray face is being aligned. A horizontal tray
turning into a vertical riser, or a wide tray reducing into a narrow tray, cannot
be solved by sharing only a centerline node.

This note defines the next foundation before we add orientation controls,
face-offset authoring, or persisted fitting/accessory records.

## Why Design First

Orientation is architecture-sensitive because it affects:

- visual proxy geometry,
- rough clash envelopes,
- reducer handedness,
- riser inside/outside handedness,
- future bend/riser/tee fitting geometry,
- measurement snap points on tray edges,
- what must persist as engineering intent.

Coding this as a one-off viewer rotation would create migration pain. The first
implementation should be deliberately small, but the semantics must be clear.

## Current Geometry

Current Raceway proxy geometry is derived from:

- saved `RacewayRun` and ordered `RacewayNode` centerline,
- catalogue width/depth,
- `segmentPlanBasis()` in `raceway_overlay.js`,
- derived bottom plus two side faces,
- line overlays for rails, lower edges, depth ticks, rungs/cross-members, bend
  markers, riser markers, and warning highlights.

The current default:

- bottom face starts at authored/source elevation,
- tray depth extends upward for normal horizontal segments,
- vertical/pure-riser segments choose a fallback side direction because there is
  no intrinsic plan direction.

That fallback is acceptable for preview, but not for constructability.

## Orientation Model

Terminology:

- `centerline`: the saved route polyline, still the primary truth.
- `width_axis`: cross-tray direction.
- `depth_axis`: tray depth direction, normally from bottom face upward.
- `reference_face`: the tray face used for alignment.
- `handedness`: left/right/center choice when widths differ or when a riser
  attaches to one side.

Recommended representation:

- run-level default orientation:
  - `mode`: `auto` first,
  - `reference_face`: `bottom`,
  - `roll_quarter_turn`: integer quarter-turn preset, default `0`,
  - arbitrary numeric roll is deferred.
- segment-level override:
  - keyed by stable segment identity,
  - stores only authoring intent, not derived vertices,
  - allows `inherit_previous`, `rotate_90`, `rotate_180`, `rotate_270`, and
    later `face_offset`.

Avoid for MVP:

- free numeric roll angle,
- per-vertex mesh edits,
- persisted fitting rows,
- vendor-specific geometry.

## Persistence Decision

Do not add fitting/accessory persistence yet.

For the first coded orientation slice, prefer:

- draft-local orientation changes while the user is editing,
- persistence through the existing scene/save flow, not immediate autosave,
- a tightly validated `RacewayRun.metadata["orientation"]` schema if we save
  orientation before a segment table exists.

Before persisting segment-level orientation, one prerequisite must be handled:

- `PUT /raceway/runs/<id>/nodes/` deletes/recreates node rows,
- segment overrides keyed by node UUIDs would become unstable if recreated rows
  silently received new UUID keys,
- therefore node replacement preserves existing node keys where the client sends
  keys already owned by that run.

Possible later schema if metadata becomes too loose:

- `RacewaySegmentIntent`
  - `run`,
  - `start_node_key_snapshot`,
  - `end_node_key_snapshot`,
  - `sequence`,
  - `orientation_mode`,
  - `reference_face`,
  - `handedness`,
  - `face_offset_m`,
  - `metadata`.

That table should wait until segment intent is proven useful.

## Default Inheritance Rules

Initial behavior should be predictable:

1. Horizontal or sloped segment:
   - compute width/depth axes from current centreline direction,
   - bottom face remains the reference face,
   - depth axis generally points upward.
2. Pure vertical riser:
   - inherit width/depth orientation from the nearest adjacent non-vertical
     segment,
   - if both sides are available, prefer the previous segment,
   - if neither is available, use current fallback and mark orientation as
     unresolved.
3. Reducer candidate:
   - default to one-edge alignment, not centerline alignment,
   - curve/taper the opposite edge smoothly where geometry is later modelled,
   - expose left/right edge selection from the reducer-specific pass,
   - keep center alignment as an explicit uncommon option only if justified,
   - never silently assume a stocked part.
4. Service transition:
   - keep in fitting projection taxonomy,
   - promote to warning before persistence, because this is usually segregation
     evidence rather than a reducer.

## First Code Slice Recommendation

Smallest useful implementation after this note is reviewed:

- add a run-level Orientation preset control:
  - `Open Up`,
  - `Roll Right`,
  - `Open Down`,
  - `Roll Left`,
  - later segment-level face/handedness overrides.
- apply it to selected run preview geometry,
- use undo/redo,
- no immediate autosave; persist orientation only when the user saves the
  Raceway layer/scene.

Second slice:

- preserve node UUID keys on node replacement before any segment-level override,
- reflect orientation in schedule/fitting projection assumptions.

Third slice:

- segment-level override and face-offset workflow,
- reducer handedness,
- riser inside/outside handedness,
- fitting projection emits resolved/unresolved face-alignment status.

## Measurement Snap Requirement

KR requirement recorded on 2026-07-12:

- Measure with `Snap Vertex On` must be able to snap to cable tray/raceway edges.

Recommended platform approach:

- extend the viewer layer contract with an optional snap provider,
  for example `getMeasurementSnapObjects()` or `getSnapTargets({ tool })`,
- Measurement asks visible layers for snap objects instead of knowing about
  Raceway,
- Raceway exposes snap targets from existing proxy edge geometry:
  - side rails,
  - lower edges,
  - depth ticks,
  - rung/cross-member edges,
  - possibly shaded-face vertices when surface mode is on.

Do not make Measurement import or special-case Raceway. Lighting, supports, and
future consumer overlays should use the same snap-provider contract.

## Effects On Existing Projections

Fitting projection:

- `requires_face_alignment` stays true for risers and reducer candidates until a
  resolved orientation/handedness exists.
- Add future fields:
  - `orientation_status`,
  - `reference_face`,
  - `handedness`,
  - `face_offset_m`,
  - `resolved_by`.

Warnings:

- add `raceway.warning.unresolved_face_alignment` only when orientation becomes
  user-addressable,
- add `raceway.warning.service_mismatch_at_junction` before fitting persistence,
  per Claude N-16.

Clash:

- rough AABB may continue using conservative centerline envelope until
  orientation is persisted,
- once orientation is persisted, clash envelope should use oriented proxy
  corners but remain warning-only.

Schedule/CSV:

- include orientation assumptions before any quantity depends on them,
- do not emit final fitting quantities until orientation/handedness is resolved.

## Not In This Foundation

- Vendor-specific bends/reducers/risers.
- Detailed miter geometry at bends.
- Covers/dividers/barriers.
- Arbitrary roll angle.
- Cable pulling radius/tension.
- Fitting/support fabrication drawings.

## Review Questions

- KR answered 2026-07-12: orientation changes should be saved with the normal
  Raceway scene/save flow, not immediately on every control change.
- KR answered 2026-07-12: reducer/expander centerline matching is unusual.
  Default to matching one edge and smoothing the other edge unless a project
  reason proves center alignment is needed.
- Codex implemented first run-level orientation slice on 2026-07-13:
  - four orthogonal presets are draft-local while editing,
  - undo/redo aware,
  - persisted only through the existing Save Draft flow under validated
    `RacewayRun.metadata["orientation"]`,
  - no segment-level override, face-offset, or reducer handedness authority yet.
- Codex implemented node-key preservation on 2026-07-13:
  - saved Raceway nodes resend their durable UUID keys on replacement,
  - the server reuses keys only when they already belong to the same run,
  - new nodes still receive fresh UUID keys,
  - segment-level overrides remain deferred, but their identity prerequisite is
    now closed.
- Claude/Fable: is run metadata acceptable for a first saved orientation schema,
  or should we require node-key preservation first and then add a segment-intent
  model?
- Claude/Fable: should measurement snap providers return Object3D geometry only,
  or a richer list of source-frame snap points/edges with labels?
