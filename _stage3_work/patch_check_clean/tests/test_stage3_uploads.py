"""Bounded intake, filename handling and existing Arabic Word fidelity."""
import io
from urllib.parse import unquote
from zipfile import ZipFile, ZIP_DEFLATED

import docx
import pytest

import database
from docx_parser import parse_jd_docx
from upload_security import (DEFAULT_MAX_UPLOAD_BYTES, download_filename, max_upload_bytes,
                             sanitize_docx_filename, validated_docx, upload_limit_megabytes)


def document(name='اختبار.docx'):
    file = io.BytesIO()
    doc = docx.Document()
    doc.add_paragraph('نص عربي محفوظ')
    doc.save(file)
    file.name = name
    file.seek(0)
    return file


def test_default_and_configured_size_limits(monkeypatch):
    monkeypatch.delenv('JD_MAX_UPLOAD_BYTES', raising=False)
    assert max_upload_bytes() == DEFAULT_MAX_UPLOAD_BYTES
    file = document()
    length = len(file.getvalue())
    monkeypatch.setenv('JD_MAX_UPLOAD_BYTES', str(length))
    assert validated_docx(file).getvalue() == file.getvalue()
    monkeypatch.setenv('JD_MAX_UPLOAD_BYTES', str(length - 1))
    with pytest.raises(ValueError):
        parse_jd_docx(file)


@pytest.mark.parametrize('limit', ['0', '-1', 'bad', '10.5'])
def test_invalid_limit_fails_closed(monkeypatch, limit):
    monkeypatch.setenv('JD_MAX_UPLOAD_BYTES', limit)
    with pytest.raises(ValueError):
        validated_docx(document())


def test_widget_limit_tracks_byte_configuration_with_safe_rounding(monkeypatch):
    monkeypatch.setenv('JD_MAX_UPLOAD_BYTES', str(20 * 1024 * 1024))
    assert upload_limit_megabytes() == 20
    monkeypatch.setenv('JD_MAX_UPLOAD_BYTES', str(1024 * 1024 + 1))
    assert upload_limit_megabytes() == 2


def test_claimed_size_rejected_before_reading():
    class Upload:
        name = 'large.docx'
        size = DEFAULT_MAX_UPLOAD_BYTES + 1
        def read(self, *args):
            pytest.fail('Oversized upload must be rejected before reading')
    with pytest.raises(ValueError):
        validated_docx(Upload())


@pytest.mark.parametrize('data,name', [(b'<script>bad</script>', 'x.docx'), (b'PK\x03\x04not-a-zip', 'x.docx'),
                                       (b'plain text', 'x.docx'), (b'PK\x03\x04', 'x.exe')])
def test_extension_and_zip_magic_are_not_sufficient(data, name):
    file = io.BytesIO(data)
    file.name = name
    with pytest.raises(ValueError):
        parse_jd_docx(file)


@pytest.mark.parametrize('entry', ['../../escape.xml', '/absolute.xml', 'C:/escape.xml', 'word/../escape.xml'])
def test_archive_path_traversal_rejected(entry):
    file = document()
    with ZipFile(file, 'a') as archive:
        archive.writestr(entry, '<xml/>')
    with pytest.raises(ValueError):
        validated_docx(file)


def test_generic_zip_and_zip_expansion_bomb_rejected(monkeypatch):
    generic = io.BytesIO()
    with ZipFile(generic, 'w') as archive:
        archive.writestr('readme.txt', 'unrelated')
    with pytest.raises(ValueError):
        validated_docx(generic)
    bomb = document()
    with ZipFile(bomb, 'a', compression=ZIP_DEFLATED) as archive:
        archive.writestr('word/bomb.xml', 'x' * (6 * 1024 * 1024))
    monkeypatch.setenv('JD_MAX_UPLOAD_BYTES', '100000')
    validated_docx(document())
    with pytest.raises(ValueError):
        validated_docx(bomb)


def test_duplicate_zip_entries_rejected():
    file = document()
    with ZipFile(file, 'a') as archive:
        with pytest.warns(UserWarning, match='Duplicate'):
            archive.writestr('word/document.xml', 'duplicate')
    with pytest.raises(ValueError):
        validated_docx(file)


@pytest.mark.parametrize('name', ['../../بطاقة.docx', '..\\..\\card.docx', '%2e%2e%2fcard.docx',
                                 '%252e%252e%252fcard.docx', '<script>alert(1)</script>.docx',
                                 'evil\r\nX-Header:yes.docx', 'CON.docx', '\u202eevil.docx'])
def test_uploaded_names_are_safe_and_keep_docx_extension(name):
    safe = sanitize_docx_filename(name)
    assert safe.endswith('.docx')
    assert not any(char in safe for char in '/\\<>:\r\n%\u202e')
    assert '..' not in safe and safe != 'CON.docx'


def test_valid_arabic_input_keeps_text_and_stream_position():
    file = document('../../مدير الموارد البشرية.docx')
    file.seek(8)
    parsed = parse_jd_docx(file)
    assert file.tell() == 8
    assert parsed['file_name'] == 'مدير_الموارد_البشرية.docx'
    assert parsed['purpose'] == 'نص عربي محفوظ'


def test_filename_based_legacy_title_remains_readable_after_sanitizing():
    parsed = parse_jd_docx(document('../../JD - مدير مالي.docx'))
    assert parsed['title'] == 'مدير مالي'
    assert parsed['purpose'] == 'نص عربي محفوظ'


def test_safe_download_has_stable_identifier_and_one_url_encoding_layer():
    card = {'id': 26, 'title': '../../مدير <script>\r\n'}
    plain = download_filename(card)
    encoded = download_filename(card, url_encoded=True)
    assert plain.startswith('3S-JD-26_') and 'بطاقة_وصف_وظيفي' in plain
    assert not any(c in plain for c in '/\\<>:\r\n')
    assert unquote(encoded) == plain and encoded.isascii() and '%D8' in encoded
    assert '%25D8' not in encoded


def test_backend_sanitizes_import_provenance_even_without_ui(sign_in, db):
    sign_in('hr')
    jd_id = database.create_or_update_jd({'title': 'بطاقة اختبار'}, '../../evil<script>.docx', actor_id=1)
    assert database.get_jd_by_id(jd_id)['source_file'] == 'evil_script.docx'
