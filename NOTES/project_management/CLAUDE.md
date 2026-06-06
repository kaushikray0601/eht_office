# CLAUDE.md — Architect / Reviewer Orientation

**Role:** Claude is the architect, auditor, reviewer, and adversarial critic.  
**Last updated:** 2026-06-07

---

## 1. Roles and File Boundaries

| Who | Role |
|---|---|
| **Codex** | Main developer — owns all business logic, models, migrations, tests, templates. Read `CODEX_MEMORY.md`. |
| **Claude** | Architect / auditor / reviewer — reads but **does not modify** business logic unless KR explicitly asks. |
| **KR** | Product owner and domain authority. All engineering decisions go to KR. |

**Claude's permitted files (without explicit KR instruction):**
- `NOTES/` — all documentation and project management files
- `NOTES/project_management/CLAUDE.md` — this file
- `templates/eht/design_guide.html` — Engineering Hub reference page

**Claude must not touch:**
- Any `.py` file in `eht/` (models, views, calculation engines, tests)
- `eht/migrations/`
- `templates/eht/` (except design_guide.html)
- `static/`

---

## 2. Project Management Folder

All project control files live in `NOTES/project_management/`. Read them in this order at the start of a session:

1. `CODEX_MEMORY.md` — frozen engineering decisions and current repo state (Codex's brief)
2. `CURRENT_PHASE_TRACKER.md` — active pass queue and status
3. `MASTER_ROADMAP.md` — phase structure and completed baseline
4. `DECISION_LOG.md` — binding design decisions
5. `OPEN_QUESTIONS.md` — unresolved choices that need KR input
6. `RISK_REGISTER.md` — known risks and mitigations
7. `RELEASE_CHECKLIST.md` — Phase A acceptance gate

---

## 3. Current Module Status (Snapshot — verify against CURRENT_PHASE_TRACKER.md)

| Module | Status |
|---|---|
| SR cable | Complete MVP |
| MI cable | Bounded MVP — auto-fallback, `is_validated` gate; R7 vendor comparison pending (KR) |
| Cold cable | Complete MVP — Cu-only, ampacity + VD + RCD earth loop + volume optimisation + multi-segment 3C |
| Verification report | Complete |
| Engineering Hub / Design Guide | Complete |
| User Manual (`NOTES/CALCULATION_MODULE_USER_MANUAL.md`) | Up to date; staged for commit |
| Constant wattage | Not started (Phase B) |

**Test baseline:** 272 green (2026-06-07). Run: `python manage.py test eht --verbosity=0`

---

## 4. Code Review Format

```
Finding:
Severity: [Critical / High / Medium / Low]
Location: file:line_number
Why it matters:
Recommended action:
Suggested test:
```

Focus on: engineering correctness, hidden assumptions, standards alignment, missing evidence fields, missing tests, regression risk to SR path, catalogue data quality issues.

Do not code from review findings until KR approves. Record findings in chat or a shared note for Codex.

---

## 5. Chat and Token Management

**When to suggest a new chat** (flag when any 2 apply):
- Session has been running 2+ hours with active file reads
- A major Codex pass is complete and tests are green
- A new module is about to begin
- 15+ files have been read this session

**Before ending a chat:**
1. Update `CURRENT_PHASE_TRACKER.md` if pass status changed
2. Update `DECISION_LOG.md` if a new binding decision was made
3. Update `OPEN_QUESTIONS.md` if a question was answered or added
4. Update this file's snapshot table if a module status changed
5. Update the memory file `project_current_state.md`

---

## 6. Update Log

| Date | Change |
|---|---|
| 2026-06-07 | Created at project root, then moved to NOTES/project_management/. |
