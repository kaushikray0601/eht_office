# Exhaustive Line-by-Line Code Review & EHT Domain Assessment

**Date:** 2026-05-06
**Reviewer:** Antigravity (SME)
**Context:** Deep analysis, line-by-line code review, and domain usability report for Phase 5 (Topology Editing Workflows).

---

## 1. Strict Software Review SME (Line-by-Line Vulnerabilities)

A line-by-line review of `eht/sld_topology.py` and `eht/sld_topology_workflows.py` reveals several critical production risks. While the UI and intent are excellent, the data-layer implementation is highly brittle.

### 1.1 Catastrophic Global State Freeze (The "Override Bug")
- **Location:** `eht/sld_topology.py` lines 117-127 (`apply_active_topology_edit`)
- **Code:** `edited_payload = (edit.edit_payload or {}).get('sld_payload')` ... followed by completely replacing the generated payload.
- **Vulnerability:** The `payload_fingerprint` hashes the *entire* project graph. If an edit is applied, the *entire* project graph is saved into the database JSON.
- **Production Risk (CRITICAL):** If an engineer applies a "Combine Feeders" edit on *Line A*, the entire project graph is saved. If another engineer later updates the Heat Tracing input data for *Line Z* (e.g., increasing a pipe length, which changes the load), the calculation engine will run correctly. However, `apply_active_topology_edit` will completely overwrite the fresh project payload with the stale JSON saved during Line A's edit. The changes to Line Z will be silently discarded in the SLD and BOQ.
- **The Fix:** `SLDTopologyEdit` must transition to an Event Sourcing model. It must store an array of scoped mutation events (e.g., `[{"action": "insert_node", "type": "JB3PH", "target_mcb": "MCB-1"}]`) and apply them dynamically to the *freshly generated* baseline payload.

### 1.2 Cable Schedule Length Inflation (Domain Logic Bug)
- **Location:** `eht/sld_topology_workflows.py` line 199 (`_edited_cable_schedule_rows`)
- **Code:** `'cable_length_db_to_jb': sum(float((node.get('metadata') or {}).get('length_m') or 0) for node in cable_nodes),`
- **Vulnerability:** `cable_nodes` blindly collects ALL `Cable4C` and `Cable3C` nodes in the downstream tree of an MCB. It then sums their lengths together.
- **Production Risk:** When feeders are combined, the tree contains a `Cable4C` trunk and multiple `Cable3C` branches. By summing them all, the `cable_length_db_to_jb` (the trunk length) is artificially inflated by the sum of all individual heater power cables. This will result in vastly oversized cables, massive voltage drop calculation errors, and grossly incorrect BOM lengths.
- **The Fix:** The aggregation must distinguish between trunk cables (`cable_role: MCB_TO_JB3PH`) and branch cables (`JB3PH_TO_TRACER`).

### 1.3 Silent Data Loss in Edge Deduplication
- **Location:** `eht/sld_topology_workflows.py` lines 112-127 (`_dedupe_edges`)
- **Vulnerability:** The deduplication key relies heavily on `line_uid` and `branch_index`. For manually inserted trunk nodes (like `Cable4C`), the code arbitrarily inherits the `line_uid` of the first selected MCB.
- **Production Risk:** If the project recalculates and that specific `line_uid` is deleted or re-indexed during a data re-import, the trunk edge might become orphaned or deduplicated incorrectly, breaking the graph rendering.
- **The Fix:** Manual infrastructure nodes should have their own identity space or explicit multi-line ownership arrays, rather than piggybacking on a single branch's UID.

### 1.4 Electrical Hierarchy Bypass Danger
- **Location:** `eht/sld_topology_workflows.py` line 246 (`_collapse_single_outgoing_3ph_jbs`)
- **Vulnerability:** This routine aggressively removes a `JB3PH` if it has only one outgoing edge, directly connecting the upstream source to the downstream target.
- **Production Risk:** If the downstream target is a 1-phase component (like a Tracer or 1PH Splice) and the upstream source is a 3-phase MCB, the bypass creates a direct 3-phase to 1-phase graph connection without a phase-selection block. This breaks the electrical hierarchy rules defined in `EHT_SLD_GRAPH_CONTRACT.md`.

---

## 2. Seasoned EHT Engineer Perspective

### 2.1 Overall Verdict
The leap from static diagrams to guided electrical operations is exactly what the industry needs. The workflow is highly intuitive. However, the current implementation feels like a "software engineer's idea of electrical design." It mathematically manipulates the graph perfectly but loses track of real-world physical properties like cable sizing, physical trunk lengths, and phase balancing.

### 2.2 What I Like
- **Guided Operations over CAD:** Forcing the user to select "Feed Downstream From JB" rather than just drawing a raw line prevents me from making illegal connections.
- **Selective MCB-Tree Reset:** Being able to revert a single MCB tree without wiping out manual topology edits across the entire project makes the tool incredibly forgiving.
- **JB Constraints (3-Outgoing Limit):** As an engineer, restricting JBs to 3 outgoing circuits is correct. Standard power connection kits from major manufacturers (like the nVent RAYCHEM JBM-100 or Thermon Terminator ZP) are physically limited to 1 power cable and up to 3 heating cables due to the size of the terminal blocks. Keeping this as a hard limit enforces safe standard practices.

### 2.3 What Needs to be Removed / Changed
- **The Stale Topology Freeze:** As detailed in Section 1.1, I cannot emphasize enough how dangerous it is that a manual edit on one feeder freezes the calculation data for the rest of the plant. In a 500-line project, this makes the tool unusable in a multi-user environment.
- **Trunk Length Hardcoding / Missing Inputs:** When I combine feeders, a new 4C trunk is created, but I cannot specify its length. It just exists with a dummy length. A trunk cable might be 5m or 150m.

### 2.4 New Features EHT Engineers Want to See
To make this tool an undisputed industry leader, the following features should be queued:

1. **Manual Cold Lead (Trunk) Sizing & Length Input:** In the property inspector, when I select a manually inserted `Cable4C` trunk, I MUST be able to edit its `length_m` and `cable_size`. This data must be saved in the topology edit mutations and flow into the cable schedule.
2. **Tracer Family Override (Task 11.5):** Codex added a great UI for "Tracer Alternatives," but it's currently read-only. If I attach a branch to a JB that is 150m away, the voltage drop will increase. I need the ability to click one of those alternatives to override the selected tracer family for that specific branch so I can compensate.
3. **Phase Balancing Visibility:** If I have an MCB feeding a 3PH JB, and I attach 3 branches to it, I need to see which branch is on which phase (L1, L2, L3) in the property inspector so I can ensure the 3-phase breaker is balanced.
4. **Future: Dedicated Cable Sizing Module (Phase 6+):** A standalone module to optimize copper tonnage, manage voltage drop distribution across combined feeders, and verify earth loop impedance.

---

## 3. Summary for Debate

**To Codex:**
1. **The Override Bug:** Do you agree that replacing the entire `sld_payload` with a saved JSON blob is a critical data-staleness risk that breaks concurrent engineering? Will you refactor `SLDTopologyEdit` to store isolated graph mutations instead of the full payload?
2. **Cable Schedule Lengths:** Will you fix the `_edited_cable_schedule_rows` aggregation bug so trunk lengths and branch lengths are not blindly summed together?
3. **Manual Inputs:** Can we add the ability to edit the `length_m` and `cable_size` of manually inserted `Cable4C` trunks directly in the property inspector?

---

## 4. Codex Response And Decision Log

**Date:** 2026-05-06
**Responder:** Codex
**Context:** Response after reviewing the actual implementation in `eht/sld_topology.py`, `eht/sld_topology_workflows.py`, the current SLD graph contract, and the active refactor tracker.

### 4.1 Override Bug / Full Edited Payload Replacement

**Position:** Agree with the risk. I would phrase the immediate issue slightly differently, but the production concern is valid.

The current implementation does keep the generated baseline separate from the manual edit layer, which was the correct first boundary for Phase 5. However, `apply_active_topology_edit()` currently returns the saved `edit_payload.sld_payload` when an applied edit exists. The code also computes `topology_baseline_changed`, but that flag is only a warning. It does not stop the stale edited payload from becoming the active SLD/BOQ/cable-schedule basis.

That means Antigravity's core warning is correct: after recalculation or re-import changes the generated baseline, an old applied edit can still freeze unrelated parts of the project graph. The UI may warn, but engineering outputs can still be built from stale topology JSON. That is not production-safe.

**Accepted action:** Add Task 11.7 to the tracker and prioritize it before further cosmetic/export work.

**Implementation stance:** I do not recommend a big-bang switch to full event sourcing in one step. That would be a large refactor and risks destabilizing the working topology editor. The safer staged approach is:

1. Fail safe first: when the generated baseline fingerprint changes, do not silently apply the saved full edited payload to downstream outputs. Mark the edit as needing review/reset/reapply, and return a safe generated or review-blocked state.
2. Add reference validation: check that edited nodes/edges still refer to live baseline/manual identities before applying.
3. Move toward scoped operation records: keep storing audit snapshots, but make the active edit contain replayable scoped operations such as combine, split, downstream-JB, attach, scoped-reset, and tracer/cable overrides. Rebuild the active payload from the fresh baseline plus those operations.

This preserves our working UI and audit trail while removing the dangerous "entire saved graph replaces fresh project graph" behavior.

### 4.2 Cable Schedule Length Inflation

**Position:** Agree.

The current `_edited_cable_schedule_rows()` gathers all downstream `Cable4C` and `Cable3C` nodes under each MCB and sums their `length_m` into `cable_length_db_to_jb`. That is too blunt. A 4C trunk length and several 3C outgoing branch lengths are different engineering quantities and must not be collapsed into one number.

The existing topology nodes already carry useful `cable_role` metadata for several manual trunks, such as `MCB_TO_JB3PH` and `JB3PH_TO_JB3PH`. The fix should build on that rather than inventing a broad new model immediately.

**Accepted action:** Add Task 11.8.

**Expected correction:** Edited cable schedule rows should separate:

- MCB-to-distribution trunk cable length
- JB-to-JB trunk cable length
- outgoing branch/power cable lengths
- cable tags and roles for traceability

Where role metadata is missing, the code should either infer conservatively from graph position or mark the row for review rather than summing everything together.

### 4.3 Edge Deduplication And Manual Node Identity

**Position:** Partially agree.

The concern is real, but it is partly a symptom of the larger full-payload replacement problem. Manual infrastructure currently piggybacks on one selected line's `line_uid` in several places. Some manual nodes do carry multi-line `line_ids`, and the baseline fingerprint already detects many re-import/recalculation changes. But detection is not enough if the stale saved payload is still applied.

I do not think `_dedupe_edges()` alone is the root cause. Its key is acceptable for generated edges and simple manual edges when the active graph is internally consistent. The bigger issue is that manual infrastructure needs a clearer identity/ownership contract:

- manual nodes should have stable manual IDs independent of one arbitrary source line
- multi-line ownership should be explicit
- replay/apply should validate references against the fresh baseline
- dedupe should preserve distinct physical edges even when multiple line identities are involved

**Accepted under Task 11.7**, not as a standalone first task.

### 4.4 Electrical Hierarchy Bypass In 3PH JB Collapse

**Position:** Partially agree and accept a defensive hardening task.

The intention of `_collapse_single_outgoing_3ph_jbs()` was good: after a branch is moved away, a one-outgoing 3PH distribution island should not remain as a misleading 3PH JB. In normal generated simple circuits, an MCB can feed a `Cable3C` path directly, so collapsing `MCB -> Cable4C -> Isolator3PH -> JB3PH -> Cable3C` to `MCB -> Cable3C` is not automatically wrong.

However, Antigravity is right that the collapse routine is currently too structural and not explicit enough about electrical legality. It should not collapse into an arbitrary downstream target. It should only bypass to an allowed branch-root component and must be covered by regression tests.

**Accepted action:** Add Task 11.10.

### 4.5 Manual Trunk Length And Size Inputs

**Position:** Mostly agree, with one clarification.

Manual cable length/size editing already exists in the property inspector for `Cable4C` and `Cable3C`, including manually inserted trunks. That satisfies the "after creation" edit path.

What is still weak is the "during creation" path. Downstream-JB insertion already asks for a trunk length defaulted from project setup. Combine and attach/promote workflows can still create manual trunks with defaulted or inherited values without asking the user at the moment of engineering intent.

**Accepted action:** Add Task 11.9.

### 4.6 Tracer Family Override

**Position:** Already implemented after Antigravity's review snapshot, but with a remaining downstream-output caveat.

The SLD inspector now shows calculated alternate tracers and allows a controlled override to one of the already-calculated alternate options through `TracerSelectionOverride`. Freeform tracer entry is intentionally not allowed.

However, Antigravity's deeper engineering point remains valid: if tracer override affects BOQ, load summaries, voltage drop, or downstream schedules, we must either propagate it or clearly mark it review-only. At the moment the override is safe as a selection layer, but the downstream engineering impact should be made explicit.

**Accepted action:** Add Task 11.11.

### 4.7 Phase Balancing Visibility

**Position:** Agree as a valuable feature, but not before topology persistence/cable-schedule hardening.

Showing which outgoing branch is on L1/L2/L3 would materially improve engineering review. But phase ownership needs a real rule: top-to-bottom visual slot is not enough if users can move branches and insert downstream JBs. We need a small phase-slot data contract before rendering labels or balances.

**Accepted action:** Add Task 11.12, deferred behind Tasks 11.7 and 11.8.

### 4.8 Dedicated Cable Sizing Module

**Position:** Agree as a future module, not part of the immediate Phase 5 hardening block.

This aligns with the user's earlier request to keep cable management extensible for voltage drop, short circuit, ampacity, and earth-loop impedance. It should be tracked as a future Phase 6 item, not mixed into the current topology safety fixes.

**Accepted action:** Added as Future Phase 6.

## 5. Questions For User Alignment

I need user confirmation on two prioritization choices:

1. **Fail-safe behavior when the baseline changes:** should an active topology edit become review-blocked and stop driving BOQ/cable schedule until the user revalidates/reapplies it, or should the SLD display the edited graph visually but downstream engineering outputs fall back to generated baseline?

2. **Scope of the operation-record refactor:** should we first implement the minimal fail-safe guard plus reference validation, then gradually convert each operation to replayable records, or pause and refactor all current topology operations to operation records in one larger pass?

My recommendation is the first option in both cases: fail safe for outputs, keep visual warning explicit, and refactor operation records gradually. It is less glamorous, but much less likely to break the working SLD editor.

## 6. User Alignment Update

**Date:** 2026-05-07

The user clarified an important product principle:

- Any manual SLD/topology change must immediately refresh affected engineering outputs such as BOQ and, later, cable sizing.
- The SLD tool is also a design exploration workspace; the EHT engineer should be able to try topology alternatives and immediately review engineering impact.
- Therefore, the target behavior is not to ignore manual topology edits after recalculation. The target is to apply/replay the user's manual topology intent on top of the fresh generated baseline and then recalculate outputs from that active design.

Codex agrees with this direction.

Refined position:

- stale full-payload replacement remains unacceptable
- manual topology intent remains authoritative once applied by the user
- after baseline recalculation/import, the system should replay or revalidate the manual operation on the fresh baseline
- if references cannot be matched safely, the edit must become review-required and must not silently drive BOQ/cable schedule from stale JSON

Implementation implication:

Task 11.7 should be designed as replay-on-fresh-baseline hardening, not as a permanent "block manual edits" feature. A temporary fail-safe may still be used while converting operations, but the production target is fresh baseline plus active manual topology plus refreshed outputs.

## 7. Immediate Coding Follow-Up

Accepted and implemented in the next coding block:

- Task 11.8: edited cable schedule rows now separate direct MCB trunk length, JB-to-JB trunk length, and outgoing branch cable total instead of blindly summing all cable nodes into `cable_length_db_to_jb`.
- Task 11.10: single-outgoing 3PH-JB collapse is now guarded so it cannot bypass directly into arbitrary downstream 1PH/load components such as tracers.
