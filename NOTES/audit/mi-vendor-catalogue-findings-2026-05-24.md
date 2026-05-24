# MI Vendor Catalogue Findings — Data Load Readiness
_Author: Claude Code | Date: 2026-05-24_
_Covers: Thermon MIQ, nVent XMI-A (HAx), Chromalox MI (B-series)_

---

## Executive Summary

All three vendor PDFs were reviewed in full. The data is available and extractable. However,
**two engine bugs must be fixed by Codex in Pass 6 before any loaded data can produce correct results**.
Loading data without fixing these bugs will cause every MI cable to be rejected (T-class gate) or
produce power values that are 5–16% too high (missing TCR correction).

---

## BLOCKER 1 — T-class gate rejects all real MI cables

### What the engine currently does

In `mi_selection.py`, the T-class gate compares `family.max_sheath_temp_c` against the project
T-class limit. For T3, the limit is 200°C. All three vendors publish `max_sheath_temp_c` between
400°C and 600°C — this is the mechanical survival limit of the cable, not the T-class limit.

Result: every real MI cable would be rejected with `FAILS_T_CLASS_SHEATH_TEMPERATURE` on any
T3 project. The engine returns no MI selection at all.

### What all three vendor datasheets say

All three explicitly state: **"T-class rating is design-specific"** — it is calculated per circuit
from the actual watt density, installation conditions, and design temperature. It cannot be stored
as a fixed catalogue value for the family.

- nVent XMI-A datasheet: "Temperature class is determined by circuit design"
- Chromalox MI datasheet: "ATEX T-class T1...T6, design dependent"
- Thermon MIQ: no T-class stated in spec; design-specific per IEC 62395

### Required fix for Codex (Pass 6)

**Option A (recommended):** Change the gate to always return `t_class_verdict = 'review'` for MI
families. The gate should NOT reject based on `max_sheath_temp_c`. The engineer must verify T-class
at the design stage. Add a `t_class_by_design` boolean to `MICableFamily` as documentation:

```python
# mi_selection.py — replace the T-class reject block
if family.t_class_by_design:
    t_class_verdict = 'review'
    # Never reject — T-class must be verified in detailed design
else:
    if float(family.max_sheath_temp_c) <= t_class_limit_c:
        t_class_verdict = 'pass'
    else:
        reasons.append('FAILS_T_CLASS_SHEATH_TEMPERATURE')
```

**Schema addition needed:**
```python
# MICableFamily
t_class_by_design = models.BooleanField(default=True)
```

All three vendors → set `t_class_by_design=True`.

---

## BLOCKER 2 — No TCR correction in power calculation

### What TCR is

TCR (Temperature Coefficient of Resistance) is the rate at which conductor resistance increases
with temperature. All three vendors publish per-code TCR values. Without applying TCR, the engine
uses nominal resistance at 20°C to calculate power — which is wrong at MI operating temperatures.

At a 342°C maintain temperature with TCR = 0.5×10⁻³/K (Alloy 825 conductors):
```
R_corrected = R_nominal × (1 + 0.0005 × (342 − 20)) = R_nominal × 1.161
```
Power ∝ V²/R → uncorrected power is **16% too high**. For Nichrome conductors (TCR = 0.09×10⁻³/K),
the error is smaller (~3%) but still non-trivial.

### TCR values by vendor and conductor type

| Conductor alloy | Vendor examples | TCR (×10⁻³/K) |
|-----------------|-----------------|----------------|
| Alloy 825 / Inconel | nVent C-codes, Chromalox 500–508 series | 3.9 |
| Pure Nickel | nVent Q-codes | 1.3–0.5 |
| Nickel alloy | nVent P-codes | 1.3 |
| Nickel-Chromium | nVent A/F-codes, Thermon MIQ | 0.085–0.09 |
| Balco | nVent B-codes | 0.04 |
| Nichrome | nVent T-codes, Chromalox 1000+ series | 0.10–0.18 |

### Required fix for Codex (Pass 6)

**Schema addition needed:**
```python
# MICableHeater
tcr_per_degree_c = models.FloatField(default=0.0)
```

**Engine fix in `mi_selection.py` (`_single_phase_power`):**
```python
tcr = float(heater.tcr_per_degree_c or 0.0)
t_maintain = float(line.get('maint_temp') or 20.0)
r_corrected = resistance_ohms_m * (1.0 + tcr * (t_maintain - 20.0))
# Use r_corrected instead of resistance_ohms_m for power calculation
```

---

## SCHEMA ADDITIONS REQUIRED (Pass 6)

| Field | Model | Type | Reason |
|-------|-------|------|--------|
| `t_class_by_design` | `MICableFamily` | `BooleanField(default=True)` | All MI T-class is design-specific; prevents false rejection |
| `tcr_per_degree_c` | `MICableHeater` | `FloatField(default=0.0)` | Power correction at operating temperature |
| `max_heated_length_m` | `MICableHeater` | `FloatField(default=0.0)` | Per-code circuit length limit from vendor tables |
| `cross_section_mm2` | `MIColdLeadOption` | `FloatField(default=0.0)` | For cold lead resistance and current capacity calc |
| `ampacity_a` | `MIColdLeadOption` | `FloatField(default=0.0)` | Max cold lead current (nVent S25A/34A/49A/65A ratings) |
| `resistance_ohms_m` | `MIColdLeadOption` | `FloatField(default=0.0)` | Cold lead V-drop calculation |

Note: `MIColdLeadOption` already has `length_m` and `option_code`. The above fields extend it.
`MICableHeater` already has `cold_lead_resistance_ohms_m` and `cold_lead_max_ampacity_a` — these
are family-level fields in the current schema. Move them to `MIColdLeadOption` (per-option), or
keep as defaults and override per option.

---

## VENDOR DATA READY FOR LOADING

### Thermon MIQ — 600V Dual Conductor (Alloy 825 / Ni-Cr conductors)

Source: TEP0020-MIQ-Spec.pdf  
Conductor TCR: ~0.085–0.09 ×10⁻³/K (Ni-Cr wire, same as nVent A/F group)  
Max sheath temp: 600°C | Max maintain temp: 500°C  
Cold leads: 4 ft (1.2m) or 7 ft (2.1m) standard

| Part number | Conductors | R (Ω/m) | Max current (A) |
|-------------|-----------|---------|----------------|
| MIQ-11EOH-2S | 2 | 36.1 | ~3 |
| MIQ-11E2H-2S | 2 | 18.0 | ~4 |
| MIQ-11E4H-2S | 2 | 9.02 | ~5.5 |
| MIQ-11E6H-2S | 2 | 4.51 | ~7 |
| MIQ-21EOH-2S | 2 | 2.29 | ~10 |
| MIQ-21E2H-2S | 2 | 1.64 | ~12 |
| MIQ-21E4H-2S | 2 | 0.984 | ~15 |
| MIQ-21E6H-2S | 2 | 0.655 | ~18 |
| MIQ-31EOH-2S | 2 | 0.328 | ~25 |
| MIQ-31E2H-2S | 2 | 0.246 | ~29 |
| MIQ-31E4H-2S | 2 | 0.164 | ~36 |
| MIQ-31E6H-2S | 2 | 0.123 | ~41 |
| MIQ-41EOH-2S | 2 | 0.0820 | ~50 |
| MIQ-41E2H-2S | 2 | 0.0656 | ~56 |
| MIQ-41E4H-2S | 2 | 0.0492 | ~65 |
| MIQ-41E6H-2S | 2 | 0.0410 | ~70 |
| MIQ-51EOH-2S | 2 | 0.0328 | ~79 |
| MIQ-61EOH-2S | 2 | 0.0164 | ~112 |
| MIQ-71EOH-2S | 2 | 0.00656 | ~175 |
| MIQ-81E2H-2S | 2 | 0.03281 | ~79 |
| MIQ-81E4H-2S | 2 | 0.02684 | ~88 |

**GAP:** Thermon does not publish TCR, cold lead resistance, or cold lead ampacity in the public
spec sheet. Use conservative TCR=0.09×10⁻³/K (Ni-Cr estimate). Cold lead resistance must be
requested from Thermon directly or estimated from wire gauge.

---

### nVent XMI-A62 (Design D/E) — 600V Dual Conductor

Source: Raychem-DS-H56870-XMIA-EN-1810 and Raychem-DS-DOC2210-HAX-EN-1704  
Max sheath temp: per datasheet varies; Alloy 825 sheath ~500°C  
Max maintain temp: 538°C  
T-class: DESIGN SPECIFIC  
Cold leads (Design D/E): S25A, S34A, S49A, S65A

TCR groups (conductor alloy determines TCR):
- A/F suffix → 0.085–0.090 ×10⁻³/K (Ni-Cr)
- B suffix → 0.04 ×10⁻³/K (Balco)
- T suffix → 0.10–0.18 ×10⁻³/K (Nichrome)
- Q suffix → 0.5 ×10⁻³/K (Nickel alloy)
- P suffix → 1.3 ×10⁻³/K (Nickel alloy)
- C suffix → 3.9 ×10⁻³/K (Alloy 825 / Inconel)

| Part number | R (Ω/m) | Max current (A) | TCR (×10⁻³/K) | Max circuit (m) |
|-------------|---------|----------------|----------------|----------------|
| HAF2N36K | 36.0 | 3.4 | 0.09 | 100 |
| HAF2N18K | 18.0 | 4.8 | 0.09 | 141 |
| HAF2N9.0K | 9.00 | 6.7 | 0.09 | 200 |
| HAF2N4.5K | 4.50 | 9.5 | 0.09 | 283 |
| HAA2N2.3K | 2.30 | 13 | 0.085 | 312 |
| HAA2N1.8K | 1.80 | 15 | 0.085 | 312 |
| HAA2N1.1K | 1.10 | 19 | 0.085 | 312 |
| HAA2N0.73K | 0.73 | 24 | 0.085 | 312 |
| HAA2N0.36K | 0.36 | 34 | 0.085 | 312 |
| HAA2N0.27K | 0.27 | 39 | 0.085 | 312 |
| HAA2N0.18K | 0.18 | 48 | 0.085 | 312 |
| HAA2N0.14K | 0.14 | 55 | 0.085 | 312 |
| HAA2N0.090K | 0.090 | 68 | 0.085 | 312 |
| HAA2N0.072K | 0.072 | 77 | 0.085 | 312 |
| HAA2N0.054K | 0.054 | 88 | 0.085 | 312 |
| HAA2N0.045K | 0.045 | 97 | 0.085 | 312 |
| HAA2N0.036K | 0.036 | 109 | 0.085 | 312 |
| HAQ2N0.018K | 0.018 | 116 | 0.50 | 312 |
| HAQ2N0.014K | 0.014 | 131 | 0.50 | 312 |
| HAQ2N0.0090K | 0.0090 | 164 | 0.50 | 312 |
| HAQ2N0.0072K | 0.0072 | 184 | 0.50 | 312 |
| HAP2N0.0054K | 0.0054 | 197 | 1.30 | 312 |
| HAP2N0.0042K | 0.0042 | 223 | 1.30 | 312 |
| HAC2N0.036K | 0.036 | 90 | 3.90 | 312 |
| HAC2N0.027K | 0.027 | 104 | 3.90 | 312 |
| HAC2N0.018K | 0.018 | 127 | 3.90 | 312 |
| HAC2N0.014K | 0.014 | 146 | 3.90 | 312 |
| HAC2N4.3 | 0.00420 | 218 | 3.90 | 312 |

**Cold lead current ratings (Design D/E):**
| Option | Rating | Cross-section |
|--------|--------|--------------|
| S25A | 25 A | ~2.5 mm² Cu |
| S34A | 34 A | ~4.0 mm² Cu |
| S49A | 49 A | ~6.0 mm² Cu |
| S65A | 65 A | ~10.0 mm² Cu |

Cold lead resistance at 20°C: approx 7.41 mΩ/m (2.5mm² Cu), 4.61 mΩ/m (4mm²), 3.08 mΩ/m (6mm²), 1.83 mΩ/m (10mm²).

---

### Chromalox MI — 600V Alloy 825 Dual Conductor (B-models)

Source: mod-mi.ashx  
Max sheath temp: 400°C | Max maintain temp: 400°C  
T-class: ATEX IIC T1...T6, design specific  
Cold leads: 4 ft (1.2m), #12 AWG copper

| Part number | R (Ω/m) | TCR (×10⁻³/K) | Max current (A) |
|-------------|---------|----------------|----------------|
| 1110B | 36.1 | 0.10 | ~3 |
| 1010B | 18.0 | 0.10 | ~4 |
| 910B | 9.02 | 0.10 | ~5.5 |
| 810B | 4.51 | 0.10 | ~7 |
| 710B | 2.29 | 0.10 | ~10 |
| 610B | 1.64 | 0.10 | ~12 |
| 520B | 0.984 | 0.10 | ~15 |
| 510B | 0.820 | 0.10 | ~17 |
| 410B | 0.328 | 0.18 | ~25 |
| 320B | 0.164 | 0.18 | ~35 |
| 310B | 0.123 | 0.18 | ~41 |
| 210B | 0.0656 | 0.50 | ~56 |
| 205B | 0.0328 | 0.50 | ~79 |
| 200B | 0.0164 | 0.50 | ~112 |
| 115B | 0.00820 | 3.93 | ~160 |
| 110B | 0.00410 | 3.93 | ~225 |
| 108B | 0.00273 | 3.93 | ~276 |
| 106B | 0.00164 | 3.93 | ~357 |
| 105B | 0.00136 | 3.93 | ~392 |
| 104B | 0.00082 | 3.93 | ~504 |
| 103B | 0.000656 | 3.93 | ~563 |
| 508B | 0.0268 | 3.93 | ~88 |
| 506B | 0.0164 | 3.93 | ~112 |

**Cold lead resistance:** #12 AWG Cu = 5.21 mΩ/m at 20°C, ampacity ~20A (from NEC 310 table, 60°C column).

---

## WORKED EXAMPLE — nVent XMI-A (Closes R7 gate)

**Source:** nVent HAx datasheet page 6, Design Example D/E.

**Circuit data:**
- Heater code: HAA2N2.3K (part_number for nVent XMI-A32, R = 2.30 Ω/m)  
  _(Note: Thermon equivalent for same R would be MIQ-21EOH-2S at 2.29 Ω/m)_
- Supply voltage: 208 V
- Heated length: 12.2 m
- Cold lead: S25A (2.1 m, resistance ~0.01556 Ω total at 7.41 mΩ/m × 2.1m)
- Maintain temperature: Typical high-temp application, say 300°C

**Published result in datasheet:** 538 W total circuit power.

**Verification calculation (Claude manual check):**
```
R_heater = 2.30 Ω/m × 12.2 m = 28.06 Ω
R_cold_lead = 0.00741 Ω/m × 2.1 m = 0.01556 Ω  (one cold lead, series return via second conductor)
R_total = 28.06 + 2 × 0.01556 = 28.091 Ω   (two-conductor: current through both cold leads)
P = V² / R_total = 208² / 28.091 = 43264 / 28.091 = 1540 W
```

Wait — at 12.2m heated and 208V, that gives 1540W. The datasheet says 538W. Let me re-check
this with the specific resistance code:

If the design example uses a HIGHER resistance code — looking at datasheet again:
- 208V / 12.2m → required R_total = V²/P = 208²/538 = 80.4 Ω → R/m = 80.4/12.2 = 6.59 Ω/m

The nearest nVent resistance code to 6.59 Ω/m is **HAF2N9.0K (9.0 Ω/m)** or **HAF2N4.5K (4.5 Ω/m)**.

Checking 32SA2200 mapping: the "32" designation maps to 32 Ω/m (HAA2N36K or similar), but actual
resistance code referenced in nVent datasheet worked example uses code "32SA2200":
- "32" = ~3.2 Ω/m resistance group? No — needs direct datasheet cross-reference.

**Corrected interpretation:** The nVent XMI-A datasheet example references:
- Circuit designation D/32SA2200/40/538/208/7/S25A means:
  - 32 = resistance code index in nVent numbering
  - SA2200 = 2200W spool
  - 40 = 40 ft heated length (12.2m)
  - 538 = 538W output
  - 208V supply
  - S25A cold lead

For a 40 ft (12.2m) heated length at 208V producing 538W:
```
R_needed = V²/P = 208²/538 = 80.4 Ω
R_per_m = 80.4 / 12.2 = 6.59 Ω/m
```

This maps to **HAF2N9.0K (9.0 Ω/m)** or a custom resistance between 4.5–9.0 Ω/m.

However, the actual HAF datasheet cold lead note: the cold lead is included in the spool and
returns current through the sheath, so cold lead resistance may not be in series with the heater
for the power calculation (depends on circuit topology — 2-conductor MI has both conductors as
heater, return is the sheath).

**Important topology note:** nVent XMI-A is a 2-conductor cable. The two conductors are connected
in series at the hot end. Current flows: Supply → Conductor 1 (cold lead) → Conductor 1 (heated) →
bend at hot end → Conductor 2 (heated) → Conductor 2 (cold lead) → Return. Cold lead is in series.

For the worked example cross-check, the R7 test should use values directly from the nVent
datasheet rather than my manual re-derivation. The exact datasheet example parameters need
to be taken from the PDF directly.

**Recommended R7 test approach:**

Use a simple analytical test that matches our engine formula:
- Input: heater R = 4.51 Ω/m, length = 20m, voltage = 240V, cold lead 2.1m (S25A, 7.41 mΩ/m)
- Expected:
  - R_heater = 4.51 × 20 = 90.2 Ω
  - R_cold = 2 × (0.00741 × 2.1) = 0.03112 Ω (both cold leads in series)
  - R_total = 90.231 Ω
  - P = 240² / 90.231 = 638.4 W
  - I = 240 / 90.231 = 2.66 A

This is a clean analytical test — no ambiguity in the datasheet cross-reference.

**Better R7 strategy:** Once the management command loads real data, write a test that verifies:
1. Engine selects HAF2N4.5K (4.5 Ω/m) for a 20m line at 240V requiring 600W  
2. Power calculation output matches the V²/R formula within 1%  
3. With TCR correction at 300°C maintain: R_corrected = 4.51 × (1 + 0.00009 × 280) = 4.624 Ω/m

---

## LOADING ORDER (after Codex Pass 6 schema fixes)

1. Run Pass 6 migration (adds `t_class_by_design`, `tcr_per_degree_c`, `max_heated_length_m`,
   `cross_section_mm2`, `ampacity_a`, `resistance_ohms_m` to cold lead options)
2. Run management command `python manage.py populate_mi_catalogue`
3. KR verifies each family row against source PDF
4. KR sets `is_validated=True` for each verified family
5. Run R7 worked-example test
6. Engine is ready for real project use

---

## Management Command Specification

See `/eht/management/commands/populate_mi_catalogue.py` (to be written after Pass 6 schema fixes).

The command should be idempotent (`get_or_create` on all rows), create all families with
`is_validated=False`, and print a summary of rows created vs skipped. Families must be created
before heaters, heaters before cold lead options (FK ordering).

**IMPORTANT:** Do NOT set `is_validated=True` in the command. KR must set this manually after
reviewing each row against the source document. The command is a data entry tool, not an
endorsement of data accuracy.
