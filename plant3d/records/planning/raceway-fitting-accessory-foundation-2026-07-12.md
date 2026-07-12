# Raceway Fitting and Accessory Foundation

Date: 2026-07-12  
Owner: Codex  
Status: Draft for KR and Claude/Fable review

## Purpose

This note freezes the next raceway rule before accessory coding becomes costly:
the saved route centerline remains the design truth. Fittings, accessories,
supports, vendor parts, and detailed meshes are derived from that truth until
we have reviewed the semantics and know what deserves persistence.

## Current Slice

The first implementation slice is a read-only fitting projection:

- endpoint: `GET /raceway/layers/<id>/fittings/`,
- module: `raceway/fittings.py`,
- no schema change,
- no fitting or accessory rows,
- no vendor part selection,
- no geometry authority beyond saved centerline nodes and catalogue dimensions.

It derives:

- `plan_bend` placeholders at saved nodes where plan direction changes,
- `riser` placeholders on saved segments where elevation changes,
- `reducer_candidate` placeholders where connected graph members have unequal
  width/depth/family/service context.

It deliberately does not derive:

- tee/cross materialization,
- reducer handedness,
- inside/outside riser type,
- bend radius or development length,
- covers/dividers/barriers,
- support steel,
- manufacturer part numbers.

## Persistence Rule

Persisted:

- `RacewayRun`,
- `RacewayNode`,
- catalogue family/size,
- loose source/package/object anchors.

Derived:

- straight segment quantities,
- bend/riser/reducer placeholders,
- warning and schedule evidence,
- proxy face/line meshes,
- future vendor visual overlays.

Not persisted yet:

- `RacewayFitting`,
- `FittingType`,
- `VendorPart`,
- support instances,
- baked fitting GLB meshes.

This avoids migration pain while the authoring semantics are still moving.

## Face Alignment Problem

KR's constructability point is central: a horizontal tray and vertical tray
should not merely share a centerline node; the tray faces must align where the
riser or bend accessory connects. The same issue appears when a wide tray
connects to a narrower tray through a reducer.

Therefore the projection marks items that need face decisions:

- `requires_face_alignment = true`,
- `face_alignment.status = required_not_modelled`.

The future workflow should let the user choose a cross-section orientation or
face offset without breaking the route-as-truth model. The likely order is:

1. default orientation inherited from adjacent horizontal segment,
2. orthogonal rotate/flip presets,
3. explicit face offset,
4. only later arbitrary roll/angle if real projects need it.

## Reducer Semantics

A reducer is currently only a candidate when connected graph members meet at a
shared graph node and differ in width/depth/family/service. The projection
categorizes these as:

- `width_reducer`,
- `depth_reducer`,
- `width_depth_reducer`,
- `family_transition`,
- `service_transition`.

Actual reducer geometry needs:

- larger and smaller tray face,
- left/right/center alignment,
- available catalogue part family,
- development length,
- service and material compatibility.

None of that is persisted in this slice.

## Tee and Cross Semantics

Graph nodes can already be `junction` or `branch`, but tee/cross fitting
materialization is deferred. A true tee needs the target run to split at the
branch point and must define which run is the main tray and which is the branch.
That is an authoring decision, not a cosmetic fitting count.

Crosses remain deferred until project usage demands them.

## Acceptance for This Slice

- Fitting projection is project-scoped and authenticated.
- Bend/riser/reducer evidence is visible in JSON.
- Schedule still derives its bend/riser counts from the same helper logic.
- No migration is created.
- Tracker records that accessory persistence remains deferred.

## Review Questions

- Claude/Fable: is the reducer candidate shape sufficient before we add
  face-offset authoring?
- KR: should reducer candidate rows be shown in the Raceway panel immediately,
  or is JSON review enough until face alignment is coded?
- KR/Claude: should service transitions be treated as reducer candidates or as
  separate segregation/design warnings?
