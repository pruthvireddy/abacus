import assert from 'node:assert/strict';

const linkTo = (html, href) => [...html.matchAll(/<a\b[^>]*>/g)].map(match => match[0]).find(tag => tag.includes(`href="${href}"`));

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
