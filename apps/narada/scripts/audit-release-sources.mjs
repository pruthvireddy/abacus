import assert from 'node:assert/strict';
import { studyPublicationReferences } from './lib/study-selections.mjs';
import { readFile, lstat } from 'node:fs/promises';
import { isAbsolute, relative, resolve, sep } from 'node:path';
import { hash } from './lib/release.mjs';

function validateLocator(locator) {
  assert(
    typeof locator === 'string'
      && locator.length > 0
      && !isAbsolute(locator)
      && !/[\\:#?]/.test(locator)
      && [...locator].every(character => {
        const code = character.charCodeAt(0);
        return code > 31 && code !== 127;
      })
      && locator.split('/').every(part => part !== '' && part !== '.' && part !== '..'),
    `Source locator must be workspace-relative without traversal or invalid separators: ${locator}`,
  );
}

function verificationGate(verification, superseded, publicationId) {
  if (verification.result === 'passed') {
    return verification.result;
  }
  if (
    superseded
    && typeof verification.result === 'string'
    && verification.result.startsWith('superseded presentation')
  ) {
    return verification.result;
  }
  if (
    !Object.hasOwn(verification, 'result')
    && Array.isArray(verification.checks)
    && verification.checks.length > 0
    && verification.checks.every(check => check?.passed === true)
  ) {
    return 'all recorded checks passed';
  }
  assert.fail(`Incomplete verification: ${publicationId}`);
}

// The publisher's canonical JSON serializes -0 as 0. Compare that numeric
// representation without changing retained source bytes or accepting other
// differences (including nonfinite values, nulls, strings or booleans).
function canonicalZero(value) {
  if (typeof value === 'number') return Object.is(value, -0) ? 0 : value;
  if (Array.isArray(value)) return value.map(canonicalZero);
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, canonicalZero(item)]));
  }
  return value;
}

// This private release audit follows explicit locators. The website build never
// imports this file or discovers research directories.
export async function auditSources(workspace, mapping, bundles, catalog) {
  assert(
    mapping.schemaVersion === '1.0' && Array.isArray(mapping.publications),
    'Invalid release source map.',
  );
  assert.deepEqual(
    mapping.publications.map(publication => publication.publicationId).sort(),
    bundles.map(bundle => bundle.report.id).sort(),
    'Release source map must cover exactly the selected index.',
  );

  const root = resolve(workspace);
  const checked = new Map();

  // Check every selected locator and its ancestors before reading any bytes.
  // JSON reads do not insert hashes here, preserving the retained inventory order.
  async function readChecked(locator) {
    validateLocator(locator);
    const file = resolve(root, locator);
    const contained = relative(root, file);
    assert(
      contained !== ''
        && contained !== '..'
        && !contained.startsWith(`..${sep}`)
        && !isAbsolute(contained),
      `Source locator escapes workspace: ${locator}`,
    );
    const rootInfo = await lstat(root);
    assert(!rootInfo.isSymbolicLink() && rootInfo.isDirectory(), 'Workspace must be a real directory.');

    let current = root;
    const parts = locator.split('/');
    for (const [index, part] of parts.entries()) {
      current = resolve(current, part);
      const info = await lstat(current);
      assert(!info.isSymbolicLink(), `Source symlink: ${locator}`);
      if (index < parts.length - 1) {
        assert(info.isDirectory(), `Source ancestor must be a directory: ${locator}`);
      } else {
        assert(info.isFile(), `Source must be a regular file: ${locator}`);
      }
    }
    return await readFile(file);
  }

  async function digest(locator) {
    const actual = hash(await readChecked(locator));
    checked.set(locator, actual);
    return actual;
  }

  async function checkPinned(locator, sha256) {
    assert(
      typeof sha256 === 'string' && /^[a-f0-9]{64}$/i.test(sha256),
      `Missing or invalid SHA-256 pin: ${locator}`,
    );
    assert.equal(await digest(locator), sha256, `Changed source/export: ${locator}`);
  }

  const records = [];
  for (const selected of mapping.publications) {
    const isRun = Object.hasOwn(selected, 'run');
    assert(isRun !== Object.hasOwn(selected, 'revision'), 'Select exactly one sealed run or presentation revision.');
    const locator = isRun ? selected.run : selected.revision;
    validateLocator(locator);
    assert(
      (isRun ? /^runs\/[^/]+\/[^/]+$/ : /^reports\/exports\/[^/]+\/[^/]+\/[^/]+$/).test(locator),
      isRun ? 'Expected an explicit sealed run.' : 'Expected an explicit presentation revision.',
    );
    if (Object.hasOwn(selected, 'publicationDirectory')) {
      assert(isRun, 'Publication directories require a sealed-run mapping.');
      validateLocator(selected.publicationDirectory);
      assert(
        selected.publicationDirectory === `publications/${selected.publicationId}`,
        'Expected the exact publications/<publication-id> source directory.',
      );
    }
    const publicationLocator = selected.publicationDirectory
      ? `${locator}/${selected.publicationDirectory}` : locator;
    const readSourceJson = async name => JSON.parse(
      (await readChecked(`${publicationLocator}/${name}`)).toString('utf8'),
    );
    const manifestName = isRun ? 'publication-manifest.json' : 'manifest.json';
    const manifest = await readSourceJson(manifestName);
    const report = await readSourceJson('publication.json');
    const bundle = bundles.find(candidate => candidate.report.id === selected.publicationId);
    assert.deepEqual(canonicalZero(report), canonicalZero(bundle.report), 'Presentation source differs from staged bundle.');
    assert.equal(manifest.publication_id, report.id);
    assert.equal(manifest.source_run_id, report.source.runId);
    if (isRun) {
      assert.equal(locator, `runs/${manifest.study_id}/${manifest.source_run_id}`, 'Sealed-run locator attribution mismatch.');
      const runManifest = JSON.parse((await readChecked(`${locator}/manifest.json`)).toString('utf8'));
      assert.equal(runManifest.study_id, manifest.study_id, 'Run manifest study attribution mismatch.');
      assert.equal(runManifest.run_id, report.source.runId, 'Run manifest identity mismatch.');
      // Retain the ordinary evidence manifest identity separately. Its contract
      // and scientific validity remain owned by the research validator.
      await digest(`${locator}/manifest.json`);
    }

    const study = catalog.studies.find(candidate => studyPublicationReferences(candidate).some(publication => publication.publicationId === report.id));
    assert(study && study.studyId === manifest.study_id, 'Export study attribution mismatch.');

    for (const entry of manifest.source_artifacts) {
      await checkPinned(entry.path, entry.sha256);
    }
    // All retained source outputs are immutable, including prior check records.
    for (const entry of manifest.outputs) {
      await checkPinned(entry.path, entry.sha256);
    }
    for (const asset of bundle.provenance.assets) {
      await checkPinned(`${publicationLocator}/${asset.path}`, asset.sha256);
    }
    for (const name of ['publication.json', 'source-map.json']) {
      assert(
        manifest.outputs.some(output => output.path === `${publicationLocator}/${name}`),
        `Missing ${name} in export manifest.`,
      );
    }

    const related = study.relatedPublications?.find(publication => publication.publicationId === report.id);
    const superseded = related?.relationship === 'presentation-revision';
    const verificationName = isRun ? 'publication-verification.json' : 'verification.json';
    const verificationPath = `${publicationLocator}/${verificationName}`;
    const hasVerification = manifest.outputs.some(output => output.path === verificationPath);
    let gate;
    if (hasVerification) {
      const verification = await readSourceJson(verificationName);
      const independentSchema = typeof verification.schema_version === 'string'
        ? /^([a-z0-9]+(?:[.-][a-z0-9]+)*)-publication-independent\/v1$/.exec(verification.schema_version)
        : null;
      if (independentSchema) {
        assert(isRun, 'Independent status receipts require a sealed run.');
        assert.equal(verification.status, 'passed', 'Independent verification did not pass.');
        assert.equal(verification.publication_id, report.id, 'Independent verification publication identity mismatch.');
        assert.equal(verification.publication_sha256, checked.get(`${publicationLocator}/publication.json`), 'Independent verification report hash mismatch.');
        assert.equal(verification.source_map_sha256, checked.get(`${publicationLocator}/source-map.json`), 'Independent verification source-map hash mismatch.');
        assert(typeof verification.checker_sha256 === 'string' && /^[a-f0-9]{64}$/.test(verification.checker_sha256), 'Independent verification requires an exact checker hash.');
        const sourceMap = await readSourceJson('source-map.json');
        assert.equal(sourceMap.schema_version, `${independentSchema[1]}-web-source-cells/v1`, 'Independent source-map schema mismatch.');
        assert.equal(sourceMap.source_row_base, 0, 'Independent source-map row base mismatch.');
        assert.equal(sourceMap.run_id, report.source.runId, 'Independent source-map run identity mismatch.');
        assert.equal(sourceMap.publication_id, report.id, 'Independent source-map publication identity mismatch.');
        const globalPath = `${locator}/publication-verification.json`;
        const globalBytes = await readChecked(globalPath);
        const global = JSON.parse(globalBytes.toString('utf8'));
        assert.equal(global.schema_version, `${independentSchema[1]}-independent-publication/v1`, 'Independent global receipt schema mismatch.');
        assert.equal(global.status, 'passed', 'Independent global verification did not pass.');
        assert.equal(global.checker_sha256, verification.checker_sha256, 'Independent global checker hash mismatch.');
        assert(typeof global.source_snapshot === 'string' && global.source_snapshot.startsWith('verification/'), 'Independent checker requires a retained run snapshot.');
        if (Object.hasOwn(global, 'run_id')) assert.equal(global.run_id, report.source.runId, 'Independent global run identity mismatch.');
        const records = Array.isArray(global.publications) ? global.publications.filter(entry => entry.publication_id === report.id) : [];
        assert.equal(records.length, 1, 'Independent global receipt must bind exactly one publication record.');
        const record = records[0];
        assert.equal(record.status, 'passed', 'Independent publication record did not pass.');
        assert.equal(record.publication_sha256, verification.publication_sha256, 'Independent global report hash mismatch.');
        assert.equal(record.source_map_sha256, verification.source_map_sha256, 'Independent global source-map hash mismatch.');
        assert.equal(record.publication_manifest_sha256, hash(await readChecked(`${publicationLocator}/${manifestName}`)), 'Independent global manifest hash mismatch.');
        const receiptPins = Array.isArray(record.artifacts) ? record.artifacts.filter(entry => entry.path === verificationName) : [];
        assert.equal(receiptPins.length, 1, 'Independent global record requires the per-publication receipt pin.');
        assert.equal(receiptPins[0].sha256, checked.get(verificationPath), 'Independent global receipt hash mismatch.');
        await checkPinned(`${locator}/${global.source_snapshot}`, verification.checker_sha256);
        checked.set(globalPath, hash(globalBytes));
        gate = 'independent saved-cell verification passed';
      } else {
        gate = verificationGate(verification, superseded && !isRun, report.id);
      }
    } else {
      assert(!isRun, 'Sealed runs require a declared publication-verification.json.');
      const verification = await readSourceJson('content-verification.json');
      assert.equal(verification.source_hashes, 'passed');
      assert.equal(verification.private_paths_and_placeholders, 'absent');
      await digest(`${publicationLocator}/content-verification.json`);
      gate = 'Phase 2 content verification + completed Phase 2 application/browser record';
    }

    records.push({
      ...selected,
      studyId: manifest.study_id,
      sourceRunId: report.source.runId,
      manifestSha256: await digest(`${publicationLocator}/${manifestName}`),
      sourceMapSha256: await digest(`${publicationLocator}/source-map.json`),
      verification: gate,
      superseded,
      qualification: related?.label ?? study.evidenceStatus,
    });
  }
  return {
    result: 'passed',
    publications: records,
    hashedFiles: [...checked].map(([path, sha256]) => ({ path, sha256 })),
    limitation: 'Integrity and retained presentation gates checked; original historical provenance gaps and research uncertainty remain. No research or statistics rerun.',
  };
}
