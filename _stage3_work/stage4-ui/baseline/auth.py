"""
Authentication and session management for 3S Security Job Description Management System.
Fully localized in Arabic.
"""

import streamlit as st
import database
import hashlib
import html
import time
from password_security import hash_password, verify_password

IDLE_SECONDS = 30 * 60
MAX_SESSION_SECONDS = 12 * 60 * 60


def _clear_session():
    # Clear uploads, form drafts, selected records and all legacy identity keys too.
    st.session_state.clear()
    st.session_state.logged_in = False


def _credential_fingerprint(user):
    credential = f"{user['password']}\0{user.get('auth_version', 0)}"
    return hashlib.sha256(credential.encode('utf-8')).hexdigest()


def get_authenticated_user():
    """Resolve only the server-owned principal; never trust widgets or URL IDs/roles."""
    state = st.session_state
    principal_id = state.get('_auth_user_id')
    if type(principal_id) is not int:
        if state.get('logged_in'):
            _clear_session()
        return None
    now = time.time()
    issued = state.get('_auth_issued_at', 0)
    seen = state.get('_auth_last_seen', 0)
    if now - issued > MAX_SESSION_SECONDS or now - seen > IDLE_SECONDS or now < issued:
        _clear_session()
        return None
    user = database.get_user_by_id(principal_id)
    if (not user or not user.get('is_active', 1) or user['role'] not in ('admin', 'manager', 'employee')
            or state.get('_auth_credential') != _credential_fingerprint(user)):
        _clear_session()
        return None
    public = {key: value for key, value in user.items() if key not in ('password', 'auth_version')}
    state.logged_in = True
    state.username = public['username']
    state.user_info = public
    state['user'] = public
    state.role = public['role']
    state.permissions = ('review', 'import', 'schedule', 'all_cards') if public['role'] == 'admin' else ('assigned_card',)
    state['_auth_last_seen'] = now
    return public


def require_actor(actor_id):
    user = get_authenticated_user()
    if not user or type(actor_id) is not int or user['id'] != actor_id:
        raise PermissionError('انتهت الجلسة أو هوية المستخدم غير صالحة. يرجى تسجيل الدخول مجدداً.')
    return user


def init_auth():
    """Initializes authentication variables in Streamlit session_state."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    get_authenticated_user()


def login(username, password):
    """Validates credentials and logs in the user."""
    user = database.get_user_by_username(username)
    valid = user and verify_password(user['password'], password)
    _clear_session()
    if valid and user.get('is_active', 1) and user['role'] in ('admin', 'manager', 'employee'):
        st.session_state['_auth_user_id'] = user['id']
        st.session_state['_auth_credential'] = _credential_fingerprint(user)
        st.session_state['_auth_issued_at'] = time.time()
        st.session_state['_auth_last_seen'] = time.time()
        get_authenticated_user()
        return True, "تم تسجيل الدخول بنجاح"
    return False, "اسم المستخدم أو كلمة المرور غير صحيحة"


def logout():
    """Logs out current user."""
    _clear_session()
    st.rerun()


def render_auth_sidebar():
    """
    Renders login widget or active user profile in the sidebar in Arabic.
    Identity is established only by explicit database credential verification.
    """
    init_auth()

    st.sidebar.markdown("### 🏢 شركة ثري إس للأنظمة الأمنية")
    st.sidebar.markdown("**منظومة حوكمة واعتماد بطاقات الوصف الوظيفي — 2027**")
    st.sidebar.markdown("---")

    if not st.session_state.logged_in:
        st.sidebar.subheader("🔐 تسجيل الدخول إلى النظام")

        with st.sidebar.form("login_form"):
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
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
        user = get_authenticated_user()
        role_label = "إدارة الموارد البشرية / مسؤول النظام" if user['role'] == 'admin' else ("مدير إدارة" if user['role'] == 'manager' else "موظف")
        badge_class = "badge-approved" if user['role'] == 'admin' else "badge-pending"

        st.sidebar.markdown(f"""
        <div style="background-color: #f1f5f9; padding: 14px; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 14px; direction: rtl; text-align: right;">
            <div style="font-size: 0.8rem; color: #64748b; font-weight: 700;">المستخدم الحالي:</div>
            <div style="font-size: 1.1rem; font-weight: 800; color: #0f172a; margin-top: 2px;">{html.escape(user['full_name'])}</div>
            <div style="margin-top: 8px;">
                <span class="status-badge {badge_class}">{role_label}</span>
            </div>
            <div style="font-size: 0.85rem; color: #475569; margin-top: 8px;">
                الإدارة التابع لها: <b>{html.escape(user['department'] or 'الإدارة العامة')}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
            logout()
