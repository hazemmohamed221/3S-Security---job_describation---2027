"""Synthetic Stage 2 governance, migration, concurrency and preservation regressions."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import threading

import pytest

import database
import governance


def propose(section='Job Purpose', clause='purpose', text='هدف جديد'):
    old = database.get_accountabilities(1)[0]['description'] if section == 'Accountability' else database.get_jd_by_id(1)[clause]
    return database.submit_modification_request(1, section, clause, old, text, 'سبب موثق', actor_id=2)


def dump(path):
    with closing(sqlite3.connect(path)) as conn:
        return list(conn.iterdump())


@pytest.mark.parametrize('field', governance.CONTENT_FIELDS)
def test_every_metadata_mutation_versions_parent_and_invalidates_approval(sign_in, db, field):
    sign_in()
    database.approve_jd_as_is(1, actor_id=2)
    with sqlite3.connect(db) as conn:
        conn.execute(f'UPDATE job_descriptions SET {field}=? WHERE id=1', ('قيمة جديدة',))
    card = database.get_jd_by_id(1)
    assert (card['version'], card['status'], card['review_hash']) == (2, 'قيد المراجعة', None)
    assert database.get_approval_metadata(1) is None
    with pytest.raises(ValueError):
        database.approve_jd_as_is(1, actor_id=2)


@pytest.mark.parametrize('statement', [
    "UPDATE accountabilities SET description='نص جديد' WHERE id=1",
    "UPDATE accountabilities SET kpi='99%' WHERE id=1",
    'UPDATE accountabilities SET item_order=7 WHERE id=1',
    'UPDATE accountabilities SET is_active=0 WHERE id=1',
    "INSERT INTO accountabilities(jd_id,item_order,description) VALUES(1,2,'إضافة')",
    'DELETE FROM accountabilities WHERE id=1',
])
def test_all_responsibility_mutations_version_parent(db, statement):
    with sqlite3.connect(db) as conn:
        conn.execute(statement)
    assert database.get_jd_by_id(1)['version'] == 2
    assert database.get_jd_by_id(2)['version'] == 1


def test_noop_content_updates_do_not_increment_version(db):
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE job_descriptions SET purpose=purpose WHERE id=1')
        conn.execute('UPDATE accountabilities SET description=description,kpi=kpi WHERE id=1')
    assert database.get_jd_by_id(1)['version'] == 1


@pytest.mark.parametrize('kind', ['unrelated_field', 'kpi', 'aba'])
def test_whole_card_conflict_even_if_target_text_unchanged(sign_in, db, kind):
    sign_in()
    rid = propose()
    with sqlite3.connect(db) as conn:
        if kind == 'unrelated_field':
            conn.execute("UPDATE job_descriptions SET competencies='جدارات جديدة' WHERE id=1")
        elif kind == 'kpi':
            conn.execute("UPDATE accountabilities SET kpi='100%' WHERE id=1")
        else:
            conn.execute("UPDATE job_descriptions SET purpose='مؤقت' WHERE id=1")
            conn.execute("UPDATE job_descriptions SET purpose='هدف أصلي' WHERE id=1")
    before = dump(db)
    sign_in('hr')
    assert not database.review_modification_request(rid, 'Accept', '', actor_id=1)[0]
    assert dump(db) == before


@pytest.mark.parametrize('decision', ['Accept', 'Reject'])
def test_decision_evidence_exact_immutable_and_survives_future_edits(sign_in, db, decision):
    sign_in()
    rid = propose('Competencies', 'competencies', 'سلوكية: تعاون\nفنية: تحليل')
    sign_in('hr')
    with closing(database.get_connection()) as conn:
        before = governance.snapshot(conn, 1)
    assert database.review_modification_request(rid, decision, 'قرار', actor_id=1)[0]
    evidence = database.get_decision_evidence(1)[0]
    assert evidence['snapshot_json'] == before
    assert evidence['actor_id'] == 1 and evidence['card_version'] == 1
    assert evidence['result_json']['card']['version'] == (2 if decision == 'Accept' else 1)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE job_descriptions SET hazards='تغيير لاحق' WHERE id=1")
        for statement in ('UPDATE jd_audit_trail SET snapshot_json=NULL', 'DELETE FROM jd_audit_trail',
                          "UPDATE modification_requests SET status='قيد الانتظار'", 'DELETE FROM modification_requests'):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(statement)
    assert database.get_decision_evidence(1)[0] == evidence


def test_hash_verification_detects_tampering_even_if_owner_drops_guard(sign_in, db):
    sign_in()
    database.approve_jd_as_is(1, actor_id=2)
    with sqlite3.connect(db) as conn:
        conn.execute('DROP TRIGGER stage2_audit_no_update')
        conn.execute("UPDATE jd_audit_trail SET snapshot_json='{}'")
    with pytest.raises(ValueError):
        database.get_decision_evidence(1)


def test_legacy_unbound_request_requires_resubmission_for_acceptance(sign_in, db):
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO modification_requests(jd_id,section_name,original_text,proposed_text,justification,requested_by) VALUES(1,'Job Purpose','هدف أصلي','جديد','سبب','قديم')")
    sign_in('hr')
    before = dump(db)
    assert not database.review_modification_request(1, 'Accept', '', actor_id=1)[0]
    assert dump(db) == before
    assert database.review_modification_request(1, 'Reject', 'إعادة تقديم', actor_id=1)[0]


def test_full_card_workflow_reject_resubmit_approve_and_replay(sign_in, db):
    sign_in('hr')
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO job_descriptions(id,title,status) VALUES(3,'مسودة','Draft')")
    with pytest.raises(ValueError):
        database.approve_jd_as_is(3, actor_id=1)
    database.request_jd_review(3, actor_id=1)
    with pytest.raises(ValueError):
        database.request_jd_review(3, actor_id=1)
    database.decide_jd_review(3, 'Rejected', actor_id=1)
    with pytest.raises(ValueError):
        database.approve_jd_as_is(3, actor_id=1)
    database.request_jd_review(3, actor_id=1)
    assert database.approve_jd_as_is(3, actor_id=1)
    before = dump(db)
    with pytest.raises(ValueError):
        database.approve_jd_as_is(3, actor_id=1)
    assert dump(db) == before
    assert len(database.get_decision_evidence(3)) == 2


def test_invalid_domain_states_blocked_by_database(db):
    with sqlite3.connect(db) as conn:
        for status in ('Draft', 'bogus'):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute('UPDATE job_descriptions SET status=? WHERE id=1', (status,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute('UPDATE job_descriptions SET version=0 WHERE id=1')
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute('UPDATE accountabilities SET jd_id=2 WHERE id=1')


def test_stale_full_card_request_and_display_token_cannot_approve(sign_in, db):
    sign_in()
    card = database.get_jd_by_id(1)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE accountabilities SET kpi='جديد' WHERE id=1")
    with pytest.raises(ValueError):
        database.approve_jd_as_is(1, actor_id=2)
    database.request_jd_review(1, actor_id=2)
    with pytest.raises(ValueError):
        database.approve_jd_as_is(1, actor_id=2, expected_version=card['version'], expected_hash=card['review_hash'])
    assert database.approve_jd_as_is(1, actor_id=2)


def test_final_approval_audit_failure_rolls_back_decision(sign_in, db):
    sign_in()
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TRIGGER fail_evidence BEFORE INSERT ON jd_audit_trail BEGIN SELECT RAISE(ABORT,'evidence failure'); END")
    before = dump(db)
    with pytest.raises(sqlite3.IntegrityError):
        database.approve_jd_as_is(1, actor_id=2)
    assert dump(db) == before


def test_competing_reviewers_create_exactly_one_decision(sign_in, monkeypatch, db):
    sign_in()
    rid = propose()
    sign_in('hr')
    # Auth is already covered by the role tests; use a thread-safe synthetic actor.
    import auth
    monkeypatch.setattr(auth, 'require_actor', lambda actor_id: {'id': 1})
    gate = threading.Barrier(2)
    def review(decision):
        gate.wait(timeout=5)
        return database.review_modification_request(rid, decision, '', actor_id=1)[0]
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(review, 'Accept')
        second = pool.submit(review, 'Reject')
        results = [first.result(timeout=10), second.result(timeout=10)]
    assert sorted(results) == [False, True]
    assert len(database.get_decision_evidence(1)) == 1


@pytest.mark.parametrize('status,notes', [(None, None), ('', ''), ('  ', '  '), ('مؤجلة', None)])
def test_interview_partial_edits_preserve_notes_and_outcomes(sign_in, db, status, notes):
    sign_in('hr')
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO interview_schedule(id,department,manager_name,status,notes,discussion_topics) VALUES(1,'إدارة','مدير','مكتملة','مخرجات وملاحظات المرشح','نقاش محفوظ')")
    database.update_interview_status(1, status, notes, actor_id=1)
    saved = database.get_interview_schedule()[0]
    assert saved['notes'] == 'مخرجات وملاحظات المرشح'
    assert saved['discussion_topics'] == 'نقاش محفوظ'
    assert saved['status'] == ('مؤجلة' if status == 'مؤجلة' else 'مكتملة')


def test_interview_stale_edit_and_explicit_clear(sign_in, db):
    sign_in('hr')
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO interview_schedule(id,department,manager_name,status,notes) VALUES(1,'إدارة','مدير','مكتملة','قديم')")
    baseline = database.get_interview_schedule()[0]
    database.update_interview_status(1, notes='مخرجات أحدث', actor_id=1)
    before = dump(db)
    with pytest.raises(ValueError):
        database.update_interview_status(1, 'قيد المراجعة', 'قديم', actor_id=1, expected=baseline)
    assert dump(db) == before
    database.update_interview_status(1, actor_id=1, clear_notes=True)
    assert database.get_interview_schedule()[0]['notes'] == ''


def test_additive_migration_preserves_all_legacy_rows_and_is_idempotent(tmp_path):
    path = tmp_path / 'legacy.db'
    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
        with conn:
            conn.execute("INSERT INTO job_descriptions(id,title,version) VALUES(26,'العربية',8)")
            conn.execute("INSERT INTO accountabilities(id,jd_id,item_order,description) VALUES(399,26,1,'مسؤولية')")
            conn.execute("INSERT INTO interview_schedule(id,department,manager_name,notes) VALUES(9,'إدارة','مدير','مخرجات')")
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        original = {t: ([r[1] for r in conn.execute(f'PRAGMA table_info({t})')],
                        [tuple(r) for r in conn.execute(f'SELECT * FROM {t} ORDER BY rowid')]) for t in tables}
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            governance.migrate(conn)
        for table, (columns, rows) in original.items():
            assert [tuple(r) for r in conn.execute(f'SELECT {",".join(columns)} FROM {table} ORDER BY rowid')] == rows
        first = list(conn.iterdump())
        with conn:
            governance.migrate(conn)
        assert list(conn.iterdump()) == first


def test_migration_rolls_back_ddl_on_failure(tmp_path):
    path = tmp_path / 'legacy.db'
    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
        # Authorizer simulates a failure midway through additive DDL.
        calls = 0
        def authorizer(action, *args):
            nonlocal calls
            if action == sqlite3.SQLITE_ALTER_TABLE:
                calls += 1
                if calls == 3:
                    return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        before = list(conn.iterdump())
        conn.set_authorizer(authorizer)
        with pytest.raises(sqlite3.DatabaseError):
            with conn:
                conn.execute('BEGIN IMMEDIATE')
                governance.migrate(conn)
        conn.set_authorizer(None)
        assert list(conn.iterdump()) == before


def test_migration_command_backs_up_preserves_and_rehearses_without_source_writes(db, tmp_path):
    from scripts.migrate_integrity import migrate_integrity
    from scripts.verify_stage2_migration import verify
    before = dump(db)
    assert verify(db, tmp_path) == {'job_descriptions': 2, 'accountabilities': 2, 'interview_schedule': 0}
    assert dump(db) == before
    counts, backup = migrate_integrity(db, tmp_path / 'backups')
    assert counts['job_descriptions'] == 2
    assert dump(backup) == before and dump(db) == before


def test_migration_command_backup_failure_prevents_writes(db, monkeypatch):
    from scripts import migrate_integrity
    def fail(*args):
        raise OSError('synthetic disk full')
    monkeypatch.setattr(migrate_integrity, 'backup_database', fail)
    before = dump(db)
    with pytest.raises(OSError):
        migrate_integrity.migrate_integrity(db)
    assert dump(db) == before
