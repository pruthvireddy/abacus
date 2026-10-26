import type { TableSection } from "../../types/report";
import { savedDefaultSelections, savedFilterOptions } from "./table-filters";

export const TABLE_SHARE_MAX_QUERY = 4096;
export const TABLE_SHARE_MAX_JSON = 2048;
const safeId = (value: string) => /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value) && value.length <= 80;
const scalarKey = (value: unknown): value is string => {
  if (typeof value !== "string" || value.length > 1100) return false;
  if (value === "") return true; // Explicitly select All values, distinct from a missing default.
  try {
    const cell: unknown = JSON.parse(value);
    return (cell === null || typeof cell === "boolean" || typeof cell === "string" || (typeof cell === "number" && Number.isFinite(cell)))
      && JSON.stringify(cell) === value;
  } catch { return false; }
};
export type PendingTableSelection =
  | { status: "none" }
  | { status: "invalid" }
  | { status: "pending"; selections: Record<string, string>; token: string; ignored: boolean };

// This parses bounded presentation selections only. Membership in the saved
// table is checked after explicit reader activation, never by fetching on mount.
export function parseTableSelection(search: string, reportId: string, section: TableSection): PendingTableSelection {
  if (!safeId(reportId) || !safeId(section.id)) return { status: "invalid" };
  const params = new URLSearchParams(search.slice(0, TABLE_SHARE_MAX_QUERY + 1));
  if (params.get("table") !== section.id) return { status: "none" };
  if (search.length > TABLE_SHARE_MAX_QUERY || params.getAll("table").length !== 1 || params.getAll("filters").length !== 1) return { status: "invalid" };
  const raw = params.get("filters") ?? "";
  if (!raw || raw.length > TABLE_SHARE_MAX_JSON) return { status: "invalid" };
  let parsed: unknown;
  try { parsed = JSON.parse(raw); } catch { return { status: "invalid" }; }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || Object.keys(parsed).length > 3) return { status: "invalid" };
  const allowed = new Set((section.rowFilters ?? []).map(filter => filter.key));
  let ignored = false;
  const selected: Array<[string, string]> = [];
  for (const [key, value] of Object.entries(parsed)) {
    if (!allowed.has(key) || !scalarKey(value)) { ignored = true; continue; }
    selected.push([key, value]);
  }
  return { status: "pending", selections: Object.fromEntries(selected), token: raw, ignored };
}

export function applyTableSelection(section: TableSection, pending: Extract<PendingTableSelection, { status: "pending" }>) {
  const selections = savedDefaultSelections(section);
  let ignored = pending.ignored;
  for (const filter of section.rowFilters ?? []) {
    if (!Object.hasOwn(pending.selections, filter.key)) continue;
    const value = pending.selections[filter.key];
    if (value === "" || savedFilterOptions(section, filter.key).some(option => option.value === value)) selections[filter.key] = value;
    else ignored = true;
  }
  return { selections, ignored };
}

export function tableSelectionHref(reportId: string, section: TableSection, selections: Record<string, string>): string | null {
  if (!safeId(reportId) || !safeId(section.id)) return null;
  const entries = (section.rowFilters ?? []).map(filter => [filter.key, selections[filter.key] ?? ""] as const);
  if (entries.some(([, value]) => !scalarKey(value))) return null;
  if (entries.some(([key, value]) => value !== "" && !savedFilterOptions(section, key).some(option => option.value === value))) return null;
  const raw = JSON.stringify(Object.fromEntries(entries));
  if (raw.length > TABLE_SHARE_MAX_JSON) return null;
  const query = new URLSearchParams({ table: section.id, filters: raw }).toString();
  if (query.length + 1 > TABLE_SHARE_MAX_QUERY) return null;
  return `/reports/${reportId}/?${query}#section-${section.id}`;
}
