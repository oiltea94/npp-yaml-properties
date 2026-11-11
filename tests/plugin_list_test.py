from pathlib import Path
import hashlib
import io
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from plugin_list_entry import build_entry, github_repository, verify_download


class PluginListTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.archive = Path(temporary.name)/'YamlProperties-0.3.1-x64-plugin-admin.zip'
        self.dll = b'isolated package test content'
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('YamlProperties.dll', self.dll)
        self.manifest = {'version': '0.3.1', 'architecture': 'x64',
                         'sha256': hashlib.sha256(self.dll).hexdigest()}

    def entry(self, **changes):
        args = dict(repository='https://github.com/example/YamlProperties', author='Example Author',
                    minimum_npp='8.9.6.4', manifest=self.manifest, archive=self.archive)
        args.update(changes)
        return build_entry(**args)

    def test_entry_uses_zip_hash_asset_url_and_explicit_compatibility(self):
        entry = self.entry()
        self.assertEqual(entry['id'], hashlib.sha256(self.archive.read_bytes()).hexdigest())
        self.assertNotEqual(entry['id'], self.manifest['sha256'])
        self.assertEqual(entry['repository'], 'https://github.com/example/YamlProperties/releases/download/v0.3.1/YamlProperties-0.3.1-x64-plugin-admin.zip')
        self.assertEqual(entry['npp-compatible-versions'], '[8.9.6.4,]')
        self.assertEqual(entry['folder-name'], 'YamlProperties')
        self.assertEqual(entry['version'], '0.3.1')
        self.assertEqual(entry['author'], 'Example Author')

    def test_clone_url_normalizes_to_homepage(self):
        self.assertEqual(github_repository('https://github.com/example/YamlProperties.git/'),
                         'https://github.com/example/YamlProperties')

    def test_all_supported_architectures_generate_distinct_asset_urls(self):
        for arch in ['x86', 'x64', 'arm64']:
            with self.subTest(architecture=arch):
                archive = self.archive.with_name(f'YamlProperties-0.3.1-{arch}-plugin-admin.zip')
                archive.write_bytes(self.archive.read_bytes())
                manifest = dict(self.manifest, architecture=arch)
                self.assertTrue(self.entry(manifest=manifest, archive=archive)['repository'].endswith(archive.name))

    def test_mismatched_archive_architecture_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'filename'):
            self.entry(manifest=dict(self.manifest, architecture='arm64'))

    def test_invalid_repository_is_rejected(self):
        for value in ['http://github.com/example/repo', 'https://example.com/a/b',
                      'https://github.com/a/b/tree/main', 'https://github.com/a/b?token=x',
                      'https://github.com/a/b#fragment', 'https://user@github.com/a/b',
                      'https://github.com/a/..']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.entry(repository=value)

    def test_author_and_verified_minimum_are_required(self):
        for changes in [{'author': ' '}, {'minimum_npp': 'latest'}, {'minimum_npp': '8.09'},
                        {'minimum_npp': '8.9.65536'}, {'minimum_npp': ''}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.entry(**changes)

    def test_nested_dll_package_is_rejected(self):
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('YamlProperties/YamlProperties.dll', self.dll)
        with self.assertRaisesRegex(ValueError, 'root'):
            self.entry()

    def test_changed_binary_is_rejected(self):
        self.manifest['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.entry()

    def test_download_hash_matches(self):
        with patch('plugin_list_entry.urllib.request.urlopen', return_value=io.BytesIO(self.archive.read_bytes())):
            verify_download(self.entry())

    def test_changed_download_is_rejected(self):
        with patch('plugin_list_entry.urllib.request.urlopen', return_value=io.BytesIO(b'wrong download')):
            with self.assertRaisesRegex(ValueError, 'differs'):
                verify_download(self.entry())


if __name__ == '__main__':
    unittest.main(verbosity=2)
