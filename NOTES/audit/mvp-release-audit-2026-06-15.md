# eTrace MVP — Final Non-Invasive Release-Readiness Audit

| | |
|---|---|
| **Auditor** | Claude (architect / reviewer / engineering critic) |
| **Date** | 2026-06-15 |
| **Scope** | SR/MI tracer selection + cold cable + SLD + BOQ/cable-schedule path |
| **Out of scope** | Constant Power tracer, 3D/model routing, IDF/PCF/IFC viewer (inspected only for release interference), full multi-tenant isolation |
| **Method** | Read-only. No code, data, migration, settings, vendor row, project row, or generated output was modified. The only database access was `SELECT`-class read queries against `eht_local`. |
| **Baseline referenced** | SQLite 360 tests (2026-06-15); PostgreSQL 320 tests (independently verified); `manage.py check` clean |

---

## 1. Executive Verdict

### **CONDITIONAL GO** for external engineering review.

The calculation engine is genuinely sound: heat-loss, SR selection, MI fallback, and the cold-cable Feeder/Branch optimizer are correctly implemented, heavily instrumented with rejection diagnostics, and honest about their documented simplifications. Architecture (clean module separation, FK integrity, transaction boundaries, per-user project scoping in read paths) is solid for the stated low-concurrency, single-company target.

**The blockers are not in the math — they are in data governance and a few security/hygiene items:**

1. The live MI catalogue validation gate is *open* on two families that were never row-approved by KR, contradicting the project's own gate.
2. Two vendors with fabricated / unverifiable SR data are user-selectable, with no SR validation gate.
3. A real user password hash and a backup database are committed to git.
4. Two workspace-mutating endpoints skip the project-authorization check that every other endpoint enforces.

All four are low-effort to close. Fix those and the MVP is defensible in front of an external reviewer.

---

## 2. Score Matrix (1–10)

| Area | Score | Note |
|---|:---:|---|
| Electrical engineering correctness | **8** | Correct formulas, conservative defaults, documented assumptions |
| Catalogue / vendor data readiness | **4** | MI gate drift + selectable fabricated SR data + no SR gate |
| Cold cable engineering | **8** | Real volume-minimizing optimizer; earth-loop non-conservatism disclosed |
| SLD / edit workflow | **8** | Hardened, audited, review-only overrides; label-overlap is a manual gate |
| BOQ / cable schedule readiness | **7.5** | Credible quantities, dedup, lifecycle audit; procurement-light |
| Software architecture | **8** | Good separation, FK cascade integrity, project scoping in read paths |
| Runtime reliability | **7.5** | Broad guards; two authz/path fragilities |
| Security / deployment readiness | **6** | Strong controls, but git secret exposure + authz gap + dep-hygiene pending |
| UX / user trust | **7.5** | Strong diagnostics and review labels; visual gates open |
| Documentation / traceability | **8** | Extensive, worked examples, alignment tests; minor drift |
| **Overall MVP release readiness** | **7** | **CONDITIONAL GO** |

---

## 3. Top 10 Findings

### F1 — BLOCKER · Live MI validation gate is open without documented KR approval
- **Evidence:** read-only `eht_local` query — `THR/MIQ is_validated=True (21 heaters)`, `CHR/MI-825B is_validated=True (23 heaters)`, `nVN/XMI-A62 is_validated=False`. The reseed note (VDV-P1) and R-011/R-018 state **all** MI families must remain `False` until KR row-by-row review.
- **Risk:** `mi_selection.get_mi_heater_options` selects only `is_validated=True` families, so in production **MI auto-fallback will fire for THR/CHR using data that was reseeded from official docs but never row-approved**, and present it to a reviewer as "selected."
- **Action:** KR must explicitly decide — either record formal row approval, or re-close the gate (`is_validated=False`) through an approved data-change path. Do not ship in the current ambiguous state.

### F2 — HIGH · Fabricated/unverifiable SR vendor data is user-selectable, with no SR validation gate
- **Evidence:** `SELECT_VENDOR` offers Thermon / Chromalox / **nVent** / SST / **KRUS-Zapad**. SR validation found nVent SR rows fabricated (max-exposure 204 °C vs real ~85 °C — *dangerously non-conservative*) and 16 Krus-Zapad rows unverifiable. `tracer_selection` / `fetch_vendor_data` apply **no `is_validated` filter** to SR rows (unlike MI).
- **Risk:** a user who selects nVent gets silently wrong, unsafe selections.
- **Action:** for MVP, restrict the vendor dropdown to verified vendors (THR, CHR, SST) **or** add an SR readiness/validation warning gate. Default (THR) is verified-good, so this is a low-risk restriction.

### F3 — HIGH · Credential hash and backup DB committed to git
- **Evidence:** `git ls-files` → `data_dump.json` (contains 1 `auth.user` with `pbkdf2_sha256$...` hash + project/vendor data) and `db.sqlite3.bak` (1 MB) are **tracked**. `.gitignore` has `*.sqlite3`, which does **not** match `db.sqlite3.bak`.
- **Risk:** offline hash cracking + valid username disclosure if the repo is ever shared/pushed.
- **Action:** add `*.bak` / `data_dump.json` to `.gitignore`, `git rm --cached` both, and **rotate that user's password** (the hash is already in history). Critical before the repo is pushed anywhere shared.

### F4 — HIGH · Cross-project mutation authorization gap
- **Evidence:** `calculate_view` (upload — *clears and replaces* a project's workspace) and `confirm_valid_data` (confirm + recalculate) do **not** call `_get_project_workspace_context` / `available_to_user`, while `result_view`, all SLD apply/override views, and `base` **do** (raising `Http404`).
- **Risk:** a non-staff authenticated user who knows a `project_id` they aren't assigned to could destroy/replace that project's data.
- **Action:** add the existing `ManagedProject.available_to_user(...).filter(proj_id=...)` gate to both endpoints (~2 lines each, consistent with the rest of the code).

### F5 — MEDIUM · Production secret/DEBUG posture depends entirely on env discipline
- **Evidence:** `settings.py` — `DEBUG` defaults **True**; `SECRET_KEY` falls back to a hardcoded `django-insecure-...`. RELEASE-P1 made these env-driven and a production-shaped `check --deploy` passes, but nothing fails closed if env vars are missing at deploy.
- **Action:** deployment runbook must set `DEBUG=false`, real `SECRET_KEY`, `ALLOWED_HOSTS`, HTTPS/HSTS/secure-cookie vars. Consider failing startup if `DEBUG=false` and `SECRET_KEY` is the dev default.

### F6 — MEDIUM · MI temperature/inrush correction is currently inert
- **Evidence:** `MIAlloyTempFactor` table is empty and heaters have `tcr_per_degree_c=None`, so `_resistance_multiplier_for_temperature` returns `1.0`; MI cold-start current ≈ nominal (no resistance elevation at energization). Already parked.
- **Action:** acceptable for MVP *if* MI is fallback-only and the limitation is visible. Keep the T-class "review" verdict (it correctly never auto-approves sheath temperature).

### F7 — MEDIUM · Earth-loop non-conservatisms stack
- **Evidence:** `check_fault_l_pe` excludes tracer PE-path resistance (R-003) and `_source_impedance_value_and_notes` uses the positive-sequence source impedance `V_phase/(I_3ph)` as the L-PE source term. Both *raise* computed fault current vs reality (tripability can look better than it is).
- **Action:** keep the non-conservative warning prominent on results. Disclosed and acceptable for MVP, but it must remain visible, not buried.

### F8 — MEDIUM · Error-file path is relative on write, absolute on read
- **Evidence:** `sanatize_input.ERROR_FILE_DIR = 'file_storage/error_file'` (relative to CWD) for writes; `download_error_file` resolves `settings.BASE_DIR / 'file_storage' / 'error_file'`. If the WSGI process CWD ≠ `BASE_DIR`, written error files won't be downloadable.
- **Action:** anchor the writer to `settings.BASE_DIR`. Low runtime risk under typical gunicorn/Docker working dir, but fragile.

### F9 — LOW/MEDIUM · Dependency hygiene pass not completed (SEC-P1b open)
- **Evidence:** no recorded CVE / `pip-audit` run; both `psycopg==3.3.3` and `psycopg2-binary==2.9.11` are pinned (redundant — only psycopg3 is used). Versions otherwise look current.
- **Action:** run `pip-audit` / `safety` once before public exposure; drop the unused `psycopg2-binary`.

### F10 — LOW · Dead code, doc drift, minor info disclosure
- **Evidence:** `sanatize_input.py` ships dead `index` / `index2` views and a stale `log_failed_attempt(session, user)`; `NOTES/project_management/CLAUDE.md` snapshot says "Django 4.2" while `requirements.txt` pins `Django==5.2.13` and "test baseline 305" vs current 360; landing page (`index`, public `/`) passes `admin_site_path` into context (template should gate it to staff).
- **Action:** cosmetic cleanup; reconcile the snapshot tables; confirm the landing template hides the admin link from anonymous users.

---

## 4. Mandatory Before External Review

1. **F1** — Resolve the MI `is_validated` discrepancy (approve rows or re-close the gate). *Data decision, KR.*
2. **F2** — Remove unverified vendors (nVent, KRUS-Zapad) from selectable list **or** gate/warn unvalidated SR. *Small code/config.*
3. **F3** — Untrack `data_dump.json` + `db.sqlite3.bak`, fix `.gitignore`, rotate the exposed user password. *Hygiene.*
4. **F4** — Add the project-authorization check to `calculate_view` and `confirm_valid_data`. *~4 lines.*
5. **F5** — Confirm the deployment env sets `DEBUG=false`, real `SECRET_KEY`, hosts, HTTPS/HSTS/cookies (already supported; just must be set). *Runbook.*

---

## 5. Acceptable for MVP With Documented Limitation

- Earth-loop excludes tracer PE resistance and uses positive-sequence source Z (F7) — **disclosed, keep warnings visible.**
- MI temperature/inrush correction inert (F6) — **acceptable as fallback-only with limitation note.**
- MI T-class is review-only, not a calculated sheath-temperature approval — **correct and conservative.**
- Cold-cable Cu-only, Method E only, PF=1.0 / reactance ignored, single-phase basis — **documented frozen decisions.**
- Heat-loss cold face approximated as ambient (neglects surface film) — **conservative (slightly overestimates loss); fine.**
- Cable schedule is procurement-light (route/drum/lot annotations only) — **deferred by KR decision.**
- Upstream main-breaker / spare-capacity coordination not built — **deferred; branch panel summary is review evidence.**

---

## 6. Post-MVP Backlog

- SR vendor curve-point interpolation; SR `is_validated` model gate symmetric with MI.
- Populate `MIAlloyTempFactor` / per-heater TCR → real MI inrush.
- Tracer PE-path impedance + short-circuit withstand sizing.
- Full procurement schedule snapshot with Draft/Issued revision semantics.
- Additional installation methods (D2 etc.) with validated catalogue rows.
- Anchor all file I/O to `BASE_DIR`; fail-closed startup on default secret in prod.
- `django-admin-honeypot` / 2FA / edge IP restriction for admin (defense-in-depth, already planned).

---

## 7. Voltage-Drop Optimization — Special Report

**KR's suspicion (that the optimizer may not optimize and instead distributes VD equally) is NOT supported by the code.** The implementation performs a genuine total-conductor-volume minimization, not an equal-VD split.

### What the code actually does — `optimise_cable_pair`, `eht/cold_cable.py:1052`
1. Enumerates **every** ampacity-qualified feeder size (catalogue ascending).
2. For each feeder size, computes the feeder VD, then for each branch greedily picks the **smallest** branch cable whose `vd_feeder% + vd_branch% ≤ allowable` **and** that passes the L-PE fault check (`_select_3c_segment_for_voltage_drop`, `eht/cold_cable.py:947`; candidates ordered ascending by `conductor_size_mm2` at `eht/cold_cable.py:518`, so "first that fits" = smallest).
3. Scores each feeder option by `option_cost = 3·size_feeder·L_feeder + Σ 3·size_branch·L_branch` (copper volume) and keeps the global minimum (`eht/cold_cable.py:1145`).

This is **not** equal distribution. The branch receives *whatever budget remains after the feeder* (greedy), and the feeder size is chosen by exhaustive cost search. Because the branches are independent given a fixed feeder, enumerate-feeder × min-branch is **globally optimal over the catalogue** for the copper-volume objective.

### Why it can *look* like "equal distribution" (the likely source of the suspicion)
- For typical short cold cables the VD budget is slack, so both feeder and branch land at the **catalogue-minimum** size (e.g., 2.5/2.5). That's a flat-looking result, but it's the correct minimum, not an enforced split.
- The objective is **copper volume**, not VD-balancing and not monetary cost. With non-linear catalogue pricing, "min volume" ≠ "min price," but volume is a defensible proxy.

### Verdict
The optimization is real and correct for its stated objective. No equal-VD-splitting logic exists anywhere (the only optimize path is `optimise_cable_pair`; the no-JB path `select_direct_3c_cable` simply picks the smallest cable passing VD+fault). **Recommendation:** document the objective explicitly ("minimizes total conductor volume across feeder+branch") so the flat-when-slack behavior isn't misread as a non-optimizing bug.

---

## 8. Catalogue Validation — Special Report

**Is SR/MI catalogue status safe enough for MVP review? Only if scoped to verified vendors and the MI gate is resolved.**

Live `eht_local` (read-only):

| Vendor (selectable) | SR rows | SR status | MI rows | MI `is_validated` |
|---|:---:|---|:---:|---|
| Thermon (THR, default) | 9 | HTSX/VSX verified good | 21 | **True** ⚠ (not row-approved) |
| Chromalox (CHR) | 6 | SRM/E verified good | 23 | **True** ⚠ (not row-approved) |
| nVent (nVN) | 8 | **fabricated** (exp 204 vs ~85 °C) | 28 | False ✅ (gated off) |
| SST | 10 | BTC/BTX verified good | – | – |
| KRUS-Zapad (KRZ) | 16 | **unverifiable** | – | – |

> 9 additional SR rows under Eltherm / Heat Trace / Pentair exist in the table but are **not** in the vendor dropdown, so they are unreachable — good.

### What KR must manually approve before external review
1. **MI gate (F1):** confirm/approve THR/MIQ and CHR/MI-825B rows, or set `is_validated=False`. The current True-state is the single most important data risk.
2. **Vendor exposure (F2):** decide whether nVent and KRUS-Zapad remain selectable. Recommendation: hide them for MVP (fabricated/unverifiable SR data, no SR validation gate to stop selection).
3. Record the final approved catalogue state in the tracker (CAT-P1 close-out).

### Engine isolation is correct
Vendor filtering maps code→name (`resolve_selected_vendor` → `fetch_vendor_data(Vendor__iexact=...)`), SR ignores legacy `Tracer_Family='MI'` rows, and the divergent `elecEHT_Vendor.csv` import is blocked behind `--execute` + exact confirmation text. The risk is purely *which rows are exposed/trusted*, not contamination across vendors.

---

## 9. Security / Deployment — Special Report

### Strong, already-implemented controls
- Login lockout (`UserAttempt`, 3 strikes / 30 min) + `django-ratelimit` (IP & username).
- Generic auth errors (no user enumeration).
- `next` redirect validated via `url_has_allowed_host_and_scheme`.
- Self-registration returns HTTP 410.
- Upload hardening: 10 MB cap, extension + `guess_type` + `content_type` + **ZIP/XLSX magic-byte** + filename-traversal guard.
- `download_error_file` path-traversal hardened (`basename` + `is_relative_to`).
- Configurable `DJANGO_ADMIN_PATH`; `LoginRequiredMiddleware` covering all non-exempt paths.
- `django-easy-audit` model-change logging; env-driven HSTS/SSL/secure-cookies.

### Minimum safe checklist before a Cloudflare/public tunnel review
- [ ] **F3** done: secrets/backup DB removed from git; exposed password rotated.
- [ ] **F4** done: authz on `calculate_view` + `confirm_valid_data`.
- [ ] `DEBUG=false`, real `SECRET_KEY`, explicit `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS` (F5).
- [ ] `SECURE_SSL_REDIRECT` / HSTS / `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` on.
- [ ] **`SECURE_PROXY_SSL_HEADER` set for Cloudflare** — not found in `settings.py`. Behind a TLS-terminating proxy, set `SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")` so `request.is_secure()` is correct and `SECURE_SSL_REDIRECT` does not loop.
- [ ] Non-default `DJANGO_ADMIN_PATH` + Cloudflare/IP restriction on `/admin/`.
- [ ] `pip-audit` clean (F9).
- [ ] Confirm `.env` is not baked into the Docker image.

---

## 10. Manual End-to-End Test Script (one representative project)

1. **Setup:** create a project; vendor **Thermon (THR)**; set ambient/voltage/area-class/T-class, EHT DB fault rating, allowable VD, RCD provided. Confirm grouped form sections + help text render.
2. **Upload:** import a line list with valid + a few invalid rows (one with `Oper_T < Maint_T`). Confirm invalid rows rejected with `Maint_T ≤ Oper_T ≤ Design_T` message, error workbook downloads, valid rows stored pending.
3. **Confirm + calculate:** confirm pending rows; verify "Last calculated" timestamp appears.
4. **Results:** check per-line heat loss, SR selection, an SR rejection diagnostic line, and (if any line exceeds SR limits) an MI fallback row labeled *automatic* fallback — **note whether MI shows "selected" (F1 sensitivity).**
5. **Cold cable:** verify Feeder/Branch sizes, VD%, L-PE fault status, mass, and the **startup-VD review note** when startup VD > threshold. Confirm review-required appears for default-length basis.
6. **Panel/load summary:** sanity-check MCB count, breaker distribution, load current.
7. **BOQ + Cable schedule:** verify quantities; export **Download Visible** vs **Full Audit**; confirm shared-feeder dedup legend and hidden procurement columns.
8. **SLD:** open workspace; verify badges (missing length / review / override); do one **Combine** and verify cold-cable resize impact + review warning; **Shift+F** fit-all; export PDF and check title block.
9. **Overrides:** apply a tracer override → confirm it's labeled **"Review-only: load/BOQ/cable sizing not recalculated."**
10. **Verification report:** render for one SR and one MI line; **manually cross-check terminal voltage** against `V − (VD_feeder + VD_branch)` (open checklist item).
11. **Exports:** open every Excel/PDF; confirm freeze panes/auto-width and no internal-note leakage.
12. **Isolation spot-check:** as a non-staff user assigned to only this project, hit another project's `/results/?project_id=...` → expect 404; try uploading to a non-assigned `project_id` → **today this is the F4 gap; should 404 after fix.**

---

## 11. Final Recommendation to Codex (release-focused fixes only)

Short list, all low-risk:

1. **F4** — Add `ManagedProject.available_to_user` gate to `calculate_view` and `confirm_valid_data` (mirror `_get_project_workspace_context`).
2. **F2** — Restrict `SELECT_VENDOR` to verified vendors (THR/CHR/SST) for MVP, or add an SR unvalidated-vendor warning.
3. **F3** — `.gitignore` `*.bak` / `data_dump.json`; `git rm --cached` both (KR rotates the password).
4. **F8** — Anchor `ERROR_FILE_DIR` to `settings.BASE_DIR`.
5. **Settings** — Add `SECURE_PROXY_SSL_HEADER` for Cloudflare; optionally fail-closed if prod + dev `SECRET_KEY`.
6. **F10** — Remove dead `index` / `index2` / stale `log_failed_attempt` from `sanatize_input.py`; drop `psycopg2-binary`.

**Data decisions for KR (not Codex):** F1 (MI validation gate) and the vendor-exposure policy in F2.

---

## Appendix A — Evidence Index (files/functions inspected)

| Area | Source of truth |
|---|---|
| Heat loss | `eht/calculations/heat_loss.py` — `calculate_heat_loss`, `calculate_accessory_adders`, `calculate_insulation_conductivity` |
| SR selection | `eht/calculations/tracer_selection.py` — `get_tracer_options`, suitability/voltage/coefficient filters |
| MI selection | `eht/calculations/mi_selection.py` — `get_mi_heater_options`, `_is_family_suitable`, `_evaluate_single_phase_candidate` |
| Orchestration / fallback | `eht/cal.py` — `orchestrate_calculations`, `_sr_fallback_selection_mode`, `_mi_selection_result` |
| Cold cable / VD optimize / fault loop | `eht/cold_cable.py` — `optimise_cable_pair`, `select_direct_3c_cable`, `check_fault_l_pe`, `calculate_vd`, ampacity candidates |
| Pipeline / vendor resolution | `eht/pipeline.py`, `eht/data_service.py` — `run_project_calculations`, `fetch_vendor_data` |
| BOQ | `eht/calculations/boq.py` — `compute_bill_of_quantities` |
| Upload security | `eht/sanatize_input.py` — `sanitize_file_basic_check`, `sanitize_file` |
| Views / authz / security | `eht/views.py` — `calculate_view`, `confirm_valid_data`, `download_error_file`, `my_login`, `my_register`, `_get_project_workspace_context`, SLD override/topology views |
| Access model | `eht/models.py` — `ManagedProject.available_to_user`, `ProjectData` |
| Middleware / URLs / settings | `eht/middleware.py`, `eht/urls.py`, `ELECSENSE/settings.py` |
| Import safety | `eht/management/commands/import_data_from_file.py` |
| Live catalogue state | read-only `eht_local` `SELECT` queries (MI families, cold-cable catalogue, vendor distribution) |

## Appendix B — Severity Legend

| Severity | Meaning |
|---|---|
| **BLOCKER** | Must fix before MVP external engineering review |
| **HIGH** | Strongly recommended before release if low-risk |
| **MEDIUM** | Record and schedule soon; not necessarily release-blocking |
| **LOW** | Polish or post-MVP |
| **DEFER** | Valid idea, outside MVP scope |
