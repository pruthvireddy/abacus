import Image from "next/image";
import type { ReportSection } from "../../types/report";
import { formatValue } from "@/lib/format";

export function ReportSections({ sections, reportId }: { sections: ReportSection[]; reportId: string }) {
  return sections.map((section, index) => (
    <section key={section.id} id={`section-${section.id}`} className={`report-section section-${section.kind}`} aria-labelledby={`heading-${section.id}`}>
      <div className="section-heading">
        <span className="section-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
        <h2 id={`heading-${section.id}`}>{section.title}</h2>
      </div>
      <SectionContent section={section} reportId={reportId} />
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
          <p className="table-hint" id={`table-help-${section.id}`}>Scroll horizontally if needed. With a keyboard, focus the table and use the left and right arrow keys.</p>
          <div className="table-scroll" role="region" aria-labelledby={`heading-${section.id}`} aria-describedby={`table-help-${section.id}`} tabIndex={0}>
          <table>
            <caption className="visually-hidden">{section.title}</caption>
            <thead><tr>{section.columns.map((column) => <th key={column.key} scope="col" className={column.format ? "numeric" : undefined}>{column.label}{column.unit ? <span className="column-unit">{column.unit}</span> : null}</th>)}</tr></thead>
            <tbody>{section.rows.map((row, index) => <tr key={index}>{section.columns.map((column) => <td key={column.key} className={column.format ? "numeric" : undefined}>{formatValue(Object.hasOwn(row, column.key) ? row[column.key] : null, { format: column.format, precision: column.precision })}</td>)}</tr>)}</tbody>
          </table>
          </div>
        </div>
      );
    case "figure":
      return (
        <figure className="report-figure">
          <Image
            src={`/publications/${reportId}/${section.path}`}
            alt={section.alt}
            width={1600}
            height={1000}
            sizes="(max-width: 900px) 100vw, 860px"
            unoptimized
            style={{ width: "100%", height: "auto" }}
          />
          {section.caption ? <figcaption>{section.caption}</figcaption> : null}
        </figure>
      );
  }
}
