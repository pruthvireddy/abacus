# Decisions — Verniman Pivot Statistics — ES

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
