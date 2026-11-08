import { lstat, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { studyPublicationReferences } from './study-selections.mjs';

// The server renderer has no dependency on the publisher or its operational
// filesystem discovery. The ordinary prebuild verifier performs the full report
// schema/assets checks; these selected reads additionally check content identity.
const DEFAULT_PUBLICATIONS_ROOT = resolve(process.cwd(), 'public/publications');
const MAX_OVERVIEW_BUNDLE_BYTES = 4 * 1024 * 1024;
const stable = value => Array.isArray(value) ? value.map(stable)
  : value !== null && typeof value === 'object'
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
const reportHash = report => createHash('sha256').update(`${JSON.stringify(stable(report), null, 2)}\n`).digest('hex');

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

export const overviewHref = source => `/reports/${source.publicationId}/#section-${source.sectionId}`;
export const overviewSources = overview => [overview.source, ...(overview.methodSource ? [overview.methodSource] : []),
  ...overview.statistics.map(item => item.source),
  ...overview.findings.map(item => item.source),
  ...overview.limitations.map(item => item.source),
  ...overview.links.map(item => item.source)];

// Catalog ownership remains authoritative. An overview can abridge only a
// publication already explicitly selected by that study, including related runs.
export function validateOverviewReferences(study, publications) {
  if (!study.overview) return;
  const selected = new Map(studyPublicationReferences(study).map(reference => [reference.publicationId, reference]));
  const reports = new Map(publications.map(report => [report.id, report]));
  for (const source of overviewSources(study.overview)) {
    const reference = selected.get(source.publicationId);
    const report = reports.get(source.publicationId);
    assert(reference && report, `Overview source must be a selected publication: ${source.publicationId}.`);
    assert(reference.sourceRunId === source.sourceRunId && report.source.runId === source.sourceRunId,
      `Overview source-run attribution disagrees: ${source.publicationId}.`);
    if (report.sourceSha256 !== undefined) {
      assert(report.sourceSha256 === source.sourceSha256, `Overview content identity disagrees: ${source.publicationId}.`);
    }
  }
}

function unique(values, label) {
  assert(values.length === 1, `Overview ${label} must resolve uniquely; found ${values.length}.`);
  return values[0];
}

export function resolveOverviewStatistic(statistic, section) {
  const common = { label: statistic.label, context: statistic.context, source: statistic.source, href: overviewHref(statistic.source) };
  if (Object.hasOwn(statistic, 'text')) return { ...common, text: statistic.text };
  const selection = statistic.selection;
  if (selection.kind === 'metric') {
    assert(section.kind === 'metrics', 'Overview metric selector requires a metrics section.');
    const metric = unique(section.items.filter(item => item.label === selection.label), 'metric selector');
    // Copy saved formatting and qualification. Do not reinterpret units or turn
    // missing/null/false/zero into each other through truthiness defaults.
    const { value, format, precision, unit, note } = metric;
    return { ...common, value, format, ...(precision !== undefined ? { precision } : {}),
      ...(unit !== undefined ? { unit } : {}), ...(note !== undefined ? { note } : {}) };
  }
  assert(section.kind === 'table', 'Overview table-cell selector requires a table section.');
  const column = unique(section.columns.filter(candidate => candidate.key === selection.columnKey), 'table column');
  const keys = new Set(section.columns.map(candidate => candidate.key));
  assert(Object.keys(selection.where).every(key => keys.has(key)), 'Overview row selector uses an unknown column.');
  const row = unique(section.rows.filter(candidate => Object.entries(selection.where).every(([key, value]) =>
    Object.hasOwn(candidate, key) && candidate[key] === value)), 'table row selector');
  assert(Object.hasOwn(row, column.key), 'Overview selected table cell is missing; it is not a saved null.');
  const { format, precision, unit } = column;
  return { ...common, value: row[column.key], ...(format !== undefined ? { format } : {}),
    ...(precision !== undefined ? { precision } : {}), ...(unit !== undefined ? { unit } : {}),
    ...(section.description !== undefined ? { description: section.description } : {}),
    ...(section.notes !== undefined ? { notes: [...section.notes] } : {}) };
}

export function resolveStudyOverview(study, bundles) {
  if (!study.overview) return undefined;
  validateOverviewReferences(study, bundles.map(bundle => ({ ...bundle.report, sourceSha256: bundle.provenance.sourceSha256 })));
  const overview = study.overview;
  const sectionFor = source => {
    const bundle = unique(bundles.filter(candidate => candidate.report.id === source.publicationId), 'publication source');
    assert(bundle.report.source.producer === 'sahadeva' && bundle.report.source.runId === source.sourceRunId,
      `Overview source-run attribution disagrees: ${source.publicationId}.`);
    assert(bundle.provenance.sourceSha256 === source.sourceSha256,
      `Overview content identity disagrees: ${source.publicationId}.`);
    return unique(bundle.report.sections.filter(section => section.id === source.sectionId), 'source section');
  };
  for (const source of overviewSources(overview)) sectionFor(source);
  const linked = item => ({ ...item, href: overviewHref(item.source) });
  return { ...overview, href: overviewHref(overview.source), methodHref: overviewHref(overview.methodSource ?? overview.source),
    statistics: overview.statistics.map(statistic => resolveOverviewStatistic(statistic, sectionFor(statistic.source))),
    findings: overview.findings.map(linked), limitations: overview.limitations.map(linked), links: overview.links.map(linked) };
}

// Only explicitly referenced app-owned staged bundles are read. No research
// directory, arbitrary path or browser-side report request participates.
export async function resolveCatalogOverviews(catalog, { bundles, publicationsRoot = DEFAULT_PUBLICATIONS_ROOT } = {}) {
  const ids = [...new Set(catalog.studies.flatMap(study => study.overview
    ? overviewSources(study.overview).map(source => source.publicationId) : []))];
  const selectedBundles = bundles ?? await Promise.all(ids.map(async id => {
    const directory = resolve(publicationsRoot, id);
    const file = resolve(directory, 'report.json');
    const [directoryInfo, info] = await Promise.all([lstat(directory), lstat(file)]);
    assert(directoryInfo.isDirectory() && !directoryInfo.isSymbolicLink() && info.isFile() && !info.isSymbolicLink(),
      'Overview publication must be a regular staged bundle.');
    assert(info.size <= MAX_OVERVIEW_BUNDLE_BYTES, 'Overview publication exceeds its byte budget.');
    const bytes = await readFile(file);
    assert(bytes.length <= MAX_OVERVIEW_BUNDLE_BYTES, 'Overview publication exceeds its byte budget.');
    const bundle = JSON.parse(bytes.toString('utf8'));
    assert(bundle.report && bundle.provenance?.sourceSha256 === reportHash(bundle.report), 'Report content does not match its source hash.');
    return bundle;
  }));
  return { ...catalog, studies: catalog.studies.map(study => study.overview
    ? { ...study, resolvedOverview: resolveStudyOverview(study, selectedBundles) } : study) };
}
