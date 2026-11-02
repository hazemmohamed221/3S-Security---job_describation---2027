"""HR reopening/editing regressions; only disposable synthetic databases are used.

Set JD_HR_TEST_PG_PORT to also run the backend cases on a dedicated local database
named jd_hr_synthetic (never DATABASE_URL). No business database is used by tests.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3

import pytest

import auth
import database
import governance
from presentation import ADMIN_PAGES, arabic_action
from statuses import CardStatus


@pytest.fixture
def workflow_db(db, session, monkeypatch):
    port = os.environ.get('JD_HR_TEST_PG_PORT')
    if not port:
        return db
    import psycopg2
    from scripts.migrate_to_supabase import SCHEMA_SQL, TABLE_ORDER
    from scripts.migrate_hr_workflow import install_postgres_guards
    # Explicit isolated local target, independently of any production credentials.
    def connect():
        return psycopg2.connect(host='127.0.0.1', port=int(port), user='jd_hr_test',
                                dbname='jd_hr_synthetic', connect_timeout=5)
    with closing(connect()) as conn, conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            cur.execute('TRUNCATE ' + ','.join(TABLE_ORDER) + ' RESTART IDENTITY CASCADE')
            with closing(sqlite3.connect(db)) as src:
                for table in TABLE_ORDER:
                    cols = [r[1] for r in src.execute(f'PRAGMA table_info({table})')]
                    for row in src.execute(f'SELECT * FROM {table}'):
                        cur.execute(f'INSERT INTO {table} ({",".join(cols)}) VALUES ({",".join(["%s"] * len(cols))})', row)
                    cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}','id'),"
                                f"COALESCE((SELECT max(id) FROM {table}),1))")
        install_postgres_guards(conn)
    monkeypatch.setattr(database, 'get_connection', lambda: database.PostgresConnectionAdapter(connect()))
    return db


def execute(sql, params=()):
    with closing(database.get_connection()) as conn, conn:
        return conn.execute(sql, params).rowcount


def rows(table):
    with closing(database.get_connection()) as conn:
        return [dict(r) for r in conn.execute(f'SELECT * FROM {table} ORDER BY id')]


def approved(sign_in):
    sign_in('hr')
    if CardStatus.parse(database.get_jd_by_id(1)['status']) != CardStatus.APPROVED:
        database.approve_jd_as_is(1, actor_id=1)
    return database.get_jd_by_id(1)


def draft(sign_in):
    card = approved(sign_in)
    assert database.revoke_jd_approval(1, 1, 'ignored', 'فتح المسودة', expected_version=card['version'])[0]
    return database.get_jd_by_id(1)


@pytest.mark.parametrize('spelling', ['Approved', CardStatus.APPROVED.value])
def test_revoke_bumps_revision_preserves_content_and_exact_immutable_evidence(workflow_db, sign_in, spelling):
    card = approved(sign_in)
    execute('UPDATE job_descriptions SET status=? WHERE id=1', (spelling,))
    reason = '  تحديث الهيكل التنظيمي\nومراجعة حدود الصلاحيات  '
    children = rows('accountabilities')
    previous = database.get_decision_evidence(1)
    assert database.revoke_jd_approval(1, 1, 'اسم مزور', reason, expected_version=card['version'])[0]
    saved = database.get_jd_by_id(1)
    assert saved['status'] == CardStatus.DRAFT.value and saved['version'] == card['version'] + 1
    assert saved['review_version'] is None and saved['review_hash'] is None
    assert rows('accountabilities') == children
    assert all(saved[f] == card[f] for f in governance.CONTENT_FIELDS)
    assert database.get_approval_metadata(1) is None
    record = database.get_audit_trail(1)[0]
    assert record['action'] == 'revoke_approval' and record['notes'] == reason
    assert record['actor_id'] == 1 and record['changed_by'] == 'مستخدم 1' and record['changed_at']
    evidence = database.get_decision_evidence(1)
    assert evidence[:-1] == previous
    assert evidence[-1]['snapshot_json']['card']['status'] == spelling
    assert evidence[-1]['result_json']['card']['status'] == CardStatus.DRAFT.value
    for statement in ('UPDATE jd_audit_trail SET notes=notes', 'DELETE FROM jd_audit_trail'):
        with pytest.raises((sqlite3.IntegrityError, getattr(database.psycopg2, 'IntegrityError', sqlite3.IntegrityError))):
            execute(statement)


@pytest.mark.parametrize('reason', ['', '  \n ', None])
def test_revoke_requires_reason_without_writes(workflow_db, sign_in, reason):
    approved(sign_in)
    before = rows('job_descriptions'), rows('jd_audit_trail')
    assert not database.revoke_jd_approval(1, 1, 'مستخدم 1', reason)[0]
    assert before == (rows('job_descriptions'), rows('jd_audit_trail'))


@pytest.mark.parametrize('status', ['Draft', 'مسودة', 'Pending Review', 'Under Review', 'قيد المراجعة', 'Rejected'])
def test_revoke_rejects_every_nonapproved_state(workflow_db, sign_in, status):
    sign_in('hr')
    execute('INSERT INTO job_descriptions(id,title,status) VALUES(3,?,?)', ('بطاقة اختبار', status))
    assert not database.revoke_jd_approval(3, 1, 'مستخدم 1', 'سبب')[0]
    assert database.get_jd_by_id(3)['version'] == 1 and not database.get_audit_trail(3)


@pytest.mark.parametrize('username,uid', [('manager', 2), ('staff', 3), ('other', 4)])
def test_nonhr_cannot_revoke_edit_or_impersonate_admin(workflow_db, sign_in, username, uid):
    approved(sign_in)
    sign_in(username)
    assert not database.revoke_jd_approval(1, uid, 'مسؤول النظام', 'سبب')[0]
    assert not database.revoke_jd_approval(1, 1, 'مسؤول النظام', 'سبب')[0]
    draft(sign_in)
    sign_in(username)
    before = rows('job_descriptions'), rows('jd_audit_trail')
    assert not database.update_jd_core_info(1, uid, 'مسؤول النظام', {'purpose': 'غير مصرح'})[0]
    assert not database.update_jd_core_info(1, 1, 'مسؤول النظام', {'purpose': 'غير مصرح'})[0]
    assert before == (rows('job_descriptions'), rows('jd_audit_trail'))


@pytest.mark.parametrize('role', ['hr', 'editor'])
def test_hr_roles_authenticate_edit_all_cards_without_admin_privileges(workflow_db, sign_in, role):
    draft(sign_in)
    uid = database.create_new_user('hr_writer', 'أخصائي موارد بشرية', role, 'synthetic-secret', actor_id=1)
    sign_in('hr_writer')
    assert database.update_jd_core_info(1, uid, 'forged', {'job_title': 'عنوان جديد'})[0]
    assert database.get_jd_by_id(1)['title'] == 'عنوان جديد'
    sign_in('hr')
    database.request_jd_review(1, actor_id=1)
    database.approve_jd_as_is(1, actor_id=1)
    sign_in('hr_writer')
    assert database.revoke_jd_approval(1, uid, 'اسم مزور', 'تحديث موثق')[0]
    assert database.get_audit_trail(1)[0]['changed_by'] == 'أخصائي موارد بشرية'
    with pytest.raises(PermissionError):
        database.get_all_users(actor_id=uid)
    with pytest.raises(PermissionError):
        database.create_new_user('escalation', 'اسم', 'admin', 'synthetic-secret', actor_id=uid)


def test_partial_core_edit_versions_once_retains_draft_and_snapshots(workflow_db, sign_in):
    card = draft(sign_in)
    fields = {'job_title': 'مدير المشروعات', 'department': 'إدارة المشروعات', 'sector': 'قطاع العمليات',
              'direct_manager': 'العضو المنتدب', 'job_purpose': 'إدارة المشروعات بكفاءة',
              'qualifications': 'المؤهل: هندسة\nالخبرة: عشر سنوات'}
    assert database.update_jd_core_info(1, 1, 'اسم مزور', fields, expected_version=card['version'])[0]
    saved = database.get_jd_by_id(1)
    assert saved['version'] == card['version'] + 1 and saved['status'] == 'مسودة'
    for name, value in fields.items():
        assert saved[database.CORE_INFO_ALIASES.get(name, name)] == value
    record = database.get_decision_evidence(1)[-1]
    assert record['actor_id'] == 1 and record['changed_by'] == 'مستخدم 1'
    assert record['snapshot_json']['card']['purpose'] == card['purpose']
    assert record['result_json']['card']['purpose'] == fields['job_purpose']
    assert json.loads(record['new_text'])['qualifications'] == fields['qualifications']
    # Unchanged, unrelated content and children survive the edit.
    assert all(saved[f] == card[f] for f in governance.CONTENT_FIELDS if f not in database.CORE_INFO_FIELDS)
    database.request_jd_review(1, actor_id=1)
    database.approve_jd_as_is(1, actor_id=1)
    assert database.get_approval_metadata(1)['version'] == saved['version']


@pytest.mark.parametrize('fields', [{}, {'status': 'Approved'}, {'version': 50}, {'id': 2},
                                     {'purpose': None}, {'title': ' '}, {'title': 'x', 'job_title': 'y'},
                                     {'education': 'do not silently lose fields'}, {'purpose; DROP TABLE users': 'x'}])
def test_invalid_edit_payload_is_atomic(workflow_db, sign_in, fields):
    draft(sign_in)
    before = rows('job_descriptions'), rows('jd_audit_trail')
    assert not database.update_jd_core_info(1, 1, 'مستخدم 1', fields)[0]
    assert before == (rows('job_descriptions'), rows('jd_audit_trail'))


def test_noop_does_not_version_or_audit_and_explicit_empty_can_clear(workflow_db, sign_in):
    card = draft(sign_in)
    before = rows('jd_audit_trail')
    assert database.update_jd_core_info(1, 1, '', {'purpose': card['purpose']})[0]
    assert database.get_jd_by_id(1)['version'] == card['version'] and rows('jd_audit_trail') == before
    assert database.update_jd_core_info(1, 1, '', {'purpose': ''})[0]
    assert database.get_jd_by_id(1)['purpose'] == ''


def test_stale_updates_and_replayed_revoke_fail_without_writes(workflow_db, sign_in):
    original = approved(sign_in)
    assert not database.update_jd_core_info(1, 1, '', {'purpose': 'ممنوع'})[0]
    assert not database.revoke_jd_approval(1, 1, '', 'سبب', expected_version=original['version'] + 1)[0]
    assert database.revoke_jd_approval(1, 1, '', 'سبب', expected_version=original['version'])[0]
    before = rows('job_descriptions'), rows('jd_audit_trail')
    assert not database.revoke_jd_approval(1, 1, '', 'تكرار')[0]
    assert not database.update_jd_core_info(1, 1, '', {'purpose': 'قديم'}, expected_version=original['version'])[0]
    assert before == (rows('job_descriptions'), rows('jd_audit_trail'))


def test_missing_card_and_unauthenticated_actions_fail(workflow_db, sign_in, session):
    sign_in('hr')
    assert not database.revoke_jd_approval(999, 1, '', 'سبب')[0]
    assert not database.update_jd_core_info(999, 1, '', {'title': 'عنوان'})[0]
    session.clear()
    assert not database.revoke_jd_approval(1, 1, '', 'سبب')[0]
    assert not database.update_jd_core_info(1, 1, '', {'title': 'عنوان'})[0]


def test_disabled_hr_account_cannot_write(workflow_db, sign_in):
    approved(sign_in)
    execute('UPDATE users SET is_active=0 WHERE id=1')
    assert not database.revoke_jd_approval(1, 1, '', 'سبب')[0]
    assert not database.update_jd_core_info(1, 1, '', {'purpose': 'تغيير'})[0]


def test_audit_failure_rolls_back_revocation_and_edit(workflow_db, sign_in, monkeypatch):
    approved(sign_in)
    def fail(*args):
        raise RuntimeError('synthetic audit failure')
    with monkeypatch.context() as scoped:
        scoped.setattr(database, '_audit_direct_change', fail)
        with pytest.raises(RuntimeError):
            database.revoke_jd_approval(1, 1, '', 'سبب')
    assert database.get_jd_by_id(1)['status'] == 'معتمد'
    assert database.revoke_jd_approval(1, 1, '', 'سبب')[0]
    before = rows('job_descriptions'), rows('jd_audit_trail')
    monkeypatch.setattr(database, '_audit_direct_change', fail)
    with pytest.raises(RuntimeError):
        database.update_jd_core_info(1, 1, '', {'purpose': 'تغيير'})
    assert before == (rows('job_descriptions'), rows('jd_audit_trail'))


def test_concurrent_revocations_only_one_wins(workflow_db, sign_in):
    approved(sign_in)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: database.revoke_jd_approval(1, 1, '', 'سبب'), range(2)))
    assert sum(ok for ok, message in results) == 1
    assert len([r for r in rows('jd_audit_trail') if r['action'] == 'revoke_approval']) == 1


def test_concurrent_core_edits_check_the_displayed_version(workflow_db, sign_in):
    card = draft(sign_in)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda text: database.update_jd_core_info(
            1, 1, '', {'purpose': text}, expected_version=card['version']), ('هدف أ', 'هدف ب')))
    assert sum(ok for ok, message in results) == 1
    assert database.get_jd_by_id(1)['version'] == card['version'] + 1


def test_guard_upgrade_is_idempotent_and_preserves_rows(workflow_db):
    before = rows('job_descriptions'), rows('accountabilities'), rows('users'), rows('jd_audit_trail')
    for _ in range(2):
        with closing(database.get_connection()) as conn, conn:
            if isinstance(conn, database.PostgresConnectionAdapter):
                from scripts.migrate_hr_workflow import install_postgres_guards
                install_postgres_guards(conn._conn)
            else:
                governance.migrate(conn)
    assert before == (rows('job_descriptions'), rows('accountabilities'), rows('users'), rows('jd_audit_trail'))


@pytest.mark.parametrize('status', ['Under Review', 'Rejected'])
def test_direct_edit_requires_draft(workflow_db, sign_in, status):
    sign_in('hr')
    execute('INSERT INTO job_descriptions(id,title,status) VALUES(3,?,?)', ('بطاقة', status))
    assert not database.update_jd_core_info(3, 1, '', {'purpose': 'غير متاح'})[0]
    assert database.get_jd_by_id(3)['version'] == 1


def ui_login(db, username='hr', card_id=None):
    from streamlit.testing.v1 import AppTest
    from password_security import hash_password
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE users SET password=?', (hash_password('synthetic-secret'),))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=10).run()
    app.sidebar.text_input[0].input(username)
    app.sidebar.text_input[1].input('synthetic-secret')
    app.sidebar.button[0].click().run()
    app.sidebar.radio[0].set_value(ADMIN_PAGES['directory']).run()
    if card_id is not None:
        selector = next(w for w in app.selectbox if w.label.startswith('اختر بطاقة الوصف الوظيفي لعرض'))
        selector.set_value(card_id).run()
    assert not app.exception and not app.error
    return app


def button(app, label):
    return next(b for b in app.button if b.label == label)


def test_ui_revoke_requires_reason_then_reopens_and_saves_arabic_metadata(db):
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO job_descriptions(id,title,status) VALUES(0,'بطاقة معتمدة','Approved')")
    app = ui_login(db, card_id=0)
    button(app, '🔄 إلغاء الاعتماد وفتح التعديل').click().run()
    button(app, 'تأكيد إلغاء الاعتماد').click().run()
    assert any('سبب' in error.value for error in app.error)
    next(w for w in app.text_area if w.label == 'سبب إلغاء الاعتماد').input('مراجعة المتطلبات')
    button(app, 'تأكيد إلغاء الاعتماد').click().run()
    assert not app.exception and not app.error
    assert not any(b.label == '🔄 إلغاء الاعتماد وفتح التعديل' for b in app.button)
    button(app, '✏️ تعديل بيانات البطاقة').click().run()
    button(app, 'حفظ بيانات البطاقة').click().run()
    assert database.get_jd_by_id(0)['version'] == 2 and database.get_jd_by_id(0)['qualifications'] is None
    next(w for w in app.text_input if w.label == 'المسمى الوظيفي').input('المسمى الجديد')
    button(app, 'حفظ بيانات البطاقة').click().run()
    assert not app.exception and not app.error
    card = database.get_jd_by_id(0)
    assert card['title'] == 'المسمى الجديد' and card['status'] == 'مسودة' and card['version'] == 3
    assert card['qualifications'] is None
    assert app.selectbox(key='directory_jd_id').value == 0
    assert any(element.value == '### المسمى الجديد' for element in app.markdown)


@pytest.mark.parametrize('role', ['hr', 'editor'])
def test_ui_hr_roles_have_directory_actions_without_admin_panel(db, role):
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET role=? WHERE id=2", (role,))
        conn.execute("INSERT INTO job_descriptions(id,title,status) VALUES(0,'بطاقة مسودة','Draft')")
    app = ui_login(db, 'manager', card_id=0)
    assert app.sidebar.radio[0].options == [ADMIN_PAGES['directory']]
    assert any(b.label == '✏️ تعديل بيانات البطاقة' for b in app.button)
    assert not any(b.label == 'إضافة المستخدم' for b in app.button)


@pytest.mark.parametrize('username', ['manager', 'staff'])
def test_ui_members_have_no_direct_edit_or_revoke_controls(db, username):
    app = ui_login(db, username)
    assert not any(b.label in ('✏️ تعديل بيانات البطاقة', '🔄 إلغاء الاعتماد وفتح التعديل') for b in app.button)


def test_revocation_action_has_readable_arabic_label():
    assert arabic_action('revoke_approval') == 'إلغاء الاعتماد وإعادة البطاقة للمسودة'


def test_ui_stale_edit_is_rejected_and_reload_recovers(db):
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO job_descriptions(id,title,status,purpose) VALUES(0,'مسودة قديمة','Draft','قديم')")
    app = ui_login(db, card_id=0)
    button(app, '✏️ تعديل بيانات البطاقة').click().run()
    next(w for w in app.text_area if w.label == 'الهدف العام من الوظيفة').input('مدخل قديم')
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE job_descriptions SET purpose='أحدث',status='مسودة',version=version+1 WHERE id=0")
    button(app, 'حفظ بيانات البطاقة').click().run()
    assert not app.exception
    assert any('تغير إصدار' in warning.value for warning in app.warning)
    assert database.get_jd_by_id(0)['purpose'] == 'أحدث'
    button(app, 'تحميل الإصدار الحالي وإغلاق النموذج القديم').click().run()
    button(app, '✏️ تعديل بيانات البطاقة').click().run()
    assert next(w for w in app.text_area if w.label == 'الهدف العام من الوظيفة').value == 'أحدث'


def test_ui_cancelling_revoke_leaves_approved_card_and_audit_untouched(db):
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO job_descriptions(id,title,status) VALUES(0,'معتمدة','Approved')")
    app = ui_login(db, card_id=0)
    button(app, '🔄 إلغاء الاعتماد وفتح التعديل').click().run()
    next(w for w in app.text_area if w.label == 'سبب إلغاء الاعتماد').input('تم إلغاء العملية')
    button(app, 'إلغاء').click().run()
    assert not app.exception and not database.get_audit_trail(0)
    assert database.get_jd_by_id(0)['status'] == 'معتمد'


def test_ui_revoke_from_filtered_directory_keeps_same_card_open(db):
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO job_descriptions(id,title,department,status) VALUES(0,'معتمدة','إدارة قديمة','Approved')")
    app = ui_login(db, card_id=0)
    app.selectbox(key='directory_status').set_value('معتمد').run()
    app.selectbox(key='directory_department').set_value('إدارة قديمة').run()
    button(app, '🔄 إلغاء الاعتماد وفتح التعديل').click().run()
    next(w for w in app.text_area if w.label == 'سبب إلغاء الاعتماد').input('تغيير الإدارة')
    button(app, 'تأكيد إلغاء الاعتماد').click().run()
    assert not app.exception and not app.error
    assert app.selectbox(key='directory_jd_id').value == 0
    assert app.selectbox(key='directory_status').value == 'كافة الحالات'
    button(app, '✏️ تعديل بيانات البطاقة').click().run()
    next(w for w in app.text_input if w.label == 'الإدارة').input('إدارة جديدة')
    button(app, 'حفظ بيانات البطاقة').click().run()
    assert not app.exception and not app.error
    assert app.selectbox(key='directory_jd_id').value == 0
    assert database.get_jd_by_id(0)['department'] == 'إدارة جديدة'


@pytest.mark.parametrize('operation,status', [('revoke_jd_approval', 'Approved'),
                                            ('update_jd_core_info', 'Draft')])
def test_ui_old_database_module_reports_deployment_mismatch_without_writes(db, monkeypatch, operation, status):
    with sqlite3.connect(db) as conn:
        conn.execute('INSERT INTO job_descriptions(id,title,status) VALUES(0,?,?)', ('بطاقة الاختبار', status))
    app = ui_login(db, card_id=0)
    before = database.get_jd_by_id(0), database.get_audit_trail(0)
    monkeypatch.delattr(database, operation)
    if operation == 'revoke_jd_approval':
        button(app, '🔄 إلغاء الاعتماد وفتح التعديل').click().run()
        next(w for w in app.text_area if w.label == 'سبب إلغاء الاعتماد').input('سبب الاختبار')
        button(app, 'تأكيد إلغاء الاعتماد').click().run()
    else:
        button(app, '✏️ تعديل بيانات البطاقة').click().run()
        next(w for w in app.text_input if w.label == 'المسمى الوظيفي').input('تعديل لن يحفظ')
        button(app, 'حفظ بيانات البطاقة').click().run()
    assert not app.exception and not app.success
    assert any('إصدار خدمة البيانات' in error.value and 'Reboot app' in error.value for error in app.error)
    assert before == (database.get_jd_by_id(0), database.get_audit_trail(0))
