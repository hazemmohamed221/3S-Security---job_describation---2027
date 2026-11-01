"""Presentation-only regression coverage for Arabic navigation and native grids."""
from copy import deepcopy
from pathlib import Path
import re
import sqlite3

import pandas as pd
import pytest

import auth
import database
import docx_parser
from presentation import (ADMIN_PAGES, MEMBER_PAGES, arabic_action, audit_dataframe,
                          audit_column_config, format_timestamp, render_table)
from utils import get_custom_css


@pytest.mark.parametrize('value,expected', [
    ('2026-10-30 09:45:30', '2026-10-30 09:45'),
    ('2026-10-30T09:45:30+00:00', '2026-10-30 11:45'),
    ('2026-07-01T06:30:59Z', '2026-07-01 09:30'),
    (None, 'غير محدد'), ('', 'غير محدد'), ('not-a-date', 'تاريخ غير صالح'),
    (pd.NA, 'غير محدد'),
])
def test_timestamp_display_has_minutes_and_respects_legacy_timezone(value, expected):
    assert format_timestamp(value) == expected


@pytest.mark.parametrize('code,label', [
    ('update', 'تعديل بيانات'), ('Direct Update', 'تعديل بيانات'), ('approve', 'اعتماد نهائي'),
    ('reject', 'رفض'), ('import', 'استيراد بطاقة'), ('Initial Import', 'استيراد بطاقة'),
    ('modification_accepted', 'قبول تعديل'), ('تم اعتماد التعديل', 'تم اعتماد التعديل'),
])
def test_audit_actions_have_readable_arabic_labels(code, label):
    assert arabic_action(code) == label


def test_audit_dataframe_does_not_change_stored_values_or_truncate_text():
    records = [{'id': 1, 'changed_at': '2026-10-30T09:45:30+00:00', 'jd_title': 'المسمى الوظيفي الكامل',
                'section_name': 'Competencies', 'action': 'update', 'changed_by': 'admin',
                'notes': 'actor_id=1; version=7; ' + 'ملاحظات كاملة ' * 40}]
    original = deepcopy(records)
    frame = audit_dataframe(records)
    assert records == original
    assert frame.loc[0, 'action_type'] == 'تعديل بيانات'
    assert frame.loc[0, 'actor_name'] == 'مسؤول النظام'
    assert frame.loc[0, 'target_field'] == 'الجدارات والكفاءات'
    assert frame.loc[0, 'created_at'] == '2026-10-30 11:45'
    assert 'معرف المنفذ: 1' in frame.loc[0, 'notes'] and 'الإصدار: 7' in frame.loc[0, 'notes']
    assert frame.loc[0, 'notes'].count('ملاحظات كاملة') == 40
    config = audit_column_config()
    assert set(config) == set(frame.columns)
    assert all(column['alignment'] == 'right' for column in config.values())
    assert config['notes']['width'] >= 400 and config['job_title']['width'] >= 300


def test_all_table_columns_have_explicit_alignment_width_and_formatted_dates(monkeypatch):
    import presentation
    captured = {}
    def render(data, **kwargs):
        captured.update(data=data, **kwargs)
    monkeypatch.setattr(presentation.st, 'dataframe', render)
    original = pd.DataFrame({'id': [1], 'title': ['نص كامل'], 'created_at': ['2026-01-01 12:30:59'],
                             'عدد بطاقات الوصف الوظيفي': [2]})
    render_table(original)
    assert captured['hide_index'] and captured['width'] == 'stretch'
    assert set(captured['column_config']) == set(original.columns)
    assert captured['column_config']['title']['label'] == 'المسمى الوظيفي'
    assert captured['column_config']['عدد بطاقات الوصف الوظيفي']['width'] >= 200
    assert captured['data']['created_at'][0] == '2026-01-01 12:30'
    assert original['created_at'][0].endswith(':59')


def test_css_preserves_icon_fonts_and_grid_geometry():
    css = get_custom_css()
    assert "family=Cairo" in css and 'min-width: 320px' in css
    assert 'margin-top: 20px' in css and '.stDeployButton' in css and '#MainMenu' in css
    assert 'p, div, span' not in css
    assert 'stDataFrame"] *' not in css
    icon_rule = css.split('[data-testid="stIconMaterial"]')[1].split('}')[0]
    assert 'font-family' not in icon_rule
    assert 'word-break: normal' in css


def test_schedule_formats_structured_timestamps_but_preserves_arabic_day_labels(monkeypatch):
    import presentation
    frames = []
    monkeypatch.setattr(presentation.st, 'dataframe', lambda frame, **kwargs: frames.append(frame))
    render_table(pd.DataFrame({'اليوم والتاريخ': ['2027-02-24 08:45:59', 'الأحد حسب الاتفاق']}))
    assert frames[0]['اليوم والتاريخ'].tolist() == ['2027-02-24 08:45', 'الأحد حسب الاتفاق']


def login_app(db, username):
    from streamlit.testing.v1 import AppTest
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE users SET password=?', (auth.hash_password('synthetic-secret'),))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=15).run()
    app.sidebar.text_input[0].input(username)
    app.sidebar.text_input[1].input('synthetic-secret')
    app.sidebar.button[0].click().run()
    assert not app.exception and not app.error
    return app


def test_every_admin_screen_is_reachable_from_sidebar(db):
    app = login_app(db, 'hr')
    assert app.sidebar.radio[0].options == list(ADMIN_PAGES.values())
    assert not app.get('tab')
    for page in ADMIN_PAGES.values():
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception and not app.error, page
        assert app.sidebar.radio[0].value == page
    assert any(button.label == 'إضافة المستخدم' for button in app.button)


@pytest.mark.parametrize('username', ['manager', 'staff'])
def test_member_navigation_keeps_exports_working_and_rejects_admin_route(db, username):
    app = login_app(db, username)
    assert app.sidebar.radio[0].options == list(MEMBER_PAGES.values())
    for page in MEMBER_PAGES.values():
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception and not app.error, page
    # Seed stale server state before any widget exists; the client serializer
    # intentionally refuses out-of-range radio values on an existing widget.
    from streamlit.testing.v1 import AppTest
    stale = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=15)
    for key in ('_auth_user_id', '_auth_credential', '_auth_issued_at', '_auth_last_seen'):
        stale.session_state[key] = app.session_state[key]
    stale.session_state['primary_navigation'] = ADMIN_PAGES['settings']
    stale.run()
    assert not stale.exception and not stale.error
    assert stale.sidebar.radio[0].value == MEMBER_PAGES['card']
    assert not any(button.label == 'إضافة المستخدم' for button in stale.button)


def test_hidden_screens_do_not_generate_documents_or_read_review_queue(db, monkeypatch):
    def hidden(*args, **kwargs):
        pytest.fail('An inactive screen was evaluated')
    monkeypatch.setattr(docx_parser, 'export_jd_to_docx', hidden)
    monkeypatch.setattr(database, 'get_pending_modification_requests', hidden)
    app = login_app(db, 'hr')
    app.sidebar.radio[0].set_value(ADMIN_PAGES['settings']).run()
    assert not app.exception and not app.error


def test_audit_screen_shows_cleansed_rows_and_full_notes(db):
    long_note = 'ملاحظات كاملة غير مختصرة ' * 20
    with sqlite3.connect(db) as conn:
        conn.execute('''INSERT INTO jd_audit_trail
            (jd_id,section_name,action,changed_by,changed_at,notes)
            VALUES(1,'Competencies','approve','admin','2026-10-30T09:45:30Z',?)''', (long_note,))
    app = login_app(db, 'hr')
    app.sidebar.radio[0].set_value(ADMIN_PAGES['audit']).run()
    assert not app.exception and not app.error
    frame = app.dataframe[0].value
    assert frame.loc[0, 'action_type'] == 'اعتماد نهائي'
    assert frame.loc[0, 'actor_name'] == 'مسؤول النظام'
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', frame.loc[0, 'created_at'])
    assert frame.loc[0, 'notes'] == long_note
    assert any(long_note.strip() == element.value.strip() for element in app.text)
