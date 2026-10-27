import Ajv2020 from 'ajv/dist/2020.js';
import { readFile, lstat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { publicationGroups, studyPublicationReferences, studyAnalyses, familyPublicationSelection } from './study-selections.mjs';
import { overviewSources, validateOverviewReferences, resolveCatalogOverviews } from './study-overviews.mjs';
import { validatePriorityReferences, resolveCatalogPriorities } from './research-priorities.mjs';
export { publicationGroups, studyPublicationReferences, studyAnalyses, familyPublicationSelection };
export const STUDY_CATALOG_MAX_BYTES = 512 * 1024;
export const DEFAULT_STUDY_CATALOG = resolve(process.cwd(), 'content/studies.json');
const schema = JSON.parse(await readFile(resolve(process.cwd(), 'contracts/studies.schema.json'), 'utf8'));
const ajv = new Ajv2020({ allErrors: true, strict: true });
const validate = ajv.compile(schema);
const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message);
  }
};
function hasCatalogControl(text) {
  return Array.from(text).some(character => {
    const code = character.codePointAt(0);
    return (code <= 31 || code === 127) && code !== 9 && code !== 10;
  });
}
function assertPublicCatalogText(text) {
  assert(text.trim() === text && text.length > 0 && !hasCatalogControl(text), 'Catalog text must be nonblank and free of control characters.');
  assert(!/(?:file:\/\/|\/Users\/|\/home\/|[A-Za-z]:\\|(?:^|\s)(?:studies|runs|reports\/exports)\/)/.test(text), 'Filesystem paths are not public catalog references.');
}
export const studyHref = slug => `/studies/${slug}/`;
export const findStudy = (catalog, slug) => catalog.studies.find(study => study.slug === slug) ?? null;
export const studyParams = catalog => catalog.studies.map(({ slug }) => ({ slug }));
export function findPublicationStudy(catalog, id) {
  for (const study of catalog.studies) {
    const family = study.phaseFamilies?.find(candidate => candidate.analyses.some(analysis => analysis.publicationTabs.some(reference => reference.publicationId === id)));
    if (family) {
      const analysis = family.analyses.find(candidate => candidate.publicationTabs.some(reference => reference.publicationId === id));
      return { study, relation: null, family, analysis, tab: analysis.publicationTabs.find(reference => reference.publicationId === id) };
    }
    const analysis = study.analyses?.find(group => group.publicationTabs.some(reference => reference.publicationId === id));
    if (analysis) {
      return { study, relation: null, tab: analysis.publicationTabs.find(reference => reference.publicationId === id), analysis, family: null };
    }
    if (study.featuredPublicationId === id) {
      return { study, relation: null, tab: study.publicationTabs?.find(reference => reference.publicationId === id) ?? null, analysis: null, family: null };
    }
    const tab = study.publicationTabs?.find(reference => reference.publicationId === id);
    if (tab) {
      return { study, relation: null, tab, analysis: null, family: null };
    }
    const relation = study.relatedPublications?.find(reference => reference.publicationId === id);
    if (relation) {
      return { study, relation, tab: null, analysis: null, family: null };
    }
  }
  return null;
}
// Only authored app metadata and the verified public index are inputs. The run
// IDs are explicit attribution assertions, never inferred from publication dates.
export function validateStudyCatalog(catalog, publications) {
  assert(validate(catalog), `Study catalog does not match its schema: ${ajv.errorsText(validate.errors)}`);
  const ids = new Set();
  const slugs = new Set();
  const owners = new Map();
  const reports = new Map(publications.map(report => [report.id, report]));
  for (const study of catalog.studies) {
    assert(!ids.has(study.studyId), 'Study IDs must be unique.');
    ids.add(study.studyId);
    assert(!slugs.has(study.slug), 'Study slugs must be unique.');
    slugs.add(study.slug);
    const related = study.relatedPublications ?? [];
    const tabs = study.publicationTabs ?? [];
    const analyses = studyAnalyses(study);
    const families = study.phaseFamilies ?? [];
    for (const text of [study.studyId, study.slug, study.featuredPublicationId, study.featuredSourceRunId,
      study.title, study.summary, study.topic, study.evidenceStatus, ...study.products, ...(study.keywords ?? []),
      ...related.flatMap(p => [p.publicationId, p.sourceRunId, p.label]),
      ...tabs.flatMap(p => [p.publicationId, p.sourceRunId, p.label]),
      ...families.flatMap(family => [family.id, family.label]),
      ...analyses.flatMap(analysis => [analysis.id, analysis.label, ...analysis.publicationTabs.flatMap(p => [p.publicationId, p.sourceRunId, p.label])]),
      ...(study.overview ? [study.overview.question, study.overview.takeaway, study.overview.evidenceType,
        study.overview.population, study.overview.period, study.overview.sampleScope,
        study.overview.qualification, study.overview.method,
        ...study.overview.statistics.flatMap(item => [item.label, item.context, item.text, item.selection?.label, item.selection?.columnKey]),
        ...study.overview.findings.map(item => item.text), ...study.overview.limitations.map(item => item.text),
        ...study.overview.links.map(item => item.label), ...overviewSources(study.overview).flatMap(source => Object.values(source))]
        .filter(text => text !== undefined) : [])]) {
      assertPublicCatalogText(text);
    }
    assert(new Set((study.keywords ?? []).map(keyword => keyword.toLowerCase())).size === (study.keywords ?? []).length,
      'Study keywords must be unique without case distinctions.');
    if (tabs.length) {
      assert(tabs[0].publicationId === study.featuredPublicationId, 'The first publication tab must be the featured publication.');
      assert(new Set(tabs.map(tab => tab.publicationId)).size === tabs.length, 'Publication tabs must not repeat.');
      assert(new Set(tabs.map(tab => tab.label)).size === tabs.length, 'Publication tab labels must be unique.');
      assert(tabs.every(tab => tab.sourceRunId === study.featuredSourceRunId), 'Publication tabs must share the featured source run.');
    }
    if (analyses.length) {
      const scopes = families.length ? families.map(family => family.analyses) : [analyses];
      for (const scope of scopes) {
        assert(new Set(scope.map(analysis => analysis.id)).size === scope.length, 'Study analysis IDs must be unique within their phase family.');
        assert(new Set(scope.map(analysis => analysis.label)).size === scope.length, 'Study analysis labels must be unique within their phase family.');
      }
      assert(analyses[0].publicationTabs[0].publicationId === study.featuredPublicationId
        && analyses[0].publicationTabs[0].sourceRunId === study.featuredSourceRunId,
      'The first analysis must start with the featured publication and source run.');
      for (const analysis of analyses) {
        assert(new Set(analysis.publicationTabs.map(tab => tab.label)).size === analysis.publicationTabs.length, 'Publication tab labels must be unique within each analysis.');
        assert(analysis.publicationTabs.every(tab => tab.sourceRunId === analysis.publicationTabs[0].sourceRunId),
          'Publication tabs must share their analysis source run.');
      }
    }
    if (families.length) {
      assert(new Set(families.map(family => family.id)).size === families.length, 'Study phase family IDs must be unique.');
      assert(new Set(families.map(family => family.label)).size === families.length, 'Study phase family labels must be unique.');
    }
    const selected = studyPublicationReferences(study);
    const seen = new Set();
    for (const reference of selected) {
      assert(!seen.has(reference.publicationId), 'Selected publication references must not repeat.');
      seen.add(reference.publicationId);
      const report = reports.get(reference.publicationId);
      assert(report, `Missing publication ${reference.publicationId} for ${study.studyId}.`);
      assert(report.source.producer === 'sahadeva' && report.source.runId === reference.sourceRunId, `Publication attribution disagrees with ${study.studyId}: ${reference.publicationId}.`);
      assert(!owners.has(reference.publicationId), 'A publication must belong to only one study.');
      owners.set(reference.publicationId, study.studyId);
      if (reference.relationship) {
        const sameRun = reference.sourceRunId === study.featuredSourceRunId;
        assert(reference.relationship === 'presentation-revision' ? sameRun : !sameRun, 'Relationship must agree with source-run identity.');
      }
    }
    validateOverviewReferences(study, publications);
  }
  const pathIds = new Set();
  const pathTitles = new Set();
  for (const path of catalog.readingPaths ?? []) {
    for (const text of [path.id, path.title, path.description, path.qualification,
      ...path.steps.flatMap(step => [step.studyId, step.destination, step.reason])]) assertPublicCatalogText(text);
    assert(!pathIds.has(path.id), 'Reading path IDs must be unique.');
    assert(!pathTitles.has(path.title), 'Reading path titles must be unique.');
    pathIds.add(path.id);
    pathTitles.add(path.title);
    const stepIds = new Set();
    for (const step of path.steps) {
      assert(ids.has(step.studyId), `Reading path references an unknown study: ${step.studyId}.`);
      assert(!stepIds.has(step.studyId), 'A reading path must not repeat a study.');
      stepIds.add(step.studyId);
    }
  }
  validatePriorityReferences(catalog, publications, assertPublicCatalogText);
  return catalog;
}
export async function readStudyCatalog(publications, file = DEFAULT_STUDY_CATALOG, options = {}) {
  const info = await lstat(file);
  assert(info.isFile() && !info.isSymbolicLink(), 'Study catalog must be a regular file.');
  assert(info.size <= STUDY_CATALOG_MAX_BYTES, 'Study catalog exceeds its byte budget.');
  const bytes = await readFile(file);
  assert(bytes.length <= STUDY_CATALOG_MAX_BYTES, 'Study catalog exceeds its byte budget.');
  // Operational callers already hold publisher-verified bundles, while the
  // renderer uses public index records. Preserve exact content identity in both.
  const supplied = new Map((options.bundles ?? []).map(bundle => [bundle.report.id, bundle.provenance.sourceSha256]));
  const reports = publications.map(report => report.sourceSha256 === undefined && supplied.has(report.id)
    ? { ...report, sourceSha256: supplied.get(report.id) } : report);
  const catalog = validateStudyCatalog(JSON.parse(bytes.toString('utf8')), reports);
  return resolveCatalogPriorities(await resolveCatalogOverviews(catalog, options), reports, options);
}
