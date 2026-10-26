import Image from "next/image";
import type { ReportSection, SourceReference } from "../../types/report";
import { formatValue } from "@/lib/format";
import { SectionReferences } from "@/components/publication-evidence";

export function ReportSections({ sections, reportId, references }: { sections: ReportSection[]; reportId: string; references?: SourceReference[] }) {
  return sections.map((section, index) => (
    <section key={section.id} id={`section-${section.id}`} className={`report-section section-${section.kind}`} aria-labelledby={`heading-${section.id}`}>
      <div className="section-heading">
        <span className="section-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
        <h2 id={`heading-${section.id}`}>{section.title}</h2>
      </div>
      <SectionContent section={section} reportId={reportId} />
      <SectionReferences ids={section.referenceIds} references={references} />
    </section>
  ));
}

function SectionContent({ section, reportId }: { section: ReportSection; reportId: string }) {
  switch (section.kind) {
    case "text":
      return <div className="prose">{section.body.split(/\n\s*\n/).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>;
    case "metrics":
      return (
        <dl className="metrics-grid">
          {section.items.map((metric, index) => (
            <div className="metric" key={`${index}-${metric.label}`}>
              <dt>{metric.label}</dt>
              <dd className={metric.value === null ? "metric-unavailable" : undefined}>{formatValue(metric.value, metric)}</dd>
              {metric.note ? <dd className="metric-note">{metric.note}</dd> : null}
            </div>
          ))}
        </dl>
      );
    case "table":
      return (
        <div className="table-presentation">
          {section.description ? <p className="table-description" id={`table-context-${section.id}`}>{section.description}</p> : null}
          <p className="table-hint" id={`table-help-${section.id}`}>Scroll horizontally: focus this table; use left and right arrow keys. Missing or blank cells display as Not available; see notes.</p>
          <div className="table-scroll" role="region" aria-labelledby={`heading-${section.id}`} aria-describedby={[`table-help-${section.id}`, ...(section.description ? [`table-context-${section.id}`] : []), ...(section.notes?.length ? [`table-notes-${section.id}`] : [])].join(" ")} tabIndex={0}>
          <table>
            <caption className="visually-hidden">{section.title}</caption>
            <thead><tr>{section.columns.map((column) => <th key={column.key} scope="col" className={column.format ? "numeric" : undefined}>{column.label}{column.unit ? <span className="column-unit">{column.unit}</span> : null}</th>)}</tr></thead>
            <tbody>{section.rows.map((row, index) => <tr key={index}>{section.columns.map((column) => <td key={column.key} className={column.format ? "numeric" : undefined}>{formatValue(Object.hasOwn(row, column.key) ? row[column.key] : null, { format: column.format, precision: column.precision })}</td>)}</tr>)}</tbody>
          </table>
          </div>
          {section.notes?.length ? <ul className="table-notes" id={`table-notes-${section.id}`}>{section.notes.map((note, index) => <li key={index}>{note}</li>)}</ul> : null}
        </div>
      );
    case "figure":
      return (
        <figure className="report-figure">
          <a href={`/publications/${reportId}/${section.path}`} aria-label={`View full-size figure: ${section.title}`}>
          <Image
            src={`/publications/${reportId}/${section.path}`}
            alt={section.alt}
            width={1600}
            height={1000}
            sizes="(max-width: 900px) 100vw, 860px"
            unoptimized
            style={{ width: "100%", height: "auto" }}
          />
          </a>
          <figcaption>{section.caption ? <span>{section.caption}</span> : null}<a className="figure-size-link" href={`/publications/${reportId}/${section.path}`}>View full-size figure</a></figcaption>
        </figure>
      );
  }
}
