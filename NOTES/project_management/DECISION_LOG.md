# Decision Log

Last updated: 2026-06-13

This log records current product and engineering decisions that should guide
implementation. Historical debate can remain in older notes; this file should
stay concise.

## Active Decisions

| Date | Decision | Rationale | Status |
| --- | --- | --- | --- |
| 2026-05-29 | SR remains the default hot-cable path. | SR is the normal first-choice technology for current workflow. | Active |
| 2026-05-29 | MI fallback is automatic only when SR catalogue suitability limits are exceeded. | Keeps project setup simple and avoids manual SR/MI technology choice. | Active |
| 2026-05-29 | Constant Power tracer is a separate future module. | Avoids mixing a distinct technology into the SR/MI cold-cable phase. | Active |
| 2026-05-29 | MI multi-sets are represented as independently protected branches. | MI heater sets remain individually protected for fault isolation and vendor-practice alignment. | Active |
| 2026-05-29 | SR parallel runs were temporarily represented as independently protected branches. | Superseded by the 2026-06-08 cold-cable rebuild decision to use shared MCB groups for SR parallel runs. | Superseded |
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
| 2026-06-07 | Project setup exposes only active Method E plus disabled coming-soon Method D2 for cold-cable installation method. | Keeps the user-facing setup simple while acknowledging the planned direct-buried basis; B2/C/D1 stay hidden until catalogue work is ready. | Active |
| 2026-06-07 | Cold-cable installation methods without validated catalogue rows produce explicit unsizeable guidance if encountered in stored/admin data. | Prevents silent use of incomplete catalogue data. | Active |
| 2026-06-07 | Branch-level 3C size is reported as the critical outgoing 3C segment; all outgoing 3C segments are exported separately. | Keeps branch summaries simple while preserving per-segment evidence for unequal route lengths. | Active |
| 2026-06-07 | 3PH JB outgoing phase visibility is inferred as L1/L2/L3 round-robin by outgoing circuit index and stored in per-segment cold-cable JSON. | Provides review visibility without adding a migration or pretending automatic phase optimization exists. | Active |
| 2026-06-07 | Topology edits are blocked in filtered/focused SLD views; cable length and tracer overrides remain allowed. | Prevents applying full-project topology mutations from a partial graph while preserving line-local engineering overrides. | Active |
| 2026-06-07 | Long SLD topology operation chains compact fail-closed rather than replaying indefinitely. | Keeps active edits usable while the generated baseline is unchanged; if the generated baseline later changes, compacted edits require review instead of unsafe replay. | Active |
| 2026-06-08 | Cold-cable rebuild uses single-phase EHT distribution: SR parallel runs share one 2-pole MCB per run group, while MI multi-sets keep individual MCBs. | Aligns SLD/current topology with common EHT practice and avoids the previous 1PH/3PH hybrid mismatch. | Active |
| 2026-06-08 | Rename cold-cable concepts to FeederCable, BranchCable, DistributionJB, and BranchJB. | Removes misleading 4C/3PH terminology while preserving the current SLD topology shape. | Active |
| 2026-06-08 | EHT DB fault rating is a mandatory project setting defaulting to 15 kA, with preset choices 10/15/25/40/50 kA plus an Other value >= 1 kA. It means the three-phase prospective short-circuit current at the EHT DB busbar. | Source impedance must be calculated from project short-circuit data rather than assumed zero. | Active |
| 2026-06-08 | Single-phase cold-cable VD and fault checks evaluate the complete terminal path: FeederCable plus BranchCable. | Voltage drop must use `2 x I x R x L`; L-PE earth-loop fault current must include source, phase, and PE path resistance. | Active |
| 2026-06-08 | BranchCable ampacity must be at least the upstream MCB rating in the MVP. | Avoids tap-conductor exceptions and keeps protection coordination conservative and reviewable. | Active |
| 2026-06-08 | Each ColdCableResult stores complete path evidence, but BOQ/cable schedule totals must deduplicate shared FeederCable quantities. | Keeps per-branch evidence self-contained while preventing material double-counting for shared feeders. | Active |
| 2026-06-08 | Existing ColdCableResult rows must be deleted during the rebuild migration. | Old results were produced under the superseded 3PH/4C/current-basis model and should not silently survive. | Active |
| 2026-06-11 | Mandatory Database Safety Protocol: `flush`, `DELETE`/`TRUNCATE`/`DROP`, and QuerySet deletes against `eht_local` or any catalogue/reference table require explicit written KR approval; the active database name must be verified and stated before every database-modifying command. | The local development database was accidentally flushed during CC-P5 verification; catalogue restoration cost a full working session. | Active |
| 2026-06-11 | `eht/tmp/elecEHT_Vendor.csv` must not be imported via `import_data_from_file` until KR rules on its 178 unverified rows. | The CSV has diverged from the validated vendor table in both directions and an import would corrupt the restored catalogue. | Active |
| 2026-06-12 | Keep SQLite as the quick/default test database; use PostgreSQL `eht_local_test` as the backup/safety full-suite path. | KR wants fast isolated tests while preserving PostgreSQL project-data backup and production-like verification. | Active |
| 2026-06-13 | Procurement-grade cable schedule fields are optional annotations on `CableScheduleOverride`, maintained through admin for MVP and exported with generated schedule rows. | Adds route/reference, installation basis, drum/lot, revision, review status, and checked-by/date without introducing a full procurement workflow before MVP convergence. | Active |

## Decision Candidates

| Candidate | Needed Before | Notes |
| --- | --- | --- |
| Whether phase slots should become user-editable. | After single-phase cold-cable rebuild | Current `CC-P3` phase visibility will be retired or reinterpreted when 3PH/4C terminology is removed from active cold-cable output. |
| Whether combined-circuit length defaults require explicit user confirmation before apply. | Before SLD combined-circuit cable re-sizing | Current direction: default to highest selected feeder length and warn/review; decide whether to block apply until user accepts. |
| Whether to checkpoint current working tree before `CC-P4`. | End of `CC-P3` | Strongly recommended now that PM setup, CC-P1, CC-P2, SLD-R1, and CC-P3 tests are green. |
| When to move to a fresh chat. | After `PM-00`/`CC-P0` | Fresh chat plus `CODEX_MEMORY.md` should improve speed and quality. |
