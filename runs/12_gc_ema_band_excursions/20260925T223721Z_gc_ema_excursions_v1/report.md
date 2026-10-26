# GC outer lower EMA band: long excursions

Study 12, protocol 1.0.0. Descriptive retrospective path analysis; not a trade backtest with costs or an exit rule.

The signal is a completed five-minute close at or below EMA225 minus three population standard deviations of signed close-minus-EMA residuals. Entry is the next complete bar's reconstructed unadjusted open. MAE and MFE use H future bars and are separate extrema.

## Default view: 10-bar cooldown, 20-bar horizon

| Year | Accepted | Valid | Mean MAE (pts) | Mean MFE (pts) | Mean terminal (pts) | Terminal positive |
|---:|---:|---:|---:|---:|---:|---:|
| 2026 YTD | 272 | 245 | 30.94 | 23.91 | -0.15 | 54.3% |
| 2025 | 218 | 207 | 11.77 | 11.50 | 1.75 | 58.9% |
| 2024 | 295 | 278 | 6.48 | 5.46 | -0.28 | 51.8% |
| 2023 | 342 | 326 | 4.22 | 3.79 | -0.29 | 49.4% |
| 2022 | 385 | 354 | 4.46 | 4.72 | 0.31 | 49.7% |
| 2021 | 335 | 315 | 5.68 | 5.30 | 0.23 | 52.1% |
| 2020 | 295 | 275 | 7.52 | 6.64 | -0.05 | 51.3% |
| 2019 | 263 | 246 | 3.14 | 2.63 | 0.01 | 52.0% |
| 2018 | 376 | 336 | 2.26 | 1.93 | -0.15 | 49.1% |
| 2017 | 374 | 341 | 2.16 | 1.97 | 0.01 | 51.9% |
| 2016 | 300 | 279 | 3.49 | 3.35 | 0.04 | 56.6% |
| 2015 | 380 | 324 | 3.18 | 3.11 | 0.03 | 54.0% |
| 2014 | 359 | 289 | 3.51 | 3.11 | -0.04 | 51.2% |
| 2013 | 410 | 376 | 6.01 | 4.59 | -0.72 | 49.5% |
| 2012 | 381 | 361 | 5.38 | 4.46 | -0.04 | 52.9% |
| 2011 | 350 | 316 | 7.82 | 5.57 | -1.11 | 48.1% |
| 2010 | 160 | 141 | 5.21 | 3.88 | -0.64 | 53.2% |

## Interpretation

In the default view, 2026 YTD has 245 valid paths and mean MAE/MFE of 30.94/23.91 points, compared with 207 and 11.77/11.50 in 2025. These point scales reflect different price and volatility regimes; their ratio is not an estimate of changing edge.

The annual excursion scale changes materially, particularly in 2025–2026. Fixed point targets or stops inferred from pooled years would ignore that regime difference. MAE and MFE alone cannot show whether a stop or target would have filled first, and the terminal-positive rate ignores trading costs. Overlapping paths and the 35 exploratory combinations do not constitute independent confirmation.

The final back-adjusted indicator snapshot is retrospective and may differ from TradingView. Paths with missing minutes, partial bars, roll transitions, or changed contracts are unavailable rather than zero. 2010 starts midyear and 2026 is year-to-date through the pinned September 18 bars.

## Full evidence

See `tables/yearly.csv` for all 595 year/cooldown/horizon cells, medians, p90s, approximate ISO-week clustered mean intervals, and exclusion reasons; `tables/events.parquet` for event-level outcomes; `metrics.json`, `config.json`, and `inputs.lock.json` for definitions and identities. Open `report.html` offline to filter the complete table.
