import assert from 'node:assert/strict';
import { readdir, stat } from 'node:fs/promises';
import { extname, join, resolve } from 'node:path';
import { readPublicationIndex, verifyPublications } from './lib/publication.mjs';

const root = resolve(import.meta.dirname, '../out');
const publicRoot = join(root, 'publications');
await verifyPublications(publicRoot);
const index = await readPublicationIndex(publicRoot);
await stat(join(root, 'index.html'));
await stat(join(root, '404.html'));
for (const report of index.reports) {
  assert((await stat(join(root, 'reports', report.id, 'index.html'))).isFile(), `Missing page for ${report.id}`);
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
console.log(`Verified ${index.reports.length} published routes and ${checked} bounded page payloads in out/.`);
