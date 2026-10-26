import assert from 'node:assert/strict';
import { mkdir, mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import test from 'node:test';
import { publishReport, validateReport, verifyPublications, sha256, REPORT_MAX_BYTES, FILTERED_REPORT_MAX_BYTES, FILTERED_BUNDLE_MAX_BYTES, FILTERED_DOWNLOAD_MAX_BYTES, FILTERED_TOTAL_DOWNLOAD_MAX_BYTES } from '../scripts/lib/publication.mjs';
import { validateCsv } from '../scripts/lib/evidence.mjs';

const example = JSON.parse(await readFile(new URL('../examples/report.json', import.meta.url), 'utf8'));
const filteredReport = () => ({ ...structuredClone(example), schemaVersion: '1.1', sections: [{ id: 'saved', kind: 'table', title: 'Saved groups', columns: [{ key: 'year', label: 'Year' }, { key: 'value', label: 'Saved value', format: 'number', precision: 0 }], rowFilters: [{ key: 'year', label: 'Year', defaultValue: 'All years' }], rows: Array.from({ length: 1080 }, (_, value) => ({ year: value < 15 ? 'All years' : '2020', value })) }] });

async function fixture(t) {
  const root = await mkdtemp(resolve(tmpdir(), 'narada-filtered-')); t.after(() => rm(root, { recursive: true, force: true }));
  const source = resolve(root, 'source'); await mkdir(source);
  const report = filteredReport(); const reportPath = resolve(source, 'publication.json');
  return { root, source, report, reportPath, outputRoot: resolve(root, 'publications') };
}

test('filtered tables require bounded declared columns, unique filters and existing exact defaults', () => {
  validateReport(filteredReport());
  for (const alter of [
    s => { delete s.rowFilters; }, s => { s.rows = Array.from({ length: 1501 }, () => s.rows[0]); },
    s => { s.rowFilters = []; }, s => { s.rowFilters[0].key = 'missing'; },
    s => { s.rowFilters.push(s.rowFilters[0]); }, s => { s.rowFilters[0].defaultValue = 'Unknown'; },
    s => { s.rowFilters[0].label = ' '; }, s => { s.rowFilters.push({ key: 'value', label: 'Value' }, { key: 'year', label: 'Third' }, { key: 'value', label: 'Fourth' }); },
  ]) {
    const report = filteredReport(); alter(report.sections[0]); assert.throws(() => validateReport(report));
  }
  const report = filteredReport(); report.sections[0].rows = Array.from({ length: 1500 }, () => ({ year: 'All years', value: 1 })); validateReport(report);
});

test('source budgets remain 96 KiB for ordinary reports and permit exact 2 MiB only with saved row filters', async t => {
  const f = await fixture(t);
  const text = JSON.stringify(f.report);
  await writeFile(f.reportPath, text + ' '.repeat(FILTERED_REPORT_MAX_BYTES - Buffer.byteLength(text)));
  assert.equal(FILTERED_REPORT_MAX_BYTES, 2 * 1024 * 1024);
  assert.equal(FILTERED_BUNDLE_MAX_BYTES, 4 * 1024 * 1024);
  assert.equal((await publishReport({ ...f, dryRun: true })).status, 'ready');
  await writeFile(f.reportPath, text + ' '.repeat(FILTERED_REPORT_MAX_BYTES + 1 - Buffer.byteLength(text)));
  await assert.rejects(publishReport({ ...f, dryRun: true }), /budget/);
  const ordinary = JSON.stringify(example);
  await writeFile(f.reportPath, ordinary + ' '.repeat(REPORT_MAX_BYTES + 1 - Buffer.byteLength(ordinary)));
  await assert.rejects(publishReport({ ...f, dryRun: true }), /Report source exceeds byte budget/);
});

test('filtered publications retain larger saved tables and immutable canonical identities', async t => {
  const f = await fixture(t);
  f.report.sections = Array.from({ length: 8 }, (_, table) => ({ id: `saved-${table}`, kind: 'table', title: 'Saved groups', columns: Array.from({ length: 12 }, (_, column) => ({ key: `c${column}`, label: `Saved ${column}` })), rowFilters: [{ key: 'c0', label: 'Group', defaultValue: 'all' }], rows: Array.from({ length: 1080 }, () => Object.fromEntries(Array.from({ length: 12 }, (_, column) => [`c${column}`, column ? 1 : 'all']))) }));
  await writeFile(f.reportPath, JSON.stringify(f.report));
  assert.equal((await publishReport(f)).status, 'published');
  const path = resolve(f.outputRoot, f.report.id, 'report.json'); const before = await readFile(path);
  assert(before.length > 192 * 1024 && before.length <= FILTERED_BUNDLE_MAX_BYTES);
  assert.equal((await publishReport(f)).status, 'unchanged'); assert.deepEqual(await readFile(path), before);
  assert.equal((await verifyPublications(f.outputRoot)).reports, 1);
  await writeFile(path, Buffer.concat([before, Buffer.alloc(FILTERED_BUNDLE_MAX_BYTES - before.length, 32)]));
  assert.equal((await verifyPublications(f.outputRoot)).reports, 1, 'Exact filtered bundle byte boundary is accepted.');
  await writeFile(path, Buffer.concat([before, Buffer.alloc(FILTERED_BUNDLE_MAX_BYTES + 1 - before.length, 32)]));
  await assert.rejects(verifyPublications(f.outputRoot), /budget/);
});

test('filtered selected CSVs allow 15000 saved rows while ordinary CSVs remain limited to 1000', async t => {
  const f = await fixture(t); await mkdir(resolve(f.source, 'downloads'));
  const bytes = Buffer.from(`value\n${Array.from({ length: 15000 }, () => 'a'.repeat(170)).join('\n')}\n`);
  const declaration = { id: 'saved', path: 'downloads/saved.csv', label: 'Saved groups', description: 'Explicit saved table rows.', population: 'Saved events', units: 'Saved units', scope: 'All saved groups', mediaType: 'text/csv', rowCount: 15000, columns: ['value'], sha256: sha256(bytes), source: { runId: f.report.source.runId, artifact: 'tables/saved.csv', sha256: 'a'.repeat(64) } };
  assert(bytes.length > 256 * 1024 && bytes.length < FILTERED_DOWNLOAD_MAX_BYTES);
  assert.equal(FILTERED_TOTAL_DOWNLOAD_MAX_BYTES, 8 * 1024 * 1024);
  f.report.downloads = [declaration]; await writeFile(resolve(f.source, declaration.path), bytes); await writeFile(f.reportPath, JSON.stringify(f.report));
  assert.equal((await publishReport(f)).status, 'published'); assert.equal((await verifyPublications(f.outputRoot)).downloads, 1);
  assert.equal(validateCsv(bytes, declaration, 15000).length, 15001);
  assert.throws(() => validateCsv(bytes, declaration), /1000 data rows/);
  const ordinary = { ...structuredClone(example), schemaVersion: '1.1', downloads: [declaration] }; assert.throws(() => validateReport(ordinary), /1000 data rows/);
  f.report.downloads = Array.from({ length: 4 }, (_, index) => ({ ...declaration, id: `saved-${index}`, path: `downloads/saved-${index}.csv` }));
  for (const download of f.report.downloads) await writeFile(resolve(f.source, download.path), bytes);
  f.report.id = 'large-filtered'; await writeFile(f.reportPath, JSON.stringify(f.report));
  await assert.rejects(publishReport({ ...f, dryRun: true }), /total download byte budget/);
  f.report.downloads = [declaration]; await writeFile(resolve(f.source, declaration.path), Buffer.alloc(FILTERED_DOWNLOAD_MAX_BYTES + 1)); await writeFile(f.reportPath, JSON.stringify(f.report));
  await assert.rejects(publishReport({ ...f, dryRun: true }), /budget/);
  const tooMany = filteredReport(); tooMany.downloads = [{ ...declaration, rowCount: 15001 }]; assert.throws(() => validateReport(tooMany));
});

test('compact filtered sources still refuse canonical bundle expansion above 4 MiB', async t => {
  const f = await fixture(t);
  f.report.sections = Array.from({ length: 16 }, (_, index) => ({ id: `saved-${index}`, kind: 'table', title: 'Saved groups', rowFilters: [{ key: 'a', label: 'Group', defaultValue: 1 }], columns: Array.from({ length: 12 }, (_, column) => ({ key: String.fromCharCode(97 + column), label: `Value ${column}` })), rows: Array.from({ length: 1500 }, () => Object.fromEntries(Array.from({ length: 12 }, (_, column) => [String.fromCharCode(97 + column), 1]))) }));
  const text = JSON.stringify(f.report); assert(Buffer.byteLength(text) < FILTERED_REPORT_MAX_BYTES);
  await writeFile(f.reportPath, text);
  await assert.rejects(publishReport({ ...f, dryRun: true }), /Publication bundle exceeds byte budget/);
});
