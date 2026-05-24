# Codex Pass 1 Implementation Checklist

**Objective:** Build MI data foundation without breaking SR path  
**Scope:** Data models + migration + seed data + tests (~1000 LOC)  
**Risk Level:** Low (no calculation changes)

---

## Pre-Implementation

- [ ] Read NOTES/Claude-MI-Integration-Proposal.md (sections 1-5, especially MVP blockers in section 4)
- [ ] Review NOTES/audit/MI-input-contract-verification-2026-05-24.md (section 4: MI Catalogue Schema — Gap Analysis)
- [ ] Confirm audit recommendation on cold-lead FK to Heater (not Family)

---

## Task 1: Expand Models in eht/models.py

### MICableFamily — Add MVP Blocker Fields
- [ ] `temp_class_rating` CharField: choices 'T1' through 'T6'
- [ ] `gas_group` CharField: 'IIA', 'IIB', 'IIC' (blank allowed)
- [ ] `zone_approval` CharField: e.g., 'ATEX-II-2G' (blank allowed)
- [ ] `is_validated` BooleanField: default False (MVP blocker)
- [ ] `min_circuit_length_m` FloatField
- [ ] `max_circuit_length_m` FloatField

### MICableHeater — Add Cold-Lead MVP Blockers
- [ ] `cold_lead_resistance_ohms_total` FloatField: (MVP blocker)
- [ ] `cold_lead_ampacity_a` FloatField: (MVP blocker)
- [ ] Verify `base_resistance_ohms_m` is Ohms/metre (not per km)

### Create New MIResistanceTemperatureFactor
- [ ] If not already present: alloy_type CharField, temperature_c FloatField, resistance_multiplier FloatField
- [ ] unique_together: (alloy_type, temperature_c)

### Create New MIColdLeadOption
- [ ] **FK to Heater** (per decision, not Family)
- [ ] option_code CharField
- [ ] length_m FloatField
- [ ] unique_together: (heater, option_code)

### Create New SelectedMIHeater (MVP Simplified Version)
```python
class SelectedMIHeater(models.Model):
    line = OneToOneField(HeatTracingInput, on_delete=CASCADE, related_name='selected_mi_heater_result')
    heater = ForeignKey(MICableHeater, on_delete=SET_NULL, null=True, blank=True)
    
    # Design
    heated_length_m = FloatField()
    cold_lead_option_code = CharField(max_length=20, blank=True)
    
    # Electrical
    heater_resistance_ohms = FloatField()
    cold_lead_resistance_ohms = FloatField()
    power_nominal_w = FloatField()
    power_density_w_m = FloatField()
    current_nominal_a = FloatField()
    current_cold_start_a = FloatField()
    
    # T-Class Gate (MVP)
    max_sheath_temp_published_c = FloatField(null=True, blank=True)
    project_t_class_limit_c = FloatField()
    t_class_verdict = CharField(max_length=20, choices=[('pass', 'Pass'), ('fail', 'Fail'), ('review', 'Review')])
    
    selection_basis = JSONField(default=dict)
```

### HeatTracingInput — Add phase Field
- [ ] `phase` CharField: choices [('1PH', 'Single Phase')], default='1PH'

### HeatLoss — Add cable_technology Field
- [ ] `cable_technology` CharField: choices [('SR', '...'), ('MI', '...'), ('CW', '...')], default='SR', blank=True

---

## Task 2: Create Migration

**File:** `eht/migrations/00xx_mi_catalogue_expansion.py`

- [ ] Run `python manage.py makemigrations`
- [ ] Verify: `python manage.py makemigrations --check --dry-run` (no errors)
- [ ] Review generated migration for correctness
- [ ] Apply to dev DB: `python manage.py migrate`
- [ ] Verify: `python manage.py migrate --check` (passes)

---

## Task 3: Create Seed Data Management Command

**File:** `eht/management/commands/populate_mi_catalogues_seed.py`

### Thermon MIQ Seed Data
Load real configurations from Thermon MIQ spec sheet (verify in NOTES/):
- [ ] ≥3 MIQ sizes at different resistances (e.g., 6Ω/m, 10Ω/m, 15Ω/m)
- [ ] For each: vendor='THR', family_name='MIQ', alloy_type='Alloy 825'
- [ ] Max sheath temp: verified from Thermon spec (e.g., 600°C)
- [ ] T-class rating: 'T4' or verified value
- [ ] is_validated=True (only after verification against real spec)

### nVent Raychem MI Seed Data
Load real configurations from nVent design guide (verify in NOTES/):
- [ ] ≥2 nVent sizes at different resistances
- [ ] For each: vendor='nVN', family_name='XMI-A' or similar
- [ ] Max sheath temp: verified from nVent guide
- [ ] T-class rating: verified value
- [ ] is_validated=True

### Command Implementation
```python
def handle(self, *args, **options):
    """Populate MI catalogue with real vendor data only."""
    # DO NOT USE FABRICATED DATA
    # Every value must reference real vendor documentation
    # Log the source document for each entry
```

- [ ] Command runs without errors: `python manage.py populate_mi_catalogues_seed`
- [ ] Verify data in DB/admin: FamilyX, HeaterY, ColdLeadZ records exist
- [ ] All seed records have is_validated=True
- [ ] Document source of each seed row (Thermon spec date, nVent guide version)

---

## Task 4: Create Tests

**File:** `eht/test_mi_catalogue_structure.py`

### Model Structure Tests
- [ ] test_mi_cable_family_unique_constraint: cannot create duplicate (vendor, family_name)
- [ ] test_mi_cable_heater_unique_part_number: part_number is unique
- [ ] test_cold_lead_option_fk_to_heater: ColdLeadOption must have heater FK (not family)
- [ ] test_mi_cold_lead_unique_constraint: unique_together (heater, option_code)

### Catalogue Validation Tests
- [ ] test_is_validated_flag_defaults_false: new MICableFamily has is_validated=False
- [ ] test_seed_data_is_validated_true: all seed data has is_validated=True
- [ ] test_thermon_miq_seed_loads: ≥3 Thermon MIQ entries exist
- [ ] test_nvent_mi_seed_loads: ≥2 nVent MI entries exist
- [ ] test_seed_data_has_mvp_fields: all seed rows have T-class, gas_group, temp limits

### Integration Tests
- [ ] test_thermon_miq_matches_spec_sheet: validate values against real Thermon spec (e.g., max_sheath_temp_c ~600)
- [ ] test_nvent_mi_matches_guide: validate values against nVent design guide

**Target:** ≥8 tests, all passing

- [ ] Run: `python manage.py test eht.test_mi_catalogue_structure` (all pass)

---

## Task 5: Documentation

**File:** `NOTES/eht/mi_model_design.md`

- [ ] Explain why SelectedMIHeater is separate from SelectedTracer
- [ ] Document cold-lead FK choice: "FK to Heater (not Family) because series current varies by heater size"
- [ ] Add provisional note: "FK to Heater for now; revisit as separate MIColdLead table once real vendor data is loaded"
- [ ] Explain catalogue validation discipline: refuse to select if is_validated=False
- [ ] Note the MVP blocker fields and their purpose

---

## Regression Testing

After all tasks complete:

- [ ] `python manage.py test eht.test_sr_calculation_hardening` (all pass)
- [ ] `python manage.py test eht.test_sr_reporting_alignment` (all pass)
- [ ] `python manage.py test eht` (full suite: should see 158 SR tests + new MI model tests, all green)

---

## Review Readiness

Before submitting for Claude review:

- [ ] All 5 MVP blockers implemented
- [ ] Migration created and applied locally
- [ ] Seed data loaded from **real vendor docs only**
- [ ] ≥8 tests passing
- [ ] Full SR suite passing (158+ tests)
- [ ] No changes to pipeline.py, cal.py, tracer_selection.py
- [ ] Documentation complete

---

## Diff Summary

Expected files to change:
- eht/models.py (+~200 LOC)
- eht/migrations/00xx_mi_catalogue_expansion.py (+~150 LOC)
- eht/management/commands/populate_mi_catalogues_seed.py (+~200 LOC, new)
- eht/test_mi_catalogue_structure.py (+~300 LOC, new)
- NOTES/eht/mi_model_design.md (+~100 LOC, new)

**Total: ~950 LOC**

---

## Questions During Implementation?

If any question arises:
1. Check NOTES/Claude-MI-Integration-Proposal.md section 2 (data model details)
2. Check NOTES/audit/MI-input-contract-verification-2026-05-24.md section 4 (MVP blocker details)
3. Reference the exact field names and constraints listed above

**Do not deviate from the MVP blocker list.** All 5 are required for Pass 2 to work.
