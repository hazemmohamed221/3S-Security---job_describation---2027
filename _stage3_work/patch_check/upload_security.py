"""Bounded DOCX intake and filenames safe for HTML, Windows paths and downloads."""
import io
import os
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote, unquote
from zipfile import BadZipFile, ZipFile

DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def max_upload_bytes():
    raw = os.environ.get('JD_MAX_UPLOAD_BYTES', str(DEFAULT_MAX_UPLOAD_BYTES))
    try:
        limit = int(raw)
    except ValueError as exc:
        raise ValueError('JD_MAX_UPLOAD_BYTES must be a positive integer.') from exc
    if limit <= 0:
        raise ValueError('JD_MAX_UPLOAD_BYTES must be a positive integer.')
    return limit


def upload_limit_megabytes():
    """Widget limit follows the backend setting; the byte check stays exact."""
    return (max_upload_bytes() + 1024 * 1024 - 1) // (1024 * 1024)


def sanitize_docx_filename(name):
    # Decode encoded separators before removing path components. Never join this
    # untrusted name to a disk path; the parser consumes an in-memory stream.
    name = str(name or '')[:4096]
    for _ in range(3):
        decoded = unquote(name)
        if decoded == name:
            break
        name = decoded
    name = unicodedata.normalize('NFKC', name).replace('\\', '/').split('/')[-1]
    name = re.sub(r'(?i)\.docx$', '', name)
    safe = ''.join(c if (unicodedata.category(c)[0] in ('L', 'N') or c in ' _-') else '_'
                   for c in name)
    safe = re.sub(r'[ _-]+', '_', safe).strip('_')[:100]
    safe = safe.encode('utf-8')[:180].decode('utf-8', errors='ignore').rstrip('_') or 'document'
    if safe.upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        safe = 'document_' + safe
    return safe + '.docx'


def download_filename(card, *, url_encoded=False):
    identifier = re.sub('[^A-Za-z0-9_-]', '_', str(card.get('id') or 'new'))[:24]
    title = sanitize_docx_filename(card.get('title') or 'Job_Description')[:-5]
    title = title.encode('utf-8')[:120].decode('utf-8', errors='ignore')
    name = f'3S-JD-{identifier}_{title}_بطاقة_وصف_وظيفي.docx'
    # Streamlit percent-encodes Unicode in RFC 5987 filename* itself. Give it the
    # readable name; encode once here only for callers constructing a URL.
    return quote(name, safe='-_.', encoding='utf-8', errors='strict') if url_encoded else name


def validated_docx(source):
    """Validate before python-docx/lxml sees the archive; return bounded bytes."""
    limit = max_upload_bytes()
    if isinstance(source, (str, bytes, os.PathLike)):
        path = Path(source)
        if path.stat().st_size > limit:
            raise ValueError('يتجاوز حجم ملف Word الحد المسموح.')
        with path.open('rb') as handle:
            data = handle.read(limit + 1)
        name = path.name
    else:
        name = getattr(source, 'name', 'uploaded_document.docx')
        claimed_size = getattr(source, 'size', None)
        if isinstance(claimed_size, int) and claimed_size > limit:
            raise ValueError('يتجاوز حجم ملف Word الحد المسموح.')
        original = source.tell()
        try:
            source.seek(0)
            data = source.read(limit + 1)
        finally:
            source.seek(original)
    if not isinstance(data, bytes) or len(data) > limit:
        raise ValueError('يتجاوز حجم ملف Word الحد المسموح أو أن نوع الملف غير صالح.')
    if not str(name).lower().endswith('.docx') or not data.startswith(b'PK\x03\x04'):
        raise ValueError('يجب رفع ملف Word بصيغة DOCX وتوقيع ZIP صحيح.')
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [item.filename for item in entries]
            if len(entries) > 2048 or len(names) != len(set(names)):
                raise ValueError('يحتوي ملف Word على عدد غير مسموح أو مكرر من المكونات.')
            if not {'[Content_Types].xml', '_rels/.rels', 'word/document.xml'}.issubset(names):
                raise ValueError('الملف ليس حزمة Word صالحة.')
            total = 0
            expanded_limit = max(limit * 5, 5 * 1024 * 1024)
            for item in entries:
                parts = item.filename.replace('\\', '/').split('/')
                if (item.filename.startswith(('/', '\\')) or '..' in parts or ':' in item.filename or
                        item.flag_bits & 1 or (item.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError('يحتوي ملف Word على مكونات غير آمنة.')
                total += item.file_size
                if total > expanded_limit or item.file_size > expanded_limit:
                    raise ValueError('حجم مكونات ملف Word بعد فك الضغط غير مسموح.')
            if archive.testzip() is not None:
                raise ValueError('أحد مكونات ملف Word تالف.')
    except (BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise ValueError('تعذر التحقق من سلامة حزمة Word.') from exc
    result = io.BytesIO(data)
    result.name = sanitize_docx_filename(name)
    return result
