"""
Database module for 3S Security Job Description Management System.
Handles SQLite connection, schema definition, seed data, and CRUD operations in Arabic.
"""

import sqlite3
import os
import glob
import re
from datetime import datetime, timezone
from contextlib import closing, contextmanager
from backups import backup_before_startup
import openpyxl
from docx_parser import parse_jd_docx

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


def get_connection():
    """Returns a connection to the SQLite database with row_factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initializes tables and seeds initial data if database is empty."""
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
        status TEXT DEFAULT 'قيد المراجعة',
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

    cur.execute("SELECT COUNT(*) as cnt FROM job_descriptions")
    jd_count = cur.fetchone()['cnt']
    if jd_count == 0:
        seed_job_descriptions(conn)
        seed_interview_schedule(conn)

    conn.close()


def _insert_parsed_jd(conn, parsed, source_file, changed_by="مسؤول النظام", *, commit=True, notes="تمت الإضافة من ملف Word المعتمد"):
    """Inserts a parsed JD dictionary and its accountabilities into DB with auto Arabic translation."""
    cur = conn.cursor()

    raw_title = parsed.get('title', 'بطاقة وصف وظيفي جديدة').strip()
    title = TITLE_MAP.get(raw_title, raw_title)

    raw_dept = parsed.get('department', '').strip()
    dept = DEPT_MAP.get(raw_dept, raw_dept if raw_dept else 'الإدارة العامة')

    raw_rep = parsed.get('reports_to', '').strip()
    reports_to = REPORTS_MAP.get(raw_rep, raw_rep if raw_rep else 'مجلس الإدارة')

    dimensions = translate_dimensions(parsed.get('dimensions', ''))
    qualifications = translate_qualifications(parsed.get('qualifications', ''))

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
        parsed.get('sector', 'الإدارة العامة والمجموعة') or 'الإدارة العامة والمجموعة',
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
        """, (jd_id, idx + 1, acc.get('description', ''), acc.get('kpi', '')))

    cur.execute("""
    INSERT INTO jd_audit_trail (jd_id, section_name, action, new_text, changed_by, notes)
    VALUES (?, 'كامل الوثيقة', 'إدراج أولي', ?, ?, ?)
    """, (jd_id, f"استيراد الوصف الوظيفي من الملف: {source_file}", changed_by, notes))

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
                    status = str(row[6]).strip() if row[6] else 'قيد المراجعة'
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
            conn.execute("BEGIN IMMEDIATE")
            yield conn


def _require_actor(conn, actor_id, *, jd_id=None, admin=False):
    # Import lazily: authentication reads users through this module.
    import auth
    authenticated = auth.require_actor(actor_id)
    actor = conn.execute("SELECT * FROM users WHERE id=?", (authenticated['id'],)).fetchone()
    if not actor or actor['role'] not in ('admin', 'manager', 'employee'):
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
    conn.close()
    return rows


def get_jd_by_id(jd_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM job_descriptions WHERE id = ?", (jd_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


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
        return _insert_parsed_jd(conn, parsed_jd, source_file, actor['full_name'], commit=False,
                                 notes=f"تمت الإضافة من ملف Word; actor_id={actor['id']}")


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
        cur = conn.execute("""
            INSERT INTO modification_requests
            (jd_id,section_name,clause_id,original_text,proposed_text,justification,requested_by,status)
            VALUES (?,?,?,?,?,?,?,'قيد الانتظار')
        """, (jd_id, section_name, str(clause_id), current, proposed_text, justification, actor['full_name']))
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
    conn.close()
    return rows


def review_modification_request(request_id, decision, reviewer_comments, *, actor_id):
    with _write_connection() as conn:
        actor = _require_actor(conn, actor_id, admin=True)
        decisions = {"Accept": "مقبول", "مقبول": "مقبول", "Reject": "مرفوض", "مرفوض": "مرفوض"}
        if decision not in decisions:
            return False, "قرار المراجعة غير صالح."
        req = conn.execute("SELECT * FROM modification_requests WHERE id=?", (request_id,)).fetchone()
        if not req:
            return False, "طلب التعديل غير موجود."
        if req['status'] not in ('Pending', 'قيد الانتظار'):
            return False, "تمت مراجعة هذا الطلب بالفعل."
        try:
            kind, target, current = _resolve_target(conn, req['jd_id'], req['section_name'], req['clause_id'])
        except ValueError as exc:
            return False, str(exc)
        status = decisions[decision]
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
                changed = conn.execute("""
                    UPDATE job_descriptions SET version=version+1,status='قيد المراجعة',updated_at=? WHERE id=?
                """, (now, req['jd_id'])).rowcount
            else:
                changed = conn.execute(f"""
                    UPDATE job_descriptions SET {target}=?,version=version+1,status='قيد المراجعة',updated_at=? WHERE id=?
                """, (req['proposed_text'], now, req['jd_id'])).rowcount
            if changed != 1:
                raise ValueError("تعذر تحديث البطاقة.")
        action = "تم اعتماد التعديل" if status == 'مقبول' else "تم رفض التعديل"
        conn.execute("""
            INSERT INTO jd_audit_trail
            (jd_id,mod_request_id,section_name,action,old_text,new_text,changed_by,notes,changed_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (req['jd_id'], request_id, req['section_name'], action, current, req['proposed_text'],
              actor['full_name'], f"actor_id={actor['id']}; طلب #{request_id}; {reviewer_comments}", now))
    return True, f"تمت معالجة الطلب بنجاح ({status})."


def approve_jd_as_is(jd_id, comments="", *, actor_id):
    with _write_connection() as conn:
        actor = _require_actor(conn, actor_id, jd_id=jd_id)
        if conn.execute("SELECT 1 FROM modification_requests WHERE jd_id=? AND status IN ('Pending','قيد الانتظار')",
                        (jd_id,)).fetchone():
            raise ValueError("توجد طلبات تعديل معلقة. يرجى مراجعتها قبل الاعتماد.")
        card = conn.execute("SELECT version,status FROM job_descriptions WHERE id=?", (jd_id,)).fetchone()
        if card['status'] in ('Approved', 'معتمد'):
            return True
        now = _utc_now()
        changed = conn.execute("UPDATE job_descriptions SET status='معتمد',updated_at=? WHERE id=?", (now, jd_id)).rowcount
        if changed != 1:
            raise ValueError("تعذر اعتماد البطاقة.")
        conn.execute("""
            INSERT INTO jd_audit_trail (jd_id,section_name,action,new_text,changed_by,notes,changed_at)
            VALUES (?,'حالة الوثيقة','اعتماد نهائي دون تعديل','الحالة: معتمد',?,?,?)
        """, (jd_id, actor['full_name'], f"actor_id={actor['id']}; version={card['version']}; {comments}", now))
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


def get_interview_schedule():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM interview_schedule ORDER BY seq_num ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def update_interview_status(item_id, status, notes="", *, actor_id):
    with _write_connection() as conn:
        _require_actor(conn, actor_id, admin=True)
        changed = conn.execute("UPDATE interview_schedule SET status=?,notes=? WHERE id=?",
                               (status, notes, item_id)).rowcount
        if changed != 1:
            raise ValueError("المقابلة غير موجودة.")


def get_dashboard_stats():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as total_jds FROM job_descriptions")
    total_jds = cur.fetchone()['total_jds']

    cur.execute("SELECT COUNT(*) as approved_jds FROM job_descriptions WHERE status = 'معتمد' OR status = 'Approved'")
    approved_jds = cur.fetchone()['approved_jds']

    cur.execute("SELECT COUNT(*) as pending_mods FROM modification_requests WHERE status = 'قيد الانتظار' OR status = 'Pending'")
    pending_mods = cur.fetchone()['pending_mods']

    cur.execute("SELECT COUNT(DISTINCT department) as depts FROM job_descriptions WHERE department != ''")
    depts_count = cur.fetchone()['depts']

    conn.close()
    return {
        'total_jds': total_jds,
        'approved_jds': approved_jds,
        'under_review': total_jds - approved_jds,
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


def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, role, department, assigned_jd_id FROM users ORDER BY full_name ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_user_by_id(user_id):
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None
