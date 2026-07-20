# Raceway Overlay JavaScript Audit - 2026-07-19

Owner: Codex

Context: KR reported that `Apply Edge Match` did not reliably activate after
connecting dissimilar cable trays, and asked whether the large vanilla
JavaScript overlay is now at risk of silent drift.

## Audit Scope

- Reviewed `raceway/static/raceway/js/raceway_overlay.js` structurally from the
  top-level state/constants through:
  - command enablement and keyboard dispatch,
  - persistence/save/reload lifecycle,
  - graph/schedule/fitting projection refresh lifecycle,
  - reducer candidate collection and edge-match offset application,
  - fitting proxy rendering and measurement snap exposure,
  - panel rendering and event handlers.
- Ran JavaScript syntax checks and focused browser regressions after the fix.

## Findings

### F-21 - Global Dirty Gate Blocked Reducer Command Too Broadly

Severity: medium-high.

`Apply Edge Match` was disabled whenever *any* local run was unsaved or dirty.
That was too broad for real authoring sessions, because a harmless unfinished
one-node draft can remain in memory while the saved graph already contains a
valid reducer candidate. The command should only block on unsaved savable graph
changes.

Fix implemented:

- added `runHasUnsavedSavableChanges` and `hasUnsavedSavableChanges`,
- reducer application now blocks only when a two-node-or-longer run is unsaved
  or dirty,
- browser regression injects a one-node local draft beside two saved unequal
  trays and confirms `Apply Edge Match` remains active.

### F-22 - Transition Candidates Had No User-Facing Diagnostic

Severity: medium.

When fittings contained a reducer/transition candidate but no edge-offset action
was applicable, the button could feel random: disabled or no-op depending on
candidate details. This particularly affects "dissimilar tray" tests where the
connection is a family/depth transition, not a same-family width reducer.

Fix implemented:

- added `reducerTransitionCandidates`,
- button stays callable when fitting projection contains reducer candidates,
  even if no offset suggestions exist,
- `Apply Edge Match` now explains whether candidates are already edge-aligned,
  service transitions, family/depth placeholders, or missing adjacent segment
  context,
- browser regression covers a same-width ladder-to-tray family/depth
  transition and confirms the explanatory status message.

### A-6 - Reducer Body V0 Scope Must Be Made Explicit In UX

Severity: product clarity issue, not a defect.

The current synthetic reducer body is intentionally limited to saved
same-family unequal-width left-edge matches. Family transitions, service
transitions, and depth-only/width-depth transitions remain catalogue-validation
placeholders. This follows the earlier Claude/Fable A-5 advice, but the UI must
surface it clearly because a user will naturally call many of these cases
"dissimilar trays".

Status: clarified in `Apply Edge Match` diagnostic text. Full body generation
for depth and family adapters remains open.

### A-7 - Right/Center Reducer Side Is Draft-Local

Severity: medium future bug risk.

The UI exposes `right_edge` and `centerline`, and the command can apply those
offset suggestions. However the server-side resolved reducer body currently
materializes only the default left-edge resolved case because reducer handedness
is not persisted as accessory intent yet.

Recommendation: before advertising right/center as final reducer geometry,
persist reducer handedness using the segment-intent metadata idiom, or label
right/center as drafting/diagnostic helpers only.

### R-1 - Vanilla JS Scale Risk Is Now Real

Severity: architecture risk.

The overlay is approximately 4,775 lines and combines pure geometry,
mutable state transitions, HTML rendering, persistence, telemetry, and command
availability in one file. That is still workable for MVP, but future tee/cross,
accessory intent persistence, and AI-assisted workflow telemetry will increase
the risk of silent regressions.

## Hardening Recommendation

Do a short architecture hardening pass before detailed tee/cross body geometry:

1. Extract a pure command-state layer.
   - `computeRacewayCommandStates(snapshot)` returns enabled/disabled/reason
     for each command.
   - Unit/browser tests cover saved, dirty, one-node draft, loaded/unloaded
     fitting projection, transition placeholder, and reducer proxy cases.
2. Add JSDoc typedefs and `// @ts-check` compatible structure.
   - No build step required at first.
   - Later migration to TypeScript becomes incremental instead of disruptive.
3. Split pure geometry helpers from DOM/event handlers.
   - First split target: segment/fitting geometry and reducer/tee/cross proxy
     render recipes.
4. Add viewer-state invariants.
   - After topology changes: derived projections must clear.
   - Before save: only savable runs are persisted.
   - After save: saved segment keys and intent overrides must agree.
5. Keep browser tests on user workflows, not only static source assertions.
   - Button enabled state,
   - click status text,
   - rendered proxy existence,
   - measurement snap kind exposure,
   - console error absence.

## Manual Check For KR

- In the same-family unequal-width case, use `LADDER-HDG 300 x 100` to
  `LADDER-HDG 600 x 150` or another same-family width mismatch:
  - save,
  - refresh fittings,
  - click `Apply Edge Match`,
  - save,
  - refresh fittings,
  - confirm reducer proxy appears.
- In a family/depth transition such as ladder 300 x 100 to perforated tray
  300 x 75:
  - refresh fittings,
  - click `Apply Edge Match`,
  - expect an explanatory status message rather than a reducer body.

## 2026-07-20 Amendment - Save Draft Additive Regression

KR's next manual cycle exposed a second state-lifecycle defect: Save Draft was
additive. Deleted local trays could remain as saved server runs, then reappear
under newly added trays after save/reload and pollute fitting/edge-match
projection.

Root cause:

- the viewer remembered local `runs`,
- Save Draft POST/PATCHed only local runs with at least two nodes,
- but the viewer did not remember which server run IDs were loaded into this
  editing session,
- so it could not delete loaded server runs that were removed locally or reduced
  below two nodes.

Fix implemented 2026-07-20:

- overlay state tracks `loadedServerRunIds`,
- Save Draft treats the loaded server run set as the reconciliation base,
- loaded server IDs absent from the current savable local draft are deleted via
  the normal run DELETE endpoint,
- deletion-only saves are enabled,
- pending server-run deletion counts as an unsaved graph change, so
  `Apply Edge Match` waits until the saved graph is synchronized,
- live browser regression `test_real_viewer_save_reconciles_deleted_saved_runs`
  locks this behavior.

Hardening added in the same pass:

- `EXPECTED_FITTING_PROJECTION` pins the client-consumed fitting projection
  version,
- fitting projection load warns on version mismatch,
- reducer candidates that filter to zero edge-match actions log exclusion
  reasons.

Architecture note:

This confirms the audit's R-1 warning: the next serious step should be a
dedicated state/command hardening pass before more geometry features. Priority:
pure command-state extraction, server-client projection contract tests,
visible disabled-reason UX, then persisted reducer accessory intent.

## 2026-07-20 Amendment - Claude B-List Guardrails

KR supplied Claude's B-1..B-5 balance list while manually testing the save
reconciliation pass. The following guardrails were added before further
accessory geometry:

- B-1 reducer contract tests now pin the server fields and exact strings the
  JS reads for reducer candidates and reducer proxies:
  `raceway.fittings.v0`, `derived_placeholder`, `reducer_candidate`,
  `placeholder`, `synthetic_proxy`, `width_reducer`, `one_edge_matching`,
  `required_not_modelled`, `edges_not_aligned`, `member_offsets`, and
  `reducer_taper`.
- B-2 fail-loud client checks now warn on missing fitting projections,
  projection-version mismatch, malformed `items`/`counts`, malformed reducer
  candidate identity/status/alignment payloads, and candidate-filter
  exclusions.
- B-3 is landed for Edge Match: the disabled reason now appears below the
  Raceway status line in `#racewayCommandHint`; it is not tooltip-only.
- B-4 is diagnostic-hardened: the `insufficient_segment_context` fallback now
  includes segment-context counts and missing member identities. Tests prove
  a normally connected unequal-size endpoint transition does not reach that
  branch; a malformed one-node shared-point case keeps the fallback covered.

Still open:

- B-5/CI wiring.
- Pure command-state extraction (`computeRacewayCommandStates(snapshot)`).
- JSDoc/`// @ts-check` shaping.
- Geometry/DOM split.
- Broader graph/schedule/fitting contract pins outside reducer-specific fields.
