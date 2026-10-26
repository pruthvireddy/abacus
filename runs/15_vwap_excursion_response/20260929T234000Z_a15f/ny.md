# New York — anchored VWAP excursion and return

Fresh historical execution · Protocol 1.0.0 · Frozen before new outcomes · 2026 YTD through September 18

New York uses its own 09:30 New York-clock anchor and [09:30, 16:00) observation window. Both entry and complete horizons stay inside this window; a final candle closing exactly at the end is eligible. DST uses America/New_York. Globex is a separate overlapping population, not a sum of local sessions.

The pinned VWAP uses completed two-minute HLC3 weighted by bar volume and a volume-weighted population sigma; it is not trade-by-trade VWAP. Signals are first fresh strict closes beyond 2, 2.5 or 3 sigma within a causal parent excursion. Entry is the next two-minute open. Horizons 5/10/15/20/50 candles are 10/20/30/40/100 minutes; 15 is supplementary. Touch is source one-minute range overlap with the tick-rounded ±1-tick VWAP zone available at that minute open. Evolving VWAP is primary; signal-frozen VWAP is secondary. A gap or reference overtake alone is not a touch. Touch response begins after the containing two-minute candle closes. All MAE/MFE excludes the signal/touch candle and follows the full horizon. Upper departures: continuation is long and fade is short; upper-arrival bounce is long and through is short. Lower departures: continuation is short and fade is long; lower-arrival bounce is short and through is long.

The release contains 1,037 ES days, 1,177 NQ days and 825 GC days, selected retrospectively for whole-day completeness. ES/NQ feature history begins in 2021; GC eligible history begins in 2016; all end September 18, 2026. Absent minutes can be no-trade intervals; absence is not asserted to be corruption. This is previously inspected exploratory history, with overlapping sessions and nested thresholds. No threshold or horizon was optimized. Tick-rounded OHLC contact does not establish an executable fill, and OHLC cannot order two barriers reached in the same minute. No fees, slippage, position sizing, stops or profitability were tested. Delta means price change; true aggressor volume delta is unavailable.

Intervals are marginal 95% percentile intervals from 2,000 shared ISO-week cluster draws (seed 1501), preserving cross-product/session dependence. Brackets contain intervals. † marks zero/all-success boundary uncertainty unresolved by a degenerate bootstrap. Sparse flags: fewer than 100 events, 30 product-session dates or 20 weeks. Latency summaries condition on actual touching. Unavailable horizons never enter success/failure denominators.

[Full numerical tables: points, ticks, sigma units, tails, contexts, uncertainty and counts](tables/summary.csv)

[Per-horizon eligibility, exclusion reasons, parent/date/week support](tables/coverage.csv)

## Primary 2-sigma overview

Mirrored upper/lower sides are combined only within each product and session in this overview. The side-specific tables below retain every threshold and horizon. Endpoint bounce frequency describes the closing direction; it differs from the 0.5-sigma first-move race.

| Session | Product | h | Departure n | Evolving return % [CI] | Continuation Δ points [CI] | Touch n | Bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| New York | ES | 10 | 2,936 | 44.1% [42.5%, 45.7%] | 0.34 [-0.11, 0.78] | 2,379 | 49.6% [47.4%, 51.7%] |
| New York | ES | 50 | 2,748 | 74.2% [72.8%, 75.6%] | 0.72 [-0.19, 1.73] | 2,195 | 50.3% [48.2%, 52.3%] |
| New York | GC | 10 | 2,023 | 45.6% [43.5%, 47.6%] | 0.25 [0.03, 0.51] | 1,623 | 49.6% [46.9%, 52.2%] |
| New York | GC | 50 | 1,927 | 75.3% [73.8%, 76.8%] | -0.06 [-0.61, 0.51] | 1,558 | 50.7% [48.3%, 53.3%] |
| New York | NQ | 10 | 2,974 | 41.4% [39.9%, 42.9%] | 0.56 [-1.44, 2.53] | 2,353 | 50.4% [48.3%, 52.4%] |
| New York | NQ | 50 | 2,795 | 72.5% [71.1%, 73.8%] | 2.63 [-1.50, 6.71] | 2,188 | 52.6% [50.7%, 54.5%] |

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
| 2.0 | 5 | 1,489 | 5.66 [5.30, 6.05] / 3.75 | 5.78 [5.34, 6.27] / 4.00 | 5.78 [5.34, 6.27] / 4.00 | 5.66 [5.30, 6.05] / 3.75 | 0.37 [-0.03, 0.80] | -0.37 [-0.80, 0.03] | 52.9% [50.5%, 55.4%] | 52.9% [50.5%, 55.4%] | 50.1% [47.5%, 52.8%] | 41 | 838 / 262 | 12 | adequate descriptive support |
| 2.0 | 10 | 1,474 | 7.80 [7.31, 8.33] / 5.25 | 8.10 [7.42, 8.91] / 5.75 | 8.10 [7.42, 8.91] / 5.75 | 7.80 [7.31, 8.33] / 5.25 | 0.60 [-0.08, 1.34] | -0.60 [-1.34, 0.08] | 54.7% [52.1%, 57.3%] | 54.7% [52.1%, 57.3%] | 47.2% [44.7%, 49.7%] | 17 | 837 / 262 | 27 | adequate descriptive support |
| 2.0 | 15 | 1,464 | 9.55 [8.92, 10.20] / 6.25 | 10.00 [9.00, 11.30] / 7.00 | 10.00 [9.00, 11.30] / 7.00 | 9.55 [8.92, 10.20] / 6.25 | 0.77 [-0.11, 1.77] | -0.77 [-1.77, 0.11] | 54.0% [51.6%, 56.5%] | 54.0% [51.6%, 56.5%] | 50.1% [47.6%, 52.7%] | 16 | 834 / 262 | 37 | adequate descriptive support |
| 2.0 | 20 | 1,461 | 10.90 [10.16, 11.68] / 7.25 | 11.14 [10.08, 12.49] / 8.00 | 11.14 [10.08, 12.49] / 8.00 | 10.90 [10.16, 11.68] / 7.25 | 0.70 [-0.26, 1.75] | -0.70 [-1.75, 0.26] | 55.4% [52.6%, 58.3%] | 55.4% [52.6%, 58.3%] | 49.7% [47.0%, 52.4%] | 11 | 834 / 262 | 40 | adequate descriptive support |
| 2.0 | 50 | 1,377 | 16.10 [14.91, 17.29] / 11.00 | 15.89 [14.52, 17.59] / 12.25 | 15.89 [14.52, 17.59] / 12.25 | 16.10 [14.91, 17.29] / 11.00 | 1.13 [-0.32, 2.53] | -1.13 [-2.53, 0.32] | 55.0% [52.0%, 58.1%] | 55.0% [52.0%, 58.1%] | 46.9% [44.3%, 49.7%] | 9 | 818 / 262 | 124 | adequate descriptive support |
| 2.5 | 5 | 766 | 5.72 [5.25, 6.22] / 3.75 | 5.78 [5.13, 6.54] / 3.75 | 5.78 [5.13, 6.54] / 3.75 | 5.72 [5.25, 6.22] / 3.75 | 0.09 [-0.44, 0.61] | -0.09 [-0.61, 0.44] | 51.2% [47.5%, 54.8%] | 51.2% [47.5%, 54.8%] | 47.1% [43.9%, 50.5%] | 11 | 561 / 245 | 10 | adequate descriptive support |
| 2.5 | 10 | 761 | 8.04 [7.33, 8.85] / 5.25 | 8.12 [7.10, 9.50] / 5.50 | 8.12 [7.10, 9.50] / 5.50 | 8.04 [7.33, 8.85] / 5.25 | 0.22 [-0.61, 1.06] | -0.22 [-1.06, 0.61] | 50.5% [47.0%, 54.0%] | 50.5% [47.0%, 54.0%] | 50.3% [47.2%, 53.5%] | 10 | 559 / 244 | 15 | adequate descriptive support |
| 2.5 | 15 | 754 | 9.99 [9.09, 11.01] / 6.25 | 9.82 [8.57, 11.50] / 6.25 | 9.82 [8.57, 11.50] / 6.25 | 9.99 [9.09, 11.01] / 6.25 | 0.27 [-0.81, 1.38] | -0.27 [-1.38, 0.81] | 52.1% [48.7%, 55.7%] | 52.1% [48.7%, 55.7%] | 51.3% [48.0%, 54.7%] | 9 | 557 / 244 | 22 | adequate descriptive support |
| 2.5 | 20 | 746 | 11.49 [10.44, 12.68] / 7.25 | 10.91 [9.55, 12.77] / 7.00 | 10.91 [9.55, 12.77] / 7.00 | 11.49 [10.44, 12.68] / 7.25 | -0.16 [-1.39, 1.05] | 0.16 [-1.05, 1.39] | 50.1% [46.5%, 53.8%] | 50.1% [46.5%, 53.8%] | 48.0% [44.7%, 51.4%] | 10 | 554 / 244 | 30 | adequate descriptive support |
| 2.5 | 50 | 699 | 16.54 [15.13, 18.05] / 11.50 | 15.51 [13.76, 17.86] / 11.25 | 15.51 [13.76, 17.86] / 11.25 | 16.54 [15.13, 18.05] / 11.50 | 0.80 [-0.97, 2.63] | -0.80 [-2.63, 0.97] | 52.5% [48.4%, 56.7%] | 52.5% [48.4%, 56.7%] | 49.9% [46.1%, 53.5%] | 7 | 535 / 242 | 77 | adequate descriptive support |
| 3.0 | 5 | 233 | 5.89 [5.09, 6.76] / 4.00 | 6.25 [5.31, 7.20] / 4.00 | 6.25 [5.31, 7.20] / 4.00 | 5.89 [5.09, 6.76] / 4.00 | 0.90 [-0.39, 2.14] | -0.90 [-2.14, 0.39] | 54.1% [47.2%, 60.9%] | 54.1% [47.2%, 60.9%] | 48.1% [41.5%, 54.9%] | 2 | 198 / 143 | 3 | adequate descriptive support |
| 3.0 | 10 | 232 | 8.13 [6.97, 9.42] / 5.25 | 8.79 [7.49, 10.14] / 6.00 | 8.79 [7.49, 10.14] / 6.00 | 8.13 [6.97, 9.42] / 5.25 | 0.94 [-0.97, 2.84] | -0.94 [-2.84, 0.97] | 56.0% [48.8%, 63.3%] | 56.0% [48.8%, 63.3%] | 47.4% [39.9%, 55.2%] | 5 | 197 / 142 | 4 | adequate descriptive support |
| 3.0 | 15 | 232 | 9.43 [8.07, 10.88] / 6.38 | 11.28 [9.68, 12.99] / 7.62 | 11.28 [9.68, 12.99] / 7.62 | 9.43 [8.07, 10.88] / 6.38 | 2.25 [0.05, 4.41] | -2.25 [-4.41, -0.05] | 58.2% [51.6%, 65.3%] | 58.2% [51.6%, 65.3%] | 46.6% [40.2%, 53.2%] | 4 | 197 / 142 | 4 | adequate descriptive support |
| 3.0 | 20 | 230 | 10.54 [9.04, 12.14] / 7.38 | 12.54 [10.82, 14.34] / 8.62 | 12.54 [10.82, 14.34] / 8.62 | 10.54 [9.04, 12.14] / 7.38 | 2.80 [0.58, 4.99] | -2.80 [-4.99, -0.58] | 59.1% [52.7%, 65.8%] | 59.1% [52.7%, 65.8%] | 50.0% [44.1%, 56.4%] | 3 | 195 / 142 | 6 | adequate descriptive support |
| 3.0 | 50 | 209 | 15.19 [13.10, 17.52] / 11.75 | 17.81 [15.53, 20.43] / 14.00 | 17.81 [15.53, 20.43] / 14.00 | 15.19 [13.10, 17.52] / 11.75 | 3.26 [-0.23, 6.69] | -3.26 [-6.69, 0.23] | 58.9% [51.5%, 66.5%] | 58.9% [51.5%, 66.5%] | 50.7% [43.4%, 57.6%] | 3 | 183 / 134 | 27 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,489 | 460 | 30.9% [28.7%, 33.1%] | 1,029 | 2.0 / 4.0 | 1 | 0 | 12 | 67 | 0 |
| 2.0 | 5 | frozen | 1,489 | 393 | 26.4% [24.4%, 28.5%] | 1,096 | 2.0 / 3.0 | 1 | 0 | 12 | 67 | 0 |
| 2.0 | 10 | evolving | 1,474 | 640 | 43.4% [41.3%, 45.7%] | 834 | 3.0 / 6.0 | 1 | 0 | 27 | 114 | 0 |
| 2.0 | 10 | frozen | 1,474 | 526 | 35.7% [33.4%, 38.1%] | 948 | 3.0 / 6.0 | 1 | 0 | 27 | 114 | 0 |
| 2.0 | 15 | evolving | 1,464 | 729 | 49.8% [47.7%, 52.0%] | 735 | 4.0 / 8.0 | 1 | 0 | 37 | 123 | 0 |
| 2.0 | 15 | frozen | 1,464 | 606 | 41.4% [39.0%, 43.8%] | 858 | 4.0 / 7.0 | 1 | 0 | 37 | 123 | 0 |
| 2.0 | 20 | evolving | 1,461 | 805 | 55.1% [53.0%, 57.4%] | 656 | 5.0 / 10.0 | 1 | 0 | 40 | 131 | 0 |
| 2.0 | 20 | frozen | 1,461 | 674 | 46.1% [43.6%, 48.8%] | 787 | 4.0 / 10.0 | 1 | 0 | 40 | 131 | 0 |
| 2.0 | 50 | evolving | 1,377 | 989 | 71.8% [69.7%, 73.9%] | 388 | 6.0 / 17.0 | 1 | 0 | 124 | 170 | 0 |
| 2.0 | 50 | frozen | 1,377 | 819 | 59.5% [57.0%, 62.1%] | 558 | 6.0 / 16.0 | 1 | 0 | 124 | 170 | 0 |
| 2.5 | 5 | evolving | 766 | 207 | 27.0% [23.8%, 30.1%] | 559 | 3.0 / 4.0 | 0 | 0 | 10 | 33 | 0 |
| 2.5 | 5 | frozen | 766 | 174 | 22.7% [19.8%, 25.7%] | 592 | 2.5 / 4.0 | 0 | 0 | 10 | 33 | 0 |
| 2.5 | 10 | evolving | 761 | 293 | 38.5% [35.3%, 41.7%] | 468 | 4.0 / 6.0 | 0 | 0 | 15 | 61 | 0 |
| 2.5 | 10 | frozen | 761 | 232 | 30.5% [27.3%, 33.6%] | 529 | 3.0 / 5.2 | 0 | 0 | 15 | 61 | 0 |
| 2.5 | 15 | evolving | 754 | 337 | 44.7% [41.5%, 47.8%] | 417 | 4.0 / 8.0 | 0 | 0 | 22 | 62 | 0 |
| 2.5 | 15 | frozen | 754 | 275 | 36.5% [33.1%, 39.7%] | 479 | 4.0 / 8.0 | 0 | 0 | 22 | 62 | 0 |
| 2.5 | 20 | evolving | 746 | 379 | 50.8% [47.7%, 54.0%] | 367 | 5.0 / 10.0 | 0 | 0 | 30 | 68 | 0 |
| 2.5 | 20 | frozen | 746 | 311 | 41.7% [38.3%, 45.1%] | 435 | 5.0 / 11.0 | 0 | 0 | 30 | 68 | 0 |
| 2.5 | 50 | evolving | 699 | 474 | 67.8% [64.7%, 70.9%] | 225 | 7.0 / 19.0 | 0 | 0 | 77 | 84 | 0 |
| 2.5 | 50 | frozen | 699 | 390 | 55.8% [52.2%, 59.5%] | 309 | 7.0 / 19.0 | 0 | 0 | 77 | 84 | 0 |
| 3.0 | 5 | evolving | 233 | 73 | 31.3% [25.7%, 36.9%] | 160 | 3.0 / 4.0 | 0 | 0 | 3 | 12 | 0 |
| 3.0 | 5 | frozen | 233 | 61 | 26.2% [21.0%, 31.4%] | 172 | 2.0 / 3.0 | 0 | 0 | 3 | 12 | 0 |
| 3.0 | 10 | evolving | 232 | 99 | 42.7% [36.2%, 48.8%] | 133 | 4.0 / 6.0 | 0 | 0 | 4 | 16 | 0 |
| 3.0 | 10 | frozen | 232 | 83 | 35.8% [29.7%, 41.6%] | 149 | 3.0 / 6.0 | 0 | 0 | 4 | 16 | 0 |
| 3.0 | 15 | evolving | 232 | 105 | 45.3% [39.4%, 50.9%] | 127 | 4.0 / 6.0 | 0 | 0 | 4 | 16 | 0 |
| 3.0 | 15 | frozen | 232 | 89 | 38.4% [32.4%, 44.2%] | 143 | 3.0 / 6.0 | 0 | 0 | 4 | 16 | 0 |
| 3.0 | 20 | evolving | 230 | 120 | 52.2% [46.2%, 57.9%] | 110 | 4.0 / 8.0 | 0 | 0 | 6 | 24 | 0 |
| 3.0 | 20 | frozen | 230 | 96 | 41.7% [35.6%, 47.5%] | 134 | 4.0 / 7.0 | 0 | 0 | 6 | 24 | 0 |
| 3.0 | 50 | evolving | 209 | 142 | 67.9% [62.0%, 73.4%] | 67 | 6.0 / 17.8 | 0 | 0 | 27 | 31 | 0 |
| 3.0 | 50 | frozen | 209 | 111 | 53.1% [46.2%, 59.2%] | 98 | 5.0 / 14.0 | 0 | 0 | 27 | 31 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,169 | 6.25 [5.82, 6.70] / 4.25 | 6.08 [5.51, 6.84] / 4.25 | 6.08 [5.51, 6.84] / 4.25 | 6.25 [5.82, 6.70] / 4.25 | 0.00 [-0.45, 0.47] | -0.00 [-0.47, 0.45] | 49.8% [47.0%, 52.6%] | 49.8% [47.0%, 52.6%] | 46.4% [43.3%, 49.4%] | 21 | 728 / 257 | 27 | adequate descriptive support | 440 / 487 / 102 / 140 | 0 |
| 2.0 | 10 | 1,159 | 8.70 [8.04, 9.38] / 6.00 | 8.06 [7.38, 8.92] / 5.75 | 8.06 [7.38, 8.92] / 5.75 | 8.70 [8.04, 9.38] / 6.00 | -0.24 [-0.89, 0.45] | 0.24 [-0.45, 0.89] | 51.3% [48.4%, 54.2%] | 51.3% [48.4%, 54.2%] | 46.8% [44.0%, 49.6%] | 18 | 723 / 256 | 37 | adequate descriptive support | 461 / 511 / 47 / 140 | 0 |
| 2.0 | 15 | 1,152 | 10.55 [9.72, 11.41] / 7.25 | 9.72 [8.91, 10.69] / 6.75 | 9.72 [8.91, 10.69] / 6.75 | 10.55 [9.72, 11.41] / 7.25 | -0.12 [-1.01, 0.80] | 0.12 [-0.80, 1.01] | 51.6% [48.6%, 54.6%] | 51.6% [48.6%, 54.6%] | 50.4% [48.0%, 53.0%] | 15 | 723 / 256 | 44 | adequate descriptive support | 475 / 522 / 15 / 140 | 0 |
| 2.0 | 20 | 1,143 | 11.83 [10.91, 12.83] / 8.00 | 10.99 [10.14, 12.04] / 8.00 | 10.99 [10.14, 12.04] / 8.00 | 11.83 [10.91, 12.83] / 8.00 | 0.41 [-0.57, 1.46] | -0.41 [-1.46, 0.57] | 52.8% [49.8%, 56.0%] | 52.8% [49.8%, 56.0%] | 52.4% [49.6%, 55.3%] | 11 | 720 / 256 | 53 | adequate descriptive support | 477 / 520 / 6 / 140 | 0 |
| 2.0 | 50 | 1,075 | 17.31 [15.87, 18.86] / 11.75 | 15.76 [14.54, 17.20] / 11.50 | 15.76 [14.54, 17.20] / 11.50 | 17.31 [15.87, 18.86] / 11.75 | 0.03 [-1.54, 1.67] | -0.03 [-1.67, 1.54] | 53.3% [50.0%, 56.6%] | 53.3% [50.0%, 56.6%] | 45.2% [42.1%, 48.3%] | 4 | 700 / 254 | 121 | adequate descriptive support | 446 / 489 / 0 / 140 | 0 |
| 2.5 | 5 | 575 | 6.50 [5.86, 7.19] / 4.50 | 6.19 [5.32, 7.42] / 4.25 | 6.19 [5.32, 7.42] / 4.25 | 6.50 [5.86, 7.19] / 4.50 | -0.15 [-0.88, 0.64] | 0.15 [-0.64, 0.88] | 49.6% [45.5%, 53.8%] | 49.6% [45.5%, 53.8%] | 45.6% [41.0%, 49.9%] | 12 | 453 / 229 | 15 | adequate descriptive support | 213 / 245 / 55 / 62 | 0 |
| 2.5 | 10 | 570 | 9.17 [8.19, 10.14] / 6.12 | 8.10 [7.09, 9.53] / 5.50 | 8.10 [7.09, 9.53] / 5.50 | 9.17 [8.19, 10.14] / 6.12 | -0.57 [-1.58, 0.58] | 0.57 [-0.58, 1.58] | 50.4% [46.3%, 54.7%] | 50.4% [46.3%, 54.7%] | 47.4% [43.3%, 51.4%] | 11 | 449 / 227 | 20 | adequate descriptive support | 220 / 261 / 27 / 62 | 0 |
| 2.5 | 15 | 566 | 11.20 [10.01, 12.40] / 7.38 | 9.80 [8.64, 11.40] / 6.75 | 9.80 [8.64, 11.40] / 6.75 | 11.20 [10.01, 12.40] / 7.38 | -0.47 [-1.88, 1.15] | 0.47 [-1.15, 1.88] | 50.2% [46.0%, 54.7%] | 50.2% [46.0%, 54.7%] | 50.5% [46.4%, 54.6%] | 7 | 448 / 227 | 24 | adequate descriptive support | 228 / 266 / 10 / 62 | 0 |
| 2.5 | 20 | 561 | 12.50 [11.20, 13.83] / 8.00 | 10.99 [9.77, 12.67] / 8.00 | 10.99 [9.77, 12.67] / 8.00 | 12.50 [11.20, 13.83] / 8.00 | -0.00 [-1.60, 1.79] | 0.00 [-1.79, 1.60] | 51.7% [47.3%, 56.3%] | 51.7% [47.3%, 56.3%] | 50.6% [46.4%, 55.0%] | 6 | 446 / 227 | 29 | adequate descriptive support | 229 / 264 / 6 / 62 | 0 |
| 2.5 | 50 | 524 | 17.91 [15.94, 19.73] / 12.38 | 15.74 [13.98, 17.88] / 11.25 | 15.74 [13.98, 17.88] / 11.25 | 17.91 [15.94, 19.73] / 12.38 | -0.33 [-2.51, 1.90] | 0.33 [-1.90, 2.51] | 51.1% [47.0%, 55.6%] | 51.1% [47.0%, 55.6%] | 44.8% [40.8%, 49.2%] | 3 | 424 / 222 | 66 | adequate descriptive support | 215 / 247 / 0 / 62 | 0 |
| 3.0 | 5 | 177 | 6.04 [5.13, 7.00] / 4.25 | 6.69 [5.63, 7.89] / 4.75 | 6.69 [5.63, 7.89] / 4.75 | 6.04 [5.13, 7.00] / 4.25 | 1.09 [-0.29, 2.58] | -1.09 [-2.58, 0.29] | 54.2% [47.4%, 61.1%] | 54.2% [47.4%, 61.1%] | 48.0% [39.8%, 56.0%] | 4 | 154 / 120 | 3 | adequate descriptive support | 69 / 66 / 16 / 26 | 0 |
| 3.0 | 10 | 175 | 7.91 [6.71, 9.18] / 6.00 | 9.05 [7.69, 10.56] / 6.50 | 9.05 [7.69, 10.56] / 6.50 | 7.91 [6.71, 9.18] / 6.00 | 1.85 [0.05, 3.72] | -1.85 [-3.72, -0.05] | 57.7% [49.7%, 65.8%] | 57.7% [49.7%, 65.8%] | 53.1% [45.3%, 60.7%] | 3 | 152 / 118 | 5 | adequate descriptive support | 68 / 73 / 8 / 26 | 0 |
| 3.0 | 15 | 173 | 9.58 [8.07, 11.14] / 6.75 | 11.33 [9.74, 13.13] / 8.25 | 11.33 [9.74, 13.13] / 8.25 | 9.58 [8.07, 11.14] / 6.75 | 2.68 [0.20, 5.15] | -2.68 [-5.15, -0.20] | 58.4% [49.8%, 66.7%] | 58.4% [49.8%, 66.7%] | 46.2% [38.4%, 54.0%] | 3 | 151 / 118 | 7 | adequate descriptive support | 69 / 75 / 3 / 26 | 0 |
| 3.0 | 20 | 171 | 11.00 [9.31, 12.76] / 7.25 | 12.92 [11.11, 14.88] / 9.50 | 12.92 [11.11, 14.88] / 9.50 | 11.00 [9.31, 12.76] / 7.25 | 2.88 [0.22, 5.55] | -2.88 [-5.55, -0.22] | 62.0% [53.9%, 70.2%] | 62.0% [53.9%, 70.2%] | 52.0% [44.6%, 59.3%] | 1 | 149 / 117 | 9 | adequate descriptive support | 68 / 75 / 2 / 26 | 0 |
| 3.0 | 50 | 155 | 17.11 [14.19, 20.41] / 11.75 | 17.79 [14.95, 21.01] / 14.75 | 17.79 [14.95, 21.01] / 14.75 | 17.11 [14.19, 20.41] / 11.75 | 1.24 [-3.51, 5.87] | -1.24 [-5.87, 3.51] | 54.8% [46.5%, 62.9%] | 54.8% [46.5%, 62.9%] | 47.1% [39.7%, 54.1%] | 1 | 137 / 108 | 25 | adequate descriptive support | 60 / 69 / 0 / 26 | 0 |

### Lower departure / arrival: continuation and bounce short; fade and through long

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,472 | 6.19 [5.75, 6.66] / 4.50 | 6.52 [6.12, 6.96] / 4.50 | 6.52 [6.12, 6.96] / 4.50 | 6.19 [5.75, 6.66] / 4.50 | 0.01 [-0.42, 0.41] | -0.01 [-0.41, 0.42] | 48.1% [45.4%, 50.8%] | 49.8% [47.2%, 52.5%] | 47.2% [44.6%, 49.7%] | 31 | 802 / 265 | 15 | adequate descriptive support |
| 2.0 | 10 | 1,462 | 8.54 [7.90, 9.24] / 6.00 | 9.02 [8.45, 9.63] / 6.25 | 9.02 [8.45, 9.63] / 6.25 | 8.54 [7.90, 9.24] / 6.00 | 0.07 [-0.58, 0.73] | -0.07 [-0.73, 0.58] | 48.5% [45.7%, 51.1%] | 50.7% [48.0%, 53.4%] | 45.9% [43.4%, 48.3%] | 12 | 799 / 265 | 25 | adequate descriptive support |
| 2.0 | 15 | 1,451 | 10.20 [9.45, 11.05] / 7.25 | 10.90 [10.18, 11.68] / 7.75 | 10.90 [10.18, 11.68] / 7.75 | 10.20 [9.45, 11.05] / 7.25 | 0.27 [-0.56, 1.12] | -0.27 [-1.12, 0.56] | 48.8% [46.1%, 51.6%] | 50.0% [47.1%, 52.6%] | 48.4% [45.9%, 50.9%] | 18 | 797 / 265 | 36 | adequate descriptive support |
| 2.0 | 20 | 1,445 | 11.70 [10.75, 12.86] / 8.25 | 12.49 [11.62, 13.42] / 8.50 | 12.49 [11.62, 13.42] / 8.50 | 11.70 [10.75, 12.86] / 8.25 | 0.23 [-0.88, 1.27] | -0.23 [-1.27, 0.88] | 48.7% [45.6%, 51.8%] | 50.7% [47.6%, 53.8%] | 46.9% [44.4%, 49.4%] | 8 | 797 / 265 | 42 | adequate descriptive support |
| 2.0 | 50 | 1,371 | 16.60 [15.31, 17.97] / 12.25 | 18.11 [16.78, 19.54] / 12.75 | 18.11 [16.78, 19.54] / 12.75 | 16.60 [15.31, 17.97] / 12.25 | 0.30 [-1.10, 1.76] | -0.30 [-1.76, 1.10] | 46.5% [43.4%, 49.9%] | 52.8% [49.4%, 56.0%] | 49.2% [46.5%, 51.8%] | 9 | 782 / 263 | 116 | adequate descriptive support |
| 2.5 | 5 | 799 | 6.56 [6.03, 7.12] / 4.75 | 6.50 [5.99, 7.03] / 4.50 | 6.50 [5.99, 7.03] / 4.50 | 6.56 [6.03, 7.12] / 4.75 | -0.53 [-1.13, 0.06] | 0.53 [-0.06, 1.13] | 46.8% [43.3%, 50.1%] | 51.7% [48.3%, 55.2%] | 45.4% [42.1%, 49.0%] | 12 | 561 / 245 | 14 | adequate descriptive support |
| 2.5 | 10 | 795 | 8.84 [8.10, 9.66] / 6.50 | 8.91 [8.26, 9.62] / 6.25 | 8.91 [8.26, 9.62] / 6.25 | 8.84 [8.10, 9.66] / 6.50 | -0.28 [-1.19, 0.59] | 0.28 [-0.59, 1.19] | 48.3% [44.4%, 52.0%] | 51.1% [47.4%, 54.9%] | 48.7% [45.3%, 51.9%] | 5 | 560 / 245 | 18 | adequate descriptive support |
| 2.5 | 15 | 792 | 10.59 [9.73, 11.58] / 7.75 | 10.83 [9.93, 11.78] / 7.50 | 10.83 [9.93, 11.78] / 7.50 | 10.59 [9.73, 11.58] / 7.75 | -0.14 [-1.30, 0.95] | 0.14 [-0.95, 1.30] | 48.9% [44.9%, 52.6%] | 50.0% [46.1%, 54.0%] | 48.7% [45.3%, 52.1%] | 9 | 558 / 245 | 21 | adequate descriptive support |
| 2.5 | 20 | 784 | 11.95 [10.98, 13.08] / 8.25 | 12.31 [11.23, 13.41] / 8.62 | 12.31 [11.23, 13.41] / 8.62 | 11.95 [10.98, 13.08] / 8.25 | -0.18 [-1.55, 1.11] | 0.18 [-1.11, 1.55] | 47.8% [43.9%, 51.6%] | 51.0% [47.3%, 55.0%] | 48.7% [45.0%, 52.6%] | 9 | 554 / 245 | 29 | adequate descriptive support |
| 2.5 | 50 | 737 | 16.44 [15.09, 17.89] / 12.00 | 17.88 [16.35, 19.54] / 12.75 | 17.88 [16.35, 19.54] / 12.75 | 16.44 [15.09, 17.89] / 12.00 | 0.18 [-1.64, 2.03] | -0.18 [-2.03, 1.64] | 46.9% [43.0%, 50.9%] | 52.2% [48.3%, 56.2%] | 50.9% [47.4%, 54.7%] | 6 | 531 / 243 | 76 | adequate descriptive support |
| 3.0 | 5 | 242 | 7.33 [6.27, 8.60] / 5.00 | 7.10 [6.17, 8.17] / 4.62 | 7.10 [6.17, 8.17] / 4.62 | 7.33 [6.27, 8.60] / 5.00 | -1.08 [-2.53, 0.29] | 1.08 [-0.29, 2.53] | 45.5% [39.1%, 51.7%] | 52.9% [46.7%, 59.1%] | 48.3% [41.7%, 55.4%] | 4 | 215 / 155 | 3 | adequate descriptive support |
| 3.0 | 10 | 241 | 9.59 [8.23, 11.16] / 6.50 | 9.48 [8.27, 10.87] / 6.50 | 9.48 [8.27, 10.87] / 6.50 | 9.59 [8.23, 11.16] / 6.50 | -0.12 [-1.93, 1.69] | 0.12 [-1.69, 1.93] | 48.5% [41.7%, 55.4%] | 51.5% [44.6%, 58.3%] | 44.4% [38.2%, 50.2%] | 0 | 215 / 155 | 4 | adequate descriptive support |
| 3.0 | 15 | 239 | 11.08 [9.57, 12.82] / 7.25 | 11.65 [10.00, 13.49] / 8.00 | 11.65 [10.00, 13.49] / 8.00 | 11.08 [9.57, 12.82] / 7.25 | 0.65 [-1.60, 2.86] | -0.65 [-2.86, 1.60] | 48.5% [42.5%, 54.7%] | 51.0% [44.9%, 57.0%] | 48.1% [42.3%, 54.3%] | 1 | 214 / 154 | 6 | adequate descriptive support |
| 3.0 | 20 | 239 | 12.19 [10.58, 14.01] / 8.50 | 13.58 [11.53, 15.89] / 8.75 | 13.58 [11.53, 15.89] / 8.75 | 12.19 [10.58, 14.01] / 8.50 | 1.18 [-1.34, 3.76] | -1.18 [-3.76, 1.34] | 48.1% [41.4%, 54.6%] | 51.5% [45.1%, 58.2%] | 46.9% [40.3%, 53.4%] | 1 | 214 / 154 | 6 | adequate descriptive support |
| 3.0 | 50 | 218 | 17.09 [14.84, 19.50] / 12.75 | 19.40 [16.66, 22.46] / 14.25 | 19.40 [16.66, 22.46] / 14.25 | 17.09 [14.84, 19.50] / 12.75 | 0.82 [-2.43, 4.19] | -0.82 [-4.19, 2.43] | 47.2% [40.3%, 53.9%] | 51.8% [45.5%, 58.5%] | 47.2% [40.3%, 53.4%] | 2 | 198 / 144 | 27 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,472 | 480 | 32.6% [30.2%, 35.0%] | 992 | 2.0 / 4.0 | 0 | 0 | 15 | 73 | 0 |
| 2.0 | 5 | frozen | 1,472 | 407 | 27.6% [25.3%, 29.9%] | 1,065 | 2.0 / 4.0 | 0 | 0 | 15 | 73 | 0 |
| 2.0 | 10 | evolving | 1,462 | 655 | 44.8% [42.4%, 47.2%] | 807 | 3.0 / 6.0 | 0 | 0 | 25 | 102 | 0 |
| 2.0 | 10 | frozen | 1,462 | 553 | 37.8% [35.2%, 40.4%] | 909 | 3.0 / 6.0 | 0 | 0 | 25 | 102 | 0 |
| 2.0 | 15 | evolving | 1,451 | 775 | 53.4% [50.9%, 55.7%] | 676 | 4.0 / 8.0 | 0 | 0 | 36 | 141 | 0 |
| 2.0 | 15 | frozen | 1,451 | 634 | 43.7% [41.0%, 46.3%] | 817 | 4.0 / 7.0 | 0 | 0 | 36 | 141 | 0 |
| 2.0 | 20 | evolving | 1,445 | 856 | 59.2% [56.9%, 61.4%] | 589 | 5.0 / 10.0 | 0 | 0 | 42 | 151 | 0 |
| 2.0 | 20 | frozen | 1,445 | 705 | 48.8% [46.2%, 51.4%] | 740 | 4.0 / 9.0 | 0 | 0 | 42 | 151 | 0 |
| 2.0 | 50 | evolving | 1,371 | 1,050 | 76.6% [74.4%, 78.5%] | 321 | 6.0 / 16.0 | 0 | 0 | 116 | 186 | 0 |
| 2.0 | 50 | frozen | 1,371 | 864 | 63.0% [60.4%, 65.5%] | 507 | 6.0 / 17.0 | 0 | 0 | 116 | 186 | 0 |
| 2.5 | 5 | evolving | 799 | 232 | 29.0% [26.0%, 32.1%] | 567 | 3.0 / 4.0 | 0 | 0 | 14 | 33 | 0 |
| 2.5 | 5 | frozen | 799 | 199 | 24.9% [21.8%, 27.9%] | 600 | 2.0 / 4.0 | 0 | 0 | 14 | 33 | 0 |
| 2.5 | 10 | evolving | 795 | 314 | 39.5% [36.2%, 42.8%] | 481 | 3.0 / 6.0 | 0 | 0 | 18 | 59 | 0 |
| 2.5 | 10 | frozen | 795 | 255 | 32.1% [28.7%, 35.2%] | 540 | 3.0 / 5.0 | 0 | 0 | 18 | 59 | 0 |
| 2.5 | 15 | evolving | 792 | 381 | 48.1% [44.5%, 51.6%] | 411 | 4.0 / 8.0 | 0 | 0 | 21 | 77 | 0 |
| 2.5 | 15 | frozen | 792 | 304 | 38.4% [35.0%, 41.7%] | 488 | 4.0 / 7.0 | 0 | 0 | 21 | 77 | 0 |
| 2.5 | 20 | evolving | 784 | 425 | 54.2% [50.7%, 57.6%] | 359 | 5.0 / 11.0 | 0 | 0 | 29 | 80 | 0 |
| 2.5 | 20 | frozen | 784 | 345 | 44.0% [40.5%, 47.5%] | 439 | 4.0 / 11.0 | 0 | 0 | 29 | 80 | 0 |
| 2.5 | 50 | evolving | 737 | 526 | 71.4% [68.0%, 74.5%] | 211 | 7.0 / 18.0 | 0 | 0 | 76 | 111 | 0 |
| 2.5 | 50 | frozen | 737 | 415 | 56.3% [52.7%, 59.6%] | 322 | 6.0 / 18.0 | 0 | 0 | 76 | 111 | 0 |
| 3.0 | 5 | evolving | 242 | 79 | 32.6% [26.9%, 38.3%] | 163 | 3.0 / 4.0 | 0 | 0 | 3 | 11 | 0 |
| 3.0 | 5 | frozen | 242 | 68 | 28.1% [22.3%, 34.0%] | 174 | 2.0 / 3.2 | 0 | 0 | 3 | 11 | 0 |
| 3.0 | 10 | evolving | 241 | 94 | 39.0% [33.2%, 44.9%] | 147 | 3.0 / 5.0 | 0 | 0 | 4 | 12 | 0 |
| 3.0 | 10 | frozen | 241 | 82 | 34.0% [28.4%, 39.7%] | 159 | 3.0 / 4.0 | 0 | 0 | 4 | 12 | 0 |
| 3.0 | 15 | evolving | 239 | 114 | 47.7% [41.6%, 53.5%] | 125 | 4.0 / 7.0 | 0 | 0 | 6 | 19 | 0 |
| 3.0 | 15 | frozen | 239 | 95 | 39.7% [33.7%, 45.4%] | 144 | 3.0 / 6.0 | 0 | 0 | 6 | 19 | 0 |
| 3.0 | 20 | evolving | 239 | 127 | 53.1% [47.2%, 58.8%] | 112 | 4.0 / 11.0 | 0 | 0 | 6 | 23 | 0 |
| 3.0 | 20 | frozen | 239 | 104 | 43.5% [37.3%, 49.5%] | 135 | 4.0 / 7.0 | 0 | 0 | 6 | 23 | 0 |
| 3.0 | 50 | evolving | 218 | 151 | 69.3% [63.4%, 75.1%] | 67 | 5.0 / 18.5 | 0 | 0 | 27 | 28 | 0 |
| 3.0 | 50 | frozen | 218 | 123 | 56.4% [50.2%, 62.4%] | 95 | 5.0 / 16.5 | 0 | 0 | 27 | 28 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,227 | 5.64 [5.20, 6.09] / 3.75 | 6.01 [5.55, 6.49] / 4.50 | 6.01 [5.55, 6.49] / 4.50 | 5.64 [5.20, 6.09] / 3.75 | 0.10 [-0.38, 0.55] | -0.10 [-0.55, 0.38] | 49.2% [46.3%, 52.0%] | 48.4% [45.5%, 51.4%] | 48.3% [45.4%, 51.2%] | 29 | 715 / 263 | 28 | adequate descriptive support | 488 / 448 / 189 / 102 | 0 |
| 2.0 | 10 | 1,220 | 7.80 [7.20, 8.41] / 5.25 | 8.31 [7.65, 9.00] / 6.00 | 8.31 [7.65, 9.00] / 6.00 | 7.80 [7.20, 8.41] / 5.25 | 0.13 [-0.49, 0.81] | -0.13 [-0.81, 0.49] | 48.0% [45.3%, 50.7%] | 50.7% [48.0%, 53.4%] | 49.5% [46.8%, 52.3%] | 16 | 714 / 263 | 35 | adequate descriptive support | 539 / 500 / 79 / 102 | 0 |
| 2.0 | 15 | 1,211 | 9.55 [8.69, 10.59] / 6.50 | 10.05 [9.25, 10.87] / 7.00 | 10.05 [9.25, 10.87] / 7.00 | 9.55 [8.69, 10.59] / 6.50 | 0.12 [-0.77, 0.99] | -0.12 [-0.99, 0.77] | 49.5% [46.4%, 52.5%] | 49.9% [46.9%, 52.9%] | 46.5% [43.6%, 49.4%] | 8 | 711 / 263 | 44 | adequate descriptive support | 552 / 518 / 38 / 103 | 0 |
| 2.0 | 20 | 1,199 | 10.75 [9.80, 11.86] / 7.50 | 11.45 [10.56, 12.38] / 8.25 | 11.45 [10.56, 12.38] / 8.25 | 10.75 [9.80, 11.86] / 7.50 | 0.21 [-0.75, 1.13] | -0.21 [-1.13, 0.75] | 48.5% [45.2%, 51.6%] | 50.2% [47.0%, 53.5%] | 46.6% [43.6%, 49.5%] | 16 | 708 / 263 | 56 | adequate descriptive support | 551 / 522 / 23 / 103 | 0 |
| 2.0 | 50 | 1,120 | 16.06 [14.71, 17.60] / 11.38 | 16.51 [15.19, 17.90] / 11.50 | 16.51 [15.19, 17.90] / 11.50 | 16.06 [14.71, 17.60] / 11.38 | -0.51 [-1.93, 0.94] | 0.51 [-0.94, 1.93] | 47.3% [44.1%, 50.6%] | 52.2% [49.0%, 55.4%] | 47.1% [44.3%, 49.9%] | 5 | 687 / 263 | 135 | adequate descriptive support | 519 / 496 / 2 / 103 | 0 |
| 2.5 | 5 | 640 | 5.51 [5.00, 6.04] / 3.75 | 6.11 [5.53, 6.76] / 4.25 | 6.11 [5.53, 6.76] / 4.25 | 5.51 [5.00, 6.04] / 3.75 | 0.41 [-0.27, 1.05] | -0.41 [-1.05, 0.27] | 50.0% [46.3%, 53.5%] | 46.7% [43.2%, 50.6%] | 48.6% [44.7%, 52.5%] | 21 | 465 / 233 | 19 | adequate descriptive support | 240 / 224 / 116 / 60 | 0 |
| 2.5 | 10 | 634 | 7.70 [7.01, 8.41] / 5.25 | 8.35 [7.52, 9.27] / 5.75 | 8.35 [7.52, 9.27] / 5.75 | 7.70 [7.01, 8.41] / 5.25 | 0.17 [-0.75, 1.11] | -0.17 [-1.11, 0.75] | 47.5% [43.8%, 51.0%] | 51.1% [47.6%, 55.0%] | 50.9% [46.9%, 55.2%] | 9 | 460 / 232 | 25 | adequate descriptive support | 264 / 257 / 53 / 60 | 0 |
| 2.5 | 15 | 627 | 9.09 [8.26, 9.99] / 6.50 | 10.11 [9.15, 11.18] / 7.00 | 10.11 [9.15, 11.18] / 7.00 | 9.09 [8.26, 9.99] / 6.50 | 0.55 [-0.65, 1.72] | -0.55 [-1.72, 0.65] | 50.6% [46.6%, 54.3%] | 49.0% [45.1%, 52.9%] | 46.4% [42.4%, 50.2%] | 3 | 456 / 230 | 32 | adequate descriptive support | 275 / 267 / 25 / 60 | 0 |
| 2.5 | 20 | 622 | 10.33 [9.39, 11.38] / 7.25 | 11.56 [10.46, 12.77] / 8.25 | 11.56 [10.46, 12.77] / 8.25 | 10.33 [9.39, 11.38] / 7.25 | 0.38 [-1.02, 1.67] | -0.38 [-1.67, 1.02] | 49.4% [45.0%, 53.5%] | 49.5% [45.4%, 53.8%] | 47.1% [43.2%, 51.0%] | 7 | 454 / 229 | 37 | adequate descriptive support | 277 / 270 / 15 / 60 | 0 |
| 2.5 | 50 | 568 | 15.54 [14.08, 17.15] / 10.75 | 16.48 [14.70, 18.41] / 11.50 | 16.48 [14.70, 18.41] / 11.50 | 15.54 [14.08, 17.15] / 10.75 | -0.21 [-2.25, 1.83] | 0.21 [-1.83, 2.25] | 47.4% [43.3%, 51.5%] | 51.8% [47.7%, 55.9%] | 43.1% [39.3%, 46.8%] | 5 | 429 / 226 | 91 | adequate descriptive support | 258 / 248 / 2 / 60 | 0 |
| 3.0 | 5 | 185 | 5.91 [4.92, 7.10] / 3.25 | 6.03 [5.12, 6.98] / 3.75 | 6.03 [5.12, 6.98] / 3.75 | 5.91 [4.92, 7.10] / 3.25 | -0.13 [-1.54, 1.19] | 0.13 [-1.19, 1.54] | 48.6% [40.9%, 56.5%] | 47.0% [39.4%, 54.4%] | 49.2% [41.7%, 56.9%] | 8 | 169 / 130 | 7 | adequate descriptive support | 74 / 54 / 34 / 23 | 0 |
| 3.0 | 10 | 183 | 8.11 [6.90, 9.55] / 5.25 | 8.49 [7.02, 10.07] / 5.50 | 8.49 [7.02, 10.07] / 5.50 | 8.11 [6.90, 9.55] / 5.25 | 0.45 [-1.31, 2.22] | -0.45 [-2.22, 1.31] | 47.0% [40.0%, 53.6%] | 53.0% [46.4%, 60.0%] | 47.5% [41.0%, 54.3%] | 0 | 167 / 128 | 9 | adequate descriptive support | 76 / 65 / 19 / 23 | 0 |
| 3.0 | 15 | 179 | 9.30 [7.86, 10.99] / 6.00 | 10.35 [8.57, 12.35] / 6.25 | 10.35 [8.57, 12.35] / 6.25 | 9.30 [7.86, 10.99] / 6.00 | 1.33 [-1.11, 3.71] | -1.33 [-3.71, 1.11] | 52.5% [44.9%, 59.4%] | 47.5% [40.6%, 55.1%] | 46.9% [39.8%, 54.3%] | 0 | 164 / 126 | 13 | adequate descriptive support | 80 / 67 / 9 / 23 | 0 |
| 3.0 | 20 | 179 | 10.34 [8.78, 12.21] / 6.75 | 12.07 [10.03, 14.28] / 7.50 | 12.07 [10.03, 14.28] / 7.50 | 10.34 [8.78, 12.21] / 6.75 | 1.66 [-1.16, 4.30] | -1.66 [-4.30, 1.16] | 50.8% [43.3%, 58.7%] | 48.0% [40.0%, 55.5%] | 45.8% [38.6%, 53.1%] | 2 | 164 / 126 | 13 | adequate descriptive support | 83 / 67 / 6 / 23 | 0 |
| 3.0 | 50 | 155 | 16.44 [13.74, 19.33] / 11.00 | 16.12 [13.28, 19.08] / 10.75 | 16.12 [13.28, 19.08] / 10.75 | 16.44 [13.74, 19.33] / 11.00 | -1.11 [-4.56, 2.64] | 1.11 [-2.64, 4.56] | 48.4% [40.6%, 56.2%] | 51.6% [43.8%, 59.4%] | 43.9% [36.3%, 51.7%] | 0 | 144 / 109 | 37 | adequate descriptive support | 72 / 59 / 1 / 23 | 0 |

### Common cohort, distribution and year diagnostics

The horizon curves use the identical complete-50 cohort. Distribution quantiles and year diagnostics use each horizon’s eligible cohort. Year 2026 is partial. These diagnostics are descriptive on previously inspected history.

![ES New York return](figures/ny-ES-return.svg)

![ES New York excursion](figures/ny-ES-excursion.svg)

![ES New York endpoint](figures/ny-ES-endpoint.svg)

![ES New York mae-mfe-distribution](figures/ny-ES-mae-mfe-distribution.svg)

![ES New York terminal-distribution](figures/ny-ES-terminal-distribution.svg)

![ES New York year-stability](figures/ny-ES-year-stability.svg)

### Sensitivity and chronological periods at 10 candles

| Module | Scope | n | Days / weeks | Directional Δ [CI] | Return or bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- |
| departure | all | 2,936 | 1,028 / 267 | 0.34 [-0.11, 0.78] | 44.1% [42.5%, 45.7%] |
| departure | common_50 | 2,748 | 1,027 / 267 | 0.21 [-0.24, 0.66] | 46.6% [45.0%, 48.3%] |
| departure | age_ge30 | 1,731 | 920 / 267 | 0.15 [-0.32, 0.61] | 23.5% [21.4%, 25.6%] |
| departure | through_2023 | 1,382 | 492 / 126 | 0.13 [-0.41, 0.67] | 41.4% [38.8%, 44.0%] |
| departure | year_2024_period | 480 | 158 / 52 | 0.08 [-0.77, 0.89] | 48.1% [45.1%, 50.9%] |
| departure | years_2025_2026 | 1,074 | 378 / 90 | 0.72 [-0.17, 1.64] | 45.8% [43.5%, 48.2%] |
| touch | all | 2,379 | 964 / 267 | -0.05 [-0.50, 0.44] | 49.6% [47.4%, 51.7%] |
| touch | common_50 | 2,195 | 949 / 267 | -0.15 [-0.60, 0.35] | 49.2% [47.1%, 51.4%] |
| touch | age_ge30 | 1,210 | 727 / 265 | 0.32 [-0.33, 1.00] | 50.7% [47.7%, 53.6%] |
| touch | through_2023 | 1,110 | 458 / 126 | 0.11 [-0.48, 0.76] | 49.7% [46.9%, 52.6%] |
| touch | year_2024_period | 394 | 151 / 52 | 0.01 [-0.67, 0.64] | 48.2% [43.1%, 53.0%] |
| touch | years_2025_2026 | 875 | 355 / 90 | -0.27 [-1.20, 0.72] | 50.1% [46.5%, 53.4%] |

### Deterministic source-path examples

Examples are the earliest stable ID in each prespecified class. They illustrate mechanisms and exclusions, not representative trade quality. The source table includes reference available_at and known sigma for every minute; charts plot raw one-minute high/low and references. Source minute open time relative to entry is shown; contacts have interval resolution. Lines join minute OHLC observations for display and do not imply intraminute order or trades through gaps. The 2-sigma envelope is plotted; 2.5/3-sigma references are retained in the example-path table.

return: ES-ny-2021-06-28-P0002-K2-H10; lower side. Signal/confirmation 2021-06-28 09:36:00-04:00; entry 2021-06-28 09:36:00-04:00; deadline 2021-06-28 09:56:00-04:00 (New York time). Frozen sigma 0.52 points; signal VWAP 4,276.43. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-ny-2021-06-28-P0002-K2-H10](figures/example-ny-ES-return.svg)

non_return: ES-ny-2021-06-28-P0109-K2-H10; lower side. Signal/confirmation 2021-06-28 13:10:00-04:00; entry 2021-06-28 13:10:00-04:00; deadline 2021-06-28 13:30:00-04:00 (New York time). Frozen sigma 2.33 points; signal VWAP 4,270.61. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-ny-2021-06-28-P0109-K2-H10](figures/example-ny-ES-non_return.svg)

bounce: ES-ny-2021-06-29-P0063-T-H10; lower side. Signal/confirmation 2021-06-29 14:10:00-04:00; entry 2021-06-29 14:10:00-04:00; deadline 2021-06-29 14:30:00-04:00 (New York time). Frozen sigma 1.64 points; signal VWAP 4,286.33. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-ny-2021-06-29-P0063-T-H10](figures/example-ny-ES-bounce.svg)

through: ES-ny-2021-06-28-P0002-T-H10; lower side. Signal/confirmation 2021-06-28 09:56:00-04:00; entry 2021-06-28 09:56:00-04:00; deadline 2021-06-28 10:16:00-04:00 (New York time). Frozen sigma 3.45 points; signal VWAP 4,271.42. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-ny-2021-06-28-P0002-T-H10](figures/example-ny-ES-through.svg)

ambiguity: ES-ny-2021-06-29-P0031-T-H10; upper side. Signal/confirmation 2021-06-29 10:46:00-04:00; entry 2021-06-29 10:46:00-04:00; deadline 2021-06-29 11:06:00-04:00 (New York time). Frozen sigma 1.01 points; signal VWAP 4,287.24. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-ny-2021-06-29-P0031-T-H10](figures/example-ny-ES-ambiguity.svg)

exclusion: ES-ny-2021-06-28-P0166-K2-H50; upper side. Signal/confirmation 2021-06-28 15:04:00-04:00; entry 2021-06-28 15:04:00-04:00; deadline 2021-06-28 16:44:00-04:00 (New York time). Frozen sigma 2.71 points; signal VWAP 4,270.51. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: session_boundary.

![ES-ny-2021-06-28-P0166-K2-H50](figures/example-ny-ES-exclusion.svg)

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
| 2.0 | 5 | 1,477 | 27.46 [25.68, 29.28] / 18.00 | 26.78 [24.72, 29.08] / 19.25 | 26.78 [24.72, 29.08] / 19.25 | 27.46 [25.68, 29.28] / 18.00 | 1.17 [-0.92, 3.26] | -1.17 [-3.26, 0.92] | 51.3% [48.7%, 53.8%] | 51.3% [48.7%, 53.8%] | 52.6% [50.2%, 55.2%] | 6 | 881 / 270 | 17 | adequate descriptive support |
| 2.0 | 10 | 1,466 | 37.82 [35.51, 40.29] / 25.50 | 37.10 [33.93, 40.74] / 26.75 | 37.10 [33.93, 40.74] / 26.75 | 37.82 [35.51, 40.29] / 25.50 | 0.82 [-2.51, 4.06] | -0.82 [-4.06, 2.51] | 51.6% [48.8%, 54.1%] | 51.6% [48.8%, 54.1%] | 49.5% [46.7%, 52.0%] | 4 | 876 / 270 | 28 | adequate descriptive support |
| 2.0 | 15 | 1,458 | 46.46 [43.57, 49.56] / 31.25 | 45.50 [41.21, 50.92] / 32.75 | 45.50 [41.21, 50.92] / 32.75 | 46.46 [43.57, 49.56] / 31.25 | 1.07 [-3.23, 5.65] | -1.07 [-5.65, 3.23] | 53.4% [50.6%, 56.1%] | 53.4% [50.6%, 56.1%] | 51.9% [49.2%, 54.7%] | 1 | 872 / 270 | 36 | adequate descriptive support |
| 2.0 | 20 | 1,446 | 53.09 [49.57, 56.91] / 35.00 | 51.10 [46.52, 57.00] / 39.00 | 51.10 [46.52, 57.00] / 39.00 | 53.09 [49.57, 56.91] / 35.00 | 2.49 [-1.97, 7.03] | -2.49 [-7.03, 1.97] | 55.2% [52.4%, 57.6%] | 55.2% [52.4%, 57.6%] | 52.2% [49.6%, 54.9%] | 4 | 870 / 270 | 48 | adequate descriptive support |
| 2.0 | 50 | 1,372 | 75.47 [69.80, 81.70] / 50.38 | 72.87 [66.96, 80.07] / 55.75 | 72.87 [66.96, 80.07] / 55.75 | 75.47 [69.80, 81.70] / 50.38 | 5.25 [-1.38, 11.70] | -5.25 [-11.70, 1.38] | 57.0% [54.1%, 59.9%] | 57.0% [54.1%, 59.9%] | 49.1% [46.5%, 51.8%] | 2 | 854 / 270 | 122 | adequate descriptive support |
| 2.5 | 5 | 707 | 27.46 [25.37, 29.76] / 18.25 | 26.39 [23.40, 29.91] / 18.00 | 26.39 [23.40, 29.91] / 18.00 | 27.46 [25.37, 29.76] / 18.25 | -0.37 [-3.13, 2.35] | 0.37 [-2.35, 3.13] | 49.6% [46.0%, 53.4%] | 49.6% [46.0%, 53.4%] | 50.8% [47.5%, 54.3%] | 1 | 530 / 241 | 12 | adequate descriptive support |
| 2.5 | 10 | 704 | 39.72 [36.43, 43.47] / 25.50 | 36.53 [31.89, 42.42] / 24.75 | 36.53 [31.89, 42.42] / 24.75 | 39.72 [36.43, 43.47] / 25.50 | -2.03 [-6.37, 2.09] | 2.03 [-2.09, 6.37] | 49.6% [45.6%, 53.4%] | 49.6% [45.6%, 53.4%] | 48.9% [45.1%, 52.5%] | 1 | 528 / 241 | 15 | adequate descriptive support |
| 2.5 | 15 | 699 | 48.02 [44.02, 52.64] / 32.00 | 43.80 [38.26, 51.04] / 30.50 | 43.80 [38.26, 51.04] / 30.50 | 48.02 [44.02, 52.64] / 32.00 | -1.91 [-6.84, 3.09] | 1.91 [-3.09, 6.84] | 49.4% [45.4%, 53.2%] | 49.4% [45.4%, 53.2%] | 51.2% [47.4%, 55.0%] | 1 | 525 / 241 | 20 | adequate descriptive support |
| 2.5 | 20 | 695 | 55.15 [50.44, 60.44] / 35.50 | 48.95 [43.04, 56.67] / 35.50 | 48.95 [43.04, 56.67] / 35.50 | 55.15 [50.44, 60.44] / 35.50 | -2.21 [-7.82, 3.46] | 2.21 [-3.46, 7.82] | 51.1% [47.2%, 54.9%] | 51.1% [47.2%, 54.9%] | 48.1% [44.3%, 52.0%] | 2 | 522 / 241 | 24 | adequate descriptive support |
| 2.5 | 50 | 650 | 78.15 [70.59, 86.22] / 52.88 | 71.24 [63.67, 80.67] / 53.75 | 71.24 [63.67, 80.67] / 53.75 | 78.15 [70.59, 86.22] / 52.88 | -0.25 [-9.52, 8.32] | 0.25 [-8.32, 9.52] | 54.5% [50.5%, 58.6%] | 54.5% [50.5%, 58.6%] | 47.4% [43.7%, 50.9%] | 1 | 502 / 238 | 69 | adequate descriptive support |
| 3.0 | 5 | 209 | 32.06 [27.74, 36.40] / 22.25 | 26.23 [22.33, 30.64] / 17.50 | 26.23 [22.33, 30.64] / 17.50 | 32.06 [27.74, 36.40] / 22.25 | -2.96 [-8.18, 2.35] | 2.96 [-2.35, 8.18] | 44.5% [38.1%, 51.3%] | 44.5% [38.1%, 51.3%] | 53.6% [47.1%, 60.2%] | 1 | 185 / 143 | 4 | adequate descriptive support |
| 3.0 | 10 | 208 | 42.34 [37.03, 48.03] / 29.50 | 40.02 [31.92, 51.21] / 25.50 | 40.02 [31.92, 51.21] / 25.50 | 42.34 [37.03, 48.03] / 29.50 | 3.93 [-6.07, 16.19] | -3.93 [-16.19, 6.07] | 51.0% [44.3%, 57.4%] | 51.0% [44.3%, 57.4%] | 55.8% [48.9%, 62.8%] | 1 | 184 / 143 | 5 | adequate descriptive support |
| 3.0 | 15 | 208 | 48.82 [42.91, 54.71] / 35.12 | 49.61 [39.29, 64.34] / 32.62 | 49.61 [39.29, 64.34] / 32.62 | 48.82 [42.91, 54.71] / 35.12 | 7.74 [-4.05, 23.61] | -7.74 [-23.61, 4.05] | 51.0% [44.3%, 57.4%] | 51.0% [44.3%, 57.4%] | 52.9% [45.5%, 59.9%] | 0 | 184 / 143 | 5 | adequate descriptive support |
| 3.0 | 20 | 207 | 55.31 [48.61, 62.13] / 38.25 | 56.14 [45.36, 71.23] / 37.75 | 56.14 [45.36, 71.23] / 37.75 | 55.31 [48.61, 62.13] / 38.25 | 10.11 [-1.64, 24.13] | -10.11 [-24.13, 1.64] | 52.7% [45.8%, 59.8%] | 52.7% [45.8%, 59.8%] | 54.6% [48.6%, 61.2%] | 1 | 183 / 142 | 6 | adequate descriptive support |
| 3.0 | 50 | 184 | 76.53 [65.72, 87.69] / 53.00 | 78.05 [63.84, 97.72] / 55.12 | 78.05 [63.84, 97.72] / 55.12 | 76.53 [65.72, 87.69] / 53.00 | 7.19 [-12.15, 28.77] | -7.19 [-28.77, 12.15] | 56.5% [49.1%, 63.5%] | 56.5% [49.1%, 63.5%] | 45.7% [38.7%, 52.4%] | 0 | 170 / 134 | 29 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,477 | 397 | 26.9% [24.9%, 28.9%] | 1,080 | 3.0 / 4.0 | 4 | 0 | 17 | 58 | 0 |
| 2.0 | 5 | frozen | 1,477 | 339 | 23.0% [20.9%, 25.0%] | 1,138 | 2.0 / 4.0 | 4 | 0 | 17 | 58 | 0 |
| 2.0 | 10 | evolving | 1,466 | 581 | 39.6% [37.5%, 41.8%] | 885 | 4.0 / 6.0 | 9 | 2 | 28 | 99 | 0 |
| 2.0 | 10 | frozen | 1,466 | 482 | 32.9% [30.7%, 35.1%] | 984 | 3.0 / 6.0 | 9 | 2 | 28 | 99 | 0 |
| 2.0 | 15 | evolving | 1,458 | 690 | 47.3% [45.2%, 49.4%] | 768 | 5.0 / 8.0 | 13 | 2 | 36 | 122 | 0 |
| 2.0 | 15 | frozen | 1,458 | 568 | 39.0% [36.7%, 41.2%] | 890 | 4.0 / 9.0 | 13 | 2 | 36 | 122 | 0 |
| 2.0 | 20 | evolving | 1,446 | 762 | 52.7% [50.7%, 54.7%] | 684 | 5.0 / 10.0 | 18 | 2 | 48 | 144 | 0 |
| 2.0 | 20 | frozen | 1,446 | 618 | 42.7% [40.4%, 45.2%] | 828 | 5.0 / 10.0 | 18 | 2 | 48 | 144 | 0 |
| 2.0 | 50 | evolving | 1,372 | 960 | 70.0% [67.8%, 72.1%] | 412 | 7.0 / 18.2 | 40 | 2 | 122 | 190 | 0 |
| 2.0 | 50 | frozen | 1,372 | 770 | 56.1% [53.7%, 58.8%] | 602 | 7.0 / 18.0 | 40 | 2 | 122 | 190 | 0 |
| 2.5 | 5 | evolving | 707 | 163 | 23.1% [20.0%, 26.2%] | 544 | 3.0 / 4.0 | 1 | 0 | 12 | 29 | 0 |
| 2.5 | 5 | frozen | 707 | 134 | 19.0% [16.2%, 21.7%] | 573 | 2.0 / 3.0 | 1 | 0 | 12 | 29 | 0 |
| 2.5 | 10 | evolving | 704 | 242 | 34.4% [31.1%, 37.5%] | 462 | 4.0 / 6.0 | 5 | 2 | 15 | 44 | 0 |
| 2.5 | 10 | frozen | 704 | 198 | 28.1% [25.0%, 31.1%] | 506 | 3.0 / 6.0 | 5 | 2 | 15 | 44 | 0 |
| 2.5 | 15 | evolving | 699 | 300 | 42.9% [39.8%, 46.2%] | 399 | 5.0 / 9.0 | 6 | 2 | 20 | 68 | 0 |
| 2.5 | 15 | frozen | 699 | 232 | 33.2% [30.0%, 36.3%] | 467 | 4.0 / 8.0 | 6 | 2 | 20 | 68 | 0 |
| 2.5 | 20 | evolving | 695 | 338 | 48.6% [45.4%, 51.9%] | 357 | 6.0 / 11.0 | 9 | 2 | 24 | 73 | 0 |
| 2.5 | 20 | frozen | 695 | 265 | 38.1% [34.9%, 41.4%] | 430 | 6.0 / 11.0 | 9 | 2 | 24 | 73 | 0 |
| 2.5 | 50 | evolving | 650 | 423 | 65.1% [61.7%, 68.4%] | 227 | 8.0 / 18.0 | 23 | 2 | 69 | 84 | 0 |
| 2.5 | 50 | frozen | 650 | 339 | 52.2% [48.4%, 55.8%] | 311 | 8.0 / 20.0 | 23 | 2 | 69 | 84 | 0 |
| 3.0 | 5 | evolving | 209 | 58 | 27.8% [21.7%, 34.0%] | 151 | 2.0 / 3.0 | 1 | 0 | 4 | 8 | 0 |
| 3.0 | 5 | frozen | 209 | 50 | 23.9% [18.2%, 29.7%] | 159 | 2.0 / 3.0 | 1 | 0 | 4 | 8 | 0 |
| 3.0 | 10 | evolving | 208 | 83 | 39.9% [33.8%, 45.8%] | 125 | 3.0 / 6.0 | 2 | 0 | 5 | 18 | 0 |
| 3.0 | 10 | frozen | 208 | 65 | 31.2% [25.3%, 36.9%] | 143 | 2.0 / 5.0 | 2 | 0 | 5 | 18 | 0 |
| 3.0 | 15 | evolving | 208 | 96 | 46.2% [40.2%, 51.8%] | 112 | 4.0 / 7.0 | 2 | 0 | 5 | 24 | 0 |
| 3.0 | 15 | frozen | 208 | 72 | 34.6% [28.4%, 40.1%] | 136 | 3.0 / 7.0 | 2 | 0 | 5 | 24 | 0 |
| 3.0 | 20 | evolving | 207 | 105 | 50.7% [44.8%, 56.3%] | 102 | 5.0 / 9.0 | 3 | 0 | 6 | 27 | 0 |
| 3.0 | 20 | frozen | 207 | 78 | 37.7% [31.1%, 43.4%] | 129 | 3.0 / 8.0 | 3 | 0 | 6 | 27 | 0 |
| 3.0 | 50 | evolving | 184 | 125 | 67.9% [61.9%, 74.2%] | 59 | 7.0 / 16.0 | 10 | 0 | 29 | 34 | 0 |
| 3.0 | 50 | frozen | 184 | 91 | 49.5% [42.2%, 56.3%] | 93 | 5.0 / 15.0 | 10 | 0 | 29 | 34 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,123 | 29.64 [27.59, 31.71] / 21.00 | 30.37 [27.42, 34.00] / 21.00 | 30.37 [27.42, 34.00] / 21.00 | 29.64 [27.59, 31.71] / 21.00 | 1.42 [-1.07, 3.93] | -1.42 [-3.93, 1.07] | 53.3% [50.2%, 56.4%] | 53.3% [50.2%, 56.4%] | 50.8% [47.7%, 54.0%] | 3 | 734 / 262 | 27 | adequate descriptive support | 446 / 441 / 119 / 117 | 0 |
| 2.0 | 10 | 1,118 | 40.68 [37.83, 43.73] / 29.50 | 40.72 [37.09, 45.03] / 27.88 | 40.72 [37.09, 45.03] / 27.88 | 40.68 [37.83, 43.73] / 29.50 | 1.76 [-1.77, 4.97] | -1.76 [-4.97, 1.77] | 52.9% [49.7%, 55.8%] | 52.9% [49.7%, 55.8%] | 49.1% [46.1%, 52.1%] | 2 | 730 / 261 | 32 | adequate descriptive support | 479 / 469 / 53 / 117 | 0 |
| 2.0 | 15 | 1,108 | 48.05 [44.70, 51.79] / 33.75 | 47.88 [43.64, 52.75] / 34.25 | 47.88 [43.64, 52.75] / 34.25 | 48.05 [44.70, 51.79] / 33.75 | 3.81 [-0.43, 7.99] | -3.81 [-7.99, 0.43] | 55.1% [52.2%, 58.2%] | 55.1% [52.2%, 58.2%] | 50.8% [47.8%, 53.9%] | 3 | 728 / 261 | 42 | adequate descriptive support | 490 / 476 / 25 / 117 | 0 |
| 2.0 | 20 | 1,102 | 54.28 [50.29, 58.81] / 37.00 | 54.49 [49.85, 59.49] / 40.12 | 54.49 [49.85, 59.49] / 40.12 | 54.28 [50.29, 58.81] / 37.00 | 5.42 [0.76, 9.80] | -5.42 [-9.80, -0.76] | 55.8% [52.6%, 59.0%] | 55.8% [52.6%, 59.0%] | 52.3% [49.3%, 55.3%] | 3 | 726 / 261 | 48 | adequate descriptive support | 492 / 480 / 13 / 117 | 0 |
| 2.0 | 50 | 1,051 | 76.74 [70.31, 84.05] / 51.25 | 75.16 [69.68, 80.87] / 58.50 | 75.16 [69.68, 80.87] / 58.50 | 76.74 [70.31, 84.05] / 51.25 | 5.38 [-1.48, 12.10] | -5.38 [-12.10, 1.48] | 57.8% [54.7%, 60.8%] | 57.8% [54.7%, 60.8%] | 51.9% [49.0%, 54.7%] | 1 | 707 / 261 | 99 | adequate descriptive support | 471 / 464 / 0 / 116 | 0 |
| 2.5 | 5 | 517 | 29.46 [26.73, 32.39] / 21.00 | 32.17 [27.46, 38.53] / 21.25 | 32.17 [27.46, 38.53] / 21.25 | 29.46 [26.73, 32.39] / 21.00 | 3.00 [-1.12, 7.05] | -3.00 [-7.05, 1.12] | 54.2% [49.7%, 58.5%] | 54.2% [49.7%, 58.5%] | 52.2% [47.9%, 56.5%] | 2 | 410 / 216 | 14 | adequate descriptive support | 206 / 192 / 63 / 56 | 0 |
| 2.5 | 10 | 517 | 40.85 [37.04, 44.62] / 29.50 | 42.74 [36.96, 50.34] / 30.00 | 42.74 [36.96, 50.34] / 30.00 | 40.85 [37.04, 44.62] / 29.50 | 1.63 [-3.77, 7.09] | -1.63 [-7.09, 3.77] | 52.8% [48.2%, 57.4%] | 52.8% [48.2%, 57.4%] | 47.4% [43.2%, 51.6%] | 1 | 410 / 216 | 14 | adequate descriptive support | 224 / 206 / 31 / 56 | 0 |
| 2.5 | 15 | 512 | 48.54 [44.08, 53.27] / 35.00 | 49.65 [43.38, 57.61] / 34.88 | 49.65 [43.38, 57.61] / 34.88 | 48.54 [44.08, 53.27] / 35.00 | 4.12 [-3.08, 11.60] | -4.12 [-11.60, 3.08] | 56.1% [51.5%, 60.3%] | 56.1% [51.5%, 60.3%] | 48.6% [44.2%, 52.9%] | 1 | 407 / 216 | 19 | adequate descriptive support | 232 / 211 / 13 / 56 | 0 |
| 2.5 | 20 | 507 | 55.71 [50.43, 61.55] / 37.50 | 56.42 [49.85, 64.77] / 42.25 | 56.42 [49.85, 64.77] / 42.25 | 55.71 [50.43, 61.55] / 37.50 | 3.82 [-4.13, 11.25] | -3.82 [-11.25, 4.13] | 55.2% [50.5%, 59.8%] | 55.2% [50.5%, 59.8%] | 49.9% [45.5%, 54.4%] | 0 | 403 / 214 | 24 | adequate descriptive support | 232 / 212 / 7 / 56 | 0 |
| 2.5 | 50 | 476 | 80.77 [71.78, 91.16] / 52.12 | 76.27 [68.22, 85.56] / 58.75 | 76.27 [68.22, 85.56] / 58.75 | 80.77 [71.78, 91.16] / 52.12 | -1.01 [-11.84, 9.21] | 1.01 [-9.21, 11.84] | 56.1% [51.7%, 60.7%] | 56.1% [51.7%, 60.7%] | 53.2% [48.8%, 57.6%] | 1 | 384 / 209 | 55 | adequate descriptive support | 218 / 203 / 0 / 55 | 0 |
| 3.0 | 5 | 155 | 26.82 [22.42, 31.38] / 19.75 | 39.40 [30.90, 52.60] / 24.25 | 39.40 [30.90, 52.60] / 24.25 | 26.82 [22.42, 31.38] / 19.75 | 11.36 [3.48, 20.30] | -11.36 [-20.30, -3.48] | 58.1% [50.3%, 65.9%] | 58.1% [50.3%, 65.9%] | 49.0% [40.8%, 57.1%] | 2 | 145 / 121 | 0 | adequate descriptive support | 67 / 47 / 17 / 24 | 0 |
| 3.0 | 10 | 155 | 35.90 [30.17, 41.53] / 28.75 | 52.91 [42.19, 68.35] / 31.25 | 52.91 [42.19, 68.35] / 31.25 | 35.90 [30.17, 41.53] / 28.75 | 14.85 [4.97, 26.49] | -14.85 [-26.49, -4.97] | 58.1% [50.3%, 66.1%] | 58.1% [50.3%, 66.1%] | 45.8% [38.0%, 53.9%] | 0 | 145 / 121 | 0 | adequate descriptive support | 70 / 49 / 12 / 24 | 0 |
| 3.0 | 15 | 152 | 41.79 [35.78, 48.13] / 33.50 | 61.44 [49.88, 77.16] / 36.25 | 61.44 [49.88, 77.16] / 36.25 | 41.79 [35.78, 48.13] / 33.50 | 20.25 [7.08, 35.19] | -20.25 [-35.19, -7.08] | 61.2% [53.2%, 68.6%] | 61.2% [53.2%, 68.6%] | 50.0% [42.2%, 57.0%] | 1 | 143 / 119 | 3 | adequate descriptive support | 72 / 50 / 6 / 24 | 0 |
| 3.0 | 20 | 151 | 48.99 [41.26, 57.12] / 33.50 | 69.25 [56.97, 85.59] / 47.25 | 69.25 [56.97, 85.59] / 47.25 | 48.99 [41.26, 57.12] / 33.50 | 21.72 [4.78, 39.87] | -21.72 [-39.87, -4.78] | 58.9% [51.0%, 66.7%] | 58.9% [51.0%, 66.7%] | 55.0% [46.5%, 63.7%] | 0 | 142 / 118 | 4 | adequate descriptive support | 73 / 51 / 3 / 24 | 0 |
| 3.0 | 50 | 141 | 68.90 [57.10, 82.01] / 46.75 | 86.00 [70.88, 105.69] / 64.25 | 86.00 [70.88, 105.69] / 64.25 | 68.90 [57.10, 82.01] / 46.75 | 15.59 [-3.81, 36.24] | -15.59 [-36.24, 3.81] | 63.1% [55.7%, 70.5%] | 63.1% [55.7%, 70.5%] | 62.4% [54.2%, 70.7%] | 0 | 133 / 112 | 14 | adequate descriptive support | 69 / 49 / 0 / 23 | 0 |

### Lower departure / arrival: continuation and bounce short; fade and through long

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,517 | 31.12 [29.16, 33.45] / 22.50 | 31.89 [30.01, 33.86] / 23.50 | 31.89 [30.01, 33.86] / 23.50 | 31.12 [29.16, 33.45] / 22.50 | -0.57 [-2.81, 1.62] | 0.57 [-1.62, 2.81] | 49.4% [47.0%, 51.9%] | 50.4% [48.0%, 52.9%] | 50.8% [48.4%, 53.3%] | 2 | 896 / 271 | 17 | adequate descriptive support |
| 2.0 | 10 | 1,508 | 41.96 [39.33, 45.22] / 30.38 | 43.88 [41.24, 46.80] / 31.38 | 43.88 [41.24, 46.80] / 31.38 | 41.96 [39.33, 45.22] / 30.38 | 0.30 [-2.86, 3.50] | -0.30 [-3.50, 2.86] | 48.9% [46.2%, 51.4%] | 51.0% [48.5%, 53.7%] | 50.8% [48.1%, 53.3%] | 2 | 894 / 271 | 26 | adequate descriptive support |
| 2.0 | 15 | 1,503 | 50.06 [46.79, 53.89] / 34.50 | 52.80 [49.44, 56.34] / 38.00 | 52.80 [49.44, 56.34] / 38.00 | 50.06 [46.79, 53.89] / 34.50 | -0.35 [-4.49, 3.53] | 0.35 [-3.53, 4.49] | 48.4% [45.8%, 51.0%] | 51.5% [48.9%, 54.1%] | 49.8% [47.2%, 52.2%] | 1 | 892 / 271 | 31 | adequate descriptive support |
| 2.0 | 20 | 1,497 | 56.78 [52.73, 61.82] / 40.25 | 59.54 [55.70, 63.52] / 42.00 | 59.54 [55.70, 63.52] / 42.00 | 56.78 [52.73, 61.82] / 40.25 | -0.67 [-5.79, 4.17] | 0.67 [-4.17, 5.79] | 47.8% [45.1%, 50.4%] | 52.2% [49.6%, 54.9%] | 50.8% [48.3%, 53.4%] | 0 | 892 / 271 | 37 | adequate descriptive support |
| 2.0 | 50 | 1,423 | 78.62 [73.23, 84.72] / 58.25 | 84.72 [78.84, 90.80] / 61.75 | 84.72 [78.84, 90.80] / 61.75 | 78.62 [73.23, 84.72] / 58.25 | 0.11 [-6.32, 6.76] | -0.11 [-6.76, 6.32] | 47.4% [44.5%, 50.4%] | 52.4% [49.5%, 55.3%] | 50.7% [48.2%, 53.3%] | 2 | 876 / 271 | 111 | adequate descriptive support |
| 2.5 | 5 | 784 | 30.57 [28.14, 33.17] / 22.62 | 30.92 [28.73, 33.19] / 23.25 | 30.92 [28.73, 33.19] / 23.25 | 30.57 [28.14, 33.17] / 22.62 | -1.62 [-4.71, 1.38] | 1.62 [-1.38, 4.71] | 48.2% [44.8%, 51.7%] | 51.8% [48.3%, 55.2%] | 51.0% [47.3%, 54.9%] | 0 | 574 / 248 | 10 | adequate descriptive support |
| 2.5 | 10 | 780 | 41.44 [38.17, 44.93] / 30.25 | 43.63 [40.58, 46.94] / 31.75 | 43.63 [40.58, 46.94] / 31.75 | 41.44 [38.17, 44.93] / 30.25 | 0.30 [-3.71, 4.26] | -0.30 [-4.26, 3.71] | 47.9% [44.3%, 51.4%] | 52.1% [48.6%, 55.7%] | 54.2% [50.7%, 57.7%] | 0 | 572 / 248 | 14 | adequate descriptive support |
| 2.5 | 15 | 775 | 49.26 [45.33, 53.58] / 34.50 | 52.33 [48.26, 56.37] / 38.00 | 52.33 [48.26, 56.37] / 38.00 | 49.26 [45.33, 53.58] / 34.50 | 0.24 [-5.38, 5.68] | -0.24 [-5.68, 5.38] | 47.9% [44.4%, 51.3%] | 52.0% [48.6%, 55.5%] | 50.2% [46.5%, 53.7%] | 1 | 571 / 248 | 19 | adequate descriptive support |
| 2.5 | 20 | 771 | 55.29 [50.90, 60.02] / 39.75 | 58.94 [54.03, 63.78] / 42.50 | 58.94 [54.03, 63.78] / 42.50 | 55.29 [50.90, 60.02] / 39.75 | -0.44 [-6.41, 5.46] | 0.44 [-5.46, 6.41] | 46.0% [42.6%, 49.5%] | 53.8% [50.3%, 57.3%] | 50.2% [46.7%, 53.6%] | 1 | 570 / 248 | 23 | adequate descriptive support |
| 2.5 | 50 | 730 | 76.71 [70.47, 83.01] / 56.38 | 84.80 [77.84, 92.53] / 60.00 | 84.80 [77.84, 92.53] / 60.00 | 76.71 [70.47, 83.01] / 56.38 | 2.68 [-6.12, 11.23] | -2.68 [-11.23, 6.12] | 47.9% [44.3%, 51.6%] | 51.9% [48.3%, 55.6%] | 48.6% [45.2%, 52.1%] | 1 | 550 / 247 | 64 | adequate descriptive support |
| 3.0 | 5 | 241 | 29.55 [25.82, 33.71] / 20.75 | 32.40 [28.68, 36.61] / 24.75 | 32.40 [28.68, 36.61] / 24.75 | 29.55 [25.82, 33.71] / 20.75 | 0.10 [-5.16, 5.52] | -0.10 [-5.52, 5.16] | 51.0% [44.6%, 57.2%] | 48.5% [42.3%, 55.0%] | 51.0% [45.3%, 56.9%] | 1 | 208 / 155 | 4 | adequate descriptive support |
| 3.0 | 10 | 238 | 38.72 [33.79, 43.89] / 29.62 | 46.99 [41.46, 53.02] / 35.25 | 46.99 [41.46, 53.02] / 35.25 | 38.72 [33.79, 43.89] / 29.62 | 4.21 [-3.57, 12.54] | -4.21 [-12.54, 3.57] | 50.0% [43.0%, 57.0%] | 50.0% [43.0%, 57.0%] | 56.7% [50.4%, 63.2%] | 0 | 205 / 154 | 7 | adequate descriptive support |
| 3.0 | 15 | 235 | 46.10 [40.36, 52.09] / 34.00 | 56.71 [49.30, 65.33] / 41.75 | 56.71 [49.30, 65.33] / 41.75 | 46.10 [40.36, 52.09] / 34.00 | 7.21 [-2.46, 17.67] | -7.21 [-17.67, 2.46] | 50.2% [43.8%, 57.2%] | 49.8% [42.8%, 56.2%] | 47.2% [40.5%, 53.5%] | 0 | 204 / 153 | 10 | adequate descriptive support |
| 3.0 | 20 | 234 | 51.35 [45.17, 58.03] / 36.75 | 63.91 [54.97, 74.80] / 44.00 | 63.91 [54.97, 74.80] / 44.00 | 51.35 [45.17, 58.03] / 36.75 | 4.20 [-6.77, 16.12] | -4.20 [-16.12, 6.77] | 46.2% [39.6%, 52.8%] | 53.4% [46.5%, 59.9%] | 51.7% [45.1%, 58.4%] | 1 | 204 / 153 | 11 | adequate descriptive support |
| 3.0 | 50 | 219 | 72.14 [63.25, 81.68] / 52.00 | 89.82 [76.93, 104.08] / 68.50 | 89.82 [76.93, 104.08] / 68.50 | 72.14 [63.25, 81.68] / 52.00 | 10.70 [-6.91, 29.07] | -10.70 [-29.07, 6.91] | 50.2% [43.0%, 57.4%] | 49.3% [42.0%, 56.6%] | 50.2% [43.7%, 56.8%] | 1 | 194 / 148 | 26 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,517 | 460 | 30.3% [28.1%, 32.5%] | 1,057 | 2.0 / 4.0 | 3 | 3 | 17 | 72 | 0 |
| 2.0 | 5 | frozen | 1,517 | 388 | 25.6% [23.6%, 27.8%] | 1,129 | 2.0 / 3.0 | 3 | 3 | 17 | 72 | 0 |
| 2.0 | 10 | evolving | 1,508 | 651 | 43.2% [40.8%, 45.5%] | 857 | 3.0 / 6.0 | 5 | 4 | 26 | 120 | 0 |
| 2.0 | 10 | frozen | 1,508 | 531 | 35.2% [32.8%, 37.6%] | 977 | 3.0 / 6.0 | 5 | 4 | 26 | 120 | 0 |
| 2.0 | 15 | evolving | 1,503 | 775 | 51.6% [49.3%, 54.0%] | 728 | 4.0 / 8.0 | 9 | 5 | 31 | 147 | 0 |
| 2.0 | 15 | frozen | 1,503 | 628 | 41.8% [39.3%, 44.3%] | 875 | 4.0 / 8.0 | 9 | 5 | 31 | 147 | 0 |
| 2.0 | 20 | evolving | 1,497 | 859 | 57.4% [55.1%, 59.8%] | 638 | 5.0 / 10.0 | 12 | 5 | 37 | 155 | 0 |
| 2.0 | 20 | frozen | 1,497 | 704 | 47.0% [44.6%, 49.5%] | 793 | 4.5 / 10.0 | 12 | 5 | 37 | 155 | 0 |
| 2.0 | 50 | evolving | 1,423 | 1,065 | 74.8% [72.6%, 76.9%] | 358 | 7.0 / 17.0 | 27 | 5 | 111 | 203 | 0 |
| 2.0 | 50 | frozen | 1,423 | 862 | 60.6% [58.0%, 63.0%] | 561 | 7.0 / 16.0 | 27 | 5 | 111 | 203 | 0 |
| 2.5 | 5 | evolving | 784 | 187 | 23.9% [20.9%, 26.8%] | 597 | 2.0 / 4.0 | 1 | 2 | 10 | 29 | 0 |
| 2.5 | 5 | frozen | 784 | 158 | 20.2% [17.3%, 23.1%] | 626 | 2.0 / 3.8 | 1 | 2 | 10 | 29 | 0 |
| 2.5 | 10 | evolving | 780 | 286 | 36.7% [33.5%, 39.8%] | 494 | 4.0 / 6.0 | 2 | 2 | 14 | 63 | 0 |
| 2.5 | 10 | frozen | 780 | 223 | 28.6% [25.6%, 31.8%] | 557 | 3.0 / 6.0 | 2 | 2 | 14 | 63 | 0 |
| 2.5 | 15 | evolving | 775 | 351 | 45.3% [42.1%, 48.6%] | 424 | 5.0 / 9.0 | 3 | 3 | 19 | 74 | 0 |
| 2.5 | 15 | frozen | 775 | 277 | 35.7% [32.6%, 39.1%] | 498 | 4.0 / 9.0 | 3 | 3 | 19 | 74 | 0 |
| 2.5 | 20 | evolving | 771 | 392 | 50.8% [47.4%, 54.2%] | 379 | 6.0 / 11.0 | 4 | 3 | 23 | 81 | 0 |
| 2.5 | 20 | frozen | 771 | 311 | 40.3% [37.0%, 43.7%] | 460 | 5.0 / 11.0 | 4 | 3 | 23 | 81 | 0 |
| 2.5 | 50 | evolving | 730 | 507 | 69.5% [66.3%, 72.4%] | 223 | 8.0 / 20.0 | 13 | 3 | 64 | 107 | 0 |
| 2.5 | 50 | frozen | 730 | 400 | 54.8% [51.0%, 58.4%] | 330 | 9.0 / 19.2 | 13 | 3 | 64 | 107 | 0 |
| 3.0 | 5 | evolving | 241 | 62 | 25.7% [20.6%, 30.8%] | 179 | 2.0 / 3.0 | 0 | 0 | 4 | 10 | 0 |
| 3.0 | 5 | frozen | 241 | 52 | 21.6% [16.4%, 26.5%] | 189 | 2.0 / 3.0 | 0 | 0 | 4 | 10 | 0 |
| 3.0 | 10 | evolving | 238 | 90 | 37.8% [32.2%, 43.4%] | 148 | 3.0 / 6.0 | 0 | 0 | 7 | 22 | 0 |
| 3.0 | 10 | frozen | 238 | 68 | 28.6% [23.2%, 34.1%] | 170 | 3.0 / 5.0 | 0 | 0 | 7 | 22 | 0 |
| 3.0 | 15 | evolving | 235 | 107 | 45.5% [39.4%, 51.8%] | 128 | 4.0 / 8.0 | 0 | 0 | 10 | 27 | 0 |
| 3.0 | 15 | frozen | 235 | 80 | 34.0% [28.6%, 39.4%] | 155 | 3.0 / 7.2 | 0 | 0 | 10 | 27 | 0 |
| 3.0 | 20 | evolving | 234 | 116 | 49.6% [43.2%, 55.8%] | 118 | 5.0 / 9.2 | 0 | 0 | 11 | 24 | 0 |
| 3.0 | 20 | frozen | 234 | 92 | 39.3% [33.3%, 45.1%] | 142 | 4.0 / 11.0 | 0 | 0 | 11 | 24 | 0 |
| 3.0 | 50 | evolving | 219 | 150 | 68.5% [62.5%, 74.6%] | 69 | 8.0 / 18.8 | 3 | 0 | 26 | 32 | 0 |
| 3.0 | 50 | frozen | 219 | 118 | 53.9% [46.7%, 60.7%] | 101 | 7.5 / 18.8 | 3 | 0 | 26 | 32 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,243 | 27.37 [25.38, 29.52] / 18.50 | 27.64 [25.65, 29.59] / 19.00 | 27.64 [25.65, 29.59] / 19.00 | 27.37 [25.38, 29.52] / 18.50 | -0.26 [-2.58, 2.11] | 0.26 [-2.11, 2.58] | 48.7% [45.8%, 51.4%] | 50.7% [47.9%, 53.5%] | 49.9% [46.7%, 52.8%] | 8 | 794 / 271 | 25 | adequate descriptive support | 443 / 462 / 211 / 127 | 0 |
| 2.0 | 10 | 1,235 | 37.03 [34.41, 39.73] / 27.00 | 37.71 [34.86, 40.63] / 25.50 | 37.71 [34.86, 40.63] / 25.50 | 37.03 [34.41, 39.73] / 27.00 | -0.16 [-3.16, 2.99] | 0.16 [-2.99, 3.16] | 48.1% [45.3%, 50.9%] | 51.7% [48.9%, 54.5%] | 50.2% [47.5%, 52.9%] | 3 | 792 / 271 | 33 | adequate descriptive support | 495 / 510 / 102 / 128 | 0 |
| 2.0 | 15 | 1,225 | 44.94 [41.20, 49.46] / 32.75 | 45.50 [42.12, 49.00] / 30.75 | 45.50 [42.12, 49.00] / 30.75 | 44.94 [41.20, 49.46] / 32.75 | -1.08 [-5.30, 2.96] | 1.08 [-2.96, 5.30] | 48.9% [46.2%, 51.8%] | 51.0% [48.1%, 53.7%] | 49.8% [46.9%, 52.9%] | 1 | 790 / 271 | 43 | adequate descriptive support | 508 / 528 / 61 / 128 | 0 |
| 2.0 | 20 | 1,217 | 50.49 [46.43, 55.26] / 37.00 | 51.51 [47.82, 55.29] / 35.50 | 51.51 [47.82, 55.29] / 35.50 | 50.49 [46.43, 55.26] / 37.00 | -1.89 [-5.87, 2.16] | 1.89 [-2.16, 5.87] | 47.2% [44.3%, 50.1%] | 52.6% [49.8%, 55.5%] | 52.4% [49.9%, 54.8%] | 2 | 789 / 271 | 51 | adequate descriptive support | 519 / 538 / 32 / 128 | 0 |
| 2.0 | 50 | 1,137 | 72.86 [67.19, 79.21] / 52.50 | 75.78 [70.04, 81.64] / 53.75 | 75.78 [70.04, 81.64] / 53.75 | 72.86 [67.19, 79.21] / 52.50 | -1.95 [-8.29, 4.62] | 1.95 [-4.62, 8.29] | 47.8% [44.5%, 51.1%] | 52.1% [48.8%, 55.4%] | 50.0% [47.1%, 52.7%] | 1 | 756 / 271 | 131 | adequate descriptive support | 498 / 511 / 2 / 126 | 0 |
| 2.5 | 5 | 619 | 26.21 [23.92, 28.76] / 17.50 | 27.72 [25.29, 30.31] / 18.25 | 27.72 [25.29, 30.31] / 18.25 | 26.21 [23.92, 28.76] / 17.50 | 0.53 [-2.42, 3.40] | -0.53 [-3.40, 2.42] | 49.4% [45.7%, 52.9%] | 49.9% [46.5%, 53.6%] | 50.6% [46.4%, 54.6%] | 4 | 477 / 233 | 12 | adequate descriptive support | 226 / 226 / 117 / 50 | 0 |
| 2.5 | 10 | 614 | 35.40 [32.28, 38.82] / 25.12 | 37.52 [33.97, 41.16] / 25.38 | 37.52 [33.97, 41.16] / 25.38 | 35.40 [32.28, 38.82] / 25.12 | 1.26 [-2.82, 5.39] | -1.26 [-5.39, 2.82] | 48.5% [44.7%, 52.4%] | 51.3% [47.4%, 55.2%] | 49.2% [45.4%, 53.3%] | 1 | 476 / 233 | 17 | adequate descriptive support | 251 / 249 / 64 / 50 | 0 |
| 2.5 | 15 | 606 | 42.26 [38.43, 46.48] / 30.00 | 45.15 [40.98, 49.36] / 31.00 | 45.15 [40.98, 49.36] / 31.00 | 42.26 [38.43, 46.48] / 30.00 | 0.10 [-5.03, 5.33] | -0.10 [-5.33, 5.03] | 49.0% [45.0%, 53.1%] | 50.8% [46.8%, 54.8%] | 51.5% [47.4%, 55.7%] | 1 | 473 / 233 | 25 | adequate descriptive support | 258 / 254 / 44 / 50 | 0 |
| 2.5 | 20 | 599 | 48.28 [43.98, 52.99] / 34.25 | 50.81 [46.24, 55.54] / 35.25 | 50.81 [46.24, 55.54] / 35.25 | 48.28 [43.98, 52.99] / 34.25 | -2.68 [-8.08, 2.86] | 2.68 [-2.86, 8.08] | 47.1% [43.1%, 50.9%] | 52.9% [49.1%, 56.9%] | 56.1% [52.5%, 59.7%] | 0 | 470 / 232 | 32 | adequate descriptive support | 265 / 262 / 22 / 50 | 0 |
| 2.5 | 50 | 555 | 69.58 [63.34, 76.15] / 47.00 | 75.14 [68.07, 82.40] / 52.25 | 75.14 [68.07, 82.40] / 52.25 | 69.58 [63.34, 76.15] / 47.00 | 0.01 [-8.46, 8.81] | -0.01 [-8.81, 8.46] | 49.2% [44.8%, 53.5%] | 50.6% [46.2%, 55.0%] | 49.4% [45.0%, 53.7%] | 1 | 441 / 228 | 76 | adequate descriptive support | 254 / 251 / 2 / 48 | 0 |
| 3.0 | 5 | 185 | 25.79 [21.61, 30.35] / 16.25 | 26.41 [22.69, 30.36] / 18.00 | 26.41 [22.69, 30.36] / 18.00 | 25.79 [21.61, 30.35] / 16.25 | -1.40 [-6.78, 3.84] | 1.40 [-3.84, 6.78] | 46.5% [39.3%, 53.8%] | 51.9% [44.6%, 59.2%] | 53.5% [46.3%, 60.5%] | 3 | 164 / 131 | 4 | adequate descriptive support | 65 / 62 / 37 / 21 | 0 |
| 3.0 | 10 | 183 | 33.14 [28.30, 38.41] / 23.25 | 36.06 [30.83, 41.81] / 25.50 | 36.06 [30.83, 41.81] / 25.50 | 33.14 [28.30, 38.41] / 23.25 | 4.24 [-2.44, 11.32] | -4.24 [-11.32, 2.44] | 50.3% [43.5%, 57.5%] | 49.7% [42.5%, 56.5%] | 45.9% [39.0%, 52.9%] | 0 | 162 / 130 | 6 | adequate descriptive support | 73 / 67 / 22 / 21 | 0 |
| 3.0 | 15 | 180 | 39.00 [33.53, 44.96] / 28.25 | 44.29 [37.45, 52.08] / 31.12 | 44.29 [37.45, 52.08] / 31.12 | 39.00 [33.53, 44.96] / 28.25 | 3.97 [-5.23, 13.59] | -3.97 [-13.59, 5.23] | 51.7% [44.4%, 58.9%] | 47.8% [40.6%, 55.0%] | 55.0% [47.3%, 62.7%] | 1 | 160 / 128 | 9 | adequate descriptive support | 75 / 68 / 16 / 21 | 0 |
| 3.0 | 20 | 177 | 44.59 [38.14, 51.41] / 33.25 | 48.64 [40.86, 57.18] / 33.25 | 48.64 [40.86, 57.18] / 33.25 | 44.59 [38.14, 51.41] / 33.25 | -0.53 [-10.72, 10.36] | 0.53 [-10.36, 10.72] | 46.9% [39.3%, 54.7%] | 53.1% [45.3%, 60.7%] | 54.2% [46.5%, 61.8%] | 0 | 158 / 128 | 12 | adequate descriptive support | 79 / 69 / 8 / 21 | 0 |
| 3.0 | 50 | 163 | 65.19 [55.34, 75.55] / 46.75 | 68.76 [57.04, 81.83] / 48.75 | 68.76 [57.04, 81.83] / 48.75 | 65.19 [55.34, 75.55] / 46.75 | 2.50 [-14.57, 20.15] | -2.50 [-20.15, 14.57] | 48.5% [40.6%, 56.3%] | 51.5% [43.7%, 59.4%] | 47.2% [39.3%, 54.4%] | 0 | 144 / 119 | 26 | adequate descriptive support | 73 / 68 / 1 / 21 | 0 |

### Common cohort, distribution and year diagnostics

The horizon curves use the identical complete-50 cohort. Distribution quantiles and year diagnostics use each horizon’s eligible cohort. Year 2026 is partial. These diagnostics are descriptive on previously inspected history.

![NQ New York return](figures/ny-NQ-return.svg)

![NQ New York excursion](figures/ny-NQ-excursion.svg)

![NQ New York endpoint](figures/ny-NQ-endpoint.svg)

![NQ New York mae-mfe-distribution](figures/ny-NQ-mae-mfe-distribution.svg)

![NQ New York terminal-distribution](figures/ny-NQ-terminal-distribution.svg)

![NQ New York year-stability](figures/ny-NQ-year-stability.svg)

### Sensitivity and chronological periods at 10 candles

| Module | Scope | n | Days / weeks | Directional Δ [CI] | Return or bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- |
| departure | all | 2,974 | 1,152 / 273 | 0.56 [-1.44, 2.53] | 41.4% [39.9%, 42.9%] |
| departure | common_50 | 2,795 | 1,147 / 273 | 0.45 [-1.53, 2.53] | 43.7% [42.1%, 45.3%] |
| departure | age_ge30 | 1,725 | 993 / 272 | -0.29 [-2.38, 1.70] | 21.1% [19.3%, 22.9%] |
| departure | through_2023 | 1,436 | 557 / 131 | -1.07 [-3.29, 1.14] | 40.4% [38.1%, 42.7%] |
| departure | year_2024_period | 574 | 210 / 53 | 1.38 [-3.20, 5.60] | 44.3% [41.2%, 47.1%] |
| departure | years_2025_2026 | 964 | 385 / 90 | 2.50 [-2.15, 7.47] | 41.3% [38.8%, 43.8%] |
| touch | all | 2,353 | 1,054 / 273 | 0.75 [-1.53, 2.95] | 50.4% [48.3%, 52.4%] |
| touch | common_50 | 2,188 | 1,037 / 273 | 0.64 [-1.71, 2.86] | 50.1% [48.0%, 52.2%] |
| touch | age_ge30 | 1,147 | 724 / 270 | 1.40 [-1.69, 4.86] | 52.2% [49.5%, 55.1%] |
| touch | through_2023 | 1,131 | 512 / 131 | -0.05 [-2.45, 2.46] | 49.6% [46.9%, 52.4%] |
| touch | year_2024_period | 467 | 199 / 53 | 3.01 [-1.77, 7.72] | 50.3% [45.9%, 54.5%] |
| touch | years_2025_2026 | 755 | 343 / 89 | 0.55 [-4.55, 5.55] | 51.5% [47.6%, 55.4%] |

### Deterministic source-path examples

Examples are the earliest stable ID in each prespecified class. They illustrate mechanisms and exclusions, not representative trade quality. The source table includes reference available_at and known sigma for every minute; charts plot raw one-minute high/low and references. Source minute open time relative to entry is shown; contacts have interval resolution. Lines join minute OHLC observations for display and do not imply intraminute order or trades through gaps. The 2-sigma envelope is plotted; 2.5/3-sigma references are retained in the example-path table.

return: NQ-ny-2021-06-30-P0013-K2-H10; lower side. Signal/confirmation 2021-06-30 09:58:00-04:00; entry 2021-06-30 09:58:00-04:00; deadline 2021-06-30 10:18:00-04:00 (New York time). Frozen sigma 8.24 points; signal VWAP 14,549.34. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-ny-2021-06-30-P0013-K2-H10](figures/example-ny-NQ-return.svg)

non_return: NQ-ny-2021-06-28-P0020-K2-H10; upper side. Signal/confirmation 2021-06-28 10:12:00-04:00; entry 2021-06-28 10:12:00-04:00; deadline 2021-06-28 10:32:00-04:00 (New York time). Frozen sigma 11.77 points; signal VWAP 14,445.77. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-ny-2021-06-28-P0020-K2-H10](figures/example-ny-NQ-non_return.svg)

bounce: NQ-ny-2021-06-28-P0020-T-H10; upper side. Signal/confirmation 2021-06-28 11:02:00-04:00; entry 2021-06-28 11:02:00-04:00; deadline 2021-06-28 11:22:00-04:00 (New York time). Frozen sigma 15.76 points; signal VWAP 14,455.21. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-ny-2021-06-28-P0020-T-H10](figures/example-ny-NQ-bounce.svg)

through: NQ-ny-2021-06-29-P0003-T-H10; upper side. Signal/confirmation 2021-06-29 10:02:00-04:00; entry 2021-06-29 10:02:00-04:00; deadline 2021-06-29 10:22:00-04:00 (New York time). Frozen sigma 14.66 points; signal VWAP 14,505.13. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-ny-2021-06-29-P0003-T-H10](figures/example-ny-NQ-through.svg)

ambiguity: NQ-ny-2021-08-04-P0007-T-H10; upper side. Signal/confirmation 2021-08-04 09:48:00-04:00; entry 2021-08-04 09:48:00-04:00; deadline 2021-08-04 10:08:00-04:00 (New York time). Frozen sigma 3.74 points; signal VWAP 15,051.82. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-ny-2021-08-04-P0007-T-H10](figures/example-ny-NQ-ambiguity.svg)

exclusion: NQ-ny-2021-06-28-P0161-K2-H50; upper side. Signal/confirmation 2021-06-28 14:54:00-04:00; entry 2021-06-28 14:54:00-04:00; deadline 2021-06-28 16:34:00-04:00 (New York time). Frozen sigma 16.19 points; signal VWAP 14,463.99. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: session_boundary.

![NQ-ny-2021-06-28-P0161-K2-H50](figures/example-ny-NQ-exclusion.svg)

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
| 2.0 | 5 | 1,021 | 2.63 [2.36, 2.92] / 1.50 | 2.89 [2.54, 3.25] / 1.60 | 2.89 [2.54, 3.25] / 1.60 | 2.63 [2.36, 2.92] / 1.50 | 0.21 [-0.07, 0.50] | -0.21 [-0.50, 0.07] | 48.9% [45.8%, 51.9%] | 48.9% [45.8%, 51.9%] | 48.8% [45.7%, 52.0%] | 23 | 616 / 319 | 9 | adequate descriptive support |
| 2.0 | 10 | 1,019 | 3.73 [3.33, 4.15] / 2.00 | 3.95 [3.50, 4.43] / 2.30 | 3.95 [3.50, 4.43] / 2.30 | 3.73 [3.33, 4.15] / 2.00 | 0.11 [-0.24, 0.47] | -0.11 [-0.47, 0.24] | 51.0% [47.9%, 54.4%] | 51.0% [47.9%, 54.4%] | 46.2% [43.2%, 49.2%] | 10 | 616 / 319 | 11 | adequate descriptive support |
| 2.0 | 15 | 1,013 | 4.68 [4.17, 5.25] / 2.40 | 4.77 [4.22, 5.36] / 2.80 | 4.77 [4.22, 5.36] / 2.80 | 4.68 [4.17, 5.25] / 2.40 | 0.10 [-0.43, 0.64] | -0.10 [-0.64, 0.43] | 51.4% [48.4%, 54.6%] | 51.4% [48.4%, 54.6%] | 46.9% [43.7%, 50.0%] | 12 | 614 / 318 | 17 | adequate descriptive support |
| 2.0 | 20 | 1,006 | 5.34 [4.73, 6.02] / 2.70 | 5.34 [4.72, 5.99] / 3.20 | 5.34 [4.72, 5.99] / 3.20 | 5.34 [4.73, 6.02] / 2.70 | 0.10 [-0.52, 0.71] | -0.10 [-0.71, 0.52] | 51.8% [48.6%, 54.9%] | 51.8% [48.6%, 54.9%] | 46.9% [43.9%, 49.9%] | 12 | 613 / 318 | 24 | adequate descriptive support |
| 2.0 | 50 | 970 | 8.08 [7.08, 9.10] / 3.90 | 7.49 [6.63, 8.41] / 4.50 | 7.49 [6.63, 8.41] / 4.50 | 8.08 [7.08, 9.10] / 3.90 | -0.14 [-1.12, 0.86] | 0.14 [-0.86, 1.12] | 51.6% [48.2%, 55.0%] | 51.6% [48.2%, 55.0%] | 47.1% [44.0%, 50.1%] | 6 | 609 / 318 | 60 | adequate descriptive support |
| 2.5 | 5 | 398 | 2.60 [2.25, 2.97] / 1.40 | 3.23 [2.63, 3.89] / 1.50 | 3.23 [2.63, 3.89] / 1.50 | 2.60 [2.25, 2.97] / 1.40 | 0.59 [0.09, 1.13] | -0.59 [-1.13, -0.09] | 50.5% [45.3%, 55.7%] | 50.5% [45.3%, 55.7%] | 47.2% [42.1%, 52.3%] | 8 | 317 / 216 | 1 | adequate descriptive support |
| 2.5 | 10 | 396 | 3.58 [3.07, 4.11] / 2.00 | 4.36 [3.59, 5.17] / 2.20 | 4.36 [3.59, 5.17] / 2.20 | 3.58 [3.07, 4.11] / 2.00 | 0.43 [-0.20, 1.13] | -0.43 [-1.13, 0.20] | 52.8% [47.4%, 58.4%] | 52.8% [47.4%, 58.4%] | 48.0% [42.9%, 52.8%] | 4 | 316 / 216 | 3 | adequate descriptive support |
| 2.5 | 15 | 393 | 4.48 [3.78, 5.21] / 2.40 | 5.16 [4.25, 6.19] / 2.60 | 5.16 [4.25, 6.19] / 2.60 | 4.48 [3.78, 5.21] / 2.40 | 0.13 [-0.77, 1.05] | -0.13 [-1.05, 0.77] | 48.9% [43.9%, 54.1%] | 48.9% [43.9%, 54.1%] | 46.1% [41.3%, 51.1%] | 3 | 314 / 214 | 6 | adequate descriptive support |
| 2.5 | 20 | 390 | 5.15 [4.31, 6.07] / 2.70 | 5.77 [4.78, 6.88] / 3.05 | 5.77 [4.78, 6.88] / 3.05 | 5.15 [4.31, 6.07] / 2.70 | 0.19 [-0.88, 1.22] | -0.19 [-1.22, 0.88] | 50.5% [45.1%, 56.0%] | 50.5% [45.1%, 56.0%] | 47.9% [42.9%, 53.0%] | 6 | 311 / 212 | 9 | adequate descriptive support |
| 2.5 | 50 | 365 | 7.65 [6.38, 9.00] / 3.60 | 7.71 [6.36, 9.26] / 4.40 | 7.71 [6.36, 9.26] / 4.40 | 7.65 [6.38, 9.00] / 3.60 | 0.04 [-1.38, 1.59] | -0.04 [-1.59, 1.38] | 51.5% [46.2%, 56.7%] | 51.5% [46.2%, 56.7%] | 47.1% [41.8%, 52.4%] | 3 | 298 / 206 | 34 | adequate descriptive support |
| 3.0 | 5 | 100 | 2.82 [2.12, 3.65] / 1.50 | 3.68 [2.71, 4.90] / 1.80 | 3.68 [2.71, 4.90] / 1.80 | 2.82 [2.12, 3.65] / 1.50 | 0.85 [-0.07, 1.86] | -0.85 [-1.86, 0.07] | 50.0% [40.4%, 59.4%] | 50.0% [40.4%, 59.4%] | 47.0% [37.5%, 56.2%] | 3 | 94 / 90 | 2 | adequate descriptive support |
| 3.0 | 10 | 99 | 3.94 [2.95, 4.96] / 2.00 | 4.67 [3.45, 6.22] / 2.30 | 4.67 [3.45, 6.22] / 2.30 | 3.94 [2.95, 4.96] / 2.00 | -0.06 [-1.13, 1.00] | 0.06 [-1.00, 1.13] | 47.5% [37.3%, 57.3%] | 47.5% [37.3%, 57.3%] | 38.4% [28.6%, 48.4%] | 3 | 94 / 90 | 3 | events_below_100 |
| 3.0 | 15 | 97 | 5.28 [3.83, 6.82] / 2.80 | 5.18 [3.81, 6.80] / 2.60 | 5.18 [3.81, 6.80] / 2.60 | 5.28 [3.83, 6.82] / 2.80 | -0.67 [-2.40, 1.11] | 0.67 [-1.11, 2.40] | 45.4% [35.2%, 55.0%] | 45.4% [35.2%, 55.0%] | 45.4% [35.6%, 55.3%] | 1 | 93 / 89 | 5 | events_below_100 |
| 3.0 | 20 | 95 | 6.22 [4.54, 8.14] / 3.10 | 5.73 [4.20, 7.56] / 3.10 | 5.73 [4.20, 7.56] / 3.10 | 6.22 [4.54, 8.14] / 3.10 | -0.73 [-2.85, 1.37] | 0.73 [-1.37, 2.85] | 44.2% [34.3%, 54.4%] | 44.2% [34.3%, 54.4%] | 52.6% [42.6%, 63.0%] | 1 | 91 / 88 | 7 | events_below_100 |
| 3.0 | 50 | 87 | 9.17 [6.62, 12.41] / 4.10 | 7.45 [5.51, 9.76] / 4.00 | 7.45 [5.51, 9.76] / 4.00 | 9.17 [6.62, 12.41] / 4.10 | -0.34 [-3.22, 2.35] | 0.34 [-2.35, 3.22] | 51.7% [40.7%, 62.5%] | 51.7% [40.7%, 62.5%] | 55.2% [44.9%, 65.4%] | 0 | 83 / 80 | 15 | events_below_100 |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,021 | 329 | 32.2% [29.5%, 34.8%] | 692 | 2.0 / 4.0 | 0 | 0 | 9 | 58 | 0 |
| 2.0 | 5 | frozen | 1,021 | 271 | 26.5% [24.0%, 29.1%] | 750 | 2.0 / 4.0 | 0 | 0 | 9 | 58 | 0 |
| 2.0 | 10 | evolving | 1,019 | 463 | 45.4% [42.6%, 48.2%] | 556 | 3.0 / 6.0 | 5 | 0 | 11 | 101 | 0 |
| 2.0 | 10 | frozen | 1,019 | 362 | 35.5% [32.6%, 38.3%] | 657 | 3.0 / 5.8 | 5 | 0 | 11 | 101 | 0 |
| 2.0 | 15 | evolving | 1,013 | 542 | 53.5% [50.4%, 56.5%] | 471 | 4.0 / 8.0 | 7 | 0 | 17 | 109 | 0 |
| 2.0 | 15 | frozen | 1,013 | 433 | 42.7% [39.7%, 45.8%] | 580 | 4.0 / 8.0 | 7 | 0 | 17 | 109 | 0 |
| 2.0 | 20 | evolving | 1,006 | 585 | 58.2% [55.2%, 61.0%] | 421 | 4.0 / 10.0 | 9 | 0 | 24 | 114 | 0 |
| 2.0 | 20 | frozen | 1,006 | 471 | 46.8% [43.8%, 49.9%] | 535 | 4.0 / 10.0 | 9 | 0 | 24 | 114 | 0 |
| 2.0 | 50 | evolving | 970 | 729 | 75.2% [72.8%, 77.7%] | 241 | 7.0 / 16.0 | 21 | 0 | 60 | 139 | 0 |
| 2.0 | 50 | frozen | 970 | 590 | 60.8% [57.8%, 63.8%] | 380 | 6.5 / 17.0 | 21 | 0 | 60 | 139 | 0 |
| 2.5 | 5 | evolving | 398 | 103 | 25.9% [21.7%, 29.8%] | 295 | 2.0 / 4.0 | 0 | 0 | 1 | 16 | 0 |
| 2.5 | 5 | frozen | 398 | 87 | 21.9% [17.9%, 25.7%] | 311 | 1.0 / 3.5 | 0 | 0 | 1 | 16 | 0 |
| 2.5 | 10 | evolving | 396 | 145 | 36.6% [32.1%, 41.1%] | 251 | 3.0 / 6.0 | 0 | 0 | 3 | 33 | 0 |
| 2.5 | 10 | frozen | 396 | 112 | 28.3% [24.0%, 32.4%] | 284 | 2.0 / 5.0 | 0 | 0 | 3 | 33 | 0 |
| 2.5 | 15 | evolving | 393 | 171 | 43.5% [38.6%, 48.2%] | 222 | 4.0 / 8.0 | 1 | 0 | 6 | 45 | 0 |
| 2.5 | 15 | frozen | 393 | 126 | 32.1% [27.3%, 36.3%] | 267 | 3.0 / 8.0 | 1 | 0 | 6 | 45 | 0 |
| 2.5 | 20 | evolving | 390 | 185 | 47.4% [42.7%, 52.2%] | 205 | 4.0 / 10.0 | 1 | 0 | 9 | 49 | 0 |
| 2.5 | 20 | frozen | 390 | 136 | 34.9% [30.2%, 39.5%] | 254 | 4.0 / 8.2 | 1 | 0 | 9 | 49 | 0 |
| 2.5 | 50 | evolving | 365 | 242 | 66.3% [61.8%, 70.7%] | 123 | 7.5 / 19.8 | 6 | 0 | 34 | 53 | 0 |
| 2.5 | 50 | frozen | 365 | 189 | 51.8% [46.5%, 56.5%] | 176 | 8.0 / 21.0 | 6 | 0 | 34 | 53 | 0 |
| 3.0 | 5 | evolving | 100 | 30 | 30.0% [21.3%, 38.7%] | 70 | 1.0 / 3.8 | 0 | 0 | 2 | 6 | 0 |
| 3.0 | 5 | frozen | 100 | 24 | 24.0% [15.8%, 32.7%] | 76 | 1.0 / 2.0 | 0 | 0 | 2 | 6 | 0 |
| 3.0 | 10 | evolving | 99 | 43 | 43.4% [33.9%, 52.7%] | 56 | 3.0 / 6.0 | 0 | 0 | 3 | 9 | 0 |
| 3.0 | 10 | frozen | 99 | 34 | 34.3% [25.3%, 43.7%] | 65 | 1.5 / 6.0 | 0 | 0 | 3 | 9 | 0 |
| 3.0 | 15 | evolving | 97 | 50 | 51.5% [41.7%, 61.4%] | 47 | 4.0 / 8.0 | 0 | 0 | 5 | 14 | 0 |
| 3.0 | 15 | frozen | 97 | 36 | 37.1% [28.0%, 47.1%] | 61 | 2.0 / 7.0 | 0 | 0 | 5 | 14 | 0 |
| 3.0 | 20 | evolving | 95 | 51 | 53.7% [43.3%, 63.5%] | 44 | 4.0 / 8.0 | 0 | 0 | 7 | 14 | 0 |
| 3.0 | 20 | frozen | 95 | 37 | 38.9% [29.7%, 48.6%] | 58 | 2.0 / 7.0 | 0 | 0 | 7 | 14 | 0 |
| 3.0 | 50 | evolving | 87 | 58 | 66.7% [57.0%, 75.6%] | 29 | 5.0 / 10.8 | 3 | 0 | 15 | 9 | 0 |
| 3.0 | 50 | frozen | 87 | 49 | 56.3% [45.5%, 66.7%] | 38 | 6.0 / 20.0 | 3 | 0 | 15 | 9 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 818 | 2.87 [2.50, 3.28] / 1.40 | 2.58 [2.29, 2.91] / 1.50 | 2.58 [2.29, 2.91] / 1.50 | 2.87 [2.50, 3.28] / 1.40 | -0.11 [-0.42, 0.19] | 0.11 [-0.19, 0.42] | 51.5% [47.9%, 54.9%] | 51.5% [47.9%, 54.9%] | 47.1% [43.4%, 50.6%] | 16 | 547 / 306 | 7 | adequate descriptive support | 321 / 319 / 101 / 77 | 0 |
| 2.0 | 10 | 814 | 4.08 [3.57, 4.63] / 2.05 | 3.46 [3.09, 3.87] / 2.00 | 3.46 [3.09, 3.87] / 2.00 | 4.08 [3.57, 4.63] / 2.05 | -0.23 [-0.69, 0.19] | 0.23 [-0.19, 0.69] | 49.8% [45.9%, 53.6%] | 49.8% [45.9%, 53.6%] | 48.5% [45.0%, 51.9%] | 11 | 546 / 305 | 11 | adequate descriptive support | 351 / 346 / 40 / 77 | 0 |
| 2.0 | 15 | 808 | 5.02 [4.40, 5.72] / 2.40 | 4.11 [3.67, 4.60] / 2.30 | 4.11 [3.67, 4.60] / 2.30 | 5.02 [4.40, 5.72] / 2.40 | -0.37 [-0.91, 0.15] | 0.37 [-0.15, 0.91] | 50.6% [46.8%, 54.4%] | 50.6% [46.8%, 54.4%] | 47.6% [44.6%, 50.8%] | 8 | 544 / 305 | 17 | adequate descriptive support | 353 / 356 / 22 / 77 | 0 |
| 2.0 | 20 | 805 | 5.66 [4.94, 6.46] / 2.60 | 4.62 [4.13, 5.18] / 2.70 | 4.62 [4.13, 5.18] / 2.70 | 5.66 [4.94, 6.46] / 2.60 | -0.39 [-1.10, 0.27] | 0.39 [-0.27, 1.10] | 52.8% [49.0%, 56.6%] | 52.8% [49.0%, 56.6%] | 46.7% [43.5%, 49.8%] | 5 | 543 / 305 | 20 | adequate descriptive support | 361 / 359 / 8 / 77 | 0 |
| 2.0 | 50 | 783 | 8.32 [7.20, 9.51] / 3.80 | 6.91 [6.16, 7.72] / 4.20 | 6.91 [6.16, 7.72] / 4.20 | 8.32 [7.20, 9.51] / 3.80 | -0.28 [-1.36, 0.69] | 0.28 [-0.69, 1.36] | 55.0% [50.8%, 59.1%] | 55.0% [50.8%, 59.1%] | 48.8% [45.4%, 52.4%] | 7 | 531 / 302 | 42 | adequate descriptive support | 353 / 351 / 2 / 77 | 0 |
| 2.5 | 5 | 284 | 2.79 [2.29, 3.33] / 1.10 | 2.67 [2.17, 3.26] / 1.40 | 2.67 [2.17, 3.26] / 1.40 | 2.79 [2.29, 3.33] / 1.10 | -0.09 [-0.59, 0.43] | 0.09 [-0.43, 0.59] | 49.6% [43.7%, 55.3%] | 49.6% [43.7%, 55.3%] | 45.8% [39.5%, 51.9%] | 7 | 239 / 182 | 3 | adequate descriptive support | 106 / 94 / 53 / 31 | 0 |
| 2.5 | 10 | 283 | 4.13 [3.40, 4.98] / 1.90 | 3.44 [2.84, 4.15] / 1.80 | 3.44 [2.84, 4.15] / 1.80 | 4.13 [3.40, 4.98] / 1.90 | -0.45 [-1.26, 0.30] | 0.45 [-0.30, 1.26] | 49.8% [43.5%, 56.0%] | 49.8% [43.5%, 56.0%] | 50.9% [45.5%, 56.6%] | 5 | 239 / 182 | 4 | adequate descriptive support | 124 / 110 / 18 / 31 | 0 |
| 2.5 | 15 | 280 | 5.36 [4.35, 6.44] / 2.35 | 4.13 [3.42, 4.97] / 2.20 | 4.13 [3.42, 4.97] / 2.20 | 5.36 [4.35, 6.44] / 2.35 | -0.88 [-1.87, 0.10] | 0.88 [-0.10, 1.87] | 49.6% [43.0%, 56.2%] | 49.6% [43.0%, 56.2%] | 50.0% [44.4%, 55.5%] | 1 | 238 / 181 | 7 | adequate descriptive support | 125 / 115 / 9 / 31 | 0 |
| 2.5 | 20 | 278 | 5.91 [4.82, 7.07] / 2.60 | 4.74 [3.93, 5.63] / 2.45 | 4.74 [3.93, 5.63] / 2.45 | 5.91 [4.82, 7.07] / 2.60 | -0.61 [-1.66, 0.44] | 0.61 [-0.44, 1.66] | 51.1% [44.8%, 57.6%] | 51.1% [44.8%, 57.6%] | 50.0% [44.5%, 55.4%] | 1 | 237 / 181 | 9 | adequate descriptive support | 131 / 114 / 2 / 31 | 0 |
| 2.5 | 50 | 267 | 8.57 [7.06, 10.28] / 4.00 | 6.95 [5.79, 8.17] / 3.60 | 6.95 [5.79, 8.17] / 3.60 | 8.57 [7.06, 10.28] / 4.00 | -0.60 [-2.20, 0.82] | 0.60 [-0.82, 2.20] | 54.3% [48.4%, 60.5%] | 54.3% [48.4%, 60.5%] | 43.8% [38.3%, 49.4%] | 1 | 229 / 178 | 20 | adequate descriptive support | 127 / 108 / 1 / 31 | 0 |
| 3.0 | 5 | 64 | 2.83 [1.87, 3.94] / 1.35 | 3.42 [2.46, 4.46] / 1.80 | 3.42 [2.46, 4.46] / 1.80 | 2.83 [1.87, 3.94] / 1.35 | 0.65 [-0.43, 1.73] | -0.65 [-1.73, 0.43] | 56.2% [43.5%, 68.5%] | 56.2% [43.5%, 68.5%] | 46.9% [34.5%, 59.6%] | 2 | 61 / 60 | 1 | events_below_100 | 29 / 16 / 7 / 12 | 0 |
| 3.0 | 10 | 64 | 4.85 [3.45, 6.40] / 2.45 | 4.17 [3.00, 5.40] / 2.30 | 4.17 [3.00, 5.40] / 2.30 | 4.85 [3.45, 6.40] / 2.45 | -1.02 [-2.78, 0.69] | 1.02 [-0.69, 2.78] | 42.2% [29.3%, 54.8%] | 42.2% [29.3%, 54.8%] | 50.0% [38.6%, 62.3%] | 0 | 61 / 60 | 1 | events_below_100 | 32 / 18 / 2 / 12 | 0 |
| 3.0 | 15 | 64 | 6.53 [4.56, 8.79] / 3.05 | 4.77 [3.37, 6.27] / 2.50 | 4.77 [3.37, 6.27] / 2.50 | 6.53 [4.56, 8.79] / 3.05 | -2.12 [-4.61, 0.08] | 2.12 [-0.08, 4.61] | 42.2% [30.4%, 54.0%] | 42.2% [30.4%, 54.0%] | 37.5% [26.0%, 50.0%] | 0 | 61 / 60 | 1 | events_below_100 | 32 / 19 / 1 / 12 | 0 |
| 3.0 | 20 | 63 | 7.54 [5.41, 10.01] / 3.20 | 5.40 [3.68, 7.35] / 2.50 | 5.40 [3.68, 7.35] / 2.50 | 7.54 [5.41, 10.01] / 3.20 | -1.73 [-4.50, 0.85] | 1.73 [-0.85, 4.50] | 39.7% [27.3%, 51.6%] | 39.7% [27.3%, 51.6%] | 54.0% [41.0%, 66.2%] | 0 | 61 / 60 | 2 | events_below_100 | 32 / 18 / 1 / 12 | 0 |
| 3.0 | 50 | 58 | 10.39 [7.16, 14.71] / 4.45 | 7.27 [5.08, 9.64] / 3.60 | 7.27 [5.08, 9.64] / 3.60 | 10.39 [7.16, 14.71] / 4.45 | -0.91 [-4.77, 2.29] | 0.91 [-2.29, 4.77] | 48.3% [34.5%, 61.5%] | 48.3% [34.5%, 61.5%] | 43.1% [29.9%, 56.4%] | 0 | 56 / 55 | 7 | events_below_100 | 30 / 16 / 0 / 12 | 0 |

### Lower departure / arrival: continuation and bounce short; fade and through long

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,016 | 3.04 [2.64, 3.53] / 1.60 | 3.97 [3.46, 4.52] / 2.10 | 3.97 [3.46, 4.52] / 2.10 | 3.04 [2.64, 3.53] / 1.60 | 0.41 [0.06, 0.79] | -0.41 [-0.79, -0.06] | 48.8% [46.0%, 51.6%] | 49.7% [46.8%, 52.6%] | 50.2% [47.1%, 53.3%] | 15 | 618 / 325 | 4 | adequate descriptive support |
| 2.0 | 10 | 1,004 | 4.14 [3.61, 4.74] / 2.30 | 5.32 [4.66, 6.08] / 2.70 | 5.32 [4.66, 6.08] / 2.70 | 4.14 [3.61, 4.74] / 2.30 | 0.40 [-0.03, 0.85] | -0.40 [-0.85, 0.03] | 49.2% [46.0%, 52.3%] | 49.2% [46.2%, 52.3%] | 47.5% [44.5%, 50.4%] | 16 | 614 / 325 | 16 | adequate descriptive support |
| 2.0 | 15 | 1,001 | 4.88 [4.26, 5.54] / 2.70 | 6.35 [5.52, 7.27] / 3.30 | 6.35 [5.52, 7.27] / 3.30 | 4.88 [4.26, 5.54] / 2.70 | 0.45 [-0.06, 0.99] | -0.45 [-0.99, 0.06] | 47.6% [44.5%, 50.6%] | 50.8% [47.8%, 53.9%] | 48.0% [45.0%, 50.9%] | 16 | 613 / 325 | 19 | adequate descriptive support |
| 2.0 | 20 | 999 | 5.45 [4.78, 6.17] / 3.00 | 7.13 [6.22, 8.17] / 3.60 | 7.13 [6.22, 8.17] / 3.60 | 5.45 [4.78, 6.17] / 3.00 | 0.36 [-0.22, 0.95] | -0.36 [-0.95, 0.22] | 47.7% [44.5%, 50.9%] | 51.5% [48.2%, 54.7%] | 47.0% [44.2%, 50.0%] | 8 | 613 / 325 | 21 | adequate descriptive support |
| 2.0 | 50 | 957 | 7.78 [6.84, 8.78] / 4.40 | 9.38 [8.22, 10.69] / 4.80 | 9.38 [8.22, 10.69] / 4.80 | 7.78 [6.84, 8.78] / 4.40 | 0.02 [-0.97, 1.01] | -0.02 [-1.01, 0.97] | 47.3% [44.0%, 50.8%] | 52.1% [48.7%, 55.6%] | 48.3% [45.0%, 51.5%] | 5 | 606 / 324 | 63 | adequate descriptive support |
| 2.5 | 5 | 439 | 3.70 [2.88, 4.71] / 1.80 | 4.06 [3.41, 4.80] / 2.20 | 4.06 [3.41, 4.80] / 2.20 | 3.70 [2.88, 4.71] / 1.80 | -0.19 [-1.08, 0.56] | 0.19 [-0.56, 1.08] | 46.7% [41.8%, 51.3%] | 50.8% [46.3%, 55.5%] | 50.3% [45.8%, 54.9%] | 11 | 340 / 235 | 4 | adequate descriptive support |
| 2.5 | 10 | 434 | 4.85 [3.84, 6.09] / 2.40 | 5.25 [4.40, 6.21] / 2.70 | 5.25 [4.40, 6.21] / 2.70 | 4.85 [3.84, 6.09] / 2.40 | -0.27 [-1.34, 0.64] | 0.27 [-0.64, 1.34] | 48.2% [43.1%, 53.2%] | 50.7% [45.7%, 55.7%] | 47.7% [42.6%, 53.0%] | 5 | 338 / 235 | 9 | adequate descriptive support |
| 2.5 | 15 | 432 | 5.64 [4.53, 6.93] / 2.70 | 6.37 [5.38, 7.46] / 3.20 | 6.37 [5.38, 7.46] / 3.20 | 5.64 [4.53, 6.93] / 2.70 | 0.06 [-0.76, 0.84] | -0.06 [-0.84, 0.76] | 46.8% [42.1%, 51.5%] | 52.5% [47.8%, 57.2%] | 50.7% [45.5%, 55.8%] | 3 | 337 / 234 | 11 | adequate descriptive support |
| 2.5 | 20 | 430 | 6.18 [5.02, 7.49] / 3.00 | 7.36 [6.19, 8.70] / 3.60 | 7.36 [6.19, 8.70] / 3.60 | 6.18 [5.02, 7.49] / 3.00 | -0.06 [-1.08, 0.95] | 0.06 [-0.95, 1.08] | 45.1% [40.5%, 49.6%] | 54.0% [49.4%, 58.8%] | 48.1% [43.6%, 53.0%] | 4 | 337 / 234 | 13 | adequate descriptive support |
| 2.5 | 50 | 395 | 8.86 [7.26, 10.56] / 4.20 | 9.56 [8.18, 11.20] / 4.80 | 9.56 [8.18, 11.20] / 4.80 | 8.86 [7.26, 10.56] / 4.20 | -1.02 [-2.45, 0.39] | 1.02 [-0.39, 2.45] | 46.1% [41.1%, 51.0%] | 53.4% [48.4%, 58.3%] | 48.4% [43.3%, 53.2%] | 2 | 319 / 228 | 48 | adequate descriptive support |
| 3.0 | 5 | 123 | 3.63 [2.59, 4.91] / 1.90 | 4.47 [3.30, 5.81] / 2.20 | 4.47 [3.30, 5.81] / 2.20 | 3.63 [2.59, 4.91] / 1.90 | -0.05 [-1.04, 0.91] | 0.05 [-0.91, 1.04] | 43.9% [35.4%, 52.0%] | 55.3% [47.0%, 64.1%] | 51.2% [42.7%, 59.4%] | 1 | 113 / 98 | 1 | adequate descriptive support |
| 3.0 | 10 | 122 | 5.13 [3.80, 6.61] / 2.45 | 5.68 [4.33, 7.22] / 2.65 | 5.68 [4.33, 7.22] / 2.65 | 5.13 [3.80, 6.61] / 2.45 | -0.06 [-1.29, 1.21] | 0.06 [-1.21, 1.29] | 46.7% [38.0%, 55.6%] | 50.8% [41.7%, 59.7%] | 52.5% [43.6%, 60.5%] | 3 | 112 / 97 | 2 | adequate descriptive support |
| 3.0 | 15 | 116 | 6.33 [4.76, 8.03] / 2.80 | 6.72 [5.15, 8.50] / 3.05 | 6.72 [5.15, 8.50] / 3.05 | 6.33 [4.76, 8.03] / 2.80 | -0.47 [-2.01, 1.24] | 0.47 [-1.24, 2.01] | 44.8% [35.0%, 54.4%] | 55.2% [45.6%, 65.0%] | 50.0% [41.5%, 59.0%] | 0 | 106 / 91 | 8 | adequate descriptive support |
| 3.0 | 20 | 114 | 6.91 [5.25, 8.68] / 3.15 | 7.80 [5.66, 10.39] / 3.30 | 7.80 [5.66, 10.39] / 3.30 | 6.91 [5.25, 8.68] / 3.15 | -0.40 [-2.30, 1.75] | 0.40 [-1.75, 2.30] | 44.7% [35.1%, 54.0%] | 55.3% [46.0%, 64.9%] | 50.0% [40.3%, 60.2%] | 0 | 104 / 91 | 10 | adequate descriptive support |
| 3.0 | 50 | 100 | 8.46 [6.28, 10.83] / 4.05 | 9.92 [7.40, 12.81] / 4.80 | 9.92 [7.40, 12.81] / 4.80 | 8.46 [6.28, 10.83] / 4.05 | -0.67 [-3.28, 1.96] | 0.67 [-1.96, 3.28] | 43.0% [33.0%, 53.1%] | 57.0% [46.9%, 67.0%] | 54.0% [44.0%, 64.2%] | 0 | 92 / 81 | 24 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,016 | 307 | 30.2% [27.4%, 32.9%] | 709 | 2.0 / 4.0 | 6 | 0 | 4 | 70 | 0 |
| 2.0 | 5 | frozen | 1,016 | 237 | 23.3% [20.8%, 26.0%] | 779 | 2.0 / 3.0 | 6 | 0 | 4 | 70 | 0 |
| 2.0 | 10 | evolving | 1,004 | 460 | 45.8% [42.6%, 48.7%] | 544 | 4.0 / 7.0 | 7 | 0 | 16 | 114 | 0 |
| 2.0 | 10 | frozen | 1,004 | 346 | 34.5% [31.6%, 37.3%] | 658 | 3.0 / 6.0 | 7 | 0 | 16 | 114 | 0 |
| 2.0 | 15 | evolving | 1,001 | 549 | 54.8% [51.7%, 57.6%] | 452 | 5.0 / 9.0 | 11 | 0 | 19 | 138 | 0 |
| 2.0 | 15 | frozen | 1,001 | 411 | 41.1% [37.9%, 44.0%] | 590 | 4.0 / 8.0 | 11 | 0 | 19 | 138 | 0 |
| 2.0 | 20 | evolving | 999 | 595 | 59.6% [56.6%, 62.3%] | 404 | 5.0 / 10.0 | 13 | 0 | 21 | 143 | 0 |
| 2.0 | 20 | frozen | 999 | 452 | 45.2% [42.0%, 48.3%] | 547 | 5.0 / 10.0 | 13 | 0 | 21 | 143 | 0 |
| 2.0 | 50 | evolving | 957 | 722 | 75.4% [73.1%, 77.7%] | 235 | 7.0 / 15.0 | 17 | 0 | 63 | 157 | 0 |
| 2.0 | 50 | frozen | 957 | 565 | 59.0% [55.9%, 61.9%] | 392 | 7.0 / 17.0 | 17 | 0 | 63 | 157 | 0 |
| 2.5 | 5 | evolving | 439 | 107 | 24.4% [20.4%, 27.9%] | 332 | 2.0 / 3.0 | 1 | 0 | 4 | 15 | 0 |
| 2.5 | 5 | frozen | 439 | 92 | 21.0% [17.1%, 24.5%] | 347 | 2.0 / 3.0 | 1 | 0 | 4 | 15 | 0 |
| 2.5 | 10 | evolving | 434 | 163 | 37.6% [33.4%, 41.5%] | 271 | 4.0 / 7.0 | 1 | 0 | 9 | 37 | 0 |
| 2.5 | 10 | frozen | 434 | 126 | 29.0% [25.1%, 32.8%] | 308 | 3.0 / 6.0 | 1 | 0 | 9 | 37 | 0 |
| 2.5 | 15 | evolving | 432 | 191 | 44.2% [39.9%, 48.4%] | 241 | 5.0 / 8.0 | 3 | 0 | 11 | 46 | 0 |
| 2.5 | 15 | frozen | 432 | 145 | 33.6% [29.4%, 37.5%] | 287 | 3.0 / 7.0 | 3 | 0 | 11 | 46 | 0 |
| 2.5 | 20 | evolving | 430 | 219 | 50.9% [46.4%, 55.3%] | 211 | 6.0 / 11.0 | 5 | 0 | 13 | 63 | 0 |
| 2.5 | 20 | frozen | 430 | 156 | 36.3% [32.1%, 40.2%] | 274 | 4.0 / 9.0 | 5 | 0 | 13 | 63 | 0 |
| 2.5 | 50 | evolving | 395 | 280 | 70.9% [66.6%, 75.1%] | 115 | 8.0 / 19.0 | 7 | 0 | 48 | 61 | 0 |
| 2.5 | 50 | frozen | 395 | 219 | 55.4% [51.0%, 59.9%] | 176 | 8.0 / 22.0 | 7 | 0 | 48 | 61 | 0 |
| 3.0 | 5 | evolving | 123 | 31 | 25.2% [17.9%, 33.6%] | 92 | 2.0 / 3.0 | 0 | 0 | 1 | 3 | 0 |
| 3.0 | 5 | frozen | 123 | 28 | 22.8% [15.4%, 30.6%] | 95 | 2.0 / 3.0 | 0 | 0 | 1 | 3 | 0 |
| 3.0 | 10 | evolving | 122 | 43 | 35.2% [27.3%, 44.3%] | 79 | 3.0 / 6.0 | 0 | 0 | 2 | 9 | 0 |
| 3.0 | 10 | frozen | 122 | 34 | 27.9% [20.0%, 36.3%] | 88 | 2.0 / 4.0 | 0 | 0 | 2 | 9 | 0 |
| 3.0 | 15 | evolving | 116 | 46 | 39.7% [31.1%, 48.3%] | 70 | 3.0 / 7.0 | 1 | 0 | 8 | 9 | 0 |
| 3.0 | 15 | frozen | 116 | 37 | 31.9% [23.6%, 40.2%] | 79 | 2.0 / 5.0 | 1 | 0 | 8 | 9 | 0 |
| 3.0 | 20 | evolving | 114 | 49 | 43.0% [33.9%, 52.0%] | 65 | 3.0 / 7.0 | 1 | 0 | 10 | 11 | 0 |
| 3.0 | 20 | frozen | 114 | 38 | 33.3% [25.0%, 41.9%] | 76 | 2.5 / 5.8 | 1 | 0 | 10 | 11 | 0 |
| 3.0 | 50 | evolving | 100 | 68 | 68.0% [58.2%, 77.2%] | 32 | 7.0 / 23.2 | 2 | 0 | 24 | 12 | 0 |
| 3.0 | 50 | frozen | 100 | 56 | 56.0% [45.3%, 66.7%] | 44 | 5.5 / 23.5 | 2 | 0 | 24 | 12 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 816 | 2.53 [2.19, 2.93] / 1.45 | 2.77 [2.43, 3.16] / 1.40 | 2.77 [2.43, 3.16] / 1.40 | 2.53 [2.19, 2.93] / 1.45 | 0.20 [-0.13, 0.53] | -0.20 [-0.53, 0.13] | 49.3% [45.9%, 52.5%] | 47.7% [44.3%, 51.1%] | 47.8% [44.2%, 51.4%] | 25 | 552 / 306 | 4 | adequate descriptive support | 315 / 319 / 143 / 39 | 0 |
| 2.0 | 10 | 809 | 3.58 [3.15, 4.10] / 2.10 | 3.97 [3.44, 4.55] / 2.00 | 3.97 [3.44, 4.55] / 2.00 | 3.58 [3.15, 4.10] / 2.10 | 0.07 [-0.37, 0.51] | -0.07 [-0.51, 0.37] | 49.4% [45.9%, 52.9%] | 49.2% [45.8%, 52.9%] | 48.6% [45.3%, 51.8%] | 11 | 551 / 306 | 11 | adequate descriptive support | 341 / 359 / 70 / 39 | 0 |
| 2.0 | 15 | 805 | 4.31 [3.78, 4.94] / 2.60 | 4.72 [4.10, 5.39] / 2.30 | 4.72 [4.10, 5.39] / 2.30 | 4.31 [3.78, 4.94] / 2.60 | -0.03 [-0.55, 0.50] | 0.03 [-0.50, 0.55] | 48.3% [44.8%, 52.0%] | 50.6% [47.1%, 54.0%] | 48.4% [45.0%, 52.0%] | 9 | 549 / 305 | 15 | adequate descriptive support | 350 / 370 / 46 / 39 | 0 |
| 2.0 | 20 | 804 | 4.88 [4.27, 5.58] / 2.90 | 5.44 [4.73, 6.22] / 2.85 | 5.44 [4.73, 6.22] / 2.85 | 4.88 [4.27, 5.58] / 2.90 | -0.01 [-0.61, 0.58] | 0.01 [-0.58, 0.61] | 47.1% [43.6%, 50.7%] | 51.5% [48.1%, 55.1%] | 47.6% [44.0%, 51.3%] | 11 | 549 / 305 | 16 | adequate descriptive support | 357 / 371 / 37 / 39 | 0 |
| 2.0 | 50 | 775 | 7.28 [6.35, 8.30] / 4.00 | 8.11 [7.10, 9.25] / 4.40 | 8.11 [7.10, 9.25] / 4.40 | 7.28 [6.35, 8.30] / 4.00 | 0.15 [-0.74, 1.06] | -0.15 [-1.06, 0.74] | 46.3% [42.7%, 49.9%] | 53.4% [49.8%, 57.1%] | 48.1% [44.5%, 51.5%] | 2 | 537 / 305 | 45 | adequate descriptive support | 363 / 364 / 9 / 39 | 0 |
| 2.5 | 5 | 318 | 2.93 [2.29, 3.74] / 1.50 | 3.02 [2.48, 3.69] / 1.40 | 3.02 [2.48, 3.69] / 1.40 | 2.93 [2.29, 3.74] / 1.50 | 0.24 [-0.48, 0.88] | -0.24 [-0.88, 0.48] | 52.8% [47.2%, 58.6%] | 44.7% [38.9%, 50.3%] | 43.7% [37.8%, 49.2%] | 8 | 266 / 195 | 3 | adequate descriptive support | 115 / 120 / 62 / 21 | 0 |
| 2.5 | 10 | 315 | 3.93 [3.17, 4.84] / 1.90 | 4.28 [3.44, 5.30] / 2.10 | 4.28 [3.44, 5.30] / 2.10 | 3.93 [3.17, 4.84] / 1.90 | -0.03 [-0.84, 0.71] | 0.03 [-0.71, 0.84] | 50.8% [45.0%, 56.3%] | 47.3% [41.7%, 53.0%] | 51.7% [46.6%, 56.9%] | 6 | 266 / 195 | 6 | adequate descriptive support | 126 / 136 / 32 / 21 | 0 |
| 2.5 | 15 | 314 | 4.72 [3.85, 5.72] / 2.55 | 5.10 [4.08, 6.28] / 2.40 | 5.10 [4.08, 6.28] / 2.40 | 4.72 [3.85, 5.72] / 2.55 | -0.10 [-1.01, 0.79] | 0.10 [-0.79, 1.01] | 45.9% [39.8%, 51.4%] | 53.2% [47.7%, 59.1%] | 49.0% [43.1%, 54.4%] | 3 | 265 / 194 | 7 | adequate descriptive support | 131 / 141 / 21 / 21 | 0 |
| 2.5 | 20 | 314 | 5.33 [4.40, 6.38] / 2.90 | 5.92 [4.79, 7.19] / 2.95 | 5.92 [4.79, 7.19] / 2.95 | 5.33 [4.40, 6.38] / 2.90 | 0.12 [-0.79, 1.03] | -0.12 [-1.03, 0.79] | 47.5% [41.8%, 52.9%] | 50.0% [44.6%, 55.7%] | 47.5% [41.9%, 53.3%] | 8 | 265 / 194 | 7 | adequate descriptive support | 133 / 142 / 18 / 21 | 0 |
| 2.5 | 50 | 299 | 8.17 [6.60, 9.80] / 4.40 | 8.47 [6.94, 10.08] / 4.40 | 8.47 [6.94, 10.08] / 4.40 | 8.17 [6.60, 9.80] / 4.40 | -0.38 [-1.93, 1.20] | 0.38 [-1.20, 1.93] | 42.5% [36.9%, 48.2%] | 57.5% [51.8%, 63.1%] | 51.2% [45.4%, 57.0%] | 0 | 255 / 190 | 22 | adequate descriptive support | 137 / 137 / 4 / 21 | 0 |
| 3.0 | 5 | 77 | 2.74 [2.03, 3.56] / 1.60 | 3.41 [2.03, 5.01] / 1.20 | 3.41 [2.03, 5.01] / 1.20 | 2.74 [2.03, 3.56] / 1.60 | 0.40 [-0.88, 1.70] | -0.40 [-1.70, 0.88] | 55.8% [44.4%, 67.1%] | 42.9% [31.9%, 53.9%] | 42.9% [31.4%, 53.8%] | 1 | 72 / 63 | 1 | events_below_100 | 25 / 28 / 14 / 10 | 0 |
| 3.0 | 10 | 76 | 4.09 [2.99, 5.41] / 2.10 | 4.24 [2.68, 6.01] / 1.90 | 4.24 [2.68, 6.01] / 1.90 | 4.09 [2.99, 5.41] / 2.10 | -0.39 [-2.06, 1.27] | 0.39 [-1.27, 2.06] | 48.7% [36.7%, 60.5%] | 51.3% [39.5%, 63.3%] | 57.9% [46.4%, 68.9%] | 0 | 71 / 62 | 2 | events_below_100 | 27 / 31 / 8 / 10 | 0 |
| 3.0 | 15 | 76 | 4.99 [3.71, 6.45] / 3.00 | 5.57 [3.19, 8.55] / 2.10 | 5.57 [3.19, 8.55] / 2.10 | 4.99 [3.71, 6.45] / 3.00 | -0.18 [-2.29, 2.17] | 0.18 [-2.17, 2.29] | 38.2% [26.6%, 49.5%] | 61.8% [50.5%, 73.4%] | 52.6% [40.4%, 64.3%] | 0 | 71 / 62 | 2 | events_below_100 | 30 / 32 / 4 / 10 | 0 |
| 3.0 | 20 | 76 | 5.54 [4.19, 7.11] / 3.40 | 6.47 [3.70, 9.91] / 2.35 | 6.47 [3.70, 9.91] / 2.35 | 5.54 [4.19, 7.11] / 3.40 | 0.43 [-2.03, 2.97] | -0.43 [-2.97, 2.03] | 38.2% [26.6%, 49.3%] | 59.2% [47.9%, 70.9%] | 40.8% [29.7%, 51.3%] | 2 | 71 / 62 | 2 | events_below_100 | 30 / 32 / 4 / 10 | 0 |
| 3.0 | 50 | 71 | 7.90 [5.62, 10.50] / 5.10 | 9.37 [5.45, 13.92] / 3.50 | 9.37 [5.45, 13.92] / 3.50 | 7.90 [5.62, 10.50] / 5.10 | 0.24 [-3.56, 4.31] | -0.24 [-4.31, 3.56] | 32.4% [22.9%, 43.0%] | 67.6% [57.0%, 77.1%] | 50.7% [38.4%, 62.6%] | 0 | 66 / 58 | 7 | events_below_100 | 31 / 29 / 1 / 10 | 0 |

### Common cohort, distribution and year diagnostics

The horizon curves use the identical complete-50 cohort. Distribution quantiles and year diagnostics use each horizon’s eligible cohort. Year 2026 is partial. These diagnostics are descriptive on previously inspected history.

![GC New York return](figures/ny-GC-return.svg)

![GC New York excursion](figures/ny-GC-excursion.svg)

![GC New York endpoint](figures/ny-GC-endpoint.svg)

![GC New York mae-mfe-distribution](figures/ny-GC-mae-mfe-distribution.svg)

![GC New York terminal-distribution](figures/ny-GC-terminal-distribution.svg)

![GC New York year-stability](figures/ny-GC-year-stability.svg)

### Sensitivity and chronological periods at 10 candles

| Module | Scope | n | Days / weeks | Directional Δ [CI] | Return or bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- |
| departure | all | 2,023 | 808 / 355 | 0.25 [0.03, 0.51] | 45.6% [43.5%, 47.6%] |
| departure | common_50 | 1,927 | 806 / 355 | 0.14 [-0.12, 0.41] | 47.7% [45.6%, 49.8%] |
| departure | age_ge30 | 1,225 | 722 / 337 | 0.41 [0.07, 0.76] | 22.7% [20.3%, 25.1%] |
| departure | through_2023 | 1,261 | 496 / 240 | 0.14 [-0.04, 0.34] | 45.9% [43.3%, 48.5%] |
| departure | year_2024_period | 167 | 62 / 32 | 0.04 [-0.61, 0.74] | 49.1% [42.6%, 55.3%] |
| departure | years_2025_2026 | 595 | 250 / 83 | 0.55 [-0.10, 1.24] | 44.0% [40.2%, 47.6%] |
| touch | all | 1,623 | 755 / 345 | -0.08 [-0.39, 0.21] | 49.6% [46.9%, 52.2%] |
| touch | common_50 | 1,558 | 746 / 345 | -0.05 [-0.36, 0.24] | 49.6% [46.9%, 52.3%] |
| touch | age_ge30 | 836 | 571 / 303 | -0.06 [-0.40, 0.29] | 50.0% [46.7%, 53.4%] |
| touch | through_2023 | 1,011 | 467 / 232 | 0.08 [-0.12, 0.28] | 50.1% [46.8%, 53.4%] |
| touch | year_2024_period | 128 | 60 / 31 | -0.62 [-1.73, 0.49] | 41.4% [30.8%, 52.2%] |
| touch | years_2025_2026 | 484 | 228 / 82 | -0.28 [-1.20, 0.60] | 50.6% [46.7%, 54.4%] |

### Deterministic source-path examples

Examples are the earliest stable ID in each prespecified class. They illustrate mechanisms and exclusions, not representative trade quality. The source table includes reference available_at and known sigma for every minute; charts plot raw one-minute high/low and references. Source minute open time relative to entry is shown; contacts have interval resolution. Lines join minute OHLC observations for display and do not imply intraminute order or trades through gaps. The 2-sigma envelope is plotted; 2.5/3-sigma references are retained in the example-path table.

return: GC-ny-2016-05-09-P0005-K2-H10; lower side. Signal/confirmation 2016-05-09 09:42:00-04:00; entry 2016-05-09 09:42:00-04:00; deadline 2016-05-09 10:02:00-04:00 (New York time). Frozen sigma 0.35 points; signal VWAP 1,270.11. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-ny-2016-05-09-P0005-K2-H10](figures/example-ny-GC-return.svg)

non_return: GC-ny-2016-02-11-P0032-K2-H10; upper side. Signal/confirmation 2016-02-11 10:36:00-05:00; entry 2016-02-11 10:36:00-05:00; deadline 2016-02-11 10:56:00-05:00 (New York time). Frozen sigma 2.90 points; signal VWAP 1,238.15. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-ny-2016-02-11-P0032-K2-H10](figures/example-ny-GC-non_return.svg)

bounce: GC-ny-2016-05-09-P0005-T-H10; lower side. Signal/confirmation 2016-05-09 09:54:00-04:00; entry 2016-05-09 09:54:00-04:00; deadline 2016-05-09 10:14:00-04:00 (New York time). Frozen sigma 1.82 points; signal VWAP 1,267.19. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-ny-2016-05-09-P0005-T-H10](figures/example-ny-GC-bounce.svg)

through: GC-ny-2016-02-11-P0032-T-H10; upper side. Signal/confirmation 2016-02-11 13:02:00-05:00; entry 2016-02-11 13:02:00-05:00; deadline 2016-02-11 13:22:00-05:00 (New York time). Frozen sigma 7.63 points; signal VWAP 1,247.06. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-ny-2016-02-11-P0032-T-H10](figures/example-ny-GC-through.svg)

ambiguity: GC-ny-2016-11-17-P0009-T-H10; lower side. Signal/confirmation 2016-11-17 09:54:00-05:00; entry 2016-11-17 09:54:00-05:00; deadline 2016-11-17 10:14:00-05:00 (New York time). Frozen sigma 0.35 points; signal VWAP 1,225.27. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-ny-2016-11-17-P0009-T-H10](figures/example-ny-GC-ambiguity.svg)

exclusion: GC-ny-2016-05-09-P0190-K2-H05; lower side. Signal/confirmation 2016-05-09 15:52:00-04:00; entry 2016-05-09 15:52:00-04:00; deadline 2016-05-09 16:02:00-04:00 (New York time). Frozen sigma 1.31 points; signal VWAP 1,266.86. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: session_boundary.

![GC-ny-2016-05-09-P0190-K2-H05](figures/example-ny-GC-exclusion.svg)

## Interpretation and verification

Return rates, first-move rates and terminal directional frequencies answer different questions. MAE/MFE maxima are favorable/adverse opportunities on an observed path, not obtainable trading profits. Threshold comparisons are descriptive because signal times and eligible populations differ. Treat sparse cells and boundary uncertainty as unresolved. Shared week intervals do not remove retrospective selection or establish a causal predictor.

[Numerical verification record](verification.json)

[Dated findings and advice](advice.md)

[Example selection ledger](tables/example-selection.csv)

[Independent source recounts](tables/independent-recounts.csv)

[Retained event evidence and checksums](events.manifest.json)
