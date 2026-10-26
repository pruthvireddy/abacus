# GC- Overnight Breakout 15M — supplied source rules

This is a source specification for the [draft study plan](plan.md), dated 2026-10-13. No
historical analysis, Pine compilation or TradingView replay has been performed. **S** below
means [original strategy](sources/original-strategy.pine); **I** means [indicator
adaptation](sources/indicator-adaptation.pine). Line numbers refer to the retained, unchanged
files; [input lock](inputs.lock.json) records their byte identities. Code behavior takes
precedence over explanatory comments.

## Comparison at a glance

| Rule | Original strategy (S) | Indicator adaptation (I) |
|---|---|---|
| Execution | Native strategy orders; calculate at close, orders eligible afterward | Custom confirmed-bar OHLC path estimate; no orders |
| Default clock | Fixed `GMT+3`; optional `New York + 7h` | Same |
| Default range / trade window | Broker 00:00–07:00 / 07:00–20:00 | Same civil hours |
| Initial-history day | Entire first loaded broker day skipped | Same |
| Environment | Invalid hour order disables entries; chart/timeframe only warn | Invalid hours, chart or minute timeframe disable engine |
| First breakout | Two stop entries in cancelling OCA group | First inferred touch; optional dual-boundary day exclusion |
| Stop | Boundary-anchored initially; surviving percentage entry resets to fill | Same intended delay, explicit path and reset handling |
| Missing close/day boundary | Native standing orders; no explicit new-day position close | Explicit next-observed-open fallback exit and day/window entry gate |
| Sizing / costs / guard | Equity/fixed size, cap, step, native margin, commission, optional guard | None |
| Trade statistics | Monetary getter values, account-equity estimate and R | Raw points and equal-risk R; closed-trade R drawdown |
| Calendar/horizon statistics | None; performance chart uses trade number | Independent close-reference H-bar observations and entry-period buckets |
| Midpoint / re-entry | No midpoint or re-entry rule | Midpoint drawing only; no re-entry rule |

## Clock, eligibility and overnight range

1. Both default to fixed `GMT+3`, range start 0, range end 7 and close hour 20
   (S 81–99; I 11–22). These are broker civil hours, not exchange-session or
   New York overnight hours. A chart's display timezone does not enter this code.
2. Fixed mode uses the timestamp with the chosen timezone. A numeric offset such
   as `GMT+3` stays fixed; a supplied IANA timezone can itself follow DST. The
   source phrase “fixed timezone ... all year round” selects a timezone string,
   and does not force an IANA zone to ignore DST (S 310–313, 401–403; I 32–40).
3. `New York + 7h` extracts New York date/time fields, interprets those fields in
   UTC and adds seven civil hours; fields are then read in UTC. The synthetic
   broker clock follows the New York DST calendar, effectively UTC+2 in winter
   and UTC+3 in summer. Broker midnight corresponds to previous-date New York
   17:00; broker 07:00/20:00 correspond to New York 00:00/13:00. Under default
   fixed GMT+3 the same window shifts by an hour relative to New York in winter.
   Day identity follows the derived broker date, not the raw UTC date.
4. Range membership uses **bar opening hour**: start inclusive, end exclusive.
   Range high/low are max/min OHLC extremes of observed qualifying bars, reset
   on a newly observed broker day; readiness requires both finite and high > low
   (S 450–488; I 38–44, 142–147, 228–231). No minimum bar count, completeness
   flag, explicit exchange calendar or missing-range-bar rejection exists.
5. Both skip every entry on the first loaded broker day, even if that day happens
   to be complete (S 468–471, 579; I 121–123, 149, 237). Loaded-history cutoffs
   can therefore change the eligible sample. Zero-width/unavailable ranges do
   not arm; missing bars are not synthesized.
6. S requires start < end < close for entries (`envOk = hoursOk`). Its `tfOk`
   check accepts positive bar seconds ≤3600 dividing an hour; this and standard
   chart status only generate warnings (S 443–448, 735–741). I requires standard
   charts and **minute** timeframes ≤60 dividing 60, in addition to hour order;
   engine state advances only on confirmed bars with `envOk` (I 42–44, 125, 241–242).
   Neither validates that the instrument actually is GC. Use regular 15M GC bars
   in this study; broader source applicability is not evidence of GC validity.

## Arming, entry, fills and cancellation

S declares `calc_on_every_tick=false` and `process_orders_on_close=false` (24–41). At each
close it can submit/update native stop entries when the range is ready, the scheduled
`time_close` hour is within the trade window, it is flat, the broker day is untraded and it
is not the initial-history day or guard-halted (487–488, 577–579, 623–640). Thus normal 15M
arming includes the 06:45–07:00 range candle; 07:00 is the first eligible following open.
This is a boundary **touch/stop** rule, without a required closing breakout or extra tick
offset. Long is at range high; short is at range low. Positive quantity and positive stop
distance are required separately for each side. The two entries share OCA group `RB` with
cancellation after the first fill, and each has an attached SL. Unfilled entries are
cancelled when flat and setup is ineligible. A detected open position also cancels both entry
IDs (S 493–503, 622–654).

I arms at confirmed close for the following scheduled window, requiring that `time_close`
remains on the same broker day. Entry on the next observed bar requires its actual hour to be
inside the trade window, its broker day to match the armed day, flat state and no earlier
accepted trade that day (I 148–156, 233–238). This avoids stale fills that native S orders
may encounter before their next bar-close cancellation after a data gap. S's `nextInWindow`
checks only the next hour, without a next-date comparison or actual-next-bar guard.

I resolves each candle as open → nearer extreme → other extreme → close, choosing high first
when `high-open < open-low`; equality explicitly chooses low first (158–163, 186–205). The
comment calls this an official broker-emulator assumption, but also states that TradingView's
public documentation does not specify tie behavior. Native S fills remain platform-dependent
until verified; I's low-first tie is an authored assumption, not established exact parity.

An eligible I opening price at/beyond a boundary fills at **open**, preferring long if the
long condition is met. Otherwise the first qualifying path crossing fills at its boundary.
Initial stop distance must remain positive; an invalid entry attempt disables further
attempts on that candle (169–205). Excursions start at fill, and only remaining path segments
count. A candle touching both boundaries is counted as dual even when its open establishes
direction. Default `engineSkipDual=false` keeps the inferred trade; true skips that whole
opportunity and consumes the day's trade allowance (18–19, 149–156).

Both permit one accepted trade per broker day, with no reversal or recovery entry after
stopping out. S records `tradedDay` when it detects a position at close, and separately on
same-bar entry/exit records so an invisible-at-close trade still consumes the day (493–503,
533–535). I records the day at fill, including same-bar exits (181, 201). I alerts/markers
are emitted only at the confirmed signal candle close even if estimated fill and exit
occurred earlier (1–5, 250–258); a live response to that alert cannot claim the earlier fill.
S order alerts attach to native fills, while its custom template `price` field is the order
level or scheduling close, not necessarily actual fill (212–220, 629–637, 655–658, 994–997).

## Stops, exits, gap handling and risk denominators

- No take-profit, trailing stop, breakeven move or midpoint exit exists. In range
  mode the stop is the opposite boundary. In percentage mode the initial stop
  is boundary × (1 − direction × percentage/100), rounded to symbol mintick
  (S 586–589; I 173, 193). It protects the entry candle before any fill reset.
- A percentage-mode trade that survives its entry candle resets once at that
  close to actual/estimated fill × (1 − direction × percentage/100), rounded
  to mintick; it then stays fixed (S 494–503, 649–654; I 207–213). A same-bar
  stop cannot be retroactively rescued by the fill-based reset. I queues an SL
  exit at the next open when the reset stop is already beyond/touched by the
  entry close, even if that next open rebounds (132–138, 213).
- I stop crossings are inclusive and fill at the stop within a monotonic segment;
  when a segment starts through the stop, fill is that starting price, including
  adverse opening gaps (77–87, 165–167). It never credits extrema after exit.
- S queues a native market close when the scheduled next hour is ≥close hour or
  <range end, unless guard already fired; normal exit is next-bar open, such as
  the 20:00 open after the 19:45 candle. The active SL is also submitted, so
  competing native stop/market orders require explicit replay verification
  (644–658). There is no explicit S close merely because a broker day changed.
- I gives first priority at each observed open to queued time exit, new broker
  day, actual hour ≥close or <range end. Fill is open; reason 2 means a previously
  queued time exit, reason 3 means its fallback for observed day/window escape.
  Queued reset-stop exit comes next, then ordinary SL path processing (125–140,
  215–240). Missing close candles therefore use the next available open;
  reason 3 is a boundary fallback label, not a general detector of every gap.
  Source S may retain a position/pending order through missing candles; do not
  silently substitute I's fallback into a faithful S reproduction.
- For I, initial risk starts as |fill − initial boundary-based stop| (65–75).
  If the percentage entry survives, its risk field is replaced by |fill − reset
  stop| (209–211). `closedR = direction × (exit−fill) / risk`; same-bar exits
  retain the pre-reset denominator. The statistics tooltip calls this “initial
  risk” (555), but the code uses the replaced denominator for surviving entries.
- S's R is `strategy.closedtrades.profit(i)` divided by converted
  |actual entry − current directional `slActive`| × |quantity| × point value
  (527–532; labels repeat at 703–711). There is no independently frozen risk
  field per closed trade. Same-bar positions never reach `justOpened` and keep
  their planned SL; surviving percentage positions normally use the reset SL.
  Preserve planned risk, entry-candle risk and effective reset risk separately
  in future audit output rather than calling all three the same quantity.
- Neither source forces a synthetic terminal close when loaded history ends.
  Open trades and pending horizons remain incomplete and need disclosed counts.

## Quantity, monetary P&L and account guard

S defaults: capital 10,000; equity risk 1%; percentage SL 1%; max leverage 10; fixed quantity
option 1; margin 5% long/short; cash-per-order commission 0.4; slippage 0; spread absent.
Platform Properties can alter realized execution assumptions (24–41, 102–141). Risk quantity
is converted symbol-currency equity × risk% / (planned stop distance × point value). **Both
risk and fixed sizing** are capped by equity × max leverage / (boundary × point value), then
floored to input step or reported minimum contract; zero/below-step sides are skipped
(352–355, 584–600, 628–637). Size is not recomputed after gap fill/reset. Lot ounce input is
display-only (120–123, 339–344); future GC contract economics must be pinned from actual
data, not inferred from the display's default 100 oz.

S's optional guard defaults off, threshold 4% from daily equity peak. It estimates worst
candle equity using current position and adverse low/high, but entry candles use close equity
only. The peak is prior to the current candle's update; daily reset uses prior-bar equity. On
threshold breach it cancels all orders, queues `close_all` and halts entries until new broker
day (474–479, 557–572, 611–619). Reaction occurs at close with subsequent native fill. The
later open-position block still resubmits an SL; it can compete with the queued guard close.
This estimate is not continuous intrabar account protection. I has no quantity, monetary
equity, margin, compounding, commission, spread, slippage or guard; its points/R are gross
price-path estimates (22, 564).

## Closed-trade and fixed-horizon statistics

S counts every closed trade; win is monetary getter value >0, loss <0, zero is neither. Win
rate uses all trades; positive/negative sums give average win/loss, payoff, PF and
expectancy. PF is unavailable when loss sum is zero; breakeven win rate is 100/(1+payoff).
Undefined R adds zero to `sumR`, while all trades remain the expectancy-R denominator. A zero
monetary trade leaves losing streak unchanged, though a zero result gets a winning visual
label (523–555, 713, 828–837). `closedtrades.profit`, native `netprofit`, commissions and
native tester exports must be reconciled before declaring monetary metric equivalence. Equity
drawdown is the candle-worst estimate above; the optional cumulative getter-P&L chart uses
closed-trade number and exchange-timezone endpoint dates, covers loaded chart history, and
adds no day/week/month research buckets (868–955).

I includes closed trades only when R is defined, and separately counts invalid R.
All/Buy/Sell tables always include both directions irrespective of display side filter. Win
is R>0; zero resets losing streak. PF is positive R sum divided by negative R magnitude, ∞
with gains and no losses, otherwise unavailable. Net/expectancy are sum/mean R; MFE/MAE are
nonnegative raw price-point excursions along post-fill/pre-exit paths; hold is exit bar index
minus entry bar index, including zero for same-bar exits. Drawdown uses cumulative **closed**
R, without floating equity. Stop/time fractions use defined-R completed trades; fallback
exits are separately counted (382–400, 466–501, 553–565).

I's separate horizon study enters at confirmed **signal close**, not estimated stop fill;
default H=10 observed chart bars (261–285). Observation uses bars entry+1 through entry+H,
excludes the signal candle, crosses broker days and continues after trade SL/time exit.
Highest/lowest initialize at signal close; direction-adjusted MFE/MAE clamp at zero, terminal
delta is direction×(H-close −signal-close). Favorable means delta>0; edge means MFE−MAE
exceeds `1e-10 × max(1,MFE,MAE)`; ties fail (338–355, 442–464). Missing elapsed time does not
add bars. Signal counts include pending observations; averages and rates use completed
observations only, and pending terminal samples are excluded.

Calendar timezone defaults to `America/New_York`, independent of broker clock; `Exchange`
resolves to symbol timezone. Day/week/month buckets use signal bar **opening timestamp**
`time` even though horizon reference price is that bar's close. Weeks start Monday; results
stay in entry-period objects after completion, even if that period scrolls off the recent
display. Default display is eight weeks; loaded totals retain older samples; edge periods can
be partial. The side filter affects horizon/calendar and optional weekday tables, never
engine entry eligibility or All/Buy/Sell trade tables. Weekdays use estimated trade entry bar
opening time in calendar timezone, including weekends when present (270–279, 287, 323–336,
418–477, 534–580).

## What these sources do not answer

I draws `(high+low)/2`, default extending to broker midnight; retention and visibility inputs
do not change signals or statistics (676–735). Neither script tests pullback/midpoint
entries, within-range recovery, multiple attempts, re-entry after stop, or filtering the
original breakout. Those are separate prospective hypotheses in the [plan](plan.md). A best
hindsight entry is an outcome label; it cannot establish a tradable rule without a causal
trigger, availability timestamp, fill assumption and independent validation sample.