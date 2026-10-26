# Camarilla R3/S3 rejection strategy with an EMA cloud

Study `20_camarilla_ema_cloud_reversals` · Draft protocol 0.2.0 · 2026-10-08.

## Scope and question

Deliver the combined indicator, configurable chart-local rejection statistics and\na formal testing plan. The user authorizes private TradingView saving and runtime\ntesting on ES five-minute candles. The formal pinned-data strategy backtest,\ntrading orders and public publication remain outside this delivery. Source screenshots are evidence
of an author's proposed method and cloud settings, not executable instructions.

Question: after a completed rejection of previous-day Camarilla S3/L3 or R3/H3,
does a five-minute close-based EMA 20/50 condition improve net trade expectancy
relative to the identical rejection policy without that filter? The author's
daily 21 EMA policy is a separately reported comparator. Assess whether any
improvement survives a chronological holdout and realistic execution costs.

Primary scope is R3/S3. S4/R4 extreme reversals, volume filters, EMA slopes,
EMA-length optimization, delayed reclaim patterns, and alternative sessions are
separate exploratory extensions, not pooled into the primary result.

## Proposed baseline and unresolved choices

The screenshot specifies TF = 5 minutes, fast 20 and slow 50 but does not identify
the trading condition. Proposed baseline: allow longs when EMA20 > EMA50 and
shorts when EMA20 < EMA50, evaluated at the completed rejection candle's close.
Equality/undefined values permit neither direction. The user's choice replaces
this proposal before freezing the empirical protocol. Two declared alternatives
are price above/below both EMAs, and requiring both alignment and price outside
the cloud. Do not choose the best variant using the final evaluation sample.

The cloud replaces the daily 21 EMA in the proposed primary branch. Do not silently
require both. The cloud is computed through the full pinned electronic session
history, carried across sessions, with at least 250 preceding five-minute bars
for warmup. Compare this warmup with a longer seed before implementation; discard
bars with inadequate/gapped history rather than silently restart a supposedly
continuous EMA. It is not reset at the U.S. cash open.

The excerpt mentions both opposite-pivot destinations and a fixed 3R exit. Use
fixed 3R as the proposed primary management policy; measure opposite-pivot reach
as a secondary outcome, and test an opposite-pivot exit separately. It also says
enter at the next candle open but stop beyond the entry candle's extreme. That
extreme is unknown at entry. Proposed executable interpretation: stop beyond the
completed confirmation candle, with a one-tick buffer. These are declared
interpretations, not a claim to reproduce every detail of the author's method.

## 1. Pin instruments, sessions, and inputs before outcomes

The excerpt discusses MES and MNQ. Test these separately using contract-specific
micro data if available. Existing Abacus ES/NQ one-minute publications are possible
research inputs, not verified substitutes for micro fills, fees or liquidity.
Any ES/NQ proxy study must be clearly labeled and followed by a micro execution
check. Do not report mini-contract outcomes as measured micro performance.

Resolve storage through workspace path configuration and consume Bhishma's public
loaders. Select immutable dataset IDs, versions and manifest hashes, then freeze
the selection in `inputs.lock.json`. No market release is selected by this draft.
Never rebuild or overwrite an existing publication. Review timestamps, contract
mapping, holidays, missing minutes, roll boundaries and input `available_at`.

Use regular time bars, not Range XV or synthetic candlesticks. Aggregate five-minute
OHLC from pinned source bars, retaining bar start/end and completeness. Use
unadjusted contract prices for executions and P&L. Specify the price basis for
EMA/pivot calculations and do not mix adjusted levels with unadjusted prices.
Avoid carrying EMAs or pivots across an unhandled contract-price discontinuity:
either warm the selected contract on its own history or declare and test a
point-in-time roll adjustment. Final back-adjusted history is not automatically
point-in-time certified. Flag excluded roll sessions and retrospective day
eligibility explicitly.

Proposed entry window: 09:30 <= entry time < 11:30 America/New_York, following
the excerpt's discussion of the first two U.S. hours. This is a study choice,
not a source-established exclusive window. It controls entries, not forced exits.
Choose a maximum holding policy before outcomes; proposed baseline closes open
positions by 16:00 New York, without overnight holds. Cancel pending entries
outside the window. Respect DST and early-close exchange calendars.

Daily pivot parity needs a separate decision: a broker daily bar can use settlement
as close and electronic-session high/low, while an intraday-built day can use the
last trade. First compare the combined chart with TradingView's standard Camarilla
indicator under matching settings. Then freeze the exact daily session and close
convention for the backtest. If pinned inputs only support last-trade close, label
that variant rather than claim settlement-based chart parity.

## 2. Define rejection on a completed candle

Calculate established current-session levels only from the completed previous
eligible daily period: L3 = C - 0.275(H-L), H3 = C + 0.275(H-L). These levels must
be available before the candidate candle; next-period projections are excluded.

Proposed strict one-candle rejection, with zero contact tolerance:

| Direction | Approach | Contact and return | Candle confirmation | Cloud proposal |
| --- | --- | --- | --- | --- |
| Long at L3/S3 | Previous close > L3 and candle open >= L3 | Low <= L3 and close > L3 | Close > open | EMA20 > EMA50 at candle close |
| Short at H3/R3 | Previous close < H3 and candle open <= H3 | High >= H3 and close < H3 | Close < open | EMA20 < EMA50 at candle close |

These definitions operationalize a rejection; they do not assert that a discretionary
hammer/shooting-star judgment is equivalent. A candle opening beyond the level and
reclaiming it is a separate candidate, not this primary approach definition.
Skip a candle that touches both L3 and H3 because its intrabar path is unresolved.
Primary level-3 signals do not require or exclude a level-4 touch; record such
overlap and report it separately. A one-tick contact tolerance is one prespecified
sensitivity. Wick/body-ratio requirements are exploratory, not tuned silently.

Use the cloud state at the completed confirmation close. On the primary five-minute
chart, the EMAs include that candle and are known at that moment. If a later study
uses a higher cloud timeframe, use only its already completed source bar; never
historical final current-period OHLC or an unoffset `lookahead_on` value. Missing
cloud/level/history information is undefined and excluded, not counted as a failure.

## 3. Define entries, deduplication, stops and fills

Enter at the next contiguous five-minute bar's open, provided it is inside the
entry window and on the same permitted trading session/contract. Rejection is
decided before this entry. Do not recompute the decision using the next candle's
eventual EMA or extreme. A data gap or absent next bar cancels the entry.

Long stop = confirmation low minus one tick; short stop = confirmation high plus
one tick. Let E be the adverse-slippage-adjusted entry fill and S the stop price.
Risk distance is |E-S|. Skip a next open already beyond the proposed stop or giving
nonpositive risk. Primary gross target is E + 3|E-S| for longs and E - 3|E-S| for
shorts; round executable targets outward to the contract tick. Charge costs
separately and report resulting realized net R. No trailing stop or partial exit.

Primary executable policy: one position per instrument, no pyramiding. A new
contact episode begins only after a full completed candle remains strictly away
from the level on its approach side. Admit only the first eligible rejection in
that episode; lock further signals until a later fully separated candle rearms
the level. Reset episodes at a session/level change. Preserve all contacts,
rejections, filter rejections, accepted signals and position-blocked opportunities
in the event ledger. Do not treat adjacent candles at a level as independent trades.

For intrabar barriers, replay pinned one-minute or finer bars. If target and stop
remain inside the same finest available bar, mark the result ambiguous and report
stop-first/target-first bounds; do not drop it silently or impose a favorable
ordering. Stop gaps fill at the worse opening price plus adverse slippage; target
gaps fill at the target limit without favorable price improvement in the baseline.
Respect the stated order activation and position-exit timing.

Record broker/contract-specific commissions, exchange fees and adverse entry/exit
slippage before evaluating net profitability. Report several prespecified slippage
scenarios including the actual proposed live cost assumption. No zero-cost result
alone qualifies as evidence of a profitable strategy.

## 4. Compare a small declared family

Use the same base rejection events, entry timing and exit policy in each branch:

1. No EMA direction filter.
2. Source-style daily 21 EMA comparator, using the last completed daily close
   relative to its completed EMA21. This causal definition is a declared choice;
   the screenshot does not fully specify its daily timing.
3. Primary five-minute EMA20/EMA50 alignment proposal.
4. Secondary price outside both five-minute EMAs.
5. Secondary alignment plus price outside the cloud.

The user-selected cloud condition becomes the primary comparison before the
protocol is frozen. Keep others secondary and account for multiple comparisons.
Report opportunity-level comparisons on a shared event ledger and actual
one-position trade-policy results separately, because filtering can change which
later signals are available while a position is open. Report filter coverage,
not only the surviving trades' win rate. Consider a matched-distance price-level
control as a later robustness check, not a substitute for the primary comparison.

## 5. Development, validation and final holdout

Audit data availability without selecting dates based on trade outcomes. Choose a
common calendar span and pin chronological boundaries before the first backtest:
proposed oldest 60% of complete sessions for development, next 20% for validation,
latest 20% for one final holdout. Freeze exact dates, known prior inspection and
sample exclusions. Positions cannot cross a split; earlier history may warm an
EMA, but its future outcomes cannot influence a prior signal. A short or sparse
history may require a different prespecified allocation and an inconclusive result.

Use development data for debugging and choosing among already declared definitions.
Validation checks whether the frozen candidate survives different conditions;
changing it consumes that validation sample. Evaluate the final holdout once.
Optional walk-forward windows supplement rather than replace the untouched test.

Review a fixed sample of chart events for numerical and execution parity before
scoring outcomes. Include eligible and rejected contacts, both directions, a cloud
cross, session boundaries, news-related gaps and roll/holiday examples. Do not
select only attractive successful examples.

## 6. Outcomes and interpretation

Primary outcome: difference in mean realized net R per trade between the selected
cloud branch and no-filter branch on the final holdout. Also report net R per
eligible session and opportunity coverage, so a tiny selected subset cannot hide
reduced opportunity. Report by MES/MNQ or explicitly identified ES/NQ proxy and
direction separately; never pool them without showing their components.

Report trade/contact counts, exclusions and ambiguous/pending counts, win/loss/
timeout definitions, mean and median net R, profit factor, session-level drawdown,
holding time, MAE/MFE, opposite-pivot reach before stop and cloud-state coverage.
Compute uncertainty with paired trading-session blocks across branches, preserving
within-day dependence. Report uncertainty/bounds even when signs are favorable.
Do not equate level-hit rates or theoretical 3R targets with achieved profitability.

A candidate remains inconclusive if its sample is too sparse, its uncertainty
does not separate it from the baseline, ambiguity bounds reverse the conclusion,
or plausible costs eliminate its edge. A favorable result must survive the frozen
holdout and a prospective paper-trading period with actual opportunity/fill logs.
Retain negative results and every declared branch rather than display a winner only.

## 7. Implementation gates and reproducibility

Current delivery is the visual Pine indicator, not a backtesting strategy. First
complete [the Pine acceptance checklist](pine/README.md). A future implementation
can add a separate TradingView `strategy()` for chart inspection and a study-local
Python replay for full history and ambiguous-bar accounting. Both must implement
the same versioned event/management rules; a visual match is not numerical parity.

Before empirical execution, add focused checks for known pivot/EMA values,
availability and prefix invariance, exact touch/reclaim cases, warmup/gaps,
deduplication, next-open execution, tick rounding, fees, stop gaps, simultaneous
barriers, DST/early closes, roll boundaries and split leakage. Resolve input storage
through the configured roots. Stage at `work/<study-id>/<unique-run-id>/`; seal
verified evidence at a new `runs/` location with frozen settings, code revision and
dirty snapshot, environment/input/config hashes, exclusions, exact commands,
check outputs, metrics, event locators and artifact checksums. This draft is not
a completed run or permission to overwrite historical evidence. Publication or
deployment is outside the current scope.

## Source and technical references

User-supplied indicator and screenshots are pinned in [inputs.lock.json](inputs.lock.json).
The screenshots' author claims, including improved odds and liquidity claims,
are unverified. The added EMA cloud is reconstructed from the visible settings,
not extracted from unavailable cloud source code.

- [TradingView: higher-timeframe requests and avoiding repainting](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/#avoiding-repainting)
- [TradingView: fill between two plots](https://www.tradingview.com/pine-script-docs/visuals/fills/)
- [TradingView: Camarilla formulas and daily-based/session inputs](https://www.tradingview.com/support/solutions/43000521824-pivot-points-standard/)


## 2026-10-08 scope extension: exploratory indicator panel (protocol 0.2.0)

The user now authorizes configurable strategy criteria, chart-local MAE/MFE and
weekly tables, private account saving and TradingView testing on **ES futures,
standard five-minute candles**. This implements an exploratory event panel;
the formal MES/MNQ strategy backtest above remains a proposal. The panel does
not resolve intrabar stop/target ordering, simulate a 3R exit or estimate net P&L.

Freeze these initial panel choices before observing ES table values: both sides,
R3/S3, close-based EMA 20/50 alignment on five minutes, strict contact/reclaim,
previous-close/open approach condition, directional body, no tolerance/extra
wick/volume/size/penetration/distance filters, skip dual-level candles, 10-candle
shared cooldown (reset NY calendar date), contact-episode deduplication off,
09:30–11:30 NY next-open entries weekdays, 250 loaded bars of warmup, ATR 14 fixed
at confirmation, horizons 5/10/15/50/100 and weekly close horizon 15. All are
explicit settings and can be changed; input changes restart calculations.

Daily statistics use a dedicated offset previous-daily HLC request. They never
use inherited next-period projections or current-day highs/lows. Enabled stats
require Daily/Auto on a five-minute chart and daily-based values. A display-only
control plots the exact studied support/resistance for parity checks. Higher
cloud timeframes use confirmed EMAs in statistics, even if the visual developing
mode is selected. There is no added daily 21 EMA gate.

Each accepted signal queues the immediately following contiguous five-minute
open. The entry candle counts as horizon bar 1. Signal-bar highs/lows are excluded.
Keep each path independent and allow overlap. ATR is frozen on the confirmation
bar; compute each event's normalized MFE, MAE and signed terminal delta before
averaging. MAE/MFE are nonnegative magnitudes. Favorable close means signed delta
strictly > 0; MFE > MAE is also strict. Ties remain in the denominator. Interrupted
or unfinished horizons are missing outcomes, not zeroes or losses; already
completed shorter horizons remain. Counts can differ by horizon.

Each observed in-scope loaded NY week is retained, including zero-signal weeks.
Accepted counts are bucketed by signal-close week. Weekly outcomes use those same
signal cohorts, even if the selected horizon finishes in a later week. N counts
completed horizons and can be below accepted. First/last weeks may be partial.
Default paths can extend outside the entry window through contiguous chart bars;
missing bars always interrupt paths. The optional date-boundary cutoff cancels
unfinished paths at the next NY date. This is not an exchange-session close rule.

Sensitivity work must record exact criteria, symbol/contract, chart session,
settlement/back-adjustment settings and loaded-history span. A continuous ES
chart is suitable for UI acceptance; contract rolls and daily settlement make it
an exploratory input, not a pinned execution/P&L dataset. Test a small predeclared
parameter grid and retain the unfavorable cases. Lock selected choices before
untouched evaluation data or paper trading, as described in the formal plan.
