import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

// Compile the actual server component for Node's test runner (which cannot parse
// TSX). This adds no build output or fixture to Narada's public directory.
const require = createRequire(import.meta.url);
function compile(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022,
    esModuleInterop: true,
  } });
  const module = { exports: {} };
  const resolve = id => id === '@/lib/format' ? compile('../src/lib/format.ts') : id === '@/components/publication-evidence' ? compile('../src/components/publication-evidence.tsx') : require(id);
  new Function('require', 'module', 'exports', outputText)(resolve, module, module.exports);
  return module.exports;
}
const { ReportSections } = compile('../src/components/report-sections.tsx');

test('table scroll region describes keyboard access while preserving scalar meanings and escaping text', () => {
  const section = { id: 'evidence', kind: 'table', title: 'Selected evidence', columns: [
    { key: 'label', label: 'Long source label' },
    { key: 'rate', label: 'Rate', format: 'percent', precision: 1 },
    { key: 'delta', label: 'Difference', format: 'number', precision: 2, unit: 'pp' },
    { key: 'status', label: 'Status' },
  ], rows: [
    { label: '<script>untrusted</script>', rate: 0, delta: -1.374, status: false },
    { label: 'Unevaluable', rate: null, delta: null },
  ] };
  const html = renderToStaticMarkup(React.createElement(ReportSections, { sections: [section], reportId: 'test-only' }));
  assert.match(html, /id="table-help-evidence"/);
  assert.match(html, /aria-describedby="table-help-evidence" tabindex="0"/);
  assert.match(html, /left and right arrow keys/);
  assert.match(html, /Missing or blank cells display as Not available/);
  assert.match(html, /<caption class="visually-hidden">Selected evidence<\/caption>/);
  assert.match(html, />0\.0%<\/td>/);
  assert.match(html, />-1\.37<\/td>/);
  assert.match(html, /class="column-unit">pp<\/span>/);
  assert.match(html, />false<\/td>/);
  assert.equal((html.match(/>Not available<\/td>/g) ?? []).length, 3);
  assert.match(html, /&lt;script&gt;untrusted&lt;\/script&gt;/);
  assert(!html.includes('<script>'));
});

test('table context remains visible, accessible and linked to an attributed reference', () => {
  const section = { id: 'context', kind: 'table', title: 'Different horizons', description: 'Each horizon has its own complete-path denominator.', notes: ['Bounds are pointwise; not a profitability result.'], referenceIds: ['saved-summary'], columns: [{ key: 'n', label: 'Eligible events', format: 'number', precision: 0 }], rows: [{ n: 3 }] };
  const html = renderToStaticMarkup(React.createElement(ReportSections, { sections: [section], reportId: 'test-only', references: [{ id: 'saved-summary', label: 'Executed summary table' }] }));
  assert.match(html, /Executed summary table/);
  assert.match(html, /id="table-context-context"/);
  assert.match(html, /aria-describedby="table-help-context table-context-context table-notes-context"/);
  assert.match(html, /Bounds are pointwise/);
  assert.match(html, /href="#reference-saved-summary"/);
});

test('selected downloads and references render safe links, visible scope and useful filenames', () => {
  const { PublicationEvidence } = compile('../src/components/publication-evidence.tsx');
  const hash = 'a'.repeat(64);
  const report = { id: 'test-only', downloads: [{ id: 'sample', path: 'downloads/selected.csv', label: 'Saved rates', description: 'Selected summary rows', population: 'Two separate cohorts', units: 'Rates as ratios', scope: 'No pooling', mediaType: 'text/csv', sha256: hash, rowCount: 2, columns: ['rate'], source: { runId: 'saved-run', artifact: 'tables/summary.csv', sha256: hash } }], references: [{ id: 'lesson', kind: 'external', label: '<Lesson>', title: 'A saved source', creator: 'Author', url: 'https://example.org/watch?t=60', startSeconds: 60, endSeconds: 120 }] };
  const html = renderToStaticMarkup(React.createElement(PublicationEvidence, { report }));
  assert.match(html, /download="selected.csv"/);
  assert.match(html, /href="\/publications\/test-only\/downloads\/selected.csv"/);
  assert.match(html, /Two separate cohorts/);
  assert.match(html, /Rates as ratios/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.match(html, /Media 1:00–2:00/);
  assert.match(html, /&lt;Lesson&gt;/);
});


test('figures retain alternative text and caption with a visible full-size link', () => {
  const section = { id: 'saved-chart', kind: 'figure', title: 'Saved path', path: 'figures/path.png', alt: 'A saved path with an unresolved barrier order.', caption: 'Illustration only; no assumed fill.' };
  const html = renderToStaticMarkup(React.createElement(ReportSections, { sections: [section], reportId: 'test-only' }));
  assert.match(html, /alt="A saved path with an unresolved barrier order\."/);
  assert.match(html, /href="\/publications\/test-only\/figures\/path\.png"/);
  assert.match(html, /Illustration only; no assumed fill/);
  assert.match(html, /View full-size figure<\/a>/);
});
