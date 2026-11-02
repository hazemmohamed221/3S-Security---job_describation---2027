"""Revision-bound comprehensive Streamlit JD editor; changes remain local until confirmed."""
from uuid import uuid4

import streamlit as st

import database
from jd_fields import EDIT_GROUPS
from roles import JD_EDIT_ROLES
from statuses import CardStatus


def render_full_jd_editor(jd, principal, run_workflow):
    if principal['role'] not in JD_EDIT_ROLES or CardStatus.parse(jd['status']) not in (
            CardStatus.DRAFT, CardStatus.PENDING_REVIEW):
        return
    token = f"{jd['id']}_{jd['version']}"
    state_key = f'full_editor_{token}'
    if st.button('✏️ تعديل شامل لبطاقة الوصف الوظيفي', key=f'full_open_{token}', type='primary'):
        st.session_state[state_key] = {
            'nonce': uuid4().hex,
            'rows': [dict(row, entry_key=uuid4().hex) for row in database.get_accountabilities(jd['id'])],
        }
        st.session_state['_jd_action_base'] = {'card_id': jd['id'], 'version': jd['version']}
        st.session_state.pop(f'core_edit_{token}', None)
        st.rerun()
    state = st.session_state.get(state_key)
    if state is None:
        return
    prefix = f"full_{token}_{state['nonce']}"
    with st.expander('التعديل الشامل لبطاقة الوصف الوظيفي', expanded=True):
        st.caption(f"تعديل الإصدار {jd['version']}. لا تحفظ الإضافات أو الحذف إلا عند تأكيد الحفظ النهائي.")
        st.info('تبقى البطاقة في حالتها الحالية. يلزم إرسال الإصدار المعدل للمراجعة قبل الاعتماد. '
                'تُحفظ المسؤوليات المحذوفة في التاريخ وتختفي من القائمة الحالية.')
        tabs = st.tabs([label for label, _ in EDIT_GROUPS])
        values = {}
        desired = []
        for tab, (_, fields) in zip(tabs, EDIT_GROUPS):
            with tab:
                for name, label in fields:
                    key = f'{prefix}_{name}'
                    value = jd.get(name) or ''
                    if name in ('title', 'job_code', 'department', 'sector', 'reports_to', 'job_grade'):
                        values[name] = st.text_input(label, value=value, key=key)
                    else:
                        values[name] = st.text_area(label, value=value, key=key, height=100)
                if tab is tabs[2]:
                    st.markdown('#### المسؤوليات والمهام ومؤشرات قياس الأداء')
                    if not state['rows']:
                        st.caption('لا توجد مسؤوليات في القائمة الحالية. يمكنك إضافة بند جديد.')
                    for index, row in enumerate(state['rows'], 1):
                        row_prefix = f"{prefix}_{row['entry_key']}"
                        st.markdown(f'**مسؤولية {index}**')
                        description = st.text_area(f'نص المسؤولية {index}', value=row['description'],
                                                   key=f'{row_prefix}_description', height=100)
                        kpi = st.text_area(f'مؤشر قياس الأداء {index}', value=row.get('kpi') or '',
                                           key=f'{row_prefix}_kpi', height=68)
                        order = st.number_input(f'ترتيب المسؤولية {index}', min_value=1,
                                                value=row['item_order'], step=1, key=f'{row_prefix}_order')
                        desired.append({'id': row.get('id'), 'description': description,
                                        'kpi': row.get('kpi') if kpi == (row.get('kpi') or '') else kpi,
                                        'item_order': order})
                        if st.button(f'🗑️ حذف المسؤولية {index}', key=f'{row_prefix}_remove'):
                            state['rows'].remove(row)
                            st.rerun()
                        st.divider()
                    if st.button('➕ إضافة مسؤولية جديدة', key=f'{prefix}_add'):
                        state['rows'].append({'entry_key': uuid4().hex, 'id': None,
                            'description': '', 'kpi': '',
                            'item_order': max((r['item_order'] for r in desired), default=0) + 1})
                        st.rerun()
        confirm = st.checkbox('أؤكد حفظ التعديلات على هذا الإصدار', key=f'{prefix}_confirmed')
        if st.button('💾 حفظ التعديل الشامل', key=f'{prefix}_save', type='primary', disabled=not confirm):
            fields = {name: value for name, value in values.items() if value != (jd.get(name) or '')}
            ok, message = run_workflow('update_jd_full_details', jd['id'], principal['id'], principal['full_name'],
                                       fields, desired, expected_version=jd['version'])
            if ok:
                st.session_state.pop(state_key, None)
                st.session_state.pop('_jd_action_base', None)
                st.session_state['_jd_edit_flash'] = message
                st.session_state['_jd_saved_card_id'] = jd['id']
                st.rerun()
            st.error(message)
        if st.button('إلغاء التعديل الشامل', key=f'{prefix}_cancel'):
            st.session_state.pop(state_key, None)
            st.session_state.pop('_jd_action_base', None)
            st.rerun()
