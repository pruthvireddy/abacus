import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import * as release from '../scripts/lib/release.mjs';

// Frozen from the pre-cleanup implementation using only temporary synthetic files.
const catalog = { studies: [{ slug: 'z-last' }, { slug: 'a-first' }] };
const publications = [
  { report: { id: 'metric-one', downloads: [{ path: 'downloads/a.b.csv' }, { path: 'downloads/summary.csv' }] } },
  { report: { id: 'retained-two' } },
];
const target = { teamId: 'team_fixture', teamSlug: 'fixture', projectId: 'prj_fixture' };
const expectedInventory = [
  { path: 'A.txt', bytes: 6, sha256: 'e83189db38554920ea572093f9ad32facf682f28ccecdac085c1511735a2b492' },
  { path: 'b-lower.txt', bytes: 6, sha256: 'b908e4daaf9d57fe9cb551a689a35c9a9e0fac85fdf11faaa0a1ba0e5efc06fd' },
  { path: 'nested/é.txt', bytes: 11, sha256: 'cb6b8b4caa623860c5dbf5b0caf14afb4277fe64eafc7e5ab817176164229f64' },
  { path: 'z.txt', bytes: 3, sha256: 'f742b965f156c10374bc23aea96e3a8aff8facd6fc079defeaa30219ad86f211' },
];
const expectedConfig = {
  version: 3,
  routes: [
    {
      src: '^/publications/metric-one/downloads/a\\.b\\.csv$',
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename="a.b.csv"',
        'X-Content-Type-Options': 'nosniff',
      },
      continue: true,
    },
    {
      src: '^/publications/metric-one/downloads/summary\\.csv$',
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename="summary.csv"',
        'X-Content-Type-Options': 'nosniff',
      },
      continue: true,
    },
    { src: '^//?$', dest: '/index.html' },
    { src: '^/studies/z-last/?$', dest: '/studies/z-last/index.html' },
    { src: '^/studies/a-first/?$', dest: '/studies/a-first/index.html' },
    { src: '^/reports/metric-one/?$', dest: '/reports/metric-one/index.html' },
    { src: '^/reports/retained-two/?$', dest: '/reports/retained-two/index.html' },
    { handle: 'filesystem' },
    { src: '^/.*$', dest: '/404.html', status: 404 },
  ],
};

test('release helper export surface and insertion-order JSON bytes remain identical', () => {
  assert.deepEqual(Object.keys(release), [
    'buildOutputConfig', 'checkHosted', 'copyInventory', 'deployArgs', 'deploymentResult',
    'hash', 'inventory', 'inventoryHash', 'jsonBytes', 'parseHttpResponse', 'protectedGet',
    'releaseId', 'run', 'safeId', 'saveNew', 'validateStaticFiles', 'verifyInventory',
  ]);
  const value = { z: 1, a: { beta: false, alpha: null }, list: ['é', 0, -0] };
  const bytes = release.jsonBytes(value);
  assert.equal(bytes.toString('utf8'), '{\n  "z": 1,\n  "a": {\n    "beta": false,\n    "alpha": null\n  },\n  "list": [\n    "é",\n    0,\n    0\n  ]\n}\n');
  assert.equal(release.hash(bytes), '9f2545ae70fd275683dcde3a4ceca757d11c32ed18a58effef8c5986db324d10');
});

test('inventory preserves original locale ordering, field ordering, hashes and source bytes', async t => {
  const root = await mkdtemp(resolve(tmpdir(), 'narada-release-identity-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(resolve(root, 'nested'));
  const sources = [
    ['z.txt', Buffer.from([0, 255, 128])],
    ['A.txt', Buffer.from('upper\n')],
    ['b-lower.txt', Buffer.from('lower\n')],
    ['nested/é.txt', Buffer.from('unicode é\n')],
  ];
  for (const [path, bytes] of sources) await writeFile(resolve(root, path), bytes);
  const actual = await release.inventory(root);
  assert.deepEqual(actual, expectedInventory);
  assert.equal(release.inventoryHash(actual), '6f5076fe7877aa5de37964b4ee4effd9c88279125b8737c59e04fc2b46c5faaa');
  assert.deepEqual(await release.verifyInventory(root, expectedInventory), expectedInventory);
  for (const [path, bytes] of sources) assert.deepEqual(await readFile(resolve(root, path)), bytes);
});

test('complete Build Output routes and serialized config retain their original order and bytes', () => {
  const config = release.buildOutputConfig(catalog, publications);
  assert.deepEqual(config, expectedConfig);
  assert.equal(release.hash(release.jsonBytes(config)), '02daef440ecab01ea2dbd0fcc13ab76c064a9b7b04dcb928b96e7ba2af652735');
});

test('deployment argument arrays and parsed deployment fields remain identical', () => {
  const preview = [
    'deploy', '--prebuilt', '--yes', '--non-interactive', '--format', 'json', '--target', 'preview',
    '--scope', 'fixture', '--cwd', '/isolated/artifact', '--local-config', '/isolated/artifact/vercel.json',
  ];
  assert.deepEqual(release.deployArgs('preview', target, '/isolated/artifact'), preview);
  assert.deepEqual(release.deployArgs('production', target, '/isolated/artifact'), [
    ...preview.slice(0, 7), 'production', ...preview.slice(8), '--prod', '--skip-domain',
  ]);
  assert.deepEqual(release.deploymentResult('{"status":"ok","deployment":{"id":"dpl_fixture","url":"https://fixture.vercel.app","extra":false}}'), {
    id: 'dpl_fixture', url: 'https://fixture.vercel.app', extra: false,
  });
  assert.equal(release.protectedGet.length, 4, 'Protected retrieval retains its existing four-argument interface.');
});

test('protected HTTP parser skips proxy and interim headers while preserving binary bytes', () => {
  const bytes = Buffer.from([0, 255, 128, 13, 10]);
  const raw = Buffer.concat([
    Buffer.from('HTTP/1.1 200 Connection established\r\nProxy-Agent: fixture\r\n\r\nHTTP/1.1 100 Continue\r\n\r\nHTTP/2 200\r\nContent-Type: image/png\r\nCONTENT-DISPOSITION: inline\r\nX-Content-Type-Options: nosniff\r\n\r\n'),
    bytes,
  ]);
  assert.deepEqual(release.parseHttpResponse(raw), {
    status: 200,
    headers: { 'content-type': 'image/png', 'content-disposition': 'inline', 'x-content-type-options': 'nosniff' },
    bytes,
  });
  assert.throws(() => release.parseHttpResponse(Buffer.from('HTTP/2 200\r\n')), /Missing HTTP response headers/);
});

test('local command execution preserves strings, binary output and original failure payloads', async () => {
  const success = await release.run(process.execPath, ['-e', 'process.stdout.write("local"); process.stderr.write("notice");']);
  assert.deepEqual(success, { stdout: 'local', stderr: 'notice', exitCode: 0 });
  const script = 'process.stdout.write(Buffer.from([0,255,128])); process.stderr.write("binary notice");';
  assert.deepEqual(await release.run(process.execPath, ['-e', script], { binary: true }), {
    stdout: Buffer.from([0, 255, 128]), stderr: 'binary notice', exitCode: 0,
  });
  const failure = 'process.stdout.write("partial"); process.stderr.write("failure"); process.exit(7);';
  for (const binary of [false, true]) {
    await assert.rejects(release.run(process.execPath, ['-e', failure], { binary }), error => {
      assert.equal(error.message, `Command failed (7): ${process.execPath} -e ${failure}`);
      assert.equal(error.code, 7);
      assert.equal(error.stdout, binary ? '' : 'partial');
      assert.equal(error.stderr, 'failure');
      return true;
    });
  }
});
