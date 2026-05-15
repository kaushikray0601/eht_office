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
- When a task adds or changes model fields, run `makemigrations --check
  --dry-run`, apply the migration to the local development database, and verify
  with `migrate --check` before using the browser workflow.
- Do not keep growing `eht/tests.py` for new SR/MI work. New substantial test
  coverage should move into smaller `eht/test_*.py` modules by domain, then the
  existing large file can be split incrementally.

## Task Queue

- [x] SR-01: Confirmed input safety
  - Make project calculations use only `HeatTracingInput.status='confirmed'`.
  - Add regression coverage proving pending rows are ignored and pending-only
    projects are rejected.
- [x] SR-02: Heat loss safety factor
  - Apply `ProjectData.heat_loss_sf` explicitly.
  - Preserve/report base heat loss and design heat loss.
- [x] SR-03: Heat loss evidence payload
  - Store/report pipe OD, conductivity, wind factor, and accessory breakdown.
- [x] SR-04: Accessory adder refactor
  - Replace hidden hard-coded valve/flange/support adders with named rules or
    project-configurable defaults.
- [x] SR-05: Conductivity basis review
  - Confirm whether conductivity should use maintain temperature, mean
    insulation temperature, or a project/vendor-specific basis.
- [x] SR-06: SR catalogue filtering
  - Restore suitability filters for maintain temperature, operating/design
    temperature, exposure limit, area approval, gas group, and T-rating where
    catalogue data exists.
- [x] SR-07: Scenario-based SR selection
  - Separate low-voltage heat delivery, nominal operation, and high-voltage
    current/safety checks.
- [x] SR-08: Circuit current model
  - Refactor current, circuit count, and breaker sizing around per-circuit or
    per-branch load rather than ambiguous total-line current.
- [x] SR-09: Termination margin semantics
  - Decide and implement whether termination margin is heated cable length,
    installation allowance, or cold-tail allowance for SR.
- [x] SR-10: Rejection reasons
  - Persist structured reasons when no SR tracer is selected or when options
    are rejected.
- [x] SR-11: Reporting alignment
  - Update result tab, exports, BOQ labels, and SLD metadata to reflect
    corrected calculation fields.
- [x] SR-12: Regression sweep
  - Run and update import, heat loss, selection, power distribution,
    persistence, BOQ, cable schedule, and SLD tests after the SR fixes.

## Deferred Heat-Loss Method Backlog

- [ ] HL-01: External heat-transfer model
  - Add recommended/basic presets for outside film coefficient, wind,
    radiation/emissivity, jacket material, and indoor/outdoor basis.
- [ ] HL-02: Standard/vendor table method
  - Add project-owned table definitions or licensed/vendor-approved table
    sources with source metadata, interpolation, and stated assumptions.
- [ ] HL-03: Integrated k(T) method
  - Add an iterative outer-surface temperature solver and polynomial
    integration of insulation conductivity across the layer temperature
    gradient.
- [ ] HL-04: Fixed project basis method
  - Add user/project-specified conductivity values, reference temperatures,
    source notes, and report warnings.
- [ ] HL-05: Multi-layer insulation
  - Extend heat-loss calculation to layer-by-layer thermal resistances.

## Progress Notes

- 2026-05-12: Tracker created. Starting SR-01.
- 2026-05-12: SR-01 complete. `fetch_process_lines()` now returns only
  confirmed rows. Added focused tests for mixed confirmed/pending input and
  pending-only project rejection. Related upload/confirm tests pass.
- 2026-05-12: Full `eht` suite was run for regression awareness. SR-01 tests
  and upload/confirm tests pass; one unrelated SLD payload test currently
  fails because a legacy saved-topology expectation conflicts with the newer
  fail-safe baseline-change behavior.
- 2026-05-12: SR-02 complete. Heat-loss calculation now applies
  `heat_loss_sf`; the compatibility `heat_loss` value is the design heat loss,
  and `HeatLoss` persists `base_heat_loss`, `design_heat_loss`, and
  `heat_loss_sf`. Focused heat-loss, tracer-selection, orchestration,
  persistence, upload, and confirm tests pass. Full `eht` suite still has the
  same unrelated SLD payload test failure noted above.
- 2026-05-12: Local upload error fixed by applying migration
  `0018_heatloss_design_basis_fields` to the development database. Added the
  migration-application check to the review discipline because unit tests use a
  test database and cannot prove the developer's current browser database has
  been migrated.
- 2026-05-12: SR-03 complete. Heat-loss calculation now returns pipe OD,
  conductivity, wind correction, and accessory-adder breakdown. `HeatLoss`
  persists this evidence through migration `0019_heatloss_evidence_fields`,
  which was applied to the development database immediately. New SR hardening
  tests start the modular `eht/test_*.py` pattern instead of growing
  `eht/tests.py`.
- 2026-05-13: SR-04 complete. The legacy valve/support/flange adder formulas
  are now isolated in `calculate_accessory_adders()` under rule set
  `SR_LEGACY_EMPIRICAL_PIPE_SIZE_IN_V1`. Numeric behavior is preserved, and
  heat-loss evidence now records the named rule, pipe-size basis, quantities,
  per-item adders, and totals.
- 2026-05-13: SR-05 paused for engineering-basis decision. Created
  `NOTES/SR_CONDUCTIVITY_BASIS_RESEARCH.md` after reviewing
  `heat_tracing_insulation_conductivity_basis.docx` and checking insulation
  design guidance, ASTM/ISO/IEC/IEEE references, and manufacturer design
  guides. No conductivity-basis code change will be made until the preferred
  method is agreed.
- 2026-05-14: SR-05 implemented after decision. Project setup now has a
  heat-loss method dropdown defaulting to mean insulation temperature. Legacy
  maintain-temperature mode remains available for comparison, while standard
  table, integrated k(T), and fixed project basis are recorded as placeholders
  that currently fall back to mean-temperature with explicit evidence. Heat
  loss results persist the conductivity basis payload for review/reporting.
- 2026-05-15: Project setup layout adjusted. The heat-loss method dropdown now
  sits in the top project/vendor row and uses a tooltip instead of helper text
  so the dense calculation rows do not shift vertically.
- 2026-05-15: SR-06 complete. SR selection now filters declared catalogue data
  for self-regulating family, maintain temperature, operating temperature,
  energized exposure temperature, area zone, optional gas group, and
  temperature class. Blank/missing catalogue fields remain non-blocking until
  catalogue data is curated. `fetch_vendor_data()` now carries suitability
  fields forward to the selection engine.
- 2026-05-15: SR-06 bug fix. Project area class values such as
  `Zone-II, IIB` combine zone and gas group in one field; the first SR-06 pass
  treated that whole string as a literal zone and rejected every catalogue row.
  The filter now parses Roman/Arabic zone tokens and IEC gas group tokens
  separately, restoring existing Thermon SR selection for `p1`.
- 2026-05-15: Vendor-selection bug fix. The embedded workspace project setup
  form did not have an explicit save action, so saving from `/base/` could post
  back to `/base/` and leave the old `ProjectData.vendor` value in place. The
  workspace form now posts to the project-data save route. Added regression
  tests proving an existing project vendor can be changed and that the base
  workspace form targets `/create-project-data/`. Also softened gas-group
  filtering so NEC-style catalogue text such as `Class I Div.2, Gr. A, B, C, D`
  is not rejected as an IEC IIA/IIB/IIC mismatch.
- 2026-05-15: Restored local project metadata after investigation side effect.
  A debugging command had removed `ManagedProject` rows; `p2` and the hidden
  `default_project` metadata are restored locally. The dropdown now shows `p1`
  and `p2` while excluding `default_project` as intended.
- 2026-05-15: SR-07 complete. SR selection now sizes heat delivery at the low
  voltage scenario, keeps nominal-voltage power output for display/persistence,
  and passes high-voltage correction into max-current and breaker sizing.
  Focused scenario and power-distribution tests were added.
- 2026-05-15: Vendor catalogue compatibility fix. Removed the database-level
  voltage lower-bound from vendor fetches because it made valid nominal 230 V
  catalogues unavailable to 240 V projects before voltage correction could be
  applied. Vendor fetch now matches names case-insensitively, which fixes the
  `KRUS-Zapad` dropdown label versus `Krus-Zapad` stored catalogue spelling.
  SR selection now applies named voltage compatibility rule
  `SR_NOMINAL_VOLTAGE_CLASS_V1`: prefer catalogue rows rated at/above project
  nominal voltage when present, otherwise allow nearby nominal classes within a
  10 percent deviation. Current local catalogue status: SST and KRUS-Zapad have
  selectable SR rows after this fix; nVent has only constant-wattage/MI rows in
  the SR catalogue table, so no nVent SR tracer can be selected until real
  nVent SR rows are loaded.
- 2026-05-15: SR-08 complete. Current and breaker sizing now use a named
  per-circuit rule set `SR_PER_CIRCUIT_BREAKER_SIZING_V1`. Line-level maximum
  and operating currents are calculated first, circuit count is based on the
  restricted loading of the maximum breaker size, and breaker size is selected
  from the per-circuit maximum current divided by the loading restriction.
  Existing result fields remain schema-compatible, with `starting_current` and
  `operating_current` now representing per-circuit values.
- 2026-05-15: SR-09 complete. The existing termination-margin behavior is now
  explicit under rule set `SR_TERMINATION_MARGIN_INSTALLATION_ALLOWANCE_V1`.
  Termination margin is treated as an installation/termination allowance added
  to ordered SR tracer length per circuit, but excluded from energized
  heat-delivery length, current, and breaker sizing. The calculation payload now
  carries heated tracer length, termination allowance length, and the semantic
  basis for review/reporting.
- 2026-05-15: Upload-time vendor persistence bug fix. The calculation pipeline
  was honoring the saved `ProjectData.vendor`, but the workspace upload AJAX
  sent only `file` and `project_id`. If a user changed the vendor dropdown and
  uploaded before pressing Save, the visible vendor was ignored and the old
  saved vendor, commonly Thermon, was used. Upload now sends the visible project
  setup fields, and `calculate_view` validates/saves them before clearing input
  data or running calculations.
- 2026-05-15: SR-10 complete. SR tracer selection now records structured
  rejection evidence on the heat-loss result under rule set
  `SR_SELECTION_REJECTION_REASON_V1`. Lines rejected for no vendor rows, no SR
  suitability match, no voltage-compatible nominal class, no positive power
  output, or no spiral-factor match remain persisted in `HeatLoss` with a
  status and machine-readable reason instead of silently disappearing after heat
  loss.
- 2026-05-16: SR-11 complete. Result tab and result Excel now distinguish
  design heat loss from base heat loss, show heat-loss safety factor and
  conductivity method evidence, label starting/operating current as
  per-circuit values, and label ordered SR tracer length as including the
  termination installation allowance. SR selection diagnostics are visible in
  the result tab and exported as a separate worksheet. BOQ tracer descriptions
  now state the ordered SR length basis, and SLD tracer nodes carry
  `sr_calculation` metadata for heat-loss, current, and tracer-length basis.
- 2026-05-16: SR-12 complete. Ran the full `eht` Django suite after the SR
  reporting pass. Import, heat loss, selection, power distribution,
  persistence, result/BOQ/cable schedule, SLD payload, SLD topology, and SLD PDF
  coverage are green with 158 passing tests.
