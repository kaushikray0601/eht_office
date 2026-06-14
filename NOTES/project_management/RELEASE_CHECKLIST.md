# Release Checklist

Last updated: 2026-06-14

Purpose: checklist for declaring the current SR/MI + cold cable + SLD path
production-ready for serious engineering review.

## Code Health

- [x] `venv/bin/python manage.py check` passes.
- [x] `env USE_POSTGRES=false venv/bin/python manage.py makemigrations --check --dry-run` passes.
- [x] `node --check static/js/sld_workspace.js` passes.
- [x] `git diff --check` passes.
- [x] Full SQLite `eht` test suite passes.
- [x] Full PostgreSQL-backed `eht` test suite passes against `eht_local_test`.
- [x] Current migrations are applied to the development database.
- [x] No accidental unrelated file changes remain in the release diff.
- [ ] Production deployment settings satisfy Django deploy checks: HSTS/HTTPS
      policy, secure session/CSRF cookies, and non-development `SECRET_KEY`.

## Hot Engineering

- [ ] SR heat-loss and selection tests pass.
- [ ] SR rejection diagnostics are visible in result/export.
- [ ] MI fallback tests pass.
- [ ] MI multi-set tests pass.
- [ ] MI limitations are visible in report/manual.
- [ ] Tracer override review-only status is visible and not misleading.

## Cold Cable Engineering

- [ ] Ampacity sizing works for available catalogue basis.
- [ ] Voltage drop sizing works for direct single-phase FeederCable branches.
- [ ] Voltage drop optimization works for shared FeederCable + BranchCable paths.
- [x] Per-outgoing 3C sizing works for unequal route lengths.
- [x] Three-phase EHT DB fault rating is captured in project setup and source impedance is calculated from it.
- [ ] L-PE fault loop uses project source impedance plus full FeederCable/BranchCable phase and PE path.
- [ ] RCD-provided behavior is review-required when MCB earth-loop is weak.
- [ ] No-RCD behavior upsizes or fails as a hard gate.
- [ ] Cable mass/tonnage is reported.
- [ ] Project-default length basis forces review-required status.
- [x] Installation-method catalogue readiness is clear; setup allows Method E only and shows D2 as coming soon.
- [x] Per-segment 3C results are exported/reported.
- [x] Phase-balancing visibility is available or explicitly deferred.
- [x] Panel/load summary is available as branch-based review evidence; upstream
      spare-capacity coordination remains deferred.
- [x] Panel/load summary deduplicates shared MCB breaker capacity while summing
      downstream branch load current.

## Cable Schedule / BOQ

- [x] Cable schedule separates generated and manual quantities.
- [x] Manual length/size overrides are visible.
- [x] Cold-cable calculated size/status/VD/fault evidence is visible.
- [x] Shared FeederCable quantities are deduplicated in cable schedule and BOQ totals.
- [x] Total cable length and conductor mass are summarized.
- [x] Procurement fields are present or explicitly deferred.
- [x] Excel export is suitable for engineering review.

## SLD

- [x] Generated SLD renders correctly for representative projects.
- [x] Playwright SLD browser smoke passes in local dev environment, including preview/apply for the four main topology workflows.
- [x] Frontend SLD render paths use guarded render lifecycle.
- [ ] Saved layout persists and resets correctly.
- [x] Controlled topology edits remain auditable.
- [x] Filtered/focused SLD views block topology edits while preserving cable/tracer overrides.
- [x] Topology operation records and saved graph invariants are validated before active edits are persisted.
- [ ] PDF export reflects active topology.
- [ ] Cold-cable labels fit and do not overlap key symbols.
- [x] Review-required and missing-data states are visible through SLD visual
      review badges for missing length, cold-cable review/unsizeable, manual
      override, and topology-review states.
- [ ] Large-project browsing/search remains usable.

## Documentation / Verification

- [x] Calculation manual aligns with implemented formulas.
- [ ] User manual (`NOTES/CALCULATION_MODULE_USER_MANUAL.md`) is current and committed.
- [x] Engineering Hub design guide formulas match implemented cold cable basis.
- [x] Verification report aligns with source-of-truth code.
- [x] Worked SR example exists.
- [x] Worked MI example exists.
- [x] Worked direct single-phase FeederCable example exists.
- [x] Worked shared FeederCable / BranchCable optimization example exists.
- [ ] Known limitations are visible and plain-language.

## Demo / Acceptance

- [ ] Demo project can be imported/calculated without manual database fixes.
- [ ] Result tab, BOQ, cable schedule, SLD, PDF, and export all load.
- [ ] Manual cable length edit triggers expected cold-cable result update.
- [ ] Manual topology edit shows expected schedule/SLD impact.
- [ ] Verification report renders correctly for a representative SR line and an MI line.
- [ ] Verification report terminal voltage cross-check result matches a manual calculation.
- [ ] User can identify which items are selected, review-required, or unsizeable.
