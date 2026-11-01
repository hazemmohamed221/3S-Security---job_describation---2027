"""
Database module for 3S Security Job Description Management System.
Handles SQLite connection, schema definition, seed data, and CRUD operations in Arabic.
"""

import sqlite3
import os
import sys
import glob
import re
from datetime import datetime, timezone
from contextlib import closing, contextmanager
from backups import backup_before_startup
import openpyxl
from docx_parser import parse_jd_docx
import governance
from statuses import CardStatus, ReviewStatus, InterviewStatus, display_status
from upload_security import sanitize_docx_filename

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None, **_kwargs):
        if dotenv_path and os.path.exists(dotenv_path):
            try:
                with open(dotenv_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
            except OSError:
                pass
        return False

# Try importing psycopg2 for Supabase / PostgreSQL support
try:
    import psycopg2
    from psycopg2.extras import DictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    HAS_PSYCOPG2 = False
    DictCursor = None

# Load .env if present
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def get_database_url():
    """Retrieve DATABASE_URL from environment or streamlit secrets."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
                url = st.secrets["DATABASE_URL"]
        except Exception:
            pass
    return url.strip() if url and url.strip() else None

DB_PATH = os.environ.get("JD_DB_PATH", os.path.join(os.path.dirname(__file__), "job_descriptions.db"))

TITLE_MAP = {
    'Commercial Director': 'المدير التجاري',
    'CUSTUMER SERVISE MANAGER': 'مدير خدمة العملاء',
    'Installation Manager': 'مدير التركيبات',
    'MARKETTING MANAGER': 'مدير التسويق',
    'QUALITY ASSURANCE MANAGER': 'مدير توكيد الجودة',
    'Accounts Receivable Head': 'رئيس قسم حسابات العملاء والتحصيل',
    'ACCOUNTING MANAGER': 'مدير الحسابات العامة',
    'Administrative & Personnel Affairs Manager': 'مدير الشئون الإدارية وشئون العاملين',
    'AUDIT MANAGER': 'مدير المراجعة الداخلية والتفتيش',
    'Business Development manager': 'مدير تطوير الأعمال',
    'Collection Officer': 'مسؤول التحصيل',
    'CRM  MANAGER': 'مدير إدارة علاقات العملاء (CRM)',
    'Company Advisor for Government Affairs': 'مستشار الشركة للعلاقات الحكومية والتراخيص',
    'HR Manager': 'مدير الموارد البشرية',
    'Managing Director': 'العضو المنتدب والمدير التنفيذي',
    'Public Relations Manager': 'مدير العلاقات العامة',
    'Projects  Manager': 'مدير إدارة المشروعات',
    'QUALITY CONTROL MANAGER': 'مدير مراقبة الجودة',
    'SALES MANAGER': 'مدير عام المبيعات',
    'TECHNICAL SUPPORT MANAGER': 'مدير الدعم الفني',
    'Technical Support Manager': 'مدير الدعم الفني',
    'WAREHOUSE HEAD': 'أمين عام المخازن / مدير المخازن',
    'MAINTENANCE MANAGER': 'مدير الصيانة',
    'PROCURMENT MANAGER': 'مدير المشتريات وسلاسل الإمداد',
    'TECHNICALOFFICE MANAGER': 'مدير المكتب الفني',
    'CHIEF FINANCIAL OFFICER (CFO)': 'المدير المالي التنفيذي (CFO)',
    'finanace team': 'دليل مهام واختصاصات الإدارة المالية'
}

DEPT_MAP = {
    'COMMERCIAL DEPARTMENT': 'الإدارة التجارية',
    'QUALITY ASSURANCE': 'إدارة توكيد الجودة',
    'QUALITY': 'إدارة الجودة',
    'ACCOUNTING': 'إدارة حسابات العملاء',
    'ACCOUNTING DEPARTMENT': 'إدارة الحسابات العامة',
    'AUDITING DEPARTMENT': 'إدارة المراجعة والتفتيش',
    'FINANCE': 'الإدارة المالية',
    'HR': 'إدارة الموارد البشرية',
    'Hr': 'إدارة الموارد البشرية',
    'MAINTENANCE': 'إدارة الصيانة',
    'MARKETTING DEPARTMENT': 'إدارة التسويق',
    'PROCURMENT': 'إدارة المشتريات وسلاسل الإمداد',
    'Projects': 'إدارة المشروعات',
    'TECHNICAL MANAGER': 'إدارة المكتب الفني',
    'TOP Managemant': 'الإدارة العليا والتنفيذية',
    'Technical Support': 'إدارة الدعم الفني والتركيبات',
    'Top Management': 'الإدارة العليا',
    'WAREHOUSE': 'إدارة المخازن',
    'الادارة العامة': 'الإدارة العامة',
    '': 'الإدارة العامة'
}

REPORTS_MAP = {
    'Top Management': 'مجلس الإدارة / الإدارة العليا',
    'MANAGING DIRECTOR': 'العضو المنتدب والمدير التنفيذي',
    'Managing Director': 'العضو المنتدب والمدير التنفيذي',
    'Managing director': 'العضو المنتدب والمدير التنفيذي',
    'COMMERCIAL DIRECTOR': 'المدير التجاري',
    'COMMERCIAL MANAGER': 'المدير التجاري',
    'CFO': 'المدير المالي التنفيذي',
    'ACCOUNT MANAGER': 'مدير الحسابات',
    'PLANT MANAGER': 'مدير العمليات والتشغيل',
    'SUPPLY CHAIN MANAGER': 'مدير سلاسل الإمداد',
    'Technical Support Manager': 'مدير الدعم الفني',
    '': 'الإدارة العليا'
}


def translate_dimensions(dim_str):
    if not dim_str:
        return 'النطاق الإشرافي المعتمد للإدارة'
    t = dim_str
    t = re.sub(r'Number of Staff Supervised:\s*\|\s*Direct Reports:\s*\|\s*', 'المرؤوسين المباشرين: ', t)
    t = re.sub(r'Number of Staff Supervised:\s*\|\s*Total:\s*\|\s*', 'إجمالي فريق العمل الخاضع للإشراف: ', t)
    t = re.sub(r'Number of Staff Supervised:\s*\|\s*Direct Reports:\s*', 'المرؤوسين المباشرين: لا يوجد مرؤوسين مباشرين', t)
    t = re.sub(r'Number of Staff Supervised:\s*\|\s*Total:\s*', 'إجمالي فريق العمل: —', t)
    t = t.replace('Number of Staff Supervised:', 'عدد الموظفين الخاضعين للإشراف:')
    t = t.replace('Direct Reports:', 'المرؤوسين المباشرين:')
    t = t.replace('Total:', 'الإجمالي:')
    return t


def translate_qualifications(qual_str):
    if not qual_str:
        return ''
    t = qual_str
    t = t.replace('Qualifications :', 'المؤهل العلمي والدراسي:')
    t = t.replace('Qualifications:', 'المؤهل العلمي والدراسي:')
    t = t.replace('Experience     :', 'سنوات الخبرة العملية:')
    t = t.replace('Experience :', 'سنوات الخبرة العملية:')
    t = t.replace('Experience:', 'سنوات الخبرة العملية:')
    t = t.replace('Skills               :', 'المهارات واللغات:')
    t = t.replace('Skills               ', 'المهارات واللغات:')
    t = t.replace('Skills :', 'المهارات واللغات:')
    t = t.replace('Skills:', 'المهارات واللغات:')
    t = t.replace('Excellent English language skills', 'إتقان تام للغة الإنجليزية')
    t = t.replace('Excellent Computer skills', 'إتقان ممتاز لبرامج وتطبيقات الحاسب الآلي')
    t = t.replace('Very good in English', 'مستوى جيد جداً في اللغة الإنجليزية')
    t = t.replace('Good Computer skills', 'إجادة برامج وتطبيقات الحاسب الآلي')
    t = t.replace('Good English language skills', 'إجادة جيدة للغة الإنجليزية')
    return t


class PostgresCursorAdapter:
    """Adapts psycopg2 cursor to mirror sqlite3 cursor semantics."""
    def __init__(self, cursor, conn_adapter):
        self._cur = cursor
        self._conn = conn_adapter
        self.lastrowid = None

    def execute(self, sql, params=None):
        sql_pg = sql
        # Normalize SQLite placeholder syntax to PostgreSQL
        if '?' in sql_pg:
            sql_pg = sql_pg.replace('?', '%s')

        # Auto-append RETURNING id for INSERT queries if not already present
        sql_trimmed = sql_pg.strip()
        is_insert = sql_trimmed.upper().startswith("INSERT INTO ")
        has_returning = " RETURNING " in sql_trimmed.upper()

        if is_insert and not has_returning:
            # Check if target table has an id serial primary key
            sql_pg = sql_pg.rstrip().rstrip(';') + " RETURNING id;"
            self._cur.execute(sql_pg, params)
            try:
                ret = self._cur.fetchone()
                if ret:
                    self.lastrowid = ret[0]
            except Exception:
                self.lastrowid = None
        else:
            self._cur.execute(sql_pg, params)

        return self

    def executemany(self, sql, seq_of_params):
        if '?' in sql:
            sql = sql.replace('?', '%s')
        self._cur.executemany(sql, seq_of_params)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size) if size is not None else self._cur.fetchmany()

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()

    def __iter__(self):
        return iter(self._cur)


class PostgresConnectionAdapter:
    """Adapts a psycopg2 connection to mirror sqlite3 connection semantics."""
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return PostgresCursorAdapter(self._conn.cursor(cursor_factory=DictCursor), self)

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    @property
    def closed(self):
        return bool(self._conn.closed)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()


def get_connection():
    """Returns a connection to either Supabase PostgreSQL (if DATABASE_URL is set and not running in pytest) or local SQLite."""
    # When running tests (pytest loaded or custom DB_PATH), use SQLite.
    is_testing = "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("JD_DB_PATH") or DB_PATH != os.path.join(os.path.dirname(__file__), "job_descriptions.db")

    pg_url = get_database_url() if not is_testing else None
    if pg_url and HAS_PSYCOPG2:
        try:
            raw_conn = psycopg2.connect(
                pg_url,
                connect_timeout=15,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            return PostgresConnectionAdapter(raw_conn)
        except Exception:
            # If PostgreSQL connection fails, fallback to SQLite
            pass

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        conn.execute("PRAGMA synchronous=NORMAL")
        if mode != 'wal':
            raise RuntimeError('The portal requires a file-backed SQLite database with WAL support.')
        conn.row_factory = sqlite3.Row
    except BaseException:
        conn.close()
        raise
    return conn


def init_db():
    """Initializes tables and seeds initial data if database is empty."""
    is_testing = "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("JD_DB_PATH") or DB_PATH != os.path.join(os.path.dirname(__file__), "job_descriptions.db")
    pg_url = get_database_url() if not is_testing else None
    if pg_url and HAS_PSYCOPG2:
        # Schema is created and initialized in PostgreSQL
        return

    backup_before_startup(DB_PATH)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT,
        assigned_jd_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS job_descriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_code TEXT,
        title TEXT NOT NULL,
        department TEXT,
        sector TEXT,
        reports_to TEXT,
        purpose TEXT,
        dimensions TEXT,
        frameworks TEXT,
        qualifications TEXT,
        competencies TEXT,
        hazards TEXT,
        safe_practices TEXT,
        internal_relations TEXT,
        external_relations TEXT,
        approvals TEXT,
        source_file TEXT,
        status TEXT DEFAULT 'مسودة',
        version INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS accountabilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jd_id INTEGER NOT NULL,
        item_order INTEGER NOT NULL,
        description TEXT NOT NULL,
        kpi TEXT,
        version INTEGER DEFAULT 1,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (jd_id) REFERENCES job_descriptions (id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS modification_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jd_id INTEGER NOT NULL,
        section_name TEXT NOT NULL,
        clause_id TEXT,
        original_text TEXT,
        proposed_text TEXT NOT NULL,
        justification TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'قيد الانتظار',
        reviewer_comments TEXT,
        reviewed_by TEXT,
        reviewed_at TIMESTAMP,
        FOREIGN KEY (jd_id) REFERENCES job_descriptions (id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS jd_audit_trail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jd_id INTEGER NOT NULL,
        mod_request_id INTEGER,
        section_name TEXT,
        action TEXT NOT NULL,
        old_text TEXT,
        new_text TEXT,
        changed_by TEXT NOT NULL,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (jd_id) REFERENCES job_descriptions (id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS interview_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seq_num INTEGER,
        department TEXT NOT NULL,
        manager_name TEXT NOT NULL,
        day_date TEXT,
        meeting_time TEXT,
        discussion_topics TEXT,
        status TEXT DEFAULT 'قيد المراجعة',
        notes TEXT
    )
    """)

    conn.commit()
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        governance.migrate(conn)
        _migrate_user_management(conn)

    cur.execute("SELECT COUNT(*) as cnt FROM job_descriptions")
    jd_count = cur.fetchone()['cnt']
    if jd_count == 0:
        seed_job_descriptions(conn)
        seed_interview_schedule(conn)

    conn.close()


def _migrate_user_management(conn):
    """Add access controls without changing existing credentials, IDs or roles."""
    columns = {row[1] for row in conn.execute('PRAGMA table_info(users)')}
    if 'is_active' not in columns:
        conn.execute('ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1))')
    if 'auth_version' not in columns:
        conn.execute('ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0 CHECK(auth_version>=0)')


def _insert_parsed_jd(conn, parsed, source_file, changed_by="مسؤول النظام", *, commit=True, notes="تمت الإضافة من ملف Word المعتمد"):
    """Inserts a parsed JD dictionary and its accountabilities into DB with auto Arabic translation."""
    cur = conn.cursor()
    source_file = sanitize_docx_filename(source_file)

    system_export = parsed.get('format_version') == 2
    raw_title = parsed.get('title', 'بطاقة وصف وظيفي جديدة')
    raw_title = raw_title if system_export else raw_title.strip()
    title = raw_title if system_export else TITLE_MAP.get(raw_title, raw_title)

    raw_dept = parsed.get('department', '')
    raw_dept = raw_dept if system_export else raw_dept.strip()
    dept = raw_dept if system_export else DEPT_MAP.get(raw_dept, raw_dept if raw_dept else 'الإدارة العامة')

    raw_rep = parsed.get('reports_to', '')
    raw_rep = raw_rep if system_export else raw_rep.strip()
    reports_to = raw_rep if system_export else REPORTS_MAP.get(raw_rep, raw_rep if raw_rep else 'مجلس الإدارة')

    dimensions = parsed.get('dimensions', '') if system_export else translate_dimensions(parsed.get('dimensions', ''))
    qualifications = parsed.get('qualifications', '') if system_export else translate_qualifications(parsed.get('qualifications', ''))

    cur.execute("""
    INSERT INTO job_descriptions (
        job_code, title, department, sector, reports_to, purpose,
        dimensions, frameworks, qualifications, competencies, hazards,
        safe_practices, internal_relations, external_relations, approvals,
        source_file, status, version, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'قيد المراجعة', 1, CURRENT_TIMESTAMP)
    """, (
        parsed.get('job_code', ''),
        title,
        dept,
        parsed.get('sector', '') if system_export else (parsed.get('sector') or 'الإدارة العامة والمجموعة'),
        reports_to,
        parsed.get('purpose', ''),
        dimensions,
        parsed.get('frameworks', ''),
        qualifications,
        parsed.get('competencies', ''),
        parsed.get('hazards', ''),
        parsed.get('safe_practices', ''),
        parsed.get('internal_relations', ''),
        parsed.get('external_relations', ''),
        parsed.get('approvals', ''),
        source_file
    ))
    jd_id = cur.lastrowid

    for idx, acc in enumerate(parsed.get('accountabilities', [])):
        cur.execute("""
        INSERT INTO accountabilities (jd_id, item_order, description, kpi, version, is_active)
        VALUES (?, ?, ?, ?, 1, 1)
        """, (jd_id, acc.get('item_order', idx + 1), acc.get('description', ''), acc.get('kpi', '')))

    cur.execute("""
    INSERT INTO jd_audit_trail (jd_id, section_name, action, new_text, changed_by, notes)
    VALUES (?, 'كامل الوثيقة', 'إدراج أولي', ?, ?, ?)
    """, (jd_id, f"استيراد الوصف الوظيفي من الملف: {source_file}", changed_by, notes))

    governance.bind_review(conn, jd_id)
    if commit:
        conn.commit()
    return jd_id


def seed_job_descriptions(conn):
    folder = os.path.join(os.path.dirname(__file__), "job describation")
    if not os.path.exists(folder):
        return

    docx_files = glob.glob(os.path.join(folder, "*.docx"))
    for file_path in docx_files:
        try:
            parsed = parse_jd_docx(file_path)
            _insert_parsed_jd(conn, parsed, source_file=os.path.basename(file_path), changed_by="النظام الأساسي")
        except Exception as e:
            print(f"Error seeding {file_path}: {e}")


def seed_interview_schedule(conn):
    excel_candidates = [
        f for f in os.listdir(os.path.dirname(__file__)) if f.endswith('.xlsx')
    ]
    if not excel_candidates:
        return

    excel_path = os.path.join(os.path.dirname(__file__), excel_candidates[0])
    try:
        wb = openpyxl.load_workbook(excel_path)
        if 'جدول المقابلات' in wb.sheetnames:
            ws = wb['جدول المقابلات']
            cur = conn.cursor()
            for row in list(ws.iter_rows(values_only=True))[3:]:
                if row and row[0] is not None and row[1]:
                    seq = row[0]
                    dept = str(row[1]).strip()
                    mgr = str(row[2]).strip() if row[2] else ''
                    day = str(row[3]).strip() if row[3] else ''
                    time_val = str(row[4]).strip() if row[4] else ''
                    topics = str(row[5]).strip() if row[5] else ''
                    status = InterviewStatus.parse(str(row[6]).strip() if row[6] else InterviewStatus.PENDING_REVIEW).value
                    notes = str(row[7]).strip() if row[7] else ''

                    cur.execute("""
                    INSERT INTO interview_schedule (seq_num, department, manager_name, day_date, meeting_time, discussion_topics, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (seq, dept, mgr, day, time_val, topics, status, notes))
            conn.commit()
    except Exception as e:
        print(f"Error seeding interview schedule: {e}")



@contextmanager
def _write_connection():
    """Serialize validation and writes; roll back the whole action on any error."""
    with closing(get_connection()) as conn:
        with conn:
            if isinstance(conn, PostgresConnectionAdapter):
                yield conn
            else:
                conn.execute("BEGIN IMMEDIATE")
                yield conn


def _require_actor(conn, actor_id, *, jd_id=None, admin=False):
    # Import lazily: authentication reads users through this module.
    import auth
    authenticated = auth.require_actor(actor_id)
    actor = conn.execute("SELECT * FROM users WHERE id=?", (authenticated['id'],)).fetchone()
    if not actor or not dict(actor).get('is_active', 1) or actor['role'] not in ('admin', 'manager', 'employee'):
        raise PermissionError("المستخدم غير مخول بإجراء هذا التغيير.")
    if admin and actor['role'] != 'admin':
        raise PermissionError("هذا الإجراء متاح لإدارة الموارد البشرية فقط.")
    if jd_id is not None:
        if actor['role'] != 'admin' and actor['assigned_jd_id'] != jd_id:
            raise PermissionError("لا توجد صلاحية لتعديل أو اعتماد هذه البطاقة.")
        if not conn.execute("SELECT 1 FROM job_descriptions WHERE id=?", (jd_id,)).fetchone():
            raise ValueError("بطاقة الوصف الوظيفي غير موجودة.")
    return dict(actor)


FIELD_MAP = {
    "كود الوظيفة": "job_code", "Job Code": "job_code",
    "الهدف العام من الوظيفة": "purpose", "Job Purpose": "purpose",
    "أبعاد الوظيفة": "dimensions", "Job Dimensions": "dimensions",
    "إطار العمل وحدود اتخاذ القرارات": "frameworks", "Frameworks & Authority": "frameworks",
    "المؤهلات والخبرات والمهارات": "qualifications", "Qualifications & Skills": "qualifications",
    "الجدارات والكفاءات": "competencies", "Competencies": "competencies",
    "مخاطر الوظيفة": "hazards", "Job Hazards": "hazards",
    "ممارسات السلامة والصحة المهنية": "safe_practices", "Safe Practices": "safe_practices",
    "العلاقات الداخلية": "internal_relations", "Internal Relations": "internal_relations",
    "العلاقات الخارجية": "external_relations", "External Relations": "external_relations",
    "المسمى الوظيفي": "title", "Position Title": "title",
    "الإدارة": "department", "Department": "department", "القطاع": "sector", "Sector": "sector",
    "المسؤول المباشر": "reports_to", "Reports To": "reports_to",
}


def _resolve_target(conn, jd_id, section_name, clause_id):
    """Resolve typed targets and parent ownership for both acceptance and rejection."""
    if not isinstance(section_name, str):
        raise ValueError("قسم التعديل غير صالح.")
    if section_name.startswith(("المسؤولية #", "Accountability")):
        if not str(clause_id).isdigit():
            raise ValueError("معرف المسؤولية غير صالح.")
        row = conn.execute("SELECT description FROM accountabilities WHERE id=? AND jd_id=? AND is_active=1",
                           (int(clause_id), jd_id)).fetchone()
        if not row:
            raise ValueError("المسؤولية غير موجودة أو لا تتبع البطاقة المحددة.")
        return "accountability", int(clause_id), row['description'] or ""
    field = FIELD_MAP.get(section_name)
    if field is None or clause_id not in (None, "", section_name, field):
        raise ValueError("قسم التعديل أو معرف البند غير صالح.")
    # Column names come exclusively from the fixed whitelist above.
    row = conn.execute(f"SELECT {field} FROM job_descriptions WHERE id=?", (jd_id,)).fetchone()
    if not row:
        raise ValueError("بطاقة الوصف الوظيفي غير موجودة.")
    return "field", field, row[field] or ""


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_all_jds():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT j.*, 
           (SELECT COUNT(*) FROM accountabilities a WHERE a.jd_id = j.id AND a.is_active = 1) as acc_count,
           (SELECT COUNT(*) FROM modification_requests m WHERE m.jd_id = j.id AND (m.status = 'قيد الانتظار' OR m.status = 'Pending')) as pending_mods
    FROM job_descriptions j
    ORDER BY j.title ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        row['status'] = governance.STATUS_ALIASES.get(row['status'], row['status'])
    conn.close()
    return rows


def get_jd_by_id(jd_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM job_descriptions WHERE id = ?", (jd_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result['status'] = governance.STATUS_ALIASES.get(result['status'], result['status'])
    return result


def get_accountabilities(jd_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT * FROM accountabilities 
    WHERE jd_id = ? AND is_active = 1
    ORDER BY item_order ASC
    """, (jd_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_accountability_by_id(acc_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accountabilities WHERE id = ?", (acc_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_or_update_jd(parsed_jd, source_file, *, actor_id):
    with _write_connection() as conn:
        actor = _require_actor(conn, actor_id, admin=True)
        if parsed_jd.get('format_version') == 2:
            import_hash = governance.digest(governance.encode({
                'fields': {f: parsed_jd.get(f) or '' for f in governance.CONTENT_FIELDS if f != 'source_file'},
                'accountabilities': parsed_jd.get('accountabilities', []),
            }))
            existing = conn.execute('SELECT * FROM job_descriptions WHERE id=?',
                                    (parsed_jd.get('portal_card_id'),)).fetchone()
            existing = conn.execute('SELECT * FROM job_descriptions WHERE import_hash=? ORDER BY id LIMIT 1',
                                    (import_hash,)).fetchone() or existing
            if existing:
                fields_match = all((existing[f] or '') == (parsed_jd.get(f) or '')
                                   for f in governance.CONTENT_FIELDS if f != 'source_file')
                current = [(r['item_order'], r['description'], r['kpi'] or '') for r in conn.execute(
                    'SELECT * FROM accountabilities WHERE jd_id=? AND is_active=1 ORDER BY item_order,id', (existing['id'],))]
                incoming = [(a['item_order'], a['description'], a.get('kpi') or '')
                            for a in parsed_jd.get('accountabilities', [])]
                if fields_match and current == incoming:
                    return existing['id']
                raise ValueError('تختلف البطاقة المستوردة عن البطاقة المسجلة. يرجى استخدام طلب تعديل لحفظ المراجعة.')
        jd_id = _insert_parsed_jd(conn, parsed_jd, source_file, actor['full_name'], commit=False,
                                  notes=f"تمت الإضافة من ملف Word; actor_id={actor['id']}")
        if parsed_jd.get('format_version') == 2:
            conn.execute('UPDATE job_descriptions SET import_hash=? WHERE id=?', (import_hash, jd_id))
        return jd_id


def submit_modification_request(jd_id, section_name, clause_id, original_text, proposed_text, justification, *, actor_id):
    with _write_connection() as conn:
        actor = _require_actor(conn, actor_id, jd_id=jd_id)
        _, _, current = _resolve_target(conn, jd_id, section_name, clause_id)
        if not isinstance(proposed_text, str) or not proposed_text.strip() or not isinstance(justification, str) or not justification.strip():
            raise ValueError("يجب إدخال النص المقترح ومبرر التعديل.")
        if (original_text or "") != current:
            raise ValueError("تغير النص الحالي. يرجى إعادة تحميل البطاقة.")
        if proposed_text.strip() == current.strip():
            raise ValueError("النص المقترح مطابق للنص الحالي.")
        state = governance.snapshot(conn, jd_id)
        cur = conn.execute("""
            INSERT INTO modification_requests
            (jd_id,section_name,clause_id,original_text,proposed_text,justification,requested_by,status,
             expected_version,expected_hash,requested_snapshot)
            VALUES (?,?,?,?,?,?,?,'قيد الانتظار',?,?,?)
        """, (jd_id, section_name, str(clause_id), current, proposed_text, justification, actor['full_name'],
              state['card']['version'], governance.content_hash(state), governance.encode(state)))
        return cur.lastrowid


def get_pending_modification_requests(jd_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if jd_id:
        cur.execute("""
        SELECT m.*, j.title as jd_title, j.department as jd_department
        FROM modification_requests m
        JOIN job_descriptions j ON m.jd_id = j.id
        WHERE (m.status = 'قيد الانتظار' OR m.status = 'Pending') AND m.jd_id = ?
        ORDER BY m.requested_at DESC
        """, (jd_id,))
    else:
        cur.execute("""
        SELECT m.*, j.title as jd_title, j.department as jd_department
        FROM modification_requests m
        JOIN job_descriptions j ON m.jd_id = j.id
        WHERE (m.status = 'قيد الانتظار' OR m.status = 'Pending')
        ORDER BY m.requested_at DESC
        """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_requests_by_user(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT m.*, j.title as jd_title
    FROM modification_requests m
    JOIN job_descriptions j ON m.jd_id = j.id
    WHERE m.requested_by = ?
    ORDER BY m.requested_at DESC
    """, (username,))
    rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        row['status'] = display_status(ReviewStatus, row['status'])
    conn.close()
    return rows


def review_modification_request(request_id, decision, reviewer_comments, *, actor_id):
    with _write_connection() as conn:
        actor = _require_actor(conn, actor_id, admin=True)
        try:
            status = ReviewStatus.parse(decision)
        except ValueError:
            return False, "قرار المراجعة غير صالح."
        if status == ReviewStatus.PENDING:
            return False, "قرار المراجعة غير صالح."
        req = conn.execute("SELECT * FROM modification_requests WHERE id=?", (request_id,)).fetchone()
        if not req:
            return False, "طلب التعديل غير موجود."
        if ReviewStatus.parse(req['status']) != ReviewStatus.PENDING:
            return False, "تمت مراجعة هذا الطلب بالفعل."
        try:
            kind, target, current = _resolve_target(conn, req['jd_id'], req['section_name'], req['clause_id'])
        except ValueError as exc:
            return False, str(exc)
        status = status.value
        before = governance.snapshot(conn, req['jd_id'])
        if status == 'مقبول' and (req['expected_version'] != before['card']['version'] or
                                  req['expected_hash'] != governance.content_hash(before)):
            return False, 'تغير إصدار البطاقة أو محتواها منذ تقديم الطلب. يرجى تقديم طلب جديد.'
        if status == 'مقبول' and current != (req['original_text'] or ""):
            return False, "تغير النص منذ تقديم الطلب. يرجى إعادة المراجعة."
        if status == 'مقبول' and not req['proposed_text'].strip():
            return False, "النص المقترح غير صالح."
        now = _utc_now()
        changed = conn.execute("""
            UPDATE modification_requests SET status=?,reviewer_comments=?,reviewed_by=?,reviewed_at=?
            WHERE id=? AND jd_id=? AND status IN ('Pending','قيد الانتظار')
        """, (status, reviewer_comments, actor['full_name'], now, request_id, req['jd_id'])).rowcount
        if changed != 1:
            raise RuntimeError("تعذر تحديث طلب التعديل.")
        if status == 'مقبول':
            if kind == 'accountability':
                # jd_id is the existing parent-card column; no schema rename.
                changed = conn.execute("""
                    UPDATE accountabilities SET description=?,version=version+1
                    WHERE id=? AND jd_id=? AND is_active=1
                """, (req['proposed_text'], target, req['jd_id'])).rowcount
                if changed != 1:
                    raise ValueError("تعذر تحديث المسؤولية التابعة للبطاقة.")
            else:
                changed = conn.execute(f"""
                    UPDATE job_descriptions SET {target}=?,updated_at=? WHERE id=?
                """, (req['proposed_text'], now, req['jd_id'])).rowcount
            if changed != 1:
                raise ValueError("تعذر تحديث البطاقة.")
            governance.bind_review(conn, req['jd_id'])
        action = "تم اعتماد التعديل" if status == 'مقبول' else "تم رفض التعديل"
        conn.execute("""
            INSERT INTO jd_audit_trail
            (jd_id,mod_request_id,section_name,action,old_text,new_text,changed_by,notes,changed_at,
             actor_id,card_version,decision,snapshot_json,snapshot_hash,result_json,result_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (req['jd_id'], request_id, req['section_name'], action, current, req['proposed_text'],
              actor['full_name'], f"actor_id={actor['id']}; طلب #{request_id}; {reviewer_comments}", now,
              *_evidence_values(actor, status, before, governance.snapshot(conn, req['jd_id']))))
    return True, f"تمت معالجة الطلب بنجاح ({status})."


def _evidence_values(actor, decision, before, after):
    original, result = governance.encode(before), governance.encode(after)
    return (actor['id'], before['card']['version'], decision, original, governance.digest(original),
            result, governance.digest(result))


def request_jd_review(jd_id, *, actor_id):
    with _write_connection() as conn:
        _require_actor(conn, actor_id, jd_id=jd_id)
        card = conn.execute('SELECT * FROM job_descriptions WHERE id=?', (jd_id,)).fetchone()
        state = governance.canonical_status(card['status'])
        if state == 'معتمد':
            raise ValueError('لا يمكن إعادة مراجعة بطاقة معتمدة دون تعديل المحتوى.')
        if state == 'قيد المراجعة' and card['review_hash'] is not None:
            raise ValueError('البطاقة قيد المراجعة بالفعل.')
        conn.execute("UPDATE job_descriptions SET status='قيد المراجعة' WHERE id=?", (jd_id,))
        governance.bind_review(conn, jd_id)


def approve_jd_as_is(jd_id, comments="", *, actor_id, expected_version=None, expected_hash=None):
    return decide_jd_review(jd_id, 'Approved', comments, actor_id=actor_id,
                            expected_version=expected_version, expected_hash=expected_hash)


def decide_jd_review(jd_id, decision, comments='', *, actor_id, expected_version=None, expected_hash=None):
    target_status = governance.canonical_status(decision)
    if target_status not in ('معتمد', 'مرفوض'):
        raise ValueError('قرار المراجعة غير صالح.')
    with _write_connection() as conn:
        actor = _require_actor(conn, actor_id, jd_id=jd_id)
        if target_status == 'مرفوض':
            _require_actor(conn, actor_id, admin=True)
        if conn.execute("SELECT 1 FROM modification_requests WHERE jd_id=? AND status IN ('Pending','قيد الانتظار')",
                        (jd_id,)).fetchone():
            raise ValueError("توجد طلبات تعديل معلقة. يرجى مراجعتها قبل الاعتماد.")
        card = conn.execute("SELECT * FROM job_descriptions WHERE id=?", (jd_id,)).fetchone()
        if governance.canonical_status(card['status']) != 'قيد المراجعة':
            raise ValueError('لا يمكن اتخاذ القرار إلا لبطاقة قيد المراجعة.')
        before = governance.snapshot(conn, jd_id)
        fingerprint = governance.content_hash(before)
        if (card['review_version'] != card['version'] or card['review_hash'] != fingerprint or
                (expected_version is not None and expected_version != card['version']) or
                (expected_hash is not None and expected_hash != fingerprint)):
            raise ValueError('تغيرت البطاقة منذ طلب المراجعة. يرجى إعادة تحميلها وإرسالها للمراجعة.')
        now = _utc_now()
        changed = conn.execute("UPDATE job_descriptions SET status=?,updated_at=? WHERE id=?",
                               (target_status, now, jd_id)).rowcount
        if changed != 1:
            raise ValueError("تعذر اعتماد البطاقة.")
        conn.execute("""
            INSERT INTO jd_audit_trail (jd_id,section_name,action,new_text,changed_by,notes,changed_at,
                actor_id,card_version,decision,snapshot_json,snapshot_hash,result_json,result_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (jd_id, 'حالة الوثيقة', 'اعتماد نهائي دون تعديل' if target_status == 'معتمد' else 'رفض اعتماد البطاقة',
              target_status, actor['full_name'], f"actor_id={actor['id']}; version={card['version']}; {comments}", now,
              *_evidence_values(actor, target_status, before, governance.snapshot(conn, jd_id))))
    return True


def get_audit_trail(jd_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if jd_id:
        cur.execute("""
        SELECT a.*, j.title as jd_title
        FROM jd_audit_trail a
        JOIN job_descriptions j ON a.jd_id = j.id
        WHERE a.jd_id = ?
        ORDER BY a.changed_at DESC
        """, (jd_id,))
    else:
        cur.execute("""
        SELECT a.*, j.title as jd_title
        FROM jd_audit_trail a
        JOIN job_descriptions j ON a.jd_id = j.id
        ORDER BY a.changed_at DESC
        """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_decision_evidence(jd_id, *, _conn=None):
    """Verify persisted bytes before exposing revision-bound evidence."""
    import json
    if _conn is None:
        with closing(get_connection()) as conn:
            return get_decision_evidence(jd_id, _conn=conn)
    records = _conn.execute('SELECT * FROM jd_audit_trail WHERE jd_id=? AND snapshot_json IS NOT NULL ORDER BY id',
                            (jd_id,)).fetchall()
    result = []
    for row in records:
        row = dict(row)
        for value, checksum in (('snapshot_json', 'snapshot_hash'), ('result_json', 'result_hash')):
            if governance.digest(row[value]) != row[checksum]:
                raise ValueError('فشل التحقق من سلامة سجل المراجعة.')
            row[value] = json.loads(row[value])
        result.append(row)
    return result


def get_approval_metadata(jd_id, *, _conn=None):
    """Only a final approval of the current revision is electronic approval."""
    if _conn is None:
        with closing(get_connection()) as conn:
            conn.execute('BEGIN')
            return get_approval_metadata(jd_id, _conn=conn)
    state = governance.snapshot(_conn, jd_id)
    if governance.canonical_status(state['card']['status']) != 'معتمد':
        return None
    for record in reversed(get_decision_evidence(jd_id, _conn=_conn)):
        if (record['mod_request_id'] is None and record['decision'] == 'معتمد' and
                record['card_version'] == state['card']['version'] and
                governance.content_hash(record['snapshot_json']) == governance.content_hash(state)):
            return {'approver': record['changed_by'], 'actor_id': record['actor_id'],
                    'decided_at': record['changed_at'], 'version': record['card_version'],
                    'snapshot_hash': record['snapshot_hash'], 'evidence_id': record['id']}
    return None


def get_export_data(jd_id):
    """Content and approval evidence from one consistent SQLite read transaction."""
    with closing(get_connection()) as conn:
        conn.execute('BEGIN')
        state = governance.snapshot(conn, jd_id)
        card = state['card']
        card['status'] = governance.canonical_status(card['status'])
        return (card, [r for r in state['accountabilities'] if r['is_active']],
                get_approval_metadata(jd_id, _conn=conn))


def get_interview_schedule():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM interview_schedule ORDER BY seq_num ASC")
    rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        row['status'] = display_status(InterviewStatus, row['status'])
    conn.close()
    return rows


def update_interview_status(item_id, status=None, notes=None, *, actor_id, expected=None, clear_notes=False):
    with _write_connection() as conn:
        _require_actor(conn, actor_id, admin=True)
        current = conn.execute('SELECT * FROM interview_schedule WHERE id=?', (item_id,)).fetchone()
        if not current:
            raise ValueError("المقابلة غير موجودة.")
        if expected is not None and (display_status(InterviewStatus, current['status']) != expected['status'] or current['notes'] != expected['notes']):
            raise ValueError('تغيرت بيانات المقابلة. يرجى إعادة تحميلها قبل الحفظ.')
        new_status = display_status(InterviewStatus, current['status'])
        if status is not None and not (isinstance(status, str) and not status.strip()):
            new_status = InterviewStatus.parse(status).value
        new_notes = '' if clear_notes else (notes if isinstance(notes, str) and notes.strip() else current['notes'])
        conn.execute('UPDATE interview_schedule SET status=?,notes=? WHERE id=?', (new_status, new_notes, item_id))


def get_dashboard_stats():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as total_jds FROM job_descriptions")
    total_jds = cur.fetchone()['total_jds']

    cur.execute("SELECT COUNT(*) as approved_jds FROM job_descriptions WHERE status = 'معتمد' OR status = 'Approved'")
    approved_jds = cur.fetchone()['approved_jds']

    cur.execute("SELECT COUNT(*) FROM job_descriptions WHERE status IN ('قيد المراجعة','Under Review','Pending Review')")
    under_review = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as pending_mods FROM modification_requests WHERE status = 'قيد الانتظار' OR status = 'Pending'")
    pending_mods = cur.fetchone()['pending_mods']

    cur.execute("SELECT COUNT(DISTINCT department) as depts FROM job_descriptions WHERE department != ''")
    depts_count = cur.fetchone()['depts']

    conn.close()
    return {
        'total_jds': total_jds,
        'approved_jds': approved_jds,
        'under_review': under_review,
        'pending_mods': pending_mods,
        'departments_count': depts_count
    }


def get_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users(*, actor_id):
    """Admin directory; credential material never leaves this query."""
    with closing(get_connection()) as conn:
        _require_actor(conn, actor_id, admin=True)
        return [dict(row) for row in conn.execute('''
            SELECT id,username,full_name,role,department,assigned_jd_id,is_active,created_at
            FROM users ORDER BY full_name,id
        ''')]


def _validate_new_password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise ValueError('يجب أن تكون كلمة المرور بين 12 و1024 حرفاً.')


def create_new_user(username, full_name, role, password, *, actor_id, department=None, assigned_jd_id=None):
    import auth
    with _write_connection() as conn:
        _require_actor(conn, actor_id, admin=True)
        if not isinstance(username, str) or not re.fullmatch(r'[\w.@-]{1,100}', username.strip()):
            raise ValueError('اسم المستخدم مطلوب، ويسمح بالحروف والأرقام والنقطة والشرطة و@ فقط.')
        if not isinstance(full_name, str) or not full_name.strip() or len(full_name.strip()) > 150:
            raise ValueError('يرجى إدخال الاسم الكامل بما لا يتجاوز 150 حرفاً.')
        if role not in ('admin', 'manager', 'employee'):
            raise ValueError('دور المستخدم غير صالح.')
        _validate_new_password(password)
        if assigned_jd_id is not None and (type(assigned_jd_id) is not int or not conn.execute(
                'SELECT 1 FROM job_descriptions WHERE id=?', (assigned_jd_id,)).fetchone()):
            raise ValueError('بطاقة الوصف الوظيفي المخصصة غير موجودة.')
        if department is not None and (not isinstance(department, str) or len(department) > 150):
            raise ValueError('اسم الإدارة غير صالح.')
        encoded = auth.hash_password(password)
        try:
            cursor = conn.execute('''INSERT INTO users
                (username,password,full_name,role,department,assigned_jd_id)
                VALUES (?,?,?,?,?,?)''',
                (username.strip(), encoded, full_name.strip(), role, department, assigned_jd_id))
        except (sqlite3.IntegrityError, getattr(psycopg2, "IntegrityError", sqlite3.IntegrityError)) as exc:
            code = getattr(exc, "sqlite_errorcode", None)
            pgcode = getattr(exc, "pgcode", None)
            if code == sqlite3.SQLITE_CONSTRAINT_UNIQUE or pgcode == "23505":
                raise ValueError('اسم المستخدم مسجل بالفعل. يرجى اختيار اسم آخر.') from None
            raise
        return cursor.lastrowid


def admin_reset_password(user_id, new_password, *, actor_id):
    import auth
    with _write_connection() as conn:
        _require_actor(conn, actor_id, admin=True)
        if type(user_id) is not int or not conn.execute('SELECT 1 FROM users WHERE id=?', (user_id,)).fetchone():
            raise ValueError('المستخدم غير موجود.')
        _validate_new_password(new_password)
        conn.execute('UPDATE users SET password=?,auth_version=auth_version+1 WHERE id=?',
                     (auth.hash_password(new_password), user_id))
    return True


def toggle_user_status(user_id, *, actor_id, expected_active=None):
    with _write_connection() as conn:
        actor = _require_actor(conn, actor_id, admin=True)
        if type(user_id) is not int:
            raise ValueError('المستخدم غير موجود.')
        target = conn.execute('SELECT is_active FROM users WHERE id=?', (user_id,)).fetchone()
        if not target:
            raise ValueError('المستخدم غير موجود.')
        if user_id == actor['id']:
            raise ValueError('لا يمكنك تعطيل حسابك الحالي.')
        if expected_active is not None and expected_active != bool(target['is_active']):
            raise ValueError('تغيرت حالة الحساب. يرجى إعادة تحميل قائمة المستخدمين.')
        active = not bool(target['is_active'])
        conn.execute('UPDATE users SET is_active=?,auth_version=auth_version+1 WHERE id=?', (int(active), user_id))
        return active


def get_admin_system_summary(*, actor_id):
    with closing(get_connection()) as conn:
        _require_actor(conn, actor_id, admin=True)
        row = conn.execute('''SELECT
            (SELECT count(*) FROM job_descriptions) AS cards,
            (SELECT count(*) FROM accountabilities) AS responsibilities,
            (SELECT count(*) FROM interview_schedule) AS interviews,
            (SELECT count(*) FROM users) AS users''').fetchone()
        return dict(row)


def create_manual_backup(*, actor_id):
    from backups import backup_database, sha256_file, verify_backup_checksum
    with closing(get_connection()) as conn:
        _require_actor(conn, actor_id, admin=True)
    # Do not hold a writer transaction while SQLite's backup API copies the DB.
    artifact = backup_database(DB_PATH)
    verify_backup_checksum(artifact, required=True)
    return {'name': artifact.name, 'sha256': sha256_file(artifact)}


def get_user_by_id(user_id):
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None
