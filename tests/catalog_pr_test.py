"""Exercise catalog updates and PR reuse without writing to GitHub."""
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.catalog_pr import update_catalog, find_open_pr, pr_body, version_tuple, submit


def entry(name='YamlProperties', version='0.4.1'):
    return {'folder-name': name, 'display-name': name, 'version': version,
            'id': 'a'*64, 'repository': 'https://github.com/example/'+name+'/'+version}


class CatalogTests(unittest.TestCase):
    def catalog(self, items, newline='\r\n'):
        return (json.dumps({'name': 'npp-pluginList', 'version': '1', 'arch': '64',
                            'npp-plugins': items}, indent='\t')+'\n').replace('\n', newline)

    def test_add_and_update_preserve_other_entries_and_line_endings(self):
        for newline in ['\n', '\r\n']:
            for items in [[entry('Other')], [entry('Other'), entry(version='0.4.0')], []]:
                with self.subTest(newline=newline, items=items):
                    before = self.catalog(items, newline)
                    after = update_catalog(before, entry())
                    parsed = json.loads(after)['npp-plugins']
                    self.assertEqual([p for p in parsed if p['folder-name'] != 'YamlProperties'],
                                     [p for p in items if p['folder-name'] != 'YamlProperties'])
                    self.assertEqual(next(p for p in parsed if p['folder-name']=='YamlProperties'), entry())
                    self.assertEqual('\r\n' in after, newline=='\r\n')

    def test_unchanged_catalog_is_byte_identical(self):
        before = self.catalog([entry('Other'), entry()])
        self.assertEqual(update_catalog(before, entry()), before)

    def test_downgrade_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'downgrade'):
            update_catalog(self.catalog([entry(version='0.5.0')]), entry())

    def test_same_version_new_hash_is_rejected(self):
        original = dict(entry(), id='b'*64)
        with self.assertRaisesRegex(ValueError, 'same version'):
            update_catalog(self.catalog([original]), entry())

    def test_duplicate_name_is_rejected(self):
        with self.assertRaises(ValueError):
            update_catalog(self.catalog([entry(), entry()]), entry())

    def test_pr_selection_reuses_legacy_and_automated_branches_only(self):
        def pr(branch, state='open', fork='oiltea94/nppPluginList'):
            return {'state': state, 'number': 1271,
                    'head': {'ref': branch, 'repo': {'full_name': fork}}}
        for branch in ['add-yamlproperties-x64', 'yamlproperties-v0.4.1']:
            match = pr(branch)
            self.assertEqual(find_open_pr([match], 'oiltea94/nppPluginList'), match)
        self.assertIsNone(find_open_pr([pr('unrelated'), pr('yamlproperties-v0.4.1', 'closed'),
                                       pr('yamlproperties-v0.4.1', fork='someone/nppPluginList')],
                                      'oiltea94/nppPluginList'))

    def test_multiple_open_prs_are_not_chosen_arbitrarily(self):
        prs = [{'state': 'open', 'head': {'ref': branch, 'repo': {'full_name': 'oiltea94/nppPluginList'}}}
               for branch in ['add-yamlproperties-x64', 'yamlproperties-v0.4.1']]
        with self.assertRaises(ValueError):
            find_open_pr(prs, 'oiltea94/nppPluginList')

    def test_body_updates_managed_section_and_preserves_manual_notes(self):
        entries = {'x64': entry()}
        first = pr_body('v0.4.1', entries, 'https://github.com/example/repo', 'Manual reviewer notes')
        second = pr_body('v0.4.2', entries, 'https://github.com/example/repo', first)
        self.assertIn('Manual reviewer notes', second)
        self.assertIn('v0.4.2', second)
        self.assertNotIn('v0.4.1', second)
        self.assertEqual(second.count('<!-- yamlproperties-catalog:start -->'), 1)
        self.assertIn('not verified', second)

    def test_version_comparison_is_numeric_and_padded(self):
        self.assertGreater(version_tuple('0.10.0'), version_tuple('0.9.0'))
        self.assertEqual(version_tuple('0.4.0'), version_tuple('0.4.0.0'))

    def plan(self, **changes):
        return dict({'fork': 'oiltea94/nppPluginList', 'branch': 'yamlproperties-v0.4.1',
                     'base_sha': 'base', 'pr_number': None, 'upstream_matches': False,
                     'branch_exists': False, 'title': 'Update YamlProperties 0.4.1',
                     'base_branch': 'master'}, **changes)

    def test_already_accepted_release_makes_no_api_writes(self):
        with patch('scripts.catalog_pr.api') as api:
            self.assertIsNone(submit(self.plan(upstream_matches=True), [], 'body'))
            api.assert_not_called()

    def test_retry_after_branch_push_creates_missing_pr(self):
        with patch('scripts.catalog_pr.api', return_value={'html_url': 'https://github.com/example/pull/1'}) as api:
            result = submit(self.plan(branch_exists=True), [], 'body')
            self.assertTrue(result.endswith('/1'))
            self.assertEqual(api.call_count, 1)
            self.assertEqual(api.call_args.args[1], 'POST')
            self.assertEqual(api.call_args.args[2]['head'], 'oiltea94:yamlproperties-v0.4.1')

    def test_pr_closed_during_validation_stops_before_writes(self):
        with patch('scripts.catalog_pr.api', return_value={'state': 'closed', 'head': {'sha': 'base'}}) as api:
            with self.assertRaisesRegex(ValueError, 'PR changed'):
                submit(self.plan(pr_number=1271, branch_exists=True), [], 'body')
            self.assertEqual(api.call_count, 1)

    def test_existing_pr_updates_without_creating_another(self):
        responses = [{'state': 'open', 'head': {'sha': 'base'}}, {'html_url': 'https://github.com/example/pull/1271'}]
        with patch('scripts.catalog_pr.api', side_effect=responses) as api:
            submit(self.plan(pr_number=1271, branch_exists=True), [], 'body')
            self.assertEqual(api.call_args.args[1], 'PATCH')
            self.assertTrue(api.call_args.args[0].endswith('/pulls/1271'))


if __name__ == '__main__':
    unittest.main()
