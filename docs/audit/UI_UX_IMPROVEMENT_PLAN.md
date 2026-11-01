# UI and UX improvement plan

Audit date: 29 October 2026. Assessment is based on source, aggregate data and isolated function probes. Browser rendering, mobile layouts, screen readers and Word print layout were **not verified**. Visual/accessibility recommendations below are validation tasks, not claims of observed failures.

Evidence and issue details: [docs/audit/ISSUE_REGISTER.md](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docs/audit/ISSUE_REGISTER.md). No UI changes were implemented.

## Product experience to preserve

The application already has a coherent Arabic review purpose, clear role-oriented tabs, explicit old/proposed text, a word-level diff with escaped output, Arabic labels, RTL styling, card counts, request-empty states and structured import preview. Preserve broad directory browsing for coordination; distinguish it from authority to approve unrelated cards.

The largest usability improvements are about truthful content and safe decisions. Cosmetic restyling alone would leave the material workflow problems intact.

## Prioritized journey repairs

| Order | Journey / evidence | Proposed change | Dependencies | Acceptance |
|---:|---|---|---|---|
| 1 | Login and account change: [auth.py:54](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:54), [auth.py:110](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:110); AUD-001–003/031 | Remove demo credentials/impersonation from real data operation; show the current identity clearly; clear or isolate prior-user drafts | Authentication/session policy | Normal users cannot become another user; logout/login does not carry another person’s draft |
| 2 | Assigned card: [app.py:545](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:545), [app.py:561](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:561); AUD-004/018 | Separate “my assigned card” from directory browsing; show a useful unassigned state with HR guidance; expose actions only when authorized | Assignment-aware service | Empty/unassigned cards never crash or silently choose another person’s card; unauthorized writes fail server-side |
| 3 | HR review: [app.py:199](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:199), [app.py:212](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:212); AUD-006/007/020 | Label submitted base text and actual current text separately; show a conflict state and prevent stale/replayed decisions; render untrusted text safely | Conditional transaction and revision rules | Two reviewers cannot silently finalize one request twice; changed-base request requires renewed review |
| 4 | Interview editing: [app.py:525](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:525); AUD-017 | Load chosen interview’s current notes/status, isolate draft by record, make “save unchanged” safe | Record revision/freshness policy | No-change save preserves every existing value; switching interview never overwrites another record’s notes |
| 5 | Card display/export: [app.py:389](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:389), [docx_parser.py:181](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:181); AUD-015/032 | Show all supported sections, distinguish missing from populated, use truthful draft/approval labels and real IDs | Shared section registry, revision-bound approval | Missing hazards stay missing; competencies appear; draft heading/footer agree; no repeated invented identifiers |
| 6 | Import: [app.py:295](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:295); AUD-013/014/016 | Add full-field extraction review, warnings, duplicate detection and explicit new-card/new-revision choice; validate template/language coverage | Document contract and safe import policy | Unrelated DOCX rejected; incomplete legitimate card visibly remains draft; repeat import requires an explicit choice |
| 7 | Request composition: [app.py:600](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:600); AUD-033 | Add agreed KPI/dimensions/profile edit targets; label target and version clearly; keep text and KPI edits distinct | Typed target model, product field matrix | Every supported editable value completes submit→review→display→export correctly |
| 8 | Request tracking/history: [app.py:739](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:739), [app.py:467](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:467); AUD-011/012/019 | Canonical state labels, immutable ownership, visible decision trail and revision links; qualify history guarantees | Actor IDs, canonical statuses, event coverage | Legacy Accepted displays accepted; own-request lists survive renames; rejected requests have decision events |
| 9 | Schedule view: [app.py:513](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:513); AUD-034 | Display meeting time and explicit missing dates/times; format consistently for Cairo users | Field presentation only | Synthetic populated time is visible and blank time is “unspecified” |
| 10 | Account operations: AUD-030 | Provide supported account disable/reset/assignment workflow or identity-provider path | Agreed identity strategy | Authorized HR can maintain access without direct database editing |

## Proposed screen behavior

**Staff landing:** show assigned card title, document revision, current review/approval status and next action. When no assignment exists, explain the condition and direct the user to the established HR process. Do not fabricate an assignment from the first catalog entry.

**Card review:** use one read-only section renderer for both roles. Every supported section has a clear label and an explicit “not supplied” state. Keep large responsibilities/KPI tables readable; offer detail expansion when long text makes comparisons difficult. Restrict edit controls by permissions and supported targets.

**Amendment form:** bind draft state to actor ID + JD ID + target + base revision. Validate nonempty changed text/reason on client-facing submit and in the service. Preserve a user’s draft when a recoverable error occurs. On conflict, explain what changed and let the user refresh/rebase intentionally.

**HR queue:** offer bounded list/filter controls for pending requests rather than expanding every item indefinitely. Show request actor/time, target JD/revision and justification before decision. On accept/reject, keep a visible outcome or receipt after rerun and prevent repeat action. A rejection reason policy should be confirmed with HR; the audit does not invent a mandatory one.

**Import review:** distinguish successful file parsing from a complete JD. Show all parsed sections, not only the first four responsibilities and a truncated purpose. Identify extraction warnings and unsupported formats/languages. Keep original source provenance. Do not call dictionary normalization “automatic translation of all prose.”

**Export:** label draft versus approved revision consistently. Include all supported stored fields and a clear distinction between blank physical signature areas, source-imported approval text and actual electronic approval events. The current footer’s real status does not excuse an approved headline on a draft.

**Interview outcomes:** bind the existing record before rendering the form; display the current stored values and revision. Capture who changed the outcome and when. Allow notes to be cleared deliberately, without making blank the accidental initial value.

## Component and styling plan

Use a shared card renderer, section definitions, status-label/badge mapping, safe-text helper and record-specific form keys. Keep action controls separate so permissions are easy to review. Avoid a full design-system rebuild until these repeated elements are centralized.

Scope CSS to intentional wrappers where possible. Global tag rules and framework-internal selectors in [utils.py:64](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/utils.py:64) can change across upgrades. Retain the existing Arabic font fallbacks; consider a packaged approved font only if offline/privacy deployment requirements justify it. Loading Google Fonts is an external dependency to document, not an established privacy violation.

Suggested consistency tokens: spacing, primary action, destructive/reject action, border/color states, Arabic typography hierarchy and section heading levels. Use both text and color for statuses and diff changes; the current +/- diff notation is worth preserving.

## Visual, responsive and accessibility validation backlog

These checks remain **unassessed**, so no UI/UX score was invented.

| Test surface | Scenarios | Proposed acceptance |
|---|---|---|
| Desktop RTL | Full card, long job title, mixed Arabic/English KPI, long justification | No clipping/overlap; readable text order; stable headings/table labels |
| Small screen | Approx. 360–390 px wide staff card, login/sidebar, HR comparison and schedule | Main tasks usable without horizontal page scrolling; table overflow is deliberate and labeled |
| Tablet/large desktop | Portrait/landscape, two-column compare, six admin tabs | Navigation remains discoverable; primary action remains identifiable |
| Keyboard | Login, tab navigation, request form, expander, accept/reject, download | All actionable controls reachable and focus visible; no focus traps |
| Screen reader | Arabic labels, headings, status changes, errors and diff content | Correct language/reading order; meaningful names; changes conveyed in text |
| Zoom/text | 200% zoom, long unbroken tokens | Content and actions remain usable; text is not truncated without access to full content |
| Color/contrast | Badges, new/deleted diff, primary/reject actions | Validate against the organization’s chosen WCAG 2.2 AA target; no result asserted before measurement |
| Empty/loading/error | No JD, unassigned user, no requests, invalid upload, stale edit, locked DB | Clear next action; no traceback; no silent loss; retry only where safe |
| State transition | Switch target/JD/interview, submit then rerun, logout/login | Draft ownership correct; feedback persists long enough to understand; repeated submit safe |
| Word output | Arabic/English text, multiple pages, long tables and signatures | Reopen and visually inspect in target Word/PDF renderer; no missing rows or misleading approval state |

WCAG target and supported devices are proposed acceptance choices to confirm, not pre-existing contractual requirements. The [W3C WCAG 2.2 recommendation](https://www.w3.org/TR/WCAG22/) is the reference for any later conformance evaluation.

## Product simplifications and proposed enhancements

After correctness, consider one task-oriented landing view instead of requiring users to infer workflow from several tabs. Preserve familiar labels and validate with HR plus at least one manager and one employee. Use explicit status summaries to avoid separate counts and lists disagreeing.

Proposed later enhancements, subject to product-owner agreement: assignment exceptions for executives, in-app due/decision notifications, revision-to-revision comparison, interview reminders and controlled bulk import. These are not missing original requirements and should not delay the release-blocking repairs.

## Delivery sequence and exit criteria

First ship access/state/form preservation and truthful document status. Next share rendering/status definitions and restore complete supported-field coverage. Then validate actual desktop/mobile/accessibility behavior and iterate on navigation. Finally consider optional notifications and workflow automation.

Exit this plan only after the same approved sample card has consistent content/status across both roles, review history and Word output; no-change interview editing preserves data; empty/conflict/error journeys are safe; and the agreed browser/device/accessibility matrix is actually executed.

