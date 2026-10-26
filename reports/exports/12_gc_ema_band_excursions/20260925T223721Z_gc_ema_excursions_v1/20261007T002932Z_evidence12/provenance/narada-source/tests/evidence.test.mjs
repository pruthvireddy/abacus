import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, symlink, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { publishReport, validateReport, verifyPublications, sha256, DOWNLOAD_MAX_BYTES } from '../scripts/lib/publication.mjs';
import { validateCsv } from '../scripts/lib/evidence.mjs';

const example = JSON.parse(await readFile(new URL('../examples/report.json', import.meta.url), 'utf8'));
const csv = Buffer.from('cohort,rate,delta\nA,0.42,-1.25\nB,,0\n');
function enhanced() {
  const report = structuredClone(example); report.schemaVersion = '1.1'; report.id = 'enhanced-fixture';
  report.references = [{ id: 'source', kind: 'external', label: 'Saved source', title: 'Original lesson', creator: 'Creator', url: 'https://example.org/watch?t=60', startSeconds: 60, endSeconds: 120 }];
  report.sections[2].description = 'Explicit denominator and horizon.'; report.sections[2].notes = ['Pointwise uncertainty.']; report.sections[2].referenceIds = ['source'];
  report.downloads = [{ id: 'selected', path: 'downloads/selected.csv', label: 'Selected rates', description: 'Two saved summary rows', population: 'Separate cohorts', units: 'Rate is a ratio; delta is points', scope: 'Same evidence as the page', mediaType: 'text/csv', sha256: sha256(csv), rowCount: 2, columns: ['cohort', 'rate', 'delta'], source: { runId: report.source.runId, artifact: 'tables/summary.csv', sha256: 'a'.repeat(64) } }];
  return report;
}
async function fixture(t) {
  const root = await mkdtemp(resolve(tmpdir(), 'narada-evidence-')); t.after(() => rm(root, { recursive: true, force: true }));
  const source = resolve(root, 'source'); await mkdir(resolve(source, 'downloads'), { recursive: true });
  const reportPath = resolve(source, 'report.json'); const report = enhanced();
  await writeFile(reportPath, JSON.stringify(report)); await writeFile(resolve(source, report.downloads[0].path), csv);
  return { root, source, reportPath, report, outputRoot: resolve(root, 'publications') };
}
async function save(f) { await writeFile(f.reportPath, JSON.stringify(f.report)); }

test('versions 1.0 and 1.1 coexist without rewriting old publication bytes', async t => {
  const f = await fixture(t); const oldPath = resolve(f.source, 'old.json'); await writeFile(oldPath, JSON.stringify(example));
  await publishReport({ ...f, reportPath: oldPath }); const oldBundle = resolve(f.outputRoot, example.id, 'report.json'); const before = await readFile(oldBundle);
  assert.equal((await publishReport({ ...f, dryRun: true })).status, 'ready'); await publishReport(f);
  assert.deepEqual(await readFile(oldBundle), before);
  assert.equal((await verifyPublications(f.outputRoot)).downloads, 1);
  assert.equal((await publishReport(f)).status, 'unchanged');
  const bundle = JSON.parse(await readFile(resolve(f.outputRoot, f.report.id, 'report.json')));
  assert.equal(bundle.provenance.assets[0].sha256, sha256(csv));
  f.report.downloads[0].description = 'Changed scope'; await save(f); await assert.rejects(publishReport(f), /new report ID/);
});
test('version selection, unsafe URLs, references and source attribution are strict', () => {
  assert.throws(() => validateReport({ ...enhanced(), schemaVersion: '1.0' }), /schema/);
  for (const change of [r => r.schemaVersion = '2.0', r => r.references[0].url = 'javascript:alert(1)', r => r.references[0].url = 'https://user:pass@example.org', r => r.references[0].url = 'https://127.0.0.1', r => r.references[0].url = 'file:///Users/private.csv', r => r.references[0].url = 'https://example.org\n', r => r.references[0].endSeconds = 30, r => r.references[0].publishedOn = '2026-02-30', r => r.references.push(r.references[0]), r => r.sections[0].referenceIds = ['missing'], r => r.downloads[0].source.runId = 'other-run', r => r.downloads.push(r.downloads[0])]) {
    const report = enhanced(); change(report); assert.throws(() => validateReport(report));
  }
});
test('download paths, unsupported types, missing files and source/file/directory symlinks are rejected', async t => {
  const f = await fixture(t);
  const sourceLink = resolve(f.root, 'source-link'); await symlink(f.source, sourceLink);
  await assert.rejects(publishReport({ ...f, reportPath: resolve(sourceLink, 'report.json') }), /source must be a real directory/);
  await rm(sourceLink);
  for (const path of ['../private.csv', '/Users/private.csv', 'downloads/../private.csv', 'downloads/private.html', 'downloads/a.csv/extra']) {
    f.report.downloads[0].path = path; await save(f); await assert.rejects(publishReport(f), /schema/);
  }
  f.report.downloads[0].path = 'downloads/selected.csv'; f.report.downloads[0].mediaType = 'text/html'; await save(f); await assert.rejects(publishReport(f), /schema/);
  f.report.downloads[0].mediaType = 'text/csv'; await save(f); const asset = resolve(f.source, 'downloads/selected.csv'); await rm(asset); await assert.rejects(publishReport(f), /ENOENT/);
  const external = resolve(f.root, 'external.csv'); await writeFile(external, csv); await symlink(external, asset); await assert.rejects(publishReport(f), /symlink/); await rm(asset);
  await rm(resolve(f.source, 'downloads'), { recursive: true }); const outside = resolve(f.root, 'outside'); await mkdir(outside); await writeFile(resolve(outside, 'selected.csv'), csv); await symlink(outside, resolve(f.source, 'downloads')); await assert.rejects(publishReport(f), /symlink/);
});
test('download hashes, UTF-8 structure, headers, row count and formulas are checked', async t => {
  const f = await fixture(t);
  for (const data of [Buffer.from('wrong,header\n1,2\n'), Buffer.from([255,254]), Buffer.from('cohort,rate,delta\nA,1\n'), Buffer.from('cohort,rate,delta\n"unterminated,1,2\n'), Buffer.from('cohort,rate,delta\n=HYPERLINK("x"),0,1\n')]) {
    f.report.downloads[0].sha256 = sha256(data); await save(f); await writeFile(resolve(f.source, 'downloads/selected.csv'), data); await assert.rejects(publishReport(f));
  }
  await writeFile(resolve(f.source, 'downloads/selected.csv'), csv); f.report.downloads[0].sha256 = 'b'.repeat(64); await save(f); await assert.rejects(publishReport(f), /hash/);
  assert.deepEqual(validateCsv(Buffer.from('label,value\n"comma, quote ""yes""",-2e-3\n'), { columns: ['label', 'value'], rowCount: 1 })[1], ['comma, quote "yes"', '-2e-3']);
});
test('per-file and total download budgets are independent of figure budgets', async t => {
  const f = await fixture(t); await writeFile(resolve(f.source, 'downloads/selected.csv'), Buffer.alloc(DOWNLOAD_MAX_BYTES + 1)); await assert.rejects(publishReport(f), /budget/);
  const data = Buffer.from('value\n' + ('x'.repeat(249) + '\n').repeat(1000));
  f.report.downloads = [];
  for (let i = 0; i < 3; i++) { const declaration = structuredClone(enhanced().downloads[0]); Object.assign(declaration, { id: `file-${i}`, path: `downloads/file-${i}.csv`, columns: ['value'], rowCount: 1000, sha256: sha256(data) }); f.report.downloads.push(declaration); await writeFile(resolve(f.source, declaration.path), data); }
  await save(f); await assert.rejects(publishReport(f), /total download/);
});
test('staged downloads verify their hashes and unselected source files never cross the boundary', async t => {
  const f = await fixture(t); await writeFile(resolve(f.source, 'downloads/private.csv'), 'private'); await publishReport(f);
  const path = resolve(f.outputRoot, f.report.id, 'downloads/selected.csv'); assert.deepEqual(await readFile(path), csv);
  await assert.rejects(readFile(resolve(f.outputRoot, f.report.id, 'downloads/private.csv')), /ENOENT/);
  await writeFile(path, 'cohort,rate,delta\nA,0.43,-1.25\nB,,0\n'); await assert.rejects(verifyPublications(f.outputRoot), /hash/);
});
