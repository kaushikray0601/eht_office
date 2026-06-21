# Claude General Review - 2026-06-18

Source: user-provided Claude review attachment pasted into the Codex session on 2026-06-18.

## Current Status

- The app is mounted at `/idfviewer/`.
- Upload -> parse -> render -> optional save -> library/download is a complete loop for IDF and PCF.
- IDF parsing handles negative metadata records, inherited `-30` pipeline references, continuation lines, and known false Record 90 origin outliers.
- PCF parsing captures richer block metadata including tracing/insulation specs, bores, end types, and tee main/branch geometry.
- IFC parsing uses IfcOpenShell and returns preview mesh geometry plus metadata; IFC save is intentionally blocked.
- Persistence uses SHA-256 content signatures, idempotent re-save, conflict detection, force replace, duplicate cleanup, transactions, bulk creation, and `IDFFileSaveEvent`.
- Nearest-structure analysis compares pipeline line geometry against IFC raw bounding boxes and warns on likely coordinate-frame mismatch.

## Findings

1. The idfviewer test suite was red because `LoginRequiredMiddleware` redirected unauthenticated view tests to login.
2. Some root-level documentation drifted from the current implementation state.
3. IDF/PCF/service rebuild/analysis paths assume `mm -> m` with a hardcoded `0.001` scale, while IFC preview uses `1.0`.
4. `_filter_scene` can drop valid local-origin geometry below the current low-limit threshold.
5. Folder provenance is still weak because upload handling collapses paths to basename only.
6. Project scoping is not yet aligned with the managed-project access rules used elsewhere in the EHT app.
7. `PlotPlanOverlay` exists in the data model, but the viewer overlay remains browser-only.
8. The frontend depends on CDN-hosted Three.js and Tailwind, which is a deployment risk for offline or plant-network use.
9. UIDs are per-file rather than globally unique across a combined scene.

## Codex Follow-Up

- Auth-related view tests were updated to log in with a test user instead of relaxing production middleware.
- The idfviewer test suite was rerun successfully: 17 tests run, 16 passed, 1 skipped because the optional sample IFC file is absent.
- A fresh in-app records structure was added under `idfviewer/records/`.
- Naming recommendation was recorded as a decision: keep the Django app name `idfviewer` for now, and rename the product-facing module later.
