# Codex Pass 1 Preparation — Architectural Review
_Date: 2026-05-24 | Author: Claude Code (architect/auditor role)_
_Documents reviewed: 00_START_HERE, CODEX_PASS1_IMPLEMENTATION_CHECKLIST,_
_READY_FOR_CODEX_IMPLEMENTATION, Claude-MI-Integration-Proposal, FIRST_PASS_SUMMARY,_
_Claude-to-Codex.md (authoritative MVP directive)_

---

## Overall Assessment

The Pass 1 concept (data-model-only, no calculation logic, no SR changes) is the
right strategy. The stated scope matches the MVP directive. However, the preparation
documents contain several internal contradictions and technical errors that, if
uncorrected, will cause Codex to build the wrong schema. Codex must be given
corrected instructions before implementation begins — not a "read all five docs and
figure it out" instruction set.

**Verdict: Do not start implementation yet. Resolve the five issues below first.**

---

## Issue 1 — BLOCKING: Cold-Lead FK Direction Contradicts Itself Across Documents

**The agreed decision** (from today's architect discussion): FK to Heater, NOT Family.

**What the documents actually say:**

| Document | Cold-lead FK direction stated |
|---|---|
| `00_START_HERE_IMPLEMENTATION_READY.md` | `cold_lead_resistance_ohms_total, cold_lead_ampacity_a` on MICableHeater ← correct |
| `CODEX_PASS1_IMPLEMENTATION_CHECKLIST.md` line 36 | "FK to Heater (per decision, not Family)" ← correct |
| `Claude-MI-Integration-Proposal.md` model code block | FK to Heater ← correct |
| `Claude-MI-Integration-Proposal.md` narrative section (near end, "Cold-Lead Model") | "**FK to Family** (not heaters)" ← WRONG |
| `FIRST_PASS_SUMMARY.md` line 72-79 | "**FK to family**… Thermon MIQ offers options **per family**" ← WRONG |

Two of the five documents give the wrong answer. `FIRST_PASS_SUMMARY.md` is
positioned as the executive summary — the document Codex is most likely to read
first for orientation. It contains the wrong FK direction.

**Action required:** Correct the cold-lead FK direction in `FIRST_PASS_SUMMARY.md`
and in the narrative section of `Claude-MI-Integration-Proposal.md` before Codex
reads them. Alternatively, add a CORRECTION header at the top of those documents.

---

## Issue 2 — BLOCKING: `MIResistanceTemperatureFactor` Duplicates Existing `MIAlloyTempFactor`

The proposal creates a new model `MIResistanceTemperatureFactor` with these fields:
`alloy_type`, `temperature_c`, `resistance_multiplier`.

`MIAlloyTempFactor` already exists in `eht/models.py` (line 583) with exactly those
same fields and the same `unique_together` constraint.

If Codex follows the checklist literally, it will create a second model that is
either a duplicate (two tables storing the same thing) or a migration collision.
The checklist caveat "If not already present" is insufficient — the existing model
has a different name, so Codex will not recognise them as the same thing.

**Action required:** Remove `MIResistanceTemperatureFactor` from the proposal
entirely. The existing `MIAlloyTempFactor` is the correct model; just use it.
The checklist should say "reuse existing `MIAlloyTempFactor`" not "create new
`MIResistanceTemperatureFactor`."

---

## Issue 3 — BLOCKING: `cold_lead_resistance_ohms_total` Is the Wrong Unit

The Claude-to-Codex.md (the authoritative MVP directive) specifies:

> "cold-lead options with their **Ω/m** and current rating"

The proposal and checklist store `cold_lead_resistance_ohms_total` — a total
resistance, not a per-metre value. This is architecturally wrong for the following
reason:

The V_effective calculation is `V_eff = V_supply − (I × R_cold_lead_total)`, where
`R_cold_lead_total = cold_lead_Ω_per_m × cold_lead_length_m`.

Cold lead length is a design-time variable (the standard options are 1.2 m and
2.1 m). `MIColdLeadOption` stores `length_m`. If you also store `ohms_total` on
`MICableHeater` without knowing which length option is selected, you cannot
compute the actual total resistance. The two fields are incoherent together.

The correct fields are:
- `cold_lead_resistance_ohms_m` on `MICableHeater` — Ω per metre, derived from
  the AWG the vendor welds to this heater model (catalogue attribute, fixed per heater)
- `cold_lead_max_ampacity_a` on `MICableHeater` — from the same AWG (catalogue attribute)
- `length_m` on `MIColdLeadOption` — the selectable lengths (1.2 m, 2.1 m etc.)

Then the engine computes: `R_cold_lead_total = cold_lead_resistance_ohms_m × selected_length_m`

This is what the MVP directive means by "Ω/m and current rating." Fix the field
name on `MICableHeater` to `cold_lead_resistance_ohms_m` before implementation.

Note also: `MIColdLeadOption` itself currently has no resistance field at all. If
different cold lead lengths use different AWGs (which can happen for long runs),
`MIColdLeadOption` would need its own `resistance_ohms_m`. For MVP, assume AWG is
fixed per heater and `cold_lead_resistance_ohms_m` on `MICableHeater` is sufficient
— but flag this assumption explicitly for Pass 2.

---

## Issue 4 — MODERATE: Seed Data Will Be Fabricated and Marked `is_validated=True`

The checklist instructs Codex to:
- Load real Thermon MIQ and nVent configurations from public spec sheets
- Set `is_validated=True` only after verification against real specs

No real spec sheet data is stored anywhere in the repo. The existing
`populate_mi_cables.py` uses a flat resistance array (10, 16, 25… Ω/km) with
`max_ampacity=60.0` on every row — clearly fabricated uniform values.

Codex will face two bad choices when it hits this instruction:
1. **Fabricate values and set `is_validated=True`** — worse than the current state
   because the engine would treat fabricated data as authoritative and return
   "selected" results based on invented numbers.
2. **Stall or skip** — leaves the catalogue empty and breaks the seed-data tests.

This is also the KR decision flagged in the audit note as a prerequisite:
_"Is real MI vendor catalogue data available to load?"_

**Action required before implementation:**
- KR decides whether real catalogue data is available. If yes, provide it for the
  seed command. If no, the seed command must load placeholder data with
  `is_validated=False`, which will cause the engine to return "no validated
  catalogue data" for every MI line (correct and safe behaviour).
- Do NOT set `is_validated=True` on any row unless KR has verified the value
  against a physical copy of the vendor catalogue or design guide.
- Revise the checklist instruction to make this explicit: "If real data is not
  yet available, load placeholders with `is_validated=False` and add a TODO."

---

## Issue 5 — MODERATE: `area_approvals` JSONField vs `zone_approval` CharField Inconsistency

The proposal (`Claude-MI-Integration-Proposal.md` section 2.1) shows:
```python
area_approvals = JSONField(default=list)  # e.g., ['ATEX-II-2G', 'IEC-Zone-1']
```

The checklist shows:
```python
zone_approval = CharField(max_length=...)  # e.g., 'ATEX-II-2G'
gas_group = CharField(...)
```

These are different field types for the same concept. JSONField with a list makes
catalogue filtering harder — the SR engine uses simple string matching on CharFields
(`_catalogue_supports_area_zone`, `_catalogue_supports_gas_group`). MI should
mirror this pattern, not diverge from it.

The SR approach (CharField per attribute: zone, gas_group, T_rating) is simpler
and more consistent. The JSONField approach is over-engineered for MVP.

**Action required:** Use CharFields matching SR's pattern (`zone_approval`,
`gas_group`, `temp_class_rating`). Remove `area_approvals` JSONField from the
proposal.

---

## Issue 6 — MINOR: `cable_technology` on `HeatLoss` Is Premature for Pass 1

The proposal adds `cable_technology = CharField(choices=[('SR',...),('MI',...),('CW',...)])` to
the `HeatLoss` model in Pass 1.

Pass 1 is data-model-only. No MI lines will be calculated, so no MI HeatLoss
records will be created. This field enables nothing in Pass 1 and adds migration
scope without benefit. It also implies a settled decision about whether MI lines
share the `HeatLoss` table — which has not been explicitly confirmed.

**Recommendation:** Defer `cable_technology` to Pass 3 when the pipeline integration
is actually being wired. Cut it from Pass 1 scope to keep the migration minimal.

---

## Issue 7 — PROCESS: The Worked-Example Test Gate Is Missing From the Plan

The authoritative MVP directive (Claude-to-Codex.md) states:

> "≥2 worked-example MI tests validated against a **published vendor design example**
> (Thermon MIQ or nVent Raychem MI design guide). A suite testing only our own
> arithmetic proves nothing about engineering correctness."

The Pass 1 checklist plans ≥8 structural model tests (unique constraints, FK checks,
seed data loads). None of these are the worked-example engineering tests.

This is technically defensible — Pass 1 has no selection logic to test against
examples — but the plan does not explicitly state that Pass 2 must include these
tests before any merge. The merge gate (≥2 worked examples) applies to the MI
selection engine, not to the data model alone.

**Action required:** The checklist should state explicitly: "The ≥2 worked-example
engineering tests (against published Thermon MIQ or nVent MI design guide values)
are a Pass 2 gate, not Pass 1. Pass 1 alone does NOT satisfy the merge prerequisite
in the MVP directive. Pass 1 and Pass 2 must both be complete and green before MI
is merged."

---

## Summary Table

| # | Severity | Issue | Action |
|---|---|---|---|
| 1 | **BLOCKING** | FK direction contradicts itself (two docs say FK to Family) | Correct FIRST_PASS_SUMMARY.md and Proposal narrative before Codex reads them |
| 2 | **BLOCKING** | `MIResistanceTemperatureFactor` duplicates existing `MIAlloyTempFactor` | Remove new model; reuse existing one |
| 3 | **BLOCKING** | `cold_lead_resistance_ohms_total` is wrong unit; must be `cold_lead_resistance_ohms_m` | Rename field; update V_effective formula reference |
| 4 | **MODERATE** | Seed data will be fabricated and marked `is_validated=True` | KR decision on real data first; placeholder-with-is_validated=False if not available |
| 5 | **MODERATE** | `area_approvals` JSONField vs CharField inconsistency | Use CharFields matching SR pattern |
| 6 | **MINOR** | `cable_technology` on HeatLoss is premature | Defer to Pass 3 |
| 7 | **PROCESS** | Worked-example test gate is not explicitly tied to a pass | State clearly: gate applies at Pass 2 merge, not Pass 1 |

---

## What Is Correct in the Preparation (Credit Where Due)

- The Pass 1 concept (data-model-only, no calculation changes) is sound.
- Scope isolation is correct — no pipeline.py, no cal.py, no tracer_selection.py.
- `SelectedMIHeater` as a separate model (not reusing `SelectedTracer`) is correct.
- `is_validated` flag concept is correct and matches catalogue discipline.
- `phase` field on `HeatTracingInput` with default `'1PH'` is correctly scoped.
- The SR regression test requirement (158 green) is correctly stated.
- The T-class verdict (pass/fail/review) with vendor-published sheath temp is correct.
- The rejection-diagnostics pattern (distinct keys: `mi_selection_status`,
  `mi_selection_rejection_reasons`) is correctly identified.

---

## Recommended Next Steps (In Order)

1. KR decides: is real MI catalogue data available for the seed command?
2. Correct the two documents with wrong FK direction (Issues 1).
3. Remove `MIResistanceTemperatureFactor` from the plan (Issue 2).
4. Change `cold_lead_resistance_ohms_total` → `cold_lead_resistance_ohms_m`
   everywhere it appears (Issue 3).
5. Resolve JSONField vs CharField for area approvals (Issue 5).
6. Update checklist to state Pass 2 worked-example test gate (Issue 7).
7. Only then: give Codex the corrected checklist as the single source of truth.
   Do not ask Codex to reconcile five contradictory documents.
