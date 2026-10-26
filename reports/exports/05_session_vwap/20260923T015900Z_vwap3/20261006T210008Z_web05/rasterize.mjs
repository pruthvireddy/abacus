import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
const root = resolve(import.meta.dirname, '../../../../..');
const require = createRequire(resolve(root, 'apps/narada/package.json'));
const sharp = require('sharp');
const source = await readFile(resolve(root, 'runs/05_session_vwap/20260923T015900Z_vwap3/figures/barrier-outcomes.svg'), 'utf8');
// The original right-edge denominator text extends beyond its 900px canvas.
// Preserve all series, text, positions and colors; extend only the white margin.
const svg = source.replace("width='900' height='250' viewBox='0 0 900 250'", "width='960' height='250' viewBox='0 0 960 250'")
  .replace("<rect width='900' height='250'", "<rect width='960' height='250'");
await writeFile(resolve(import.meta.dirname, 'provenance/barrier-outcomes.svg'), svg);
await sharp(Buffer.from(svg), { density: 144 }).png().toFile(resolve(import.meta.dirname, 'figures/barrier-outcomes.png'));
await writeFile(resolve(import.meta.dirname, 'provenance/rasterizer-versions.json'), JSON.stringify({ node: process.version, ...sharp.versions }, null, 2) + '\n');
console.log('Rasterized saved SVG at 1920×500 with its labels and unchanged plot geometry.');
