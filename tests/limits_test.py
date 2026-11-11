from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT/'build/ypconvert.exe'

def main():
    cases = [
        ('input size limit', 'to-yaml', b'x=' + b'a'*(8*1024*1024), b'8 MiB'),
        ('path depth limit', 'to-yaml', ('.'.join(['x']*65)+'=v').encode(), b'depth'),
        ('YAML depth limit', 'to-properties', ('x: '+ '['*70+'a'+']'*70).encode(), b'depth'),
        ('YAML parser recursion bound', 'to-properties', ('x: '+ '['*2000+'a'+']'*2000).encode(), b'YAML parse error'),
        ('array bound', 'to-yaml', b'a[10000]=v', b'index'),
        ('property count bound', 'to-yaml', ''.join(f'k{i}=x\n' for i in range(100001)).encode(), b'Too many properties'),
        ('expanded alias output bound', 'to-properties', ('base: &a "'+'x'*(1024*1024)+'"\n'+''.join(f'key{i}: *a\n' for i in range(20))).encode(), b'16 MiB'),
    ]
    results = []
    for name, mode, data, expected in cases:
        r = subprocess.run([CLI, mode], input=data, capture_output=True, timeout=15)
        assert r.returncode == 1 and expected in r.stderr, (name, r.returncode, r.stderr[:300])
        assert not r.stdout, (name, 'partial output on error')
        results.append({'test': name, 'result': 'PASS', 'message': r.stderr.decode('utf-8').strip()})
        print('PASS '+name)
    (ROOT/'evidence/limits-tests.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    main()
