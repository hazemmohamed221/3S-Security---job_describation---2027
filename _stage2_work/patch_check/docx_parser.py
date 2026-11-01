"""
Word Document Parser and Exporter for 3S Security Job Descriptions.
Full Arabic & RTL support for parsing and document generation.
"""

import os
import io
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx_format import parse_system_document


def set_cell_background(cell, fill_hex):
    """Sets background color of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)


def set_p_rtl(p):
    """Sets paragraph direction to RTL (Right-to-Left) with Arabic font."""
    pPr = p._p.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    pPr.append(bidi)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def parse_jd_docx(file_source):
    """
    Parses a Job Description Word document (.docx).
    Accepts either a file path (str) or a file-like stream (io.BytesIO).
    Supports English & Arabic table headers.
    """
    if isinstance(file_source, (str, bytes, os.PathLike)):
        doc = docx.Document(file_source)
        file_name = os.path.basename(file_source) if isinstance(file_source, str) else "uploaded_document.docx"
    else:
        file_source.seek(0)
        doc = docx.Document(file_source)
        file_name = getattr(file_source, 'name', 'uploaded_document.docx')

    system_document = parse_system_document(doc, file_name)
    if system_document is not None:
        return system_document

    res = {
        'file_name': file_name,
        'title': '',
        'job_code': '',
        'reports_to': '',
        'department': '',
        'sector': 'الإدارة العامة والمجموعة',
        'purpose': '',
        'dimensions': '',
        'accountabilities': [],
        'frameworks': '',
        'qualifications': '',
        'competencies': '',
        'hazards': '',
        'safe_practices': '',
        'internal_relations': '',
        'external_relations': '',
        'approvals': ''
    }

    if not doc.tables:
        text_lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        res['title'] = file_name.replace('.docx', '').replace('JD -', '').replace('JD _', '').replace('JD-', '').strip()
        res['purpose'] = '\n'.join(text_lines)
        return res

    for table in doc.tables:
        if not table.rows:
            continue
        
        header_text = ' '.join([c.text.strip() for c in table.rows[0].cells]).upper()

        # 1. JOB CODE & JOB DETAILS
        if any(k in header_text for k in ['JOB DETAILS', 'JOB CODE', 'بيانات الوظيفة', 'تفاصيل الوظيفة', 'كود الوظيفة']):
            for r in table.rows:
                cells = [c.text.strip() for c in r.cells]
                row_str = ' '.join(cells).upper()
                if any(k in row_str for k in ['POSITION TITLE', 'المسمى الوظيفي', 'اسم الوظيفة']) and len(cells) > 1:
                    res['title'] = cells[1].replace('Position Title:', '').replace('المسمى الوظيفي:', '').strip()
                elif any(k in row_str for k in ['REPORTS TO', 'المسؤول المباشر', 'الرئيس المباشر', 'يتبع']) and len(cells) > 1:
                    res['reports_to'] = cells[1].replace('Reports to:', '').replace('المسؤول المباشر:', '').strip()
                elif any(k in row_str for k in ['DEPARTMENT', 'الإدارة', 'الادارة']) and len(cells) > 1:
                    res['department'] = cells[1].replace('Department:', '').replace('الإدارة:', '').strip()
                elif any(k in row_str for k in ['SECTOR', 'القطاع']) and len(cells) > 1:
                    res['sector'] = cells[1].replace('Sector:', '').replace('القطاع:', '').strip()
                elif any(k in row_str for k in ['JOB CODE', 'كود الوظيفة']) and len(cells) > 1:
                    res['job_code'] = cells[1].replace('1. JOB CODE:', '').replace('JOB CODE:', '').replace('كود الوظيفة:', '').strip()

        # 2. JOB PURPOSE
        elif any(k in header_text for k in ['PURPOSE', 'الهدف العام', 'هدف الوظيفة', 'الغرض']):
            if len(table.rows) > 1:
                res['purpose'] = table.rows[1].cells[0].text.strip()

        # 3. JOB DIMENSIONS
        elif any(k in header_text for k in ['DIMENSION', 'أبعاد الوظيفة', 'ابعاد الوظيفة', 'النطاق الإشرافي']):
            dim_lines = []
            for r in table.rows[1:]:
                row_vals = [c.text.strip() for c in r.cells if c.text.strip()]
                unique_vals = []
                for v in row_vals:
                    if not unique_vals or unique_vals[-1] != v:
                        unique_vals.append(v)
                if unique_vals:
                    dim_lines.append(' | '.join(unique_vals))
            res['dimensions'] = '\n'.join(dim_lines)

        # 4. KEY ACCOUNTABILITIES
        elif any(k in header_text for k in ['ACCOUNTABILITIES', 'المسؤوليات', 'الواجبات', 'المهام']):
            start_idx = 1
            if len(table.rows) > 1:
                first_row_c0 = table.rows[1].cells[0].text.strip().upper()
                if any(k in first_row_c0 for k in ['DESCRIPTION', 'الوصف', 'بيان المسؤولية']):
                    start_idx = 2
            
            for r in table.rows[start_idx:]:
                cells = [c.text.strip() for c in r.cells]
                desc = cells[0] if len(cells) > 0 else ''
                kpi = cells[1] if len(cells) > 1 else ''
                if desc or kpi:
                    res['accountabilities'].append({'description': desc, 'kpi': kpi})

        # 5. FRAMEWORKS & AUTHORITY
        elif any(k in header_text for k in ['FRAMEWORK', 'AUTHORITY', 'الصلاحيات', 'حدود اتخاذ القرار', 'إطار العمل']):
            if len(table.rows) > 1:
                res['frameworks'] = table.rows[1].cells[0].text.strip()

        # 6. QUALIFICATIONS & SKILLS
        elif not any(k in header_text for k in ['COMPETENC', 'الجدارات', 'الكفاءات']) and any(k in header_text for k in ['QUALIFICATION', 'المؤهلات', 'الخبرات', 'المهارات', 'EXPERIENCE']):
            if len(table.rows) > 1:
                res['qualifications'] = table.rows[1].cells[0].text.strip()

        # 7. COMPETENCIES
        elif any(k in header_text for k in ['COMPETENC', 'الجدارات', 'الكفاءات']):
            lines = []
            for row in table.rows[1:]:
                seen_cells = set()
                values = []
                for cell in row.cells:
                    if cell._tc not in seen_cells:
                        seen_cells.add(cell._tc)
                        if cell.text.strip():
                            values.append(cell.text.strip())
                if values:
                    lines.append(' | '.join(values))
            res['competencies'] = '\n'.join(lines)

        # 8. JOB HAZARDS & SAFE PRACTICES
        elif any(k in header_text for k in ['HAZAARD', 'HAZARD', 'مخاطر', 'السلامة']):
            if len(table.rows) > 1:
                res['hazards'] = table.rows[1].cells[0].text.strip()
                if len(table.rows[1].cells) > 1:
                    res['safe_practices'] = table.rows[1].cells[1].text.strip()

        # 9. INTERNAL & EXTERNAL RELATIONS
        elif any(k in header_text for k in ['RELATION', 'العلاقات', 'الاتصال']):
            if len(table.rows) > 1:
                res['internal_relations'] = table.rows[1].cells[0].text.strip()
                if len(table.rows[1].cells) > 1:
                    res['external_relations'] = table.rows[1].cells[1].text.strip()

        # 10. APPROVALS
        elif any(k in header_text for k in ['APPROVAL', 'الاعتماد', 'التوقيع']):
            appr = []
            for r in table.rows[1:]:
                row_vals = [c.text.strip() for c in r.cells if c.text.strip()]
                if row_vals:
                    appr.append(' | '.join(row_vals))
            res['approvals'] = '\n'.join(appr)

    if not res['title']:
        clean_name = file_name.replace('.docx', '').replace('JD -', '').replace('JD _', '').replace('JD-', '').strip()
        res['title'] = clean_name

    return res


# One explicit format contract for all newly exported documents.
from docx_format import export_jd_to_docx
