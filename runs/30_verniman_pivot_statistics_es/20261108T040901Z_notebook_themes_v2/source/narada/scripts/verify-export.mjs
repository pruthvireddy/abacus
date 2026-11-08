import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { readPublicationIndex, verifyPublications } from './lib/publication.mjs';
import { readStudyCatalog, studyHref, publicationGroups, studyPublicationReferences, findPublicationStudy, familyPublicationSelection } from './lib/studies.mjs';
import { assertPagePayloadSize } from './lib/static-page-budget.mjs';
import { verifyStaticPublicationJson } from './lib/static-json-delivery.mjs';
import { overviewHref, overviewSources } from './lib/study-overviews.mjs';
import { STUDY_DESTINATIONS, studyDestinationHref, studyPageRoutes, pageRouteFile, legacyStudyAnchorSelection } from './lib/study-routes.mjs';
import { assertPublicationNavigation, assertReaderContext } from './lib/static-reader-verification.mjs';

const root = resolve(import.meta.dirname, '../out');
const publicRoot = join(root, 'publications');
const { bundles } = await verifyPublications(publicRoot);
const delivery = await verifyStaticPublicationJson({
  canonicalRoot: resolve(import.meta.dirname, '../public/publications'),
  exportRoot: publicRoot,
});
const index = await readPublicationIndex(publicRoot);
const catalog = await readStudyCatalog(index.reports, undefined, { bundles });
await stat(join(root, 'index.html'));
await stat(join(root, '404.html'));
const homepage = await readFile(join(root, 'index.html'), 'utf8');
assert(homepage.includes('id="study-search"') && homepage.includes('<noscript>'), 'Discovery must retain a static collection and its no-JavaScript explanation.');
assert.equal((homepage.match(/data-study-slug="/g) ?? []).length, catalog.studies.length, 'Every study card must be in the static collection.');
for (const path of catalog.readingPaths ?? []) {
  assert(homepage.includes(`id="reading-path-${path.id}"`), `Missing authored reading path ${path.id}`);
  for (const step of path.steps) {
    const study = catalog.studies.find(study => study.studyId === step.studyId);
    assert(homepage.includes(`href="${studyDestinationHref(study.slug, step.destination)}"`), `Missing authored reading-path destination ${step.studyId}`);
  }
}
const noEagerReportJson = html => assert(!/<(?:script|link)\b[^>]*(?:src|href)="[^"]*\/publications\/[^"]*\/report\.json/.test(html), 'Core pages must not preload or execute report JSON.');
const linkTo = (html, href) => [...html.matchAll(/<a\b[^>]*>/g)].map(match => match[0]).find(tag => tag.includes(`href="${href}"`));
function verifyStudyNavigation(html, study, current, route) {
  const nav = /<nav\b[^>]*aria-label="Study destinations"[^>]*>[\s\S]*?<\/nav>/.exec(html)?.[0];
  assert(nav, `Missing persistent study navigation on ${route}`);
  assert.equal((nav.match(/aria-current="page"/g) ?? []).length, 1, `One current study destination required on ${route}`);
  for (const target of STUDY_DESTINATIONS) {
    const href = studyDestinationHref(study.slug, target.key);
    const link = linkTo(nav, href);
    assert(link, `Missing study destination link ${href} on ${route}`);
    assert.equal(link.includes('aria-current="page"'), target.key === current, `Incorrect current study destination on ${route}`);
  }
}
function verifyActiveResult(html, report, route) {
  assert.equal((html.match(/data-publication-id="/g) ?? []).length, 1, `Results must mount exactly one saved report on ${route}`);
  assert(html.includes(`data-publication-id="${report.id}"`), `Wrong selected result on ${route}`);
  assert.equal((html.match(/class="report-section /g) ?? []).length, report.sections.length, `Results must render only the active report's sections on ${route}`);
  let previousSection = -1;
  for (const section of report.sections) {
    const at = html.indexOf(`id="section-${section.id}"`);
    assert(at > previousSection, `Saved result section order/identity changed on ${route}: ${section.id}`);
    previousSection = at;
  }
}
noEagerReportJson(homepage);
const reportPages = new Map();
const reportHtml = async id => {
  if (!reportPages.has(id)) reportPages.set(id, await readFile(join(root, 'reports', id, 'index.html'), 'utf8'));
  return reportPages.get(id);
};
for (const study of catalog.studies) {
  assert(homepage.includes(`href="${studyHref(study.slug)}"`), `Study not linked from library: ${study.studyId}`);
  const pages = new Map();
  for (const destination of STUDY_DESTINATIONS) {
    const route = studyDestinationHref(study.slug, destination.key);
    const file = join(root, pageRouteFile(route));
    assert((await stat(file)).isFile(), `Missing study destination ${route}`);
    const html = await readFile(file, 'utf8');
    noEagerReportJson(html);
    pages.set(destination.key, html);
    verifyStudyNavigation(html, study, destination.key, route);
    if (destination.key === 'explore') {
      const featured = bundles.find(bundle => bundle.report.id === study.featuredPublicationId);
      verifyActiveResult(html, featured.report, route);
      const group = publicationGroups(study).find(group => group.some(tab => tab.publicationId === featured.report.id));
      if (group) assertPublicationNavigation(html, featured.report, group, route);
    } else {
      assert(!html.includes('class="report-section '), `Inactive study destinations must not mount report bodies: ${route}`);
      assert(!html.includes('class="table-filter-controls"'), `Inactive study destinations must not initialize report-table controls: ${route}`);
    }
  }
  const html = [...pages.values()].join('\n');
  if (study.overview) {
    for (const source of overviewSources(study.overview)) {
      const href = overviewHref(source);
      assert(html.includes(`href="${href}"`), `Missing overview evidence link ${href}`);
      const sourceHtml = await reportHtml(source.publicationId);
      assert(sourceHtml.includes(`id="section-${source.sectionId}"`), `Missing overview evidence destination ${href}`);
    }
  }
  const featured = bundles.find(bundle => bundle.report.id === study.featuredPublicationId);
  const selectedIds = new Set(studyPublicationReferences(study).map(p => p.publicationId));
  const selected = featured.report.presentation === 'research-paper'
    ? studyPublicationReferences(study).map(reference => bundles.find(bundle => bundle.report.id === reference.publicationId)) : [];
  for (const anchor of legacyStudyAnchorSelection(featured, selected)) {
    assert(pages.get('overview').includes(`id="${anchor.id}"`), `Missing legacy study fragment ${study.slug}/#${anchor.id}`);
    assert(pages.get('overview').includes(`href="${anchor.href}"`), `Missing visible compatibility link ${anchor.href}`);
    const targetId = anchor.href.split('/')[2];
    assert(selectedIds.has(targetId), `Legacy compatibility target is not selected: ${anchor.href}`);
    const targetHtml = await reportHtml(targetId);
    assert(targetHtml.includes(`id="${anchor.href.split('#')[1]}"`), `Missing legacy compatibility target ${anchor.href}`);
  }
  for (const id of selectedIds) {
    assert(html.includes(`href="/reports/${id}/"`), `Study destinations missing selected publication ${id}`);
    assert((await stat(join(root, 'reports', id, 'index.html'))).isFile(), `Missing selected publication page ${id}`);
  }
  for (const group of publicationGroups(study)) {
    for (const tab of group) {
      const publicationHtml = await reportHtml(tab.publicationId);
      const report = bundles.find(bundle => bundle.report.id === tab.publicationId)?.report;
      assert(report, `Missing selected publication ${tab.publicationId}`);
      assertPublicationNavigation(publicationHtml, report, group, `/reports/${tab.publicationId}/`);
      const context = findPublicationStudy(catalog, tab.publicationId);
      const analyses = context?.family?.analyses ?? study.analyses;
      if (analyses?.length) {
        assert(publicationHtml.includes('aria-label="Study analysis navigation"'), `Missing analysis navigation for ${tab.publicationId}`);
        for (const analysis of analyses) {
          const target = analysis.publicationTabs.find(candidate => candidate.label === tab.label) ?? analysis.publicationTabs[0];
          assert(publicationHtml.includes(`href="/reports/${target.publicationId}/"`), `Missing analysis selection ${analysis.id}`);
        }
      }
      if (study.phaseFamilies?.length) {
        const phaseHtml = /<nav\b[^>]*aria-label="Study phase navigation"[^>]*>[\s\S]*?<\/nav>/.exec(publicationHtml)?.[0];
        assert(phaseHtml, `Missing phase navigation for ${tab.publicationId}`);
        for (const family of study.phaseFamilies) {
          const target = familyPublicationSelection(family, context.analysis.id, tab.label).tab;
          assert(phaseHtml.includes(`href="/reports/${target.publicationId}/"`), `Missing phase selection ${family.id}`);
          if (family.id === context.family.id) {
            assert(linkTo(phaseHtml, `/reports/${target.publicationId}/`)?.includes('aria-current="page"'), `Missing current phase ${family.id}`);
          }
        }
      }
    }
  }
}
for (const report of index.reports) {
  assert((await stat(join(root, 'reports', report.id, 'index.html'))).isFile(), `Missing page for ${report.id}`);
}
for (const { report } of bundles) {
  const html = await reportHtml(report.id);
  let previousSection = -1;
  for (const section of report.sections) {
    const at = html.indexOf(`id="section-${section.id}"`);
    assert(at > previousSection, `Saved report section order/identity changed: ${report.id}/${section.id}`);
    assert(html.includes(`href="#section-${section.id}"`), `Missing direct section link: ${report.id}/${section.id}`);
    previousSection = at;
  }
  assertReaderContext(html, report);
  const context = findPublicationStudy(catalog, report.id);
  noEagerReportJson(html);
  if (context) {
    verifyStudyNavigation(html, context.study, 'explore', `/reports/${report.id}/`);
    verifyActiveResult(html, report, `/reports/${report.id}/`);
  }
  for (const download of report.downloads ?? []) {
    assert(html.includes(`href="/publications/${report.id}/${download.path}"`), `Missing download link for ${report.id}/${download.path}`);
    assert(html.includes(`download="${download.path.split('/').at(-1)}"`), 'Download must retain its selected filename.');
  }
  for (const reference of report.references ?? []) {
    assert(html.includes(`id="reference-${reference.id}"`), `Missing reference anchor ${reference.id}`);
  }
}
let checked = 0;
async function visit(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const file = join(directory, entry.name);
    assert(!entry.isSymbolicLink(), 'Static export must not contain symbolic links.');
    if (entry.isDirectory()) {
      await visit(file);
    } else if (assertPagePayloadSize(file, (await stat(file)).size)) {
      checked++;
    }
  }
}
await visit(root);
console.log(`Verified library, ${studyPageRoutes(catalog).length} study destinations, ${index.reports.length} publication routes and ${checked} bounded page payloads in out/.`);
console.log(`Verified compact delivery for ${delivery.reports} reports: ${delivery.sourceBytes} canonical bytes -> ${delivery.deliveryBytes} delivered bytes; all saved content preserved.`);
