import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
import { relative, resolve } from 'node:path';
import {
  hash, jsonBytes, releaseId, safeId, saveNew, inventory, inventoryHash,
  verifyInventory, copyInventory, validateStaticFiles, buildOutputConfig,
  deployArgs, deploymentResult, run, checkHosted, protectedGet,
} from './lib/release.mjs';
import { requireGate } from './lib/release-gates.mjs';
import { verifyPublications } from './lib/publication.mjs';
import { readStudyCatalog } from './lib/studies.mjs';
import { auditSources } from './audit-release-sources.mjs';
import { verifyStaticPublicationJson } from './lib/static-json-delivery.mjs';

const app = resolve(import.meta.dirname, '..');
const workspace = resolve(app, '../..');
assert(resolve(process.cwd()) === app, 'Run release commands from apps/narada.');
assert(process.versions.node.split('.')[0] === '24', 'Use Node 24.');
const [action, id, ...args] = process.argv.slice(2);
const cli = process.env.NARADA_VERCEL_CLI ?? 'vercel';
const readJson = async path => JSON.parse(await readFile(path, 'utf8'));
const eventId = () => `${Date.now()}-${crypto.randomUUID().slice(0, 8)}`;

async function event(record, kind, details) {
  await saveNew(resolve(record, 'events', `${eventId()}-${kind}.json`), {
    kind,
    at: new Date().toISOString(),
    ...details,
  });
}

async function prepare() {
  assert(!id, 'Preparation generates its own unique release ID.');
  const rid = releaseId();
  const record = resolve(app, 'releases', rid);
  const generated = resolve(app, '.release-artifacts', rid);
  const artifact = resolve(generated, 'deploy');
  await mkdir(resolve(app, 'releases'), { recursive: true });
  await mkdir(record, { recursive: false });
  const checks = [];
  try {
    for (const command of [
      ['npm', 'run', 'verify'],
      ['npm', 'test'],
      ['npm', 'run', 'lint'],
      ['npm', 'run', 'build'],
    ]) {
      console.log(`Release gate: ${command.join(' ')}`);
      const start = new Date().toISOString();
      const result = await run(command[0], command.slice(1), { cwd: app, echo: true });
      checks.push({
        command: command.join(' '),
        startedAt: start,
        exitCode: result.exitCode,
        stdout: result.stdout,
        stderr: result.stderr,
      });
    }
    const publications = await verifyPublications();
    const catalog = await readStudyCatalog(publications.bundles.map(bundle => bundle.report));
    const sources = await readJson(resolve(app, 'content/release-sources.json'));
    const audit = await auditSources(workspace, sources, publications.bundles, catalog);
    await saveNew(resolve(record, 'source-audit.json'), audit);
    const staticJsonDelivery = await verifyStaticPublicationJson({
      canonicalRoot: resolve(app, 'public/publications'),
      exportRoot: resolve(app, 'out/publications'),
    });
    const files = await inventory(resolve(app, 'out'));
    validateStaticFiles(files, catalog, publications.bundles);
    await copyInventory(resolve(app, 'out'), resolve(artifact, '.vercel/output/static'), files);
    await saveNew(resolve(artifact, '.vercel/output/config.json'), buildOutputConfig(catalog, publications.bundles));
    await saveNew(resolve(artifact, 'vercel.json'), {
      framework: null,
      buildCommand: null,
      installCommand: null,
      outputDirectory: null,
      public: false,
    });
    const payload = await inventory(artifact);
    const sourceFiles = [];
    for (const folder of ['src', 'types', 'scripts', 'contracts', 'content', 'public', 'tests', 'examples']) {
      sourceFiles.push(...(await inventory(resolve(app, folder))).map(file => ({
        ...file,
        path: `${folder}/${file.path}`,
      })));
    }
    for (const path of [
      'package.json', 'package-lock.json', 'next.config.ts', 'next-env.d.ts',
      'tsconfig.json', 'eslint.config.mjs', '.npmrc', 'vercel.json',
    ]) {
      const bytes = await readFile(resolve(app, path));
      sourceFiles.push({ path, bytes: bytes.length, sha256: hash(bytes) });
    }
    sourceFiles.sort((a, b) => a.path.localeCompare(b.path, 'en'));
    await copyInventory(app, resolve(generated, 'source'), sourceFiles);
    const gitRevision = (await run('git', ['rev-parse', 'HEAD'], { cwd: workspace })).stdout.trim();
    const appDirectory = relative(workspace, app).split('\\').join('/');
    const isolatedApp = appDirectory !== 'apps/narada';
    const dirty = (await run('git', [
      'status', '--porcelain', '--untracked-files=normal',
      ...(isolatedApp ? ['--ignored=matching'] : []), '--', appDirectory,
    ], { cwd: workspace })).stdout.trim();
    const npm = (await run('npm', ['--version'])).stdout.trim();
    const vercel = (await run(cli, ['--version'])).stdout.trim();
    const routes = [
      { route: '/', file: 'index.html' },
      ...catalog.studies.map(study => ({
        route: `/studies/${study.slug}/`,
        file: `studies/${study.slug}/index.html`,
      })),
      ...publications.bundles.map(bundle => ({
        route: `/reports/${bundle.report.id}/`,
        file: `reports/${bundle.report.id}/index.html`,
      })),
    ];
    const release = {
      schemaVersion: '1.0',
      releaseId: rid,
      preparedAt: new Date().toISOString(),
      status: 'prepared',
      source: {
        gitRevision,
        appDirectory,
        isolatedApp,
        appDirty: !!dirty,
        dirtyStatus: dirty,
        snapshot: `.release-artifacts/${rid}/source`,
        files: sourceFiles,
        sha256: inventoryHash(sourceFiles),
      },
      tools: { node: process.version, npm, vercel },
      lockSha256: hash(await readFile(resolve(app, 'package-lock.json'))),
      catalog: {
        path: 'content/studies.json',
        sha256: hash(await readFile(resolve(app, 'content/studies.json'))),
        studies: catalog.studies.length,
      },
      indexSha256: hash(await readFile(resolve(app, 'public/publications/index.json'))),
      staticJsonDelivery,
      publications: publications.bundles.map(bundle => ({
        id: bundle.report.id,
        sourceRunId: bundle.report.source.runId,
        sourceSha256: bundle.provenance.sourceSha256,
        assets: bundle.provenance.assets,
      })),
      figures: publications.assets,
      downloads: publications.downloads,
      routes,
      staticFiles: files,
      staticSha256: inventoryHash(files),
      artifact: `.release-artifacts/${rid}/deploy`,
      artifactFiles: payload,
      artifactSha256: inventoryHash(payload),
      preparationCommands: ['npm run release:prepare', ...checks.map(check => check.command)],
      verification: checks,
      limitations: [
        'Exact prepared bytes identified and checked; byte-identical rebuild has not been demonstrated.',
        'Generated static payload and necessary source snapshot are retained locally outside Git. No off-device backup verified.',
        'Source audit preserves original research qualifications; see source-audit.json. Hosted and browser gates are recorded separately.',
      ],
    };
    await saveNew(resolve(record, 'release.json'), release);
    await saveNew(resolve(record, 'checksums.json'), {
      artifactSha256: release.artifactSha256,
      files: payload,
    });
    console.log(`Prepared ${rid}: ${catalog.studies.length} studies, ${publications.reports} publications.\nArtifact: ${artifact}\nRecord: ${record}\nNo deployment performed.`);
  } catch (error) {
    await event(record, 'preparation-failed', {
      message: error.message,
      completedChecks: checks.map(check => ({ command: check.command, exitCode: check.exitCode })),
    });
    throw error;
  }
}

async function load() {
  safeId(id);
  const record = resolve(app, 'releases', id);
  const release = await readJson(resolve(record, 'release.json'));
  assert(release.releaseId === id && release.status === 'prepared', 'Incomplete release.');
  assert(release.artifact === `.release-artifacts/${id}/deploy`, 'Unexpected artifact root.');
  const artifact = resolve(app, release.artifact);
  const expected = [...release.artifactFiles];
  assert.equal(inventoryHash(expected), release.artifactSha256, 'Artifact inventory identity mismatch.');
  let target;
  try {
    target = await readJson(resolve(record, 'target.json'));
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  if (target) {
    expected.push({
      path: '.vercel/project.json',
      bytes: jsonBytes({ orgId: target.teamId, projectId: target.projectId, projectName: target.projectName }).length,
      sha256: hash(jsonBytes({ orgId: target.teamId, projectId: target.projectId, projectName: target.projectName })),
    });
  }
  expected.sort((a, b) => a.path.localeCompare(b.path, 'en'));
  await verifyInventory(artifact, expected);
  return { record, release, artifact, target, staticRoot: resolve(artifact, '.vercel/output/static') };
}

async function confirmTarget(ctx) {
  assert(ctx.target, 'Bind an explicitly inspected target before deployment.');
  const result = await run(cli, [
    'project', 'inspect', '--format', 'json', '--non-interactive',
    '--scope', ctx.target.teamSlug, '--cwd', ctx.artifact,
  ]);
  const project = JSON.parse(result.stdout);
  assert.equal(project.id, ctx.target.projectId, 'Vercel linked project differs.');
  assert.equal(project.owner.slug, ctx.target.teamSlug, 'Vercel owner differs.');
  const full = JSON.parse((await run(cli, [
    'api', `/v9/projects/${ctx.target.projectId}?teamId=${ctx.target.teamId}`,
  ])).stdout);
  assert.equal(full.accountId, ctx.target.teamId);
  assert(!full.link, 'Project must remain disconnected from Git.');
  for (const key of ['framework', 'buildCommand', 'installCommand', 'outputDirectory', 'rootDirectory']) {
    assert.equal(full[key] ?? null, null, `Dedicated static project must not use ${key}.`);
  }
  const version = (await run(cli, ['--version'])).stdout.trim();
  assert.equal(version, ctx.release.tools.vercel, 'Deployment CLI differs from prepared tool version.');
}

async function deploy(ctx, environment) {
  await confirmTarget(ctx);
  if (environment === 'production') await requireGate(ctx, 'hosted-preview');
  const commandArgs = [
    ...deployArgs(environment, ctx.target, ctx.artifact),
    '--meta', `naradaRelease=${id}`,
    '--meta', `naradaArtifact=${ctx.release.artifactSha256}`,
  ];
  await event(ctx.record, 'deployment-attempt', {
    environment,
    command: [cli, ...commandArgs],
    artifactSha256: ctx.release.artifactSha256,
  });
  let url;
  try {
    const result = await run(cli, commandArgs);
    const deployed = deploymentResult(result.stdout);
    url = deployed.url;
    const info = JSON.parse((await run(cli, [
      'api', `/v13/deployments/${deployed.id}?teamId=${ctx.target.teamId}`,
    ])).stdout);
    assert.equal(info.target ?? 'preview', environment);
    assert.equal(info.projectId, ctx.target.projectId);
    assert.equal(info.readyState, 'READY');
    await event(ctx.record, 'deployed', {
      environment,
      url,
      deploymentId: info.id,
      target: ctx.target,
      artifactSha256: ctx.release.artifactSha256,
      readyState: info.readyState,
    });
    console.log(`${environment}: ${url} (${info.id})`);
  } catch (error) {
    await event(ctx.record, 'deployment-failed-or-unknown', {
      environment,
      url: url ?? null,
      message: error.message,
      exitCode: error.code ?? null,
    });
    throw error;
  }
}

try {
  if (action === 'prepare') {
    await prepare();
  } else {
    const ctx = await load();
    if (action === 'check') {
      console.log(`Exact artifact inventory verified: ${ctx.release.artifactSha256}`);
    } else if (action === 'bind') {
      assert(args.length === 4, 'Bind expects team ID, team slug, project ID, project name.');
      assert(!ctx.target, 'Target already bound.');
      const target = {
        teamId: args[0],
        teamSlug: args[1],
        projectId: args[2],
        projectName: args[3],
      };
      deployArgs('preview', target, ctx.artifact);
      const project = JSON.parse((await run(cli, [
        'project', 'inspect', target.projectName, '--scope', target.teamSlug,
        '--format', 'json', '--non-interactive',
      ])).stdout);
      assert.equal(project.id, target.projectId);
      assert.equal(project.owner.slug, target.teamSlug);
      const full = JSON.parse((await run(cli, [
        'api', `/v9/projects/${target.projectId}?teamId=${target.teamId}`,
      ])).stdout);
      assert.equal(full.accountId, target.teamId);
      assert(!full.link, 'Git-connected project rejected.');
      await saveNew(resolve(ctx.artifact, '.vercel/project.json'), {
        orgId: target.teamId,
        projectId: target.projectId,
        projectName: target.projectName,
      });
      await saveNew(resolve(ctx.record, 'target.json'), target);
      console.log('Explicit target bound.');
    } else if (action === 'preview') {
      await deploy(ctx, 'preview');
    } else if (action === 'stage') {
      await deploy(ctx, 'production');
    } else if (action === 'hosted') {
      const [environment, origin, access] = args;
      assert(['preview', 'staged-production', 'production'].includes(environment), 'Invalid hosted gate.');
      assert(!access || access === '--protected', 'Use --protected only for protected deployment verification.');
      assert(environment !== 'production' || !access, 'Public production must be checked anonymously.');
      if (access) await confirmTarget(ctx);
      const info = JSON.parse((await run(cli, [
        'api', `/v13/deployments/${new URL(origin).hostname}?teamId=${ctx.target.teamId}`,
      ])).stdout);
      assert.equal(info.projectId, ctx.target.projectId);
      assert.equal(info.meta.naradaRelease, id);
      assert.equal(info.meta.naradaArtifact, ctx.release.artifactSha256);
      if (environment === 'preview') {
        assert.equal(info.target ?? 'preview', 'preview');
      } else {
        assert.equal(info.target, 'production');
      }
      const check = await checkHosted(
        ctx.release,
        ctx.staticRoot,
        origin,
        access ? protectedGet(cli, origin, ctx.target, ctx.artifact) : undefined,
      );
      if (access) {
        check.authentication = 'authenticated Vercel CLI curl; no protection change, secrets, cookies or auth state retained';
      }
      check.command = `npm run release -- hosted ${id} ${environment} ${origin}${access ? ' --protected' : ''}`;
      await event(ctx.record, `hosted-${environment}`, { ...check, artifactSha256: ctx.release.artifactSha256 });
      console.log(`Hosted ${environment}: ${check.filesChecked} exact files and five 404s passed.`);
    } else if (action === 'promote') {
      const [url] = args;
      await confirmTarget(ctx);
      await requireGate(ctx, 'hosted-staged-production', url);
      await requireGate(ctx, 'browser-preview');
      const info = JSON.parse((await run(cli, [
        'api', `/v13/deployments/${new URL(url).hostname}?teamId=${ctx.target.teamId}`,
      ])).stdout);
      assert.equal(info.projectId, ctx.target.projectId);
      assert.equal(info.target, 'production');
      assert.equal(info.readyState, 'READY');
      await event(ctx.record, 'promotion-attempt', {
        deploymentId: info.id,
        url,
        artifactSha256: ctx.release.artifactSha256,
      });
      await run(cli, ['promote', url, '--scope', ctx.target.teamSlug, '--cwd', ctx.artifact, '--non-interactive']);
      await event(ctx.record, 'promoted', {
        deploymentId: info.id,
        url,
        artifactSha256: ctx.release.artifactSha256,
      });
      console.log(`Promoted staged production ${info.id}. Run the public production hosted gate.`);
    } else {
      throw new Error('Use prepare | check <id> | bind <id> <teamId> <teamSlug> <projectId> <projectName> | preview <id> | stage <id> | hosted <id> <environment> <origin> | promote <id> <staged-url>.');
    }
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
