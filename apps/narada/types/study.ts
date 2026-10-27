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
export type OverviewSource = {
  publicationId: string;
  sourceRunId: string;
  sourceSha256: string;
  sectionId: string;
};
export type OverviewSelection = { kind: "metric"; label: string } | {
  kind: "table-cell";
  columnKey: string;
  where: Record<string, string | number | boolean | null>;
};
type OverviewStatisticBase = { label: string; context: string; source: OverviewSource };
export type OverviewStatistic = OverviewStatisticBase & ({ text: string } | { selection: OverviewSelection });
export type OverviewClaim = { text: string; source: OverviewSource };
export type OverviewLink = { label: string; source: OverviewSource };
export type StudyOverview = {
  question: string;
  takeaway: string;
  evidenceType: string;
  population: string;
  period?: string;
  sampleScope?: string;
  qualification: string;
  method: string;
  source: OverviewSource;
  methodSource?: OverviewSource;
  statistics: OverviewStatistic[];
  findings: OverviewClaim[];
  limitations: OverviewClaim[];
  links: OverviewLink[];
};
export type ResolvedOverviewStatistic = OverviewStatisticBase & {
  href: string;
  text?: string;
  value?: string | number | boolean | null;
  format?: "number" | "percent";
  precision?: number;
  unit?: string;
  note?: string;
  description?: string;
  notes?: string[];
};
export type ResolvedStudyOverview = Omit<StudyOverview, "statistics" | "findings" | "limitations" | "links"> & {
  href: string;
  methodHref: string;
  statistics: ResolvedOverviewStatistic[];
  findings: Array<OverviewClaim & { href: string }>;
  limitations: Array<OverviewClaim & { href: string }>;
  links: Array<OverviewLink & { href: string }>;
};
export type Study = {
  studyId: string;
  slug: string;
  title: string;
  summary: string;
  topic: string;
  keywords?: string[];
  products: string[];
  evidenceStatus: string;
  featuredPublicationId: string;
  featuredSourceRunId: string;
  publicationTabs?: PublicationTab[];
  analyses?: StudyAnalysis[];
  phaseFamilies?: StudyPhaseFamily[];
  relatedPublications?: RelatedPublication[];
  overview?: StudyOverview;
  resolvedOverview?: ResolvedStudyOverview;
  researchPriority?: PublicResearchPriority;
  resolvedResearchPriority?: ResolvedResearchPriority;
};
export type ReadingPathStep = { studyId: string; destination: StudyDestination; reason: string };
export type ReadingPath = {
  id: string;
  title: string;
  description: string;
  qualification: string;
  steps: ReadingPathStep[];
};
export type StudyCatalog = { schemaVersion: "1.0"; studies: Study[]; readingPaths?: ReadingPath[]; researchPriorityRubric?: ResearchPriorityRubric };
export type StudyDestination = "overview" | "findings" | "explore" | "methods" | "evidence";

export type ResearchPriorityState = "assessed" | "not_assessed" | "needs_review" | "not_applicable";
export type ResearchPriorityEvidence = { text: string; source: OverviewSource };
export type ResearchPriorityIdentity = { publicationId: string; sourceRunId: string; sourceSha256: string };
export type PublicResearchPriority = {
  assessmentId: string;
  rubricVersion: string;
  rubricSha256: string;
  reviewedAt: string;
  reviewer: string;
  state: ResearchPriorityState;
  score?: 1 | 2 | 3 | 4 | 5;
  scope: string;
  rationale: string;
  materiality: string;
  supporting: ResearchPriorityEvidence[];
  contrary: ResearchPriorityEvidence[];
  blocker: string;
  nextTest: { description: string; supports: string; rejects: string };
  highPriorityEvidence?: { executionAndCosts: ResearchPriorityEvidence; separatedEvaluation: ResearchPriorityEvidence; materialEffect: ResearchPriorityEvidence; independentCorroboration?: ResearchPriorityEvidence };
  reviewedStudySha256: string;
  reviewedPublications: ResearchPriorityIdentity[];
  reassessment?: { required: true; reason: string; markedAt: string };
};
export type ResolvedResearchPriority = PublicResearchPriority & {
  effectiveState: ResearchPriorityState;
  staleReasons: string[];
  supporting: Array<ResearchPriorityEvidence & { href: string }>;
  contrary: Array<ResearchPriorityEvidence & { href: string }>;
};
export type ResearchPriorityRubric = {
  version: string;
  sourceSha256: string;
  meaning: string;
  disclaimer: string;
  bands: Array<{ score: 1 | 2 | 3 | 4 | 5; label: string; definition: string }>;
};
