import type { ReactNode } from "react";
import Link from "next/link";
import type { Study, StudyDestination } from "../../types/study";
import { STUDY_DESTINATIONS, studyDestinationHref } from "../../scripts/lib/study-routes.mjs";
import { SiteFooter, SiteHeader } from "./site-header";
import { StudyTabList } from "./study-tab-list";

export function StudyDestinationNavigation({ study, current }: { study: Study; current: StudyDestination }) {
  return <nav className="study-overview-nav study-destination-nav" aria-label="Study destinations"><StudyTabList links={STUDY_DESTINATIONS.map(destination => ({ href: studyDestinationHref(study.slug, destination.key), label: destination.label, current: destination.key === current }))} /></nav>;
}

export function StudyShell({ study, current, children }: { study: Study; current: StudyDestination; children: ReactNode }) {
  const overview = study.resolvedOverview;
  const studyIdentity = overview ? `Overview source: ${overview.source.publicationId} · run ${overview.source.sourceRunId} · content SHA-256 ${overview.source.sourceSha256}.` : `Featured publication: ${study.featuredPublicationId} · source run ${study.featuredSourceRunId}.`;
  return <><SiteHeader /><main id="main" className={`shell study-overview-main study-experience study-destination-${current}`}>
    <Link href="/" prefetch={false} className="library-back">← Research library</Link>
    <header className="study-masthead study-masthead-compact" id="overview">
      <p className="eyebrow">{study.topic.replaceAll("_", " ")} <span /> {study.products.join(" / ")}</p>
      <h1>{study.title}</h1>{overview && current !== "explore" ? <p className="study-question">{overview.question}</p> : null}
    </header>
    <StudyDestinationNavigation study={study} current={current} />
    {current !== "overview" && current !== "explore" ? <p className="destination-qualification"><strong>{overview?.evidenceType ?? "Evidence basis"}.</strong> {overview?.qualification ?? study.evidenceStatus}</p> : null}
    {children}
    <p className="print-publication-identity">Study {study.studyId}.{current !== "explore" ? ` ${studyIdentity}` : ""}</p>
  </main><SiteFooter /></>;
}
