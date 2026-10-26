import assert from 'node:assert/strict';
import test from 'node:test';
import { STUDY_DESTINATIONS, studyDestinationHref, studyPageRoutes, pageRoutes, pageRouteFile, legacyStudyAnchors } from '../scripts/lib/study-routes.mjs';
import { buildOutputConfig, validateStaticFiles } from '../scripts/lib/release.mjs';

const catalog = { studies: [{ slug: 'simple' }, { slug: 'long-study' }] };
const bundles = [{ report: { id: 'saved-primary' }, provenance: { assets: [] } }];

test('the shared inventory enumerates five static destinations in authored study order', () => {
  assert.deepEqual(STUDY_DESTINATIONS.map(destination => [destination.key, destination.label]), [
    ['overview', 'Overview'], ['findings', 'Findings'], ['explore', 'Explore'], ['methods', 'Method & scope'], ['evidence', 'Evidence'],
  ]);
  assert.deepEqual(studyPageRoutes(catalog), [
    '/studies/simple/', '/studies/simple/findings/', '/studies/simple/explore/', '/studies/simple/methods/', '/studies/simple/evidence/',
    '/studies/long-study/', '/studies/long-study/findings/', '/studies/long-study/explore/', '/studies/long-study/methods/', '/studies/long-study/evidence/',
  ]);
  assert.deepEqual(pageRoutes(catalog, bundles), ['/', ...studyPageRoutes(catalog), '/reports/saved-primary/']);
  assert.deepEqual(pageRoutes(catalog, [{ id: 'saved-primary' }]), pageRoutes(catalog, bundles));
  assert.equal(pageRouteFile('/'), 'index.html');
  assert.equal(pageRouteFile(studyDestinationHref('simple', 'evidence')), 'studies/simple/evidence/index.html');
  assert.deepEqual(studyPageRoutes(catalog, { legacyStudyRoutes: true }), ['/studies/simple/', '/studies/long-study/']);
});

test('route generation rejects private, malformed and unsupported destinations instead of inventing routes', () => {
  for (const slug of ['../private', '/Users/private', 'a/b', 'with space', 'UPPER', '', undefined]) assert.throws(() => studyDestinationHref(slug), /safe catalog slug/);
  assert.throws(() => studyDestinationHref('simple', 'search'), /Unknown study destination/);
  assert.throws(() => pageRoutes(catalog, [{ id: '../private' }]), /safe publication ID/);
});

test('release adapter admits exactly the new inventory while explicit legacy generation stays available', () => {
  const routes = pageRoutes(catalog, bundles);
  const files = [...routes.map(route => ({ path: pageRouteFile(route) })),
    ...['404.html', '404/index.html', '_not-found/index.html', 'publications/index.json', 'publications/saved-primary/report.json'].map(path => ({ path }))];
  assert.doesNotThrow(() => validateStaticFiles(files, catalog, bundles));
  assert.throws(() => validateStaticFiles(files.filter(file => file.path !== 'studies/simple/methods/index.html'), catalog, bundles), /Missing static page/);
  assert.throws(() => validateStaticFiles([...files, { path: 'studies/simple/search/index.html' }], catalog, bundles), /Unselected static output/);
  const config = buildOutputConfig(catalog, bundles);
  for (const route of routes) assert(config.routes.some(entry => entry.dest === `/${pageRouteFile(route)}`));
  assert.deepEqual(config.routes.slice(-2), [{ handle: 'filesystem' }, { src: '^/.*$', dest: '/404.html', status: 404 }]);
  assert.equal(buildOutputConfig(catalog, bundles, { legacyStudyRoutes: true }).routes.length, 6);
});

test('legacy fragment inventory preserves sections, headings, evidence, notes and used pattern keys without full report bodies', () => {
  const publication = { report: { id: 'saved-primary', sections: [{ id: 'summary', title: 'Saved summary', patternId: 'used' }],
    downloads: [{ id: 'csv', label: 'Selected CSV' }], references: [{ id: 'source', label: 'Source review' }],
    notes: ['Saved qualification'], patterns: [{ id: 'used', title: 'Used schematic' }, { id: 'unused', title: 'Not rendered' }] } };
  const anchors = legacyStudyAnchors(publication);
  assert.deepEqual(anchors.map(anchor => anchor.id), ['section-summary', 'heading-summary', 'publication-downloads', 'download-csv', 'publication-references', 'reference-source', 'publication-notes', 'pattern-key-used']);
  assert.equal(anchors.find(anchor => anchor.id === 'heading-summary').href, '/reports/saved-primary/#section-summary');
  assert(anchors.every(anchor => anchor.href.startsWith('/reports/saved-primary/#')));
  assert.equal(new Set(anchors.map(anchor => anchor.id)).size, anchors.length);
  assert(!JSON.stringify(anchors).includes('Saved qualification'));
});
