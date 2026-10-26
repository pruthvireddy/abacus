# HAC LPT configurable MTF levels

Copy the whole [Pine v6 script](hac_lpt_mtf__20260926.pine) into a new TradingView
Pine Editor indicator, save it, and select **Add to chart**.

The script extends the user's HAC LPT Phase 1 range formula. It draws current
horizontal levels with labels such as `[3 min] HTF Top 3`. The four source sets
retain their calculation intervals when the chart interval changes. Labels
identify the original source mapping, not the interval of the current chart.

| Named source set | Default calculation interval | Default color |
| --- | --- | --- |
| 1 min | 150 minutes | Orange |
| 3 min | 450 minutes | Blue |
| 5 min | 750 minutes | Teal |
| 15 min | 2 days | Magenta |

Pine supports minute intervals from 1 to 1440. The original 15 min mapping
produces the invalid interval `2250`. The editable `2D` default follows the
existing Abacus combined indicator's approximation. It does **not** recreate
an exact 2250-minute series or establish parity with the protected indicator.
See [TradingView's timeframe specification](https://www.tradingview.com/pine-script-docs/concepts/timeframes/#timeframe-string-specifications).

In **Settings → Inputs**, each timeframe has its own enable switch, color,
calculation interval, line width/style, label switch, label offset, and six
original level switches. All levels in one timeframe use its selected color.
Changing a calculation interval overrides that named source set; its label
continues to identify the set. Label offsets are measured in current chart bars.
Different default offsets separate labels when two timeframes have equal prices;
coincident lines retain the same true price and can cover one another.

**Display** controls labels, label prices/font size, line extension, segment
length, and auto-scale. Enable **Show only closest enabled level per timeframe**
to get one line from each enabled timeframe, as in the screenshot. The nearest
level is selected from that timeframe's enabled levels using the current chart
close. Equal-distance ties use the first enabled level in this order: Top 1,
Bottom 4, Top 3, Top 4/top 6, Top 5. With the option off, all enabled levels show.
Leave space to the right of the last candle to see the labels; reduce the offsets
if necessary. Chart price-scale settings can override indicator auto-scale.

**Range calculation** controls the shared lookback (default 300 calculation
bars), range unit (0.20), inner factor (0.59), and outer factor (1.32).
Top 4 and top 6 have the same price in the supplied formula. When both are
enabled they share one line and a `Top 4 / top 6` label. Either can be enabled
alone. There are five unique prices per timeframe, at most 20 lines/labels.

Requests use standard OHLC for the chart symbol, including on Heikin Ashi
charts. The range is evaluated inside each requested interval. No interval is
derived from the current chart multiplier. When a chart bar is larger than a
calculation bar, the request selects the last available intrabar value. Historical
chart sampling and the amount of data TradingView supplies can differ between
chart intervals; the script displays current levels rather than every intrabar
transition. It retains the original `gaps_off` / `lookahead_off` behavior:
developing range values can change live and can differ after reload. See
[TradingView's request behavior](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/#lower-timeframes)
and [repainting explanation](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/#historical-and-realtime-behavior).

This is a standalone Phase 1 level indicator. The other screenshot modules
(EMA, bands, bar colors, and boxes) are outside this script. The retained combined
indicator and research input locks are unchanged. No data release, research run,
or public publication is created by this chart companion.

Local verification checked the four fixed request contexts, delimiters, drawing
limits/lifecycle, and guide links. The actual level arithmetic matched the supplied
six-plot formula across 1,000 generated high/low cases. Workspace documentation
checks passed. These checks do not execute Pine: TradingView compilation and chart
rendering remain unverified.
