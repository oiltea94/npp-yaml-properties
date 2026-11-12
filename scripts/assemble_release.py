"""Collect verified CI packages into the ten public release attachments."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_config import TARGETS, pe_machine


def metadata(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def source_contents(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError(f'Duplicate source entries: {path}')
        return {name: metadata(archive.read(name)) for name in names}


def release_notes(changelog, version):
    for section in re.split(r'^## ', changelog, flags=re.MULTILINE)[1:]:
        heading, _, body = section.partition('\n')
        if heading.split()[0] == version and body.strip():
            return body.strip() + '\n'
    raise ValueError(f'Missing or empty changelog section for {version}')


def assemble(candidates, output, version):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Expected a stable major.minor.patch version')
    if output.exists():
        raise FileExistsError(output)
    source_name = f'YamlProperties-{version}-source.zip'
    shared_source = candidates/'YamlProperties-x64-release-candidates'/source_name
    shared_contents = source_contents(shared_source)
    shared_metadata = metadata(shared_source.read_bytes())
    copies = [shared_source]
    checksums = {}
    for arch in TARGETS:
        folder = candidates/f'YamlProperties-{arch}-release-candidates'
        manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        hashes = json.loads((folder/'checksums.json').read_text(encoding='utf-8'))
        if manifest['architecture'] != arch or manifest['version'] != version:
            raise ValueError(f'Inconsistent manifest: {arch}')
        manual = folder/f'YamlProperties-{version}-{arch}.zip'
        admin = folder/f'YamlProperties-{version}-{arch}-plugin-admin.zip'
        source = folder/source_name
        for path in [manual, admin, source]:
            if metadata(path.read_bytes()) != hashes[path.name]:
                raise ValueError(f'Archive checksum mismatch: {path}')
        if source_contents(source) != shared_contents:
            raise ValueError(f'Different source content: {arch}')
        for path, dll_name in [(manual, 'YamlProperties/YamlProperties.dll'), (admin, 'YamlProperties.dll')]:
            with zipfile.ZipFile(path) as archive:
                if archive.testzip() is not None:
                    raise ValueError(f'Corrupt ZIP: {path}')
                dll = archive.read(dll_name)
                if metadata(dll) != hashes['YamlProperties.dll'] or metadata(dll)['sha256'] != manifest['sha256']:
                    raise ValueError(f'DLL checksum mismatch: {path}')
                if pe_machine(dll) != TARGETS[arch][1]:
                    raise ValueError(f'DLL architecture mismatch: {path}')
                if path == manual and archive.read('source/'+source_name) != source.read_bytes():
                    raise ValueError(f'Embedded source mismatch: {path}')
        copies.extend([manual, admin])
        checksums[arch] = {path.name: hashes[path.name] for path in [manual, admin]}
        checksums[arch][source_name] = shared_metadata
        checksums[arch]['YamlProperties.dll'] = hashes['YamlProperties.dll']
    # Validate all architectures before creating any output; never repack binaries.
    output.mkdir(parents=True)
    for source in copies:
        shutil.copyfile(source, output/source.name)
    for arch, hashes in checksums.items():
        (output/f'checksums-{arch}.json').write_text(json.dumps(hashes, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version-file', type=Path, default=Path('VERSION'))
    parser.add_argument('--changelog', type=Path, default=Path('CHANGELOG.md'))
    parser.add_argument('--notes', type=Path, required=True)
    args = parser.parse_args()
    version = args.version_file.read_text(encoding='utf-8').strip()
    notes = release_notes(args.changelog.read_text(encoding='utf-8'), version)
    assemble(args.candidates, args.output, version)
    args.notes.write_text(notes, encoding='utf-8')
    print(f'Verified 10 release attachments for v{version}: {args.output}')


if __name__ == '__main__':
    main()
