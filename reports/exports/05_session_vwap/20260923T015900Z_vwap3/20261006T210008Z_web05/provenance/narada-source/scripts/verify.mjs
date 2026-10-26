import { readdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { DEFAULT_OUTPUT_ROOT, verifyPublications } from './lib/publication.mjs';
try {
  const entries=await readdir(dirname(DEFAULT_OUTPUT_ROOT),{withFileTypes:true});
  if(entries.length!==1 || entries[0].name!=='publications' || !entries[0].isDirectory() || entries[0].isSymbolicLink()) throw new Error('Public directory must contain only the publications directory; unexpected public files would be deployed.');
  const result=await verifyPublications(); console.log(`Verified ${result.reports} publications and ${result.assets} raster assets.`);
} catch(error) { console.error(error.message); process.exitCode=1; }
