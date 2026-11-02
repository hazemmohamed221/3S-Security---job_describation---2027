"""
شركة ثري إس للأنظمة الأمنية (3S Security Systems)
منظومة حوكمة وإدارة بطاقات الوصف الوظيفي — 2027
تطبيق ويب متكامل باللغة العربية مع دعم كامل للاتجاه من اليمين إلى اليسار (RTL)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import sqlite3
from html import escape

# Local modules
import database
import docx_parser
import utils
import auth
from roles import JD_EDIT_ROLES, ROLE_LABELS
from jd_editor import render_full_jd_editor
from jd_fields import DETAIL_FIELDS
from presentation import (ADMIN_PAGES, MEMBER_PAGES, render_table, audit_dataframe, audit_column_config,
                          format_timestamp, arabic_action, arabic_field, readable_notes)
from statuses import CardStatus, InterviewStatus
from upload_security import sanitize_docx_filename, download_filename, upload_limit_megabytes

def _run_write(operation, *args, **kwargs):
    """Present safe failures without continuing into success/rerun handlers."""
    try:
        return operation(*args, **kwargs)
    except (PermissionError, ValueError) as exc:
        st.error(str(exc))
        st.stop()
    except (OSError, sqlite3.Error, RuntimeError, getattr(database.psycopg2, 'Error', sqlite3.Error)):
        logging.getLogger(__name__).exception("Governance write failed")
        st.error("تعذر حفظ التغيير. لم يتم اعتماد العملية. يرجى المحاولة مجدداً.")
        st.stop()


def _run_jd_workflow(operation_name, *args, **kwargs):
    """A warm deployment can retain an older imported database module."""
    operation = getattr(database, operation_name, None)
    if not callable(operation):
        logging.getLogger(__name__).error(
            'Deployment mismatch: database.%s is unavailable; loaded module: %s',
            operation_name, getattr(database, '__file__', 'unknown'))
        st.error('إصدار خدمة البيانات لا يتوافق مع واجهة التطبيق. لم يتم حفظ أي تغيير. '
                 'يرجى إبلاغ مسؤول النظام لإعادة تشغيل التطبيق من Manage app → Reboot app '
                 'والتأكد من نشر ملفات الإصدار نفسه.')
        st.stop()
    return _run_write(operation, *args, **kwargs)


def render_jd_edit_actions(jd, principal):
    """Confirmed revocation precedes editing; forms are bound to a displayed revision."""
    if principal['role'] not in JD_EDIT_ROLES:
        return
    if flash := st.session_state.pop('_jd_edit_flash', None):
        st.toast(flash, icon='✅')
        st.success(flash)
    active = st.session_state.get('_jd_action_base')
    if active and active['card_id'] != jd['id']:
        st.session_state.pop('_jd_action_base', None)
        active = None
    if active and active['version'] != jd['version']:
        st.warning('تغير إصدار البطاقة منذ فتح النموذج. لم يتم حفظ مدخلات الإصدار القديم.')
        if st.button('تحميل الإصدار الحالي وإغلاق النموذج القديم'):
            st.session_state.pop('_jd_action_base', None)
            st.rerun()
        return
    state = CardStatus.parse(jd['status'])
    token = f"{jd['id']}_{jd['version']}"
    if state == CardStatus.APPROVED:
        st.warning('⚠️ البطاقة معتمدة رسمياً. لإجراء تعديلات، يجب إلغاء الاعتماد أولاً.')
        if st.button('🔄 إلغاء الاعتماد وفتح التعديل', key=f'revoke_open_{token}'):
            st.session_state['_jd_action_base'] = {'card_id': jd['id'], 'version': jd['version']}
            st.session_state[f'revoke_confirm_{token}'] = True
        if st.session_state.get(f'revoke_confirm_{token}'):
            with st.expander('تأكيد إلغاء اعتماد البطاقة', expanded=True):
                with st.form(f'revoke_form_{token}'):
                    reason = st.text_area('سبب إلغاء الاعتماد', key=f'revoke_reason_{token}')
                    confirm = st.form_submit_button('تأكيد إلغاء الاعتماد', type='primary')
                    cancel = st.form_submit_button('إلغاء')
                if cancel:
                    st.session_state.pop('_jd_action_base', None)
                    st.session_state.pop(f'revoke_confirm_{token}', None)
                    st.rerun()
                if confirm:
                    ok, message = _run_jd_workflow('revoke_jd_approval', jd['id'], principal['id'],
                                              principal['full_name'], reason, expected_version=jd['version'])
                    if ok:
                        st.session_state.pop('_jd_action_base', None)
                        st.session_state.pop(f'revoke_confirm_{token}', None)
                        st.session_state['_jd_edit_flash'] = message
                        st.session_state['_jd_saved_card_id'] = jd['id']
                        st.rerun()
                    st.error(message)
    elif state == CardStatus.DRAFT:
        if st.button('✏️ تعديل بيانات البطاقة', key=f'core_open_{token}'):
            st.session_state['_jd_action_base'] = {'card_id': jd['id'], 'version': jd['version']}
            st.session_state[f'core_edit_{token}'] = True
        if st.session_state.get(f'core_edit_{token}'):
            with st.expander('تعديل بيانات الوصف الوظيفي', expanded=True):
                with st.form(f'core_form_{token}'):
                    fields = {}
                    for name, label in (('title', 'المسمى الوظيفي'), ('department', 'الإدارة'),
                                        ('sector', 'القطاع'), ('reports_to', 'المسؤول المباشر')):
                        fields[name] = st.text_input(label, value=jd[name] or '', key=f'core_{name}_{token}')
                    fields['purpose'] = st.text_area('الهدف العام من الوظيفة', value=jd['purpose'] or '',
                                                     key=f'core_purpose_{token}')
                    fields['qualifications'] = st.text_area('المؤهلات العلمية ومتطلبات الخبرة والمهارات',
                        value=jd['qualifications'] or '', key=f'core_qualifications_{token}')
                    save = st.form_submit_button('حفظ بيانات البطاقة', type='primary')
                    cancel = st.form_submit_button('إلغاء التعديل')
                if cancel:
                    st.session_state.pop('_jd_action_base', None)
                    st.session_state.pop(f'core_edit_{token}', None)
                    st.rerun()
                if save:
                    changes = {name: value for name, value in fields.items() if value != (jd[name] or '')}
                    if not changes:
                        st.info('لا توجد تغييرات للحفظ.')
                    else:
                        ok, message = _run_jd_workflow('update_jd_core_info', jd['id'], principal['id'],
                            principal['full_name'], changes, expected_version=jd['version'])
                        if ok:
                            st.session_state.pop('_jd_action_base', None)
                            st.session_state.pop(f'core_edit_{token}', None)
                            st.session_state['_jd_edit_flash'] = message
                            st.session_state['_jd_saved_card_id'] = jd['id']
                            st.rerun()
                        st.error(message)

    if state in (CardStatus.DRAFT, CardStatus.PENDING_REVIEW):
        render_full_jd_editor(jd, principal, _run_jd_workflow)


def render_jd_detail_fields(jd):
    if any(jd.get(name) for name in DETAIL_FIELDS):
        st.markdown('#### الهيكل التنظيمي ومتطلبات الوظيفة التفصيلية')
        for name, label in DETAIL_FIELDS.items():
            if jd.get(name):
                st.markdown(f'**{label}**')
                st.text(jd[name])


def render_admin_settings():
    """Render only for a freshly verified administrator, never a cached UI role."""
    principal = auth.get_authenticated_user()
    if not principal or st.session_state.get('user', {}).get('role') != 'admin':
        st.error('هذه اللوحة متاحة لمسؤول النظام فقط.')
        st.stop()
    actor_id = principal['id']
    for key in st.session_state.pop('_admin_clear_keys', []):
        st.session_state.pop(key, None)
    st.subheader('⚙️ لوحة الإدارة والإعدادات')
    if message := st.session_state.pop('_admin_flash', None):
        st.success(message)

    summary = _run_write(database.get_admin_system_summary, actor_id=actor_id)
    for column, (label, key) in zip(st.columns(4), (
            ('بطاقات الوصف', 'cards'), ('إجمالي المسؤوليات', 'responsibilities'),
            ('المقابلات', 'interviews'), ('المستخدمون', 'users'))):
        column.metric(label, summary[key])

    users_tab, backups_tab = st.tabs(['المستخدمون والصلاحيات', 'النسخ الاحتياطي'])
    with users_tab:
        roles = ROLE_LABELS
        st.markdown('#### إضافة مستخدم جديد')
        st.caption('كلمة المرور من 12 إلى 1024 حرفاً. الحساب الجديد لا يحصل على بطاقة مخصصة تلقائياً.')
        with st.form('admin_create_user', clear_on_submit=True):
            username = st.text_input('اسم المستخدم الجديد', max_chars=100, key='admin_new_username')
            full_name = st.text_input('الاسم الكامل', max_chars=150, key='admin_new_full_name')
            role = st.selectbox('الدور الوظيفي', list(roles), format_func=roles.get, key='admin_new_role')
            password = st.text_input('كلمة المرور للمستخدم الجديد', type='password', key='admin_new_password')
            if st.form_submit_button('إضافة المستخدم', type='primary'):
                st.session_state['_admin_clear_keys'] = [
                    'admin_new_username', 'admin_new_full_name', 'admin_new_role', 'admin_new_password']
                _run_write(database.create_new_user, username, full_name, role, password, actor_id=actor_id)
                st.session_state['_admin_flash'] = 'تم إنشاء المستخدم بنجاح.'
                st.rerun()

        users = _run_write(database.get_all_users, actor_id=actor_id)
        st.markdown('#### دليل المستخدمين')
        render_table(pd.DataFrame([{
            'المعرف': account['id'], 'اسم المستخدم': account['username'], 'الاسم الكامل': account['full_name'],
            'الدور': roles.get(account['role'], 'غير معروف'), 'حالة الحساب': 'نشط' if account['is_active'] else 'معطل',
            'تاريخ الإنشاء': format_timestamp(account['created_at']),
        } for account in users]))
        if users:
            by_id = {account['id']: account for account in users}
            selected_id = st.selectbox('اختر الحساب لإدارته', list(by_id),
                                       format_func=lambda uid: f"#{uid} — {by_id[uid]['full_name']} ({by_id[uid]['username']})",
                                       key='admin_selected_user')
            selected = by_id[selected_id]
            if selected_id == actor_id:
                st.caption('إعادة تعيين كلمة مرور حسابك تتطلب تسجيل الدخول مجدداً. لا يمكنك تعطيل حسابك الحالي.')
            with st.form(f'admin_reset_password_{selected_id}', clear_on_submit=True):
                replacement = st.text_input('كلمة المرور البديلة', type='password', key=f'admin_reset_secret_{selected_id}')
                if st.form_submit_button('إعادة تعيين كلمة المرور'):
                    st.session_state['_admin_clear_keys'] = [f'admin_reset_secret_{selected_id}']
                    _run_write(database.admin_reset_password, selected_id, replacement, actor_id=actor_id)
                    st.session_state['_admin_flash'] = 'تمت إعادة تعيين كلمة المرور وإبطال الجلسات السابقة.'
                    st.rerun()
            toggle_label = 'تعطيل الحساب' if selected['is_active'] else 'تفعيل الحساب'
            if st.button(toggle_label, key=f'admin_toggle_{selected_id}', disabled=selected_id == actor_id):
                active = _run_write(database.toggle_user_status, selected_id, actor_id=actor_id,
                                    expected_active=bool(selected['is_active']))
                st.session_state['_admin_flash'] = 'تم تفعيل الحساب.' if active else 'تم تعطيل الحساب وإبطال جلساته.'
                st.rerun()

    with backups_tab:
        st.markdown('#### النسخ الاحتياطي اليدوي')
        if st.button('إنشاء نسخة احتياطية SHA-256', key='admin_manual_backup'):
            st.session_state['_admin_backup_receipt'] = _run_write(database.create_manual_backup, actor_id=actor_id)
        if receipt := st.session_state.get('_admin_backup_receipt'):
            st.success('تم إنشاء النسخة الاحتياطية والتحقق من سلامتها.')
            st.text(receipt['name'])
            st.code(receipt['sha256'], language=None)


# Page configuration
st.set_page_config(
    page_title="ثري إس للأمن | منظومة الوصف الوظيفي 2027",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global Arabic RTL styling
import importlib
importlib.reload(utils)
st.markdown(utils.get_custom_css(), unsafe_allow_html=True)

# Initialize database and seed data
try:
    database.init_db()
except (OSError, sqlite3.Error, RuntimeError):
    logging.getLogger(__name__).exception("Database startup/backup failed")
    st.error("تعذر التحقق من قاعدة البيانات والنسخة الاحتياطية. يرجى التواصل مع مسؤول النظام.")
    st.stop()

# Render authentication in sidebar
auth.render_auth_sidebar()

# Check if user is logged in
if not st.session_state.logged_in:
    # Landing page for unauthenticated visitors
    st.markdown("""
    <div class="brand-header" style="box-sizing: border-box; width: 100%; max-width: 100%; overflow: visible;">
        <div style="min-width: 0; max-width: 100%; box-sizing: border-box;">
            <div class="brand-title">🛡️ شركة ثري إس للأنظمة الأمنية (3S Security)</div>
            <div class="brand-subtitle">بوابة حوكمة ومراجعة واعتماد بطاقات الوصف والتوصيف الوظيفي — خطة 2027</div>
        </div>
        <div style="text-align: left; flex-shrink: 0; max-width: 100%; box-sizing: border-box;">
            <span class="status-badge badge-pending" style="font-size: 0.95rem; padding: 6px 16px;">النسخة المؤسسية المعتمدة</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2], gap="large")
    with col1:
        st.markdown("""
        ### مرحباً بكم في البوابة الرقمية لبطاقات الوصف الوظيفي
        تم تصميم هذه المنظومة خصيصاً لتيسير وميكنة دورة العمل الخاصة بمراجعة وتحديث وتدقيق وتوثيق بطاقات الوصف الوظيفي لكافة إدارات وقطاعات الشركة، مع الحفاظ على سجل تاريخي لكافة التعديلات المعتمدة.
        
        #### 🌟 أبرز مميزات المنظومة:
        - **تكامل ذكي مع ملفات Word (.docx)**: استخراج ومعالجة بيانات بطاقات الوصف المعتمدة وتقسيمها آلياً إلى أقسام وجداول واضحة.
        - **صلاحيات وأدوار وظيفية محددة**:
          - **مديرو الإدارات والموظفون (Role A)**: الاطلاع على بطاقة الوصف المخصصة، اعتمادها كما هي بنقرة واحدة، أو طلب تعديل أي بند مع ذكر المبرر الفني.
          - **إدارة الموارد البشرية والإدارة العليا (Role B)**: فحص طلبات التعديل عبر شاشة مقارنة بصرية جنباً إلى جنب (النص القديم مقابل المقترح)، قبول أو رفض التعديلات، ورفع ملفات جديدة.
        - **متابعة جدول المقابلات الميدانية**: ربط مباشر مع جدول مقابلات ومخرجات مناقشة الوصف الوظيفي لمديري الإدارات.
        - **تصدير وطباعة رسمية**: إمكانية تنزيل بطاقات الوصف المعتمدة كملفات Word منسقة باللغة العربية وجاهزة للتوقيع والطباعة.
        """)
        
        st.info("👈 **يرجى تسجيل الدخول من القائمة الجانبية (يمين الشاشة)**. يجب إدخال اسم المستخدم وكلمة المرور الخاصة بك للوصول إلى صلاحياتك المعتمدة.")

    with col2:
        stats = database.get_dashboard_stats()
        st.markdown(f"""
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 22px; box-shadow: 0 4px 10px rgba(0,0,0,0.04); direction: rtl; text-align: right; box-sizing: border-box; width: 100%; max-width: 100%; overflow: visible;">
            <h4 style="margin-top: 0; color: #1e3a8a; font-weight: 800; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">📊 مؤشرات المنظومة العامة</h4>
            <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 15px; width: 100%; max-width: 100%; box-sizing: border-box;">
                <div class="metric-card">
                    <div class="metric-value">{stats['total_jds']}</div>
                    <div class="metric-label">إجمالي بطاقات الوصف</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats['departments_count']}</div>
                    <div class="metric-label">الإدارات والقطاعات</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #2563eb;">{stats['pending_mods']}</div>
                    <div class="metric-label">طلبات التعديل المعلقة</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #059669;">{stats['approved_jds']}</div>
                    <div class="metric-label">البطاقات المعتمدة</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# --- LOGGED IN USER INTERFACE ---
user = auth.get_authenticated_user()
if user is None:
    st.stop()
is_admin = (st.session_state['user']['role'] == 'admin')
is_manager = (user['role'] == 'manager')
stats = database.get_dashboard_stats()

# Header Banner
st.markdown(f"""
<div class="brand-header" style="box-sizing: border-box; width: 100%; max-width: 100%; overflow: visible;">
    <div style="min-width: 0; max-width: 100%; box-sizing: border-box;">
        <div class="brand-title">🛡️ ثري إس للأنظمة الأمنية</div>
        <div class="brand-subtitle">بوابة حوكمة بطاقات الوصف الوظيفي · 2027</div>
    </div>
    <div style="text-align: left; flex-shrink: 0; max-width: 100%; box-sizing: border-box;">
        <span class="status-badge {'badge-approved' if is_admin else 'badge-pending'}" style="font-size: 0.9rem; padding: 6px 16px;">
            {ROLE_LABELS[user['role']]}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# ADMIN / HR MANAGER (ROLE B) INTERFACE
# -------------------------------------------------------------
if user['role'] in JD_EDIT_ROLES:
    available_pages = ADMIN_PAGES if is_admin else {'directory': ADMIN_PAGES['directory']}
    if st.session_state.get('primary_navigation') not in available_pages.values():
        st.session_state.pop('primary_navigation', None)
    selected_page = st.sidebar.radio('التنقل الرئيسي', list(available_pages.values()), key='primary_navigation')
    page = next(key for key, label in available_pages.items() if label == selected_page)

    if page == 'settings':
        render_admin_settings()

    # --- TAB 1: DASHBOARD & METRICS ---
    if page == 'dashboard':
        st.subheader("مؤشرات الإنجاز وموقف مراجعة بطاقات الوصف الوظيفي")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats['total_jds']}</div>
                <div class="metric-label">إجمالي بطاقات الوصف الوظيفي</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #059669;">{stats['approved_jds']}</div>
                <div class="metric-label">البطاقات المعتمدة نهائياً</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #d97706;">{stats['under_review']}</div>
                <div class="metric-label">بطاقات قيد المراجعة</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #2563eb;">{stats['pending_mods']}</div>
                <div class="metric-label">طلبات تعديل بانتظار المراجعة</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_left, col_right = st.columns([3, 2])
        with col_left:
            st.markdown("#### 🏢 توزيع البطاقات الوظيفية حسب الإدارات")
            all_jds = database.get_all_jds()
            df_jds = pd.DataFrame(all_jds)
            if not df_jds.empty:
                dept_counts = df_jds['department'].replace('', 'الإدارة العامة').value_counts().reset_index()
                dept_counts.columns = ['الإدارة / القطاع', 'عدد بطاقات الوصف الوظيفي']
                dept_counts.index = dept_counts.index + 1
                render_table(dept_counts)
        
        with col_right:
            st.markdown("#### ⚡ إجراءات الموارد البشرية السريعة")
            if stats['pending_mods'] > 0:
                st.warning(f"🔔 يوجد حالياً **{stats['pending_mods']} طلب تعديل معلق** بحاجة لمراجعة واعتماد مدير الموارد البشرية.")
            else:
                st.success("✅ جميع طلبات التعديل محدثة ومراجعة بالكامل.")
            
            st.markdown("""
            - انتقل إلى **مراجعة واعتماد التعديلات** لمقارنة التعديلات المقترحة جنباً إلى جنب مع إبراز الفروقات اللونية.
            - انتقل إلى **رفع بطاقة وورد جديدة** لاستيراد بطاقات مهام إضافية بصيغة Word.
            - انتقل إلى **جدول المقابلات** لتسجيل مخرجات اجتماعات مديري الإدارات.
            """)

    # --- TAB 2: REVIEW MODIFICATIONS (SIDE-BY-SIDE DIFF) ---
    if page == 'reviews':
        st.subheader("⚖️ شاشة مراجعة واعتماد طلبات التعديل المقترحة")
        st.markdown("تتيح هذه الشاشة لمدير الموارد البشرية والإدارة العليا فحص التعديلات المقترحة على أي بند أو مسؤولية وظيفية، مع مقارنة بصرية دقيقة بين النص الحالي والنص المقترح.")

        pending_requests = database.get_pending_modification_requests()

        if not pending_requests:
            st.success("🎉 لا توجد طلبات تعديل معلقة في الوقت الحالي!")
        else:
            st.info(f"يوجد حالياً **{len(pending_requests)} طلب(ات) بانتظار القرار**:")

            for req in pending_requests:
                with st.expander(f"📌 طلب رقم #{req['id']}: [{req['jd_title']}] — البند: {req['section_name']} (مقدم الطلب: {req['requested_by']})", expanded=True):
                    col_meta1, col_meta2, col_meta3 = st.columns(3)
                    col_meta1.markdown(f"**الوصف الوظيفي:** {req['jd_title']}")
                    col_meta2.markdown(f"**مقدم الطلب:** `{req['requested_by']}`")
                    col_meta3.markdown(f"**تاريخ تقديم الطلب:** {format_timestamp(req['requested_at'])}")

                    st.markdown("---")
                    st.markdown("#### 🔍 المقارنة جنباً إلى جنب (النص وقت تقديم الطلب مقابل التعديل المقترح)")
                    
                    diff_col1, diff_col2 = st.columns(2)
                    with diff_col1:
                        st.markdown(f"**النص وقت تقديم الطلب — الإصدار {req['expected_version'] or 'غير موثق'}:**")
                        st.markdown(f"""
                        <div class="diff-box diff-old">
                            {req['original_text'] or '<i>(البند فارغ أو مضاف حديثاً)</i>'}
                        </div>
                        """, unsafe_allow_html=True)

                    with diff_col2:
                        st.markdown("**التعديل الجديد المقترح من الموظف/المدير:**")
                        st.markdown(f"""
                        <div class="diff-box diff-new">
                            {req['proposed_text']}
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("#### 💡 الفروقات المحددة بصرياً (إضافة / حذف)")
                    diff_html = utils.generate_diff_html(req['original_text'], req['proposed_text'])
                    st.markdown(f"""
                    <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; margin-bottom: 12px; direction: rtl; text-align: right;">
                        {diff_html}
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"""
                    <div style="background-color: #eff6ff; border-right: 5px solid #2563eb; padding: 12px 16px; border-radius: 6px; margin-bottom: 14px; direction: rtl; text-align: right;">
                        <b>💬 مبررات وأسباب التعديل المقدمة:</b> {req['justification']}
                    </div>
                    """, unsafe_allow_html=True)

                    # HR Decision Form
                    with st.form(f"decision_form_{req['id']}"):
                        reviewer_notes = st.text_input("ملاحظات وتوجيهات مدير الموارد البشرية (اختياري)", placeholder="أدخل أية توجيهات أو قرارات توثق في سجل التعديلات...")
                        col_btn1, col_btn2, _ = st.columns([1, 1, 2])
                        
                        btn_accept = col_btn1.form_submit_button("✅ قبول واعتماد التعديل", type="primary", use_container_width=True)
                        btn_reject = col_btn2.form_submit_button("❌ رفض التعديل", use_container_width=True)

                        if btn_accept:
                            success, msg = _run_write(database.review_modification_request,
                                request_id=req['id'],
                                decision="Accept",
                                reviewer_comments=reviewer_notes,
                                actor_id=user['id']
                            )
                            if success:
                                st.success("تم اعتماد التعديل وتحديث بطاقة الوصف الوظيفي وسجل التاريخ بنجاح!")
                                st.rerun()
                            else:
                                st.error(msg)

                        if btn_reject:
                            success, msg = _run_write(database.review_modification_request,
                                request_id=req['id'],
                                decision="Reject",
                                reviewer_comments=reviewer_notes,
                                actor_id=user['id']
                            )
                            if success:
                                st.warning("تم رفض طلب التعديل وتسجيل القرار في النظام.")
                                st.rerun()
                            else:
                                st.error(msg)

    # --- TAB 3: UPLOAD NEW JD (.docx) ---
    if page == 'import':
        st.subheader("📤 رفع بطاقات وصف وظيفي جديدة بصيغة Word (.docx)")
        st.markdown("""
        يمكن لمسؤول النظام رفع ملفات Word إضافية تتبع النموذج الرسمي المعتمد لشركة **ثري إس للأنظمة الأمنية**.
        يقوم النظام آلياً بقراءة وتحليل وترجمة كافة البنود العشرة للبطاقة وإدراجها فوراً في قاعدة البيانات باللغة العربية.
        """)

        uploaded_files = st.file_uploader(
            "اختر ملف أو عدة ملفات بصيغة Word (.docx) للرفع والاستيراد",
            type=["docx"],
            accept_multiple_files=True,
            max_upload_size=upload_limit_megabytes()
        )

        if uploaded_files:
            st.markdown(f"**تم اختيار {len(uploaded_files)} ملف(ات) للمعالجة.**")

            for upload_index, uploaded_file in enumerate(uploaded_files):
                safe_name = sanitize_docx_filename(uploaded_file.name)
                st.markdown("---")
                with st.expander(f"📄 معاينة استخراج البيانات من: {safe_name}", expanded=True):
                    try:
                        parsed_data = docx_parser.parse_jd_docx(uploaded_file)

                        # Auto-translate title and department for preview
                        title_preview = database.TITLE_MAP.get(parsed_data['title'], parsed_data['title'])
                        dept_preview = database.DEPT_MAP.get(parsed_data['department'], parsed_data['department'] or 'الإدارة العامة')
                        rep_preview = database.REPORTS_MAP.get(parsed_data['reports_to'], parsed_data['reports_to'] or 'الإدارة العليا')

                        p_col1, p_col2, p_col3 = st.columns(3)
                        p_col1.markdown(f"**المسمى الوظيفي:** {title_preview}")
                        p_col2.markdown(f"**الإدارة:** {dept_preview}")
                        p_col3.markdown(f"**المسؤول المباشر:** {rep_preview}")

                        st.markdown(f"**الهدف العام من الوظيفة:** {parsed_data['purpose'][:250]}..." if len(parsed_data['purpose']) > 250 else f"**الهدف العام من الوظيفة:** {parsed_data['purpose']}")
                        st.markdown(f"**عدد المسؤوليات والواجبات المستخرجة:** `{len(parsed_data['accountabilities'])}` بند")

                        if parsed_data['accountabilities']:
                            preview_rows = []
                            for idx, a in enumerate(parsed_data['accountabilities'][:4]):
                                preview_rows.append({
                                    "م": idx + 1,
                                    "بيان المسؤولية والواجب الوظيفي": a['description'],
                                    "مؤشر قياس الأداء (KPI)": a['kpi'] or '—'
                                })
                            render_table(pd.DataFrame(preview_rows))

                        # Confirmation button to insert into DB
                        if st.button(f"💾 تأكيد وإدراج بطاقة '{title_preview}' في قاعدة البيانات", key=f"btn_import_{upload_index}_{safe_name}"):
                            new_jd_id = _run_write(database.create_or_update_jd,
                                parsed_jd=parsed_data,
                                source_file=parsed_data['file_name'],
                                actor_id=user['id']
                            )
                            st.success(f"تم إدراج بطاقة الوصف الوظيفي '{title_preview}' بنجاح برقم #{new_jd_id}!")
                            st.rerun()

                    except ValueError as exc:
                        st.error(f"تعذر استيراد الملف {safe_name}: {exc}")
                    except Exception:
                        logging.getLogger(__name__).exception('DOCX import failed')
                        st.error(f"تعذر استيراد الملف {safe_name}. يرجى التحقق من الملف والمحاولة مجدداً.")

    # --- TAB 4: JOB DESCRIPTIONS EXPLORER ---
    if page == 'directory':
        st.subheader("📁 الدليل الشامل لبطاقات الوصف الوظيفي")
        all_jds = database.get_all_jds()
        saved_card_id = st.session_state.pop('_jd_saved_card_id', None)
        if saved_card_id is not None:
            st.session_state['directory_jd_id'] = saved_card_id
            st.session_state['directory_search'] = ''
            st.session_state['directory_department'] = 'كافة الإدارات'
            st.session_state['directory_status'] = 'كافة الحالات'

        fcol1, fcol2, fcol3 = st.columns([3, 2, 2])
        search_kw = fcol1.text_input("🔍 البحث باسم الوظيفة أو الكلمات المفتاحية", placeholder="مثال: مشروعات، مبيعات، جودة، مخازن...", key='directory_search')
        
        dept_list = ["كافة الإدارات"] + sorted(list({j['department'] for j in all_jds if j['department']}))
        selected_dept = fcol2.selectbox("تصفية حسب الإدارة", dept_list, key='directory_department')
        
        status_list = ["كافة الحالات", *(status.value for status in CardStatus)]
        selected_status = fcol3.selectbox("تصفية حسب حالة الاعتماد", status_list, key='directory_status')

        filtered_jds = all_jds
        if search_kw:
            filtered_jds = [j for j in filtered_jds if search_kw.lower() in j['title'].lower() or search_kw.lower() in (j['department'] or '').lower()]
        if selected_dept != "كافة الإدارات":
            filtered_jds = [j for j in filtered_jds if j['department'] == selected_dept]
        if selected_status != "كافة الحالات":
            filtered_jds = [j for j in filtered_jds if j['status'] == selected_status]

        st.caption(f"يتم عرض **{len(filtered_jds)}** من أصل **{len(all_jds)}** بطاقة وصف وظيفي")

        jd_options = {j['id']: f"#{j['id']} — {j['title']} ({j['department'] or 'الإدارة العامة'})" for j in filtered_jds}
        
        if jd_options:
            if st.session_state.get('directory_jd_id') not in jd_options:
                st.session_state.pop('directory_jd_id', None)
            chosen_jd_id = st.selectbox("اختر بطاقة الوصف الوظيفي لعرض كافة تفاصيلها:", list(jd_options),
                                        format_func=jd_options.get, key='directory_jd_id')
            jd = database.get_jd_by_id(chosen_jd_id)
            accountabilities = database.get_accountabilities(chosen_jd_id)

            render_jd_edit_actions(jd, user)

            st.markdown("---")
            head_col1, head_col2 = st.columns([3, 1])
            with head_col1:
                st.markdown(f"### {jd['title']}")
                st.markdown(f"**الإدارة:** {jd['department'] or '—'} | **القطاع:** {jd['sector'] or '—'} | **المسؤول المباشر:** {jd['reports_to'] or '—'}")
            with head_col2:
                badge_style = "badge-approved" if jd['status'] == 'معتمد' else "badge-under-review"
                st.markdown(f"""
                <div style="text-align: left; padding-top: 10px;">
                    <span class="status-badge {badge_style}" style="font-size: 0.95rem; padding: 6px 14px;">{jd['status']}</span>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">الإصدار: {jd['version']}</div>
                </div>
                """, unsafe_allow_html=True)

            # Export Word Document Button in Arabic
            doc_stream = docx_parser.export_jd_to_docx(*database.get_export_data(jd['id']))
            st.download_button(
                label=f"📥 تحميل بطاقة '{jd['title']}' كملف Word منسق (.docx)",
                data=doc_stream,
                file_name=download_filename(jd),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary"
            )

            # Render 10 Arabic sections
            sec1, sec2 = st.columns(2)
            with sec1:
                st.markdown("""<div class="jd-section-card"><div class="jd-section-title">١. بيانات وبطاقة الوظيفة</div>""", unsafe_allow_html=True)
                st.write(f"- **كود الوظيفة:** {jd['job_code'] or 'غير مسجل'} | **معرف المنصة:** {jd['id']}")
                st.write(f"- **المسمى الوظيفي:** {jd['title']}")
                st.write(f"- **الإدارة التابع لها:** {jd['department'] or '—'}")
                st.write(f"- **المسؤول المباشر:** {jd['reports_to'] or '—'}")
                st.write(f"- **القطاع:** {jd['sector'] or 'الإدارة العامة والمجموعة'}")
                st.markdown("</div>", unsafe_allow_html=True)

            with sec2:
                st.markdown("""<div class="jd-section-card"><div class="jd-section-title">٢. أبعاد الوظيفة والنطاق الإشرافي</div>""", unsafe_allow_html=True)
                st.write(jd['dimensions'] or "النطاق الإشرافي المعتمد للإدارة.")
                st.markdown("</div>", unsafe_allow_html=True)

            # Purpose
            st.markdown(f"""
            <div class="jd-section-card">
                <div class="jd-section-title">٣. الهدف العام من الوظيفة</div>
                <div style="white-space: pre-line;">{escape(jd['purpose'] or 'لم يتم إدراج بيان الهدف العام بعد.')}</div>
            </div>
            """, unsafe_allow_html=True)

            # Accountabilities Table RTL
            st.markdown("""<div class="jd-section-card"><div class="jd-section-title">٤. المسؤوليات والواجبات الرئيسية ومؤشرات قياس الأداء (KPIs)</div>""", unsafe_allow_html=True)
            if accountabilities:
                acc_rows = []
                for a in accountabilities:
                    acc_rows.append({
                        "م": a['item_order'],
                        "بيان المسؤولية والواجب الوظيفي": a['description'],
                        "مؤشر قياس الأداء (KPI)": a['kpi'] or '—'
                    })
                render_table(pd.DataFrame(acc_rows))
            else:
                st.info("لا توجد مسؤوليات مسجلة.")
            st.markdown("</div>", unsafe_allow_html=True)

            # Frameworks & Authority
            if jd['frameworks']:
                st.markdown(f"""
                <div class="jd-section-card">
                    <div class="jd-section-title">٥. إطار العمل وحدود اتخاذ القرارات والصلاحيات</div>
                    <div style="white-space: pre-line;">{jd['frameworks']}</div>
                </div>
                """, unsafe_allow_html=True)

            # Qualifications
            if jd['qualifications']:
                st.markdown(f"""
                <div class="jd-section-card">
                    <div class="jd-section-title">٦. المؤهلات والخبرات والمهارات المطلوبة</div>
                    <div style="white-space: pre-line;">{escape(jd['qualifications'])}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('#### الجدارات والكفاءات والمعايير السلوكية والفنية')
            st.write(jd['competencies'] or 'غير مسجلة')
            render_jd_detail_fields(jd)
            st.markdown('#### بيانات الاعتماد الواردة في المصدر')
            st.write(jd['approvals'] or 'غير مسجلة')

            # Hazards & Relations
            c_haz1, c_haz2 = st.columns(2)
            with c_haz1:
                st.markdown(f"""
                <div class="jd-section-card">
                    <div class="jd-section-title">٧. مخاطر الوظيفة وممارسات السلامة والصحة المهنية</div>
                    <b>المخاطر المهنية:</b> {jd['hazards'] or 'بيئة عمل مكتبية اعتيادية ومخاطر استخدام الحاسب الآلي'}<br>
                    <b>إجراءات السلامة:</b> {jd['safe_practices'] or 'توفير التجهيزات المكتبية المناسبة والالتزام بإرشادات السلامة'}
                </div>
                """, unsafe_allow_html=True)
            with c_haz2:
                st.markdown(f"""
                <div class="jd-section-card">
                    <div class="jd-section-title">٨. شبكة العلاقات والاتصال الوظيفي</div>
                    <b>الاتصال الداخلي:</b> {jd['internal_relations'] or 'كافة إدارات وأقسام الشركة ذات الصلة'}<br>
                    <b>الاتصال الخارجي:</b> {jd['external_relations'] or 'العملاء، الموردين، والجهات الحكومية والرقابية'}
                </div>
                """, unsafe_allow_html=True)

    # --- TAB 5: AUDIT TRAIL & VERSION HISTORY ---
    if page == 'audit':
        st.subheader("📜 سجل التعديلات التاريخي وتتبع النسخ (Audit Trail)")
        st.markdown("سجل رقمي غير قابل للتعديل يوثق كل عملية اعتماد، تعديل بند، أو استيراد مع تسجيل الوقت والمستخدم والنص قبل وبعد التعديل.")

        audit_records = database.get_audit_trail()
        if audit_records:
            st.caption('يمكن تمرير الجدول أفقياً أو فتحه بملء الشاشة. اختر سجلاً أسفله لقراءة جميع التفاصيل دون اختصار.')
            render_table(audit_dataframe(audit_records), column_config=audit_column_config(),
                         key='audit_table', row_height=88)

            st.markdown("#### 🔎 فحص ومقارنة نص تعديل محدد")
            selected_audit_id = st.selectbox(
                "اختر سجل التعديل لعرض النص القديم مقابل النص الجديد:",
                options=[r['id'] for r in audit_records],
                format_func=lambda x: next(f"سجل #{r['id']} - {format_timestamp(r['changed_at'])} | {r['jd_title']} | {arabic_action(r['action'])}" for r in audit_records if r['id'] == x)
            )

            rec = next((r for r in audit_records if r['id'] == selected_audit_id), None)
            if rec:
                st.markdown('#### تفاصيل السجل كاملة')
                st.text(f"{rec['jd_title']} · {arabic_field(rec['section_name'])} · {arabic_action(rec['action'])}")
                st.caption(f"تاريخ ووقت التعديل: {format_timestamp(rec['changed_at'])}")
                st.text(readable_notes(rec['notes']))
            if rec and (rec['old_text'] or rec['new_text']):
                c_old, c_new = st.columns(2)
                with c_old:
                    st.markdown("**النص قبل التعديل:**")
                    st.markdown(f"""<div class="diff-box diff-old">{escape(rec['old_text']).replace(chr(10), '<br>') if rec['old_text'] else '<i>(لا يوجد)</i>'}</div>""", unsafe_allow_html=True)
                with c_new:
                    st.markdown("**النص المعتمد بعد التعديل:**")
                    st.markdown(f"""<div class="diff-box diff-new">{escape(rec['new_text']).replace(chr(10), '<br>') if rec['new_text'] else '<i>(لا يوجد)</i>'}</div>""", unsafe_allow_html=True)
        else:
            st.info("لا توجد سجلات تعديل حتى الآن.")

    # --- TAB 6: INTERVIEW SCHEDULE ---
    if page == 'interviews':
        st.subheader("📅 جدول مقابلات مناقشة واعتماد الوصف الوظيفي لمديري الإدارات")
        st.markdown("متابعة الاجتماعات والمقابلات المنسقة مع السادة مديري الإدارات لمناقشة محاور التكامل واعتماد البطاقات النهائية وفقاً للمخطط الرئيسي.")

        schedule_items = database.get_interview_schedule()
        if schedule_items:
            sch_display = []
            for it in schedule_items:
                sch_display.append({
                    "م": it['seq_num'],
                    "الإدارة / القطاع": it['department'],
                    "المدير المسؤول": it['manager_name'],
                    "اليوم والتاريخ": it['day_date'],
                    "وقت المقابلة": it['meeting_time'] or 'غير محدد',
                    "حالة المقابلة": it['status'],
                    "محاور النقاش الرئيسية والتكامل المطلوب": it['discussion_topics'],
                    "ملاحظات ومخرجات الاجتماع": it['notes'] or '—'
                })
            render_table(pd.DataFrame(sch_display))

            st.markdown("#### ✏️ تحديث حالة المقابلة وتوثيق المخرجات")
            item_options = {f"#{it['seq_num']}: {it['department']} - {it['manager_name']}": it['id'] for it in schedule_items}
            chosen_item_label = st.selectbox("اختر المقابلة / الإدارة المستهدفة", list(item_options.keys()))
            chosen_id = item_options[chosen_item_label]
            selected_interview = next(it for it in schedule_items if it['id'] == chosen_id)
            base_key = f'interview_base_{chosen_id}'
            if st.button('إعادة تحميل بيانات المقابلة'):
                st.session_state.pop(base_key, None)
                st.session_state.pop(f'interview_status_{chosen_id}', None)
                st.session_state.pop(f'interview_notes_{chosen_id}', None)
                st.rerun()
            interview_base = st.session_state.setdefault(base_key, {
                'status': selected_interview['status'], 'notes': selected_interview['notes']})
            statuses = list(dict.fromkeys([selected_interview['status'], *(status.value for status in InterviewStatus)]))
            with st.form(f"update_interview_form_{chosen_id}"):
                new_status = st.selectbox("حالة المقابلة الحالية", statuses, key=f'interview_status_{chosen_id}')
                interview_notes = st.text_area("الملاحظات ومخرجات الاجتماع المتفق عليها", value=selected_interview['notes'] or "", key=f'interview_notes_{chosen_id}')
                save_interview = st.form_submit_button("حفظ وتحديث حالة المقابلة", type="primary")
                if save_interview:
                    _run_write(database.update_interview_status, chosen_id,
                               new_status if new_status != interview_base['status'] else None,
                               interview_notes if interview_notes != (interview_base['notes'] or '') else None,
                               actor_id=user['id'], expected=interview_base)
                    st.session_state.pop(base_key, None)
                    st.success("تم تحديث حالة المقابلة وتوثيق المخرجات بنجاح!")
                    st.rerun()

# -------------------------------------------------------------
# EMPLOYEE / DEPARTMENT MANAGER (ROLE A) INTERFACE
# -------------------------------------------------------------
else:
    all_jds = database.get_all_jds()
    assigned_jd_id = user.get('assigned_jd_id')
    if st.session_state.get('primary_navigation') not in MEMBER_PAGES.values():
        st.session_state.pop('primary_navigation', None)
    selected_page = st.sidebar.radio('التنقل الرئيسي', list(MEMBER_PAGES.values()), key='primary_navigation')
    page = next(key for key, label in MEMBER_PAGES.items() if label == selected_page)
    available_ids = {card['id'] for card in all_jds}
    if page in ('card', 'export') and assigned_jd_id not in available_ids:
        st.info('لم يتم تخصيص بطاقة وصف وظيفي صالحة لحسابك. يرجى التواصل مع الموارد البشرية.')
        st.stop()
    current_jd_id = assigned_jd_id
    if is_manager and st.session_state.get('viewed_jd_id') in available_ids:
        current_jd_id = st.session_state['viewed_jd_id']
    jd = database.get_jd_by_id(current_jd_id) if current_jd_id in available_ids else None
    accountabilities = database.get_accountabilities(current_jd_id) if jd else []

    # --- TAB 1: MY JOB DESCRIPTION ---
    if page == 'card':
        if is_manager:
            col_sel1, col_sel2 = st.columns([3, 1])
            with col_sel1:
                jd_map = {f"{j['title']} ({j['department'] or 'الإدارة العامة'})": j['id'] for j in all_jds}
                default_index = list(jd_map.values()).index(current_jd_id) if current_jd_id in jd_map.values() else 0
                selected_label = st.selectbox("بطاقة الوصف الوظيفي المعروضة حالياً للمراجعة:", list(jd_map.keys()), index=default_index)
                current_jd_id = jd_map[selected_label]
                st.session_state['viewed_jd_id'] = current_jd_id
        else:
            current_jd_id = assigned_jd_id

        jd = database.get_jd_by_id(current_jd_id)
        accountabilities = database.get_accountabilities(current_jd_id)

        top_c1, top_c2 = st.columns([3, 1])
        with top_c1:
            st.markdown(f"## {jd['title']}")
            st.markdown(f"**الإدارة:** {jd['department'] or '—'} | **المسؤول المباشر:** {jd['reports_to'] or '—'} | **رقم الإصدار:** {jd['version']}")
        with top_c2:
            badge_class = "badge-approved" if jd['status'] == 'معتمد' else "badge-under-review"
            st.markdown(f"""
            <div style="text-align: left; padding-top: 15px;">
                <span class="status-badge {badge_class}" style="font-size: 1rem; padding: 6px 16px;">{jd['status']}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        can_write_card = current_jd_id == user['assigned_jd_id']
        if not can_write_card:
            st.info("هذه البطاقة متاحة للاستعراض. صلاحية الاعتماد وطلب التعديل تقتصر على البطاقة المخصصة لك.")

        # Approval & Modification Action Bar in Arabic
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            with st.expander("✅ الخيار الأول: اعتماد بطاقة الوصف الوظيفي كما هي", expanded=(jd['status'] != 'معتمد')):
                st.markdown("في حال كانت كافة المهام والمسؤوليات والصلاحيات والمؤهلات مطابقة تماماً لطبيعة عملكم، يرجى تأكيد الاعتماد النهائي للبطاقة.")
                appr_notes = st.text_input("ملاحظات الاعتماد والتوقيع (اختياري)", placeholder="مثال: تمت المراجعة والاتفاق في اجتماع مراجعة الوصف الوظيفي.")
                approval_key = f'approval_base_{current_jd_id}'
                approval_base = st.session_state.setdefault(approval_key, {
                    'expected_version': jd['version'], 'expected_hash': jd['review_hash']})
                if jd['status'] in ('مسودة', 'مرفوض') or (jd['status'] == 'قيد المراجعة' and not jd['review_hash']):
                    if st.button('إرسال الإصدار الحالي للمراجعة', disabled=not can_write_card):
                        _run_write(database.request_jd_review, current_jd_id, actor_id=user['id'])
                        st.session_state.pop(approval_key, None)
                        st.rerun()
                if st.button('إعادة تحميل بيانات المراجعة'):
                    st.session_state.pop(approval_key, None)
                    st.rerun()
                if st.button("تأكيد الاعتماد والموافقة النهائية", type="primary", use_container_width=True,
                             disabled=not can_write_card or jd['status'] != 'قيد المراجعة' or not jd['review_hash']):
                    _run_write(database.approve_jd_as_is, current_jd_id, actor_id=user['id'], comments=appr_notes, **approval_base)
                    st.session_state.pop(approval_key, None)
                    st.success("🎉 تم اعتماد بطاقة الوصف الوظيفي رسمياً بنجاح وتوثيق ذلك في سجل النظام!")
                    st.rerun()

        with col_act2:
            with st.expander("✏️ الخيار الثاني: طلب تعديل بند أو مسؤولية محددة مع ذكر المبرر", expanded=False):
                st.markdown("يمكنك اقتراح تعديل أو إعادة صياغة لأي بند أو مسؤولية. سيقوم مدير الموارد البشرية بفحص التعديل والموافقة عليه.")

                section_choices = [
                    "الهدف العام من الوظيفة",
                    "إطار العمل وحدود اتخاذ القرارات",
                    "المؤهلات والخبرات والمهارات",
                    "الجدارات والكفاءات",
                    "مخاطر الوظيفة",
                    "ممارسات السلامة والصحة المهنية",
                    "العلاقات الداخلية",
                    "العلاقات الخارجية"
                ]
                for a in accountabilities:
                    desc_snippet = (a['description'][:45] + "...") if len(a['description']) > 45 else a['description']
                    section_choices.append(f"المسؤولية #{a['item_order']}: {desc_snippet}")

                chosen_section = st.selectbox("اختر البند أو المسؤولية المراد طلب تعديلها:", section_choices)

                if chosen_section.startswith("المسؤولية #"):
                    acc_num = int(chosen_section.split(":")[0].replace("المسؤولية #", "").strip())
                    target_acc = next((a for a in accountabilities if a['item_order'] == acc_num), None)
                    current_clause_text = target_acc['description'] if target_acc else ""
                    clause_id_val = str(target_acc['id']) if target_acc else ""
                else:
                    clause_id_val = chosen_section
                    field_lookup = {
                        "الهدف العام من الوظيفة": jd['purpose'],
                        "إطار العمل وحدود اتخاذ القرارات": jd['frameworks'],
                        "المؤهلات والخبرات والمهارات": jd['qualifications'],
                        "الجدارات والكفاءات": jd['competencies'],
                        "مخاطر الوظيفة": jd['hazards'],
                        "ممارسات السلامة والصحة المهنية": jd['safe_practices'],
                        "العلاقات الداخلية": jd['internal_relations'],
                        "العلاقات الخارجية": jd['external_relations']
                    }
                    current_clause_text = field_lookup.get(chosen_section, "")

                st.markdown("**النص المعتمد الحالي للبند:**")
                st.text_area("النص الحالي (للقراءة فقط)", value=current_clause_text, height=90, disabled=True)

                with st.form(f"submit_mod_form_{current_jd_id}_{clause_id_val}"):
                    proposed_text_input = st.text_area("النص المقترح الجديد المطلوب اعتماده *", value=current_clause_text, height=120)
                    justification_input = st.text_area("المبرر الفني وسبب طلب التعديل *", placeholder="اشرح هنا سبب التعديل ومبرراته التنظيمية أو التشغيلية...")
                    
                    submit_mod_btn = st.form_submit_button("إرسال طلب التعديل إلى الموارد البشرية", type="primary", use_container_width=True, disabled=not can_write_card)

                    if submit_mod_btn:
                        if not proposed_text_input.strip():
                            st.error("لا يمكن ترك النص المقترح فارغاً.")
                        elif not justification_input.strip():
                            st.error("يرجى كتابة مبرر وسبب التعديل المطلوب.")
                        elif proposed_text_input.strip() == current_clause_text.strip():
                            st.warning("النص المقترح مطابق تماماً للنص الحالي دون تغيير.")
                        else:
                            req_id = _run_write(database.submit_modification_request,
                                jd_id=current_jd_id,
                                section_name=chosen_section,
                                clause_id=clause_id_val,
                                original_text=current_clause_text,
                                proposed_text=proposed_text_input,
                                justification=justification_input,
                                actor_id=user['id']
                            )
                            st.success(f"تم إرسال طلب التعديل بنجاح برقم #{req_id} وسيتم عرضه على الموارد البشرية!")
                            st.rerun()

        st.markdown("---")
        st.subheader("📖 البيانات الكاملة لبطاقة الوصف الوظيفي")

        col_jd1, col_jd2 = st.columns(2)
        with col_jd1:
            st.markdown("""<div class="jd-section-card"><div class="jd-section-title">١. بيانات وبطاقة الوظيفة</div>""", unsafe_allow_html=True)
            st.write(f"- **المسمى الوظيفي:** {jd['title']}")
            st.write(f"- **الإدارة:** {jd['department'] or '—'}")
            st.write(f"- **المسؤول المباشر:** {jd['reports_to'] or '—'}")
            st.write(f"- **القطاع:** {jd['sector'] or 'الإدارة العامة والمجموعة'}")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_jd2:
            st.markdown("""<div class="jd-section-card"><div class="jd-section-title">٢. أبعاد الوظيفة والنطاق الإشرافي</div>""", unsafe_allow_html=True)
            st.write(jd['dimensions'] or "النطاق الإشرافي المعتمد للإدارة.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="jd-section-card">
            <div class="jd-section-title">٣. الهدف العام من الوظيفة</div>
            <div style="white-space: pre-line;">{escape(jd['purpose'] or 'لم يتم إدراج بيان الهدف العام بعد.')}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""<div class="jd-section-card"><div class="jd-section-title">٤. المسؤوليات والواجبات الرئيسية ومؤشرات قياس الأداء (KPIs)</div>""", unsafe_allow_html=True)
        if accountabilities:
            acc_list = []
            for a in accountabilities:
                acc_list.append({
                    "م": a['item_order'],
                    "بيان المسؤولية والواجب الوظيفي": a['description'],
                    "مؤشر قياس الأداء (KPI)": a['kpi'] or '—'
                })
            render_table(pd.DataFrame(acc_list))
        else:
            st.info("لا توجد مسؤوليات مسجلة.")
        st.markdown("</div>", unsafe_allow_html=True)

        if jd['frameworks']:
            st.markdown(f"""
            <div class="jd-section-card">
                <div class="jd-section-title">٥. إطار العمل وحدود اتخاذ القرارات والصلاحيات</div>
                <div style="white-space: pre-line;">{jd['frameworks']}</div>
            </div>
            """, unsafe_allow_html=True)

        if jd['qualifications']:
            st.markdown(f"""
            <div class="jd-section-card">
                <div class="jd-section-title">٦. المؤهلات العلمية والخبرات والمهارات المطلوبة</div>
                <div style="white-space: pre-line;">{escape(jd['qualifications'])}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('#### الجدارات والكفاءات والمعايير السلوكية والفنية')
        st.write(jd['competencies'] or 'غير مسجلة')
        render_jd_detail_fields(jd)
        st.markdown('#### بيانات الاعتماد الواردة في المصدر')
        st.write(jd['approvals'] or 'غير مسجلة')

        hz_c1, hz_c2 = st.columns(2)
        with hz_c1:
            st.markdown(f"""
            <div class="jd-section-card">
                <div class="jd-section-title">٧. مخاطر الوظيفة وممارسات السلامة والصحة المهنية</div>
                <b>المخاطر المهنية:</b> {jd['hazards'] or 'بيئة عمل مكتبية اعتيادية ومخاطر استخدام الحاسب الآلي'}<br>
                <b>إجراءات السلامة:</b> {jd['safe_practices'] or 'توفير التجهيزات المكتبية المناسبة والالتزام بإرشادات السلامة'}
            </div>
            """, unsafe_allow_html=True)
        with hz_c2:
            st.markdown(f"""
            <div class="jd-section-card">
                <div class="jd-section-title">٨. شبكة العلاقات والاتصال الوظيفي</div>
                <b>الاتصال الداخلي:</b> {jd['internal_relations'] or 'كافة إدارات وأقسام الشركة ذات الصلة'}<br>
                <b>الاتصال الخارجي:</b> {jd['external_relations'] or 'العملاء، الموردين، والجهات الحكومية والرقابية'}
            </div>
            """, unsafe_allow_html=True)

    # --- TAB 2: MY MODIFICATION REQUESTS ---
    if page == 'requests':
        st.subheader("📬 متابعة طلبات التعديل المقدمة من طرفي")
        my_reqs = database.get_requests_by_user(user['full_name'])

        if not my_reqs:
            st.info("لم تقم بتقديم أية طلبات تعديل حتى الآن. يمكنك تقديم طلبات مباشرة من تبويب 'بطاقة الوصف الوظيفي الخاصة بي'.")
        else:
            for r in my_reqs:
                badge_type = "badge-approved" if r['status'] == 'مقبول' else ("badge-rejected" if r['status'] == 'مرفوض' else "badge-under-review")
                with st.expander(f"طلب #{r['id']} — {r['section_name']} ({r['status']}) - {format_timestamp(r['requested_at'])}", expanded=True):
                    st.markdown(f"**الوصف الوظيفي المستهدف:** {r['jd_title']}")
                    st.markdown(f"**حالة الطلب:** <span class='status-badge {badge_type}'>{r['status']}</span>", unsafe_allow_html=True)
                    st.markdown(f"**المبرر الفني المقدم:** {r['justification']}")
                    
                    if r['reviewer_comments']:
                        st.markdown(f"""
                        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 12px; border-radius: 6px; margin-top: 10px; direction: rtl; text-align: right;">
                            <b>رد وقرار الموارد البشرية ({r['reviewed_by']}):</b> {r['reviewer_comments']}
                        </div>
                        """, unsafe_allow_html=True)

                    c_o, c_p = st.columns(2)
                    with c_o:
                        st.markdown("**النص الأصلي السابق:**")
                        st.markdown(f"""<div class="diff-box diff-old">{r['original_text'] or '—'}</div>""", unsafe_allow_html=True)
                    with c_p:
                        st.markdown("**النص المقترح للتعديل:**")
                        st.markdown(f"""<div class="diff-box diff-new">{r['proposed_text']}</div>""", unsafe_allow_html=True)

    # --- TAB 3: COMPANY JDS DIRECTORY ---
    if page == 'directory':
        st.subheader("🏢 الدليل التعريفي لبطاقات إدارات شركة ثري إس")
        st.markdown("استعراض بطاقات الوظائف الأخرى لضمان وضوح فواصل المسؤوليات وتنسيق المهام بين الإدارات المختلفة.")
        all_jds_df = pd.DataFrame(all_jds, columns=['title', 'department', 'reports_to', 'status', 'version'])[['title', 'department', 'reports_to', 'status', 'version']]
        all_jds_df.columns = ['المسمى الوظيفي', 'الإدارة التابع لها', 'المسؤول المباشر', 'حالة الاعتماد', 'رقم الإصدار']
        render_table(all_jds_df)

    # --- TAB 4: EXPORT DOCUMENT ---
    if page == 'export':
        st.subheader("📥 تنزيل وطباعة بطاقة الوصف الوظيفي المعتمدة")
        st.markdown("يمكنك تنزيل نسخة رسمية منسقة بملف Word (.docx) باللغة العربية وتحتوي على كافة الجداول ومربعات التوقيع الرسمية.")
        doc_stream = docx_parser.export_jd_to_docx(*database.get_export_data(jd['id']))
        st.download_button(
            label=f"📥 تنزيل بطاقة '{jd['title']}' كملف Word (.docx)",
            data=doc_stream,
            file_name=download_filename(jd),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary"
        )
