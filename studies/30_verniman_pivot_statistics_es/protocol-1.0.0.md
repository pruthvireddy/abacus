# Protocol 1.0.0 — Verniman Pivot Statistics — ES

Study `30_verniman_pivot_statistics_es` · approved definitions: 2026-10-31

The original Phase 1 scope was source and coverage audit only. Subsequent user
steering authorizes the full descriptive workflow through saved statistics and
local Narada presentation, using repository-retained data and pivots only.
External acquisition is cancelled. The requested coverage calendar still ends
2026-10-30; retained market data currently ends 2026-09-18. This document is not
itself an execution receipt. Before Phase 3, retain actual executable source,
settings, input pins, environment lock and commands in a new pre-execution
record. Do not use market outcomes to decide source eligibility.

## 1. Population, sources and audit

Requested session dates are 2020-01-01–2026-10-30 inclusive, ES only, in
America/New_York. The primary numerical sample will require an unambiguous
single-price pivot, resolved source date and interpretation, exact quoted ES
delivery contract, complete required same-contract data and ready features.
Do not replace a quoted non-volume-lead contract with a continuous series.
Use unadjusted OHLCV and preserve tick size and source lineage.

Inventory every calendar date, every retained canonical outlook and separate
observations; preserve duplicates and missing days. Multiple source revisions
on one date require an explicit source-only selection decision before research.
Selection must cite retained evidence, not subsequent market behavior. Keep
unpriced pivots, zones, separate bullish/bearish thresholds, one-sided triggers,
unknown roles, conflicts and ambiguous dates/contracts out of an automatically
eligible single-line sample.

Phase 1 produces logical tables for canonical-outlook audit, calendar audit,
observation audit, observation-level audit and summary. The source auditor's
`source_shape` distinguishes `single_shared_trigger`, `shared_zone`,
`separate_thresholds`, `one_sided`, `no_trigger`, `invalid_trigger_data`,
`unsupported_trigger_side` and `multiple_triggers_per_side`.
`source_only_disposition` is `undated`, `outside_requested_range`,
`review_required` or `candidate_pending_data`. A candidate is not a delivered
eligible research day. Blank legacy `trigger_interpretation` requires
`pivot_semantics_unreviewed`; multiple canonical outlooks on a date remain
flagged for review. Preserve the original contract string alongside any
normalized delivery symbol and the evidence supporting its interpretation.

User recollections, supplied images and image role legends remain separate
observations, with disposition `separate_observation_not_canonical_plan`.
They do not silently fill canonical plan gaps. Do not estimate an unprinted
price from chart geometry or infer a delivery contract by matching prices.

Nominal pivot observation is 09:25. Source date, source publication/update
claims, capture time and verified historical availability are distinct fields.
Retain historical `available_at: null`; Phase 1 does not certify pre-open
availability. The audit's `point_in_time_eligible` remains false, including
when a claimed timestamp is nonnull but not independently verified. Future
retrospective descriptive eligibility and prospective eligibility must be
separate cohorts. Retrospective day-quality selection must be disclosed.

Inventory pinned source identities and actual market-data/feature coverage.
The requested calendar and exact-contract policy leave unavailable dates and
contracts. Preserve the earlier external-data request as cancelled planning;
use only retained data, and do not imply complete requested-calendar coverage.
Reuse prebuilt OHLCV where its contract, clock and quality semantics match.

## 2. Future feature contract

Derive independent one-, three- and five-minute bars from the pinned exact
delivery contract, on fixed New York clock boundaries. Preserve open/close
timestamps, complete-minute counts and `available_at`. Do not fill missing
minutes, synthesize OHLCV, average contracts or bridge a missing bar by treating
it as observed. Calendar uncertainty is an explicit unusable quality state.

**Globex VWAP:** reset at the preceding 18:00 New York session anchor. At each
completed one-minute bar accumulate `(high + low + close) / 3 * volume`, divided
by cumulative volume. Zero cumulative volume is undefined. Use this same
one-minute cumulative series at later as-of snapshots; three-/five-minute HLC3
aggregation is not equivalent and must not be substituted. This is bar-price
VWAP, not exact trade-price VWAP.

**EMAs:** EMA6 on completed three-minute closes; EMA20 and EMA50 on completed
five-minute closes. For period N, alpha is `2 / (N + 1)` and
`EMA[t] = alpha * close[t] + (1 - alpha) * EMA[t-1]`, seeded with the first valid
same-contract close. Use the full electronic session and require at least 250
preceding valid bars of the corresponding timeframe before evaluation.
Carry history through RTH, day/year and study boundaries. Do not reset at 09:30
or import another delivery contract's price history. Missing input and warmup
readiness remain explicit; a bar gap must not become a fabricated comparison.

Cloud lower/upper are `min(EMA20, EMA50)` / `max(EMA20, EMA50)`; signed spread
is EMA20 minus EMA50; width is its absolute value. Bullish/bearish/flat ordering
means positive/negative/zero spread, without a fitted tolerance. A line's
15-minute change is its completed value minus the value exactly 15 minutes
earlier in the same contract series; unavailable endpoints yield unknown.
Store EMA20, EMA50, EMA6 and VWAP changes separately. Width is measured in ES
points; its 15-minute change is current width minus width 15 minutes earlier.
Context basis points are 10000 times the signed distance divided by pivot;
outcome basis points use their own event reference close. Missing/nonpositive
denominators remain undefined. Opening gap uses actual 09:30 open minus the
preceding applicable RTH close of the same delivery contract, never another
contract's close.

The full-day primary quality gate requires complete expected one-minute data
from the 18:00 anchor through 16:00, a known applicable calendar and full RTH,
plus the required preceding feature history. Shortened/partial sessions remain
in coverage with reasons and are not silently treated as full 09:30–16:00 days.
Metric-specific unknowns remain unknown even where another metric is available.

## 3. Observation times and sections

Keep 09:25 and 09:30 snapshots distinct. The 09:25 price snapshot is the last
completed one-minute close available then. The 09:30 price seed is the actual
09:30 minute open. Indicators use their latest completed value available at or
before the snapshot. For example, a 09:25 EMA6 snapshot normally uses the
09:24 close, while its five-minute cloud can use the 09:25 close. At 09:30,
both native intervals have completed values; no 09:30–09:33 or 09:30–09:35
future bar may enter the opening snapshot.

Retain complete raw feature snapshots at each actual price/EMA crossing and
confirmation, with raw price/indicator values, source observation times and
stable snapshot IDs linked from the event/outcome records. These event
snapshots do not enter scheduled snapshot distributions: those remain the five
labels 09:25, 09:30 and the three section endpoints. This preserves one scheduled
observation per day/label and avoids overweighting days with repeated crosses.

| Section ID | New York three-minute bar-open interval |
|---|---|
| `opening_range` | [09:30, 10:30) |
| `new_york_am` | [10:30, 12:30) |
| `new_york_pm` | [12:30, 16:00) |

Events are observed at completed three-minute close; membership follows the
event bar's open. Thus the 10:27–10:30 event belongs to Opening range and a
12:27–12:30 event to New York AM. The last RTH event bar opens 15:57 and closes
16:00. Retain the actual event timestamp and assigned section separately.
Opening range is a named analysis window, not an entry rule.

## 4. Price and EMA crossing state

For pivot P define strict side of a value x as above if x>P, below if x<P,
equal if x=P. Use exact comparisons with no buffer, rounding-to-tick test or
fitted epsilon. Equality alone is not a cross; it retains the last observed
strict side. With no established strict side, the first strict observation
initializes the state. Seed price from the actual 09:30 open and EMA6 from
the completed EMA6 available at 09:30. Neither seed is an opening crossing.

At each later completed three-minute bar, a price cross occurs when close
enters the opposite strict side from its last strict side; an EMA cross uses
the same rule applied to EMA6. Do not infer an intrabar EMA crossing from a
wick. Preserve equal observations explicitly. Comparisons spanning missing or
unusable observations are unknown, not crossings; re-establish a known state
before counting subsequent transitions. No event rearm buffer or cooldown is
applied to raw recurrence counts.

A price episode begins at a price-cross close and ends at the first reverse
price-cross close or 16:00. The confirmation interval includes its start and
excludes its reverse-price endpoint. At a shared timestamp, close the old
episode first, start the new episode, and attach any same-direction EMA cross
to the new episode. Record direction, source bar and observed time for both
events; simultaneous crossings have zero confirmation lag.

At the price event, store EMA6 state as **same-close actual crossing**,
**already aligned without a same-close crossing**, **opposite**, **equal with
remembered side**, or **unavailable/uninitialized**, preserving raw equality
and remembered-side fields. A later same-direction actual EMA6 cross confirms
only while the price episode is active. Already-aligned state is never relabeled
as a crossing. Record the first valid delayed confirmation and its lag.

An episode returning through the pivot before a new EMA6 crossing receives a
returned-without-new-cross label only at its return time. Preserve whether EMA6
was already aligned; do not equate that case with an EMA-opposite shallow break.
An episode without a reverse cross by 16:00 is right-censored for return time,
even if its closing displacement is observed. Day end without EMA confirmation
does not prove a shallow failed break. Raw episode penetration and duration are
descriptive future measurements, not signal-time features.

## 5. Outcomes and retests

Measure signed displacement from the completed event close in the event
direction. Use 15/30/60 minutes, with 30 minutes primary, and section-end/16:00
endpoints. Fixed horizons require the complete interval within RTH; do not
truncate, carry overnight or drop the unavailable observation without a count.
Record elapsed minutes for endpoint outcomes. A section/day endpoint coinciding
with the event has no followthrough interval and is not applicable for a
followthrough estimate. Closing location remains separately observable.

Forward favorable/adverse excursion and 5/10/20-point reach use one-minute bars
whose opens are at or after the event-observed time and before the endpoint.
Exclude the signal bar's earlier high/low. Reach means the relevant extreme
touches or exceeds the threshold. Save favorable and adverse reach separately;
do not infer which came first inside a one-minute bar. These are path outcomes,
not assumed executable fills. Returns after delayed EMA confirmation start at
that confirmation close and carry their own information time and eligibility.

For each actual EMA6 pivot crossing, seek the first **subsequent** completed
three-minute bar with `low <= P <= high`, bar open at or after the event's
observed time, and completion at or before `min(event + 30 minutes, 16:00)`.
Exclude the signal bar. This is the first pivot retest. Record its close as
`hold` on the crossing side, `failed` on the opposite side or `equal` at pivot.
Touch time is resolved only to the three-minute bar; infer no intrabar ordering.
No retest in a fully observed 30-minute window is false. A shortened or missing
window is censored/unknown, with the observed duration retained.

## 6. Cohorts, inference and future evidence

Report raw all-cross recurrence, first-event-per-day and first-event-per-section
outcome panels; none may be substituted for another without its denominator.
Keep direction and section panels as well as signed-direction pooled displays.
Retain no-cross days in daily counts. Sampled close occupancy is the count/share
of completed three-minute closes above/below/equal to pivot; it is not an exact
intrabar time measurement.
Longest same-side run counts consecutive strict three-minute closing sides;
equality, opposite side or unknown breaks a run. Section transition tables
retain source/target states and support for price-side and cloud ordering.

Compare time-zero known EMA/cloud/VWAP states separately from eventual episode
labels. A price break's later confirmation or return cannot be used as if known
at its beginning. Confirmation-start outcome panels are descriptive conditional
samples; a later strategy claim requires a matching decision-time baseline,
including survival to that landmark, and a separate strategy protocol.

Save overall, year, calendar-year/month and trailing **20/60/120 eligible
observed-session** summaries, all anchored to the 2026-10-30 requested cutoff.
Show actual latest usable date and observed start/end, especially if usable
coverage ends earlier. Sparse means fewer than 30 distinct days. Every rate
shows successes, valid denominator and distinct days, with unknown/censored
counts. No-sample is not zero and a zero denominator yields null.

Use 2,000 five-observed-session moving-block bootstrap replicates, seed
20261031, resampling complete chronological day records with all events and
labels retained. Select conditions after resampling whole days. Descriptive
95% intervals do not correct the broad exploratory family or establish a
profitable edge. Preserve negative and inconclusive results. No trading-cost,
fill or P&L claim is authorized by this protocol.

Before a numerical run, require tests of hand-recursion and source aggregation,
prefix/as-of invariance, equality/seeds, same-close ordering, missing intervals,
section boundaries, retests, horizon censoring, null/false/zero and aggregation
denominators. Independently reconstruct events and selected statistics from
saved evidence. Future presentation uses saved tables only; source-cell maps
and selected assets must be prepared before sealing any intended publication.
