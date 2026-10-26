import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { auditSources } from './audit-release-sources.mjs';
import { verifyPublications } from './lib/publication.mjs';
import { readStudyCatalog } from './lib/studies.mjs';

try {
  const publications = await verifyPublications();
  const catalog = await readStudyCatalog(publications.bundles.map(bundle => bundle.report));
  const mapping = JSON.parse(await readFile(resolve('content/release-sources.json'), 'utf8'));
  const result = await auditSources(resolve('../..'), mapping, publications.bundles, catalog);
  console.log(`Source audit passed: ${result.publications.length} publications, ${result.hashedFiles.length} hashed files.`);
  console.log(result.limitation);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
