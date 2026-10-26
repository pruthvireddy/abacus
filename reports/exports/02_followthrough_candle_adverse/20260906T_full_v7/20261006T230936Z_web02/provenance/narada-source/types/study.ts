export type RelatedPublication = {
  publicationId: string;
  sourceRunId: string;
  relationship: "other-run" | "exploratory-supplement" | "presentation-revision";
  label: string;
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
  relatedPublications?: RelatedPublication[];
};
export type StudyCatalog = { schemaVersion: "1.0"; studies: Study[] };
