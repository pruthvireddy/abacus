# Phase 1 execution semantics and retained source differences

The [frozen protocol](protocol-phase1.md) implements only the baseline. Retained
[strategy](sources/original-strategy.pine) and
[indicator](sources/indicator-adaptation.pine) bytes remain unchanged. The engine
is [study-local](src/engine.py); its tests use synthetic candles, not historical
outcomes or TradingView replay. Native equivalence has not been established.

| Model | Entry orders through a missing window | Existing position when the evening decision is absent | Quality and roll treatment |
| --- | --- | --- | --- |
| `validated_native` (primary) | Native 15m submissions; unobserved first-fill opportunity becomes unknown | Accepted outcome becomes censored; no invented fallback market fill | Causal audited range mask; expected-minute gaps censor after acceptance; all rolls are barriers |
| `native_strategy_approx` | Standing orders can fill at the next observed open before a later close cancels them, including outside the intended window | Remains open until an observed close queues an exit; no new-day-only close | Observed-chart range; gaps retained as source limitations; rolls still censor for valid GC P&L |
| `indicator_approx` | Actual day/window guard cancels a stale order before a possible fill | Next observed open outside the day/window forces the indicator's fallback exit | Authored indicator correction; not silently used as strategy behavior; rolls still censor |

The primary model's quality overlay is a deliberate separately named correction
to incomplete source evidence. It never retrospectively deletes a fill known
before a later gap. No-trade means an eligible, fully observed opportunity with
no accepted fill; unknown and censored evidence cannot be assigned zero profit.
Source-account quantity skips are independently recorded. Scheduled closures
come from the pinned input audit and are not missing expected minutes.

Signal decisions and resets occur only at 15m closes. During normal data, the
range's final 06:59 minute closes at 07:00 and the completed 06:45 candle submits
both stop entries. Minute evidence resolves their first touch after submission.
If the last minute of an entry candle is missing, the primary model censors
before any reset is written. If that last minute is observed and only the next
minute is absent, the known reset is retained before the unknown outcome begins.
A retained endpoint inside a candle cannot prove a future reset or decision.

The stop initially uses the submitted boundary, including an adverse opening
gap fill. A surviving entry candle resets it once from the actual slipped fill.
A stop touched before that reset closes the trade on the original stop. A reset
already through the confirmed entry close queues the next observed open exit
even if that opening has rebounded. A normal time exit queues at 20:00 after the
19:45 candle. Stop/time competition at the following open is explicitly flagged;
both use that observed open and the same adverse exit slippage, with the reason
selected by a frozen market-first convention. A stop-first label sensitivity is
supported for synthetic reconciliation, not a profitability-selected setting.

`source_ohlc` walks each observed 1m open → nearer extreme → other extreme →
close, choosing low first at equal distance. This tie is authored by the
indicator; it is not proof of TradingView's native tie resolution. Whole-15m
source OHLC execution can separately be requested with `execution_minutes=15`.
Its decision timeframe remains 15m. This view has less fill-order evidence than
the primary observed-minute model.

For the standardized complete-day baseline, `high_first` and `low_first` expose
the first-fill minute's possible directions or same-minute entry/stop ordering.
Because there is one trade and no take profit, later minute ordering changes
excursions but cannot change the price of a later stop/time exit. Daywise minima
and maxima of the two completed outcomes form the adverse/favorable first-fill
ordering envelope. If either branch is censored, its bound is null. These bounds
are conditional on the observed OHLC and authored fill model; they do not bound
unobserved missing-minute prices, source-account compounding, or cross-day native
stale positions. Dual candles with an already crossed opening boundary have a
known first direction from the open; a later opposite extreme is not an OCA
reversal opportunity.

Every trade retains raw observed/level fills and adversely slipped actual fills.
`gross_points` and `gross_dollars` measure actual fill-to-exit movement before
fees and therefore include the configured slippage; `raw_price_points` is the
raw movement along **that scenario's stop-reset path**. A separate zero-slip,
zero-fee execution supplies zero-cost results. Fees are two sides × quantity ×
$2.50 in the assumed standardized scenario. Source cash-per-order fees are
$0.40 × two regardless of its quantity, with zero slippage and whole-GC sizing.
These source values are reproduced assumptions, not a realistic broker tariff.

Initial study risk is positive directional actual fill minus boundary stop,
frozen at fill. Effective/reset and active-stop source risk are distinct fields.
Dollar results remain recorded when a risk denominator is invalid. Source-style
R is a clearly named translated net-dollar/active-stop-risk ratio; no native
getter monetary parity is claimed. An optional native account guard is absent
because the frozen baseline turns it off.

Minute open fills have observed opening times. Intraminute fills retain an
earliest opening timestamp and latest minute-end bound; exact tick time is
unavailable. Cohorts use the estimated actual fill minute, with any reporting
boundary ambiguity flagged. Holding-time bounds retain this precision. A trade
is attributed wholly to its New York entry year/session, including Asia after
midnight. MFE/MAE are direction-adjusted points on post-fill/pre-exit segments;
pre-fill lows/highs and post-exit extrema never count. Censored excursions are
marked incomplete. H10 signal-close diagnostics and all Phase 2 outcomes are
uncomputed.

Public API: `run_backtest(Iterable[Bar], EngineConfig, range_eligibility=...,
expected_minute=...)` returns dictionary-row `trades`, `orders`, `events` and
`days`. Dates are UTC-aware on input and ISO UTC in ledgers. The input audit owns
the full holiday-aware expected-minute predicate and range mask. Duplicate,
descending, malformed, early-available OHLC and missing contract identities fail.
