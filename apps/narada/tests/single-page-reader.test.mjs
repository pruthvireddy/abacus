import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';
import { assertSinglePageReader } from '../scripts/lib/static-reader-verification.mjs';
import { studyThemeHref } from '../scripts/lib/study-routes.mjs';

process.env.__NEXT_TRAILING_SLASH = 'true';
const require = createRequire(import.meta.url);
const modules = new Map();
function compile(relativePath) {
  const file = new URL(relativePath, import.meta.url);
  if (modules.has(file.href)) return modules.get(file.href);
  const { outputText } = ts.transpileModule(readFileSync(file, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    target: ts.ScriptTarget.ES2022, esModuleInterop: true,
  } });
  const compiled = { exports: {} };
  const resolve = id => {
    if (!id.startsWith('.') && !id.startsWith('@/')) return require(id);
    const target = id.startsWith('@/') ? new URL(`../src/${id.slice(2)}`, import.meta.url) : new URL(id, file);
    if (target.pathname.endsWith('.mjs')) return require(fileURLToPath(target));
    const source = ['.tsx', '.ts'].map(extension => new URL(`${target.href}${extension}`)).find(candidate => existsSync(candidate));
    if (!source) throw new Error(`Could not resolve ${id} from ${file.pathname}`);
    return compile(source.href);
  };
  new Function('require', 'module', 'exports', outputText)(resolve, compiled, compiled.exports);
  modules.set(file.href, compiled.exports);
  return compiled.exports;
}

const { StudyResultsPaper } = compile('../src/components/study-results-paper.tsx');
const { PublicationEvidence } = compile('../src/components/publication-evidence.tsx');
const render = (Component, props) => renderToStaticMarkup(React.createElement(Component, props));
const catalog = JSON.parse(readFileSync(new URL('../content/studies.json', import.meta.url), 'utf8'));
const study = catalog.studies.find(study => study.slug === 'verniman-pivot-statistics-es');
const readBundle = id => JSON.parse(readFileSync(new URL(`../public/publications/${id}/report.json`, import.meta.url), 'utf8'));
const publications = study.publicationTabs.map(tab => readBundle(tab.publicationId));
const earlierPublications = study.relatedPublications.map(reference => readBundle(reference.publicationId));
const escapeText = value => renderToStaticMarkup(React.createElement('span', null, value)).slice(6, -7);

test('six native theme tabs select only their own saved insights in Results', () => {
  const counts = [2, 4, 3, 5, 2, 5];
  let totalTables = 0;
  let totalFigures = 0;
  for (const [index, { report }] of publications.entries()) {
    const html = render(StudyResultsPaper, { study, publications, activePublicationId: report.id });
    assert.doesNotThrow(() => assertSinglePageReader(html, study, publications, studyThemeHref(study, report.id), report.id));
    const nav = html.match(/<nav class="single-page-contents"[\s\S]*?<\/nav>/)?.[0];
    assert(nav);
    assert.equal((nav.match(/<a /g) ?? []).length, 6);
    assert.equal((nav.match(/aria-current="page"/g) ?? []).length, 1);
    for (const tab of study.publicationTabs) {
      const link = [...nav.matchAll(/<a\b[^>]*>/g)].map(match => match[0]).find(tag => tag.includes(`href="${studyThemeHref(study, tab.publicationId)}"`));
      assert(link);
      assert.equal(link.includes('aria-current="page"'), tab.publicationId === report.id);
    }
    assert(!nav.includes('role="tab"'));
    assert.equal((html.match(/class="report-section /g) ?? []).length, counts[index]);
    const expectedTables = report.sections.filter(section => section.kind === 'table').length;
    const expectedFigures = report.sections.filter(section => section.kind === 'figure').length;
    assert.equal((html.match(/<table>/g) ?? []).length, expectedTables);
    assert.equal((html.match(/<img /g) ?? []).length, expectedFigures);
    totalTables += expectedTables;
    totalFigures += expectedFigures;
    assert.equal((html.match(/id="study-scope"/g) ?? []).length, 1);
    assert.match(html, /id="research-priority"/);
    assert(!html.includes('<pre'));
    assert(!html.includes('Insights in this theme'));
    assert(!html.includes('Study question themes'));
    assert(!html.includes('Related study results'));
    assert.match(html, new RegExp(`data-active-publication-id="${report.id}"`));
    for (const { report: unselected } of publications.filter(bundle => bundle.report.id !== report.id)) {
      assert(!html.includes(`id="theme-${unselected.id}"`));
      assert(!html.includes(`data-publication-id="${unselected.id}"`));
      for (const section of unselected.sections) {
        assert(!html.includes(`id="section-${section.id}"`));
        assert(!html.includes(escapeText(section.description)));
        assert(!html.includes(escapeText(section.finding)));
      }
    }
    for (const section of report.sections) {
      const start = html.indexOf(`id="section-${section.id}"`);
      const end = html.indexOf('</section>', start);
      const insight = html.slice(start, end);
      assert(insight.includes(`<h3 id="heading-${section.id}">${escapeText(section.title)}</h3>`));
      assert(insight.includes(escapeText(section.description)));
      assert(insight.includes(escapeText(section.finding)));
      assert(insight.indexOf(escapeText(section.description)) < insight.indexOf('Findings summary'));
      assert(insight.indexOf('Findings summary') < insight.indexOf(section.kind === 'table' ? '<table>' : '<figure'));
      if (section.kind === 'figure') assert(insight.includes(`/publications/${report.id}/${section.path}`));
    }
  }
  assert.equal(totalTables, 14);
  assert.equal(totalFigures, 7);
});

test('the featured theme is the default selection and unknown themes fail explicitly', () => {
  const html = render(StudyResultsPaper, { study, publications });
  assert.match(html, new RegExp(`data-active-publication-id="${study.featuredPublicationId}"`));
  assert.equal((html.match(/class="report-section /g) ?? []).length, 2);
  assert.throws(() => render(StudyResultsPaper, { study, publications, activePublicationId: 'unselected-theme' }), /Selected study theme is not in this study/);
});

test('scope notes remain while notebook publication and archive records are absent', () => {
  const html = render(StudyResultsPaper, { study, publications });
  assert.match(html, /<details class="single-page-scope" id="study-scope">/);
  assert.match(html, /<summary>Scope &amp; interpretation<\/summary>/);
  assert(!html.includes('<details open'));
  const lastInsight = Math.max(...publications[0].report.sections.map(section => html.indexOf(`id="section-${section.id}"`)));
  assert(html.indexOf('id="study-scope"') > lastInsight);
  const uniqueNotes = new Set(publications.flatMap(({ report }) => report.notes ?? []));
  const notesBody = html.slice(html.indexOf('<ul class="scope-notes">'), html.indexOf('</ul>', html.indexOf('<ul class="scope-notes">')));
  for (const note of uniqueNotes) assert(notesBody.includes(escapeText(note)));
  assert.equal((notesBody.match(/<li>/g) ?? []).length, uniqueNotes.size);
  for (const text of ['Notebook publication records', 'Saved publication data', 'Content SHA-256', 'Selected asset identities', 'Earlier &amp; companion evidence', 'Source run', 'id="publication-record"', 'class="print-publication-identity"']) assert(!html.includes(text), `Unexpected reader audit record: ${text}`);
  for (const { report, provenance } of [...publications, ...earlierPublications]) {
    assert(!html.includes(`id="saved-${report.id}"`));
    assert(!html.includes(provenance.sourceSha256));
    assert(!html.includes(`/publications/${report.id}/report.json`));
    assert(!html.includes(report.source.runId));
    for (const download of report.downloads ?? []) assert(!html.includes(`/publications/${report.id}/${download.path}`));
  }
});

test('the reader renders from selected narrative and evidence without requiring audit metadata', () => {
  const renderingFields = publications.map(({ report }) => ({ report: Object.fromEntries(['id', 'summary', 'sections', 'references', 'notes'].filter(key => report[key] !== undefined).map(key => [key, report[key]])) }));
  const html = render(StudyResultsPaper, { study, publications: renderingFields });
  assert.equal((html.match(/class="report-section /g) ?? []).length, 2);
  assert.match(html, /id="study-scope"/);
  assert(!html.includes('SHA-256'));
  assert(!html.includes('Notebook publication records'));
});

test('a missing explicitly selected theme fails instead of silently removing insights', () => {
  assert.throws(() => render(StudyResultsPaper, { study, publications: publications.slice(1) }), /Selected study theme is missing/);
});

test('compact evidence can keep exact hashes inline rather than link back to its own report', () => {
  const bundle = earlierPublications.find(({ report }) => report.downloads?.length);
  assert(bundle);
  const inline = render(PublicationEvidence, { report: bundle.report, compact: true, linkToRecord: false, idPrefix: 'saved-' });
  assert(!inline.includes('href="/reports/'));
  assert(inline.includes('Source and content hashes'));
  for (const download of bundle.report.downloads) assert(inline.includes(download.sha256));
  const unchanged = render(PublicationEvidence, { report: bundle.report, compact: true });
  assert(unchanged.includes(`href="/reports/${bundle.report.id}/#download-`));
});
