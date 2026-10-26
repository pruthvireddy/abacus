# Anchored VWAP — departure, return and first-touch response

Fresh historical execution · Protocol 1.0.0 · Frozen before new outcomes · 2026 YTD through September 18

The pinned VWAP uses completed two-minute HLC3 weighted by bar volume and a volume-weighted population sigma; it is not trade-by-trade VWAP. Signals are first fresh strict closes beyond 2, 2.5 or 3 sigma within a causal parent excursion. Entry is the next two-minute open. Horizons 5/10/15/20/50 candles are 10/20/30/40/100 minutes; 15 is supplementary. Touch is source one-minute range overlap with the tick-rounded ±1-tick VWAP zone available at that minute open. Evolving VWAP is primary; signal-frozen VWAP is secondary. A gap or reference overtake alone is not a touch. Touch response begins after the containing two-minute candle closes. All MAE/MFE excludes the signal/touch candle and follows the full horizon. Upper departures: continuation is long and fade is short; upper-arrival bounce is long and through is short. Lower departures: continuation is short and fade is long; lower-arrival bounce is short and through is long.

The release contains 1,037 ES days, 1,177 NQ days and 825 GC days, selected retrospectively for whole-day completeness. ES/NQ feature history begins in 2021; GC eligible history begins in 2016; all end September 18, 2026. Absent minutes can be no-trade intervals; absence is not asserted to be corruption. This is previously inspected exploratory history, with overlapping sessions and nested thresholds. No threshold or horizon was optimized. Tick-rounded OHLC contact does not establish an executable fill, and OHLC cannot order two barriers reached in the same minute. No fees, slippage, position sizing, stops or profitability were tested. Delta means price change; true aggressor volume delta is unavailable.

Intervals are marginal 95% percentile intervals from 2,000 shared ISO-week cluster draws (seed 1501), preserving cross-product/session dependence. Brackets contain intervals. † marks zero/all-success boundary uncertainty unresolved by a degenerate bootstrap. Sparse flags: fewer than 100 events, 30 product-session dates or 20 weeks. Latency summaries condition on actual touching. Unavailable horizons never enter success/failure denominators.

[Full numerical tables: points, ticks, sigma units, tails, contexts, uncertainty and counts](tables/summary.csv)

[Per-horizon eligibility, exclusion reasons, parent/date/week support](tables/coverage.csv)

## The four session populations

| Session | New York anchor | Observation window | Report |
| --- | --- | --- | --- |
| Asia | 20:00 | 20:00–03:00 | asia.html |
| London | 03:00 | 03:00–09:00 | london.html |
| New York | 09:30 | 09:30–16:00 | ny.html |
| Globex | 18:00 | 18:00–17:00 | globex.html |

[Asia report: ES, NQ and GC separately](asia.html)

[London report: ES, NQ and GC separately](london.html)

[New York report: ES, NQ and GC separately](ny.html)

[Globex report: ES, NQ and GC separately](globex.html)

## Primary findings across products and sessions

The table prespecifies 2 sigma at 10 and 50 candles; 10 candles is 20 minutes and 50 is 100 minutes. These rows combine mirrored sides, while the session reports retain upper/lower sides and all 2/2.5/3-sigma thresholds at every requested horizon.

| Session | Product | h | Departure n | Evolving return % [CI] | Continuation Δ points [CI] | Touch n | Bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Asia | ES | 10 | 3,124 | 44.2% [42.5%, 46.0%] | 0.04 [-0.09, 0.17] | 2,589 | 50.7% [48.9%, 52.5%] |
| Asia | ES | 50 | 2,810 | 77.7% [76.3%, 78.9%] | 0.02 [-0.28, 0.35] | 2,317 | 49.3% [47.2%, 51.5%] |
| Asia | GC | 10 | 2,401 | 43.0% [41.1%, 45.0%] | 0.34 [0.11, 0.58] | 1,998 | 51.7% [49.6%, 53.9%] |
| Asia | GC | 50 | 2,168 | 77.1% [75.4%, 78.7%] | 0.13 [-0.24, 0.52] | 1,789 | 49.6% [47.1%, 52.0%] |
| Asia | NQ | 10 | 3,300 | 38.3% [36.6%, 39.9%] | 0.51 [-0.09, 1.15] | 2,660 | 52.1% [50.3%, 53.9%] |
| Asia | NQ | 50 | 2,937 | 74.8% [73.4%, 76.1%] | 0.52 [-0.74, 1.86] | 2,370 | 49.1% [47.1%, 51.1%] |
| Globex | ES | 10 | 5,645 | 29.6% [28.4%, 30.9%] | -0.00 [-0.20, 0.20] | 5,108 | 47.9% [46.5%, 49.2%] |
| Globex | ES | 50 | 5,546 | 63.1% [61.8%, 64.4%] | -0.04 [-0.39, 0.31] | 5,000 | 48.9% [47.5%, 50.3%] |
| Globex | GC | 10 | 3,793 | 31.0% [29.3%, 32.6%] | 0.18 [0.04, 0.33] | 3,314 | 50.0% [48.2%, 51.7%] |
| Globex | GC | 50 | 3,763 | 62.1% [60.7%, 63.5%] | 0.41 [0.11, 0.76] | 3,285 | 51.7% [50.0%, 53.4%] |
| Globex | NQ | 10 | 6,060 | 24.2% [23.0%, 25.4%] | 0.69 [-0.13, 1.53] | 5,426 | 49.3% [48.0%, 50.6%] |
| Globex | NQ | 50 | 5,945 | 59.8% [58.6%, 61.0%] | 0.34 [-1.18, 1.87] | 5,333 | 49.4% [48.0%, 50.8%] |
| London | ES | 10 | 3,293 | 46.8% [45.2%, 48.4%] | 0.11 [-0.10, 0.32] | 2,821 | 49.0% [47.4%, 50.7%] |
| London | ES | 50 | 2,919 | 81.9% [80.7%, 83.1%] | -0.12 [-0.52, 0.32] | 2,436 | 49.9% [47.9%, 52.0%] |
| London | GC | 10 | 2,526 | 44.7% [43.0%, 46.6%] | 0.03 [-0.16, 0.21] | 2,128 | 49.3% [47.1%, 51.6%] |
| London | GC | 50 | 2,132 | 83.2% [81.7%, 84.7%] | 0.06 [-0.38, 0.53] | 1,777 | 49.7% [47.3%, 52.2%] |
| London | NQ | 10 | 3,482 | 42.2% [40.7%, 43.7%] | 0.45 [-0.33, 1.31] | 2,892 | 49.6% [47.9%, 51.2%] |
| London | NQ | 50 | 3,042 | 79.5% [78.1%, 80.8%] | 0.05 [-1.61, 1.78] | 2,474 | 50.0% [48.1%, 52.0%] |
| New York | ES | 10 | 2,936 | 44.1% [42.5%, 45.7%] | 0.34 [-0.11, 0.78] | 2,379 | 49.6% [47.4%, 51.7%] |
| New York | ES | 50 | 2,748 | 74.2% [72.8%, 75.6%] | 0.72 [-0.19, 1.73] | 2,195 | 50.3% [48.2%, 52.3%] |
| New York | GC | 10 | 2,023 | 45.6% [43.5%, 47.6%] | 0.25 [0.03, 0.51] | 1,623 | 49.6% [46.9%, 52.2%] |
| New York | GC | 50 | 1,927 | 75.3% [73.8%, 76.8%] | -0.06 [-0.61, 0.51] | 1,558 | 50.7% [48.3%, 53.3%] |
| New York | NQ | 10 | 2,974 | 41.4% [39.9%, 42.9%] | 0.56 [-1.44, 2.53] | 2,353 | 50.4% [48.3%, 52.4%] |
| New York | NQ | 50 | 2,795 | 72.5% [71.1%, 73.8%] | 2.63 [-1.50, 6.71] | 2,188 | 52.6% [50.7%, 54.5%] |

## How to use the evidence

Use the per-horizon denominator for its direct question and common-50 tables when comparing horizon curves. The evolving-minus-frozen paired probability contrast quantifies reference dependence, not price-only mean reversion. Touch-confirmation displacement and next-open location are retained in the event ledger; same-candle movement cannot be credited to the later response entry.

The session reports include all main comparisons, year coverage, common-cohort plots, excursion and terminal-delta distributions, stability diagnostics, warm-up sensitivity and deterministic examples. Full tables also contain marginal anchor-age, local-hour and return-latency cuts. Latency beyond 50 candles belongs to touch-response context, not a new fixed-horizon return estimate.

[Dated findings and advice](advice.md)

[Metric definitions and uncertainty](metrics.json)

[Numerical verification results](verification.json)

[All input hashes and verification](input-checks.json)

[Event ledger retention and locators](events.manifest.json)

[Frozen executable protocol](protocol-1.0.0.md)

[Product/year release coverage](tables/release-coverage.csv)

[Figure inventory and saved-table sources](tables/figure-inventory.csv)
