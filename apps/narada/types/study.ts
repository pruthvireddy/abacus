export type RelatedPublication = {
  publicationId: string;
  sourceRunId: string;
  relationship: "other-run" | "exploratory-supplement" | "presentation-revision";
  label: string;
};
export type PublicationTab = {
  publicationId: string;
  sourceRunId: string;
  label: string;
};
export type StudyAnalysis = {
  id: string;
  label: string;
  publicationTabs: PublicationTab[];
};
export type StudyPhaseFamily = {
  id: string;
  label: string;
  analyses: StudyAnalysis[];
};
export type Study = {
  studyId: string;
  slug: string;
  title: string;
  summary: string;
  topic: string;
  products: string[];
  evidenceStatus: string;
  featuredPublicationId: string;
  featuredSourceRunId: string;
  publicationTabs?: PublicationTab[];
  analyses?: StudyAnalysis[];
  phaseFamilies?: StudyPhaseFamily[];
  relatedPublications?: RelatedPublication[];
};
export type StudyCatalog = { schemaVersion: "1.0"; studies: Study[] };
