"""Verified backups with SHA-256 and age/count retention; suitable for a scheduler."""
import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

from backups import (backup_database, checksum_path, readonly_connection, verify_database,
                     verify_backup_checksum, write_backup_checksum)
from scripts.migrate_passwords import DEFAULT_DB


def rotate_backups(database, directory, *, retention_days=30, keep=5, now=None):
    if retention_days < 1 or keep < 5:
        raise ValueError('Retention must be at least one day and keep at least five backups.')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Retention requires a timezone-aware clock.')
    root = Path(directory).resolve(strict=True)
    pattern = re.compile(re.escape(Path(database).stem) + r'_(\d{8}T\d{6}\.\d{6}Z)_[0-9a-f]{8}\.db\Z')
    candidates = []
    for item in root.iterdir():
        match = pattern.fullmatch(item.name)
        if not match:
            continue
        # Validate the final absolute targets before deleting any artifact.
        if item.is_symlink() or item.resolve().parent != root or not item.is_file():
            raise RuntimeError('Backup rotation encountered an unsafe path.')
        sidecar = checksum_path(item)
        if sidecar.is_symlink() or sidecar.resolve().parent != root:
            raise RuntimeError('Backup rotation encountered an unsafe checksum path.')
        stamp = datetime.strptime(match[1], '%Y%m%dT%H%M%S.%fZ').replace(tzinfo=timezone.utc)
        # Validate and seal managed legacy backups before making retention decisions.
        verify_backup_checksum(item)
        with closing(readonly_connection(item)) as conn:
            verify_database(conn)
        write_backup_checksum(item)
        candidates.append((stamp, item))
    candidates.sort(key=lambda pair: (pair[0], pair[1].name), reverse=True)
    expired = [item for stamp, item in candidates[keep:] if stamp < now - timedelta(days=retention_days)]
    for item in expired:
        if item.is_symlink() or item.resolve().parent != root or checksum_path(item).is_symlink():
            raise RuntimeError('Backup target changed during rotation.')
        item.unlink()
        checksum_path(item).unlink()
    return expired


def run_backup(database=DEFAULT_DB, directory=None, *, retention_days=30, keep=5):
    directory = Path(directory) if directory else Path(database).resolve().parent / 'data' / 'backups'
    artifact = backup_database(database, directory)
    pruned = rotate_backups(database, directory, retention_days=retention_days, keep=keep)
    return artifact, pruned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DB)
    parser.add_argument('--backup-dir', type=Path)
    parser.add_argument('--retention-days', type=int, default=30)
    parser.add_argument('--keep', type=int, default=5)
    args = parser.parse_args()
    artifact, pruned = run_backup(args.database, args.backup_dir, retention_days=args.retention_days, keep=args.keep)
    print(f'Verified backup: {artifact}; checksum: {checksum_path(artifact)}; pruned: {len(pruned)}')


if __name__ == '__main__':
    main()
