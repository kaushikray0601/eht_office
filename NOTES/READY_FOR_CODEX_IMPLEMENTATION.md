# MI Integration: Analysis Complete → Ready for Codex Implementation

**Date:** 2026-05-24  
**Status:** Decisions finalized, audit validated, Codex can begin Pass 1

---

## What Was Done

✓ **Read all NOTES files** — Codebase architecture, SR hardening, MI research, induction notes  
✓ **Inspected Django models and calculations** — Validated architecture, identified MVP blockers  
✓ **Ran audit on MI input contract** — Verified what heat_loss provides, what's missing, what's safe to reuse  
✓ **Resolved 3 design questions** — Cold-lead modeling, seed data timing, field simplification  
✓ **Fixed gitignore issue** — db.sqlite3 removed from git tracking  
✓ **Created detailed proposal** — Pass 1 scope, MVP blockers, audit findings, implementation checklist

---

## Key Decisions (User Input + Audit Consensus)

### 1. Cold-Lead Modeling: **FK to Heater**
- Series current varies by heater size/resistance, not family
- Family grouping is too coarse for ampacity checks
- Flagged as provisional — revisit when real Thermon/nVent data loads

### 2. Seed Data Timing: **Populate NOW (Pass 1)**
- Validates schema with real vendor data before selection logic is written
- Aligns with audit finding that catalogue schema must be correct first
- Source: Public Thermon MIQ spec sheet + nVent Raychem MI design guide

### 3. SelectedMIHeater Fields: **Simplified for MVP**
- Removed comprehensive thermal scenario fields
- Kept only: heater spec, power, current, T-class verdict (pass/fail/review)
- Matches MVP requirement: vendor-published sheath temp gate only

---

## Critical Audit Findings: MVP Blockers

The MI Input Contract Verification audit identified **5 must-have fields before any MI selection code is written:**

| # | Blocker | Location | Pass 1 Action |
| --- | --- | --- | --- |
| 1 | `phase` field | HeatTracingInput | Add CharField with default '1PH' |
| 2 | T-class + gas_group + zone_approval | MICableFamily | Add fields (gates T-class check) |
| 3 | cold_lead_resistance_ohms + ampacity | MICableHeater | Add fields (MVP requirement) |
| 4 | SelectedMIHeater result model | New model | Create (distinct from SelectedTracer) |
| 5 | is_validated catalogue flag | MICableFamily | Add BooleanField to gate selection |

**Audit also validated:** Heat-loss, input validation, and rejection diagnostics patterns are MI-ready with no refactoring needed.

---

## Pass 1: Data Foundation (Ready for Codex Implementation)

### Scope
**4 focused tasks, ~1000 LOC, zero risk to SR:**

1. **Expand MI catalogue models** with MVP blocker fields
2. **Create database migration** (00xx_mi_catalogue_expansion.py)
3. **Load seed data** (Thermon MIQ + nVent MI from public specs only)
4. **Write tests** (≥8 model structure + integration tests)

### What Stays Untouched
- ❌ No calculation logic changes
- ❌ No pipeline or tracer_selection.py modifications
- ❌ No SR behaviour affected

### Review Checklist for Codex
- [ ] All 5 MVP blockers present in models
- [ ] Migration applies cleanly: `makemigrations --check --dry-run` pass
- [ ] Applied to dev DB: `migrate` success
- [ ] Seed data from **real vendor documentation only** (not fabricated)
- [ ] Tests pass: `test eht.test_mi_catalogue_structure` (≥8 tests)
- [ ] SR tests pass: all 158 green
- [ ] Documentation explains cold-lead FK rationale + provisional note

---

## What Codex Should Do Now

1. **Implement Pass 1** using the detailed spec in NOTES/Claude-MI-Integration-Proposal.md
2. **Focus on MVP blockers** — ensure all 5 are implemented correctly
3. **Use real vendor data only** — Thermon MIQ and nVent MI from public guides
4. **Run full SR test suite** after migration — verify no regressions

---

## What Claude Will Do During Implementation

- Review diff for schema correctness
- Verify seed data provenance (real vendor docs, not fabricated)
- Check test coverage against audit findings
- Ensure no SR path breakage
- Flag any emerging architecture risks
- Validate cold-lead FK logic against audit recommendation

---

## Timeline

**Pass 1 (Now):** Data model + seed data + tests (~1000 LOC, low risk)  
**Pass 2 (After Pass 1):** MI selection engine (logic only, uses Pass 1 models)  
**Pass 3 (After Pass 2):** Integration into orchestration + reporting  

---

## Files You Should Read Before Asking Codex to Start

- [NOTES/Claude-MI-Integration-Proposal.md](NOTES/Claude-MI-Integration-Proposal.md) — Full technical spec + rationale
- [NOTES/FIRST_PASS_SUMMARY.md](NOTES/FIRST_PASS_SUMMARY.md) — Executive summary
- [NOTES/audit/MI-input-contract-verification-2026-05-24.md](NOTES/audit/MI-input-contract-verification-2026-05-24.md) — Audit findings
- [NOTES/Claude-to-Codex.md](NOTES/Claude-to-Codex.md) — MVP directive + explicit constraints

---

## Summary

**The analysis phase is complete.** The proposal is sound, audit-validated, and ready for implementation. Codex can now build Pass 1 with confidence that:

1. ✓ The data model is correct (audit-verified)
2. ✓ All MVP blockers are identified and scoped
3. ✓ No breaking changes to SR path
4. ✓ Schema is validated with real vendor data before selection logic touches it

**Ready to proceed?** Codex can start on Pass 1 immediately.
