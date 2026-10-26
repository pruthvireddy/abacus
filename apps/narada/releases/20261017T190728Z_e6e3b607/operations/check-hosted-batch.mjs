import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { checkHosted, parseHttpResponse, run, hash, verifyInventory, inventoryHash, jsonBytes } from '../../apps/narada/scripts/lib/release.mjs';

async function safeRun(...args) {
  try { return await run(...args); }
  catch { throw new Error('Vercel command failed; raw HTTP or authentication output was suppressed.'); }
}

async function main() {

// Operational transport adapter. The app-owned checker still checks every byte,
// selected CSV header and hard 404. No cookies or authentication headers are saved.
const workspace = resolve(import.meta.dirname, '../..');
const app = resolve(workspace, 'apps/narada');
const cli = '/Users/ppanati/.nvm/versions/node/v24.18.0/bin/vercel';
const [id, environment, origin] = process.argv.slice(2);
assert(/^\d{8}T\d{6}Z_[a-f0-9]{8}$/.test(id));
assert(['preview', 'staged-production'].includes(environment));
const url = new URL(origin);
assert(url.origin === origin && url.protocol === 'https:' && url.hostname.endsWith('.vercel.app'));
const record = resolve(app, 'releases', id);
const release = JSON.parse(await readFile(resolve(record, 'release.json'), 'utf8'));
assert.equal(release.releaseId, id);
assert.equal(release.status, 'prepared');
assert.equal(release.artifact, `.release-artifacts/${id}/deploy`);
assert.equal(inventoryHash(release.artifactFiles), release.artifactSha256);
assert.equal(hash(await readFile(resolve(app, 'scripts/lib/release.mjs'))), release.source.files.find(file => file.path === 'scripts/lib/release.mjs').sha256, 'App-owned checker bytes changed.');
const target = JSON.parse(await readFile(resolve(record, 'target.json'), 'utf8'));
const artifact = resolve(app, release.artifact);
const staticRoot = resolve(artifact, '.vercel/output/static');
const inventory = [...release.artifactFiles];
// Binding adds only this nonsecret identity file; the frozen deployment payload
// must otherwise match exactly. Use the release wrapper's own check first.
assert.equal((await safeRun(cli, ['--version'], { cwd: artifact })).stdout.trim(), release.tools.vercel);
const { lstat } = await import('node:fs/promises');
assert((await lstat(resolve(artifact, '.vercel/project.json'))).isFile());
const projectBytes = await readFile(resolve(artifact, '.vercel/project.json'));
const expectedProject = jsonBytes({ orgId: target.teamId, projectId: target.projectId, projectName: target.projectName });
assert.equal(hash(projectBytes), hash(expectedProject), 'Bound project bytes changed.');
await verifyInventory(artifact, [...inventory, { path: '.vercel/project.json', bytes: expectedProject.length, sha256: hash(expectedProject) }].sort((a, b) => a.path.localeCompare(b.path, 'en')));
const project = JSON.parse(projectBytes);
assert.equal(project.orgId, target.teamId);
assert.equal(project.projectId, target.projectId);
assert.equal(project.projectName, target.projectName);
const inspected = JSON.parse((await safeRun(cli, ['project', 'inspect', '--format', 'json', '--non-interactive', '--scope', target.teamSlug, '--cwd', artifact])).stdout);
assert.equal(inspected.id, target.projectId);
assert.equal(inspected.owner.slug, target.teamSlug);
const full = JSON.parse((await safeRun(cli, ['api', `/v9/projects/${target.projectId}?teamId=${target.teamId}`], { cwd: artifact })).stdout);
assert.equal(full.accountId, target.teamId);
assert(!full.link, 'Git-connected project rejected.');
for (const key of ['framework', 'buildCommand', 'installCommand', 'outputDirectory', 'rootDirectory']) assert.equal(full[key] ?? null, null);
const info = JSON.parse((await safeRun(cli, ['api', `/v13/deployments/${url.hostname}?teamId=${target.teamId}`], { cwd: artifact })).stdout);
assert.equal(info.projectId, target.projectId);
assert.equal(info.meta.naradaRelease, id);
assert.equal(info.meta.naradaArtifact, release.artifactSha256);
assert.equal(info.readyState, 'READY');
assert.equal(info.target ?? 'preview', environment === 'preview' ? 'preview' : 'production');

const routes = new Map(release.routes.map(route => [route.file, route.route]));
const paths = release.staticFiles.map(file => routes.get(file.path) ?? `/${file.path.split('/').map(encodeURIComponent).join('/')}`);
paths.push('/studies/not-a-study/', '/reports/not-a-publication/', '/runs/private/', '/source-map.json', '/manifest.json');
assert.equal(new Set(paths).size, paths.length);
const responses = new Map();
const chunks = [];
for (let index = 0; index < paths.length; index += 48) chunks.push(paths.slice(index, index + 48));
let next = 0;
let completed = 0;
async function batch(selected) {
  const marker = `\nABACUS_${randomUUID()}_URL:`;
  const delimiter = Buffer.from(marker);
  const args = ['curl', `${origin}${selected[0]}`, '--', '--silent', '--show-error', '--include', '--max-time', '30', '--write-out', `${marker}%{url_effective}\n`];
  for (const path of selected.slice(1)) args.push('--url', `${origin}${path}`);
  const result = await safeRun(cli, args, { cwd: artifact, binary: true });
  const bytes = result.stdout;
  let cursor = 0;
  const found = new Set();
  for (;;) {
    const boundary = bytes.indexOf(delimiter, cursor);
    if (boundary < 0) break;
    const urlStart = boundary + delimiter.length;
    const urlEnd = bytes.indexOf(10, urlStart);
    assert(urlEnd >= 0, 'Missing batch URL terminator.');
    const actual = new URL(bytes.subarray(urlStart, urlEnd).toString('utf8'));
    assert.equal(actual.origin, origin, 'Response origin changed.');
    assert(!actual.search && !actual.hash, 'Unexpected effective URL query or fragment.');
    assert(selected.includes(actual.pathname), 'Unexpected response path.');
    assert(!found.has(actual.pathname) && !responses.has(actual.pathname), 'Duplicate response.');
    responses.set(actual.pathname, parseHttpResponse(bytes.subarray(cursor, boundary)));
    found.add(actual.pathname);
    cursor = urlEnd + 1;
  }
  assert.equal(cursor, bytes.length, 'Unparsed batch response bytes.');
  assert.equal(found.size, selected.length, 'Incomplete response batch.');
  completed += selected.length;
  console.log(`Authenticated responses fetched: ${completed}/${paths.length}`);
}
await Promise.all(Array.from({ length: 4 }, async () => {
  while (next < chunks.length) await batch(chunks[next++]);
}));
assert.equal(responses.size, paths.length);
const checked = await checkHosted(release, staticRoot, origin, async path => {
  assert(responses.has(path), 'No actual hosted response for expected path.');
  return responses.get(path);
});
checked.authentication = 'authenticated Vercel CLI curl; same-origin sequential URL batches in four workers; no protection change, cookies, secrets or auth state retained';
checked.command = `node work/forex-news-publication-20261017/check-hosted-batch.mjs ${id} ${environment} ${origin}`;
checked.artifactSha256 = release.artifactSha256;
checked.kind = `hosted-${environment}`;
checked.at = new Date().toISOString();
checked.transport = { verifierSha256: hash(await readFile(import.meta.filename)), appOwnedChecks: 'unchanged checkHosted and parseHttpResponse from apps/narada/scripts/lib/release.mjs', batchSize: 48, workers: 4, responseBodies: 'actual deployment bytes held in process memory only' };
const path = resolve(record, 'events', `${Date.now()}-${randomUUID().slice(0, 8)}-hosted-${environment}.json`);
await writeFile(path, `${JSON.stringify(checked, null, 2)}\n`, { flag: 'wx' });
console.log(`Hosted ${environment}: ${checked.filesChecked} exact files, all CSV headers and five hard 404s passed.`);
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
