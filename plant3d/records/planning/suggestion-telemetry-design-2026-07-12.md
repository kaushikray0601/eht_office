# Suggestion Telemetry (`suggestion_event`) — Tier-0 Design Note

Date: 2026-07-12
Author: Claude (architect), parallel work while Codex codes Stage 10
Audience: KR + Codex
Status: design note for the next architecture pass — small by intent
Parent: `raceway-methodology-and-ai-strategy-2026-07-11.md` (Tier 0) + Codex addendum C-3

## Purpose

Record every suggestion the software shows and what the engineer did about it, so that later AI ranking (Tier 2) has labeled training data from day one. This is the data flywheel's intake valve. It must cost almost nothing now and never influence current behavior.

## Design rules (non-negotiable)

1. **Observation only.** Telemetry never changes what the user sees. A failed telemetry write must never break a save or a warning display.
2. **Consumer-neutral.** `owner_module` + string codes, exactly like the overlay-anchor pattern. Raceway is the first producer; EHT/lighting join later with zero schema change.
3. **No FKs to domain tables.** Loose `project_id` string and UUID keys (`run_key`, `node_key`) only — extraction-safe, same discipline as everything else.
4. **Stays inside the deployment.** Events live in the project database and never leave it by default. Cross-project/fleet aggregation is a separate, explicit, consented future decision (belongs to decision record 0007 / `ai_gateway`).
5. **Log transitions, not renders.** A warning re-rendered 50 times in a session is one fact, not 50 rows.

## Where it lives

Recommend a minimal new peer app **`telemetry`** (one model, one endpoint, imports nothing from any domain app; domain apps import it). Rationale: the first producer exists *today* (Stage 10 warnings), and starting shared avoids a table-move migration when EHT/lighting join. Acceptable fallback if Codex prefers: raceway-owned table now, consumer-neutral columns, promotion later — Codex's call, record it either way.

## Schema — `SuggestionEvent`

| Field | Type | Notes |
|---|---|---|
| `id` | auto PK | |
| `key` | UUID, default, indexed | groups one suggestion's lifecycle (shown → acted) |
| `created_at` | datetime auto | |
| `user` | FK AUTH_USER_MODEL, SET_NULL | |
| `project_id` | char(80), indexed, loose | gateway-validated at write |
| `owner_module` | char(40) | `"raceway"` today |
| `suggestion_code` | char(120), indexed | e.g. `raceway.graph.near_miss_endpoint`, `raceway.ortho.axis_lock`, future `raceway.route.candidate` |
| `action` | choices | `shown` \| `accepted` \| `rejected` \| `edited` \| `dismissed` \| `unresolved_at_save` |
| `context` | JSON | the suggestion's own evidence payload (warning body, thresholds, distances, run/node UUID keys) — reuse the existing warning shape verbatim |
| `action_detail` | JSON | edit delta, chosen candidate index, time-to-action seconds |
| `client` | char(80), blank | overlay cache key, for version-aware analysis later |

Indexes: (`project_id`, `suggestion_code`), (`suggestion_code`, `action`), `created_at`.

## Event taxonomy v0 (maps to features that already exist)

| Source | `shown` | Resolution events |
|---|---|---|
| Near-miss endpoint warning | first appearance in a session per (`node_key`, code) | `accepted` = user connects/moves endpoint and warning disappears from next projection; `unresolved_at_save` = still present when drafts saved |
| Unconnected crossing warning | same | same |
| Ortho assist | segment committed with ortho adjustment applied | `accepted` = survives; `rejected` = undone/moved off-axis within the session |
| Short-segment / excessive-bends warnings | first appearance | resolved / `unresolved_at_save` |
| (Future) Dijkstra route candidates | candidates presented | `accepted` (+index), `edited` (+delta), `rejected` |

Resolution detection is client-side diffing of consecutive projections — cheap, and it's already how the panel refreshes.

## Ingestion

`POST /telemetry/events/` (batch array), session+CSRF auth, project access via the gateway pattern, schema-validated per event, rate-limited (reuse the eht `django-ratelimit` pattern), silently capped batch size. Client: one small fire-and-forget batched helper in the overlay (queue, flush on interval/save/unload); failures logged to console only.

## Explicitly NOT in scope

Dashboards/analytics UI; third-party analytics SDKs; model training; any PII beyond the user FK; any cross-deployment transmission; any behavior change driven by the data. Retention/pruning policy deferred until volume is real (revisit when a table passes ~1M rows).

## Acceptance for the implementation pass

- Events written for at least two sources (one warning code + ortho).
- A failed/blocked telemetry endpoint provably does not affect authoring or save (test).
- Events carry UUID keys, not domain PK FKs (test).
- Project access enforced on ingestion (test).
- Tracker + this note updated with what shipped.

Sizing: model + migration + endpoint + two client hooks ≈ one small pass, comparable to the catalogue-endpoint pass.
