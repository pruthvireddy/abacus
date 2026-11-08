import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { validateStudyCatalog, readStudyCatalog, STUDY_CATALOG_MAX_BYTES } from '../scripts/lib/studies.mjs';
import { STUDY_DESTINATIONS, studyDestinationHref } from '../scripts/lib/study-routes.mjs';

const study = (id, publicationId) => ({ studyId: id, slug: publicationId, title: `Saved ${id}`, summary: 'An explicitly selected saved study.', topic: 'Synthetic evidence', products: ['NQ'], evidenceStatus: 'Synthetic temporary metadata; no research result.', featuredPublicationId: publicationId, featuredSourceRunId: `${id}_run` });
const catalogFixture = () => ({ schemaVersion: '1.0', studies: [study('first_study', 'first-publication'), study('second_study', 'second-publication')] });
const reportsFixture = () => catalogFixture().studies.map(item => ({ id: item.featuredPublicationId, source: { producer: 'sahadeva', runId: item.featuredSourceRunId } }));
const pathFixture = () => ({ id: 'first-questions', title: 'A route through two questions', description: 'Read the saved questions in an editorial order.', qualification: 'Separate source populations retain their own limitations.', steps: [
  { studyId: 'first_study', destination: 'overview', reason: 'Begin with the first saved question and its limitations.' },
  { studyId: 'second_study', destination: 'findings', reason: 'Read a different saved question without pooling results.' },
] });
const withPaths = () => ({ ...catalogFixture(), readingPaths: [pathFixture()] });

test('reading paths extend the same optional catalog without changing identities, selections or order', () => {
  const plain = catalogFixture();
  assert.equal(validateStudyCatalog(plain, reportsFixture()), plain);
  const catalog = withPaths();
  const originalStudies = structuredClone(catalog.studies);
  const originalSteps = structuredClone(catalog.readingPaths[0].steps);
  assert.equal(validateStudyCatalog(catalog, reportsFixture()), catalog);
  assert.deepEqual(catalog.studies, originalStudies);
  assert.deepEqual(catalog.readingPaths[0].steps, originalSteps);
});

test('missing studies, repeated steps, duplicate paths and invalid destinations fail closed', () => {
  for (const alter of [
    catalog => { catalog.readingPaths[0].steps[1].studyId = 'missing_study'; },
    catalog => { catalog.readingPaths[0].steps[1].studyId = 'first_study'; },
    catalog => { catalog.readingPaths.push(structuredClone(catalog.readingPaths[0])); },
    catalog => { catalog.readingPaths.push({ ...pathFixture(), id: 'different-id' }); },
    catalog => { catalog.readingPaths[0].steps[0].destination = 'not-a-route'; },
    catalog => { catalog.readingPaths[0].steps[0].href = '/reports/unselected/'; },
    catalog => { catalog.readingPaths[0].steps[0].studyId = '../private'; },
  ]) {
    const catalog = withPaths(); alter(catalog);
    assert.throws(() => validateStudyCatalog(catalog, reportsFixture()));
  }
});

test('bounded reading-path text rejects missing qualifications, private locators and control characters', () => {
  for (const alter of [
    path => { delete path.qualification; },
    path => { path.qualification = ' '; },
    path => { path.title = ' Untrimmed'; },
    path => { path.id = 'Unsafe Path'; },
    path => { path.description = 'Read /Users/private/research'; },
    path => { path.steps[0].reason = 'Read reports/exports/private'; },
    path => { path.steps[0].reason = 'Hidden\u0000control'; },
    path => { path.steps[0].reason = 'x'.repeat(401); },
    path => { path.steps.pop(); },
    path => { path.steps = Array(7).fill(path.steps[0]); },
    path => { path.score = 99; },
  ]) {
    const catalog = withPaths(); alter(catalog.readingPaths[0]);
    assert.throws(() => validateStudyCatalog(catalog, reportsFixture()));
  }
  const tooMany = withPaths();
  tooMany.readingPaths = Array.from({ length: 7 }, (_, index) => ({ ...pathFixture(), id: `path-${index}`, title: `Path ${index}` }));
  assert.throws(() => validateStudyCatalog(tooMany, reportsFixture()));
});

test('optional authored keywords are bounded plain text with case-insensitive uniqueness', () => {
  const catalog = catalogFixture();
  catalog.studies[0].keywords = ['VWAP', 'session context'];
  assert.doesNotThrow(() => validateStudyCatalog(catalog, reportsFixture()));
  for (const keywords of [[], ['VWAP', 'vwap'], [' duplicated', 'safe'], ['file:///private'], ['bad\u0000value'], ['x'.repeat(61)], Array.from({ length: 9 }, (_, index) => `word ${index}`)]) {
    const invalid = catalogFixture(); invalid.studies[0].keywords = keywords;
    assert.throws(() => validateStudyCatalog(invalid, reportsFixture()));
  }
});

test('the authored reading paths resolve to real static study destinations within the catalog budget', async () => {
  const bytes = await readFile('content/studies.json');
  assert(bytes.length <= STUDY_CATALOG_MAX_BYTES);
  const index = JSON.parse(await readFile('public/publications/index.json', 'utf8'));
  const catalog = await readStudyCatalog(index.reports);
  assert.equal(catalog.readingPaths.length, 3);
  const studies = new Map(catalog.studies.map(item => [item.studyId, item]));
  for (const path of catalog.readingPaths) {
    assert(path.qualification.length > 0);
    for (const step of path.steps) {
      const selectedStudy = studies.get(step.studyId);
      assert(selectedStudy);
      assert.equal(studyDestinationHref(selectedStudy.slug, step.destination), `/studies/${selectedStudy.slug}/${step.destination === 'overview' ? '' : `${step.destination}/`}`);
    }
  }
  const schema = JSON.parse(await readFile('contracts/studies.schema.json', 'utf8'));
  assert.deepEqual(schema.$defs.readingPath.properties.steps.items.properties.destination.enum, STUDY_DESTINATIONS.map(item => item.key));
});
