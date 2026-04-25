# EHT Office

This repository contains the current Electric Heat Tracing (EHT) design application.
The active Django app supports project setup, input import, calculation persistence,
result/BOQ review, and the project-backed Single Line Diagram (SLD) workspace.

## Current Architecture Notes

The SLD work is no longer based on the retired hardcoded prototype. The canonical
SLD path is the workspace tab backed by stored power-distribution branch data.

Current references:
- [Codebase review snapshot](NOTES/CODEBASE_REVIEW_2026-04-17.md)
- [Diagram platform decision memo](NOTES/DIAGRAM_PLATFORM_DECISION_MEMO_2026-04-23.md)
- [Diagram platform target architecture](NOTES/DIAGRAM_PLATFORM_TARGET_ARCHITECTURE.md)
- [SLD refactor and build roadmap](NOTES/SLD_REFACTOR_BUILD_ROADMAP.md)
- [EHT SLD graph contract](NOTES/EHT_SLD_GRAPH_CONTRACT.md)
- [Refactor task tracker](NOTES/REFRACTOR_TASK_TRACKER.md)

## Current SLD Baseline

The generated EHT SLD is derived from persisted `PowerDistributionBranch`
records and rendered in the main workspace. Saved node positions are stored
separately in `SLDNodeLayout` so layout can survive recalculation when stable
component IDs remain valid.

Primary implementation files:
- `eht/sld_payload.py`
- `eht/sld_validation.py`
- `eht/sld_layout.py`
- `eht/views.py`
- `templates/eht/partials/sld_tab.html`
- `static/js/sld_workspace.js`
