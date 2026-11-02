"""Arabic presentation only: navigation, table schemas and readable audit values."""
import re
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from roles import ROLE_LABELS

ADMIN_PAGES = {
    'dashboard': '📊 لوحة المؤشرات والمتابعة',
    'directory': '📋 دليل واستعراض بطاقات الوصف',
    'reviews': '✍️ مراجعة واعتماد التعديلات',
    'import': '📤 استيراد وتحديث بطاقة (Word)',
    'interviews': '📅 مقابلات مناقشة البطاقات',
    'audit': '📜 سجل التعديلات التاريخي (Audit Trail)',
    'settings': '⚙️ لوحة الإدارة والإعدادات',
}
MEMBER_PAGES = {
    'card': '📋 بطاقة الوصف الوظيفي الخاصة بي',
    'requests': '📬 متابعة طلبات التعديل المقدمة مني',
    'directory': ADMIN_PAGES['directory'],
    'export': '📥 تحميل وطباعة البطاقة',
}
COLUMN_LABELS = {'id': 'المعرف', 'title': 'المسمى الوظيفي', 'department': 'الإدارة',
                 'reports_to': 'المسؤول المباشر', 'status': 'الحالة', 'version': 'الإصدار',
                 'created_at': 'تاريخ الإنشاء', 'updated_at': 'تاريخ التحديث'}
ACTION_LABELS = {
    'revoke approval': 'إلغاء الاعتماد وإعادة البطاقة للمسودة',
    'update': 'تعديل بيانات', 'direct update': 'تعديل بيانات',
    'approve': 'اعتماد نهائي', 'approved': 'اعتماد نهائي', 'approved as is': 'اعتماد نهائي دون تعديل',
    'accept': 'قبول تعديل', 'accepted': 'قبول تعديل', 'modification accepted': 'قبول تعديل',
    'reject': 'رفض', 'rejected': 'رفض', 'modification rejected': 'رفض تعديل',
    'import': 'استيراد بطاقة', 'initial import': 'استيراد بطاقة',
    'create': 'إنشاء', 'insert': 'إضافة', 'delete': 'حذف',
}
FIELD_LABELS = {
    'purpose': 'الهدف العام من الوظيفة', 'job purpose': 'الهدف العام من الوظيفة',
    'competencies': 'الجدارات والكفاءات', 'qualifications': 'المؤهلات والخبرات',
    'accountability': 'المسؤوليات والواجبات', 'accountabilities': 'المسؤوليات والواجبات',
    'status': 'حالة الوثيقة', 'document status': 'حالة الوثيقة', 'full document': 'كامل الوثيقة',
    'title': 'المسمى الوظيفي', 'department': 'الإدارة', 'frameworks': 'الصلاحيات وحدود القرارات',
    'hazards': 'مخاطر الوظيفة', 'safe practices': 'ممارسات السلامة',
    'internal relations': 'العلاقات الداخلية', 'external relations': 'العلاقات الخارجية',
    'reports to': 'المسؤول المباشر', 'job code': 'كود الوظيفة', 'dimensions': 'أبعاد الوظيفة',
}


def _code(value):
    return re.sub(r'[_-]+', ' ', str(value or '')).strip().casefold()


def arabic_action(value):
    return ACTION_LABELS.get(_code(value), str(value or 'غير محدد'))


def arabic_field(value):
    return FIELD_LABELS.get(_code(value), str(value or 'كامل الوثيقة'))


def format_timestamp(value):
    """Convert aware timestamps to Cairo; do not invent a timezone for legacy data."""
    if value is None or value is pd.NA or (isinstance(value, str) and not value.strip()):
        return 'غير محدد'
    try:
        timestamp = pd.Timestamp(value)
        if pd.isna(timestamp):
            return 'غير محدد'
        if timestamp.tzinfo is not None:
            timestamp = timestamp.tz_convert(ZoneInfo('Africa/Cairo'))
        return timestamp.strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError, OverflowError):
        return 'تاريخ غير صالح'


def readable_notes(value):
    text = str(value or '—')
    for name, label in (('actor_id', 'معرف المنفذ'), ('version', 'الإصدار')):
        text = re.sub(rf'\b{name}\s*=\s*(\d+)', rf'{label}: \1', text)
    return text


def audit_dataframe(records):
    columns = ['id', 'created_at', 'job_title', 'target_field', 'action_type', 'actor_name', 'notes']
    return pd.DataFrame([{
        'id': row['id'], 'created_at': format_timestamp(row.get('changed_at')),
        'job_title': row.get('jd_title') or 'غير محدد',
        'target_field': arabic_field(row.get('section_name')),
        'action_type': arabic_action(row.get('action')),
        'actor_name': ROLE_LABELS.get(row.get('changed_by'), row.get('changed_by') or 'غير محدد'),
        'notes': readable_notes(row.get('notes')),
    } for row in records], columns=columns)


def audit_column_config():
    return {
        'id': st.column_config.NumberColumn('رقم السجل', width=95, format='%d', alignment='right'),
        'created_at': st.column_config.TextColumn('تاريخ ووقت التعديل', width=190, alignment='right'),
        'job_title': st.column_config.TextColumn('المسمى الوظيفي', width=320, alignment='right'),
        'target_field': st.column_config.TextColumn('البند المعني', width=240, alignment='right'),
        'action_type': st.column_config.TextColumn('نوع الإجراء', width=190, alignment='right'),
        'actor_name': st.column_config.TextColumn('القائم بالإجراء', width=210, alignment='right'),
        'notes': st.column_config.TextColumn('الملاحظات', width=420, alignment='right'),
    }


def render_table(data, *, column_config=None, key=None, row_height=68):
    """Every grid gets a declared schema, sensible widths and native icon fonts."""
    frame = pd.DataFrame(data).copy()
    config = {}
    for column in frame.columns:
        name = COLUMN_LABELS.get(str(column), str(column))
        if pd.api.types.is_datetime64_any_dtype(frame[column]) or str(column) in (
                'created_at', 'updated_at', 'changed_at', 'requested_at', 'reviewed_at',
                'تاريخ الإنشاء', 'تاريخ ووقت التعديل', 'تاريخ وساعة التعديل'):
            frame[column] = frame[column].map(format_timestamp)
        elif str(column) == 'اليوم والتاريخ':
            frame[column] = frame[column].map(lambda value: format_timestamp(value)
                if re.match(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}', str(value)) else (value or 'غير محدد'))
        if pd.api.types.is_numeric_dtype(frame[column]):
            config[column] = st.column_config.NumberColumn(name, width=220 if len(name) > 12 else 100,
                                                           alignment='right')
        else:
            width = 420 if any(word in name for word in ('مسؤولية', 'بيان', 'ملاحظ', 'محاور')) else 220
            config[column] = st.column_config.TextColumn(name, width=width, alignment='right')
    config.update(column_config or {})
    return st.dataframe(frame, width='stretch', hide_index=True, column_config=config,
                        row_height=row_height, key=key)
