# Open Items Register

Owner: Claude/Fable consolidates review history; Codex updates during closure
passes when KR approves the work. Companion to `development-scorecard.md`
and `claude-notes-2026-07-08.md`.

Created: 2026-07-19.
Last updated: 2026-08-28, Closure Pass 6.

This is the single source of truth for open/closed/deferred items. The Phase G
closure audit is supporting analysis, not a competing register.

Phase G implementation and closure sequence are complete as of Closure Pass 6.
A1/A2/A3 remain explicit KR decisions, not Codex-closed items.

Disposition legend:

- `needs-decision`: KR must decide.
- `close-now`: close during the Phase G closure sequence.
- `defer-to-H`: deliberately deferred to Phase H.
- `defer-later`: post-Phase-H or post-MVP backlog.
- `closed`: done or accepted for MVP.
- `gate`: must close before the named milestone.

## A. KR Decisions

| # | Item | Since | Ref | Disposition | Note |
| --- | --- | --- | --- | --- | --- |
| A1 | Catalogue-seed confirmation: bless the seeded generic catalogue, or amend it | §14, 2026-07-09 | claude-notes §14, §21, §49 | needs-decision | Codex/Claude recommendation: accept as generic IEC/vendor-free MVP seed, explicitly not vendor-validated. One KR word closes it. |
| A2 | `.code-workspace` file in `plant3d/records/audit/` | §13, 2026-07-09 | claude-notes §13, §17, §49 | needs-decision | File exists at `plant3d/records/audit/eht_office.code-workspace`. Recommendation: untrack/remove from records and add ignore rule unless KR wants it kept deliberately. |
| A3 | CI go-ahead for L1 GitHub Actions pipeline | 2026-07-18 | CI course, scorecard, claude-notes §49 | needs-decision | Claude §49 moves CI inside Technical Closure. Codex agrees; needs KR approval before workflow work. |

## B. KR Actions And Habits

| # | Item | Since | Ref | Disposition | Note |
| --- | --- | --- | --- | --- | --- |
| B1 | Weekly 10-minute decision sweep over section A | 2026-07-18 | assessment (f) | defer-later | Useful project habit; not a Phase H technical blocker. |
| B2 | EHT manual release sign-off | 2026-06-14 | eht tracker RELEASE-P1, claude-notes §49 | defer-later | Important but separate from Raceway Phase H. Needs KR walkthrough/sign-off. |
| B3 | Root `CLAUDE.md` stub refresh | §28 | claude-notes F-02, §28, §49 | closed | Refreshed on 2026-08-02 along with `NOTES/project_management/CLAUDE.md`. |

## C. Codex Technical / Housekeeping Backlog

| # | Item | Ref | Disposition | Note |
| --- | --- | --- | --- | --- |
| C1 | Vendor-catalogue sync command, dry-run default, source read-only, explicit targets, includes `RacewayFamily`/`RacewaySize` | claude-notes §42, §49 | closed | Closed in Closure Pass 3 with `sync_curated_catalogue_data`; command is dry-run by default, requires explicit target aliases, performs no deletes, reports missing/stale schema as readiness warnings in dry-run, fails clearly before `--execute`, and is pinned by dispatch/scope tests. This does not bless catalogue content. |
| C2 | L1 CI workflow file | CI course, claude-notes §49 | close-now after A3 | Implement only after KR approves A3. |
| C3 | Accessory v0 acceptance sweep | §40-§47 | closed | Accessory arc is accepted for MVP; limitations table added to accessory note on 2026-08-02. |
| C4 | Telemetry `session_key` or equivalent browser-session grouping | telemetry note T-2, §49 | closed | Additive nullable `SuggestionEvent.session_key`, browser-session UUID producer, and API validation landed in Closure Pass 3. |
| C5 | Browser assertion for blocked telemetry endpoint behavior | §26, §49 | closed | Focused browser smoke now pins that blocked telemetry returns a console warning and authoring continues. |
| C6 | M-5 copy-run-with-offset; M-6 EL grid while drawing | RFC M-table, §49 | defer-later | Useful UX, not a Phase H-A1 blocker. |
| C7 | Work-plane/free-route messaging and broader segment-pick reuse | tracker deferred list, §49 | defer-later | Partly landed for Make Tee. Record UX gap; not H-A1 blocker. |
| C8 | BOQ gross-length/development-length assumption line | §40, §47 | closed | Closed in C10.2 and pinned in tests. |
| C9 | Radius/handedness/accessory-intent persistence via segment-intent idiom | §43, §47, §49 | defer-later | Waits for accessory acceptance palette and catalogue workflow. |
| C10 | JS hardening: pure seams, geometry/DOM split, separate module files, JS tests | js-audit, §44, §46, §49, §51 | defer-to-H | Low-risk pure helper extraction closed in Technical Closure Pass 3B and Node unit coverage added in Closure Pass 5. Interaction/panel/state restructuring remains the H-A2 precondition. |
| C11 | Mark/retire stale legacy docs | scorecard, §49-§51 | closed | Closed in Closure Pass 5 with `markdown-housekeeping-inventory-2026-08-28.md` and lifecycle headers on active-sounding historical files. No files were deleted; destructive cleanup stays KR-approved only. |

## D. Gates

| # | Gate | Blocks | Ref | Disposition | Note |
| --- | --- | --- | --- | --- | --- |
| D1 | Accessory-arc timebox | Phase G closure | claude-notes §45-§49 | closed | Reducer, bend/riser, Tee/Cross v0 accepted for MVP. Vendor-grade/accessory-intent work remains deferred. |
| D2 | Georeferenced/plant-global IFC precision proof | Real plant-global demo | reset tracker carry-forward | gate | Not required for H-A1 on the current sample, but required before serious real-plant demo claims. |
| D3 | Larger real EPC model test beyond 15 MB IFC | Real plant demo / scale confidence | reset tracker carry-forward | gate | Biggest runtime/scalability unknown; not a server-side H-A1 blocker. |
| D4 | EHT dependency-hygiene + deployment-hardening leftovers (SEC-P1b) | Production deployment | eht tracker | defer-later | Production gate, separate from Raceway Phase H-A1. |
| D5 | Vendor-mesh licensing check | Vendor-library stage | assessment (c) | defer-later | Required before redistributing vendor meshes/assets. |
| D6 | Decision record `0007-ai_gateway` | First Tier-1 AI feature | strategy RFC | gate | Must precede first real AI agent/AI suggestion feature beyond Tier-0 telemetry. |

## E. Phase H Preconditions

| # | Item | Blocks | Ref | Disposition | Note |
| --- | --- | --- | --- | --- | --- |
| H1 | Route edge identity must be durable node-pair key, not ordinal `E###` | H-A1 | claude-notes §48 | gate | Route payloads must never expose ordinal graph keys as stored consumer truth. |
| H2 | Route weight function must be injectable | H-A1 | claude-notes §48 | gate | Start length-only, but leave seam for bends/fill/clash/learned weights. |
| H3 | Deterministic path tie-breaking | H-A1 | claude-notes §48 | gate | Stable ordering by node/edge keys and tests. |
| H4 | Route preview payload contract pin | H-A1 | claude-notes §48 | gate | Pin path node/edge pair keys, edge lengths, total, riser/horizontal flags, basis/assumptions. |
| H5 | Consumer-neutral cable reference design note | H-A2 | claude-notes §48, §49 | gate | Needed before assignment persistence/UI: `owner_module` + opaque `cable_ref`, no EHT imports. |
| H6 | Clash v0 edge-penalty bridge | H-A1/H-A2 route quality | claude-notes §49-§50 | closed | Closed in Closure Pass 4 with `raceway.clash_edge_penalties.v0`; existing AABB clash/clearance warnings are aggregated by durable adjacent node UUID edge key as soft route-cost hints, with no new mesh physics. |

## Recently Closed

- B-1..B-4: reducer/server-client hardening closed and verified in §46.
- C8: schedule assumption `raceway.schedule.gross_straight_length_basis`
  closed in C10.2.
- A-7: reducer handedness decided as drafting controls; only resulting face
  offsets persist until real accessory intent exists.
- M-3: Make Tee and Make Cross authoring shipped and KR-accepted.
- B3: stale root/project Claude orientation refreshed on 2026-08-02.
- C1/C4/C5: vendor-catalogue sync command, telemetry browser session key,
  and blocked-telemetry browser assertion closed in Closure Pass 3.
- C10 low-risk slice: pure Raceway projection/command helper module extracted
  in Closure Pass 3B; larger interaction refactor deferred to H-A2.
- H6: Clash v0 durable edge-penalty bridge and clash/pathfinding staging note
  closed in Closure Pass 4.
- C11: markdown housekeeping inventory and historical lifecycle headers closed
  in Closure Pass 5; deletion candidates remain approval-only.
- C10 test foundation: `raceway_projection_core.test.js` added in Closure
  Pass 5, closing the cheap JS unit-test gap Claude §51 identified.
- Phase G closure sequence: final acceptance brief added in Closure Pass 6;
  H-A1 may start server-side with A1/A2/A3 carried explicitly.
