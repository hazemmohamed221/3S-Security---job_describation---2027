from pathlib import Path
import difflib
root=Path.cwd()
work=root/'_stage3_work/stage4-ui'
baseline=work/'baseline'
check=work/'patch_check'
originals=['app.py','auth.py','utils.py','.streamlit/config.toml','tests/test_app_smoke.py','tests/test_stage2_app.py','tests/test_admin_management.py']
added=['presentation.py','tests/test_stage4_ui.py','docs/STAGE4_UI_UX.md']
parts=[]
for name in originals+added:
    new=(root/name).read_text(encoding='utf-8')
    old=(baseline/name).read_text(encoding='utf-8') if name in originals else ''
    parts.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+name if name in originals else '/dev/null',tofile='b/'+name))
    if name in originals:
        p=check/name
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(old,encoding='utf-8',newline='\n')
patch=root/'docs/changes/stage4-ui-ux.patch'
patch.write_text(''.join(parts),encoding='utf-8',newline='\n')
(work/'changed-files.txt').write_text('\n'.join(originals+added),encoding='utf-8')
print(f'Unified patch: {len(originals+added)} files; {patch.stat().st_size} bytes.')
