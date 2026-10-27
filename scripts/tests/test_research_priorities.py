"""Synthetic projection/state tests; no research or retained input execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_priorities import Context, LABELS, check_reviewed_inputs, digest, project, read_json, rubric_hash, study_hash, validate_registry


class Priorities(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for folder in ['strategies', 'studies/01_example', 'apps/narada/content', 'apps/narada/public/publications/example-report']:
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        (self.root / 'strategies/research-priority-rubric.md').write_text('Synthetic rubric1.0\n')
        self.study = {'studyId': '01_example', 'slug': 'example', 'title': 'Synthetic question', 'summary': 'Saved synthetic scope.', 'topic': 'Synthetic', 'products': ['ES'], 'evidenceStatus': 'Synthetic, not a finding.', 'featuredPublicationId': 'example-report', 'featuredSourceRunId': 'example_run'}
        self.catalog = {'schemaVersion': '1.0', 'studies': [self.study]}
        self.write('apps/narada/content/studies.json', self.catalog)
        self.write('apps/narada/public/publications/index.json', {'schemaVersion': '1.0', 'reports': [{'id': 'example-report', 'source': {'runId': 'example_run'}, 'sourceSha256': 'a' * 64}]})
        self.write('apps/narada/public/publications/example-report/report.json', {'report': {'id': 'example-report', 'source': {'runId': 'example_run'}, 'sections': [{'id': 'findings'}]}, 'provenance': {'sourceSha256': 'a' * 64}})
        self.context = Context(self.root)
        source = {'publicationId': 'example-report', 'sourceRunId': 'example_run', 'sourceSha256': 'a' * 64, 'sectionId': 'findings'}
        self.assessment = {'assessmentId': 'example-20261026', 'studyId': '01_example', 'rubricVersion': '1.0', 'rubricSha256': self.context.rubric_sha, 'reviewedAt': '2026-10-26', 'reviewer': 'Synthetic fixture reviewer', 'state': 'assessed', 'score': 2, 'scope': 'One synthetic question.', 'rationale': 'A bounded definition test is needed.', 'materiality': 'Specify units before testing.', 'supporting': [{'text': 'Saved synthetic scope only.', 'source': source}], 'contrary': [{'text': 'No claimed execution evidence.', 'source': source}], 'blocker': 'No executed test.', 'nextTest': {'description': 'Define a synthetic prospective test.', 'supports': 'Prespecified success criterion.', 'rejects': 'Prespecified rejection criterion.'}, 'reviewedStudySha256': study_hash(self.study), 'reviewedPublications': self.context.bindings(self.study), 'reviewedMaterials': [{'path': 'strategies/research-priority-rubric.md', 'sha256': self.context.rubric_sha}], 'reviewNotes': ['Private notes do not cross the projection.']}
        self.registry = {'schemaVersion': '1.0', 'rubric': {'version': '1.0', 'meaning': 'Synthetic research triage.', 'disclaimer': 'Not a trade recommendation.', 'bands': [{'score': n + 1, 'label': label, 'definition': f'Synthetic definition {n + 1}.'} for n, label in enumerate(LABELS)]}, 'assessments': [self.assessment]}

        self.assessment['rubricSha256'] = rubric_hash(self.registry['rubric'], self.context.rubric_sha)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value, indent=2) + '\n')

    def test_projection_is_bounded_idempotent_and_keeps_private_fields_out(self):
        result = project(self.registry, self.context)
        p = result['studies'][0]['researchPriority']
        self.assertEqual(p['score'], 2)
        self.assertNotIn('reviewedMaterials', p)
        self.assertNotIn('reviewNotes', p)
        self.assertNotIn('bundleSha256', p['reviewedPublications'][0])
        stripped = copy.deepcopy(result)
        del stripped['studies'][0]['researchPriority']; del stripped['researchPriorityRubric']
        self.assertEqual(stripped, self.catalog)
        self.assertEqual(project(self.registry, Context(self.root, catalog=result)), result)

    def test_absence_is_not_a_zero_score(self):
        self.registry['assessments'] = []
        result = project(self.registry, self.context)
        self.assertNotIn('researchPriority', result['studies'][0])

    def test_states_and_integer_score_rules(self):
        for score in [0, 6, True, 2.5, '2', None]:
            with self.subTest(score=score):
                bad = copy.deepcopy(self.registry); bad['assessments'][0]['score'] = score
                with self.assertRaises(ValueError): project(bad, self.context)
        for state in ['not_assessed', 'needs_review', 'not_applicable']:
            good = copy.deepcopy(self.registry); a = good['assessments'][0]; a['state'] = state; del a['score']
            self.assertEqual(project(good, self.context)['studies'][0]['researchPriority']['state'], state)
            a['score'] = 0
            with self.assertRaises(ValueError): project(good, self.context)

    def test_missing_wrong_or_changed_evidence_identities_fail(self):
        for key, value in [('sectionId', 'missing'), ('publicationId', 'unselected'), ('sourceRunId', 'wrong_run'), ('sourceSha256', 'b' * 64)]:
            bad = copy.deepcopy(self.registry); bad['assessments'][0]['supporting'][0]['source'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): project(bad, self.context)
        path = self.root / 'apps/narada/public/publications/example-report/report.json'
        path.write_text(path.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'bundle bytes'): project(self.registry, Context(self.root))

    def test_historical_rubric_scope_and_selection_bindings_are_not_rewritten(self):
        old = copy.deepcopy(self.registry)
        self.context.catalog['studies'][0]['summary'] = 'Changed question scope.'
        result = project(self.registry, self.context)
        self.assertEqual(result['studies'][0]['researchPriority']['reviewedStudySha256'], old['assessments'][0]['reviewedStudySha256'])
        (self.root / 'strategies/research-priority-rubric.md').write_text('Changed rubric\n')
        changed = project(self.registry, Context(self.root))
        self.assertNotEqual(rubric_hash(self.registry['rubric'], changed['researchPriorityRubric']['sourceSha256']), old['assessments'][0]['rubricSha256'])
        self.assertEqual(self.registry, old)

    def test_high_scores_need_explicit_evidence_gates(self):
        for score in [4, 5]:
            bad = copy.deepcopy(self.registry); bad['assessments'][0]['score'] = score
            with self.assertRaises(ValueError): project(bad, self.context)
        a = self.assessment; a['score'] = 4
        a['highPriorityEvidence'] = {key: copy.deepcopy(a['supporting'][0]) for key in ['executionAndCosts', 'separatedEvaluation', 'materialEffect']}
        project(self.registry, self.context)
        a['score'] = 5
        with self.assertRaises(ValueError): project(self.registry, self.context)
        a['highPriorityEvidence']['independentCorroboration'] = copy.deepcopy(a['supporting'][0])
        project(self.registry, self.context)

    def test_public_text_rejects_private_paths_and_unknown_fields(self):
        for mutate in [lambda a: a.update(rationale='Read /Users/private/source'), lambda a: a.update(extra=True), lambda a: a.update(reviewedAt='2026-02-30')]:
            bad = copy.deepcopy(self.registry); mutate(bad['assessments'][0])
            with self.assertRaises(ValueError): project(bad, self.context)

    def test_rubric_definition_and_full_authored_claim_bindings(self):
        original = rubric_hash(self.registry['rubric'], self.context.rubric_sha)
        self.registry['rubric']['bands'][0]['definition'] += ' Changed criterion.'
        self.assertNotEqual(rubric_hash(self.registry['rubric'], self.context.rubric_sha), original)
        study = copy.deepcopy(self.study)
        before = study_hash(study)
        study['overview'] = {'findings': [{'text': 'New contrary claim.'}], 'statistics': [{'selection': {'where': {'value': 0.25, 'zero': -0.0, 'flag': False}}}]}
        self.assertNotEqual(study_hash(study), before)
        digest_before = study_hash(study)
        study['overview']['findings'][0]['text'] += ' Changed.'
        self.assertNotEqual(study_hash(study), digest_before)

    def test_nonfinite_and_overflow_json_are_refused(self):
        file = self.root / 'overflow.json'
        for token in ['1e1000', '-1e1000', 'NaN', 'Infinity', '9' * 400]:
            file.write_text('{"value":' + token + '}')
            with self.assertRaises(ValueError): read_json(file)

    def test_cross_language_binding_vector(self):
        vector = {'studyId': '01_synthetic', 'title': 'É中文', 'overview': {'statistics': [{'selection': {'where': {'value': 0.25, 'zero': -0.0, 'flag': False, 'large': 1e+20}}}]}}
        self.assertEqual(study_hash(vector), '0669a280766483b701394300a58d2aacdc6b39f33f594b655fbe7e86eb19fdf2')

    def test_explicit_cli_check_write_and_reassessment_transition(self):
        self.write('strategies/research-priorities.json', self.registry)
        script = Path(__file__).resolve().parents[1] / 'project-research-priorities.py'
        def run(*args):
            return subprocess.run([sys.executable, str(script), '--root', str(self.root), *args], capture_output=True, text=True)
        original = (self.root / 'apps/narada/content/studies.json').read_bytes()
        self.assertNotEqual(run('--check').returncode, 0)
        self.assertEqual((self.root / 'apps/narada/content/studies.json').read_bytes(), original)
        self.assertEqual(run('--write').returncode, 0)
        self.assertEqual(run('--check').returncode, 0)
        self.assertEqual(run('--mark-needs-review', '01_example', '--reason', 'New contrary findings.', '--date', '2026-10-26').returncode, 0)
        flagged = json.loads((self.root / 'strategies/research-priorities.json').read_text())['assessments'][0]
        self.assertEqual(flagged['score'], 2)
        self.assertEqual(flagged['assessmentId'], self.assessment['assessmentId'])
        self.assertTrue(flagged['reassessment']['required'])
        self.assertNotEqual(run('--check').returncode, 0)
        self.assertEqual(run('--write').returncode, 0)
        self.assertEqual(run('--check').returncode, 0)

    def test_reviewed_material_audit_is_separate_and_read_only(self):
        self.assertEqual(check_reviewed_inputs(self.registry, self.root), [])
        (self.root / 'strategies/research-priority-rubric.md').write_text('Changed\n')
        findings = check_reviewed_inputs(self.registry, self.root)
        self.assertEqual(findings[0]['state'], 'changed')
        self.assertEqual(self.assessment['rubricSha256'], rubric_hash(self.registry['rubric'], self.context.rubric_sha))


if __name__ == '__main__':
    unittest.main()
