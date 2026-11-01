from pathlib import Path
p = Path('app.py')
s = p.read_text(encoding='utf-8')
s = s.replace('from datetime import datetime', 'from datetime import datetime\nimport logging\nimport sqlite3')
s = s.replace('# Page configuration', '''def _run_write(operation, *args, **kwargs):
    """Present safe failures without continuing into success/rerun handlers."""
    try:
        return operation(*args, **kwargs)
    except (PermissionError, ValueError) as exc:
        st.error(str(exc))
        st.stop()
    except (sqlite3.Error, RuntimeError):
        logging.getLogger(__name__).exception("Governance write failed")
        st.error("تعذر حفظ التغيير. لم يتم اعتماد العملية. يرجى المحاولة مجدداً.")
        st.stop()


# Page configuration''', 1)
s = s.replace('database.init_db()', '''try:
    database.init_db()
except (OSError, sqlite3.Error, RuntimeError):
    logging.getLogger(__name__).exception("Database startup/backup failed")
    st.error("تعذر التحقق من قاعدة البيانات والنسخة الاحتياطية. يرجى التواصل مع مسؤول النظام.")
    st.stop()''', 1)
s = s.replace("يمكنك استخدام ميزة 'التبديل السريع' لتجربة النظام كمدير موارد بشرية، أو عضو منتدب، أو مدير إدارة.", "يجب إدخال اسم المستخدم وكلمة المرور الخاصة بك للوصول إلى صلاحياتك المعتمدة.")
s = s.replace('user = st.session_state.user_info', '''user = auth.get_authenticated_user()
if user is None:
    st.stop()''', 1)
for name in ('review_modification_request','create_or_update_jd','update_interview_status','approve_jd_as_is','submit_modification_request'):
    s = s.replace(f'database.{name}(', f'_run_write(database.{name}, ')
s = s.replace("reviewed_by=user['full_name']", "actor_id=user['id']")
s = s.replace("changed_by=user['full_name']", "actor_id=user['id']")
s = s.replace("approved_by=user['full_name']", "actor_id=user['id']")
s = s.replace("requested_by=user['full_name']", "actor_id=user['id']")
s = s.replace('chosen_id, new_status, interview_notes)', "chosen_id, new_status, interview_notes, actor_id=user['id'])")
start = s.index('    if not assigned_jd_id:')
end = s.index('    tab_my_jd,', start)
s = s[:start] + '''    if not all_jds or assigned_jd_id not in {j['id'] for j in all_jds}:
        st.info("لم يتم تخصيص بطاقة وصف وظيفي صالحة لحسابك. يرجى التواصل مع الموارد البشرية.")
        if all_jds:
            st.dataframe(pd.DataFrame(all_jds)[['title', 'department', 'reports_to', 'status', 'version']], hide_index=True)
        st.stop()

''' + s[end:]
s = s.replace("        # Approval & Modification Action Bar in Arabic", '''        can_write_card = current_jd_id == user['assigned_jd_id']
        if not can_write_card:
            st.info("هذه البطاقة متاحة للاستعراض. صلاحية الاعتماد وطلب التعديل تقتصر على البطاقة المخصصة لك.")

        # Approval & Modification Action Bar in Arabic''')
s = s.replace('st.button("تأكيد الاعتماد والموافقة النهائية", type="primary", use_container_width=True)', 'st.button("تأكيد الاعتماد والموافقة النهائية", type="primary", use_container_width=True, disabled=not can_write_card)')
s = s.replace('with st.form("submit_mod_form"):', 'with st.form(f"submit_mod_form_{current_jd_id}_{clause_id_val}"):')
s = s.replace('st.form_submit_button("إرسال طلب التعديل إلى الموارد البشرية", type="primary", use_container_width=True)', 'st.form_submit_button("إرسال طلب التعديل إلى الموارد البشرية", type="primary", use_container_width=True, disabled=not can_write_card)')
# Make interview fields reflect the selected record; a selector inside the form cannot rerun.
start = s.index('            with st.form("update_interview_form"):')
end = s.index('\n# -------------------------------------------------------------\n# EMPLOYEE', start)
s = s[:start] + '''            item_options = {f"#{it['seq_num']}: {it['department']} - {it['manager_name']}": it['id'] for it in schedule_items}
            chosen_item_label = st.selectbox("اختر المقابلة / الإدارة المستهدفة", list(item_options.keys()))
            chosen_id = item_options[chosen_item_label]
            selected_interview = next(it for it in schedule_items if it['id'] == chosen_id)
            statuses = list(dict.fromkeys([selected_interview['status'], "قيد المراجعة", "مكتملة", "مؤجلة", "لم تبدأ"]))
            with st.form(f"update_interview_form_{chosen_id}"):
                new_status = st.selectbox("حالة المقابلة الحالية", statuses)
                interview_notes = st.text_area("الملاحظات ومخرجات الاجتماع المتفق عليها", value=selected_interview['notes'] or "")
                save_interview = st.form_submit_button("حفظ وتحديث حالة المقابلة", type="primary")
                if save_interview:
                    _run_write(database.update_interview_status, chosen_id, new_status, interview_notes, actor_id=user['id'])
                    st.success("تم تحديث حالة المقابلة وتوثيق المخرجات بنجاح!")
                    st.rerun()
''' + s[end:]
p.write_text(s, encoding='utf-8', newline='\n')

# Remove published credentials and unsafe one-click production-publication advice.
p = Path('README.md')
s = p.read_text(encoding='utf-8')
start = s.index('## 👥')
s = s[:start] + '''## 🔐 التشغيل الآمن وإدارة الحسابات

أُزيلت الحسابات التجريبية من واجهة الدخول والتبديل بين المستخدمين. تسجيل الدخول يتطلب إدخال بيانات الحساب والتحقق منها في قاعدة البيانات. صلاحيات التعديل والاعتماد للمدير والموظف تقتصر على البطاقة المخصصة، مع استمرار استعراض دليل الشركة.

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python -m pip install -r requirements-dev.txt
.\\.venv\\Scripts\\python -m scripts.migrate_passwords
.\\.venv\\Scripts\\python -m pytest -q
.\\.venv\\Scripts\\python -m streamlit run app.py
```

الترحيل يحفظ كلمات المرور الحالية كقيم Argon2id في العمود الحالي دون تغيير الجداول أو المعرفات أو السجلات التاريخية. يجب تغيير كلمات المرور التي سبق نشرها من خلال أداة إدارة الحسابات، باستخدام إدخال سري تفاعلي:

```powershell
.\\.venv\\Scripts\\python -m scripts.manage_account --username YOUR_USERNAME
```

لا يتم إنشاء حسابات أو كلمات مرور افتراضية في التشغيل الجديد. لإنشاء مسؤول جديد بشكل صريح:

```powershell
.\\.venv\\Scripts\\python -m scripts.manage_account --username YOUR_ADMIN --create-admin
```

تُنشأ نسخة SQLite متسقة ومختبرة الاستعادة قبل بدء عملية الخادم وقبل الترحيل أو تغيير بيانات الحسابات في `data/backups/`. قد تحتوي النسخ السابقة للترحيل على كلمات المرور القديمة؛ يجب حمايتها بصلاحيات نظام التشغيل وعدم نشرها. لا ترفع قاعدة البيانات أو النسخ الاحتياطية أو مستندات الموظفين إلى مستودع عام. التشغيل الإنتاجي يتطلب تخزيناً دائماً ونسخاً محمية خارج الجهاز.

انظر [دليل تنفيذ المرحلة الأولى](docs/STAGE1_SECURITY.md) للتفاصيل، الاختبارات، الاستعادة والحدود المتبقية. تحافظ هذه المرحلة على البنية الحالية ولا تمثل اعتماداً لجاهزية الإنتاج.
'''
p.write_text(s, encoding='utf-8', newline='\n')
