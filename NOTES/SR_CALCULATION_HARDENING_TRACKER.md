# SR Calculation Hardening Tracker

Date started: 2026-05-12

Purpose: stabilize the current self-regulating cable calculation before MI cable
work starts. MI will be developed as a separate calculation module, but it will
reuse shared thermal/design-basis services from the hardened SR foundation.

## Architecture Recommendation

Use layered calculation boundaries:

1. Input and validation layer: project setup and line-list rows become clean,
   confirmed engineering inputs.
2. Shared thermal layer: pipe OD, insulation conductivity, base heat loss,
   design heat loss, wind factor, and heat-sink/accessory adders.
3. Technology-specific selection engines:
   - SR selection for self-regulating cable catalogue curves.
   - MI selection for series-resistance factory heater sets.
4. Electrical and topology layer: current, circuit count, breaker sizing,
   branch grouping, and SLD-ready component graph.
5. Persistence layer: calculation evidence, selected/alternate/rejected
   options, power distribution, BOQ, and warnings.
6. Presentation layer: result tab, BOQ, cable schedule, SLD, and exports only
   display persisted engineering evidence.

## Review Discipline

- Keep each task small enough to review in one VS Code diff.
- Prefer one calculation behavior change plus its regression tests per pass.
- Do not change MI and SR behavior in the same pass.
- Preserve the current working UI/reporting path unless a task explicitly
  updates that path.
- Run targeted tests after each task, then broaden test coverage after related
  calculation tasks are complete.

## Task Queue

- [x] SR-01: Confirmed input safety
  - Make project calculations use only `HeatTracingInput.status='confirmed'`.
  - Add regression coverage proving pending rows are ignored and pending-only
    projects are rejected.
- [ ] SR-02: Heat loss safety factor
  - Apply `ProjectData.heat_loss_sf` explicitly.
  - Preserve/report base heat loss and design heat loss.
- [ ] SR-03: Heat loss evidence payload
  - Store/report pipe OD, conductivity, wind factor, and accessory breakdown.
- [ ] SR-04: Accessory adder refactor
  - Replace hidden hard-coded valve/flange/support adders with named rules or
    project-configurable defaults.
- [ ] SR-05: Conductivity basis review
  - Confirm whether conductivity should use maintain temperature, mean
    insulation temperature, or a project/vendor-specific basis.
- [ ] SR-06: SR catalogue filtering
  - Restore suitability filters for maintain temperature, operating/design
    temperature, exposure limit, area approval, gas group, and T-rating where
    catalogue data exists.
- [ ] SR-07: Scenario-based SR selection
  - Separate low-voltage heat delivery, nominal operation, and high-voltage
    current/safety checks.
- [ ] SR-08: Circuit current model
  - Refactor current, circuit count, and breaker sizing around per-circuit or
    per-branch load rather than ambiguous total-line current.
- [ ] SR-09: Termination margin semantics
  - Decide and implement whether termination margin is heated cable length,
    installation allowance, or cold-tail allowance for SR.
- [ ] SR-10: Rejection reasons
  - Persist structured reasons when no SR tracer is selected or when options
    are rejected.
- [ ] SR-11: Reporting alignment
  - Update result tab, exports, BOQ labels, and SLD metadata to reflect
    corrected calculation fields.
- [ ] SR-12: Regression sweep
  - Run and update import, heat loss, selection, power distribution,
    persistence, BOQ, cable schedule, and SLD tests after the SR fixes.

## Progress Notes

- 2026-05-12: Tracker created. Starting SR-01.
- 2026-05-12: SR-01 complete. `fetch_process_lines()` now returns only
  confirmed rows. Added focused tests for mixed confirmed/pending input and
  pending-only project rejection. Related upload/confirm tests pass.
- 2026-05-12: Full `eht` suite was run for regression awareness. SR-01 tests
  and upload/confirm tests pass; one unrelated SLD payload test currently
  fails because a legacy saved-topology expectation conflicts with the newer
  fail-safe baseline-change behavior.
