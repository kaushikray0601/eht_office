# SR Vendor Data Validation — 2026-06-12

**Pass:** Vendor Data Validation (VDV-P1), SR phase — REPORT ONLY, no DB change.
**Author:** Claude (architect/auditor), instructed by KR.
**Scope:** All 58 Self-Regulating rows in `ElecEHT_Vendor` (the live SR
selection library — note this table has NO `is_validated` gate; SR is the
production default path).
**Method:** Official vendor datasheets downloaded and read directly; stored
quadratic `P(T) = A·T² + B·T + C` evaluated at 10 °C and compared with the
vendor's published W/m rating at 10 °C (50 °F). Source PDFs archived in
`NOTES/vendor_validation/source_docs/`.

## Headline verdict

| Block | Rows | Verdict |
|---|---|---|
| Thermon HTSX 3/6/9/12/15-2 | 5 | **VERIFIED GOOD** — real models, P(10 °C) within 4% of official 9/19/29/38/48 W/m (240 V basis) |
| Thermon VSX 5/10/15/20-2 | 4 | **VERIFIED GOOD** — real models, P(10 °C) within 4% of official 16/33/49/66 W/m; temps match (maintain 149→150, power-on exposure 232 ✓) |
| Chromalox SRM/E 3–20 (2CT) | 6 | **VERIFIED GOOD** — exact ordering-matrix naming, maintain 150 °C ✓, exposure 215 °C ✓, P(10 °C) within 3% of 3/5/8/10/15/20 W/ft |
| SST BTC 15–60 (BTC2-BP) | 6 | **VERIFIED GOOD** — exact marking-scheme naming, 230 V ✓, maintain 120 °C ✓, exposure 200 °C ✓, P(10 °C) within 3.5% of class ratings |
| SST BTX 15/30/45/60 | 4 | **GOOD with caveats** — real family/classes; exposure 200 °C ✓; stored maintain 120 °C is far below official 250 °C (over-restrictive); P(10 °C) runs ~9% above the 230 V classes (looks like a 240 V scaling while the row says 230 V) |
| nVent BTV "BTV-2-10/25/50/75/100" | 5 | **WRONG/FABRICATED** — see below |
| nVent QTVR "QTVR-2-25/50/100" | 3 | **WRONG/FABRICATED** — see below |
| Eltherm "FSH-230-15/30/50" | 3 | **NO SUCH FAMILY** at Eltherm (their SR range is ELSR-*; "FSH" is a Heat Trace Ltd product name) |
| Heat Trace "PH-240-20/50/100" | 3 | **NO SUCH FAMILY** found (their SR families are FSR/FSE/FSLe/FSM/FSEw/FSS/FSH…) |
| Pentair "ACE-240-20/50/75" | 3 | **NO SUCH FAMILY** found (Pentair-era Raychem SR families are BTV/QTVR/XTV/KTV/HTV; Pentair thermal became nVent in 2018) |
| Krus-Zapad CK-FS.250 (16 ratings) | 16 | **UNVERIFIABLE ONLINE** — no public vendor literature found; coefficients are exact straight lines crossing zero at 240.0 °C with C = P0×(240/230), i.e. formula-generated, not digitized. KR to supply the source document. |

**25 of 58 rows verified good. 8 fabricated (nVent). 9 attributed to families
that do not exist at the named vendors. 16 unverifiable online.**

The fabricated/unsourced block is recognisable by shared template
coefficients: every nVent, Heat Trace, and Pentair row uses A = −0.00025,
B = −0.15 (QTVR −0.18; Eltherm A = −0.0003, B = −0.16) with C set to a round
W/m number — unlike the genuinely digitized rows, which have distinct fitted
coefficients.

## nVent detail (Raychem-DS-H51086-BTV-EN-1805, archived)

- Real BTV catalogue: **3BTV2, 5BTV2, 8BTV2, 10BTV2** (-CR/-CT), i.e.
  3/5/8/10 W/ft ≈ 10/16/26/33 W/m. Supply 200–277 V.
- Stored models `BTV-2-10/25/50/75/100` (10–100 W/m): naming matches no
  vendor format, and **50/75/100 W/m exceed anything the BTV family makes**.
- Temperatures: official maintain/continuous power-on **65 °C** (stored 65 ✓)
  but official intermittent exposure is **85 °C** — stored `Max_Exp_T_On=204`
  is wildly non-conservative: a line with design temperature up to 204 °C
  would pass the exposure check against a cable rated 85 °C.
- QTVR: official maintain/continuous exposure 110 °C (stored 110 ✓); real
  models are `10/15/20QTVR2-CT` (≈33/49/66 W/m). Stored `QTVR-2-100`
  (≈98 W/m at 10 °C) exceeds the family; naming matches no vendor format.
- **Engine impact:** SR is the default path and `ElecEHT_Vendor` has no
  validation gate. A project configured with vendor = nVent would today
  select from fabricated curves and accept exposure temperatures ~2.4× the
  real cable rating. This is the most safety-relevant SR finding.

## Verified-row evidence (sample points, stored P(10 °C) vs official)

| Row | Stored P(10) W/m | Official @10 °C | Δ |
|---|---|---|---|
| HTSX 3-2 | 10.1 | 9 (230 V) ≈ 9.8 @240 V | +3% |
| HTSX 15-2 | 49.9 | 48 (230 V) ≈ 52.3 @240 V | −4.5% |
| VSX 10-2 | 31.8 | 33 | −3.6% |
| VSX 20-2 | 65.6 | 66 | −0.6% |
| SRM/E10-2CT | 33.0 | 32.8 (10 W/ft) | +0.6% |
| SRM/E20-2CT | 65.5 | 65.6 (20 W/ft) | −0.2% |
| 15BTC2-BP | 15.5 | 15 | +3.5% |
| 60BTC2-BP | 60.1 | 60 | +0.2% |

## Minor gaps in otherwise-good blocks (for KR's list)

- Thermon HTSX 20-2 (64 W/m) exists in the catalogue but is missing from DB.
- SST 8BTC2-BP (8 W/m) exists but is missing from DB.
- SST BTX 75/100 W/m classes exist but are missing from DB.
- HTSX rows store V=240 while the European spec is 230 V nominal; VSX rows
  store V=230 while the US spec is 240 V nominal — labels appear swapped;
  curve magnitudes suggest HTSX was digitized at 240 V, VSX at 240 V class
  ratings. Worth a deliberate KR decision on the voltage basis convention.
- HTSX stored `Max_Exp_T_On=204` is the *continuous power-off* figure; the
  power-on intermittent figure is 250 °C. Conservative, but mislabeled.
- SST rows have `Power_at_Startup_T = 0` (missing data, engine impact
  depends on startup-current usage).
- BTX maintain temperature stored as 120 °C vs official 250 °C
  (over-restrictive; copied from BTC).

## Source documents (archived in source_docs/)

| Vendor | Document | File |
|---|---|---|
| nVent | Raychem-DS-H51086-BTV-EN-1805 | `nvent_btv_us.pdf` |
| Thermon | HTSX spec, Form TEP0074U-0317 (230 V) | `thermon_htsx.pdf` |
| Thermon | VSX spec, Form TEP0008-0219 | `thermon_vsx.pdf` |
| Chromalox | SRM/E catalogue pages G-11..G-13 | `chromalox_srme.pdf` |
| SST | PREMIUM line BTC datasheet (280223) | `sst_btc.pdf` |
| SST | BTX family figures confirmed via distributor product page (sigmian.com); official `TDS_PREMIUM_BTX` blocked by TLS error — fetch directly from sst-international.com when possible | — |

QTVR EU datasheet (RAYCHEM-DS-EU1381) download was corrupt; maintain 110 °C
confirmed from nVent product page. Fetch and archive before correcting QTVR
rows.

## Recommended corrective plan (NOT executed — KR decision required)

1. **Quarantine or replace the 8 nVent rows** with the real BTV/QTVR (and
   optionally XTV/KTV) families from official datasheets. BTV data is already
   in hand. Until then, do not run SR calculations with project vendor =
   nVent.
2. **Eltherm / Heat Trace / Pentair rows (9):** decide per vendor — obtain
   the real family data (Eltherm ELSR-*, Heat Trace FSR/FSH), or delete.
   "Pentair" as a vendor identity should probably be retired (now nVent).
3. **Krus-Zapad (16):** KR to provide the source catalogue; rows stay as-is
   until then (they are at least self-consistent and conservative-shaped).
4. Minor fixes from the gaps list above (BTX maintain temp, HTSX/VSX voltage
   basis, missing classes, BTV/HTSX exposure semantics).
5. **Schema recommendation for Codex (KR to approve):** `ElecEHT_Vendor` has
   no `is_validated` gate, unlike the MI catalogue. Phase A hardening should
   consider one, so unverified SR rows cannot silently drive the default
   production path (extends R-008/R-011 to SR).
