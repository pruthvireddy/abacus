"use client";

import { Children, useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { ReactNode } from "react";
import {
  DISCOVERY_QUERY_MAX_CHARS, DISCOVERY_SELECTION_MAX, discoveryOptions, emptyDiscoveryState,
  hasDiscoveryCriteria, matchingStudySlugs, parseDiscoveryState, serializeDiscoveryState,
} from "@/lib/discovery";
import type { DiscoveryCategory, DiscoveryEntry, DiscoveryState } from "@/lib/discovery";

const CHANGE_EVENT = "narada-library-change";
const categoryLabels: Record<DiscoveryCategory, string> = { topic: "Topic", instrument: "Instrument", type: "Evidence type" };
const categories: DiscoveryCategory[] = ["topic", "instrument", "type"];
const emptyServerSearch = () => "";
const browserSearch = () => window.location.search;
const enhancedSnapshot = () => true;
const serverEnhancedSnapshot = () => false;
const subscribeReady = () => () => {};

export function LibraryDiscovery({ entries, children }: { entries: DiscoveryEntry[]; children: ReactNode }) {
  const queryEditing = useRef(false);
  const subscribe = useCallback((callback: () => void) => {
    const onPop = () => { queryEditing.current = false; callback(); };
    window.addEventListener("popstate", onPop);
    window.addEventListener(CHANGE_EVENT, callback);
    return () => { window.removeEventListener("popstate", onPop); window.removeEventListener(CHANGE_EVENT, callback); };
  }, []);
  const search = useSyncExternalStore(subscribe, browserSearch, emptyServerSearch);
  const enhanced = useSyncExternalStore(subscribeReady, enhancedSnapshot, serverEnhancedSnapshot);
  const options = useMemo(() => discoveryOptions(entries), [entries]);
  const state = useMemo(() => parseDiscoveryState(search, options), [search, options]);
  const matching = useMemo(() => matchingStudySlugs(entries, state), [entries, state]);
  const visible = useMemo(() => new Set(matching), [matching]);
  const hasCriteria = hasDiscoveryCriteria(state);
  const canonical = serializeDiscoveryState(state, options);
  const cards = Children.toArray(children);
  const unclassified = entries.filter(entry => entry.evidenceType === null).length;
  if (cards.length !== entries.length) throw new Error("Discovery entries and static study cards must have matching authored order.");
  const [announcement, setAnnouncement] = useState(`${entries.length} studies available.`);

  useEffect(() => {
    if (search === canonical) return;
    window.history.replaceState(null, "", `${window.location.pathname}${canonical}${window.location.hash}`);
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }, [search, canonical]);
  useEffect(() => {
    const timer = window.setTimeout(() => setAnnouncement(`${matching.length} of ${entries.length} studies ${hasCriteria ? "match" : "available"}.`), 350);
    return () => window.clearTimeout(timer);
  }, [matching.length, entries.length, hasCriteria]);

  const update = (next: DiscoveryState, replace = false) => {
    const nextSearch = serializeDiscoveryState(next, options);
    if (window.location.search === nextSearch) return;
    window.history[replace ? "replaceState" : "pushState"](null, "", `${window.location.pathname}${nextSearch}${window.location.hash}`);
    window.dispatchEvent(new Event(CHANGE_EVENT));
  };
  const reset = () => { queryEditing.current = false; update(emptyDiscoveryState()); };
  const remove = (category: DiscoveryCategory, value: string) => {
    queryEditing.current = false;
    update({ ...state, [category]: state[category].filter(selection => selection !== value) });
  };
  return <div className="library-discovery" data-discovery-count={matching.length}>
    <form className="discovery-controls" role="search" aria-label="Search and filter studies" onSubmit={event => event.preventDefault()}>
      <fieldset disabled={!enhanced}>
        <legend className="visually-hidden">Find studies in the research library</legend>
        <div className="discovery-search-row"><label htmlFor="study-search">Search studies <span className="discovery-inline-count" aria-hidden="true">{matching.length} of {entries.length} studies</span></label><div className="discovery-search-input"><input id="study-search" name="q" type="search" maxLength={DISCOVERY_QUERY_MAX_CHARS} value={state.query} placeholder="Try VWAP, overnight, or NQ" aria-describedby="discovery-rule discovery-count" onChange={event => {
          update({ ...state, query: event.target.value }, queryEditing.current);
          queryEditing.current = true;
        }} onBlur={() => { queryEditing.current = false; }} /><button type="button" disabled={!state.query} onClick={() => { queryEditing.current = false; update({ ...state, query: "" }); }}>Clear search</button></div></div>
        <div className="discovery-filter-row">{categories.map(category => <details className="discovery-filter" key={category}><summary>{categoryLabels[category]}{state[category].length ? <span>{state[category].length} selected</span> : null}</summary><div className="discovery-options">{options[category].map(option => {
          const checked = state[category].includes(option.value);
          return <label key={option.value}><input type="checkbox" checked={checked} disabled={!checked && state[category].length >= DISCOVERY_SELECTION_MAX} onChange={event => {
            queryEditing.current = false;
            update({ ...state, [category]: event.target.checked ? [...state[category], option.value] : state[category].filter(value => value !== option.value) });
          }} /><span>{option.label}</span></label>;
        })}</div></details>)}</div>
        <div className="discovery-result-row"><p id="discovery-count"><strong>{matching.length}</strong> of {entries.length} studies</p><button type="button" className="discovery-reset" hidden={!hasCriteria} onClick={reset}>Reset all</button></div>
        <p id="discovery-rule" className="discovery-rule">Every search word must match authored study text. Selections use OR within a category and AND between categories. Collection order stays authored.</p>
        {hasCriteria ? <ul className="discovery-active" aria-label="Active search and filters">{state.query ? <li><button type="button" aria-label="Remove search query" onClick={() => { queryEditing.current = false; update({ ...state, query: "" }); }}>Search: {state.query.trim()} <span aria-hidden="true">×</span></button></li> : null}{categories.flatMap(category => state[category].map(value => <li key={`${category}:${value}`}><button type="button" aria-label={`Remove ${categoryLabels[category].toLowerCase()}: ${options[category].find(option => option.value === value)?.label}`} onClick={() => remove(category, value)}>{categoryLabels[category]}: {options[category].find(option => option.value === value)?.label}<span aria-hidden="true">×</span></button></li>))}</ul> : null}
      </fieldset>
      <noscript><p className="discovery-noscript">Search and filters need JavaScript. The complete collection and all study links are available below.</p></noscript>
    </form>
    <p className="visually-hidden discovery-announcement" role="status" aria-live="polite" aria-atomic="true">{announcement}</p>
    <p className="discovery-print-context">Library view: {matching.length} of {entries.length} studies.{hasCriteria ? ` Active selections: ${[state.query ? `Search: ${state.query.trim()}` : "", ...categories.flatMap(category => state[category].map(value => `${categoryLabels[category]}: ${options[category].find(option => option.value === value)?.label}`))].filter(Boolean).join("; ")}.` : " Authored collection order."}</p>
    <div className="discovery-empty" hidden={matching.length !== 0}><h3>No studies match these selections.</h3><p>Try a broader phrase, remove a selection, or use Reset all above.</p></div>
    <div className="study-grid discovery-grid">{cards.map((card, index) => <div className="discovery-card-slot" key={entries[index].slug} data-study-slug={entries[index].slug} hidden={!visible.has(entries[index].slug)}>{card}</div>)}</div>
    {unclassified ? <p className="discovery-metadata-note">{unclassified} {unclassified === 1 ? "study does" : "studies do"} not specify an evidence type. They remain available when no evidence-type filter is selected.</p> : null}
  </div>;
}
