# Claude MI/CW Integration Strategy and First Coding Pass Proposal

**Date:** 2026-05-24  
**Status:** Architecture review + first pass proposal ready for user decision

---

## 1. Architecture Validation

### 1.1 Separate Engine Decision ✓ Confirmed Correct

The decision to build MI as a separate calculation engine (not mixed into SR code) is architecturally sound. Here's why:

| Aspect | SR | MI | Implication |
| --- | --- | --- | --- |
| **Core physics** | Parallel self-regulating heater | Series-resistance fixed-length set | Different equations, different selection logic |
| **Selection basis** | Power curve at maintain temp | Required W/m + resistance lookup + sheath check | Different catalogue predicates |
| **Output semantics** | "Cable meters to order" | "Factory heater set spec (length, cold leads, config)" | Different BOQ/deliverables |
| **Electrical circuit** | Can be field-cut within limits | Fixed heater + cold leads + joints | Different design constraints |
| **T-class interaction** | Output limits + cert data | Sheath temp at design W/m is central gate | Different validation flow |
| **Phase support** | Implicit single-phase only | Needs explicit single/three-phase modeling | Different calculation branches |

**Recommendation:** Keep SR and MI fully separated. Shared layers (heat loss, persistence, reporting) can be reused, but tracer selection engines must not share code paths.

### 1.2 Shared Layers: Correct Boundaries

Current shared layers are appropriate:

1. **Input/validation layer** (`fetch_process_lines`, `fetch_project_data`)
   - Both SR and MI use confirmed rows only ✓
   - Both use project ambient/design-basis fields ✓
   - Both need vendor/area/temp-class filters ✓
   - **MI addition:** `phase` field on HeatTracingInput (one-time field, no breaking changes)

2. **Heat-loss layer** (`calculate_heat_loss`, accessory adders, thermal conductivity)
   - Both start from same pipe OD + insulation + heat-loss SF ✓
   - MI will add its own heat-loss method adjustments later (deferred)
   - **Audit finding:** `calculate_heat_loss` output is directly usable by MI (design_heat_loss, pipe_size_mm, tracer_adder)

3. **Persistence/evidence layer** (`store_calculated_results`, HeatLoss model)
   - Current HeatLoss model is SR-specific but extensible (see below)
   - **CRITICAL:** MI must NOT write into `selection_status` / `selection_rejection_reasons` (SR fields)
   - **MI will use distinct keys:** `mi_selection_status` and `mi_selection_rejection_reasons`

4. **Reporting/export layer** (result views, BOQ, cable schedule, SLD)
   - Both will eventually feed the same reporting, but MI result semantics differ significantly

**Recommendation:** Create a new `SelectedMIHeater` result model (parallel to `SelectedTracer`). Do NOT try to reuse `SelectedTracer` for MI results. See section 2.2 below.

---

## 2. Data Model Recommendations

### 2.1 Enhance MI Catalogue Models

Current placeholder models need significant expansion. Minimum required fields:

```python
class MICableFamily(models.Model):
    """Factory heater set family."""
    vendor = CharField(max_length=30, choices=SELECT_VENDOR)
    family_name = CharField(max_length=50)  # e.g., 'MIQ', 'XMI-A'
    alloy_type = CharField(max_length=50)
    max_voltage = FloatField()
    max_sheath_temp_c = FloatField()  # VENDOR-PUBLISHED max sheath temp at design condition
    max_maintain_temp_c = FloatField()
    max_watt_density_w_m = FloatField()
    min_circuit_length_m = FloatField()  # Minimum heated length
    max_circuit_length_m = FloatField()  # Maximum heated length (important!)
    area_approvals = JSONField(default=list)  # e.g., ['ATEX-II-2G', 'IEC-Zone-1']
    temp_class_rating = CharField(max_length=10)  # e.g., 'T3', 'T4'
    
    class Meta:
        unique_together = ('vendor', 'family_name')

class MICableHeater(models.Model):
    """Specific heater resistance/size within a family."""
    family = ForeignKey(MICableFamily, on_delete=CASCADE, related_name='heaters')
    part_number = CharField(max_length=100, unique=True)
    
    # Resistance data
    base_resistance_ohms_m = FloatField()  # Ohms per METRE at 20°C (NOTE: per metre, not per km)
    cold_lead_resistance_ohms = FloatField(default=0)  # Cold lead total resistance
    
    # Current and sheath
    cold_lead_ampacity_a = FloatField()  # Max amperage the cold lead can carry
    sheath_material = CharField(max_length=50)
    
    # Conductor data
    conductor_material = CharField(max_length=50)  # e.g., 'Nickel-Chromium'
    
    class Meta:
        ordering = ['base_resistance_ohms_m']

class MIResistanceTemperatureFactor(models.Model):
    """Temperature-dependent resistance correction: R(T) = R20 * factor(T)."""
    alloy_type = CharField(max_length=50)
    temperature_c = FloatField()
    resistance_multiplier = FloatField()  # R(T_deg_c) / R20
    
    class Meta:
        unique_together = ('alloy_type', 'temperature_c')
        ordering = ['alloy_type', 'temperature_c']

class MIColdLeadOption(models.Model):
    """Pre-defined cold-lead configurations (FK to Heater per decision)."""
    heater = ForeignKey(MICableHeater, on_delete=CASCADE, related_name='cold_lead_options')
    option_code = CharField(max_length=20)  # e.g., 'CL-3M', 'CL-5M'
    length_m = FloatField()

    class Meta:
        unique_together = ('heater', 'option_code')
```

**Decision Applied:** Cold-lead FK is to **Heater** (not Family), per audit recommendation. Current depends on heater size; family is too coarse. Flagged as provisional — revisit when real Thermon/nVent data is loaded.

### 2.2 Create SelectedMIHeater Result Model (SIMPLIFIED for MVP)

**Do NOT reuse SelectedTracer.** Create a parallel result model (simplified for MVP):

```python
class SelectedMIHeater(models.Model):
    """
    Result of MI heater selection for one line.
    MVP fields only: heater spec, power, current, T-class verdict.
    """
    line = OneToOneField(HeatTracingInput, on_delete=CASCADE, related_name='selected_mi_heater_result')
    
    # Selected product
    heater = ForeignKey(MICableHeater, on_delete=SET_NULL, null=True, blank=True)
    
    # Design specifications (from series-resistance math)
    heated_length_m = FloatField()  # Pipe + accessories
    cold_lead_option_code = CharField(max_length=20, blank=True)
    
    # Electrical calculations
    heater_resistance_ohms = FloatField()
    cold_lead_resistance_ohms = FloatField()
    
    # Power @ nominal voltage
    power_nominal_w = FloatField()
    power_density_w_m = FloatField()
    current_nominal_a = FloatField()
    
    # Cold-start current (for breaker sizing)
    current_cold_start_a = FloatField()
    
    # T-class gate (MVP blocker)
    max_sheath_temp_published_c = FloatField(null=True, blank=True)  # Vendor-rated value
    project_t_class_limit_c = FloatField()
    t_class_verdict = CharField(
        max_length=20,
        choices=[
            ('pass', 'Pass - within T-class'),
            ('fail', 'Fail - exceeds T-class'),
            ('review', 'Review - vendor data missing'),
        ]
    )
    
    # Selection justification
    selection_basis = JSONField(default=dict)
    
    class Meta:
        ordering = ['line']
```

**MVP simplification applied:** Removed detailed per-scenario temperature fields. Kept only vendor-published sheath temp + project T-class limit + pass/fail/review verdict.

### 2.3 Add Required Fields to Existing Models

#### HeatTracingInput: Add `phase` field (MVP blocker from audit)

```python
class HeatTracingInput(models.Model):
    # ... existing fields ...
    
    # New: MI support (MVP blocker)
    phase = CharField(
        max_length=10,
        choices=[('1PH', 'Single Phase')],  # Extend later for 3PH
        default='1PH',
        blank=True,
    )
```

**Why:** MVP builds 1-phase only. Field must exist to avoid confusion when 3-phase is added later. Default `'1PH'` ensures all existing SR lines are unaffected.

#### HeatLoss model: Add optional `cable_technology` field

```python
class HeatLoss(models.Model):
    # ... existing SR fields ...
    
    # Optional: Track which technology this heat loss feeds
    cable_technology = CharField(
        max_length=20,
        choices=[
            ('SR', 'Self-Regulating'),
            ('MI', 'Mineral Insulated'),
            ('CW', 'Constant Wattage'),
        ],
        default='SR',
        blank=True,
    )
    
    # IMPORTANT: Do NOT use these SR-specific fields for MI results:
    # - selection_status (SR only)
    # - selection_rejection_reasons (SR only)
    # MI will use distinct keys: mi_selection_status, mi_selection_rejection_reasons
```

---

## 3. First Coding Pass: MI MVP Foundational Setup

### 3.1 Pass Goal

Establish the **data model and catalogue infrastructure** for MI without yet implementing MI selection logic or breaking the existing SR path.

This pass is **pure data/model work**, no calculation changes.

### 3.2 Tasks

#### Task 1: Create MI Models Migration

**File:** `eht/migrations/00xx_mi_catalogue_expansion.py`

Model changes (with MVP blockers from audit):

- **MICableFamily:** Add T-class, gas_group, zone_approval, is_validated, min/max circuit length fields
- **MICableHeater:** Add cold_lead_resistance_ohms_total and cold_lead_ampacity_a (MVP blockers)
- **MIResistanceTemperatureFactor:** (new) Temperature-dependent R correction
- **MIColdLeadOption:** (new) FK to Heater (per decision), length, option code
- **SelectedMIHeater:** (new) Result model with simplified MVP fields
- **HeatTracingInput:** Add `phase` field with default '1PH' (MVP blocker)
- **HeatLoss:** Add optional `cable_technology` field

**Why first:** Migrations must be applied before any calculation code tries to save results.

**Validation:**
- Run `python manage.py makemigrations --check --dry-run` (no errors)
- Apply to local dev database: `python manage.py migrate`
- Verify with `python manage.py migrate --check`
- Run existing SR tests: all 158 should still pass

#### Task 2: Create MI Catalogue Management Command

**File:** `eht/management/commands/populate_mi_catalogues_seed.py`

Load validated seed catalogue data:

```python
def handle(self, *args, **options):
    """Populate MI catalogue with representative real-world data."""
    # Example: Thermon MIQ standard configurations
    # - Each entry must reference real vendor documentation
    # - Each entry includes base_resistance_ohms_m, cold_lead_resistance, ampacity, max sheath temp
    # - NO synthetic/guessed values
```

**Why now:** Catalogue data is prerequisite for any MI testing. Seed data should come from real vendor data (e.g., Thermon MIQ spec sheet, nVent Raychem MI guide).

**Data sources:**
- Thermon MIQ: standard sizes, published specs
- nVent Raychem MI: published resistance tables, sheath ratings
- Do NOT use fabricated data; only real manufacturer data

**Validation:**
- Run the command: `python manage.py populate_mi_catalogues_seed`
- Verify data is in DB: inspect admin or shell
- Existing SR tests unaffected

#### Task 3: Create test_mi_catalogue_structure.py

**File:** `eht/test_mi_catalogue_structure.py`

Unit tests for MI catalogue data model (not selection logic yet):

```python
class MICatalogueStructureTests(TestCase):
    def test_mi_cable_family_unique_constraint(self):
        """Cannot create duplicate (vendor, family_name) pairs."""
        
    def test_mi_cable_heater_fields_required(self):
        """Heater part_number and base_resistance_ohms_m are required."""
        
    def test_cold_lead_option_persists_family_fk(self):
        """Cold lead options must reference a family."""
        
    def test_resistance_temperature_factor_lookup(self):
        """Can retrieve correction factor for alloy + temperature."""

class MICatalogueIntegrationTests(TestCase):
    """Verify catalogue seed data is plausible."""
    def test_thermon_miq_representative_seeds_load(self):
        """Thermon MIQ seed data matches real Thermon spec sheet."""
        # Example: 6 MIQ configurations at different resistances
        # Each with published max sheath temp, verify range is realistic
        
    def test_nvent_raychem_mi_seed_data_load(self):
        """nVent Raychem MI seed data matches published guide."""
```

**Why now:** Model structure tests prevent silent schema bugs and document expected catalogue data quality.

**Validation:**
- Run tests: `python manage.py test eht.test_mi_catalogue_structure`
- Tests should pass (demonstrate working data model)
- SR tests remain unaffected

#### Task 4: Document MI Data Model in Code

**File:** `eht/mi_model_design.md` (new documentation)

Record:

```markdown
# MI Cable Data Model Design

## Why Separate Models

MI is not just a "different SR cable type." The data model must reflect that:

- **SelectedMIHeater** vs **SelectedTracer**: Different semantics
  - SR result: "Order X meters of cable at Y power output"
  - MI result: "Order factory set: heated_length=A m, cold_leads=B m, config=C, sheath_temp_proof=D"
  
- **Cold lead is a first-class design element**, not an afterthought
  - Cold lead carries full heater current
  - Cold lead resistance affects power output
  - Cold lead ampacity must be checked
  - Cold lead is not "extra length" — it's a distinct product component

- **T-class verification uses published vendor sheath temp**, not calculated value
  - This pass: vendor-published max sheath temp at design W/m
  - Future pass: if no vendor data, preliminary calc (marked unsafe)

## Catalogue Data Quality Discipline

The MI engine will refuse to return a "selected" result if:
- No matching heater families exist for the project vendor + area + temp class
- No heater part numbers exist with valid base_resistance_ohms_m
- No cold-lead options exist for the selected family
- No published maximum sheath temp is available

The rejection reason will be structured (like SR rejection diagnostics) so engineers know why MI is not available rather than getting a silent empty result.

## Cold-Lead Model

Cold leads are modeled as ForeignKey relationships to families (not heaters):
- Thermon MIQ offers CL-3M, CL-5M, CL-10M options
- Each option has fixed length and typically fixed resistance
- The cold lead carries the same current as the heater → ampacity check is required
- Cold-lead voltage drop reduces available voltage for the heater: V_heater = V_supply - I * R_cold_lead
```

### 3.3 Review Checklist for Pass 1

Before merge, verify all MVP blockers are in place (from audit):

**MVP Blockers (Required):**
- [ ] `phase` field on `HeatTracingInput` with default '1PH'
- [ ] T-class, gas_group, zone_approval, is_validated fields on `MICableFamily`
- [ ] cold_lead_resistance_ohms_total and cold_lead_ampacity_a on `MICableHeater`
- [ ] `SelectedMIHeater` result model with T-class verdict fields
- [ ] `MIColdLeadOption` FK is to Heater (not Family) — flagged as provisional per audit

**Standard Pass 1 Checks:**
- [ ] Migration `00xx_mi_catalogue_expansion` applies cleanly
- [ ] `python manage.py migrate` and `python manage.py migrate --check` pass
- [ ] `populate_mi_catalogues_seed` loads real Thermon MIQ + nVent MI data (verified against published specs)
- [ ] `test_mi_catalogue_structure` passes (≥8 tests, including validation tests for is_validated flag)
- [ ] All existing 158 SR tests still pass
- [ ] No changes to `pipeline.py`, `cal.py`, or `tracer_selection.py`
- [ ] Documentation clarifies cold-lead FK rationale (provisional, flagged for revisit after real data loads)

### 3.4 Diff Scope

This pass should be reviewable in one VS Code diff:

```
eht/models.py
  - MICableFamily: add T-class, gas_group, zone_approval, is_validated, min/max circuit length
  - MICableHeater: add cold_lead_resistance_ohms_total, cold_lead_ampacity_a
  - Add MIResistanceTemperatureFactor
  - Add MIColdLeadOption (FK to Heater)
  - Add SelectedMIHeater
  - HeatTracingInput: add phase field with default '1PH'
  - HeatLoss: add cable_technology field

eht/migrations/00xx_mi_catalogue_expansion.py
  - New migration

eht/management/commands/populate_mi_catalogues_seed.py
  - New command (Thermon MIQ + nVent MI seed from public docs only)

eht/test_mi_catalogue_structure.py
  - New focused test module
  - ≥8 tests: model constraints, cold-lead FK validation, seed data source verification

NOTES/eht/mi_model_design.md
  - Design rationale and provisional note on cold-lead FK

(NO changes to calculation modules or SR logic)
```

**Estimated LOC:** ~1000 total (models + migration + command + tests + docs)

---

## 4. Audit Findings: MVP Blockers Validated

The MI Input Contract Verification audit (NOTES/audit/MI-input-contract-verification-2026-05-24.md) independently validated that:

✓ **Heat-loss output is MI-ready:** `calculate_heat_loss` returns design_heat_loss, pipe_size_mm, tracer_adder — all directly usable by MI selection  
✓ **Input models are complete:** HeatTracingInput and ProjectData already contain maintain/operating/design temps, vendor, area, T-class — no refactor needed  
✓ **Rejection pattern is reusable:** SR's diagnostic approach can be mirrored for MI with distinct keys (mi_selection_status, mi_selection_rejection_reasons)  

⚠️ **MVP Blockers identified in audit:**
1. `phase` field on HeatTracingInput (missing)
2. T-class, gas_group, zone_approval, is_validated on MICableFamily (missing)
3. cold_lead_resistance_ohms_total and cold_lead_ampacity_a on MICableHeater (missing)
4. SelectedMIHeater result model (does not exist)
5. Catalogue validation flag to refuse unvalidated data (missing)

**This Pass 1 directly addresses all MVP blockers.** No other preparatory work is required before Pass 2 (MI selection engine) can be written.

---

## 5. Why This Pass First? (Why Not Start with Selection Logic?)

1. **Unblocks downstream work:** MI selection engine will need these models
2. **Low risk:** No calculation changes, no SR impact
3. **Validates data model early:** Better to discover schema issues now than after selection logic is written
4. **Builds catalogue discipline:** Seed data from real vendor docs (Thermon, nVent) proves the model can hold realistic data
5. **Enables vendor testing:** Once seed data exists, AI can write tests against published design examples

---

## 6. Second Pass Preview (Not This PR)

After Pass 1 merges:

**Pass 2: MI Selection Engine Skeleton**
- Create `eht/calculations/mi_selection.py`
- Implement series-resistance power equation: `P = V_eff² / R_total`
- Build catalogue filtering predicates
- Implement T-class gate
- Return structured rejection diagnostics (like SR)
- Write 2-3 integration tests against published vendor examples

**Pass 3: MI Result Integration**
- Wire MI into `orchestrate_calculations()` (call MI selection if vendor is MI-capable)
- Add line-level technology choice (SR, MI, or auto)
- Persist SelectedMIHeater results
- Update reporting/BOQ to handle MI semantics

---

## 7. Key Standards/Data Sources This Pass Uses

**No external data fetched in Pass 1.** Only:
- `eht/management/commands/populate_mi_catalogues_seed.py` loads manually curated seed data
- Seed data source: Thermon MIQ spec sheet + nVent Raychem MI design guide (public docs in local NOTES)

For Pass 2, will need access to:
- Thermon MIQ design guide (section on resistance, cold leads, sheath temperature)
- nVent Raychem MI design guide (resistance tables, cold-lead options)
- IEC/IEEE 62395 or IEC/IEEE 60079-30-1 reference (sheath temp limits by T-class) — this is already captured in Claude-to-Codex.md and MI_CABLE_RESEARCH_AND_INTEGRATION_PLAN.md

---

## 8. Risk Assessment

### Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Migration conflicts with other branches | Low | High | Apply immediately, test SR path |
| Seed data is incorrect | Low | Medium | Use published vendor docs only, document source |
| SelectedMIHeater schema insufficient for Pass 2 | Medium | Medium | Review with selection engine design before final pass 1 |
| Test coverage gaps | Medium | Low | Leverage test_mi_catalogue_structure as pattern for Pass 2 |

### Strengths

- **Non-breaking:** No SR code changes
- **Clear scope:** Data model only, no logic
- **Testable:** Model tests can verify schema early
- **Documented:** Rationale is clear in models and MD files

---

## 8. Decisions Made & Next Steps for Codex Implementation

### Decisions Finalized ✓

1. **Cold-lead modeling:** FK to Heater (not Family) — flagged as provisional per audit recommendation
2. **Seed data timing:** Populate real Thermon MIQ + nVent MI in Pass 1 (now)
3. **SelectedMIHeater fields:** Simplified for MVP (removed detailed temperature scenarios)

**Audit also validated:** All MVP blockers are identified and scoped into Pass 1. No other preparation needed.

### Ready for Codex Implementation

Codex can now proceed with Pass 1 implementation:

1. **Expand models** (MICableFamily, MICableHeater, add SelectedMIHeater, etc.) with all MVP blocker fields
2. **Create migration** (`00xx_mi_catalogue_expansion.py`)
3. **Load seed data** (Thermon MIQ + nVent MI from public vendor guides)
4. **Write tests** (≥8 model structure + integration tests)
5. **Document rationale** (mi_model_design.md, provisional notes)

### Claude's Role During Implementation

Claude will:
- Review diff for schema correctness and audit compliance
- Verify seed data comes from real vendor documentation (not fabricated)
- Check test coverage for model constraints and catalogue validation
- Ensure no SR path changes or regressions
- Flag any emerging risks or data model gaps

---

## 9. Conclusion

**Pass 1 is a pure data foundation** that establishes the MI catalogue schema and validates it with real vendor seed data. It does not implement MI selection logic or break the SR path.

Once Pass 1 merges (all tests green, no SR regressions), Pass 2 can build the selection engine with confidence that the data model is sound.

This approach follows the SR_CALCULATION_HARDENING pattern: small, focused, reviewable tasks that build on a hardened foundation.
