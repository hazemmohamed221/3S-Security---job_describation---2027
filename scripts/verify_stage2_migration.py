"""Read-only-source migration rehearsal; never upgrades the source database."""
import argparse
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile

from backups import readonly_connection, verify_database
from database import DB_PATH
from scripts.migrate_integrity import upgrade_connection


def verify(path=DB_PATH, work_dir=None):
    source = Path(path)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='stage2-', dir=work_dir) as folder:
        trial = Path(folder) / 'trial.db'
        with closing(readonly_connection(source)) as src, closing(sqlite3.connect(trial)) as dst:
            src.backup(dst)
            verify_database(dst)
            counts = upgrade_connection(dst)
            first = list(dst.iterdump())
            assert upgrade_connection(dst) == counts
            if first != list(dst.iterdump()):
                raise RuntimeError('Repeated migration changed the database.')
            restored = Path(folder) / 'restored.db'
            with closing(sqlite3.connect(restored)) as recovery:
                dst.backup(recovery)
                verify_database(recovery)
                if list(recovery.iterdump()) != list(dst.iterdump()):
                    raise RuntimeError('Migration restore comparison failed.')
    if before != hashlib.sha256(source.read_bytes()).hexdigest():
        raise RuntimeError('Source database changed during rehearsal.')
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=DB_PATH)
    parser.add_argument('--work-dir')
    args = parser.parse_args()
    print(f'Migration, preservation, idempotence and restore verified: {verify(args.database, args.work_dir)}')


if __name__ == '__main__':
    main()
