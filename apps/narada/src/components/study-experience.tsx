import type { Study, StudyDestination } from "../../types/study";
import { getPublication } from "@/lib/publications";
import { studyPublicationReferences } from "../../scripts/lib/study-selections.mjs";
import { StudyShell } from "./study-shell";
import { StudyOverview, StudyStatistics, StudyFindings, StudyMethods, OverviewSourceRecord } from "./study-overview";
import { StudyReportDirectory } from "./study-directory";
import { StudyEvidenceDirectory } from "./study-evidence";
import { LegacyStudyLinks } from "./legacy-study-links";
import { StudyReadingPaths } from "./reading-paths";
import { getStudyCatalog } from "@/lib/studies";

export async function StudyExperiencePage({ study, destination }: { study: Study; destination: StudyDestination }) {
  const featured = await getPublication(study.featuredPublicationId);
  if (!featured) throw new Error("Validated featured publication is missing.");
  const overview = study.resolvedOverview;
  const catalog = destination === "overview" ? await getStudyCatalog() : null;
  const bundles = destination === "evidence" ? await Promise.all(studyPublicationReferences(study).map(async reference => {
    const bundle = await getPublication(reference.publicationId);
    if (!bundle) throw new Error("Validated selected publication is missing.");
    return bundle;
  })) : [];
  return <StudyShell study={study} current={destination}>
    {destination === "overview" ? <><StudyOverview study={study} />{catalog ? <StudyReadingPaths study={study} paths={catalog.readingPaths ?? []} studies={catalog.studies} /> : null}<LegacyStudyLinks featured={featured} /></> : null}
    {destination === "findings" ? <section className="destination-content" aria-labelledby="destination-title"><p className="eyebrow">SAVED CONCLUSIONS</p><h2 id="destination-title">Findings</h2><p className="section-intro">Read each result with its stated population, horizon, and limitations. These are abridgments of the linked saved sections.</p><StudyFindings study={study} />{overview ? <><h3 className="destination-subtitle">Selected statistics & scope</h3><StudyStatistics study={study} /></> : null}{featured.report.sections.some(section => section.kind === "figure") ? <div className="saved-figure-links"><h3>Figures in the featured report</h3><ul>{featured.report.sections.filter(section => section.kind === "figure").map(section => <li key={section.id}><a href={`/reports/${featured.report.id}/#section-${section.id}`}>{section.title}</a></li>)}</ul></div> : null}</section> : null}
    {destination === "explore" ? <section className="destination-content" aria-labelledby="destination-title"><p className="eyebrow">ANALYSES & REPORT VIEWS</p><h2 id="destination-title">Explore the study</h2><p className="section-intro">Choose an authored analysis, population, or saved view. The featured report is the starting selection; detailed report links keep the matching condition and view where available.</p>{overview ? <ul className="explore-links">{overview.links.map((link, index) => <li key={index}><a href={link.href}>{link.label}<span aria-hidden="true">↗</span></a></li>)}</ul> : null}<StudyReportDirectory study={study} /></section> : null}
    {destination === "methods" ? <section className="destination-content" aria-labelledby="destination-title"><p className="eyebrow">DEFINITIONS, ASSUMPTIONS & BOUNDARIES</p><h2 id="destination-title">Method & scope</h2><StudyMethods study={study} /><details className="method-section-directory"><summary>Detailed sections in the featured report</summary><ul>{featured.report.sections.map(section => <li key={section.id}><a href={`/reports/${featured.report.id}/#section-${section.id}`}>{section.title}</a></li>)}</ul></details></section> : null}
    {destination === "evidence" ? <section className="destination-content" aria-labelledby="destination-title"><p className="eyebrow">SAVED PUBLICATIONS & SOURCE RECORDS</p><h2 id="destination-title">Evidence</h2><p className="section-intro">Open a selected publication’s record for its downloads, references, and source identity. Earlier runs and presentation revisions retain their catalog relationship. These records verify saved identities and bytes; they do not revalidate the research.</p><OverviewSourceRecord study={study} /><StudyEvidenceDirectory study={study} bundles={bundles} /></section> : null}
  </StudyShell>;
}
