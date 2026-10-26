"use client";

import { useEffect, useRef, useState } from "react";
import type { TableSection } from "../../types/report";
import { formatValue } from "@/lib/format";
import { savedDefaultSelections, savedFilterOptions, selectSavedRows, TABLE_PAGE_ROWS } from "@/lib/table-filters";
import { loadSavedTables } from "@/lib/saved-tables";
import { ReportTable } from "./report-table";

type Props = { initialSection: TableSection; reportId: string; totalSavedRows: number };

export function FilteredReportTable(props: Props) {
  return <SavedReportTable key={`${props.reportId}/${props.initialSection.id}/${props.totalSavedRows}`} {...props} />;
}

function SavedReportTable({ initialSection, reportId, totalSavedRows }: Props) {
  const [savedSection, setSavedSection] = useState<TableSection | null>(null);
  const [loadState, setLoadState] = useState<"idle" | "loading" | "loaded" | "error">("idle");
  const [selections, setSelections] = useState<Record<string, string>>(() => savedDefaultSelections(initialSection));
  const [page, setPage] = useState(0);
  const active = useRef(false);
  const inFlight = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; };
  }, []);
  async function loadSelections() {
    if (inFlight.current) return;
    inFlight.current = true;
    setLoadState("loading");
    try {
      const tables = await loadSavedTables(reportId);
      const section = tables.find(table => table.id === initialSection.id);
      if (!section || section.rows.length !== totalSavedRows) throw new Error("Saved table identity changed.");
      if (active.current) { setSavedSection(section); setLoadState("loaded"); }
    } catch {
      if (active.current) setLoadState("error");
    } finally {
      inFlight.current = false;
    }
  }
  const section = savedSection ?? initialSection;
  const matchedRows = selectSavedRows(section.rows, selections);
  const pageCount = Math.max(1, Math.ceil(matchedRows.length / TABLE_PAGE_ROWS));
  const currentPage = Math.min(page, pageCount - 1);
  const rows = matchedRows.slice(currentPage * TABLE_PAGE_ROWS, (currentPage + 1) * TABLE_PAGE_ROWS);
  const filtered = Object.values(selections).some(Boolean);
  return <ReportTable section={section} rows={rows} controls={<div className="table-filter-controls">
    {!savedSection && loadState !== "error" ? <button type="button" onClick={loadSelections} disabled={loadState === "loading"}>{loadState === "loading" ? "Loading table filters…" : "Load table filters"}</button> : null}
    <div className="table-filters" role="group" aria-label={`Filter saved rows: ${section.title}`}>
      {(section.rowFilters ?? []).map(filter => {
        const column = section.columns.find(candidate => candidate.key === filter.key);
        return <label key={filter.key} htmlFor={`filter-${section.id}-${filter.key}`}>{filter.label}
          <select id={`filter-${section.id}-${filter.key}`} disabled={!savedSection} value={selections[filter.key] ?? ""} onChange={event => {
            const value = event.target.value;
            setSelections(current => ({ ...current, [filter.key]: value })); setPage(0);
          }}>
            <option value="">All values</option>
            {savedFilterOptions(section, filter.key).map(option => <option key={option.value} value={option.value}>{formatValue(option.label, { format: column?.format, precision: column?.precision })}</option>)}
          </select>
        </label>;
      })}
      <button type="button" onClick={() => { setSelections({}); setPage(0); }} disabled={!savedSection || !filtered}>Reset selections</button>
    </div>
    <p className="table-filter-status" role="status" aria-live="polite">{savedSection ? `Showing ${rows.length} of ${matchedRows.length} matching saved rows (${totalSavedRows} total).` : loadState === "error" ? `Showing ${rows.length} default saved rows. Other selections are unavailable.` : loadState === "loading" ? `Showing ${rows.length} saved rows. Loading table filters…` : `Showing ${rows.length} saved rows. Load table filters to choose other saved rows.`} Selections only change the rows shown.</p>
    {pageCount > 1 && savedSection ? <div className="table-pagination" aria-label={`Saved row pages: ${section.title}`}><button type="button" disabled={currentPage === 0} onClick={() => setPage(current => Math.max(0, current - 1))}>Previous rows</button><span>Page {currentPage + 1} of {pageCount}</span><button type="button" disabled={currentPage + 1 === pageCount} onClick={() => setPage(current => current + 1)}>Next rows</button></div> : null}
    {loadState === "error" ? <p className="table-load-error" role="alert">Saved selections could not load. <button type="button" onClick={loadSelections}>Try again</button> or <a href={`/publications/${reportId}/report.json`}>view the saved publication data</a>.</p> : null}
    <noscript><p>Enable JavaScript to select other saved rows, or use the evidence downloads below for every group.</p></noscript>
  </div>} />;
}
