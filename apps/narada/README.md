# Narada — Publishing

Use the [component instructions](AGENTS.md) and the current
[repository map](../../ARCHITECTURE.md) when extending this app.

Narada publishes selected Sahadeva reports as lightweight static webpages.
Sahadeva supplies the results and explanation; Narada validates, stages, and
renders them. The broader [research library](../../reports/index.html) remains
available locally.

## Setup and checks

Use Node 24. Run these commands from `apps/narada`:

```sh
npm ci
npm run verify
npm test
npm run lint
npm run build
npm run preview
```

`preview` serves the generated `out/` site at `http://127.0.0.1:4173`.
Use `PORT=4174 npm run preview` to change the port. The app has its own
package manifest and lockfile; no root JavaScript workspace setup is required.

Lint explicitly covers maintained `src`, `types`, `scripts`, and `tests`. Node
globals are scoped to operational/test `.mjs` files; generated output, retained
release snapshots, and dependencies are excluded.

The static export postcheck bounds each HTML page at 768 KiB and each serialized
React `.txt`/`.rsc` payload at 512 KiB. These account for table markup and rendered
payload expansion. Authored reports remain limited to 96 KiB, canonical bundles
to 192 KiB, and the report table/download/asset limits remain separate.
Reports that explicitly declare saved-row filters have a 2 MiB source and
4 MiB canonical bundle allowance, with at most 1,500 saved rows per filtered
table. Initial/default rendering and each selected page stay bounded at 100
rows. Other saved rows are downloaded only when a reader presses **Load table
filters**; mounting the page makes no publication-JSON request. Tables share one
request per report, with retry after failure. Default rows and CSV downloads
remain available without JavaScript. The HTML/React page limits and ordinary-report
budgets stay unchanged.

`postbuild` runs `optimize:static-json` before verifying the export. It compacts
the selected `out/publications/<id>/report.json` delivery files without changing
any saved value, key order, public ID, figure or CSV. Canonical files under
`public/publications/`, sealed runs and presentation revisions remain byte-identical.
The export verifier compares every compact file to its canonical input; new
release records retain both file hashes and byte counts under `staticJsonDelivery`.
Repeating the compactor is safe:

```sh
npm run optimize:static-json
npm run optimize:static-json -- --verify
```

After building, keep `npm run preview` running in one terminal and use another:

```sh
npm run smoke:preview -- --origin http://127.0.0.1:4173
```

For every catalog-derived study destination and immutable report route, also run:

```sh
npm run smoke:preview -- --origin http://127.0.0.1:4173 --all-routes
```

This bounded full-inventory mode checks each exported page with GET/HEAD and exact bytes, plus selected JSON/raster/CSV files and unknown destinations. It does not prepare a release.

The smoke command requires an explicit clean loopback HTTP origin. It checks a
bounded set of library/study/featured/retained report routes, publication JSON,
a raster, and a selected CSV using GET/HEAD, exact exported bytes, media types,
download headers, and real 404s. Its cases are verification selections, not an
authored study catalog. It reads app-owned inputs and `out/`, never private
research locators. It rejects redirects and remains separate from verify/build.

For a read-only private integrity audit, run separately:

```sh
npm run audit:sources
```

This follows only explicit `content/release-sources.json` locators and needs the
retained presentation/source files. Each entry chooses a presentation `revision`
or a sealed `run`; new runs use a separate publication manifest and verification
record as specified in the [private audit guide](../../docs/narada.md#local-maintenance-verification).
Multiple reports prepared in one run can select `publicationDirectory` exactly
`publications/<publication-id>`, with per-report source files and selected assets;
the run's ordinary evidence manifest stays at its root.
It checks safe file reads, declared hashes,
attribution, and retained verification records. It does not reconstruct source
cells, rerun research, or establish browser correctness. Ordinary verify/build
remain independent of those private evidence files and the Python environment.

Browser inspection checks actual navigation, keyboard focus/table scrolling,
desktop/mobile layout, figures, references, and downloads after local smoke.
Optional phase families add a bounded phase → condition → saved report hierarchy
without changing classic study navigation. A study selects either legacy tabs,
legacy analyses, or two to four phase families with one to eight analyses each.
Each analysis keeps one to twelve reports from its own source run; phase families
can retain earlier analyses from different runs. These remain ordinary immutable
report links, and the browse control retains every explicitly selected route.
Local maintenance findings are separate from hosted release gates; these commands
do not create a release or append an event to an existing release.

## Maintenance source map

| Task | Owner | Focused tests | Boundary |
|---|---|---|---|
| Report contract and selected assets | [publication.mjs](scripts/lib/publication.mjs), [evidence.mjs](scripts/lib/evidence.mjs) | [Publication](tests/publication.test.mjs), [evidence](tests/evidence.test.mjs), [input boundaries](tests/operational-inputs.test.mjs) | Explicit saved content, immutable IDs and exact selected bytes |
| Static study destinations and legacy links | [study-routes.mjs](scripts/lib/study-routes.mjs), [study shell](src/components/study-shell.tsx), [report directory](src/components/study-directory.tsx) | [Routes](tests/study-routes.test.mjs), [presentation](tests/study-presentation.test.mjs); export/HTTP checks | Five catalog-derived pages, native links, explicit current selection and saved-section compatibility |
| Authored navigation | [studies.mjs](scripts/lib/studies.mjs), [catalog](content/studies.json) | [Studies](tests/studies.test.mjs) | Stable slugs and explicit run/publication relationships |
| Study briefs and selected highlights | [study-overviews.mjs](scripts/lib/study-overviews.mjs), [catalog schema](contracts/studies.schema.json) | [Overview selections](tests/study-overviews.test.mjs), [presentation](tests/study-presentation.test.mjs); build postcheck | Optional app-owned abridgments, exact saved cells and pinned publication/section identities; no new research calculations |
| Research-priority presentation | [saved priority validator](scripts/lib/research-priorities.mjs), [ResearchPriority](src/components/research-priority.tsx), [display rules](src/lib/research-priority-display.mjs), [Sahadeva rubric](../../strategies/research-priority-rubric.md) | [Priority bindings](tests/research-priorities.test.mjs), [UI](tests/research-priority-ui.test.mjs), root [projector tests](../../scripts/tests/test_research_priorities.py) | Explicit offline projection; app-owned identity/freshness checks; no Python/research dependency in the build |
| Library search, filters and shared URLs | [discovery.ts](src/lib/discovery.ts), [LibraryDiscovery](src/components/library-discovery.tsx), [discovery styles](src/app/discovery.css) | [Discovery](tests/discovery.test.mjs) | Bounded authored index; complete static cards; no report-body search or runtime API |
| Curated reading paths | [catalog](content/studies.json), [schema](contracts/studies.schema.json), [validator](scripts/lib/studies.mjs), [ReadingPaths](src/components/reading-paths.tsx) | [Reading paths](tests/reading-paths.test.mjs) | Explicit study/destination references and editorial reasons; separate evidence qualifications |
| Report contents, section links and print | [ReportContents](src/components/report-contents.tsx), [SectionLink](src/components/section-link.tsx), [reader styles](src/app/reader.css) | [Reader](tests/report-reader.test.mjs), [sections](tests/report-sections.test.mjs) | Native section anchors, small client identity/title props, visible source identity and print-specific layout |
| Rendering and scalar display | [ReportSections](src/components/report-sections.tsx), [PublicationEvidence](src/components/publication-evidence.tsx), [format.ts](src/lib/format.ts) | [Sections](tests/report-sections.test.mjs), [format](tests/format.test.mjs) | Report meaning, ratios, nulls, units and accessibility |
| Illustrative candle panels | [PatternPanel](src/components/pattern-panel.tsx), [report contract](contracts/report-1.1.schema.json), [publication validator](scripts/lib/publication.mjs) | [Pattern boundaries](tests/patterns.test.mjs), [section rendering](tests/report-sections.test.mjs) | Authored schematic OHLC and explicit focus captions, no live prices or statistical calculations |
| Saved-row selectors, sharing and pagination | [FilteredReportTable](src/components/filtered-report-table.tsx), [table filters](src/lib/table-filters.ts), [table-share.ts](src/lib/table-share.ts), [saved JSON loader](src/lib/saved-tables.ts), [table styles](src/app/table-reader.css) | [Filters](tests/table-filters.test.mjs), [sharing](tests/table-share.test.mjs), [loader](tests/saved-tables.test.mjs), [filtered boundaries](tests/filtered-publication.test.mjs) | Exact saved cells only, typed bounded pending links, 100-row pages, explicit activation and one shared immutable JSON request |
| Static output and local preview | [verify-export.mjs](scripts/verify-export.mjs), [page budgets](scripts/lib/static-page-budget.mjs), [preview.mjs](scripts/preview.mjs), [preview-smoke.mjs](scripts/lib/preview-smoke.mjs) | [Page budgets](tests/static-page-budget.test.mjs), [local smoke](tests/preview-smoke.test.mjs); build postcheck | App-owned `out/` and explicit loopback server |
| Compact JSON delivery | [static-json-delivery.mjs](scripts/lib/static-json-delivery.mjs), [CLI](scripts/optimize-static-json.mjs) | [Delivery tests](tests/static-json-delivery.test.mjs); build postcheck | Lossless output-only transform; canonical publication identities and research bytes preserved |
| Release-gate lookup | [release-gates.mjs](scripts/lib/release-gates.mjs), [release CLI](scripts/release.mjs) | [Gate tests](tests/release-gates.test.mjs), [release identities](tests/release-identity.test.mjs), [release tests](tests/release.test.mjs) | Append-only events and exact artifact identity; no deployment in tests |
| Private source audit | [audit-release-sources.mjs](scripts/audit-release-sources.mjs) | [Audit tests](tests/audit-release-sources.test.mjs) | Explicit retained locators/pins; read-only integrity, not research revalidation |

Run focused tests with `node --test tests/<file>.test.mjs`. The full `npm test`
suite uses temporary synthetic fixtures; local HTTP smoke needs a running preview,
and browser inspection needs an actual browser. Hosted exact-byte checks and
promotion remain part of an explicitly authorized [release](releases/README.md).

The optional root [workspace harness](../../README.md#workspace-check-harness)
selects these local gates with `./scripts/check-workspace --profile narada`, using
this app as cwd and Node 24/npm from the caller's environment. It does not install
dependencies. Its standard-library orchestration needs no Python research
environment; the direct npm commands remain available independently. Preview
smoke and private source auditing have separate checks/profiles and prerequisites,
and are excluded from the default workspace gate and `narada` profile. No release
or publication action is registered.

## Publish a report

Create a report JSON following the [source contract](contracts/report.schema.json)
and the illustrative
[`examples/report.json`](examples/report.json). Use a new immutable publication
ID, identify its source run, and select the text, metrics, tables, and raster
figures intended for the web. Numeric results must have clear formats and
applicable units. `percent` values are ratios (`0.42` renders as `42%`), and
`unit` is a label without implicit scaling. Use `null` for an unavailable value.
PNG, JPEG, and WebP figures belong under `figures/` next to the source JSON and
must have alternative text.

Prepare source content before sealing a new run. For an already completed run,
create a later presentation revision under
`reports/exports/<study-id>/<run-id>/<revision-id>/` and record its provenance
using the [artifact guide](../../templates/README.md). Pass that revision's
`publication.json` to the same publisher command. Do not append it to the
completed source run.

```sh
npm run report:publish -- --report ../../runs/<study-id>/<run-id>/publication.json --dry-run
npm run report:publish -- --report ../../runs/<study-id>/<run-id>/publication.json
npm run verify
npm run build
npm run preview
```

The dry run validates without publishing. The publisher records a hash of the
canonicalized report JSON and hashes of the exact selected asset bytes. Repeating an
unchanged publication is safe; a changed report under an existing ID is
rejected. Use a new ID for a revision. Keep staged bundles in Git for
reproducible site builds.

The default output is `public/publications/`. For isolated checks, `--output`
can select a temporary publication directory. The normal site build always
reads `public/publications/`. See the [workflow](../../docs/narada.md) for size
and row limits.

The [authored catalog](content/studies.json) defines the current selected web
library, including the
[study 19 external tracker review](../../studies/19_value_area_fade_tracker/README.md) and
[study 20 Camarilla/EMA historical evidence](../../studies/20_camarilla_ema_cloud_reversals/README.md), retaining the two
[Phase 2 pilots](../../docs/narada-publication-plan.md#phase-2-completion-record).
The [Phase 3 record](../../docs/narada-publication-plan.md#phase-3-completion-record)
identifies that phase's selected runs, revisions and publications. To publish the illustrative example
in a separate temporary output for testing:

```sh
npm run report:publish -- --report examples/report.json --output /tmp/narada-example-publications
```

The example is not computed research. Temporary output is separate from the
normal site build, which does not stage examples.

Report tables have a focusable horizontal scroll region and a linked keyboard
hint. Numeric cells stay on one line; long contents lists scroll within the
desktop viewport. On mobile, contents return to the ordinary page flow. Figures
keep their aspect ratio; native-size files are linked from the figure and publication record.

Narada accepts the defined JSON sections. It does not import arbitrary HTML or
Markdown, read whole research directories, or compute results. Sahadeva can add
a producer that writes publication content before a run is sealed, or creates
a separately identified presentation revision. Existing reports and run
artifacts are not converted or rewritten.

Version 1.1 supports optional illustrative candle `patterns`, selected explicitly
with report `patternOverviewId` or section `patternId`. A section's `patternFocus`
caption identifies the part its saved table measures. Pattern producers supply
normalized OHLC geometry and plain text; the app renders its own accessible SVG,
measured shading, signal outlines and a role key. These are schematics rather
than observed samples. See the [contract guide](../../docs/narada.md#report-contract)
for role meanings, reference checks and fixed limits. The existing report and
page byte budgets still apply.
Repeated panels share a report-local SVG symbol for each authored variant.
Their titles, descriptions and focus captions remain specific to each panel;
the same geometry is drawn without duplicated markup or client-side code.
The first instance of each pattern retains its full numbered key and role
explanation. Repeated panels keep the candles and section focus, with a link
and accessible description reference to that canonical key.
Diagrams retain the site's light background. Solid green/purple candle bodies
are slim and spaced evenly; thin wicks share their direction color. The visible
price domain includes authored OHLC and all level/band marks, with padding;
this scales the schematic without changing its saved values or statistics.

## Evidence context and downloads

Source versions 1.0 and 1.1 coexist. Use 1.1 for visible table descriptions/notes,
section reference links and a bounded `references`/`downloads` declaration. The
[contract and download guide](../../docs/narada.md#evidence-contract-11-and-compatibility)
describes required fields, safe URLs, provenance checks and CSV restrictions.
Old publication bundles do not need migration. New report content always needs a
new immutable ID.

Declare selected UTF-8 summary CSVs under `downloads/`; limits are 256 KiB per
file, 512 KiB total, four files, 1,000 rows and 24 columns. Figure limits remain
separate. Prepare exact saved-cell projections and verify their source map before
dry-running and staging. No full research-directory copy or live analytical code
belongs in the app. Publisher verification checks selected bytes, headers, row
counts and hashes; the author's source-cell check establishes analytical traceability.
Explicitly filtered reports can declare CSVs up to 4 MiB each, 8 MiB total and
15,000 rows, retaining four files and 24 columns. Ordinary publications keep
the limits above. Neither allowance permits event-ledger discovery or general
workspace downloads.

Tables explain the missing/blank-cell display and expose context near their values, references have attributed labels and
media ranges, and CSV links show population/units/scope and filenames. Preview
serves CSV downloads with attachment headers. Verify real downloaded bytes in the
static preview as well as the generated links. The
[Phase 4 completion record](../../docs/narada-publication-plan.md#phase-4-completion-record)
identifies the enriched reports and reusable checks.

## Study catalog and navigation

[content/studies.json](content/studies.json) is the single authored catalog;
[contracts/studies.schema.json](contracts/studies.schema.json) owns its shape.
The full homepage collection follows its explicit array order; the separate
curated selection explicitly features the four redesign pilots. Stable
`/studies/<slug>/` pages show scope, products, evidence wording and selected
publication links. Immutable
reports remain at `/reports/<publication-id>/`; their study context comes from
the catalog without changing their saved content.

Optional `overview` metadata adds a research question, takeaway, evidence type,
population and scope, selected highlights, findings, limitations, method context
and supporting report-section links. It belongs in this same catalog, under the
app-owned schema and types. Keep these abridgments faithful to saved report
conclusions. Every highlight and supporting statement names a selected publication,
source run, canonical report-content hash and section. A numerical highlight selects
one saved metric by its exact label, or one table cell by a column and a uniquely
matching typed row selector. The build copies its saved value, units, precision
and notes; it does not calculate a new statistic. Authored scope facts can be used
where performance statistics are inappropriate. Null, zero and false retain their
separate meanings.
An optional `methodSource` pins a separate supporting method section with the same
publication/run/content identity shape; otherwise method context uses the brief's
root supporting source.

The resolver reads only selected app-owned publication bundles during verification
and the static build. Cards and overview HTML include the resolved brief without
downloading report JSON in the browser or embedding full report tables. Entries
without an overview use their existing title, summary, instruments and evidence
wording as complete card fallbacks. No second study registry or computed study
grade is introduced.

All catalog entries use the same five statically generated destinations:

| Destination | Route | Purpose |
| --- | --- | --- |
| Overview | `/studies/<slug>/` | Question, takeaway, selected highlights, key findings and limits |
| Findings | `/studies/<slug>/findings/` | Principal saved findings, supporting statistics and figure links |
| Explore | `/studies/<slug>/explore/` | Explicit phase/analysis/product/view directory and earlier publications |
| Method & scope | `/studies/<slug>/methods/` | Saved definitions, assumptions, coverage and limitations |
| Evidence | `/studies/<slug>/evidence/` | Report identities, selected CSVs, references and provenance |

The 22-study collection identified by the last verified production release now has
reviewed overview metadata, retaining the four Phase 1 pilots. The two additional
local entries (manual companion and ES opening pivot) retain authored summary and
evidence fallbacks inside the same shell. This rollout changes no production
selection and does not authorize publication or a release.

[StudyExperiencePage](src/components/study-experience.tsx) assembles small server
components; no destination mounts a hidden full report. Explore uses the existing
authored hierarchy and highlights the featured selection. Reports retain ordinary
phase/analysis/chart links and matching-label/condition fallbacks, plus explicit
routes to Overview, Explore and Evidence. The shared
[route projection](scripts/lib/study-routes.mjs) supplies export validation, preview
smoke, and reusable release adapters; historical releases keep their frozen routes.

Earlier `/studies/<slug>/#section-...` and evidence/reference/pattern fragments
retain static anchors. CSS `:target` reveals a visible link to the same saved
report destination without JavaScript or fragment-blind HTTP redirects. The first
redesign's `#findings`, `#explore`, `#method` and `#evidence` anchors remain useful
overview previews with links to the dedicated pages. Native links keep browser
history and new-tab behavior. Route navigation carries one `aria-current="page"`;
links are not ARIA tab widgets. Header links disable automatic prefetch, and study
and report directory links are ordinary anchors.

To maintain a study, preserve its stable identity and selections, author exact
saved sources, run verify/test/lint/build plus both preview checks, and inspect
representative browser interactions. Explicitly unavailable scope stays unavailable;
new numerical results or interpretations still require the research workflow.

To add a publication, prepare a new presentation revision, dry-run it, review
saved-cell transfers and prose, and publish it normally. Then edit the catalog:
set the featured publication and its explicit source-run ID. Related entries
require publication/run IDs, a reader-facing label and one relationship:
`other-run`, `exploratory-supplement`, or `presentation-revision`. Revisions must
share the featured source run; the other relationships must use different runs.
Keep the existing stable study ID and slug. A changed navigation selection does
not register a research reference or rewrite an old publication.

For parallel reports from one run, such as separate chart settings, author optional
`publicationTabs` with two to twelve `{ publicationId, sourceRunId, label }`
entries. The first entry must be the featured publication; every tab must share
its source run, have a unique public label, and name a distinct staged publication.
Explore presents each parallel saved view. Each links to its saved `/reports/<publication-id>/` page,
which retains the same navigation and
marks the current chart. These are ordinary keyboard-accessible route links;
the app renders selected saved content without calculating or combining results.
Tabs must not repeat related-publication selections. Existing catalogs can omit
the field and keep a direct featured-report directory.

For distinct analyses within one study, use optional `analyses` instead of
top-level `publicationTabs`. Each of two to eight entries has an `id`, `label`
and one to twelve `publicationTabs`. A group may retain a single saved baseline
without creating a duplicate report. Each group has one source run, which can
differ from the other groups. The first group/tab matches the featured
publication/run. Analysis IDs, labels and publication ownership are unique;
chart labels are unique within each group. Analysis links preserve a matching
chart label where available, and the study page lists every selected immutable
report under its browse control. Existing study slugs and report routes remain.

Version 1.1 tables can declare up to three `rowFilters` with a declared column
`key`, reader-facing `label`, and optional `defaultValue` that occurs in its
saved rows. Selectors use exact typed saved values, preserve ordering and cells,
and paginate at 100 rows. They select presentation rows without recalculating
rates or denominators. Defaults render on the server; all selections become
available after the bounded static JSON fetch. Errors offer retry and the
publication-data link, and evidence CSVs retain the full declared selection.
Verify default, yearly/window/cohort choices, reset, pagination, keyboard access,
and a failed load in the browser when changing this component.

`npm run verify` validates catalog fields, unique identities, ownership and all
publication/run relationships. `npm run build` generates and verifies library,
study and publication routes. Run the full checks above and inspect static
preview navigation after a catalog change. Do not maintain another catalog or
make a site build scan research directories. Superseded presentations retain
routes and a contextual label/link to the featured revision.

## Library discovery and reading paths

[LibraryDiscovery](src/components/library-discovery.tsx) enhances the complete
server-rendered card collection. Its [index projection](src/lib/discovery.ts)
selects only authored title, research question, summary, takeaway, topic,
instruments and optional `keywords`. It excludes report bodies, tables, source
locators and evidence-status prose. The serialized index has a 48 KiB budget;
there is no external search service, database, search API or report-JSON request.
Without JavaScript the search controls remain disabled, an explanation is shown,
and every study card and ordinary study link remains available.

Search uses every normalized word as a substring term across the selected text.
Case, accents, punctuation and repeated whitespace do not affect matching.
Different words may match different authored fields. The collection keeps its
authored order. Topic, instrument and evidence-type choices use **OR within each
category**, **AND between categories**, with search applied alongside them.
Topic/type keys normalize case and punctuation; display labels retain authored
wording. Evidence type comes only from validated overview metadata. Entries that
lack that field stay unclassified and remain visible when no type is selected.
Optional `keywords` belong on the existing study entry: one to eight unique,
trimmed plain-text values, each at most 60 characters; uniqueness ignores case.

Discovery state uses `q` and repeated `topic`, `instrument` and `type` query
parameters. For example:

```text
/?q=VWAP&instrument=gc
/?topic=range+xv&instrument=nq
/?type=qualitative+source+review
```

The query is bounded at 120 characters, each category at eight valid selections,
and the encoded query string, including `?`, at 2,048 characters. Values must
resolve to the current catalog-derived options. Duplicate choices, unknown
parameters and unavailable values are removed during canonicalization; an
oversized input returns the browseable default. Serialization retains existing
valid state when an additional selection would exceed its bound. Reset all
removes discovery query parameters. The first query edit pushes a history entry;
consecutive typing replaces that entry until blur. Filter changes, individual
removals, clear and reset are discrete history steps. Back/forward and refresh
restore the URL state. Input focus stays in place while typing; result counts
are announced after a short pause rather than on every keystroke.

Top-level `readingPaths` in the same catalog owns curated sequences. Each path
has an ID, title, explanation, qualification and two to six ordered steps; each
step names an existing `studyId`, one of the five study destinations and a reason
for inclusion. There may be up to six paths. IDs/titles must be unique, and a path
cannot repeat a study. The validator rejects missing references and unsafe text.
The current paths connect VWAP questions, Range XV questions, and session/event
context. They are authored reading sequences with explicit negative and
inconclusive evidence, not computed recommendations or independent replications.
Path and per-study qualifications remain visible. Homepage anchors such as
`/#reading-path-vwap-behavior` share a path, and study pages link back to their
path context. Adding a path changes navigation only; it does not select another
publication or alter a saved conclusion.

## Research priority

Study cards and overviews present **Research priority** as a dated editorial
assessment, with a text label alongside the stars. The explanation identifies
the reviewed candidate, materiality, supporting and contrary saved report
sections, main blocker and proposed next test. The [rubric](../../strategies/research-priority-rubric.md)
defines 1 Pause, 2 Define and test, 3 Targeted follow-up, 4 Strong candidate and
5 Highest priority. It is research triage, not a probability of profitability,
paper-quality rating or trading advice. Not assessed, Needs review and Not
applicable never appear as zero stars. Initial AI-assisted reviews remain
explicitly pending human approval.

Sahadeva owns [research-priorities.json](../../strategies/research-priorities.json).
From the workspace root, `python3 scripts/project-research-priorities.py --check`
validates its exact public report bindings and current catalog projection;
`--write` explicitly updates only generated priority fields and their rubric in
the existing catalog. Follow the rubric to reassess; do not edit the public
rating separately. Local reviewed-material paths/notes stay outside the app.
The full server-owned study catalog permits 200 studies within 512 KiB to retain
bounded explanations. The client discovery index keeps its separate 48 KiB limit
and carries only current priority state/score, not rationale or evidence arrays.

The app independently checks selected publication/run/content/section identity.
Bad or missing identities fail validation. Changed authored scope, the entire
selected evidence set, the rubric or an explicit reassessment flag makes a
still-valid historical assessment Needs review; its previous score/date remain
context and do not participate in numeric ranking. New evidence never upgrades
a score automatically. Relevant unpublished findings require Sahadeva to mark
Needs review and conduct a manual reassessment. The separate root
`--check-reviewed-inputs` audit hashes explicitly recorded local materials and
is not an app build dependency. App verify/build remain Node-only and consume
only app-owned catalog and publication bundles.

The library's optional Research priority filter accepts `priority=1` through
`priority=5`, `priority=not_assessed`, `priority=needs_review` and
`priority=not_applicable`. Repeated selections use OR, combined with AND against
other categories/search. `sort=priority` lists current numeric scores highest
first, preserving authored order for ties and placing nonnumeric states after
numeric assessments. Default order remains authored. For example:

```text
/?priority=2&instrument=gc
/?priority=not_assessed
/?sort=priority
```

The existing bounds, URL restoration, back/forward, focus, reset and no-JavaScript
fallback rules also apply. Without JavaScript, the complete authored-order
collection and server-rendered rating explanations remain available.

## Detailed report reader, table links and print

[ReportContents](src/components/report-contents.tsx) receives only section IDs
and titles plus evidence-destination flags. It renders a desktop rail and a
compact native mobile disclosure. Ordinary links retain every existing section
and evidence fragment. An optional intersection observer marks the visible
section with `aria-current="location"` without changing the URL or scrolling.
[SectionLink](src/components/section-link.tsx) renders a native server-side
`#section-<id>` permalink at each heading. The shared **Copy section link**
control in the desktop contents rail and mobile disclosure copies the currently
tracked section, whose title appears beside the control. This avoids a separate
client component and serialized props at every heading. Native permalinks remain
useful without JavaScript or clipboard access. Reader context stays compact and keeps routes
back to the study overview and Explore. Figures retain saved pixels, alternative
text, captions and full-size links. Download/reference components keep population,
units, scope, source run and saved-artifact identity visible. Full reports keep
exact hash pins in technical disclosures. Compact study Evidence directories link
to each immutable report’s exact `#download-<id>` or `#reference-<id>` record rather
than repeating those hashes; essential qualifications remain beside the evidence.
External sources and saved artifacts have explicit labels.

After **Load table filters**, readers can open or copy a selected-rows link.
Its immutable report path identifies the report, `table` identifies its saved
section, `filters` carries bounded URL-encoded JSON and the fragment targets the
same section. Filter values preserve their serialized scalar types; null, false,
zero, strings and **All values** remain distinct. Use the generated link controls
rather than hand-authoring values. Query input is limited to 4,096 characters,
filter JSON to 2,048 characters and three declared row filters. Unknown keys or
unavailable saved values are ignored with an explanation while valid choices and
authored defaults remain available. Malformed links retain defaults.

Opening a link leaves its selections pending and does **not** activate a report
request. Authored default rows remain visible until loading succeeds. After
explicit activation, membership is checked against the saved table and the pending
choices apply. A changed pending link on an already loaded table offers **Apply
linked selections**. **Reset selections** shows all saved values; **Restore
authored defaults** restores the declared defaults. Table links select existing
rows and never compute another result. Matching counts, current selections,
100-row pagination, loading/error/retry states and the shared per-report request
remain separate from research statistics.

Print styles in [reader.css](src/app/reader.css) and
[table-reader.css](src/app/table-reader.css) retain findings, qualifications,
figures/captions, notes, useful evidence links and publication/run identity.
Navigation and interactive controls are removed. A printed table states the
actual displayed default slice or row range/page, active selections, matching
row count and selected-table total; it is explicitly not the complete research
dataset. Printing never loads additional rows. Library print context likewise
identifies the shown study slice and active discovery state.

Run the normal verify/test/lint/build gates and both preview smoke modes, then
browser-check shared discovery URLs, history, keyboard focus, contents/permalinks,
pending table links, failure/retry/pagination, downloads, figures and reduced-width
layouts. Record request patterns, index/JavaScript sizes and source/asset integrity
separately from visual inspection; appearance alone is not a performance result.
Check print CSS layout in the browser and inspect native paged print/PDF manually
before publication. A QA screen wrapper applying print rules is a layout check
and does not establish native pagination. No local check prepares a release or
changes the publication/evidence boundary.

## Hosting

Use the [release operations guide](releases/README.md) to prepare an identifiable
static-only artifact and deploy to the dedicated `brew-vee/abacus-narada` project.
The workflow uploads an isolated Build Output API directory, without a repository
connection or remote source build. The app-root `vercel.json` describes source
build settings and is not used by the isolated upload.

```sh
npm run release:prepare
npm run release -- check <release-id>
```

Preparation runs local gates, audits explicit [source-revision locators](content/release-sources.json),
freezes selected output and records hashes under `releases/<id>/`. Generated payloads
and dirty-source snapshots stay ignored under `.release-artifacts/<id>/`. Neither
build nor preparation deploys. The guide specifies target binding, preview checks,
production staging/promotion, public verification and rollback. Deploy only the
recorded artifact; normal publication updates still require new immutable IDs.

See [the publication workflow](../../docs/narada.md) for ownership, preservation,
and the distinction between the local library and selected web reports.
