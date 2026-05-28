-- ============================================
-- VERIFY SR CABLE POPULATION IN PostgreSQL
-- ============================================

-- 1. CHECK CURRENT STATE - ALL VENDORS
SELECT
    "Vendor",
    COUNT(*) as total_records,
    STRING_AGG(DISTINCT "Tracer_Family", ', ' ORDER BY "Tracer_Family") as families
FROM public.eht_eleceht_vendor
GROUP BY "Vendor"
ORDER BY "Vendor" ASC;

-- ============================================

-- 2. CHECK NEW RECORDS - HEAT TRACE (should show 3)
SELECT
    "V_UID",
    "Vendor",
    "Tracer_Family",
    "Tracer_Model",
    "Tracer_Cat_No",
    "Voltage",
    "Power_at_Startup_T",
    "Maint_T",
    "Max_Op_T",
    "Max_Exp_T_On"
FROM public.eht_eleceht_vendor
WHERE "Vendor" = 'Heat Trace'
ORDER BY "Tracer_Model" ASC;

-- ============================================

-- 3. CHECK NEW RECORDS - ELTHERM (should show 3)
SELECT
    "V_UID",
    "Vendor",
    "Tracer_Family",
    "Tracer_Model",
    "Tracer_Cat_No",
    "Voltage",
    "Power_at_Startup_T",
    "Maint_T",
    "Max_Op_T",
    "Max_Exp_T_On"
FROM public.eht_eleceht_vendor
WHERE "Vendor" = 'Eltherm'
ORDER BY "Tracer_Model" ASC;

-- ============================================

-- 4. CHECK NEW RECORDS - PENTAIR (should show 3)
SELECT
    "V_UID",
    "Vendor",
    "Tracer_Family",
    "Tracer_Model",
    "Tracer_Cat_No",
    "Voltage",
    "Power_at_Startup_T",
    "Maint_T",
    "Max_Op_T",
    "Max_Exp_T_On"
FROM public.eht_eleceht_vendor
WHERE "Vendor" = 'Pentair'
ORDER BY "Tracer_Model" ASC;

-- ============================================

-- 5. CHECK NEW nVENT RECORDS (BTV & QTVR series - should show 8)
SELECT
    "V_UID",
    "Vendor",
    "Tracer_Family",
    "Tracer_Model",
    "Tracer_Cat_No",
    "Voltage",
    "Power_at_Startup_T",
    "Maint_T",
    "Max_Op_T",
    "Max_Exp_T_On"
FROM public.eht_eleceht_vendor
WHERE "Vendor" = 'nVent'
  AND "Tracer_Family" IN ('BTV', 'QTVR')
ORDER BY "Tracer_Model" ASC;

-- ============================================

-- 6. SUMMARY - TOTAL RECORDS BY VENDOR
SELECT
    "Vendor",
    COUNT(*) as record_count
FROM public.eht_eleceht_vendor
GROUP BY "Vendor"
ORDER BY "Vendor" ASC;

-- ============================================

-- 7. GRAND TOTAL
SELECT COUNT(*) as total_sr_cables FROM public.eht_eleceht_vendor;

-- ============================================

-- 8. CHECK IF NEW RECORDS EXIST (Quick validation)
SELECT
    CASE
        WHEN COUNT(*) > 0 THEN 'YES - New records found'
        ELSE 'NO - New records NOT found'
    END as new_records_status
FROM public.eht_eleceht_vendor
WHERE "V_UID" IN (
    'HT-PowerHeat-240V-20',
    'Eltherm-FSH-230V-15',
    'Pentair-ACE-240V-20',
    'nVent-BTV-240V-10'
);
