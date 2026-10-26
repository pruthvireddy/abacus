# Web study report authoring template

Template version: `web-study-report-1.1` · Supported Narada source contracts: `1.0` / `1.1`.
Use this for selected presentations of saved evidence. The
[publication plan](../docs/narada-publication-plan.md) owns the study inventory,
source-selection decisions, and pilot assignments. This document owns the reading
order and authoring checklist. It is an authoring aid, not a Markdown importer or
an implemented report generator.

Follow the [artifact conventions](README.md), [architecture](../ARCHITECTURE.md),
and [publication workflow](../docs/narada.md). The authoritative fields are in
Narada's [report schema](../apps/narada/contracts/report.schema.json) and
[types](../apps/narada/types/report.ts). Do not add fields to that contract to
match this worksheet.

## Authoring worksheet

Replace placeholders; omit optional evidence sections that do not help the reader.
The six reading stages below can occupy several ordered Narada sections. Every
section needs a unique lowercase hyphenated `id`, `title`, and supported `kind`.
Text is plain prose: the renderer splits blank-line-separated paragraphs; it does
not interpret Markdown, HTML, lists, or embedded links.

| Identity | Fill in before authoring |
|---|---|
| Study | `<study_id>`, registered title, topic, products |
| Evidence status | Exact registered wording and the selected run's qualifications |
| Selected source | `<source_run_id>`; registered reference or explicitly proposed/selected publication source |
| Presentation revision | `<unique_revision_id>` under `reports/exports/<study-id>/<run-id>/<revision-id>/` |
| Publication | New lowercase hyphenated `id`; `publishedAt` in valid UTC ISO form ending in `Z` |
| Producer | `source.producer`, normally `sahadeva`; `source.runId` is the actual analytical/source-review run, not the export revision |
| Title | `<specific question or result, with product/context where useful>` |
| Summary | `<scope + supported finding + material qualification>` |
| Source map | Paths, hashes, row/metric/claim IDs, units, transfer operations, and checks |

### 1. Study question and scope

Suggested section: `question`, `kind: text`.

`<What question was investigated? What products, dates, contexts, and observation
units does this publication cover? Which protocol and source run support it?>`

State the evidence status early. A broad study may contain both tested questions
and unexecuted proposals: name the selected scope. Keep study status (for example,
completed) distinct from evidence strength (for example, descriptive or unverified).

### 2. Findings supported by the selected evidence

Suggested section: `findings`, `kind: text`.

`<Give two to four substantive findings from the saved report. Identify the
supporting metric/table/claim IDs. Preserve negative and inconclusive findings
and qualifications that change the conclusion.>`

Do not turn a planned study into an executed finding, a conditional path rate
into a trade win rate, or a source-review example into a performance record.
Use the saved conclusion; changed interpretation requires a new research run.

### 3. Selected key evidence

Use only the evidence that explains those findings. Optional subsections:

- `key-metrics`, `kind: metrics`: a few numeric estimates with units and notes
  containing numerator/denominator, horizon, cohort, uncertainty, and source ID.
- `primary-evidence`, `kind: table`: readable selected rows/columns with counts,
  comparison values and saved intervals where applicable. Use 1.1 `description`
  and `notes` to explain denominator, selection and uncertainty beside the table;
  1.0 needs a preceding text section.
- `evidence-figure`, `kind: figure`: selected raster asset, descriptive alternative
  text, and a caption stating population, meaning, source, and limitations.
- Further text/table/figure pairs when needed, each with a distinct section ID.

`<Explain why these rows or figures were selected. Preserve outcomes that oppose
the headline, including failures, ambiguity, timeout, no-trade, and target shortfall.>`

### 4. Definitions and methods needed to read the results

Suggested section: `definitions-methods`, `kind: text`; optional definition table.

`<Define the setup, observation, decision time, outcome, units, horizon, source
coverage, exclusions, and comparisons. Explain only the methods needed to interpret
the selected results; reference the saved protocol for the complete method.>`

Use the quantitative or qualitative variant below. The same four section types
serve both; metrics and charts are optional.

### 5. Limitations and uncertainty

Suggested section: `limitations`, `kind: text`.

`<What does this evidence establish, what remains uncertain, and what was not
tested? Explain source limits, dependence, missingness, retrospective eligibility,
prior outcome exposure, and execution limitations when applicable.>`

Keep a negative result visible alongside any favorable descriptive pattern.
An interval spanning zero remains inconclusive. “Locally verified” describes the
saved checks, not independent replication, an untouched holdout, or profitable use.
Historical imports retain “unreviewed during consolidation.”

### 6. Source-run and publication provenance

Suggested section: `sources-provenance`, `kind: text`; optional source table.

`<Study ID; actual source run ID; executed protocol; presentation revision and
template version; selected source-artifact references; checks; publication date.
For an external source, include creator/title, URL, access date, and relevant
timestamps. Explain which dates describe execution, source events, and publication.>`

The built-in Publication record displays producer, run ID, canonical report hash,
and selected asset hashes, plus links to the generated JSON and assets. Version 1.1
references/downloads also carry explicitly authored saved-source hashes. The complete
analytical provenance and presentation manifest remain local. Record those in
the export manifest and authoring source map; include useful identifiers in plain
text on the page. A filesystem path is a traceability identifier, not a working
public download link. Omit machine-specific absolute paths from public prose.

Optional top-level `notes` hold short qualifications. Do not rely on collapsed
provenance or final notes for a qualification required to understand a headline.

## Quantitative variant

Use this checklist within the six stages:

- Define the event/setup and when it becomes observable. Preserve `available_at`,
  completed-bar versus intrabar distinctions, reference entry, and signal/touch-bar
  exclusions. Use the selected run's definitions, not a later study plan.
- State population and coverage by product, dates, anchor/window, timeframe, side,
  cohort and chronological split as applicable. Say when 2026 is YTD. Keep correlated
  views separate from independent observations.
- State numerator, eligible denominator, event/session/week counts and exclusions.
  Distinguish candidate events, evaluable outcomes, conditional subsets and common
  opportunity sets. Give different horizons their own denominators.
- Preserve units and horizons: minutes versus physical candles; points versus ticks,
  sigma or fixed quote equivalents; frozen versus evolving reference. MAE/MFE are
  separate extrema with unknown ordering unless the source resolves it.
- Carry saved interval endpoints and their confidence/dependence method, support
  flags and sparse/degenerate qualifications. Do not compute new intervals or
  aggregate rows during publication.
- Identify the baseline/control and common-support limits. Preserve paired versus
  unpaired comparisons, adjustments, familywise versus pointwise intervals, and
  competing classes. Never silently use 50% as the baseline for unequal targets.
- Explain whether results are behavioral/path descriptions, gross price proxies,
  assumed-cost sensitivities, or an actual execution model. State fills/costs that
  remain unmodeled; do not infer net profitability from a hit rate or MFE/MAE.
- Preserve exploratory, retrospective and holdout qualifications. A protocol frozen
  before this calculation can still use previously viewed history.

## Qualitative and source-review variant

Use this checklist within the same six stages:

- Identify source creator/title, source identity/URL, publication and access dates,
  reviewed duration, captions/transcript type, selected example period, and capture
  timestamps. Keep source publication time, media time and chart clock distinct.
- Describe the reviewed scope and observation units; selected examples from one week
  are not independent trades or a complete opportunity population.
- Attribute each claim to the source, each chart observation to its saved capture,
  and each interpretation to the saved reviewer assessment. Preserve their distinct
  evidence labels and stable claim/chart IDs.
- Explain what the examples illustrate and what remains unverified: definitions,
  original forecast timestamps, fills, trade records, universality, and profitability.
- Select figures that explain the process and its failures/abstentions. Caption with
  creator, source identity, media timestamp, chart context and interpretive limit.
  Alternative text describes what is visible; it does not authenticate a claim.
- Preserve original annotations and disclose any crop/resize/compression in the
  export manifest. Do not invent prices, redraw implied future outcomes, or use an
  AI-generated chart as a substitute for the source capture.
- Optional tables may show vocabulary, sequence, claims or coverage. Omit statistical
  scorecards. Saved source-coverage counts are not evidence of effectiveness.

## Field mapping and authoring rules

| Page element | Current schema location | Authoring rule / current gap |
|---|---|---|
| Page identity and summary | `id`, `title`, `summary`, `publishedAt` | ID ≤80 characters; title ≤160; summary ≤800. New content uses a new ID. Do not imply study completion date is web publication date. |
| Run attribution | `source.producer`, `source.runId` | No structured study, topic, product, protocol or export-revision fields; explain them in text. |
| Reading order / contents | Ordered `sections[]` with `id`, `title`, `kind` | Renderer derives the contents links; maximum 30 sections. |
| Question, findings, methods, limitations, references | `kind: text`, `body` | Maximum 16,000 characters per body. Use blank lines for paragraphs; body citations are plain text; 1.1 `referenceIds` link to structured references. |
| Key estimates | `kind: metrics`, `items[]` | 1–24 items; numeric/null `value`, required `format`; optional `unit`, `precision`, `note` (≤600 characters). Denominators/intervals go in notes or a table. |
| Evidence and definition tables | `kind: table`, `columns[]`, `rows[]` | 1–12 columns; 0–100 rows. Column `key` is a unique identifier; `label` explains meaning; numeric formats require numbers/null. 1.1 adds optional `description`, `notes` and `referenceIds`. |
| Evidence figure | `kind: figure`, `path`, `alt`, optional `caption` | Regular file at `figures/<filename>.png`, `.jpg`, `.jpeg` or `.webp`; no SVG, HTML, GIF, remote asset or symlink. `alt` ≤500 characters; caption ≤1,000. |
| Additional qualifications | `notes[]` | Up to 20 plain strings of ≤1,000 characters. |
| Generated publication record | Bundle `provenance.sourceSha256`, `provenance.assets[]` | Publisher supplies canonical JSON/asset hashes; author must not fabricate them. Analytical provenance remains in the export manifest. |
| Source references (1.1) | Top-level `references[]`, section `referenceIds[]` | Up to 20 typed external or saved-artifact references; identifiers resolve to visible attributed entries. See the [contract guide](../docs/narada.md#evidence-contract-11-and-compatibility). |
| Selected CSVs (1.1) | Top-level `downloads[]` | Up to four explicitly selected local CSVs; label, description, population, units, scope, headers/row count, content hash and source identity/hash are required. |
| Study navigation / related publications | App-owned `content/studies.json` | Already supported; author the catalog after staging. No report field or workspace scan. |

Titles identify the question or saved result without advertising an edge. Summaries
stand alone on a library card: include product/context, the finding and its strongest
qualification. Keep product/side/cohort names consistent with the source.

For table labels, expand opaque identifiers into readable terms without changing
their definition. Specify whether counts are events, sessions or original
opportunities. Keep a local mapping back to every source key. Counts normally use
`format: number`, `precision: 0`; rates and intervals normally use `format: percent`
with an explicit precision. The renderer defaults to two decimals when precision
is absent; choose a precision appropriate to the source rather than implying extra
accuracy.

`percent` takes ratios: `0.42` renders as `42%`. A source stored as `42` percent
requires a documented division by 100 for presentation. A ratio difference of
`0.014` displayed as `1.4 pp` requires a documented multiplication by 100,
`format: number`, and `unit: pp`. These are unit conversions, not new estimates.
A unit label alone never scales a value. Do not clamp a saved contrast to [0,1].

Use explicit `null` for unavailable values; the renderer displays “Not available.”
Distinguish zero successes with an eligible denominator from no eligible cases.
Keep undefined, false, not tested and not observed separate in the surrounding
text or a status column. JSON cannot contain NaN/Infinity. An omitted table cell
also displays as unavailable, but explicit null plus an explanation is clearer.

Figure captions must explain axes/units, cohort, deadline and uncertainty for plots,
or attribution/timestamp and evidentiary limits for source captures. Alternative
text should describe the information conveyed without repeating an entire caption.
Color must have visible labels and an accompanying textual explanation. Rasterize
existing SVGs faithfully; do not recalculate their data to improve the illustration.

## Version 1.1 evidence context and selected downloads

Choose 1.1 only when using its fields; old 1.0 sources remain valid. Each revised
report has a new publication ID and export revision. For a table, supply a short
`description` and up to six `notes` explaining denominator, horizon, comparison,
uncertainty and missingness. Attach limitations to the table they govern.

Use `references` for established sources. An external reference records creator,
title, meaningful label, HTTPS URL, publication/access dates and optional media
start/end seconds. A saved-artifact reference records this source run's identity,
artifact identifier and hash. Section `referenceIds` resolve to those entries;
local artifact paths never become hyperlinks. Keep claim attribution visible in
prose as well as in references. A linked source does not independently verify its
claims. Do not investigate new external material during presentation preparation.

For each CSV, author the required declaration in the
[download contract guide](../docs/narada.md#selected-summary-downloads). Create
`downloads/<filename>.csv` from exact selected saved rows and columns, with their
original strings, ratios and blank meanings. Explain population, units, scope,
source and any rows added beyond the page. Record the selection and every output
cell in the source map; check against the saved source before publishing. Hash both
the source artifact and output. The publisher checks declared hashes and CSV
structure, rather than opening the research artifact to validate your selection.

Use at most four UTF-8 CSVs, each ≤256 KiB, total ≤512 KiB, 1–1,000 data rows,
1–24 unique declared columns and cells ≤1,000 characters. Formula cells and
unsupported formats are rejected. Preserve null/empty meanings with explicit
context, including empty support flags versus unavailable estimates. Selected
CSV budgets are separate from figure and JSON budgets. Keep the full research
grid, event ledger, source archive and authoring files outside public output.

Check actual downloaded bytes and filename, visible units/scope and keyboard
access in the generated static preview. References need safe links, working
section anchors and accurate saved media ranges. Figures link to full size;
check that small-screen readers can inspect the labels and captions. Static
views are sufficient unless selecting saved views would materially help the
reader; introducing analytical computation is outside publication scope.

## Source map and presentation manifest

Maintain this worksheet beside the export, outside `publication.json`:

| Output section / value / figure | Source path + SHA-256 | Saved selector / ID / field | Original unit → displayed unit | Presentation operation | Check and outcome |
|---|---|---|---|---|---|
| `<section/row/column>` | `<workspace-relative artifact + hash>` | `<exact row key, metric ID, claim ID or chart ID>` | `<unchanged or explicit conversion>` | `<copy, select, format, rasterize>` | `<source equality, rounding, visual check>` |

Record study/source-run/revision/publication identities, UTC creation time, every
consumed source path/hash, exact authoring/render/export command, tool/code revision
and dirty script snapshot where needed, template version, presentation changes,
checks and results, and output paths/hashes in `manifest.json`. Exclude the
manifest's own hash. This follows the existing human-authored revision convention;
there is no generic machine-validated presentation-manifest schema.

Transfer saved numbers by stable selectors, keeping full precision in JSON and
rounding only in display. A presentation script may select columns/rows, apply
documented unit conversions and serialize saved values. It must not rerun a study,
calculate new statistics, recompute uncertainty or silently combine cohorts.
Check each displayed value and interval against its selected saved cell and each
statement against the saved report. Record discrepancies for source review rather
than resolving them with new calculations.

## Delivery checklist

- [ ] Source selection is explicit; registered reference selections and study
  metadata remain unchanged. Supplemental sources are identified separately.
- [ ] Six reading stages are covered; optional metrics/figures are omitted when
  inappropriate. Findings and contrary evidence retain their saved meaning.
- [ ] Definitions, denominators, units, horizons, uncertainty and evidence status
  remain attached to the values they qualify.
- [ ] Every selected item has a checked source mapping; public prose has no stale
  filesystem hyperlinks or machine-specific paths.
- [ ] Publication source ≤96 KiB; generated bundle ≤128 KiB; selected images ≤2 MiB
  each and ≤8 MiB total. Table/section/string limits above are satisfied. Measure
  final bytes; source artifact sizes do not establish output compliance.
- [ ] Selected CSVs meet the separate budgets, declare provenance, and pass exact
  source-cell/header/row/hash checks; actual downloads have been inspected.
- [ ] Figures have readable labels, alt text and captions; selected files are local
  regular raster files. Do not copy a whole run, caption archive or event ledger.
- [ ] A unique export revision contains source, selected assets, source map,
  manifest and verification record; earlier revisions/runs remain unchanged.
- [ ] Within the user’s authorized publication scope, publisher dry-run passes; then stage explicitly
  selected bundles. Run Narada verify/test/lint/build and inspect the static preview.
- [ ] Browser checks cover library card, report route, contents anchors, provenance
  links, image/alt/caption readability, narrow-screen tables, keyboard navigation,
  missing-value display and absence of private/stale links. Record what was checked.
- [ ] Expected routes, generated JSON and selected raster assets are present; no
  unrelated public files remain. Deployment is a separate later task.

For this template's own documentation changes, run only
`python3 scripts/check-agent-docs.py` from the workspace root.

## Study navigation after staging

After publishing a new immutable ID, explicitly select it in Narada's
[authored study catalog](../apps/narada/content/studies.json), following the
[app guide](../apps/narada/README.md#study-catalog-and-navigation). Preserve the
stable study ID/slug, assert the source run, and label related research runs,
exploratory supplements or presentation revisions. Catalog selections change
navigation only. Validate and inspect both `/studies/<slug>/` and the selected
`/reports/<id>/` in the static preview; never make the build discover workspace
research. Historical catalog snapshots in export provenance are archival records,
not another maintained authoring source.
