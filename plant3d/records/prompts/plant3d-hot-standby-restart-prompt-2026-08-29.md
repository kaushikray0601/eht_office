# Plant3D/Raceway Hot-Standby Restart Prompt

Use this when restarting Codex or Claude/Fable after the 2026-08-29 pause.

We are returning to `/home/kr/mydev/eht_office` after pausing
Plant3D/Raceway. Phase G Raceway MVP is implementation-closed. Claude/Fable
§53 approved the closure and confirmed H-A1 may start with A1/A2/A3 carried
explicitly.

Read first:

1. `CLAUDE.md`
2. `NOTES/project_management/CLAUDE.md`
3. `NOTES/project_management/CODEX_MEMORY.md`
4. `plant3d/records/README.md`
5. `plant3d/records/audit/hot-standby-pause-index-2026-08-29.md`
6. `plant3d/records/audit/open-items-register.md`
7. `plant3d/records/audit/phase-g-final-acceptance-brief-2026-08-28.md`
8. `plant3d/records/audit/claude-notes-2026-07-08.md`, especially §53
9. last entries of `plant3d/records/tracking/raceway-mvp-progress-tracker-2026-07-08.md`
10. `plant3d/records/planning/raceway-clash-pathfinding-staging-2026-08-28.md`

Then run `git status --short` and do not revert user/Claude changes.

Next coding pass:

- start Phase H-A1 server-side routing foundation,
- create `raceway.routing`,
- build deterministic shortest path over saved Raceway topology,
- use durable edge keys: `start_node_key::end_node_key`,
- make edge weight injectable from the first pass,
- start with length-only cost,
- add route preview JSON endpoint,
- pin the route preview payload contract in Python tests.

Do not start in the first pass:

- route persistence,
- assignment UI,
- direct EHT imports in Raceway,
- mesh/BVH/narrow-phase collision,
- vendor accessory workflow,
- large JS interaction refactor.

Open KR decisions:

- A1: catalogue seed blessing,
- A2: workspace-file cleanup,
- A3: CI go-ahead.

Verification re-warm:

- `node --test raceway/static/raceway/js/raceway_projection_core.test.js`
- `env USE_POSTGRES=false venv/bin/python manage.py test raceway --noinput -v 1`
- `env USE_POSTGRES=false venv/bin/python manage.py test plant3d --noinput -v 1`
