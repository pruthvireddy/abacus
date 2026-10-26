# Long after a GC outer lower EMA band close

Strategy `gc_ema_outer_lower_long` · **descriptive evidence only** · Last decision: 2026-09-25

## Setup and question

On a five-minute GC chart, a completed close at or below the 225-bar EMA minus
three rolling population standard deviations of close-minus-EMA residuals is
a long candidate. The original Pine script's separate inner-band re-entry
marker is not this setup. A hypothetical entry at the next complete bar's
unadjusted open permits long-side MAE/MFE measurement. Cooldowns of 5, 10, 20,
and 30 following bars, plus a zero reference, and horizons of 5, 10, 15, 20,
30, 50, and 100 bars were inspected.

## Evidence and current advice

The [two-year static report](../runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/report.html)
compares nine prespecified signal-time filters. Using only 2025 for selection,
the chosen filter requires the signal candle to close in the upper half of its
own high–low range while still closing at or below the outer lower band. At a
10-bar cooldown and 20-bar path horizon, its 2025 capped, volatility-normalized
MFE-minus-MAE score improved by 0.263σ versus the unfiltered setup. Applying
that frozen rule in 2026 YTD improved the score by 0.131σ, from -0.309σ to
-0.179σ. The 2026 mean MAE was 30.31 GC points versus 30.94 unfiltered,
and mean MFE was 25.00 versus 23.91, on 182 and 245 valid paths respectively.
The approximate paired-week 95% interval for the score difference was
[-0.05, +0.32]σ. See the [primary candidate table](../runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/tables/primary.csv),
[sensitivity table](../runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/tables/sensitivity.csv),
and [dated advice](../runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/advice.md).
This is an uncertain directional improvement, not a validated trading edge.
The 2026 unfiltered outcomes had already been viewed in study 12, so this
chronological check is not an untouched holdout.

The [corrected interactive report](../reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/20260925T224602Z_html_interactivity_v1/report.html)
and [yearly evidence table](../runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/tables/yearly.csv)
cover 2010–2026 YTD. In the 10-bar cooldown/20-bar horizon cell, 2026 YTD has
245 valid paths with mean MAE 30.94 GC points and mean MFE 23.91; 2025 has 207
with mean MAE 11.77 and mean MFE 11.50. The 2026 point scale is much larger;
yearly means should not be pooled into a fixed stop or target without accounting
for the changing price and volatility regime. The 2026 terminal-positive rate
is 54.3% before costs, but this is not a realized trade win rate.

The evidence describes separate path extrema. It does not establish which
extreme occurred first within a five-minute bar, an executable exit, fills,
costs, or a profitable policy. Later roll adjustments enter the final chart
snapshot, and 35 exploratory parameter combinations create selection risk.
Keep this as research only. A later execution study should freeze one rule,
model costs and stop/target ordering on finer bars, and compare with a
time-matched GC baseline using later data. See [dated run advice](../runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/advice.md)
and the [study plan](../studies/12_gc_ema_band_excursions/plan.md).

## Pine chart companion

The separate [GC Band MAE/MFE TradingView companion](../studies/13_gc_ema_band_filter_validation/pine/gc_band_mae_mfe_study_panel.pine)
plots the study EMA and outer bands, marks accepted long signal candles with
**MAE/MFE LONG** text, and displays a study-identification badge on the price
chart. A lower pane shows chart-local mean MAE/MFE by horizon and a cooldown
comparison, following the [user-supplied panel example](../studies/13_gc_ema_band_filter_validation/pine/source_user_gc_band_mae_mfe.pine).
A paged calendar-week table counts filtered setup candles, entry-ready
confirmations, and accepted confirmations by Monday–Sunday New York week,
with chart coverage shown beside the counts.
On a five-minute GC chart, leave **Require upper-half signal close** on and **Minimum
close position** at 50% to match the selected filter. **Cooldown after accepted confirmation**
defaults to 10 bars and suppresses the next 10 chart candles after each accepted
signal. The filter can be turned off to display the unfiltered outer-band setup.
The script exposes a separate **GC Band MAE/MFE study LONG** alert condition.

The companion also offers optional oversized-signal rejection using prior-bar
ATR and a delayed reclaim entry above the setup's frozen outer-band price.
Both default off. Its chart statistics, cooldown comparison, and weekly counts
follow the selected model; excursion paths begin at the open after confirmation.
See the [companion settings and timing](../studies/13_gc_ema_band_filter_validation/pine/README.md).
These two options have not been evaluated in the sealed research runs.

The saved report remains the source of record. The chart pane uses TradingView's
loaded bars and cannot reproduce the backtest's complete-bar exclusions,
continuous-contract adjustments, or exact hypothetical next-bar entries.
Changes to its threshold, cooldown, band inputs, feed, or timeframe are outside
the frozen study 13 result.

## Decision history

- 2026-09-25: Selected the upper-half close filter on 2025 data and checked
  its fixed rule on 2026 YTD. Descriptive score improved, but uncertainty
  includes no improvement; retained as research only.
- 2026-09-25: Registered the long-only outer-band idea and completed the
  descriptive excursion study. No live trading rule was promoted.
