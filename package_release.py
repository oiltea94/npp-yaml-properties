from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile
from build_config import TARGETS, architecture, target_dir, pe_machine

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--arch', choices=TARGETS, default=architecture())
    args = parser.parse_args()
    DIST = target_dir('dist', args.arch)
    manifest = json.loads((DIST/'manifest.json').read_text())
    dll = DIST/manifest['file']
    if manifest['architecture'] != args.arch or pe_machine(dll.read_bytes()) != TARGETS[args.arch][1]:
        raise RuntimeError('DLL architecture differs from the requested package.')
    if hashlib.sha256(dll.read_bytes()).hexdigest() != manifest['sha256']:
        raise RuntimeError('DLL differs from the verified build manifest.')
    version = manifest['version']
    source = DIST/f'YamlProperties-{version}-source.zip'
    standalone = ['.gitignore', '.gitattributes', 'VERSION', 'CHANGELOG.md', 'LICENSE', 'README.md', 'README.zh-CN.md', 'SPEC.md', 'THIRD_PARTY.md',
                  'bootstrap.py', 'build.ps1', 'build.py', 'build_config.py', 'install.ps1', 'package_release.py']
    files = [ROOT/name for name in standalone]
    for name in ['src', 'tests', 'vendor', 'docs', 'scripts', '.github']:
        files.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in sorted(files):
            archive.write(file, Path('YamlProperties')/file.relative_to(ROOT))
    notice = DIST/'licenses'
    notice.mkdir(exist_ok=True)
    for original, name in [
        (ROOT/'vendor/yaml-cpp-0.8.0/LICENSE', 'yaml-cpp-MIT.txt'),
        (ROOT/'vendor/npp/Scintilla.License.txt', 'Scintilla.txt'),
        (ROOT/'.tools/llvm-mingw-20261104-ucrt-x86_64/LICENSE.TXT', 'LLVM-runtime.txt')
    ]:
        shutil.copy2(original, notice/name)
    binary = DIST/f'YamlProperties-{version}-{args.arch}.zip'
    with zipfile.ZipFile(binary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(dll, manifest['file'])
        archive.write(DIST/'manifest.json', 'manifest.json')
        for name in ['README.md', 'README.zh-CN.md', 'CHANGELOG.md', 'install.ps1', 'LICENSE', 'THIRD_PARTY.md']:
            archive.write(ROOT/name, name)
        for file in sorted((ROOT/'docs').glob('*.md')):
            archive.write(file, file.relative_to(ROOT))
        for file in notice.iterdir():
            archive.write(file, Path('licenses')/file.name)
        archive.write(source, Path('source')/source.name)
    # Plugins Admin creates plugins/YamlProperties itself, so the DLL must be at ZIP root.
    admin = DIST/f'YamlProperties-{version}-{args.arch}-plugin-admin.zip'
    with zipfile.ZipFile(admin, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(dll, 'YamlProperties.dll')
        for name in ['LICENSE', 'THIRD_PARTY.md']:
            archive.write(ROOT/name, name)
        for file in notice.iterdir():
            archive.write(file, Path('licenses')/file.name)
    for artifact in [source, binary, admin]:
        with zipfile.ZipFile(artifact) as archive:
            if archive.testzip() is not None:
                raise RuntimeError('ZIP integrity check failed: '+str(artifact))
    with zipfile.ZipFile(binary) as archive:
        if hashlib.sha256(archive.read(manifest['file'])).hexdigest() != manifest['sha256']:
            raise RuntimeError('Packaged DLL checksum differs.')
    with zipfile.ZipFile(admin) as archive:
        if hashlib.sha256(archive.read('YamlProperties.dll')).hexdigest() != manifest['sha256']:
            raise RuntimeError('Plugins Admin DLL checksum differs.')
    hashes = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in [binary, source, admin, dll]}
    (DIST/'checksums.json').write_text(json.dumps(hashes, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(hashes, indent=2))

if __name__ == '__main__':
    main()
