"""Restore a backup to a NEW path for rehearsal/recovery; never overwrite a database."""
import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3

from backups import readonly_connection, verify_database, verify_backup_checksum


def restore_database(backup, destination, *, require_checksum=False):
    source = Path(backup).resolve(strict=True)
    verify_backup_checksum(backup, required=require_checksum)
    target = Path(destination).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    # Fail if the destination exists (including the source or a live database).
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(readonly_connection(source)) as src, closing(sqlite3.connect(target)) as dst:
            verify_database(src)
            src.backup(dst)
            verify_database(dst)
            if list(src.iterdump()) != list(dst.iterdump()):
                raise RuntimeError("Restored database differs from the backup.")
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument('--require-checksum', action='store_true')
    args = parser.parse_args()
    print(restore_database(args.backup, args.destination, require_checksum=args.require_checksum))
