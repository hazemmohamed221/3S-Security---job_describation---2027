# Comprehensive JD editor

Implemented on 2 November 2026 for the existing Python/Streamlit application and
both SQLite and PostgreSQL adapters. No remote deployment or business-row edits
were performed as part of this implementation.

## Editing and governance

Authenticated `admin`, `hr`, and `editor` accounts can use **✏️ تعديل شامل لبطاقة
الوصف الوظيفي** from the directory for Draft or Pending Review cards, including
their canonical Arabic and legacy English spellings. Approved cards still require
the existing reason-based revocation first. Rejected cards do not expose direct
editing. The quick Draft core editor remains available for existing workflows.

The full editor has four internal tabs:

1. General information and reporting structure: title, job code, department,
   sector, supervisor, subordinates, grade, supervisory dimensions and source
   approval text. Source approval text does not confer electronic approval.
2. Purpose, work environment and requirements: purpose, working conditions,
   education, experience, certifications, languages, the original combined
   qualification text, hazards and safety practices.
3. Authority, responsibilities and KPIs: edit each responsibility and its order,
   add new rows, and remove rows from the active list.
4. Skills, technical/behavioral competencies and criteria, and internal/external
   relationships.

New fields use eight additive nullable TEXT columns: `subordinates`, `job_grade`,
`working_conditions`, `education`, `experience`, `certifications`, `languages`,
and `skills`. Existing `qualifications`, `dimensions`, competencies and other
source content are retained without automatic splitting or rewriting.

UI additions/deletions remain unsaved until **أؤكد حفظ التعديلات على هذا الإصدار**
is checked and **💾 حفظ التعديل الشامل** is clicked. Cancel discards the draft.
Dynamic rows retain typed values through add/remove reruns. Successful saves retain
the selected card even when its title, department or filter membership changes.
The new details are visible in both the HR and assigned-card read-only views.

## API contract and atomicity

```python
update_jd_full_details(card_id, actor_id, actor_name, core_fields, responsibilities,
                       *, expected_version=None) -> tuple[bool, str]
```

`core_fields` is a partial dictionary of editable content fields. The aliases
`job_title`, `direct_manager`, and `job_purpose` map to the existing `title`,
`reports_to`, and `purpose` columns. Omitted fields are preserved. Explicit empty
strings clear optional text; blank titles, unknown/protected fields and non-text
values are rejected. Identity, status, revision, source-file identity, timestamps
and governance tokens cannot be supplied through this dictionary.

`responsibilities` is the complete desired active list. Each item contains a
required nonblank `description`, optional `kpi`, optional positive unique
`item_order`, and an optional existing `id`. Existing IDs must belong to active
rows on this card. Omitted KPIs/orders preserve existing values; new orders
default to the list position. New rows omit `id`. An empty list explicitly removes
all active responsibilities.

Removed rows are archived with `is_active=0` and retain their IDs/text for audit
references; they disappear from active reads and Word exports. Updated rows keep
their IDs and increment their own revision. New rows receive fresh IDs. Duplicate,
inactive or other-card IDs cannot be injected or reactivated.

Validation, metadata changes, responsibility synchronization, revision advancement
and one immutable `full_update` audit event commit together. An audit failure
rolls back every content change, including inserted/archived responsibilities.
The event records the verified actor ID/name, UTC timestamp, changed fields and
responsibility IDs, exact before/after text, and hash-verified full snapshots.
Caller-supplied display names cannot forge attribution.

One successful changed save advances the existing **integer** parent revision
once, for example 7 → 8, while retaining Draft/Pending Review status. Decimal
revisions are not introduced into the existing integer schema/Word contract.
No-op saves add neither a revision nor an audit entry. A private `edit_batch_token`
column scopes trigger suppression to the locked transaction; ordinary metadata
and responsibility writes still advance revisions normally. The marker is cleared
before commit and excluded from content fingerprints and editable payloads.

SQLite serializes writes with `BEGIN IMMEDIATE`; PostgreSQL locks the verified
account, card and current responsibilities. UI submissions carry their original
`expected_version`, and stale/concurrent submissions cannot overwrite a newer
revision. All edits clear the previous review binding. Pending Review status stays
visible, but approval requires an explicit new review submission through the
existing review workflow. Existing pending modification requests also become stale.

Empty new columns are omitted from content fingerprints so historical approval
evidence and review hashes remain valid after the additive migration. Old immutable
snapshot JSON and recorded decisions are not rewritten.

## Word parity

Word v2 exports include the new structured details whenever any are populated,
using the existing RTL paragraph/table formatting and visible bookmarked fields.
The `3S-JD/details-v1` extension marker requires all eight detail bookmarks on
reimport, so a damaged extended document fails explicitly. Older v2 exports remain
readable and do not need fabricated detail values. Structured details, Arabic
newlines, KPIs and existing active-row order survive export/import and deduplication.
The original combined qualification text remains independent from the new fields.

## Deployment

For an existing PostgreSQL deployment, run the updated idempotent migration with
the existing server-side `DATABASE_URL`, then reboot/restart Streamlit so every
Python module is loaded from the same release:

```powershell
.\.venv\Scripts\python -B -m scripts.migrate_hr_workflow --postgres
```

It adds the columns and updates private invoker triggers for metadata, responsibility
revisions and immutable audit evidence. It does not add public RPC endpoints,
change RLS policies or rewrite business records. The normal migration-to-Supabase
schema also includes the additive columns. Use a database operator account for DDL.

SQLite startup performs its existing verified backup and applies the additive
migration automatically. The optional explicit SQLite migration command is:

```powershell
.\.venv\Scripts\python -B -m scripts.migrate_hr_workflow
```

No schema migration was applied to a remote Supabase project during development.
Owner-level file/schema access can remove database triggers, as with the existing
governance model; these are not off-host signed audit archives.

## Files and verification

| File | Change |
| --- | --- |
| `database.py` | Full update service; transactional synchronization and detailed evidence; structured Word imports. |
| `governance.py` | Additive fields, compatible fingerprints and one-revision batching. |
| `jd_fields.py` | Shared field schema, labels, aliases and editor groups. |
| `jd_editor.py` | Four-tab dynamic editor with confirmation, cancellation and stable widget identity. |
| `app.py` | Draft/Pending Review entry point and new detail displays; existing compatibility handling retained. |
| `docx_format.py` | Backward-compatible structured detail bookmarks and required extension validation. |
| `presentation.py` | Readable Arabic full-update audit label. |
| `scripts/migrate_hr_workflow.py` | Additive PostgreSQL columns and transactional revision triggers. |
| `scripts/migrate_to_supabase.py` | Include new columns when creating/upgrading a migration target. |
| `tests/test_revoke_and_edit_jd.py` | Preserve seeded revisions while loading the isolated PostgreSQL fixture. |
| `tests/test_full_jd_editor.py` | 44 backend/UI regressions covering edits, role/state guards, atomicity, concurrency and Word parity. |
| `docs/FULL_JD_EDITOR.md` | Implementation, deployment and verification record. |

- Repeat pre-flight: **295 passed**. The first unchanged-source pre-flight had
  an intermittent python-docx style-resolution error in a directory UI test;
  it did not recur on the repeat or final regression gate.
- Required final regression command: **347 passed**, no failures/skips, in
  **60.62 seconds**. All 295 pre-flight cases remain, with eight newly parameterized
  metadata-revision checks and 44 comprehensive-editor cases. The 170 warnings
  are upstream Streamlit/importlib metadata deprecations.
- Real local PostgreSQL 18.4 gate: **75 passed**, 16 UI cases deselected; combines
  the new full-editor backend cases with the existing HR workflow backend cases.
  These tests use only the dedicated local `jd_hr_synthetic` database and never
  the production `DATABASE_URL`. UI cases run on SQLite in the full gate.
- `pip check`: **No broken requirements found**. No packages were added.
- Read-only-source migration, idempotence, preservation and exact-restore rehearsal
  verified all preexisting values/IDs, including **26 cards, 399 responsibilities
  and 9 interviews**; the source business database stayed unchanged.
- Browser QA at 1280×720 verified all four Arabic tabs, preserved edits through
  responsibility addition/removal, mandatory confirmation, and a successful
  Pending Review save that kept the same card selected and advanced revision
  1 → 2. Screenshots with synthetic data only:
  `_stage3_work/hr-jd-edit/full-editor/responsibility-editor.png` and
  `full-save-success.png`. Temporary QA servers were stopped afterward.
- The unified patch passes whitespace/application checks and exactly reconstructs
  all 12 delivered text files from the saved pre-task source baseline.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python -B -m pytest -q
.\.venv\Scripts\python -m pip check

# Optional dedicated local PostgreSQL gate; never point this at a business database.
$env:JD_HR_TEST_PG_PORT = '55439'
.\.venv\Scripts\python -B -m pytest -q tests/test_full_jd_editor.py tests/test_revoke_and_edit_jd.py -k 'not test_ui'
Remove-Item Env:JD_HR_TEST_PG_PORT
```

Unified patch: `docs/changes/full-jd-editor.patch`. It is based on the source at
the start of this task, preserving the already-staged deployment-compatibility fix.
Business databases, credentials and local test artifacts are excluded.
