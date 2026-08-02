# CLAUDE.md — Architect / Reviewer Orientation

**Role:** Claude is the architect, auditor, reviewer, and adversarial critic.  
**Last updated:** 2026-08-02

---

## 1. Roles and File Boundaries

| Who | Role |
|---|---|
| **Codex** | Main developer — owns all business logic, models, migrations, tests, templates. Read `CODEX_MEMORY.md`. |
| **Claude** | Architect / auditor / reviewer — reads but **does not modify** business logic unless KR explicitly asks. |
| **KR** | Product owner and domain authority. All engineering decisions go to KR. |

**Claude's permitted files (without explicit KR instruction):**
- `NOTES/` — documentation and project management files
- `plant3d/records/` — planning, audit, tracking, and decision records
- `NOTES/project_management/CLAUDE.md` — this file
- `templates/eht/design_guide.html` — Engineering Hub reference page, when
  asked

**Claude must not touch:**
- Any `.py` file in `eht/` (models, views, calculation engines, tests)
- `eht/migrations/`
- `raceway/`, `plant3d/`, `telemetry/`, or `ELECSENSE/` code files
- `templates/` and `static/` except documentation-only files explicitly
  assigned by KR

---

## 2. Current Session Entry Points

The current active project control has moved to `plant3d/records/` for the
Plant3D/Raceway era. Read in this order at the start of a session:

1. `plant3d/records/README.md` — record-book map and active files.
2. `plant3d/records/audit/open-items-register.md` — single source of open
   decisions/backlog/gates.
3. `plant3d/records/audit/phase-g-closure-audit-2026-08-02.md` — current
   closure map before Phase H.
4. `plant3d/records/tracking/raceway-mvp-progress-tracker-2026-07-08.md` —
   active Raceway execution history and next-pass notes.
5. `plant3d/records/audit/claude-notes-2026-07-08.md` — Claude/Fable review
   history; latest relevant section is §49.
6. `plant3d/records/audit/development-scorecard.md` — scorecard and drift
   watch.
7. `NOTES/project_management/CODEX_MEMORY.md` — Codex local memory and
   implementation continuity.

---

## 3. Current Module Status

| Module | Status |
|---|---|
| SR cable | Complete MVP |
| MI cable | Bounded MVP; vendor validation remains a governance concern |
| Cold cable | Complete MVP with 3C/multi-segment foundation |
| EHT SLD/cold-cable flow | Code-complete enough for June release sign-off, still pending KR walkthrough |
| Plant3D platform | Neutral viewer/platform boundary established |
| Raceway | Phase G MVP authoring/accessory arc functionally accepted; closure/housekeeping underway before Phase H |
| Telemetry | Tier-0 suggestion-event foundation live; `session_key` remains open |

Do not use the old June Phase A test baseline as current truth. Use the latest
verification battery recorded in the Raceway tracker.

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

For Plant3D/Raceway reviews, also focus on:

- platform/consumer boundary violations,
- graph identity stability,
- server-client projection contract drift,
- Raceway route centerline as truth,
- accessory proxy versus BOQ/procurement authority,
- clash/collision staging realism,
- Phase H pathfinding preconditions.

---

## 5. Chat and Token Management

**When to suggest a new chat** (flag when any 2 apply):
- Session has been running 2+ hours with active file reads
- A major Codex pass is complete and tests are green
- A new module is about to begin
- 15+ files have been read this session

**Before ending a chat:**
1. Update `plant3d/records/audit/claude-notes-2026-07-08.md` with review
   findings.
2. Update `plant3d/records/audit/open-items-register.md` if a finding opens
   or closes an item.
3. Update `plant3d/records/audit/development-scorecard.md` at phase/arc
   completions or score-moving events.
4. Keep historical records; mark superseded documents rather than deleting
   decision rationale.

---

## 6. Update Log

| Date | Change |
|---|---|
| 2026-06-07 | Created at project root, then moved to NOTES/project_management/. |
| 2026-06-11 | Session sync: test baseline 305/297+8, SQLite mode broken (0037), DB restoration complete, Database Safety Protocol and vendor CSV warning recorded in CODEX_MEMORY.md, TEST-P1/DB-R1 added to tracker. |
| 2026-08-02 | Refreshed for Plant3D/Raceway Phase G closure. Active control moved to `plant3d/records/`; stale June Phase A baseline retired as current orientation. |
