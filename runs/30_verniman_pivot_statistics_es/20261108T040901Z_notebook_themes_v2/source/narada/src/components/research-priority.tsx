import type { ResearchPriorityRubric as PriorityRubric, Study } from "../../types/study";
import Link from "next/link";
import { PRIORITY_BAND_LABELS, priorityAccessibleLabel, priorityPresentation } from "@/lib/research-priority-display.mjs";

const reviewDate = (value: string) => new Intl.DateTimeFormat("en-US", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" }).format(new Date(value + "T00:00:00Z"));
const highPriorityChecks = [
  ["executionAndCosts", "Execution and costs"],
  ["separatedEvaluation", "Separated evaluation"],
  ["materialEffect", "Material effect"],
  ["independentCorroboration", "Independent corroboration"],
] as const;

export function ResearchPriority({ study, explanationHref }: { study: Study; explanationHref?: string }) {
  const priority = priorityPresentation(study);
  return <div className="research-priority" data-priority-state={priority.state}>
    <p className="priority-value-row">
      <span className="visually-hidden">{priorityAccessibleLabel(study)}</span>
      <span className="priority-caption" aria-hidden="true">Research priority</span>
      {priority.score !== null ? <><span className="priority-stars" aria-hidden="true"><span>{"★".repeat(priority.score)}</span><span className="priority-stars-empty">{"☆".repeat(5 - priority.score)}</span></span><strong className="priority-number" aria-hidden="true">{priority.score}/5</strong><span className="priority-band" aria-hidden="true">{priority.label}</span></> : <strong className="priority-state" aria-hidden="true">{priority.label}</strong>}
    </p>
    <a className="priority-explanation-link" href={explanationHref ?? "/studies/" + study.slug + "/#research-priority"}>Read assessment<span className="visually-hidden"> for {study.title}</span> <span aria-hidden="true">↗</span></a>
  </div>;
}

export function ResearchPriorityAssessment({ study, rubric }: { study: Study; rubric?: PriorityRubric }) {
  const priority = priorityPresentation(study);
  const assessment = priority.assessment;
  const staleReasons = study.resolvedResearchPriority?.staleReasons ?? (assessment?.reassessment?.required ? [assessment.reassessment.reason] : []);
  const strongerEvidence = highPriorityChecks.flatMap(([key, label]) => assessment?.highPriorityEvidence?.[key] ? [{ label, evidence: assessment.highPriorityEvidence[key]! }] : []);
  const sources = assessment ? [...new Map([...assessment.supporting, ...assessment.contrary, ...strongerEvidence.map(item => item.evidence)].map(item => [item.source.publicationId + ":" + item.source.sectionId, item.source])).values()] : [];
  const evidence = (kind: "supporting" | "contrary") => assessment?.[kind].length ? <ul className="priority-evidence-list">{assessment[kind].map((item, index) => <li key={index}><p>{item.text}</p><a href={"href" in item && typeof item.href === "string" ? item.href : "/reports/" + item.source.publicationId + "/#section-" + item.source.sectionId} aria-label={"Saved evidence for " + kind + " finding " + (index + 1)}>Saved evidence <span aria-hidden="true">↗</span></a></li>)}</ul> : <p className="priority-uncited">No {kind} result is cited in this assessment.</p>;
  return <section className="research-priority-assessment" id="research-priority" aria-labelledby="research-priority-title">
    <div className="priority-section-heading"><p className="eyebrow">DATED EDITORIAL ASSESSMENT</p><h2 id="research-priority-title">Research priority</h2></div>
    <ResearchPriority study={study} explanationHref="#research-priority-explanation" />
    <div id="research-priority-explanation" className="priority-explanation">
      {priority.state === "needs_review" ? <div className="priority-review-needed"><p><strong>Reassessment needed.</strong> This assessment is excluded from numeric priority filters and ordering.</p>{staleReasons.length ? <ul>{staleReasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul> : null}{assessment?.state === "assessed" && assessment.score !== undefined ? <p className="priority-previous">Previous assessment: <strong>{assessment.score}/5 — {PRIORITY_BAND_LABELS[assessment.score]}</strong>, reviewed <time dateTime={assessment.reviewedAt}>{reviewDate(assessment.reviewedAt)}</time>. The dated reasoning below is retained as context.</p> : null}</div> : null}
      {assessment ? <>
        <h3>{priority.state === "needs_review" ? "Previous assessment rationale" : "Why this assessment"}</h3><p>{assessment.rationale}</p>
        <dl className="priority-context"><div><dt>Specific candidate or question</dt><dd>{assessment.scope}</dd></div><div><dt>What material would mean here</dt><dd>{assessment.materiality}</dd></div><div><dt>Main unresolved blocker</dt><dd>{assessment.blocker}</dd></div></dl>
        <div className="priority-evidence"><div><h3>Supporting evidence</h3>{evidence("supporting")}</div><div><h3>Contrary evidence & limits</h3>{evidence("contrary")}</div></div>
        {strongerEvidence.length ? <div className="priority-stronger-evidence"><h3>Recorded evidence for this priority</h3><dl className="priority-context">{strongerEvidence.map(({ label, evidence }) => <div key={label}><dt>{label}</dt><dd><p>{evidence.text}</p><a href={"/reports/" + evidence.source.publicationId + "/#section-" + evidence.source.sectionId}>Saved evidence <span aria-hidden="true">↗</span></a></dd></div>)}</dl></div> : null}
        <div className="priority-next-test"><h3>Next proposed test</h3><p>{assessment.nextTest.description}</p><dl><div><dt>Would support the idea</dt><dd>{assessment.nextTest.supports}</dd></div><div><dt>Would reject or pause it</dt><dd>{assessment.nextTest.rejects}</dd></div></dl><p className="priority-test-note">Proposed investigation; it has not been executed as part of this assessment.</p></div>
        <p className="priority-review-meta">Reviewed <time dateTime={assessment.reviewedAt}>{reviewDate(assessment.reviewedAt)}</time> · Rubric {assessment.rubricVersion} · {assessment.reviewer}</p>
        {sources.length ? <details className="priority-source-record"><summary>Assessment sources & content identities</summary><ul>{sources.map(source => <li key={source.publicationId + ":" + source.sectionId}><a href={"/reports/" + source.publicationId + "/#section-" + source.sectionId}>{source.publicationId} · {source.sectionId}</a><dl><div><dt>Source run</dt><dd>{source.sourceRunId}</dd></div><div><dt>Content SHA-256</dt><dd><code>{source.sourceSha256}</code></dd></div></dl></li>)}</ul></details> : null}
      </> : <p>No assessment has been published for this study. Its existing evidence qualifications remain available above.</p>}
      <p className="priority-disclaimer">{rubric?.disclaimer ?? "Research priority is a dated editorial research judgment. It is not a probability of profitability, a rating of paper quality, or a trading recommendation."}{rubric ? <> <Link href="/#research-priority-rubric" prefetch={false}>Read the rubric <span aria-hidden="true">↗</span></Link></> : null}</p>
    </div>
  </section>;
}

export function ResearchPriorityRubric({ rubric }: { rubric?: PriorityRubric }) {
  if (!rubric) return null;
  return <section className="research-priority-rubric" id="research-priority-rubric" aria-labelledby="priority-rubric-title">
    <p className="eyebrow">HOW TO READ THE STARS</p><h2 id="priority-rubric-title">Research priority</h2>
    <p className="priority-rubric-meaning">{rubric.meaning}</p><p>{rubric.disclaimer}</p>
    <details><summary>The five bands and assessment states · rubric {rubric.version}</summary><ol>{rubric.bands.map(band => <li key={band.score}><strong>{band.score}/5 — {band.label}</strong><p>{band.definition}</p></li>)}</ol><p><strong>Not assessed</strong> means there is no completed assessment. <strong>Needs review</strong> means a dated assessment requires reassessment and its previous score is excluded from numeric filters and ordering. <strong>Not applicable</strong> means the study is outside this edge-research rubric. These states are not zero stars.</p><p>Higher priority expresses the saved evidence for a specific next investigation. It does not rank profitability or remove the study’s evidence qualifications.</p></details>
  </section>;
}
