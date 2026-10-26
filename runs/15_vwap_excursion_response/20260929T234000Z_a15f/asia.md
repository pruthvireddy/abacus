# Asia — anchored VWAP excursion and return

Fresh historical execution · Protocol 1.0.0 · Frozen before new outcomes · 2026 YTD through September 18

Asia uses its own 20:00 New York-clock anchor and [20:00, 03:00) observation window. Both entry and complete horizons stay inside this window; a final candle closing exactly at the end is eligible. DST uses America/New_York. Globex is a separate overlapping population, not a sum of local sessions.

The pinned VWAP uses completed two-minute HLC3 weighted by bar volume and a volume-weighted population sigma; it is not trade-by-trade VWAP. Signals are first fresh strict closes beyond 2, 2.5 or 3 sigma within a causal parent excursion. Entry is the next two-minute open. Horizons 5/10/15/20/50 candles are 10/20/30/40/100 minutes; 15 is supplementary. Touch is source one-minute range overlap with the tick-rounded ±1-tick VWAP zone available at that minute open. Evolving VWAP is primary; signal-frozen VWAP is secondary. A gap or reference overtake alone is not a touch. Touch response begins after the containing two-minute candle closes. All MAE/MFE excludes the signal/touch candle and follows the full horizon. Upper departures: continuation is long and fade is short; upper-arrival bounce is long and through is short. Lower departures: continuation is short and fade is long; lower-arrival bounce is short and through is long.

The release contains 1,037 ES days, 1,177 NQ days and 825 GC days, selected retrospectively for whole-day completeness. ES/NQ feature history begins in 2021; GC eligible history begins in 2016; all end September 18, 2026. Absent minutes can be no-trade intervals; absence is not asserted to be corruption. This is previously inspected exploratory history, with overlapping sessions and nested thresholds. No threshold or horizon was optimized. Tick-rounded OHLC contact does not establish an executable fill, and OHLC cannot order two barriers reached in the same minute. No fees, slippage, position sizing, stops or profitability were tested. Delta means price change; true aggressor volume delta is unavailable.

Intervals are marginal 95% percentile intervals from 2,000 shared ISO-week cluster draws (seed 1501), preserving cross-product/session dependence. Brackets contain intervals. † marks zero/all-success boundary uncertainty unresolved by a degenerate bootstrap. Sparse flags: fewer than 100 events, 30 product-session dates or 20 weeks. Latency summaries condition on actual touching. Unavailable horizons never enter success/failure denominators.

[Full numerical tables: points, ticks, sigma units, tails, contexts, uncertainty and counts](tables/summary.csv)

[Per-horizon eligibility, exclusion reasons, parent/date/week support](tables/coverage.csv)

## Primary 2-sigma overview

Mirrored upper/lower sides are combined only within each product and session in this overview. The side-specific tables below retain every threshold and horizon. Endpoint bounce frequency describes the closing direction; it differs from the 0.5-sigma first-move race.

| Session | Product | h | Departure n | Evolving return % [CI] | Continuation Δ points [CI] | Touch n | Bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Asia | ES | 10 | 3,124 | 44.2% [42.5%, 46.0%] | 0.04 [-0.09, 0.17] | 2,589 | 50.7% [48.9%, 52.5%] |
| Asia | ES | 50 | 2,810 | 77.7% [76.3%, 78.9%] | 0.02 [-0.28, 0.35] | 2,317 | 49.3% [47.2%, 51.5%] |
| Asia | GC | 10 | 2,401 | 43.0% [41.1%, 45.0%] | 0.34 [0.11, 0.58] | 1,998 | 51.7% [49.6%, 53.9%] |
| Asia | GC | 50 | 2,168 | 77.1% [75.4%, 78.7%] | 0.13 [-0.24, 0.52] | 1,789 | 49.6% [47.1%, 52.0%] |
| Asia | NQ | 10 | 3,300 | 38.3% [36.6%, 39.9%] | 0.51 [-0.09, 1.15] | 2,660 | 52.1% [50.3%, 53.9%] |
| Asia | NQ | 50 | 2,937 | 74.8% [73.4%, 76.1%] | 0.52 [-0.74, 1.86] | 2,370 | 49.1% [47.1%, 51.1%] |

## ES

Coverage: 1,037 retrospectively eligible dates, 2021-06-28 through 2026-09-18. All prices below are raw contract points. Full point/tick/sigma distributions and every tie numerator are saved in summary.csv.

### ES year coverage and retrospective exclusions

| Year | Candidate days | Eligible | Excluded |
| --- | --- | --- | --- |
| 2010 | 150 | 0 | 150 |
| 2011 | 260 | 0 | 260 |
| 2012 | 261 | 0 | 261 |
| 2013 | 261 | 0 | 261 |
| 2014 | 261 | 0 | 261 |
| 2015 | 261 | 0 | 261 |
| 2016 | 261 | 0 | 261 |
| 2017 | 260 | 0 | 260 |
| 2018 | 261 | 0 | 261 |
| 2019 | 261 | 0 | 261 |
| 2020 | 262 | 0 | 262 |
| 2021 | 261 | 101 | 160 |
| 2022 | 260 | 239 | 21 |
| 2023 | 260 | 155 | 105 |
| 2024 | 262 | 159 | 103 |
| 2025 | 261 | 216 | 45 |
| 2026 | 187 | 167 | 20 |

[Release exclusion reasons by product/year (reasons may overlap)](tables/release-coverage.csv)

### Upper departure / arrival: continuation and bounce long; fade and through short

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,615 | 1.76 [1.63, 1.89] / 1.25 | 2.06 [1.86, 2.28] / 1.25 | 2.06 [1.86, 2.28] / 1.25 | 1.76 [1.63, 1.89] / 1.25 | 0.14 [-0.02, 0.31] | -0.14 [-0.31, 0.02] | 46.6% [44.1%, 48.9%] | 46.6% [44.1%, 48.9%] | 41.0% [38.5%, 43.5%] | 98 | 843 / 266 | 6 | adequate descriptive support |
| 2.0 | 10 | 1,596 | 2.45 [2.28, 2.63] / 1.75 | 2.75 [2.49, 3.05] / 1.75 | 2.75 [2.49, 3.05] / 1.75 | 2.45 [2.28, 2.63] / 1.75 | 0.18 [-0.03, 0.42] | -0.18 [-0.42, 0.03] | 47.6% [45.1%, 50.0%] | 47.6% [45.1%, 50.0%] | 42.0% [39.6%, 44.4%] | 63 | 839 / 266 | 25 | adequate descriptive support |
| 2.0 | 15 | 1,578 | 3.07 [2.84, 3.30] / 2.00 | 3.26 [2.96, 3.59] / 2.00 | 3.26 [2.96, 3.59] / 2.00 | 3.07 [2.84, 3.30] / 2.00 | 0.15 [-0.09, 0.40] | -0.15 [-0.40, 0.09] | 48.4% [46.2%, 50.6%] | 48.4% [46.2%, 50.6%] | 43.3% [40.9%, 45.8%] | 64 | 835 / 266 | 43 | adequate descriptive support |
| 2.0 | 20 | 1,558 | 3.52 [3.25, 3.79] / 2.25 | 3.71 [3.38, 4.05] / 2.50 | 3.71 [3.38, 4.05] / 2.50 | 3.52 [3.25, 3.79] / 2.25 | 0.13 [-0.13, 0.39] | -0.13 [-0.39, 0.13] | 50.4% [48.0%, 52.9%] | 50.4% [48.0%, 52.9%] | 43.1% [40.6%, 45.5%] | 51 | 828 / 266 | 63 | adequate descriptive support |
| 2.0 | 50 | 1,436 | 5.37 [4.94, 5.83] / 3.50 | 5.46 [4.99, 5.97] / 3.75 | 5.46 [4.99, 5.97] / 3.75 | 5.37 [4.94, 5.83] / 3.50 | 0.24 [-0.20, 0.67] | -0.24 [-0.67, 0.20] | 52.8% [49.8%, 55.8%] | 52.8% [49.8%, 55.8%] | 40.5% [37.7%, 43.4%] | 30 | 800 / 265 | 185 | adequate descriptive support |
| 2.5 | 5 | 692 | 1.72 [1.53, 1.94] / 1.25 | 2.07 [1.85, 2.31] / 1.25 | 2.07 [1.85, 2.31] / 1.25 | 1.72 [1.53, 1.94] / 1.25 | 0.13 [-0.09, 0.35] | -0.13 [-0.35, 0.09] | 46.8% [42.9%, 50.6%] | 46.8% [42.9%, 50.6%] | 43.5% [40.0%, 47.2%] | 39 | 518 / 248 | 3 | adequate descriptive support |
| 2.5 | 10 | 680 | 2.44 [2.18, 2.75] / 1.75 | 2.70 [2.44, 2.99] / 1.75 | 2.70 [2.44, 2.99] / 1.75 | 2.44 [2.18, 2.75] / 1.75 | 0.17 [-0.13, 0.46] | -0.17 [-0.46, 0.13] | 47.2% [42.9%, 51.2%] | 47.2% [42.9%, 51.2%] | 42.4% [38.7%, 46.0%] | 32 | 513 / 248 | 15 | adequate descriptive support |
| 2.5 | 15 | 671 | 3.06 [2.71, 3.43] / 2.00 | 3.16 [2.84, 3.51] / 2.00 | 3.16 [2.84, 3.51] / 2.00 | 3.06 [2.71, 3.43] / 2.00 | 0.14 [-0.19, 0.45] | -0.14 [-0.45, 0.19] | 48.6% [44.6%, 52.5%] | 48.6% [44.6%, 52.5%] | 45.3% [41.2%, 49.4%] | 24 | 506 / 246 | 24 | adequate descriptive support |
| 2.5 | 20 | 659 | 3.49 [3.09, 3.93] / 2.25 | 3.69 [3.32, 4.08] / 2.50 | 3.69 [3.32, 4.08] / 2.50 | 3.49 [3.09, 3.93] / 2.25 | 0.22 [-0.22, 0.63] | -0.22 [-0.63, 0.22] | 50.2% [46.4%, 54.2%] | 50.2% [46.4%, 54.2%] | 41.6% [38.2%, 44.8%] | 22 | 497 / 243 | 36 | adequate descriptive support |
| 2.5 | 50 | 592 | 5.30 [4.70, 5.93] / 3.38 | 5.41 [4.87, 6.01] / 3.50 | 5.41 [4.87, 6.01] / 3.50 | 5.30 [4.70, 5.93] / 3.38 | 0.05 [-0.59, 0.70] | -0.05 [-0.70, 0.59] | 50.8% [46.8%, 55.0%] | 50.8% [46.8%, 55.0%] | 39.4% [35.2%, 43.6%] | 9 | 465 / 234 | 103 | adequate descriptive support |
| 3.0 | 5 | 192 | 1.88 [1.46, 2.42] / 1.00 | 2.11 [1.78, 2.50] / 1.25 | 2.11 [1.78, 2.50] / 1.25 | 1.88 [1.46, 2.42] / 1.00 | 0.07 [-0.38, 0.54] | -0.07 [-0.54, 0.38] | 47.9% [41.2%, 55.2%] | 47.9% [41.2%, 55.2%] | 46.4% [39.8%, 53.2%] | 10 | 175 / 134 | 1 | adequate descriptive support |
| 3.0 | 10 | 185 | 2.72 [2.16, 3.35] / 1.75 | 2.57 [2.20, 2.98] / 1.75 | 2.57 [2.20, 2.98] / 1.75 | 2.72 [2.16, 3.35] / 1.75 | -0.23 [-0.73, 0.31] | 0.23 [-0.31, 0.73] | 40.0% [32.8%, 47.4%] | 40.0% [32.8%, 47.4%] | 39.5% [32.3%, 46.7%] | 7 | 170 / 132 | 8 | adequate descriptive support |
| 3.0 | 15 | 184 | 3.18 [2.59, 3.82] / 2.00 | 3.14 [2.67, 3.70] / 2.25 | 3.14 [2.67, 3.70] / 2.25 | 3.18 [2.59, 3.82] / 2.00 | 0.03 [-0.53, 0.62] | -0.03 [-0.62, 0.53] | 46.7% [39.9%, 54.0%] | 46.7% [39.9%, 54.0%] | 42.9% [35.3%, 50.5%] | 9 | 169 / 132 | 9 | adequate descriptive support |
| 3.0 | 20 | 180 | 3.63 [3.03, 4.31] / 2.50 | 3.56 [3.03, 4.15] / 2.50 | 3.56 [3.03, 4.15] / 2.50 | 3.63 [3.03, 4.31] / 2.50 | -0.02 [-0.60, 0.59] | 0.02 [-0.59, 0.60] | 51.7% [44.5%, 59.3%] | 51.7% [44.5%, 59.3%] | 40.0% [33.1%, 47.5%] | 4 | 165 / 128 | 13 | adequate descriptive support |
| 3.0 | 50 | 158 | 5.08 [4.12, 6.11] / 3.50 | 5.27 [4.46, 6.17] / 3.38 | 5.27 [4.46, 6.17] / 3.38 | 5.08 [4.12, 6.11] / 3.50 | 0.17 [-0.99, 1.35] | -0.17 [-1.35, 0.99] | 55.1% [46.9%, 62.9%] | 55.1% [46.9%, 62.9%] | 36.7% [28.9%, 44.6%] | 0 | 148 / 120 | 35 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,615 | 481 | 29.8% [27.6%, 32.0%] | 1,134 | 2.0 / 3.0 | 0 | 0 | 6 | 70 | 0 |
| 2.0 | 5 | frozen | 1,615 | 411 | 25.4% [23.2%, 27.6%] | 1,204 | 2.0 / 3.0 | 0 | 0 | 6 | 70 | 0 |
| 2.0 | 10 | evolving | 1,596 | 668 | 41.9% [39.6%, 44.1%] | 928 | 3.0 / 6.0 | 0 | 0 | 25 | 107 | 0 |
| 2.0 | 10 | frozen | 1,596 | 561 | 35.2% [32.8%, 37.4%] | 1,035 | 3.0 / 6.0 | 0 | 0 | 25 | 107 | 0 |
| 2.0 | 15 | evolving | 1,578 | 778 | 49.3% [47.0%, 51.6%] | 800 | 4.0 / 8.0 | 0 | 0 | 43 | 129 | 0 |
| 2.0 | 15 | frozen | 1,578 | 649 | 41.1% [38.7%, 43.5%] | 929 | 3.0 / 8.0 | 0 | 0 | 43 | 129 | 0 |
| 2.0 | 20 | evolving | 1,558 | 861 | 55.3% [53.0%, 57.5%] | 697 | 4.0 / 10.0 | 0 | 0 | 63 | 139 | 0 |
| 2.0 | 20 | frozen | 1,558 | 722 | 46.3% [43.9%, 48.9%] | 836 | 4.0 / 10.0 | 0 | 0 | 63 | 139 | 0 |
| 2.0 | 50 | evolving | 1,436 | 1,082 | 75.3% [73.4%, 77.3%] | 354 | 7.0 / 19.0 | 0 | 0 | 185 | 199 | 0 |
| 2.0 | 50 | frozen | 1,436 | 883 | 61.5% [58.9%, 64.1%] | 553 | 6.0 / 18.0 | 0 | 0 | 185 | 199 | 0 |
| 2.5 | 5 | evolving | 692 | 172 | 24.9% [21.4%, 28.5%] | 520 | 2.0 / 4.0 | 0 | 0 | 3 | 22 | 0 |
| 2.5 | 5 | frozen | 692 | 150 | 21.7% [18.3%, 25.2%] | 542 | 2.0 / 3.0 | 0 | 0 | 3 | 22 | 0 |
| 2.5 | 10 | evolving | 680 | 242 | 35.6% [32.0%, 39.2%] | 438 | 3.0 / 6.0 | 0 | 0 | 15 | 43 | 0 |
| 2.5 | 10 | frozen | 680 | 199 | 29.3% [25.9%, 32.9%] | 481 | 3.0 / 5.0 | 0 | 0 | 15 | 43 | 0 |
| 2.5 | 15 | evolving | 671 | 289 | 43.1% [39.5%, 46.7%] | 382 | 4.0 / 8.0 | 0 | 0 | 24 | 62 | 0 |
| 2.5 | 15 | frozen | 671 | 227 | 33.8% [30.2%, 37.6%] | 444 | 3.0 / 7.5 | 0 | 0 | 24 | 62 | 0 |
| 2.5 | 20 | evolving | 659 | 317 | 48.1% [44.4%, 51.7%] | 342 | 5.0 / 10.0 | 0 | 0 | 36 | 65 | 0 |
| 2.5 | 20 | frozen | 659 | 252 | 38.2% [34.4%, 42.3%] | 407 | 4.0 / 9.0 | 0 | 0 | 36 | 65 | 0 |
| 2.5 | 50 | evolving | 592 | 417 | 70.4% [67.1%, 73.8%] | 175 | 8.0 / 22.0 | 0 | 0 | 103 | 92 | 0 |
| 2.5 | 50 | frozen | 592 | 325 | 54.9% [51.0%, 58.9%] | 267 | 6.0 / 20.0 | 0 | 0 | 103 | 92 | 0 |
| 3.0 | 5 | evolving | 192 | 59 | 30.7% [24.7%, 37.1%] | 133 | 2.0 / 3.5 | 0 | 0 | 1 | 6 | 0 |
| 3.0 | 5 | frozen | 192 | 53 | 27.6% [21.6%, 33.9%] | 139 | 1.0 / 3.0 | 0 | 0 | 1 | 6 | 0 |
| 3.0 | 10 | evolving | 185 | 79 | 42.7% [36.3%, 49.8%] | 106 | 3.0 / 5.5 | 0 | 0 | 8 | 15 | 0 |
| 3.0 | 10 | frozen | 185 | 64 | 34.6% [28.2%, 41.2%] | 121 | 2.0 / 5.0 | 0 | 0 | 8 | 15 | 0 |
| 3.0 | 15 | evolving | 184 | 90 | 48.9% [41.8%, 55.9%] | 94 | 4.0 / 8.0 | 0 | 0 | 9 | 17 | 0 |
| 3.0 | 15 | frozen | 184 | 73 | 39.7% [33.1%, 46.6%] | 111 | 3.0 / 7.0 | 0 | 0 | 9 | 17 | 0 |
| 3.0 | 20 | evolving | 180 | 99 | 55.0% [48.1%, 62.1%] | 81 | 4.0 / 9.0 | 0 | 0 | 13 | 19 | 0 |
| 3.0 | 20 | frozen | 180 | 80 | 44.4% [37.2%, 51.8%] | 100 | 3.0 / 8.0 | 0 | 0 | 13 | 19 | 0 |
| 3.0 | 50 | evolving | 158 | 117 | 74.1% [67.5%, 80.7%] | 41 | 5.0 / 15.0 | 0 | 0 | 35 | 25 | 0 |
| 3.0 | 50 | frozen | 158 | 92 | 58.2% [50.6%, 66.2%] | 66 | 4.0 / 12.5 | 0 | 0 | 35 | 25 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,304 | 1.87 [1.71, 2.05] / 1.25 | 1.89 [1.74, 2.07] / 1.25 | 1.89 [1.74, 2.07] / 1.25 | 1.87 [1.71, 2.05] / 1.25 | 0.13 [-0.01, 0.27] | -0.13 [-0.27, 0.01] | 50.5% [47.9%, 53.2%] | 50.5% [47.9%, 53.2%] | 45.4% [42.7%, 48.2%] | 91 | 753 / 265 | 18 | adequate descriptive support | 557 / 499 / 171 / 77 | 0 |
| 2.0 | 10 | 1,294 | 2.64 [2.42, 2.89] / 1.50 | 2.70 [2.49, 2.93] / 1.75 | 2.70 [2.49, 2.93] / 1.75 | 2.64 [2.42, 2.89] / 1.50 | 0.14 [-0.04, 0.34] | -0.14 [-0.34, 0.04] | 52.2% [49.8%, 54.7%] | 52.2% [49.8%, 54.7%] | 43.2% [40.4%, 46.2%] | 52 | 750 / 265 | 28 | adequate descriptive support | 611 / 541 / 65 / 77 | 0 |
| 2.0 | 15 | 1,282 | 3.24 [2.96, 3.54] / 2.00 | 3.21 [2.96, 3.47] / 2.25 | 3.21 [2.96, 3.47] / 2.25 | 3.24 [2.96, 3.54] / 2.00 | 0.04 [-0.23, 0.30] | -0.04 [-0.30, 0.23] | 51.4% [48.6%, 54.1%] | 51.4% [48.6%, 54.1%] | 41.9% [39.2%, 44.6%] | 48 | 746 / 264 | 40 | adequate descriptive support | 619 / 553 / 33 / 77 | 0 |
| 2.0 | 20 | 1,269 | 3.67 [3.36, 4.01] / 2.25 | 3.66 [3.36, 3.97] / 2.50 | 3.66 [3.36, 3.97] / 2.50 | 3.67 [3.36, 4.01] / 2.25 | 0.02 [-0.28, 0.30] | -0.02 [-0.30, 0.28] | 49.8% [46.8%, 52.7%] | 49.8% [46.8%, 52.7%] | 41.6% [39.0%, 44.2%] | 38 | 741 / 264 | 53 | adequate descriptive support | 621 / 551 / 20 / 77 | 0 |
| 2.0 | 50 | 1,163 | 5.72 [5.14, 6.32] / 3.25 | 5.35 [4.93, 5.81] / 3.75 | 5.35 [4.93, 5.81] / 3.75 | 5.72 [5.14, 6.32] / 3.25 | 0.12 [-0.44, 0.67] | -0.12 [-0.67, 0.44] | 53.9% [50.5%, 57.2%] | 53.9% [50.5%, 57.2%] | 42.7% [40.1%, 45.4%] | 19 | 709 / 262 | 159 | adequate descriptive support | 572 / 513 / 2 / 76 | 0 |
| 2.5 | 5 | 517 | 1.91 [1.70, 2.16] / 1.25 | 1.86 [1.66, 2.08] / 1.25 | 1.86 [1.66, 2.08] / 1.25 | 1.91 [1.70, 2.16] / 1.25 | -0.02 [-0.26, 0.22] | 0.02 [-0.22, 0.26] | 47.4% [43.3%, 52.0%] | 47.4% [43.3%, 52.0%] | 41.0% [36.8%, 45.2%] | 38 | 408 / 221 | 9 | adequate descriptive support | 220 / 191 / 73 / 33 | 0 |
| 2.5 | 10 | 514 | 2.76 [2.41, 3.15] / 1.75 | 2.66 [2.39, 2.96] / 1.75 | 2.66 [2.39, 2.96] / 1.75 | 2.76 [2.41, 3.15] / 1.75 | -0.01 [-0.39, 0.34] | 0.01 [-0.34, 0.39] | 49.0% [45.0%, 53.2%] | 49.0% [45.0%, 53.2%] | 43.8% [39.3%, 48.3%] | 27 | 406 / 221 | 12 | adequate descriptive support | 246 / 213 / 22 / 33 | 0 |
| 2.5 | 15 | 507 | 3.37 [2.94, 3.85] / 2.00 | 3.15 [2.84, 3.49] / 2.25 | 3.15 [2.84, 3.49] / 2.25 | 3.37 [2.94, 3.85] / 2.00 | -0.17 [-0.67, 0.30] | 0.17 [-0.30, 0.67] | 48.5% [43.9%, 52.9%] | 48.5% [43.9%, 52.9%] | 42.8% [38.7%, 46.8%] | 19 | 402 / 219 | 19 | adequate descriptive support | 247 / 218 / 9 / 33 | 0 |
| 2.5 | 20 | 499 | 3.79 [3.32, 4.32] / 2.25 | 3.63 [3.24, 4.05] / 2.50 | 3.63 [3.24, 4.05] / 2.50 | 3.79 [3.32, 4.32] / 2.25 | -0.02 [-0.53, 0.48] | 0.02 [-0.48, 0.53] | 46.7% [41.7%, 51.4%] | 46.7% [41.7%, 51.4%] | 42.9% [38.6%, 47.3%] | 10 | 399 / 218 | 27 | adequate descriptive support | 247 / 216 / 3 / 33 | 0 |
| 2.5 | 50 | 457 | 5.73 [4.96, 6.54] / 3.50 | 5.32 [4.75, 5.95] / 3.75 | 5.32 [4.75, 5.95] / 3.75 | 5.73 [4.96, 6.54] / 3.50 | 0.13 [-0.66, 0.98] | -0.13 [-0.98, 0.66] | 51.9% [47.4%, 56.4%] | 51.9% [47.4%, 56.4%] | 42.5% [38.1%, 46.8%] | 5 | 373 / 211 | 69 | adequate descriptive support | 224 / 200 / 0 / 33 | 0 |
| 3.0 | 5 | 141 | 1.83 [1.53, 2.21] / 1.25 | 1.67 [1.34, 2.08] / 0.75 | 1.67 [1.34, 2.08] / 0.75 | 1.83 [1.53, 2.21] / 1.25 | -0.16 [-0.65, 0.35] | 0.16 [-0.35, 0.65] | 40.4% [32.4%, 48.8%] | 40.4% [32.4%, 48.8%] | 29.8% [22.7%, 36.8%] | 9 | 131 / 112 | 1 | adequate descriptive support | 59 / 54 / 15 / 13 | 0 |
| 3.0 | 10 | 140 | 2.64 [2.18, 3.15] / 1.75 | 2.31 [1.89, 2.78] / 1.25 | 2.31 [1.89, 2.78] / 1.25 | 2.64 [2.18, 3.15] / 1.75 | -0.26 [-0.79, 0.27] | 0.26 [-0.27, 0.79] | 41.4% [33.6%, 49.7%] | 41.4% [33.6%, 49.7%] | 40.0% [31.8%, 48.3%] | 11 | 130 / 112 | 2 | adequate descriptive support | 62 / 57 / 8 / 13 | 0 |
| 3.0 | 15 | 138 | 3.18 [2.67, 3.77] / 2.25 | 2.71 [2.22, 3.25] / 1.75 | 2.71 [2.22, 3.25] / 1.75 | 3.18 [2.67, 3.77] / 2.25 | -0.32 [-0.93, 0.28] | 0.32 [-0.28, 0.93] | 42.0% [34.1%, 50.4%] | 42.0% [34.1%, 50.4%] | 39.1% [31.1%, 47.3%] | 5 | 130 / 112 | 4 | adequate descriptive support | 63 / 60 / 2 / 13 | 0 |
| 3.0 | 20 | 137 | 3.62 [3.02, 4.33] / 2.75 | 3.31 [2.70, 3.99] / 2.00 | 3.31 [2.70, 3.99] / 2.00 | 3.62 [3.02, 4.33] / 2.75 | -0.16 [-1.00, 0.65] | 0.16 [-0.65, 1.00] | 44.5% [36.4%, 52.3%] | 44.5% [36.4%, 52.3%] | 40.1% [32.3%, 48.8%] | 1 | 129 / 111 | 5 | adequate descriptive support | 64 / 60 / 0 / 13 | 0 |
| 3.0 | 50 | 128 | 5.47 [4.32, 6.88] / 3.25 | 5.31 [4.40, 6.27] / 3.50 | 5.31 [4.40, 6.27] / 3.50 | 5.47 [4.32, 6.88] / 3.25 | 0.21 [-1.22, 1.61] | -0.21 [-1.61, 1.22] | 52.3% [43.8%, 60.6%] | 52.3% [43.8%, 60.6%] | 43.8% [34.5%, 52.8%] | 2 | 121 / 105 | 14 | adequate descriptive support | 59 / 56 / 0 / 13 | 0 |

### Lower departure / arrival: continuation and bounce short; fade and through long

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,545 | 2.08 [1.92, 2.26] / 1.50 | 2.32 [2.12, 2.55] / 1.25 | 2.32 [2.12, 2.55] / 1.25 | 2.08 [1.92, 2.26] / 1.50 | -0.02 [-0.20, 0.16] | 0.02 [-0.16, 0.20] | 42.6% [40.2%, 45.0%] | 51.0% [48.7%, 53.4%] | 45.0% [42.5%, 47.6%] | 99 | 810 / 262 | 13 | adequate descriptive support |
| 2.0 | 10 | 1,528 | 2.86 [2.64, 3.10] / 2.00 | 3.11 [2.85, 3.39] / 2.00 | 3.11 [2.85, 3.39] / 2.00 | 2.86 [2.64, 3.10] / 2.00 | -0.11 [-0.33, 0.10] | 0.11 [-0.10, 0.33] | 43.9% [41.5%, 46.3%] | 51.8% [49.5%, 54.2%] | 43.3% [40.7%, 45.8%] | 65 | 802 / 262 | 30 | adequate descriptive support |
| 2.0 | 15 | 1,510 | 3.45 [3.18, 3.73] / 2.50 | 3.74 [3.42, 4.08] / 2.50 | 3.74 [3.42, 4.08] / 2.50 | 3.45 [3.18, 3.73] / 2.50 | -0.05 [-0.35, 0.23] | 0.05 [-0.23, 0.35] | 44.2% [41.4%, 46.9%] | 52.1% [49.3%, 54.9%] | 44.9% [42.5%, 47.5%] | 57 | 800 / 262 | 48 | adequate descriptive support |
| 2.0 | 20 | 1,498 | 3.97 [3.63, 4.34] / 2.75 | 4.26 [3.88, 4.65] / 2.75 | 4.26 [3.88, 4.65] / 2.75 | 3.97 [3.63, 4.34] / 2.75 | -0.12 [-0.46, 0.21] | 0.12 [-0.21, 0.46] | 46.3% [43.4%, 49.1%] | 50.8% [48.0%, 53.7%] | 42.1% [39.7%, 44.7%] | 44 | 799 / 262 | 60 | adequate descriptive support |
| 2.0 | 50 | 1,374 | 5.99 [5.50, 6.56] / 4.00 | 6.47 [5.83, 7.18] / 4.00 | 6.47 [5.83, 7.18] / 4.00 | 5.99 [5.50, 6.56] / 4.00 | -0.21 [-0.76, 0.41] | 0.21 [-0.41, 0.76] | 44.5% [41.1%, 47.8%] | 53.5% [50.0%, 56.8%] | 43.4% [40.7%, 46.0%] | 28 | 771 / 261 | 184 | adequate descriptive support |
| 2.5 | 5 | 690 | 2.05 [1.87, 2.24] / 1.50 | 2.41 [2.12, 2.71] / 1.50 | 2.41 [2.12, 2.71] / 1.50 | 2.05 [1.87, 2.24] / 1.50 | 0.05 [-0.20, 0.30] | -0.05 [-0.30, 0.20] | 43.2% [39.7%, 46.7%] | 50.6% [47.0%, 54.2%] | 46.7% [43.1%, 50.2%] | 43 | 491 / 236 | 10 | adequate descriptive support |
| 2.5 | 10 | 677 | 2.81 [2.57, 3.06] / 2.00 | 3.23 [2.86, 3.64] / 1.75 | 3.23 [2.86, 3.64] / 1.75 | 2.81 [2.57, 3.06] / 2.00 | 0.04 [-0.28, 0.37] | -0.04 [-0.37, 0.28] | 42.7% [39.3%, 46.1%] | 53.2% [49.5%, 56.8%] | 42.5% [38.7%, 46.3%] | 28 | 483 / 234 | 23 | adequate descriptive support |
| 2.5 | 15 | 667 | 3.40 [3.09, 3.74] / 2.25 | 3.88 [3.45, 4.36] / 2.25 | 3.88 [3.45, 4.36] / 2.25 | 3.40 [3.09, 3.74] / 2.25 | 0.12 [-0.30, 0.57] | -0.12 [-0.57, 0.30] | 45.0% [40.9%, 49.0%] | 52.2% [48.3%, 56.1%] | 44.1% [40.6%, 47.8%] | 19 | 479 / 233 | 33 | adequate descriptive support |
| 2.5 | 20 | 652 | 3.96 [3.56, 4.40] / 2.75 | 4.40 [3.91, 4.92] / 2.50 | 4.40 [3.91, 4.92] / 2.50 | 3.96 [3.56, 4.40] / 2.75 | -0.10 [-0.56, 0.39] | 0.10 [-0.39, 0.56] | 45.6% [41.6%, 49.6%] | 52.8% [48.8%, 56.9%] | 43.3% [39.1%, 47.7%] | 11 | 475 / 232 | 48 | adequate descriptive support |
| 2.5 | 50 | 588 | 5.99 [5.37, 6.65] / 4.25 | 6.43 [5.65, 7.30] / 3.75 | 6.43 [5.65, 7.30] / 3.75 | 5.99 [5.37, 6.65] / 4.25 | -0.06 [-0.85, 0.79] | 0.06 [-0.79, 0.85] | 46.4% [42.0%, 50.9%] | 51.0% [46.6%, 55.3%] | 41.5% [37.8%, 45.3%] | 15 | 443 / 224 | 112 | adequate descriptive support |
| 3.0 | 5 | 198 | 1.73 [1.48, 1.99] / 1.25 | 2.58 [2.10, 3.14] / 1.75 | 2.58 [2.10, 3.14] / 1.75 | 1.73 [1.48, 1.99] / 1.25 | 0.28 [-0.10, 0.68] | -0.28 [-0.68, 0.10] | 49.5% [42.9%, 56.1%] | 45.5% [38.8%, 52.1%] | 55.6% [48.7%, 62.5%] | 10 | 182 / 128 | 6 | adequate descriptive support |
| 3.0 | 10 | 197 | 2.42 [2.11, 2.77] / 1.75 | 3.15 [2.60, 3.79] / 2.00 | 3.15 [2.60, 3.79] / 2.00 | 2.42 [2.11, 2.77] / 1.75 | -0.04 [-0.50, 0.43] | 0.04 [-0.43, 0.50] | 46.2% [39.1%, 53.4%] | 50.3% [42.9%, 57.3%] | 48.2% [40.5%, 55.9%] | 7 | 182 / 128 | 7 | adequate descriptive support |
| 3.0 | 15 | 193 | 3.06 [2.60, 3.57] / 2.00 | 3.63 [3.06, 4.31] / 2.50 | 3.63 [3.06, 4.31] / 2.50 | 3.06 [2.60, 3.57] / 2.00 | -0.04 [-0.66, 0.56] | 0.04 [-0.56, 0.66] | 45.1% [38.0%, 52.4%] | 49.7% [42.2%, 56.9%] | 34.7% [28.2%, 41.3%] | 10 | 179 / 128 | 11 | adequate descriptive support |
| 3.0 | 20 | 192 | 3.49 [2.94, 4.10] / 2.38 | 4.17 [3.55, 4.90] / 2.88 | 4.17 [3.55, 4.90] / 2.88 | 3.49 [2.94, 4.10] / 2.38 | -0.12 [-0.84, 0.51] | 0.12 [-0.51, 0.84] | 46.9% [40.2%, 53.5%] | 50.5% [43.8%, 57.1%] | 43.2% [36.5%, 50.3%] | 5 | 178 / 127 | 12 | adequate descriptive support |
| 3.0 | 50 | 170 | 5.29 [4.49, 6.17] / 3.75 | 5.76 [4.79, 6.89] / 3.75 | 5.76 [4.79, 6.89] / 3.75 | 5.29 [4.49, 6.17] / 3.75 | -0.09 [-1.26, 1.16] | 0.09 [-1.16, 1.26] | 46.5% [38.5%, 54.5%] | 50.6% [42.2%, 58.4%] | 44.7% [37.2%, 52.8%] | 5 | 159 / 116 | 34 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,545 | 527 | 34.1% [31.6%, 36.5%] | 1,018 | 2.0 / 4.0 | 0 | 0 | 13 | 91 | 0 |
| 2.0 | 5 | frozen | 1,545 | 436 | 28.2% [25.8%, 30.5%] | 1,109 | 2.0 / 3.0 | 0 | 0 | 13 | 91 | 0 |
| 2.0 | 10 | evolving | 1,528 | 714 | 46.7% [44.1%, 49.2%] | 814 | 3.0 / 6.0 | 0 | 0 | 30 | 124 | 0 |
| 2.0 | 10 | frozen | 1,528 | 590 | 38.6% [36.0%, 41.3%] | 938 | 3.0 / 6.0 | 0 | 0 | 30 | 124 | 0 |
| 2.0 | 15 | evolving | 1,510 | 837 | 55.4% [52.7%, 58.2%] | 673 | 4.0 / 8.0 | 0 | 0 | 48 | 146 | 0 |
| 2.0 | 15 | frozen | 1,510 | 691 | 45.8% [42.9%, 48.6%] | 819 | 4.0 / 8.0 | 0 | 0 | 48 | 146 | 0 |
| 2.0 | 20 | evolving | 1,498 | 914 | 61.0% [58.5%, 63.6%] | 584 | 4.0 / 10.0 | 0 | 0 | 60 | 163 | 0 |
| 2.0 | 20 | frozen | 1,498 | 751 | 50.1% [47.3%, 53.0%] | 747 | 5.0 / 9.0 | 0 | 0 | 60 | 163 | 0 |
| 2.0 | 50 | evolving | 1,374 | 1,100 | 80.1% [78.0%, 82.1%] | 274 | 6.0 / 16.0 | 0 | 0 | 184 | 195 | 0 |
| 2.0 | 50 | frozen | 1,374 | 905 | 65.9% [63.1%, 68.6%] | 469 | 6.0 / 16.0 | 0 | 0 | 184 | 195 | 0 |
| 2.5 | 5 | evolving | 690 | 194 | 28.1% [24.9%, 31.4%] | 496 | 2.0 / 4.0 | 0 | 0 | 10 | 33 | 0 |
| 2.5 | 5 | frozen | 690 | 161 | 23.3% [20.3%, 26.6%] | 529 | 2.0 / 4.0 | 0 | 0 | 10 | 33 | 0 |
| 2.5 | 10 | evolving | 677 | 261 | 38.6% [35.2%, 41.8%] | 416 | 3.0 / 6.0 | 0 | 0 | 23 | 45 | 0 |
| 2.5 | 10 | frozen | 677 | 216 | 31.9% [28.7%, 35.3%] | 461 | 3.0 / 6.0 | 0 | 0 | 23 | 45 | 0 |
| 2.5 | 15 | evolving | 667 | 311 | 46.6% [43.2%, 49.9%] | 356 | 4.0 / 8.0 | 0 | 0 | 33 | 51 | 0 |
| 2.5 | 15 | frozen | 667 | 260 | 39.0% [35.7%, 42.4%] | 407 | 4.0 / 8.0 | 0 | 0 | 33 | 51 | 0 |
| 2.5 | 20 | evolving | 652 | 356 | 54.6% [51.1%, 58.1%] | 296 | 5.0 / 11.0 | 0 | 0 | 48 | 64 | 0 |
| 2.5 | 20 | frozen | 652 | 292 | 44.8% [41.3%, 48.4%] | 360 | 5.0 / 11.0 | 0 | 0 | 48 | 64 | 0 |
| 2.5 | 50 | evolving | 588 | 442 | 75.2% [71.8%, 78.2%] | 146 | 8.0 / 20.0 | 0 | 0 | 112 | 86 | 0 |
| 2.5 | 50 | frozen | 588 | 356 | 60.5% [56.5%, 64.3%] | 232 | 7.0 / 19.0 | 0 | 0 | 112 | 86 | 0 |
| 3.0 | 5 | evolving | 198 | 63 | 31.8% [26.0%, 37.7%] | 135 | 2.0 / 4.0 | 0 | 0 | 6 | 13 | 0 |
| 3.0 | 5 | frozen | 198 | 50 | 25.3% [19.3%, 31.1%] | 148 | 1.0 / 3.0 | 0 | 0 | 6 | 13 | 0 |
| 3.0 | 10 | evolving | 197 | 80 | 40.6% [34.0%, 47.2%] | 117 | 3.0 / 5.0 | 0 | 0 | 7 | 18 | 0 |
| 3.0 | 10 | frozen | 197 | 62 | 31.5% [25.0%, 37.7%] | 135 | 2.0 / 5.0 | 0 | 0 | 7 | 18 | 0 |
| 3.0 | 15 | evolving | 193 | 96 | 49.7% [42.9%, 56.8%] | 97 | 4.0 / 8.0 | 0 | 0 | 11 | 18 | 0 |
| 3.0 | 15 | frozen | 193 | 78 | 40.4% [34.0%, 46.8%] | 115 | 4.0 / 8.8 | 0 | 0 | 11 | 18 | 0 |
| 3.0 | 20 | evolving | 192 | 106 | 55.2% [48.5%, 61.9%] | 86 | 5.0 / 9.0 | 0 | 0 | 12 | 17 | 0 |
| 3.0 | 20 | frozen | 192 | 89 | 46.4% [39.4%, 53.0%] | 103 | 5.0 / 12.0 | 0 | 0 | 12 | 17 | 0 |
| 3.0 | 50 | evolving | 170 | 130 | 76.5% [69.9%, 82.7%] | 40 | 6.5 / 16.8 | 0 | 0 | 34 | 25 | 0 |
| 3.0 | 50 | frozen | 170 | 105 | 61.8% [54.2%, 68.9%] | 65 | 6.0 / 16.0 | 0 | 0 | 34 | 25 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,308 | 1.84 [1.70, 2.00] / 1.25 | 2.07 [1.88, 2.30] / 1.25 | 2.07 [1.88, 2.30] / 1.25 | 1.84 [1.70, 2.00] / 1.25 | 0.17 [0.02, 0.33] | -0.17 [-0.33, -0.02] | 48.5% [45.7%, 51.3%] | 45.2% [42.7%, 47.8%] | 44.8% [41.9%, 47.6%] | 83 | 740 / 260 | 12 | adequate descriptive support | 534 / 503 / 178 / 93 | 0 |
| 2.0 | 10 | 1,295 | 2.56 [2.34, 2.81] / 1.75 | 2.88 [2.60, 3.20] / 1.75 | 2.88 [2.60, 3.20] / 1.75 | 2.56 [2.34, 2.81] / 1.75 | 0.09 [-0.17, 0.35] | -0.09 [-0.35, 0.17] | 49.2% [46.4%, 51.9%] | 46.9% [44.2%, 49.7%] | 43.7% [41.1%, 46.4%] | 50 | 733 / 259 | 25 | adequate descriptive support | 583 / 544 / 75 / 93 | 0 |
| 2.0 | 15 | 1,277 | 3.12 [2.84, 3.43] / 2.00 | 3.52 [3.19, 3.89] / 2.25 | 3.52 [3.19, 3.89] / 2.25 | 3.12 [2.84, 3.43] / 2.00 | 0.13 [-0.17, 0.41] | -0.13 [-0.41, 0.17] | 49.2% [46.5%, 51.9%] | 48.0% [45.1%, 51.0%] | 45.3% [42.6%, 48.1%] | 36 | 729 / 259 | 43 | adequate descriptive support | 596 / 557 / 31 / 93 | 0 |
| 2.0 | 20 | 1,256 | 3.57 [3.27, 3.92] / 2.25 | 4.07 [3.69, 4.48] / 2.75 | 4.07 [3.69, 4.48] / 2.75 | 3.57 [3.27, 3.92] / 2.25 | 0.19 [-0.14, 0.51] | -0.19 [-0.51, 0.14] | 48.4% [45.5%, 51.3%] | 48.5% [45.6%, 51.4%] | 43.1% [40.3%, 45.6%] | 39 | 725 / 259 | 64 | adequate descriptive support | 590 / 550 / 23 / 93 | 0 |
| 2.0 | 50 | 1,154 | 5.60 [5.12, 6.14] / 3.75 | 6.03 [5.43, 6.68] / 4.00 | 6.03 [5.43, 6.68] / 4.00 | 5.60 [5.12, 6.14] / 3.75 | -0.22 [-0.76, 0.36] | 0.22 [-0.36, 0.76] | 44.7% [41.2%, 48.4%] | 53.5% [49.9%, 57.0%] | 44.5% [41.9%, 47.2%] | 21 | 693 / 257 | 166 | adequate descriptive support | 550 / 510 / 1 / 93 | 0 |
| 2.5 | 5 | 547 | 1.81 [1.64, 1.99] / 1.25 | 1.91 [1.71, 2.13] / 1.25 | 1.91 [1.71, 2.13] / 1.25 | 1.81 [1.64, 1.99] / 1.25 | 0.11 [-0.12, 0.34] | -0.11 [-0.34, 0.12] | 49.0% [44.3%, 53.5%] | 43.9% [39.7%, 48.0%] | 44.8% [40.6%, 49.0%] | 39 | 402 / 212 | 9 | adequate descriptive support | 204 / 207 / 91 / 45 | 0 |
| 2.5 | 10 | 535 | 2.66 [2.34, 3.07] / 1.75 | 2.68 [2.38, 3.01] / 1.75 | 2.68 [2.38, 3.01] / 1.75 | 2.66 [2.34, 3.07] / 1.75 | -0.14 [-0.60, 0.27] | 0.14 [-0.27, 0.60] | 50.1% [46.0%, 54.1%] | 46.5% [42.5%, 50.7%] | 44.1% [40.2%, 48.2%] | 18 | 395 / 210 | 21 | adequate descriptive support | 223 / 226 / 41 / 45 | 0 |
| 2.5 | 15 | 525 | 3.18 [2.79, 3.65] / 2.00 | 3.40 [3.00, 3.82] / 2.25 | 3.40 [3.00, 3.82] / 2.25 | 3.18 [2.79, 3.65] / 2.00 | 0.14 [-0.32, 0.60] | -0.14 [-0.60, 0.32] | 48.6% [44.4%, 52.7%] | 48.4% [44.0%, 52.6%] | 46.3% [42.1%, 50.8%] | 16 | 392 / 208 | 31 | adequate descriptive support | 232 / 228 / 20 / 45 | 0 |
| 2.5 | 20 | 512 | 3.57 [3.15, 4.06] / 2.25 | 3.98 [3.51, 4.49] / 2.50 | 3.98 [3.51, 4.49] / 2.50 | 3.57 [3.15, 4.06] / 2.25 | 0.33 [-0.15, 0.87] | -0.33 [-0.87, 0.15] | 49.8% [45.7%, 54.0%] | 48.4% [44.3%, 52.6%] | 41.4% [37.5%, 45.3%] | 9 | 388 / 206 | 44 | adequate descriptive support | 227 / 226 / 14 / 45 | 0 |
| 2.5 | 50 | 460 | 5.56 [4.90, 6.33] / 3.75 | 5.90 [5.19, 6.75] / 3.88 | 5.90 [5.19, 6.75] / 3.88 | 5.56 [4.90, 6.33] / 3.75 | -0.23 [-1.04, 0.64] | 0.23 [-0.64, 1.04] | 47.2% [42.3%, 52.1%] | 50.4% [45.7%, 55.1%] | 45.2% [40.7%, 49.3%] | 11 | 361 / 199 | 96 | adequate descriptive support | 209 / 205 / 1 / 45 | 0 |
| 3.0 | 5 | 160 | 1.65 [1.40, 1.92] / 1.25 | 1.76 [1.48, 2.06] / 1.25 | 1.76 [1.48, 2.06] / 1.25 | 1.65 [1.40, 1.92] / 1.25 | 0.24 [-0.13, 0.59] | -0.24 [-0.59, 0.13] | 49.4% [41.9%, 57.1%] | 43.1% [35.9%, 50.7%] | 37.5% [29.4%, 45.4%] | 12 | 149 / 112 | 2 | adequate descriptive support | 51 / 64 / 22 / 23 | 0 |
| 3.0 | 10 | 154 | 2.32 [1.89, 2.79] / 1.50 | 2.45 [2.04, 2.90] / 1.50 | 2.45 [2.04, 2.90] / 1.50 | 2.32 [1.89, 2.79] / 1.50 | 0.12 [-0.40, 0.59] | -0.12 [-0.59, 0.40] | 52.6% [44.5%, 60.8%] | 41.6% [34.2%, 49.1%] | 33.1% [25.6%, 41.0%] | 9 | 143 / 108 | 8 | adequate descriptive support | 54 / 66 / 11 / 23 | 0 |
| 3.0 | 15 | 151 | 2.74 [2.26, 3.27] / 1.75 | 3.31 [2.77, 3.89] / 2.50 | 3.31 [2.77, 3.89] / 2.50 | 2.74 [2.26, 3.27] / 1.75 | 0.46 [-0.22, 1.16] | -0.46 [-1.16, 0.22] | 53.0% [45.5%, 60.6%] | 45.0% [37.3%, 52.7%] | 43.7% [36.1%, 51.8%] | 3 | 140 / 106 | 11 | adequate descriptive support | 59 / 65 / 4 / 23 | 0 |
| 3.0 | 20 | 147 | 3.18 [2.65, 3.82] / 2.25 | 4.07 [3.34, 4.86] / 2.75 | 4.07 [3.34, 4.86] / 2.75 | 3.18 [2.65, 3.82] / 2.25 | 0.74 [-0.08, 1.63] | -0.74 [-1.63, 0.08] | 50.3% [41.9%, 58.1%] | 48.3% [40.7%, 56.5%] | 42.2% [34.4%, 50.0%] | 2 | 136 / 103 | 15 | adequate descriptive support | 57 / 64 / 3 / 23 | 0 |
| 3.0 | 50 | 136 | 4.67 [3.92, 5.45] / 3.25 | 5.77 [4.50, 7.29] / 3.62 | 5.77 [4.50, 7.29] / 3.62 | 4.67 [3.92, 5.45] / 3.25 | 0.40 [-0.99, 1.89] | -0.40 [-1.89, 0.99] | 45.6% [36.8%, 54.2%] | 50.7% [42.6%, 59.5%] | 47.1% [38.8%, 55.3%] | 5 | 127 / 100 | 26 | adequate descriptive support | 53 / 60 / 0 / 23 | 0 |

### Common cohort, distribution and year diagnostics

The horizon curves use the identical complete-50 cohort. Distribution quantiles and year diagnostics use each horizon’s eligible cohort. Year 2026 is partial. These diagnostics are descriptive on previously inspected history.

![ES Asia return](figures/asia-ES-return.svg)

![ES Asia excursion](figures/asia-ES-excursion.svg)

![ES Asia endpoint](figures/asia-ES-endpoint.svg)

![ES Asia mae-mfe-distribution](figures/asia-ES-mae-mfe-distribution.svg)

![ES Asia terminal-distribution](figures/asia-ES-terminal-distribution.svg)

![ES Asia year-stability](figures/asia-ES-year-stability.svg)

### Sensitivity and chronological periods at 10 candles

| Module | Scope | n | Days / weeks | Directional Δ [CI] | Return or bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- |
| departure | all | 3,124 | 1,024 / 267 | 0.04 [-0.09, 0.17] | 44.2% [42.5%, 46.0%] |
| departure | common_50 | 2,810 | 1,012 / 267 | 0.07 [-0.07, 0.22] | 48.0% [46.3%, 49.8%] |
| departure | age_ge30 | 2,069 | 964 / 267 | 0.09 [-0.04, 0.23] | 25.2% [23.3%, 27.2%] |
| departure | through_2023 | 1,478 | 492 / 126 | 0.03 [-0.14, 0.19] | 44.3% [41.5%, 47.1%] |
| departure | year_2024_period | 520 | 157 / 52 | 0.09 [-0.13, 0.32] | 47.1% [42.6%, 51.7%] |
| departure | years_2025_2026 | 1,126 | 375 / 90 | 0.03 [-0.21, 0.29] | 42.8% [40.5%, 45.3%] |
| touch | all | 2,589 | 986 / 267 | 0.12 [-0.04, 0.28] | 50.7% [48.9%, 52.5%] |
| touch | common_50 | 2,317 | 969 / 267 | 0.10 [-0.07, 0.26] | 50.9% [48.9%, 52.8%] |
| touch | age_ge30 | 1,538 | 830 / 264 | 0.24 [0.07, 0.42] | 51.6% [49.3%, 54.0%] |
| touch | through_2023 | 1,225 | 478 / 126 | 0.03 [-0.16, 0.22] | 49.1% [46.5%, 52.0%] |
| touch | year_2024_period | 437 | 154 / 52 | 0.03 [-0.17, 0.23] | 50.3% [45.3%, 54.9%] |
| touch | years_2025_2026 | 927 | 354 / 90 | 0.29 [-0.09, 0.62] | 53.0% [49.8%, 56.0%] |

### Deterministic source-path examples

Examples are the earliest stable ID in each prespecified class. They illustrate mechanisms and exclusions, not representative trade quality. The source table includes reference available_at and known sigma for every minute; charts plot raw one-minute high/low and references. Source minute open time relative to entry is shown; contacts have interval resolution. Lines join minute OHLC observations for display and do not imply intraminute order or trades through gaps. The 2-sigma envelope is plotted; 2.5/3-sigma references are retained in the example-path table.

return: ES-asia-2021-06-28-P0041-K2.5-H10; lower side. Signal/confirmation 2021-06-27 21:26:00-04:00; entry 2021-06-27 21:26:00-04:00; deadline 2021-06-27 21:46:00-04:00 (New York time). Frozen sigma 0.81 points; signal VWAP 4,274.61. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-asia-2021-06-28-P0041-K2.5-H10](figures/example-asia-ES-return.svg)

non_return: ES-asia-2021-06-28-P0041-K2-H10; lower side. Signal/confirmation 2021-06-27 21:24:00-04:00; entry 2021-06-27 21:24:00-04:00; deadline 2021-06-27 21:44:00-04:00 (New York time). Frozen sigma 0.77 points; signal VWAP 4,274.65. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-asia-2021-06-28-P0041-K2-H10](figures/example-asia-ES-non_return.svg)

bounce: ES-asia-2021-06-30-P0016-T-H10; lower side. Signal/confirmation 2021-06-29 21:14:00-04:00; entry 2021-06-29 21:14:00-04:00; deadline 2021-06-29 21:34:00-04:00 (New York time). Frozen sigma 1.05 points; signal VWAP 4,288.04. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-asia-2021-06-30-P0016-T-H10](figures/example-asia-ES-bounce.svg)

through: ES-asia-2021-06-28-P0041-T-H10; lower side. Signal/confirmation 2021-06-27 21:46:00-04:00; entry 2021-06-27 21:46:00-04:00; deadline 2021-06-27 22:06:00-04:00 (New York time). Frozen sigma 0.96 points; signal VWAP 4,274.35. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-asia-2021-06-28-P0041-T-H10](figures/example-asia-ES-through.svg)

ambiguity: ES-asia-2021-08-27-P0004-T-H10; lower side. Signal/confirmation 2021-08-26 20:12:00-04:00; entry 2021-08-26 20:12:00-04:00; deadline 2021-08-26 20:32:00-04:00 (New York time). Frozen sigma 0.38 points; signal VWAP 4,464.30. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-asia-2021-08-27-P0004-T-H10](figures/example-asia-ES-ambiguity.svg)

exclusion: ES-asia-2021-06-28-P0178-K2-H50; upper side. Signal/confirmation 2021-06-28 01:58:00-04:00; entry 2021-06-28 01:58:00-04:00; deadline 2021-06-28 03:38:00-04:00 (New York time). Frozen sigma 0.91 points; signal VWAP 4,273.92. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: session_boundary.

![ES-asia-2021-06-28-P0178-K2-H50](figures/example-asia-ES-exclusion.svg)

## NQ

Coverage: 1,177 retrospectively eligible dates, 2021-06-28 through 2026-09-18. All prices below are raw contract points. Full point/tick/sigma distributions and every tie numerator are saved in summary.csv.

### NQ year coverage and retrospective exclusions

| Year | Candidate days | Eligible | Excluded |
| --- | --- | --- | --- |
| 2010 | 150 | 0 | 150 |
| 2011 | 260 | 0 | 260 |
| 2012 | 261 | 0 | 261 |
| 2013 | 261 | 0 | 261 |
| 2014 | 261 | 0 | 261 |
| 2015 | 261 | 0 | 261 |
| 2016 | 261 | 0 | 261 |
| 2017 | 260 | 0 | 260 |
| 2018 | 261 | 0 | 261 |
| 2019 | 261 | 0 | 261 |
| 2020 | 262 | 0 | 262 |
| 2021 | 261 | 115 | 146 |
| 2022 | 260 | 236 | 24 |
| 2023 | 260 | 217 | 43 |
| 2024 | 262 | 213 | 49 |
| 2025 | 261 | 224 | 37 |
| 2026 | 187 | 172 | 15 |

[Release exclusion reasons by product/year (reasons may overlap)](tables/release-coverage.csv)

### Upper departure / arrival: continuation and bounce long; fade and through short

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,670 | 7.59 [6.94, 8.26] / 5.00 | 9.37 [8.51, 10.35] / 5.50 | 9.37 [8.51, 10.35] / 5.50 | 7.59 [6.94, 8.26] / 5.00 | 1.15 [0.46, 1.88] | -1.15 [-1.88, -0.46] | 49.5% [47.2%, 51.9%] | 49.5% [47.2%, 51.9%] | 47.5% [45.2%, 50.1%] | 20 | 957 / 271 | 11 | adequate descriptive support |
| 2.0 | 10 | 1,653 | 10.82 [9.93, 11.80] / 6.75 | 12.46 [11.33, 13.81] / 7.50 | 12.46 [11.33, 13.81] / 7.50 | 10.82 [9.93, 11.80] / 6.75 | 0.97 [0.03, 2.01] | -0.97 [-2.01, -0.03] | 50.3% [48.1%, 52.6%] | 50.3% [48.1%, 52.6%] | 47.7% [45.3%, 50.1%] | 15 | 953 / 271 | 28 | adequate descriptive support |
| 2.0 | 15 | 1,632 | 13.49 [12.37, 14.70] / 8.25 | 14.86 [13.56, 16.41] / 9.38 | 14.86 [13.56, 16.41] / 9.38 | 13.49 [12.37, 14.70] / 8.25 | 1.16 [0.09, 2.35] | -1.16 [-2.35, -0.09] | 51.7% [49.4%, 54.2%] | 51.7% [49.4%, 54.2%] | 47.7% [45.1%, 50.3%] | 11 | 943 / 271 | 49 | adequate descriptive support |
| 2.0 | 20 | 1,608 | 15.26 [13.98, 16.63] / 9.25 | 17.04 [15.55, 18.77] / 10.75 | 17.04 [15.55, 18.77] / 10.75 | 15.26 [13.98, 16.63] / 9.25 | 1.55 [0.31, 2.87] | -1.55 [-2.87, -0.31] | 51.6% [49.0%, 54.3%] | 51.6% [49.0%, 54.3%] | 46.1% [43.8%, 48.3%] | 20 | 940 / 271 | 73 | adequate descriptive support |
| 2.0 | 50 | 1,461 | 24.18 [22.01, 26.66] / 15.25 | 24.98 [22.69, 27.49] / 16.00 | 24.98 [22.69, 27.49] / 16.00 | 24.18 [22.01, 26.66] / 15.25 | 1.02 [-1.25, 3.27] | -1.02 [-3.27, 1.25] | 51.9% [49.3%, 54.6%] | 51.9% [49.3%, 54.6%] | 49.0% [46.5%, 51.6%] | 7 | 909 / 270 | 220 | adequate descriptive support |
| 2.5 | 5 | 707 | 7.85 [6.95, 8.77] / 5.25 | 9.58 [8.53, 10.77] / 5.75 | 9.58 [8.53, 10.77] / 5.75 | 7.85 [6.95, 8.77] / 5.25 | 1.03 [0.02, 2.13] | -1.03 [-2.13, -0.02] | 49.5% [46.4%, 53.0%] | 49.5% [46.4%, 53.0%] | 48.9% [45.5%, 52.5%] | 5 | 545 / 254 | 8 | adequate descriptive support |
| 2.5 | 10 | 694 | 11.18 [9.87, 12.50] / 7.12 | 12.67 [11.30, 14.13] / 8.25 | 12.67 [11.30, 14.13] / 8.25 | 11.18 [9.87, 12.50] / 7.12 | 0.75 [-0.61, 2.13] | -0.75 [-2.13, 0.61] | 51.0% [47.8%, 54.4%] | 51.0% [47.8%, 54.4%] | 50.9% [47.2%, 54.5%] | 5 | 538 / 252 | 21 | adequate descriptive support |
| 2.5 | 15 | 683 | 13.90 [12.35, 15.57] / 8.50 | 15.18 [13.61, 16.83] / 9.50 | 15.18 [13.61, 16.83] / 9.50 | 13.90 [12.35, 15.57] / 8.50 | 1.20 [-0.48, 2.90] | -1.20 [-2.90, 0.48] | 50.8% [47.1%, 54.6%] | 50.8% [47.1%, 54.6%] | 46.3% [42.6%, 50.0%] | 7 | 531 / 251 | 32 | adequate descriptive support |
| 2.5 | 20 | 665 | 15.94 [14.15, 17.95] / 10.25 | 17.49 [15.75, 19.42] / 10.75 | 17.49 [15.75, 19.42] / 10.75 | 15.94 [14.15, 17.95] / 10.25 | 1.59 [-0.31, 3.46] | -1.59 [-3.46, 0.31] | 50.2% [46.4%, 54.1%] | 50.2% [46.4%, 54.1%] | 45.1% [41.2%, 48.9%] | 6 | 521 / 251 | 50 | adequate descriptive support |
| 2.5 | 50 | 589 | 25.18 [22.05, 28.47] / 15.25 | 24.82 [22.21, 27.66] / 15.75 | 24.82 [22.21, 27.66] / 15.75 | 25.18 [22.05, 28.47] / 15.25 | -0.67 [-4.04, 2.61] | 0.67 [-2.61, 4.04] | 48.4% [44.5%, 52.4%] | 48.4% [44.5%, 52.4%] | 52.6% [48.2%, 56.8%] | 3 | 478 / 244 | 126 | adequate descriptive support |
| 3.0 | 5 | 180 | 9.16 [7.50, 11.11] / 5.88 | 8.46 [7.06, 10.03] / 5.62 | 8.46 [7.06, 10.03] / 5.62 | 9.16 [7.50, 11.11] / 5.88 | -0.39 [-2.27, 1.58] | 0.39 [-1.58, 2.27] | 48.3% [41.2%, 55.8%] | 48.3% [41.2%, 55.8%] | 52.8% [45.9%, 60.4%] | 1 | 166 / 120 | 4 | adequate descriptive support |
| 3.0 | 10 | 179 | 12.48 [10.04, 15.01] / 7.50 | 11.72 [9.70, 14.07] / 7.00 | 11.72 [9.70, 14.07] / 7.00 | 12.48 [10.04, 15.01] / 7.50 | -1.24 [-3.91, 1.40] | 1.24 [-1.40, 3.91] | 44.7% [37.1%, 52.3%] | 44.7% [37.1%, 52.3%] | 44.1% [36.8%, 51.5%] | 3 | 165 / 119 | 5 | adequate descriptive support |
| 3.0 | 15 | 173 | 15.17 [12.50, 18.05] / 10.25 | 13.79 [11.50, 16.56] / 7.75 | 13.79 [11.50, 16.56] / 7.75 | 15.17 [12.50, 18.05] / 10.25 | -1.12 [-4.04, 1.81] | 1.12 [-1.81, 4.04] | 39.9% [32.8%, 47.2%] | 39.9% [32.8%, 47.2%] | 46.8% [39.6%, 54.1%] | 2 | 160 / 118 | 11 | adequate descriptive support |
| 3.0 | 20 | 170 | 17.24 [14.38, 20.33] / 12.38 | 16.15 [13.55, 19.29] / 9.25 | 16.15 [13.55, 19.29] / 9.25 | 17.24 [14.38, 20.33] / 12.38 | -0.78 [-3.92, 2.60] | 0.78 [-2.60, 3.92] | 43.5% [36.2%, 51.5%] | 43.5% [36.2%, 51.5%] | 51.8% [44.7%, 58.8%] | 1 | 158 / 116 | 14 | adequate descriptive support |
| 3.0 | 50 | 141 | 27.40 [22.74, 32.27] / 19.25 | 22.82 [18.44, 28.05] / 14.75 | 22.82 [18.44, 28.05] / 14.75 | 27.40 [22.74, 32.27] / 19.25 | -4.18 [-10.45, 2.34] | 4.18 [-2.34, 10.45] | 39.7% [32.0%, 47.9%] | 39.7% [32.0%, 47.9%] | 54.6% [47.2%, 62.0%] | 1 | 135 / 109 | 43 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,670 | 397 | 23.8% [21.8%, 25.8%] | 1,273 | 2.0 / 4.0 | 20 | 0 | 11 | 72 | 0 |
| 2.0 | 5 | frozen | 1,670 | 325 | 19.5% [17.6%, 21.4%] | 1,345 | 2.0 / 4.0 | 20 | 0 | 11 | 72 | 0 |
| 2.0 | 10 | evolving | 1,653 | 587 | 35.5% [33.2%, 37.6%] | 1,066 | 4.0 / 7.0 | 46 | 0 | 28 | 117 | 0 |
| 2.0 | 10 | frozen | 1,653 | 470 | 28.4% [26.1%, 30.6%] | 1,183 | 4.0 / 6.8 | 46 | 0 | 28 | 117 | 0 |
| 2.0 | 15 | evolving | 1,632 | 714 | 43.8% [41.5%, 45.8%] | 918 | 5.0 / 9.0 | 63 | 0 | 49 | 139 | 0 |
| 2.0 | 15 | frozen | 1,632 | 575 | 35.2% [33.1%, 37.3%] | 1,057 | 5.0 / 9.0 | 63 | 0 | 49 | 139 | 0 |
| 2.0 | 20 | evolving | 1,608 | 798 | 49.6% [47.3%, 51.8%] | 810 | 6.0 / 11.0 | 84 | 0 | 73 | 153 | 0 |
| 2.0 | 20 | frozen | 1,608 | 645 | 40.1% [37.8%, 42.3%] | 963 | 5.0 / 11.0 | 84 | 0 | 73 | 153 | 0 |
| 2.0 | 50 | evolving | 1,461 | 1,041 | 71.3% [69.0%, 73.3%] | 420 | 9.0 / 21.0 | 204 | 0 | 220 | 213 | 0 |
| 2.0 | 50 | frozen | 1,461 | 828 | 56.7% [54.2%, 59.1%] | 633 | 9.0 / 20.0 | 204 | 0 | 220 | 213 | 0 |
| 2.5 | 5 | evolving | 707 | 150 | 21.2% [18.3%, 24.1%] | 557 | 2.0 / 4.0 | 7 | 0 | 8 | 28 | 0 |
| 2.5 | 5 | frozen | 707 | 122 | 17.3% [14.6%, 20.0%] | 585 | 2.0 / 4.0 | 7 | 0 | 8 | 28 | 0 |
| 2.5 | 10 | evolving | 694 | 214 | 30.8% [27.9%, 33.8%] | 480 | 3.0 / 6.8 | 18 | 0 | 21 | 46 | 0 |
| 2.5 | 10 | frozen | 694 | 168 | 24.2% [21.3%, 27.1%] | 526 | 3.0 / 6.0 | 18 | 0 | 21 | 46 | 0 |
| 2.5 | 15 | evolving | 683 | 261 | 38.2% [34.8%, 41.6%] | 422 | 4.0 / 9.0 | 21 | 0 | 32 | 54 | 0 |
| 2.5 | 15 | frozen | 683 | 207 | 30.3% [27.0%, 33.6%] | 476 | 4.0 / 9.0 | 21 | 0 | 32 | 54 | 0 |
| 2.5 | 20 | evolving | 665 | 298 | 44.8% [41.1%, 48.5%] | 367 | 5.0 / 12.0 | 26 | 0 | 50 | 60 | 0 |
| 2.5 | 20 | frozen | 665 | 238 | 35.8% [32.3%, 39.4%] | 427 | 5.0 / 11.8 | 26 | 0 | 50 | 60 | 0 |
| 2.5 | 50 | evolving | 589 | 393 | 66.7% [63.3%, 70.2%] | 196 | 9.0 / 22.0 | 77 | 0 | 126 | 84 | 0 |
| 2.5 | 50 | frozen | 589 | 309 | 52.5% [48.4%, 56.4%] | 280 | 9.0 / 21.0 | 77 | 0 | 126 | 84 | 0 |
| 3.0 | 5 | evolving | 180 | 56 | 31.1% [24.5%, 38.3%] | 124 | 2.0 / 3.0 | 3 | 0 | 4 | 6 | 0 |
| 3.0 | 5 | frozen | 180 | 50 | 27.8% [21.5%, 34.6%] | 130 | 2.0 / 4.0 | 3 | 0 | 4 | 6 | 0 |
| 3.0 | 10 | evolving | 179 | 75 | 41.9% [34.6%, 49.6%] | 104 | 3.0 / 5.5 | 9 | 0 | 5 | 12 | 0 |
| 3.0 | 10 | frozen | 179 | 63 | 35.2% [28.4%, 42.1%] | 116 | 3.0 / 5.0 | 9 | 0 | 5 | 12 | 0 |
| 3.0 | 15 | evolving | 173 | 79 | 45.7% [38.1%, 53.5%] | 94 | 3.0 / 6.0 | 11 | 0 | 11 | 9 | 0 |
| 3.0 | 15 | frozen | 173 | 70 | 40.5% [33.3%, 47.8%] | 103 | 3.0 / 7.0 | 11 | 0 | 11 | 9 | 0 |
| 3.0 | 20 | evolving | 170 | 87 | 51.2% [43.4%, 58.9%] | 83 | 3.0 / 7.0 | 13 | 0 | 14 | 13 | 0 |
| 3.0 | 20 | frozen | 170 | 74 | 43.5% [36.1%, 51.2%] | 96 | 4.0 / 8.0 | 13 | 0 | 14 | 13 | 0 |
| 3.0 | 50 | evolving | 141 | 108 | 76.6% [69.7%, 83.2%] | 33 | 5.5 / 20.0 | 21 | 0 | 43 | 22 | 0 |
| 3.0 | 50 | frozen | 141 | 86 | 61.0% [53.3%, 68.5%] | 55 | 4.0 / 13.8 | 21 | 0 | 43 | 22 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,304 | 8.70 [7.98, 9.47] / 5.25 | 8.24 [7.47, 9.09] / 5.12 | 8.24 [7.47, 9.09] / 5.12 | 8.70 [7.98, 9.47] / 5.25 | 0.51 [-0.18, 1.21] | -0.51 [-1.21, 0.18] | 52.0% [49.1%, 54.8%] | 52.0% [49.1%, 54.8%] | 51.4% [48.8%, 54.2%] | 25 | 832 / 266 | 15 | adequate descriptive support | 521 / 527 / 180 / 76 | 0 |
| 2.0 | 10 | 1,290 | 12.25 [11.16, 13.42] / 7.00 | 11.83 [10.79, 13.05] / 7.25 | 11.83 [10.79, 13.05] / 7.25 | 12.25 [11.16, 13.42] / 7.00 | 0.77 [-0.19, 1.75] | -0.77 [-1.75, 0.19] | 54.0% [51.2%, 56.6%] | 54.0% [51.2%, 56.6%] | 50.9% [48.2%, 53.8%] | 13 | 829 / 266 | 29 | adequate descriptive support | 579 / 565 / 70 / 76 | 0 |
| 2.0 | 15 | 1,282 | 14.51 [13.20, 15.96] / 8.50 | 14.17 [12.89, 15.56] / 8.75 | 14.17 [12.89, 15.56] / 8.75 | 14.51 [13.20, 15.96] / 8.50 | 0.41 [-0.76, 1.60] | -0.41 [-1.60, 0.76] | 50.9% [48.2%, 53.8%] | 50.9% [48.2%, 53.8%] | 48.4% [45.7%, 51.0%] | 8 | 827 / 266 | 37 | adequate descriptive support | 594 / 580 / 32 / 76 | 0 |
| 2.0 | 20 | 1,262 | 16.56 [15.01, 18.22] / 9.50 | 16.30 [14.81, 17.89] / 10.25 | 16.30 [14.81, 17.89] / 10.25 | 16.56 [15.01, 18.22] / 9.50 | 0.59 [-0.80, 1.92] | -0.59 [-1.92, 0.80] | 51.5% [48.7%, 54.5%] | 51.5% [48.7%, 54.5%] | 48.6% [45.7%, 51.6%] | 6 | 823 / 266 | 57 | adequate descriptive support | 595 / 576 / 16 / 75 | 0 |
| 2.0 | 50 | 1,158 | 26.45 [23.73, 29.42] / 15.38 | 23.62 [21.50, 25.98] / 15.75 | 23.62 [21.50, 25.98] / 15.75 | 26.45 [23.73, 29.42] / 15.38 | -0.59 [-3.29, 2.02] | 0.59 [-2.02, 3.29] | 53.2% [50.0%, 56.4%] | 53.2% [50.0%, 56.4%] | 49.5% [46.7%, 52.3%] | 7 | 777 / 264 | 161 | adequate descriptive support | 543 / 538 / 3 / 74 | 0 |
| 2.5 | 5 | 499 | 9.10 [7.92, 10.42] / 5.50 | 8.58 [7.52, 9.77] / 5.25 | 8.58 [7.52, 9.77] / 5.25 | 9.10 [7.92, 10.42] / 5.50 | 0.41 [-0.82, 1.72] | -0.41 [-1.72, 0.82] | 52.7% [48.4%, 56.9%] | 52.7% [48.4%, 56.9%] | 48.3% [43.7%, 52.5%] | 10 | 401 / 227 | 8 | adequate descriptive support | 185 / 205 / 71 / 38 | 0 |
| 2.5 | 10 | 492 | 13.05 [11.20, 15.14] / 7.25 | 12.34 [10.82, 14.05] / 7.25 | 12.34 [10.82, 14.05] / 7.25 | 13.05 [11.20, 15.14] / 7.25 | 0.38 [-1.83, 2.43] | -0.38 [-2.43, 1.83] | 52.6% [48.3%, 57.1%] | 52.6% [48.3%, 57.1%] | 49.8% [45.3%, 54.3%] | 5 | 398 / 227 | 15 | adequate descriptive support | 201 / 221 / 32 / 38 | 0 |
| 2.5 | 15 | 488 | 15.63 [13.46, 18.06] / 8.75 | 14.67 [12.94, 16.67] / 8.75 | 14.67 [12.94, 16.67] / 8.75 | 15.63 [13.46, 18.06] / 8.75 | -0.24 [-2.59, 1.91] | 0.24 [-1.91, 2.59] | 48.2% [43.7%, 52.8%] | 48.2% [43.7%, 52.8%] | 50.2% [46.1%, 54.2%] | 3 | 395 / 226 | 19 | adequate descriptive support | 208 / 227 / 15 / 38 | 0 |
| 2.5 | 20 | 477 | 17.75 [15.40, 20.40] / 10.00 | 16.76 [14.82, 19.00] / 10.25 | 16.76 [14.82, 19.00] / 10.25 | 17.75 [15.40, 20.40] / 10.00 | -0.44 [-2.86, 2.00] | 0.44 [-2.00, 2.86] | 47.8% [43.4%, 52.2%] | 47.8% [43.4%, 52.2%] | 48.4% [44.4%, 52.8%] | 2 | 392 / 226 | 30 | adequate descriptive support | 207 / 226 / 7 / 37 | 0 |
| 2.5 | 50 | 433 | 28.81 [24.34, 33.64] / 16.50 | 23.63 [20.87, 26.77] / 15.50 | 23.63 [20.87, 26.77] / 15.50 | 28.81 [24.34, 33.64] / 16.50 | -3.02 [-7.57, 1.52] | 3.02 [-1.52, 7.57] | 50.8% [46.2%, 55.8%] | 50.8% [46.2%, 55.8%] | 49.4% [44.6%, 54.2%] | 3 | 361 / 215 | 74 | adequate descriptive support | 185 / 210 / 1 / 37 | 0 |
| 3.0 | 5 | 133 | 8.65 [7.06, 10.57] / 5.75 | 8.68 [6.87, 10.73] / 5.25 | 8.68 [6.87, 10.73] / 5.25 | 8.65 [7.06, 10.57] / 5.75 | 0.36 [-2.23, 2.74] | -0.36 [-2.74, 2.23] | 47.4% [39.0%, 55.8%] | 47.4% [39.0%, 55.8%] | 45.9% [36.7%, 54.3%] | 3 | 126 / 100 | 0 | adequate descriptive support | 48 / 56 / 11 / 18 | 0 |
| 3.0 | 10 | 130 | 12.48 [9.90, 15.55] / 7.62 | 12.51 [9.85, 15.79] / 7.25 | 12.51 [9.85, 15.79] / 7.25 | 12.48 [9.90, 15.55] / 7.62 | 0.32 [-3.46, 3.93] | -0.32 [-3.93, 3.46] | 46.9% [38.1%, 55.6%] | 46.9% [38.1%, 55.6%] | 47.7% [39.3%, 56.3%] | 0 | 123 / 100 | 3 | adequate descriptive support | 50 / 58 / 4 / 18 | 0 |
| 3.0 | 15 | 129 | 15.51 [12.47, 18.97] / 9.50 | 14.25 [11.40, 17.83] / 8.50 | 14.25 [11.40, 17.83] / 8.50 | 15.51 [12.47, 18.97] / 9.50 | -1.31 [-5.16, 2.75] | 1.31 [-2.75, 5.16] | 45.7% [36.9%, 55.0%] | 45.7% [36.9%, 55.0%] | 48.8% [39.9%, 58.4%] | 1 | 122 / 100 | 4 | adequate descriptive support | 52 / 59 / 0 / 18 | 0 |
| 3.0 | 20 | 126 | 18.16 [14.58, 22.28] / 11.00 | 16.95 [13.62, 20.93] / 10.00 | 16.95 [13.62, 20.93] / 10.00 | 18.16 [14.58, 22.28] / 11.00 | -1.59 [-6.23, 3.12] | 1.59 [-3.12, 6.23] | 42.1% [33.3%, 51.1%] | 42.1% [33.3%, 51.1%] | 44.4% [36.0%, 52.4%] | 1 | 122 / 100 | 7 | adequate descriptive support | 50 / 58 / 0 / 18 | 0 |
| 3.0 | 50 | 116 | 30.65 [23.22, 38.74] / 17.88 | 25.92 [20.72, 31.70] / 15.25 | 25.92 [20.72, 31.70] / 15.25 | 30.65 [23.22, 38.74] / 17.88 | -3.54 [-12.60, 5.08] | 3.54 [-5.08, 12.60] | 49.1% [39.3%, 58.9%] | 49.1% [39.3%, 58.9%] | 53.4% [43.4%, 62.8%] | 1 | 113 / 95 | 17 | adequate descriptive support | 46 / 52 / 0 / 18 | 0 |

### Lower departure / arrival: continuation and bounce short; fade and through long

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,670 | 9.20 [8.44, 10.03] / 6.00 | 10.83 [9.80, 11.97] / 6.25 | 10.83 [9.80, 11.97] / 6.25 | 9.20 [8.44, 10.03] / 6.00 | 0.31 [-0.43, 1.09] | -0.31 [-1.09, 0.43] | 47.4% [44.9%, 49.9%] | 51.3% [48.8%, 53.8%] | 49.0% [46.5%, 51.3%] | 22 | 921 / 271 | 13 | adequate descriptive support |
| 2.0 | 10 | 1,647 | 12.60 [11.58, 13.75] / 8.25 | 14.71 [13.34, 16.10] / 8.75 | 14.71 [13.34, 16.10] / 8.75 | 12.60 [11.58, 13.75] / 8.25 | 0.05 [-0.84, 0.98] | -0.05 [-0.98, 0.84] | 48.5% [46.2%, 50.9%] | 51.2% [48.9%, 53.5%] | 48.4% [46.0%, 50.8%] | 4 | 912 / 271 | 36 | adequate descriptive support |
| 2.0 | 15 | 1,622 | 15.08 [13.83, 16.48] / 9.50 | 18.05 [16.31, 19.76] / 10.25 | 18.05 [16.31, 19.76] / 10.25 | 15.08 [13.83, 16.48] / 9.50 | 0.91 [-0.31, 2.14] | -0.91 [-2.14, 0.31] | 48.3% [45.6%, 50.9%] | 50.7% [48.1%, 53.4%] | 48.6% [46.4%, 50.9%] | 16 | 907 / 271 | 61 | adequate descriptive support |
| 2.0 | 20 | 1,602 | 17.48 [15.97, 19.27] / 11.00 | 20.27 [18.43, 22.21] / 12.00 | 20.27 [18.43, 22.21] / 12.00 | 17.48 [15.97, 19.27] / 11.00 | 0.06 [-1.38, 1.49] | -0.06 [-1.49, 1.38] | 47.0% [44.5%, 49.6%] | 52.4% [49.7%, 55.0%] | 50.6% [48.5%, 52.7%] | 10 | 900 / 271 | 81 | adequate descriptive support |
| 2.0 | 50 | 1,476 | 26.44 [24.16, 29.00] / 17.25 | 29.94 [26.95, 33.15] / 17.75 | 29.94 [26.95, 33.15] / 17.75 | 26.44 [24.16, 29.00] / 17.25 | 0.03 [-2.21, 2.46] | -0.03 [-2.46, 2.21] | 45.7% [42.7%, 48.9%] | 54.1% [51.1%, 57.1%] | 47.0% [44.6%, 49.4%] | 2 | 872 / 271 | 207 | adequate descriptive support |
| 2.5 | 5 | 737 | 9.25 [8.37, 10.20] / 6.25 | 11.46 [10.07, 13.14] / 6.25 | 11.46 [10.07, 13.14] / 6.25 | 9.25 [8.37, 10.20] / 6.25 | 0.70 [-0.46, 1.96] | -0.70 [-1.96, 0.46] | 44.4% [40.6%, 48.2%] | 54.5% [50.9%, 58.2%] | 45.7% [42.0%, 49.4%] | 8 | 571 / 253 | 8 | adequate descriptive support |
| 2.5 | 10 | 719 | 13.00 [11.60, 14.45] / 8.25 | 14.82 [13.11, 16.69] / 8.75 | 14.82 [13.11, 16.69] / 8.75 | 13.00 [11.60, 14.45] / 8.25 | -0.54 [-2.13, 1.11] | 0.54 [-1.11, 2.13] | 43.9% [40.4%, 48.0%] | 55.5% [51.4%, 59.0%] | 48.7% [45.1%, 51.9%] | 4 | 561 / 251 | 26 | adequate descriptive support |
| 2.5 | 15 | 704 | 15.86 [14.13, 17.71] / 10.00 | 17.78 [15.77, 19.95] / 10.38 | 17.78 [15.77, 19.95] / 10.38 | 15.86 [14.13, 17.71] / 10.00 | -0.47 [-2.37, 1.46] | 0.47 [-1.46, 2.37] | 44.2% [40.1%, 48.2%] | 55.0% [51.0%, 59.0%] | 48.6% [45.1%, 52.3%] | 6 | 553 / 251 | 41 | adequate descriptive support |
| 2.5 | 20 | 692 | 18.24 [16.24, 20.48] / 11.50 | 20.01 [17.68, 22.56] / 11.50 | 20.01 [17.68, 22.56] / 11.50 | 18.24 [16.24, 20.48] / 11.50 | -0.93 [-2.97, 1.09] | 0.93 [-1.09, 2.97] | 46.5% [42.7%, 50.4%] | 53.0% [49.2%, 56.8%] | 49.7% [46.1%, 53.4%] | 3 | 547 / 250 | 53 | adequate descriptive support |
| 2.5 | 50 | 614 | 27.99 [25.10, 31.27] / 18.38 | 29.90 [26.15, 34.44] / 16.25 | 29.90 [26.15, 34.44] / 16.25 | 27.99 [25.10, 31.27] / 18.38 | -1.54 [-5.10, 2.25] | 1.54 [-2.25, 5.10] | 41.5% [37.6%, 45.6%] | 58.1% [54.0%, 62.1%] | 47.1% [43.3%, 50.9%] | 2 | 491 / 240 | 131 | adequate descriptive support |
| 3.0 | 5 | 175 | 8.75 [7.36, 10.28] / 5.75 | 13.04 [10.14, 16.61] / 6.50 | 13.04 [10.14, 16.61] / 6.50 | 8.75 [7.36, 10.28] / 5.75 | 2.71 [0.12, 5.60] | -2.71 [-5.60, -0.12] | 50.9% [43.5%, 58.6%] | 47.4% [39.7%, 54.9%] | 43.4% [36.2%, 50.8%] | 3 | 165 / 127 | 6 | adequate descriptive support |
| 3.0 | 10 | 171 | 12.26 [10.00, 14.84] / 7.50 | 16.54 [12.98, 20.61] / 9.75 | 16.54 [12.98, 20.61] / 9.75 | 12.26 [10.00, 14.84] / 7.50 | 0.38 [-3.33, 4.52] | -0.38 [-4.52, 3.33] | 45.0% [37.4%, 52.9%] | 55.0% [47.1%, 62.6%] | 49.7% [42.7%, 57.5%] | 0 | 161 / 125 | 10 | adequate descriptive support |
| 3.0 | 15 | 166 | 15.47 [12.83, 18.38] / 9.75 | 19.20 [15.26, 23.92] / 11.00 | 19.20 [15.26, 23.92] / 11.00 | 15.47 [12.83, 18.38] / 9.75 | -0.77 [-4.99, 3.78] | 0.77 [-3.78, 4.99] | 42.8% [35.1%, 50.7%] | 56.0% [47.8%, 63.7%] | 57.8% [50.0%, 65.7%] | 2 | 158 / 124 | 15 | adequate descriptive support |
| 3.0 | 20 | 164 | 18.53 [15.47, 21.98] / 11.50 | 20.85 [16.42, 25.88] / 11.00 | 20.85 [16.42, 25.88] / 11.00 | 18.53 [15.47, 21.98] / 11.50 | -2.41 [-6.50, 2.04] | 2.41 [-2.04, 6.50] | 40.9% [33.1%, 48.7%] | 58.5% [50.7%, 66.3%] | 56.1% [48.4%, 63.8%] | 1 | 156 / 122 | 17 | adequate descriptive support |
| 3.0 | 50 | 138 | 29.29 [24.71, 34.27] / 20.88 | 30.51 [22.69, 39.60] / 14.12 | 30.51 [22.69, 39.60] / 14.12 | 29.29 [24.71, 34.27] / 20.88 | -2.93 [-10.30, 5.45] | 2.93 [-5.45, 10.30] | 39.9% [31.9%, 49.1%] | 59.4% [50.0%, 67.5%] | 50.7% [43.2%, 58.8%] | 1 | 133 / 109 | 43 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,670 | 465 | 27.8% [25.8%, 30.0%] | 1,205 | 2.0 / 4.0 | 21 | 1 | 13 | 75 | 0 |
| 2.0 | 5 | frozen | 1,670 | 390 | 23.4% [21.3%, 25.5%] | 1,280 | 2.0 / 4.0 | 21 | 1 | 13 | 75 | 0 |
| 2.0 | 10 | evolving | 1,647 | 677 | 41.1% [38.8%, 43.4%] | 970 | 4.0 / 6.0 | 39 | 1 | 36 | 126 | 0 |
| 2.0 | 10 | frozen | 1,647 | 551 | 33.5% [31.1%, 35.8%] | 1,096 | 4.0 / 6.0 | 39 | 1 | 36 | 126 | 0 |
| 2.0 | 15 | evolving | 1,622 | 805 | 49.6% [47.3%, 51.9%] | 817 | 5.0 / 8.0 | 64 | 2 | 61 | 155 | 0 |
| 2.0 | 15 | frozen | 1,622 | 650 | 40.1% [37.6%, 42.5%] | 972 | 4.5 / 8.0 | 64 | 2 | 61 | 155 | 0 |
| 2.0 | 20 | evolving | 1,602 | 895 | 55.9% [53.5%, 58.1%] | 707 | 5.0 / 10.0 | 89 | 2 | 81 | 172 | 0 |
| 2.0 | 20 | frozen | 1,602 | 723 | 45.1% [42.6%, 47.5%] | 879 | 5.0 / 10.0 | 89 | 2 | 81 | 172 | 0 |
| 2.0 | 50 | evolving | 1,476 | 1,155 | 78.3% [76.4%, 80.0%] | 321 | 8.0 / 20.0 | 196 | 2 | 207 | 238 | 0 |
| 2.0 | 50 | frozen | 1,476 | 917 | 62.1% [59.7%, 64.6%] | 559 | 8.0 / 20.0 | 196 | 2 | 207 | 238 | 0 |
| 2.5 | 5 | evolving | 737 | 167 | 22.7% [19.8%, 25.7%] | 570 | 2.0 / 4.0 | 8 | 1 | 8 | 22 | 0 |
| 2.5 | 5 | frozen | 737 | 145 | 19.7% [16.8%, 22.6%] | 592 | 2.0 / 4.0 | 8 | 1 | 8 | 22 | 0 |
| 2.5 | 10 | evolving | 719 | 244 | 33.9% [30.5%, 37.3%] | 475 | 4.0 / 6.0 | 19 | 1 | 26 | 44 | 0 |
| 2.5 | 10 | frozen | 719 | 200 | 27.8% [24.5%, 30.9%] | 519 | 4.0 / 6.0 | 19 | 1 | 26 | 44 | 0 |
| 2.5 | 15 | evolving | 704 | 294 | 41.8% [38.2%, 45.1%] | 410 | 5.0 / 9.0 | 27 | 1 | 41 | 57 | 0 |
| 2.5 | 15 | frozen | 704 | 237 | 33.7% [30.3%, 36.9%] | 467 | 4.0 / 8.0 | 27 | 1 | 41 | 57 | 0 |
| 2.5 | 20 | evolving | 692 | 342 | 49.4% [46.0%, 52.7%] | 350 | 6.0 / 11.8 | 34 | 1 | 53 | 70 | 0 |
| 2.5 | 20 | frozen | 692 | 272 | 39.3% [36.0%, 42.6%] | 420 | 5.0 / 11.0 | 34 | 1 | 53 | 70 | 0 |
| 2.5 | 50 | evolving | 614 | 450 | 73.3% [70.2%, 76.4%] | 164 | 9.0 / 22.0 | 72 | 1 | 131 | 98 | 0 |
| 2.5 | 50 | frozen | 614 | 352 | 57.3% [53.7%, 61.0%] | 262 | 8.0 / 22.0 | 72 | 1 | 131 | 98 | 0 |
| 3.0 | 5 | evolving | 175 | 47 | 26.9% [20.4%, 33.3%] | 128 | 2.0 / 3.0 | 4 | 0 | 6 | 7 | 0 |
| 3.0 | 5 | frozen | 175 | 40 | 22.9% [16.3%, 29.3%] | 135 | 1.0 / 3.0 | 4 | 0 | 6 | 7 | 0 |
| 3.0 | 10 | evolving | 171 | 57 | 33.3% [26.5%, 40.4%] | 114 | 2.0 / 5.0 | 6 | 0 | 10 | 10 | 0 |
| 3.0 | 10 | frozen | 171 | 47 | 27.5% [20.7%, 34.4%] | 124 | 2.0 / 4.0 | 6 | 0 | 10 | 10 | 0 |
| 3.0 | 15 | evolving | 166 | 69 | 41.6% [33.8%, 48.9%] | 97 | 3.0 / 6.0 | 10 | 0 | 15 | 17 | 0 |
| 3.0 | 15 | frozen | 166 | 52 | 31.3% [24.1%, 38.7%] | 114 | 2.0 / 5.0 | 10 | 0 | 15 | 17 | 0 |
| 3.0 | 20 | evolving | 164 | 79 | 48.2% [39.9%, 55.7%] | 85 | 4.0 / 12.0 | 11 | 0 | 17 | 18 | 0 |
| 3.0 | 20 | frozen | 164 | 61 | 37.2% [29.6%, 44.9%] | 103 | 3.0 / 10.0 | 11 | 0 | 17 | 18 | 0 |
| 3.0 | 50 | evolving | 138 | 102 | 73.9% [65.9%, 80.9%] | 36 | 6.0 / 21.5 | 20 | 0 | 43 | 16 | 0 |
| 3.0 | 50 | frozen | 138 | 86 | 62.3% [53.0%, 71.0%] | 52 | 7.0 / 27.5 | 20 | 0 | 43 | 16 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,385 | 8.10 [7.44, 8.84] / 5.00 | 9.16 [8.23, 10.13] / 5.50 | 9.16 [8.23, 10.13] / 5.50 | 8.10 [7.44, 8.84] / 5.00 | 0.83 [0.19, 1.46] | -0.83 [-1.46, -0.19] | 50.0% [47.6%, 52.5%] | 48.2% [45.8%, 50.7%] | 47.4% [44.7%, 50.1%] | 25 | 832 / 269 | 19 | adequate descriptive support | 551 / 543 / 210 / 81 | 0 |
| 2.0 | 10 | 1,370 | 11.33 [10.34, 12.52] / 7.25 | 12.90 [11.62, 14.25] / 7.50 | 12.90 [11.62, 14.25] / 7.50 | 11.33 [10.34, 12.52] / 7.25 | 0.78 [-0.22, 1.68] | -0.78 [-1.68, 0.22] | 50.4% [47.7%, 53.1%] | 48.6% [45.9%, 51.3%] | 50.4% [47.5%, 53.1%] | 14 | 828 / 269 | 34 | adequate descriptive support | 603 / 589 / 97 / 81 | 0 |
| 2.0 | 15 | 1,348 | 13.79 [12.61, 15.22] / 8.75 | 15.59 [14.01, 17.24] / 9.75 | 15.59 [14.01, 17.24] / 9.75 | 13.79 [12.61, 15.22] / 8.75 | 0.64 [-0.59, 1.87] | -0.64 [-1.87, 0.59] | 49.6% [46.7%, 52.5%] | 49.4% [46.6%, 52.2%] | 50.9% [48.0%, 53.7%] | 13 | 819 / 268 | 56 | adequate descriptive support | 622 / 598 / 47 / 81 | 0 |
| 2.0 | 20 | 1,326 | 15.79 [14.46, 17.37] / 10.00 | 17.90 [16.11, 19.81] / 11.25 | 17.90 [16.11, 19.81] / 11.25 | 15.79 [14.46, 17.37] / 10.00 | 0.53 [-0.93, 2.02] | -0.53 [-2.02, 0.93] | 49.2% [46.2%, 52.1%] | 49.7% [46.7%, 52.7%] | 47.3% [44.8%, 49.9%] | 15 | 810 / 267 | 78 | adequate descriptive support | 621 / 589 / 35 / 81 | 0 |
| 2.0 | 50 | 1,212 | 24.90 [22.78, 27.23] / 16.00 | 26.95 [24.20, 29.94] / 17.00 | 26.95 [24.20, 29.94] / 17.00 | 24.90 [22.78, 27.23] / 16.00 | -0.21 [-2.55, 2.32] | 0.21 [-2.32, 2.55] | 45.1% [42.0%, 48.2%] | 54.1% [51.1%, 57.3%] | 48.8% [45.8%, 51.8%] | 9 | 776 / 266 | 192 | adequate descriptive support | 579 / 552 / 0 / 81 | 0 |
| 2.5 | 5 | 569 | 8.56 [7.62, 9.61] / 5.25 | 8.73 [7.80, 9.78] / 5.50 | 8.73 [7.80, 9.78] / 5.50 | 8.56 [7.62, 9.61] / 5.25 | 0.15 [-0.96, 1.21] | -0.15 [-1.21, 0.96] | 51.3% [47.4%, 55.5%] | 47.3% [43.2%, 51.3%] | 46.6% [42.8%, 50.4%] | 8 | 457 / 235 | 6 | adequate descriptive support | 212 / 226 / 100 / 31 | 0 |
| 2.5 | 10 | 559 | 12.46 [10.87, 14.32] / 7.75 | 11.91 [10.62, 13.37] / 7.50 | 11.91 [10.62, 13.37] / 7.50 | 12.46 [10.87, 14.32] / 7.75 | -1.32 [-2.98, 0.24] | 1.32 [-0.24, 2.98] | 47.6% [43.7%, 51.2%] | 51.5% [47.9%, 55.4%] | 53.8% [49.7%, 57.9%] | 5 | 450 / 235 | 16 | adequate descriptive support | 231 / 251 / 46 / 31 | 0 |
| 2.5 | 15 | 544 | 14.85 [13.03, 16.98] / 9.25 | 14.29 [12.73, 16.10] / 9.75 | 14.29 [12.73, 16.10] / 9.75 | 14.85 [13.03, 16.98] / 9.25 | -1.09 [-3.12, 0.73] | 1.09 [-0.73, 3.12] | 47.2% [43.1%, 51.3%] | 52.2% [48.2%, 56.4%] | 51.1% [46.6%, 55.5%] | 3 | 440 / 232 | 31 | adequate descriptive support | 242 / 250 / 21 / 31 | 0 |
| 2.5 | 20 | 534 | 16.93 [14.86, 19.29] / 10.75 | 16.33 [14.54, 18.34] / 11.25 | 16.33 [14.54, 18.34] / 11.25 | 16.93 [14.86, 19.29] / 10.75 | -0.91 [-3.04, 1.06] | 0.91 [-1.06, 3.04] | 48.7% [44.1%, 52.9%] | 50.2% [46.2%, 54.6%] | 45.9% [41.6%, 50.0%] | 6 | 433 / 228 | 41 | adequate descriptive support | 243 / 245 / 15 / 31 | 0 |
| 2.5 | 50 | 466 | 25.87 [22.83, 29.48] / 16.25 | 24.47 [21.47, 27.96] / 16.25 | 24.47 [21.47, 27.96] / 16.25 | 25.87 [22.83, 29.48] / 16.25 | -2.47 [-6.42, 1.23] | 2.47 [-1.23, 6.42] | 41.2% [36.6%, 45.8%] | 57.5% [53.0%, 62.1%] | 48.7% [44.0%, 53.3%] | 6 | 388 / 219 | 109 | adequate descriptive support | 213 / 222 / 0 / 31 | 0 |
| 3.0 | 5 | 131 | 8.62 [6.87, 10.60] / 5.00 | 8.79 [7.10, 10.44] / 6.00 | 8.79 [7.10, 10.44] / 6.00 | 8.62 [6.87, 10.60] / 5.00 | 0.02 [-2.28, 2.17] | -0.02 [-2.17, 2.28] | 52.7% [44.2%, 61.2%] | 45.8% [37.2%, 54.3%] | 49.6% [40.8%, 57.9%] | 2 | 126 / 103 | 1 | adequate descriptive support | 47 / 53 / 18 / 13 | 0 |
| 3.0 | 10 | 131 | 12.67 [10.01, 15.57] / 8.00 | 11.47 [9.31, 13.61] / 7.25 | 11.47 [9.31, 13.61] / 7.25 | 12.67 [10.01, 15.57] / 8.00 | -2.83 [-6.11, 0.18] | 2.83 [-0.18, 6.11] | 45.0% [36.3%, 53.3%] | 53.4% [45.0%, 62.8%] | 57.3% [49.3%, 64.9%] | 2 | 126 / 103 | 1 | adequate descriptive support | 51 / 59 / 8 / 13 | 0 |
| 3.0 | 15 | 125 | 15.45 [12.46, 18.85] / 9.00 | 13.16 [10.83, 15.54] / 9.75 | 13.16 [10.83, 15.54] / 9.75 | 15.45 [12.46, 18.85] / 9.00 | -3.41 [-7.18, 0.06] | 3.41 [-0.06, 7.18] | 43.2% [34.5%, 51.6%] | 56.8% [48.4%, 65.5%] | 55.2% [47.2%, 63.8%] | 0 | 120 / 98 | 7 | adequate descriptive support | 52 / 57 / 3 / 13 | 0 |
| 3.0 | 20 | 121 | 17.43 [14.25, 20.95] / 12.75 | 15.41 [12.65, 18.41] / 10.50 | 15.41 [12.65, 18.41] / 10.50 | 17.43 [14.25, 20.95] / 12.75 | -1.46 [-5.03, 2.12] | 1.46 [-2.12, 5.03] | 47.9% [38.4%, 57.1%] | 49.6% [40.8%, 58.6%] | 36.4% [28.7%, 44.4%] | 3 | 116 / 94 | 11 | adequate descriptive support | 50 / 55 / 3 / 13 | 0 |
| 3.0 | 50 | 107 | 28.28 [23.46, 33.12] / 19.75 | 22.27 [17.52, 27.57] / 13.50 | 22.27 [17.52, 27.57] / 13.50 | 28.28 [23.46, 33.12] / 19.75 | -5.25 [-11.34, 1.53] | 5.25 [-1.53, 11.34] | 38.3% [29.4%, 47.8%] | 61.7% [52.2%, 70.6%] | 47.7% [38.5%, 56.6%] | 0 | 103 / 87 | 25 | adequate descriptive support | 44 / 50 / 0 / 13 | 0 |

### Common cohort, distribution and year diagnostics

The horizon curves use the identical complete-50 cohort. Distribution quantiles and year diagnostics use each horizon’s eligible cohort. Year 2026 is partial. These diagnostics are descriptive on previously inspected history.

![NQ Asia return](figures/asia-NQ-return.svg)

![NQ Asia excursion](figures/asia-NQ-excursion.svg)

![NQ Asia endpoint](figures/asia-NQ-endpoint.svg)

![NQ Asia mae-mfe-distribution](figures/asia-NQ-mae-mfe-distribution.svg)

![NQ Asia terminal-distribution](figures/asia-NQ-terminal-distribution.svg)

![NQ Asia year-stability](figures/asia-NQ-year-stability.svg)

### Sensitivity and chronological periods at 10 candles

| Module | Scope | n | Days / weeks | Directional Δ [CI] | Return or bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- |
| departure | all | 3,300 | 1,165 / 273 | 0.51 [-0.09, 1.15] | 38.3% [36.6%, 39.9%] |
| departure | common_50 | 2,937 | 1,146 / 273 | 0.55 [-0.12, 1.24] | 42.2% [40.4%, 43.9%] |
| departure | age_ge30 | 2,230 | 1,099 / 273 | 0.69 [-0.01, 1.42] | 20.0% [18.2%, 21.9%] |
| departure | through_2023 | 1,616 | 564 / 131 | 0.22 [-0.40, 0.86] | 39.0% [36.6%, 41.3%] |
| departure | year_2024_period | 580 | 210 / 53 | 0.83 [-0.17, 1.89] | 37.6% [33.4%, 41.8%] |
| departure | years_2025_2026 | 1,104 | 391 / 90 | 0.78 [-0.69, 2.29] | 37.7% [34.8%, 40.5%] |
| touch | all | 2,660 | 1,101 / 272 | 0.77 [0.09, 1.45] | 52.1% [50.3%, 53.9%] |
| touch | common_50 | 2,370 | 1,070 / 272 | 0.62 [-0.05, 1.30] | 51.6% [49.7%, 53.6%] |
| touch | age_ge30 | 1,606 | 938 / 270 | 1.28 [0.48, 2.14] | 53.4% [51.1%, 55.8%] |
| touch | through_2023 | 1,314 | 538 / 131 | 0.30 [-0.50, 1.04] | 50.7% [47.9%, 53.5%] |
| touch | year_2024_period | 465 | 198 / 52 | -0.30 [-1.44, 0.95] | 49.0% [44.8%, 53.7%] |
| touch | years_2025_2026 | 881 | 365 / 90 | 2.04 [0.44, 3.60] | 55.8% [52.7%, 58.6%] |

### Deterministic source-path examples

Examples are the earliest stable ID in each prespecified class. They illustrate mechanisms and exclusions, not representative trade quality. The source table includes reference available_at and known sigma for every minute; charts plot raw one-minute high/low and references. Source minute open time relative to entry is shown; contacts have interval resolution. Lines join minute OHLC observations for display and do not imply intraminute order or trades through gaps. The 2-sigma envelope is plotted; 2.5/3-sigma references are retained in the example-path table.

return: NQ-asia-2021-06-29-P0019-K2-H10; lower side. Signal/confirmation 2021-06-28 20:40:00-04:00; entry 2021-06-28 20:40:00-04:00; deadline 2021-06-28 21:00:00-04:00 (New York time). Frozen sigma 1.85 points; signal VWAP 14,485.97. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-asia-2021-06-29-P0019-K2-H10](figures/example-asia-NQ-return.svg)

non_return: NQ-asia-2021-06-28-P0041-K2-H10; lower side. Signal/confirmation 2021-06-27 21:24:00-04:00; entry 2021-06-27 21:24:00-04:00; deadline 2021-06-27 21:44:00-04:00 (New York time). Frozen sigma 3.18 points; signal VWAP 14,343.35. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-asia-2021-06-28-P0041-K2-H10](figures/example-asia-NQ-non_return.svg)

bounce: NQ-asia-2021-06-28-P0041-T-H10; lower side. Signal/confirmation 2021-06-27 21:48:00-04:00; entry 2021-06-27 21:48:00-04:00; deadline 2021-06-27 22:08:00-04:00 (New York time). Frozen sigma 3.92 points; signal VWAP 14,342.00. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-asia-2021-06-28-P0041-T-H10](figures/example-asia-NQ-bounce.svg)

through: NQ-asia-2021-07-01-P0003-T-H10; lower side. Signal/confirmation 2021-06-30 20:12:00-04:00; entry 2021-06-30 20:12:00-04:00; deadline 2021-06-30 20:32:00-04:00 (New York time). Frozen sigma 1.12 points; signal VWAP 14,556.92. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-asia-2021-07-01-P0003-T-H10](figures/example-asia-NQ-through.svg)

ambiguity: NQ-asia-2021-08-10-P0006-T-H10; upper side. Signal/confirmation 2021-08-09 20:16:00-04:00; entry 2021-08-09 20:16:00-04:00; deadline 2021-08-09 20:36:00-04:00 (New York time). Frozen sigma 0.57 points; signal VWAP 15,120.12. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-asia-2021-08-10-P0006-T-H10](figures/example-asia-NQ-ambiguity.svg)

exclusion: NQ-asia-2021-06-29-P0203-K2-H10; lower side. Signal/confirmation 2021-06-29 02:48:00-04:00; entry 2021-06-29 02:48:00-04:00; deadline 2021-06-29 03:08:00-04:00 (New York time). Frozen sigma 3.58 points; signal VWAP 14,482.15. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: session_boundary.

![NQ-asia-2021-06-29-P0203-K2-H10](figures/example-asia-NQ-exclusion.svg)

## GC

Coverage: 825 retrospectively eligible dates, 2016-02-11 through 2026-09-18. All prices below are raw contract points. Full point/tick/sigma distributions and every tie numerator are saved in summary.csv.

### GC year coverage and retrospective exclusions

| Year | Candidate days | Eligible | Excluded |
| --- | --- | --- | --- |
| 2010 | 150 | 0 | 150 |
| 2011 | 260 | 0 | 260 |
| 2012 | 261 | 0 | 261 |
| 2013 | 261 | 0 | 261 |
| 2014 | 261 | 0 | 261 |
| 2015 | 261 | 0 | 261 |
| 2016 | 261 | 10 | 251 |
| 2017 | 260 | 55 | 205 |
| 2018 | 261 | 56 | 205 |
| 2019 | 261 | 83 | 178 |
| 2020 | 262 | 145 | 117 |
| 2021 | 261 | 73 | 188 |
| 2022 | 260 | 55 | 205 |
| 2023 | 260 | 35 | 225 |
| 2024 | 262 | 62 | 200 |
| 2025 | 261 | 165 | 96 |
| 2026 | 187 | 86 | 101 |

[Release exclusion reasons by product/year (reasons may overlap)](tables/release-coverage.csv)

### Upper departure / arrival: continuation and bounce long; fade and through short

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,241 | 1.75 [1.48, 2.10] / 0.80 | 2.00 [1.76, 2.26] / 1.00 | 2.00 [1.76, 2.26] / 1.00 | 1.75 [1.48, 2.10] / 0.80 | 0.18 [-0.06, 0.38] | -0.18 [-0.38, 0.06] | 49.9% [47.1%, 52.5%] | 49.9% [47.1%, 52.5%] | 47.6% [44.7%, 50.7%] | 48 | 674 / 330 | 8 | adequate descriptive support |
| 2.0 | 10 | 1,226 | 2.47 [2.14, 2.88] / 1.20 | 2.77 [2.43, 3.13] / 1.40 | 2.77 [2.43, 3.13] / 1.40 | 2.47 [2.14, 2.88] / 1.20 | 0.22 [-0.04, 0.47] | -0.22 [-0.47, 0.04] | 48.5% [45.9%, 51.2%] | 48.5% [45.9%, 51.2%] | 45.4% [42.7%, 48.3%] | 33 | 669 / 327 | 23 | adequate descriptive support |
| 2.0 | 15 | 1,215 | 3.11 [2.70, 3.60] / 1.50 | 3.36 [2.94, 3.80] / 1.70 | 3.36 [2.94, 3.80] / 1.70 | 3.11 [2.70, 3.60] / 1.50 | 0.23 [-0.10, 0.56] | -0.23 [-0.56, 0.10] | 49.7% [46.9%, 52.4%] | 49.7% [46.9%, 52.4%] | 46.5% [43.5%, 49.4%] | 28 | 665 / 326 | 34 | adequate descriptive support |
| 2.0 | 20 | 1,193 | 3.68 [3.19, 4.23] / 1.60 | 3.93 [3.43, 4.46] / 2.10 | 3.93 [3.43, 4.46] / 2.10 | 3.68 [3.19, 4.23] / 1.60 | 0.28 [-0.10, 0.68] | -0.28 [-0.68, 0.10] | 51.2% [48.0%, 54.4%] | 51.2% [48.0%, 54.4%] | 44.4% [41.7%, 47.3%] | 18 | 659 / 325 | 56 | adequate descriptive support |
| 2.0 | 50 | 1,113 | 6.04 [5.18, 7.02] / 2.90 | 6.26 [5.43, 7.25] / 3.20 | 6.26 [5.43, 7.25] / 3.20 | 6.04 [5.18, 7.02] / 2.90 | 0.37 [-0.32, 1.08] | -0.37 [-1.08, 0.32] | 53.0% [49.2%, 56.8%] | 53.0% [49.2%, 56.8%] | 48.2% [45.0%, 51.4%] | 14 | 641 / 320 | 136 | adequate descriptive support |
| 2.5 | 5 | 507 | 2.07 [1.55, 2.81] / 0.90 | 1.93 [1.65, 2.25] / 1.10 | 1.93 [1.65, 2.25] / 1.10 | 2.07 [1.55, 2.81] / 0.90 | -0.09 [-0.65, 0.36] | 0.09 [-0.36, 0.65] | 47.5% [42.5%, 52.2%] | 47.5% [42.5%, 52.2%] | 45.8% [41.6%, 50.2%] | 19 | 374 / 247 | 6 | adequate descriptive support |
| 2.5 | 10 | 502 | 2.81 [2.18, 3.64] / 1.30 | 2.73 [2.32, 3.14] / 1.50 | 2.73 [2.32, 3.14] / 1.50 | 2.81 [2.18, 3.64] / 1.30 | 0.02 [-0.50, 0.47] | -0.02 [-0.47, 0.50] | 47.2% [42.7%, 51.8%] | 47.2% [42.7%, 51.8%] | 42.2% [38.4%, 46.5%] | 18 | 369 / 242 | 11 | adequate descriptive support |
| 2.5 | 15 | 496 | 3.36 [2.68, 4.23] / 1.60 | 3.38 [2.85, 3.92] / 1.80 | 3.38 [2.85, 3.92] / 1.80 | 3.36 [2.68, 4.23] / 1.60 | 0.32 [-0.25, 0.91] | -0.32 [-0.91, 0.25] | 49.2% [44.8%, 53.5%] | 49.2% [44.8%, 53.5%] | 46.8% [42.6%, 51.1%] | 16 | 369 / 242 | 17 | adequate descriptive support |
| 2.5 | 20 | 491 | 3.82 [3.10, 4.71] / 1.80 | 4.13 [3.47, 4.86] / 2.10 | 4.13 [3.47, 4.86] / 2.10 | 3.82 [3.10, 4.71] / 1.80 | 0.48 [-0.09, 1.06] | -0.48 [-1.06, 0.09] | 51.1% [47.0%, 55.5%] | 51.1% [47.0%, 55.5%] | 45.8% [41.5%, 50.2%] | 4 | 368 / 242 | 22 | adequate descriptive support |
| 2.5 | 50 | 454 | 6.19 [4.92, 7.78] / 2.90 | 6.35 [5.20, 7.57] / 3.10 | 6.35 [5.20, 7.57] / 3.10 | 6.19 [4.92, 7.78] / 2.90 | 0.33 [-0.90, 1.61] | -0.33 [-1.61, 0.90] | 52.6% [47.0%, 58.2%] | 52.6% [47.0%, 58.2%] | 49.6% [44.9%, 54.4%] | 9 | 343 / 230 | 59 | adequate descriptive support |
| 3.0 | 5 | 114 | 1.55 [1.09, 2.18] / 0.90 | 1.62 [1.19, 2.12] / 0.85 | 1.62 [1.19, 2.12] / 0.85 | 1.55 [1.09, 2.18] / 0.90 | 0.30 [-0.24, 0.83] | -0.30 [-0.83, 0.24] | 52.6% [42.3%, 62.7%] | 52.6% [42.3%, 62.7%] | 47.4% [38.0%, 58.3%] | 4 | 96 / 85 | 0 | adequate descriptive support |
| 3.0 | 10 | 114 | 2.51 [1.68, 3.49] / 1.30 | 2.40 [1.82, 3.11] / 1.20 | 2.40 [1.82, 3.11] / 1.20 | 2.51 [1.68, 3.49] / 1.30 | -0.12 [-1.02, 0.68] | 0.12 [-0.68, 1.02] | 48.2% [39.3%, 57.9%] | 48.2% [39.3%, 57.9%] | 36.0% [27.1%, 44.9%] | 7 | 96 / 85 | 0 | adequate descriptive support |
| 3.0 | 15 | 113 | 2.83 [1.92, 3.91] / 1.50 | 2.97 [2.25, 3.83] / 1.70 | 2.97 [2.25, 3.83] / 1.70 | 2.83 [1.92, 3.91] / 1.50 | 0.15 [-0.76, 1.10] | -0.15 [-1.10, 0.76] | 47.8% [39.1%, 57.6%] | 47.8% [39.1%, 57.6%] | 43.4% [33.7%, 52.8%] | 4 | 95 / 84 | 1 | adequate descriptive support |
| 3.0 | 20 | 113 | 3.23 [2.23, 4.40] / 1.50 | 3.75 [2.67, 5.03] / 2.00 | 3.75 [2.67, 5.03] / 2.00 | 3.23 [2.23, 4.40] / 1.50 | 0.46 [-0.79, 1.83] | -0.46 [-1.83, 0.79] | 57.5% [47.4%, 67.3%] | 57.5% [47.4%, 67.3%] | 46.9% [37.8%, 55.6%] | 0 | 95 / 84 | 1 | adequate descriptive support |
| 3.0 | 50 | 107 | 4.87 [3.50, 6.58] / 2.50 | 5.83 [4.17, 7.73] / 3.10 | 5.83 [4.17, 7.73] / 3.10 | 4.87 [3.50, 6.58] / 2.50 | 1.33 [-0.43, 3.06] | -1.33 [-3.06, 0.43] | 59.8% [47.7%, 70.4%] | 59.8% [47.7%, 70.4%] | 45.8% [37.4%, 54.5%] | 0 | 89 / 80 | 7 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,241 | 368 | 29.7% [27.3%, 32.1%] | 873 | 2.0 / 3.0 | 4 | 0 | 8 | 65 | 0 |
| 2.0 | 5 | frozen | 1,241 | 303 | 24.4% [22.2%, 26.7%] | 938 | 2.0 / 3.0 | 4 | 0 | 8 | 65 | 0 |
| 2.0 | 10 | evolving | 1,226 | 523 | 42.7% [39.9%, 45.3%] | 703 | 3.0 / 6.0 | 11 | 0 | 23 | 84 | 0 |
| 2.0 | 10 | frozen | 1,226 | 439 | 35.8% [33.2%, 38.6%] | 787 | 3.0 / 6.0 | 11 | 0 | 23 | 84 | 0 |
| 2.0 | 15 | evolving | 1,215 | 629 | 51.8% [49.3%, 54.3%] | 586 | 4.0 / 9.0 | 18 | 0 | 34 | 129 | 0 |
| 2.0 | 15 | frozen | 1,215 | 500 | 41.2% [38.5%, 43.9%] | 715 | 4.0 / 7.0 | 18 | 0 | 34 | 129 | 0 |
| 2.0 | 20 | evolving | 1,193 | 706 | 59.2% [56.6%, 61.7%] | 487 | 5.0 / 11.0 | 23 | 0 | 56 | 155 | 0 |
| 2.0 | 20 | frozen | 1,193 | 551 | 46.2% [43.4%, 49.0%] | 642 | 5.0 / 10.0 | 23 | 0 | 56 | 155 | 0 |
| 2.0 | 50 | evolving | 1,113 | 848 | 76.2% [73.9%, 78.3%] | 265 | 7.0 / 17.0 | 55 | 0 | 136 | 160 | 0 |
| 2.0 | 50 | frozen | 1,113 | 688 | 61.8% [58.8%, 64.4%] | 425 | 6.0 / 17.0 | 55 | 0 | 136 | 160 | 0 |
| 2.5 | 5 | evolving | 507 | 145 | 28.6% [24.7%, 32.4%] | 362 | 2.0 / 4.0 | 2 | 0 | 6 | 25 | 0 |
| 2.5 | 5 | frozen | 507 | 120 | 23.7% [20.0%, 27.3%] | 387 | 2.0 / 3.0 | 2 | 0 | 6 | 25 | 0 |
| 2.5 | 10 | evolving | 502 | 203 | 40.4% [36.3%, 44.7%] | 299 | 3.0 / 6.0 | 5 | 0 | 11 | 37 | 0 |
| 2.5 | 10 | frozen | 502 | 166 | 33.1% [28.8%, 37.3%] | 336 | 3.0 / 6.0 | 5 | 0 | 11 | 37 | 0 |
| 2.5 | 15 | evolving | 496 | 241 | 48.6% [44.4%, 52.7%] | 255 | 4.0 / 8.0 | 7 | 0 | 17 | 55 | 0 |
| 2.5 | 15 | frozen | 496 | 186 | 37.5% [33.3%, 41.7%] | 310 | 3.0 / 7.0 | 7 | 0 | 17 | 55 | 0 |
| 2.5 | 20 | evolving | 491 | 271 | 55.2% [51.1%, 59.2%] | 220 | 5.0 / 10.5 | 8 | 0 | 22 | 62 | 0 |
| 2.5 | 20 | frozen | 491 | 209 | 42.6% [38.2%, 46.9%] | 282 | 5.0 / 9.0 | 8 | 0 | 22 | 62 | 0 |
| 2.5 | 50 | evolving | 454 | 330 | 72.7% [68.8%, 76.4%] | 124 | 7.0 / 16.0 | 23 | 0 | 59 | 60 | 0 |
| 2.5 | 50 | frozen | 454 | 270 | 59.5% [54.8%, 63.7%] | 184 | 7.0 / 19.8 | 23 | 0 | 59 | 60 | 0 |
| 3.0 | 5 | evolving | 114 | 46 | 40.4% [30.4%, 49.3%] | 68 | 1.0 / 3.0 | 2 | 0 | 0 | 5 | 0 |
| 3.0 | 5 | frozen | 114 | 41 | 36.0% [27.1%, 44.8%] | 73 | 1.0 / 2.0 | 2 | 0 | 0 | 5 | 0 |
| 3.0 | 10 | evolving | 114 | 60 | 52.6% [43.0%, 61.4%] | 54 | 2.0 / 5.0 | 2 | 0 | 0 | 7 | 0 |
| 3.0 | 10 | frozen | 114 | 53 | 46.5% [36.9%, 55.2%] | 61 | 2.0 / 5.0 | 2 | 0 | 0 | 7 | 0 |
| 3.0 | 15 | evolving | 113 | 67 | 59.3% [50.0%, 67.6%] | 46 | 3.0 / 6.0 | 2 | 0 | 1 | 12 | 0 |
| 3.0 | 15 | frozen | 113 | 55 | 48.7% [38.8%, 57.5%] | 58 | 2.0 / 5.5 | 2 | 0 | 1 | 12 | 0 |
| 3.0 | 20 | evolving | 113 | 69 | 61.1% [52.3%, 69.2%] | 44 | 3.0 / 7.0 | 2 | 0 | 1 | 10 | 0 |
| 3.0 | 20 | frozen | 113 | 59 | 52.2% [42.2%, 61.1%] | 54 | 2.0 / 6.0 | 2 | 0 | 1 | 10 | 0 |
| 3.0 | 50 | evolving | 107 | 81 | 75.7% [67.0%, 83.5%] | 26 | 4.0 / 12.0 | 6 | 0 | 7 | 13 | 0 |
| 3.0 | 50 | frozen | 107 | 68 | 63.6% [53.1%, 73.0%] | 39 | 3.0 / 8.2 | 6 | 0 | 7 | 13 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,025 | 2.04 [1.72, 2.43] / 0.90 | 1.81 [1.57, 2.07] / 0.90 | 1.81 [1.57, 2.07] / 0.90 | 2.04 [1.72, 2.43] / 0.90 | -0.02 [-0.28, 0.22] | 0.02 [-0.22, 0.28] | 49.9% [46.9%, 52.9%] | 49.9% [46.9%, 52.9%] | 44.5% [41.5%, 47.4%] | 33 | 602 / 313 | 9 | adequate descriptive support | 421 / 406 / 140 / 58 | 0 |
| 2.0 | 10 | 1,014 | 2.74 [2.35, 3.19] / 1.20 | 2.60 [2.24, 2.98] / 1.30 | 2.60 [2.24, 2.98] / 1.30 | 2.74 [2.35, 3.19] / 1.20 | 0.02 [-0.28, 0.30] | -0.02 [-0.30, 0.28] | 53.2% [50.0%, 56.2%] | 53.2% [50.0%, 56.2%] | 46.5% [43.6%, 49.5%] | 24 | 600 / 313 | 20 | adequate descriptive support | 456 / 430 / 70 / 58 | 0 |
| 2.0 | 15 | 1,002 | 3.37 [2.91, 3.89] / 1.60 | 3.21 [2.77, 3.66] / 1.60 | 3.21 [2.77, 3.66] / 1.60 | 3.37 [2.91, 3.89] / 1.60 | 0.06 [-0.33, 0.44] | -0.06 [-0.44, 0.33] | 50.0% [46.7%, 53.2%] | 50.0% [46.7%, 53.2%] | 45.3% [42.3%, 48.2%] | 22 | 597 / 312 | 32 | adequate descriptive support | 463 / 436 / 45 / 58 | 0 |
| 2.0 | 20 | 993 | 3.90 [3.38, 4.49] / 1.90 | 3.73 [3.21, 4.30] / 1.90 | 3.73 [3.21, 4.30] / 1.90 | 3.90 [3.38, 4.49] / 1.90 | 0.13 [-0.30, 0.58] | -0.13 [-0.58, 0.30] | 50.6% [47.1%, 53.9%] | 50.6% [47.1%, 53.9%] | 45.6% [42.5%, 48.6%] | 16 | 596 / 311 | 41 | adequate descriptive support | 471 / 438 / 26 / 58 | 0 |
| 2.0 | 50 | 917 | 6.18 [5.32, 7.19] / 3.20 | 5.79 [4.95, 6.76] / 2.90 | 5.79 [4.95, 6.76] / 2.90 | 6.18 [5.32, 7.19] / 3.20 | 0.13 [-0.60, 0.89] | -0.13 [-0.89, 0.60] | 50.3% [46.3%, 54.3%] | 50.3% [46.3%, 54.3%] | 47.7% [44.4%, 51.0%] | 7 | 568 / 302 | 117 | adequate descriptive support | 439 / 417 / 3 / 58 | 0 |
| 2.5 | 5 | 406 | 2.08 [1.64, 2.64] / 0.90 | 1.72 [1.42, 2.05] / 0.90 | 1.72 [1.42, 2.05] / 0.90 | 2.08 [1.64, 2.64] / 0.90 | -0.06 [-0.49, 0.31] | 0.06 [-0.31, 0.49] | 51.0% [46.1%, 55.9%] | 51.0% [46.1%, 55.9%] | 45.3% [40.7%, 50.1%] | 11 | 313 / 216 | 2 | adequate descriptive support | 161 / 168 / 55 / 22 | 0 |
| 2.5 | 10 | 401 | 2.68 [2.16, 3.31] / 1.20 | 2.50 [2.08, 2.96] / 1.40 | 2.50 [2.08, 2.96] / 1.40 | 2.68 [2.16, 3.31] / 1.20 | 0.07 [-0.33, 0.45] | -0.07 [-0.45, 0.33] | 53.1% [48.4%, 58.3%] | 53.1% [48.4%, 58.3%] | 48.6% [44.0%, 53.4%] | 14 | 310 / 214 | 7 | adequate descriptive support | 173 / 175 / 31 / 22 | 0 |
| 2.5 | 15 | 395 | 3.31 [2.72, 3.98] / 1.50 | 3.16 [2.61, 3.77] / 1.60 | 3.16 [2.61, 3.77] / 1.60 | 3.31 [2.72, 3.98] / 1.50 | 0.07 [-0.48, 0.61] | -0.07 [-0.61, 0.48] | 48.6% [43.4%, 53.4%] | 48.6% [43.4%, 53.4%] | 49.1% [44.4%, 53.8%] | 8 | 305 / 211 | 13 | adequate descriptive support | 175 / 179 / 19 / 22 | 0 |
| 2.5 | 20 | 392 | 3.88 [3.20, 4.65] / 1.90 | 3.75 [3.06, 4.55] / 1.90 | 3.75 [3.06, 4.55] / 1.90 | 3.88 [3.20, 4.65] / 1.90 | 0.11 [-0.54, 0.75] | -0.11 [-0.75, 0.54] | 47.7% [42.2%, 52.7%] | 47.7% [42.2%, 52.7%] | 45.7% [40.8%, 50.3%] | 7 | 304 / 211 | 16 | adequate descriptive support | 177 / 182 / 11 / 22 | 0 |
| 2.5 | 50 | 362 | 6.32 [5.07, 7.92] / 3.15 | 5.58 [4.57, 6.84] / 2.80 | 5.58 [4.57, 6.84] / 2.80 | 6.32 [5.07, 7.92] / 3.15 | -0.32 [-1.57, 0.80] | 0.32 [-0.80, 1.57] | 50.6% [44.6%, 56.3%] | 50.6% [44.6%, 56.3%] | 45.3% [39.9%, 50.8%] | 1 | 286 / 203 | 46 | adequate descriptive support | 165 / 174 / 1 / 22 | 0 |
| 3.0 | 5 | 95 | 1.69 [1.06, 2.47] / 0.60 | 1.34 [0.98, 1.74] / 0.70 | 1.34 [0.98, 1.74] / 0.70 | 1.69 [1.06, 2.47] / 0.60 | -0.31 [-1.08, 0.32] | 0.31 [-0.32, 1.08] | 53.7% [43.2%, 64.5%] | 53.7% [43.2%, 64.5%] | 41.1% [30.5%, 51.1%] | 0 | 78 / 72 | 1 | events_below_100 | 36 / 44 / 7 / 8 | 0 |
| 3.0 | 10 | 92 | 2.27 [1.50, 3.15] / 0.80 | 1.86 [1.40, 2.39] / 1.10 | 1.86 [1.40, 2.39] / 1.10 | 2.27 [1.50, 3.15] / 0.80 | -0.31 [-1.14, 0.39] | 0.31 [-0.39, 1.14] | 54.3% [42.6%, 66.2%] | 54.3% [42.6%, 66.2%] | 53.3% [43.3%, 63.4%] | 3 | 75 / 70 | 4 | events_below_100 | 36 / 44 / 4 / 8 | 0 |
| 3.0 | 15 | 92 | 2.90 [1.92, 4.11] / 1.15 | 2.39 [1.83, 2.95] / 1.50 | 2.39 [1.83, 2.95] / 1.50 | 2.90 [1.92, 4.11] / 1.15 | -0.37 [-1.46, 0.53] | 0.37 [-0.53, 1.46] | 48.9% [39.1%, 58.8%] | 48.9% [39.1%, 58.8%] | 52.2% [40.9%, 61.9%] | 2 | 75 / 70 | 4 | events_below_100 | 37 / 45 / 2 / 8 | 0 |
| 3.0 | 20 | 91 | 3.37 [2.32, 4.67] / 1.50 | 2.87 [2.20, 3.51] / 2.00 | 2.87 [2.20, 3.51] / 2.00 | 3.37 [2.32, 4.67] / 1.50 | -0.23 [-1.31, 0.75] | 0.23 [-0.75, 1.31] | 47.3% [36.5%, 57.6%] | 47.3% [36.5%, 57.6%] | 44.0% [33.3%, 54.0%] | 3 | 75 / 70 | 5 | events_below_100 | 37 / 45 / 1 / 8 | 0 |
| 3.0 | 50 | 83 | 4.61 [3.25, 6.39] / 2.20 | 5.02 [3.63, 6.71] / 3.50 | 5.02 [3.63, 6.71] / 3.50 | 4.61 [3.25, 6.39] / 2.20 | 0.97 [-0.81, 2.65] | -0.97 [-2.65, 0.81] | 60.2% [48.3%, 70.4%] | 60.2% [48.3%, 70.4%] | 34.9% [25.0%, 45.4%] | 1 | 69 / 65 | 13 | events_below_100 | 34 / 41 / 0 / 8 | 0 |

### Lower departure / arrival: continuation and bounce short; fade and through long

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,184 | 1.88 [1.61, 2.17] / 0.90 | 2.59 [2.05, 3.26] / 1.00 | 2.59 [2.05, 3.26] / 1.00 | 1.88 [1.61, 2.17] / 0.90 | 0.28 [-0.03, 0.65] | -0.28 [-0.65, 0.03] | 46.2% [43.4%, 49.0%] | 49.9% [47.3%, 52.7%] | 45.3% [42.3%, 48.1%] | 46 | 653 / 332 | 6 | adequate descriptive support |
| 2.0 | 10 | 1,175 | 2.48 [2.14, 2.84] / 1.20 | 3.51 [2.81, 4.40] / 1.30 | 3.51 [2.81, 4.40] / 1.30 | 2.48 [2.14, 2.84] / 1.20 | 0.46 [0.07, 0.90] | -0.46 [-0.90, -0.07] | 49.5% [46.7%, 52.4%] | 48.0% [45.2%, 50.9%] | 47.6% [44.6%, 50.5%] | 29 | 653 / 332 | 15 | adequate descriptive support |
| 2.0 | 15 | 1,163 | 3.08 [2.64, 3.55] / 1.50 | 4.25 [3.45, 5.27] / 1.60 | 4.25 [3.45, 5.27] / 1.60 | 3.08 [2.64, 3.55] / 1.50 | 0.26 [-0.15, 0.69] | -0.26 [-0.69, 0.15] | 46.2% [43.3%, 49.2%] | 51.9% [49.0%, 54.8%] | 45.5% [42.5%, 48.5%] | 22 | 653 / 332 | 27 | adequate descriptive support |
| 2.0 | 20 | 1,145 | 3.55 [3.03, 4.10] / 1.70 | 4.85 [3.94, 5.97] / 1.90 | 4.85 [3.94, 5.97] / 1.90 | 3.55 [3.03, 4.10] / 1.70 | 0.23 [-0.19, 0.66] | -0.23 [-0.66, 0.19] | 48.0% [45.1%, 51.3%] | 49.7% [46.4%, 52.5%] | 44.5% [41.4%, 47.6%] | 26 | 651 / 332 | 45 | adequate descriptive support |
| 2.0 | 50 | 1,055 | 5.73 [4.84, 6.65] / 2.70 | 6.88 [5.66, 8.45] / 3.00 | 6.88 [5.66, 8.45] / 3.00 | 5.73 [4.84, 6.65] / 2.70 | -0.12 [-0.83, 0.62] | 0.12 [-0.62, 0.83] | 47.3% [43.4%, 51.1%] | 51.1% [47.2%, 54.9%] | 46.3% [43.2%, 49.2%] | 17 | 627 / 326 | 135 | adequate descriptive support |
| 2.5 | 5 | 499 | 1.99 [1.58, 2.46] / 0.90 | 3.16 [2.18, 4.53] / 1.00 | 3.16 [2.18, 4.53] / 1.00 | 1.99 [1.58, 2.46] / 0.90 | 0.36 [-0.17, 0.98] | -0.36 [-0.98, 0.17] | 48.3% [43.6%, 53.1%] | 47.9% [43.3%, 52.7%] | 49.1% [44.4%, 53.9%] | 19 | 376 / 248 | 3 | adequate descriptive support |
| 2.5 | 10 | 494 | 2.54 [2.07, 3.06] / 1.40 | 3.98 [2.90, 5.47] / 1.40 | 3.98 [2.90, 5.47] / 1.40 | 2.54 [2.07, 3.06] / 1.40 | 0.51 [0.02, 1.07] | -0.51 [-1.07, -0.02] | 49.0% [44.5%, 53.7%] | 48.8% [44.3%, 53.2%] | 48.8% [44.9%, 53.0%] | 11 | 373 / 246 | 8 | adequate descriptive support |
| 2.5 | 15 | 488 | 3.13 [2.56, 3.76] / 1.60 | 4.88 [3.65, 6.50] / 1.65 | 4.88 [3.65, 6.50] / 1.65 | 3.13 [2.56, 3.76] / 1.60 | 0.40 [-0.19, 1.11] | -0.40 [-1.11, 0.19] | 47.5% [42.9%, 52.3%] | 49.8% [44.8%, 54.4%] | 44.9% [40.4%, 49.2%] | 13 | 371 / 246 | 14 | adequate descriptive support |
| 2.5 | 20 | 475 | 3.52 [2.89, 4.22] / 1.70 | 5.73 [4.25, 7.68] / 1.90 | 5.73 [4.25, 7.68] / 1.90 | 3.52 [2.89, 4.22] / 1.70 | 0.63 [-0.11, 1.50] | -0.63 [-1.50, 0.11] | 48.8% [44.7%, 53.5%] | 49.3% [44.5%, 53.7%] | 40.0% [35.4%, 44.8%] | 9 | 363 / 242 | 27 | adequate descriptive support |
| 2.5 | 50 | 423 | 5.67 [4.55, 6.86] / 2.80 | 7.74 [5.62, 10.87] / 3.00 | 7.74 [5.62, 10.87] / 3.00 | 5.67 [4.55, 6.86] / 2.80 | -0.00 [-1.14, 1.20] | 0.00 [-1.20, 1.14] | 47.3% [42.4%, 52.5%] | 51.1% [45.9%, 56.1%] | 48.5% [43.8%, 53.0%] | 7 | 333 / 228 | 79 | adequate descriptive support |
| 3.0 | 5 | 116 | 1.64 [1.18, 2.16] / 0.85 | 2.70 [1.82, 3.90] / 0.95 | 2.70 [1.82, 3.90] / 0.95 | 1.64 [1.18, 2.16] / 0.85 | 0.73 [-0.12, 1.83] | -0.73 [-1.83, 0.12] | 51.7% [42.3%, 60.9%] | 46.6% [37.5%, 55.9%] | 44.8% [35.6%, 53.6%] | 2 | 104 / 93 | 0 | adequate descriptive support |
| 3.0 | 10 | 113 | 2.39 [1.67, 3.18] / 1.10 | 3.22 [2.24, 4.57] / 1.30 | 3.22 [2.24, 4.57] / 1.30 | 2.39 [1.67, 3.18] / 1.10 | 0.04 [-0.71, 0.87] | -0.04 [-0.87, 0.71] | 44.2% [35.2%, 53.6%] | 53.1% [43.8%, 61.9%] | 45.1% [36.2%, 54.5%] | 3 | 101 / 91 | 3 | adequate descriptive support |
| 3.0 | 15 | 111 | 3.09 [2.08, 4.24] / 1.40 | 4.19 [2.86, 5.76] / 1.40 | 4.19 [2.86, 5.76] / 1.40 | 3.09 [2.08, 4.24] / 1.40 | -0.02 [-1.17, 1.17] | 0.02 [-1.17, 1.17] | 39.6% [31.0%, 48.3%] | 56.8% [47.8%, 65.5%] | 41.4% [32.5%, 50.0%] | 4 | 100 / 91 | 5 | adequate descriptive support |
| 3.0 | 20 | 109 | 3.55 [2.39, 4.83] / 1.60 | 4.89 [3.35, 6.71] / 1.50 | 4.89 [3.35, 6.71] / 1.50 | 3.55 [2.39, 4.83] / 1.60 | -0.30 [-1.55, 0.95] | 0.30 [-0.95, 1.55] | 43.1% [34.7%, 52.2%] | 55.0% [45.6%, 63.7%] | 40.4% [30.8%, 50.5%] | 2 | 98 / 89 | 7 | adequate descriptive support |
| 3.0 | 50 | 97 | 6.00 [4.31, 7.73] / 2.80 | 8.01 [4.92, 12.96] / 2.70 | 8.01 [4.92, 12.96] / 2.70 | 6.00 [4.31, 7.73] / 2.80 | 1.01 [-2.17, 6.06] | -1.01 [-6.06, 2.17] | 42.3% [32.3%, 52.2%] | 56.7% [46.6%, 66.7%] | 51.5% [41.6%, 61.3%] | 1 | 88 / 81 | 19 | events_below_100 |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,184 | 365 | 30.8% [28.2%, 33.6%] | 819 | 3.0 / 4.0 | 3 | 0 | 6 | 60 | 0 |
| 2.0 | 5 | frozen | 1,184 | 305 | 25.8% [23.2%, 28.4%] | 879 | 2.0 / 4.0 | 3 | 0 | 6 | 60 | 0 |
| 2.0 | 10 | evolving | 1,175 | 509 | 43.3% [40.6%, 46.1%] | 666 | 4.0 / 6.0 | 13 | 0 | 15 | 100 | 1 |
| 2.0 | 10 | frozen | 1,175 | 410 | 34.9% [32.1%, 37.7%] | 765 | 3.0 / 6.0 | 13 | 0 | 15 | 100 | 1 |
| 2.0 | 15 | evolving | 1,163 | 611 | 52.5% [49.9%, 55.1%] | 552 | 4.0 / 8.0 | 17 | 0 | 27 | 144 | 1 |
| 2.0 | 15 | frozen | 1,163 | 468 | 40.2% [37.3%, 43.2%] | 695 | 4.0 / 7.0 | 17 | 0 | 27 | 144 | 1 |
| 2.0 | 20 | evolving | 1,145 | 669 | 58.4% [55.8%, 60.9%] | 476 | 5.0 / 10.0 | 22 | 0 | 45 | 143 | 0 |
| 2.0 | 20 | frozen | 1,145 | 526 | 45.9% [42.9%, 49.1%] | 619 | 4.0 / 10.0 | 22 | 0 | 45 | 143 | 0 |
| 2.0 | 50 | evolving | 1,055 | 824 | 78.1% [75.8%, 80.4%] | 231 | 7.0 / 17.0 | 33 | 0 | 135 | 173 | 0 |
| 2.0 | 50 | frozen | 1,055 | 651 | 61.7% [58.9%, 64.7%] | 404 | 6.0 / 18.0 | 33 | 0 | 135 | 173 | 0 |
| 2.5 | 5 | evolving | 499 | 124 | 24.8% [21.0%, 28.7%] | 375 | 3.0 / 4.0 | 2 | 0 | 3 | 22 | 0 |
| 2.5 | 5 | frozen | 499 | 102 | 20.4% [16.8%, 24.2%] | 397 | 2.0 / 4.0 | 2 | 0 | 3 | 22 | 0 |
| 2.5 | 10 | evolving | 494 | 183 | 37.0% [32.8%, 41.2%] | 311 | 4.0 / 6.0 | 7 | 0 | 8 | 38 | 0 |
| 2.5 | 10 | frozen | 494 | 145 | 29.4% [25.2%, 33.6%] | 349 | 4.0 / 6.0 | 7 | 0 | 8 | 38 | 0 |
| 2.5 | 15 | evolving | 488 | 226 | 46.3% [42.0%, 50.7%] | 262 | 5.0 / 9.0 | 10 | 0 | 14 | 53 | 0 |
| 2.5 | 15 | frozen | 488 | 173 | 35.5% [30.9%, 39.9%] | 315 | 5.0 / 8.0 | 10 | 0 | 14 | 53 | 0 |
| 2.5 | 20 | evolving | 475 | 255 | 53.7% [49.4%, 57.7%] | 220 | 6.0 / 11.5 | 11 | 0 | 27 | 63 | 0 |
| 2.5 | 20 | frozen | 475 | 192 | 40.4% [35.7%, 45.1%] | 283 | 5.0 / 10.0 | 11 | 0 | 27 | 63 | 0 |
| 2.5 | 50 | evolving | 423 | 316 | 74.7% [70.6%, 78.6%] | 107 | 8.0 / 18.0 | 15 | 0 | 79 | 76 | 0 |
| 2.5 | 50 | frozen | 423 | 240 | 56.7% [51.6%, 61.6%] | 183 | 7.0 / 19.0 | 15 | 0 | 79 | 76 | 0 |
| 3.0 | 5 | evolving | 116 | 37 | 31.9% [24.3%, 39.7%] | 79 | 2.0 / 4.0 | 1 | 0 | 0 | 4 | 0 |
| 3.0 | 5 | frozen | 116 | 33 | 28.4% [21.2%, 35.6%] | 83 | 1.0 / 4.0 | 1 | 0 | 0 | 4 | 0 |
| 3.0 | 10 | evolving | 113 | 54 | 47.8% [38.9%, 57.0%] | 59 | 3.5 / 6.0 | 4 | 0 | 3 | 10 | 0 |
| 3.0 | 10 | frozen | 113 | 44 | 38.9% [30.7%, 47.2%] | 69 | 3.0 / 5.2 | 4 | 0 | 3 | 10 | 0 |
| 3.0 | 15 | evolving | 111 | 66 | 59.5% [50.5%, 68.1%] | 45 | 4.5 / 8.8 | 6 | 0 | 5 | 14 | 0 |
| 3.0 | 15 | frozen | 111 | 52 | 46.8% [38.3%, 55.3%] | 59 | 4.0 / 7.0 | 6 | 0 | 5 | 14 | 0 |
| 3.0 | 20 | evolving | 109 | 71 | 65.1% [56.6%, 73.4%] | 38 | 5.0 / 10.5 | 6 | 0 | 7 | 15 | 0 |
| 3.0 | 20 | frozen | 109 | 56 | 51.4% [42.6%, 59.8%] | 53 | 4.0 / 8.2 | 6 | 0 | 7 | 15 | 0 |
| 3.0 | 50 | evolving | 97 | 80 | 82.5% [74.5%, 89.8%] | 17 | 6.0 / 13.0 | 7 | 0 | 19 | 11 | 0 |
| 3.0 | 50 | frozen | 97 | 69 | 71.1% [61.7%, 79.8%] | 28 | 6.0 / 16.0 | 7 | 0 | 19 | 11 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 997 | 1.66 [1.42, 1.94] / 0.80 | 1.76 [1.48, 2.06] / 0.80 | 1.76 [1.48, 2.06] / 0.80 | 1.66 [1.42, 1.94] / 0.80 | 0.04 [-0.17, 0.26] | -0.04 [-0.26, 0.17] | 48.2% [45.1%, 51.3%] | 48.8% [45.7%, 52.1%] | 43.9% [40.9%, 46.9%] | 29 | 601 / 317 | 7 | adequate descriptive support | 380 / 392 / 169 / 56 | 0 |
| 2.0 | 10 | 984 | 2.37 [2.01, 2.79] / 1.10 | 2.57 [2.14, 3.03] / 1.20 | 2.57 [2.14, 3.03] / 1.20 | 2.37 [2.01, 2.79] / 1.10 | 0.13 [-0.22, 0.48] | -0.13 [-0.48, 0.22] | 50.2% [47.0%, 53.5%] | 47.2% [44.0%, 50.5%] | 46.5% [43.4%, 49.4%] | 26 | 599 / 317 | 20 | adequate descriptive support | 425 / 430 / 72 / 57 | 0 |
| 2.0 | 15 | 974 | 2.95 [2.46, 3.48] / 1.30 | 3.24 [2.70, 3.84] / 1.50 | 3.24 [2.70, 3.84] / 1.50 | 2.95 [2.46, 3.48] / 1.30 | 0.10 [-0.30, 0.49] | -0.10 [-0.49, 0.30] | 51.1% [47.8%, 54.4%] | 47.2% [44.1%, 50.5%] | 45.8% [42.5%, 49.0%] | 16 | 594 / 315 | 30 | adequate descriptive support | 439 / 441 / 37 / 57 | 0 |
| 2.0 | 20 | 963 | 3.41 [2.85, 4.02] / 1.60 | 3.75 [3.13, 4.43] / 1.70 | 3.75 [3.13, 4.43] / 1.70 | 3.41 [2.85, 4.02] / 1.60 | -0.05 [-0.56, 0.43] | 0.05 [-0.43, 0.56] | 49.3% [46.0%, 52.5%] | 49.1% [46.0%, 52.5%] | 44.8% [41.7%, 47.9%] | 15 | 592 / 315 | 41 | adequate descriptive support | 436 / 441 / 29 / 57 | 0 |
| 2.0 | 50 | 872 | 5.53 [4.62, 6.54] / 2.50 | 6.00 [4.95, 7.16] / 2.60 | 6.00 [4.95, 7.16] / 2.60 | 5.53 [4.62, 6.54] / 2.50 | -0.09 [-0.85, 0.60] | 0.09 [-0.60, 0.85] | 48.9% [44.7%, 52.7%] | 50.1% [46.1%, 54.2%] | 46.1% [42.8%, 49.6%] | 9 | 558 / 304 | 132 | adequate descriptive support | 407 / 407 / 1 / 57 | 0 |
| 2.5 | 5 | 401 | 1.71 [1.35, 2.11] / 0.80 | 1.86 [1.45, 2.34] / 0.80 | 1.86 [1.45, 2.34] / 0.80 | 1.71 [1.35, 2.11] / 0.80 | 0.09 [-0.22, 0.42] | -0.09 [-0.42, 0.22] | 49.1% [44.3%, 53.9%] | 47.6% [42.8%, 52.6%] | 43.4% [39.1%, 47.6%] | 13 | 320 / 220 | 5 | adequate descriptive support | 140 / 161 / 77 / 23 | 0 |
| 2.5 | 10 | 395 | 2.38 [1.85, 2.97] / 1.10 | 2.71 [2.07, 3.49] / 1.10 | 2.71 [2.07, 3.49] / 1.10 | 2.38 [1.85, 2.97] / 1.10 | 0.24 [-0.38, 0.97] | -0.24 [-0.97, 0.38] | 50.4% [45.4%, 55.4%] | 46.1% [41.2%, 51.1%] | 45.1% [40.2%, 50.1%] | 14 | 315 / 217 | 11 | adequate descriptive support | 157 / 177 / 37 / 24 | 0 |
| 2.5 | 15 | 389 | 2.99 [2.29, 3.76] / 1.30 | 3.49 [2.65, 4.52] / 1.50 | 3.49 [2.65, 4.52] / 1.50 | 2.99 [2.29, 3.76] / 1.30 | 0.25 [-0.46, 1.01] | -0.25 [-1.01, 0.46] | 51.2% [46.2%, 56.1%] | 47.0% [42.2%, 51.9%] | 47.0% [42.2%, 51.8%] | 7 | 311 / 215 | 17 | adequate descriptive support | 165 / 181 / 19 / 24 | 0 |
| 2.5 | 20 | 383 | 3.48 [2.65, 4.40] / 1.50 | 4.10 [3.07, 5.33] / 1.70 | 4.10 [3.07, 5.33] / 1.70 | 3.48 [2.65, 4.40] / 1.50 | 0.11 [-0.77, 1.03] | -0.11 [-1.03, 0.77] | 48.6% [43.6%, 53.7%] | 50.1% [45.0%, 55.1%] | 43.1% [38.1%, 48.3%] | 5 | 308 / 214 | 23 | adequate descriptive support | 163 / 181 / 15 / 24 | 0 |
| 2.5 | 50 | 341 | 5.54 [4.32, 6.97] / 2.50 | 6.36 [4.60, 8.48] / 2.60 | 6.36 [4.60, 8.48] / 2.60 | 5.54 [4.32, 6.97] / 2.50 | -0.01 [-1.24, 1.28] | 0.01 [-1.28, 1.24] | 47.8% [41.7%, 53.8%] | 51.0% [45.0%, 56.9%] | 47.2% [41.7%, 52.8%] | 4 | 277 / 198 | 65 | adequate descriptive support | 153 / 164 / 0 / 24 | 0 |
| 3.0 | 5 | 91 | 2.05 [1.35, 2.82] / 0.70 | 1.47 [1.10, 1.90] / 0.80 | 1.47 [1.10, 1.90] / 0.80 | 2.05 [1.35, 2.82] / 0.70 | -0.29 [-0.95, 0.33] | 0.29 [-0.33, 0.95] | 48.4% [38.0%, 58.5%] | 47.3% [37.0%, 57.5%] | 42.9% [33.3%, 52.3%] | 4 | 82 / 76 | 2 | events_below_100 | 29 / 45 / 5 / 12 | 0 |
| 3.0 | 10 | 89 | 2.90 [1.91, 4.01] / 1.20 | 2.33 [1.63, 3.20] / 1.20 | 2.33 [1.63, 3.20] / 1.20 | 2.90 [1.91, 4.01] / 1.20 | -0.34 [-1.52, 0.84] | 0.34 [-0.84, 1.52] | 50.6% [40.6%, 61.2%] | 48.3% [37.6%, 58.4%] | 46.1% [36.2%, 55.9%] | 1 | 80 / 74 | 4 | events_below_100 | 32 / 44 / 1 / 12 | 0 |
| 3.0 | 15 | 89 | 3.43 [2.24, 4.74] / 1.30 | 3.42 [2.23, 4.90] / 1.60 | 3.42 [2.23, 4.90] / 1.60 | 3.43 [2.24, 4.74] / 1.30 | -0.06 [-1.52, 1.31] | 0.06 [-1.31, 1.52] | 50.6% [40.2%, 62.4%] | 47.2% [35.6%, 57.9%] | 44.9% [35.1%, 55.3%] | 2 | 80 / 74 | 4 | events_below_100 | 32 / 45 / 0 / 12 | 0 |
| 3.0 | 20 | 89 | 3.98 [2.68, 5.43] / 1.60 | 4.07 [2.56, 5.95] / 1.60 | 4.07 [2.56, 5.95] / 1.60 | 3.98 [2.68, 5.43] / 1.60 | -0.15 [-2.00, 1.73] | 0.15 [-1.73, 2.00] | 49.4% [39.3%, 59.6%] | 49.4% [39.0%, 59.7%] | 33.7% [24.2%, 43.2%] | 1 | 80 / 74 | 4 | events_below_100 | 32 / 45 / 0 / 12 | 0 |
| 3.0 | 50 | 83 | 6.10 [4.24, 8.06] / 2.80 | 7.37 [3.82, 13.20] / 2.60 | 7.37 [3.82, 13.20] / 2.60 | 6.10 [4.24, 8.06] / 2.80 | 0.53 [-2.53, 4.64] | -0.53 [-4.64, 2.53] | 43.4% [31.1%, 55.3%] | 55.4% [43.8%, 67.5%] | 45.8% [34.7%, 56.8%] | 1 | 76 / 71 | 10 | events_below_100 | 29 / 42 / 0 / 12 | 0 |

### Common cohort, distribution and year diagnostics

The horizon curves use the identical complete-50 cohort. Distribution quantiles and year diagnostics use each horizon’s eligible cohort. Year 2026 is partial. These diagnostics are descriptive on previously inspected history.

![GC Asia return](figures/asia-GC-return.svg)

![GC Asia excursion](figures/asia-GC-excursion.svg)

![GC Asia endpoint](figures/asia-GC-endpoint.svg)

![GC Asia mae-mfe-distribution](figures/asia-GC-mae-mfe-distribution.svg)

![GC Asia terminal-distribution](figures/asia-GC-terminal-distribution.svg)

![GC Asia year-stability](figures/asia-GC-year-stability.svg)

### Sensitivity and chronological periods at 10 candles

| Module | Scope | n | Days / weeks | Directional Δ [CI] | Return or bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- |
| departure | all | 2,401 | 814 / 355 | 0.34 [0.11, 0.58] | 43.0% [41.1%, 45.0%] |
| departure | common_50 | 2,168 | 806 / 354 | 0.30 [0.07, 0.55] | 46.8% [44.7%, 48.8%] |
| departure | age_ge30 | 1,633 | 781 / 351 | 0.56 [0.26, 0.90] | 26.0% [23.8%, 28.3%] |
| departure | through_2023 | 1,490 | 504 / 241 | 0.13 [0.03, 0.24] | 43.4% [40.8%, 45.9%] |
| departure | year_2024_period | 205 | 62 / 32 | 0.08 [-0.31, 0.45] | 44.4% [38.8%, 49.8%] |
| departure | years_2025_2026 | 706 | 248 / 82 | 0.85 [0.11, 1.63] | 41.6% [37.8%, 45.7%] |
| touch | all | 1,998 | 779 / 348 | 0.07 [-0.18, 0.32] | 51.7% [49.6%, 53.9%] |
| touch | common_50 | 1,789 | 760 / 345 | 0.07 [-0.21, 0.34] | 51.4% [49.2%, 53.8%] |
| touch | age_ge30 | 1,233 | 689 / 331 | 0.21 [-0.06, 0.51] | 53.6% [51.1%, 56.3%] |
| touch | through_2023 | 1,245 | 486 / 237 | 0.05 [-0.05, 0.17] | 52.3% [49.8%, 54.9%] |
| touch | year_2024_period | 172 | 60 / 31 | 0.07 [-0.30, 0.41] | 55.8% [47.8%, 63.5%] |
| touch | years_2025_2026 | 581 | 233 / 80 | 0.12 [-0.69, 0.98] | 49.2% [45.0%, 53.6%] |

### Deterministic source-path examples

Examples are the earliest stable ID in each prespecified class. They illustrate mechanisms and exclusions, not representative trade quality. The source table includes reference available_at and known sigma for every minute; charts plot raw one-minute high/low and references. Source minute open time relative to entry is shown; contacts have interval resolution. Lines join minute OHLC observations for display and do not imply intraminute order or trades through gaps. The 2-sigma envelope is plotted; 2.5/3-sigma references are retained in the example-path table.

return: GC-asia-2016-05-09-P0005-K2-H10; upper side. Signal/confirmation 2016-05-08 20:12:00-04:00; entry 2016-05-08 20:12:00-04:00; deadline 2016-05-08 20:32:00-04:00 (New York time). Frozen sigma 0.17 points; signal VWAP 1,287.41. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-asia-2016-05-09-P0005-K2-H10](figures/example-asia-GC-return.svg)

non_return: GC-asia-2016-02-11-P0036-K2-H10; lower side. Signal/confirmation 2016-02-10 21:14:00-05:00; entry 2016-02-10 21:14:00-05:00; deadline 2016-02-10 21:34:00-05:00 (New York time). Frozen sigma 0.83 points; signal VWAP 1,208.50. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-asia-2016-02-11-P0036-K2-H10](figures/example-asia-GC-non_return.svg)

bounce: GC-asia-2016-05-09-P0045-T-H10; upper side. Signal/confirmation 2016-05-08 22:40:00-04:00; entry 2016-05-08 22:40:00-04:00; deadline 2016-05-08 23:00:00-04:00 (New York time). Frozen sigma 0.85 points; signal VWAP 1,287.66. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-asia-2016-05-09-P0045-T-H10](figures/example-asia-GC-bounce.svg)

through: GC-asia-2016-02-11-P0036-T-H10; lower side. Signal/confirmation 2016-02-10 23:22:00-05:00; entry 2016-02-10 23:22:00-05:00; deadline 2016-02-10 23:42:00-05:00 (New York time). Frozen sigma 1.20 points; signal VWAP 1,207.60. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-asia-2016-02-11-P0036-T-H10](figures/example-asia-GC-through.svg)

ambiguity: GC-asia-2016-05-09-P0005-T-H10; upper side. Signal/confirmation 2016-05-08 20:14:00-04:00; entry 2016-05-08 20:14:00-04:00; deadline 2016-05-08 20:34:00-04:00 (New York time). Frozen sigma 0.19 points; signal VWAP 1,287.50. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-asia-2016-05-09-P0005-T-H10](figures/example-asia-GC-ambiguity.svg)

exclusion: GC-asia-2016-05-09-P0165-K2-H50; lower side. Signal/confirmation 2016-05-09 01:32:00-04:00; entry 2016-05-09 01:32:00-04:00; deadline 2016-05-09 03:12:00-04:00 (New York time). Frozen sigma 1.01 points; signal VWAP 1,287.21. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: session_boundary.

![GC-asia-2016-05-09-P0165-K2-H50](figures/example-asia-GC-exclusion.svg)

## Interpretation and verification

Return rates, first-move rates and terminal directional frequencies answer different questions. MAE/MFE maxima are favorable/adverse opportunities on an observed path, not obtainable trading profits. Threshold comparisons are descriptive because signal times and eligible populations differ. Treat sparse cells and boundary uncertainty as unresolved. Shared week intervals do not remove retrospective selection or establish a causal predictor.

[Numerical verification record](verification.json)

[Dated findings and advice](advice.md)

[Example selection ledger](tables/example-selection.csv)

[Independent source recounts](tables/independent-recounts.csv)

[Retained event evidence and checksums](events.manifest.json)
