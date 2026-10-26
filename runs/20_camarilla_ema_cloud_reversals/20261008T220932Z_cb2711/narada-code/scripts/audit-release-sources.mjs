import assert from 'node:assert/strict';
import { readFile, lstat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { hash } from './lib/release.mjs';

// This private release audit follows explicit locators. The website build never
// imports this file or discovers research directories.
export async function auditSources(workspace, mapping, bundles, catalog) {
  assert(mapping.schemaVersion === '1.0' && Array.isArray(mapping.publications), 'Invalid release source map.');
  assert.deepEqual(mapping.publications.map(p=>p.publicationId).sort(), bundles.map(b=>b.report.id).sort(), 'Release source map must cover exactly the selected index.');
  const checked = new Map();
  async function check(path, sha256) {
    assert(!path.startsWith('/') && !path.split('/').includes('..'), 'Source locator must stay in the workspace.');
    let current = workspace;
    for (const part of path.split('/')) { current = resolve(current, part); assert(!(await lstat(current)).isSymbolicLink(), `Source symlink: ${path}`); }
    const info = await lstat(current); assert(info.isFile(), 'Source must be a regular file.');
    let actual = checked.get(path);
    if (!actual) { actual = hash(await readFile(current)); checked.set(path, actual); }
    if (sha256) assert.equal(actual, sha256, `Changed source/export: ${path}`);
    return actual;
  }
  const records = [];
  for (const selected of mapping.publications) {
    assert(/^reports\/exports\/[^/]+\/[^/]+\/[^/]+$/.test(selected.revision), 'Expected an explicit presentation revision.');
    const read = async name => JSON.parse(await readFile(resolve(workspace, selected.revision, name), 'utf8'));
    const manifest = await read('manifest.json'), report = await read('publication.json');
    const bundle = bundles.find(b=>b.report.id === selected.publicationId);
    assert.deepEqual(report, bundle.report, 'Presentation source differs from staged bundle.');
    assert.equal(manifest.publication_id, report.id); assert.equal(manifest.source_run_id, report.source.runId);
    const study = catalog.studies.find(s => s.featuredPublicationId === report.id || s.relatedPublications?.some(p=>p.publicationId === report.id));
    assert(study && study.studyId === manifest.study_id, 'Export study attribution mismatch.');
    for (const entry of manifest.source_artifacts) await check(entry.path, entry.sha256);
    // All retained revision outputs are immutable, including prior check records.
    for (const entry of manifest.outputs) await check(entry.path, entry.sha256);
    for (const asset of bundle.provenance.assets) await check(`${selected.revision}/${asset.path}`, asset.sha256);
    for (const name of ['publication.json', 'source-map.json']) assert(manifest.outputs.some(o=>o.path === `${selected.revision}/${name}`), `Missing ${name} in export manifest.`);
    const related = study.relatedPublications?.find(p=>p.publicationId === report.id);
    const superseded = related?.relationship === 'presentation-revision';
    const verificationPath = `${selected.revision}/verification.json`;
    const hasVerification = manifest.outputs.some(o=>o.path === verificationPath);
    let gate;
    if (hasVerification) {
      const v = await read('verification.json');
      assert(v.result === 'passed' || superseded && v.result?.startsWith('superseded presentation') || v.checks?.length && v.checks.every(c=>c.passed === true), `Incomplete verification: ${report.id}`);
      gate = v.result ?? 'all recorded checks passed';
    } else {
      const v = await read('content-verification.json');
      assert.equal(v.source_hashes, 'passed'); assert.equal(v.private_paths_and_placeholders, 'absent');
      gate = 'Phase 2 content verification + completed Phase 2 application/browser record';
    }
    records.push({ ...selected, studyId: manifest.study_id, sourceRunId: report.source.runId,
      manifestSha256: await check(`${selected.revision}/manifest.json`), sourceMapSha256: await check(`${selected.revision}/source-map.json`),
      verification: gate, superseded, qualification: related?.label ?? study.evidenceStatus });
  }
  return { result: 'passed', publications: records, hashedFiles: [...checked].map(([path,sha256])=>({path,sha256})),
    limitation: 'Integrity and retained presentation gates checked; original historical provenance gaps and research uncertainty remain. No research or statistics rerun.' };
}
