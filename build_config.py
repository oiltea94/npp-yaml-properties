"""Shared target architecture and artifact paths (x64 keeps its original paths)."""
from pathlib import Path
import os
import struct

ROOT = Path(__file__).resolve().parent
TARGETS = {'x86': ('i686', 0x014c), 'x64': ('x86_64', 0x8664), 'arm64': ('aarch64', 0xaa64)}


def architecture(value=None):
    value = value or os.environ.get('YP_ARCH', 'x64')
    if value not in TARGETS:
        raise ValueError('Architecture must be x86, x64 or arm64.')
    return value


def target_dir(name, arch=None):
    arch = architecture(arch)
    return ROOT / name if arch == 'x64' else ROOT / name / arch


def pe_machine(data):
    if len(data) < 64 or data[:2] != b'MZ':
        raise ValueError('Not a Windows PE binary.')
    offset = struct.unpack_from('<I', data, 0x3c)[0]
    if offset + 6 > len(data) or data[offset:offset+4] != b'PE\0\0':
        raise ValueError('Invalid Windows PE header.')
    return struct.unpack_from('<H', data, offset+4)[0]
