"""Connection durability, active FK enforcement and status domain tests."""
from contextlib import closing
import sqlite3

import pytest

import database
from statuses import CardStatus, ReviewStatus, InterviewStatus, ALIASES


def test_every_factory_connection_has_required_pragmas(db):
    for _ in range(3):
        with closing(database.get_connection()) as conn:
            assert conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1
            assert conn.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
            assert conn.execute('PRAGMA synchronous').fetchone()[0] == 1


def test_wal_reader_snapshot_does_not_block_writer(db):
    with closing(database.get_connection()) as reader, closing(database.get_connection()) as writer:
        reader.execute('BEGIN')
        original = reader.execute('SELECT purpose FROM job_descriptions WHERE id=1').fetchone()[0]
        with writer:
            writer.execute("UPDATE job_descriptions SET purpose='كتابة متزامنة' WHERE id=1")
        assert reader.execute('SELECT purpose FROM job_descriptions WHERE id=1').fetchone()[0] == original
        reader.commit()
        assert reader.execute('SELECT purpose FROM job_descriptions WHERE id=1').fetchone()[0] == 'كتابة متزامنة'


@pytest.mark.parametrize('statement', [
    "INSERT INTO accountabilities(jd_id,item_order,description) VALUES(999,1,'أصل غير موجود')",
    "INSERT INTO modification_requests(jd_id,section_name,proposed_text,justification,requested_by) VALUES(999,'Job Purpose','جديد','سبب','مستخدم')",
    "INSERT INTO jd_audit_trail(jd_id,action,changed_by) VALUES(999,'قرار','مستخدم')",
])
def test_orphan_inserts_raise_foreign_key_errors_and_rollback(db, statement):
    with closing(database.get_connection()) as conn:
        with pytest.raises(sqlite3.IntegrityError, match='FOREIGN KEY'):
            with conn:
                conn.execute("UPDATE job_descriptions SET purpose='يجب التراجع' WHERE id=1")
                conn.execute(statement)
        assert conn.execute('SELECT purpose,version FROM job_descriptions WHERE id=1').fetchone()[:] == ('هدف أصلي', 1)
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()


def test_failed_pragma_initialization_closes_connection(monkeypatch):
    class Connection:
        closed = False
        def execute(self, sql):
            if 'journal_mode' in sql:
                raise sqlite3.OperationalError('synthetic WAL failure')
        def close(self):
            self.closed = True
    conn = Connection()
    monkeypatch.setattr(database.sqlite3, 'connect', lambda path: conn)
    with pytest.raises(sqlite3.OperationalError):
        database.get_connection()
    assert conn.closed


@pytest.mark.parametrize('domain', [CardStatus, ReviewStatus, InterviewStatus])
def test_status_enum_aliases_and_unknown_values(domain):
    for alias, canonical in ALIASES[domain].items():
        assert domain.parse(alias) is canonical
        assert domain.parse(canonical.value) is canonical
    for invalid in ('unknown', '<script>', None, 0):
        with pytest.raises(ValueError):
            domain.parse(invalid)


@pytest.mark.parametrize('table,statement', [
    ('job_descriptions', "INSERT INTO job_descriptions(title,status) VALUES('اختبار',?)"),
    ('modification_requests', "INSERT INTO modification_requests(jd_id,section_name,proposed_text,justification,requested_by,status) VALUES(1,'Job Purpose','نص','سبب','مستخدم',?)"),
    ('interview_schedule', "INSERT INTO interview_schedule(department,manager_name,status) VALUES('إدارة','مدير',?)"),
])
def test_status_domains_enforced_at_sql_boundary(db, table, statement):
    with closing(database.get_connection()) as conn:
        for invalid in ('invalid', None):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(statement, (invalid,))


def test_interview_alias_writes_canonical_and_invalid_status_is_atomic(sign_in, db):
    sign_in('hr')
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO interview_schedule(id,department,manager_name,status,notes) VALUES(1,'إدارة','مدير','Completed','مخرجات')")
    assert database.get_interview_schedule()[0]['status'] == InterviewStatus.COMPLETED
    database.update_interview_status(1, InterviewStatus.POSTPONED, actor_id=1)
    with pytest.raises(ValueError):
        database.update_interview_status(1, 'invalid', 'حذف غير مسموح', actor_id=1)
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT status,notes FROM interview_schedule').fetchone() == ('مؤجلة', 'مخرجات')


def test_legacy_completed_review_displays_canonically_without_rewriting_history(db):
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO modification_requests(jd_id,section_name,proposed_text,justification,requested_by,status) VALUES(1,'Job Purpose','نص','سبب','قديم','Accepted')")
    assert database.get_requests_by_user('قديم')[0]['status'] == ReviewStatus.ACCEPTED
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT status FROM modification_requests').fetchone()[0] == 'Accepted'


def test_dashboard_counts_only_pending_review_cards(db):
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO job_descriptions(title,status) VALUES('مسودة','Draft')")
        conn.execute("INSERT INTO job_descriptions(title,status) VALUES('مرفوضة','Rejected')")
    stats = database.get_dashboard_stats()
    assert stats['total_jds'] == 4 and stats['under_review'] == 2
