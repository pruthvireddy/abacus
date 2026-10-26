import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { mkdir, mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import test from 'node:test';
import ts from 'typescript';
import { publishReport, validateReport, verifyPublications, sha256, REPORT_MAX_BYTES, FILTERED_REPORT_MAX_BYTES, FILTERED_BUNDLE_MAX_BYTES, FILTERED_DOWNLOAD_MAX_BYTES, FILTERED_TOTAL_DOWNLOAD_MAX_BYTES } from '../scripts/lib/publication.mjs';
import { validateCsv } from '../scripts/lib/evidence.mjs';

const example = JSON.parse(await readFile(new URL('../examples/report.json', import.meta.url), 'utf8'));
const filteredReport = () => ({ ...structuredClone(example), schemaVersion: '1.1', sections: [{ id: 'saved', kind: 'table', title: 'Saved groups', columns: [{ key: 'year', label: 'Year' }, { key: 'value', label: 'Saved value', format: 'number', precision: 0 }], rowFilters: [{ key: 'year', label: 'Year', defaultValue: 'All years' }], rows: Array.from({ length: 1080 }, (_, value) => ({ year: value < 15 ? 'All years' : '2020', value })) }] });

async function fixture(t) {
  const root = await mkdtemp(resolve(tmpdir(), 'narada-filtered-')); t.after(() => rm(root, { recursive: true, force: true }));
  const source = resolve(root, 'source'); await mkdir(source);
  const report = filteredReport(); const reportPath = resolve(source, 'publication.json');
  return { root, source, report, reportPath, outputRoot: resolve(root, 'publications') };
}

test('filtered tables require bounded declared columns, unique filters and existing exact defaults', () => {
  validateReport(filteredReport());
  for (const alter of [
    s => { delete s.rowFilters; }, s => { s.rows = Array.from({ length: 1501 }, () => s.rows[0]); },
    s => { s.rowFilters = []; }, s => { s.rowFilters[0].key = 'missing'; },
    s => { s.rowFilters.push(s.rowFilters[0]); }, s => { s.rowFilters[0].defaultValue = 'Unknown'; },
    s => { s.rowFilters[0].label = ' '; }, s => { s.rowFilters.push({ key: 'value', label: 'Value' }, { key: 'year', label: 'Third' }, { key: 'value', label: 'Fourth' }); },
  ]) {
    const report = filteredReport(); alter(report.sections[0]); assert.throws(() => validateReport(report));
  }
  const report = filteredReport(); report.sections[0].rows = Array.from({ length: 1500 }, () => ({ year: 'All years', value: 1 })); validateReport(report);
});

test('source budgets remain 96 KiB for ordinary reports and permit exact 2 MiB only with saved row filters', async t => {
  const f = await fixture(t);
  const text = JSON.stringify(f.report);
  await writeFile(f.reportPath, text + ' '.repeat(FILTERED_REPORT_MAX_BYTES - Buffer.byteLength(text)));
  assert.equal(FILTERED_REPORT_MAX_BYTES, 2 * 1024 * 1024);
  assert.equal(FILTERED_BUNDLE_MAX_BYTES, 4 * 1024 * 1024);
  assert.equal((await publishReport({ ...f, dryRun: true })).status, 'ready');
  await writeFile(f.reportPath, text + ' '.repeat(FILTERED_REPORT_MAX_BYTES + 1 - Buffer.byteLength(text)));
  await assert.rejects(publishReport({ ...f, dryRun: true }), /budget/);
  const ordinary = JSON.stringify(example);
  await writeFile(f.reportPath, ordinary + ' '.repeat(REPORT_MAX_BYTES + 1 - Buffer.byteLength(ordinary)));
  await assert.rejects(publishReport({ ...f, dryRun: true }), /Report source exceeds byte budget/);
});

test('filtered publications retain larger saved tables and immutable canonical identities', async t => {
  const f = await fixture(t);
  f.report.sections = Array.from({ length: 8 }, (_, table) => ({ id: `saved-${table}`, kind: 'table', title: 'Saved groups', columns: Array.from({ length: 12 }, (_, column) => ({ key: `c${column}`, label: `Saved ${column}` })), rowFilters: [{ key: 'c0', label: 'Group', defaultValue: 'all' }], rows: Array.from({ length: 1080 }, () => Object.fromEntries(Array.from({ length: 12 }, (_, column) => [`c${column}`, column ? 1 : 'all']))) }));
  await writeFile(f.reportPath, JSON.stringify(f.report));
  assert.equal((await publishReport(f)).status, 'published');
  const path = resolve(f.outputRoot, f.report.id, 'report.json'); const before = await readFile(path);
  assert(before.length > 192 * 1024 && before.length <= FILTERED_BUNDLE_MAX_BYTES);
  assert.equal((await publishReport(f)).status, 'unchanged'); assert.deepEqual(await readFile(path), before);
  assert.equal((await verifyPublications(f.outputRoot)).reports, 1);
  await writeFile(path, Buffer.concat([before, Buffer.alloc(FILTERED_BUNDLE_MAX_BYTES - before.length, 32)]));
  assert.equal((await verifyPublications(f.outputRoot)).reports, 1, 'Exact filtered bundle byte boundary is accepted.');
  await writeFile(path, Buffer.concat([before, Buffer.alloc(FILTERED_BUNDLE_MAX_BYTES + 1 - before.length, 32)]));
  await assert.rejects(verifyPublications(f.outputRoot), /budget/);
});

test('filtered selected CSVs allow 15000 saved rows while ordinary CSVs remain limited to 1000', async t => {
  const f = await fixture(t); await mkdir(resolve(f.source, 'downloads'));
  const bytes = Buffer.from(`value\n${Array.from({ length: 15000 }, () => 'a'.repeat(170)).join('\n')}\n`);
  const declaration = { id: 'saved', path: 'downloads/saved.csv', label: 'Saved groups', description: 'Explicit saved table rows.', population: 'Saved events', units: 'Saved units', scope: 'All saved groups', mediaType: 'text/csv', rowCount: 15000, columns: ['value'], sha256: sha256(bytes), source: { runId: f.report.source.runId, artifact: 'tables/saved.csv', sha256: 'a'.repeat(64) } };
  assert(bytes.length > 256 * 1024 && bytes.length < FILTERED_DOWNLOAD_MAX_BYTES);
  assert.equal(FILTERED_TOTAL_DOWNLOAD_MAX_BYTES, 8 * 1024 * 1024);
  f.report.downloads = [declaration]; await writeFile(resolve(f.source, declaration.path), bytes); await writeFile(f.reportPath, JSON.stringify(f.report));
  assert.equal((await publishReport(f)).status, 'published'); assert.equal((await verifyPublications(f.outputRoot)).downloads, 1);
  assert.equal(validateCsv(bytes, declaration, 15000).length, 15001);
  assert.throws(() => validateCsv(bytes, declaration), /1000 data rows/);
  const ordinary = { ...structuredClone(example), schemaVersion: '1.1', downloads: [declaration] }; assert.throws(() => validateReport(ordinary), /1000 data rows/);
  f.report.downloads = Array.from({ length: 4 }, (_, index) => ({ ...declaration, id: `saved-${index}`, path: `downloads/saved-${index}.csv` }));
  for (const download of f.report.downloads) await writeFile(resolve(f.source, download.path), bytes);
  f.report.id = 'large-filtered'; await writeFile(f.reportPath, JSON.stringify(f.report));
  await assert.rejects(publishReport({ ...f, dryRun: true }), /total download byte budget/);
  f.report.downloads = [declaration]; await writeFile(resolve(f.source, declaration.path), Buffer.alloc(FILTERED_DOWNLOAD_MAX_BYTES + 1)); await writeFile(f.reportPath, JSON.stringify(f.report));
  await assert.rejects(publishReport({ ...f, dryRun: true }), /budget/);
  const tooMany = filteredReport(); tooMany.downloads = [{ ...declaration, rowCount: 15001 }]; assert.throws(() => validateReport(tooMany));
});

test('compact filtered sources still refuse canonical bundle expansion above 4 MiB', async t => {
  const f = await fixture(t);
  f.report.sections = Array.from({ length: 16 }, (_, index) => ({ id: `saved-${index}`, kind: 'table', title: 'Saved groups', rowFilters: [{ key: 'a', label: 'Group', defaultValue: 1 }], columns: Array.from({ length: 12 }, (_, column) => ({ key: String.fromCharCode(97 + column), label: `Value ${column}` })), rows: Array.from({ length: 1500 }, () => Object.fromEntries(Array.from({ length: 12 }, (_, column) => [String.fromCharCode(97 + column), 1]))) }));
  const text = JSON.stringify(f.report); assert(Buffer.byteLength(text) < FILTERED_REPORT_MAX_BYTES);
  await writeFile(f.reportPath, text);
  await assert.rejects(publishReport({ ...f, dryRun: true }), /Publication bundle exceeds byte budget/);
});

// Execute the actual component and its handlers with a small hook lifecycle
// fixture. DOM/layout and hydration remain covered by browser verification.
const require = createRequire(import.meta.url);
function controlHarness(initialProps, loadSavedTables) {
  let slots = [], cursor = 0, effects = [], currentKey, epoch = 0, staleUpdates = 0;
  const hooks = {
    useState(initial) {
      const slot = slots[cursor++] ??= { value: typeof initial === 'function' ? initial() : initial };
      const mountedEpoch = epoch;
      return [slot.value, next => {
        if (mountedEpoch !== epoch) staleUpdates++;
        slot.value = typeof next === 'function' ? next(slot.value) : next;
      }];
    },
    useRef(initial) { return slots[cursor++] ??= { current: initial }; },
    useEffect(effect, dependencies) {
      const slot = slots[cursor++] ??= {};
      if (!slot.dependencies || dependencies.some((value, index) => value !== slot.dependencies[index])) {
        effects.push(() => { slot.cleanup?.(); slot.dependencies = dependencies; slot.cleanup = effect(); });
      }
    },
  };
  function compile(relativePath) {
    const source = readFileSync(new URL(relativePath, import.meta.url), 'utf8');
    const { outputText } = ts.transpileModule(source, { compilerOptions: {
      module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022,
    } });
    const compiled = { exports: {} };
    const resolveImport = id => id === 'react' ? hooks
      : id === '@/lib/saved-tables' ? { loadSavedTables }
        : id === '@/lib/format' ? compile('../src/lib/format.ts')
          : id === '@/lib/table-filters' ? compile('../src/lib/table-filters.ts')
            : id === './report-table' ? { ReportTable: 'report-table' } : require(id);
    new Function('require', 'module', 'exports', outputText)(resolveImport, compiled, compiled.exports);
    return compiled.exports;
  }
  const { FilteredReportTable } = compile('../src/components/filtered-report-table.tsx');
  const unmount = () => { for (const slot of slots) slot.cleanup?.(); slots = []; epoch++; };
  let props = initialProps;
  return {
    render(nextProps = props) {
      props = nextProps;
      const instance = FilteredReportTable(props);
      if (instance.key !== currentKey) { unmount(); currentKey = instance.key; }
      cursor = 0; effects = [];
      const table = instance.type(instance.props);
      for (const effect of effects) effect();
      return table;
    },
    unmount,
    get staleUpdates() { return staleUpdates; },
  };
}
function controls(table, type) {
  const found = [];
  function visit(node) {
    if (Array.isArray(node)) { node.forEach(visit); return; }
    if (!node || typeof node !== 'object') return;
    if (node.type === type) found.push(node);
    visit(node.props?.children);
  }
  visit(table.props.controls);
  return found;
}
const controlButton = (table, label) => controls(table, 'button').find(button => button.props.children === label);
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
function controlFixture() {
  const section = filteredReport().sections[0];
  section.rows = [{ year: 'All years', value: 0 }, { year: 'All years', value: null },
    ...Array.from({ length: 105 }, (_, value) => ({ year: 2020, value })),
    { year: '2020', value: 99 }, { year: null, value: null }, { year: false, value: 0 }];
  return { section, props: { initialSection: { ...section, rows: section.rows.slice(0, 2) }, reportId: 'saved-reader', totalSavedRows: section.rows.length } };
}

test('saved table controls wait for a reader action and preserve default rows throughout loading', async () => {
  const { section, props } = controlFixture();
  const request = deferred(); const calls = [];
  const harness = controlHarness(props, id => { calls.push(id); return request.promise; });
  let table = harness.render();
  assert.deepEqual(calls, [], 'Mount effects must not request publication JSON.');
  assert.deepEqual(table.props.rows, props.initialSection.rows);
  assert(controls(table, 'select').every(select => select.props.disabled));
  assert.equal(controls(table, 'noscript').length, 1);
  const load = controlButton(table, 'Load table filters').props.onClick;
  const pending = load(); await load();
  assert.deepEqual(calls, ['saved-reader'], 'Repeated clicks while pending share the active request.');
  table = harness.render();
  assert(controlButton(table, 'Loading table filters…').props.disabled);
  assert.deepEqual(table.props.rows, props.initialSection.rows);
  request.resolve([section]); await pending;
  table = harness.render();
  assert(!controlButton(table, 'Load table filters'));
  assert(controls(table, 'select').every(select => !select.props.disabled));
  assert.deepEqual(table.props.rows, props.initialSection.rows, 'Loading never changes the authored default selection.');
  harness.unmount();
});

test('reader loading failures retain exact defaults, expose a download fallback, and allow retry', async () => {
  const { section, props } = controlFixture(); let attempts = 0;
  const harness = controlHarness(props, async () => { if (++attempts === 1) throw new Error('Unavailable'); return [section]; });
  await controlButton(harness.render(), 'Load table filters').props.onClick();
  let table = harness.render();
  assert.deepEqual(table.props.rows, props.initialSection.rows);
  assert.equal(controls(table, 'p').find(node => node.props.role === 'alert')?.props.className, 'table-load-error');
  assert.equal(controls(table, 'a')[0].props.href, '/publications/saved-reader/report.json');
  await controlButton(table, 'Try again').props.onClick();
  table = harness.render();
  assert.equal(attempts, 2);
  assert.equal(controls(table, 'a').length, 0);
  assert(controls(table, 'select').every(select => !select.props.disabled));
  harness.unmount();
});

test('loaded selectors preserve typed saved values, nulls, row order and bounded pagination', async () => {
  const { section, props } = controlFixture();
  const harness = controlHarness(props, async () => [section]);
  await controlButton(harness.render(), 'Load table filters').props.onClick();
  let table = harness.render();
  const selectYear = value => { controls(table, 'select')[0].props.onChange({ target: { value } }); table = harness.render(); };
  selectYear('2020');
  assert.deepEqual(table.props.rows, section.rows.slice(2, 102));
  controlButton(table, 'Next rows').props.onClick(); table = harness.render();
  assert.deepEqual(table.props.rows, section.rows.slice(102, 107));
  selectYear('"2020"'); assert.deepEqual(table.props.rows, [{ year: '2020', value: 99 }]);
  selectYear('null'); assert.deepEqual(table.props.rows, [{ year: null, value: null }]);
  selectYear('false'); assert.deepEqual(table.props.rows, [{ year: false, value: 0 }]);
  controlButton(table, 'Reset selections').props.onClick(); table = harness.render();
  assert.deepEqual(table.props.rows, section.rows.slice(0, 100));
  assert.equal(controls(table, 'select')[0].props.value, '');
  harness.unmount();
});

test('late loads cannot update a different report or an unmounted table', async () => {
  const { section, props } = controlFixture();
  const request = deferred();
  const harness = controlHarness(props, () => request.promise);
  const pending = controlButton(harness.render(), 'Load table filters').props.onClick();
  let table = harness.render({ ...props, reportId: 'another-report' });
  assert(controlButton(table, 'Load table filters'));
  request.resolve([section]); await pending;
  table = harness.render();
  assert(controlButton(table, 'Load table filters'));
  assert(controls(table, 'select')[0].props.disabled);
  assert.equal(harness.staleUpdates, 0);
  const second = controlButton(table, 'Load table filters').props.onClick(); harness.unmount(); await second;
  assert.equal(harness.staleUpdates, 0);
});
