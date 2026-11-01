from contextlib import closing
import sqlite3

import pytest
from backups import backup_database, readonly_connection
from password_security import is_password_hash, verify_password
from scripts import migrate_passwords as migration


def dump(path):
    with closing(readonly_connection(path)) as conn:
        return list(conn.iterdump())


def test_backup_restores_complete_database(db, tmp_path):
    backup = backup_database(db, tmp_path / "backups")
    assert "Z_" in backup.name and dump(backup) == dump(db)


def test_migration_preserves_schema_rows_and_access(db, tmp_path):
    original = dump(db)
    with sqlite3.connect(db) as conn:
        before = {name: conn.execute(f'SELECT * FROM "{name}"').fetchall() for (name,) in
                  conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        schema = conn.execute("SELECT name,sql FROM sqlite_master ORDER BY name").fetchall()
    count, backup = migration.migrate_passwords(db, tmp_path / "backups")
    assert count == 4 and dump(backup) == original
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT name,sql FROM sqlite_master ORDER BY name").fetchall() == schema
        for name, rows in before.items():
            current = conn.execute(f'SELECT * FROM "{name}"').fetchall()
            if name == "users":
                for old, new in zip(rows, current, strict=True):
                    assert old[:2] == new[:2] and old[3:] == new[3:]
                    assert is_password_hash(new[2]) and verify_password(new[2], old[2])
            else:
                assert current == rows
    migrated = dump(db)
    assert b"synthetic-secret" not in db.read_bytes()
    assert migration.migrate_passwords(db, tmp_path / "backups")[0] == 0
    assert dump(db) == migrated


def test_migration_failure_rolls_back_all_passwords(db, tmp_path, monkeypatch):
    original = dump(db)
    original_hash = migration.hash_password
    calls = []
    def fail_on_second(password):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("synthetic failure")
        return original_hash(password)
    monkeypatch.setattr(migration, "hash_password", fail_on_second)
    with pytest.raises(RuntimeError, match="synthetic failure"):
        migration.migrate_passwords(db, tmp_path / "backups")
    assert dump(db) == original


def test_bad_backup_aborts_migration(db, monkeypatch):
    original = dump(db)
    def broken(*args, **kwargs):
        raise OSError("no backup space")
    monkeypatch.setattr(migration, "backup_database", broken)
    with pytest.raises(OSError):
        migration.migrate_passwords(db)
    assert dump(db) == original
