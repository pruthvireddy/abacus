import type { TableSection } from "../../types/report";

export const savedValueKey = (value: string | number | boolean | null | undefined) => JSON.stringify(value ?? null);
export const TABLE_PAGE_ROWS = 100;
const savedCell = (row: TableSection["rows"][number], key: string) => Object.hasOwn(row, key) ? row[key] ?? null : null;

export function savedFilterOptions(section: TableSection, key: string) {
  const values = new Map<string, string | number | boolean | null>();
  for (const row of section.rows) values.set(savedValueKey(savedCell(row, key)), savedCell(row, key));
  return [...values].map(([value, label]) => ({ value, label }));
}

export function savedDefaultSelections(section: TableSection) {
  return Object.fromEntries((section.rowFilters ?? []).filter(filter => Object.hasOwn(filter, "defaultValue"))
    .map(filter => [filter.key, savedValueKey(filter.defaultValue)]));
}

// Select existing rows only; values, denominators and ordering stay unchanged.
export function selectSavedRows(rows: TableSection["rows"], selections: Record<string, string>) {
  return rows.filter(row => Object.entries(selections).every(([key, value]) => !value || savedValueKey(savedCell(row, key)) === value));
}

export function initialSavedTable(section: TableSection): TableSection {
  return { ...section, rows: selectSavedRows(section.rows, savedDefaultSelections(section)).slice(0, TABLE_PAGE_ROWS) };
}
