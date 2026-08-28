# Raceway Clash And Pathfinding Staging

Date: 2026-08-28  
Owner: Codex, with KR decision authority and Claude/Fable review

## Purpose

This note closes the Phase G closure question: what happened to deferred
clash/collision physics, and how should pathfinding consume the rough clash
work already in the Raceway MVP?

The answer is staged. The current implementation is useful, but it is not a
final geometric collision engine. H-A1 routing should consume the current
evidence as a route-cost hint, while harder clash/clearance validation remains
separate.

## Current State: Clash v0

Clash v0 already exists in the Raceway warning pipeline.

- Server code compares Raceway proxy segment envelopes against Plant3D model
  object bounds.
- The method is broad-phase AABB only.
- The scan is capped, and warns when the model-object scan is limited.
- Segment envelopes honor saved run orientation and saved segment face offset.
- Warnings are surfaced in schedule JSON, CSV, and the warning detail page.

Codes:

- `raceway.warning.model_clash_aabb`
- `raceway.warning.model_clearance_aabb`
- `raceway.warning.model_clash_scan_limited`

Clash v0 is good enough to say: "this segment overlaps or comes close to a
known object bounds box; prefer another route if one exists." It is not good
enough to say: "this installation is clash-free."

## H6 Bridge

Closure Pass 4 adds the H6 bridge:

- server module: `raceway.clash`,
- endpoint:
  `/raceway/layers/<layer_id>/clash-penalties/`,
- projection tag: `raceway.clash_edge_penalties.v0`,
- edge identity: ordered adjacent Raceway node UUID pair
  `start_node_key::end_node_key`,
- authority: soft route-cost hint only.

The bridge aggregates existing Clash v0 warnings by durable saved segment
edge. It deliberately does not use graph-local ordinal edge keys such as `E001`
as consumer truth.

Default soft penalties:

- model AABB clash: `5.0 m`
- model AABB clearance-band warning: `1.0 m`

These penalty numbers are not physical lengths. They are cost bias values for
route comparison. The H-A1 route engine may start length-only, then optionally
inject these penalties through its weight-function seam.

## Pathfinding Staging

### H-A1 Routing Foundation

Build first:

- graph from saved Raceway topology,
- durable node-pair edge keys,
- deterministic tie-breaking by node/edge keys,
- injectable edge weight function,
- preview endpoint that reports:
  - path node keys,
  - path edge keys,
  - per-edge length,
  - horizontal/riser flags,
  - total cost and total geometric length,
  - basis and assumptions.

Initial route cost may be simple length. The H6 bridge is ready as the first
optional penalty source.

### H-A2 Cable Assignment

After H-A1:

- define consumer-neutral cable reference:
  `owner_module` plus opaque `cable_ref`,
- no direct EHT dependency inside Raceway,
- persist assignment intent separately from route geometry,
- allow route preview before commit,
- record telemetry for suggestions and user overrides.

### H6 Penalty Use

When enabled, route weight should look like:

`edge_cost = geometric_length_m + bend_cost + riser_cost + clash_penalty_m`

For H-A1, only `geometric_length_m` and optional `clash_penalty_m` are required.
Bend/riser/fill/segregation costs can plug into the same weight seam later.

## Deferred Clash Physics

### Clash v1

Target after routing basics:

- spatial indexing for faster model-object candidate search,
- discipline/category-specific clearance rules,
- optional hard constraints for blocked zones or forbidden objects,
- richer warning lifecycle: acknowledge, accept, ignore, assign action owner.

### Clash v2

Target after real-model scale proof:

- OBB or mesh/BVH narrow-phase checks,
- swept volume around tray accessories,
- high-risk local refinement around bends, risers, reducers, Tee, and Cross,
- offline or worker-based processing for heavy geometry.

This must not run on every ordinary mouse move in the browser. Live drawing
should stay responsive; heavy clash proof belongs to explicit checks,
background jobs, or focused high-risk areas.

## Design Rules

- Raceway centerline and saved node topology remain the source of routing
  truth.
- Accessory proxies may contribute future weight/cost hints, but vendor-grade
  fitting geometry is not required for H-A1.
- AABB warning evidence must remain explainable to the user: object stable id,
  label, raceway bounds, object bounds, source point.
- Route-cost penalties should be visible in route preview, not hidden inside
  a magic optimizer.

## Manual Check

After login, open:

`/raceway/layers/<layer_id>/clash-penalties/`

Expected shape:

- top-level `layer`,
- top-level `clash_edge_penalties`,
- projection `raceway.clash_edge_penalties.v0`,
- `basis.source` is `existing_raceway_aabb_warnings`,
- `edges[*].edge_key` uses `node_uuid::node_uuid`,
- clash and clearance warning counts roll up per edge,
- route penalties appear as soft cost hints.

## Note To Claude/Fable

Please challenge the H6 bridge shape before H-A1 begins:

- Is the durable node-pair key enough for the first route preview engine?
- Are the `5.0 m` and `1.0 m` default penalties acceptable as explicit
  configurable constants for MVP, or should they move to settings before H-A1?
- Do you agree that Clash v1 spatial indexing can wait until routing exists,
  provided the bridge remains explicit about scan limits and soft authority?
