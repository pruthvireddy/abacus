// Pure authored-navigation projections, independent of schemas, cwd and I/O.
export const studyAnalyses = study => study.phaseFamilies?.flatMap(family => family.analyses)
  ?? study.analyses ?? [];
export const publicationGroups = study => {
  const analyses = studyAnalyses(study);
  return analyses.length ? analyses.map(analysis => analysis.publicationTabs)
    : (study.publicationTabs?.length ? [study.publicationTabs] : []);
};
export const familyPublicationSelection = (family, currentAnalysisId, currentChartLabel) => {
  const analysis = family.analyses.find(candidate => candidate.id === currentAnalysisId) ?? family.analyses[0];
  const tab = analysis.publicationTabs.find(candidate => candidate.label === currentChartLabel) ?? analysis.publicationTabs[0];
  return { analysis, tab };
};
export const studyPublicationReferences = study => [
  ...(studyAnalyses(study).length ? studyAnalyses(study).flatMap(analysis => analysis.publicationTabs)
    : [{ publicationId: study.featuredPublicationId, sourceRunId: study.featuredSourceRunId }, ...(study.publicationTabs ?? []).slice(1)]),
  ...(study.relatedPublications ?? []),
];
