// Pure static route ownership. These destinations do not select publications or
// infer research structure; the authored catalog remains the sole study registry.
export const STUDY_DESTINATIONS = Object.freeze([
  { key: 'overview', path: '', label: 'Overview' },
  { key: 'findings', path: 'findings', label: 'Findings' },
  { key: 'explore', path: 'explore', label: 'Explore' },
  { key: 'methods', path: 'methods', label: 'Method & scope' },
  { key: 'evidence', path: 'evidence', label: 'Evidence' },
].map(destination => Object.freeze(destination)));
const safeSlug = value => typeof value === 'string' && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
export function studyDestinationHref(slug, key = 'overview') {
  if (!safeSlug(slug)) throw new Error('A static study route requires a safe catalog slug.');
  const destination = STUDY_DESTINATIONS.find(candidate => candidate.key === key);
  if (!destination) throw new Error('Unknown study destination.');
  return `/studies/${slug}/${destination.path ? `${destination.path}/` : ''}`;
}
export const studyPageRoutes = (catalog, { legacyStudyRoutes = false } = {}) => catalog.studies.flatMap(study =>
  (legacyStudyRoutes ? STUDY_DESTINATIONS.slice(0, 1) : STUDY_DESTINATIONS).map(destination => studyDestinationHref(study.slug, destination.key)));
export const pageRoutes = (catalog, publications, options) => ['/', ...studyPageRoutes(catalog, options),
  ...publications.map(publication => {
    const id = publication.report?.id ?? publication.id;
    if (!safeSlug(id)) throw new Error('A static report route requires a safe publication ID.');
    return `/reports/${id}/`;
  })];
export const pageRouteFile = route => route === '/' ? 'index.html' : `${route.slice(1)}index.html`;

// Legacy study pages embedded the featured publication. Fragments are resolved
// by browsers, so static visible links keep those destinations meaningful without
// pretending an HTTP redirect can inspect the fragment.
export function legacyStudyAnchors(publication) {
  const report = publication.report ?? publication;
  const link = (id, label) => ({ id, label, href: `/reports/${report.id}/#${id}` });
  const usedPatterns = new Set([report.patternOverviewId, ...report.sections.map(section => section.patternId)].filter(Boolean));
  return [
    ...report.sections.flatMap(section => [link(`section-${section.id}`, section.title),
      { ...link(`heading-${section.id}`, `${section.title}: heading`), href: `/reports/${report.id}/#section-${section.id}` }]),
    ...(report.downloads?.length ? [link('publication-downloads', 'Selected evidence downloads'),
      ...report.downloads.map(download => link(`download-${download.id}`, download.label))] : []),
    ...(report.references?.length ? [link('publication-references', 'Source references'),
      ...report.references.map(reference => link(`reference-${reference.id}`, reference.label))] : []),
    ...(report.notes?.length ? [link('publication-notes', 'Notes')] : []),
    ...(report.patterns ?? []).filter(pattern => usedPatterns.has(pattern.id)).map(pattern => link(`pattern-key-${pattern.id}`, `${pattern.title}: pattern key`)),
  ];
}
