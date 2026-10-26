# Anchored VWAP excursion and return research plan

Prepared 2026-09-29 for a fresh local study in Abacus. This document specifies
what the coding agent should implement; it contains no new statistical findings.
The three questions are how price behaves after closing outside a VWAP band,
how often it subsequently touches VWAP, and how it behaves after the first touch.

Existing studies 05, 06 and 11, their statistics, indicators and sealed runs must
remain unchanged. Reuse the immutable market-data release and its documented
semantics, but create fresh events, outcomes, summaries and reports. Do not reuse
old probabilities or choose definitions to reproduce earlier results.

## Scope and proposed decisions

| Item | Proposed specification |
| --- | --- |
| Products | ES, NQ, GC; separate primary estimates |
| Signal candles | Completed two-minute candles |
| Future path | Matching unadjusted one-minute OHLC, covering exactly the requested number of two-minute candles |
| Bands | 2, 2.5 and 3 sigma for module 1; 2 sigma primary and 2.5/3 sigma secondary for modules 2 and 3 |
| Horizons | 5, 10, 20, 50 candles primary; 15 candles supplementary because it was also mentioned |
| Elapsed time | Respectively 10, 20, 40, 100 minutes; the supplementary 15 candles equals 30 minutes |
| Sides | Upper and lower departures separately; directional summaries additionally combine mirrored sides |
| Delta | Working interpretation: signed price change. Actual buy-minus-sell volume delta is a separate, currently unsupported metric |
| Entry reference | First subsequent two-minute candle open, after a completed signal or completed touch candle |
| Main session rule | Both signal and the complete measurement horizon stay inside the named session |
| Early anchor data | Include valid early signals; do not silently import study 11's 30-minute warm-up |
| Statistical status | Exploratory historical price-path research; no untouched holdout or profitability claim |

The delta meaning and preferred interpretation of bounce were asked during
planning. If no clarification is supplied, implement price delta and both
directional responses as specified here. Record these as working assumptions,
not user-confirmed preferences. Other choices above are explicit proposed
defaults, to be frozen before outcomes are inspected.

## Four separate session populations

Use `America/New_York` with daylight saving handled by the timezone library.
Store timestamps in UTC and display New York wall time in reports. Use the
published session date, not a UTC calendar date.

| Report | VWAP anchor | Signal and primary observation window |
| --- | --- | --- |
| Asia | 20:00 on the preceding evening | 20:00–03:00 |
| London | 03:00 | 03:00–09:00 |
| New York | 09:30 | 09:30–16:00 |
| Globex | 18:00 on the preceding evening | 18:00–17:00 |

Windows include their opening instant and exclude their ending instant; a
horizon whose final candle closes exactly at the window end is complete.
The signal candle must belong wholly to its window, and its next candle must
open before the window ends. No local-session signal is reassigned across the
09:00–09:30 or 16:00–20:00 gaps. Globex is its own analysis using its own VWAP,
not the sum of the three local sessions. These populations overlap and are not
independent replications.

Published local VWAPs continue accumulating until the Globex close. Restrict
their use to their named membership windows for the main results. Do not
silently follow an Asia setup into London. Exclude incomplete horizons per
horizon and show the counts: an event can support 5 candles but not 50.
Also produce a common-cohort comparison restricted to events supporting all
50 candles, so changes across horizons can be separated from sample changes.
For example, an Asia signal at 02:40 can support 5 and 10 candles but not 20
or 50; it must not become a 50-candle failure or be carried into London.

## Data and price conventions

Use the pinned `session_anchored_vwap` version `1.0.0`, its two-minute dataset,
and matching `volume_lead_unadjusted_v1` one-minute source. The input lock pins
catalog identities, including the upstream adjusted-series manifest, indicator
definition, schema, calendar and eligibility audit. The coding agent must verify
every consumed physical partition against its manifest before calculation.

The feature release contains output-bar HLC3 VWAP and volume-weighted population
sigma. It is not trade-by-trade VWAP. Calculate the study-local 2.5-sigma band as
`VWAP +/- 2.5 * sigma`; do not request a rebuilt release just to add this threshold.
Use strict close inequalities for all band departures. Signal bands evolve
through the completed signal candle and are available only at `available_at`.

Signals may be detected in the published adjusted coordinates. Translate every
price reference into the matching unadjusted contract coordinates before path
measurement: feature OHLC and `price_adjustment` use fixed-point `1e-9` scaling;
VWAP and sigma are already price-point floats. Subtract
`price_adjustment * 1e-9` from VWAP/band levels; sigma is translation invariant.
Use the schema to verify units rather than applying one conversion to all fields.
Require product, session date, timestamp, raw symbol, instrument and adjustment
continuity. Do not measure an excursion across a roll or splice contracts.

The published feature sample ends on 2026-09-18. It has 1,037 eligible ES days
and 1,177 NQ days from the 2021-06-28 session onward, and 825 eligible GC days
from the 2016-02-11 session onward. These are sparse retrospectively complete
days, not an uninterrupted history. Report coverage and excluded days by year.
Although the underlying one-minute series starts earlier, do not present it as
earlier VWAP coverage or silently regenerate a longer feature history.

The verified schemas contain OHLCV, not aggressor buy/sell volume. Therefore
price delta is computable, but true volume delta is not available from these
inputs. Never label candle direction times volume as true volume delta. If
volume delta is requested, document this gap and create a precise request under
`requests/inbox/` using the existing request workflow; continue all price-based
modules. A future volume-delta extension needs its own pinned data, side semantics,
unknown-side counts, matched coverage and new run.

## Event ledger and causal episode rules

Construct events in timestamp order using only information available by each
completed candle. A valid signal needs positive cumulative volume and positive
sigma, two consecutive valid bars from the same anchor/session, and contiguous
source data. Include valid early-anchor events; expose anchor ages 0–9, 10–29,
30–59 and 60+ minutes. A separately labeled 30-minute-minimum sensitivity tests
the effect of excluding the earliest signals. Do not select that cutoff from
outcomes.

Use a parent excursion to avoid counting every outside candle as a new setup:

1. Arm an anchor after observing a valid completed close inside or on its
   two-sigma envelope. An already-outside first valid observation is left
   censored and cannot be given an invented departure time.
2. Start the parent on the first later fresh close strictly above `VWAP + 2*sigma`
   or below `VWAP - 2*sigma`. Store side `d = +1` for upper and `d = -1` for lower.
3. Within that parent, record only the first fresh same-side crossing of each
   threshold 2, 2.5 and 3. The preceding completed close must be on or inside
   its own contemporaneous same-side band and the current close outside its
   current band. A jump across all three creates three linked threshold rows
   at the same timestamp, not three independent episodes. A later 3-sigma event
   starts its own forward clock; do not backdate it to the 2-sigma event.
4. The parent ends on the first causal evolving-VWAP contact, a whole-zone
   gap-through, reference overtake, data/contract break or session end. A
   reference overtake means the completed reference update moves the known
   VWAP zone across the current close without a source-price contact; it is
   not a traded touch. Record the reason and timestamp separately.
5. After termination, an observed valid inside-two-sigma close is required
   to rearm. The terminating candle may arm, but cannot also create a new
   departure; departure must occur on a later candle. Crossing back inside
   2 sigma without touching VWAP does not by itself start a new parent.

For an existing parent, process contacts/gaps in the just-completed candle
before any higher-threshold signal at that candle's close. For a newly created
parent, the original signal candle cannot satisfy a future touch. Preserve all
candidate/excluded rows and causal parent/threshold IDs. Store validity reasons
separately from false outcomes.

## Module 1 Price response after an outer band close

For each first threshold crossing, let `t0` be its exclusive close and `E` the
unadjusted open of the next two-minute candle, which opens at `t0`. Use the
one-minute source to cover `[t0, t0 + 2*h minutes)` for horizon `h`.
Do not include the signal candle's high/low or assume a fill at the threshold.
Follow the entire requested horizon even if VWAP is touched earlier.

Let `Hh` and `Lh` be the highest and lowest future prices, `Ch` the final close,
and `Oh` the open of the last two-minute candle in the horizon. Report both a
continuation direction `s=d` and a fade direction `s=-d`. For any direction `s`:

```text
price_delta = Ch - E
directional_delta = s * (Ch - E)
long_MFE  = max(0, Hh - E)       long_MAE  = max(0, E - Lh)
short_MFE = max(0, E - Lh)       short_MAE = max(0, Hh - E)
```

Report means, medians, p25/p75 and p90/p95 for MAE and MFE; mean/median and
p05/p25/p75/p95 for price/directional delta. Give points, ticks and units of
the frozen signal sigma, with the same eligible rows in each unit. Raw average
`Ch` and `E` may be included as descriptive columns per product, but centered
price delta is the principal close statistic across different years.

Report three distinct questions with numerators, denominators and ties:

- Did the horizon close finish above the entry open: `Ch > E`?
- Did it finish in the continuation/fade direction: `s*(Ch-E) > 0`?
- Was the final candle itself up: `Ch > Oh`?

Also retain `Ch - signal_close` to expose the next-open gap rather than silently
mixing it into the entry-based result. Report event count, parent count, distinct
product-session dates and weeks. MFE minus MAE is not terminal return or P&L.

## Module 2 Probability and timing of a return to VWAP

Start with exactly module 1's departure ledger, with the 2-sigma population
primary. Measure cumulative touch probabilities by 5/10/15/20/50 candles after
the relevant threshold signal. Outcomes continue to their original horizon
even if the causal parent has terminated; for example, a gap-through followed
by a later real contact can be a later module 2 touch, with the earlier gap
flagged. Parent termination controls event creation, not retrospective deletion
of a signal or truncation of its module 1/2 outcome window.

The primary target is the **causally evolving anchored VWAP**. At each future
one-minute open, use the most recent completed two-minute VWAP already available
at that instant. Hold that reference constant through that one-minute candle.
At a two-minute boundary the just-completed value can be used for the new
minute, never for either earlier minute. Round the center half-up to the product
tick and define a touch as overlap of the source low/high with its inclusive
plus/minus-one-tick zone. No future completed VWAP is applied backward to its
own high/low.

Secondary tables use VWAP frozen at the departure signal under the identical
touch rule. Report evolving-only and frozen-only contact. This distinguishes
price returning toward a reference from the reference moving toward price.
A complete gap across a zone or a reference overtake alone is not an exact
touch. Keep those flags and actual later touches; never infer a traded path
between non-overlapping source candles.

For each horizon report touch count/rate, no-touch count, missing and
boundary-excluded counts, 95% interval and the distribution of first-touch
latency among actual touchers. Touch time has one-minute resolution; store
the minute's open/close interval, not an invented exact trade time. Add the
equivalent two-minute candle number. Show a cumulative curve on the common
50-candle cohort and label latency summaries as conditional on touching.
Continue observing first touches to session end for module 3, labeling returns
after 50 candles separately from the requested fixed-horizon outcomes.

## Module 3 Response after the first return touch

Take each parent excursion's first genuine evolving-VWAP touch, provided it
occurs before a non-contact termination and inside the same session. This is
one event per parent. Higher-threshold strata use only threshold crossings
observed before the touch; never classify by the later maximum excursion.
Report 2-sigma parents as primary and nested reached-2.5/reached-3 cohorts as
secondary, plus return-latency groups 1–5, 6–10, 11–15, 16–20, 21–50 and >50
two-minute candles from the original departure. These groups are descriptive,
not a search for the best strategy.

Confirm contact only after the containing two-minute candle closes. Start the
5/10/15/20/50-candle response clock at the next two-minute open `E_touch`.
Exclude all touch-candle high/low from post-entry MAE/MFE. Save the touched VWAP,
the touch candle's close and the next open, so any displacement before the
measured entry is visible. Touch is an observed condition, not an assumed
limit-order fill at VWAP. No same-candle bounce can be credited to that entry.

An upper-band excursion returning from above has bounce direction **long** and
through-VWAP direction **short**. A lower-band excursion has bounce direction
**short** and through-VWAP direction **long**. Use these explicit words in tables
because “fade at VWAP” can otherwise refer to opposite directions.

Give both directions the full module 1 MAE/MFE and terminal-close statistics.
Define endpoint bounce as `d*(Ch-E_touch)>0`, through-direction endpoint as
`<0`, and unchanged as equality. This is separate from which direction moved
first. The next open may already be across VWAP; preserve the event and flag
its entry location rather than silently assuming entry at the reference.

For an objective first-move classification, freeze the valid sigma known at
the touch candle's close. Set symmetric barriers around `E_touch` at
`max(1, ceil(0.5*sigma_touch/min_tick))` ticks in either direction. For each
horizon show bounce barrier first, through barrier first, neither, and
same-one-minute ambiguous; unavailable paths are separate. When a source open
is already beyond one barrier, its opening crossing is known first and flagged
as a gap. If neither was resolved at the open and both are reached inside the
same minute, do not infer their order from OHLC. Interpret this explicitly as
a 0.5-sigma first-move definition, not a universal bounce win rate. Missing or
zero touch sigma makes this barrier outcome unavailable; retain otherwise valid
point/tick response metrics. Full-horizon MAE/MFE continues past either barrier.

## Denominators and statistical comparisons

Build the event ledger before applying horizon eligibility. Determine scheduled
time remaining causally, then require all source minutes and stable identities
for a complete measurement. A missing minute, truncated horizon, invalid reference
or contract change is unavailable, not a failure. Do not fill missing bars or
allow “50 available candles” to span an unscheduled gap. Record earlier observed
contacts on censored paths in the ledger but keep primary rates on complete
horizons; do not mix partial successes with a full-horizon failure denominator.

The unit of observation is an event, but correlated events share days, weeks,
anchors and thresholds. For uncertainty use a shared-ISO-week cluster bootstrap
with 2,000 replicates and seed 1501, resampling entire weeks jointly across all
products, sessions, thresholds and horizons. Report 95% intervals for mean
MAE/MFE, mean directional delta and probabilities; use paired week draws for
contrasts. Show the underlying event/day/week counts and flag cells with fewer
than 100 events, 30 distinct product-session dates or 20 weeks. Those descriptive
support flags are not pass/fail evidence of an edge. Zero successes are 0/n;
zero eligible cases are unavailable. If a zero/all-success cell produces a
degenerate bootstrap interval, explicitly mark boundary uncertainty unresolved;
do not present the degenerate interval as certainty.

Report calendar-year estimates, 2026 YTD, and the historical periods through
2023, 2024, and 2025–2026. They are stability diagnostics on previously inspected
history, not untouched training/validation/test evidence. Show product/session
results before any pooling. Compare thresholds descriptively: their events and
signal times differ, so a higher rate at 3 sigma is not a paired improvement
over entering at 2 sigma. Do not optimize thresholds, horizons or filters.

Use limited context summaries: upper/lower side, anchor age, local clock hour
and return latency. Keep marginal cuts readable; avoid a sparse Cartesian grid
of all conditions. The mandatory study is descriptive. Matched controls, a
predictive model, optimized stops, fees/slippage and strategy ranking are not
required to answer these questions and must not be smuggled into the first run.
No directional frequency or MAE/MFE extremum establishes executable profitability.

## Report and evidence design

Produce one offline master report plus four self-contained session reports:
Asia, London, New York and Globex, each in HTML and Markdown. Within each session
keep ES, NQ and GC separate, then upper/lower side and threshold. Every report
must state anchor/window, observation/entry convention, horizon units, sample
coverage and evidence limitations next to the relevant results.

The main tables should be easy to compare across horizons:

| Table | Essential columns |
| --- | --- |
| Departure response | Product, side, threshold, horizon, n, mean/median MAE and MFE for fade and continuation, mean directional close delta, above-entry %, final-candle-up %, ties, intervals |
| VWAP return | Product, side, threshold, horizon, target reference, n, touches, touch %, no touch, first-touch median/p75, gaps, unavailable, intervals |
| Touch response | Product, arrival side, reached threshold, horizon, n, bounce/through MAE and MFE, terminal delta, endpoint bounce %, four first-move classes, intervals |
| Coverage | Product, year, session, candidate/eligible counts, distinct parents/days/weeks and each exclusion reason |

Use stable IDs and save full distributions to CSV/Parquet rather than forcing
every percentile into the opening table. Add common-cohort horizon curves,
MAE/MFE distributions, terminal-delta distributions, return curves and year
stability plots generated only from saved tables. Select actual example paths
by a fixed rule, covering return, non-return, bounce, through, ambiguity and
exclusion; do not cherry-pick attractive trades. Include sigma/band references,
event/entry times and deadlines on examples.

Retain episode, threshold, touch and horizon ledgers with explicit foreign keys,
source references and schema/version. Save exclusions, input-check results,
exact commands, settings, code revision and dirty-source snapshot, environment
lock, metrics, tables, figures, reports, advice and artifact hashes. Large event
evidence needs a retained locator/checksum and backup/retention status outside
ordinary Git history; do not leave its only copy in disposable scratch.

## Implementation placement and sequence

All study logic belongs in `studies/15_vwap_excursion_response/`: `run.py` as the
thin entry point, `src/` for causal state/event/path/statistical/report modules,
and `tests/` for focused numerical checks. Add `pilot.py`, `verify.py` or separate
render/seal entry points only as useful. Shared methods move into Sahadeva only
when reuse is demonstrated. No indicator/Pine or Narada work is needed.

1. Read the root and component guides listed in the handoff prompt. Inspect the
   current dirty tree and preserve unrelated work. Resolve storage via
   `abacus_bhishma.paths.load_workspace_paths`; use the existing workspace lock
   and environment. Verify the input lock and consumed partition hashes.
2. Implement and test causal definitions with synthetic paths. Run a feature-only
   pilot for coverage, units, joins, candidate counts and reference validity.
   Sequential past observations may construct causal episode state, but do not
   aggregate future returns, MAE/MFE, touch rates or first-move outcomes yet.
3. Freeze `protocol-1.0.0.md` plus executable JSON/settings, report schema,
   thresholds, session rules, sample and tests before reading real outcomes.
   Record the decision and any feasibility change with its non-outcome reason.
4. Execute all three modules under a unique
   `work/15_vwap_excursion_response/<UTC-run-id>/`. Process manageable partitions
   deterministically and keep failed/intermediate executions identifiable.
5. Independently recount representative paths from one-minute source; reconcile
   ledgers and denominators. Render reports from verified saved evidence and
   inspect their tables and figures. Keep negative and inconclusive results.
6. Seal a new `runs/15_vwap_excursion_response/<run-id>/` only after checks pass.
   Never overwrite or append to an existing completed run. Document retained
   event storage. Update README, notes and navigation metadata with exact links;
   choose a reference run explicitly after review, not by recency.

The research report stays local. Any later indicator is a separately requested
presentation project using the new saved tables. External publication is a
separate decision; if authorized later, follow Narada's explicit bundle contract
and the presentation-export lifecycle rather than altering a sealed run.

## Required checks

Focused tests must cover upper/lower symmetry; exact equality versus strict
threshold crossing; 2.5-sigma calculation; jump across multiple thresholds;
already-outside initial data; rearming and parent deduplication; no signal-bar
leakage; lagged evolving VWAP availability; frozen/evolving disagreement;
gap-through and reference overtake without traded touch; touch confirmation
and excluded touch-bar movement; correct 5/10/15/20/50 candle indexing; entry
versus terminal-candle-open comparisons; zero-sigma cases; missing minutes;
roll/adjustment breaks; DST, midnight, session ends and local gaps; late-horizon
exclusions; symmetric-barrier same-minute ambiguity; and null versus false.

On the same event cohort MAE, MFE and cumulative touch flags must be monotone
across longer horizons. Long MFE equals short MAE and long MAE equals short MFE
for the same entry/path. Terminal up/down/tie counts and first-move class counts
must reconcile to their declared denominators. Confirm adjustment-invariance
of relative features under a constant translation. Hashes and independent
source recounts must reconcile to saved report values.

Run the owning study's focused tests and audit. Run
`python3 scripts/check-agent-docs.py` for guidance, and regenerate the research
index when metadata changes, followed by
`python3 scripts/build-research-index.py --check`. Use `./scripts/check-workspace`
only if package/configuration/migration changes require it. Do not rebuild
Narada or rerun archived studies merely to verify this research.
