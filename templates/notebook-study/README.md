# Notebook-authored study reports

Template version: `notebook-study-1.0`.

This is the default layout for newly authored Abacus study reports and requested
conversions of older reports. The reference is the
[Vern Pivot Cross Statistics study](../../studies/30_verniman_pivot_statistics_es/README.md)
and its [live Results page](https://abacus-narada.vercel.app/studies/verniman-pivot-statistics-es/).
Use the structure and visual treatment; choose questions, theme names and evidence
for the study being written. Six themes and 21 insights are specific to that reference.

The study-local notebook owns the analysis, narrative, generated findings and
figures/tables. Narada presents a verified saved projection of selected notebook
content, with code omitted from the public content. Its Node build never executes
Python or imports notebook HTML. The [architecture](../../ARCHITECTURE.md),
[artifact lifecycle](../README.md) and [publication contract](../../docs/narada.md)
remain authoritative.

The present reader supports the reference study's prose, typed tables and raster
figures. Before adopting it for a report with structured citations, downloads or
candle schematics, complete the capability check below; those features are not
fully presented by the current Results-only projection.

## Start here

1. Read the owning study's plan, settings, input lock and evidence status. Decide
   whether this is new analysis or a presentation of already saved evidence.
2. Copy [study-report.ipynb](study-report.ipynb) to a new filename inside
   `studies/<study-id>/`. Do not replace an existing authored notebook or sealed
   execution. Record this template version in the study guide and execution record.
3. Replace its draft settings, loader and illustrative measure definitions with
   the study's actual questions and pinned inputs. The scaffold deliberately
   stops until configured; it contains no saved results or invented findings.
4. Review the notebook first. After execution and evidence checks pass, export
   selected theme reports, review the local Narada pages, then release within the
   user's publication scope.

The scaffold demonstrates a table, chronological line chart and category bar
chart in three themes. These are examples of cell structure, not a requirement
to use those measures or all three visual types in every study. In Cursor, open
the copied `.ipynb`, choose the workspace `.venv` Python kernel, and inspect its
ordinary Markdown and Python cells. Optional notebook dependencies are installed
with `./scripts/bootstrap --group notebooks`; subsequent execution uses the
locked environment without syncing it.

## Reader layout

```text
Study title
Brief study summary + essential evidence qualification

Results                         ← only outer study destination
  Theme A | Theme B | Theme C    ← question themes, one selected at a time

  Theme title and guiding question

  Insight question / headline
  Brief description: what is being investigated and the population
  Findings summary: supported result, interpretation and material limit
  Chart or table: evidence for that finding

  Next insight in the same structure

  Scope & interpretation        ← short shared notes, collapsible
```

Only the selected theme's insights are mounted. Keep the Research paper
typography, generous spacing, single reading column and restrained colors in
Narada's existing components. Use a descriptive headline, clear visual hierarchy
and legible evidence instead of notebook chrome, dashboard tiles or repeated
link directories. Keep technical notebook publication records, hashes and run
directories out of this reader. Retain that audit evidence in the repository
and saved bundles; hiding the directory does not unpublish existing artifact URLs.

Keep limitations needed to understand a finding beside that finding. The shared
scope disclosure supplements the introduction and insight-specific qualifications.
Keep useful citations, figure access and direct insight links. Avoid duplicate
library links, repeated menus and circular "back to results" links within Results.

## Plan themes and questions

Group related research questions, rather than splitting by file type, execution
date or chart type. Give each insight one primary theme. A useful quantitative
starting set is context/sample, occurrence/frequency, outcomes, path/risk,
conditional comparisons and timing/stability. Rename, combine or omit these when
they do not match the investigation. A source-review study can instead group
definitions, observed examples, contrary examples and unresolved claims; do not
invent a statistical scorecard for qualitative evidence.

Before coding, fill a question map in the study's plan:

| Theme / insight ID | Question | Population and observation unit | Input or saved evidence | Estimate, denominator and uncertainty | Visual | Status |
|---|---|---|---|---|---|---|
| `<theme>/<insight>` | `<one answerable question>` | `<cohort, dates, grain>` | `<pinned source/selector>` | `<units, horizon, support, method>` | `<table/line/bar/other>` | `<planned/exploratory/verified/inconclusive>` |

Record a baseline, eligibility/exclusions, timing of information, missing/censored
outcomes and dependence where relevant. Retain negative and inconclusive findings.
Each theme needs a short guiding question and each insight needs enough context
to stand alone. Empty themes should not appear on the website.

## Notebook cell contract

Use several ordinary cells per logical insight. Do not put the entire page in
one cell or embed an existing website as an HTML document in the notebook.

| Cell | Notebook content | Selected website content |
|---|---|---|
| Heading, Markdown | `### <specific question or supported headline>` | Insight heading |
| Description, Markdown | Purpose, population, unit and comparison | Brief description |
| Analysis, Python | Actual study-specific filters, calculations, comparisons and checks | Omitted |
| Findings, Python/Markdown output | Text generated from the computed result, with its interpretation and limits | Findings summary |
| Evidence, Python output | Table or chart from the same computed object | Chart/table and caption/notes |

An insight may need several analysis cells. Keep its analysis beside the finding
it supports. Small helpers may load pinned inputs, format evidence or record
execution; do not move the entire analysis into a hidden module and leave a
notebook that merely calls `render_report()` or reads website report JSON.
Shared methods with demonstrated reuse can stay in Sahadeva, with their version
and assumptions explicit.

Use stable cell IDs, stable theme/insight IDs, explicit order and cell roles.
The scaffold's `metadata.abacus` roles and `publish` flags are an authoring
convention for a study-local exporter, not a universal notebook import API.
Publish only explicitly selected introduction/theme/heading/description/findings/
evidence content. Editor instructions, setup, source code, debug output, private
paths and execution prompts stay outside public publication bytes.

Generate numerical findings from the same full-precision result used for the
visual. Round only at presentation time. Include counts, actual date coverage,
units, denominators and saved uncertainty where applicable. Explain missingness;
zero, null, false and not tested have different meanings. State retrospective
eligibility, exploratory comparisons and unmodeled execution costs where relevant.

For tables, retain typed scalar rows and columns from the displayed DataFrame;
do not scrape formatted HTML. For figures, retain the exact executed raster,
caption and meaningful alternative text. Use labeled axes and units. Line charts
need chronological ordering and visible coverage/gaps; connected observations
do not establish a fitted or significant trend. Bars compare declared groups
with their own support. A table is often the clearest evidence for exact values,
unequal denominators or multiple qualifiers. Do not force a chart to fill space.

## Execute, verify and retain evidence

Stage each execution in a fresh `work/<study-id>/<unique-run-id>/` directory.
Resolve inputs through the configured storage roots; pin dataset versions,
manifest/content hashes, input locks, settings and the environment lock.
Restart the kernel and execute in order. Retain the executed notebook separately
from its editable source, execution command, source signature, receipt and checks.
Refuse stale outputs after analytical/narrative/source/input edits.

Use the owning study's numerical checks and independent saved-value comparisons
where definitions match existing results. Check units, denominator/support,
missingness and date coverage, not just a headline estimate. Verify theme/insight
membership and order, and reject incomplete or failed execution. Keep claims of
integrity, recorded checks and scientific validity distinct.

Prepare intended publication source before sealing a new run. Retain the notebook
snapshot, settings, inputs/environment/code identities, numerical evidence,
exclusions, checks and artifact hashes in that unique completed run. Follow the
[run guide](../../runs/README.md). Do not execute into a completed run directory.

## Export to Narada

Use the existing report and catalog contracts; do not create a competing schema.
One selected theme becomes one immutable report. One insight normally becomes
one table or figure section with `title`, `description`, `finding`, and its
evidence. Set `schemaVersion: "1.1"` and `presentation: "research-paper"` on each
theme report. Generate these values from the notebook; avoid a second manually
maintained prose specification in the website.

The exporter must bind the authoring source, fresh executed snapshot and receipt,
input/environment identities, cell IDs/order, exact selected text, typed table
cells and raster hashes. Use bounded plain-text conversion for selected Markdown.
Omit source code rather than merely hiding it with CSS. Retain a source map,
publication verification record and manifest alongside the source. Narada checks
the saved handoff, not the underlying calculations.

Study 30's [execution helper](../../studies/30_verniman_pivot_statistics_es/notebook_v2.py)
and [exporter](../../studies/30_verniman_pivot_statistics_es/publish_notebook.py)
are reference implementations. They contain Study 30 identities, question
coverage and reconciliation rules. They are not commands for arbitrary studies.
Adapt execution/export in the owning study with focused checks; extract common
infrastructure only when its inputs and behavior are deliberately generalized.
The starter notebook does not provide a generic exporter or automatic publication.

### Check reader capabilities before migration

The generic Results-only component currently renders narrative, findings,
tables, raster figures and scope notes. It does not render the classic evidence
directory containing structured reference targets/download listings, and its
report projection omits candle `patterns`. A section's `referenceIds` can therefore
produce a citation link without a matching target in this reader. The reference
Vern notebook has none of these unsupported selections; other studies do.

Inventory `referenceIds`, `references`, `downloads`, `patterns` and saved filters
before switching a catalog entry. For a study that needs them, first extend the
reader to present the useful citations, selected download scope/links or diagrams,
with focused component and browser checks. Keep the technical publication-record
directory omitted. Do not silently remove evidence, leave dangling citations or
enable the layout merely because schema validation passes. Check filters and
their saved-row links on the selected tables as part of the same review.

After staging the theme reports, merge this shape into the complete authored
[study catalog](../../apps/narada/content/studies.json) entry (illustrative IDs):

```json
{
  "readingMode": "single-page",
  "featuredPublicationId": "example-context-v1",
  "featuredSourceRunId": "example-run-v1",
  "publicationTabs": [
    {"publicationId": "example-context-v1", "sourceRunId": "example-run-v1", "label": "Context"},
    {"publicationId": "example-outcomes-v1", "sourceRunId": "example-run-v1", "label": "Outcomes"}
  ]
}
```

Current catalog bounds are **2–12 themes**, unique labels and publication IDs,
featured theme first, and one source run shared by the primary theme reports.
This flat mode cannot coexist with `analyses` or `phaseFamilies`. Six tabs are
not required. A one-theme Results-only reader needs a deliberate catalog/UI
extension; do not create a duplicate or empty theme to pass validation. Multi-run
studies need an explicit selected edition with separate attribution; do not flatten
incompatible cohorts or phases into a fabricated common run.

Keep the study slug stable. Add explicit private source locators in
`apps/narada/content/release-sources.json` following the
[publication contract](../../docs/narada.md#local-maintenance-verification).
That file and private evidence are not website inputs. Preserve former report
routes and meaningful section bookmarks during migration.

From `apps/narada`, use Node 24 and the existing npm lock:

```sh
npm run report:publish -- --report <prepared-publication.json> --dry-run
npm run report:publish -- --report <prepared-publication.json>
npm run verify
npm test
npm run lint
npm run build
npm run preview
```

Repeat publisher commands for the explicitly selected theme files; do not scan
and publish a whole directory. Against the running preview, run
`npm run smoke:preview -- --origin http://127.0.0.1:4173 --all-routes` and inspect
desktop/mobile views, every theme, refresh/history, keyboard links/table overflow,
figures/alt/captions, citations, retained routes and console errors. Confirm the
required insight order and absence of code/private output/technical record
directories. Compare all selected narrative, typed table cells and figure bytes
to the executed notebook before calling the projection verified.

The [report schema](../../apps/narada/contracts/report-1.1.schema.json) and
[contract guide](../../docs/narada.md) own content/asset/payload limits. Split an
oversized theme by its research questions or select a documented evidence subset;
do not raise budgets just to copy an entire research grid. GitHub push, local
publication staging and hosted deployment are distinct actions. Use the existing
[release workflow](../../apps/narada/releases/README.md) within the user's scope.

## Convert an older study

Inventory the selected source run, evidence, original report/publication IDs,
cohorts, claims, uncertainty and existing links before changing the presentation.
Record a theme/question map and a source-to-insight mapping in its study plan.

| Migration | What the notebook does | New retained identity |
|---|---|---|
| Presentation only | Reads exact saved evidence, selects/formats it, preserves numbers, methods and the meaning of findings | New `reports/exports/<study-id>/<run-id>/<revision-id>/` and new publication IDs |
| Analytical reconstruction | Recalculates measures in visible cells, adds questions, changes methods/numbers or changes interpretation | Fresh verified analytical run, even if some estimates match earlier evidence |

A presentation-only notebook must be labeled as a saved-evidence presentation;
it must not claim to contain or reproduce the original analytical engine. Keep
that engine and its frozen run cited. If full notebook-owned analysis is required,
plan a reconstruction with new checks and a new run. Never disguise a website
JSON reader or a collection of screenshots as a reproducible analytical notebook.

For either migration, preserve sealed runs and historical bundles unchanged.
Keep original cohort/period/units, contrary evidence and uncertainty visible;
map every displayed value to the saved source. Preserve slugs and old immutable
report URLs. A changed layout uses a new publication ID, not an overwritten bundle.
Reassess research priority when selected scope/evidence changes under the
[rubric](../../strategies/research-priority-rubric.md#reassess-when-evidence-or-scope-changes).
Migrate one chosen study through notebook review and local page review before
expanding the batch. An inventory or template does not execute old research or
authorize converting every past study automatically.

### Suggested first migration batch

This November 8, 2026 queue is based on the selected catalog, saved report shapes
and study guides. It is a starting proposal, not a new review of their scientific
findings or an instruction to execute them.

| Order | Study | Why it is a useful pilot | Preserve or resolve first |
|---|---|---|---|
| 1 | [GC outer EMA band excursions](../../studies/12_gc_ema_band_excursions/README.md) | Clear selected run; compact tables and an annual figure can test two question themes | Cooldown/horizon, exclusion counts, partial-year coverage and uncertainty |
| 2 | [VWAP excursion response](../../studies/15_vwap_excursion_response/README.md) | Natural Asia/London/New York/Globex themes, with related outcome insights | Restore exact retained summary bytes; separate ES/NQ/GC and preserve ambiguous/neither outcomes |
| 3 | [Session-anchored VWAP](../../studies/05_session_vwap/README.md) | Three executed primary questions in one selected run | Preserve baselines and outcome classes; keep later exploratory context work separate |

Start with exact saved-evidence presentation when only layout changes are wanted.
If the actual analytical engine must move into notebook cells, explicitly scope
a new verified reconstruction run. A later
[NQ video source-review pilot](../../studies/17_nq_advanced_amd_video/README.md)
can test the qualitative variant using real saved frames and attributed claim
rows. Larger multi-run studies such as ES Range XV and GC overnight breakout
need an agreed phase/analysis/theme hierarchy before conversion. Instrument tabs
such as Forex News need a deliberate instrument-versus-question navigation choice.

## Completion checklist and reusable request

- [ ] Theme/question map is explicit; the notebook contains separate cells per insight.
- [ ] Source status, actual coverage, support, units, missingness and limits are clear.
- [ ] Analysis, generated findings and visual share verified result objects.
- [ ] Fresh execution and owning numerical checks pass, or a presentation-only
      notebook is explicitly labeled and checked against saved evidence.
- [ ] Exact selected notebook-to-publication transfer and provenance checks pass.
- [ ] Required citations, downloads, schematics and saved filters are supported
      and verified in this reader before changing its catalog selection.
- [ ] Results is the only outer destination; populated themes switch one active body.
- [ ] Reader contains heading, description, findings and evidence in that order,
      with no code or technical publication-record directory.
- [ ] Desktop/mobile, accessibility interactions, retained links and app gates pass.
- [ ] Completed evidence remains immutable; any later export has a new revision/ID.
- [ ] Publication and hosting have been completed only within the requested scope.

Use this request when starting a study or choosing a past one:

> Use the Abacus notebook-study template for `<study>`. First map the questions
> into themes and choose a table or chart for each insight. Keep actual analysis
> in ordinary notebook cells, followed by generated findings and the evidence.
> Use `<pinned inputs or selected saved run>` and retain its qualifications.
> For an older study, identify presentation-only work versus new analysis before
> implementation. Let me review the notebook before the local Narada projection.
> Render the selected notebook content with code hidden, Results as the only
> outer page and question themes as tabs, using the Research paper design.
