import assert from 'node:assert/strict';
import { studyPublicationReferences } from './study-selections.mjs';
import { createHash } from 'node:crypto';
import { lstat, readFile, realpath } from 'node:fs/promises';
import { basename, extname, relative, resolve, sep } from 'node:path';

// Verification cases, not an authored catalog or a release-source mapping.
export const REPRESENTATIVE_PAGE_ROUTES = Object.freeze([
  '/',
  '/studies/countertrend-bar-continuation/',
  '/reports/08-countertrend-bar-continuation-20261006-web-r2/',
  '/reports/08-countertrend-bar-continuation-20261006-web/',
  '/reports/01-reversal-follow-through-20261006-web/',
  '/reports/camarilla-ema-20261008t220932z-cb2711/',
  '/reports/nq-amd-source-review-20261007-references/',
]);

export function validatePreviewOrigin(value) {
  assert(typeof value === 'string' && !/[\s\\]/u.test(value), 'Preview origin must be a clean loopback HTTP origin.');
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error('Preview origin must be a valid loopback HTTP origin.');
  }
  assert(url.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname),
    'Preview origin must use loopback HTTP.');
  assert(!url.username && !url.password && !url.search && !url.hash && url.pathname === '/' && url.origin === value,
    'Preview origin must contain only an origin, without credentials, paths, queries or fragments.');
  return url.origin;
}

const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const mediaTypes = {
  '.html': 'text/html',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.csv': 'text/csv',
};

function smokeCases(catalog, bundles, pageRoutes) {
  assert(Array.isArray(pageRoutes) && pageRoutes.length > 0 && pageRoutes.length <= 7,
    'Preview smoke requires one to seven explicit page routes.');
  assert(new Set(pageRoutes).size === pageRoutes.length, 'Preview page routes must be unique.');
  const selectedIds = new Set(catalog.studies.flatMap(study => studyPublicationReferences(study).map(reference => reference.publicationId)));
  const selected = bundles.filter(bundle => selectedIds.has(bundle.report.id));
  const knownPages = new Set([
    '/',
    ...catalog.studies.map(study => `/studies/${study.slug}/`),
    ...selected.map(bundle => `/reports/${bundle.report.id}/`),
  ]);
  for (const route of pageRoutes) {
    assert(knownPages.has(route), `Preview case is not selected by the app catalog and bundles: ${route}`);
  }
  const reports = pageRoutes.flatMap(route => selected.filter(bundle => route === `/reports/${bundle.report.id}/`));
  assert(reports.length > 0, 'Preview smoke requires an explicit selected report route.');
  const figureBundle = reports.find(bundle => bundle.report.sections.some(section => section.kind === 'figure'));
  const downloadBundle = reports.find(bundle => (bundle.report.downloads ?? []).length > 0);
  assert(figureBundle && downloadBundle, 'Preview cases must include a selected raster figure and CSV.');
  const figure = figureBundle.report.sections.find(section => section.kind === 'figure');
  const figurePin = figureBundle.provenance.assets.find(asset => asset.path === figure.path);
  const download = downloadBundle.report.downloads[0];
  const downloadPin = downloadBundle.provenance.assets.find(asset => asset.path === download.path);
  assert(/^[a-f0-9]{64}$/u.test(figurePin?.sha256 ?? ''), 'Selected figure must have a valid bundle hash.');
  assert(/^[a-f0-9]{64}$/u.test(download.sha256 ?? '') && downloadPin?.sha256 === download.sha256,
    'Selected CSV declaration and bundle hashes must match.');
  const cases = pageRoutes.map(path => ({ path, file: path === '/' ? 'index.html' : `${path.slice(1)}index.html` }));
  cases.push(
    { path: `/publications/${reports[0].report.id}/report.json`, file: `publications/${reports[0].report.id}/report.json` },
    { path: `/publications/${figureBundle.report.id}/${figure.path}`, file: `publications/${figureBundle.report.id}/${figure.path}`, sha256: figurePin.sha256 },
    { path: `/publications/${downloadBundle.report.id}/${download.path}`, file: `publications/${downloadBundle.report.id}/${download.path}`, sha256: download.sha256 },
  );
  const missing = [
    '/studies/narada-smoke-missing/',
    '/reports/narada-smoke-missing/',
    `/publications/${reports[0].report.id}/downloads/narada-smoke-missing.csv`,
    '/runs/narada-smoke-private/manifest.json',
  ];
  assert(!missing.some(path => knownPages.has(path)), 'Unknown-route smoke case has become an authored route.');
  return { cases, missing };
}

async function exportedBytes(root, file) {
  const target = resolve(root, file);
  const locator = relative(root, target);
  assert(locator && locator !== '..' && !locator.startsWith(`..${sep}`), 'Preview case escapes the static export.');
  let current = root;
  for (const segment of locator.split(sep)) {
    current = resolve(current, segment);
    assert(!(await lstat(current)).isSymbolicLink(), `Preview export contains a symlink: ${file}`);
  }
  assert((await lstat(target)).isFile(), `Preview case must identify a regular exported file: ${file}`);
  return readFile(target);
}

function responseHeaders(response) {
  return new Map(Object.entries(response.headers).map(([name, value]) => [name.toLowerCase(), value]));
}

function checkHeaders(response, expectedType, filename, path) {
  const headers = responseHeaders(response);
  assert(headers.get('content-type')?.split(';')[0].trim().toLowerCase() === expectedType,
    `Unexpected media type for ${path}.`);
  if (filename) {
    assert(headers.get('content-disposition') === `attachment; filename="${filename}"`,
      `CSV attachment filename differs for ${path}.`);
    assert(headers.get('x-content-type-options')?.toLowerCase() === 'nosniff',
      `CSV nosniff header missing for ${path}.`);
  }
}

// The caller supplies transport explicitly. Tests never acquire a network default.
export async function checkPreview({ origin, staticRoot, catalog, bundles, transport, pageRoutes = REPRESENTATIVE_PAGE_ROUTES }) {
  const cleanOrigin = validatePreviewOrigin(origin);
  assert(typeof transport === 'function', 'Preview smoke requires an explicit transport.');
  const { cases, missing } = smokeCases(catalog, bundles, pageRoutes);
  const rootInfo = await lstat(staticRoot);
  assert(rootInfo.isDirectory() && !rootInfo.isSymbolicLink(), 'Preview static root must be a real directory.');
  const root = await realpath(staticRoot);
  const prepared = [];
  for (const item of cases) {
    const bytes = await exportedBytes(root, item.file);
    const digest = sha256(bytes);
    assert(!item.sha256 || digest === item.sha256, `Exported asset differs from its selected hash: ${item.path}`);
    const contentType = mediaTypes[extname(item.file)];
    assert(contentType, `Unsupported preview smoke media type: ${item.file}`);
    prepared.push({ ...item, bytes, digest, contentType, status: 200 });
  }
  const notFound = await exportedBytes(root, '404.html');
  for (const path of missing) {
    prepared.push({ path, bytes: notFound, digest: sha256(notFound), contentType: 'text/html', status: 404 });
  }
  const checks = [];
  for (const item of prepared) {
    const url = `${cleanOrigin}${item.path}`;
    const filename = item.status === 200 && item.file.endsWith('.csv') ? basename(item.file) : null;
    for (const method of ['GET', 'HEAD']) {
      const response = await transport(url, { method, redirect: 'error' });
      assert(!response.redirected && (!response.url || response.url === url), `Preview redirect rejected for ${item.path}.`);
      assert(response.status === item.status, `Expected ${item.status} for ${method} ${item.path}; got ${response.status}.`);
      checkHeaders(response, item.contentType, filename, item.path);
      assert(Buffer.isBuffer(response.bytes), 'Preview transport must return response bytes as a Buffer.');
      if (method === 'HEAD') {
        assert(response.bytes.length === 0, `HEAD returned a body for ${item.path}.`);
      } else {
        assert(response.bytes.equals(item.bytes), `Preview bytes differ from the static export: ${item.path}`);
      }
    }
    checks.push({ path: item.path, status: item.status, sha256: item.digest, contentType: item.contentType });
  }
  return { origin: cleanOrigin, pagesChecked: pageRoutes.length, filesChecked: cases.length,
    notFoundChecked: missing.length, requestsChecked: prepared.length * 2, checks };
}
