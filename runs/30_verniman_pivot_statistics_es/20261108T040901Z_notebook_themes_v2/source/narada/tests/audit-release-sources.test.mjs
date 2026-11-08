import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, mkdir, readFile, readdir, readlink, rename, rm, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { auditSources } from '../scripts/audit-release-sources.mjs';
import { hash, jsonBytes } from '../scripts/lib/release.mjs';

const REVISION = 'reports/exports/synthetic/saved_run/web_revision';
const SOURCE = 'runs/synthetic/saved_run/report.md';
const PUBLICATION_ID = 'synthetic-publication';
const LIMITATION = 'Integrity and retained presentation gates checked; original historical provenance gaps and research uncertainty remain. No research or statistics rerun.';

async function tree(root) {
  const entries = [];
  async function visit(directory, prefix = '') {
    const children = await readdir(directory, { withFileTypes: true });
    for (const child of children.sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
      const path = prefix + child.name;
      const absolute = resolve(directory, child.name);
      if (child.isSymbolicLink()) {
        entries.push({ path, kind: 'symlink', target: await readlink(absolute) });
      } else if (child.isDirectory()) {
        entries.push({ path, kind: 'directory' });
        await visit(absolute, `${path}/`);
      } else {
        entries.push({ path, kind: 'file', bytes: (await readFile(absolute)).toString('hex') });
      }
    }
  }
  await visit(root);
  return entries;
}

async function fixture(t, { fallback = false, declareFallback = true } = {}) {
  const workspace = await mkdtemp(resolve(tmpdir(), 'narada-source-audit-'));
  t.after(() => rm(workspace, { recursive: true, force: true }));
  const report = { id: PUBLICATION_ID, title: 'Explicit saved evidence', source: { producer: 'sahadeva', runId: 'saved_run' } };
  const assets = [
    { path: 'figures/selected.png', bytes: Buffer.from([137, 80, 78, 71, 13, 10, 26, 10, 0, 255]) },
    { path: 'downloads/selected.csv', bytes: Buffer.from('metric,value\nsaved_metric,.125\n') },
  ];
  const verificationName = fallback ? 'content-verification.json' : 'verification.json';
  const verification = fallback
    ? { source_hashes: 'passed', private_paths_and_placeholders: 'absent' }
    : { result: 'passed', checks: ['retained descriptive check'] };
  const contents = new Map([
    [SOURCE, Buffer.from('# Saved evidence\nResearch uncertainty remains.\n')],
    [`${REVISION}/publication.json`, jsonBytes(report)],
    [`${REVISION}/source-map.json`, jsonBytes({ bindings: [] })],
    [`${REVISION}/${verificationName}`, jsonBytes(verification)],
    ...assets.map(asset => [`${REVISION}/${asset.path}`, asset.bytes]),
  ]);
  for (const [path, bytes] of contents) {
    await mkdir(resolve(workspace, path, '..'), { recursive: true });
    await writeFile(resolve(workspace, path), bytes);
  }
  const manifest = {
    publication_id: report.id,
    source_run_id: report.source.runId,
    study_id: 'synthetic',
    source_artifacts: [{ path: SOURCE, sha256: hash(contents.get(SOURCE)) }],
    outputs: ['publication.json', 'source-map.json', ...(!fallback || declareFallback ? [verificationName] : [])]
      .map(name => ({ path: `${REVISION}/${name}`, sha256: hash(contents.get(`${REVISION}/${name}`)) })),
  };
  const selected = { publicationId: PUBLICATION_ID, revision: REVISION };
  const mapping = { schemaVersion: '1.0', publications: [selected] };
  const bundles = [{ report, provenance: { assets: assets.map(({ path, bytes }) => ({ path, sha256: hash(bytes) })) } }];
  const catalog = { studies: [{ studyId: 'synthetic', featuredPublicationId: PUBLICATION_ID, evidenceStatus: 'Recorded uncertainty' }] };
  const saveManifest = () => writeFile(resolve(workspace, REVISION, 'manifest.json'), jsonBytes(manifest));
  const setVerification = async record => {
    const bytes = jsonBytes(record);
    const path = `${REVISION}/${verificationName}`;
    await writeFile(resolve(workspace, path), bytes);
    const output = manifest.outputs.find(entry => entry.path === path);
    if (output) output.sha256 = hash(bytes);
    await saveManifest();
  };
  await saveManifest();
  return { workspace, mapping, bundles, catalog, manifest, saveManifest, setVerification };
}

const audit = subject => auditSources(subject.workspace, subject.mapping, subject.bundles, subject.catalog);

test('private source ownership resolves an explicit report nested inside a phase family without changing bytes', async t => {
  const subject = await fixture(t);
  subject.catalog.studies[0].featuredPublicationId = 'different-featured';
  subject.catalog.studies[0].phaseFamilies = [
    { id: 'earlier', analyses: [{ id: 'retained', publicationTabs: [{ publicationId: PUBLICATION_ID }] }] },
    { id: 'later', analyses: [{ id: 'context', publicationTabs: [{ publicationId: 'different-featured' }] }] },
  ];
  const result = await readOnly(subject, () => audit(subject));
  assert.equal(result.publications.length, 1);
  assert.equal(result.publications[0].publicationId, PUBLICATION_ID);
  assert.equal(result.publications[0].sourceRunId, 'saved_run');
});

async function readOnly(subject, action) {
  const before = await tree(subject.workspace);
  const identities = structuredClone([subject.mapping, subject.bundles, subject.catalog]);
  const result = await action();
  assert.deepEqual(await tree(subject.workspace), before, 'Audit must preserve input bytes and file inventory.');
  assert.deepEqual([subject.mapping, subject.bundles, subject.catalog], identities);
  return result;
}

const rejectsReadOnly = (subject, expected) => readOnly(subject, () => assert.rejects(audit(subject), expected));

function supersede(subject, relationship = 'presentation-revision') {
  subject.catalog.studies[0].featuredPublicationId = 'corrected-featured-publication';
  subject.catalog.studies[0].relatedPublications = [{
    publicationId: PUBLICATION_ID,
    sourceRunId: 'saved_run',
    relationship,
    label: 'Retained prior presentation; use corrected featured revision',
  }];
}

test('a same-run chart tab retains its explicit study attribution without a revision label', async t => {
  const subject = await fixture(t);
  subject.catalog.studies[0].featuredPublicationId = 'another-chart';
  subject.catalog.studies[0].publicationTabs = [
    { publicationId: 'another-chart', sourceRunId: 'saved_run', label: 'Chart A' },
    { publicationId: PUBLICATION_ID, sourceRunId: 'saved_run', label: 'Chart B' },
  ];
  const result = await readOnly(subject, () => audit(subject));
  assert.equal(result.publications[0].studyId, 'synthetic');
  assert.equal(result.publications[0].superseded, false);
  assert.equal(result.publications[0].qualification, 'Recorded uncertainty');
});

async function sealedRunFixture(t) {
  const subject = await fixture(t);
  const run = 'runs/synthetic/saved_run';
  for (const name of ['publication.json', 'source-map.json', 'figures', 'downloads']) {
    await rename(resolve(subject.workspace, REVISION, name), resolve(subject.workspace, run, name));
  }
  await rename(resolve(subject.workspace, REVISION, 'verification.json'), resolve(subject.workspace, run, 'publication-verification.json'));
  subject.manifest.outputs = subject.manifest.outputs.map(output => ({
    ...output,
    path: output.path.replace(`${REVISION}/`, `${run}/`).replace('/verification.json', '/publication-verification.json'),
  }));
  const manifestPath = resolve(subject.workspace, run, 'publication-manifest.json');
  subject.saveManifest = () => writeFile(manifestPath, jsonBytes(subject.manifest));
  await subject.saveManifest();
  await writeFile(resolve(subject.workspace, run, 'manifest.json'), jsonBytes({ study_id: 'synthetic', run_id: 'saved_run' }));
  subject.mapping.publications[0] = { publicationId: PUBLICATION_ID, run };
  return subject;
}

async function groupedRunFixture(t) {
  const subject = await sealedRunFixture(t);
  const selected = subject.mapping.publications[0];
  selected.publicationDirectory = `publications/${PUBLICATION_ID}`;
  const publication = `${selected.run}/${selected.publicationDirectory}`;
  await mkdir(resolve(subject.workspace, publication), { recursive: true });
  for (const name of ['publication.json', 'source-map.json', 'publication-verification.json', 'publication-manifest.json', 'figures', 'downloads']) {
    await rename(resolve(subject.workspace, selected.run, name), resolve(subject.workspace, publication, name));
  }
  subject.manifest.outputs = subject.manifest.outputs.map(output => ({
    ...output, path: output.path.replace(`${selected.run}/`, `${publication}/`),
  }));
  subject.saveManifest = () => writeFile(resolve(subject.workspace, publication, 'publication-manifest.json'), jsonBytes(subject.manifest));
  await subject.saveManifest();
  return subject;
}

async function independentRunFixture(t) {
  const subject = await groupedRunFixture(t);
  const selected = subject.mapping.publications[0];
  const publication = `${selected.run}/${selected.publicationDirectory}`;
  const checkerPath = 'verification/independent/checker.py';
  const checkerBytes = Buffer.from('# Synthetic independent checker snapshot\n');
  await mkdir(resolve(subject.workspace, selected.run, checkerPath, '..'), { recursive: true });
  await writeFile(resolve(subject.workspace, selected.run, checkerPath), checkerBytes);
  subject.sourceMap = { schema_version: 'synthetic.phase2-web-source-cells/v1', source_row_base: 0, publication_id: PUBLICATION_ID, run_id: 'saved_run', bindings: [] };
  subject.verification = { schema_version: 'synthetic.phase2-publication-independent/v1', status: 'passed', publication_id: PUBLICATION_ID,
    publication_sha256: hash(await readFile(resolve(subject.workspace, publication, 'publication.json'))), checker_sha256: hash(checkerBytes) };
  subject.global = { schema_version: 'synthetic.phase2-independent-publication/v1', status: 'passed', checker_sha256: hash(checkerBytes), source_snapshot: checkerPath };
  subject.saveIndependent = async ({ mutateVerification = record => record, mutateGlobal = record => record } = {}) => {
    const mapBytes = jsonBytes(subject.sourceMap);
    await writeFile(resolve(subject.workspace, publication, 'source-map.json'), mapBytes);
    subject.manifest.outputs.find(entry => entry.path === `${publication}/source-map.json`).sha256 = hash(mapBytes);
    const verification = mutateVerification({ ...subject.verification, source_map_sha256: hash(mapBytes) });
    const bytes = jsonBytes(verification);
    await writeFile(resolve(subject.workspace, publication, 'publication-verification.json'), bytes);
    subject.manifest.outputs.find(entry => entry.path === `${publication}/publication-verification.json`).sha256 = hash(bytes);
    await subject.saveManifest();
    const record = { ...verification, publication_manifest_sha256: hash(await readFile(resolve(subject.workspace, publication, 'publication-manifest.json'))), artifacts: [{ path: 'publication-verification.json', sha256: hash(bytes) }] };
    await writeFile(resolve(subject.workspace, selected.run, 'publication-verification.json'), jsonBytes(mutateGlobal({ ...subject.global, publications: [record] })));
  };
  await subject.saveIndependent();
  return subject;
}

test('independent status receipts require exact report/map/run identities and retained checker bytes', async t => {
  const subject = await independentRunFixture(t);
  const result = await readOnly(subject, () => audit(subject));
  assert.equal(result.publications[0].verification, 'independent saved-cell verification passed');
  assert(result.hashedFiles.some(entry => entry.path === 'runs/synthetic/saved_run/verification/independent/checker.py'));
  assert(result.hashedFiles.some(entry => entry.path === 'runs/synthetic/saved_run/publication-verification.json'));
});

test('independent receipt mismatches and unsupported status-only versions fail closed', async t => {
  for (const [key, value, expected] of [
    ['status', 'failed', /did not pass/],
    ['publication_id', 'another-publication', /publication identity mismatch/],
    ['publication_sha256', '0'.repeat(64), /report hash mismatch/],
    ['source_map_sha256', '0'.repeat(64), /source-map hash mismatch/],
    ['checker_sha256', '0'.repeat(64), /global checker hash mismatch/],
    ['schema_version', 'synthetic.phase2-publication-independent/v2', /Incomplete verification/],
  ]) {
    const subject = await independentRunFixture(t);
    await subject.saveIndependent({ mutateVerification: record => ({ ...record, [key]: value }) });
    await rejectsReadOnly(subject, expected);
  }
  const subject = await groupedRunFixture(t);
  const selected = subject.mapping.publications[0];
  const path = `${selected.run}/${selected.publicationDirectory}/publication-verification.json`;
  const bytes = jsonBytes({ status: 'passed' });
  await writeFile(resolve(subject.workspace, path), bytes);
  subject.manifest.outputs.find(entry => entry.path === path).sha256 = hash(bytes);
  await subject.saveManifest();
  await rejectsReadOnly(subject, /Incomplete verification/);
});

test('independent source-map and final global receipt identity mismatches are refused', async t => {
  for (const [key, value, expected] of [
    ['run_id', 'wrong_run', /run identity mismatch/], ['publication_id', 'another', /publication identity mismatch/],
    ['schema_version', 'unknown/v1', /source-map schema mismatch/], ['source_row_base', 1, /row base mismatch/],
  ]) {
    const subject = await independentRunFixture(t);
    subject.sourceMap[key] = value;
    await subject.saveIndependent();
    await rejectsReadOnly(subject, expected);
  }
  for (const [mutateGlobal, expected] of [
    [record => ({ ...record, status: 'failed' }), /global verification did not pass/],
    [record => ({ ...record, run_id: 'wrong_run' }), /global run identity mismatch/],
    [record => ({ ...record, publications: [...record.publications, record.publications[0]] }), /exactly one publication record/],
    [record => ({ ...record, publications: [{ ...record.publications[0], publication_manifest_sha256: '0'.repeat(64) }] }), /global manifest hash mismatch/],
    [record => ({ ...record, publications: [{ ...record.publications[0], artifacts: [] }] }), /per-publication receipt pin/],
    [record => ({ ...record, source_snapshot: 'verification/../../outside.py' }), /Source locator/],
  ]) {
    const subject = await independentRunFixture(t);
    await subject.saveIndependent({ mutateGlobal });
    await rejectsReadOnly(subject, expected);
  }
  const subject = await independentRunFixture(t);
  await writeFile(resolve(subject.workspace, 'runs/synthetic/saved_run/verification/independent/checker.py'), '# changed checker\n');
  await rejectsReadOnly(subject, /Changed source\/export/);
});

test('new sealed-run publication sources retain their separate publication and evidence manifest identities', async t => {
  const subject = await sealedRunFixture(t);
  const result = await readOnly(subject, () => audit(subject));
  const run = subject.mapping.publications[0].run;
  assert.equal(result.publications[0].run, run);
  assert.equal(result.publications[0].verification, 'passed');
  assert.equal(result.publications[0].manifestSha256, hash(await readFile(resolve(subject.workspace, run, 'publication-manifest.json'))));
  assert(result.hashedFiles.some(entry => entry.path === `${run}/manifest.json`));
  for (const name of ['source-map.json', 'publication-verification.json', 'downloads/selected.csv']) {
    const bytes = await readFile(resolve(subject.workspace, run, name));
    await writeFile(resolve(subject.workspace, run, name), 'changed sealed bytes');
    await rejectsReadOnly(subject, /Changed source\/export/);
    await writeFile(resolve(subject.workspace, run, name), bytes);
  }
});

test('multiple saved report directories share one sealed run while preserving separate publication pins', async t => {
  const subject = await groupedRunFixture(t);
  const selected = subject.mapping.publications[0];
  const original = `${selected.run}/${selected.publicationDirectory}`;
  const publicationId = 'second-synthetic-publication';
  const publicationDirectory = `publications/${publicationId}`;
  const destination = `${selected.run}/${publicationDirectory}`;
  const report = { ...subject.bundles[0].report, id: publicationId };
  await mkdir(resolve(subject.workspace, destination), { recursive: true });
  for (const name of ['publication.json', 'source-map.json', 'publication-verification.json', 'figures/selected.png', 'downloads/selected.csv']) {
    const bytes = name === 'publication.json' ? jsonBytes(report) : await readFile(resolve(subject.workspace, original, name));
    await mkdir(resolve(subject.workspace, destination, name, '..'), { recursive: true });
    await writeFile(resolve(subject.workspace, destination, name), bytes);
  }
  const manifest = structuredClone(subject.manifest);
  manifest.publication_id = publicationId;
  for (const output of manifest.outputs) {
    output.path = output.path.replace(`${original}/`, `${destination}/`);
    output.sha256 = hash(await readFile(resolve(subject.workspace, output.path)));
  }
  await writeFile(resolve(subject.workspace, destination, 'publication-manifest.json'), jsonBytes(manifest));
  subject.mapping.publications.push({ publicationId, run: selected.run, publicationDirectory });
  subject.bundles.push({ ...subject.bundles[0], report });
  subject.catalog.studies[0].analyses = [
    { id: 'first', publicationTabs: [{ publicationId: PUBLICATION_ID }] },
    { id: 'second', publicationTabs: [{ publicationId }] },
  ];
  const result = await readOnly(subject, () => audit(subject));
  assert.equal(result.publications.length, 2);
  assert.equal(result.hashedFiles.filter(entry => entry.path === `${selected.run}/manifest.json`).length, 1);
  assert(result.hashedFiles.some(entry => entry.path === `${original}/publication-manifest.json`));
  assert(result.hashedFiles.some(entry => entry.path === `${destination}/publication-manifest.json`));
  assert.equal(result.publications[1].sourceRunId, 'saved_run');
  assert.equal(result.publications[1].publicationDirectory, publicationDirectory);
  await writeFile(resolve(subject.workspace, destination, 'figures/selected.png'), 'changed second report figure');
  await rejectsReadOnly(subject, /Changed source\/export/);
});

test('publication directories reject arbitrary paths, other IDs, revision mappings and missing run identity', async t => {
  for (const directory of ['', '/absolute', '../outside', 'publications', 'publications/other-id', `publications/${PUBLICATION_ID}/extra`, `publications/${PUBLICATION_ID}/`, `publications\\${PUBLICATION_ID}`, null]) {
    await t.test(String(directory), async t => {
      const subject = await groupedRunFixture(t);
      subject.mapping.publications[0].publicationDirectory = directory;
      await rejectsReadOnly(subject, /locator|exact publications/);
    });
  }
  const revision = await fixture(t);
  revision.mapping.publications[0].publicationDirectory = `publications/${PUBLICATION_ID}`;
  await rejectsReadOnly(revision, /require a sealed-run/);
  const run = await groupedRunFixture(t);
  await writeFile(resolve(run.workspace, run.mapping.publications[0].run, 'manifest.json'), jsonBytes({ study_id: 'synthetic', run_id: 'other_run' }));
  await rejectsReadOnly(run, /Run manifest identity/);
  await rm(resolve(run.workspace, run.mapping.publications[0].run, 'manifest.json'));
  await rejectsReadOnly(run, /ENOENT/);
});

test('per-publication source directories reject symlinked selected roots and ancestors before reading', async t => {
  for (const path of ['runs/synthetic/saved_run/publications', `runs/synthetic/saved_run/publications/${PUBLICATION_ID}`]) {
    const subject = await groupedRunFixture(t);
    const original = resolve(subject.workspace, path);
    const retained = resolve(subject.workspace, 'synthetic-retained-copy');
    await rename(original, retained);
    await symlink(retained, original);
    await rejectsReadOnly(subject, /Source symlink/);
  }
});

test('sealed-run mappings fail closed on ambiguous sources, invalid locators, attribution and missing verification', async t => {
  for (const mode of ['both', 'neither', 'wrong-depth', 'wrong-run', 'wrong-evidence-study', 'missing-verification', 'superseded']) {
    await t.test(mode, async t => {
      const subject = await sealedRunFixture(t);
      const run = subject.mapping.publications[0].run;
      let expected;
      if (mode === 'both') { subject.mapping.publications[0].revision = REVISION; expected = /exactly one/; }
      if (mode === 'neither') { delete subject.mapping.publications[0].run; expected = /exactly one/; }
      if (mode === 'wrong-depth') { subject.mapping.publications[0].run = `${run}/extra`; expected = /explicit sealed run/; }
      if (mode === 'wrong-run') { subject.manifest.source_run_id = 'another_run'; await subject.saveManifest(); expected = /another_run/; }
      if (mode === 'wrong-evidence-study') { await writeFile(resolve(subject.workspace, run, 'manifest.json'), jsonBytes({ study_id: 'other', run_id: 'saved_run' })); expected = /study attribution/; }
      if (mode === 'missing-verification') { subject.manifest.outputs = subject.manifest.outputs.filter(output => !output.path.endsWith('/publication-verification.json')); await subject.saveManifest(); expected = /declared publication-verification/; }
      if (mode === 'superseded') {
        supersede(subject);
        const path = `${run}/publication-verification.json`;
        const bytes = jsonBytes({ result: 'superseded presentation; use revised report' });
        await writeFile(resolve(subject.workspace, path), bytes);
        subject.manifest.outputs.find(output => output.path === path).sha256 = hash(bytes);
        await subject.saveManifest(); expected = /Incomplete verification/;
      }
      await rejectsReadOnly(subject, expected);
    });
  }
});

test('a publication selected inside an analysis group retains explicit study attribution', async t => {
  const subject = await fixture(t);
  subject.catalog.studies[0].featuredPublicationId = 'different-featured';
  subject.catalog.studies[0].analyses = [{ id: 'saved-analysis', publicationTabs: [{ publicationId: PUBLICATION_ID }] }];
  const record = await readOnly(subject, () => audit(subject));
  assert.equal(record.publications[0].studyId, 'synthetic');
});

test('ordinary passed records preserve exact inventory order, attribution and qualifications', async t => {
  const subject = await fixture(t);
  const result = await readOnly(subject, () => audit(subject));
  const files = [SOURCE, ...subject.manifest.outputs.map(entry => entry.path),
    `${REVISION}/figures/selected.png`, `${REVISION}/downloads/selected.csv`, `${REVISION}/manifest.json`];
  assert.deepEqual(result, {
    result: 'passed',
    publications: [{
      ...subject.mapping.publications[0],
      studyId: 'synthetic',
      sourceRunId: 'saved_run',
      manifestSha256: hash(await readFile(resolve(subject.workspace, REVISION, 'manifest.json'))),
      sourceMapSha256: hash(await readFile(resolve(subject.workspace, REVISION, 'source-map.json'))),
      verification: 'passed',
      superseded: false,
      qualification: 'Recorded uncertainty',
    }],
    hashedFiles: await Promise.all(files.map(async path => ({ path, sha256: hash(await readFile(resolve(subject.workspace, path))) }))),
    limitation: LIMITATION,
  });
});

test('source mappings require exact selected-index coverage and supported version', async t => {
  for (const failure of ['missing', 'extra', 'duplicate', 'version']) {
    await t.test(failure, async t => {
      const subject = await fixture(t);
      if (failure === 'missing') subject.mapping.publications = [];
      if (failure === 'extra') subject.mapping.publications.push({ publicationId: 'unselected', revision: REVISION });
      if (failure === 'duplicate') subject.mapping.publications.push({ ...subject.mapping.publications[0] });
      if (failure === 'version') subject.mapping.schemaVersion = '2.0';
      await rejectsReadOnly(subject, /source map|selected index/);
    });
  }
});

test('revision locators reject absolute, traversal, dot, separator and wrong-depth forms', async t => {
  for (const revision of ['/reports/exports/s/r/v', 'reports/exports/s/r/..', 'reports/exports/s/r/.',
    'reports//exports/s/r/v', 'reports\\exports\\s\\r\\v', 'C:/reports/exports/s/r/v',
    'reports/exports/s/r/v/', 'runs/s/r/v', 'reports/exports/s/r/v/extra']) {
    const subject = await fixture(t);
    subject.mapping.publications[0].revision = revision;
    await rejectsReadOnly(subject, /locator|explicit presentation revision/);
  }
});

test('every declared source, output and asset locator is checked before reading', async t => {
  const invalid = ['/absolute', '../outside', './relative', 'runs/../outside', 'runs//saved',
    'runs\\saved', 'C:/outside', 'file://outside', 'runs/saved/', 'runs/saved?query', 'runs/saved#fragment', 'runs/\u0000saved'];
  for (const kind of ['source', 'output', 'asset']) {
    await t.test(kind, async t => {
      for (const path of invalid) {
        const subject = await fixture(t);
        if (kind === 'source') subject.manifest.source_artifacts[0].path = path;
        if (kind === 'output') subject.manifest.outputs[1].path = path;
        if (kind === 'asset') subject.bundles[0].provenance.assets[0].path = path;
        await subject.saveManifest();
        await rejectsReadOnly(subject, /locator/);
      }
    });
  }
});

test('source publication must equal staged content', async t => {
  const subject = await fixture(t);
  subject.bundles[0].report.title = 'Different staged report';
  await rejectsReadOnly(subject, /differs from staged bundle/);
});

test('canonical signed-zero serialization retains exact source-byte pins without masking other numeric differences', async t => {
  const subject = await fixture(t);
  const path = `${REVISION}/publication.json`;
  subject.bundles[0].report.saved = { values: [0, null, false, '0'] };
  const bytes = Buffer.from(jsonBytes(subject.bundles[0].report).toString().replace('"values": [\n      0,', '"values": [\n      -0,'));
  assert.match(bytes.toString(), /-0,/);
  await writeFile(resolve(subject.workspace, path), bytes);
  subject.manifest.outputs.find(entry => entry.path === path).sha256 = hash(bytes);
  await subject.saveManifest();
  await readOnly(subject, () => audit(subject));
  subject.bundles[0].report.saved.values[0] = -1;
  await rejectsReadOnly(subject, /differs from staged bundle/);
  subject.bundles[0].report.saved.values[0] = null;
  await rejectsReadOnly(subject, /differs from staged bundle/);
});

test('publication, source-run and study attribution must agree', async t => {
  for (const field of ['publication_id', 'source_run_id', 'study_id']) {
    await t.test(field, async t => {
      const subject = await fixture(t);
      subject.manifest[field] = 'different-attribution';
      await subject.saveManifest();
      await rejectsReadOnly(subject, /different-attribution|attribution mismatch/);
    });
  }
});

test('changed saved sources, revision outputs and declared selected assets fail closed', async t => {
  for (const path of [SOURCE, `${REVISION}/source-map.json`, `${REVISION}/verification.json`,
    `${REVISION}/figures/selected.png`, `${REVISION}/downloads/selected.csv`]) {
    const subject = await fixture(t);
    await writeFile(resolve(subject.workspace, path), 'changed retained bytes');
    await rejectsReadOnly(subject, /Changed source\/export/);
  }
});

test('publication and source-map outputs must be declared in the retained manifest', async t => {
  for (const name of ['publication.json', 'source-map.json']) {
    const subject = await fixture(t);
    subject.manifest.outputs = subject.manifest.outputs.filter(entry => entry.path !== `${REVISION}/${name}`);
    await subject.saveManifest();
    await rejectsReadOnly(subject, new RegExp(`Missing ${name.replace('.', '\\.')}`));
  }
});

test('declared source, output and asset identities require nonempty valid SHA-256 pins', async t => {
  for (const kind of ['source', 'output', 'asset']) {
    await t.test(kind, async t => {
      for (const pin of [undefined, null, '', false, 0, 'abc', 'g'.repeat(64)]) {
        const subject = await fixture(t);
        const entry = kind === 'source' ? subject.manifest.source_artifacts[0]
          : kind === 'output' ? subject.manifest.outputs[1] : subject.bundles[0].provenance.assets[0];
        if (pin === undefined) delete entry.sha256;
        else entry.sha256 = pin;
        await subject.saveManifest();
        await rejectsReadOnly(subject, /Missing or invalid SHA-256 pin/);
      }
    });
  }
});

test('missing and nonregular selected files are rejected across each read boundary', async t => {
  const paths = [SOURCE, `${REVISION}/manifest.json`, `${REVISION}/publication.json`,
    `${REVISION}/source-map.json`, `${REVISION}/verification.json`, `${REVISION}/figures/selected.png`];
  for (const kind of ['missing', 'directory']) {
    await t.test(kind, async t => {
      for (const path of paths) {
        const subject = await fixture(t);
        await rm(resolve(subject.workspace, path));
        if (kind === 'directory') await mkdir(resolve(subject.workspace, path));
        await rejectsReadOnly(subject, kind === 'missing' ? /ENOENT/ : /regular file/);
      }
    });
  }
});

test('file symlinks are rejected before JSON parsing or retained-byte access', async t => {
  for (const path of [SOURCE, `${REVISION}/manifest.json`, `${REVISION}/publication.json`,
    `${REVISION}/source-map.json`, `${REVISION}/verification.json`, `${REVISION}/downloads/selected.csv`]) {
    const subject = await fixture(t);
    const target = resolve(subject.workspace, 'malformed-target.json');
    await writeFile(target, '{malformed JSON must never be parsed');
    await rm(resolve(subject.workspace, path));
    await symlink(target, resolve(subject.workspace, path));
    await rejectsReadOnly(subject, /Source symlink/);
  }
});

test('symlinked ancestors of revision, source and asset files are rejected', async t => {
  for (const path of ['reports', 'reports/exports', 'reports/exports/synthetic', 'reports/exports/synthetic/saved_run',
    REVISION, 'runs', `${REVISION}/figures`]) {
    const subject = await fixture(t);
    const destination = resolve(subject.workspace, 'relocated-real-directory');
    await rename(resolve(subject.workspace, path), destination);
    await symlink(destination, resolve(subject.workspace, path));
    await rejectsReadOnly(subject, /Source symlink/);
  }
});

test('safe retained snapshot filenames with bracketed app routes remain accepted', async t => {
  const subject = await fixture(t);
  const path = `${REVISION}/provenance/narada-source/src/app/reports/[id]/page.tsx`;
  await mkdir(resolve(subject.workspace, path, '..'), { recursive: true });
  await writeFile(resolve(subject.workspace, path), 'retained snapshot bytes');
  subject.manifest.outputs.push({ path, sha256: hash(await readFile(resolve(subject.workspace, path))) });
  await subject.saveManifest();
  const result = await readOnly(subject, () => audit(subject));
  assert(result.hashedFiles.some(entry => entry.path === path));
});

test('checks-only verification requires a nonempty array of explicitly passed checks', async t => {
  const subject = await fixture(t);
  await subject.setVerification({ checks: [{ name: 'content', passed: true }, { name: 'browser', passed: true }] });
  const result = await readOnly(subject, () => audit(subject));
  assert.equal(result.publications[0].verification, 'all recorded checks passed');
  for (const checks of [[], [{ passed: false }], [{ passed: true }, { passed: false }],
    [{ passed: true }, {}], ['descriptive only'], [null], 'not an array']) {
    await subject.setVerification({ checks });
    await rejectsReadOnly(subject, /Incomplete verification/);
  }
});

test('explicit passed verification accepts historical descriptive checks without imposing a new schema', async t => {
  const subject = await fixture(t);
  await subject.setVerification({ result: 'passed', checks: ['source integrity', 'all selected figures unchanged'] });
  const result = await readOnly(subject, () => audit(subject));
  assert.equal(result.publications[0].verification, 'passed');
});

test('superseded presentation status retains its catalog qualification only for a presentation revision', async t => {
  const subject = await fixture(t);
  supersede(subject);
  const status = 'superseded presentation; numeric/route checks pass, use corrected featured revision';
  await subject.setVerification({ result: status });
  const result = await readOnly(subject, () => audit(subject));
  assert.equal(result.publications[0].verification, status);
  assert.equal(result.publications[0].superseded, true);
  assert.equal(result.publications[0].qualification, 'Retained prior presentation; use corrected featured revision');
  subject.catalog.studies[0].relatedPublications[0].relationship = 'other-run';
  await subject.setVerification({ result: status, checks: [{ passed: true }] });
  await rejectsReadOnly(subject, /Incomplete verification/);
});

test('explicit failed and unknown results cannot be rescued by positive checks', async t => {
  for (const result of ['failed', 'incomplete', null, 'superseded presentation without catalog relationship']) {
    const subject = await fixture(t);
    await subject.setVerification({ result, checks: [{ passed: true }] });
    await rejectsReadOnly(subject, /Incomplete verification/);
  }
});

test('Phase 2 fallback preserves its inherited qualification and hashes the consumed record', async t => {
  for (const declareFallback of [true, false]) {
    const subject = await fixture(t, { fallback: true, declareFallback });
    const result = await readOnly(subject, () => audit(subject));
    assert.equal(result.publications[0].verification, 'Phase 2 content verification + completed Phase 2 application/browser record');
    const path = `${REVISION}/content-verification.json`;
    assert.deepEqual(result.hashedFiles.find(entry => entry.path === path), {
      path, sha256: hash(await readFile(resolve(subject.workspace, path))),
    });
    assert.equal(result.limitation, LIMITATION);
    await subject.setVerification({ source_hashes: 'failed', private_paths_and_placeholders: 'absent' });
    await rejectsReadOnly(subject, /failed/);
    await subject.setVerification({ source_hashes: 'passed', private_paths_and_placeholders: 'present' });
    await rejectsReadOnly(subject, /present/);
  }
});

test('undeclared Phase 2 fallback is checked before parsing and missing fallback fails', async t => {
  const subject = await fixture(t, { fallback: true, declareFallback: false });
  const path = resolve(subject.workspace, REVISION, 'content-verification.json');
  await rm(path);
  await rejectsReadOnly(subject, /ENOENT/);
  const target = resolve(subject.workspace, 'malformed-fallback.json');
  await writeFile(target, '{malformed JSON must never be parsed');
  await symlink(target, path);
  await rejectsReadOnly(subject, /Source symlink/);
});

test('future study 08/09 exporter and shared-helper snapshots are covered by generic output hashes', async t => {
  for (const study of ['08_countertrend_bar_continuation', '09_range_xv_c2_confirmation']) {
    const subject = await fixture(t);
    subject.manifest.study_id = study;
    subject.catalog.studies[0].studyId = study;
    const files = new Map([
      [`${REVISION}/provenance/publish_web.py`, Buffer.from('# exact exporter source bytes\n')],
      [`${REVISION}/provenance/saved_evidence.py`, Buffer.from('# exact saved-evidence helper bytes\n')],
    ]);
    const inventoryPath = `${REVISION}/provenance/source-inventory.json`;
    files.set(inventoryPath, jsonBytes([...files].map(([path, bytes]) => ({ path: path.slice(REVISION.length + 1), sha256: hash(bytes) }))));
    for (const [path, bytes] of files) {
      await mkdir(resolve(subject.workspace, path, '..'), { recursive: true });
      await writeFile(resolve(subject.workspace, path), bytes);
      subject.manifest.outputs.push({ path, sha256: hash(bytes) });
    }
    await subject.saveManifest();
    const result = await readOnly(subject, () => audit(subject));
    for (const [path, bytes] of files) {
      assert.deepEqual(result.hashedFiles.find(entry => entry.path === path), { path, sha256: hash(bytes) });
    }
    await writeFile(resolve(subject.workspace, REVISION, 'provenance/saved_evidence.py'), '# changed helper source\n');
    await rejectsReadOnly(subject, /Changed source\/export: .*provenance\/saved_evidence\.py/);
  }
});

test('importing the audit is side-effect free and independent of Python or CLI dispatch', async t => {
  const subject = await fixture(t);
  const moduleUrl = new URL('../scripts/audit-release-sources.mjs', import.meta.url).href;
  await readOnly(subject, async () => {
    const result = await promisify(execFile)(process.execPath, ['--input-type=module', '-e',
      `const module = await import(${JSON.stringify(moduleUrl)}); console.log(typeof module.auditSources);`],
    { cwd: subject.workspace });
    assert.equal(result.stdout, 'function\n');
    assert.equal(result.stderr, '');
  });
});
