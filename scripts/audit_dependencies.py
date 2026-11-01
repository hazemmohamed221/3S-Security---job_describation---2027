"""Fail-closed pip consistency, lock-drift and live OSV vulnerability audit."""
import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import Request, urlopen

from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))
from scripts.lock_dependencies import APP_ROOTS, dependency_closure
OSV_ENDPOINT = 'https://api.osv.dev/v1/querybatch'


def read_lock(path):
    pins = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9.+!-]+)', line)
        if not match:
            raise ValueError('The production lock must contain only exact package==version pins.')
        name = canonicalize_name(match[1])
        if name in pins:
            raise ValueError('Duplicate package in lock.')
        pins[name] = match[2]
    if not pins:
        raise ValueError('Dependency lock is empty.')
    return pins


def query_osv(pins, *, opener=urlopen):
    packages = sorted(pins.items())
    results = []
    for offset in range(0, len(packages), 100):
        batch = packages[offset:offset + 100]
        payload = {'queries': [{'package': {'name': name, 'ecosystem': 'PyPI'}, 'version': version}
                               for name, version in batch]}
        request = Request(OSV_ENDPOINT, data=json.dumps(payload).encode('utf-8'),
                          headers={'Content-Type': 'application/json', 'User-Agent': '3S-dependency-audit/1'})
        with opener(request, timeout=30) as response:
            result = json.load(response)
        if not isinstance(result.get('results'), list) or len(result['results']) != len(batch):
            raise RuntimeError('Incomplete OSV response; audit did not pass.')
        for (name, version), item in zip(batch, result['results']):
            if not isinstance(item, dict) or item.get('next_page_token') or item.get('error'):
                raise RuntimeError('Incomplete/paginated OSV response; audit did not pass.')
            vulns = item.get('vulns', [])
            if not isinstance(vulns, list) or any(not isinstance(v, dict) or not v.get('id') for v in vulns):
                raise RuntimeError('Malformed OSV findings; audit did not pass.')
            results.extend({'package': name, 'version': version, 'id': vuln['id']} for vuln in vulns)
    return results


def audit(lock=ROOT / 'requirements.lock', *, online=True, runner=subprocess.run, version=metadata.version, query=query_osv,
          closure=dependency_closure):
    check = runner([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True, timeout=120)
    if check.returncode:
        raise RuntimeError('pip check failed: ' + (check.stdout + check.stderr).strip())
    pins = read_lock(lock)
    for name, expected in pins.items():
        if version(name) != expected:
            raise RuntimeError(f'Installed version differs from lock: {name}')
    # These two upstream Windows advisories remain an offline safety floor.
    # GHSA-7p48-42j8-8846 fixed in 1.54.0; GHSA-rxff-vr5r-8cj5 fixed in 1.37.0.
    if 'streamlit' in pins and Version(pins['streamlit']) < Version('1.54.0'):
        raise RuntimeError('Known insecure Streamlit version; require >=1.54.0.')
    if 'pillow' in pins and Version(pins['pillow']) < Version('13.0.0'):
        raise RuntimeError('Known insecure Pillow version; require >=13.0.0.')
    if pins != closure(APP_ROOTS):
        raise RuntimeError('Lock does not match the complete application dependency closure.')
    findings = query(pins) if online else []
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'pip_check': 'passed',
              'package_count': len(pins), 'source': OSV_ENDPOINT if online else 'offline minimum-version floor only',
              'online_complete': online, 'findings': findings}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, default=ROOT / 'requirements.lock')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--offline', action='store_true', help='Limited offline floor check; does not establish a CVE-free dependency set.')
    args = parser.parse_args()
    try:
        report = audit(args.lock, online=not args.offline)
    except Exception as exc:
        print(f'Dependency audit failed: {exc}', file=sys.stderr)
        return 2
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 1 if report['findings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
