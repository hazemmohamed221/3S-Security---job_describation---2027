"""Editable Word interchange v2: visible text is the source of truth, not hidden JSON."""
import io
import re

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from jd_fields import DETAIL_FIELDS

FORMAT = '3S-JD/v2'
DETAIL_FORMAT = '3S-JD/details-v1'
PROFILE = (
    ('job_code', 'كود الوظيفة'), ('title', 'المسمى الوظيفي'),
    ('department', 'الإدارة'), ('sector', 'القطاع'), ('reports_to', 'المسؤول المباشر'),
)
SECTIONS = (
    ('purpose', 'الهدف العام من الوظيفة'), ('dimensions', 'أبعاد الوظيفة والنطاق الإشرافي'),
    ('frameworks', 'إطار العمل وحدود اتخاذ القرارات'),
    ('qualifications', 'المؤهلات والخبرات والمهارات'),
    ('competencies', 'الجدارات والكفاءات والمعايير السلوكية والفنية'),
    ('hazards', 'مخاطر الوظيفة'), ('safe_practices', 'ممارسات السلامة والصحة المهنية'),
    ('internal_relations', 'العلاقات الداخلية'), ('external_relations', 'العلاقات الخارجية'),
    ('approvals', 'بيانات الاعتماد الواردة في المصدر'),
)


def rtl(paragraph):
    prop = paragraph._p.get_or_add_pPr()
    if prop.find(qn('w:bidi')) is None:
        prop.append(OxmlElement('w:bidi'))
    # Logical start aligns Arabic to the leading (right) edge in modern Word.
    prop.get_or_add_jc().set(qn('w:val'), 'start')
    for run in paragraph.runs:
        run.font.name = 'Arial'
        run.font.rtl = True
        run._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:cs'), 'Arial')


def field(paragraph, key, value, number):
    paragraph.text = '' if value is None else str(value)
    start = OxmlElement('w:bookmarkStart')
    start.set(qn('w:id'), str(number))
    start.set(qn('w:name'), 's3jd2_' + key)
    paragraph._p.insert(0, start)
    end = OxmlElement('w:bookmarkEnd')
    end.set(qn('w:id'), str(number))
    paragraph._p.append(end)
    rtl(paragraph)


def table(doc, headers, widths, caption):
    result = doc.add_table(rows=1, cols=len(headers))
    result.style = 'Table Grid'
    result.alignment = WD_TABLE_ALIGNMENT.CENTER
    result.autofit = False
    prop = result._tbl.tblPr
    prop.append(OxmlElement('w:bidiVisual'))
    label = OxmlElement('w:tblCaption')
    label.set(qn('w:val'), caption)
    prop.append(label)
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        item = OxmlElement('w:' + edge)
        for k, v in (('val', 'single'), ('sz', '4'), ('color', 'D9D9D9')):
            item.set(qn('w:' + k), v)
        borders.append(item)
    prop.append(borders)
    for column, width in zip(result.columns, widths):
        column.width = Inches(width)
    total = prop.find(qn('w:tblW'))
    total.set(qn('w:type'), 'dxa')
    total.set(qn('w:w'), str(round(sum(widths) * 1440)))
    for cell, text in zip(result.rows[0].cells, headers):
        cell.text = text
        shade = OxmlElement('w:shd')
        shade.set(qn('w:fill'), '1A365D')
        cell._tc.get_or_add_tcPr().append(shade)
        for run in cell.paragraphs[0].runs:
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.bold = True
    repeat = OxmlElement('w:tblHeader')
    result.rows[0]._tr.get_or_add_trPr().append(repeat)
    return result


def competency_criteria(text):
    criteria = {'behavioral': [], 'technical': [], 'other': []}
    for line in (text or '').splitlines():
        group = 'other'
        if re.search(r'سلوك|behavior', line, re.I):
            group = 'behavioral'
        elif re.search(r'فني|فنية|تقني|technical', line, re.I):
            group = 'technical'
        criteria[group].append(line)
    return criteria


def parse_system_document(doc, file_name):
    identifier = doc.core_properties.identifier or ''
    if not identifier.startswith('3S-JD/'):
        if any(b.get(qn('w:name'), '').startswith('s3jd2_')
               for b in doc.element.body.iter(qn('w:bookmarkStart'))):
            raise ValueError('معرف قالب Word مفقود. أعد تصدير الوثيقة من المنصة.')
        return None
    if identifier != FORMAT:
        raise ValueError('إصدار قالب Word غير مدعوم.')
    fields = {}
    # Bookmarks identify editable visible paragraphs, including paragraphs in cells.
    for paragraph in doc.element.body.iter(qn('w:p')):
        for bookmark in paragraph.iter(qn('w:bookmarkStart')):
            name = bookmark.get(qn('w:name'), '')
            if name.startswith('s3jd2_'):
                key = name[6:]
                if key in fields:
                    raise ValueError('تكرار حقل في قالب Word.')
                fields[key] = docx.text.paragraph.Paragraph(paragraph, doc).text
    required = {k for k, _ in (*PROFILE, *SECTIONS)} | {'portal_card_id', 'version', 'status'}
    if DETAIL_FORMAT in (doc.core_properties.keywords or ''):
        required.update(DETAIL_FIELDS)
    if not required.issubset(fields):
        raise ValueError('قالب Word غير مكتمل. أعد التصدير مع الحفاظ على أقسام الوثيقة.')
    for key in DETAIL_FIELDS:
        fields.setdefault(key, '')
    tables = [t for t in doc.tables if t._tbl.tblPr.find(qn('w:tblCaption')) is not None and
              t._tbl.tblPr.find(qn('w:tblCaption')).get(qn('w:val')) == '3SJD2:accountabilities']
    if len(tables) != 1:
        raise ValueError('جدول المسؤوليات مفقود أو مكرر.')
    responsibilities = []
    for row in tables[0].rows[1:]:
        if len(row.cells) != 3:
            raise ValueError('تنسيق جدول المسؤوليات غير صالح.')
        order, description, kpi = (c.text for c in row.cells)
        if not order.isdigit():
            raise ValueError('ترتيب المسؤولية غير صالح.')
        responsibilities.append({'item_order': int(order), 'description': description, 'kpi': kpi})
    try:
        fields['portal_card_id'] = int(fields['portal_card_id']) if fields['portal_card_id'] else None
        fields['version'] = int(fields['version'])
    except ValueError as exc:
        raise ValueError('معرف البطاقة أو إصدارها غير صالح.') from exc
    fields.update(file_name=file_name, format_version=2, accountabilities=responsibilities,
                  competency_criteria=competency_criteria(fields['competencies']))
    return fields


def export_jd_to_docx(jd_data, accountabilities, approval_metadata=None):
    doc = docx.Document()
    doc.core_properties.identifier = FORMAT
    detailed = any(jd_data.get(key) not in (None, '') for key in DETAIL_FIELDS)
    if detailed:
        doc.core_properties.keywords = DETAIL_FORMAT
    section = doc.sections[0]
    section.left_margin = section.right_margin = Inches(.7)
    section.page_width, section.page_height = Inches(8.27), Inches(11.69)
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Arial', Pt(11)
    style.paragraph_format.space_after = Pt(6)
    for name in ('Title', 'Heading 1', 'Heading 2'):
        doc.styles[name].font.color.rgb = RGBColor(0, 0, 0)
    for style in doc.styles:
        if style.type == 1:
            prop = style.element.find(qn('w:pPr'))
            if prop is not None:
                for border in list(prop.findall(qn('w:pBdr'))):
                    prop.remove(border)
    title = doc.add_paragraph('شركة ثري إس للأنظمة الأمنية\nبطاقة الوصف الوظيفي', 'Title')
    rtl(title)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    intro = doc.add_paragraph('توضح هذه البطاقة نطاق الوظيفة ومسؤولياتها ومعاييرها. '
                              'الحقول الفارغة غير مسجلة. بيانات اعتماد المصدر لا تثبت اعتماد الإصدار الحالي.')
    rtl(intro)
    number = 0

    def put(p, key, value):
        nonlocal number
        number += 1
        field(p, key, value, number)

    profile = table(doc, ('بيانات الوظيفة والحوكمة', 'القيمة المسجلة'), (2.2, 4.6), '3SJD2:profile')
    profile_details = tuple((key, DETAIL_FIELDS[key]) for key in ('subordinates', 'job_grade')) if detailed else ()
    for key, label in (*PROFILE, *profile_details, ('portal_card_id', 'معرف البطاقة في المنصة'),
                       ('version', 'الإصدار'), ('status', 'حالة الوثيقة')):
        cells = profile.add_row().cells
        cells[0].text = label
        put(cells[1].paragraphs[0], key, jd_data.get('id') if key == 'portal_card_id' else jd_data.get(key, ''))
    for key, heading in SECTIONS:
        rtl(doc.add_heading(heading, 2))
        put(doc.add_paragraph(), key, jd_data.get(key, ''))
        extra = ('working_conditions',) if key == 'purpose' else (
            ('education', 'experience', 'certifications', 'languages', 'skills') if key == 'qualifications' else ())
        if detailed:
            for name in extra:
                rtl(doc.add_heading(DETAIL_FIELDS[name], 2))
                put(doc.add_paragraph(), name, jd_data.get(name, ''))
        if key == 'dimensions':
            rtl(doc.add_heading('المسؤوليات ومؤشرات قياس الأداء', 2))
            acc_table = table(doc, ('م', 'بيان المسؤولية والواجب الوظيفي', 'مؤشر قياس الأداء'),
                              (.4, 4.3, 2.1), '3SJD2:accountabilities')
            for index, acc in enumerate(accountabilities, 1):
                cells = acc_table.add_row().cells
                for cell, value in zip(cells, (acc.get('item_order', index), acc.get('description', ''), acc.get('kpi') or '')):
                    cell.text = str(value)
    rtl(doc.add_heading('قرار اعتماد الإصدار الحالي', 2))
    if approval_metadata:
        evidence = table(doc, ('بيانات القرار', 'القيمة الموثقة'), (2.2, 4.6), '3SJD2:evidence')
        for label, key in (('اسم المعتمد', 'approver'), ('معرف المعتمد', 'actor_id'),
                           ('تاريخ القرار UTC', 'decided_at'), ('الإصدار المعتمد', 'version'),
                           ('معرف سجل القرار', 'evidence_id'), ('بصمة لقطة المراجعة SHA256', 'snapshot_hash')):
            cells = evidence.add_row().cells
            cells[0].text, cells[1].text = label, str(approval_metadata[key])
    else:
        rtl(doc.add_paragraph('لا يوجد اعتماد إلكتروني موثق لهذا الإصدار.'))
    for tbl in doc.tables:
        widths = [column.width for column in tbl.columns]
        for row_index, row in enumerate(tbl.rows):
            for cell, width in zip(row.cells, widths):
                cell.width = width
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                for paragraph in cell.paragraphs:
                    rtl(paragraph)
                    if paragraph.text and paragraph.text.isascii():
                        paragraph._p.pPr.find(qn('w:bidi')).set(qn('w:val'), '0')
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                        for run in paragraph.runs:
                            run.font.rtl = False
                    paragraph.paragraph_format.space_after = Pt(5)
                if row_index and row_index % 2 == 0:
                    shade = OxmlElement('w:shd')
                    shade.set(qn('w:fill'), 'F0F4F8')
                    cell._tc.get_or_add_tcPr().append(shade)
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output
