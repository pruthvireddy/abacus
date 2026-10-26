# Narada study publication plan — Phase 1

Inventory date: 2026-10-06. This is the decision document and Phase 2 handoff for
the five-phase publication initiative. The [web report template](../templates/web-study-report.md)
owns authoring conventions; this plan owns the inventory and publication order.
Read it with [Narada's contract](narada.md), the [architecture](../ARCHITECTURE.md),
[run rules](../runs/README.md), and [presentation revision conventions](../templates/README.md#later-presentation-revisions).

## Decisions and boundaries

Keep Narada inside Abacus, with its independent Node 24/npm environment. Prepare
selected presentations of saved evidence; research execution is not a publication
dependency. The intended deployment is a locally built static website uploaded to
Vercel without connecting the whole Abacus Git repository. Exact upload tooling,
project configuration and release procedure belong to Phase 5. Existing repository
connection examples describe an alternative; they are not a requirement for this
initiative. No Vercel connection or deployment is part of Phase 1 or the pilots.

Phase 2 should author two presentation revisions and use today's generic report
renderer: study 05 for quantitative evidence and study 17 for a qualitative,
figure-led explanation. Phase 3 adds study navigation and coverage; Phase 4 adds
richer evidence and selected downloads; Phase 5 establishes repeatable releases.
Do not make a schema/navigation redesign a prerequisite for the pilots.

This inventory discovered **17** `studies/*/study.json` registrations and **29**
completed/imported run directories. It read study metadata, READMEs, plans and
decision notes; for historical studies 01–04, the archived READMEs/settings and
saved methodology replace absent active plans/notes. Executed run reports,
manifests and saved table layouts take precedence over current proposals.
In particular, the broader plans for 05/06 and the preparation history for 14
must not be mistaken for the scope actually executed.

Inspection covered report/source JSON contents, manifest records, selected saved
report prose, table headers/dimensions, asset filenames/sizes, and presentation
exports. The primary study 05 raster was also visually inspected. Existing
`publication.json` sources were **inspected only**, not schema-validated or passed
through the publisher. Recorded run verification is historical evidence, not a
new audit performed by this task. No statistics, backtests, dataset rebuilds,
archived scripts, Narada builds or public staging were run.

The initial working tree contained extensive existing changes, including Narada,
new studies/runs and guidance. Phase 1 edits are limited to this plan, the template,
links from their owning guides, and documentation-checker registration. Completed
runs, exports, data, study metadata, reference selections and findings are preserved.

## Page identities and navigation

| Surface / identity | Supported today | Intended later model |
|---|---|---|
| Library homepage `/` | Lists staged publications from `public/publications/index.json`, newest publication timestamp first; currently empty | A study-oriented library of explicitly selected study identities, with featured and related publications |
| Stable study page | None | Proposed `/studies/<study-slug>/`: stable study identity, question/scope, evidence wording and an explicitly featured publication |
| Immutable publication page | `/reports/<publication-id>/`, generated only for indexed bundles | Continues to identify one saved presentation; old IDs/content remain unchanged |
| Related publication | Separate report IDs can already be published | Catalog associates supplemental runs and revisions with a study, preserving each publication's identity |
| Presentation revision | New export revision and new publication ID required by convention; publisher rejects changed content under an existing ID | Study navigation may feature a newer revision without rewriting an older publication |

A future small, curated study catalog can map `study_id` and stable slug to
`featured_publication_id` and a list of related publication IDs, with labels such
as primary, exploratory supplement or presentation revision. These are conceptual
fields, not a new contract in this phase. Author the mapping explicitly and validate
that all referenced IDs exist in Narada's publication index. The website build
reads only staged bundles and that curated catalog; it must not scan `studies/`,
`runs/`, retained data or arbitrary exports to discover publishable material.

Selecting a featured publication is a navigation decision. It does not change a
study's registered `reference_run`, evidence status or earlier publications.
A study without a registered reference can have an explicitly selected publication
source without silently promoting that run to the research reference. Keep related
research executions distinct from revisions of the same presentation.

## Current contract and shared reading format

The implementation inspected was the three schemas, TypeScript report types,
publisher/validation library, publication and static-export verifiers, homepage,
report route, section renderer, formatter, example, and empty public index under
[apps/narada](../apps/narada/README.md).

Today's content is ordered plain text, metrics, tables and raster figures. The
report route supplies a contents list, optional notes, producer/run attribution,
canonical JSON hash and figure hashes, and links to generated JSON/selected figures.
It accepts no arbitrary HTML/Markdown import, remote figures, SVGs, interactive
embeds or general download attachments. Text/captions/table strings do not render
Markdown links. There is no structured study identity, evidence-status field,
analytical source-artifact reference, revision relationship or study registry.

Use this common reading order; quantitative and qualitative variants and field
mapping are defined in the [template](../templates/web-study-report.md#field-mapping-and-authoring-rules):

| Reading stage | Existing section types | Required intent |
|---|---|---|
| Question and scope | `text` | Selected question, product/source, coverage and evidence status |
| Supported findings | `text` | Saved conclusions, including contrary or inconclusive findings |
| Selected key evidence | Optional `metrics`, `table`, `figure`, accompanying `text` | A few explanatory items with their definitions, denominators or attribution |
| Definitions and methods | `text`, optional definition `table` | Enough setup/source/method detail to read the evidence |
| Limitations and uncertainty | `text` | Retrospective/exploratory qualifications, missing evidence, uncertainty and execution limits |
| Source-run and publication provenance | `text`, optional source `table`; built-in record | Source run/protocol, revision identity, source references and recorded checks |

Quantitative reports retain events, population, exclusions, numerator/denominator,
units, horizons, baselines, saved uncertainty and dependence. Distinguish price-path
behavior from execution/net profitability and chronological labels from untouched
holdouts. Qualitative reports identify source material and reviewed scope, distinguish
source claims, observations and saved interpretation, and explain what examples
leave unverified. They can be entirely text/table/figure reports without metrics.

Work within these limits when selecting content:

| Limit | Current enforcement |
|---|---|
| Source / bundle / catalog JSON | 96 KiB / 128 KiB / 256 KiB; catalog at most 200 publications |
| Sections / metrics | 1–30 sections; 1–24 items per metrics section |
| Tables | At most 100 rows and 12 columns each; formatted columns require numeric/null values |
| Figures | PNG/JPEG/WebP regular local files under `figures/`; ≤2 MiB each, ≤8 MiB total; no symlinks |
| Static export payloads | HTML ≤384 KiB each; `.txt`/`.rsc` ≤256 KiB each, checked after build |

Source figure sizes found in this inventory do not exceed the raster byte limits;
this is size inspection, not image/publisher validation. SVGs still require raster
presentation copies. Final output bytes must be measured: a small source table can
still create a large formatted JSON or HTML page. Preserve the full evidence locally
and select readable rows/columns with a documented selection, rather than dropping
unfavorable results or calculating new aggregates to fit.

## Readiness categories and complete inventory

These are **publication-preparation** categories, not research evidence grades.
Use one primary category per study; detailed gaps remain in its notes.

| Code | Meaning | Studies | Count |
|---|---|---|---:|
| A | Existing publication source; review and validation needed | 05 | 1 |
| B | Saved evidence available; presentation conversion needed | 06–13, 15 | 9 |
| C | Source selection unresolved: no registered reference; candidates proposed below | 01–04, 14, 16, 17 | 7 |
| D | Specific source or provenance gap prevents even a bounded source presentation | None assigned as the primary category | 0 |

There are 16 quantitative studies, four of them historical imports, and one
qualitative source review. All have saved evidence; none is publication-validated
by Phase 1. Category C does not mean evidence is absent or a pilot must stop: the
explicit proposed source can be selected for publication when Phase 2 is authorized.
Publication readiness does not fill missing research evidence.

The table records registry `status` verbatim. Evidence wording and complete run
lists are in the per-study notes. **R** means registered `reference_run`; **P** is
a proposed publication source with no reference selection made. Titles are registered
titles. Run IDs below are exact, not shorthand recency recommendations.

| Study | Topic / products | Material; registered status | Reference or proposed source | Readiness; conversion effort |
|---|---|---|---|---|
| [01_reversal_follow_through — Reversal follow-through](../studies/01_reversal_follow_through/README.md) | Range XV; ES/NQ/GC | Historical quantitative; `historical_import` | No R; P `20260906T_full_v3` | C; medium — historical selection, wide tables, SVGs |
| [02_followthrough_candle_adverse — Follow-through candle adverse movement](../studies/02_followthrough_candle_adverse/README.md) | Range XV; ES/NQ/GC | Historical quantitative; `historical_import` | No R; P `20260906T_full_v7` | C; large — seven versions and separate duration evidence |
| [03_multi_rxv_alignment — Multi-Range-XV alignment](../studies/03_multi_rxv_alignment/README.md) | Range XV; ES/NQ/GC | Historical quantitative; `historical_import` | No R; P `20260908T_multi_rxv_v1` | C; medium — summary/CSV conversion and limited original provenance |
| [04_reversal_candle_quality — Reversal candle quality](../studies/04_reversal_candle_quality/README.md) | Range XV; ES/NQ/GC | Historical quantitative; `historical_import` | No R; P `20260908T_reversal_quality_v1` | C; medium — table selection, payoff qualification and limited provenance |
| [05_session_vwap — Session-anchored VWAP](../studies/05_session_vwap/README.md) | VWAP; ES/NQ/GC | Quantitative; `evaluated` | R `20260923T015900Z_vwap3` | A; small — expand existing source, repair presentation labels |
| [06_vwap_state_dynamics — VWAP state dynamics](../studies/06_vwap_state_dynamics/README.md) | VWAP; ES/NQ/GC | Quantitative; `evaluated` | R `20260923T180000Z_state06c` | B; medium — three questions, paired baselines and SVGs |
| [07_range_xv_edge_candidates — Range XV edge candidates](../studies/07_range_xv_edge_candidates/README.md) | Range XV; ES/NQ/GC | Quantitative; `evaluated` | R `20260924T004900Z_rxv07` | B; small — compact negative result with clock qualification |
| [08_countertrend_bar_continuation — Range XV first countertrend bar continuation](../studies/08_countertrend_bar_continuation/README.md) | range_xv; ES/GC/NQ | Quantitative; `completed` | R `20260924T132916Z_ctbars_v1` | B; medium — denominator-sensitive, broad lookup tables |
| [09_range_xv_c2_confirmation — Range XV C2 confirmation decision](../studies/09_range_xv_c2_confirmation/README.md) | range_xv; ES/GC/NQ | Quantitative; `completed` | R `20260924T141810Z_c2confirm_v1` | B; medium — opportunity/pair populations and exploratory age-two check |
| [10_range_xv_session_overlay — Range XV Asia, London, and New York session overlay](../studies/10_range_xv_session_overlay/README.md) | range_xv; ES/GC/NQ | Quantitative synthesis; `completed` | R `20260924T145715Z_session_v1` | B; medium — three studies with different clocks/horizons |
| [11_vwap_conditional_probabilities — VWAP conditional probabilities](../studies/11_vwap_conditional_probabilities/README.md) | VWAP; ES/NQ/GC | Quantitative; `completed` | R `20260924T155331Z_vwap11` | B; medium — competing outcomes, calibration, SVGs |
| [12_gc_ema_band_excursions — GC outer lower EMA band excursions](../studies/12_gc_ema_band_excursions/README.md) | ema_bands; GC | Quantitative; `completed` | R `20260925T223721Z_gc_ema_excursions_v1` | B; medium — interactive full grid needs static selection |
| [13_gc_ema_band_filter_validation — GC lower-band long: two-year filter selection](../studies/13_gc_ema_band_filter_validation/README.md) | ema_bands; GC | Quantitative; `completed` | R `20260926T000219Z_gc_band_filters_v1` | B; small — compact saved comparison, uncertainty essential |
| [14_asia_session_vp_levels — Asia session VP levels study](../studies/14_asia_session_vp_levels/README.md) | volume_profile; NQ | Quantitative; `executed_local_evidence` | No R; P `20260929T124500Z_asiavp_b2` | C; large — distinct protocols, extensive outcomes and SVG |
| [15_vwap_excursion_response — Anchored VWAP excursion and return study](../studies/15_vwap_excursion_response/README.md) | session_vwap; ES/NQ/GC | Quantitative; `completed` | R `20260929T234000Z_a15f` | B; large — four session reports, 409-column evidence and 144 SVGs |
| [16_range_xv_reversal_paths — Range XV reversals: follow-through and predictive lead-up](../studies/16_range_xv_reversal_paths/README.md) | range_xv; 6E/6B/6J/6S | Quantitative; `completed` | No R; P `20261002T010500Z_ohlc200_161001` | C; large — model/path/censoring and historical unit distinctions |
| [17_nq_advanced_amd_video — NQ advanced AMD video source study](../studies/17_nq_advanced_amd_video/README.md) | price_action; NQ | Qualitative; `source_review_complete` | No R; P `20261005T172713Z_video17` | C; medium — figure-led source attribution and claim separation |

### Inventory conventions and shared gaps

In each note, filenames are relative to the linked run directory unless an export
path is stated. All runs for 05–17 have `report.html`, `report.md`, `metrics.json`,
`advice.md` and `manifest.json`. These reports are evidence sources, not proof of a
Narada-compatible publication. Studies 01–04 use `run_manifest.json` plus additive
`import_manifest.json`; none has `metrics.json`. Their numerical evidence is CSV.

Only study 05 has publication JSONs (two). Only 11 and 12 have current presentation
revisions under `reports/exports/` (four and one respectively); none is a Narada
source. All other registered studies have no publication JSON or export revision
in those trees at inventory time. Historical report copies under
`legacy/sahadeva/reports/01…04/` remain archives, not new export revisions.

There is also a retained, **unassigned**
[legacy presentation collection](../legacy/sahadeva/presentation-exports/).
The [migration record](migration/README.md#historical-input-limitation) preserves
these files and explicitly leaves their source-run correspondence unresolved.
They are possible historical presentation references, not selected evidence for
any of studies 01–04. Filename/size/provenance inspection only was performed here;
the PDF/workbook contents were not validated or traced to run cells.

| Legacy artifacts (relative to that collection) | Format / size | Publication disposition |
|---|---|---|
| `ES_4RXV_Poster`, `ES_5RXV_Poster`, `ES_6RXV_Poster`, `GC_6RXV_Poster`, `GC_10RXV_Poster`, `NQ_10RXV_Poster`, `NQ_20RXV_Poster` (each `.pdf` and `.png`) | Seven PDFs, 47,648–47,691 bytes; seven PNGs, 460,230–479,849 bytes | PNG bytes fit the figure limit, but source-run/table mapping is unresolved; no selection by instrument filename |
| `RangeXV_All_7_Posters.pdf`, `RangeXV_Poster_Collection.png` | PDF 79,225 bytes; PNG 451,020 bytes | Same attribution gap; PDF is not a current Narada figure/attachment type |
| `RangeXV_Stats_First_Draft.xlsx` | Workbook 162,326 bytes | Not a Narada input/download type; do not use a first-draft workbook as numerical authority without a verified source mapping |

Initial historical publications should use the directly identified run reports
and CSVs instead. Tracing these 17 legacy exports is a later provenance task,
not permission to regenerate them or fill their missing attribution. Studies 01
and 02 also name original short-window inputs that are absent from today's source
inventory, for example `ESU6_rangexv5_0614_0904.csv`; the migration record does not
claim a full rerun is possible. This limits fresh source verification, while their
retained reports/tables remain available for a qualified historical presentation.

Saved report Markdown links were checked for local target existence without
recursing into linked historical documents; no missing inline local targets were
found in the run reports/summaries examined. This does not validate public URLs,
all HTML/script links, manifest locators or retained ledger hashes. Old active-plan
absolute paths, historical manifest `analysis/...` paths and original execution
commands remain historical provenance. Map authoring references to preserved
workspace files in a new manifest; do not modernize originals. Private filesystem
links in an offline report will not become live public links in Narada.

Clock normalization must not reinterpret old runs as having used corrected inputs.
Studies 01–04 retain historical clock/holdout language and consolidation status;
07 explicitly pins pre-normalization bytes. Study 10's saved overlay labels those
07 events with a corrected clock but does not rerun its quiet-breakout cohort.
Execution/fill provenance, independent validation and absent datasets are research
limits that conversion cannot supply. Optional new visualizations/compact tables
are presentation work only when faithfully made from saved evidence.

### 01 — Reversal follow-through

Registry evidence: “Imported historical results; unreviewed during consolidation.”
Completed imports: [20260906T_full_v1](../runs/01_reversal_follow_through/20260906T_full_v1/),
[20260906T_full_v2](../runs/01_reversal_follow_through/20260906T_full_v2/), and
[20260906T_full_v3](../runs/01_reversal_follow_through/20260906T_full_v3/).
No registered reference. Propose v3 because its expanded decision summary explains
the saved “no clear winner” conclusions and companion movement evidence; confirm
source/version differences before adopting it, rather than selecting by suffix.

Each has HTML/Markdown reports, `methodology.md`, `data_quality.md` and
`selection_ledger.json`; relevant CSVs are `cross_asset_summary.csv`, `headline.csv`,
`candidate_selection.csv`, `continuation_thresholds.csv`, `excursions_fixed.csv`,
`timing_milestones_proxy.csv` and `paired_comparisons.csv` under `tables/`.
Nine SVGs include `continuation_curves.svg`, `excursion_profiles.svg` and
`coverage_gap.svg`. Even `headline.csv` is 73×31; excursions reach 58 columns.
Select columns/rows and rasterize figures. Missing GC20 and unresolved feed,
clock/completion/contract-adjustment metadata remain explicit; GC6 was inventory-only
in this study. Initial scope: a historical follow-through and adverse-movement
summary, preserving frozen candidate decisions and timing-proxy language.
Advance C→B by recording the publication source decision; then prepare the revision.

### 02 — Follow-through candle adverse movement

Registry evidence: “Imported historical results; unreviewed during consolidation.”
Completed imports under [this run root](../runs/02_followthrough_candle_adverse/):
`20260906T_full_v1`, `20260906T_full_v2`, `20260906T_full_v3`, `20260906T_full_v4`,
`20260906T_full_v5`, `20260906T_full_v6`, `20260906T_full_v7`. No reference.
Propose v7 for its combined adverse, confirmation, hold-time and corrected full-leg
duration material; the scope/version review is unresolved. Earlier versions are
related historical variants, not independent validation.

All have HTML/Markdown reports and methodology/quality notes; v6/v7 also have
`leg_duration_report.html`/`.md`. Relevant `tables/`: `headline.csv` (7×93),
`long_short.csv`, `chronological_stability.csv`, `hold_time_summary.csv`,
`leg_duration_summary.csv`, `leg_duration_by_session.csv` (v7), and the raw-clock
half-hour tables. Figures range from five to eight SVGs; v7 includes
`mean_adverse.svg`, `hold_time_30min.svg` and `leg_duration_30min.svg`.
Initial scope: second-candle geometry and a separately labeled duration explanation.
Do not turn a cohort conditioned on its eventual close into a live filter, raw
clock buckets into corrected NY sessions, or successful-only timing into all-event
holding time. Advance by choosing source coverage and making narrow static tables;
no new metric JSON or empirical verification is required merely to present the CSVs.

### 03 — Multi-Range-XV alignment

Registry evidence: “Imported historical results; unreviewed during consolidation.”
Only completed import: [20260908T_multi_rxv_v1](../runs/03_multi_rxv_alignment/20260908T_multi_rxv_v1/).
It is the proposed source because it directly covers the registered question;
there is no reference or supplemental run. Available prose: `summary.md` and
`methodology.md`; no HTML report or saved figures. Relevant `tables/`:
`aligned_vs_countertrend.csv` (216×12), `pullback_continuation.csv` (864×14),
`exhaustion_comparisons.csv`, `countertrend_large_confirmation.csv`, `pair_audit.csv`.

Initial scope: short-horizon alignment, limits at longer horizons and strict prior
completion rules, with selected table rows; charts are optional. Missing ES4 prevents
its requested pairs. The original manifest contains config/input-manifest locators,
table paths and audits, but lacks the richer code/environment/input-hash record of
new runs; import hashes identify preserved copies, not a reconstructed execution.
Record those limits and map archived configuration separately. Advance by explicitly
selecting the sole source and preparing a table-first historical presentation.

### 04 — Reversal candle quality

Registry evidence: “Imported historical results; unreviewed during consolidation.”
Only completed import: [20260908T_reversal_quality_v1](../runs/04_reversal_candle_quality/20260908T_reversal_quality_v1/).
Proposed as the direct source; no reference or supplement. `summary.md` and
`methodology.md` exist; HTML and figures do not. Relevant `tables/`:
`one_bar_snapback_contrasts.csv` (144×13), `continuation_feature_contrasts.csv`
(4,320×20), `large_confirmation_feature_contrasts.csv`, `geometry_distributions.csv`
and `pair_audit.csv`. The original manifest has the same limited provenance shape
as study 03; retain that disclosure and additive import hashes.

Initial scope: define the saved quality stack, present the one-bar association
alongside longer-run weakness and negative next-bar close-return evidence. A high
continuation rate must not hide payoff asymmetry. Advance by selecting the source
and converting saved comparison rows; no missing chart needs to be invented.

### 05 — Session-anchored VWAP

Registry evidence: “Price-path statistics from the pinned 1.0.0 release; execution
costs and fills remain unmodeled. A/C context cuts are exploratory and re-entry
lacks a paired policy comparison.” Registered reference:
[20260923T015900Z_vwap3](../runs/05_session_vwap/20260923T015900Z_vwap3/).
Related registered exploratory run:
[20260923T035300Z_ac_context](../runs/05_session_vwap/20260923T035300Z_ac_context/).
Both have publication JSONs. The primary source is 3,259 bytes, ID
`vwap-three-20260923t015900z-vwap3`; the context source is 2,134 bytes, ID
`vwap-ac-context-20260923t035300z-ac-context`. Neither is staged publicly or
validated here. The context `metrics.json` is 116,669 bytes, already larger than
the source-report limit; select its saved values rather than copying it wholesale.

Primary evidence: `metrics.json`, `tables/scorecards.csv` (12×90), `baselines.csv`
(96×17), `eligibility.csv`, `exclusions.csv`, `stability.csv`, `sensitivity.csv`,
`warmup_sensitivity.csv`, SVG and PNG barrier figures. Context: `cuts.csv`,
`ny_early.csv`, `reentry.csv`, `control_comparisons.csv`, `interactions.csv`, two
SVGs (`ny-early.svg`, `c-peak.svg`). The documented warmup20/warmup40 extractions
are sensitivity sources summarized in the primary table, not additional completed
directories under this run root. Initial scope: the reference's three executed
B/A/C questions; context can become a separate later publication. Re-entry's paired
policy evidence is missing, and cross-acceptance/outside continuation remain proposed.
Advance by following the [pilot handoff](#pilot-05--quantitative-reference-presentation).

### 06 — VWAP state dynamics

Registry evidence: “Three frozen probability questions evaluated; all available
dates exploratory because prior VWAP outcomes were viewed. No execution or
profitability model.” Reference:
[20260923T180000Z_state06c](../runs/06_vwap_state_dynamics/20260923T180000Z_state06c/).
Related registered exploratory supplement:
[20260923T182800Z_state06supp](../runs/06_vwap_state_dynamics/20260923T182800Z_state06supp/).
The supplement pins the parent's unchanged ledger and repeats its primary report;
identify supplement attribution explicitly rather than treating repeated prose as
a new primary execution. The five optional modules in the plan were not executed.

Relevant `tables/`: `probability_atlas.csv` (9×22), `matched_comparisons.csv`,
`paired_errors.csv`, `replications.csv`, `barrier_comparisons.csv`, `exclusions.csv`.
Both runs have `primary-probabilities.svg` and `barrier-contrast.svg`; the supplement
adds `first_cross_time.csv`, `explicit_clock_windows.csv`, `feature_descriptives.csv`
and `secondary_paired_targets.csv`. Initial scope: the reference's three questions,
raw versus adjusted context and conflicting local-anchor sensitivities. Advance by
splitting the atlas into ≤12-column tables and rasterizing selected SVGs; keep the
supplement separately identified. Abandoned feature-only pilots in work are not runs.

### 07 — Range XV edge candidates

Registry evidence: “Three chart-price candidates evaluated; none passes the declared
two-tick and familywise screen. All dates retrospectively inspected.” Only completed
run/reference: [20260924T004900Z_rxv07](../runs/07_range_xv_edge_candidates/20260924T004900Z_rxv07/),
executed protocol 1.0.1. Relevant `tables/`: `primary_summary.csv` (108×22),
`primary_contrasts.csv` (36×12), `secondary_horizons.csv`, `stop_target_bounds.csv`,
`declared_subgroups.csv`; figure `two_tick_cost_screen.svg`. Saved Parquet event
ledgers and extraction audit remain local. No completed supplement; study 10 is a
separate exploratory overlay, not a replacement.

Initial scope: the negative nine-comparison result with selected contrast rows and
the cost-screen figure. “Net ticks” means an assumed two-tick chart-price haircut,
not verified fills/cost-adjusted trading profit. The sealed input clock predates
normalization; quiet-period conditioning is not corrected by publication. Advance
with faithful rasterization, a concise conversion and explicit clock/proxy caveats.

### 08 — First countertrend bar continuation

Registry evidence: “locally verified.” Only run/reference:
[20260924T132916Z_ctbars_v1](../runs/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/).
Relevant `tables/`: `overall.csv` (98×12), `headline_screen.csv` (280×25),
`period.csv`, `onebar_larger.csv`, `larger_aggregate.csv`, `structure.csv`,
`sensitivity.csv`, `real_event_traces.csv`; full lookup is 1,960×22. No saved figures.
Study 10 supplies a later related overlay; unsealed implementation stages do not
count as completed supplements.

Initial scope: one-more versus two-more versus conditional C3 probabilities, the
zero-of-210 positive screen and larger-chart context. Keep C1 excluded from the
two-more count, distinguish the C4 denominator, report GC exclusions and inferred
clock semantics. Advance by selecting overall rows and ≤12 meaningful columns
from the screen/period tables. Tables can carry the page; no chart generation or
fresh validation is needed. Local verification does not establish a live edge.

### 09 — C2 confirmation decision

Registry evidence: “locally verified.” Completed runs:
[20260924T140720Z_c2confirm_v1](../runs/09_range_xv_c2_confirmation/20260924T140720Z_c2confirm_v1/)
and registered reference
[20260924T141810Z_c2confirm_v1](../runs/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/).
Notes explain the second complete run corrects prose: seven selected contrasts
narrowed and one widened under the exploratory age-two diagnostic. Keep the first
run and do not revert to its overbroad wording; numerical/primary screen results
were unchanged. Study 10 is separately related.

Relevant `tables/`: `overall.csv` (42×24), `comparison.csv`, `headline_screen.csv`,
`age2_comparison.csv`, `opportunity_overall.csv` (84×12), `price.csv`,
`price_delta.csv` (14×12), `gc_sensitivity.csv`; no saved figures. Initial scope:
conditional C3+C4 continuation, original-C1 opportunity costs and price proxies,
with the age-two diagnostic labeled post-result. Advance by preparing separate
conditional and common-opportunity tables; their horizons/denominators must not
be presented as the same outcome. Preserve strict completion and inferred-clock limits.

### 10 — Session overlay

Registry evidence: “locally verified exploratory overlay.” Only run/reference:
[20260924T145715Z_session_v1](../runs/10_range_xv_session_overlay/20260924T145715Z_session_v1/).
Its manifests pin studies 07, 08 and the registered second 09 run. Relevant
`tables/`: `07_summary.csv` (36×31), `07_period.csv`, `08_summary.csv` (56×25),
`08_prior_bin.csv`, `09_summary.csv` (56×36), `09_age_two.csv`,
`09_opportunity.csv` (336×13), and period tables. No figures.

Initial scope: three separate segment comparisons and the absence of a supported
price edge, rather than a pooled study ranking. Preserve different source samples,
horizons, C1/C2 clocks, exploratory screens and the study 07 old-cohort/current-label
distinction. Advance with three compact selected tables and explanatory text;
no resegmentation or recalculation is needed. Source dependency mapping exists;
ATAS clock verification and fresh validation do not.

### 11 — VWAP conditional probabilities

Registry evidence: “Locally verified exploratory conditional-probability evidence;
no pristine holdout and no profitability claim.” Only run/reference:
[20260924T155331Z_vwap11](../runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/).
Relevant `tables/`: `probability_atlas.csv` (9×12), `question_a_rates.csv`,
`question_b_outcomes.csv`, `question_c_outcomes.csv`, `model_scores.csv`,
`calibration.csv`, `updated_corridor.csv`, `funnel.csv`, `exclusions.csv`.
Ten SVGs include `remaining-return-by-elapsed.svg`, `calibration.svg`,
`corridor-by-width.svg` and saved success/failure/ambiguity examples.

Four existing [Pine presentation revisions](../reports/exports/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/):
`20260925T031500Z_conditional_pine`, `20260925T033300Z_conditional_pine_v2`,
`20260925T033700Z_conditional_pine_v3`, `20260925T034500Z_stats_only_v4`.
Each has README, generator, manifest, verification and Pine outputs; none is a web
publication JSON. Initial scope: three deadline-specific outcome vectors and limited
incremental context support. Advance by adapting the saved atlas and selected SVGs.
The Pine companion is a chart-feed proxy with native compile/replay still unverified;
its presence does not add empirical evidence or authorize a download.

### 12 — GC EMA band excursions

Registry evidence: “locally verified descriptive evidence.” Only run/reference:
[20260925T223721Z_gc_ema_excursions_v1](../runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/).
Relevant `tables/`: `yearly.csv` (595×29), `cohorts.csv` (85×4); event evidence has
a locator/hash manifest. No standalone figures. The sealed HTML is 402,694 bytes
and includes an interactive selector; neither the script nor the full table can
be imported into today's Narada.

Existing [20260925T224602Z_html_interactivity_v1](../reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/20260925T224602Z_html_interactivity_v1/)
has corrected HTML, README, manifest and verification; its 408,697-byte HTML fixes
the selector and preserves the 595 numerical records. Both HTML files exceed
Narada's 384-KiB per-generated-HTML budget if copied unchanged; conversion must
create a smaller new page. Initial scope: saved default 10-bar cooldown/20-bar
horizon yearly evidence, regime changes, coverage and selected sensitivities.
Advance with static selected rows/columns and preserve retrospective adjusted-input,
path-ordering and YTD limitations. Rich selector behavior belongs to a later phase.

### 13 — GC filter selection

Registry evidence: “locally verified descriptive evidence; improvement uncertain.”
Only run/reference:
[20260926T000219Z_gc_band_filters_v1](../runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/).
Relevant assets: `decision.json`, `tables/primary.csv` (20×29),
`tables/sensitivity.csv` (140×28), metrics, static HTML/Markdown report. No figures.
The separate Pine companion under the study is not a presentation export or another
sealed validation run; its added chart options are exploratory.

Initial scope: all nine candidate filters plus baseline, the frozen upper-half-close
selection and uncertain 2026 chronological check. Preserve the interval spanning
zero and negative filtered score; do not call this improvement established or 2026
untouched. Advance by making a ≤12-column primary comparison and saved interpretation.
No missing scorecard/figure should be fabricated. Sensitivity counts are correlated,
not independent confirmations.

### 14 — Asia VP levels

Registry evidence: “Frozen protocols 1.0.0 and exploratory 1.1.0; sealed local runs
20260929T124500Z_asiavp_b2 and 20260929T141000Z_prev_rth_de have verified signal and
path evidence. The extension adds 5/10/20-bar means and is not untouched validation.
No web publication or strategy promotion.” Completed runs:
[20260929T124500Z_asiavp_b2](../runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/)
and [20260929T141000Z_prev_rth_de](../runs/14_asia_session_vp_levels/20260929T141000Z_prev_rth_de/).
No `reference_run` is registered. Propose the 1.0.0 run as the first publication
source because it answers the original A–C scope; publish the D/E extension as a
separate related presentation. This proposal does not select a research reference.

Original `tables/`: `metrics.csv` (576×36), `control_effects.csv` (24×18),
`quality_by_year.csv`, `yearly_primary.csv`, `structural_hits.csv`, `races.csv`,
`robustness.csv`, `funnel.csv`, `representative_profiles.csv`; one 30,253-byte SVG
`representative_profiles.svg`. Large outcome/control tables include 310,488×44
primary horizon rows; leave them local. The extension has `metrics.csv` (64×24),
`yearly.csv` (108×9), `funnel.csv`, `outcomes.csv` and an event manifest, no figures.
Original large ledgers are saved in the run and hashed in its artifact manifest;
an `events.manifest.json` is absent in that original run, unlike the extension.

Initial scope: A–C primary paths with control differences, inconclusive/adverse
evidence and sparse pre-2018 quality. Keep the extension's previous-RTH meaning,
working POC-side assumption and exploratory years separate. Feature preparation in
work is quality evidence; failed stages are not completed runs. Advance by selecting
sources explicitly, narrowing tables and rasterizing the profile. Do not invent
TradingView parity, missing horizons or fills.

### 15 — VWAP excursion response

Registry evidence: “Protocol 1.0.0 frozen before outcomes. Verified local run:
42,096 parent excursions, 67,392 threshold signals, 35,843 first touches; shared-week
bootstrap and independent raw-source recounts. Descriptive only; no profitability
claim. Browser HTML layout not verified; offline figures/table values checked.”
Only run/reference:
[20260929T234000Z_a15f](../runs/15_vwap_excursion_response/20260929T234000Z_a15f/).
Master report plus `asia`, `london`, `ny`, `globex` HTML/Markdown reports exist.
Relevant `tables/`: `findings.csv` (12×16), `summary.csv` (9,260×409, 39,296,307 bytes),
`coverage.csv`, `release-coverage.csv`, `example-selection.csv`, `example-paths.csv`,
`figure-inventory.csv`; corresponding saved Parquet summaries also exist.

There are 144 SVG figures (returns, excursions, endpoints, yearly stability,
distributions and deterministic paths), plus eight QA PNGs. QA contact sheets are
inspection artifacts, not automatically chosen publication figures. Initial scope:
a concise overview preserving product/session differences, three modules, frozen
versus evolving return and horizon-specific denominators. Later related publications
may cover each session from the same run. Advance by projecting exact saved cells,
selecting a few SVGs for raster export and browser-checking the new pages. The run's
`report-schema.json` is its research report contract, not Narada's schema. No true
volume delta, execution edge, untouched holdout or verified off-device backup exists.

### 16 — FX reversal paths and lead-up

Registry evidence: “Protocol 2.0.0 sealed locally with complete event/prediction
evidence, numerical/source/bootstrap/report verification, and negative/inconclusive
results. No executable trading edge is established.” Only completed run:
[20261002T010500Z_ohlc200_161001](../runs/16_range_xv_reversal_paths/20261002T010500Z_ohlc200_161001/).
No registered reference; propose this sole complete protocol-2.0.0 source for its
direct coverage, not recency. HTML is 793,246 bytes; Markdown is 98,797 bytes.
The full report cannot be copied into a bounded Narada page.

Relevant `tables/`: `report-findings.csv` (20×8), `continuation.csv` (516×148),
`price-paths.csv` (580×154), `L2-L3-direct.csv`, `L2-L3-adjustment.csv`,
`L2-L3-yearly-audit.csv`, `model-paired-improvements.csv`, `candidate-support-summary.csv`,
`candidate-matched-differences.csv`, `unit-definitions.csv`, input/eligibility tables.
There are 144 SVGs: continuation, L–F matrices, excursions, elapsed time,
calibration/lift and verified example paths. Selection/prediction artifacts and
retained evidence manifests exist. No publication source/export.

Initial scope: baseline persistence, inconclusive L2/L3 differences, lack of richer
lead-up improvement beyond R/context, and negative/inconclusive price evidence.
Advance by selecting the source, making small finding/model/path tables and raster
figures. Preserve candle-order versus strict-price populations, B4-open endpoint,
censoring, constant quote-equivalent units and mandatory 6S pre/post-era limits.
Clock, contract/adjustment and fill provenance remain research limits; no volume
delta or independently verified off-device backup should be implied.

### 17 — NQ AMD video review

Registry evidence: “Qualitative source review only. No independent trade verification
or profitability test. Quarterly-candle regularity is unverified; the all-time-high
objective was not reached in the lesson's reviewed week.” Only completed source
review: [20261005T172713Z_video17](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/).
No reference is registered; propose this sole directly relevant review as the pilot
publication source. HTML/Markdown reports, `source.json`, `inputs.lock.json`,
`capture-log.json`, `checks.json`, acquisition/source provenance, and 14 JPEGs exist.
`metrics.json` records source/review coverage, not a statistical strategy scorecard.

Relevant `tables/`: `coverage.csv` (18×4), `claims.csv` (21×7), `charts.csv` (14×12).
JPEGs are 66,096–97,567 bytes each, 1,232,115 bytes total, well below byte limits.
The full English automatic captions are retained at the private locator in the
source lock; that file exists locally, but its checksum/backup was not re-audited
here. Initial scope: conditional weekly view, local confirmation and abstention,
with source timestamps and explicit unverified claims. No empirical performance,
quarterly enumeration or audited trades exists. Advance by explicitly selecting
the proposed publication source and following the [pilot handoff](#pilot-17--qualitative-source-review).

## Content preparation and provenance

The existing-run path is:

```text
saved run
  → new reports/exports/<study-id>/<source-run-id>/<revision-id>/
  → publication.json + explicitly selected figures + presentation provenance
  → Narada publisher
  → staged public bundle → static website
```

Choose a unique revision ID and a new immutable publication ID. Never append
publication sources or replacement figures to completed runs. Future analytical
runs may prepare publication JSON/selected figures while staged in work, derive
them from saved results, and include them before sealing the unique run.

Each presentation revision must contain a manifest following
[existing conventions](../templates/README.md#later-presentation-revisions):

- Study, source run, presentation revision and publication identities; UTC creation
  time; template/format version. Supplemental source runs are identified explicitly.
- Exact workspace-relative source-artifact paths and SHA-256 hashes, including
  consumed reports, metrics, tables, original figures and relevant source manifests.
- Exact rendering/export/authoring command, tool version or code revision, and any
  dirty presentation-script snapshot needed to reproduce the output.
- Presentation changes: selected rows/columns/figures, wording condensation,
  formatting/unit conversion, rasterization, crop/resize/compression. Preserve the
  numerical results, definitions and meaning of the saved interpretation.
- Checks performed, their results and remaining limitations; output artifact paths
  and hashes, excluding the manifest's own hash.

Keep a source map beside the revision using the
[template worksheet](../templates/web-study-report.md#source-map-and-presentation-manifest).
Transfer values by exact saved metric IDs or row selectors. Preserve full precision
in source JSON, format at display time, and carry the saved denominators/intervals.
Selection, serialization and explicit unit scaling are presentation operations;
new estimates, aggregation, model scoring and recomputed intervals are research.
Compare every displayed value to its saved cell, including nulls and uncertainty
endpoints, and every conclusion to the saved report. If sources disagree, record
the specific discrepancy and narrow the presentation; do not calculate a replacement.

Narada hashes canonicalized report JSON and exact selected asset bytes. That hash
is not the original `publication.json` file-byte hash, and neither proves numerical
accuracy. The presentation manifest records source evidence hashes independently.
Only the chosen report content and referenced regular raster assets cross into
`apps/narada/public/publications/`; raw data, full transcripts, ledgers, source
code/snapshots and complete run directories remain outside public output.

An export's discoverability link belongs in study notes or a strategy card when
that later work is authorized, without changing findings/reference selection.
There is no generic export generator or automatic export-index discovery today.
Only run the research-index check if its actual inputs change; Phase 1 changes none.

## Phase 2 handoff

Start from this inventory and the [template](../templates/web-study-report.md).
Read the specified source reports/protocols for authoring accuracy; do not repeat
the repository inventory or rerun research. Both recommended pilots have concrete
sources and are suitable. Neither is blocked by absent research evidence for its
bounded proposed scope. Study 17's publication-source selection remains proposed;
it must be made explicit in the export manifest without registering a reference.

### Pilot 05 — quantitative reference presentation

Source: registered reference `20260923T015900Z_vwap3` for study `05_session_vwap`.
Create a new revision under
`reports/exports/05_session_vwap/20260923T015900Z_vwap3/<new-revision-id>/`.
Proposed publication ID shape: `session-vwap-vwap3-<revision-suffix>`; choose a
unique real ID during authoring. Do not modify/reuse the existing source ID for
expanded content. The context run is outside this first pilot's findings.

| Exact source artifact | Purpose / selected candidates |
|---|---|
| [runs/05_session_vwap/20260923T015900Z_vwap3/publication.json](../runs/05_session_vwap/20260923T015900Z_vwap3/publication.json) | Starting source; its 3-row scorecard preserves saved primary values, but scope/definitions/baselines need expansion |
| [runs/05_session_vwap/20260923T015900Z_vwap3/report.md](../runs/05_session_vwap/20260923T015900Z_vwap3/report.md) and [report.html](../runs/05_session_vwap/20260923T015900Z_vwap3/report.html) | Saved interpretation, sample construction, adverse evidence and limits |
| [runs/05_session_vwap/20260923T015900Z_vwap3/protocol-1.0.0.md](../runs/05_session_vwap/20260923T015900Z_vwap3/protocol-1.0.0.md) | Executed B/A/C event, contact, availability, horizon and comparison definitions |
| [runs/05_session_vwap/20260923T015900Z_vwap3/metrics.json](../runs/05_session_vwap/20260923T015900Z_vwap3/metrics.json) | IDs `b.all.primary`, `a.all.primary`, `c.all.primary`; ES/NQ/GC counterparts available |
| [runs/05_session_vwap/20260923T015900Z_vwap3/tables/scorecards.csv](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/scorecards.csv) | Select `product=ALL`, `strategy=B/A/C`: events, evaluable, sessions, successes, rate and interval; explicit horizon text; retain A/C competing classes in a separate table |
| [runs/05_session_vwap/20260923T015900Z_vwap3/tables/baselines.csv](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/baselines.csv) | Select `product=ALL`, `split=ALL/final`, treated/control A/A_control and C/C_near; show both `half_sigma` and `fixed_8_ticks` definitions, matched counts, rates, difference, conditional-overlap interval and claim status |
| [runs/05_session_vwap/20260923T015900Z_vwap3/tables/eligibility.csv](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/eligibility.csv) and [exclusions.csv](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/exclusions.csv) | Coverage/exclusions with product/year and source labels; select existing rows, no fresh total calculation |
| [runs/05_session_vwap/20260923T015900Z_vwap3/tables/sensitivity.csv](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/sensitivity.csv) and [stability.csv](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/stability.csv) | Optional saved barrier/stability detail; project selected columns rather than publishing 21-column stability table |
| [runs/05_session_vwap/20260923T015900Z_vwap3/figures/barrier-outcomes.svg](../runs/05_session_vwap/20260923T015900Z_vwap3/figures/barrier-outcomes.svg) and [barrier-outcomes.png](../runs/05_session_vwap/20260923T015900Z_vwap3/figures/barrier-outcomes.png) | Candidate plot. SVG includes title/row/legend labels; inspected 900×250 PNG has bars/swatches but no visible labels. Rasterize SVG faithfully into the new revision and check readability |
| [runs/05_session_vwap/20260923T015900Z_vwap3/manifest.json](../runs/05_session_vwap/20260923T015900Z_vwap3/manifest.json), [inputs.lock.json](../runs/05_session_vwap/20260923T015900Z_vwap3/inputs.lock.json), [events.manifest.json](../runs/05_session_vwap/20260923T015900Z_vwap3/events.manifest.json), [verification-results.json](../runs/05_session_vwap/20260923T015900Z_vwap3/verification-results.json) | Source identity and historical checks; ledgers are traceability sources, not public attachments |

Proposed section outline:

1. `text` — question/scope: three executed questions on pinned 1.0.0, ES/NQ/GC,
   seven correlated anchor/window views, 2m/5m, retrospective complete-day coverage.
2. `text` — supported findings: frequent deadline return does not establish an
   executable magnet trade; A/C do not demonstrate stable incremental advantage.
3. `table` — three primary questions, numerator/denominator, sessions, rates and
   saved intervals; B is frozen return by window end, A/C are 30-minute favorable-first.
4. `figure` plus supporting `table` — A/C favorable/adverse/neither/ambiguous
   distribution and labeled barrier illustration.
5. `text` plus `table` — selected saved baselines, overlap caveats and barrier reversal.
6. `text` — setup definitions, observed next-open reference, maturity/contact and
   uncertainty rules; optional selected coverage/exclusion table.
7. `text` — limitations: fills/costs absent, correlated views, chronological data
   not certified unseen, exploratory baselines; two other VWAP ideas still proposed.
8. `text` — source-run/protocol/export identities and recorded provenance/checks.

Preparation and compatibility: existing source/table values need no new research.
Add horizon labels and denominator context, plain-text traceability, explicit count
precision and ratio formats. Keep primary source intervals (the exploratory context
source has its own intervals). Numeric CSV fields must become numbers/null, not
formatted strings; Boolean/missing statuses must retain their meanings. The 90-column
scorecards and 17-column baselines require projections. Do not import offline HTML.

Content checks: every primary value/interval against the three metric IDs and
matching scorecard rows; A/C exhaustive classes and their evaluable denominators;
B's distinct deadline; selected baseline rows/units/status; causal definition and
contrary findings against the saved report. Check SVG-to-raster labels, legend and
series order, byte budgets and source/output hashes. These are transfer/render checks,
not statistical recomputation or a rerun of study audits.

Browser checks: library title/summary, direct `/reports/<new-id>/`, contents anchors,
mobile table scroll, counts/rates/CI rendering, caption/alt text and legible plot,
keyboard access, publication JSON/figure links, and no private/stale source hyperlinks.
Expected deliverables: new export directory with `publication.json`, selected raster,
source map, manifest and check record; one staged immutable Narada bundle/index entry;
verified static pilot page and recorded browser checks. Keep the old two study 05
source JSONs and all runs unchanged. No deployment.

### Pilot 17 — qualitative source review

Proposed source selection: `20261005T172713Z_video17` for
`17_nq_advanced_amd_video`, because it is the sole complete review of the requested
lesson. There is no registered reference. Make the publication selection explicit
in a new export manifest; preserve that registry fact. Create
`reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/<new-revision-id>/`
and a unique ID such as `nq-amd-source-review-<revision-suffix>`.

| Exact source artifact | Purpose |
|---|---|
| [runs/17_nq_advanced_amd_video/20261005T172713Z_video17/report.md](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/report.md) and [report.html](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/report.html) | Saved interpretation, vocabulary, day sequence, rejected examples and unverified claims |
| [runs/17_nq_advanced_amd_video/20261005T172713Z_video17/source.json](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/source.json), [config.json](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/config.json), [inputs.lock.json](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/inputs.lock.json) | Tmac, video `mmem9CI7vvw`, displayed publication/access 2026-10-05, duration 27:11; full review from 0:00; chart week 2026-09-28–10-02; private automatic-caption locator/hash |
| [runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/coverage.csv](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/coverage.csv) | Reviewed timeline; optionally select rows relevant to chosen figures |
| [runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/claims.csv](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/claims.csv) | Stable C01–C21 attribution/status/qualification; select C02/C06/C11/C14/C15/C17/C20/C21 for a compact evidence ledger |
| [runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/charts.csv](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/charts.csv) | 14 chart IDs with actual media timestamps, visible observation, interpretive limit, bytes/hashes |
| [runs/17_nq_advanced_amd_video/20261005T172713Z_video17/capture-log.json](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/capture-log.json), [provenance/acquisition.md](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/provenance/acquisition.md), [manifest.json](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/manifest.json), [checks.json](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/checks.json) | Capture method, source/protocol/run identities and historical checks |

Candidate figures (paths below are exact within
`runs/17_nq_advanced_amd_video/20261005T172713Z_video17/`):

| Asset | Media time | Role |
|---|---|---|
| [figures/01_weekly_context.jpg](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/01_weekly_context.jpg) | 3:33 | Conditional weekly thesis, not a forecast distribution |
| [figures/03_quarterly_candle.jpg](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/03_quarterly_candle.jpg) | 8:03 | Optional: illustrate and explicitly qualify the unverified quarterly assertion |
| [figures/06_wednesday_ob_chain.jpg](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/06_wednesday_ob_chain.jpg) | 15:23 | Reaction → structure break → later zone, preserving annotations |
| [figures/07_wednesday_weak_reentry.jpg](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/07_wednesday_weak_reentry.jpg) | 16:28 | Optional counterexample: discretionary quality judgment |
| [figures/09_thursday_no_trade.jpg](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/09_thursday_no_trade.jpg) | 20:08 | No-trade state, speaker-reported abstention |
| [figures/11_friday_news_distribution.jpg](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/11_friday_news_distribution.jpg) | 23:23 | Response to observed expansion and change of view |
| [figures/13_friday_target_shortfall.jpg](../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/13_friday_target_shortfall.jpg) | 24:48 | Broad all-time-high objective was unmet |

Use five core figures (01/06/09/11/13); 03/07 are optional if the page remains
readable. All 14 are saved, but selected files alone enter the public bundle.
Captions should attribute Tmac's lesson and video ID/URL, actual media time,
visible chart context and the saved interpretive limit. Do not recapture the video,
copy full captions, replace annotations or derive executable prices from images.

Proposed section outline:

1. `text` — question/source scope and “qualitative source review only.”
2. `text` — saved finding: conditional higher-timeframe view, local confirmation
   and permission to abstain; distinguish bias from an acceptable entry.
3. `figure`/`text` pairs — weekly context, Wednesday confirmation, Thursday pass,
   Friday revision and target shortfall, interleaved in that order.
4. Optional `table` — vocabulary/claim ledger with claim, attribution, observed
   support, evidence status and limit; use saved claims, not performance statistics.
5. `text` — source-review method: full captions, selected real captures, chart/media
   clock distinctions, dependence of examples from one week.
6. `text` — unverified quarterly regularity, forecast authentication and trade
   performance; incomplete mechanical definitions; no independent profitability test.
7. `text` — source/run/revision/protocol provenance and checks; brief optional notes.

Preparation and compatibility: JPEGs already fit format/size budgets; copy selected
exact bytes into regular files next to the new source. Write alt text and captions,
condense saved prose without changing interpretation, and select claim-table columns.
Source URLs can be shown in plain text today; clickable citations/related links
require later implementation. Do not insert unsupported citation, video-embed or
study-ID fields. Omit metrics; coverage counts would not establish strategy efficacy.
Confirm suitability of source excerpts for the intended public selection before any
later deployment; source review authorization itself was local, not public release.

Content checks: selected figure SHA-256/bytes against charts.csv and manifest;
actual paused timestamp against capture log; every caption/claim against report,
chart/claim IDs and saved qualifications. Preserve Thursday abstention, Friday
reassessment, unmet target and quarterly uncertainty. Keep chart UTC+4 indications
distinct from NY assumptions and media time. Check no unaudited point/R example
becomes a headline return. No new source fetch or market calculation is required.

Browser checks: narrow/desktop figure detail and text sizes, meaningful alt/captions,
section ordering/anchors, claim-table keyboard scroll, evidence wording visible
near the introduction, publication/asset links and absence of a full transcript or
private locator in output. Expected deliverables: new revision with source JSON,
five selected JPEGs (optional two), source map, manifest and check record; one staged
bundle/index entry; static qualitative pilot page and browser verification record.
No study metadata change, market test, strategy promotion or deployment.

### Pilot execution gates and remaining batch order

When Phase 2 is separately authorized, author and check the revisions first. From
`apps/narada` with its existing environment, use the publisher on each revision's
source (replace placeholders with the concrete new paths):

```sh
npm run report:publish -- --report ../../reports/exports/<study-id>/<source-run-id>/<revision-id>/publication.json --dry-run
npm run report:publish -- --report ../../reports/exports/<study-id>/<source-run-id>/<revision-id>/publication.json
npm run verify
npm test
npm run lint
npm run build
npm run preview
```

The dry run validates report schema, bounded bytes, raster paths/signatures and
existing catalog consistency; it does not validate findings. `build` runs the
static-export verifier afterward. Inspect the generated homepage and both report
routes via the preview. Preserve any genuine existing publications and unrelated
working changes; never hand-edit generated bundles/catalog or leave example fixtures
in delivery. These commands are handoff instructions, not Phase 1 work performed.

Suggested remaining publication batches, after pilot acceptance:

1. **07 and 13:** compact negative/uncertain evidence; establish that the shared
   format preserves disappointing results as clearly as favorable descriptions.
2. **06 and 11:** quantitative probability atlases and comparison/uncertainty
   conventions. Keep 06's exploratory supplement and 05's context as separately
   identified related publications rather than expanding the primary source silently.
3. **08, 09 and 10:** denominator-sensitive Range XV sequence; publish source
   studies before their cross-study overlay and introduce their explicit relationships.
4. **12:** static selection from the interactive grid; retain its existing corrected
   HTML export as local evidence. Defer richer selectors to Phase 4.
5. **14, 15 and 16:** source selection for 14/16, multi-protocol/session or model
   complexity, strict cohort/unit limits and extensive evidence. Start with concise
   summaries; design related publication identities before expanding their coverage.
6. **01–04:** resolve historical publication-source/version choices and disclose
   provenance gaps. Prefer bounded historical summaries over implied modern validation.

## Unresolved decisions and later-phase proposals

| Decision / gap | Working direction | Phase / action |
|---|---|---|
| Seven studies without registered references | Candidate sources are proposed above; explicit publication selection does not register a research reference | Phase 2 for 17; Phase 3 batches for the rest; record selection/reason in export manifests |
| Stable study slugs, catalog ownership and featured selection | Small curated catalog owned by Narada; source identities supplied explicitly by Sahadeva | Phase 3 design/validation; no registry implemented here |
| Related-run versus presentation-revision labels | Both retain separate publication IDs; navigation relationships do not mutate old content | Phase 3; decide catalog relationship fields |
| Structured study/evidence/protocol/revision/source references | Use ordinary text/notes and export provenance now | Later contract proposal only if authoring proves the need; no schema change required for pilots |
| Clickable citations, table notes and rich evidence/downloads | Current strings are plain text; generated report JSON/figures already downloadable | Phase 4; explicit selected-download/citation design and public-content review |
| Large tables, SVGs and interactive HTML | Select saved cells, faithfully rasterize SVGs, retain full local evidence | Pilot/batch authoring; rich exploration deferred to Phase 4 |
| Study 17 source excerpts and attribution | Preserve source identity, selected frames and claims' limitations; review intended public selection before release | Phase 2 content selection; any broader transcript/video redistribution outside this plan |
| Static Vercel upload without repository connection | Build Narada locally and release only its static output | Phase 5 chooses and verifies tooling, rollback and immutable release records; no connection now |
| Empty public catalog | Two pilot publications are the first selected entries | Phase 2 only; do not publish the illustrative example as research |

Phase 1 delivery is documentation only. On 2026-10-06,
`python3 scripts/check-agent-docs.py` passed for 27 maintained guides with zero
errors. Inventory consistency checks confirmed all 17 registered IDs, titles,
statuses, evidence wording and reference selections, all 29 run IDs, and the
readiness counts above. New local links resolved. The task diff was reviewed
against the initial working tree; checker changes only register the two new guides.
The research index inputs are unchanged, so no index rebuild/check, numerical
suite or Narada build was run. Public-source validity, static payloads and browser
behavior remain Phase 2 checks; historical provenance gaps and absent research
evidence remain explicit limitations rather than work to fabricate during
publication.

## Phase 2 completion record

Delivered on 2026-10-06 for local static preview only. The Phase 1 inventory above
remains a dated assessment; this work resolves study 17's publication-source
selection without changing its absent registered research reference.

| Pilot | Selected source run | Presentation export | Publication ID / route |
|---|---|---|---|
| 05 · quantitative | Registered reference `20260923T015900Z_vwap3` | [20261006T210008Z_web05](../reports/exports/05_session_vwap/20260923T015900Z_vwap3/20261006T210008Z_web05/README.md) · [manifest](../reports/exports/05_session_vwap/20260923T015900Z_vwap3/20261006T210008Z_web05/manifest.json) | `session-vwap-vwap3-20261006-web05` · `/reports/session-vwap-vwap3-20261006-web05/` |
| 17 · qualitative | Explicitly selected sole complete review `20261005T172713Z_video17`; no reference registration | [20261006T210008Z_web17](../reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261006T210008Z_web17/README.md) · [manifest](../reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261006T210008Z_web17/manifest.json) | `nq-amd-source-review-20261006-web17` · `/reports/nq-amd-source-review-20261006-web17/` |

Both sources passed dry runs and were staged by the publisher under new immutable
IDs. The catalog contains only these two real reports. The static homepage and
report routes render; no hosted state changed. Existing source publication JSONs,
completed runs, datasets, reference selections and evidence wording are preserved.

Reusable decisions established by the pilots:

- Generate quantitative rows and metric notes from saved structured evidence.
  All 96 numeric fields have selectors and transfer checks. Keep rates
  as ratios and convert saved contrasts explicitly to percentage points. Retain
  adverse classes, denominator differences and exploratory baseline qualifications.
- A qualitative page can use text, an attributed claim ledger and selected figures
  without metrics. Five byte-identical captures and eight saved claim rows preserve
  source claims, observed examples and reviewer interpretation separately.
- Faithfully rasterize the quantitative SVG; extend its white canvas only where
  existing labels are clipped. Record the source, geometry-preserving change and
  exact conversion tool. Do not use the source's unlabeled raster as the web chart.
- Keep definitions, limits and source identity visible in ordinary sections.
  The existing four section types suffice for both pilots; no schema change is needed.
- Generic renderer improvements: visible table scrolling/keyboard hint with an
  accessible description, wider first-column labels, unbroken numeric cells, and
  a bounded scrollable desktop contents list. Mobile contents remain in page flow.

Verification: Narada verify, all 14 app tests, lint and static build passed. The
export verifier checked both routes and 35 bounded page payloads. Static content
checks matched all 160 rendered table cells, 22 preview HTTP paths returned 200,
and the missing publication returned the expected 404. Browser inspection covered
the homepage and both pilots at desktop and 390px widths, anchors, keyboard table
scrolling, figures/alt/captions and expanded publication records, with no captured
browser errors. Export verification records retain screenshots and details. Source
hash checks compare consumed artifacts with the sealed manifests and initial working
tree; no research rerun is used as a publication check.

Phase 3 priorities remain the explicit study catalog/stable identity model and the
batch order above. Six other studies still need publication-source choices; study
17's presentation choice is now explicit. Preserve old publication identities and
distinguish supplemental runs from revisions. No study registry, route, search or
filter was added in Phase 2. Navigation inputs to the local research index are
unchanged: study notes gain links, but the index does not read their contents or
discover these exports.

Later proposals remain structured citations/provenance, table notes and related
publication relationships. Long tables still require selections and horizontal
scrolling. Original chart annotations are small on phones; the existing native-size
asset links and descriptive captions are sufficient for this pilot, while richer
figure inspection belongs to Phase 4. Public source-excerpt selection and the
static-output Vercel release procedure remain decisions before a future deployment.

## Phase 3 completion record

Completed locally on 2026-10-06. The Phase 1 inventory and Phase 2 delivery
records above remain historical snapshots. This record advances their proposed
source selections and navigation model using concrete saved-evidence exports.
The registered set remains **17 studies**. All 17 have a stable study page and
one real featured publication: the two preserved pilots and 15 new featured
summaries. There are **19 immutable publication routes** because two earlier
presentations were superseded during baseline wording review.

The authoritative [Narada study catalog](../apps/narada/content/studies.json)
explicitly maps study IDs/slugs, selected public metadata, evidence wording,
featured publication/run IDs and labelled related references. Its
[owned schema](../apps/narada/contracts/studies.schema.json), validator, types and
cached loader read only app-owned metadata and staged publication bundles. No
build discovers studies, runs, exporters, input data or research dependencies.
Array order follows study IDs. Stable study pages link to the existing report
renderer rather than duplicate report bodies. Report pages link back to their
study and show a related-revision label where applicable.

### Final coverage checklist

`R` retains the registered research reference; `P` is a publication-only selection.
`Existing` means accepted Phase 2 coverage at task start. `New` means Phase 3
conversion completed. Every row passed content/hash verification and static
browser route/content checks; pilot content verification records were preserved
and their unchanged sources/bundles were checked again. Export links contain the
publication source, source map, manifest and verification records. Public routes
below are paths under the local static preview, not filesystem targets.

| Study | At start / conversion | Source run / selection | Presentation export | Immutable publication route | Stable study route | Content / browser | Remaining qualification |
|---|---|---|---|---|---|---|---|
| [01_reversal_follow_through](../studies/01_reversal_follow_through/README.md) | None / new, complete | `20260906T_full_v3` / P | [20261006T230936Z_web01](../reports/exports/01_reversal_follow_through/20260906T_full_v3/20261006T230936Z_web01/) | `/reports/01-reversal-follow-through-20261006-web/` | `/studies/reversal-follow-through/` | Passed / passed | Historical import; missing GC20 and original short inputs |
| [02_followthrough_candle_adverse](../studies/02_followthrough_candle_adverse/README.md) | None / new, complete | `20260906T_full_v7` / P | [20261006T230936Z_web02](../reports/exports/02_followthrough_candle_adverse/20260906T_full_v7/20261006T230936Z_web02/) | `/reports/02-followthrough-candle-adverse-20261006-web/` | `/studies/followthrough-candle-adverse/` | Passed / passed | Historical conditional geometry; missing original short inputs; timing proxy |
| [03_multi_rxv_alignment](../studies/03_multi_rxv_alignment/README.md) | None / new, complete | `20260908T_multi_rxv_v1` / P | [20261006T230936Z_web03](../reports/exports/03_multi_rxv_alignment/20260908T_multi_rxv_v1/20261006T230936Z_web03/) | `/reports/03-multi-rxv-alignment-20261006-web/` | `/studies/multi-rxv-alignment/` | Passed / passed | Historical import; ES4 absent; limited execution provenance |
| [04_reversal_candle_quality](../studies/04_reversal_candle_quality/README.md) | None / new, complete | `20260908T_reversal_quality_v1` / P | [20261006T230936Z_web04](../reports/exports/04_reversal_candle_quality/20260908T_reversal_quality_v1/20261006T230936Z_web04/) | `/reports/04-reversal-candle-quality-20261006-web/` | `/studies/reversal-candle-quality/` | Passed / passed | Historical import; negative payoff; limited execution provenance |
| [05_session_vwap](../studies/05_session_vwap/README.md) | Existing / preserved | `20260923T015900Z_vwap3` / R | [20261006T210008Z_web05](../reports/exports/05_session_vwap/20260923T015900Z_vwap3/20261006T210008Z_web05/) | `/reports/session-vwap-vwap3-20261006-web05/` | `/studies/session-vwap/` | Passed / passed | Price paths; paired re-entry comparison remains absent |
| [06_vwap_state_dynamics](../studies/06_vwap_state_dynamics/README.md) | None / new, complete | `20260923T180000Z_state06c` / R | [20261006T230936Z_web06](../reports/exports/06_vwap_state_dynamics/20260923T180000Z_state06c/20261006T230936Z_web06/) | `/reports/06-vwap-state-dynamics-20261006-web/` | `/studies/vwap-state-dynamics/` | Passed / passed | Exploratory; coarse matching; anchor replications disagree |
| [07_range_xv_edge_candidates](../studies/07_range_xv_edge_candidates/README.md) | None / new, complete | `20260924T004900Z_rxv07` / R | [20261006T230936Z_web07](../reports/exports/07_range_xv_edge_candidates/20260924T004900Z_rxv07/20261006T230936Z_web07/) | `/reports/07-range-xv-edge-candidates-20261006-web/` | `/studies/range-xv-edge-candidates/` | Passed / passed | Negative screen; original clock cohort retained |
| [08_countertrend_bar_continuation](../studies/08_countertrend_bar_continuation/README.md) | None / new, complete | `20260924T132916Z_ctbars_v1` / R | [20261006T235500Z_web08r2](../reports/exports/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/20261006T235500Z_web08r2/) | `/reports/08-countertrend-bar-continuation-20261006-web-r2/` | `/studies/countertrend-bar-continuation/` | Passed / passed | Corrected baseline wording in r2; no positive frozen-screen lift |
| [09_range_xv_c2_confirmation](../studies/09_range_xv_c2_confirmation/README.md) | None / new, complete | `20260924T141810Z_c2confirm_v1` / R | [20261006T230936Z_web09](../reports/exports/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/20261006T230936Z_web09/) | `/reports/09-range-xv-c2-confirmation-20261006-web/` | `/studies/range-xv-c2-confirmation/` | Passed / passed | Confirmed/original opportunity denominators differ; age-two cut deferred |
| [10_range_xv_session_overlay](../studies/10_range_xv_session_overlay/README.md) | None / new, complete | `20260924T145715Z_session_v1` / R | [20261006T235500Z_web10r2](../reports/exports/10_range_xv_session_overlay/20260924T145715Z_session_v1/20261006T235500Z_web10r2/) | `/reports/10-range-xv-session-overlay-20261006-web-r2/` | `/studies/range-xv-session-overlay/` | Passed / passed | Corrected other-segment label in r2; unequal upstream samples |
| [11_vwap_conditional_probabilities](../studies/11_vwap_conditional_probabilities/README.md) | None / new, complete | `20260924T155331Z_vwap11` / R | [20261006T230936Z_web11](../reports/exports/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/20261006T230936Z_web11/) | `/reports/11-vwap-conditional-probabilities-20261006-web/` | `/studies/vwap-conditional-probabilities/` | Passed / passed | Exploratory; competing/ambiguous outcomes; frozen A target |
| [12_gc_ema_band_excursions](../studies/12_gc_ema_band_excursions/README.md) | None / new, complete | `20260925T223721Z_gc_ema_excursions_v1` / R | [20261006T230936Z_web12](../reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/20261006T230936Z_web12/) | `/reports/12-gc-ema-band-excursions-20261006-web/` | `/studies/gc-ema-band-excursions/` | Passed / passed | Retrospective yearly/default-grid selection; no interactive HTML import |
| [13_gc_ema_band_filter_validation](../studies/13_gc_ema_band_filter_validation/README.md) | None / new, complete | `20260926T000219Z_gc_band_filters_v1` / R | [20261006T230936Z_web13](../reports/exports/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/20261006T230936Z_web13/) | `/reports/13-gc-ema-band-filter-validation-20261006-web/` | `/studies/gc-ema-band-filter-validation/` | Passed / passed | Uncertain 2026 change; not pristine holdout |
| [14_asia_session_vp_levels](../studies/14_asia_session_vp_levels/README.md) | None / new, complete | `20260929T124500Z_asiavp_b2` / P | [20261006T230936Z_web14](../reports/exports/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/20261006T230936Z_web14/) | `/reports/14-asia-session-vp-levels-20261006-web/` | `/studies/asia-session-vp-levels/` | Passed / passed | Original A–C only; D/E separate; original event-manifest gap |
| [15_vwap_excursion_response](../studies/15_vwap_excursion_response/README.md) | None / new, complete | `20260929T234000Z_a15f` / R | [20261006T230936Z_web15](../reports/exports/15_vwap_excursion_response/20260929T234000Z_a15f/20261006T230936Z_web15/) | `/reports/15-vwap-excursion-response-20261006-web/` | `/studies/vwap-excursion-response/` | Passed / passed | Twenty-minute saved findings only; boundary/sparse uncertainty; no Pine parity |
| [16_range_xv_reversal_paths](../studies/16_range_xv_reversal_paths/README.md) | None / new, complete | `20261002T010500Z_ohlc200_161001` / P | [20261006T230936Z_web16](../reports/exports/16_range_xv_reversal_paths/20261002T010500Z_ohlc200_161001/20261006T230936Z_web16/) | `/reports/16-range-xv-reversal-paths-20261006-web/` | `/studies/range-xv-reversal-paths/` | Passed / passed | Negative primary prediction; censoring/unit-era and execution limits |
| [17_nq_advanced_amd_video](../studies/17_nq_advanced_amd_video/README.md) | Existing / preserved | `20261005T172713Z_video17` / P | [20261006T210008Z_web17](../reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261006T210008Z_web17/) | `/reports/nq-amd-source-review-20261006-web17/` | `/studies/nq-advanced-amd-video/` | Passed / passed | Qualitative only; selected source charts; independent performance unverified |

### Actual publication-only choices

No study metadata was changed. These choices resolve public source selection,
not the absence of a registered research reference:

- **01:** `20260906T_full_v3` retains expanded chart-selection decisions and
  companion excursion context, including no clear winner and missing GC20.
- **02:** `20260906T_full_v7` contains the explicitly corrected full-leg duration
  definition alongside conditional second-candle geometry.
- **03:** `20260908T_multi_rxv_v1` is the sole retained direct-question alignment
  run; strict timing and historical provenance qualifications remain visible.
- **04:** `20260908T_reversal_quality_v1` is the sole direct candle-quality
  follow-up and preserves the negative price diagnostic.
- **14:** `20260929T124500Z_asiavp_b2` answers original protocol 1.0.0 A–C.
  The separate exploratory D/E extension is outside this featured publication.
- **16:** `20261002T010500Z_ohlc200_161001` is the sole completed protocol 2.0.0
  run covering the registered questions, including negative primary results.
- **17:** retain Phase 2's `20261005T172713Z_video17` source-review selection.

These reasons and registered-reference retention are recorded in each new
manifest. No selection was inferred from run-ID ordering. Study 10 retains its
own overlay identity and names the three upstream run IDs in its methods;
Study 05's separate exploratory run is not silently combined into the pilot.

### Preparation and presentation decisions

Study-specific `publish_web.py` files beside each remaining study consume only
pinned saved reports, protocols, manifests and explicit CSV row/column selectors.
They neither invoke research nor compute totals, cohort aggregates, intervals
or models. All 15 new featured reports use bounded, table-first summaries; the
six raster assets from the pilots remain unchanged. Large grids and original
SVG/interactive HTML stay in the source evidence. Study 15 uses the twelve
actual twenty-minute rows in `findings.csv`; the source prose also mentions a
longer horizon, but this export does not fabricate absent concise-table rows.

Source maps bind all table cells to the saved CSV row, field, raw value and any
unit conversion, and identify actual saved-document headings for abridged prose.
Numeric values remain numeric, percent values are ratios, null remains unavailable,
and unit/precision labels are explicit. Study 10's percentage-valued source cells
are divided by 100 for the contract; already-percentage-point contrasts remain
unchanged. Models in Study 11 label the saved relative Brier change with its
original sign. Study 16 retains pointwise and five-session uncertainty and separates
bar-order from strict-price denominators. Historical pages retain import grades;
publication/browser review does not revalidate their original execution.

Each new revision contains a source map, frozen exporter, independent cell/hash
check, verification records and manifest with source/output SHA-256 hashes,
exact preparation/publisher commands, code revision, Node/Python versions and an
archival snapshot of the uncommitted renderer/catalog identity. Snapshots are
provenance records, not competing maintained catalogs. The active study exporter
may evolve; an older revision's retained exporter and recorded reconstruction
check identify its exact presentation. Manifest hashes exclude the manifest itself.

**Corrections during staging:** initial 08 and 10 presentations incorrectly
used fifty-percent wording for a matched chart/window or other-segment baseline.
Saved numerical values were correct. The corrections use new publication IDs
ending `-web-r2` and new revisions `20261006T235500Z_web08r2` /
`20261006T235500Z_web10r2`. Old immutable routes and source revisions remain;
the catalog labels them as superseded, and their report context directs readers
to the corrected featured publication. Both numerical/source identities were
checked; the old wording is explicitly a known correction, not approved interpretation.

Generic changes reuse existing styling: study evidence panels, explicit featured
and related links, report-to-study navigation and a study-library header link.
Focusable table overflow, contents anchors and figure presentation established
in Phase 2 remain shared. React review confirmed Server Components, cached bounded
reads, semantic links/landmarks and no client analytical dependencies.

### Verification and preservation

- **Content:** independently checked **2,698 numeric cells / 3,540 total cell
  bindings** across the 15 new featured reports; raw saved cells, declared scaling,
  nulls, full JSON precision and frozen-export reconstruction match. Prose was
  reviewed against executed reports/protocols, retaining uncertainty, adverse
  evidence and exclusions. Superseded revisions have separate correction records.
- **Application:** Node `v24.18.0`, existing npm lock and installed dependencies;
  `npm run verify`, `npm test` (**22 passed**), `npm run lint`, and `npm run build`
  passed at the final gate. Static verification checked 17 study routes, 19 report
  routes and **341 bounded payloads**. No dependencies were installed for Phase 3.
- **Browser:** served `apps/narada/out` with `npm run preview` at
  `http://127.0.0.1:4173`. Visited every study and featured publication, plus both
  superseded routes. Compared each report's rendered table cells and plain text
  with its staged source. Inspected desktop **1440×1000** and narrow **390×844**
  quantitative, qualitative, historical and table-heavy layouts; checked contents
  anchors, table arrow-key scrolling, keyboard skip navigation, related correction
  links, evidence panels, figure alt/captions and publication-record disclosure/link.
  Six actual raster assets loaded; no document-wide horizontal overflow in inspected
  layouts. Browser error/warning logs were empty. Lazy images were checked after
  becoming visible or by their native asset links, rather than treating an immediate
  offscreen probe as a missing asset.
- **HTTP:** **62** selected homepage/study/report/publication-record/figure URLs
  returned 200. Unknown study, unknown publication and research-directory paths
  returned 404 with the missing-page view. No missing selected asset requests.
- **Preservation:** initial **2,504** local file hashes were retained (bounded
  baseline excludes files above 20 MiB and generated dependencies/build caches).
  Consumed numerical files are within that baseline. Initial completed runs,
  prior exports, pilot public bundles/assets, research metadata and existing
  unrelated work remain unchanged. Study notes were appended with local export
  references; historical studies received publication notes. Original report,
  bundle and publication-index contracts remain unchanged; only the new app-owned
  study-catalog contract was added. No dataset writes, research runs, deployment,
  commit, push or hosted changes occurred.
- **Documentation:** `python3 scripts/check-agent-docs.py` passed. Existing
  maintained owning guides were updated; no new guide-list registration or checker
  behavior change was required. The research-index inputs were unchanged: no study
  metadata, run registration or strategy metadata changed, so its check/regeneration
  was not required.

### Remaining limitations and Phase 4 priorities

No study is blocked and no required Phase 3 verification gate remains outstanding.
Full numerical tables, excluded variants and prior provenance gaps are preserved
locally. The original research uncertainties in the coverage checklist remain;
web presentation does not fill them. Browser inspection is local, with two shared
viewport sizes; no hosted/browser-matrix compatibility claim is made.

Phase 4 can add selected faithful raster evidence for table-first studies, a few
traceable downloadable artifacts with explicit public selection, and richer source
references/notes where useful. Keep negative, ambiguous and incomplete evidence
visible. Prioritize denominator/coverage aids for 06/11/15, selected comparison
figures for 07/13/16, and clear historical provenance context for 01–04. Treat the
14 D/E extension as a separately attributed exploratory publication if selected.

Later contract proposals remain unimplemented: typed external citations, per-table
notes/denominator metadata, and a public study identity in publication provenance.
The current report contract has only producer/run ID; the catalog explicitly
asserts its run mapping and enforces single-study publication ownership, while
source maps/manifests establish the actual local study attribution. No richer
catalog search/filtering, downloads, interactive charts or release/deployment
workflow was introduced. Phase 4 and Phase 5 have not begun.

Local visual records: [library](assets/narada-phase3-library.png),
[mobile table](assets/narada-phase3-table-mobile.png), and
[mobile qualitative chart](assets/narada-phase3-qualitative-mobile.png).


## Phase 4 completion record

Completed locally on 2026-10-06 (new publication timestamps are 2026-10-07 UTC).
Phase 3 coverage/navigation was complete before work: 17 studies, 19 publications
and six selected rasters. The existing dirty working tree was recorded before
editing. No earlier bundle, source run, export or study metadata was rewritten.

Three quantitative studies now expose deeper selected evidence; Study 17 receives
an additional attribution revision of the same review. The library still covers
17 studies and now contains 23 immutable publications, 16 selected raster assets
and six bounded summary CSVs. The authored catalog explicitly features the new
IDs and retains the previous IDs as `presentation-revision` relationships.

The cell-map paths below are workspace-relative private artifact locators. These
files are excluded from Git and require exact-byte restoration from separately
retained copies; their paths and hashes are recorded in the
[GitHub bulk artifact inventory](github-bulk-artifacts.json).

| Study / reader need | Source and revised publication | Delivered evidence / size |
|---|---|---|
| 12 — Separate annual path scale, valid denominators and exclusions | Run `20260925T223721Z_gc_ema_excursions_v1`; publication `12-gc-ema-band-excursions-20261007-evidence`. [Export](../reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/20261007T002932Z_evidence12/README.md) · [Source](../reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/20261007T002932Z_evidence12/publication.json) · [Manifest](../reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/20261007T002932Z_evidence12/manifest.json) · Cell map: `reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/20261007T002932Z_evidence12/source-map.json` · [Checks](../reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/20261007T002932Z_evidence12/verification.json) | Four tables (17/17/17/7 rows), one exact saved-value annual mean/interval plot; one 119-row ×22-column CSV, 20,439 bytes. JSON 32,329 bytes; raster 74,459 bytes. |
| 15 — Separate anchor/product/horizon cohorts and return, endpoint and barrier-first outcomes | Run `20260929T234000Z_a15f`; publication `15-vwap-excursion-response-20261007-evidence`. [Export](../reports/exports/15_vwap_excursion_response/20260929T234000Z_a15f/20261007T002932Z_evidence15/README.md) · [Source](../reports/exports/15_vwap_excursion_response/20260929T234000Z_a15f/20261007T002932Z_evidence15/publication.json) · [Manifest](../reports/exports/15_vwap_excursion_response/20260929T234000Z_a15f/20261007T002932Z_evidence15/manifest.json) · Cell map: `reports/exports/15_vwap_excursion_response/20260929T234000Z_a15f/20261007T002932Z_evidence15/source-map.json` · [Checks](../reports/exports/15_vwap_excursion_response/20260929T234000Z_a15f/20261007T002932Z_evidence15/verification.json) | Twelve six-row tables split across four anchors; 20-/100-minute departure, touch endpoint and barrier classes; two unchanged-value saved SVG rasterizations. Two 24-row CSVs, 9,280 bytes total. JSON 63,406 bytes; rasters 190,488 bytes. |
| 16 — Separate colour persistence, primary prediction and strict price paths | Run `20261002T010500Z_ohlc200_161001`; publication `16-range-xv-reversal-paths-20261007-evidence`. [Export](../reports/exports/16_range_xv_reversal_paths/20261002T010500Z_ohlc200_161001/20261007T002932Z_evidence16/README.md) · [Source](../reports/exports/16_range_xv_reversal_paths/20261002T010500Z_ohlc200_161001/20261007T002932Z_evidence16/publication.json) · [Manifest](../reports/exports/16_range_xv_reversal_paths/20261002T010500Z_ohlc200_161001/20261007T002932Z_evidence16/manifest.json) · Cell map: `reports/exports/16_range_xv_reversal_paths/20261002T010500Z_ohlc200_161001/20261007T002932Z_evidence16/source-map.json` · [Checks](../reports/exports/16_range_xv_reversal_paths/20261002T010500Z_ohlc200_161001/20261007T002932Z_evidence16/verification.json) | Six tables: 16-row continuation, separate 16-row M1/M2 primary later comparisons, 16-row strict paths, four exact unit definitions and eight 6S era rows; two saved audit illustrations. CSV rows 16/32/24, 11,275 bytes total. JSON 49,683 bytes; rasters 42,244 bytes. |
| 17 — Make established qualitative attribution and media ranges clickable | Run `20261005T172713Z_video17`; publication `nq-amd-source-review-20261007-references`. [Export](../reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261007T002932Z_references17/README.md) · [Source](../reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261007T002932Z_references17/publication.json) · [Manifest](../reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261007T002932Z_references17/manifest.json) · Cell map: `reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261007T002932Z_references17/source-map.json` · [Checks](../reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261007T002932Z_references17/verification.json) | Same eight qualitative claim rows and five unchanged chart captures; six creator/title/date/media-range references. No numerical scorecard or download. JSON 19,261 bytes; rasters 440,134 bytes. |

Study 12 retains its registered reference `20260925T223721Z_gc_ema_excursions_v1`;
Study 15 retains `20260929T234000Z_a15f`. Studies 16 and 17 retain their Phase 3
publication-only selections, `20261002T010500Z_ohlc200_161001` and
`20261005T172713Z_video17`; neither acquires a research reference. Each export has
its own sortable revision ID, authoring snapshot, cell/claim source map, manifest,
content/browser/static verification and source/old-publication preservation record.

The current-page inspection found broad tables with context far from values,
Study 15's concise 20-minute-only coverage, limited price-path separation in 16,
and plain URL strings in 17. Sealed `yearly.csv` and `metrics.json` support 12;
15's 39 MB `summary.csv`, frozen protocol and selected saved SVGs support both
horizons and examples; 16's continuation/model/price/unit tables and saved SVGs
support separate views; 17's saved source metadata, report, claims and selected
captures support attribution. Only small selected projections cross into Narada.
The full 15 summary, event ledgers, caption track and authoring snapshots stay local.

The new presentation corrects two earlier webpage labels using concrete saved
definitions: 12's mean bounds are approximate 95% **normal ISO-week cluster**
intervals, unadjusted for multiple comparisons, as named by `metrics.json`; 15's
`directional_delta` is signed continuation endpoint movement, rather than a
continuation-minus-fade difference. Numerical values and research conclusions are
unchanged. Earlier pages keep their bytes and receive catalog labels pointing to
the clarification. This resolves presentation wording, without changing Phase 1's
research-source selections or other unresolved inventory decisions.

**Reusable presentation decisions.** Existing ordered text/metrics/table/figure
sections remain. Version 1.1 adds visible table descriptions/notes, section links
to typed external/saved-artifact references, and explicit CSV declarations.
Version 1.0 remains validated/rendered without migration. The bundle retains its
report/provenance shape; the publication index remains 1.0. No arbitrary HTML,
Markdown, workspace discovery or research runtime enters Narada.

CSV limits are 256 KiB/file, 512 KiB/publication, four files, 1,000 data rows,
24 unique columns and 1,000 characters/cell. File types, containment, symlinks,
UTF-8/CSV structure, headers, row counts, formula cells and declared hashes are
checked. Existing figure/JSON budgets remain unchanged. Download population,
units, scope, filenames and source/content identities are visible. Authoring
verification establishes source-cell equality; the publisher validates selected
bytes without opening research artifacts.

Static figures and distinct tables meet these needs, so no interactive analytical
view was added. Figures have a visible full-size link for small-screen inspection;
short chart/product labels use a smaller generic first-column minimum, while
horizontal overflow stays within accessible table regions. Blank/null cells retain
the existing “Not available” display with a nearby hint and field-specific notes;
blank support flags mean no saved sparse flag, not independent confirmation.

**Verification.** Every displayed quantitative table cell (1,941), downloaded cell
(4,626), annual-plot saved value (102), selected qualitative claim row (eight) and
consumed source hash was checked. The saved SVG conversions reproduce byte-for-byte
under the retained renderer; Study 17 captures are exact source copies. Six CSVs
were checked over local HTTP for row/header identity, bytes/hashes, attachment
filenames, UTF-8 media type and `nosniff`; actual browser downloads for 12 and 15
also matched. Publisher dry-run and normal staging passed for all four sources.
Node 24 verify, 31 focused tests, lint, static build and export checks pass, as does
the documentation checker. Source/old-publication hashes, metadata and prior note
prefixes remain preserved; verification records state the audit's scope.

Browser inspection used generated `out/` via port 4174, desktop 1440×1000 and
mobile 390×844. It covered all enhanced reports, table context/uncertainty/local
scrolling, keyboard focus, full-size figure access, six saved references, downloads,
all four stable study/previous-publication mappings, the library, unchanged Study 05,
an earlier Study 15 revision and 404 behavior. No unexpected browser errors or
missing selected assets were found. The narrow-screen inspection led to the
full-size figure cue, smaller short-label columns and missing-cell hint. Source
URLs were checked against saved attribution; the external lesson was not newly
investigated. Browser/HTTP records distinguish these checks from research validation.

**Remaining limits and Phase 5 requirements.** Wide evidence tables require scrolling;
raster labels may require the full-size view. CSV column keys retain source names;
units/scope live beside each file. Schema 1.1 does not express per-column missing
labels, semantic analytical validation or a machine-validated presentation manifest.
A future narrowly scoped column dictionary/missing-label field is optional; it must
retain old-version support and source definitions. Do not infer trade effectiveness
from examples, extrema, marginal bounds or dependent cohorts. Unresolved source
selections for other studies remain as recorded in Phase 1.

Phase 5 must freeze an explicit accepted catalog/bundle/static-output set, record
release and asset hashes plus Node/lock/tool identities, make a repeatable local
build/verification and rollback procedure, and implement the separately authorized
static-output upload to Vercel without a repository connection. Verify hosted deep
routes, 404s, HTTPS source links, CSV media/disposition/filenames, image assets and
mobile/keyboard behavior against the released bytes. Provider-specific headers and
deployment protection must be tested there. No deployment, Vercel/GitHub/CI setup,
commit, push or hosted state change occurred in Phase 4.


## Phase 5 completion record

Completed on 2026-10-06 local time (2026-10-07 UTC). Phase 2–4 content, static and
browser gates were present before release work. The selected scope remains
17 studies, 23 immutable publications, 16 raster figures and six summary CSVs.
No catalog selection, report bundle, completed run, earlier export, research
finding or evidence status changed. No new analytical work was performed.

**Live release.** The [production outcome](../apps/narada/releases/20261007T014040Z_abdf5f57/outcome.json)
records that [production](https://abacus-narada.vercel.app) serves
`20261007T014040Z_abdf5f57`, deployment `dpl_8Ku2riANm66q78uvYSRwkFWJka2t`,
READY in project `abacus-narada` (`prj_yNCdZap19oy5BDaDlI8U8F2lnxdE`), team
`brew-vee` (`team_Nw4wZvuRefB6IZzHok6sIPul`). The dedicated project has no Git
connection, framework or remote source build. Existing unrelated projects and
team protection policy were preserved. Authentication used normal Vercel CLI
login; no authentication secrets are included in release metadata or output.

The accepted [preview](https://abacus-narada-9d8m849h7-brew-vee.vercel.app),
`dpl_FKgzaobiTjtxN7UuEfNRedyBmFTv`, and
[staged production](https://abacus-narada-j5brv0lgy-brew-vee.vercel.app),
`dpl_8Ku2riANm66q78uvYSRwkFWJka2t`, used the same prepared artifact. Promotion
assigned the production hostname to that verified production deployment; it did
not rebuild or promote a preview into a different build.

**Workflow and identity.** The [release guide](../apps/narada/releases/README.md)
documents preparation, binding, preview, production staging, complete hosted
verification, promotion, updates and rollback. `npm run release:prepare` runs local
gates and stops after freezing an isolated artifact. Build/verify never deploy.
The adapter deliberately produces Build Output API v3 from Next's static export:
only selected pages, navigation payloads, runtime assets, public bundles, rasters
and CSVs are uploaded. Explicit page routes and a status-404 fallback preserve
missing-page behavior; CSV attachment, UTF-8 media and `nosniff` headers are set.
Private source maps, manifests, caption archives, event ledgers, research code and
the dirty-source snapshot remain outside the deployment directory.

The [release record](../apps/narada/releases/20261007T014040Z_abdf5f57/release.json),
[checksum inventory](../apps/narada/releases/20261007T014040Z_abdf5f57/checksums.json)
and [source audit](../apps/narada/releases/20261007T014040Z_abdf5f57/source-audit.json)
retain Node 24.18.0, npm 11.16.0, Vercel CLI 62.7.0, Git revision and dirty app
identity, lock/catalog/index hashes, publication and asset identities, preparation
commands and verification results. The artifact inventory SHA-256 is
`70f14f1f2e75c75072098c591a243d64eb1df2a81cb82b7aa6fcbe5349562190`;
437 static files total 8,146,761 bytes. Ignored `.release-artifacts/<id>/deploy/`
retains the exact upload and separate `source/` retains necessary uncommitted app
inputs. Metadata is durable under `apps/narada/releases/`; deployment and gate
events append without rewriting preparation. The private explicit
[release-source locators](../apps/narada/content/release-sources.json) are used by
the provenance audit only, never the website build.

**Verification.** Node 24 verify, 38 tests (seven focused release tests), lint,
build and static-export checks pass. Release tests cover explicit output selection,
checksums/copying/symlink rejection, incomplete inputs, static routing/headers,
production staging, structured CLI output, binary HTTP response parsing, command
failures and rejection of authentication walls or changed hosted bytes. Source
and retained-export integrity was checked for 1,291 files; prior content checks
and research qualifications remain explicit, including superseded presentations.
No statistical suite, research rerun or dataset rebuild was used as a release gate.

Preview and staged production were checked with authenticated Vercel CLI curl;
public production was independently checked with anonymous HTTPS. Each accepted
gate checked every one of the 437 file hashes plus five unknown/private paths
returning the exact saved 404 body and status. All selected study/report routes,
Next navigation payloads, 16 images and six CSVs passed. CSV filenames, MIME and
`nosniff` passed; an actual public browser download also matched its saved hash.
Desktop 1440×1000 and mobile 390×844 inspections covered quantitative 05,
historical 01, table-heavy 11, enhanced 15 and qualitative 17, plus the library,
study/featured/related navigation, contents anchors, keyboard table overflow,
figure captions/alternative text, references, publication records and missing
pages. No material application console errors or missing selected assets were
found. Public browser review used the independent in-app browser without needing
a Vercel login. Screenshots remain in the ignored release evidence directory;
HTTP/browser events distinguish source validation from hosting checks.

**Operational findings and rollback.** The first CLI upload unexpectedly
assigned production for the new project; its separate bootstrap record retains
that outcome. A provider feedback loader changed runtime bytes on that deployment
and on the initial corrected preview. Both failed exact hosted checks. The optional
feedback toolbar was disabled only on the dedicated project; protection stayed
intact. The same frozen accepted artifact was uploaded again, verified as preview,
staged as production, verified and promoted. CLI JSON deployment output and binary
curl forwarding are handled explicitly in the thin wrappers.

Prior production deployment `dpl_7y8ypnMxwBhaWGQKuLDLvRG5rnLd` belongs to bootstrap
`20261007T013423Z_7df6951f`; its served runtime mismatch makes it unsuitable for
rollback. This is the first accepted release with no earlier verified rollback
target. Keep the current accepted deployment as a future rollback target; prepare
a corrected release if needed now. The guide names the exact command and describes
post-rollback public verification and explicit promotion to resume production
assignment. No rollback was executed for demonstration.

**Remaining limits.** Exact prepared-byte integrity is established, while a
byte-identical rebuild has not been demonstrated. Generated payloads and dirty
source snapshots are retained locally; no off-device backup was verified. Wide
tables still need horizontal scrolling, and raster labels may need full-size
viewing. Existing historical/source-selection gaps and research qualifications
remain as recorded in Phase 1–4. Vercel's first-project auto-assignment and optional
asset injection are documented operational exceptions. No schema, additional
website features, Git integration, CI, recurring automation, custom domain, paid
service, commit or push was introduced. Future content updates require new
presentation revisions and immutable publication IDs, explicit navigation changes
where appropriate, and a fresh independently verified static release.
