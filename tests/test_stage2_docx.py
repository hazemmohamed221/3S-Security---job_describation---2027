"""Word contract parity, visible edits, metadata and Arabic/RTL layout structure."""
import io
import sqlite3

import docx
from docx.oxml.ns import qn
import pytest

import database
from docx_parser import export_jd_to_docx, parse_jd_docx


def card():
    return {
        'id': 26, 'job_code': '3S-HR-026', 'title': 'مدير الموارد البشرية',
        'department': 'إدارة الموارد البشرية', 'sector': 'القطاع الإداري',
        'reports_to': 'المدير العام', 'purpose': '  هدف عربي\nسطر ثانٍ  ',
        'dimensions': 'النطاق الإشرافي: 3', 'frameworks': 'سلطات وحدود',
        'qualifications': 'بكالوريوس\nخبرة خمس سنوات',
        'competencies': 'سلوكية: التعاون والإنصات\nفنية: تحليل البيانات\nTechnical: SQL\nمعيار عام',
        'hazards': 'مخاطر مسجلة', 'safe_practices': 'إجراءات موثقة',
        'internal_relations': 'الإدارات الداخلية', 'external_relations': 'جهات خارجية',
        'approvals': 'توقيع مصدر قديم\nتاريخ غير محدد', 'version': 7, 'status': 'قيد المراجعة',
    }


def rows():
    return [{'item_order': 2, 'description': 'نص عربي متكرر', 'kpi': '97%\nشهرياً'},
            {'item_order': 4, 'description': 'نص عربي متكرر', 'kpi': ''},
            {'item_order': 9, 'description': '  فقرة\nثانية  ', 'kpi': '—'}]


def stream(document):
    result = io.BytesIO()
    document.save(result)
    result.seek(0)
    return result


def test_all_fields_responsibility_order_kpis_and_criteria_roundtrip():
    original = card()
    parsed = parse_jd_docx(export_jd_to_docx(original, rows()))
    for key, value in original.items():
        assert parsed['portal_card_id' if key == 'id' else key] == value
    assert parsed['accountabilities'] == rows()
    assert parsed['competency_criteria']['behavioral'] == ['سلوكية: التعاون والإنصات']
    assert len(parsed['competency_criteria']['technical']) == 2
    # A repeated round trip retains intentional duplicate responsibilities exactly once per row.
    parsed['id'] = parsed['portal_card_id']
    again = parse_jd_docx(export_jd_to_docx(parsed, parsed['accountabilities']))
    assert again['accountabilities'] == rows()
    assert again['competencies'] == original['competencies']


def test_empty_fields_remain_empty_without_fabricated_safety_or_codes():
    original = {k: '' for k in card()}
    original.update(id=1, version=1, status='مسودة')
    output = export_jd_to_docx(original, [])
    parsed = parse_jd_docx(output)
    assert parsed['accountabilities'] == []
    for key in ('job_code', 'hazards', 'safe_practices', 'approvals', 'competencies', 'purpose'):
        assert parsed[key] == ''
    document = docx.Document(output)
    text = '\n'.join(p.text for p in document.paragraphs)
    assert 'لا يوجد اعتماد إلكتروني موثق' in text
    assert 'بطاقة الوصف والتوصيف الوظيفي المعتمدة' not in text
    assert '3S-JD-001' not in text


def test_parser_reads_visible_word_edits_instead_of_hidden_payload():
    document = docx.Document(export_jd_to_docx(card(), rows()))
    target = next(p for p in document.paragraphs if p.text == card()['competencies'])
    # Simulate editing a run in Word; bookmarks remain around the visible text.
    target.runs[0].text = 'فنية: كفاءة معدلة'
    parsed = parse_jd_docx(stream(document))
    assert parsed['competencies'] == 'فنية: كفاءة معدلة'


@pytest.mark.parametrize('damage', ['version', 'missing_marker', 'missing_field', 'duplicate_table', 'duplicate_field'])
def test_damaged_or_unknown_system_format_fails_closed(damage):
    from copy import deepcopy
    document = docx.Document(export_jd_to_docx(card(), rows()))
    if damage == 'version':
        document.core_properties.identifier = '3S-JD/v999'
    elif damage == 'missing_marker':
        document.core_properties.identifier = ''
    elif damage == 'missing_field':
        mark = next(b for b in document.element.body.iter(qn('w:bookmarkStart')) if b.get(qn('w:name')) == 's3jd2_competencies')
        mark.getparent().remove(mark)
    elif damage == 'duplicate_field':
        mark = next(b for b in document.element.body.iter(qn('w:bookmarkStart')) if b.get(qn('w:name')) == 's3jd2_competencies')
        mark.getparent().append(deepcopy(mark))
    else:
        document.element.body.append(deepcopy(document.tables[1]._tbl))
    with pytest.raises(ValueError):
        parse_jd_docx(stream(document))


def test_rtl_tables_headers_widths_and_arabic_paragraphs():
    document = docx.Document(export_jd_to_docx(card(), rows()))
    for table in document.tables:
        assert table._tbl.tblPr.find(qn('w:bidiVisual')) is not None
        assert table.rows[0]._tr.trPr.find(qn('w:tblHeader')) is not None
        assert table._tbl.tblPr.find(qn('w:tblBorders')) is not None
        for row in table.rows:
            for cell, column in zip(row.cells, table.columns):
                assert cell.width == column.width
                for paragraph in cell.paragraphs:
                    assert paragraph._p.pPr.find(qn('w:bidi')) is not None
    acc = document.tables[1]
    assert acc.columns[0].width < acc.columns[1].width


def test_current_approval_metadata_exported_and_legacy_text_retained(sign_in, db):
    sign_in()
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE job_descriptions SET approvals='توقيع المصدر',competencies='فنية: التحليل' WHERE id=1")
    database.request_jd_review(1, actor_id=2)
    database.approve_jd_as_is(1, actor_id=2)
    metadata = database.get_approval_metadata(1)
    assert metadata['approver'] == 'مستخدم 2' and metadata['version'] == 2
    result = export_jd_to_docx(database.get_jd_by_id(1), database.get_accountabilities(1), metadata)
    document = docx.Document(result)
    text = '\n'.join(c.text for t in document.tables for r in t.rows for c in r.cells)
    for value in (metadata['approver'], metadata['decided_at'], metadata['snapshot_hash']):
        assert value in text
    assert parse_jd_docx(result)['approvals'] == 'توقيع المصدر'


def test_reimport_own_export_is_idempotent_and_changed_import_does_not_overwrite(sign_in, db):
    sign_in('hr')
    output = export_jd_to_docx(database.get_jd_by_id(1), database.get_accountabilities(1))
    parsed = parse_jd_docx(output)
    with sqlite3.connect(db) as conn:
        before = list(conn.iterdump())
    assert database.create_or_update_jd(parsed, 'roundtrip.docx', actor_id=1) == 1
    assert database.create_or_update_jd(parsed, 'roundtrip.docx', actor_id=1) == 1
    parsed['competencies'] = 'محتوى معدل'
    with pytest.raises(ValueError):
        database.create_or_update_jd(parsed, 'roundtrip.docx', actor_id=1)
    with sqlite3.connect(db) as conn:
        assert list(conn.iterdump()) == before


def test_import_new_system_document_preserves_empty_and_literal_english_values(sign_in, db):
    sign_in('hr')
    original = card() | {'id': 99, 'title': 'HR Manager', 'reports_to': '', 'department': '', 'sector': '', 'dimensions': '', 'qualifications': ''}
    parsed = parse_jd_docx(export_jd_to_docx(original, rows()))
    jd_id = database.create_or_update_jd(parsed, 'new.docx', actor_id=1)
    assert database.create_or_update_jd(parsed, 'new.docx', actor_id=1) == jd_id
    saved = database.get_jd_by_id(jd_id)
    for field in ('title', 'reports_to', 'department', 'sector', 'dimensions', 'qualifications', 'competencies', 'approvals'):
        assert saved[field] == original[field]
    assert [(r['item_order'], r['description'], r['kpi']) for r in database.get_accountabilities(jd_id)] == [
        (r['item_order'], r['description'], r['kpi']) for r in rows()]
    assert saved['status'] == 'قيد المراجعة' and database.get_approval_metadata(jd_id) is None


@pytest.mark.parametrize('heading', ['Competencies', 'Required Competencies & Skills'])
def test_legacy_competency_table_retains_all_rows_without_merged_cell_duplication(heading):
    document = docx.Document()
    table = document.add_table(rows=3, cols=2)
    table.rows[0].cells[0].merge(table.rows[0].cells[1]).text = heading
    table.rows[1].cells[0].merge(table.rows[1].cells[1]).text = 'سلوكية: التعاون'
    table.rows[2].cells[0].text = 'فنية'
    table.rows[2].cells[1].text = 'تحليل'
    parsed = parse_jd_docx(stream(document))
    assert parsed['competencies'] == 'سلوكية: التعاون\nفنية | تحليل'
