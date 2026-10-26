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
  const resolve = id => id === '@/lib/format' ? compile('../src/lib/format.ts') : require(id);
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
  assert.match(html, /<caption class="visually-hidden">Selected evidence<\/caption>/);
  assert.match(html, />0\.0%<\/td>/);
  assert.match(html, />-1\.37<\/td>/);
  assert.match(html, /class="column-unit">pp<\/span>/);
  assert.match(html, />false<\/td>/);
  assert.equal((html.match(/Not available/g) ?? []).length, 3);
  assert.match(html, /&lt;script&gt;untrusted&lt;\/script&gt;/);
  assert(!html.includes('<script>'));
});
