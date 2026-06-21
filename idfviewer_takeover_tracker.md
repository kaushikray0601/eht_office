# IDF Viewer Takeover Tracker

Baseline reviewed on takeover:
- Latest committed AG baseline: `bd6b46b` (`feat: Enhance IDF Viewer with multi-file upload, improved UI, and robust database integration`)
- One unrelated live local edit exists in `ELECSENSE/settings.py`; avoid touching it during `idfviewer` stabilization unless explicitly needed

Tracking convention:
- `todo`: reviewed and confirmed, not started
- `in progress`: actively being fixed in the current handover
- `done`: fixed and verified in this takeover stream
- `later`: valid issue, but intentionally deferred until higher-risk items are stable

## Current Fix Order

1. `done` Parser stability: restore inherited `pipeline_ref` parsing for multi-file hierarchy, fix negative-record text slicing/continuation corruption, and filter false `Record 90` plant-to-origin outliers.
   Validation:
   - Add parser-focused tests.
   - Re-run scene statistics to confirm `Unknown Line` collapse is reduced and giant false bounds are removed.
   - Current measured result on bundled IDFs: blank `pipeline_ref` count improved from `743/767` in the previous review to `169/762`, and false `Record 90` outliers dropped from `5` bogus origin-spanning fittings to `1` short valid fitting.

2. `done` Viewer state model: unify hierarchy checkbox visibility with manual hide/show so sidebar state and scene state cannot drift apart.
   Why it matters:
   - The current left hierarchy can say an item is visible while the mesh is still hidden by the manual hide tool.
   Validation:
   - Manual hide now stores hidden logical items separately from hierarchy filters.
   - Restore/show-hidden now respects the current checkbox state instead of blindly turning every mesh back on.

3. `done` Upload ingest safety: make imports idempotent and transactional.
   Why it matters:
   - Re-uploading the same folder should not duplicate `IDFFile` and `IDFComponent` records.
   - A failed save should not leave partial data in PostgreSQL.
   Current state:
   - `services.persist_preview_scene()` uses content signatures, conflict detection, `transaction.atomic()`, duplicate cleanup, and `bulk_create()`.
   - The preview upload itself remains in-memory until the user explicitly saves IDF/PCF components.

4. `todo` Folder provenance: stop collapsing uploaded folder entries to basename-only filenames.
   Why it matters:
   - Duplicate filenames from different folders can collide and be attached to the wrong DB file row.

5. `todo` Project scoping: align `idfviewer` project selection with managed-project access rules already used elsewhere in EHT.

6. `todo` Data model hardening: stop writing the same combined bounds to every `IDFFile`, and prepare a cleaner path toward queryable geometry instead of overloading `properties` JSON forever.

7. `todo` Plot plan backend wiring: either complete persistence for `PlotPlanOverlay` end-to-end or downgrade the documentation to match the current browser-only prototype.

8. `todo` Documentation cleanup: `walkthrough.md` currently overstates what is robust/persistent/complete and should be brought back in line with the real implementation state.

9. `later` Performance work: evaluate `InstancedMesh` and more geometry batching only after parser correctness and visibility state are trustworthy.

## Notes From The Takeover Review

- The AG work added real momentum: multi-file normalization, a richer viewer shell, and the start of persistence were all the right ambitions.
- The highest-risk failures are still correctness failures, not styling failures. For EHT use, a clean wrong-looking UI is much safer than a beautiful viewer that silently groups lines under the wrong pipeline or stores duplicate plant data.
- We should keep using this file as the working punch list and update statuses after each fix step.
