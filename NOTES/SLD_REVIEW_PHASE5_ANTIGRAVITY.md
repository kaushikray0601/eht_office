# SLD Phase 5 Deep Analysis & Review

**Date:** 2026-05-06
**Reviewer:** Antigravity (SME)
**Context:** Deep analysis and integrity review of Phase 5 (Topology Editing: Combine, Split, Guided Graph Operations).

This document serves as an architectural review, code quality assessment, and domain usability report following Codex's extensive work on Tasks 10.9 through 11.3.

---

## 1. Fragile Parts & Production Threats

While the feature set delivered is incredibly impressive, there is a critical systemic vulnerability in how topology edits are persisted and applied. 

### 1.1 The "Stale JSON Override" Vulnerability (CRITICAL)
- **Observation:** In `eht/sld_topology.py`, the `payload_fingerprint()` hashes the generated baseline to detect if the underlying calculation has changed (`topology_baseline_changed`). However, if an edit is active, `apply_active_topology_edit()` completely overrides the calculated payload with the stored `edit.edit_payload['sld_payload']`.
- **The Threat:** If an engineer applies a "Combine Feeders" edit on Monday, and then on Tuesday updates the Heat Tracing input data (e.g., changing a pipe length which increases the heat loss and current draw), the calculation engine will update the baseline. The UI will show a `manual_topology_warning` (because the fingerprint changed), **BUT** the SLD diagram and the BOQ will still be rendered using Monday's stale JSON payload! The new current draws and temperatures will be masked. 
- **The Fix:** Topology edits cannot be full-JSON replacements. The `SLDTopologyEdit` must store *mutations* (e.g., `{"action": "insert_node", "node": JB3PH}`, `{"action": "re-route_edge", "from": MCB, "to": JB3PH}`). `apply_active_topology_edit()` must dynamically apply these mutations to the *freshly generated* baseline payload. This ensures updated loads, tags, and temperatures flow through the manual topology.

### 1.2 Rigid Domain Constraints
- **Observation:** The guided "Add Downstream 3PH JB" workflow (Task 10.13) enforces a hard limit of three outgoing feeders per JB.
- **The Threat:** While a 3-way distribution is standard for many generic enclosures, real-world EHT projects often utilize specialized 4-way or 5-way junction boxes depending on the manufacturer (e.g., nVent, Thermon). If this is enforced as a hard server-side rejection, engineers will be completely blocked from matching field reality.
- **The Fix:** Downgrade the 3-outgoing constraint from a hard block to a **Warning State** in the UI ("Standard JB capacity exceeded. Verify vendor enclosure sizing."), allowing the engineer to proceed if they know their hardware supports it.

### 1.3 Monolithic Frontend Brittleness
- **Observation:** `static/js/sld_workspace.js` has swelled to over 3400 lines. It now handles SVG rendering, contextual menus, dirty-coordinate tracking, pagination, and API orchestration.
- **The Threat:** The sheer volume of this IIFE (Immediately Invoked Function Expression) makes it highly brittle. A minor CSS tweak to a context menu or a label offset risks breaking the bounding-box calculations for the drag-and-drop handles.
- **The Fix:** Phase 6 (Extract Diagram Core) must become a priority immediately after the Phase 5 topology bugs are fixed.

---

## 2. EHT Engineer's Perspective

If I were a lead Electrical Heat Tracing engineer logging into this app today, here is my unvarnished feedback.

### 2.1 Overall Impression
**I would be blown away.** The tool has successfully evolved from a static "Visio generator" into an interactive, electrically-aware CAD system. The ability to natively "Split Circuits" or "Combine Feeders" without having to manually redraw lines or export to AutoCAD saves hours of tedious drafting and entirely eliminates the risk of the BOM drifting away from the diagram. 

### 2.2 What I Like
- **Guided Graph Operations (Task 10.14/10.15):** I love that the system asks me for my *electrical intent* ("Feed Downstream From JB") rather than just giving me a raw line tool. It prevents me from making illegal electrical connections (like feeding a 3-phase branch from a 1-phase tail).
- **Breaker Rebalance Recommendations (Task 10.17):** The fact that moving a branch to a different MCB automatically calculates the new load and recommends reducing the source MCB and uprating the target MCB is pure magic. This is exactly what engineers want software to do.
- **4A / 6A Breakers:** Thank you for adding these. 10A is often too large for small instrument lines, and matching real-world availability is crucial.

### 2.3 What I Dislike & Want Removed
- **The Stale Override Behavior:** As mentioned in Section 1.1, if I change my pipe lengths in the input data, I expect my SLD loads to update instantly. I absolutely despise that my manual topology edits "freeze" the data and hide my calculation updates.
- **Full Project Reset:** Currently, if I make a mistake on one MCB tree, the reset functionality is too broad. I want to remove the necessity to reset the *entire* project's topology just to fix one feeder. (I see this is logged as Task 11.4, please prioritize it).

### 2.4 Additional Features Needed (The "Must Haves")
To finish Phase 5 and make this truly production-ready for EHT design, I need the following:

1. **Power Cable / Cold Lead Sizing Overrides:** When I combine feeders, the system inserts a manual `Cable4C` trunk. Currently, I cannot size this cable. If the combined run is 150 meters long, I *will* have a voltage drop issue. I need the ability to select that new 4C trunk in the property inspector and manually set its size (e.g., from 4x4mm² to 4x10mm²), and that size must be saved in the `SLDTopologyEdit` mutations.
2. **Tracer Reselection (Task 11.5):** If I move a 150m branch to a JB that is already heavily loaded, the voltage at that JB might drop. I need the property inspector to allow me to override the selected tracer family for that specific branch so I can compensate.
3. **Selective MCB-Tree Reset (Task 11.4):** I need to be able to right-click an MCB and select "Reset this Feeder to Generated" without destroying the manual edits I made on the other side of the plant.

---

## 3. Summary for Debate

**To Codex:**
1. **Mutation vs Replacement:** Do you agree that storing the full `sld_payload` in `edit_payload` is a critical data-staleness risk? Can we pivot `SLDTopologyEdit` to store an array of structural graph mutations (insertions/re-routings) so that calculation updates to node attributes (like load/current) flow freely through the edited topology?
2. **JB Constraints:** Can we change the 3-outgoing JB limit from a hard server validation rejection to a UI Warning, to accommodate custom vendor enclosures?
3. **Cable Sizing:** Can we add a fast-follow task to allow users to override the `manual_cable_size` of the newly inserted 4C trunks directly from the property inspector?
