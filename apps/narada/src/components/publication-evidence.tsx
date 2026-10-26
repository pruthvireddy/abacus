import type { SourceReference, SourceReport } from "../../types/report";

export function SectionReferences({ ids, references = [] }: { ids?: string[]; references?: SourceReference[] }) {
  return ids?.length ? <p className="section-references">Sources: {ids.map((id, index) => <span key={id}>{index ? " · " : ""}<a href={`#reference-${id}`}>{references.find(reference => reference.id === id)?.label ?? id.replaceAll("-", " ")}</a></span>)}</p> : null;
}

function mediaTime(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function PublicationEvidence({ report, idPrefix = "", compact = false }: { report: SourceReport; idPrefix?: string; compact?: boolean }) {
  const Heading = compact ? "h4" : "h2";
  const ItemHeading = compact ? "h5" : "h3";
  return <>
    {report.downloads?.length ? <section id={`${idPrefix}publication-downloads`} className="evidence-block" aria-labelledby={`${idPrefix}downloads-title`}>
      <Heading id={`${idPrefix}downloads-title`}>Selected evidence downloads</Heading>
      {!compact ? <p>These CSVs contain selected saved summary evidence. Blank cells retain their saved meaning and are distinct from zero. The scope and units below apply to each file.</p> : null}
      <ul className="evidence-list">{report.downloads.map(download => <li key={download.id} id={`${idPrefix}download-${download.id}`}>
        <ItemHeading><a href={`/publications/${report.id}/${download.path}`} download={download.path.split("/").at(-1)}>{download.label} <span className="file-kind">CSV</span></a></ItemHeading>
        <p>{download.description}</p>
        <dl><div><dt>Population</dt><dd>{download.population}</dd></div><div><dt>Units</dt><dd>{download.units}</dd></div><div><dt>Scope</dt><dd>{download.scope}</dd></div><div><dt>File</dt><dd><code>{download.path.split("/").at(-1)}</code> · {download.rowCount} saved rows</dd></div></dl>
        <p className="reference-context">Source run <code>{download.source.runId}</code> · saved summary <code>{download.source.artifact}</code>.</p>{compact ? <a className="evidence-record-link" href={`/reports/${report.id}/#download-${download.id}`}>Source and content hashes ↗</a> : <details className="evidence-record"><summary>Source and content hashes</summary><dl><div><dt>Saved source SHA-256</dt><dd><code>{download.source.sha256}</code></dd></div><div><dt>CSV SHA-256</dt><dd><code>{download.sha256}</code></dd></div></dl></details>}
      </li>)}</ul>
    </section> : null}
    {report.references?.length ? <section id={`${idPrefix}publication-references`} className="evidence-block" aria-labelledby={`${idPrefix}references-title`}>
      <Heading id={`${idPrefix}references-title`}>Source references</Heading>
      <ol className="evidence-list">{report.references.map(reference => <li key={reference.id} id={`${idPrefix}reference-${reference.id}`}>
        <ItemHeading>{reference.kind === "external" ? <a href={reference.url} target="_blank" rel="noopener noreferrer">{reference.label} ↗</a> : reference.label}</ItemHeading>
        <p>{reference.kind === "external" ? `External source · ${reference.creator} · ` : "Saved artifact · "}{reference.title}</p>
        {reference.kind === "external" ? <p className="reference-context">{reference.startSeconds !== undefined ? `Media ${mediaTime(reference.startSeconds)}${reference.endSeconds !== undefined ? `–${mediaTime(reference.endSeconds)}` : ""}. ` : ""}{reference.publishedOn ? `Published ${reference.publishedOn}. ` : ""}{reference.accessedOn ? `Reviewed ${reference.accessedOn}.` : ""}</p> : <><p className="reference-context">Source run <code>{reference.runId}</code> · <code>{reference.artifact}</code>.</p>{compact ? <a className="evidence-record-link" href={`/reports/${report.id}/#reference-${reference.id}`}>Saved artifact hash ↗</a> : <details className="evidence-record"><summary>Saved artifact hash</summary><code>{reference.sha256}</code></details>}</>}
      </li>)}</ol>
    </section> : null}
  </>;
}
