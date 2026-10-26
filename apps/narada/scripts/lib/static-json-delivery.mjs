import assert from 'node:assert/strict';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { lstat, open, realpath } from 'node:fs/promises';
import { isAbsolute, relative, resolve, sep } from 'node:path';
import {
  BUNDLE_MAX_BYTES, DEFAULT_OUTPUT_ROOT, FILTERED_BUNDLE_MAX_BYTES,
  INDEX_MAX_BYTES, hasFilteredTables, validateBundle, validateIndex,
} from './publication.mjs';

const defaultExportRoot = resolve(import.meta.dirname, '../../out/publications');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const pretty = value => Buffer.from(`${JSON.stringify(value, null, 2)}\n`);

// The publisher's original spelling is required before parsing can be used as a
// lossless delivery transform. This also refuses duplicate keys, non-finite
// numeric literals, negative zero and invalid UTF-8 instead of normalizing them.
export function staticPublicationDeliveryBytes(canonicalBytes) {
  assert(Buffer.isBuffer(canonicalBytes), 'Canonical publication bytes must be a Buffer.');
  const value = JSON.parse(canonicalBytes.toString('utf8'));
  assert(canonicalBytes.equals(pretty(value)), 'Canonical publication must retain its publisher JSON serialization.');
  const delivery = Buffer.from(JSON.stringify(value));
  assert.deepEqual(JSON.parse(delivery.toString('utf8')), value, 'Static JSON delivery changed a publication value.');
  return delivery;
}

function contained(parent, child) {
  const path = relative(parent, child);
  return path === '' || (!isAbsolute(path) && path !== '..' && !path.startsWith(`..${sep}`));
}

async function directory(path) {
  const info = await lstat(path);
  assert(info.isDirectory() && !info.isSymbolicLink(), `Static JSON directory must be real, without symlinks: ${path}`);
  assert(await realpath(path) === path, `Static JSON directory ancestors must not be symlinks: ${path}`);
}

async function reportPath(root, id) {
  // IDs are checked by the strict publication index, independently of joins.
  assert(typeof id === 'string' && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id) && id.length <= 80, 'Invalid static publication ID.');
  await directory(root);
  const folder = resolve(root, id);
  assert(contained(root, folder), 'Static publication path escapes its root.');
  await directory(folder);
  return resolve(folder, 'report.json');
}

async function boundedRead(handle, budget, path) {
  const info = await handle.stat();
  assert(info.isFile(), `Static JSON must be a regular file: ${path}`);
  assert(info.size <= budget, `Static JSON exceeds its byte budget: ${path}`);
  // Read at most one byte beyond the limit even if a file grows after stat.
  const buffer = Buffer.alloc(budget + 1);
  let length = 0;
  while (length < buffer.length) {
    const { bytesRead } = await handle.read(buffer, length, buffer.length - length, length);
    if (bytesRead === 0) break;
    length += bytesRead;
  }
  assert(length <= budget, `Static JSON exceeds its byte budget: ${path}`);
  return { bytes: buffer.subarray(0, length), info };
}

async function readFile(path, budget) {
  const info = await lstat(path);
  assert(info.isFile() && !info.isSymbolicLink(), `Static JSON must be a regular file without symlinks: ${path}`);
  const handle = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    return await boundedRead(handle, budget, path);
  } finally {
    await handle.close();
  }
}

async function inspect({ canonicalRoot = DEFAULT_OUTPUT_ROOT, exportRoot = defaultExportRoot } = {}, requireCompact) {
  canonicalRoot = resolve(canonicalRoot);
  exportRoot = resolve(exportRoot);
  assert(!contained(canonicalRoot, exportRoot) && !contained(exportRoot, canonicalRoot), 'Canonical and static JSON roots must be disjoint.');
  await directory(canonicalRoot);
  await directory(exportRoot);
  const canonicalIndex = await readFile(resolve(canonicalRoot, 'index.json'), INDEX_MAX_BYTES);
  const index = validateIndex(JSON.parse(canonicalIndex.bytes.toString('utf8')));
  const exportedIndex = await readFile(resolve(exportRoot, 'index.json'), INDEX_MAX_BYTES);
  assert(exportedIndex.bytes.equals(canonicalIndex.bytes), 'Static publication index differs from the canonical index.');

  const files = [];
  const plans = [];
  let sourceBytes = 0;
  let deliveryBytes = 0;
  for (const entry of index.reports) {
    const sourcePath = await reportPath(canonicalRoot, entry.id);
    const targetPath = await reportPath(exportRoot, entry.id);
    const source = await readFile(sourcePath, FILTERED_BUNDLE_MAX_BYTES);
    const compact = staticPublicationDeliveryBytes(source.bytes);
    const bundle = validateBundle(JSON.parse(source.bytes.toString('utf8')));
    const budget = hasFilteredTables(bundle.report) ? FILTERED_BUNDLE_MAX_BYTES : BUNDLE_MAX_BYTES;
    assert(source.bytes.length <= budget, `Canonical publication exceeds its bundle byte budget: ${entry.id}`);
    const { id, title, summary, publishedAt, source: attribution } = bundle.report;
    assert.deepEqual(entry, { id, title, summary, publishedAt, source: attribution,
      href: `/reports/${id}/`, sourceSha256: bundle.provenance.sourceSha256 }, 'Static publication index does not match its canonical report.');
    assert(id === entry.id, 'Canonical publication ID differs from its selected directory.');
    const target = await readFile(targetPath, budget);
    assert(target.info.nlink === 1 && !(target.info.dev === source.info.dev && target.info.ino === source.info.ino), 'Static publication output must not be hard-linked to canonical or other files.');
    assert.deepEqual(JSON.parse(target.bytes.toString('utf8')), bundle, `Static publication values differ from canonical: ${id}`);
    if (requireCompact) {
      assert(target.bytes.equals(compact), `Static publication JSON is not the exact compact delivery: ${id}`);
    }
    sourceBytes += source.bytes.length;
    deliveryBytes += compact.length;
    const deliverySha256 = hash(compact);
    files.push({ id, path: `publications/${id}/report.json`, canonicalBytes: source.bytes.length,
      canonicalSha256: hash(source.bytes), deliveryBytes: compact.length, deliverySha256 });
    if (!target.bytes.equals(compact)) {
      plans.push({ id, targetPath, compact, originalSha256: hash(target.bytes), info: target.info });
    }
  }
  return {
    receipt: { format: 'abacus.static-json-delivery/v1', reports: files.length,
      changed: plans.length, sourceBytes, deliveryBytes, savedBytes: sourceBytes - deliveryBytes, files },
    plans, exportRoot,
  };
}

export async function compactStaticPublicationJson(options = {}) {
  // Preflight every selected report before touching any exported bytes. Only
  // existing report.json files are rewritten; canonical bundles and assets stay
  // untouched, and no temp files or extra public artifacts are introduced.
  const { receipt, plans, exportRoot } = await inspect(options, false);
  for (const plan of plans) {
    const path = await reportPath(exportRoot, plan.id);
    assert(path === plan.targetPath, 'Static JSON output path changed.');
    const handle = await open(path, constants.O_RDWR | constants.O_NOFOLLOW);
    try {
      const current = await boundedRead(handle, FILTERED_BUNDLE_MAX_BYTES, path);
      assert(current.info.nlink === 1 && current.info.ino === plan.info.ino && current.info.dev === plan.info.dev,
        'Static publication output identity changed during compaction.');
      assert(hash(current.bytes) === plan.originalSha256, 'Static publication bytes changed during compaction.');
      // Reads above use explicit offsets and leave this handle at position zero.
      await handle.writeFile(plan.compact);
      await handle.truncate(plan.compact.length);
    } finally {
      await handle.close();
    }
  }
  return receipt;
}

export async function verifyStaticPublicationJson(options = {}) {
  return (await inspect(options, true)).receipt;
}
