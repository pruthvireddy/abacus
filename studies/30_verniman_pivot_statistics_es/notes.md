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
