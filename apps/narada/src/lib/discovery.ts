import type { Study } from "../../types/study";

export const DISCOVERY_QUERY_MAX_CHARS = 120;
export const DISCOVERY_SELECTION_MAX = 8;
export const DISCOVERY_URL_MAX_CHARS = 2048;
export const DISCOVERY_INDEX_MAX_BYTES = 48 * 1024;

export type DiscoveryEntry = {
  slug: string;
  searchText: string;
  topic: string;
  instruments: string[];
  evidenceType: string | null;
};
export type DiscoveryOption = { value: string; label: string };
export type DiscoveryOptions = {
  topic: DiscoveryOption[];
  instrument: DiscoveryOption[];
  type: DiscoveryOption[];
};
export type DiscoveryCategory = keyof DiscoveryOptions;
export type DiscoveryState = {
  query: string;
  topic: string[];
  instrument: string[];
  type: string[];
};
export const emptyDiscoveryState = (): DiscoveryState => ({ query: "", topic: [], instrument: [], type: [] });

// Search is a conjunction of substring terms. Letter case, accents, whitespace,
// and punctuation do not change matching; no report body participates.
export function normalizeDiscoveryText(value: string): string {
  return value.normalize("NFKD").replace(/\p{M}/gu, "").toLocaleLowerCase("en-US")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim().replace(/\s+/g, " ");
}
export function discoveryIndexBytes(entries: DiscoveryEntry[]): number {
  return new TextEncoder().encode(JSON.stringify(entries)).length;
}
export function buildDiscoveryIndex(studies: Study[]): DiscoveryEntry[] {
  const entries = studies.map(study => ({
    slug: study.slug,
    searchText: normalizeDiscoveryText([study.title, study.overview?.question, study.summary,
      study.overview?.takeaway, study.topic, ...study.products, ...(study.keywords ?? [])].filter(Boolean).join(" ")),
    topic: study.topic.replaceAll("_", " "),
    instruments: [...study.products],
    evidenceType: study.overview?.evidenceType ?? null,
  }));
  if (discoveryIndexBytes(entries) > DISCOVERY_INDEX_MAX_BYTES) throw new Error("Discovery index exceeds its 48 KiB budget.");
  return entries;
}
function optionsFor(values: string[]): DiscoveryOption[] {
  const valuesByKey = new Map<string, DiscoveryOption>();
  for (const label of values) {
    const value = normalizeDiscoveryText(label);
    if (value && !valuesByKey.has(value)) valuesByKey.set(value, { value, label });
  }
  return [...valuesByKey.values()].sort((a, b) => a.label.localeCompare(b.label, "en"));
}
export function discoveryOptions(entries: DiscoveryEntry[]): DiscoveryOptions {
  return {
    topic: optionsFor(entries.map(entry => entry.topic)),
    instrument: optionsFor(entries.flatMap(entry => entry.instruments)),
    type: optionsFor(entries.flatMap(entry => entry.evidenceType === null ? [] : [entry.evidenceType])),
  };
}
function cleanQuery(value: unknown): string {
  if (typeof value !== "string" || value.length > DISCOVERY_QUERY_MAX_CHARS) return "";
  // Retain ordinary typing whitespace in the controlled input. Matching alone
  // normalizes it, so typing the space between two words never moves the caret.
  const query = value.replace(/[\u0000-\u001f\u007f]/g, " ");
  return normalizeDiscoveryText(query) ? query : "";
}
function selections(values: string[], options: DiscoveryOption[]): string[] {
  const requested = new Set(values.slice(0, 200).map(normalizeDiscoveryText));
  return options.filter(option => requested.has(option.value)).slice(0, DISCOVERY_SELECTION_MAX).map(option => option.value);
}
export function normalizeDiscoveryState(state: DiscoveryState, options: DiscoveryOptions): DiscoveryState {
  return {
    query: cleanQuery(state.query),
    topic: selections(state.topic ?? [], options.topic),
    instrument: selections(state.instrument ?? [], options.instrument),
    type: selections(state.type ?? [], options.type),
  };
}
export function parseDiscoveryState(search: string, options: DiscoveryOptions): DiscoveryState {
  if (search.length > DISCOVERY_URL_MAX_CHARS) return emptyDiscoveryState();
  const params = new URLSearchParams(search);
  return normalizeDiscoveryState({ query: params.get("q") ?? "", topic: params.getAll("topic"),
    instrument: params.getAll("instrument"), type: params.getAll("type") }, options);
}
export function serializeDiscoveryState(state: DiscoveryState, options: DiscoveryOptions): string {
  const normalized = normalizeDiscoveryState(state, options);
  let params = new URLSearchParams();
  if (normalized.query) params.set("q", normalized.query);
  for (const category of ["topic", "instrument", "type"] as const) {
    for (const value of normalized[category]) {
      const candidate = new URLSearchParams(params);
      candidate.append(category, value);
      if (candidate.toString().length + 1 <= DISCOVERY_URL_MAX_CHARS) params = candidate;
    }
  }
  const query = params.toString();
  // Bound shared state without discarding an existing query or all selections
  // when an unusually long additional filter would exceed the URL budget.
  return query ? `?${query}` : "";
}
export function hasDiscoveryCriteria(state: DiscoveryState): boolean {
  return Boolean(normalizeDiscoveryText(state.query) || state.topic.length || state.instrument.length || state.type.length);
}
export function matchingStudySlugs(entries: DiscoveryEntry[], state: DiscoveryState): string[] {
  const terms = normalizeDiscoveryText(state.query).split(" ").filter(Boolean);
  return entries.filter(entry => terms.every(term => entry.searchText.includes(term))
    && (!state.topic.length || state.topic.includes(normalizeDiscoveryText(entry.topic)))
    && (!state.instrument.length || entry.instruments.some(instrument => state.instrument.includes(normalizeDiscoveryText(instrument))))
    && (!state.type.length || (entry.evidenceType !== null && state.type.includes(normalizeDiscoveryText(entry.evidenceType)))))
    .map(entry => entry.slug);
}
