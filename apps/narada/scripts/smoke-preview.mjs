import { resolve } from 'node:path';
import { verifyPublications } from './lib/publication.mjs';
import { readStudyCatalog } from './lib/studies.mjs';
import { checkPreview, validatePreviewOrigin } from './lib/preview-smoke.mjs';

try {
  const args = process.argv.slice(2);
  if (args.length !== 2 || args[0] !== '--origin') {
    throw new Error('Usage: node scripts/smoke-preview.mjs --origin http://127.0.0.1:4173');
  }
  const origin = validatePreviewOrigin(args[1]);
  const { bundles } = await verifyPublications();
  const catalog = await readStudyCatalog(bundles.map(bundle => bundle.report));
  const transport = async (url, options) => {
    const response = await fetch(url, { ...options, signal: AbortSignal.timeout(15000) });
    return { status: response.status, headers: Object.fromEntries(response.headers),
      bytes: Buffer.from(await response.arrayBuffer()), url: response.url, redirected: response.redirected };
  };
  const result = await checkPreview({ origin, staticRoot: resolve(import.meta.dirname, '../out'),
    catalog, bundles, transport });
  console.log(`Verified local preview: ${result.pagesChecked} pages, ${result.filesChecked} exported files, ${result.notFoundChecked} real 404s and ${result.requestsChecked} GET/HEAD requests at ${result.origin}.`);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
