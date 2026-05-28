# Comprehensive Vendor Research Findings
**Date**: 2026-05-29
**Status**: Research Complete - Ready for Database Comparison

## Data Collected by Vendor

### 1. HEAT TRACE
**Current DB**: 3 records (PowerHeat 20, 50, 100W @ 240V)
**Research Found**: Additional models available
- PowerHeat (PHT) series: Cut-to-length constant wattage (not self-regulating) - different from current SR data
- Freezstop Regular (FSR): 10, 17, 25, 31, 40 W/m outputs, max 85°C (185°F)
- Note: Current 3 records are SR, need to verify if these additional models should be added

**Action**: Research shows Heat Trace has both SR and CW cables. Current 3 are SR (estimated from industry standards). Freezstop Regular models are genuine SR cables available for 230V.

---

### 2. ELTHERM  
**Current DB**: 3 records (FSH 15, 30, 50W @ 230V)
**Research Found**: Additional model families
- ELSR-H+ series: Power outputs 15, 30, 45, 60, 75 W/m @ 230V
- ELSR-H series: Power outputs 10, 15, 20, 30, 45, 60, 75 W/m @ 230V  
- ELSR-SH series: Power outputs 15, 35, 45, 75, 90 W/m @ 230V (up to 250°C)
- Temperature ranges: Power off 210°C (ELSR-H+), 250°C (ELSR-SH)

**Current DB Analysis**: Only has FSH 15, 30, 50. FSH appears to be a different designation for ELSR series.

**Action**: Need to determine if FSH is an alias for ELSR or a separate product line. If separate, many more records can be added.

---

### 3. PENTAIR RAYCHEM
**Current DB**: 3 records (ACE 20, 50, 75W @ 240V - estimated)
**Research Found**: Actual product lines
- FrostGuard (FG) series: Pre-assembled, 6, 12, 18, 24, 36, 50, 75, 100 foot lengths @ 120V
- FrostGuard 240V models: FG2 series with 6 W/ft power output
- WinterGard Wet: 6 W/ft cut-to-length @ 120V and 240V options
- Temperature ratings: Thermal protection up to 150°F/65°C

**Current DB Analysis**: "ACE" designation not found in research. ACE records appear to be estimated placeholders rather than actual Pentair models.

**Action**: Replace estimated ACE records with actual FrostGuard/WinterGard models if they match database voltage/power specifications.

---

### 4. nVENT (RAYCHEM)
**Current DB**: 77 records (8 SR + 69 MI)
**SR Records**: BTV and QTVR at 240V
**Research Found**: Additional SR models
- BTV series: 240V self-regulating (currently have 5 records)
- QTVR series: 240V higher wattage SR (currently have 3 records)
- QTV series: Additional self-regulating model not in database
- HQTVR: High-temperature variant mentioned
- Supply voltage range: 200-277V

**Action**: Investigate QTV and HQTVR models - these may be genuinely new models not in database.

---

### 5. THERMON
**Current DB**: 31 records (9 SR + 22 MI)
**SR Records**: VSX (5 models) + HTSX (4 models)
**Research Found**: Confirmed more models available
- VSX/VSX-HT: Complete line available
- HTSX: Models 3, 6, 9, 12, 15, 20 (variants -1 and -2 for voltage)
- Additional high-temperature options

**Current DB Analysis**: Has HTSX 3, 6, 9, 12, 15 (5 records) + VSX 5, 10, 15, 20 (4 records). Missing HTSX 20 and other potential variants.

**Action**: HTSX 20-2 may not be in database - need to verify.

---

### 6. CHROMALOX
**Current DB**: 6 records (All SRM/E series @ 240V)
**Current Records**: SRM/E 20, 15, 10, 8, 5, 3 W/ft (all -2CT variants)
**Research Found**: Same SRM/E series but confirms all power ratings
- SRM/E available in: 3, 5, 8, 10, 15, 20 W/ft
- Also available: SRL (Low Temperature) variant - not researched yet

**Action**: Database appears to have complete SRM/E line at 240V already. SRL series is separate (low temp), potentially new.

---

### 7. SST
**Current DB**: 10 records (BTC and BTX series)
**Current Records**: BTC 15-60 W/m (6 records) + BTX 15-60 W/m (4 records)
**Research Found**: Extended power ratings available
- BTC: 15, 24, 30, 37, 45, 60 W/m (database has all of these!)
- BTX: 15, 30, 45, 60, 80, 95 W/m (database only has up to 60)

**Action**: BTX 80 and 95 W/m models may be new additions.

---

### 8. KRUS-ZAPAD
**Current DB**: 103 records (16 SR + 87 MI)
**Research**: Could not find comprehensive online catalogue
**Note**: Russian manufacturer - limited English documentation available

**Action**: Defer to existing backup CSV as source of truth for this vendor.

---

## Summary of Potential New Records

| Vendor | Current | Potential New | Notes |
|--------|---------|---------------|-------|
| Heat Trace | 3 | 4-8 | Freezstop Regular models to verify |
| Eltherm | 3 | 12+ | ELSR-H, ELSR-H+, ELSR-SH variants if not FSH aliases |
| Pentair | 3 | 8+ | FrostGuard/WinterGard actual models |
| nVent | 8 SR | 4-6 | QTV, HQTVR, additional BTV/QTVR variants |
| Thermon | 9 SR | 1-3 | HTSX 20-2, possible missing variants |
| Chromalox | 6 | 0-2 | SRL series (low temp) if needed |
| SST | 10 | 2+ | BTX 80, 95 W/m models |
| **Total Potential** | **47 SR** | **35-50** | Conservative estimate |

---

## Next Steps

1. ✅ Research complete
2. Create detailed temporary CSV with all feasible new records
3. Compare with database using SQL to identify truly unique records
4. Validate each record format against ElecEHT_Vendor model
5. Create safe import script with verification
6. Add to database without corruption
7. Comprehensive validation

---

## Data Quality Notes

- Some vendors (Heat Trace, Pentair) use pre-assembled fixed-length cables (not cut-to-length)
- May need separate handling or clarification on Power_at_Startup_T field
- Temperature ratings vary by model - must be verified per datasheet
- Coefficients (A, B, C) for new SR cables may need estimation or verification
