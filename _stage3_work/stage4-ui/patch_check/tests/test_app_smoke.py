"""Real Streamlit app execution against synthetic records, with no browser server."""
from pathlib import Path
import sqlite3

import pytest
from password_security import hash_password
from presentation import ADMIN_PAGES


@pytest.mark.parametrize("username,role", [("hr", "admin"), ("manager", "manager"), ("staff", "employee")])
def test_real_app_login_and_logout(db, username, role):
    from streamlit.testing.v1 import AppTest
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET password=?", (hash_password("synthetic-secret"),))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
    assert not app.exception and not app.error
    assert len(app.sidebar.text_input) == 2 and not app.sidebar.selectbox
    assert all(widget.value == "" for widget in app.sidebar.text_input)
    app.sidebar.text_input[0].input(username)
    app.sidebar.text_input[1].input("synthetic-secret")
    app.sidebar.button[0].click().run()
    assert not app.exception and not app.error
    assert app.session_state['role'] == role
    assert 'password' not in app.session_state['user_info']
    assert not app.sidebar.selectbox
    app.query_params['user_id'] = '1'
    app.query_params['role'] = 'admin'
    app.run()
    assert not app.exception
    assert app.session_state['role'] == role
    app.sidebar.button[0].click().run()
    assert not app.exception and not app.session_state['logged_in']
    assert len(app.sidebar.text_input) == 2


def test_manager_can_browse_other_card_but_cannot_submit_writes(db):
    from streamlit.testing.v1 import AppTest
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET password=?", (hash_password("synthetic-secret"),))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
    app.sidebar.text_input[0].input("manager")
    app.sidebar.text_input[1].input("synthetic-secret")
    app.sidebar.button[0].click().run()
    selector = next(widget for widget in app.selectbox if "المعروضة حالياً" in widget.label)
    selector.select(selector.options[1]).run()
    assert not app.exception
    approval = next(button for button in app.button if button.label == "تأكيد الاعتماد والموافقة النهائية")
    submission = next(button for button in app.button if button.label == "إرسال طلب التعديل إلى الموارد البشرية")
    assert approval.disabled and submission.disabled


def test_employee_submit_and_hr_accept_real_app(db):
    from streamlit.testing.v1 import AppTest
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET password=?", (hash_password("synthetic-secret"),))
    path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(path, default_timeout=10).run()
    app.sidebar.text_input[0].input("staff")
    app.sidebar.text_input[1].input("synthetic-secret")
    app.sidebar.button[0].click().run()
    next(widget for widget in app.text_area if "النص المقترح الجديد" in widget.label).input("هدف معدل من الاختبار")
    next(widget for widget in app.text_area if "المبرر الفني" in widget.label).input("مبرر الاختبار")
    next(button for button in app.button if button.label == "إرسال طلب التعديل إلى الموارد البشرية").click().run()
    assert not app.exception and not app.error
    app.sidebar.button[0].click().run()
    app.sidebar.text_input[0].input("hr")
    app.sidebar.text_input[1].input("synthetic-secret")
    app.sidebar.button[0].click().run()
    assert not app.exception and not app.error
    app.sidebar.radio[0].set_value(ADMIN_PAGES['reviews']).run()
    next(button for button in app.button if button.label == "✅ قبول واعتماد التعديل").click().run()
    assert not app.exception and not app.error
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT purpose FROM job_descriptions WHERE id=1").fetchone()[0] == "هدف معدل من الاختبار"
        assert conn.execute("SELECT reviewed_by FROM modification_requests").fetchone()[0] == "مستخدم 1"


def test_interview_no_change_save_preserves_values(db):
    from streamlit.testing.v1 import AppTest
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET password=?", (hash_password("synthetic-secret"),))
        conn.execute("INSERT INTO interview_schedule(seq_num,department,manager_name,status,notes) VALUES(1,'إدارة','مدير','مكتملة','ملاحظات محفوظة')")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
    app.sidebar.text_input[0].input("hr")
    app.sidebar.text_input[1].input("synthetic-secret")
    app.sidebar.button[0].click().run()
    assert not app.exception
    app.sidebar.radio[0].set_value(ADMIN_PAGES['interviews']).run()
    notes = next(widget for widget in app.text_area if widget.label == "الملاحظات ومخرجات الاجتماع المتفق عليها")
    assert notes.value == "ملاحظات محفوظة"
    next(button for button in app.button if button.label == "حفظ وتحديث حالة المقابلة").click().run()
    assert not app.exception and not app.error
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT status,notes FROM interview_schedule").fetchone() == ("مكتملة", "ملاحظات محفوظة")
