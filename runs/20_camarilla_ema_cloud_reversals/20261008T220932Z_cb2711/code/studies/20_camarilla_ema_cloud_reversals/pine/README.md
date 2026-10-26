# Camarilla Pivot Levels

Use [camarilla_pivot_levels.pine](camarilla_pivot_levels.pine) as one TradingView
indicator: open Pine Editor, paste the entire file, save, then add it to the chart.
The delivered title and short title are both **Camarilla Pivot Levels**.
The [original supplied source](../reference/source_user_camarilla_optional_cpr.pine)
is preserved byte-for-byte; its pivot/CPR code and existing alert logic remain
in the combined script. Strategy controls are inserted near the top; a separate
statistics engine is appended. Tabs are normalized to four spaces in the combined file.

## Cloud controls and timing

The **EMA Cloud** group supplies Show, TF, Fast, Slow, Up and Down controls.
Defaults: Show enabled, TF = 5 minutes, Fast = 20, Slow = 50. Both EMAs use close.
The cloud is green when fast is above slow, red when fast is below slow, and
unfilled at equality. Color and transparency can be changed independently.
Show EMA boundaries controls the two edge lines without removing the fill.

On a five-minute chart with TF = 5, the cloud uses the chart's EMAs directly;
there is no extra candle of delay. Its open candle develops normally, so research
signals must use the completed candle's values. When TF exceeds the chart
timeframe, **Use confirmed higher-timeframe bars** defaults to enabled: the cloud
uses the previous completed source EMA values from the start of the new source
period. This is causal but intentionally waits for source-bar confirmation.
Disabling it displays a developing higher-timeframe cloud that can repaint.
These behaviors follow [Pine's documented higher-timeframe rules](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/#avoiding-repainting).

An enabled cloud cannot have a timeframe below the chart's timeframe; the script
reports an explanatory error. Use a five-minute or lower chart for TF = 5, choose
a larger cloud TF, or disable the cloud. The combined indicator retains the
source's `dynamic_requests=false`; its new requests execute in global scope.

## Display for the proposed strategy

Use a standard five-minute candlestick chart and select **Daily** explicitly in
Pivots Timeframe. The source's Auto setting also selects daily pivots on a
five-minute chart, but explicitly selecting Daily avoids a changed pivot anchor
if the chart interval changes. Show H3/L3/H4/L4; other levels, CPR, zones,
midlines, and compact mode remain available from the supplied indicator.

H3 = R3, L3 = S3, H4 = R4, and L4 = S4. `P` is the classic pivot; `CP` is the
previous close. CPR is separate from the EMA cloud. The source's **Show only
zones** switch hides its pivot lines; the cloud has its own Show control.

For current-session research, disable Show Next Period's Pivots/CPR. Those are
projections in the supplied implementation, not established current-session
levels; their current-period OHLC request path needs a separate causality audit.
The added cloud does not repair or certify all inherited pivot code paths.
Daily-based versus intraday-built pivots can differ because of session/feed and
settlement-price choices. Match and record these settings before comparison.
See [TradingView's pivot data explanation](https://www.tradingview.com/support/solutions/43000521824-pivot-points-standard/).

The combined indicator now generates accepted rejection markers and two event
statistics tables. Inherited pivot-crossing alerts remain separate. New Accepted
S/R reversal alert conditions use the selected Strategy Criteria at confirmation
close; create an alert with Once Per Bar Close. Existing alerts retain the settings
snapshot from when they were created, so recreate them after changing criteria.
There are no strategy orders or 3R exit simulation.

## Strategy Criteria: tweak without editing code

Open the indicator's Settings → Inputs → **Strategy Criteria**, which is the first
group. Applying an input change restarts the indicator over loaded chart history,
including signals, delayed entries, horizon statistics and weekly cohorts. This
is Pine's [documented input behavior](https://www.tradingview.com/pine-script-docs/concepts/inputs/).

| Control | Initial setting | Interpretation |
| --- | --- | --- |
| Trade direction | Both | Pool long S reversals and short R reversals; select either side separately. |
| Reversal levels | R3/S3 | R4/S4 is an explicitly separate exploratory choice. |
| EMA filter | Cloud alignment | Also None, close outside both EMAs, or alignment plus outside. Change TF/Fast/Slow in EMA Cloud. |
| Previous-close/open approach | On | Long previous close > S and open ≥ S; short previous close < R and open ≤ R. |
| Directional body | On | Long close > open; short close < open. |
| Contact tolerance | 0 ticks | Allows a near-touch; close must still strictly reclaim the actual level. |
| Wick/body minimum | 0/off | Lower wick for longs, upper wick for shorts; denominator is at least a tick. |
| Previous-close distance / penetration | 0/off | ATR-normalized approach distance and maximum excursion through the level. |
| Maximum signal range | 0/off | True range versus **prior** ATR, to avoid inflated baselines. |
| Skip dual-level candles | On | Exclude candles touching both selected levels; dual-direction confirmations are always excluded. |
| One per contact episode | Off | Optional rearm requires a complete candle strictly on the approach side. |
| Cooldown | 10 bars | Skip the next ten bars; bar 11 can qualify. Shared sides, reset at a new NY date. |
| Entry window | 09:30–11:30 NY | Next-open time, start inclusive/end exclusive; weekdays only. |
| Relative volume | Off | Signal volume versus prior 20-bar mean; multiplier configurable. |
| Warmup | 250 loaded bars | No signal before warmup or when required inputs are undefined. |
| Signal years | 2020–2100 | New York confirmation-close year. |

A support rejection requires low ≤ S + tolerance and close > S. A resistance
rejection requires high ≥ R − tolerance and close < R. Approach/body/wick and
other controls add the stated requirements. The statistical levels always use
confirmed prior **daily** HLC; Daily/Auto and daily-based pivot settings are required
while statistics are enabled. Visibility switches do not filter the statistics.
Use Show exact daily levels used by statistics to inspect the studied prices.

## What the two tables measure

**Statistics / Measurement** controls ATR length (14), five candle horizons
(5/10/15/50/100), the weekly close horizon (15), and optional NY-date path cutoff.
The following contiguous five-minute open is the measurement entry. Its candle
counts as bar 1; signal-bar highs/lows never enter the path. Signal-bar ATR is
frozen independently for every event. Higher-timeframe cloud statistics always
use confirmed EMAs; a developing visual cloud can therefore differ from the filter.

- MFE: maximum price movement in the trade's favor, a nonnegative magnitude / ATR.
- MAE: maximum price movement against the trade, a nonnegative magnitude / ATR.
- Close delta: signed terminal close minus entry in the trade direction / ATR.
- Favorable close: percentage with signed delta strictly positive.
- MFE > MAE: percentage with the favorable magnitude strictly larger.

Normalize each event first, then average; ties remain in N. N counts only complete
horizons and may differ across rows. Paths can overlap and have no stops, targets,
fees or slippage. They can continue beyond the entry window. Every missing/short
chart candle interrupts unfinished paths; completed shorter horizons remain.
With strict continuity, ES's daily maintenance break can leave the 100-bar morning
horizon with N=0. A blank result denotes no complete observations, not a zero return.

The weekly table uses Monday–Sunday NY weeks of the **confirmation close**. It
shows accepted opportunities and favorable close/mean delta at the selected weekly
horizon, using that same signal cohort even when a path ends in a later week.
Zero-signal observed weeks are included; first/last weeks may be partial. Change
weeks per page/page number to inspect older loaded history. Statistics / Display
provides hide/show, positions, text size, accepted markers and entry dots.\nVisuals render in front of candles so bars cannot obscure table cells; cloud fill\nkeeps its configurable transparency. Expand a narrow browser/chart pane to view\nall seven columns, or reduce table text size.

These are exploratory event summaries. Favorable close and MFE > MAE are not a
stop/target win rate or evidence of net profitability.

## TradingView acceptance checks

TradingView chart acceptance is recorded in the staged [verification log](../../../work/20_camarilla_ema_cloud_reversals/tradingview-20261008/verification.json).\nThe broader parity/live-reload checks below remain recommended before formal\nresearch; compilation alone does not establish causality for inherited projections:

1. Compile in Pine Editor and verify the displayed indicator name.
2. On a five-minute chart, compare both cloud edges with separate close-based
   EMA 20 and EMA 50 indicators over at least 250 preceding bars. Check upward
   and downward crossings, hide/show, line visibility and color/transparency.
3. Compare daily H3/L3/H4/L4 with TradingView Pivot Points Standard set to
   Camarilla, Daily, and matching daily-based/session/settlement settings. Check
   a session boundary and a contract-roll boundary separately.
4. On a one-minute chart with a five-minute cloud, confirmed mode should update
   with the preceding five-minute bar's completed EMAs at each new five-minute
   interval. Record a live value, let the interval finish, reload, and compare.
   The same-timeframe open candle and developing HTF mode may change normally.
5. On a 15-minute chart, an enabled five-minute cloud should raise the stated
   timeframe error; disabling it should leave the original pivot display usable.
6. Toggle CPR, compact mode and zones to check interactions with the cloud.

These are acceptance checks for later chart execution, not recorded passes.
