# CLAUDE.md

This is the auto-loaded orientation stub for Claude Code.

- **Full architect/reviewer brief:** `NOTES/project_management/CLAUDE.md`
- **Codex developer memory:** `NOTES/project_management/CODEX_MEMORY.md`
- **Plant3D/Raceway record book:** `plant3d/records/README.md`
- **Active Raceway tracker:** `plant3d/records/tracking/raceway-mvp-progress-tracker-2026-07-08.md`
- **Open items register:** `plant3d/records/audit/open-items-register.md`
- **Claude/Fable running notes:** `plant3d/records/audit/claude-notes-2026-07-08.md`

Read these before starting any session work.

---

## Quick Facts

- **Project:** eTrace / ELECSENSE — Django engineering platform with EHT,
  neutral Plant3D model viewer, and peer `raceway` app.
- **Current focus:** Phase G closure for Raceway MVP before Phase H cable
  assignment/pathfinding.
- **Closure audit:** `plant3d/records/audit/phase-g-closure-audit-2026-08-02.md`.
- **Claude role:** Architect / auditor / reviewer / independent researcher.
- **Codex role:** Main developer and implementation owner.
- **KR role:** Product owner and electrical engineering authority.
- **Current testing norm:** use the verification commands recorded in the
  latest Raceway tracker entry; do not rely on the old June EHT baseline.
- **Important boundary:** `plant3d` is the neutral platform; `raceway`, `eht`,
  and future modules are peer consumers. `raceway` must not import EHT models
  directly, and `plant3d` must not runtime-import `raceway`.
