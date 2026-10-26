import { readFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';

export async function requireGate(ctx, name, url) {
  const records = await readdir(resolve(ctx.record, 'events'));
  for (const path of records.filter(path => path.endsWith(`-${name}.json`))) {
    const gate = JSON.parse(await readFile(resolve(ctx.record, 'events', path), 'utf8'));
    if (
      gate.result === 'passed' &&
      gate.artifactSha256 === ctx.release.artifactSha256 &&
      (!url || gate.origin === url)
    ) {
      return;
    }
  }
  throw new Error(`Required ${name} gate missing for this exact release/deployment.`);
}
