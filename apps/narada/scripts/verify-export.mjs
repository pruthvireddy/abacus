import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { readPublicationIndex, verifyPublications } from './lib/publication.mjs';
import { readStudyCatalog, studyHref, publicationGroups, studyPublicationReferences, findPublicationStudy, familyPublicationSelection } from './lib/studies.mjs';
import { assertPagePayloadSize } from './lib/static-page-budget.mjs';
import { verifyStaticPublicationJson } from './lib/static-json-delivery.mjs';

const root = resolve(import.meta.dirname, '../out');
const publicRoot = join(root, 'publications');
const { bundles } = await verifyPublications(publicRoot);
const delivery = await verifyStaticPublicationJson({
  canonicalRoot: resolve(import.meta.dirname, '../public/publications'),
  exportRoot: publicRoot,
});
const index = await readPublicationIndex(publicRoot);
const catalog = await readStudyCatalog(index.reports);
await stat(join(root, 'index.html'));
await stat(join(root, '404.html'));
const homepage = await readFile(join(root, 'index.html'), 'utf8');
for (const study of catalog.studies) {
  assert(homepage.includes(`href="${studyHref(study.slug)}"`), `Study not linked from library: ${study.studyId}`);
  const file = join(root, 'studies', study.slug, 'index.html');
  assert((await stat(file)).isFile(), `Missing study page for ${study.studyId}`);
  const html = await readFile(file, 'utf8');
  const selectedIds = new Set(studyPublicationReferences(study).map(p => p.publicationId));
  for (const id of selectedIds) {
    assert(html.includes(`href="/reports/${id}/"`), `Study page missing selected publication ${id}`);
    assert((await stat(join(root, 'reports', id, 'index.html'))).isFile(), `Missing selected publication page ${id}`);
  }
  for (const group of publicationGroups(study)) {
    for (const tab of group) {
      const reportHtml = await readFile(join(root, 'reports', tab.publicationId, 'index.html'), 'utf8');
      assert(reportHtml.includes('aria-label="Study chart navigation"'), `Missing publication navigation for ${tab.publicationId}`);
      assert(reportHtml.includes(`href="/reports/${tab.publicationId}/" aria-current="page"`), `Missing current tab for ${tab.publicationId}`);
      for (const sibling of group) {
        assert(reportHtml.includes(`href="/reports/${sibling.publicationId}/"`), `Missing sibling tab ${sibling.publicationId}`);
      }
      const context = findPublicationStudy(catalog, tab.publicationId);
      const analyses = context?.family?.analyses ?? study.analyses;
      if (analyses?.length) {
        assert(reportHtml.includes('aria-label="Study analysis navigation"'), `Missing analysis navigation for ${tab.publicationId}`);
        for (const analysis of analyses) {
          const target = analysis.publicationTabs.find(candidate => candidate.label === tab.label) ?? analysis.publicationTabs[0];
          assert(reportHtml.includes(`href="/reports/${target.publicationId}/"`), `Missing analysis selection ${analysis.id}`);
        }
      }
      if (study.phaseFamilies?.length) {
        const phaseHtml = /<nav\b[^>]*aria-label="Study phase navigation"[^>]*>[\s\S]*?<\/nav>/.exec(reportHtml)?.[0];
        assert(phaseHtml, `Missing phase navigation for ${tab.publicationId}`);
        for (const family of study.phaseFamilies) {
          const target = familyPublicationSelection(family, context.analysis.id, tab.label).tab;
          assert(phaseHtml.includes(`href="/reports/${target.publicationId}/"`), `Missing phase selection ${family.id}`);
          if (family.id === context.family.id) {
            assert(phaseHtml.includes(`href="/reports/${target.publicationId}/" aria-current="page"`), `Missing current phase ${family.id}`);
          }
        }
      }
    }
  }
}
for (const report of index.reports) {
  assert((await stat(join(root, 'reports', report.id, 'index.html'))).isFile(), `Missing page for ${report.id}`);
}
for (const { report } of bundles) {
  const html = await readFile(join(root, 'reports', report.id, 'index.html'), 'utf8');
  for (const download of report.downloads ?? []) {
    assert(html.includes(`href="/publications/${report.id}/${download.path}"`), `Missing download link for ${report.id}/${download.path}`);
    assert(html.includes(`download="${download.path.split('/').at(-1)}"`), 'Download must retain its selected filename.');
  }
  for (const reference of report.references ?? []) {
    assert(html.includes(`id="reference-${reference.id}"`), `Missing reference anchor ${reference.id}`);
  }
}
let checked = 0;
async function visit(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const file = join(directory, entry.name);
    assert(!entry.isSymbolicLink(), 'Static export must not contain symbolic links.');
    if (entry.isDirectory()) {
      await visit(file);
    } else if (assertPagePayloadSize(file, (await stat(file)).size)) {
      checked++;
    }
  }
}
await visit(root);
console.log(`Verified library, ${catalog.studies.length} study routes, ${index.reports.length} publication routes and ${checked} bounded page payloads in out/.`);
console.log(`Verified compact delivery for ${delivery.reports} reports: ${delivery.sourceBytes} canonical bytes -> ${delivery.deliveryBytes} delivered bytes; all saved content preserved.`);
