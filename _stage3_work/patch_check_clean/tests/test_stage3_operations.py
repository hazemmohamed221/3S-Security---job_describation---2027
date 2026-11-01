"""Production configuration, exact locks and fail-closed advisory checks."""
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tomllib

import pytest

from scripts import audit_dependencies as audit
from scripts.lock_dependencies import APP_ROOTS, dependency_closure, generate

ROOT = Path(__file__).resolve().parents[1]


def test_production_configuration_masks_errors_and_preserves_origin_protection():
    config = tomllib.loads((ROOT / '.streamlit/config.toml').read_text(encoding='utf-8'))
    assert config['browser']['gatherUsageStats'] is False
    assert config['client']['showErrorDetails'] is False
    assert config['server']['enableCORS'] is True and config['server']['enableXsrfProtection'] is True
    assert config['server']['maxUploadSize'] == 10
    assert config['runner']['magicEnabled'] is False


def test_lock_is_exact_complete_and_excludes_unrelated_host_packages():
    pins = audit.read_lock(ROOT / 'requirements.lock')
    assert pins == dependency_closure(APP_ROOTS)
    assert pins['pillow'] == '13.0.0' and pins['streamlit'] == '1.66.1'
    assert 'pywin32' not in pins and 'weasyprint' not in pins
    generate(check=True)
    docker = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
    assert '-r requirements.lock' in docker and '--upgrade pip' not in docker


@pytest.mark.parametrize('line', ['streamlit>=1.35', 'streamlit', 'streamlit==1.66.1\nstreamlit==1.66.1', '-r requirements.txt', ''])
def test_incomplete_or_nonexact_lock_rejected(tmp_path, line):
    path = tmp_path / 'bad.lock'
    path.write_text(line, encoding='utf-8')
    with pytest.raises(ValueError):
        audit.read_lock(path)


def runner_ok(*args, **kwargs):
    assert args[0][-3:] == ['-m', 'pip', 'check']
    return SimpleNamespace(returncode=0, stdout='No broken requirements found.', stderr='')


def test_audit_runs_pip_and_full_online_scan():
    called = []
    def query(pins):
        called.append(pins)
        return []
    report = audit.audit(runner=runner_ok, query=query)
    assert report['pip_check'] == 'passed' and report['online_complete']
    assert report['package_count'] == len(called[0]) == 43 and report['findings'] == []


def test_audit_reports_vulnerabilities_instead_of_suppressing_them():
    finding = {'package': 'pillow', 'version': '13.0.0', 'id': 'SYNTHETIC-ADVISORY'}
    report = audit.audit(runner=runner_ok, query=lambda pins: [finding])
    assert report['findings'] == [finding]


def test_pip_failure_prevents_advisory_success():
    with pytest.raises(RuntimeError, match='pip check failed'):
        audit.audit(runner=lambda *a, **k: SimpleNamespace(returncode=1, stdout='broken', stderr=''))


def test_lock_drift_and_missing_closure_fail():
    with pytest.raises(RuntimeError, match='differs from lock'):
        audit.audit(runner=runner_ok, version=lambda name: '0')
    with pytest.raises(RuntimeError, match='complete application'):
        audit.audit(runner=runner_ok, closure=lambda roots: {})


@pytest.mark.parametrize('package,version', [('streamlit', '1.53.0'), ('pillow', '12.3.0')])
def test_known_insecure_floor_detected_offline(tmp_path, package, version):
    lock = tmp_path / 'unsafe.lock'
    lock.write_text(f'{package}=={version}\n', encoding='utf-8')
    with pytest.raises(RuntimeError, match='Known insecure'):
        audit.audit(lock, online=False, runner=runner_ok, version=lambda name: version)


def test_offline_result_is_explicitly_partial():
    report = audit.audit(online=False, runner=runner_ok, query=lambda p: pytest.fail('Offline should not call network'))
    assert not report['online_complete'] and 'offline' in report['source']


def test_osv_payload_contains_only_package_versions():
    def opener(request, timeout):
        body = json.loads(request.data)
        assert body == {'queries': [{'package': {'name': 'pillow', 'ecosystem': 'PyPI'}, 'version': '13.0.0'}]}
        assert timeout == 30 and request.full_url == audit.OSV_ENDPOINT
        return io.BytesIO(b'{"results":[{}]}')
    assert audit.query_osv({'pillow': '13.0.0'}, opener=opener) == []


@pytest.mark.parametrize('response', [b'{}', b'{"results":[]}', b'{"results":[{"error":"unavailable"}]}',
                                    b'{"results":[{"next_page_token":"more"}]}', b'{"results":[{"vulns":[{}]}]}'])
def test_osv_partial_or_malformed_responses_never_pass(response):
    with pytest.raises(RuntimeError):
        audit.query_osv({'pillow': '13.0.0'}, opener=lambda *a, **k: io.BytesIO(response))


def test_network_failure_is_audit_failure():
    def unavailable(*args, **kwargs):
        raise OSError('network unavailable')
    with pytest.raises(OSError):
        audit.audit(runner=runner_ok, query=unavailable)
