# Open Questions

Last updated: 2026-06-07

## Immediate Questions

1. Should the current working set be committed/checkpointed before `CC-P4`?
   - Recommendation: yes, now that `CC-P3` and the SLD regression rerun passed.

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
   - Basic breaker/load/current counts?
   - Phase current imbalance?
   - Panel spare capacity?

3. When should tracer PE-path resistance be added?
   - Requires SR braid/shield and MI sheath/armour resistance data.
   - Current result is explicitly non-conservative for earth-loop checks.

4. Should short-circuit withstand be a production gate now or advanced option later?
   - Current user preference: defer deep short-circuit sizing for now.

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
   - Decision still needed: should the combine apply be blocked until the user
     explicitly accepts/reviews this default length, or is a warning plus
     editable default enough for the first production pass?

## Future Module Questions

1. Constant Power tracer:
   - Which vendor catalogue should be the first reference?
   - What installation/selection rules are required?

2. 3D/model-routing:
   - Should IDF/PCF/IFC route length feed cold cable first, or EHT component
     placement first?
   - What export target is most valuable first: Excel schedule, SLD sync, or
     SP3D/E3D-friendly data?
