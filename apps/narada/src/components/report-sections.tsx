import Image from "next/image";
import type { ReportPattern, ReportSection, SourceReference } from "../../types/report";
import { formatValue } from "@/lib/format";
import { SectionReferences } from "@/components/publication-evidence";
import { ReportTable } from "./report-table";
import { FilteredReportTable } from "./filtered-report-table";
import { initialSavedTable } from "@/lib/table-filters";
import { PatternDefinitions, PatternPanel } from "./pattern-panel";

export function ReportSections({ sections, reportId, references, patterns, patternDefinitionsProvided = false, explainedPatternIds = [] }: { sections: ReportSection[]; reportId: string; references?: SourceReference[]; patterns?: ReportPattern[]; patternDefinitionsProvided?: boolean; explainedPatternIds?: string[] }) {
  const explainedPatterns = new Set(explainedPatternIds);
  return <>
    {patterns?.length && !patternDefinitionsProvided ? <PatternDefinitions patterns={patterns} reportId={reportId} /> : null}
    {sections.map((section, index) => {
    const pattern = patterns?.find(item => item.id === section.patternId);
    const compact = pattern ? explainedPatterns.has(pattern.id) : false;
    if (pattern) explainedPatterns.add(pattern.id);
    return (
    <section key={section.id} id={`section-${section.id}`} className={`report-section section-${section.kind}`} aria-labelledby={`heading-${section.id}`}>
      <div className="section-heading">
        <span className="section-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
        <h2 id={`heading-${section.id}`}>{section.title}</h2>
      </div>
      {pattern ? <PatternPanel pattern={pattern} instanceId={`pattern-section-${section.id}`} focus={section.patternFocus} symbolReportId={reportId} compact={compact} /> : null}
      <SectionContent section={section} reportId={reportId} />
      <SectionReferences ids={section.referenceIds} references={references} />
    </section>
    );
    })}
  </>;
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
      return section.rowFilters?.length ? <FilteredReportTable initialSection={initialSavedTable(section)} reportId={reportId} totalSavedRows={section.rows.length} /> : <ReportTable section={section} />;
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
