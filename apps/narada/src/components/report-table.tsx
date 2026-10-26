import type { ReactNode } from "react";
import type { TableSection } from "../../types/report";
import { formatValue } from "@/lib/format";

export function ReportTable({ section, rows = section.rows, controls }: { section: TableSection; rows?: TableSection["rows"]; controls?: ReactNode }) {
  return <div className="table-presentation">
    {section.description ? <p className="table-description" id={`table-context-${section.id}`}>{section.description}</p> : null}
    {controls}
    <p className="table-hint" id={`table-help-${section.id}`}>Scroll horizontally: focus this table; use left and right arrow keys. Missing or blank cells display as Not available; see notes.</p>
    <div className="table-scroll" role="region" aria-labelledby={`heading-${section.id}`} aria-describedby={[`table-help-${section.id}`, ...(section.description ? [`table-context-${section.id}`] : []), ...(section.notes?.length ? [`table-notes-${section.id}`] : [])].join(" ")} tabIndex={0}>
      <table>
        <caption className="visually-hidden">{section.title}</caption>
        <thead><tr>{section.columns.map(column => <th key={column.key} scope="col" className={column.format ? "numeric" : undefined}>{column.label}{column.unit ? <span className="column-unit">{column.unit}</span> : null}</th>)}</tr></thead>
        <tbody>{rows.length ? rows.map((row, index) => <tr key={index}>{section.columns.map(column => <td key={column.key} className={column.format ? "numeric" : undefined}>{formatValue(Object.hasOwn(row, column.key) ? row[column.key] : null, { format: column.format, precision: column.precision })}</td>)}</tr>) : <tr><td colSpan={section.columns.length} className="table-empty">No saved rows match these selections.</td></tr>}</tbody>
      </table>
    </div>
    {section.notes?.length ? <ul className="table-notes" id={`table-notes-${section.id}`}>{section.notes.map((note, index) => <li key={index}>{note}</li>)}</ul> : null}
  </div>;
}
