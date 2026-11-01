# Stage 1 access control and security stabilization

Implemented and verified on 30 October 2026. Scope is the user's four implementation work packages; this is not closure of all 35 audit findings or every additional roadmap recommendation. The Streamlit + SQLite architecture, existing columns, IDs and Arabic content are preserved.

## Changes, in implementation order

| Step | Files | Result |
|---|---|---|
| 1 | `backups.py`; `scripts/backup_database.py`; `scripts/restore_database.py` | UTC-stamped SQLite backup API snapshots under `data/backups/`, integrity/FK checks, full restore comparison. A failed backup blocks initialization/migration. Startup backs up once per server process and database, before DDL/seeding; Streamlit widget reruns reuse it. Restore refuses to overwrite any existing path. |
| 2 | `pytest.ini`; `requirements-dev.txt`; `tests/conftest.py`; `tests/schema.sql`; `tests/test_regression.py` | Disposable synthetic databases matching the existing table definitions; baseline fetch/schema, parameterized query and escaped Arabic word-diff checks. No business rows are used by pytest. |
| 3 | `password_security.py`; `scripts/migrate_passwords.py`; `scripts/verify_password_migration.py`; `requirements.txt` | Pinned argon2-cffi 25.1.0, Argon2id verification only, no plaintext login fallback. One transaction converts existing `users.password` values after a verified backup. Existing hashes are retained. Migration verifies each new hash and enables SQLite secure deletion for removed credential bytes. No DDL is executed. Rehearsal proves account access, preservation, idempotence and rollback. |
| 4 | `auth.py` | Removes demo credential autofill and password-free switching. Only explicit credential verification creates a server session. User payloads exclude passwords and password hashes. Reserved server session keys hold principal ID, credential fingerprint and expiry; no widget or URL binds them. Each action reloads identity/role/assignment. Password resets, missing accounts, invalid roles, 30-minute inactivity and 12-hour absolute expiry invalidate access. Login/logout clear all old forms, uploads and drafts. |
| 5 | `database.py` | Removes default account seeding. All public workflow writes require the current session actor ID; a supplied ID cannot select another actor. HR alone reviews/imports/updates interviews. Other roles write only their assigned card. Responsibility lookup and update both use `id AND jd_id AND is_active=1`; `jd_id` is the existing parent-card column, not a new `card_id`. No DELETE statement exists in the application. Foreign keys are enabled per connection. |
| 6 | `database.py`; `app.py` | Review validation, pending-state transition, target update and audit event are atomic under `BEGIN IMMEDIATE`. Invalid decisions, unsupported/missing/inactive/cross-card targets, replay and stale text fail safely. Accepting an edit increments the parent revision and returns it to review. Approvals reject pending requests and record the actor ID and revision in existing audit notes. New acceptance/rejection events derive the display name from the verified actor. Historical attribution is unchanged. |
| 7 | `app.py` | Uses actor-aware handlers and safe error paths. Other-card manager views remain readable, with write controls disabled and server enforcement underneath. No arbitrary fallback assignment is made. Form drafts are keyed by card/clause or interview. Interview fields load saved values; no-change saves preserve outcomes. |
| 8 | `scripts/manage_account.py`; `README.md` | Local operator reset/provisioning with hidden, confirmed password input; fresh installations create no default users. Existing identities/assignments survive password resets. Published credential tables and quick-switch instructions are removed. |
| 9 | `.gitignore`; `.dockerignore`; `.streamlit/config.toml` | Excludes live databases, backups, working copies, secrets and personnel source documents from Git/build context. Enables CORS while retaining XSRF. `JD_DB_PATH` can select an existing durable database; scripts honor the same variable. |
| 10 | Remaining `tests/test_*.py`; `docs/changes/stage1-security.patch` | Negative authorization, session, migration failure/rollback, startup backup and real Streamlit application regression checks; reviewable unified diff because the supplied directory has no Git repository. |

## Verification evidence

- Before business-logic changes: **4/4 baseline tests passed**. The first security regression run against the old auth/database behavior produced **16 failures and 8 passes**, including rejection of hash-based login and acceptance of plaintext login. Immediately after the auth/database changes, **24/24 passed**.
- Final suite: **47 passed**, no failures or skips, in 9.35 seconds on Python 3.14.5 / Streamlit 1.66.1. Thirty upstream `importlib.metadata` deprecation warnings were emitted by AppTest; no application exception occurred. `pip check` found no broken requirements.
- The real app was executed with Streamlit AppTest using synthetic databases: all three roles login/logout; URL user/role tampering does not change identity; other-card manager actions are disabled; employee submission and HR acceptance complete; interview no-change save preserves data. These tests do not establish rendered browser/mobile/RTL accessibility or target-container compatibility.
- The Windows sandbox stalled Streamlit's local asyncio socket setup. The complete suite passed outside that sandbox. No live server or real account was used for UI tests. In this session the virtual environment reused existing application dependencies and installed matching Argon2/CFFI wheels locally; a clean Python 3.11/container build was not performed.
- Before changing the supplied database, an isolated copy migrated **15 accounts**, verified all passwords against their new hashes, proved a second migration made zero changes, and restored the original snapshot exactly. The source stayed unchanged during rehearsal.
- The supplied local database was then migrated successfully: **15 users, 26 cards, 399 responsibilities, 1 request, 28 audit rows, 9 interviews**. Complete schema definitions and every noncredential value, row ID and sequence were compared and preserved. Existing account access was verified without printing credentials or business text.
- Verified pre-migration rollback backup: `data/backups/job_descriptions_20261030T083344.046293Z_04bad736.db`. The initial pre-flight snapshot is also retained in the same directory. No backup is included in the patch or build context.
- The unified diff passed `git apply --check` against an isolated pre-change source tree; applying it reconstructed all 27 delivered text files exactly after newline normalization.

## Commands (PowerShell, project root)

For an existing environment, use its Python executable. For a fresh environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
```

Run the synthetic suite in a normal terminal. A successful run must exit 0 and show every test passing:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python -B -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Regression suite failed' }
.\.venv\Scripts\python -B -m pip check
```

If the environment restricts its default temp directory, provide a **new, disposable directory inside this workspace** using `--basetemp`. Pytest owns and clears that directory; never point it at business data. The final session run used `--basetemp=_stage1_work/pytest-full -p no:cacheprovider`.

For another installation, stop its Streamlit process and other writers before migration. Never run migration/recovery against a changing deployment. The supplied local database is already migrated; repeating the migration is safe and creates another backup.

```powershell
# Optional: set the same existing durable path for the application and all tools.
# $env:JD_DB_PATH = 'D:\protected-data\job_descriptions.db'
.\.venv\Scripts\python -B -m scripts.backup_database
.\.venv\Scripts\python -B -m scripts.verify_password_migration
.\.venv\Scripts\python -B -m scripts.migrate_passwords
.\.venv\Scripts\python -m streamlit run app.py
```

The rehearsal reads the selected database and creates temporary copies; it never migrates the source. The migration itself makes only password updates. Neither command prints passwords/hashes.

Reset a previously published password locally; repeat for each affected account. Passwords are entered at hidden prompts and must be at least 12 characters. Do not put passwords in command-line arguments or shell history.

```powershell
.\.venv\Scripts\python -m scripts.manage_account --username YOUR_USERNAME

# Explicit fresh administrator provisioning; refuses to overwrite an existing account.
.\.venv\Scripts\python -m scripts.manage_account --username YOUR_NEW_ADMIN --create-admin
```

## Recovery

Stop all writers first. Restore into a new path; the command verifies the copy and will never overwrite the current database:

```powershell
.\.venv\Scripts\python -m scripts.restore_database 'data\backups\YOUR_BACKUP.db' 'data\recovery\recovered.db'
```

For an application-code rollback, use the corresponding old source privately with the pre-migration copy, via `JD_DB_PATH`; keep the current database for reconciliation. The hardened login deliberately rejects plaintext, so retaining the hardened application requires migrating the restored copy before restarting. Restart the server to invalidate all in-memory sessions. Do not replace a database while SQLite connections or WAL/SHM files are live. Recovery from an old snapshot does not include newer business writes; reconcile them explicitly.

## Limits and follow-up

- **Existing passwords were preserved to avoid losing access.** Hashing does not make previously published passwords secret again. The operator must reset those passwords before a real-data pilot. No account was removed, renamed, disabled or silently assigned an unknown replacement password.
- Pre-migration backups and the requested unified diff necessarily retain historical sensitive material, including removed demo credential definitions. Keep them private. Backups use restrictive creation modes where supported; Windows ACLs and protected/off-host storage still require operator configuration. No backup deletion or retention policy was invented.
- Manager/employee writes default to the explicit existing assignment. Company-wide read browsing is retained. No implicit executive write exception was inferred from a username or job title; an approved broader grant needs a separate explicit policy.
- Actor IDs are verified on each action and added to new decision/approval/import audit notes using the existing schema. Request ownership still uses historical display-name fields; new actor FK columns, full immutable revision reconstruction and unambiguous legacy attribution remain later schema work. Interview edits are role-checked but still lack a dedicated historical event store.
- CORS was enabled, but proxy/host deployment tests, login rate limiting, a general account disable UI, complete HTML escaping/upload budgets, document interchange fixes and the remaining audit findings are outside the four requested work packages. No claim is made that those are resolved or that the portal is production-ready.
- `utils.py` and `docx_parser.py` are unchanged. Word-diff escaping, Arabic whitespace/newlines and UTF-8 decoding are covered; visual RTL rendering still needs browser/Word acceptance testing.

## Primary implementation references

[argon2-cffi PasswordHasher documentation](https://argon2-cffi.readthedocs.io/en/stable/api.html), [Streamlit Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state), [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
