# EHT Refactor Task Tracker

This tracker is derived from [CODEBASE_REVIEW_2026-04-17.md](/home/kr/mydev/eht_office/NOTES/CODEBASE_REVIEW_2026-04-17.md:1) and is intended to be worked through in order.

- [x] Task 1: Stabilize result persistence for the current calculation payloads so calculations can complete without runtime storage errors.
- [x] Task 2: Redesign result models so persisted rows are project-safe and line-safe instead of overwriting by tracer catalog ID, and so BOQ data can be stored as real line items instead of being skipped.
- [x] Task 3: Finish the partial-invalid upload flow so "proceed with valid rows" actually runs calculations and stores outputs.
- [ ] Task 4: Fix project setup constraints, including hard-coded project IDs, invalid defaults, and form/model mismatches.
- [ ] Task 5: Normalize the calculation pipeline contracts and remove duplicate old/new code paths that drifted during the refactor.
- [ ] Task 6: Build usable result and BOQ views on top of persisted calculation data.
- [ ] Task 7: Connect the SLD prototype to real stored project/component relationships.
- [ ] Task 8: Add automated test coverage for import, calculation, persistence, and reporting flows.
