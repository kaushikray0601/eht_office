# QA-P1 Worked Examples

Last updated: 2026-06-14

Purpose: compact reviewer-facing arithmetic examples for the current MVP
calculation path. These examples are not catalogue certification. They document
the formula basis that the code and verification report must continue to show.

## Example 1 - SR Heat Loss And Straight-Run Selection

Given:

- Pipe OD: 60.3 mm = 0.0603 m.
- Insulation thickness: 50 mm = 0.05 m.
- Maintain temperature: 80 C.
- Minimum ambient temperature: 0 C.
- Insulation conductivity: 0.05 W/m.K.
- Heat-loss safety factor: 1.25.
- SR catalogue polynomial: `A = 0`, `B = 0`, `C = 40 W/m`.
- Low-voltage heat-delivery factor: `VCF = 0.9`.
- Selected SR run count: 1.

Calculation:

```text
q_base = 2 x pi x k x (T_maint - T_amb,min) / ln((2t + D) / D)
       = 2 x pi x 0.05 x 80 / ln((2 x 0.05 + 0.0603) / 0.0603)
       = 25.71 W/m

Q_design = q_base x SF
         = 25.71 x 1.25
         = 32.14 W/m

P_nom = A x T^2 + B x T + C
      = 40.00 W/m

P_LV = P_nom x VCF^2
     = 40.00 x 0.9^2
     = 32.40 W/m

F_duty = Q_design / (P_LV x N_SR)
       = 32.14 / (32.40 x 1)
       = 0.992
```

Expected interpretation:

- `F_duty <= 1.0`, so one full straight run has enough heat delivery.
- The duty ratio is evidence of heat margin, not a command to shorten installed
  tracer length.
- The verification report Section B and Section C formula text must match this
  basis.

## Example 2 - MI Automatic Fallback Evidence

Given:

- SR catalogue temperature limits are exceeded for the process line.
- Validated MI catalogue data exists for the selected vendor.
- Design heat requirement: 50 W/m over a 20 m heated length.
- One selected MI heater set supplies 1,100 W nominal.
- Cold lead option: 5 m.

Calculation:

```text
Required line heat = Q_design x heated_length
                   = 50 x 20
                   = 1,000 W

Selected MI heater nominal power = 1,100 W

Heat margin = (1,100 - 1,000) / 1,000
            = 10%
```

Expected interpretation:

- MI fallback is automatic only because SR temperature suitability failed.
- The selected MI row is valid only when the MI family is catalogue-validated.
- MI multi-set selections remain independently protected branches. This differs
  from SR parallel straight runs, which share one 2-pole MCB per run group in
  the cold-cable rebuild.

## Example 3 - Direct Single-Phase Cold Cable

Given:

- Load current: 8 A.
- Nominal voltage: 230 V.
- FeederCable length: 30 m.
- Cu conductor resistance at 20 C: 7.41 mOhm/m.
- Conductor operating temperature: 90 C.
- Copper alpha: 0.00393 / C.
- Breaker: 10 A Type C.
- EHT DB fault rating: 15 kA.

Calculation:

```text
R(T) = R_20 x (1 + alpha x (T_op - 20))
     = 7.41 x (1 + 0.00393 x (90 - 20))
     = 9.45 mOhm/m
     = 0.00945 Ohm/m

VD = 2 x I x R(T) x L
   = 2 x 8 x 0.00945 x 30
   = 4.54 V

VD_pct = 4.54 / 230 x 100
       = 1.97%

Z_source = V_phase / (fault_rating_kA x 1000)
         = 230 / (15 x 1000)
         = 0.0153 Ohm

Z_loop = Z_source + R_phase + R_PE
       = 0.0153 + (0.00945 x 30) + (0.00945 x 30)
       = 0.582 Ohm

I_fault = 230 / 0.582
        = 395 A

Type C threshold = 5 x 10
                 = 50 A
```

Expected interpretation:

- Voltage drop passes a typical 5% allowance.
- L-PE fault-loop check passes because `395 A >= 50 A`.
- The verification report Section E must show the single-phase factor 2 and the
  complete L-PE loop basis.

## Example 4 - Shared FeederCable / BranchCable Optimisation

Given:

- One SR parallel-run group feeds three downstream branches.
- FeederCable length: 25 m.
- BranchCable length: 15 m per branch.
- Per-branch current: 5 A.
- Feeder group current: 15 A.
- Candidate A: 4 mm2 FeederCable and 2.5 mm2 BranchCable.
- Candidate B: 6 mm2 FeederCable and 1.5 mm2 BranchCable.

Material proxy:

```text
Conductor volume proxy = 3 x A_feeder x L_feeder
                       + sum(3 x A_branch x L_branch)

Candidate A = 3 x 4 x 25 + 3 branches x 3 x 2.5 x 15
            = 300 + 337.5
            = 637.5 mm2.m

Candidate B = 3 x 6 x 25 + 3 branches x 3 x 1.5 x 15
            = 450 + 202.5
            = 652.5 mm2.m
```

Expected interpretation:

- If both candidates satisfy ampacity, voltage drop, and L-PE fault-loop rules,
  Candidate A has the lower material proxy.
- The optimizer must search valid catalogue pairs and choose the lowest valid
  material proxy, rather than applying a fixed voltage-drop split.
- Shared FeederCable material is counted once; BranchCable material is counted
  once per downstream branch.

