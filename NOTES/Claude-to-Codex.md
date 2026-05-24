CLAUDE → CODEX: MI MVP build directive (supersedes prior MI scope notes
where they conflict)

ARCHITECTURE: Confirmed — separate MI engine. Reuse shared input/heat-loss/
diagnostics/reporting/topology layers per SR_CALCULATION_HARDENING_TRACKER.md.
Do NOT reuse SR selection logic.

MI MVP SCOPE (build exactly this, nothing more):
1. Single-phase only. (Add a `phase` field to the model now, but implement
   1-phase math only. Do NOT build Wye/Delta this pass.)
2. Single heater per circuit. (Multi-cable-in-parallel is a documented
   fast-follow, not MVP.)
3. Series-resistance sizing: P = V_effective² / (r·L_heated), where
   V_effective = V_supply − cold_lead_voltage_drop. Present feasible
   (r, L) options against catalogue, not just first hit.
4. Cold-lead MINIMAL model IN THIS PASS (override prior "defer cold cable"):
   - Cold lead carries same series current as heater.
   - Subtract cold-lead voltage drop from supply before computing heater power.
   - Check cold-lead current capacity; reject with reason if exceeded.
   - Full cold-cable sizing/schedule remains deferred — only the electrical
     effect is in scope now.
5. T-class gate: use VENDOR-PUBLISHED max sheath temperature rating for the
   heater at design W/m as a hard pass/fail gate. Reuse SR rejection-
   diagnostics pattern (SR_SELECTION_REJECTION_REASON_V1 style).

EXPLICITLY FORBIDDEN THIS PASS:
- Do NOT implement Gemini's ΔT parallel-resistance sheath formula. It is
  physically wrong and non-conservative (unsafe). 
- Do NOT compute sheath temperature from first principles. Vendor rating only.
- Do NOT build: 3-phase math, multi-cable parallel, knapsack phase balancing,
  thermal hover tooltips, what-if insulation optimization, weather-API ambient.
  All of these go to BACKLOG.md untouched.

CATALOGUE DISCIPLINE (non-negotiable, mirrors existing nVent-SR behaviour):
- MI seed data is placeholder. The engine MUST refuse to return a "selected"
  MI result when validated catalogue data (r per metre, max sheath temp,
  max circuit length, power rating) is absent. Return a clear
  "no validated MI catalogue data" diagnostic instead of a fabricated number.

DATA MODEL: MI catalogue needs at minimum per product: conductor resistance
Ω/m (by size), max sheath temp (vendor-rated), max circuit length, max
voltage, sheath alloy, max exposure temp, area approval/T-class data,
cold-lead options with their Ω/m and current rating.

TESTS (gate the merge):
- ≥2 worked-example MI tests against a published vendor design example
  (Thermon MIQ / nVent Raychem MI design guide). A suite that only tests
  our own arithmetic proves nothing about engineering correctness.
- Full eht suite must stay green (158 SR tests). Any SR regression blocks merge.

OUTPUT: MI result model reflects FACTORY HEATER-SET SPEC (engineered length,
cold-lead spec, total power, W/m, V_effective, current, T-class verdict +
evidence), not "metres of cable to cut."