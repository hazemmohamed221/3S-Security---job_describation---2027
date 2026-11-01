"""Backed-up, transactional Stage 2 upgrade of an existing portal database."""
import argparse
from contextlib import closing
import sqlite3

from backups import backup_database, verify_database
from database import DB_PATH
import governance


def legacy_values(conn):
    result = {}
    for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        quoted = '"' + name.replace('"', '""') + '"'
        columns = [r[1] for r in conn.execute(f'PRAGMA table_info({quoted})')]
        result[name] = (columns, [tuple(r) for r in conn.execute(f'SELECT * FROM {quoted} ORDER BY rowid')])
    return result


def assert_preserved(conn, original):
    for name, (columns, values) in original.items():
        quoted = '"' + name.replace('"', '""') + '"'
        selected = ','.join('"' + c.replace('"', '""') + '"' for c in columns)
        if [tuple(r) for r in conn.execute(f'SELECT {selected} FROM {quoted} ORDER BY rowid')] != values:
            raise RuntimeError(f'Preservation check failed for {name}; migration rolled back.')


def upgrade_connection(conn):
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        original = legacy_values(conn)
        governance.migrate(conn)
        assert_preserved(conn, original)
        # verify_database expects tuple rows rather than sqlite3.Row objects.
        conn.row_factory = None
        verify_database(conn)
        counts = {t: conn.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
                  for t in ('job_descriptions', 'accountabilities', 'interview_schedule')}
    return counts


def migrate_integrity(path=DB_PATH, backup_dir=None):
    backup = backup_database(path, backup_dir)
    with closing(sqlite3.connect(path)) as conn:
        counts = upgrade_connection(conn)
    return counts, backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=DB_PATH)
    args = parser.parse_args()
    counts, backup = migrate_integrity(args.database)
    print(f'Preserved records: {counts}. Verified backup: {backup}')


if __name__ == '__main__':
    main()
