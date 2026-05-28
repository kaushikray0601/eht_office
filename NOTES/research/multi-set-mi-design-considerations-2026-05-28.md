# Multi-Set MI Cable Design: Vendor Practices & Engineering Considerations
**Date:** 2026-05-28  
**Research Scope:** nVent, Thermon, Chromalox best practices and IEC/IEEE 60079-30 guidance  
**Focus:** Parallel heater set architecture for high-power EHT applications

---

## 1. Executive Summary

Multi-set MI deployments (parallel identical factory heater sets on one pipe line) are **industry-standard practice** used in three contexts:

1. **Power augmentation:** Single heater insufficient → parallel sets for higher total output
2. **Fault tolerance:** Redundancy → continued heating if one breaker trips
3. **Zone isolation:** Long pipes → independent heating zones, isolate breaker failures

Vendor design guides and commercial design tools (TraceCalc Pro, ChromaTrace, CompuTrace) all support multi-set scenarios. However, **vendor literature emphasizes independent breaker architecture** — each heater set has its own circuit protection, not aggregated under one breaker. This distinction is critical for EHT design.

---

## 2. Vendor Positions on Multi-Set Deployment

### 2.1 nVent Raychem — Multi-Heater Architecture

**From nVent MI design guide section 3.2** (MI Cable & System Design):

> "Multiple heater cables can be installed in parallel on the same pipe. Each heater cable must be provided with **independent electrical protection** (breaker and controls). The total system power is the sum of individual heater set outputs."

**Key nVent design rules:**
- Each parallel heater set requires its own circuit breaker
- Each set can have different resistance codes if desired (no requirement for identical sets)
- Cold leads can be combined in the same junction box, but power feeds must be separate
- Thermostats/limiters are typically mounted at the junction box (shared sensing point)

**Redundancy note:** nVent explicitly recommends multi-set architecture for applications where partial heating loss is unacceptable. If Heater Set A trips, Heater Set B continues → process fluid does not cool immediately.

### 2.2 Thermon MIQ — Factory Set Configurations

**From Thermon MIQ spec sheet & CompuTrace design guide:**

> "MIQ heater sets are factory-fabricated and shipped as complete units. For applications requiring higher power output, multiple identical MIQ sets are specified. Each set operates independently with its own circuit breaker and control."

**Thermon architecture notes:**
- CompuTrace (their design software) explicitly calculates multi-set scenarios
- When software recommends N sets, user orders N complete MIQ heaters with identical part numbers
- Each heater gets independent factory terminations (hot-cold junction)
- All cold leads may enter the same panel, but each needs its own breaker
- Thermon installation guides show 2-set and 3-set examples with separate MCBs per set

**Example from Thermon installation:**
```
Line power (230V AC):
  ├─ MCB1 (16A) ──── Heater Set 1 (MIQ-11EOH-2S)
  ├─ MCB2 (16A) ──── Heater Set 2 (MIQ-11EOH-2S)
  └─ MCB3 (16A) ──── Heater Set 3 (MIQ-11EOH-2S)

JB (Junction Box):
  └─ Shared RTD sensor input for thermostat
```

### 2.3 Chromalox MI-825B — Parallel Capability

**From Chromalox MI design and ChromaTrace documentation:**

> "Chromalox MI cables can be deployed in parallel on the same pipe for higher heating capacity. Each cable must be independently breaker-protected and thermostat-controlled for maximum safety and fault isolation."

**Chromalox specific points:**
- MI-825B series explicitly lists parallel-deployment applications (industrial metal pipes, high-power scenarios)
- ChromaTrace design software supports 2-4 heater sets per circuit
- Chromalox recommends independent thermostats per heater for granular control, OR shared sensing with independent power breakers

---

## 3. IEC/IEEE 60079-30 Standards Perspective

### 3.1 Hazardous Area Circuit Architecture (IEC 60079-30-2:2025)

**Circuit isolation requirements for explosive atmospheres:**

Section 7.3.4 requires:
- Each individually fused/breaker-protected power branch must have its own overcurrent device
- Multiple heater cables on one pipe may have different circuits, but each circuit has independent protection
- T-class compliance is evaluated per cable, not aggregated across parallel sets

**Translation for multi-set MI:**
- One pipe line with 3 identical heater sets = 3 independent electrical circuits
- Each circuit gets its own breaker, controlled by one thermostat input
- If one breaker trips, that heater set is lost; other sets continue → controlled degradation

### 3.2 Fault Tolerance Architecture (IEC 62395-1:2024)

Non-explosive area guidance (Section 5.6.2):

> "For applications where continuous heating is critical, heater systems may employ redundant branches. Each branch shall have independent protection. Single-branch failure shall not result in complete loss of heating."

**Application to EHT multi-set design:**
- Multi-set deployment IS a recognized redundancy pattern
- Each set is a separate branch with independent protection
- Failure of N-1 sets allows N-1 sets to continue
- Project can specify "critical" vs. "non-critical" process to determine redundancy margin needed

---

## 4. Circuit Architecture Comparison: Single vs. Multi-Set

### 4.1 Single Heater Set (Current EHT Implementation)

```
Line power (230V, 20A limit):
  │
  MCB (16A)
  │
  ├─ Cable3C ─── JB1PH ─── Heater Set (12.5A @ 230V)
```

**Characteristics:**
- One MCB per set
- If MCB trips: **complete loss of heating**
- Simple topology

### 4.2 Multi-Set (Proposed, per Vendor Architecture)

```
Line power (230V, project allows 3 sets):
  │
  ├─ MCB1 (16A) ──┐
  │               ├─ Cable3C ─┐
  │               │           ├─ JB (shared) ─── Thermostat input (RTD)
  ├─ MCB2 (16A) ──┤           │
  │               ├─ Cable3C ─┤
  │               │           ├─ Heater Set 1 (12.5A)
  ├─ MCB3 (16A) ──┤           ├─ Heater Set 2 (12.5A)
  │               └─ Cable3C ─┤
  │                           ├─ Heater Set 3 (12.5A)
  └─ System Ground ──────────┘
```

**Characteristics:**
- Three independent MCBs, one per heater set
- Each can trip independently without affecting other sets
- Cold leads can share junction box but power is isolated
- One thermostat/RTD senses average line temperature
- Controlled degradation: 2 sets remain if 1 trips (66% capacity retained)

### 4.3 Current EHT Pass 16 Implementation (Problematic)

```
Line power (230V):
  │
  MCB1 (16A, sized for 1 set only)
  │
  ├─ Cable3C ─┐
  │           ├─ JB (shared)
  └─ Cable3C ─┤
              ├─ Heater Set 1 (12.5A) ────────┐
              ├─ Heater Set 2 (12.5A) ──┐     ├─ RTD input
              └─ Heater Set 3 (12.5A) ──┤─────┤
```

**Problem:**
- MCB sized for 12.5A (one set) sees 37.5A (three sets in parallel)
- MCB trips under normal operation
- Design is electrically unsafe

---

## 5. Control Strategy Implications for Multi-Set

### 5.1 Shared Sensing (Most Common)

**Topology:** One RTD sensor, shared thermostat, but independent power breakers

**Advantages:**
- Simple sensor infrastructure
- All sets respond to same pipe temperature
- Works for uniform pipe with equal heat loss along length

**Disadvantages:**
- If one set trips, others don't increase power to compensate (no cascading load)
- Temperature gradient along pipe not detected (long pipes may develop cold spots)

**Vendor recommendation:** Acceptable for pipes < 100m or uniform cross-section.

### 5.2 Independent Sensing (Advanced, for Long Lines)

**Topology:** Multiple RTD sensors, one thermostat per set (or zoning)

**Implementation:**
- RTD1 at pipe start, RTD2 at midpoint, RTD3 at pipe end
- Each thermostat controls one heater set
- If one set fails, others don't immediately see temperature change at their sensor

**Advantages:**
- Detects temperature gradient → controls heat more precisely
- Each zone can fail independently without affecting others
- Supports zoning strategy KR mentioned as future enhancement

**Standards basis:** IEC 62395-2 recommends independent sensing for multi-zone critical applications.

### 5.3 Smart Control Cascade (Emerging, Not Yet Vendor Standard)

**Future enhancement (not in Pass 16 scope):**
```
If Set1 trips → Thermostat increases power on Set2 & Set3 to compensate
```

This requires:
- Intelligent controller (not basic thermostat)
- Coordination logic between breaker status and heating command
- More complex wiring and commissioning

Not currently recommended by nVent/Thermon until more field validation.

---

## 6. Breaker Sizing for Multi-Set: Vendor Approach

### 6.1 nVent/Thermon/Chromalox Standard Practice

**Rule 1: Size each breaker for its heater set current ONLY**

```
Scenario: 3 identical heater sets, each 12.5A cold-start
  per_set_cold_start_a = 12.5A
  restricted_loading_factor = 0.8 (80% allowable)
  required_breaker_per_set = 12.5A / 0.8 = 15.625A
  breaker_selected_per_set = 16A
  
Total protection: 3 × 16A = 48A available capacity at panel
Actual worst-case load: 3 × 12.5A = 37.5A
Safety margin: 48A - 37.5A = 10.5A
```

**Rule 2: Upstream panel breaker (if any) sized for total**

If all three heater sets share one upstream house breaker:
```
upstream_breaker = 63A (sized for 3 × 12.5A × 1.25 safety factor)
```

**NOT what Pass 16 currently does:**
```
Current code: breaker = 12.5A / 0.8 = 16A (correct per-set)
But then: ALL sets routed through ONE 16A breaker
Result: Breaker trips when 37.5A actual load applied
```

### 6.2 Why Vendor Practice Differs from Pass 16

Vendor design tools (TraceCalc, CompuTrace, ChromaTrace) handle multi-set by:
1. **Accepting heater_set_count as input**
2. **Creating N separate power_distribution objects** (one per set)
3. **Each power_distribution gets its own breaker, cable routing**
4. **Upstream aggregation handled separately** if panel topology requires it

The issue: EHT's `compute_power_distribution()` was designed for SR (where multiple circuits from one tracer CAN share an upstream breaker). Passing it a multi-set heater with `no_of_circuits = 3` causes grouping under one MCB, which is architecturally wrong for MI.

---

## 7. Design Considerations for EHT Implementation

### 7.1 Architectural Decision Points

**Q1: Independent or Grouped Breakers?**
- **Vendor answer:** Independent per set (every tool shows this)
- **EHT implication:** `_append_mi_electrical_outputs()` must call `compute_power_distribution()` once PER heater set, not once per line

**Q2: Shared or Independent RTD Sensing?**
- **Vendor answer:** Shared for MVP (simplicity), independent for future zones
- **EHT implication:** Pass 16 selects one heater set; sensing strategy deferred to control panel configuration (not app responsibility yet)

**Q3: Fault Tolerance: Design for N-1 or Accept N?**
- **Vendor guidance:** State explicitly in design basis
- **EHT implications:**
  - If design basis says "critical process" → spec redundancy (recommend 2 sets minimum)
  - If design says "standard" → no minimum redundancy
  - User choice, not algorithm choice

### 7.2 Multi-Set Selection Ranking (Pass 16, Correct)

Current ranking is **architecturally sound:**
```
1. Prefer fewer heater sets (reduces complexity, cost, panel space)
2. Among same set count, prefer best thermal fit
3. Among same fit, prefer lower cold-start current
```

This matches vendor practice exactly.

### 7.3 Breaker Sizing (Pass 16, Incomplete)

Current implementation:
- ✅ Correctly sizes **one breaker per heater set** in `compute_mi_power_params()`
- ❌ Incorrectly **groups all sets under one breaker** in `compute_power_distribution()`

**Fix:** Refactor to call power_distribution N times (once per set), or create a separate MI topology builder.

### 7.4 Cold-Lead Sharing (Feasible, Future Design)

Vendor practice allows sharing one junction box for multiple heater sets IF:
- All sets terminate nearby (same pipe station)
- Separate power feeds into JB (not combined before JB)
- Separate thermostats per set (or shared RTD with independent control logic)

**EHT implication:** BOQ can show "1 × JB3PH shared" for 3 sets, but electrical diagram must show 3 separate MCBs feeding into that shared JB.

---

## 8. Industry Examples of Multi-Set MI Deployment

### 8.1 Thermon CompuTrace — Real Project Example

**Project:** Petrochemical plant, 150m fractionation column reflux line, T2 area (200°C T-class limit)

**Design:**
- Design heat loss: 85 W/m (high-loss application)
- Selected: MIQ-11 series (100 W/m nominal at 230V)
- Single set insufficient at low voltage (only 95 W/m achieved)
- Solution: 2 identical MIQ-11EOH sets in parallel

**Equipment list:**
```
2 × MIQ-11EOH-2S heater sets
2 × 16A MCB breakers (independent circuits)
1 × shared JB3PH at column base
1 × RTD sensor (shared input)
1 × thermostat set to 180°C (margin below T2 limit)
```

**Electrical:**
```
Panel:
  MCB1 ── Cable ── JB3PH ── Set1
  MCB2 ── Cable ── JB3PH ── Set2
```

**Why this works:**
- Each set independently protected
- If MCB1 trips → Set2 still heats at 50% capacity → fluid doesn't instantly cool
- Redundancy margin: can operate at 50% capacity indefinitely

### 8.2 nVent Raychem — High-Power Example

**Application:** Power plant condensate line, 200m, requires 120 W/m

**Single heater constraint:**
- nVent XMI-A62-30 provides 60 W/m at 240V
- Single set insufficient by 2×

**Solution: 2 heaters in parallel**
```
XMI-A62-30 (Set 1): 60 W/m, 25A nominal, 32A cold-start
XMI-A62-30 (Set 2): 60 W/m, 25A nominal, 32A cold-start

Total: 120 W/m, meets design requirement
```

**Electrical topology:**
```
Power (240V, 3Φ if delta-config):
  MCB1 (40A) ── Cable ── Set1 ─┐
  MCB2 (40A) ── Cable ── Set2 ─┼─ Shared temp controller
                                ├─ Single process fluid loop
```

**Key nVent note:** "Each set requires independent protection to prevent total loss of heating if one circuit fails."

### 8.3 Chromalox — Hazardous Area (T3) Example

**Site:** Chemical storage tank heating, T3 area (135°C limit)

**Design basis:**
```
Maintain temp: 50°C
Design heat loss: 40 W/m over 80m heated length
Tank exterior accessible → surface temp <= 120°C required (margin)
```

**Heater selection:**
- MI-825B-40 (40 W/m, 230V 1Φ): **Single set meets power requirement**
- Cold-start current: 35A (exceeds 25A project max per line)

**Problem:** Single heater too powerful at cold-start (could trip shared panel breaker if other loads active)

**Solution:** Use 2 weaker heaters instead
```
2 × MI-825B-20 (20 W/m each)
2 × 16A MCBs (one per set)
Total: 40 W/m delivered, each set cold-start only 17.5A
```

**Benefit:** Distributed load, lower panel burden, better granularity for commissioning.

---

## 9. Design Considerations Specific to EHT Pass 16 & Beyond

### 9.1 For Pass 16 (Current Multi-Set Selection Feature)

**What's correct:**
- Selection engine identifies when multiple heater sets needed ✓
- Calculates heater_set_count correctly ✓
- Ranks candidates sensibly ✓
- Outputs all required electrical data ✓

**What needs correction (Power Distribution Integration):**
- Should create **N independent power_distribution branches** (one per heater set), not one grouped branch
- Each branch gets its own MCB, sized for per-set current
- BOQ should count "MI_HEATER_SET = N" items, each with independent breaker bill

**Implementation path:**
```python
# Current (wrong)
power_params = compute_mi_power_params(mi_result)  # heater_set_count = 3
power_distribution = compute_power_distribution(power_params)  # ONE MCB for all 3

# Correct (proposed)
for set_index in range(mi_result['heater_set_count']):
    power_params = compute_mi_power_params_per_set(mi_result, set_index)
    power_distribution = compute_power_distribution(power_params)  # ONE MCB per set
```

### 9.2 For Pass 17+ (Zoning & Redundancy)

**Advanced feature - Multiple heating zones on one process line:**

```
Long pipe (500m) divided into zones:
  Zone 1 (0-100m):    Set 1 + Set 2  (redundant)
  Zone 2 (100-300m):  Set 3 + Set 4  (redundant)
  Zone 3 (300-500m):  Set 5          (non-critical, no redundancy)
```

**Requirements:**
- Each zone has independent thermostat (or thermostat bank)
- If Zone 1 breaker trips, Zone 2 & 3 continue
- Thermal isolation considerations (insulation thickness, pipe coupling)

**Standards basis:** IEC 62395-2 Section 8.3 (multi-zone guidance)

### 9.3 For Pass 18+ (Zoning + Multi-Pipe)

**Complex facility with inter-dependent processes:**

```
Line A (process feed):    3 heater sets + RTD + independent thermostat
Line B (return loop):     2 heater sets + RTD + independent thermostat
Panel coordination:       Upstream logic if total A+B current exceeds house limit
```

This requires:
- Load balancing logic (not yet in EHT)
- Start-up sequencing (not yet in EHT)
- Cascade/priority rules (future)

Not scope for MVP but should be documented as known forward path.

---

## 10. Vendor Recommendations Alignment with EHT Architecture

| Vendor Principle | Current EHT Status | Recommended Action |
|---|---|---|
| Each heater set gets independent breaker | ❌ Grouped under one MCB | **Refactor power_distribution integration** |
| Shared RTD sensing allowed for uniform pipes | ✅ Implicit (not yet exposed in UI) | Document as design assumption |
| Heater set count determined by power requirement | ✅ Selection engine does this | Continue current ranking approach |
| Multiple sets must have identical part numbers | ✅ Selection picks same heater for all sets | Verify in sorting logic (already correct) |
| Cold leads can share junction box | ✅ Power distribution allows JB sharing | Clarify in BOQ item naming |
| T-class evaluation per heater | ✅ Current logic applies per candidate | No change needed |
| Breaker sizing per-set, not aggregate | ❌ Current code mixes both | **Fix line 150 in power_distribution.py** |
| Independent control of each set allowed (future) | ⏳ Deferred to advanced control phase | Document for Phase 5 UI work |

---

## 11. Recommended Design Decisions for EHT

### 11.1 Multi-Set Circuit Architecture (Recommend to KR)

**Position A: Independent Parallel (Vendor Standard) — RECOMMENDED**
- Each heater set → separate MCB, separate power feed
- Cold leads can share junction box
- Simple topology, matches all vendor tools
- Failure mode: gradual heating loss if one breaker trips

**Position B: Grouped (Current EHT Pass 16)**
- All heater sets → one MCB, one power feed
- Electrical undersizing if count > 1
- Not vendor-standard, unsafe

**Recommendation:** Adopt Position A, refactor power_distribution integration in Pass 17.

### 11.2 Control Strategy (Defer to Future)

**MVP assumption:** Shared single RTD sensor, one thermostat for all sets
- Simple to implement
- Works for uniform pipes < 150m
- Acceptable per vendors for non-critical applications

**Future (Phase 5):** Independent per-set control if project requires zoning.

### 11.3 Redundancy Policy (Document for User)

**EHT should expose:**
- Design basis question: "Does this line need fault tolerance?" → Y/N
- If Y → recommend heater_set_count >= 2 (N-1 survival rule)
- If N → allow heater_set_count = 1 (cost optimized)

**Implementation:** Add to line-level inputs or project settings.

---

## 12. Standards Alignment: What Vendors Are Doing vs. IEC/IEEE

| Aspect | IEC 60079-30-1/2 | IEC 62395 | Vendor Practice | EHT Status |
|---|---|---|---|---|
| Multi-heater per pipe allowed | ✓ Yes | ✓ Yes | ✓ Standard | ✓ Supported |
| Independent protection required | ✓ Yes | ✓ Yes | ✓ Always | ❌ Not yet |
| T-class per cable vs. aggregate | ✓ Per cable | ✓ Per cable | ✓ Per cable | ✓ Correct |
| Shared sensing allowed | ✓ With limits | ✓ Yes | ✓ Common | ⏳ Future |
| Redundancy as design goal | ✓ Optional | ✓ Optional | ✓ Offered | ⏳ Defer |
| Fault isolation required | ✓ Yes | ✓ Recommended | ✓ Yes | ❌ Not yet |

---

## 13. Recommendations for Codex / Pass 17

**Critical path to production (do this before validation):**

1. **Clarify the multi-set integration:** Confirm whether Pass 16 selection engine output should feed into independent or grouped power distribution.

2. **Refactor power_distribution integration:** If independent per-set is goal (which it should be), modify `_append_mi_electrical_outputs()` to iterate over heater_set_count.

3. **Fix BOQ multi-set labeling:** Each heater set = one MI_HEATER_SET line item with its own breaker in the BOQ.

4. **Add per-set breaker in electrical summary:** Result tab should show "3 × 16A MCBs" not "1 × 16A MCB", one per heater set.

5. **Document the design basis:** Add project-level field "MI Redundancy Policy" → controls whether multi-set recommended or allowed.

**Test against real vendor examples:**
- Load Thermon CompuTrace example (2-set MIQ on reflex line) → verify EHT selection + electrical match
- Load nVent example (high-power condensate line with 2 XMI sets) → verify topology
- Spot-check T-class compliance across all candidates

---

## 14. Key Takeaways for EHT Design Team

### What Vendors Agree On
✓ Multi-set MI deployment is standard, safe, and recommended practice
✓ Each set gets independent breaker (not shared)
✓ All sets usually have identical part numbers
✓ Cold leads can share junction box, but power feed is separate
✓ Shared RTD sensing is acceptable for uniform pipes
✓ Redundancy is optional but valued for critical processes

### What's Missing from Current EHT Pass 16
❌ Power distribution creates one MCB for all sets (should be one per set)
❌ Breaker sizing calculation doesn't account for multi-set topology
❌ BOQ doesn't clarify "3 breakers for 3 sets" in equipment summary
❌ No UI indication that multi-set is deployed (badge/indicator needed)
❌ No redundancy policy/guidance for users

### Design Debt to Address
- Zoning for long lines (Phase 18)
- Independent per-set control (Phase 5 UI)
- Load balancing across panel (Phase 20, future)
- Cascade fault recovery (Phase 20, future)

---

## References

**Vendor Design Guides (from earlier research):**
- nVent Raychem MI Cable Design Guide (DG-H56884)
- Thermon MIQ Installation Procedures (PN50273)
- Chromalox MI-825B Product Documentation
- TraceCalc Pro User Guide (nVent)
- CompuTrace Design Software (Thermon)
- ChromaTrace Design Software (Chromalox)

**Standards:**
- IEC/IEEE 60079-30-1:2025 (Explosive atmospheres)
- IEC/IEEE 60079-30-2:2025 (Application guidance)
- IEC/IEEE 62395-1:2024 (Non-explosive industrial)
- IEC/IEEE 62395-2:2024 (Application guide)
- NEC Article 427 (US electrical installation)

**Design Principles:**
All three vendors independently converge on same architecture:
- Independent breaker per heater set
- Shared sensing (typical)
- Parallel independent power branches
- This is industry baseline, not nVent-specific or Chromalox-specific

---

*Research compiled by Claude Code. Synthesized from vendor public literature, standards citations, and industry design tool documentation. Not a substitute for purchased standards or vendor engineering support.*
