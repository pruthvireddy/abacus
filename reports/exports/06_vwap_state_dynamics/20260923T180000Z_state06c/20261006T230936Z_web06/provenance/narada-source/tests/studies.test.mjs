import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, writeFile, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { validateStudyCatalog, readStudyCatalog, studyHref, studyParams, findStudy, findPublicationStudy, STUDY_CATALOG_MAX_BYTES } from '../scripts/lib/studies.mjs';

const reports = [
  { id: 'primary', source: { producer: 'sahadeva', runId: 'run_a' } },
  { id: 'revision', source: { producer: 'sahadeva', runId: 'run_a' } },
  { id: 'supplement', source: { producer: 'sahadeva', runId: 'run_b' } },
];
const fixture = () => ({ schemaVersion: '1.0', studies: [{
  studyId: '01_test', slug: 'test-study', title: 'Temporary test', summary: 'Saved evidence.',
  topic: 'Testing', products: ['NQ'], evidenceStatus: 'Exploratory.',
  featuredPublicationId: 'primary', featuredSourceRunId: 'run_a',
  relatedPublications: [
    { publicationId: 'revision', sourceRunId: 'run_a', relationship: 'presentation-revision', label: 'Earlier presentation of the same evidence' },
    { publicationId: 'supplement', sourceRunId: 'run_b', relationship: 'exploratory-supplement', label: 'Exploratory later observations' },
  ],
}] });
test('explicit catalog supports routes, lookup and distinct source relationships', () => {
  const catalog = validateStudyCatalog(fixture(), reports);
  assert.equal(studyHref(catalog.studies[0].slug), '/studies/test-study/');
  assert.deepEqual(studyParams(catalog), [{ slug: 'test-study' }]);
  assert.equal(findStudy(catalog, 'test-study').featuredPublicationId, 'primary');
  assert.equal(findStudy(catalog, 'missing'), null);
  assert.equal(findStudy(catalog, '../primary'), null);
  const other = fixture(); other.studies[0].relatedPublications[1].relationship = 'other-run';
  validateStudyCatalog(other, reports);
});
test('duplicate identities, slugs and publication ownership fail', () => {
  for (const alter of [
    s => { s.slug = 'second'; },
    s => { s.studyId = '02_test'; },
    s => { s.studyId = '02_test'; s.slug = 'second'; },
  ]) {
    const catalog = fixture(), second = structuredClone(catalog.studies[0]); alter(second);
    catalog.studies.push(second); assert.throws(() => validateStudyCatalog(catalog, reports), /unique|only one study/);
  }
});
test('missing, repeated or wrongly attributed publication references fail', () => {
  for (const alter of [
    s => { s.featuredPublicationId = 'absent'; },
    s => { s.relatedPublications[0].publicationId = 'absent'; },
    s => { s.relatedPublications[0].publicationId = 'primary'; },
    s => { s.relatedPublications.push(s.relatedPublications[0]); },
    s => { s.featuredSourceRunId = 'wrong_run'; },
    s => { s.relatedPublications[0].sourceRunId = 'wrong_run'; },
  ]) {
    const catalog = fixture(); alter(catalog.studies[0]);
    assert.throws(() => validateStudyCatalog(catalog, reports), /Missing publication|repeat|attribution/);
  }
});
test('relationship labels must agree with source-run identity and allowed kinds', () => {
  for (const [index, relationship] of [[0, 'other-run'], [0, 'exploratory-supplement'], [1, 'presentation-revision'], [1, 'latest']]) {
    const catalog = fixture(); catalog.studies[0].relatedPublications[index].relationship = relationship;
    assert.throws(() => validateStudyCatalog(catalog, reports), /Relationship|schema/);
  }
});
test('bounded authored fields reject paths, unsafe slugs and unexpected containers', () => {
  for (const alter of [
    s => { s.slug = '../test'; }, s => { s.featuredSourceRunId = '/runs/run'; },
    s => { s.summary = 'See file:///private/report'; }, s => { s.title = ' '; },
    s => { s.evidenceStatus = 'x'.repeat(801); }, s => { s.products = ['NQ', 'NQ']; },
    s => { s.privateFiles = []; }, s => { s.title = 'bad\u0000text'; },
  ]) {
    const catalog = fixture(); alter(catalog.studies[0]); assert.throws(() => validateStudyCatalog(catalog, reports));
  }
});
test('catalog loader rejects oversized input and symlinks without workspace access', async t => {
  const root = await mkdtemp(join(tmpdir(), 'narada-catalog-')); t.after(() => rm(root, { recursive: true, force: true }));
  const file = join(root, 'studies.json'); await writeFile(file, JSON.stringify(fixture()));
  assert.deepEqual(await readStudyCatalog(reports, file), fixture());
  const link = join(root, 'link.json'); await symlink(file, link);
  await assert.rejects(readStudyCatalog(reports, link), /regular file/);
  await writeFile(file, ' '.repeat(STUDY_CATALOG_MAX_BYTES + 1));
  await assert.rejects(readStudyCatalog(reports, file), /budget/);
});

test('identity and product fields reject trailing whitespace and control characters', () => {
  for (const alter of [
    s => { s.slug += '\n'; }, s => { s.studyId += '\n'; },
    s => { s.featuredPublicationId += '\n'; }, s => { s.featuredSourceRunId += '\n'; },
    s => { s.relatedPublications[0].sourceRunId += '\n'; },
    s => { s.products = ['NQ ']; },
  ]) {
    const catalog = fixture(); alter(catalog.studies[0]);
    assert.throws(() => validateStudyCatalog(catalog, reports));
  }
});

test('publication context separates featured content, related revision labels and missing IDs', () => {
  const catalog = validateStudyCatalog(fixture(), reports);
  assert.equal(findPublicationStudy(catalog, 'primary').relation, null);
  assert.equal(findPublicationStudy(catalog, 'revision').relation.relationship, 'presentation-revision');
  assert.equal(findPublicationStudy(catalog, 'revision').study.slug, 'test-study');
  assert.equal(findPublicationStudy(catalog, 'missing'), null);
});
