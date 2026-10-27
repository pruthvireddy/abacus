import assert from 'node:assert/strict';
import { readFile, mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { validateStudyCatalog, readStudyCatalog } from '../scripts/lib/studies.mjs';
import { priorityStudyHash, priorityFreshness } from '../scripts/lib/research-priorities.mjs';
const index = JSON.parse(await readFile('public/publications/index.json', 'utf8'));
const original = JSON.parse(await readFile('content/studies.json', 'utf8'));
const fixture = () => structuredClone(original);

test('absent and explicit nonnumeric states remain valid without zero scores', () => {
  const absent = fixture(); absent.studies.forEach(s => { delete s.researchPriority; }); delete absent.researchPriorityRubric;
  assert.doesNotThrow(() => validateStudyCatalog(absent, index.reports));
  for (const state of ['not_assessed', 'needs_review', 'not_applicable']) {
    const c = fixture(), p = c.studies[0].researchPriority; p.state = state; delete p.score;
    assert.doesNotThrow(() => validateStudyCatalog(c, index.reports));
    p.score = 0; assert.throws(() => validateStudyCatalog(c, index.reports));
  }
  for (const score of [0, 6, true, 1.5, '2', null, undefined]) {
    const c = fixture(); c.studies[0].researchPriority.score = score;
    assert.throws(() => validateStudyCatalog(c, index.reports));
  }
});

test('missing/incorrect identities and unsafe metadata fail independently of freshness', () => {
  for (const mutate of [
    p => { p.reviewedPublications[0].publicationId = 'missing'; },
    p => { p.reviewedPublications[0].sourceRunId = 'wrong_run'; },
    p => { p.reviewedPublications[0].sourceSha256 = 'a'.repeat(64); },
    p => { p.supporting[0].source.sourceSha256 = 'b'.repeat(64); },
    p => { p.reviewer = 'Read /Users/private/source'; },
    p => { p.reviewedAt = '2026-02-30'; },
    p => { p.state = 'unknown'; },
    p => { p.privatePath = 'runs/private'; },
  ]) { const c = fixture(); mutate(c.studies[0].researchPriority); assert.throws(() => validateStudyCatalog(c, index.reports)); }
});

test('valid historical assessments need review after scope, evidence set, rubric or explicit flag changes', () => {
  const c = fixture(), s = c.studies[0], p = s.researchPriority;
  assert.deepEqual(priorityFreshness(s, c.researchPriorityRubric, index.reports), { effectiveState: 'assessed', staleReasons: [] });
  for (const change of [
    study => { study.summary = 'Changed scope.'; },
    (study, rb) => { rb.version = '1.1'; },
    (study, rb) => { rb.sourceSha256 = 'a'.repeat(64); },
    (study, rb) => { rb.bands[2].definition = 'Changed materiality rule.'; },
    study => { study.overview.findings[0].text += ' New contrary qualification.'; },
    study => { study.overview.limitations[0].text += ' New scope limit.'; },
    study => { study.overview.statistics[0].context += ' New interpretation.'; },
    study => { study.relatedPublications = [{ publicationId: 'new-report', sourceRunId: 'new_run' }]; },
    study => { study.researchPriority.reassessment = { required: true, reason: 'New contrary evidence.', markedAt: '2026-10-26' }; },
  ]) { const next = fixture(); change(next.studies[0], next.researchPriorityRubric); const f = priorityFreshness(next.studies[0], next.researchPriorityRubric, index.reports); assert.equal(f.effectiveState, 'needs_review'); assert(f.staleReasons.length); assert.equal(next.studies[0].researchPriority.score, p.score); assert.equal(next.studies[0].researchPriority.reviewedAt, p.reviewedAt); }
});

test('four/five require explicit gate evidence; five additionally requires independent corroboration', () => {
  const c = fixture(), p = c.studies[0].researchPriority; p.score = 4;
  assert.throws(() => validateStudyCatalog(c, index.reports), /explicit/);
  p.highPriorityEvidence = Object.fromEntries(['executionAndCosts', 'separatedEvaluation', 'materialEffect'].map(k => [k, structuredClone(p.supporting[0])]));
  assert.doesNotThrow(() => validateStudyCatalog(c, index.reports)); p.score = 5;
  assert.throws(() => validateStudyCatalog(c, index.reports), /corroboration/);
  p.highPriorityEvidence.independentCorroboration = structuredClone(p.supporting[0]); assert.doesNotThrow(() => validateStudyCatalog(c, index.reports));
});

test('app-owned resolution verifies source sections/content and leaves historical scores available', async () => {
  const c = await readStudyCatalog(index.reports);
  assert(c.studies.every(s => s.resolvedResearchPriority));
  assert(c.studies.every(s => ['assessed', 'not_assessed', 'needs_review', 'not_applicable'].includes(s.resolvedResearchPriority.effectiveState)));
  assert(c.studies[0].resolvedResearchPriority.supporting[0].href.includes('#section-'));
  const temp = await mkdtemp(join(tmpdir(), 'priority-ref-'));
  try {
    const bad = fixture(); bad.studies[0].researchPriority.supporting[0].source.sectionId = 'not-a-saved-section';
    const file = join(temp, 'studies.json'); await writeFile(file, JSON.stringify(bad));
    await assert.rejects(readStudyCatalog(index.reports, file), /Missing priority evidence section/);
    const source = bad.studies[0].researchPriority.supporting[0].source;
    const publicationRoot = join(temp, 'publications'); await mkdir(join(publicationRoot, source.publicationId), { recursive: true });
    const bundle = JSON.parse(await readFile(`public/publications/${source.publicationId}/report.json`, 'utf8')); bundle.report.summary += ' Changed.';
    await writeFile(join(publicationRoot, source.publicationId, 'report.json'), JSON.stringify(bundle));
    const isolated = fixture(); isolated.studies = [isolated.studies[0]]; delete isolated.studies[0].overview; delete isolated.readingPaths;
    await writeFile(file, JSON.stringify(isolated));
    await assert.rejects(readStudyCatalog(index.reports, file, { publicationsRoot: publicationRoot }), /source hash/);
  } finally { await rm(temp, { recursive: true, force: true }); }
  const implementation = await readFile('scripts/lib/research-priorities.mjs', 'utf8');
  assert(!/strategies\/|child_process|execFile|spawn\(/.test(implementation));
});

test('scope hash ignores generated/resolved assessments while binding authored questions', () => {
  const s = fixture().studies[0], hash = priorityStudyHash(s);
  s.researchPriority.score = 2; s.resolvedResearchPriority = { effectiveState: 'needs_review' };
  assert.equal(priorityStudyHash(s), hash); s.summary += ' New scope'; assert.notEqual(priorityStudyHash(s), hash);
});

test('cross-language binding vector preserves typed numeric selectors and Unicode', () => {
  const vector = { studyId: '01_synthetic', title: 'É中文', overview: { statistics: [{ selection: { where: { value: .25, zero: -0, flag: false, large: 1e20 } } }] } };
  assert.equal(priorityStudyHash(vector), '0669a280766483b701394300a58d2aacdc6b39f33f594b655fbe7e86eb19fdf2');
});


test('operational callers retain exact identities from supplied verified bundles', async () => {
  const temp = await mkdtemp(join(tmpdir(), 'priority-operational-'));
  try {
    const c = fixture(); c.studies = [c.studies[0]]; delete c.studies[0].overview; delete c.readingPaths;
    const id = c.studies[0].featuredPublicationId;
    const bundle = JSON.parse(await readFile(`public/publications/${id}/report.json`, 'utf8'));
    const file = join(temp, 'studies.json'); await writeFile(file, JSON.stringify(c));
    const resolved = await readStudyCatalog([bundle.report], file, { bundles: [bundle] });
    assert(resolved.studies[0].resolvedResearchPriority);
    assert.equal(resolved.studies[0].resolvedResearchPriority.effectiveState, 'needs_review');
  } finally { await rm(temp, { recursive: true, force: true }); }
});
