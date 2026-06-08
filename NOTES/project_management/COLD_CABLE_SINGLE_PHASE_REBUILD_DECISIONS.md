# Cold Cable Single-Phase Rebuild Decisions

Last updated: 2026-06-08

This file is the consolidated implementation brief for the cold-cable rebuild
that replaces the earlier mixed 1PH/3PH terminology and calculation basis.

## Naming

| Old term | New concept | UI label |
| --- | --- | --- |
| Cable4C / SourceCable | FeederCable | Feeder Cable |
| Cable3C / LoadCable | BranchCable | Branch Cable |
| 3PHJB | DistributionJB | Distribution JB |
| 1PHJB / LoadJB | BranchJB | Branch JB |

## Electrical Topology

- SR parallel runs use one shared 2-pole MCB per run group.
- SR grouped path: `MCB -> FeederCable -> DistributionJB -> BranchCables -> BranchJBs -> SR runs`.
- MI multi-sets remain individually protected: `MCB -> FeederCable -> BranchJB -> MI heater set`.
- Single-circuit direct path: `MCB -> FeederCable -> BranchJB -> tracer`.
- DistributionJB appears only when one MCB feeds two or more downstream branches.
- DistributionJB maximum outgoing branches is 4.

## Calculation Basis

- All active cold-cable engineering is single-phase for now.
- Voltage drop is evaluated at the tracer terminal as:
  `VD_total = VD_feeder + VD_branch`, using `VD = 2 x I x R x L`.
- L-PE fault-loop check is:
  `Z_loop = Z_source + R_phase_feeder + R_PE_feeder + R_phase_branch + R_PE_branch`.
- Fault current is `I_fault = V_phase / Z_loop` and is checked against the
  selected MCB type B/C/D instantaneous threshold.
- `Z_source` is calculated from the three-phase prospective short-circuit
  current at the EHT distribution board busbar entered in project setup:
  `Z_source = V_phase / (three-phase EHT DB fault rating kA x 1000)`.
- EHT DB fault rating defaults to 15 kA. Presets are 10, 15, 25, 40, and 50 kA.
  An Other value is allowed but must be at least 1 kA.
- BranchCable ampacity must be at least the upstream MCB rating. Tap-conductor
  exceptions are not part of the MVP.
- Current basis for branch summaries is branch load first:
  `per_circuit_operating_current_a x circuit_count`; line-total current is a
  fallback only.

## Storage And Quantity Rules

- Use complete path evidence per ColdCableResult, even when the FeederCable is
  shared by several branches.
- The cable schedule and BOQ must deduplicate shared FeederCable material by a
  stable feeder/group identifier so shared feeder length and mass are not
  counted once per branch.
- BranchCable quantities are counted per downstream branch.

## Migration Rules

- Delete existing ColdCableResult rows during the rebuild migration. They were
  produced under the superseded 3PH/4C/current-basis model and should not be
  partially reused.
- Retire the old phase-to-phase 4C fault fields during the rebuild:
  `fault_current_4c_phase_to_phase_a` and `fault_protection_4c_status`.
- Retire the legacy 3C line-to-neutral fault fields after the L-PE rebuild:
  `fault_current_3c_line_to_neutral_a` and `fault_protection_3c_status`.
- Add L-PE fault-loop result fields during the rebuild:
  `fault_current_l_pe_a`, `fault_loop_status`, and `fault_loop_basis`.
- Add `pe_conductor_size_mm2` to ColdCableCatalogue and seed equal-core
  unarmored 3C rows as PE = phase conductor.
- Armored/2C cable is deferred. Current active scope is unarmored/equal-core
  3C style cold cable with a dedicated PE conductor.

## Sequence

1. Fix CC-P4 current summation and shared-MCB summary foundation.
2. Add EHT DB fault rating project setting and source impedance calculation.
3. Rebuild cold-cable schema and delete stale ColdCableResult rows.
4. Rebuild cold-cable engine around single-phase FeederCable/BranchCable paths.
5. Refactor SLD/UI nomenclature away from 3PH/4C labels.
6. Add SLD-P2 combine-circuit cold-cable recalculation and length-review warning.
7. Add SLD-P1 visual review badges.
