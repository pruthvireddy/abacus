import Ajv2020 from 'ajv/dist/2020.js';
import { readFile, lstat } from 'node:fs/promises';
import { resolve } from 'node:path';

export const STUDY_CATALOG_MAX_BYTES = 256 * 1024;
export const DEFAULT_STUDY_CATALOG = resolve(process.cwd(), 'content/studies.json');
const schema = JSON.parse(await readFile(resolve(process.cwd(), 'contracts/studies.schema.json'), 'utf8'));
const ajv = new Ajv2020({ allErrors: true, strict: true });
const validate = ajv.compile(schema);
const assert = (condition, message) => { if (!condition) throw new Error(message); };
export const studyHref = slug => `/studies/${slug}/`;
export const findStudy = (catalog, slug) => catalog.studies.find(study => study.slug === slug) ?? null;
export const studyParams = catalog => catalog.studies.map(({ slug }) => ({ slug }));
export function findPublicationStudy(catalog, id) {
  for (const study of catalog.studies) {
    if (study.featuredPublicationId === id) return { study, relation: null };
    const relation = study.relatedPublications?.find(reference => reference.publicationId === id);
    if (relation) return { study, relation };
  }
  return null;
}

// Only authored app metadata and the verified public index are inputs. The run
// IDs are explicit attribution assertions, never inferred from publication dates.
export function validateStudyCatalog(catalog, publications) {
  assert(validate(catalog), `Study catalog does not match its schema: ${ajv.errorsText(validate.errors)}`);
  const ids = new Set(), slugs = new Set(), owners = new Map();
  const reports = new Map(publications.map(report => [report.id, report]));
  for (const study of catalog.studies) {
    assert(!ids.has(study.studyId), 'Study IDs must be unique.'); ids.add(study.studyId);
    assert(!slugs.has(study.slug), 'Study slugs must be unique.'); slugs.add(study.slug);
    const related = study.relatedPublications ?? [];
    for (const text of [study.studyId, study.slug, study.featuredPublicationId, study.featuredSourceRunId,
      study.title, study.summary, study.topic, study.evidenceStatus, ...study.products,
      ...related.flatMap(p => [p.publicationId, p.sourceRunId, p.label])]) {
      assert(text.trim() === text && text.length > 0 && !/[\x00-\x08\x0b-\x1f\x7f]/.test(text), 'Catalog text must be nonblank and free of control characters.');
      assert(!/(?:file:\/\/|\/Users\/|\/home\/|[A-Za-z]:\\|(?:^|\s)(?:studies|runs|reports\/exports)\/)/.test(text), 'Filesystem paths are not public catalog references.');
    }
    const selected = [{ publicationId: study.featuredPublicationId, sourceRunId: study.featuredSourceRunId }, ...(study.relatedPublications ?? [])];
    const seen = new Set();
    for (const reference of selected) {
      assert(!seen.has(reference.publicationId), 'Featured and related publication references must not repeat.'); seen.add(reference.publicationId);
      const report = reports.get(reference.publicationId);
      assert(report, `Missing publication ${reference.publicationId} for ${study.studyId}.`);
      assert(report.source.producer === 'sahadeva' && report.source.runId === reference.sourceRunId, `Publication attribution disagrees with ${study.studyId}: ${reference.publicationId}.`);
      assert(!owners.has(reference.publicationId), 'A publication must belong to only one study.'); owners.set(reference.publicationId, study.studyId);
      if (reference.relationship) {
        const sameRun = reference.sourceRunId === study.featuredSourceRunId;
        assert(reference.relationship === 'presentation-revision' ? sameRun : !sameRun, 'Relationship must agree with source-run identity.');
      }
    }
  }
  return catalog;
}

export async function readStudyCatalog(publications, file = DEFAULT_STUDY_CATALOG) {
  const info = await lstat(file);
  assert(info.isFile() && !info.isSymbolicLink(), 'Study catalog must be a regular file.');
  assert(info.size <= STUDY_CATALOG_MAX_BYTES, 'Study catalog exceeds its byte budget.');
  const bytes = await readFile(file);
  assert(bytes.length <= STUDY_CATALOG_MAX_BYTES, 'Study catalog exceeds its byte budget.');
  return validateStudyCatalog(JSON.parse(bytes.toString('utf8')), publications);
}
