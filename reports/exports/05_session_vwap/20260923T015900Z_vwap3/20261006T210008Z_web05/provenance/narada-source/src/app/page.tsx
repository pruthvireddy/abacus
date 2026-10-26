import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { formatDate } from "@/lib/format";
import { getPublicationIndex } from "@/lib/publications";

export default async function LibraryPage() {
  const index = await getPublicationIndex();
  const reports = index.reports;
  return (
    <>
      <SiteHeader />
      <main id="main" className="shell library-main">
        <section className="library-intro" aria-labelledby="library-title">
          <div><p className="eyebrow"><span /> THE RESEARCH JOURNAL</p><h1 id="library-title">Ideas, examined.<br /><em>Evidence, shared.</em></h1><p className="intro-copy">Research from Abacus, brought together in a collection of findings, figures, and considered conclusions.</p></div>
          <div className="journal-mark" aria-hidden="true"><span>N</span><i /><small>ABACUS<br />PUBLICATIONS</small></div>
        </section>
        <section className="publications" aria-labelledby="publications-title">
          <div className="collection-heading"><h2 id="publications-title">The collection</h2><span>{reports.length} {reports.length === 1 ? "publication" : "publications"}</span></div>
          {reports.length ? <div className="publication-list">{reports.map((report, index) => (
            <article className="publication-card" key={report.id}>
              <div className="publication-number" aria-hidden="true">{String(reports.length - index).padStart(2, "0")}</div>
              <div className="publication-copy"><div className="publication-meta"><span>{report.source.producer}</span><time dateTime={report.publishedAt}>{formatDate(report.publishedAt)}</time></div><h3><Link href={`/reports/${report.id}/`}>{report.title}</Link></h3><p>{report.summary}</p><Link className="read-link" href={`/reports/${report.id}/`}>Read publication <span aria-hidden="true">↗</span><span className="visually-hidden">: {report.title}</span></Link></div>
            </article>
          ))}</div> : <div className="empty-collection"><div className="empty-symbol" aria-hidden="true"><i /><i /><i /></div><p className="eyebrow">A NEW COLLECTION</p><h3>The first pages are still to come.</h3><p>There are no publications here yet.<br />When new research is ready to share, you’ll find it here.</p></div>}
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
