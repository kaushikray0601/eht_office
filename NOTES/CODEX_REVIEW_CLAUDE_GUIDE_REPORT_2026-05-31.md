# Codex Review - Claude Guide and Verification Report

Date: 2026-05-31

## Context

Claude added an engineering hub / design guide and a hand-calculation style
verification report while Codex was unavailable. Codex reviewed the work before
resuming cold cable development.

## Finding Summary

The guide/report work was generally well isolated from the cold cable sizing
engine. It added new pages, static assets, URL routes, navbar entries, and
manual content without overwriting the core cold cable calculation module.

## Issues Found and Fixed by Codex

1. Verification report project access was too broad.
   - Previous behavior: listed all `ProjectData` rows.
   - Risk: showed projects unavailable to the current user and exposed the
     default/template project.
   - Fix: report selector now follows `ManagedProject.available_to_user()` and
     excludes `DEFAULT_PROJECT_ID`.

2. Verification report line lookup needed hardening.
   - Previous behavior: direct `get()` with raw query string.
   - Fix: validates the line UID and filters within the selected confirmed-line
     queryset.

3. Cold cable report branch list was truncated.
   - Previous behavior: rendered only the first three `ColdCableResult` rows.
   - Risk: hid branches on multi-run/multi-branch lines.
   - Fix: report now renders all branch results.

4. Direct 3C branch cold cable evidence could inherit a 4C temperature fallback.
   - Fix: conductor-temperature evidence now falls back to the 3C catalogue row
     when no 4C catalogue row exists.

5. Cold cable evidence text needed alignment with current engineering basis.
   - Fix: report now distinguishes direct 3C voltage drop from 4C+3C branch
     voltage drop.

6. Grouping derating documentation was stale.
   - Previous text: 0.1 to 1.0.
   - Current basis: 0.25 to 1.0.
   - Fix: updated manual and design-guide references.

7. A latent string-concatenation bug was found in the verification report.
   - Fix: corrected the result-label expression and added coverage through the
     broader result/report tests.

## Tests Added

- Verification report lists only available working projects.
- Verification report rejects unavailable projects.
- Verification report renders cold cable evidence.
- Verification report does not truncate cold cable branches.

## Recommendation for Claude Follow-Up

Keep the guide/report as downstream evidence renderers. They should continue to
read persisted calculation results and avoid duplicating sizing, SR/MI selection,
or voltage-drop logic in presentation code.

