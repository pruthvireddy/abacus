# Calculation and terminology specification

Study `29_verniman_level_reconstruction` · Phase 1 · Protocol 1.0.0

The [Pine derivative](indicator/verniman_levels.pine) is **Verniman Levels**.
This document separates source language from our engineering choices. The
[plan](plan.md), [settings](study.yaml) and [source lock](inputs.lock.json)
define scope; [verification](verification.md) records what was actually checked.

## What the supplied script calculates

The [unchanged baseline](reference/vp_levels_original.pine) declares `VP Levels`.
Its actual families are:

| Baseline family | Actual calculation and limitation |
|---|---|
| PDH / PDL | Prior full 18:00–17:00 futures-session high/low, detected using an in/out transition; these are not RTH extremes |
| Current week | Developing weekly approximate VAH/POC/VAL, reset by `time("W")`; every available chart bar enters the profile |
| Previous week | The weekly profile copied at the next detected week boundary |
| Previous RTH | A 09:30–16:00 profile with a display switch between current and stored previous values; a separate accumulator duplicates the developing calculation |
| Developing RTH | A separately configurable 09:30–16:00 approximate VAH/POC/VAL profile, displayed until the anchor resets |
| Overnight | A developing 18:00–09:30 approximate VAH/POC/VAL profile, retained after the window |

It finds one POC and expands a single contiguous value area. It does not segment
multiple HVNs/LVNs, detect their edges, compute PBTs, select an LIS, or order
targets. The baseline's `init()` clears bins and total volume but leaves level
fields populated; zero-volume periods can therefore display stale levels.
Simple in/out transitions also miss rollovers when the feed omits break bars or
the chart shows only RTH. Initial partial profiles are not qualified.

## Retained profile arithmetic

Let row size be `syminfo.mintick × row_ticks`. The provisional defaults are
16 ticks and a 70% value area, inherited from the supplied baseline.

For each eligible confirmed bar, the low/high keys are `floor(low / row_size)`
and `floor(high / row_size)`. Allocate its volume equally across every integer
key in that inclusive range. A high exactly on a bin boundary touches that
boundary's bin. Grow the histogram while retaining prior key coordinates.

POC is the key with the largest allocated volume; ties choose the lowest-price
key. Starting there, add the more populated immediately adjacent bin until
cumulative allocated volume meets the selected percentage. An equal-volume
adjacent tie expands upward first. VAH/POC/VAL are key × row size, preserving
the baseline's bin-base coordinate convention rather than silently moving to
bin centers or outer edges.

This is a **chart-bar volume allocation approximation**. It is not exact observed
volume at price, lower-timeframe reconstruction, order-flow classification or
Vern's recovered calculation. Changing the timeframe changes bar ranges and the
allocated distribution; changing row size changes binning, ties and levels.
Chart-feed corrections and continuous-contract adjustments can also change
historical results. Record those settings before comparison.

An empty/zero-total-volume profile has undefined VAH/POC/VAL. Invalid or missing
volume and a 6,000-bin profile overflow make the affected profile unavailable;
they must not reuse its old levels. Price extrema and a closing reference have
their own coverage meaning and do not become volume-profile validation.

## Session and availability contract

All session arithmetic uses `America/New_York` civil timestamps, including
daylight-saving changes. Chart display timezone does not redefine the sessions.
Trading date is the following civil date for bars at/after 18:00, and the current
civil date for daytime bars. Sunday 18:00 belongs to Monday's trading date.
The futures week begins Sunday 18:00 New York and ends Friday 17:00.

| Family | Reference period | Availability |
|---|---|---|
| Previous full-session high/low | Prior completed 18:00–17:00 futures session | After its last confirmed bar closes; distinct from RTH |
| Current-week VAH/POC/VAL | Current futures week through included confirmed bars | Developing; requires the supported start and coverage |
| Previous-week VAH/POC/VAL | Prior week relative to the current Sunday-18:00 futures-week identity | Rolls at the next Sunday 18:00 boundary; a partial or nonadjacent prior week is unavailable |
| Completed-RTH VAH/POC/VAL | Latest completed 09:30–16:00 RTH | Available at completion and retained separately from current RTH; YVAH/YPOC/YVAL are pre-open aliases |
| Developing-RTH VAH/POC/VAL | Current trading date's 09:30–16:00 RTH | Only from confirmed RTH bars; separate from the frozen pre-open map |
| Overnight VAH/POC/VAL; ONH/ONL | Current trading date's 18:00–09:30 overnight window | Developing before 09:30; snapshot includes only the prefix through cutoff |
| Completed-RTH high/low | Latest completed 09:30–16:00 RTH | Available after completion, separately from full-session extremes |
| Prior RTH last-traded close | Close of the last retained bar ending at 16:00 | Available only with the required RTH coverage; not official settlement |

Explicit period identities replace dependence on seeing an out-of-session bar.
The maintenance break and weekend do not need fabricated bars. Missing required
bars, unsupported session configurations and incomplete initial history receive
an unavailable/readiness status. Complete weekly history requires more warm-up
than a single daily profile. This fixed-clock baseline does not claim an
exchange holiday/early-close calendar; incomplete shortened periods are
unavailable rather than silently treated as full sessions.

All out-of-full-session bars are ignored by the state updates. Within a week,
only an exact 17:00–18:00 scheduled maintenance gap is allowed. At a new trading
date, full-session and RTH sources must be the expected preceding weekday
(Friday for Monday); an entirely absent weekday invalidates older references.
No exchange-holiday substitution is inferred. Weekly references must likewise
come from the adjacent prior week. Friday 17:00 completes the current profile;
it remains current week until the next Sunday-18:00 week identity begins.

An overnight reference requires its last included bar to end exactly at the
requested through-time: the current confirmed close before RTH, or 09:30 after
RTH begins. A missing terminal overnight bar therefore withholds the profile
and ONH/ONL, even if earlier overnight bars were continuous. The pre-open saved
map independently keeps the prefix that was ready at its cutoff.

Initial support is standard 1-minute or 5-minute ES, MES, NQ or MNQ futures charts
with full electronic-session coverage. RTH-only charts can identify separate
RTH periods but cannot provide a complete overnight/full-session/weekly map;
the relevant families remain unavailable. Synthetic-price and non-time-based
charts, other timeframes and other instruments/session conventions require a
separate suitability decision. The indicator cannot establish that a retained
feed is the correct contract or that continuous prices are unadjusted; inspect
those settings in TradingView.

## Snapshot boundary and presentation

Default cutoff is **09:25 New York**, before RTH. Only completed, confirmed bars
with `time_close <= cutoff` may enter. On a 5-minute chart the default last
included bar is 09:20–09:25; on a 1-minute chart it is 09:24–09:25. The snapshot
records that bar and the source period identities. An unfinished or straddling
bar cannot contribute its later high, low, close or volume. The cutoff must
align with the supported bar grid; a missing exact boundary is a clear status.

Copy the candidate map once per futures trading date. Later replay steps may
change developing profiles but cannot mutate the saved candidate prices or
their recorded source identities. A reload recomputes the saved map from the
same preceding bars and settings; reproducibility still depends on equal retained
history and unchanged feed bytes. The next trading date starts a new snapshot.

The saved map has 19 fields: two full-session extremes, three current-week,
three previous-week and three completed-RTH profile values, three overnight
profile values, ONH/ONL and three completed-RTH price references. An optional
separate live candidate map defaults off. Three developing-RTH profile values
remain separate and default on.

The developing RTH display also requires coverage through the earlier of the
last processed close and 16:00. A missing terminal RTH bar therefore hides its
developing levels after the window instead of extending a partial profile.
The status reports effective ON/RTH coverage, the live processing timestamp,
and the trading date of the live latest completed RTH reference.

The status table is compact by default. **Expand table with all candidate
values** defaults off and reveals the 19 saved/live comparisons for verification.

Frozen labels carry a snapshot qualifier and developing labels retain their
period qualifiers. Family toggles control readable presentation. Lines use
timestamps; a historical drawing start never means that the final value was
known then. The saved map is available at its cutoff, not at the prior 18:00
session start. The pre-open map includes no actual opening gap: today's RTH
opening price is unavailable before 09:30.

## Source vocabulary and extension boundaries

The allowed generic sources are Study 27's
[levels](../../runs/27_verniman_method_knowledge/20261023T174000Z_review27/knowledge-base/levels.md),
[glossary](../../runs/27_verniman_method_knowledge/20261023T174000Z_review27/knowledge-base/glossary.md),
[method model](../../runs/27_verniman_method_knowledge/20261023T174000Z_review27/knowledge-base/method-model.md)
and [unknowns](../../runs/27_verniman_method_knowledge/20261023T174000Z_review27/knowledge-base/unknowns-and-tensions.md).
They distinguish Vern's explicit definitions, curated teaching and Abacus synthesis.

| Term | Source meaning | Phase 1 treatment |
|---|---|---|
| HVE | High Volume Edge | Exact detector not recovered; not implemented |
| HVN / LVN | High / Low Volume Node | Segmentation not recovered; not implemented |
| PBT | Projected Balance Target | Formula/anchors not recovered; not implemented |
| LIS | Line in the Sand | Scenario divider selection not recovered; not implemented |
| YVAH / YPOC / YVAL | Yesterday's value area high / POC / value area low | Pre-open aliases for latest completed RTH, with source trading date; live labels retain Completed RTH because today's completed profile becomes latest at 16:00 |
| ONH / ONL | Overnight high / low | Explicit 18:00–09:30 window, prefix through cutoff in snapshot |

Weekly and developing qualifiers are descriptive implementation labels, not
invented Vern shorthand. Future HVN/LVN segmentation, HVE candidates, composite
balance, PBT anchors, LIS/pivot selection and ordered bullish/bearish targets
are extension modules only. No result from this phase validates their rules.
