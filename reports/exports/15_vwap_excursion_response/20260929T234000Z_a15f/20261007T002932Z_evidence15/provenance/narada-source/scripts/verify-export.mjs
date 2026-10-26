import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { extname, join, resolve } from 'node:path';
import { readPublicationIndex, verifyPublications } from './lib/publication.mjs';
import { readStudyCatalog, studyHref } from './lib/studies.mjs';

const root = resolve(import.meta.dirname, '../out');
const publicRoot = join(root, 'publications');
const { bundles } = await verifyPublications(publicRoot);
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
  for (const id of [study.featuredPublicationId, ...(study.relatedPublications ?? []).map(p => p.publicationId)]) {
    assert(html.includes(`href="/reports/${id}/"`), `Study page missing selected publication ${id}`);
    assert((await stat(join(root, 'reports', id, 'index.html'))).isFile(), `Missing selected publication page ${id}`);
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
  for (const reference of report.references ?? []) assert(html.includes(`id="reference-${reference.id}"`), `Missing reference anchor ${reference.id}`);
}
let checked = 0;
async function visit(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const file = join(directory, entry.name);
    assert(!entry.isSymbolicLink(), 'Static export must not contain symbolic links.');
    if (entry.isDirectory()) await visit(file);
    else if (['.html', '.txt', '.rsc'].includes(extname(entry.name))) {
      const budget = extname(entry.name) === '.html' ? 384 * 1024 : 256 * 1024;
      assert((await stat(file)).size <= budget, `${file} exceeds its static page budget.`);
      checked++;
    }
  }
}
await visit(root);
console.log(`Verified library, ${catalog.studies.length} study routes, ${index.reports.length} publication routes and ${checked} bounded page payloads in out/.`);
