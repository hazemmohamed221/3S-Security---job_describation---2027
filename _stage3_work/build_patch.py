from pathlib import Path
import difflib
root=Path.cwd()
baseline=root/'_stage3_work/baseline'
check=root/'_stage3_work/patch_check_clean'
originals=['database.py','governance.py','docx_parser.py','app.py','backups.py','scripts/restore_database.py','.gitignore','.dockerignore','.streamlit/config.toml','requirements.txt','requirements-dev.txt','Dockerfile','tests/conftest.py']
added=['statuses.py','upload_security.py','scripts/backup.py','scripts/lock_dependencies.py','scripts/audit_dependencies.py','requirements.lock','requirements-dev.lock','tests/test_stage3_database.py','tests/test_stage3_uploads.py','tests/test_stage3_backups.py','tests/test_stage3_operations.py','docs/STAGE3_PRODUCTION.md']
parts=[]
changed=[]
for name in originals+added:
    new=(root/name).read_text(encoding='utf-8')
    old=(baseline/name).read_text(encoding='utf-8') if name in originals else ''
    if old==new:
        continue
    changed.append(name)
    parts.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+name if name in originals else '/dev/null',tofile='b/'+name))
    if name in originals:
        target=check/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(old,encoding='utf-8',newline='\n')
target=root/'docs/changes/stage3-production.patch'
target.write_text(''.join(parts),encoding='utf-8',newline='\n')
(root/'_stage3_work/changed-files.txt').write_text('\n'.join(changed),encoding='utf-8')
print(f'Unified patch: {len(changed)} text files, {target.stat().st_size} bytes.')
