# Open Items Register — for KR to take up at his own pace

Owner: Claude (consolidates every open point from the review history; updated whenever items open/close)
Created: 2026-07-19 at KR's request. Companion to `development-scorecard.md` (scores/trends) and `claude-notes-2026-07-08.md` (full findings history, §-references below).

Legend: 🔴 decision needed · 🟡 action/habit · 🟢 backlog (Codex executes when scheduled) · ⚪ gate (must close before a named milestone)

## A. KR decisions (each is minutes, not hours)

| # | Item | Since | Ref | Note |
| --- | --- | --- | --- | --- |
| A1 🔴 | **Catalogue-seed confirmation** — bless the seeded generic catalogue (ladder 300/450/600, perforated 150/300/450, HDG, IEC 61537) or amend | §14 (2026-07-09) | claude-notes §14, §21 | Oldest open decision; seed data now appears in exportable CSVs — one word closes it |
| A2 🔴 | **`.code-workspace` file** — untrack from `records/audit/` + gitignore, or keep deliberately | §13 (2026-07-09) | claude-notes §13, §17 | One `git rm --cached` + one gitignore line |
| A3 🔴 | **CI go-ahead** — approve the L1 GitHub Actions pipeline (one small Codex pass, ~2–3 min battery per push) | 2026-07-18 | CI/CD course; scorecard | Highest score-per-effort move on the board (DevOps 5→6, Testing 7.5→8) |

## B. KR actions & habits

| # | Item | Since | Ref | Note |
| --- | --- | --- | --- | --- |
| B1 🟡 | **Weekly 10-minute decision sweep** over section A — answer or defer-with-date | 2026-07-18 | assessment (f) | The habit that stops small items aging into reminders |
| B2 🟡 | **eht manual release sign-off** — demo walkthrough, cold-cable label overlap, large-project browsing feel, terminal-voltage cross-check | 2026-06-14 | eht tracker RELEASE-P1 | The eht MVP has been code-complete and waiting since June |
| B3 🟡 | Approve a **root `CLAUDE.md` stub refresh** so fresh agent sessions orient to the raceway era, not June's Phase A | §28 | claude-notes F-02, §28 | 5-line doc change; Codex or Claude can draft |

## C. Codex backlog (consolidated; schedule when convenient — none blocking)

| # | Item | Ref | Size |
| --- | --- | --- | --- |
| C1 🟢 | **Vendor-catalogue sync command** (dev → two backup DBs; dry-run default; incl. `RacewayFamily`/`Size`) — KR-assigned | §42 | small pass |
| C2 🟢 | L1 **CI workflow file** (after A3) | CI course | small pass |
| C3 🟢 | **Reducer body proxy** (handedness + taper, wider-port frame, A-2 cutback already solved) — last accessory-arc MVP item | §40–§43 | 1–2 passes |
| C4 🟢 | T-2 `session_key` column on telemetry | telemetry note T-2 | one column |
| C5 🟢 | §26 blocked-telemetry-endpoint browser assertion | §26 | tiny |
| C6 🟢 | M-5 copy-run-with-offset; M-6 remainder (EL grid while drawing) | RFC M-table | small each |
| C7 🟢 | Segment-interior canvas picking; explicit work-plane mode messaging | tracker deferred list | small each |
| C8 🟢 | A-3 BOQ assumptions line ("straight lengths gross; development lengths not deducted") | §40 | one line |
| C9 🟢 | Radius/handedness persistence via the segment-intent idiom (when choice UI lands) | §43 | with reducer UI |
| C10 🟢 | **JS hardening pass** (upgraded from "plan" after the Apply Edge Match incident): Codex's 5 recommendations (pure command-state layer, JSDoc/@ts-check, geometry/DOM split, state invariants, workflow browser tests) **+ Claude B-1..B-4**. 2026-07-21 status: reducer B-1 contract pins, stronger B-2 fail-loud checks, Edge Match B-3 visible disabled reason, B-4 context diagnostics/tests, and the first `computeRacewayCommandStates(snapshot)` seam are landed; remaining work is JSDoc/@ts-check, geometry/DOM split, broader graph/schedule pins, CI/B-5, and A-7 persistence decision | js-audit + claude-notes §44 | 2–3 passes |
| C11 🟢 | Mark/retire stale legacy docs (idfviewer-era, NOTES June trackers) | scorecard | housekeeping |

## D. Gates (close before the named milestone)

| # | Gate | Blocks | Ref |
| --- | --- | --- | --- |
| D1 ⚪ | **Accessory-arc timebox** — reducer body + tee close the arc; then **pivot to Phase H cable assignment + durable EHT persistence** (the integrated-chain demo) | The strategic milestone | scorecard drift-watch |
| D2 ⚪ | **Georeferenced/plant-global IFC precision proof** | Any demo on a real plant-global file | reset tracker carry-forward |
| D3 ⚪ | **Larger real EPC model test** (beyond 15 MB IFC) | Same; also the biggest technical unknown | reset tracker carry-forward |
| D4 ⚪ | eht dependency-hygiene + deployment-hardening leftovers (SEC-P1b) | Production deployment | eht tracker |
| D5 ⚪ | **Vendor-mesh licensing check** (redistribution rights per vendor) | The vendor-library stage | assessment (c) |
| D6 ⚪ | Decision record 0007 `ai_gateway` | First Tier-1 AI feature | strategy RFC |

## Recently closed (kept one cycle for visibility)

- N-20 frame-coupled merge rule — closed `579af3d` (§43). A-2 cutback — delivered for bends/risers (§43). N-18 PG fixture — closed (§38). N-19 browser flake — closed (§39). T-1 event dictionary — being followed at source since §38.
