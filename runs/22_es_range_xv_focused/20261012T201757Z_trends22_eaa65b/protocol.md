# Focused ES Range XV trend-length protocol

Study `22_es_range_xv_focused` · Authorized first analysis · Version 0.2.0 · 2026-10-12.

## Scope

The user authorized implementation, calculation and publication of the first
statistic: the number of consecutive directional candles in each trend for all
three ES 4-, 5- and 6-tick charts, with overall, annual, session and annual-by-session
results and a final tabbed Narada website on Vercel. Keep charts separate.

The research question is descriptive: how long are maximal consecutive bullish
or bearish candle runs in the retained exports? A directional candle uses the
exact Decimal sign of close minus open. This is a candle-colour trend definition,
not a swing/indicator trend, close-to-close momentum label or trading strategy.
The calculation uses no threshold optimization, predictive hypothesis, fills or
profitability estimate. All dates are descriptive; no holdout claim is made.

Pin [inputs.lock.json](inputs.lock.json). Input row counts remain inventory
metadata, not eligible sample sizes. Primary research excludes the entire partial
final session 2026-09-24 in every chart. Retain exclusion counts and terminal rows
in the input audit. No other dates are removed based on observed trend lengths.

## Trend definition and observation unit

A trend is a maximal uninterrupted run of consecutive completed non-doji candles
whose close-open signs agree. The observation unit is a trend, not a candle.
Bullish means close > open; bearish means close < open; exact equality is a doji.
Dojis terminate the current trend and do not belong to either direction.

Completed means status `next_bar_start_proxy` or `next_bar_start_same_second`.
Accept same-second bars in original source order, with no invented subsecond timing.
Status `unavailable_session_boundary` or `unavailable_export_end` is an
unconfirmed bar and creates a barrier. Never stitch around barriers or cross
inferred daily sessions. Retain repeated identical timestamp/OHLC rows and flag
counts only: second-resolution exports do not prove such rows are erroneous.
Validate OHLC ordering, finite exact prices, monotone opening timestamps and the
inferred session-date rollover before calculation; malformed inputs fail.

An observed completed opposite candle or doji establishes the prior run's end.
The first directional run of each valid segment has an unknown start unless a
completed doji/opposite predecessor is observed inside the segment. It is
left-censored. A run without an observed completed breaker is right-censored.
Save observed length, both censor flags and end reason for every run. Exact
length is null if either boundary is unknown. Report censored runs separately;
never count them as exact short runs or failed continuations.

Examples: an observed doji followed by bull,bull,bull,bear has an exact bullish
length of three; the bearish run is unresolved until its breaker is seen. A
segment starting bull,bull,bear has a left-censored bullish length observed as
two, not exact two. A same-direction run at a session's end is right-censored.

Assign each trend to the first candle's opening time and inferred session date.
Measure its full observed/exact length even when it crosses a named window
boundary. Thus session tables describe trends starting in that window, not
fragments cut to fit it. All-hours includes trends that start outside windows.

## Required reporting structure

For every metric and selected chart, retain these sections:

1. Overall, all observed hours.
2. Yearly, all observed hours.
3. All-years results for each of the seven named windows.
4. Yearly results for each of the same seven windows.

Use `session_date_proxy` year for annual assignment. An evening observation on
December 31 at or after 18:00 belongs to the following year's inferred session.
Retain source-row identity and order. Display actual covered dates and flags for
partial years; 2019 starts in November and 2026 ends in September. Label
all-years results as observed history, not a collection of complete calendar years.

The [settings](study.yaml) are the single machine-readable source of the windows:

| Group | ID | Label | Interval in New York time |
|---|---|---|---|
| Sessions | `asia` | Asia | [20:00, 02:00 next day) |
| Sessions | `london` | London | [02:00, 09:00) |
| Sessions | `ny` | NY | [09:30, 16:00) |
| Subwindows | `asia_open` | Asia Open | [19:30, 21:30) |
| Subwindows | `ny_open` | NY Open | [09:30, 10:30) |
| Subwindows | `ny_am` | NY AM | [10:30, 12:30) |
| Subwindows | `ny_pm` | NY PM | [12:30, 16:00) |

Use America/New_York wall time and its seasonal clock changes. Enhanced files
are already normalized using an inferred clock; do not apply another conversion.
The grouping helper accepts naive datetimes representing this normalized clock
and rejects timezone-aware timestamps to prevent accidental double conversion.
It uses the supplied session date unchanged; the future loader must validate
that date against the pinned input's documented 18:00 rollover.

Each window is a separate filter, including overlapping session/subwindow
membership. Asia Open is not a subset of Asia: its first half hour precedes Asia.
Unassigned hours, including [09:00, 09:30), stay in all-hours/yearly summaries.
Do not discard a row simply because it lacks a named window.

For base-bar descriptions, assign using opening time. A bar that crosses a
window boundary retains its opening-time group; do not split its OHLC. Future
signal/opportunity statistics must freeze their grouping anchor separately,
normally causal decision `available_at`, and must not use a later outcome time
to select their subgroup. Year assignment uses that observation's inferred
session date. Window membership does not truncate the future outcome horizon;
any horizon restriction must be an explicit metric-level rule.

## Denominators and evidence requirements

Each future table cell must record chart, metric ID, year or all-years marker,
window ID or all-hours marker, units, observation count, eligible denominator,
distinct sessions, exclusions and unknown/censored count. Probabilities also
retain numerator and denominator. Recompute each statistic from its own eligible
observations; do not average subgroup rates or yearly medians. Emit cells with
no observations explicitly, using zero counts and null estimates; undefined or
censored outcomes must not become false outcomes or zeros.

Report actual data coverage beside estimates. Missing timestamps/rows are not
proof of missing trades in event-driven bars. The partial final export session
and unavailable session-boundary/end completion proxies need explicit handling
per metric. Do not silently describe all bars as completed. Same-second bars
retain source order and unresolved subsecond timing. Do not infer volume or
exact durations from these exports.

The first analysis freezes the descriptive question, event/causal timing,
price/reference convention, horizons, exclusions, ambiguity, baseline, and
uncertainty method. Descriptive versus predictive claims, sample dependence,
prior inspection and any development/validation/reserved periods must be stated
for that question. This scaffold supplies no optimized thresholds, statistical
tests, costs, fills or profitability claim. Contract/roll and adjustment history
are not verified; a future execution/P&L study needs verified unadjusted prices.

## Implementation and validation

The [local helper](src/timeframes.py) generates memberships and overall/year/window
reporting keys. [run.py](run.py) executes, renders and seals explicitly selected
new stages; `describe` inspects declared settings without market-data execution.
Focused synthetic checks in [tests](tests/test_timeframes.py) must establish each
endpoint, overnight wrap, fractional seconds, overlap, unassigned hours,
same-second membership and December-to-January session-year assignment. Invalid
or ambiguous configuration is refused. These checks do not validate market
data, certify completeness or create research evidence.

Use the focused and documentation/metadata/index commands in [README.md](README.md).
The first analysis uses independent source reconstruction and saved-table
checks. Preserve
frozen settings, input hashes, exact commands, code/dirty snapshot, environment
lock, exclusions and saved artifact identities under the
[run lifecycle](../../runs/README.md). Keep completed records and imported inputs
unchanged.

## First analysis estimates and checks

For bullish, bearish and pooled-direction trend observations within each chart,
compute exact-run N, mean, median, mode (smallest tie plus all tied modes), q25,
q75, p90, p95 and maximum, alongside all-run and left/right/any-censored counts.
Quantiles use linear interpolation at (N-1)*q. Empty estimates are null.
Show exact-run frequency and ratios for lengths 1,2,3,4,5,6-7,8-9,10-14,15-19,20+,
and P(length >= 2,3,5,10,20). Every rate names its exact-run denominator.

These are empirical descriptions of the retained, censored sample. No iid
standard errors, predictive probabilities or population confidence intervals
are claimed. Censored and exact trends can differ, so exact-length summaries
are explicitly conditional on fully observed starts/ends. Include coverage,
eligible bars, distinct sessions, dojis, barriers and excluded bars by chart.

Focused synthetic tests must cover exact/censored sequences and grouping.
An independent verifier reconstructs every trend from the pinned OHLC inputs
without importing the engine, compares the full ordered ledger and recomputes
all saved summary, histogram and survival cells. Require conservation of all
eligible non-doji bars across observed trend lengths, no cross-session trends,
exact-versus-censor counts, annual-to-overall counts/length sums, histogram totals
and survival monotonicity. Verify selected web cells and CSV strings against the
saved tables before sealing. Build only from selected pre-seal publication
bundles; add generic chart tabs and keep older public artifacts unchanged.
