import sqlite3

import pytest
import auth
import database


def request(actor_id=2, jd_id=1, clause_id="purpose", section="Job Purpose"):
    original = "مسؤولية أصلية" if section == "Accountability" else "هدف أصلي"
    return database.submit_modification_request(jd_id, section, clause_id, original,
                                                 "نص مقترح ' آمن", "مبرر", actor_id=actor_id)


def test_login_requires_hash_and_explicit_credentials(db, session):
    assert not auth.login("hr", "wrong")[0]
    assert not auth.login("' OR 1=1 --", "synthetic-secret")[0]
    assert auth.login("hr", "synthetic-secret")[0]
    assert "password" not in session.user_info
    assert "synthetic-secret" not in repr(session)
    assert "$argon2" not in repr(session)


def test_plaintext_login_is_rejected(db, session):
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET password='legacy-plaintext' WHERE id=1")
    assert not auth.login("hr", "legacy-plaintext")[0]


def test_logout_and_login_clear_all_drafts(session, sign_in):
    session["upload_draft"] = "private"
    sign_in()
    assert "upload_draft" not in session
    session["review_draft"] = "private"
    with pytest.raises(RuntimeError, match="rerun"):
        auth.logout()
    assert not session.get("logged_in") and "review_draft" not in session
    with pytest.raises(PermissionError):
        database.approve_jd_as_is(1, actor_id=2)


def test_forged_actor_id_and_role_are_rejected(sign_in, session):
    sign_in("staff")
    session["role"] = "admin"
    session["user_info"] = {"id": 1, "role": "admin"}
    with pytest.raises(PermissionError):
        database.approve_jd_as_is(1, actor_id=1)
    with pytest.raises(PermissionError):
        database.review_modification_request(1, "Reject", "", actor_id=3)
    assert auth.get_authenticated_user()["id"] == 3


@pytest.mark.parametrize("username,actor_id", [("manager", 2), ("staff", 3)])
def test_assignment_scope_blocks_other_card(sign_in, username, actor_id):
    sign_in(username)
    with pytest.raises(PermissionError):
        database.approve_jd_as_is(2, actor_id=actor_id)
    with pytest.raises(PermissionError):
        request(actor_id=actor_id, jd_id=2)
    assert len(database.get_all_jds()) == 2


def test_cross_card_clause_is_rejected_at_submission(sign_in, db):
    sign_in()
    with pytest.raises(ValueError):
        request(clause_id="2", section="Accountability")
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM modification_requests").fetchone()[0] == 0


@pytest.mark.parametrize("decision", ["Accept", "Reject"])
def test_legacy_cross_card_request_rejected_without_any_writes(sign_in, db, decision):
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO modification_requests(jd_id,section_name,clause_id,original_text,proposed_text,justification,requested_by) VALUES (1,'Accountability','2',?,?,?,?)",
                     ("مسؤولية أصلية", "bad", "reason", "legacy actor"))
        before = list(conn.iterdump())
    sign_in("hr")
    ok, _ = database.review_modification_request(1, decision, "", actor_id=1)
    assert not ok
    with sqlite3.connect(db) as conn:
        assert list(conn.iterdump()) == before


@pytest.mark.parametrize("decision", ["Accept", "Reject", "مقبول", "مرفوض"])
def test_valid_review_and_replay(sign_in, db, decision):
    sign_in()
    rid = request(clause_id="1", section="Accountability")
    sign_in("hr")
    assert database.review_modification_request(rid, decision, "ملاحظات", actor_id=1)[0]
    assert not database.review_modification_request(rid, "Reject", "", actor_id=1)[0]
    with sqlite3.connect(db) as conn:
        actor, notes = conn.execute("SELECT changed_by,notes FROM jd_audit_trail").fetchone()
        assert actor == "مستخدم 1" and "actor_id=1" in notes
    if decision in ("Accept", "مقبول"):
        assert database.get_accountabilities(1)[0]["description"] == "نص مقترح ' آمن"
        assert database.get_jd_by_id(1)["version"] == 2
        assert database.get_jd_by_id(1)["status"] == "قيد المراجعة"


def test_valid_approval_is_attributed_from_session(sign_in, db):
    sign_in()
    assert database.approve_jd_as_is(1, actor_id=2)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT changed_by FROM jd_audit_trail").fetchone()[0] == "مستخدم 2"


def test_revocation_and_expiry_prevent_writes(sign_in, db, session, monkeypatch):
    sign_in()
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET password='revoked' WHERE id=2")
    with pytest.raises(PermissionError):
        database.approve_jd_as_is(1, actor_id=2)
    assert not session.get("logged_in")


def test_unauthenticated_mutations_are_denied(session):
    for action in (lambda: request(), lambda: database.approve_jd_as_is(1, actor_id=2),
                   lambda: database.review_modification_request(1, "Reject", "", actor_id=1),
                   lambda: database.create_or_update_jd({}, "x.docx", actor_id=1),
                   lambda: database.update_interview_status(1, "done", actor_id=1)):
        with pytest.raises(PermissionError):
            action()


@pytest.mark.parametrize("username,actor_id", [("manager", 2), ("staff", 3)])
def test_admin_only_actions_are_denied(sign_in, username, actor_id):
    sign_in(username)
    for action in (lambda: database.create_or_update_jd({}, "x.docx", actor_id=actor_id),
                   lambda: database.update_interview_status(1, "done", actor_id=actor_id)):
        with pytest.raises(PermissionError):
            action()


def test_expired_session_cannot_write(sign_in, session, monkeypatch):
    sign_in()
    monkeypatch.setattr(auth.time, "time", lambda: session['_auth_last_seen'] + auth.IDLE_SECONDS + 1)
    with pytest.raises(PermissionError):
        database.approve_jd_as_is(1, actor_id=2)


def test_role_and_assignment_are_reloaded_on_every_action(sign_in, db):
    sign_in("hr")
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET role='employee',assigned_jd_id=2 WHERE id=1")
    with pytest.raises(PermissionError):
        database.review_modification_request(1, "Reject", "", actor_id=1)
    with pytest.raises(PermissionError):
        database.approve_jd_as_is(1, actor_id=1)


def test_stale_review_and_invalid_decision_preserve_pending_request(sign_in, db):
    sign_in()
    rid = request()
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE job_descriptions SET purpose='newer content' WHERE id=1")
        before = list(conn.iterdump())
    sign_in("hr")
    assert not database.review_modification_request(rid, "Accept", "", actor_id=1)[0]
    assert not database.review_modification_request(rid, "anything", "", actor_id=1)[0]
    with sqlite3.connect(db) as conn:
        assert list(conn.iterdump()) == before


def test_unknown_target_and_missing_card_do_not_create_audit(sign_in, db):
    sign_in("hr")
    with pytest.raises(ValueError):
        request(actor_id=1, section="purpose; DROP TABLE users")
    with pytest.raises(ValueError):
        database.approve_jd_as_is(999, actor_id=1)
    assert database.get_audit_trail() == []


def test_review_failure_rolls_back_status_content_and_audit(sign_in, db):
    sign_in()
    rid = request()
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON jd_audit_trail BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        before = list(conn.iterdump())
    sign_in("hr")
    with pytest.raises(sqlite3.IntegrityError, match="synthetic failure"):
        database.review_modification_request(rid, "Accept", "", actor_id=1)
    with sqlite3.connect(db) as conn:
        assert list(conn.iterdump()) == before
