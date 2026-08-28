# Development Scorecard

Owner: Claude (architect/auditor) — KR-assigned responsibility, 2026-07-18
Purpose: periodic self-assessment against how the best software companies build — to introspect, stay on target, catch drift early, and measure our own improvement. Scores are honest, not motivational.

## Update policy

Claude updates this file:

1. **At every phase/arc completion** (e.g., accessory arc closed, Phase H cable assignment started/completed, first external pilot).
2. **After ~10 coding passes** since the last update, whichever comes first.
3. **Immediately on any score-moving event** (CI added, TypeScript adopted, a production incident, a major gate closed such as the georeference proof).
4. Minimum cadence: monthly, even if nothing moved — a "no change" entry is itself information.

Each update appends a row to the History Log (never rewrites old entries) and adjusts the scorecard table with a trend arrow. Scores: 1–10, where 10 = best-in-class production grade at a top software company.

## Scorecard — as of 2026-07-18 (baseline)

| Category | Score | Trend | Justification | Path to +1 |
| --- | --- | --- | --- | --- |
| Architecture & boundary discipline | 9 | — | Enforced by tests (import guards both directions), written contracts, extraction-ready seams, consumer-neutral patterns proven by second consumer | Close the georeference/large-model proof gates; first real service-extraction dry run |
| Backend code quality (Python) | 8 | — | Consistent idioms, named constants, server-side canonicalization, deterministic outputs; helper duplication happened once (caught, consolidated) | Type hints on public seams; split the largest view modules |
| Frontend code quality (JS) | 7 | ▲ | 2026-07-28: pure command-state layer (`computeRacewayCommandStates`), JSDoc typedefs, DOM-free view-model helpers, fail-loud version/shape checks — the Apply-Edge-Match failure *class* is now structurally addressed. Still one monolith file, no bundler | Complete the geometry/DOM module split; separate JS module file; `node:test` unit runner for pure functions |
| Testing | 8 | ▲ | 2026-07-28: 512 backend tests incl. **cross-boundary contract pins** (reducer fields + Phase-H schedule contract) and six browser workflow tests; still no CI, still PG/SQLite duality | CI on push (the multiplier); broader graph/fitting pins; JS unit tests |
| Documentation & records | 9.5 | — | Decision records, design-notes-before-code (house style now), verification logs per pass, event dictionary, living strategy RFC + this scorecard | Retire/mark stale legacy docs (idfviewer-era, NOTES June trackers) |
| Process & verification hygiene | 8.5 | ▲ | 2026-08-28: the Phase G closure sequence itself — audit-before-cleanup, register as single source with dispositions, and **authority boundaries held under temptation** (Codex refused to silently decide A1/A2/A3 mid-housekeeping) | CI makes "green" a fact not a claim; formal batteries only on landed passes (no racing live editors) |
| Development speed (per headcount) | 10 | — | Reset → full raceway MVP + graph + BOQ + warnings + clash + telemetry + accessory foundation in ~10 days, sustained by the review loop | Maintain while headcount of consumers grows (lighting will test this) |
| Security | 7.5 | — | Access checks universal, rate limiting, CSRF, traversal fixes, admin hardening; pending: dependency hygiene pass, deployment hardening completion, secrets story | Complete eht SEC-P1b leftovers; `pip-audit`/`npm audit` in CI |
| Data engineering & schema | 8.5 | — | UUID durable identity, versioned metadata schemas, additive-only migrations, evidence JSON, telemetry corpus accumulating | Vendor-data sync automation (task queued); partitioning/retention when triggers hit |
| DevOps / CI / deployment | 5 | — | **Corrected 2026-07-18:** remote push discipline exists (GitHub, AI-generated commit notes), DB backup topology exists (local WSL Docker + cloud Ubuntu Docker holding the irreplaceable vendor catalogue — a deliberate, reasonable scope decision since test data is regenerable). Missing: automated test pipeline, backup-sync automation, staging environment, containerized deploy | GitHub Actions CI on push (~2–3 min battery); vendor-sync management command; staging VPS when first pilot approaches |
| **Weighted overall** | **~7.9** | — | Production-grade domain logic, architecture, and records; the gap to "production company" is concentrated in JS engineering and CI/CD | |

## Drift watch (updated with each entry)

- 2026-07-18: **Accessory arc is at its timebox boundary.** Reducer proxy v0 + tee = MVP-sufficient; crosses/covers/vendor meshes are post-MVP. The strategic frontier is Phase H cable assignment + durable EHT persistence (the integrated-chain demo). Flag raised in claude-notes §41-era review; watch whether the next 5 passes move toward Phase H.
- 2026-07-19: On plan, not drifting — `579af3d` delivered bend/riser proxies + cutback + tee/cross placeholders and closed N-20 (§43). **Remaining arc item: reducer body only.** Companion register created: `open-items-register.md`.

## History Log (append-only)

| Date | Event | Score changes | Notes |
| --- | --- | --- | --- |
| 2026-07-18 | Baseline created at KR's request | — | Corrected DevOps from initial 4 → 5 after verifying `git remote -v` (remote push + backup topology exist; Claude's earlier "no remote" flag was wrong — lesson: verify before declaring). Next scheduled update: accessory-arc close or +10 passes |
| 2026-07-28 | B-list + hybrid doctrine + Tee/Cross v0 + first C10 slice (5 passes, `4ba609d`→`888ef9b`) | JS 6→7, Testing 7.5→8, **overall ≈ 8.0** | The Apply-Edge-Match incident's structural fixes landed (command-state seam, contract pins, fail-loud checks, visible disabled reasons). Accessory arc effectively closed pending KR acceptance. DevOps unchanged at 5 — **CI (A3) is now the lone item holding two categories down.** Drift watch: on plan; next update at Phase H start |
| 2026-08-28 | Phase G closure Passes 1–3 (audit, register/orientation, technical closure: C1 sync command, C4 `session_key`, C5 assertion) | Process 8→8.5, **overall ≈ 8.05** | Closure discipline exemplary; B3/C1/C3/C4/C5/C8/A-7/M-3/D1 all dispositioned closed; register is single source of truth. Remaining before Phase G declared closed: pure-JS extraction slice, Pass 4 clash note (H6 edge-penalty bridge), Pass 5 doc housekeeping, Pass 6 acceptance — **and KR's A1/A2/A3 words (A3 still holds DevOps at 5)**. Next update: Phase G closure declaration or H-A1 start |
