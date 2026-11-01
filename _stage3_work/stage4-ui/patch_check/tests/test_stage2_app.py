"""Real Streamlit form checks for Stage 2 stale-update protection."""
from pathlib import Path
import sqlite3

from password_security import hash_password
import governance
from presentation import ADMIN_PAGES


def login(db, username):
    from streamlit.testing.v1 import AppTest
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE users SET password=?', (hash_password('synthetic-secret'),))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=10).run()
    app.sidebar.text_input[0].input(username)
    app.sidebar.text_input[1].input('synthetic-secret')
    app.sidebar.button[0].click().run()
    assert not app.exception and not app.error
    return app


def test_interview_form_detects_concurrent_notes_and_can_reload(db):
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO interview_schedule(id,department,manager_name,status,notes) VALUES(1,'إدارة','مدير','مكتملة','ملاحظات قديمة')")
    app = login(db, 'hr')
    app.sidebar.radio[0].set_value(ADMIN_PAGES['interviews']).run()
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE interview_schedule SET notes='مخرجات أحدث' WHERE id=1")
    next(b for b in app.button if b.label == 'حفظ وتحديث حالة المقابلة').click().run()
    assert not app.exception and app.error
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT notes,status FROM interview_schedule').fetchone() == ('مخرجات أحدث', 'مكتملة')
    next(b for b in app.button if b.label == 'إعادة تحميل بيانات المقابلة').click().run()
    assert not app.exception and not app.error
    assert next(t for t in app.text_area if t.label == 'الملاحظات ومخرجات الاجتماع المتفق عليها').value == 'مخرجات أحدث'


def test_approval_form_binds_decision_to_displayed_revision(db):
    app = login(db, 'manager')
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("UPDATE job_descriptions SET competencies='جدارات أحدث' WHERE id=1")
        governance.bind_review(conn, 1)
    next(b for b in app.button if b.label == 'تأكيد الاعتماد والموافقة النهائية').click().run()
    assert not app.exception and app.error
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT status,version FROM job_descriptions WHERE id=1').fetchone() == ('قيد المراجعة', 2)
        assert conn.execute('SELECT count(*) FROM jd_audit_trail').fetchone()[0] == 0
    next(b for b in app.button if b.label == 'إعادة تحميل بيانات المراجعة').click().run()
    next(b for b in app.button if b.label == 'تأكيد الاعتماد والموافقة النهائية').click().run()
    assert not app.exception and not app.error
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT status FROM job_descriptions WHERE id=1').fetchone()[0] == 'معتمد'
        assert conn.execute('SELECT count(*) FROM jd_audit_trail').fetchone()[0] == 1
