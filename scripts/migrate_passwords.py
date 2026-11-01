"""One-way, idempotent conversion in the existing users.password column.

Run with: python -m scripts.migrate_passwords [--database PATH]
Existing passwords remain usable; rotate previously exposed credentials separately.
"""
import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3

from backups import backup_database, verify_database
from password_security import hash_password, is_password_hash, verify_password

DEFAULT_DB = Path(os.environ.get("JD_DB_PATH", Path(__file__).resolve().parents[1] / "job_descriptions.db"))


def migrate_passwords(db_path=DEFAULT_DB, backup_dir=None):
    path = Path(db_path).resolve(strict=True)
    backup = backup_database(path, backup_dir)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        # Overwrite removed credential bytes in database pages, including slack space.
        conn.execute("PRAGMA secure_delete=ON")
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute("SELECT id,password FROM users ORDER BY id").fetchall()
            migrated = 0
            for user_id, password in rows:
                if is_password_hash(password):
                    continue
                # Do not silently double-hash damaged/unsupported encoded credentials.
                if password.startswith(("$argon2", "$2a$", "$2b$", "$2y$")):
                    raise ValueError("Unsupported/damaged hash found; restore is not needed, transaction rolled back.")
                encoded = hash_password(password)
                if not verify_password(encoded, password):
                    raise RuntimeError("Password verification failed; transaction rolled back.")
                changed = conn.execute("UPDATE users SET password=? WHERE id=? AND password=?",
                                       (encoded, user_id, password)).rowcount
                if changed != 1:
                    raise RuntimeError("Credential changed concurrently; transaction rolled back.")
                migrated += 1
            verify_database(conn)
    return migrated, backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    count, backup = migrate_passwords(args.database)
    print(f"Migrated {count} credentials. Verified rollback backup: {backup}")


if __name__ == "__main__":
    main()
