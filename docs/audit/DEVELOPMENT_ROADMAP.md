# Development roadmap

Audit date: 29 October 2026. **Planning only; no fixes, migrations or deployment changes were performed.** The roadmap preserves the existing Streamlit/Python/SQLite architecture and existing production-style records.

Use [docs/audit/ISSUE_REGISTER.md](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docs/audit/ISSUE_REGISTER.md) for precise issue evidence/effort and [docs/audit/ARCHITECTURE_RECOMMENDATIONS.md](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docs/audit/ARCHITECTURE_RECOMMENDATIONS.md) for design choices. The current assessed health is 34.4/100; UI/UX rendering and application performance are unassessed. A score is not a release gate.

## Planning assumptions and effort

The supplied 26-card, 399-responsibility, 9-interview deployment is treated as a modest internal single-instance service until the owner supplies contrary usage/availability needs. No business approval hierarchy beyond the documented roles is invented. Resolve ordinary manager assignment scope versus explicitly authorized executive scope before changing permissions.

Small ≈ up to one engineer-day; Medium ≈ 2–5 engineer-days; Large ≈ more than 5 engineer-days. These are relative implementation bands with substantial overlap across findings. Stage estimates are **relative**, not sums, calendar commitments or promises that production sign-off is included. Each stage should be delivered in independently reviewable increments.

| Stage | Relative effort | Release implication |
|---|---|---|
| 1 — Critical stabilization | Large; multiple small/medium increments | Required before any real-data pilot or external exposure |
| 2 — Technical quality | Large | Required controls and data/document correctness before production approval |
| 3 — Product and UX | Medium–Large | Complete agreed workflow/device/accessibility acceptance |
| 4 — Future development | Individually scoped | Optional capabilities; no immediate platform rewrite |

Suggested responsibility labels below are roles, not an instruction to add staff or delegate agents.

## Shared delivery safeguards

- Capture a consistent protected backup and verify restoration before implementation that affects data.
- Work against synthetic fixtures and an isolated copy. Never run reset, seed or migration commands against an unknown DB.
- Preserve all IDs, document values, user ownership, source provenance and historical records.
- Write failing regression cases for reproduced defects before their fixes; CI must never connect to the live DB.
- Keep schema changes additive where possible, map legacy values explicitly, and rehearse any SQLite table rebuild on a copy.
- Review and deploy small increments. Avoid changing authentication, document format and storage platform in one unreviewable change.
- Keep rollback/restore instructions with each release and record the exact supported dependency/runtime set.

## Stage 1 — Critical stabilization

**Objective:** restore meaningful access control and stop ordinary operations from silently corrupting approval or interview evidence.

**Suggested owners:** application engineer, security reviewer, HR/product owner, QA.

### Execution order and tasks

| Order | Task / issue IDs | Dependencies | Expected benefit | Acceptance |
|---:|---|---|---|---|
| 1 | Establish safe fixture harness and first regression checks (AUD-025); capture pre-change baseline and protected backup (AUD-023) | Confirm deployment/data owner; identify real DB without opening it for writes | Fixes become reviewable and reversible | Synthetic tests can run without touching live records; backup restore yields the same counts and values |
| 2 | Remove production demo credential selector and password-free identity switch (AUD-001/002); rotate bundled credentials | Safe initial admin provisioning plan | Closes the two Critical access paths | Anonymous form supplies no credentials; employee cannot become admin; old bundled credentials fail |
| 3 | Migrate plaintext credentials or integrate the agreed identity provider; add throttling/session freshness and safe credential-free session payloads (AUD-003/031) | Step 2; recovery path for existing users | Meaningful authentication and revocation | Hash/provider checks verified; resets work; disabled/expired sessions cannot write; drafts do not cross identities |
| 4 | Enforce trusted actor and assignment scope in all writes (AUD-004/005) | HR confirms manager/executive authority matrix | Blocks unrelated-card writes and forged attribution | Negative role/assignment and cross-JD clause tests pass; intended directory reading still works |
| 5 | Conditional pending decisions, version conflict checks and target/affected-row validation (AUD-006/007/009) | Step 1 regression cases; step 4 service boundary | Prevents duplicate decisions, silent overwrite and false success | Replay and stale requests cannot mutate; unsupported/missing targets leave no partial state |
| 6 | Bind approval to exact content revision and increment parent revision for child changes (AUD-008) | Step 5; approved policy for pending requests and post-approval edits | Makes approval/export/version meaning reliable | Every content edit advances the document revision; approved snapshot is unambiguous; unresolved requests handled explicitly |
| 7 | Prefill interview edit values and guard record-specific drafts (AUD-017) | Synthetic existing notes/status fixture | Prevents accidental loss of meeting outcomes | No-change save preserves notes/status; changing selection does not reuse another interview’s draft |
| 8 | Remove misleading draft/approved wording and invented missing safety/ID values (AUD-032) | Agreed missing-data and identifier presentation | Prevents official-looking false content | Draft labels agree throughout UI/export; missing safety stays visibly unknown |
| 9 | Enable and verify CORS/origin/host protections; escape dynamic HTML; constrain uploads initially (AUD-020/021/022) | Known deployment URL/proxy, locked supported runtime | Reduces cross-origin/markup/resource exposure | Hostile origin rejected; malicious markup literal; oversized fixtures rejected early; normal upload works |
| 10 | Protect release with the above regression checks and a staging smoke test | All preceding fixes | Stops immediate regressions | P0 tests and affected P1 cases pass on supported runtime; no live-data test writes |

**Dependencies:** a safe way to provision the first real admin, explicit manager versus executive authority, revision/approval policy and a recoverable copy of existing data. Implement account provisioning needed for secure access now; full administrative UI may follow later.

**Risks:** account lockout, over-restricting legitimate executive workflows, schema compatibility for version-bound approvals, and presenting historical approvals as stronger evidence than they originally were.

**Risk controls:** test account migration/reset on a copy, retain a controlled recovery process, implement compatibility reads for legacy records, and preserve old attribution/status values as historical data.

**Exit gate:** both Critical findings closed; the reproduced replay/stale/cross-target/false-success/notes-loss cases fail safely; no approval can silently cover changed content; all remaining risks have explicit owners. Stage 1 alone does not prove production readiness.

## Stage 2 — Technical quality

**Objective:** make data evolution, documents, history, failure handling and deployment reproducible.

**Suggested owners:** application/data engineer, QA, operations, HR reviewer.

### Execution order and tasks

| Order | Task / issue IDs | Dependencies | Benefit / acceptance |
|---:|---|---|---|
| 1 | Create versioned migration path; canonicalize observed legacy statuses and add immutable actor references (AUD-010/011/019/029) | Restored copy; Stage 1 identity/revision model | 26 JDs, 399 responsibilities, existing requests/audit IDs and text retained; known English/Arabic statuses agree; ambiguous attribution not guessed |
| 2 | Enforce FK/domain/target constraints and safe connection/transaction cleanup (AUD-010/028) | Step 1 data preflight | Invalid/orphan writes rejected; fault-injected failures roll back all related rows and close connections |
| 3 | Capture complete decision/interview/account events and document revision snapshots (AUD-012) | Actor IDs, revision semantics | Rejections and schedule edits attributable; historical complete card reconstructable; immutability wording accurately qualified |
| 4 | Separate startup schema check, explicit provisioning and content import (AUD-029) | Migration/provisioning design | Interrupted setup resumes safely; normal requests never seed accounts or partial data |
| 5 | Define document contract; fix own-export round trip and omitted fields (AUD-014/015) | Shared section registry; golden fixtures from original formats | Valid DOCX still generated; all agreed fields, Arabic text, responsibilities/KPIs survive round trip |
| 6 | Add import diagnostics, idempotency/new-revision choice and ID-based selection (AUD-013/016) | Step 5; explicit card identity policy | Unrelated files rejected; incomplete cards visibly draft; duplicate uploads deliberate and all IDs selectable |
| 7 | Centralize safe card rendering, status mapping and target definitions (AUD-027/033) | Correct model and format contract | No duplicated divergent field lists; both roles display identical supported content |
| 8 | Lock dependency/runtime set, add advisory checks and harden image/configuration (AUD-024/035) | Choose tested Python version and deployment target | Reproducible clean build, reviewed direct/transitive scan, non-root runtime, correct port and readiness check |
| 9 | Deploy durable DB path, consistent protected backup/retention and restore runbook (AUD-023) | Ownership of RPO/RTO and storage | Restart/redeploy retains all writes; restored copy passes counts, text, revisions and relationship checks; source/image excludes live data |
| 10 | Add measured-use indexes, bounded reads and remove eager hidden work (AUD-026) | Stable parent revision; representative growth fixtures | Query plans use intended indexes; hidden tabs do not parse/export; authorized caches invalidate correctly |
| 11 | Expand synthetic unit/integration, format and deployment CI (AUD-025) | Earlier steps supply stable contracts | P0/P1 fixes protected; supported Python/container checks actually run; no test points at an existing database |

**Expected benefits:** fewer data anomalies, defensible history, reliable Word interchange, safer updates, reproducible builds and recoverable deployments.

**Risks:** migration can mis-map legacy names/statuses; stricter parsers may reject legitimate older templates; cached data may be stale or over-shared; index/schema changes may block writes during rollout.

**Risk controls:** compare all original values before/after rehearsal, retain legacy snapshots, use explicit unsupported-template diagnostics, scope cache by actor/revision and plan a controlled maintenance/rollback procedure.

**Exit gate:** all applicable High findings are resolved or have an explicitly accepted, time-bounded exception; restore/migration rehearsals succeed; clean deployment and document fixtures pass; no partial bootstrap repair requires deleting records.

## Stage 3 — Product and UX improvements

**Objective:** complete supported user journeys and verify the actual Arabic interface across agreed devices/accessibility needs.

**Suggested owners:** application/frontend engineer, HR product owner, QA and representative staff users.

### Execution order and tasks

1. Agree the complete editable/display/export field matrix. Add required KPI/dimensions/profile edits using typed targets (AUD-033); display competencies consistently (AUD-015). Preserve source authority and do not invent content.
2. Add safe empty/unassigned/missing-record pages and clear current identity/scope (AUD-018). Keep company-wide read visibility where intended.
3. Finalize truthful canonical status labels, document revision and draft/approved export states (AUD-019/032).
4. Provide supported account disable/reset/assignment administration or corresponding identity-provider workflow (AUD-030). This is a production capability recommendation; HR must approve the operating policy.
5. Show schedule time and bind interview form values correctly (AUD-017/034). Capture attributed outcome events.
6. Simplify navigation/queue filters and provide persistent success/conflict/error feedback after reruns. These are proposed improvements to validate with users.
7. Scope RTL styling and verify desktop/tablet/mobile rendering, mixed-script tables, keyboard/focus, screen-reader language/order, zoom and contrast. Apply the agreed accessibility target; no conformance claim before execution.
8. Render representative Arabic DOCX output in the actual target Word/PDF environment, including multipage tables and signatures.
9. Run acceptance sessions with HR, one ordinary manager, an employee and any explicitly authorized executive.

**Dependencies:** Stage 1 safety controls; Stage 2 shared model/status/document contracts. Visual and workflow experiments can begin earlier on synthetic data, but must not replace integrity work.

**Expected benefits:** fewer off-system corrections, clearer ownership and status, accessible Arabic review, more trustworthy official documents and easier HR operations.

**Risks:** changing navigation may confuse existing users; global CSS changes can alter unrelated widgets; executive scope may be accidentally removed; Word rendering can vary across environments.

**Acceptance:** complete submit→review→track→export journey for each agreed editable target; all roles see correct content; no-change edits preserve stored information; agreed device/accessibility matrix is executed with documented results; HR accepts truthful status/approval wording.

**Exit gate:** known P1 workflow gaps closed, agreed UI/device requirements met and actual user acceptance recorded. This stage must not claim success based only on source inspection.

## Stage 4 — Future development

**Objective:** add value based on measured demand and approved business needs.

All items below are **proposed enhancements**, not confirmed missing original requirements.

| Suggested order | Capability | Dependencies | Expected benefit | Risk / acceptance |
|---:|---|---|---|---|
| 1 | Review due dates, decision alerts and interview reminders | Stable ownership, states, delivery consent and supported channel | Reduces manual chasing | Avoid duplicate/noisy notifications; verify preferences and idempotency with synthetic schedules |
| 2 | Historical revision comparison and controlled approved-revision export | Complete snapshots and trusted approval lifecycle | Easier audit preparation | Preserve original evidence; every displayed revision is reconstructable |
| 3 | Controlled bulk import and import-result reconciliation | Bounded parser, fingerprints, typed schema | Less HR repetition | Partial failures explicit; reruns safe; no silent duplicate cards |
| 4 | Read-only management reporting with explicit access scope | Canonical statuses and actor policy | Better review tracking | Counts reconcile to records; no sensitive scope leakage |
| 5 | Stronger independent audit archive/tamper-evidence | Approved retention/compliance need and operational owner | Higher assurance | Do not market absolute immutability; demonstrate recovery and access controls |
| 6 | Background document processing | Measured synchronous latency/resource pressure | Responsive large-batch work | Requires job idempotency, retry/status visibility and bounded resources |
| 7 | Shared database/HA or multi-instance deployment | Measured contention/availability need, migration and rollback plan | Supports proven growth needs | Reconcile all IDs/history and validate concurrency; no immediate platform change justified |

**Relative effort:** Small/Medium for narrow reporting; Medium/Large for notifications, bulk workflows or independent audit storage; Large for new job infrastructure or datastore/HA migration. Scope after actual requirements.

**Acceptance:** each enhancement has an owner, measurable user benefit, explicit data/access policy, safe rollout and regression coverage. A future platform change must be justified by measured need rather than aspiration.

## Top 10 improvement packages

1. Remove demo access paths (AUD-001/002).
2. Secure credentials and session lifecycle (AUD-003/031).
3. Enforce actor/assignment/target scope (AUD-004/005).
4. Establish synthetic regression and CI gates (AUD-025), alongside every fix.
5. Make review decisions conditional, conflict-aware and truthful (AUD-006/007/009).
6. Bind versions, approvals and audit evidence (AUD-008/012/019).
7. Preserve interview edits (AUD-017).
8. Repair document fidelity and validate imports (AUD-013–016/032/033).
9. Introduce legacy-safe constraints, identity and provisioning (AUD-010/011/029).
10. Prove secure, durable, reproducible operation (AUD-020–024/028/035).

This ranking is by impact and dependencies, not a recommendation to delay tests or CORS until last. Execute baseline tests first and harden exposure in Stage 1 while building the data/document foundations in small compatible increments.

## Production acceptance checklist

Production approval requires actual evidence of:

- No impersonation/default passwords; negative role, assignment and revocation tests.
- One decision per pending request; stale conflicts safe; revision-bound approval and trustworthy history.
- Existing data retained through migration; declared relationships enforced; no guessed legacy ownership.
- Every supported field consistent across source import, UI, accepted revision and Word output.
- Safe interview/empty-state behavior and actual device/accessibility/Arabic-document verification.
- Locked, scanned, tested deployment with durable storage, restricted runtime and working restore.
- Agreed owner-approved retention, recovery objectives and authority model.
- Measured end-to-end performance/concurrency against a stated target, with documented residual risks.

Do not call the project production-ready simply because the Streamlit health route responds or a numerical audit score improves.

