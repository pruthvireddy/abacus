import { createRequire } from 'node:module';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const args = process.argv.slice(2);
const revision = args[args.indexOf('--revision') + 1];
if (!/^[A-Za-z0-9_-]+$/.test(revision)) throw new Error('A safe revision ID is required.');
const root = args.includes('--workspace-root') ? resolve(args[args.indexOf('--workspace-root') + 1]) : resolve(fileURLToPath(new URL('../..', import.meta.url)));
const require = createRequire(resolve(root, 'apps/narada/package.json'));
const sharp = require('sharp');
const out = resolve(root, 'reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1', revision);
const jobs = JSON.parse(await readFile(resolve(out, 'provenance/figure-jobs.json'), 'utf8'));
for (const job of jobs) {
  const bytes = await sharp(await readFile(resolve(root, job.source)), { density: 144 }).resize({ width: 1800 }).flatten({ background: '#ffffff' }).png({ compressionLevel: 9 }).toBuffer();
  if (args.includes('--check')) {
    const current = await readFile(resolve(out, job.output));
    if (!bytes.equals(current)) throw new Error('Deterministic raster mismatch: ' + job.output);
  } else await writeFile(resolve(out, job.output), bytes, { flag: 'wx' });
  console.log(job.output + ' ' + bytes.length + ' bytes ' + createHash('sha256').update(bytes).digest('hex'));
}
