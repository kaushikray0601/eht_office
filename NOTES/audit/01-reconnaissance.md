# EHT Audit — Session 1: Reconnaissance
_Date: 2026-05-18_
_Auditor: Claude (Anthropic), via Claude Code_

---

## 1. Repo Topology

**Single Django project.** No microservices. No Docker.

| Layer | Detail |
|---|---|
| Django project config | `ELECSENSE/` (settings, urls, wsgi, asgi) |
| Primary engineering app | `eht/` — heat-loss calc, SR selection, SLD, BOQ, cable schedule, views, models |
| 3D model viewer app | `idfviewer/` — IDF/PCF/IFC parsing and visualization |
| Calculation subpackage | `eht/calculations/` — heat_loss, tracer_selection, power_distribution, boq, tag_management |
| Root-level artefacts | `manage.py`, `requirements.txt`, `db.sqlite3` (active dev DB committed to repo), `IDF/` (real isometric files), `NOTES/`, `static/`, `templates/` |
| Discarded code | `eht/tmp/discardedCodes/calculation.py` (437 LOC, old calc orchestrator) |
| Loose scripts | `generate_mi_doc.py`, `parse_meta.py` at root — appear to be one-off tools |

**No docker-compose file exists** in the repo at any level. No container definition found.

---

## 2. Docker Topology

**None.** No docker-compose.yml, no Dockerfile, no compose/ directory. Deployment mechanism is unspecified by the repo. Dev runs directly with Django dev server against SQLite or a remote Postgres instance (IP `129.151.129.146` hardcoded in settings.py).

---

## 3. Implementation Status Check

| Feature (claimed/planned) | Status | Evidence |
|---|---|---|
| FastAPI microservices | **NOT PRESENT** | Not in `requirements.txt`; zero `.py` files import or reference FastAPI |
| django-fsm workflow | **NOT PRESENT** | Not in `requirements.txt`; no `.py` reference; workflow/status is ad-hoc |
| JWT inter-service auth | **NOT PRESENT** | Not in `requirements.txt`; only `venv/` match for `jwt` keyword |
| DRF / REST API surface | **NOT PRESENT** | DRF not installed; no `rest_framework` imports; API-style endpoints use raw `JsonResponse` |
| Basic Django auth | **PRESENT (partial)** | Login/logout/register views exist (`eht/urls.py:42-44`); no role separation, no permissions |
| Approval workflow / FSM | **NOT PRESENT** | No state machine; no role/status workflow beyond auth |
| Multi-tenancy | **NOT PRESENT** | No `Organization` model, no tenant field (see §6) |

---

## 4. Top 10 Largest Python Modules

| Rank | Path | LOC | Inferred Purpose |
|---|---|---|---|
| 1 | `eht/tests.py` | 4597 | Monolithic test suite — all eht app tests in one file |
| 2 | `eht/sld_topology_workflows.py` | 2677 | SLD manual-edit operations: combine, split, JB attach |
| 3 | `eht/views.py` | 1945 | All Django views for eht app — fat controller |
| 4 | `idfviewer/tests.py` | 703 | idfviewer test suite |
| 5 | `eht/models.py` | 693 | All eht ORM models |
| 6 | `eht/sld_pdf.py` | 607 | SLD PDF export (ReportLab) |
| 7 | `idfviewer/pcf_parser.py` | 536 | PCF isometric file parser |
| 8 | `eht/data_service.py` | 480 | Query/assembly layer between models and views |
| 9 | `idfviewer/services.py` | 465 | idfviewer business logic |
| 10 | `idfviewer/ifc_parser.py` | 460 | IFC 3D model file parser |

**Heat-loss engine location (inferred):** distributed across `eht/calculations/` subpackage — `heat_loss.py` (223 LOC), `tracer_selection.py` (403 LOC), `power_distribution.py` (352 LOC) — orchestrated via `eht/calculation.py` (450 LOC). `eht/heat_loss_methods.py` (35 LOC) appears to hold method-enum/dispatch logic only.

---

## 5. Test Footprint (Quantitative)

| File | LOC | Framework signal |
|---|---|---|
| `eht/tests.py` | 4597 | Django `TestCase` |
| `idfviewer/tests.py` | 703 | Django `TestCase` |
| `eht/test_sr_reporting_alignment.py` | 240 | Django `TestCase` |
| `eht/test_sr_calculation_hardening.py` | 198 | Django `TestCase` |
| `eht/test_manual_guide.py` | ~26 | Django `TestCase` |
| `ELECSENSE/test_runner.py` | — | Custom runner: `ExistingPostgresTestRunner` |

**Total test files: 6.** Framework: Django test runner (no pytest in `requirements.txt`). Custom test runner exists to support Postgres test runs against a pre-existing DB. All substantive tests are in the `eht/` app; `idfviewer` has 703-LOC coverage.

---

## 6. Initial Multi-Tenancy Signals

**None found.** Grep for `Organization`, `tenant`, `Tenant`, `multi_tenant`, `org_id` in all non-migration `.py` files returned zero hits. The current data model appears to be single-user/single-tenant. No user-to-project scoping mechanism visible at this reconnaissance level.

---

## 7. Discrepancies Between `Notes/eht-overview.md` and Code Reality

| # | Overview implies | Code reality |
|---|---|---|
| 1 | "Django FSM or a simple hardcoded role/status workflow" as first implementation option | No FSM installed. No hardcoded status workflow visible. Workflow is implied by field presence but not enforced. |
| 2 | FastAPI microservices as architectural direction | Completely absent from repo, requirements, and all source files. |
| 3 | JWT inter-service auth | Not in requirements. No JWT library present. |
| 4 | "Robust auth system" | Basic Django session auth only — login/logout/register. No permissions, no roles, no multi-user access control. |
| 5 | `eht/tests.py` described as "large and should eventually be split" | It is 4597 LOC, currently unsplit. The overview correctly identifies this as a known debt. |
| 6 | Cold cable, MI module, voltage-drop engine described as "pending" | Correct — these are absent from `eht/calculations/`. Overview accurately represents these as future scope. |
| 7 | Overview describes IDF parsing as "first step" toward 3D integration | `idfviewer` app is substantive (4 files >400 LOC, 4 migrations, its own URL space). More developed than "first step" framing suggests. |

---

## 8. Areas to Deep-Read in Session 2 (Architecture & Domain)

1. **`eht/calculation.py` + `eht/calculations/` subpackage** — Core engineering path. Verify: is SR heat-loss calculation correct per IEC basis? How are method placeholders handled? What can break silently with bad catalogue data?

2. **`eht/models.py`** — All data structures in one file. Understand: how is a "project" scoped? What are the key model relationships? What state fields exist and are they enforced?

3. **`eht/sld_topology_workflows.py` (2677 LOC)** — Largest substantive module. The SLD subsystem is the most complex feature. Understand: topology state machine, active/superseded/reset logic, how recalculation interacts with manual edits.

4. **`eht/data_service.py`** — The layer between models and views. Understand: what queries are expensive? Is there an N+1 problem at scale (500–1000 line projects)?

5. **`eht/views.py` (1945 LOC)** — Fat controller. Understand: how much business logic is embedded in views vs. delegated to service/calculation layer? How is auth enforced across views?

---

## 9. Areas to Deep-Read in Session 3 (Security, Config, Production Readiness, Tests)

1. **`ELECSENSE/settings.py`** — Already identified critical issues: `ALLOWED_HOSTS = ["*"]` hardcoded (overrides env config), `DEBUG = True` default, insecure `SECRET_KEY` as default, Postgres IP `129.151.129.146` hardcoded. Need full audit.

2. **Auth enforcement in `eht/views.py`** — With basic Django session auth and no DRF, verify: are all views login-protected? Is there any access control between users' projects? Can User A access User B's data?

3. **`eht/tests.py` test quality** — 4597 LOC is a large surface. Understand: what is actually being tested? Are calculation paths covered with realistic engineering inputs? Are edge cases (missing catalogue data, zero-length lines, invalid inputs) covered?

4. **`eht/sanatize_input.py` (252 LOC)** — [sic] Input handling for the Excel upload path. This is a boundary with untrusted data. Understand: what validation exists? What can a malformed `.xlsx` do?

5. **Database configuration and migration hygiene** — 21 migrations in `eht/`, `db.sqlite3` committed to repo (likely contains real project data), dual-DB alias setup in settings for migration tooling. Assess production-readiness of DB layer.

---

## 10. Questions for the Developer Before Session 2

1. The overview mentions FastAPI microservices and JWT inter-service auth as architectural goals. Are these still on the roadmap, or has the decision been made to stay monolithic Django? This affects how I should evaluate the current architecture.

2. `ALLOWED_HOSTS = ["*"]` is hardcoded on line 36 of `settings.py`, overriding the env-configurable value two lines above it. Is this intentional for the Cloudflare Tunnel setup, or is it a TODO that got left in?

3. `db.sqlite3` (the live development database) appears to be in the repo (not in `.gitignore`). Does this contain real project data? Should it be excluded?

4. The Postgres host `129.151.129.146` is hardcoded in `settings.py`. Is this a dev/staging server? Is there a production Postgres deployment, or is production still SQLite?

5. The `easyaudit` package is installed and in `INSTALLED_APPS`. What is it currently auditing? Is it capturing the right events for an eventual approval/sign-off workflow?

6. Are multiple engineers expected to use this concurrently on the same Django instance right now, or is it currently single-user? This determines whether the absence of multi-tenancy is a present-day gap or a future concern.

7. `eht/tmp/discardedCodes/calculation.py` (437 LOC) — is this dead code safe to ignore for the audit, or does it document an intentional architecture decision worth understanding?

---

## 11. Initial Impressions

- The calculation engine is substantively developed and structurally sound: the `eht/calculations/` subpackage shows deliberate domain decomposition, and the SR path appears meaningfully hardened per recent commits.
- The SLD subsystem (`sld_topology_workflows.py` at 2677 LOC) is the most complex and highest-risk component. Its size relative to everything else is a flag.
- The gap between the overview's architectural claims (FastAPI, JWT, FSM, robust auth) and the actual code is large — but the engineering domain work is real. The infrastructure ambition hasn't landed yet; the domain logic has.
- There are at least two settings-level issues (`ALLOWED_HOSTS = ["*"]`, committed `db.sqlite3`) that must be resolved before any production or multi-user use. These are not subtle.
- Test coverage is concentrated in one large file. The custom test runner and Postgres support suggest the developer is thinking about test quality, but the monolith structure makes coverage hard to assess from the outside.

---

Reconnaissance complete. Awaiting developer responses to Section 10 questions before proceeding to Session 2.
