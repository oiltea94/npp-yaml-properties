"""Check release assembly without a compiler, network or publishing credentials."""
from pathlib import Path
import hashlib
import io
import json
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.assemble_release import assemble, release_notes


def metadata(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def zipped(files, year=2026):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, data in files.items():
            archive.writestr(zipfile.ZipInfo(name, (year, 1, 1, 0, 0, 0)), data)
    return buffer.getvalue()


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root/'release'
        self.source = 'YamlProperties-1.2.3-source.zip'
        for arch, machine in [('x86', 0x14c), ('x64', 0x8664), ('arm64', 0xaa64)]:
            folder = self.folder(arch)
            folder.mkdir()
            dll = bytearray(128)
            dll[:2] = b'MZ'
            struct.pack_into('<I', dll, 0x3c, 64)
            dll[64:68] = b'PE\0\0'
            struct.pack_into('<H', dll, 68, machine)
            dll = bytes(dll)
            source = zipped({'YamlProperties/VERSION': b'1.2.3'}, 2025 if arch == 'x86' else 2026)
            artifacts = {
                self.source: source,
                f'YamlProperties-1.2.3-{arch}.zip': zipped({
                    'YamlProperties/YamlProperties.dll': dll,
                    'source/'+self.source: source}),
                f'YamlProperties-1.2.3-{arch}-plugin-admin.zip': zipped({'YamlProperties.dll': dll})}
            for name, data in artifacts.items():
                (folder/name).write_bytes(data)
            hashes = {name: metadata(data) for name, data in artifacts.items()}
            hashes['YamlProperties.dll'] = metadata(dll)
            (folder/'checksums.json').write_text(json.dumps(hashes))
            (folder/'manifest.json').write_text(json.dumps({
                'version': '1.2.3', 'architecture': arch,
                'file': 'YamlProperties/YamlProperties.dll', 'sha256': metadata(dll)['sha256']}))

    def folder(self, arch):
        return self.root/f'YamlProperties-{arch}-release-candidates'

    def test_ten_assets_preserve_binaries_and_share_verified_source(self):
        assemble(self.root, self.output, '1.2.3')
        self.assertEqual(len(list(self.output.iterdir())), 10)
        source = (self.folder('x64')/self.source).read_bytes()
        self.assertEqual((self.output/self.source).read_bytes(), source)
        for arch in ['x86', 'x64', 'arm64']:
            checksums = json.loads((self.output/f'checksums-{arch}.json').read_text())
            self.assertEqual(checksums[self.source], metadata(source))
            for suffix in ['.zip', '-plugin-admin.zip']:
                name = f'YamlProperties-1.2.3-{arch}{suffix}'
                self.assertEqual((self.output/name).read_bytes(), (self.folder(arch)/name).read_bytes())

    def test_missing_architecture_stops_before_writing(self):
        (self.folder('arm64')/'manifest.json').unlink()
        with self.assertRaises(FileNotFoundError):
            assemble(self.root, self.output, '1.2.3')
        self.assertFalse(self.output.exists())

    def test_mixed_version_or_architecture_is_rejected(self):
        path = self.folder('arm64')/'manifest.json'
        original = path.read_text()
        for key, value in [('version', '1.2.2'), ('architecture', 'x64')]:
            data = json.loads(original)
            data[key] = value
            path.write_text(json.dumps(data))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'manifest'):
                assemble(self.root, self.output, '1.2.3')

    def test_corrupt_archive_is_rejected(self):
        archive = self.folder('x86')/'YamlProperties-1.2.3-x86.zip'
        archive.write_bytes(archive.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            assemble(self.root, self.output, '1.2.3')

    def test_different_source_content_is_rejected_even_with_valid_checksum(self):
        folder = self.folder('arm64')
        changed = zipped({'YamlProperties/VERSION': b'1.2.2'})
        (folder/self.source).write_bytes(changed)
        hashes = json.loads((folder/'checksums.json').read_text())
        hashes[self.source] = metadata(changed)
        (folder/'checksums.json').write_text(json.dumps(hashes))
        with self.assertRaisesRegex(ValueError, 'source'):
            assemble(self.root, self.output, '1.2.3')

    def test_existing_output_is_not_overwritten(self):
        self.output.mkdir()
        marker = self.output/'keep.txt'
        marker.write_text('keep')
        with self.assertRaises(FileExistsError):
            assemble(self.root, self.output, '1.2.3')
        self.assertEqual(marker.read_text(), 'keep')

    def test_notes_include_only_requested_version(self):
        text = '# Changelog\n\n## Unreleased\n\n- Later\n\n## 1.2.3 — 2026-11-12\n\n- Feature\n\n## 1.2.2\n\n- Old\n'
        notes = release_notes(text, '1.2.3')
        self.assertIn('- Feature', notes)
        self.assertNotIn('- Later', notes)
        self.assertNotIn('- Old', notes)

    def test_missing_or_empty_changelog_section_is_rejected(self):
        for text in ['## Unreleased\n', '## 1.2.3\n\n## 1.2.2\n- Old']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                release_notes(text, '1.2.3')


if __name__ == '__main__':
    unittest.main()
