# HR direct JD editing and approval revocation

Implemented on 2 November 2026. The existing SQLite/PostgreSQL adapters, Argon2id
authentication, integer revision numbers, Arabic statuses and Word format remain in use.

## Behavior

- The JD directory exposes revocation to authenticated `admin`, `hr` and `editor`
  accounts for Approved cards. Both English legacy statuses and canonical Arabic
  values are recognized. A confirmation form requires a nonblank reason.
- Revocation atomically sets the status to `مسودة`, advances the integer revision
  once (for example, 1 → 2), clears review tokens and appends `revoke_approval` to
  the existing audit `action` column. This is the schema's equivalent of the
  requested `action_type`; no duplicate audit column is introduced.
- The exact reason, verified actor ID/name, UTC timestamp and hash-verified before
  and after snapshots are retained. The supplied `actor_name` argument cannot
  override the authenticated actor. Old approval evidence is preserved, and
  the reopened revision no longer exports current electronic approval metadata.
- Drafts expose a form for title, department, sector, direct supervisor, purpose
  and the existing combined qualification/experience/skills text. Partial edits
  preserve omitted values. Explicit empty strings can clear optional fields;
  a blank title is rejected. Changed fields are allowlisted and recorded with
  before/after evidence. A successful edit advances the revision once and remains
  Draft until the existing review workflow is used. No-op saves add no revision
  or audit event and preserve untouched NULL values.
- UI forms retain the displayed revision. Stale forms show a reload action, and
  the APIs also accept `expected_version` to reject stale submissions under the
  write lock. Simultaneous revocations succeed only once. SQLite uses the existing
  `BEGIN IMMEDIATE`; PostgreSQL locks the account and card with `FOR UPDATE`.
- The directory selector uses stable card IDs, including for duplicate titles.
  Successful writes keep the edited card selected and reset active search/status/
  department filters so its new title, department or Draft status stays visible.
- `hr` and `editor` accounts can use this directory workflow across cards. They
  cannot access user management, password resets, backups or other admin screens.
  `manager` and `employee` retain their existing assigned-card workflows and cannot
  call the new direct editing APIs. Roles come from fresh server-side user records.

## Modified files

| File | Change |
| --- | --- |
| `database.py` | Transactional revocation/core-edit APIs, role/state validation, revision checks, immutable snapshots and deterministic audit ordering. |
| `app.py` | Arabic confirmation/edit forms, toast and refresh, stale-form recovery, stable card selection and safe multiline text presentation. |
| `roles.py` | Shared role allowlists and Arabic role labels. |
| `auth.py` | Authenticate the explicit HR/editor roles while retaining active-account/session checks. |
| `governance.py` | Idempotently upgrade SQLite revision/status triggers; permit versioned Approved → Draft and preserve intentional Draft edits. |
| `presentation.py` | Arabic label for `revoke_approval`, shared role labels. |
| `scripts/migrate_hr_workflow.py` | Transactional PostgreSQL role/revision/status/audit guards and backed-up SQLite migration entry point. |
| `scripts/migrate_to_supabase.py` | Include new roles and guards when provisioning a PostgreSQL target. |
| `tests/test_revoke_and_edit_jd.py` | Dedicated backend and real Streamlit AppTest workflow regressions; optional isolated local PostgreSQL execution. |
| `.gitignore` | Exclude disposable HR test databases/server artifacts and SQLite journal sidecars. |
| `docs/HR_JD_EDIT_WORKFLOW.md` | Behavior, rollout instructions and verification evidence. |

## Deployment

For an existing PostgreSQL deployment, run the migration once with the existing
server-side `DATABASE_URL` configured, then restart Streamlit:

```powershell
.\.venv\Scripts\python -B -m scripts.migrate_hr_workflow --postgres
```

The migration targets PostgreSQL explicitly and never falls back to SQLite.
It installs invoker trigger functions in the private `jd_governance` schema,
revokes public function access, expands the shipped `users_role_check`, and
protects audit rows against UPDATE/DELETE. It does not create public RPCs,
change RLS policies, or update business rows. Use a database operator account
with DDL privileges for this migration. This work did not change a remote
Supabase project.

SQLite startup applies the updated guards after the existing verified backup.
An operator can instead apply them before startup with:

```powershell
.\.venv\Scripts\python -B -m scripts.migrate_hr_workflow
```

There is no automatic promotion of existing accounts. An admin can create an
explicit HR/editor account through the existing user-management form.

## Verification

- Pre-flight: **248 passed** before changes.
- Final required regression command: **293 passed**, no failures or skips, in
  **52.35 seconds**: all **248 existing + 45 new** cases. The 130 warnings are
  upstream Streamlit/importlib metadata deprecations.
- Dependency verification: **No broken requirements found**.
- All HR backend cases were also executed against a disposable localhost
  PostgreSQL 18.4 database: **37 passed**. UI cases execute against SQLite in the
  full regression gate.
- A read-only-source rehearsal verified migration preservation, idempotence and
  exact restore with **26 cards, 399 responsibilities and 9 interviews**. It
  preserved every preexisting value/ID in all tables and left the supplied
  business database unchanged.
- Browser QA verified the Arabic confirmation/reason form, successful revocation,
  Draft metadata editing and version advancement. It also verified that the
  renamed card stays selected after saving. Screenshots use synthetic data only:
  `_stage3_work/hr-jd-edit/revoke-confirmation.png` and `draft-edit-success.png`.
  No business records or credentials are included in the patch. Temporary QA
  servers are stopped after verification.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python -B -m pytest -q
.\.venv\Scripts\python -m pip check
```

The optional PostgreSQL test fixture requires a dedicated local test instance
with a disposable database named `jd_hr_synthetic` and user `jd_hr_test`. It
resets only that explicitly named database's synthetic tables and never reads
`DATABASE_URL`:

```powershell
$env:JD_HR_TEST_PG_PORT = '55439'
.\.venv\Scripts\python -B -m pytest -q tests/test_revoke_and_edit_jd.py -k 'not test_ui'
Remove-Item Env:JD_HR_TEST_PG_PORT
```

Row-lock behavior follows the official
[PostgreSQL locking documentation](https://www.postgresql.org/docs/current/explicit-locking.html).
Audit triggers guard ordinary database operations; a database/schema owner can
remove those guards, as with the existing SQLite governance model.

Unified patch: `docs/changes/hr-jd-edit-workflow.patch`.
