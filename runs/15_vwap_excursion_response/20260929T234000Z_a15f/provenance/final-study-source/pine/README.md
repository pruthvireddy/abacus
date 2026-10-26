# VWAP OE fade statistics indicator

Use [vwap_oe_fade_stats.pine](vwap_oe_fade_stats.pine) as the complete replacement
script in a new private TradingView Pine Editor indicator on **standard two-minute
candles**. It combines the saved VWAP OE price-chart visuals with the supplied
GC indicator's style of lower-pane statistics. Native Pine compilation and chart
replay are still unverified; the local numerical-helper checks are documented in
[verification.md](verification.md).

The measured strategy is **long after a confirmed close below minus two sigma,
short after a confirmed close above plus two sigma**, with entry measured from
the next contiguous two-minute open. Exactly-on-band closes do not qualify.
The signal candle's extrema are excluded. This is a chart-local horizon study;
it does not place orders or simulate a VWAP exit, stop, costs or fills.

## What is displayed

- VWAPs and bands show only the **two most recent daily occurrences of each
  anchor**, including the current session. This counts observed sessions, so a
  weekend does not discard Friday merely because 48 hours have passed. Asia,
  London, New York, optional Globex and the studied envelope use the same limit.
- OE buy/sell triangles and accepted FADE markers remain across **all loaded
  history**. FADE markers still honor the selected anchor, years, direction and
  cooldown. Curve retention does not filter markers or statistics. OE markers
  have their own visibility input, independent of the VWAP line toggles.
- Volume/footprint-delta annotations, TICK bubbles and original alerts remain
  on the main price chart. These ancillary text labels retain Pine's existing
  label cap; buy/sell markers use plot shapes and are not capped at 500 labels.
  The anchor reset recognizes an exact scheduled opening when the chart omits
  all bars outside that session, including the Globex maintenance break.
- A separate pane shows positive average MFE and negative average MAE curves,
  with candle-count labels. The curves are a horizon diagram, not a time series.
- The horizon table gives samples, average MFE, average MAE, direction-adjusted
  close change and favorable-close percentage at **5, 10, 15, 20, 30, 50 and 100
  candles**. The entry candle counts as candle 1. Five candles means ten minutes.
- The cooldown table compares **0, 5, 10, 20 and 30 candles** independently at
  the selected comparison horizon. The selected row controls the main table,
  curves, accepted FADE labels, next-open markers and dedicated alert conditions.
- The weekly table gives candidates, entry-ready candidates, accepted long and
  short signals, and loaded session bars. Pagination includes observed weeks
  with no signals. It does not invent weeks absent from loaded history.

For longs, favorable close means `close > entry`; for shorts, `close < entry`.
The displayed close delta is `direction * (horizon_close - entry_open)`, where
long direction is +1 and short direction is -1. It is **price change**, not
footprint volume delta. Flat outcomes remain in the denominator; hover for
long/short counts, favorable/adverse closes and ties. MAE is a positive magnitude
in the table, drawn below zero only to separate the curves visually.

## Defaults and controls

Defaults are **Asia**, both directions, every outside close, cooldown 10,
comparison horizon 20, signal-close years 2025–2026, and complete horizons inside
the original anchor session. All calculations use the symbol and bars currently
loaded in TradingView; selecting earlier years does not fetch extra history.
Points/ticks changes display units. Visibility controls never filter the sample.

Choose Asia, London, New York, Globex, or Active local session. The latter pools
local anchors with an independent cooldown clock for each anchor. Select one
anchor for separate results. Long/short filtering occurs before cooldown;
when both are selected, the two directions share that anchor's cooldown.
Cooldown starts at an accepted signal close, suppresses exactly the next N
chart candles, and permits another at N+1. Blocked candidates do not restart it.
Each new anchor session resets its clock. Open measurement paths may overlap;
cooldown is not a one-position-at-a-time execution model. Signals outside the
chosen year range do not advance the study's acceptance clocks.

**Session inputs are inherited from the OE source**, not silently replaced by
the broader research plan. Their original defaults are:

| Anchor | Default window in the General Settings timezone |
| --- | --- |
| Asia | 20:00–00:00 |
| London | 03:00–08:00 |
| New York | 09:30–16:00 |
| Globex | 18:00–17:00 |

General Settings defaults to America/New_York. To use the proposed research
windows, change Asia to `2000-0300` and London to `0300-0900`. Active local
session requires non-overlapping local windows. The new exact 2-sigma study
envelope can be shown even when original OE visual multipliers differ.
Original OE candle/wick, alternate-timeframe, offset and confluence settings
do not alter the study rule; only the distinct **FADE** labels identify accepted
study signals. The source selection and session/timezone settings do affect
the VWAP used by both layers.

The optional **Fresh band crossing only** mode requires a prior valid close on
or inside its own evolving band, then a strict close outside the current band.
Default **Every outside close** follows the supplied GC-style event study.
Neither mode claims equivalence to the proposed study 15 parent-excursion rule.
There is no reclaim wait, close-position filter or ATR filter in this one-rule
VWAP companion.

## Availability and incomplete paths

The actual anchor-opening candle must be loaded, with valid volume/source and
contiguous bars thereafter. Starting chart history halfway through an anchor
does not manufacture a valid VWAP sample; that session is unavailable for new
signals. A missing bar invalidates that anchor until its next scheduled start.
At least two completed anchor bars and positive sigma are required. Minimum
anchor age defaults to zero, with an optional minutes input.

By default a signal at the final session close is a candidate but not entry
ready. An entry candle may close exactly at session end. Missing/partial chart
bars cancel pending entries and truncate active paths. A 5-candle result remains
counted if a later gap prevents its 10-candle result; missing longer horizons
are not losses. The latest pending signal and active right-edge paths are
reported explicitly. Longer horizons can have different samples, so aggregate
mean curves need not be monotone. Turning off the session-boundary restriction
allows paths to cross the original window end but never to skip missing candles.

Continuous-contract adjustments and TradingView chart-session/feed choices can
change these statistics. This companion does not establish parity with Abacus's
pinned contract-truth data or retrospective day-eligibility filter. The broader
three-module historical study has not been executed by this indicator task.

## Source and verification

The reported **RE10140 / 74 plots** issue is addressed by replacing all VWAP and
band plots with bounded polylines and removing six invisible gradient fills.
Merely shortening a plot's visible history does not reduce its plot-slot cost.
TradingView documents [plot counts separately from drawing objects](https://www.tradingview.com/pine-script-docs/writing/limitations/).
The revised source has a conservative ceiling of **33 plot counts** (counting
every possible color series in its two plots, nine plot shapes and two alert
conditions), below 64. At most **42 polylines** fit within the declared limit of
50, including the lower-pane diagram. This is source-level accounting, not a
native compiler result. Curve visibility and colors are controlled in Inputs.

[source_vwap_oe.pine](source_vwap_oe.pine) preserves the original OE file from the
study 11 presentation snapshot. [source_stats_reference.pine](source_stats_reference.pine)
preserves the newly pasted GC reference byte-for-byte. [manifest.json](manifest.json)
records source/artifact identities. Existing study 11 exports remain unchanged.

The original `request.footprint()` and TICK requests remain dependencies of the
integrated script. TradingView restricts footprint requests to Premium/Ultimate
plans; see its [footprint documentation](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/#volume-footprints).
The new statistics themselves use chart OHLC and anchored VWAP, not footprint
delta or TICK filters. Separate-pane and price-chart rendering use TradingView's
[documented force_overlay support](https://www.tradingview.com/pine-script-docs/visuals/overview/).

Run the focused local checks from the repository root:

```sh
python3 -m unittest discover -s studies/15_vwap_excursion_response/tests -p 'test_pine_fade_stats.py' -v
python3 scripts/check-agent-docs.py
python3 scripts/build-research-index.py --check
```

The numerical tests execute the actual delivered Pine scalar helper bodies
through a restricted test translator. They do not compile Pine, emulate series
rollback or verify UDT arrays, tables, plot placement or TradingView runtime
limits. Those still need a native Pine Editor compile and replay.
