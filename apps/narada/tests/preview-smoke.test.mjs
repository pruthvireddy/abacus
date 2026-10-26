import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { mkdir, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import test from 'node:test';
import { checkPreview, validatePreviewOrigin } from '../scripts/lib/preview-smoke.mjs';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const origin = 'http://127.0.0.1:4173';
const pageRoutes = ['/', '/studies/one/', '/reports/featured/', '/reports/retained/'];

async function fixture(t) {
  const staticRoot = await mkdtemp(resolve(tmpdir(), 'narada-local-smoke-'));
  t.after(() => rm(staticRoot, { recursive: true, force: true }));
  const figure = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10, 0, 255, 128]);
  const csv = Buffer.from('rate,label\n0.125,selected_original\n');
  const files = new Map([
    ['/', ['index.html', Buffer.from('<main>Temporary library</main>'), 'text/html']],
    ['/studies/one/', ['studies/one/index.html', Buffer.from('<main>Temporary study</main>'), 'text/html']],
    ['/reports/featured/', ['reports/featured/index.html', Buffer.from('<main>Featured evidence</main>'), 'text/html']],
    ['/reports/retained/', ['reports/retained/index.html', Buffer.from('<main>Retained revision</main>'), 'text/html']],
    ['/publications/featured/report.json', ['publications/featured/report.json', Buffer.from('{"id":"featured"}\n'), 'application/json']],
    ['/publications/featured/figures/chart.png', ['publications/featured/figures/chart.png', figure, 'image/png']],
    ['/publications/featured/downloads/selected.csv', ['publications/featured/downloads/selected.csv', csv, 'text/csv']],
  ]);
  for (const [file, bytes] of files.values()) {
    await mkdir(resolve(staticRoot, file, '..'), { recursive: true });
    await writeFile(resolve(staticRoot, file), bytes);
  }
  const notFound = Buffer.from('<main>Saved 404</main>');
  await writeFile(resolve(staticRoot, '404.html'), notFound);
  // Unselected material is outside the bounded smoke cases, even if present.
  await writeFile(resolve(staticRoot, 'not-selected.txt'), 'not a smoke input');
  const catalog = { studies: [{ slug: 'one', featuredPublicationId: 'featured',
    relatedPublications: [{ publicationId: 'retained', relationship: 'presentation-revision' }] }] };
  const bundles = [{ report: { id: 'featured', sections: [{ kind: 'figure', path: 'figures/chart.png' }],
    downloads: [{ path: 'downloads/selected.csv', sha256: hash(csv) }] },
  provenance: { assets: [{ path: 'figures/chart.png', sha256: hash(figure) },
    { path: 'downloads/selected.csv', sha256: hash(csv) }] } },
  { report: { id: 'retained', sections: [] }, provenance: { assets: [] } }];
  const requests = [];
  const transport = async (url, options) => {
    requests.push({ url, ...options });
    const path = new URL(url).pathname;
    const entry = files.get(path);
    const type = entry?.[2] ?? 'text/html';
    const headers = { 'content-type': `${type}; charset=utf-8` };
    if (type === 'text/csv') {
      headers['content-disposition'] = 'attachment; filename="selected.csv"';
      headers['x-content-type-options'] = 'nosniff';
    }
    return { status: entry ? 200 : 404, headers,
      bytes: options.method === 'HEAD' ? Buffer.alloc(0) : entry?.[1] ?? notFound, url };
  };
  return { options: { origin, staticRoot, catalog, bundles, pageRoutes, transport }, files, requests, notFound };
}

function alterTransport(fixture, alter) {
  return async (url, options) => alter(await fixture.options.transport(url, options), new URL(url).pathname, options.method);
}

test('preview origins admit only explicit clean HTTP loopback origins', () => {
  for (const value of ['http://127.0.0.1:4173', 'http://localhost:4173', 'http://[::1]:4173']) {
    assert.equal(validatePreviewOrigin(value), value);
  }
  for (const value of [undefined, '', 'not a URL', 'https://127.0.0.1:4173',
    'http://example.org', 'http://127.0.0.2:4173', 'http://0.0.0.0:4173',
    'http://127.0.0.1:4173/', 'http://127.0.0.1:4173/path', 'http://127.0.0.1:4173?x=1',
    'http://127.0.0.1:4173#x', 'http://user:secret@127.0.0.1:4173',
    ' http://127.0.0.1:4173', 'http://127.0.0.1:4173\n', 'http://127.0.0.1:4173\\path',
    'http://2130706433:4173', 'http://127.0.0.1:99999']) {
    assert.throws(() => validatePreviewOrigin(value), /origin|loopback/);
  }
});

test('local smoke checks bounded app-owned bytes and GET/HEAD headers without changing output', async t => {
  const f = await fixture(t);
  const before = await readFile(resolve(f.options.staticRoot, 'not-selected.txt'));
  const result = await checkPreview(f.options);
  assert.deepEqual({ pages: result.pagesChecked, files: result.filesChecked,
    notFound: result.notFoundChecked, requests: result.requestsChecked },
  { pages: 4, files: 7, notFound: 4, requests: 22 });
  assert.equal(f.requests.length, 22);
  assert(f.requests.every(request => request.redirect === 'error'));
  assert.deepEqual(f.requests.map(request => request.method), Array.from({ length: 11 }, () => ['GET', 'HEAD']).flat());
  assert.equal(result.checks[6].sha256, hash(f.files.get('/publications/featured/downloads/selected.csv')[1]));
  assert.deepEqual(await readFile(resolve(f.options.staticRoot, 'not-selected.txt')), before);
  for (const [file, bytes] of f.files.values()) {
    assert.deepEqual(await readFile(resolve(f.options.staticRoot, file)), bytes);
  }
});

test('explicit smoke selections include same-run publication tabs', async t => {
  const f = await fixture(t);
  delete f.options.catalog.studies[0].relatedPublications;
  f.options.catalog.studies[0].publicationTabs = [
    { publicationId: 'featured', sourceRunId: 'saved_run', label: 'Chart A' },
    { publicationId: 'retained', sourceRunId: 'saved_run', label: 'Chart B' },
  ];
  assert.equal((await checkPreview(f.options)).pagesChecked, 4);
});

test('explicit smoke selections include a chart selected through an analysis group', async t => {
  const f = await fixture(t);
  delete f.options.catalog.studies[0].relatedPublications;
  f.options.catalog.studies[0].analyses = [{ id: 'analysis', publicationTabs: [{ publicationId: 'featured' }, { publicationId: 'retained' }] }];
  assert.equal((await checkPreview(f.options)).pagesChecked, 4);
});

test('explicit smoke selections resolve charts across two phase families through the same authored selection helper', async t => {
  const f = await fixture(t);
  delete f.options.catalog.studies[0].relatedPublications;
  f.options.catalog.studies[0].phaseFamilies = [
    { id: 'earlier', analyses: [{ id: 'retained', publicationTabs: [{ publicationId: 'retained' }] }] },
    { id: 'later', analyses: [{ id: 'current', publicationTabs: [{ publicationId: 'featured' }] }] },
  ];
  assert.equal((await checkPreview(f.options)).pagesChecked, 4);
});

test('preview smoke rejects incorrect GET bytes, media headers and HEAD bodies', async t => {
  const f = await fixture(t);
  for (const path of ['/', '/publications/featured/report.json',
    '/publications/featured/figures/chart.png', '/publications/featured/downloads/selected.csv']) {
    await assert.rejects(checkPreview({ ...f.options, transport: alterTransport(f, (response, route, method) =>
      route === path && method === 'GET' ? { ...response, bytes: Buffer.from('different') } : response) }), /bytes differ/);
    for (const method of ['GET', 'HEAD']) {
      await assert.rejects(checkPreview({ ...f.options, transport: alterTransport(f, (response, route, verb) =>
        route === path && verb === method ? { ...response, headers: { ...response.headers, 'content-type': 'text/plain' } } : response) }), /media type/);
    }
  }
  await assert.rejects(checkPreview({ ...f.options, transport: alterTransport(f, (response, _route, method) =>
    method === 'HEAD' ? { ...response, bytes: Buffer.from('unexpected body') } : response) }), /HEAD returned a body/);
  await assert.rejects(checkPreview({ ...f.options, transport: alterTransport(f, response =>
    ({ ...response, status: 401 })) }), /Expected 200/);
});

test('selected CSV attachment filenames and nosniff are checked for GET and HEAD', async t => {
  const f = await fixture(t);
  for (const method of ['GET', 'HEAD']) {
    for (const [header, value, message] of [
      ['content-disposition', 'attachment; filename="other.csv"', /filename/],
      ['x-content-type-options', '', /nosniff/],
    ]) {
      await assert.rejects(checkPreview({ ...f.options, transport: alterTransport(f, (response, route, verb) =>
        route.endsWith('.csv') && response.status === 200 && verb === method
          ? { ...response, headers: { ...response.headers, [header]: value } } : response) }), message);
    }
  }
});

test('unknown study, report, asset and private routes must return the exported 404 rather than 200 fallbacks', async t => {
  const f = await fixture(t);
  const result = await checkPreview(f.options);
  for (const item of result.checks.filter(check => check.status === 404)) {
    await assert.rejects(checkPreview({ ...f.options, transport: alterTransport(f, (response, route) =>
      route === item.path ? { ...response, status: 200 } : response) }), /Expected 404/);
    await assert.rejects(checkPreview({ ...f.options, transport: alterTransport(f, (response, route, method) =>
      route === item.path && method === 'GET' ? { ...response, bytes: Buffer.from('wrong 404') } : response) }), /bytes differ/);
  }
});

test('redirect status, redirect metadata and a changed response URL fail closed', async t => {
  const f = await fixture(t);
  for (const alter of [response => ({ ...response, status: 302 }),
    response => ({ ...response, redirected: true }),
    response => ({ ...response, url: 'https://external.invalid/' })]) {
    await assert.rejects(checkPreview({ ...f.options, transport: alterTransport(f, alter) }), /Expected 200|redirect rejected/);
  }
});

test('invalid cases, selected hashes and export file boundaries fail before transport', async t => {
  const f = await fixture(t);
  await assert.rejects(checkPreview({ ...f.options, transport: undefined }), /explicit transport/);
  for (const pageRoutes of [['/', '/reports/unselected/'], ['/', '/'], Array(8).fill('/')]) {
    await assert.rejects(checkPreview({ ...f.options, pageRoutes }), /not selected|unique|one to seven/);
  }
  const changed = structuredClone(f.options.bundles);
  changed[0].report.downloads[0].sha256 = 'a'.repeat(64);
  await assert.rejects(checkPreview({ ...f.options, bundles: changed }), /hashes must match/);
  const file = resolve(f.options.staticRoot, 'publications/featured/figures/chart.png');
  await writeFile(file, 'changed selected figure');
  await assert.rejects(checkPreview(f.options), /selected hash/);
  await rm(file);
  await mkdir(file);
  await assert.rejects(checkPreview(f.options), /regular exported file/);
  await rm(file, { recursive: true });
  await symlink(resolve(f.options.staticRoot, '404.html'), file);
  await assert.rejects(checkPreview(f.options), /symlink/);
  assert.equal(f.requests.length, 0);
});

test('a supplied local fixture server transport checks actual HTTP and rejects redirects', async t => {
  const f = await fixture(t);
  let redirect = false;
  const server = createServer(async (request, response) => {
    if (redirect) {
      response.writeHead(302, { Location: '/redirected-local-route/' }).end();
      return;
    }
    const result = await f.options.transport(`${origin}${request.url}`, { method: request.method });
    response.writeHead(result.status, result.headers).end(result.bytes);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve())));
  const localOrigin = `http://127.0.0.1:${server.address().port}`;
  const transport = async (url, options) => {
    const response = await fetch(url, options);
    return { status: response.status, headers: Object.fromEntries(response.headers),
      bytes: Buffer.from(await response.arrayBuffer()), url: response.url, redirected: response.redirected };
  };
  const result = await checkPreview({ ...f.options, origin: localOrigin, transport });
  assert.equal(result.requestsChecked, 22);
  redirect = true;
  await assert.rejects(checkPreview({ ...f.options, origin: localOrigin, transport }), /fetch failed/);
});
