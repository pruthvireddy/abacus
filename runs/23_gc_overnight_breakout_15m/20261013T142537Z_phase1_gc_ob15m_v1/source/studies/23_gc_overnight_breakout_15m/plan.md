# GC- Overnight Breakout 15M

Study `23_gc_overnight_breakout_15m` · Phase 1 approved October 13, 2026 · Phase 2 proposals retained · Plan version `0.1.1`.

## Research questions

First measure the supplied overnight breakout idea from entry to exit: profits,
losses, risk, holding time, and the path taken while the trade was open. Then
test whether waiting for a pullback gives a better entry, including at the
overnight midpoint, and whether a second entry adds value within a fixed risk
budget. Report how often these opportunities occur and how often they succeed.

Eventually publish the verified results as a navigable study on the existing
Narada site hosted on Vercel. Keep **GC- Overnight Breakout 15M** as one study
navigation entry, with smaller condition tabs inside it and visual explanations
of the backtest. Annual performance and entry-session statistics are required
for the baseline and every evaluated condition.

“Optimal” will mean the best of a small, prespecified family that survives
chronological evaluation. The lowest long entry or highest short entry visible
after a day ends is a hindsight benchmark, not a trading rule.

The user approved Phase 1 implementation, input preparation, baseline execution, verification, publication and production deployment on October 13, 2026. The dedicated Phase 1 protocol and settings govern this execution. The alternative-entry, pullback, additional-trade and filter sections below remain Phase 2 proposals and are unexecuted. Publication of annual baseline outcomes creates prior exposure: these years cannot later be described as untouched Phase 2 holdouts.

## Script rules and the baseline

The full [source specification](source-rules.md) documents actual code behavior
and its differences from explanatory comments. Preserve both
[source files](README.md) and their [byte identities](inputs.lock.json).

| Rule | Original strategy | Indicator adaptation |
| --- | --- | --- |
| Range and clock | Broker-day high/low from 00:00 inclusive to 07:00 exclusive; fixed GMT+3 default; optional New York +7 hours follows US DST | Same defaults and clock choices |
| Breakout | Long stop at range high and short stop at range low; first fill cancels the other; one trade per broker day | Estimates the first boundary fill from an OHLC path; optional skip of a candle crossing both boundaries consumes that day |
| Timing | Calculates at candle close; newly placed orders can fill on the following candle | Estimates intrabar fills, but markers and alerts become known at confirmed candle close |
| Stop | Default 1%; initially from breakout boundary, reset from actual fill at the close of a surviving entry candle; optional opposite boundary | Models this reset; a same-candle stop occurs before the reset |
| Exit | Stop or queued market close at the next bar open around 20:00; optional equity guard | Stop or timed exit, with explicit fallback for missing evening bars/new broker day; no account guard |
| Sizing and costs | 1% equity risk, 10x leverage cap, quantity-step rounding; $10,000 initial capital, 0.4 cash commission/order, zero slippage, no spread by default | No sizing, costs, margin, compounding, or floating equity model |
| Statistics | Native closed-trade getters plus custom money/R statistics and estimated equity drawdown | Estimated closed-trade R statistics plus a separate next-10-bar study from signal close |
| Midpoint | No midpoint entry rule | Dotted midpoint is visual only; no midpoint entry rule |

Both skip the first loaded broker day, but neither proves every expected range
bar exists. The strategy only disables trading for invalid hour ordering; the
indicator also disables unsuitable charts/timeframes. The indicator uses a
declared OHLC ordering and low-first equal-distance tie. That does not establish
native strategy parity. Missing-bar handling, same-bar fills/stops, guard/stop
competition, breakeven streaks, and R denominators need explicit reconciliation.

Use three clearly labeled views. **Source reproduction** preserves each script's
defaults and limitations. **GC execution baseline** uses exactly 15-minute
regular bars, validated input coverage, executable quantities, and stated costs.
**Signal-close path study** reproduces the indicator's H=10 statistics; its
reference price is the signal close, not the earlier breakout fill. These views
must not share a generic “win rate” or interchangeable profit claim.

Proposed main comparison: fixed GMT+3, 00:00–07:00 range, 07:00–20:00 entry
window, 1% stop, no target, and evening exit. New York +7 hours and the opposite
range stop are prespecified sensitivities, not settings chosen for the best
observed return. A future New York overnight window would be a distinct variant.
Store actual UTC fill time, broker date, New York time, and decision availability.

## Inputs and evaluation periods

Use GC futures, not a substitute spot-gold/CFD series. Prefer pinned unadjusted
same-contract one-minute bars or finer evidence for execution, with independently
checked 15-minute aggregation. Pin dataset ID/version, manifests, selected file
hashes, timestamp semantics, calendar, contract multiplier/tick/quantity rules,
and roll mapping before outcomes. Request reusable inputs from Bhishma if absent;
do not rebuild an existing release or silently borrow another study's lock.

Resolve storage through workspace path configuration. A range must stay in one
contract; a roll during range/trade observation creates an exclusion or censored
outcome. Never calculate P&L across an adjusted roll jump. Distinguish scheduled
market closures from missing expected bars. Define DST transitions, holidays,
early closes, partial broker days, duplicate bars, and stale quotes in preflight.
Eligibility must use information available at the decision; later missing exits
produce censored outcomes and cannot remove an earlier accepted signal.

Proposed split, subject to quality-qualified coverage: 2018–2020 development,
2021–2023 validation, 2024–2025 final evaluation, and qualified complete broker
days in 2026 as a separate recent replication. Record partial-year coverage and
prior GC inspection by other Abacus research. Do not call these dates pristine
holdout. Change unavailable dates and freeze their replacements before viewing
outcomes. Later periods remain unopened for this study until rules are frozen.
Assign episodes to breakout decision date; purge or censor observations whose
trade or horizon crosses an evaluation boundary so information cannot leak
between selection and evaluation periods.

For GC dollar results, freeze a numeric per-contract, per-side commission/fee
schedule and executable tick slippage assumptions before scoring. Keep zero-cost
and original 0.4/order reproduction separately labeled. Report zero, one, and
two adverse ticks per fill as sensitivities; the primary fee/slippage choice is
pending input and execution review. Do not infer GC net profitability from the
source's broker sizing defaults.

## Baseline performance and path statistics

Retain a day/range roster, signal ledger, order/fill ledger, and trade ledger so
every exclusion and denominator can be traced. Report counts of eligible days,
valid ranges, breakouts, executable fills, skipped quantities, completed trades,
open/censored trades, dual-boundary bars, gap fills, and exit reasons.

Report points, dollars per one GC contract, and R as distinct units. Use
direction-adjusted exit minus fill for gross movement; subtract explicit costs
for net P&L. Baseline metrics include win/loss/breakeven counts, net win rate,
mean/median trade, payoff, profit factor, expectancy, net P&L, cumulative closed
P&L drawdown, losing streak, holding time, and stop versus timed exits. Account
sizing/compounding is a separate reproduction view and uses actual quantity
steps; a below-minimum order is skipped rather than fractionalized.

Measure maximum favorable/adverse excursion only after fill and before exit.
Retain initial boundary stop, effective post-entry stop, their activation times,
and both risk amounts. For comparable study R, freeze its denominator at fill
using the initial effective stop, disclose later reset, and retain a separate
source-style R column. Never silently substitute source R for study R.

Reproduce the indicator's horizon study independently: signal-close reference,
next 10 observed chart bars, signal candle excluded, signed H-bar close,
MFE/MAE, favorable close >0, and MFE>MAE with ties separate. These observations
continue after trade exit; pending horizons are excluded from completed averages.
For source parity, the MFE>MAE flag uses the indicator's tolerance:
MFE−MAE must exceed `1e-10 × max(1, MFE, MAE)`; near ties do not count.
Calendar tables use the source's bar-opening grouping even though the price
reference is close. Main study tables group by actual decision/fill availability;
store both anchors. No observations means undefined, not zero probability.

## Annual performance and entry sessions

For the baseline and every entry/condition policy, report overall performance,
each calendar year, each entry session, and **year × entry session**, with
long/short breakdowns. Annual rows include covered dates, eligible breakout days,
signals, fills, wins/losses/breakevens, win rate, net points/dollars/R, expectancy,
profit factor, MFE/MAE, holding time, and drawdown. Show partial years, no-fill
days, exclusions, and unknown outcomes. Calculate yearly drawdown from that
year's closed P&L path and label it separately from full-history drawdown.

Use America/New_York civil time with DST for reporting. Proposed session windows
follow existing Abacus reporting conventions; they are analytical windows rather
than an assertion about official GC exchange sessions. Review them before freezing:

| Entry session | New York time | Boundary rule |
| --- | --- | --- |
| Asia | 20:00 to 02:00 next day | Start included, end excluded |
| London | 02:00 to 09:00 | Start included, end excluded |
| New York | 09:30 to 16:00 | Start included, end excluded |
| Outside named sessions | All other times, including 09:00–09:30 | Retained explicitly |

Assign a trade's year, weekday, hour, and session by **actual entry fill time**,
not exit time or the earlier breakout marker. For a later reclaim entry, retain
both its own entry session and the original breakout session. Include counts
and shares of entries by session and New York hour, timing since trading start,
and a breakout-session → alternative-entry-session table. No fill means no
invented entry session. Signals/opportunities use their own available-at/event
anchor; H10 source reproduction retains its documented signal-bar-opening anchor.

For paired policy comparisons, use the original breakout's New York entry year
and session as the common cohort anchor, so both policies compare the same days.
Label these separately from each policy's own entry-session performance. Entire
trade P&L belongs to its entry cohort even if exit crosses a year/session boundary;
do not truncate the trade at a reporting boundary. The separate evaluation-split
purge/censor rule still applies. Asia entries after midnight use their actual
calendar date/year; no automatic next-session date reassignment.

Every session/year probability retains its numerator, denominator, distinct
days, and unknown count. Show the full entry distribution alongside conditional
performance; sparse or absent session entries remain visible. Named sessions
partition observed entries with the outside bucket; they do not filter trade
eligibility. Week/month displays remain descriptive, and subgroup findings are
exploratory unless separately frozen.

## Pullbacks and their success rates

Anchor one episode to the first accepted daily breakout and its direction.
Freeze range high H, low L, width W=H−L, and midpoint M=(H+L)/2 before breakout.
Track returns after the breakout to the broken boundary, 25%, 50%, and 75%
inside the range. For long episodes the levels are H−qW; for shorts L+qW,
where q is 0, 0.25, 0.50, or 0.75. This is symmetric across directions.

For each level, record first post-breakout touch, first close reaching the level,
later outward reclaim, time to each event, deepest penetration, and excursions
after that event. The daily opportunity rate uses all accepted breakouts as its
denominator, showing known opportunities and unknown eligibility separately.
Report known successes / known outcomes alongside the full breakout/opportunity
roster and unknown counts. Bound full-roster rates by treating unknown outcomes
as none versus all successful; never silently classify them as failures.
Repeated contacts describe the same episode and are not independent samples.

Distinguish three meanings of success:

1. **Tradable success:** a filled alternative trade has positive net P&L at its
   declared stop/timed exit; breakeven is separate.
2. **Range recovery:** after an interior-level opportunity, price reaches the
   original broken boundary before the opposite boundary or evening cutoff.
   If both barriers occur in unresolved order, the result is unknown.
3. **Excursion opportunity:** favorable movement reaches 1R before adverse
   movement reaches 1R. This is a path statistic, not an implemented target.

The report will show successes as counts and percentages with their exact
denominators. A return to the breakout level need not imply a profitable trade
held to evening, and a frequent opportunity need not have positive expectancy.

## Fixed alternative entry family

The primary family contains four **replacement policies**, one for each q.
They wait for a confirmed return/reclaim instead of taking the original fill.
The first breakout direction becomes available at its candle close b. Only
later completed candles can arm these rules; no hindsight fill on candle b.

For q>0, arm after the first candle j>b closes at or farther inward than its
level. For q=0, require a close strictly inside the broken boundary. After arming,
wait for a later candle k>j to close strictly outward of that level: above it
for a long, below it for a short. Submit a market order at k close only when
the next scheduled opening lies inside the original broker day and entry window.
Fill at that next opening price; the fill is not assumed to equal the level.
If its expected price is missing, retain the submitted order with unknown fill
or outcome rather than recording an unfilled zero. Keep any next-observed-open
simulation as a source-style sensitivity. Retain the first qualifying reclaim
only; no repeated optimization within a day, and no new orders at cutoff.

Each policy uses the same primary percentage-stop convention and evening exit
as the baseline, no profit target, and at most one trade per episode. It may
enter after the baseline would have exited: record that timing explicitly.
For a reclaim market entry, anchor the initial percentage stop to its signal
close; for a resting limit, anchor it to the limit price. Reset from actual fill
only at the close of a surviving entry candle, as in the source. These entry
references differ from the baseline's broken boundary and must be recorded.
An opposite-boundary touch does not cancel the waiting percentage-stop policy;
record it as context and as failure of the separate recovery statistic. Opposite-
boundary stops are a fixed sensitivity. Reject nonpositive or below-minimum
planned risk before order submission. Once an order is submitted, retain its
actual gap fill and resulting protective exit even when fill is beyond the
planned stop; R may be undefined, but dollar P&L and costs remain. Do not skip
an executed trade retrospectively or invent a zero-risk opposite-boundary entry.

For a separate exploratory comparison, place a buy/sell limit at q=0.25, 0.50,
or 0.75 after candle b closes, active from the next candle until cutoff. If the
level was already reached before submission, label it missed before arming
and skip using that known history; do not backdate a fill. An order already
resting may fill at a favorable opening gap, including a gap through its stop;
retain that fill and exit rather than skipping after observing the opening price.
Require one tick of trade-through for intrabar resting fills, disclose gaps,
and retain touch-only sensitivity. Limit entries and confirmed reclaims answer
different execution questions and cannot be pooled.

Primary policy comparison uses paired **net P&L per baseline breakout day**:
alternative minus original. An unfilled replacement contributes zero P&L and
still appears in the day denominator. Also report conditional P&L per fill,
coverage, missed profitable breakouts, avoided losing breakouts, entry improvement
in points, risk, holding time, and drawdown. Do not rank policies on filled-only
win rate or best entry price. Never replace censored P&L with zero.

The computable primary mean uses the common complete-day mask for the baseline
and four policies. Report that denominator, the total accepted-breakout roster,
missing-pair rate, and each policy's separately observed-pair sensitivity.
Keep censored episodes in the ledgers; the complete-day estimate cannot be
presented as the return of all breakout days when outcomes are unknown.

An optional hindsight reference reports the best post-breakout price seen before
cutoff on complete episodes. Label it unattainable without future knowledge,
exclude it from policy rankings, and never use it to choose a rule or stop.

## Protected overnight boundary breaks and recovery trades

Phase 2 planning amendment, October 13, 2026. The user defined **protected low**
as the frozen overnight range low L after the first accepted upper breakout H.
It is not a swing low, a guaranteed support level, or necessarily the baseline's
active stop. Mirror lower-first episodes using the protected overnight high H.
Keep upper-first/protected-low results prominent and the mirror distinctly labeled.
The frozen Phase 1 protocol and baseline evidence are unaffected by this proposal.

### Occurrence and session horizons

Use the original accepted breakout episode and frozen H/L/M. Follow the opposite
boundary from the original fill through the broker trading cutoff even if the
baseline exits earlier. Keep first-side order explicit; a low broken before the
upper breakout is not a post-upper protected-low break. Same-bar visits need
ordered finer evidence; unresolved ordering stays unknown rather than choosing
the most favorable sequence.

For upper-first episodes record these distinct events, with symmetric high-side
thresholds for lower-first episodes:

| Event | Upper-first protected-low definition |
| --- | --- |
| Touch | Subsequent price reaches L or below |
| One-tick breach | Subsequent price trades at or below L minus one instrument tick |
| Close-confirmed break | A completed 15-minute candle closes strictly below L |
| Reclaim | Following a breach, a later completed candle closes strictly above L |

Report occurrence over two separate windows: the remainder of the original New
York session instance up to its end or broker cutoff, whichever comes first;
and the entire remaining broker trading window up to cutoff. Asia is one
cross-midnight session instance. For outside-session entries, use the connected
outside interval ending at the next named session or cutoff. Do not merge two
different instances of the same named session.

Show all original upper-first episodes, known event counts, complete-observation
denominators, unknown counts, and full-roster probability bounds. A fully observed
window without a break is false; incomplete unresolved exposure is unknown.
An observed break remains known even if a later gap censors recovery. Record
first event time where known, first confirmation availability, repeat contacts,
time at risk, and time-to-event distributions; later breakouts have less time
available and cannot be compared as though exposure were equal.

Group occurrence by the original breakout's New York year/session, and record
each boundary event's actual year/session separately. Include breakout-session
to breach-session and breach-session to recovery-entry-session transitions.
The full-window probability answers whether the low eventually broke; the
same-session probability answers whether it broke before that session ended.

### Three fixed protected-boundary trade policies

Test these as a separate exploratory family of one-contract **replacement**
policies: they observe the original breakout but do not initially take it.
The original direction becomes available at breakout candle b close. Trade
signals below use later candles j>b; events before availability remain descriptive
evidence and cannot produce a backdated trade. Keep the first qualifying setup
per policy/episode, next-opening execution, original day/window, and cutoff.

| Policy | Upper-first rule | Lower-first mirror |
| --- | --- | --- |
| Protected-boundary touch and hold | First later candle touches L, closes >L, and no one-tick breach has occurred since the original breakout through that close; buy next open | Touch H, close <H, no prior upward breach; sell next open |
| Failed boundary break and reclaim | First qualifying later candle j breaches below L by one tick; arm at j close; a separate later candle k>j closes >L; buy next open | Breach above H, later close <H; sell next open |
| Confirmed opposite-boundary reversal | First later candle closes <L; sell next open | First later candle closes >H; buy next open |

For the reclaim policy, distinguish any earlier breach before arming from its
first post-availability qualifying breach. Do not replace it with the best of
several later sweeps. For all three policies use a 1% initial stop from the
signal close, the inherited surviving-entry-candle fill reset, and the baseline's
evening exit, costs and execution model. Preserve gap fills and missing-price
uncertainty. No new take-profit or structural-stop optimization is introduced.

### Price recovery and financial recovery

After a protected-low breach, record whether and when price returns to L, M,
and H before cutoff; mirror H, M, and L after a protected-high breach. Distinguish
touches from confirmed reclaim closes and preserve ordering uncertainty. These
are path diagnostics, not assumed profit targets. A level reached before a
policy fills is not an executed-trade target success.

Separately report positive net trade P&L at the actual stop/timed exit. **Financial
loss recovery** means a genuinely executed later leg offsets a loss already
realized on the original leg, including both legs' costs; show full recovery
(combined net P&L >=0), partial recovery, and further loss. Never decide to trade
because the original position is known to lose later.

Actual second-leg comparisons use the existing fixed 1% daily risk budget with
50/50 allocation, executable whole-GC quantities, and no risk replenishment or
third attempt. Distinguish an add-on while the original is open from a re-entry
after exit. A protected-boundary reversal is not automatically an executable
close-and-reverse or hedge. In the genuine post-exit recovery model require the
original to be flat and its loss known at signal time; skip an ineligible first
signal rather than retroactively closing the baseline or inventing a later try.
Freeze any separate concurrent-exposure model before outcomes and label it.

### Comparison and required reporting

For each protected-boundary policy show its opportunity/fill/success funnel,
gross/net points/dollars/R, expectancy, profit factor, MFE/MAE, holding time,
drawdown, missed winners, and net improvement versus the original baseline.
Use all original upper-first episodes for policy coverage and paired day P&L,
with true no-fills zero and unknown outcomes null. Conditional low-touch/breach
subsets are separate retrospective descriptions, not filters of the earlier
breakout. Mirror results and combined totals remain clearly labeled.

Provide overall, annual, original-session, event-session, actual-entry-session,
year-by-session, and direction breakdowns with counts, uncertainty and partial
coverage. Retain the existing four-candidate primary comparison family unchanged.
Keep the three protected-boundary contrasts exploratory with their own common
complete-day mask, resampling, and declared multiplicity scope; use 98.333333%
Bonferroni marginal intervals for the three upper-first contrasts if simultaneous
inference is presented. Mirrored/subgroup findings do not silently add chances
to pass that family. Select on development/validation only, and disclose prior
baseline exposure before assessing later dates.

## Additional trades and causal filters

Additional entries require a separate comparison because they change exposure.
After selecting at most one reclaim rule on development/validation, compare a
fixed daily risk budget: original breakout only, chosen replacement only, and
50% budget on original plus 50% on one later qualifying reclaim. Propose a
budget of 1% of start-of-day equity; the starting equity and leverage limits
must be frozen before evaluating this account comparison. No pyramiding
beyond that allocation and no third attempt. A stopped first leg does not
restore spent risk. Account for both commissions, concurrent exposure, gaps,
rounding, combined daily P&L, and drawdown; aggregate by episode/day, not leg.
Separate second legs while the original is open from re-entries after its exit.
If GC quantity steps make a half-budget leg infeasible, skip and report it;
unit-R diagnostics remain distinct from executable sizing.

A later pullback cannot be used to filter an earlier breakout: it was not known
then. Waiting for a midpoint/reclaim is an entry policy. Any filter at the
original breakout must use earlier information. Proposed descriptive contexts
are range width scaled by the preceding 20 completed valid broker-day median
and elapsed time since trading start, both causal. Log their availability and
warmup. Define any cutoffs on development only, with a separate protocol amendment
before validation; this draft does not authorize a wide filter search.

State whether a candidate should be retained as a waiting policy, an additional
trade, a causal filter requiring another study, or an inconclusive/negative idea.
Evidence that some eventual winners first retraced is insufficient to filter
the original entries.

## Selection, uncertainty, and execution ambiguity

Show all four primary policies, including failures. Use chronological development
and validation to choose at most one rule by mean paired net P&L/day under the
frozen primary costs. A rule must have positive validation difference and enough
support; propose at least 100 completed fills across at least two validation
years. If none qualifies, retain the baseline and report no selected alternative.
Ties prefer the shallower level; do not add thresholds to improve a tie.

Estimate intervals by resampling four-week blocks of the full eligible broker-day
roster, preserving aligned policy outcomes, unfilled zero days, and within-day
dependence. Use 10,000 replications with frozen seed 230015; one/eight-week blocks
are sensitivities. Report pointwise 95% and Bonferroni 98.75% intervals for the four
primary alternative-minus-baseline comparisons using the same complete-day mask,
preserving censor flags
in sampled blocks. Nonbreakout days preserve calendar spacing but do not enter
the breakout-day metric denominator. Report missingness and mask sensitivity.
Additional-entry and limit-fill
families are separate exploratory results, not extra chances to pass the primary
test. Freeze their selected rule before opening final outcomes.

Final evaluation asks whether the frozen selected policy has positive net
expectancy and a positive paired improvement whose 95% interval excludes zero,
with at least 100 completed fills across both final years. Show annual consistency,
coverage, costs, and risk tradeoffs even when those criteria pass. Failure, sparse
support, or sensitivity to fills leads to a negative or inconclusive decision;
do not tune on final dates. Treat recent partial 2026 as replication only.

Use ordered finer bars when available, while retaining signal-candle availability.
One-minute OHLC can still leave ordering unknown. Without adequate ordering,
report adverse-first and favorable-first bounds for competing entries/stops,
source OHLC approximation, and ambiguity counts. Never assume an intrabar signal
close was available earlier. Missing prices preserve unknown/censored events;
known market closures do not create fabricated bars. A conclusion must disclose
whether it survives cost and ordering sensitivities.

## Web publication and condition navigation

The future destination is the existing Narada/Vercel site, using one stable
study title **GC- Overnight Breakout 15M** and a proposed study path
`/studies/gc-overnight-breakout-15m/`. Keep the study visible in library navigation
and keep its title and route stable as new conditions are added. Inside it,
smaller tabs should lead to explicitly saved results, with a clear current tab,
links that can be bookmarked, and a way back to the study overview.

| Proposed study tab | Reader question |
| --- | --- |
| Overview | What was tested, what does the evidence support, and how do the conditions compare? |
| Breakout baseline | What happens from the original breakout fill to exit? |
| Pullback opportunities | How often does price return to each range level, and then recover? |
| Boundary reclaim | Does waiting for a boundary return and reclaim improve results? |
| 25% reclaim | What changes after a shallow return inside the range? |
| Midpoint reclaim | What changes after a return to the midpoint? |
| 75% reclaim | What changes after a deeper return inside the range? |
| Protected boundary | After the upper side breaks, how often does the overnight low break, and do touch/hold, failed-break recovery or reversal trades help? |
| Additional entries and filters | Does a second allocation or a causal condition add value? |
| Validation and methods | How do costs, clocks, stops, missing data, and evaluation periods affect the findings? |

The tab list is a proposed reading order, not computed evidence. Add future
conditions within this study rather than creating unrelated study navigation
entries. Keep tested negatives and inconclusive conditions accessible. When tabs
become crowded, use clear grouping and a compact selector on small screens.
Each condition must show what changed from baseline and its exact saved run.

The protected-boundary view needs separate **Occurrence**, **Recovery and
reversal trades**, **Year-wise**, and **Entry sessions** tabs or equally explicit
sub-navigation. Preserve the baseline, midpoint and other condition views, and
review the generic navigation bounds before adding further groups.

Use a consistent reading sequence: an illustrated rule and entry/exit timeline;
tested settings, dates and costs; summary performance and exact success counts;
year/session/side tables; paired baseline comparison, coverage and missed trades;
then limitations and the decision. Let readers select **Year, Entry session,
and Side** from saved rows, with overall and year-by-session views available.
Changing a display selection must preserve the reported population and denominator.
Keep trade P&L, source-style estimates, and H10 excursions distinctly labeled.

Reuse Narada's authored study catalog and saved-report tabs where supported.
Current parallel-report tabs share one source run; later runs need explicit
analysis/related-report selection, and a more flexible condition hierarchy may
require a later generic navigation extension. Do not assume unlimited nesting.
Follow the [publication contract](../../docs/narada.md) without calculating
statistics in the website or discovering arbitrary research files.

## Visual guides and chart examples

Retain the supplied [indicator screenshot](sources/indicator-chart-reference.png)
as an appearance reference, with its hash in [the source lock](inputs.lock.json).
Its visible vocabulary includes purple shaded range boxes, solid high/low
boundaries, purple dotted guides, red/green directional markers, and candles.
Use the source-defined midpoint to explain a dotted midpoint in future guides.
The screenshot has no visible symbol, dates, price scale, time axis, settings,
or legend; do not infer performance or meanings for its other red/gray lines
and “D” marker.

Plan a compact overview diagram of range formation → breakout → possible
pullback/reclaim → actual fill → stop or evening exit. Condition-specific guides
should label range high/low, midpoint/interior level, direction, confirmation
close, fill time/price, active stop and exit. Distinguish when the signal became
available from any earlier estimated intrabar fill, and distinguish an entry
triangle from an exit marker. Include long and short examples, a failed reclaim,
and a profitable breakout that a waiting policy misses.

Add a protected-low sequence guide: upper breakout → low touch → strict breach
→ reclaim or confirmed reversal → actual fill → exit. Distinguish price recovery
to L/M/H from financial recovery after costs, and show the original position's
status at each signal. Include the protected-high mirror with clear labels.

Label authored candle diagrams **illustrative**. Any empirical chart example
must trace to pinned data and an event/trade ledger, display actual dates and
timezones, and state its selection rule. Show a balanced set of successful,
failed and missed cases; illustrative examples cannot substitute for aggregate
statistics. Reuse supported schematic patterns or selected raster figures with
captions, alternative text, and labels/line styles that work without color.

In addition to rule diagrams, plan annual performance bars, yearly cumulative
P&L/drawdown, entry counts by session/hour, a year-by-session performance grid,
and pullback-opportunity frequency. Charts must identify units, costs, sample
counts and missing/partial periods, and use exactly the saved table values.
The reference screenshot stays a retained source unless explicitly selected
as a labeled public illustration during the later page-building stage.

## Planned artifacts and verification

Future runs will retain frozen protocol/settings, input locks, source and dirty
workspace snapshots, environment lock, exact commands, exclusions, ledgers,
table/figure hashes, recorded checks, and a dated decision. Stage under `work/`
and seal a unique completed run without altering prior evidence. Prepare any
optional report source before sealing; web publication needs separate scope.

Web publication is a planned deliverable. Prepare the selected report sources,
condition identities, figures, summary downloads and source-cell provenance
before sealing each future run. Later presentation-only changes use a separate
revision directory; numerical or interpretive changes require a new run.
Publish immutable report IDs and preserve earlier report links as the study grows.
Only explicitly selected report content/assets enter the public site.

Required tables: input/eligibility audit; source-version reconciliation; baseline
performance; H10 signal-close statistics; pullback funnel/recovery; alternative
policy scorecard; paired day comparisons; additional-entry budget comparisons;
year/side/time and year-by-entry-session breakdowns; entry distributions and
breakout-to-re-entry session transitions; cost/clock/stop/ordering sensitivities; uncertainty and
decisions. Required figures: cumulative net P&L and drawdown, pullback-depth
frequency, entry timing/session distributions, yearly paired policy differences,
year-by-session performance, and the explanatory chart guides above.

Protected-boundary artifacts additionally retain ordered event ledgers,
same-session/full-window exposure and breach rates, recovery-to-level outcomes,
the three trade-policy scorecards, baseline comparisons, session transitions,
and any separately executed two-leg financial-recovery evidence.

Before future execution, test synthetic long/short days, exact threshold ties,
midpoint calculations, delayed arming, same-bar stops, gap fills, stop resets,
dual-boundary ordering, breakevens, missing bars, DST, roll/closure barriers,
quantity steps, no-fill day accounting, and prevention of future-data filters.
Independently reconcile ledger P&L/R, counts, table denominators, selected paired
differences, and interval calculations. Verify source-style statistics against
native TradingView exports if available; otherwise label native parity unverified.

Protected-boundary fixtures must distinguish touch versus one-tick breach versus
closing break, pre-upper versus post-upper low visits, unknown same-bar ordering,
same-session versus later-session events, breach and later reclaim candles,
levels reached before entry, continuation versus reversal direction, and realized
loss known at decision versus an eventual loss. Verify financial recovery from
both actual legs' costs and P&L, not from a price-level recovery label.

During the later publication stage, verify exact table/figure transfers and
report-to-run attribution, then run Narada verify/test/lint/build and its static
preview checks. Review desktop/mobile navigation, keyboard access, tab links,
saved-row controls, chart legends, year/session denominators, downloads and old
report routes. Follow the existing release workflow for hosted publication and
verify the intended Vercel target and served content. These are future actions;
the current approval covers Phase 1 baseline implementation, execution, publication and deployment only. All alternative-entry outcomes remain uncomputed.

The immediate review covers the default broker clock, primary 1% stop, four
reclaim levels, secondary limits, success definitions, replacement versus second
trade scope, proposed chronological split, entry-session windows, and study/tab
navigation with visual guides. Input identities and numeric GC
costs remain explicit prerequisites for a frozen execution protocol.
