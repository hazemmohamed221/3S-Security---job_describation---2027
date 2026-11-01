import sqlite3

import database
from utils import generate_diff_html


def test_existing_card_fetch_and_schema(db):
    card = database.get_jd_by_id(1)
    assert card["title"] == "بطاقة 1"
    assert card["purpose"] == "هدف أصلي"
    assert database.get_accountabilities(1)[0]["jd_id"] == 1
    assert database.get_jd_by_id(999) is None
    with database.get_connection() as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert {r[1] for r in conn.execute("PRAGMA table_info(users)")} == {
            "id", "username", "password", "full_name", "role", "department", "assigned_jd_id", "created_at"}
        assert {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")} == {
            "users", "job_descriptions", "accountabilities", "modification_requests", "jd_audit_trail", "interview_schedule"}


def test_parameterized_queries_preserve_literal_text(db):
    hostile = "هدف ' ; DROP TABLE users; -- العربية"
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE job_descriptions SET purpose=? WHERE id=?", (hostile, 1))
    assert database.get_jd_by_id(1)["purpose"] == hostile
    assert database.get_user_by_username("' OR 1=1 --") is None
    assert database.get_jd_by_id("1 OR 1=1") is None
    assert len(database.get_all_jds()) == 2


def test_word_diff_arabic_replacement_and_escaping():
    result = generate_diff_html("نص قديم", "نص جديد <script>bad</script>")
    assert "direction: rtl" in result
    assert "نص " in result and "- قديم" in result and "+ جديد" in result
    assert "text-decoration: line-through" in result
    assert "&lt;script&gt;" in result and "<script>" not in result


def test_word_diff_empty_whitespace_and_newlines():
    assert "<br>" in generate_diff_html("عربي\n  ثابت", "عربي\n  ثابت")
    assert "<span" not in generate_diff_html(None, None)
    assert "+ إضافة" in generate_diff_html(None, "إضافة")
    assert "- حذف" in generate_diff_html("حذف", None)
