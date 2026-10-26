# Executed Stage 1 protocol

Protocol `0.1.0-stage1.2`, frozen before the fresh corrected run on October 10, 2026.
Initial scientific definitions preceded historical scoring; the implementation
correction below followed diagnostic scoring and preceded uncertainty interpretation.
The scientific specification is [plan 0.1.0](plan.md). The user's Stage 1
instruction authorizes implementation, reusable input preparation, development
execution, private report preparation and verification/sealing. Stages 2 and 3
and public staging/deployment remain separately scoped.

The six cells are ES/GC/NQ × independently rebuilt 3m/5m candles. All use the
five-minute first-close-seeded EMA20/50, Wilder ATR14 seeded by fourteen true
ranges, unadjusted same-contract prices and 250 consecutive usable source bars.
State carries across known closures and resets at rolls and unknown/invalid
feature slots. A 500-bar input-only warmup sensitivity documents seed residuals
without changing the primary roster. Fixed inclusive raw-point width minima are
ES 2.4, GC 2 and NQ 10, with epsilon `1e-10 * max(1, abs(threshold))`.

The signal stream uses the slow boundary, both directions, zero cooldown and one
event per selected-EMA pullback. Full strict departure outside the cloud arms;
any slow penetration consumes, including a gap through or a rejected touch.
Acceptance uses the pre-bar state. Invalid data/features, contract changes,
direction changes and equality clear state. Five-minute candles use their
current completed close-derived cloud. Three-minute candles freeze the latest
scheduled five-minute cloud completed at their open, including invalid slots
in that mapping; source and signal contracts must agree.

## Calendar and input qualification

The frozen nominal schedule is the normal New York electronic session
18:00–17:00 for weekday trading dates, with the retained ES/NQ 16:15–16:30
pause omitted. Rule-generated holiday/possibly shortened sessions are retained
as `calendar_uncertified`, unusable records; feature state resets. Their annual
intraday clocks are not individually certified. This conservative input-quality
qualification is frozen before outcomes and removes uncertain support rather
than inferring a closure from absent prices. Actual dates and rule source bytes
are saved in the new input delivery and coverage audit. No VWAP-specific
two-minute exclusions or whole-day eligibility are inherited.

Buckets use New York fixed-clock half-open 3m/5m boundaries with UTC identities
and modeled completion. Every expected source minute and exactly one contract
are required. Partial, empty, mixed and calendar-invalid slots remain quality
records. Unknown missing slots are never compressed or filled. Published source
bytes, manifest pins, instrument master, roll schedule and additive adjustment
records are checked independently; old releases are preserved.

## Outcomes and frozen estimators

Only signal times in New York 2018–2020 are scored, with path completion no later
than `2021-01-01T00:00:00-05:00`. Earlier bars are causal warmup only. All signals
and state updates are saved before path exclusions. Horizons are 5, 10, 15, 20,
30, 50 and 100 scheduled signal slots, plus 12 for 5m. H15 is primary.
The signal candle is excluded; reference is its unadjusted close. MFE/MAE use
the following highs/lows, clamp to zero, and reverse for Sell. Terminal delta is
direction × (terminal close − reference). Missing/partial/invalid slots, rolls
and the endpoint censor the affected horizon; shorter valid horizons survive.
Overlapping paths and opposite signals never alter acceptance/state.

Terminal sign is strict: positive/favorable, zero/neutral, negative/adverse.
Source-parity MFE-above-MAE uses `mfe-mae > 1e-10*max(1,mfe,mae)`; ties do not
count. Zero excursions have no attainment time; ties use the first candle.
Undefined observations and estimates are null, never zero. Raw points are
reported separately by product; positive entry ATR provides normalization.

Quantiles use linear interpolation at rank `p*(n-1)`, including exact deciles
P0–P100. Event-weighted means and contributing-session-balanced means are saved.
Calendar year/week/month and hour use signal-open New York time; weeks begin
Monday, months on the first. Session strata are fixed clock bins, defined in
config.json, and are descriptive. Zero-event periods with auditable coverage
remain visible; unknown coverage does not establish zero opportunities.

Paired circular contiguous calendar-week moving-block bootstrap uses the full
development-week roster (Monday 2018-01-01 through Monday 2020-12-28; 157 weeks),
common sampled blocks across cells, 10,000 replicates,
seed 20261010, four-week primary blocks and one/eight-week sensitivity. Event
weights use the signal-open calendar week. Complete contributing-session means
are assigned intact to the week of their New York trading date; a session is not
split between its Sunday evening and Monday morning fragments. Intervals
are descriptive pointwise 95% percentile intervals. Undefined draws are counted.
Support below 100 completed events or 30 sessions receives a sparse flag.
No Stage 1 search, selected-hour recommendation or trading-profit estimate is
performed. Matched active-minute comparisons are 3m H20 versus 5m H12 (60), and
3m H50 versus 5m H30 (150), alongside common-H and uninterrupted-path views.

## Prespecified examples and reporting

Before full scoring, independently reconcile the fixed June 4–15, 2018 signal
slice in all six cells, using prior causal state and only development paths.
The input prefix ends June 29, 2018; this is a verification sample rather than a
parameter/period selection. Save every sample outcome, including censoring.

For each cell, H15/All examples are the completed event nearest the median signed
terminal delta (typical), maximum MAE (high-adverse), maximum MFE (high-favorable),
earliest rejected technical candidate, and earliest H15 censored/partial path.
Ties use signal timestamp then stable event ID. Missing categories remain
explicitly unavailable; there are no favorable replacements. Illustrations use
saved signal/path bars only within authorized development dates.

Saved evidence supplies S1-T00 coverage/quality, T01 signal flow/exclusions, T02
horizon scorecard, T03 quantiles/deciles, T04 annual/session/time stability, T05
weekly/monthly summaries and T06 selections. Offline reports, advice, figures,
private Narada 1.1 source and selected downloads are prepared and reconciled
before sealing. Source identities are captured before historical scoring;
scientific receipts bind inputs, executed sources and outputs. Numerical testing,
scientific reconciliation, declared-byte integrity and publication schema validity
are separate gates. Failed diagnostic attempts remain staged and never count as
completed research runs. Later periods remain reserved for this study; prior
Abacus exposure prevents calling them pristine market holdouts.

## Calendar-roster implementation correction — 2026-10-10

Independent review found that the first scored diagnostic implementation included
the empty week beginning 2017-12-25, contrary to the frozen development-week
settings. That attempt is retained and will not be sealed. Before interpreting
its uncertainty or rendering findings, the roster is corrected to the 157 Monday
weeks intersecting 2018–2020. The new run captures corrected source bytes and
repeats numerical, historical and independent checks. No event/outcome rule,
width, horizon, estimator, seed or block length changes. This corrects the
implementation to the declared protocol; it does not select a result.
