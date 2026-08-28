# Markdown Housekeeping Inventory

Date: 2026-08-28  
Owner: Codex, with KR deletion authority and Claude/Fable review

## Purpose

This inventory closes Closure Pass 5 without deleting history. The rule is:
records that explain why we changed direction should stay. Scratch files and
workspace files can be removed only after KR approves the exact deletion.

## Keep Canonical

These remain current control records:

- `plant3d/records/README.md`
- `plant3d/records/audit/open-items-register.md`
- `plant3d/records/audit/development-scorecard.md`
- `plant3d/records/audit/claude-notes-2026-07-08.md`
- `plant3d/records/audit/phase-g-closure-audit-2026-08-02.md`
- `plant3d/records/tracking/raceway-mvp-progress-tracker-2026-07-08.md`
- `plant3d/records/planning/raceway-mvp-execution-plan-2026-07-08.md`
- `plant3d/records/planning/raceway-accessory-geometry-note-2026-07-17.md`
- `plant3d/records/planning/raceway-clash-pathfinding-staging-2026-08-28.md`
- `plant3d/records/planning/raceway-methodology-and-ai-strategy-2026-07-11.md`
- `plant3d/records/planning/suggestion-telemetry-design-2026-07-12.md`
- all `plant3d/records/decisions/*.md`
- `CLAUDE.md`
- `NOTES/project_management/CLAUDE.md`
- `NOTES/project_management/CODEX_MEMORY.md`

## Keep As Supporting Context

These are not day-to-day control documents, but they preserve important
reasoning and should remain linked:

- `plant3d/records/planning/agreed-architecture-2026-06-22.md`
- `plant3d/records/planning/plant3d-platform-boundary-contract-2026-07-05.md`
- `plant3d/records/planning/public-api-boundary-contract-2026-07-05.md`
- `plant3d/records/planning/viewer-extension-contract-2026-07-11.md`
- `plant3d/records/operations/worker-container-runbook-2026-06-28.md`
- `plant3d/records/testing/browser_viewer_probe.py`
- `plant3d/records/testing/ifc-sample-conversion-results-2026-06-23.md`

## Historical Or Superseded, Keep With Header

These records are useful history but should not be treated as current
execution direction. Closure Pass 5 added lifecycle notes to the first four.

- `plant3d/records/tracking/pipeline-spike-tracker-2026-06-22.md`
- `plant3d/records/tracking/platform-ecosystem-reset-tracker-2026-07-08.md`
- `plant3d/records/planning/platform-ecosystem-development-plan-2026-07-08.md`
- `plant3d/records/planning/cable-routing-foundation-review-2026-07-06.md`
- `plant3d/records/planning/cable-routing-vision-and-gap-analysis-2026-07-06.md`
- `plant3d/records/planning/platform-reset-handover-2026-07-08.md`
- `plant3d/records/planning/pipeline-explainer-for-kr-2026-06-23.md`
- `plant3d/records/planning/claude-render-format-research-2026-06-23.md`
- reset prompts under `plant3d/records/prompts/`
- `plant3d/records/audit/claude-review-2026-06-22.md`

## Deletion Candidates Requiring KR Approval

No deletion was performed in Closure Pass 5.

Exact candidates:

- `plant3d/records/audit/eht_office.code-workspace`
- repo-root `implementation_plan.md`
- repo-root `ifc_first_step.md`
- repo-root `index.html`
- repo-root `parse_meta.py`
- repo-root sample `*.pcf`
- repo-root `IDF/*.idf` sample set, if no longer needed locally

Before deleting any sample engineering input, confirm whether it is still used
for a parser, rendering, or regression workflow.

## Broad Legacy NOTES

The root `NOTES/` tree contains EHT, MI, SR, SLD, validation, and release
history. Do not bulk-delete it during Raceway closure. It should be handled as
a separate EHT records cleanup pass after the pending EHT release sign-off.

Recommended future action:

- keep `NOTES/project_management/*` that current stubs reference,
- keep vendor validation source documents and validation records,
- archive old implementation checklists only after confirming they are not the
  sole source of a still-open EHT decision.

## Pass 5 Result

Closure Pass 5 is a non-destructive housekeeping pass:

- lifecycle headers added where old documents could mislead a fresh session,
- deletion candidates named but not removed,
- active records remain under `plant3d/records/README.md`,
- A2 remains open because workspace-file removal needs explicit KR approval.
