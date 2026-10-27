"""Bounded offline editorial registry validation and explicit public projection.

Standard library only; no research imports, calculations, or default writes.
"""
from __future__ import annotations
import copy
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import struct

STATES = {'assessed', 'not_assessed', 'needs_review', 'not_applicable'}
LABELS = ['Pause', 'Define and test', 'Targeted follow-up', 'Strong candidate', 'Highest priority']
PUBLIC_KEYS = ('assessmentId', 'rubricVersion', 'rubricSha256', 'reviewedAt', 'reviewer', 'state', 'score', 'scope', 'rationale', 'materiality', 'supporting', 'contrary', 'blocker', 'nextTest', 'reviewedStudySha256', 'reviewedPublications', 'reassessment', 'highPriorityEvidence')
HASH = re.compile(r'^[a-f0-9]{64}$')
SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
STUDY = re.compile(r'^[0-9]{2}_[a-z0-9_]+$')
PRIVATE = re.compile(r'(?:file://|/Users/|/home/|[A-Za-z]:\\|(?:^|\s)(?:studies|runs|reports/exports)/)')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stable_hash(value):
    def typed(item):
        if item is None: return ['null']
        if isinstance(item, bool): return ['boolean', item]
        if isinstance(item, (int, float)):
            try:
                number = float(item)
            except OverflowError as error:
                raise ValueError('Nonfinite priority metadata.') from error
            require(math.isfinite(number), 'Nonfinite priority metadata.')
            return ['number', struct.pack('!d', 0.0 if number == 0 else number).hex()]
        if isinstance(item, str): return ['string', item]
        if isinstance(item, list): return ['array', [typed(child) for child in item]]
        return ['object', [[key, typed(item[key])] for key in sorted(item)]]
    return digest((json.dumps(typed(value), ensure_ascii=False, separators=(',', ':')) + '\n').encode())


def rubric_hash(rubric, guide_sha):
    return stable_hash({'guideSha256': guide_sha, 'rubric': rubric})


def read_json(path, maximum=1024 * 1024):
    require(path.is_file() and not path.is_symlink(), f'Expected regular metadata file: {path.name}.')
    raw = path.read_bytes()
    require(len(raw) <= maximum, f'Metadata byte budget exceeded: {path.name}.')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key.')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f'Nonfinite JSON value: {value}.')
    def number(value):
        parsed = float(value)
        require(math.isfinite(parsed), 'Nonfinite JSON numeric value.')
        return parsed
    def integer(value):
        parsed = int(value)
        try:
            require(math.isfinite(float(parsed)), 'Nonfinite JSON numeric value.')
        except OverflowError as error:
            raise ValueError('Nonfinite JSON numeric value.') from error
        return parsed
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid, parse_float=number, parse_int=integer)


def text(value, maximum=1200, public=True):
    require(isinstance(value, str) and value and value == value.strip() and len(value) <= maximum, 'Invalid bounded assessment text.')
    require(not any(ord(c) < 32 and c not in '\n\t' or ord(c) == 127 for c in value), 'Assessment text contains controls.')
    require(not public or not PRIVATE.search(value), 'Private source locator in public assessment text.')


def date(value):
    require(isinstance(value, str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value)), 'Invalid review date.')
    require(dt.date.fromisoformat(value).isoformat() == value, 'Invalid review date.')


def selected_refs(study):
    analyses = [a for f in study.get('phaseFamilies', []) for a in f['analyses']] if study.get('phaseFamilies') else study.get('analyses', [])
    selected = [p for a in analyses for p in a['publicationTabs']] if analyses else [dict(publicationId=study['featuredPublicationId'], sourceRunId=study['featuredSourceRunId'])] + study.get('publicationTabs', [])[1:]
    return [{k: p[k] for k in ['publicationId', 'sourceRunId']} for p in selected + study.get('relatedPublications', [])]


def study_scope(study):
    return {key: value for key, value in study.items() if key not in ['researchPriority', 'resolvedResearchPriority', 'resolvedOverview']}


def study_hash(study):
    return stable_hash(study_scope(study))


class Context:
    def __init__(self, root, catalog=None):
        self.root = Path(root)
        self.catalog_path = self.root / 'apps/narada/content/studies.json'
        self.catalog = catalog if catalog is not None else read_json(self.catalog_path)
        self.index = read_json(self.root / 'apps/narada/public/publications/index.json')
        self.reports = {p['id']: p for p in self.index['reports']}
        require(len(self.reports) == len(self.index['reports']), 'Repeated public publication ID.')
        self.cache = {}
        self.rubric_path = self.root / 'strategies/research-priority-rubric.md'
        self.rubric_sha = digest(self.rubric_path.read_bytes())

    def bundle(self, publication_id):
        require(isinstance(publication_id, str) and SLUG.fullmatch(publication_id), 'Invalid public publication ID.')
        require(publication_id in self.reports, f'Publication is not explicitly public: {publication_id}.')
        if publication_id not in self.cache:
            directory = self.root / 'apps/narada/public/publications' / publication_id
            require(not directory.is_symlink(), 'Publication directory must not be a symlink.')
            path = directory / 'report.json'
            bundle = read_json(path, 4 * 1024 * 1024)
            self.cache[publication_id] = (bundle, digest(path.read_bytes()))
        return self.cache[publication_id]

    def bindings(self, study):
        result = []
        for ref in selected_refs(study):
            bundle, sha = self.bundle(ref['publicationId'])
            require(bundle['report']['source']['runId'] == ref['sourceRunId'], 'Study source-run attribution disagrees.')
            result.append({**ref, 'sourceSha256': bundle['provenance']['sourceSha256'], 'bundleSha256': sha})
        return result


def evidence_items(assessment):
    return assessment['supporting'] + assessment['contrary'] + list(assessment.get('highPriorityEvidence', {}).values())


def validate_registry(registry, context):
    require(set(registry) == {'schemaVersion', 'rubric', 'assessments'} and registry['schemaVersion'] == '1.0', 'Invalid research-priority registry version/fields.')
    rubric = registry['rubric']
    require(set(rubric) == {'version', 'meaning', 'disclaimer', 'bands'} and re.fullmatch(r'\d+\.\d+', rubric['version']), 'Invalid rubric fields/version.')
    text(rubric['meaning'], 500); text(rubric['disclaimer'], 500)
    require(len(rubric['bands']) == 5, 'Rubric requires five bands.')
    for i, band in enumerate(rubric['bands']):
        require(set(band) == {'score', 'label', 'definition'} and type(band['score']) is int and band['score'] == i + 1 and band['label'] == LABELS[i], 'Invalid rubric band order/label.')
        text(band['definition'], 500)
    require(isinstance(registry['assessments'], list) and len(registry['assessments']) <= 64, 'Assessment count exceeds its bound.')
    ids, studies = set(), set()
    required = set(PUBLIC_KEYS) - {'score', 'reassessment', 'highPriorityEvidence'} | {'studyId', 'reviewedMaterials', 'reviewNotes'}
    allowed = set(PUBLIC_KEYS) | {'studyId', 'reviewedMaterials', 'reviewNotes'}
    owner = {p['publicationId']: s['studyId'] for s in context.catalog['studies'] for p in selected_refs(s)}
    for a in registry['assessments']:
        require(isinstance(a, dict) and required <= set(a) <= allowed, 'Invalid assessment fields.')
        require(STUDY.fullmatch(a['studyId']) and (context.root / 'studies' / a['studyId']).is_dir(), 'Unknown assessment study.')
        require(SLUG.fullmatch(a['assessmentId']) and a['assessmentId'] not in ids and a['studyId'] not in studies, 'Repeated assessment/study identity.')
        ids.add(a['assessmentId']); studies.add(a['studyId'])
        require(a['state'] in STATES, 'Unknown assessment state.')
        if a['state'] == 'assessed':
            require(type(a.get('score')) is int and 1 <= a['score'] <= 5, 'Assessed priority requires integer score 1–5.')
        else:
            require('score' not in a, 'Nonnumeric states cannot carry a current score.')
        require(re.fullmatch(r'\d+\.\d+', a['rubricVersion']), 'Invalid reviewed rubric version.')
        for key in ['rubricSha256', 'reviewedStudySha256']:
            require(isinstance(a[key], str) and HASH.fullmatch(a[key]), 'Invalid assessment hash.')
        date(a['reviewedAt'])
        for key, limit in [('reviewer', 200), ('scope', 1000), ('rationale', 1200), ('materiality', 1000), ('blocker', 1000)]: text(a[key], limit)
        require(set(a['nextTest']) == {'description', 'supports', 'rejects'}, 'Next test requires explicit support/reject criteria.')
        for value in a['nextTest'].values(): text(value)
        if 'reassessment' in a:
            flag = a['reassessment']; require(set(flag) == {'required', 'reason', 'markedAt'} and flag['required'] is True, 'Invalid reassessment flag.')
            text(flag['reason'], 1000); date(flag['markedAt'])
        require(isinstance(a['reviewedPublications'], list) and 1 <= len(a['reviewedPublications']) <= 128, 'Invalid reviewed publication coverage.')
        reviewed = {}
        for source in a['reviewedPublications']:
            require(set(source) == {'publicationId', 'sourceRunId', 'sourceSha256', 'bundleSha256'}, 'Invalid reviewed publication binding.')
            require(source['publicationId'] not in reviewed, 'Duplicate reviewed publication.')
            bundle, sha = context.bundle(source['publicationId']); report = bundle['report']; index = context.reports[source['publicationId']]
            require(owner.get(source['publicationId'], a['studyId']) == a['studyId'], 'Priority evidence belongs to another study.')
            require(source['sourceRunId'] == report['source']['runId'] == index['source']['runId'] and source['sourceSha256'] == bundle['provenance']['sourceSha256'] == index['sourceSha256'], 'Invalid reviewed publication identity.')
            require(HASH.fullmatch(source['sourceSha256']) and source['bundleSha256'] == sha, 'Reviewed canonical bundle bytes changed.')
            reviewed[source['publicationId']] = source
        for key in ['supporting', 'contrary']:
            require(isinstance(a[key], list) and len(a[key]) <= 6, 'Evidence list exceeds its bound.')
        if a.get('score', 0) >= 4:
            proof = a.get('highPriorityEvidence', {})
            require({'executionAndCosts', 'separatedEvaluation', 'materialEffect'} <= set(proof), 'High priority needs explicit material separated evaluation and execution/cost evidence.')
            require(a['score'] != 5 or 'independentCorroboration' in proof, 'Highest priority needs independent corroboration evidence.')
        if 'highPriorityEvidence' in a:
            require(set(a['highPriorityEvidence']) <= {'executionAndCosts', 'separatedEvaluation', 'materialEffect', 'independentCorroboration'}, 'Unknown high-priority evidence gate.')
        for item in evidence_items(a):
            require(set(item) == {'text', 'source'}, 'Invalid evidence explanation.')
            text(item['text'], 800); source = item['source']
            require(set(source) == {'publicationId', 'sourceRunId', 'sourceSha256', 'sectionId'}, 'Invalid public evidence reference fields.')
            bound = reviewed.get(source['publicationId'])
            require(bound and all(source[k] == bound[k] for k in ['publicationId', 'sourceRunId', 'sourceSha256']), 'Evidence must cite an exactly reviewed publication.')
            bundle, _ = context.bundle(source['publicationId'])
            require(any(s['id'] == source['sectionId'] for s in bundle['report']['sections']), 'Missing referenced saved report section.')
        require(isinstance(a['reviewedMaterials'], list) and 1 <= len(a['reviewedMaterials']) <= 128, 'Invalid reviewed material inventory.')
        for item in a['reviewedMaterials']:
            require(set(item) == {'path', 'sha256'} and isinstance(item['path'], str) and not Path(item['path']).is_absolute() and '..' not in Path(item['path']).parts and HASH.fullmatch(item['sha256']), 'Invalid local reviewed material locator/hash.')
        require(isinstance(a['reviewNotes'], list) and len(a['reviewNotes']) <= 32, 'Invalid private review notes.')
        for note in a['reviewNotes']: text(note, 3000, public=False)
    return registry


def project(registry, context):
    validate_registry(registry, context)
    by_study = {a['studyId']: a for a in registry['assessments']}
    result = copy.deepcopy(context.catalog)
    result['researchPriorityRubric'] = {**copy.deepcopy(registry['rubric']), 'sourceSha256': context.rubric_sha}
    for study in result['studies']:
        a = by_study.get(study['studyId'])
        if not a:
            study.pop('researchPriority', None)
            continue
        public = {k: copy.deepcopy(a[k]) for k in PUBLIC_KEYS if k in a}
        public['reviewedPublications'] = [{k: source[k] for k in ['publicationId', 'sourceRunId', 'sourceSha256']} for source in a['reviewedPublications']]
        study['researchPriority'] = public
    require(len((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()) <= 512 * 1024, 'Projected catalog exceeds its bounded 512 KiB budget.')
    return result


def check_reviewed_inputs(registry, root):
    findings = []
    for a in registry['assessments']:
        for item in a['reviewedMaterials']:
            path = Path(root) / item['path']
            try:
                require(path.resolve().is_relative_to(Path(root).resolve()), 'Review material escapes workspace.')
                actual = digest(path.read_bytes())
                if actual != item['sha256']: findings.append({'studyId': a['studyId'], 'path': item['path'], 'state': 'changed'})
            except (OSError, ValueError):
                findings.append({'studyId': a['studyId'], 'path': item['path'], 'state': 'missing_or_unavailable'})
    return findings
