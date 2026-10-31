import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

// Compile actual server primitives without writing build fixtures, mounting
// hidden reports or involving a browser. Static export/browser gates are separate.
const require = createRequire(import.meta.url);
const compiledModules = new Map();
function compile(relativePath) {
  const file = new URL(relativePath, import.meta.url);
  if (compiledModules.has(file.href)) return compiledModules.get(file.href);
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
    if (!source) throw new Error(`Test compiler could not resolve ${id} from ${file.pathname}`);
    return compile(source.href);
  };
  new Function('require', 'module', 'exports', outputText)(resolve, compiled, compiled.exports);
  compiledModules.set(file.href, compiled.exports);
  return compiled.exports;
}
const { StudyCard } = compile('../src/components/study-card.tsx');
const { StudyOverview, StudyStatistics, StudyCoverage, StudyFindings, StudyMethods, OverviewSourceRecord } = compile('../src/components/study-overview.tsx');
const { StudyShell, StudyDestinationNavigation } = compile('../src/components/study-shell.tsx');
const { StudyReportDirectory } = compile('../src/components/study-directory.tsx');
const { LegacyStudyLinks } = compile('../src/components/legacy-study-links.tsx');
const { StudyEvidenceDirectory } = compile('../src/components/study-evidence.tsx');
const { PublicationEvidence } = compile('../src/components/publication-evidence.tsx');
const catalog = JSON.parse(readFileSync(new URL('../content/studies.json', import.meta.url), 'utf8'));
const render = (Component, props) => renderToStaticMarkup(React.createElement(Component, props));
const escaped = text => renderToStaticMarkup(React.createElement(React.Fragment, null, text));
const renderCard = study => render(StudyCard, { study, number: 1 });
const localSlugs = ['trader-assistant-manual', 'es-opening-pivot-cloud', 'verniman-pivot-statistics-es'];

function overviewStudy() {
  const source = { publicationId: 'saved-primary', sourceRunId: 'frozen-run', sourceSha256: 'a'.repeat(64), sectionId: 'decision' };
  const href = '/reports/saved-primary/#section-decision';
  return { ...catalog.studies[0], featuredPublicationId: source.publicationId,
    resolvedOverview: {
      question: 'Did any primary policy qualify?', takeaway: 'No primary policy qualified; the saved baseline was retained.',
      evidenceType: 'Frozen historical comparison', population: 'One explicitly selected population.',
      period: 'Saved observation period.', sampleScope: 'No pooling across policy groups.',
      qualification: 'Assumed fills and unverified executable-account outcomes.',
      method: 'Compare saved policy summaries under the frozen validation rule.', source, href,
      methodSource: { ...source, sectionId: 'methods' }, methodHref: '/reports/saved-primary/#section-methods',
      statistics: [{ label: 'Selected zero', value: 0, format: 'percent', precision: 1, source, href, context: 'One saved cohort; full horizon.', note: '0 / 10 evaluable outcomes; saved interval.' },
        { label: 'Unknown outcome', value: null, source, href, context: 'Not counted as false.', description: 'Original table population.', notes: ['Unknown account paths excluded.'] }],
      findings: [{ text: 'The primary comparison did not change the baseline in its selected population.', source, href }],
      limitations: [{ text: 'No live executable-account conclusion.', source, href }],
      links: [{ label: 'Read the frozen decision', source, href }],
    },
  };
}

test('22 authored overviews and three fallback selections retain complete study presentation', () => {
  assert.equal(catalog.studies.filter(study => study.overview).length, 22);
  assert.deepEqual(catalog.studies.filter(study => !study.overview).map(study => study.slug).sort(), [...localSlugs].sort());
  for (const slug of localSlugs) {
    const study = catalog.studies.find(study => study.slug === slug);
    assert(study);
    const html = renderCard(study);
    for (const text of [study.title, study.topic.replaceAll('_', ' '), study.products.join(' / '), study.summary, study.evidenceStatus]) assert(html.includes(escaped(text)), `Missing authored fallback text for ${slug}`);
    assert.equal((html.match(/<a /g) ?? []).length, 2);
    assert(html.includes('href="/studies/' + study.slug + '/#research-priority"'));
    assert(html.includes(`href="/studies/${study.slug}/"`));
    assert(!html.includes('<dl'));
    assert(!html.includes('undefined'));
    assert(render(StudyOverview, { study }).includes(escaped(study.summary)));
    assert(render(StudyMethods, { study }).includes(escaped(study.evidenceStatus)));
  }
});

test('Study 30 keeps ranked priority reports and all six baseline reports in their own source-run analyses', () => {
  const study = catalog.studies.find(item => item.studyId === '30_verniman_pivot_statistics_es');
  assert(study);
  assert.equal(study.publicationTabs, undefined);
  assert.deepEqual(study.analyses.map(analysis => analysis.label), ['Ranked statistics', 'Original baseline']);
  assert.deepEqual(study.analyses[0].publicationTabs.map(tab => tab.label), ['Pivot statistics', 'Globex VWAP statistics']);
  assert.equal(study.analyses[1].publicationTabs.length, 6);
  assert(study.analyses[0].publicationTabs.every(tab => tab.sourceRunId === '20261031_ranked_v2'));
  assert(study.analyses[1].publicationTabs.every(tab => tab.sourceRunId === '20261031_repo_v2'));
  assert.equal(study.featuredPublicationId, study.analyses[0].publicationTabs[0].publicationId);
  assert.equal(study.featuredSourceRunId, study.analyses[0].publicationTabs[0].sourceRunId);
  for (const text of ['20 ranked descriptive measures', '875 pivot-matched RTH', '1,308 VWAP-only RTH', '1,292 full-Globex', 'January 3, 2020–September 18, 2026', 'January 1, 2020–October 30, 2026']) assert(study.summary.includes(text));
  assert(study.evidenceStatus.includes('Historical pivot available_at remains null and unverified.'));
  assert(study.evidenceStatus.includes('Original baseline reports retain their 20261031_repo_v2 attribution.'));
  const html = render(StudyReportDirectory, { study });
  for (const analysis of study.analyses) {
    assert(html.includes(analysis.label));
    for (const tab of analysis.publicationTabs) assert(html.includes(`href="/reports/${tab.publicationId}/"`));
  }
  assert.match(html, /8 selected publications/);
  assert(!html.includes('role="tab"'));
});

test('cards and statistic panels preserve zero, null, saved qualifiers and exact source links', () => {
  const study = overviewStudy();
  for (const html of [renderCard(study), render(StudyStatistics, { study })]) {
    assert.match(html, />0\.0%</);
    assert.match(html, />Not available</);
    for (const text of ['One saved cohort; full horizon.', 'Not counted as false.', '0 / 10 evaluable outcomes; saved interval.', 'Original table population.', 'Unknown account paths excluded.']) assert(html.includes(text));
    assert.match(html, /href="\/reports\/saved-primary\/#section-decision"/);
    assert(!html.includes('<table'));
    assert(!html.includes('table-filter-controls'));
  }
  assert(renderCard(study).includes('No primary policy qualified;'));
});

test('qualitative briefs use reviewed scope facts without performance placeholders or invented scores', () => {
  const study = overviewStudy();
  study.resolvedOverview.evidenceType = 'Qualitative source review';
  study.resolvedOverview.qualification = 'No computed Abacus performance statistics.';
  study.resolvedOverview.statistics = [
    { label: 'Review scope', text: 'One source video', context: 'Reviewed narrative only.', href: '/reports/saved-primary/#section-decision' },
    { label: 'Themes', text: 'Accumulation, manipulation, distribution', context: 'Author descriptions.', href: '/reports/saved-primary/#section-decision' },
  ];
  const html = renderCard(study) + render(StudyStatistics, { study }) + render(StudyCoverage, { study });
  assert.match(html, /One source video/);
  assert.match(html, /Accumulation, manipulation, distribution/);
  assert.match(html, /No computed Abacus performance statistics/);
  assert(!html.includes('Not available'));
  assert(!html.includes('confidence score'));
});

test('study destination links identify exactly one current static page and keep ordinary link semantics', () => {
  const study = overviewStudy();
  for (const current of ['overview', 'findings', 'explore', 'methods', 'evidence']) {
    const html = render(StudyDestinationNavigation, { study, current });
    assert.match(html, /aria-label="Study destinations"/);
    assert.equal((html.match(/<a /g) ?? []).length, 5);
    assert.equal((html.match(/aria-current="page"/g) ?? []).length, 1);
    for (const destination of ['overview', 'findings', 'explore', 'methods', 'evidence']) {
      const href = `/studies/${study.slug}/${destination === 'overview' ? '' : `${destination}/`}`;
      const tag = [...html.matchAll(/<a\b[^>]*>/g)].map(match => match[0]).find(tag => tag.includes(`href="${href}"`));
      assert(tag);
      assert.equal(tag.includes('aria-current="page"'), current === destination);
    }
    assert(!html.includes('role="tab"'));
    assert(!html.includes('<button'));
  }
});

test('the common shell retains study context without repeating the main takeaway on every destination', () => {
  const study = overviewStudy();
  const html = render(StudyShell, { study, current: 'methods', children: React.createElement('p', null, 'Destination content') });
  assert(html.includes(escaped(study.title)));
  assert(html.includes(study.resolvedOverview.question));
  assert.match(html, /href="\/"/);
  assert.match(html, /Destination content/);
  assert.match(html, /Assumed fills and unverified executable-account outcomes/);
  assert(!html.includes(study.resolvedOverview.takeaway));
  assert(!html.includes('table-filter-controls'));
});

test('overview, findings and methods retain precise support while keeping detailed report bodies separate', () => {
  const study = overviewStudy();
  const overview = render(StudyOverview, { study });
  for (const key of ['findings', 'explore', 'methods', 'evidence']) assert(overview.includes(`href="/studies/${study.slug}/${key}/"`));
  const methods = render(StudyMethods, { study });
  assert(methods.includes('href="/reports/saved-primary/#section-methods"'));
  assert(methods.includes(study.resolvedOverview.method));
  const findings = render(StudyFindings, { study });
  assert(findings.includes(study.resolvedOverview.findings[0].text));
  assert(findings.includes('href="/reports/saved-primary/#section-decision"'));
  const sources = render(OverviewSourceRecord, { study });
  assert(sources.includes('frozen-run'));
  assert(sources.includes('a'.repeat(64)));
  assert(sources.includes('href="/publications/saved-primary/report.json"'));
  for (const html of [overview, methods, findings, sources]) {
    assert(!html.includes('<table'));
    assert(!html.includes('table-filter-controls'));
    assert(!html.includes('class="report-section'));
  }
  delete study.resolvedOverview.period;
  assert(render(StudyCoverage, { study }).includes('does not specify a common date range'));
});

test('the Explore directory preserves every authored navigation shape and earlier-run relationship', () => {
  const base = overviewStudy();
  const tab = (publicationId, label) => ({ publicationId, label, sourceRunId: 'frozen-run' });
  const related = [
    { publicationId: 'earlier', sourceRunId: 'earlier-run', label: 'Earlier research', relationship: 'other-run' },
    { publicationId: 'revision', sourceRunId: 'frozen-run', label: 'Later presentation', relationship: 'presentation-revision' },
    { publicationId: 'supplement', sourceRunId: 'supplement-run', label: 'Exploratory extension', relationship: 'exploratory-supplement' },
  ];
  const shapes = [
    { shape: {}, ids: ['saved-primary'] },
    { shape: { publicationTabs: [tab('saved-primary', 'Product A'), tab('second', 'Product B')] }, ids: ['saved-primary', 'second'] },
    { shape: { analyses: [{ id: 'first', label: 'Frozen comparison', publicationTabs: [tab('saved-primary', 'Summary'), tab('year', 'Year-wise')] }, { id: 'baseline', label: 'Retained baseline', publicationTabs: [tab('baseline', 'Summary')] }] }, ids: ['saved-primary', 'year', 'baseline'] },
    { shape: { phaseFamilies: [{ id: 'initial', label: 'Initial phase', analyses: [{ id: 'condition', label: 'Authored condition', publicationTabs: [tab('saved-primary', 'Summary')] }] }, { id: 'later', label: 'Later phase', analyses: [{ id: 'condition', label: 'Separate condition', publicationTabs: [tab('later', 'Summary')] }] }] }, ids: ['saved-primary', 'later'] },
  ];
  for (const { shape, ids } of shapes) {
    const html = render(StudyReportDirectory, { study: { ...base, ...shape, relatedPublications: related } });
    for (const id of [...ids, ...related.map(reference => reference.publicationId)]) assert(html.includes(`href="/reports/${id}/"`), `Unreachable selected publication ${id}`);
    for (const relationship of ['other run', 'presentation revision', 'exploratory supplement']) assert(html.includes(relationship));
    for (const run of ['earlier-run', 'frozen-run', 'supplement-run']) assert(html.includes(run));
    assert.match(html, /Browse every report/);
    assert(!html.includes('role="tab"'));
    assert(!html.includes('<table'));
  }
});

function evidenceBundle(id) {
  return { report: { id, title: `Selected ${id}`, publishedAt: '2026-10-01T00:00:00Z', source: { producer: 'sahadeva', runId: `${id}-run` }, sections: [{ id: 'summary', title: 'Summary' }], notes: ['Saved note'],
    downloads: [{ id: 'shared', path: 'downloads/summary.csv', label: 'Saved CSV', description: 'Selected summary only.', population: `Separate ${id} population`, units: 'Unchanged units', scope: 'Fixed saved horizon', rowCount: 2, sha256: 'b'.repeat(64), source: { runId: `${id}-run`, artifact: 'tables/saved.csv', sha256: 'c'.repeat(64) } }],
    references: [{ id: 'shared', kind: 'saved-artifact', label: 'Saved reference', title: 'Saved artifact', runId: `${id}-run`, artifact: 'tables/saved.csv', sha256: 'd'.repeat(64) }] },
    provenance: { sourceSha256: 'a'.repeat(64), assets: [] } };
}

test('the evidence directory preserves per-report populations, units, scope and identities with isolated anchor IDs', () => {
  const bundles = [evidenceBundle('saved-primary'), evidenceBundle('earlier')];
  const study = { ...overviewStudy(), relatedPublications: [{ publicationId: 'earlier', sourceRunId: 'earlier-run', label: 'Earlier saved run', relationship: 'other-run' }] };
  const html = render(StudyEvidenceDirectory, { study, bundles });
  const ids = [...html.matchAll(/ id="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length);
  assert.equal(ids.filter(id => id.endsWith("download-shared")).length, 2);
  assert.equal(ids.filter(id => id.endsWith("reference-shared")).length, 2);
  for (const bundle of bundles) {
    const id = bundle.report.id;
    assert(html.includes(`Separate ${id} population`));
    assert(html.includes(`${id}-run`));
    assert(html.includes(`href="/reports/${id}/#publication-record"`));
    assert(html.includes(`href="/reports/${id}/#download-shared"`));
    assert(html.includes(`href="/reports/${id}/#reference-shared"`));
  }
  for (const text of ['Unchanged units', 'Fixed saved horizon', 'other run', 'download="summary.csv"', 'a'.repeat(64)]) assert(html.includes(text));
  const original = render(PublicationEvidence, { report: bundles[0].report });
  assert(original.includes('id="publication-downloads"'));
  assert(original.includes('id="download-shared"'));
  assert(original.includes('id="reference-shared"'));
  assert(!original.includes('id="saved-primary-download-shared"'));
  assert(original.includes('b'.repeat(64)) && original.includes('c'.repeat(64)), 'Full report records retain the exact CSV and saved-source hashes.');
});

test('legacy study fragments retain visible native links to the same saved report sections and evidence', () => {
  const featured = evidenceBundle('saved-primary');
  const html = render(LegacyStudyLinks, { featured });
  for (const id of ['section-summary', 'heading-summary', 'publication-downloads', 'download-shared', 'publication-references', 'reference-shared', 'publication-notes']) assert(html.includes(`id="${id}"`));
  for (const anchor of ['section-summary', 'publication-downloads', 'download-shared', 'publication-references', 'reference-shared', 'publication-notes']) assert(html.includes(`href="/reports/saved-primary/#${anchor}"`));
  assert.match(html, /Continue to Summary/);
  assert(!html.includes('<script'));
  assert(!html.includes('<table'));
});
