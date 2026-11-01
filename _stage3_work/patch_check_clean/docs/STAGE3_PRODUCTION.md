# Stage 3 production hardening

Implemented and verified on 30 October 2026. This stage preserves the Python, Streamlit, python-docx and SQLite stack and extends the Stage 1/2 controls without rebuilding tables or rewriting historical records.

## Changes by file

| Files | Result |
|---|---|
| `database.py` | Every application connection immediately sets foreign keys ON, journal mode WAL and synchronous NORMAL. Failed initialization closes the connection. Workflow writes validate shared status domains; known legacy review/interview labels display consistently. Dashboard pending counts exclude drafts/rejections. New import provenance is sanitized at the backend boundary. |
| `statuses.py`; `governance.py` | Explicit `CardStatus`, `ReviewStatus`, `InterviewStatus` Enums with canonical Arabic values and documented English aliases. Additive insert/update guards reject unknown/null future statuses. Stage 2 transition, revision and immutable-evidence guards remain in force. Existing stored aliases, IDs and historical snapshots are preserved. |
| `upload_security.py`; `docx_parser.py` | Configurable byte limit, default 10 MiB; bounded reads; required `PK\x03\x04` signature and DOCX extension; ZIP component/CRC validation; required Word parts; rejection of duplicate entries, traversal/absolute paths, encrypted/symlink entries and excessive expansion. Parsing errors return safe messages. Legacy filename-based titles remain readable. |
| `app.py` | Safe upload previews, widget keys and stored filenames; expected import failures show controlled messages and unexpected failures are masked. The upload widget follows the configured byte threshold, rounded up to MiB; the parser enforces the exact byte boundary. Downloads retain `3S-JD-<ID>`, a sanitized title and an Arabic document label. |
| `.streamlit/config.toml` | Telemetry disabled; error details disabled; CORS/XSRF enabled; default upload limit 10 MiB. Unused Streamlit magic is disabled after the regression gate exposed a Python 3.14 AST compilation failure in that feature. All application rendering uses explicit Streamlit calls. |
| `requirements.lock`; `requirements-dev.lock`; `requirements.txt`; `requirements-dev.txt`; `scripts/lock_dependencies.py` | Exact versions for the complete tested dependency closure: 43 production packages, 48 including tests. Unrelated host tools are excluded. Regeneration/check commands detect drift. |
| `scripts/audit_dependencies.py` | Runs `pip check`, checks installed versions and dependency-closure completeness, checks known insecure minimum versions, then queries the live OSV API for every production pin. Findings cause exit 1; unavailable/malformed/incomplete advisory responses and other failures cause exit 2. Offline mode is explicitly a limited check. |
| `Dockerfile` | Installs the production lock and an exact pip version instead of resolving minimum-only application dependencies or floating the installer. The Python 3.11 image target is retained. |
| `backups.py`; `scripts/backup.py`; `scripts/restore_database.py` | Every new backup gets a verified SHA-256 sidecar. Backups use the SQLite backup API, include committed WAL data and are independent of WAL sidecars. Scheduled backup runs validate/seal managed legacy backups and prune expired artifacts while retaining at least five. Restore checks available hashes before creating its target; strict checksum mode is available. |
| `tests/conftest.py`; four `tests/test_stage3_*.py` files | 79 new cases. A recovery gate can restore a verified synthetic backup independently for every database fixture; it refuses personnel-account inputs. All 107 original cases retain their assertions. |
| `.gitignore`; `.dockerignore` | Exclude Stage 3 work, private recovery copies and database checksum artifacts from source/build delivery. |

## SQLite and statuses

`database.get_connection()` executes these PRAGMAs before returning a connection:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
```

The factory requires a file-backed database supporting WAL. NORMAL appears as `1` when read back. Foreign keys are connection-local; tests prove orphan responsibilities, modification requests and audit events raise `sqlite3.IntegrityError` and roll back the surrounding transaction. A concurrent reader test proves WAL readers retain their snapshot while another connection commits.

| Domain | Canonical values |
|---|---|
| Card | `مسودة`, `قيد المراجعة`, `معتمد`, `مرفوض` |
| Review request | `قيد الانتظار`, `مقبول`, `مرفوض` |
| Interview | `قيد المراجعة`, `مكتملة`, `مؤجلة`, `لم تبدأ` |

English aliases are explicit in `statuses.ALIASES`. New public workflow writes validate these domains and write canonical values. Database guards also reject invalid future inserts/status changes. Existing aliases are not bulk-normalized: the historical `Accepted` request stays exactly as stored, while its UI label is `مقبول`. Unknown historical values remain available for explicit correction rather than being guessed. Historical decision snapshots and hashes are never rewritten.

Normal startup applies the additive guards after its verified pre-startup backup. Existing Stage 2 optimistic concurrency, authority checks and immutable decision evidence remain unchanged.

## Uploads and document downloads

Set `JD_MAX_UPLOAD_BYTES` to a positive integer to change the per-document byte threshold. For example:

```powershell
$env:JD_MAX_UPLOAD_BYTES = '10485760'
```

The default is 10,485,760 bytes. The widget derives its MiB limit from the same setting. Reads stop after the configured limit plus one byte, and oversized claimed sizes are rejected before reading. Archive expansion is capped at five times the configured upload allowance, with a 5 MiB minimum expansion budget for small valid OOXML documents. Archives may contain at most 2,048 unique entries. No archive member is extracted to a filesystem path.

Filenames are normalized and stripped of path components, encoded separators, controls, markup and Windows reserved basenames. Arabic/English letters are retained and names end in `.docx`. This changes transport/provenance names, not document content. All 26 supplied Word sources were compared with the Stage 2 parser: every content field remains identical, including the legacy document whose title comes from its filename.

Downloads pass a sanitized readable Unicode name to Streamlit, which generates the UTF-8 percent-encoded RFC 5987 `filename*` header. This avoids saving literal double-encoded percent sequences as the filename. `download_filename(..., url_encoded=True)` supplies the explicit encoded form for URL-building callers. IDs and the Arabic document label remain present even when a title contains separators or markup. Existing Arabic content, RTL/table layout and v2 DOCX round-trip regressions pass.

## Dependencies and deployment

The live audit initially found advisories affecting Pillow 12.3.0. Pillow was upgraded **inside the project virtual environment** to **13.0.0**, the upstream fixed version allowed by Streamlit's range. Other application dependencies retained their tested versions. The final live OSV audit at **2026-10-30 09:42:57 UTC** checked all **43** production pins and returned **zero findings**. This is a dated advisory result, not a guarantee against future disclosures.

Install the matching lock for the intended environment:

```powershell
# Production
.\.venv\Scripts\python -m pip install -r requirements.lock

# Development and synthetic testing
.\.venv\Scripts\python -m pip install -r requirements-dev.lock

.\.venv\Scripts\python -B -m scripts.lock_dependencies --check
.\.venv\Scripts\python -B -m scripts.audit_dependencies
.\.venv\Scripts\python -m pip check
```

Locks use exact versions, as permitted by the stage requirements; they do not contain wheel hashes. `scripts.lock_dependencies` generates the app/test closures from installed distribution metadata, evaluating the Windows/Python 3.14 and Linux/Python 3.11 targets. Review and audit intended upgrades before regenerating a lock. An offline audit must be requested explicitly with `--offline`; it checks consistency, drift and known Streamlit/Pillow floors but does not replace the live vulnerability scan.

Binary-only resolution of the complete production lock succeeded for **CPython 3.11 on Linux x86-64**, matching the container target. The local test runtime is Windows/Python 3.14.5. Docker is unavailable here, so no container build or running-container/proxy validation is claimed.

Run one writable application instance against a durable local SQLite directory. `JD_DB_PATH` selects the database file; mount/protect the containing directory so SQLite can maintain its WAL/SHM files. Deploy the supplied CORS/XSRF settings without disabling them at the proxy. Start the portal with the same virtual environment used for the lock and checks.

## Backup rotation and recovery

Use this scheduler-compatible command with the project root as its working directory:

```powershell
.\.venv\Scripts\python -B -m scripts.backup
```

An external deployment scheduler can invoke it at the chosen backup frequency. No OS scheduler or Codex automation was installed. The command creates and fully verifies a fresh backup before rotation. Optional arguments are `--database`, `--backup-dir`, `--retention-days` (default 30) and `--keep` (default 5, cannot be lower than 5).

Only managed UTC-stamped filenames belonging to the selected database are candidates. Every candidate must pass checksum, SQLite integrity and FK checks. Legacy candidates without sidecars are verified and given checksums first. Corruption or unsafe paths abort rotation before any deletion. Unrelated files remain untouched. A candidate is deleted only if it is **older than** the age limit **and outside the five newest verified backups**. If all backups are old, the newest five still remain. Age uses the UTC creation timestamp in the managed filename rather than a mutable filesystem mtime.

New snapshots have adjacent `<backup>.sha256` files. Startup and the existing `scripts.backup_database` entrypoint also create checksummed snapshots; rotation is performed by `scripts.backup`. Checksum files detect corruption and are not a signature against someone who can rewrite the database and sidecar together.

For recovery, stop writers and restore into a **new** path:

```powershell
.\.venv\Scripts\python -B -m scripts.restore_database 'data\backups\YOUR_BACKUP.db' 'data\recovery\recovered.db' --require-checksum
```

Strict mode rejects missing/tampered hashes before creating the destination. The default restore API retains compatibility with pre-Stage-3 backups/raw SQLite copies without a sidecar, but always validates integrity, foreign keys and exact logical equality. It never overwrites an existing destination. Use `JD_DB_PATH` to select the verified restored file; do not overwrite an open database or copy just its main file while WAL writers are active.

## Verification and preservation

- Required command: **186 passed**, no failures/skips, in **17.59 seconds**: all **107 existing + 79 new** cases.
- Full restored-backup gate: **186 passed**, no failures/skips, in **16.45 seconds**. Each database fixture was restored independently from a checksummed synthetic baseline. The dedicated recovery test also proves decision hashes, approval metadata and replay guards survive restore.
- `pip check`: **No broken requirements found**. Exact production/test lock verification passed. Live OSV: **0 findings across 43 production pins**.
- Forty upstream `importlib.metadata` deprecation warnings remain in each full Streamlit AppTest run. The Windows sandbox restricts default temp directories and Streamlit sockets, so full application tests ran outside it, as in Stages 1/2.
- The local additive startup upgrade preserved **15 users, 26 cards, 399 responsibilities, 1 modification request, 28 audit rows and 9 interviews**. Every preexisting column value, ID and sequence was compared against the pre-upgrade snapshot. No credential, historical status or audit event was rewritten.
- Live factory verification returned `foreign_keys=1`, `journal_mode=wal`, `synchronous=1`. Integrity/FK checks passed. A business-database backup was restored into an isolated private work path and compared against all original records; business rows were never used by pytest.
- Verified pre-upgrade backup: `data/backups/job_descriptions_20261030T093751.657809Z_43257de7.db` and its SHA-256 sidecar.
- Verified Stage 3 backup: `data/backups/job_descriptions_20261030T094410.045767Z_20b22bdd.db` and its sidecar. The first rotation verified/sealed existing managed backups and pruned **0** because none were eligible by age/count.
- Unified patch: `docs/changes/stage3-production.patch`. No database, backup, installed wheel or private recovery artifact is included. The patch is checked/applied against an isolated Stage 2 baseline and all reconstructed text files are compared exactly after newline normalization.

Reproduce the required gate:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python -B -m pytest -q
.\.venv\Scripts\python -m pip check
```

To reproduce the recovery gate, create a disposable **synthetic** seed using `build_synthetic_database` in `tests/conftest.py`, back it up with `backups.backup_database`, and pass that backup to:

```powershell
.\.venv\Scripts\python -B -m pytest tests -q --restored-fixture 'PATH_TO_SYNTHETIC_BACKUP.db'
```

The explicit `tests` path loads the custom fixture option before pytest parses it. The option rejects real personnel account sets. It is a test-only switch and never changes the normal application database selection.

## References

- [SQLite PRAGMAs](https://www.sqlite.org/pragma.html) and [WAL](https://www.sqlite.org/wal.html).
- [Streamlit configuration](https://docs.streamlit.io/develop/api-reference/configuration/config.toml).
- [OSV batch API](https://google.github.io/osv.dev/post-v1-querybatch/).
- [Pillow package advisories for 12.3.0](https://pypi.org/pypi/pillow/12.3.0/json) and [13.0.0 release](https://pypi.org/project/pillow/13.0.0/).
