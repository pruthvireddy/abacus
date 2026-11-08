import assert from 'node:assert/strict';
import test from 'node:test';
import { assertSinglePageReader } from '../scripts/lib/static-reader-verification.mjs';

const study = { slug: 'single-study', readingMode: 'single-page', featuredPublicationId: 'opening', publicationTabs: [
  { publicationId: 'opening', label: 'Opening context' },
  { publicationId: 'crossing', label: 'Crossing activity' },
] };
const reports = [
  { id: 'opening', sections: [{ id: 'position', title: 'Opening position' }] },
  { id: 'crossing', sections: [{ id: 'frequency', title: 'Crossing frequency' }, { id: 'support', title: 'Crossing support' }] },
];
function markup(id = 'opening') {
  const selected = reports.find(report => report.id === id);
  const active = target => target === id ? ' aria-current="page"' : '';
  return `<article data-study-reading-mode="single-page" data-active-publication-id="${id}">
<nav aria-label="Study themes"><a href="/studies/single-study/"${active('opening')}>Opening context</a><a href="/reports/crossing/"${active('crossing')}>Crossing activity</a></nav>
<section id="theme-${id}" data-publication-id="${id}">${selected.sections.map(section => `<section class="report-section table" id="section-${section.id}"><a href="#section-${section.id}">${section.title}</a></section>`).join('')}</section>
<details id="publication-record"><summary>Scope and sources</summary></details></article>`;
}

test('the Results guard requires the selected theme body with native choices and one current choice', () => {
  assert.doesNotThrow(() => assertSinglePageReader(markup(), study, reports));
  assert.doesNotThrow(() => assertSinglePageReader(markup('crossing'), study, reports.map(report => ({ report })), '/reports/crossing/', 'crossing'));
  for (const [alter, expected] of [
    [html => html.replace('data-study-reading-mode="single-page"', ''), /Missing Results/],
    [html => html.replace('href="/reports/crossing/"', 'href="#theme-crossing"'), /theme route/],
    [html => html.replace('data-publication-id="opening"', ''), /only the active theme/],
    [html => html.replace('data-publication-id="opening"', 'data-publication-id="crossing"'), /Wrong selected theme/],
    [html => html.replace('data-active-publication-id="opening"', 'data-active-publication-id="crossing"'), /Wrong Results theme identity/],
    [html => html.replace('id="section-position"', 'id="section-missing"'), /insight order/],
    [html => html.replace('href="#section-position"', 'href="#elsewhere"'), /insight permalink/],
    [html => html.replace('id="theme-opening"', 'id="theme-missing"'), /Missing active theme body/],
    [html => html + '<p id="theme-opening">Duplicate</p>', /Duplicate DOM/],
    [html => html.replace('id="publication-record"', ''), /source record/],
    [html => html + '<nav aria-label="Related study results"></nav>', /repeats report navigation/],
    [html => html + '<section class="report-section table"></section>', /only the active theme's insights/],
    [html => html.replace('aria-current="page"', ''), /One current theme/],
    [html => html.replace('aria-current="page"', '').replace('href="/reports/crossing/"', 'href="/reports/crossing/" aria-current="page"'), /Incorrect current theme/],
    [html => html.replace('href="/reports/crossing/"', 'role="tab" href="/reports/crossing/"'), /native route links/],
  ]) assert.throws(() => assertSinglePageReader(alter(markup()), study, reports), expected);
});

test('the Results guard rejects inactive hidden bodies and incorrect route selections', () => {
  const inactive = '<section id="theme-crossing" data-publication-id="crossing" hidden><section class="report-section table" id="section-frequency"></section></section>';
  assert.throws(() => assertSinglePageReader(markup() + inactive, study, reports), /Inactive theme body/);
  assert.throws(() => assertSinglePageReader(markup(), study, reports, '/reports/crossing/', 'crossing'), /Incorrect current theme/);
  assert.throws(() => assertSinglePageReader(markup(), study, reports, undefined, 'unselected'), /not selected/);
  assert.throws(() => assertSinglePageReader(markup(), { ...study, publicationTabs: [...study.publicationTabs].reverse() }, reports), /theme choice order/);
  // Old fragment targets may remain as compatibility stubs without mounting
  // another theme's report body or table controls.
  assert.doesNotThrow(() => assertSinglePageReader(markup() + '<span id="section-frequency"></span>', study, reports));
  assert.doesNotThrow(() => assertSinglePageReader(markup() + '<p class="legacy-study-target" id="theme-crossing"><a href="/reports/crossing/">Crossing activity</a></p>', study, reports));
  assert.throws(() => assertSinglePageReader(markup() + '<section class="legacy-study-target" id="theme-crossing">Inactive theme body</section>', study, reports), /Inactive theme body/);
});
