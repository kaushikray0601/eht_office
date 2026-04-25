# EHT SLD Graph Contract

Date: 2026-04-23
Last updated: 2026-04-25

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

This document does not yet define:
- user-authored topology overrides
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

`component_uid` is a stable short derived identifier.

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

## 10. Backward Compatibility

The payload builder currently supports:
- rich branch JSON with explicit `component_details` and `connections`
- legacy branch JSON through fallback reconstruction

Reference:
- [eht/sld_payload.py](/home/kr/mydev/eht_office/eht/sld_payload.py:105)

## 11. Near-Term Contract Decisions

Before advanced editing begins, we must decide:
- whether user-authored topology deltas are stored separately from generated topology
- whether a normalized graph table is needed beyond branch JSON
- how concurrent layout saves will be detected or reconciled
- how viewport preferences should be persisted separately from node coordinates

## 12. Current Canonical Endpoints

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
