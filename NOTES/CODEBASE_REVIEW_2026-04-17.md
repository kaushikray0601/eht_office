# EHT Codebase Review

Date: 2026-04-17

Current status note, 2026-04-24:
This document is a historical review snapshot. Several findings were correct at
the time but have since moved forward. In particular, the old hardcoded SLD
prototype has been retired, and the current canonical SLD path is the
project-backed workspace documented in:
- [SLD_REFACTOR_BUILD_ROADMAP.md](/home/kr/mydev/eht_office/NOTES/SLD_REFACTOR_BUILD_ROADMAP.md:1)
- [EHT_SLD_GRAPH_CONTRACT.md](/home/kr/mydev/eht_office/NOTES/EHT_SLD_GRAPH_CONTRACT.md:1)

## 1. Executive Summary

This repository is a partially completed Django application for electrical heat tracing (EHT) design. The intended product flow is clear from the code and the `NOTES/` folder:

1. Capture project-level design settings.
2. Import piping/process-line input from Excel.
3. Calculate heat loss per line.
4. Select a suitable tracer and alternates from vendor data.
5. Derive power distribution and component tagging.
6. Produce BOQ, reports, and an SLD.

The project did not stop at the idea stage. A meaningful amount of work is already present:

- Django app scaffold is in place.
- Project setup UI exists.
- Excel template download and upload flow exist.
- Input sanitization exists.
- Lookup data import exists.
- A modular calculation pipeline exists in `eht/cal.py` and `eht/calculations/`.
- Sample database content shows that project data, input lines, heat loss, and selected tracer records were generated at least once.

The project appears to have stopped during a refactor from an older monolithic calculation approach (`eht/calculation.py`) into a more modular pipeline (`eht/cal.py`, `eht/data_service.py`, `eht/calculations/*`). The current repository state is best described as:

- Domain intent: clear
- Core calculation direction: established
- Persistence/reporting layer: broken/incomplete
- UI integration: partial
- SLD/reporting layer: prototype only
- Test coverage: absent

## 2. What I Reviewed

I reviewed:

- `NOTES/Assumptions`
- `NOTES/UI_development.md`
- `NOTES/code_review.md`
- Django settings, URLs, models, forms, views
- Input sanitization and data import command
- Current modular calculation pipeline
- Templates and frontend JS
- Database contents in the existing `db.sqlite3`

I also ran lightweight validation:

- `venv/bin/python manage.py check`
- `venv/bin/python manage.py test eht`
- `venv/bin/python manage.py showmigrations`
- Shell-level checks of current table counts and sample calculation execution

## 3. Runtime Verification Snapshot

### 3.1 Django health

- `manage.py check`: passed
- `manage.py test eht`: 0 tests
- `showmigrations`: only `eht.0001_initial` is applied

### 3.2 Database snapshot

At review time, the database contained:

- `ProjectData`: 2
- `HeatTracingInput`: 7
- `ElecEHT_ThermalConductivity`: 5
- `ElecEHT_Vendor`: 219
- `ElecEHT_ASMEB36`: 200
- `HeatLoss`: 2
- `SelectedTracer`: 2
- `AlternateTracer`: 0
- `PowerDistribution`: 0
- `BOQ`: 0
- `ProcessLineCalculation`: 0

Interpretation:

- Lookup/reference data is loaded.
- Input rows were uploaded and confirmed.
- Some calculation output was persisted for heat loss and selected tracers.
- Downstream persistence for power distribution, BOQ, and process-line result tables is not working.

### 3.3 Calculation pipeline behavior

Running the current orchestrator for project `p1` produced in-memory results:

- `heat_loss`: 5
- `selected_tracers`: 3
- `alternative_tracers`: 3
- `power_distribution`: 3
- `boq_per_line`: 3
- `consolidated_boq`: 15 items
- `tracer_power_param`: 3

This is important: the modular pipeline can compute a meaningful subset of the workflow in memory.

However, persisting those results currently fails:

- `store_calculated_results()` crashes with `KeyError: 'alternate_tracers'`

That is the first confirmed blocker after the in-memory calculations.

## 4. Reconstructed Product Intent From Notes

The most important design intent is captured in `NOTES/Assumptions`:

- Heat loss from insulation conductivity, line size, ambient, and maintenance temperature.
- Wind-speed correction and tracer-length adders for valves/supports/flanges.
- Polynomial-based tracer power output selection from vendor data.
- Power distribution branching based on circuit count and breaker loading.
- BOQ generation for tracers, junction boxes, cables, isolators, RTDs/thermostats, labels, and accessories.
- SLD generation backed by stored relationships and coordinates.

The UI note in `NOTES/UI_development.md` shows the next intended stage after basic calculations:

- Dashboard
- Calculation results table
- BOQ views
- Power distribution visualization
- Component tagging page
- Selected vs alternate tracer comparison

This matches the codebase: backend calculation modules were being prepared so a richer reporting UI could be built on top.

## 5. What Is Already Implemented

### 5.1 Project scaffolding

- Django project/app structure is present.
- Static/templates layout exists.
- SQLite database is used locally.
- Crispy forms and easy audit are configured.

### 5.2 Project setup

- `ProjectData` model exists.
- `ProjectDataForm` exists.
- Create/edit views exist.
- Project setup UI is rendered in `templates/eht/project_data.html`.

### 5.3 Input import flow

- Template download endpoint exists.
- Upload endpoint exists in `calculate_view`.
- Excel file validation exists in `eht/sanatize_input.py`.
- Valid rows are bulk inserted into `HeatTracingInput`.
- Partial-invalid upload flow exists conceptually, with error-file generation.

### 5.4 Lookup/reference data

- Thermal conductivity table model exists.
- Vendor catalogue model exists.
- ASME B36 pipe size table exists.
- Management command imports CSV seed data from `eht/tmp/`.

### 5.5 Calculation modules

The newer modular design is visible:

- `eht/cal.py`: orchestration layer
- `eht/calculations/heat_loss.py`
- `eht/calculations/tracer_selection.py`
- `eht/calculations/power_distribution.py`
- `eht/calculations/boq.py`
- `eht/data_service.py`: fetch/store helpers

### 5.6 Early SLD prototype

Current status note, 2026-04-24:
The details below describe the old prototype state. The standalone
`templates/eht/sld.html` and `static/js/sld_module.js` path has since been
removed. The current SLD implementation is rendered inside the main workspace
from persisted `PowerDistributionBranch.tagged_components`, with layout stored
in `SLDNodeLayout`.

- `templates/eht/sld.html` and `static/js/sld_module.js` exist.
- JointJS is loaded.
- Drag/drop toolbar exists.
- Example auto-generated SLD data is hardcoded.

This is not integrated with actual project data, but it shows the UI direction.

## 6. Development Stage Assessment

### 6.1 Where development clearly reached

The project reached:

- Working project settings form
- Working reference data import
- Working-ish Excel validation
- Working in-memory heat loss calculation
- Working in-memory tracer selection
- Working in-memory basic power distribution and BOQ derivation
- Initial result table design in models
- Initial SLD front-end prototype

### 6.2 Where development stopped

Development appears to have stopped during or immediately after the refactor into modular calculations, before the application became end-to-end usable.

The clearest stopping points are:

- Result persistence was not finished.
- Result pages were not built.
- SLD backend data model / persistence was not connected.
- Auth was never fully implemented.
- Tests were never written.
- Old and new code paths still coexist.

## 7. End-to-End Flow Documented Step by Step

This is the current intended application flow as implemented today.

### Step 1. User creates or edits project setup

Files involved:

- `eht/models.py`
- `eht/forms.py`
- `eht/views.py`
- `templates/eht/project_data.html`

What happens:

- User enters project-level settings like ambient temperature, voltage, breaker limits, wind speed, RTD/thermostat mode, and cable lengths.
- Data is saved into `ProjectData`.

Current state:

- Partially working.
- The UI exists and edit/save logic exists.
- Real project lifecycle is constrained by hard-coded project IDs.

### Step 2. User downloads input template

Files involved:

- `eht/views.py`
- `file_storage/EHT_Input_template.xlsx`

What happens:

- A login-protected endpoint returns the Excel template.

Current state:

- Likely working if the user is authenticated and the file exists.
- Error handling is incomplete.

### Step 3. User uploads piping input file

Files involved:

- `templates/eht/project_data.html`
- `static/js/form_handler.js`
- `eht/views.py`
- `eht/sanatize_input.py`

What happens:

- Browser sends the selected Excel file to `/upload-input-file/`.
- `sanitize_file()` checks extension, MIME type, and row content.
- Valid rows are inserted into `HeatTracingInput`.
- Invalid rows are written into an error workbook.

Current state:

- Basic path exists.
- Duplicate-row handling is buggy.
- Partial-valid upload confirmation path does not trigger calculations.

### Step 4. Confirm valid rows and mark them confirmed

Files involved:

- `eht/views.py`

What happens:

- Rows in `HeatTracingInput` move from `pending` to `confirmed`.

Current state:

- Status update exists.
- The standalone confirm endpoint does not continue the calculation pipeline.

### Step 5. Fetch project/reference data

Files involved:

- `eht/data_service.py`

What happens:

- Project settings are fetched.
- Vendor rows are filtered by selected vendor and voltage.
- ASME and thermal conductivity reference data are loaded.

Current state:

- Implemented and usable.

### Step 6. Run modular calculations per line

Files involved:

- `eht/cal.py`
- `eht/calculations/*`

What happens per line:

1. Compute heat loss.
2. Select best tracer and alternates.
3. Compute electrical parameters.
4. Derive basic power distribution branches/tags.
5. Compute per-line BOQ.
6. Aggregate consolidated BOQ.

Current state:

- Works in memory for at least some inputs.
- Domain logic is still simplified and not fully validated.

### Step 7. Store results

Files involved:

- `eht/data_service.py`
- result models in `eht/models.py`

What happens:

- Code attempts to write heat loss, tracer selection, power distribution, BOQ, and power parameters to DB tables.

Current state:

- Broken.
- This is the current main blocker preventing the app from becoming a usable system.

### Step 8. Display results / BOQ / SLD

Files involved:

- `templates/eht/base.html`
- `templates/eht/sld.html`
- `static/js/sld_module.js`

What happens:

- The intended UI has tabs for Project Setup, Import Input, Result, BOQ, SLD, and Isometric.

Current state:

- Only Project Setup is meaningfully connected.
- Result/BOQ tabs are placeholders.
- SLD is a separate prototype page, not data-driven.

## 8. Major Review Findings

This section focuses on the most important issues first.

### Critical

1. Result persistence is broken immediately after orchestration.

- `eht/cal.py` produces `alternative_tracers`.
- `eht/data_service.py` looks for `alternate_tracers`.
- Verified by runtime shell execution: `store_calculated_results()` raises `KeyError`.

References:

- `eht/cal.py:15-23`
- `eht/cal.py:34-38`
- `eht/data_service.py:117-122`

2. Even beyond the first crash, the persistence layer and model schema do not match the runtime payloads.

Examples:

- `boq_per_line` is a dict keyed by line UID, but `store_calculated_results()` iterates it as if each item were a row dict.
- `PowerDistributionBranch` expects `branch_type`, but runtime branch objects use `type`.
- `PowerDistributionBranch.tagged_components` is a `TextField`, but code passes a nested dict/list structure directly.
- `ProcessLineCalculation` requires fields such as `line_size`, `selected_tracer`, `starting_current`, and `total_power_consumption`, but `compute_power_params()` does not return them.

References:

- `eht/cal.py:20-22`
- `eht/cal.py:56-66`
- `eht/models.py:235-262`
- `eht/data_service.py:124-145`

3. The result tables are not modeled correctly for multi-line, multi-project storage.

Examples:

- `SelectedTracer` and `AlternateTracer` use tracer catalogue `v_uid` as the primary key.
- If the same tracer is selected on multiple lines, rows will overwrite each other.
- A TODO already notes that project IDs should be added to result tables.

References:

- `eht/models.py:183-229`

4. Project creation is effectively capped and inconsistent.

Examples:

- Project IDs are hard-coded to only `p1` and `p2`.
- `ProjectDataForm` omits required model fields such as `tracer_family` and `req_local_isolator`.
- `isolator_location` default is `'II'`, which is not one of the declared choices.

This means the system does not yet support real project creation as a scalable business application.

References:

- `eht/models.py:10-15`
- `eht/models.py:17-18`
- `eht/models.py:29`
- `eht/models.py:42`
- `eht/models.py:45`
- `eht/forms.py:21-29`

5. The partial-invalid upload flow does not complete the promised behavior.

What the UI promises:

- If some rows are valid and some invalid, the user can confirm proceeding with valid rows.

What the backend does:

- `confirm_valid_data()` only updates status and returns success.
- It does not fetch project data, run calculations, store outputs, or redirect to results.

References:

- `templates/eht/project_data.html:77-141`
- `eht/views.py:135-144`
- `eht/views.py:293-306`

6. Duplicate-row validation in the sanitizer is broken.

Why:

- Most invalid entries are appended as dicts with `row_number` and `errors`.
- Duplicate entries are appended as tuples.
- The error-file writer later assumes every invalid entry is a dict.

This will break or mis-handle files containing duplicates.

References:

- `eht/sanatize_input.py:126-141`

### High

7. The UI is mixing multiple page structures and framework versions.

Examples:

- `base.html` includes `project_data.html`.
- `project_data.html` is a full standalone HTML document with its own `<html>`, `<head>`, `<body>`, CDN imports, and inline scripts.
- `base.html` uses Bootstrap 5, while `project_data.html` uses Bootstrap 4.

This is a structural integration problem, not just a styling issue.

References:

- `templates/eht/base.html:1-97`
- `templates/eht/project_data.html:1-249`

8. The frontend form markup has invalid/fragile structure.

Examples:

- Duplicate ID `form-container` is used for both a wrapping div and the form element.
- `project_data_form.html` contains an extra closing `</form>`.
- Three buttons share `type="submit"` even though they represent different actions.

References:

- `templates/eht/project_data.html:146-148`
- `templates/eht/project_data.html:239-241`
- `templates/eht/partials/project_data_form.html:3-4`
- `templates/eht/partials/project_data_form.html:95-99`

9. Authentication is only scaffolded.

Examples:

- `my_login`, `my_logout`, and `my_register` simply render templates.
- There is no real authentication logic, form handling, login throttling integration, or logout call to Django auth.
- Several core endpoints are `@login_required`, so real usage is blocked without manual admin/user setup.

References:

- `eht/views.py:429-436`

10. SLD is only a front-end prototype, not a working feature.

Examples:

- It uses hard-coded example data.
- It is not connected to `PowerDistribution` or `ElecEHT_TagManagement`.
- Context menu calls undefined functions: `rotateElement()`, `resizeElement()`, `highlightElement()`.

References:

- `templates/eht/sld.html:1-31`
- `static/js/sld_module.js:101-110`
- `static/js/sld_module.js:166-176`

11. Tag generation resets per line and will create duplicate tags.

Because the tag counters are local to each `compute_power_distribution()` call, tags restart from `MCB_001`, `JB1PH_001`, etc. on every process line. That breaks any project-wide SLD, BOQ traceability, or persisted relationship graph.

References:

- `eht/calculations/power_distribution.py:164-175`

### Medium

12. Security/deployment configuration is still development-only.

Examples:

- Hard-coded secret key in source.
- `DEBUG = True`
- `ALLOWED_HOSTS = []`

References:

- `ELECSENSE/settings.py:10-16`

13. Logging and error handling are inconsistent.

Examples:

- Some code uses `logging`.
- Some code uses `print()`.
- There are broad `except Exception` blocks that swallow actionable context.

References:

- `eht/views.py:369-405`
- `eht/management/commands/import_data_from_file.py:26-38`

14. Empty or abandoned modules indicate unfinished refactor work.

Examples:

- `eht/calculations/tag_management.py` is empty.
- `eht/calculations/utils.py` is empty.
- `eht/display_module.py` is empty.
- `eht/calculation.py` still contains the older, heavier path.

This strongly suggests refactoring was started but not completed.

15. Test coverage is missing.

- `eht/tests.py` is empty.
- `manage.py test eht` ran zero tests.

16. Admin support is minimal.

- Only `ProjectData` is registered in admin.
- None of the lookup or result models are registered for inspection/debugging.

## 9. What Is Finished vs Unfinished

### Finished enough to reuse

- Lookup-data import pattern
- Project setup form concept
- Heat loss calculation structure
- Tracer selection structure
- Early power distribution branching logic
- Early BOQ structure
- Notes/roadmap documents

### Partially done and salvageable

- Input sanitization
- Data-service layer
- Calculation orchestration
- Frontend upload flow
- Base layout and navigation concept
- SLD technology choice and prototype direction

### Clearly unfinished

- Correct result schema and persistence
- Result page
- BOQ page
- Consolidated reporting/export
- SLD back-end integration
- Project-wide tagging model
- Alternate tracer persistence/selection workflow
- Cable optimization / voltage-drop details
- Authentication
- Automated tests
- Production configuration

## 10. Long TODO List

This is the recommended forward plan from the current state.

### Phase A. Stabilize the data model first

1. Replace hard-coded project choices with a real project entity or free-text/code-based project ID.
2. Make `ProjectData` represent actual project metadata, not a restricted fixed-choice record.
3. Fix `isolator_location` default so it matches the declared choices.
4. Decide which `ProjectData` fields are actually required and remove dead fields.
5. Add proper `project` / `process_line` foreign keys to result tables.
6. Redesign `SelectedTracer` and `AlternateTracer` so they are keyed by process line result, not by tracer catalogue item.
7. Redesign `BOQ` into either:
   - one row per project+line+item, or
   - one normalized BOQ header/detail structure.
8. Redesign `ProcessLineCalculation` to match the actual outputs you want to store.
9. Normalize `PowerDistribution` and `PowerDistributionBranch` so stored fields match generated objects.
10. Decide whether `tagged_components` should be JSON, normalized child tables, or a true graph model.

### Phase B. Fix end-to-end persistence

1. Align `alternative_tracers` vs `alternate_tracers`.
2. Fix alternate tracer transformation logic so each alternate item is mapped independently.
3. Fix BOQ persistence to iterate through per-line item dictionaries correctly.
4. Fix power distribution branch persistence so `type` maps to `branch_type`.
5. Serialize nested tagged component data in a consistent format.
6. Expand `compute_power_params()` output or reduce `ProcessLineCalculation` requirements.
7. Wrap upload + calculate + store flow in a transaction where appropriate.
8. Add idempotent result replacement for a re-run of the same project.

### Phase C. Clean up the input pipeline

1. Refactor `sanitize_file()` into:
   - file-level checks
   - schema validation
   - row normalization
   - row validation
   - duplicate detection
   - error report generation
2. Fix duplicate detection payload shape.
3. Validate column presence explicitly before row iteration.
4. Validate booleans, quantities, temperatures, and allowed service types more rigorously.
5. Add a reusable import schema definition for the Excel template.
6. Stop using wildcard import in `views.py`.
7. Replace `print()` with logger calls.

### Phase D. Finish the calculation engine

1. Decide whether the modular path in `eht/cal.py` is the canonical calculation engine.
2. Remove or archive the older monolithic `eht/calculation.py` once the modular path is complete.
3. Validate the engineering formulas against your domain assumptions note.
4. Add the missing heat-loss safety factor if it is intended to be applied.
5. Confirm the correct temperature basis for maximum current calculation.
6. Confirm spiral-factor rules and minimum/maximum constraints.
7. Add vendor filtering beyond voltage, including operating and exposure temperature suitability if required.
8. Add line/service-type-specific logic if EP vs freeze protection vs process maintenance must differ.
9. Add explicit remarks or failure reasons per line when no suitable tracer is found.
10. Add deterministic sorting/selection and alternate ranking rules.

### Phase E. Build the reporting layer

1. Create a result summary model/view per project.
2. Create a process-line result page/table.
3. Create a per-line BOQ page.
4. Create a consolidated BOQ page.
5. Add export to Excel/PDF only after the stored schema is stable.
6. Add alternate tracer comparison UI and selection override flow.
7. Add project rerun/regenerate capability with versioning or overwrite rules.

### Phase F. Finish the SLD architecture

1. Define the stored graph structure for electrical relationships.
2. Decide whether `ElecEHT_TagManagement` remains the canonical SLD/tag table.
3. Generate project-wide unique tags, not per-line resets.
4. Generate SLD JSON from stored power distribution/tag data.
5. Connect `sld.html` to real project data instead of hard-coded demo data.
6. Implement coordinate persistence and reload.
7. Implement manual editing and relationship persistence only after the generated baseline works.
8. Add cold cable length update logic and alternate tracer reselection workflow.

### Phase G. Repair the UI structure

1. Convert `project_data.html` into a true partial or page, not both.
2. Stop mixing Bootstrap 4 and Bootstrap 5.
3. Move inline JS out of templates into static modules.
4. Give each action its own button type and endpoint.
5. Fix duplicate IDs and malformed HTML.
6. Build real content into the Import Input, Result, BOQ, and SLD tabs.
7. Add loading indicators and better error messaging around AJAX actions.

### Phase H. Add real auth and permissions

1. Replace placeholder login/logout/register views with Django auth flows.
2. Connect `UserAttempt` lockout logic to the actual login process.
3. Define whether projects are user-scoped or globally visible.
4. Protect download/upload/result routes consistently.

### Phase I. Improve project hygiene

1. Add unit tests for:
   - heat loss
   - tracer selection
   - power distribution
   - BOQ
   - sanitizer edge cases
2. Add integration tests for upload-to-results flow.
3. Register lookup and result models in admin for debugging.
4. Move secrets/settings to environment variables.
5. Clean up migrations and preserve a trustworthy migration history.
6. Decide whether sample DB/data files belong in repo or in fixtures.
7. Replace the nearly empty `README.md` with setup + architecture + workflow documentation.

## 11. Recommended Restart Strategy

If I were continuing this project from here, I would do it in this order:

1. Freeze the current domain assumptions.
2. Redesign result schemas and relationships.
3. Fix persistence so one full project can run end-to-end.
4. Add tests around the modular calculation path.
5. Build result and BOQ pages from stored data.
6. Only then connect SLD generation and editing.

This order minimizes rework. Right now the biggest risk is building more UI on top of unstable persistence.

## 12. Final Assessment

This is a useful codebase, not a dead one. The application intent is strong, the engineering workflow is thoughtfully outlined, and the modular calculation direction is the right foundation. The main problem is not lack of ideas; it is that the refactor was left halfway between prototype and integrated product.

In practical terms:

- You do have a recoverable base.
- You do not yet have a reliable end-to-end application.
- The next milestone should be "one project uploads, calculates, stores, and displays results correctly" before adding more features.
