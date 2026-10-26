# GC- Overnight Breakout 15M — frozen Phase 1 protocol

Protocol `1.0.0`, approved by the user on October 13, 2026. The attached instruction
authorizes baseline implementation, input preparation, execution, verification,
saved evidence, publication and production deployment to the existing Narada
website. It supersedes the earlier documentation-only flags **for Phase 1 only**.
Freeze this protocol and [settings](config-phase1.json) with the selected input
lock before loading outcomes. Midpoint, reclaim, interior entries, re-entry,
additional trades, filters and optimization remain unimplemented and uncomputed.

GC regular 15-minute candles decide the strategy. Fixed UTC+3 broker range is
[00:00,07:00), trading is [07:00,20:00). The 06:45 candle normally submits long
and short boundary stop orders at its 07:00 close. Inclusive boundary touches
fill; the first fill cancels the opposite order. One accepted fill consumes the
broker day, even if it stops in its entry candle. The first loaded broker day is
excluded. No target, trailing stop, guard, reversal or synthetic endpoint exit is
used. A range cannot cross contracts.

The 1% initial stop is computed from the boundary and rounded to the GC 0.1 tick.
It protects the entire entry candle. Only a surviving position resets its stop
from its actual adverse-slippage fill at that candle's 15-minute close; the new
stop activates afterward and stays fixed. An entry-candle stop is never rescued
by a later reset. An already crossed reset stop queues an exit at the following
observed open. A time close is queued at the close preceding 20:00, normally
19:45–20:00, and executes at the following open. Time and protective stop orders
can compete; the authored model chooses market first at that opening, records
competition, and does not claim native TradingView parity.

Execution walks observed same-contract unadjusted one-minute OHLC candles while
retaining 15-minute decision/reset timing. Open gap fills use the observed open;
within-minute boundary/stop touches use the order level. Adverse slippage is
added in the transaction direction. The estimated intraminute fill timestamp is
bounded by that minute's open and close; it is not a tick-observed event time.
Excursions include only post-fill, pre-exit path segments. The primary path visits
the extreme nearest open first, with low-first ties, reproducing the indicator's
authored assumption on finer evidence. High-first and low-first alternatives
produce per-day adverse/favorable first-fill ordering bounds; any unresolved
branch remains unknown. Native TradingView compilation/replay is unverified.

The primary `validated_native` model preserves native order submission semantics
and applies an explicit quality overlay: range eligibility uses only evidence
available at the 07:00 decision; missing expected execution evidence or a contract
change censors an accepted trade, and an armed but unobserved opportunity becomes
unknown rather than a no-trade day. It does not create the indicator's missing-bar
fallback exits. `native_strategy_approx` separately preserves observed-chart stale
orders and positions through gaps. `indicator_approx` separately demonstrates its
actual-day/window entry guard and fallback close. These are execution-model
differences, not alternate entry research.

Scheduled closures are calendar evidence, not missing minutes. The input audit
must pin actual holidays, early closes, roll mapping, contract identities,
timestamps, availability, duplicates, partial endpoints and coverage before
scoring. A later missing outcome cannot retrospectively exclude an accepted
breakout. Published execution P&L never crosses an adjusted continuous roll jump.

Primary quantity is exactly one executable GC contract, $100 per price point,
$10 per 0.1 tick. Prespecified costs are an **assumed scenario**, $2.50 per
contract per side and one adverse tick per fill. Zero/one/two-tick sensitivities
and zero-cost gross results are separate executions because a slipped entry
changes the surviving-candle reset stop. These are not the user's broker charges.
The separate source account retains $10,000, 1% equity risk, 10x leverage cap,
whole-contract floor, 5% margin and $0.40 cash per order; it may produce no
executable orders. Quantities below one are faithfully skipped. Standardized
profits are never described as attainable source-account returns.

Study R freezes positive directional actual-fill-to-initial-stop risk at fill.
Nonpositive protective risk is null; executed fills and dollar costs survive.
Initial, reset/effective and source-style risk fields are separate. Breakeven is
absolute net dollars ≤1e-8. Win/loss/breakeven use completed trades; net win rate
includes all completed trades in its denominator. Invalid R is excluded only
from R denominators. Profit factor with no losses is unavailable, not zero or an
invented infinity. Annual drawdown uses its own closed-P&L path.

All result cohorts use actual estimated entry fill converted to America/New_York:
Asia [20:00,02:00), London [02:00,09:00), New York [09:30,16:00), otherwise outside.
These are reporting windows, not exchange sessions or eligibility filters. Asia
after midnight retains its actual calendar date/year. A whole trade remains in
its entry cohort across later session/year boundaries. Zero-support and unknown
cohorts remain visible. Save overall, annual, session, year×session, side, hour
and weekday rows, coverage dates, counts and uncertainty. Wilson 95% intervals
describe net win rates; fixed-seed four-calendar-week block bootstrap describes
mean net dollars/trade and mean valid net R, without optimizing settings.

Every displayed value must reconcile to saved ledgers/tables. The run retains
frozen settings/input identities, actual commands/tests, source/lock snapshots,
exclusions, coverage, order/fill/trade ledgers, numerical checks, figures and
selected publication content before sealing. All reported baseline years become
prior exposure for Phase 2; they cannot later be called untouched holdouts.
Indicator H10 diagnostics are omitted from Phase 1 and remain distinct from
realized execution results. Later presentation changes use a new revision.
