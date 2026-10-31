# Verniman Pivot Statistics — ES

Approved study roadmap · Study `30_verniman_pivot_statistics_es` · 2026-10-31

## Purpose and scope

Build a reproducible description of how ES behaves around Verniman's daily
pivot, with the indicators used to read that auction: Globex-anchored VWAP,
a five-minute EMA20/EMA50 cloud, and three-minute EMA6. Lead with the difference
between a price break that returns without a new EMA6 crossing and a break
accompanied or followed by an actual EMA6 crossing. An EMA already on the same
side is a separate state; alignment is not a crossing.

The intended coverage calendar is **2020-01-01 through 2026-10-30 inclusive**.
The approved execution uses only repository-retained pivots and market data;
the actual market-data endpoint is currently **2026-09-18**. Preserve later
requested dates as uncovered dates, not fabricated observations. External
acquisition is cancelled. Reuse existing OHLCV and feature infrastructure where
the exact requested semantics match. Use the
exact ES delivery contract quoted in the source plan, even when it differs
from a volume-lead contract. Use unadjusted same-contract prices throughout.
The primary sample requires one unambiguous single-price pivot. Preserve
zones, multiple competing pivots, missing prices/contracts, uncertain dates
and source conflicts in the audit rather than coercing them into a line.
Historical `available_at` is currently unverified; a nominal 09:25 plan time
does not establish that the retained source was available before the open.

The first research release measures market behavior. It does not simulate
entries, stops, fills, costs or net profitability. Later strategy work needs
its own approved protocol and evidence.

## Inputs and reusable features

Bhishma owns requested data and causal features; Sahadeva owns pivot selection,
events, forward outcomes, statistics and interpretation. Pin every delivered
manifest and selected artifact hash. Preserve older releases and source captures.

- Base: one-minute ES OHLCV for each required delivery contract, including the
  earlier history needed for EMA warmup, the preceding 18:00 anchor, and the
  actual retained endpoint. Audit existing coverage and exclude unavailable
  contracts/dates explicitly; do not purchase or download an extension.
- VWAP: accumulate one-minute `HLC3 * volume` divided by cumulative volume,
  resetting at **18:00 America/New_York** for each Globex session. This is a
  one-minute bar-price approximation, not trade-price VWAP. Do not substitute
  a VWAP calculated from three- or five-minute HLC3.
- EMA cloud: EMA20 and EMA50 on completed fixed-clock five-minute closes,
  through the full electronic session. Keep both lines, their ordering,
  absolute width, and 15-minute changes.
- EMA6: completed fixed-clock three-minute closes, through the full electronic
  session. Require an actual change of its strict side relative to the pivot
  to identify a line crossing.
- EMAs are recursive close-based `adjust=False`, seeded with the first valid
  same-contract close, with at least **250 preceding valid bars of each
  timeframe**. Do not reset at RTH, calendar years or study boundaries, and
  do not splice another contract's absolute prices into the history.
- Features carry bar-open, bar-close and `available_at`; an as-of join may use
  only a completed value available by the observation time. Missing minutes,
  uncertain calendars and inadequate warmup remain explicit quality states.

## Observation and statistics design

Use New York local time with daylight-saving-aware conversion. Observe the
09:25 pre-open snapshot and the 09:30 opening snapshot separately. The opening
price is the actual 09:30 open. At either snapshot, use only indicator values
whose completed bars are available then.

RTH is 09:30–16:00. Its three sections are **Opening range 09:30–10:30**,
**New York AM 10:30–12:30**, and **New York PM 12:30–16:00**. Three-minute
bar-open membership assigns events to sections; the event becomes known at
bar close. A 10:30 close of a 10:27 bar belongs to Opening range. No fourth
section is included.

Retain linked daily, section and event ledgers. Record all raw strict
three-minute close side changes, EMA6 line crossings, touches, price episodes,
confirmation timing and later returns through the pivot. Equality preserves
the last strict side; touching the pivot alone is not a cross. Seed the RTH
state at 09:30 and do not count the opening state as a crossing. Raw recurring
crosses remain measurable without a fitted buffer or cooldown.

For each price event, distinguish EMA6 crossing at the same close, already
aligned EMA6, opposite EMA6 and unavailable EMA6. A later crossing is recorded
only while that price episode remains active. A return before confirmation is
known only when it occurs; a day-end unfinished episode is censored. Outcomes
after later EMA confirmation begin at that confirmation time.

The statistics catalog in [statistics.md](statistics.md) covers:

1. Opening location, pivot distance, cloud direction/width/slopes, EMA6 side,
   prior same-contract RTH-close opening gap, and the ordering of price, pivot,
   cloud and Globex VWAP; distances in points and basis points.
2. Daily and section touch/cross frequency, first/last event times, time on each
   sampled close side, recrosses, longest strict same-side close run,
   episode depth/duration, and price/EMA disagreement.
3. Price-only breaks, same-close EMA crossings, delayed EMA crossings, shallow
   returned breaks and censored episodes, retaining their different information
   times and denominators.
4. Signed displacement, favorable/adverse excursion and **5/10/20 ES-point**
   reach at **15/30/60 minutes**, with **30 minutes primary**, plus section-end
   and 16:00 outcomes. A fixed horizon extending past RTH is unavailable, not
   silently shortened or continued overnight.
5. Pivot retests following actual EMA6 crossings, including the first retest
   within 30 minutes and subsequent holding/failure behavior.
6. Cloud and VWAP context, section-to-section transitions, daily closing
   location and stability across years, calendar months and month of year.

Report all-cross recurrence alongside first-event-per-day and
first-event-per-section outcome panels. Preserve no-event days in daily
denominators. Do not treat multiple events on one day as independent sessions.
Keep observed zero, false, undefined and censored outcomes distinct.

Save whole-sample, year and calendar-year/month summaries, plus trailing
20/60/120 eligible observed-session windows anchored to the 2026-10-30 cutoff.
Show actual latest usable dates and observed window bounds. Curated filters
select saved cohort rows.
Display numerator, eligible denominator, distinct day count, exclusions,
units and outcome horizon with each statistic. Flag cells with fewer than
30 distinct days. Main uncertainty uses **2,000 moving-block bootstrap
replicates of five chronologically ordered observed sessions**, seed
**20261031**, retaining complete within-day records. Broad conditional
exploration does not establish a confirmed edge or justify choosing only
favorable variants.

## Phases and completion gates

| Phase | Work and deliverable | Gate before the next phase |
|---|---|---|
| **1 — Protocol and source audit** | Register this study; preserve the agreed roadmap and measurement definitions; inventory source plans, exact contracts, pivots, availability, dates and coverage; inventory current feature coverage. Preserve the earlier acquisition request as cancelled historical planning. | Review source dispositions and unresolved semantics; no automatic eligible label when required semantics are blank. |
| **2 — Retained data and features** | Reuse repository-retained same-contract OHLCV and compatible feature builders; derive only missing requested indicator values through Bhishma. No external acquisition. | Retained coverage, warmup, as-of availability, source reconciliation and independent feature checks pass; missing dates/contracts remain excluded. |
| **3 — Evidence engine** | Freeze an executable protocol/settings/input/environment snapshot before outcomes; implement daily/section/event ledgers and outcome calculations with synthetic and independent checks. | Event timing, equality, same-close ordering, censoring and numerical reconciliation pass; preserve exclusions and incomplete stages. |
| **4 — Statistics and interpretation** | Generate saved baseline and curated conditional statistics, distributions, calendar/recent panels and uncertainty; document negative and inconclusive patterns. | Every reported number traces to saved evidence; support and retrospective limits remain visible; no profitability claim. |
| **5 — Narada presentation** | Prepare selected report bundles and figures before sealing; provide curated saved filters, phase/analysis navigation and summary downloads; inspect desktop/mobile behavior. | Source-cell checks and app verify/test/lint/build/browser gates pass; publish/deploy only within separately authorized scope. |
| **6 — Subsequent strategy studies** | Specify and test selected actionable hypotheses with entry/exit timing, fills, costs and chronological validation. | New explicit approval and a new decision-complete strategy protocol; descriptive results alone are insufficient. |

The user subsequently authorized the full descriptive workflow through saved
statistics and local Narada presentation using repository-available data only.
Proceed sequentially through Phases 2–5 with their checks, preserving the Phase 1
audit. No additional permission is needed for those steps. External acquisition,
hosted deployment and Phase 6 strategy execution remain outside this instruction.

## Evidence and preservation

Stage new audit/evidence output under `work/30_verniman_pivot_statistics_es/`.
Freeze code/settings/input/environment identities and exact commands for each
future execution, and seal verified completed evidence only under a unique
`runs/30_verniman_pivot_statistics_es/<run-id>/`. Do not overwrite prior releases,
captures or runs. Narada consumes explicitly selected saved reports, never
research modules or arbitrary workspace ledgers. Later presentation-only changes
use a separate revision and publication identity.
