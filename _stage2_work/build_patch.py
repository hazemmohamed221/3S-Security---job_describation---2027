from pathlib import Path
import difflib
import shutil

root=Path.cwd()
baseline=root / '_stage2_work/baseline'
check=root / '_stage2_work/patch_check'
originals=['database.py','app.py','docx_parser.py','tests/conftest.py','.gitignore','.dockerignore']
added=['governance.py','docx_format.py','scripts/migrate_integrity.py','scripts/verify_stage2_migration.py','tests/test_stage2_integrity.py','tests/test_stage2_docx.py','tests/test_stage2_app.py','docs/STAGE2_INTEGRITY.md']
parts=[]
for name in originals+added:
    new=(root/name).read_text(encoding='utf-8')
    if name in ('.gitignore','.dockerignore'):
        old=''.join(line for line in new.splitlines(keepends=True) if line.strip() not in ('_stage2_work/','_stage2_work'))
    elif name in originals:
        old=(baseline/Path(name).name).read_text(encoding='utf-8')
    else:
        old=''
    parts.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+name if name in originals else '/dev/null',tofile='b/'+name))
    if name in originals:
        target=check/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(old,encoding='utf-8',newline='\n')
patch=root / 'docs/changes/stage2-integrity.patch'
patch.parent.mkdir(parents=True,exist_ok=True)
patch.write_text(''.join(parts),encoding='utf-8',newline='\n')
(root/'_stage2_work/changed-files.txt').write_text('\n'.join(originals+added),encoding='utf-8')
print(f'Unified patch: {len(originals+added)} files; {patch.stat().st_size} bytes.')
