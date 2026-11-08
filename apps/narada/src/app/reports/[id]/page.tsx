import type { Metadata } from "next";
import type { PublicationTab } from "../../../../types/study";
import { notFound } from "next/navigation";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { PublicationContent } from "@/components/publication-content";
import { StudyShell } from "@/components/study-shell";
import { StudyResults } from "@/components/study-results";
import { StudyExperiencePage } from "@/components/study-experience";
import { isSinglePageStudy, studyThemeHref } from "../../../../scripts/lib/study-routes.mjs";
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
  const [publication, context] = await Promise.all([getPublication(id), getPublicationStudy(id)]);
  if (context && isSinglePageStudy(context.study) && context.study.publicationTabs?.some((tab: PublicationTab) => tab.publicationId === id)) {
    return { title: `${publication?.report.title} · ${context.study.title}`, description: publication?.report.summary, alternates: { canonical: studyThemeHref(context.study, id) } };
  }
  return publication
    ? { title: publication.report.title, description: publication.report.summary }
    : { title: "Publication not found", robots: { index: false, follow: false } };
}

export default async function PublicationPage({ params }: Props) {
  const { id } = await params;
  const [publication, context] = await Promise.all([getPublication(id), getPublicationStudy(id)]);
  if (!publication) notFound();
  const { report } = publication;
  if (context && isSinglePageStudy(context.study) && context.study.publicationTabs?.some((tab: PublicationTab) => tab.publicationId === id)) {
    return <StudyExperiencePage study={context.study} destination="explore" activePublicationId={id} />;
  }
  if (context) return <StudyShell study={context.study} current="explore"><StudyResults study={context.study} publication={publication} /></StudyShell>;
  return (
    <>
      <SiteHeader title={report.title} />
      <main id="main" className={`shell report-main report-reader${report.presentation === "research-paper" ? " research-paper" : ""}`}>
        <article>
          <header className="report-header"><p className="eyebrow"><span /> {report.source.producer}</p><h1>{report.title}</h1><p className="report-summary">{report.summary}</p><div className="report-byline"><span>Published <time dateTime={report.publishedAt}>{formatDate(report.publishedAt)}</time></span><span>Abacus / Narada</span></div></header>
          <PublicationContent publication={publication} />
        </article>
      </main>
      <SiteFooter />
    </>
  );
}
