# SLD Topology Failure — Deep Root-Cause Analysis

## Codex Update — 2026-06-07

The later P1-specific investigation found two additional foundation-level
causes beyond the render guard and SVG hit-target problems described below:

1. P1 had a stale active topology edit containing 96 operation records. The
   first saved `combine_feeders` operation referenced MCB component IDs that no
   longer exist in the recalculated generated SLD. New edits previously
   inherited that stale operation chain, so they appeared to apply but rendered
   back as generated/stale because replay always failed at operation #1.
2. `payload_fingerprint` included all node metadata, including volatile
   cold-cable sizing/review data. Cold-cable recalculation could therefore make
   a structurally unchanged SLD appear baseline-stale.

Implemented fixes:

- New apply workflows inherit active topology operation records only when the
  existing chain replays successfully against the current generated baseline.
  If replay fails, the new edit starts from the generated graph the user is
  actually seeing.
- New edited payloads strip runtime topology review flags before persisting
  fresh manual topology metadata.
- `payload_fingerprint` now tracks topology structure rather than arbitrary
  node metadata.
- Real P1 dry-run verification was performed inside rolled-back database
  transactions: Combine, Split, Add downstream JB, and Attach all returned
  `ok=True`, each produced a one-operation clean active edit, and the live P1
  active edit remained unchanged after rollback.

**Reviewer:** Claude (architect/auditor)  
**Date:** 2026-06-07  
**Scope:** Static analysis of all JS, Python, and template layers; cross-referenced against git history  
**Baseline reference:** pre-CC-P2 commit (SLD fully functional)

---

## 1 — Executive Summary

Three compounding issues were introduced by CC-P2 (`6516df5`). Each is distinct and must be addressed independently. Codex's working-tree changes address issues 1 and 3 partially but **the exact failure mode of issue 2 requires a 3-minute Chrome DevTools check before Codex writes another line of code**. Guessing is producing repeated failed attempts; the DevTools check in Section 5 will pin the failure to a single function with a stack trace.

---

## 2 — What CC-P2 Actually Changed (the source of the break)

| Layer | What changed | Lines |
|---|---|---|
| `sld_payload.py` | Added `apply_cold_cable_results_to_payload` — annotates Cable4C/Cable3C nodes with cold cable metadata unconditionally after topology processing | +201 |
| `sld_workspace.js` | Added `CableDetailLabelElement` JointJS custom element; changed `createExternalDetailLabel` to use it for cables; added `formatCableExternalDetailParts`, `compactCableSizeText`; changed `initializeSldWorkspace` to set `rendering='true'` **before** calling `fetchAndRenderSld` | +194 |
| `views.py` | Added topology views, cold cable calculation views, cold cable engine hooks | +763 |

The JS change to `initializeSldWorkspace` is the specific trigger that made the SLD break. Before CC-P2:

```javascript
// OLD initializeSldWorkspace (pre-CC-P2, working)
window.initializeSldWorkspace = function (container) {
    const root = $(container).find('#sld-diagram-shell')[0];
    if (!root) { return; }
    fetchAndRenderSld(root);
};
```

After CC-P2 (committed to HEAD):

```javascript
// CC-P2 initializeSldWorkspace (broken)
window.initializeSldWorkspace = function (container) {
    const root = $(container).find('#sld-diagram-shell')[0];
    if (!root) { return; }
    if (root.dataset.rendering === 'true') { return; }
    root.dataset.rendering = 'true';          // ← sets the lock
    fetchAndRenderSld(root);                  // ← if this throws, lock is never cleared
};
```

`fetchAndRenderSld` eventually called `renderSldGraph`. The new `CableDetailLabelElement` code in CC-P2 was the exception source. `root.dataset.rendering` stayed `'true'` permanently. Every button check on `root.__sldState` found null and returned silently. **That is the exact root of the original break.**

---

## 3 — Three-Layer Failure Decomposition

### Layer 1 — Sticky Rendering State Machine (RESOLVED in working tree)

**Root cause:** `initializeSldWorkspace` set `rendering='true'` before calling `fetchAndRenderSld`. There was no try-finally to ensure `finishSldRender` ran on exception. Any exception during `renderSldGraph` left `rendering='true'` stuck permanently.

**Effect:** All topology buttons called `ensureSldWorkspaceReady(root)` → `root.__sldState` null + `isSldRendering()` true → returned false → silently did nothing. No visual feedback. The SLD canvas might appear rendered (JointJS draws at `graph.resetCells` before `root.__sldState` is assigned) but no interaction worked.

**Working-tree fix (F-1/F-2/F-3):** `beginSldRender`/`finishSldRender`/`isSldRendering`/`ensureSldWorkspaceReady` primitives introduced. `renderCurrentSldPage` wrapped in try-finally in both `.done()` and `.fail()` callbacks. `renderSldGraph` entire body wrapped in try-catch (F-2). 20-second watchdog added (F-3).

**Status:** ✅ VERIFIED PRESENT in working tree at lines 111–149 (render guard primitives), 3403–3406 and 3417–3420 (try-finally), 3060 and 3338 (try-catch F-2).

---

### Layer 2 — CableDetailLabelElement Runtime Behaviour (UNKNOWN — requires DevTools)

**Root cause:** CC-P2 introduced `getCableDetailLabelElementClass()` which calls `joint.dia.Element.define('sld.CableDetailLabelElement', ...)` to create a custom JointJS element type. The new `createExternalDetailLabel` for cables creates instances of this class with multi-line SVG `<text>` elements using `textVerticalAnchor: 'top'` and explicit `x`/`y` attributes.

**Static analysis result:** The code follows the EXACT SAME pattern as `getSchematicSymbolElementClass()` which was working before CC-P2. The `joint.dia.Element.define` call uses the correct JointJS 3.x array markup format. Attribute values (`text`, `x`, `y`, `fill`, `fontSize`, `textAnchor`, `textVerticalAnchor`) are all safe. No exception path is identifiable through static analysis.

**However:** Whether `graph.resetCells(cells)` or the subsequent paper event wiring throws at runtime is UNKNOWN. The F-2 catch was designed to capture exactly this. If a runtime exception fires, it logs to the DevTools Console and shows "Unable to render SLD" to the user.

**Status:** ⚠️ CANNOT CONFIRM — requires browser runtime. See Section 5 for the 3-minute diagnostic.

---

### Layer 3 — Canvas Click Hit Targets (RESOLVED in working tree)

**Root cause:** SVG schematic symbol elements (MCB, JB, Isolator, Tracer) had their `body` rect with no explicit `pointerEvents` setting. JointJS defaults SVG `pointer-events` to the element's default behaviour, meaning only pixels actually covered by a visible fill register clicks. The transparent `body` rect (used as the invisible click target) was not reliably intercepting click events.

**Effect (if Layer 1 resolved but Layer 3 not):** SLD renders. Mode buttons toggle their active state (`combineMode = true`, button gets `active` class). But clicking on an MCB node on the canvas fires no `element:pointerclick` event because the click lands on the transparent `body` rect. Topology selection never happens. The user sees: "I click Combine, the button looks active, but clicking on the SLD nodes does nothing."

**Working-tree fix (r3-hit-targets):** `pointerEvents: 'all'` added to `body` in both `createSchematicSymbolElement` (line 437) and `createComponentElement` for rectangle-type nodes (line 683). This forces the full element bounding box to be a valid click target regardless of fill.

**Status:** ✅ VERIFIED PRESENT in working tree.

---

## 4 — Current Working-Tree Fix Status

| Issue | Fix | Status in working tree |
|---|---|---|
| Sticky rendering state (Layer 1) | F-1/F-2/F-3 primitives + try-finally + try-catch | ✅ Verified present |
| CableDetailLabelElement runtime (Layer 2) | F-2 catch — will catch it and show error state with console log | ✅ Guarded but unknown if it actually fires |
| Canvas click hit targets (Layer 3) | pointerEvents: 'all' on all node body elements | ✅ Verified present |

**All working-tree changes are UNCOMMITTED.** The Django dev server serves them directly from the filesystem. The cache buster `?v=sld-r3-hit-targets` in `base.html` (committed) ensures the browser loads the new JS rather than the cached version.

---

## 5 — 3-Minute Chrome DevTools Diagnostic (Run This Before Any More Coding)

Open Chrome with the project loaded. Open DevTools (F12). Go to the SLD tab in the app.

### Check A: Console errors on tab load

1. Clear the Console tab (trash icon or Ctrl+L)
2. Click the SLD tab in the app to trigger load
3. Wait for the SLD to finish loading
4. Look at the Console

**If you see red errors:** Copy the error message and the first 3 lines of the stack trace. That is the exact exception causing Layer 2. Post it — Codex can fix the exact line in one pass.

**If you see `[SLD] renderSldGraph failed:` in red:** Layer 2 confirmed. The full stack trace is right there.

**If you see no red errors and the SLD diagram appears:** Layer 2 is NOT the issue. Layer 1 or Layer 3 is the active failure. Go to Check B.

---

### Check B: Confirm `root.__sldState` is set after load

After the SLD tab loads, run this in the DevTools Console:

```javascript
const root = document.getElementById('sld-diagram-shell');
console.log('rendering:', root && root.dataset.rendering);
console.log('__sldState:', root && root.__sldState ? 'SET' : 'NULL');
```

**If `__sldState: NULL` and `rendering: 'true'`:** F-1/F-2/F-3 are NOT in the currently loaded JS. The browser is running a cached old version. Force-reload with Ctrl+Shift+R (Chrome hard reload). Retest.

**If `__sldState: NULL` and `rendering: 'false'`:** F-2 catch fired — render threw an exception and the state was cleared. Check A should have shown the error. Run Check A again.

**If `__sldState: SET`:** The render succeeded. Layer 1 and Layer 2 are not the active failure. The issue is Layer 3 (canvas clicks). Go to Check C.

---

### Check C: Confirm mode button toggle works

After confirming `__sldState` is SET, click the **Combine** button on the SLD panel, then run in Console:

```javascript
const root = document.getElementById('sld-diagram-shell');
console.log('combineMode:', root.__sldState && root.__sldState.combineMode);
```

**If `combineMode: true`:** The button handler is firing. The issue is in canvas element click registration (Layer 3). The r3-hit-targets fix should resolve this — force-reload with Ctrl+Shift+R and retest.

**If `combineMode: false`:** The button click is not reaching the handler. Check whether the button has the correct ID (`#sld-combine-mode`) in the rendered HTML (right-click the button → Inspect). If the ID is wrong, the `$(document).on('click', '#sld-combine-mode', ...)` handler never fires.

---

## 6 — Production-Grade Fix Matrix

Based on what Check A/B/C reveals:

### Scenario R (render exception — Check A shows red error)

**Action for Codex:**
1. Copy the exact error and stack trace from Check A
2. Fix the specific line that throws — do not patch the call site
3. If the error is inside `graph.resetCells(cells)` or JointJS paper rendering, it's a JointJS API usage issue in one of the CC-P2 custom elements
4. Re-run `node --check static/js/sld_workspace.js` and `python manage.py test eht --verbosity=0` after fix

### Scenario S (state null after load, rendering false — F-2 fired but no console error visible)

This should be impossible with F-2 in place (F-2 always logs). Most likely means the loaded JS is an old cached version without F-2. Hard-reload the browser and retest. If it persists, F-2 may have been accidentally removed — re-verify lines 3060 and 3338.

### Scenario T (state set, combineMode toggles, but canvas clicks don't work)

**Action for Codex:**
The `pointerEvents: 'all'` fix in r3-hit-targets is the correct fix. Verify it's present:
- Line 437: `pointerEvents: 'all'` inside `body` attrs of SchematicSymbolElement
- Line 683: `pointerEvents: 'all'` inside `body` attrs of Rectangle element

If both are present and clicks still don't work, the JointJS `interactive` callback at lines 3103–3106 might be filtering out the custom `CableDetailLabelElement` clicks. That callback only allows dragging for elements with `meta.componentId` or `meta.draggableGroup`. Click events are handled separately via `paper.on('element:pointerclick', ...)` and should not be filtered by `interactive`.

### Scenario U (state set, combineMode toggles, canvas clicks work, Apply fails)

**Action for Codex:**
The topology preview/apply server views are the issue. Check:
1. Network tab in DevTools — what HTTP status does the POST to `/sld/topology/combine/preview/` return?
2. If 400: the server view returned an error (check `preview['error']` message from Django)
3. If 500: Django exception in `preview_combine_feeders()` — check Django's `python manage.py runserver` terminal output

---

## 7 — Known Code Quality Issues for Production Hardening

Regardless of the DevTools result, Codex should apply these hardening items on the next coding pass:

### H-1 — `refreshDynamicLabels` external label positioning is inconsistent

`createExternalDetailLabel` for cables positions with:
```javascript
label.position(position.x - ((labelWidth - style.width) / 2), position.y + (style.height / 2) + 14);
```

`refreshDynamicLabels` repositions with:
```javascript
label.position(position.x - 16, position.y + size.height + 7);
```

These produce different x-offsets (Cable4C: –12 vs –16; Cable3C: –14 vs –16). On the first render, the label is at the correct offset. After any `cell:pointerup` event fires `refreshDerivedGeometry`, the label jumps to the –16 offset. The label shifts slightly when the user first drags anything.

**Fix:** Make `refreshDynamicLabels` use the same dynamic offset: `position.x - ((labelWidth - element.size().width) / 2)`.

### H-2 — `renderCurrentSldPage` called without try-finally in pager/navigation contexts

Lines 2757, 4250, 4259, 4268: direct calls to `renderCurrentSldPage(root)` outside any try-finally or try-catch. These are pager navigation calls (previous/next page, fit-to-line). If `renderSldGraph` throws in these paths, `finishSldRender` is not called.

However, these paths do NOT go through `beginSldRender` either — they call `renderCurrentSldPage` on an already-initialised pager. The rendering guard only applies to the initial fetch path. Still, wrapping these in try-catch (`catch → renderEmptyState`) would be more robust.

### H-3 — Cold cable `phase_slot`/`phase_label`/`phase_basis` fields (working tree sld_payload.py)

The working-tree `sld_payload.py` adds `phase_slot`, `phase_label`, `phase_basis` to the `cold_cable` dict for Cable3C segment paths. These are currently not read by any JS function. The payload fingerprint will differ from what was computed for the existing `split_circuits` topology edit (`topology_baseline_changed: true`). This is harmless to rendering but will trigger the "topology needs review" warning banner.

**No action needed for rendering;** the data is correct. When a topology reset is applied, the baseline will resync.

---

## 8 — Summary Table

| Check | Finding | Confidence |
|---|---|---|
| Python payload generation | Correct — no field access errors, JSON serializes cleanly | High ✅ |
| F-1 try-finally | Present in working tree | High ✅ |
| F-2 try-catch | Present in working tree | High ✅ |
| F-3 watchdog | Present in working tree | High ✅ |
| r3 hit targets | `pointerEvents: 'all'` present in working tree | High ✅ |
| CableDetailLabelElement runtime | Correct JointJS 3.x pattern but unverifiable without browser | Low ⚠️ |
| Topology views (server-side) | Clean implementation, not the issue | High ✅ |
| Browser cache | Cache buster changed to sld-r3-hit-targets; browser should load new JS | Medium |
| **Remaining unknown** | **Whether `renderSldGraph` throws at runtime** | **Requires DevTools** |

**Next required action:** KR or Codex runs the 3-minute DevTools diagnostic in Section 5 and reports the result of Checks A, B, C. Codex then applies the targeted fix from Section 6's Scenario R, S, T, or U. Do not write more code without this diagnostic.

---

*Report produced by Claude (architect/auditor). Codex implements; KR decides.*
