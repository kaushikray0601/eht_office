# MI Input Contract Verification
_Date: 2026-05-24 | Author: Claude Code_

## Purpose
Verify what the shared heat-loss and input layers actually deliver before any
MI code is written. Identify gaps and entanglements that must be resolved first.

---

## 1. `calculate_heat_loss` — What It Actually Returns

**Signature:**
```python
calculate_heat_loss(line, project_specific_settings, asme_b36_table, thermal_cond_data)
```

**Successful return dict keys** (all fields present on success, `None` on error):

| Key | Type | Value |
|-----|------|-------|
| `uid` | str | line uid |
| `heat_loss` | float | W/m (alias for design_heat_loss) |
| `base_heat_loss` | float | W/m before safety factor |
| `design_heat_loss` | float | W/m = base_heat_loss × wind_correction × heat_loss_sf |
| `heat_loss_sf` | float | safety factor |
| `pipe_size_mm` | float | pipe OD in mm |
| `conductivity` | float | W/m·K at evaluation temperature |
| `conductivity_basis` | dict | full provenance |
| `wind_correction` | float | multiplier |
| `accessory_adders` | dict | per-type adders + total |
| `tracer_adder` | float | total accessory length adder in metres |

**What is NOT in the heat_loss return dict:**

- Maintain temperature — only in `line['maint_temp']`
- Ambient temperature — only in `project_specific_settings['min_amb_t']`
- Supply voltage — not in heat_loss at all; lives in `project_settings['voltage']`
- Hazardous area T-class — not in heat_loss; lives in `project_settings['temp_class']`
- Heated pipe length — not echoed back; lives in `line['line_length']`
- Max exposure temperature — not echoed back; lives in `line['design_temp']`

**Conclusion:** `calculate_heat_loss` is not a self-contained record. It is a
partial result. Both downstream consumers (SR selection and, in future, MI
selection) also receive `line` and `project_settings` separately and must
read those fields directly from those dicts.

---

## 2. SR Entanglements in heat_loss Output — Verdict per Item

### 2a. `tracer_adder` naming (SR-centric name, neutral value)
The key name says "tracer" but the value is the accessory heated-length
equivalent in metres. This is directly applicable to MI: when sizing the
heater length, accessories add real metres to the heated run.

**Decision: No refactor needed.** MI reads `heat_loss['tracer_adder']` as-is.
If the name is ever cleaned up, do it project-wide as a separate rename pass,
not as a precondition for MI.

### 2b. `selection_status` / `selection_rejection_reasons` mutation
`get_tracer_options()` mutates the heat_loss dict in-place via
`_record_selection_rejection` and `_record_selection_success`. The `HeatLoss`
model stores these fields. This is where the entanglement is real.

**Consequence for MI:** If MI writes into `selection_status`, it overwrites
the SR result. A line could in principle carry both evaluations. Sharing these
keys between SR and MI in the same dict is unsafe.

**Decision: MI must NOT write into `selection_status` / `selection_rejection_reasons`.**
MI selection must use distinct keys: `mi_selection_status` and
`mi_selection_rejection_reasons`. Alternatively (cleaner for MVP): MI
returns its own result dict entirely rather than mutating the heat_loss dict.

### 2c. Does heat_loss need to be refactored to a neutral shape BEFORE MI?
No. The value fields (`design_heat_loss`, `pipe_size_mm`, `tracer_adder`)
are neutral and directly usable by MI. The in-place mutation pattern is the
only real design smell, and it is managed by using distinct keys.

**Verdict: Heat-loss output does NOT need reshaping before MI build starts.**

---

## 3. `get_tracer_options` — How SR Consumes Heat Loss (MI Integration Points)

**Signature:**
```python
get_tracer_options(heat_loss, line, project_settings, vendor_data)
```

**What SR reads from heat_loss:**
- `heat_loss['heat_loss']` — required W/m for spiral factor sizing
- `heat_loss['tracer_adder']` — accessory length adder

**What SR reads from `line` directly (NOT from heat_loss):**
- `line['maint_temp']` — maintain temperature for power-curve evaluation
- `line['line_length']` — pipe length for tracer length calculation
- `line['oper_temp']`, `line['design_temp']` — for catalogue suitability filter

**What SR reads from `project_settings` directly:**
- `voltage`, `voltage_var_factor`, `spiral_wrap_allowed`, `spiral_factor`,
  `margin_on_tracer_lengths`, `area_class`, `gas_group`, `temp_class`

**MI must mirror exactly this three-source input pattern:**
`(heat_loss, line, project_settings)` plus the MI-specific catalogue data.
No extra inputs needed; all required values are already in these three sources.

**Rejection diagnostics pattern to reuse:**
The `_record_selection_rejection(heat_loss, code, message, details)` and
`_record_selection_success(heat_loss)` helpers are importable from
`tracer_selection.py`. MI should call equivalent helpers that write to
`mi_selection_status` / `mi_selection_rejection_reasons` instead.

---

## 4. MI Catalogue Schema — Gap Analysis Against MVP Scope

### Existing models (eht/models.py lines 554–593)

**`MICableFamily`:** vendor, family_name, alloy_type, max_voltage,
max_sheath_temp_c, max_maintain_temp_c, max_watt_density_w_m

**`MICableHeater`:** family FK, part_number, conductors,
base_resistance_ohms_km (at 20°C implied), max_ampacity

**`MIAlloyTempFactor`:** alloy_type, temperature_c, resistance_multiplier

### Gaps against MVP scope

| Missing field | Where needed | Priority |
|---|---|---|
| T-class / hazardous area rating | `MICableFamily` | **MVP BLOCKER** — T-class gate is explicit MVP requirement |
| Gas group / Zone | `MICableFamily` | MVP — needed for hazardous-area suitability filter (mirrors SR pattern) |
| `max_circuit_length_m` | `MICableFamily` or `MICableHeater` | MVP — catalogue hard limit on series circuit length |
| Cold lead `max_ampacity_a` | new field or model | **MVP BLOCKER** — cold-lead current capacity check is explicit MVP requirement |
| Cold lead `resistance_ohms_per_m` | same | **MVP BLOCKER** — needed for V_effective = V_supply − cold_lead_drop |
| Validated catalogue data flag | `MICableFamily` | **MVP BLOCKER** — must refuse to select on unvalidated seed data |
| MI result storage model | new model | **MVP BLOCKER** — no `MISelectedResult` equivalent exists |

### Fields present but needing confirmation

- `base_resistance_ohms_km` in `MICableHeater` — is this at 20°C specifically?
  The `MIAlloyTempFactor` table exists to correct this to operating temperature.
  Need to confirm the reference temperature convention matches published catalogue
  data before the engine uses it.
- `max_ampacity` — at what ambient/sheath temperature? For MVP the conservative
  approach is to use the catalogue-published max without further derating.

---

## 5. `HeatTracingInput` — Completeness Check for MI

All fields MI needs are already present:

| Field | Use in MI |
|---|---|
| `line_length` | heated pipe length |
| `maint_temp` | maintain temperature for resistance target |
| `oper_temp` | operating temperature (catalogue suitability) |
| `design_temp` | max exposure temperature (T-class gate) |
| `line_size` | pipe NPS (ASME B36 OD lookup — shared with SR) |
| `insul_thick`, `ins_mat_type` | consumed by heat_loss calc (shared) |
| `valve_qty`, `flange_qty`, `support_qty` | accessory adders (shared) |

**Missing field: `phase`.**
No `phase` field exists yet. The MVP note says add it now and implement
1-phase only. Default must be `'1PH'` so all existing SR lines are unaffected.

**`ProjectData` fields MI needs (all present):**

| Field | Use in MI |
|---|---|
| `voltage` | V_supply |
| `temp_class` | T-class gate |
| `area_class` | hazardous area suitability filter |
| `allowablevdrop` | cold-lead voltage drop limit |
| `heat_loss_sf` | already applied inside `calculate_heat_loss` — do NOT apply again in MI sizing |

Note on `voltage_var_factor`: SR uses it for spiral-factor sizing at low
voltage. For MI, the series resistance is fixed; the question is whether to
use nominal or worst-case voltage for the cold-lead drop calculation. This
needs a decision — recommend worst-case (low voltage = V × (1 − var_factor))
to be conservative, consistent with SR's sizing-at-low-voltage discipline.

---

## 6. Summary: What Is Safe to Build On, What Needs Resolution First

### Safe to build on without any changes:
- `calculate_heat_loss` output — `design_heat_loss`, `pipe_size_mm`, `tracer_adder` are directly usable
- `HeatTracingInput` model — all necessary fields present (except `phase`)
- `ProjectData` — all necessary project-level fields present
- Rejection-diagnostics pattern from `tracer_selection.py` — reuse with distinct MI keys
- `MIAlloyTempFactor` table concept — sound; confirm reference temperature convention

### Must be resolved BEFORE MI selection engine is written:

1. **Add `phase` field to `HeatTracingInput`** — CharField, choices `[('1PH', 'Single Phase')]` for now, default `'1PH'`. One migration.

2. **Add T-class / gas group / Zone to `MICableFamily`** — T-class gate is a hard MVP requirement; cannot build the gate without this field.

3. **Add cold lead fields** — `cold_lead_resistance_ohms_m` and `cold_lead_max_ampacity_a` somewhere in the MI catalogue schema. Without these the cold-lead V-drop and current capacity checks (explicit MVP scope) cannot be implemented.

4. **Add `max_circuit_length_m`** — series circuits have a hard catalogue length limit; selection must enforce it.

5. **Add validated-data flag to `MICableFamily`** — catalogue discipline requires refusing selection on unvalidated seed data. A boolean `is_validated` field is sufficient for MVP.

6. **Design and add `MISelectedResult` storage model** — parallel to `SelectedTracer`; without it the MI pipeline cannot persist results.

### KR decisions needed before schema work starts:

- **Is real MI vendor catalogue data available to load?** The validated-data
  requirement is non-negotiable; every MI line will return "no validated
  catalogue data" until real data is loaded. Thermon MIQ or nVent MI design
  guide worked examples are also needed for the mandatory test gate.

- **Cold lead schema placement** — separate `MIColdLead` model, or attributes
  directly on `MICableFamily`? Depends on how Thermon/nVent publish cold lead
  specs. If cold leads are always paired with a specific heater family at a
  standard gauge, attributes on `MICableFamily` are sufficient for MVP.

- **`phase` field scope** — on `HeatTracingInput` only, or also a project-level
  default on `ProjectData`?

---

## 7. Recommended Build Sequence (awaiting KR sign-off)

1. KR confirms catalogue data availability and cold-lead schema approach.
2. Schema changes in one migration batch: `phase` on `HeatTracingInput`, missing columns on MI catalogue models, `MISelectedResult` model.
3. Load at least 1–2 published worked examples with known correct answers as validated seed data.
4. Build MI selection engine (`eht/calculations/mi_selection.py`) against those examples.
5. Add ≥2 worked-example tests validated against a published vendor design guide before any merge.
6. Full eht test suite must stay green. Any SR regression blocks the MI merge.
