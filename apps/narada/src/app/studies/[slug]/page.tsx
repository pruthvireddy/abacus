import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { getStudy, getStudyCatalog } from "@/lib/studies";
import { getPublication } from "@/lib/publications";
import { formatDate } from "@/lib/format";
import { PublicationTabs } from "@/components/publication-tabs";
import { PublicationContent } from "@/components/publication-content";
import { StudyAnalysisDirectory, StudyAnalysisNavigation, StudyPhaseDirectory, StudyPhaseNavigation } from "@/components/study-analyses";

export const dynamicParams = false;
export async function generateStaticParams() {
  const { studies } = await getStudyCatalog();
  return studies.length ? studies.map(({ slug }) => ({ slug })) : [{ slug: "__narada_empty__" }];
}
type Props = { params: Promise<{ slug: string }> };
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const study = await getStudy((await params).slug);
  return study ? { title: study.title, description: study.summary } : { title: "Study not found", robots: { index: false, follow: false } };
}
export default async function StudyPage({ params }: Props) {
  const study = await getStudy((await params).slug);
  if (!study) notFound();
  const featured = await getPublication(study.featuredPublicationId);
  if (!featured) throw new Error("Validated featured publication is missing.");
  const phaseFamilies = study.phaseFamilies ?? [];
  const featuredFamily = phaseFamilies[0];
  const featuredAnalysis = featuredFamily?.analyses[0] ?? study.analyses?.[0];
  const tabs = featuredAnalysis?.publicationTabs ?? study.publicationTabs;
  return <>
    <SiteHeader title={study.title} />
    <main id="main" className={`shell report-main${tabs?.length ? "" : " study-main"}`}>
      <Link href="/" className="read-link">← Back to the library</Link>
      <header className="report-header">
        <p className="eyebrow">{study.topic} · {study.products.join(" / ")}</p>
        <h1>{study.title}</h1><p className="report-summary">{study.summary}</p>
      </header>
      <aside className="evidence-status" aria-labelledby="evidence-title"><h2 id="evidence-title">Evidence status</h2><p>{study.evidenceStatus}</p></aside>
      {featuredFamily ? <>
        <StudyPhaseNavigation families={phaseFamilies} currentFamilyId={featuredFamily.id} currentAnalysisId={featuredAnalysis?.id} currentChartLabel={tabs?.[0].label} />
        <StudyAnalysisNavigation analyses={featuredFamily.analyses} currentAnalysisId={featuredAnalysis?.id} currentChartLabel={tabs?.[0].label} asConditions />
        <StudyPhaseDirectory families={phaseFamilies} />
      </> : study.analyses?.length ? <>
        <StudyAnalysisNavigation analyses={study.analyses} currentAnalysisId={featuredAnalysis?.id} currentChartLabel={tabs?.[0].label} />
        <StudyAnalysisDirectory analyses={study.analyses} />
      </> : null}
      {tabs?.length ? <>
        <PublicationTabs tabs={tabs} currentPublicationId={featured.report.id} />
        <section aria-labelledby="featured-title" className="study-selected-publication">
          <h2 id="featured-title">{featured.report.title}</h2>
          <p className="publication-meta">Published {formatDate(featured.report.publishedAt)}</p>
          <p className="report-summary">{featured.report.summary}</p>
          <PublicationContent publication={featured} />
        </section>
      </> : <section className="study-publications" aria-labelledby="featured-title">
        <h2 id="featured-title">Featured publication</h2>
        <article className="publication-card"><div className="publication-copy">
          <p className="publication-meta">Published {formatDate(featured.report.publishedAt)}</p>
          <h3><Link href={`/reports/${featured.report.id}/`}>{featured.report.title}</Link></h3>
          <p>{featured.report.summary}</p><Link className="read-link" href={`/reports/${featured.report.id}/`}>Read publication <span aria-hidden="true">↗</span></Link>
        </div></article>
      </section>}
      {study.relatedPublications?.length ? <section className="study-publications" aria-labelledby="related-title">
        <h2 id="related-title">Related publications</h2><ul className="related-publications">{study.relatedPublications.map(publication => <li key={publication.publicationId}><Link href={`/reports/${publication.publicationId}/`}>{publication.label}</Link><span>{publication.relationship.replaceAll("-", " ")}</span></li>)}</ul>
      </section> : null}
    </main><SiteFooter />
  </>;
}
