# Codex Response to MVP Release Audit

| | |
|---|---|
| **Reviewer** | Codex |
| **Date** | 2026-06-18 |
| **Source audit** | `NOTES/audit/mvp-release-audit-2026-06-15.md` / attached Claude final audit text |
| **Purpose** | Freeze release scope, classify Claude's findings, and record Codex agreement/disagreement before any further coding |
| **Mode** | Non-invasive review only. No code, database, migration, settings, or generated project data changes in this pass. |

## 1. Overall Position

I broadly agree with Claude's release verdict: **CONDITIONAL GO** is the right
label for the current MVP.

The important distinction is:

- The implemented engineering engine is largely ready for external engineering
  review.
- The release cannot be called clean until a small number of governance,
  authorization, repository hygiene, and deployment posture issues are closed.

I do **not** recommend opening a new feature pass. The release scope should now
be frozen to:

1. Fix direct release blockers.
2. Resolve KR data-governance decisions.
3. Run manual end-to-end acceptance.
4. Record accepted limitations clearly.

Anything outside those four buckets should move to post-MVP.

## 2. Release Scope Freeze

### Allowed Before MVP External Review

- Catalogue/vendor exposure decisions needed to avoid unsafe selections.
- Authorization/security fixes that prevent cross-project mutation or accidental
  secret/data exposure.
- Deployment settings that are required for safe Cloudflare/public tunnel review.
- Small fragility fixes that can cause user-visible runtime failure during
  manual acceptance.
- Documentation wording only where it prevents misleading engineering output.

### Not Allowed Before MVP External Review

- New tracer technologies.
- New heat-loss methods.
- New cable installation methods.
- Major dashboard/UX redesign.
- New procurement lifecycle workflows.
- Large refactors that do not directly close a release blocker.
- Non-essential cleanup that risks regression.

## 3. Finding-by-Finding Response

### F1 - BLOCKER - Live MI validation gate open without documented KR approval

**Codex stance: Agree, with one qualification.**

Claude is right that this is a release governance blocker if `is_validated=True`
is present without KR's explicit row-level approval. The MI engine correctly
uses the validation gate, so the problem is not the selection code; the problem
is the live data state and traceability of the approval.

Qualification: this is not necessarily a coding task. It is first a KR data
decision:

- either formally approve the THR/MIQ and CHR/MI-825B rows and record that
  approval;
- or set those families back to `is_validated=False` through an approved,
  backed-up, auditable data-change path.

**Release decision:** Must be resolved before external engineering review.

**Allowed action:** Data governance action only, with explicit KR approval and
backup/snapshot before any mutation.

### F2 - HIGH - Fabricated/unverifiable SR vendor data selectable, no SR validation gate

**Codex stance: Agree.**

If nVent SR rows are fabricated/non-conservative and KRUS-Zapad rows are
unverifiable, they should not remain silently selectable for MVP. This is a
high-confidence release risk because SR selection does not currently have the
same `is_validated` hard gate as MI.

For MVP, the safest narrow fix is to restrict user-selectable SR vendors to the
verified set only, likely THR, CHR, and SST, while leaving historical/unverified
database rows untouched.

**Release decision:** Must be resolved before external review if users can
select vendors other than the verified set.

**Allowed action:** Small UI/config/code restriction or clear hard warning gate.
No fabricated catalogue row should be silently available for selection.

### F3 - HIGH - Credential hash and backup DB committed to git

**Codex stance: Strongly agree.**

This is not an engineering-calculation issue, but it is a release hygiene and
security blocker before the repository is pushed, shared, or used in any public
deployment workflow.

The proposed actions are correct:

- add `*.bak` and `data_dump.json` protection to `.gitignore`;
- remove tracked sensitive artifacts from the index;
- rotate the exposed user's password because the hash has already existed in
  git history.

**Release decision:** Must be done before repo sharing or production/public
deployment. For purely local manual testing it does not block the calculation
workflow, but it should still be closed now because it is low-risk and important.

**Allowed action:** Repository hygiene only. Avoid deleting the user's physical
backup unless KR explicitly asks; untracking is enough for git hygiene.

### F4 - HIGH - Cross-project mutation authorization gap

**Codex stance: Strongly agree.**

This is the most important code fix in the audit. Read views and most SLD paths
use project scoping, but upload/confirm paths are dangerous because they mutate
project workspace data. If an authenticated user can target a project they are
not assigned to, the current low-concurrency/single-company assumption does not
make that safe.

**Release decision:** Must be fixed before external engineering review.

**Allowed action:** Small surgical code fix only: use the existing
`ManagedProject.available_to_user()` style gate consistently in
`calculate_view` and `confirm_valid_data`. Add focused tests.

### F5 - MEDIUM - Production secret/DEBUG posture depends on env discipline

**Codex stance: Agree, but classify as deployment gate rather than core code blocker.**

The code supports production settings, but release depends on correct
environment values. That is normal for Django, but it must be captured in the
deployment runbook and checked before any public Cloudflare/tunnel review.

I also agree with Claude's later point that `SECURE_PROXY_SSL_HEADER` should be
explicitly reviewed for Cloudflare/TLS termination.

**Release decision:** Required before public deployment or public tunnel review.
Not a blocker for local manual end-to-end testing.

**Allowed action:** Deployment settings/runbook update, plus a small settings
fix if `SECURE_PROXY_SSL_HEADER` is missing.

### F6 - MEDIUM - MI temperature/inrush correction currently inert

**Codex stance: Partly agree, requires re-verification.**

The limitation is valid in principle: if MI resistance temperature correction is
not populated, MI startup/inrush behavior can be under-modeled. However, earlier
MI population work was intended to populate per-heater `tcr_per_degree_c`, so
the audit's claim that all heaters have `tcr_per_degree_c=None` must be
rechecked against the current database before accepting it as current truth.

If the audit is correct for the live DB, then the limitation is acceptable for
MVP only if MI remains fallback-only and clearly review-labelled. It should not
block the MVP unless MI is being sold as fully production-validated engineering.

**Release decision:** Recheck live MI TCR data. If absent, document as accepted
MVP limitation unless KR wants MI validation to be stricter.

**Allowed action:** Read-only verification first. No catalogue mutation without
KR approval.

### F7 - MEDIUM - Earth-loop non-conservatisms stack

**Codex stance: Agree.**

This was already known and documented: tracer PE-path resistance is deferred and
the source impedance approximation is simplified. Claude is right that these
can make calculated fault current look better than reality.

The current MVP position remains acceptable only if warnings stay visible on
result/report surfaces. This is not a new coding scope unless the warning is
missing or buried.

**Release decision:** Accept for MVP with visible limitation.

**Allowed action:** Manual UI/report check during end-to-end acceptance.

### F8 - MEDIUM - Error-file path relative on write, absolute on read

**Codex stance: Agree.**

This is a real deployment fragility. It may not appear in local development if
the process CWD is the project root, but Docker/gunicorn/service managers can
change working directory behavior.

This is small and low-risk enough to include in the release-fix set.

**Release decision:** Should fix before external review if uploads/error
workbooks are part of the demo path.

**Allowed action:** Anchor writer path to `settings.BASE_DIR`, with focused
test or existing test adjustment.

### F9 - LOW/MEDIUM - Dependency hygiene not completed

**Codex stance: Agree.**

A dependency hygiene pass remains open. It should happen before public exposure,
especially because this app will sit behind Cloudflare and may be shown to
external reviewers.

Dropping unused `psycopg2-binary` is reasonable if confirmed unused. Do not
remove it blindly without import/test verification.

**Release decision:** Required before public deployment. Acceptable to perform
after manual local end-to-end testing, before public tunnel/release tag.

**Allowed action:** Dependency audit and minimal package cleanup only.

### F10 - LOW - Dead code, doc drift, minor info disclosure

**Codex stance: Partly agree, mostly not release-blocking.**

Dead `index/index2` style stubs and stale internal notes are cleanup items, not
release blockers. The admin-path context point matters only if the public
template leaks admin links to anonymous/non-staff users. Existing tests already
cover staff/non-staff landing-page admin link behavior, so this should be
verified before coding.

I do **not** recommend spending release time cleaning internal `NOTES`
snapshots unless they mislead current release decisions or are exposed through
production views.

**Release decision:** Defer most cleanup. Verify no public admin-link leakage.

**Allowed action:** Only fix if a real user-facing leak or runtime issue is
confirmed.

## 4. Mandatory Before External Engineering Review

I agree with Claude that these are the release gates:

1. **F1 MI validation gate:** KR must approve or re-close the MI validation
   state. This is a data-governance blocker.
2. **F2 SR vendor exposure:** unverified/fabricated SR vendors must not be
   silently selectable.
3. **F3 git hygiene:** tracked sensitive dump/backup artifacts must be untracked
   and the exposed password rotated before repo sharing/public deployment.
4. **F4 mutation authorization:** upload/confirm endpoints must enforce project
   assignment before mutating workspace data.
5. **F5 deployment posture:** production/tunnel environment must be explicitly
   configured and checked.

I would add two near-gates:

6. **F8 error-file path anchoring:** small enough and practical enough to fix
   before release.
7. **Cloudflare proxy header:** confirm/add `SECURE_PROXY_SSL_HEADER` before
   any HTTPS reverse-proxy testing.

## 5. Acceptable for MVP With Documented Limitation

I agree these should remain accepted limitations, not new MVP scope:

- Earth-loop excludes tracer PE-path resistance.
- Source impedance is simplified.
- Cold-cable is Cu-only.
- Installation Method E only.
- PF = 1.0 and reactance ignored.
- Single-phase heat tracing basis.
- Cable schedule remains procurement-light.
- Main upstream spare-capacity coordination is deferred.
- MI T-class is review-only.
- Constant Power tracer is post-MVP.
- Advanced heat-loss methods are post-MVP.

Condition: these limitations must remain visible in user-facing result/report
or manual surfaces where they affect engineering judgement.

## 6. Voltage-Drop Optimization Special Response

**Codex stance: Agree with Claude.**

Claude's explanation matches the intended design of the cold-cable optimizer:
it enumerates feeder candidates, picks the smallest passing branch sizes for
each feeder candidate, and chooses the lowest conductor-volume option. That is
not equal voltage-drop distribution.

The likely confusion is that, when VD is not tight, the minimum catalogue sizes
win across both feeder and branch segments, making the output look flat or
evenly distributed. That is expected behavior for a minimum-copper-volume
objective.

No new algorithm scope is recommended before MVP. The only recommended action
is documentation wording:

- describe the objective as "minimum total conductor volume across feeder and
  branch cable segments";
- clarify that it is not a monetary-cost optimizer and not a VD-balancing
  optimizer.

## 7. Catalogue Validation Special Response

**Codex stance: Agree with the risk framing.**

The engine isolation appears correct, so the release risk is data exposure and
validation status, not cross-contamination between vendors.

Release-freeze position:

- THR default path is acceptable if verified.
- CHR/SST may be acceptable if verified.
- nVent and KRUS-Zapad should not remain selectable if the audit evidence is
  accurate.
- MI validation state must be explicitly approved or closed.

No broad SR validation model should be added before MVP unless KR chooses that
over simply restricting selectable vendors. The minimal MVP fix is vendor
exposure control.

## 8. Security and Deployment Special Response

**Codex stance: Agree, with release-stage separation.**

For local manual acceptance, the app can be tested as-is after F4/F8 style code
fixes are queued. For Cloudflare/public tunnel review, the following must be
confirmed:

- no sensitive dump/backup tracked in git;
- exposed password rotated;
- `DEBUG=false`;
- strong env `SECRET_KEY`;
- correct `ALLOWED_HOSTS`;
- correct `CSRF_TRUSTED_ORIGINS`;
- secure cookies/HSTS/HTTPS redirect settings;
- `SECURE_PROXY_SSL_HEADER` for Cloudflare/TLS termination;
- non-default admin path;
- admin path protected by Cloudflare/IP/identity control where practical;
- dependency audit completed or consciously accepted.

I do not recommend adding larger security features before MVP unless the
dependency audit reveals a direct known vulnerability requiring upgrade.

## 9. Manual End-to-End Test Script

**Codex stance: Agree.**

Claude's manual test script is good and should become the actual MVP acceptance
script. I would add three explicit evidence-capture requirements:

1. Save the exact line list used for the test.
2. Save representative exports/PDFs from the run.
3. Record every manual warning/review-required item as either accepted,
   blocking, or post-MVP.

This is not new scope; it is release evidence.

## 10. New Points Codex Adds Without Expanding Scope

### N1 - Audit freshness check before coding

Claude's audit was dated 2026-06-15. Before acting on any finding, verify it
against the current 2026-06-18 worktree/database state. This especially applies
to MI TCR population, tracked files, and any endpoint changes made after the
audit.

### N2 - Separate "external engineering review" from "public deployment"

Some items are required before any external engineering review, such as F1, F2,
and F4. Others are specifically public-deployment gates, such as Cloudflare
proxy settings, dependency audit, and admin exposure hardening. The release
checklist should keep those categories separate so we do not block manual
engineering review on non-essential deployment polish.

### N3 - Any data mutation requires KR approval and backup

F1 may require changing `is_validated` values. That is a data mutation, not a
code change. It must be done only after KR approval, with a backup/snapshot and
with exact before/after rows recorded.

### N4 - Do not physically delete backup files as part of git hygiene

F3 should remove sensitive artifacts from git tracking. It should not delete
KR's physical backup files unless KR explicitly asks. Use untracking and
`.gitignore`; preserve user-owned backups.

### N5 - Final fixes should be one small release-fix pass

If KR approves coding after this freeze, combine only the small release fixes:

- F4 authorization gate;
- F2 vendor exposure control, if KR chooses code restriction;
- F8 error-file path anchoring;
- Cloudflare proxy setting, if absent;
- F3 git hygiene, with KR password rotation outside code;
- possibly small verification tests.

Do not mix these with cleanup/refactor work.

## 11. Codex Proposed Release-Fix Scope

If KR decides to proceed with a final fix pass, my recommended scope is:

| Item | Include? | Reason |
|---|---:|---|
| F1 MI gate decision | Yes, but KR/data action first | Release data-governance blocker |
| F2 restrict/warn SR vendors | Yes | Prevent unsafe silent selection |
| F3 untrack dump/backup | Yes | Security hygiene, low-risk if not deleting files |
| F4 upload/confirm authorization | Yes | Real mutation authorization gap |
| F5 env/runbook | Yes | Deployment gate |
| F6 MI TCR/inrush | Verify only | May be stale; likely documented limitation |
| F7 earth-loop simplification | No code unless warning missing | Accepted limitation |
| F8 error-file path | Yes | Small runtime fragility |
| F9 dependency audit | Yes before public exposure | Not a feature |
| F10 dead code/doc drift | Mostly defer | Not release-critical unless exposed |

## 12. Final Codex Recommendation

Freeze the MVP scope now.

Before external engineering review, close F1, F2, F3, F4, F5, and preferably F8
plus the Cloudflare proxy header check. Treat F6/F7 and the documented
engineering simplifications as accepted MVP limitations. Defer F10-style cleanup
unless it is proven user-facing.

The product is close enough that the next coding pass should be called a
**release-fix pass**, not a feature pass.
