# EHT Refactor Task Tracker

This tracker is derived from [CODEBASE_REVIEW_2026-04-17.md](/home/kr/mydev/eht_office/NOTES/CODEBASE_REVIEW_2026-04-17.md:1) and is intended to be worked through in order.

- [x] Task 1: Stabilize result persistence for the current calculation payloads so calculations can complete without runtime storage errors.
- [x] Task 2: Redesign result models so persisted rows are project-safe and line-safe instead of overwriting by tracer catalog ID, and so BOQ data can be stored as real line items instead of being skipped.
- [x] Task 3: Finish the partial-invalid upload flow so "proceed with valid rows" actually runs calculations and stores outputs.
- [x] Task 4: Fix project setup constraints, then correct project setup UX to use an admin-managed project dropdown and remove tracer-family from global setup.
- [x] Task 5: Normalize the calculation pipeline contracts and remove duplicate old/new code paths that drifted during the refactor.
- [x] Task 6: Build usable result and BOQ views on top of persisted calculation data.
- [ ] Task 7: Connect the SLD prototype to real stored project/component relationships.
- [ ] Task 8: Add automated test coverage for import, calculation, persistence, and reporting flows.

Carry-over items:
- [ ] Add deeper domain/business-rule validation for `ProjectData` so admin-created setup/templates fail early on engineering constraints instead of only on field/model-level validation.
