# Globex — anchored VWAP excursion and return

Fresh historical execution · Protocol 1.0.0 · Frozen before new outcomes · 2026 YTD through September 18

Globex uses its own 18:00 New York-clock anchor and [18:00, 17:00) observation window. Both entry and complete horizons stay inside this window; a final candle closing exactly at the end is eligible. DST uses America/New_York. Globex is a separate overlapping population, not a sum of local sessions.

The pinned VWAP uses completed two-minute HLC3 weighted by bar volume and a volume-weighted population sigma; it is not trade-by-trade VWAP. Signals are first fresh strict closes beyond 2, 2.5 or 3 sigma within a causal parent excursion. Entry is the next two-minute open. Horizons 5/10/15/20/50 candles are 10/20/30/40/100 minutes; 15 is supplementary. Touch is source one-minute range overlap with the tick-rounded ±1-tick VWAP zone available at that minute open. Evolving VWAP is primary; signal-frozen VWAP is secondary. A gap or reference overtake alone is not a touch. Touch response begins after the containing two-minute candle closes. All MAE/MFE excludes the signal/touch candle and follows the full horizon. Upper departures: continuation is long and fade is short; upper-arrival bounce is long and through is short. Lower departures: continuation is short and fade is long; lower-arrival bounce is short and through is long.

The release contains 1,037 ES days, 1,177 NQ days and 825 GC days, selected retrospectively for whole-day completeness. ES/NQ feature history begins in 2021; GC eligible history begins in 2016; all end September 18, 2026. Absent minutes can be no-trade intervals; absence is not asserted to be corruption. This is previously inspected exploratory history, with overlapping sessions and nested thresholds. No threshold or horizon was optimized. Tick-rounded OHLC contact does not establish an executable fill, and OHLC cannot order two barriers reached in the same minute. No fees, slippage, position sizing, stops or profitability were tested. Delta means price change; true aggressor volume delta is unavailable.

Intervals are marginal 95% percentile intervals from 2,000 shared ISO-week cluster draws (seed 1501), preserving cross-product/session dependence. Brackets contain intervals. † marks zero/all-success boundary uncertainty unresolved by a degenerate bootstrap. Sparse flags: fewer than 100 events, 30 product-session dates or 20 weeks. Latency summaries condition on actual touching. Unavailable horizons never enter success/failure denominators.

[Full numerical tables: points, ticks, sigma units, tails, contexts, uncertainty and counts](tables/summary.csv)

[Per-horizon eligibility, exclusion reasons, parent/date/week support](tables/coverage.csv)

## Primary 2-sigma overview

Mirrored upper/lower sides are combined only within each product and session in this overview. The side-specific tables below retain every threshold and horizon. Endpoint bounce frequency describes the closing direction; it differs from the 0.5-sigma first-move race.

| Session | Product | h | Departure n | Evolving return % [CI] | Continuation Δ points [CI] | Touch n | Bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Globex | ES | 10 | 5,645 | 29.6% [28.4%, 30.9%] | -0.00 [-0.20, 0.20] | 5,108 | 47.9% [46.5%, 49.2%] |
| Globex | ES | 50 | 5,546 | 63.1% [61.8%, 64.4%] | -0.04 [-0.39, 0.31] | 5,000 | 48.9% [47.5%, 50.3%] |
| Globex | GC | 10 | 3,793 | 31.0% [29.3%, 32.6%] | 0.18 [0.04, 0.33] | 3,314 | 50.0% [48.2%, 51.7%] |
| Globex | GC | 50 | 3,763 | 62.1% [60.7%, 63.5%] | 0.41 [0.11, 0.76] | 3,285 | 51.7% [50.0%, 53.4%] |
| Globex | NQ | 10 | 6,060 | 24.2% [23.0%, 25.4%] | 0.69 [-0.13, 1.53] | 5,426 | 49.3% [48.0%, 50.6%] |
| Globex | NQ | 50 | 5,945 | 59.8% [58.6%, 61.0%] | 0.34 [-1.18, 1.87] | 5,333 | 49.4% [48.0%, 50.8%] |

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
| 2.0 | 5 | 2,814 | 2.86 [2.65, 3.11] / 1.50 | 2.93 [2.68, 3.21] / 1.50 | 2.93 [2.68, 3.21] / 1.50 | 2.86 [2.65, 3.11] / 1.50 | -0.07 [-0.24, 0.11] | 0.07 [-0.11, 0.24] | 45.5% [43.5%, 47.5%] | 45.5% [43.5%, 47.5%] | 43.2% [41.3%, 45.1%] | 141 | 973 / 266 | 0 | adequate descriptive support |
| 2.0 | 10 | 2,814 | 3.96 [3.67, 4.33] / 2.25 | 4.09 [3.67, 4.62] / 2.25 | 4.09 [3.67, 4.62] / 2.25 | 3.96 [3.67, 4.33] / 2.25 | 0.06 [-0.24, 0.35] | -0.06 [-0.35, 0.24] | 48.3% [46.3%, 50.3%] | 48.3% [46.3%, 50.3%] | 45.7% [43.7%, 47.8%] | 105 | 973 / 266 | 0 | adequate descriptive support |
| 2.0 | 15 | 2,808 | 4.84 [4.48, 5.28] / 2.75 | 4.86 [4.39, 5.48] / 2.75 | 4.86 [4.39, 5.48] / 2.75 | 4.84 [4.48, 5.28] / 2.75 | 0.09 [-0.26, 0.43] | -0.09 [-0.43, 0.26] | 49.1% [47.3%, 51.0%] | 49.1% [47.3%, 51.0%] | 44.4% [42.6%, 46.2%] | 87 | 973 / 266 | 6 | adequate descriptive support |
| 2.0 | 20 | 2,803 | 5.53 [5.14, 6.00] / 3.00 | 5.43 [4.92, 6.07] / 3.00 | 5.43 [4.92, 6.07] / 3.00 | 5.53 [5.14, 6.00] / 3.00 | 0.03 [-0.37, 0.40] | -0.03 [-0.40, 0.37] | 49.0% [47.0%, 51.0%] | 49.0% [47.0%, 51.0%] | 44.1% [42.3%, 45.8%] | 71 | 972 / 266 | 11 | adequate descriptive support |
| 2.0 | 50 | 2,763 | 9.00 [8.38, 9.73] / 5.25 | 8.12 [7.46, 8.94] / 4.75 | 8.12 [7.46, 8.94] / 4.75 | 9.00 [8.38, 9.73] / 5.25 | -0.24 [-0.82, 0.29] | 0.24 [-0.29, 0.82] | 49.2% [47.2%, 51.3%] | 49.2% [47.2%, 51.3%] | 45.1% [43.2%, 47.2%] | 44 | 971 / 266 | 51 | adequate descriptive support |
| 2.5 | 5 | 1,274 | 3.09 [2.77, 3.48] / 1.75 | 3.28 [2.79, 4.04] / 1.75 | 3.28 [2.79, 4.04] / 1.75 | 3.09 [2.77, 3.48] / 1.75 | 0.07 [-0.21, 0.37] | -0.07 [-0.37, 0.21] | 45.9% [42.9%, 49.1%] | 45.9% [42.9%, 49.1%] | 44.7% [42.4%, 47.2%] | 58 | 749 / 261 | 0 | adequate descriptive support |
| 2.5 | 10 | 1,273 | 4.20 [3.73, 4.82] / 2.25 | 4.31 [3.73, 5.15] / 2.25 | 4.31 [3.73, 5.15] / 2.25 | 4.20 [3.73, 4.82] / 2.25 | 0.05 [-0.30, 0.45] | -0.05 [-0.45, 0.30] | 46.2% [43.4%, 49.3%] | 46.2% [43.4%, 49.3%] | 46.5% [43.9%, 49.4%] | 50 | 749 / 261 | 1 | adequate descriptive support |
| 2.5 | 15 | 1,272 | 4.98 [4.43, 5.70] / 2.75 | 5.15 [4.52, 6.04] / 2.75 | 5.15 [4.52, 6.04] / 2.75 | 4.98 [4.43, 5.70] / 2.75 | 0.22 [-0.20, 0.64] | -0.22 [-0.64, 0.20] | 48.3% [45.7%, 51.1%] | 48.3% [45.7%, 51.1%] | 42.2% [39.5%, 45.1%] | 36 | 748 / 261 | 2 | adequate descriptive support |
| 2.5 | 20 | 1,269 | 5.65 [5.04, 6.41] / 3.00 | 5.69 [5.03, 6.63] / 3.25 | 5.69 [5.03, 6.63] / 3.25 | 5.65 [5.04, 6.41] / 3.00 | 0.24 [-0.25, 0.78] | -0.24 [-0.78, 0.25] | 49.9% [47.2%, 52.7%] | 49.9% [47.2%, 52.7%] | 43.3% [40.6%, 45.9%] | 24 | 747 / 261 | 5 | adequate descriptive support |
| 2.5 | 50 | 1,250 | 9.19 [8.29, 10.20] / 5.25 | 8.37 [7.48, 9.50] / 5.00 | 8.37 [7.48, 9.50] / 5.00 | 9.19 [8.29, 10.20] / 5.25 | -0.39 [-1.22, 0.40] | 0.39 [-0.40, 1.22] | 49.2% [46.3%, 52.1%] | 49.2% [46.3%, 52.1%] | 43.9% [41.4%, 46.3%] | 21 | 741 / 260 | 24 | adequate descriptive support |
| 3.0 | 5 | 354 | 4.54 [3.56, 5.73] / 2.00 | 4.04 [2.65, 6.37] / 1.75 | 4.04 [2.65, 6.37] / 1.75 | 4.54 [3.56, 5.73] / 2.00 | -0.62 [-1.65, 0.32] | 0.62 [-0.32, 1.65] | 44.9% [40.0%, 50.3%] | 44.9% [40.0%, 50.3%] | 44.9% [40.4%, 49.7%] | 19 | 293 / 186 | 0 | adequate descriptive support |
| 3.0 | 10 | 352 | 6.00 [4.65, 7.72] / 2.75 | 5.24 [3.59, 7.91] / 2.25 | 5.24 [3.59, 7.91] / 2.25 | 6.00 [4.65, 7.72] / 2.75 | -0.72 [-1.96, 0.43] | 0.72 [-0.43, 1.96] | 45.7% [40.1%, 51.4%] | 45.7% [40.1%, 51.4%] | 46.0% [40.9%, 51.0%] | 12 | 292 / 186 | 2 | adequate descriptive support |
| 3.0 | 15 | 351 | 6.81 [5.30, 8.69] / 3.00 | 6.29 [4.42, 9.15] / 2.50 | 6.29 [4.42, 9.15] / 2.50 | 6.81 [5.30, 8.69] / 3.00 | -0.10 [-1.43, 1.16] | 0.10 [-1.16, 1.43] | 47.6% [42.4%, 52.7%] | 47.6% [42.4%, 52.7%] | 48.4% [42.7%, 53.9%] | 7 | 291 / 186 | 3 | adequate descriptive support |
| 3.0 | 20 | 350 | 7.53 [6.00, 9.42] / 3.50 | 6.88 [4.93, 9.84] / 3.00 | 6.88 [4.93, 9.84] / 3.00 | 7.53 [6.00, 9.42] / 3.50 | 0.50 [-1.13, 2.23] | -0.50 [-2.23, 1.13] | 49.4% [44.1%, 54.9%] | 49.4% [44.1%, 54.9%] | 48.3% [43.6%, 53.3%] | 8 | 290 / 185 | 4 | adequate descriptive support |
| 3.0 | 50 | 347 | 11.31 [9.37, 13.63] / 5.25 | 9.53 [7.24, 12.87] / 4.75 | 9.53 [7.24, 12.87] / 4.75 | 11.31 [9.37, 13.63] / 5.25 | -1.37 [-3.45, 0.68] | 1.37 [-0.68, 3.45] | 46.7% [41.6%, 52.2%] | 46.7% [41.6%, 52.2%] | 48.7% [43.9%, 53.7%] | 4 | 288 / 185 | 7 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 2,814 | 530 | 18.8% [17.3%, 20.4%] | 2,284 | 2.0 / 4.0 | 0 | 0 | 0 | 77 | 0 |
| 2.0 | 5 | frozen | 2,814 | 453 | 16.1% [14.6%, 17.6%] | 2,361 | 2.0 / 4.0 | 0 | 0 | 0 | 77 | 0 |
| 2.0 | 10 | evolving | 2,814 | 794 | 28.2% [26.5%, 30.0%] | 2,020 | 4.0 / 6.0 | 0 | 0 | 0 | 137 | 0 |
| 2.0 | 10 | frozen | 2,814 | 657 | 23.3% [21.7%, 25.0%] | 2,157 | 4.0 / 6.0 | 0 | 0 | 0 | 137 | 0 |
| 2.0 | 15 | evolving | 2,808 | 978 | 34.8% [33.0%, 36.7%] | 1,830 | 5.0 / 9.0 | 0 | 0 | 6 | 165 | 0 |
| 2.0 | 15 | frozen | 2,808 | 813 | 29.0% [27.2%, 30.8%] | 1,995 | 5.0 / 9.0 | 0 | 0 | 6 | 165 | 0 |
| 2.0 | 20 | evolving | 2,803 | 1,136 | 40.5% [38.6%, 42.4%] | 1,667 | 6.0 / 12.0 | 0 | 0 | 11 | 193 | 0 |
| 2.0 | 20 | frozen | 2,803 | 943 | 33.6% [31.7%, 35.5%] | 1,860 | 6.0 / 12.0 | 0 | 0 | 11 | 193 | 0 |
| 2.0 | 50 | evolving | 2,763 | 1,671 | 60.5% [58.8%, 62.2%] | 1,092 | 11.0 / 26.0 | 0 | 1 | 51 | 270 | 0 |
| 2.0 | 50 | frozen | 2,763 | 1,401 | 50.7% [48.8%, 52.7%] | 1,362 | 11.0 / 26.0 | 0 | 1 | 51 | 270 | 0 |
| 2.5 | 5 | evolving | 1,274 | 213 | 16.7% [14.6%, 18.8%] | 1,061 | 2.0 / 3.0 | 0 | 0 | 0 | 31 | 0 |
| 2.5 | 5 | frozen | 1,274 | 182 | 14.3% [12.3%, 16.3%] | 1,092 | 2.0 / 3.0 | 0 | 0 | 0 | 31 | 0 |
| 2.5 | 10 | evolving | 1,273 | 304 | 23.9% [21.7%, 26.3%] | 969 | 3.0 / 6.0 | 0 | 0 | 1 | 59 | 0 |
| 2.5 | 10 | frozen | 1,273 | 245 | 19.2% [17.1%, 21.5%] | 1,028 | 3.0 / 6.0 | 0 | 0 | 1 | 59 | 0 |
| 2.5 | 15 | evolving | 1,272 | 381 | 30.0% [27.4%, 32.5%] | 891 | 5.0 / 9.0 | 0 | 0 | 2 | 80 | 0 |
| 2.5 | 15 | frozen | 1,272 | 301 | 23.7% [21.4%, 26.1%] | 971 | 4.0 / 9.0 | 0 | 0 | 2 | 80 | 0 |
| 2.5 | 20 | evolving | 1,269 | 449 | 35.4% [32.9%, 38.0%] | 820 | 6.0 / 12.0 | 0 | 0 | 5 | 90 | 0 |
| 2.5 | 20 | frozen | 1,269 | 359 | 28.3% [25.8%, 30.8%] | 910 | 5.0 / 13.0 | 0 | 0 | 5 | 90 | 0 |
| 2.5 | 50 | evolving | 1,250 | 697 | 55.8% [53.1%, 58.6%] | 553 | 13.0 / 28.0 | 0 | 0 | 24 | 135 | 0 |
| 2.5 | 50 | frozen | 1,250 | 562 | 45.0% [42.3%, 47.8%] | 688 | 14.0 / 28.0 | 0 | 0 | 24 | 135 | 0 |
| 3.0 | 5 | evolving | 354 | 68 | 19.2% [15.5%, 23.0%] | 286 | 1.0 / 3.0 | 0 | 0 | 0 | 6 | 0 |
| 3.0 | 5 | frozen | 354 | 62 | 17.5% [13.9%, 21.1%] | 292 | 1.0 / 3.0 | 0 | 0 | 0 | 6 | 0 |
| 3.0 | 10 | evolving | 352 | 93 | 26.4% [22.2%, 30.6%] | 259 | 2.0 / 6.0 | 0 | 0 | 2 | 14 | 0 |
| 3.0 | 10 | frozen | 352 | 79 | 22.4% [18.5%, 26.5%] | 273 | 2.0 / 5.0 | 0 | 0 | 2 | 14 | 0 |
| 3.0 | 15 | evolving | 351 | 119 | 33.9% [29.0%, 39.1%] | 232 | 4.0 / 9.0 | 0 | 0 | 3 | 24 | 0 |
| 3.0 | 15 | frozen | 351 | 95 | 27.1% [22.6%, 31.6%] | 256 | 3.0 / 8.0 | 0 | 0 | 3 | 24 | 0 |
| 3.0 | 20 | evolving | 350 | 139 | 39.7% [34.5%, 45.0%] | 211 | 6.0 / 13.0 | 0 | 0 | 4 | 28 | 0 |
| 3.0 | 20 | frozen | 350 | 111 | 31.7% [26.7%, 36.8%] | 239 | 4.0 / 13.0 | 0 | 0 | 4 | 28 | 0 |
| 3.0 | 50 | evolving | 347 | 189 | 54.5% [49.1%, 59.6%] | 158 | 11.0 / 22.0 | 0 | 0 | 7 | 30 | 0 |
| 3.0 | 50 | frozen | 347 | 159 | 45.8% [40.5%, 51.3%] | 188 | 11.0 / 23.5 | 0 | 0 | 7 | 30 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 2,507 | 3.37 [3.14, 3.61] / 1.75 | 3.00 [2.78, 3.26] / 1.75 | 3.00 [2.78, 3.26] / 1.75 | 3.37 [3.14, 3.61] / 1.75 | -0.17 [-0.39, 0.06] | 0.17 [-0.06, 0.39] | 46.5% [44.5%, 48.5%] | 46.5% [44.5%, 48.5%] | 43.6% [41.6%, 45.9%] | 123 | 951 / 266 | 1 | adequate descriptive support | 887 / 982 / 540 / 98 | 0 |
| 2.0 | 10 | 2,506 | 4.62 [4.32, 4.96] / 2.50 | 4.14 [3.82, 4.51] / 2.25 | 4.14 [3.82, 4.51] / 2.25 | 4.62 [4.32, 4.96] / 2.50 | -0.14 [-0.44, 0.18] | 0.14 [-0.18, 0.44] | 48.2% [46.2%, 50.3%] | 48.2% [46.2%, 50.3%] | 44.6% [42.7%, 46.5%] | 89 | 951 / 266 | 2 | adequate descriptive support | 1,048 / 1,125 / 235 / 98 | 0 |
| 2.0 | 15 | 2,505 | 5.60 [5.22, 6.03] / 3.00 | 5.00 [4.60, 5.48] / 2.75 | 5.00 [4.60, 5.48] / 2.75 | 5.60 [5.22, 6.03] / 3.00 | -0.12 [-0.47, 0.24] | 0.12 [-0.24, 0.47] | 48.1% [46.2%, 50.1%] | 48.1% [46.2%, 50.1%] | 44.1% [41.9%, 46.1%] | 72 | 951 / 266 | 3 | adequate descriptive support | 1,092 / 1,173 / 142 / 98 | 0 |
| 2.0 | 20 | 2,502 | 6.35 [5.90, 6.84] / 3.50 | 5.66 [5.23, 6.17] / 3.25 | 5.66 [5.23, 6.17] / 3.25 | 6.35 [5.90, 6.84] / 3.50 | -0.08 [-0.47, 0.29] | 0.08 [-0.29, 0.47] | 49.8% [47.8%, 51.7%] | 49.8% [47.8%, 51.7%] | 45.2% [43.4%, 47.1%] | 60 | 951 / 266 | 6 | adequate descriptive support | 1,121 / 1,195 / 88 / 98 | 0 |
| 2.0 | 50 | 2,462 | 10.02 [9.31, 10.83] / 5.75 | 8.89 [8.17, 9.69] / 5.50 | 8.89 [8.17, 9.69] / 5.50 | 10.02 [9.31, 10.83] / 5.75 | -0.11 [-0.83, 0.54] | 0.11 [-0.54, 0.83] | 51.5% [49.3%, 53.6%] | 51.5% [49.3%, 53.6%] | 46.3% [44.1%, 48.5%] | 36 | 946 / 266 | 46 | adequate descriptive support | 1,140 / 1,215 / 9 / 98 | 0 |
| 2.5 | 5 | 1,129 | 3.30 [2.98, 3.64] / 1.75 | 3.31 [2.99, 3.67] / 1.75 | 3.31 [2.99, 3.67] / 1.75 | 3.30 [2.98, 3.64] / 1.75 | 0.12 [-0.16, 0.42] | -0.12 [-0.42, 0.16] | 47.8% [44.8%, 50.8%] | 47.8% [44.8%, 50.8%] | 43.9% [40.6%, 47.0%] | 47 | 696 / 259 | 1 | adequate descriptive support | 388 / 415 / 272 / 54 | 0 |
| 2.5 | 10 | 1,129 | 4.56 [4.15, 5.00] / 2.75 | 4.52 [4.06, 5.06] / 2.50 | 4.52 [4.06, 5.06] / 2.50 | 4.56 [4.15, 5.00] / 2.75 | 0.15 [-0.27, 0.60] | -0.15 [-0.60, 0.27] | 48.4% [45.5%, 51.5%] | 48.4% [45.5%, 51.5%] | 44.2% [41.4%, 47.1%] | 36 | 696 / 259 | 1 | adequate descriptive support | 471 / 491 / 113 / 54 | 0 |
| 2.5 | 15 | 1,128 | 5.54 [5.02, 6.10] / 3.00 | 5.44 [4.85, 6.15] / 3.00 | 5.44 [4.85, 6.15] / 3.00 | 5.54 [5.02, 6.10] / 3.00 | 0.22 [-0.27, 0.75] | -0.22 [-0.75, 0.27] | 49.3% [46.6%, 52.1%] | 49.3% [46.6%, 52.1%] | 44.4% [41.2%, 47.5%] | 32 | 696 / 259 | 2 | adequate descriptive support | 492 / 514 / 68 / 54 | 0 |
| 2.5 | 20 | 1,126 | 6.28 [5.69, 6.90] / 3.50 | 6.10 [5.48, 6.87] / 3.75 | 6.10 [5.48, 6.87] / 3.75 | 6.28 [5.69, 6.90] / 3.50 | 0.19 [-0.30, 0.68] | -0.19 [-0.68, 0.30] | 50.1% [47.4%, 52.9%] | 50.1% [47.4%, 52.9%] | 45.0% [42.2%, 47.9%] | 30 | 695 / 259 | 4 | adequate descriptive support | 504 / 522 / 46 / 54 | 0 |
| 2.5 | 50 | 1,109 | 10.32 [9.37, 11.36] / 6.00 | 9.34 [8.28, 10.68] / 5.50 | 9.34 [8.28, 10.68] / 5.50 | 10.32 [9.37, 11.36] / 6.00 | -0.47 [-1.36, 0.43] | 0.47 [-0.43, 1.36] | 48.8% [45.7%, 52.0%] | 48.8% [45.7%, 52.0%] | 43.2% [40.4%, 46.0%] | 16 | 688 / 258 | 21 | adequate descriptive support | 519 / 532 / 4 / 54 | 0 |
| 3.0 | 5 | 310 | 3.55 [2.99, 4.12] / 2.00 | 3.65 [2.85, 4.65] / 1.75 | 3.65 [2.85, 4.65] / 1.75 | 3.55 [2.99, 4.12] / 2.00 | 0.29 [-0.37, 1.01] | -0.29 [-1.01, 0.37] | 48.1% [42.9%, 53.7%] | 48.1% [42.9%, 53.7%] | 43.9% [38.7%, 48.9%] | 10 | 262 / 176 | 0 | adequate descriptive support | 96 / 110 / 77 / 27 | 0 |
| 3.0 | 10 | 310 | 4.92 [4.20, 5.63] / 2.75 | 5.11 [3.96, 6.70] / 2.50 | 5.11 [3.96, 6.70] / 2.50 | 4.92 [4.20, 5.63] / 2.75 | 0.55 [-0.44, 1.82] | -0.55 [-1.82, 0.44] | 46.8% [41.1%, 52.4%] | 46.8% [41.1%, 52.4%] | 43.2% [37.9%, 48.7%] | 14 | 262 / 176 | 0 | adequate descriptive support | 119 / 130 / 34 / 27 | 0 |
| 3.0 | 15 | 309 | 5.92 [5.02, 6.88] / 3.25 | 6.18 [4.85, 7.90] / 3.00 | 6.18 [4.85, 7.90] / 3.00 | 5.92 [5.02, 6.88] / 3.25 | 0.74 [-0.23, 1.78] | -0.74 [-1.78, 0.23] | 51.5% [46.5%, 56.6%] | 51.5% [46.5%, 56.6%] | 49.5% [44.7%, 54.6%] | 10 | 261 / 176 | 1 | adequate descriptive support | 123 / 137 / 22 / 27 | 0 |
| 3.0 | 20 | 309 | 6.49 [5.53, 7.53] / 4.00 | 6.89 [5.51, 8.63] / 3.75 | 6.89 [5.51, 8.63] / 3.75 | 6.49 [5.53, 7.53] / 4.00 | 0.74 [-0.20, 1.72] | -0.74 [-1.72, 0.20] | 53.1% [48.0%, 58.3%] | 53.1% [48.0%, 58.3%] | 46.6% [41.0%, 52.1%] | 12 | 261 / 176 | 1 | adequate descriptive support | 127 / 141 / 14 / 27 | 0 |
| 3.0 | 50 | 307 | 11.11 [9.47, 13.04] / 6.75 | 9.82 [8.21, 11.66] / 5.75 | 9.82 [8.21, 11.66] / 5.75 | 11.11 [9.47, 13.04] / 6.75 | -1.47 [-3.39, 0.33] | 1.47 [-0.33, 3.39] | 45.0% [39.5%, 50.5%] | 45.0% [39.5%, 50.5%] | 42.0% [36.1%, 48.0%] | 6 | 260 / 175 | 3 | adequate descriptive support | 132 / 146 / 2 / 27 | 0 |

### Lower departure / arrival: continuation and bounce short; fade and through long

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 2,832 | 3.29 [3.07, 3.54] / 2.00 | 3.62 [3.38, 3.87] / 2.00 | 3.62 [3.38, 3.87] / 2.00 | 3.29 [3.07, 3.54] / 2.00 | 0.01 [-0.19, 0.22] | -0.01 [-0.22, 0.19] | 46.7% [44.7%, 48.6%] | 49.1% [47.3%, 50.9%] | 45.4% [43.6%, 47.2%] | 120 | 977 / 265 | 1 | adequate descriptive support |
| 2.0 | 10 | 2,831 | 4.52 [4.21, 4.84] / 2.75 | 4.90 [4.57, 5.23] / 2.75 | 4.90 [4.57, 5.23] / 2.75 | 4.52 [4.21, 4.84] / 2.75 | -0.07 [-0.35, 0.22] | 0.07 [-0.22, 0.35] | 45.3% [43.3%, 47.2%] | 51.9% [50.0%, 53.8%] | 45.6% [43.8%, 47.4%] | 81 | 977 / 265 | 2 | adequate descriptive support |
| 2.0 | 15 | 2,830 | 5.44 [5.07, 5.83] / 3.25 | 5.92 [5.53, 6.33] / 3.25 | 5.92 [5.53, 6.33] / 3.25 | 5.44 [5.07, 5.83] / 3.25 | -0.00 [-0.37, 0.35] | 0.00 [-0.35, 0.37] | 45.3% [43.4%, 47.1%] | 52.4% [50.6%, 54.4%] | 45.0% [43.1%, 46.9%] | 65 | 977 / 265 | 3 | adequate descriptive support |
| 2.0 | 20 | 2,828 | 6.17 [5.77, 6.61] / 3.75 | 6.74 [6.29, 7.21] / 3.75 | 6.74 [6.29, 7.21] / 3.75 | 6.17 [5.77, 6.61] / 3.75 | 0.07 [-0.33, 0.47] | -0.07 [-0.47, 0.33] | 45.5% [43.7%, 47.3%] | 52.4% [50.6%, 54.1%] | 42.6% [40.9%, 44.6%] | 61 | 977 / 265 | 5 | adequate descriptive support |
| 2.0 | 50 | 2,783 | 9.38 [8.77, 10.03] / 5.75 | 10.09 [9.41, 10.76] / 5.75 | 10.09 [9.41, 10.76] / 5.75 | 9.38 [8.77, 10.03] / 5.75 | 0.15 [-0.40, 0.70] | -0.15 [-0.70, 0.40] | 46.5% [44.4%, 48.4%] | 52.0% [50.0%, 54.1%] | 45.8% [44.1%, 47.7%] | 43 | 976 / 265 | 50 | adequate descriptive support |
| 2.5 | 5 | 1,429 | 3.51 [3.22, 3.81] / 2.00 | 3.89 [3.56, 4.24] / 2.00 | 3.89 [3.56, 4.24] / 2.00 | 3.51 [3.22, 3.81] / 2.00 | -0.15 [-0.48, 0.19] | 0.15 [-0.19, 0.48] | 45.6% [43.1%, 48.3%] | 50.0% [47.4%, 52.5%] | 47.5% [45.1%, 49.9%] | 64 | 797 / 262 | 0 | adequate descriptive support |
| 2.5 | 10 | 1,429 | 4.77 [4.38, 5.16] / 2.75 | 5.35 [4.91, 5.82] / 2.75 | 5.35 [4.91, 5.82] / 2.75 | 4.77 [4.38, 5.16] / 2.75 | 0.14 [-0.30, 0.57] | -0.14 [-0.57, 0.30] | 46.9% [44.4%, 49.3%] | 51.2% [48.9%, 53.6%] | 45.6% [42.9%, 48.3%] | 27 | 797 / 262 | 0 | adequate descriptive support |
| 2.5 | 15 | 1,429 | 5.68 [5.22, 6.15] / 3.25 | 6.41 [5.88, 6.97] / 3.25 | 6.41 [5.88, 6.97] / 3.25 | 5.68 [5.22, 6.15] / 3.25 | 0.16 [-0.35, 0.65] | -0.16 [-0.65, 0.35] | 47.0% [44.4%, 49.6%] | 50.4% [47.7%, 53.0%] | 45.3% [42.8%, 47.9%] | 37 | 797 / 262 | 0 | adequate descriptive support |
| 2.5 | 20 | 1,428 | 6.38 [5.89, 6.89] / 3.75 | 7.12 [6.52, 7.75] / 3.75 | 7.12 [6.52, 7.75] / 3.75 | 6.38 [5.89, 6.89] / 3.75 | 0.16 [-0.40, 0.74] | -0.16 [-0.74, 0.40] | 47.1% [44.6%, 49.8%] | 50.8% [48.1%, 53.4%] | 42.8% [40.1%, 45.4%] | 30 | 797 / 262 | 1 | adequate descriptive support |
| 2.5 | 50 | 1,402 | 9.32 [8.59, 10.05] / 6.00 | 10.40 [9.56, 11.26] / 5.75 | 10.40 [9.56, 11.26] / 5.75 | 9.32 [8.59, 10.05] / 6.00 | 0.47 [-0.32, 1.27] | -0.47 [-1.27, 0.32] | 47.6% [45.0%, 50.3%] | 50.7% [48.0%, 53.4%] | 46.6% [44.3%, 49.1%] | 24 | 792 / 262 | 27 | adequate descriptive support |
| 3.0 | 5 | 448 | 3.73 [3.25, 4.27] / 2.00 | 3.77 [3.29, 4.25] / 1.75 | 3.77 [3.29, 4.25] / 1.75 | 3.73 [3.25, 4.27] / 2.00 | -0.29 [-0.90, 0.27] | 0.29 [-0.27, 0.90] | 46.4% [42.0%, 51.0%] | 49.1% [44.5%, 53.8%] | 44.6% [39.9%, 49.3%] | 20 | 354 / 214 | 0 | adequate descriptive support |
| 3.0 | 10 | 448 | 4.79 [4.18, 5.43] / 2.75 | 4.98 [4.35, 5.62] / 2.62 | 4.98 [4.35, 5.62] / 2.62 | 4.79 [4.18, 5.43] / 2.75 | -0.08 [-0.85, 0.73] | 0.08 [-0.73, 0.85] | 46.2% [41.8%, 50.8%] | 52.5% [47.9%, 57.0%] | 48.4% [43.9%, 53.0%] | 6 | 354 / 214 | 0 | adequate descriptive support |
| 3.0 | 15 | 448 | 5.68 [4.98, 6.41] / 3.25 | 5.94 [5.20, 6.72] / 3.00 | 5.94 [5.20, 6.72] / 3.00 | 5.68 [4.98, 6.41] / 3.25 | -0.03 [-0.90, 0.85] | 0.03 [-0.85, 0.90] | 44.9% [40.4%, 49.6%] | 52.2% [47.6%, 56.6%] | 41.3% [36.5%, 46.1%] | 13 | 354 / 214 | 0 | adequate descriptive support |
| 3.0 | 20 | 448 | 6.43 [5.65, 7.28] / 3.75 | 6.53 [5.70, 7.45] / 3.50 | 6.53 [5.70, 7.45] / 3.50 | 6.43 [5.65, 7.28] / 3.75 | -0.53 [-1.55, 0.52] | 0.53 [-0.52, 1.55] | 43.3% [38.9%, 47.7%] | 54.2% [49.9%, 58.6%] | 45.3% [40.5%, 49.9%] | 11 | 354 / 214 | 0 | adequate descriptive support |
| 3.0 | 50 | 439 | 9.26 [8.20, 10.41] / 6.00 | 10.02 [8.78, 11.44] / 5.75 | 10.02 [8.78, 11.44] / 5.75 | 9.26 [8.20, 10.41] / 6.00 | 0.67 [-0.65, 2.02] | -0.67 [-2.02, 0.65] | 45.3% [41.0%, 49.8%] | 53.5% [49.1%, 57.9%] | 43.3% [39.0%, 47.8%] | 5 | 350 / 212 | 9 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 2,832 | 572 | 20.2% [18.8%, 21.7%] | 2,260 | 3.0 / 4.0 | 0 | 0 | 1 | 84 | 0 |
| 2.0 | 5 | frozen | 2,832 | 488 | 17.2% [15.8%, 18.7%] | 2,344 | 2.0 / 4.0 | 0 | 0 | 1 | 84 | 0 |
| 2.0 | 10 | evolving | 2,831 | 876 | 30.9% [29.3%, 32.7%] | 1,955 | 4.0 / 7.0 | 0 | 0 | 2 | 142 | 0 |
| 2.0 | 10 | frozen | 2,831 | 734 | 25.9% [24.3%, 27.7%] | 2,097 | 4.0 / 6.8 | 0 | 0 | 2 | 142 | 0 |
| 2.0 | 15 | evolving | 2,830 | 1,102 | 38.9% [37.3%, 40.6%] | 1,728 | 5.0 / 9.0 | 0 | 0 | 3 | 191 | 0 |
| 2.0 | 15 | frozen | 2,830 | 911 | 32.2% [30.5%, 34.0%] | 1,919 | 5.0 / 9.0 | 0 | 0 | 3 | 191 | 0 |
| 2.0 | 20 | evolving | 2,828 | 1,265 | 44.7% [42.9%, 46.5%] | 1,563 | 6.0 / 12.0 | 0 | 0 | 5 | 227 | 0 |
| 2.0 | 20 | frozen | 2,828 | 1,038 | 36.7% [35.0%, 38.6%] | 1,790 | 6.0 / 12.0 | 0 | 0 | 5 | 227 | 0 |
| 2.0 | 50 | evolving | 2,783 | 1,827 | 65.6% [63.9%, 67.4%] | 956 | 11.0 / 24.0 | 0 | 0 | 50 | 335 | 0 |
| 2.0 | 50 | frozen | 2,783 | 1,492 | 53.6% [51.6%, 55.7%] | 1,291 | 11.0 / 24.0 | 0 | 0 | 50 | 335 | 0 |
| 2.5 | 5 | evolving | 1,429 | 234 | 16.4% [14.5%, 18.4%] | 1,195 | 2.0 / 4.0 | 0 | 0 | 0 | 38 | 0 |
| 2.5 | 5 | frozen | 1,429 | 196 | 13.7% [12.0%, 15.5%] | 1,233 | 2.0 / 3.0 | 0 | 0 | 0 | 38 | 0 |
| 2.5 | 10 | evolving | 1,429 | 370 | 25.9% [23.8%, 28.1%] | 1,059 | 4.0 / 7.0 | 0 | 0 | 0 | 67 | 0 |
| 2.5 | 10 | frozen | 1,429 | 303 | 21.2% [19.2%, 23.3%] | 1,126 | 3.0 / 7.0 | 0 | 0 | 0 | 67 | 0 |
| 2.5 | 15 | evolving | 1,429 | 461 | 32.3% [29.8%, 34.7%] | 968 | 5.0 / 9.0 | 0 | 0 | 0 | 87 | 0 |
| 2.5 | 15 | frozen | 1,429 | 374 | 26.2% [23.9%, 28.6%] | 1,055 | 5.0 / 9.0 | 0 | 0 | 0 | 87 | 0 |
| 2.5 | 20 | evolving | 1,428 | 535 | 37.5% [34.8%, 40.0%] | 893 | 6.0 / 12.0 | 0 | 0 | 1 | 103 | 0 |
| 2.5 | 20 | frozen | 1,428 | 432 | 30.3% [27.9%, 32.7%] | 996 | 6.0 / 12.0 | 0 | 0 | 1 | 103 | 0 |
| 2.5 | 50 | evolving | 1,402 | 831 | 59.3% [56.9%, 61.7%] | 571 | 13.0 / 27.0 | 0 | 0 | 27 | 185 | 0 |
| 2.5 | 50 | frozen | 1,402 | 646 | 46.1% [43.5%, 48.8%] | 756 | 12.0 / 26.0 | 0 | 0 | 27 | 185 | 0 |
| 3.0 | 5 | evolving | 448 | 89 | 19.9% [16.3%, 23.7%] | 359 | 2.0 / 4.0 | 0 | 0 | 0 | 18 | 0 |
| 3.0 | 5 | frozen | 448 | 71 | 15.8% [12.7%, 19.2%] | 377 | 2.0 / 2.5 | 0 | 0 | 0 | 18 | 0 |
| 3.0 | 10 | evolving | 448 | 118 | 26.3% [22.4%, 30.2%] | 330 | 3.0 / 5.0 | 0 | 0 | 0 | 22 | 0 |
| 3.0 | 10 | frozen | 448 | 96 | 21.4% [17.8%, 25.1%] | 352 | 2.0 / 6.0 | 0 | 0 | 0 | 22 | 0 |
| 3.0 | 15 | evolving | 448 | 147 | 32.8% [28.5%, 37.2%] | 301 | 4.0 / 8.5 | 0 | 0 | 0 | 29 | 0 |
| 3.0 | 15 | frozen | 448 | 118 | 26.3% [22.2%, 30.6%] | 330 | 3.0 / 8.8 | 0 | 0 | 0 | 29 | 0 |
| 3.0 | 20 | evolving | 448 | 166 | 37.1% [32.4%, 41.5%] | 282 | 5.0 / 11.8 | 0 | 0 | 0 | 32 | 0 |
| 3.0 | 20 | frozen | 448 | 134 | 29.9% [25.7%, 34.2%] | 314 | 5.0 / 11.0 | 0 | 0 | 0 | 32 | 0 |
| 3.0 | 50 | evolving | 439 | 258 | 58.8% [53.9%, 63.3%] | 181 | 12.0 / 26.0 | 0 | 0 | 9 | 53 | 0 |
| 3.0 | 50 | frozen | 439 | 205 | 46.7% [42.0%, 51.4%] | 234 | 11.0 / 26.0 | 0 | 0 | 9 | 53 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 2,604 | 3.13 [2.88, 3.38] / 1.75 | 3.07 [2.84, 3.35] / 1.75 | 3.07 [2.84, 3.35] / 1.75 | 3.13 [2.88, 3.38] / 1.75 | -0.05 [-0.24, 0.17] | 0.05 [-0.17, 0.24] | 46.0% [44.0%, 48.1%] | 49.7% [47.7%, 51.7%] | 44.8% [42.6%, 46.9%] | 112 | 960 / 265 | 2 | adequate descriptive support | 900 / 968 / 656 / 80 | 0 |
| 2.0 | 10 | 2,602 | 4.27 [3.97, 4.60] / 2.50 | 4.31 [3.98, 4.67] / 2.25 | 4.31 [3.98, 4.67] / 2.25 | 4.27 [3.97, 4.60] / 2.50 | -0.03 [-0.29, 0.22] | 0.03 [-0.22, 0.29] | 47.5% [45.8%, 49.3%] | 49.0% [47.2%, 50.9%] | 45.2% [43.3%, 47.2%] | 90 | 960 / 265 | 4 | adequate descriptive support | 1,063 / 1,124 / 334 / 81 | 0 |
| 2.0 | 15 | 2,602 | 5.24 [4.86, 5.60] / 3.00 | 5.19 [4.82, 5.62] / 2.75 | 5.19 [4.82, 5.62] / 2.75 | 5.24 [4.86, 5.60] / 3.00 | -0.30 [-0.62, 0.02] | 0.30 [-0.02, 0.62] | 46.0% [44.0%, 48.2%] | 51.3% [49.2%, 53.3%] | 47.0% [45.3%, 48.8%] | 69 | 960 / 265 | 4 | adequate descriptive support | 1,137 / 1,187 / 197 / 81 | 0 |
| 2.0 | 20 | 2,600 | 5.98 [5.58, 6.39] / 3.50 | 5.91 [5.49, 6.38] / 3.25 | 5.91 [5.49, 6.38] / 3.25 | 5.98 [5.58, 6.39] / 3.50 | -0.26 [-0.61, 0.09] | 0.26 [-0.09, 0.61] | 45.7% [43.8%, 47.7%] | 51.4% [49.5%, 53.2%] | 44.3% [42.4%, 46.2%] | 75 | 960 / 265 | 6 | adequate descriptive support | 1,169 / 1,219 / 131 / 81 | 0 |
| 2.0 | 50 | 2,538 | 9.21 [8.58, 9.87] / 5.50 | 9.25 [8.60, 9.89] / 5.50 | 9.25 [8.60, 9.89] / 5.50 | 9.21 [8.58, 9.87] / 5.50 | -0.35 [-0.91, 0.19] | 0.35 [-0.19, 0.91] | 46.5% [44.6%, 48.2%] | 52.4% [50.7%, 54.3%] | 45.1% [43.2%, 46.9%] | 30 | 953 / 264 | 68 | adequate descriptive support | 1,201 / 1,239 / 16 / 82 | 0 |
| 2.5 | 5 | 1,288 | 3.12 [2.80, 3.47] / 1.75 | 3.16 [2.87, 3.48] / 1.75 | 3.16 [2.87, 3.48] / 1.75 | 3.12 [2.80, 3.47] / 1.75 | 0.08 [-0.23, 0.39] | -0.08 [-0.39, 0.23] | 46.4% [43.5%, 49.3%] | 48.7% [45.9%, 51.5%] | 45.5% [42.5%, 48.6%] | 63 | 742 / 260 | 2 | adequate descriptive support | 434 / 437 / 378 / 39 | 0 |
| 2.5 | 10 | 1,287 | 4.25 [3.85, 4.69] / 2.50 | 4.50 [4.08, 4.98] / 2.50 | 4.50 [4.08, 4.98] / 2.50 | 4.25 [3.85, 4.69] / 2.50 | 0.16 [-0.21, 0.55] | -0.16 [-0.55, 0.21] | 48.2% [45.7%, 50.6%] | 48.6% [46.2%, 51.2%] | 46.7% [43.9%, 49.5%] | 41 | 742 / 260 | 3 | adequate descriptive support | 532 / 519 / 197 / 39 | 0 |
| 2.5 | 15 | 1,287 | 5.19 [4.70, 5.70] / 3.00 | 5.42 [4.94, 6.00] / 3.00 | 5.42 [4.94, 6.00] / 3.00 | 5.19 [4.70, 5.70] / 3.00 | -0.11 [-0.55, 0.35] | 0.11 [-0.35, 0.55] | 47.5% [44.8%, 50.2%] | 49.9% [47.2%, 52.6%] | 47.2% [44.7%, 49.7%] | 34 | 742 / 260 | 3 | adequate descriptive support | 583 / 553 / 112 / 39 | 0 |
| 2.5 | 20 | 1,285 | 5.91 [5.36, 6.47] / 3.25 | 6.18 [5.64, 6.81] / 3.50 | 6.18 [5.64, 6.81] / 3.50 | 5.91 [5.36, 6.47] / 3.25 | -0.11 [-0.63, 0.42] | 0.11 [-0.42, 0.63] | 47.2% [44.6%, 50.0%] | 50.7% [48.2%, 53.3%] | 44.4% [41.6%, 47.0%] | 26 | 742 / 260 | 5 | adequate descriptive support | 598 / 570 / 78 / 39 | 0 |
| 2.5 | 50 | 1,252 | 9.19 [8.39, 9.99] / 5.50 | 9.50 [8.72, 10.36] / 5.62 | 9.50 [8.72, 10.36] / 5.62 | 9.19 [8.39, 9.99] / 5.50 | -0.06 [-0.85, 0.74] | 0.06 [-0.74, 0.85] | 46.6% [43.7%, 49.3%] | 52.6% [49.9%, 55.5%] | 43.7% [40.8%, 46.4%] | 10 | 728 / 260 | 38 | adequate descriptive support | 619 / 583 / 10 / 40 | 0 |
| 3.0 | 5 | 407 | 3.33 [2.68, 4.18] / 1.75 | 3.08 [2.63, 3.64] / 1.75 | 3.08 [2.63, 3.64] / 1.75 | 3.33 [2.68, 4.18] / 1.75 | -0.06 [-0.77, 0.58] | 0.06 [-0.58, 0.77] | 47.2% [42.6%, 52.1%] | 47.7% [43.1%, 52.2%] | 44.0% [39.1%, 48.7%] | 21 | 328 / 208 | 0 | adequate descriptive support | 125 / 147 / 114 / 21 | 0 |
| 3.0 | 10 | 406 | 4.37 [3.65, 5.27] / 2.38 | 4.72 [3.99, 5.57] / 2.50 | 4.72 [3.99, 5.57] / 2.50 | 4.37 [3.65, 5.27] / 2.38 | 0.59 [-0.20, 1.39] | -0.59 [-1.39, 0.20] | 49.8% [45.1%, 54.5%] | 46.6% [41.6%, 51.4%] | 43.8% [39.1%, 48.7%] | 15 | 328 / 208 | 1 | adequate descriptive support | 151 / 174 / 60 / 21 | 0 |
| 3.0 | 15 | 406 | 5.04 [4.27, 5.99] / 2.75 | 5.64 [4.77, 6.63] / 3.00 | 5.64 [4.77, 6.63] / 3.00 | 5.04 [4.27, 5.99] / 2.75 | 0.31 [-0.71, 1.32] | -0.31 [-1.32, 0.71] | 50.5% [45.7%, 55.5%] | 46.8% [41.8%, 51.6%] | 48.8% [44.0%, 54.0%] | 11 | 328 / 208 | 1 | adequate descriptive support | 166 / 181 / 38 / 21 | 0 |
| 3.0 | 20 | 406 | 5.67 [4.87, 6.67] / 3.25 | 6.52 [5.53, 7.65] / 3.50 | 6.52 [5.53, 7.65] / 3.50 | 5.67 [4.87, 6.67] / 3.25 | 0.86 [-0.23, 2.04] | -0.86 [-2.04, 0.23] | 49.8% [44.9%, 54.7%] | 48.3% [43.5%, 53.1%] | 41.6% [37.3%, 46.2%] | 8 | 328 / 208 | 1 | adequate descriptive support | 171 / 191 / 23 / 21 | 0 |
| 3.0 | 50 | 395 | 9.10 [7.92, 10.44] / 5.75 | 9.99 [8.50, 11.56] / 5.25 | 9.99 [8.50, 11.56] / 5.25 | 9.10 [7.92, 10.44] / 5.75 | 0.34 [-1.27, 1.90] | -0.34 [-1.90, 1.27] | 48.1% [42.7%, 53.0%] | 50.9% [46.0%, 56.3%] | 42.5% [37.5%, 47.2%] | 4 | 318 / 205 | 12 | adequate descriptive support | 175 / 194 / 5 / 21 | 0 |

### Common cohort, distribution and year diagnostics

The horizon curves use the identical complete-50 cohort. Distribution quantiles and year diagnostics use each horizon’s eligible cohort. Year 2026 is partial. These diagnostics are descriptive on previously inspected history.

![ES Globex return](figures/globex-ES-return.svg)

![ES Globex excursion](figures/globex-ES-excursion.svg)

![ES Globex endpoint](figures/globex-ES-endpoint.svg)

![ES Globex mae-mfe-distribution](figures/globex-ES-mae-mfe-distribution.svg)

![ES Globex terminal-distribution](figures/globex-ES-terminal-distribution.svg)

![ES Globex year-stability](figures/globex-ES-year-stability.svg)

### Sensitivity and chronological periods at 10 candles

| Module | Scope | n | Days / weeks | Directional Δ [CI] | Return or bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- |
| departure | all | 5,645 | 1,036 / 267 | -0.00 [-0.20, 0.20] | 29.6% [28.4%, 30.9%] |
| departure | common_50 | 5,546 | 1,036 / 267 | 0.00 [-0.19, 0.20] | 30.1% [28.8%, 31.4%] |
| departure | age_ge30 | 4,638 | 1,030 / 267 | 0.06 [-0.18, 0.31] | 19.1% [17.9%, 20.4%] |
| departure | through_2023 | 2,917 | 495 / 126 | -0.15 [-0.38, 0.10] | 29.9% [28.1%, 31.6%] |
| departure | year_2024_period | 866 | 159 / 52 | 0.28 [-0.14, 0.76] | 30.0% [26.6%, 33.4%] |
| departure | years_2025_2026 | 1,862 | 382 / 90 | 0.09 [-0.32, 0.53] | 28.9% [26.7%, 31.2%] |
| touch | all | 5,108 | 1,034 / 267 | -0.08 [-0.29, 0.14] | 47.9% [46.5%, 49.2%] |
| touch | common_50 | 5,000 | 1,034 / 267 | -0.09 [-0.30, 0.14] | 48.0% [46.6%, 49.3%] |
| touch | age_ge30 | 4,101 | 1,023 / 267 | -0.07 [-0.33, 0.20] | 48.0% [46.4%, 49.5%] |
| touch | through_2023 | 2,643 | 494 / 126 | -0.16 [-0.39, 0.06] | 47.7% [45.9%, 49.4%] |
| touch | year_2024_period | 783 | 158 / 52 | -0.16 [-0.58, 0.27] | 47.6% [43.7%, 51.9%] |
| touch | years_2025_2026 | 1,682 | 382 / 90 | 0.08 [-0.41, 0.60] | 48.3% [45.8%, 50.8%] |

### Deterministic source-path examples

Examples are the earliest stable ID in each prespecified class. They illustrate mechanisms and exclusions, not representative trade quality. The source table includes reference available_at and known sigma for every minute; charts plot raw one-minute high/low and references. Source minute open time relative to entry is shown; contacts have interval resolution. Lines join minute OHLC observations for display and do not imply intraminute order or trades through gaps. The 2-sigma envelope is plotted; 2.5/3-sigma references are retained in the example-path table.

return: ES-globex-2021-06-28-P0003-K2-H10; lower side. Signal/confirmation 2021-06-27 18:08:00-04:00; entry 2021-06-27 18:08:00-04:00; deadline 2021-06-27 18:28:00-04:00 (New York time). Frozen sigma 0.32 points; signal VWAP 4,276.01. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-globex-2021-06-28-P0003-K2-H10](figures/example-globex-ES-return.svg)

non_return: ES-globex-2021-06-28-P0061-K2-H10; lower side. Signal/confirmation 2021-06-27 20:04:00-04:00; entry 2021-06-27 20:04:00-04:00; deadline 2021-06-27 20:24:00-04:00 (New York time). Frozen sigma 0.71 points; signal VWAP 4,276.69. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-globex-2021-06-28-P0061-K2-H10](figures/example-globex-ES-non_return.svg)

bounce: ES-globex-2021-06-28-P0008-T-H10; upper side. Signal/confirmation 2021-06-27 18:22:00-04:00; entry 2021-06-27 18:22:00-04:00; deadline 2021-06-27 18:42:00-04:00 (New York time). Frozen sigma 0.41 points; signal VWAP 4,276.17. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-globex-2021-06-28-P0008-T-H10](figures/example-globex-ES-bounce.svg)

through: ES-globex-2021-06-28-P0013-T-H10; upper side. Signal/confirmation 2021-06-27 18:38:00-04:00; entry 2021-06-27 18:38:00-04:00; deadline 2021-06-27 18:58:00-04:00 (New York time). Frozen sigma 0.81 points; signal VWAP 4,276.65. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-globex-2021-06-28-P0013-T-H10](figures/example-globex-ES-through.svg)

ambiguity: ES-globex-2021-06-28-P0003-T-H10; lower side. Signal/confirmation 2021-06-27 18:10:00-04:00; entry 2021-06-27 18:10:00-04:00; deadline 2021-06-27 18:30:00-04:00 (New York time). Frozen sigma 0.31 points; signal VWAP 4,275.99. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![ES-globex-2021-06-28-P0003-T-H10](figures/example-globex-ES-ambiguity.svg)

exclusion: ES-globex-2021-06-28-P0647-K2-H50; upper side. Signal/confirmation 2021-06-28 15:36:00-04:00; entry 2021-06-28 15:36:00-04:00; deadline 2021-06-28 17:16:00-04:00 (New York time). Frozen sigma 3.23 points; signal VWAP 4,271.71. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: session_boundary.

![ES-globex-2021-06-28-P0647-K2-H50](figures/example-globex-ES-exclusion.svg)

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
| 2.0 | 5 | 2,999 | 12.74 [11.84, 13.73] / 6.75 | 13.37 [12.44, 14.42] / 7.50 | 13.37 [12.44, 14.42] / 7.50 | 12.74 [11.84, 13.73] / 6.75 | 0.35 [-0.41, 1.16] | -0.35 [-1.16, 0.41] | 49.1% [47.4%, 50.9%] | 49.1% [47.4%, 50.9%] | 47.7% [45.9%, 49.4%] | 39 | 1,106 / 273 | 1 | adequate descriptive support |
| 2.0 | 10 | 2,997 | 17.58 [16.36, 18.88] / 9.50 | 18.35 [16.92, 20.12] / 10.25 | 18.35 [16.92, 20.12] / 10.25 | 17.58 [16.36, 18.88] / 9.50 | 0.70 [-0.49, 1.92] | -0.70 [-1.92, 0.49] | 49.8% [48.1%, 51.6%] | 49.8% [48.1%, 51.6%] | 48.6% [46.9%, 50.5%] | 22 | 1,106 / 273 | 3 | adequate descriptive support |
| 2.0 | 15 | 2,993 | 21.76 [20.26, 23.41] / 11.25 | 22.15 [20.52, 24.07] / 12.50 | 22.15 [20.52, 24.07] / 12.50 | 21.76 [20.26, 23.41] / 11.25 | 0.43 [-0.97, 1.80] | -0.43 [-1.80, 0.97] | 51.2% [49.4%, 52.9%] | 51.2% [49.4%, 52.9%] | 48.7% [46.9%, 50.4%] | 15 | 1,106 / 273 | 7 | adequate descriptive support |
| 2.0 | 20 | 2,985 | 24.84 [23.07, 26.80] / 13.25 | 25.00 [23.17, 27.07] / 14.50 | 25.00 [23.17, 27.07] / 14.50 | 24.84 [23.07, 26.80] / 13.25 | 0.48 [-1.17, 2.00] | -0.48 [-2.00, 1.17] | 50.4% [48.6%, 52.0%] | 50.4% [48.6%, 52.0%] | 49.5% [47.5%, 51.4%] | 24 | 1,106 / 273 | 15 | adequate descriptive support |
| 2.0 | 50 | 2,934 | 39.82 [37.03, 42.82] / 21.25 | 37.57 [35.20, 40.36] / 22.75 | 37.57 [35.20, 40.36] / 22.75 | 39.82 [37.03, 42.82] / 21.25 | 0.69 [-1.75, 2.93] | -0.69 [-2.93, 1.75] | 52.1% [50.2%, 54.0%] | 52.1% [50.2%, 54.0%] | 50.2% [48.5%, 52.1%] | 12 | 1,101 / 273 | 66 | adequate descriptive support |
| 2.5 | 5 | 1,472 | 13.30 [11.89, 14.82] / 7.00 | 14.69 [12.77, 17.43] / 7.75 | 14.69 [12.77, 17.43] / 7.75 | 13.30 [11.89, 14.82] / 7.00 | 0.86 [-0.29, 2.14] | -0.86 [-2.14, 0.29] | 49.0% [46.5%, 51.6%] | 49.0% [46.5%, 51.6%] | 47.6% [44.9%, 50.2%] | 14 | 852 / 265 | 1 | adequate descriptive support |
| 2.5 | 10 | 1,469 | 18.52 [16.66, 20.74] / 9.50 | 19.16 [16.88, 22.23] / 10.75 | 19.16 [16.88, 22.23] / 10.75 | 18.52 [16.66, 20.74] / 9.50 | 0.38 [-1.29, 1.96] | -0.38 [-1.96, 1.29] | 48.9% [46.5%, 51.5%] | 48.9% [46.5%, 51.5%] | 48.7% [46.2%, 51.3%] | 7 | 852 / 265 | 4 | adequate descriptive support |
| 2.5 | 15 | 1,467 | 22.81 [20.41, 25.54] / 11.25 | 23.21 [20.62, 26.65] / 12.50 | 23.21 [20.62, 26.65] / 12.50 | 22.81 [20.41, 25.54] / 11.25 | 0.54 [-1.71, 2.54] | -0.54 [-2.54, 1.71] | 50.0% [47.2%, 52.6%] | 50.0% [47.2%, 52.6%] | 46.2% [43.7%, 48.7%] | 10 | 852 / 265 | 6 | adequate descriptive support |
| 2.5 | 20 | 1,463 | 26.00 [23.42, 28.98] / 13.00 | 25.78 [23.03, 29.51] / 14.50 | 25.78 [23.03, 29.51] / 14.50 | 26.00 [23.42, 28.98] / 13.00 | 0.77 [-1.74, 3.19] | -0.77 [-3.19, 1.74] | 48.7% [46.0%, 51.5%] | 48.7% [46.0%, 51.5%] | 48.9% [46.4%, 51.3%] | 9 | 850 / 265 | 10 | adequate descriptive support |
| 2.5 | 50 | 1,438 | 40.99 [37.29, 45.29] / 21.25 | 38.37 [34.80, 42.87] / 22.25 | 38.37 [34.80, 42.87] / 22.25 | 40.99 [37.29, 45.29] / 21.25 | -0.21 [-3.67, 3.40] | 0.21 [-3.40, 3.67] | 51.0% [48.4%, 53.8%] | 51.0% [48.4%, 53.8%] | 48.7% [45.8%, 51.4%] | 4 | 846 / 265 | 35 | adequate descriptive support |
| 3.0 | 5 | 453 | 16.52 [13.35, 20.55] / 7.50 | 18.75 [13.71, 26.56] / 8.50 | 18.75 [13.71, 26.56] / 8.50 | 16.52 [13.35, 20.55] / 7.50 | 0.51 [-2.74, 3.74] | -0.51 [-3.74, 2.74] | 48.3% [43.6%, 53.2%] | 48.3% [43.6%, 53.2%] | 46.1% [41.6%, 50.8%] | 2 | 381 / 220 | 0 | adequate descriptive support |
| 3.0 | 10 | 452 | 21.82 [17.49, 27.90] / 10.25 | 23.90 [18.31, 32.42] / 11.25 | 23.90 [18.31, 32.42] / 11.25 | 21.82 [17.49, 27.90] / 10.25 | 1.10 [-2.51, 4.50] | -1.10 [-4.50, 2.51] | 51.3% [46.6%, 55.8%] | 51.3% [46.6%, 55.8%] | 51.8% [47.0%, 56.5%] | 4 | 381 / 220 | 1 | adequate descriptive support |
| 3.0 | 15 | 450 | 25.75 [20.83, 32.49] / 12.25 | 28.26 [22.19, 37.24] / 12.75 | 28.26 [22.19, 37.24] / 12.75 | 25.75 [20.83, 32.49] / 12.25 | 2.84 [-1.82, 7.25] | -2.84 [-7.25, 1.82] | 50.4% [46.0%, 54.8%] | 50.4% [46.0%, 54.8%] | 50.7% [45.9%, 55.4%] | 3 | 379 / 220 | 3 | adequate descriptive support |
| 3.0 | 20 | 448 | 28.63 [23.55, 35.37] / 14.00 | 31.19 [24.45, 40.87] / 14.62 | 31.19 [24.45, 40.87] / 14.62 | 28.63 [23.55, 35.37] / 14.00 | 3.07 [-2.45, 8.73] | -3.07 [-8.73, 2.45] | 50.0% [45.4%, 54.6%] | 50.0% [45.4%, 54.6%] | 51.6% [46.6%, 56.5%] | 2 | 377 / 219 | 5 | adequate descriptive support |
| 3.0 | 50 | 436 | 44.67 [37.86, 52.89] / 22.25 | 44.33 [35.90, 56.01] / 22.25 | 44.33 [35.90, 56.01] / 22.25 | 44.67 [37.86, 52.89] / 22.25 | -1.15 [-7.88, 5.40] | 1.15 [-5.40, 7.88] | 48.4% [43.7%, 53.0%] | 48.4% [43.7%, 53.0%] | 47.9% [43.4%, 52.2%] | 2 | 368 / 218 | 17 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 2,999 | 424 | 14.1% [12.8%, 15.5%] | 2,575 | 3.0 / 4.0 | 20 | 0 | 1 | 63 | 0 |
| 2.0 | 5 | frozen | 2,999 | 361 | 12.0% [10.7%, 13.4%] | 2,638 | 3.0 / 4.0 | 20 | 0 | 1 | 63 | 0 |
| 2.0 | 10 | evolving | 2,997 | 713 | 23.8% [22.2%, 25.4%] | 2,284 | 5.0 / 7.0 | 39 | 0 | 3 | 117 | 0 |
| 2.0 | 10 | frozen | 2,997 | 596 | 19.9% [18.3%, 21.7%] | 2,401 | 4.0 / 7.0 | 39 | 0 | 3 | 117 | 0 |
| 2.0 | 15 | evolving | 2,993 | 889 | 29.7% [28.1%, 31.4%] | 2,104 | 6.0 / 9.0 | 56 | 0 | 7 | 144 | 0 |
| 2.0 | 15 | frozen | 2,993 | 745 | 24.9% [23.3%, 26.7%] | 2,248 | 6.0 / 10.0 | 56 | 0 | 7 | 144 | 0 |
| 2.0 | 20 | evolving | 2,985 | 1,071 | 35.9% [34.3%, 37.6%] | 1,914 | 7.0 / 13.0 | 78 | 0 | 15 | 201 | 0 |
| 2.0 | 20 | frozen | 2,985 | 870 | 29.1% [27.4%, 31.0%] | 2,115 | 7.0 / 12.0 | 78 | 0 | 15 | 201 | 0 |
| 2.0 | 50 | evolving | 2,934 | 1,688 | 57.5% [56.0%, 59.2%] | 1,246 | 14.0 / 27.0 | 196 | 1 | 66 | 315 | 0 |
| 2.0 | 50 | frozen | 2,934 | 1,373 | 46.8% [44.9%, 48.7%] | 1,561 | 14.0 / 27.0 | 196 | 1 | 66 | 315 | 0 |
| 2.5 | 5 | evolving | 1,472 | 177 | 12.0% [10.4%, 13.6%] | 1,295 | 3.0 / 4.0 | 4 | 0 | 1 | 26 | 0 |
| 2.5 | 5 | frozen | 1,472 | 151 | 10.3% [8.7%, 11.8%] | 1,321 | 2.0 / 3.0 | 4 | 0 | 1 | 26 | 0 |
| 2.5 | 10 | evolving | 1,469 | 284 | 19.3% [17.4%, 21.5%] | 1,185 | 4.0 / 7.0 | 13 | 0 | 4 | 49 | 0 |
| 2.5 | 10 | frozen | 1,469 | 235 | 16.0% [14.2%, 18.0%] | 1,234 | 4.0 / 7.0 | 13 | 0 | 4 | 49 | 0 |
| 2.5 | 15 | evolving | 1,467 | 375 | 25.6% [23.5%, 27.7%] | 1,092 | 6.0 / 10.0 | 18 | 0 | 6 | 71 | 0 |
| 2.5 | 15 | frozen | 1,467 | 304 | 20.7% [18.7%, 22.8%] | 1,163 | 6.0 / 10.0 | 18 | 0 | 6 | 71 | 0 |
| 2.5 | 20 | evolving | 1,463 | 448 | 30.6% [28.6%, 32.8%] | 1,015 | 7.0 / 13.0 | 27 | 0 | 10 | 89 | 0 |
| 2.5 | 20 | frozen | 1,463 | 359 | 24.5% [22.4%, 26.8%] | 1,104 | 7.0 / 13.0 | 27 | 0 | 10 | 89 | 0 |
| 2.5 | 50 | evolving | 1,438 | 758 | 52.7% [50.1%, 55.2%] | 680 | 16.0 / 29.0 | 80 | 1 | 35 | 157 | 0 |
| 2.5 | 50 | frozen | 1,438 | 601 | 41.8% [39.4%, 44.3%] | 837 | 15.0 / 29.0 | 80 | 1 | 35 | 157 | 0 |
| 3.0 | 5 | evolving | 453 | 54 | 11.9% [9.0%, 14.9%] | 399 | 2.0 / 4.0 | 3 | 0 | 0 | 8 | 0 |
| 3.0 | 5 | frozen | 453 | 46 | 10.2% [7.4%, 13.2%] | 407 | 1.0 / 3.8 | 3 | 0 | 0 | 8 | 0 |
| 3.0 | 10 | evolving | 452 | 82 | 18.1% [14.8%, 21.7%] | 370 | 4.0 / 6.8 | 6 | 0 | 1 | 13 | 0 |
| 3.0 | 10 | frozen | 452 | 69 | 15.3% [12.2%, 18.6%] | 383 | 4.0 / 7.0 | 6 | 0 | 1 | 13 | 0 |
| 3.0 | 15 | evolving | 450 | 103 | 22.9% [19.3%, 26.7%] | 347 | 5.0 / 9.0 | 7 | 0 | 3 | 19 | 0 |
| 3.0 | 15 | frozen | 450 | 84 | 18.7% [15.3%, 22.2%] | 366 | 4.5 / 8.2 | 7 | 0 | 3 | 19 | 0 |
| 3.0 | 20 | evolving | 448 | 129 | 28.8% [25.1%, 32.6%] | 319 | 7.0 / 13.0 | 10 | 0 | 5 | 27 | 0 |
| 3.0 | 20 | frozen | 448 | 102 | 22.8% [19.0%, 26.7%] | 346 | 7.0 / 12.8 | 10 | 0 | 5 | 27 | 0 |
| 3.0 | 50 | evolving | 436 | 214 | 49.1% [43.9%, 54.0%] | 222 | 16.0 / 30.0 | 24 | 0 | 17 | 45 | 0 |
| 3.0 | 50 | frozen | 436 | 169 | 38.8% [34.1%, 43.6%] | 267 | 16.0 / 31.0 | 24 | 0 | 17 | 45 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 2,636 | 16.36 [15.17, 17.60] / 8.25 | 13.81 [12.98, 14.72] / 7.25 | 13.81 [12.98, 14.72] / 7.25 | 16.36 [15.17, 17.60] / 8.25 | -1.06 [-2.05, -0.14] | 1.06 [0.14, 2.05] | 50.1% [48.3%, 52.0%] | 50.1% [48.3%, 52.0%] | 49.2% [47.2%, 51.1%] | 30 | 1,070 / 273 | 1 | adequate descriptive support | 942 / 1,060 / 561 / 73 | 0 |
| 2.0 | 10 | 2,635 | 22.69 [21.02, 24.53] / 11.50 | 18.82 [17.72, 20.06] / 10.25 | 18.82 [17.72, 20.06] / 10.25 | 22.69 [21.02, 24.53] / 11.50 | -1.85 [-3.18, -0.58] | 1.85 [0.58, 3.18] | 49.9% [48.1%, 51.8%] | 49.9% [48.1%, 51.8%] | 49.4% [47.4%, 51.4%] | 17 | 1,070 / 273 | 2 | adequate descriptive support | 1,103 / 1,202 / 256 / 74 | 0 |
| 2.0 | 15 | 2,633 | 27.12 [25.03, 29.40] / 14.00 | 22.67 [21.27, 24.23] / 12.50 | 22.67 [21.27, 24.23] / 12.50 | 27.12 [25.03, 29.40] / 14.00 | -1.17 [-2.74, 0.30] | 1.17 [-0.30, 2.74] | 51.0% [49.1%, 52.8%] | 51.0% [49.1%, 52.8%] | 50.5% [48.6%, 52.4%] | 14 | 1,070 / 273 | 4 | adequate descriptive support | 1,161 / 1,252 / 146 / 74 | 0 |
| 2.0 | 20 | 2,630 | 30.67 [28.37, 33.10] / 16.00 | 26.30 [24.58, 28.39] / 14.50 | 26.30 [24.58, 28.39] / 14.50 | 30.67 [28.37, 33.10] / 16.00 | -0.60 [-2.38, 1.17] | 0.60 [-1.17, 2.38] | 49.9% [47.9%, 51.8%] | 49.9% [47.9%, 51.8%] | 49.0% [47.2%, 51.0%] | 9 | 1,070 / 273 | 7 | adequate descriptive support | 1,188 / 1,279 / 89 / 74 | 0 |
| 2.0 | 50 | 2,602 | 47.82 [44.37, 51.41] / 25.75 | 40.93 [38.26, 43.85] / 24.50 | 40.93 [38.26, 43.85] / 24.50 | 47.82 [44.37, 51.41] / 25.75 | -1.16 [-4.28, 1.69] | 1.16 [-1.69, 4.28] | 52.0% [49.9%, 54.0%] | 52.0% [49.9%, 54.0%] | 50.6% [48.8%, 52.6%] | 13 | 1,066 / 273 | 35 | adequate descriptive support | 1,219 / 1,302 / 8 / 73 | 0 |
| 2.5 | 5 | 1,275 | 17.23 [15.62, 19.03] / 8.25 | 14.69 [13.52, 15.95] / 7.50 | 14.69 [13.52, 15.95] / 7.50 | 17.23 [15.62, 19.03] / 8.25 | -0.65 [-2.18, 0.81] | 0.65 [-0.81, 2.18] | 50.7% [48.2%, 53.2%] | 50.7% [48.2%, 53.2%] | 48.9% [46.3%, 51.7%] | 12 | 797 / 264 | 0 | adequate descriptive support | 428 / 492 / 309 / 46 | 0 |
| 2.5 | 10 | 1,275 | 23.25 [21.02, 25.61] / 11.75 | 20.02 [18.44, 21.71] / 10.75 | 20.02 [18.44, 21.71] / 10.75 | 23.25 [21.02, 25.61] / 11.75 | -0.41 [-2.19, 1.40] | 0.41 [-1.40, 2.19] | 50.0% [47.1%, 52.7%] | 50.0% [47.1%, 52.7%] | 50.2% [47.5%, 52.9%] | 10 | 797 / 264 | 0 | adequate descriptive support | 514 / 569 / 145 / 47 | 0 |
| 2.5 | 15 | 1,274 | 27.62 [25.10, 30.30] / 14.50 | 24.13 [22.17, 26.26] / 12.62 | 24.13 [22.17, 26.26] / 12.62 | 27.62 [25.10, 30.30] / 14.50 | 0.33 [-1.77, 2.54] | -0.33 [-2.54, 1.77] | 51.2% [48.6%, 53.7%] | 51.2% [48.6%, 53.7%] | 52.1% [49.5%, 54.6%] | 5 | 797 / 264 | 1 | adequate descriptive support | 548 / 600 / 79 / 47 | 0 |
| 2.5 | 20 | 1,272 | 31.18 [28.46, 34.11] / 16.75 | 28.09 [25.54, 31.31] / 14.88 | 28.09 [25.54, 31.31] / 14.88 | 31.18 [28.46, 34.11] / 16.75 | 0.94 [-1.78, 3.83] | -0.94 [-3.83, 1.78] | 49.7% [46.8%, 52.5%] | 49.7% [46.8%, 52.5%] | 47.5% [44.8%, 50.4%] | 4 | 796 / 264 | 3 | adequate descriptive support | 564 / 611 / 50 / 47 | 0 |
| 2.5 | 50 | 1,258 | 49.81 [45.62, 54.24] / 27.25 | 43.67 [39.80, 47.96] / 24.62 | 43.67 [39.80, 47.96] / 24.62 | 49.81 [45.62, 54.24] / 27.25 | -0.96 [-5.22, 3.05] | 0.96 [-3.05, 5.22] | 51.8% [49.0%, 54.5%] | 51.8% [49.0%, 54.5%] | 51.3% [48.6%, 53.9%] | 5 | 792 / 264 | 17 | adequate descriptive support | 584 / 624 / 4 / 46 | 0 |
| 3.0 | 5 | 381 | 16.87 [14.38, 19.73] / 8.25 | 17.15 [14.91, 19.80] / 8.25 | 17.15 [14.91, 19.80] / 8.25 | 16.87 [14.38, 19.73] / 8.25 | 1.76 [-1.19, 4.70] | -1.76 [-4.70, 1.19] | 52.8% [47.7%, 58.1%] | 52.8% [47.7%, 58.1%] | 47.8% [43.2%, 52.4%] | 4 | 328 / 208 | 0 | adequate descriptive support | 129 / 124 / 105 / 23 | 0 |
| 3.0 | 10 | 381 | 22.71 [19.71, 26.10] / 12.00 | 23.19 [19.87, 27.26] / 11.00 | 23.19 [19.87, 27.26] / 11.00 | 22.71 [19.71, 26.10] / 12.00 | 2.28 [-1.37, 6.15] | -2.28 [-6.15, 1.37] | 48.8% [44.0%, 53.6%] | 48.8% [44.0%, 53.6%] | 48.8% [44.0%, 54.0%] | 3 | 328 / 208 | 0 | adequate descriptive support | 154 / 148 / 56 / 23 | 0 |
| 3.0 | 15 | 381 | 27.24 [23.80, 31.10] / 14.75 | 27.88 [23.44, 33.30] / 12.50 | 27.88 [23.44, 33.30] / 12.50 | 27.24 [23.80, 31.10] / 14.75 | 2.35 [-2.14, 7.22] | -2.35 [-7.22, 2.14] | 48.6% [43.7%, 53.5%] | 48.6% [43.7%, 53.5%] | 48.6% [43.5%, 53.5%] | 0 | 328 / 208 | 0 | adequate descriptive support | 167 / 157 / 34 / 23 | 0 |
| 3.0 | 20 | 381 | 31.12 [27.15, 35.31] / 17.00 | 33.57 [27.07, 43.20] / 15.25 | 33.57 [27.07, 43.20] / 15.25 | 31.12 [27.15, 35.31] / 17.00 | 3.92 [-2.30, 11.57] | -3.92 [-11.57, 2.30] | 46.2% [40.8%, 51.6%] | 46.2% [40.8%, 51.6%] | 49.1% [44.1%, 54.0%] | 2 | 328 / 208 | 0 | adequate descriptive support | 176 / 160 / 22 / 23 | 0 |
| 3.0 | 50 | 379 | 51.82 [45.20, 58.88] / 28.75 | 48.34 [40.04, 59.90] / 24.75 | 48.34 [40.04, 59.90] / 24.75 | 51.82 [45.20, 58.88] / 28.75 | -0.92 [-8.49, 6.40] | 0.92 [-6.40, 8.49] | 49.1% [44.3%, 54.0%] | 49.1% [44.3%, 54.0%] | 50.1% [45.1%, 55.0%] | 2 | 327 / 208 | 2 | adequate descriptive support | 184 / 170 / 2 / 23 | 0 |

### Lower departure / arrival: continuation and bounce short; fade and through long

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 3,065 | 15.21 [14.17, 16.38] / 8.00 | 17.01 [15.76, 18.31] / 9.00 | 17.01 [15.76, 18.31] / 9.00 | 15.21 [14.17, 16.38] / 8.00 | 0.40 [-0.46, 1.30] | -0.40 [-1.30, 0.46] | 47.8% [46.1%, 49.5%] | 51.2% [49.5%, 52.9%] | 48.5% [46.6%, 50.3%] | 30 | 1,098 / 273 | 0 | adequate descriptive support |
| 2.0 | 10 | 3,063 | 20.45 [19.12, 21.94] / 11.25 | 23.35 [21.62, 25.03] / 12.50 | 23.35 [21.62, 25.03] / 12.50 | 20.45 [19.12, 21.94] / 11.25 | 0.67 [-0.54, 1.91] | -0.67 [-1.91, 0.54] | 48.4% [46.7%, 50.1%] | 50.8% [49.1%, 52.5%] | 48.4% [46.7%, 50.1%] | 23 | 1,098 / 273 | 2 | adequate descriptive support |
| 2.0 | 15 | 3,059 | 24.42 [22.83, 26.15] / 13.25 | 27.92 [25.83, 29.97] / 14.50 | 27.92 [25.83, 29.97] / 14.50 | 24.42 [22.83, 26.15] / 13.25 | 0.78 [-0.56, 2.23] | -0.78 [-2.23, 0.56] | 48.3% [46.4%, 49.9%] | 51.3% [49.6%, 53.1%] | 48.7% [47.0%, 50.3%] | 14 | 1,098 / 273 | 6 | adequate descriptive support |
| 2.0 | 20 | 3,055 | 27.36 [25.65, 29.24] / 15.75 | 31.35 [29.04, 33.62] / 16.25 | 31.35 [29.04, 33.62] / 16.25 | 27.36 [25.65, 29.24] / 15.75 | 1.01 [-0.42, 2.54] | -1.01 [-2.54, 0.42] | 46.6% [44.8%, 48.3%] | 52.9% [51.2%, 54.8%] | 50.0% [48.2%, 51.8%] | 14 | 1,097 / 273 | 10 | adequate descriptive support |
| 2.0 | 50 | 3,011 | 42.04 [39.35, 44.81] / 24.50 | 45.83 [42.55, 49.12] / 25.00 | 45.83 [42.55, 49.12] / 25.00 | 42.04 [39.35, 44.81] / 24.50 | 0.00 [-2.18, 2.31] | -0.00 [-2.31, 2.18] | 47.1% [45.1%, 49.2%] | 52.6% [50.5%, 54.6%] | 49.5% [47.7%, 51.4%] | 9 | 1,094 / 273 | 54 | adequate descriptive support |
| 2.5 | 5 | 1,646 | 15.32 [14.09, 16.73] / 8.50 | 18.12 [16.56, 19.74] / 8.75 | 18.12 [16.56, 19.74] / 8.75 | 15.32 [14.09, 16.73] / 8.50 | 0.84 [-0.51, 2.33] | -0.84 [-2.33, 0.51] | 47.9% [45.4%, 50.3%] | 51.3% [48.9%, 53.7%] | 49.1% [46.6%, 51.4%] | 13 | 892 / 272 | 1 | adequate descriptive support |
| 2.5 | 10 | 1,644 | 20.57 [19.01, 22.27] / 11.25 | 24.76 [22.67, 26.92] / 12.62 | 24.76 [22.67, 26.92] / 12.62 | 20.57 [19.01, 22.27] / 11.25 | 1.14 [-0.61, 3.02] | -1.14 [-3.02, 0.61] | 46.7% [44.2%, 49.0%] | 52.8% [50.5%, 55.3%] | 48.2% [45.8%, 50.8%] | 9 | 892 / 272 | 3 | adequate descriptive support |
| 2.5 | 15 | 1,642 | 24.70 [22.87, 26.73] / 13.75 | 29.53 [27.11, 32.09] / 15.00 | 29.53 [27.11, 32.09] / 15.00 | 24.70 [22.87, 26.73] / 13.75 | 1.16 [-0.94, 3.32] | -1.16 [-3.32, 0.94] | 45.1% [42.6%, 47.4%] | 54.2% [51.9%, 56.6%] | 50.5% [48.1%, 53.1%] | 12 | 892 / 272 | 5 | adequate descriptive support |
| 2.5 | 20 | 1,641 | 27.78 [25.79, 29.94] / 16.00 | 32.88 [30.20, 35.68] / 16.50 | 32.88 [30.20, 35.68] / 16.50 | 27.78 [25.79, 29.94] / 16.00 | 0.59 [-1.59, 2.89] | -0.59 [-2.89, 1.59] | 46.5% [44.2%, 48.9%] | 53.1% [50.6%, 55.4%] | 48.3% [45.9%, 50.8%] | 7 | 892 / 272 | 6 | adequate descriptive support |
| 2.5 | 50 | 1,610 | 42.18 [39.27, 45.30] / 25.75 | 47.18 [43.30, 51.25] / 25.75 | 47.18 [43.30, 51.25] / 25.75 | 42.18 [39.27, 45.30] / 25.75 | 1.12 [-2.37, 4.61] | -1.12 [-4.61, 2.37] | 46.6% [44.0%, 49.3%] | 53.3% [50.6%, 55.9%] | 49.0% [46.6%, 51.4%] | 2 | 885 / 272 | 37 | adequate descriptive support |
| 3.0 | 5 | 525 | 17.62 [15.72, 19.62] / 9.75 | 20.22 [17.44, 23.25] / 10.00 | 20.22 [17.44, 23.25] / 10.00 | 17.62 [15.72, 19.62] / 9.75 | 0.26 [-2.43, 3.14] | -0.26 [-3.14, 2.43] | 46.7% [41.8%, 51.4%] | 52.8% [48.0%, 57.6%] | 50.9% [46.6%, 55.5%] | 3 | 413 / 219 | 1 | adequate descriptive support |
| 3.0 | 10 | 524 | 23.36 [20.92, 25.93] / 13.25 | 27.31 [23.70, 31.23] / 14.75 | 27.31 [23.70, 31.23] / 14.75 | 23.36 [20.92, 25.93] / 13.25 | -0.08 [-3.61, 3.62] | 0.08 [-3.62, 3.61] | 45.8% [41.4%, 50.2%] | 53.4% [48.8%, 57.6%] | 51.1% [46.3%, 56.2%] | 4 | 412 / 219 | 2 | adequate descriptive support |
| 3.0 | 15 | 523 | 27.98 [24.94, 31.13] / 15.75 | 31.44 [27.57, 35.58] / 16.75 | 31.44 [27.57, 35.58] / 16.75 | 27.98 [24.94, 31.13] / 15.75 | -0.90 [-4.67, 2.87] | 0.90 [-2.87, 4.67] | 43.6% [39.5%, 48.0%] | 55.4% [51.2%, 59.4%] | 52.4% [48.1%, 56.7%] | 5 | 412 / 219 | 3 | adequate descriptive support |
| 3.0 | 20 | 520 | 31.56 [27.97, 35.28] / 18.62 | 34.19 [30.01, 38.64] / 18.38 | 34.19 [30.01, 38.64] / 18.38 | 31.56 [27.97, 35.28] / 18.62 | -2.49 [-6.88, 2.26] | 2.49 [-2.26, 6.88] | 46.0% [41.6%, 50.5%] | 53.5% [49.0%, 58.0%] | 49.8% [45.6%, 53.8%] | 3 | 410 / 219 | 6 | adequate descriptive support |
| 3.0 | 50 | 503 | 43.90 [39.28, 48.68] / 27.75 | 47.92 [42.16, 54.31] / 25.50 | 47.92 [42.16, 54.31] / 25.50 | 43.90 [39.28, 48.68] / 27.75 | 1.74 [-3.78, 7.68] | -1.74 [-7.68, 3.78] | 46.1% [41.4%, 50.7%] | 53.5% [48.9%, 58.2%] | 49.3% [45.2%, 53.5%] | 2 | 401 / 217 | 23 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 3,065 | 451 | 14.7% [13.5%, 16.0%] | 2,614 | 3.0 / 4.0 | 12 | 1 | 0 | 67 | 0 |
| 2.0 | 5 | frozen | 3,065 | 384 | 12.5% [11.4%, 13.8%] | 2,681 | 3.0 / 4.0 | 12 | 1 | 0 | 67 | 0 |
| 2.0 | 10 | evolving | 3,063 | 753 | 24.6% [23.2%, 26.0%] | 2,310 | 5.0 / 7.0 | 42 | 1 | 2 | 139 | 0 |
| 2.0 | 10 | frozen | 3,063 | 614 | 20.0% [18.8%, 21.4%] | 2,449 | 4.0 / 7.0 | 42 | 1 | 2 | 139 | 0 |
| 2.0 | 15 | evolving | 3,059 | 1,023 | 33.4% [31.9%, 35.0%] | 2,036 | 7.0 / 11.0 | 72 | 1 | 6 | 228 | 0 |
| 2.0 | 15 | frozen | 3,059 | 795 | 26.0% [24.5%, 27.6%] | 2,264 | 6.0 / 10.0 | 72 | 1 | 6 | 228 | 0 |
| 2.0 | 20 | evolving | 3,055 | 1,206 | 39.5% [37.9%, 41.2%] | 1,849 | 8.0 / 13.0 | 97 | 1 | 10 | 261 | 0 |
| 2.0 | 20 | frozen | 3,055 | 945 | 30.9% [29.4%, 32.6%] | 2,110 | 7.0 / 13.0 | 97 | 1 | 10 | 261 | 0 |
| 2.0 | 50 | evolving | 3,011 | 1,866 | 62.0% [60.3%, 63.6%] | 1,145 | 14.0 / 26.0 | 223 | 1 | 54 | 385 | 0 |
| 2.0 | 50 | frozen | 3,011 | 1,481 | 49.2% [47.3%, 51.1%] | 1,530 | 14.0 / 27.0 | 223 | 1 | 54 | 385 | 0 |
| 2.5 | 5 | evolving | 1,646 | 188 | 11.4% [9.9%, 13.0%] | 1,458 | 3.0 / 4.0 | 3 | 0 | 1 | 29 | 0 |
| 2.5 | 5 | frozen | 1,646 | 159 | 9.7% [8.2%, 11.1%] | 1,487 | 2.0 / 4.0 | 3 | 0 | 1 | 29 | 0 |
| 2.5 | 10 | evolving | 1,644 | 313 | 19.0% [17.2%, 20.8%] | 1,331 | 4.0 / 7.0 | 17 | 0 | 3 | 62 | 0 |
| 2.5 | 10 | frozen | 1,644 | 251 | 15.3% [13.6%, 16.9%] | 1,393 | 4.0 / 7.0 | 17 | 0 | 3 | 62 | 0 |
| 2.5 | 15 | evolving | 1,642 | 435 | 26.5% [24.4%, 28.5%] | 1,207 | 7.0 / 11.0 | 29 | 0 | 5 | 108 | 0 |
| 2.5 | 15 | frozen | 1,642 | 327 | 19.9% [18.0%, 21.8%] | 1,315 | 6.0 / 10.0 | 29 | 0 | 5 | 108 | 0 |
| 2.5 | 20 | evolving | 1,641 | 530 | 32.3% [30.1%, 34.5%] | 1,111 | 8.0 / 13.0 | 43 | 0 | 6 | 135 | 0 |
| 2.5 | 20 | frozen | 1,641 | 395 | 24.1% [22.1%, 26.1%] | 1,246 | 7.0 / 13.0 | 43 | 0 | 6 | 135 | 0 |
| 2.5 | 50 | evolving | 1,610 | 886 | 55.0% [52.7%, 57.4%] | 724 | 16.0 / 29.0 | 107 | 0 | 37 | 212 | 0 |
| 2.5 | 50 | frozen | 1,610 | 674 | 41.9% [39.5%, 44.4%] | 936 | 16.0 / 29.0 | 107 | 0 | 37 | 212 | 0 |
| 3.0 | 5 | evolving | 525 | 50 | 9.5% [7.3%, 12.0%] | 475 | 2.0 / 3.0 | 1 | 0 | 1 | 10 | 0 |
| 3.0 | 5 | frozen | 525 | 40 | 7.6% [5.6%, 9.8%] | 485 | 2.0 / 3.0 | 1 | 0 | 1 | 10 | 0 |
| 3.0 | 10 | evolving | 524 | 83 | 15.8% [13.0%, 18.8%] | 441 | 5.0 / 7.0 | 8 | 0 | 2 | 17 | 0 |
| 3.0 | 10 | frozen | 524 | 66 | 12.6% [10.0%, 15.2%] | 458 | 3.0 / 7.0 | 8 | 0 | 2 | 17 | 0 |
| 3.0 | 15 | evolving | 523 | 111 | 21.2% [18.1%, 24.5%] | 412 | 6.0 / 10.5 | 11 | 0 | 3 | 26 | 0 |
| 3.0 | 15 | frozen | 523 | 85 | 16.3% [13.6%, 19.1%] | 438 | 6.0 / 10.0 | 11 | 0 | 3 | 26 | 0 |
| 3.0 | 20 | evolving | 520 | 139 | 26.7% [23.4%, 30.3%] | 381 | 8.0 / 14.0 | 13 | 0 | 6 | 39 | 0 |
| 3.0 | 20 | frozen | 520 | 100 | 19.2% [16.4%, 22.2%] | 420 | 7.0 / 13.0 | 13 | 0 | 6 | 39 | 0 |
| 3.0 | 50 | evolving | 503 | 239 | 47.5% [43.3%, 51.8%] | 264 | 17.0 / 30.0 | 28 | 0 | 23 | 60 | 0 |
| 3.0 | 50 | frozen | 503 | 179 | 35.6% [31.6%, 39.9%] | 324 | 17.0 / 32.0 | 28 | 0 | 23 | 60 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 2,791 | 13.89 [12.85, 15.00] / 7.50 | 13.87 [12.85, 14.98] / 7.25 | 13.87 [12.85, 14.98] / 7.25 | 13.89 [12.85, 15.00] / 7.50 | 0.13 [-0.69, 0.95] | -0.13 [-0.95, 0.69] | 49.3% [47.4%, 51.2%] | 49.7% [47.7%, 51.5%] | 48.4% [46.5%, 50.1%] | 30 | 1,071 / 273 | 2 | adequate descriptive support | 984 / 973 / 755 / 79 | 0 |
| 2.0 | 10 | 2,791 | 19.22 [17.85, 20.65] / 10.50 | 19.42 [17.96, 20.98] / 10.00 | 19.42 [17.96, 20.98] / 10.00 | 19.22 [17.85, 20.65] / 10.50 | 0.09 [-1.12, 1.28] | -0.09 [-1.28, 1.12] | 48.7% [46.7%, 50.5%] | 50.7% [48.8%, 52.7%] | 47.9% [46.0%, 49.9%] | 17 | 1,071 / 273 | 2 | adequate descriptive support | 1,165 / 1,146 / 400 / 80 | 0 |
| 2.0 | 15 | 2,788 | 23.21 [21.61, 24.89] / 13.00 | 23.60 [21.80, 25.49] / 12.50 | 23.60 [21.80, 25.49] / 12.50 | 23.21 [21.61, 24.89] / 13.00 | -0.23 [-1.68, 1.13] | 0.23 [-1.13, 1.68] | 47.6% [45.8%, 49.5%] | 51.7% [49.8%, 53.6%] | 49.5% [47.8%, 51.3%] | 19 | 1,071 / 273 | 5 | adequate descriptive support | 1,253 / 1,219 / 235 / 81 | 0 |
| 2.0 | 20 | 2,785 | 26.64 [24.77, 28.54] / 15.25 | 26.95 [24.94, 29.01] / 14.25 | 26.95 [24.94, 29.01] / 14.25 | 26.64 [24.77, 28.54] / 15.25 | -0.92 [-2.35, 0.58] | 0.92 [-0.58, 2.35] | 47.3% [45.4%, 49.4%] | 51.8% [49.8%, 53.8%] | 49.4% [47.4%, 51.4%] | 23 | 1,071 / 273 | 8 | adequate descriptive support | 1,287 / 1,264 / 154 / 80 | 0 |
| 2.0 | 50 | 2,731 | 41.42 [38.64, 44.35] / 24.50 | 41.77 [38.77, 44.71] / 23.75 | 41.77 [38.77, 44.71] / 23.75 | 41.42 [38.64, 44.35] / 24.50 | -2.22 [-4.52, 0.04] | 2.22 [-0.04, 4.52] | 46.9% [44.9%, 48.9%] | 52.5% [50.6%, 54.6%] | 49.8% [47.8%, 51.9%] | 14 | 1,064 / 273 | 62 | adequate descriptive support | 1,323 / 1,302 / 26 / 80 | 0 |
| 2.5 | 5 | 1,477 | 14.68 [13.41, 16.08] / 7.75 | 14.02 [12.75, 15.28] / 7.25 | 14.02 [12.75, 15.28] / 7.25 | 14.68 [13.41, 16.08] / 7.75 | -0.31 [-1.59, 0.98] | 0.31 [-0.98, 1.59] | 49.3% [46.7%, 51.8%] | 49.9% [47.4%, 52.5%] | 47.3% [44.8%, 49.7%] | 12 | 840 / 271 | 1 | adequate descriptive support | 474 / 508 / 455 / 40 | 0 |
| 2.5 | 10 | 1,477 | 19.83 [18.30, 21.57] / 11.00 | 20.03 [18.22, 21.95] / 10.25 | 20.03 [18.22, 21.95] / 10.25 | 19.83 [18.30, 21.57] / 11.00 | 0.70 [-1.03, 2.51] | -0.70 [-2.51, 1.03] | 49.7% [46.8%, 52.4%] | 49.8% [47.1%, 52.7%] | 49.4% [46.7%, 52.1%] | 7 | 840 / 271 | 1 | adequate descriptive support | 583 / 606 / 248 / 40 | 0 |
| 2.5 | 15 | 1,475 | 23.80 [22.04, 25.70] / 13.75 | 24.17 [21.99, 26.52] / 13.00 | 24.17 [21.99, 26.52] / 13.00 | 23.80 [22.04, 25.70] / 13.75 | 0.00 [-2.04, 2.03] | -0.00 [-2.03, 2.04] | 48.3% [45.5%, 51.1%] | 51.4% [48.6%, 54.1%] | 49.7% [47.1%, 52.2%] | 5 | 840 / 271 | 3 | adequate descriptive support | 638 / 645 / 151 / 41 | 0 |
| 2.5 | 20 | 1,472 | 27.28 [25.26, 29.43] / 16.00 | 27.66 [25.20, 30.22] / 14.88 | 27.66 [25.20, 30.22] / 14.88 | 27.28 [25.26, 29.43] / 16.00 | -0.80 [-3.01, 1.52] | 0.80 [-1.52, 3.01] | 47.4% [44.5%, 50.2%] | 51.8% [48.8%, 54.6%] | 49.9% [47.2%, 52.7%] | 13 | 840 / 271 | 6 | adequate descriptive support | 664 / 675 / 93 / 40 | 0 |
| 2.5 | 50 | 1,441 | 42.36 [39.42, 45.50] / 25.25 | 42.93 [39.49, 46.54] / 24.50 | 42.93 [39.49, 46.54] / 24.50 | 42.36 [39.42, 45.50] / 25.25 | -1.95 [-5.17, 1.50] | 1.95 [-1.50, 5.17] | 46.1% [43.5%, 48.8%] | 53.4% [50.8%, 56.1%] | 49.6% [46.9%, 52.3%] | 6 | 825 / 270 | 37 | adequate descriptive support | 688 / 697 / 16 / 40 | 0 |
| 3.0 | 5 | 462 | 16.61 [14.30, 19.15] / 7.75 | 15.82 [13.68, 17.81] / 7.75 | 15.82 [13.68, 17.81] / 7.75 | 16.61 [14.30, 19.15] / 7.75 | -0.60 [-3.04, 1.83] | 0.60 [-1.83, 3.04] | 51.9% [47.7%, 56.2%] | 47.2% [43.0%, 51.4%] | 47.8% [42.9%, 52.6%] | 4 | 374 / 216 | 0 | adequate descriptive support | 145 / 157 / 144 / 16 | 0 |
| 3.0 | 10 | 462 | 22.80 [19.82, 26.12] / 11.00 | 22.79 [19.89, 25.83] / 11.88 | 22.79 [19.89, 25.83] / 11.88 | 22.80 [19.82, 26.12] / 11.00 | -0.10 [-3.40, 3.11] | 0.10 [-3.11, 3.40] | 49.1% [44.6%, 53.4%] | 49.8% [45.5%, 54.3%] | 50.2% [45.6%, 55.1%] | 5 | 374 / 216 | 0 | adequate descriptive support | 175 / 185 / 86 / 16 | 0 |
| 3.0 | 15 | 462 | 26.91 [23.52, 30.55] / 13.62 | 27.25 [23.79, 30.83] / 15.00 | 27.25 [23.79, 30.83] / 15.00 | 26.91 [23.52, 30.55] / 13.62 | 0.90 [-2.89, 4.80] | -0.90 [-4.80, 2.89] | 49.1% [44.5%, 53.8%] | 50.2% [45.5%, 54.8%] | 48.7% [44.2%, 53.4%] | 3 | 374 / 216 | 0 | adequate descriptive support | 190 / 199 / 57 / 16 | 0 |
| 3.0 | 20 | 461 | 30.28 [26.48, 34.30] / 16.50 | 31.30 [27.24, 35.63] / 16.75 | 31.30 [27.24, 35.63] / 16.75 | 30.28 [26.48, 34.30] / 16.50 | 0.46 [-3.86, 4.91] | -0.46 [-4.91, 3.86] | 48.4% [43.8%, 53.0%] | 50.8% [46.2%, 55.4%] | 49.7% [44.6%, 54.9%] | 4 | 374 / 216 | 1 | adequate descriptive support | 200 / 212 / 33 / 16 | 0 |
| 3.0 | 50 | 450 | 45.88 [40.66, 51.51] / 28.50 | 48.15 [42.52, 54.12] / 27.75 | 48.15 [42.52, 54.12] / 27.75 | 45.88 [40.66, 51.51] / 28.50 | -0.53 [-7.15, 6.27] | 0.53 [-6.27, 7.15] | 46.4% [41.6%, 51.2%] | 53.3% [48.5%, 58.1%] | 48.9% [44.0%, 54.0%] | 1 | 365 / 214 | 12 | adequate descriptive support | 206 / 224 / 4 / 16 | 0 |

### Common cohort, distribution and year diagnostics

The horizon curves use the identical complete-50 cohort. Distribution quantiles and year diagnostics use each horizon’s eligible cohort. Year 2026 is partial. These diagnostics are descriptive on previously inspected history.

![NQ Globex return](figures/globex-NQ-return.svg)

![NQ Globex excursion](figures/globex-NQ-excursion.svg)

![NQ Globex endpoint](figures/globex-NQ-endpoint.svg)

![NQ Globex mae-mfe-distribution](figures/globex-NQ-mae-mfe-distribution.svg)

![NQ Globex terminal-distribution](figures/globex-NQ-terminal-distribution.svg)

![NQ Globex year-stability](figures/globex-NQ-year-stability.svg)

### Sensitivity and chronological periods at 10 candles

| Module | Scope | n | Days / weeks | Directional Δ [CI] | Return or bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- |
| departure | all | 6,060 | 1,176 / 273 | 0.69 [-0.13, 1.53] | 24.2% [23.0%, 25.4%] |
| departure | common_50 | 5,945 | 1,176 / 273 | 0.73 [-0.07, 1.53] | 24.6% [23.4%, 25.8%] |
| departure | age_ge30 | 5,017 | 1,174 / 273 | 0.97 [-0.02, 1.99] | 15.7% [14.6%, 16.8%] |
| departure | through_2023 | 3,169 | 568 / 131 | 0.09 [-0.84, 0.97] | 24.6% [22.9%, 26.3%] |
| departure | year_2024_period | 1,069 | 213 / 53 | 0.97 [-0.37, 2.44] | 24.2% [21.6%, 26.9%] |
| departure | years_2025_2026 | 1,822 | 395 / 90 | 1.55 [-0.50, 3.67] | 23.5% [21.6%, 25.3%] |
| touch | all | 5,426 | 1,173 / 273 | -0.85 [-1.82, 0.05] | 49.3% [48.0%, 50.6%] |
| touch | common_50 | 5,333 | 1,173 / 273 | -0.75 [-1.67, 0.13] | 49.3% [48.0%, 50.6%] |
| touch | age_ge30 | 4,384 | 1,162 / 273 | -1.01 [-2.16, 0.07] | 49.4% [47.9%, 50.8%] |
| touch | through_2023 | 2,837 | 566 / 131 | -0.31 [-1.27, 0.63] | 50.4% [48.7%, 52.2%] |
| touch | year_2024_period | 962 | 213 / 53 | -1.03 [-2.91, 0.77] | 47.5% [43.8%, 51.0%] |
| touch | years_2025_2026 | 1,627 | 394 / 90 | -1.68 [-4.17, 0.63] | 48.3% [45.9%, 50.7%] |

### Deterministic source-path examples

Examples are the earliest stable ID in each prespecified class. They illustrate mechanisms and exclusions, not representative trade quality. The source table includes reference available_at and known sigma for every minute; charts plot raw one-minute high/low and references. Source minute open time relative to entry is shown; contacts have interval resolution. Lines join minute OHLC observations for display and do not imply intraminute order or trades through gaps. The 2-sigma envelope is plotted; 2.5/3-sigma references are retained in the example-path table.

return: NQ-globex-2021-06-29-P0265-K2-H10; lower side. Signal/confirmation 2021-06-29 02:52:00-04:00; entry 2021-06-29 02:52:00-04:00; deadline 2021-06-29 03:12:00-04:00 (New York time). Frozen sigma 5.52 points; signal VWAP 14,484.16. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-globex-2021-06-29-P0265-K2-H10](figures/example-globex-NQ-return.svg)

non_return: NQ-globex-2021-06-28-P0007-K2-H10; upper side. Signal/confirmation 2021-06-27 18:16:00-04:00; entry 2021-06-27 18:16:00-04:00; deadline 2021-06-27 18:36:00-04:00 (New York time). Frozen sigma 2.10 points; signal VWAP 14,343.98. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-globex-2021-06-28-P0007-K2-H10](figures/example-globex-NQ-non_return.svg)

bounce: NQ-globex-2021-06-28-P0007-T-H10; upper side. Signal/confirmation 2021-06-27 19:38:00-04:00; entry 2021-06-27 19:38:00-04:00; deadline 2021-06-27 19:58:00-04:00 (New York time). Frozen sigma 6.85 points; signal VWAP 14,352.79. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-globex-2021-06-28-P0007-T-H10](figures/example-globex-NQ-bounce.svg)

through: NQ-globex-2021-06-28-P0102-T-H10; lower side. Signal/confirmation 2021-06-27 22:38:00-04:00; entry 2021-06-27 22:38:00-04:00; deadline 2021-06-27 22:58:00-04:00 (New York time). Frozen sigma 7.63 points; signal VWAP 14,347.08. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-globex-2021-06-28-P0102-T-H10](figures/example-globex-NQ-through.svg)

ambiguity: NQ-globex-2021-06-29-P0463-T-H10; upper side. Signal/confirmation 2021-06-29 09:32:00-04:00; entry 2021-06-29 09:32:00-04:00; deadline 2021-06-29 09:52:00-04:00 (New York time). Frozen sigma 7.92 points; signal VWAP 14,488.43. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![NQ-globex-2021-06-29-P0463-T-H10](figures/example-globex-NQ-ambiguity.svg)

exclusion: NQ-globex-2021-07-12-P0662-K2-H50; upper side. Signal/confirmation 2021-07-12 16:06:00-04:00; entry 2021-07-12 16:06:00-04:00; deadline 2021-07-12 17:46:00-04:00 (New York time). Frozen sigma 19.23 points; signal VWAP 14,840.54. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: session_boundary.

![NQ-globex-2021-07-12-P0662-K2-H50](figures/example-globex-NQ-exclusion.svg)

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
| 2.0 | 5 | 1,922 | 1.69 [1.52, 1.88] / 0.90 | 2.17 [1.94, 2.43] / 0.90 | 2.17 [1.94, 2.43] / 0.90 | 1.69 [1.52, 1.88] / 0.90 | 0.32 [0.18, 0.48] | -0.32 [-0.48, -0.18] | 49.4% [47.4%, 51.4%] | 49.4% [47.4%, 51.4%] | 45.4% [43.1%, 47.7%] | 57 | 758 / 348 | 0 | adequate descriptive support |
| 2.0 | 10 | 1,920 | 2.34 [2.10, 2.60] / 1.20 | 2.91 [2.59, 3.26] / 1.30 | 2.91 [2.59, 3.26] / 1.30 | 2.34 [2.10, 2.60] / 1.20 | 0.30 [0.10, 0.49] | -0.30 [-0.49, -0.10] | 47.7% [45.5%, 49.8%] | 47.7% [45.5%, 49.8%] | 45.9% [43.8%, 48.2%] | 61 | 758 / 348 | 2 | adequate descriptive support |
| 2.0 | 15 | 1,918 | 2.88 [2.58, 3.19] / 1.50 | 3.45 [3.09, 3.84] / 1.60 | 3.45 [3.09, 3.84] / 1.60 | 2.88 [2.58, 3.19] / 1.50 | 0.36 [0.14, 0.59] | -0.36 [-0.59, -0.14] | 49.0% [46.7%, 51.3%] | 49.0% [46.7%, 51.3%] | 45.3% [42.9%, 47.7%] | 46 | 758 / 348 | 4 | adequate descriptive support |
| 2.0 | 20 | 1,916 | 3.35 [3.01, 3.72] / 1.70 | 3.96 [3.55, 4.39] / 1.80 | 3.96 [3.55, 4.39] / 1.80 | 3.35 [3.01, 3.72] / 1.70 | 0.39 [0.12, 0.67] | -0.39 [-0.67, -0.12] | 50.4% [48.2%, 52.4%] | 50.4% [48.2%, 52.4%] | 46.0% [43.8%, 48.3%] | 34 | 757 / 348 | 6 | adequate descriptive support |
| 2.0 | 50 | 1,908 | 5.28 [4.69, 5.98] / 2.70 | 6.06 [5.42, 6.75] / 3.00 | 6.06 [5.42, 6.75] / 3.00 | 5.28 [4.69, 5.98] / 2.70 | 0.92 [0.45, 1.41] | -0.92 [-1.41, -0.45] | 53.5% [51.0%, 55.9%] | 53.5% [51.0%, 55.9%] | 44.6% [42.3%, 47.1%] | 21 | 755 / 348 | 14 | adequate descriptive support |
| 2.5 | 5 | 851 | 1.91 [1.66, 2.20] / 1.00 | 2.36 [2.07, 2.67] / 1.00 | 2.36 [2.07, 2.67] / 1.00 | 1.91 [1.66, 2.20] / 1.00 | 0.29 [-0.05, 0.59] | -0.29 [-0.59, 0.05] | 49.7% [46.4%, 52.8%] | 49.7% [46.4%, 52.8%] | 46.2% [42.8%, 49.5%] | 23 | 548 / 304 | 0 | adequate descriptive support |
| 2.5 | 10 | 851 | 2.58 [2.25, 2.98] / 1.40 | 3.20 [2.80, 3.63] / 1.50 | 3.20 [2.80, 3.63] / 1.50 | 2.58 [2.25, 2.98] / 1.40 | 0.30 [-0.08, 0.68] | -0.30 [-0.68, 0.08] | 48.2% [44.9%, 51.3%] | 48.2% [44.9%, 51.3%] | 48.4% [45.1%, 51.5%] | 17 | 548 / 304 | 0 | adequate descriptive support |
| 2.5 | 15 | 850 | 3.17 [2.76, 3.68] / 1.70 | 3.85 [3.35, 4.35] / 1.70 | 3.85 [3.35, 4.35] / 1.70 | 3.17 [2.76, 3.68] / 1.70 | 0.43 [-0.09, 0.90] | -0.43 [-0.90, 0.09] | 48.5% [45.2%, 51.9%] | 48.5% [45.2%, 51.9%] | 42.7% [39.5%, 45.8%] | 16 | 548 / 304 | 1 | adequate descriptive support |
| 2.5 | 20 | 848 | 3.71 [3.19, 4.39] / 2.00 | 4.29 [3.72, 4.86] / 2.00 | 4.29 [3.72, 4.86] / 2.00 | 3.71 [3.19, 4.39] / 2.00 | 0.38 [-0.32, 0.97] | -0.38 [-0.97, 0.32] | 47.8% [44.5%, 51.1%] | 47.8% [44.5%, 51.1%] | 46.0% [42.9%, 49.1%] | 13 | 547 / 303 | 3 | adequate descriptive support |
| 2.5 | 50 | 836 | 5.91 [4.96, 7.21] / 2.95 | 6.35 [5.53, 7.24] / 3.10 | 6.35 [5.53, 7.24] / 3.10 | 5.91 [4.96, 7.21] / 2.95 | 0.70 [-0.16, 1.47] | -0.70 [-1.47, 0.16] | 52.8% [49.4%, 55.9%] | 52.8% [49.4%, 55.9%] | 46.5% [43.3%, 49.9%] | 9 | 543 / 302 | 15 | adequate descriptive support |
| 3.0 | 5 | 208 | 2.09 [1.61, 2.60] / 1.00 | 2.58 [2.08, 3.17] / 1.30 | 2.58 [2.08, 3.17] / 1.30 | 2.09 [1.61, 2.60] / 1.00 | 0.34 [-0.20, 0.88] | -0.34 [-0.88, 0.20] | 50.5% [44.0%, 57.6%] | 50.5% [44.0%, 57.6%] | 50.0% [43.7%, 56.4%] | 7 | 180 / 145 | 0 | adequate descriptive support |
| 3.0 | 10 | 208 | 2.89 [2.17, 3.64] / 1.40 | 3.31 [2.72, 4.00] / 1.70 | 3.31 [2.72, 4.00] / 1.70 | 2.89 [2.17, 3.64] / 1.40 | 0.19 [-0.53, 0.93] | -0.19 [-0.93, 0.53] | 50.0% [43.0%, 57.4%] | 50.0% [43.0%, 57.4%] | 43.3% [36.7%, 49.8%] | 5 | 180 / 145 | 0 | adequate descriptive support |
| 3.0 | 15 | 207 | 3.51 [2.62, 4.48] / 1.80 | 3.77 [3.10, 4.52] / 2.00 | 3.77 [3.10, 4.52] / 2.00 | 3.51 [2.62, 4.48] / 1.80 | 0.20 [-0.59, 0.97] | -0.20 [-0.97, 0.59] | 49.8% [42.8%, 56.6%] | 49.8% [42.8%, 56.6%] | 43.0% [35.3%, 50.3%] | 2 | 180 / 145 | 1 | adequate descriptive support |
| 3.0 | 20 | 206 | 4.02 [3.02, 5.18] / 2.05 | 4.34 [3.53, 5.25] / 2.25 | 4.34 [3.53, 5.25] / 2.25 | 4.02 [3.02, 5.18] / 2.05 | 0.22 [-0.85, 1.22] | -0.22 [-1.22, 0.85] | 49.5% [42.2%, 56.5%] | 49.5% [42.2%, 56.5%] | 44.2% [37.2%, 51.4%] | 5 | 179 / 144 | 2 | adequate descriptive support |
| 3.0 | 50 | 201 | 6.48 [4.88, 8.38] / 2.90 | 6.16 [4.86, 7.69] / 3.20 | 6.16 [4.86, 7.69] / 3.20 | 6.48 [4.88, 8.38] / 2.90 | 0.47 [-0.85, 1.88] | -0.47 [-1.88, 0.85] | 50.2% [43.4%, 57.3%] | 50.2% [43.4%, 57.3%] | 53.7% [47.0%, 59.9%] | 1 | 175 / 141 | 7 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,922 | 375 | 19.5% [17.6%, 21.4%] | 1,547 | 2.0 / 4.0 | 1 | 0 | 0 | 56 | 0 |
| 2.0 | 5 | frozen | 1,922 | 319 | 16.6% [14.8%, 18.3%] | 1,603 | 2.0 / 4.0 | 1 | 0 | 0 | 56 | 0 |
| 2.0 | 10 | evolving | 1,920 | 588 | 30.6% [28.4%, 32.9%] | 1,332 | 4.0 / 7.0 | 4 | 0 | 2 | 121 | 0 |
| 2.0 | 10 | frozen | 1,920 | 467 | 24.3% [22.3%, 26.5%] | 1,453 | 4.0 / 6.0 | 4 | 0 | 2 | 121 | 0 |
| 2.0 | 15 | evolving | 1,918 | 719 | 37.5% [35.3%, 39.7%] | 1,199 | 5.0 / 9.0 | 11 | 0 | 4 | 129 | 0 |
| 2.0 | 15 | frozen | 1,918 | 590 | 30.8% [28.7%, 33.0%] | 1,328 | 5.0 / 10.0 | 11 | 0 | 4 | 129 | 0 |
| 2.0 | 20 | evolving | 1,916 | 821 | 42.8% [40.7%, 45.1%] | 1,095 | 6.0 / 12.0 | 15 | 0 | 6 | 155 | 0 |
| 2.0 | 20 | frozen | 1,916 | 666 | 34.8% [32.6%, 37.0%] | 1,250 | 6.0 / 12.0 | 15 | 0 | 6 | 155 | 0 |
| 2.0 | 50 | evolving | 1,908 | 1,157 | 60.6% [58.6%, 62.7%] | 751 | 10.0 / 23.0 | 47 | 0 | 14 | 223 | 0 |
| 2.0 | 50 | frozen | 1,908 | 934 | 49.0% [46.9%, 51.0%] | 974 | 10.5 / 23.0 | 47 | 0 | 14 | 223 | 0 |
| 2.5 | 5 | evolving | 851 | 138 | 16.2% [13.6%, 18.9%] | 713 | 2.0 / 4.0 | 1 | 0 | 0 | 21 | 0 |
| 2.5 | 5 | frozen | 851 | 117 | 13.7% [11.4%, 16.2%] | 734 | 2.0 / 4.0 | 1 | 0 | 0 | 21 | 0 |
| 2.5 | 10 | evolving | 851 | 200 | 23.5% [20.3%, 26.6%] | 651 | 4.0 / 7.0 | 1 | 0 | 0 | 54 | 0 |
| 2.5 | 10 | frozen | 851 | 146 | 17.2% [14.5%, 19.9%] | 705 | 3.0 / 5.0 | 1 | 0 | 0 | 54 | 0 |
| 2.5 | 15 | evolving | 850 | 260 | 30.6% [27.3%, 33.8%] | 590 | 5.0 / 9.2 | 2 | 0 | 1 | 65 | 0 |
| 2.5 | 15 | frozen | 850 | 195 | 22.9% [20.2%, 25.9%] | 655 | 4.0 / 10.5 | 2 | 0 | 1 | 65 | 0 |
| 2.5 | 20 | evolving | 848 | 298 | 35.1% [31.9%, 38.4%] | 550 | 7.0 / 12.0 | 3 | 0 | 3 | 74 | 0 |
| 2.5 | 20 | frozen | 848 | 224 | 26.4% [23.4%, 29.5%] | 624 | 5.0 / 13.0 | 3 | 0 | 3 | 74 | 0 |
| 2.5 | 50 | evolving | 836 | 449 | 53.7% [50.4%, 57.2%] | 387 | 12.0 / 25.0 | 19 | 0 | 15 | 99 | 0 |
| 2.5 | 50 | frozen | 836 | 350 | 41.9% [38.6%, 45.1%] | 486 | 13.0 / 26.0 | 19 | 0 | 15 | 99 | 0 |
| 3.0 | 5 | evolving | 208 | 53 | 25.5% [18.8%, 32.0%] | 155 | 2.0 / 3.0 | 1 | 0 | 0 | 5 | 0 |
| 3.0 | 5 | frozen | 208 | 48 | 23.1% [16.9%, 29.5%] | 160 | 2.0 / 4.0 | 1 | 0 | 0 | 5 | 0 |
| 3.0 | 10 | evolving | 208 | 67 | 32.2% [25.4%, 38.9%] | 141 | 3.0 / 5.0 | 1 | 0 | 0 | 12 | 0 |
| 3.0 | 10 | frozen | 208 | 55 | 26.4% [19.6%, 33.0%] | 153 | 2.0 / 4.0 | 1 | 0 | 0 | 12 | 0 |
| 3.0 | 15 | evolving | 207 | 83 | 40.1% [32.7%, 47.0%] | 124 | 4.0 / 8.5 | 1 | 0 | 1 | 14 | 0 |
| 3.0 | 15 | frozen | 207 | 69 | 33.3% [26.4%, 40.2%] | 138 | 3.0 / 8.0 | 1 | 0 | 1 | 14 | 0 |
| 3.0 | 20 | evolving | 206 | 89 | 43.2% [35.7%, 50.2%] | 117 | 4.0 / 9.0 | 2 | 0 | 2 | 15 | 0 |
| 3.0 | 20 | frozen | 206 | 74 | 35.9% [28.7%, 42.8%] | 132 | 4.0 / 10.8 | 2 | 0 | 2 | 15 | 0 |
| 3.0 | 50 | evolving | 201 | 122 | 60.7% [53.2%, 67.8%] | 79 | 8.0 / 21.0 | 8 | 0 | 7 | 25 | 0 |
| 3.0 | 50 | frozen | 201 | 97 | 48.3% [40.9%, 55.5%] | 104 | 6.0 / 18.0 | 8 | 0 | 7 | 25 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,668 | 1.89 [1.69, 2.11] / 0.90 | 1.83 [1.62, 2.07] / 0.90 | 1.83 [1.62, 2.07] / 0.90 | 1.89 [1.69, 2.11] / 0.90 | 0.08 [-0.10, 0.25] | -0.08 [-0.25, 0.10] | 50.2% [47.9%, 52.4%] | 50.2% [47.9%, 52.4%] | 47.0% [44.7%, 49.4%] | 67 | 716 / 343 | 1 | adequate descriptive support | 594 / 662 / 372 / 40 | 0 |
| 2.0 | 10 | 1,667 | 2.73 [2.42, 3.05] / 1.20 | 2.54 [2.24, 2.87] / 1.30 | 2.54 [2.24, 2.87] / 1.30 | 2.73 [2.42, 3.05] / 1.20 | 0.04 [-0.23, 0.30] | -0.04 [-0.30, 0.23] | 51.5% [48.8%, 54.1%] | 51.5% [48.8%, 54.1%] | 46.6% [44.1%, 49.3%] | 46 | 716 / 343 | 2 | adequate descriptive support | 685 / 732 / 210 / 40 | 0 |
| 2.0 | 15 | 1,667 | 3.31 [2.90, 3.78] / 1.50 | 3.02 [2.68, 3.39] / 1.60 | 3.02 [2.68, 3.39] / 1.60 | 3.31 [2.90, 3.78] / 1.50 | 0.09 [-0.19, 0.36] | -0.09 [-0.36, 0.19] | 50.8% [48.5%, 53.1%] | 50.8% [48.5%, 53.1%] | 46.3% [44.1%, 48.6%] | 39 | 716 / 343 | 2 | adequate descriptive support | 732 / 763 / 132 / 40 | 0 |
| 2.0 | 20 | 1,666 | 3.75 [3.30, 4.27] / 1.70 | 3.45 [3.07, 3.86] / 1.80 | 3.45 [3.07, 3.86] / 1.80 | 3.75 [3.30, 4.27] / 1.70 | 0.10 [-0.26, 0.42] | -0.10 [-0.42, 0.26] | 51.8% [49.4%, 54.1%] | 51.8% [49.4%, 54.1%] | 44.9% [42.4%, 47.2%] | 32 | 716 / 343 | 3 | adequate descriptive support | 755 / 783 / 88 / 40 | 0 |
| 2.0 | 50 | 1,656 | 5.76 [5.10, 6.49] / 2.80 | 5.68 [5.02, 6.41] / 3.10 | 5.68 [5.02, 6.41] / 3.10 | 5.76 [5.10, 6.49] / 2.80 | 0.69 [0.16, 1.26] | -0.69 [-1.26, -0.16] | 54.6% [51.8%, 57.3%] | 54.6% [51.8%, 57.3%] | 47.4% [45.1%, 49.8%] | 12 | 715 / 343 | 13 | adequate descriptive support | 785 / 813 / 19 / 39 | 0 |
| 2.5 | 5 | 694 | 1.91 [1.67, 2.17] / 0.90 | 1.96 [1.71, 2.24] / 1.00 | 1.96 [1.71, 2.24] / 1.00 | 1.91 [1.67, 2.17] / 0.90 | 0.22 [-0.01, 0.47] | -0.22 [-0.47, 0.01] | 52.2% [48.7%, 55.7%] | 52.2% [48.7%, 55.7%] | 47.1% [43.6%, 50.5%] | 29 | 463 / 282 | 1 | adequate descriptive support | 248 / 257 / 172 / 17 | 0 |
| 2.5 | 10 | 693 | 2.84 [2.39, 3.35] / 1.30 | 2.68 [2.34, 3.06] / 1.50 | 2.68 [2.34, 3.06] / 1.50 | 2.84 [2.39, 3.35] / 1.30 | 0.04 [-0.45, 0.45] | -0.04 [-0.45, 0.45] | 52.2% [48.5%, 56.1%] | 52.2% [48.5%, 56.1%] | 44.0% [40.4%, 47.9%] | 18 | 462 / 282 | 2 | adequate descriptive support | 282 / 284 / 110 / 17 | 0 |
| 2.5 | 15 | 693 | 3.56 [2.89, 4.48] / 1.60 | 3.21 [2.82, 3.67] / 1.80 | 3.21 [2.82, 3.67] / 1.80 | 3.56 [2.89, 4.48] / 1.60 | 0.12 [-0.45, 0.60] | -0.12 [-0.60, 0.45] | 53.0% [49.5%, 56.5%] | 53.0% [49.5%, 56.5%] | 48.1% [44.5%, 51.4%] | 18 | 462 / 282 | 2 | adequate descriptive support | 310 / 301 / 65 / 17 | 0 |
| 2.5 | 20 | 692 | 4.04 [3.30, 5.09] / 1.80 | 3.64 [3.21, 4.14] / 1.90 | 3.64 [3.21, 4.14] / 1.90 | 4.04 [3.30, 5.09] / 1.80 | 0.06 [-0.64, 0.66] | -0.06 [-0.66, 0.64] | 53.5% [50.1%, 57.0%] | 53.5% [50.1%, 57.0%] | 44.9% [41.2%, 48.5%] | 9 | 462 / 282 | 3 | adequate descriptive support | 323 / 308 / 44 / 17 | 0 |
| 2.5 | 50 | 688 | 6.18 [5.16, 7.48] / 2.80 | 5.77 [5.08, 6.55] / 3.35 | 5.77 [5.08, 6.55] / 3.35 | 6.18 [5.16, 7.48] / 2.80 | 0.33 [-0.41, 1.08] | -0.33 [-1.08, 0.41] | 53.9% [50.0%, 57.7%] | 53.9% [50.0%, 57.7%] | 46.2% [42.6%, 49.8%] | 4 | 460 / 281 | 7 | adequate descriptive support | 341 / 324 / 7 / 16 | 0 |
| 3.0 | 5 | 167 | 1.96 [1.50, 2.51] / 0.90 | 1.79 [1.45, 2.18] / 1.00 | 1.79 [1.45, 2.18] / 1.00 | 1.96 [1.50, 2.51] / 0.90 | 0.01 [-0.44, 0.41] | -0.01 [-0.41, 0.44] | 51.5% [44.5%, 58.9%] | 51.5% [44.5%, 58.9%] | 49.7% [41.7%, 57.3%] | 6 | 145 / 121 | 0 | adequate descriptive support | 64 / 61 / 33 / 9 | 0 |
| 3.0 | 10 | 167 | 2.79 [2.11, 3.56] / 1.10 | 2.32 [1.90, 2.78] / 1.40 | 2.32 [1.90, 2.78] / 1.40 | 2.79 [2.11, 3.56] / 1.10 | -0.25 [-0.83, 0.32] | 0.25 [-0.32, 0.83] | 49.7% [42.1%, 56.7%] | 49.7% [42.1%, 56.7%] | 41.3% [34.2%, 48.4%] | 2 | 145 / 121 | 0 | adequate descriptive support | 68 / 67 / 23 / 9 | 0 |
| 3.0 | 15 | 167 | 3.57 [2.68, 4.65] / 1.40 | 3.01 [2.35, 3.79] / 1.60 | 3.01 [2.35, 3.79] / 1.60 | 3.57 [2.68, 4.65] / 1.40 | -0.03 [-0.94, 0.92] | 0.03 [-0.92, 0.94] | 49.7% [42.9%, 56.9%] | 49.7% [42.9%, 56.9%] | 41.9% [34.7%, 48.8%] | 4 | 145 / 121 | 0 | adequate descriptive support | 73 / 73 / 12 / 9 | 0 |
| 3.0 | 20 | 166 | 4.07 [3.01, 5.41] / 1.80 | 3.36 [2.63, 4.23] / 1.75 | 3.36 [2.63, 4.23] / 1.75 | 4.07 [3.01, 5.41] / 1.80 | 0.12 [-1.16, 1.31] | -0.12 [-1.31, 1.16] | 49.4% [42.7%, 56.5%] | 49.4% [42.7%, 56.5%] | 45.8% [38.5%, 53.5%] | 4 | 144 / 120 | 1 | adequate descriptive support | 74 / 75 / 8 / 9 | 0 |
| 3.0 | 50 | 166 | 6.32 [4.64, 8.41] / 2.95 | 5.66 [4.36, 7.29] / 2.85 | 5.66 [4.36, 7.29] / 2.85 | 6.32 [4.64, 8.41] / 2.95 | 0.31 [-1.31, 2.03] | -0.31 [-2.03, 1.31] | 51.2% [42.8%, 59.3%] | 51.2% [42.8%, 59.3%] | 42.8% [35.5%, 50.3%] | 1 | 144 / 120 | 1 | adequate descriptive support | 78 / 79 / 0 / 9 | 0 |

### Lower departure / arrival: continuation and bounce short; fade and through long

#### Departure response

| σ | h | n | Continuation MAE mean [CI] / median | Continuation MFE mean [CI] / median | Fade MAE mean [CI] / median | Fade MFE mean [CI] / median | Continuation Δ mean [CI] | Fade Δ mean [CI] | Continuation endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,873 | 2.12 [1.84, 2.44] / 0.90 | 2.57 [2.23, 2.99] / 1.00 | 2.57 [2.23, 2.99] / 1.00 | 2.12 [1.84, 2.44] / 0.90 | 0.05 [-0.14, 0.25] | -0.05 [-0.25, 0.14] | 45.4% [43.5%, 47.6%] | 50.2% [47.9%, 52.3%] | 47.4% [45.3%, 49.4%] | 81 | 754 / 346 | 0 | adequate descriptive support |
| 2.0 | 10 | 1,873 | 2.88 [2.51, 3.27] / 1.30 | 3.50 [3.05, 4.02] / 1.40 | 3.50 [3.05, 4.02] / 1.40 | 2.88 [2.51, 3.27] / 1.30 | 0.07 [-0.19, 0.34] | -0.07 [-0.34, 0.19] | 47.9% [45.7%, 50.2%] | 48.9% [46.6%, 51.0%] | 48.5% [46.4%, 50.7%] | 60 | 754 / 346 | 0 | adequate descriptive support |
| 2.0 | 15 | 1,872 | 3.37 [2.95, 3.82] / 1.50 | 4.29 [3.72, 4.93] / 1.70 | 4.29 [3.72, 4.93] / 1.70 | 3.37 [2.95, 3.82] / 1.50 | 0.14 [-0.18, 0.47] | -0.14 [-0.47, 0.18] | 46.6% [44.4%, 48.9%] | 51.0% [48.7%, 53.4%] | 45.6% [43.3%, 48.0%] | 44 | 754 / 346 | 1 | adequate descriptive support |
| 2.0 | 20 | 1,871 | 3.79 [3.34, 4.29] / 1.80 | 4.80 [4.16, 5.53] / 1.80 | 4.80 [4.16, 5.53] / 1.80 | 3.79 [3.34, 4.29] / 1.80 | 0.24 [-0.13, 0.63] | -0.24 [-0.63, 0.13] | 48.5% [46.0%, 51.0%] | 49.6% [47.1%, 52.2%] | 46.1% [44.1%, 48.1%] | 36 | 754 / 346 | 2 | adequate descriptive support |
| 2.0 | 50 | 1,855 | 5.75 [5.07, 6.52] / 2.90 | 7.06 [6.07, 8.27] / 2.90 | 7.06 [6.07, 8.27] / 2.90 | 5.75 [5.07, 6.52] / 2.90 | -0.10 [-0.62, 0.43] | 0.10 [-0.43, 0.62] | 47.5% [45.0%, 50.1%] | 51.6% [49.1%, 54.0%] | 45.8% [43.6%, 48.1%] | 16 | 751 / 345 | 18 | adequate descriptive support |
| 2.5 | 5 | 872 | 2.40 [2.06, 2.83] / 1.10 | 3.06 [2.60, 3.61] / 1.10 | 3.06 [2.60, 3.61] / 1.10 | 2.40 [2.06, 2.83] / 1.10 | 0.08 [-0.22, 0.40] | -0.08 [-0.40, 0.22] | 45.3% [42.3%, 48.6%] | 50.0% [46.7%, 53.2%] | 48.4% [44.9%, 51.6%] | 41 | 553 / 306 | 0 | adequate descriptive support |
| 2.5 | 10 | 871 | 3.22 [2.71, 3.89] / 1.50 | 3.99 [3.36, 4.71] / 1.60 | 3.99 [3.36, 4.71] / 1.60 | 3.22 [2.71, 3.89] / 1.50 | -0.05 [-0.55, 0.45] | 0.05 [-0.45, 0.55] | 46.0% [42.8%, 49.4%] | 51.2% [47.6%, 54.6%] | 47.9% [44.5%, 51.3%] | 24 | 552 / 306 | 1 | adequate descriptive support |
| 2.5 | 15 | 870 | 3.79 [3.19, 4.58] / 1.80 | 4.81 [4.05, 5.69] / 1.90 | 4.81 [4.05, 5.69] / 1.90 | 3.79 [3.19, 4.58] / 1.80 | -0.05 [-0.72, 0.60] | 0.05 [-0.60, 0.72] | 46.7% [43.1%, 49.9%] | 51.0% [47.7%, 54.8%] | 43.4% [40.0%, 47.0%] | 20 | 552 / 306 | 2 | adequate descriptive support |
| 2.5 | 20 | 870 | 4.27 [3.62, 5.11] / 2.00 | 5.26 [4.45, 6.24] / 2.20 | 5.26 [4.45, 6.24] / 2.20 | 4.27 [3.62, 5.11] / 2.00 | -0.10 [-0.71, 0.50] | 0.10 [-0.50, 0.71] | 49.3% [45.9%, 52.5%] | 48.7% [45.4%, 52.1%] | 47.2% [44.0%, 50.5%] | 17 | 552 / 306 | 2 | adequate descriptive support |
| 2.5 | 50 | 863 | 6.62 [5.63, 7.94] / 3.20 | 7.84 [6.53, 9.50] / 3.30 | 7.84 [6.53, 9.50] / 3.30 | 6.62 [5.63, 7.94] / 3.20 | -0.49 [-1.25, 0.30] | 0.49 [-0.30, 1.25] | 45.7% [42.5%, 48.8%] | 53.2% [50.1%, 56.4%] | 47.2% [44.1%, 50.5%] | 10 | 550 / 306 | 9 | adequate descriptive support |
| 3.0 | 5 | 240 | 2.52 [2.08, 3.05] / 1.30 | 3.10 [2.53, 3.77] / 1.30 | 3.10 [2.53, 3.77] / 1.30 | 2.52 [2.08, 3.05] / 1.30 | -0.04 [-0.57, 0.54] | 0.04 [-0.54, 0.57] | 45.0% [39.0%, 51.3%] | 52.5% [46.4%, 58.4%] | 46.7% [39.9%, 52.5%] | 6 | 210 / 173 | 1 | adequate descriptive support |
| 3.0 | 10 | 240 | 3.23 [2.67, 3.82] / 1.80 | 3.81 [3.16, 4.58] / 1.65 | 3.81 [3.16, 4.58] / 1.65 | 3.23 [2.67, 3.82] / 1.80 | -0.24 [-0.86, 0.36] | 0.24 [-0.36, 0.86] | 38.8% [32.6%, 45.0%] | 56.7% [50.2%, 63.0%] | 47.1% [40.9%, 53.3%] | 11 | 210 / 173 | 1 | adequate descriptive support |
| 3.0 | 15 | 240 | 3.61 [3.00, 4.25] / 2.00 | 4.58 [3.75, 5.55] / 2.00 | 4.58 [3.75, 5.55] / 2.00 | 3.61 [3.00, 4.25] / 2.00 | -0.05 [-0.84, 0.75] | 0.05 [-0.75, 0.84] | 45.8% [39.3%, 51.9%] | 52.5% [46.2%, 59.1%] | 44.6% [38.9%, 50.6%] | 4 | 210 / 173 | 1 | adequate descriptive support |
| 3.0 | 20 | 240 | 4.06 [3.36, 4.80] / 2.30 | 5.03 [4.09, 6.17] / 2.20 | 5.03 [4.09, 6.17] / 2.20 | 4.06 [3.36, 4.80] / 2.30 | 0.26 [-0.67, 1.18] | -0.26 [-1.18, 0.67] | 46.2% [40.2%, 52.4%] | 51.7% [45.5%, 58.0%] | 44.2% [38.4%, 49.8%] | 5 | 210 / 173 | 1 | adequate descriptive support |
| 3.0 | 50 | 236 | 5.74 [4.77, 6.73] / 3.50 | 7.26 [5.87, 9.02] / 3.10 | 7.26 [5.87, 9.02] / 3.10 | 5.74 [4.77, 6.73] / 3.50 | 0.09 [-1.22, 1.45] | -0.09 [-1.45, 1.22] | 42.8% [35.9%, 49.8%] | 57.2% [50.2%, 64.1%] | 47.0% [40.2%, 53.9%] | 0 | 206 / 172 | 5 | adequate descriptive support |

#### VWAP return probability and timing

| σ | h | Target | n | Touches | Touch % [CI] | No touch | Latency h median / p75 | Gap paths | Overtake paths | Unavailable | Evolving only | Frozen only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | evolving | 1,873 | 361 | 19.3% [17.1%, 21.3%] | 1,512 | 2.0 / 4.0 | 6 | 0 | 0 | 50 | 0 |
| 2.0 | 5 | frozen | 1,873 | 311 | 16.6% [14.6%, 18.7%] | 1,562 | 2.0 / 4.0 | 6 | 0 | 0 | 50 | 0 |
| 2.0 | 10 | evolving | 1,873 | 587 | 31.3% [28.9%, 33.8%] | 1,286 | 4.0 / 7.0 | 8 | 0 | 0 | 108 | 0 |
| 2.0 | 10 | frozen | 1,873 | 479 | 25.6% [23.3%, 27.8%] | 1,394 | 4.0 / 7.0 | 8 | 0 | 0 | 108 | 0 |
| 2.0 | 15 | evolving | 1,872 | 721 | 38.5% [36.1%, 40.8%] | 1,151 | 5.0 / 9.0 | 17 | 0 | 1 | 133 | 0 |
| 2.0 | 15 | frozen | 1,872 | 588 | 31.4% [29.0%, 33.7%] | 1,284 | 5.0 / 9.0 | 17 | 0 | 1 | 133 | 0 |
| 2.0 | 20 | evolving | 1,871 | 835 | 44.6% [42.2%, 47.0%] | 1,036 | 7.0 / 11.5 | 23 | 0 | 2 | 166 | 0 |
| 2.0 | 20 | frozen | 1,871 | 669 | 35.8% [33.5%, 38.1%] | 1,202 | 6.0 / 11.0 | 23 | 0 | 2 | 166 | 0 |
| 2.0 | 50 | evolving | 1,855 | 1,181 | 63.7% [61.4%, 65.8%] | 674 | 11.0 / 23.0 | 50 | 0 | 18 | 234 | 0 |
| 2.0 | 50 | frozen | 1,855 | 947 | 51.1% [48.5%, 53.3%] | 908 | 10.0 / 23.0 | 50 | 0 | 18 | 234 | 0 |
| 2.5 | 5 | evolving | 872 | 133 | 15.3% [12.8%, 17.6%] | 739 | 2.0 / 4.0 | 2 | 0 | 0 | 14 | 0 |
| 2.5 | 5 | frozen | 872 | 119 | 13.6% [11.4%, 16.0%] | 753 | 2.0 / 3.5 | 2 | 0 | 0 | 14 | 0 |
| 2.5 | 10 | evolving | 871 | 227 | 26.1% [23.0%, 29.0%] | 644 | 5.0 / 7.0 | 5 | 0 | 1 | 43 | 0 |
| 2.5 | 10 | frozen | 871 | 184 | 21.1% [18.2%, 23.9%] | 687 | 4.0 / 7.0 | 5 | 0 | 1 | 43 | 0 |
| 2.5 | 15 | evolving | 870 | 284 | 32.6% [29.5%, 35.8%] | 586 | 6.0 / 9.0 | 9 | 0 | 2 | 60 | 0 |
| 2.5 | 15 | frozen | 870 | 224 | 25.7% [22.7%, 28.7%] | 646 | 5.0 / 9.0 | 9 | 0 | 2 | 60 | 0 |
| 2.5 | 20 | evolving | 870 | 324 | 37.2% [34.0%, 40.3%] | 546 | 6.5 / 11.0 | 10 | 0 | 2 | 74 | 0 |
| 2.5 | 20 | frozen | 870 | 250 | 28.7% [25.6%, 31.7%] | 620 | 6.0 / 11.0 | 10 | 0 | 2 | 74 | 0 |
| 2.5 | 50 | evolving | 863 | 493 | 57.1% [54.1%, 60.1%] | 370 | 12.0 / 27.0 | 25 | 0 | 9 | 117 | 0 |
| 2.5 | 50 | frozen | 863 | 376 | 43.6% [40.3%, 46.5%] | 487 | 11.0 / 26.0 | 25 | 0 | 9 | 117 | 0 |
| 3.0 | 5 | evolving | 240 | 49 | 20.4% [15.0%, 26.1%] | 191 | 2.0 / 3.0 | 2 | 0 | 1 | 8 | 0 |
| 3.0 | 5 | frozen | 240 | 41 | 17.1% [12.2%, 22.3%] | 199 | 1.0 / 3.0 | 2 | 0 | 1 | 8 | 0 |
| 3.0 | 10 | evolving | 240 | 69 | 28.7% [22.5%, 34.9%] | 171 | 3.0 / 6.0 | 2 | 0 | 1 | 10 | 0 |
| 3.0 | 10 | frozen | 240 | 59 | 24.6% [19.0%, 30.2%] | 181 | 2.0 / 6.0 | 2 | 0 | 1 | 10 | 0 |
| 3.0 | 15 | evolving | 240 | 79 | 32.9% [26.7%, 38.9%] | 161 | 3.0 / 8.0 | 2 | 0 | 1 | 13 | 0 |
| 3.0 | 15 | frozen | 240 | 66 | 27.5% [21.7%, 33.2%] | 174 | 3.0 / 8.0 | 2 | 0 | 1 | 13 | 0 |
| 3.0 | 20 | evolving | 240 | 87 | 36.2% [30.1%, 42.4%] | 153 | 5.0 / 9.5 | 2 | 0 | 1 | 13 | 0 |
| 3.0 | 20 | frozen | 240 | 74 | 30.8% [24.8%, 36.6%] | 166 | 4.5 / 9.8 | 2 | 0 | 1 | 13 | 0 |
| 3.0 | 50 | evolving | 236 | 124 | 52.5% [45.5%, 59.1%] | 112 | 9.0 / 23.0 | 6 | 0 | 5 | 29 | 0 |
| 3.0 | 50 | frozen | 236 | 95 | 40.3% [33.9%, 46.3%] | 141 | 7.0 / 18.0 | 6 | 0 | 5 | 29 | 0 |

#### First-return response

Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.

| σ | h | n | Bounce MAE mean [CI] / median | Bounce MFE mean [CI] / median | Through MAE mean [CI] / median | Through MFE mean [CI] / median | Bounce Δ mean [CI] | Through Δ mean [CI] | Bounce endpoint % | Close > entry % | Final candle up % | Entry ties | Days / weeks | Unavailable | Support | First B / T / neither / ambiguous | Barrier unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 1,648 | 1.80 [1.55, 2.12] / 0.80 | 1.68 [1.47, 1.93] / 0.80 | 1.68 [1.47, 1.93] / 0.80 | 1.80 [1.55, 2.12] / 0.80 | -0.10 [-0.34, 0.09] | 0.10 [-0.09, 0.34] | 50.1% [47.6%, 52.7%] | 45.8% [43.3%, 48.2%] | 44.2% [41.7%, 46.8%] | 68 | 715 / 340 | 0 | adequate descriptive support | 558 / 620 / 423 / 47 | 0 |
| 2.0 | 10 | 1,647 | 2.57 [2.21, 3.01] / 1.20 | 2.31 [2.01, 2.62] / 1.10 | 2.31 [2.01, 2.62] / 1.10 | 2.57 [2.21, 3.01] / 1.20 | -0.26 [-0.53, -0.00] | 0.26 [0.00, 0.53] | 48.5% [46.2%, 51.0%] | 48.3% [45.7%, 50.7%] | 46.1% [43.5%, 48.5%] | 53 | 715 / 340 | 1 | adequate descriptive support | 650 / 708 / 241 / 48 | 0 |
| 2.0 | 15 | 1,647 | 3.10 [2.68, 3.59] / 1.50 | 2.78 [2.44, 3.15] / 1.40 | 2.78 [2.44, 3.15] / 1.40 | 3.10 [2.68, 3.59] / 1.50 | -0.38 [-0.75, -0.03] | 0.38 [0.03, 0.75] | 46.9% [44.5%, 49.5%] | 51.1% [48.7%, 53.6%] | 44.9% [42.5%, 47.4%] | 33 | 715 / 340 | 1 | adequate descriptive support | 695 / 753 / 151 / 48 | 0 |
| 2.0 | 20 | 1,645 | 3.61 [3.09, 4.20] / 1.70 | 3.21 [2.82, 3.63] / 1.60 | 3.21 [2.82, 3.63] / 1.60 | 3.61 [3.09, 4.20] / 1.70 | -0.48 [-0.93, -0.05] | 0.48 [0.05, 0.93] | 49.2% [46.7%, 51.6%] | 48.8% [46.3%, 51.2%] | 46.5% [44.2%, 48.9%] | 34 | 715 / 340 | 3 | adequate descriptive support | 722 / 774 / 101 / 48 | 0 |
| 2.0 | 50 | 1,629 | 5.64 [4.89, 6.52] / 2.70 | 5.37 [4.72, 6.13] / 2.70 | 5.37 [4.72, 6.13] / 2.70 | 5.64 [4.89, 6.52] / 2.70 | -0.38 [-0.96, 0.14] | 0.38 [-0.14, 0.96] | 48.7% [46.2%, 51.3%] | 50.0% [47.5%, 52.5%] | 46.0% [43.6%, 48.3%] | 21 | 714 / 340 | 19 | adequate descriptive support | 758 / 797 / 26 / 48 | 0 |
| 2.5 | 5 | 726 | 1.87 [1.60, 2.18] / 0.90 | 1.73 [1.46, 2.07] / 0.80 | 1.73 [1.46, 2.07] / 0.80 | 1.87 [1.60, 2.18] / 0.90 | -0.12 [-0.36, 0.10] | 0.12 [-0.10, 0.36] | 49.2% [45.5%, 53.0%] | 47.9% [44.1%, 51.8%] | 42.0% [38.3%, 45.8%] | 21 | 480 / 290 | 0 | adequate descriptive support | 222 / 266 / 219 / 19 | 0 |
| 2.5 | 10 | 725 | 2.67 [2.22, 3.24] / 1.30 | 2.31 [1.98, 2.69] / 1.20 | 2.31 [1.98, 2.69] / 1.20 | 2.67 [2.22, 3.24] / 1.30 | -0.29 [-0.69, 0.09] | 0.29 [-0.09, 0.69] | 49.8% [46.1%, 53.5%] | 47.2% [43.5%, 50.9%] | 43.4% [39.5%, 47.4%] | 22 | 479 / 289 | 1 | adequate descriptive support | 267 / 304 / 134 / 20 | 0 |
| 2.5 | 15 | 725 | 3.17 [2.66, 3.78] / 1.60 | 2.79 [2.42, 3.22] / 1.40 | 2.79 [2.42, 3.22] / 1.40 | 3.17 [2.66, 3.78] / 1.60 | -0.46 [-0.94, -0.02] | 0.46 [0.02, 0.94] | 47.4% [44.1%, 51.2%] | 51.0% [47.3%, 54.5%] | 46.1% [42.8%, 49.5%] | 11 | 479 / 289 | 1 | adequate descriptive support | 287 / 322 / 96 / 20 | 0 |
| 2.5 | 20 | 723 | 3.82 [3.13, 4.70] / 1.80 | 3.28 [2.86, 3.79] / 1.70 | 3.28 [2.86, 3.79] / 1.70 | 3.82 [3.13, 4.70] / 1.80 | -0.63 [-1.42, 0.04] | 0.63 [-0.04, 1.42] | 50.9% [47.4%, 54.7%] | 47.2% [43.3%, 50.7%] | 46.5% [43.0%, 49.9%] | 14 | 479 / 289 | 3 | adequate descriptive support | 303 / 335 / 65 / 20 | 0 |
| 2.5 | 50 | 715 | 5.87 [4.89, 7.08] / 2.80 | 5.63 [4.79, 6.69] / 2.90 | 5.63 [4.79, 6.69] / 2.90 | 5.87 [4.89, 7.08] / 2.80 | -0.20 [-0.96, 0.57] | 0.20 [-0.57, 0.96] | 49.8% [46.0%, 53.6%] | 48.3% [44.5%, 51.9%] | 45.5% [42.2%, 48.9%] | 14 | 474 / 289 | 11 | adequate descriptive support | 327 / 348 / 20 / 20 | 0 |
| 3.0 | 5 | 182 | 1.58 [1.24, 2.00] / 0.80 | 1.68 [1.32, 2.09] / 0.70 | 1.68 [1.32, 2.09] / 0.70 | 1.58 [1.24, 2.00] / 0.80 | -0.11 [-0.61, 0.32] | 0.11 [-0.32, 0.61] | 48.9% [41.5%, 56.1%] | 45.6% [38.4%, 53.0%] | 45.1% [37.5%, 52.3%] | 10 | 161 / 139 | 0 | adequate descriptive support | 59 / 69 / 49 / 5 | 0 |
| 3.0 | 10 | 182 | 2.22 [1.71, 2.85] / 1.10 | 2.15 [1.73, 2.60] / 1.20 | 2.15 [1.73, 2.60] / 1.20 | 2.22 [1.71, 2.85] / 1.10 | -0.07 [-0.53, 0.37] | 0.07 [-0.37, 0.53] | 48.9% [41.1%, 56.5%] | 47.3% [40.0%, 55.1%] | 44.0% [36.4%, 51.2%] | 7 | 161 / 139 | 0 | adequate descriptive support | 65 / 78 / 34 / 5 | 0 |
| 3.0 | 15 | 182 | 2.57 [1.98, 3.31] / 1.35 | 2.58 [2.08, 3.17] / 1.40 | 2.58 [2.08, 3.17] / 1.40 | 2.57 [1.98, 3.31] / 1.35 | -0.12 [-0.85, 0.54] | 0.12 [-0.54, 0.85] | 51.1% [43.8%, 58.1%] | 48.4% [41.2%, 55.6%] | 53.8% [47.1%, 61.1%] | 1 | 161 / 139 | 0 | adequate descriptive support | 71 / 82 / 24 / 5 | 0 |
| 3.0 | 20 | 181 | 3.05 [2.36, 3.86] / 1.50 | 3.10 [2.49, 3.86] / 1.60 | 3.10 [2.49, 3.86] / 1.60 | 3.05 [2.36, 3.86] / 1.50 | -0.01 [-0.70, 0.69] | 0.01 [-0.69, 0.70] | 53.6% [45.9%, 61.4%] | 44.8% [37.0%, 52.3%] | 44.2% [36.8%, 51.7%] | 3 | 161 / 139 | 1 | adequate descriptive support | 74 / 86 / 16 / 5 | 0 |
| 3.0 | 50 | 177 | 5.05 [3.97, 6.29] / 2.70 | 4.91 [3.97, 6.04] / 3.00 | 4.91 [3.97, 6.04] / 3.00 | 5.05 [3.97, 6.29] / 2.70 | -0.18 [-1.55, 1.12] | 0.18 [-1.12, 1.55] | 50.8% [43.5%, 58.2%] | 44.6% [37.3%, 51.7%] | 49.7% [41.9%, 57.3%] | 8 | 157 / 135 | 5 | adequate descriptive support | 81 / 86 / 5 / 5 | 0 |

### Common cohort, distribution and year diagnostics

The horizon curves use the identical complete-50 cohort. Distribution quantiles and year diagnostics use each horizon’s eligible cohort. Year 2026 is partial. These diagnostics are descriptive on previously inspected history.

![GC Globex return](figures/globex-GC-return.svg)

![GC Globex excursion](figures/globex-GC-excursion.svg)

![GC Globex endpoint](figures/globex-GC-endpoint.svg)

![GC Globex mae-mfe-distribution](figures/globex-GC-mae-mfe-distribution.svg)

![GC Globex terminal-distribution](figures/globex-GC-terminal-distribution.svg)

![GC Globex year-stability](figures/globex-GC-year-stability.svg)

### Sensitivity and chronological periods at 10 candles

| Module | Scope | n | Days / weeks | Directional Δ [CI] | Return or bounce endpoint % [CI] |
| --- | --- | --- | --- | --- | --- |
| departure | all | 3,793 | 823 / 356 | 0.18 [0.04, 0.33] | 31.0% [29.3%, 32.6%] |
| departure | common_50 | 3,763 | 823 / 356 | 0.20 [0.06, 0.34] | 31.2% [29.5%, 32.9%] |
| departure | age_ge30 | 3,111 | 822 / 356 | 0.31 [0.15, 0.49] | 20.8% [19.1%, 22.5%] |
| departure | through_2023 | 2,446 | 512 / 241 | 0.05 [-0.04, 0.15] | 31.7% [29.4%, 33.8%] |
| departure | year_2024_period | 318 | 62 / 32 | 0.36 [-0.09, 0.83] | 34.3% [30.9%, 37.6%] |
| departure | years_2025_2026 | 1,029 | 249 / 83 | 0.44 [0.00, 0.90] | 28.3% [24.9%, 31.7%] |
| touch | all | 3,314 | 814 / 355 | -0.11 [-0.30, 0.06] | 50.0% [48.2%, 51.7%] |
| touch | common_50 | 3,285 | 814 / 355 | -0.12 [-0.31, 0.06] | 50.1% [48.4%, 51.9%] |
| touch | age_ge30 | 2,632 | 798 / 353 | -0.06 [-0.27, 0.14] | 50.8% [48.8%, 52.7%] |
| touch | through_2023 | 2,142 | 510 / 241 | -0.05 [-0.13, 0.03] | 49.8% [47.7%, 51.8%] |
| touch | year_2024_period | 286 | 61 / 31 | -0.21 [-0.50, 0.08] | 43.4% [37.2%, 49.2%] |
| touch | years_2025_2026 | 886 | 243 / 83 | -0.24 [-0.91, 0.37] | 52.7% [48.7%, 56.6%] |

### Deterministic source-path examples

Examples are the earliest stable ID in each prespecified class. They illustrate mechanisms and exclusions, not representative trade quality. The source table includes reference available_at and known sigma for every minute; charts plot raw one-minute high/low and references. Source minute open time relative to entry is shown; contacts have interval resolution. Lines join minute OHLC observations for display and do not imply intraminute order or trades through gaps. The 2-sigma envelope is plotted; 2.5/3-sigma references are retained in the example-path table.

return: GC-globex-2016-02-11-P0002-K2-H10; upper side. Signal/confirmation 2016-02-10 18:06:00-05:00; entry 2016-02-10 18:06:00-05:00; deadline 2016-02-10 18:26:00-05:00 (New York time). Frozen sigma 0.18 points; signal VWAP 1,196.90. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-globex-2016-02-11-P0002-K2-H10](figures/example-globex-GC-return.svg)

non_return: GC-globex-2016-02-11-P0286-K2-H10; upper side. Signal/confirmation 2016-02-11 03:34:00-05:00; entry 2016-02-11 03:34:00-05:00; deadline 2016-02-11 03:54:00-05:00 (New York time). Frozen sigma 3.83 points; signal VWAP 1,208.25. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-globex-2016-02-11-P0286-K2-H10](figures/example-globex-GC-non_return.svg)

bounce: GC-globex-2016-02-11-P0002-T-H10; upper side. Signal/confirmation 2016-02-10 18:22:00-05:00; entry 2016-02-10 18:22:00-05:00; deadline 2016-02-10 18:42:00-05:00 (New York time). Frozen sigma 0.62 points; signal VWAP 1,197.59. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-globex-2016-02-11-P0002-T-H10](figures/example-globex-GC-bounce.svg)

through: GC-globex-2016-05-09-P0012-T-H10; upper side. Signal/confirmation 2016-05-08 18:32:00-04:00; entry 2016-05-08 18:32:00-04:00; deadline 2016-05-08 18:52:00-04:00 (New York time). Frozen sigma 0.42 points; signal VWAP 1,287.28. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-globex-2016-05-09-P0012-T-H10](figures/example-globex-GC-through.svg)

ambiguity: GC-globex-2016-11-17-P0003-T-H10; upper side. Signal/confirmation 2016-11-16 18:10:00-05:00; entry 2016-11-16 18:10:00-05:00; deadline 2016-11-16 18:30:00-05:00 (New York time). Frozen sigma 0.12 points; signal VWAP 1,225.26. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: none.

![GC-globex-2016-11-17-P0003-T-H10](figures/example-globex-GC-ambiguity.svg)

exclusion: GC-globex-2016-06-17-P0655-K2-H50; upper side. Signal/confirmation 2016-06-17 15:52:00-04:00; entry 2016-06-17 15:52:00-04:00; deadline 2016-06-17 17:32:00-04:00 (New York time). Frozen sigma 4.62 points; signal VWAP 1,290.54. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: session_boundary.

![GC-globex-2016-06-17-P0655-K2-H50](figures/example-globex-GC-exclusion.svg)

## Interpretation and verification

Return rates, first-move rates and terminal directional frequencies answer different questions. MAE/MFE maxima are favorable/adverse opportunities on an observed path, not obtainable trading profits. Threshold comparisons are descriptive because signal times and eligible populations differ. Treat sparse cells and boundary uncertainty as unresolved. Shared week intervals do not remove retrospective selection or establish a causal predictor.

[Numerical verification record](verification.json)

[Dated findings and advice](advice.md)

[Example selection ledger](tables/example-selection.csv)

[Independent source recounts](tables/independent-recounts.csv)

[Retained event evidence and checksums](events.manifest.json)
