# Consolidated issue register

Audit date: 29 October 2026 (Africa/Cairo). Scope: the supplied local project. No application fixes were implemented. Credentials and personal data are intentionally excluded.

Severity reflects consequence; priority reflects execution order and dependencies. P0 = remove immediate access exposure; P1 = release blocker or prerequisite; P2 = next quality/product increment; P3 = later polish. Small = roughly up to 1 engineer-day; Medium = roughly 2–5 engineer-days; Large = more than 5 engineer-days. These are relative planning bands, not delivery commitments, and exclude coordinated rollout and business approval.

“Verified” describes source/data or an executed synthetic observation, not a production penetration-test result. Potential consequences and untested exposure are labeled separately. Test IDs refer to the validation ledger in [PROJECT_AUDIT_REPORT.md](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docs/audit/PROJECT_AUDIT_REPORT.md).

## Priority index

| ID | Finding | Category | Severity | Priority | Effort | Evidence status |
|---|---|---|---|---|---|---|
| AUD-001 | Password-free account switching grants administrator access | Security | Critical | P0 | Small | Verified behavior |
| AUD-002 | Login form supplies seeded credentials | Security | Critical | P0 | Small | Verified source exposure |
| AUD-003 | Passwords are stored and compared as plaintext | Security | High | P0 | Medium | Verified implementation |
| AUD-004 | Every manager can approve any company card | Security | High | P1 | Medium | Verified code path; policy discrepancy |
| AUD-005 | Mutation functions trust actor strings and unrelated responsibility IDs | Backend | High | P1 | Medium | Verified behavior |
| AUD-006 | Review decisions can be replayed or reversed | Backend | High | P1 | Small | Verified behavior |
| AUD-007 | Stale requests overwrite newer content and misstate history | Backend | High | P1 | Medium | Verified sequential reproduction; concurrent risk |
| AUD-008 | Approval status and document versions diverge from changed content | Backend | High | P1 | Medium | Verified behavior |
| AUD-009 | Invalid targets can report success and create false audit events | Backend | High | P1 | Small | Verified behavior |
| AUD-010 | Relational and domain constraints are not enforced comprehensively | Database | High | P1 | Medium | Verified configuration and synthetic violations |
| AUD-011 | Request ownership and audit identity use mutable display names | Database | Medium | P2 | Medium | Verified design risk |
| AUD-012 | Audit trail is incomplete and does not prove immutable revision history | Database | High | P1 | Medium | Verified coverage gap; tampering risk |
| AUD-013 | Repeated imports duplicate cards and duplicate labels hide records | Backend | Medium | P2 | Medium | Verified behavior; derived UI consequence |
| AUD-014 | Word export cannot be re-imported without content loss | Backend | High | P1 | Medium | Verified behavior |
| AUD-015 | Competencies and stored approvals are omitted from views and exports | Frontend | Medium | P1 | Small | Verified implementation and synthetic export |
| AUD-016 | Word imports accept incomplete and unrelated documents | Backend | Medium | P1 | Medium | Verified validation gap |
| AUD-017 | Saving an interview form can overwrite existing notes and status | UX | High | P1 | Small | Verified source behavior; UI execution unavailable |
| AUD-018 | Empty catalogs and invalid assignments can crash employee pages | Frontend | High | P1 | Small | Verified reachable code assumptions |
| AUD-019 | Legacy English statuses are inconsistently interpreted | Frontend | Medium | P1 | Small | Verified data/source mismatch |
| AUD-020 | Unescaped stored text is inserted into raw HTML | Security | Medium | P1 | Small | Verified HTML interpolation; browser exploit not tested |
| AUD-021 | Cross-origin protection is explicitly disabled | Security | High | P1 | Small | Verified effective configuration; exploitation not tested |
| AUD-022 | Uploads lack document-specific resource limits | Security | Medium | P2 | Small | Verified missing safeguards; denial-of-service risk |
| AUD-023 | Deployment packages mutable business data without a recovery plan | Architecture | High | P1 | Medium | Verified packaging gap; data-loss/exposure risk |
| AUD-024 | Dependency versions are unbounded and permit known vulnerable runtimes | Security | High | P1 | Medium | Verified manifest risk; installed versions not shown affected |
| AUD-025 | No regression suite or CI validation is supplied | Testing | High | P1 | Medium | Verified absence and command result |
| AUD-026 | Reruns repeat broad queries, imports and exports | Architecture | Medium | P2 | Medium | Verified execution pattern; scaling risk, no present bottleneck |
| AUD-027 | Duplicated card rendering and broad CSS increase UI drift | Frontend | Medium | P2 | Medium | Verified structure; visual effects not assessed |
| AUD-028 | Database failures lack controlled rollback, cleanup and useful observability | Backend | Medium | P2 | Medium | Verified code gap; failure modes not fault-injected |
| AUD-029 | Partial bootstrap can permanently skip missing users and schedules | Architecture | High | P1 | Medium | Verified synthetic failure scenario |
| AUD-030 | Operational account and assignment administration is missing | UX | Medium | P2 | Medium | Verified missing capability; production-readiness recommendation |
| AUD-031 | Session transitions retain unrelated state and have no freshness policy | Security | Medium | P2 | Small | Verified state behavior; exposure risk |
| AUD-032 | Official views fabricate missing identifiers and safety/approval content | UX | High | P1 | Small | Verified output logic |
| AUD-033 | Promised edit coverage excludes important card fields | UX | Medium | P2 | Medium | Verified UI gap |
| AUD-034 | Interview time is stored but omitted from the schedule view | UX | Low | P3 | Small | Verified presentation omission |
| AUD-035 | Container privileges and health checks are minimal | Security | Medium | P2 | Small | Verified configuration; deployment risk |

## AUD-001 — Password-free account switching grants administrator access

| Field | Assessment |
|---|---|
| Issue ID | AUD-001 |
| Category | Security |
| Severity | Critical |
| Location | [auth.py:110](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:110), [auth.py:118](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:118) |
| Evidence | Verified behavior. T04: real render_auth_sidebar(), with a synthetic sidebar adapter, changed an employee session to admin without a password prompt. |
| Description | Every logged-in user receives the complete account selector and can adopt the selected identity. |
| Root Cause | Demo impersonation is enabled unconditionally. |
| Impact | An employee can reach HR review, imports and schedule changes under another identity. |
| Recommended Fix | Remove impersonation from normal operation; if a demo is retained, isolate it from real data and production configuration. |
| Implementation Effort | Small |
| Priority | P0 |
| Verification | An employee cannot change identity or role through any normal widget; negative role tests pass. |

## AUD-002 — Login form supplies seeded credentials

| Field | Assessment |
|---|---|
| Issue ID | AUD-002 |
| Category | Security |
| Severity | Critical |
| Location | [auth.py:54](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:54), [database.py:350](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:350), [README.md:35](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/README.md:35) |
| Evidence | Verified source exposure. The unauthenticated demo selector fills username and password, including an admin account; bootstrap seeds matching fixed credentials. Values intentionally omitted. |
| Description | Anyone reaching an unchanged seeded deployment is offered credentials for privileged access. |
| Root Cause | Demonstration accounts and real authentication share one runtime and database. |
| Impact | Authentication provides no meaningful protection while these defaults remain usable. Actual external exposure was not assessed. |
| Recommended Fix | Disable credential autofill in production, remove demo accounts through a controlled change, rotate existing credentials, and provision the initial admin securely. |
| Implementation Effort | Small |
| Priority | P0 |
| Verification | Anonymous users see no credential selector; all bundled passwords fail; an independently provisioned admin can log in. |

## AUD-003 — Passwords are stored and compared as plaintext

| Field | Assessment |
|---|---|
| Issue ID | AUD-003 |
| Category | Security |
| Severity | High |
| Location | [database.py:133](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:133), [database.py:380](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:380), [auth.py:19](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:19) |
| Evidence | Verified implementation. users.password is populated directly; login compares user["password"] with the submitted string and stores the full user row in session state. |
| Description | Password hashing, login throttling and authentication event logging are absent in the supplied application. |
| Root Cause | Minimal custom authentication was carried from a demonstration into product claims. |
| Impact | Database or backup disclosure exposes reusable passwords; repeated guesses are unrestricted by application code. |
| Recommended Fix | Use a maintained identity provider or a vetted password hash and rate limiter; migrate accounts with forced resets or a controlled hash conversion and remove password values from session payloads. |
| Implementation Effort | Medium |
| Priority | P0 |
| Verification | No readable passwords in database/backups or session payloads; throttling and failed-login audit tests pass. |

## AUD-004 — Every manager can approve any company card

| Field | Assessment |
|---|---|
| Issue ID | AUD-004 |
| Category | Security |
| Severity | High |
| Location | [app.py:558](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:558), [app.py:561](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:561), [app.py:591](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:591), [README.md:16](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/README.md:16) |
| Evidence | Verified code path; policy discrepancy. The manager selector contains every JD and its selected ID is passed to approve_jd_as_is; the README describes assigned-card review and separately calls out company-wide browsing for one executive. |
| Description | The ordinary manager role has company-wide mutation scope rather than an explicit assignment scope. |
| Root Cause | Read visibility and approval authority are conflated. |
| Impact | Managers can approve or propose changes outside their assignment. Company-wide directory visibility itself is intentional and should be preserved. |
| Recommended Fix | Define an explicit approval policy with product owners; default writes to assigned cards, with a separate executive grant where authorized. Enforce in a service. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | Assigned managers can act on their cards; unrelated IDs fail; authorized executive behavior remains covered. |

## AUD-005 — Mutation functions trust actor strings and unrelated responsibility IDs

| Field | Assessment |
|---|---|
| Issue ID | AUD-005 |
| Category | Backend |
| Severity | High |
| Location | [database.py:440](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:440), [database.py:493](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:493), [database.py:519](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:519), [database.py:577](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:577), [database.py:631](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:631) |
| Evidence | Verified behavior. T07: a request belonging to JD 1 updated a responsibility belonging to JD 2. Mutation functions accept display-name strings and do not check role or ownership. |
| Description | The database layer cannot establish who is authorized or whether the target responsibility belongs to the request JD. |
| Root Cause | Authorization exists only in UI branching; target validation is absent from business operations. |
| Impact | Incorrect or future callers can alter unrelated data and attribute it to arbitrary names. These functions are not separately exposed HTTP APIs. |
| Recommended Fix | Add an actor-aware service; derive identity from the authenticated session and constrain responsibility writes by id AND jd_id AND active state. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | Cross-JD requests and unauthorized actors are rejected without writes; existing valid review paths still work. |

## AUD-006 — Review decisions can be replayed or reversed

| Field | Assessment |
|---|---|
| Issue ID | AUD-006 |
| Category | Backend |
| Severity | High |
| Location | [database.py:497](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:497), [database.py:506](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:506), [database.py:572](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:572) |
| Evidence | Verified behavior. T05: accepting the same request twice succeeded twice, advanced JD version from 1 to 3 and wrote two acceptance events. |
| Description | The decision path does not require pending status or conditionally claim the request. |
| Root Cause | Unconditional UPDATE after an unrestricted SELECT. |
| Impact | Repeated clicks, stale sessions or retries can duplicate history or reverse a completed decision. |
| Recommended Fix | Make a pending-to-final transition conditional and atomic; return an explicit already-reviewed result; reject invalid decision values. |
| Implementation Effort | Small |
| Priority | P1 |
| Verification | Repeat acceptance/rejection is idempotent; accept-then-reject does not change a finalized request; concurrent reviewers yield one winner. |

## AUD-007 — Stale requests overwrite newer content and misstate history

| Field | Assessment |
|---|---|
| Issue ID | AUD-007 |
| Category | Backend |
| Severity | High |
| Location | [database.py:440](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:440), [database.py:517](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:517), [database.py:557](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:557), [database.py:563](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:563) |
| Evidence | Verified sequential reproduction; concurrent risk. T06: two requests based on "Original" were accepted in sequence; the second overwrote the first, while its audit old_text still said "Original". |
| Description | Neither target version nor current content is checked at decision time; the review UI labels a saved snapshot as current text. |
| Root Cause | Requests capture text without an expected version and writes use last-writer-wins semantics. |
| Impact | A legitimate newer amendment can be lost; historical diffs can be inaccurate. No simultaneous load test was run. |
| Recommended Fix | Store expected JD/clause version, compare it within the decision transaction, reject conflicts and show both the saved base and live current text. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | A stale request produces a conflict with no mutation; audit old_text equals the actual pre-update value. |

## AUD-008 — Approval status and document versions diverge from changed content

| Field | Assessment |
|---|---|
| Issue ID | AUD-008 |
| Category | Backend |
| Severity | High |
| Location | [database.py:519](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:519), [database.py:557](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:557), [database.py:577](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:577) |
| Evidence | Verified behavior. T08: editing an approved JD left it approved; T07: a responsibility edit incremented its clause version but left parent JD version at 1. approve-as-is does not check pending requests. |
| Description | Approval is not bound to a specific content revision, and child changes do not advance the document revision. |
| Root Cause | Document lifecycle and revision rules are not centralized. |
| Impact | An export can be presented as approved although its content changed since approval; version-based caches and traceability would be unreliable. |
| Recommended Fix | Define revision-bound approval, bump the parent on every content mutation and invalidate or explicitly renew approval according to agreed policy; prevent silent approval with unresolved conflicts. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | Field and responsibility edits both advance JD revision; approval identifies the exact revision; pending requests receive explicit treatment. |

## AUD-009 — Invalid targets can report success and create false audit events

| Field | Assessment |
|---|---|
| Issue ID | AUD-009 |
| Category | Backend |
| Severity | High |
| Location | [database.py:555](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:555), [database.py:563](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:563), [database.py:582](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:582) |
| Evidence | Verified behavior. T09: accepting an unsupported section returned success and wrote an audit row without changing content. T18: approving nonexistent JD 999 created an orphan audit event. |
| Description | Missing rows, unsupported sections and zero-row updates are not rejected consistently. |
| Root Cause | No whitelist validation before request creation and no affected-row checks before finalizing. |
| Impact | Users receive false confirmation and history records events that did not occur. |
| Recommended Fix | Validate typed targets and decisions, require exactly one changed target, and roll back request status and history on any invalid target. |
| Implementation Effort | Small |
| Priority | P1 |
| Verification | Unknown fields, missing JDs and inactive/missing responsibilities fail with no request transition or audit row. |

## AUD-010 — Relational and domain constraints are not enforced comprehensively

| Field | Assessment |
|---|---|
| Issue ID | AUD-010 |
| Category | Database |
| Severity | High |
| Location | [database.py:120](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:120), [database.py:133](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:133), [database.py:172](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:172), [database.py:185](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:185), [database.py:204](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:204) |
| Evidence | Verified configuration and synthetic violations. T03: connections using the current SQLite defaults have foreign_keys=0; T18: an orphan request with empty proposed text/reason was accepted. users.assigned_jd_id and audit.mod_request_id have no declared FK; no domain CHECK constraints are declared. |
| Description | Declared child relationships do not protect current writes; important identity, ordering and status constraints are absent. |
| Root Cause | Connection setup omits foreign-key enforcement and schema relies on UI validation. |
| Impact | Potential orphan rows and invalid states. The supplied database currently has zero declared-FK violations and zero dangling user assignments. |
| Recommended Fix | Audit existing rows first; enable FKs on every connection; add validated domain/relationship constraints via a versioned, reversible migration, preserving all existing IDs and history. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | Read-only preflight is clean; invalid writes fail in disposable fixtures; existing 26-card database migrates and restores without data loss. |

## AUD-011 — Request ownership and audit identity use mutable display names

| Field | Assessment |
|---|---|
| Issue ID | AUD-011 |
| Category | Database |
| Severity | Medium |
| Location | [app.py:659](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:659), [app.py:739](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:739), [database.py:193](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:193), [database.py:478](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:478), [database.py:212](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:212) |
| Evidence | Verified design risk. The UI submits and filters by full_name, although get_requests_by_user calls its parameter username. No user FK is stored for requester/reviewer. Current users have no duplicate full_name groups. |
| Description | Identity is ambiguous after a name change or when two people share a name. |
| Root Cause | Human-readable labels are used as primary identity references. |
| Impact | Future renames can hide requests or combine unrelated histories; current collision is not alleged. |
| Recommended Fix | Add immutable actor IDs, retain historical display-name snapshots and backfill only unambiguous matches; retain unresolved legacy attribution for manual review. |
| Implementation Effort | Medium |
| Priority | P2 |
| Verification | Two users with the same name see only their own requests; renames preserve ownership and historical labels. |

## AUD-012 — Audit trail is incomplete and does not prove immutable revision history

| Field | Assessment |
|---|---|
| Issue ID | AUD-012 |
| Category | Database |
| Severity | High |
| Location | [database.py:294](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:294), [database.py:512](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:512), [database.py:563](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:563), [database.py:631](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:631), [app.py:467](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:467), [README.md:30](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/README.md:30) |
| Evidence | Verified coverage gap; tampering risk. T11: rejecting a request wrote no jd_audit_trail event. Interview updates have no actor/history; imports log a filename summary rather than a full revision snapshot. Schema has no append-only guards or independent archive. SQLite CURRENT_TIMESTAMP and naive datetime.now are mixed in event timestamps; actual historical offsets were not established. |
| Description | The UI promises uneditable history beyond what this database implements. |
| Root Cause | Operational records and compliance evidence are treated as the same concern. |
| Impact | Rejections and interview changes lack event history; earlier complete documents cannot reliably be reconstructed. File owners could alter history; no in-app delete endpoint was found. |
| Recommended Fix | Record all decisions and schedule changes with actor IDs, consistent timezone-aware timestamps and revision references; preserve document snapshots and define append-only controls plus protected off-host backups. Qualify immutability claims. Preserve uncertain legacy timestamp provenance instead of guessing offsets. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | Every mutation has one attributable event; rejected requests and schedule edits are covered; a historical card can be reconstructed; restricted app access cannot edit events. |

## AUD-013 — Repeated imports duplicate cards and duplicate labels hide records

| Field | Assessment |
|---|---|
| Issue ID | AUD-013 |
| Category | Backend |
| Severity | Medium |
| Location | [database.py:433](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:433), [database.py:245](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:245), [app.py:321](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:321), [app.py:357](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:357), [app.py:561](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:561) |
| Evidence | Verified behavior; derived UI consequence. T10: two calls with the same file and parsed data created different IDs and two copies. Selectors use title+department as dictionary keys. No such duplicate title/department groups exist in the supplied DB. |
| Description | create_or_update_jd always inserts; equal selector labels overwrite earlier dictionary entries. |
| Root Cause | No defined import identity or idempotency policy; display labels double as keys. |
| Impact | A repeat upload can silently create competing cards; some duplicates become inaccessible through the selectors. |
| Recommended Fix | Add file fingerprints and an explicit new-card versus new-revision decision; use IDs as selector values with disambiguated display labels. Preserve existing copies for reconciliation. |
| Implementation Effort | Medium |
| Priority | P2 |
| Verification | Repeated upload prompts for a deliberate action; all records remain selectable even with matching titles. |

## AUD-014 — Word export cannot be re-imported without content loss

| Field | Assessment |
|---|---|
| Issue ID | AUD-014 |
| Category | Backend |
| Severity | High |
| Location | [docx_parser.py:65](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:65), [docx_parser.py:93](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:93), [docx_parser.py:112](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:112), [docx_parser.py:215](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:215), [docx_parser.py:228](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:228) |
| Evidence | Verified behavior. T14: a synthetic exported DOCX reopened successfully, but re-parsing lost purpose and all responsibilities. The exporter uses paragraph sections and a three-column responsibility table; the parser expects purpose tables and a different header/column layout. |
| Description | The application does not support its own exported format. |
| Root Cause | Parser and exporter implement different document contracts. |
| Impact | Users who round-trip a reviewed document through upload lose structured content and may import a misleading new card. |
| Recommended Fix | Define supported format versions; make parser/exporter share a schema and preserve values across the supported round trip; reject unsupported layouts with a useful message. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | All critical synthetic fields, Arabic text, responsibility order and KPIs survive export→parse; all original fixtures remain supported. |

## AUD-015 — Competencies and stored approvals are omitted from views and exports

| Field | Assessment |
|---|---|
| Issue ID | AUD-015 |
| Category | Frontend |
| Severity | Medium |
| Location | [app.py:389](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:389), [app.py:665](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:665), [docx_parser.py:268](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:268), [docx_parser.py:316](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:316) |
| Evidence | Verified implementation and synthetic export. T14: distinct competency and approval sentinel strings were absent from the generated DOCX. Both full-card views skip competencies; export renders blank signature boxes instead of stored approvals. All 26 current competency fields are empty. |
| Description | A user can request a competency edit without a normal full-card display or export of the accepted value. Existing imported approvals are not preserved in export. |
| Root Cause | UI/export field lists have drifted from the stored schema. |
| Impact | Accepted content can disappear from the official artifact; stored approval text is replaced by a blank signature template. |
| Recommended Fix | Render all supported fields from a shared section registry; distinguish legacy signature text from revision-bound electronic approvals and do not fabricate evidence. |
| Implementation Effort | Small |
| Priority | P1 |
| Verification | Populated competency fields appear in both roles and exports; stored approval information is preserved or explicitly identified as legacy source evidence. |

## AUD-016 — Word imports accept incomplete and unrelated documents

| Field | Assessment |
|---|---|
| Issue ID | AUD-016 |
| Category | Backend |
| Severity | Medium |
| Location | [docx_parser.py:65](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:65), [docx_parser.py:164](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:164), [app.py:295](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:295), [app.py:321](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:321), [database.py:249](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:249) |
| Evidence | Verified validation gap. T18: a paragraph-only unrelated DOCX produced an importable title and zero responsibilities. All 26 source files parse without exceptions, but one has zero responsibilities; all source parses yield empty job_code and competencies. |
| Description | There is no required-field or template validation gate before insertion; preview shows only selected fields. |
| Root Cause | Parsing success is equated with business-valid content. |
| Impact | Malformed or incomplete cards enter the catalog; silent field omissions can be mistaken for source truth. Empty source fields alone do not establish a parser defect. |
| Recommended Fix | Introduce import diagnostics, supported-template checks, per-field completeness review and explicit confirmation for incomplete drafts. Compare source values rather than silently defaulting. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | Unrelated documents fail validation; incomplete legitimate documents remain quarantined/draft with visible warnings; complete fixtures retain their content. |

## AUD-017 — Saving an interview form can overwrite existing notes and status

| Field | Assessment |
|---|---|
| Issue ID | AUD-017 |
| Category | UX |
| Severity | High |
| Location | [app.py:525](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:525), [app.py:528](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:528), [app.py:529](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:529), [app.py:534](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:534), [database.py:631](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:631) |
| Evidence | Verified source behavior; UI execution unavailable. The form always initializes the first status option and an empty text area; it does not load the chosen interview values. The database operation replaces both stored values. |
| Description | An admin saving without retyping existing content replaces it with empty notes/default status. |
| Root Cause | Edit fields are not bound to the selected record. |
| Impact | Previously recorded meeting outcomes can be lost through an ordinary edit. Browser execution was not completed in this environment. |
| Recommended Fix | Load selected row values before constructing the form, key state by interview ID/revision and prevent stale overwrites; show a save result that survives rerun. |
| Implementation Effort | Small |
| Priority | P1 |
| Verification | A no-change save preserves notes and status; switching interview never carries another row’s draft; stale edits conflict safely. |

## AUD-018 — Empty catalogs and invalid assignments can crash employee pages

| Field | Assessment |
|---|---|
| Issue ID | AUD-018 |
| Category | Frontend |
| Severity | High |
| Location | [app.py:545](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:545), [app.py:547](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:547), [app.py:568](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:568), [app.py:573](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:573), [app.py:770](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:770) |
| Evidence | Verified reachable code assumptions. Fallback unconditionally reads all_jds[0]; a non-null dangling assigned ID produces jd=None and then subscripting. The directory selects columns from an empty DataFrame. Current supplied assignments are valid. |
| Description | The employee journey has no safe empty/unassigned/missing-card branch. |
| Root Cause | Catalog completeness is assumed despite fallible bootstrap/imports. |
| Impact | Fresh or partially initialized deployments can fail instead of guiding a user to HR; fallback can attach an arbitrary first card. |
| Recommended Fix | Render explicit unavailable/unassigned states; require an authorized assignment and never use the first catalog record as identity policy. |
| Implementation Effort | Small |
| Priority | P1 |
| Verification | Empty DB, missing assigned JD and absent department match produce helpful non-mutating states without exceptions. |

## AUD-019 — Legacy English statuses are inconsistently interpreted

| Field | Assessment |
|---|---|
| Issue ID | AUD-019 |
| Category | Frontend |
| Severity | Medium |
| Location | [app.py:344](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:344), [app.py:371](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:371), [app.py:745](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:745), [database.py:503](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:503), [database.py:650](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:650) |
| Evidence | Verified data/source mismatch. The current DB contains one request with status Accepted; request UI recognizes only Arabic accepted/rejected labels and styles everything else as under review. Dashboard supports English Approved, while explorer filter/badges do not. |
| Description | Status vocabulary varies between stored legacy records, queries and UI. |
| Root Cause | Localized display strings are used as persistent business-state values. |
| Impact | Completed legacy requests can appear pending; filters and counts can disagree. |
| Recommended Fix | Introduce canonical status codes and a shared compatibility mapping; migrate known values safely and retain unknown values for explicit review. |
| Implementation Effort | Small |
| Priority | P1 |
| Verification | Fixtures covering all observed English/Arabic statuses show consistent labels, colors, filters and counts; unknown states are visibly unknown. |

## AUD-020 — Unescaped stored text is inserted into raw HTML

| Field | Assessment |
|---|---|
| Issue ID | AUD-020 |
| Category | Security |
| Severity | Medium |
| Location | [app.py:212](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:212), [app.py:220](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:220), [app.py:234](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:234), [app.py:497](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:497), [app.py:681](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:681), [auth.py:97](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:97), [utils.py:10](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/utils.py:10) |
| Evidence | Verified HTML interpolation; browser exploit not tested. Request text, justifications, card sections and names are placed in unsafe_allow_html=True strings without html.escape. The separate word-diff helper correctly escapes its input (T12). |
| Description | Untrusted content can become HTML markup in multiple views. |
| Root Cause | Presentation templates mix content with trusted HTML. |
| Impact | Stored markup can alter the page or insert deceptive links/images. Arbitrary script execution and a working XSS exploit were not established. |
| Recommended Fix | Use plain Streamlit text components or escape every dynamic value before HTML interpolation; centralize safe rendering and retain escaped diff generation. |
| Implementation Effort | Small |
| Priority | P1 |
| Verification | Markup payloads render as literal text in every relevant surface; no injected links/images/styles; browser security checks confirm sanitizer behavior. |

## AUD-021 — Cross-origin protection is explicitly disabled

| Field | Assessment |
|---|---|
| Issue ID | AUD-021 |
| Category | Security |
| Severity | High |
| Location | [.streamlit/config.toml:10](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/.streamlit/config.toml:10) |
| Evidence | Verified effective configuration; exploitation not tested. T17: installed Streamlit 1.66.1 reports enableCORS=False and enableXsrfProtection=True; its warning states XSRF does not protect WebSocket origin checks. |
| Description | Cross-origin connections are accepted under the inspected runtime despite XSRF being enabled. |
| Root Cause | An insecure deployment setting is shipped as the default. |
| Impact | Untrusted origins may connect to the service. Exact production exposure, reverse-proxy controls and exploitation were not assessed. |
| Recommended Fix | Enable CORS protection, set trusted origins and hostnames for the chosen environment, retain XSRF protection and verify proxy/WebSocket behavior. |
| Implementation Effort | Small |
| Priority | P1 |
| Verification | Allowed origins work; hostile origins and unexpected hosts fail; legitimate uploads work with XSRF protection enabled. |

## AUD-022 — Uploads lack document-specific resource limits

| Field | Assessment |
|---|---|
| Issue ID | AUD-022 |
| Category | Security |
| Severity | Medium |
| Location | [app.py:282](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:282), [app.py:295](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:295), [docx_parser.py:37](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:37), [.streamlit/config.toml:8](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/.streamlit/config.toml:8) |
| Evidence | Verified missing safeguards; denial-of-service risk. Multiple uploads are parsed synchronously; no archive expanded-size, entry count, document structure or batch budget exists. Effective per-file Streamlit limit is 200 MB; largest supplied uncompressed DOCX is about 498 KB. |
| Description | Extension filtering is the principal upload gate; it is not a safe document budget. |
| Root Cause | No bounded ingestion policy for ZIP/XML documents. |
| Impact | A large or highly compressed document could exhaust memory or delay a session; no zip-bomb or load attack was executed. |
| Recommended Fix | Set a justified small file/batch limit; inspect ZIP metadata safely, cap expanded size/entries and parse only on an explicit action; avoid exposing parser internals in user errors. |
| Implementation Effort | Small |
| Priority | P2 |
| Verification | Over-budget synthetic fixtures reject early with bounded resource use; normal 26-document corpus still imports. |

## AUD-023 — Deployment packages mutable business data without a recovery plan

| Field | Assessment |
|---|---|
| Issue ID | AUD-023 |
| Category | Architecture |
| Severity | High |
| Location | [database.py:14](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:14), [Dockerfile:24](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/Dockerfile:24), [.dockerignore:1](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/.dockerignore:1), [README.md:68](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/README.md:68) |
| Evidence | Verified packaging gap; data-loss/exposure risk. DB path is fixed next to source; COPY . . includes the existing DB, Word corpus and workbook. No .gitignore, volume/deployment manifest, backup/restore runbook or retention configuration exists; README suggests git add . |
| Description | Deployment and mutable business records are coupled; deployment instructions do not establish durable storage or protected backups. |
| Root Cause | Prototype filesystem persistence is treated as production persistence. |
| Impact | Container replacement without a mounted durable path can lose changes; broad publishing/build access could expose data. No actual repository publication or data loss was verified. |
| Recommended Fix | Externalize the DB path, document persistent single-instance storage and consistent backups with restore drills; exclude real data from source/build artifacts and use sanitized demo fixtures separately. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | Restart/redeploy retains records in staging; a backup restores counts and history; build context/source publishing excludes live data. |

## AUD-024 — Dependency versions are unbounded and permit known vulnerable runtimes

| Field | Assessment |
|---|---|
| Issue ID | AUD-024 |
| Category | Security |
| Severity | High |
| Location | [requirements.txt:1](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/requirements.txt:1), [Dockerfile:2](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/Dockerfile:2), [Dockerfile:20](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/Dockerfile:20) |
| Evidence | Verified manifest risk; installed versions not shown affected. All four direct dependencies have minimum-only constraints. streamlit>=1.35.0 permits versions below the Windows security fixes 1.37.0 and 1.54.0. Installed Streamlit is 1.66.1; pip check passes; no full transitive advisory scan ran. |
| Description | Builds are not reproducible and the allowed version range includes known affected releases. |
| Root Cause | No lockfile, supported-runtime matrix or vulnerability gate. |
| Impact | Future resolution and older environments can diverge; the two cited advisories do not establish vulnerability of the installed 1.66.1 runtime or Linux image. |
| Recommended Fix | Select and lock supported versions with hashes, align local/container Python, and add dependency/advisory scanning to CI; update on a tested schedule. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | Clean locked builds reproduce resolved versions; known advisories are excluded; direct/transitive scan is reviewed on target Windows/Linux platforms. |

## AUD-025 — No regression suite or CI validation is supplied

| Field | Assessment |
|---|---|
| Issue ID | AUD-025 |
| Category | Testing |
| Severity | High |
| Location | [app.py:1](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:1), [database.py:493](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:493), [requirements.txt:1](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/requirements.txt:1) |
| Evidence | Verified absence and command result. T16: pytest collection found no tests. Recursive inventory found no test files, test configuration or CI workflow. Audit probes are documented but are not an installed regression suite. |
| Description | Business-critical mutations, document interchange and roles have no repeatable repository quality gate. |
| Root Cause | Demonstration workflows were built without executable acceptance coverage. |
| Impact | The reproduced integrity/security defects can recur; changes lack automated confidence. |
| Recommended Fix | First capture isolated regression fixtures for reproduced bugs; then add service integration tests, role-focused Streamlit tests and CI against supported Python versions. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | Every P0/P1 defect has a failing-before/fixed-after test; CI runs safe synthetic tests and never opens a live DB. |

## AUD-026 — Reruns repeat broad queries, imports and exports

| Field | Assessment |
|---|---|
| Issue ID | AUD-026 |
| Category | Architecture |
| Severity | Medium |
| Location | [app.py:29](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:29), [app.py:166](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:166), [app.py:295](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:295), [app.py:336](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:336), [app.py:380](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:380), [app.py:470](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:470), [database.py:387](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:387) |
| Evidence | Verified execution pattern; scaling risk, no present bottleneck. Default tabs compute all content; admin reads catalog twice, loads all history and renders all pending requests. EXPLAIN shows correlated child table scans and no application indexes. Local 26-card query median is 0.705 ms over 25 runs. |
| Description | Each widget rerun can do work for hidden tabs, rebuild a DOCX and reparse retained uploads. |
| Root Cause | Eager top-level orchestration, broad fetches and no scoped cache/pagination. |
| Impact | Larger history/upload/user volumes may increase latency and memory. Current timings do not justify a database rewrite. |
| Recommended Fix | Measure end-to-end reruns; use compatible conditional navigation, explicit parse/export actions, bounded history, selective indexes and identity/revision-aware caching after version fixes. |
| Implementation Effort | Medium |
| Priority | P2 |
| Verification | Hidden workflows do no expensive work; larger synthetic fixtures meet an agreed latency budget; authorization and cache invalidation regressions pass. |

## AUD-027 — Duplicated card rendering and broad CSS increase UI drift

| Field | Assessment |
|---|---|
| Issue ID | AUD-027 |
| Category | Frontend |
| Severity | Medium |
| Location | [app.py:389](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:389), [app.py:665](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:665), [utils.py:54](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/utils.py:54), [utils.py:64](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/utils.py:64), [utils.py:97](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/utils.py:97) |
| Evidence | Verified structure; visual effects not assessed. Two large role-specific card renderers have diverged fields; CSS targets global tags and Streamlit data-testid/data-baseweb selectors. No responsive media rules are supplied; Google Fonts is fetched externally with local fallbacks. |
| Description | UI consistency depends on maintaining duplicate templates and framework-internal selectors. |
| Root Cause | No reusable section renderer or scoped presentation contract. |
| Impact | Field omissions recur; framework upgrades can alter layout. Actual mobile, RTL assistive-technology and contrast behavior remain untested. |
| Recommended Fix | Share a read-only card renderer and field registry; keep role-specific actions separate, scope CSS and verify responsive/keyboard/RTL behavior on the locked framework version. |
| Implementation Effort | Medium |
| Priority | P2 |
| Verification | Both roles show the same supported content; desktop/mobile Arabic review passes; CSS does not restyle unrelated widgets unexpectedly. |

## AUD-028 — Database failures lack controlled rollback, cleanup and useful observability

| Field | Assessment |
|---|---|
| Issue ID | AUD-028 |
| Category | Backend |
| Severity | Medium |
| Location | [database.py:433](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:433), [database.py:493](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:493), [database.py:572](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:572), [database.py:631](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:631), [database.py:313](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:313), [app.py:330](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:330) |
| Evidence | Verified code gap; failure modes not fault-injected. Connections close only on normal paths; mutation handlers lack try/finally or context managers, startup prints exceptions, and upload UI displays raw exception text. No structured operation/error logs are supplied. |
| Description | An exception can escape the UI, defer connection cleanup and provide little operational context. |
| Root Cause | Persistence, exception translation and logging are not centralized. |
| Impact | Potential lock/resource retention, poor recovery feedback and disclosure of implementation details. An actual lock leak was not measured. |
| Recommended Fix | Use explicit transaction/connection lifetime management, rollback on errors, safe user messages and structured logs with actor/request IDs; avoid logging passwords or document bodies. |
| Implementation Effort | Medium |
| Priority | P2 |
| Verification | Injected mid-operation failures leave all related rows unchanged and close connections; logs are useful and contain no sensitive payloads. |

## AUD-029 — Partial bootstrap can permanently skip missing users and schedules

| Field | Assessment |
|---|---|
| Issue ID | AUD-029 |
| Category | Architecture |
| Severity | High |
| Location | [app.py:29](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:29), [database.py:233](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:233), [database.py:235](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:235), [database.py:299](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:299), [database.py:303](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:303), [database.py:317](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:317) |
| Evidence | Verified synthetic failure scenario. T18: after a synthetic interrupted bootstrap committed one JD, the next init_db skipped missing user creation because JD count was nonzero. Per-file imports commit separately; seed errors are printed and swallowed. |
| Description | Initialization completeness is determined only by the JD table count and is retried on every script run. |
| Root Cause | Schema creation, business imports and account provisioning are coupled. |
| Impact | A partially initialized deployment can appear populated while accounts or meetings are absent; concurrent cold starts may seed duplicates. Simultaneous bootstrap was not tested. |
| Recommended Fix | Separate explicit provisioning/import jobs from normal startup; add a schema version and idempotent per-step state with transactional boundaries and actionable failure reporting. |
| Implementation Effort | Medium |
| Priority | P1 |
| Verification | Interrupted provisioning resumes missing steps exactly once; production requests never seed demo accounts; existing data survives upgrades. |

## AUD-030 — Operational account and assignment administration is missing

| Field | Assessment |
|---|---|
| Issue ID | AUD-030 |
| Category | UX |
| Severity | Medium |
| Location | [auth.py:19](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:19), [database.py:350](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:350), [database.py:669](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:669), [app.py:118](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:118) |
| Evidence | Verified missing capability; production-readiness recommendation. No account create/disable/reset, assignment editor or persistent account/session revocation workflow exists in the supplied UI/code. Accounts come from fixed seeding. |
| Description | HR cannot maintain real employee access through a supported administrative workflow. |
| Root Cause | Account lifecycle remains a seed-data concern. |
| Impact | Offboarding, password recovery and assignment correction require unsafe manual database work. These are production capabilities proposed by the audit, not pre-existing contractual features. |
| Recommended Fix | Adopt an identity provider or add controlled account administration with explicit assignment policy, actor logging and disabled-user/session checks. |
| Implementation Effort | Medium |
| Priority | P2 |
| Verification | HR can safely provision, disable and reassign synthetic users; disabled users lose access; operations are attributable. |

## AUD-031 — Session transitions retain unrelated state and have no freshness policy

| Field | Assessment |
|---|---|
| Issue ID | AUD-031 |
| Category | Security |
| Severity | Medium |
| Location | [auth.py:10](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:10), [auth.py:19](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:19), [auth.py:31](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:31), [auth.py:118](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:118) |
| Evidence | Verified state behavior; exposure risk. T04: an unrelated synthetic draft key survived both user switching and logout; only four auth keys are reset. Role/user_info are cached for the session; no idle expiry or account revocation recheck exists. |
| Description | The session can retain drafts from a prior identity and stale authorization state. |
| Root Cause | No explicit session lifecycle or per-user draft namespace. |
| Impact | Potential cross-account draft carryover in a shared browser; disabled or changed accounts cannot be promptly revalidated. Widget-specific visible disclosure was not browser-tested. |
| Recommended Fix | Clear or namespace user-specific widget state on authentication changes; establish idle/max age and recheck active role/account state for sensitive actions. |
| Implementation Effort | Small |
| Priority | P2 |
| Verification | Logout/login across two users does not retain another user’s draft; expired/disabled sessions cannot write. |

## AUD-032 — Official views fabricate missing identifiers and safety/approval content

| Field | Assessment |
|---|---|
| Issue ID | AUD-032 |
| Category | UX |
| Severity | High |
| Location | [app.py:393](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:393), [app.py:452](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:452), [app.py:723](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:723), [docx_parser.py:181](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:181), [docx_parser.py:196](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:196), [docx_parser.py:294](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:294), [docx_parser.py:335](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:335) |
| Evidence | Verified output logic. All 26 stored job codes are empty, so exports use the same 3S-JD-001 fallback. Four cards have empty hazards/safety fields, triggering office-work safety assertions. Export heading says approved even when stored status is under review. |
| Description | Missing data is rendered as authoritative content rather than unknown/incomplete, and draft exports carry an approved headline. |
| Root Cause | Presentation defaults substitute business facts and static marketing labels. |
| Impact | Cards can be misidentified or present unreviewed safety/approval claims. The footer still includes actual status, creating contradictory signals. |
| Recommended Fix | Show missing values explicitly, allocate real unique identifiers under a controlled policy, remove invented safety text and label draft/approved exports consistently with revision-bound approval. |
| Implementation Effort | Small |
| Priority | P1 |
| Verification | Every draft is clearly marked; missing safety fields remain visibly incomplete; exports have stable unique IDs without altering legacy records silently. |

## AUD-033 — Promised edit coverage excludes important card fields

| Field | Assessment |
|---|---|
| Issue ID | AUD-033 |
| Category | UX |
| Severity | Medium |
| Location | [app.py:600](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:600), [app.py:610](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:610), [app.py:623](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:623), [database.py:527](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:527) |
| Evidence | Verified UI gap. The request selector exposes eight text sections and responsibility descriptions, but no KPI, dimensions, job code or profile-field edits. Backend field_map supports some additional fields but no KPI target. |
| Description | The interface cannot request changes to every clause promised in the product text. |
| Root Cause | Editable fields are duplicated in disconnected lookup lists and lack typed targets. |
| Impact | Reviewers must work outside the system to correct KPIs and other material sections. Scope beyond the README’s any-clause wording needs product-owner validation. |
| Recommended Fix | Agree a supported field matrix; add explicit typed targets for KPIs and required metadata; use one section registry for UI, validation and review. |
| Implementation Effort | Medium |
| Priority | P2 |
| Verification | Each agreed editable field can be proposed, reviewed, versioned, displayed and exported without losing the other fields. |

## AUD-034 — Interview time is stored but omitted from the schedule view

| Field | Assessment |
|---|---|
| Issue ID | AUD-034 |
| Category | UX |
| Severity | Low |
| Location | [database.py:226](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:226), [database.py:336](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:336), [app.py:513](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:513) |
| Evidence | Verified presentation omission. meeting_time is imported and returned but the displayed schedule dictionary has no meeting-time column. |
| Description | Users cannot see an available meeting-time field in the schedule table. |
| Root Cause | Display schema omits an existing model field. |
| Impact | Meeting coordination requires opening the original workbook or another source. Current nonempty meeting-time values were not inspected. |
| Recommended Fix | Display the meeting-time column with an explicit missing-value label and consistent local date/time formatting. |
| Implementation Effort | Small |
| Priority | P3 |
| Verification | A synthetic meeting with a populated time displays it correctly; missing times show as unspecified. |

## AUD-035 — Container privileges and health checks are minimal

| Field | Assessment |
|---|---|
| Issue ID | AUD-035 |
| Category | Security |
| Severity | Medium |
| Location | [Dockerfile:2](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/Dockerfile:2), [Dockerfile:13](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/Dockerfile:13), [Dockerfile:30](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/Dockerfile:30), [Dockerfile:33](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/Dockerfile:33) |
| Evidence | Verified configuration; deployment risk. The image has no USER directive, retains build tools and checks only the Streamlit HTTP health route. PORT is defined but launch hardcodes 8501. Docker is unavailable here. |
| Description | Container hardening, application readiness and host runtime expectations are unspecified. |
| Root Cause | A development-oriented image is the only supplied deployment artifact. |
| Impact | Elevated process privileges increase impact if compromised; a responsive HTTP server can still have broken application/database workflows. No container exploit/build failure was verified. |
| Recommended Fix | Run with a restricted user and durable-directory permissions, reduce build packages, align port configuration and add a safe readiness/restore smoke test in deployment validation. |
| Implementation Effort | Small |
| Priority | P2 |
| Verification | Staging runs without root, retains data across restart and detects unavailable schema/storage; target port routing works. |

