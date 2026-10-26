# Fibonacci Memory v1

A complete Pine Script v6 indicator prototype implementing the user's
[first-version protocol](plan.md). It draws confirmed Fibonacci levels and
measures hypothetical opportunities after their first eligible touches.
No market-data study or profitability result has been produced.

## Indicator and installation

Open [the complete source](pine/fibonacci_memory_v1.pine), copy it into
TradingView's Pine Editor, save it, and add it to a chart. Use a standard
OHLC chart if interpreting the paths as traded prices.

Compilation and chart execution in TradingView have **not** been verified here.
The local test adapter validates the marked numerical kernel; it does not
validate all Pine syntax, qualifier rules, chart execution, or panel layout.

Turn on **Run Deterministic Engine Self-checks** to execute the included
synthetic checks with the production helpers inside Pine. A failure raises a
named runtime error. Synthetic records never enter the chart's statistics.
This option's presence is not a claim that those tests have run in TradingView.

## Defaults

| Setting | Value |
| --- | --- |
| Swing Length | 12 bars left and right |
| Minimum Leg Size | 2 ATR |
| Touch tolerance | 0.15 ATR |
| Observation horizon | 16 chart bars, including the entry bar |
| Hypothetical target / stop | 1.0 / 0.5 ATR |
| Estimated round-trip costs | 0 ticks; explicitly labeled ZERO COST |
| Memory | Latest 200 completed events per bucket and direction |
| Statistics selection | Combined, with Long and Short also available |
| Minimum sample for visual emphasis | 30 completed events |

These are initial research settings, not optimized parameters. Changing inputs,
symbol, timeframe, or available chart history recalculates the sample.

## Event lifecycle

1. A pair of confirmed pivots establishes the official impulse. Its identity
   includes direction and both pivot bar indexes. Equal prices on different
   bars therefore create different identities. There is no live-end extension.
2. The ladder first permits touches on the next bar. The dashed impulse drawing
   connects the historical pivots; it does not imply that the ladder existed
   at those earlier candles. Horizontal drawings start at ladder confirmation.
3. Compare an eligible candle to the ladder already known before it began.
   Freeze ATR(14) from the prior completed candle. Require the previous close
   above the expanded zone for a long, or below it for a short, and a high–low
   overlap with the expanded zone. The signal is confirmed at the touch close.
4. Register at most one event per swing and bucket. The 0.618–0.650 pocket is
   one bucket, alongside 0.236, 0.382, 0.500 and 0.786. A candle can create
   linked observations at several different buckets; these are not independent
   replications.
5. Use the next available chart bar's open as the hypothetical entry. The
   signal candle is excluded. On live charts the indicator processes that
   entry bar at its close, using the predetermined next-open convention.
6. Track H complete chart bars, including entry as bar 1, even after a barrier
   outcome. A later swing never cancels or reanchors existing observations.
7. Only after all H bars does a record join its completed rolling cohort.
   A resolved target/stop with an unfinished observation window remains pending.

An observation retains swing ID/key, anchor indexes, bucket, direction, signal
and entry bars, zone boundaries, frozen ATR, entry price, signed distance from
the nearest zone boundary, horizon, target/stop distances and prices, tick size,
estimated cost, full-window extrema, first-barrier timing, pre-exit excursion
bounds, payoff bounds and completion bar.

## Metric definitions

For a long, window MFE is max(0, highest post-entry high − entry), and window
MAE is max(0, entry − lowest post-entry low). For shorts the directions reverse.
The panel divides these values by the event's frozen ATR. These excursions
continue after a hypothetical exit; they are not realized payoff.

All percentiles use ascending-order linear interpolation at rank (N−1) × p.
The median uses p=0.5 and MAE P90 uses p=0.9. Empty statistics are undefined and
display a dash. Zero excursion and zero return are valid numbers.

Target/stop prices are offsets from the actual hypothetical entry, measured
using frozen ATR. The bar's open is evaluated before its high and low:

- An open past a barrier establishes that first outcome.
- If the open is between barriers and the candle reaches both, the result is
  ambiguous; no intrabar path is invented.
- An intrabar target-first event fills at the target, including favorable gaps.
- An intrabar stop-first event fills at the stop; a gap through it fills at open.
- If neither barrier is reached, timeout exits at the Hth bar's close.

Once established, a barrier outcome and its payoff cannot change. A gap after
an already resolved event changes only its full-window excursions.

Pre-target MAE and pre-stop MFE do not use post-exit extremes as exact facts.
The prior extrema plus the exit bar's open give a guaranteed lower bound.
For an intrabar exit, including the relevant exit-bar extreme gives an upper
bound. An exit at the bar's open has exact equal bounds. Median bounds appear
in tooltips, in ATR units. These need no invented order within the exit candle.

Initial risk is stop distance × frozen ATR. Net R is signed entry-to-exit payoff
divided by initial risk, less costTicks × minimumTick / initialRisk.
Ambiguous events retain stop-first and target-first payoff bounds.
The mean uses every completed event, including timeouts and ambiguity.
It is a mean hypothetical opportunity payoff, not a portfolio return:
observations can overlap and the indicator implements no position sizing.

For N completed events, W target-first events and A ambiguous events:

- Target-first probability is bounded by W/N and (W+A)/N.
- Timeouts and stops remain in N.
- With A=0, the tooltip displays an approximate 95% Wilson interval.
- With A>0, it displays ordering bounds and withholds Wilson.

Ordering bounds are not confidence intervals. Wilson assumes a binomial model
and does not correct clustering across swings or trading days.

## Memory, display and alerts

Each bucket has independent long/short circular buffers. All visible metrics
are recomputed from those same retained completed records. Combined pools both
buffers and can contain 400 events per bucket at default settings; it does not
average side percentages or medians. Pending observations are separate.

The panel shows Zone, N, window median MFE, window median MAE, MAE P90,
target-first percentage/bounds, median bars to target and mean net R/bounds.
Hover cells or level labels for Wilson, outcome counts, distinct swings,
pending count, pre-exit bounds and cost assumptions.

Line width/brightness and text opacity communicate the sample threshold,
not a composite opportunity score or a best-level ranking. Both pocket
boundaries share one set of statistics. Endpoints and correctly projected
continuation extensions are ungraded.

L/S triangles mark close-confirmed touch signals. T circles, X squares and
? diamonds mark later target, stop and ambiguous confirmations. Multiple
same-type outcomes on one bar share one marker; event accounting retains each
record. Alerts are available for new confirmed impulses, first touches,
target-first confirmations and stop-first confirmations. All depend on
completed bars.

## Corrections to the original

- Removed repeated live-end resets and identified swings by their anchor bars.
- Corrected continuation extensions to project beyond the impulse endpoint.
- Prevented newly calculated levels from classifying earlier movement in their
  own confirmation candle.
- Excluded signal-bar movement and used explicit next-open references.
- Replaced close-inferred reaction direction with fixed impulse direction and
  required approach side.
- Merged pocket boundaries and prevented same-swing retest duplication.
- Froze volatility, references and distances for each observation.
- Preserved stops, timeouts, gap losses and same-bar ordering uncertainty.
- Replaced the smoothed respect score with completed-cohort probabilities,
  actual Wilson calculations when applicable, and explicit payoff bounds.
- Recomputed pooled medians and probabilities from records with matched
  denominators and bounded storage.

## Verification and reproduction

Run from the workspace root:

```sh
.venv/bin/python -m unittest discover -s studies/18_fibonacci_memory/tests -p 'test_*.py' -v
python3 scripts/check-agent-docs.py
```

Forty focused checks passed in the workspace Python 3.11 environment. They
execute the actual marked Pine numerical functions through a restricted Python
adapter, including the embedded self-check functions, and include deterministic
mirror tests over 100 generated ten-bar paths. Expected deterministic values
test gaps, ambiguity, timeouts, percentile interpolation, rolling eviction,
pooling and causal entry/ladder boundaries.

The adapter does not emulate full TradingView execution. Compiler acceptance,
chart runtime, visual layout, actual alerts and performance on long chart
histories remain unverified. Nonstandard charts use their provided prices;
missing bars are not reconstructed, and a horizon counts available chart bars
rather than wall-clock minutes. Zero-cost settings exclude costs. No historical
finding, holdout performance or profitability claim is established.

The [implementation inputs](inputs.lock.json) pin retained copies of the
original indicator and requested specification. Verification output is staged
under `work/18_fibonacci_memory/`. No dataset releases or completed runs were
modified, and no historical study was rerun.

Primary language references consulted:
[Pine objects](https://www.tradingview.com/pine-script-docs/language/objects/),
[arrays](https://www.tradingview.com/pine-script-docs/language/arrays/),
[tables](https://www.tradingview.com/pine-script-docs/visuals/tables/), and
[execution model](https://www.tradingview.com/pine-script-docs/language/execution-model/).
