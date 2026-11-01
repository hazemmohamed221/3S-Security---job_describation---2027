from pathlib import Path
import difflib
import shutil

root = Path.cwd()
baseline = root / '_stage1_work' / 'baseline'
originals = ['app.py', 'auth.py', 'database.py', 'requirements.txt', 'README.md',
             '.streamlit/config.toml', '.dockerignore']
added = ['.gitignore', 'backups.py', 'password_security.py', 'pytest.ini', 'requirements-dev.txt',
         'docs/STAGE1_SECURITY.md']
added += [str(p.relative_to(root)).replace('\\', '/') for folder in ('scripts', 'tests')
          for p in sorted((root / folder).glob('*')) if p.suffix in ('.py', '.sql')]
parts = []
changed = []
check_dir = root / '_stage1_work' / 'patch_check_final'
check_dir.mkdir(parents=True, exist_ok=True)
for name in originals + added:
    old_path = baseline / name
    new = (root / name).read_text(encoding='utf-8')
    old = old_path.read_text(encoding='utf-8') if name in originals else ''
    if old == new:
        continue
    changed.append(name)
    parts.extend(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                 fromfile=f'a/{name}' if name in originals else '/dev/null', tofile=f'b/{name}'))
    if name in originals:
        copy = check_dir / name
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old_path, copy)
target = root / 'docs' / 'changes' / 'stage1-security.patch'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(''.join(parts), encoding='utf-8', newline='\n')
(root / '_stage1_work' / 'changed_files.txt').write_text('\n'.join(changed),encoding='utf-8')
print(f'Unified patch: {len(changed)} files, {target.stat().st_size} bytes.')
