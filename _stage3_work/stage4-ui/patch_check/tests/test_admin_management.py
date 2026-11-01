"""Admin-only account lifecycle and real dashboard tests on synthetic data."""
from contextlib import closing
from pathlib import Path
import re
import sqlite3

from argon2 import Type, extract_parameters
import pytest

import auth
import backups
import database
from password_security import verify_password

PASSWORD = 'New-user-password-2027'
REPLACEMENT = 'Replacement-password-2027'
PANEL = '⚙️ لوحة الإدارة والإعدادات'


def dump(path):
    with closing(backups.readonly_connection(path)) as conn:
        return list(conn.iterdump())


def invoke(action, actor_id):
    operations = {
        'directory': lambda: database.get_all_users(actor_id=actor_id),
        'create': lambda: database.create_new_user('new-account', 'اسم جديد', 'employee', PASSWORD, actor_id=actor_id),
        'reset': lambda: database.admin_reset_password(3, REPLACEMENT, actor_id=actor_id),
        'toggle': lambda: database.toggle_user_status(3, actor_id=actor_id),
        'summary': lambda: database.get_admin_system_summary(actor_id=actor_id),
        'backup': lambda: database.create_manual_backup(actor_id=actor_id),
    }
    return operations[action]()


@pytest.mark.parametrize('username,actor_id', [('manager', 2), ('staff', 3)])
@pytest.mark.parametrize('action', ['directory', 'create', 'reset', 'toggle', 'summary', 'backup'])
def test_non_admin_access_denied(sign_in, db, monkeypatch, username, actor_id, action):
    sign_in(username)
    before = dump(db)
    monkeypatch.setattr(backups, 'backup_database', lambda *a, **k: pytest.fail('Unauthorized backup'))
    monkeypatch.setattr(auth, 'hash_password', lambda *a: pytest.fail('Unauthorized password hashing'))
    with pytest.raises(PermissionError):
        invoke(action, actor_id)
    assert dump(db) == before


def test_anonymous_and_forged_admin_identity_cannot_manage_users(session, sign_in, db):
    for action in ('directory', 'create', 'reset', 'toggle', 'summary', 'backup'):
        with pytest.raises(PermissionError):
            invoke(action, 1)
    sign_in('staff')
    session['user'] = {'id': 1, 'role': 'admin'}
    session['role'] = 'admin'
    with pytest.raises(PermissionError):
        database.create_new_user('spoofed', 'اسم', 'admin', PASSWORD, actor_id=1)
    assert session['user']['id'] == 3 and session['user']['role'] == 'employee'
    assert database.get_user_by_username('spoofed') is None


@pytest.mark.parametrize('role', ['admin', 'manager', 'employee'])
def test_new_user_creation_with_argon2id_hash(sign_in, db, monkeypatch, role):
    sign_in('hr')
    original_hash = auth.hash_password
    called = []
    def hashed(password):
        called.append(password)
        return original_hash(password)
    monkeypatch.setattr(auth, 'hash_password', hashed)
    uid = database.create_new_user(' new.account ', 'مستخدم عربي', role, PASSWORD, actor_id=1,
                                   department='إدارة الاختبار', assigned_jd_id=1)
    user = database.get_user_by_username('new.account')
    assert user['id'] == uid and user['role'] == role
    assert user['is_active'] == 1 and user['auth_version'] == 0
    assert user['full_name'] == 'مستخدم عربي' and user['assigned_jd_id'] == 1
    assert user['password'] != PASSWORD and extract_parameters(user['password']).type is Type.ID
    assert verify_password(user['password'], PASSWORD) and called == [PASSWORD]
    assert auth.login('new.account', PASSWORD)[0]


def test_duplicate_username_rejected_gracefully_without_mutation(sign_in, db):
    sign_in('hr')
    before = dump(db)
    with pytest.raises(ValueError, match='مسجل بالفعل') as error:
        database.create_new_user(' manager ', 'اسم بديل', 'admin', PASSWORD, actor_id=1)
    assert 'UNIQUE' not in str(error.value) and PASSWORD not in str(error.value)
    assert dump(db) == before


@pytest.mark.parametrize('overrides', [
    {'username': ''}, {'username': '../bad<script>'}, {'full_name': ''},
    {'role': 'superadmin'}, {'password': 'short'}, {'assigned_jd_id': 999}, {'assigned_jd_id': True},
])
def test_invalid_user_details_fail_atomically(sign_in, db, overrides):
    sign_in('hr')
    values = dict(username='new', full_name='اسم', role='employee', password=PASSWORD, actor_id=1)
    values.update(overrides)
    before = dump(db)
    with pytest.raises(ValueError):
        database.create_new_user(**values)
    assert dump(db) == before


def test_directory_excludes_passwords_and_internal_revocation_version(sign_in):
    sign_in('hr')
    users = database.get_all_users(actor_id=1)
    assert len(users) == 4
    assert all('password' not in user and 'auth_version' not in user for user in users)
    assert all('is_active' in user for user in users)


def test_admin_password_reset_uses_auth_hash_and_revokes_old_session(sign_in, session, monkeypatch):
    sign_in('manager')
    old_session = dict(session)
    before = database.get_user_by_id(2)
    sign_in('hr')
    original_hash = auth.hash_password
    calls = []
    def hashed(password):
        calls.append(password)
        return original_hash(password)
    monkeypatch.setattr(auth, 'hash_password', hashed)
    assert database.admin_reset_password(2, REPLACEMENT, actor_id=1)
    after = database.get_user_by_id(2)
    assert calls == [REPLACEMENT]
    assert extract_parameters(after['password']).type is Type.ID
    assert verify_password(after['password'], REPLACEMENT)
    assert not verify_password(after['password'], 'synthetic-secret')
    assert after['auth_version'] == before['auth_version'] + 1
    assert {k: v for k, v in before.items() if k not in ('password', 'auth_version')} == {
        k: v for k, v in after.items() if k not in ('password', 'auth_version')}
    session.clear()
    session.update(old_session)
    assert auth.get_authenticated_user() is None
    assert auth.login('manager', REPLACEMENT)[0]


def test_disable_then_reenable_does_not_resurrect_old_sessions(sign_in, session):
    sign_in('manager')
    old_session = dict(session)
    sign_in('hr')
    assert database.toggle_user_status(2, actor_id=1, expected_active=True) is False
    assert not auth.login('manager', 'synthetic-secret')[0]
    sign_in('hr')
    assert database.toggle_user_status(2, actor_id=1, expected_active=False) is True
    session.clear()
    session.update(old_session)
    assert auth.get_authenticated_user() is None
    assert auth.login('manager', 'synthetic-secret')[0]


def test_disabled_account_session_cannot_execute_existing_workflow(sign_in, session):
    sign_in('manager')
    old_session = dict(session)
    sign_in('hr')
    database.toggle_user_status(2, actor_id=1)
    session.clear()
    session.update(old_session)
    with pytest.raises(PermissionError):
        database.approve_jd_as_is(1, actor_id=2)
    assert not session.get('logged_in') and 'user' not in session


def test_reset_does_not_reactivate_disabled_account(sign_in):
    sign_in('hr')
    database.toggle_user_status(2, actor_id=1)
    database.admin_reset_password(2, REPLACEMENT, actor_id=1)
    assert database.get_user_by_id(2)['is_active'] == 0
    assert not auth.login('manager', REPLACEMENT)[0]


def test_self_disable_stale_toggle_and_invalid_reset_are_atomic(sign_in, db):
    sign_in('hr')
    before = dump(db)
    for operation in (
        lambda: database.toggle_user_status(1, actor_id=1),
        lambda: database.toggle_user_status(2, actor_id=1, expected_active=False),
        lambda: database.admin_reset_password(999, PASSWORD, actor_id=1),
        lambda: database.admin_reset_password(2, 'short', actor_id=1),
    ):
        with pytest.raises(ValueError):
            operation()
        assert dump(db) == before


def test_self_password_reset_revokes_current_admin_session(sign_in):
    sign_in('hr')
    assert database.admin_reset_password(1, REPLACEMENT, actor_id=1)
    assert auth.get_authenticated_user() is None
    assert auth.login('hr', REPLACEMENT)[0]


def test_summary_counts_all_four_entities(sign_in, db):
    sign_in('hr')
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO interview_schedule(department,manager_name) VALUES('إدارة','مدير')")
    assert database.get_admin_system_summary(actor_id=1) == {'cards': 2, 'responsibilities': 2, 'interviews': 1, 'users': 4}


def test_manual_sha256_backup_preserves_database_and_creates_verified_artifact(sign_in, db):
    sign_in('hr')
    before = dump(db)
    receipt = database.create_manual_backup(actor_id=1)
    assert re.fullmatch('[0-9a-f]{64}', receipt['sha256'])
    artifact = db.parent / 'data' / 'backups' / receipt['name']
    assert backups.verify_backup_checksum(artifact, required=True)
    assert backups.sha256_file(artifact) == receipt['sha256']
    assert dump(artifact) == before and dump(db) == before


def test_additive_access_migration_preserves_legacy_columns_and_is_idempotent(tmp_path):
    with closing(sqlite3.connect(tmp_path / 'legacy.db')) as conn:
        conn.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
        with conn:
            conn.execute("INSERT INTO users(id,username,password,full_name,role) VALUES(15,'legacy','old-encoded-value','اسم محفوظ','admin')")
        before = conn.execute('SELECT * FROM users').fetchall()
        columns = [r[1] for r in conn.execute('PRAGMA table_info(users)')]
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            database._migrate_user_management(conn)
        assert conn.execute(f'SELECT {",".join(columns)} FROM users').fetchall() == before
        assert conn.execute('SELECT is_active,auth_version FROM users').fetchone() == (1, 0)
        first = list(conn.iterdump())
        with conn:
            database._migrate_user_management(conn)
        assert list(conn.iterdump()) == first


def test_access_migration_rolls_back_if_second_column_fails(tmp_path):
    with closing(sqlite3.connect(tmp_path / 'legacy.db')) as conn:
        conn.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
        calls = 0
        def authorizer(action, *args):
            nonlocal calls
            if action == sqlite3.SQLITE_ALTER_TABLE:
                calls += 1
                if calls == 2:
                    return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        before = list(conn.iterdump())
        conn.set_authorizer(authorizer)
        with pytest.raises(sqlite3.DatabaseError):
            with conn:
                conn.execute('BEGIN IMMEDIATE')
                database._migrate_user_management(conn)
        conn.set_authorizer(None)
        assert list(conn.iterdump()) == before


def login_app(db, username):
    from streamlit.testing.v1 import AppTest
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE users SET password=?', (auth.hash_password('synthetic-secret'),))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=15).run()
    app.sidebar.text_input[0].input(username)
    app.sidebar.text_input[1].input('synthetic-secret')
    app.sidebar.button[0].click().run()
    assert not app.exception and not app.error
    return app


@pytest.mark.parametrize('username,role', [('manager', 'manager'), ('staff', 'employee')])
def test_admin_panel_is_hidden_even_when_nonadmin_tampers_with_user_state(db, username, role):
    app = login_app(db, username)
    assert PANEL not in app.sidebar.radio[0].options
    app.session_state['user'] = {'id': 1, 'role': 'admin'}
    app.run()
    assert not app.exception and not app.error
    assert app.session_state['user']['role'] == role
    assert PANEL not in app.sidebar.radio[0].options
    assert not any(button.label == 'إضافة المستخدم' for button in app.button)


def test_real_admin_dashboard_create_reset_toggle_and_manual_backup(db):
    app = login_app(db, 'hr')
    assert PANEL in app.sidebar.radio[0].options
    app.sidebar.radio[0].set_value(PANEL).run()
    next(w for w in app.text_input if w.key == 'admin_new_username').input('ui-user')
    next(w for w in app.text_input if w.key == 'admin_new_full_name').input('مستخدم الواجهة')
    next(w for w in app.selectbox if w.key == 'admin_new_role').select('manager')
    next(w for w in app.text_input if w.key == 'admin_new_password').input(PASSWORD)
    next(b for b in app.button if b.label == 'إضافة المستخدم').click().run()
    assert not app.exception and not app.error
    user = database.get_user_by_username('ui-user')
    assert user['role'] == 'manager' and verify_password(user['password'], PASSWORD)
    assert next(w for w in app.text_input if w.key == 'admin_new_password').value == ''
    assert str(next(m for m in app.metric if m.label == 'المستخدمون').value) == '5'
    next(w for w in app.selectbox if w.key == 'admin_selected_user').select(user['id']).run()
    next(w for w in app.text_input if w.label == 'كلمة المرور البديلة').input(REPLACEMENT)
    next(b for b in app.button if b.label == 'إعادة تعيين كلمة المرور').click().run()
    assert not app.exception and not app.error
    assert verify_password(database.get_user_by_id(user['id'])['password'], REPLACEMENT)
    assert next(w for w in app.text_input if w.label == 'كلمة المرور البديلة').value == ''
    next(b for b in app.button if b.label == 'تعطيل الحساب').click().run()
    assert not app.exception and not app.error
    assert database.get_user_by_id(user['id'])['is_active'] == 0
    next(b for b in app.button if b.label == 'تفعيل الحساب').click().run()
    assert not app.exception and not app.error
    assert database.get_user_by_id(user['id'])['is_active'] == 1
    next(b for b in app.button if b.label == 'إنشاء نسخة احتياطية SHA-256').click().run()
    assert not app.exception and not app.error
    receipt = app.session_state['_admin_backup_receipt']
    assert backups.verify_backup_checksum(db.parent / 'data' / 'backups' / receipt['name'], required=True)
    assert app.session_state['user']['role'] == 'admin'
