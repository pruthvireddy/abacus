# Narada report publication

Narada is the web publication component of Abacus. It turns selected, saved
report content into lightweight pages that can be statically hosted on Vercel.
It has an independent Node 24/npm environment under `apps/narada/`; the Python
workspace remains responsible for data and research.

The [Phase 1 publication plan](narada-publication-plan.md) inventories all studies
and hands off the two pilots. Use the [web report authoring template](../templates/web-study-report.md)
for selected content. The [release operations guide](../apps/narada/releases/README.md)
defines the static-output Vercel upload without a repository connection, local
preparation gates, release identity, hosted checks and rollback.

## Ownership

The [current repository map](../ARCHITECTURE.md) defines the three components:
Bhishma — Data & Features, Sahadeva — Research & Analysis, and Narada — Publishing.
Sahadeva owns the report's meaning and numerical content; Narada owns the
generic publication schema, validation, and presentation.

Narada does not compute statistics or call Python during a site build. Its
publication input is a saved report contract, rather than research code or a
live data service.

## Local library and selected web reports

`reports/index.html` is the local research library. It links studies, runs,
strategy cards, and historical artifacts across the workspace. It remains
useful offline and is not the directory to deploy as Narada's site.

Narada builds only from its explicitly staged public report bundles. A source
report and its declared raster figures and summary downloads cross that boundary
after validation.
Raw data, full event ledgers, local storage paths, and unrelated run files do
not become web artifacts merely because they are present in the workspace.
Everything staged in Narada's public directory is intended to be downloadable.

## Report contract

The [source contract](../apps/narada/contracts/report.schema.json) defines a
versioned JSON document with an immutable publication ID, title,
summary, publication timestamp, and source producer/run ID. Its ordered sections
are plain text, metrics, tables, or raster figures. Numeric content declares its
format and applicable units. `percent` values are ratios: `0.42` displays as
`42%`; a `unit` label never changes a value's scale. `null` displays as
"Not available". Figures are PNG, JPEG, or WebP files under `figures/` next to
the source JSON and include accessible alternative text.

The contract is deliberately independent of any instrument, indicator, or
strategy. It does not accept arbitrary HTML, execute Markdown, or automatically
extract content from older reports. Future Sahadeva report producers should
emit this contract directly while preparing a run in working storage. Include
`publication.json` and selected figures before sealing the run at
`runs/<study-id>/<run-id>/`. No analysis or automatic report producer
is introduced by adding Narada.

Version 1.1 can also declare bounded illustrative candle `patterns`. Each pattern
has an ID, title, description and one or two variants. Each variant supplies
one to twelve authored OHLC candles in normalized schematic coordinates from
0 to 100, with a label and an explicit `context`, `signal`, `measured` or
`termination` role. Low/high must contain open/close. Up to eight authored
`span`, `level` or `band` marks reference ordered candles in that variant; bands
require low below high. The geometry is explanatory content, not an observed
price series or an additional numerical result.

The report may explicitly select `patternOverviewId` to show a panel above its
sections. Any section can select `patternId` and an optional `patternFocus`
caption to explain what its current saved statistics measure. References must
resolve within that report. Unselected patterns are not rendered at the top.
The app renders escaped text and its own SVG elements; arbitrary SVG, HTML,
paths and drawing programs are not accepted. Signal outlines, measured shading,
candle labels, a visible role key and SVG title/description distinguish roles
without relying on color alone. Termination marks mean the stated run ends;
producers must not label an opposite candle as ending a payoff horizon that
continues across opposite physical bars.
The renderer defines each variant's SVG geometry once per report and references
it in repeated section panels. Each visible instance retains its own accessible
title/description and focus caption. Drawing coordinates are rounded to two
decimal places; source schematic values and saved statistical cells are unchanged.
The first visible instance of a pattern supplies its full caption, numbered
mark key and role legend. Later section panels retain their candles and focus
caption, and link back to that explanation; their SVG accessibility descriptions
reference its saved variant key. Distinct patterns retain distinct explanations.

Patterns are limited to twelve per report. Pattern/variant titles are bounded
at 100 characters, descriptions at 600, candle labels at 20, mark labels at 48
and section focus captions at 500. Existing source, canonical bundle and static
page budgets still apply. This optional presentation vocabulary does not change
1.0 reports or existing publication bytes.

For an already completed run, create a presentation-only revision at
`reports/exports/<study-id>/<run-id>/<revision-id>/` with its own `publication.json`,
figures, and provenance manifest. Record exact source-artifact paths and hashes
under the [artifact conventions](../templates/README.md). The same publishing
command accepts this source path. A changed numerical result or finding belongs
to a new analytical run. Completed run directories remain unchanged.

The publisher enforces the schema and publication limits, records a SHA-256
hash of the canonicalized report JSON and hashes of the exact selected asset bytes,
and stages the selected bundle for the site. Republishing identical content
under its existing ID leaves it unchanged. Reusing an ID for different content
is rejected; publish a correction under a new ID. The source run and older
publications remain unchanged.

Ordinary reports are bounded: source JSON is at most 96 KiB, a published bundle at most
192 KiB, and each table at most 100 rows and 12 columns. The bundle allowance
includes canonical formatting and provenance; the authored source limit stays
96 KiB. Figures are limited to
2 MiB each and 8 MiB total per report. The catalog allows at most 200 reports
within 256 KiB. These limits keep the site suitable for selected summaries;
detailed research evidence stays in its source run.

The exported-page verifier separately permits at most 768 KiB per HTML page and
512 KiB per serialized React `.txt`/`.rsc` payload. Rendering a bounded report
adds table markup and serialized content; these allowances do not change the
authored report, canonical bundle, table, download or raster limits.

An explicitly filtered report has at least one table declaring `rowFilters`.
Its source is bounded at 2 MiB and its canonical bundle at 4 MiB. Each filtered
table can contain 1,500 saved rows; tables without filters retain 100 rows and
all tables retain 12 columns. These are conditional allowances, not changes to
ordinary reports. The renderer passes at most 100 authored default rows to the
client and shares one fetch of the immutable selected publication JSON for the
remaining controls. Selecting or paginating saved rows does not compute results.
HTML and serialized React payloads retain their original bounds above.

## Evidence contract 1.1 and compatibility

The source [dispatcher schema](../apps/narada/contracts/report.schema.json) accepts
both [1.0](../apps/narada/contracts/report-1.0.schema.json) and
[1.1](../apps/narada/contracts/report-1.1.schema.json). Existing 1.0 inputs and
bundles retain their original fields, validation and immutable bytes. Choose
`schemaVersion: "1.1"` for table context, structured references or selected CSVs.
The bundle retains its report/provenance shape and the publication index remains
version 1.0. Every revised report uses a new ID and export revision.

Version 1.1 adds optional table `description` (1,000 characters) and up to six
`notes` (1,000 characters each). They appear beside the table and are included in
the scroll region's accessible description. Any section may name `referenceIds`;
these resolve to a top-level `references` array of at most 20 entries. Tables,
figures and plain text keep the existing reading order. No HTML or Markdown is
executed. Figures link to their full-size raster file.

An `external` reference requires `id`, `kind`, `label`, `title`, `creator` and
`url`; optional `publishedOn`/`accessedOn` are valid calendar dates, and
`startSeconds`/`endSeconds` are ordered media offsets. URLs must be clean public
HTTPS URLs without credentials, custom ports, local/internal/test hosts or IP
literals. They render with `noopener noreferrer`. Validation does not fetch the
source or authenticate its claims. Use only references established by saved evidence.
A `saved-artifact` reference requires `id`, `kind`, `label`, `title`, `runId`,
`artifact` and `sha256`; the run must match `source.runId`. Artifact identifiers
are bounded JSON/Markdown/CSV basenames, optionally under `tables/`. They remain
provenance text, never workspace hyperlinks or automatically copied files.

Tables may declare one to three `rowFilters`, each with a declared column `key`,
reader-facing `label` and optional scalar `defaultValue` found in its saved rows.
Filter keys are unique. Selection preserves exact saved cells and order,
including distinct string/number/boolean values, nulls and zero rates. Initial
rendering applies only the explicit defaults. A reader explicitly presses
**Load table filters** to download other saved rows for choices and 100-row
pagination; mounting a table does not initiate that download. Multiple tables
share one static publication-JSON request per report. The browser never calculates
rates, recomputes denominators or combines populations.
Until loading succeeds, controls are disabled and authored defaults remain
visible. Failure offers retry and the saved JSON link. Without JavaScript,
the default rows and declared evidence downloads remain available.

### Compact static delivery

After the static export, `scripts/optimize-static-json.mjs` minifies only the
selected `out/publications/<id>/report.json` files. The authored/public canonical
bundles keep their existing bytes, IDs and canonical report-content hashes.
Every exported object must equal its canonical input, and the export verifier
requires the exact compact serialization; all report text, table cells, nulls,
units, row order, references, provenance and asset declarations are preserved.
CSV and figure bytes and the publication index remain unchanged.

The transform is confined to generated output, rejects linked or overlapping
source/output paths, and is repeatable. New release metadata records
`abacus.static-json-delivery/v1` with each canonical file hash/size and delivered
file hash/size. Existing source-content hashes identify the canonical report;
the release inventory identifies the actual compact bytes served by the host.
This formatting transform does not create a new research result or rewrite an
old publication or release record.

## Selected summary downloads

Version 1.1 permits up to four explicitly declared UTF-8 CSVs under
`downloads/<safe-filename>.csv` beside `publication.json`. Each declaration has:

| Field | Required meaning |
|---|---|
| `id`, `path`, `label`, `description` | Unique download identity/path and useful reader-facing explanation |
| `population`, `units`, `scope` | Cohort, units and selected rows; disclose any additional rows beyond the page |
| `mediaType` | Exactly `text/csv` |
| `columns`, `rowCount` | Ordered unique header keys (1–24) and exact data-row count (1–1,000) |
| `sha256` | SHA-256 of the exact selected CSV bytes |
| `source.runId`, `source.artifact`, `source.sha256` | This report's source run, selected `tables/<filename>.csv` and saved-source hash |

Select rows/columns in a presentation producer outside Narada. Preserve original
CSV strings and blank-cell meanings; preserve numeric ratios, flags and units.
Do not copy the full summary by default or include event ledgers/private locators.
Record every selected cell and selector in the export source map. The authoring
check must compare those cells and the declared source hash with the saved artifact.
Narada checks declared source identity/hash syntax and selected-file content; it
never reads the analytical source file, so publisher validation alone does not
prove the source-cell transfer. Keep this distinction in verification records.

Limits are **256 KiB per CSV and 512 KiB total per publication**, separate from
the unchanged 2 MiB/image and 8 MiB figure budgets. They permit useful summary
projections while bounding accidental exports and browser transfers. The publisher
checks exact CSV headers, row count/width, valid UTF-8, well-formed comma/quote
structure, cells of at most 1,000 characters and content hashes. Control characters
and spreadsheet formula cells are rejected; signed numeric/scientific values are
permitted. Unsupported extensions/media types, missing files, traversal, symlinks
(including parent directories), oversize files and hash mismatches fail before
staging. No general download endpoint exists.

Explicitly filtered reports have conditional selected-download bounds of
4 MiB per CSV, 8 MiB total and 15,000 rows. Four files, 24 columns, safe paths,
UTF-8 parsing, cell/formula rules and exact provenance/hash requirements remain.
Reports without declared row filters retain the ordinary limits above. These
saved summary projections remain explicit publication assets; raw events and
workspace files do not cross the boundary.

The publisher copies only declared figures and CSVs. Authoring notes, source maps,
manifest snapshots and unrelated revision files stay outside public output. CSV
links have their selected filename and a native download attribute. Static preview
serves CSV as `text/csv; charset=utf-8` with attachment disposition and `nosniff`.
Other hosts must preserve sensible static-file handling; the release workflow tests
the actual host's headers and download behavior. The build verifies staged and exported
asset hashes/budgets, download links/filenames and source-reference anchors.

For changes to these capabilities, use temporary fixtures for compatibility and
rejection tests, run verify/test/lint/build, then inspect generated `out/` at desktop
and mobile widths. Check visible context, keyboard table scrolling, full-size
figures, references, downloaded filenames/bytes, old report routes and featured /
previous navigation. Keep source-cell, browser and preservation records in the new
revision. Static tables and figures currently solve the selected reader needs;
there is no client-side analytical selection or calculation.

## Study catalog

Narada owns the explicitly authored [study catalog](../apps/narada/content/studies.json)
and its [schema](../apps/narada/contracts/studies.schema.json), types and validator.
It maps stable study IDs/slugs to selected publication IDs and asserted source-run
IDs. Public titles, scope, products and evidence wording are selected explicitly;
these fields do not replace study research metadata. No build reads `studies/`
or `runs/`, and no timestamp chooses a featured report.

The library links every catalog entry to `/studies/<slug>/`. Each study links to
its featured `/reports/<publication-id>/` and optional labelled related reports.
`other-run` and `exploratory-supplement` use distinct source runs;
`presentation-revision` shares the featured run. Publications belong to one study;
a cross-study overlay keeps its own study/run and names upstream sources in prose.
Older revisions remain accessible with their catalog relationship label and a
featured-publication link. Report bodies are rendered once by existing sections.

Optional `publicationTabs` group two to twelve parallel saved reports from the
same source run. Each explicitly selects a publication/run ID and unique label;
the featured publication must be first. Explore lists the selected views, and
ordinary report-route links styled as tabs select sibling
reports, whose pages mark the current selection and retain the study link. This
supports chart-specific reports without study-specific routes or client-side
statistics. Tabs cannot repeat a related publication; omitted tabs retain the
existing overview layout and featured-card behavior.

Optional `analyses` replaces top-level `publicationTabs` for two to eight
distinct analysis groups. Each group declares a unique `id` and `label` plus
one to twelve report `publicationTabs`, all from one source run. A singleton
group can retain an earlier saved baseline without fabricating a sibling report.
Groups can use
different source runs; the first group/tab must match the featured selection.
All publication selections remain unique across the study and cannot repeat
related selections. Route links preserve a matching chart label when switching
analyses, with the first chart as an explicit fallback. The study page includes
every selected immutable chart route in its browse control. Attribution, private
source auditing, local smoke and static export checks consume this same authored
selection without discovering research files.

Optional `phaseFamilies` replaces both `analyses` and top-level `publicationTabs`
with two to four authored phase containers. Each family declares a unique study-
local `id` and `label`, plus one to eight existing-shaped analysis groups. Each
analysis retains one to twelve report tabs from a single asserted source run;
a family can include separately attributed earlier runs in distinct analyses.
Analysis IDs and labels are unique within their family. Publication selections
remain unique across the entire study, including related reports. The first
family/analysis/tab must match the featured publication and source run.

Phase, condition and chart navigation uses ordinary report route links. Switching
phase preserves a matching condition ID when available, then a matching chart
label; absent matches fall back to the first authored condition or chart.
Condition navigation is scoped to the current family. The study browse control
retains every phase's immutable report links. Classic catalogs remain unchanged
when this optional container is absent. Shared selection helpers supply route
attribution, private audits, local smoke, inventories and static-export checks;
no research data or phase name is inferred by the app. These bounded navigation
containers do not change report, table, selected CSV or static-page budgets.

Optional `overview` metadata supplies an app-owned research brief in the existing
catalog: question, takeaway, evidence type, population, period/sample scope,
selected highlights, findings, limitations, method context and supporting report
links. It abridges saved conclusions without changing research interpretation.
The [overview resolver](../apps/narada/scripts/lib/study-overviews.mjs) checks each
supporting publication/run/content-hash/section identity against selected staged
bundles. Numerical highlights select an exact metric label or a single table cell
with a unique typed row selector. The saved value, format, precision, units and
notes are copied without aggregation; null, false and zero remain distinct.
Supported authored scope facts replace metrics where appropriate, including
qualitative reviews. Missing, ambiguous or stale references fail verification.
An optional `methodSource` selects a separately pinned method section; otherwise
method context links to the brief's supporting source. It uses the same identity
and destination checks as other overview sources.

These briefs and library cards render as static HTML. They do not fetch report
JSON in the browser or carry full report tables in overview navigation state.
All catalog entries expose Overview at `/studies/<slug>/`, then `/findings/`,
`/explore/`, `/methods/` and `/evidence/` beneath that study. The shared shell uses
native links and one current-page indication. Each destination has a distinct role;
none mounts hidden report bodies. The 22-study verified published collection has
reviewed briefs; two additional local entries retain metadata-based fallbacks in
the same shell. Catalog presence and this local rollout do not authorize production
selection or deployment.

Explore keeps every selected immutable report reachable through the supplied
phase/analysis/view hierarchy and preserves related-publication relationships.
Evidence groups existing selected CSVs, references, content hashes and source-run
identities by saved report, without combining populations. Methods link directly
to pinned saved scope. Reports retain their own phase/analysis/product/chart
navigation, contents and provenance, with routes back to Overview and Explore.

The app-owned [route projection](../apps/narada/scripts/lib/study-routes.mjs) supplies
all five destination paths to export verification, preview smoke and current
release adapters. Frozen historical release inventories remain unchanged. Run the
normal bounded smoke and `npm run smoke:preview -- --origin
http://127.0.0.1:4173 --all-routes` against a running local preview to check the
complete exported page inventory; neither creates a release.

Legacy study fragments retain anchors that reveal visible links to their exact
saved report sections through CSS `:target`. This covers sections, headings,
downloads, references, notes and used pattern keys without a JavaScript redirect.
The earlier overview section anchors remain navigation previews. The full library
preserves catalog order and its explicitly curated four starting points. None of
this changes report identities, source hashes, saved evidence or release records.

After staging a new immutable report through the publisher, edit only this
catalog to feature it or add a related reference. Keep study slugs stable. Run
`npm run verify`, `npm test`, `npm run lint`, `npm run build`, then static preview
checks. The validator rejects missing references, repeated identities/relationships,
incorrect source attribution, unsafe fields and private path references. The
static verifier checks homepage study links, study routes and every selected
publication route. Catalog edits affect navigation, not research references or
publication hashes. Current limits are 200 studies and 512 KiB of server-owned
catalog JSON, including bounded generated editorial explanations. The separate
client discovery index remains bounded at 48 KiB.

## Research-priority ownership and projection

Sahadeva owns the current [research-priority registry](../strategies/research-priorities.json)
and [rubric](../strategies/research-priority-rubric.md). Narada presents their
bounded saved projection in its existing catalog; it does not infer ratings from
reports, evidence-status prose, filenames or statistical significance. The label
means how strongly saved evidence supports focused investigation toward an
actionable material edge. Stars are not profit probabilities, paper-quality
ratings or recommendations. Not assessed, Needs review and Not applicable are
nonnumeric states. Display reviewer/date and preserve the AI-assisted review's
pending human approval.

The explicit standard-library
[projector](../scripts/project-research-priorities.py) reads only the declared
registry, rubric, catalog and selected public bundles. Run it from the root:

```sh
python3 scripts/project-research-priorities.py --check
python3 scripts/project-research-priorities.py --write
./scripts/check-workspace --profile research-priority
```

`--check` validates exact report/run/content/section bindings and projection
freshness without writing. `--write` changes only generated `researchPriority`
fields and the public rubric; authored navigation, selections and reading paths
remain in place. The app's verify/build independently validates app-owned saved
bindings without importing Python, the registry, private locators or research
directories. Keep local `reviewedMaterials` and review notes out of the public
projection, and keep rationale/evidence arrays out of client discovery props.

An assessment pins authored scope, the complete ordered selected-report set and
rubric bytes. A still-valid dated judgment becomes Needs review when those
bindings change; do not automatically upgrade it or silently refresh hashes.
Missing/bad public identities are errors. For relevant unprojected findings or
decisions, Sahadeva explicitly uses `--mark-needs-review STUDY_ID --reason "..."`
then `--write`, retaining the old score/date as historical context. Reassessment
requires reading the new supporting and contrary evidence and a new dated
assessment ID. Preserve approved previous judgments in repository history;
never alter sealed runs, original report content or historical release records.
The separate `--check-reviewed-inputs` action audits only explicitly recorded
local material hashes; a source-only clone may lack those retained inputs. It is
not part of ordinary metadata validation or the app build, and does not execute
research or establish scientific validity.

Cards and study overviews retain useful explanations and ordinary links to
supporting and contrary report sections without fetching table JSON. The
optional library `priority` filter accepts integers 1–5 or the three nonnumeric
states; repeated choices use OR within the category and AND with other criteria.
`sort=priority` orders current numeric assessments highest first, preserves
authored order for ties and places nonnumeric states afterward. Needs review
uses no active numeric score. Default order stays authored, and static/no-JavaScript
browsing retains the complete collection and rendered explanations. Examples:
`/?priority=2&instrument=gc`, `/?priority=needs_review`, `/?sort=priority`.

## Library discovery and report reading

Discovery remains an enhancement to the complete static collection. The
[small index projection](../apps/narada/src/lib/discovery.ts) uses only authored
title, question, summary, takeaway, topic, instruments and optional study
`keywords`. It does not read report tables, bodies, research files or private
locators. Every card and study link renders without JavaScript; enhancement
controls are disabled with a no-JavaScript explanation. Search matches every
normalized substring term across the authored fields, ignoring case, accents,
punctuation and repeated whitespace. Filters use OR within a category and AND
between categories, alongside search; authored ordering is preserved. Evidence
type comes only from explicit validated overview metadata, and missing values
remain unclassified.

`q` plus repeated `topic`, `instrument`, `type` and `priority` parameters share the library
state. They are validated against current catalog-derived choices and canonicalized.
Limits are 120 query characters, eight selections per category and 2,048 encoded
query-string characters including `?`. Unknown/stale parameters and duplicate
choices are ignored; oversized input restores the browseable default. Reset
removes discovery parameters. The first query edit pushes a history entry and
continued typing replaces it until blur; selection/removal/reset actions push
separate entries. Back/forward and refresh restore state. Typing preserves input
focus. Examples are `/?q=VWAP&instrument=gc` and
`/?topic=range+xv&instrument=nq`.

Optional `keywords` are one to eight trimmed plain-text values of at most 60
characters, unique without case distinctions. Optional top-level `readingPaths`
uses the same authored catalog, not a second registry. Each of up to six paths
has a title, explanation, qualification and two to six distinct existing-study
steps. Each step declares a valid study destination and a reason. The validator
checks references, uniqueness, bounds and safe text. Current authored paths
connect VWAP, Range XV and session/event questions. Reading order preserves each
study's evidence limits, negative findings and separate populations; it does not
imply replication or a pooled result. [ReadingPaths](../apps/narada/src/components/reading-paths.tsx)
renders ordinary study links and shareable homepage anchors, with qualifications
visible beside the related questions.

The [contents component](../apps/narada/src/components/report-contents.tsx) passes
only section identities/titles to the client, rendering both a desktop rail and
native mobile disclosure. Its current-section marker changes presentation only;
it does not mutate history or scroll. [Section links](../apps/narada/src/components/section-link.tsx)
are server-rendered native `#section-<id>` permalinks at each heading. Clipboard
copying is shared by the desktop rail and mobile disclosure, targeting the
currently tracked section and showing its title. Per-heading client components
and props are unnecessary; native links remain available without the enhancement.
Report bodies and order, existing anchors, figures, captions, alt text,
download paths and provenance remain saved inputs. Essential download scope,
units, population and source/run identities stay visible. Full report hash records
remain in technical disclosures. Compact study Evidence directories link each
download/reference to its exact immutable `#download-<id>` or `#reference-<id>`
record, preserving every pin without repeating dense technical markup. Essential
qualifications remain visible. External references and saved artifacts are labelled
distinctly.

[Table sharing](../apps/narada/src/lib/table-share.ts) identifies the immutable
report in its path, the saved table with `table`, and typed display-filter values
with URL-encoded `filters` JSON. Limits are 4,096 query characters, 2,048 filter-JSON
characters and three declared row filters. Values preserve null, false, zero and
string distinctions; the explicit All values selection differs from a missing
authored default. Generated selected-row links validate against the loaded saved
table. Opening a shared link leaves pending selections and authored default rows
visible until the reader presses **Load table filters**. No report JSON is fetched
just to restore the URL. After success, valid saved values apply; stale values
are explained and defaults remain available. An already loaded table can apply
a new pending link explicitly. Pagination stays at 100 rows, requests remain
shared per report, and failures retain defaults and retry. Sharing/filtering
selects saved rows without recalculating statistics.

The [reader styles](../apps/narada/src/app/reader.css) and
[table styles](../apps/narada/src/app/table-reader.css) provide print layouts for
study summaries and reports. They retain findings, qualifications, captions,
notes, evidence references and source identity while removing navigation and
controls. Printed tables identify the actual displayed slice/page and selections,
matching-row count and selected-table total; they do not claim complete-dataset
coverage. Printing never fetches more rows. Browser print-CSS layout checks and
native paged print/PDF inspection are distinct: a screen QA wrapper does not
verify native pagination. Use the [app maintenance map](../apps/narada/README.md#maintenance-source-map)
for focused discovery, reading-path, reader, and table-sharing tests. Record actual
browser checks, request/index/JavaScript measurements and integrity comparisons;
these are independent of research revalidation and hosted release authorization.

## Workflow

From `apps/narada`, using Node 24:

```sh
npm ci
npm run report:publish -- --report ../../runs/<study-id>/<run-id>/publication.json --dry-run
npm run report:publish -- --report ../../runs/<study-id>/<run-id>/publication.json
npm run verify
npm test
npm run lint
npm run build
npm run preview
```

`--dry-run` validates the proposed input without publishing it. Review the
report content and selected assets before staging. Keep staged bundles in Git
so the deployment build can use them without access to local research data.

The authored [study catalog](../apps/narada/content/studies.json) defines the
current selected library. The [Phase 3 record](narada-publication-plan.md#phase-3-completion-record)
documents that phase's library, including the retained Phase 2 pilots. `npm run report:example` explicitly stages
the illustrative report in `examples/report.json`; it is for trying the
publication flow and is not research evidence. Running a normal build does not
publish the example.

`preview` serves only the static `out/` directory at `http://127.0.0.1:4173`.
Set `PORT` to use another port, for example `PORT=4174 npm run preview`. The app
README is the command reference. Research checks continue to run separately
through the workspace's existing scripts.

## Local maintenance verification

Use the [app command reference and source map](../apps/narada/README.md#maintenance-source-map)
for maintained owners and focused synthetic tests. `npm run lint` includes
`src`, `types`, `scripts`, and `tests`, with Node configuration scoped to `.mjs`
operations/tests and historical/generated snapshots excluded.

The verification claims are separate: `verify` checks staged app inputs; build
and its postcheck check generated static output; `npm run smoke:preview --
--origin http://127.0.0.1:4173` checks an explicitly running local preview's GET/HEAD
bytes, headers and 404s. Inspect desktop/mobile layout and real interaction in a
browser separately. These checks are Python-independent and use no private
release-source locators. They do not prepare a release or establish hosted gates.

`npm run audit:sources` separately reads the explicit private mapping and retained
source/revision files. Safe checked reads precede parsing, and declared source/output
identities require SHA-256 pins. It preserves accepted passed records, qualified
superseded presentation records, nonempty all-passed checks-only records, and the
inherited Phase 2 content-verification fallback. The fallback's consumed bytes are
hashed; its historical application/browser qualification is not a new browser
verification. Explicit failures cannot be rescued by unrelated positive checks.
This is read-only integrity and attribution auditing, without source-cell
reconstruction, statistical revalidation, race-free reads, or transactional guarantees.

Every private mapping entry selects exactly one `revision` under
`reports/exports/<study>/<run>/<revision>` or `run` under `runs/<study>/<run>`.
New runs may publish the source prepared before sealing directly. They retain a
separate `publication-manifest.json` with `publication_id`, `source_run_id`,
`study_id`, `source_artifacts` and `outputs`. Each artifact/output entry has an
exact workspace-relative `path` and `sha256`. Required declared outputs are
`publication.json`, `source-map.json` and `publication-verification.json`; all
selected assets are checked against their publication hashes. The generic verification
record uses `result: "passed"`, or omits `result` and contains a nonempty `checks`
array whose objects each have `passed: true`. A bare `status: "passed"` or
`checks[].status` does not satisfy this generic gate. The namespaced independent
receipt format below has separate identity/hash requirements. No historical
fallback or superseded-presentation status applies to a direct run.
The ordinary `manifest.json` must exist with matching `study_id` and `run_id`;
the audit retains its hash without validating the research contract or rerunning
the study. Later presentation changes still require a separate revision and new
publication ID. No sealed run is edited by this read-only audit.
For multiple reports prepared before sealing the same run, the mapping may add
`publicationDirectory`, exactly `publications/<publication-id>`. The per-report
`publication.json`, `publication-manifest.json`, `source-map.json`,
`publication-verification.json`, figures and downloads reside there. Declared
source/output pins remain workspace-relative. The audit checks the run's ordinary
`manifest.json` at the run root separately. This field is allowed only with
`run`; it cannot select arbitrary directories, another report ID, a presentation
revision or a deeper path. Existing root-level run sources retain their behavior.

New version-1 independent publication receipts may use a namespaced
`*-publication-independent/v1` schema and `status: passed`. This is accepted only
for sealed runs with matching publication and source-map identities and exact
report/map hashes, plus a passing run-level `*-independent-publication/v1`
receipt that pins the publication manifest, per-publication receipt and retained
checker snapshot. Bare status values, other schema versions, stale hashes and
wrong run identities fail. This verifies recorded metadata and bytes; it does
not repeat the research or source-cell calculations.
The content comparison preserves canonical JSON's `-0` to `0` numeric
serialization; retained source/output bytes still require exact SHA-256 pins.

Future study 08/09 revision manifests can declare exporter/helper source snapshots
and their compact inventory as ordinary retained outputs. Generic output-pin checks
cover those bytes without importing Python or discovering producer dependencies.
Existing revisions need no new snapshots or schema fields. Keep maintenance
findings outside existing release histories; hosted verification needs separate
release authorization and actual hosted checks.

## Vercel configuration

The [release workflow](../apps/narada/releases/README.md) builds locally with
Node 24 and the npm lock, then packages `out/` into an isolated Vercel Build Output
API v3 payload. The dedicated `brew-vee/abacus-narada` project serves that payload
with no Git connection, framework, installation or remote build. The app-root
source-build configuration is not used for upload.

`npm run release:prepare` verifies/tests/lints/builds and records a unique release
under `apps/narada/releases/`. It freezes routes, publication/asset checksums,
catalog/lock/tool/dirty-source identities and retained source-map checks. Payloads
and separate reconstruction snapshots stay ignored under `.release-artifacts/`;
private release records and research sources never cross the upload boundary.
Preparation and ordinary builds do not deploy. Explicit deployment commands bind
and verify the target, upload a preview, stage production without domain assignment,
verify served bytes and promote the checked production deployment. Public production
access and real 404 behavior must pass independently of authenticated preview access.
The guide owns current/previous target records, retention, updates and rollback.

## Reuse decision

Narada carries forward useful generic ideas from `abacus-board`: explicit
publication inputs, bounded reports, source hashes, small presentation
components, and a static export. Its report contract and navigation serve the
new Abacus workspace. Old study-specific routes, schemas, conclusions, and the
separate research backend are not part of this component.
