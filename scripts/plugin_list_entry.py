"""Generate one official x64 plugin-list entry from a verified local release ZIP."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = r'(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){0,3}'


def github_repository(value):
    url = urllib.parse.urlsplit(value.strip().rstrip('/'))
    if url.scheme != 'https' or url.netloc != 'github.com' or url.query or url.fragment:
        raise ValueError('Use an HTTPS GitHub repository URL without query parameters.')
    parts = url.path.strip('/').split('/')
    if len(parts) != 2:
        raise ValueError('Repository URL must identify exactly an owner and a repository.')
    if parts[1].endswith('.git'):
        parts[1] = parts[1][:-4]
    if any(p in {'.', '..'} or not re.fullmatch(r'[A-Za-z0-9_.-]+', p) for p in parts):
        raise ValueError('Invalid GitHub owner or repository name.')
    return 'https://github.com/' + '/'.join(parts)


def build_entry(repository, author, minimum_npp, manifest, archive):
    homepage = github_repository(repository)
    if not author.strip():
        raise ValueError('Supply the author name to display in Plugins Admin.')
    version = manifest['version']
    for value in [version, minimum_npp]:
        if not re.fullmatch(VERSION_PATTERN, value) or any(int(p) > 65535 for p in value.split('.')):
            raise ValueError('Versions must have one to four numeric components, each at most 65535.')
    if manifest['architecture'] != 'x64':
        raise ValueError('This generator only handles the tested x64 release.')
    data = archive.read_bytes()
    with zipfile.ZipFile(archive) as z:
        if z.namelist().count('YamlProperties.dll') != 1:
            raise ValueError('Plugins Admin ZIP must contain one YamlProperties.dll at its root.')
        if hashlib.sha256(z.read('YamlProperties.dll')).hexdigest() != manifest['sha256']:
            raise ValueError('ZIP DLL differs from the build manifest.')
    return {
        'folder-name': 'YamlProperties',
        'display-name': 'YamlProperties',
        'version': version,
        'npp-compatible-versions': f'[{minimum_npp},]',
        'id': hashlib.sha256(data).hexdigest(),
        'repository': f'{homepage}/releases/download/v{version}/{archive.name}',
        'description': 'Convert YAML and Java Properties in either direction. Supports selections, '
                       'automatic format detection, literal keys and configurable new-tab or in-place output.',
        'author': author.strip(),
        'homepage': homepage,
    }


def verify_download(entry):
    request = urllib.request.Request(entry['repository'], headers={'User-Agent': 'YamlProperties-release-check'})
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(request, timeout=60) as response:
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > 32 * 1024 * 1024:
                raise ValueError('Release download unexpectedly exceeds 32 MiB.')
            digest.update(chunk)
    if digest.hexdigest() != entry['id']:
        raise ValueError('Public download differs from the local Plugins Admin ZIP.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True, help='Public GitHub repository HTTPS URL')
    parser.add_argument('--author', required=True, help='Author display name')
    parser.add_argument('--min-npp', required=True, help='Lowest Notepad++ version verified for this release')
    parser.add_argument('--verify-download', action='store_true', help='Verify the published ZIP before writing JSON')
    args = parser.parse_args()
    manifest = json.loads((ROOT/'dist/manifest.json').read_text(encoding='utf-8'))
    archive = ROOT/'dist'/f"YamlProperties-{manifest['version']}-x64-plugin-admin.zip"
    entry = build_entry(args.repository, args.author, args.min_npp, manifest, archive)
    if args.verify_download:
        verify_download(entry)
    target = ROOT/'dist/nppPluginList-entry-x64.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(entry, ensure_ascii=False, indent=4)+'\n', encoding='utf-8')
    temporary.replace(target)
    print('Generated:', target)
    print('Public ZIP verified.' if args.verify_download else
          'Public download not checked. After publishing, rerun with --verify-download before submitting the entry.')


if __name__ == '__main__':
    main()
