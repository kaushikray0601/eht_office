# Pass Review: TEST-P1, SLD-P2, SLD-P1
# Reviewed by Claude — 2026-06-13
# Commit reviewed: 0e31ffd ("Refactor code structure for improved readability and maintainability")
#
# CODEX: start reading from line 15.

---

## Context

Commit `0e31ffd` (2026-06-13) bundled three passes that were previously dirty work
from `dc8c741`: TEST-P1, SLD-P2, and SLD-P1, plus Claude's vendor-validation NOTES
files. Test baseline after commit: **307 SQLite / 306 PostgreSQL, both green.**

---

## TEST-P1 — Test Baseline Repair

**Verdict: Clean. No action needed.**

All three fixes are correct and consistent with the project:

- `SldLayoutTests.setUp` (eht/tests.py:2614) now calls `self.client.force_login(self.user)`
  — matches the pattern used by `ResultAndBoqViewTests` and every other auth-gated class.
- `'4C x 2.5 mm2'` → `'3C x 2.5 mm2'` assertion — correct CC-P5 single-phase alignment.
- Migration `0037` SQLite fix uses schema-editor column removal guarded by introspection —
  the right approach for a PostgreSQL-specific DDL in a shared migration.

---

## SLD-P2 — Combined-Circuit Cold-Cable Resizing

**Verdict: Solid implementation. Three low-severity findings.**

### What was reviewed

- `eht/cold_cable.py`: `build_cold_cable_sizing_snapshot` extraction from
  `size_cold_cable_for_branch`.
- `eht/sld_topology_workflows.py`: operating-current lookup, trunk-length defaulting,
  cold-cable impact calculation and persistence.
- `static/js/sld_workspace.js`: `formatColdCableImpactWarning` and apply-response
  handling.
- `eht/tests.py:3811`: `test_combine_feeders_apply_recalculates_manual_trunk_cold_cable_impact`.

### What is good

**Architecture:** The extraction of `build_cold_cable_sizing_snapshot(project, sizing_input)`
from `size_cold_cable_for_branch` is a clean, minimal refactor. Public interface unchanged;
new function returns the sizing dict without FK fields; original function adds those back.
Correct scope for reuse.

**Operating-current resolution:** `_combined_feeder_operating_current` cascades node
metadata → DB lookup (`ProcessLineCalculation.operating_current`) → breaker-rating
fallback. Fallback fires a review note. Empty-nodes edge case guarded. Defensively designed.

**Trunk-length defaulting:** Defaults to `max(selected feeder lengths)`, basis recorded as
`'max_selected_feeder_length'`. Falls back to `project.ckt_ln` if no feeder has a length.
`_trunk_length_basis` correctly distinguishes `'user_input'` vs the automatic default.

**Impact evidence:** Rich — calculated size, VD %, fault loop, conductor mass, previous
mass delta, affected lines, affected schedule rows, review notes. Persisted in
`SLDTopologyEdit.edit_payload['cold_cable_impact_summary']` and
`edit_payload['downstream_summaries']['cold_cable']`. SLD payload meta gets
`combined_feeder_cold_cable_status` / `combined_feeder_cold_cable_review_required`. Manual
trunk Cable4C node carries full cold-cable evidence dict.

**Main test (tests.py:3811):** Thorough end-to-end — creates project, sizes cold cables,
applies combine, asserts trunk_length_basis, impact status, calculated size format, affected
schedule rows, conductor mass, review notes, edit_payload persistence, SLD payload meta, and
manual trunk node metadata.

### Findings

**F-001 — Low: No test for user-supplied `trunk_length_m`.**

The `trunk_length_basis: 'user_input'` branch of `_trunk_length_basis`
(sld_topology_workflows.py:482) is untested. When a user passes an explicit length in the
apply request body, the preview propagates it and `_trunk_length_basis` returns `'user_input'`.
This path is exercised by the frontend but has no automated test coverage.

Suggested action: Add an assertion variant to the existing test at tests.py:3811 that
passes `'trunk_length_m': <value>` in the request body and asserts
`payload['preview']['trunk_length_basis'] == 'user_input'`.

**F-002 — Low: Human-readable warning does not explicitly identify superseded
individual feeder lengths.**

The review note appended at sld_topology_workflows.py:944 reads:
"Manual combined-feeder topology edit requires route and schedule review before issue."

The SLD-P2 specification called for warning that prior separate feeder cable lengths are
now invalid. The mechanical information is present in `feeder_length_m` and
`previous_feeder_length_max_m` fields, but the human-readable message does not surface it.
Example of a more informative note:
"Prior individual feeder cable lengths are superseded by the combined trunk (defaulted to
max selected feeder length). Verify trunk length, then review BOQ and cable schedule."

This is a UX improvement, not a defect. Suggested for a future polish pass.

**F-003 — Low: No test for the no-prior-sizing path.**

The test at tests.py:3811 calls `size_cold_cables_for_project` before combining, so
Cable4C nodes already carry stored lengths. The path where `_default_combined_trunk_length`
finds no stored lengths on any feeder and falls back to `project.ckt_ln` is untested.
Edge case but worth a short unit test on `_default_combined_trunk_length` directly — it is
a plain function, no DB needed.

---

## SLD-P1 — Visual Review Badges

**Verdict: Consistent with project test style. One observation on test depth.**

### What was reviewed

- `static/js/sld_workspace.js`: `ReviewBadgeElement`, `coldCableBadgeStatus`,
  `topologyBadgeStatus`, `reviewBadgesForNode`, `reviewBadgeToneAttrs`,
  `reviewBadgeGeometry`, `hasMissingCableLength`, `hasManualOverride`.
- `eht/tests.py:156`: `test_sld_review_badges_render_from_existing_metadata`.

### What is good

`ReviewBadgeElement` as a JointJS element is the right approach — badges are positioned
overlays that move with their owning component and are refreshed after layout changes. The
four badge conditions (topology stale/review, length missing, cold-cable danger/review,
manual override) map cleanly to existing payload metadata fields. Badge order is sensible:
topology first, then engineering signals. Cap at 3 badges is pragmatic — a node
accumulating all 4 simultaneously is a rare production edge case.

### Findings

**F-004 — Low: Badge logic not unit-tested.**

`test_sld_review_badges_render_from_existing_metadata` (tests.py:156) asserts that
function names and key string literals exist in the compiled JS source — consistent with the
established `SldWorkspaceJavaScriptTests` pattern. However, the branching logic inside
`hasMissingCableLength`, `coldCableBadgeStatus`, and `topologyBadgeStatus` is unexercised:
- `hasMissingCableLength` returning true for `sizing_status === 'length_missing'` or
  `length <= 0` is not verified.
- `coldCableBadgeStatus` upgrading to `'danger'` for `status === 'unsizeable'` is not
  verified.

Suggested action: Defer to QA-P1. Add `SldWorkspaceJavaScriptTests` cases that construct
representative metadata objects and assert expected badge label strings.

---

## PM Documentation Gap

**Action needed before starting SCH-P1.**

`CODEX_MEMORY.md` and `CURRENT_PHASE_TRACKER.md` both still read:
"HEAD is `dc8c741`. Current dirty work includes `TEST-P1`, `SLD-P2`, `SLD-P1`..."

Actual HEAD is `0e31ffd`. Working tree is clean. The individual pass entries are correctly
marked complete but the "Current Repo State" / "Current State" blocks were not updated in
the commit.

Codex must update both files:
1. Change HEAD reference to `0e31ffd`.
2. Remove the "current dirty work" sentence (no dirty work remains).
3. Confirm SQLite 307 / PostgreSQL 306.
4. Set immediate next pass to `SCH-P1`.

---

## Action Summary for Codex

| ID | Priority | Location | Action |
|----|----------|----------|--------|
| PM-001 | Do first | CODEX_MEMORY.md + CURRENT_PHASE_TRACKER.md | Update HEAD to 0e31ffd, clear dirty-work sentence, set SCH-P1 as next pass |
| F-001 | Low | eht/tests.py:3811 | Add user-supplied trunk_length_m variant to the combine-feeders impact test |
| F-002 | Low | eht/sld_topology_workflows.py:944 | (Optional) Improve review note to name superseded individual feeder lengths |
| F-003 | Low | eht/tests.py | Add unit test for `_default_combined_trunk_length` no-prior-sizing path |
| F-004 | Low | eht/tests.py | Defer badge logic branch tests to QA-P1 |
