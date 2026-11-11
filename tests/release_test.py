"""Validate installable release artifacts on Windows, without publishing anything."""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import struct
import unittest
import zipfile
from support import ARCH, TARGETS, DIST, pe_machine

ROOT = Path(__file__).resolve().parents[1]


def binary_version(path):
    api = C.WinDLL('version', use_last_error=True)
    api.GetFileVersionInfoSizeW.argtypes = [W.LPCWSTR, C.POINTER(W.DWORD)]
    api.GetFileVersionInfoSizeW.restype = W.DWORD
    api.GetFileVersionInfoW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, C.c_void_p]
    api.GetFileVersionInfoW.restype = W.BOOL
    api.VerQueryValueW.argtypes = [C.c_void_p, W.LPCWSTR, C.POINTER(C.c_void_p), C.POINTER(W.UINT)]
    api.VerQueryValueW.restype = W.BOOL
    size = api.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        raise ValueError('DLL has no Windows version resource')
    data = C.create_string_buffer(size)
    if not api.GetFileVersionInfoW(str(path), 0, size, data):
        raise C.WinError(C.get_last_error())
    pointer, length = C.c_void_p(), W.UINT()
    if not api.VerQueryValueW(data, '\\', C.byref(pointer), C.byref(length)):
        raise C.WinError(C.get_last_error())
    fixed = C.cast(pointer, C.POINTER(W.DWORD))
    assert fixed[0] == 0xFEEF04BD
    return '.'.join(str(v) for v in (fixed[2] >> 16, fixed[2] & 65535, fixed[3] >> 16, fixed[3] & 65535))


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((DIST/'manifest.json').read_text())
        cls.version = cls.manifest['version']
        cls.dll = DIST/cls.manifest['file']

    def test_windows_version_matches_release(self):
        expected = self.version + '.0' * (3 - self.version.count('.'))
        self.assertEqual(binary_version(self.dll), expected)

    def test_plugin_admin_zip_has_matching_dll_at_root(self):
        path = DIST/f'YamlProperties-{self.version}-{ARCH}-plugin-admin.zip'
        with zipfile.ZipFile(path) as z:
            self.assertIn('YamlProperties.dll', z.namelist())
            self.assertNotIn('YamlProperties/YamlProperties.dll', z.namelist())
            self.assertEqual(z.read('YamlProperties.dll'), self.dll.read_bytes())

    def test_binary_matches_target_architecture_and_manifest(self):
        data = self.dll.read_bytes()
        offset = struct.unpack_from('<I', data, 0x3c)[0]
        self.assertEqual(data[offset:offset+4], b'PE\0\0')
        self.assertEqual(pe_machine(data), TARGETS[ARCH][1])
        self.assertEqual(self.manifest['architecture'], ARCH)
        self.assertEqual(hashlib.sha256(data).hexdigest(), self.manifest['sha256'])

    def test_source_archive_contains_build_inputs_without_local_artifacts(self):
        with zipfile.ZipFile(DIST/f'YamlProperties-{self.version}-source.zip') as z:
            names = z.namelist()
            for name in ['VERSION', 'src/plugin.rc', 'build.py', 'build_config.py', 'LICENSE', 'docs/RELEASING.md']:
                self.assertTrue('YamlProperties/'+name in names, f'Missing required source file: {name}')
            for name in names:
                self.assertFalse(set(Path(name).parts) & {'.git', '.tools', '.runtime', '.backups', 'evidence', '__pycache__'})

    def test_manual_package_contains_matching_dll_manifest_and_installer(self):
        with zipfile.ZipFile(DIST/f'YamlProperties-{self.version}-{ARCH}.zip') as z:
            self.assertEqual(z.read('YamlProperties/YamlProperties.dll'), self.dll.read_bytes())
            self.assertEqual(json.loads(z.read('manifest.json'))['architecture'], ARCH)
            self.assertIn('install.ps1', z.namelist())


if __name__ == '__main__':
    unittest.main(verbosity=2)
