import type { Study, StudyDestination } from "../../types/study";
import { getPublication } from "@/lib/publications";
import { studyPublicationReferences } from "../../scripts/lib/study-selections.mjs";
import { StudyShell } from "./study-shell";
import { StudyOverview, StudyStatistics, StudyFindings, StudyMethods, OverviewSourceRecord } from "./study-overview";
import { StudyResults } from "./study-results";
import { StudyEvidenceDirectory } from "./study-evidence";
import { LegacyStudyLinks } from "./legacy-study-links";
import { StudyReadingPaths } from "./reading-paths";
import { getStudyCatalog } from "@/lib/studies";
import { isSinglePageStudy, studyThemeHref } from "../../scripts/lib/study-routes.mjs";
import { StudyResultsPaper } from "./study-results-paper";

export async function StudyExperiencePage({ study, destination, activePublicationId }: { study: Study; destination: StudyDestination; activePublicationId?: string }) {
  const featured = await getPublication(study.featuredPublicationId);
  if (!featured) throw new Error("Validated featured publication is missing.");
  if (isSinglePageStudy(study)) {
    const bundles = await Promise.all(studyPublicationReferences(study).map(async reference => {
      if (reference.publicationId === featured.report.id) return featured;
      const bundle = await getPublication(reference.publicationId);
      if (!bundle) throw new Error("Validated selected publication is missing.");
      return bundle;
    }));
    const primaryIds = new Set(study.publicationTabs?.map(tab => tab.publicationId));
    const primary = bundles.filter(bundle => primaryIds.has(bundle.report.id));
    const earlier = bundles.filter(bundle => !primaryIds.has(bundle.report.id));
    const active = primary.find(bundle => bundle.report.id === (activePublicationId ?? featured.report.id));
    if (!active) throw new Error("Selected study theme is not a primary publication.");
    const readerThemes = primary.map(({ report }) => ({ report: {
      id: report.id, summary: report.summary, sections: report.sections,
      references: report.references, notes: report.notes,
    } }));
    return <StudyShell study={study} current="explore">
      <StudyResultsPaper study={study} publications={readerThemes} activePublicationId={active.report.id} />
      <LegacyStudyLinks featured={earlier[0] ?? active} selected={[...primary, ...earlier]} targetsOnly excludeIds={active.report.sections.flatMap(section => [`section-${section.id}`, `heading-${section.id}`])} />
      <aside className="legacy-study-links legacy-study-targets-only" aria-label="Earlier theme link compatibility">{primary.filter(bundle => bundle.report.id !== active.report.id).map(bundle => <p className="legacy-study-target" id={`theme-${bundle.report.id}`} key={bundle.report.id}>This theme is available in Results. <a href={studyThemeHref(study, bundle.report.id)}>Open {study.publicationTabs?.find(tab => tab.publicationId === bundle.report.id)?.label}</a></p>)}</aside>
    </StudyShell>;
  }
  const overview = study.resolvedOverview;
  const preserveSelectedAnchors = destination === "overview" && featured.report.presentation === "research-paper";
  const [catalog, bundles] = await Promise.all([
    destination === "overview" ? getStudyCatalog() : null,
    destination === "evidence" || preserveSelectedAnchors ? Promise.all(studyPublicationReferences(study).map(async reference => {
      if (reference.publicationId === featured.report.id) return featured;
      const bundle = await getPublication(reference.publicationId);
      if (!bundle) throw new Error("Validated selected publication is missing.");
      return bundle;
    })) : [],
  ]);
  return <StudyShell study={study} current={destination}>
    {destination === "overview" ? <><StudyOverview study={study} rubric={catalog?.researchPriorityRubric} />{catalog ? <StudyReadingPaths study={study} paths={catalog.readingPaths ?? []} studies={catalog.studies} /> : null}<LegacyStudyLinks featured={featured} selected={preserveSelectedAnchors ? bundles : undefined} /></> : null}
    {destination === "findings" ? <section className="destination-content" aria-labelledby="destination-title"><p className="eyebrow">SAVED CONCLUSIONS</p><h2 id="destination-title">Findings</h2><p className="section-intro">Read each result with its stated population, horizon, and limitations. These are abridgments of the linked saved sections.</p><StudyFindings study={study} />{overview ? <><h3 className="destination-subtitle">Selected statistics & scope</h3><StudyStatistics study={study} /></> : null}{featured.report.sections.some(section => section.kind === "figure") ? <div className="saved-figure-links"><h3>Figures in the featured report</h3><ul>{featured.report.sections.filter(section => section.kind === "figure").map(section => <li key={section.id}><a href={`/reports/${featured.report.id}/#section-${section.id}`}>{section.title}</a></li>)}</ul></div> : null}</section> : null}
    {destination === "explore" ? <StudyResults study={study} publication={featured} /> : null}
    {destination === "methods" ? <section className="destination-content" aria-labelledby="destination-title"><p className="eyebrow">DEFINITIONS, ASSUMPTIONS & BOUNDARIES</p><h2 id="destination-title">Method & scope</h2><StudyMethods study={study} /><details className="method-section-directory"><summary>Detailed sections in the featured report</summary><ul>{featured.report.sections.map(section => <li key={section.id}><a href={`/reports/${featured.report.id}/#section-${section.id}`}>{section.title}</a></li>)}</ul></details></section> : null}
    {destination === "evidence" ? <section className="destination-content" aria-labelledby="destination-title"><p className="eyebrow">SAVED PUBLICATIONS & SOURCE RECORDS</p><h2 id="destination-title">Evidence</h2><p className="section-intro">Open a selected publication’s record for its downloads, references, and source identity. Earlier runs and presentation revisions retain their catalog relationship. These records verify saved identities and bytes; they do not revalidate the research.</p><OverviewSourceRecord study={study} /><StudyEvidenceDirectory study={study} bundles={bundles} /></section> : null}
  </StudyShell>;
}
