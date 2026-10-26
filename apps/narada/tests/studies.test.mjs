import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, writeFile, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { validateStudyCatalog, readStudyCatalog, studyHref, studyParams, findStudy, findPublicationStudy, publicationGroups, studyPublicationReferences, familyPublicationSelection, STUDY_CATALOG_MAX_BYTES } from '../scripts/lib/studies.mjs';

const reports = [
  { id: 'primary', source: { producer: 'sahadeva', runId: 'run_a' } },
  { id: 'revision', source: { producer: 'sahadeva', runId: 'run_a' } },
  { id: 'supplement', source: { producer: 'sahadeva', runId: 'run_b' } },
  { id: 'additional', source: { producer: 'sahadeva', runId: 'run_b' } },
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

const tabFixture = () => {
  const catalog = fixture();
  delete catalog.studies[0].relatedPublications;
  catalog.studies[0].publicationTabs = [
    { publicationId: 'primary', sourceRunId: 'run_a', label: 'Chart A' },
    { publicationId: 'revision', sourceRunId: 'run_a', label: 'Chart B' },
  ];
  return catalog;
};

test('authored publication tabs preserve the default report and sibling study context', () => {
  const catalog = validateStudyCatalog(tabFixture(), reports);
  const primary = findPublicationStudy(catalog, 'primary');
  assert.equal(primary.tab.label, 'Chart A');
  assert.equal(primary.relation, null);
  const sibling = findPublicationStudy(catalog, 'revision');
  assert.equal(sibling.study.slug, 'test-study');
  assert.equal(sibling.tab.label, 'Chart B');
  assert.equal(sibling.relation, null);
});

test('publication tabs reject missing, repeated, private and wrongly attributed selections', () => {
  for (const alter of [
    s => { s.publicationTabs.reverse(); },
    s => { s.publicationTabs[1].publicationId = 'primary'; },
    s => { s.publicationTabs[1].label = 'Chart A'; },
    s => { s.publicationTabs[1].sourceRunId = 'run_b'; },
    s => { s.publicationTabs[1].publicationId = 'absent'; },
    s => { s.publicationTabs[1].publicationId = 'supplement'; },
    s => { s.publicationTabs[1].label = 'See /Users/private'; },
    s => { s.publicationTabs[1].label = '  Chart B'; },
    s => { s.publicationTabs[1].relationship = 'other-run'; },
    s => { s.publicationTabs.pop(); },
    s => { s.relatedPublications = [{ publicationId: 'revision', sourceRunId: 'run_a', relationship: 'presentation-revision', label: 'Repeated' }]; },
  ]) {
    const catalog = tabFixture();
    alter(catalog.studies[0]);
    assert.throws(() => validateStudyCatalog(catalog, reports));
  }
  const catalog = tabFixture();
  const second = fixture().studies[0];
  Object.assign(second, { studyId: '02_test', slug: 'second', featuredPublicationId: 'revision' });
  delete second.relatedPublications;
  catalog.studies.push(second);
  assert.throws(() => validateStudyCatalog(catalog, reports), /only one study/);
});

const analysisFixture = () => {
  const catalog = tabFixture();
  const study = catalog.studies[0];
  study.analyses = [{ id: 'first', label: 'First analysis', publicationTabs: study.publicationTabs },
    { id: 'second', label: 'Second analysis', publicationTabs: [{ publicationId: 'supplement', sourceRunId: 'run_b', label: 'Chart A' }, { publicationId: 'additional', sourceRunId: 'run_b', label: 'Chart B' }] }];
  delete study.publicationTabs;
  return catalog;
};
test('analysis groups own distinct runs while retaining explicit chart labels and featured attribution', () => {
  const catalog = validateStudyCatalog(analysisFixture(), reports);
  const context = findPublicationStudy(catalog, 'additional');
  assert.equal(context.analysis.id, 'second');
  assert.equal(context.tab.label, 'Chart B');
  assert.equal(context.relation, null);
  assert.equal(publicationGroups(catalog.studies[0]).length, 2);
  assert.deepEqual(studyPublicationReferences(catalog.studies[0]).map(reference => reference.publicationId), ['primary', 'revision', 'supplement', 'additional']);
});
test('a single saved baseline remains an analysis beside a later run without a fabricated sibling report', () => {
  const catalog = analysisFixture();
  const study = catalog.studies[0];
  study.analyses[0].publicationTabs = [study.analyses[0].publicationTabs[0]];
  study.analyses.reverse();
  study.featuredPublicationId = 'supplement';
  study.featuredSourceRunId = 'run_b';
  validateStudyCatalog(catalog, reports);
  const baseline = findPublicationStudy(catalog, 'primary');
  assert.equal(baseline.analysis.id, 'first');
  assert.equal(baseline.tab.sourceRunId, 'run_a');
  assert.deepEqual(publicationGroups(study).map(group => group.length), [2, 1]);
  assert.deepEqual(studyPublicationReferences(study).map(reference => reference.publicationId), ['supplement', 'additional', 'primary']);
  study.analyses[1].publicationTabs = [];
  assert.throws(() => validateStudyCatalog(catalog, reports), /schema/);
});
test('analysis groups reject duplicate ownership, mismatched defaults, unsafe labels and mixed source runs', () => {
  for (const alter of [
    s => { s.analyses[1].id = 'first'; }, s => { s.analyses[1].label = 'First analysis'; },
    s => { s.analyses[0].publicationTabs.reverse(); }, s => { s.analyses[1].publicationTabs[1].publicationId = 'primary'; s.analyses[1].publicationTabs[1].sourceRunId = 'run_a'; },
    s => { s.analyses[1].publicationTabs[1].sourceRunId = 'run_a'; }, s => { s.analyses[1].publicationTabs[1].label = 'Chart A'; },
    s => { s.analyses[1].label = '/Users/private'; }, s => { s.analyses[1].publicationTabs[1].publicationId = 'missing'; },
    s => { s.publicationTabs = s.analyses[0].publicationTabs; }, s => { s.analyses.pop(); },
    s => { s.relatedPublications = [{ publicationId: 'additional', sourceRunId: 'run_b', relationship: 'other-run', label: 'Repeated' }]; },
  ]) {
    const catalog = analysisFixture(); alter(catalog.studies[0]);
    assert.throws(() => validateStudyCatalog(catalog, reports));
  }
});

const familyFixture = () => {
  const catalog = analysisFixture();
  const study = catalog.studies[0];
  study.phaseFamilies = study.analyses.map((analysis, index) => ({
    id: `phase-${index}`, label: `Phase ${index}`, analyses: [analysis],
  }));
  delete study.analyses;
  return catalog;
};
test('bounded phase families retain all explicit reports, per-analysis runs and legacy lookup', () => {
  const catalog = validateStudyCatalog(familyFixture(), reports);
  const study = catalog.studies[0];
  const later = findPublicationStudy(catalog, 'additional');
  assert.equal(later.family.id, 'phase-1');
  assert.equal(later.analysis.id, 'second');
  assert.equal(later.tab.sourceRunId, 'run_b');
  assert.equal(later.tab.label, 'Chart B');
  assert.equal(later.relation, null);
  assert.deepEqual(publicationGroups(study).map(group => group.length), [2, 2]);
  assert.deepEqual(studyPublicationReferences(study).map(reference => reference.publicationId), ['primary', 'revision', 'supplement', 'additional']);
  assert.equal(findPublicationStudy(validateStudyCatalog(analysisFixture(), reports), 'primary').family, null);
});
test('phase analysis IDs are scoped while publication ownership stays unique across the entire study', () => {
  const catalog = familyFixture();
  const families = catalog.studies[0].phaseFamilies;
  families[1].analyses[0].id = families[0].analyses[0].id;
  families[1].analyses[0].label = families[0].analyses[0].label;
  validateStudyCatalog(catalog, reports);
  assert.equal(findPublicationStudy(catalog, 'additional').family.id, 'phase-1');
  assert.equal(familyPublicationSelection(families[1], 'first', 'Chart B').tab.publicationId, 'additional');
  assert.equal(familyPublicationSelection(families[1], 'absent', 'absent').tab.publicationId, 'supplement');
  families[1].analyses[0].publicationTabs = [{ ...families[0].analyses[0].publicationTabs[0] }];
  assert.throws(() => validateStudyCatalog(catalog, reports), /repeat/);
});
test('eight retained groups and seven new conditions fit without raising the legacy eight-group cap', () => {
  const catalog = fixture(), study = catalog.studies[0];
  delete study.relatedPublications;
  const syntheticReports = [];
  study.phaseFamilies = [8, 7].map((count, phase) => ({
    id: `phase-${phase}`, label: `Phase ${phase}`, analyses: Array.from({ length: count }, (_, index) => {
      const id = `p${phase}-a${index}`;
      const runId = phase === 0 && index === 1 ? 'saved_earlier_parent' : `run_${phase}`;
      syntheticReports.push({ id, source: { producer: 'sahadeva', runId } });
      return { id: `condition-${index}`, label: `Condition ${index}`, publicationTabs: [{ publicationId: id, sourceRunId: runId, label: 'Summary' }] };
    }),
  }));
  study.featuredPublicationId = 'p0-a0'; study.featuredSourceRunId = 'run_0';
  validateStudyCatalog(catalog, syntheticReports);
  assert.equal(publicationGroups(study).length, 15);
  assert.equal(studyPublicationReferences(study).length, 15);
  assert.equal(findPublicationStudy(catalog, 'p0-a1').tab.sourceRunId, 'saved_earlier_parent');
  const legacy = structuredClone(study); legacy.analyses = legacy.phaseFamilies[0].analyses;
  delete legacy.phaseFamilies; legacy.analyses.push(legacy.analyses[0]);
  assert.throws(() => validateStudyCatalog({ schemaVersion: '1.0', studies: [legacy] }, syntheticReports), /schema/);
});
test('phase families reject ambiguous, oversized, unsafe and wrongly attributed selections', () => {
  for (const alter of [
    s => { s.analyses = s.phaseFamilies[0].analyses; },
    s => { s.publicationTabs = s.phaseFamilies[0].analyses[0].publicationTabs; },
    s => { s.phaseFamilies.pop(); },
    s => { s.phaseFamilies = Array(5).fill(s.phaseFamilies[0]); },
    s => { s.phaseFamilies[0].analyses = []; },
    s => { s.phaseFamilies[0].analyses = Array(9).fill(s.phaseFamilies[0].analyses[0]); },
    s => { s.phaseFamilies[0].analyses[0].publicationTabs = Array(13).fill(s.phaseFamilies[0].analyses[0].publicationTabs[0]); },
    s => { s.phaseFamilies[1].id = s.phaseFamilies[0].id; },
    s => { s.phaseFamilies[1].label = s.phaseFamilies[0].label; },
    s => { s.phaseFamilies[1].label = '/Users/private'; },
    s => { s.phaseFamilies[1].label = 'Hidden\u0000phase'; },
    s => { s.phaseFamilies[1].label = ' '; },
    s => { s.phaseFamilies[0].analyses.push(s.phaseFamilies[0].analyses[0]); },
    s => { s.phaseFamilies.reverse(); },
    s => { s.phaseFamilies[1].analyses[0].publicationTabs[1].sourceRunId = 'run_a'; },
    s => { s.phaseFamilies[1].analyses[0].publicationTabs[1].publicationId = 'missing'; },
    s => { s.phaseFamilies[1].analyses[0].publicationTabs[1].label = 'Chart A'; },
  ]) {
    const catalog = familyFixture(); alter(catalog.studies[0]);
    assert.throws(() => validateStudyCatalog(catalog, reports));
  }
});
