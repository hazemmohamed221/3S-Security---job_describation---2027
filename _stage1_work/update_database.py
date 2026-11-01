from pathlib import Path

path = Path('database.py')
source = path.read_text(encoding='utf-8')
source = source.replace('from datetime import datetime', 'from datetime import datetime, timezone\nfrom contextlib import closing, contextmanager\nfrom backups import backup_before_startup')
source = source.replace('DB_PATH = os.path.join(os.path.dirname(__file__), "job_descriptions.db")', 'DB_PATH = os.environ.get("JD_DB_PATH", os.path.join(os.path.dirname(__file__), "job_descriptions.db"))')
source = source.replace('    conn.row_factory = sqlite3.Row\n    return conn', '    conn.row_factory = sqlite3.Row\n    conn.execute("PRAGMA foreign_keys=ON")\n    return conn')
source = source.replace('    conn = get_connection()\n    cur = conn.cursor()\n\n    cur.execute("""\n    CREATE', '    backup_before_startup(DB_PATH)\n    conn = get_connection()\n    cur = conn.cursor()\n\n    cur.execute("""\n    CREATE', 1)
source = source.replace('        seed_users(conn)\n', '')
start = source.index('def seed_users(conn):')
end = source.index('def get_all_jds():', start)
source = source[:start] + source[end:]
source = source.replace('insert_parsed_jd(', '_insert_parsed_jd(')
source = source.replace('def _insert_parsed_jd(conn, parsed, source_file, changed_by="مسؤول النظام"):', 'def _insert_parsed_jd(conn, parsed, source_file, changed_by="مسؤول النظام", *, commit=True, notes="تمت الإضافة من ملف Word المعتمد"):')
source = source.replace('changed_by, "تمت الإضافة من ملف Word المعتمد"))', 'changed_by, notes))')
source = source.replace('    conn.commit()\n    return jd_id', '    if commit:\n        conn.commit()\n    return jd_id', 1)

helpers = '''
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


'''
pos = source.index('def get_all_jds():')
source = source[:pos] + helpers + source[pos:]
start = source.index('def create_or_update_jd(')
end = source.index('def get_pending_modification_requests(', start)
source = source[:start] + '''def create_or_update_jd(parsed_jd, source_file, *, actor_id):
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


''' + source[end:]
start = source.index('def review_modification_request(')
end = source.index('def get_audit_trail(', start)
source = source[:start] + '''def review_modification_request(request_id, decision, reviewer_comments, *, actor_id):
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


''' + source[end:]
start = source.index('def update_interview_status(')
end = source.index('def get_dashboard_stats(', start)
source = source[:start] + '''def update_interview_status(item_id, status, notes="", *, actor_id):
    with _write_connection() as conn:
        _require_actor(conn, actor_id, admin=True)
        changed = conn.execute("UPDATE interview_schedule SET status=?,notes=? WHERE id=?",
                               (status, notes, item_id)).rowcount
        if changed != 1:
            raise ValueError("المقابلة غير موجودة.")


''' + source[end:]
source += '''

def get_user_by_id(user_id):
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None
'''
path.write_text(source, encoding='utf-8', newline='\n')
