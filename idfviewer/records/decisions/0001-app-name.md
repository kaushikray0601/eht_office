# Decision 0001 - Keep Django App Name For Now

Date: 2026-06-18

## Decision

Keep the Django app/package name as `idfviewer` for the current MVP and next development pass.

Use broader product-facing language in UI/docs, such as "Engineering Model Viewer", "Pipeline Model Viewer", or "Model-Assisted EHT Workspace", without renaming the Django app yet.

## Rationale

The implementation has expanded beyond IDF into IDF, PCF, IFC preview, persistence, analysis, and future EHT model-routing workflows. The name `idfviewer` is therefore no longer conceptually complete.

However, renaming the Django app now would touch:

- `INSTALLED_APPS`
- URL namespaces and route names
- migration app labels and historical migration dependencies
- database table names and content types
- template/static paths
- imports across views, tests, services, and parsers
- any saved records or references that assume the old app label

That is too much churn during the final MVP release stage and before the 3D module direction is stable.

## Consequence

`idfviewer` remains the internal legacy app label. We can introduce a new user-facing module name immediately in docs/UI copy, then consider a controlled rename or replacement app only after MVP release and after the database migration strategy is planned.

