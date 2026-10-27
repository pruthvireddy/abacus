import type { ResearchPriorityRubric, Study } from "../../types/study";
import { formatValue } from "@/lib/format";
import { studyDestinationHref } from "../../scripts/lib/study-routes.mjs";
import { ResearchPriorityAssessment } from "./research-priority";

export function StudyStatistics({ study }: { study: Study }) {
  const overview = study.resolvedOverview;
  return overview ? <dl className="overview-statistics" aria-label="Selected saved statistics and scope">{overview.statistics.map((statistic, index) => <div className={`overview-statistic${statistic.text !== undefined ? " scope-statistic" : ""}`} key={index}>
    <dt>{statistic.label}</dt><dd className={statistic.value === null ? "statistic-unavailable" : ""}>{statistic.text ?? formatValue(statistic.value, statistic)}</dd>
    <dd className="statistic-context">{statistic.context}{statistic.note ? <span>{statistic.note}</span> : null}<a href={statistic.href}>Saved source <span aria-hidden="true">↗</span></a></dd>
    {statistic.description || statistic.notes?.length ? <dd className="statistic-saved-context"><details><summary>Saved table qualifications</summary>{statistic.description ? <p>{statistic.description}</p> : null}{statistic.notes?.length ? <ul>{statistic.notes.map((note, noteIndex) => <li key={noteIndex}>{note}</li>)}</ul> : null}</details></dd> : null}
  </div>)}</dl> : null;
}
export function StudyCoverage({ study }: { study: Study }) {
  const overview = study.resolvedOverview;
  return <aside className="overview-coverage" aria-label="Coverage and evidence qualification"><div><p className="brief-label">{overview?.evidenceType ?? "Evidence basis"}</p>{overview ? <><p>{overview.population}</p>{overview.period ? <p>{overview.period}</p> : <p>The overview does not specify a common date range; use the saved report’s coverage.</p>}{overview.sampleScope ? <p>{overview.sampleScope}</p> : null}</> : <p>{study.products.join(" / ")} · {study.topic.replaceAll("_", " ")}</p>}</div><div><p className="brief-label">HOW TO READ THIS EVIDENCE</p><p>{overview?.qualification ?? study.evidenceStatus}</p></div></aside>;
}
export function StudyFindings({ study, brief = false }: { study: Study; brief?: boolean }) {
  const findings = study.resolvedOverview?.findings;
  return findings ? <ul className="finding-list">{(brief ? findings.slice(0, 2) : findings).map((finding, index) => <li key={index}><p>{finding.text}</p><a href={finding.href}>Supporting evidence <span aria-hidden="true">↗</span></a></li>)}</ul> : <div className="fallback-study-brief"><p>{study.summary}</p><a href={`/reports/${study.featuredPublicationId}/`}>Read the selected saved account ↗</a><p className="section-intro">{study.evidenceStatus}</p></div>;
}
export function StudyLimitations({ study, brief = false }: { study: Study; brief?: boolean }) {
  const limitations = study.resolvedOverview?.limitations;
  return <div className="overview-limitations"><h3>Important limitations</h3>{limitations ? <ul>{(brief ? limitations.slice(0, 2) : limitations).map((limitation, index) => <li key={index}>{limitation.text} <a href={limitation.href}>Source<span className="visually-hidden"> for limitation {index + 1}</span> ↗</a></li>)}</ul> : <p>{study.evidenceStatus}</p>}</div>;
}
export function StudyMethods({ study }: { study: Study }) {
  const overview = study.resolvedOverview;
  return <><p className="method-copy">{overview?.method ?? "The selected publication retains the review’s definitions and source context. Follow its saved sections for methodological detail and boundaries."}</p><a className="source-link" href={overview?.methodHref ?? `/reports/${study.featuredPublicationId}/`}>Read the saved method & scope <span aria-hidden="true">↗</span></a><StudyCoverage study={study} /><StudyLimitations study={study} /></>;
}
export function OverviewSourceRecord({ study }: { study: Study }) {
  const overview = study.resolvedOverview;
  if (!overview) return null;
  const sources = [overview.source, ...(overview.methodSource ? [overview.methodSource] : []), ...overview.statistics.map(statistic => statistic.source), ...overview.findings.map(finding => finding.source), ...overview.limitations.map(limitation => limitation.source), ...overview.links.map(link => link.source)];
  const uniqueSources = [...new Map(sources.map(source => [`${source.publicationId}:${source.sectionId}`, source])).values()];
  return <details className="overview-source-record"><summary>Overview sources & content identities</summary><ul>{uniqueSources.map(source => <li key={`${source.publicationId}:${source.sectionId}`}><a href={`/reports/${source.publicationId}/#section-${source.sectionId}`}>{source.publicationId} · {source.sectionId}</a><dl><div><dt>Source run</dt><dd>{source.sourceRunId}</dd></div><div><dt>Content SHA-256</dt><dd><code>{source.sourceSha256}</code></dd></div></dl><a href={`/publications/${source.publicationId}/report.json`}>Saved report JSON</a></li>)}</ul></details>;
}
export function StudyOverview({ study, rubric }: { study: Study; rubric?: ResearchPriorityRubric }) {
  const overview = study.resolvedOverview;
  return <>
    <section className="study-takeaway" aria-label="Main takeaway"><p className="brief-label">MAIN TAKEAWAY</p><p>{overview?.takeaway ?? study.summary}</p><a href={overview?.href ?? `/reports/${study.featuredPublicationId}/`}>Read the supporting report <span aria-hidden="true">↗</span></a></section>
    <StudyStatistics study={study} /><StudyCoverage study={study} />
    <ResearchPriorityAssessment study={study} rubric={rubric} />
    <div className="overview-body">
      <section className="overview-section" id="findings" aria-labelledby="findings-title"><div className="overview-section-heading"><span aria-hidden="true">01</span><h2 id="findings-title">What the study found</h2></div><StudyFindings study={study} brief /><a className="read-link destination-next" href={studyDestinationHref(study.slug, "findings")}>Read the findings <span aria-hidden="true">→</span></a></section>
      <section className="overview-section" id="explore" aria-labelledby="explore-title"><div className="overview-section-heading"><span aria-hidden="true">02</span><h2 id="explore-title">Where to go next</h2></div>{overview ? <ul className="explore-links">{overview.links.slice(0, 3).map((link, index) => <li key={index}><a href={link.href}>{link.label}<span aria-hidden="true">↗</span></a></li>)}</ul> : null}<a className="read-link" href={studyDestinationHref(study.slug, "explore")}>Explore the selected analyses and reports <span aria-hidden="true">→</span></a></section>
      <section className="overview-section" id="method" aria-label="Scope and limitations"><StudyLimitations study={study} brief /><a className="read-link destination-next" href={studyDestinationHref(study.slug, "methods")}>Method & scope <span aria-hidden="true">→</span></a></section>
      <section className="overview-section" id="evidence" aria-label="Saved evidence"><p className="section-intro">Every selected value and claim leads back to a saved publication. Evidence records retain report identities, source runs, and selected asset hashes.</p><a className="read-link" href={studyDestinationHref(study.slug, "evidence")}>Trace the evidence and downloads <span aria-hidden="true">→</span></a></section>
    </div>
  </>;
}
