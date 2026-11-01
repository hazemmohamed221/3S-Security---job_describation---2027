from contextlib import closing
import sqlite3

import pytest
from password_security import verify_password
from scripts.manage_account import set_account_password
from scripts.restore_database import restore_database


def test_account_reset_preserves_identity_and_revokes_session(db, session, sign_in, tmp_path):
    import auth
    sign_in()
    with sqlite3.connect(db) as conn:
        before = conn.execute("SELECT * FROM users WHERE id=2").fetchone()
    set_account_password(db, "manager", "independent-new-password", backup_dir=tmp_path / "backups")
    with sqlite3.connect(db) as conn:
        after = conn.execute("SELECT * FROM users WHERE id=2").fetchone()
    assert before[:2] == after[:2] and before[3:] == after[3:]
    assert verify_password(after[2], "independent-new-password")
    assert not verify_password(after[2], "synthetic-secret")
    assert auth.get_authenticated_user() is None


def test_explicit_admin_creation_and_no_overwrite(db, tmp_path):
    set_account_password(db, "new-admin", "independent-new-password", create_admin=True,
                         full_name="مسؤول جديد", backup_dir=tmp_path / "backups")
    with sqlite3.connect(db) as conn:
        user = conn.execute("SELECT role,password FROM users WHERE username='new-admin'").fetchone()
    assert user[0] == "admin" and verify_password(user[1], "independent-new-password")
    with pytest.raises(ValueError):
        set_account_password(db, "manager", "independent-new-password", create_admin=True,
                             backup_dir=tmp_path / "backups")


def test_restore_is_exact_and_refuses_overwrite(db, tmp_path):
    restored = restore_database(db, tmp_path / "restore.db")
    with closing(sqlite3.connect(db)) as src, closing(sqlite3.connect(restored)) as dst:
        assert list(src.iterdump()) == list(dst.iterdump())
    with pytest.raises(FileExistsError):
        restore_database(db, restored)
    with pytest.raises(FileExistsError):
        restore_database(db, db)
