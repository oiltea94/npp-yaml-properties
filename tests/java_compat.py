"""Compare native conversion with Java's actual Properties.load(Reader)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import base64
import json
import random
import subprocess
from support import BUILD, EVIDENCE, RUNTIME

ROOT = Path(__file__).resolve().parents[1]
WORK = RUNTIME / 'java'
CLI = BUILD / 'ypconvert.exe'

def main():
    WORK.mkdir(parents=True, exist_ok=True)
    subprocess.run(['javac', '-encoding', 'UTF-8', '-d', str(WORK), str(ROOT/'tests/PropertiesOracle.java')], check=True)
    cases = [
        'key=value\n', 'key : value\r\n', 'key\t:\tvalue\r', 'key value\n', 'key\n',
        '=empty-key\n', ':empty-key\n', 'a\\ b=x\n', 'a\\=b:x\n', 'a\\:b=x\n',
        '\\#key=x\n', '\\!key=x\n', 'x=\\u4e2d\\u6587\n', 'x=\\uD83D\\uDE00\n',
        'x=\\u0000\n', 'x=\\t\\r\\n\\f\n', 'x=\\a\\z\\q\n', 'x=中文😀\n',
        'a=x\\\n  y\n', 'a=x\\\r\n\ty\n', 'a=x\\\r\fy\n', 'a=x\\\n#y\n',
        'a=x\\\n!y\n', 'a=x\\', 'a=x\\\\', 'a=x\\\\\\', 'a=x\\\n',
        'a=x\\\n\n', '\\\n\n', '\\\n', '\\', '\\\n  #x\n',
        '#ignored\\\na=x\n', '  !ignored\na=x\n', 'a=x  \n', 'a=\\  x\n',
        'a\\u000Ab=x\n', 'a=\\\\u1234\n', 'a=\\uFEFF\n', '\f\t a \t :  x\n',
    ]
    rng = random.Random(20261111)
    atoms = ['a', 'Z', '0', ' ', '=', ':', '#', '!', '中文', '😀', r'\n', r'\t', r'\r', r'\f', r'\\', r'\q', r'\u0061', r'\u4e2d', r'\ ']
    for i in range(200):
        cases.append(''.join(f'key{j}{rng.choice(["=", ":", " : ", " "])}' + ''.join(rng.choice(atoms) for _ in range(rng.randint(0,40))) + rng.choice(['\n','\r','\r\n']) for j in range(rng.randint(1,8))))
    paths = []
    def convert(item):
        i, source = item
        original = WORK / f'{i:03}.in.properties'
        result = WORK / f'{i:03}.out.properties'
        original.write_bytes(source.encode('utf-8'))
        first = subprocess.run([CLI, 'to-yaml', '--literal'], input=source.encode('utf-8'), capture_output=True, check=True)
        second = subprocess.run([CLI, 'to-properties', '--literal'], input=first.stdout, capture_output=True, check=True)
        result.write_bytes(second.stdout)
        return original, result
    with ThreadPoolExecutor(max_workers=6) as pool:
        for pair in pool.map(convert, enumerate(cases)):
            paths.extend(pair)
    parsed = []
    for start in range(0, len(paths), 80):
        output = subprocess.run(['java', '-cp', str(WORK), 'PropertiesOracle', *map(str, paths[start:start+80])], capture_output=True, check=True).stdout.decode('ascii')
        for block in output.split('FILE')[1:]:
            values = {}
            for row in block.splitlines():
                if not row:
                    continue
                key, value = row.split(':')
                values[base64.b64decode(key).decode('utf-8')] = base64.b64decode(value).decode('utf-8')
            parsed.append(values)
    errors = []
    for i, source in enumerate(cases):
        if parsed[2*i] != parsed[2*i+1]:
            errors.append({'case': i, 'input': source, 'expected': parsed[2*i], 'actual': parsed[2*i+1]})
    report = {'cases': len(cases), 'passed': len(cases)-len(errors), 'errors': errors}
    (EVIDENCE / 'java-compat.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if errors:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
