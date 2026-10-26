import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { cp, link, mkdir, mkdtemp, readFile, readdir, realpath, rm, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { FILTERED_BUNDLE_MAX_BYTES, INDEX_MAX_BYTES, publishReport } from '../scripts/lib/publication.mjs';
import { compactStaticPublicationJson, staticPublicationDeliveryBytes, verifyStaticPublicationJson } from '../scripts/lib/static-json-delivery.mjs';

const example = JSON.parse(await readFile(new URL('../examples/report.json', import.meta.url), 'utf8'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const pretty = value => `${JSON.stringify(value, null, 2)}\n`;
const cli = new URL('../scripts/optimize-static-json.mjs', import.meta.url);

async function fixture(t, count = 1) {
  const root = await realpath(await mkdtemp(resolve(tmpdir(), 'narada-static-json-')));
  t.after(() => rm(root, { recursive: true, force: true }));
  const source = resolve(root, 'source');
  const canonicalRoot = resolve(root, 'canonical');
  const exportRoot = resolve(root, 'static');
  await mkdir(source);
  const ids = [];
  for (let i = 0; i < count; i++) {
    const report = structuredClone(example);
    report.id = `synthetic-report-${i}`;
    report.sections[0].body = 'Synthetic Unicode 雪, whitespace\n\tand escaped "quotation".';
    const reportPath = resolve(source, 'report.json');
    await writeFile(reportPath, JSON.stringify(report));
    await publishReport({ reportPath, outputRoot: canonicalRoot });
    ids.push(report.id);
  }
  await cp(canonicalRoot, exportRoot, { recursive: true });
  const file = id => resolve(exportRoot, id, 'report.json');
  const canonicalFile = id => resolve(canonicalRoot, id, 'report.json');
  return { root, canonicalRoot, exportRoot, ids, file, canonicalFile };
}

async function snapshot(root) {
  const files = {};
  async function visit(folder, prefix = '') {
    for (const entry of await readdir(folder, { withFileTypes: true })) {
      const path = prefix + entry.name;
      if (entry.isDirectory()) await visit(resolve(folder, entry.name), `${path}/`);
      else files[path] = hash(await readFile(resolve(folder, entry.name)));
    }
  }
  await visit(root);
  return files;
}

test('delivery preserves JSON values and key order including Unicode, null, booleans and numbers', () => {
  const value = { z: [null, false, true, 0, -1.25, 1e-20, 9007199254740991, '雪\n\t"'], a: { last: 2, first: 1 } };
  const bytes = Buffer.from(pretty(value));
  const compact = staticPublicationDeliveryBytes(bytes);
  assert.equal(compact.toString(), JSON.stringify(value));
  assert.deepEqual(JSON.parse(compact), value);
  assert(compact.length < bytes.length);
});

test('nonpublisher spellings refuse silent key, UTF-8 or numeric normalization', () => {
  for (const text of ['{"x":-0}', '{"x":1e999}', '{"x":1,"x":2}', '{"x":1.00}', '{"x":9007199254740993}', '{"x":1}', '{broken']) {
    assert.throws(() => staticPublicationDeliveryBytes(Buffer.from(text)));
  }
  assert.throws(() => staticPublicationDeliveryBytes(Buffer.from([123, 34, 120, 34, 58, 34, 255, 34, 125])));
  assert.throws(() => staticPublicationDeliveryBytes('not a Buffer'), /Buffer/);
});

test('compaction changes only selected export reports and returns both byte identities', async t => {
  const f = await fixture(t, 2);
  const beforeSource = await snapshot(f.canonicalRoot);
  const beforeOutput = await snapshot(f.exportRoot);
  const receipt = await compactStaticPublicationJson(f);
  assert.equal(receipt.format, 'abacus.static-json-delivery/v1');
  assert.equal(receipt.reports, 2);
  assert.equal(receipt.changed, 2);
  assert(receipt.savedBytes > 0);
  assert.equal(receipt.savedBytes, receipt.sourceBytes - receipt.deliveryBytes);
  assert.deepEqual(await snapshot(f.canonicalRoot), beforeSource);
  const after = await snapshot(f.exportRoot);
  assert.deepEqual(Object.keys(after), Object.keys(beforeOutput), 'No additional public files are created.');
  assert.equal(after['index.json'], beforeOutput['index.json']);
  for (const entry of receipt.files) {
    const source = await readFile(f.canonicalFile(entry.id));
    const delivery = await readFile(f.file(entry.id));
    assert.equal(entry.path, `publications/${entry.id}/report.json`);
    assert.equal(entry.canonicalBytes, source.length);
    assert.equal(entry.canonicalSha256, hash(source));
    assert.equal(entry.deliveryBytes, delivery.length);
    assert.equal(entry.deliverySha256, hash(delivery));
    assert.deepEqual(JSON.parse(delivery), JSON.parse(source));
  }
  const again = await compactStaticPublicationJson(f);
  assert.equal(again.changed, 0);
  assert.deepEqual(again.files, receipt.files);
  assert.deepEqual(await snapshot(f.exportRoot), after);
  const verified = await verifyStaticPublicationJson(f);
  assert.deepEqual(verified, again);
  assert.deepEqual(await snapshot(f.canonicalRoot), beforeSource);
});

test('verification is read-only and requires exact compact bytes, including no trailing newline', async t => {
  const f = await fixture(t);
  const before = await snapshot(f.exportRoot);
  await assert.rejects(verifyStaticPublicationJson(f), /exact compact/);
  assert.deepEqual(await snapshot(f.exportRoot), before);
  await compactStaticPublicationJson(f);
  const file = f.file(f.ids[0]);
  await writeFile(file, Buffer.concat([await readFile(file), Buffer.from('\n')]));
  await assert.rejects(verifyStaticPublicationJson(f), /exact compact/);
});

test('all report values are preflighted before any report is rewritten', async t => {
  const f = await fixture(t, 2);
  const first = await readFile(f.file(f.ids[0]));
  const secondPath = f.file(f.ids[1]);
  const second = JSON.parse(await readFile(secondPath));
  second.report.summary = 'Altered saved meaning';
  await writeFile(secondPath, pretty(second));
  await assert.rejects(compactStaticPublicationJson(f), /values differ/);
  assert.deepEqual(await readFile(f.file(f.ids[0])), first);
});

test('strict explicit index rejects traversal, duplicate IDs and exported index drift', async t => {
  const f = await fixture(t);
  const canonicalIndex = resolve(f.canonicalRoot, 'index.json');
  const exportedIndex = resolve(f.exportRoot, 'index.json');
  const original = await readFile(canonicalIndex);
  for (const mutate of [index => { index.reports[0].id = '../escape'; }, index => { index.reports.push(index.reports[0]); }]) {
    const index = JSON.parse(original);
    mutate(index);
    await writeFile(canonicalIndex, pretty(index));
    await writeFile(exportedIndex, pretty(index));
    await assert.rejects(compactStaticPublicationJson(f), /schema|unique/);
  }
  await writeFile(canonicalIndex, original);
  await writeFile(exportedIndex, `${original.toString()} `);
  await assert.rejects(compactStaticPublicationJson(f), /index differs/);
});

test('unselected files and selected assets are never transformed or discovered', async t => {
  const f = await fixture(t);
  const extra = resolve(f.exportRoot, 'not-selected');
  await mkdir(extra);
  await writeFile(resolve(extra, 'report.json'), 'outside explicit index');
  await mkdir(resolve(f.exportRoot, f.ids[0], 'figures'));
  const asset = resolve(f.exportRoot, f.ids[0], 'figures', 'retained.png');
  await writeFile(asset, 'untouched asset fixture');
  await compactStaticPublicationJson(f);
  assert.equal(await readFile(resolve(extra, 'report.json'), 'utf8'), 'outside explicit index');
  assert.equal(await readFile(asset, 'utf8'), 'untouched asset fixture');
});

test('identical or nested roots cannot transform canonical inputs', async t => {
  const f = await fixture(t);
  const before = await snapshot(f.canonicalRoot);
  for (const roots of [
    { canonicalRoot: f.canonicalRoot, exportRoot: f.canonicalRoot },
    { canonicalRoot: f.canonicalRoot, exportRoot: resolve(f.canonicalRoot, 'nested') },
    { canonicalRoot: resolve(f.exportRoot, 'nested'), exportRoot: f.exportRoot },
  ]) await assert.rejects(compactStaticPublicationJson(roots), /disjoint/);
  assert.deepEqual(await snapshot(f.canonicalRoot), before);
});

test('root, ancestor and selected-directory symlinks are refused', async t => {
  const f = await fixture(t);
  const alias = resolve(f.root, 'alias');
  await symlink(f.exportRoot, alias, 'dir');
  await assert.rejects(compactStaticPublicationJson({ ...f, exportRoot: alias }), /symlink/);
  await assert.rejects(compactStaticPublicationJson({ ...f, exportRoot: resolve(alias, f.ids[0]) }), /ancestors/);
  const folder = resolve(f.exportRoot, f.ids[0]);
  await rm(folder, { recursive: true });
  await symlink(resolve(f.canonicalRoot, f.ids[0]), folder, 'dir');
  await assert.rejects(compactStaticPublicationJson(f), /symlink/);
});

test('report and index symlinks are refused without changing canonical bytes', async t => {
  const f = await fixture(t);
  const before = await snapshot(f.canonicalRoot);
  const report = f.file(f.ids[0]);
  await rm(report);
  await symlink(f.canonicalFile(f.ids[0]), report);
  await assert.rejects(compactStaticPublicationJson(f), /symlink/);
  await rm(report);
  await writeFile(report, await readFile(f.canonicalFile(f.ids[0])));
  const index = resolve(f.exportRoot, 'index.json');
  await rm(index);
  await symlink(resolve(f.canonicalRoot, 'index.json'), index);
  await assert.rejects(compactStaticPublicationJson(f), /symlink/);
  assert.deepEqual(await snapshot(f.canonicalRoot), before);
});

test('hard-linked report outputs are refused before a canonical inode could be changed', async t => {
  const f = await fixture(t);
  const before = await readFile(f.canonicalFile(f.ids[0]));
  await rm(f.file(f.ids[0]));
  await link(f.canonicalFile(f.ids[0]), f.file(f.ids[0]));
  await assert.rejects(compactStaticPublicationJson(f), /hard-linked/);
  assert.deepEqual(await readFile(f.canonicalFile(f.ids[0])), before);
});

test('bounded source/index reads and regular file requirements fail closed', async t => {
  const f = await fixture(t);
  const source = f.canonicalFile(f.ids[0]);
  const original = await readFile(source);
  await writeFile(source, Buffer.alloc(FILTERED_BUNDLE_MAX_BYTES + 1, 32));
  await assert.rejects(compactStaticPublicationJson(f), /byte budget/);
  await writeFile(source, original);
  const index = resolve(f.canonicalRoot, 'index.json');
  await writeFile(index, Buffer.alloc(INDEX_MAX_BYTES + 1, 32));
  await assert.rejects(compactStaticPublicationJson(f), /byte budget/);
  await writeFile(index, await readFile(resolve(f.exportRoot, 'index.json')));
  await rm(f.file(f.ids[0]));
  await mkdir(f.file(f.ids[0]));
  await assert.rejects(compactStaticPublicationJson(f), /regular file/);
});

test('CLI only transforms supplied output and rejects malformed arguments before mutation', async t => {
  const f = await fixture(t);
  const before = await snapshot(f.exportRoot);
  const args = ['--canonical-root', f.canonicalRoot, '--export-root', f.exportRoot];
  for (const invalid of [['--unknown'], ['--export-root'], [...args, '--export-root', f.exportRoot], ['--verify', '--verify']]) {
    const result = spawnSync(process.execPath, [cli.pathname, ...invalid], { encoding: 'utf8' });
    assert.equal(result.status, 1);
    assert.deepEqual(await snapshot(f.exportRoot), before);
  }
  const compact = spawnSync(process.execPath, [cli.pathname, ...args], { encoding: 'utf8' });
  assert.equal(compact.status, 0, compact.stderr);
  assert.equal(JSON.parse(compact.stdout).changed, 1);
  assert.equal(JSON.parse(compact.stdout).files, undefined, 'Build logs contain the summary rather than the full release receipt.');
  const verify = spawnSync(process.execPath, [cli.pathname, ...args, '--verify'], { encoding: 'utf8' });
  assert.equal(verify.status, 0, verify.stderr);
  assert.equal(JSON.parse(verify.stdout).changed, 0);
});
