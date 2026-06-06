# Open Questions

Last updated: 2026-06-07

## Immediate Questions

1. Should the current large working set be committed/checkpointed before `CC-P1`?
   - Recommendation: yes, after `CC-P0` tests pass.

2. For cold-cable installation methods without validated catalogue rows, should
   the UI disable the option or allow it and report no catalogue rows?
   - Recommendation: keep option visible but show readiness status and clear
     review guidance. Do not hide engineering choices just because the catalogue
     is incomplete.

3. When should we start a fresh chat?
   - Resolved for now: continue through `CC-P0`; start a fresh chat for `CC-P1`
     if the user wants lower token cost and faster execution.

4. When will the MI worked-example comparison (R7 gate) be completed?
   - This is blocking `is_validated=True` for all MI families, meaning MI
     auto-fallback cannot fire in production until at least one family is
     validated. Owner: KR.

## Cold Cable Engineering Questions

1. How should phase slots be assigned for 3PH JB outgoing branches?
   - Fixed round-robin by outgoing order?
   - User-editable phase assignment?
   - Inherited from physical JB slot position?
   - Current basis: phase current is assumed balanced for all outgoing circuits
     as stated in `CODEX_MEMORY.md`. `CC-P3` adds visibility only, not automatic
     rebalancing.

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

## Future Module Questions

1. Constant Power tracer:
   - Which vendor catalogue should be the first reference?
   - What installation/selection rules are required?

2. 3D/model-routing:
   - Should IDF/PCF/IFC route length feed cold cable first, or EHT component
     placement first?
   - What export target is most valuable first: Excel schedule, SLD sync, or
     SP3D/E3D-friendly data?
