import assert from 'node:assert/strict';
import { studyCanonicalHref, studyThemeHref } from './study-routes.mjs';

const linkTo = (html, href) => [...html.matchAll(/<a\b[^>]*>/g)].map(match => match[0]).find(tag => tag.includes(`href="${href}"`));

export function assertSinglePageReader(html, study, publications, route = studyCanonicalHref(study), activePublicationId = study.featuredPublicationId) {
  assert(html.includes('data-study-reading-mode="single-page"'), `Missing Results reader on ${route}`);
  const byId = new Map(publications.map(bundle => [(bundle.report ?? bundle).id, bundle.report ?? bundle]));
  const tabs = study.publicationTabs ?? [];
  const themes = /<nav\b[^>]*aria-label="Study themes"[^>]*>[\s\S]*?<\/nav>/.exec(html)?.[0];
  assert(themes, `Missing Results theme navigation on ${route}`);
  assert.equal((themes.match(/<a\b/g) ?? []).length, tabs.length, `Wrong theme selection count on ${route}`);
  assert.equal((themes.match(/aria-current="page"/g) ?? []).length, 1, `One current theme required on ${route}`);
  assert(!themes.includes('role="tab"'), `Theme choices must retain native route links on ${route}`);
  assert(tabs.some(tab => tab.publicationId === activePublicationId), `Active Results theme is not selected on ${route}`);
  let previousLink = -1;
  for (const tab of tabs) {
    assert(byId.has(tab.publicationId), `Missing saved theme ${tab.publicationId}`);
    const link = linkTo(themes, studyThemeHref(study, tab.publicationId));
    assert(link, `Missing Results theme route: ${tab.publicationId} on ${route}`);
    const at = themes.indexOf(link);
    assert(at > previousLink, `Results theme choice order changed on ${route}`);
    previousLink = at;
    assert.equal(link.includes('aria-current="page"'), tab.publicationId === activePublicationId, `Incorrect current theme on ${route}`);
    if (tab.publicationId !== activePublicationId) {
      const inactiveTargets = [...html.matchAll(/<[^>]+>/g)].map(match => match[0])
        .filter(tag => tag.includes(`id="theme-${tab.publicationId}"`));
      assert(inactiveTargets.every(tag => /^<p\b/.test(tag) && /\sclass="[^"]*\blegacy-study-target\b[^"]*"/.test(tag)),
        `Inactive theme body must not be mounted on ${route}: ${tab.publicationId}`);
    }
  }
  const report = byId.get(activePublicationId);
  assert.equal((html.match(/data-publication-id="/g) ?? []).length, 1, `Results must mount only the active theme on ${route}`);
  assert(html.includes(`data-publication-id="${report.id}"`), `Wrong selected theme body on ${route}`);
  assert(html.includes(`data-active-publication-id="${report.id}"`), `Wrong Results theme identity on ${route}`);
  const position = html.indexOf(`id="theme-${report.id}"`);
  assert(position >= 0, `Missing active theme body on ${route}`);
  let previousSection = position;
  for (const section of report.sections) {
    const at = html.indexOf(`id="section-${section.id}"`);
    assert(at > previousSection, `Active theme insight order/identity changed on ${route}: ${section.id}`);
    assert(html.includes(`href="#section-${section.id}"`), `Missing active theme insight permalink: ${section.id}`);
    previousSection = at;
  }
  assert.equal((html.match(/class="report-section /g) ?? []).length, report.sections.length, `Results must render only the active theme's insights on ${route}`);
  assert(!/aria-label="(?:Study question themes|Study chart navigation|Related study results|Insights in this theme)"/.test(html), `Results repeats report navigation on ${route}`);
  assert(html.includes('id="publication-record"'), `Missing Results source record on ${route}`);
  const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length, `Duplicate DOM identities in Results on ${route}`);
}

export function assertPublicationNavigation(html, report, siblings, route = report.id) {
  const label = report.presentation === 'research-paper' ? 'Study question themes' : 'Study chart navigation';
  const nav = new RegExp(`<nav\\b[^>]*aria-label="${label}"[^>]*>[\\s\\S]*?<\\/nav>`).exec(html)?.[0];
  assert(nav, `Missing ${label} on ${route}`);
  assert.equal((nav.match(/<a\b/g) ?? []).length, siblings.length, `Wrong saved selection count on ${route}`);
  assert.equal((nav.match(/aria-current="page"/g) ?? []).length, 1, `One current saved selection required on ${route}`);
  for (const sibling of siblings) {
    const href = `/reports/${sibling.publicationId}/`;
    const link = linkTo(nav, href);
    assert(link, `Missing sibling selection ${sibling.publicationId} on ${route}`);
    assert.equal(link.includes('aria-current="page"'), sibling.publicationId === report.id,
      `Incorrect current saved selection on ${route}`);
  }
}

export function assertReaderContext(html, report) {
  if (report.presentation === 'research-paper') {
    const contents = /<nav\b[^>]*aria-label="Insights in this theme"[^>]*>[\s\S]*?<\/nav>/.exec(html)?.[0];
    assert(contents, `Missing research-paper insight navigation: ${report.id}`);
    for (const section of report.sections) {
      assert(linkTo(contents, `#section-${section.id}`), `Missing research-paper insight link: ${report.id}/${section.id}`);
    }
  } else {
    assert(html.includes('class="contents-mobile"'), `Missing mobile reader context: ${report.id}`);
  }
  assert(html.includes('class="print-publication-identity"'), `Missing print reader identity: ${report.id}`);
}
