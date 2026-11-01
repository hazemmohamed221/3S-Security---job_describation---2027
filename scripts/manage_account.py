"""Local operator tool for explicit provisioning/reset; password input is never echoed.

The operator must already have filesystem access to the database. Not a web endpoint.
"""
import argparse
from contextlib import closing
from getpass import getpass
from pathlib import Path
import sqlite3

from backups import backup_database
from password_security import hash_password
from scripts.migrate_passwords import DEFAULT_DB


def set_account_password(db_path, username, password, *, create_admin=False, full_name="مسؤول النظام", backup_dir=None):
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Username is required.")
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("Use a unique password of at least 12 characters.")
    encoded = hash_password(password)
    backup = backup_database(db_path, backup_dir)
    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            if create_admin:
                if conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
                    raise ValueError("Account already exists; omit --create-admin to reset its password.")
                conn.execute("INSERT INTO users(username,password,full_name,role) VALUES (?,?,?,'admin')",
                             (username, encoded, full_name))
            elif conn.execute("UPDATE users SET password=? WHERE username=?", (encoded, username)).rowcount != 1:
                raise ValueError("Account not found; no changes made.")
    return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--username", required=True)
    parser.add_argument("--create-admin", action="store_true")
    parser.add_argument("--full-name", default="مسؤول النظام")
    args = parser.parse_args()
    password = getpass("New password (at least 12 characters): ")
    if password != getpass("Confirm new password: "):
        parser.error("Passwords do not match; no changes made.")
    if not args.database.exists():
        if not args.create_admin:
            parser.error("Database does not exist.")
        import database
        database.DB_PATH = str(args.database)
        database.init_db()
    backup = set_account_password(args.database, args.username, password, create_admin=args.create_admin, full_name=args.full_name)
    print(f"Account updated. Verified backup: {backup}")
