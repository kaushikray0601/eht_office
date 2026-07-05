# plant3d Platform Boundary & Overlay Contract — v1 (RFC)

Date: 2026-07-05
Author: Claude (architect), at Codex's request in `extraction-readiness-and-claude-brief-2026-07-04.md`
Audience: KR + Codex
Status: design proposal — grounded in the actual current code (2026-07-05), not an abstract ideal

## 0. What this is and why it's shaped this way

Codex asked for two linked things: (A) the public `plant3d` API/boundary contract, and (B) a generic viewer overlay/layer contract so EHT, raceway, and future modules can share one viewer without coupling their data models. They're one document because they're one seam — every response over the API *is* what a rendered overlay is built from.

Every claim below was checked against the real code (`urls.py`, `views.py`, `models.py`, `services.py`, `package_viewer.js`, `project_gateway.py`, and `idfviewer/models.py` for the anti-pattern). Where I found a gap or leak while grounding this, I've named it as a concrete, actionable finding rather than folding it silently into "the ideal design."

---

## 1. Design principles (nothing new — this formalizes what's already been decided)

- **Neutral platform, consumer modules.** Decisions 0001, 0004, 0005 and the raceway RFC already establish: `plant3d` owns geometry/identity/rendering; EHT/raceway/future modules own domain meaning and persistence. This document is the *contract* that makes that boundary enforceable rather than just intended.
- **The anti-pattern to name explicitly:** `idfviewer.EHTDesignElement` ([idfviewer/models.py:162](../../../idfviewer/models.py#L162)) bakes an EHT-specific `ELEMENT_TYPES` enum and a hard FK to `IDFFile` directly into the viewer app. That is exactly what happens when a consumer's domain model gets welded into the platform: it can never serve a second consumer (PCF-only, raceway, a future review tool) without duplication or deeper coupling. Every design choice below exists to make that mistake structurally hard to repeat.
- **Stable identifiers, not relationships.** Consumers reference `plant3d` by opaque IDs (`project_id`, source id, package id, `ModelObject.stable_id`) — never by importing `plant3d` models, joining its tables, or holding a Django FK into it. This mirrors `project_gateway.py`'s own shape (`plant3d → eht` is exactly the relationship `consumer → plant3d` must be).
- **Additive evolution, not silent breakage.** A public contract is a promise. The rule from here on: adding a new field/key is safe; removing, renaming, or repurposing an existing one requires a version marker and a deprecation window, not a quiet edit.

---

## 2. Stability tiers

Every field in every response now belongs to one of three tiers. This is the single most load-bearing idea in this document — it lets Codex keep improving `plant3d` fast without breaking consumers, because only **STABLE** fields are promises.

| Tier | Meaning | Consumers may |
|---|---|---|
| **STABLE** | Frozen shape; part of the public contract | Depend on it across releases; write tests against it |
| **PROVISIONAL** | Present today, shape may still change | Read it, but must tolerate absence/change; not a promise |
| **INTERNAL** | Debug/diagnostic only | Must not be read by any consumer module; may vanish any time |

---

## 3. Part A — Public API Contract

### 3.1 Stable identifiers

| Identifier | Type | Meaning |
|---|---|---|
| `project_id` | string | EHT `proj_id`, opaque to `plant3d`; validated via `project_gateway.validate_project_id` |
| Source id | int | `SourceModel.pk` |
| Package id | int | `RenderPackage.pk` |
| Tile id | int | `RenderTile.pk` |
| Job id | int | `ConversionJob.pk` |
| `ModelObject.stable_id` | string | Stable per-object identity within a source (`ifc:{GlobalId}` or a deterministic fallback) — **the** anchor key for overlays |
| Feature id | int | Package-local vertex-attribute id (`_FEATURE_ID_0`); resolves to a `ModelObject` via the package's sidecar, **not stable across packages** |

### 3.2 Endpoint reference (as it exists today, tier-tagged)

| Endpoint | Tier | Notes |
|---|---|---|
| `GET /plant3d/sources/` | STABLE | List view. **Gap found:** no per-source JSON endpoint exists — only this list and the HTML detail page. Recommend adding `GET /sources/<id>/json/` mirroring `job_json_view`'s shape, so a consumer can poll one source without scraping HTML or filtering the list. |
| `POST /plant3d/sources/upload/` | STABLE (session-authenticated) | Requires Django session today; needs the Stage-1 token layer before a non-browser caller can use it |
| `POST /plant3d/sources/<id>/save-case/`, `/delete/` | STABLE | Owner/access-checked as documented elsewhere |
| `POST /plant3d/sources/<id>/convert-{metadata,ifc-geometry,ifc-glb}/` | STABLE | Returns `{job: {id, job_type, status, progress_percent, url}, process_hint, worker_hint}`; `metrics` is **PROVISIONAL** (diagnostic shape evolves) |
| `GET /plant3d/jobs/<id>/json/` | STABLE | `id, source_model_id, job_type, status, progress_percent, error_message`. `metrics`/`timing_summary` = **PROVISIONAL** (already correctly separated from the raw `metrics` dict — good existing practice, keep it) |
| `GET /plant3d/packages/<id>/json/` | STABLE core, with two leaks to fix (below) | `object_count, tile_count, byte_size, coordinate_unit, coordinate_frame, bounds, objects[], tiles[], tileset` |
| `GET /plant3d/objects/<id>/json/` | STABLE | `stable_id, object_type, tag, line_id, bounds, selection_summary` |
| `GET /plant3d/tiles/<id>/json/` (sidecar), `/blob/` (binary) | STABLE | Reached only via `tiles[].url`/`blob_url` in the package payload — **this is the correct pattern**, apply it to the one leak below |

### 3.3 Two concrete leaks found — fix before freezing the contract

1. **`package_json_view` returns `manifest_storage_key`** ([views.py:400](../../views.py#L400)) — a raw storage key, exactly the kind of internal detail Codex's brief said must not be exposed. Tiles already avoid this correctly (`url`/`blob_url`, not `storage_key`). Fix: drop `manifest_storage_key` from the response, or replace it with a resolved `tileset_url` if the manifest ever needs direct fetching.
2. **RTC/coordinate-transform fields are buried inside the `metadata` JSON blob**, not promoted to top-level response keys. `package.metadata`/`tile.metadata` today mix genuinely load-bearing data (`coordinate_transform`, `origin_source_xyz`, `rtc_origin_render_xyz`) with diagnostic data (`meshopt_compression`, timing hints). A consumer cannot tell which sub-keys are promises. **Recommend:** promote `coordinate_transform` to an explicit top-level key in both `package_json_view` and the tile payload (view-layer change only, no migration needed — the data already exists in `metadata`), and leave `metadata` explicitly documented as **INTERNAL/opaque**.

### 3.4 The RTC coordinate contract (STABLE — this is the physics, freeze it explicitly)

Grounded exactly in `services.py`'s existing keys — this section *names* what already exists as frozen, it doesn't invent anything:

```
source_axis_order:  ["x", "y", "z"]      # source/IFC convention, Z-up
render_axis_order:  ["x", "z", "y"]      # glTF/Three.js convention, Y-up
origin_source_xyz:      [x, y, z]        # tile/package center, in source coordinates
rtc_origin_render_xyz:  [x, y, z]        # same center, axis-swapped + scaled, in render coordinates
scale_to_m:              float

render_world_xyz_m      = rtc_origin_render_xyz + local_position_xyz_m
source_xyz              = [render_world.x/scale, render_world.z/scale, render_world.y/scale]
```

Any module placing geometry (a tray support, an EHT device, a future annotation) **must** compute its position through this exact formula, using the *package's* `rtc_origin_render_xyz` — never invent a second origin. This is the one piece of this contract where a small mistake produces a silently-wrong 3D position, so it deserves a named contract test (§6).

### 3.5 Auth note

Today's entire contract assumes a Django session (`request.user`, `LoginRequiredMiddleware`). That's fine and correct for the current co-located stage. It is **not yet** a contract a separate process/service could call — that requires the signed-token layer decision 0005 already named. Do not build a non-browser API caller against this contract until that lands.

---

## 4. Part B — Overlay/Layer Contract

### 4.1 The rule

`plant3d` renders geometry and exposes identity. **It does not persist, model, or render domain-specific overlay data.** Consumer modules (EHT-integration, raceway, future cable-routing) each own their own Django app, their own persistence, their own business rules — and each anchors its objects to `plant3d` using one shared, documented shape. This is deliberately **not** a shared database table (that would recreate `EHTDesignElement`, just generalized) — it's a shape every consumer implements independently, the same way BCF is a shape many BIM tools implement without a shared "BCF service," or the way IFC's GUID reference works: a stable pointer, interpreted independently by whoever holds it.

### 4.2 `OverlayAnchor` — the shared shape

```python
@dataclass(frozen=True)
class OverlayAnchor:
    package_id: int
    coordinate_frame: str          # "model_object" | "render_xyz_m"
    model_object_stable_id: str = ""   # set when snapped to plant geometry
    position_xyz: tuple = ()           # set when coordinate_frame == "render_xyz_m"
    owner_module: str = ""             # e.g. "eht", "raceway" — for provenance/debug only
```

Two cases, both real: **snapped** (references `model_object_stable_id`; position is resolved live from that object's current geometry — e.g. a tray support hanging off beam B-0472) and **free-positioned** (a raw `position_xyz` in the package's render frame — e.g. a manually placed device with no structural anchor). A consumer's own model stores one of these two shapes (as explicit fields or a small JSON column following this shape) — `plant3d` never stores it.

### 4.3 What `plant3d` provides (mirrors `project_gateway`'s shape exactly)

A small `plant3d/overlay.py` module, analogous to `project_gateway.py`:

```python
def resolve_anchor_position(anchor, package) -> tuple[float, float, float]:
    """Snapped -> current ModelObject position via RTC contract. Free -> position_xyz as-is."""

def validate_anchor(anchor, user) -> bool:
    """Confirms package_id is accessible to user and, if snapped, that
    model_object_stable_id exists in that package. Read-only, no persistence."""
```

This is the entire platform-side surface for overlays: a resolver and a validator, not a table. Consumers call it the same way `forms.py` calls `project_gateway.validate_project_id` — a function call today, an API call after Stage 1, with zero change to consumer-side code either time.

### 4.4 Client-side: formalize the existing ad hoc groups into a registration API

`package_viewer.js` already has the right instinct — `root`, `ehtDraftGroup`, `pendingRouteGroup`, `measurementGroup` ([package_viewer.js:89-96](../../static/plant3d/js/package_viewer.js#L89)) are effectively one overlay group per feature, just not named as a contract and not something a future module (raceway) can hook into without editing this file directly. Formalize it:

```javascript
function registerOverlayLayer({ id, ownerModule, resolvePosition }) {
  const group = new THREE.Group();
  group.userData = { ownerModule, layerId: id };
  scene.add(group);
  return group;   // consumer module adds/removes its own Object3D children
}
```

`ehtDraftGroup`/`measurementGroup`/`pendingRouteGroup` become the first three callers of this function rather than special-cased globals. Raceway's future JS calls the same function for its own overlay group — no edits to core viewer internals required, and no risk of one module's globals colliding with another's (a real, if currently small, risk with 44 module-level `let`s already flagged in STRUCT1).

### 4.5 Worked example — proving the shape generalizes

- **EHT (future, replacing today's unpersisted draft tools):** a `DesignElement` model in an `eht`-owned app, with `anchor = OverlayAnchor(model_object_stable_id="ifc:3kP7...", coordinate_frame="model_object")`. On load, EHT's own view calls `resolve_anchor_position` to place it, and registers its own overlay group via `registerOverlayLayer({id: "eht-devices", ownerModule: "eht", ...})`.
- **Raceway (per the RFC):** `TraySupport.anchor = OverlayAnchor(model_object_stable_id="ifc:beam-472", ...)` — identical shape, different owning app, zero coupling between the two.

Both consume the same two platform functions and the same registration call. Neither imports the other's models. That's the proof this contract is genuinely generic, not EHT-shaped with raceway bolted on.

---

## 5. Research synthesis (tied directly to the choices above, not standalone)

1. **BCF (BIM Collaboration Format)** — the industry's answer to "how do you attach an issue to a BIM object + a coordinate + a viewpoint" without a shared server: a self-contained shape (component GUID reference + camera/clipping state), implemented independently by every tool that reads it. `OverlayAnchor` borrows exactly this idea at a smaller scale.
2. **Speckle's object model** (Stream → Commit → objects with a stable `applicationId`, grouped by "Collections") — the precedent for treating cross-discipline federation as *reference by stable id*, not shared schema. Reinforces stable-id-only, no-shared-table.
3. **IFC GUID referencing** — the same pattern one layer down: an IFC GlobalId is a portable pointer any tool can hold without owning the file. `ModelObject.stable_id` already follows this; §4 just extends the same idea to consumer overlays.
4. **Auth for future extraction** — already decided in 0005 (short-lived signed token over hot-path API calls). Nothing new here; §3.5 just states the current-stage caveat plainly.
5. **Orphan reporting after the FK→string change** — a lightweight periodic check ("list `plant3d` `project_id`s that no longer resolve in EHT") is a `project_gateway`-adjacent management command, not urgent now; noted so it isn't forgotten once Stage 1 pressure appears.

---

## 6. Contract tests (extends Codex's "harden project_gateway tests" ask)

Propose a dedicated `plant3d/tests_contract.py` (or a clearly marked section in `tests.py`) that pins **STABLE** tier fields only:

- Package JSON always contains exactly the STABLE keys listed in §3.2 (fails loudly if one is renamed/removed; passes silently if a new field is added — enforcing the additive-only rule automatically).
- The RTC round-trip test already exists for the service layer (F1) — add one at the **API response** layer: fetch a package's JSON, apply the documented formula from §3.4 using only the response's own fields, and confirm it reconstructs the known source bounds. This catches a future refactor that accidentally changes what's serialized, not just what's computed internally.
- `OverlayAnchor` resolver: a snapped anchor against a real `ModelObject` resolves to a position within its bounds; an anchor referencing a nonexistent `stable_id` fails `validate_anchor` cleanly (no exception).

---

## 7. Explicit non-claims (say what this is NOT, so it isn't overclaimed)

- This contract does not make `plant3d` callable from outside a Django session yet (§3.5).
- It does not prove precision at plant-global scale (F3 remains open regardless of this document).
- It does not retroactively fix `manifest_storage_key`/metadata-promotion — those are recommended fixes, not yet applied.
- It is a v1 — expect additive revisions as raceway becomes the second real consumer and actually exercises `OverlayAnchor` in anger.

---

## 8. Immediate next actions for Codex

1. Fix the two leaks in §3.3 (drop `manifest_storage_key`; promote `coordinate_transform` to a top-level key) — small, view-layer only.
2. Add `GET /sources/<id>/json/` (the missing per-source endpoint).
3. Add `plant3d/overlay.py` with `OverlayAnchor`, `resolve_anchor_position`, `validate_anchor` (§4.2–4.3).
4. Add `registerOverlayLayer()` to the viewer and migrate `ehtDraftGroup`/`measurementGroup`/`pendingRouteGroup` onto it (§4.4) — behavior-preserving refactor, existing tests should still pass unchanged.
5. Start `tests_contract.py` per §6, beginning with the STABLE-field pin test and the API-layer RTC round-trip.
6. Only after 3–4 exist: revisit the raceway placement decision — build its first `TraySupport.anchor` against this exact contract as the real-world proof.

## 9. Open questions for KR / Codex

1. Agree with the three-tier stability model, or prefer a simpler two-tier (stable/internal) split?
2. Any objection to the two leak fixes in §3.3 — either is a response-shape change, technically breaking if anything already depends on the old shape (unlikely at this stage, but worth a conscious yes)?
3. Does `OverlayAnchor` as a plain dataclass/shape-convention (not a DB table) match KR's mental model, or was a shared `plant3d`-owned "annotations" table actually intended? (I'd push back on that — it's the `EHTDesignElement` mistake again — but flagging it as a real fork, not assuming.)
