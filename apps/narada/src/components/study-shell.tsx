import type { ReactNode } from "react";
import Link from "next/link";
import type { Study, StudyDestination } from "../../types/study";
import { STUDY_DESTINATIONS, studyDestinationHref } from "../../scripts/lib/study-routes.mjs";
import { SiteFooter, SiteHeader } from "./site-header";

export function StudyDestinationNavigation({ study, current }: { study: Study; current: StudyDestination }) {
  return <nav className="study-overview-nav study-destination-nav" aria-label="Study destinations"><ul>{STUDY_DESTINATIONS.map(destination => <li key={destination.key}><a href={studyDestinationHref(study.slug, destination.key)} aria-current={destination.key === current ? "page" : undefined}>{destination.label}</a></li>)}</ul></nav>;
}

export function StudyShell({ study, current, children }: { study: Study; current: StudyDestination; children: ReactNode }) {
  const overview = study.resolvedOverview;
  return <><SiteHeader title={study.title} /><main id="main" className={`shell study-overview-main study-experience study-destination-${current}`}>
    <Link href="/" prefetch={false} className="library-back">← Research library</Link>
    <header className={`study-masthead${current === "overview" ? "" : " study-masthead-compact"}`} id="overview">
      <p className="eyebrow">{study.topic.replaceAll("_", " ")} <span /> {study.products.join(" / ")}</p>
      <h1>{study.title}</h1><p className="study-question">{overview?.question ?? study.summary}</p>
    </header>
    <StudyDestinationNavigation study={study} current={current} />
    {current !== "overview" ? <p className="destination-qualification"><strong>{overview?.evidenceType ?? "Evidence basis"}.</strong> {overview?.qualification ?? study.evidenceStatus}</p> : null}
    {children}
    <p className="print-publication-identity">Study {study.studyId}. {overview ? `Overview source: ${overview.source.publicationId} · run ${overview.source.sourceRunId} · content SHA-256 ${overview.source.sourceSha256}.` : `Selected publication: ${study.featuredPublicationId} · source run ${study.featuredSourceRunId}.`}</p>
  </main><SiteFooter /></>;
}
