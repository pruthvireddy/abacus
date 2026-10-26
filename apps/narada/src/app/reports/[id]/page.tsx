import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { PublicationContent } from "@/components/publication-content";
import { PublicationTabs } from "@/components/publication-tabs";
import { formatDate } from "@/lib/format";
import { getPublication, getPublicationIndex } from "@/lib/publications";
import { getPublicationStudy } from "@/lib/studies";
import { StudyAnalysisNavigation, StudyPhaseNavigation } from "@/components/study-analyses";

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
  const [publication, context] = await Promise.all([getPublication(id), getPublicationStudy(id)]);
  if (!publication) notFound();
  const { report } = publication;
  const tabs = context?.analysis?.publicationTabs ?? context?.study.publicationTabs;
  return (
    <>
      <SiteHeader title={report.title} />
      <main id="main" className="shell report-main">
        <article>
          {context ? <aside className="publication-context" aria-label="Study navigation">
            <a href={`/studies/${context.study.slug}/`}>← {context.study.title}</a>
            {context.relation ? <p>{context.relation.label} <a href={`/reports/${context.study.featuredPublicationId}/`}>Read the featured publication</a>.</p> : null}
          </aside> : null}
          {context?.study.phaseFamilies?.length ? <StudyPhaseNavigation families={context.study.phaseFamilies} currentFamilyId={context.family?.id} currentAnalysisId={context.analysis?.id} currentChartLabel={context.tab?.label} /> : null}
          {context?.family ? <StudyAnalysisNavigation analyses={context.family.analyses} currentAnalysisId={context.analysis?.id} currentChartLabel={context.tab?.label} asConditions /> : context?.study.analyses?.length ? <StudyAnalysisNavigation analyses={context.study.analyses} currentAnalysisId={context.analysis?.id} currentChartLabel={context.tab?.label} /> : null}
          {tabs?.length ? <PublicationTabs tabs={tabs} currentPublicationId={report.id} /> : null}
          <header className="report-header"><p className="eyebrow"><span /> {report.source.producer}</p><h1>{report.title}</h1><p className="report-summary">{report.summary}</p><div className="report-byline"><span>Published <time dateTime={report.publishedAt}>{formatDate(report.publishedAt)}</time></span><span>Abacus / Narada</span></div></header>
          <PublicationContent publication={publication} />
        </article>
      </main>
      <SiteFooter />
    </>
  );
}
