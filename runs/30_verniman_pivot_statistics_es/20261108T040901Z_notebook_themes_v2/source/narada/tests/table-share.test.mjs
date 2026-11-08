import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const require = createRequire(import.meta.url);
function compile(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022, esModuleInterop: true,
  } });
  const compiled = { exports: {} };
  const resolve = id => ['@/lib/table-filters', './table-filters'].includes(id) ? compile('../src/lib/table-filters.ts')
    : id === '@/lib/table-share' ? compile('../src/lib/table-share.ts')
      : id === '@/lib/saved-tables' ? compile('../src/lib/saved-tables.ts')
        : id === '@/lib/format' ? compile('../src/lib/format.ts')
          : id === './report-table' ? compile('../src/components/report-table.tsx') : require(id);
  new Function('require', 'module', 'exports', outputText)(resolve, compiled, compiled.exports);
  return compiled.exports;
}
const { parseTableSelection, applyTableSelection, tableSelectionHref, TABLE_SHARE_MAX_QUERY, TABLE_SHARE_MAX_JSON } = compile('../src/lib/table-share.ts');
const { selectSavedRows } = compile('../src/lib/table-filters.ts');
const fixture = () => ({ id: 'saved-population', kind: 'table', title: 'Separate saved populations', columns: [
  { key: 'value', label: 'Saved key' }, { key: 'scope', label: 'Scope' }, { key: 'rate', label: 'Saved rate', format: 'percent', precision: 1 },
], rowFilters: [{ key: 'value', label: 'Saved key', defaultValue: '0' }, { key: 'scope', label: 'Scope', defaultValue: 'A' }], rows: [
  { value: 0, scope: 'A', rate: 0 }, { value: '0', scope: 'A', rate: null },
  { value: false, scope: 'B', rate: .5 }, { value: null, scope: 'B', rate: 1 },
] });
const searchFor = (table, filters) => `?${new URLSearchParams({ table, filters: JSON.stringify(filters) })}`;

test('table links identify report and table and round-trip typed selections and explicit All', () => {
  const section = fixture();
  for (const value of ['0', '"0"', 'false', 'null', '']) {
    const selections = { value, scope: '' };
    const href = tableSelectionHref('saved-report', section, selections);
    assert(href.startsWith('/reports/saved-report/?table=saved-population&'));
    assert(href.endsWith('#section-saved-population'));
    const pending = parseTableSelection(new URL(href, 'https://example.test').search, 'saved-report', section);
    assert.equal(pending.status, 'pending');
    const result = applyTableSelection(section, pending);
    assert.deepEqual(result.selections, selections);
    assert.equal(result.ignored, false);
    const rows = selectSavedRows(section.rows, result.selections);
    assert.deepEqual(rows, value === '' ? section.rows : [section.rows[['0', '"0"', 'false', 'null'].indexOf(value)]]);
  }
  const defaults = parseTableSelection(searchFor(section.id, {}), 'saved-report', section);
  assert.deepEqual(applyTableSelection(section, defaults).selections, { value: '"0"', scope: '"A"' }, 'Missing keys retain authored defaults; explicit All overrides them.');
});

test('stale selections retain defaults while valid saved values and empty selections survive', () => {
  const section = fixture();
  const pending = parseTableSelection(searchFor(section.id, { value: '"removed"', scope: '"B"', obsolete: '0' }), 'saved-report', section);
  assert.equal(pending.status, 'pending');
  const result = applyTableSelection(section, pending);
  assert.deepEqual(result.selections, { value: '"0"', scope: '"B"' });
  assert.equal(result.ignored, true);
  assert.deepEqual(section.rows, fixture().rows);
});

test('malformed, ambiguous, unsafe and oversized parameters fail closed', () => {
  const section = fixture();
  assert.deepEqual(parseTableSelection('', 'saved-report', section), { status: 'none' });
  assert.deepEqual(parseTableSelection(searchFor('another-table', {}), 'saved-report', section), { status: 'none' });
  for (const search of [
    '?table=saved-population', searchFor(section.id, {}) + '&table=saved-population',
    searchFor(section.id, {}) + '&filters=%7B%7D', '?table=saved-population&filters=broken',
    searchFor(section.id, []), searchFor(section.id, null), searchFor(section.id, { a: '', b: '', c: '', d: '' }),
    searchFor(section.id, { value: '"x"'.repeat(TABLE_SHARE_MAX_JSON) }),
    '?table=saved-population&filters=' + 'x'.repeat(TABLE_SHARE_MAX_QUERY),
  ]) assert.equal(parseTableSelection(search, 'saved-report', section).status, 'invalid');
  for (const unsafe of ['{}', '[]', 'NaN', 'null ', '1e3', 'undefined']) {
    const parsed = parseTableSelection(searchFor(section.id, { value: unsafe }), 'saved-report', section);
    assert.equal(parsed.status, 'pending'); assert.deepEqual(parsed.selections, {}); assert.equal(parsed.ignored, true);
  }
  assert.equal(tableSelectionHref('../private', section, {}), null);
  assert.equal(parseTableSelection(searchFor(section.id, {}), '../private', section).status, 'invalid');
  assert.equal(tableSelectionHref('saved-report', section, { value: '[]' }), null);
  assert.equal(tableSelectionHref('saved-report', section, { value: '"not saved"' }), null);
  assert.equal(tableSelectionHref('saved-report', section, { value: JSON.stringify('x'.repeat(TABLE_SHARE_MAX_JSON)) }), null);
});

test('pending links do not fetch; explicit shared loading retries and restores exact saved rows', async t => {
  const section = fixture();
  const prior = globalThis.fetch; t.after(() => { globalThis.fetch = prior; }); let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return new Response(JSON.stringify({ report: { id: 'saved-report', sections: [section] } }), { status: calls === 1 ? 503 : 200 });
  };
  const pending = parseTableSelection(searchFor(section.id, { value: '0', scope: '' }), 'saved-report', section);
  assert.equal(calls, 0); assert.deepEqual(section.rows, fixture().rows);
  const { loadSavedTables } = compile('../src/lib/saved-tables.ts');
  await assert.rejects(loadSavedTables('saved-report'), /unavailable/);
  const [tables, sharedTables] = await Promise.all([loadSavedTables('saved-report'), loadSavedTables('saved-report')]);
  assert.equal(calls, 2); assert.equal(tables, sharedTables);
  const restored = applyTableSelection(tables[0], pending);
  assert.deepEqual(selectSavedRows(tables[0].rows, restored.selections), [{ value: 0, scope: 'A', rate: 0 }]);
});

test('server rendering retains default rows and a truthful print slice without fetching or applying links', () => {
  const { FilteredReportTable } = compile('../src/components/filtered-report-table.tsx');
  const rows = Array.from({ length: 150 }, (_, index) => ({ value: index < 12 ? '0' : 0, scope: 'A', rate: index === 0 ? null : 0 }));
  const section = { ...fixture(), rows: rows.slice(0, 12) };
  const html = renderToStaticMarkup(React.createElement(FilteredReportTable, { initialSection: section, reportId: 'saved-report', totalSavedRows: 150 }));
  assert.equal((html.match(/<tbody>.*?<\/tbody>/s)?.[0].match(/<tr>/g) ?? []).length, 12);
  assert.match(html, /class="table-caption">Separate saved populations/);
  assert.match(html, /Displayed authored default slice: 12 rows; 150 saved rows/);
  assert.match(html, /Other saved rows have not been loaded/);
  assert.match(html, /Saved key: 0; Scope: A/);
  assert.match(html, /not the complete research dataset/);
  assert.match(html, /Report saved-report; table saved-population/);
  assert.match(html, /href="\/reports\/saved-report\/#section-saved-population"/);
  assert.match(html, /Load table filters/); assert.match(html, /<noscript>/);
  assert(!html.includes('selected rows link')); assert(!html.includes('A linked selection is waiting'));
  assert.match(html, /Not available/); assert.match(html, /0\.0%/);
});
