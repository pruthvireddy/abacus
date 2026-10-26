import Ajv2020 from 'ajv/dist/2020.js';
import { createHash, randomUUID } from 'node:crypto';
import { readFile, writeFile, mkdir, rename, rm, lstat, readdir, realpath, open } from 'node:fs/promises';
import { dirname, resolve, relative, sep, basename } from 'node:path';
import { validateCsv, validateReferenceUrl } from './evidence.mjs';
export const REPORT_MAX_BYTES = 96 * 1024;
export const BUNDLE_MAX_BYTES = 192 * 1024;
export const INDEX_MAX_BYTES = 256 * 1024;
export const ASSET_MAX_BYTES = 2 * 1024 * 1024;
export const TOTAL_ASSET_MAX_BYTES = 8 * 1024 * 1024;
export const DOWNLOAD_MAX_BYTES = 256 * 1024;
export const TOTAL_DOWNLOAD_MAX_BYTES = 512 * 1024;
export const FILTERED_REPORT_MAX_BYTES = 2 * 1024 * 1024;
export const FILTERED_BUNDLE_MAX_BYTES = 4 * 1024 * 1024;
export const FILTERED_DOWNLOAD_MAX_BYTES = 4 * 1024 * 1024;
export const FILTERED_TOTAL_DOWNLOAD_MAX_BYTES = 8 * 1024 * 1024;
export const hasFilteredTables = report => report.sections.some(section => section.kind === 'table' && section.rowFilters?.length);
const reportLimits = report => hasFilteredTables(report)
  ? { source: FILTERED_REPORT_MAX_BYTES, bundle: FILTERED_BUNDLE_MAX_BYTES, download: FILTERED_DOWNLOAD_MAX_BYTES, totalDownloads: FILTERED_TOTAL_DOWNLOAD_MAX_BYTES, csvRows: 15000 }
  : { source: REPORT_MAX_BYTES, bundle: BUNDLE_MAX_BYTES, download: DOWNLOAD_MAX_BYTES, totalDownloads: TOTAL_DOWNLOAD_MAX_BYTES, csvRows: 1000 };
const appRoot = resolve(import.meta.dirname, '../..');
export const DEFAULT_OUTPUT_ROOT = resolve(appRoot, 'public/publications');
const ajv = new Ajv2020({ allErrors: true, strict: true, allowUnionTypes: true });
const schemas = await Promise.all(['report', 'bundle', 'index', 'report-1.0', 'report-1.1'].map(async (name) => JSON.parse(await readFile(resolve(appRoot, `contracts/${name}.schema.json`), 'utf8'))));
for (const schema of schemas) {
  ajv.addSchema(schema);
}
const validators = schemas.map(schema => ajv.getSchema(schema.$id));
function assert(ok, message) {
  if (!ok) {
    throw new Error(message);
  }
}
function schemaCheck(validator, value, label) {
  assert(validator(value), `${label} does not match its schema: ${ajv.errorsText(validator.errors)}`);
  return value;
}
export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
function stable(value) {
  return Array.isArray(value) ? value.map(stable) : value !== null && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(k => [k, stable(value[k])])) : value;
}
const serialize = value => `${JSON.stringify(stable(value), null, 2)}\n`;
function unique(values, label) {
  assert(new Set(values).size === values.length, `${label} must be unique.`);
}
function validDate(value) {
  const normalized = value.includes('.') ? value : value.replace('Z', '.000Z');
  assert(Number.isFinite(Date.parse(value)) && new Date(value).toISOString() === normalized, 'publishedAt must be a valid UTC ISO date.');
}
export function validateReport(value) {
  schemaCheck(validators[0], value, 'Report');
  validDate(value.publishedAt);
  unique(value.sections.map(s => s.id), 'Section IDs');
  const patterns = value.patterns ?? [];
  unique(patterns.map(pattern => pattern.id), 'Pattern IDs');
  if (value.patternOverviewId !== undefined) {
    assert(patterns.some(pattern => pattern.id === value.patternOverviewId), `Unknown overview pattern: ${value.patternOverviewId}`);
  }
  for (const pattern of patterns) {
    unique(pattern.variants.map(variant => variant.id), `Pattern ${pattern.id} variant IDs`);
    for (const variant of pattern.variants) {
      unique(variant.candles.map(candle => candle.id), `Pattern ${pattern.id} candle IDs`);
      for (const candle of variant.candles) {
        assert(candle.low <= Math.min(candle.open, candle.close) && candle.high >= Math.max(candle.open, candle.close),
          `Pattern ${pattern.id} has invalid OHLC ordering.`);
      }
      for (const mark of variant.marks ?? []) {
        const start = variant.candles.findIndex(candle => candle.id === mark.startCandle);
        const end = variant.candles.findIndex(candle => candle.id === mark.endCandle);
        assert(start >= 0 && end >= start, `Pattern ${pattern.id} marks require ordered candle references.`);
        if (mark.kind === 'band') {
          assert(mark.low < mark.high, `Pattern ${pattern.id} bands require low below high.`);
        }
      }
    }
  }
  const references = value.references ?? [];
  unique(references.map(r => r.id), 'Reference IDs');
  for (const ref of references) {
    if (ref.kind === 'external') {
      validateReferenceUrl(ref.url);
      for (const key of ['publishedOn', 'accessedOn']) {
        if (ref[key]) {
          validDate(`${ref[key]}T00:00:00Z`);
        }
      }
      assert(ref.endSeconds === undefined || ref.startSeconds !== undefined && ref.endSeconds >= ref.startSeconds, 'Reference end time requires an ordered start time.');
    }
    else {
      assert(ref.runId === value.source.runId, 'Saved reference must identify this publication source run.');
    }
  }
  for (const section of value.sections) {
    if (section.patternId !== undefined) {
      assert(patterns.some(pattern => pattern.id === section.patternId), `Unknown section pattern: ${section.patternId}`);
    }
    for (const id of section.referenceIds ?? []) {
      assert(references.some(r => r.id === id), `Unknown section reference: ${id}`);
    }
    if (value.schemaVersion === '1.1') {
      assert(!['publication-references', 'publication-downloads'].includes(section.id), 'Section ID is reserved for publication evidence.');
    }
  }
  const downloads = value.downloads ?? [];
  const limits = reportLimits(value);
  unique(downloads.map(d => d.id), 'Download IDs');
  unique(downloads.map(d => d.path), 'Download paths');
  for (const download of downloads) {
    assert(download.source.runId === value.source.runId, 'Download provenance must identify this publication source run.');
    assert(download.rowCount <= limits.csvRows, `CSV exceeds ${limits.csvRows} data rows for this report.`);
  }
  for (const section of value.sections) {
    if (section.kind === 'table') {
      const keys = section.columns.map(c => c.key);
      unique(keys, 'Table column keys');
      unique((section.rowFilters ?? []).map(filter => filter.key), 'Table row filter keys');
      for (const filter of section.rowFilters ?? []) {
        assert(keys.includes(filter.key), `Table ${section.id} row filter must select a declared column.`);
        assert(filter.label.trim() === filter.label && filter.label.length > 0, 'Table row filter labels must be nonblank.');
        if (Object.hasOwn(filter, 'defaultValue')) {
          assert(section.rows.some(row => (Object.hasOwn(row, filter.key) ? row[filter.key] ?? null : null) === filter.defaultValue),
            `Table ${section.id} row filter default must name a saved value.`);
        }
      }
      for (const row of section.rows) {
        assert(Object.keys(row).every(k => keys.includes(k)), `Table ${section.id} contains an undeclared row field.`);
        for (const column of section.columns) {
          if (column.format && row[column.key] !== undefined && row[column.key] !== null) {
            assert(typeof row[column.key] === 'number', `Formatted column ${column.key} requires numeric or null values.`);
          }
        }
      }
    }
  }
  return value;
}
const figurePaths = report => [...new Set(report.sections.filter(s => s.kind === 'figure').map(s => s.path))].sort();
const assetPaths = report => [...figurePaths(report), ...(report.downloads ?? []).map(d => d.path)].sort();
export function validateBundle(value) {
  schemaCheck(validators[1], value, 'Publication bundle');
  validateReport(value.report);
  assert(value.provenance.sourceSha256 === sha256(serialize(value.report)), 'Report content does not match its source hash.');
  unique(value.provenance.assets.map(a => a.path), 'Asset paths');
  assert(JSON.stringify(value.provenance.assets.map(a => a.path).sort()) === JSON.stringify(assetPaths(value.report)), 'Asset manifest must exactly match selected figures and downloads.');
  for (const download of value.report.downloads ?? []) {
    assert(value.provenance.assets.find(a => a.path === download.path)?.sha256 === download.sha256, 'Download hash disagrees with its provenance.');
  }
  return value;
}
export function validateIndex(value) {
  schemaCheck(validators[2], value, 'Publication index');
  unique(value.reports.map(r => r.id), 'Report IDs');
  for (const entry of value.reports) {
    validDate(entry.publishedAt);
    assert(entry.href === `/reports/${entry.id}/`, 'Index href must match its report ID.');
  }
  return value;
}
async function exists(path) {
  try {
    await lstat(path);
    return true;
  }
  catch (error) {
    if (error.code === 'ENOENT') {
      return false;
    }
    throw error;
  }
}
async function readBounded(path, budget) {
  const info = await lstat(path);
  assert(info.isFile() && !info.isSymbolicLink(), `Expected a regular file: ${path}`);
  assert(info.size <= budget, `File exceeds ${budget}-byte budget: ${path}`);
  const bytes = await readFile(path);
  assert(bytes.length <= budget, `File exceeds byte budget: ${path}`);
  return bytes;
}
async function readJson(path, budget) {
  return JSON.parse((await readBounded(path, budget)).toString('utf8'));
}
async function safeAsset(root, path, download, limits) {
  const base = await realpath(root);
  const target = resolve(base, path);
  const rel = relative(base, target);
  assert(rel && rel !== '..' && !rel.startsWith(`..${sep}`), 'Figure path escapes its source directory.');
  let current = base;
  for (const part of rel.split(sep)) {
    current = resolve(current, part);
    assert(!(await lstat(current)).isSymbolicLink(), `Figure symlinks are not permitted: ${path}`);
  }
  const actual = await realpath(target);
  assert(actual === target, `Figure path escapes its source directory: ${path}`);
  const bytes = await readBounded(actual, download ? limits.download : ASSET_MAX_BYTES);
  if (download) {
    assert(sha256(bytes) === download.sha256, `Download hash disagrees with its declaration: ${path}`);
    validateCsv(bytes, download, limits.csvRows);
  }
  else {
    assertImage(bytes, path);
  }
  return bytes;
}
function assertImage(bytes, path) {
  const ext = path.split('.').at(-1);
  let ok = false;
  if (ext === 'png') {
    ok = bytes.length >= 24 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && bytes.toString('ascii', 12, 16) === 'IHDR';
  }
  if (ext === 'jpg' || ext === 'jpeg') {
    ok = bytes.length >= 4 && bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255 && bytes.at(-2) === 255 && bytes.at(-1) === 217;
  }
  if (ext === 'webp') {
    ok = bytes.length >= 16 && bytes.toString('ascii', 0, 4) === 'RIFF' && bytes.toString('ascii', 8, 12) === 'WEBP' && bytes.readUInt32LE(4) + 8 === bytes.length;
  }
  assert(ok, `Figure signature does not match its raster extension: ${path}`);
}
async function walk(root, prefix = '') {
  const files = [];
  for (const entry of await readdir(root, { withFileTypes: true })) {
    const path = prefix ? `${prefix}/${entry.name}` : entry.name;
    assert(!entry.isSymbolicLink(), `Publication symlink is forbidden: ${path}`);
    if (entry.isDirectory()) {
      const children = await walk(resolve(root, entry.name), path);
      assert(children.length, `Empty publication directory is not permitted: ${path}`);
      files.push(...children);
    }
    else {
      assert(entry.isFile(), `Unsupported publication entry: ${path}`);
      files.push(path);
    }
  }
  return files.sort();
}
function entryFor(bundle) {
  const { id, title, summary, publishedAt, source } = bundle.report;
  return { id, title, summary, publishedAt, source, href: `/reports/${id}/`, sourceSha256: bundle.provenance.sourceSha256 };
}
function indexFor(bundles) {
  return { schemaVersion: '1.0', reports: bundles.map(entryFor).sort((a, b) => Date.parse(b.publishedAt) - Date.parse(a.publishedAt) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)) };
}
export async function readPublicationIndex(root = DEFAULT_OUTPUT_ROOT) {
  return validateIndex(await readJson(resolve(root, 'index.json'), INDEX_MAX_BYTES));
}
export async function readPublication(root, id) {
  assert(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id), 'Invalid publication ID.');
  const dir = resolve(root, id);
  const info = await lstat(dir);
  assert(info.isDirectory() && !info.isSymbolicLink(), 'Publication must be a real directory.');
  const bundleBytes = await readBounded(resolve(dir, 'report.json'), FILTERED_BUNDLE_MAX_BYTES);
  const bundle = validateBundle(JSON.parse(bundleBytes.toString('utf8')));
  const limits = reportLimits(bundle.report);
  assert(bundleBytes.length <= limits.bundle, 'Publication bundle exceeds byte budget.');
  assert(bundle.report.id === id, 'Bundle ID does not match its directory.');
  let total = 0, downloadTotal = 0;
  for (const asset of bundle.provenance.assets) {
    const download = bundle.report.downloads?.find(d => d.path === asset.path);
    const bytes = await safeAsset(dir, asset.path, download, limits);
    if (download) {
      downloadTotal += bytes.length;
    }
    else {
      total += bytes.length;
    }
    assert(sha256(bytes) === asset.sha256, `Modified asset: ${id}/${asset.path}`);
  }
  assert(total <= TOTAL_ASSET_MAX_BYTES, 'Publication exceeds total figure byte budget.');
  assert(downloadTotal <= limits.totalDownloads, 'Publication exceeds total download byte budget.');
  return bundle;
}
export async function verifyPublications(root = DEFAULT_OUTPUT_ROOT) {
  const rootInfo = await lstat(root);
  assert(rootInfo.isDirectory() && !rootInfo.isSymbolicLink(), 'Publication root must be a real directory.');
  const index = await readPublicationIndex(root);
  const bundles = [];
  for (const entry of index.reports) {
    bundles.push(await readPublication(root, entry.id));
  }
  assert(serialize(index) === serialize(indexFor(bundles)), 'Publication index is stale or does not match its reports.');
  const expected = ['index.json', ...bundles.flatMap(b => [`${b.report.id}/report.json`, ...b.provenance.assets.map(a => `${b.report.id}/${a.path}`)])].sort();
  assert(JSON.stringify(await walk(root)) === JSON.stringify(expected), 'Publication tree contains stale or unselected files.');
  return { reports: bundles.length, assets: bundles.reduce((n, b) => n + figurePaths(b.report).length, 0), downloads: bundles.reduce((n, b) => n + (b.report.downloads?.length ?? 0), 0), bundles };
}
async function atomicJson(path, value, budget) {
  const bytes = Buffer.from(serialize(value));
  assert(bytes.length <= budget, `JSON exceeds ${budget}-byte budget.`);
  const temporary = resolve(dirname(path), `.${basename(path)}.${randomUUID()}.tmp`);
  try {
    await writeFile(temporary, bytes, { flag: 'wx' });
    await rename(temporary, path);
  }
  finally {
    await rm(temporary, { force: true });
  }
}
export async function publishReport({ reportPath, outputRoot = DEFAULT_OUTPUT_ROOT, dryRun = false }) {
  const input = resolve(reportPath);
  const sourceInfo = await lstat(dirname(input));
  assert(sourceInfo.isDirectory() && !sourceInfo.isSymbolicLink(), 'Publication source must be a real directory without symlinks.');
  const bytes = await readBounded(input, FILTERED_REPORT_MAX_BYTES);
  let parsed;
  try { parsed = JSON.parse(bytes.toString('utf8')); }
  catch (error) { assert(bytes.length <= REPORT_MAX_BYTES, 'Report source exceeds byte budget.'); throw error; }
  const report = validateReport(parsed);
  const limits = reportLimits(report);
  assert(bytes.length <= limits.source, 'Report source exceeds byte budget.');
  const assets = [];
  let total = 0, downloadTotal = 0;
  for (const path of assetPaths(report)) {
    const download = report.downloads?.find(d => d.path === path);
    const data = await safeAsset(dirname(input), path, download, limits);
    if (download) {
      downloadTotal += data.length;
    }
    else {
      total += data.length;
    }
    assets.push({ path, sha256: sha256(data), data });
  }
  assert(total <= TOTAL_ASSET_MAX_BYTES, 'Publication exceeds total figure byte budget.');
  assert(downloadTotal <= limits.totalDownloads, 'Publication exceeds total download byte budget.');
  const bundle = validateBundle({ report, provenance: { sourceSha256: sha256(serialize(report)), assets: assets.map(({ path, sha256 }) => ({ path, sha256 })) } });
  assert(Buffer.byteLength(serialize(bundle)) <= limits.bundle, 'Publication bundle exceeds byte budget.');
  const output = resolve(outputRoot);
  const inspect = async () => {
    if (!(await exists(output))) {
      return [];
    }
    const outputInfo = await lstat(output);
    assert(outputInfo.isDirectory() && !outputInfo.isSymbolicLink(), 'Publication root must be a real directory.');
    const entries = await readdir(output);
    if (!entries.length) {
      return [];
    }
    return (await verifyPublications(output)).bundles;
  };
  const assess = existing => {
    const previous = existing.find(b => b.report.id === report.id);
    assert(!previous || serialize(previous) === serialize(bundle), `Report ID "${report.id}" already has different content; use a new report ID.`);
    const index = validateIndex(indexFor(previous ? existing : [...existing, bundle]));
    assert(Buffer.byteLength(serialize(index)) <= INDEX_MAX_BYTES, 'Publication index exceeds byte budget.');
    return { previous, index };
  };
  if (dryRun) {
    const { previous } = assess(await inspect());
    return { id: report.id, status: previous ? 'unchanged' : 'ready', dryRun: true };
  }
  await mkdir(dirname(output), { recursive: true });
  const lockPath = resolve(dirname(output), `.${basename(output)}.publish.lock`);
  let lock;
  try {
    lock = await open(lockPath, 'wx');
  }
  catch (error) {
    if (error.code === 'EEXIST') {
      throw new Error(`Another publication is in progress (${lockPath}).`);
    }
    throw error;
  }
  const staging = resolve(dirname(output), `.narada-stage-${randomUUID()}`);
  const destination = resolve(output, report.id);
  let installed = false;
  let committed = false;
  try {
    const { previous, index } = assess(await inspect());
    if (previous) {
      return { id: report.id, status: 'unchanged', dryRun: false };
    }
    await mkdir(staging, { recursive: false });
    for (const asset of assets) {
      const target = resolve(staging, asset.path);
      await mkdir(dirname(target), { recursive: true });
      await writeFile(target, asset.data, { flag: 'wx' });
    }
    await atomicJson(resolve(staging, 'report.json'), bundle, limits.bundle);
    await mkdir(output, { recursive: true });
    await rename(staging, destination);
    installed = true;
    await atomicJson(resolve(output, 'index.json'), index, INDEX_MAX_BYTES);
    committed = true;
    return { id: report.id, status: 'published', dryRun: false };
  }
  finally {
    await rm(staging, { recursive: true, force: true });
    if (installed && !committed) {
      await rm(destination, { recursive: true, force: true });
    }
    await lock.close();
    await rm(lockPath, { force: true });
  }
}
