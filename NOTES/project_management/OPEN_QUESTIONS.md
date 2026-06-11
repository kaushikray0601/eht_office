# Open Questions

Last updated: 2026-06-11

## Immediate Questions

1. Should the current working set be committed/checkpointed before `CC-P4`?
   - Resolved: Phase A work through `CC-P5` is committed; worktree clean at
     `46d47d5` (2026-06-11).

1a. Should the 178 unverified rows in `eht/tmp/elecEHT_Vendor.csv` (Constant
    Wattage Thermon/nVent = 91, Krus-Zapad MI = 87) be validated and added to
    the vendor catalogue?
   - Owner: KR. Until decided, the CSV must not be imported (see R-016); it
     is also missing 89 validated rows that are in the database.

1b. Should SQLite test mode be fixed (migration `0037` compatibility) or
    formally retired?
   - Owner: KR + Codex in `TEST-P1`. Retiring simplifies to one supported
     test path (PostgreSQL programmatic runner) but loses the isolated
     no-Postgres check; fixing keeps both at small migration-maintenance cost.

2. For cold-cable installation methods without validated catalogue rows, should
   the UI disable the option or allow it and report no catalogue rows?
   - Resolved in `CC-P1`: project setup shows Method E as active and Method D2
     as disabled/coming soon. B2, C, and D1 are hidden from setup for now.
     Admin/readiness and explicit unsizeable guidance remain for stored or
     catalogue-maintenance contexts.

3. When should we start a fresh chat?
   - Resolved for now: checkpoint before `CC-P4` if the user wants lower token
     cost and faster execution.

4. When will the MI worked-example comparison (R7 gate) be completed?
   - This is blocking `is_validated=True` for all MI families, meaning MI
     auto-fallback cannot fire in production until at least one family is
     validated. Owner: KR.

## Cold Cable Engineering Questions

1. How should phase slots be assigned for 3PH JB outgoing branches?
   - Resolved for `CC-P3`: infer L1/L2/L3 by fixed round-robin outgoing circuit
     index and expose the result for review only.
   - Future question: should phase slots become user-editable or inherited from
     a physical JB slot position?

2. How much of the panel/load summary should be calculated now?
   - Resolved for `CC-P4`: provide branch-based review evidence now: source
     grouping, MCB count, circuit count, load current, connected load, breaker
     distribution, and cold-cable selected/review/unsizeable/not-sized counts.
   - Future question: when formal panel objects/main breakers exist, add spare
     capacity checks and bus phase-current totals.

3. When should tracer PE-path resistance be added?
   - Requires SR braid/shield and MI sheath/armour resistance data.
   - Current result is explicitly non-conservative for earth-loop checks.

4. Should short-circuit withstand be a production gate now or advanced option later?
   - Current user preference: defer deep short-circuit sizing for now.

5. What source impedance basis should the cold-cable rebuild use?
   - Resolved 2026-06-08: use mandatory project setup field
     `EHT DB fault rating`, default 15 kA, presets 10/15/25/40/50 kA plus
     Other >= 1 kA. This is the three-phase prospective short-circuit current
     at the EHT DB busbar. Calculate
     `Z_source = V_phase / (three_phase_fault_rating_ka x 1000)`.

6. How should shared FeederCable quantities be stored and counted?
   - Resolved 2026-06-08: each branch result stores complete FeederCable +
     BranchCable evidence for traceability, but cable schedule and BOQ totals
     must deduplicate shared FeederCable material by stable feeder/group ID.

## SLD / Cable Schedule Questions

0. SLD filtered/focused view topology policy:
   - Resolved 2026-06-07: topology edits are not allowed from filtered SLD
     views. Cable length overrides and alternate tracer selection remain
     allowed.

1. What visual issue badges are most important for first SLD production polish?
   - Missing length.
   - Review-required cable.
   - Manual override.
   - Stale topology.
   - Unsizeable result.

2. Which cable schedule fields are needed first for procurement?
   - Route reference.
   - Drum tag.
   - Installation area.
   - Revision/status.
   - Checked-by/date.

3. Should topology edit impact summary be persisted or generated on demand?
   - Recommendation: start generated on demand; persist later if audit requires.

4. Combined-circuit cable re-sizing workflow:
   - Next SLD feature: combined circuits must recalculate the combined feeder
     cable size from combined current.
   - The app should warn that the prior separate feeder cable lengths are no
     longer valid and default the new combined trunk length to the highest
     length among the combined feeder cables.
   - Current direction: build this after `CC-P5`, so the warning and automatic
     recalculation use the new single-phase FeederCable/BranchCable engine.

## Future Module Questions

1. Constant Power tracer:
   - Which vendor catalogue should be the first reference?
   - What installation/selection rules are required?

2. 3D/model-routing:
   - Should IDF/PCF/IFC route length feed cold cable first, or EHT component
     placement first?
   - What export target is most valuable first: Excel schedule, SLD sync, or
     SP3D/E3D-friendly data?
