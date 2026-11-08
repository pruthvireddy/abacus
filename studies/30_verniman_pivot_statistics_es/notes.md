# Decisions — Verniman Pivot Statistics — ES

## 2026-10-31 — Ranked extension authorization and definition freeze

The user authorized all 20 ranked statistics, independently verified evidence,
and two local Narada priority reports. Preserve the completed baseline and its
separate operational correction. The [2.0.0 protocol](protocol-2.0.0.md) and
[matrix](implementation-matrix.md) freeze new definitions before new outcomes,
including fixed opening-distance bands and separate RTH/full-Globex quality.
Prior baseline findings were viewed; this is an exploratory extension after
exposure. Exact baseline source/contract/quality rules and legacy event meaning
remain unchanged. No acquisition, release rebuild, installation, strategy
simulation or hosted deployment is within scope.

## 2026-10-31 — Ranked diagnostic and verification reconciliation

Retain `work/30_verniman_pivot_statistics_es/20261031_ranked_v1/` as an unsealed
diagnostic. Its baseline parity and publication-cell checks passed. Independent
reconstruction found an S11 recross-delay censored-count mismatch: the saved
summary correctly retained incomplete-window censoring, while the checker
expected zero for that delay distribution. The same checker accounting issue
affected S14 disposition counts. S13 summaries also omitted censored flags on
incomplete forward paths; correct those support metadata while preserving all
event/path values and point estimates. Regression-test and independently
reconcile the saved diagnostic before freezing a fresh `20261031_ranked_v2`
for full recomputation. New
diagnostic outcomes have been viewed; this remains an exploratory extension.
No numerical event, cohort or outcome rule is selected from their performance.

The initial parity attempt lacked the original six download projections, which
are not new priority publications. Reconstruct those from recalculated baseline
summaries before complete parity checks. The v1 first-cross chart bins also
needed chronological ordering and explicit selected-range captions; retained
before/after presentation bytes and its separate receipt document that repair.
The new exporter freezes that presentation order directly. Neither repair
changes research estimates or any sealed baseline artifact.

## 2026-10-31 — Study identity and staged execution

- Use the title **Verniman Pivot Statistics — ES** and study ID
  `30_verniman_pivot_statistics_es`. Earlier spoken variants of the name do
  not create separate studies.
- Preserve the full approved [roadmap](plan.md). Implement and execute only
  Phase 1: protocol, retained-source/coverage audit and a concrete data request.
  Later phases require progression after reviewing that handoff.
- Requested dates are 2020-01-01–2026-10-30 inclusive. Existing market-data
  coverage is not assumed to span that calendar; required historical delivery
  contracts may differ from volume lead. Acquisition remains a separate step.
- Use the exact ES contract quoted in each source plan and unadjusted prices.
  Do not map unresolved generic ES or image-only contracts by price matching.
- Single-price pivots form the primary sample. Preserve zones, multiple
  candidates, uncertain source roles/dates and absent prices as audit states.
  A source row with unreviewed required semantics is not automatically eligible.
- Nominal 09:25 plan timing is the intended observation convention. Retained
  historical `available_at: null` remains null; later captures and source
  publication/update claims do not prove pre-open availability.

## 2026-10-31 — Features and events

- VWAP uses one-minute HLC3 weighted by volume, anchored at 18:00 New York.
  EMA20/50 uses completed five-minute closes; EMA6 uses completed three-minute
  closes. Full-session same-contract EMA history carries through RTH and year
  boundaries with 250 preceding valid bars of each timeframe.
- The 09:30 price seed is the actual open. Indicator snapshots are as-of the
  observation time. The opening state is not a crossing.
- Count strict close-side transitions with no buffer. Equality retains the
  previous strict side; a first strict side with no seed initializes state.
- An EMA6 already aligned at a price cross is distinct from a true line
  crossing. Delayed EMA confirmation must occur before the reverse price close;
  same-close reverse events belong to the new price episode.
- Distinguish information available at a signal from subsequent labels.
  A returned break without confirmation is recognized only when it returns.
  Day-end incomplete episodes remain censored, not failed/shallow by default.
- Primary horizon is 30 minutes, with 15/60-minute, section-end and 16:00
  context. Full fixed horizons may not spill past RTH. Excursions exclude
  the signal bar's earlier price path.
- Preserve all-cross recurrence plus first-event-per-day/section panels.
  Five-observed-session moving-block bootstrap: 2,000 replicates, seed
  20261031; fewer than 30 distinct days is a sparse cell.
- Retests use the first subsequent completed three-minute bar containing the
  exact pivot, completed by the earlier of 30 minutes after an actual EMA6
  crossing and 16:00. Preserve touch-bar hold/failed/equal close and infer no
  intrabar order. Occupancy is sampled three-minute close counts/shares.
- Recent panels are the trailing 20/60/120 eligible observed sessions at the
  2026-10-30 requested cutoff, with actual usable bounds and gaps disclosed.

## Evidence status

No pivot behavior, feature values, outcome estimates, strategy edge or
profitability findings are claimed here. The current protocol/settings express
agreed definitions and the authorized audit scope. A future numerical execution
must retain its own pre-execution freeze, input pins, actual checks and
completion records. No Narada report is selected and no deployment is authorized
by this planning record.

## 2026-10-31 — Repository-only execution steering

The user cancelled external acquisition and authorized continuation through the
full descriptive evidence/statistics/local Narada workflow using only retained
pivots and market data, reusing compatible prebuilt OHLCV wherever possible.
Actual retained market data currently ends 2026-09-18; the requested calendar
through 2026-10-30 remains a coverage obligation, not invented data. Preserve
unavailable contracts/dates as exclusions and the earlier Phase 1 audit as its
original record. No further phase permission is needed within this scope.
Hosted deployment and subsequent strategy execution remain separate.

## 2026-10-31 — Complete evidence and observed exposure revision

The unsealed `20261031_repo_v1` diagnostic execution passed independent numerical
and source-cell checks. Its outcomes were viewed before this revision. Preserve
that stage; it is not selected as completed evidence or published in Narada.

`20261031_repo_v2` adds full crossing-time EMA/VWAP snapshots and stable links
from events, confirmations and outcomes. It also saves observed-hour exposures
and crossing rates, already required by the approved plan. Event formation,
source/day eligibility, episodes, horizons and price-path outcomes are unchanged.
Compare all original evidence fields and original summary rows to the retained
first stage before selecting the completed run. No rule is selected using the
first stage's performance. This is retrospective exploratory research, not a
pristine holdout evaluation.

The plotting dependency is absent from the locked Python environment. The
presentation-only fallback uses the already installed Narada Sharp/SVG renderer
from saved summary cells, with its Node package lock, exact source-row bindings,
renderer versions, command and PNG/SVG hashes retained. No dependency is installed
or synchronized, and the website performs no analytical calculations.

## 2026-10-31 — Selected completed evidence

Selected `20261031_repo_v2` for complete crossing snapshots, observed-hour rates,
independent verification and six saved Narada views, not performance or recency.
Original event/outcome fields equal the retained unsealed first stage; original
summary values agree within 8.53e-14 of floating-point roundoff. Diagnostics and
negative/inconclusive findings remain retained. No hosted deployment occurred.

The sealed local-verification receipt prematurely marked its first HTTP smoke
attempt as passed, although its retained log shows a local-access failure. The
separate [operational correction](../../reports/exports/30_verniman_pivot_statistics_es/20261031_repo_v2/20261031_local_verification_correction_v1/manifest.json)
records the actual successful rerun with local-network access. It supersedes
only that check; sealed evidence and public bundles remain unchanged.


## 2026-10-31 — Selected ranked extension

Selected `20261031_ranked_v2` after 173 source-bound tests, baseline parity,
independent native/summary reconstruction and local publication/application/browser
checks. The failed ranked v1 remains unsealed diagnostic evidence. Complete
private summaries, whole-day bootstrap settings, period rosters and exact public
cell/asset maps were prepared before sealing. Two priority reports use the new
run; the original six retain `20261031_repo_v2` in a separate catalog analysis.

The separate [post-seal verification](../../reports/exports/30_verniman_pivot_statistics_es/20261031_ranked_v2/20261031_final_verification_v1/manifest.json)
passed the full 105-publication source audit, final publication transfer and
sealed artifact hashes. The original baseline, six public bundles and its
operational correction remain byte-identical. The 88,824,148-byte private ranked
summary remains local and manifest-pinned, excluded from ordinary Git history
with an additive locator. No acquisition, dependency installation, trade
simulation or hosted deployment occurred. Remaining limitations are recorded in
[verification](verification.md).

## 2026-11-07 — Notebook as the study authoring document

The user clarified that all study analysis should live in an IPython notebook
that is part of this study. Abacus Narada should present a rendered version of
that notebook with code omitted. Design iteration should establish the actual
notebook first; website mockups follow once its structure and content are settled.

The November 3 notebooks are saved-report readers generated from publication
JSON. Their cells call display helpers, and their edits do not drive Narada.
They preserve useful saved findings but do not fulfill this authoring preference.
Keep those completed presentation revisions and the research record intact.

The intended workflow is an authored study-local notebook, followed by a
verified executed snapshot, then an explicit export of its saved narrative and
selected outputs into Narada's publication contract. Questions, study-specific
analysis code, comparisons, denominators, chart/table generation and findings
belong in readable notebook cells. Generic data loaders can still be imported.
The notebook's narrative is authored once; there is no independent prose
specification for the website to diverge from it.

Each insight is a logical group of cells: heading/question, brief description,
analysis code, findings summary and supporting chart/table. The reader-facing
order is heading, description/findings, then evidence. Private setup/scratch
cells remain explicitly distinguished from publishable content. The exported
page omits code and execution prompts, and preserves selected cell order,
wording, saved values and figures; Narada supplies its typography and navigation.

The recommended first review is a small notebook version with representative
crossing-frequency, conditional-comparison and forward-outcome insights. Review
readability and authoring before expanding the rest. After the notebook is
settled, compare website layout mockups that render that same content. These
prototype choices are recommendations, not completed implementation or executed
findings. Future calculation changes retain the existing protocol, input pins
and new-run requirements. Actual fresh-kernel execution, source/output checks
and any subsequent publication/deployment remain separately recorded work.

## 2026-11-07 — Authorized and built three-insight notebook V1

The user authorized a demonstrative study-local notebook with actual analysis
code in its cells and exactly three insight forms: one table, one trend-line
chart and one bar chart. Each insight's reader-facing order is its heading,
brief purpose, findings/inference summary and visual evidence. Notebook review
precedes website mockups.

The editable [V1 notebook](vern-pivot-cross-statistics.ipynb) implements that
scope from the retained `20261031_ranked_v2` ledger. Its table classifies initially
unconfirmed price breaks; its line connects annual EMA6–pivot crossing means;
its bars compare mean daily crossing rates per observed hour across RTH sections.
The line is descriptive, without a fitted regression or trend-significance claim.
All calculations, dynamic finding summaries and figure/table generation live in
visible notebook cells. The separate helper only validates structure and runs a
fresh kernel with provenance receipts.

The [notebook input lock](notebook-v1.inputs.lock.json) identifies the six saved
source artifacts and workspace environment lock. The optional `notebooks`
dependency group was installed into the existing `.venv`; no previously locked
dependency version changed. Each replay creates new staged output under `work/`.
The [verification record](verification.md#authored-three-insight-notebook-v1--november-7-2026)
identifies the actual executed snapshot, 11 passing saved-result comparisons,
202 passing study tests and separately recorded workspace input failures.
This is an editable review version, not a replacement sealed research run.
The earlier reader notebooks, completed runs and Narada bundles are preserved.

## Research paper design selected — theme redesign proposed

The user selected the Research paper mockup and requested theme tabs, each
containing a series of notebook-authored insights. They explicitly asked for a
plan first, followed by implementation. The [redesign plan](plan.md#notebook-and-theme-redesign-plan)
proposes six themes covering all 20 existing pivot question families, retains
the separate VWAP-only populations as companion evidence, and stages delivery
through the reviewed three-insight slice before the complete pivot edition.

The selected design and notebook-as-source requirement are decisions. Theme
names, question placement and rollout remain proposed for review. This planning
step changes documentation only; it does not expand the notebook, calculate
results, export publications or implement/deploy Narada changes.

## Six-theme notebook and local Narada implementation authorized

The user approved the preceding plan and authorized expansion of the notebook
into all six themes and implementation of the Research paper design on Narada.
The notebook remains the authoring source; the website receives selected saved
narrative and evidence with Python source omitted. This approval covers the
retained-data analytical reproduction, verified local publication and UI work.
It does not authorize acquisition or hosted deployment.

Stage the new notebook execution as `20261108T035627Z_notebook_themes_v2`, with
`20261031_ranked_v2` retained as the upstream evidence reference. Record actual
execution, comparison, export and application checks before selecting or sealing
the new result. Historical runs and the V1 notebook execution remain unchanged.

## Six-theme notebook edition implemented

Selected `20261108T040901Z_notebook_themes_v2` after fresh-kernel execution of all
68 code cells, 86 saved-row comparisons covering all 21 insights, 225 study tests,
exact narrative/table/PNG transfer and local Narada application/browser checks.
The six Results tabs follow the approved question map. Earlier ranked/baseline
and VWAP-only reports remain separately attributed in Evidence.

The first execution adapter stopped before analysis on serialized source arrays;
the failed attempt is retained as a diagnostic and a new real-kernel regression
covers the correction. The [verification record](verification.md) identifies
scope and operational attempts. The new edition presents point estimates and
retains upstream event/eligibility definitions; it does not reconstruct vendor
events, re-estimate confidence intervals or select an executable trading policy.
No hosted deployment occurred.
