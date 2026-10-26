import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';
import * as discovery from '../src/lib/discovery.ts';

const { buildDiscoveryIndex, discoveryIndexBytes, discoveryOptions, emptyDiscoveryState,
  hasDiscoveryCriteria, matchingStudySlugs, normalizeDiscoveryText, parseDiscoveryState,
  serializeDiscoveryState, DISCOVERY_INDEX_MAX_BYTES, DISCOVERY_SELECTION_MAX, DISCOVERY_URL_MAX_CHARS,
} = discovery;
const sourceStudies = [
  { slug: 'nq-source', title: 'NQ advanced AMD', summary: 'Weekly context and permission to abstain.', topic: 'Source_review', products: ['NQ'], keywords: ['Tmac', 'Café'], evidenceStatus: 'Not a filter classification.', overview: { question: 'What does the lesson teach?', takeaway: 'Conditional weekly view.', evidenceType: 'Qualitative source review' } },
  { slug: 'session-vwap', title: 'Session-anchored VWAP', summary: 'ES, NQ and GC price paths.', topic: 'VWAP', products: ['ES', 'NQ', 'GC'], overview: { question: 'Does price return?', takeaway: 'No stable incremental edge.', evidenceType: 'Descriptive price-path study' } },
  { slug: 'gc-policy', title: 'GC overnight breakout', summary: 'Frozen baseline retained.', topic: 'Overnight_breakout', products: ['GC'], overview: { question: 'Does waiting help?', takeaway: 'No primary policy qualified.', evidenceType: 'Frozen policy comparison' } },
  { slug: 'unclassified', title: 'Local manual', summary: 'A source companion.', topic: 'Source review', products: ['Multiple markets'] },
];
const entries = buildDiscoveryIndex(sourceStudies);
const options = discoveryOptions(entries);
const matches = search => matchingStudySlugs(entries, parseDiscoveryState(search, options));

test('the build-resolved index includes only explicit authored search fields and keeps publication data out', () => {
  const studies = structuredClone(sourceStudies);
  studies[0].report = { sections: [{ rows: [{ private: 'unselected-ledger-secret' }] }] };
  studies[0].overview.statistics = [{ value: 123456789, source: { publicationId: 'not-search-index-material' } }];
  const before = JSON.stringify(studies);
  const index = buildDiscoveryIndex(studies);
  assert.deepEqual(Object.keys(index[0]).sort(), ['evidenceType', 'instruments', 'searchText', 'slug', 'topic']);
  for (const phrase of ['nq advanced amd', 'weekly context', 'what does the lesson teach', 'conditional weekly view', 'tmac', 'cafe']) assert(index[0].searchText.includes(phrase));
  assert(!JSON.stringify(index).includes('not-search-index-material'));
  assert(!JSON.stringify(index).includes('unselected-ledger-secret'));
  assert(!JSON.stringify(index).includes('Not a filter classification'));
  assert.equal(JSON.stringify(studies), before);
  assert.equal(index[3].evidenceType, null, 'Missing evidence-type metadata stays unclassified.');
  assert.equal(options.topic.filter(option => option.value === 'source review').length, 1);
});

test('case, accents, punctuation and whitespace have predictable AND-term matching across authored fields', () => {
  assert.equal(normalizeDiscoveryText('  SESSION—VWAP / NQ  '), 'session vwap nq');
  assert.deepEqual(matches('?q=SESSION%20%20VWAP%20NQ'), ['session-vwap']);
  assert.deepEqual(matches('?q=weekly-view%20Tmac'), ['nq-source']);
  assert.deepEqual(matches('?q=CAF%C3%89'), ['nq-source']);
  assert.deepEqual(matches('?q=weekly%20GC'), []);
  assert.deepEqual(matches('?q=%20%20%20'), entries.map(entry => entry.slug));
  assert.deepEqual(matches('?q=not-a-saved-study'), []);
});

test('filters use OR within a category and AND across categories and search, preserving authored order', () => {
  assert.deepEqual(matches('?instrument=nq&instrument=gc'), ['nq-source', 'session-vwap', 'gc-policy']);
  assert.deepEqual(matches('?instrument=nq&instrument=gc&topic=vwap'), ['session-vwap']);
  assert.deepEqual(matches('?topic=source+review&type=qualitative+source+review'), ['nq-source']);
  assert.deepEqual(matches('?q=retained&instrument=gc'), ['gc-policy']);
  assert.deepEqual(matches('?instrument=gc&type=qualitative+source+review'), []);
  assert.deepEqual(matches('?topic=source+review'), ['nq-source', 'unclassified']);
  assert.deepEqual(matches('?type=frozen+policy+comparison'), ['gc-policy']);
});

test('shared URLs canonicalize valid catalog selections, duplicates and unknown parameters without inventing values', () => {
  const state = parseDiscoveryState('?q=VWAP&instrument=GC&instrument=gc&topic=VWAP&topic=private&type=made-up&sort=quality', options);
  assert.deepEqual(state, { query: 'VWAP', topic: ['vwap'], instrument: ['gc'], type: [] });
  assert.equal(serializeDiscoveryState(state, options), '?q=VWAP&topic=vwap&instrument=gc');
  assert.equal(serializeDiscoveryState(emptyDiscoveryState(), options), '');
  assert.equal(hasDiscoveryCriteria(emptyDiscoveryState()), false);
  assert.equal(hasDiscoveryCriteria(state), true);
  assert.deepEqual(parseDiscoveryState('?unknown=anything', options), emptyDiscoveryState());
  const canonical = serializeDiscoveryState(state, options);
  assert.deepEqual(parseDiscoveryState(canonical, options), state);
});

test('bounded URL state ignores stale or oversized input and retains query whitespace while typing', () => {
  assert.deepEqual(parseDiscoveryState(`?q=${'a'.repeat(121)}`, options), emptyDiscoveryState());
  assert.deepEqual(parseDiscoveryState(`?q=${'a'.repeat(DISCOVERY_URL_MAX_CHARS + 1)}`, options), emptyDiscoveryState());
  const typing = parseDiscoveryState('?q=weekly+', options);
  assert.equal(typing.query, 'weekly ');
  assert.equal(serializeDiscoveryState(typing, options), '?q=weekly+');
  assert.deepEqual(matchingStudySlugs(entries, typing), ['nq-source']);
  const many = { ...options, type: Array.from({ length: 12 }, (_, index) => ({ value: `saved category ${index} ${'x'.repeat(100)}`, label: `Saved category ${index}` })) };
  const state = { query: `VWAP${'😀'.repeat(55)}`, topic: [], instrument: [], type: many.type.map(option => option.value) };
  const url = serializeDiscoveryState(state, many);
  assert(url.length <= DISCOVERY_URL_MAX_CHARS);
  const restored = parseDiscoveryState(url, many);
  assert.equal(restored.query, state.query);
  assert(restored.type.length <= DISCOVERY_SELECTION_MAX);
  assert(restored.type.length > 0);
});

test('the encoded URL boundary includes its leading question mark and round-trips at exactly 2048 characters', () => {
  const boundedOptions = {
    topic: [{ value: 't'.repeat(80), label: 'A bounded topic' }],
    instrument: [{ value: 'i'.repeat(40), label: 'A bounded instrument' }],
    type: [{ value: '研'.repeat(120), label: 'First bounded evidence type' },
      { value: '文'.repeat(90) + 'abc', label: 'Second bounded evidence type' }],
  };
  const state = { query: 'a', topic: [boundedOptions.topic[0].value], instrument: [boundedOptions.instrument[0].value], type: boundedOptions.type.map(option => option.value) };
  const url = serializeDiscoveryState(state, boundedOptions);
  assert.equal(url.length, DISCOVERY_URL_MAX_CHARS);
  assert.deepEqual(parseDiscoveryState(url, boundedOptions), state);
  boundedOptions.type[1].value += 'd';
  state.type[1] += 'd';
  const overflow = serializeDiscoveryState(state, boundedOptions);
  assert(overflow.length <= DISCOVERY_URL_MAX_CHARS);
  const retained = parseDiscoveryState(overflow, boundedOptions);
  assert.equal(retained.query, state.query);
  assert.deepEqual(retained.topic, state.topic);
  assert.deepEqual(retained.instrument, state.instrument);
  assert.deepEqual(retained.type, [state.type[0]], 'Only the extra oversized selection is omitted.');
});

test('restoring successive history URLs reproduces counts and authored result order', () => {
  const urls = ['', '?q=VWAP', '?q=VWAP&instrument=gc', '?instrument=nq', ''];
  const forward = urls.map(search => matches(search));
  const backward = [...urls].reverse().map(search => matches(search));
  assert.deepEqual(backward, [...forward].reverse());
  assert.deepEqual(forward.map(result => result.length), [4, 1, 1, 2, 4]);
  assert.deepEqual(forward[3], ['nq-source', 'session-vwap']);
});

const require = createRequire(import.meta.url);
function compileDiscovery() {
  const source = readFileSync(new URL('../src/components/library-discovery.tsx', import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022, esModuleInterop: true } });
  const compiledModule = { exports: {} };
  new Function('require', 'module', 'exports', outputText)(id => id === '@/lib/discovery' ? discovery : require(id), compiledModule, compiledModule.exports);
  return compiledModule.exports.LibraryDiscovery;
}
const LibraryDiscovery = compileDiscovery();

test('server rendering retains every study and usable ordinary links without JavaScript', () => {
  const children = sourceStudies.map(study => React.createElement('article', { key: study.slug }, React.createElement('a', { href: `/studies/${study.slug}/` }, study.title)));
  const html = renderToStaticMarkup(React.createElement(LibraryDiscovery, { entries }, children));
  assert.match(html, /data-discovery-count="4"/);
  assert.match(html, /fieldset disabled=""/);
  assert.match(html, /<noscript>/);
  assert.match(html, /complete collection and all study links are available below/);
  for (const entry of entries) {
    assert(html.includes(`data-study-slug="${entry.slug}"`));
    assert(html.includes(`href="/studies/${entry.slug}/"`));
    assert(!html.includes(`data-study-slug="${entry.slug}" hidden`));
  }
  assert.match(html, /label for="study-search">Search studies/);
  assert.match(html, /class="discovery-inline-count" aria-hidden="true">4 of 4 studies/);
  assert.match(html, /aria-describedby="discovery-rule discovery-count"/);
  assert.match(html, /role="status" aria-live="polite" aria-atomic="true"/);
  assert.match(html, /No studies match these selections/);
  assert.match(html, /Evidence type/);
  assert.match(html, /1 study does not specify an evidence type/);
  assert(!html.includes('role="tab"'));
});

test('the actual catalog index remains bounded and excludes raw report sections and source locators', () => {
  const catalog = JSON.parse(readFileSync(new URL('../content/studies.json', import.meta.url), 'utf8'));
  const index = buildDiscoveryIndex(catalog.studies);
  assert.equal(index.length, catalog.studies.length);
  assert(discoveryIndexBytes(index) <= DISCOVERY_INDEX_MAX_BYTES);
  const text = JSON.stringify(index);
  for (const privateField of ['sourceRunId', 'sourceSha256', 'release-sources', 'publicationTabs', 'rowFilters', 'resolvedOverview']) assert(!text.includes(privateField));
  assert.equal(index.filter(entry => entry.evidenceType === null).length, 2);
});
