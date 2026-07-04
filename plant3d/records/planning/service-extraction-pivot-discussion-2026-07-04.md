# plant3d Service-Extraction Pivot — Discussion

Date: 2026-07-04
Author: Claude, at KR's request
Status: discussion draft — Codex to react, KR to decide

## KR's Question

`plant3d` has grown from a spike into a serious engineering tool. Should it stop being "an app inside the EHT Django project" and become its own service: separate Docker container, own database, own Celery/Redis, integrated with EHT (and future engineering tools) purely via API? Rationale offered: separation of concerns, independent scalability (horizontal/vertical), and reuse of the 3D module by other future engineering tools in the ecosystem.

## Grounding: current actual coupling (checked in code, 2026-07-04)

Exactly three points, all narrow:

1. **Hard DB FK:** `SourceModel.project` → `eht.ProjectData`, `to_field='proj_id'`, **`on_delete=CASCADE`** ([models.py:15-18](../../models.py#L15)). Deleting an EHT project today silently cascades and deletes all associated `plant3d` data. This is a real hidden coupling regardless of the DB-split question.
2. **Live Python import:** `plant3d/access.py:1` — `from eht.models import ManagedProject`, used directly for project-access scoping.
3. **Form-level import:** `plant3d/forms.py` imports `ProjectData` for the upload project dropdown.

No Celery/Redis exists anywhere yet (confirmed by grep) — today's async worker is `process_plant3d_job --watch`, a management-command poller. Single shared Postgres `DATABASES["default"]` today.

## Claude's Position

**Agree with the destination. Not yet with immediate full extraction.** This is the same principle already enforced at the Django-app layer (platform neutrality, ARCH1, decision 0004, raceway's one-way `module → platform` dependency) — now being asked one layer up, at the infrastructure/deployment layer. That the question makes sense to ask is a good sign the earlier boundaries were drawn well.

### Why not the full leap right now

- **Most of the stated goals (separate container, independent scaling) are already achievable without a database split** — the "worker container role, same repo/image" pattern from the original architecture freeze already delivers this. A DB split is a much bigger, harder-to-reverse step than "run the worker in its own container," and the two shouldn't be conflated.
- **The DB split is expensive and not yet justified by concrete pressure.** Splitting means: two migration histories, no cross-table joins, and the `on_delete=CASCADE` FK above becomes literally inexpressible (Postgres cannot FK across databases) — it must become a loose reference validated by an API call. Real, valuable work, but the architecture freeze's own rule was to defer this kind of split until real pressure (a second consumer, licensing isolation, genuine release-cadence conflict, polyglot need) exists, not merely anticipated pressure. Today there is one consumer (EHT) and one team.
- **Authentication is the hardest new problem, and it isn't priced into the ask yet.** Today `plant3d` and `eht` share one Django session; `ManagedProject.available_to_user` is a direct import. Split into a separate service and `plant3d` can no longer import that function — it needs its own way to know who the user is and what they can see: either a short-lived signed token EHT issues at login (user id + accessible project ids, verified with no DB round-trip) or an internal "access" API call (now a network hop on the hot path, needs caching). This is genuine new engineering, not a footnote.
- **Team-size reality.** Two databases + a broker + cross-service auth is real ongoing operational surface (backups, migration ordering, network failure handling, API version skew) for the team actually running this. Worth paying for when the benefit is concrete.

### What's genuinely worth pulling forward now (Stage 0)

Cheap, high-leverage, valuable regardless of whether full extraction ever happens:

1. Replace the `on_delete=CASCADE` FK with a **loose `project_id` reference**, validated at write time, no cascade. Removes the one real schema-level coupling; also fixes the hidden "EHT project delete silently deletes plant3d data" landmine.
2. Replace the direct `ManagedProject` import in `plant3d/access.py` with a call through a small, explicitly named internal interface — today still a plain function call, but drawn as a seam so it becomes an HTTP call later by touching one file, not the whole app.
3. **Introduce Celery + Redis now**, replacing `--watch` polling. Already an acknowledged production gap; doing it now gets real async infra immediately and is a prerequisite for extraction either way — and it directly delivers "own celery/redis" without requiring "own database" first.

### Staged path (proposed)

- **Stage 0 (now):** the three items above. Makes `plant3d` "extraction-ready" without paying the operational tax yet.
- **Stage 1 (when a second real consumer appears, or release-cadence genuinely collides):** `plant3d` becomes its own deployable Django project — own database, own container image — but **stays in the same git repo** initially (a `services/`-style split). A monorepo with clearly separated deployables captures most of the isolation benefit (own DB, own image, independent scale/release) while keeping cross-boundary refactors and CI simple for a small team. Define a small versioned HTTP API contract for the `eht ↔ plant3d` boundary. Solve auth via the signed-token approach.
- **Stage 2 (only if clearly justified — licensing/selling the 3D engine independently, a separate team/vendor, or CI/release velocity a shared repo genuinely can't give):** split the git repo.

## Open Questions For Codex / KR

1. Does Codex see additional coupling points beyond the three found (worth a fresh grep before Stage 0 starts)?
2. Agree to do Stage 0 (loose project reference, explicit access seam, Celery+Redis) as the next infrastructure pass, ahead of/alongside raceway feature work?
3. What is the concrete trigger we'll watch for to move to Stage 1? (Candidates: raceway module reaching real usage by a second consumer; EHT needing a release that `plant3d`'s fast iteration would otherwise block; a genuine performance/resource contention incident on shared Postgres.)
4. Token-based auth vs internal access-API for the eventual Stage-1 boundary — any early preference, given the rest of the stack?

## Claude's Recommendation Summary

Endorse the destination; treat it as validation of the architecture built so far, not a rejection of it. Do Stage 0 now — it is cheap, irreversible-to-skip-later, and reduces real risk (the CASCADE landmine) independent of any future split. Defer Stage 1/2 until a concrete trigger, not an anticipated one, consistent with every prior "don't build ahead of proof" call in this project (JSON-vs-GLB, microservices-vs-monolith freeze, LOD/completeness).

## Claude — Final Review Before Go-Ahead (2026-07-04b)

KR agrees with Codex's response and is ready to say "go ahead." Asked me to hold-check before that. **No objection to the destination or staging — Codex's resequencing (FK/cascade → access seam → Celery) is correct and I endorse it as-is.** The only value I can add now is sharpening the *mechanics* of Stage 0, grounded in the actual call sites, so the coding pass doesn't hit avoidable surprises.

### Grounded findings (checked in code)

- `services.py:203` and `services.py:997` pass `source_model.project` into `parse_multiple_ifc_uploads(file_payloads, project)`, which immediately does `del project` — **these two call sites are dead weight**, zero risk to change.
- `views.py` has 4 `select_related("project")` calls — mechanical to remove/adjust.
- **The real call site: `forms.py`'s `project = forms.ModelChoiceField(queryset=ProjectData.objects.filter(proj_id__in=accessible_project_ids(user)))`.** A `ModelChoiceField` renders `<option>` tags and validates the POST against real `ProjectData` rows — it **cannot survive** a naive FK→string conversion. This is the one place where "remove the FK" is a real design decision, not a search-and-replace.
- `ProjectData.proj_id` (a unique `CharField`) appears to be the primary display identity — no separate "project name" field found nearby. Worth double-checking before assuming a bare ID is all that ever needs displaying.

### Four things to fold into Stage 0's execution (not policy disagreements — implementation completeness)

1. **The new "project seam" must cover three responsibilities, not one:** (a) access check — already exists (`accessible_project_ids`); (b) **enumerate/display** — list a user's accessible projects with a display label, needed by `forms.py`'s picker and any template showing a project; (c) **validate** — confirm a `project_id` is real at write time, replacing what the FK's referential integrity used to guarantee. If the seam only does (a), `forms.py` will either break or someone will quietly leave a direct `ProjectData` import in place, undermining the goal.
2. **Say explicitly in decision 0005: Stage 0 does not eliminate the plant3d→eht Python dependency — it relocates and confines it.** The seam's implementation will still call `eht.models.ManagedProject` internally (there's no other source of truth until Stage 1's auth exists). That's correct and intentional, but the record should say so plainly, so it isn't misread later as "already decoupled" when only the boundary line has been drawn.
3. **Removing `CASCADE` trades one risk for another, consciously.** Today: deleting an EHT project silently deletes plant3d data (bad — surprise data loss). After: a `project_id` can point at nothing (a project renamed/deleted) with no signal (silent orphaning). Validate at write time (covered by seam responsibility (c) above); a lightweight future "list plant3d sources whose project_id no longer resolves" check is worth a mental note, not urgent now.
4. **Treat the FK→string migration as schema surgery, not a pure add.** It touches `models.py`, a migration, `access.py`, `forms.py`, `admin.py`, `views.py`, and templates displaying `{{ source.project }}` — recommend a full call-site grep pass *before* writing the migration (`\.project\b`, `select_related.*project`, admin `list_display`/`list_filter`/`search_fields`), not reactive patching after tests fail. Given real saved-case data likely already exists in the dev DB, verify the migration backfills correctly before dropping the old field, and keep the project's existing check+test discipline (it already does this well).

### Verdict

None of the above changes the plan — they're the concrete details that make "remove the FK, add the seam" actually land cleanly in one pass instead of two. **No hold on go-ahead; fold points 1–4 into the Stage 0 work.**
