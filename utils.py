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
    
    /* Inherit Cairo for text; never override every div/span or icon glyphs. */
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        direction: rtl;
        text-align: right;
        font-family: 'Cairo', Tahoma, sans-serif;
        box-sizing: border-box;
    }
    [data-testid="stAppViewContainer"] {
        width: 100% !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }
    .main, [data-testid="stMain"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }
    .main .block-container,
    [data-testid="stMain"] .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-top: 2.5rem !important;
        padding-right: 2.5rem !important;
        padding-left: 2.5rem !important;
        box-sizing: border-box !important;
        width: 100% !important;
        max-width: 100% !important;
        margin-right: 0 !important;
        margin-left: 0 !important;
    }
    [data-testid="stHorizontalBlock"] {
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        gap: 1.5rem;
    }
    [data-testid="stColumn"] {
        min-width: 0 !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }
    h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"], input, textarea, select, button {
        font-family: 'Cairo', Tahoma, sans-serif;
    }
    [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
    input, textarea, select, button, [data-testid="stAlert"] {
        direction: rtl;
        text-align: right;
        box-sizing: border-box;
    }
    [data-testid="stMarkdownContainer"] {
        width: 100%;
        max-width: 100%;
        overflow-wrap: break-word;
        word-break: normal;
    }
    [data-testid="stMarkdownContainer"] ul,
    [data-testid="stMarkdownContainer"] ol {
        direction: rtl;
        text-align: right;
        padding-right: 1.5rem !important;
        padding-left: 0 !important;
        margin-right: 0 !important;
        margin-left: 0 !important;
        box-sizing: border-box;
    }
    [data-testid="stMarkdownContainer"] li {
        direction: rtl;
        text-align: right;
        line-height: 1.75;
    }
    input, textarea { line-height: 1.8; }
    [data-testid="stIconMaterial"] {
        direction: ltr;
        text-align: center;
        flex-shrink: 0;
    }
    /* The canvas keeps its native coordinate system. Column config aligns text. */
    [data-testid="stDataFrame"] {
        direction: ltr;
        margin-top: 20px;
        margin-bottom: 18px;
        padding-top: 12px;
    }
    [data-testid="stTable"] table { direction: rtl; width: 100%; }
    [data-testid="stTable"] th, [data-testid="stTable"] td {
        text-align: right;
        padding: 10px 12px;
    }
    .stDeployButton, [data-testid="stAppDeployButton"],
    [data-testid="stMainMenu"], #MainMenu, footer { display: none !important; }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"],
    [data-testid="stSidebar"][data-collapsed="true"],
    [data-testid="stSidebar"][data-collapsed="false"],
    [data-testid="stSidebar"][aria-expanded="true"],
    [data-testid="stSidebar"][aria-expanded="false"] {
        width: 340px !important;
        min-width: 320px !important;
        max-width: 340px !important;
        flex: 0 0 340px !important;
        transform: none !important;
        transition: none !important;
        margin-right: 0 !important;
        margin-left: 0 !important;
        right: 0 !important;
        left: auto !important;
        box-sizing: border-box !important;
    }
    [data-testid="stSidebarContent"] {
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarResizeHandle"] {
        display: none !important;
    }
    [data-testid="stSidebarUserContent"] {
        padding: 1rem 1.1rem 1.5rem;
        box-sizing: border-box;
        width: 100%;
        max-width: 100%;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .65rem; }
    .sidebar-brand {
        padding: 4px 0 8px;
        line-height: 1.7;
        font-weight: 800;
        font-size: 15px;
        box-sizing: border-box;
        width: 100%;
        max-width: 100%;
    }
    .sidebar-brand small { display: block; color: #64748b; font-size: 11px; font-weight: 500; }
    .sidebar-profile {
        background: #fff; border: 1px solid #dbe3ef; border-radius: 12px;
        padding: 12px 14px; line-height: 1.7; margin-bottom: 2px;
        white-space: normal; word-break: normal; overflow-wrap: break-word;
        box-sizing: border-box; width: 100%; max-width: 100%; overflow: visible;
    }
    .sidebar-profile .profile-name { font-size: 16px; font-weight: 800; margin-bottom: 6px; }
    .sidebar-profile .profile-department { font-size: 12px; color: #475569; margin-top: 6px; }
    [data-testid="stSidebar"] [role="radiogroup"] { flex-direction: column; gap: 4px; }
    [data-testid="stSidebar"] [data-baseweb="radio"],
    [data-testid="stSidebar"] [data-testid="stRadioOption"] {
        margin: 0; padding: 5px 8px; border: 1px solid transparent; border-radius: 9px;
        align-items: flex-start; white-space: normal;
    }
    [data-testid="stSidebar"] [data-baseweb="radio"]:has(input:checked),
    [data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) {
        background: #e8f0ff; border-color: #b8cff9;
    }
    .st-key-primary_navigation [role="radiogroup"] > div:nth-child(7) label {
        border-color: #c7d8f5; font-weight: 800; background: #f0f5ff;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        word-break: normal; white-space: normal; line-height: 1.65;
    }
    [data-testid="stAlert"] {
        padding: 14px 18px;
        overflow: visible;
        box-sizing: border-box;
        width: 100%;
        max-width: 100%;
    }
    [data-testid="stCode"] { direction: ltr; text-align: left; }
    [data-testid="stTabs"] [role="tablist"] { gap: 8px; flex-wrap: wrap; }
    button[data-baseweb="tab"] { font-weight: 700; }
    @media (max-width: 768px) {
        [data-testid="stAppViewContainer"] {
            flex-direction: column !important;
            overflow-y: auto !important;
        }
        [data-testid="stSidebar"],
        [data-testid="stSidebar"][data-collapsed="true"],
        [data-testid="stSidebar"][aria-expanded="false"] {
            width: 100% !important;
            min-width: 0 !important;
            max-width: 100% !important;
            flex: 0 0 auto !important;
            height: auto !important;
            transform: none !important;
        }
        .main, [data-testid="stMain"] {
            height: auto !important;
        }
        .main .block-container,
        [data-testid="stMain"] .block-container,
        [data-testid="stMainBlockContainer"] {
            padding-right: 1.25rem !important;
            padding-left: 1.25rem !important;
        }
        .brand-header { flex-direction: column; align-items: stretch; gap: 12px; padding: 18px; }
        .brand-title { font-size: 1.3rem; }
    }

    /* Top Brand Header */
    .brand-header {
        background: linear-gradient(135deg, #0a2540 0%, #173b64 60%, #1e5a88 100%);
        color: white;
        padding: 1.1rem 1.4rem;
        border-radius: 12px;
        margin: 0 0 1.5rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        justify-content: space-between;
        align-items: center;
        direction: rtl;
        text-align: right;
        box-sizing: border-box !important;
        width: 100% !important;
        max-width: 100% !important;
        overflow: visible;
    }
    .brand-header > div {
        min-width: 0;
        max-width: 100%;
        box-sizing: border-box;
    }
    .brand-title {
        font-size: 1.4rem;
        line-height: 1.6;
        font-weight: 800;
        margin: 0;
        color: #ffffff;
        overflow-wrap: break-word;
        word-break: normal;
    }
    .brand-subtitle {
        font-size: 0.85rem;
        color: #93c5fd;
        margin-top: 4px;
        font-weight: 500;
        overflow-wrap: break-word;
        word-break: normal;
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
        box-sizing: border-box !important;
        width: 100%;
        max-width: 100%;
        overflow: visible;
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
        margin: 0 0 1.2rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        direction: rtl;
        text-align: right;
        box-sizing: border-box !important;
        width: 100%;
        max-width: 100%;
        overflow: visible;
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
        max-width: 100%;
        white-space: normal;
        line-height: 1.8;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 700;
        box-sizing: border-box;
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
        box-sizing: border-box !important;
        width: 100%;
        max-width: 100%;
        overflow: visible;
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
