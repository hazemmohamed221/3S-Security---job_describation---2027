"""
Utility functions for text diffing, HTML styling, and RTL Arabic presentation.
"""

import difflib
import html
import re


def generate_diff_html(old_text, new_text):
    """
    Generates an RTL HTML snippet comparing old_text and new_text with colored highlights:
    - Red strike-through for deleted words.
    - Green highlighted bold for added words.
    """
    old_text = old_text or ""
    new_text = new_text or ""

    old_words = re.findall(r'\S+|\n|\s+', old_text)
    new_words = re.findall(r'\S+|\n|\s+', new_text)

    matcher = difflib.SequenceMatcher(None, old_words, new_words)
    diff_html_parts = []

    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == 'equal':
            chunk = "".join(old_words[a0:a1])
            diff_html_parts.append(html.escape(chunk).replace('\n', '<br>'))
        elif opcode == 'insert':
            chunk = "".join(new_words[b0:b1])
            diff_html_parts.append(
                f'<span style="background-color: #d1fae5; color: #065f46; font-weight: 700; padding: 2px 6px; border-radius: 4px; border: 1px solid #a7f3d0;">+ {html.escape(chunk).replace(chr(10), "<br>")}</span>'
            )
        elif opcode == 'delete':
            chunk = "".join(old_words[a0:a1])
            diff_html_parts.append(
                f'<span style="background-color: #fee2e2; color: #991b1b; text-decoration: line-through; padding: 2px 6px; border-radius: 4px; border: 1px solid #fecdd3;">- {html.escape(chunk).replace(chr(10), "<br>")}</span>'
            )
        elif opcode == 'replace':
            old_chunk = "".join(old_words[a0:a1])
            new_chunk = "".join(new_words[b0:b1])
            diff_html_parts.append(
                f'<span style="background-color: #fee2e2; color: #991b1b; text-decoration: line-through; padding: 2px 6px; border-radius: 4px; border: 1px solid #fecdd3;">- {html.escape(old_chunk).replace(chr(10), "<br>")}</span> '
                f'<span style="background-color: #d1fae5; color: #065f46; font-weight: 700; padding: 2px 6px; border-radius: 4px; border: 1px solid #a7f3d0;">+ {html.escape(new_chunk).replace(chr(10), "<br>")}</span>'
            )

    return f'<div style="direction: rtl; text-align: right; line-height: 2; font-family: Cairo, Tahoma, sans-serif;">{"".join(diff_html_parts)}</div>'


def get_custom_css():
    """Returns custom CSS styles for a complete Right-to-Left (RTL) Arabic layout."""
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&display=swap');
    
    /* Global RTL Direction & Font */
    html, body, [data-testid="stAppViewContainer"], .main, [data-testid="stSidebar"], [data-testid="stSidebarContent"], .stApp {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Cairo', -apple-system, BlinkMacSystemFont, Tahoma, sans-serif !important;
    }

    /* Streamlit components RTL overrides */
    h1, h2, h3, h4, h5, h6, p, div, span, label, input, textarea, select, button {
        font-family: 'Cairo', -apple-system, BlinkMacSystemFont, Tahoma, sans-serif !important;
        text-align: right !important;
    }

    /* RTL for Dataframes and Tables */
    div[data-testid="stDataFrame"], div[data-testid="stTable"] {
        direction: rtl !important;
        text-align: right !important;
    }
    div[data-testid="stDataFrame"] * {
        text-align: right !important;
        direction: rtl !important;
    }
    table {
        direction: rtl !important;
        text-align: right !important;
        width: 100% !important;
        border-collapse: collapse !important;
    }
    th {
        background-color: #1e3a5f !important;
        color: white !important;
        text-align: right !important;
        font-weight: 700 !important;
        padding: 10px 12px !important;
    }
    td {
        text-align: right !important;
        padding: 8px 12px !important;
        border-bottom: 1px solid #e2e8f0 !important;
    }

    /* Tabs RTL */
    button[data-baseweb="tab"] {
        direction: rtl !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
    }

    /* Top Brand Header */
    .brand-header {
        background: linear-gradient(135deg, #0a2540 0%, #173b64 60%, #1e5a88 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        display: flex;
        justify-content: space-between;
        align-items: center;
        direction: rtl;
        text-align: right;
    }
    .brand-title {
        font-size: 1.75rem;
        font-weight: 800;
        margin: 0;
        color: #ffffff;
    }
    .brand-subtitle {
        font-size: 0.95rem;
        color: #93c5fd;
        margin-top: 4px;
        font-weight: 500;
    }

    /* Metric Card */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        text-align: center !important;
        transition: transform 0.2s, box-shadow 0.2s;
        direction: rtl;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(0,0,0,0.08);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e3a8a;
    }
    .metric-label {
        font-size: 0.9rem;
        font-weight: 700;
        color: #64748b;
        margin-top: 4px;
    }

    /* Section Cards */
    .jd-section-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-right: 5px solid #2563eb;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        direction: rtl;
        text-align: right;
    }
    .jd-section-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 0.75rem;
        border-bottom: 2px solid #f1f5f9;
        padding-bottom: 6px;
    }

    /* Badges */
    .status-badge {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 700;
    }
    .badge-approved {
        background-color: #d1fae5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }
    .badge-under-review {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }
    .badge-pending {
        background-color: #dbeafe;
        color: #1e40af;
        border: 1px solid #bfdbfe;
    }
    .badge-rejected {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecdd3;
    }

    /* Diff View Boxes */
    .diff-box {
        border-radius: 8px;
        padding: 1.1rem;
        margin: 0.5rem 0;
        font-size: 1rem;
        line-height: 1.9;
        direction: rtl;
        text-align: right;
    }
    .diff-old {
        background-color: #fff1f2;
        border: 1px solid #fecdd3;
        color: #881337;
    }
    .diff-new {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: #14532d;
    }

    /* Radio buttons & Checkboxes aligned right */
    div[data-testid="stRadio"] > div {
        flex-direction: row-reverse !important;
        justify-content: flex-end !important;
    }

    /* Expander header bold */
    div[data-testid="stExpander"] details summary {
        font-weight: 700 !important;
        direction: rtl !important;
        text-align: right !important;
    }
    </style>
    """


def is_arabic(text):
    """Detects whether text contains Arabic characters."""
    if not text:
        return True
    return bool(re.search(r'[\u0600-\u06FF]', str(text)))
