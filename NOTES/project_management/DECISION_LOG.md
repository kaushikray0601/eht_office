# Decision Log

Last updated: 2026-06-07

This log records current product and engineering decisions that should guide
implementation. Historical debate can remain in older notes; this file should
stay concise.

## Active Decisions

| Date | Decision | Rationale | Status |
| --- | --- | --- | --- |
| 2026-05-29 | SR remains the default hot-cable path. | SR is the normal first-choice technology for current workflow. | Active |
| 2026-05-29 | MI fallback is automatic only when SR catalogue suitability limits are exceeded. | Keeps project setup simple and avoids manual SR/MI technology choice. | Active |
| 2026-05-29 | Constant Power tracer is a separate future module. | Avoids mixing a distinct technology into the SR/MI cold-cable phase. | Active |
| 2026-05-29 | SR parallel runs and MI multi-sets are represented as independently protected branches. | MVP clarity for SLD, cable schedule, and breaker protection. | Active |
| 2026-05-29 | SLD tracer overrides are review-only. | Current override does not recalculate load, BOQ, breaker, or cable schedule. | Active |
| 2026-05-29 | SR Allowed Spiral Factor default is 1.0; selector evaluates straight-run duty ratio as heat-delivery evidence, not as a command to install fractional cable length. | Reflects shift to straight-run default; duty ratio below 1.0 means margin, not shortened cable. | Active |
| 2026-05-29 | MI `is_validated` is a hard catalogue gate; unvalidated MI families are rejected even if rows exist. | Prevents selection from unreviewed catalogue data. | Active |
| 2026-05-29 | Cold cable consumes stabilized SR/MI output and does not reselect tracer technology. | Maintains module boundary and avoids hidden recalculation. | Active |
| 2026-05-29 | Cold cable sizes on continuous operating current, not starting current. | Starting current is transient and should not drive cable ampacity sizing. | Active |
| 2026-05-29 | Cold cable PF is 1.0 and reactance is ignored for current pass. | EHT load is resistive; simplifies VD basis for MVP. | Active |
| 2026-05-29 | RCD-provided 3C earth-loop weakness is review-required, not automatic upsizing. | RCD is primary earth-fault protection; MCB check is secondary. | Active |
| 2026-05-29 | Without RCD, MCB earth-loop check is a hard gate. | MCB is sole earth-fault protection in that configuration. | Active |
| 2026-05-29 | Tracer PE-path resistance is deferred and flagged as non-conservative. | SR/MI PE-path data is not yet available in catalogue models. | Active |
| 2026-05-29 | Project default cable lengths force review-required status. | Procurement needs measured/confirmed route lengths. | Active |
| 2026-06-01 | Aluminium cold-cable path is deferred; Cu-only active path. | EHT branch circuits are usually small Cu cables; Al adds complexity with limited value. | Active |
| 2026-06-01 | Use RCD terminology instead of GFEP in active UI/docs/code. | RCD is better aligned with IEC/common international terminology. | Active |
| 2026-06-07 | Create project-management files and Codex memory file. | Reduces context loss, token cost, and planning ambiguity. | Active |

## Decision Candidates

| Candidate | Needed Before | Notes |
| --- | --- | --- |
| How to represent phase-slot ownership for 3PH JB outgoing branches. | `CC-P3` | Must support visibility first, optimization later. |
| Whether installation methods without catalogue rows should be disabled or allowed with clear unsizeable outcome. | `CC-P1` | Prefer explicit guidance without overblocking admin/catalogue workflows. |
| Whether to checkpoint current working tree before `CC-P1`. | End of `CC-P0` | Strongly recommended due large dirty diff. |
| When to move to a fresh chat. | After `PM-00`/`CC-P0` | Fresh chat plus `CODEX_MEMORY.md` should improve speed and quality. |
