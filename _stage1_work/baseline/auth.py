"""
Authentication and session management for 3S Security Job Description Management System.
Fully localized in Arabic.
"""

import streamlit as st
import database


def init_auth():
    """Initializes authentication variables in Streamlit session_state."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_info = None
        st.session_state.role = None


def login(username, password):
    """Validates credentials and logs in the user."""
    user = database.get_user_by_username(username)
    if user and user['password'] == password:
        st.session_state.logged_in = True
        st.session_state.username = user['username']
        st.session_state.user_info = user
        st.session_state.role = user['role']
        return True, "تم تسجيل الدخول بنجاح"
    return False, "اسم المستخدم أو كلمة المرور غير صحيحة"


def logout():
    """Logs out current user."""
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_info = None
    st.session_state.role = None
    st.rerun()


def render_auth_sidebar():
    """
    Renders login widget or active user profile in the sidebar in Arabic.
    Includes quick demo-switcher for easy testing of different roles.
    """
    init_auth()

    st.sidebar.markdown("### 🏢 شركة ثري إس للأنظمة الأمنية")
    st.sidebar.markdown("**منظومة حوكمة واعتماد بطاقات الوصف الوظيفي — 2027**")
    st.sidebar.markdown("---")

    if not st.session_state.logged_in:
        st.sidebar.subheader("🔐 تسجيل الدخول إلى النظام")

        st.sidebar.caption("⚡ تجربة سريعة (اختر صفة لتسجيل الدخول التلقائي):")
        demo_accounts = {
            "اختر حساباً للتجربة...": ("", ""),
            "👑 مدير الموارد البشرية (صلاحيات كاملة واعتماد)": ("admin", "admin123"),
            "👔 د. أشرف شاكر (العضو المنتدب والمدير التنفيذي)": ("ashraf.shaker", "md123"),
            "🏗️ م. أحمد طه (مدير إدارة المشروعات)": ("ahmed.taha", "pass123"),
            "📐 م. رامي (مدير المكتب الفني)": ("ramy.tech", "pass123"),
            "💼 مدير عام المبيعات والتجاري": ("sales.mgr", "pass123"),
            "📦 أ. توفيق (أمين عام المخازن)": ("tawfik.wh", "pass123"),
            "🔧 م. محمد عبدالرازق (مدير الدعم الفني)": ("tech.support", "pass123"),
            "👷 مهندس التركيبات الميداني (موظف)": ("employee", "emp123")
        }

        selected_demo = st.sidebar.selectbox("الحسابات التجريبية", list(demo_accounts.keys()), label_visibility="collapsed")
        
        default_user, default_pass = demo_accounts[selected_demo]

        with st.sidebar.form("login_form"):
            username = st.text_input("اسم المستخدم", value=default_user)
            password = st.text_input("كلمة المرور", value=default_pass, type="password")
            submitted = st.form_submit_button("تسجيل الدخول", use_container_width=True, type="primary")

            if submitted:
                if username and password:
                    success, msg = login(username, password)
                    if success:
                        st.sidebar.success(msg)
                        st.rerun()
                    else:
                        st.sidebar.error(msg)
                else:
                    st.sidebar.warning("يرجى إدخال اسم المستخدم وكلمة المرور.")

        st.sidebar.info("""
        **الأدوار والصلاحيات في النظام:**
        - **مدير الموارد البشرية / مسؤول النظام**: فحص ومقارنة طلبات التعديل جنباً إلى جنب، قبول أو رفض التعديلات، رفع بطاقات وورد جديدة، ومتابعة سجل التغييرات ومحاضر المقابلات.
        - **مدير الإدارة / الموظف**: مراجعة بطاقة الوصف الوظيفي المخصصة له، اعتمادها كما هي، أو اقتراح تعديل على أي بند مع ذكر المبرر الفني.
        """)
    else:
        user = st.session_state.user_info
        role_label = "إدارة الموارد البشرية / مسؤول النظام" if user['role'] == 'admin' else ("مدير إدارة" if user['role'] == 'manager' else "موظف")
        badge_class = "badge-approved" if user['role'] == 'admin' else "badge-pending"

        st.sidebar.markdown(f"""
        <div style="background-color: #f1f5f9; padding: 14px; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 14px; direction: rtl; text-align: right;">
            <div style="font-size: 0.8rem; color: #64748b; font-weight: 700;">المستخدم الحالي:</div>
            <div style="font-size: 1.1rem; font-weight: 800; color: #0f172a; margin-top: 2px;">{user['full_name']}</div>
            <div style="margin-top: 8px;">
                <span class="status-badge {badge_class}">{role_label}</span>
            </div>
            <div style="font-size: 0.85rem; color: #475569; margin-top: 8px;">
                الإدارة التابع لها: <b>{user['department'] or 'الإدارة العامة'}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.sidebar.caption("التبديل إلى مستخدم آخر:")
        all_users = database.get_all_users()
        user_options = {f"{u['full_name']} ({u['department'] or 'الإدارة العامة'})": u['username'] for u in all_users}
        
        current_selection_key = next((k for k, v in user_options.items() if v == user['username']), list(user_options.keys())[0])
        switch_choice = st.sidebar.selectbox("تبديل المستخدم", list(user_options.keys()), index=list(user_options.keys()).index(current_selection_key), label_visibility="collapsed")
        
        chosen_username = user_options[switch_choice]
        if chosen_username != user['username']:
            new_user = database.get_user_by_username(chosen_username)
            st.session_state.username = new_user['username']
            st.session_state.user_info = new_user
            st.session_state.role = new_user['role']
            st.rerun()

        if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
            logout()
