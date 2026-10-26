import type { Study, StudyAnalysis, PublicationTab } from "../../types/study";
import { studyAnalyses, studyPublicationReferences } from "../../scripts/lib/study-selections.mjs";

function ReportViews({ study, tabs }: { study: Study; tabs: PublicationTab[] }) {
  return <ul className="report-view-list">{tabs.map(tab => <li key={tab.publicationId}><a href={`/reports/${tab.publicationId}/`}>{tab.label}<span aria-hidden="true"> ↗</span></a>{tab.publicationId === study.featuredPublicationId ? <span className="selection-badge">Featured</span> : null}</li>)}</ul>;
}
function AnalysisDirectory({ study, analyses, conditions = false }: { study: Study; analyses: StudyAnalysis[]; conditions?: boolean }) {
  const Heading = conditions ? "h4" : "h3";
  return <div className="analysis-card-grid">{analyses.map(analysis => <section className="analysis-card" key={analysis.id}>
    <p className="brief-label">{conditions ? "Condition" : "Analysis"} · {analysis.publicationTabs.length} saved {analysis.publicationTabs.length === 1 ? "view" : "views"}</p><Heading>{analysis.label}</Heading>
    <p>Each view retains this group’s saved population and source run.</p><ReportViews study={study} tabs={analysis.publicationTabs} />
  </section>)}</div>;
}
export function RelatedStudyReports({ study }: { study: Study }) {
  return study.relatedPublications?.length ? <section className="study-related-directory" aria-labelledby="earlier-reports-title"><h3 id="earlier-reports-title">Related and earlier publications</h3><p>Relationship labels distinguish earlier research runs, exploratory supplements, and later presentations of the same run.</p><ul className="related-publications">{study.relatedPublications.map(reference => <li key={reference.publicationId}><a href={`/reports/${reference.publicationId}/`}>{reference.label}</a><span>{reference.relationship.replaceAll("-", " ")} · <code>{reference.sourceRunId}</code></span></li>)}</ul></section> : null;
}
export function StudyReportDirectory({ study }: { study: Study }) {
  const analyses = studyAnalyses(study);
  const references = studyPublicationReferences(study);
  return <>
    {study.phaseFamilies?.length ? <div className="phase-card-stack">{study.phaseFamilies.map(family => <section className="phase-card" key={family.id}><p className="brief-label">Phase</p><h3>{family.label}</h3><AnalysisDirectory study={study} analyses={family.analyses} conditions /></section>)}</div> : analyses.length ? <AnalysisDirectory study={study} analyses={analyses} /> : study.publicationTabs?.length ? <section className="parallel-report-directory"><h3>{study.products.length > 1 ? "Products and saved views" : "Saved report views"}</h3><p>Choose a separate saved population or view. The featured selection is marked below.</p><ReportViews study={study} tabs={study.publicationTabs} /></section> : <article className="single-report-card"><p className="brief-label">Featured saved publication</p><h3>{study.title}</h3><p>{study.summary}</p><a className="read-link" href={`/reports/${study.featuredPublicationId}/`}>Read the detailed report <span aria-hidden="true">↗</span></a></article>}
    <RelatedStudyReports study={study} />
    <details className="all-report-directory"><summary>Browse every report · {references.length} selected {references.length === 1 ? "publication" : "publications"}</summary><ul>{references.map(reference => <li key={reference.publicationId}><a href={`/reports/${reference.publicationId}/`}>{"label" in reference ? reference.label : "Featured report"}</a><code>{reference.publicationId}</code></li>)}</ul></details>
  </>;
}
