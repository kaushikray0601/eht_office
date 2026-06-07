# SLD Rendering Guard — Production Review
**Reviewer:** Claude (architect/auditor)  
**Date:** 2026-06-07  
**Scope:** `static/js/sld_workspace.js` — working-tree changes only  
**Baseline:** 281 tests green, `node --check` clean  

---

## Executive Summary

Codex's working-tree fix introduced the correct primitives (`beginSldRender`,
`finishSldRender`, `isSldRendering`, `ensureSldWorkspaceReady`) and wired them
to all button handlers correctly. **However, the fix is incomplete.** One
structural error remains that will reproduce the original "sticky rendering"
lockup on any runtime exception during the JS render cycle. Three additional
findings cover robustness gaps.

## Codex Follow-up Status

Updated: 2026-06-07

- F-1 fixed: `fetchAndRenderSld` now releases the render guard in `finally`
  around both saved-layout success and fallback render callbacks.
- F-2 fixed: `renderSldGraph` now catches top-level render exceptions, logs the
  failure, clears stale SLD state, and renders an error state.
- F-3 fixed: `beginSldRender`/`finishSldRender` now maintain a watchdog that
  clears a stuck rendering flag after 20 seconds.
- F-4 remains optional polish; the refetch path already shows the normal loading
  message when `ensureSldWorkspaceReady` triggers a reload.

---

## Findings

### F-1 · CRITICAL — Missing try-finally in `fetchAndRenderSld` callbacks

**Location:** lines 3384–3385 (`.done` callback) and lines 3395–3396 (`.fail` callback)

**Current code (both locations):**
```javascript
renderCurrentSldPage(root);
finishSldRender(root);
```

**The bug:** `renderCurrentSldPage → renderSldGraph` is not in a try-finally.
If `renderSldGraph` throws any uncaught exception, the JavaScript engine
skips `finishSldRender`. The state machine ends with:
- `root.dataset.rendering = 'true'` — permanently locked
- `root.__sldState = null` — cleared by `beginSldRender`, never restored

`ensureSldWorkspaceReady` then always returns `false`:
- `root.__sldState` is null → not ready
- `isSldRendering()` returns true → does not re-trigger
- All four topology buttons silently return on every click

The SLD canvas may appear correct (JointJS draws at `graph.resetCells` which
precedes `root.__sldState` assignment), masking the corruption. The only
recovery without this fix is a full page refresh.

**Required fix — apply identically to both `.done` and `.fail` callbacks:**
```javascript
try {
    renderCurrentSldPage(root);
} finally {
    finishSldRender(root);
}
```

**Smoke test verification path:**
1. State after successful render: `rendering='false'`, `__sldState` set → buttons work ✓
2. State after exception: `finally` fires → `rendering='false'` → `__sldState` null → next button click re-triggers fetch → SLD reloads → state set → buttons work ✓

---

### F-2 · HIGH — No top-level exception handler in `renderSldGraph`

**Location:** `renderSldGraph`, lines 3037–~3310 (entire function body)

The function has exactly one internal try-catch, protecting only
`placeEditedTopology` (lines 3054–3059). The remaining ~250 lines — cell
creation, `graph.resetCells`, `root.__sldState` assignment, all paper/graph
event handler wiring — run completely unguarded.

**Consequence of an exception:**
- DOM is left in a half-rendered state (canvas div created, innerHTML set, JointJS
  Graph and Paper objects alive but cells only partially added)
- No user-visible error message — the user sees a blank or partial SLD with no
  explanation
- Exception propagates to `fetchAndRenderSld` callbacks (triggering F-1 if
  not fixed)

**Required fix — wrap the rendering body in a try-catch:**
```javascript
function renderSldGraph(root, payload, savedLayout) {
    if (!payload || !payload.nodes || !payload.nodes.length) {
        renderEmptyState(root, 'No stored graph nodes were returned for this project.');
        return;
    }
    if (typeof joint === 'undefined') {
        renderEmptyState(root, 'JointJS is not available in the current page context.');
        return;
    }
    try {
        root.innerHTML = '';
        root.classList.add('sld-diagram-shell--canvas');
        // ... (all existing lines from 3047 through end of function) ...
    } catch (renderError) {
        console.error('[SLD] renderSldGraph failed:', renderError);
        renderEmptyState(root, 'SLD diagram could not be rendered. Check browser console for details.');
    }
}
```

This ensures:
- User sees a meaningful error state instead of blank/partial canvas
- Exception is logged with stack trace in DevTools Console
- `finishSldRender` in the caller's `finally` block still fires correctly (F-1 fix)

---

### F-3 · MEDIUM — Watchdog timer to self-heal any future stuck state

Even with F-1 and F-2 fixed, future code changes could reintroduce a
scenario where `finishSldRender` is not called (async code in the JointJS
Paper render callbacks, for example). A safety watchdog guards against this
class of regression without imposing any cost on the happy path.

**Required fix — add to `beginSldRender` and `finishSldRender`:**
```javascript
function beginSldRender(root) {
    if (!root || root.dataset.rendering === 'true') {
        return false;
    }
    root.dataset.rendering = 'true';
    root.__sldState = null;
    // Safety net: clear stuck state after 20s regardless of what happens
    clearTimeout(root.__sldRenderWatchdog);
    root.__sldRenderWatchdog = setTimeout(function () {
        if (root.dataset.rendering === 'true') {
            console.warn('[SLD] render watchdog fired — clearing stuck rendering state');
            root.dataset.rendering = 'false';
        }
    }, 20000);
    return true;
}

function finishSldRender(root) {
    if (root) {
        clearTimeout(root.__sldRenderWatchdog);
        root.dataset.rendering = 'false';
    }
}
```

20 seconds is generous — the AJAX fetch + layout + JointJS init should
complete in under 5 seconds on any realistic project. If the watchdog fires,
it means something went wrong that escaped F-1 and F-2.

---

### F-4 · LOW — UX gap when auto-rerender is triggered by a topology button click

**Location:** `ensureSldWorkspaceReady`, lines 130–141

When `__sldState` is null and `rendering='false'` (e.g., after a failed
render with F-1 fix applied), clicking any topology button auto-triggers a
fresh `fetchAndRenderSld`. The user's action is silently swallowed (the
button press has no visible effect), and a new loading cycle starts
invisibly.

The user sees: "I clicked Combine — nothing happened." They don't see the
SLD reloading.

**Suggested improvement (optional, not blocking):** Inside
`ensureSldWorkspaceReady`, after triggering the re-fetch, briefly display a
"Reloading SLD..." message or flash the SLD panel. This is polish, not a
correctness fix.

---

## Analytical Smoke Test

**Test conditions:** assume F-1, F-2, F-3 are applied.

### Path A — Happy path (render succeeds, then topology operations)

| Step | State | Expected |
|---|---|---|
| `fetchAndRenderSld` called | rendering='true', __sldState=null | ✓ |
| AJAX returns payload | — | ✓ |
| `fetchSavedLayout` resolves | — | ✓ |
| `renderCurrentSldPage` called | — | ✓ |
| `renderSldGraph` completes | __sldState set at line 3176, paper events wired | ✓ |
| `finally: finishSldRender` | rendering='false' | ✓ |
| Click `#sld-combine-mode` | `ensureSldWorkspaceReady` → __sldState truthy → true | ✓ |
| `combineMode` toggled | `updateCombineControls` + `scheduleTopologyPreview` | ✓ |
| Click `#sld-split-mode` | same pattern | ✓ |
| Click `#sld-downstream-jb-mode` | same pattern | ✓ |
| Click `#sld-attach-jb-mode` | same pattern | ✓ |
| Click `#sld-combine-apply` | `ensureSldWorkspaceReady` → true → `applyCombineFeeders` | ✓ |

### Path B — Render throws before `root.__sldState` assignment

| Step | State | Expected |
|---|---|---|
| `renderSldGraph` body throws | try-catch (F-2) catches → `renderEmptyState` | ✓ |
| F-2 catch logs to console | User sees error message | ✓ |
| `finally: finishSldRender` | rendering='false', __sldState=null | ✓ |
| Click `#sld-combine-mode` | `ensureSldWorkspaceReady` → null, not rendering → triggers new fetch → returns false | ✓ |
| Fresh fetch + successful render | __sldState set, rendering='false' | ✓ |
| Second click `#sld-combine-mode` | `ensureSldWorkspaceReady` → true | ✓ |

### Path C — AJAX 404 retry path

| Step | State | Expected |
|---|---|---|
| AJAX returns 404, selectedLineId set | `clearFocusedLineFilter` → true | ✓ |
| `finishSldRender` called FIRST | rendering='false' | ✓ |
| `fetchAndRenderSld` called | `beginSldRender` → not blocked → rendering='true' | ✓ |
| New AJAX fetch succeeds | full render cycle completes | ✓ |

### Path D — Topology button click during in-flight AJAX render

| Step | State | Expected |
|---|---|---|
| Render in progress | rendering='true', __sldState=null | — |
| Click `#sld-combine-mode` | `ensureSldWorkspaceReady` → null, isSldRendering=true → false | ✓ |
| No action taken, no duplicate fetch | — | ✓ |
| AJAX completes, render finishes | rendering='false', __sldState set | ✓ |
| Next click on combine | `ensureSldWorkspaceReady` → true | ✓ |

### Path E — Watchdog fires (stuck state edge case)

| Step | State | Expected |
|---|---|---|
| `beginSldRender` sets rendering='true', starts 20s timer | — | ✓ |
| Some edge case prevents `finishSldRender` (async JointJS callback etc.) | rendering stays 'true' | — |
| 20s elapses | watchdog fires → rendering='false' | ✓ |
| Click topology button | `ensureSldWorkspaceReady` → null, not rendering → fresh fetch | ✓ |

---

## Test Protocol for Manual Browser Verification

Open Chrome DevTools → Console tab before each test.

**T1 — Normal SLD load:**
1. Open a project with a calculated SLD
2. Click the SLD tab
3. Confirm: SLD renders, no console errors
4. Confirm: Combine, Split, Downstream JB, Move MCB buttons all toggle correctly

**T2 — Simulate stuck rendering:**
1. Open DevTools Console
2. While SLD tab is active, run: `document.getElementById('sld-diagram-shell').dataset.rendering = 'true'; document.getElementById('sld-diagram-shell').__sldState = null;`
3. Click any topology button — should silently do nothing (correct: re-fetch is triggered)
4. Wait 2–3 seconds for re-fetch → SLD reloads
5. Click topology button again — should work

**T3 — Watchdog:**
1. Open DevTools Console
2. Manually set: `document.getElementById('sld-diagram-shell').dataset.rendering = 'true';`
3. Wait 20 seconds
4. Confirm DevTools prints `[SLD] render watchdog fired — clearing stuck rendering state`
5. Confirm topology buttons now work

**T4 — Combine circuit end-to-end:**
1. SLD loaded
2. Click Combine mode (button goes active)
3. Click MCB node → MCB highlights
4. Click another branch's MCB → second MCB highlights
5. Click Apply — confirm HTMX POST fires, response reloads SLD
6. Confirm combine summary shows merged branch

**T5 — Page refresh clears all state cleanly:**
1. Toggle any topology mode
2. Hard-refresh the page (Ctrl+Shift+R)
3. Confirm SLD reloads cleanly from server, no stale mode active

---

## Summary for Codex

Apply these changes to `static/js/sld_workspace.js`:

1. **F-1 (required):** In `fetchAndRenderSld`, wrap `renderCurrentSldPage(root)` in `try { } finally { finishSldRender(root); }` in BOTH the `.done()` and `.fail()` callbacks. Remove the bare `finishSldRender(root)` lines that follow.

2. **F-2 (required):** In `renderSldGraph`, after the two early-return guards, wrap everything from `root.innerHTML = ''` to the end of the function in `try { } catch (renderError) { console.error('[SLD] renderSldGraph failed:', renderError); renderEmptyState(root, 'SLD diagram could not be rendered. Check browser console for details.'); }`.

3. **F-3 (strongly recommended):** Add the 20-second watchdog timer to `beginSldRender` and the corresponding `clearTimeout` to `finishSldRender`.

4. **F-4 (optional polish):** Consider displaying a brief loading indicator when `ensureSldWorkspaceReady` auto-triggers a re-fetch.

After implementing, run:
- `node --check static/js/sld_workspace.js` — must pass
- `python manage.py test eht --verbosity=0` — must stay at 281 green
- Manual T1–T5 browser verification above
