import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, readFile, writeFile, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { publishReport } from '../scripts/lib/publication.mjs';
import { readStudyCatalog, validateStudyCatalog } from '../scripts/lib/studies.mjs';
import { overviewHref, resolveStudyOverview, resolveCatalogOverviews } from '../scripts/lib/study-overviews.mjs';

const source = sectionId => ({ publicationId: 'saved-primary', sourceRunId: 'saved_run', sourceSha256: 'a'.repeat(64), sectionId });
const claim = text => ({ text, source: source('context') });
const metric = () => ({ label: 'Saved zero rate', context: 'Separate population and fixed horizon.', source: source('metrics'), selection: { kind: 'metric', label: 'Zero rate' } });
const cell = (kind = 'null') => ({ label: 'Selected saved cell', context: 'No pooling across rows.', source: source('table'), selection: { kind: 'table-cell', columnKey: 'value', where: { kind, enabled: false } } });
const reportFixture = () => ({ schemaVersion: '1.1', id: 'saved-primary', title: 'Synthetic saved report', summary: 'A temporary test report.', publishedAt: '2026-01-01T00:00:00Z', source: { producer: 'sahadeva', runId: 'saved_run' }, sections: [
  { id: 'context', kind: 'text', title: 'Scope', body: 'A saved qualitative review, not performance evidence.' },
  { id: 'metrics', kind: 'metrics', title: 'Saved metrics', items: [
    { label: 'Zero rate', value: 0, format: 'percent', precision: 0, unit: 'eligible events', note: 'Saved denominator applies.' },
    { label: 'Unavailable', value: null, format: 'number', precision: 2 },
  ] },
  { id: 'table', kind: 'table', title: 'Separate saved rows', description: 'A separate cohort per row.', notes: ['Fixed source horizon.'], columns: [
    { key: 'kind', label: 'Population' }, { key: 'enabled', label: 'Enabled' },
    { key: 'value', label: 'Saved amount', format: 'number', precision: 3, unit: 'points' },
  ], rows: [{ kind: 'null', enabled: false, value: null }, { kind: 'zero', enabled: false, value: 0 }, { kind: 'other', enabled: true, value: 5 }] },
] });
const bundleFixture = () => ({ report: reportFixture(), provenance: { sourceSha256: 'a'.repeat(64), assets: [] } });
const catalogFixture = () => ({ schemaVersion: '1.0', studies: [{
  studyId: '01_fixture', slug: 'synthetic-study', title: 'Synthetic study', summary: 'Explicit selected evidence.', topic: 'Tests', products: ['NQ'], evidenceStatus: 'Synthetic fixture only.', featuredPublicationId: 'saved-primary', featuredSourceRunId: 'saved_run',
  overview: { question: 'What does the saved review cover?', takeaway: 'A scope-limited saved conclusion.', evidenceType: 'Descriptive saved evidence', population: 'Separate saved populations.', qualification: 'No execution claim.', method: 'Read the explicitly selected saved sections.', source: source('context'), statistics: [metric(), cell()], findings: [claim('A saved finding.')], limitations: [claim('A saved limitation.')], links: [{ label: 'Read scope', source: source('context') }] },
}] });
const reportsFixture = () => [{ ...reportFixture(), sourceSha256: 'a'.repeat(64) }];

test('optional bounded overview metadata preserves existing studies and rejects malformed fields', () => {
  const plain = catalogFixture(); delete plain.studies[0].overview;
  assert.equal(validateStudyCatalog(plain, reportsFixture()), plain);
  assert.doesNotThrow(() => validateStudyCatalog(catalogFixture(), reportsFixture()));
  for (const alter of [
    overview => { delete overview.question; }, overview => { overview.question = ' '; },
    overview => { overview.takeaway = 'x'.repeat(801); }, overview => { overview.statistics.pop(); },
    overview => { overview.statistics = Array(5).fill(metric()); }, overview => { overview.findings = []; },
    overview => { overview.limitations[0].text = 'See /Users/private/evidence'; },
    overview => { overview.method = 'Hidden\u0000control'; }, overview => { overview.grade = 10; },
    overview => { overview.source.sourceSha256 = 'not-a-hash'; },
    overview => { overview.statistics[0].text = 'Unselected override'; },
    overview => { overview.statistics[1].selection.where = {}; },
  ]) {
    const catalog = catalogFixture(); alter(catalog.studies[0].overview);
    assert.throws(() => validateStudyCatalog(catalog, reportsFixture()));
  }
});

test('overview sources must belong to the authored study and pin the saved run and content identity', () => {
  for (const [key, value] of [['publicationId', 'unselected'], ['sourceRunId', 'different_run'], ['sourceSha256', 'b'.repeat(64)]]) {
    const catalog = catalogFixture(); catalog.studies[0].overview.source[key] = value;
    assert.throws(() => validateStudyCatalog(catalog, reportsFixture()), /selected publication|attribution|identity/);
  }
});

test('exact metrics and table cells retain null, zero, precision, units and source attribution without mutation', () => {
  const catalog = validateStudyCatalog(catalogFixture(), reportsFixture());
  const study = catalog.studies[0], bundle = bundleFixture();
  const before = JSON.stringify({ study, bundle });
  const overview = resolveStudyOverview(study, [bundle]);
  assert.equal(overview.statistics[0].value, 0);
  assert.equal(overview.statistics[0].format, 'percent');
  assert.equal(overview.statistics[0].precision, 0);
  assert.equal(overview.statistics[0].unit, 'eligible events');
  assert.equal(overview.statistics[0].note, 'Saved denominator applies.');
  assert.equal(overview.statistics[1].value, null);
  assert.equal(overview.statistics[1].unit, 'points');
  assert.equal(overview.statistics[1].precision, 3);
  assert.equal(overview.statistics[1].description, 'A separate cohort per row.');
  assert.deepEqual(overview.statistics[1].notes, ['Fixed source horizon.']);
  assert.equal(overview.statistics[1].href, '/reports/saved-primary/#section-table');
  assert.deepEqual(overview.statistics[1].source, source('table'));
  assert.equal(overview.findings[0].href, overviewHref(source('context')));
  assert.equal(overview.methodHref, overview.href);
  assert.equal(JSON.stringify({ study, bundle }), before);
  study.overview.statistics[1] = cell('zero');
  assert.equal(resolveStudyOverview(study, [bundle]).statistics[1].value, 0);
  study.overview.statistics[0].selection.label = 'Unavailable';
  assert.equal(resolveStudyOverview(study, [bundle]).statistics[0].value, null);
  study.overview.statistics[1].selection.columnKey = 'enabled';
  assert.equal(resolveStudyOverview(study, [bundle]).statistics[1].value, false);
});

test('an optional method source resolves its own pinned section and rejects missing or stale sources', () => {
  const catalog = catalogFixture(), study = catalog.studies[0];
  study.overview.methodSource = source('table');
  validateStudyCatalog(catalog, reportsFixture());
  assert.equal(resolveStudyOverview(study, [bundleFixture()]).methodHref, '/reports/saved-primary/#section-table');
  study.overview.methodSource.sourceSha256 = 'b'.repeat(64);
  assert.throws(() => validateStudyCatalog(catalog, reportsFixture()), /identity/);
  study.overview.methodSource = source('missing');
  assert.throws(() => resolveStudyOverview(study, [bundleFixture()]), /source section/);
});

test('missing and ambiguous report, section, metric, row and column selectors fail instead of guessing', () => {
  for (const alter of [
    (study, bundles) => { bundles.pop(); },
    (study, bundles) => { bundles.push(bundles[0]); },
    study => { study.overview.source.sectionId = 'missing'; },
    (study, bundles) => { bundles[0].report.sections.push(bundles[0].report.sections[0]); },
    study => { study.overview.statistics[0].selection.label = 'Missing'; },
    (study, bundles) => { bundles[0].report.sections[1].items.push(bundles[0].report.sections[1].items[0]); },
    study => { study.overview.statistics[1].selection.where.kind = 'absent'; },
    (study, bundles) => { bundles[0].report.sections[2].rows.push(bundles[0].report.sections[2].rows[0]); },
    study => { study.overview.statistics[1].selection.columnKey = 'absent'; },
    study => { study.overview.statistics[1].selection.where.unknown = null; },
    (study, bundles) => { delete bundles[0].report.sections[2].rows[0].value; },
    (study, bundles) => { delete bundles[0].report.sections[2].rows[0].enabled; },
    study => { study.overview.statistics[0].source.sectionId = 'table'; },
    study => { study.overview.statistics[1].source.sectionId = 'metrics'; },
  ]) {
    const study = catalogFixture().studies[0], bundles = [bundleFixture()]; alter(study, bundles);
    assert.throws(() => resolveStudyOverview(study, bundles), /selected publication|uniquely|missing|unknown|requires/);
  }
});

test('qualitative overviews resolve supported scope facts without manufacturing performance values', () => {
  const study = catalogFixture().studies[0];
  study.overview.evidenceType = 'Qualitative source review';
  study.overview.statistics = ['Session context', 'Source themes'].map(label => ({ label, context: 'Reviewed source scope only.', text: 'Qualitative review', source: source('context') }));
  validateStudyCatalog({ schemaVersion: '1.0', studies: [study] }, reportsFixture());
  const overview = resolveStudyOverview(study, [bundleFixture()]);
  assert(overview.statistics.every(item => item.text === 'Qualitative review' && !Object.hasOwn(item, 'value')));
  assert(overview.statistics.every(item => item.href.endsWith('#section-context')));
});

test('catalog loader resolves exact staged content at build time and rejects changed bytes and linked bundles', async t => {
  const root = await mkdtemp(join(tmpdir(), 'narada-overview-')); t.after(() => rm(root, { recursive: true, force: true }));
  const report = reportFixture(), reportPath = join(root, 'source.json'), publicationsRoot = join(root, 'publications');
  await writeFile(reportPath, JSON.stringify(report));
  await publishReport({ reportPath, outputRoot: publicationsRoot });
  const bundlePath = join(publicationsRoot, report.id, 'report.json');
  const original = await readFile(bundlePath, 'utf8'), bundle = JSON.parse(original);
  const catalog = catalogFixture(), study = catalog.studies[0];
  const sources = [study.overview.source, ...study.overview.statistics.map(item => item.source), ...study.overview.findings.map(item => item.source), ...study.overview.limitations.map(item => item.source), ...study.overview.links.map(item => item.source)];
  for (const pinned of sources) pinned.sourceSha256 = bundle.provenance.sourceSha256;
  const file = join(root, 'studies.json'); await writeFile(file, JSON.stringify(catalog));
  const reports = [{ ...report, sourceSha256: bundle.provenance.sourceSha256 }];
  assert.equal((await readStudyCatalog(reports, file, { publicationsRoot })).studies[0].resolvedOverview.statistics[0].value, 0);
  assert.equal((await resolveCatalogOverviews(catalog, { bundles: [bundle] })).studies[0].resolvedOverview.statistics[1].value, null);
  bundle.report.sections[1].items[0].value = 1;
  await writeFile(bundlePath, JSON.stringify(bundle));
  await assert.rejects(readStudyCatalog(reports, file, { publicationsRoot }), /source hash/);
  await rm(bundlePath); await writeFile(join(root, 'linked.json'), original); await symlink(join(root, 'linked.json'), bundlePath);
  await assert.rejects(readStudyCatalog(reports, file, { publicationsRoot }), /regular staged bundle/);
});
