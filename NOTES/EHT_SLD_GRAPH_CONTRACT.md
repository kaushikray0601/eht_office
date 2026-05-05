# EHT SLD Graph Contract

Date: 2026-04-23
Last updated: 2026-04-26

Status: Canonical contract for the current EHT SLD implementation

Purpose:
- define the payload and persistence contract used by the current EHT SLD
- make graph assumptions explicit before more editing features are added

## 1. Source Of Truth

The generated EHT SLD is currently derived from persisted power-distribution data:
- [PowerDistributionBranch.tagged_components](/home/kr/mydev/eht_office/eht/models.py:233)

The current stack is:
- graph generation: [eht/sld_payload.py](/home/kr/mydev/eht_office/eht/sld_payload.py:162)
- validation: [eht/sld_validation.py](/home/kr/mydev/eht_office/eht/sld_validation.py:117)
- layout persistence: [eht/sld_layout.py](/home/kr/mydev/eht_office/eht/sld_layout.py:35)
- browser rendering/edit shell: [static/js/sld_workspace.js](/home/kr/mydev/eht_office/static/js/sld_workspace.js:1)

## 2. Contract Scope

This document covers:
- generated payload structure
- node invariants
- edge invariants
- line-group invariants
- layout persistence invariants
- presentation-only regrouping behavior
- controlled topology-edit invariants

This document does not yet define:
- annotations/comments schema
- cross-module reusable graph document standard

## 3. Payload Shape

The current EHT SLD payload is a JSON object with:

```json
{
  "schema_version": 1,
  "project_id": "p1",
  "nodes": [],
  "edges": [],
  "line_groups": [],
  "meta": {
    "branch_count": 0,
    "node_count": 0,
    "edge_count": 0
  }
}
```

Schema versioning:
- `schema_version` is required at the top level of the public SLD payload.
- current supported version: `1`
- rich branch JSON also uses `schema_version` inside `tagged_components`; that
  internal source-data version is separate from the public graph payload version.
- validation fails payloads with missing or unsupported public `schema_version`.
- validation warns when stored branch `tagged_components` still require legacy
  fallback reconstruction. Fallback removal should happen only after the schema
  audit reports explicit component details and graph connections for all active
  branches.

## 4. Node Contract

Each node must contain:
- `component_id`
- `component_uid`
- `display_tag`
- `component_type`
- `display_name`
- `label`
- `line_id`
- `line_ids`
- `line_uid`
- `branch_index`
- `circuit_index`
- `metadata`

### 4.1 Node Identity Rules

`component_id` is the canonical stable node identity for a project graph.

Rules:
- must be unique within one project payload
- should remain stable across recalculation when the underlying topology meaning is unchanged
- is the key used by saved layout persistence
- uses the persisted process-line `line_uid` as the line identity scope; the
  display `line_id` remains payload metadata and may also appear in the readable
  component ID string, but must not be the only uniqueness scope

`component_uid` is a stable 32-hex-character derived identifier.

Rules:
- must be unique within one project payload
- is not the primary persistence key for layout

`display_tag` is the human-readable engineering tag.

Rules:
- must be unique within one project payload
- is allowed to change only when tag-generation rules intentionally change
- remains stable across recalculation for the same stored process-line set and
  sorted line order
- may legitimately renumber if process lines are inserted, deleted, or receive a
  changed sorting identity such as `xlid`, `line_id`, or `uid`
- must not be used as the primary technical persistence key

## 5. Edge Contract

Each edge must contain:
- `from_component_id`
- `to_component_id`
- `line_ids`
- `line_uid`
- `branch_index`
- `circuit_index`

Rules:
- both endpoints must resolve to real payload nodes
- edges are directional in the payload even if visually rendered as undirected lines
- `branch_index` must map to a real stored branch for the line(s) referenced

## 6. Line Group Contract

Each line group contains:
- `line_id`
- `line_uid`
- `branch_indices`

Rules:
- each line group represents one stored process line, keyed by `line_uid`
- `branch_indices` must match stored `PowerDistributionBranch` ownership for that line
- duplicate display `line_id` values produce separate line groups with distinct
  `line_uid` values
- browser line-focused navigation should rely on this structure rather than re-infer grouping ad hoc

## 7. Metadata Rules

Node `metadata` is domain-specific and may include values such as:
- breaker size
- cable length
- cable role
- branch type
- circuit count
- isolator location

Rules:
- metadata enriches presentation and inspection
- metadata must not be required as the only source of core node identity
- if metadata changes, layout should still survive if `component_id` is stable

## 8. Validation Expectations

The validation layer currently checks:
- branch count alignment
- uniqueness of display tags
- uniqueness of component IDs
- uniqueness of component UIDs
- edge endpoint resolution
- line-group ownership alignment
- branch topology counts against project setup

Reference:
- [eht/sld_validation.py](/home/kr/mydev/eht_office/eht/sld_validation.py:117)

## 9. Layout Persistence Contract

Saved layout is stored separately from the generated graph in `SLDNodeLayout`.

Rules:
- layout rows are keyed by `project + component_id`
- layout stores only position/orientation-related data, not topology
- generated graph remains the source for what nodes exist
- saved layout is valid only for nodes whose `component_id` still exists in the current payload

Current behavior:
- the save endpoint currently uses a merge/patch-style coordinate update
- omitted nodes are preserved, which allows line-focused or partial saves
- layout rows for components that no longer exist in the current generated
  payload are deleted defensively during save
- the layout response exposes `meta.save_mode = "merge"`
- line and branch regrouping is presentation-only: browser handles move groups
  of rendered component nodes, and save persists only the resulting component
  coordinates
- group handles are derived from `line_groups` and `branch_indices`; they are
  not saved as graph nodes and do not change generated edges or branch ownership

This behavior is intentional. Future changes must keep partial saves safe unless
the API contract is explicitly redesigned and tested.

## 10. Controlled Topology Edit Contract

Topology editing is an engineering override layer over the generated SLD.

Baseline rules:
- `PowerDistributionBranch.tagged_components` remains the generated baseline.
- topology edits must be stored separately from generated branch/source data.
- applying an edit must not rewrite or destroy the generated baseline.
- reset-to-generated means deactivating the applied edit layer, not rebuilding
  source calculation rows by hand.

First allowed edit types:
- `combine_feeders`: selected MCB feeder paths are combined into one edited
  feeder path.
- `split_circuits`: one selected multi-circuit MCB feeder is split into
  independent MCB-fed circuit paths.
- `downstream_jb`: selected outgoing branches of an upstream 3PH JB are moved
  under a new downstream 3PH JB through a new manual 4C trunk cable.
- `attach_to_jb`: one existing MCB-fed feeder path is reattached to an eligible
  3PH JB with spare outgoing capacity.
- `move_branch_to_jb`: one downstream branch root currently fed from a 3PH JB is
  moved to another eligible 3PH JB. Same-MCB moves keep breaker sizing
  unchanged; cross-MCB moves require a target breaker recommendation before
  apply.

Combine-feeder topology rule:
- a combined MCB must not directly feed multiple outgoing 3C power cables.
- the edited graph must insert a manual 4C trunk cable and 3PH junction box
  between the combined MCB and the existing outgoing feeder paths.
- when project settings require an incoming 3PH isolator, the manual combined
  feeder path must include that isolator before the 3PH junction box, matching
  the generated topology rule.
- required flow:
  `MCB -> Cable4C -> optional Isolator3PH -> JB3PH -> existing outgoing Cable3C/JB1PH/tracer paths`.
- the MCB, 4C cable, optional isolator, and 3PH JB must carry manual edit
  metadata and display-tag markers; cable sizing remains a review-required
  downstream design step.
- repeated combine operations may extend the active combine topology. In that
  case the new edit revision supersedes the previous applied revision and reuses
  the existing manual trunk/JB instead of creating another trunk layer.

Downstream-3PH-JB topology rule:
- the user selects one upstream `JB3PH` and then selects direct outgoing branch
  root components fed by that JB.
- the edit inserts `JB3PH -> Cable4C -> optional Isolator3PH -> JB3PH`
  between the selected upstream JB and the moved branch roots.
- the optional isolator is included when the project isolator setting requires
  incoming 3PH isolation for 3PH junction boxes.
- the new 4C trunk length is entered during the edit flow, with the project
  `loop_ln` value as the default.
- in this pass, each 3PH JB may feed at most three direct outgoing feeders. The
  upstream JB must remain within that limit after selected branches are moved,
  and the new downstream JB may receive at most three moved branches.
- the new cable and downstream JB must carry manual topology metadata and remain
  review-required engineering data for later cable sizing and validation passes.

Attach-to-JB topology rule:
- the user selects an existing MCB-fed feeder/circuit and an eligible target
  `JB3PH`.
- the selected source MCB must have a single outgoing feeder entry in this first
  pass. More complex multi-outgoing source moves should be handled by split or
  by a later branch-level reassignment workflow.
- the target `JB3PH` must remain within the configured outgoing-feeder limit
  after the feeder is attached.
- the selected source MCB is removed from the edited graph and its outgoing
  feeder entry is reconnected to the selected target `JB3PH`.
- when a branch is attached to a standalone target MCB, that MCB is promoted
  to a manual 3PH distribution path using
  `MCB -> Cable4C -> optional Isolator3PH -> JB3PH`, with the optional
  isolator governed by the same project incoming-isolator setting.

Redundant 3PH-JB simplification rule:
- after an edited topology rewires branches, any `JB3PH` with exactly one
  incoming and one outgoing path is treated as a redundant distribution point.
- the renderer/export graph should not show that as a live 3PH distribution
  island. The edit layer removes the single-purpose upstream `Cable4C`,
  optional `Isolator3PH`, and `JB3PH` chain when it is safe to do so, then
  reconnects the upstream source directly to the remaining branch root.
- this simplification is intentionally graph-local: it does not rewrite the
  generated baseline, and reset-to-generated still restores the original
  calculated topology.

Split topology rule:
- split works against the active SLD graph, not only the generated baseline.
  This allows an engineer to split a manually combined feeder without first
  discarding unrelated manual topology edits.
- when one generated multi-circuit line is split, the edited line identities
  continue to use `-partN` suffixes.
- when a manual combine of distinct line IDs is split, each resulting feeder
  keeps its original line identity instead of receiving a synthetic part suffix.
- the generated baseline snapshot remains stored with the edit, so full
  reset-to-generated still returns to the original calculated arrangement.
- the upstream MCB feeding the target JB receives a review-required breaker
  recommendation based on the previous target-source rating plus the removed
  source MCB rating.
- this is the first guided graph operation: user intent is "feed this circuit
  from that JB"; detach/attach edge rewiring, capacity validation, downstream
  summary updates, and audit persistence are system responsibilities.

Move-branch-to-JB topology rule:
- the user may select any component in a downstream branch, such as `Cable3C`,
  `JB1PH`, tracer, or end termination.
- the system resolves that selection back to the direct branch root fed by the
  current source `JB3PH`.
- the target may be a different `JB3PH` with spare outgoing capacity, or a
  standalone one-outgoing `MCB` that can be promoted into a proper 3PH
  distribution point.
- the edit removes only the source-JB-to-branch-root edge and adds the
  target-JB-to-branch-root edge. Downstream branch components remain intact.
- when the target `JB3PH` is under a different upstream MCB, the system
  estimates the moved branch rating from the source MCB and source-JB outgoing
  count, reduces the source MCB to the next configured breaker size for the
  remaining outgoing branches, and uprates the target MCB to the next configured
  breaker size. These recommendations remain review-required engineering data
  until detailed load/cable sizing is added.
- when the user targets a standalone one-outgoing MCB instead of an existing
  `JB3PH`, the system inserts a manual `Cable4C -> JB3PH` distribution point
  under that MCB, reconnects the original outgoing feeder and moved branch under
  the new JB, and applies the same target-MCB breaker recommendation.
- this operation exists so users do not have to split and recombine a manually
  engineered SLD just to move one outgoing branch after plant layout review.

Selectable-link editing rule:
- rendered SLD links may be selected as a UI convenience, but raw link
  delete/create is not a valid topology operation by itself.
- a selected link represents the downstream component fed by that connection and
  may seed a guided graph operation such as attach/move.
- any persisted topology change must still pass through a named graph operation
  with electrical validation, audit trail, reset-to-generated behavior, and
  downstream BOQ/cable-schedule consistency.
- drag/drop topology editing is deferred for now. The accepted interaction
  pattern is guided intent selection, such as "move this branch" and "feed
  selected branch here", backed by preview/apply validation. This keeps the SLD
  tool adaptable without turning the browser canvas into an unsafe freeform CAD
  editor before the domain rules are complete.

Split-circuit topology rule:
- the user selects the MCB that currently feeds multiple outgoing circuits, not
  an individual downstream branch component.
- the edited graph removes the shared multi-circuit distribution path between
  the MCB and the fan-out point, then reconnects each outgoing circuit entry to
  its own MCB.
- the original MCB remains assigned to the first outgoing circuit and receives a
  split marker; additional circuits receive new manual MCB nodes.
- each split circuit is displayed as a complete source-to-load electrical
  circuit. The display line ID uses the original line ID with `-partN` suffixes
  while preserving the original line ID/UID in metadata for traceability and
  focused filtering.
- the recommended MCB rating is the source MCB rating divided across the split
  circuits, rounded up to the next configured breaker size. The recommendation
  remains review-required engineering data, not an automatic final issue value.

Workflow rules:
- selection and preview are transient UI/server state.
- the user must run validation before applying an edit.
- only applied topology edits become the active basis for SLD, BOQ, cable
  schedule, and connected-load summaries.
- failed or abandoned previews must not affect downstream outputs.
- the generated baseline must remain available for comparison and reset.

Recommended persistence shape:
- use a first-class topology-edit table, not JSON embedded in existing result
  rows.
- JSON is acceptable inside that table for generated snapshots and edit payloads,
  but audit/provenance fields must be queryable.

Required audit/provenance fields:
- project
- edit type
- status, such as `applied`, `superseded`, or `reset`
- created by
- created at
- optional user remarks
- generated baseline fingerprint
- generated snapshot for the affected feeder paths
- edit payload
- validation summary

Tagging rules:
- edited display tags should carry a clear manual marker, for example `-M`.
- technical identity must remain separate from display tag text.
- inspector and reports must show that a component/path is manually edited.

MCB sizing rules for combine edits:
- sum the selected feeder ratings/load basis.
- choose the next available standard MCB rating.
- highlight the proposed rating as user-review-required.
- allow user override, then validate against available ratings and loading
  limits before apply.

Recalculation rules:
- recalculation always regenerates the baseline.
- applied topology edits may survive recalculation only when their referenced
  generated components/feeder paths can still be matched.
- if the baseline fingerprint or referenced components no longer match, the edit
  must be marked for review instead of being silently reapplied.

## 11. Backward Compatibility

The payload builder currently supports:
- rich branch JSON with explicit `component_details` and `connections`
- legacy branch JSON through fallback reconstruction

Reference:
- [eht/sld_payload.py](/home/kr/mydev/eht_office/eht/sld_payload.py:105)

## 12. Near-Term Contract Decisions

Before advanced editing begins, we must decide:
- whether a normalized graph table is needed beyond branch JSON
- how concurrent layout saves will be detected or reconciled
- how viewport preferences should be persisted separately from node coordinates

## 13. Current Canonical Endpoints

The canonical EHT SLD endpoints are:
- workspace view: `/sld/workspace/`
- payload view: `/sld/payload/`
- validation view: `/sld/validation/`
- layout load/save: `/sld/layout/`
- layout reset: `/sld/layout/reset/`

Filtering:
- `/sld/workspace/`, `/sld/payload/`, and `/sld/layout/` accept an optional
  `line_id` query parameter for one-line focused browsing.
- `line_id` matching is case-insensitive, but successful responses normalize the
  selected line back to the canonical `line_id` from the generated payload.
- filtered payload/layout responses include only nodes and edges owned by the
  selected line; layout saves still validate against the full current graph so
  omitted nodes from other lines are preserved.

The old standalone prototype route is no longer part of the canonical SLD path.
