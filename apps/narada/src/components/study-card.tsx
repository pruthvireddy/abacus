import type { Study } from "../../types/study";
import { formatValue } from "@/lib/format";
import { ResearchPriority } from "./research-priority";

// An overview enriches the same catalog entry; unmigrated studies retain their
// authored summary and evidence wording without invented scores or statistics.
export function StudyCard({ study, number }: { study: Study; number: number }) {
  const overview = study.resolvedOverview;
  return <article className="study-card">
    <div className="study-card-meta"><span>{study.topic.replaceAll("_", " ")}</span><span>{study.products.join(" / ")}</span></div>
    <h3>{study.title}</h3>
    {overview ? <p className="card-question">{overview.question}</p> : null}
    <p className="card-takeaway">{overview?.takeaway ?? study.summary}</p>
    {overview ? <dl className="card-facts">{overview.statistics.slice(0, 2).map((statistic, index) => <div key={index}>
      <dt>{statistic.label}</dt><dd>{statistic.text ?? formatValue(statistic.value, statistic)}</dd>
      <dd className="card-fact-context">{statistic.context}</dd>
    </div>)}</dl> : null}
    {overview ? <details className="card-statistic-sources"><summary>Statistic context & sources</summary><ul>{overview.statistics.slice(0, 2).map((statistic, index) => <li key={index}><strong>{statistic.label}</strong>{statistic.note ? <p>{statistic.note}</p> : null}{statistic.description ? <p>{statistic.description}</p> : null}{statistic.notes?.map((note, noteIndex) => <p key={noteIndex}>{note}</p>)}<a href={statistic.href}>Saved source ↗</a></li>)}</ul></details> : null}
    <div className="card-evidence"><ResearchPriority study={study} /><p className="brief-label">{overview?.evidenceType ?? "Evidence basis"}</p><p>{overview?.qualification ?? study.evidenceStatus}</p></div>
    <a className="card-primary" href={`/studies/${study.slug}/`}>Study overview <span className="visually-hidden">: {study.title}</span><span aria-hidden="true">↗</span></a>
    <span className="card-number" aria-hidden="true">{String(number).padStart(2, "0")}</span>
  </article>;
}
