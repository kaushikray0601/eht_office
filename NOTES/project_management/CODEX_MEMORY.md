# Codex Memory

Last updated: 2026-06-07

Purpose: compact operating memory for Codex when resuming work after context
compression, pauses, or new chats. Keep this file short and current.

## Current Objective

Make the current SR/MI + cold cable + SLD + BOQ/cable schedule path
production-ready before starting Constant Power tracer or major 3D/model-routing
work.

## Product Vision

eTrace should become a comprehensive EHT engineering platform that exceeds
manufacturer tools by combining heat-loss calculation, tracer selection, cold
cable engineering, interactive SLDs, BOQ/schedules, auditable reports, and
eventually model-based routing/component placement.

## Active Phase

Phase A: production hardening of the current working path.

Immediate next pass after project-management file creation:

1. Start `CC-P1`: installation-method catalogue readiness and UI guidance.
2. Keep the calculation manual aligned with any behavior changes.
3. Consider starting a fresh chat before `CC-P1` for lower context cost.

## Current Repo State

- Working directory: `/home/kr/mydev/eht_office`.
- Current date at creation: 2026-06-07.
- Current untracked files are project-management/orientation files:
  `CLAUDE.md` and `NOTES/project_management/`.
- The previous large cold-cable/SLD code diff is not present in the current
  workspace state.
- Migrations through `0034_rcd_cu_only_cold_cable` applied cleanly in the
  SQLite-mode test run. The default PostgreSQL connection was unavailable for
  plain `showmigrations` during the 2026-06-07 checkpoint.
- Latest full test status: `272 tests OK` on 2026-06-07.
- Latest quick check: `venv/bin/python manage.py check` passed on 2026-06-07.

## Frozen Engineering Decisions

- SR remains the default hot-cable technology.
- MI is automatic only when SR catalogue suitability limits are exceeded.
- Users do not manually choose SR versus MI in project setup.
- Constant Power tracer is a future separate hot-engineering module.
- SR parallel runs and MI multi-sets are represented as independently protected
  branches for MVP clarity.
- SLD alternate tracer overrides are review-only and do not recalculate load,
  BOQ, breaker size, or cable schedule yet.
- SR A/B/C polynomial method remains active; vendor curve-point interpolation is deferred.
- MI T-class is review evidence, not final calculated sheath-temperature approval.
- Cold cable conductor path is Cu-only for now.
- Aluminium cold-cable catalogue path has been removed/deferred.
- Cold cable uses RCD terminology, not GFEP terminology.
- Cold cable sizing uses operating current, not starting current.
- Cold cable voltage-drop basis: PF = 1.0; reactance term ignored.
- 1PH VD formula: `2 x I x R x L`.
- 3PH trunk VD formula: `sqrt(3) x I_phase x R x L`.
- For 3PH JB trunk, `I_phase = per_circuit_operating_current`.
- Cable conductor temperature basis: XLPE = 90 C, PVC = 70 C.
- Copper resistance temperature coefficient: `0.00393 / C`.
- Ampacity derating: `K_temp x K_group`.
- Grouping derating valid range: `0.25` to `1.0`.
- RCD provided: weak 3C MCB earth-loop result becomes review-required, not automatic upsizing.
- RCD not provided: MCB earth-loop check is hard gate; engine can upsize 3C if a larger cable passes.
- Tracer PE-path resistance is deferred and documented as non-conservative.
- Project default cable lengths force `review_required` even when sizing passes.

## Important Implemented Cold-Cable Behavior

- `ColdCableResult.cable_3c_segments` stores per-outgoing 3C sizing evidence.
- Different outgoing 3C lengths from the same JB can select different 3C sizes.
- Branch-level 3C result stores the critical/largest selected 3C summary.
- SLD/cable schedule metadata can read per-node 3C segment results.
- Cable mass is calculated from conductor area, length, core count, and copper density.
- Migration `0034_rcd_cu_only_cold_cable` renames GFEP fields to RCD and deletes Al catalogue rows.

## Known Deferred Gaps

- Installation-method catalogue coverage is not yet production-grade.
- Per-segment 3C reporting/export needs improvement.
- 3PH JB phase-balancing visibility is not built.
- Panel/load summary is not built.
- Procurement-grade cable schedule fields are not built.
- SLD visual issue badges are not built.
- Topology edit impact summary is not built.
- Tracer PE-path impedance is not included in earth-loop calculation.
- Short-circuit withstand/minimum conductor cross-section is deferred.
- MI max heated length, cold-lead completeness, terminal/gland/JB capacity are deferred.
- SR vendor curve-point interpolation is deferred.
- Constant Power tracer is deferred.
- Model-based cable routing and 3D component placement are deferred.

## Collaboration Notes

- Claude acts as architect/auditor/reviewer/critic/collaborator.
- Codex acts as senior developer/collaborator/consultant/adviser and implements.
- Do not code immediately from Claude review notes unless user approves.
- Record review findings intended for Claude in a shareable note.
- Keep `NOTES/CALCULATION_MODULE_USER_MANUAL.md` aligned when implementing or
  changing any calculation behavior. Claude maintains the manual, but Codex
  should flag discrepancies during implementation.

## Testing Commands

Use SQLite test mode unless PostgreSQL is explicitly required:

```bash
venv/bin/python manage.py check
env USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run
node --check static/js/sld_workspace.js
git diff --check
env USE_POSTGRES=false venv/bin/python manage.py test eht -v 2 --noinput
```

## New Chat Guidance

Recommend a new chat when:

- A major pass is complete and tests are green.
- The worktree is checkpointed.
- A new module begins.
- Context replay becomes more expensive than reading this memory file.
- The next task is large enough to deserve a clean brief.

Current recommendation: project-management setup and stabilization are complete.
Consider a fresh chat before `CC-P1` if the user wants maximum speed and low
context cost.
