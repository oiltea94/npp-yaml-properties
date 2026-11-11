from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.runtime/installer'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    WORK.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='run-', dir=WORK))
    package = work / 'package'
    npp = work / 'Notepad++'
    package.mkdir(parents=True, exist_ok=True)
    npp.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/'install.ps1', package/'install.ps1')
    shutil.copy2(r'C:\Program Files\Notepad++\notepad++.exe', npp/'notepad++.exe')
    (package/'YamlProperties').mkdir(exist_ok=True)
    built = ROOT/'dist/YamlProperties/YamlProperties.dll'
    shutil.copy2(built, package/'YamlProperties/YamlProperties.dll')
    target = npp/'plugins/YamlProperties/YamlProperties.dll'
    commands = []
    def run(restore=False, expected=0):
        args = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(package/'install.ps1'), '-NotepadDir', str(npp)]
        if restore:
            args.append('-Restore')
        r = subprocess.run(args, capture_output=True)
        commands.append({'restore': restore, 'exit': r.returncode, 'stdout': r.stdout.decode('utf-8', errors='replace'), 'stderr': r.stderr.decode('utf-8', errors='replace')})
        assert (r.returncode == 0) == (expected == 0), commands[-1]
    run()
    assert digest(target) == digest(built)
    run(restore=True)
    assert not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    previous = b'original plugin bytes for restoration test\x00\x01'
    target.write_bytes(previous)
    run()
    assert digest(target) == digest(built)
    state = json.loads((package/'.install-state.json').read_text(encoding='utf-8-sig'))
    assert Path(state['Backup']).read_bytes() == previous
    target.write_bytes(b'changed after installation')
    run(restore=True, expected=1)
    assert target.read_bytes() == b'changed after installation'
    shutil.copy2(built, target)
    run(restore=True)
    assert target.read_bytes() == previous
    (ROOT/'evidence/installer-tests.json').write_text(json.dumps({'result': 'PASS', 'checks': ['install checksum', 'fresh-install removal', 'upgrade backup', 'modified-file guard', 'byte-exact restoration'], 'commands': commands}, indent=2)+'\n', encoding='utf-8')
    print('5/5 installer and restoration checks passed')

if __name__ == '__main__':
    main()
