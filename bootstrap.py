"""Download the pinned build-only toolchain, verify it, and extract locally."""
from pathlib import Path
import hashlib
import os
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
NAME = 'llvm-mingw-20261104-ucrt-x86_64'
URL = 'https://github.com/mstorsjo/llvm-mingw/releases/download/20261104/' + NAME + '.zip'
SHA256 = '552191b5754c49a5a20723276a6fc56541ea1922c4c50b7b669022333fc1b40f'

def main():
    tools = ROOT / '.tools'
    tools.mkdir(exist_ok=True)
    archive = tools / 'toolchain.zip'
    compiler = tools / NAME / 'bin/x86_64-w64-mingw32-clang++.exe'
    if compiler.exists():
        print('Portable compiler already present:', compiler)
        return
    if not archive.exists() or hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest() != SHA256:
        temporary = archive.with_suffix('.download')
        command = ['curl.exe', '-fSL', '--retry', '3', '--max-time', '900']
        proxy = urllib.request.getproxies().get('https')
        if proxy:
            command += ['--proxy', proxy]
        subprocess.run(command + [URL, '-o', str(temporary)], check=True)
        actual = hashlib.file_digest(temporary.open('rb'), 'sha256').hexdigest()
        if actual != SHA256:
            raise RuntimeError('Toolchain checksum mismatch; extraction was not performed.')
        os.replace(temporary, archive)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            destination = (tools / item.filename).resolve()
            if not destination.is_relative_to(tools.resolve()):
                raise RuntimeError('Archive path is outside .tools')
        z.extractall(tools)
    print('Verified and extracted:', compiler)

if __name__ == '__main__':
    main()
