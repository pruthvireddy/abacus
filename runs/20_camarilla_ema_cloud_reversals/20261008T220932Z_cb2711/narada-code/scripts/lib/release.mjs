import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { readFile, writeFile, mkdir, readdir, lstat, copyFile } from 'node:fs/promises';
import { resolve, dirname, relative } from 'node:path';
import { spawn } from 'node:child_process';

export const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export const jsonBytes = value => Buffer.from(`${JSON.stringify(value, null, 2)}\n`);
export const releaseId = () => `${new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z')}_${randomUUID().slice(0, 8)}`;
export function safeId(id) { assert(/^\d{8}T\d{6}Z_[a-f0-9]{8}$/.test(id), 'Invalid release ID.'); return id; }
export async function saveNew(file, value) {
  await mkdir(dirname(file), { recursive: true });
  await writeFile(file, jsonBytes(value), { flag: 'wx' });
}
export async function inventory(root) {
  const files = [];
  async function visit(dir) {
    assert((await lstat(dir)).isDirectory() && !(await lstat(dir)).isSymbolicLink(), 'Directory symlinks are forbidden.');
    for (const entry of await readdir(dir, { withFileTypes: true })) {
      assert(!entry.isSymbolicLink(), `Symlinks are forbidden: ${entry.name}`);
      const path = resolve(dir, entry.name);
      if (entry.isDirectory()) await visit(path);
      else {
        assert(entry.isFile(), 'Only regular files are permitted.');
        const bytes = await readFile(path);
        files.push({ path: relative(root, path).split('\\').join('/'), bytes: bytes.length, sha256: hash(bytes) });
      }
    }
  }
  await visit(root);
  return files.sort((a,b) => a.path.localeCompare(b.path, 'en'));
}
export const inventoryHash = files => hash(jsonBytes(files));
export async function verifyInventory(root, expected) {
  const actual = await inventory(root);
  assert.deepEqual(actual, expected, 'Release file inventory changed (missing, modified or extra files).');
  return actual;
}
export async function copyInventory(from, to, files) {
  for (const entry of files) {
    const target = resolve(to, entry.path);
    assert(target.startsWith(`${resolve(to)}/`), 'File path escapes destination.');
    await mkdir(dirname(target), { recursive: true });
    await copyFile(resolve(from, entry.path), target);
  }
  await verifyInventory(to, files);
}

// Fail closed on new output kinds; adding a public feature requires explicit review.
export function validateStaticFiles(files, catalog, publications) {
  const selected = new Set(['publications/index.json', ...publications.flatMap(b => [
    `publications/${b.report.id}/report.json`, ...b.provenance.assets.map(a => `publications/${b.report.id}/${a.path}`),
  ])]);
  const pages = new Set(['', '404/', '_not-found/', ...catalog.studies.map(s => `studies/${s.slug}/`),
    ...publications.map(b => `reports/${b.report.id}/`)]);
  const actual = new Set(files.map(f => f.path));
  for (const page of pages) assert(actual.has(`${page}index.html`), `Missing static page ${page}`);
  assert(actual.has('404.html'), 'Missing 404 page.');
  for (const path of selected) assert(actual.has(path), `Missing selected public file ${path}`);
  for (const {path} of files) {
    const slash = path.lastIndexOf('/');
    const folder = slash < 0 ? '' : path.slice(0, slash + 1), name = path.slice(slash + 1);
    const pageFile = pages.has(folder) && (/^index\.(html|txt)$/.test(name) || /^__next\.[A-Za-z0-9_.$-]+\.txt$/.test(name));
    const runtime = /^_next\/static\/(?:[A-Za-z0-9_-]+\/)+[A-Za-z0-9_.-]+\.(js|css)$/.test(path);
    assert(path === '404.html' || selected.has(path) || pageFile || runtime, `Unselected static output: ${path}`);
  }
}
const escapeRegex = text => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
export function buildOutputConfig(catalog, publications) {
  const routes = [];
  for (const b of publications) for (const d of b.report.downloads ?? []) routes.push({
    src: `^${escapeRegex(`/publications/${b.report.id}/${d.path}`)}$`,
    headers: { 'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': `attachment; filename="${d.path.split('/').at(-1)}"`, 'X-Content-Type-Options': 'nosniff' }, continue: true,
  });
  // Enumerate actual pages; an unknown study/report must never fall back to 200.
  for (const route of ['/', ...catalog.studies.map(s=>`/studies/${s.slug}/`), ...publications.map(b=>`/reports/${b.report.id}/`)]) {
    routes.push({src: `^${escapeRegex(route === '/' ? route : route.slice(0,-1))}/?$`, dest: `${route}index.html`});
  }
  routes.push({ handle: 'filesystem' }, { src: '^/.*$', dest: '/404.html', status: 404 });
  return { version: 3, routes };
}
export function deployArgs(environment, target, artifact) {
  assert(['preview', 'production'].includes(environment), 'Invalid deployment environment.');
  assert(target?.teamId?.startsWith('team_') && target?.projectId?.startsWith('prj_') && /^[a-z0-9-]+$/.test(target.teamSlug), 'Explicit team/project required.');
  return ['deploy', '--prebuilt', '--yes', '--non-interactive', '--format', 'json', '--target', environment, '--scope', target.teamSlug, '--cwd', artifact, '--local-config', resolve(artifact,'vercel.json'),
    ...(environment === 'production' ? ['--prod', '--skip-domain'] : [])];
}
export function deploymentResult(stdout) {
  const value = JSON.parse(stdout);
  assert(value.status === 'ok' && value.deployment?.id?.startsWith('dpl_'), 'Missing successful deployment result.');
  const url = new URL(value.deployment.url);
  assert(url.protocol === 'https:' && url.origin === value.deployment.url && url.hostname.endsWith('.vercel.app'), 'Unexpected deployment URL.');
  return value.deployment;
}
export async function run(command, args, options = {}) {
  return await new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: options.cwd, env: { ...process.env, VERCEL_TELEMETRY_DISABLED: '1' }, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = ''; const buffers = [];
    child.stdout.on('data', chunk => { if(options.binary) buffers.push(chunk); else stdout += chunk; if (options.echo) process.stdout.write(chunk); });
    child.stderr.on('data', chunk => { stderr += chunk; if (options.echo) process.stderr.write(chunk); });
    child.on('error', reject);
    child.on('close', code => {
      if (code !== 0) reject(Object.assign(new Error(`Command failed (${code}): ${command} ${args.join(' ')}`), { code, stdout, stderr }));
      else resolvePromise({ stdout: options.binary ? Buffer.concat(buffers) : stdout, stderr, exitCode: code });
    });
  });
}
export function parseHttpResponse(bytes) {
  let offset=0, end, header;
  do {
    end=bytes.indexOf('\r\n\r\n',offset);assert(end>=0,'Missing HTTP response headers.');
    header=bytes.subarray(offset,end).toString('utf8');offset=end+4;
  } while (/^HTTP\/\S+ (?:100|200 Connection established)/.test(header));
  const status=Number(header.match(/^HTTP\/\S+ (\d{3})/)?.[1]);assert(status,'Invalid HTTP status.');
  const headers={};
  for(const name of ['content-type','content-disposition','x-content-type-options']) headers[name]=header.match(new RegExp(`^${name}:\\s*([^\\r\\n]*)`,'im'))?.[1]?.trim();
  return {status,headers,bytes:bytes.subarray(offset)};
}
export function protectedGet(cli, origin, target, artifact) {
  return async path => parseHttpResponse((await run(cli,['curl',`${origin}${path}`,'--','--silent','--show-error','--include','--max-time','30'],{binary:true,cwd:artifact})).stdout);
}

export async function checkHosted(release, staticRoot, origin, get = async path => {
  const response = await fetch(new URL(path, origin), { redirect: 'manual', signal: AbortSignal.timeout(30000) });
  return { status: response.status, headers: Object.fromEntries(response.headers), bytes: Buffer.from(await response.arrayBuffer()) };
}) {
  const url = new URL(origin);
  assert(url.origin === origin && url.protocol === 'https:' && url.hostname.endsWith('.vercel.app'), 'Expected a clean Vercel HTTPS origin.');
  const results = [];
  const pagePaths = new Map(release.routes.map(r => [r.file, r.route]));
  // Every prepared file is retrieved, including Next navigation payloads and chunks.
  async function checkFile(file) {
    const path = pagePaths.get(file.path) ?? `/${file.path.split('/').map(encodeURIComponent).join('/')}`;
    const response = await get(path);
    assert.equal(response.status, 200, `Hosted ${path}: status ${response.status}; an authentication page is not verification.`);
    assert.equal(hash(response.bytes), file.sha256, `Hosted file differs: ${path}`);
    if (file.path.endsWith('.csv')) {
      assert(/^text\/csv(?:;|$)/i.test(response.headers['content-type'] ?? ''), 'CSV media type missing.');
      assert.equal(response.headers['content-disposition'], `attachment; filename="${file.path.split('/').at(-1)}"`, 'CSV attachment filename differs.');
      assert.equal(response.headers['x-content-type-options'], 'nosniff', 'CSV nosniff missing.');
    }
    return { path, status: response.status, sha256: hash(response.bytes), bytes: response.bytes.length };
  }
  let next=0,done=0; const fileResults=new Array(release.staticFiles.length);
  await Promise.all(Array.from({length:Math.min(6,release.staticFiles.length)},async()=>{
    while(next<release.staticFiles.length) {
      const i=next++;fileResults[i]=await checkFile(release.staticFiles[i]);done++;
      if(done%50===0)console.log(`Hosted files checked: ${done}/${release.staticFiles.length}`);
    }
  }));
  results.push(...fileResults);
  const expected404 = hash(await readFile(resolve(staticRoot, '404.html')));
  for (const path of ['/studies/not-a-study/', '/reports/not-a-publication/', '/runs/private/', '/source-map.json', '/manifest.json']) {
    const response = await get(path);
    assert.equal(response.status, 404, `Unknown/private path ${path} must return 404.`);
    assert.equal(hash(response.bytes), expected404, `Unexpected missing-page response for ${path}`);
    results.push({ path, status: 404, sha256: expected404 });
  }
  return { result: 'passed', origin, authentication: 'anonymous HTTPS; no cookies or bypass credentials', checkedAt: new Date().toISOString(), filesChecked: release.staticFiles.length, results };
}
