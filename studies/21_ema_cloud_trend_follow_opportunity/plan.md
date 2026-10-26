# 20/50 5minEMA Cloud Trend Follow Opportunity Study

Study 21_ema_cloud_trend_follow_opportunity · Proposed protocol 0.1.0 · October 10, 2026.

The question is whether a pullback touching the EMA20/50 cloud offers subsequent
movement in the prevailing trend direction, how much adverse movement accompanies
it, and whether cloud width improves the quality of those opportunities. The
EMA cloud stays on five-minute closes; signals and forward measurements use
three-minute or five-minute candles in ES, GC and NQ.

Every stage ends with a complete report: findings supported by saved numerical
tables, coverage and uncertainty, limitations, reproducible evidence, and selected
Narada-ready content. Negative or inconclusive results are publishable findings.
This proposal authorizes planning only. Implementation and execution will be
commissioned through separate stage prompts after review.

## Stage sequence and decisions

| Stage | Research question | Added complexity | Publishable result |
| --- | --- | --- | --- |
| 1 | What follows a slow EMA touch under the specified width minima? | Six product/candle cells; fixed rules and horizons | Opportunity frequency, MAE/MFE distributions, terminal movement and stability |
| 2 | What changes when the fast EMA is also studied? | Independent fast/slow streams and overlap comparisons | Whether fast touches add frequency, change adverse movement or capture different paths |
| 3 | Which width gateways and horizons improve the quality/coverage tradeoff? | Absolute versus ATR width grid and chronological selection | Development surfaces, frozen candidates, reserved-period comparisons and stable parameter regions |

Stages add evidence without replacing earlier records. Stage 2 must reproduce
Stage 1's slow branch under identical settings. Stage 3 retains both fixed-width
branches as benchmarks. Each stage receives a new run ID and report source;
earlier completed runs remain immutable.

## Proposed defaults to freeze before execution

| Item | Proposed definition |
| --- | --- |
| Products | ES, GC, NQ outright futures; no pooling of their raw points |
| Signal/outcome candles | 3m and 5m, independently aggregated from 1m |
| Cloud | EMA20 and EMA50 of completed 5m closes; lengths/timeframe fixed throughout |
| Fixed minimum cloud width | ES 2.4 points; NQ 10 points; GC 2.0 points; inclusive |
| Directions | Buy in a bullish cloud; Sell in a bearish cloud; All/Buy/Sell report views |
| Pullback convention | One signal per selected-EMA pullback, with the supplied source's arm/consume rules |
| Cooldown | Zero chart bars; no cooldown optimization in these stages |
| Reference price | Confirmed signal candle close; an observation convention rather than a fill |
| Primary horizon | 15 signal candles; proposed research choice, distinct from the source's default 10 |
| Descriptive horizons | 5, 10, 15, 20, 30, 50, 100 candles; add H=12 for the 5m 60-minute comparison |
| Session | All supported electronic-session bars; report New York time/session strata separately |
| Feature warmup | At least 250 consecutive usable 5m observations after a contract/unknown-gap reset |
| Stages 1–2 visible outcomes | 2018–2020 development; optional earlier 2010–2017 robustness panel |
| Later periods | 2021–2023 validation; 2024–2025 final evaluation; 2026 through September 18 recent replication |

These are proposed defaults, rather than unspecified choices left to an engine.
The first scoped prompt should confirm or amend them. In Stage 3, interpret
"candle thickness" as the EMA cloud's width; candle range/body filters are outside
this grid. Changing the EMA timeframe to 3m would answer a different question.

## Historical inputs and quality audit

### Retained inputs

The [prior ES/NQ/GC inventory](../20_camarilla_ema_cloud_reversals/data-inventory.md)
and the catalog identify retained history from June 7, 2010 trading session through
September 18, 2026. This is the available endpoint, rather than October 2026.
The current planning inspection found all 51 declared product/year partitions
present for each of the three releases below, with manifest sizes matching.
Complete partition-byte verification remains a prerequisite to execution.

| Input | Intended role | Treatment |
| --- | --- | --- |
| [volume_lead_unadjusted_v1](../../catalog/datasets/volume_lead_unadjusted_v1.json) | Primary 1m contract prices and identifiers | Pin manifest, consumed partitions, roll schedule and instrument master |
| [volume_lead_back_adjusted_v1](../../catalog/datasets/volume_lead_back_adjusted_v1.json) | Optional additive-price reconciliation | Frozen synthetic snapshot; no direct execution/P&L interpretation |
| [existing 5m OHLCV delivery](../../catalog/datasets/tv_indicators__dridr_ohlcv_5m__v1.json) | Aggregation/lineage cross-check | Adjusted prices; reconcile by exact adjustment translation |

The 5m delivery contains bars and lineage despite its DR/IDR name. It does not
supply this study's cloud or touch labels. No retained 3m delivery was found;
derive 3m from 1m, never from 5m or Range XV. Specialized GC bands and VWAP-day
eligibility are not substitutes for the requested inputs.

Older history requires a separate qualification: existing all-session 5m partial
shares in 2010–2017 are ES 4.295%, NQ 21.082% and GC 7.897%, versus 0.393%,
0.246% and 2.299% from 2018 onward. These are retained-delivery quality counts,
not this study's signal eligibility. The proposed main start is therefore 2018.

### Preparation steps

1. Resolve storage through [path configuration](../../config/paths.example.toml)
   and documented overrides. Use Bhishma public loaders with explicit
   manifest/hash pins. Never hardcode a package directory as the publication root.
2. Pin the selected release manifests and every consumed partition, schedules,
   instrument records, calendar specification and source-condition records.
   Verify hashes before analysis and retain a portable input lock. Save the
   supplied Pine source and its hash as a semantic reference.
3. Audit timestamps, sort order, duplicate keys, contract/product identity,
   positive/tick-valid prices, OHLC bounds, nonnegative volume, source counts and
   per-product/year coverage. Record every excluded row/bucket by reason.
4. Establish expected tradable minutes using historical session regimes,
   holidays and early closes. The old ES/NQ afternoon pause and pre-2015 GC close
   need handling in earlier-history work. Do not inherit VWAP's two-minute
   calendar exclusions or Camarilla's prior-session requirements.
5. Aggregate both intervals directly from 1m using New York fixed-clock buckets:
   3m at :00/:03/.../:57 and 5m at :00/:05/.../:55. Use half-open intervals,
   first open, maximum high, minimum low, last close and summed volume. Preserve
   UTC identity, New York offset, modeled close/available-at time, minute
   membership, missing offsets, source count and contract lineage.
6. A usable primary bucket must contain every expected source minute and exactly
   one contract. Preserve partial/mixed/empty buckets as quality records;
   fabricate no prices, zero-volume candles or missing-minute fills. An absent
   no-trade minute does not establish source corruption.
7. Reconcile rebuilt 5m OHLCV/lineage against the pinned existing 5m release where
   their contracts and calendar anchors agree, translating its adjustment exactly.
   Explain differences outside that support. Validate new 3m aggregation with
   synthetic fixtures and independent minute-to-bucket reconciliation.
8. Build the causal feature layer, audit its timestamps and warmup, then freeze
   the eligible decision-bar roster. Future path quality must not influence
   whether a historical signal was generated or which later setup is armed.

Source bar timestamps identify opens. Derived available-at is modeled completion,
not actual vendor receipt. Mapping effective sessions are retained; original
mapping arrival/publication times are absent. Individually certified annual
holiday schedules are also not currently established. Disclose these limits and
calendar-dependent exclusions; the study is historical descriptive research,
not a certified reconstruction of a live data feed.

The consecutive-complete-bar warmup is deliberately conservative and may remove
substantial overnight/GC history. Show feature-eligible coverage before scoring
outcomes. If that audit makes the proposed sample inadequate, revise and freeze
the quality/warmup policy using input quality alone before any outcome inspection;
do not quietly relax it to obtain attractive results.

### Price basis and resets

Use unadjusted same-contract bars for the primary cloud and all reference/path
prices. Reset EMA/ATR state at a selected-contract switch and at an unknown
feature-history gap; require warmup again. Carry state across known scheduled
maintenance/closures within the same contract. A contract roll must never create
a fake trend or excursion. Censor an outcome crossing a contract switch even
when the continuous series supplies a price on both sides.

This is a declared roll-handling choice. It differs from a chart's arbitrary
continuous-contract adjustment convention. A final back-adjusted cloud may be
checked later as a separately labeled sensitivity, with consistent translation
to the observed contract basis. Do not assume parity across a roll or use a
future cumulative adjustment as proof of real-time feature availability.

Reusable aggregation and five-minute EMA/ATR definitions belong to Bhishma.
After the Stage 1 scope is approved, create a request under requests/inbox/ using
the [request workflow](../../requests/README.md), then a new immutable delivery
if needed. Do not rebuild existing releases. Signal rules, pullback episodes,
forward labels and estimates remain with this Sahadeva study.

## Feature and evidence design

| Layer | Required fields | Available when |
| --- | --- | --- |
| Base 3m/5m bars | Product/contract, UTC open/close, OHLCV, source counts/lineage, complete/partial/mixed flags, session/calendar regime | Candle completion |
| 5m cloud | EMA20, EMA50, upper/lower, signed difference, absolute width, trend sign, source bar and available-at, reset/warmup status | Completed source 5m bar |
| 5m volatility | True range, Wilder ATR14, width/ATR, valid seed/history flags | Completed source 5m bar |
| Mapped decision features | Selected cloud/ATR source, timing mode, width threshold, gate pass, source age | Defined by the mapping below |
| Event ledger | Direction, selected EMA, geometric touch flags, pre/post arm state, episode ID, candidate/acceptance flags, suppression reasons, reference close | Signal candle confirmation |
| Forward outcome ledger | Horizon/end time, MFE, MAE, signed close delta, attainment intervals, complete/censored reason | Horizon completion only |

EMA recurrence is alpha times close plus (1-alpha) times the prior EMA, with
alpha=2/(length+1), a declared first-close seed and 250 usable-bar warmup.
Freeze exact initialization and numerical tolerance; use a 500-bar sensitivity
to quantify residual seed dependence rather than selecting warmup by returns.
True range is max(high-low, abs(high-previous_close), abs(low-previous_close))
within a contract segment. Wilder ATR14 seeds from the first 14 usable true
ranges and then updates as (13 times previous ATR + current TR)/14.
ATR normalization requires positive valid ATR; invalid values stay undefined.

Width is abs(EMA20-EMA50). Bullish means EMA20>EMA50, bearish means EMA20<EMA50;
equality has no directional event. No tick rounding of EMAs or width thresholds.
The source uses an epsilon of 1e-10 times max(1, absolute threshold) for inclusive
width comparisons; retain and test that boundary convention.

Slopes, candle body/range, bars since crossover, time-of-day and prior-known
volatility may be saved for descriptive context. They are not extra entry gates
or search dimensions in this proposal. Forward outcomes remain clearly labeled
and separate from signal-time features.

## Exact signal timing and state logic

### Five-minute cloud on two candle intervals

Follow the supplied [Pine source](reference/ema_cloud_trend_follower_user.pine):

- On a 5m signal candle, use that completed candle's current EMA values at its
  close. Its range can then be tested against those close-derived levels.
- On a 3m signal candle, freeze the most recent completed 5m cloud available
  at the 3m candle's OPEN, matching the source's confirmed higher-timeframe
  convention. Use that level for the entire touch range test.
- For example, a 09:33–09:36 candle uses the 5m cloud that completed at 09:30;
  the cloud completing at 09:35 does not replace its touch level midway through
  the candle. Retain the exact source bar/time and modeled available-at.
- ATR for Stage 3 uses the same mapping as its cloud. No interpolation,
  developing higher-timeframe EMA, or backward use of future feature values.

The mapped source must also be the latest SCHEDULED 5m slot expected to have
completed at that decision reference time, accounting for known closures, and
must pass source validity/warmup. A missing or partial latest slot makes the
mapped cloud/ATR undefined immediately and clears armed state; an as-of join
must not silently carry an older cloud through that gap. Establish this from
information available then, without waiting for the next observed source bar.
Retain invalid/reset source records rather than dropping them before the join.
The selected cloud source contract must match the signal candle's contract.

Because 3m does not divide 5m, test these alignments directly. This timing choice
means the two candle intervals differ in feature staleness as well as candle
aggregation. Describe it in every comparison. A uniform cloud-known-at-open
convention for both intervals can be a separately authorized sensitivity; it
must not silently replace the baseline. Synthetic parity tests establish the
translated rules under identical inputs, not native TradingView verification.

### Pullback event definition

Process bars chronologically for each product/candle interval and selected EMA.
Both directions are enabled; Buy and Sell are conditional on cloud direction.

1. On missing/unusable cloud, equality, direction change or data/contract reset,
   clear the relevant armed state.
2. A full confirmed candle strictly above the bullish cloud arms a Buy; a full
   candle strictly below the bearish cloud arms a Sell. Consecutive departure
   candles extend the same armed episode rather than creating extra entries.
3. A touch is inclusive: low <= selected EMA <= high. Test the cloud direction,
   pre-bar armed state, data eligibility and the inclusive width gateway at
   this touch candle. If all pass, accept one event at its close.
4. Any penetration of the selected EMA consumes its setup, even if the candle
   gaps beyond rather than straddles it, or width rejects the event. A fresh
   full departure outside the entire cloud is needed to rearm.
5. In the slow branch, touching only fast does not consume the slow setup.
   In Stage 2, fast and slow have independent armed states. Preserve direction
   resets and consumption for rejected candidates in both branches.
6. Finish state updates before processing the next candle. Zero cooldown permits
   another eligible event on the next candle, subject to the pullback rule.

Use a chronological technical-candidate ledger before thickness filtering and
future exclusions. Stage 3 applies each gateway independently to that history;
it cannot filter the already accepted fixed-width signal list. Gateway rejection
consumes the touched setup under the same source rules. Future missingness,
completion, split assignment or an opposite signal never changes acceptance.

The touch is a confirmed candle-range observation. It is not a simulated limit
fill at the EMA, and the reference price is not the EMA itself. No additional
rejection-body, close-above-cloud or bounce confirmation is required.

## MAE and MFE computations

For accepted event i, reference E is its unadjusted signal close and direction
d is +1 for Buy or -1 for Sell. For the following H scheduled chart bars,
excluding the signal candle, let U be the maximum high, L the minimum low and
C_H the terminal close.

| Metric | Buy | Sell |
| --- | --- | --- |
| MFE | max(0, U-E) | max(0, E-L) |
| MAE | max(0, E-L) | max(0, U-E) |
| Signed terminal delta | C_H-E | E-C_H |
| Favorable close | terminal delta > 0 | terminal delta > 0 |
| MFE exceeds MAE | MFE > MAE with declared tie tolerance | Same |

Report raw price points first. Also report MFE/entry ATR, MAE/entry ATR and
terminal delta/entry ATR where ATR is valid. Explain numerator/denominator and
never add ES, GC and NQ points together. MFE/MAE are positive excursions;
terminal delta can be positive, negative or zero. Zero terminal delta is neutral.
Do not make a headline ratio from MFE/MAE when MAE is zero; report numerator
and denominator separately. MFE and MAE generally occur at different times.

H counts scheduled tradable candle slots; known closures do not fabricate bars,
and unknown missing slots do not collapse the timeline. Record nominal active
minutes H times interval and actual elapsed time. Observations may continue
across a session boundary/known closure within the same contract. Include a
same-session descriptive panel; mark paths crossing closures in clock-time
comparisons. Compare 60 active minutes as 3m H=20 versus 5m H=12, and 150 as
3m H=50 versus 5m H=30, with uninterrupted-path views for actual clock minutes.
Fifteen 3m candles and fifteen 5m candles are different durations.

Overlapping observations are allowed. An opposite signal does not close an
observation. Save first attainment candle intervals for MFE/MAE, using the first
interval in a tie; zero excursion has no attainment time. OHLC cannot establish
within-candle ordering, an executable stop/target combination, or an optimal exit.

If any required outcome slot is missing, partial, mixed-contract or crosses a
roll, that horizon is undefined and receives a reason-coded null. Shorter complete
horizons may still be evaluable. An event at the data edge remains pending/right
censored. Keep generated, accepted, completed and censored counts separate;
never recode missing outcomes as zero or quietly drop them from the signal flow.

## Chronological evaluation and uncertainty

### Reserve later outcomes from the beginning

| Period | Role | When its outcomes may be viewed |
| --- | --- | --- |
| 2010–2017 | Optional earlier-history robustness, quality-qualified | Stage 1/2 development appendix, separately labeled |
| 2018–2020 | Development and initial publishable insights | Stages 1 and 2; Stage 3 grid/fold scoring |
| 2021–2023 | Validation of frozen candidate rules | Stage 3, after development shortlist is locked |
| 2024–2025 | Final evaluation | After candidate configuration and claims are frozen |
| 2026 through September 18 | Recent replication | After final evaluation, with no retuning |

Stage 1/2 reports must not reveal reserved outcomes through distributions,
selected examples, yearly charts, gate rankings or narrative conclusions.
Coverage/schema/input integrity can be audited across all dates without scoring
those outcomes. This reservation concerns this new study. Study 20 and prior GC
studies have used parts of the later market history; record that exposure and
avoid claims of a pristine market holdout. Truly new confirmation needs later
data under frozen rules.

Assign events by signal time. Exclude from split scores any path extending into
the next period, retaining it as boundary-censored evidence. Warmup can use prior
causal bars. Keep signal/pullback state continuous at year/split boundaries;
do not invent a January reset. For selection folds, purge boundary-crossing
paths and embargo at least the maximum 100-bar observation span on each fold's
tradable timeline; record actual boundaries rather than treating 500 minutes
as a universal clock duration over closures.

### Estimates and dependence

For every cohort/horizon, save counts, contributing sessions/weeks, mean/median
MFE and MAE, P10/P25/P50/P75/P90/P95, mean/median signed delta, favorable/neutral/
adverse close shares, and MFE>MAE share. Save exact deciles separately to reproduce
the source's percentile view. Top-tail cutoffs are percentiles, not tail averages.
Keep the full eligible completed population primary; a recent-N plot is a labeled
display window, not a replacement denominator.

Provide event-weighted and session-balanced means. For the latter, average within
each contributing session, then across those sessions; this is conditional on
having evaluable events. Opportunity counts/rates also use the broader auditable
eligible-bar/session roster, including valid zero-event sessions. A session with
unknown signal coverage cannot be asserted to contain zero opportunities.

Use paired contiguous New York calendar-week blocks, proposed four-week block
length, 10,000 resamples and seed 20261010. Resample the same blocks for compared
touch/gateway branches and across products. Show pointwise 95% intervals and
one-/eight-week block sensitivities for headline contrasts; overlapping signals
and contemporaneous ES/NQ behavior are not independent observations.

Display sparse warnings below 100 completed events or 30 contributing sessions.
Do not turn a sparse favorable average into a recommendation. Undefined bootstrap
draws and inadequate support remain explicit. Continuous missing outcomes have
no invented worst-case price; percentages can additionally show missing-outcome
best/worst bounds against the accepted-event denominator.

Stage 2 has six primary fast-minus-slow terminal-delta contrasts at H=15, one per
product/candle cell. Stage 3 has at most twelve primary selected-gateway-minus-
fixed-gateway contrasts at H=15, one per product/candle/touch cell. Use paired
blocks and familywise intervals across each declared family, alongside pointwise
intervals. All other grid and subgroup intervals are descriptive. Search scores
on development are not independent confirmation.

## Stage 1 slow EMA touches under fixed gateways

### Implementation and analysis steps

1. Freeze protocol version, date allocation, calendar, price basis, warmup,
   signal timing, episode state, horizons and the ES/NQ/GC user-fixed minima.
2. Complete the Bhishma request/delivery and input audit described above. Build
   and verify the common bar/cloud features once for later stages to reuse.
3. Implement the study-local slow-touch event engine and forward outcome scorer.
   Keep raw candidates, accepted events, suppressions and horizon censoring.
4. Run synthetic numerical tests and a small declared development slice for
   reconciliation before the full authorized development calculation. Do not
   use a successful large run as a substitute for definition tests.
5. Score six product/candle cells, pooled directions plus Buy/Sell views, at the
   frozen horizons. Produce raw-point and ATR-normalized summaries and deciles.
6. Show year/week/month stability, session/time-of-day strata and horizon curves.
   These are descriptions under a fixed rule, not a search for a favorable hour.
7. Select chart examples by a prespecified rule from development: typical,
   high-adverse, high-favorable and rejected/partial cases. Retain selection IDs
   and avoid showcasing only attractive signals.
8. Generate full and selected reports from saved tables, reconcile every claim
   and displayed value, verify the bundle, then seal a unique Stage 1 run.

### Questions the report must answer

- How often does the exact slow-touch rule generate opportunities in each cell?
- What are typical and upper-tail adverse/favorable excursions over each horizon?
- How often is the terminal close favorable, and how often does MFE exceed MAE?
- Does apparent movement persist across years, sides and session strata?
- How much do coverage, missing paths and elapsed-time differences limit comparison?

Required output tables are S1-T00 coverage/quality, S1-T01 signal flow/exclusions,
S1-T02 horizon scorecard, S1-T03 excursion quantiles/deciles, S1-T04 annual/session
stability, S1-T05 weekly/monthly summaries and S1-T06 example selections.
Figures include horizon curves, MAE/MFE quantile curves on a common scale,
calendar stability and saved event illustrations.

Stage 1 completes when the six cells reconcile to their ledgers, boundary and
timing fixtures pass, all outcome/censoring denominators are explicit, and a
standalone report plus selected publication source can be read without Stage 2.
Its conclusions remain development-period findings.

## Stage 2 independent fast and slow touch comparisons

### Implementation and analysis steps

1. Pin the Stage 1 run/features and reuse its exact slow branch. Add an independent
   fast-touch arm/consume stream under the same fixed width minima and horizons.
2. Prove slow signal IDs, outcomes and Stage 1 aggregates are unchanged. A desired
   rule correction requires a new baseline run, not a quiet Stage 2 adjustment.
3. Save two memberships: candle geometry (fast only, slow only, both) and accepted
   stream membership after episode/quality/gateway logic. They are not interchangeable.
4. Present standalone fast and slow cohorts. Build a union view with one observation
   per product/candle/direction/signal bar; a same-bar dual touch cannot count twice.
   If the branches signal on different bars, retain different event times.
5. Compare the two branch means by calendar blocks/common eligible support.
   Report both unconditional branch differences and paired same-bar dual touches,
   whose reference prices and forward paths should agree exactly.
6. Add episode-matched descriptive comparisons: fast touch time, later slow touch
   when present, time/reference-price difference and conditional paths. A future
   slow touch must never become a signal-time fast-entry filter. Report fast
   episodes that never reach slow and episode-boundary ambiguities.
7. Separate differences in event frequency/population from differences in path
   behavior; show shared-horizon and equal-active-minute comparisons.
8. Generate and seal a new Stage 2 report/evidence bundle, retaining Stage 1 as
   an explicit reference rather than replacing its report.

For matching, define a separate shared geometric episode per product/candle
interval/direction/contract segment. Its first qualifying full-cloud departure
starts an episode; consecutive full-departure bars retain the ID. After any
non-departure bar, the next full departure ends the prior episode and starts a
new ID. A direction/quality/contract reset ends it immediately. Assign events
to the active geometric episode at signal time, and pair its first accepted
fast event with its first accepted slow event when both exist. Do not pair
across a new departure/reset or change either branch's independent arm state.
Classify unpaired and same-bar events explicitly; eventual pairing is a
retrospective descriptive label.

Required tables add S2-T07 touch geometry/membership, S2-T08 branch contrasts,
S2-T09 episode pairing and S2-T10 union/overlap diagnostics, alongside Stage 2
versions of coverage, flow, scorecards, quantiles and calendar summaries.
Figures compare distributions, horizon responses and opportunity counts for
both boundaries, including common-support and matched-time views.

Stage 2 completes when slow parity holds, dual-touch union identities reconcile,
retrospective pairing is clearly labeled, six primary contrasts have uncertainty,
and the report answers what fast touches add without implying a combined executable
strategy. A position policy using both entries is a later separate question.

## Stage 3 cloud width and horizon search

### Gate and horizon grid

Keep EMA lengths/timeframe, ATR14 length, session policy, reference price,
pullback semantics and cooldown fixed. Study the following bounded grid:

| Dimension | Prespecified candidate values |
| --- | --- |
| Absolute minimum width | Asset fixed minimum times 0, 0.5, 0.75, 1, 1.25, 1.5, 2, 3 |
| ATR minimum width | Width/ATR14_5m >= 0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.00, 1.50 |
| Horizon candles | 1, 2, 3, 5, 10, 12, 15, 20, 30, 40, 50, 60, 80, 100 |
| Touch mode | Fast and slow, separately |
| Product/candle cell | ES/GC/NQ times 3m/5m |

The zero absolute gateway is the no-minimum-width control; directional inequality
still applies. Do not duplicate that zero under ATR. The absolute point grids are
ES [0, 1.2, 1.8, 2.4, 3.0, 3.6, 4.8, 7.2],
NQ [0, 5, 7.5, 10, 12.5, 15, 20, 30], and
GC [0, 1, 1.5, 2, 2.5, 3, 4, 6].

This gives 16 gates times 14 horizons times 12 product/candle/touch cells =
2,688 development grid cells before Buy/Sell and stability breakdowns.
Buy/Sell are diagnostic strata, not independently optimized rule sets. Candidate
gates must generate their own acceptance stream; horizon scoring is shared only
for identical accepted events. Use identical ATR-valid support when comparing
absolute and dynamic gates, plus report full absolute-gate support separately.

### Definition of a better outcome

Primary gateway selection occurs at the frozen H=15 horizon. Rank by mean signed
terminal delta divided by entry ATR, measured on chronological development folds;
publish raw-point estimates as well. MFE alone is unsuitable as the objective
because a large favorable maximum can coexist with large adverse movement and
an unfavorable terminal close.

Proposed candidate eligibility, to freeze before grid inspection:

- At least 200 completed events in the scored 2019–2020 folds, 60 contributing sessions and
  20 contributing weeks; at least 25 events and 10 sessions in each scored fold.
- At least 20% of the comparable fixed-gateway event count, to expose the
  opportunity cost of narrow selection.
- Fold-pooled normalized mean MAE no higher than the same-support fixed baseline;
  normalized mean MFE at least 90% of baseline.
- Improvement in signed terminal movement over the baseline in at least three
  of four scored half-year folds, rather than one extreme winning interval.

Use 2018 as the initial history, then expanding prior history with scored folds
2019 H1, 2019 H2, 2020 H1 and 2020 H2. Apply the purge/embargo rule. These are
proposed support/tradeoff requirements, not guarantees of reliability. If no
candidate qualifies, retain the fixed baseline and report no supported improvement.
Ties favor stronger coverage, then the simpler absolute gateway, then smaller
minimum width. Log the actual deterministic comparison tolerance.

For each fold compute mean over events of (signed delta / entry ATR), then rank
by the equally weighted mean of the four fold estimates. Pool completed events
across those scored folds for the stated support and MAE/MFE guards, and also
publish equal-fold and event-weighted summaries. The same-support comparator
uses the identical eligible date/feature/ATR/path roster, with each gateway's
own accepted events. It does not intersect accepted candidate and baseline
events: nested thickness gates would otherwise yield identical path samples.
Outcome eligibility is a scoring restriction after independent signal acceptance,
never a prospective entry filter or a change to pullback state.

### Joint horizon interpretation

Evaluate all thickness-by-horizon cells against their same-horizon fixed baseline.
Report a frontier of retained opportunities, normalized terminal movement, MAE
and MFE, and contiguous regions of similar performance. Longer horizons
mechanically allow greater extrema; the largest raw MFE does not identify an
optimal holding period. This plan recommends a fixed-horizon primary gateway
decision plus horizon-specific exploratory combinations rather than forcing one
global horizon winner.

If the later Stage 3 prompt requires a single gateway/horizon pair per cell,
freeze that secondary objective BEFORE scoring: proposed mean of
(signed delta / entry ATR) / actual elapsed hours, with the same support/risk
requirements. Describe this as an overlapping price-path movement rate, not
hourly trading profit. Compare it to the unchanged baseline at the selected
horizon and report nominal/actual duration. Do not switch ranking objectives
after seeing which definition gives the most attractive result.

### Selection and reserved evaluation steps

1. Freeze gate/horizon lists, objective, support constraints, tie-breaking,
   fold/split boundaries, primary comparison family and report selectors.
2. Calculate the complete development grid and retain every candidate, failed
   support reason, fold score and exclusion. Show neighboring parameter values
   and uncertainty; isolated peaks are weak candidates.
3. Select at most one primary gateway per product/candle/touch cell at H=15
   from development, and hash the shortlist before reading 2021–2023 outcomes.
4. Evaluate only that shortlist and the fixed baseline on validation. Apply the
   frozen validation criteria below. A validation failure
   falls back to the baseline; do not browse alternative validation winners.
5. Freeze the final configuration and interpretation rules. Evaluate 2024–2025
   once, then 2026 replication without retuning. Report twelve or fewer primary
   contrasts and the declared familywise intervals, including failures.
6. Use reserved data for frozen comparisons, not a new full-grid search. Any
   validation-driven redesign needs a new protocol/run and disclosed exploratory
   status; consumed periods do not become pristine holdouts again.
7. Publish the development heatmaps/frontiers, frozen choice rationale,
   validation/final/recent scorecards, coverage and negative findings together.

Validation uses all six 2021–2023 half-years: require pooled support of 200 events,
60 sessions and 20 weeks, at least 25 events/10 sessions per half-year, retention
of at least 20% of baseline events, the same normalized MAE/MFE guards, positive
pooled mean normalized terminal-delta improvement and improvement in at least
four of six half-years. Freeze these separately from the four development folds.
Final/recent outcomes are assessments of the frozen choice: publish effects,
uncertainty, support and failures without selecting replacements or inventing
new pass rules. Sparse final/recent evidence remains inconclusive.

Required tables are S3-T11 full development grid, S3-T12 fold/support scores,
S3-T13 frozen candidates/decision log, S3-T14 reserved-period contrasts,
S3-T15 parameter neighborhoods/frontiers and S3-T16 split/censoring audit,
plus the common coverage, flow, horizon and quantile tables.

Stage 3 completes when the grid is fully inventoried, choices are frozen before
reserved outcomes, every finalist has a same-horizon baseline, support/risk
tradeoffs are visible, and final findings distinguish historical descriptive
optimization from fresh confirmation or achieved trading profitability.

## Numerical verification and scientific reconciliation

Implementation must include meaningful fixtures for:

- Exact 1m to 3m/5m aggregation, lineage, partial/mixed buckets and half-open edges.
- EMA/ATR seed, warmup, trend equality, width boundary/epsilon and ATR-invalid cases.
- 3m/5m cloud availability at awkward boundaries, prefix invariance and no
  future-bar changes to already confirmed signals/features.
- Armed departures, fast-only versus slow touches, gaps through the selected EMA,
  rejected-touch consumption, direction changes and zero-cooldown behavior.
- Hand-calculated long/short excursions, entry-bar exclusion, neutral deltas,
  cumulative extrema, overlapping paths and per-horizon incomplete outcomes.
- Contract rolls, unknown gaps, scheduled closures, DST folds, early closes and
  the data-end boundary; no silent compression or fabricated bars.
- Stage 2 slow parity and dual-touch identity, plus independent Stage 3 gateway
  streams, original chart-bar positions and split/fold purging.
- Ledgers-to-summary counts, quantile definitions, side/union identities, block
  resampling, public source-cell equality, null versus false/zero and hash gates.

Use a scalar reference calculation and independent reconciliations where useful.
Retain actual numerical test commands, results/logs and scientific verification
receipts bound to the stage inputs, code and outputs before sealing. The bounded
existing numerical-test recorder supports only studies 08/09/10/12/13; extending
it to study 21 is separate implementation work, not an already working command.

The workspace registry will gain a numerical suite when implementation exists.
Run focused study tests in their own locked process. Changes to Bhishma/shared
package/configuration also require the workspace gate. Integrity checks verify
declared bytes, not the calculations or completeness of scientific validation.

## Saved artifacts and ownership

Use a thin future run.py entry point, local src/ modules and tests/ under this
study. Proposed modules separate inputs/features integration, event state,
forward paths, summaries, optimization, rendering and verification. Reuse existing
shared methods only where semantics match; do not build a universal research engine
or put numerical code into root scripts.

Stage each execution at work/21_ema_cloud_trend_follow_opportunity/<unique-run-id>/.
After all required checks, seal a fresh runs/21_ema_cloud_trend_follow_opportunity/
<unique-run-id>/ bundle. Save large ledgers in configured retained research storage
with schema, row count, locator, checksum and retention status. Never overwrite
source data, retained historical work or an existing run.

| Artifact | Contents |
| --- | --- |
| protocol.md and config.json | Frozen stage definitions, parameters, splits, selection and exclusions |
| inputs.lock.json and exclusions.json | Exact release/partition/feature identities and reason-coded audits |
| provenance/ | Retained source bytes, Git revision/dirty status, uv.lock, actual environment inventory, commands and check records |
| events.manifest.json | Technical/event/outcome ledger schemas, identities, locators and hashes |
| metrics.json and tables/ | Stable estimate IDs and exact tabular numerical evidence, denominators and uncertainty |
| figures/ | Saved-table-derived research figures; selected raster variants for Narada |
| report.md and report.html | Complete offline stage report, methods, findings and reproduction instructions |
| advice.md | Dated interpretation with exact supporting/opposing table-row references |
| publication.json and downloads/ | Selected Narada 1.1 report source and explicit summary CSVs |
| publication-source-map.json | Private bindings from claims/display cells/figures to exact saved artifacts |
| manifest.json | Unique study/run/stage provenance and all declared artifact hashes |

Adopt [abacus.evidence/v1](../../docs/evidence-contract.md) explicitly for each new
quantitative research bundle, using its exact allowed fields. Keep additional
stage/test/selection metadata in inventoried companion files rather than inventing
top-level contract fields. The validator assesses declared local bytes; external
ledgers need a separate explicit byte check. Metrics/event/source-map designs are
study-owned conventions until their own schemas/checks are implemented.

Stable table row keys include stage, product, EMA interval, signal interval,
direction, touch mode/membership, gate ID, horizon bars/nominal minutes, split
and support cohort. Event IDs bind product, contract, bar time, direction and
touch stream; union IDs omit stream identity to prevent duplicate same-bar counts.
Do not bind conclusions to row numbers that sorting can change.

Every claim/displayed cell records the source artifact SHA-256, exact row selector,
column/metric, source/display scale and operation. Preserve numerical ratios,
blank/null meanings and original selected CSV strings. Figures record saved table
sources and renderer identity. Reconcile these bindings before sealing.

## Lightweight Narada reports at every stage

Use the existing [Narada source contract](../../apps/narada/contracts/report.schema.json)
with schemaVersion 1.1. The page reads selected saved content; it imports no research
modules, computes no statistics and discovers no private artifacts.

Each stage page should follow this reading order:

1. The question, supported findings and main qualifications.
2. Scope card: product/candle interval, five-minute cloud, touch/gateway, horizon,
   dates, accepted/completed counts and reference-price convention.
3. Compact primary scorecard and saved MAE/MFE distribution/horizon figures.
4. Stage-specific comparison or search evidence, with coverage and uncertainty.
5. Stability, missingness, definitions, selection method and study limitations.
6. Selected downloads and saved-artifact provenance references.

The existing contract supports plain text, metrics, tables and raster figures,
not a browser-side optimizer or arbitrary HTML. Select views that explain the
results without adding bespoke app analysis. Target approximately 12–18 sections
per stage, small scorecards and four to six compressed figures.

Respect the current limits: 30 sections; source JSON 96 KiB; public JSON bundle
128 KiB; table 100 rows/12 columns; PNG/JPEG/WebP 2 MiB each/8 MiB total; at most
four selected CSVs, each 1,000 rows/24 columns/256 KiB and 512 KiB combined.
The full grid and private event ledgers remain outside the website. Suggested
downloads are scorecard, quantiles, stability, and Stage 2 contrasts or Stage 3
frozen selections. Do not export every numerical file by default.

Prepare publication.json, selected figures/downloads and private source checks
BEFORE sealing each analytical run. Later layout-only revisions use a separate
reports/exports/<study>/<run>/<revision>/ directory; changed numbers, methods or
interpretation require a new analytical run. Use new immutable publication IDs
for every stage/revision and a stable proposed study slug
ema-cloud-trend-follow-opportunity. Author featured/related selections explicitly.

Report readiness is the stage deliverable. Later authorized publication runs the
publisher dry-run, selected local staging and authored catalog update, then
Narada verify/test/lint/build, static smoke and desktop/mobile/keyboard/download
inspection. Hosted release/deployment has its own scope. Planning creates neither
a public bundle nor a hosted page.

## Handoffs for the later scoped prompts

| Prompt | Must authorize and specify | Deliverable boundary |
| --- | --- | --- |
| Stage 1 | Defaults/revisions, Bhishma request and new delivery, consumed-input audit, slow engine/tests, development outcomes, report preparation and sealing | Six-cell fixed-width slow-touch evidence; no fast search or reserved outcomes |
| Stage 2 | Stage 1 run pins, independent fast stream, unchanged slow parity, membership/pairing contrasts, new report/seal | Comparative fast/slow development evidence; no gateway tuning |
| Stage 3 | Frozen grid/objective/constraints, fold/split reservation, selected candidates and permitted joint-horizon objective, validation/final/recent evaluation, report/seal | Complete search record and frozen out-of-period comparisons |
| Publication | Exact approved report IDs/assets, local staging/catalog and preview; hosted release if explicitly included | Selected webpage delivery with preserved source provenance |

The next requested prompt can therefore be strictly Stage 1: approve the data
and signal definitions, implement and test only the slow branch, compute only
its allowed outcomes, and deliver its complete publishable report evidence.
Stages 2 and 3 remain planned until their own scope is commissioned.
