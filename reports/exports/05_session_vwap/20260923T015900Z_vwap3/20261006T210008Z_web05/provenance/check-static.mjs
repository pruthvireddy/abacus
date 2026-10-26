import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const root = resolve(import.meta.dirname, '../../../../../..');
const app = resolve(root, 'apps/narada');
const { formatValue } = await import(pathToFileURL(resolve(app, 'src/lib/format.ts')));
const index = JSON.parse(await readFile(resolve(app, 'out/publications/index.json'), 'utf8'));
assert.deepEqual(index.reports.map(r => r.id).sort(), ['nq-amd-source-review-20261006-web17', 'session-vwap-vwap3-20261006-web05']);
const routes = ['/', ...index.reports.map(r => r.href)];
const paths = new Set(routes);
const pages = [];
const decode = value => value.replace(/<[^>]*>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#x27;/g, "'").replace(/&quot;/g, '"');
for (const route of routes) {
  const html = await readFile(resolve(app, 'out', route.slice(1), 'index.html'), 'utf8');
  for (const tag of html.matchAll(/<(?:a|link|script|img)\b[^>]*>/g)) {
    const attribute = tag[0].match(/(?:href|src)="([^"]+)"/);
    if (!attribute) continue;
    const target = decode(attribute[1]);
    if (target.startsWith('#')) assert(html.includes(`id="${target.slice(1)}"`), `Missing anchor ${route}${target}`);
    else if (target.startsWith('/')) paths.add(target);
  }
  if (route === '/') continue;
  const id = route.split('/')[2];
  const bundle = JSON.parse(await readFile(resolve(app, 'out/publications', id, 'report.json'), 'utf8'));
  const savedTables = bundle.report.sections.filter(s => s.kind === 'table');
  const renderedTables = [...html.matchAll(/<table\b[^>]*>([\s\S]*?)<\/table>/g)];
  assert.equal(renderedTables.length, savedTables.length);
  let cells = 0;
  for (let i = 0; i < savedTables.length; i++) {
    const section = savedTables[i];
    const actual = [...renderedTables[i][1].matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/g)].map(m => decode(m[1]));
    const expected = section.rows.flatMap(row => section.columns.map(col => formatValue(row[col.key], {format: col.format, precision: col.precision})));
    assert.deepEqual(actual, expected, section.id);
    cells += actual.length;
  }
  pages.push({publication_id:id, static_table_cells_checked:cells, section_count:bundle.report.sections.length, bytes:Buffer.byteLength(html)});
}
const responses = [];
for (const path of paths) {
  const response = await fetch('http://127.0.0.1:4173' + path);
  assert.equal(response.status, 200, path);
  await response.arrayBuffer();
  responses.push({path, status:response.status});
}
const missing = await fetch('http://127.0.0.1:4173/reports/missing-phase2-publication/');
assert.equal(missing.status, 404);
assert((await missing.text()).includes('PAGE NOT FOUND'));
const result = {pages, responses, missing_page_status:404, evidence:'HTTP checks of documented static preview; no dev server or hosted endpoint'};
await writeFile(resolve(import.meta.dirname, '../static-verification.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({pages, successful_paths:responses.length, missing_page_status:404}));
