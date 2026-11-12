"""Build a Windows target and run semantic tests; standard-library only."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
from build_config import TARGETS, architecture, target_dir, pe_machine

ROOT = Path(__file__).resolve().parent
def run(args):
    result = subprocess.run([str(x) for x in args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        print(result.stdout + result.stderr, flush=True)
        raise RuntimeError('Command failed: ' + ' '.join(map(str, args)))
    return result.stdout + result.stderr

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', help='Override the target C++ compiler')
    parser.add_argument('--arch', choices=TARGETS, default=architecture())
    parser.add_argument('--compile-only', action='store_true', help='Cross-compile without executing target tests')
    parser.add_argument('--core-only', action='store_true')
    args = parser.parse_args()
    arch = args.arch
    triple = TARGETS[arch][0] + '-w64-mingw32'
    cxx = Path(args.compiler) if args.compiler else ROOT / '.tools/llvm-mingw-20261104-ucrt-x86_64/bin' / (triple + '-clang++.exe')
    build = target_dir('build', arch)
    build.mkdir(parents=True, exist_ok=True)
    version = (ROOT / 'VERSION').read_text(encoding='ascii').strip()
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise ValueError('VERSION must contain major.minor.patch numeric components.')
    numbers = [int(part) for part in version.split('.')]
    if any(part > 65535 for part in numbers):
        raise ValueError('Windows version components must be at most 65535.')
    header = ('#pragma once\n'
              f'#define YP_VERSION_STRING "{version}"\n'
              f'#define YP_VERSION_W L"{version}"\n'
              f'#define YP_ARCH_W L"{arch}"\n'
              '#define YP_VERSION_NUMBERS ' + ','.join(map(str, [*numbers, 0])) + '\n')
    (build / 'version.h').write_text(header, encoding='ascii')
    evidence = target_dir('evidence', arch)
    evidence.mkdir(parents=True, exist_ok=True)
    yaml = ROOT / 'vendor/yaml-cpp-0.8.0'
    includes = ['-I', yaml / 'include', '-I', ROOT / 'src', '-I', ROOT / 'vendor/npp', '-I', build]
    common = ['-std=c++17', '-O2', '-DYAML_CPP_STATIC_DEFINE', '-DUNICODE', '-D_UNICODE', '-DNOMINMAX', *includes]
    def compile_yaml(source):
        obj = build / ('yaml_' + source.stem + '.o')
        if not obj.exists() or obj.stat().st_mtime < source.stat().st_mtime:
            run([cxx, *common, '-I', yaml / 'src', '-c', source, '-o', obj])
        return obj
    sources = sorted((yaml / 'src').glob('*.cpp'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        objects = list(pool.map(compile_yaml, sources))
    archive = build / 'libyaml-cpp.a'
    run([cxx.parent / 'llvm-ar.exe', 'rcs', archive, *objects])
    print('yaml-cpp: compiled', flush=True)
    core = build / 'converter.o'
    run([cxx, *common, '-Wall', '-Wextra', '-Werror', '-c', ROOT / 'src/converter.cpp', '-o', core])
    test = build / 'converter_test.exe'
    run([cxx, *common, ROOT / 'tests/converter_test.cpp', core, archive, '-static', '-o', test])
    if pe_machine(test.read_bytes()) != TARGETS[arch][1]:
        raise ValueError('Compiler produced the wrong target architecture.')
    if args.compile_only:
        (evidence / 'core-tests.txt').write_text('NOT RUN: cross-compiled target; run on a compatible Windows host.\n', encoding='utf-8')
        print('Target tests compiled but not executed (--compile-only).', flush=True)
    else:
        result = subprocess.run([test], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        (evidence / 'core-tests.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        print(result.stdout, flush=True)
        if result.returncode:
            return result.returncode
    if args.core_only:
        return 0
    dist = target_dir('dist', arch) / 'YamlProperties'
    dist.mkdir(parents=True, exist_ok=True)
    dll = dist / 'YamlProperties.dll'
    resource = build / 'plugin-resource.o'
    run([cxx.parent / (triple + '-windres.exe'), '-I', build,
         '-i', ROOT / 'src/plugin.rc', '-o', resource, '-O', 'coff'])
    run([cxx, *common, '-Wall', '-Wextra', '-Werror', '-shared', ROOT / 'src/plugin.cpp', resource, core, archive,
         '-static', '-luser32', '-lcomctl32', '-lshell32', '-Wl,--no-insert-timestamp', '-o', dll])
    about_test = build / 'about_callback_test.exe'
    run([cxx, *common, '-Wall', '-Wextra', '-Werror', ROOT / 'tests/about_callback_test.cpp', core, archive,
         '-static', '-luser32', '-lcomctl32', '-lshell32', '-o', about_test])
    about_result = 'NOT RUN: cross-compiled target.\n' if args.compile_only else run([about_test])
    (evidence / 'about-callback-tests.txt').write_text(about_result, encoding='utf-8')
    print(about_result, flush=True)
    run([cxx, *common, ROOT / 'src/cli.cpp', core, archive, '-static', '-o', build / 'ypconvert.exe'])
    info = run([cxx.parent / 'llvm-readobj.exe', '--coff-exports', '--coff-imports', dll])
    (evidence / 'dll-inspection.txt').write_text(info, encoding='utf-8')
    if pe_machine(dll.read_bytes()) != TARGETS[arch][1]:
        raise ValueError('DLL architecture differs from requested target.')
    manifest = {'version': version, 'architecture': arch, 'file': 'YamlProperties/YamlProperties.dll',
                'core_tests': 'not-run-cross-compile' if args.compile_only else 'passed',
                'sha256': hashlib.sha256(dll.read_bytes()).hexdigest(), 'bytes': dll.stat().st_size}
    (target_dir('dist', arch) / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2), flush=True)
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(error, file=sys.stderr)
        sys.exit(1)
