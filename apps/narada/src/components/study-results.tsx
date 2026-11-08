import Link from "next/link";
import type { PublicationBundle } from "../../types/report";
import type { Study } from "../../types/study";
import { formatDate } from "@/lib/format";
import { PublicationContent } from "./publication-content";
import { PublicationTabs } from "./publication-tabs";
import { StudyAnalysisNavigation, StudyPhaseNavigation } from "./study-analyses";
import { isSinglePageStudy } from "../../scripts/lib/study-routes.mjs";

// Render one selected saved publication at a time. Navigation changes the saved
// selection; table enhancements retain their existing bounded loading behavior.
export function StudyResults({ study, publication }: { study: Study; publication: PublicationBundle }) {
  const { report } = publication;
  const researchPaper = report.presentation === "research-paper";
  const singlePage = isSinglePageStudy(study);
  const relation = study.relatedPublications?.find(reference => reference.publicationId === report.id);
  const selectedFamily = relation ? undefined : study.phaseFamilies?.find(family => family.analyses.some(analysis => analysis.publicationTabs.some(tab => tab.publicationId === report.id)));
  const analyses = relation ? undefined : selectedFamily?.analyses ?? study.phaseFamilies?.[0]?.analyses ?? study.analyses;
  const selectedAnalysis = analyses?.find(analysis => analysis.publicationTabs.some(tab => tab.publicationId === report.id));
  const tabs = relation ? undefined : selectedAnalysis?.publicationTabs ?? analyses?.[0]?.publicationTabs ?? study.publicationTabs;
  const selectedTab = tabs?.find(tab => tab.publicationId === report.id);

  return <article className={`study-results report-reader${researchPaper ? " research-paper" : ""}`} aria-labelledby="selected-result-title" data-publication-id={report.id}>
    {!singlePage ? <div className="study-result-navigation">
      {!relation && study.phaseFamilies?.length ? <StudyPhaseNavigation families={study.phaseFamilies} currentFamilyId={selectedFamily?.id} currentAnalysisId={selectedAnalysis?.id} currentChartLabel={selectedTab?.label} /> : null}
      {analyses?.length ? <StudyAnalysisNavigation analyses={analyses} currentAnalysisId={selectedAnalysis?.id} currentChartLabel={selectedTab?.label} asConditions={!!study.phaseFamilies?.length} /> : null}
      {tabs?.length ? <PublicationTabs tabs={tabs} currentPublicationId={report.id} variant={researchPaper ? "themes" : "views"} /> : null}
      {relation ? <nav className="publication-tabs study-related-tabs" aria-label="Related study results"><p className="eyebrow">EARLIER RESULT</p><ul><li><Link href={`/reports/${study.featuredPublicationId}/`} prefetch={false} scroll={false}>Featured result</Link></li><li><Link href={`/reports/${report.id}/`} prefetch={false} scroll={false} aria-current="page">{relation.label}</Link></li></ul></nav> : null}
    </div> : null}
    <header className="report-header study-result-header">
      <p className="eyebrow">{researchPaper ? "RESEARCH NOTE" : `SAVED RESULT · ${report.source.producer}`}</p>
      <h2 id="selected-result-title">{report.title}</h2>
      <p className="report-summary">{report.summary}</p>
      {relation ? <p className="report-selection-context">{relation.label} · {relation.relationship.replaceAll("-", " ")}</p> : null}
      <div className="report-byline"><span>Published <time dateTime={report.publishedAt}>{formatDate(report.publishedAt)}</time></span>{researchPaper ? <a href="#publication-record">Source &amp; execution record</a> : <span>Source run <code>{report.source.runId}</code></span>}</div>
    </header>
    <PublicationContent publication={publication} headingLevel={researchPaper ? 3 : 2} />
  </article>;
}
