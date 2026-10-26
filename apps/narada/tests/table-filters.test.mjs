import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import ts from 'typescript';

const source = readFileSync(new URL('../src/lib/table-filters.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } });
const compiledModule = { exports: {} };
new Function('module', 'exports', outputText)(compiledModule, compiledModule.exports);
const { savedFilterOptions, savedDefaultSelections, selectSavedRows, initialSavedTable, TABLE_PAGE_ROWS } = compiledModule.exports;

test('saved row selection preserves order, nulls, zeros and typed values without aggregation', () => {
  const rows = [{ key: 0, scope: 'A', rate: null }, { key: '0', scope: 'A', rate: 0 }, { key: false, scope: 'A', rate: .5 }, { key: null, scope: 'B', rate: 1 }, { scope: 'B' }];
  const section = { rows, rowFilters: [{ key: 'key', label: 'Key', defaultValue: 0 }] };
  assert.deepEqual(savedDefaultSelections(section), { key: '0' });
  assert.deepEqual(selectSavedRows(rows, { key: '0' }), [rows[0]]);
  assert.deepEqual(selectSavedRows(rows, { key: '"0"' }), [rows[1]]);
  assert.deepEqual(selectSavedRows(rows, { key: 'false' }), [rows[2]]);
  assert.deepEqual(selectSavedRows(rows, { key: 'null', scope: '"B"' }), rows.slice(3));
  assert.deepEqual(selectSavedRows(rows, { key: '' }), rows);
  assert.deepEqual(savedFilterOptions(section, 'key').map(option => option.value), ['0', '"0"', 'false', 'null']);
  assert.deepEqual(savedFilterOptions({ rows: [{}] }, 'constructor'), [{ value: 'null', label: null }]);
  assert.deepEqual(selectSavedRows([{}], { constructor: 'null' }), [{}]);
});

test('initial saved table uses only declared defaults and never exceeds one 100-row page', () => {
  const section = { rows: Array.from({ length: 1080 }, (_, value) => ({ year: value < 15 ? 'All years' : '2020', window: 'All hours', value })), rowFilters: [{ key: 'year', label: 'Year', defaultValue: 'All years' }, { key: 'window', label: 'Window', defaultValue: 'All hours' }] };
  assert.equal(TABLE_PAGE_ROWS, 100);
  const initial = initialSavedTable(section);
  assert.equal(initial.rows.length, 15);
  assert.equal(initial.rows[14].value, 14);
  assert.equal(section.rows.length, 1080);
  assert.equal(initialSavedTable({ ...section, rowFilters: [{ key: 'year', label: 'Year' }] }).rows.length, 100);
});
