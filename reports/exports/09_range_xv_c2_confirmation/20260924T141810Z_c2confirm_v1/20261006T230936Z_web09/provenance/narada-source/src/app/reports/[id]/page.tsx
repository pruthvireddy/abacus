import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { ReportSections } from "@/components/report-sections";
import { formatDate } from "@/lib/format";
import { getPublication, getPublicationIndex } from "@/lib/publications";
import { getPublicationStudy } from "@/lib/studies";

export const dynamicParams = false;

export async function generateStaticParams() {
  const { reports } = await getPublicationIndex();
  // Next static export requires a nonempty path list. This reserved invalid slug
  // resolves to notFound(), never enters the index, and cannot name a publication.
  return reports.length ? reports.map(({ id }) => ({ id })) : [{ id: "__narada_empty__" }];
}

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const publication = await getPublication(id);
  return publication
    ? { title: publication.report.title, description: publication.report.summary }
    : { title: "Publication not found", robots: { index: false, follow: false } };
}

export default async function PublicationPage({ params }: Props) {
  const { id } = await params;
  const publication = await getPublication(id);
  if (!publication) notFound();
  const { report, provenance } = publication;
  const context = await getPublicationStudy(id);
  return (
    <>
      <SiteHeader title={report.title} />
      <main id="main" className="shell report-main">
        <article>
          {context ? <aside className="publication-context" aria-label="Study navigation">
            <a href={`/studies/${context.study.slug}/`}>← {context.study.title}</a>
            {context.relation ? <p>{context.relation.label} <a href={`/reports/${context.study.featuredPublicationId}/`}>Read the featured publication</a>.</p> : null}
          </aside> : null}
          <header className="report-header"><p className="eyebrow"><span /> {report.source.producer}</p><h1>{report.title}</h1><p className="report-summary">{report.summary}</p><div className="report-byline"><span>Published <time dateTime={report.publishedAt}>{formatDate(report.publishedAt)}</time></span><span>Abacus / Narada</span></div></header>
          <div className="article-layout">
            <nav className="contents" aria-label="Publication contents"><span className="eyebrow">IN THIS PUBLICATION</span><ol>{report.sections.map((section) => <li key={section.id}><a href={`#section-${section.id}`}>{section.title}</a></li>)}</ol>{report.notes?.length ? <a href="#publication-notes" className="contents-note">Notes</a> : null}</nav>
            <div className="article-body"><ReportSections sections={report.sections} reportId={report.id} />
              {report.notes?.length ? <aside id="publication-notes" className="publication-notes" aria-labelledby="notes-title"><p className="eyebrow">FURTHER CONTEXT</p><h2 id="notes-title">Notes</h2><ul>{report.notes.map((note, index) => <li key={index}>{note}</li>)}</ul></aside> : null}
              <details className="provenance"><summary>Publication record</summary><dl><div><dt>Source</dt><dd>{report.source.producer}</dd></div><div><dt>Run</dt><dd><code>{report.source.runId}</code></dd></div><div><dt>Source SHA-256</dt><dd><code>{provenance.sourceSha256}</code></dd></div></dl><a href={`/publications/${report.id}/report.json`}>View publication data <span aria-hidden="true">↗</span></a>{provenance.assets.length ? <details className="asset-record"><summary>Figure records ({provenance.assets.length})</summary><ul>{provenance.assets.map((asset) => <li key={asset.path}><a href={`/publications/${report.id}/${asset.path}`}>{asset.path}</a><code>{asset.sha256}</code></li>)}</ul></details> : null}</details>
            </div>
          </div>
        </article>
      </main>
      <SiteFooter />
    </>
  );
}
