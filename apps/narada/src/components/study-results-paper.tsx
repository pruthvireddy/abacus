import Link from "next/link";
import type { PublicationBundle } from "../../types/report";
import type { Study } from "../../types/study";
import { formatDate } from "@/lib/format";
import { studyThemeHref } from "../../scripts/lib/study-routes.mjs";
import { PublicationEvidence } from "./publication-evidence";
import { ReportSections } from "./report-sections";

function SavedSourceRecord({ publication, archived = false }: { publication: PublicationBundle; archived?: boolean }) {
  const { report, provenance } = publication;
  return <details className="single-page-source" id={`saved-${report.id}`}>
    <summary>{report.title}</summary>
    {archived ? <p className="source-summary">{report.summary}</p> : null}
    <dl className="report-identity">
      <div><dt>Publication</dt><dd>{report.id}</dd></div>
      <div><dt>Source</dt><dd>{report.source.producer}</dd></div>
      <div><dt>Source run</dt><dd>{report.source.runId}</dd></div>
      <div><dt>Published</dt><dd><time dateTime={report.publishedAt}>{formatDate(report.publishedAt)}</time></dd></div>
      <div><dt>Content SHA-256</dt><dd><code>{provenance.sourceSha256}</code></dd></div>
    </dl>
    <a href={`/publications/${report.id}/report.json`}>Saved publication data</a>
    <PublicationEvidence report={report} idPrefix={archived ? `archive-${report.id}-` : ""} compact linkToRecord={false} />
    {archived && report.notes?.length ? <ul className="source-notes">{report.notes.map((note, index) => <li key={index}>{note}</li>)}</ul> : null}
    {provenance.assets.length ? <details className="asset-record"><summary>Selected asset identities ({provenance.assets.length})</summary><ul>{provenance.assets.map(asset => <li key={asset.path}><span>{asset.path}</span><code>{asset.sha256}</code></li>)}</ul></details> : null}
  </details>;
}

// The catalog selects the saved themes and their order. Only the active theme's
// body is mounted; the source disclosure retains every selected publication.
export function StudyResultsPaper({ study, publications, earlierPublications = [], activePublicationId = study.featuredPublicationId }: { study: Study; publications: PublicationBundle[]; earlierPublications?: PublicationBundle[]; activePublicationId?: string }) {
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
        <p className="print-publication-identity">Publication {publication.report.id} · {publication.report.source.producer} · source run {publication.report.source.runId}. Content SHA-256: {publication.provenance.sourceSha256}.</p>
      </section>
    </div>
    <div className="single-page-records">
      <p className="single-page-priority" id="research-priority">Research priority: {priorityLabel}.</p>
      <details className="single-page-sources" id="publication-record">
        <summary>Scope, methods &amp; source records</summary>
        <div className="single-page-sources-content">
          {study.resolvedOverview ? <><h2>Method &amp; scope</h2><p>{study.resolvedOverview.method}</p><p>{study.resolvedOverview.qualification}</p></> : null}
          {notes.length ? <><h2>Scope &amp; interpretation</h2><ul className="source-notes">{notes.map(note => <li key={note}>{note}</li>)}</ul></> : null}
          <h2>Notebook publication records</h2>
          {themes.map(({ publication }) => <SavedSourceRecord publication={publication} key={publication.report.id} />)}
          {earlierPublications.length ? <details className="single-page-archive"><summary>Earlier &amp; companion evidence ({earlierPublications.length})</summary><p>Retained publications preserve their separate populations, methods and original source runs.</p>{earlierPublications.map(publication => <SavedSourceRecord publication={publication} archived key={publication.report.id} />)}</details> : null}
        </div>
      </details>
    </div>
  </article>;
}
