# Stage 2 data integrity and document governance

Implemented and verified on 30 October 2026. This extends the Stage 1 SQLite, Streamlit and python-docx implementation for revision evidence, interview preservation, Word interchange and document states.

## Delivered changes

| Files | Behavior |
|---|---|
| `governance.py`; `database.py` | Additive, transactional schema upgrade. All content-field changes and responsibility insert/update/delete operations advance the parent revision. No-op content updates do not. Changed content invalidates approval and the pending review binding. |
| `database.py` | New modification requests bind the entire card and its responsibilities to an expected revision and SHA-256 fingerprint, alongside the original snapshot. Accepting a stale request fails without changing content, request status or audit history, including unrelated-field changes and changes subsequently reverted. |
| `governance.py`; `database.py` | Every new accepted/rejected modification decision and final card approval/rejection stores complete before/after content snapshots, hashes, actor ID and reviewed version atomically. SQLite triggers prevent changes to audit events, request bases and completed decisions. Evidence reads verify both snapshot hashes. |
| `database.py`; `app.py` | Canonical Arabic document statuses with explicit English legacy aliases. Draft → Pending Review → Approved/Rejected; rejected or invalidated cards can be submitted again. Approved content must change before another review. Final decisions require a current review binding, no pending modifications and a matching displayed revision. Replay produces no second event. |
| `database.py`; `app.py` | Interview forms retain a per-record baseline, load saved fields and reject concurrent changes. Omitted, `None`, empty or whitespace-only notes/status preserve existing values. Explicit backend `clear_notes=True` is required to erase notes. Outcomes and candidate feedback reside in the existing `notes` column; there are no separate outcome/feedback columns. Other interview fields remain untouched. |
| `docx_format.py`; `docx_parser.py` | Shared editable Word format `3S-JD/v2`. Export/import preserves all supported content fields, competencies, behavioral/technical criterion lines, responsibility order and KPIs, including intentional duplicate descriptions and whitespace. Competencies retain the existing TEXT storage and are also returned as categorized criteria during parsing. |
| `database.py`; `docx_format.py`; `app.py` | Word exports read content and verified approval evidence in one SQLite read transaction. They include the actual status/version, portal card ID, recorded job code, safety fields, legacy source approval text and current revision-bound approver, actor ID, UTC decision timestamp, version, evidence ID and snapshot hash. Missing codes/safety data stay empty; missing electronic approval is stated explicitly. |
| `database.py` | Reimporting a matching v2 export returns the existing card ID without creating rows or changing history. Repeated imports of a new v2 document also return its first imported card. A changed known document must use the modification workflow rather than overwriting or silently creating another card. Imported approval text never authorizes electronic approval. |
| `app.py` | Competencies and source approval text appear in both full-card views. Status filters include Draft/Rejected. Revision-bound approval and interview reload controls recover from stale form conflicts. Review comparisons label the saved request base accurately. |
| `scripts/migrate_integrity.py`; `scripts/verify_stage2_migration.py` | Verified backup before upgrade; transaction-wide comparison of every preexisting column, row, ID and sequence; integrity/FK checks; read-only-source migration/idempotence/restore rehearsal. |
| `tests/conftest.py`; three new Stage 2 test files | Apply the same additive migration to synthetic fixtures. All 47 original test cases are retained without weakening their assertions; 60 cases cover the new behaviors. |
| `.gitignore`; `.dockerignore` | Exclude Stage 2 working copies and synthetic visual QA artifacts. |

## State and evidence rules

Canonical stored transition values are `مسودة`, `قيد المراجعة`, `معتمد`, and `مرفوض`. The read boundary also recognizes `Draft`, `Under Review`, `Pending Review`, `Approved`, and `Rejected`. Existing stored spellings are not rewritten by the migration. Workflow writes use canonical Arabic. Interview statuses belong to a separate domain.

Responsibility changes advance the parent revision even when made through another SQLite connection. Child reparenting and version decreases are rejected. Accepted modification requests advance the revision exactly once, then bind that resulting revision for final review. Arbitrary content changes invalidate the pending review token and require resubmission. Each responsibility inserted during a new bulk import advances the parent counter, so an initial import can begin above revision 1.

Final full-card approval remains available to the assigned actor or HR under the existing Stage 1 authorization policy. Full-card rejection is available to HR through `decide_jd_review`. Full-card decisions and modification decisions use `BEGIN IMMEDIATE`; concurrent reviewers cannot both finalize the same pending state. Manager/employee final approval widgets retain the revision originally displayed across reruns.

At upgrade, existing pending cards receive a binding to their current content. This starts Stage 2 governance; it does not reconstruct a historical review request. Historical approved statuses remain unchanged and do not acquire fabricated electronic evidence. Legacy pending modification requests lack a provable complete base revision: acceptance is blocked, while HR can reject them and the assigned actor can submit a fresh request. The existing request is preserved.

The snapshots include all card content fields, the reviewed status/version and all responsibility rows, including inactive rows. Both the pre-decision content and resulting state are retained. Historical timestamps and attribution are unchanged. New decision timestamps use UTC.

SQLite guards provide append-only protection through ordinary application/SQL operations. An owner with unrestricted file/schema access can remove guards or rewrite data and hashes; these controls are not an externally signed or off-host archive. Existing history without snapshots cannot be retroactively reconstructed.

## Word contract and visual verification

V2 uses Word bookmarks to identify editable visible text and a tagged three-column responsibility table. The parser reads those visible paragraphs and cells, rather than an embedded JSON copy. Unknown format versions, missing/duplicated required bookmarks and missing/duplicated responsibility tables fail explicitly. Preserve the bookmarks and table structure when editing in Word. System-export import deduplication applies to v2; arbitrary legacy uploads still need the broader import-identity policy from AUD-013/AUD-016.

All 26 supplied legacy source documents were compared against the Stage 1 parser and produced identical dictionaries. Legacy competency tables additionally preserve multiple rows and merged cells, including `Competencies & Skills` headers. Older unversioned portal exports are not the v2 interchange contract.

A synthetic Arabic export with 12 responsibilities, competency criteria and full approval evidence was rendered in native Microsoft Word. The first inspection exposed table clipping; the final exporter sets consistent grid/cell widths, logical RTL alignment, repeating headers and LTR dates/hashes. Both regenerated pages were visually inspected with clean tables and pagination. Native Word save/reopen preserved every parsed field and responsibility exactly. The bundled `render_docx.py` was attempted but could not convert because LibreOffice is absent; native Word was used for this verification. No personnel document was rendered or included in the patch.

The table implementation follows the [python-docx table API](https://python-docx.readthedocs.io/en/latest/api/table.html), and logical paragraph alignment uses the Open XML [justification values](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.justificationvalues?view=openxml-3.0.1).

## Verification evidence

- Required regression command: **107 passed**, no failures or skips, in **16.26 seconds**. This includes all **47 existing + 60 new** cases. Forty upstream `importlib.metadata` deprecation warnings were emitted by Streamlit AppTest.
- Required dependency command: **No broken requirements found**.
- Tests cover every core metadata field, all responsibility mutation types, no-op updates, unrelated-field and ABA conflicts, immutable/hash-verified evidence, migration rollback and backup failure, canonical transitions/replay, simultaneous reviewers, partial/stale interviews, DOCX round trips and real Streamlit stale-form recovery.
- The required test command passed outside the Windows sandbox because its default temp directory and Streamlit local socket setup are restricted inside the sandbox. No real account or business row is used by pytest.
- Read-only-source rehearsal verified preservation, repeat-upgrade idempotence, integrity, foreign keys and exact restore on an isolated copy of the supplied database.
- The local database was then upgraded with **26 cards, 399 responsibilities and 9 interviews** preserved. The migration compared every preexisting value and ID across all tables, including users, requests, audit events and sequences, before committing. Credentials and content were not printed.
- Verified pre-upgrade backup: `data/backups/job_descriptions_20261030T091225.817992Z_2272655a.db`.
- Unified patch: `docs/changes/stage2-integrity.patch`. It excludes databases, backups and visual QA artifacts. Patch application is checked against the Stage 1 text baseline, with reconstructed files compared to the delivered files.

## Commands and recovery

From the project root:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python -B -m pytest -q
.\.venv\Scripts\python -m pip check

# Read-only source rehearsal; uses a disposable directory for copies.
.\.venv\Scripts\python -B -m scripts.verify_stage2_migration --work-dir _stage2_work

# For another existing deployment, stop writers before upgrading.
# The supplied local database has already been upgraded.
.\.venv\Scripts\python -B -m scripts.migrate_integrity
```

`JD_DB_PATH` selects an existing durable database, as in Stage 1. Normal application startup also applies this idempotent upgrade after its verified startup backup. Migration failure rolls back the additive DDL and blocks startup. Fresh installations retain the original explicit account-provisioning flow.

For recovery, stop writers and use the existing restore command to restore the pre-upgrade backup into a **new** path. Never overwrite an open database. Run the matching Stage 1 code against that restored path when rolling back application code; Stage 2 startup would apply the additive migration again. Keep the current database for reconciliation of any writes made after the backup. No rollback action deletes current data.
