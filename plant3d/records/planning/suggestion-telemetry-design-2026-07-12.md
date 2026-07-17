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
| --- | --- | --- |
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
| --- | --- | --- |
| Near-miss endpoint warning | first appearance in a session per (`node_key`, code) | `accepted` = user connects/moves endpoint and warning disappears from next projection; `unresolved_at_save` = still present when drafts saved |
| Unconnected crossing warning | same | same |
| Ortho assist | segment committed with ortho adjustment applied | `accepted` = survives; `rejected` = undone/moved off-axis within the session |
| Short-segment / excessive-bends warnings | first appearance | resolved / `unresolved_at_save` |
| Rough model clash / clearance warnings | first appearance | resolved / `unresolved_at_save` |
| (Future) Dijkstra route candidates | candidates presented | `accepted` (+index), `edited` (+delta), `rejected` |

Resolution detection is client-side diffing of consecutive projections — cheap, and it's already how the panel refreshes.

## Event dictionary v0

Context is telemetry-sanitized before storage: primary-key-like fields are
removed, while durable UUID keys and stable model object ids are preserved.

| `suggestion_code` | Context shape |
| --- | --- |
| `raceway.warning.model_clash_aabb` | warning payload with `run_key`, `run_tag`, `node_keys`, `segment_index`, `source_point_m`, and `values.method = "aabb"`, `values.clearance_m`, `values.gap_m`, `values.object_stable_id`, `values.object_source_object_id`, `values.object_type`, `values.object_label`, `values.object_bounds`, `values.raceway_bounds` |
| `raceway.warning.model_clearance_aabb` | same as `model_clash_aabb`; `gap_m` is the rough AABB gap inside the configured broad-phase clearance band |
| `raceway.warning.model_clash_scan_limited` | layer-level warning payload with `values.scan_limit`; indicates the broad-phase object-bounds scan was capped and warnings may be incomplete |
| `raceway.warning.service_mismatch_at_junction` | graph-node warning payload with `run_keys`, `run_tags`, `source_point_m`, and `values.graph_node_key`, `values.graph_node_kind`, `values.service_classes`, `values.member_count`, `values.members[]` containing run key/tag, service class, segment index, and node keys |
| `raceway.warning.face_offset_step_at_node` | route-node warning payload with `run_key`, `run_tag`, `node_keys`, `segment_index`, `source_point_m`, and `values.node_key`, `values.previous_segment_key`, `values.next_segment_key`, `values.previous_face_offset_m`, `values.next_face_offset_m`, `values.face_offset_delta_m`, `values.epsilon_m`, `values.recommended_action` |
| `raceway.reducer.edge_match_offset` | reducer suggestion payload with `fitting_key`, `category`, `graph_node_key`, `graph_node_kind`, `source_point_m`, `recommended_handedness`, `current_status`, `centerline_aligned`, `run_key`, `run_tag`, `node_key`, `segment_key`, `segment_index`, `width_mm`, `current_face_offset_m`, `suggested_face_offset_m`, `delta_face_offset_m`, and `max_recommended_offset_delta_m`; `accepted` action includes previous/applied offsets and `source = "apply_edge_match_command"` |

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

---

## Scale analysis and carry-forward register (added 2026-07-13, Claude, at KR's request)

### Volume arithmetic — large project, 10 concurrent designers

Aggressive bound: 1 event/designer/minute × 8 h × 10 designers ≈ **5,000 events/day** (realistic is 1,000–3,000/day, since we log suggestion *transitions*, deduped per session — not every click). At ~1–2 KB/row (UUID + strings + two JSONB blobs + index share):

| Horizon | Rows | Disk (incl. indexes) |
| --- | --- | --- |
| 1 project-year (aggressive) | ~1.25 M | ~1.5–2.5 GB |
| 2-year mega-project | ~2.5 M | ~3–5 GB |
| 10 concurrent projects, 1 year | ~12 M | ~15–25 GB |

Write rate: 0.06/s average, ~20/s worst-case burst (already capped by the 120/min/user rate limit). PostgreSQL routinely serves tables of **billions** of rows and multi-TB size; an append-only, never-updated event table written via `bulk_create` is its easiest possible workload. **Verdict: plain PostgreSQL is comfortably sufficient for years at this scale. No second database type is needed now, and every future upgrade we would choose is Postgres-native or file-based — no architecture change on any horizon we can see.**

### Where the real scaling questions live (not raw size)

1. **Analytics/training queries, not writes.** Extracting training data means OLAP-style scans over an OLTP table. Policy: **never train against the live DB** — snapshot to files (Parquet; readable by DuckDB/pandas offline) when Tier 2 starts. Until then, simple aggregate/materialized views (acceptance rate by code and threshold) deliver the threshold-calibration value with zero new infrastructure.
2. **Retention.** Trigger recorded: at **~10 M rows or ~10 GB**, introduce monthly range partitioning (native Postgres) so retention becomes "drop partition," plus an archival-to-Parquet policy. Additive change; nothing about today's schema blocks it.
3. **Vectorization — two different needs, only one involves vectors.**
   - *Tier-2 learned ranking* (the flywheel) is **tabular** learning: engineered features from the context JSON (distances, bend counts, thresholds) → accept/reject labels. Gradient-boosted trees/logistic models. **No embeddings, no vector DB.**
   - *Tier-1 RAG* (evidence narrator, NL query over manuals/evidence) is where embeddings enter. Decision parked with `0007-ai-gateway`: use **pgvector** (a Postgres extension; HNSW-indexed, handles millions of vectors) — preserves the single-database, on-prem-deployable story. A separate vector-DB service (Pinecone/Qdrant/etc.) is unjustified at our scale and would complicate the on-prem sales line for nothing.
   - The schema doesn't block either path: embeddings, if ever wanted over "design situations," are a derived column/table computed from the existing JSONB context — additive.

### What the shipped schema already got right for scale

Append-only immutable rows (trivial to partition/archive; event-sourcing-clean); UUID lifecycle keys that never join to mutable state; durable loose refs so events stay interpretable after runs are edited/deleted; JSONB context = new suggestion types without migrations (GIN-indexable if querying into context ever matters); `owner_module`/`suggestion_code` namespacing = multi-consumer without schema change; `client` version tag = drift analysis across releases; batch + rate-limited write path.

### Carry-forward register (for future passes — none urgent)

| # | Item | Trigger |
| --- | --- | --- |
| T-1 | **Event dictionary**: per-`suggestion_code` context shape documented in this note as codes are added (else 2 years of data needs archaeology) | With every pass that adds a suggestion_code |
| T-2 | `session_key` column (browser-session UUID) for behavioral sequence context | Next telemetry-touching pass; one additive column |
| T-3 | Monthly range partitioning + retention/archive policy | ~10 M rows or ~10 GB |
| T-4 | Parquet snapshot export path for offline training | Start of Tier-2 work |
| T-5 | Aggregate/materialized views for threshold calibration | When first month of real usage data exists |
| T-6 | pgvector adoption for Tier-1 RAG | With `0007-ai-gateway` |
| T-7 | Fleet/cross-deployment aggregation format + consent model | Parked inside 0007 scope; on-prem installs own their data by default |
