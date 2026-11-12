"""Fetch a pinned portable Notepad++ matching YP_ARCH for isolated tests."""
import hashlib
import subprocess
import urllib.request
import zipfile
from support import ARCH, RUNTIME

ASSETS = {
    'x86': ('npp.8.9.6.portable.zip', 'f1f40ba76eb357ce5ab86f5ba451197f35467c711a133399b69af2493c7719b0'),
    'x64': ('npp.8.9.6.portable.x64.zip', '5528d2de7e44fcc676bb1a4d59d212c74b23f365b5db54f474058d6a68db4041'),
    'arm64': ('npp.8.9.6.portable.arm64.zip', '4fb150a5a1db9e9e13770362ec0e77cc508f60ca863b5e66d0a58693bc51ba91'),
}


def main():
    name, expected = ASSETS[ARCH]
    RUNTIME.mkdir(parents=True, exist_ok=True)
    archive = RUNTIME/name
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        command = ['curl.exe', '-fSL', '--retry', '3', '--max-time', '180']
        proxy = urllib.request.getproxies().get('https')
        if proxy:
            command += ['--proxy', proxy]
        subprocess.run(command + ['https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.9.6/'+name,
                                 '-o', str(archive)], check=True)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError('Notepad++ archive checksum mismatch.')
    target = RUNTIME/'npp-source'
    with zipfile.ZipFile(archive) as z:
        # Only the files used by the isolated harness; no installed plugins/configuration.
        for file in ['notepad++.exe', 'langs.model.xml', 'stylers.model.xml',
                     'localization/english.xml', 'localization/chineseSimplified.xml',
                     'localization/taiwaneseMandarin.xml', 'localization/hongKongCantonese.xml',
                     'localization/french.xml']:
            z.extract(file, target)
    print(target)


if __name__ == '__main__':
    main()
