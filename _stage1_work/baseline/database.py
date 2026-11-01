"""
Database module for 3S Security Job Description Management System.
Handles SQLite connection, schema definition, seed data, and CRUD operations in Arabic.
"""

import sqlite3
import os
import glob
import re
from datetime import datetime
import openpyxl
from docx_parser import parse_jd_docx

DB_PATH = os.path.join(os.path.dirname(__file__), "job_descriptions.db")

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
    return conn


def init_db():
    """Initializes tables and seeds initial data if database is empty."""
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
        seed_users(conn)

    conn.close()


def insert_parsed_jd(conn, parsed, source_file, changed_by="مسؤول النظام"):
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
    """, (jd_id, f"استيراد الوصف الوظيفي من الملف: {source_file}", changed_by, "تمت الإضافة من ملف Word المعتمد"))

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
            insert_parsed_jd(conn, parsed, source_file=os.path.basename(file_path), changed_by="النظام الأساسي")
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


def seed_users(conn):
    cur = conn.cursor()
    users_data = [
        ("admin", "admin123", "مدير الموارد البشرية والمسؤول العام", "admin", "إدارة الموارد البشرية", None),
        ("hr.manager", "hr123", "مدير الموارد البشرية", "admin", "إدارة الموارد البشرية", None),
        ("ashraf.shaker", "md123", "د. أشرف شاكر (العضو المنتدب والمدير التنفيذي)", "manager", "الإدارة العليا والتنفيذية", "العضو المنتدب"),
        ("ahmed.taha", "pass123", "م. أحمد طه (مدير إدارة المشروعات)", "manager", "إدارة المشروعات", "مدير إدارة المشروعات"),
        ("ramy.tech", "pass123", "م. رامي (مدير المكتب الفني)", "manager", "إدارة المكتب الفني", "مدير المكتب الفني"),
        ("sales.mgr", "pass123", "مدير عام المبيعات والتجاري", "manager", "الإدارة التجارية", "مدير عام المبيعات"),
        ("tech.support", "pass123", "م. محمد عبدالرازق (مدير الدعم الفني)", "manager", "إدارة الدعم الفني والتركيبات", "مدير الدعم الفني"),
        ("qc.mgr", "pass123", "مدير إدارة الجودة وتوكيد الجودة", "manager", "إدارة الجودة", "مدير مراقبة الجودة"),
        ("tawfik.wh", "pass123", "أ. توفيق (أمين عام المخازن)", "manager", "إدارة المخازن", "المخازن"),
        ("procurement.mgr", "pass123", "ريمون / سندس (مدير المشتريات وسلاسل الإمداد)", "manager", "إدارة المشتريات وسلاسل الإمداد", "المشتريات"),
        ("maintenance.mgr", "pass123", "م. محمد مدكور (مدير الصيانة)", "manager", "إدارة الصيانة", "مدير الصيانة"),
        ("pr.mgr", "pass123", "أ. هشام حسين (مدير العلاقات العامة والشئون الإدارية)", "manager", "الإدارة العامة", "العلاقات العامة"),
        ("cfo", "pass123", "أ. محمد مصطفى (المدير المالي التنفيذي)", "manager", "الإدارة المالية", "المالي"),
        ("employee", "emp123", "مهندس التركيبات الميداني", "employee", "إدارة الدعم الفني والتركيبات", "التركيبات"),
        ("employee.sales", "emp123", "أخصائي المبيعات والحسابات التجارية", "employee", "الإدارة التجارية", "المبيعات"),
    ]

    for u in users_data:
        username, pwd, full_name, role, dept, jd_title_hint = u
        assigned_id = None
        if jd_title_hint:
            cur.execute("SELECT id FROM job_descriptions WHERE title LIKE ? LIMIT 1", (f"%{jd_title_hint}%",))
            row = cur.fetchone()
            if row:
                assigned_id = row['id']

        cur.execute("""
        INSERT OR IGNORE INTO users (username, password, full_name, role, department, assigned_jd_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (username, pwd, full_name, role, dept, assigned_id))

    conn.commit()


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


def create_or_update_jd(parsed_jd, source_file, changed_by="مسؤول النظام"):
    conn = get_connection()
    jd_id = insert_parsed_jd(conn, parsed_jd, source_file=source_file, changed_by=changed_by)
    conn.close()
    return jd_id


def submit_modification_request(jd_id, section_name, clause_id, original_text, proposed_text, justification, requested_by):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO modification_requests (
        jd_id, section_name, clause_id, original_text, proposed_text, justification, requested_by, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'قيد الانتظار')
    """, (jd_id, section_name, str(clause_id), original_text, proposed_text, justification, requested_by))
    req_id = cur.lastrowid
    conn.commit()
    conn.close()
    return req_id


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


def review_modification_request(request_id, decision, reviewer_comments, reviewed_by):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM modification_requests WHERE id = ?", (request_id,))
    req = cur.fetchone()
    if not req:
        conn.close()
        return False, "طلب التعديل غير موجود."

    status = "مقبول" if (decision == "Accept" or decision == "مقبول") else "مرفوض"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    UPDATE modification_requests
    SET status = ?, reviewer_comments = ?, reviewed_by = ?, reviewed_at = ?
    WHERE id = ?
    """, (status, reviewer_comments, reviewed_by, now_str, request_id))

    if status == "مقبول":
        jd_id = req['jd_id']
        section_name = req['section_name']
        clause_id = req['clause_id']
        proposed_text = req['proposed_text']
        original_text = req['original_text']

        if "المسؤولية #" in section_name or "Accountability" in section_name or (clause_id and clause_id.isdigit()):
            acc_id = int(clause_id)
            cur.execute("""
            UPDATE accountabilities
            SET description = ?, version = version + 1
            WHERE id = ?
            """, (proposed_text, acc_id))
        else:
            field_map = {
                "الهدف العام من الوظيفة": "purpose",
                "Job Purpose": "purpose",
                "أبعاد الوظيفة": "dimensions",
                "Job Dimensions": "dimensions",
                "إطار العمل وحدود اتخاذ القرارات": "frameworks",
                "Frameworks & Authority": "frameworks",
                "المؤهلات والخبرات والمهارات": "qualifications",
                "Qualifications & Skills": "qualifications",
                "الجدارات والكفاءات": "competencies",
                "Competencies": "competencies",
                "مخاطر الوظيفة": "hazards",
                "Job Hazards": "hazards",
                "ممارسات السلامة والصحة المهنية": "safe_practices",
                "Safe Practices": "safe_practices",
                "العلاقات الداخلية": "internal_relations",
                "Internal Relations": "internal_relations",
                "العلاقات الخارجية": "external_relations",
                "External Relations": "external_relations",
                "المسمى الوظيفي": "title",
                "Position Title": "title",
                "الإدارة": "department",
                "Department": "department",
                "القطاع": "sector",
                "Sector": "sector",
                "المسؤول المباشر": "reports_to",
                "Reports To": "reports_to"
            }
            col_name = field_map.get(section_name, None)
            if col_name:
                cur.execute(f"""
                UPDATE job_descriptions
                SET {col_name} = ?, version = version + 1, updated_at = ?
                WHERE id = ?
                """, (proposed_text, now_str, jd_id))

        cur.execute("""
        INSERT INTO jd_audit_trail (
            jd_id, mod_request_id, section_name, action, old_text, new_text, changed_by, notes
        ) VALUES (?, ?, ?, 'تم اعتماد التعديل', ?, ?, ?, ?)
        """, (
            jd_id, request_id, section_name, original_text, proposed_text,
            reviewed_by, f"تم قبول الطلب رقم #{request_id} المقدم من: {req['requested_by']}. ملاحظات المراجع: {reviewer_comments}"
        ))

    conn.commit()
    conn.close()
    return True, f"تمت معالجة الطلب بنجاح ({status})."


def approve_jd_as_is(jd_id, approved_by, comments=""):
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    UPDATE job_descriptions
    SET status = 'معتمد', updated_at = ?
    WHERE id = ?
    """, (now_str, jd_id))

    cur.execute("""
    INSERT INTO jd_audit_trail (
        jd_id, section_name, action, new_text, changed_by, notes
    ) VALUES (?, 'حالة الوثيقة', 'اعتماد نهائي دون تعديل', 'الحالة: معتمد', ?, ?)
    """, (jd_id, approved_by, f"تم الاعتماد والموافقة على الوصف الوظيفي كما هو. ملاحظات: {comments}"))

    conn.commit()
    conn.close()
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


def update_interview_status(item_id, status, notes=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    UPDATE interview_schedule
    SET status = ?, notes = ?
    WHERE id = ?
    """, (status, notes, item_id))
    conn.commit()
    conn.close()


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
