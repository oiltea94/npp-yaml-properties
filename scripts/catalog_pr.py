"""Prepare or submit a catalog PR using immutable, public release attachments."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_config import TARGETS, pe_machine
from scripts.plugin_list_entry import build_entry

UPSTREAM = 'notepad-plus-plus/nppPluginList'
START = '<!-- yamlproperties-catalog:start -->'
END = '<!-- yamlproperties-catalog:end -->'


def api(endpoint, method='GET', data=None):
    command = ['gh', 'api', endpoint, '--method', method]
    if data is not None:
        command += ['--input', '-']
    result = subprocess.run(command, input=json.dumps(data) if data is not None else None,
                            capture_output=True, text=True, encoding='utf-8', timeout=90)
    if result.returncode:
        raise RuntimeError(f'GitHub API {method} {endpoint}: {result.stderr.strip()}')
    return json.loads(result.stdout) if result.stdout.strip() else None


def pages(endpoint):
    results = []
    for page in range(1, 101):
        batch = api(f'{endpoint}{"&" if "?" in endpoint else "?"}per_page=100&page={page}')
        results.extend(batch)
        if len(batch) < 100:
            return results
    raise ValueError('Pagination limit exceeded')


def version_tuple(version):
    if not re.fullmatch(r'\d+(?:\.\d+){0,3}', version):
        raise ValueError('Invalid catalog version')
    parts = tuple(map(int, version.split('.')))
    return parts + (0,) * (4-len(parts))


def update_catalog(text, entry):
    catalog = json.loads(text)
    items = catalog['npp-plugins']
    matches = [item for item in items if item['folder-name'] == 'YamlProperties']
    if len(matches) > 1:
        raise ValueError('Duplicate YamlProperties entries')
    if matches:
        old = matches[0]
        if version_tuple(old['version']) > version_tuple(entry['version']):
            raise ValueError('Refusing to downgrade a catalog entry')
        if version_tuple(old['version']) == version_tuple(entry['version']) and old['id'] != entry['id']:
            raise ValueError('Different archive for the same version')
        if old == entry:
            return text
    for other in items:
        if other['folder-name'] != 'YamlProperties':
            for key in ['display-name', 'repository']:
                if other[key] == entry[key]:
                    raise ValueError(f'Duplicate catalog {key}')
    # Locate object spans with a JSON decoder so unrelated formatting stays intact.
    array = re.search(r'"npp-plugins"\s*:\s*\[', text)
    decoder = json.JSONDecoder()
    position = array.end()
    spans = []
    while True:
        while text[position].isspace() or text[position] == ',':
            position += 1
        if text[position] == ']':
            break
        item, end = decoder.raw_decode(text, position)
        spans.append((position, end, item))
        position = end
    newline = '\r\n' if '\r\n' in text else '\n'
    for start, end, item in spans:
        if item['folder-name'] == 'YamlProperties':
            indent = re.match(r'[ \t]*', text[text.rfind('\n', 0, start)+1:start]).group()
            block = json.dumps(entry, ensure_ascii=False, indent='\t').replace('\n', newline+indent)
            return text[:start] + block + text[end:]
    block = json.dumps(entry, ensure_ascii=False, indent='\t').replace('\n', newline+'\t\t')
    if spans:
        end = spans[-1][1]
        return text[:end] + ',' + newline+'\t\t'+block + text[end:]
    return text[:array.end()] + newline+'\t\t'+block + text[array.end():]


def find_open_pr(prs, fork):
    matches = [pr for pr in prs if pr['state'] == 'open'
               and (pr['head'].get('repo') or {}).get('full_name') == fork
               and (pr['head']['ref'] == 'add-yamlproperties-x64'
                    or re.fullmatch(r'yamlproperties-v\d+\.\d+\.\d+', pr['head']['ref']))]
    if len(matches) > 1:
        raise ValueError('Multiple open YamlProperties PRs; resolve the duplicate PRs first')
    return matches[0] if matches else None


def pr_body(tag, entries, homepage, previous=''):
    block = f'''{START}
## YamlProperties {tag} (x86, x64, ARM64)

Release: {homepage}/releases/tag/{tag}

Only the three YamlProperties catalog entries are added or updated. Public release
downloads, ZIP/DLL SHA-256, DLL architecture, root DLL layout and the full catalog
schema have been checked by the submission workflow.

| Architecture | Plugins Admin ZIP SHA-256 |
| --- | --- |
'''
    block += ''.join(f'| {arch} | `{entry["id"]}` |\n' for arch, entry in entries.items())
    block += f'''
Plugins Admin search/install/remove/update detection is not verified by this
automation. Release editor integration and installer checks are separate tests.
Maintainer review and official list distribution remain required.
{END}'''
    if START in previous and END in previous:
        return re.sub(re.escape(START)+r'.*?'+re.escape(END), lambda _: block, previous, count=1, flags=re.S)
    return block + ('\n\n## Previous submission context / reviewer notes\n\n'+previous if previous else '') + '\n'


def file_at(repo, path, ref):
    result = api(f'repos/{repo}/contents/{path}?ref={ref}')
    if result.get('encoding') != 'base64':
        raise ValueError(f'Unexpected content encoding: {path}')
    return base64.b64decode(result['content']).decode('utf-8')


def download(url, path):
    request = urllib.request.Request(url, headers={'User-Agent': 'YamlProperties-catalog-release'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(32*1024*1024+1)
    if len(data) > 32*1024*1024:
        raise ValueError('Release asset exceeds 32 MiB')
    path.write_bytes(data)
    return data


def prepare(args):
    from jsonschema import Draft202012Validator, FormatChecker
    if not re.fullmatch(r'v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)', args.tag):
        raise ValueError('Expected a stable vMAJOR.MINOR.PATCH tag')
    for repo in [args.repository, args.fork]:
        if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+', repo):
            raise ValueError('Expected owner/repository')
    release = api(f'repos/{args.repository}/releases/tags/{args.tag}')
    if release['draft'] or release['prerelease'] or release['tag_name'] != args.tag:
        raise ValueError('Expected a published stable release')
    upstream = api(f'repos/{UPSTREAM}')
    fork = api(f'repos/{args.fork}')
    if not fork.get('fork') or fork.get('parent', {}).get('full_name') != UPSTREAM:
        raise ValueError('Configured fork does not belong to nppPluginList')
    prs = pages(f'repos/{UPSTREAM}/pulls?state=open')
    pr = find_open_pr(prs, args.fork)
    upstream_sha = api(f'repos/{UPSTREAM}/commits/{upstream["default_branch"]}')['sha']
    branch = pr['head']['ref'] if pr else 'yamlproperties-'+args.tag
    refs = [] if pr else api(f'repos/{args.fork}/git/matching-refs/heads/{branch}')
    existing = next((ref for ref in refs if ref['ref'] == 'refs/heads/'+branch), None)
    branch_exists = bool(pr or existing)
    base_sha = pr['head']['sha'] if pr else existing['object']['sha'] if existing else upstream_sha
    base_repo = args.fork if branch_exists else UPSTREAM
    allowed_paths = {f'src/pl.{arch}.json' for arch in TARGETS}
    if pr:
        files = pages(f'repos/{UPSTREAM}/pulls/{pr["number"]}/files')
        if any(item['filename'] not in allowed_paths for item in files):
            raise ValueError('Existing PR includes files outside the three catalogs')
    elif existing:
        comparison = api(f'repos/{UPSTREAM}/compare/{upstream_sha}...{args.fork.split("/")[0]}:{branch}')
        if any(item['filename'] not in allowed_paths for item in comparison['files']):
            raise ValueError('Existing release branch includes files outside the three catalogs')
    schema = json.loads(file_at(UPSTREAM, 'pl.schema', upstream_sha))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    args.output.mkdir(parents=True, exist_ok=False)
    homepage = 'https://github.com/'+args.repository
    entries, changes = {}, []
    upstream_matches = True
    for arch in TARGETS:
        checksum_name = f'checksums-{arch}.json'
        base_url = homepage+'/releases/download/'+args.tag+'/'
        hashes = json.loads(download(base_url+checksum_name, args.output/checksum_name))
        name = f'YamlProperties-{args.tag[1:]}-{arch}-plugin-admin.zip'
        archive = args.output/name
        data = download(base_url+name, archive)
        if {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} != hashes[name]:
            raise ValueError(f'Public ZIP checksum mismatch: {arch}')
        with zipfile.ZipFile(archive) as z:
            dll = z.read('YamlProperties.dll')
            if pe_machine(dll) != TARGETS[arch][1]:
                raise ValueError(f'DLL architecture mismatch: {arch}')
            if len(dll) != hashes['YamlProperties.dll']['bytes']:
                raise ValueError(f'DLL size mismatch: {arch}')
        manifest = {'version': args.tag[1:], 'architecture': arch, 'sha256': hashes['YamlProperties.dll']['sha256']}
        entry = build_entry(homepage, args.author, args.minimum_npp, manifest, archive)
        entries[arch] = entry
        path = f'src/pl.{arch}.json'
        # Check upstream too, preventing an old retry from downgrading an accepted entry.
        upstream_text = file_at(UPSTREAM, path, upstream_sha)
        upstream_matches &= update_catalog(upstream_text, entry) == upstream_text
        original = file_at(base_repo, path, base_sha) if branch_exists else upstream_text
        updated = update_catalog(original, entry)
        validator.validate(json.loads(updated))
        (args.output/f'pl.{arch}.json').write_bytes(updated.encode('utf-8'))
        if updated != original:
            changes.append({'path': path, 'mode': '100644', 'type': 'blob', 'content': updated})
    title = f'Update YamlProperties {args.tag[1:]} (x86, x64, ARM64)'
    body = pr_body(args.tag, entries, homepage, (pr or {}).get('body') or '')
    (args.output/'pr-body.md').write_text(body, encoding='utf-8')
    plan = {'tag': args.tag, 'fork': args.fork, 'branch': branch, 'base_sha': base_sha,
            'branch_exists': branch_exists, 'upstream_matches': upstream_matches,
            'base_branch': upstream['default_branch'], 'pr_number': pr['number'] if pr else None,
            'title': title, 'changed_files': [change['path'] for change in changes], 'entries': entries}
    (args.output/'plan.json').write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8')
    return plan, changes, body


def submit(plan, changes, body):
    fork, branch = plan['fork'], plan['branch']
    if not plan['pr_number'] and plan['upstream_matches']:
        print('Official catalog already matches this release; no PR needed.')
        return None
    if plan['pr_number']:
        current = api(f'repos/{UPSTREAM}/pulls/{plan["pr_number"]}')
        if current['state'] != 'open' or current['head']['sha'] != plan['base_sha']:
            raise ValueError('PR changed during validation; rerun to refresh the plan')
    if changes:
        commit = api(f'repos/{fork}/git/commits/{plan["base_sha"]}')
        tree = api(f'repos/{fork}/git/trees', 'POST', {'base_tree': commit['tree']['sha'], 'tree': changes})
        commit = api(f'repos/{fork}/git/commits', 'POST', {
            'message': plan['title'], 'tree': tree['sha'], 'parents': [plan['base_sha']]})
        if plan['branch_exists']:
            api(f'repos/{fork}/git/refs/heads/{branch}', 'PATCH', {'sha': commit['sha'], 'force': False})
        else:
            api(f'repos/{fork}/git/refs', 'POST', {'ref': 'refs/heads/'+branch, 'sha': commit['sha']})
    if plan['pr_number']:
        pr = api(f'repos/{UPSTREAM}/pulls/{plan["pr_number"]}', 'PATCH', {'title': plan['title'], 'body': body})
    else:
        pr = api(f'repos/{UPSTREAM}/pulls', 'POST', {
            'title': plan['title'], 'body': body, 'head': fork.split('/')[0]+':'+branch,
            'base': plan['base_branch'], 'maintainer_can_modify': True})
    print('Catalog PR: '+pr['html_url'])
    return pr['html_url']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--repository', default='oiltea94/npp-yaml-properties')
    parser.add_argument('--fork', default='oiltea94/nppPluginList')
    parser.add_argument('--author', default='OILTEA')
    parser.add_argument('--minimum-npp', default='8.9.6.4')
    parser.add_argument('--output', type=Path, default=Path('catalog-output'))
    parser.add_argument('--submit', action='store_true', help='Write the fork branch and official PR')
    args = parser.parse_args()
    plan, changes, body = prepare(args)
    print(json.dumps({key: value for key, value in plan.items() if key != 'entries'}, indent=2))
    if args.submit:
        url = submit(plan, changes, body)
        (args.output/'result.json').write_text(json.dumps({'pr_url': url})+'\n', encoding='utf-8')
    else:
        print('Dry run complete; no GitHub branch or PR was modified.')


if __name__ == '__main__':
    main()
