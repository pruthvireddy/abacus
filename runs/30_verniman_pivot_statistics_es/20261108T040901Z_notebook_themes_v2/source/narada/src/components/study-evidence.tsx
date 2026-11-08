import type { Study, StudyAnalysis } from "../../types/study";
import type { PublicationBundle } from "../../types/report";
import { studyAnalyses } from "../../scripts/lib/study-selections.mjs";
import { formatDate } from "@/lib/format";
import { PublicationEvidence } from "./publication-evidence";

function selectionLabel(study: Study, id: string) {
  const related = study.relatedPublications?.find(reference => reference.publicationId === id);
  if (related) return `${related.label} · ${related.relationship.replaceAll("-", " ")}`;
  const family = study.phaseFamilies?.find(family => family.analyses.some(analysis => analysis.publicationTabs.some(tab => tab.publicationId === id)));
  const analysis = (studyAnalyses(study) as StudyAnalysis[]).find(analysis => analysis.publicationTabs.some(tab => tab.publicationId === id));
  const tab = (analysis?.publicationTabs ?? study.publicationTabs)?.find(tab => tab.publicationId === id);
  return [family?.label, analysis?.label, tab?.label].filter(Boolean).join(" · ") || "Featured publication";
}
export function StudyEvidenceDirectory({ study, bundles }: { study: Study; bundles: PublicationBundle[] }) {
  return <div className="study-evidence-directory">{bundles.map(({ report, provenance }, index) => <details className="report-evidence-group" key={report.id} id={`saved-${report.id}`}>
    <summary><h3><span>{selectionLabel(study, report.id)}</span><strong>{report.title}</strong><small>{report.id === study.featuredPublicationId ? "Featured · " : ""}{report.downloads?.length ?? 0} CSVs · {report.references?.length ?? 0} references</small></h3></summary>
    <div className="report-evidence-content"><p className="publication-meta">Published {formatDate(report.publishedAt)}</p><a className="read-link" href={`/reports/${report.id}/`}>Read this saved report <span aria-hidden="true">↗</span></a>
      <dl className="report-identity"><div><dt>Publication</dt><dd><code>{report.id}</code></dd></div><div><dt>Source run</dt><dd><code>{report.source.runId}</code></dd></div><div><dt>Report content SHA-256</dt><dd><code>{provenance.sourceSha256}</code></dd></div></dl>
      <p className="evidence-report-links"><a href={`/publications/${report.id}/report.json`}>Saved report JSON</a><a href={`/reports/${report.id}/#publication-record`}>Publication record & asset hashes</a></p>
      <PublicationEvidence report={report} idPrefix={`e${index + 1}-`} compact />
      {!report.downloads?.length ? <p className="evidence-absence">This publication declares no selected CSV downloads.</p> : null}
      {!report.references?.length ? <p className="evidence-absence">This publication declares no structured source-reference entries. Its saved sections and publication record retain the available context.</p> : null}
    </div>
  </details>)}</div>;
}
