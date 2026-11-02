"""Full JD editor transactions, role boundaries, additive data, Word parity and UI."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import sqlite3

import docx
from docx.oxml.ns import qn
import pytest

import database
import governance
from docx_parser import export_jd_to_docx, parse_jd_docx
from jd_fields import DETAIL_FIELDS, EDIT_FIELDS
from test_revoke_and_edit_jd import workflow_db, execute, rows, ui_login, button


def prepare(status='Draft'):
    with closing(database.get_connection()) as conn, conn:
        conn.execute('''INSERT INTO job_descriptions(id,title,status,purpose,edit_batch_token)
            VALUES(3,'بطاقة شاملة',?,'هدف أصلي','synthetic-seed')''', (status,))
        for uid, order in ((3, 1), (4, 2)):
            conn.execute('INSERT INTO accountabilities(id,jd_id,item_order,description,kpi) VALUES(?,3,?,?,?)',
                         (uid, order, f'مسؤولية {order}', f'مؤشر {order}'))
        conn.execute('UPDATE job_descriptions SET edit_batch_token=NULL WHERE id=3')
        if isinstance(conn, database.PostgresConnectionAdapter):
            for table in ('job_descriptions', 'accountabilities'):
                conn.execute(f"SELECT setval(pg_get_serial_sequence('{table}','id'),"
                             f"(SELECT max(id) FROM {table}))")
        if status in ('Pending Review', 'قيد المراجعة', 'Under Review'):
            governance.bind_review(conn, 3)
    return database.get_jd_by_id(3)


def active():
    return [{name: row[name] for name in ('id', 'description', 'kpi', 'item_order')}
            for row in database.get_accountabilities(3)]


def save(fields, responsibilities=None, **kwargs):
    return database.update_jd_full_details(3, 1, 'اسم غير موثوق', fields,
        active() if responsibilities is None else responsibilities, **kwargs)


def data():
    return {table: rows(table) for table in ('job_descriptions', 'accountabilities', 'jd_audit_trail')}


@pytest.mark.parametrize('status', ['Draft', 'مسودة', 'Pending Review', 'قيد المراجعة', 'Under Review'])
def test_edit_all_fields_once_in_both_editable_states(workflow_db, sign_in, status):
    before = prepare(status)
    sign_in('hr')
    fields = {name: f'قيمة {label}\nتفاصيل عربية' for name, label in EDIT_FIELDS.items()}
    assert save(fields, expected_version=before['version'])[0]
    card = database.get_jd_by_id(3)
    assert all(card[name] == value for name, value in fields.items())
    assert card['version'] == before['version'] + 1
    assert card['status'] == governance.canonical_status(status)
    assert card['review_hash'] is None and card['review_version'] is None and card['edit_batch_token'] is None
    evidence = database.get_decision_evidence(3)
    assert len(evidence) == 1 and evidence[0]['action'] == 'full_update'
    assert evidence[0]['actor_id'] == 1 and evidence[0]['changed_by'] == 'مستخدم 1'
    assert evidence[0]['changed_at']
    assert evidence[0]['snapshot_json']['card']['version'] == before['version']
    assert evidence[0]['result_json']['card']['version'] == card['version']
    assert set(json.loads(evidence[0]['notes'])['الحقول المعدلة']) == set(fields)


@pytest.mark.parametrize('status', ['Approved', 'معتمد', 'Rejected', 'مرفوض'])
def test_approved_and_rejected_cards_cannot_be_fully_edited(workflow_db, sign_in, status):
    prepare(status)
    sign_in('hr')
    before = data()
    assert not save({'job_title': 'مرفوض'})[0]
    assert data() == before


@pytest.mark.parametrize('username,uid', [('manager', 2), ('staff', 3)])
def test_members_cannot_edit_or_impersonate_admin(workflow_db, sign_in, username, uid):
    prepare()
    sign_in(username)
    before = data()
    assert not database.update_jd_full_details(3, uid, 'مسؤول', {'title': 'غير مصرح'}, active())[0]
    assert not save({'title': 'انتحال'})[0]
    assert data() == before


@pytest.mark.parametrize('role', ['hr', 'editor'])
def test_hr_editors_can_edit_unassigned_cards(workflow_db, sign_in, role):
    prepare()
    execute('UPDATE users SET role=? WHERE id=2', (role,))
    sign_in('manager')
    assert database.update_jd_full_details(3, 2, 'مزور', {'job_title': 'عنوان موارد بشرية'}, active())[0]
    assert database.get_audit_trail(3)[0]['changed_by'] == 'مستخدم 2'


def test_add_update_remove_responsibilities_and_metadata_are_one_revision(workflow_db, sign_in):
    before = prepare()
    sign_in('hr')
    other = database.get_accountabilities(1)
    desired = [{'id': 3, 'description': 'مهمة محدثة', 'kpi': '100%', 'item_order': 5},
               {'description': 'مهمة جديدة', 'kpi': 'شهرياً', 'item_order': 7}]
    assert save({'job_code': '3S-TEST', 'education': 'بكالوريوس'}, desired)[0]
    card = database.get_jd_by_id(3)
    assert card['version'] == before['version'] + 1 and card['status'] == 'مسودة'
    saved = database.get_accountabilities(3)
    assert saved[0]['id'] == 3 and saved[0]['description'] == 'مهمة محدثة' and saved[0]['version'] == 2
    assert saved[1]['id'] not in (1, 2, 3, 4) and saved[1]['description'] == 'مهمة جديدة'
    removed = next(row for row in rows('accountabilities') if row['id'] == 4)
    assert removed['is_active'] == 0 and removed['description'] == 'مسؤولية 2'
    assert database.get_accountabilities(1) == other
    notes = json.loads(database.get_audit_trail(3)[0]['notes'])['المسؤوليات']
    assert notes == {'معدلة': [3], 'مضافة': [saved[1]['id']], 'محذوفة من العرض': [4]}


def test_audit_failure_rolls_back_every_field_and_responsibility(workflow_db, sign_in, monkeypatch):
    prepare()
    sign_in('hr')
    before = data()
    def fail(*args):
        raise RuntimeError('synthetic audit unavailable')
    monkeypatch.setattr(database, '_audit_direct_change', fail)
    with pytest.raises(RuntimeError):
        save({'title': 'لن يحفظ', 'languages': 'العربية'}, [{'description': 'إضافة لن تحفظ'}])
    assert data() == before


@pytest.mark.parametrize('fields', [{'id': 1}, {'version': 77}, {'status': 'Approved'},
                                   {'source_file': 'changed.docx'}, {'title': ''}, {'skills': None},
                                   {'job_title': 'أ', 'title': 'ب'}, {'title;DROP TABLE users': 'x'}])
def test_protected_unknown_or_invalid_fields_are_rejected_atomically(workflow_db, sign_in, fields):
    prepare()
    sign_in('hr')
    before = data()
    assert not save(fields)[0]
    assert data() == before


@pytest.mark.parametrize('desired', [
    [{'id': 2, 'description': 'بطاقة أخرى'}],
    [{'id': 3, 'description': 'أ'}, {'id': 3, 'description': 'ب'}],
    [{'description': ''}], [{'description': 'مهمة', 'kpi': 100}],
    [{'description': 'أ', 'item_order': 1}, {'description': 'ب', 'item_order': 1}],
    [{'description': 'أ', 'item_order': 0}], [{'description': 'أ', 'jd_id': 1}],
    [{'id': '3', 'description': 'أ'}],
])
def test_invalid_responsibility_payloads_never_partially_save(workflow_db, sign_in, desired):
    prepare()
    sign_in('hr')
    before = data()
    assert not save({'title': 'لن يتغير'}, desired)[0]
    assert data() == before


def test_removed_rows_cannot_be_reactivated_by_injected_id(workflow_db, sign_in):
    prepare()
    sign_in('hr')
    assert save({}, [active()[0]])[0]
    before = data()
    assert not save({}, [{'id': 4, 'description': 'إعادة غير مصرح بها'}])[0]
    assert data() == before


def test_explicit_empty_list_archives_all_and_noop_is_truly_noop(workflow_db, sign_in):
    prepare()
    sign_in('hr')
    before = data()
    assert save({})[0] and data() == before
    assert save({}, [dict(row, kpi=row['kpi']) for row in active()])[0] and data() == before
    assert save({}, [])[0]
    assert database.get_accountabilities(3) == []
    assert len([row for row in rows('accountabilities') if row['jd_id'] == 3]) == 2
    assert database.get_jd_by_id(3)['version'] == 2


def test_stale_or_parallel_saves_cannot_overwrite_newer_revision(workflow_db, sign_in):
    card = prepare('Pending Review')
    sign_in('hr')
    original = active()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda title: save({'job_title': title}, original,
            expected_version=card['version']), ('عنوان أ', 'عنوان ب')))
    assert sum(ok for ok, message in results) == 1
    assert database.get_jd_by_id(3)['version'] == 2
    before = data()
    assert not save({'title': 'نسخة قديمة'}, original, expected_version=card['version'])[0]
    assert data() == before


def test_pending_review_token_and_modification_requests_are_invalidated(workflow_db, sign_in):
    card = prepare('Pending Review')
    execute('UPDATE users SET assigned_jd_id=3 WHERE id=2')
    sign_in('manager')
    rid = database.submit_modification_request(3, 'Job Purpose', 'purpose', 'هدف أصلي',
                                               'طلب قديم', 'سبب', actor_id=2)
    sign_in('hr')
    assert save({'education': 'مؤهل محدث'})[0]
    assert not database.review_modification_request(rid, 'Accept', '', actor_id=1)[0]
    with pytest.raises(ValueError):
        database.approve_jd_as_is(3, actor_id=1, expected_version=card['version'], expected_hash=card['review_hash'])
    assert database.review_modification_request(rid, 'Reject', 'طلب إصدار أحدث', actor_id=1)[0]
    database.request_jd_review(3, actor_id=1)
    assert database.approve_jd_as_is(3, actor_id=1)


def test_empty_additive_columns_preserve_legacy_review_hash(workflow_db, sign_in):
    prepare('Pending Review')
    sign_in('hr')
    with closing(database.get_connection()) as conn:
        old = governance.snapshot(conn, 3)
    for name in DETAIL_FIELDS:
        old['card'].pop(name)
    legacy_hash = governance.content_hash(old)
    assert database.get_jd_by_id(3)['review_hash'] == legacy_hash
    assert database.approve_jd_as_is(3, actor_id=1)


def test_structured_details_word_export_import_is_lossless_and_deduplicated(workflow_db, sign_in):
    prepare()
    sign_in('hr')
    fields = {name: f'{label}\nتفاصيل عربية' for name, label in EDIT_FIELDS.items()}
    assert save(fields)[0]
    parsed = parse_jd_docx(export_jd_to_docx(*database.get_export_data(3)))
    assert all(parsed[name] == value for name, value in fields.items())
    before = data()
    assert database.create_or_update_jd(parsed, 'same.docx', actor_id=1) == 3
    assert data() == before
    parsed['portal_card_id'] = 999
    imported = database.create_or_update_jd(parsed, 'new.docx', actor_id=1)
    assert all(database.get_jd_by_id(imported)[name] == value for name, value in fields.items())


def test_new_word_detail_markers_are_required_when_extension_is_present(workflow_db, sign_in):
    prepare()
    sign_in('hr')
    assert save({'education': 'بكالوريوس'})[0]
    doc = docx.Document(export_jd_to_docx(*database.get_export_data(3)))
    marker = next(b for b in doc.element.body.iter(qn('w:bookmarkStart'))
                  if b.get(qn('w:name')) == 's3jd2_education')
    marker.getparent().remove(marker)
    import io
    stream = io.BytesIO()
    doc.save(stream)
    stream.seek(0)
    with pytest.raises(ValueError):
        parse_jd_docx(stream)


def ui_prepare(db, status='Draft', role='admin'):
    prepare(status)
    if role != 'admin':
        with sqlite3.connect(db) as conn:
            conn.execute('UPDATE users SET role=? WHERE id=1', (role,))
    app = ui_login(db, card_id=3)
    button(app, '✏️ تعديل شامل لبطاقة الوصف الوظيفي').click().run()
    assert not app.exception and not app.error
    return app


@pytest.mark.parametrize('status', ['Draft', 'Pending Review'])
def test_ui_full_editor_tabs_dynamic_rows_and_confirmed_save(db, status):
    app = ui_prepare(db, status)
    assert len(app.get('tab')) == 4
    assert button(app, '💾 حفظ التعديل الشامل').disabled
    next(w for w in app.text_input if w.label == 'المسمى الوظيفي').input('مدير البطاقة الشاملة')
    next(w for w in app.text_area if w.label == 'المؤهل العلمي').input('هندسة')
    next(w for w in app.text_area if w.label == 'نص المسؤولية 1').input('مهمة معدلة')
    button(app, '➕ إضافة مسؤولية جديدة').click().run()
    assert next(w for w in app.text_input if w.label == 'المسمى الوظيفي').value == 'مدير البطاقة الشاملة'
    next(w for w in app.text_area if w.label == 'نص المسؤولية 3').input('مهمة مضافة')
    button(app, '🗑️ حذف المسؤولية 2').click().run()
    next(w for w in app.checkbox if w.label == 'أؤكد حفظ التعديلات على هذا الإصدار').check().run()
    button(app, '💾 حفظ التعديل الشامل').click().run()
    assert not app.exception and not app.error
    assert app.selectbox(key='directory_jd_id').value == 3
    card = database.get_jd_by_id(3)
    assert card['title'] == 'مدير البطاقة الشاملة' and card['education'] == 'هندسة' and card['version'] == 2
    assert card['status'] == governance.canonical_status(status)
    assert [r['description'] for r in database.get_accountabilities(3)] == ['مهمة معدلة', 'مهمة مضافة']


@pytest.mark.parametrize('role', ['hr', 'editor'])
def test_ui_hr_roles_have_full_editor(db, role):
    app = ui_prepare(db, 'Pending Review', role)
    assert len(app.get('tab')) == 4


def test_ui_cancelling_discards_draft_and_stale_save_requires_reload(db):
    app = ui_prepare(db)
    next(w for w in app.text_area if w.label == 'المؤهل العلمي').input('مدخل ملغى')
    button(app, '➕ إضافة مسؤولية جديدة').click().run()
    button(app, 'إلغاء التعديل الشامل').click().run()
    assert database.get_jd_by_id(3)['education'] is None and len(database.get_accountabilities(3)) == 2
    button(app, '✏️ تعديل شامل لبطاقة الوصف الوظيفي').click().run()
    assert next(w for w in app.text_area if w.label == 'المؤهل العلمي').value == ''
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE job_descriptions SET education='نسخة أحدث',status='مسودة',version=version+1 WHERE id=3")
    next(w for w in app.checkbox if w.label == 'أؤكد حفظ التعديلات على هذا الإصدار').check().run()
    assert any('تغير إصدار' in w.value for w in app.warning)
    assert not any(b.label == '💾 حفظ التعديل الشامل' for b in app.button)
    assert database.get_jd_by_id(3)['education'] == 'نسخة أحدث'


def test_ui_approved_requires_revocation_first(db):
    prepare('Approved')
    app = ui_login(db, card_id=3)
    assert not any(b.label == '✏️ تعديل شامل لبطاقة الوصف الوظيفي' for b in app.button)
    assert any(b.label == '🔄 إلغاء الاعتماد وفتح التعديل' for b in app.button)
