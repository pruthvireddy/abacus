# GC Band MAE/MFE TradingView companion

Copy [gc_band_mae_mfe_study_panel.pine](gc_band_mae_mfe_study_panel.pine) into a
new TradingView Pine Editor script and add it to a standard five-minute GC
chart. It creates a separate lower statistics pane and forces the EMA bands,
signal markers, entry references, and horizon-end markers onto the price chart.
The chart badge identifies this as the **GC Band MAE/MFE long study**.

The default signal matches the [study 13 plan](../plan.md): a completed close
at or below the lower outer band, close position at least 50% of the signal
candle range, and 10 following bars of cooldown. The band multiplier is 3,
the EMA and residual-sigma windows are 225, and the panel includes signals
whose New York confirmation close years are 2025–2026. Inputs also allow the unfiltered
close signal, a wick-touch exploration, other thresholds, cooldowns, and
comparison horizons. The pane shows chart-local mean MAE/MFE in GC points at
5, 10, 15, 20, 30, 50, and 100 bars. Table MAE is a positive magnitude; the
adverse curve appears below zero to separate it visually from MFE.

## Optional entry models and candle-size filter

Under **Entry model / optional candle filter**, the defaults keep both new
options off. These are exploratory chart settings; study 13 did not test them.

- **Reject oversized signal candles** requires `true range <= maximum multiple
  × ATR[1]`. The initial settings are ATR length 14 and multiple 2.0. True range
  includes a gap from the previous close. Prior-bar ATR prevents the signal
  candle from inflating its own baseline. Equality passes; missing or zero ATR
  fails when enabled. This filter and the existing close-position filter apply
  to the original setup candle, not the later reclaim candle.
- **Entry model → Next open after signal** confirms immediately on the filtered
  band-contact close and uses the following contiguous open.
- **Entry model → Wait for a band reclaim** saves the qualifying setup's outer
  lower-band price. A later completed candle must close **strictly above that
  frozen price** within **Maximum candles to wait for reclaim**, initially 2.
  Candles 1 through N are eligible, including N; the setup candle cannot confirm
  itself. The threshold does not drift with subsequent bands. No additional
  close-position or size filter is required on the reclaim candle.

One reclaim setup is tracked at a time before the five cooldown cohorts.
Further qualifying candles do not replace it or extend its deadline. An expired
setup may be replaced by a new qualifying setup on the expiry candle. A confirming
candle cannot also arm a new setup. A five-minute gap cancels pending setups.
The orange chart line shows the frozen level while waiting.

Cooldown starts at the **accepted confirmation**, then suppresses the next N
chart candles. Setups can form during cooldown; the cooldown test happens when
they confirm. A blocked confirmation is consumed and does not restart cooldown.
All five comparison cohorts receive the same stream of model confirmations.
The year range applies to confirmation close years in New York; a setup from
the preceding year may confirm inside the selected range. Model and cooldown
state carry across the range boundary using loaded chart history.

Changing any input recalculates the horizon curves, all statistics tables,
cooldown comparisons, weekly counts, markers, and alert condition. For reclaim
entries, MAE/MFE starts from the **open after reclaim confirmation**, with that
entry candle counted as candle 1. The setup and waiting candles are excluded
from the excursion path. Pending, expired, or cooldown-blocked setups contribute
no outcome samples. A missing next bar prevents an entry; an interrupted path
retains already completed short horizons and contributes no longer horizons.

The badge and horizon-table footer identify the active model and size filter.
Reclaim confirmations are marked **MAE/MFE RECLAIM** on the price chart.
If you use alerts, recreate an existing TradingView alert after changing inputs;
an existing alert retains its saved script/settings snapshot.
See [TradingView's alert snapshot rules](https://www.tradingview.com/pine-script-docs/concepts/alerts/).

## Weekly opportunities

The bottom-right table groups signal closes into Monday–Sunday calendar weeks
in New York. The date column is that week's Monday. **Setup candles** counts
all candles passing band contact, close position, and the optional size filter,
including additional contacts while a reclaim is pending. **Entry ready** counts
confirmations produced by the selected entry model before cooldown. **Accepted
C…** counts those accepted by the selected cooldown. Immediate mode has the
same setup and ready counts. In reclaim mode failed setups produce no ready
confirmation, and setup/confirmation weeks may differ. Each count uses its own
completed candle's week; ready/accepted counts include confirmations whose
entry or MAE/MFE horizon has not completed. Cooldown carries across weeks.
**Loaded bars** shows the confirmed chart bars observed in each week within
the chosen signal-year range. Observed weeks with zero opportunities are kept;
the first, latest, and year-boundary weeks may contain only part of a week.

By default the table shows the latest eight observed weeks. Set **Weeks per
page** to fit the pane and use **Week page (1 = latest)** to browse older weeks.
The Σ row gives totals across all observed weeks, not just the displayed page.

The panel uses bars loaded by TradingView. It discards event paths when a
five-minute bar gap occurs, but cannot reproduce the pinned source's
contract/roll exclusions, final adjustment snapshot, or the full sample if
TradingView has loaded fewer historical bars. Its numbers may differ from the
[sealed research report](../../../runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/report.html).
No stop, target, fill, fee, or slippage is modeled. The horizon-end marker is a
measurement boundary, not a sell order.

## Verification

Run the focused transition checks with:

```sh
python3 -m unittest discover -s studies/13_gc_ema_band_filter_validation/tests -p 'test_pine_entry_models.py'
```

These exercise the actual scalar Pine helper bodies through a deliberately
limited Python translation, with timing, deadline, gap, and price-level cases.
They do not compile Pine or verify TradingView rendering. TradingView compilation
and chart execution still need to be checked in Pine Editor.

[source_user_gc_band_mae_mfe.pine](source_user_gc_band_mae_mfe.pine) preserves
the example supplied by the user. The revised file retains its MPL-2.0 notice.
