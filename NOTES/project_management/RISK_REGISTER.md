# Risk Register

Last updated: 2026-06-07

| ID | Risk | Severity | Probability | Mitigation | Status |
| --- | --- | --- | --- | --- | --- |
| R-001 | Large uncommitted working set makes future changes harder to review. | High | High | Run `CC-P0`, then checkpoint/commit when tests are green. | Open |
| R-002 | Cold-cable installation methods are exposed before catalogue coverage is complete. | Medium | High | Project setup now exposes only active Method E plus disabled coming-soon D2; explicit unsizeable guidance remains for stored/admin data. Catalogue population remains future work. | Mitigated |
| R-003 | Tracer PE-path resistance is excluded from 3C earth-loop check, overestimating fault current. | High | High | Keep prominent non-conservative warning; add future catalogue data before enforcing. | Open |
| R-004 | SLD topology edits are powerful and may create confusing review states for users. | Medium | Medium | Browser-side topology controls were hardened in `SLD-R1`; stale operation chains are audited/dropped when they cannot replay; long chains compact fail-closed; topology fingerprints ignore volatile cold-cable metadata; filtered views block topology mutation; rendered-cell preview/apply coverage protects the four main workflows. Add visual issue badges and impact summary next. | Open |
| R-005 | Cable schedule is still calculation-oriented, not procurement-grade. | Medium | High | Add procurement fields and export polish in `SCH-P1`. | Open |
| R-006 | Verification report may drift from calculation source of truth. | High | Medium | Add worked examples and formula alignment checks in `QA-P1`. | Open |
| R-007 | Context compression or chat length may lose engineering nuance. | Medium | High | Maintain `CODEX_MEMORY.md`; start fresh chats at clean checkpoints. | Mitigated |
| R-008 | Catalogue data quality can silently affect engineering decisions. | High | Medium | Keep readiness checks, validation, and explicit review notes. | Open |
| R-009 | Phase imbalance is not visible for 3PH JB outgoing branches. | Medium | Medium | `CC-P3` now shows inferred L1/L2/L3 currents and imbalance in result UI/export. Automatic rebalancing remains future scope. | Mitigated |
| R-010 | Future Constant Power and 3D work could distract from closing current production path. | Medium | Medium | Keep them deferred until Phase A release checklist is substantially complete. | Open |
| R-011 | MI auto-fallback cannot fire in production because `is_validated=False` for all catalogue families. Users see MI rejection records, not MI selection, until at least one family is validated. | High | High | R7 vendor comparison gate - KR to close before any MI-sensitive project is calculated in production. | Open |
| R-012 | Normal Django `manage.py test` command can fail during existing PostgreSQL test DB setup even when direct connections work. | Medium | Medium | Runner alias handling and cached-wrapper cleanup were improved; programmatic existing-PostgreSQL runner passes focused SLD tests. Keep standard command failure as a follow-up before relying on it as CI gate. | Open |
