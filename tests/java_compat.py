"""Check raw YAML emission and YAML decoding against Java Properties.load(Reader)."""
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
    for direction in ['to-yaml', 'to-properties']:
        for flag in ['--quote-all', '--literal']:
            removed = subprocess.run([CLI, direction, flag], input=b'name=value\n', capture_output=True)
            assert removed.returncode == 2 and not removed.stdout, 'Removed CLI flag must be rejected'

    def oracle(paths):
        parsed = []
        for start in range(0, len(paths), 80):
            output = subprocess.run(['java', '-cp', str(WORK), 'PropertiesOracle', *map(str, paths[start:start+80])], capture_output=True, check=True).stdout.decode('ascii')
            for block in output.split('FILE')[1:]:
                values = {}
                for row in block.splitlines():
                    if row:
                        key, value = row.split(':')
                        values[base64.b64decode(key).decode('utf-8')] = base64.b64decode(value).decode('utf-8')
                parsed.append(values)
        return parsed

    originals = []
    for i, source in enumerate(cases):
        path = WORK / f'{i:03}.in.properties'
        path.write_bytes(source.encode('utf-8'))
        originals.append(path)
    expected = oracle(originals)

    def convert(item):
        i, source = item
        result = WORK / f'{i:03}.out.properties'
        first = subprocess.run([CLI, 'to-yaml'], input=source.encode('utf-8'), capture_output=True)
        yaml_input = json.dumps(expected[i], ensure_ascii=False).encode('utf-8')
        if '' in expected[i]:
            # Hierarchical paths have no empty-key representation in either direction.
            assert first.returncode == 1 and b'Empty property key' in first.stderr and not first.stdout
            second = subprocess.run([CLI, 'to-properties'], input=yaml_input, capture_output=True)
            assert second.returncode == 1 and b'Empty YAML key' in second.stderr and not second.stdout
            return None
        first.check_returncode()
        # Compare exact emission against independently parsed Java key/value text.
        # Raw output deliberately retains source syntax, even for special scalars.
        expected_yaml = ''.join(f'{key}: {value}\n' for key, value in expected[i].items()) or '{}\n'
        assert first.stdout.decode('utf-8') == expected_yaml, (i, source, first.stdout, expected_yaml)
        # Independently exercise YAML -> Properties with valid quoted YAML/JSON,
        # then let Java check retained quote syntax, escapes and empty values.
        second = subprocess.run([CLI, 'to-properties'], input=yaml_input, capture_output=True, check=True)
        result.write_bytes(second.stdout)
        return result
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(convert, enumerate(cases)))
    valid_indices = [i for i, path in enumerate(results) if path is not None]
    parsed = oracle([results[i] for i in valid_indices])
    errors = []
    for i, actual in zip(valid_indices, parsed):
        quoted = {key: json.dumps(value, ensure_ascii=False) for key, value in expected[i].items()}
        # The Java-decoded values must retain their exact JSON/YAML spelling;
        # Python's independent JSON parser must also recover the original text.
        if quoted != actual or {key: json.loads(value) for key, value in actual.items()} != expected[i]:
            errors.append({'case': i, 'input': cases[i], 'expected': quoted, 'actual': actual})
    report = {'cases': len(cases), 'passed': len(cases)-len(errors),
              'raw_emission_checks': len(valid_indices), 'empty_key_cases': len(cases)-len(valid_indices),
              'quoted_value_checks': len(valid_indices),
              'removed_flag_checks': 4, 'errors': errors}
    (EVIDENCE / 'java-compat.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if errors:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
