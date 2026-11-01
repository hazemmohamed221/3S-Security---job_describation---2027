"""Consistent, fail-closed SQLite backups, including restore rehearsal."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
import tempfile
from threading import Lock
from uuid import uuid4

_startup_lock = Lock()
_backed_up = set()


def readonly_connection(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)


def verify_database(conn):
    if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise RuntimeError("SQLite integrity verification failed; no migration was performed.")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Foreign key violations found; no migration was performed.")


def backup_database(db_path, backup_dir=None):
    """Snapshot committed data via SQLite backup API (safe with WAL), then restore-test it.

    Backup files intentionally preserve the source, including legacy credentials.
    Protect the directory with OS permissions; never publish it or commit it.
    """
    source = Path(db_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    directory = Path(backup_dir) if backup_dir else source.parent / "data" / "backups"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    target = directory / f"{source.stem}_{stamp}_{uuid4().hex[:8]}.db"
    # Exclusive creation avoids replacing any previous backup.
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(readonly_connection(source)) as src, closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
            verify_database(dst)
            # Rehearse restore to an independent file; compare complete schema and values.
            with tempfile.TemporaryDirectory(prefix="restore-", dir=directory) as temp:
                with closing(sqlite3.connect(Path(temp) / "restored.db")) as restored:
                    dst.backup(restored)
                    verify_database(restored)
                    if list(dst.iterdump()) != list(restored.iterdump()):
                        raise RuntimeError("Backup restore comparison failed.")
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


def backup_before_startup(db_path):
    """Once per server process/database, before startup DDL or seeding; reruns reuse it."""
    path = Path(db_path).resolve()
    with _startup_lock:
        if path in _backed_up:
            return
        if path.exists():
            backup_database(path)
        _backed_up.add(path)
