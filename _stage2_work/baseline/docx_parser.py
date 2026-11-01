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
        elif any(k in header_text for k in ['QUALIFICATION', 'المؤهلات', 'الخبرات', 'المهارات', 'EXPERIENCE']):
            if len(table.rows) > 1:
                res['qualifications'] = table.rows[1].cells[0].text.strip()

        # 7. COMPETENCIES
        elif any(k in header_text for k in ['COMPETENC', 'الجدارات', 'الكفاءات']):
            if len(table.rows) > 1:
                res['competencies'] = table.rows[1].cells[0].text.strip()

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


def export_jd_to_docx(jd_data, accountabilities):
    """
    Exports a structured JD into a professional Arabic RTL Word document (.docx).
    """
    doc = docx.Document()

    # Document Header Title
    title_p = doc.add_paragraph()
    set_p_rtl(title_p)
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_p.add_run("شركة ثري إس للأنظمة الأمنية (3S Security Systems)\nبطاقة الوصف والتوصيف الوظيفي المعتمدة")
    run.font.name = "Arial"
    run.font.size = Pt(16)
    run.font.bold = True
    run.font.color.rgb = RGBColor(15, 43, 72)

    # 1. Job Profile Details Table
    h1 = doc.add_heading("١. بيانات وبطاقة الوظيفة", level=2)
    set_p_rtl(h1)

    tbl_profile = doc.add_table(rows=5, cols=2)
    tbl_profile.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_profile.style = 'Table Grid'

    profile_data = [
        ("كود الوظيفة:", jd_data.get('job_code', '') or '3S-JD-001'),
        ("المسمى الوظيفي:", jd_data.get('title', '')),
        ("الإدارة التابع لها:", jd_data.get('department', '') or 'الإدارة العامة'),
        ("القطاع:", jd_data.get('sector', '') or 'الإدارة العامة والمجموعة'),
        ("المسؤول المباشر:", jd_data.get('reports_to', '') or 'الإدارة العليا')
    ]

    for i, (k, v) in enumerate(profile_data):
        cell_k = tbl_profile.rows[i].cells[0]
        cell_v = tbl_profile.rows[i].cells[1]
        cell_k.text = k
        cell_v.text = v or "—"
        set_cell_background(cell_k, "F0F4F8")
        set_p_rtl(cell_k.paragraphs[0])
        set_p_rtl(cell_v.paragraphs[0])
        cell_k.paragraphs[0].runs[0].font.bold = True
        cell_k.paragraphs[0].runs[0].font.name = "Arial"
        cell_v.paragraphs[0].runs[0].font.name = "Arial"

    # 2. Purpose
    h2 = doc.add_heading("٢. الهدف العام من الوظيفة", level=2)
    set_p_rtl(h2)
    p_purpose = doc.add_paragraph(jd_data.get('purpose', '') or "لم يتم تحديد وصف الهدف العام بعد.")
    set_p_rtl(p_purpose)

    # 3. Dimensions
    if jd_data.get('dimensions'):
        h3 = doc.add_heading("٣. أبعاد الوظيفة والنطاق الإشرافي", level=2)
        set_p_rtl(h3)
        p_dim = doc.add_paragraph(jd_data.get('dimensions', ''))
        set_p_rtl(p_dim)

    # 4. Key Accountabilities
    h4 = doc.add_heading("٤. المسؤوليات والواجبات الرئيسية ومؤشرات قياس الأداء (KPIs)", level=2)
    set_p_rtl(h4)

    if accountabilities:
        tbl_acc = doc.add_table(rows=len(accountabilities) + 1, cols=3)
        tbl_acc.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_acc.style = 'Table Grid'

        # Headers
        h_seq = tbl_acc.rows[0].cells[0]
        h_desc = tbl_acc.rows[0].cells[1]
        h_kpi = tbl_acc.rows[0].cells[2]

        h_seq.text = "م"
        h_desc.text = "بيان المسؤولية والواجب الوظيفي"
        h_kpi.text = "مؤشر قياس الأداء (KPI)"

        for h in [h_seq, h_desc, h_kpi]:
            set_cell_background(h, "1A365D")
            set_p_rtl(h.paragraphs[0])
            h.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
            h.paragraphs[0].runs[0].font.bold = True
            h.paragraphs[0].runs[0].font.name = "Arial"

        for idx, acc in enumerate(accountabilities):
            row = tbl_acc.rows[idx + 1]
            row.cells[0].text = str(acc.get('item_order', idx + 1))
            row.cells[1].text = acc.get('description', '')
            row.cells[2].text = acc.get('kpi', '') or "—"
            
            for c in row.cells:
                set_p_rtl(c.paragraphs[0])
                c.paragraphs[0].runs[0].font.name = "Arial"

            if idx % 2 == 1:
                set_cell_background(row.cells[0], "F9FAFB")
                set_cell_background(row.cells[1], "F9FAFB")
                set_cell_background(row.cells[2], "F9FAFB")

    # 5. Frameworks & Authority
    if jd_data.get('frameworks'):
        h5 = doc.add_heading("٥. إطار العمل وحدود اتخاذ القرارات والصلاحيات", level=2)
        set_p_rtl(h5)
        p_fw = doc.add_paragraph(jd_data.get('frameworks', ''))
        set_p_rtl(p_fw)

    # 6. Qualifications & Skills
    if jd_data.get('qualifications'):
        h6 = doc.add_heading("٦. المؤهلات العلمية والخبرات والمهارات المطلوبة", level=2)
        set_p_rtl(h6)
        p_qual = doc.add_paragraph(jd_data.get('qualifications', ''))
        set_p_rtl(p_qual)

    # 7. Hazards & Safe Practices
    h7 = doc.add_heading("٧. مخاطر الوظيفة وممارسات السلامة والصحة المهنية", level=2)
    set_p_rtl(h7)
    tbl_haz = doc.add_table(rows=2, cols=2)
    tbl_haz.style = 'Table Grid'
    tbl_haz.rows[0].cells[0].text = "مخاطر الوظيفة وبيئة العمل"
    tbl_haz.rows[0].cells[1].text = "ممارسات وإجراءات السلامة المتبعة"
    set_cell_background(tbl_haz.rows[0].cells[0], "F0F4F8")
    set_cell_background(tbl_haz.rows[0].cells[1], "F0F4F8")
    set_p_rtl(tbl_haz.rows[0].cells[0].paragraphs[0])
    set_p_rtl(tbl_haz.rows[0].cells[1].paragraphs[0])

    tbl_haz.rows[1].cells[0].text = jd_data.get('hazards', '') or "بيئة مكتبية اعتيادية ومخاطر استخدام الحاسب الآلي."
    tbl_haz.rows[1].cells[1].text = jd_data.get('safe_practices', '') or "توفير التجهيزات المكتبية المناسبة والالتزام بإرشادات السلامة."
    set_p_rtl(tbl_haz.rows[1].cells[0].paragraphs[0])
    set_p_rtl(tbl_haz.rows[1].cells[1].paragraphs[0])

    # 8. Internal & External Relations
    h8 = doc.add_heading("٨. شبكة العلاقات والاتصال الوظيفي", level=2)
    set_p_rtl(h8)
    tbl_rel = doc.add_table(rows=2, cols=2)
    tbl_rel.style = 'Table Grid'
    tbl_rel.rows[0].cells[0].text = "العلاقات والاتصالات الداخلية"
    tbl_rel.rows[0].cells[1].text = "العلاقات والاتصالات الخارجية"
    set_cell_background(tbl_rel.rows[0].cells[0], "F0F4F8")
    set_cell_background(tbl_rel.rows[0].cells[1], "F0F4F8")
    set_p_rtl(tbl_rel.rows[0].cells[0].paragraphs[0])
    set_p_rtl(tbl_rel.rows[0].cells[1].paragraphs[0])

    tbl_rel.rows[1].cells[0].text = jd_data.get('internal_relations', '') or "كافة إدارات وأقسام الشركة المعنية."
    tbl_rel.rows[1].cells[1].text = jd_data.get('external_relations', '') or "العملاء، الموردين، والجهات الحكومية والرقابية."
    set_p_rtl(tbl_rel.rows[1].cells[0].paragraphs[0])
    set_p_rtl(tbl_rel.rows[1].cells[1].paragraphs[0])

    # 9. Signatures / Status
    h9 = doc.add_heading("٩. محضر الاعتماد والتوقيعات", level=2)
    set_p_rtl(h9)
    tbl_appr = doc.add_table(rows=2, cols=3)
    tbl_appr.style = 'Table Grid'
    tbl_appr.rows[0].cells[0].text = "شاغل الوظيفة / المدير المسؤول"
    tbl_appr.rows[0].cells[1].text = "مدير إدارة الموارد البشرية"
    tbl_appr.rows[0].cells[2].text = "العضو المنتدب والمدير التنفيذي"
    for c in tbl_appr.rows[0].cells:
        set_cell_background(c, "F0F4F8")
        set_p_rtl(c.paragraphs[0])
        c.paragraphs[0].runs[0].font.bold = True
    tbl_appr.rows[1].cells[0].text = "التوقيع: ............................\nالتاريخ:    /    / 2027"
    tbl_appr.rows[1].cells[1].text = "التوقيع: ............................\nالتاريخ:    /    / 2027"
    tbl_appr.rows[1].cells[2].text = "التوقيع: ............................\nالتاريخ:    /    / 2027"
    for c in tbl_appr.rows[1].cells:
        set_p_rtl(c.paragraphs[0])

    # Footer
    p_status = doc.add_paragraph(
        f"حالة الوثيقة: {jd_data.get('status', 'قيد المراجعة')} | الإصدار: {jd_data.get('version', 1)} | صدرت إلكترونياً عبر منصة ثري إس للأنظمة الأمنية 2027"
    )
    set_p_rtl(p_status)
    p_status.paragraph_format.space_before = Pt(14)

    target_stream = io.BytesIO()
    doc.save(target_stream)
    target_stream.seek(0)
    return target_stream
