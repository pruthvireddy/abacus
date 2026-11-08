import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';
import { PRIORITY_BAND_LABELS, priorityPresentation } from '../src/lib/research-priority-display.mjs';

const require = createRequire(import.meta.url);
const compiledModules = new Map();
function compile(relativePath) {
  const file = new URL(relativePath, import.meta.url);
  if (compiledModules.has(file.href)) return compiledModules.get(file.href);
  const { outputText } = ts.transpileModule(readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022, esModuleInterop: true } });
  const compiled = { exports: {} };
  const resolve = id => {
    if (!id.startsWith('.') && !id.startsWith('@/')) return require(id);
    const target = id.startsWith('@/') ? new URL('../src/' + id.slice(2), import.meta.url) : new URL(id, file);
    if (target.pathname.endsWith('.mjs')) return require(fileURLToPath(target));
    const source = ['.tsx', '.ts'].map(extension => new URL(target.href + extension)).find(candidate => existsSync(candidate));
    if (!source) throw new Error('Test compiler could not resolve ' + id);
    return compile(source.href);
  };
  new Function('require', 'module', 'exports', outputText)(resolve, compiled, compiled.exports);
  compiledModules.set(file.href, compiled.exports);
  return compiled.exports;
}
const { ResearchPriority, ResearchPriorityAssessment, ResearchPriorityRubric } = compile('../src/components/research-priority.tsx');
const { StudyCard } = compile('../src/components/study-card.tsx');
const { StudyOverview } = compile('../src/components/study-overview.tsx');
const render = (Component, props) => renderToStaticMarkup(React.createElement(Component, props));
const source = { publicationId: 'saved-primary', sourceRunId: 'frozen-run', sourceSha256: 'a'.repeat(64), sectionId: 'primary-validation' };
const contrary = { ...source, sectionId: 'contrary-evidence' };
const rubric = { version: '1.0', sourceSha256: 'b'.repeat(64), meaning: 'How strongly does the saved evidence justify further focused investigation toward an actionable, material edge?', disclaimer: 'A dated editorial research judgment, not a probability of profitability or a trading recommendation.', bands: [1, 2, 3, 4, 5].map(score => ({ score, label: PRIORITY_BAND_LABELS[score], definition: 'Saved definition for band ' + score + '.' })) };
const baseStudy = { studyId: 'saved-study', slug: 'saved-study', title: 'A saved study', summary: 'A saved primary decision.', topic: 'Saved comparison', products: ['GC'], evidenceStatus: 'The saved primary validation failed.', featuredPublicationId: source.publicationId, featuredSourceRunId: source.sourceRunId };
function assessedStudy(score = 3) {
  const assessment = { assessmentId: 'priority-saved-study-20261026', rubricVersion: '1.0', rubricSha256: rubric.sourceSha256, reviewedAt: '2026-10-26', reviewer: 'Codex — AI-assisted editorial review', state: 'assessed', score, scope: 'A specific exploratory candidate, separate from the failed primary.', rationale: 'The declared primary validation failed. An exploratory mechanism remains unresolved.', materiality: 'A positive net USD-per-trade difference after the stated cost assumptions.', supporting: [{ text: 'The saved exploratory contrast is specific but uncertain.', source }], contrary: [{ text: 'Primary validation failed; previously inspected data cannot provide new confirmation.', source: contrary }], blocker: 'Protected validation and executable fills remain unresolved.', nextTest: { description: 'Freeze one causal candidate and evaluate it on an untouched separated sample.', supports: 'A positive paired net-USD contrast with a wholly positive uncertainty interval.', rejects: 'A nonpositive contrast or failure under the fixed cost assumptions.' }, reviewedStudySha256: 'c'.repeat(64), reviewedPublications: [{ publicationId: source.publicationId, sourceRunId: source.sourceRunId, sourceSha256: source.sourceSha256 }] };
  return { ...baseStudy, researchPriority: assessment, resolvedResearchPriority: { ...assessment, effectiveState: 'assessed', staleReasons: [], supporting: assessment.supporting.map(item => ({ ...item, href: '/reports/' + item.source.publicationId + '/#section-' + item.source.sectionId })), contrary: assessment.contrary.map(item => ({ ...item, href: '/reports/' + item.source.publicationId + '/#section-' + item.source.sectionId })) } };
}

test('server priority labels expose the whole score and band while stars remain decorative', () => {
  const html = render(ResearchPriority, { study: assessedStudy(3) });
  assert(html.includes('Research priority: 3 out of 5 — Targeted follow-up.'));
  assert.equal((html.match(/★/g) ?? []).length, 3);
  assert.equal((html.match(/☆/g) ?? []).length, 2);
  assert.match(html, /class="priority-stars" aria-hidden="true"/);
  assert.match(html, /3\/5/);
  assert.match(html, /href="\/studies\/saved-study\/#research-priority"/);
  for (const interactive of ['<button', 'role="slider"', 'role="radiogroup"', 'role="radio"', '<script']) assert(!html.includes(interactive));
});

test('absent and explicit nonnumeric states never masquerade as zero-star ratings', () => {
  for (const [state, label] of [['not_assessed', 'Not assessed'], ['needs_review', 'Needs review'], ['not_applicable', 'Not applicable']]) {
    const html = render(ResearchPriority, { study: { ...baseStudy, researchPriority: { state } } });
    assert(html.includes('Research priority: ' + label + '.'));
    assert(!/[★☆]/.test(html));
    assert(!html.includes('0/5'));
  }
  const absent = render(ResearchPriorityAssessment, { study: baseStudy });
  assert(absent.includes('No assessment has been published'));
  assert(absent.includes('Research priority: Not assessed.'));
  assert(!/[★☆]/.test(absent));
  for (const score of [0, 6, 2.5, null, '3']) assert.throws(() => priorityPresentation({ ...baseStudy, researchPriority: { state: 'assessed', score } }), /integer score/);
});

test('stale assessments show Needs review and preserve a clearly dated previous score and reasoning', () => {
  const study = assessedStudy(5);
  study.resolvedResearchPriority.effectiveState = 'needs_review';
  study.resolvedResearchPriority.staleReasons = ['A relevant new report was selected after this review.'];
  const badge = render(ResearchPriority, { study });
  assert(badge.includes('Research priority: Needs review.'));
  assert(!/[★☆]/.test(badge));
  assert(!badge.includes('5/5'));
  const html = render(ResearchPriorityAssessment, { study, rubric });
  for (const text of ['Reassessment needed.', 'excluded from numeric priority filters and ordering', 'Previous assessment:', '5/5 — Highest priority', 'October 26, 2026', 'Previous assessment rationale', 'A relevant new report was selected after this review.', study.researchPriority.rationale]) assert(html.includes(text));
});

test('the compact assessment retains scope, materiality, both evidence sides, next criteria and identity pins', () => {
  const study = assessedStudy(2);
  const html = render(ResearchPriorityAssessment, { study, rubric });
  for (const text of [study.researchPriority.rationale, study.researchPriority.scope, study.researchPriority.materiality, study.researchPriority.blocker, study.researchPriority.nextTest.description, study.researchPriority.nextTest.supports, study.researchPriority.nextTest.rejects, study.researchPriority.reviewer, source.sourceRunId, source.sourceSha256]) assert(html.includes(text));
  for (const pattern of [/id="research-priority"/, /id="research-priority-explanation"/, /href="#research-priority-explanation"/, /Supporting evidence/, /Contrary evidence &amp; limits/, /href="\/reports\/saved-primary\/#section-primary-validation"/, /href="\/reports\/saved-primary\/#section-contrary-evidence"/, /has not been executed as part of this assessment/, /Rubric 1\.0/, /href="\/#research-priority-rubric"/]) assert.match(html, pattern);
  assert(!html.includes('<script'));
});

test('cards and overview preserve existing findings and qualifications beside server-rendered priority', () => {
  const study = assessedStudy(2);
  study.resolvedOverview = { question: 'Did the primary qualify?', takeaway: 'No primary candidate qualified.', evidenceType: 'Frozen policy comparison', population: 'One saved population.', qualification: 'Assumed fills; no audited account result.', period: 'Saved period.', method: 'Saved method.', source, href: '/reports/saved-primary/#section-primary-validation', statistics: [], findings: [], limitations: [], links: [] };
  const card = render(StudyCard, { study, number: 1 });
  for (const text of ['Research priority: 2 out of 5 — Define and test.', 'Frozen policy comparison', 'Assumed fills; no audited account result.', 'No primary candidate qualified.']) assert(card.includes(text));
  const overview = render(StudyOverview, { study, rubric });
  assert(overview.includes('id="research-priority"'));
  assert(overview.indexOf('MAIN TAKEAWAY') < overview.indexOf('id="research-priority"'));
  assert(overview.includes('No primary candidate qualified.'));
  assert(!overview.includes('table-filter-controls'));
});

test('rubric meaning and all authored definitions are available through a static native disclosure', () => {
  const html = render(ResearchPriorityRubric, { rubric });
  assert(html.includes('id="research-priority-rubric"'));
  assert(html.includes(rubric.meaning));
  assert(html.includes(rubric.disclaimer));
  assert.match(html, /<details><summary>/);
  for (const band of rubric.bands) {
    assert(html.includes(band.score + '/5 — ' + band.label));
    assert(html.includes(band.definition));
  }
  for (const text of ['Not assessed', 'Needs review', 'Not applicable', 'not zero stars']) assert(html.includes(text));
  assert(!html.includes('<script'));
});

test('explicit stronger-score evidence is server-rendered with its saved support and identity', () => {
  const study = assessedStudy(5);
  const highPriorityEvidence = {
    executionAndCosts: { text: 'Saved causal fills and explicit net-cost assumptions.', source: { ...source, sectionId: 'execution' } },
    separatedEvaluation: { text: 'Saved untouched separated evaluation.', source: { ...source, sectionId: 'separated' } },
    materialEffect: { text: 'Saved material net-USD effect versus the declared baseline.', source: { ...source, sectionId: 'material' } },
    independentCorroboration: { text: 'Saved independently corroborated result.', source: { ...source, sectionId: 'corroboration' } },
  };
  study.resolvedResearchPriority.highPriorityEvidence = highPriorityEvidence;
  const html = render(ResearchPriorityAssessment, { study, rubric });
  for (const item of Object.values(highPriorityEvidence)) {
    assert(html.includes(item.text));
    assert(html.includes('href="/reports/saved-primary/#section-' + item.source.sectionId + '"'));
  }
  for (const label of ['Execution and costs', 'Separated evaluation', 'Material effect', 'Independent corroboration']) assert(html.includes(label));
});
