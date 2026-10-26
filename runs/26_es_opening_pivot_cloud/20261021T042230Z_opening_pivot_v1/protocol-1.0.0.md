# Frozen protocol 1.0.0

This protocol incorporates the complete [user request](sources/user-request.txt).
Any discrepancy is resolved by the explicit implementation decisions below.
The freeze receipt pins these bytes, settings, input lock and executable source
before any actual strategy outcomes are calculated. Synthetic QA and descriptive
input/feature audits precede that receipt. No tuning uses 2025 or 2026 outcomes.

## Inputs and eligibility

Consume the five independent annual Verne releases (2022 v6, 2023 v5, 2024 v4,
2025 v3, 2026 v2), pinned same-contract EMA cloud v1.1.0 ES 5m and unadjusted
volume-lead ES 1m. Bhishma supported loaders and configured publication root
resolve them; verify consumed manifest and selected file hashes. Preserve source
row IDs, trigger descriptions, target ordinals, quoted contracts and null
available_at. Duplicate dates are skipped entirely. No pivot substitution or
level translation is permitted. Triggers alone form one outer-bound pivot zone;
coincident bounds are a price. Targets never become pivots.

The requested starting date is January 1, 2022. The end is the latest common
complete date in pinned prices/features and annual levels. Record the actual
observed overlap and exclusions. The cash-session calendar uses the existing
published calendar rules; disclose uncertified/shortened dates separately.
Retain staged counts for weekdays, exchange cash sessions, levels, unique complete
plans, duplicate exclusions, calendar certification, contract matches, usable
opening bars, readiness and full execution data. Missing levels do not imply the
source never posted. All availability is conditional retrospective research; a
verified pre-open cohort is empty unless explicit reliable evidence exists.

Require unbroken, unique one-minute data at every minute 09:30–10:59 inclusive
and a constant matching underlying quoted contract. This fixed future data-quality
window is retrospective eligibility and must be disclosed. Missing days are not
zero no-trade outcomes. Require published valid/usable/250-bar-ready features for
09:10–09:55, including values used by lag-three filters. Preserve resets at rolls,
invalid slots and unknown gaps and overnight continuity. Independent feature
recurrence and timing audits precede outcomes; native TradingView parity remains
unestablished. No alternative readiness rule is computed.

## Causal candidate engine

All timestamps are timezone-aware America/New_York. A 09:30 bar is open-labelled,
completes at 09:35, and can first fill at 09:35. Reset state at 09:30. Seed approach
history with only the completed 09:25 bar. All qualifying touches are cash bars.
At a prospective first pivot return freeze delta = ceil_tick(max(1 point,
0.10 × previous completed bar ATR14)); tick is 0.25. The prior approach close
must be strictly earlier: short close <= pivot_lower-delta, long close >=
pivot_upper+delta. Range intersections and gap between closed intervals use
inclusive comparisons. Candidate reaction and confirmation closes use strict
comparisons. Bullish means close > open; bearish close < open; doji cannot react.

A pivot-return touch starts an episode lasting that bar plus the next two bars.
Touches of pivot and cloud can accumulate on separate bars. Each touch uses the
bar's completed cloud expanded by delta. On at least one bar touching either zone,
the unexpanded pivot/cloud interval separation must be <= delta. Short reaction
is the first bearish close < cloud_lower after both touches and separation;
long is the mirror bullish close > cloud_upper. Filters do not alter formation.
Incomplete episodes expire after three bars. Simultaneous opposite eligible
starts are rejected as ambiguous. After any terminal episode (candidate, expiry,
ambiguous start), clear approach history; a later completed bar must establish a
new approach before another episode. An episode cannot rearm on its terminal bar.
Keep all candidate/rejection records; freeze the first candidate before masks and
entries. No filtered-out or unfilled first candidate is replaced that day.

At reaction close freeze a common candidate ID and structural stop. Short stop
is max(episode high, pivot upper)+1 point; long is min(episode low,pivot lower)-1.
Round stops outward to a tradable ES tick (up for shorts, down for longs).
Record body/wick/range characteristics without adding filters. A and B/C/D masks
are respectively off, ordering, slope, both. Ordering is strict EMA20>EMA50 long
and < short. Slope requires each EMA strictly above/below its value three
completed bars earlier. Evaluate once at the common reaction close for both
entry policies, with no entry-time recheck. Cloud interaction always remains.

## Entry and execution

Early enters next 5m open after reaction. Confirmed enters next 5m open after a
completed close strictly beyond both pivot and cloud in direction. Reaction-bar
confirmation is allowed; record coincident fills. Otherwise consider next three
completed bars, expiring at stop touch, cutoff or expiry. Minute stop touches
at/after reaction close before entry cancel the unfilled candidate. Reject raw
opening price at/beyond stop; also reject nonpositive actual slipped-entry risk.
No eligible fill is before 09:30 or at/after 10:00; earliest is 09:35.

One ES contract, one trade per variant per day, no scaling/pyramiding/trailing or
breakeven. Primary target is exactly 2R using actual slipped entry and frozen
structural stop. Secondary target is nearest strictly profitable near edge among
original first two targets in the direction, using actual entry; preserve ordinal,
description and price. No available target => undefined policy, no 2R fallback.
Compare target policies on common defined daily and both-filled populations;
show unavailable counts and coverage separately.

Use one-minute OHLC from entry, excluding earlier target touches. Opening gaps
have known temporal priority: stop gap exits at worse open; a known target
trade-through at open fills at target before later minute extremes. For unresolved
same-minute stop/target touches use stop first and retain optimistic target bound.
Target limits require one tick beyond target, fills at target without slippage.
Market entry, stop and time exit incur one tick adverse slippage each execution;
fees are $5 total round trip, an assumption. ES point=$50, tick=$12.50. Stops gap
at worse of structural level/open then apply adverse slippage. Flatten at 11:00
using 10:59 minute close plus adverse slippage. Never double count costs. Net R
uses actual fill-to-frozen-stop risk (points×$50), including all fees and slip in
net dollars. MAE/MFE are minute OHLC envelopes through the exit minute. Intraminute exits are stamped at minute completion (known gap exits at open), so holding time has one-minute resolution; do not
claim ordered post-exit extremes are attainable excursions.

## Comparisons and uncertainty

The full baseline is 2 entries × 4 masks × 2 exits =16 variants. Primary estimate
is early minus confirmed dollars per input-eligible session, reported pooled and
separately in development, validation and temporal test, including genuine zeros.
A missing primary outcome makes the full-denominator estimate undefined. Save
both-filled paired contrasts and early-only/confirmed-only/neither counts, explaining
selection. Provide every requested trade, risk, holding, excursion, ambiguity,
equity/drawdown and distribution measure with null undefined denominators.

Use fixed seed 26021, 4000 day-clustered bootstrap samples, percentile 95% intervals,
and ISO-week cluster sensitivity. Fixed bins and bounded one-way and two-way cuts
are declared in [reporting decisions](reporting-decisions.md); no test-derived
thresholds or unrestricted cross-products. Cells below 30 trades are weak
descriptive evidence. Secondary comparisons to the primary early/off/2R variant
form one 15-comparison Holm family of descriptive bootstrap sign-tail probabilities,
not randomization p-values. Primary inference, secondary comparisons and exploratory
cuts remain distinct. No best-cut strategy recommendation is justified.

One-factor sensitivities on the primary pair only: slippage2 and4 ticks;
stop buffer0.5 and1.5 points; proximity multiplier0.05 and0.15. Everything else
is baseline; do not cross parameters. Re-form candidates only for the changed
stop/proximity setting (stop buffer leaves event formation unchanged). Preserve
all baseline eligibility and readiness. Source availability remains unverified.
The inspiration date 2026-09-15 has no date-specific exclusion and is tagged, per user clarification; regular input gates still apply;
do not add an exclusion analysis. Retain negative and inconclusive findings.

## Verification and evidence

Run focused synthetic QA for the entire event/fill/time/cost/null chain, independent
feature timing/values and an independent saved-ledger numerical reconstruction.
Save coverage, candidate/episode/rejection, daily, trade, feature/level lineage,
variant, sensitivity, metrics, cuts and paired evidence. Select chart examples by
earliest date then ID within win/loss/failed confirmation/stop invalidation; report
missing example categories explicitly. Retain exact commands, timestamps, source
snapshots, dirty Git state, environment lock/runtime versions, seeds and artifact
hashes. Verify saved publication cells and hashes before sealing. Run workspace,
metadata/navigation and Narada verify/test/lint/build/local smoke and browser QA.
Source integrity, scientific verification and UI validation are separate receipts.
No hosted deployment is authorized.
