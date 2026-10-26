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
  const compiledModule = { exports: {} };
  const resolve = id => id === '@/lib/format' ? compile('../src/lib/format.ts')
    : id === '@/lib/table-filters' ? compile('../src/lib/table-filters.ts')
      : id === '@/lib/saved-tables' ? compile('../src/lib/saved-tables.ts')
        : id === './report-table' ? compile('../src/components/report-table.tsx')
          : id === './filtered-report-table' ? compile('../src/components/filtered-report-table.tsx')
            : id === './pattern-panel' ? compile('../src/components/pattern-panel.tsx')
    : id === '../../scripts/lib/study-selections.mjs' ? require('../scripts/lib/study-selections.mjs')
    : ['@/components/publication-evidence', './publication-evidence'].includes(id) ? compile('../src/components/publication-evidence.tsx')
      : id === './report-sections' ? compile('../src/components/report-sections.tsx') : require(id);
  new Function('require', 'module', 'exports', outputText)(resolve, compiledModule, compiledModule.exports);
  return compiledModule.exports;
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

test('publication tabs use ordinary accessible links with exactly one current chart', () => {
  const { PublicationTabs } = compile('../src/components/publication-tabs.tsx');
  const tabs = [
    { publicationId: 'chart-a', sourceRunId: 'saved-run', label: 'Chart A' },
    { publicationId: 'chart-b', sourceRunId: 'saved-run', label: 'Chart B' },
    { publicationId: 'chart-c', sourceRunId: 'saved-run', label: 'Chart <C>' },
  ];
  const html = renderToStaticMarkup(React.createElement(PublicationTabs, { tabs, currentPublicationId: 'chart-b' }));
  assert.match(html, /<nav[^>]+aria-label="Study chart navigation"/);
  assert.match(html, /href="\/reports\/chart-b\/" aria-current="page"/);
  assert.equal((html.match(/aria-current="page"/g) ?? []).length, 1);
  assert.equal((html.match(/<a /g) ?? []).length, 3);
  assert.match(html, /Chart &lt;C&gt;/);
  assert(!html.includes('role="tab"'), 'Route links use native navigation semantics.');
});

test('shared publication content renders saved values once with downloads and provenance', () => {
  const { PublicationContent } = compile('../src/components/publication-content.tsx');
  const publication = { report: { id: 'saved-report', source: { producer: 'sahadeva', runId: 'saved-run' },
    sections: [{ id: 'overall', kind: 'metrics', title: 'Overall', items: [{ label: 'Saved length', value: 12.5, format: 'number', precision: 1, unit: 'candles' }] }],
    notes: ['Saved interpretation.'] }, provenance: { sourceSha256: 'a'.repeat(64), assets: [] } };
  const html = renderToStaticMarkup(React.createElement(PublicationContent, { publication }));
  assert.match(html, /href="#section-overall"/);
  assert.equal((html.match(/Saved length/g) ?? []).length, 1);
  assert.match(html, />12\.5/);
  assert.match(html, /href="\/publications\/saved-report\/report.json"/);
  assert.match(html, /<code>saved-run<\/code>/);
  assert.match(html, /Saved interpretation/);
});

test('analysis links retain a corresponding chart and keep every immutable report reachable', () => {
  const { StudyAnalysisNavigation, StudyAnalysisDirectory } = compile('../src/components/study-analyses.tsx');
  const analyses = [{ id: 'first', label: 'First analysis', publicationTabs: [{ publicationId: 'first-a', label: 'Chart A' }, { publicationId: 'first-b', label: 'Chart B' }] },
    { id: 'second', label: 'Second <analysis>', publicationTabs: [{ publicationId: 'second-a', label: 'Chart A' }, { publicationId: 'second-b', label: 'Chart B' }] }];
  const nav = renderToStaticMarkup(React.createElement(StudyAnalysisNavigation, { analyses, currentAnalysisId: 'first', currentChartLabel: 'Chart B' }));
  assert.match(nav, /aria-label="Study analysis navigation"/);
  assert.match(nav, /href="\/reports\/first-b\/" aria-current="page"/);
  assert.match(nav, /href="\/reports\/second-b\/"/);
  assert.match(nav, /Second &lt;analysis&gt;/);
  assert.equal((nav.match(/aria-current="page"/g) ?? []).length, 1);
  const directory = renderToStaticMarkup(React.createElement(StudyAnalysisDirectory, { analyses }));
  for (const id of ['first-a', 'first-b', 'second-a', 'second-b']) assert(directory.includes(`/reports/${id}/`));
});
test('analysis navigation falls back to the single saved baseline while retaining later-run report choices', () => {
  const { StudyAnalysisNavigation, StudyAnalysisDirectory } = compile('../src/components/study-analyses.tsx');
  const analyses = [
    { id: 'later', label: 'Later conditions', publicationTabs: [{ publicationId: 'later-summary', label: 'Summary' }, { publicationId: 'later-year', label: 'Year-wise' }] },
    { id: 'baseline', label: 'Saved baseline', publicationTabs: [{ publicationId: 'retained-baseline', label: 'Baseline' }] },
  ];
  const nav = renderToStaticMarkup(React.createElement(StudyAnalysisNavigation, { analyses, currentAnalysisId: 'later', currentChartLabel: 'Year-wise' }));
  assert.match(nav, /href="\/reports\/later-year\/" aria-current="page"/);
  assert.match(nav, /href="\/reports\/retained-baseline\/"/);
  assert.equal((nav.match(/aria-current="page"/g) ?? []).length, 1);
  const directory = renderToStaticMarkup(React.createElement(StudyAnalysisDirectory, { analyses }));
  for (const id of ['later-summary', 'later-year', 'retained-baseline']) assert(directory.includes(`/reports/${id}/`));
});

test('phase links preserve a declared condition and view with accessible native fallback links', () => {
  const { StudyPhaseNavigation, StudyPhaseDirectory, StudyAnalysisNavigation } = compile('../src/components/study-analyses.tsx');
  const families = [
    { id: 'earlier', label: 'Phase 1 and 2', analyses: [
      { id: 'baseline', label: 'Baseline', publicationTabs: [{ publicationId: 'original-parent', label: 'Summary' }] },
      { id: 'context', label: 'Earlier context', publicationTabs: [{ publicationId: 'earlier-summary', label: 'Summary' }, { publicationId: 'earlier-year', label: 'Year-wise' }] },
    ] },
    { id: 'later', label: 'EMA <cloud>', analyses: [
      { id: 'context', label: 'Trend context', publicationTabs: [{ publicationId: 'later-summary', label: 'Summary' }, { publicationId: 'later-year', label: 'Year-wise' }] },
      { id: 'risk', label: 'Methods and risk', publicationTabs: [{ publicationId: 'risk-summary', label: 'Summary' }] },
    ] },
  ];
  const phase = renderToStaticMarkup(React.createElement(StudyPhaseNavigation, { families, currentFamilyId: 'later', currentAnalysisId: 'context', currentChartLabel: 'Year-wise' }));
  assert.match(phase, /aria-label="Study phase navigation"/);
  assert.match(phase, /href="\/reports\/earlier-year\/"/);
  assert.match(phase, /href="\/reports\/later-year\/" aria-current="page"/);
  assert.equal((phase.match(/aria-current="page"/g) ?? []).length, 1);
  assert.match(phase, /EMA &lt;cloud&gt;/);
  assert(!phase.includes('role="tab"'));
  const fallback = renderToStaticMarkup(React.createElement(StudyPhaseNavigation, { families, currentFamilyId: 'later', currentAnalysisId: 'risk', currentChartLabel: 'Sessions' }));
  assert.match(fallback, /href="\/reports\/original-parent\/"/);
  assert.match(fallback, /href="\/reports\/risk-summary\/" aria-current="page"/);
  const conditions = renderToStaticMarkup(React.createElement(StudyAnalysisNavigation, { analyses: families[1].analyses, currentAnalysisId: 'context', currentChartLabel: 'Year-wise', asConditions: true }));
  assert.match(conditions, /CHOOSE A CONDITION/);
  assert.match(conditions, /href="\/reports\/later-year\/" aria-current="page"/);
  assert(!conditions.includes('/reports/earlier-year/'));
  const directory = renderToStaticMarkup(React.createElement(StudyPhaseDirectory, { families }));
  assert.match(directory, /<details class="analysis-directory phase-directory">/);
  assert.match(directory, /Browse every phase, condition and chart/);
  for (const id of ['original-parent', 'earlier-summary', 'earlier-year', 'later-summary', 'later-year', 'risk-summary']) assert(directory.includes(`/reports/${id}/`));
});

test('phase, condition and chart styles permit long labels to wrap within the viewport', () => {
  const css = readFileSync(new URL('../src/app/globals.css', import.meta.url), 'utf8');
  for (const selector of ['.study-phases ul', '.study-analyses ul', '.publication-tabs ul']) {
    const rules = css.slice(css.indexOf(selector));
    assert.match(rules.slice(0, rules.indexOf('}')), /flex-wrap: wrap/);
  }
  for (const selector of ['.study-phases li', '.study-analyses li', '.publication-tabs li']) {
    const rules = css.slice(css.indexOf(selector));
    assert.match(rules.slice(0, rules.indexOf('}')), /min-width: 0/);
    assert.match(rules.slice(0, rules.indexOf('}')), /max-width: 100%/);
  }
  for (const selector of ['.study-phases a', '.study-analyses a', '.publication-tabs a']) {
    const rules = css.slice(css.indexOf(selector));
    assert.match(rules.slice(0, rules.indexOf('}')), /overflow-wrap: anywhere/);
  }
  assert.match(css, /\.study-phases a\[aria-current="page"\]/);
  assert.match(css, /@media print \{ \.study-phases,/);
});

test('filtered tables render a bounded authored default without sending all rows to the client', () => {
  const rows = Array.from({ length: 1080 }, (_, index) => ({ year: index < 15 ? 'All years' : '2020', window: 'All hours', prior: index % 15, value: index }));
  const section = { id: 'large', kind: 'table', title: 'Saved groups', rowFilters: [{ key: 'year', label: 'Year', defaultValue: 'All years' }, { key: 'window', label: 'Window', defaultValue: 'All hours' }, { key: 'prior', label: 'Preceding leg' }], columns: [{ key: 'year', label: 'Year' }, { key: 'window', label: 'Window' }, { key: 'prior', label: 'Preceding leg' }, { key: 'value', label: 'Saved value', format: 'number', precision: 0 }], rows };
  const html = renderToStaticMarkup(React.createElement(ReportSections, { sections: [section], reportId: 'saved-only' }));
  assert.equal((html.match(/<tbody>.*?<\/tbody>/gs)[0].match(/<tr>/g) ?? []).length, 15);
  assert.match(html, /Showing 15 saved rows/);
  assert.match(html, /Load table filters/);
  assert(!html.includes('Loading all selections'), 'Initial rendering does not start a data download.');
  assert.match(html, /<noscript>/);
  assert.match(html, /id="filter-large-year" disabled=""/);
  assert(!html.includes('>1079<'), 'Default markup excludes unrelated saved rows.');
});

const pattern = { id: 'example', title: 'Reversal continuation', description: 'Count the candles after the signal.', variants: [{ id: 'up', title: 'Bullish example', description: 'R is the signal; F1 is measured.', candles: [
  { id: 'prior', label: 'P', open: 60, high: 65, low: 35, close: 40, role: 'context' },
  { id: 'signal', label: 'R', open: 40, high: 70, low: 35, close: 65, role: 'signal' },
  { id: 'follow', label: 'F1', open: 65, high: 90, low: 50, close: 85, role: 'measured' },
], marks: [{ kind: 'span', startCandle: 'follow', endCandle: 'follow', label: 'Following candles exclude R' }, { kind: 'level', startCandle: 'signal', endCandle: 'follow', price: 65, label: 'Signal close' }, { kind: 'band', startCandle: 'signal', endCandle: 'follow', low: 40, high: 65, label: 'Signal body' }] }] };

test('section schematics explain the measured part before saved statistics with unique accessible SVG IDs', () => {
  const section = { id: 'followups', kind: 'table', title: 'Following candles', patternId: 'example', patternFocus: 'Probability of at least n candles after R.', columns: [{ key: 'rate', label: 'Saved rate', format: 'percent' }], rows: [{ rate: .5 }] };
  const html = renderToStaticMarkup(React.createElement(ReportSections, { sections: [section, { ...section, id: 'followups-second' }], reportId: 'test-only', patterns: [pattern] }));
  assert.equal((html.match(/class="pattern-panel(?: pattern-compact)?"/g) ?? []).length, 2);
  assert.match(html, /Illustrative schematic/);
  assert.match(html, /This section measures:/);
  assert.match(html, /Probability of at least n candles after R/);
  assert.match(html, /role="img" aria-labelledby="pattern-section-followups-up-title pattern-section-followups-up-description"/);
  assert.match(html, /id="pattern-section-followups-second-up-title"/);
  assert.match(html, /R: Signal, rising candle/);
  assert.match(html, /F1: Measured, rising candle/);
  assert.match(html, /Following candles exclude R/);
  assert.match(html, /Signal body/);
  assert(html.indexOf('This section measures:') < html.indexOf('<table'));
  assert.equal((html.match(/>50\.00%<\/td>/g) ?? []).length, 2);
});

test('only an explicit overview is rendered at the top and diagram text is escaped', () => {
  const { PublicationContent } = compile('../src/components/publication-content.tsx');
  const unsafe = structuredClone(pattern);
  unsafe.title = '<script>unsafe</script>';
  unsafe.variants[0].candles[0].label = '<path/>';
  const publication = { report: { id: 'illustration', source: { producer: 'sahadeva', runId: 'saved-run' }, sections: [{ id: 'summary', kind: 'text', title: 'Summary', body: 'Saved content.' }], patterns: [unsafe], patternOverviewId: 'example' }, provenance: { sourceSha256: 'a'.repeat(64), assets: [] } };
  const html = renderToStaticMarkup(React.createElement(PublicationContent, { publication }));
  assert.equal((html.match(/class="pattern-panel pattern-overview"/g) ?? []).length, 1);
  assert.match(html, /&lt;script&gt;unsafe&lt;\/script&gt;/);
  assert.match(html, /&lt;path\/&gt;/);
  assert(!html.includes('<script>unsafe'));
  delete publication.report.patternOverviewId;
  const noOverview = renderToStaticMarkup(React.createElement(PublicationContent, { publication }));
  assert(!noOverview.includes('class="pattern-panel'));
});

test('coincident price levels have separate callouts and body bands use the other side', () => {
  const { PatternPanel } = compile('../src/components/pattern-panel.tsx');
  const sample = structuredClone(pattern);
  sample.variants[0].marks = [{ kind: 'band', startCandle: 'signal', endCandle: 'follow', low: 40, high: 70, label: 'Body band' }, { kind: 'level', startCandle: 'signal', endCandle: 'follow', price: 55, label: 'Half body' }, { kind: 'level', startCandle: 'signal', endCandle: 'follow', price: 55, label: 'Reference at same price' }];
  const html = renderToStaticMarkup(React.createElement(PatternPanel, { pattern: sample, instanceId: 'callouts' }));
  const matches = [...html.matchAll(/<text x="505" y="([\d.]+)">\d<\/text>/g)];
  assert.equal(matches.length, 2);
  assert.equal(Math.abs(Number(matches[1][1]) - Number(matches[0][1])), 18);
  assert.match(html, /pattern-level-leader/);
  assert(!html.includes('<text x="505" y="105.25">1</text>'), 'Band callout is placed at the left of its band.');
});

test('repeated panels share one SVG geometry definition and retain unique accessible instances', () => {
  const { PublicationContent } = compile('../src/components/publication-content.tsx');
  const section = { id: 'one', kind: 'table', title: 'Saved statistics', patternId: 'example', patternFocus: 'The measured candles.', columns: [{ key: 'n', label: 'Count' }], rows: [{ n: 2 }] };
  const publication = { report: { id: 'shared-geometry', source: { producer: 'sahadeva', runId: 'saved-run' }, patterns: [pattern], patternOverviewId: 'example', sections: [section, { ...section, id: 'two' }] }, provenance: { sourceSha256: 'a'.repeat(64), assets: [] } };
  const html = renderToStaticMarkup(React.createElement(PublicationContent, { publication }));
  const symbols = [...html.matchAll(/<symbol id="([^"]+)"/g)].map(match => match[1]);
  const uses = [...html.matchAll(/<use href="#([^"]+)"/g)].map(match => match[1]);
  assert.equal(symbols.length, 1);
  assert.equal(uses.length, 3);
  assert(uses.every(id => symbols.includes(id)), 'Every referenced variant has a local definition.');
  assert.equal((html.match(/class="pattern-wick"/g) ?? []).length, 3, 'Candle geometry appears once rather than once per panel.');
  assert.equal((html.match(/This section measures:/g) ?? []).length, 2);
  assert.equal((html.match(/id="pattern-key-example"/g) ?? []).length, 1);
  assert.equal((html.match(/class="pattern-mark-key"/g) ?? []).length, 1, 'Full numeral key is retained once for the shared pattern.');
  assert.equal((html.match(/class="pattern-key-link" href="#pattern-key-example"/g) ?? []).length, 2);
  assert.equal((html.match(/aria-describedby="pattern-key-example-up-key"/g) ?? []).length, 2);
  assert.match(html, /id="pattern-key-example-up-key"/);
  const ids = [...html.matchAll(/ id="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length, 'Instance titles/descriptions and symbol IDs stay unique.');
  const coordinates = [...html.matchAll(/\b(?:x|y|x1|x2|y1|y2|width|height)="(-?\d+(?:\.\d+)?)"/g)].map(match => match[1]);
  assert(coordinates.every(value => !value.includes('.') || value.split('.')[1].length <= 2), 'SVG coordinates have at most two decimal places.');
  assert(!/\d+\.\d{3,}/.test(html.match(/<defs>.*?<\/defs>/s)?.[0] ?? ''), 'Path coordinates share the same precision bound.');
});

test('body and risk band labels stay in the margin above candle painting with separate callouts', () => {
  const { PatternPanel } = compile('../src/components/pattern-panel.tsx');
  const sample = structuredClone(pattern);
  sample.variants[0].marks = [{ kind: 'band', startCandle: 'signal', endCandle: 'follow', low: 40, high: 70, label: 'Body' }, { kind: 'band', startCandle: 'follow', endCandle: 'follow', low: 45, high: 65, label: 'Risk' }];
  const html = renderToStaticMarkup(React.createElement(PatternPanel, { pattern: sample, instanceId: 'band-callouts', focus: 'This section measures the separate target scenario.' }));
  const numbers = [...html.matchAll(/<g class="pattern-band-callout"><text x="16" y="([\d.]+)">\d<\/text>/g)];
  assert.equal(numbers.length, 2);
  assert.equal(Math.abs(Number(numbers[1][1]) - Number(numbers[0][1])), 18);
  assert(html.indexOf('class="pattern-band-callout"') > html.lastIndexOf('class="pattern-candle-label"'), 'Number labels paint after candle bodies.');
  assert.match(html, /pattern-band-leader/);
  assert.match(html, /<strong>This section measures:<\/strong> the separate target scenario\./);
  assert(!html.includes('This section measures: This section measures'));
});

test('RXV-style candles stay slim, centred and tall while all explicit price marks remain visible', () => {
  const { PatternPanel } = compile('../src/components/pattern-panel.tsx');
  const sample = { id: 'slim', title: 'RXV-style illustration', description: 'Illustrative values only.', variants: [{ id: 'up', title: 'Bullish', description: 'Slim solid candles.', candles: [
    { id: 'doji', label: 'Doji', open: 45, high: 46, low: 44, close: 45, role: 'context' },
    { id: 'r', label: 'R', open: 45, high: 60, low: 40, close: 55, role: 'signal' },
    { id: 'f1', label: 'F1', open: 55, high: 60, low: 53, close: 59, role: 'measured' },
  ], marks: [] }] };
  const render = () => renderToStaticMarkup(React.createElement(PatternPanel, { pattern: sample, instanceId: 'rxv-shape' }));
  const candleRects = html => [...html.matchAll(/<rect class="pattern-body" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"/g)];
  const original = render();
  const bodies = candleRects(original);
  assert.equal(bodies.length, 3);
  assert(bodies.every(rect => Number(rect[3]) === 12));
  assert.equal(Number(bodies[1][1]) - Number(bodies[0][1]), 36);
  assert.equal(Number(bodies[2][1]) - Number(bodies[1][1]), 36);
  assert.equal(Number(bodies[1][1]) + 6, 260, 'The middle candle is centred in the viewBox.');
  assert(Number(bodies[1][4]) > 50, 'A compact explicit price range renders a tall reversal body.');
  assert.match(original, /<tspan[^>]*>Doji<\/tspan>/);
  assert.match(original, /purple candles close below/);
  assert.match(original, /Unmarked candles show context/);
  assert(!original.includes('Muted candles'));
  sample.variants[0].marks = [{ kind: 'level', startCandle: 'r', endCandle: 'f1', price: 95, label: 'Outer target' }, { kind: 'band', startCandle: 'r', endCandle: 'r', low: 5, high: 10, label: 'Outer risk band' }];
  const marked = render();
  assert(Number(candleRects(marked)[1][4]) < Number(bodies[1][4]), 'The domain expands to include marks outside candle extrema.');
  const wickCoordinates = [...marked.matchAll(/class="pattern-wick"[^>]*y1="([\d.]+)"[^>]*y2="([\d.]+)"/g)].flatMap(match => [Number(match[1]), Number(match[2])]);
  const levelCoordinate = Number(marked.match(/class="pattern-level"><line[^>]*y1="([\d.]+)"/)?.[1]);
  const band = marked.match(/class="pattern-band"><rect[^>]*y="([\d.]+)"[^>]*height="([\d.]+)"/);
  assert([...wickCoordinates, levelCoordinate, Number(band?.[1]), Number(band?.[1]) + Number(band?.[2])].every(y => y >= 26 && y <= 191), 'Candles, distant targets and risk bounds remain inside the padded plot.');
  assert(levelCoordinate < Math.min(...wickCoordinates), 'The higher target stays above the candles.');
});
