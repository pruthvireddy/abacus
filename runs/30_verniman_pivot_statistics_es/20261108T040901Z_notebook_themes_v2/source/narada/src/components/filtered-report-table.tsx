"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import type { TableSection } from "../../types/report";
import { formatValue } from "@/lib/format";
import { savedDefaultSelections, savedFilterOptions, selectSavedRows, TABLE_PAGE_ROWS } from "@/lib/table-filters";
import { applyTableSelection, parseTableSelection, tableSelectionHref } from "@/lib/table-share";
import { loadSavedTables } from "@/lib/saved-tables";
import { ReportTable } from "./report-table";

type Props = { initialSection: TableSection; reportId: string; totalSavedRows: number };
const subscribeLocation = (listener: () => void) => {
  window.addEventListener("popstate", listener);
  return () => window.removeEventListener("popstate", listener);
};
const currentSearch = () => window.location.search;
const serverSearch = () => "";

export function FilteredReportTable(props: Props) {
  return <SavedReportTable key={`${props.reportId}/${props.initialSection.id}/${props.totalSavedRows}`} {...props} />;
}

function SavedReportTable({ initialSection, reportId, totalSavedRows }: Props) {
  const [savedSection, setSavedSection] = useState<TableSection | null>(null);
  const [loadState, setLoadState] = useState<"idle" | "loading" | "loaded" | "error">("idle");
  const [selections, setSelections] = useState<Record<string, string>>(() => savedDefaultSelections(initialSection));
  const [page, setPage] = useState(0);
  const [appliedShare, setAppliedShare] = useState<string | null>(null);
  const [shareNotice, setShareNotice] = useState("");
  const [copyNotice, setCopyNotice] = useState("");
  const search = useSyncExternalStore(subscribeLocation, currentSearch, serverSearch);
  const pending = parseTableSelection(search, reportId, initialSection);
  const pendingWaiting = pending.status === "pending" && pending.token !== appliedShare;
  const active = useRef(false);
  const inFlight = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; };
  }, []);
  function applyLinkedSelection(section: TableSection) {
    const linked = parseTableSelection(window.location.search, reportId, initialSection);
    if (linked.status === "pending") {
      const restored = applyTableSelection(section, linked);
      setSelections(restored.selections); setPage(0); setAppliedShare(linked.token);
      setShareNotice(restored.ignored ? "Some linked selections are unavailable in this saved table; available values and authored defaults are shown." : "Linked selections applied to saved rows. No values were recomputed.");
    } else if (linked.status === "invalid") {
      setShareNotice("The linked table selection is invalid. Authored defaults are shown.");
    }
  }
  async function loadSelections() {
    if (inFlight.current) return;
    if (savedSection) { applyLinkedSelection(savedSection); return; }
    inFlight.current = true;
    setLoadState("loading");
    try {
      const tables = await loadSavedTables(reportId);
      const section = tables.find(table => table.id === initialSection.id);
      if (!section || section.rows.length !== totalSavedRows) throw new Error("Saved table identity changed.");
      if (active.current) { setSavedSection(section); setLoadState("loaded"); applyLinkedSelection(section); }
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
  const firstRow = rows.length ? currentPage * TABLE_PAGE_ROWS + 1 : 0;
  const lastRow = rows.length ? firstRow + rows.length - 1 : 0;
  const filtered = Object.values(selections).some(Boolean);
  const summary = (section.rowFilters ?? []).map(filter => {
    const value = selections[filter.key];
    const column = section.columns.find(candidate => candidate.key === filter.key);
    return `${filter.label}: ${value ? formatValue(JSON.parse(value), { format: column?.format, precision: column?.precision }) : "All values"}`;
  }).join("; ");
  const shareHref = savedSection ? tableSelectionHref(reportId, section, selections) : null;
  const printContext = <p className="table-print-context">{savedSection ? `Displayed saved rows ${firstRow}–${lastRow} of ${matchedRows.length} matching rows; page ${currentPage + 1} of ${pageCount}; ${totalSavedRows} saved rows in this selected table.` : `Displayed authored default slice: ${rows.length} rows; ${totalSavedRows} saved rows in this selected table. Other saved rows have not been loaded.`} Active selections: {summary || "All values"}. This printed slice is not the complete research dataset. Report {reportId}; table {section.id}.</p>;
  return <ReportTable section={section} rows={rows} printContext={printContext} controls={<div className="table-filter-controls">
    {!savedSection && loadState !== "error" ? <button type="button" onClick={loadSelections} disabled={loadState === "loading"}>{loadState === "loading" ? "Loading table filters…" : "Load table filters"}</button> : null}
    {pendingWaiting ? <p className="table-pending-selection">A linked selection is waiting. {savedSection ? <button type="button" onClick={loadSelections}>Apply linked selections</button> : "Load table filters to apply it. Authored defaults remain visible until loading succeeds."}</p> : null}
    {pending.status === "invalid" && !shareNotice ? <p className="table-selection-notice">The linked table selection is invalid. Authored defaults remain available.</p> : null}
    <div className="table-filters" role="group" aria-label={`Filter saved rows: ${section.title}`}>
      {(section.rowFilters ?? []).map(filter => {
        const column = section.columns.find(candidate => candidate.key === filter.key);
        return <label key={filter.key} htmlFor={`filter-${section.id}-${filter.key}`}><span className="table-filter-label">{filter.label}</span>
          <select id={`filter-${section.id}-${filter.key}`} disabled={!savedSection} value={selections[filter.key] ?? ""} onChange={event => {
            const value = event.target.value;
            setSelections(current => ({ ...current, [filter.key]: value })); setPage(0); setCopyNotice(""); setShareNotice("");
          }}>
            <option value="">All values</option>
            {savedFilterOptions(section, filter.key).map(option => <option key={option.value} value={option.value}>{formatValue(option.label, { format: column?.format, precision: column?.precision })}</option>)}
          </select>
        </label>;
      })}
      <button type="button" onClick={() => { setSelections({}); setPage(0); setCopyNotice(""); setShareNotice(""); }} disabled={!savedSection || !filtered}>Reset selections</button>
      <button type="button" onClick={() => { setSelections(savedDefaultSelections(section)); setPage(0); setCopyNotice(""); setShareNotice(""); }} disabled={!savedSection}>Restore authored defaults</button>
    </div>
    <p className="table-active-selections">Current selection: {summary || "All values"}.</p>
    <p className="table-filter-status" role="status" aria-live="polite">{savedSection ? `Showing ${rows.length} of ${matchedRows.length} matching saved rows (${totalSavedRows} total).` : loadState === "error" ? `Showing ${rows.length} default saved rows. Other selections are unavailable.` : loadState === "loading" ? `Showing ${rows.length} saved rows. Loading table filters…` : `Showing ${rows.length} saved rows. Load table filters to choose other saved rows.`} Selections only change the rows shown.</p>
    {pageCount > 1 && savedSection ? <div className="table-pagination" aria-label={`Saved row pages: ${section.title}`}><button type="button" disabled={currentPage === 0} onClick={() => setPage(current => Math.max(0, current - 1))}>Previous rows</button><span>Page {currentPage + 1} of {pageCount} · rows {firstRow}–{lastRow}</span><button type="button" disabled={currentPage + 1 === pageCount} onClick={() => setPage(current => current + 1)}>Next rows</button></div> : null}
    {shareNotice ? <p className="table-selection-notice">{shareNotice}</p> : null}
    <div className="table-share-links"><a href={`/reports/${reportId}/#section-${section.id}`}>Open section link</a>{savedSection && shareHref ? <><a href={shareHref}>Open selected rows link</a><button type="button" onClick={async () => {
      try { await navigator.clipboard.writeText(new URL(shareHref, window.location.origin).href); setCopyNotice("Selection link copied."); }
      catch { setCopyNotice("Copy is unavailable. Use the selected rows link."); }
    }}>Copy selection link</button></> : savedSection ? <span>The selected values exceed the sharing limit; use the section link.</span> : null}</div>
    {copyNotice ? <p className="table-copy-notice" role="status">{copyNotice}</p> : null}
    {loadState === "error" ? <p className="table-load-error" role="alert">Saved selections could not load. <button type="button" onClick={loadSelections}>Try again</button> or <a href={`/publications/${reportId}/report.json`}>view the saved publication data</a>.</p> : null}
    <noscript><p>Enable JavaScript to select other saved rows, or use the evidence downloads below for every group.</p></noscript>
  </div>} />;
}
