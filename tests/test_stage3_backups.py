"""Checksummed snapshots, conservative retention, WAL recovery and rollback."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

import pytest

import backups
import database
from scripts.backup import rotate_backups, run_backup
from scripts.restore_database import restore_database


def dump(path):
    with closing(backups.readonly_connection(path)) as conn:
        return list(conn.iterdump())


def test_backup_checksum_and_verified_restore_are_exact(db, tmp_path):
    artifact = backups.backup_database(db, tmp_path / 'backups')
    assert backups.verify_backup_checksum(artifact, required=True)
    assert backups.checksum_path(artifact).read_text(encoding='utf-8').startswith(backups.sha256_file(artifact))
    restored = restore_database(artifact, tmp_path / 'restored.db', require_checksum=True)
    assert dump(restored) == dump(db)
    with closing(backups.readonly_connection(restored)) as conn:
        backups.verify_database(conn)


def test_backup_captures_committed_wal_without_checkpoint(db, tmp_path):
    with closing(database.get_connection()) as writer:
        writer.execute('PRAGMA wal_autocheckpoint=0')
        with writer:
            writer.execute("UPDATE job_descriptions SET purpose='محتوى WAL' WHERE id=1")
        assert Path(str(db) + '-wal').stat().st_size > 0
        artifact = backups.backup_database(db, tmp_path / 'backups')
        with closing(backups.readonly_connection(artifact)) as copy:
            assert copy.execute('SELECT purpose FROM job_descriptions WHERE id=1').fetchone()[0] == 'محتوى WAL'
        assert not Path(str(artifact) + '-wal').exists()
        assert backups.verify_backup_checksum(artifact, required=True)


@pytest.mark.parametrize('tamper', ['database', 'checksum', 'missing'])
def test_strict_restore_rejects_tampered_or_missing_checksums(db, tmp_path, tamper):
    artifact = backups.backup_database(db, tmp_path / 'backups')
    if tamper == 'database':
        with artifact.open('ab') as handle:
            handle.write(b'tampered')
    elif tamper == 'checksum':
        backups.checksum_path(artifact).write_text('0' * 64, encoding='utf-8')
    else:
        backups.checksum_path(artifact).unlink()
    destination = tmp_path / 'never-created.db'
    with pytest.raises(RuntimeError):
        restore_database(artifact, destination, require_checksum=True)
    assert not destination.exists()


def managed_fixture(source, folder, stamp, number):
    folder.mkdir(exist_ok=True)
    name = f'{source.stem}_{stamp:%Y%m%dT%H%M%S.%fZ}_{number:08x}.db'
    target = folder / name
    with closing(backups.readonly_connection(source)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
    backups.write_backup_checksum(target)
    return target


def test_rotation_prunes_only_expired_managed_backups_and_keeps_five(db, tmp_path):
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    folder = tmp_path / 'backups'
    old = [managed_fixture(db, folder, now - timedelta(days=40 + n), n) for n in range(7)]
    new = [managed_fixture(db, folder, now - timedelta(days=n), n + 100) for n in range(2)]
    unrelated = folder / 'other-project.db'
    unrelated.write_bytes(b'must be retained')
    pruned = rotate_backups(db, folder, now=now)
    assert set(pruned) == set(old[3:])
    assert all(p.exists() for p in old[:3] + new)
    assert all(not p.exists() and not backups.checksum_path(p).exists() for p in pruned)
    assert unrelated.read_bytes() == b'must be retained'


def test_retention_boundary_and_minimum_five_even_if_all_expired(db, tmp_path):
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    folder = tmp_path / 'backups'
    recent = [managed_fixture(db, folder, now - timedelta(days=n), n) for n in range(5)]
    boundary = managed_fixture(db, folder, now - timedelta(days=30), 80)
    assert rotate_backups(db, folder, now=now) == []
    assert rotate_backups(db, folder, now=now + timedelta(seconds=1)) == [boundary]
    assert rotate_backups(db, folder, now=now + timedelta(days=400)) == []
    assert all(p.exists() for p in recent)


def test_legacy_backups_are_verified_and_sealed_before_rotation(db, tmp_path):
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    artifact = managed_fixture(db, tmp_path / 'backups', now, 1)
    backups.checksum_path(artifact).unlink()
    assert rotate_backups(db, artifact.parent, now=now) == []
    assert backups.verify_backup_checksum(artifact, required=True)


def test_bad_candidate_aborts_rotation_before_any_deletion(db, tmp_path):
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    old = [managed_fixture(db, tmp_path / 'backups', now - timedelta(days=100 + n), n) for n in range(6)]
    backups.checksum_path(old[2]).write_text('corrupt', encoding='utf-8')
    with pytest.raises(RuntimeError):
        rotate_backups(db, old[0].parent, now=now)
    assert all(p.exists() for p in old)


def test_backup_failure_does_not_start_rotation(db, monkeypatch, tmp_path):
    import scripts.backup as command
    def fail(*args):
        raise OSError('synthetic disk failure')
    monkeypatch.setattr(command, 'backup_database', fail)
    monkeypatch.setattr(command, 'rotate_backups', lambda *args, **kwargs: pytest.fail('Must not prune without a new verified snapshot'))
    with pytest.raises(OSError):
        run_backup(db, tmp_path / 'backups')


def test_checksum_write_failure_removes_incomplete_new_artifact(db, monkeypatch, tmp_path):
    def fail(*args):
        raise OSError('synthetic checksum failure')
    monkeypatch.setattr(backups, 'write_backup_checksum', fail)
    folder = tmp_path / 'backups'
    with pytest.raises(OSError):
        backups.backup_database(db, folder)
    assert list(folder.iterdir()) == []


@pytest.mark.parametrize('days,keep', [(0, 5), (30, 4)])
def test_invalid_retention_cannot_remove_backups(tmp_path, days, keep):
    with pytest.raises(ValueError):
        rotate_backups('synthetic.db', tmp_path, retention_days=days, keep=keep)


def test_restored_backup_retains_decision_snapshots_and_replay_guard(sign_in, db, tmp_path, monkeypatch):
    sign_in()
    database.approve_jd_as_is(1, actor_id=2)
    before = database.get_decision_evidence(1)
    artifact = backups.backup_database(db, tmp_path / 'backups')
    restored = restore_database(artifact, tmp_path / 'restored.db', require_checksum=True)
    monkeypatch.setattr(database, 'DB_PATH', str(restored))
    assert database.get_decision_evidence(1) == before
    assert database.get_approval_metadata(1)['version'] == 1
    with pytest.raises(ValueError):
        database.approve_jd_as_is(1, actor_id=2)
