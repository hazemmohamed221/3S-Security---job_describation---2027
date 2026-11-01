import sqlite3
from contextlib import closing

import pytest
import backups
import database


def test_startup_backup_precedes_initialization_and_does_not_repeat_on_rerun(db, monkeypatch):
    events = []
    real_connect = database.get_connection
    real_backup = backups.backup_database
    def snapshot(path):
        events.append("backup")
        return real_backup(path)
    def connect():
        events.append("connect")
        return real_connect()
    monkeypatch.setattr(backups, "backup_database", snapshot)
    monkeypatch.setattr(database, "get_connection", connect)
    database.init_db()
    assert events[:2] == ["backup", "connect"]
    events.clear()
    database.init_db()
    assert events == ["connect"]


def test_failed_startup_backup_prevents_any_initialization(db, monkeypatch):
    def failed(path):
        raise OSError("disk full")
    def no_connect():
        pytest.fail("Initialization must not open a writable connection after backup failure")
    monkeypatch.setattr(backups, "backup_database", failed)
    monkeypatch.setattr(database, "get_connection", no_connect)
    with pytest.raises(OSError):
        database.init_db()


def test_fresh_bootstrap_creates_no_default_users(db, tmp_path, monkeypatch):
    path = tmp_path / "new.db"
    monkeypatch.setattr(database, "DB_PATH", str(path))
    monkeypatch.setattr(database, "seed_job_descriptions", lambda conn: None)
    monkeypatch.setattr(database, "seed_interview_schedule", lambda conn: None)
    database.init_db()
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_sqlite_foreign_keys_are_enabled(db):
    with closing(database.get_connection()) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO accountabilities(jd_id,item_order,description) VALUES(999,1,'bad')")
