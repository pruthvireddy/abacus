# ES Range XV reversal continuation and retracement

Protocol 0.3.0 · Separate second analysis of Study 22 · Authorized 2026-10-12.

The user requested the probability that a reversal continues for n candles and
the frequency of a retracement followed by a favorable continuation close,
with navigable study and website views. Preserve the completed trend-length run.
This protocol and [reversal settings](reversal.yaml) freeze a new numerical run
before viewing its outcomes. The existing [input lock](inputs.lock.json) applies.

## Event and timing

For each ES 4/5/6 chart separately, R is an eligible completed non-doji candle
directly after an eligible completed candle of the opposite close-open sign.
Both candles must be contiguous original source rows in the same inferred
session. A one-candle preceding leg is sufficient. Dojis and eligibility barriers
prevent reversal selection across them. A preceding leg with an unknown start
does not invalidate an observed adjacent reversal; retain its observed length
and start-known flag. Never infer a minimum unobserved preceding length.

Every reversal metric also has preceding-leg cohorts: 1 through 10 candles
individually, 11–15, 16–20, 21+, and unknown_start. Use the exact known-start
preceding length, ending immediately before R. An unknown-start leg is assigned
only to unknown_start, regardless of its observed length. Each event belongs
to one disjoint size cohort plus the overlapping all cohort. For example a
known three-candle bearish leg followed by bullish R, F1 and F2 belongs to
prior length 3 and succeeds at n=2. Group selection uses information available
at R's completion. Check all counts equal the sum of disjoint size cohorts.

Use exact Decimal OHLC. Completion means next_bar_start_proxy or
next_bar_start_same_second; exact final trade time is unknown. Retain original
same-second order and identical rows. The event becomes available at R's
completion proxy, and this timestamp determines its named-window membership.
The annual group uses R's validated inferred session date. This anchor differs
deliberately from the first analysis's descriptive trend-opening anchor.
Neither future outcomes nor retracement timing select a subgroup.

## Continuation

Report n = 1 through 20 **additional candles after R**, excluding R itself.
Success requires the next n eligible completed candles to have R's close-open
sign without interruption. A completed opposite candle or doji establishes
failure for that horizon and every larger one. A barrier, export end or inferred
session boundary before success/failure establishes an unknown outcome.
Already-observed lower-horizon successes remain known even when the full leg is
censored. Never filter the event population on a later fully observed run end.

Save observed additional count and exact count (null if right-censored), F1 OHLC,
event timing and source identities. Each horizon records events, successes,
failures, unknowns, numerator and denominator. The rate is successes divided by
successes plus failures. Unknowns are shown and excluded from that denominator.
Recompute pooled rates from pooled counts. Horizon-specific denominators may
differ; do not imply that their rates are a censor-adjusted survival estimator.
Counts of observed successes must be nonincreasing with n; rates can differ
because the known population changes. Empty known populations have null rates.

## Retracement and recovery

The primary scope is the **immediate next completed candle F1**. Measure touches
at 25%, 50%, 75% and 100% of R's body, from R.close toward R.open. Bullish R uses
F1.low <= R.close - fraction*(R.close-R.open); bearish R mirrors this with F1.high.
Equality counts as a touch. A 100% retracement reaches R.open; it does not mean
the entire wick range was erased. This is not a within-R wick statistic.

The primary favorable close is strictly beyond R.close in R's direction; equal
is not favorable. Save a secondary same-colour F1 flag separately, because a
gap can make candle colour and close-relative-to-R disagree. The initial user
clarification offered these alternatives; the user confirmed the stated
next-candle, beyond-close interpretation before execution. No outcome
is inspected to choose the definition. A later change requires a new run or
properly identified presentation of the already-declared secondary metric.

For every depth show three distinct rates: touch / known F1; touch AND favorable
close / known F1; favorable close / touched F1. The last is conditional and its
denominator is the touch count, while the joint rate uses every known F1.
Unavailable F1 is unknown, not untouched or unfavorable. An opposite/doji F1
can still have a favorable price-relative close in a gap; apply each definition
literally. OHLC establishes a level touch and the final close, without resolving
the complete intrabar path, first-touch time or a tradable fill.

## Required sections and population

Retain overall all-hours, annual all-hours, all-years named windows, and annual
by named window for every metric and bullish, bearish and pooled directions.
Use all eight observed years 2019–2026, including explicit empty cells. The seven
independent overlapping NY wall-time windows are Asia [20:00,02:00), London
[02:00,09:00), NY [09:30,16:00), Asia Open [19:30,21:30), NY Open [09:30,10:30),
NY AM [10:30,12:30), NY PM [12:30,16:00). Outside-window events remain all-hours.
Do not truncate follow-up at a named window boundary. Never cross an inferred
daily session or stitch over a barrier. Exclude the entire partial final session
2026-09-24 before selection and retain excluded counts. 2019 and 2026 are partial.

Use the six pinned source/enhanced inputs plus the export manifest and clock
migration bytes. Enhanced times are already inferred NY wall time; do not convert
again. Bar coverage uses opening time and must be labeled separately from signal
completion-time groups. Volume, exact completion, contract/roll treatment and
adjustment history remain unverified. No execution prices, costs or P&L are tested.

## Interpretation and checks

These are empirical descriptive historical frequencies. The history has already
been inspected for trend lengths and other Range XV questions; no untouched
validation split or future forecasting claim is made. Neighboring events and
charts share market history. Do not attach iid confidence intervals or optimize
levels/horizons after observing outcomes. Retain negative and sparse cells.

Synthetic numerical checks cover mirrored directions, one-bar prior legs,
dojis, gaps, exact touch/equal-close cases, session/barrier censoring, same-second
order, lower-bound successes, empty groups and annual/window assignment.
An independent verifier parses the pinned source inputs without importing the
engine, reproduces every ordered event, and recomputes every summary,
continuation, retracement and coverage cell. Check count conservation,
horizon successes, touch nesting, joint/conditional denominators and annual to
overall counts. Bind all receipts to exact artifacts and verifier source.

Freeze numerical execution and verification bytes, settings/protocol/input lock,
environment lock, dirty Git identity and exact commands before calculation.
Stage in a unique work directory; record actual ordinary numerical tests without
skips, verify all selected web cells/CSV strings, then seal a new immutable run.
External ordered event ledgers retain checksums and locators. New source code is
[reversal_run.py](reversal_run.py), separate from the first analysis entry point.

Publication consumes saved CSVs only. Six new immutable chart/view sources
provide continuation and retracement separately, with analysis navigation and
4/5/6 chart tabs alongside preserved trend-length reports. All n=1–20 rates and
all year/window cells are visible; exact horizon counts and pooled-direction
results are retained in selected downloadable CSVs. Narada filters saved rows
for navigation and never computes rates. Verify its required gates and inspect
desktop/mobile filters, keyboard overflow and links before releasing the same
prepared bytes to the existing dedicated Vercel project.
