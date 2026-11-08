import { createHash } from 'node:crypto';
import { lstat, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { studyPublicationReferences } from './study-selections.mjs';

const assert = (condition, message) => { if (!condition) throw new Error(message); };
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
// Type-tag metadata and encode numbers as normalized IEEE-754 bytes so Python
// and JavaScript bind the same authored selectors without float spelling drift.
const bindingValue = value => {
  if (value === null) return ['null'];
  if (typeof value === 'number') {
    assert(Number.isFinite(value), 'Nonfinite priority metadata.');
    const bytes = Buffer.alloc(8); bytes.writeDoubleBE(value === 0 ? 0 : value);
    return ['number', bytes.toString('hex')];
  }
  if (Array.isArray(value)) return ['array', value.map(bindingValue)];
  if (typeof value === 'object') return ['object', Object.keys(value).sort().map(key => [key, bindingValue(value[key])])];
  return [typeof value, value];
};
const hash = value => createHash('sha256').update(`${JSON.stringify(bindingValue(value))}\n`).digest('hex');
const reportHash = value => createHash('sha256').update(`${JSON.stringify(stable(value), null, 2)}\n`).digest('hex');
export const PRIORITY_BAND_LABELS = ['Pause', 'Define and test', 'Targeted follow-up', 'Strong candidate', 'Highest priority'];

// Bind all authored scope/claims/selections. Generated assessment fields and
// resolved saved values are excluded; file dates are never freshness evidence.
export function priorityStudyScope(study) {
  return Object.fromEntries(Object.entries(study).filter(([key]) =>
    !['researchPriority', 'resolvedResearchPriority', 'resolvedOverview'].includes(key)));
}
export const priorityStudyHash = study => hash(priorityStudyScope(study));
export const priorityRubricHash = rubric => hash({ guideSha256: rubric.sourceSha256,
  rubric: Object.fromEntries(['version', 'meaning', 'disclaimer', 'bands'].map(key => [key, rubric[key]])) });
export const priorityEvidence = priority => [...priority.supporting, ...priority.contrary,
  ...Object.values(priority.highPriorityEvidence ?? {})];
export const prioritySources = priority => priorityEvidence(priority).map(item => item.source);
export const priorityHref = source => `/reports/${source.publicationId}/#section-${source.sectionId}`;

export function validatePriorityReferences(catalog, publications, publicText = () => {}) {
  const reports = new Map(publications.map(report => [report.id, report]));
  const owners = new Map(catalog.studies.flatMap(study => studyPublicationReferences(study).map(ref => [ref.publicationId, study.studyId])));
  const rubric = catalog.researchPriorityRubric;
  if (rubric) {
    assert(rubric.bands.every((band, index) => band.score === index + 1 && band.label === PRIORITY_BAND_LABELS[index]), 'Priority rubric must define all five ordered bands.');
    for (const text of [rubric.meaning, rubric.disclaimer, ...rubric.bands.flatMap(band => [band.label, band.definition])]) publicText(text);
  }
  const ids = new Set();
  for (const study of catalog.studies) {
    const priority = study.researchPriority;
    if (!priority) continue;
    assert(rubric, 'Research-priority assessments require a published rubric.');
    assert(!ids.has(priority.assessmentId), 'Research-priority assessment IDs must be unique.');
    ids.add(priority.assessmentId);
    assert(new Date(`${priority.reviewedAt}T00:00:00Z`).toISOString().slice(0, 10) === priority.reviewedAt, 'Priority review date must be a real calendar date.');
    for (const text of [priority.assessmentId, priority.reviewer, priority.scope, priority.rationale, priority.materiality,
      priority.blocker, ...Object.values(priority.nextTest), ...priorityEvidence(priority).map(item => item.text),
      ...(priority.reassessment ? [priority.reassessment.reason] : [])]) publicText(text);
    if ((priority.score ?? 0) >= 4) {
      const proof = priority.highPriorityEvidence;
      assert(proof?.executionAndCosts && proof?.separatedEvaluation && proof?.materialEffect, 'Four/five priority needs explicit execution/cost, separated-evaluation and material-effect evidence.');
      if (priority.score === 5) assert(proof.independentCorroboration, 'Five priority needs explicit independent corroboration evidence.');
    }
    const reviewed = new Map();
    for (const source of priority.reviewedPublications) {
      assert(!reviewed.has(source.publicationId), 'Priority reviewed publications must not repeat.');
      reviewed.set(source.publicationId, source);
      const report = reports.get(source.publicationId);
      assert(report, `Missing priority evidence publication: ${source.publicationId}.`);
      assert(!owners.has(source.publicationId) || owners.get(source.publicationId) === study.studyId, 'Priority evidence belongs to another study.');
      assert(report.source.runId === source.sourceRunId && report.sourceSha256 === source.sourceSha256,
        `Invalid priority evidence identity: ${source.publicationId}.`);
    }
    for (const source of prioritySources(priority)) {
      const bound = reviewed.get(source.publicationId);
      assert(bound && bound.sourceRunId === source.sourceRunId && bound.sourceSha256 === source.sourceSha256,
        'Priority explanation must cite an exactly reviewed publication.');
    }
  }
}

export function priorityFreshness(study, rubric, publications) {
  const p = study.researchPriority;
  if (!p) return { effectiveState: 'not_assessed', staleReasons: [] };
  const reasons = [];
  if (!rubric || p.rubricVersion !== rubric.version || p.rubricSha256 !== priorityRubricHash(rubric)) reasons.push('The rubric changed after this assessment.');
  if (p.reviewedStudySha256 !== priorityStudyHash(study)) reasons.push('The authored study scope or publication selection changed after this assessment.');
  const reports = new Map(publications.map(report => [report.id, report]));
  const current = studyPublicationReferences(study).map(source => ({ ...source, sourceSha256: reports.get(source.publicationId)?.sourceSha256 }))
    .map(({ publicationId, sourceRunId, sourceSha256 }) => ({ publicationId, sourceRunId, sourceSha256 }));
  if (hash(current) !== hash(p.reviewedPublications)) reasons.push('The selected evidence set changed; later findings need editorial review.');
  if (p.reassessment?.required) reasons.push(p.reassessment.reason);
  return { effectiveState: reasons.length ? 'needs_review' : p.state, staleReasons: reasons };
}

export async function resolveCatalogPriorities(catalog, publications, { bundles, publicationsRoot = resolve(process.cwd(), 'public/publications') } = {}) {
  const ids = [...new Set(catalog.studies.flatMap(study => study.researchPriority ? prioritySources(study.researchPriority).map(source => source.publicationId) : []))];
  const selected = bundles ?? await Promise.all(ids.map(async id => {
    const directory = resolve(publicationsRoot, id), file = resolve(directory, 'report.json');
    const [d, f] = await Promise.all([lstat(directory), lstat(file)]);
    assert(d.isDirectory() && !d.isSymbolicLink() && f.isFile() && !f.isSymbolicLink() && f.size <= 4 * 1024 * 1024, 'Priority source must be a bounded regular app-owned report bundle.');
    const bytes = await readFile(file);
    assert(bytes.length <= 4 * 1024 * 1024, 'Priority source exceeds its byte budget.');
    const bundle = JSON.parse(bytes.toString('utf8'));
    assert(bundle.provenance?.sourceSha256 === reportHash(bundle.report), 'Priority report content does not match its source hash.');
    return bundle;
  }));
  const byId = new Map(selected.map(bundle => [bundle.report.id, bundle]));
  return { ...catalog, studies: catalog.studies.map(study => {
    const p = study.researchPriority;
    if (!p) return study;
    for (const source of prioritySources(p)) {
      const bundle = byId.get(source.publicationId);
      assert(bundle && bundle.report.source.runId === source.sourceRunId && bundle.provenance.sourceSha256 === source.sourceSha256,
        'Priority evidence source identity is invalid.');
      assert(bundle.report.sections.some(section => section.id === source.sectionId), `Missing priority evidence section: ${source.sectionId}.`);
    }
    const linked = item => ({ ...item, href: priorityHref(item.source) });
    return { ...study, resolvedResearchPriority: { ...p, ...priorityFreshness(study, catalog.researchPriorityRubric, publications),
      supporting: p.supporting.map(linked), contrary: p.contrary.map(linked) } };
  }) };
}
