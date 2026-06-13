# MI Vendor Data Validation — 2026-06-12

**Pass:** Vendor Data Validation (R7 gate evidence)
**Author:** Claude (architect/auditor), instructed by KR
**Scope:** All 72 `MICableHeater` rows + 3 `MICableFamily` rows seeded by
`populate_mi_catalogue.py`, validated against the manufacturers' own current
published documents.
**Method:** Official PDFs downloaded directly from vendor/distributor servers
and read page-by-page (no summarization, no third-party data). Archived in
`NOTES/vendor_validation/source_docs/`.

## Source documents

| Vendor | Document | Form / revision | File |
|---|---|---|---|
| Thermon | MIQ Mineral Insulated Cable Product Specifications | TEP0020-0714 | `thermon_miq_spec.pdf` (content.thermon.com) |
| nVent | XMI-A (Alloy 825) datasheet, US | Raychem-DS-H56870-XMIA-EN-1810 | `nvent_xmia_h56870.pdf` |
| nVent | HAx MI Alloy 825 heating cable datasheet, EMEA | Raychem-DS-DOC2210-HAX-EN-1704 | `nvent_hax_doc2210.pdf` |
| Chromalox | MI Mineral Insulated High Temperature, Heating Cable section | G-25..G-30 (mod-mi.ashx) | `chromalox_mi.pdf` (content.chromalox.com) |

## Headline verdict

**The seeded MI heater tables are largely fabricated.** Of 72 heater rows,
only 5 carry a part number AND resistance that match the vendor's published
catalogue. 3 further rows are REAL vendor codes carrying WRONG resistances
(the most dangerous class). The remaining 64 rows use part numbers that do
not exist in any of the four documents, with resistances forming invented
geometric series.

| Family | Rows | Fully correct | Real code, wrong resistance | Nonexistent code |
|---|---|---|---|---|
| Thermon MIQ | 21 | 2 (`MIQ-11EOH-2S`, `MIQ-81E4H-2S`) | 0 | 19 |
| nVent XMI-A62 | 28 | 1 (`HAF2N36K`) (+1 malformed code with right value: `HAC2N0.027K` ≙ official `HAC2N27`) | 1 (`HAC2N4.3`: DB 0.0042, official 0.0043 Ω/m) | 25 |
| Chromalox MI-825B | 23 | 2 (`1110B`, `508B`) | 3 (`810B`: DB 4.51 vs official 3.28; `710B`: DB 2.29 vs official 0.328; `520B`: DB 0.984 vs official 0.0656 Ω/m) | 18 |

Per-heater `max_current_a` is **not published in any of the four documents**
for any heater code — every stored max-current value (up to the absurd 619 A)
is fabricated. `tcr_per_degree_c` assignments are wrong almost everywhere
(see below). All three families are currently `is_validated=True`, so the MI
engine will select from this data.

A note on `is_validated`: it was found set to `True` on all three families
with no Django admin log entry (flipped programmatically, outside the
documented KR-via-admin workflow). Given this report, it must go back to
`False` until reseed + KR row review.

---

## 1. Thermon MIQ (vendor THR)

### Family row vs TEP0020-0714

| Field | Stored | Official | Verdict |
|---|---|---|---|
| max_voltage | 600 | 300 and 600 Vac | OK (600 V family) |
| max_maintain_temp_c | 500 | 932°F = 500°C | **Correct** |
| max_exposure_temp_c | 600 | 1112°F = 600°C continuous, power-off | **Correct** |
| max_sheath_temp_c | 600 | (not stated as "sheath"; 600°C exposure is the published ceiling) | Acceptable |
| max_watt_density_w_m | 250 | up to 80 W/ft = **262 W/m** | Conservative understatement; cite 262 |
| min/max_circuit_length_m | 1 / 200 | Not published; doc states tracing "up to 1 mile (1.6 km) from a single power supply point" | **200 m unverifiable and likely far too restrictive** |
| alloy/sheath | Alloy 825 | Alloy 825 seamless sheath | Correct |
| Cold leads | CL-4FT 1.219 m, CL-7FT 2.134 m | standard 4' (1.2 m) or 7' (2.1 m), 12" pigtails | **Correct** |
| TCR | 0.000088 (all heaters) | **Not published** in TEP0020 | Unverifiable — must not be stored as fact |

### Heater rows — official 600 Vac Two-Conductor table (Heater Set Type D/E), 21 codes

Official (Ω/m at 20°C, ±10%): MIQ-11EOH-2S 36.1 · MIQ-90E1H-2S 29.5 ·
MIQ-60E1H-2S 19.7 · MIQ-40E1H-2S 13.1 · MIQ-20E1H-2S 6.56 · MIQ-10E1H-2S 3.28 ·
MIQ-70E2H-2S 2.30 · MIQ-50E2H-2S 1.64 · MIQ-30E2H-2S 0.98 · MIQ-20E2H-2S 0.66 ·
MIQ-15E2H-2S 0.49 · MIQ-10E2H-2S 0.33 · MIQ-70E3H-2S 0.230 · MIQ-50E3H-2S 0.164 ·
MIQ-40E3H-2S 0.131 · MIQ-30E3H-2S 0.098 · MIQ-20E3H-2S 0.066 · MIQ-16E3H-2S 0.052 ·
MIQ-13E3H-2S 0.043 · MIQ-10E3H-2S 0.0341 · MIQ-81E4H-2S 0.02684

(The catalogue numbering encodes resistance: mantissa + E-band, e.g. 50E3H =
0.050 Ω/ft. The DB's `MIQ-21E*/31E*/41E*/51-71EOH/81E2H` codes violate this
scheme and do not appear in the document.)

DB row-by-row:

| DB part number | DB Ω/m | Verdict |
|---|---|---|
| MIQ-11EOH-2S | 36.10 | ✔ matches official 36.1 |
| MIQ-11E2H-2S | 18.00 | ✘ code and value nonexistent |
| MIQ-11E4H-2S | 9.02 | ✘ nonexistent (9.02 Ω/m exists only in the 300 V table as MIQ-27E1L-2S) |
| MIQ-11E6H-2S | 4.51 | ✘ nonexistent |
| MIQ-21EOH-2S | 2.29 | ✘ nonexistent (2.30 Ω/m is MIQ-70E2H-2S) |
| MIQ-21E2H-2S | 1.64 | ✘ nonexistent (1.64 is MIQ-50E2H-2S) |
| MIQ-21E4H-2S | 0.984 | ✘ nonexistent (0.98 is MIQ-30E2H-2S) |
| MIQ-21E6H-2S | 0.655 | ✘ nonexistent (0.66 is MIQ-20E2H-2S) |
| MIQ-31EOH-2S | 0.328 | ✘ nonexistent (0.33 is MIQ-10E2H-2S) |
| MIQ-31E2H-2S | 0.246 | ✘ nonexistent |
| MIQ-31E4H-2S | 0.164 | ✘ nonexistent (0.164 is MIQ-50E3H-2S) |
| MIQ-31E6H-2S | 0.123 | ✘ nonexistent |
| MIQ-41EOH-2S | 0.0820 | ✘ nonexistent |
| MIQ-41E2H-2S | 0.0656 | ✘ nonexistent (0.066 is MIQ-20E3H-2S) |
| MIQ-41E4H-2S | 0.0492 | ✘ nonexistent |
| MIQ-41E6H-2S | 0.0410 | ✘ nonexistent (0.043 is MIQ-13E3H-2S) |
| MIQ-51EOH-2S | 0.0328 | ✘ nonexistent (0.0341 is MIQ-10E3H-2S) |
| MIQ-61EOH-2S | 0.0164 | ✘ nonexistent — below the 2-conductor range floor |
| MIQ-71EOH-2S | 0.00656 | ✘ nonexistent — below the 2-conductor range floor |
| MIQ-81E2H-2S | 0.03281 | ✘ nonexistent |
| MIQ-81E4H-2S | 0.02684 | ✔ matches official 0.02684 |

Max current: not published per code in TEP0020. TCR: not published in TEP0020.

---

## 2. nVent XMI-A62 / HAx2N (vendor nVN)

### Family row vs both official documents

| Field | Stored | H56870 (US) | DOC2210-HAX (EMEA) | Verdict |
|---|---|---|---|---|
| max_maintain_temp_c | 538 | maintain applications up to 1022°F = **550°C** | not stated as maintain | **Wrong** — matches neither. (538 also happens to be the watts value in the doc's example catalog number; origin of the stored value is unexplained.) |
| max_sheath_temp_c | 500 | — | — | **Unsupported** |
| max_exposure_temp_c | 600 | cable 1200°F = **650°C**; brazed joints/end caps 1022°F = **550°C** | **550°C brazed / 700°C laser-welded** units | **Wrong vs both**; correct value depends on termination technology and governing doc |
| max_watt_density_w_m | 250 | 61 W/ft = **200 W/m** | **270 W/m** for HAx2N (600 V dual) | **Wrong vs both** (non-conservative vs US, conservative vs EMEA) — KR must choose governing document |
| max_circuit_length_m | 312 | per-code max unjointed length **48–312 m** (Table 5) | per-code max coil length **48–312 m** | **Non-conservative as a flat family value**; it is the limit of only the highest-resistance code |
| min_installation_temp | (not modeled) | — | –60°C | note |
| Cold leads | S25A/S34A/S49A/S65A @ 2.100 m | Table 2: S25A=25 A, S34A=34 A, S49A=49 A, S65A=65 A (Design A/D/E, 600 V); standard lengths 4 ft/7 ft | EMEA codes ACxH* with cross-sections 1–25 mm² | Codes/lengths **correct**; max currents now **verified** (25/34/49/65 A); **resistance not published in either doc** |

### Heater rows — official HAx2N table (600 V dual conductor), 28 codes

Official (Ω/km at 20°C, with per-code TCR ×10⁻³/K and max coil length):
HAF2N36K 36000/0.09/312 · HAF2N29.5K 29500/0.09/312 · HAF2N24.5K 24500/0.09/279 ·
HAF2N19.7K 19700/0.09/222 · HAA2N13.6K 13600/0.09/204 · HAA2N9000 9000/0.09/232 ·
HAF2N6600 6600/0.09/196 · HAA2N5600 5600/0.09/205 · HAT2N3750 3750/0.18/254 ·
HAB2N3000 3000/0.04/219 · HAB2N2300 2300/0.04/168 · HAT2N1670 1670/0.18/255 ·
HAQ2N1240 1240/0.5/254 · HAQ2N940 940/0.5/239 · HAQ2N660 660/0.5/229 ·
HAQ2N495 495/0.5/229 · HAQ2N330 330/0.5/179 · HAP2N255 255/1.3/188 ·
HAP2N185 185/1.3/171 · HAP2N130 130/1.3/154 · HAP2N92 92/1.3/139 ·
HAC2N66 66/3.9/145 · HAC2N43 43/3.9/128 · HAC2N27 27/3.9/100 · HAC2N17 17/3.9/90 ·
HAC2N10.5 10.5/3.9/74 · HAC2N6.6 6.6/3.9/48 · HAC2N4.3 4.3/3.9/143
(H56870 Table 5 lists the same 28 cables under US references 62Sxnnnn with
identical resistances — the two documents cross-confirm each other.)

DB row-by-row: only `HAF2N36K` (36.00 Ω/m) matches code-and-value.
`HAC2N4.3` is a real code with the wrong value (DB 0.00420; official 4.3 Ω/km
= 0.0043 Ω/m). `HAC2N0.027K` matches official `HAC2N27` in value (0.027 Ω/m)
but is not a real order reference. The other 25 codes
(HAF2N18K, HAF2N9.0K, HAF2N4.5K, HAA2N2.3K…HAA2N0.036K, HAC2N0.036K/0.018K/0.014K,
HAQ2N0.018K/0.014K/0.0090K/0.0072K, HAP2N0.0054K/0.0042K) do not exist; their
resistance ladder (18, 9.0, 4.5, 2.3, 1.8, 1.1, 0.73 …) is invented.

Conductor-letter / TCR errors are systematic: the DB labels mid-range
resistances "HAA" (TCR 0.085×10⁻³) where the real catalogue uses Q
(0.5×10⁻³) and P (1.3×10⁻³) conductors, and low resistances "HAQ/HAP" where
the real cables are C (3.9×10⁻³). Example: DB `HAA2N0.090K` TCR 0.000085 —
the real 92 Ω/km cable is `HAP2N92` with TCR 0.0013, **15× higher**. Any
resistance-vs-temperature correction computed from the stored TCRs is
invalid.

Max current: not published per heater code in either nVent document (current
capacity is governed by the cold-lead selection — Table 2 of H56870 / Table 4
of DOC2210).

---

## 3. Chromalox MI-825B (vendor CHR)

### Family row vs G-25

| Field | Stored | Official | Verdict |
|---|---|---|---|
| max_maintain_temp_c | 400 | process temperature maintenance to 1112°F = **600°C** (factory consult required above 400°F = 204°C) | **Wrong** — overly restrictive |
| max_exposure_temp_c | 450 | 1200°F = **648°C** power-off | **Wrong** — overly restrictive |
| max_sheath_temp_c | 400 | (not stated separately) | Unsupported |
| max_watt_density_w_m | 200 | up to 50 W/ft = **164 W/m**, declining with maintain temperature (Graph, p. G-29) | **Wrong — NON-CONSERVATIVE** (200 > 164) |
| Cold lead | CL-4FT 1.219 m | 4 ft standard, #12 AWG 12" pigtails | **Correct** |
| Voltage | 600 | 600 V (B-series) | Correct |

### Heater rows — official "Two conductor, Alloy 825, 600 Volts" B-series, 23 codes

Official (Ω/m at 20°C with per-model TCR multiplier):
508B 0.0268/0.00393 · 513B 0.0427/0.00393 · 520B 0.0656/0.00393 ·
528B 0.0922/0.0013 · 640B 0.1320/0.0013 · 656B 0.1840/0.0013 ·
677B 0.2540/0.0013 · 710B 0.3280/0.0007 · 715B 0.4920/0.0007 ·
720B 0.6560/0.00045 · 728B 0.9380/0.00045 · 730B 0.9840/0.00045 ·
750B 1.6600/0.00045 · 770B 2.3000/0.00006 · 810B 3.2800/0.00006 ·
811B 3.7700/0.00006 · 815B 4.9200/0.0001 · 820B 6.5600/0.0001 ·
841B 13.6000/0.0001 · 844B 14.6300/0.0001 · 960B 19.7000/0.0001 ·
989B 29.5000/0.0001 · 1110B 36.1000/0.0001

DB row-by-row:

| DB code | DB Ω/m | Official | Verdict |
|---|---|---|---|
| 1110B | 36.10 | 36.10 | ✔ correct |
| 508B | 0.0268 | 0.0268 | ✔ correct |
| 810B | 4.51 | **3.28** | ✘ **real code, wrong resistance (−27%)** |
| 710B | 2.29 | **0.328** | ✘ **real code, wrong resistance (7× high)** |
| 520B | 0.984 | **0.0656** | ✘ **real code, wrong resistance (15× high)** |
| 1010B 18.00 / 910B 9.02 / 610B 1.64 / 510B 0.820 / 410B 0.328 / 320B 0.164 / 310B 0.123 / 210B 0.0656 / 205B 0.0328 / 200B 0.0164 / 506B 0.0164 / 115B 0.0082 / 110B 0.0041 / 108B 0.00273 / 106B 0.00164 / 105B 0.00136 / 104B 0.00082 / 103B 0.000656 | — | — | ✘ **18 codes do not exist** in the B-series (catalogue floor is 0.0268 Ω/m — every stored row below that, with max currents up to 619 A, is fictitious) |

Note the booby traps: DB `410B` carries 0.328 — the value belonging to real
`710B`; DB `210B` carries 0.0656 — the value belonging to real `520B`.

TCR: official multipliers are per-model and non-monotonic; the seed script's
series-number heuristic disagrees with the catalogue for nearly every model
(e.g. official 520B = 0.00393 vs stored 0.0001; official 810B = 0.00006 vs
stored 0.0001; official 710B = 0.0007 vs stored 0.0001).

---

## 4. Items correct as seeded (for completeness)

- Thermon family temperatures (500/600°C), cold-lead lengths, Alloy 825.
- nVent cold-lead option codes S25A/S34A/S49A/S65A and 2.1 m standard length;
  their max currents (25/34/49/65 A) are now verified from H56870 Table 2.
- Chromalox 4 ft standard cold lead.
- The conductor-letter → TCR-class concept for nVent (F/A≈0.09, B=0.04,
  T=0.18, Q=0.5, P=1.3, C=3.9 ×10⁻³/K) matches the official column — it was
  just applied to invented codes.

## 5. Data now available from official sources for a correct reseed

- **Thermon**: 21 real 600 V 2-conductor codes with Ω/m and OD. No TCR, no
  per-code max current (would stay NULL/0 = engine check skipped).
- **nVent**: 28 real HAx2N codes with Ω/km, **official per-code TCR**, OD,
  max coil length, plus verified cold-lead max currents.
- **Chromalox**: 23 real B-series codes with Ω/m, **official per-model TCR**,
  OD. (G-25 also publishes 300 V K-series, 1-conductor S-series, and
  stainless SC/S tables — out of current scope.)
- Family limits per the tables above (nVent needs KR's governing-document
  decision: US H56870 vs EMEA DOC2210 values differ).

## 6. Open gaps that remain even after a reseed (no published source)

- Per-heater max current (all vendors) — not a published catalogue figure;
  the practical limit comes from cold-lead rating (nVent), breaker sizing
  tables (Thermon design guide), or watt-density/temperature curves.
- Cold-lead conductor resistance (all vendors) — not published; nVent EMEA
  gives cross-sections (1–25 mm² Cu) from which standard IEC 60228 values
  could be **derived** if KR approves clearly-labeled derived data.
- Thermon TCR — not in TEP0020; Thermon publishes resistance-vs-temperature
  in design-guide graphs only.
- Chromalox maintain-temperature watt-density derating curve — published as a
  graph (G-29), not storable as a single number; flat family watt density is
  a simplification either way.

## 7. Status — corrective action EXECUTED 2026-06-12 (KR-approved)

KR approved all four corrective decisions in writing on 2026-06-12:
revoke validation now; Claude reseeds from official tables; nVent governed by
EMEA DOC2210 with brazed-unit (conservative) limits; cold-lead resistance
stays empty (no derived data).

Executed against `eht_local` (backup first:
`backup_mi_catalogue_pre_reseed_2026-06-12.json` — 3 families, 72 heaters,
177 cold-lead options, 15 selections):

- Deleted 72 fabricated `MICableHeater` rows + 177 cascaded cold-lead options.
- Inserted 72 official heaters (21 THR + 28 nVN + 23 CHR) and 177 cold-lead
  options, official resistance/TCR only; `max_current_a=0.0` and cold-lead
  electrical fields left empty (no published source).
- Families corrected and **all set `is_validated=False`**:
  - THR MIQ: maintain 500 / sheath 600 / exposure 600 °C, watt density 262 W/m.
  - nVN XMI-A62: maintain 550 / sheath 550 / exposure 550 °C (brazed-unit
    basis), watt density 270 W/m.
  - CHR MI-825B: maintain 600 / sheath 648 / exposure 648 °C, watt density
    164 W/m (G-29 derating curve caveat; factory consult above 400 °F per doc).
- Verified: 72 heaters / 177 cold leads; spot checks `710B`=0.328,
  `520B`=0.0656/TCR 0.00393, `810B`=3.28, `HAC2N4.3`=0.0043, `HAP2N92`
  TCR 0.0013, Thermon TCR=None.
- **15 `SelectedMIHeater` snapshots are now orphaned (`heater=NULL`)** — they
  were computed from fabricated data and must be recalculated.

Remaining for KR (R7 gate): row-by-row review of the reseeded data against
the archived PDFs, then set `is_validated=True` per family **via Django
admin** (logged).

Side findings for Codex (not fixed by Claude):
- `MIColdLeadOption.__str__` raises `MICableHeater.DoesNotExist` while
  django-easy-audit stringifies instances during cascade delete (audit noise,
  delete still succeeds).
- Schema gap: no per-heater max cable length field — nVent publishes per-code
  max coil lengths (48–312 m); flat family `max_circuit_length_m=312` is
  non-conservative for most codes.
- Engine note: with `max_current_a=0.0` the per-heater current check in
  `mi_selection.py` is skipped — current limiting now relies on breaker/cold
  lead design checks only.
