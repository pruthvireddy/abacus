import type { PublicationBundle } from "../../types/report";
import { ReportSections } from "./report-sections";
import { PublicationEvidence } from "./publication-evidence";
import { PatternDefinitions, PatternPanel } from "./pattern-panel";

export function PublicationContent({ publication }: { publication: PublicationBundle }) {
  const { report, provenance } = publication;
  const overview = report.patterns?.find(pattern => pattern.id === report.patternOverviewId);
  return <div className="article-layout">
    <nav className="contents" aria-label="Publication contents">
      <span className="eyebrow">IN THIS PUBLICATION</span>
      <ol>{report.sections.map(section => <li key={section.id}><a href={`#section-${section.id}`}>{section.title}</a></li>)}</ol>
      {report.downloads?.length ? <a href="#publication-downloads" className="contents-note">Evidence downloads</a> : null}
      {report.references?.length ? <a href="#publication-references" className="contents-note">Source references</a> : null}
      {report.notes?.length ? <a href="#publication-notes" className="contents-note">Notes</a> : null}
    </nav>
    <div className="article-body">
      {report.patterns?.length ? <PatternDefinitions patterns={report.patterns} reportId={report.id} /> : null}
      {overview ? <PatternPanel pattern={overview} instanceId="pattern-overview" overview symbolReportId={report.id} /> : null}
      <ReportSections sections={report.sections} reportId={report.id} references={report.references} patterns={report.patterns} patternDefinitionsProvided explainedPatternIds={overview ? [overview.id] : []} />
      <PublicationEvidence report={report} />
      {report.notes?.length ? <aside id="publication-notes" className="publication-notes" aria-labelledby="notes-title"><p className="eyebrow">FURTHER CONTEXT</p><h2 id="notes-title">Notes</h2><ul>{report.notes.map((note, index) => <li key={index}>{note}</li>)}</ul></aside> : null}
      <details className="provenance">
        <summary>Publication record</summary>
        <dl><div><dt>Source</dt><dd>{report.source.producer}</dd></div><div><dt>Run</dt><dd><code>{report.source.runId}</code></dd></div><div><dt>Source SHA-256</dt><dd><code>{provenance.sourceSha256}</code></dd></div></dl>
        <a href={`/publications/${report.id}/report.json`}>View publication data <span aria-hidden="true">↗</span></a>
        {provenance.assets.length ? <details className="asset-record"><summary>Selected asset records ({provenance.assets.length})</summary><ul>{provenance.assets.map(asset => <li key={asset.path}><a href={`/publications/${report.id}/${asset.path}`}>{asset.path}</a><code>{asset.sha256}</code></li>)}</ul></details> : null}
      </details>
    </div>
  </div>;
}
