# Range XV reversal follow through and predictive lead up

Study `16_range_xv_reversal_paths`. Status: planned. Proposed protocol: 2.0.0.
This revision replaces the previous proposed plan. The current task prepares
an executable research specification and handoff; it does not extract study
outcomes. The human can authorize implementation and execution by giving the
[handoff prompt](handoff-prompt.md) to the receiving agent.

## 1 Research question and scope

Using completed OHLC bars alone, locate the first opposite-direction candle
after a directional leg. Measure how often its direction continues, how many
additional candles follow, the subsequent price path, and elapsed time. Test
whether the lead-up adds useful predictive information beyond the ordinary
reversal baseline and the information already embodied in the reversal bar.

The hypothesis that a qualifying reversal tends to continue is plausible;
it is not an assumed finding. An opposite candle already records price movement
that happened before the decision. That movement is not post-entry profit.
Report both continuation and failure, including results that contradict the
hypothesis. A high colour-continuation rate alone does not establish an edge.

Use the eight pinned FX Range XV exports, 6E/6B/6J/6S at 4/5 settings, from
[data/range_xv/fx_20170721_20261001](../../data/range_xv/fx_20170721_20261001/README.md).
The [input lock](inputs.lock.json) pins source/enhanced files, manifest/mirror,
and quality/provenance artifacts. The inventory is 2,002,278 source rows and
2,377 common inferred session dates; these are not reversal findings. Analyze
charts and reversal directions separately. Older ES/GC/NQ work supplies methods,
not pooled observations. Exclude first session 2017-07-21 and partial final
session 2026-10-01 from primary estimates, retaining audit records.

The exports have OHLC and timestamp proxies, with no volume, aggressive-buy/sell
delta, bid/ask, or verified contract-roll/adjustment history. Delta means signed
price change. Use configured paths, existing local files, and the locked workspace
environment. Preserve all inputs, historical evidence, and completed runs.

## 2 Data only workflow and chart construction

There is no requirement for ATAS, chart screenshots, screen capture, image
recognition, OCR, browser automation, laptop application control, or manual
visual candle labelling. Do not search for screenshots, install/open ATAS, or
ask the user for chart images. Classify bars directly from numeric OHLC. Doji
means exact `close == open`; its definition requires no visual investigation.
Generate local report figures from saved tables; figures are outputs, not inputs.
Validate the saved report programmatically without controlling a GUI/browser.

[ATAS's chart guide](https://help.atas.net/en/support/solutions/articles/72000602350-chart-periods-and-types)
and [Range XV explanation](https://atas.net/blog/specific-of-the-range-xv-chart/)
establish that these bars organize price movement rather than fixed elapsed
time, compress some sideways activity, and often display sustained movement
as runs. The exact construction algorithm is proprietary. The
[developer API](https://docs.atas.net/en/classATAS_1_1Indicators_1_1ExoticCandleSeriesTimeFrame.html)
identifies the setting as price ticks. These sources supply chart context,
not proof of a particular continuation probability or undisclosed reversal rule.
No external lookup is needed to execute this OHLC study.

Retain setting 4/5 as source labels. Measure actual body, high-low span, wicks,
open gaps, and duration; never impose fixed candle height or reconstruct candles.
Do not assume a reversal requires a known multiple of the setting, that each
candle takes equal time, or that every printed bar is an independent signal.
This study's reversal is a direction change in the exported Range XV bars.
It is not ATAS's separate Reversal chart or a named candlestick-pattern library.

## 3 Reversal and follow through definitions

Use Decimal or exact fixed-point prices: `direction = sign(close - open)`.
Bullish is +1, bearish -1, doji 0. No epsilon, rounding, wick pattern, minimum
body filter, or future confirmation changes the primary label.

A prior leg is a maximal uninterrupted run of adjacent completed non-doji bars
in one direction. R is the immediately following completed non-doji bar in the
opposite direction. Prior length L excludes R and includes L=1. A doji ends a
leg and cannot be R; a candle after a doji is a new leg rather than a reversal
of the pre-doji leg. Never skip physical bars or stitch across a barrier.

Use B1, B2, B3, ... for the physical bars after R, regardless of colour. F is
only the number of consecutive completed bars immediately after R having R's
direction. The first completed opposite or doji bar ends F. R is excluded.

```text
bull bull bull | R bear | bear bear bear bear | bull
    L = 3                  F = 4
```

The full new directional leg has 1+F candles. Exact F=4 needs an observed
completed breaker B5. If a boundary occurs after four confirmed followers,
F_observed=4, F_exact=null, right_censored=true. An unfinished opposite candle
cannot establish failure. Store exact L and F/lower bounds. Display L=1..10,
11-15,16+ and F=0,1,2,3,4,5,6-7,8-9,10+, plus unresolved/censored counts.

A run touching the beginning of an observed valid segment has an unknown
start. Exclude left-censored prior legs from exact-L analyses and describe them
separately. An observed completed opposite/doji predecessor establishes a known
start. Never equate an export/session/quality boundary with a known run start.

## 4 Availability quality and populations

Use enhanced timestamps as already-normalized inferred New York wall time;
do not convert them again. Next-bar start is a completion/availability proxy.
The clock, 18:00 session boundary, exact execution timing, and subsecond order
are not independently verified. Preserve original source row order.

R becomes available at B1 start. Features use R and earlier completed bars
only, and carry `available_at`. In a same-second chain, row order gives event
order but the clock cannot prove separate opportunities to act.

The primary candle-order population allows completed
`next_bar_start_proxy` and `next_bar_start_same_second` bars. The primary
price/time population requires positive-duration `next_bar_start_proxy` for
R and every measured future bar plus a same-session exit mark. Prior same-second
bars can remain if observed by the decision; disclose them and exclude in a
sensitivity. Use distinct denominators, with continuation rates also shown
on the price cohort. Include same-second price paths as a separate descriptive
sensitivity with unresolved execution timing, never invented elapsed seconds.

Repeated timestamp/OHLC flagged rows break primary valid segments; preserve
rows and do not stitch around them. Retain an include-all-original-rows
sensitivity. Zero-range bars are dojis. Invalid data, quality barriers, session
ends, and export ends have explicit reasons. A boundary-limited result is
unknown rather than false or zero. Do not cross sessions or skip a future bar
when it is unsuitable. Long same-session gaps over 3,600 seconds are retained
and flagged; omit affected legs/windows in a declared sensitivity.

For each threshold/horizon, report candidate, eligible, excluded, unresolved,
and distinct-date counts, including dates with zero events. Require the same
k-completed-physical-bar availability for successes and early failures in
complete-window probability estimates. Also classify all candidates into known
success, known failure, unresolved and give bounds
`[success/N, (success+unresolved)/N]`. Do not assume censoring is random.

## 5 Lead up features available at the reversal decision

The central feature is L. Add interpretable OHLC-derived context to test whether
three fast, efficient candles differ from three slow, overlapping candles.
Freeze an exact feature dictionary and missingness rules before outcomes.

Let s..r-1 be the prior leg, p its direction, r index R, and d R's direction.
Use actual prices and the constant quote quantum q from section 9.

| Feature group | Required quantities |
|---|---|
| Prior leg size | L; p*(close(r-1)-open(s)); sum of absolute candle bodies; max(high)-min(low); each in price and q equivalents |
| Prior leg pace | start(R)-start(s); duration per bar; bars per minute and signed net distance per minute, undefined for zero duration |
| Prior leg efficiency | abs(close(r-1)-open(s)) divided by abs(close(s)-open(s))+sum(abs(close(i)-close(i-1))) for i=s+1..r-1; undefined when denominator is zero |
| Prior leg shape | Mean/median body and span; median body/span; mean directional and counter-direction wick fractions; consecutive-bar range overlap |
| Recent context | Previous three completed leg lengths; prior 20 physical bars' median true range and close-path efficiency; prior 10/20 bars' direction-switch proportions |
| R geometry | Body, span, body/span; upper/lower wick fractions; close location in d's direction; d*(close(R)-close(r-1)); gap from previous close |
| R relative to lead up | R body/prior span; opposing close displacement divided by prior span; R span/prior-20 median true range |
| R formation and clock | R duration proxy; decision-time session window; product/setting/direction; 6S tick era |

Range overlap for adjacent prior bars is intersection length of their [low,high]
intervals divided by the smaller span; leave zero-span divisions undefined.
Directional close location is (C-Low)/span for a bullish R and (High-C)/span for
a bearish R. Wick fractions are nonnegative upper/lower wick length divided by
span. Opposing displacement relative to the prior span is
`-p*(close(R)-close(r-1))/prior_span`; it may be negative or exceed one and must
not be clipped. True range is max(H-L, abs(H-prevC), abs(L-prevC)).

Context windows end at r-1, use physical bars, require complete history in the
valid same-session segment, and are never lengthened by skipping dojis. Switch
proportions use adjacent pairs where both bars are non-doji; report that pair
count and leave zero denominators undefined. Previous-leg history ends before
the immediate lead-up; no next leg or eventual F enters a feature. Report the
feature-complete subset against all primary events instead of silently excluding
all short-history events. Compare models on identical eligible event sets.

Keep L tables primary. Secondary feature tables use discovery-period quartiles
within chart/direction, frozen and applied to later periods, with a separate
missing category. Collapse duplicate cutpoints deterministically. Do not choose
quartiles or thresholds from the full history. Use only a few prespecified
interactions: L with pace, efficiency, recent chop, and R relative size. Avoid
an exhaustive cross-product of every feature and subgroup.

## 6 Continuation and failure outcomes

Report P(F>=1/2/3/4/5/10), progression P(F>=k+1 | F>=k) for k=1..4, and the
row-normalized L-to-F matrix. All exact bins require a known breaker; 10+ can
include censored runs with at least ten followers. Censored lower bounds below
ten enter the unresolved column. Columns must partition their cohort.

On a common fully completed ten-physical-bar cohort, summarize min(F,10):
mean, median, mode, quartiles, p90, and the 10+ share. Its mean must equal the
sum of P(F>=k), k=1..10, on that same cohort. Exact uncensored F summaries and
censored lower bounds are separate. On a common three-bar cohort show
P(F>=1/2/3) together to avoid misleading changes in denominators.

Characterize failure: immediate opposite versus doji, F=1/F=2 exhaustion,
three-bar loss despite colour continuation, and favourable three-bar landing
despite an early colour break. Report the joint table of F>=3 and D3>0.
Classify quick switchbacks by observed direction only, with no visual pattern
names. Report length and duration of the new leg only when its end is observed;
no hindsight leg-end exit is proposed as a tradable rule.

## 7 Price path MAE MFE and average delta

Primary horizon is the next THREE PHYSICAL bars, regardless of colour. Include
immediate failures. Let entry E=open(B1), and exit mark X_h=open(B(h+1)), after
Bh completes by proxy. For h=3 this means B4 open, not B3 open. This is a chart
price reference, not a verified fill. Never credit R's already-completed move.

Define signed landing delta D_h=d*(X_h-E). Evaluate h=1,2,3,5,10; h=3 is
primary, with horizon-specific eligibility. Include entry, future highs/lows
B1..Bh, and X_h in excursions so opening gaps are included:

```text
long:  MFE=max(0, max(E, highs(B1..Bh), X_h)-E)
       MAE=max(0, E-min(E, lows(B1..Bh), X_h))
short: MFE=max(0, E-min(E, lows(B1..Bh), X_h))
       MAE=max(0, max(E, highs(B1..Bh), X_h)-E)
```

MAE/MFE are nonnegative. Exclude R's own range. Check
MFE>=max(D_h,0), MAE>=max(-D_h,0), and nested-horizon monotonicity on common
eligible paths. Report means/medians, D_h p10/p25/p75/p90, excursion
p50/p75/p90/p95, favourable/flat/adverse landing shares and tail losses.

Separate secondary marks are d*(close(Bh)-E), structural
`d*(close(Bh)-close(R))`, and the mean signed future candle body. Do not mix
these definitions under average delta. Supplement raw/q-unit results with
normalization by R span and prior-20 median true range, using only known
positive denominators. Mean MFE/mean MAE is descriptive, not a reward-risk
ratio for a specified executable trade. D_h/MFE is undefined when MFE=0.

Provide OHLC-only excursion attainment rates at 0.5 and 1.0 R-span, favourable
and adverse separately, within three and ten bars. These are reachability
statistics without a first-hit stop/target ordering claim. Both levels may be
hit in one candle; mark intrabar order as unknown. No trade optimizer, best-MFE
exit, or assumed stop/target sequencing is part of the study.

Add a clearly labelled break-even cost allowance: positive gross mean D_h in
q equivalents, before costs. A fixed sensitivity subtracts round-trip price
costs of 1/2/4 q equivalents from every D_h; these are assumed costs rather than
observed spreads/fees. Do not search a cost or claim executable net profitability
with unknown roll/adjustment and fill provenance. Retain prices as exported without further
adjustment; do not back-adjust, reaggregate, or repair chart prices.

## 8 Elapsed time and speed

Elapsed_h=start(B(h+1))-start(B1), with positive duration in the strict cohort.
Report mean/median/p25/p75/p90/p95, and fractions of h=3 endpoints reached
within 1/5/15/30 minutes. Three physical bars can represent very different
wall-clock durations; do not assume an equal time horizon.

For k=1..5 consecutive followers, give attainment probability together with
conditional time to the kth completed follower. The kth endpoint is B(k+1)
start; a broken run is unattained and a boundary-limited run unresolved. Do
not describe successful-only time distributions as unconditional time-to-success.
Save duration of R separately from time after its completion.

Record the first physical bar containing each positive favourable/adverse
extreme. OHLC supports a hit-time interval between that bar's start/completion
proxy, not an exact intrabar instant. Exit-open extremes have the endpoint
proxy time; zero excursions have no positive-hit time. This also applies to
excursion thresholds. No invented wall-clock price interpolation.

For secondary 5/15/30-minute clock horizons, use the last completed future-bar
close whose completion proxy is <= decision+T and in the same session. Report
actual mark time and staleness T-actual_elapsed. If no future bar completed,
leave the future-close outcome missing; if the boundary prevents observing T,
mark it censored. Summarize coverage/staleness, and a <=60-second-staleness
sensitivity. These are stale completed-bar marks, not exact prices at T and
not executable time exits. Keep them separate from primary bar horizons.

## 9 Units and historical changes

Always retain raw price-unit metrics. Constant 2026 quote-tick-equivalent
quanta are 6E=0.00005, 6B=0.0001, 6J=0.0000005, 6S=0.00005, supported by the
[CME FX guide](https://www.cmegroup.com/markets/fx/fx-product-guide).
Validate exact price grids without rounding. Constant equivalents are not a
claim about historical exchange ticks or ATAS's historical rebuild settings.

6S changed from 0.0001 to 0.00005 effective trade date 2022-05-02; see the
[CME notice](https://www.cmegroup.com/notices/clearing/2022/03/Chadv22-119.html)
and [2023 specifications](https://www.cmegroup.com/trading/fx/files/fx-product-guide-2023-us.pdf).
Mandatory 6S tables split pre/post change. Historical event-date ticks are a
separate secondary unit, never a changing-unit pooled headline. Freeze the
schedule and source references before outcomes. Off-grid observations remain
flagged; continue valid raw-price/order analysis when unit provenance limits
conversion. Never infer dollar P&L from the normalization.

## 10 Baselines and chronological prediction

The question is incremental predictive information, not whether F is more
likely than a 50 percent coin flip. Range XV construction makes that comparator
unsuitable. Never treat colour persistence as proof of order flow or causality.

First describe L-specific rates/deltas versus all-reversal rates for the same
chart/direction and identical eligibility. Report absolute percentage-point
lift, relative lift where baseline>0, and D3/MFE/MAE/time differences. Also
standardize comparisons across the prespecified decision windows and 6S eras
using common supported strata and pooled stratum weights. Show overlap,
missing support, and unstandardized estimates; do not call these causal effects.

Prediction is secondary but required by the user's lead-up question. Use:
- Development: 2017-2019, excluding the first session.
- Validation: 2020-2022.
- Later chronological evaluation: 2023-2026, excluding the partial final session.

Record prior inspection; do not claim a pristine untouched holdout. Outcome
summaries of the later block must remain unread until the final feature/model/
rule configuration is saved. Input checks can inspect schemas/quality there.
Freeze the protocol before outcomes; save a second selection lock after
validation and before later-block evaluation. Revisions after that evaluation
are new research, not improvements to the same held-out result.

Split by session dates across all instruments/settings together. Never random
split bars/events. For prediction only, purge training outcomes whose observation window overlaps
a later split and embargo the last observed session of the earlier block and
the first observed session of the next block. This does not alter the full-history
descriptive populations. Check timestamp/row availability, not just label dates.

Fit the following four model families separately by chart/direction:
1. B0: constant training-period reversal probability or target mean.
2. B1: decision window, tick era, and R geometry/formation duration.
3. M1: B1 plus prior length (log1p(L) and declared L bins).
4. M2: M1 plus prior-leg shape/pace and recent history.

M1 versus B1 tests L beyond the information in R; M2 versus M1 tests richer
lead-up information. Models use identical target-eligible event populations,
training-only imputation/scaling with missing indicators, and recorded handling
of unseen categories. B0 is computed from the same training population. Never
impute a missing outcome. Do not use raw clock timestamps, future F, later
extremes, hindsight eligibility, or full-sample transformations as predictors.

Primary prediction target is F>=3 on the common three-bar candle-order cohort;
F>=1 is supplementary. Use regularized logistic regression with L2 penalty.
Also fit ridge regression for signed D3 in q equivalents on the strict price
cohort, and min(F,10) on the complete ten-bar cohort (predictions clipped to
[0,10], with unclipped diagnostics). Restrict penalty candidates to 0.1/1/10;
choose on validation log loss for probabilities and MAE for regressions, then
refit the chosen specification on development+validation before final evaluation.
Use the same existing-library or local numerical implementation across models,
freeze penalty normalization, solver/convergence rules, and deterministic seed.
Do not add a model zoo or exhaustive interaction/threshold search.

Save event-level predictions. For binary targets report Brier score, log loss,
calibration curves/counts, discrimination, and incremental score improvements
versus B0/B1 on identical later events. Probability clipping for score evaluation
only is fixed at 1e-6. For regressions report MAE/RMSE, predicted-versus-observed
bins, and improvements over target means. Bootstrap paired score differences by
session. Calibration and stability matter alongside rank discrimination.

A maximum of three interpretable candidate conditions may be nominated using
development and validation only: one L-only, one L-plus-leg-context, and one
adding R geometry, if supported. Conditions must use declared bins/quartiles
and contain no more than three predicates. Choose candidates by validated
F>=3 lift with D3/MAE/MFE/time shown alongside, not by inspecting later outcomes.
Save predicates, selection history, and eligible populations in the selection
lock; carry every nominated candidate forward, including subsequent failures.
It is acceptable to nominate none if validation does not support a condition.

Candidate tables must show later-period frequency/coverage, events/dates,
F>=1/3, capped F, D3, MAE/MFE, elapsed time, uncertainty, and differences versus
the matching baseline. Explicitly answer whether L=2 differs from L=3 and
whether that difference survives R/context adjustment and later years. A stable
predictive association is distinct from a verified executable trading edge.

## 11 Dependence uncertainty and sensitivity

Keep chart/direction results separate; 4/5 charts share underlying trading
activity and assets share macro conditions. For comparisons use synchronized
session-date cluster resampling, 2,000 replicates, seed 161001, pointwise 95
percent intervals. Resample event sums for rates rather than averaging daily
percentages. Record undefined bootstrap replicates and support coverage.
Use paired resamples for lifts/model score differences. Do not fit/choose a new
model inside final-test bootstrap; intervals describe frozen predictions.

A five-consecutive-observed-session moving-block bootstrap checks serial
dependence. Other declared sensitivities: all original flagged rows, removal
of long-gap windows, exclusion of prior same-second bars, same-second price
paths, common-ten-bar horizon comparisons, and nonoverlapping paths. For the
latter accept the earliest eligible entry and next entry strictly after its
exit, per chart/direction/horizon. This does not create an independent-trade
claim. Pooling across charts is an optional labelled summary, never the only
headline or eight independent confirmations.

Show yearly and development/validation/later panels, long/short differences,
and decision-time half-open New York windows: Asia 18:00-03:00; London/pre-NY
03:00-09:30; NY morning 09:30-12:00; NY afternoon 12:00-16:00; transition
16:00-18:00. These windows depend on the inferred clock. Do not optimize them.

Mark cells below 100 events or 30 dates sparse. A highlighted candidate needs
at least 300 events and 100 dates in later evaluation plus displayed validation
support and uncertainty. Multiple correlated comparisons, prior inspection,
and candidate selection prevent a confirmatory familywise claim. Report all
negative/inconclusive results and any lack of improvement over B1.

## 12 Saved evidence and report

Retain an event ledger with stable chart/source-row IDs; feature values and
availability; prior leg boundaries/censoring; R geometry; F exact/lower bound;
eligibility/reasons by target; endpoint price/time; units; session/regime/split;
quality flags; and future labels kept separate from signal-time features.
Save predictions and the selection lock separately. Large evidence stays
retained with locators/schema/row counts/hashes outside ordinary Git history.

Required numerical tables and figures:
1. Input, quality, feature coverage, split leakage, and eligibility audits.
2. L-to-F counts/percentages including censoring, continuation curves and
   capped/exact run-length summaries.
3. Primary three-bar landing table by L: counts/dates, F>=1/3, D3 mean/median,
   favourable landing share, MAE/MFE tails, elapsed-time summaries and lift.
4. Secondary horizon, excursion attainment, cost assumption, time-to-follow,
   interval-to-extreme and clock-mark/staleness tables.
5. Leg shape/pace/chop/R-geometry tables with frozen development bins.
6. Model calibration, score comparisons, feature ablations, later candidate
   conditions/coverage, and yearly/window/6S-era stability.
7. Independent synthetic/source-row audits and reconciliation results.

Build offline HTML and Markdown reports from saved numerical evidence. Include
heatmaps, continuation curves, MAE/MFE distributions, time distributions, and
prediction calibration/lift plots with readable labels, counts and units.
Use tables/plots derived from OHLC to illustrate verified L=2/L=3, F=0/F=4
source-row paths; chart screenshots are unnecessary. No GUI/browser/image
capture is part of report validation. Check HTML/links/local assets, reconcile
rendered numeric source values, and parse local SVG/PNG artifacts programmatically.
Do not deploy or publish externally. Prepare any optional publication source
before sealing, following the existing artifact contract.

## 13 Execution and acceptance

The receiving agent is authorized by the copied prompt to implement, execute,
verify, report, and seal locally without routine approval pauses:
1. Read workspace/component/study guides. Verify all pinned bytes, quality files,
   clock interpretation and unit schedule. Resolve routine choices in writing.
2. Implement study-local src/tests and thin run/summarize/verify/seal commands.
   Freeze protocol 2.0.0, feature dictionary, units, splits, settings and code
   identities before outcome inspection; document actual commands in README.
3. Test both directions; L=1/2/3; F=0/1/4/10+; dojis and unfinished breakers;
   left/right censoring; sessions/midnight; repeated rows; same-second order;
   B4 indexing; gap-aware excursions; zero denominators; feature availability;
   model preprocessing/split purge; clock staleness; units/6S transition.
4. Independently recount sampled real OHLC paths from every chart/direction and
   deterministic synthetic cases, including anomaly-touching cases. Validate
   input rows, labels, feature arithmetic, price/time outputs, and denominators.
5. Run into a unique work/16_range_xv_reversal_paths/<run-id>. Develop/validate
   models/conditions in chronological order; save selection lock before reading
   later results. Produce all outcome, prediction and sensitivity evidence.
6. Verify probability monotonicity on common cohorts, capped mean identity,
   row totals/censoring, long/short symmetry, excursion endpoint bounds and
   nested-horizon monotonicity, no feature leakage, identical comparison rows,
   predictions, interval coverage, report/table agreement, assets and hashes.
7. Run focused numerical checks, python3 scripts/check-agent-docs.py and index
   freshness checks. Shared package/config changes also need check-workspace;
   no Narada/UI change or browser verification is requested.
8. Seal verified evidence under a unique runs/16_range_xv_reversal_paths/<run-id>,
   with config/input lock, code revision/dirty snapshot, environment lock, exact
   commands, exclusions, metrics/tables/reports/advice and artifact hashes.
   Update study metadata/notes and regenerate/check the research index. Preserve
   previous runs and source files; later method changes require a new run.

Completion means direct evidence-based answers to baseline follow-through,
typical additional count, L=2 versus L=3 and other lead-ups, incremental later
prediction, post-signal three-bar delta/MAE/MFE, elapsed time, failure/tail risk,
and conditions supported or contradicted by the data. No result is presumed.
