import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { getStudyCatalog } from "@/lib/studies";

export default async function LibraryPage() {
  const index = await getStudyCatalog();
  const studies = index.studies;
  return (
    <>
      <SiteHeader />
      <main id="main" className="shell library-main">
        <section className="library-intro" aria-labelledby="library-title">
          <div><p className="eyebrow"><span /> THE RESEARCH JOURNAL</p><h1 id="library-title">Ideas, examined.<br /><em>Evidence, shared.</em></h1><p className="intro-copy">Research from Abacus, brought together in a collection of findings, figures, and considered conclusions.</p></div>
          <div className="journal-mark" aria-hidden="true"><span>N</span><i /><small>ABACUS<br />PUBLICATIONS</small></div>
        </section>
        <section className="publications" aria-labelledby="publications-title">
          <div className="collection-heading"><h2 id="publications-title">The collection</h2><span>{studies.length} {studies.length === 1 ? "study" : "studies"}</span></div>
          {studies.length ? <div className="publication-list">{studies.map((study, index) => (
            <article className="publication-card" key={study.studyId}>
              <div className="publication-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</div>
              <div className="publication-copy"><div className="publication-meta"><span>{study.topic}</span><span>{study.products.join(" / ")}</span></div><h3><Link href={`/studies/${study.slug}/`}>{study.title}</Link></h3><p>{study.summary}</p><p className="study-evidence"><strong>Evidence:</strong> {study.evidenceStatus}</p><Link className="read-link" href={`/studies/${study.slug}/`}>Explore study <span aria-hidden="true">↗</span><span className="visually-hidden">: {study.title}</span></Link></div>
            </article>
          ))}</div> : <div className="empty-collection"><div className="empty-symbol" aria-hidden="true"><i /><i /><i /></div><p className="eyebrow">A NEW COLLECTION</p><h3>The first pages are still to come.</h3><p>There are no studies here yet.<br />When new research is ready to share, you’ll find it here.</p></div>}
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
