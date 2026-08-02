# Raceway Accessory Geometry Note

Date: 2026-07-17  
Owner: Codex  
Status: Short design note for KR and Claude/Fable review before accessory geometry coding

## Purpose

This note corrects one important product misunderstanding before we code real
accessories:

`Apply Edge Match` / `Shift+T` is not a reducer fitting. It is only an
authoring aid that moves tray proxy faces into a constructible edge-alignment
state. A real reducer is a separate physical transition accessory with its own
length, handedness, tapered sides, connection ports, and later catalogue/vendor
identity.

The goal is to define the generic accessory geometry strategy before we add
reducers, bends, risers, tees, or crosses to the rendered model.

## Sources Checked

The online product/catalogue references agree on the same practical family of
parts:

- reducers appear as concentric/straight, left-hand, and right-hand styles,
- reducers are physical tapered transition pieces, not just shifted centerline
  segments,
- standard fitting families include horizontal bends, vertical inside/outside
  bends or risers, tees, crosses, reducers, covers, couplers, and supports,
- catalogue implementations are manufacturer-specific but the topology and
  port logic is generic enough for our first parametric proxy.

References:

- Eaton B-Line imperial cable tray fittings:
  https://www.eaton.com/jp/ja-jp/catalog/support-systems/imperial-cable-tray-and-ladder.html
- Superior Tray ladder tray reducers:
  https://www.superiortray.com/products/cable-tray/ladder-tray/reducers/
- PohlCon reducer example and drawing:
  https://pohlcon.com/en-de/products/rr-110/cable-tray-reducer-rr-110-30s-rr-110-30s
- BIMobject curved mesh tray reducer example:
  https://www.bimobject.com/en/solar-project/product/meshtraysystem_reducercurved
- PlantCon PDMS cable tray catalogue component families:
  https://www.plantcon.dk/uk/98008.htm
- OBO standardized cable tray fittings:
  https://www.obo.global/products/industrial-installations/product-highlights/obo-cable-trays/fittings/

## Geometry Doctrine

Persisted truth remains:

- `RacewayRun`,
- ordered `RacewayNode` centerline,
- catalogue family and size,
- segment orientation intent,
- segment face-offset intent,
- later branch/split intent.

Derived geometry includes:

- straight tray proxy faces and rails,
- bend/riser/reducer/tee/cross proxy bodies,
- fitting warnings,
- schedule placeholders,
- later vendor part projections.

Do not move centerline nodes just to make a reducer look right. Instead:

- the route remains the engineering path,
- segment face offsets describe how the tray body is placed relative to that
  path,
- a reducer accessory spans between two tray ports and models the transition
  body.

## Accessory Ports

Every accessory should be generated from connection ports, not from arbitrary
mesh edits.

A port is derived from a segment end and contains:

- `run_key`,
- `segment_key`,
- `node_key`,
- source point,
- tangent direction,
- width axis,
- depth axis,
- catalogue width/depth,
- family kind: tray, ladder, mesh, trunking later,
- service class,
- orientation preset,
- face offset,
- left/right/center edge positions.

Accessories connect one or more ports:

- reducer: two ports,
- bend: two ports on the same run around a route node,
- riser: two ports where elevation direction changes,
- tee: three ports after explicit segment split,
- cross: four ports after explicit crossing acceptance,
- coupler: two ports of same size/family with no direction change.

## Reducer Geometry

A reducer is a transition body between unequal-width ports. It needs a
handedness:

- `left_edge`: one left edge remains aligned; opposite edge tapers,
- `right_edge`: one right edge remains aligned; opposite edge tapers,
- `center`: centerlines remain aligned; both edges taper symmetrically.

Default handedness for MVP:

- default to `left_edge`,
- keep the selected handedness visible,
- allow the user to change it to `right_edge` or `center`,
- later move the default into a project/user preference panel.

Port-frame convention:

- handedness is expressed in the frame of the wider port,
- the narrower port frame is flip-aligned so both port tangents point in the
  same comparison direction before left/right edges are compared,
- this avoids mirrored reducers when one segment tangent points into a node and
  the other points out of it,
- the current segment convention remains `left = +lateral normal` in ordered
  node direction, but reducer comparison must normalize both ports to the wider
  port frame before applying handedness.

This is why `Shift+T` is only a preparatory action. It can set the segment face
offsets that make a chosen edge match, but it does not create the reducer body.

Generic reducer proxy v0 should generate:

- bottom plate or ladder center plane between the two port rectangles,
- two side rails/walls transitioning from large width to small width,
- connection plates indicated at both ends,
- optional ladder rungs/cross-bars sampled along the reducer length,
- a rough clash envelope based on the generated accessory body.

The unaligned side should not jump abruptly at the shared node. It should taper
or curve over a development length. For v0, use a simple smooth interpolation:

- straight linear taper is acceptable for solid/perforated tray proxies,
- a low-segment Bezier or eased polyline can approximate curved reducers for
  mesh/ladder visual quality,
- catalogue radius and exact pressed/fabricated shapes are deferred.

Development length should initially be rule-derived:

- if a vendor catalogue or project/user preference provides a length, use it,
- else use a named local heuristic such as
  `max(0.45 m, 2.0 * abs(width_delta_m))`,
- always expose the assumption in fitting JSON/CSV,
- later vendor-specific catalogue import can override this value.

Scope for reducer proxy v0:

- same-family unequal-width transitions only,
- `family_transition` and `service_transition` remain warnings/advisories, not
  generated reducer bodies,
- auto-suggestion should be gated to near-collinear ports, with a named
  tolerance such as `REDUCER_COLLINEARITY_MAX_ANGLE_DEG = 15`.

Straight proxy cutback:

- a reducer of development length `L` occupies centerline space that straight
  tray proxies would otherwise also render,
- reducer proxy v0 must trim the adjacent straight proxy extents by derived
  cutback distances, initially `L / 2` on each side unless the catalogue gives
  asymmetric data,
- cutback is derived geometry and must not be persisted as design truth.

## Bends

Horizontal bends are route-node accessories where plan direction changes.

Generic bend proxy v0:

- uses route tangent before and after the node,
- carries catalogue width/depth and segment orientation,
- has angle from the route,
- snaps/report nearest standard angles already tracked: 30, 45, 60, 90 degrees,
- uses a configurable bend radius,
- generates curved side rails and bottom/ladder plane,
- for ladder tray, places rungs radially or as simplified cross bars.

Non-standard bend angles stay advisory until either:

- user adjusts the route,
- a variable/adjustable bend is selected,
- a fabrication-specific custom fitting is accepted.

## Risers

Vertical bends/risers are route accessories where elevation changes.

Catalogue language varies, but the engineering distinction we need is:

- inside riser / inside vertical bend,
- outside riser / outside vertical bend,
- vertical tee up/down later.

Generic riser proxy v0:

- uses the same port model as bends,
- derives inside/outside from the active tray face and direction of elevation
  turn,
- keeps cable path curvature honest with a bend radius assumption,
- renders the two side rails/walls through the vertical curve,
- exposes unresolved inside/outside status when face orientation is ambiguous.

Vertical orientation rider:

- vertical-segment orientation should inherit from the nearest adjacent
  non-vertical segment before or with riser proxy v0,
- otherwise most risers will be correctly marked ambiguous but visually less
  useful than they should be.

### Compound Vertical Return / 270 Degree Riser Case

KR raised a constructability case on 2026-07-18:

- a tray runs horizontally at an upper elevation,
- turns downward,
- reverses direction at a lower elevation,
- and the lower horizontal tray may appear geometrically parallel/opposite to
  the upper tray while the cable-bearing surface continuity is not obvious.

This must not be treated as a simple 90 degree riser plus a generic plan bend.
The fitting logic must distinguish at least two engineering intents:

- **continuous face return:** the physical tray face follows a compound
  vertical return path; the lower run may inherit an inverted orientation unless
  a turnover/landing fitting changes the cable-bearing surface,
- **surface-reset return:** the cable leaves one bearing surface through a
  vertical return/turnover fitting and lands on a lower tray intentionally
  facing upward again.

Future detection should look for:

- two near-parallel horizontal segments with opposite tangents,
- an elevation change between them,
- one or more riser/vertical-bend nodes connecting the two levels,
- a large cumulative vertical bend angle, approximately 180 to 270 degrees,
- and a face-orientation discontinuity or ambiguity at the lower horizontal
  segment.

The derived fitting category should be explicit, for example
`compound_vertical_return` or `vertical_return_270_candidate`, and must carry:

- upper and lower horizontal ports,
- riser/return ports,
- effective orientation at each port,
- cable-bearing-surface continuity status,
- default radius/development assumptions,
- and a user-resolvable intent: continuous return vs surface-reset/turnover.

For MVP, keep this as a detected advisory/proxy candidate before trying to
generate final catalogue geometry. The first implementation should warn and
show the candidate; catalogue-grade geometry can follow once ordinary reducer,
bend, riser, tee, and cross proxies are stable.

## Tee And Cross

Tee and cross geometry must wait until topology is explicit.

Before a tee can be generated:

- the target segment must be split at the branch point,
- the split node must be a real saved node,
- one run/segment must be identified as the main tray,
- the branch must connect through a graph node, not merely cross visually.

Generic tee proxy v0:

- three ports,
- main port in/out plus branch port,
- branch width sanity warning if branch is wider than main,
- service segregation warning if services are mixed,
- no cross until four-port semantics are explicit.

Implementation update 2026-07-27:

- projection-only Tee/Cross proxy v0 is coded,
- tee/cross records are derived from connected graph node degree,
- each record carries `branch_intent` with inferred/ambiguous status,
  `persistence: projection_only`, and main/branch run evidence,
- browser rendering creates lightweight port-stub proxy bodies at the graph
  node with branch rail/lower-edge/cross-member snap targets,
- straight tray proxies are cut back around the branch fitting proxy,
- inferred main/branch may drive proxy visuals and warnings only,
- exportable procurement sizing must stay unresolved unless the branch intent
  is unambiguous or later user-confirmed.

## Offset And Move Are Different Commands

The current `Offset m` is a local face offset:

- positive/negative are relative to the segment left/right width axis,
- it is useful for reducer edge alignment,
- it does not move nodes,
- it does not change route length or graph topology.

KR's requested six-direction movement is a different operation:

- move segment or sub-run in global `+X`, `-X`, `+Y`, `-Y`, `+Z`, `-Z`,
- this changes route geometry,
- it may need inserted nodes at both ends,
- it may create bends, risers, reducers, or offset fittings at boundaries,
- it should be implemented after segment split/insert semantics exist.

Therefore the UI should eventually separate:

- `Face Offset`: local left/right face alignment,
- `Move Segment`: global route edit in six directions.

KR answer recorded 2026-07-18:

- `Face Offset` remains local and signed relative to segment width axis,
- global six-direction movement is a future route-edit command and should not
  be hidden inside `Offset m`.

## Rendering Strategy

Do not import vendor meshes for MVP.

First build a generic parametric accessory proxy engine:

- one merged `BufferGeometry` per run/accessory group where possible,
- low segment counts for curves,
- wireframe always available,
- shaded faces optional,
- metadata snap targets generated from accessory ports/edges,
- broad-phase AABB/OBB warnings generated from accessory proxy corners.

Later vendor replacement:

- if a manufacturer catalogue provides BIM/IFC/Revit/glTF data, map the
  accessory projection to a vendor part,
- use vendor mesh for visual/detail mode,
- keep the generic parametric proxy for clash approximation, fallback, and
  projects without vendor-specific catalogues.

## Accessory Library And Automation Doctrine

KR question recorded 2026-07-21:

- can a user-selectable accessory library/palette simplify bend, reducer,
  riser, tee, and cross development compared with automatically creating every
  accessory?
- would manual routing be simpler and more robust for MVP?

Decision:

- use a hybrid model,
- do not switch to manual-only accessories,
- do not attempt full automatic catalogue selection for MVP.

MVP doctrine:

1. The saved route/graph remains the engineering truth.
2. The server derives accessory candidates from topology, size transitions,
   direction changes, elevation changes, and face alignment.
3. The UI presents candidates as lightweight parametric proxies.
4. The user can accept, reject, override, or replace a candidate from an
   accessory palette/library.
5. User decisions are stored as accessory intent, not baked mesh vertices.
6. Vendor catalogue parts can later replace the generic proxy when selected.

Why not manual-only:

- manual placement may look simpler, but it risks drifting from cable route
  continuity, schedule quantities, clash envelopes, and later pathfinding,
- EPC users need traceability: each accessory must explain which route node,
  segment pair, or graph junction caused it,
- route optimization and cable routing need graph-aware fittings, not loose
  visual blocks.

Why not full automation-only:

- catalogue selection depends on vendor, project preference, bend radius,
  side/handedness, available parts, covers, dividers, branch orientation, and
  construction practice,
- forcing the system to decide all of that early will create brittle logic and
  unnecessary UI complexity.

Implementation implication:

- accessory defaults, validation rules, assumptions, and schedule semantics
  should live server-side,
- JavaScript should become a renderer and command surface,
- the palette should select or override projected accessory intent rather than
  hand-place disconnected geometry,
- command availability must be extracted into tested pure state functions
  before the palette grows.

## Persistence Plan

Phase 1: projection-only accessories.

- extend `raceway/fittings.py` to emit richer accessory projections,
- no new DB rows,
- include `accessory_key`, ports, assumption block, geometry recipe, and
  warnings.

Phase 2: user-resolved accessory intent in metadata.

- store only decisions that cannot be re-derived reliably:
  - reducer handedness,
  - selected bend radius/catalogue class,
  - riser inside/outside override,
  - tee main/branch decision,
  - accepted variable/custom fitting.

Phase 3: persisted accessory rows.

- add only after projection semantics survive manual use:
  - `RacewayAccessory`,
  - `AccessoryPort`,
  - optional `VendorPart`,
  - optional source geometry reference.

Do not persist baked vertices as authoritative design data.

## Implementation Order

Recommended next sequence:

1. Segment split/insert semantics. `coded enough for current branch nodes`
   - Needed for tee/cross and for segment movement boundaries.
   - Child segments inherit orientation and face-offset intent.
2. Reducer handedness UI. `coded v0`
   - User chooses left, right, or center.
   - `Apply Edge Match` becomes one possible helper, not the accessory itself.
3. Reducer proxy geometry v0. `coded v0`
   - Generate tapered transition body between two ports.
   - Expose assumptions and development length.
4. Bend/riser proxy geometry v0. `coded v0`
   - Replace simple markers with real bend/riser bodies.
5. Tee/Cross proxy geometry v0. `coded projection-only v0`
   - Requires split node and branch/main semantics.
6. Advanced accessories.
   - Wye, covers, dividers, couplers, supports, vendor models, and
     catalogue-grade persisted accessory intent.

## MVP Acceptance Sweep

Date: 2026-08-02
Status: accepted for Raceway MVP / Phase G closure.

The accessory arc is accepted as a graph-aware parametric proxy foundation, not
as a vendor-grade accessory catalogue.

| Accessory / workflow | MVP status | Authoritative for MVP | Explicit limitations |
| --- | --- | --- | --- |
| Reducer taper proxy | accepted | graph/fitting candidate, proxy visual, clash/schedule warning evidence | not vendor part selection; development length is heuristic unless catalogue/preference overrides later; handedness dropdown is drafting control until accessory intent persistence exists |
| `Apply Edge Match` | accepted as authoring aid | writes face-offset intent needed for one-edge matching | not itself a reducer; does not move centerline truth or create procurement identity |
| Plan bend proxy | accepted | bend count, advisory standard-angle flags, lightweight proxy geometry | bend radius is project-neutral/default unless later user/catalogue intent persists it |
| Riser proxy | accepted | riser count, elevation-change proxy, unresolved status where face orientation is ambiguous | vertical orientation inheritance remains a deferred refinement; inside/outside should not be guessed when ambiguous |
| Tee proxy and Make Tee | accepted | explicit graph-node branch proxy, count placeholder, visual/snap proxy | inferred main/branch may guide visuals/warnings only; procurement sizing remains unresolved unless unambiguous or later user-confirmed |
| Cross proxy and Make Cross | accepted | explicit graph-node cross proxy, count placeholder, visual/snap proxy | detailed catalogue cross body and branch-size variants remain deferred |
| Schedule/fitting quantities | accepted as informative | centerline straight lengths, placeholder counts, warning evidence | fitting development lengths are not deducted from straight lengths in MVP schedule basis |
| Accessory palette / accepted vendor part | deferred | none yet | future UI should accept/reject/override projected candidates and persist intent, not hand-place disconnected meshes |

Boundary rule retained from Claude §45:

- inferred branch/accessory intent may drive proxy visuals and warnings,
- inferred intent must not drive exportable procurement part sizing unless it
  is unambiguous or user-confirmed,
- catalogue-grade dimensions, handedness intent, bend radius, tee branch
  intent, covers/dividers/couplers, supports, and vendor meshes are post-MVP.

## Acceptance For First Reducer Geometry Pass

- Unequal-width connected runs produce an accessory projection with two ports.
- User can choose `left_edge`, `right_edge`, or `center`.
- The rendered reducer has a visible tapered body; no abrupt visual jump.
- The wider and narrower tray faces connect to the reducer ports.
- The route centerline and node keys remain unchanged.
- Fitting JSON documents development-length assumptions.
- Rough clash warning includes the reducer accessory envelope.
- Browser/manual test proves the old `Shift+T` helper is not mistaken for final
  reducer geometry.
- Reducer body trims or masks adjacent straight proxies at the accessory extents
  so shaded geometry does not overlap visibly.
- Fitting JSON states whether development length came from catalogue,
  preference, or heuristic.

## Open Questions

- Closed 2026-07-18, KR: default to `left_edge`, expose override, later project
  preference panel.
- Closed 2026-07-18, KR and Claude: use local heuristic first; vendor catalogue
  or project/user preference overrides later.
- Closed 2026-07-18, Claude: gate reducer auto-suggestion on near-collinearity
  using a named tolerance.
