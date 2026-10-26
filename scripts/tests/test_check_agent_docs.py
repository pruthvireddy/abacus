"""Focused fixtures for the read-only active-guide checker."""
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('check_agent_docs', Path(__file__).resolve().parents[1] / 'check-agent-docs.py')
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class CheckAgentDocsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repo'
        self.root.mkdir()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def check(self, source, **kwargs):
        self.write('AGENTS.md', source)
        return checker.check(self.root, ('AGENTS.md',), **kwargs)

    def registry(self, guides=('README.md',)):
        registry = {
            'schema_version': 1,
            'default_profile': 'default',
            'profiles': {'default': {'description': 'Fixture', 'checks': ['docs']}},
            'owners': {'workspace': {
                'kind': 'workspace', 'path': '.', 'description': 'Workspace',
                'guides': list(guides), 'read_first': list(guides),
                'entry_points': ['scripts/check-agent-docs.py'],
                'preservation': ['Preserve retained evidence'],
            }},
            'checks': [{
                'id': 'docs', 'owner': 'workspace', 'kind': 'command',
                'description': 'Docs', 'cwd': '.',
                'argv': ['{python}', 'scripts/check-agent-docs.py'],
                'env': {}, 'prerequisites': [], 'scope': ['Fixture guides'],
            }],
        }
        self.write('scripts/check-agent-docs.py', '# Fixture entry point\n')
        self.write_registry(registry)
        return registry

    def write_registry(self, registry):
        self.write('config/workspace-checks.json', json.dumps(registry))

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes() if path.is_file() else None
                for path in self.root.rglob('*')}

    def main_output(self):
        with patch('sys.argv', ['check-agent-docs.py', '--root', str(self.root)]), contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
            outcome = checker.main()
        return outcome, stdout.getvalue(), stderr.getvalue()

    def test_missing_required_guide_has_file_and_line(self):
        self.assertEqual(checker.check(self.root, ('docs/README.md',)), ['docs/README.md:1: missing required navigation guide'])

    def test_broken_target_and_anchor_have_source_lines(self):
        self.write('docs/valid.md', '# A heading\n')
        errors = self.check('# Navigation\n[Missing](no-such.md)\n[Bad heading](docs/valid.md#absent)\n')
        self.assertEqual(len(errors), 2)
        self.assertTrue(errors[0].startswith('AGENTS.md:2: missing link target:'))
        self.assertTrue(errors[1].startswith('AGENTS.md:3: missing Markdown heading anchor:'))

    def test_relative_encoded_and_angle_paths_and_duplicate_anchors(self):
        self.write('docs/Space Name.md', '# A heading\n## Repeated\n## Repeated\n## `Code` & Café!\nSetext title\n============\n')
        self.write('docs/Guide_(small).md', '# Small\n')
        errors = self.check('[One](docs/Space%20Name.md#a-heading)\n[Two](<docs/Space Name.md#repeated-1>)\n[Three](docs/Space%20Name.md#code--caf%C3%A9)\n[Four](docs/Space%20Name.md#setext-title "Title")\n[Five](docs/Guide_(small).md#small)\n[Directory](docs/)\n')
        self.assertEqual(errors, [])
        self.write('docs/AGENTS.md', '[Parent](../AGENTS.md)\n')
        self.assertEqual(checker.check(self.root, ('docs/AGENTS.md',)), [])

    def test_self_link_fragments_and_duplicate_collisions(self):
        errors = self.check('# Intro\n## Intro\n## Intro-1\n[Self](#intro) [Duplicate](#intro-1) [Collision](#intro-1-1)\n')
        self.assertEqual(errors, [])

    def test_outside_paths_and_symlinks_fail(self):
        outside = self.root.parent / 'outside.md'
        outside.write_text('# Outside\n', encoding='utf-8')
        (self.root / 'linked.md').symlink_to(outside)
        errors = self.check('[Relative](../outside.md)\n[Symlink](linked.md)\n')
        self.assertEqual(len(errors), 2)
        self.assertTrue(all('outside repository' in error for error in errors))
        (self.root / 'escape').symlink_to(self.root.parent, target_is_directory=True)
        self.assertIn('outside repository', self.check('[Escaped directory](escape/outside.md)')[0])

    def test_required_guide_symlink_cannot_escape(self):
        outside = self.root.parent / 'outside.md'
        outside.write_text('# Outside\n', encoding='utf-8')
        (self.root / 'AGENTS.md').symlink_to(outside)
        self.assertEqual(checker.check(self.root, ('AGENTS.md',)), ['AGENTS.md:1: required guide resolves outside repository'])

    def test_code_fences_inline_code_comments_and_external_links_are_ignored(self):
        errors = self.check('''# Guide
`[Inline](missing.md)` and ``[More](also-missing.md)``
```markdown
[Example](not-real.md)
# Hidden heading
```
~~~~text
[More](still-not-real.md)
~~~~
<!-- [Comment](secret.md) -->
[Web](https://example.invalid/never-fetch) [Email](mailto:test@example.invalid)
[Network](//example.invalid/page)
''')
        self.assertEqual(errors, [])
        self.assertNotIn('hidden-heading', checker.anchors((self.root / 'AGENTS.md').read_text()))

    def test_reference_links_definitions_and_undefined_reference(self):
        self.write('docs/guide.md', '# Guide\n')
        errors = self.check('[Full][guide]\n[Guide][]\n[guide]\n[guide]: docs/guide.md#guide "Description"\n[Missing][undefined]\n')
        self.assertEqual(errors, ['AGENTS.md:5: undefined link reference [undefined]'])
        self.assertEqual(self.check('[unused]: nonexistent.md\n'), ['AGENTS.md:1: missing link target: nonexistent.md'])

    def test_linked_documents_are_not_recursively_crawled(self):
        self.write('runs/example/report.md', '# Result\n[Broken private link](nonexistent.md)\n')
        self.assertEqual(self.check('[Result](runs/example/report.md#result)'), [])

    def test_cli_is_read_only_and_exits_nonzero(self):
        self.write('AGENTS.md', '[Broken](missing.md)\n')
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        with patch('sys.argv', ['check-agent-docs.py', '--root', str(self.root)]), patch.object(checker, 'guide_inventory', return_value=('AGENTS.md',)), contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(checker.main(), 1)
        self.assertIn('AGENTS.md:1:', stderr.getvalue())
        self.assertIn('Checked 1 active navigation guides', stdout.getvalue())
        self.assertIn('1 error(s)', stdout.getvalue())
        after = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(before, after)

    def test_default_is_resolved_at_call_time_and_injection_bypasses_registry(self):
        self.write('README.md', '# Guide\n')
        self.write('second.md', '[Missing](absent.md)\n')
        with patch.object(checker, 'guide_inventory', side_effect=[('README.md',), ('second.md',)]) as inventory:
            self.assertEqual(checker.check(self.root), [])
            self.assertEqual(checker.check(self.root), ['second.md:1: missing link target: absent.md'])
            self.assertEqual(inventory.call_count, 2)
        with patch.object(checker, 'guide_inventory', side_effect=AssertionError('injected guides must not load registry')):
            self.assertEqual(checker.check(self.root, ('README.md',)), [])

    def test_duplicate_injected_guide_fails(self):
        self.write('README.md', '# Guide\n')
        self.assertEqual(checker.check(self.root, ('README.md', 'README.md')), ['README.md:1: duplicate required navigation guide'])

    def test_invalid_default_inventory_is_nonpassing_without_a_fabricated_count(self):
        with patch.object(checker, 'guide_inventory', side_effect=ValueError('duplicate guide')):
            self.assertEqual(checker.check(self.root), ['config/workspace-checks.json:1: invalid maintained guide registry: duplicate guide'])
            with patch('sys.argv', ['check-agent-docs.py', '--root', str(self.root)]), contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(checker.main(), 1)
        self.assertIn('Checked 0 active navigation guides: 1 error(s).', stdout.getvalue())
        self.assertIn('duplicate guide', stderr.getvalue())

    def test_newly_declared_study_links_are_checked(self):
        self.write('README.md', '# Workspace\n')
        self.write('studies/12_example/README.md', '# Study\n[Plan](plan.md#protocol)\n[Broken](absent.md)\n')
        self.write('studies/12_example/plan.md', '# Protocol\n')
        self.registry(('README.md', 'studies/12_example/README.md', 'studies/12_example/plan.md'))
        self.assertEqual(checker.check(self.root), ['studies/12_example/README.md:3: missing link target: absent.md'])

    def test_registry_guide_count_changes_between_calls(self):
        self.write('README.md', '# Workspace\n')
        registry = self.registry()
        outcome, stdout, stderr = self.main_output()
        self.assertEqual(outcome, 0)
        self.assertEqual(stderr, '')
        self.assertIn('Checked 1 active navigation guides: 0 error(s).', stdout)
        self.write('studies/18_example/README.md', '# Study\n')
        registry['owners']['workspace']['guides'].append('studies/18_example/README.md')
        self.write_registry(registry)
        outcome, stdout, stderr = self.main_output()
        self.assertEqual(outcome, 0)
        self.assertEqual(stderr, '')
        self.assertIn('Checked 2 active navigation guides: 0 error(s).', stdout)

    def test_missing_guide_declaration_is_nonpassing(self):
        self.write('README.md', '# Workspace\n')
        self.registry(('README.md', 'studies/18_example/README.md'))
        errors = checker.check(self.root)
        self.assertTrue(errors)
        self.assertIn('studies/18_example/README.md', errors[0])

    def test_duplicate_guide_declaration_is_nonpassing(self):
        self.write('README.md', '# Workspace\n')
        registry = self.registry()
        registry['owners']['other'] = deepcopy(registry['owners']['workspace'])
        self.write_registry(registry)
        errors = checker.check(self.root)
        self.assertTrue(errors)
        self.assertIn('duplicate', errors[0].lower())

    def test_escaping_guide_declaration_is_nonpassing(self):
        outside = self.root.parent / 'outside.md'
        outside.write_text('# Outside\n', encoding='utf-8')
        self.registry(('../outside.md',))
        errors = checker.check(self.root)
        self.assertTrue(errors)
        self.assertIn('bounded repository-relative path', errors[0])

    def test_study_18_guides_do_not_require_study_json(self):
        self.write('README.md', '# Workspace\n')
        registry = self.registry()
        study = 'studies/18_fibonacci_memory'
        self.write(study + '/README.md', '# Study\n[Plan](plan.md#protocol)\n')
        self.write(study + '/plan.md', '# Protocol\n')
        self.write(study + '/tests/test_fixture.py', '# Tests are not imported by the documentation checker\n')
        registry['owners']['study-18'] = {
            'kind': 'study', 'study_id': '18_fibonacci_memory', 'path': study,
            'description': 'Study 18 fixture',
            'guides': [study + '/README.md', study + '/plan.md'],
            'read_first': [study + '/README.md', study + '/plan.md'],
            'entry_points': [study + '/tests'],
            'preservation': ['Do not generate metadata or evidence'],
        }
        self.write_registry(registry)
        before = self.snapshot()
        self.assertEqual(checker.check(self.root), [])
        self.assertEqual(len(checker.guide_inventory(self.root)), 3)
        self.assertFalse((self.root / study / 'study.json').exists())
        self.assertEqual(self.snapshot(), before)

    def test_historical_adapter_explicitly_lacks_a_current_plan(self):
        self.write('README.md', '# Workspace\n')
        registry = self.registry()
        study = 'studies/01_reversal_follow_through'
        self.write(study + '/README.md', '# Historical adapter\n')
        registry['owners']['study-01'] = {
            'kind': 'study', 'study_id': '01_reversal_follow_through', 'path': study,
            'description': 'Historical adapter fixture',
            'guides': [study + '/README.md'], 'read_first': [study + '/README.md'],
            'entry_points': [study + '/README.md'],
            'preservation': ['Preserve historical implementations'],
            'plan_absence_reason': 'Historical adapter has no current plan',
            'no_suite_reason': 'No local suite; legacy checks are separately registered',
        }
        self.write_registry(registry)
        before = self.snapshot()
        self.assertEqual(checker.check(self.root), [])
        self.assertEqual(len(checker.guide_inventory(self.root)), 2)
        self.assertFalse((self.root / study / 'plan.md').exists())
        self.assertEqual(self.snapshot(), before)

    def test_registry_guide_symlink_cannot_escape(self):
        outside = self.root.parent / 'outside.md'
        outside.write_text('# Outside\n', encoding='utf-8')
        (self.root / 'README.md').symlink_to(outside)
        self.registry()
        errors = checker.check(self.root)
        self.assertTrue(errors)
        self.assertIn('escapes repository', errors[0])

    def test_registry_defaults_exclude_historical_markdown_and_are_read_only(self):
        self.write('README.md', '# Workspace\n[Evidence](runs/example/report.md)\n[Web](https://example.invalid/page)\n')
        for name in ('runs/example/report.md', 'reports/exports/example/README.md',
                     'legacy/example/README.md', 'apps/narada/releases/retained/README.md',
                     'apps/narada/out/README.md', 'data/example/README.md'):
            self.write(name, '# Retained\n[Broken](absent.md)\n')
        self.registry()
        before = self.snapshot()
        old_path = sys.path[:]
        old_bytecode = sys.dont_write_bytecode
        with patch('socket.create_connection', side_effect=AssertionError('no network')), patch('urllib.request.urlopen', side_effect=AssertionError('no network')):
            self.assertEqual(checker.check(self.root), [])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(sys.path, old_path)
        self.assertEqual(sys.dont_write_bytecode, old_bytecode)

    def test_cli_from_an_unrelated_cwd_uses_explicit_registry_read_only(self):
        self.write('README.md', '# Workspace\n')
        self.registry()
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(Path(checker.__file__).resolve()), '--root', str(self.root)],
                                cwd=self.root.parent, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Checked 1 active navigation guides: 0 error(s).', result.stdout)
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
