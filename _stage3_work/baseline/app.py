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

# Local modules
import database
import docx_parser
import utils
import auth

def _run_write(operation, *args, **kwargs):
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


# Page configuration
st.set_page_config(
    page_title="ثري إس للأمن | منظومة الوصف الوظيفي 2027",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global Arabic RTL styling
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
    <div class="brand-header">
        <div>
            <div class="brand-title">🛡️ شركة ثري إس للأنظمة الأمنية (3S Security)</div>
            <div class="brand-subtitle">بوابة حوكمة ومراجعة واعتماد بطاقات الوصف والتوصيف الوظيفي — خطة 2027</div>
        </div>
        <div style="text-align: left;">
            <span class="status-badge badge-pending" style="font-size: 0.95rem; padding: 6px 16px;">النسخة المؤسسية المعتمدة</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
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
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 22px; box-shadow: 0 4px 10px rgba(0,0,0,0.04); direction: rtl; text-align: right;">
            <h4 style="margin-top: 0; color: #1e3a8a; font-weight: 800; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">📊 مؤشرات المنظومة العامة</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 15px;">
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
is_admin = (user['role'] == 'admin')
is_manager = (user['role'] == 'manager')
stats = database.get_dashboard_stats()

# Header Banner
st.markdown(f"""
<div class="brand-header">
    <div>
        <div class="brand-title">🛡️ شركة ثري إس للأنظمة الأمنية — منظومة الوصف الوظيفي</div>
        <div class="brand-subtitle">المستخدم المتصل: <b>{user['full_name']}</b> | الإدارة: <b>{user['department'] or 'الإدارة العامة'}</b></div>
    </div>
    <div style="text-align: left;">
        <span class="status-badge {'badge-approved' if is_admin else 'badge-pending'}" style="font-size: 0.9rem; padding: 6px 16px;">
            {'👑 إدارة الموارد البشرية / مسؤول النظام' if is_admin else ('👔 مدير إدارة' if is_manager else '👷 موظف')}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# ADMIN / HR MANAGER (ROLE B) INTERFACE
# -------------------------------------------------------------
if is_admin:
    tab_dash, tab_reviews, tab_upload, tab_explorer, tab_audit, tab_schedule = st.tabs([
        "📊 لوحة المؤشرات والمتابعة",
        f"⚖️ مراجعة واعتماد التعديلات ({stats['pending_mods']})",
        "📤 رفع بطاقة وورد جديدة (.docx)",
        "📁 دليل واستعراض بطاقات الوصف",
        "📜 سجل التعديلات التاريخي (Audit Trail)",
        "📅 جدول مقابلات مناقشة البطاقات"
    ])

    # --- TAB 1: DASHBOARD & METRICS ---
    with tab_dash:
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
                st.dataframe(dept_counts, use_container_width=True)
        
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
    with tab_reviews:
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
                    col_meta3.markdown(f"**تاريخ تقديم الطلب:** {req['requested_at']}")

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
    with tab_upload:
        st.subheader("📤 رفع بطاقات وصف وظيفي جديدة بصيغة Word (.docx)")
        st.markdown("""
        يمكن لمسؤول النظام رفع ملفات Word إضافية تتبع النموذج الرسمي المعتمد لشركة **ثري إس للأنظمة الأمنية**.
        يقوم النظام آلياً بقراءة وتحليل وترجمة كافة البنود العشرة للبطاقة وإدراجها فوراً في قاعدة البيانات باللغة العربية.
        """)

        uploaded_files = st.file_uploader(
            "اختر ملف أو عدة ملفات بصيغة Word (.docx) للرفع والاستيراد",
            type=["docx"],
            accept_multiple_files=True
        )

        if uploaded_files:
            st.markdown(f"**تم اختيار {len(uploaded_files)} ملف(ات) للمعالجة.**")

            for uploaded_file in uploaded_files:
                st.markdown("---")
                with st.expander(f"📄 معاينة استخراج البيانات من: {uploaded_file.name}", expanded=True):
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
                            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

                        # Confirmation button to insert into DB
                        if st.button(f"💾 تأكيد وإدراج بطاقة '{title_preview}' في قاعدة البيانات", key=f"btn_import_{uploaded_file.name}"):
                            new_jd_id = _run_write(database.create_or_update_jd,
                                parsed_jd=parsed_data,
                                source_file=uploaded_file.name,
                                actor_id=user['id']
                            )
                            st.success(f"تم إدراج بطاقة الوصف الوظيفي '{title_preview}' بنجاح برقم #{new_jd_id}!")
                            st.rerun()

                    except Exception as e:
                        st.error(f"حدث خطأ أثناء معالجة الملف {uploaded_file.name}: {e}")

    # --- TAB 4: JOB DESCRIPTIONS EXPLORER ---
    with tab_explorer:
        st.subheader("📁 الدليل الشامل لبطاقات الوصف الوظيفي")
        all_jds = database.get_all_jds()

        fcol1, fcol2, fcol3 = st.columns([3, 2, 2])
        search_kw = fcol1.text_input("🔍 البحث باسم الوظيفة أو الكلمات المفتاحية", placeholder="مثال: مشروعات، مبيعات، جودة، مخازن...")
        
        dept_list = ["كافة الإدارات"] + sorted(list({j['department'] for j in all_jds if j['department']}))
        selected_dept = fcol2.selectbox("تصفية حسب الإدارة", dept_list)
        
        status_list = ["كافة الحالات", "مسودة", "قيد المراجعة", "معتمد", "مرفوض"]
        selected_status = fcol3.selectbox("تصفية حسب حالة الاعتماد", status_list)

        filtered_jds = all_jds
        if search_kw:
            filtered_jds = [j for j in filtered_jds if search_kw.lower() in j['title'].lower() or search_kw.lower() in (j['department'] or '').lower()]
        if selected_dept != "كافة الإدارات":
            filtered_jds = [j for j in filtered_jds if j['department'] == selected_dept]
        if selected_status != "كافة الحالات":
            filtered_jds = [j for j in filtered_jds if j['status'] == selected_status]

        st.caption(f"يتم عرض **{len(filtered_jds)}** من أصل **{len(all_jds)}** بطاقة وصف وظيفي")

        jd_options = {f"{j['title']} ({j['department'] or 'الإدارة العامة'})": j['id'] for j in filtered_jds}
        
        if jd_options:
            selected_jd_label = st.selectbox("اختر بطاقة الوصف الوظيفي لعرض كافة تفاصيلها:", list(jd_options.keys()))
            chosen_jd_id = jd_options[selected_jd_label]
            jd = database.get_jd_by_id(chosen_jd_id)
            accountabilities = database.get_accountabilities(chosen_jd_id)

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
                file_name=f"{jd['title'].replace(' ', '_')}_بطاقة_وصف_وظيفي.docx",
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
                <div>{jd['purpose'] or 'لم يتم إدراج بيان الهدف العام بعد.'}</div>
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
                st.dataframe(pd.DataFrame(acc_rows), use_container_width=True, hide_index=True)
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
                    <div style="white-space: pre-line;">{jd['qualifications']}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('#### الجدارات والكفاءات والمعايير السلوكية والفنية')
            st.write(jd['competencies'] or 'غير مسجلة')
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
    with tab_audit:
        st.subheader("📜 سجل التعديلات التاريخي وتتبع النسخ (Audit Trail)")
        st.markdown("سجل رقمي غير قابل للتعديل يوثق كل عملية اعتماد، تعديل بند، أو استيراد مع تسجيل الوقت والمستخدم والنص قبل وبعد التعديل.")

        audit_records = database.get_audit_trail()
        if audit_records:
            audit_display_rows = []
            for r in audit_records:
                audit_display_rows.append({
                    "رقم السجل": r['id'],
                    "تاريخ وساعة التعديل": r['changed_at'],
                    "مسمى الوظيفة": r['jd_title'],
                    "البند المعني": r['section_name'],
                    "نوع الإجراء": r['action'],
                    "القائم بالإجراء": r['changed_by'],
                    "ملاحظات": r['notes']
                })
            st.dataframe(pd.DataFrame(audit_display_rows), use_container_width=True, hide_index=True)

            st.markdown("#### 🔎 فحص ومقارنة نص تعديل محدد")
            selected_audit_id = st.selectbox(
                "اختر سجل التعديل لعرض النص القديم مقابل النص الجديد:",
                options=[r['id'] for r in audit_records],
                format_func=lambda x: next(f"سجل #{r['id']} - {r['changed_at']} | {r['jd_title']} | {r['action']}" for r in audit_records if r['id'] == x)
            )

            rec = next((r for r in audit_records if r['id'] == selected_audit_id), None)
            if rec and (rec['old_text'] or rec['new_text']):
                c_old, c_new = st.columns(2)
                with c_old:
                    st.markdown("**النص قبل التعديل:**")
                    st.markdown(f"""<div class="diff-box diff-old">{rec['old_text'] or '<i>(لا يوجد)</i>'}</div>""", unsafe_allow_html=True)
                with c_new:
                    st.markdown("**النص المعتمد بعد التعديل:**")
                    st.markdown(f"""<div class="diff-box diff-new">{rec['new_text'] or '<i>(لا يوجد)</i>'}</div>""", unsafe_allow_html=True)
        else:
            st.info("لا توجد سجلات تعديل حتى الآن.")

    # --- TAB 6: INTERVIEW SCHEDULE ---
    with tab_schedule:
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
                    "حالة المقابلة": it['status'],
                    "محاور النقاش الرئيسية والتكامل المطلوب": it['discussion_topics'],
                    "ملاحظات ومخرجات الاجتماع": it['notes'] or '—'
                })
            st.dataframe(pd.DataFrame(sch_display), use_container_width=True, hide_index=True)

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
            statuses = list(dict.fromkeys([selected_interview['status'], "قيد المراجعة", "مكتملة", "مؤجلة", "لم تبدأ"]))
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
    
    if not all_jds or assigned_jd_id not in {j['id'] for j in all_jds}:
        st.info("لم يتم تخصيص بطاقة وصف وظيفي صالحة لحسابك. يرجى التواصل مع الموارد البشرية.")
        if all_jds:
            st.dataframe(pd.DataFrame(all_jds)[['title', 'department', 'reports_to', 'status', 'version']], hide_index=True)
        st.stop()

    tab_my_jd, tab_my_requests, tab_company_jds, tab_export = st.tabs([
        "📋 بطاقة الوصف الوظيفي الخاصة بي",
        "📬 متابعة طلبات التعديل المقدمة مني",
        "🏢 دليل بطاقات إدارات الشركة" if is_manager else "🏢 استعراض الوظائف الأخرى",
        "📥 تحميل وطباعة البطاقة"
    ])

    # --- TAB 1: MY JOB DESCRIPTION ---
    with tab_my_jd:
        if is_manager:
            col_sel1, col_sel2 = st.columns([3, 1])
            with col_sel1:
                jd_map = {f"{j['title']} ({j['department'] or 'الإدارة العامة'})": j['id'] for j in all_jds}
                default_index = list(jd_map.values()).index(assigned_jd_id) if assigned_jd_id in jd_map.values() else 0
                selected_label = st.selectbox("بطاقة الوصف الوظيفي المعروضة حالياً للمراجعة:", list(jd_map.keys()), index=default_index)
                current_jd_id = jd_map[selected_label]
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
            <div>{jd['purpose'] or 'لم يتم إدراج بيان الهدف العام بعد.'}</div>
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
            st.dataframe(pd.DataFrame(acc_list), use_container_width=True, hide_index=True)
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
                <div style="white-space: pre-line;">{jd['qualifications']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('#### الجدارات والكفاءات والمعايير السلوكية والفنية')
        st.write(jd['competencies'] or 'غير مسجلة')
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
    with tab_my_requests:
        st.subheader("📬 متابعة طلبات التعديل المقدمة من طرفي")
        my_reqs = database.get_requests_by_user(user['full_name'])

        if not my_reqs:
            st.info("لم تقم بتقديم أية طلبات تعديل حتى الآن. يمكنك تقديم طلبات مباشرة من تبويب 'بطاقة الوصف الوظيفي الخاصة بي'.")
        else:
            for r in my_reqs:
                badge_type = "badge-approved" if r['status'] == 'مقبول' else ("badge-rejected" if r['status'] == 'مرفوض' else "badge-under-review")
                with st.expander(f"طلب #{r['id']} — {r['section_name']} ({r['status']}) - {r['requested_at']}", expanded=True):
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
    with tab_company_jds:
        st.subheader("🏢 الدليل التعريفي لبطاقات إدارات شركة ثري إس")
        st.markdown("استعراض بطاقات الوظائف الأخرى لضمان وضوح فواصل المسؤوليات وتنسيق المهام بين الإدارات المختلفة.")
        all_jds_df = pd.DataFrame(all_jds)[['title', 'department', 'reports_to', 'status', 'version']]
        all_jds_df.columns = ['المسمى الوظيفي', 'الإدارة التابع لها', 'المسؤول المباشر', 'حالة الاعتماد', 'رقم الإصدار']
        st.dataframe(all_jds_df, use_container_width=True, hide_index=True)

    # --- TAB 4: EXPORT DOCUMENT ---
    with tab_export:
        st.subheader("📥 تنزيل وطباعة بطاقة الوصف الوظيفي المعتمدة")
        st.markdown("يمكنك تنزيل نسخة رسمية منسقة بملف Word (.docx) باللغة العربية وتحتوي على كافة الجداول ومربعات التوقيع الرسمية.")
        doc_stream = docx_parser.export_jd_to_docx(*database.get_export_data(jd['id']))
        st.download_button(
            label=f"📥 تنزيل بطاقة '{jd['title']}' كملف Word (.docx)",
            data=doc_stream,
            file_name=f"{jd['title'].replace(' ', '_')}_بطاقة_وصف_معتمدة.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary"
        )
