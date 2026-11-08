import Link from "next/link";
import type { SourceReport } from "../../types/report";
import type { Study } from "../../types/study";
import { studyThemeHref } from "../../scripts/lib/study-routes.mjs";
import { ReportSections } from "./report-sections";

// The catalog selects the saved themes and their order. Only the active theme's
// body is mounted. Audit and publication records remain repository evidence.
type ResearchTheme = { report: Pick<SourceReport, "id" | "summary" | "sections" | "references" | "notes"> };
export function StudyResultsPaper({ study, publications, activePublicationId = study.featuredPublicationId }: { study: Study; publications: ResearchTheme[]; activePublicationId?: string }) {
  const byId = new Map(publications.map(publication => [publication.report.id, publication]));
  const themes = (study.publicationTabs ?? []).map(tab => {
    const publication = byId.get(tab.publicationId);
    if (!publication) throw new Error(`Selected study theme is missing: ${tab.publicationId}`);
    return { ...tab, publication };
  });
  const activeThemeIndex = themes.findIndex(theme => theme.publicationId === activePublicationId);
  const activeTheme = themes[activeThemeIndex];
  if (!activeTheme) throw new Error(`Selected study theme is not in this study: ${activePublicationId}`);
  const { publication } = activeTheme;
  const notes = [...new Set(themes.flatMap(({ publication }) => publication.report.notes ?? []))];
  const priority = study.resolvedResearchPriority ?? study.researchPriority;
  const priorityState = study.resolvedResearchPriority?.effectiveState ?? priority?.state ?? "not_assessed";
  const priorityLabel = priorityState === "assessed" ? `${priority?.score} / 5` : ({ not_assessed: "Not assessed", needs_review: "Needs review", not_applicable: "Not applicable" })[priorityState];

  return <article className="study-results report-reader research-paper single-page-results" aria-label="Study results" data-study-reading-mode="single-page" data-active-publication-id={publication.report.id}>
    <div className="single-page-intro">
      <p className="report-summary">{study.summary}</p>
      <p className="single-page-qualification">{study.evidenceStatus}</p>
    </div>
    <nav className="single-page-contents" aria-label="Study themes"><p className="eyebrow">THEMES</p><ol>{themes.map(theme => <li key={theme.publicationId}><Link href={studyThemeHref(study, theme.publicationId)} prefetch={false} scroll={false} aria-current={theme.publicationId === activePublicationId ? "page" : undefined}>{theme.label}</Link></li>)}</ol></nav>
    <div className="article-body">
      <section className="single-page-theme" id={`theme-${publication.report.id}`} key={publication.report.id} aria-labelledby={`theme-title-${publication.report.id}`} data-publication-id={publication.report.id}>
        <header className="single-page-theme-heading"><p className="eyebrow">THEME {String(activeThemeIndex + 1).padStart(2, "0")}</p><h2 id={`theme-title-${publication.report.id}`}>{activeTheme.label}</h2><p>{publication.report.summary}</p></header>
        <ReportSections sections={publication.report.sections} reportId={publication.report.id} references={publication.report.references} headingLevel={3} />
      </section>
    </div>
    <div className="single-page-endnotes">
      <p className="single-page-priority" id="research-priority">Research priority: {priorityLabel}.</p>
      <details className="single-page-scope" id="study-scope">
        <summary>Scope &amp; interpretation</summary>
        <div className="single-page-scope-content">
          {study.resolvedOverview ? <><h2>Method &amp; scope</h2><p>{study.resolvedOverview.method}</p><p>{study.resolvedOverview.qualification}</p></> : null}
          {notes.length ? <ul className="scope-notes">{notes.map(note => <li key={note}>{note}</li>)}</ul> : null}
        </div>
      </details>
    </div>
  </article>;
}
