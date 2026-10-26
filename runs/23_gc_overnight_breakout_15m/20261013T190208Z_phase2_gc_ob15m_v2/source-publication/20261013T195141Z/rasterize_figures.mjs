// Rasterize authored SVG presentation files; no analytical code or inputs.
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { readFile, writeFile } from 'node:fs/promises';

const [packageRoot, inventoryPath] = process.argv.slice(2);
if (!packageRoot || !inventoryPath) throw new Error('Expected bundled Node package root and figure inventory.');
const require = createRequire(resolve(packageRoot, 'package.json'));
const sharp = require('sharp');
const files = JSON.parse(await readFile(inventoryPath, 'utf8'));
for (const file of files) {
  await sharp(file.svg).png().toFile(file.png);
}
await writeFile(`${inventoryPath}.runtime.json`, JSON.stringify({
  node: process.version, sharp: sharp.versions,
  role: 'SVG-to-PNG rendering only; no research statistics calculated',
}, null, 2) + '\n');
