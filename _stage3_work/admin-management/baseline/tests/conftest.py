"""All writes use disposable synthetic databases, never the business database."""
from pathlib import Path
import sqlite3
from contextlib import closing

import pytest
import database
import governance


def build_synthetic_database(path):
    with sqlite3.connect(path) as conn:
        conn.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        for n in (1, 2):
            conn.execute("INSERT INTO job_descriptions(id,title,department,purpose) VALUES (?,?,?,?)",
                         (n, f"بطاقة {n}", "إدارة الاختبار", "هدف أصلي"))
            conn.execute("INSERT INTO accountabilities(id,jd_id,item_order,description) VALUES (?,?,1,?)",
                         (n, n, "مسؤولية أصلية"))
        for uid, name, role, assigned in ((1, "hr", "admin", None), (2, "manager", "manager", 1),
                                           (3, "staff", "employee", 1), (4, "other", "manager", 2)):
            conn.execute("INSERT INTO users(id,username,password,full_name,role,assigned_jd_id) VALUES (?,?,?,?,?,?)",
                         (uid, name, "synthetic-secret", f"مستخدم {uid}", role, assigned))
        conn.row_factory = sqlite3.Row
        governance.migrate(conn)
    return path


def pytest_addoption(parser):
    parser.addoption('--restored-fixture', help='Verified synthetic backup to restore independently for every db fixture.')


@pytest.fixture
def db(monkeypatch, tmp_path, request):
    path = tmp_path / 'synthetic.db'
    monkeypatch.setattr(database, 'DB_PATH', str(path))
    source = request.config.getoption('--restored-fixture')
    if source:
        from backups import readonly_connection
        from scripts.restore_database import restore_database
        # Explicitly refuse personnel databases, including accidental operator input.
        with closing(readonly_connection(source)) as conn:
            users = conn.execute('SELECT id,username,password FROM users ORDER BY id').fetchall()
            if users != [(1, 'hr', 'synthetic-secret'), (2, 'manager', 'synthetic-secret'),
                         (3, 'staff', 'synthetic-secret'), (4, 'other', 'synthetic-secret')]:
                raise ValueError('The recovery test gate requires the synthetic fixture, never a business database.')
        restore_database(source, path, require_checksum=True)
    else:
        build_synthetic_database(path)
    return path


class Session(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


@pytest.fixture
def session(db, monkeypatch):
    from types import SimpleNamespace
    import auth
    from password_security import hash_password
    encoded = hash_password("synthetic-secret")
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET password=?", (encoded,))
    state = Session()
    def rerun():
        raise RuntimeError("rerun")
    monkeypatch.setattr(auth, "st", SimpleNamespace(session_state=state, rerun=rerun))
    return state


@pytest.fixture
def sign_in(session):
    import auth
    def enter(username="manager"):
        assert auth.login(username, "synthetic-secret")[0]
        return session
    return enter
