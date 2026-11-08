import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';
import { validateReport } from '../scripts/lib/publication.mjs';
import { assertPublicationNavigation, assertReaderContext } from '../scripts/lib/static-reader-verification.mjs';

process.env.__NEXT_TRAILING_SLASH = 'true';
const require = createRequire(import.meta.url);
const modules = new Map();
function compile(relativePath, bindings = {}, memo = modules) {
  const file = new URL(relativePath, import.meta.url);
  if (memo.has(file.href)) return memo.get(file.href);
  const { outputText } = ts.transpileModule(readFileSync(file, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    target: ts.ScriptTarget.ES2022, esModuleInterop: true,
  } });
  const compiled = { exports: {} };
  const resolve = id => {
    if (Object.hasOwn(bindings, id)) return bindings[id];
    if (!id.startsWith('.') && !id.startsWith('@/')) return require(id);
    const target = id.startsWith('@/') ? new URL(`../src/${id.slice(2)}`, import.meta.url) : new URL(id, file);
    if (target.pathname.endsWith('.mjs')) return require(fileURLToPath(target));
    const source = ['.tsx', '.ts'].map(extension => new URL(`${target.href}${extension}`)).find(candidate => existsSync(candidate));
    if (!source) throw new Error(`Could not resolve ${id} from ${file.pathname}`);
    return compile(source.href, bindings, memo);
  };
  new Function('require', 'module', 'exports', outputText)(resolve, compiled, compiled.exports);
  memo.set(file.href, compiled.exports);
  return compiled.exports;
}
const { StudyResults } = compile('../src/components/study-results.tsx');
const { PublicationContent } = compile('../src/components/publication-content.tsx');
const render = (Component, props) => renderToStaticMarkup(React.createElement(Component, props));

function publication() {
  return { report: {
    schemaVersion: '1.1', presentation: 'research-paper', id: 'selected-theme',
    title: 'Opening context', summary: 'Where does the opening price sit?',
    publishedAt: '2026-11-08T00:00:00Z', source: { producer: 'Sahadeva', runId: 'saved-execution' },
    sections: [
      { id: 'opening', kind: 'table', title: 'Where does price open?',
        description: 'Use the eligible sessions.\n\nRetain zero-event sessions.',
        finding: 'The selected result is descriptive.\n\nUnknown <state> remains unavailable.',
        columns: [{ key: 'state', label: 'State' }, { key: 'count', label: 'Sessions', format: 'number', precision: 0 }],
        rows: [{ state: 'Observed', count: 0 }, { state: 'Unknown', count: null }],
        notes: ['The saved denominator is unchanged.'] },
      { id: 'separation', kind: 'figure', title: 'How far apart are the levels?',
        description: 'Compare the saved distance distribution.', finding: 'This does not establish a trade rule.',
        path: 'figures/separation.png', alt: 'Saved level separation distribution.', caption: 'Point estimates only.' },
    ], notes: ['Historical availability is unverified.'],
  }, provenance: { sourceSha256: 'a'.repeat(64), assets: [{ path: 'figures/separation.png', sha256: 'b'.repeat(64) }] } };
}

function study() {
  return { featuredPublicationId: 'selected-theme', publicationTabs: [
    ['selected-theme', 'Opening context'], ['activity', 'Crossing activity'],
    ['breaks', 'Breaks & confirmation'], ['after', 'After the cross'],
    ['context', 'VWAP & cloud'], ['timing', 'Timing & stability'],
  ].map(([publicationId, label]) => ({ publicationId, label, sourceRunId: 'saved-execution' })) };
}

test('research-paper is an explicit 1.1 presentation selection with strict legacy compatibility', () => {
  const { report } = publication();
  assert.doesNotThrow(() => validateReport(report));
  assert.throws(() => validateReport({ ...report, presentation: 'arbitrary-html' }), /schema/);
  assert.throws(() => validateReport({ ...report, schemaVersion: '1.0' }), /schema/);
  const classic = structuredClone(report);
  delete classic.presentation;
  assert.doesNotThrow(() => validateReport(classic));
});

test('theme navigation keeps six native report links and one current theme', () => {
  const html = render(StudyResults, { study: study(), publication: publication() });
  assert.match(html, /class="study-results report-reader research-paper"/);
  assert.match(html, /aria-label="Study question themes"/);
  assert.match(html, /QUESTION THEMES/);
  const nav = html.match(/<nav class="publication-tabs publication-theme-tabs"[\s\S]*?<\/nav>/)?.[0];
  assert(nav);
  assert.equal((nav.match(/<a /g) ?? []).length, 6);
  assert.equal((nav.match(/aria-current="page"/g) ?? []).length, 1);
  const current = [...nav.matchAll(/<a\b[^>]*>/g)].map(match => match[0]).find(tag => tag.includes('href="/reports/selected-theme/"'));
  assert(current?.includes('aria-current="page"'));
  assert(!nav.includes('role="tab"'));
  assert.match(html, /href="#publication-record">Source &amp; execution record/);
  assert.match(html, /<code>saved-execution<\/code>/);
});

test('research-paper renders question, purpose, findings and evidence in order with complete prose', () => {
  const bundle = publication();
  const html = render(StudyResults, { study: study(), publication: bundle });
  assert.match(html, /<h2 id="selected-result-title">Opening context<\/h2>/);
  assert.match(html, /<h3 id="heading-opening">Where does price open\?<\/h3>/);
  assert.match(html, /aria-label="Insights in this theme"/);
  assert.match(html, /href="#section-opening"/);
  assert(!html.includes('class="reader-contents"'));
  const body = html.slice(html.indexOf('id="section-opening"'));
  assert(body.indexOf('Where does price open?') < body.indexOf('Use the eligible sessions.'));
  assert(body.indexOf('Use the eligible sessions.') < body.indexOf('Findings summary'));
  assert(body.indexOf('Findings summary') < body.indexOf('<table>'));
  assert(body.includes(bundle.report.sections[0].description));
  assert.match(body, /Unknown &lt;state&gt; remains unavailable/);
  assert.match(body, />0<\/td>/);
  assert.match(body, />Not available<\/td>/);
  assert.match(body, /href="\/publications\/selected-theme\/figures\/separation\.png"/);
  assert.match(body, /Scope &amp; interpretation/);
  assert(!html.includes('<pre'));
  assert(!html.includes('<script'));
});

test('classic reports retain sidebar contents, saved-view labels and original heading levels', () => {
  const bundle = publication();
  delete bundle.report.presentation;
  const html = render(StudyResults, { study: study(), publication: bundle });
  assert(!html.includes('report-reader research-paper'));
  assert.match(html, /class="reader-contents"/);
  assert.match(html, /aria-label="Study chart navigation"/);
  assert.match(html, /SAVED VIEW/);
  assert.match(html, /<h2 id="heading-opening">/);
  assert(!html.includes('Insights in this theme'));
});

test('standalone research notes keep level-two insight headings beneath their report title', () => {
  const html = render(PublicationContent, { publication: publication() });
  assert.match(html, /<h2 id="heading-opening">/);
  assert(!html.includes('<h3 id="heading-opening">'));
});

test('an earlier publication retains its compact access path without mounting the primary theme navigation', () => {
  const bundle = publication();
  bundle.report.id = 'earlier';
  delete bundle.report.presentation;
  const selected = { ...study(), relatedPublications: [{ publicationId: 'earlier', sourceRunId: 'saved-execution', label: 'Earlier saved result', relationship: 'other-run' }] };
  const html = render(StudyResults, { study: selected, publication: bundle });
  assert.match(html, /aria-label="Related study results"/);
  assert.match(html, /href="\/reports\/selected-theme\/"/);
  assert.match(html, /href="\/reports\/earlier\/"/);
  assert(!html.includes('href="/reports/activity/"'));
  assert(!html.includes('Study question themes'));
});

test('legacy anchor projection preserves selected earlier sections with featured-first duplicate precedence', () => {
  const { LegacyStudyLinks } = compile('../src/components/legacy-study-links.tsx');
  const featured = publication();
  const earlier = id => ({ ...publication(), report: { ...publication().report, id, sections: [
    { id: 'opening', kind: 'text', title: 'Repeated opening', body: 'PRIVATE_DUPLICATE_BODY' },
    { id: 's06', kind: 'text', title: 'Original returned-break question', body: 'PRIVATE_ORIGINAL_BODY' },
  ] } });
  const html = render(LegacyStudyLinks, { featured, selected: [featured, earlier('previous-featured'), earlier('older-ranked')] });
  const anchors = [...html.matchAll(/ id="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(anchors).size, anchors.length);
  assert.match(html, /id="section-s06"/);
  assert.match(html, /href="\/reports\/previous-featured\/#section-s06"/);
  assert(!html.includes('href="/reports/older-ranked/#section-s06"'));
  assert.match(html, /href="\/reports\/selected-theme\/#section-opening"/);
  assert(!html.includes('href="/reports/previous-featured/#section-opening"'));
  assert(!html.includes('PRIVATE_DUPLICATE_BODY'));
  assert(!html.includes('PRIVATE_ORIGINAL_BODY'));
  assert(!html.includes('<table'));
  assert(!html.includes('<img'));
});

test('only a research-paper overview loads authored sibling and earlier reports for legacy anchors', async () => {
  for (const [presentation, destination, preserve] of [['research-paper', 'overview', true], [undefined, 'overview', false], ['research-paper', 'explore', false]]) {
    const featured = publication();
    featured.report.presentation = presentation;
    const previous = { ...publication(), report: { ...publication().report, id: 'previous-featured', sections: [
      { id: 's06', kind: 'text', title: 'Original returned-break question', body: 'PRIVATE_ORIGINAL_BODY' },
    ] } };
    const sibling = { ...publication(), report: { ...publication().report, id: 'sibling', sections: [
      { id: 'other-question', kind: 'text', title: 'Sibling question', body: 'PRIVATE_SIBLING_BODY' },
    ] } };
    const selected = { ...study(), featuredSourceRunId: 'saved-execution',
      publicationTabs: [{ publicationId: 'selected-theme', sourceRunId: 'saved-execution', label: 'Featured' },
        { publicationId: 'sibling', sourceRunId: 'saved-execution', label: 'Sibling' }],
      relatedPublications: [{ publicationId: 'previous-featured', sourceRunId: 'earlier-execution', label: 'Previous feature', relationship: 'other-run' }] };
    const calls = [];
    const bundles = new Map([featured, sibling, previous].map(bundle => [bundle.report.id, bundle]));
    const empty = () => null;
    const bindings = {
      '@/lib/publications': { getPublication: async id => { calls.push(id); return bundles.get(id) ?? null; } },
      '@/lib/studies': { getStudyCatalog: async () => ({ studies: [], readingPaths: [] }) },
      './study-shell': { StudyShell: ({ children }) => React.createElement(React.Fragment, null, children) },
      './study-overview': { StudyOverview: empty, StudyStatistics: empty, StudyFindings: empty, StudyMethods: empty, OverviewSourceRecord: empty },
      './study-results': { StudyResults: empty },
      './study-evidence': { StudyEvidenceDirectory: empty },
      './reading-paths': { StudyReadingPaths: empty },
    };
    const { StudyExperiencePage } = compile('../src/components/study-experience.tsx', bindings, new Map());
    const html = renderToStaticMarkup(await StudyExperiencePage({ study: selected, destination }));
    assert.deepEqual(calls, preserve ? ['selected-theme', 'sibling', 'previous-featured'] : ['selected-theme']);
    assert.equal(html.includes('id="section-s06"'), preserve);
    assert.equal(html.includes('href="/reports/previous-featured/#section-s06"'), preserve);
    assert(!html.includes('PRIVATE_ORIGINAL_BODY'));
    assert(!html.includes('PRIVATE_SIBLING_BODY'));
  }
});

test('static navigation verification checks the selected presentation and confines current/sibling links to its navigation', () => {
  const selected = study();
  for (const presentation of ['research-paper', undefined]) {
    const bundle = publication();
    bundle.report.presentation = presentation;
    const html = render(StudyResults, { study: selected, publication: bundle });
    const expectedLabel = presentation === 'research-paper' ? 'Study question themes' : 'Study chart navigation';
    assert.doesNotThrow(() => assertPublicationNavigation(html, bundle.report, selected.publicationTabs));
    assert.throws(() => assertPublicationNavigation(html.replace(expectedLabel, 'Unrelated navigation'), bundle.report, selected.publicationTabs), /Missing/);
    const outsideCurrent = html.replace('aria-current="page"', '') + '<a href="/reports/selected-theme/" aria-current="page">Outside</a>';
    assert.throws(() => assertPublicationNavigation(outsideCurrent, bundle.report, selected.publicationTabs), /One current/);
    const outsideSibling = html.replace('href="/reports/activity/"', 'href="/reports/unselected/"') + '<a href="/reports/activity/">Outside sibling</a>';
    assert.throws(() => assertPublicationNavigation(outsideSibling, bundle.report, selected.publicationTabs), /Missing sibling/);
    const wrongCurrent = html.replace('aria-current="page" href="/reports/selected-theme/"', 'href="/reports/selected-theme/"')
      .replace('href="/reports/activity/"', 'aria-current="page" href="/reports/activity/"');
    assert.throws(() => assertPublicationNavigation(wrongCurrent, bundle.report, selected.publicationTabs), /Incorrect current/);
  }
});

test('static reader verification requires the appropriate responsive contents and print identity', () => {
  for (const presentation of ['research-paper', undefined]) {
    const bundle = publication();
    bundle.report.presentation = presentation;
    const html = render(StudyResults, { study: study(), publication: bundle });
    assert.doesNotThrow(() => assertReaderContext(html, bundle.report));
    assert.throws(() => assertReaderContext(html.replaceAll('print-publication-identity', 'missing-print-record'), bundle.report), /Missing print/);
    if (presentation) {
      assert.throws(() => assertReaderContext(html.replace('aria-label="Insights in this theme"', 'aria-label="Unrelated links"'), bundle.report), /Missing research-paper/);
      assert.throws(() => assertReaderContext(html.replace('href="#section-opening"', 'href="#unselected"'), bundle.report), /Missing research-paper insight link/);
    } else {
      assert.throws(() => assertReaderContext(html.replaceAll('contents-mobile', 'not-responsive-contents'), bundle.report), /Missing mobile/);
    }
  }
});
