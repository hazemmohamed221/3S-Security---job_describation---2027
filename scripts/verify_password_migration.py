"""Rehearse migration and rollback on independent copies; never write the source DB."""
import argparse
from contextlib import closing
from pathlib import Path
import tempfile

from backups import backup_database, readonly_connection, verify_database
from password_security import is_password_hash, verify_password
from scripts.migrate_passwords import DEFAULT_DB, migrate_passwords
from scripts.restore_database import restore_database


def snapshot(path):
    with closing(readonly_connection(path)) as conn:
        verify_database(conn)
        schema = conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        # Table identifiers come from SQLite metadata, escaped as identifiers.
        rows = {name: conn.execute('SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid').fetchall()
                for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        return schema, rows


def verify_preservation(before, after):
    old_schema, old_tables = before
    new_schema, new_tables = after
    if old_schema != new_schema or old_tables.keys() != new_tables.keys():
        raise RuntimeError("Database schema changed.")
    credentials = 0
    for name, rows in old_tables.items():
        current = new_tables[name]
        if name != 'users':
            if rows != current:
                raise RuntimeError(f"Rows changed in {name}.")
            continue
        if len(rows) != len(current):
            raise RuntimeError("Account count changed.")
        for old, new in zip(rows, current, strict=True):
            if old[:2] != new[:2] or old[3:] != new[3:]:
                raise RuntimeError("Account identity/metadata changed.")
            if is_password_hash(old[2]):
                if old[2] != new[2]:
                    raise RuntimeError("Existing password hash changed unexpectedly.")
            elif not verify_password(new[2], old[2]):
                raise RuntimeError("Credential access lost.")
            credentials += 1
    return {name: len(rows) for name, rows in old_tables.items()}, credentials


def rehearse(db_path, work_dir=None):
    source = Path(db_path).resolve(strict=True)
    before = snapshot(source)
    if work_dir is None:
        work_dir = source.parent / '_stage1_work'
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="migration-rehearsal-", dir=work_dir) as folder:
        directory = Path(folder)
        seed = backup_database(source, directory / 'backups')
        trial = restore_database(seed, directory / 'trial.db')
        count, rollback_backup = migrate_passwords(trial, directory / 'backups')
        counts, credentials = verify_preservation(before, snapshot(trial))
        migrated = snapshot(trial)
        if migrate_passwords(trial, directory / 'backups')[0] != 0 or snapshot(trial) != migrated:
            raise RuntimeError("Migration is not idempotent.")
        rollback = restore_database(rollback_backup, directory / 'rollback.db')
        if snapshot(rollback) != before:
            raise RuntimeError("Rollback restore did not preserve the source.")
    if snapshot(source) != before:
        raise RuntimeError("Source changed during rehearsal; retry in a maintenance window.")
    return {"migrated": count, "credentials_verified": credentials, "counts": counts,
            "schema_preserved": True, "rollback_verified": True, "source_unchanged": True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    print(rehearse(args.database))
