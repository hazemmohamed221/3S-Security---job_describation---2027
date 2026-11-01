"""Revision-bound SQLite governance; additive migration preserves legacy values."""
import hashlib
import json
from statuses import CardStatus, ALIASES, install_constraints

CONTENT_FIELDS = (
    'job_code', 'title', 'department', 'sector', 'reports_to', 'purpose',
    'dimensions', 'frameworks', 'qualifications', 'competencies', 'hazards',
    'safe_practices', 'internal_relations', 'external_relations', 'approvals',
    'source_file',
)
STATUS_ALIASES = {key: status.value for key, status in ALIASES[CardStatus].items()}


def canonical_status(value):
    return CardStatus.parse(value).value


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def snapshot(conn, jd_id):
    card = dict(conn.execute('SELECT * FROM job_descriptions WHERE id=?', (jd_id,)).fetchone())
    # Workflow evidence is excluded from the content fingerprint.
    card = {k: card[k] for k in ('id', *CONTENT_FIELDS, 'version', 'status')}
    rows = [dict(r) for r in conn.execute(
        'SELECT * FROM accountabilities WHERE jd_id=? ORDER BY item_order,id', (jd_id,))]
    return {'card': card, 'accountabilities': rows}


def content_hash(state):
    card = {k: v for k, v in state['card'].items() if k not in ('status', 'version')}
    return digest(encode({'card': card, 'accountabilities': state['accountabilities']}))


def bind_review(conn, jd_id):
    state = snapshot(conn, jd_id)
    conn.execute('UPDATE job_descriptions SET review_version=?,review_hash=? WHERE id=?',
                 (state['card']['version'], content_hash(state), jd_id))


def migrate(conn):
    """Run inside a transaction, after the startup backup and base schema creation.

    No business value or historical evidence is rewritten. Legacy pending requests
    have no provable base revision and must be rejected/resubmitted to be accepted.
    """
    additions = {
        'job_descriptions': {'review_version': 'INTEGER', 'review_hash': 'TEXT', 'import_hash': 'TEXT'},
        'modification_requests': {
            'expected_version': 'INTEGER', 'expected_hash': 'TEXT', 'requested_snapshot': 'TEXT',
        },
        'jd_audit_trail': {
            'actor_id': 'INTEGER', 'card_version': 'INTEGER', 'decision': 'TEXT',
            'snapshot_json': 'TEXT', 'snapshot_hash': 'TEXT',
            'result_json': 'TEXT', 'result_hash': 'TEXT',
        },
    }
    new_review_columns = False
    for table, columns in additions.items():
        existing = {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
        for name, kind in columns.items():
            if name not in existing:
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')
                new_review_columns |= table == 'job_descriptions' and name == 'review_hash'

    def trigger(name, timing, body):
        conn.execute(f'CREATE TRIGGER IF NOT EXISTS {name} {timing} BEGIN {body} END')

    dirty = ' OR '.join(f'NEW.{f} IS NOT OLD.{f}' for f in CONTENT_FIELDS)
    trigger('stage2_card_revision',
            f'AFTER UPDATE OF {",".join(CONTENT_FIELDS)} ON job_descriptions WHEN {dirty}',
            "UPDATE job_descriptions SET version=OLD.version+1,status='قيد المراجعة',"
            "review_version=NULL,review_hash=NULL,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=NEW.id;")
    trigger('stage2_version_guard', 'BEFORE UPDATE OF version ON job_descriptions WHEN NEW.version < OLD.version',
            "SELECT RAISE(ABORT,'Revision cannot decrease');")
    for event, ref, condition in (
        ('INSERT', 'NEW', ''), ('DELETE', 'OLD', ''),
        ('UPDATE', 'NEW', ' WHEN ' + ' OR '.join(
            f'NEW.{f} IS NOT OLD.{f}' for f in ('description', 'kpi', 'item_order', 'is_active'))),
    ):
        trigger(f'stage2_child_{event.lower()}', f'AFTER {event} ON accountabilities{condition}',
                "UPDATE job_descriptions SET version=version+1,status='قيد المراجعة',review_version=NULL,review_hash=NULL,"
                f"updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id={ref}.jd_id;")
    trigger('stage2_child_parent_lock', 'BEFORE UPDATE OF jd_id ON accountabilities WHEN NEW.jd_id IS NOT OLD.jd_id',
            "SELECT RAISE(ABORT,'Responsibility parent is immutable');")
    # Keep legacy aliases readable, while all service transitions write Arabic.
    case = 'CASE {ref}.status ' + ' '.join(
        f"WHEN '{alias}' THEN '{status}'" for alias, status in STATUS_ALIASES.items()) + ' END'
    old, new = case.format(ref='OLD'), case.format(ref='NEW')
    valid = (f"({old}={new}) OR ({old}='مسودة' AND {new}='قيد المراجعة') OR "
             f"({old}='قيد المراجعة' AND {new} IN ('معتمد','مرفوض')) OR "
             f"({old}='مرفوض' AND {new}='قيد المراجعة') OR "
             f"({old}='معتمد' AND {new}='قيد المراجعة' AND NEW.version>OLD.version)")
    trigger('stage2_status_guard', f'BEFORE UPDATE OF status ON job_descriptions WHEN ({new}) IS NULL OR NOT ({valid})',
            "SELECT RAISE(ABORT,'Invalid document state transition');")
    for operation in ('UPDATE', 'DELETE'):
        trigger(f'stage2_audit_no_{operation.lower()}', f'BEFORE {operation} ON jd_audit_trail',
                "SELECT RAISE(ABORT,'Audit evidence is immutable');")
        trigger(f'stage2_request_no_{operation.lower()}',
                f"BEFORE {operation} ON modification_requests WHEN OLD.status NOT IN ('Pending','قيد الانتظار')",
                "SELECT RAISE(ABORT,'Review decision is immutable');")
    base_fields = ('jd_id', 'section_name', 'clause_id', 'original_text', 'proposed_text',
                   'justification', 'requested_by', 'requested_at', 'expected_version', 'expected_hash', 'requested_snapshot')
    trigger('stage2_request_base_lock', 'BEFORE UPDATE ON modification_requests WHEN ' +
            ' OR '.join(f'NEW.{f} IS NOT OLD.{f}' for f in base_fields),
            "SELECT RAISE(ABORT,'Review request base is immutable');")
    trigger('stage2_request_status_guard',
            "BEFORE UPDATE OF status ON modification_requests WHEN NEW.status NOT IN ('مقبول','مرفوض')",
            "SELECT RAISE(ABORT,'Invalid review decision');")
    if new_review_columns:
        for row in conn.execute('SELECT id,status FROM job_descriptions').fetchall():
            if STATUS_ALIASES.get(row['status']) == 'قيد المراجعة':
                bind_review(conn, row['id'])
    install_constraints(conn)
