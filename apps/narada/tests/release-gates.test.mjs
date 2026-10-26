import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, mkdir, writeFile, readFile, readdir, lstat, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { requireGate } from '../scripts/lib/release-gates.mjs';

const artifactSha256 = 'exact-prepared-artifact';
const origin = 'https://fixture.vercel.app';
const execute = promisify(execFile);

async function tree(root) {
  const paths = (await readdir(root, { recursive: true })).sort();
  return await Promise.all(paths.map(async path => ({
    path,
    bytes: (await lstat(resolve(root, path))).isDirectory() ? null : await readFile(resolve(root, path)),
  })));
}

async function fixture(t, records, { events = true } = {}) {
  const root = await mkdtemp(resolve(tmpdir(), 'narada-release-gates-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await writeFile(resolve(root, 'sentinel.txt'), 'retained bytes\n');
  if (events) await mkdir(resolve(root, 'events'));
  for (const [name, record] of Object.entries(records)) {
    await writeFile(resolve(root, 'events', name), typeof record === 'string' ? record : JSON.stringify(record));
  }
  return { record: root, release: { artifactSha256 } };
}

async function unchanged(ctx, operation) {
  const before = await tree(ctx.record);
  try {
    return await operation();
  } finally {
    assert.deepEqual(await tree(ctx.record), before, 'Gate reads must preserve event and fixture bytes.');
  }
}

test('gate accepts exact passed artifact and supplied origin without inspecting JSON kind or timestamps', async t => {
  const ctx = await fixture(t, {
    '000-hosted-staged-production.json': { kind: 'unrelated', at: 'not-a-date', result: 'passed', artifactSha256, origin },
    '999-hosted-staged-production.json': { result: 'failed', artifactSha256, origin },
  });
  assert.equal(await unchanged(ctx, () => requireGate(ctx, 'hosted-staged-production', origin)), undefined);
});

test('any matching passing event suffices after a failed event', async t => {
  const ctx = await fixture(t, {
    '000-hosted-preview.json': { result: 'failed', artifactSha256 },
    '999-hosted-preview.json': { result: 'passed', artifactSha256 },
  });
  assert.equal(await unchanged(ctx, () => requireGate(ctx, 'hosted-preview')), undefined);
});

test('browser gate without an origin retains the original optional-origin predicate', async t => {
  for (const suppliedOrigin of [undefined, null, '']) {
    const ctx = await fixture(t, {
      '000-browser-preview.json': { result: 'passed', artifactSha256, origin: 'https://different.vercel.app' },
    });
    assert.equal(await unchanged(ctx, () => requireGate(ctx, 'browser-preview', suppliedOrigin)), undefined);
  }
  const ctx = await fixture(t, { '000-browser-preview.json': { result: 'passed', artifactSha256 } });
  assert.equal(await unchanged(ctx, () => requireGate(ctx, 'browser-preview')), undefined);
});

test('missing, failed and mismatched gates reject without changing bytes', async t => {
  const cases = [
    {},
    { '000-other-gate.json': { result: 'passed', artifactSha256, origin } },
    { '000-hosted-preview.json.backup': { result: 'passed', artifactSha256, origin } },
    { '000-hosted-preview.json': { result: 'failed', artifactSha256, origin } },
    { '000-hosted-preview.json': { result: true, artifactSha256, origin } },
    { '000-hosted-preview.json': { result: 'passed', artifactSha256: 'another-artifact', origin } },
    { '000-hosted-preview.json': { result: 'passed', artifactSha256, origin: 'https://different.vercel.app' } },
    { '000-hosted-preview.json': { result: 'passed', artifactSha256, origin: `${origin}/` } },
    { '000-hosted-preview.json': { result: 'passed', artifactSha256 } },
  ];
  for (const records of cases) {
    const ctx = await fixture(t, records);
    await unchanged(ctx, () => assert.rejects(
      requireGate(ctx, 'hosted-preview', origin),
      { message: 'Required hosted-preview gate missing for this exact release/deployment.' },
    ));
  }
});

test('malformed matching JSON and missing event directory retain their underlying errors', async t => {
  const malformed = await fixture(t, { '000-hosted-preview.json': '{invalid' });
  await unchanged(malformed, () => assert.rejects(requireGate(malformed, 'hosted-preview'), SyntaxError));
  const missing = await fixture(t, {}, { events: false });
  await unchanged(missing, () => assert.rejects(requireGate(missing, 'hosted-preview'), { code: 'ENOENT' }));
});

test('malformed unrelated files are ignored by the exact filename suffix', async t => {
  const ctx = await fixture(t, {
    '000-other-gate.json': '{invalid',
    '000-hosted-preview.json.backup': '{invalid',
    '000-hosted-preview.json': { result: 'passed', artifactSha256 },
  });
  assert.equal(await unchanged(ctx, () => requireGate(ctx, 'hosted-preview')), undefined);
});

test('helper import from an unrelated directory has no CLI, subprocess or filesystem side effects', async t => {
  const ctx = await fixture(t, {});
  const helper = new URL('../scripts/lib/release-gates.mjs', import.meta.url).href;
  const source = `
    import { syncBuiltinESMExports } from 'node:module';
    import childProcess from 'node:child_process';
    const forbidden = () => { throw new Error('Unexpected import side effect'); };
    for (const method of ['spawn', 'spawnSync', 'exec', 'execSync', 'execFile', 'execFileSync', 'fork']) {
      childProcess[method] = forbidden;
    }
    syncBuiltinESMExports();
    globalThis.fetch = forbidden;
    process.argv = [process.execPath, 'release.mjs', 'prepare'];
    await import(${JSON.stringify(helper)});
  `;
  const result = await unchanged(ctx, () => execute(process.execPath, ['--input-type=module', '-e', source], {
    cwd: ctx.record,
    env: { ...process.env, NODE_OPTIONS: '', NARADA_VERCEL_CLI: 'must-not-run' },
  }));
  assert.equal(result.stdout, '');
  assert.equal(result.stderr, '');
});
